#!/usr/bin/env python3
"""Prepare an explicitly synthetic stage call by reusing the feedback fixture."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from examples.prepare_feedback_case import prepare, write_json, powershell_command, TAG

def prepare_stage(output_dir, stage="island"):
    if stage not in {"scaffold", "island", "reconnect", "change"}:
        raise ValueError("Only synthetic calculation stages are supported, never fake delivery")
    directory = Path(output_dir).absolute()
    source = prepare(directory)
    feedback = json.loads(Path(source["request_path"]).read_text(encoding="utf-8"))
    context = feedback["payload"]["context"]
    payload = {
        "stage": stage, "question": "换热器负荷、面积与压降应如何约束当前流程的设备安排？",
        **{key: context[key] for key in ("case_id", "run_id", "source_export", "authority")},
        "equipment_requests": [{"equipment_id": TAG, "request": feedback["payload"]["selector_request"]}],
        "context": context, "pressure_checks": context["configuration_checks"][TAG],
    }
    request = write_json(directory, "design_stage_request.json", {"operation": "design_stage", "payload": payload})
    argv = [sys.executable, "-X", "utf8", str(ROOT / "tools/expert_cli.py"),
            "--request", str(directory / request["path"]), "--evidence-root", str(directory),
            "--output", str(directory / "design_stage_result.json")]
    summary = {"schema": "synthetic-design-stage-example-v1", "synthetic": True,
        "engineering_evidence": False, "status": "INPUTS_PREPARED_NOT_EXECUTED",
        "stage": stage, "files": source["files"] + [request],
        "next_command_argv": argv, "next_command": powershell_command(argv),
        "boundary": source["evidence_boundary"],
        "next_action": "Execute the printed command. Inspect actual calls, equipment feedback and local needs; no Aspen model or engineering acceptance is created."}
    write_json(directory, "design_stage_manifest.json", summary)
    return summary

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--stage", choices=["scaffold", "island", "reconnect", "change"], default="island")
    args = parser.parse_args()
    try:
        value = prepare_stage(args.output_dir, args.stage)
    except (ValueError, OSError) as exc:
        print(json.dumps({"status": "NOT_PREPARED", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(value, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
