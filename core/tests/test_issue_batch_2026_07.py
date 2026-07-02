"""Regression tests for the 2026-07 engine-fix batch (GitHub issues #8, #10, #19, #20, #21, #23, #24).

Each test pins the fixed behavior AND its anti-bypass / no-false-negative boundary, so a future edit
that "simplifies" a fix and reopens the hole fails here.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

from line1_core import coordinator, gate, inventory, dependency_graph, venue_engine


def _write(pkg: Path, files: dict[str, str]) -> Path:
    for rel, content in files.items():
        p = pkg / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return pkg


def _write_xlsx(path: Path, sheet_names: list[str]) -> None:
    """Minimal .xlsx (a zip with just xl/workbook.xml) carrying the given sheet names."""
    path.parent.mkdir(parents=True, exist_ok=True)
    sheets = "".join(
        f'<sheet name="{n}" sheetId="{i + 1}" r:id="rId{i + 1}"/>' for i, n in enumerate(sheet_names)
    )
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("xl/workbook.xml", f'<?xml version="1.0"?><workbook><sheets>{sheets}</sheets></workbook>')


def _fired(root: Path, venue: str | None = None) -> set[str]:
    return {it["rule_id"] for it in coordinator.check(root, venue)["advisory_plan"]["items"]}


def _venue_status(root: Path, venue: str = "generic_dataverse") -> dict[str, str]:
    entries = inventory.scan(root)
    edges = dependency_graph.build(root, entries)
    _meta, checks = venue_engine.run(root, entries, venue, edges)
    # keep the last status per detector (each detector appears at most once per profile here)
    return {c.detector: c.status for c in checks if c.detector}


# ---------------------------------------------------------------------------- #21 screenreg export
def test_screenreg_file_export_is_credited(tmp_path: Path) -> None:
    pkg = _write(tmp_path / "p", {"a.R": (
        '# --> Table 1\n'
        'm1 <- glm(y ~ x, data = df, family = binomial())\n'
        'screenreg(list(m1), file = "output/tables/table_1.txt")\n'
    )})
    code, report = gate.gate_static(pkg)
    assert code == 0 and report["passed"], report
    assert report["expected_total"] == 1 and report["with_export"] == 1


def test_screenreg_without_canonical_path_still_fails(tmp_path: Path) -> None:
    # anti-bypass: a console screenreg (no tables/ segment) must NOT count
    pkg = _write(tmp_path / "p", {"a.R": (
        '# --> Table 1\nm1 <- glm(y ~ x, data = df)\nscreenreg(list(m1), file = "console.txt")\n'
    )})
    code, report = gate.gate_static(pkg)
    assert code == 1 and report["with_export"] == 0


# ---------------------------------------------------------------------------- #20 multi-line export
def test_multiline_texreg_file_on_continuation_is_credited(tmp_path: Path) -> None:
    pkg = _write(tmp_path / "p", {"a.R": (
        '# --> Table 1\n'
        'm1 <- lm(y ~ x1, data = df); m2 <- lm(y ~ x1 + x2, data = df)\n'
        'texreg::texreg(l = list(m1, m2),\n'
        '       custom.model.names = c("Model A", "Model B"),\n'
        '       file = "output/tables/table_1.txt")\n'
    )})
    code, report = gate.gate_static(pkg)
    assert code == 0 and report["passed"], report


def test_multiline_export_decoy_in_caption_not_credited(tmp_path: Path) -> None:
    # anti-bypass: a tables/ path that appears only inside a label option is not an output target
    pkg = _write(tmp_path / "p", {"a.R": (
        '# --> Table 1\nm1 <- lm(y ~ x, data = df)\n'
        'texreg::texreg(list(m1),\n'
        '       caption = "see output/tables/appendix for details")\n'
    )})
    code, report = gate.gate_static(pkg)
    assert code == 1 and report["with_export"] == 0


def test_downstream_input_read_not_swallowed_as_export(tmp_path: Path) -> None:
    # the export call closes on its own line; a later read.csv INPUT must not be credited to it
    pkg = _write(tmp_path / "p", {"a.R": (
        '# --> Table 1\nm1 <- lm(y ~ x, data = df)\n'
        'texreg(list(m1), file = "plain.txt")\n'
        'prior <- read.csv("output/tables/prior_run.csv")\n'
    )})
    code, report = gate.gate_static(pkg)
    assert code == 1 and report["with_export"] == 0


# ---------------------------------------------------------------------------- #19 abs-path UNC / LaTeX
def test_latex_macro_in_coef_names_is_not_an_abs_path(tmp_path: Path) -> None:
    pkg = _write(tmp_path / "p", {"a.R": (
        'm <- MASS::polr(as.factor(y) ~ x, data = read.csv("data/synthetic.csv"))\n'
        'texreg::texreg(list(m),\n'
        '       custom.coef.names = c("Intercept", "x", "\\\\tau_{1|2}", "\\\\tau_{2|3}"),\n'
        '       file = "output/tables/table_1.tex")\n'
    )})
    assert "B4-no-abs-paths" not in _fired(pkg)
    assert _venue_status(pkg).get("no_absolute_paths") == "pass"


def test_real_unc_and_drive_paths_still_flag(tmp_path: Path) -> None:
    # no-false-negative: genuine absolute paths (letter host, IP host, drive) must still fire
    pkg = _write(tmp_path / "p", {"a.R": (
        'a <- read.csv("\\\\\\\\fileserver\\\\share\\\\data.csv")\n'
        'b <- read.csv("\\\\\\\\192.168.1.5\\\\share\\\\panel.csv")\n'
        'setwd("C:\\\\project\\\\data")\n'
    )})
    assert "B4-no-abs-paths" in _fired(pkg)
    assert _venue_status(pkg).get("no_absolute_paths") == "fail"


# ---------------------------------------------------------------------------- #8 no executable code
def test_a16_fires_on_data_only_no_code(tmp_path: Path) -> None:
    pkg = _write(tmp_path / "p", {"survey.xlsx": "x,y\n1,2\n", "README.md": "GUI analysis in SmartPLS"})
    assert "A16-no-executable-code" in _fired(pkg)


def test_a16_fires_on_gui_project_with_embedded_data(tmp_path: Path) -> None:
    # SmartPLS with data embedded in the .splsm binary and only a README: no loose data file
    pkg = _write(tmp_path / "p", {"model.splsm": "<binary>", "README.md": "see the SmartPLS project"})
    assert "A16-no-executable-code" in _fired(pkg)


def test_a16_fires_when_only_code_is_empty(tmp_path: Path) -> None:
    # a comment-only script is not runnable, so it must not silence A16
    pkg = _write(tmp_path / "p", {"empty.do": "* just a header comment\n", "data.csv": "x\n1\n"})
    assert "A16-no-executable-code" in _fired(pkg)


def test_a16_silent_on_normal_package(tmp_path: Path) -> None:
    pkg = _write(tmp_path / "p", {
        "a.do": 'use "data.csv", clear\nreg y x\nesttab using "output/tables/t.csv", replace\n',
        "data.csv": "x\n1\n"})
    assert "A16-no-executable-code" not in _fired(pkg)


def test_a16_silent_on_qualitative_deposit(tmp_path: Path) -> None:
    # no code AND no data: a document corpus expects no computation (composes with #24)
    pkg = _write(tmp_path / "p", {"interview.pdf": "%PDF", "notes.md": "methodology"})
    assert "A16-no-executable-code" not in _fired(pkg)


# ---------------------------------------------------------------------------- #10 results not shipped
def test_d8_fires_when_no_code_and_no_results(tmp_path: Path) -> None:
    pkg = _write(tmp_path / "p", {"data.csv": "x,y\n1,2\n", "README.md": "results in the manuscript"})
    assert "D8-results-not-shipped" in _fired(pkg)


def test_d8_silent_when_results_are_shipped(tmp_path: Path) -> None:
    pkg = _write(tmp_path / "p", {
        "data.csv": "x,y\n1,2\n", "README.md": "r", "output/tables/t1.csv": "coef\n1\n"})
    assert "D8-results-not-shipped" not in _fired(pkg)


def test_d8_silent_when_code_present(tmp_path: Path) -> None:
    # with code, D1 + the gate own output coverage; D8 must not double-flag
    pkg = _write(tmp_path / "p", {"a.do": "use data.csv\nreg y x\n", "data.csv": "x\n1\n"})
    assert "D8-results-not-shipped" not in _fired(pkg)


def test_d8_silent_on_qualitative_deposit(tmp_path: Path) -> None:
    pkg = _write(tmp_path / "p", {"interview.pdf": "%PDF", "notes.md": "methodology"})
    assert "D8-results-not-shipped" not in _fired(pkg)


# ---------------------------------------------------------------------------- #23 structural master
def test_master_script_recognized_by_structure_not_name(tmp_path: Path) -> None:
    # meta.R is a run-all whose name matches none of master/main/run_all/runall
    pkg = _write(tmp_path / "p", {
        "meta.R": 'source("01_prep.R")\nsource("02_analyze.R")\n',
        "01_prep.R": "x <- 1\n", "02_analyze.R": "m <- lm(y ~ x)\n", "README.md": "run meta.R"})
    assert _venue_status(pkg).get("has_master_script") == "pass"
    # and the venue check now agrees with the architecture report about the same file
    arch_eps = {e["path"] for e in coordinator.check(pkg, "generic_dataverse")["architecture_report"]["entry_points"]}
    assert "meta.R" in arch_eps


def test_bogus_master_sourcing_only_missing_file_does_not_pass(tmp_path: Path) -> None:
    # anti-bypass: a script whose only include is dangling must not manufacture a master
    pkg = _write(tmp_path / "p", {"driver.R": 'source("does_not_exist.R")\n', "README.md": "x"})
    assert _venue_status(pkg).get("has_master_script") == "needs_author_action"


# ---------------------------------------------------------------------------- #24 no-code venue checks
def test_code_presuming_venue_checks_not_applicable_without_code(tmp_path: Path) -> None:
    pkg = _write(tmp_path / "p", {
        "interview_corpus.pdf": "%PDF", "document_corpus.pdf": "%PDF", "README.md": "qualitative deposit"})
    status = _venue_status(pkg)
    for det in ("has_master_script", "env_declared", "rederive_from_raw", "no_absolute_paths"):
        assert status.get(det) == "not_applicable", (det, status.get(det))


def test_code_presuming_venue_checks_active_with_code(tmp_path: Path) -> None:
    # byte-for-byte behavior when code IS present: these detectors run normally
    pkg = _write(tmp_path / "p", {
        "master.do": 'do "a.do"\n', "a.do": 'use data.csv\nreg y x\n', "data.csv": "x\n1\n",
        "README.md": "software: Stata 17"})
    status = _venue_status(pkg)
    assert status.get("has_master_script") == "pass"
    assert status.get("no_absolute_paths") in {"pass", "fail"}  # ran, not skipped


# ---------------------------------------------------------------------------- #22 figure-served estimations
def test_figure_only_script_does_not_demand_a_phantom_table(tmp_path: Path) -> None:
    pkg = _write(tmp_path / "p", {"a.R": (
        "# --> Figure 1\n"
        "m1 <- glm(y ~ x * g, data = df, family = binomial())\n"
        'pdf(file = "output/figures/figure_1.pdf")\n'
        "plot(m1)\ndev.off()\n"
    )})
    code, report = gate.gate_static(pkg)
    assert code == 0 and report["passed"], report
    # exactly one artifact (the figure), no unlabeled table
    assert report["expected_total"] == 1
    assert "D1-output-artifact-coverage" not in _fired(pkg)


def test_stata_regression_grouped_with_its_plot_needs_no_table(tmp_path: Path) -> None:
    pkg = _write(tmp_path / "p", {"a.do": (
        "* Figure 1\nreg y x\ncoefplot\ngraph export \"output/figures/f1.png\", replace\n"
    )})
    code, report = gate.gate_static(pkg)
    assert code == 0 and report["passed"], report


def test_naked_regression_still_demands_a_table(tmp_path: Path) -> None:
    # teeth preserved: an estimation with neither a table nor a figure export must still fail the gate
    pkg = _write(tmp_path / "p", {"a.do": "use d.dta\nreg y x\n"})
    code, report = gate.gate_static(pkg)
    assert code == 1
    assert any(a["artifact_id"] == "Table (unlabeled)" for a in report["missing_export"])


def test_unlabeled_table_with_real_export_still_passes(tmp_path: Path) -> None:
    pkg = _write(tmp_path / "p", {"a.do": 'reg y x\nesttab using "output/tables/t.csv", replace\n'})
    code, report = gate.gate_static(pkg)
    assert code == 0 and report["passed"]


# ---------------------------------------------------------------------------- #9 LLM data provenance
def test_d9_fires_on_llm_data_without_provenance(tmp_path: Path) -> None:
    pkg = _write(tmp_path / "p", {"gpt4_survey.csv": "a\n1\n", "README.md": "we generated the survey"})
    _write_xlsx(pkg / "GPT Prompts.xlsx", ["Sheet1"])
    assert "D9-llm-data-provenance" in _fired(pkg)


def test_d9_silent_with_full_provenance(tmp_path: Path) -> None:
    pkg = _write(tmp_path / "p", {
        "gpt4_survey.csv": "a\n1\n",
        "README.md": "Generated with gpt-4o (snapshot 2024-08-06), temperature = 0.7, seed = 42."})
    assert "D9-llm-data-provenance" not in _fired(pkg)


def test_d9_ignores_bare_prompt_variable_name(tmp_path: Path) -> None:
    # 'prompt' is a common survey variable name; without a strong LLM token it must not fire
    pkg = _write(tmp_path / "p", {"prompt_response.csv": "a\n1\n", "analysis.do": "reg y x\n"})
    assert "D9-llm-data-provenance" not in _fired(pkg)


def test_d9_requires_versioned_model_id_not_vague_mention(tmp_path: Path) -> None:
    # a vague "we used GPT" with no versioned id / parameter does NOT clear the finding
    pkg = _write(tmp_path / "p", {"gpt_data.csv": "a\n1\n", "README.md": "We used GPT to generate this."})
    assert "D9-llm-data-provenance" in _fired(pkg)


def test_d9_detects_llm_sheet_in_innocuous_workbook(tmp_path: Path) -> None:
    pkg = _write(tmp_path / "p", {"README.md": "survey data"})
    _write_xlsx(pkg / "data.xlsx", ["Responses", "ChatGPT prompts"])
    assert "D9-llm-data-provenance" in _fired(pkg)


def test_d9_silent_on_ordinary_package(tmp_path: Path) -> None:
    pkg = _write(tmp_path / "p", {"a.do": "use d.dta\nreg y x\n", "d.dta": "x\n1\n"})
    assert "D9-llm-data-provenance" not in _fired(pkg)
