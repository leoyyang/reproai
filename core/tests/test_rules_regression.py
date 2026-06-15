from __future__ import annotations

from pathlib import Path

from line1_core import coordinator


def _rules_fired(root: Path, venue: str | None = None) -> set[str]:
    result = coordinator.check(root, venue)
    return {item["rule_id"] for item in result["advisory_plan"]["items"]}


def test_messy_pkg_fires_expected_rules(messy_pkg: Path) -> None:
    fired = _rules_fired(messy_pkg, venue="aea")
    expected = {
        "A6-guarded-fallback-load",
        "A8-data-ref-extension-mismatch",
        "B4-no-abs-paths",
        "B7-no-cross-script-clearall",
        "C5-deprecated-r-packages",
        "C6-old-stata-merge-syntax",
        "B8-r-table-call-syntax",
        "B11-rmd-chunk-in-r",
    }
    missing = expected - fired
    assert not missing, f"expected rules not fired: {missing} (fired: {sorted(fired)})"


def test_messy_pkg_has_orphan_missing_ref(messy_pkg: Path) -> None:
    result = coordinator.check(messy_pkg, "aea")
    missing = result["architecture_report"]["orphans"]["referenced_missing"]
    targets = {m["target"] for m in missing}
    assert any("helper_missing" in t for t in targets), f"helper_missing not flagged: {targets}"


def test_clean_pkg_is_low_noise(clean_pkg: Path) -> None:
    fired = _rules_fired(clean_pkg, venue="aea")
    forbidden = {
        "B4-no-abs-paths", "C5-deprecated-r-packages", "C6-old-stata-merge-syntax",
        "A6-guarded-fallback-load", "B11-rmd-chunk-in-r", "B8-r-table-call-syntax",
        "N1-no-delimit-semicolon", "C4-deprecated-syntax-signature",
        "D1-output-artifact-coverage", "D3-intermediate-data-hygiene",
    }
    leaked = forbidden & fired
    assert not leaked, f"clean package falsely fired: {leaked}"


def test_d1_fires_when_estimation_has_no_export(tmp_path: Path) -> None:
    pkg = tmp_path / "no_export"
    pkg.mkdir()
    (pkg / "a.do").write_text('use data.dta, clear\nreg y x z\n', encoding="utf-8")
    assert "D1-output-artifact-coverage" in _rules_fired(pkg)


def test_a11_and_d3_fire_on_multiscript_intermediate(tmp_path: Path) -> None:
    pkg = tmp_path / "multi"
    pkg.mkdir()
    (pkg / "01_build.do").write_text('use raw.dta, clear\nsave "intermediate.dta", replace\n', encoding="utf-8")
    (pkg / "02_analysis.do").write_text('use "intermediate.dta", clear\nreg y x\n', encoding="utf-8")
    (pkg / "readme.txt").write_text("See paper.\n", encoding="utf-8")
    fired = _rules_fired(pkg)
    assert "A11-explicit-run-order" in fired, fired
    assert "D3-intermediate-data-hygiene" in fired, fired


def test_d1_reports_each_table_section(tmp_path: Path) -> None:
    pkg = tmp_path / "tables"
    pkg.mkdir()
    (pkg / "a.do").write_text(
        "use data.dta, clear\n"
        "* Table 1: first\nreg y x\n"
        "* Table 2: second\nreg y z\n"
        "* Table 3: third\nreg y w\n",
        encoding="utf-8",
    )
    result = coordinator.check(pkg, None)
    d1 = [it for it in result["advisory_plan"]["items"] if it["rule_id"] == "D1-output-artifact-coverage"]
    assert d1, "D1 did not fire"
    labels = " ".join(e.get("snippet", "") for e in d1[0]["evidence"])
    assert "Table 1" in labels and "Table 2" in labels and "Table 3" in labels, labels


def test_a12_fires_when_tables_uncommented(tmp_path: Path) -> None:
    pkg = tmp_path / "uncommented"
    pkg.mkdir()
    (pkg / "a.do").write_text(
        "use data.dta, clear\nreg y x1 x2, cluster(id)\nreg y x1 x2 x3, cluster(id)\nreg z x1, cluster(id)\n",
        encoding="utf-8",
    )
    assert "A12-table-comment-mapping" in _rules_fired(pkg)


def test_a12_silent_when_tables_commented(tmp_path: Path) -> None:
    pkg = tmp_path / "commented"
    pkg.mkdir()
    (pkg / "a.do").write_text(
        "use data.dta, clear\n* Table 1\nreg y x1, cluster(id)\n* Table 2\nreg z x1, cluster(id)\n",
        encoding="utf-8",
    )
    assert "A12-table-comment-mapping" not in _rules_fired(pkg)


def test_r_assigned_estimations_are_detected(tmp_path: Path) -> None:
    pkg = tmp_path / "rpkg"
    pkg.mkdir()
    (pkg / "tables.R").write_text(
        "df <- read.csv('d.csv')\n"
        "m1 <- ivreg(y ~ x | z, data=df)\n"
        "m2 <- lm(y ~ x2, data=df)\n"
        "fit = feols(y ~ x3, data=df)\n",
        encoding="utf-8",
    )
    fired = _rules_fired(pkg)
    assert "A12-table-comment-mapping" in fired, fired
    assert "D1-output-artifact-coverage" in fired, fired


def test_d4_fires_when_files_undocumented(tmp_path: Path) -> None:
    pkg = tmp_path / "undoc"
    pkg.mkdir()
    (pkg / "clean.do").write_text("use raw.dta, clear\nreg y x\n", encoding="utf-8")
    (pkg / "build.do").write_text("use raw.dta, clear\ngen z = x\n", encoding="utf-8")
    assert "D4-per-file-documentation" in _rules_fired(pkg)


def test_priority_sorting(messy_pkg: Path) -> None:
    items = coordinator.check(messy_pkg, "aea")["advisory_plan"]["items"]
    order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}
    priorities = [order[i["priority"]] for i in items]
    assert priorities == sorted(priorities), "advisory items are not priority-sorted"


def test_no_reproducibility_verdict(messy_pkg: Path) -> None:
    result = coordinator.check(messy_pkg, "aea")
    blob = str(result).upper()
    for forbidden in ("REPRODUCIBLE", "NOT_REPRODUCIBLE", "FULLY", "LARGELY"):
        assert forbidden not in blob, f"Line 1 must not emit a reproducibility verdict, found: {forbidden}"
