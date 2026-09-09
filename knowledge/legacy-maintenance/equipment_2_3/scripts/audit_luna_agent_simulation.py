from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent

import sys

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from validate_agent_hybrid_protocol import AgentProcess, request  # noqa: E402


LUNA_MODEL_ID = "gpt-5.6-luna"
STEP_SCHEMA = "equipment-design-llm-step-output-v1"


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def step_output(prepared: dict[str, Any], injection_point: str, summary: str) -> dict[str, Any]:
    output = {
        "schema": STEP_SCHEMA,
        "injection_point": injection_point,
        "context_sha256": prepared["context_pack"]["context_sha256"],
        "summary": summary,
        "citations": [],
        "proposed_changes": [],
        "condition_assessments": [],
        "terminal_selection_assists": [],
        "calculation_assists": [],
        "retrieval_plan": [],
        "ambiguity_decision": None,
        "audit_findings": [],
        "output_composition": {"title": "Luna assisted equipment reasoning", "blocks": []},
    }
    return organize_output(output)


def organize_output(output: dict[str, Any]) -> dict[str, Any]:
    section_operations = {
        "summary": "explain_result",
        "condition_assessments": "assess_conditions",
        "terminal_selection_assists": "select_registered_terminal_form",
        "calculation_assists": "supplement_calculation_input",
        "retrieval_plan": "plan_knowledge_retrieval",
        "ambiguity_decision": "resolve_ambiguity",
        "audit_findings": "audit",
        "proposed_changes": "propose_descriptive_change",
    }
    blocks: list[dict[str, Any]] = []
    for section, operation in section_operations.items():
        value = output.get(section)
        nonempty = bool(str(value).strip()) if section == "summary" else value is not None and bool(value)
        if nonempty:
            blocks.append({
                "block_id": section,
                "operation": operation,
                "section_ref": section,
                "heading": section.replace("_", " ").title(),
                "citations": ["deterministic_result"],
            })
    output["output_composition"] = {
        "title": "Luna assisted equipment reasoning",
        "blocks": blocks,
    }
    return output


def require_rule(prepared: dict[str, Any], rule_id: str) -> dict[str, Any]:
    rules = prepared["context_pack"].get("terminal_type_rule_registry", [])
    for item in rules:
        if isinstance(item, dict) and item.get("rule_id") == rule_id:
            return item
    raise RuntimeError(f"registered terminal rule not found: {rule_id}")


def prepare_luna_pump(prepared: dict[str, Any]) -> dict[str, Any]:
    output = step_output(
        prepared,
        "audit",
        (
            "The volume flow and density close the registered mass-flow identity. "
            "Use the registered recipe and leave the arithmetic and replay to the program."
        ),
    )
    output["calculation_assists"] = [{
        "assist_id": "derive_mass_flow_from_frozen_inputs",
        "target_field": "mass_flow_kg_h",
        "target_unit": "kg/h",
        "method": "deterministic_recipe",
        "recipe_id": "mass_flow_from_volume_density",
        "proposed_value": None,
        "certainty": "certain",
        "uncertainty_note": None,
        "reason": (
            "The prepared package supplies flow_m3_h and density_kg_m3; the allowlisted "
            "recipe is applicable to the current pump family."
        ),
        "citations": ["deterministic_result"],
    }]
    return organize_output(output)


def prepare_luna_tower_upgrade(prepared: dict[str, Any]) -> dict[str, Any]:
    rule = require_rule(
        prepared,
        "tower:semantic:vacuum_low_pressure_drop_structured_packing",
    )
    output = step_output(
        prepared,
        "textual_condition_judgment",
        (
            "The frozen service description explicitly combines vacuum operation, a low-pressure-drop "
            "objective and clean non-fouling service. Select the matching registered rule only."
        ),
    )
    output["condition_assessments"] = [{
        "condition_id": rule["condition_id"],
        "status": "supported",
        "reason": (
            "All semantic discriminators required by the registered condition occur in the frozen "
            "process-function description."
        ),
        "citations": ["deterministic_result"],
    }]
    output["terminal_selection_assists"] = [{
        "assist_id": "select_registered_structured_packing_rule",
        "terminal_rule_id": rule["rule_id"],
        "condition_id": rule["condition_id"],
        "selection_context_sha256": rule["selection_context_sha256"],
        "reason": (
            "Upgrade the visible default only through the registered condition; the program must replay "
            "the terminal selection."
        ),
        "citations": ["deterministic_result"],
    }]
    return organize_output(output)


