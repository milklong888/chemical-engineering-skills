from __future__ import annotations

import argparse
import atexit
import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AGENT = PACKAGE_ROOT / "app" / "equipment_design_agent.py"


def request(operation: str, payload: dict[str, Any] | None = None, request_id: str | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {
        "schema": "equipment-design-agent-request-v1",
        "operation": operation,
        "payload": payload or {},
    }
    if request_id:
        value["request_id"] = request_id
    return value


class AgentProcess:
    def __init__(
        self,
        executable: Path,
        working_directory: Path,
        timeout_s: int = 300,
        *,
        persistent: bool = False,
    ) -> None:
        self.executable = executable.resolve()
        self.working_directory = working_directory.resolve()
        self.timeout_s = timeout_s
        self.persistent = bool(persistent)
        self.command = (
            [sys.executable, str(self.executable)]
            if self.executable.suffix.casefold() == ".py"
            else [str(self.executable)]
        )
        self._process: subprocess.Popen[str] | None = None
        self._responses: queue.Queue[str | None] = queue.Queue()
        self._stderr_lines: list[str] = []
        self._session_lock = threading.RLock()
        if self.persistent:
            atexit.register(self.close)

    @staticmethod
    def _sanitized_environment() -> dict[str, str]:
        return {
            key: value
            for key, value in os.environ.items()
            if key.casefold() not in {
                "equipment_design_llm_api_key",
                "equipment_design_llm_base_url",
            }
        }

    def _read_session_stdout(self, process: subprocess.Popen[str]) -> None:
        assert process.stdout is not None
        try:
            for line in process.stdout:
                self._responses.put(line)
        finally:
            self._responses.put(None)

    def _read_session_stderr(self, process: subprocess.Popen[str]) -> None:
        assert process.stderr is not None
        for line in process.stderr:
            self._stderr_lines.append(line.rstrip("\r\n"))
            if len(self._stderr_lines) > 200:
                del self._stderr_lines[:50]

    def _ensure_session(self) -> subprocess.Popen[str]:
        if self._process is not None and self._process.poll() is None:
            return self._process
        process = subprocess.Popen(
            [*self.command, "--session-jsonl"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="strict",
            bufsize=1,
            cwd=self.working_directory,
            env=self._sanitized_environment(),
        )
        self._process = process
        self._responses = queue.Queue()
        self._stderr_lines = []
        threading.Thread(
            target=self._read_session_stdout,
            args=(process,),
            name="equipment-agent-jsonl-stdout",
            daemon=True,
        ).start()
        threading.Thread(
            target=self._read_session_stderr,
            args=(process,),
            name="equipment-agent-jsonl-stderr",
            daemon=True,
        ).start()
        return process

    def _call_session(self, value: dict[str, Any]) -> tuple[dict[str, Any], int]:
        with self._session_lock:
            process = self._ensure_session()
            assert process.stdin is not None
            try:
                process.stdin.write(
                    json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                    + "\n"
                )
                process.stdin.flush()
                line = self._responses.get(timeout=self.timeout_s)
            except queue.Empty as exc:
                self.close(force=True)
                raise TimeoutError(
                    f"Agent JSONL session did not respond within {self.timeout_s} s"
                ) from exc
            if line is None:
                return_code = process.poll()
                stderr = "\n".join(self._stderr_lines[-20:])
                raise RuntimeError(
                    f"Agent JSONL session ended before responding; exit={return_code}; stderr={stderr[:1000]!r}"
                )
            try:
                response = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"Agent JSONL response is not one UTF-8 JSON object: {line[:500]!r}"
                ) from exc
            if not isinstance(response, dict):
                raise RuntimeError("Agent JSONL response is not a JSON object.")
            return response, int(response.get("exit_code", 0 if response.get("ok") is True else 2))

    def call(self, value: dict[str, Any]) -> tuple[dict[str, Any], int]:
        if self.persistent:
            return self._call_session(value)
        completed = subprocess.run(
            self.command,
            input=json.dumps(value, ensure_ascii=False),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
            cwd=self.working_directory,
            env=self._sanitized_environment(),
            timeout=self.timeout_s,
            check=False,
        )
        try:
            response = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Agent stdout 不是单一 UTF-8 JSON；exit={completed.returncode}; "
                f"stdout={completed.stdout[:500]!r}; stderr={completed.stderr[:500]!r}"
            ) from exc
        if not isinstance(response, dict):
            raise RuntimeError("Agent 响应不是 JSON 对象。")
        return response, completed.returncode

    def close(self, *, force: bool = False) -> None:
        with self._session_lock:
            process = self._process
            self._process = None
            if process is None or process.poll() is not None:
                return
            try:
                if process.stdin is not None:
                    process.stdin.close()
            except OSError:
                pass
            if force:
                process.kill()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    @property
    def process_mode(self) -> str:
        return "persistent_jsonl" if self.persistent else "one_process_per_request"

    @property
    def session_pid(self) -> int | None:
        return self._process.pid if self._process is not None and self._process.poll() is None else None

    def call_file(
        self,
        value: dict[str, Any],
        request_path: Path,
        response_path: Path,
        *,
        gui_agent_entry: bool = False,
    ) -> tuple[dict[str, Any], int]:
        request_path = request_path.resolve()
        response_path = response_path.resolve()
        request_path.parent.mkdir(parents=True, exist_ok=True)
        response_path.parent.mkdir(parents=True, exist_ok=True)
        request_path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        if gui_agent_entry:
            arguments = ["--agent-request", str(request_path), "--agent-response", str(response_path)]
        else:
            arguments = ["--request", str(request_path), "--output", str(response_path), "--pretty"]
        completed = subprocess.run(
            [*self.command, *arguments],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
            cwd=self.working_directory,
            env=self._sanitized_environment(),
            timeout=self.timeout_s,
            check=False,
        )
        if not response_path.is_file():
            raise RuntimeError(
                f"Agent 文件模式未生成响应；exit={completed.returncode}; "
                f"stdout={completed.stdout[:500]!r}; stderr={completed.stderr[:500]!r}"
            )
        response = json.loads(response_path.read_text(encoding="utf-8-sig"))
        if not isinstance(response, dict):
            raise RuntimeError("Agent 文件响应不是 JSON 对象。")
        return response, completed.returncode


