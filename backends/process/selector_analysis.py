"""Preserved selector feedback analysis from the reviewed local bridge.

Transport moved to the packaged backend; numerical/diagnostic functions remain.
The extension in feedback.py owns new series/parallel plans and replay gates.
"""
from __future__ import annotations
import hashlib
import json
import math
from typing import Any
PHYSICAL_CHECKS = {"pump_npsh_margin", "compressor_surge_margin", "storage_required_volume"}

def canonical_sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest().upper()

def equipment_records(result: Any, pointer: str = "/result"):
    """Locate upstream physical records, preserving their wrapper and JSON pointer."""
    if not isinstance(result, dict):
        return
    if isinstance(result.get("result"), dict) and ("model_decision" in result["result"] or result.get("schema") == "equipment-design-app-manual-result-v1"):
        yield pointer, result, result["result"]
        return
    if isinstance(result.get("match_result"), dict):
        yield pointer, result, result["match_result"]
        return
    if "model_decision" in result:
        yield pointer, result, result
        return
    for key in ("items", "equipment", "piping"):
        collection = result.get(key)
        if isinstance(collection, list):
            for index, child in enumerate(collection):
                yield from equipment_records(child, f"{pointer}/{key}/{index}")


def pick_rules(value: Any) -> list[str]:
    rules: set[str] = set()
    def visit(node: Any) -> None:
        if isinstance(node, dict):
            for key, item in node.items():
                if key == "terminal_selection" and isinstance(item, dict) and item.get("rule_id"):
                    rules.add(str(item["rule_id"]))
                if key in {"terminal_rule_id", "selected_terminal_rule_id", "terminal_selection_rule_id"} and isinstance(item, str):
                    rules.add(item)
                elif key in {"terminal_rule_ids", "selected_terminal_rule_ids"} and isinstance(item, list):
                    rules.update(str(entry) for entry in item)
                visit(item)
        elif isinstance(node, list):
            for item in node:
                visit(item)
    visit(value)
    return sorted(rules)


