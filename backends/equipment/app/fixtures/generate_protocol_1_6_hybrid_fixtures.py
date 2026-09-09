from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


FIXTURE_DIR = Path(__file__).resolve().parent
APP_DIR = FIXTURE_DIR.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import equipment_design_agent as agent  # noqa: E402
import llm_bridge  # noqa: E402


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"JSON fixture must be an object: {path}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def execute_checked(request: dict[str, Any]) -> dict[str, Any]:
    response, exit_code = agent.execute_request(request)
    if exit_code != 0 or response.get("ok") is not True:
        raise RuntimeError(json.dumps(response, ensure_ascii=False, indent=2))
    return response


def audit_step_output(prepared: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": llm_bridge.STEP_OUTPUT_SCHEMA,
        "injection_point": "audit",
        "context_sha256": prepared["context_pack"]["context_sha256"],
        "summary": "Protocol 1.6 offline fixture audit completed.",
        "citations": [],
        "proposed_changes": [],
        "condition_assessments": [],
        "retrieval_plan": [],
        "ambiguity_decision": None,
        "audit_findings": [
            {
                "finding_id": "P16-FIXTURE-BOUNDARY",
                "severity": "info",
                "message": "The deterministic result remains authoritative.",
                "citations": ["deterministic_result"],
            }
        ],
    }


def build_suite() -> dict[str, Any]:
    prepare_request = read_json(FIXTURE_DIR / "protocol_1_6_hybrid_prepare_request.json")
    no_llm_request = read_json(FIXTURE_DIR / "protocol_1_6_hybrid_run_no_llm_request.json")
    prepare_response = execute_checked(prepare_request)
    prepared = prepare_response["result"]
    step_output = audit_step_output(prepared)
    continue_request = {
        "schema": "equipment-design-agent-request-v1",
        "request_id": "REQ-P16-HYBRID-CONTINUE",
        "operation": "hybrid_continue",
        "payload": {"prepared": prepared, "step_output": step_output},
    }
    continue_response = execute_checked(continue_request)

    run_request = {
        "schema": "equipment-design-agent-request-v1",
        "request_id": "REQ-P16-HYBRID-RUN-MOCK",
        "operation": "hybrid_run",
        "payload": {
            **prepare_request["payload"],
            "llm": {
                "enabled": True,
                "config": {
                    "provider": "mock",
                    "model": "offline-fixture",
                    "mock_response": step_output,
                },
            },
        },
    }
    run_response = execute_checked(run_request)
    no_llm_response = execute_checked(no_llm_request)
    run_orchestration = run_response["result"]["orchestration"]
    continue_orchestration = continue_response["result"]
    if run_orchestration["orchestration_sha256"] != continue_orchestration["orchestration_sha256"]:
        raise RuntimeError("hybrid_run and hybrid_continue produced different orchestration hashes")
    if no_llm_response["result"]["machine_state"]["state"] != "COMPLETED_DETERMINISTIC_ONLY":
        raise RuntimeError("no-LLM hybrid_run did not preserve deterministic-only state")
    return {
        "prepare_request": prepare_request,
        "prepare_response": prepare_response,
        "prepared": prepared,
        "step_output": step_output,
        "continue_request": continue_request,
        "continue_response": continue_response,
        "run_request": run_request,
        "run_response": run_response,
        "no_llm_request": no_llm_request,
        "no_llm_response": no_llm_response,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate and verify replay-safe Agent protocol 1.6 hybrid fixtures."
    )
    parser.add_argument(
        "--output-dir",
        help="Optional directory for materialized prepared/continue/run fixtures and responses.",
    )
    args = parser.parse_args(argv)
    suite = build_suite()
    written: list[str] = []
    if args.output_dir:
        output_dir = Path(args.output_dir).expanduser().resolve()
        names = {
            "prepared": "protocol_1_6_prepared.json",
            "step_output": "protocol_1_6_step_output.json",
            "continue_request": "protocol_1_6_hybrid_continue_request.json",
            "continue_response": "protocol_1_6_hybrid_continue_response.json",
            "run_request": "protocol_1_6_hybrid_run_mock_request.json",
            "run_response": "protocol_1_6_hybrid_run_mock_response.json",
            "prepare_response": "protocol_1_6_hybrid_prepare_response.json",
            "no_llm_response": "protocol_1_6_hybrid_run_no_llm_response.json",
        }
        for key, filename in names.items():
            path = output_dir / filename
            write_json(path, suite[key])
            written.append(str(path))
    summary = {
        "schema": "equipment-design-protocol-1.6-fixture-summary-v1",
        "status": "PASS",
        "agent_protocol_version": agent.PROTOCOL_VERSION,
        "prepared_sha256": suite["prepared"]["prepared_sha256"],
        "context_sha256": suite["prepared"]["context_pack"]["context_sha256"],
        "orchestration_sha256": suite["continue_response"]["result"]["orchestration_sha256"],
        "operations_verified": ["hybrid_prepare", "hybrid_continue", "hybrid_run"],
        "no_llm_state": suite["no_llm_response"]["result"]["machine_state"]["state"],
        "written": written,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
