#!/usr/bin/env python3
"""Prepare a hash-bound SYNTHETIC feedback example, then print its real CLI command.

Usage: python examples/prepare_feedback_case.py --output-dir NEW_DIRECTORY
The parent directory must exist. An existing output directory is never reused.
This prepares inputs only; the printed command runs the bundled equipment and
pressure implementations. No Aspen model or successful replay is fabricated.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
TAG = "SYN-E1"
FAMILY = "family_fixed_tubesheet_exchanger"
BOUNDARY = (
    "SYNTHETIC SOFTWARE EXAMPLE ONLY. The 30 m2 limit is invented for this test, "
    "not a standard, manufacturer rating, project authority or equipment recommendation. "
    "Two units is a conditional initial bound, not a selected count. Segment thermal "
    "states, each side pressure loss, equipment capability and all replay gates remain unverified."
)


def write_json(directory, name, document):
    data = (json.dumps(document, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode("utf-8")
    with (directory / name).open("xb") as handle:
        handle.write(data)
    return {"path": name, "sha256": hashlib.sha256(data).hexdigest().upper()}


def powershell_command(argv):
    """Quote literal arguments, including spaces, apostrophes and dollar signs."""
    return "& " + " ".join("'" + str(part).replace("'", "''") + "'" for part in argv)


def prepare(output_dir):
    directory = Path(output_dir).absolute()
    # Atomic reservation prevents overwriting even an existing empty directory.
    directory.mkdir(exist_ok=False)
    case_id = "SYNTHETIC-FEEDBACK-" + uuid.uuid4().hex
    run_id = "SYNTHETIC-RUN-" + uuid.uuid4().hex
    identity = {"case_id": case_id, "run_id": run_id, "synthetic": True,
                "engineering_evidence": False, "evidence_boundary": BOUNDARY}
    values = {"heat_duty_kw": 1000, "overall_u_w_m2k": 500,
              "lmtd_k": 40, "lmtd_correction_factor": 1}
    units = {"heat_duty_kw": "kW", "overall_u_w_m2k": "W/m2/K",
             "lmtd_k": "K", "lmtd_correction_factor": "1"}
    equipment = {TAG: {"family_id": FAMILY, "values": values, "units": units}}
    export = write_json(directory, "source_export.json", {
        "schema": "equipment-process-canonical-export-v1", **identity,
        "source_type": "synthetic_canonical_input_not_an_Aspen_export", "equipment": equipment})
    authority = write_json(directory, "authority.json", {
        "schema": "equipment-process-authority-v1", **identity,
        "required_method": "Current manual_match calculation; compare a hash-bound synthetic area limit; screen series pressure in Pa",
        "acceptance_criteria": [
            "Exercise actual area derivation Q_W/(U*LMTD*F) and source binding",
            "Retain only a conditional initial count bound; never select two units automatically",
            "Retain connected consumers stale until same-case engineering replay",
            "Do not claim Aspen execution, equipment selection or engineering acceptance"],
        "equipment": equipment})
    limit = write_json(directory, "synthetic_single_unit_limit.json", {
        "schema": "equipment-process-limit-v1", **identity,
        "quantity": "heat_transfer_area_m2", "value": 30, "unit": "m2",
        "source_id": "SYNTHETIC-30-M2-NOT-A-STANDARD", "version": "synthetic-example-v1",
        "locator": "synthetic_single_unit_limit.json#/value",
        "applicability": {"equipment_id": TAG, "family_id": FAMILY,
                          "case_id": case_id, "run_id": run_id,
                          "scope": "Only this synthetic software example"}})
    # This independently computable input expectation is checked against the real
    # backend's current derivation and calculation trace when the command runs.
    expected_area = values["heat_duty_kw"] * 1000 / (
        values["overall_u_w_m2k"] * values["lmtd_k"] * values["lmtd_correction_factor"])
    constraint = write_json(directory, "constraint_review.json", {
        "schema": "synthetic-equipment-constraint-review-v1", **identity,
        "constraints": [{**identity, "equipment_id": TAG, "status": "verified_applicable",
            "applicability": "Applicability verified only inside this synthetic fixture; no real engineering authority",
            "quantity": "heat_transfer_area_m2", "unit": "m2", "relation": "max",
            "value": expected_area, "limit": 30,
            "value_source": {"kind": "current_selector_derivation", "field": "heat_transfer_area_m2"},
            "limit_source": {**limit, "pointer": "/value"}}]})
    context = {**identity, "source_export": export, "authority": authority,
        "constraint_evidence": {TAG: [{**constraint, "pointer": "/constraints/0"}]},
        "configuration_checks": {TAG: [{"method": "series_pressure",
            "input_basis": "Synthetic absolute inlet 500 kPa; one declared side has sequential losses 20 and 30 kPa, converted to Pa. No EDR rating or second-side check.",
            "inputs": {"inlet_pressure_pa": 500000, "losses_pa": [20000, 30000]}}]},
        "topology": {"nodes": ["SYN-P1", TAG, "SYN-S1", "SYN-DISCONNECTED"],
                     "edges": [["SYN-P1", TAG], [TAG, "SYN-S1"]]}}
    request = write_json(directory, "feedback_request.json", {
        **identity, "operation": "feedback", "payload": {
            "selector_request": {"schema": "equipment-design-agent-request-v1",
                "request_id": case_id, "operation": "manual_match", "payload": {
                    "selection_id": "family:" + FAMILY,
                    "values": {"equipment_tag": TAG, **values}}}, "context": context}})
    request_path = directory / request["path"]
    result_path = directory / "feedback_result.json"
    argv = [sys.executable, "-X", "utf8", str(ROOT / "tools" / "expert_cli.py"),
            "--request", str(request_path), "--evidence-root", str(directory),
            "--output", str(result_path)]
    summary = {"schema": "synthetic-feedback-example-v1", **identity,
        "status": "INPUTS_PREPARED_NOT_EXECUTED", "output_dir": str(directory),
        "request_path": str(request_path), "result_path": str(result_path),
        "files": [export, authority, limit, constraint, request],
        "next_command_argv": argv, "next_command": powershell_command(argv),
        "next_action": "Run next_command once to produce actual backend and feedback results. Inspect binding_gaps, revision, configuration_calculations and affected_consumers; do not treat a candidate as accepted."}
    write_json(directory, "case_manifest.json", summary)
    return summary


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path,
                        help="New directory in an existing parent; existing paths are never overwritten")
    args = parser.parse_args()
    try:
        result = prepare(args.output_dir)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "NOT_PREPARED", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