def prepare_luna_tower_restraint(prepared: dict[str, Any]) -> dict[str, Any]:
    rule = require_rule(
        prepared,
        "tower:semantic:vacuum_low_pressure_drop_structured_packing",
    )
    output = step_output(
        prepared,
        "textual_condition_judgment",
        (
            "Vacuum service alone does not establish the full registered condition. Retain the program's "
            "visible default until low-pressure-drop intent and clean/non-fouling service are supported."
        ),
    )
    output["condition_assessments"] = [{
        "condition_id": rule["condition_id"],
        "status": "unknown",
        "reason": (
            "The frozen context states vacuum distillation but does not establish both remaining "
            "condition discriminators."
        ),
        "citations": ["deterministic_result"],
    }]
    return organize_output(output)


def check(condition: bool, check_id: str, detail: Any) -> dict[str, Any]:
    return {"id": check_id, "pass": bool(condition), "detail": detail}


def run_case(
    agent: AgentProcess,
    *,
    case_id: str,
    source_input: dict[str, Any],
    knowledge: dict[str, Any],
    injection_point: str,
    response_builder: Callable[[dict[str, Any]], dict[str, Any]],
    verifier: Callable[[dict[str, Any]], list[dict[str, Any]]],
) -> dict[str, Any]:
    prepare_request = request(
        "hybrid_prepare",
        {
            "input": source_input,
            "knowledge": knowledge,
            "injection_point": injection_point,
            "context_scope": "routed",
        },
        request_id=f"{case_id}_prepare",
    )
    prepared_response, prepare_exit = agent.call(prepare_request)
    if prepare_exit != 0 or prepared_response.get("ok") is not True:
        raise RuntimeError(f"{case_id}: hybrid_prepare failed: {prepared_response}")
    prepared = prepared_response["result"]
    simulated_model_output = response_builder(prepared)
    hybrid_request = request(
        "hybrid_run",
        {
            "input": source_input,
            "knowledge": knowledge,
            "injection_point": injection_point,
            "context_scope": "routed",
            "llm": {
                "enabled": True,
                "config": {
                    "provider": "mock",
                    "model": LUNA_MODEL_ID,
                    "mock_response": simulated_model_output,
                },
            },
        },
        request_id=f"{case_id}_run",
    )
    hybrid_response, hybrid_exit = agent.call(hybrid_request)
    checks = [
        check(prepare_exit == 0, "prepare_exit_zero", prepare_exit),
        check(hybrid_exit == 0, "hybrid_exit_zero", hybrid_exit),
        check(hybrid_response.get("ok") is True, "agent_response_ok", hybrid_response.get("status")),
    ]
    if hybrid_response.get("ok") is True:
        result = hybrid_response["result"]
        orchestration = result.get("orchestration") or {}
        checks.extend([
            check(
                result.get("machine_state", {}).get("deterministic_authority") is True,
                "deterministic_authority_preserved",
                result.get("machine_state"),
            ),
            check(
                result.get("machine_state", {}).get("deterministic_result_preserved") is True,
                "initial_result_preserved",
                result.get("machine_state"),
            ),
            check(orchestration.get("provider") == "mock", "mock_provider_recorded", orchestration.get("provider")),
            check(orchestration.get("model") == LUNA_MODEL_ID, "luna_model_id_recorded", orchestration.get("model")),
            check(result.get("fallback", {}).get("used") is False, "no_fallback_used", result.get("fallback")),
        ])
        checks.extend(verifier(result))
    return {
        "case_id": case_id,
        "simulation_contract": {
            "provider": "mock",
            "model_id": LUNA_MODEL_ID,
            "remote_network_call": False,
            "uses_public_agent_operation": "hybrid_run",
            "validator_path": "hybrid_prepare -> provider mock -> hybrid_continue -> deterministic replay",
        },
        "source_input": source_input,
        "knowledge_request": knowledge,
        "prepare_request_sha256": canonical_sha256(prepare_request),
        "prepared_sha256": prepared.get("prepared_sha256"),
        "prepared_coverage_status": prepared.get("context_pack", {}).get("coverage_status"),
        "prepared_knowledge_hits": len(prepared.get("context_pack", {}).get("knowledge_hits", [])),
        "simulated_model_output": simulated_model_output,
        "hybrid_request_sha256": canonical_sha256(hybrid_request),
        "hybrid_response": hybrid_response,
        "checks": checks,
        "status": "PASS" if checks and all(item["pass"] for item in checks) else "FAIL",
    }


