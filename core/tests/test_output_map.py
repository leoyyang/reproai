"""Phase 4: `reproai map` — advisory overlay of manuscript exhibits on package output nodes.

It is OUTSIDE `check`, advisory, LaTeX-only, and degrades gracefully — those properties are tested
as hard as the mapping itself, because the whole point is that it cannot dent check's credibility.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from line1_core import coordinator


def _pkg_with_figure(tmp_path: Path, *, manuscript_ref: str, produces: str) -> tuple[Path, Path]:
    pkg = tmp_path / "p"
    pkg.mkdir()
    (pkg / "fig.do").write_text(
        f'use d.dta, clear\ntwoway scatter y x\ngraph export "{produces}", replace\n', encoding="utf-8")
    tex = pkg / "paper.tex"
    tex.write_text(
        "\\begin{figure}\n"
        f"\\includegraphics{{{manuscript_ref}}}\n"
        "\\caption{The main result.}\n\\label{fig:main}\n"
        "\\end{figure}\n",
        encoding="utf-8",
    )
    return pkg, tex


def test_map_matches_exhibit_to_output(tmp_path: Path) -> None:
    pkg, tex = _pkg_with_figure(tmp_path, manuscript_ref="output/figures/fig1.pdf",
                                produces="output/figures/fig1.pdf")
    rep = coordinator.output_map(pkg, str(tex))
    assert rep["status"] == "ok"
    assert rep["summary"]["exhibits"] == 1
    assert rep["summary"]["exhibits_without_output"] == 0
    assert rep["summary"]["outputs_without_exhibit"] == 0
    assert rep["exhibits"][0]["n_mapped"] == 1


def test_map_matches_when_includegraphics_omits_extension(tmp_path: Path) -> None:
    pkg, tex = _pkg_with_figure(tmp_path, manuscript_ref="fig1", produces="output/figures/fig1.pdf")
    rep = coordinator.output_map(pkg, str(tex))
    assert rep["exhibits"][0]["n_mapped"] == 1, "a bare \\includegraphics{fig1} should match fig1.pdf"


def test_map_flags_exhibit_without_output(tmp_path: Path) -> None:
    pkg, tex = _pkg_with_figure(tmp_path, manuscript_ref="figures/ghost.pdf",
                                produces="output/figures/fig1.pdf")
    rep = coordinator.output_map(pkg, str(tex))
    assert rep["summary"]["exhibits_without_output"] == 1
    assert rep["exhibits_without_output"][0]["kind"] == "figure"


def test_map_flags_output_without_exhibit(tmp_path: Path) -> None:
    pkg, tex = _pkg_with_figure(tmp_path, manuscript_ref="output/figures/fig1.pdf",
                                produces="output/figures/fig1.pdf")
    # the package also produces a second figure the manuscript never shows
    (pkg / "extra.do").write_text('graph export "output/figures/fig_unused.pdf", replace\n', encoding="utf-8")
    rep = coordinator.output_map(pkg, str(tex))
    assert any("fig_unused.pdf" in o for o in rep["outputs_without_exhibit"]), rep["outputs_without_exhibit"]


def test_map_panel_mismatch(tmp_path: Path) -> None:
    pkg = tmp_path / "panels"
    pkg.mkdir()
    (pkg / "fig.do").write_text(
        'graph export "output/figures/panel_a.pdf", replace\n'
        'graph export "output/figures/panel_b.pdf", replace\n',
        encoding="utf-8",
    )
    (pkg / "paper.tex").write_text(
        "\\begin{figure}\n"
        "\\includegraphics{output/figures/panel_a.pdf}\n"
        "\\includegraphics{output/figures/panel_b.pdf}\n"
        "\\includegraphics{output/figures/panel_c.pdf}\n"  # third panel never produced
        "\\caption{Three panels.}\\label{fig:three}\n\\end{figure}\n",
        encoding="utf-8",
    )
    rep = coordinator.output_map(pkg, str(pkg / "paper.tex"))
    assert rep["summary"]["panel_mismatches"] == 1
    pm = rep["panel_mismatches"][0]
    assert pm["n_panels"] == 3 and pm["n_mapped"] == 2


def test_map_matches_stata_table_input(tmp_path: Path) -> None:
    pkg = tmp_path / "tbl"
    pkg.mkdir()
    (pkg / "t.do").write_text(
        'use d.dta, clear\n* Table 1\nreg y x\nesttab using "output/tables/t1.tex", replace\n', encoding="utf-8")
    (pkg / "paper.tex").write_text(
        "\\begin{table}\n\\input{output/tables/t1.tex}\n\\caption{Estimates.}\\label{tab:1}\n\\end{table}\n",
        encoding="utf-8",
    )
    rep = coordinator.output_map(pkg, str(pkg / "paper.tex"))
    assert rep["exhibits"][0]["kind"] == "table" and rep["exhibits"][0]["n_mapped"] == 1


def test_map_appendix_numbering(tmp_path: Path) -> None:
    pkg = tmp_path / "appx"
    pkg.mkdir()
    (pkg / "fig.do").write_text('graph export "output/figures/a.pdf", replace\n', encoding="utf-8")
    (pkg / "paper.tex").write_text(
        "\\begin{figure}\\includegraphics{main.pdf}\\caption{Main}\\label{fig:m}\\end{figure}\n"
        "\\appendix\n"
        "\\begin{figure}\\includegraphics{output/figures/a.pdf}\\caption{Appx}\\label{fig:a}\\end{figure}\n",
        encoding="utf-8",
    )
    rep = coordinator.output_map(pkg, str(pkg / "paper.tex"))
    numbers = {e["number"] for e in rep["exhibits"]}
    assert "1" in numbers and "A1" in numbers, numbers


# --- graceful degradation ---------------------------------------------------------------------

def test_map_unsupported_pdf(tmp_path: Path) -> None:
    pkg = tmp_path / "pdf"
    pkg.mkdir()
    (pkg / "paper.pdf").write_bytes(b"%PDF-1.4")
    rep = coordinator.output_map(pkg, str(pkg / "paper.pdf"))
    assert rep["status"] == "unsupported_format"


def test_map_manuscript_not_found(tmp_path: Path) -> None:
    pkg = tmp_path / "nf"
    pkg.mkdir()
    rep = coordinator.output_map(pkg, str(pkg / "nope.tex"))
    assert rep["status"] == "manuscript_not_found"


# --- isolation from check ---------------------------------------------------------------------

def test_map_is_not_part_of_check(tmp_path: Path) -> None:
    pkg = tmp_path / "iso"
    pkg.mkdir()
    (pkg / "a.do").write_text("reg y x\n", encoding="utf-8")
    result = coordinator.check(pkg, None)
    assert "output_map" not in result, "map must never appear in a check result"


def test_map_report_matches_schema(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    pkg, tex = _pkg_with_figure(tmp_path, manuscript_ref="output/figures/fig1.pdf",
                                produces="output/figures/fig1.pdf")
    rep = coordinator.output_map(pkg, str(tex))
    schema_dir = Path(__file__).resolve().parents[1] / "src/line1_core/schemas"
    schema = json.loads((schema_dir / "output_map_report.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(instance=rep, schema=schema)
