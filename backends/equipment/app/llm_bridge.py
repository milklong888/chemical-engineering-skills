from __future__ import annotations

import hashlib
import json
import math
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import authority_revision


ALLOWLISTED_DRAFT_FIELDS = {"equipment_type", "process_function", "phase"}
CANONICAL_PHASES = {"liquid", "vapor", "mixed", "solid"}
FORBIDDEN_FIELDS = {
    "pressure_basis", "design_pressure_basis", "atmospheric_pressure_mpa", "inlet_pressure_mpa", "outlet_pressure_mpa",
    "operating_pressure_mpa", "design_pressure_mpa", "design_temperature_c", "volume_basis", "material",
    "vendor_model", "verification_result", "model_status", "final_model",
}

HARD_PARAMETER_FIELDS = {
    "equipment_tag", "equipment_family", "aspen_block_type",
    "pressure_basis", "design_pressure_basis", "atmospheric_pressure_mpa",
    "flow_m3_h", "mass_flow_kg_h", "head_m", "density_kg_m3", "efficiency_percent",
    "inlet_pressure_mpa", "outlet_pressure_mpa", "operating_pressure_mpa",
    "design_pressure_mpa", "design_pressure_factor", "temperature_c",
    "inlet_temperature_c", "design_temperature_c", "pressure_drop_kpa",
    "allowable_pressure_drop_kpa", "heat_duty_kw", "heat_transfer_area_m2",
    "overall_u_w_m2k", "lmtd_k", "lmtd_correction_factor", "diameter_mm", "height_mm", "inner_diameter_mm", "straight_shell_length_mm",
    "volume_m3", "volume_basis", "required_volume_m3", "straight_shell_geometric_volume_m3",
    "pressure_drop_head_component_m", "pressure_drop_power_component_kw",
    "pressure_component_shaft_power_screening_kw",
    "stage_count", "retention_time_min", "fill_fraction",
    "target_velocity_m_s", "selected_dn", "selected_outer_diameter_mm",
    "selected_wall_thickness_mm", "wall_series", "allowable_stress_mpa",
    "weld_efficiency", "npsha_m", "npshr_m", "gas_molecular_weight",
    "compressibility_factor", "surge_margin_percent", "required_surge_margin_percent",
    "surge_margin_evidence_scope", "rotational_speed_rpm",
    "shaft_power_kw", "pressure_drop_power_component_kw", "mixing_metric",
    "membrane_geometry_type", "element_count", "channel_count",
    "channel_inner_diameter_mm", "element_length_m", "membrane_area_m2",
    "flux", "selectivity", "recovery_percent", "capacity", "cycle_time_h",
    "fitting_type", "connection_type", "pressure_class", "flange_face",
    "gasket_material", "valve_function", "cv", "cavitation_margin_m",
    "material", "vendor_model", "verification_result", "approval_status",
    "model_status", "final_model",
}

INJECTION_POINT_POLICIES: dict[str, dict[str, Any]] = {
    "semantic_extraction": {
        "change_fields": {"equipment_type", "process_function", "phase"},
        "sections": {"proposed_changes", "calculation_assists"},
    },
    "textual_condition_judgment": {
        "change_fields": set(),
        "sections": {"condition_assessments", "terminal_selection_assists", "calculation_assists"},
    },
    "ambiguity_resolution": {
        "change_fields": {"equipment_type", "process_function", "phase"},
        "sections": {"proposed_changes", "ambiguity_decision", "calculation_assists"},
    },
    "kg_retrieval_planning": {
        "change_fields": set(),
        "sections": {"retrieval_plan", "calculation_assists"},
    },
    "audit": {
        "change_fields": set(),
        "sections": {"audit_findings", "calculation_assists"},
    },
}

STEP_OUTPUT_KEYS = {
    "schema", "injection_point", "context_sha256", "summary", "citations",
    "proposed_changes", "condition_assessments", "terminal_selection_assists", "calculation_assists", "retrieval_plan",
    "ambiguity_decision", "audit_findings", "output_composition",
}
STEP_OUTPUT_REQUIRED_KEYS = STEP_OUTPUT_KEYS - {"terminal_selection_assists"}

OUTPUT_SECTION_OPERATIONS = {
    "summary": "explain_result",
    "proposed_changes": "propose_descriptive_change",
    "condition_assessments": "assess_conditions",
    "terminal_selection_assists": "select_registered_terminal_form",
    "calculation_assists": "supplement_calculation_input",
    "retrieval_plan": "plan_knowledge_retrieval",
    "ambiguity_decision": "resolve_ambiguity",
    "audit_findings": "audit",
}
OUTPUT_COMPOSITION_KEYS = {"title", "blocks"}
OUTPUT_COMPOSITION_BLOCK_KEYS = {
    "block_id", "operation", "section_ref", "heading", "citations",
}

CALCULATION_ASSIST_KEYS = {
    "assist_id", "target_field", "target_unit", "method", "recipe_id",
    "proposed_value", "certainty", "uncertainty_note", "reason", "citations",
}

# These fields are mandatory only for ``model_inference``.  They make a last-
# resort engineering estimate auditable and bounded instead of accepting a
# naked number from the model.  Deterministic-recipe assists retain the compact
# protocol-1.9 shape for backwards compatibility.
MODEL_INFERENCE_ASSIST_KEYS = {
    "inference_basis", "assumptions", "lower_bound", "upper_bound",
    "confidence", "sensitivity_note", "requested_preliminary_auto_apply",
}

TERMINAL_SELECTION_ASSIST_KEYS = {
    "assist_id", "terminal_rule_id", "condition_id", "selection_context_sha256",
    "reason", "citations",
}

# The model selects a recipe; the program performs the arithmetic.  This keeps
# simple derived inputs useful without handing numeric authority to the model.
CALCULATION_RECIPES: dict[str, dict[str, Any]] = {
    "mass_flow_from_volume_density": {
        "target_field": "mass_flow_kg_h",
        "target_unit": "kg/h",
        "applicable_family_ids": ["*"],
        "inputs": ["flow_m3_h", "density_kg_m3"],
        "formula": "mass_flow_kg_h = flow_m3_h * density_kg_m3",
    },
    "volume_flow_from_mass_density": {
        "target_field": "flow_m3_h",
        "target_unit": "m3/h",
        "applicable_family_ids": ["*"],
        "inputs": ["mass_flow_kg_h", "density_kg_m3"],
        "formula": "flow_m3_h = mass_flow_kg_h / density_kg_m3",
    },
    "pressure_head_component_from_drop_density": {
        "target_field": "pressure_drop_head_component_m",
        "target_unit": "m",
        "applicable_family_ids": ["family_liquid_power_recovery_turbine"],
        "inputs": ["pressure_drop_kpa", "density_kg_m3"],
        "formula": "pressure_drop_head_component_m = pressure_drop_kpa * 1000 / (density_kg_m3 * 9.80665)",
    },
    "pump_shaft_power_from_flow_head": {
        "target_field": "shaft_power_kw",
        "target_unit": "kW",
        "applicable_family_ids": ["family_pump"],
        "inputs": ["flow_m3_h", "head_m", "density_kg_m3", "efficiency_percent"],
        "formula": "shaft_power_kw = density_kg_m3 * 9.80665 * flow_m3_h * head_m / (3.6e6 * efficiency_percent / 100)",
    },
    "pump_hydraulic_power_from_mass_head": {
        "target_field": "hydraulic_power_kw",
        "target_unit": "kW",
        "applicable_family_ids": ["family_pump"],
        "inputs": ["mass_flow_kg_h", "head_m"],
        "formula": "hydraulic_power_kw = mass_flow_kg_h * 9.80665 * head_m / 3.6e6",
    },
    "pump_shaft_power_from_hydraulic_power": {
        "target_field": "shaft_power_kw",
        "target_unit": "kW",
        "applicable_family_ids": ["family_pump"],
        "inputs": ["hydraulic_power_kw", "efficiency_percent"],
        "formula": "shaft_power_kw = hydraulic_power_kw / (efficiency_percent / 100)",
    },
    "heat_transfer_area_from_duty_u_lmtd": {
        "target_field": "heat_transfer_area_m2",
        "target_unit": "m2",
        "applicable_family_ids": [
            "family_fixed_tubesheet_exchanger",
            "family_other_heat_exchanger",
        ],
        "inputs": ["heat_duty_kw", "overall_u_w_m2k", "lmtd_correction_factor", "lmtd_k"],
        "formula": "heat_transfer_area_m2 = abs(heat_duty_kw) * 1000 / (overall_u_w_m2k * lmtd_correction_factor * lmtd_k)",
    },
}


MODEL_ESTIMATE_ENUM_VALUES: dict[str, list[str]] = {
    "pressure_basis": ["absolute", "gauge"],
    "design_pressure_basis": ["absolute", "gauge"],
    "phase": ["liquid", "gas", "vapor", "mixed", "solid"],
    "volume_basis": ["nominal_total", "effective_working", "geometric_total"],
    "membrane_geometry_type": ["cylindrical_channels"],
    "head_type": ["2:1_ellipsoidal"],
}

# Direct equipment/component choice fields are deliberately not model-estimate
# targets.  They are owned by the deterministic model/standard registries (for
# example the HG/T flange/gasket selector).  Allowing free text here would let
# a plausible-sounding invented component bypass those registries.
MODEL_ESTIMATE_DETERMINISTIC_SELECTION_FIELDS = {
    "mixing_metric",
    "wall_series",
    "fitting_type",
    "connection_type",
    "pressure_class",
    "flange_face",
    "gasket_material",
    "valve_function",
}

# This is a preliminary performance description rather than an equipment or
# component identity.  It remains missing-only J evidence and is never treated
# as a source-backed standard choice or vendor identity.
MODEL_ESTIMATE_TEXT_FIELDS = {
}

# Deliberately broad screening guards.  These are not design ranges or defaults;
# they only stop malformed/sentinel model output before the deterministic
# matcher performs its own field and cross-field checks.
MODEL_ESTIMATE_NUMERIC_GUARDS: dict[str, tuple[float | None, float | None]] = {
    "density_kg_m3": (0.01, 50000.0),
    "efficiency_percent": (0.01, 100.0),
    "fill_fraction": (1e-6, 1.0),
    "weld_efficiency": (1e-6, 1.0),
    "lmtd_correction_factor": (1e-6, 1.0),
    "recovery_percent": (0.0, 100.0),
    "head_m": (0.0, 100000.0),
    "npsha_m": (0.0, 10000.0),
    "npshr_m": (0.0, 10000.0),
    "flow_m3_h": (0.0, 1.0e9),
    "mass_flow_kg_h": (0.0, 1.0e12),
    "heat_duty_kw": (-1.0e9, 1.0e9),
    "shaft_power_kw": (0.0, 1.0e9),
    "hydraulic_power_kw": (0.0, 1.0e9),
    "temperature_c": (-273.15, 5000.0),
    "inlet_temperature_c": (-273.15, 5000.0),
    "outlet_temperature_c": (-273.15, 5000.0),
    "design_temperature_c": (-273.15, 5000.0),
    "inlet_pressure_mpa": (-0.101325, 10000.0),
    "outlet_pressure_mpa": (-0.101325, 10000.0),
    "operating_pressure_mpa": (-0.101325, 10000.0),
    "design_pressure_mpa": (-0.101325, 10000.0),
    "design_pressure_factor": (1.0, 10.0),
}

MODEL_ESTIMATE_UNIT_NUMERIC_GUARDS: dict[str, tuple[float | None, float | None]] = {
    "dimensionless": (-1.0e9, 1.0e9),
    "-": (-1.0e9, 1.0e9),
    "%": (0.0, 100.0),
    "count": (0.0, 1.0e7),
    "h": (0.0, 1.0e6),
    "min": (0.0, 1.0e8),
    "r/min": (0.0, 1.0e7),
    "mm": (0.0, 1.0e8),
    "m": (0.0, 1.0e6),
    "m2": (0.0, 1.0e12),
    "m3": (0.0, 1.0e12),
    "m3/h": (0.0, 1.0e12),
    "kg/h": (0.0, 1.0e15),
    "kg/m3": (0.0, 1.0e7),
    "kPa": (-1.0e9, 1.0e9),
    "MPa": (-0.101325, 1.0e5),
    "kW": (-1.0e12, 1.0e12),
    "W/(m2*K)": (0.0, 1.0e9),
    "K": (0.0, 1.0e5),
    "degC": (-273.15, 1.0e5),
    "°C": (-273.15, 1.0e5),
}

CONTEXT_PACK_SCHEMA = "equipment-design-llm-context-pack-v1"
PREPARED_SCHEMA = "equipment-design-llm-prepared-v1"
STEP_OUTPUT_SCHEMA = "equipment-design-llm-step-output-v1"
ORCHESTRATION_SCHEMA = "equipment-design-app-llm-orchestration-v1"
INTERLEAVED_TIMELINE_SCHEMA = "equipment-design-interleaved-timeline-v1"


def _default_step_schema_path() -> Path:
    """Resolve the strict step schema in source and PyInstaller layouts."""
    frozen_root = getattr(sys, "_MEIPASS", None)
    schema_root = (
        Path(frozen_root).resolve() / "app" / "schemas"
        if frozen_root
        else Path(__file__).resolve().parent / "schemas"
    )
    return schema_root / "equipment_design_llm_step_output.schema.json"


STEP_SCHEMA_PATH = _default_step_schema_path()


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()


