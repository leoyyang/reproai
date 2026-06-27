"""Phase 2: missing-input detection (A5 / A14 / A15) and B4 / D6 false-positive tightening.

The confidence gate is load-bearing: a relative literal read that is genuinely absent is a P0, but a
read produced by a write edge, an absolute path, a Python read, or an ambiguous basename is NOT.
"""
from __future__ import annotations

from pathlib import Path

from line1_core import coordinator


def _fired(root: Path) -> set[str]:
    return {it["rule_id"] for it in coordinator.check(root, None)["advisory_plan"]["items"]}


# --- A5: unresolved include (now actually emits, was a ghost rule) -----------------------------

def test_a5_fires_on_missing_include(tmp_path: Path) -> None:
    pkg = tmp_path / "inc"
    pkg.mkdir()
    (pkg / "master.do").write_text('do "child.do"\n', encoding="utf-8")
    assert "A5-stable-includes" in _fired(pkg)


def test_a5_silent_when_include_resolves(tmp_path: Path) -> None:
    pkg = tmp_path / "inc_ok"
    pkg.mkdir()
    (pkg / "master.do").write_text('do "child.do"\n', encoding="utf-8")
    (pkg / "child.do").write_text("reg y x\n", encoding="utf-8")
    assert "A5-stable-includes" not in _fired(pkg)


# --- A14: unresolved relative read, gated by the write graph -----------------------------------

def test_a14_fires_on_missing_relative_read(tmp_path: Path) -> None:
    pkg = tmp_path / "rd"
    pkg.mkdir()
    (pkg / "a.do").write_text('use "data/panel.dta", clear\nreg y x\n', encoding="utf-8")
    assert "A14-missing-input" in _fired(pkg)


def test_a14_silent_when_read_is_written_upstream(tmp_path: Path) -> None:
    pkg = tmp_path / "inter"
    pkg.mkdir()
    (pkg / "raw.dta").write_text("x\n1\n", encoding="utf-8")  # the raw input ships
    (pkg / "01_build.do").write_text('use raw.dta, clear\nsave "data/inter.dta", replace\n', encoding="utf-8")
    (pkg / "02_run.do").write_text('use "data/inter.dta", clear\nreg y x\n', encoding="utf-8")
    # inter.dta is produced by a write edge -> a pipeline intermediate, not a missing input
    assert "A14-missing-input" not in _fired(pkg)


def test_a14_silent_when_read_resolves(tmp_path: Path) -> None:
    pkg = tmp_path / "rd_ok"
    (pkg / "data").mkdir(parents=True)
    (pkg / "a.do").write_text('use "data/panel.dta", clear\nreg y x\n', encoding="utf-8")
    (pkg / "data" / "panel.dta").write_text("x\n1\n", encoding="utf-8")
    assert "A14-missing-input" not in _fired(pkg)


def test_a14_skips_absolute_path_to_b4(tmp_path: Path) -> None:
    pkg = tmp_path / "abs"
    pkg.mkdir()
    (pkg / "a.do").write_text('use "/home/me/secret/panel.dta", clear\nreg y x\n', encoding="utf-8")
    fired = _fired(pkg)
    assert "A14-missing-input" not in fired, "absolute path is B4's domain, not A14"
    assert "B4-no-abs-paths" in fired


def test_a14_skips_python_read(tmp_path: Path) -> None:
    pkg = tmp_path / "py"
    pkg.mkdir()
    (pkg / "a.py").write_text('import pandas as pd\ndf = pd.read_csv("missing.csv")\n', encoding="utf-8")
    assert "A14-missing-input" not in _fired(pkg), "Python is best-effort, never a P0 missing-input"


# --- A15: ambiguous basename is advisory, never P0 ---------------------------------------------

def test_a15_fires_on_basename_collision(tmp_path: Path) -> None:
    pkg = tmp_path / "amb"
    (pkg / "data").mkdir(parents=True)
    (pkg / "other").mkdir(parents=True)
    (pkg / "data" / "x.csv").write_text("a\n", encoding="utf-8")
    (pkg / "other" / "x.csv").write_text("a\n", encoding="utf-8")
    (pkg / "a.R").write_text('d <- read.csv("x.csv")\nm <- lm(y ~ x, data = d)\n', encoding="utf-8")
    fired = _fired(pkg)
    assert "A15-ambiguous-input-path" in fired
    assert "A14-missing-input" not in fired, "ambiguous must never escalate to a P0 missing-input"


# --- B4 tightening: a regex-escape literal is not an absolute path -----------------------------

def test_b4_silent_on_regex_escape_literal(tmp_path: Path) -> None:
    pkg = tmp_path / "esc"
    pkg.mkdir()
    (pkg / "a.R").write_text('clean <- gsub("\\\\|", "_", raw)\n', encoding="utf-8")
    assert "B4-no-abs-paths" not in _fired(pkg)


def test_b4_still_fires_on_real_abs_path(tmp_path: Path) -> None:
    pkg = tmp_path / "real"
    pkg.mkdir()
    (pkg / "a.R").write_text('d <- read.csv("/home/me/data/d.csv")\n', encoding="utf-8")
    assert "B4-no-abs-paths" in _fired(pkg)


# --- D6: brace globs, package-root token, documented-as-absent --------------------------------

def test_d6_silent_on_brace_glob_when_members_ship(tmp_path: Path) -> None:
    pkg = tmp_path / "glob_ok"
    (pkg / "data").mkdir(parents=True)
    (pkg / "a.R").write_text("x <- 1\n", encoding="utf-8")
    (pkg / "data" / "wave_1.dta").write_text("a\n", encoding="utf-8")
    (pkg / "data" / "wave_2.dta").write_text("a\n", encoding="utf-8")
    (pkg / "README.md").write_text("Reads the panel waves `data/wave_{1,2}.dta`.\n", encoding="utf-8")
    assert "D6-readme-missing-paths" not in _fired(pkg)


def test_d6_fires_on_brace_glob_missing_member(tmp_path: Path) -> None:
    pkg = tmp_path / "glob_bad"
    (pkg / "data").mkdir(parents=True)
    (pkg / "a.R").write_text("x <- 1\n", encoding="utf-8")
    (pkg / "data" / "wave_1.dta").write_text("a\n", encoding="utf-8")
    (pkg / "README.md").write_text("Reads the panel waves `data/wave_{1,2}.dta`.\n", encoding="utf-8")
    assert "D6-readme-missing-paths" in _fired(pkg)


def test_d6_silent_on_documented_absent(tmp_path: Path) -> None:
    pkg = tmp_path / "absent"
    pkg.mkdir()
    (pkg / "a.R").write_text("x <- 1\n", encoding="utf-8")
    (pkg / "README.md").write_text(
        "The raw administrative data `restricted_panel.dta` is confidential and not included; "
        "obtain it from the agency.\n",
        encoding="utf-8",
    )
    assert "D6-readme-missing-paths" not in _fired(pkg)


def test_d6_silent_on_package_root_token(tmp_path: Path) -> None:
    pkg = tmp_path / "myrepl"
    pkg.mkdir()
    (pkg / "a.R").write_text("x <- 1\n", encoding="utf-8")
    (pkg / "README.md").write_text("Unzip and run everything from the `myrepl/` root.\n", encoding="utf-8")
    assert "D6-readme-missing-paths" not in _fired(pkg)
