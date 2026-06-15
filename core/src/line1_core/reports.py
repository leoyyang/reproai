from __future__ import annotations

from typing import Any

from . import GENERATED_BY
from .dependency_graph import Edge
from .inventory import FileEntry
from .orphan_detector import Orphans
from .rule_engine import Finding
from .stata_esttab_parser import TableExport
from .venue_engine import Check

_CANNOT_PREDICT = [
    "Numerical match of coefficients (random seeds, solver behavior, hidden transforms surface only at execution).",
    "Full environment reconstruction (external repos / OS libraries / licensed software may still fail).",
    "Diagnostic fidelity (instrument strength, model classification need real outputs).",
    "Runtime completeness (long scripts, memory, encoding, platform differences are execution-time facts).",
    "Repository acceptance (external validation and human review may add rules).",
]

_DISCLAIMER = (
    "Pre-diagnose maximizes the probability that the downstream reproducibility check passes "
    "on the first try by removing known avoidable failures. It does NOT guarantee a first-try pass."
)

_SEVERITY_BY_PRIORITY = {"P0": "blocker", "P1": "high", "P2": "medium", "P3": "low", "P4": "low"}
_RISK_KIND_BY_CATEGORY = {
    "structural": "structural", "code-style": "structural",
    "environment": "environment", "normalization": "expected_output",
}


def architecture_report(root, entries, edges, exports, orphans) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "generated_by": GENERATED_BY,
        "root": str(root),
        "files": [e.as_dict() for e in entries],
        "entry_points": [],
        "dependency_edges": [
            {"from": e.src, "to": e.dst, "kind": e.kind, "resolved": e.resolved} for e in edges
        ],
        "table_map": [
            {
                "table": x.table,
                "source_file": x.source_file,
                "export_command": x.export_command,
                "line": x.line,
                "output_path": x.output_path,
            }
            for x in exports
        ],
        "orphans": orphans.as_dict(),
    }


_PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}

# Universal lossless contract every host-LLM rewrite must honor, regardless of rule.
_LOSSLESS_CONTRACT = [
    "Work on a COPY of the package; never modify the author's original files.",
    "The rewrite MUST be semantics-preserving: the code must compute exactly the same "
    "results (same coefficients, same sample, same data, same file targets).",
    "Formatting / structural normalization is allowed (e.g. unrolling a foreach loop into "
    "explicit per-model commands, reflowing a call) — changing what the code computes is NOT.",
    "If you cannot make the change without risking a semantic change, do NOT apply it — leave "
    "it as a written recommendation for the author instead.",
]


def _evidence_lines(evidence: list[dict[str, Any]]) -> str:
    parts = []
    for e in evidence:
        loc = e.get("file", "?")
        if e.get("line") is not None:
            loc += f":{e['line']}"
        snip = e.get("snippet")
        parts.append(f"{loc}  {snip}" if snip else loc)
    return "; ".join(parts)


def _fix_prompt(f: Finding) -> str:
    """A self-contained natural-language rewrite directive for the host LLM."""
    mode = (
        "PROPOSE ONLY — describe the fix to the author; do NOT edit code (this finding is "
        "too semantic to rewrite safely)."
        if f.propose_only
        else "REWRITE — apply this fix to the copy, honoring the lossless contract."
    )
    lines = [
        f"[{f.rule_id} | {f.priority} | {f.kind}] {mode}",
        f"PROBLEM: {f.message}",
        f"WHERE: {_evidence_lines(f.evidence)}",
        f"WHY IT HURTS DOWNSTREAM: {f.why_downstream or f.rationale}",
        f"TARGET FORM: {f.target_form}",
    ]
    if f.lossless_note:
        lines.append(f"LOSSLESS BOUNDARY FOR THIS RULE: {f.lossless_note}")
    return "\n".join(lines)


def advisory_plan(root, findings: list[Finding]) -> dict[str, Any]:
    ordered = sorted(findings, key=lambda f: _PRIORITY_ORDER.get(f.priority, 9))
    items = []
    for i, f in enumerate(ordered, start=1):
        items.append({
            "id": f"ADV-{i:03d}",
            "rule_id": f.rule_id,
            "category": f.category,
            "kind": f.kind,
            "priority": f.priority,
            "message": f.message,
            "evidence": f.evidence,
            "rationale": f.rationale,
            "source_lessons": f.source_lessons,
            "why_downstream": f.why_downstream,
            "target_form": f.target_form,
            "rewrite": {
                "mode": "propose_only" if f.propose_only else "llm_rewrite",
                "lossless_note": f.lossless_note,
                "fix_prompt": _fix_prompt(f),
            },
        })
    by_priority = {p: sum(1 for it in items if it["priority"] == p) for p in ["P0", "P1", "P2", "P3", "P4"]}
    return {
        "schema_version": 3,
        "generated_by": GENERATED_BY,
        "root": str(root),
        "lossless_contract": _LOSSLESS_CONTRACT,
        "summary": {
            "total": len(items),
            "by_priority": by_priority,
            "defect": sum(1 for it in items if it["kind"] == "defect"),
            "normalization": sum(1 for it in items if it["kind"] == "normalization"),
            "llm_rewrite": sum(1 for it in items if it["rewrite"]["mode"] == "llm_rewrite"),
            "propose_only": sum(1 for it in items if it["rewrite"]["mode"] == "propose_only"),
        },
        "items": items,
    }


def venue_compliance_report(root, meta: dict[str, Any], checks: list[Check]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "generated_by": GENERATED_BY,
        "root": str(root),
        "venue": meta["venue"],
        "profile_version": meta["profile_version"],
        "standard": meta.get("standard", ""),
        "summary": meta["summary"],
        "checks": [
            {
                "check_id": c.check_id,
                "requirement": c.requirement,
                "status": c.status,
                "detail": c.detail,
                "evidence": c.evidence,
                "source": c.source,
            }
            for c in checks
        ],
    }


def risk_register(root, advisory: dict[str, Any], checks: list[Check]) -> dict[str, Any]:
    risks = []
    idx = 1
    for item in advisory["items"]:
        sev = _SEVERITY_BY_PRIORITY.get(item["priority"], "medium")
        risks.append({
            "id": f"RISK-{idx:03d}",
            "severity": sev,
            "kind": _RISK_KIND_BY_CATEGORY.get(item["category"], "structural"),
            "message": item["message"],
            "predicts": item["rationale"],
            "evidence": [e["file"] for e in item["evidence"]],
            "from_advisory_ids": [item["id"]],
        })
        idx += 1
    for c in checks:
        if c.status == "fail":
            risks.append({
                "id": f"RISK-{idx:03d}",
                "severity": "blocker",
                "kind": "venue",
                "message": c.requirement,
                "predicts": c.detail,
                "evidence": c.evidence,
                "from_advisory_ids": [],
            })
            idx += 1

    summary = {"blocker": 0, "high": 0, "medium": 0, "low": 0}
    for r in risks:
        summary[r["severity"]] += 1

    return {
        "schema_version": 1,
        "generated_by": GENERATED_BY,
        "root": str(root),
        "disclaimer": _DISCLAIMER,
        "summary": summary,
        "risks": risks,
        "cannot_predict": _CANNOT_PREDICT,
    }
