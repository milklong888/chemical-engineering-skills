from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from validate_agent_hybrid_protocol import AgentProcess, request  # noqa: E402


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def deterministic_result(item: dict[str, Any]) -> dict[str, Any]:
    result = item.get("result", {})
    return result if isinstance(result, dict) else {}


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# 无 LLM 设备设计验收报告",
        "",
        f"- 状态：`{report['status']}`",
        f"- Agent：`{report['agent']}`",
        f"- 工作目录：`{report['working_directory']}`",
        f"- Agent 进程模式：`{report['agent_process_mode']}`",
        f"- 检查数：{report['check_count']}",
        f"- 生成时间：{report['generated_utc']}",
        "- LLM/API Key/远程端点：未使用，子进程环境已清除相关变量",
        "",
        "| 检查 | 结果 | 说明 |",
        "| --- | --- | --- |",
    ]
    for item in report["checks"]:
        detail = json.dumps(item.get("detail"), ensure_ascii=False, sort_keys=True)
        if len(detail) > 240:
            detail = detail[:237] + "..."
        lines.append(f"| `{item['id']}` | {'PASS' if item['pass'] else 'FAIL'} | {detail.replace('|', '/')} |")
    lines.extend(["", "## 工件", "", "| 文件 | SHA-256 | 字节 |", "| --- | --- | ---: |"])
    for item in report["artifacts"]:
        lines.append(f"| `{item['relative_path']}` | `{item['sha256']}` | {item['size_bytes']} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the deterministic equipment-design acceptance flow with LLM disabled.")
    parser.add_argument("--agent", type=Path, default=PACKAGE_ROOT / "app" / "equipment_design_agent.py")
    parser.add_argument("--working-dir", type=Path, default=PACKAGE_ROOT)
    parser.add_argument("--output-dir", type=Path, default=PACKAGE_ROOT / "outputs" / "no_llm_release_acceptance")
    parser.add_argument("--gui-agent-entry", action="store_true", help="Use GUI EXE --agent-request/--agent-response file flags")
    parser.add_argument(
        "--one-process-per-request",
        action="store_true",
        help="Diagnostic baseline only; disable the default resident JSONL Agent session.",
    )
    parser.add_argument("--timeout-s", type=int, default=600)
    args = parser.parse_args()

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    runner = AgentProcess(
        args.agent,
        args.working_dir,
        timeout_s=args.timeout_s,
        persistent=not args.gui_agent_entry and not args.one_process_per_request,
    )
    checks: list[dict[str, Any]] = []
    artifact_paths: list[Path] = []

    def check(check_id: str, passed: bool, detail: Any) -> None:
        checks.append({"id": check_id, "pass": bool(passed), "detail": detail})

    def run_stdin(name: str, value: dict[str, Any]) -> tuple[dict[str, Any], int]:
        path = output_dir / f"{name}.json"
        if args.gui_agent_entry:
            request_path = output_dir / f"{name}_request.json"
            response, code = runner.call_file(
                value,
                request_path,
                path,
                gui_agent_entry=True,
            )
            artifact_paths.append(request_path)
        else:
            response, code = runner.call(value)
            path.write_text(
                json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
                newline="\n",
            )
        artifact_paths.append(path)
        return response, code

    capabilities, code = run_stdin("01_capabilities", request("capabilities", request_id="ACCEPT-CAPS"))
    capability_result = capabilities.get("result", {})
    check("capabilities", code == 0 and capabilities.get("ok") is True, capabilities.get("engine"))
    runtime_status = capability_result.get("runtime_bundle", {})
    is_packaged_agent = args.agent.suffix.casefold() == ".exe"
    check(
        "runtime_bundle",
        isinstance(runtime_status, dict)
        and runtime_status.get("verified") is True
        and (
            runtime_status.get("verification_status") == "PASS"
            if is_packaged_agent
            else runtime_status.get("verification_status") == "NOT_APPLICABLE_SOURCE_TREE"
        )
        and (
            bool(runtime_status.get("bundle_revision"))
            and bool(runtime_status.get("manifest_sha256"))
            if is_packaged_agent
            else runtime_status.get("bundle_revision") is None
            and runtime_status.get("manifest_sha256") is None
        ),
        runtime_status,
    )
    schema_registry = capability_result.get("schemas", [])
    required_schema_ids = {
        "equipment-design-agent-request-v1",
        "equipment-design-agent-response-v1",
        "equipment-design-presentation-v1",
        "equipment-design-report-status-v1",
        "equipment-design-llm-context-pack-v1",
        "equipment-design-llm-step-output-v1",
        "equipment-design-llm-prepared-v1",
        "equipment-design-app-llm-orchestration-v1",
        "equipment-design-hybrid-result-v2",
        "equipment-design-authority-revision-v1",
        "equipment-design-source-code-manifest-v1",
        "equipment-design-parameter-package-v1",
        "equipment-design-pfd-mapping-v1",
        "equipment-customer-output-profiles-v1",
        "equipment-customer-delivery-bundle-v1",
        "equipment-overview-table-v1",
        "equipment-family-datasheet-v1",
        "equipment-evidence-index-v1",
    }
    actual_schema_ids = {
        item.get("schema_id")
        for item in schema_registry
        if isinstance(item, dict) and isinstance(item.get("schema_id"), str)
    }
    check(
        "schema_registry",
        isinstance(schema_registry, list)
        and required_schema_ids <= actual_schema_ids
        and len({item.get("schema_id") for item in schema_registry if isinstance(item, dict)}) == len(schema_registry)
        and all(
            isinstance(item, dict)
            and len(str(item.get("sha256", ""))) == 64
            and int(item.get("size_bytes", 0)) > 0
            for item in schema_registry
        ),
        {
            "schema_count": len(schema_registry),
            "missing_required": sorted(required_schema_ids - actual_schema_ids),
        },
    )

    schema_response, code = run_stdin(
        "02_parameter_package_schema",
        request("schema_get", {"schema_id": "equipment-design-parameter-package-v1"}, "ACCEPT-SCHEMA"),
    )
    check(
        "schema_get",
        code == 0
        and schema_response.get("result", {}).get("document", {}).get("$id") == "equipment-design-parameter-package-v1",
        schema_response.get("result", {}).get("sha256"),
    )

    pfd_source = PACKAGE_ROOT / "data" / "aspen_equipment_export_sample.json"
    pfd_source_sha = sha256_file(pfd_source)
    pfd_response, code = run_stdin(
        "02b_pfd_build",
        request(
            "pfd_build",
            {"bundle_path": str(pfd_source.resolve()), "overrides": {}},
            "ACCEPT-PFD-BUILD",
        ),
    )
    pfd_result = pfd_response.get("result", {})
    pfd_summary = pfd_result.get("summary", {})
    pfd_mapping = pfd_result.get("mapping", {})
    check(
        "pfd_topology_and_mapping",
        code == 0
        and pfd_mapping.get("schema") == "equipment-design-pfd-mapping-v1"
        and pfd_summary.get("topology_gate", {}).get("status") == "PASS"
        and pfd_summary.get("equipment_node_count") == 1
        and pfd_summary.get("edge_count") == 2
        and pfd_summary.get("default_display_level") == "standard"
        and pfd_summary.get("model_promotion_allowed") is False
        and pfd_result.get("mapping_sha256") == pfd_summary.get("mapping_sha256")
        and sha256_file(pfd_source) == pfd_source_sha,
        {
            "mapping_sha256": pfd_result.get("mapping_sha256"),
            "topology_gate": pfd_summary.get("topology_gate"),
            "mapping_status_counts": pfd_summary.get("mapping_status_counts"),
        },
    )

    pfd_override, code = run_stdin(
        "02c_pfd_override",
        request(
            "pfd_override",
            {
                "bundle_path": str(pfd_source.resolve()),
                "overrides": {},
                "block_id": "P-101",
                "selection_id": "block:VALVE",
            },
            "ACCEPT-PFD-OVERRIDE",
        ),
    )
    override_result = pfd_override.get("result", {})
    override_blocks = override_result.get("mapping", {}).get("blocks", [])
    override_block = override_blocks[0] if override_blocks else {}
    check(
        "pfd_override_isolated_and_stale_propagated",
        code == 0
        and override_result.get("overrides") == {"P-101": "block:VALVE"}
        and override_block.get("automatic_mapping", {}).get("selection_id") == "block:PUMP"
        and override_block.get("effective_mapping", {}).get("selection_id") == "block:VALVE"
        and override_block.get("recalculation_status") == "TYPE_CHANGED_PENDING_RECALC"
        and override_result.get("summary", {}).get("model_promotion_allowed") is False
        and override_result.get("source_mutated") is False
        and sha256_file(pfd_source) == pfd_source_sha,
        {
            "automatic": override_block.get("automatic_mapping", {}).get("selection_id"),
            "effective": override_block.get("effective_mapping", {}).get("selection_id"),
            "recalculation_status": override_block.get("recalculation_status"),
        },
    )

    pfd_recalculation, code = run_stdin(
        "02d_pfd_recalculate",
        request(
            "pfd_recalculate",
            {
                "bundle_path": str(pfd_source.resolve()),
                "overrides": {},
                "parameter_overrides": {},
                "block_id": "P-101",
                "values": {
                    "required_npsh_margin_m": 0.5,
                    "npsha_m": 3.0,
                    "npshr_m": 2.0,
                },
            },
            "ACCEPT-PFD-RECALCULATE",
        ),
    )
    recalc_result = pfd_recalculation.get("result", {})
    recalc_blocks = recalc_result.get("mapping", {}).get("blocks", [])
    recalc_block = next(
        (
            item for item in recalc_blocks
            if isinstance(item, dict) and item.get("block_id") == "P-101"
        ),
        {},
    )
    recalc_edges = recalc_result.get("mapping", {}).get("pfd", {}).get("edges", [])
    check(
        "pfd_parameter_recalculation_isolated_and_stale_propagated",
        code == 0
        and recalc_result.get("schema") == "equipment-design-agent-pfd-recalculation-result-v1"
        and recalc_result.get("parameter_overrides", {}).get("P-101", {}).get("required_npsh_margin_m") == 0.5
        and recalc_result.get("merged_match_input", {}).get("npsha_m") == 3.0
        and recalc_result.get("deterministic_recalculation", {}).get("schema") == "equipment-design-app-manual-result-v1"
        and recalc_block.get("recalculation_status") == "RECALCULATED_CURRENT"
        and bool(recalc_edges)
        and all(
            edge.get("recalculation_status") == "RELATED_STREAM_PENDING_RECALC"
            for edge in recalc_edges
            if isinstance(edge, dict)
        )
        and recalc_result.get("source_mutated") is False
        and recalc_result.get("llm_used") is False
        and sha256_file(pfd_source) == pfd_source_sha,
        {
            "recalculation_status": recalc_block.get("recalculation_status"),
            "edge_statuses": sorted({
                str(edge.get("recalculation_status"))
                for edge in recalc_edges if isinstance(edge, dict)
            }),
            "formal_evidence_status": recalc_result.get("formal_evidence_status"),
        },
    )

    pfd_recalculation_clear, code = run_stdin(
        "02e_pfd_recalculate_clear",
        request(
            "aspen.pfd.recalculate",
            {
                "bundle_path": str(pfd_source.resolve()),
                "overrides": {},
                "parameter_overrides": recalc_result.get("parameter_overrides", {}),
                "block_id": "P-101",
                "clear": True,
            },
            "ACCEPT-PFD-RECALCULATE-CLEAR",
        ),
    )
    clear_result = pfd_recalculation_clear.get("result", {})
    check(
        "pfd_parameter_clear_restores_aspen_layer",
        code == 0
        and clear_result.get("action") == "CLEAR_BLOCK_PARAMETER_OVERRIDES"
        and clear_result.get("parameter_overrides") == {}
        and "required_npsh_margin_m" not in clear_result.get("merged_match_input", {})
        and clear_result.get("source_mutated") is False
        and sha256_file(pfd_source) == pfd_source_sha,
        {
            "action": clear_result.get("action"),
            "parameter_overrides": clear_result.get("parameter_overrides"),
        },
    )

    selftest, code = run_stdin("03_selftest", request("selftest", request_id="ACCEPT-SELFTEST"))
    selftest_result = selftest.get("result") or {}
    check(
        "selftest",
        code == 0 and selftest_result.get("status") == "PASS" and int(selftest_result.get("check_count", 0)) >= 12,
        {"status": selftest_result.get("status"), "check_count": selftest_result.get("check_count")},
    )

    partial_request = load_json(PACKAGE_ROOT / "app" / "fixtures" / "agent_partial_flow_request.json")
    partial_request["request_id"] = "ACCEPT-PARTIAL"
    partial, code = run_stdin("04_partial_one_field", partial_request)
    partial_inner = deterministic_result(partial.get("result", {}))
    progress = partial_inner.get("progress", {})
    check(
        "one_field_candidate_generation",
        code == 0
        and progress.get("candidate_count", 0) >= 1
        and progress.get("state") == "NEEDS_IDENTITY",
        {"state": progress.get("state"), "candidate_count": progress.get("candidate_count")},
    )

    pump_request = load_json(PACKAGE_ROOT / "app" / "fixtures" / "agent_manual_pump_request.json")
    pump_request["request_id"] = "ACCEPT-PUMP-FILE"
    pump_response_path = output_dir / "05_manual_pump_file_response.json"
    pump, code = runner.call_file(
        pump_request,
        output_dir / "05_manual_pump_file_request.json",
        pump_response_path,
        gui_agent_entry=bool(args.gui_agent_entry),
    )
    artifact_paths.extend([output_dir / "05_manual_pump_file_request.json", pump_response_path])
    pump_inner = deterministic_result(pump.get("result", {}))
    targets = {item.get("target_field") for item in pump_inner.get("calculations", [])}
    leading = pump_inner.get("model_recommendation", {}).get("leading_candidate", {})
    check(
        "manual_pump_calculate_then_select",
        code == 0
        and {"head_m", "hydraulic_power_kw", "shaft_power_kw"} <= targets
        and bool(leading.get("designation"))
        and pump_inner.get("model_recommendation", {}).get("selection_execution", {}).get("context_sha256")
        == pump_inner.get("design_parameter_package", {}).get("selection_context", {}).get("sha256"),
        {"targets": sorted(target for target in targets if target), "designation": leading.get("designation")},
    )

    customer_export_request = request(
        "customer_export",
        {
            "input": {
                "operation": "manual_match",
                "payload": pump_request["payload"],
            }
        },
        "ACCEPT-CUSTOMER-EXPORT",
    )
    customer_export, code = run_stdin("05b_customer_delivery", customer_export_request)
    customer_bundle = customer_export.get("result", {}).get("customer_delivery", {})
    customer_overview = customer_bundle.get("equipment_overview_table", {})
    customer_datasheet = customer_bundle.get("equipment_family_datasheet", {})
    customer_evidence = customer_bundle.get("equipment_evidence_index", {})
    overview_rows = customer_overview.get("rows", [])
    datasheet_equipment = customer_datasheet.get("equipment", [])
    first_datasheet_fields = datasheet_equipment[0].get("fields", []) if datasheet_equipment else []
    first_datasheet_ids = {
        item.get("field_id") for item in first_datasheet_fields if isinstance(item, dict)
    }
    formula_fields = [
        item
        for item in first_datasheet_fields
        if isinstance(item, dict) and isinstance(item.get("formula_chain"), dict)
    ]
    check(
        "authoritative_customer_delivery",
        code == 0
        and customer_bundle.get("schema") == "equipment-customer-delivery-bundle-v1"
        and customer_bundle.get("deterministic") is True
        and customer_bundle.get("llm_used") is False
        and customer_overview.get("schema") == "equipment-overview-table-v1"
        and customer_overview.get("row_count") == 1
        and bool(overview_rows)
        and bool(overview_rows[0].get("model_or_specification"))
        and bool(overview_rows[0].get("model_or_specification_status"))
        and isinstance(overview_rows[0].get("customer_table_missing_fields"), list)
        and isinstance(overview_rows[0].get("algorithm_evidence_missing_fields"), list)
        and isinstance(overview_rows[0].get("missing_information"), list)
        and customer_datasheet.get("schema") == "equipment-family-datasheet-v1"
        and customer_datasheet.get("equipment_count") == 1
        and {"model_designation", "model_status", "pending_evidence", "head_m"} <= first_datasheet_ids
        and all(
            all(chain.get(key) for key in ("target", "formula", "substitution", "answer"))
            for chain in (item["formula_chain"] for item in formula_fields)
        )
        and customer_evidence.get("schema") == "equipment-evidence-index-v1"
        and int(customer_evidence.get("record_count", 0)) >= 1,
        {
            "bundle_schema": customer_bundle.get("schema"),
            "overview_rows": customer_overview.get("row_count"),
            "datasheet_fields": len(first_datasheet_fields),
            "evidence_records": customer_evidence.get("record_count"),
            "model": overview_rows[0].get("model_or_specification") if overview_rows else None,
        },
    )

    aspen_output = output_dir / "06_aspen_derived_result.json"
    aspen_request = request(
        "aspen_derive",
        {
            "export_path": str((PACKAGE_ROOT / "data" / "aspen_equipment_export_sample.json").resolve()),
            "output_path": str(aspen_output),
            "require_clean": True,
        },
        "ACCEPT-ASPEN",
    )
    aspen, code = run_stdin("06_aspen_derive_response", aspen_request)
    if aspen_output.is_file():
        artifact_paths.append(aspen_output)
    aspen_result = aspen.get("result", {})
    piping = aspen_result.get("piping", []) if isinstance(aspen_result.get("piping"), list) else []
    check(
        "aspen_export_derivation",
        code == 0
        and aspen_result.get("formal_use_gate") == "ELIGIBLE_AS_PROCESS_BASIS"
        and aspen_result.get("llm_used") is False
        and int(aspen_result.get("piping_count", 0)) == len(piping)
        and len(piping) >= 1
        and all(
            isinstance(item.get("pfd_edge_label_data"), dict)
            and isinstance(item.get("pfd_edge_label_data", {}).get("compact_label"), dict)
            and len(item.get("pfd_edge_label_data", {}).get("compact_label", {}).get("key_values", {})) <= 3
            and isinstance(item.get("pfd_edge_label_data", {}).get("details"), dict)
            for item in piping
            if isinstance(item, dict)
        ),
        {
            "formal_use_gate": aspen_result.get("formal_use_gate"),
            "equipment_count": aspen_result.get("equipment_count"),
            "piping_count": aspen_result.get("piping_count"),
        },
    )

    meaningful_fixture = load_json(
        PACKAGE_ROOT / "app" / "fixtures" / "all_family_minimum_meaningful_inputs.json"
    )
    meaningful_cases = meaningful_fixture.get("cases", [])
    family_request = request(
        "auto_match",
        {
            "records": [
                {
                    "equipment_family": case["family_id"],
                    **case["values"],
                }
                for case in meaningful_cases
            ]
        },
        "ACCEPT-17-FAMILIES",
    )
    families, code = run_stdin("07_all_17_families_meaningful", family_request)
    family_items = families.get("result", {}).get("items", [])
    family_results = [deterministic_result(item) for item in family_items]
    family_rows = []
    for case, result in zip(meaningful_cases, family_results):
        actual_calculations = [
            item.get("calculation_id")
            for item in result.get("calculations", [])
            if isinstance(item, dict)
        ]
        recommendation = result.get("model_recommendation", {})
        leading_candidate = recommendation.get("leading_candidate") or {}
        family_rows.append({
            "family_id": case.get("family_id"),
            "matched_family_id": result.get("match", {}).get("family_id"),
            "expected_calculation_ids": case.get("expected_calculation_ids", []),
            "actual_calculation_ids": actual_calculations,
            "parameter_package_status": result.get("design_parameter_package", {}).get("status"),
            "selection_execution": recommendation.get("selection_execution", {}).get("status"),
            "candidate_kind": leading_candidate.get("candidate_kind"),
            "candidate_status": leading_candidate.get("status"),
            "candidate_selection_executed": result.get("model_decision", {}).get("candidate_selection_executed"),
        })
    total_calculations = sum(len(row["actual_calculation_ids"]) for row in family_rows)
    check(
        "all_17_family_meaningful_calculate_then_select",
        code == 0
        and len(meaningful_cases) == meaningful_fixture.get("expected_family_count") == 17
        and len(family_results) == 17
        and total_calculations == meaningful_fixture.get("expected_total_calculation_count")
        and all(
            row["matched_family_id"] == row["family_id"]
            and row["actual_calculation_ids"] == row["expected_calculation_ids"]
            and row["parameter_package_status"] == "READY_FOR_CANDIDATE_MATCHING"
            and row["selection_execution"] == "EXECUTED"
            and row["candidate_selection_executed"] is True
            and row["candidate_kind"] == case.get("expected_candidate_kind")
            and not str(row["candidate_status"] or "").startswith("PARTIAL_")
            for case, row in zip(meaningful_cases, family_rows)
        ),
        {
            "family_count": len(family_results),
            "total_calculations": total_calculations,
            "rows": family_rows,
            "zero_formula_families": [
                row["family_id"] for row in family_rows if not row["actual_calculation_ids"]
            ],
        },
    )

    family_only_request = load_json(
        PACKAGE_ROOT / "app" / "fixtures" / "agent_all_family_model_candidates_request.json"
    )
    family_only_request["request_id"] = "ACCEPT-17-FAMILY-ONLY-DEFAULTS"
    family_only, code = run_stdin("07b_all_17_family_only_defaults", family_only_request)
    family_only_items = family_only.get("result", {}).get("items", [])
    family_only_results = [deterministic_result(item) for item in family_only_items]
    check(
        "family_only_defaults_reach_visible_preliminary_selection",
        code == 0
        and len(family_only_results) == 17
        and all(
            result.get("model_recommendation", {}).get("selection_execution", {}).get("status")
            == "EXECUTED"
            and result.get("model_decision", {}).get("candidate_selection_executed") is True
            and result.get("model_decision", {}).get("generated_candidate_designation")
            and result.get("model_recommendation", {}).get("recommended_type")
            and result.get("model_recommendation", {}).get("terminal_selection", {}).get("provisional") is True
            and result.get("model_recommendation", {}).get("terminal_selection", {}).get("default_applied") is True
            and result.get("design_fallbacks")
            and result.get("model_decision", {}).get("formal_ready_candidate_count") == 0
            for result in family_only_results
        ),
        {
            "family_count": len(family_only_results),
            "executed_count": sum(
                1 for result in family_only_results
                if result.get("model_recommendation", {}).get("selection_execution", {}).get("status") == "EXECUTED"
            ),
            "generated_designation_count": sum(
                1 for result in family_only_results
                if result.get("model_decision", {}).get("generated_candidate_designation")
            ),
            "formal_ready_count": sum(
                int(result.get("model_decision", {}).get("formal_ready_candidate_count") or 0)
                for result in family_only_results
            ),
        },
    )

    representative_request = load_json(PACKAGE_ROOT / "app" / "fixtures" / "agent_representative_parameter_chain_request.json")
    representative_request["request_id"] = "ACCEPT-REPRESENTATIVE"
    representative, code = run_stdin("08_representative_parameter_chains", representative_request)
    representative_items = representative.get("result", {}).get("items", [])
    representative_results = [deterministic_result(item) for item in representative_items]
    check(
        "representative_parameter_chains",
        code == 0
        and len(representative_results) == 5
        and all(result.get("design_parameter_package", {}).get("groups") for result in representative_results)
        and all(
            all(
                all(item.get("formula_chain", {}).get(key) for key in ("target", "formula", "substitution", "answer"))
                for item in result.get("calculations", [])
            )
            for result in representative_results
        ),
        {"equipment_count": len(representative_results)},
    )

    representative_source = representative_request["payload"]
    html_path = output_dir / "09_representative_parameter_report.html"
    render_request = request(
        "render_report",
        {
            "input": {"operation": "manual_batch", "payload": representative_source},
            "format": "html",
            "output_path": str(html_path),
        },
        "ACCEPT-REPORT",
    )
    rendered, code = run_stdin("09_render_report_response", render_request)
    if html_path.is_file():
        artifact_paths.append(html_path)
    html_text = html_path.read_text(encoding="utf-8") if html_path.is_file() else ""
    check(
        "engineering_report",
        code == 0
        and rendered.get("result", {}).get("presentation", {}).get("equipment_count") == 5
        and "目标量 = 公式 = 代入式 = 答案" in html_text
        and "客户表缺项" in html_text
        and "算法 / 证据门缺项" in html_text
        and "eq-answer" in html_text
        and "hydraulic_power_kw = hydraulic_power_kw" not in html_text,
        {"path": str(html_path), "size_bytes": len(html_text.encode("utf-8"))},
    )

    knowledge_queries = {
        "equipment_core": "泵 轴功率 公式 证据门",
        "equipment_model_authority": "泵 型号 GB/T 5662",
        "design_standards": "塔式容器 固定管板 标准",
    }
    knowledge_details: dict[str, Any] = {}
    knowledge_ok = True
    for index, (package_id, query_text) in enumerate(knowledge_queries.items(), 1):
        knowledge, code = run_stdin(
            f"10_{index}_{package_id}_search",
            request(
                "knowledge_search",
                {"query": query_text, "limit": 10, "package_ids": [package_id]},
                f"ACCEPT-KG-{index}",
            ),
        )
        knowledge_result = knowledge.get("result", {})
        hits = knowledge_result.get("hits", [])
        package_ok = (
            code == 0
            and int(knowledge_result.get("result_count", len(hits))) >= 1
            and isinstance(hits, list)
            and all(hit.get("package_id") == package_id for hit in hits if isinstance(hit, dict))
        )
        knowledge_ok = knowledge_ok and package_ok
        knowledge_details[package_id] = {
            "pass": package_ok,
            "status": knowledge_result.get("status"),
            "mode": knowledge_result.get("mode"),
            "hits": len(hits) if isinstance(hits, list) else 0,
        }
    check("knowledge_graph_packages_queryable", knowledge_ok, knowledge_details)

    hybrid, code = run_stdin(
        "11_no_llm_hybrid",
        request(
            "hybrid_run",
            {
                "input": {"operation": "manual_match", "payload": pump_request["payload"]},
                "knowledge": {"enabled": False},
                "injection_point": "audit",
                "context_scope": "minimum",
                "llm": {"enabled": False},
            },
            "ACCEPT-HYBRID",
        ),
    )
    hybrid_result = hybrid.get("result", {})
    authority_revision = hybrid_result.get("prepared", {}).get("authority_revision", {})
    authority_runtime = authority_revision.get("runtime_manifest", {})
    authority_source = authority_revision.get("source_code_manifest", {})
    authority_core_assets = authority_revision.get("core_asset_sha256", {})
    authority_schema_assets = authority_revision.get("schema_asset_sha256", {})
    authority_source_assets = authority_revision.get("source_code_sha256", {})
    runtime_source = runtime_status.get("source_code_manifest", {})
    expected_core_asset_ids = {
        "rules",
        "model_rules",
        "parameter_templates",
        "customer_output_profiles",
        "pump_standard_points",
        "pipe_standard_dn_od",
        "equipment_selection_graph",
    }
    source_file_count = authority_source.get("file_count")
    revision_payload = {
        key: value
        for key, value in authority_revision.items()
        if key != "authority_revision_sha256"
    }
    check(
        "no_llm_hybrid_v2",
        code == 0
        and hybrid_result.get("schema") == "equipment-design-hybrid-result-v2"
        and hybrid_result.get("machine_state", {}).get("state") == "COMPLETED_DETERMINISTIC_ONLY"
        and hybrid_result.get("machine_state", {}).get("deterministic_result_preserved") is True,
        hybrid_result.get("machine_state"),
    )
    check(
        "authority_revision_bound",
        authority_revision.get("schema") == "equipment-design-authority-revision-v1"
        and isinstance(authority_core_assets, dict)
        and set(authority_core_assets) == expected_core_asset_ids
        and all(len(str(value)) == 64 for value in authority_core_assets.values())
        and authority_revision.get("core_asset_set_sha256") == canonical_sha256(authority_core_assets)
        and isinstance(authority_schema_assets, dict)
        and bool(authority_schema_assets)
        and all(
            str(path).startswith("app/schemas/")
            and str(path).endswith(".json")
            and len(str(digest)) == 64
            for path, digest in authority_schema_assets.items()
        )
        and authority_revision.get("schema_asset_set_sha256") == canonical_sha256(authority_schema_assets)
        and isinstance(authority_source_assets, dict)
        and isinstance(source_file_count, int)
        and not isinstance(source_file_count, bool)
        and source_file_count > 0
        and len(authority_source_assets) == source_file_count
        and all(len(str(value)) == 64 for value in authority_source_assets.values())
        and authority_revision.get("source_code_set_sha256") == canonical_sha256(authority_source_assets)
        and len(str(authority_source.get("manifest_sha256", ""))) == 64
        and authority_source.get("status") == (
            "PACKAGED_SNAPSHOT_VERIFIED"
            if is_packaged_agent
            else "SOURCE_TREE_VERIFIED"
        )
        and runtime_source.get("verified") is True
        and runtime_source.get("file_count") == source_file_count
        and runtime_source.get("source_code_sha256") == authority_source_assets
        and runtime_source.get("source_code_set_sha256")
        == authority_revision.get("source_code_set_sha256")
        and runtime_source.get("manifest_sha256") == authority_source.get("manifest_sha256")
        and runtime_source.get("manifest_payload_sha256")
        == authority_source.get("manifest_payload_sha256")
        and runtime_source.get("path_set_sha256") == authority_source.get("path_set_sha256")
        and len(str(authority_revision.get("authority_revision_sha256", ""))) == 64
        and authority_revision.get("authority_revision_sha256") == canonical_sha256(revision_payload)
        and (
            authority_runtime.get("status") == "PACKAGED"
            and authority_runtime.get("manifest_sha256") == runtime_status.get("manifest_sha256")
            and authority_runtime.get("bundle_revision") == runtime_status.get("bundle_revision")
            if is_packaged_agent
            else authority_runtime.get("status") == "NOT_PACKAGED"
        ),
        {
            "authority_revision_sha256": authority_revision.get("authority_revision_sha256"),
            "schema_asset_count": len(authority_schema_assets),
            "source_code_file_count": len(authority_source_assets),
            "source_code_manifest": authority_source,
            "runtime_source_code_manifest": runtime_source,
            "runtime_manifest": authority_runtime,
        },
    )

    unique_artifacts = sorted({path.resolve() for path in artifact_paths if path.is_file()}, key=lambda path: path.as_posix())
    artifacts = [
        {
            "relative_path": path.relative_to(output_dir).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in unique_artifacts
    ]
    status = "PASS" if checks and all(item["pass"] for item in checks) else "FAIL"
    report = {
        "schema": "equipment-design-no-llm-acceptance-v1",
        "status": status,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "agent": str(args.agent.expanduser().resolve()),
        "working_directory": str(args.working_dir.expanduser().resolve()),
        "gui_agent_entry": bool(args.gui_agent_entry),
        "agent_process_mode": runner.process_mode,
        "resident_session_pid": runner.session_pid,
        "llm_environment_removed": True,
        "check_count": len(checks),
        "checks": checks,
        "artifacts": artifacts,
    }
    report_json = output_dir / "NO_LLM_ACCEPTANCE_REPORT.json"
    report_md = output_dir / "NO_LLM_ACCEPTANCE_REPORT.md"
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    report_md.write_text(markdown_report(report), encoding="utf-8", newline="\n")
    runner.close()
    print(json.dumps({
        "status": status,
        "checks": len(checks),
        "report_json": str(report_json),
        "report_md": str(report_md),
    }, ensure_ascii=False, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
