#!/usr/bin/env python3
"""Template: project-local open-run readiness QA.

Copy into the active project, implement the Aspen adapters, then call
record_open_run_readiness.py with the resulting evidence.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ReadinessResult:
    clean_session_reopen: str
    required_input_complete: str
    manual_inputs_needed_after_open: str
    run_can_start_without_manual_input: str
    run_result_or_blocker: str
    same_version_export_after_reopen: str
    control_panel_or_history: str
    block_status_file: str
    stream_status_file: str
    audit_json: str
    post_run_bkp_saved: str
    migrated_path_readiness_record: str
    physical_plausibility_record: str
    remaining_required_input_items: list[str]
    decision: str


def perform_readiness_probe(case_file: Path, out_dir: Path) -> ReadinessResult:
    """Project edit point.

    Required proof:
    1. clean Aspen session reopens delivered file;
    2. Required Input is complete;
    3. Run starts without manual input;
    4. same-version export after reopen exists.
    5. accepted delivery also records migrated-path readiness, post-run BKP
       status when BKP is claimed, and physical plausibility evidence.
    """
    raise NotImplementedError("Implement Aspen clean reopen / Required Input / start-run probe.")


def call_recorder(project_name: str, project_dir: Path, case_file: Path, result: ReadinessResult, recorder: Path) -> int:
    cmd = [
        sys.executable,
        str(recorder),
        "--project-name", project_name,
        "--project-dir", str(project_dir),
        "--case-file", str(case_file),
        "--clean-session-reopen", result.clean_session_reopen,
        "--required-input-complete", result.required_input_complete,
        "--manual-inputs-needed-after-open", result.manual_inputs_needed_after_open,
        "--run-can-start-without-manual-input", result.run_can_start_without_manual_input,
        "--run-result-or-user-accepted-blocker", result.run_result_or_blocker,
        "--same-version-export-after-reopen", result.same_version_export_after_reopen,
        "--control-panel-or-history", result.control_panel_or_history,
        "--block-status-file", result.block_status_file,
        "--stream-status-file", result.stream_status_file,
        "--audit-json", result.audit_json,
        "--post-run-bkp-saved", result.post_run_bkp_saved,
        "--migrated-path-readiness-record", result.migrated_path_readiness_record,
        "--physical-plausibility-record", result.physical_plausibility_record,
        "--decision", result.decision,
    ]
    for item in result.remaining_required_input_items:
        cmd.extend(["--remaining-required-input-item", item])
    return subprocess.call(cmd)


def main() -> int:
    parser = argparse.ArgumentParser(description="Project-local open-run readiness template.")
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--case-file", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--recorder", required=True, help="Path to record_open_run_readiness.py")
    args = parser.parse_args()

    result = perform_readiness_probe(Path(args.case_file), Path(args.out_dir))
    rc = call_recorder(args.project_name, Path(args.project_dir), Path(args.case_file), result, Path(args.recorder))
    if result.decision.startswith("blocked") or result.decision == "candidate-backup":
        return 2
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
