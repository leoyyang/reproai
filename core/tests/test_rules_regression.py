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


def test_stata_prefixed_estimations_are_detected(tmp_path: Path) -> None:
    pkg = tmp_path / "prefixed"
    pkg.mkdir()
    (pkg / "t.do").write_text(
        "use d.dta, clear\n"
        "* Table 1\nxi: reg y x i.decade, cluster(id)\n"
        "* Table 2\nxi: ivregress 2sls y (x = z) i.decade, cluster(id)\n",
        encoding="utf-8",
    )
    fired = _rules_fired(pkg)
    assert "D1-output-artifact-coverage" in fired, fired
    assert "A12-table-comment-mapping" not in fired, "Table comments present → A12 should NOT fire"


def test_r_function_library_not_treated_as_analysis(tmp_path: Path) -> None:
    pkg = tmp_path / "lib"
    pkg.mkdir()
    # a pure helper library: estimations only INSIDE function bodies, no top-level analysis
    (pkg / "utils.R").write_text(
        "my_fit <- function(d) {\n  m <- lm(y ~ x, data = d)\n  return(coef(m))\n}\n"
        "my_plot <- function(d) {\n  plot(d$x, d$y)\n}\n",
        encoding="utf-8",
    )
    fired = _rules_fired(pkg)
    assert "A3-data-load" not in fired, "function library should not need a data load"
    assert "D1-output-artifact-coverage" not in fired, "function library defines, doesn't build tables/figures"
    assert "A12-table-comment-mapping" not in fired, "function library is not a table-building script"


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


def test_c7_fires_on_dopar_without_dorng(tmp_path: Path) -> None:
    pkg = tmp_path / "par_bad"
    pkg.mkdir()
    (pkg / "boot.R").write_text(
        "library(doParallel)\nregisterDoParallel(4)\n"
        "out <- foreach(i = 1:1000, .combine = rbind) %dopar% { mean(sample(x, replace = TRUE)) }\n",
        encoding="utf-8",
    )
    assert "C7-nonreproducible-parallel-rng" in _rules_fired(pkg)


def test_c7_silent_with_dorng(tmp_path: Path) -> None:
    pkg = tmp_path / "par_ok"
    pkg.mkdir()
    (pkg / "boot.R").write_text(
        "library(doRNG)\nregisterDoRNG(123)\n"
        "out <- foreach(i = 1:1000, .combine = rbind) %dopar% { mean(sample(x, replace = TRUE)) }\n",
        encoding="utf-8",
    )
    assert "C7-nonreproducible-parallel-rng" not in _rules_fired(pkg)


def test_d5_fires_on_divergent_readmes(tmp_path: Path) -> None:
    pkg = tmp_path / "dup"
    (pkg / "code").mkdir(parents=True)
    (pkg / "ReadMe.pdf").write_bytes(b"%PDF-1.4 draft one")
    (pkg / "code" / "paper2015_ReadMe.pdf").write_bytes(b"%PDF-1.4 draft two")
    assert "D5-duplicate-readme" in _rules_fired(pkg)


def test_d5_silent_on_md_pdf_pair(tmp_path: Path) -> None:
    # a README.md plus its rendered README.pdf at the same location is one document, not a duplicate
    pkg = tmp_path / "pair"
    pkg.mkdir()
    (pkg / "README.md").write_text("# readme\n", encoding="utf-8")
    (pkg / "README.pdf").write_bytes(b"%PDF-1.4 rendered")
    assert "D5-duplicate-readme" not in _rules_fired(pkg)


def test_d6_fires_on_readme_missing_path(tmp_path: Path) -> None:
    pkg = tmp_path / "rm"
    pkg.mkdir()
    (pkg / "a.R").write_text("x <- 1\n", encoding="utf-8")
    (pkg / "README.md").write_text("Run `a.R`. See the `tutorial/` folder for details.\n", encoding="utf-8")
    assert "D6-readme-missing-paths" in _rules_fired(pkg)


def test_d6_silent_when_paths_resolve(tmp_path: Path) -> None:
    pkg = tmp_path / "rm_ok"
    (pkg / "code").mkdir(parents=True)
    (pkg / "code" / "a.R").write_text("x <- 1\n", encoding="utf-8")
    (pkg / "README.md").write_text("Run `code/a.R` to reproduce.\n", encoding="utf-8")
    assert "D6-readme-missing-paths" not in _rules_fired(pkg)


