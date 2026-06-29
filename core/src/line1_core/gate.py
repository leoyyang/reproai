"""Deterministic, code-level gates. Markdown cannot enforce anything; these exit nonzero.

- expected_artifacts(): for every Table N / Figure N section in the package, one record with
  whether it has a VALID export (an export command, inside that section, writing under
  output/tables or output/figures). A misnamed/elsewhere export does NOT count.
- gate_static(): exits nonzero while any expected artifact lacks a valid export. The fix loop
  is "done" only when this returns zero — not when a host LLM says so.
- verify_runtime(): after the package is run, checks each expected artifact's output file
  actually exists, is non-empty, and was modified after a start time. Exits nonzero otherwise.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from . import inventory
from .rule_engine import (
    _TABLE_HEADER, _FIGURE_HEADER, _section_spans, _is_estimation, _GRAPH_CMD,
    _TABLE_EXPORT, _GRAPH_EXPORT, _mask_r_strings_comments,
    _toplevel_estimation_lines, _toplevel_graph_line,
)

# A VALID export must write under a designated `tables/`/`figures/` subfolder. Requiring that SEGMENT
# (not a bare filename) is what stops the "inject a misnamed esttab to silence the finding" bypass:
# `esttab using "mytable.csv"` has no `tables/` segment and still does not count.
#
# Follow-up D (recommend≡detect): broadened from the literal `output/tables(figures)/` to an optional
# leading path prefix `(?:[\w.\-]+[\\/])*`, matching rule_engine._OUT_TABLE_PATH/_OUT_FIGURE_PATH and
# the inline target-extractor in _section_export_targets below — so `output/tables/`,
# `results/tables/`, and bare `tables/` all satisfy D1 and the gate identically.
#
# Follow-up D fix: a left boundary `(?:^|[\\/])` prevents `.search` matching `tables/` as a SUBSTRING
# of a longer dir name (`mytables/`, `notes_tables/`, `vegetables/`, ...). The inline regex in
# _section_export_targets below is already quote-anchored (`["\']` before the path), so it is correct
# as-is and intentionally NOT changed; these two constants needed the boundary to match it.
_OUT_TABLE = re.compile(r'(?:^|[\\/])(?:[\w.\-]+[\\/])*tables[\\/]', re.IGNORECASE)
_OUT_FIGURE = re.compile(r'(?:^|[\\/])(?:[\w.\-]+[\\/])*figures[\\/]', re.IGNORECASE)


@dataclass
class Artifact:
    artifact_id: str          # e.g. "Table 3" / "Figure 2"
    kind: str                 # "table" | "figure"
    source_file: str
    header_line: int
    has_valid_export: bool     # an export under output/{tables,figures} inside this section
    export_targets: list[str]  # the output/... paths this section writes (if any)


def _section_export_targets(body: list[str], out_re: re.Pattern[str], cmd_re: re.Pattern[str]) -> list[str]:
    targets: list[str] = []
    for ln in body:
        masked = _mask_r_strings_comments(ln)
        if not cmd_re.search(masked):
            continue
        # Follow-up D: broadened in lockstep with _OUT_TABLE/_OUT_FIGURE — an optional leading path
        # prefix before the required `tables/`/`figures/` segment, so `results/tables/x.csv` and bare
        # `tables/x.csv` count, while a bare filename (`mytable.csv`, no segment) still does not.
        for m in re.finditer(r'["\']((?:[\w.\-]+[\\/])*(?:tables|figures)[\\/][^"\']+)["\']', ln, re.IGNORECASE):
            targets.append(m.group(1).replace("\\", "/"))
    return targets


def expected_artifacts(root: Path) -> list[Artifact]:
    root = root.resolve()
    out: list[Artifact] = []
    entries = inventory.scan(root)
    for e in inventory.code_entries(entries):
        if e.language not in {"stata", "r"}:
            continue
        text = (root / e.path).read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()

        table_spans = _section_spans(lines, _TABLE_HEADER)
        if table_spans:
            for label, start, end in table_spans:
                body = lines[start:end]
                if not any(_is_estimation(ln) for ln in body):
                    continue
                tgts = _section_export_targets(body, _OUT_TABLE, _TABLE_EXPORT)
                out.append(Artifact(label, "table", e.path, start + 1, bool(tgts), tgts))
        else:
            # no `* Table N` headers: an unlabeled script that builds a table is still one artifact
            tl = _toplevel_estimation_lines(text)
            if tl:
                tgts = _section_export_targets(lines, _OUT_TABLE, _TABLE_EXPORT)
                out.append(Artifact("Table (unlabeled)", "table", e.path, tl[0], bool(tgts), tgts))

        figure_spans = _section_spans(lines, _FIGURE_HEADER)
        if figure_spans:
            for label, start, end in figure_spans:
                body = lines[start:end]
                if not any(_GRAPH_CMD.search(ln) for ln in body):
                    continue
                tgts = _section_export_targets(body, _OUT_FIGURE, _GRAPH_EXPORT)
                out.append(Artifact(label, "figure", e.path, start + 1, bool(tgts), tgts))
        else:
            gl = _toplevel_graph_line(text)
            if gl is not None:
                tgts = _section_export_targets(lines, _OUT_FIGURE, _GRAPH_EXPORT)
                out.append(Artifact("Figure (unlabeled)", "figure", e.path, gl, bool(tgts), tgts))
    return out


def gate_static(root: Path) -> tuple[int, dict[str, Any]]:
    arts = expected_artifacts(root)
    missing = [a for a in arts if not a.has_valid_export]
    report = {
        "gate": "static",
        "expected_total": len(arts),
        "with_export": len(arts) - len(missing),
        "missing_export": [asdict(a) for a in missing],
        "passed": len(missing) == 0,
    }
    return (0 if not missing else 1), report


def verify_runtime(root: Path, since_epoch: float | None = None) -> tuple[int, dict[str, Any]]:
    root = root.resolve()
    arts = expected_artifacts(root)
    produced: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    for a in arts:
        ok_any = False
        detail = []
        for tgt in a.export_targets:
            fp = (root / tgt)
            exists = fp.is_file()
            size = fp.stat().st_size if exists else 0
            fresh = (exists and since_epoch is not None and fp.stat().st_mtime >= since_epoch) or (exists and since_epoch is None)
            ok = exists and size > 0 and fresh
            detail.append({"target": tgt, "exists": exists, "size": size, "fresh": fresh})
            ok_any = ok_any or ok
        rec = {"artifact_id": a.artifact_id, "kind": a.kind, "source_file": a.source_file,
               "has_valid_export": a.has_valid_export, "files": detail, "produced": ok_any}
        (produced if ok_any else failed).append(rec)
    report = {
        "gate": "verify",
        "expected_total": len(arts),
        "produced": len(produced),
        "not_produced": [r for r in failed],
        "passed": len(failed) == 0 and len(arts) > 0,
    }
    return (0 if report["passed"] else 1), report
