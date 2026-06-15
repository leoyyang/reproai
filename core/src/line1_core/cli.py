from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, coordinator, inventory
from . import fix_applier
from . import fix_planner
from . import gate as gate_mod

_REPORT_FILES = {
    "architecture_report": "architecture_report.json",
    "advisory_plan": "advisory_plan.json",
    "venue_compliance_report": "venue_compliance_report.json",
    "risk_register": "risk_register.json",
}


def _cmd_check(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2

    result = coordinator.check(root, args.venue)

    if args.out:
        out_dir = Path(args.out).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        for key, filename in _REPORT_FILES.items():
            payload = result[key]
            if payload is None:
                continue
            (out_dir / filename).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    adv = result["advisory_plan"]["summary"]
    risk = result["risk_register"]["summary"]
    conflicts = result["adversarial_review"]["conflicts"]

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        bp = adv["by_priority"]
        kv = result["knowledge_versions"]
        print(f"reproai check — {root}")
        print(f"  knowledge: engine {kv['engine']}, rules {kv['rules_version']}")
        print(f"  advisory: {adv['total']} items "
              f"(P0={bp['P0']} P1={bp['P1']} P2={bp['P2']} P3={bp['P3']} P4={bp['P4']}; "
              f"{adv['defect']} defect / {adv['normalization']} normalization)")
        if result["venue_compliance_report"] is not None:
            vc = result["venue_compliance_report"]["summary"]
            print(f"  venue ({args.venue}): {vc['pass']} pass / {vc['fail']} fail / "
                  f"{vc['needs_author_action']} need author action")
        print(f"  risk: {risk['blocker']} blocker / {risk['high']} high / "
              f"{risk['medium']} medium / {risk['low']} low")
        if conflicts:
            print(f"  adversarial review: {len(conflicts)} conflict(s) flagged")
        if args.out:
            print(f"  reports written to: {args.out}")
    return 0


def _cmd_fix(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2

    result = coordinator.check(root, args.venue)
    entries = inventory.scan(root)
    file_texts = {
        e.path: (root / e.path).read_text(encoding="utf-8", errors="replace")
        for e in inventory.code_entries(entries)
    }
    plan = fix_planner.build(result["advisory_plan"], file_texts)

    if not plan.edits:
        print("No auto-safe fixes available.")
        print(f"  {len(plan.skipped_propose_only)} advisory item(s) are propose-only — review and apply manually.")
        return 0

    diff = fix_applier.unified_diff(root, plan)
    if not args.apply:
        print(f"[dry-run] {len(plan.edits)} auto-safe edit(s) across {len({e.file for e in plan.edits})} file(s):")
        for e in plan.edits:
            print(f"  {e.file}:{e.line}  [{e.rule_id}] {e.reason}")
        print()
        print(diff)
        print("Run with --apply --out <DIR> to write fixes to a COPY (the original is never touched).")
        return 0

    if not args.out:
        print("error: --apply requires --out <DIR> (fixes are written to a copy, never in place)", file=sys.stderr)
        return 2
    try:
        dest = fix_applier.apply_to_copy(root, plan, Path(args.out))
    except FileExistsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"Applied {len(plan.edits)} auto-safe fix(es) to a copy at: {dest}")
    print(f"  {len(plan.skipped_propose_only)} propose-only item(s) left for manual review.")
    return 0


def _cmd_gate(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2
    code, report = gate_mod.gate_static(root)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"reproai gate (static) — {root}")
        print(f"  expected artifacts: {report['expected_total']}  "
              f"with valid export: {report['with_export']}  missing: {len(report['missing_export'])}")
        for a in report["missing_export"]:
            print(f"  MISSING EXPORT  {a['artifact_id']:12s} [{a['kind']}]  {a['source_file']}:{a['header_line']}")
        print(f"  GATE {'PASS' if report['passed'] else 'FAIL'} (exit {code})")
    return code


def _cmd_verify(args: argparse.Namespace) -> int:
    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 2
    code, report = gate_mod.verify_runtime(root, since_epoch=args.since)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"reproai verify (runtime artifacts) — {root}")
        print(f"  expected: {report['expected_total']}  produced: {report['produced']}  "
              f"not produced: {len(report['not_produced'])}")
        for r in report["not_produced"]:
            print(f"  NOT PRODUCED  {r['artifact_id']:12s} [{r['kind']}]  {r['source_file']}"
                  f"  (valid_export={r['has_valid_export']})")
        print(f"  VERIFY {'PASS' if report['passed'] else 'FAIL'} (exit {code})")
    return code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reproai",
        description="ReproAI pre-diagnose: static, no-execution audit of a replication package.",
    )
    parser.add_argument("--version", action="version", version=f"reproai {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="One-shot static self-check: scan + rules + venue -> JSON reports.")
    check.add_argument("path", help="Path to the replication package working directory.")
    check.add_argument("--venue", default=None, help="Venue profile id (e.g. aea).")
    check.add_argument("--out", default=None, help="Directory to write the 4 JSON reports.")
    check.add_argument("--json", action="store_true", help="Print the full result JSON to stdout.")
    check.set_defaults(func=_cmd_check)

    fix = sub.add_parser("fix", help="Apply auto-safe (semantics-preserving) fixes to a COPY. Dry-run by default.")
    fix.add_argument("path", help="Path to the replication package working directory.")
    fix.add_argument("--venue", default=None, help="Venue profile id (e.g. aea).")
    fix.add_argument("--apply", action="store_true", help="Write fixes to a copy (requires --out). Without this, dry-run.")
    fix.add_argument("--out", default=None, help="Destination directory for the fixed copy (must not exist).")
    fix.set_defaults(func=_cmd_fix)

    gate = sub.add_parser("gate", help="HARD GATE: exit nonzero while any paper Table/Figure lacks a valid output export. The fix loop is done only when this exits 0.")
    gate.add_argument("path", help="Path to the (fixed copy of the) replication package.")
    gate.add_argument("--json", action="store_true", help="Print the full gate report as JSON.")
    gate.set_defaults(func=_cmd_gate)

    verify = sub.add_parser("verify", help="HARD GATE: after running the package, exit nonzero unless every expected Table/Figure output file actually exists, is non-empty (and fresh with --since).")
    verify.add_argument("path", help="Path to the (run) fixed copy of the replication package.")
    verify.add_argument("--since", type=float, default=None, help="Epoch seconds; require artifacts modified at/after this time (run freshness).")
    verify.add_argument("--json", action="store_true", help="Print the full verify report as JSON.")
    verify.set_defaults(func=_cmd_verify)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