def _minimal_deterministic_context(result: dict[str, Any]) -> dict[str, Any]:
    design_result = result.get("result") if isinstance(result.get("result"), dict) else result
    if (
        design_result.get("schema") == "aspen-equipment-derivation-result-v1"
        or isinstance(design_result.get("equipment"), list)
        or isinstance(design_result.get("piping"), list)
    ):
        def aggregate_item(item: Any, identity_fields: tuple[str, ...]) -> dict[str, Any] | None:
            if not isinstance(item, dict):
                return None
            match_result = item.get("match_result")
            if not isinstance(match_result, dict):
                match_result = {}
            wrapped_match = dict(match_result)
            if isinstance(item.get("service_profile"), dict):
                wrapped_match["service_profile"] = item["service_profile"]
            if isinstance(item.get("connection_component_selections"), dict):
                wrapped_match["connection_component_selections"] = item[
                    "connection_component_selections"
                ]
            return {
                **{
                    field: item.get(field)
                    for field in identity_fields
                    if item.get(field) is not None
                },
                "canonical_match_input": item.get("canonical_match_input", {}),
                "adapter_blockers": item.get("adapter_blockers", []),
                "evidence_boundary": item.get("evidence_boundary", {}),
                "match_summary": _minimal_deterministic_context(wrapped_match),
            }

        equipment = [
            compact
            for item in design_result.get("equipment", [])
            if (
                compact := aggregate_item(
                    item,
                    (
                        "aspen_block_id",
                        "equipment_tag",
                        "aspen_mapping_status",
                    ),
                )
            ) is not None
        ]
        piping = [
            compact
            for item in design_result.get("piping", [])
            if (
                compact := aggregate_item(
                    item,
                    (
                        "stream_id",
                        "status",
                    ),
                )
            ) is not None
        ]
        return {
            "schema": design_result.get("schema"),
            "status": design_result.get("status"),
            "equipment_count": design_result.get("equipment_count", len(equipment)),
            "piping_count": design_result.get("piping_count", len(piping)),
            "formal_use_gate": design_result.get("formal_use_gate"),
            "formal_use_blockers": design_result.get("formal_use_blockers", []),
            "normalization_diagnostic_count": design_result.get(
                "normalization_diagnostic_count", 0
            ),
            "normalization_diagnostics": design_result.get(
                "normalization_diagnostics", []
            ),
            "source_export_sha256": design_result.get("source_export_sha256"),
            "pfd_mapping_sha256": design_result.get("pfd_mapping_sha256"),
            "equipment": equipment,
            "piping": piping,
        }
    model = design_result.get("model_recommendation", {})
    package = design_result.get("design_parameter_package", {})
    service_profile = design_result.get("_aspen_service_profile")
    if not isinstance(service_profile, dict):
        service_profile = result.get("service_profile") if isinstance(result.get("service_profile"), dict) else {}
    connection_package = design_result.get("_aspen_connection_component_selections")
    if not isinstance(connection_package, dict):
        connection_package = (
            result.get("connection_component_selections")
            if isinstance(result.get("connection_component_selections"), dict)
            else {}
        )
    connection_summary = {
        "schema": connection_package.get("schema"),
        "status": connection_package.get("status"),
        "selection_package_sha256": connection_package.get("selection_package_sha256"),
        "connections": [
            {
                "connection_id": connection.get("connection_id"),
                "stream_id": connection.get("stream_id"),
                "end_role": connection.get("end_role"),
                "applicability": connection.get("applicability"),
                "component_types": {
                    family: {
                        "status": selected.get("status"),
                        "terminal_type": selected.get("terminal_type"),
                        "minimum_missing_fields": selected.get("minimum_missing_fields", []),
                        "warnings": [
                            warning.get("warning_id")
                            for warning in selected.get("warnings", [])
                            if isinstance(warning, dict) and warning.get("warning_id")
                        ],
                        "source_refs": selected.get("source_refs", []),
                    }
                    for family, selected in connection.get("component_types", {}).items()
                    if isinstance(selected, dict)
                },
            }
            for connection in connection_package.get("connections", [])
            if isinstance(connection, dict)
        ],
    } if connection_package else {}
    return {
        "status": design_result.get("status"),
        "normalized_input": design_result.get("normalized_input", {}),
        "unmapped_input_fields": design_result.get("unmapped_input_fields", {}),
        "match": design_result.get("match", {}),
        "progress": design_result.get("progress", {}),
        "model_decision": design_result.get("model_decision", {}),
        "model_recommendation": {
            "status": model.get("status"),
            "recommended_type": model.get("recommended_type"),
            "terminal_selection": model.get("terminal_selection"),
            "terminal_type_rule_registry": model.get("terminal_type_rule_registry", []),
            "candidates": model.get("candidates", []),
            "formal_promotion_blockers": model.get("formal_promotion_blockers", []),
            "formal_model_gate": model.get("formal_model_gate"),
            "prohibited_claim": model.get("prohibited_claim"),
        },
        "selection_feature_vector": package.get("selection_feature_vector", {}),
        "constraint_checks": package.get("constraint_checks", []),
        "calculations": [
            {
                key: item.get(key)
                for key in (
                    "calculation_id",
                    "target_field",
                    "value",
                    "unit",
                    "evidence_class",
                    "result_status",
                    "promotion_cap",
                    "equation_chain",
                    "source_refs",
                )
                if item.get(key) is not None
            }
            for item in design_result.get("calculations", [])
            if isinstance(item, dict)
        ],
        "derived_parameters": design_result.get("derived_parameters", {}),
        "calculation_pending": design_result.get("calculation_pending", []),
        "parameter_errors": design_result.get("parameter_errors", []),
        "design_fallbacks": [
            {
                key: item.get(key)
                for key in (
                    "target_field",
                    "value",
                    "unit",
                    "fallback_tier",
                    "evidence_class",
                    "promotion_cap",
                    "reason",
                )
                if item.get(key) is not None
            }
            for item in design_result.get("design_fallbacks", [])
            if isinstance(item, dict)
        ],
        "service_profile_summary": {
            "schema": service_profile.get("schema"),
            "status": service_profile.get("status"),
            "profile_context_sha256": service_profile.get("profile_context_sha256"),
            "service_labels": service_profile.get("service_labels", []),
            "diagnostics": service_profile.get("diagnostics", []),
        } if service_profile else {},
        "connection_component_selection_summary": connection_summary,
    }


def _candidate_registry(value: Any) -> list[dict[str, Any]]:
    """Collect deterministic candidates without letting an LLM create new identities."""
    collected: dict[str, dict[str, Any]] = {}

    def visit(node: Any) -> None:
        if isinstance(node, list):
            for item in node:
                visit(item)
            return
        if not isinstance(node, dict):
            return
        recommendation = node.get("model_recommendation")
        package = node.get("design_parameter_package")
        if isinstance(recommendation, dict):
            selection_context_sha256 = None
            package_feature_sha256 = None
            if isinstance(package, dict):
                context = package.get("selection_context")
                if isinstance(context, dict):
                    selection_context_sha256 = str(context.get("sha256", "")).strip().upper() or None
                feature_vector = package.get("selection_feature_vector")
                if isinstance(feature_vector, dict):
                    package_feature_sha256 = str(feature_vector.get("sha256", "")).strip().upper() or None
            execution_context_sha256 = None
            execution = recommendation.get("selection_execution")
            if isinstance(execution, dict):
                execution_context_sha256 = str(execution.get("context_sha256", "")).strip().upper() or None
            if selection_context_sha256 and execution_context_sha256 and selection_context_sha256 != execution_context_sha256:
                raise ValueError("确定性 selection_context hash 与 selection_execution context hash 不一致。")
            selection_context_sha256 = selection_context_sha256 or execution_context_sha256
            candidates = recommendation.get("candidates", [])
            if isinstance(candidates, list):
                for candidate in candidates:
                    if not isinstance(candidate, dict):
                        continue
                    candidate_id = str(candidate.get("candidate_id", "")).strip()
                    designation = str(candidate.get("designation", "")).strip()
                    if not candidate_id or not designation:
                        continue
                    feature_hash = (
                        str(candidate.get("selection_feature_vector_sha256", "")).strip().upper()
                        or package_feature_sha256
                    )
                    record = {
                        "candidate_id": candidate_id,
                        "designation": designation,
                        "candidate_kind": str(candidate.get("candidate_kind", "")).strip(),
                        "selection_feature_vector_sha256": feature_hash or None,
                        "selection_context_sha256": selection_context_sha256,
                    }
                    record_key = _canonical_sha256(record)
                    collected[record_key] = record
        for key in ("result", "items", "equipment", "piping", "match_result"):
            child = node.get(key)
            if isinstance(child, (dict, list)):
                visit(child)

    visit(value)
    return sorted(
        collected.values(),
        key=lambda item: (
            item["candidate_id"],
            str(item.get("selection_context_sha256") or ""),
            str(item.get("selection_feature_vector_sha256") or ""),
        ),
    )


def candidate_registry(value: Any) -> list[dict[str, Any]]:
    return _candidate_registry(value)


def _terminal_type_rule_registry(value: Any) -> list[dict[str, Any]]:
    """Expose only matcher-registered condition choices, scoped to one selection context."""

    collected: dict[str, dict[str, Any]] = {}

    def visit(node: Any) -> None:
        if isinstance(node, list):
            for item in node:
                visit(item)
            return
        if not isinstance(node, dict):
            return
        recommendation = node.get("model_recommendation")
        package = node.get("design_parameter_package")
        if isinstance(recommendation, dict) and isinstance(package, dict):
            context = package.get("selection_context")
            context_sha256 = (
                str(context.get("sha256", "")).strip().upper()
                if isinstance(context, dict) else ""
            )
            terminal = recommendation.get("terminal_selection")
            current_status = (
                str(terminal.get("status", "")).strip()
                if isinstance(terminal, dict) else ""
            )
            current_rule_id = (
                str(terminal.get("rule_id", "")).strip()
                if isinstance(terminal, dict) else ""
            )
            current_type = str(recommendation.get("recommended_type", "")).strip()
            family_id = str(recommendation.get("family_id", "")).strip()
            registry = recommendation.get("terminal_type_rule_registry", [])
            if context_sha256 and isinstance(registry, list):
                for rule in registry:
                    if not isinstance(rule, dict):
                        continue
                    rule_id = str(rule.get("rule_id", "")).strip()
                    condition_id = str(rule.get("condition_id") or rule_id).strip()
                    recommended_type = str(rule.get("recommended_type", "")).strip()
                    condition_text = str(rule.get("condition_text", "")).strip()
                    if not all((family_id, rule_id, condition_id, recommended_type, condition_text)):
                        continue
                    record = {
                        "rule_id": rule_id,
                        "condition_id": condition_id,
                        "family_id": family_id,
                        "recommended_type": recommended_type,
                        "condition_text": condition_text,
                        "assumption": str(rule.get("assumption", "")).strip(),
                        "promotion_cap": str(rule.get("promotion_cap", "TYPE_SCREENING")).strip(),
                        "selection_context_sha256": context_sha256,
                        "current_terminal_status": current_status,
                        "current_terminal_rule_id": current_rule_id,
                        "current_recommended_type": current_type,
                    }
                    collected[_canonical_sha256(record)] = record
        for key in ("result", "items", "equipment", "piping", "match_result"):
            child = node.get(key)
            if isinstance(child, (dict, list)):
                visit(child)

    visit(value)
    return sorted(
        collected.values(),
        key=lambda item: (item["selection_context_sha256"], item["rule_id"]),
    )


def _condition_registry(value: Any) -> list[dict[str, Any]]:
    collected: dict[str, dict[str, Any]] = {}

    def add(condition_id: Any, kind: str, status: Any) -> None:
        normalized_id = str(condition_id or "").strip()
        if not normalized_id:
            return
        record = {"condition_id": normalized_id, "kind": kind, "deterministic_status": status}
        previous = collected.get(normalized_id)
        if previous is not None and previous != record:
            previous["deterministic_status"] = "MIXED"
            return
        collected[normalized_id] = record

    def visit(node: Any) -> None:
        if isinstance(node, list):
            for item in node:
                visit(item)
            return
        if not isinstance(node, dict):
            return
        checks = node.get("constraint_checks")
        if isinstance(checks, list):
            for check in checks:
                if isinstance(check, dict):
                    add(check.get("check_id"), "constraint_check", check.get("status"))
        predicate_trace = node.get("predicate_trace")
        if isinstance(predicate_trace, list):
            for predicate in predicate_trace:
                if isinstance(predicate, dict):
                    add(predicate.get("predicate_id"), "candidate_predicate", predicate.get("status"))
        terminal_registry = node.get("terminal_type_rule_registry")
        if isinstance(terminal_registry, list):
            for rule in terminal_registry:
                if isinstance(rule, dict):
                    add(
                        rule.get("condition_id") or rule.get("rule_id"),
                        "terminal_type_rule",
                        "ELIGIBLE_IF_MODEL_SUPPORTED",
                    )
        for child in node.values():
            if isinstance(child, (dict, list)):
                visit(child)

    visit(value)
    return [collected[key] for key in sorted(collected)]


def calculation_recipe_catalog() -> list[dict[str, Any]]:
    return [
        {"recipe_id": recipe_id, **json.loads(json.dumps(recipe, ensure_ascii=False))}
        for recipe_id, recipe in sorted(CALCULATION_RECIPES.items())
    ]


def _design_result(value: dict[str, Any]) -> dict[str, Any]:
    return value.get("result") if isinstance(value.get("result"), dict) else value


def _canonical_target_unit(unit: Any) -> str:
    text = str(unit or "").strip()
    return text or "dimensionless"


def _missing_input_registry(deterministic_result: dict[str, Any]) -> list[dict[str, Any]]:
    """Expose only still-missing preliminary closure fields to the model.

    Evidence artifacts, equipment identity, final-model fields and already
    available values are deliberately absent.  The model therefore cannot turn
    the last-resort completion path into a general parameter overwrite surface.
    """

    design = _design_result(deterministic_result)
    if not isinstance(design, dict):
        return []
    package = design.get("design_parameter_package")
    package = package if isinstance(package, dict) else {}
    progress = design.get("progress")
    progress = progress if isinstance(progress, dict) else {}
    model_decision = design.get("model_decision")
    model_decision = model_decision if isinstance(model_decision, dict) else {}

    goals: dict[str, set[str]] = {}

    def add(field: Any, goal: str) -> None:
        field_id = str(field or "").strip()
        if field_id:
            goals.setdefault(field_id, set()).add(goal)

    selection_vector = package.get("selection_feature_vector")
    if isinstance(selection_vector, dict):
        for field in selection_vector.get("missing_fields", []):
            add(field, "candidate_matching")
    for field in model_decision.get("sizing_missing_fields", []):
        add(field, "sizing")
    for item in design.get("calculation_pending", []):
        if not isinstance(item, dict):
            continue
        calculation_id = str(item.get("calculation_id") or "unknown")
        for field in item.get("missing_fields", []):
            add(field, f"calculation:{calculation_id}")
    for item in progress.get("minimum_missing_sets", []):
        if not isinstance(item, dict):
            continue
        goal = str(item.get("goal") or "progressive_closure")
        for field in item.get("fields", []):
            add(field, goal)
    for item in progress.get("next_fields", []):
        if isinstance(item, dict):
            add(item.get("field"), str(item.get("reason") or "progressive_closure"))

    forbidden = {
        "equipment_tag", "equipment_family", "equipment_type", "aspen_block_type",
        "candidate_model", "vendor_model", "final_model", "model_status",
        "verification_result", "approval_status", "material",
        *MODEL_ESTIMATE_DETERMINISTIC_SELECTION_FIELDS,
    }
    forbidden_suffixes = ("_path", "_sha256", "_ref")
    rows: dict[str, dict[str, Any]] = {}
    for group in package.get("groups", []):
        if not isinstance(group, dict) or group.get("group_id") == "evidence":
            continue
        for row in group.get("rows", []):
            if not isinstance(row, dict):
                continue
            field_id = str(row.get("field_id") or "").strip()
            if field_id:
                rows[field_id] = row

    registry: list[dict[str, Any]] = []
    for field_id in sorted(goals):
        if field_id in forbidden or field_id.endswith(forbidden_suffixes):
            continue
        row = rows.get(field_id, {})
        if row.get("raw_value") not in (None, ""):
            continue
        if row.get("state") == "EXTERNAL_REQUIRED":
            continue
        allowed_values = MODEL_ESTIMATE_ENUM_VALUES.get(field_id, [])
        value_type = (
            "enum" if allowed_values
            else "text" if field_id in MODEL_ESTIMATE_TEXT_FIELDS
            else "number"
        )
        target_unit = _canonical_target_unit(row.get("unit"))
        guard = (
            MODEL_ESTIMATE_NUMERIC_GUARDS.get(field_id)
            or (MODEL_ESTIMATE_UNIT_NUMERIC_GUARDS.get(target_unit) if value_type == "number" else None)
        )
        registry.append({
            "field_id": field_id,
            "label": str(row.get("label") or field_id),
            "target_unit": target_unit,
            "value_type": value_type,
            "allowed_values": list(allowed_values),
            "registry_id": f"model_estimate_enum:{field_id}:v1" if allowed_values else None,
            "program_guard": {
                "minimum": guard[0] if guard else None,
                "maximum": guard[1] if guard else None,
                "kind": "broad_non_design_sanity_guard",
            },
            "required_for": sorted(goals[field_id]),
            "current_state": str(row.get("state") or "MISSING"),
            "evidence_class_if_used": "J",
            "promotion_cap": "TYPE_SCREENING",
        })
    return registry