def verify_pump(result: dict[str, Any]) -> list[dict[str, Any]]:
    orchestration = result.get("orchestration") or {}
    application = result.get("calculation_assist_application") or {}
    recalculated = result.get("deterministic_recalculation")
    validations = orchestration.get("calculation_assist_validation") or []
    timeline = result.get("execution_timeline", {}).get("steps", [])
    timeline_ids = [item.get("step_id") for item in timeline if isinstance(item, dict)]
    return [
        check(
            orchestration.get("verified_calculation_inputs") == {"mass_flow_kg_h": 18000.0},
            "program_computed_mass_flow",
            orchestration.get("verified_calculation_inputs"),
        ),
        check(
            bool(validations) and validations[0].get("status") == "VERIFIED_DETERMINISTIC_DERIVATION",
            "registered_recipe_verified",
            validations,
        ),
        check(
            application.get("applied_inputs") == {"mass_flow_kg_h": 18000.0}
            and not application.get("overwritten_fields"),
            "missing_only_input_applied",
            application,
        ),
        check(recalculated is not None, "deterministic_recalculation_returned", recalculated is not None),
        check(
            timeline_ids[0:1] == ["program_deterministic_initial"]
            and timeline_ids[-1:] == ["program_deterministic_recalculation"],
            "program_anchors_bound_ai_operations",
            timeline_ids,
        ),
    ]


def verify_tower_upgrade(result: dict[str, Any]) -> list[dict[str, Any]]:
    initial = result["deterministic_result"]["result"]["model_recommendation"]
    recalculated = result["deterministic_recalculation"]["result"]["model_recommendation"]
    orchestration = result.get("orchestration") or {}
    application = result.get("terminal_selection_application") or {}
    rule_id = "tower:semantic:vacuum_low_pressure_drop_structured_packing"
    return [
        check(
            initial.get("terminal_selection", {}).get("status") == "DEFAULTED_TERMINAL_TYPE_SELECTED",
            "initial_terminal_form_was_visible_default",
            initial.get("terminal_selection"),
        ),
        check(
            orchestration.get("verified_terminal_selection_override_id") == rule_id,
            "registered_terminal_rule_verified",
            orchestration.get("verified_terminal_selection_override_id"),
        ),
        check(
            application.get("applied_rule_id") == rule_id,
            "registered_terminal_rule_replayed",
            application,
        ),
        check(
            recalculated.get("terminal_selection", {}).get("status")
            == "CONDITIONED_TERMINAL_TYPE_SELECTED",
            "terminal_form_upgraded_by_condition",
            recalculated.get("terminal_selection"),
        ),
        check(
            initial.get("recommended_type") != recalculated.get("recommended_type"),
            "default_and_conditioned_forms_are_distinct",
            {
                "initial": initial.get("recommended_type"),
                "recalculated": recalculated.get("recommended_type"),
            },
        ),
    ]


