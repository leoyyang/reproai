from __future__ import annotations

from typing import Any

from pathlib import Path

from . import dependency_graph, inventory, orphan_detector, reports, rule_engine, stata_esttab_parser, venue_engine, versions
from .adversarial_reviewer import audit_priorities, cross_check


def check(root: Path, venue: str | None) -> dict[str, Any]:
    root = root.resolve()
    entries = inventory.scan(root)
    edges = dependency_graph.build(root, entries)
    exports = stata_esttab_parser.parse(root, entries)
    orphans = orphan_detector.detect(entries, edges)

    arch = reports.architecture_report(root, entries, edges, exports, orphans)
    arch["entry_points"] = dependency_graph.entry_points(entries, edges)

    findings = rule_engine.run(root, entries, edges, exports)
    advisory = reports.advisory_plan(root, findings)

    venue_block = None
    checks: list[venue_engine.Check] = []
    if venue:
        meta, checks = venue_engine.run(root, entries, venue)
        venue_block = reports.venue_compliance_report(root, meta, checks)

    risk = reports.risk_register(root, advisory, checks)

    conflicts = cross_check(findings, checks)
    priority_violations = audit_priorities(findings)

    return {
        "knowledge_versions": versions.knowledge_versions(),
        "architecture_report": arch,
        "advisory_plan": advisory,
        "venue_compliance_report": venue_block,
        "risk_register": risk,
        "adversarial_review": {
            "conflicts": conflicts,
            "priority_violations": priority_violations,
        },
    }
