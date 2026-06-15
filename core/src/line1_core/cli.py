from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, coordinator, inventory
from . import fix_applier
from . import fix_planner

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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
