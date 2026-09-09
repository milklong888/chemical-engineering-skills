#!/usr/bin/env python3
"""Append a project-local Aspen learning log entry.

This script records all design and repair events. It does not promote lessons
to skills; promotion happens only through a later success review.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from learning_admission import case_audit_metadata, evidence_references, lineage_admission, resolve_project_output


def default_output_dir(project_dir: str, skill_dir: str) -> Path:
    return resolve_project_output(project_dir, '', 'aspen_learning_logs')


def main() -> int:
    parser = argparse.ArgumentParser(description="Append an Aspen learning log event.")
    parser.add_argument("--skill-dir", default=".", help="Skill directory.")
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--project-dir", default="")
    parser.add_argument("--event-type", required=True, choices=[
        "design", "repair", "probe", "failure", "fix", "success",
        "blocker", "decision", "promotion", "quarantine",
    ])
    parser.add_argument("--phase", required=True)
    parser.add_argument("--category", required=True)
    parser.add_argument("--problem-or-goal", required=True)
    parser.add_argument("--authority-basis", default="")
    parser.add_argument("--action-taken", default="")
    parser.add_argument("--evidence", action="append", default=[])
    parser.add_argument("--result", default="")
    parser.add_argument("--next-allowed-action", default="")
    parser.add_argument("--output-dir", default="")
    parser.add_argument('--lineage-manifest', help='Optional strict lineage inspection; an event remains case-audit-only even if it passes.')
    parser.add_argument('--eligibility-module', help='Explicit absolute trusted canonical evaluator for offline tests.')
    parser.add_argument('--acceptance-mode', choices=['strict', 'case_relaxed', 'legacy_unassessed', 'unknown'], default='unknown')
    args = parser.parse_args()

    try:
        out_dir = resolve_project_output(args.project_dir, args.output_dir, 'aspen_learning_logs')
    except ValueError as exc:
        parser.error(str(exc))
    out_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().isoformat(timespec="seconds")
    day = datetime.now().strftime("%Y%m%d")
    entry = {
        'schema': 'aspen-case-audit-event-v2',
        "timestamp": stamp,
        "project_name": args.project_name,
        "event_type": args.event_type,
        "phase": args.phase,
        "category": args.category,
        "problem_or_goal": args.problem_or_goal,
        "authority_basis": args.authority_basis,
        "action_taken": args.action_taken,
        "evidence": args.evidence,
        "result": args.result,
        "next_allowed_action": args.next_allowed_action,
        **case_audit_metadata(lineage_admission(args.lineage_manifest, evaluator_path=args.eligibility_module)),
        'reported_acceptance_mode': args.acceptance_mode,
        'evidence_references': evidence_references(args.evidence, base_dir=Path(args.project_dir).resolve() if args.project_dir else out_dir),
    }

    jsonl_path = out_dir / f"{day}_aspen_learning_log.jsonl"
    md_path = out_dir / f"{day}_aspen_learning_log.md"

    with jsonl_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    with md_path.open("a", encoding="utf-8") as handle:
        handle.write(f"## {stamp} - {args.event_type} - {args.phase}\n\n")
        handle.write('- Scope: `case_audit_only`; learning eligible: `false`; default retrieval: `false`.\n')
        handle.write(f'- Reported acceptance mode: `{args.acceptance_mode}` (self-report only).\n')
        handle.write(f"- Category: `{args.category}`\n")
        handle.write(f"- Problem/goal: {args.problem_or_goal}\n")
        if args.authority_basis:
            handle.write(f"- Authority basis: {args.authority_basis}\n")
        if args.action_taken:
            handle.write(f"- Action taken: {args.action_taken}\n")
        if args.evidence:
            handle.write("- Evidence:\n")
            for item in args.evidence:
                handle.write(f"  - `{item}`\n")
        if args.result:
            handle.write(f"- Result: {args.result}\n")
        if args.next_allowed_action:
            handle.write(f"- Next allowed action: {args.next_allowed_action}\n")
        handle.write("\n")

    print(f"Wrote {jsonl_path}")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
