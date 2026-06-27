"""Phase 3: C8 (unseeded stochastic, backend-aware, output-changing) and D7 (codebook coverage),
plus the constraint that C8 must not co-advise an unseeded raw-to-analysis rebuild (adversarial)."""
from __future__ import annotations

from pathlib import Path

from line1_core import coordinator


def _fired(root: Path, venue: str | None = None) -> set[str]:
    return {it["rule_id"] for it in coordinator.check(root, venue)["advisory_plan"]["items"]}


def _item(root: Path, rule_id: str, venue: str | None = None) -> dict:
    items = coordinator.check(root, venue)["advisory_plan"]["items"]
    return next(it for it in items if it["rule_id"] == rule_id)


# --- C8: unseeded stochastic ------------------------------------------------------------------

def test_c8_fires_on_unseeded_sample_r(tmp_path: Path) -> None:
    pkg = tmp_path / "c8r"
    pkg.mkdir()
    (pkg / "boot.R").write_text("idx <- sample(seq_len(n), 500, replace = TRUE)\n", encoding="utf-8")
    assert "C8-unseeded-stochastic" in _fired(pkg)


def test_c8_silent_with_set_seed_r(tmp_path: Path) -> None:
    pkg = tmp_path / "c8r_ok"
    pkg.mkdir()
    (pkg / "boot.R").write_text("set.seed(20260626)\nidx <- sample(seq_len(n), 500, replace = TRUE)\n", encoding="utf-8")
    assert "C8-unseeded-stochastic" not in _fired(pkg)


def test_c8_skips_dopar_case_c7_owns_it(tmp_path: Path) -> None:
    pkg = tmp_path / "c8_par"
    pkg.mkdir()
    (pkg / "boot.R").write_text(
        "library(doParallel)\nregisterDoParallel(4)\n"
        "out <- foreach(i = 1:1000, .combine = rbind) %dopar% { mean(sample(x, replace = TRUE)) }\n",
        encoding="utf-8",
    )
    fired = _fired(pkg)
    assert "C7-nonreproducible-parallel-rng" in fired, "C7 owns the parallel case"
    assert "C8-unseeded-stochastic" not in fired, "C8 must not double-fire on the %dopar% case"


def test_c8_backend_hint_is_future_seed(tmp_path: Path) -> None:
    pkg = tmp_path / "c8_fut"
    pkg.mkdir()
    (pkg / "sim.R").write_text("library(furrr)\nres <- future_map(1:100, ~ rnorm(.x))\n", encoding="utf-8")
    snippet = _item(pkg, "C8-unseeded-stochastic")["evidence"][0]["snippet"]
    assert "future.seed" in snippet, snippet


def test_c8_fires_on_stata_bootstrap(tmp_path: Path) -> None:
    pkg = tmp_path / "c8_stata"
    pkg.mkdir()
    (pkg / "d.dta").write_text("x\n1\n", encoding="utf-8")
    (pkg / "a.do").write_text('use "d.dta", clear\nbootstrap: regress y x\n', encoding="utf-8")
    assert "C8-unseeded-stochastic" in _fired(pkg)


def test_c8_silent_with_stata_set_seed(tmp_path: Path) -> None:
    pkg = tmp_path / "c8_stata_ok"
    pkg.mkdir()
    (pkg / "d.dta").write_text("x\n1\n", encoding="utf-8")
    (pkg / "a.do").write_text('use "d.dta", clear\nset seed 42\nbootstrap: regress y x\n', encoding="utf-8")
    assert "C8-unseeded-stochastic" not in _fired(pkg)


def test_c8_is_propose_only_and_output_changing(tmp_path: Path) -> None:
    pkg = tmp_path / "c8_meta"
    pkg.mkdir()
    (pkg / "boot.R").write_text("idx <- sample(seq_len(n), 500, replace = TRUE)\n", encoding="utf-8")
    rw = _item(pkg, "C8-unseeded-stochastic")["rewrite"]
    assert rw["mode"] == "propose_only"
    assert rw["output_changing"] is True
    assert "OUTPUT-CHANGING" in rw["fix_prompt"]


# --- D7: codebook coverage --------------------------------------------------------------------

def test_d7_fires_on_undocumented_variable(tmp_path: Path) -> None:
    pkg = tmp_path / "d7"
    pkg.mkdir()
    (pkg / "d.dta").write_text("x\n1\n", encoding="utf-8")
    (pkg / "codebook.md").write_text("# Codebook\n- educ: years of education\n- income: household income\n", encoding="utf-8")
    (pkg / "a.do").write_text('use "d.dta", clear\nregress lwage educ income experience\n', encoding="utf-8")
    item = _item(pkg, "D7-codebook-coverage")
    snippet = item["evidence"][0]["snippet"]
    assert "lwage" in snippet and "experience" in snippet, snippet
    assert "educ" not in snippet and "income" not in snippet, "documented vars must not be flagged"


def test_d7_silent_when_all_documented(tmp_path: Path) -> None:
    pkg = tmp_path / "d7_ok"
    pkg.mkdir()
    (pkg / "d.dta").write_text("x\n1\n", encoding="utf-8")
    (pkg / "codebook.md").write_text("lwage educ income experience are all defined here.\n", encoding="utf-8")
    (pkg / "a.do").write_text('use "d.dta", clear\nregress lwage educ income experience\n', encoding="utf-8")
    assert "D7-codebook-coverage" not in _fired(pkg)


def test_d7_silent_without_codebook(tmp_path: Path) -> None:
    pkg = tmp_path / "d7_none"
    pkg.mkdir()
    (pkg / "d.dta").write_text("x\n1\n", encoding="utf-8")
    (pkg / "a.do").write_text('use "d.dta", clear\nregress lwage educ income experience\n', encoding="utf-8")
    assert "D7-codebook-coverage" not in _fired(pkg)


# --- constraint #6: C8 must not co-advise an unseeded raw-to-analysis rebuild ------------------

def test_c8_conflicts_with_rederive_venue(tmp_path: Path) -> None:
    pkg = tmp_path / "c8_conflict"
    pkg.mkdir()
    (pkg / "boot.R").write_text("idx <- sample(seq_len(n), 500, replace = TRUE)\n", encoding="utf-8")
    conflicts = coordinator.check(pkg, "aea")["adversarial_review"]["conflicts"]
    assert any("C8-unseeded-stochastic" in c.get("rule_ids", []) for c in conflicts), conflicts