def verify_tower_restraint(result: dict[str, Any]) -> list[dict[str, Any]]:
    initial = result["deterministic_result"]["result"]["model_recommendation"]
    orchestration = result.get("orchestration") or {}
    assessments = (orchestration.get("step_output") or {}).get("condition_assessments") or []
    return [
        check(
            initial.get("terminal_selection", {}).get("status") == "DEFAULTED_TERMINAL_TYPE_SELECTED",
            "default_remains_visible",
            initial.get("terminal_selection"),
        ),
        check(result.get("deterministic_recalculation") is None, "unsupported_upgrade_not_replayed", None),
        check(
            orchestration.get("verified_terminal_selection_overrides") == {},
            "no_unjustified_terminal_override",
            orchestration.get("verified_terminal_selection_overrides"),
        ),
        check(
            bool(assessments) and assessments[0].get("status") == "unknown",
            "incomplete_semantic_condition_retained_as_unknown",
            assessments,
        ),
    ]


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Luna Agent 模拟推理验收报告",
        "",
        f"- 总状态：`{report['status']}`",
        f"- 模拟模型 ID：`{report['model_id']}`",
        "- 调用方式：公开 Agent `hybrid_run`，`provider=mock`；未发送网络请求。",
        "- 权限边界：模型只选登记配方/条件，数值计算和终点形式复算仍由程序完成。",
        f"- Agent 进程：`{report['agent_process_mode']}`，PID `{report['agent_session_pid']}`",
        f"- 生成时间：`{report['generated_utc']}`",
        "",
        "| 案例 | 目的 | 结果 | 检查数 |",
        "| --- | --- | --- | ---: |",
    ]
    purposes = {
        "pump_registered_recipe": "从体积流量和密度选择登记配方，程序补算质量流量",
        "tower_registered_condition": "把有充分语义证据的默认塔型升级为登记条件塔型",
        "tower_incomplete_condition": "条件不完整时克制地保留默认，不强行改型",
    }
    for case in report["cases"]:
        lines.append(
            f"| `{case['case_id']}` | {purposes.get(case['case_id'], '')} | "
            f"`{case['status']}` | {len(case['checks'])} |"
        )
    lines.extend([
        "",
        "## 结论",
        "",
        (
            "该测试证明的是 Luna/小模型的受控接入协议和正常推理路径，不是一次真实远程 Luna 调用。"
            "模型作出的登记项选择必须通过本地严格校验，随后由程序重新计算；不充分条件不会覆盖默认结果。"
        ),
        "",
        "## 工件",
        "",
        "| 文件 | SHA-256 | 字节 |",
        "| --- | --- | ---: |",
    ])
    for artifact in report["artifacts"]:
        lines.append(
            f"| `{artifact['relative_path']}` | `{artifact['sha256']}` | {artifact['size_bytes']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Exercise realistic Luna-style equipment reasoning through the public Agent hybrid protocol."
    )
    parser.add_argument("--agent", type=Path, default=PACKAGE_ROOT / "app" / "equipment_design_agent.py")
    parser.add_argument("--working-dir", type=Path, default=PACKAGE_ROOT)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PACKAGE_ROOT / "outputs" / "luna_agent_simulation_20260719",
    )
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    agent = AgentProcess(args.agent, args.working_dir, timeout_s=300, persistent=True)
    cases: list[dict[str, Any]] = []
    try:
        cases.append(run_case(
            agent,
            case_id="pump_registered_recipe",
            source_input={
                "operation": "manual_match",
                "payload": {
                    "selection_id": "block:PUMP",
                    "values": {
                        "equipment_tag": "P-LUNA-SIM",
                        "phase": "liquid",
                        "flow_m3_h": 20,
                        "head_m": 45,
                        "density_kg_m3": 900,
                        "efficiency_percent": 75,
                    },
                },
            },
            knowledge={
                "enabled": True,
                "query": "pump mass flow volume flow density registered calculation recipe",
                "limit": 6,
            },
            injection_point="audit",
            response_builder=prepare_luna_pump,
            verifier=verify_pump,
        ))
        cases.append(run_case(
            agent,
            case_id="tower_registered_condition",
            source_input={
                "operation": "manual_match",
                "payload": {
                    "selection_id": "block:RADFRAC",
                    "values": {
                        "equipment_tag": "T-LUNA-SIM-1",
                        "aspen_block_type": "RADFRAC",
                        "process_function": (
                            "vacuum distillation; low pressure drop; clean non-fouling service"
                        ),
                    },
                },
            },
            knowledge={
                "enabled": True,
                "query": "tower vacuum low pressure drop clean service structured packing terminal rule",
                "limit": 6,
            },
            injection_point="textual_condition_judgment",
            response_builder=prepare_luna_tower_upgrade,
            verifier=verify_tower_upgrade,
        ))
        cases.append(run_case(
            agent,
            case_id="tower_incomplete_condition",
            source_input={
                "operation": "manual_match",
                "payload": {
                    "selection_id": "block:RADFRAC",
                    "values": {
                        "equipment_tag": "T-LUNA-SIM-2",
                        "aspen_block_type": "RADFRAC",
                        "process_function": "vacuum distillation service",
                    },
                },
            },
            knowledge={
                "enabled": True,
                "query": "tower vacuum service terminal equipment condition selection",
                "limit": 6,
            },
            injection_point="textual_condition_judgment",
            response_builder=prepare_luna_tower_restraint,
            verifier=verify_tower_restraint,
        ))
        session_pid = agent.session_pid
    finally:
        agent.close()

    case_paths: list[Path] = []
    for case in cases:
        path = output_dir / f"{case['case_id']}.json"
        write_json(path, case)
        case_paths.append(path)

    artifacts = [
        {
            "relative_path": path.relative_to(PACKAGE_ROOT).as_posix(),
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
        }
        for path in case_paths
    ]
    report = {
        "schema": "equipment-design-luna-agent-simulation-audit-v1",
        "status": "PASS" if cases and all(case["status"] == "PASS" for case in cases) else "FAIL",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "model_id": LUNA_MODEL_ID,
        "remote_network_call": False,
        "simulation_reason": (
            "No API credential is required for this protocol/behavior test; the public Agent mock provider "
            "injects realistic Luna-style structured outputs into the same strict continuation validator."
        ),
        "agent": str(args.agent.resolve()),
        "agent_process_mode": agent.process_mode,
        "agent_session_pid": session_pid,
        "case_count": len(cases),
        "check_count": sum(len(case["checks"]) for case in cases),
        "cases": [
            {
                key: value
                for key, value in case.items()
                if key != "hybrid_response"
            }
            for case in cases
        ],
        "artifacts": artifacts,
    }
    report_path = output_dir / "LUNA_AGENT_SIMULATION_AUDIT.json"
    write_json(report_path, report)
    markdown_path = output_dir / "LUNA_AGENT_SIMULATION_AUDIT.md"
    markdown_path.write_text(markdown_report(report), encoding="utf-8", newline="\n")
    print(json.dumps({
        "status": report["status"],
        "model_id": LUNA_MODEL_ID,
        "remote_network_call": False,
        "case_count": report["case_count"],
        "check_count": report["check_count"],
        "report_json": str(report_path),
        "report_markdown": str(markdown_path),
    }, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