def build_context_pack(
    deterministic_result: dict[str, Any],
    kg_result: dict[str, Any],
    injection_point: str,
    mode: str = "minimum",
) -> dict[str, Any]:
    if injection_point not in INJECTION_POINT_POLICIES:
        raise ValueError(f"不支持的 LLM 注入点：{injection_point}")
    context_scope = {"full": "full_bundle"}.get(mode, mode)
    if context_scope not in {"minimum", "routed", "full_family", "full_bundle"}:
        raise ValueError("KG 上下文范围只能是 minimum、routed、full_family 或 full_bundle。")
    deterministic_content = (
        deterministic_result if context_scope in {"full_family", "full_bundle"}
        else _minimal_deterministic_context(deterministic_result)
    )
    sources: list[dict[str, Any]] = [{
        "context_id": "deterministic_result",
        "kind": "deterministic_result",
        "source_sha256": _canonical_sha256(deterministic_result),
        "content": deterministic_content,
    }]
    included_assets: list[dict[str, Any]] = []
    truncated_assets: list[dict[str, Any]] = []
    hits = kg_result.get("hits", [])
    hits = hits if isinstance(hits, list) else []
    for index, hit in enumerate(hits, 1):
        if not isinstance(hit, dict):
            continue
        bounded = {
            key: hit.get(key)
            for key in (
                "rank", "score", "source", "source_path", "path", "line",
                "title", "text", "vector_id", "source_type", "source_group",
            )
            if hit.get(key) is not None
        }
        source_record = {
            "context_id": f"kg:{index:03d}",
            "kind": "knowledge_graph_hit",
            "source_sha256": _canonical_sha256(bounded),
            "content": bounded,
        }
        sources.append(source_record)
        included_assets.append({
            "context_id": source_record["context_id"],
            "path": bounded.get("source_path") or bounded.get("path") or bounded.get("source"),
            "sha256": source_record["source_sha256"],
            "coverage": "hit_excerpt",
        })
        if bool(hit.get("truncated")):
            truncated_assets.append({
                "context_id": source_record["context_id"],
                "path": bounded.get("source_path") or bounded.get("path") or bounded.get("source"),
                "reason": "source_marked_truncated",
            })

    assets = kg_result.get("assets", [])
    assets = assets if isinstance(assets, list) else []
    for index, asset in enumerate(assets, 1):
        if not isinstance(asset, dict) or "content" not in asset:
            continue
        content = asset.get("content")
        source_hash = str(asset.get("sha256", "")).strip().upper() or _canonical_sha256(content)
        source_record = {
            "context_id": f"kg_asset:{index:03d}",
            "kind": "knowledge_graph_asset",
            "source_sha256": source_hash,
            "content": content,
        }
        sources.append(source_record)
        included_assets.append({
            "context_id": source_record["context_id"],
            "path": asset.get("path") or asset.get("source_path"),
            "sha256": source_hash,
            "coverage": "full_asset" if not asset.get("truncated") else "partial_asset",
        })
        if bool(asset.get("truncated")):
            truncated_assets.append({
                "context_id": source_record["context_id"],
                "path": asset.get("path") or asset.get("source_path"),
                "reason": "source_marked_truncated",
            })

    result_count = kg_result.get("result_count")
    if isinstance(result_count, int) and result_count > len(hits):
        truncated_assets.append({
            "context_id": None,
            "path": None,
            "reason": f"{result_count - len(hits)}_retrieval_hits_not_included",
        })
    supplied_truncation = kg_result.get("truncated_assets", [])
    if isinstance(supplied_truncation, list):
        for item in supplied_truncation:
            if isinstance(item, dict):
                truncated_assets.append({
                    "context_id": item.get("context_id"),
                    "path": item.get("path") or item.get("source_path"),
                    "reason": str(item.get("reason", "upstream_reported_truncation")),
                })
            else:
                truncated_assets.append({"context_id": None, "path": None, "reason": str(item)})

    upstream_coverage = str(kg_result.get("coverage_status", "")).strip().upper()
    if context_scope == "minimum":
        coverage_status = "BOUNDED_MINIMUM" if not truncated_assets else "PARTIAL"
    elif context_scope == "routed":
        coverage_status = "ROUTED_HITS" if not truncated_assets else "PARTIAL"
    elif upstream_coverage in {"COMPLETE", "COMPLETE_FAMILY", "COMPLETE_BUNDLE"} and assets and not truncated_assets:
        coverage_status = "COMPLETE"
    else:
        coverage_status = "PARTIAL"
        if not truncated_assets:
            truncated_assets.append({
                "context_id": None,
                "path": None,
                "reason": "full_scope_not_proven_by_complete_kg_assets",
            })

    char_count = sum(
        len(json.dumps(source.get("content"), ensure_ascii=False, sort_keys=True))
        for source in sources
    )
    pack: dict[str, Any] = {
        "schema": CONTEXT_PACK_SCHEMA,
        "injection_point": injection_point,
        "mode": context_scope,
        "context_scope": context_scope,
        "coverage_status": coverage_status,
        "included_assets": included_assets,
        "truncated_assets": truncated_assets,
        "char_count": char_count,
        "deterministic_result_sha256": _canonical_sha256(deterministic_result),
        "kg_result_sha256": _canonical_sha256(kg_result),
        "kg_status": kg_result.get("status", "UNKNOWN"),
        "candidate_registry": _candidate_registry(deterministic_result),
        "condition_registry": _condition_registry(deterministic_result),
        "terminal_type_rule_registry": _terminal_type_rule_registry(deterministic_result),
        "calculation_recipe_catalog": calculation_recipe_catalog(),
        "missing_input_registry": _missing_input_registry(deterministic_result),
        "model_estimate_policy": {
            "enabled": True,
            "use_only_after_registered_recipes": True,
            "missing_fields_only": True,
            "structured_bounds_and_assumptions_required": True,
            "preliminary_auto_apply_allowed_after_program_validation": True,
            "evidence_class": "J",
            "promotion_cap": "TYPE_SCREENING",
            "formal_model_promotion_allowed": False,
            "script_conflict_policy": "deterministic_script_wins",
        },
        "sources": sources,
    }
    pack["context_sha256"] = _canonical_sha256(pack)
    return pack
SUPPORTED_PROVIDERS: dict[str, dict[str, Any]] = {
    "mock": {
        "label": "Offline mock provider",
        "default_base_url": None,
        "remote": False,
    },
    "openai": {
        "label": "OpenAI",
        "default_base_url": "https://api.openai.com/v1",
        "remote": True,
    },
    "openai_compatible": {
        "label": "OpenAI-compatible API",
        "default_base_url": "https://api.openai.com/v1",
        "remote": True,
    },
    "local_openai_compatible": {
        "label": "Local OpenAI-compatible API",
        "default_base_url": "http://127.0.0.1:8000/v1",
        "remote": False,
    },
}

SUPPORTED_WIRE_APIS = {"chat_completions", "responses"}
SUPPORTED_REASONING_EFFORTS = {"minimal", "low", "medium", "high", "xhigh"}


def provider_catalog() -> dict[str, Any]:
    return {
        "providers": [
            {"id": provider_id, **metadata}
            for provider_id, metadata in SUPPORTED_PROVIDERS.items()
        ],
        "timeout_s": {"default": 90, "minimum": 5, "maximum": 600},
        "wire_apis": ["chat_completions", "responses"],
        "reasoning_efforts": ["minimal", "low", "medium", "high", "xhigh"],
        "response_storage_default": False,
        "api_key_policy": "runtime_memory_or_environment_only; never persist or echo",
        "injection_points": sorted(INJECTION_POINT_POLICIES),
        "context_scopes": ["minimum", "routed", "full_family", "full_bundle"],
        "phases": ["hybrid_prepare", "hybrid_continue", "hybrid_run"],
        "deterministic_authority": True,
    }


def test_provider_connection(config: dict[str, Any]) -> dict[str, Any]:
    """Safely validate a configured provider without retaining its credential.

    A remote check intentionally sends one minimal request over the selected
    wire protocol so
    the returned state proves the exact configured model is reachable, rather
    than merely proving that a URL parses.  This is operational metadata only:
    credentials are never included in the returned object or written to disk.
    """
    schema = "equipment-design-llm-connection-test-v1"
    api_key = str(config.get("api_key", "")).strip() if isinstance(config, dict) else ""
    provider = str(config.get("provider", "openai_compatible")).strip() if isinstance(config, dict) else ""
    model_id = str(config.get("model_id") or config.get("model") or "").strip() if isinstance(config, dict) else ""
    wire_api = "chat_completions"
    reasoning_effort: str | None = None
    disable_response_storage = True
    endpoint_profile = "unknown"
    endpoint: str | None = None
    timeout_s: int | None = None
    try:
        provider_definition = SUPPORTED_PROVIDERS.get(provider)
        if provider_definition is None:
            raise ValueError("不支持的 LLM provider。")
        if not model_id:
            raise ValueError("必须填写精确 model_id。")
        if provider == "mock":
            return {
                "schema": schema,
                "status": "CONNECTED",
                "provider": provider,
                "model_id": model_id,
                "endpoint_profile": "offline_mock",
                "message": "离线 mock provider 已验证；未发起网络请求。",
            }
        base_url = str(config.get("base_url") or provider_definition["default_base_url"]).strip()
        timeout_s = _timeout_seconds(config.get("timeout_s", 90))
        wire_api = _wire_api(config)
        reasoning_effort = _reasoning_effort(config)
        disable_response_storage = _disable_response_storage(config)
        endpoint = _endpoint(base_url, provider, wire_api)
        parsed_endpoint = urllib.parse.urlparse(endpoint)
        is_loopback = parsed_endpoint.hostname in {"localhost", "127.0.0.1", "::1"}
        endpoint_profile = "local_openai_compatible" if is_loopback else "remote_openai_compatible"
        if not api_key and not is_loopback:
            raise ValueError("远程 API 必须填写 API Key。")
        if wire_api == "responses":
            payload = _responses_payload(
                model_id,
                "Reply with exactly: pong",
                reasoning_effort=reasoning_effort,
                disable_response_storage=disable_response_storage,
                max_output_tokens=16,
            )
        else:
            payload = {
                "model": model_id,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 1,
                "temperature": 0,
            }
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_s) as response:
                response_obj = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = _redact(exc.read().decode("utf-8", errors="replace")[:1500], api_key)
            raise RuntimeError(f"LLM API HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"LLM API 连接失败：{_redact(str(exc.reason), api_key)}") from exc
        _content(response_obj)
        return {
            "schema": schema,
            "status": "CONNECTED",
            "provider": provider,
            "model_id": model_id,
            "endpoint_profile": endpoint_profile,
            "wire_api": wire_api,
            "reasoning_effort": reasoning_effort,
            "response_storage_disabled": disable_response_storage if wire_api == "responses" else None,
            "message": f"已通过最小 {wire_api} 请求验证该精确模型。",
        }
    except Exception as exc:
        return {
            "schema": schema,
            "status": "FAILED",
            "provider": provider or "unknown",
            "model_id": model_id or None,
            "endpoint_profile": endpoint_profile,
            "wire_api": wire_api,
            "reasoning_effort": reasoning_effort,
            "response_storage_disabled": disable_response_storage if wire_api == "responses" else None,
            "message": _redact(str(exc), api_key),
        }


def _wire_api(config: dict[str, Any]) -> str:
    raw = str(config.get("wire_api", "chat_completions")).strip().lower().replace("-", "_")
    aliases = {
        "chat": "chat_completions",
        "chat/completions": "chat_completions",
        "chat_completions": "chat_completions",
        "response": "responses",
        "responses": "responses",
    }
    wire_api = aliases.get(raw)
    if wire_api not in SUPPORTED_WIRE_APIS:
        raise ValueError("wire_api 只能是 chat_completions 或 responses。")
    return wire_api


def _reasoning_effort(config: dict[str, Any]) -> str | None:
    raw = str(config.get("reasoning_effort") or "").strip().lower()
    if not raw or raw == "none":
        return None
    if raw not in SUPPORTED_REASONING_EFFORTS:
        raise ValueError(
            "reasoning_effort 只能是 minimal、low、medium、high 或 xhigh。"
        )
    return raw


def _disable_response_storage(config: dict[str, Any]) -> bool:
    raw = config.get("disable_response_storage", True)
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)) and raw in {0, 1}:
        return bool(raw)
    normalized = str(raw).strip().lower()
    if normalized in {"true", "1", "yes", "on"}:
        return True
    if normalized in {"false", "0", "no", "off"}:
        return False
    raise ValueError("disable_response_storage 必须是布尔值。")


def _responses_payload(
    model: str,
    input_value: str,
    *,
    instructions: str | None = None,
    reasoning_effort: str | None = None,
    disable_response_storage: bool = True,
    max_output_tokens: int | None = None,
    json_schema: dict[str, Any] | None = None,
    schema_name: str = "equipment_design_output",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "input": input_value,
        "store": not disable_response_storage,
    }
    if instructions:
        payload["instructions"] = instructions
    if reasoning_effort:
        payload["reasoning"] = {"effort": reasoning_effort}
    if max_output_tokens is not None:
        payload["max_output_tokens"] = max_output_tokens
    if json_schema is not None:
        payload["text"] = {
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "strict": True,
                "schema": json_schema,
            }
        }
    return payload


def _endpoint(
    base_url: str,
    provider: str = "openai_compatible",
    wire_api: str = "chat_completions",
) -> str:
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"不支持的 LLM provider：{provider}。")
    if wire_api not in SUPPORTED_WIRE_APIS:
        raise ValueError(f"不支持的 wire_api：{wire_api}。")
    value = str(base_url).strip().rstrip("/")
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("API Base URL 只能使用 http/https。")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("API Base URL 禁止 userinfo、query 或 fragment。")
    if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("远程 API 必须使用 HTTPS；HTTP 仅允许本机 loopback。")
    if provider == "openai" and parsed.hostname != "api.openai.com":
        raise ValueError("provider=openai 时 API Base URL 必须使用 api.openai.com。")
    if provider == "local_openai_compatible" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("local_openai_compatible 仅允许本机 loopback 地址。")
    target_suffix = "/responses" if wire_api == "responses" else "/chat/completions"
    for known_suffix in ("/chat/completions", "/responses"):
        if value.endswith(known_suffix):
            value = value[: -len(known_suffix)]
            break
    return value + target_suffix


def _timeout_seconds(value: Any) -> int:
    try:
        timeout_s = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("timeout_s 必须是 5-600 秒的整数。") from exc
    if not 5 <= timeout_s <= 600:
        raise ValueError("timeout_s 必须在 5-600 秒之间。")
    return timeout_s


def _redact(text: str, *secrets: str) -> str:
    result = str(text)
    for secret in secrets:
        if secret:
            result = result.replace(secret, "[REDACTED]")
    return result


def _content(response: dict[str, Any]) -> str:
    output_text = response.get("output_text")
    if isinstance(output_text, str) and output_text:
        return output_text

    output = response.get("output")
    if isinstance(output, list):
        text_parts: list[str] = []
        for item in output:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for content_item in content:
                if not isinstance(content_item, dict):
                    continue
                if content_item.get("type") == "output_text" and isinstance(content_item.get("text"), str):
                    text_parts.append(content_item["text"])
        if text_parts:
            return "\n".join(text_parts)

    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("API 响应缺少可用的 output_text、output message 或 choices。")
    content = choices[0].get("message", {}).get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(item.get("text", "")) for item in content if isinstance(item, dict))
    raise ValueError("API 响应缺少文本 content。")