def test_readme_scaffold_assembles_from_structure(tmp_path: Path) -> None:
    pkg = tmp_path / "scaf"
    (pkg / "code").mkdir(parents=True)
    (pkg / "master.R").write_text("source('code/1_prepare.R')\n", encoding="utf-8")
    (pkg / "code" / "1_prepare.R").write_text("library(readr)\n", encoding="utf-8")
    out = coordinator.readme_scaffold(pkg)
    assert "# Replication package" in out
    assert "master.R" in out and "master script" in out
    assert "readr" in out  # detected dependency
    assert "[CONFIRM" in out  # author-only fields are marked, not invented


def test_cli_readme_scaffold_runs(tmp_path: Path, capsys) -> None:
    from line1_core import cli
    pkg = tmp_path / "c"
    pkg.mkdir()
    (pkg / "a.R").write_text("x <- 1\n", encoding="utf-8")
    rc = cli.main(["readme", str(pkg), "--scaffold"])
    assert rc == 0
    assert "# Replication package" in capsys.readouterr().out


def test_a13_fires_on_dead_script(tmp_path: Path) -> None:
    pkg = tmp_path / "orphan"
    (pkg / "code").mkdir(parents=True)
    (pkg / "master.R").write_text("source('code/a.R')\n", encoding="utf-8")
    (pkg / "code" / "a.R").write_text("x <- 1\n", encoding="utf-8")
    (pkg / "code" / "scratch_old.R").write_text("y <- 2\n", encoding="utf-8")
    assert "A13-unreferenced-script" in _rules_fired(pkg)


def test_a13_silent_on_named_helper(tmp_path: Path) -> None:
    # helpers.R is named (sourced) in a.R, so it is not a stray script even if the edge is unresolved
    pkg = tmp_path / "helper"
    (pkg / "code").mkdir(parents=True)
    (pkg / "master.R").write_text("source('code/a.R')\n", encoding="utf-8")
    (pkg / "code" / "a.R").write_text("source('code/helpers.R')\nx <- 1\n", encoding="utf-8")
    (pkg / "code" / "helpers.R").write_text("f <- function() 1\n", encoding="utf-8")
    assert "A13-unreferenced-script" not in _rules_fired(pkg)


def test_a13_silent_without_master(tmp_path: Path) -> None:
    # no sourcing structure at all -> A1/A11 own this, A13 must not pile on
    pkg = tmp_path / "nomaster"
    pkg.mkdir()
    (pkg / "a.R").write_text("x <- 1\n", encoding="utf-8")
    (pkg / "b.R").write_text("y <- 2\n", encoding="utf-8")
    assert "A13-unreferenced-script" not in _rules_fired(pkg)


def test_n5_fires_on_unsafe_filename(tmp_path: Path) -> None:
    pkg = tmp_path / "fn"
    pkg.mkdir()
    (pkg / "a.R").write_text("x <- 1\n", encoding="utf-8")
    (pkg / "raw data (final).csv").write_text("a\n1\n", encoding="utf-8")
    assert "N5-unsafe-filename" in _rules_fired(pkg)


def test_n5_silent_on_clean_filenames(tmp_path: Path) -> None:
    pkg = tmp_path / "fn_ok"
    (pkg / "code").mkdir(parents=True)
    (pkg / "code" / "01_prepare.R").write_text("x <- 1\n", encoding="utf-8")
    (pkg / "data").mkdir()
    (pkg / "data" / "raw_data.csv").write_text("a\n1\n", encoding="utf-8")
    assert "N5-unsafe-filename" not in _rules_fired(pkg)


def test_scaffold_includes_crosswalk(tmp_path: Path) -> None:
    pkg = tmp_path / "cw"
    pkg.mkdir()
    (pkg / "a.do").write_text('use d.dta\n* Table 1\nreg y x\nesttab using "output/tables/t1.tex"\n', encoding="utf-8")
    out = coordinator.readme_scaffold(pkg)
    assert "## Results map" in out and "| Output | Produced by | Saved to |" in out
    assert "## Last verified" in out


def test_no_reproducibility_verdict(messy_pkg: Path) -> None:
    result = coordinator.check(messy_pkg, "aea")
    blob = str(result).upper()
    for forbidden in ("REPRODUCIBLE", "NOT_REPRODUCIBLE", "FULLY", "LARGELY"):
        assert forbidden not in blob, f"Line 1 must not emit a reproducibility verdict, found: {forbidden}"