def strict_empty_step(prepared: dict[str, Any]) -> dict[str, Any]:
    context = prepared["context_pack"]
    return {
        "schema": "equipment-design-llm-step-output-v1",
        "injection_point": prepared["injection_point"],
        "context_sha256": context["context_sha256"],
        "summary": "offline deterministic protocol validation",
        "citations": [],
        "proposed_changes": [],
        "condition_assessments": [],
        "terminal_selection_assists": [],
        "calculation_assists": [],
        "retrieval_plan": [],
        "ambiguity_decision": None,
        "audit_findings": [],
        "output_composition": {
            "title": "Offline deterministic protocol validation",
            "blocks": [{
                "block_id": "summary",
                "operation": "explain_result",
                "section_ref": "summary",
                "heading": "Protocol validation",
                "citations": ["deterministic_result"],
            }],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the equipment-design Agent 1.9 replay protocol with LLM/network disabled."
    )
    parser.add_argument("--agent", type=Path, default=DEFAULT_AGENT, help="Python Agent entry or packaged CLI EXE")
    parser.add_argument("--working-dir", type=Path, default=PACKAGE_ROOT, help="Child process working directory")
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print stdout/report")
    parser.add_argument(
        "--one-process-per-request",
        action="store_true",
        help="Diagnostic baseline only; disable the default resident JSONL Agent session.",
    )
    args = parser.parse_args()

    runner = AgentProcess(
        args.agent,
        args.working_dir,
        persistent=not args.one_process_per_request,
    )
    checks: list[dict[str, Any]] = []

    def check(check_id: str, passed: bool, detail: Any) -> None:
        checks.append({"id": check_id, "pass": bool(passed), "detail": detail})

    capabilities, code = runner.call(request("capabilities", request_id="PROTO-CAPS"))
    operations = capabilities.get("result", {}).get("operations", [])
    check("capabilities", code == 0 and capabilities.get("ok") is True, capabilities.get("status"))
    check("protocol_version", capabilities.get("engine", {}).get("agent_protocol_version") == "1.9.0", capabilities.get("engine"))
    check("schema_get_advertised", "schema_get" in operations, operations)

    schema_response, code = runner.call(request(
        "schema_get",
        {"schema_id": "equipment-design-llm-step-output-v1"},
        "PROTO-SCHEMA",
    ))
    document = schema_response.get("result", {}).get("document", {})
    check(
        "strict_step_schema",
        code == 0
        and document.get("additionalProperties") is False
        and "audit_findings" in document.get("properties", {}),
        schema_response.get("result", {}).get("sha256"),
    )

    source_input = {
        "operation": "manual_match",
        "payload": {
            "selection_id": "block:PUMP",
            "values": {
                "equipment_tag": "P-PROTOCOL",
                "phase": "liquid",
                "flow_m3_h": 20,
                "inlet_pressure_mpa": 0.2,
                "outlet_pressure_mpa": 0.6,
                "density_kg_m3": 900,
                "efficiency_percent": 75,
            },
        },
    }
    prepare_payload = {
        "input": source_input,
        "knowledge": {"enabled": False},
        "injection_point": "audit",
        "context_scope": "minimum",
    }
    prepared_response, code = runner.call(request("hybrid_prepare", prepare_payload, "PROTO-PREPARE"))
    prepared = prepared_response.get("result", {})
    replay = prepared.get("replay_contract", {})
    check(
        "prepare_replay_contract",
        code == 0
        and replay.get("schema") == "equipment-design-deterministic-replay-v1"
        and replay.get("input") == source_input
        and len(str(prepared.get("prepared_sha256", ""))) == 64,
        {"state": prepared_response.get("machine_state"), "replayable": replay.get("replayable")},
    )

    step_output = strict_empty_step(prepared)
    continue_response, code = runner.call(request(
        "hybrid_continue",
        {"prepared": prepared, "step_output": step_output},
        "PROTO-CONTINUE",
    ))
    orchestration = continue_response.get("result", {})
    check(
        "external_prepare_continue_replay",
        code == 0
        and orchestration.get("schema") == "equipment-design-app-llm-orchestration-v1"
        and orchestration.get("prepared_sha256") == prepared.get("prepared_sha256")
        and len(str(orchestration.get("orchestration_sha256", ""))) == 64,
        orchestration.get("transition_contract"),
    )

    no_llm_response, code = runner.call(request(
        "hybrid_run",
        {**prepare_payload, "llm": {"enabled": False}},
        "PROTO-NO-LLM",
    ))
    hybrid = no_llm_response.get("result", {})
    deterministic = hybrid.get("deterministic_result", {})
    check(
        "no_llm_unified_v2",
        code == 0
        and hybrid.get("schema") == "equipment-design-hybrid-result-v2"
        and hybrid.get("machine_state", {}).get("state") == "COMPLETED_DETERMINISTIC_ONLY"
        and hybrid.get("machine_state", {}).get("deterministic_result_preserved") is True
        and deterministic.get("result", {}).get("llm_used") is False,
        hybrid.get("machine_state"),
    )

    tower_source_input = {
        "operation": "manual_match",
        "payload": {
            "selection_id": "block:RADFRAC",
            "values": {
                "equipment_tag": "T-PROTOCOL-CONDITION",
                "aspen_block_type": "RADFRAC",
                "process_function": "vacuum distillation; low pressure drop; clean non-fouling service",
            },
        },
    }
    tower_prepare_payload = {
        "input": tower_source_input,
        "knowledge": {"enabled": False},
        "injection_point": "textual_condition_judgment",
        "context_scope": "minimum",
    }
    tower_prepared_response, code = runner.call(request(
        "hybrid_prepare",
        tower_prepare_payload,
        "PROTO-TERMINAL-PREPARE",
    ))
    tower_prepared = tower_prepared_response.get("result", {})
    tower_rules = tower_prepared.get("context_pack", {}).get("terminal_type_rule_registry", [])
    terminal_rule_id = "tower:semantic:vacuum_low_pressure_drop_structured_packing"
    terminal_rule = next(
        (item for item in tower_rules if item.get("rule_id") == terminal_rule_id),
        {},
    )
    valid_terminal_step = strict_empty_step(tower_prepared)
    valid_terminal_step["condition_assessments"] = [{
        "condition_id": terminal_rule.get("condition_id"),
        "status": "supported",
        "reason": "The frozen service text explicitly states vacuum, low pressure drop and clean service.",
        "citations": ["deterministic_result"],
    }]
    valid_terminal_step["terminal_selection_assists"] = [{
        "assist_id": "select_registered_terminal_form",
        "terminal_rule_id": terminal_rule_id,
        "condition_id": terminal_rule.get("condition_id"),
        "selection_context_sha256": terminal_rule.get("selection_context_sha256"),
        "reason": "Select the exact registered structured-packing rule and let the program replay it.",
        "citations": ["deterministic_result"],
    }]
    valid_terminal_step["output_composition"]["blocks"].append({
        "block_id": "condition_assessments",
        "operation": "assess_conditions",
        "section_ref": "condition_assessments",
        "heading": "Registered condition assessment",
        "citations": ["deterministic_result"],
    })
    valid_terminal_step["output_composition"]["blocks"].append({
        "block_id": "terminal_selection",
        "operation": "select_registered_terminal_form",
        "section_ref": "terminal_selection_assists",
        "heading": "Registered terminal-form condition",
        "citations": ["deterministic_result"],
    })
    terminal_hybrid_response, code = runner.call(request(
        "hybrid_run",
        {
            **tower_prepare_payload,
            "llm": {
                "enabled": True,
                "config": {"provider": "mock", "mock_response": valid_terminal_step},
            },
        },
        "PROTO-TERMINAL-VALID",
    ))
    terminal_hybrid = terminal_hybrid_response.get("result", {})
    deterministic_terminal_result = terminal_hybrid.get("deterministic_result")
    if not isinstance(deterministic_terminal_result, dict):
        deterministic_terminal_result = {}
    recalculated_terminal_result = terminal_hybrid.get("deterministic_recalculation")
    if not isinstance(recalculated_terminal_result, dict):
        recalculated_terminal_result = {}
    initial_terminal = (
        deterministic_terminal_result
        .get("result", {})
        .get("model_recommendation", {})
        .get("terminal_selection", {})
    )
    recalculated_terminal = (
        recalculated_terminal_result
        .get("result", {})
        .get("model_recommendation", {})
        .get("terminal_selection", {})
    )
    terminal_application = terminal_hybrid.get("terminal_selection_application", {})
    check(
        "registered_terminal_condition_replayed",
        code == 0
        and initial_terminal.get("status") == "DEFAULTED_TERMINAL_TYPE_SELECTED"
        and initial_terminal.get("recommended_type") == "单溢流筛板塔"
        and recalculated_terminal.get("status") == "CONDITIONED_TERMINAL_TYPE_SELECTED"
        and recalculated_terminal.get("recommended_type") == "规整填料塔"
        and terminal_application.get("applied_rule_id") == terminal_rule_id,
        {
            "initial": initial_terminal,
            "recalculated": recalculated_terminal,
            "application": terminal_application,
            "response_status": terminal_hybrid_response.get("status"),
            "response_errors": terminal_hybrid_response.get("errors"),
            "machine_state": terminal_hybrid.get("machine_state"),
            "llm_status": terminal_hybrid.get("llm_status"),
            "orchestration": terminal_hybrid.get("orchestration"),
        },
    )

    invented_terminal_step = strict_empty_step(tower_prepared)
    invented_terminal_step["terminal_selection_assists"] = [{
        "assist_id": "invented_terminal_rule",
        "terminal_rule_id": "tower:model_invented:magic_tray",
        "condition_id": "tower_condition:model_invented",
        "selection_context_sha256": terminal_rule.get("selection_context_sha256"),
        "reason": "This invented rule must be rejected without blocking the deterministic default.",
        "citations": ["deterministic_result"],
    }]
    invented_terminal_step["output_composition"]["blocks"].append({
        "block_id": "terminal_selection",
        "operation": "select_registered_terminal_form",
        "section_ref": "terminal_selection_assists",
        "heading": "Invented terminal rule rejection",
        "citations": ["deterministic_result"],
    })
    invented_response, invented_code = runner.call(request(
        "hybrid_continue",
        {"prepared": tower_prepared, "step_output": invented_terminal_step},
        "PROTO-TERMINAL-INVENTED",
    ))
    invented_orchestration = invented_response.get("result")
    if not isinstance(invented_orchestration, dict):
        invented_orchestration = {}
    invented_validation = invented_orchestration.get("terminal_selection_assist_validation", [])
    check(
        "invented_terminal_rule_rejected_nonblocking",
        invented_code == 0
        and invented_orchestration.get("verified_terminal_selection_overrides") == {}
        and bool(invented_validation)
        and invented_validation[0].get("status") == "REJECTED_NONBLOCKING_UNKNOWN_RULE",
        {
            "validation": invented_validation,
            "response_status": invented_response.get("status"),
            "response_errors": invented_response.get("errors"),
        },
    )

    forged_response, code = runner.call(request(
        "hybrid_prepare",
        {
            "deterministic_result": {"result": {"model_decision": {"generated_candidate_model": "FORGED"}}},
            "knowledge": {"enabled": False},
            "injection_point": "audit",
            "context_scope": "minimum",
        },
        "PROTO-FORGED",
    ))
    forged_codes = {item.get("code") for item in forged_response.get("errors", [])}
    check(
        "naked_result_rejected",
        code == 2 and bool(forged_codes & {"UNEXPECTED_PAYLOAD_FIELDS", "UNTRUSTED_DETERMINISTIC_RESULT_FORBIDDEN"}),
        sorted(code for code in forged_codes if code),
    )

    invalid_phase_response, code = runner.call(request(
        "manual_match",
        {
            "selection_id": "block:PUMP",
            "values": {"phase": "banana", "flow_m3_h": 20},
        },
        "PROTO-PHASE",
    ))
    invalid_result = invalid_phase_response.get("result", {}).get("result", {})
    invalid_codes = {item.get("code") for item in invalid_result.get("parameter_errors", [])}
    check(
        "invalid_phase_rejected",
        code == 0
        and invalid_result.get("status") == "BLOCKED_INVALID_PARAMETERS"
        and "INVALID_PHASE" in invalid_codes,
        {"status": invalid_result.get("status"), "codes": sorted(code for code in invalid_codes if code)},
    )

    status = "PASS" if checks and all(item["pass"] for item in checks) else "FAIL"
    resident_session_pid = runner.session_pid
    report = {
        "schema": "equipment-design-agent-protocol-validation-v1",
        "status": status,
        "agent": str(args.agent.resolve()),
        "working_directory": str(args.working_dir.resolve()),
        "agent_process_mode": runner.process_mode,
        "resident_session_pid": resident_session_pid,
        "check_count": len(checks),
        "checks": checks,
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True) + "\n"
    if args.output:
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8", newline="\n")
    runner.close()
    sys.stdout.write(rendered)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
