#!/usr/bin/env python3
"""Record a project-local Aspen process slice for later digestion."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from learning_admission import case_audit_metadata, evidence_references, lineage_admission, resolve_project_output


def main() -> int:
    parser = argparse.ArgumentParser(description="Record an Aspen process slice.")
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--slice-id", required=True)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--authority-basis", default="")
    parser.add_argument("--input-boundary", default="")
    parser.add_argument("--output-boundary", default="")
    parser.add_argument("--blocks-or-scripts-touched", action="append", default=[])
    parser.add_argument("--run-status", default="")
    parser.add_argument("--control-panel-or-history", default="")
    parser.add_argument("--evidence", action="append", default=[])
    parser.add_argument("--heating-pressure-pressure-drop-notes", default="")
    parser.add_argument("--calculator-design-spec-notes", default="")
    parser.add_argument("--what-worked", default="")
    parser.add_argument("--what-failed", default="")
    parser.add_argument("--reusable-script-candidate", default="")
    parser.add_argument("--next-allowed-action", default="")
    parser.add_argument("--output-dir", default="")
    parser.add_argument('--lineage-manifest', help='Optional strict lineage inspection; a process slice remains case-audit-only.')
    parser.add_argument('--eligibility-module', help='Explicit absolute trusted canonical evaluator for offline tests.')
    parser.add_argument('--acceptance-mode', choices=['strict', 'case_relaxed', 'legacy_unassessed', 'unknown'], default='unknown')
    args = parser.parse_args()

    try:
        base_dir = resolve_project_output(args.project_dir, args.output_dir, 'aspen_material_library')
    except ValueError as exc:
        parser.error(str(exc))
    base_dir.mkdir(parents=True, exist_ok=True)

    entry = {
        'schema': 'aspen-case-process-slice-v2',
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "project_name": args.project_name,
        "slice_id": args.slice_id,
        "phase": args.phase,
        "scope": args.scope,
        "authority_basis": args.authority_basis,
        "input_boundary": args.input_boundary,
        "output_boundary": args.output_boundary,
        "blocks_or_scripts_touched": args.blocks_or_scripts_touched,
        "run_status": args.run_status,
        "control_panel_or_history": args.control_panel_or_history,
        "stream_status_audit_evidence": args.evidence,
        "heating_pressure_pressure_drop_notes": args.heating_pressure_pressure_drop_notes,
        "calculator_design_spec_notes": args.calculator_design_spec_notes,
        "what_worked": args.what_worked,
        "what_failed": args.what_failed,
        "reusable_script_candidate": args.reusable_script_candidate,
        "next_allowed_action": args.next_allowed_action,
        **case_audit_metadata(lineage_admission(args.lineage_manifest, evaluator_path=args.eligibility_module)),
        'reported_acceptance_mode': args.acceptance_mode,
        'evidence_references': evidence_references(args.evidence, base_dir=Path(args.project_dir).resolve()),
    }

    day = datetime.now().strftime("%Y%m%d")
    jsonl_path = base_dir / f"{day}_process_slices.jsonl"
    md_path = base_dir / f"{day}_process_slices.md"

    with jsonl_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    with md_path.open("a", encoding="utf-8") as handle:
        handle.write(f"## {entry['timestamp']} - {args.slice_id} - {args.phase}\n\n")
        handle.write('- Scope: `case_audit_only`; learning eligible: `false`; default retrieval: `false`.\n')
        handle.write(f'- Reported acceptance mode: `{args.acceptance_mode}` (self-report only).\n')
        handle.write(f"- Scope: {args.scope}\n")
        if args.authority_basis:
            handle.write(f"- Authority basis: {args.authority_basis}\n")
        if args.input_boundary:
            handle.write(f"- Input boundary: {args.input_boundary}\n")
        if args.output_boundary:
            handle.write(f"- Output boundary: {args.output_boundary}\n")
        if args.blocks_or_scripts_touched:
            handle.write("- Blocks/scripts touched:\n")
            for item in args.blocks_or_scripts_touched:
                handle.write(f"  - `{item}`\n")
        if args.run_status:
            handle.write(f"- Run status: {args.run_status}\n")
        if args.control_panel_or_history:
            handle.write(f"- Control Panel/history: {args.control_panel_or_history}\n")
        if args.evidence:
            handle.write("- Evidence:\n")
            for item in args.evidence:
                handle.write(f"  - `{item}`\n")
        if args.heating_pressure_pressure_drop_notes:
            handle.write(f"- Heating/pressure/pressure-drop notes: {args.heating_pressure_pressure_drop_notes}\n")
        if args.calculator_design_spec_notes:
            handle.write(f"- Calculator/Design Spec notes: {args.calculator_design_spec_notes}\n")
        if args.what_worked:
            handle.write(f"- What worked: {args.what_worked}\n")
        if args.what_failed:
            handle.write(f"- What failed: {args.what_failed}\n")
        if args.reusable_script_candidate:
            handle.write(f"- Reusable script candidate: `{args.reusable_script_candidate}`\n")
        if args.next_allowed_action:
            handle.write(f"- Next allowed action: {args.next_allowed_action}\n")
        handle.write("\n")

    print(f"Wrote {jsonl_path}")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