def _parse_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, flags=re.S | re.I)
    if fenced:
        stripped = fenced.group(1)
    parsed = json.loads(stripped)
    if not isinstance(parsed, dict):
        raise ValueError("LLM 必须返回 JSON 对象。")
    return parsed


def _require_exact_keys(value: dict[str, Any], required: set[str], label: str) -> None:
    actual = set(value)
    if actual != required:
        raise ValueError(
            f"{label} 字段必须严格等于 {sorted(required)}；"
            f"缺少 {sorted(required - actual)}，多出 {sorted(actual - required)}。"
        )


def _require_keys_with_optional(
    value: dict[str, Any],
    required: set[str],
    optional: set[str],
    label: str,
) -> None:
    actual = set(value)
    missing = required - actual
    extra = actual - required - optional
    if missing or extra:
        raise ValueError(
            f"{label} 缺少 {sorted(missing)}，多出 {sorted(extra)}；"
            f"允许字段为 {sorted(required | optional)}。"
        )


def _string(value: Any, label: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} 必须是字符串。")
    normalized = value.strip()
    if not allow_empty and not normalized:
        raise ValueError(f"{label} 不能为空。")
    return normalized


def _citations(value: Any, known_ids: set[str], label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{label} 必须是 context_id 字符串数组。")
    normalized = [item.strip() for item in value]
    if not normalized:
        raise ValueError(f"{label} 至少需要一个 context_id。")
    unknown = sorted({item for item in normalized if item not in known_ids})
    if unknown:
        raise ValueError(f"{label} 引用了上下文包中不存在的 context_id：{unknown}")
    return normalized


def _verify_context_pack(context_pack: dict[str, Any]) -> None:
    if context_pack.get("schema") != CONTEXT_PACK_SCHEMA:
        raise ValueError(f"上下文包 schema 必须是 {CONTEXT_PACK_SCHEMA}。")
    claimed = _string(context_pack.get("context_sha256"), "context_sha256")
    unhashed = {key: value for key, value in context_pack.items() if key != "context_sha256"}
    actual = _canonical_sha256(unhashed)
    if claimed != actual:
        raise ValueError(f"上下文包哈希不一致：expected={claimed}, actual={actual}")
    if context_pack.get("context_scope") not in {"minimum", "routed", "full_family", "full_bundle"}:
        raise ValueError("上下文包缺少有效 context_scope。")
    if context_pack.get("coverage_status") not in {"BOUNDED_MINIMUM", "ROUTED_HITS", "PARTIAL", "COMPLETE"}:
        raise ValueError("上下文包缺少有效 coverage_status。")
    if not isinstance(context_pack.get("sources"), list):
        raise ValueError("上下文包 sources 必须是数组。")


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _deterministic_numeric_inputs(context_pack: dict[str, Any]) -> dict[str, float]:
    sources = context_pack.get("sources", [])
    deterministic = next(
        (
            item.get("content") for item in sources
            if isinstance(item, dict) and item.get("context_id") == "deterministic_result"
        ),
        {},
    )
    if not isinstance(deterministic, dict):
        return {}
    design_result = (
        deterministic.get("result")
        if isinstance(deterministic.get("result"), dict)
        else deterministic
    )
    normalized = design_result.get("normalized_input")
    derived = design_result.get("derived_parameters")
    normalized = normalized if isinstance(normalized, dict) else {}
    derived = derived if isinstance(derived, dict) else {}
    result: dict[str, float] = {}
    for field, value in {**derived, **normalized}.items():
        number = _finite_number(value)
        if number is not None:
            result[str(field)] = number
    return result


def _deterministic_scalar_inputs(context_pack: dict[str, Any]) -> dict[str, Any]:
    sources = context_pack.get("sources", [])
    deterministic = next(
        (
            item.get("content") for item in sources
            if isinstance(item, dict) and item.get("context_id") == "deterministic_result"
        ),
        {},
    )
    if not isinstance(deterministic, dict):
        return {}
    design_result = _design_result(deterministic)
    normalized = design_result.get("normalized_input")
    derived = design_result.get("derived_parameters")
    normalized = normalized if isinstance(normalized, dict) else {}
    derived = derived if isinstance(derived, dict) else {}
    result: dict[str, Any] = {}
    for field, value in {**derived, **normalized}.items():
        if isinstance(value, bool) or isinstance(value, str):
            if not isinstance(value, str) or value.strip():
                result[str(field)] = value
        else:
            number = _finite_number(value)
            if number is not None:
                result[str(field)] = number
    return result


def _deterministic_family_id(context_pack: dict[str, Any]) -> str | None:
    sources = context_pack.get("sources", [])
    deterministic = next(
        (
            item.get("content") for item in sources
            if isinstance(item, dict) and item.get("context_id") == "deterministic_result"
        ),
        {},
    )
    if not isinstance(deterministic, dict):
        return None
    design_result = (
        deterministic.get("result")
        if isinstance(deterministic.get("result"), dict)
        else deterministic
    )
    match = design_result.get("match")
    if not isinstance(match, dict):
        return None
    family_id = str(match.get("family_id", "")).strip()
    return family_id or None


def _calculate_recipe(recipe_id: str, values: dict[str, float]) -> float:
    for field in ("density_kg_m3", "overall_u_w_m2k", "lmtd_k"):
        if field in values and values[field] <= 0:
            raise ValueError(f"{field} must be positive")
    for field in ("flow_m3_h", "mass_flow_kg_h", "head_m", "pressure_drop_kpa", "heat_transfer_area_m2"):
        if field in values and values[field] < 0:
            raise ValueError(f"{field} must be nonnegative")
    if "efficiency_percent" in values and not 0 < values["efficiency_percent"] <= 100:
        raise ValueError("efficiency_percent must be in (0, 100]")
    if "lmtd_correction_factor" in values and not 0 < values["lmtd_correction_factor"] <= 1:
        raise ValueError("lmtd_correction_factor must be in (0, 1]")
    if recipe_id == "mass_flow_from_volume_density":
        result = values["flow_m3_h"] * values["density_kg_m3"]
    elif recipe_id == "volume_flow_from_mass_density":
        result = values["mass_flow_kg_h"] / values["density_kg_m3"]
    elif recipe_id == "pressure_head_component_from_drop_density":
        result = values["pressure_drop_kpa"] * 1000.0 / (values["density_kg_m3"] * 9.80665)
    elif recipe_id == "pump_shaft_power_from_flow_head":
        efficiency = values["efficiency_percent"] / 100.0
        result = (
            values["density_kg_m3"] * 9.80665 * values["flow_m3_h"] * values["head_m"]
            / (3.6e6 * efficiency)
        )
    elif recipe_id == "pump_hydraulic_power_from_mass_head":
        result = values["mass_flow_kg_h"] * 9.80665 * values["head_m"] / 3.6e6
    elif recipe_id == "pump_shaft_power_from_hydraulic_power":
        efficiency = values["efficiency_percent"] / 100.0
        result = values["hydraulic_power_kw"] / efficiency
    elif recipe_id == "heat_transfer_area_from_duty_u_lmtd":
        if values["heat_duty_kw"] == 0:
            raise ValueError("heat_duty_kw=0 cannot close a heat-exchanger area design")
        result = (
            abs(values["heat_duty_kw"]) * 1000.0
            / (
                values["overall_u_w_m2k"]
                * values["lmtd_correction_factor"]
                * values["lmtd_k"]
            )
        )
    else:
        raise ValueError(f"unknown calculation recipe: {recipe_id}")
    if not math.isfinite(result):
        raise ValueError("calculation result is not finite")
    return result


def validate_calculation_assists(
    assists: list[dict[str, Any]],
    context_pack: dict[str, Any],
) -> list[dict[str, Any]]:
    """Close recipes first, then bounded estimates, then dependent recipes.

    This is intentionally a small dependency solver rather than an input-order
    loop.  A model may list recipes in any order; every program-verifiable
    relation is exhausted before a model estimate is considered.  When a later
    recipe can compute a field previously estimated by the model, the script
    value replaces the estimate and the estimate is retained only as a
    superseded audit record.
    """

    existing_numeric = _deterministic_numeric_inputs(context_pack)
    existing_scalars = _deterministic_scalar_inputs(context_pack)
    working_numeric = dict(existing_numeric)
    working_scalars = dict(existing_scalars)
    provenance = {field: "deterministic_context" for field in working_scalars}
    current_family_id = _deterministic_family_id(context_pack)
    missing_registry = {
        str(item.get("field_id")): item
        for item in context_pack.get("missing_input_registry", [])
        if isinstance(item, dict) and str(item.get("field_id", "")).strip()
    }
    validations: list[dict[str, Any]] = []
    pending_recipes: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
    estimate_items: list[tuple[int, dict[str, Any]]] = []

    for assist in assists:
        record = {
            "assist_id": assist["assist_id"],
            "target_field": assist["target_field"],
            "target_unit": assist["target_unit"],
            "method": assist["method"],
            "certainty": assist["certainty"],
            "auto_apply": False,
            "resolved_value": None,
            "status": "REJECTED_NONBLOCKING",
            "detail": None,
        }
        validations.append(record)
        record_index = len(validations) - 1
        if assist["method"] == "model_inference":
            estimate_items.append((record_index, assist))
            continue

        recipe = CALCULATION_RECIPES.get(str(assist["recipe_id"]))
        if recipe is None:
            record["detail"] = "unknown_recipe"
            continue
        applicable_family_ids = recipe["applicable_family_ids"]
        if "*" not in applicable_family_ids and current_family_id not in applicable_family_ids:
            record.update({
                "status": "REJECTED_NONBLOCKING_WRONG_SCOPE",
                "detail": (
                    f"current_family={current_family_id or 'UNKNOWN'}; "
                    f"applicable_families={','.join(applicable_family_ids)}"
                ),
            })
            continue
        if assist["target_field"] != recipe["target_field"] or assist["target_unit"] != recipe["target_unit"]:
            record["detail"] = "recipe_target_or_unit_mismatch"
            continue
        pending_recipes.append((record_index, assist, recipe))

    unresolved = list(pending_recipes)

    def resolve_recipe_pass() -> bool:
        nonlocal unresolved
        progress = False
        remaining: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
        for record_index, assist, recipe in unresolved:
            record = validations[record_index]
            missing = [field for field in recipe["inputs"] if field not in working_numeric]
            if missing:
                remaining.append((record_index, assist, recipe))
                continue
            try:
                value = _calculate_recipe(str(assist["recipe_id"]), working_numeric)
            except (KeyError, ValueError, ZeroDivisionError) as exc:
                record["detail"] = f"recipe_evaluation_failed:{exc}"
                progress = True
                continue
            target = assist["target_field"]
            dependency_is_provisional = any(
                provenance.get(field) in {"model_estimate", "recipe_from_model_estimate"}
                for field in recipe["inputs"]
            )
            if target in existing_numeric:
                current = existing_numeric[target]
                tolerance = max(1e-9, abs(current) * 1e-9)
                record.update({
                    "resolved_value": value,
                    "status": (
                        "ALREADY_AVAILABLE_CONSISTENT"
                        if abs(current - value) <= tolerance
                        else "REJECTED_EXISTING_VALUE_CONFLICT"
                    ),
                    "detail": (
                        "existing deterministic input already carries the same value"
                        if abs(current - value) <= tolerance
                        else f"existing={current}; calculated={value}"
                    ),
                })
                progress = True
                continue
            if target in working_numeric and provenance.get(target) != "model_estimate":
                current = working_numeric[target]
                tolerance = max(1e-9, max(abs(current), abs(value)) * 1e-9)
                record.update({
                    "resolved_value": value,
                    "status": (
                        "DUPLICATE_VERIFIED_CONSISTENT"
                        if abs(current - value) <= tolerance
                        else "REJECTED_DERIVATION_CONFLICT"
                    ),
                    "detail": (
                        f"duplicate consistent derivation for {target}"
                        if abs(current - value) <= tolerance
                        else f"verified derivations disagree for {target}: existing={current}; calculated={value}"
                    ),
                })
                progress = True
                continue
            if target in working_numeric and provenance.get(target) == "model_estimate":
                for estimate_record in validations:
                    if (
                        estimate_record.get("target_field") == target
                        and estimate_record.get("status") == "VERIFIED_PROVISIONAL_ENGINEERING_ESTIMATE"
                    ):
                        estimate_record.update({
                            "status": "SUPERSEDED_BY_DETERMINISTIC_RECIPE",
                            "auto_apply": False,
                            "detail": (
                                f"script value {value} superseded provisional model estimate "
                                f"{estimate_record.get('resolved_value')}"
                            ),
                        })
            status = (
                "VERIFIED_DETERMINISTIC_DERIVATION_FROM_PROVISIONAL_INPUT"
                if dependency_is_provisional
                else "VERIFIED_DETERMINISTIC_DERIVATION"
            )
            record.update({
                "resolved_value": value,
                "status": status,
                "auto_apply": True,
                "detail": recipe["formula"],
                "depends_on_provisional_fields": [
                    field for field in recipe["inputs"]
                    if provenance.get(field) in {"model_estimate", "recipe_from_model_estimate"}
                ],
            })
            working_numeric[target] = value
            working_scalars[target] = value
            provenance[target] = (
                "recipe_from_model_estimate" if dependency_is_provisional else "deterministic_recipe"
            )
            progress = True
        unresolved = remaining
        return progress

    while unresolved and resolve_recipe_pass():
        pass

    for record_index, assist in estimate_items:
        record = validations[record_index]
        target = assist["target_field"]
        registry = missing_registry.get(target)
        if registry is None:
            record.update({
                "resolved_value": assist.get("proposed_value"),
                "status": "REJECTED_MODEL_ESTIMATE_TARGET_NOT_REGISTERED_MISSING_INPUT",
                "detail": "target is not an allowlisted still-missing preliminary closure field",
            })
            continue
        expected_unit = str(registry.get("target_unit") or "dimensionless")
        if _canonical_target_unit(assist.get("target_unit")) != expected_unit:
            record.update({
                "resolved_value": assist.get("proposed_value"),
                "status": "REJECTED_MODEL_ESTIMATE_UNIT_MISMATCH",
                "detail": f"expected_unit={expected_unit}; proposed_unit={assist.get('target_unit')}",
            })
            continue
        if target in working_scalars:
            record.update({
                "resolved_value": assist.get("proposed_value"),
                "status": "REJECTED_EXISTING_VALUE_CONFLICT",
                "detail": f"deterministic_or_recipe_value_already_available:{working_scalars[target]}",
            })
            continue

        proposed = assist.get("proposed_value")
        value_type = registry.get("value_type")
        if value_type == "enum":
            allowed_values = registry.get("allowed_values", [])
            if not isinstance(proposed, str) or proposed not in allowed_values:
                record.update({
                    "resolved_value": proposed,
                    "status": "REJECTED_MODEL_ESTIMATE_ENUM_VALUE",
                    "detail": f"allowed_values={allowed_values}",
                })
                continue
        elif value_type == "text":
            if not isinstance(proposed, str):
                record.update({
                    "resolved_value": proposed,
                    "status": "REJECTED_MODEL_ESTIMATE_TEXT_VALUE",
                    "detail": "preliminary text field requires a string",
                })
                continue
            proposed = proposed.strip()
            unsafe_text = (
                not proposed
                or len(proposed) > 160
                or any(ord(char) < 32 for char in proposed)
                or re.search(r"https?://|[A-Fa-f0-9]{64}|[\\/]", proposed) is not None
            )
            if unsafe_text:
                record.update({
                    "resolved_value": proposed,
                    "status": "REJECTED_MODEL_ESTIMATE_TEXT_GUARD",
                    "detail": "text must be 1-160 printable characters and cannot contain URLs, paths or hashes",
                })
                continue
        else:
            number = _finite_number(proposed)
            lower = _finite_number(assist.get("lower_bound"))
            upper = _finite_number(assist.get("upper_bound"))
            if number is None or lower is None or upper is None or lower > number or number > upper:
                record.update({
                    "resolved_value": proposed,
                    "status": "REJECTED_MODEL_ESTIMATE_INVALID_BOUNDS",
                    "detail": f"lower={lower}; value={number}; upper={upper}",
                })
                continue
            guard = registry.get("program_guard", {})
            guard_min = _finite_number(guard.get("minimum"))
            guard_max = _finite_number(guard.get("maximum"))
            if guard_min is not None and (number < guard_min or lower < guard_min):
                record.update({
                    "resolved_value": number,
                    "status": "REJECTED_MODEL_ESTIMATE_PROGRAM_GUARD",
                    "detail": f"minimum_guard={guard_min}; lower={lower}; value={number}",
                })
                continue
            if guard_max is not None and (number > guard_max or upper > guard_max):
                record.update({
                    "resolved_value": number,
                    "status": "REJECTED_MODEL_ESTIMATE_PROGRAM_GUARD",
                    "detail": f"maximum_guard={guard_max}; value={number}; upper={upper}",
                })
                continue
            proposed = number
        if assist.get("requested_preliminary_auto_apply") is not True:
            record.update({
                "resolved_value": proposed,
                "status": "PROVISIONAL_UNCERTAIN_REQUIRES_APPROVAL",
                "detail": "model did not request the registered preliminary-only auto-apply path",
            })
            continue
        record.update({
            "resolved_value": proposed,
            "status": "VERIFIED_PROVISIONAL_ENGINEERING_ESTIMATE",
            "auto_apply": True,
            "detail": assist["uncertainty_note"],
            "evidence_class": "J",
            "promotion_cap": "TYPE_SCREENING",
            "inference_basis": assist.get("inference_basis"),
            "assumptions": list(assist.get("assumptions", [])),
            "lower_bound": assist.get("lower_bound"),
            "upper_bound": assist.get("upper_bound"),
            "registered_allowed_values": (
                list(registry.get("allowed_values", [])) if value_type == "enum" else []
            ),
            "registry_id": registry.get("registry_id") if value_type == "enum" else None,
            "confidence": assist.get("confidence"),
            "sensitivity_note": assist.get("sensitivity_note"),
            "citations": list(assist.get("citations", [])),
            "warning": (
                "LLM last-resort engineering estimate; not an Aspen/user/direct standard/vendor value. "
                "Replace it with same-case evidence and replay before formal promotion."
            ),
        })
        working_scalars[target] = proposed
        provenance[target] = "model_estimate"
        if isinstance(proposed, (int, float)) and not isinstance(proposed, bool):
            working_numeric[target] = float(proposed)

    while unresolved and resolve_recipe_pass():
        pass
    for record_index, assist, recipe in unresolved:
        missing = [field for field in recipe["inputs"] if field not in working_numeric]
        validations[record_index]["detail"] = f"missing_recipe_inputs:{','.join(missing)}"
    return validations


def validate_terminal_selection_assists(
    assists: list[dict[str, Any]],
    assessments: list[dict[str, Any]],
    context_pack: dict[str, Any],
) -> list[dict[str, Any]]:
    """Validate bounded type choices; invented or unsupported rules stay nonblocking."""

    registry = {
        (
            str(item.get("rule_id", "")).strip(),
            str(item.get("selection_context_sha256", "")).strip().upper(),
        ): item
        for item in context_pack.get("terminal_type_rule_registry", [])
        if isinstance(item, dict)
    }
    assessment_status = {
        str(item.get("condition_id", "")).strip(): str(item.get("status", "")).strip()
        for item in assessments
        if isinstance(item, dict)
    }
    validations: list[dict[str, Any]] = []
    for assist in assists:
        record = {
            "assist_id": assist["assist_id"],
            "terminal_rule_id": assist["terminal_rule_id"],
            "condition_id": assist["condition_id"],
            "selection_context_sha256": assist["selection_context_sha256"],
            "recommended_type": None,
            "auto_apply": False,
            "status": "REJECTED_NONBLOCKING_UNKNOWN_RULE",
            "detail": "terminal rule is not present in the frozen registered rule set",
        }
        rule = registry.get((assist["terminal_rule_id"], assist["selection_context_sha256"]))
        if rule is None:
            validations.append(record)
            continue
        record["recommended_type"] = rule.get("recommended_type")
        if assist["condition_id"] != rule.get("condition_id"):
            record.update({
                "status": "REJECTED_NONBLOCKING_CONDITION_RULE_MISMATCH",
                "detail": "condition_id does not belong to the selected registered terminal rule",
            })
            validations.append(record)
            continue
        if rule.get("current_terminal_status") != "DEFAULTED_TERMINAL_TYPE_SELECTED":
            record.update({
                "status": "REJECTED_NONBLOCKING_CURRENT_SELECTION_NOT_DEFAULTED",
                "detail": "API condition selection may upgrade only a registered deterministic default",
            })
            validations.append(record)
            continue
        if assessment_status.get(assist["condition_id"]) != "supported":
            record.update({
                "status": "REJECTED_NONBLOCKING_CONDITION_NOT_SUPPORTED",
                "detail": "the same step must mark the registered condition as supported",
            })
            validations.append(record)
            continue
        record.update({
            "status": "VERIFIED_REGISTERED_CONDITION_SELECTION",
            "auto_apply": True,
            "detail": rule.get("condition_text"),
        })
        validations.append(record)

    by_context: dict[str, list[dict[str, Any]]] = {}
    for record in validations:
        if record["status"] == "VERIFIED_REGISTERED_CONDITION_SELECTION":
            by_context.setdefault(record["selection_context_sha256"], []).append(record)
    for context_sha256, records in by_context.items():
        selected_rules = {record["terminal_rule_id"] for record in records}
        if len(selected_rules) <= 1:
            for duplicate in records[1:]:
                duplicate.update({
                    "status": "DUPLICATE_VERIFIED_REGISTERED_SELECTION",
                    "auto_apply": False,
                    "detail": f"duplicate registered terminal selection for {context_sha256}",
                })
            continue
        for record in records:
            record.update({
                "status": "REJECTED_NONBLOCKING_TERMINAL_SELECTION_CONFLICT",
                "auto_apply": False,
                "detail": f"multiple registered terminal rules selected for {context_sha256}",
            })
    return validations


def _nonempty_output_sections(validated: dict[str, Any]) -> set[str]:
    sections: set[str] = set()
    if str(validated.get("summary", "")).strip():
        sections.add("summary")
    for section in (
        "proposed_changes", "condition_assessments", "terminal_selection_assists", "calculation_assists",
        "retrieval_plan", "audit_findings",
    ):
        if validated.get(section):
            sections.add(section)
    if validated.get("ambiguity_decision") is not None:
        sections.add("ambiguity_decision")
    return sections


def _validate_output_composition(
    value: Any,
    validated: dict[str, Any],
    known_ids: set[str],
) -> dict[str, Any]:
    """Validate the AI frame and deterministically fill omitted presentation-only blocks."""
    if not isinstance(value, dict):
        raise ValueError("output_composition 必须是对象。")
    value = dict(value)
    value.setdefault("title", "")
    value.setdefault("blocks", [])
    _require_exact_keys(value, OUTPUT_COMPOSITION_KEYS, "output_composition")
    blocks = value.get("blocks")
    if not isinstance(blocks, list):
        raise ValueError("output_composition.blocks 必须是数组。")
    if len(blocks) > 16:
        raise ValueError("output_composition.blocks 最多允许 16 个 AI 操作块。")

    expected_sections = _nonempty_output_sections(validated)
    seen_ids: set[str] = set()
    seen_sections: set[str] = set()
    normalized_blocks: list[dict[str, Any]] = []
    for index, item in enumerate(blocks):
        label = f"output_composition.blocks[{index}]"
        if not isinstance(item, dict):
            raise ValueError(f"{label} 必须是对象。")
        _require_exact_keys(item, OUTPUT_COMPOSITION_BLOCK_KEYS, label)
        block_id = _string(item.get("block_id"), f"{label}.block_id")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", block_id):
            raise ValueError(f"{label}.block_id 只能包含字母、数字、下划线和连字符。")
        if block_id in seen_ids:
            raise ValueError(f"output_composition 出现重复 block_id：{block_id}")
        seen_ids.add(block_id)

        section_ref = _string(item.get("section_ref"), f"{label}.section_ref")
        if section_ref not in OUTPUT_SECTION_OPERATIONS:
            raise ValueError(f"{label}.section_ref 无效：{section_ref}")
        if section_ref not in expected_sections:
            raise ValueError(f"{label} 引用了空的 step output 段：{section_ref}")
        if section_ref in seen_sections:
            raise ValueError(f"output_composition 重复组织同一段：{section_ref}")
        seen_sections.add(section_ref)

        operation = _string(item.get("operation"), f"{label}.operation")
        expected_operation = OUTPUT_SECTION_OPERATIONS[section_ref]
        if operation != expected_operation:
            raise ValueError(
                f"{label}.operation 必须与 section_ref 对应："
                f"expected={expected_operation}, actual={operation}"
            )
        normalized_blocks.append({
            "block_id": block_id,
            "operation": operation,
            "section_ref": section_ref,
            "heading": _string(item.get("heading"), f"{label}.heading"),
            "citations": _citations(item.get("citations"), known_ids, f"{label}.citations"),
        })

    missing = sorted(expected_sections - seen_sections)
    default_citation = (
        "deterministic_result"
        if "deterministic_result" in known_ids
        else (sorted(known_ids)[0] if known_ids else None)
    )
    for section_ref in missing:
        block_id = f"auto_{section_ref}"
        suffix = 2
        while block_id in seen_ids:
            block_id = f"auto_{section_ref}_{suffix}"
            suffix += 1
        seen_ids.add(block_id)
        seen_sections.add(section_ref)
        normalized_blocks.append({
            "block_id": block_id,
            "operation": OUTPUT_SECTION_OPERATIONS[section_ref],
            "section_ref": section_ref,
            "heading": section_ref.replace("_", " ").title(),
            "citations": [default_citation] if default_citation else [],
        })
    if seen_sections - expected_sections:
        raise ValueError("output_composition 引用了不存在的 AI 输出段。")
    raw_title = value.get("title")
    title = (
        _string(raw_title, "output_composition.title")
        if isinstance(raw_title, str) and raw_title.strip()
        else ("AI assisted equipment reasoning" if normalized_blocks else "")
    )
    return {"title": title, "blocks": normalized_blocks}


def deterministic_only_timeline(deterministic_result: dict[str, Any]) -> dict[str, Any]:
    timeline: dict[str, Any] = {
        "schema": INTERLEAVED_TIMELINE_SCHEMA,
        "title": "程序计算结果",
        "deterministic_result_preserved": True,
        "ai_controls_intermediate_composition": False,
        "steps": [{
            "step_id": "program_deterministic_initial",
            "actor": "program",
            "operation": "deterministic_calculation",
            "status": "COMPLETED_AUTHORITATIVE",
            "authoritative": True,
            "immutable": True,
            "result_ref": "deterministic_result",
            "result_sha256": _canonical_sha256(deterministic_result),
        }],
    }
    timeline["timeline_sha256"] = _canonical_sha256(timeline)
    return timeline


def interleaved_timeline(
    context_pack: dict[str, Any],
    validated: dict[str, Any],
    *,
    replay_required: bool,
    calculation_validation: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    composition = validated["output_composition"]
    steps: list[dict[str, Any]] = [{
        "step_id": "program_deterministic_initial",
        "actor": "program",
        "operation": "deterministic_calculation",
        "status": "COMPLETED_AUTHORITATIVE",
        "authoritative": True,
        "immutable": True,
        "result_ref": "deterministic_result",
        "result_sha256": context_pack["deterministic_result_sha256"],
    }]
    for block in composition["blocks"]:
        block_status = "COMPLETED_VALIDATED"
        if block["section_ref"] == "calculation_assists" and any(
            item.get("status") in {
                "REJECTED_NONBLOCKING",
                "REJECTED_NONBLOCKING_WRONG_SCOPE",
                "REJECTED_EXISTING_VALUE_CONFLICT",
                "REJECTED_DERIVATION_CONFLICT",
                "PROVISIONAL_UNCERTAIN_REQUIRES_APPROVAL",
            }
            for item in (calculation_validation or [])
            if isinstance(item, dict)
        ):
            block_status = "COMPLETED_WITH_ITEM_DIAGNOSTICS"
        steps.append({
            "step_id": f"ai_{block['block_id']}",
            "actor": "ai",
            "operation": block["operation"],
            "status": block_status,
            "authoritative": False,
            "immutable": False,
            "heading": block["heading"],
            "payload_ref": f"step_output.{block['section_ref']}",
            "citations": block["citations"],
        })
    if replay_required:
        steps.append({
            "step_id": "program_deterministic_recalculation",
            "actor": "program",
            "operation": "deterministic_recalculation",
            "status": "PENDING_EXPLICIT_APPROVAL",
            "authoritative": True,
            "immutable": True,
            "result_ref": "deterministic_recalculation",
            "result_sha256": None,
        })
    timeline: dict[str, Any] = {
        "schema": INTERLEAVED_TIMELINE_SCHEMA,
        "title": composition["title"] or "程序计算结果",
        "deterministic_result_preserved": True,
        "ai_controls_intermediate_composition": True,
        "steps": steps,
    }
    timeline["timeline_sha256"] = _canonical_sha256(timeline)
    return timeline


def materialize_recalculation_timeline(
    timeline: dict[str, Any],
    recalculation: dict[str, Any],
) -> dict[str, Any]:
    copied = json.loads(json.dumps(timeline, ensure_ascii=False))
    copied.pop("timeline_sha256", None)
    replay_steps = [
        step for step in copied.get("steps", [])
        if isinstance(step, dict) and step.get("step_id") == "program_deterministic_recalculation"
    ]
    if replay_steps:
        replay_steps[0]["status"] = "COMPLETED_AUTHORITATIVE"
        replay_steps[0]["result_sha256"] = _canonical_sha256(recalculation)
    else:
        copied.setdefault("steps", []).append({
            "step_id": "program_deterministic_recalculation",
            "actor": "program",
            "operation": "deterministic_recalculation",
            "status": "COMPLETED_AUTHORITATIVE",
            "authoritative": True,
            "immutable": True,
            "result_ref": "deterministic_recalculation",
            "result_sha256": _canonical_sha256(recalculation),
        })
    copied["timeline_sha256"] = _canonical_sha256(copied)
    return copied


def validate_step_output(output: dict[str, Any], context_pack: dict[str, Any]) -> dict[str, Any]:
    """Validate an external or built-in model response against one immutable context pack."""
    _verify_context_pack(context_pack)
    actual_keys = set(output)
    missing_keys = sorted(STEP_OUTPUT_REQUIRED_KEYS - actual_keys)
    extra_keys = sorted(actual_keys - STEP_OUTPUT_KEYS)
    if missing_keys or extra_keys:
        raise ValueError(
            f"LLM step output 字段必须包含 {sorted(STEP_OUTPUT_REQUIRED_KEYS)}，且只能使用 {sorted(STEP_OUTPUT_KEYS)}；"
            f"缺少 {missing_keys}，多出 {extra_keys}。"
        )
    if output.get("schema") != STEP_OUTPUT_SCHEMA:
        raise ValueError(f"LLM step output schema 必须是 {STEP_OUTPUT_SCHEMA}。")
    injection_point = _string(output.get("injection_point"), "injection_point")
    if injection_point != context_pack.get("injection_point"):
        raise ValueError("LLM step output 的 injection_point 与 prepared context 不一致。")
    context_hash = _string(output.get("context_sha256"), "context_sha256")
    if context_hash != context_pack.get("context_sha256"):
        raise ValueError("LLM step output 的 context_sha256 与 prepared context 不一致。")
    policy = INJECTION_POINT_POLICIES[injection_point]
    sources = context_pack.get("sources", [])
    known_ids = {
        str(item.get("context_id"))
        for item in sources
        if isinstance(item, dict) and str(item.get("context_id", "")).strip()
    }
    normalized: dict[str, Any] = {
        "schema": STEP_OUTPUT_SCHEMA,
        "injection_point": injection_point,
        "context_sha256": context_hash,
        "summary": _string(output.get("summary"), "summary", allow_empty=True),
        "citations": [],
        "proposed_changes": [],
        "condition_assessments": [],
        "terminal_selection_assists": [],
        "calculation_assists": [],
        "retrieval_plan": [],
        "ambiguity_decision": None,
        "audit_findings": [],
        "output_composition": {},
    }

    citations = output.get("citations")
    if not isinstance(citations, list):
        raise ValueError("citations 必须是数组。")
    for index, item in enumerate(citations):
        if not isinstance(item, dict):
            raise ValueError(f"citations[{index}] 必须是对象。")
        _require_exact_keys(item, {"context_id", "claim"}, f"citations[{index}]")
        context_id = _string(item.get("context_id"), f"citations[{index}].context_id")
        if context_id not in known_ids:
            raise ValueError(f"citations[{index}] 引用了未知 context_id：{context_id}")
        normalized["citations"].append({
            "context_id": context_id,
            "claim": _string(item.get("claim"), f"citations[{index}].claim"),
        })

    changes = output.get("proposed_changes")
    if not isinstance(changes, list):
        raise ValueError("proposed_changes 必须是数组。")
    if changes and "proposed_changes" not in policy["sections"]:
        raise ValueError(f"{injection_point} 不允许 proposed_changes。")
    for index, item in enumerate(changes):
        if not isinstance(item, dict):
            raise ValueError(f"proposed_changes[{index}] 必须是对象。")
        _require_exact_keys(item, {"field", "value", "reason", "citations"}, f"proposed_changes[{index}]")
        field = _string(item.get("field"), f"proposed_changes[{index}].field")
        if field == "candidate_model":
            raise ValueError("candidate_model 禁止自由生成；候选只能通过 ambiguity_decision 引用确定性 candidate_id。")
        if field in HARD_PARAMETER_FIELDS or field not in policy["change_fields"]:
            raise ValueError(f"{injection_point} 不允许修改字段 {field}。")
        value = _string(item.get("value"), f"proposed_changes[{index}].value")
        if field == "phase" and value not in CANONICAL_PHASES:
            raise ValueError(f"phase 只能是：{', '.join(sorted(CANONICAL_PHASES))}。")
        normalized["proposed_changes"].append({
            "field": field,
            "value": value,
            "reason": _string(item.get("reason"), f"proposed_changes[{index}].reason"),
            "citations": _citations(item.get("citations"), known_ids, f"proposed_changes[{index}].citations"),
        })

    assessments = output.get("condition_assessments")
    if not isinstance(assessments, list):
        raise ValueError("condition_assessments 必须是数组。")
    if assessments and "condition_assessments" not in policy["sections"]:
        raise ValueError(f"{injection_point} 不允许 condition_assessments。")
    condition_registry = {
        str(item.get("condition_id")): item
        for item in context_pack.get("condition_registry", [])
        if isinstance(item, dict) and str(item.get("condition_id", "")).strip()
    }
    if assessments and not condition_registry:
        raise ValueError("确定性上下文没有 condition_registry；condition_assessments 必须为空。")
    for index, item in enumerate(assessments):
        if not isinstance(item, dict):
            raise ValueError(f"condition_assessments[{index}] 必须是对象。")
        _require_exact_keys(item, {"condition_id", "status", "reason", "citations"}, f"condition_assessments[{index}]")
        status = _string(item.get("status"), f"condition_assessments[{index}].status")
        if status not in {"supported", "not_supported", "unknown"}:
            raise ValueError("condition assessment status 只能是 supported/not_supported/unknown。")
        condition_id = _string(item.get("condition_id"), f"condition_assessments[{index}].condition_id")
        if condition_id not in condition_registry:
            raise ValueError(f"condition_assessments[{index}] 引用了未知 condition_id：{condition_id}")
        normalized["condition_assessments"].append({
            "condition_id": condition_id,
            "status": status,
            "reason": _string(item.get("reason"), f"condition_assessments[{index}].reason"),
            "citations": _citations(item.get("citations"), known_ids, f"condition_assessments[{index}].citations"),
        })

    terminal_assists = output.get("terminal_selection_assists", [])
    if not isinstance(terminal_assists, list):
        raise ValueError("terminal_selection_assists must be an array.")
    if terminal_assists and "terminal_selection_assists" not in policy["sections"]:
        raise ValueError(f"{injection_point} does not allow terminal_selection_assists.")
    if len(terminal_assists) > 16:
        raise ValueError("terminal_selection_assists 最多允许 16 条。")
    seen_terminal_assist_ids: set[str] = set()
    for index, item in enumerate(terminal_assists):
        label = f"terminal_selection_assists[{index}]"
        if not isinstance(item, dict):
            raise ValueError(f"{label} must be an object.")
        _require_exact_keys(item, TERMINAL_SELECTION_ASSIST_KEYS, label)
        assist_id = _string(item.get("assist_id"), f"{label}.assist_id")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", assist_id):
            raise ValueError(f"{label}.assist_id has an invalid format.")
        if assist_id in seen_terminal_assist_ids:
            raise ValueError(f"duplicate terminal selection assist_id: {assist_id}")
        seen_terminal_assist_ids.add(assist_id)
        selection_context_sha256 = _string(
            item.get("selection_context_sha256"),
            f"{label}.selection_context_sha256",
        ).upper()
        if not re.fullmatch(r"[A-F0-9]{64}", selection_context_sha256):
            raise ValueError(f"{label}.selection_context_sha256 has an invalid format.")
        normalized["terminal_selection_assists"].append({
            "assist_id": assist_id,
            "terminal_rule_id": _string(item.get("terminal_rule_id"), f"{label}.terminal_rule_id"),
            "condition_id": _string(item.get("condition_id"), f"{label}.condition_id"),
            "selection_context_sha256": selection_context_sha256,
            "reason": _string(item.get("reason"), f"{label}.reason"),
            "citations": _citations(item.get("citations"), known_ids, f"{label}.citations"),
        })

    calculation_assists = output.get("calculation_assists")
    if not isinstance(calculation_assists, list):
        raise ValueError("calculation_assists must be an array.")
    if calculation_assists and "calculation_assists" not in policy["sections"]:
        raise ValueError(f"{injection_point} does not allow calculation_assists.")
    if len(calculation_assists) > 64:
        raise ValueError("calculation_assists 最多允许 64 条。")
    seen_assist_ids: set[str] = set()
    for index, item in enumerate(calculation_assists):
        label = f"calculation_assists[{index}]"
        if not isinstance(item, dict):
            raise ValueError(f"{label} must be an object.")
        _require_keys_with_optional(
            item,
            CALCULATION_ASSIST_KEYS,
            MODEL_INFERENCE_ASSIST_KEYS,
            label,
        )
        assist_id = _string(item.get("assist_id"), f"{label}.assist_id")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", assist_id):
            raise ValueError(f"{label}.assist_id has an invalid format.")
        if assist_id in seen_assist_ids:
            raise ValueError(f"duplicate calculation assist_id: {assist_id}")
        seen_assist_ids.add(assist_id)
        method = _string(item.get("method"), f"{label}.method")
        if method not in {"deterministic_recipe", "model_inference"}:
            raise ValueError(f"{label}.method is invalid.")
        certainty = _string(item.get("certainty"), f"{label}.certainty")
        if certainty not in {"certain", "uncertain"}:
            raise ValueError(f"{label}.certainty is invalid.")
        recipe_id = item.get("recipe_id")
        proposed_value = item.get("proposed_value")
        uncertainty_note = item.get("uncertainty_note")
        inference_basis = None
        assumptions: list[str] = []
        lower_bound = None
        upper_bound = None
        confidence = None
        sensitivity_note = None
        requested_preliminary_auto_apply = False
        if method == "deterministic_recipe":
            if not isinstance(recipe_id, str) or not recipe_id.strip():
                raise ValueError(f"{label}.recipe_id is required for deterministic_recipe.")
            if certainty != "certain":
                raise ValueError(f"{label}.certainty must be certain for deterministic_recipe.")
            # Compatible/smaller models sometimes perform the arithmetic even
            # when asked only to select a recipe.  Never consume that number:
            # discard it and let the deterministic recipe implementation own
            # the value and all downstream replay.
            proposed_value = None
            uncertainty_note = None
        else:
            missing_inference_fields = MODEL_INFERENCE_ASSIST_KEYS - set(item)
            if missing_inference_fields:
                raise ValueError(
                    f"{label} model_inference 缺少结构化可靠性字段："
                    f"{sorted(missing_inference_fields)}。"
                )
            if recipe_id is not None:
                raise ValueError(f"{label}.recipe_id must be null for model_inference.")
            if isinstance(proposed_value, bool) or not isinstance(proposed_value, (int, float, str)):
                raise ValueError(
                    f"{label}.proposed_value must be a finite number, registered enum, or constrained text string."
                )
            if isinstance(proposed_value, (int, float)):
                proposed_value = _finite_number(proposed_value)
                if proposed_value is None:
                    raise ValueError(f"{label}.proposed_value must be finite.")
            else:
                proposed_value = proposed_value.strip()
                if not proposed_value:
                    raise ValueError(f"{label}.proposed_value string cannot be empty.")
            if certainty != "uncertain":
                raise ValueError(f"{label}.certainty must be uncertain for model_inference.")
            uncertainty_note = _string(uncertainty_note, f"{label}.uncertainty_note")
            inference_basis = _string(item.get("inference_basis"), f"{label}.inference_basis")
            if inference_basis not in {
                "unit_conversion", "same_case_fact_interpretation", "engineering_requirement",
                "registered_range_interpolation", "conservative_screening_assumption",
            }:
                raise ValueError(f"{label}.inference_basis is invalid.")
            raw_assumptions = item.get("assumptions")
            if not isinstance(raw_assumptions, list) or not raw_assumptions:
                raise ValueError(f"{label}.assumptions must be a nonempty array.")
            assumptions = [
                _string(value, f"{label}.assumptions[{assumption_index}]")
                for assumption_index, value in enumerate(raw_assumptions)
            ]
            lower_bound = item.get("lower_bound")
            upper_bound = item.get("upper_bound")
            if isinstance(proposed_value, (int, float)):
                lower_bound = _finite_number(lower_bound)
                upper_bound = _finite_number(upper_bound)
                if lower_bound is None or upper_bound is None:
                    raise ValueError(f"{label} numeric model_inference requires finite lower/upper bounds.")
            elif lower_bound is not None or upper_bound is not None:
                raise ValueError(f"{label} string model_inference requires null lower/upper bounds.")
            confidence = _string(item.get("confidence"), f"{label}.confidence")
            if confidence not in {"low", "medium"}:
                raise ValueError(f"{label}.confidence must be low or medium.")
            sensitivity_note = _string(item.get("sensitivity_note"), f"{label}.sensitivity_note")
            requested_preliminary_auto_apply = item.get("requested_preliminary_auto_apply")
            if not isinstance(requested_preliminary_auto_apply, bool):
                raise ValueError(f"{label}.requested_preliminary_auto_apply must be boolean.")
        normalized["calculation_assists"].append({
            "assist_id": assist_id,
            "target_field": _string(item.get("target_field"), f"{label}.target_field"),
            "target_unit": _string(item.get("target_unit"), f"{label}.target_unit"),
            "method": method,
            "recipe_id": recipe_id.strip() if isinstance(recipe_id, str) else None,
            "proposed_value": proposed_value,
            "certainty": certainty,
            "uncertainty_note": uncertainty_note,
            "reason": _string(item.get("reason"), f"{label}.reason"),
            "citations": _citations(item.get("citations"), known_ids, f"{label}.citations"),
            "inference_basis": inference_basis,
            "assumptions": assumptions,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "confidence": confidence,
            "sensitivity_note": sensitivity_note,
            "requested_preliminary_auto_apply": requested_preliminary_auto_apply,
        })

    retrieval_plan = output.get("retrieval_plan")
    if not isinstance(retrieval_plan, list):
        raise ValueError("retrieval_plan 必须是数组。")
    if retrieval_plan and "retrieval_plan" not in policy["sections"]:
        raise ValueError(f"{injection_point} 不允许 retrieval_plan。")
    for index, item in enumerate(retrieval_plan):
        if not isinstance(item, dict):
            raise ValueError(f"retrieval_plan[{index}] 必须是对象。")
        _require_exact_keys(item, {"query", "scope", "reason", "citations"}, f"retrieval_plan[{index}]")
        scope = _string(item.get("scope"), f"retrieval_plan[{index}].scope")
        if scope not in {"minimum", "routed", "full_family", "full_bundle"}:
            raise ValueError("retrieval_plan scope 无效。")
        normalized["retrieval_plan"].append({
            "query": _string(item.get("query"), f"retrieval_plan[{index}].query"),
            "scope": scope,
            "reason": _string(item.get("reason"), f"retrieval_plan[{index}].reason"),
            "citations": _citations(item.get("citations"), known_ids, f"retrieval_plan[{index}].citations"),
        })

    ambiguity = output.get("ambiguity_decision")
    if ambiguity is not None:
        if "ambiguity_decision" not in policy["sections"]:
            raise ValueError(f"{injection_point} 不允许 ambiguity_decision。")
        if not isinstance(ambiguity, dict):
            raise ValueError("ambiguity_decision 必须是对象或 null。")
        ambiguity_keys = {
            "status", "selected_candidate_id", "selected_designation",
            "selection_feature_vector_sha256", "selection_context_sha256",
            "reason", "citations",
        }
        _require_exact_keys(ambiguity, ambiguity_keys, "ambiguity_decision")
        status = _string(ambiguity.get("status"), "ambiguity_decision.status")
        if status not in {"retain_most_general", "candidate_reference", "needs_evidence"}:
            raise ValueError("ambiguity_decision.status 无效。")
        selected_fields = (
            "selected_candidate_id", "selected_designation",
            "selection_feature_vector_sha256", "selection_context_sha256",
        )
        selected = {key: ambiguity.get(key) for key in selected_fields}
        if status == "candidate_reference":
            if not all(isinstance(value, str) and value.strip() for value in selected.values()):
                raise ValueError("candidate_reference 必须给出 candidate_id、designation 和两个上下文哈希。")
            candidate_id = str(selected["selected_candidate_id"]).strip()
            registry = [
                item
                for item in context_pack.get("candidate_registry", [])
                if isinstance(item, dict) and str(item.get("candidate_id")) == candidate_id
            ]
            if not registry:
                raise ValueError(f"candidate_reference 不在确定性候选注册表中：{candidate_id}")
            actual = {
                key: (str(value).strip().upper() if key.endswith("sha256") else str(value).strip())
                for key, value in selected.items()
            }
            expected_records = [
                {
                    "selected_candidate_id": candidate_id,
                    "selected_designation": str(candidate.get("designation", "")).strip(),
                    "selection_feature_vector_sha256": str(candidate.get("selection_feature_vector_sha256", "")).strip().upper(),
                    "selection_context_sha256": str(candidate.get("selection_context_sha256", "")).strip().upper(),
                }
                for candidate in registry
            ]
            if actual not in expected_records:
                raise ValueError("candidate_reference 与确定性候选 designation/上下文哈希不一致。")
            selected = actual
        elif any(value not in (None, "") for value in selected.values()):
            raise ValueError("非 candidate_reference 状态不得携带候选身份或哈希。")
        normalized["ambiguity_decision"] = {
            "status": status,
            **selected,
            "reason": _string(ambiguity.get("reason"), "ambiguity_decision.reason"),
            "citations": _citations(ambiguity.get("citations"), known_ids, "ambiguity_decision.citations"),
        }

    findings = output.get("audit_findings")
    if not isinstance(findings, list):
        raise ValueError("audit_findings 必须是数组。")
    if findings and "audit_findings" not in policy["sections"]:
        raise ValueError(f"{injection_point} 不允许 audit_findings。")
    for index, item in enumerate(findings):
        if not isinstance(item, dict):
            raise ValueError(f"audit_findings[{index}] 必须是对象。")
        _require_exact_keys(item, {"finding_id", "severity", "message", "citations"}, f"audit_findings[{index}]")
        severity = _string(item.get("severity"), f"audit_findings[{index}].severity")
        if severity not in {"info", "warning", "error"}:
            raise ValueError("audit finding severity 只能是 info/warning/error。")
        normalized["audit_findings"].append({
            "finding_id": _string(item.get("finding_id"), f"audit_findings[{index}].finding_id"),
            "severity": severity,
            "message": _string(item.get("message"), f"audit_findings[{index}].message"),
            "citations": _citations(item.get("citations"), known_ids, f"audit_findings[{index}].citations"),
        })
    normalized["output_composition"] = _validate_output_composition(
        output.get("output_composition"),
        normalized,
        known_ids,
    )
    return normalized


_PROVIDER_UNSUPPORTED_SCHEMA_KEYWORDS = {"allOf", "if", "then", "else", "oneOf"}
_PROVIDER_SCHEMA_METADATA_KEYS = {"$schema", "$id", "title"}


def _provider_safe_schema(value: Any) -> Any:
    """Derive an OpenAI Structured-Outputs-safe schema without weakening local validation.

    The full schema remains in ``output_contract.json_schema`` and is always
    enforced by :func:`validate_step_output` after the provider returns.  This
    derivative is only the provider-side generation envelope: conditional
    composition is removed, ``oneOf`` is represented by supported ``anyOf``,
    and single-value ``const`` constraints become single-value enums.
    """
    if isinstance(value, list):
        return [_provider_safe_schema(item) for item in value]
    if not isinstance(value, dict):
        return value

    safe: dict[str, Any] = {}
    for key, item in value.items():
        if key in _PROVIDER_SCHEMA_METADATA_KEYS:
            continue
        if key in {"if", "then", "else"}:
            continue
        if key == "allOf":
            # The current full schema uses allOf only for a phase-dependent
            # value enum.  Local post-validation retains that exact gate.
            continue
        if key == "oneOf":
            safe["anyOf"] = _provider_safe_schema(item)
            continue
        if key == "const":
            safe["enum"] = [_provider_safe_schema(item)]
            continue
        safe[key] = _provider_safe_schema(item)

    properties = safe.get("properties")
    if safe.get("type") == "object" and isinstance(properties, dict):
        # Strict Structured Outputs requires every property to be required and
        # objects to close over additional keys.  Optional values are modeled
        # explicitly with a nullable type/anyOf branch in the full schema.
        safe["required"] = list(properties)
        safe["additionalProperties"] = False
    return safe


def _step_output_contract(injection_point: str, context_sha256: str) -> dict[str, Any]:
    policy = INJECTION_POINT_POLICIES[injection_point]
    conditional_sections = {
        "proposed_changes",
        "condition_assessments",
        "terminal_selection_assists",
        "calculation_assists",
        "retrieval_plan",
        "ambiguity_decision",
        "audit_findings",
    }
    if not STEP_SCHEMA_PATH.is_file():
        raise ValueError(f"LLM step schema 不存在：{STEP_SCHEMA_PATH}")
    json_schema = json.loads(STEP_SCHEMA_PATH.read_text(encoding="utf-8"))
    json_schema = json.loads(json.dumps(json_schema, ensure_ascii=False))
    properties = json_schema.setdefault("properties", {})
    properties["injection_point"] = {"const": injection_point}
    properties["context_sha256"] = {"const": context_sha256}
    provider_json_schema = _provider_safe_schema(json_schema)
    return {
        "schema": STEP_OUTPUT_SCHEMA,
        "json_schema": json_schema,
        "provider_json_schema": provider_json_schema,
        "empty_template": {
            "schema": STEP_OUTPUT_SCHEMA,
            "injection_point": injection_point,
            "context_sha256": context_sha256,
            "summary": "",
            "citations": [],
            "proposed_changes": [],
            "condition_assessments": [],
            "terminal_selection_assists": [],
            "calculation_assists": [],
            "retrieval_plan": [],
            "ambiguity_decision": None,
            "audit_findings": [],
            "output_composition": {"title": "", "blocks": []},
        },
        "required_top_level_keys": sorted(STEP_OUTPUT_REQUIRED_KEYS),
        "allowed_sections": sorted(policy["sections"]),
        "sections_that_must_be_empty": sorted(conditional_sections - policy["sections"]),
        "empty_value_by_section": {
            "proposed_changes": [],
            "condition_assessments": [],
            "terminal_selection_assists": [],
            "calculation_assists": [],
            "retrieval_plan": [],
            "ambiguity_decision": None,
            "audit_findings": [],
        },
        "allowed_change_fields": sorted(policy["change_fields"]),
        "forbidden_field_classes": ["numeric_overwrite", "unit_overwrite", "pressure_basis", "evidence_state", "model_status", "final_model"],
        "calculation_assistance_policy": (
            "Exhaust allowlisted deterministic recipes first; the program computes and verifies them and resolves "
            "multi-step dependencies. Remaining fields may use only missing_input_registry. A model_inference must "
            "carry structured basis, assumptions, bounds, confidence and sensitivity. After program validation it may "
            "auto-apply only to preliminary selection as visible J/provisional input capped at TYPE_SCREENING. It never "
            "overwrites an existing value, and a later deterministic calculation always wins."
        ),
        "terminal_selection_policy": (
            "Only when the deterministic terminal selection is DEFAULTED may the model cite a frozen registered "
            "condition, reference its exact terminal rule and selection-context hash, and request a program replay. "
            "Free equipment-type text is forbidden; unsupported or invented rules retain the deterministic default."
        ),
        "candidate_policy": (
            "candidate_model text is forbidden; ambiguity_resolution may only reference an existing "
            "candidate_id/designation with exact selection feature/context hashes"
        ),
        "citation_policy": "every nested claim must cite a context_id from the immutable context pack",
        "output_composition_policy": (
            "AI owns the order and headings of its intermediate operation blocks; the program inserts immutable "
            "initial/recalculation result anchors outside those blocks and never lets the model rewrite them"
        ),
    }


def hybrid_prepare(
    deterministic_result: dict[str, Any],
    kg_result: dict[str, Any],
    injection_point: str = "audit",
    context_scope: str = "minimum",
) -> dict[str, Any]:
    context_pack = build_context_pack(
        deterministic_result,
        kg_result,
        injection_point,
        context_scope,
    )
    current_revision = authority_revision.current_authority_revision()
    prepared: dict[str, Any] = {
        "schema": PREPARED_SCHEMA,
        "injection_point": injection_point,
        "deterministic_authority": True,
        "authority_revision": current_revision,
        "context_pack": context_pack,
        "output_contract": _step_output_contract(injection_point, context_pack["context_sha256"]),
    }
    prepared["prepared_sha256"] = _canonical_sha256(prepared)
    return prepared


def with_replay_contract(prepared: dict[str, Any], replay_contract: dict[str, Any]) -> dict[str, Any]:
    """Bind a deterministic replay recipe into an already verified prepared package."""
    _verify_prepared(prepared)
    if not isinstance(replay_contract, dict):
        raise ValueError("replay_contract 必须是对象。")
    replay_revision = authority_revision.validate_authority_revision(
        replay_contract.get("authority_revision")
    )
    if replay_revision != prepared.get("authority_revision"):
        raise ValueError("replay_contract 与 prepared 的 authority_revision 不一致。")
    copied = json.loads(json.dumps(prepared, ensure_ascii=False))
    copied.pop("prepared_sha256", None)
    copied["replay_contract"] = json.loads(json.dumps(replay_contract, ensure_ascii=False))
    copied["prepared_sha256"] = _canonical_sha256(copied)
    return copied


def _verify_prepared(prepared: dict[str, Any]) -> None:
    if prepared.get("schema") != PREPARED_SCHEMA:
        raise ValueError(f"prepared schema 必须是 {PREPARED_SCHEMA}。")
    claimed = _string(prepared.get("prepared_sha256"), "prepared_sha256")
    unhashed = {key: value for key, value in prepared.items() if key != "prepared_sha256"}
    actual = _canonical_sha256(unhashed)
    if claimed != actual:
        raise ValueError(f"prepared 哈希不一致：expected={claimed}, actual={actual}")
    embedded_revision = authority_revision.validate_authority_revision(
        prepared.get("authority_revision")
    )
    current_revision = authority_revision.current_authority_revision()
    if embedded_revision != current_revision:
        raise ValueError(
            "prepared 的 authority_revision 与当前确定性运行时不一致："
            f"expected={embedded_revision['authority_revision_sha256']}, "
            f"actual={current_revision['authority_revision_sha256']}"
        )
    context_pack = prepared.get("context_pack")
    if not isinstance(context_pack, dict):
        raise ValueError("prepared.context_pack 必须是对象。")
    _verify_context_pack(context_pack)
    if prepared.get("injection_point") != context_pack.get("injection_point"):
        raise ValueError("prepared injection_point 与 context pack 不一致。")
    replay = prepared.get("replay_contract")
    if replay is not None:
        if not isinstance(replay, dict) or replay.get("schema") != "equipment-design-deterministic-replay-v1":
            raise ValueError("prepared.replay_contract schema 无效。")
        replay_revision = authority_revision.validate_authority_revision(
            replay.get("authority_revision")
        )
        if replay_revision != embedded_revision:
            raise ValueError("prepared.replay_contract 的 authority_revision 不一致。")
        claimed_result_hash = str(replay.get("deterministic_result_sha256", "")).strip().upper()
        if claimed_result_hash != str(context_pack.get("deterministic_result_sha256", "")).strip().upper():
            raise ValueError("replay_contract 的确定性结果哈希与 context pack 不一致。")


def hybrid_continue(prepared: dict[str, Any], step_output: dict[str, Any]) -> dict[str, Any]:
    _verify_prepared(prepared)
    context_pack = prepared["context_pack"]
    validated = validate_step_output(step_output, context_pack)
    calculation_validation = validate_calculation_assists(
        validated["calculation_assists"],
        context_pack,
    )
    terminal_selection_validation = validate_terminal_selection_assists(
        validated["terminal_selection_assists"],
        validated["condition_assessments"],
        context_pack,
    )
    verified_calculation_inputs = {
        item["target_field"]: item["resolved_value"]
        for item in calculation_validation
        if item["status"] in {
            "VERIFIED_DETERMINISTIC_DERIVATION",
            "VERIFIED_DETERMINISTIC_DERIVATION_FROM_PROVISIONAL_INPUT",
        }
        and item["auto_apply"] is True
    }
    verified_model_estimate_inputs = {
        item["target_field"]: item["resolved_value"]
        for item in calculation_validation
        if item["status"] == "VERIFIED_PROVISIONAL_ENGINEERING_ESTIMATE"
        and item["auto_apply"] is True
    }
    verified_model_estimate_lineage = {
        item["target_field"]: {
            key: item.get(key)
            for key in (
                "assist_id", "target_field", "target_unit", "resolved_value",
                "evidence_class", "promotion_cap", "inference_basis", "assumptions",
                "lower_bound", "upper_bound", "confidence", "sensitivity_note",
                "registered_allowed_values", "registry_id", "citations", "warning", "detail",
            )
        }
        for item in calculation_validation
        if item["status"] == "VERIFIED_PROVISIONAL_ENGINEERING_ESTIMATE"
        and item["auto_apply"] is True
    }
    verified_terminal_selection_overrides = {
        item["selection_context_sha256"]: item["terminal_rule_id"]
        for item in terminal_selection_validation
        if item["status"] == "VERIFIED_REGISTERED_CONDITION_SELECTION"
        and item["auto_apply"] is True
    }
    verified_terminal_selection_override_id = (
        next(iter(verified_terminal_selection_overrides.values()))
        if len(verified_terminal_selection_overrides) == 1
        else None
    )
    legacy_proposal = {
        "summary": validated["summary"],
        "recommended_action": "review",
        "changes": [
            {
                "field": item["field"],
                "value": item["value"],
                "reason": item["reason"],
                "source": f"llm_context:{context_pack['context_sha256']}",
                "citations": item["citations"],
            }
            for item in validated["proposed_changes"]
        ],
    }
    proposal = validate_proposal(legacy_proposal)
    next_actions: list[dict[str, Any]] = []
    if validated["proposed_changes"]:
        next_actions.append({
            "action": "apply_approved_descriptive_changes_and_replay",
            "requires_explicit_approval": True,
            "requires_deterministic_replay": True,
            "allowed_change_fields": sorted({item["field"] for item in validated["proposed_changes"]}),
        })
    if validated["retrieval_plan"]:
        next_actions.append({
            "action": "execute_allowlisted_knowledge_queries_then_reprepare",
            "requires_explicit_approval": False,
            "requires_deterministic_replay": False,
            "queries": validated["retrieval_plan"],
        })
    if calculation_validation:
        next_actions.append({
            "action": "apply_verified_calculation_assists_and_replay",
            "requires_explicit_approval": False,
            "requires_deterministic_replay": bool(
                verified_calculation_inputs or verified_model_estimate_inputs
            ),
            "verified_inputs": verified_calculation_inputs,
            "verified_provisional_model_inputs": verified_model_estimate_inputs,
            "nonblocking_items": [
                item for item in calculation_validation
                if item["status"] not in {
                    "VERIFIED_DETERMINISTIC_DERIVATION",
                    "VERIFIED_DETERMINISTIC_DERIVATION_FROM_PROVISIONAL_INPUT",
                    "VERIFIED_PROVISIONAL_ENGINEERING_ESTIMATE",
                }
            ],
        })
    if terminal_selection_validation:
        next_actions.append({
            "action": "apply_verified_registered_terminal_selection_and_replay",
            "requires_explicit_approval": False,
            "requires_deterministic_replay": bool(verified_terminal_selection_overrides),
            "verified_overrides": verified_terminal_selection_overrides,
            "nonblocking_items": [
                item for item in terminal_selection_validation
                if item["status"] != "VERIFIED_REGISTERED_CONDITION_SELECTION"
            ],
        })
    if validated.get("ambiguity_decision"):
        next_actions.append({
            "action": "replay_and_revalidate_candidate_reference",
            "requires_explicit_approval": True,
            "requires_deterministic_replay": True,
        })
    if validated["condition_assessments"] or validated["audit_findings"]:
        next_actions.append({
            "action": "retain_as_advisory_review_record",
            "requires_explicit_approval": False,
            "requires_deterministic_replay": False,
            "hard_gate_override_allowed": False,
        })
    replay_required = bool(
        proposal["accepted_changes"]
        or validated.get("ambiguity_decision")
        or verified_calculation_inputs
        or verified_model_estimate_inputs
        or verified_terminal_selection_overrides
    )
    timeline = interleaved_timeline(
        context_pack,
        validated,
        replay_required=replay_required,
        calculation_validation=calculation_validation,
    )
    result = {
        "schema": ORCHESTRATION_SCHEMA,
        "prepared_sha256": prepared["prepared_sha256"],
        "authority_revision": prepared["authority_revision"],
        "context_sha256": context_pack["context_sha256"],
        "context_scope": context_pack["context_scope"],
        "coverage_status": context_pack["coverage_status"],
        "injection_point": prepared["injection_point"],
        "deterministic_authority": True,
        "step_output": validated,
        "calculation_assist_validation": calculation_validation,
        "verified_calculation_inputs": verified_calculation_inputs,
        "verified_model_estimate_inputs": verified_model_estimate_inputs,
        "verified_model_estimate_lineage": verified_model_estimate_lineage,
        "terminal_selection_assist_validation": terminal_selection_validation,
        "verified_terminal_selection_overrides": verified_terminal_selection_overrides,
        "verified_terminal_selection_override_id": verified_terminal_selection_override_id,
        "output_composition": validated["output_composition"],
        "execution_timeline": timeline,
        "proposal": legacy_proposal,
        "validated_proposal": proposal,
        "candidate_reference": validated.get("ambiguity_decision"),
        "replay_contract": prepared.get("replay_contract"),
        "transition_contract": {
            "single_step": True,
            "interleaved_output": True,
            "ai_controls_output_composition": True,
            "algorithm_remains_authoritative": True,
            "next_actions": next_actions,
        },
        "apply_contract": {
            "requires_user_acceptance": proposal["requires_user_acceptance"],
            "recalculation_required": bool(proposal["accepted_changes"]),
            "hard_parameter_override_allowed": False,
            "verified_missing_input_auto_apply_allowed": bool(verified_calculation_inputs),
            "registered_terminal_selection_auto_apply_allowed": bool(verified_terminal_selection_overrides),
            "model_inference_auto_apply_allowed": bool(verified_model_estimate_inputs),
            "model_inference_auto_apply_scope": "missing_preliminary_fields_only",
            "model_inference_evidence_class": "J",
            "model_inference_promotion_cap": "TYPE_SCREENING",
            "script_conflict_policy": "deterministic_script_wins",
            "existing_numeric_overwrite_allowed": False,
            "candidate_reference_is_advisory_only": True,
            "program_result_blocks_are_immutable": True,
        },
    }
    result["orchestration_sha256"] = _canonical_sha256(result)
    return result


def _request_step_output(config: dict[str, Any], prepared: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    _verify_prepared(prepared)
    provider = str(config.get("provider", "openai_compatible")).strip()
    provider_definition = SUPPORTED_PROVIDERS.get(provider)
    if provider_definition is None:
        raise ValueError(f"不支持的 LLM provider：{provider}。")
    model = str(config.get("model") or "").strip()
    if provider == "mock":
        mock_response = config.get("mock_response")
        if isinstance(mock_response, str):
            output = _parse_json(mock_response)
        elif isinstance(mock_response, dict):
            output = json.loads(json.dumps(mock_response, ensure_ascii=False))
        else:
            raise ValueError("mock provider 需要 mock_response JSON 对象或字符串。")
        return output, {
            "provider": "mock",
            "provider_endpoint": None,
            "model": model or "offline-mock",
            "timeout_s": None,
            "api_key_persisted": False,
            "api_key_echoed": False,
        }

    if not model:
        raise ValueError("必须填写模型名称。")

    api_key = str(config.get("api_key", "")).strip()
    base_url = str(config.get("base_url") or provider_definition["default_base_url"]).strip()
    timeout_s = _timeout_seconds(config.get("timeout_s", 90))
    wire_api = _wire_api(config)
    reasoning_effort = _reasoning_effort(config)
    disable_response_storage = _disable_response_storage(config)
    if not model:
        raise ValueError("必须填写模型名称。")
    endpoint = _endpoint(base_url, provider, wire_api)
    parsed_endpoint = urllib.parse.urlparse(endpoint)
    if not api_key and parsed_endpoint.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("远程 API 必须填写 API Key；Key 只在本次请求内使用，不保存。")
    system = (
        "You are an optional, non-authoritative equipment-design calculation-assistance and review layer. "
        "Return one JSON object matching the supplied output contract exactly. "
        "Your primary job is to close a complete preliminary equipment selection without hiding uncertainty. First scan "
        "the complete calculation_recipe_catalog and select every recipe that can close a missing target, including "
        "multi-step dependencies; the program, not you, computes every recipe and wins every numeric conflict. Then scan "
        "missing_input_registry. If a listed preliminary field still cannot be closed by a recipe, return one "
        "model_inference assist for it rather than silently abandoning selection. Infer only from cited same-case facts, "
        "explicit engineering requirements, registered ranges, or a clearly conservative screening assumption. Every "
        "model_inference must be uncertain and include inference_basis, nonempty assumptions, a plausible lower/upper "
        "bound for numbers (null bounds for registered enums or constrained preliminary text), low/medium confidence, "
        "a concrete sensitivity_note, and "
        "requested_preliminary_auto_apply=true when it should be used for the preliminary replay. Unit conversion is "
        "allowed only when the source value and unit are explicit in the immutable context; identify it as "
        "unit_conversion. Never infer a field absent from missing_input_registry. Never estimate evidence files, vendor "
        "curves, approvals, final models, hazards or corrosivity from component names. The program applies broad physical "
        "guards, deterministic field/cross-field checks and the rule engine after your proposal. All accepted model "
        "estimates remain evidence class J, visibly provisional and capped at TYPE_SCREENING. "
        "Do not overwrite existing numbers or units, pressure basis, evidence status, model status, or final models. "
        "When a terminal equipment form is visibly DEFAULTED, you may upgrade it only by selecting one exact entry "
        "from terminal_type_rule_registry, marking its registered condition supported, and returning the bound rule, "
        "condition and selection-context hash in terminal_selection_assists. If no registered condition is supported, "
        "retain the deterministic default. Never invent equipment-type text. "
        "Do not invent candidate_model text. A candidate may only be referenced from candidate_registry with its exact "
        "candidate_id, designation, selection_feature_vector_sha256 and selection_context_sha256. Cite context_id values. "
        "The active_output_policy is mandatory. Only its allowed_sections may contain non-empty values. Every entry in "
        "sections_that_must_be_empty must use the exact empty value supplied in empty_value_by_section; do not perform "
        "helpful work in a section that is inactive for this call. Your summary must state whether the preliminary "
        "selection can close, which values are model estimates, and which formal software/vendor/evidence gates remain."
    )
    output_contract = prepared["output_contract"]
    user = {
        "task": str(config.get("task", "审核确定性设备设计结果。")),
        "prepared_sha256": prepared["prepared_sha256"],
        "authority_revision": prepared["authority_revision"],
        "context_pack": prepared["context_pack"],
        "active_output_policy": {
            "injection_point": prepared["injection_point"],
            "allowed_sections": output_contract["allowed_sections"],
            "sections_that_must_be_empty": output_contract["sections_that_must_be_empty"],
            "empty_value_by_section": output_contract["empty_value_by_section"],
        },
        "output_contract": output_contract,
    }
    provider_schema = prepared["output_contract"].get("provider_json_schema")
    if provider == "openai" and not isinstance(provider_schema, dict):
        raise ValueError("prepared.output_contract 缺少 provider_json_schema。")
    if wire_api == "responses":
        payload = _responses_payload(
            model,
            json.dumps(user, ensure_ascii=False),
            instructions=system,
            reasoning_effort=reasoning_effort,
            disable_response_storage=disable_response_storage,
            json_schema=provider_schema if provider == "openai" else None,
            schema_name="equipment_design_llm_step_output",
        )
    else:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
            "temperature": 0.0,
        }
    if provider == "openai" and wire_api == "chat_completions":
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "equipment_design_llm_step_output",
                "strict": True,
                "schema": provider_schema,
            },
        }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = _redact(exc.read().decode("utf-8", errors="replace")[:1500], api_key)
        raise RuntimeError(f"LLM API HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"LLM API 连接失败：{_redact(str(exc.reason), api_key)}") from exc
    output = _parse_json(_content(json.loads(body)))
    return output, {
        "provider": provider,
        "provider_endpoint": endpoint,
        "model": model,
        "timeout_s": timeout_s,
        "wire_api": wire_api,
        "reasoning_effort": reasoning_effort,
        "response_storage_disabled": disable_response_storage if wire_api == "responses" else None,
        "api_key_persisted": False,
        "api_key_echoed": False,
    }


def hybrid_run(config: dict[str, Any], prepared: dict[str, Any]) -> dict[str, Any]:
    step_output, provider_metadata = _request_step_output(config, prepared)
    result = hybrid_continue(prepared, step_output)
    return {**result, **provider_metadata}


def validate_proposal(proposal: dict[str, Any]) -> dict[str, Any]:
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    changes = proposal.get("changes", [])
    if not isinstance(changes, list):
        changes = []
    for index, item in enumerate(changes, 1):
        if not isinstance(item, dict):
            rejected.append({"change": item, "reason": "change_not_object"})
            continue
        field = str(item.get("field", "")).strip()
        value = item.get("value")
        if field == "candidate_model":
            rejected.append({"change": item, "reason": "candidate_model_requires_deterministic_candidate_reference"})
            continue
        if field in FORBIDDEN_FIELDS or field not in ALLOWLISTED_DRAFT_FIELDS:
            rejected.append({"change": item, "reason": "field_not_allowlisted"})
            continue
        if not isinstance(value, str) or not value.strip():
            rejected.append({"change": item, "reason": "value_must_be_nonempty_string"})
            continue
        if field == "phase" and value.strip() not in CANONICAL_PHASES:
            rejected.append({"change": item, "reason": "phase_not_canonical"})
            continue
        citations = item.get("citations", [])
        if not isinstance(citations, list) or not all(isinstance(citation, str) for citation in citations):
            citations = []
        accepted.append({
            "change_id": f"change_{index:03d}",
            "field": field,
            "value": value.strip(),
            "reason": str(item.get("reason", "")).strip(),
            "source": str(item.get("source", "deterministic_result_or_candidate_set")).strip(),
            "citations": [citation.strip() for citation in citations if citation.strip()],
        })
    return {
        "summary": str(proposal.get("summary", "")).strip(),
        "recommended_action": str(proposal.get("recommended_action", "review")).strip(),
        "accepted_changes": accepted,
        "rejected_changes": rejected,
        "requires_user_acceptance": bool(accepted),
        "hard_gate_override_allowed": False,
    }


def apply_proposal(current: dict[str, Any], validated: dict[str, Any]) -> dict[str, Any]:
    result = dict(current)
    for item in validated.get("accepted_changes", []):
        field = item.get("field")
        if field in ALLOWLISTED_DRAFT_FIELDS:
            result[field] = item.get("value")
    return result


def request_review(
    config: dict[str, Any],
    deterministic_result: dict[str, Any],
    knowledge_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    api_key = str(config.get("api_key", "")).strip()
    provider = str(config.get("provider", "openai_compatible")).strip()
    provider_definition = SUPPORTED_PROVIDERS.get(provider)
    if provider_definition is None:
        raise ValueError(f"不支持的 LLM provider：{provider}。")
    if provider == "mock":
        raw = config.get("mock_response")
        if isinstance(raw, str):
            raw = _parse_json(raw)
        if not isinstance(raw, dict):
            raise ValueError("mock provider 需要 mock_response JSON 对象或字符串。")
        return {
            "schema": "equipment-design-app-llm-review-v1",
            "provider": "mock",
            "provider_endpoint": None,
            "model": str(config.get("model", "offline-mock")),
            "timeout_s": None,
            "api_key_persisted": False,
            "api_key_echoed": False,
            "knowledge_context_used": bool(knowledge_context),
            "proposal": validate_proposal(raw),
        }
    base_url = str(config.get("base_url") or provider_definition["default_base_url"]).strip()
    model = str(config.get("model") or "").strip()
    timeout_s = _timeout_seconds(config.get("timeout_s", 90))
    wire_api = _wire_api(config)
    reasoning_effort = _reasoning_effort(config)
    disable_response_storage = _disable_response_storage(config)
    if not model:
        raise ValueError("必须填写模型名称。")
    endpoint = _endpoint(base_url, provider, wire_api)
    parsed_endpoint = urllib.parse.urlparse(endpoint)
    if not api_key and parsed_endpoint.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("远程 API 必须填写 API Key；Key 只在本次请求内使用，不保存。")

    system = (
        "You are the optional review/decision layer of a deterministic chemical-equipment application. "
        "Never override BLOCKED_* states, units, pressure basis, physical-direction gates, evidence hashes, "
        "or model-status gates. When multiple choices remain, retain the most general common family/type unless "
        "the supplied evidence uniquely closes one branch. You may propose only allowlisted draft text fields: "
        "equipment_type, process_function, phase. candidate_model is forbidden here; existing candidates may only be "
        "referenced through the phased orchestration contract. Do not invent numeric values. Return JSON with "
        "summary, recommended_action, and changes:[{field,value,reason,source}]."
    )
    user = {
        "task": str(config.get("task", "审核确定性结果，并在候选集内提出可选的机械化决策。")),
        "allowlisted_fields": sorted(ALLOWLISTED_DRAFT_FIELDS),
        "deterministic_result": deterministic_result,
        "knowledge_context": knowledge_context or {
            "status": "NOT_REQUESTED",
            "hits": [],
            "limitation": "No selected knowledge package was supplied.",
        },
    }
    if wire_api == "responses":
        payload = _responses_payload(
            model,
            json.dumps(user, ensure_ascii=False),
            instructions=system,
            reasoning_effort=reasoning_effort,
            disable_response_storage=disable_response_storage,
        )
    else:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
            "temperature": 0.1,
        }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = _redact(exc.read().decode("utf-8", errors="replace")[:1500], api_key)
        raise RuntimeError(f"LLM API HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"LLM API 连接失败：{_redact(str(exc.reason), api_key)}") from exc
    response_obj = json.loads(body)
    raw_text = _content(response_obj)
    proposal = validate_proposal(_parse_json(raw_text))
    return {
        "schema": "equipment-design-app-llm-review-v1",
        "provider": provider,
        "provider_endpoint": endpoint,
        "model": model,
        "timeout_s": timeout_s,
        "wire_api": wire_api,
        "reasoning_effort": reasoning_effort,
        "response_storage_disabled": disable_response_storage if wire_api == "responses" else None,
        "api_key_persisted": False,
        "api_key_echoed": False,
        "knowledge_context_used": bool(knowledge_context),
        "proposal": proposal,
    }