def feedback_record(pointer: str, wrapper: dict, core: dict, context: dict) -> dict:
    package = core.get("design_parameter_package", {})
    decision = core.get("model_decision", {})
    recommendation = core.get("model_recommendation", {})
    plan = core.get("engineering_adjustment_plan", {})
    direct = wrapper.get("input", core.get("normalized_input", {}))
    effective = package.get("selection_context", {}).get("values", {})
    values = {**direct, **effective}
    tag = str(values.get("equipment_tag") or wrapper.get("equipment_tag") or wrapper.get("equipment_id") or wrapper.get("aspen_block_id") or wrapper.get("block_id") or wrapper.get("stream_id") or core.get("equipment_tag") or pointer)
    family = core.get("match", {}).get("family_id") or package.get("family_id")
    if (core.get("status_reason") == "NOT_APPLICABLE_SIMULATION_LOGIC_NODE"
            and str(core.get("match", {}).get("aspen_block_type", "")).upper() in {"FSPLIT", "MIXER", "HIERARCHY"}):
        return {"equipment_id": tag, "family_id": None, "physical_equipment": False,
            "primary_feedback_category": "not_applicable_simulation_logic_node", "feedback_categories": [],
            "raw_response_json_pointer": pointer, "raw_equipment_record_sha256": canonical_sha(wrapper),
            "original_upstream_fields": wrapper, "candidates_for_flowsheet_revision": [],
            "final_equipment_model": None, "terminal_rule_ids": [],
            "boundary": "Exact upstream simulation topology identity retained; no independent device inferred."}
    findings = []
    def add(category: str, code: str, evidence: Any) -> None:
        findings.append({"category": category, "code": code, "evidence": evidence})

    if str(core.get("status", "")).startswith("INVALID"):
        add("basis_invalid", "UPSTREAM_INVALID_INPUT", {"status": core.get("status"), "errors": core.get("errors", [])})
    if not family:
        add("coverage_gap", "NO_IDENTIFIED_EQUIPMENT_FAMILY", {"status": core.get("status"), "match": core.get("match")})

    # Missing inputs, source provenance and standards coverage are different axes.
    pending = core.get("calculation_pending", [])
    invalid_pending = [row for row in pending if any(word in str(row.get("status", "")) for word in ("INVALID", "ERROR", "INCOMPATIBLE"))]
    phase = package.get("phase_compatibility", {})
    if invalid_pending or phase.get("status") == "BLOCKED_INCOMPATIBLE_PHASE":
        add("basis_invalid", "UPSTREAM_INVALID_BASIS", {"pending": invalid_pending, "phase": phase})
    # Pressure direction is an identity invariant, not an invented capacity limit.
    pin, pout = values.get("inlet_pressure_mpa"), values.get("outlet_pressure_mpa")
    expected_duty = context.get("expected_duty", {}).get(tag)
    try:
        comparable = all(isinstance(v, (float, int)) and not isinstance(v, bool) and math.isfinite(v) for v in (pin, pout))
        if comparable and (family in {"family_pump", "family_compressor"} or expected_duty in {"compression", "liquid_pressure_rise"}) and pout <= pin:
            add("basis_invalid", "PRESSURE_RISE_DIRECTION_INVALID", {"inlet_pressure_mpa": pin, "outlet_pressure_mpa": pout, "pressure_basis": values.get("pressure_basis"), "caller_declared_duty": expected_duty, "upstream_selected_family": family, "rule": "A pressure-raising equipment duty requires outlet pressure greater than inlet pressure on one basis. Generic Aspen COMPR alone can also represent expansion."})
    except TypeError:
        pass
    checks = package.get("constraint_checks", [])
    for check in checks:
        if check.get("check_id") in PHYSICAL_CHECKS and check.get("status") == "FAIL":
            add("physical_or_capacity_conflict", str(check["check_id"]), check)
    missing = sorted({str(field) for row in pending for field in row.get("missing_fields", [])}
                     | set(map(str, decision.get("sizing_missing_fields", []))))
    if missing:
        add("evidence_gap", "REQUIRED_INPUTS_MISSING", missing)
    if decision.get("model_status") != "final_model":
        add("evidence_gap", "FORMAL_EQUIPMENT_EVIDENCE_OPEN", {"model_status": decision.get("model_status"), "verification_missing_fields": decision.get("verification_missing_fields", []), "machine_evidence_manifest": decision.get("machine_evidence_manifest", {})})
    for code in plan.get("trigger_codes", []):
        if "COVERAGE" in code or "CATALOG" in code:
            add("coverage_gap", code, plan.get("screening_policy", {}))
    compressor_capability = None
    staged_requested = "staged_compression" in context.get("screening_requests", {}).get(tag, [])
    basis_invalid = any(f["category"] == "basis_invalid" for f in findings)
    physical_conflict = any(f["category"] == "physical_or_capacity_conflict" for f in findings)
    staged_review = family == "family_compressor" and not basis_invalid and (staged_requested or physical_conflict)
    if family == "family_compressor":
        compressor_capability = {"status": "staged_compression_capability_not_implemented", "automatic_stage_count_supported": False,
            "pressure_ratio": core.get("derived_parameters", {}).get("compression_pressure_ratio"),
            "pressure_ratio_source_field": "derived_parameters.compression_pressure_ratio",
            "rule": "No universal stage pressure-ratio limit is assumed. Screen same-gas temperature, phase, power, efficiency, interstage losses and vendor maps before proposing stage count."}
        if staged_review:
            add("coverage_gap", "staged_compression_screening_required", {**compressor_capability, "explicit_screening_requested": staged_requested})
    if recommendation.get("leading_candidate") or recommendation.get("recommended_type"):
        add("preliminary_candidate", "UPSTREAM_SELECTION_RETAINED", {"status": recommendation.get("status"), "recommended_type": recommendation.get("recommended_type"), "leading_candidate": recommendation.get("leading_candidate")})
    configuration = plan.get("configuration", {})
    catalog_distance_only = (family == "family_pump" and plan.get("triggered") is True
        and not physical_conflict and bool(configuration.get("reference_fit"))
        and configuration.get("operating_unit_count_estimate", 1) > 1)
    if catalog_distance_only:
        add("coverage_gap", "catalog_distance_only", {"reference_fit": configuration["reference_fit"],
            "complexity_status": "complexity_not_justified",
            "reason": "Improving distance to sparse reference catalogue points is not evidence that the original duty exceeds single-unit capability or that more units improve the whole system."})
    if not findings:
        add("coverage_gap", "NO_RECOGNIZED_DECISION_EVIDENCE", {"upstream_status": core.get("status")})
    categories = list(dict.fromkeys(item["category"] for item in findings))
    primary = next((category for category in ("basis_invalid", "physical_or_capacity_conflict", "coverage_gap", "evidence_gap", "preliminary_candidate") if category in categories))
    revision = []
    if plan.get("triggered") is True and not basis_invalid:
        revision.append({"source": "upstream_engineering_adjustment_plan", "status": "candidates_for_flowsheet_revision", "plan": plan, "applied_to_aspen": False,
            "candidate_stage": "screening_only", "eligible_for_flowsheet_implementation": False,
            "adoption_gate": "REFERENCE_POINT_DISTANCE_DOES_NOT_JUSTIFY_ADDED_UNITS" if catalog_distance_only else "SAME_DUTY_CAPABILITY_OR_SYSTEM_BENEFIT_AND_CONFIGURATION_VALIDATION_REQUIRED",
            "complexity_justification": "complexity_not_justified" if catalog_distance_only else "not_yet_established",
            "eligible_for_corrective_configuration_screening": physical_conflict,
            "required_before_adoption": ["applicable_same_duty_capability_conflict_or_demonstrated_whole_system_benefit", "compare_simple_single_unit_baseline", "prove_proposed_configuration_resolves_the_specific_cause", "same_basis_energy_CAPEX_OPEX_control_reliability_maintenance_comparison", "recalculate_affected_equipment_streams_and_whole_flowsheet"],
            "simple_single_unit_baseline": {"status": "BASELINE_TO_EVALUATE_NOT_PROVEN_SELECTABLE", "operating_unit_count": 1,
                "source": "original_unsplit_parameter_package", "values": {field: values[field] for field in ("flow_m3_h", "head_m", "heat_duty_kw", "heat_transfer_area_m2", "inlet_pressure_mpa", "outlet_pressure_mpa") if field in values},
                "preserve_until_alternative_justified": True}})
    if staged_review:
        revision.append({"source": "bridge_coverage_screening", "status": "staged_compression_screening_required", "candidate_status": "candidates_for_flowsheet_revision", "candidate_stage": "screening_only", "eligible_for_flowsheet_implementation": False,
            "adoption_gate": "SAME_GAS_STAGE_ENVELOPE_AND_WHOLE_SYSTEM_BENEFIT_REQUIRED", "stage_count": None, "maximum_stage_pressure_ratio": None, "applied_to_aspen": False})
    neighbors = context.get("neighbors", {}).get(tag, [])
    recalculation = ["same_equipment_basis_and_parameter_chain", "equipment_selector_replay", "same_duty_vendor_or_specialist_evidence"]
    if revision or primary in {"basis_invalid", "physical_or_capacity_conflict"}:
        recalculation += ["upstream_downstream_stream_state_and_pressure", "material_and_energy_balances", "hydraulics_and_power", "controls_startup_turndown_backup", "whole_flowsheet_run_status_and_product_targets"]
    if "exchanger" in str(family):
        recalculation += ["temperature_approach_phase_zones_U_F_fouling", "both_side_pressure_drop_and_parallel_distribution", "same_duty_EDR_and_mechanical_rating"]
    if family == "family_compressor":
        recalculation += ["same_gas_thermodynamics_discharge_temperature_power", "stage_intercooling_pressure_loss_liquid_removal", "surge_choke_turndown_and_vendor_map"]
    return {"equipment_id": tag, "family_id": family, "physical_equipment": True, "raw_response_json_pointer": pointer,
            "raw_equipment_record_sha256": canonical_sha(wrapper), "primary_feedback_category": primary,
            "feedback_categories": categories, "findings": findings, "missing_input_fields": missing,
            "parameter_package": package, "calculation_trace": core.get("calculations", []),
            "terminal_rule_ids": pick_rules(core), "adjustment_plan": plan,
            "compressor_staging_capability": compressor_capability,
            "candidates_for_flowsheet_revision": revision,
            "revision_gate": "REPAIR_INVALID_BASIS_BEFORE_CONFIGURATION_REVIEW" if basis_invalid else "CANDIDATE_REVIEW_ONLY",
            "impact_and_recalculation": {"current_equipment": tag, "known_adjacent_equipment": neighbors,
                "topology_coverage": "CALLER_SUPPLIED_PARTIAL" if neighbors else "NOT_PROVIDED",
                "steps": recalculation, "affected_equipment_status_after_any_approved_edit": "STALE_UNTIL_RECALCULATED"},
            "final_equipment_model": decision.get("model_status") == "final_model",
            "original_upstream_fields": wrapper}


