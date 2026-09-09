#!/usr/bin/env python3
"""Record an Aspen open-run readiness check."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Record Aspen open-run readiness evidence.")
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--case-file", required=True)
    parser.add_argument("--case-version", default="")
    parser.add_argument("--clean-session-reopen", required=True)
    parser.add_argument("--required-input-complete", required=True)
    parser.add_argument("--manual-inputs-needed-after-open", default="none")
    parser.add_argument("--run-can-start-without-manual-input", required=True)
    parser.add_argument("--run-result-or-user-accepted-blocker", default="")
    parser.add_argument("--required-input-evidence-source", default="")
    parser.add_argument("--start-run-evidence-source", default="")
    parser.add_argument("--same-version-export-after-reopen", default="")
    parser.add_argument("--control-panel-or-history", default="")
    parser.add_argument("--block-status-file", default="")
    parser.add_argument("--stream-status-file", default="")
    parser.add_argument("--audit-json", default="")
    parser.add_argument("--remaining-required-input-item", action="append", default=[])
    parser.add_argument("--post-run-bkp-saved", default="")
    parser.add_argument("--migrated-path-readiness-record", default="")
    parser.add_argument("--physical-plausibility-record", default="")
    parser.add_argument(
        "--decision",
        required=True,
        choices=[
            "open-run-ready",
            "accepted-runnable",
            "accepted-runnable-and-portable",
            "open-run-ready-only",
            "candidate-backup",
            "blocked",
            "blocked-portability",
            "blocked-physical",
        ],
    )
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args()

    out_dir = Path(args.output_dir) if args.output_dir else Path(args.project_dir) / "aspen_open_run_readiness"
    out_dir.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "project_name": args.project_name,
        "case_file": args.case_file,
        "case_version": args.case_version,
        "clean_session_reopen": args.clean_session_reopen,
        "required_input_complete": args.required_input_complete,
        "manual_inputs_needed_after_open": args.manual_inputs_needed_after_open,
        "run_can_start_without_manual_input": args.run_can_start_without_manual_input,
        "run_result_or_user_accepted_blocker": args.run_result_or_user_accepted_blocker,
        "required_input_evidence_source": args.required_input_evidence_source,
        "start_run_evidence_source": args.start_run_evidence_source,
        "same_version_export_after_reopen": args.same_version_export_after_reopen,
        "control_panel_or_history": args.control_panel_or_history,
        "block_status_file": args.block_status_file,
        "stream_status_file": args.stream_status_file,
        "audit_json": args.audit_json,
        "remaining_required_input_items": args.remaining_required_input_item,
        "post_run_bkp_saved": args.post_run_bkp_saved,
        "migrated_path_readiness_record": args.migrated_path_readiness_record,
        "physical_plausibility_record": args.physical_plausibility_record,
        "decision": args.decision,
    }

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"{stamp}_open_run_readiness.json"
    md_path = out_dir / f"{stamp}_open_run_readiness.md"

    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        f"# Open-Run Readiness: {args.case_file}",
        "",
        f"- Project: `{args.project_name}`",
        f"- Case version: `{args.case_version}`",
        f"- Clean-session reopen: `{args.clean_session_reopen}`",
        f"- Required Input complete: `{args.required_input_complete}`",
        f"- Manual inputs needed after open: `{args.manual_inputs_needed_after_open}`",
        f"- Run can start without manual input: `{args.run_can_start_without_manual_input}`",
        f"- Decision: `{args.decision}`",
    ]
    if args.run_result_or_user_accepted_blocker:
        lines.append(f"- Run result or accepted blocker: {args.run_result_or_user_accepted_blocker}")
    if args.required_input_evidence_source:
        lines.append(f"- Required Input evidence source: {args.required_input_evidence_source}")
    if args.start_run_evidence_source:
        lines.append(f"- Start-run evidence source: {args.start_run_evidence_source}")
    if args.same_version_export_after_reopen:
        lines.append(f"- Same-version export after reopen: `{args.same_version_export_after_reopen}`")
    if args.control_panel_or_history:
        lines.append(f"- Control Panel/history: {args.control_panel_or_history}")
    if args.block_status_file:
        lines.append(f"- Block status file: `{args.block_status_file}`")
    if args.stream_status_file:
        lines.append(f"- Stream status file: `{args.stream_status_file}`")
    if args.audit_json:
        lines.append(f"- Audit JSON: `{args.audit_json}`")
    if args.post_run_bkp_saved:
        lines.append(f"- Post-run BKP saved: `{args.post_run_bkp_saved}`")
    if args.migrated_path_readiness_record:
        lines.append(f"- Migrated-path readiness record: `{args.migrated_path_readiness_record}`")
    if args.physical_plausibility_record:
        lines.append(f"- Physical plausibility record: `{args.physical_plausibility_record}`")
    if args.remaining_required_input_item:
        lines.append("")
        lines.append("## Remaining Required Input Items")
        for item in args.remaining_required_input_item:
            lines.append(f"- {item}")
    lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
