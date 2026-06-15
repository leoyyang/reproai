from __future__ import annotations

import time
from pathlib import Path

from line1_core import gate


def _do(pkg: Path, name: str, body: str) -> None:
    (pkg / name).write_text(body, encoding="utf-8")


def test_gate_fails_when_table_has_no_export(tmp_path: Path) -> None:
    pkg = tmp_path / "p"; pkg.mkdir()
    _do(pkg, "a.do", "use d.dta, clear\n* Table 1\nreg y x, cluster(id)\n")
    code, report = gate.gate_static(pkg)
    assert code == 1 and not report["passed"]
    assert report["expected_total"] == 1 and report["with_export"] == 0


def test_gate_rejects_misnamed_export_bypass(tmp_path: Path) -> None:
    pkg = tmp_path / "p"; pkg.mkdir()
    # an export NOT under output/tables must not silence the artifact
    _do(pkg, "a.do", '* Table 1\neststo m1: reg y x\nesttab m1 using "mytable.csv", replace\n')
    code, report = gate.gate_static(pkg)
    assert code == 1 and report["with_export"] == 0


def test_gate_passes_only_with_canonical_export(tmp_path: Path) -> None:
    pkg = tmp_path / "p"; pkg.mkdir()
    _do(pkg, "a.do", '* Table 1\neststo m1: reg y x\nesttab m1 using "output/tables/table1.csv", replace\n')
    code, report = gate.gate_static(pkg)
    assert code == 0 and report["passed"]
    assert report["expected_total"] == 1 and report["with_export"] == 1


def test_gate_counts_every_table_and_figure(tmp_path: Path) -> None:
    pkg = tmp_path / "p"; pkg.mkdir()
    _do(pkg, "a.do",
        "* Table 1\nreg y x\n* Table 2\nreg y z\n"
        "* Figure 1\ntwoway scatter y x\n")
    code, report = gate.gate_static(pkg)
    assert report["expected_total"] == 3, report
    assert code == 1


def test_verify_fails_when_output_file_absent(tmp_path: Path) -> None:
    pkg = tmp_path / "p"; pkg.mkdir()
    _do(pkg, "a.do", '* Table 1\neststo m1: reg y x\nesttab m1 using "output/tables/t1.csv", replace\n')
    # gate passes statically (export declared) but the file was never produced
    gcode, _ = gate.gate_static(pkg)
    assert gcode == 0
    vcode, vreport = gate.verify_runtime(pkg)
    assert vcode == 1 and not vreport["passed"]
    assert len(vreport["not_produced"]) == 1


def test_verify_passes_when_output_file_present_and_fresh(tmp_path: Path) -> None:
    pkg = tmp_path / "p"; pkg.mkdir()
    _do(pkg, "a.do", '* Table 1\neststo m1: reg y x\nesttab m1 using "output/tables/t1.csv", replace\n')
    (pkg / "output" / "tables").mkdir(parents=True)
    start = time.time() - 1
    (pkg / "output" / "tables" / "t1.csv").write_text("coef\n1\n", encoding="utf-8")
    vcode, vreport = gate.verify_runtime(pkg, since_epoch=start)
    assert vcode == 0 and vreport["passed"]
    assert vreport["produced"] == 1


def test_d1_and_gate_agree_on_count(tmp_path: Path) -> None:
    from line1_core import coordinator
    pkg = tmp_path / "p"; pkg.mkdir()
    # a figure section whose export goes to a NON-canonical path: both D1 and gate must flag it
    (pkg / "a.do").write_text(
        "* Table 1\nreg y x\nesttab using \"output/tables/t1.csv\", replace\n"
        "* Figure 1\ntwoway scatter y x\ngraph save a, replace\n",
        encoding="utf-8",
    )
    r = coordinator.check(pkg, None)
    d1 = [it for it in r["advisory_plan"]["items"] if it["rule_id"] == "D1-output-artifact-coverage"]
    d1_count = len(d1[0]["evidence"]) if d1 else 0
    _, rep = gate.gate_static(pkg)
    # gate expected total = sections; D1 evidence = sections lacking a canonical export.
    # Figure 1 (graph save a -> non-canonical) must be flagged by BOTH; Table 1 by neither.
    assert d1_count == 1, d1_count
    assert rep["with_export"] == 1 and len(rep["missing_export"]) == 1


def test_gate_counts_unlabeled_artifacts(tmp_path: Path) -> None:
    pkg = tmp_path / "p"; pkg.mkdir()
    # no `* Table/Figure N` headers, but the script builds a table and a figure
    (pkg / "a.do").write_text("use d.dta\nreg y x\ntwoway scatter y x\n", encoding="utf-8")
    _, rep = gate.gate_static(pkg)
    assert rep["expected_total"] == 2, rep  # 1 unlabeled table + 1 unlabeled figure
