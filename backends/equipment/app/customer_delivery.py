"""Deterministic customer-delivery projections for equipment matcher results.

The matcher remains the authority.  This module only projects already present
machine state into three customer-facing JSON objects.  It never performs an
engineering calculation, selects a model, upgrades evidence, or imports values
from a reference project.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any


FROZEN_ROOT = getattr(sys, "_MEIPASS", None)
if FROZEN_ROOT:
    PACKAGE_ROOT = Path(FROZEN_ROOT)
    APP_DIR = PACKAGE_ROOT / "app"
else:
    APP_DIR = Path(__file__).resolve().parent
    PACKAGE_ROOT = APP_DIR.parent
DEFAULT_PROFILE_PATH = PACKAGE_ROOT / "knowledge_graph" / "equipment_customer_output_profiles.json"
PARAMETER_TEMPLATE_PATH = PACKAGE_ROOT / "knowledge_graph" / "equipment_parameter_chain_templates.json"
FALLBACK_AUTHORITY_SOURCES = (
    "设备选型一览表_知识图谱重构_20260712/knowledge_graph/13-overview-table-field-schema.md",
    "设备选型一览表_知识图谱重构_20260712/knowledge_graph/30-overview-table-interface.md",
)


class CustomerDeliveryError(ValueError):
    """Raised when deterministic inputs or profile contracts are inconsistent."""


_MISSING = object()
_HASH_RE = re.compile(r"^[0-9A-Fa-f]{64}$")
_TOKEN_RE = re.compile(r"[^0-9a-z\u4e00-\u9fff]+", re.IGNORECASE)


OVERVIEW_COLUMNS = (
    "sequence_number",
    "process_section",
    "equipment_key",
    "equipment_tag",
    "equipment_name",
    "quantity_and_standby",
    "equipment_drawing_number",
    "total_mass_kg",
    "family_ids",
    "family_name",
    "equipment_type",
    "model_or_specification",
    "model_or_specification_status",
    "engineering_adjustment_status",
    "engineering_adjustment_plan",
    "algorithmic_selection_warning",
    "selection_agent_control_status",
    "terminal_selection_status",
    "terminal_selection_basis",
    "terminal_default_applied",
    "terminal_rule_id",
    "terminal_assumption",
    "standards_and_versions",
    "standard_reference_routes",
    "evidence_ids",
    "customer_table_missing_fields",
    "algorithm_evidence_missing_fields",
    "missing_information",
    "evidence_level",
    "delivery_state",
    "authority_table_id",
    "authority_table_title",
    "authority_source",
    "authority_columns",
    "authority_cells",
    "authority_missing_fields",
    "authority_completeness",
    "authority_structural_completeness",
    "authority_full_field_coverage",
    "authority_information_coverage",
    "customer_full_field_coverage",
    "customer_information_coverage",
    "selection_specificity_gate",
    "formal_readiness_gate",
    "program_generated",
    "manual_postprocessing",
    "record_kind",
    "derivation_record_kind",
    "derivation_record_identity",
    "program_generated_record_sha256",
    "program_generated_record_binding_sha256",
    "source_input_sha256",
    "source_chain_binding",
    "source_chain_binding_sha256",
    "authority_row_sha256",
    "all_equipment_fields_sha256",
    "all_equipment_fields",
)


COMMON_DELIVERY_FIELD_IDS = (
    "equipment_tag",
    "equipment_name",
    "process_function",
    "equipment_type",
    "model_or_specification",
    "model_or_specification_status",
    "quantity",
    "standards_and_versions",
    "evidence_ids",
    "missing_information",
    "evidence_level",
)


FALLBACK_FAMILY_FIELDS: dict[str, tuple[str, ...]] = {
    "family_pump": (
        "main_medium", "flow_m3_h", "head_m", "temperature_c", "density_kg_m3",
        "viscosity_mpa_s", "shaft_power_kw", "efficiency_percent", "rotational_speed_rpm",
        "material", "seal_type", "operating_state", "equipment_arrangement", "standby_scheme",
        "npsha_m", "npshr_m", "special_requirements",
    ),
    "family_compressor": (
        "gas_composition", "gas_molecular_weight", "isentropic_exponent", "compressibility_factor",
        "inlet_temperature_c", "outlet_temperature_c", "inlet_pressure_mpa", "outlet_pressure_mpa",
        "flow_m3_h", "standard_flow_m3_h", "compression_pressure_ratio", "stage_count",
        "rotational_speed_rpm", "shaft_power_kw", "motor_power_kw", "total_power_kw",
        "efficiency_percent", "cooling_method",
        "driver_type", "material",
    ),
    "family_liquid_power_recovery_turbine": (
        "main_medium", "flow_m3_h", "working_head_m", "inlet_pressure_mpa", "outlet_pressure_mpa",
        "rotational_speed_rpm", "efficiency_percent", "shaft_power_kw", "material", "npsha_m",
        "npshr_m", "total_mass_kg",
    ),
    "family_gas_expander_turbine": (
        "gas_composition", "flow_m3_h", "mass_flow_kg_h", "inlet_temperature_c",
        "outlet_temperature_c", "inlet_pressure_mpa", "outlet_pressure_mpa", "enthalpy_drop_kj_kg",
        "rotational_speed_rpm", "efficiency_percent", "shaft_power_kw", "material", "total_mass_kg",
    ),
    "family_fixed_tubesheet_exchanger": (
        "equipment_drawing_number", "heat_duty_kw", "heat_transfer_area_m2", "hot_side_operating_temperature_c",
        "cold_side_operating_temperature_c", "hot_side_operating_pressure_mpa",
        "cold_side_operating_pressure_mpa", "hot_side_design_temperature_c",
        "cold_side_design_temperature_c", "hot_side_design_pressure_mpa",
        "cold_side_design_pressure_mpa", "hot_side_allowable_pressure_drop_kpa",
        "cold_side_allowable_pressure_drop_kpa", "diameter_mm", "pressure_class",
        "tube_outer_diameter_mm", "tube_length_mm", "tube_or_plate_count", "tube_pass_count",
        "shell_pass_count", "tube_side_material", "shell_side_material",
    ),
    "family_other_heat_exchanger": (
        "equipment_drawing_number", "heat_duty_kw", "heat_transfer_area_m2", "hot_side_operating_temperature_c",
        "cold_side_operating_temperature_c", "hot_side_operating_pressure_mpa",
        "cold_side_operating_pressure_mpa", "hot_side_design_temperature_c",
        "cold_side_design_temperature_c", "hot_side_design_pressure_mpa",
        "cold_side_design_pressure_mpa", "hot_side_allowable_pressure_drop_kpa",
        "cold_side_allowable_pressure_drop_kpa", "tube_or_plate_count", "shell_pass_count",
        "tube_side_material", "shell_side_material",
    ),
    "family_storage_vessel": (
        "vessel_service", "orientation", "roof_or_cover_type", "volume_m3", "effective_volume_m3",
        "technical_specification", "diameter_mm", "height_mm", "design_temperature_c",
        "design_pressure_mpa", "main_medium", "material", "liquid_level_percent", "fill_fraction",
        "retention_time_min", "total_mass_kg", "protective_layer", "insulation_layer",
        "standard_designation",
    ),
    # The matcher deliberately keeps reactors, generic vessels, and separators
    # in one family.  The fallback therefore exposes the union instead of
    # guessing one specialised subtype.
    "family_reactor_vessel_separator": (
        "reactor_or_vessel_service", "orientation", "reactor_type", "separator_type",
        "demister_type", "volume_m3", "working_volume_m3", "bed_volume_m3",
        "active_tube_inner_diameter_mm", "active_tube_length_screening_mm",
        "one_tube_geometric_screening_volume_m3",
        "required_total_reactor_volume_m3", "selected_tube_count",
        "reactor_shell_inner_diameter_mm",
        "nominal_process_tube_wall_thickness_mm",
        "nominal_shell_wall_thickness_mm",
        "technical_specification", "diameter_mm", "height_mm", "design_temperature_c",
        "design_pressure_mpa", "head_type", "main_medium", "material", "shell_material",
        "reactor_tube_material", "jacket_material", "internals_material", "tube_count",
        "agitator_type", "shaft_power_kw", "gas_load", "liquid_load",
        "selected_wall_thickness_mm", "inlet_nozzle_diameter_mm",
        "gas_outlet_nozzle_diameter_mm", "liquid_outlet_nozzle_diameter_mm",
        "equipment_drawing_number", "tubesheet_thickness_mm", "total_mass_kg",
    ),
    "family_tower": (
        "tower_internals_type", "diameter_mm", "height_mm",
        "stage_count", "packing_or_tray_specification", "design_temperature_c",
        "design_pressure_mpa", "head_type", "material", "internals_material",
        "insulation_layer", "protective_layer", "equipment_drawing_number", "total_mass_kg",
    ),
    "family_static_mixer": (
        "main_medium", "flow_m3_h", "selected_dn", "element_type", "element_count",
        "mixer_length_mm", "technical_specification", "design_temperature_c",
        "design_pressure_mpa", "allowable_pressure_drop_kpa", "mixing_metric", "loading_coefficient",
        "rotational_speed_rpm", "material", "total_mass_kg",
    ),
    "family_agitator": (
        "main_medium", "volume_m3", "density_kg_m3", "viscosity_mpa_s", "agitator_type",
        "impeller_diameter_mm", "rotational_speed_rpm", "shaft_power_kw", "mixing_metric", "material",
    ),
    "family_membrane": (
        "main_medium", "flow_m3_h", "membrane_material", "membrane_area_m2", "flux",
        "selectivity", "recovery_percent", "element_count", "design_temperature_c",
        "design_pressure_mpa", "allowable_pressure_drop_kpa",
    ),
    "family_package_equipment": (
        "main_medium", "capacity", "cycle_time_h", "allowable_pressure_drop_kpa",
        "design_temperature_c", "design_pressure_mpa", "material", "package_boundary",
    ),
    "family_process_piping": (
        "line_origin", "line_destination", "main_medium", "phase", "flow_m3_h", "temperature_c",
        "design_temperature_c", "operating_pressure_mpa", "design_pressure_mpa", "density_kg_m3",
        "viscosity_mpa_s", "selected_dn", "selected_outer_diameter_mm",
        "selected_wall_thickness_mm", "wall_series", "corrosion_allowance_mm", "material",
        "piping_class", "insulation_layer", "heat_tracing",
    ),
    "family_pipe_fitting": (
        "line_number", "fitting_type", "selected_dn", "selected_outer_diameter_mm",
        "selected_wall_thickness_mm", "wall_series", "material", "manufacturing_method",
        "connection_type", "standard_designation",
    ),
    "family_flange_gasket": (
        "line_number", "component_type", "selected_dn", "pressure_class", "flange_type",
        "flange_face", "material", "selected_outer_diameter_mm", "selected_wall_thickness_mm",
        "fastener_material", "gasket_type", "gasket_material", "inner_ring_material",
        "centering_ring_material", "standard_designation",
    ),
    "family_valve": (
        "line_number", "valve_function", "valve_type", "selected_dn", "pressure_class",
        "pressure_temperature_rating", "cv", "normal_pressure_drop_kpa", "maximum_pressure_drop_kpa",
        "material", "trim_material", "seat_material", "connection_type", "leakage_class",
        "actuator_type", "failure_position",
    ),
}


# These fields are produced by deterministic Stage-1 safety boundaries after
# the authority profiles were generated.  They supplement (never replace)
# the formal T/X profile fields.  Tower screening geometry is deliberately
# excluded because it belongs only in the internal preliminary-design audit.
PROGRAMMATIC_FAMILY_SUPPLEMENTAL_FIELDS: dict[str, tuple[str, ...]] = {
    "family_tower": (
        "stage_count",
        "engineering_adjustment_plan",
        "algorithmic_selection_warning",
        "selection_agent_control_status",
    ),
    "family_pump": (
        "hydraulic_power_kw",
        "electrical_power_kw",
        "pump_efficiency_percent",
        "driver_efficiency_percent",
        "fluid_to_shaft_balance_status",
        "fluid_to_shaft_balance_relative_error",
        "shaft_to_electrical_balance_status",
        "shaft_to_electrical_balance_relative_error",
        "pump_power_process_audit_ref",
        "aspen_configured_shaft_speed_candidate_rpm",
        "aspen_actual_shaft_speed_rpm",
        "pump_candidate_reference_speed_rpm",
        "npsha_pressure_kpa",
        "npsha_raw_unit_semantics",
        "pump_npsha_process_audit_ref",
        "engineering_adjustment_plan",
        "algorithmic_selection_warning",
        "selection_agent_control_status",
    ),
    "family_fixed_tubesheet_exchanger": (
        "engineering_adjustment_plan",
        "algorithmic_selection_warning",
        "selection_agent_control_status",
    ),
    "family_other_heat_exchanger": (
        "engineering_adjustment_plan",
        "algorithmic_selection_warning",
        "selection_agent_control_status",
    ),
    "family_reactor_vessel_separator": (
        "active_tube_inner_diameter_mm",
        "active_tube_length_screening_mm",
        "one_tube_geometric_screening_volume_m3",
        "required_total_reactor_volume_m3",
        "selected_tube_count",
        "reactor_shell_inner_diameter_mm",
        "nominal_process_tube_wall_thickness_mm",
        "nominal_shell_wall_thickness_mm",
    ),
    "family_process_piping": (
        "technical_specification",
        "hydraulic_dn_candidate",
        "manufacturing_method",
        "manufacturing_route_code",
        "product_standard",
        "actual_velocity_m_s",
        "reynolds_number",
        "pressure_gradient_kpa_per_100m",
        "pressure_gradient_screen_limit_kpa_per_100m",
        "hydraulic_acceptance_status",
        "aspen_endpoint_pressure_drop_kpa",
        "endpoint_pressure_drop_status",
        "endpoint_pressure_drop_formal_acceptance",
        "piping_class_candidate_code",
        "external_pressure_design_status",
        "vacuum_margin_kpa",
        "significant_vacuum_threshold_kpa",
    ),
}


FALLBACK_FIELD_METADATA: dict[str, dict[str, Any]] = {
    "engineering_adjustment_plan": {
        "label": "程序非标/多台组合修改方案",
    },
    "algorithmic_selection_warning": {
        "label": "算法选型强制警告",
    },
    "selection_agent_control_status": {
        "label": "Agent计算后选型控制状态",
    },
    "actual_velocity_m_s": {
        "label": "实际流速（程序水力核算）",
        "unit": "m/s",
    },
    "reynolds_number": {
        "label": "雷诺数（程序水力核算）",
        "unit": "-",
    },
    "hydraulic_power_kw": {
        "label": "泵液体功率",
        "unit": "kW",
    },
    "electrical_power_kw": {
        "label": "泵电输入功率",
        "unit": "kW",
    },
    "pump_efficiency_percent": {
        "label": "泵效率",
        "unit": "%",
        "source_fields": ["pump_efficiency_percent", "efficiency_percent"],
    },
    "driver_efficiency_percent": {
        "label": "驱动机效率",
        "unit": "%",
    },
    "aspen_configured_shaft_speed_candidate_rpm": {
        "label": "Aspen 已配置轴转速候选（非最终解）",
        "unit": "r/min",
    },
    "fluid_to_shaft_balance_status": {
        "label": "液体功率→轴功率平衡状态",
    },
    "fluid_to_shaft_balance_relative_error": {
        "label": "液体功率→轴功率平衡相对误差",
        "unit": "-",
    },
    "shaft_to_electrical_balance_status": {
        "label": "轴功率→电输入功率平衡状态",
    },
    "shaft_to_electrical_balance_relative_error": {
        "label": "轴功率→电输入功率平衡相对误差",
        "unit": "-",
    },
    "pump_power_process_audit_ref": {
        "label": "泵功率语义与平衡审计引用",
    },
    "aspen_actual_shaft_speed_rpm": {
        "label": "Aspen 实际轴转速",
        "unit": "r/min",
    },
    "pump_candidate_reference_speed_rpm": {
        "label": "GB/T 5662 候选参考转速（非实际转速）",
        "unit": "r/min",
    },
    "npsha_pressure_kpa": {
        "label": "Aspen 可用汽蚀余量压力语义值",
        "unit": "kPa",
    },
    "npsha_raw_unit_semantics": {
        "label": "NPSHA 原始单位与重解释边界",
    },
    "pump_npsha_process_audit_ref": {
        "label": "NPSHA 过程侧审计引用",
    },
    "aspen_endpoint_pressure_drop_kpa": {
        "label": "Aspen端点压差（仅过程观测）",
        "unit": "kPa",
    },
    "endpoint_pressure_drop_status": {
        "label": "端点压差审计状态",
    },
    "endpoint_pressure_drop_formal_acceptance": {
        "label": "端点压差已完成正式验收",
    },
    "equipment_tag": {"label": "设备位号"},
    "equipment_name": {"label": "设备名称"},
    "equipment_type": {"label": "型式/结构"},
    "process_function": {"label": "工艺作用"},
    "model_or_specification": {"label": "型号/规格"},
    "model_or_specification_status": {"label": "型号/规格状态"},
    "quantity": {"label": "数量/台数"},
    "main_medium": {"label": "主要介质"},
    "operating_state": {"label": "运行状态"},
    "equipment_arrangement": {"label": "运行/组合方式"},
    "working_head_m": {"label": "工作水头", "unit": "m", "source_fields": ["working_head_m", "head_m"]},
    "motor_power_kw": {"label": "电机功率", "unit": "kW", "source_fields": ["motor_power_kw"]},
    "total_power_kw": {"label": "总功率", "unit": "kW", "source_fields": ["total_power_kw"]},
    "equipment_drawing_number": {"label": "设备图号"},
    "special_requirements": {"label": "特别需求"},
    "loading_coefficient": {"label": "装载系数", "unit": "-"},
    "tubesheet_thickness_mm": {"label": "管板厚度", "unit": "mm"},
    "tube_or_plate_count": {"label": "换热管/板数量"},
    "shell_pass_count": {"label": "壳程数"},
    "tube_side_material": {"label": "管程材料"},
    "shell_side_material": {"label": "壳程材料"},
    "technical_specification": {"label": "技术规格"},
    "total_mass_kg": {"label": "总质量", "unit": "kg"},
    "protective_layer": {"label": "保护层"},
    "insulation_layer": {"label": "保温层"},
    "standard_designation": {"label": "标准序号/标记"},
    "stage_count": {"label": "Aspen 塔板/理论级数", "unit": "-"},
    "tower_internal_height_m": {"label": "填料/塔板有效高度", "unit": "m"},
    "tower_total_height_m": {"label": "塔总高", "unit": "m"},
    "tower_diameter_screening_mm": {"label": "塔径筛选值（非正式塔径）", "unit": "mm"},
    "tower_height_screening_mm": {"label": "塔高布置筛选值（非正式总高）", "unit": "mm"},
    "formula_only_shell_thickness_mm": {"label": "筒体公式厚度（非名义厚度）", "unit": "mm"},
    "formula_only_head_thickness_mm": {"label": "封头公式厚度（非名义厚度）", "unit": "mm"},
    "nominal_shell_wall_thickness_selected": {"label": "筒体名义厚度已选定"},
    "nominal_head_wall_thickness_selected": {"label": "封头名义厚度已选定"},
    "active_tube_inner_diameter_mm": {"label": "单根有效管内径（Aspen RPLUG）", "unit": "mm"},
    "active_tube_length_screening_mm": {"label": "单根有效管长度筛选假设", "unit": "mm"},
    "one_tube_geometric_screening_volume_m3": {"label": "单根有效管几何筛选体积", "unit": "m3"},
    "required_total_reactor_volume_m3": {"label": "所需反应器总体积", "unit": "m3"},
    "selected_tube_count": {"label": "选定反应管数"},
    "reactor_shell_inner_diameter_mm": {"label": "反应器壳体内径", "unit": "mm"},
    "nominal_process_tube_wall_thickness_mm": {"label": "反应管名义壁厚", "unit": "mm"},
    "nominal_shell_wall_thickness_mm": {"label": "反应器壳体名义壁厚", "unit": "mm"},
    "head_type": {"label": "封头形式"},
    "selected_wall_thickness_mm": {"label": "选定壁厚", "unit": "mm"},
    "inlet_nozzle_diameter_mm": {"label": "进口接管直径", "unit": "mm"},
    "gas_outlet_nozzle_diameter_mm": {"label": "气体出口管直径", "unit": "mm"},
    "liquid_outlet_nozzle_diameter_mm": {"label": "液体出口管直径", "unit": "mm"},
    "standards_and_versions": {"label": "采用标准及版本", "requirement": "required"},
    "evidence_ids": {"label": "计算书/软件/厂家证据号", "requirement": "required"},
    "missing_information": {"label": "待补资料", "requirement": "required"},
    "evidence_level": {"label": "证据等级", "requirement": "required"},
}


# Customer-only aliases that expose an already-derived deterministic Aspen
# quantity under the authority table's customer-facing name.
CUSTOMER_SOURCE_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "aspen_flow_m3_h": ("flow_m3_h",),
    "aspen_simulated_head_m": ("head_m",),
    "pump_efficiency_percent": ("efficiency_percent",),
}


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CustomerDeliveryError("non-finite numeric value cannot be serialized")
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json_safe(item) for item in value]
    return str(value)


def _canonical_json(value: Any) -> str:
    return json.dumps(_json_safe(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest().upper()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _present(value: Any) -> bool:
    return value is not None and (not isinstance(value, str) or bool(value.strip()))


def _explicit_not_applicable(field: Mapping[str, Any], value: Any) -> bool:
    """Recognise N/A only where the authority profile explicitly permits it."""

    if field.get("not_applicable_allowed") is not True or not isinstance(value, str):
        return False
    normalized = value.strip().casefold()
    tokens = {
        str(token).strip().casefold()
        for token in field.get("not_applicable_tokens", [])
        if isinstance(token, str) and token.strip()
    }
    return bool(normalized) and normalized in tokens


def _not_applicable_cell(
    field: Mapping[str, Any],
    *,
    source_field: str,
    raw_token: str,
    source: Any,
) -> dict[str, Any]:
    return {
        "field_id": field["field_id"],
        "label": field.get("label"),
        "unit": field.get("unit"),
        "value": None,
        "state": str(field.get("not_applicable_state") or "NOT_APPLICABLE"),
        "source_field_id": source_field,
        "source": {
            "kind": "explicit_not_applicable_token",
            "declared_not_applicable_token": raw_token,
            "original_source": _json_safe(source),
        },
        "equation_chain": None,
        "formula_chain": None,
    }


def _token(value: Any) -> str:
    return _TOKEN_RE.sub("", str(value or "").casefold())


def _load_parameter_definitions() -> dict[str, dict[str, Any]]:
    if not PARAMETER_TEMPLATE_PATH.is_file():
        return {}
    try:
        raw = json.loads(PARAMETER_TEMPLATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    definitions = raw.get("parameter_definitions", {})
    return {
        str(field_id): dict(meta)
        for field_id, meta in definitions.items()
        if isinstance(meta, Mapping)
    } if isinstance(definitions, Mapping) else {}


def fallback_output_profiles() -> dict[str, Any]:
    """Return the source-structure-only fallback derived from graph nodes 13/30."""

    definitions = _load_parameter_definitions()
    merged_definitions = {**definitions, **FALLBACK_FIELD_METADATA}
    profiles: list[dict[str, Any]] = []
    for family_id in sorted(FALLBACK_FAMILY_FIELDS):
        field_ids = list(dict.fromkeys((*COMMON_DELIVERY_FIELD_IDS, *FALLBACK_FAMILY_FIELDS[family_id])))
        profiles.append({
            "profile_id": f"fallback:{family_id}:most_general",
            "title": f"{family_id} 客户交付字段（最泛用）",
            "family_ids": [family_id],
            "discriminator": None,
            "fields": [
                {
                    "field_id": field_id,
                    "order": order,
                    "requirement": merged_definitions.get(field_id, {}).get("requirement", "required"),
                }
                for order, field_id in enumerate(field_ids)
            ],
            "source_refs": list(FALLBACK_AUTHORITY_SOURCES),
        })
    profiles.append({
        "profile_id": "fallback:generic:most_general",
        "title": "未唯一识别设备客户交付字段（最泛用）",
        "family_ids": [],
        "discriminator": None,
        "fields": [
            {"field_id": field_id, "order": order, "requirement": "required"}
            for order, field_id in enumerate(COMMON_DELIVERY_FIELD_IDS)
        ],
        "source_refs": list(FALLBACK_AUTHORITY_SOURCES),
    })
    return {
        "schema": "equipment-customer-output-profiles-v1",
        "version": "fallback-13-30-v1",
        "authority_sources": list(FALLBACK_AUTHORITY_SOURCES),
        "field_definitions": merged_definitions,
        "common_delivery_fields": [],
        "profiles": profiles,
        "fallback": True,
    }


def _as_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, Iterable) and not isinstance(value, Mapping):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)]


def _raw_profile_entries(raw: Mapping[str, Any]) -> list[dict[str, Any]]:
    source = raw.get("profiles")
    if source is None:
        source = raw.get("output_profiles")
    if source is None:
        source = raw.get("families")
    entries: list[dict[str, Any]] = []
    if isinstance(source, Mapping):
        for key in sorted(source, key=str):
            value = source[key]
            values = value if isinstance(value, list) else [value]
            for index, item in enumerate(values):
                if not isinstance(item, Mapping):
                    raise CustomerDeliveryError(f"profile {key!r} must be an object")
                entry = dict(item)
                entry.setdefault("profile_id", f"{key}:{index}" if len(values) > 1 else str(key))
                entry.setdefault("family_ids", [str(key)] if str(key).startswith("family_") else [])
                entries.append(entry)
    elif isinstance(source, list):
        for item in source:
            if not isinstance(item, Mapping):
                raise CustomerDeliveryError("every profile must be an object")
            entries.append(dict(item))
    else:
        raise CustomerDeliveryError("profile document must contain profiles or families")
    return entries


def _algorithm_profile_family_map(raw: Mapping[str, Any]) -> dict[str, list[str]]:
    """Return profile-id -> family-ids from the generated algorithm map."""

    source = raw.get("algorithm_family_profile_map", {})
    result: dict[str, set[str]] = {}
    if not isinstance(source, Mapping):
        return {}
    for key, value in source.items():
        key_text = str(key)
        if key_text.startswith("family_"):
            if isinstance(value, Mapping):
                profile_ids = _as_string_list(value.get("profile_ids", value.get("profiles")))
            else:
                profile_ids = _as_string_list(value)
            for profile_id in profile_ids:
                result.setdefault(profile_id, set()).add(key_text)
            continue
        if isinstance(value, Mapping):
            families = _as_string_list(value.get("family_ids", value.get("family_id")))
        else:
            families = _as_string_list(value)
        for family_id in families:
            if family_id.startswith("family_"):
                result.setdefault(key_text, set()).add(family_id)
    return {key: sorted(values) for key, values in result.items()}


def _flatten_profile_fields(profile: Mapping[str, Any]) -> list[Any]:
    for key in ("required_fields", "fields", "datasheet_fields", "customer_fields"):
        if isinstance(profile.get(key), list):
            return list(profile[key])
    result: list[Any] = []
    for key in ("groups", "field_groups"):
        groups = profile.get(key)
        if isinstance(groups, list):
            for group in groups:
                if isinstance(group, Mapping) and isinstance(group.get("fields"), list):
                    result.extend(group["fields"])
    return result


def _normalise_field(
    value: Any,
    definitions: Mapping[str, Mapping[str, Any]],
    *,
    default_order: int,
) -> dict[str, Any]:
    if isinstance(value, str):
        item: dict[str, Any] = {"field_id": value}
    elif isinstance(value, Mapping):
        item = dict(value)
    else:
        raise CustomerDeliveryError("profile fields must be strings or objects")
    field_id = (
        item.get("canonical_id") or item.get("field_id") or item.get("id")
        or item.get("name") or item.get("field")
    )
    if not isinstance(field_id, str) or not field_id.strip():
        raise CustomerDeliveryError("profile field is missing field_id")
    field_id = field_id.strip()
    merged = dict(definitions.get(field_id, {}))
    merged.update(item)
    merged["field_id"] = field_id
    merged["order"] = int(merged.get("order", default_order))
    requirement = str(merged.get("requirement", "required")).strip().casefold()
    merged["requirement"] = requirement or "required"
    merged["label"] = str(merged.get("label") or field_id.replace("_", " "))
    source_fields: list[str] = []
    for key in ("source_fields", "source_field", "aliases", "sources"):
        source_fields.extend(_as_string_list(merged.get(key)))
    source_fields.append(field_id)
    source_fields.extend(CUSTOMER_SOURCE_FIELD_ALIASES.get(field_id, ()))
    merged["source_fields"] = list(dict.fromkeys(field for field in source_fields if field))
    if "source_gate" in merged and "evidence_gate" not in merged:
        merged["evidence_gate"] = merged.get("source_gate")
    merged["source_refs"] = sorted(set([
        *_as_string_list(merged.get("source_refs")),
        *_as_string_list(merged.get("authority_sources")),
    ]))
    return _json_safe(merged)


def normalise_output_profiles(raw: Mapping[str, Any], *, source: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Normalise the preferred profile contract and a few legacy container shapes."""

    definitions_raw = raw.get("canonical_field_definitions", raw.get("field_definitions", {}))
    if isinstance(definitions_raw, list):
        definitions = {
            str(item.get("canonical_id") or item.get("field_id") or item.get("id")): dict(item)
            for item in definitions_raw
            if isinstance(item, Mapping) and (item.get("canonical_id") or item.get("field_id") or item.get("id"))
        }
    elif isinstance(definitions_raw, Mapping):
        definitions = {
            str(key): dict(value)
            for key, value in definitions_raw.items()
            if isinstance(value, Mapping)
        }
    else:
        raise CustomerDeliveryError("field_definitions must be an object or list")
    common_raw = raw.get("global_output_columns", raw.get("common_delivery_fields", []))
    if not isinstance(common_raw, list):
        raise CustomerDeliveryError("common_delivery_fields must be a list")
    common = [
        _normalise_field(item, definitions, default_order=index)
        for index, item in enumerate(common_raw)
    ]
    mapped_families = _algorithm_profile_family_map(raw)
    profiles: list[dict[str, Any]] = []
    for profile_index, raw_profile in enumerate(_raw_profile_entries(raw)):
        profile_id = str(
            raw_profile.get("profile_id") or raw_profile.get("authority_section_id")
            or raw_profile.get("id") or f"profile:{profile_index}"
        )
        family_ids = _as_string_list(
            raw_profile.get("family_ids", raw_profile.get("family_id", raw_profile.get("families")))
        )
        family_ids.extend(mapped_families.get(profile_id, []))
        fields_raw = [*common, *_flatten_profile_fields(raw_profile)]
        fields = [
            item if isinstance(item, Mapping) and "source_fields" in item else
            _normalise_field(item, definitions, default_order=index)
            for index, item in enumerate(fields_raw)
        ]
        existing_field_ids = {
            str(item.get("field_id") or "")
            for item in fields
            if isinstance(item, Mapping)
        }
        for family_id in sorted(set(family_ids)):
            for field_id in PROGRAMMATIC_FAMILY_SUPPLEMENTAL_FIELDS.get(
                family_id,
                (),
            ):
                if field_id in existing_field_ids:
                    continue
                fields.append(
                    _normalise_field(
                        {
                            "field_id": field_id,
                            "requirement": "required",
                            "delivery_extension": (
                                "PROGRAMMATIC_STAGE1_SUPPLEMENT"
                            ),
                            "claim_boundary": (
                                "Supplemental deterministic screening field; "
                                "it does not replace the corresponding formal "
                                "authority-profile field."
                            ),
                        },
                        definitions,
                        default_order=len(fields),
                    )
                )
                existing_field_ids.add(field_id)
        subtype_tokens = _as_string_list(
            raw_profile.get("conditional_subtype_tokens", raw_profile.get("subfamily_ids", raw_profile.get("subfamily_id")))
        )
        discriminator = raw_profile.get("discriminator")
        if discriminator is None and subtype_tokens:
            discriminator = {"field_id": "equipment_type", "contains": subtype_tokens}
        authority_columns_raw = raw_profile.get("authority_overview_columns", [])
        if (
            (not isinstance(authority_columns_raw, list) or not authority_columns_raw)
            and str(raw_profile.get("authority_section_id") or "").startswith("X")
        ):
            # X01-X05 are additive authority schedules.  They still need a
            # complete row projection for Aspen devices such as valves; the
            # global 3-2 overview row remains present and is not replaced.
            authority_columns_raw = _flatten_profile_fields(raw_profile)
        profiles.append({
            "profile_id": profile_id,
            "title": str(raw_profile.get("title") or profile_id),
            "family_ids": sorted(set(family_ids)),
            "subfamily_ids": sorted(set(subtype_tokens)),
            "discriminator": _json_safe(discriminator),
            "authority_section_id": raw_profile.get("authority_section_id"),
            "authority_overview_columns": [
                _normalise_field(item, definitions, default_order=index)
                for index, item in enumerate(authority_columns_raw)
            ] if isinstance(authority_columns_raw, list) else [],
            "fields": fields,
            "source_refs": sorted(set([
                *_as_string_list(raw_profile.get("source_refs")),
                *_as_string_list(raw_profile.get("authority_sources")),
            ])),
        })
    if common and not any(not profile.get("family_ids") for profile in profiles):
        # Global output columns apply even when the authority map explicitly
        # records that a matcher family has no dedicated T/X profile.
        profiles.append({
            "profile_id": "__common_delivery__",
            "title": "全设备通用客户交付字段",
            "family_ids": [],
            "subfamily_ids": [],
            "discriminator": None,
            "authority_section_id": None,
            "fields": copy.deepcopy(common),
            "source_refs": [],
        })
    if not profiles:
        raise CustomerDeliveryError("profile document contains no profiles")
    profiles.sort(key=lambda item: item["profile_id"])
    return {
        "schema": str(raw.get("schema") or "equipment-customer-output-profiles-v1"),
        "version": str(raw.get("version") or "unversioned"),
        "authority_sources": _json_safe([
            *_as_string_list(raw.get("authority_sources")),
            *_as_string_list(raw.get("authority_graph_sources")),
            *_as_string_list(raw.get("source_artifacts")),
        ]),
        "common_fields": _json_safe(common),
        "field_definitions": _json_safe(definitions),
        "minimum_output_authority": _json_safe(raw.get("minimum_output_authority", {})),
        "profiles": profiles,
        "source": _json_safe(source or {"kind": "in_memory"}),
        "fallback": bool(raw.get("fallback", False)),
    }


def load_customer_output_profiles(path: str | Path | None = None) -> dict[str, Any]:
    """Load the canonical JSON profile or the graph-13/30 fallback if absent."""

    profile_path = Path(path) if path is not None else DEFAULT_PROFILE_PATH
    if not profile_path.is_file():
        raw = fallback_output_profiles()
        return normalise_output_profiles(raw, source={
            "kind": "fallback_graph_schema",
            "requested_path": str(profile_path),
            "authority_sources": list(FALLBACK_AUTHORITY_SOURCES),
        })
    try:
        raw = json.loads(profile_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CustomerDeliveryError(f"cannot load customer output profiles: {exc}") from exc
    if not isinstance(raw, Mapping):
        raise CustomerDeliveryError("customer output profile root must be an object")
    return normalise_output_profiles(raw, source={
        "kind": "canonical_profile_file",
        "path": str(profile_path.resolve()),
        "sha256": _sha256_file(profile_path),
    })


def _verified_derivation_row_binding(item: Mapping[str, Any]) -> dict[str, Any]:
    """Verify and compact the final derivation-row binding for customer use."""

    declared_record_sha256 = str(
        item.get("program_generated_record_sha256") or ""
    ).upper()
    raw_binding = item.get("program_generated_record_binding")
    if not _HASH_RE.fullmatch(declared_record_sha256):
        raise CustomerDeliveryError(
            "physical Aspen derivation row has no valid "
            "program_generated_record_sha256"
        )
    if not isinstance(raw_binding, Mapping):
        raise CustomerDeliveryError(
            "physical Aspen derivation row has no program-generated binding"
        )
    binding = copy.deepcopy(dict(raw_binding))
    if (
        binding.get("schema") != "program-generated-stage1-row-binding-v1"
        or binding.get("deterministic") is not True
        or binding.get("program_generated") is not True
        or binding.get("llm_used") is not False
    ):
        raise CustomerDeliveryError(
            "physical Aspen derivation row binding contract is invalid"
        )
    declared_binding_sha256 = str(
        binding.get("binding_sha256") or ""
    ).upper()
    if not _HASH_RE.fullmatch(declared_binding_sha256):
        raise CustomerDeliveryError(
            "physical Aspen derivation row binding has no valid SHA-256"
        )
    hash_payload = copy.deepcopy(binding)
    hash_payload.pop("binding_sha256", None)
    actual_binding_sha256 = _sha256_json(hash_payload)
    if actual_binding_sha256 != declared_binding_sha256:
        raise CustomerDeliveryError(
            "program-generated Aspen derivation row binding SHA-256 mismatch"
        )
    if declared_record_sha256 != declared_binding_sha256:
        raise CustomerDeliveryError(
            "program_generated_record_sha256 does not match the verified "
            "derivation row binding"
        )
    bound_row = binding.get("bound_row")
    if not isinstance(bound_row, Mapping):
        raise CustomerDeliveryError(
            "program-generated Aspen derivation row binding has no bound_row"
        )
    identity = bound_row.get("identity")
    record_kind = bound_row.get("record_kind")
    if not _present(identity) or not _present(record_kind):
        raise CustomerDeliveryError(
            "program-generated Aspen derivation row identity is incomplete"
        )
    return {
        "derivation_record_kind": str(record_kind),
        "derivation_record_identity": str(identity),
        "program_generated_record_sha256": declared_record_sha256,
        "program_generated_record_binding_sha256": declared_binding_sha256,
        "program_generated_record_binding_schema": binding.get("schema"),
    }


def _unwrap_results(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        result: list[dict[str, Any]] = []
        for item in value:
            result.extend(_unwrap_results(item))
        return result
    if not isinstance(value, Mapping):
        raise CustomerDeliveryError("deterministic result must be an object or list")
    if value.get("schema") == "equipment-deterministic-match-result-v1":
        return [dict(value)]
    if value.get("schema") == "aspen-equipment-derivation-result-v1":
        results: list[dict[str, Any]] = []
        aggregate_binding = {
            "schema": value.get("schema"),
            "engine_version": value.get("engine_version"),
            "case_id": value.get("case_id"),
            "source_export_path": value.get("source_export_path"),
            "source_export_sha256": value.get("source_export_sha256"),
            "pfd_mapping_sha256": value.get("pfd_mapping_sha256"),
            "source_case_evidence": _json_safe(value.get("source_case_evidence", {})),
            "aspen_run_gate": _json_safe(value.get("aspen_run_gate", {})),
            "pipe_entity_reconciliation": _json_safe(
                value.get("pipe_entity_reconciliation", {})
            ),
        }
        aggregate_rows = [
            *(
                [("equipment", item) for item in value.get("equipment", [])]
                if isinstance(value.get("equipment"), list) else []
            ),
            *(
                [("piping", item) for item in value.get("piping", [])]
                if isinstance(value.get("piping"), list) else []
            ),
        ]
        for record_kind, item in aggregate_rows:
            if not isinstance(item, Mapping):
                continue
            if item.get("alias_only") is True:
                # Endpoint-state aliases are retained in the Aspen derivation
                # evidence bundle, but must never become duplicate physical
                # pipe rows in the customer selection overview.
                continue
            if (
                item.get("pipe_entity_scope")
                == "ASPEN_PHYSICAL_PIPE_BLOCK"
                and item.get("counted_as_physical_pipe") is True
            ):
                record_kind = "piping"
            match_result = item.get("match_result")
            if not isinstance(match_result, Mapping):
                continue
            if (
                item.get("aspen_mapping_status") == "NOT_APPLICABLE_SIMULATION_LOGIC_NODE"
                or match_result.get("status") == "NOT_APPLICABLE"
            ):
                continue
            row_source_binding = {
                **aggregate_binding,
                **_verified_derivation_row_binding(item),
            }
            enriched_match = dict(match_result)
            if isinstance(item.get("service_profile"), Mapping):
                enriched_match["_aspen_service_profile"] = dict(item["service_profile"])
            if isinstance(item.get("connection_component_selections"), Mapping):
                enriched_match["_aspen_connection_component_selections"] = dict(item["connection_component_selections"])
            pipe_specification = item.get("programmatic_pipe_specification")
            if not isinstance(pipe_specification, Mapping):
                pipe_specification = match_result.get("programmatic_pipe_specification")
            if isinstance(pipe_specification, Mapping):
                enriched_match["_programmatic_pipe_specification"] = dict(pipe_specification)
            valve_specification = item.get(
                "programmatic_valve_specification"
            )
            if not isinstance(valve_specification, Mapping):
                valve_specification = match_result.get(
                    "programmatic_valve_specification"
                )
            if isinstance(valve_specification, Mapping):
                enriched_match["_programmatic_valve_specification"] = dict(
                    valve_specification
                )
            delivery_values = (
                dict(item.get("canonical_match_input"))
                if isinstance(item.get("canonical_match_input"), Mapping)
                else {}
            )
            if record_kind == "piping":
                stream_id = item.get("stream_id") or delivery_values.get("stream_id")
                if _present(stream_id):
                    delivery_values.setdefault("equipment_tag", stream_id)
                    delivery_values.setdefault("line_number", stream_id)
                details = (
                    item.get("pfd_edge_label_data", {}).get("details", {})
                    if isinstance(item.get("pfd_edge_label_data"), Mapping)
                    and isinstance(item.get("pfd_edge_label_data", {}).get("details"), Mapping)
                    else {}
                )
                from_blocks = details.get("from_block_ids") if isinstance(details.get("from_block_ids"), list) else []
                to_blocks = details.get("to_block_ids") if isinstance(details.get("to_block_ids"), list) else []
                delivery_values.setdefault(
                    "source_endpoint",
                    ",".join(str(block) for block in from_blocks) if from_blocks else "PFD boundary",
                )
                delivery_values.setdefault(
                    "destination_endpoint",
                    ",".join(str(block) for block in to_blocks) if to_blocks else "PFD boundary",
                )
            parameter_lineage = [
                dict(entry)
                for entry in item.get("parameter_lineage", [])
                if isinstance(entry, Mapping) and _present(entry.get("target_field"))
            ] if isinstance(item.get("parameter_lineage"), list) else []
            enriched_match["_aspen_record_kind"] = record_kind
            enriched_match["_aspen_delivery_values"] = _json_safe(delivery_values)
            enriched_match["_aspen_parameter_lineage"] = _json_safe(parameter_lineage)
            enriched_match["_aspen_source_binding"] = _json_safe(
                row_source_binding
            )
            results.extend(_unwrap_results(enriched_match))
        if not results:
            raise CustomerDeliveryError("Aspen derivation contains no physical equipment or piping match results")
        return results
    if isinstance(value.get("results"), list):
        return _unwrap_results(value["results"])
    nested = value.get("result")
    if isinstance(nested, Mapping):
        if nested.get("schema") == "equipment-deterministic-match-result-v1":
            return [dict(nested)]
        if isinstance(nested.get("result"), Mapping):
            return _unwrap_results(nested["result"])
    raise CustomerDeliveryError("no equipment-deterministic-match-result-v1 object found")


def _validate_deterministic_node(node: Mapping[str, Any], name: str, expected_schema: str | None = None) -> None:
    if expected_schema and node.get("schema") != expected_schema:
        raise CustomerDeliveryError(f"{name} schema must be {expected_schema}")
    if node.get("deterministic") is not True:
        raise CustomerDeliveryError(f"{name} is not marked deterministic")
    if node.get("llm_used") is not False:
        estimates = node.get("model_estimate_inputs")
        controlled = (
            isinstance(estimates, list)
            and bool(estimates)
            and all(
                isinstance(item, Mapping)
                and item.get("source_kind") == "llm_last_resort_engineering_estimate"
                and item.get("evidence_class") == "J"
                and item.get("result_status") == "PROVISIONAL"
                and item.get("promotion_cap") == "TYPE_SCREENING"
                and item.get("overwrite_allowed") is False
                for item in estimates
            )
        )
        if not controlled:
            raise CustomerDeliveryError(
                f"{name} contains an uncontrolled LLM result instead of a bounded preliminary estimate"
            )


def _family_ids(result: Mapping[str, Any], package: Mapping[str, Any], model: Mapping[str, Any]) -> list[str]:
    exact = [
        result.get("match", {}).get("family_id") if isinstance(result.get("match"), Mapping) else None,
        package.get("family_id"),
        model.get("family_id"),
    ]
    exact_ids = sorted(set(str(item) for item in exact if _present(item)))
    if len(exact_ids) > 1:
        raise CustomerDeliveryError(f"family mismatch across deterministic objects: {exact_ids}")
    if exact_ids:
        return exact_ids
    candidates: set[str] = set()
    progress = result.get("progress", {})
    if isinstance(progress, Mapping):
        common = progress.get("most_general_common")
        if isinstance(common, Mapping):
            common = common.get("family_id") or common.get("id")
        candidates.update(_as_string_list(common))
        for item in progress.get("candidate_families", []) if isinstance(progress.get("candidate_families"), list) else []:
            if isinstance(item, Mapping):
                candidate = item.get("family_id") or item.get("id")
            else:
                candidate = item
            if _present(candidate):
                candidates.add(str(candidate))
    match = result.get("match", {})
    if isinstance(match, Mapping) and not candidates:
        for item in match.get("candidates", []) if isinstance(match.get("candidates"), list) else []:
            if isinstance(item, Mapping):
                candidate = item.get("family_id") or item.get("id")
            else:
                candidate = item
            if _present(candidate):
                candidates.add(str(candidate))
    return sorted(candidates)


def _row_index(package: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    state_rank = {"CALCULATED": 4, "PROVIDED": 3, "DERIVED": 3, "EXTERNAL_REQUIRED": 1, "MISSING": 0}
    rows: dict[str, dict[str, Any]] = {}
    for group in package.get("groups", []) if isinstance(package.get("groups"), list) else []:
        if not isinstance(group, Mapping):
            continue
        for row in group.get("rows", []) if isinstance(group.get("rows"), list) else []:
            if not isinstance(row, Mapping) or not _present(row.get("field_id")):
                continue
            field_id = str(row["field_id"])
            candidate = dict(row)
            current = rows.get(field_id)
            if current is None or state_rank.get(str(candidate.get("state")), -1) > state_rank.get(str(current.get("state")), -1):
                rows[field_id] = candidate
    return rows


def _effective_values(result: Mapping[str, Any], rows: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    effective_source = result.get("effective_normalized_input")
    if not isinstance(effective_source, Mapping):
        effective_source = result.get("normalized_input", {})
    values = dict(effective_source) if isinstance(effective_source, Mapping) else {}
    if isinstance(result.get("derived_parameters"), Mapping):
        values.update(result["derived_parameters"])
    for field_id, row in rows.items():
        if _present(row.get("raw_value")):
            values[field_id] = row.get("raw_value")
    return values


def _verified_programmatic_pipe_specification(value: Any) -> dict[str, Any]:
    """Verify the selector-owned pipe specification before customer projection."""

    if not isinstance(value, Mapping):
        return {}
    specification = copy.deepcopy(dict(value))
    if specification.get("schema") != "programmatic-pipe-specification-v1":
        raise CustomerDeliveryError("programmatic pipe specification schema is invalid")
    if specification.get("deterministic") is not True or specification.get("llm_used") is not False:
        raise CustomerDeliveryError("programmatic pipe specification is not deterministic")
    status = str(specification.get("status") or "")
    if status != "PRELIMINARY_CONCRETE_SPECIFICATION_SELECTED":
        return specification
    if specification.get("program_generated") is not True:
        raise CustomerDeliveryError("selected pipe specification is not marked program-generated")
    declared_hash = str(specification.get("program_specification_sha256") or "").upper()
    if not _HASH_RE.fullmatch(declared_hash):
        raise CustomerDeliveryError("selected pipe specification has no valid SHA-256 binding")
    fields = specification.get("fields")
    if not isinstance(fields, Mapping) or not fields:
        raise CustomerDeliveryError("selected pipe specification has no field descriptors")
    hash_payload = copy.deepcopy(specification)
    hash_payload.pop("program_specification_sha256", None)
    payload_fields = hash_payload.get("fields")
    if isinstance(payload_fields, Mapping):
        for field_id, descriptor in payload_fields.items():
            if not isinstance(descriptor, Mapping):
                raise CustomerDeliveryError(
                    f"pipe specification field {field_id!r} is not a descriptor"
                )
            descriptor.pop("program_specification_sha256", None)
    actual_hash = _sha256_json(hash_payload)
    if actual_hash != declared_hash:
        raise CustomerDeliveryError(
            "programmatic pipe specification SHA-256 does not match its canonical payload"
        )
    for field_id, descriptor in fields.items():
        if not isinstance(descriptor, Mapping):
            raise CustomerDeliveryError(
                f"pipe specification field {field_id!r} is not a descriptor"
            )
        if str(descriptor.get("program_specification_sha256") or "").upper() != declared_hash:
            raise CustomerDeliveryError(
                f"pipe specification field {field_id!r} is not bound to the specification hash"
            )
    return specification


def _verified_programmatic_valve_specification(value: Any) -> dict[str, Any]:
    """Verify the selector-owned valve specification before projection."""

    if not isinstance(value, Mapping):
        return {}
    specification = copy.deepcopy(dict(value))
    if specification.get("schema") != "programmatic-valve-specification-v1":
        raise CustomerDeliveryError(
            "programmatic valve specification schema is invalid"
        )
    if (
        specification.get("deterministic") is not True
        or specification.get("llm_used") is not False
    ):
        raise CustomerDeliveryError(
            "programmatic valve specification is not deterministic"
        )
    status = str(specification.get("status") or "")
    if status != "PRELIMINARY_CONCRETE_SPECIFICATION_SELECTED":
        return specification
    if specification.get("program_generated") is not True:
        raise CustomerDeliveryError(
            "selected valve specification is not marked program-generated"
        )
    declared_hash = str(
        specification.get("program_specification_sha256") or ""
    ).upper()
    if not _HASH_RE.fullmatch(declared_hash):
        raise CustomerDeliveryError(
            "selected valve specification has no valid SHA-256 binding"
        )
    fields = specification.get("fields")
    if not isinstance(fields, Mapping) or not fields:
        raise CustomerDeliveryError(
            "selected valve specification has no field descriptors"
        )
    hash_payload = copy.deepcopy(specification)
    hash_payload.pop("program_specification_sha256", None)
    payload_fields = hash_payload.get("fields")
    if isinstance(payload_fields, Mapping):
        for field_id, descriptor in payload_fields.items():
            if not isinstance(descriptor, Mapping):
                raise CustomerDeliveryError(
                    f"valve specification field {field_id!r} is not a descriptor"
                )
            descriptor.pop("program_specification_sha256", None)
    actual_hash = _sha256_json(hash_payload)
    if actual_hash != declared_hash:
        raise CustomerDeliveryError(
            "programmatic valve specification SHA-256 does not match its canonical payload"
        )
    for field_id, descriptor in fields.items():
        if not isinstance(descriptor, Mapping):
            raise CustomerDeliveryError(
                f"valve specification field {field_id!r} is not a descriptor"
            )
        if (
            str(
                descriptor.get("program_specification_sha256") or ""
            ).upper()
            != declared_hash
        ):
            raise CustomerDeliveryError(
                f"valve specification field {field_id!r} is not bound to the specification hash"
            )
    return specification


def _verified_engineering_adjustment_plan(value: Any) -> dict[str, Any]:
    """Verify a matcher-owned nonstandard/multi-unit modification plan."""

    if not isinstance(value, Mapping):
        return {}
    plan = copy.deepcopy(dict(value))
    if plan.get("schema") != "equipment-engineering-adjustment-plan-v1":
        raise CustomerDeliveryError(
            "engineering adjustment plan schema is invalid"
        )
    if (
        plan.get("deterministic") is not True
        or plan.get("program_generated") is not True
        or plan.get("manual_postprocessing") is not False
        or plan.get("llm_used") is not False
    ):
        raise CustomerDeliveryError(
            "engineering adjustment plan is not an unmodified deterministic program result"
        )
    declared_hash = str(plan.get("plan_sha256") or "").upper()
    if not _HASH_RE.fullmatch(declared_hash):
        raise CustomerDeliveryError(
            "engineering adjustment plan has no valid SHA-256 binding"
        )
    hash_payload = copy.deepcopy(plan)
    hash_payload.pop("plan_sha256", None)
    if _sha256_json(hash_payload) != declared_hash:
        raise CustomerDeliveryError(
            "engineering adjustment plan SHA-256 does not match its canonical payload"
        )
    if plan.get("triggered") is True:
        configuration = plan.get("configuration")
        if not isinstance(configuration, Mapping):
            raise CustomerDeliveryError(
                "triggered engineering adjustment plan has no configuration"
            )
        if not _present(
            configuration.get("candidate_model_or_designation")
        ):
            raise CustomerDeliveryError(
                "triggered engineering adjustment plan has no concrete system designation"
            )
        if not _present(plan.get("algorithmic_selection_warning")):
            raise CustomerDeliveryError(
                "triggered engineering adjustment plan has no mandatory warning"
            )
    return plan


def _verified_selection_agent_control(value: Any) -> dict[str, Any]:
    """Verify the calculate-before-select Agent control without promoting it."""

    if not isinstance(value, Mapping):
        return {}
    control = copy.deepcopy(dict(value))
    if control.get("schema") != "equipment-selection-agent-control-v1":
        raise CustomerDeliveryError(
            "selection Agent control schema is invalid"
        )
    if (
        control.get("deterministic") is not True
        or control.get("program_generated") is not True
        or control.get("llm_used") is not False
    ):
        raise CustomerDeliveryError(
            "selection Agent control is not deterministic"
        )
    declared_hash = str(
        control.get("agent_control_sha256") or ""
    ).upper()
    if not _HASH_RE.fullmatch(declared_hash):
        raise CustomerDeliveryError(
            "selection Agent control has no valid SHA-256 binding"
        )
    hash_payload = copy.deepcopy(control)
    hash_payload.pop("agent_control_sha256", None)
    if _sha256_json(hash_payload) != declared_hash:
        raise CustomerDeliveryError(
            "selection Agent control SHA-256 does not match its canonical payload"
        )
    return control


def _context(
    result: Mapping[str, Any],
    package_override: Mapping[str, Any] | None = None,
    model_override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    _validate_deterministic_node(result, "result", "equipment-deterministic-match-result-v1")
    package = dict(package_override or result.get("design_parameter_package") or {})
    model = dict(model_override or result.get("model_recommendation") or {})
    if package:
        _validate_deterministic_node(package, "parameter package", "equipment-design-parameter-package-v1")
    if model:
        _validate_deterministic_node(model, "model recommendation", "equipment-model-recommendation-v1")
    engineering_adjustment_plan = (
        _verified_engineering_adjustment_plan(
            result.get("engineering_adjustment_plan")
        )
    )
    selection_agent_control = _verified_selection_agent_control(
        result.get("selection_agent_control")
    )
    package_hash = package.get("selection_context", {}).get("sha256") if isinstance(package.get("selection_context"), Mapping) else None
    model_hash = model.get("selection_execution", {}).get("context_sha256") if isinstance(model.get("selection_execution"), Mapping) else None
    if _present(package_hash) and _present(model_hash) and str(package_hash).upper() != str(model_hash).upper():
        raise CustomerDeliveryError("parameter package and model recommendation context hashes differ")
    family_ids = _family_ids(result, package, model)
    rows = _row_index(package)
    values = _effective_values(result, rows)
    aspen_delivery_values = (
        dict(result.get("_aspen_delivery_values"))
        if isinstance(result.get("_aspen_delivery_values"), Mapping)
        else {}
    )
    for field_id, value in aspen_delivery_values.items():
        if _present(value) and not _present(values.get(str(field_id))):
            values[str(field_id)] = value
    aspen_parameter_lineage = {
        str(item.get("target_field")): dict(item)
        for item in result.get("_aspen_parameter_lineage", [])
        if isinstance(item, Mapping) and _present(item.get("target_field"))
    } if isinstance(result.get("_aspen_parameter_lineage"), list) else {}
    record_kind = str(result.get("_aspen_record_kind") or "equipment")
    pipe_specification: dict[str, Any] = {}
    raw_pipe_specification = result.get("_programmatic_pipe_specification")
    if not isinstance(raw_pipe_specification, Mapping):
        raw_pipe_specification = result.get("programmatic_pipe_specification")
    pipe_specification = _verified_programmatic_pipe_specification(
        raw_pipe_specification
    )
    if (
        pipe_specification.get("status")
        == "PRELIMINARY_CONCRETE_SPECIFICATION_SELECTED"
        and isinstance(pipe_specification.get("fields"), Mapping)
    ):
        for field_id, descriptor in pipe_specification["fields"].items():
            if isinstance(descriptor, Mapping) and _present(descriptor.get("value")):
                values[str(field_id)] = descriptor.get("value")
    raw_valve_specification = result.get(
        "_programmatic_valve_specification"
    )
    if not isinstance(raw_valve_specification, Mapping):
        raw_valve_specification = result.get(
            "programmatic_valve_specification"
        )
    valve_specification = _verified_programmatic_valve_specification(
        raw_valve_specification
    )
    if (
        valve_specification.get("status")
        == "PRELIMINARY_CONCRETE_SPECIFICATION_SELECTED"
        and isinstance(valve_specification.get("fields"), Mapping)
    ):
        for field_id, descriptor in valve_specification["fields"].items():
            if (
                isinstance(descriptor, Mapping)
                and _present(descriptor.get("value"))
            ):
                values[str(field_id)] = descriptor.get("value")
    tag = values.get("equipment_tag") or values.get("line_number")
    input_sha = str(result.get("input_sha256") or _sha256_json(result)).upper()
    if _present(tag):
        key = (
            f"{record_kind}:{str(tag).strip()}"
            if _present(result.get("_aspen_record_kind"))
            else str(tag).strip()
        )
    else:
        key = f"{record_kind}:UNASSIGNED-{input_sha[:16]}"
    family_name = None
    if isinstance(result.get("match"), Mapping):
        family_name = result["match"].get("family_name")
    estimates = [
        {
            "field_id": str(item.get("field_id") or ""),
            "value": _json_safe(item.get("value")),
            "target_unit": item.get("target_unit"),
            "state": str(item.get("state") or "PROVISIONAL"),
            "evidence_class": str(item.get("evidence_class") or "J"),
            "result_status": str(item.get("result_status") or "PROVISIONAL"),
            "promotion_cap": str(item.get("promotion_cap") or "TYPE_SCREENING"),
            "inference_basis": item.get("inference_basis"),
            "assumptions": list(item.get("assumptions", [])) if isinstance(item.get("assumptions"), list) else [],
            "context_refs": list(item.get("context_refs", [])) if isinstance(item.get("context_refs"), list) else [],
            "lower_bound": item.get("lower_bound"),
            "upper_bound": item.get("upper_bound"),
            "registered_allowed_values": (
                list(item.get("registered_allowed_values", []))
                if isinstance(item.get("registered_allowed_values"), list) else []
            ),
            "registry_id": item.get("registry_id"),
            "confidence": item.get("confidence"),
            "sensitivity_note": item.get("sensitivity_note"),
            "warning": item.get("warning"),
            "superseded_by": item.get("superseded_by"),
            "effective_value": _json_safe(item.get("effective_value")),
        }
        for item in result.get("model_estimate_inputs", [])
        if isinstance(item, Mapping) and _present(item.get("field_id"))
    ]
    estimate_fields = sorted({item["field_id"] for item in estimates})
    applied_estimate_fields = sorted({
        item["field_id"] for item in estimates
        if item["state"] != "SUPERSEDED_BY_DETERMINISTIC_CALCULATION"
    })
    superseded_estimate_fields = sorted(set(estimate_fields) - set(applied_estimate_fields))
    llm_used = bool(result.get("llm_used")) and bool(estimates)
    if applied_estimate_fields:
        estimate_statement = (
            "含大模型最后一级工程估算："
            + "、".join(applied_estimate_fields)
            + "。这些值均为 J/provisional，仅用于 TYPE_SCREENING；正式选型前必须用同工况证据替换并重算。"
        )
    elif superseded_estimate_fields:
        estimate_statement = (
            "大模型曾提出估算："
            + "、".join(superseded_estimate_fields)
            + "；已由注册程序公式复算覆盖，估算值未进入最终选择参数。"
        )
    else:
        estimate_statement = "未使用大模型工程估算。"
    model_estimate_disclosure = {
        "llm_used": llm_used,
        "status": "PROVISIONAL_ESTIMATES_USED" if applied_estimate_fields else (
            "MODEL_ESTIMATES_SUPERSEDED" if superseded_estimate_fields else "NOT_USED"
        ),
        "model_estimate_fields": estimate_fields,
        "applied_model_estimate_fields": applied_estimate_fields,
        "superseded_model_estimate_fields": superseded_estimate_fields,
        "estimates": estimates,
        "evidence_class": "J" if estimates else None,
        "promotion_cap": "TYPE_SCREENING" if applied_estimate_fields else None,
        "statement": estimate_statement,
    }
    return {
        "result": dict(result),
        "package": package,
        "model": model,
        "rows": rows,
        "values": values,
        "family_ids": family_ids,
        "family_name": family_name,
        "equipment_tag": tag,
        "equipment_key": key,
        "input_sha256": input_sha,
        "llm_used": llm_used,
        "model_estimate_inputs": estimates,
        "model_estimate_disclosure": model_estimate_disclosure,
        "engineering_adjustment_plan": _json_safe(
            engineering_adjustment_plan
        ),
        "selection_agent_control": _json_safe(
            selection_agent_control
        ),
        "service_profile": (
            dict(result.get("_aspen_service_profile"))
            if isinstance(result.get("_aspen_service_profile"), Mapping)
            else {}
        ),
        "connection_component_selections": (
            dict(result.get("_aspen_connection_component_selections"))
            if isinstance(result.get("_aspen_connection_component_selections"), Mapping)
            else {}
        ),
        "record_kind": record_kind,
        "programmatic_pipe_specification": _json_safe(pipe_specification),
        "programmatic_valve_specification": _json_safe(
            valve_specification
        ),
        "aspen_delivery_values": _json_safe(aspen_delivery_values),
        "aspen_parameter_lineage": _json_safe(aspen_parameter_lineage),
        "aspen_source_binding": (
            dict(result.get("_aspen_source_binding"))
            if isinstance(result.get("_aspen_source_binding"), Mapping)
            else {}
        ),
    }


def _discriminator_match(discriminator: Any, values: Mapping[str, Any]) -> bool | None:
    if not isinstance(discriminator, Mapping) or not discriminator:
        return None
    field_id = discriminator.get("field_id") or discriminator.get("field")
    if not _present(field_id):
        return None
    field_id = str(field_id)
    if field_id not in values or not _present(values.get(field_id)):
        return None
    actual = _token(values[field_id])
    expected = discriminator.get("equals", discriminator.get("in"))
    if expected is not None:
        return actual in {_token(item) for item in _as_string_list(expected)}
    contains = discriminator.get("contains")
    if contains is not None:
        return any(_token(item) in actual for item in _as_string_list(contains))
    return None


def _selected_profiles(context: Mapping[str, Any], profiles: Mapping[str, Any]) -> list[dict[str, Any]]:
    family_ids = set(context["family_ids"])
    all_profiles = [dict(item) for item in profiles.get("profiles", [])]
    family_profiles = [
        item for item in all_profiles
        if family_ids.intersection(item.get("family_ids", []))
    ] if family_ids else []
    generic = [item for item in all_profiles if not item.get("family_ids")]
    if not family_profiles:
        return sorted(generic, key=lambda item: item["profile_id"])
    base = [item for item in family_profiles if not item.get("discriminator") and not item.get("subfamily_ids")]
    specialised = [item for item in family_profiles if item not in base]
    decisions = [(item, _discriminator_match(item.get("discriminator"), context["values"])) for item in specialised]
    matched = [item for item, decision in decisions if decision is True]
    unknown = [item for item, decision in decisions if decision is None]
    if matched:
        chosen = [*base, *matched]
    elif unknown:
        # A discriminator that cannot be resolved is not permission to pick a
        # branch.  Keep the union of all plausible profiles.
        chosen = [*base, *specialised]
    else:
        chosen = base or family_profiles
    return sorted({item["profile_id"]: item for item in chosen}.values(), key=lambda item: item["profile_id"])


def _union_fields(selected_profiles: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    fields: dict[str, dict[str, Any]] = {}
    for profile in selected_profiles:
        for field in profile.get("fields", []):
            if not isinstance(field, Mapping):
                continue
            field_id = str(field.get("field_id"))
            if field_id not in fields:
                fields[field_id] = copy.deepcopy(dict(field))
                fields[field_id]["profile_ids"] = [profile["profile_id"]]
                continue
            current = fields[field_id]
            current["profile_ids"] = sorted(set([*current.get("profile_ids", []), profile["profile_id"]]))
            current["source_fields"] = sorted(set([*current.get("source_fields", []), *field.get("source_fields", [])]))
            current["source_refs"] = sorted(set([*current.get("source_refs", []), *field.get("source_refs", [])]))
            if str(field.get("requirement", "required")) == "required":
                current["requirement"] = "required"
            if current.get("unit") != field.get("unit") and _present(current.get("unit")) and _present(field.get("unit")):
                current.setdefault("metadata_conflicts", []).append({
                    "property": "unit", "values": sorted({str(current.get("unit")), str(field.get("unit"))}),
                })
                current["unit"] = None
    return sorted(fields.values(), key=lambda item: (int(item.get("order", 1_000_000)), item["field_id"]))


def _model_status(context: Mapping[str, Any]) -> str:
    pipe_specification = context.get("programmatic_pipe_specification", {})
    if (
        isinstance(pipe_specification, Mapping)
        and pipe_specification.get("status")
        == "PRELIMINARY_CONCRETE_SPECIFICATION_SELECTED"
    ):
        return "preliminary_concrete_specification_selected"
    adjustment_plan = context.get("engineering_adjustment_plan", {})
    if (
        isinstance(adjustment_plan, Mapping)
        and adjustment_plan.get("triggered") is True
    ):
        if (
            adjustment_plan.get("status")
            == "REVIEW_REQUIRED_NO_SAFE_AUTOMATIC_CONFIGURATION"
        ):
            return "algorithmic_configuration_review_required"
        return "algorithmic_modification_screening_only"
    result = context["result"]
    decision = result.get("model_decision", {}) if isinstance(result.get("model_decision"), Mapping) else {}
    model = context["model"]
    return str(decision.get("model_status") or model.get("formal_model_status") or model.get("status") or "not_established")


def _unverified_cross_standard_source(source: Mapping[str, Any]) -> bool:
    """Reject a stitched standard identity unless a registered rule binds it."""

    registered_rule = any(
        _present(source.get(field_id))
        for field_id in (
            "registered_cross_standard_compatibility_rule",
            "registered_cross_standard_compatibility_rule_sha256",
            "registered_composition_rule_sha256",
        )
    )
    if registered_rule:
        return False
    explicit_flags = (
        "cross_standard_stitching",
        "cross_standard_assembly",
        "mixed_standard_identity",
        "standard_fragment_stitching",
    )
    if any(source.get(field_id) is True for field_id in explicit_flags):
        return True
    composition_kind = str(source.get("composition_kind") or "").upper()
    return composition_kind in {
        "CROSS_STANDARD_STITCHING",
        "UNREGISTERED_CROSS_STANDARD_ASSEMBLY",
        "MIXED_STANDARD_FRAGMENTS",
    }


def _candidate_program_origin(
    candidate: Mapping[str, Any],
    source_kind: str,
) -> str:
    declared = str(candidate.get("program_origin") or "").strip()
    if declared:
        return declared
    return {
        "knowledge_graph_model_rule": "DETERMINISTIC_ENGINEERING_SELECTOR",
        "deterministic_programmatic_pipe_specification": (
            "PROGRAMMATIC_PIPE_SELECTOR"
        ),
        "deterministic_programmatic_valve_specification": (
            "PROGRAMMATIC_VALVE_SELECTOR"
        ),
        "bundled_standard_reference_catalog": "DETERMINISTIC_STANDARD_CATALOG",
        "user_supplied_machine_verified_candidate": (
            "MACHINE_VERIFIED_SUPPLIED_CANDIDATE"
        ),
        "user_supplied_unverified_candidate": "UNVERIFIED_SUPPLIED_INPUT",
    }.get(source_kind, "UNTRACEABLE_CANDIDATE_ORIGIN")


def _leading_candidate_audit(context: Mapping[str, Any]) -> dict[str, Any]:
    """Validate that the displayed designation came from an admissible candidate."""

    model = context.get("model", {})
    leading = (
        model.get("leading_candidate")
        if isinstance(model, Mapping)
        and isinstance(model.get("leading_candidate"), Mapping)
        else {}
    )
    if not leading:
        if (
            _model_status(context) == "final_model"
            and isinstance(model, Mapping)
            and _present(model.get("formal_model"))
        ):
            return {
                "candidate_id": "formal_model_record",
                "candidate_kind": "formal_model",
                "candidate_status": "MACHINE_VERIFIED_FINAL_MODEL",
                "candidate_eligibility": "FORMAL_READY",
                "candidate_source_kind": "formal_model_decision",
                "eligible_for_leading_candidate": True,
                "program_origin": "MACHINE_VERIFIED_FORMAL_MODEL",
                "standard_scope_state": "MACHINE_VERIFIED_RECORD",
                "selection_rule_identity": "FORMAL_MODEL_DECISION",
                "validation_checks": {
                    "candidate_present": True,
                    "designation_present": True,
                    "candidate_kind_admissible": True,
                    "candidate_status_admissible": True,
                    "candidate_eligibility_admissible": True,
                    "candidate_source_admissible": True,
                    "leading_candidate_eligible": True,
                    "standard_scope_admissible": True,
                    "selection_rule_identity_present": True,
                    "cross_standard_stitching_absent": True,
                },
                "validation_blockers": [],
                "valid_for_specificity": True,
            }
        return {
            "candidate_id": None,
            "candidate_kind": None,
            "candidate_status": None,
            "candidate_eligibility": None,
            "candidate_source_kind": None,
            "eligible_for_leading_candidate": False,
            "program_origin": "UNTRACEABLE_CANDIDATE_ORIGIN",
            "standard_scope_state": "NOT_ESTABLISHED",
            "selection_rule_identity": None,
            "validation_checks": {"candidate_present": False},
            "validation_blockers": ["LEADING_CANDIDATE_MISSING"],
            "valid_for_specificity": False,
        }

    source = (
        dict(leading.get("source"))
        if isinstance(leading.get("source"), Mapping)
        else {}
    )
    candidate_kind = str(leading.get("candidate_kind") or "").strip()
    candidate_status = str(leading.get("status") or "").strip()
    candidate_eligibility = str(
        leading.get("candidate_eligibility") or ""
    ).strip()
    source_kind = str(source.get("kind") or "").strip()
    program_origin = _candidate_program_origin(leading, source_kind)
    formally_verified_supplied = (
        source_kind == "user_supplied_machine_verified_candidate"
        and candidate_eligibility == "FORMAL_READY"
        and candidate_status == "MACHINE_VERIFIED_SUPPLIED_FINAL_MODEL"
        and bool(leading.get("formal_model"))
    )
    admissible_kinds = {
        "standard_marking",
        "engineered_designation",
        "component_marking",
        "vendor_candidate",
    }
    admissible_eligibility = {
        "READY_FOR_ENGINEERING_REVIEW",
        "SCREENING_ONLY_EVIDENCE_OPEN",
        "IDENTITY_ONLY",
        "FORMAL_READY",
    }
    admissible_sources = {
        "knowledge_graph_model_rule",
        "bundled_standard_reference_catalog",
        "deterministic_programmatic_pipe_specification",
        "deterministic_programmatic_valve_specification",
        "user_supplied_machine_verified_candidate",
    }
    status_admissible = bool(candidate_status) and not (
        candidate_status.startswith("REJECTED_")
        or "CONSTRAINT_FAIL" in candidate_status
    )
    cross_standard_absent = not _unverified_cross_standard_source(source)

    if source_kind == "bundled_standard_reference_catalog":
        standard_scope_admissible = (
            leading.get("eligible_under_known_standard_scope") is True
            and str(source.get("reuse_class") or "")
            in {
                "DIRECT_REUSE_VERIFIED",
                "direct_reuse",
                "direct_reuse_standard_design_point",
            }
        )
        standard_scope_state = (
            "VERIFIED_STANDARD_SCOPE"
            if standard_scope_admissible
            else "STANDARD_SCOPE_NOT_VERIFIED"
        )
        selection_rule_identity_present = bool(
            _present(source.get("catalog_path"))
            and _present(source.get("catalog_sha256"))
        )
        selection_rule_identity = "BUNDLED_STANDARD_REFERENCE_CATALOG"
    elif source_kind == "knowledge_graph_model_rule":
        standard_scope_admissible = (
            leading.get("eligible_under_known_standard_scope") is not False
        )
        standard_scope_state = (
            "NO_EXPLICIT_STANDARD_SCOPE_FAILURE"
            if standard_scope_admissible
            else "STANDARD_SCOPE_FAILED"
        )
        selection_rule_identity_present = bool(
            _present(source.get("model_rule_path"))
            and _present(source.get("model_rule_sha256"))
        )
        selection_rule_identity = "KNOWLEDGE_GRAPH_MODEL_RULE"
    elif (
        source_kind
        == "deterministic_programmatic_pipe_specification"
    ):
        standard_scope_admissible = True
        standard_scope_state = (
            "PROGRAMMATIC_PRELIMINARY_SCOPE_FORMAL_STANDARDS_OPEN"
        )
        selection_rule_identity_present = bool(
            _HASH_RE.fullmatch(
                str(
                    source.get("program_specification_sha256") or ""
                ).upper()
            )
        )
        selection_rule_identity = "PROGRAMMATIC_PIPE_SPECIFICATION"
    elif (
        source_kind
        == "deterministic_programmatic_valve_specification"
    ):
        standard_scope_admissible = True
        standard_scope_state = (
            "PROGRAMMATIC_PRELIMINARY_SCOPE_FORMAL_STANDARDS_OPEN"
        )
        selection_rule_identity_present = bool(
            _HASH_RE.fullmatch(
                str(
                    source.get("program_specification_sha256") or ""
                ).upper()
            )
            and _HASH_RE.fullmatch(
                str(source.get("selector_rule_sha256") or "").upper()
            )
        )
        selection_rule_identity = (
            "PROGRAMMATIC_VALVE_SPECIFICATION"
        )
    elif formally_verified_supplied:
        standard_scope_admissible = True
        standard_scope_state = "MACHINE_VERIFIED_FINAL_MODEL"
        selection_rule_identity_present = True
        selection_rule_identity = "MACHINE_VERIFIED_SUPPLIED_CANDIDATE"
    else:
        standard_scope_admissible = False
        standard_scope_state = "STANDARD_SCOPE_NOT_VERIFIED"
        selection_rule_identity_present = False
        selection_rule_identity = None

    checks = {
        "candidate_present": True,
        "designation_present": _present(leading.get("designation")),
        "candidate_kind_admissible": (
            candidate_kind in admissible_kinds or formally_verified_supplied
        ),
        "candidate_status_admissible": status_admissible,
        "candidate_eligibility_admissible": (
            candidate_eligibility in admissible_eligibility
            or candidate_eligibility.startswith("TYPE_IDENTITY_ONLY_")
            or candidate_eligibility
            == "IDENTITY_AND_PRELIMINARY_GEOMETRY_ONLY"
        ),
        "candidate_source_admissible": source_kind in admissible_sources,
        "leading_candidate_eligible": (
            leading.get("eligible_for_leading_candidate") is True
        ),
        "standard_scope_admissible": standard_scope_admissible,
        "selection_rule_identity_present": selection_rule_identity_present,
        "cross_standard_stitching_absent": cross_standard_absent,
    }
    blockers = [
        check_id.upper()
        for check_id, passed in checks.items()
        if not passed
    ]
    if source_kind == "user_supplied_unverified_candidate":
        blockers.append("USER_SUPPLIED_UNVERIFIED_CANDIDATE")
    if candidate_kind == "unclassified_supplied_designation" and not formally_verified_supplied:
        blockers.append("UNCLASSIFIED_SUPPLIED_DESIGNATION")
    if candidate_eligibility == "CONSTRAINT_FAIL_FAMILY_ONLY":
        blockers.append("CONSTRAINT_FAIL_FAMILY_ONLY")
    blockers = sorted(set(blockers))
    return {
        "candidate_id": leading.get("candidate_id"),
        "candidate_kind": candidate_kind or None,
        "candidate_status": candidate_status or None,
        "candidate_eligibility": candidate_eligibility or None,
        "candidate_source_kind": source_kind or None,
        "eligible_for_leading_candidate": (
            leading.get("eligible_for_leading_candidate") is True
        ),
        "program_origin": program_origin,
        "standard_scope_state": standard_scope_state,
        "selection_rule_identity": selection_rule_identity,
        "validation_checks": checks,
        "validation_blockers": blockers,
        "valid_for_specificity": not blockers,
    }


def _model_value(context: Mapping[str, Any]) -> tuple[Any, str]:
    pipe_specification = context.get("programmatic_pipe_specification", {})
    if (
        isinstance(pipe_specification, Mapping)
        and pipe_specification.get("status")
        == "PRELIMINARY_CONCRETE_SPECIFICATION_SELECTED"
        and _present(pipe_specification.get("designation"))
    ):
        return (
            pipe_specification.get("designation"),
            "PROGRAMMATIC_PIPE_ENGINEERING_DESIGNATION",
        )
    valve_specification = context.get(
        "programmatic_valve_specification", {}
    )
    if (
        isinstance(valve_specification, Mapping)
        and valve_specification.get("status")
        == "PRELIMINARY_CONCRETE_SPECIFICATION_SELECTED"
        and _present(valve_specification.get("designation"))
    ):
        return (
            valve_specification.get("designation"),
            "PROGRAMMATIC_VALVE_ENGINEERING_DESIGNATION",
        )
    adjustment_plan = context.get("engineering_adjustment_plan", {})
    adjustment_configuration = (
        adjustment_plan.get("configuration", {})
        if isinstance(adjustment_plan, Mapping)
        else {}
    )
    if (
        isinstance(adjustment_plan, Mapping)
        and adjustment_plan.get("triggered") is True
        and isinstance(adjustment_configuration, Mapping)
        and _present(
            adjustment_configuration.get(
                "candidate_model_or_designation"
            )
        )
    ):
        return (
            adjustment_configuration.get(
                "candidate_model_or_designation"
            ),
            "ALGORITHMIC_SYSTEM_MODIFICATION_DESIGNATION",
        )
    model = context["model"]
    status = _model_status(context)
    if status == "final_model" and _present(model.get("formal_model")):
        return model.get("formal_model"), "FORMAL_MODEL"
    if "family_tower" in context.get("family_ids", []):
        # Historical tower designations embedded screening diameter, layout
        # height and formula-only thickness.  A safe current designation keeps
        # the concrete type, Aspen stage count and explicit formal OPEN labels,
        # but never promotes screening geometry into the customer model field.
        leading = (
            model.get("leading_candidate")
            if isinstance(model.get("leading_candidate"), Mapping)
            else {}
        )
        safe_designation = leading.get("designation")
        forbidden_screening_tokens = (
            "Di_screen=",
            "H_layout_screen=",
            "shell_formula_t=",
            " | Di=",
            "H_body=",
        )
        if (
            _present(safe_designation)
            and "N_stage_Aspen=" in str(safe_designation)
            and "Di_formal=OPEN" in str(safe_designation)
            and "H_formal=OPEN" in str(safe_designation)
            and not any(
                token in str(safe_designation)
                for token in forbidden_screening_tokens
            )
        ):
            return (
                safe_designation,
                "TOWER_TYPE_AND_ASPEN_STAGE_FORMAL_GEOMETRY_OPEN",
            )
        for source in (
            model.get("recommended_type"),
            context.get("values", {}).get("equipment_type"),
            context.get("values", {}).get("tower_internals_type"),
        ):
            if _present(source):
                return source, "TOWER_TYPE_ONLY_FORMAL_GEOMETRY_OPEN"
        return None, "MISSING"
    leading = model.get("leading_candidate") if isinstance(model.get("leading_candidate"), Mapping) else {}
    value = leading.get("designation") if isinstance(leading, Mapping) else None
    if not _present(value):
        decision = context["result"].get("model_decision", {})
        if isinstance(decision, Mapping):
            value = decision.get("generated_candidate_model")
    if _present(value):
        return value, "CANDIDATE_OR_ENGINEERING_DESIGNATION"
    if _present(model.get("recommended_type")):
        return model.get("recommended_type"), "TYPE_ONLY"
    return None, "MISSING"


def _programmatic_pipe_spec_cell(
    source_field: str,
    context: Mapping[str, Any],
) -> dict[str, Any] | None:
    specification = context.get("programmatic_pipe_specification")
    if not isinstance(specification, Mapping):
        return None
    if (
        specification.get("status")
        != "PRELIMINARY_CONCRETE_SPECIFICATION_SELECTED"
    ):
        return None
    fields = specification.get("fields")
    descriptor = fields.get(source_field) if isinstance(fields, Mapping) else None
    if not isinstance(descriptor, Mapping) or not _present(descriptor.get("value")):
        return None
    declared_hash = str(
        specification.get("program_specification_sha256") or ""
    ).upper()
    source_binding = (
        dict(specification.get("source_binding"))
        if isinstance(specification.get("source_binding"), Mapping)
        else {}
    )
    standard_selections = (
        dict(specification.get("standard_selections"))
        if isinstance(specification.get("standard_selections"), Mapping)
        else {}
    )
    formal_readiness = (
        dict(specification.get("formal_readiness"))
        if isinstance(specification.get("formal_readiness"), Mapping)
        else {}
    )
    source: dict[str, Any] = {
        "kind": "deterministic_programmatic_pipe_specification",
        "field_id": source_field,
        "program_generated": True,
        "deterministic": True,
        "llm_used": False,
        "specification_status": specification.get("status"),
        "program_specification_sha256": declared_hash,
        "field_evidence_class": descriptor.get("evidence_class"),
        "promotion_cap": descriptor.get("promotion_cap"),
        "source_binding_sha256": _sha256_json(source_binding),
        "source_binding_scope": (
            "DERIVATION_RECORD_PROGRAMMATIC_PIPE_SPECIFICATION"
        ),
        "standard_selections_sha256": _sha256_json(standard_selections),
        "formal_readiness_status": formal_readiness.get("status"),
        "formal_readiness_sha256": _sha256_json(formal_readiness),
    }
    lineage = (
        context.get("aspen_parameter_lineage", {}).get(source_field)
        if isinstance(context.get("aspen_parameter_lineage"), Mapping)
        else None
    )
    if isinstance(lineage, Mapping):
        source["aspen_parameter_lineage"] = _json_safe(lineage)
        source["aspen_parameter_lineage_sha256"] = _sha256_json(lineage)
    aggregate_binding = context.get("aspen_source_binding")
    if isinstance(aggregate_binding, Mapping) and aggregate_binding:
        source["aspen_source_binding"] = _json_safe(aggregate_binding)
        source["aspen_source_binding_sha256"] = _sha256_json(aggregate_binding)
    return {
        "value": _json_safe(descriptor.get("value")),
        "unit": descriptor.get("unit"),
        "state": str(descriptor.get("state") or "PROGRAM_PRELIMINARY_SELECTED"),
        "source": source,
    }


def _programmatic_valve_spec_cell(
    source_field: str,
    context: Mapping[str, Any],
) -> dict[str, Any] | None:
    specification = context.get("programmatic_valve_specification")
    if not isinstance(specification, Mapping):
        return None
    if (
        specification.get("status")
        != "PRELIMINARY_CONCRETE_SPECIFICATION_SELECTED"
    ):
        return None
    fields = specification.get("fields")
    descriptor = (
        fields.get(source_field) if isinstance(fields, Mapping) else None
    )
    if (
        not isinstance(descriptor, Mapping)
        or not _present(descriptor.get("value"))
    ):
        return None
    declared_hash = str(
        specification.get("program_specification_sha256") or ""
    ).upper()
    source_binding = (
        dict(specification.get("source_binding"))
        if isinstance(specification.get("source_binding"), Mapping)
        else {}
    )
    adjacent_line_binding = (
        dict(specification.get("adjacent_line_binding"))
        if isinstance(
            specification.get("adjacent_line_binding"), Mapping
        )
        else {}
    )
    selector_rule = (
        dict(specification.get("selector_rule"))
        if isinstance(specification.get("selector_rule"), Mapping)
        else {}
    )
    formal_readiness = (
        dict(specification.get("formal_readiness"))
        if isinstance(specification.get("formal_readiness"), Mapping)
        else {}
    )
    source: dict[str, Any] = {
        "kind": "deterministic_programmatic_valve_specification",
        "field_id": source_field,
        "program_generated": True,
        "deterministic": True,
        "llm_used": False,
        "specification_status": specification.get("status"),
        "program_specification_sha256": declared_hash,
        "field_evidence_class": descriptor.get("evidence_class"),
        "promotion_cap": descriptor.get("promotion_cap"),
        "source_binding_sha256": _sha256_json(source_binding),
        "source_binding_scope": (
            "DERIVATION_RECORD_PROGRAMMATIC_VALVE_SPECIFICATION"
        ),
        "adjacent_line_binding_sha256": _sha256_json(
            adjacent_line_binding
        ),
        "selector_rule": _json_safe(selector_rule),
        "selector_rule_sha256": specification.get(
            "selector_rule_sha256"
        ),
        "formal_readiness_status": formal_readiness.get("status"),
        "formal_readiness_sha256": _sha256_json(formal_readiness),
    }
    lineage = (
        context.get("aspen_parameter_lineage", {}).get(source_field)
        if isinstance(context.get("aspen_parameter_lineage"), Mapping)
        else None
    )
    if isinstance(lineage, Mapping):
        source["aspen_parameter_lineage"] = _json_safe(lineage)
        source["aspen_parameter_lineage_sha256"] = _sha256_json(lineage)
    aggregate_binding = context.get("aspen_source_binding")
    if isinstance(aggregate_binding, Mapping) and aggregate_binding:
        source["aspen_source_binding"] = _json_safe(aggregate_binding)
        source["aspen_source_binding_sha256"] = _sha256_json(
            aggregate_binding
        )
    return {
        "value": _json_safe(descriptor.get("value")),
        "unit": descriptor.get("unit"),
        "state": str(
            descriptor.get("state") or "PROGRAM_PRELIMINARY_SELECTED"
        ),
        "source": source,
    }


PFD_CUSTOMER_LINEAGE_ALIASES: dict[str, tuple[str, ...]] = {
    # The matcher normalises these PFD fields to customer-facing canonical
    # names, while the Aspen derivation intentionally keeps the more explicit
    # process-side target names in parameter_lineage.
    "equipment_tag": ("line_number",),
    "temperature_c": ("operating_temperature_c",),
    "line_origin": ("source_endpoint",),
    "line_destination": ("destination_endpoint",),
    "main_medium": ("medium_name",),
    "viscosity_mpa_s": (
        "dynamic_viscosity_mpa_s",
        "liquid_dynamic_viscosity_mpa_s",
    ),
}


def _lineage_values_equal(left: Any, right: Any) -> bool:
    """Compare a projected value with its lineage value conservatively."""

    if isinstance(left, bool) or isinstance(right, bool):
        return left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        left_number = float(left)
        right_number = float(right)
        if not math.isfinite(left_number) or not math.isfinite(right_number):
            return left_number == right_number
        return math.isclose(
            left_number,
            right_number,
            rel_tol=1e-10,
            abs_tol=1e-12,
        )
    return left == right


def _parameter_lineage_for_customer_field(
    source_field: str,
    context: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    """Resolve exact or registered PFD alias lineage without guessing."""

    lineages = context.get("aspen_parameter_lineage")
    if not isinstance(lineages, Mapping):
        return None
    exact = lineages.get(source_field)
    if isinstance(exact, Mapping):
        return exact
    if (
        str(context.get("record_kind") or "") != "piping"
        and "family_process_piping" not in context.get("family_ids", [])
    ):
        return None
    aliases = PFD_CUSTOMER_LINEAGE_ALIASES.get(source_field, ())
    if not aliases:
        return None
    row = (
        context.get("rows", {}).get(source_field)
        if isinstance(context.get("rows"), Mapping)
        else None
    )
    projected_value = (
        row.get("raw_value")
        if isinstance(row, Mapping) and _present(row.get("raw_value"))
        else context.get("values", {}).get(source_field)
        if isinstance(context.get("values"), Mapping)
        else None
    )
    for alias in aliases:
        candidate = lineages.get(alias)
        if not isinstance(candidate, Mapping):
            continue
        lineage_value = candidate.get("value")
        if (
            _present(projected_value)
            and _present(lineage_value)
            and not _lineage_values_equal(projected_value, lineage_value)
        ):
            continue
        return candidate
    return None


def _aspen_process_lineage(lineage: Any) -> bool:
    if not isinstance(lineage, Mapping):
        return False
    return (
        str(lineage.get("origin") or "").upper() == "ASPEN_DERIVED"
        or str(lineage.get("evidence_scope") or "").upper().startswith("ASPEN_")
        or str(lineage.get("source_path") or "").startswith("\\Data\\")
    )


def _service_profile_medium_cell(
    context: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Project a closed inlet mole-fraction observation as a medium label."""

    profile = context.get("service_profile")
    if not isinstance(profile, Mapping):
        return None
    observations = [
        item
        for item in profile.get("raw_observations", [])
        if isinstance(item, Mapping)
        and item.get("field") == "composition_fraction"
        and str(item.get("observation_id") or "").split(":")[1:2] == ["inlet"]
        and isinstance(item.get("value"), (int, float))
        and str(item.get("basis") or "").startswith("mole_fraction;component:")
    ]
    if not observations:
        return None
    total = sum(float(item["value"]) for item in observations)
    if not math.isclose(total, 1.0, rel_tol=1e-6, abs_tol=1e-6):
        return None
    components = sorted(
        (
            str(item["basis"]).split("component:", 1)[1],
            float(item["value"]),
        )
        for item in observations
    )
    label = " + ".join(
        f"{component} ({fraction * 100:g} mol%)"
        for component, fraction in components
    )
    source_binding = context.get("aspen_source_binding", {})
    return {
        "value": label,
        "unit": None,
        "state": "DERIVED_FROM_ASPEN",
        "source": {
            "kind": "aspen_service_profile_composition_projection",
            "evidence_class": "D",
            "promotion_cap": "PROCESS_SIDE_ONLY",
            "formal_design_evidence": False,
            "composition_basis": "mole_fraction",
            "input_observation_ids": sorted(
                str(item.get("observation_id")) for item in observations
            ),
            "service_profile_context_sha256": profile.get(
                "profile_context_sha256"
            ),
            "aspen_source_binding": _json_safe(source_binding),
            "aspen_source_binding_sha256": _sha256_json(source_binding),
            "program_generated": True,
        },
    }


def _pump_audit_projection_cell(
    source_field: str,
    context: Mapping[str, Any],
) -> dict[str, Any] | None:
    if "family_pump" not in context.get("family_ids", []):
        return None
    values = context.get("values", {})
    power_audit = (
        values.get("pump_power_process_audit")
        if isinstance(values, Mapping)
        and isinstance(values.get("pump_power_process_audit"), Mapping)
        else {}
    )
    npsha_audit = (
        values.get("pump_npsha_process_audit")
        if isinstance(values, Mapping)
        and isinstance(values.get("pump_npsha_process_audit"), Mapping)
        else {}
    )
    source_binding = context.get("aspen_source_binding", {})

    def source(audit: Mapping[str, Any], *, evidence_class: str = "D") -> dict[str, Any]:
        return {
            "kind": "deterministic_pump_process_audit_projection",
            "evidence_class": evidence_class,
            "promotion_cap": (
                "TYPE_SCREENING" if evidence_class == "D" else "NOT_PROMOTABLE"
            ),
            "formal_design_evidence": False,
            "audit_sha256": audit.get("audit_sha256"),
            "power_balance_sha256": audit.get("power_balance_sha256"),
            "aspen_source_binding": _json_safe(source_binding),
            "aspen_source_binding_sha256": _sha256_json(source_binding),
            "program_generated": True,
        }

    relative_error_fields = {
        "fluid_to_shaft_balance_relative_error": (
            "shaft_power_relative_error"
        ),
        "shaft_to_electrical_balance_relative_error": (
            "electrical_power_relative_error"
        ),
    }
    if source_field in relative_error_fields:
        value = power_audit.get(relative_error_fields[source_field])
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return {
                "value": value,
                "unit": "-",
                "state": "DERIVED_FROM_PUMP_PROCESS_AUDIT",
                "source": source(power_audit),
            }
        return {
            "value": None,
            "unit": "-",
            "state": EXPLICIT_OPEN_GATE_STATE,
            "source": {
                **source(power_audit, evidence_class="U"),
                "reason_code": "PUMP_POWER_BALANCE_CHANNEL_INCOMPLETE",
                "reason": "The required Aspen pump power channel is absent, so this balance cannot be calculated.",
                "required_action": "Extract the missing pump power/efficiency channel and rerun both power balances.",
            },
        }
    status_to_error = {
        "fluid_to_shaft_balance_status": "shaft_power_relative_error",
        "shaft_to_electrical_balance_status": "electrical_power_relative_error",
    }
    if source_field in status_to_error:
        error = power_audit.get(status_to_error[source_field])
        tolerance = power_audit.get("balance_relative_error_tolerance")
        status = (
            "OPEN_INCOMPLETE_POWER_BALANCE"
            if not isinstance(error, (int, float)) or isinstance(error, bool)
            else "PASS"
            if isinstance(tolerance, (int, float))
            and float(error) <= float(tolerance)
            else "FAIL"
        )
        return {
            "value": status,
            "unit": None,
            "state": "PUMP_PROCESS_AUDIT_STATUS",
            "source": source(power_audit),
        }
    if source_field == "pump_power_process_audit_ref" and power_audit:
        return {
            "value": {
                key: power_audit.get(key)
                for key in (
                    "schema",
                    "status",
                    "audit_sha256",
                    "power_balance_sha256",
                    "required_balance_count",
                    "calculated_balance_count",
                    "both_balances_complete",
                )
            },
            "unit": None,
            "state": "HASH_BOUND_AUDIT_REFERENCE",
            "source": source(power_audit),
        }
    if source_field == "pump_npsha_process_audit_ref" and npsha_audit:
        return {
            "value": {
                key: npsha_audit.get(key)
                for key in (
                    "schema",
                    "status",
                    "audit_sha256",
                    "formal_cavitation_design_complete",
                    "open_gates",
                )
            },
            "unit": None,
            "state": "HASH_BOUND_AUDIT_REFERENCE",
            "source": source(npsha_audit),
        }
    if source_field == "npsha_raw_unit_semantics":
        lineage = context.get("aspen_parameter_lineage", {}).get(
            "npsha_pressure_kpa"
        )
        if isinstance(lineage, Mapping):
            keys = (
                "hash_bound_export_raw_unit",
                "hash_bound_export_raw_value",
                "legacy_export_unit_reinterpreted_as_kpa",
                "reinterpretation_basis",
                "source_path",
                "source_file_sha256",
                "production_action",
                "warning",
            )
            return {
                "value": {key: lineage.get(key) for key in keys},
                "unit": None,
                "state": "HASH_BOUND_RAW_UNIT_SEMANTICS",
                "source": {
                    **source(npsha_audit),
                    "aspen_parameter_lineage": _json_safe(lineage),
                    "aspen_parameter_lineage_sha256": _sha256_json(lineage),
                },
            }
    if source_field == "pump_candidate_reference_speed_rpm":
        leading = context.get("model", {}).get("leading_candidate")
        speed = (
            leading.get("speed_rpm")
            if isinstance(leading, Mapping)
            else None
        )
        if isinstance(speed, (int, float)) and not isinstance(speed, bool):
            candidate_source = (
                dict(leading.get("source"))
                if isinstance(leading.get("source"), Mapping)
                else {}
            )
            return {
                "value": speed,
                "unit": "r/min",
                "state": "STANDARD_CANDIDATE_REFERENCE_VALUE",
                "source": {
                    **candidate_source,
                    "kind": "bundled_standard_reference_catalog",
                    "evidence_class": "J",
                    "promotion_cap": "TYPE_SCREENING",
                    "formal_design_evidence": False,
                    "semantic_boundary": (
                        "Reference speed of the GB/T 5662 screening candidate; "
                        "not the Aspen actual shaft speed."
                    ),
                    "program_generated": True,
                },
            }
    if source_field in {
        "driver_efficiency_percent",
        "aspen_actual_shaft_speed_rpm",
    }:
        return {
            "value": None,
            "unit": "%" if source_field == "driver_efficiency_percent" else "r/min",
            "state": EXPLICIT_OPEN_GATE_STATE,
            "source": {
                **source(power_audit, evidence_class="U"),
                "reason_code": f"PUMP_FIELD_NOT_EXTRACTED:{source_field}",
                "reason": (
                    "The current hash-bound Aspen chain does not contain "
                    "this pump quantity."
                    if source_field == "driver_efficiency_percent"
                    else (
                        "The hash-bound history contains only a configured "
                        "ACT-SH-SPEED input/design-spec candidate, not an "
                        "independently reported final solved shaft speed."
                    )
                ),
                "required_action": (
                    "Extract this exact Aspen quantity and rerun the "
                    "deterministic customer projection."
                    if source_field == "driver_efficiency_percent"
                    else (
                        "Extract a final solved shaft-speed result from an "
                        "authoritative Aspen result node or report and bind "
                        "its unit and source hash."
                    )
                ),
            },
        }
    return None


def _source_cell(source_field: str, context: Mapping[str, Any]) -> dict[str, Any] | None:
    """Return one present matcher field without changing its meaning."""

    lineage = _parameter_lineage_for_customer_field(source_field, context)
    source_binding = (
        dict(context.get("aspen_source_binding"))
        if isinstance(context.get("aspen_source_binding"), Mapping)
        else {}
    )

    def source_with_lineage(source: Any) -> dict[str, Any]:
        answer = dict(source) if isinstance(source, Mapping) else {}
        if isinstance(lineage, Mapping):
            lineage_target_field = str(
                lineage.get("target_field") or source_field
            )
            upstream_evidence_class = answer.get("evidence_class")
            upstream_promotion_cap = answer.get("promotion_cap")
            upstream_kind = answer.get("kind")
            if upstream_evidence_class not in (None, ""):
                answer["upstream_evidence_class"] = (
                    upstream_evidence_class
                )
            if upstream_promotion_cap not in (None, ""):
                answer["upstream_promotion_cap"] = (
                    upstream_promotion_cap
                )
            if (
                upstream_kind not in (None, "")
                and _aspen_process_lineage(lineage)
            ):
                answer["upstream_kind"] = upstream_kind
            answer["evidence_class"] = str(
                lineage.get("evidence_class") or "U"
            )
            answer["promotion_cap"] = lineage.get("promotion_cap")
            if _aspen_process_lineage(lineage):
                answer["kind"] = "aspen_parameter_lineage_projection"
            answer["lineage_target_field"] = lineage_target_field
            answer["lineage_projection_kind"] = (
                "DIRECT_TARGET"
                if lineage_target_field == source_field
                else "REGISTERED_CANONICAL_ALIAS"
            )
            for key in (
                "source_path",
                "source_file_path",
                "source_file_sha256",
                "source_object_type",
                "source_object_id",
                "source_field",
                "origin",
                "evidence_scope",
                "result_status",
                "formal_design_evidence",
            ):
                if key in lineage and lineage.get(key) is not None:
                    answer[key] = _json_safe(lineage.get(key))
            answer.update({
                "aspen_parameter_lineage": _json_safe(lineage),
                "aspen_parameter_lineage_sha256": _sha256_json(lineage),
            })
        if source_binding:
            answer["aspen_source_binding"] = _json_safe(source_binding)
            answer["aspen_source_binding_sha256"] = _sha256_json(source_binding)
        if str(answer.get("kind") or "") == "provisional_screening_calculation":
            # Historical matcher rows did not always carry the promotion cap
            # even though their source kind and result status were explicitly
            # preliminary.  Repair the delivery metadata, not the numeric
            # value: the value remains useful for screening but can never
            # masquerade as formal design authority.
            answer.setdefault("evidence_class", "J")
            answer.setdefault("result_status", "PROVISIONAL")
            answer.setdefault("promotion_cap", "TYPE_SCREENING")
            answer.setdefault("formal_design_evidence", False)
        answer["program_generated"] = True
        return answer

    programmatic_cell = _programmatic_pipe_spec_cell(source_field, context)
    if programmatic_cell is not None:
        return programmatic_cell
    programmatic_cell = _programmatic_valve_spec_cell(
        source_field,
        context,
    )
    if programmatic_cell is not None:
        return programmatic_cell

    row = context["rows"].get(source_field)
    if row is not None and _present(row.get("raw_value")):
        return {
            "value": _json_safe(row.get("raw_value")),
            "unit": row.get("unit"),
            "state": (
                "DERIVED_FROM_ASPEN"
                if _aspen_process_lineage(lineage)
                else row.get("state", "PROVIDED")
            ),
            "source": _json_safe(source_with_lineage(row.get("source", {}))),
        }
    if source_field in context["values"] and _present(context["values"].get(source_field)):
        calculated = source_field in context["result"].get("derived_parameters", {})
        from_aspen = isinstance(lineage, Mapping) or (
            source_field in context.get("aspen_delivery_values", {})
            if isinstance(context.get("aspen_delivery_values"), Mapping)
            else False
        )
        state = (
            "CALCULATED"
            if calculated
            else "DERIVED_FROM_ASPEN"
            if from_aspen
            else "PROVIDED"
        )
        if (
            source_field
            == "aspen_configured_shaft_speed_candidate_rpm"
        ):
            state = (
                "ASPEN_CONFIGURED_INPUT_CANDIDATE_NOT_SOLVED_ACTUAL_SPEED"
            )
        return {
            "value": _json_safe(context["values"][source_field]),
            "unit": None,
            "state": state,
            "source": _json_safe(source_with_lineage({
                "kind": "deterministic_result_value",
                "evidence_class": (
                    str(lineage.get("evidence_class") or "D")
                    if isinstance(lineage, Mapping)
                    else "D" if calculated or from_aspen else "U"
                ),
                "promotion_cap": (
                    lineage.get("promotion_cap")
                    if isinstance(lineage, Mapping)
                    else None
                ),
            })),
        }
    if source_field in {"medium_name", "main_medium"}:
        medium_cell = _service_profile_medium_cell(context)
        if medium_cell is not None:
            return medium_cell
    pump_cell = _pump_audit_projection_cell(source_field, context)
    if pump_cell is not None:
        return pump_cell
    return None


def _field_summary(source_fields: Iterable[str], context: Mapping[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for source_field in sorted(set(str(item) for item in source_fields)):
        cell = _source_cell(source_field, context)
        if cell is not None:
            summary[source_field] = cell
    return summary


def _material_summary(context: Mapping[str, Any]) -> dict[str, Any]:
    candidates = {
        field_id
        for field_id in set([*context["values"], *context["rows"]])
        if field_id == "material" or field_id.endswith("_material") or field_id.endswith("_material_grade")
    }
    return _field_summary(candidates, context)


OPERATING_SUMMARY_FIELDS = {
    "main_medium", "medium", "medium_name", "phase", "gas_composition", "flow_m3_h", "mass_flow_kg_h",
    "gas_flow_m3_h", "liquid_flow_m3_h", "standard_flow_m3_h", "standard_flow_nm3_h",
    "standard_flow_basis", "temperature_c", "inlet_temperature_c", "outlet_temperature_c",
    "operating_pressure_mpa", "inlet_pressure_mpa", "outlet_pressure_mpa", "pressure_drop_kpa",
    "density_kg_m3", "viscosity_mpa_s", "dynamic_viscosity_mpa_s",
}


DESIGN_SUMMARY_FIELDS = {
    "design_temperature_c", "design_pressure_mpa", "pressure_class", "corrosion_allowance_mm",
    "allowable_pressure_drop_kpa", "fill_fraction", "retention_time_min", "allowable_stress_mpa",
    "weld_efficiency",
}


def _operating_summary_candidates(context: Mapping[str, Any]) -> set[str]:
    result = set(OPERATING_SUMMARY_FIELDS)
    for field_id in set([*context["values"], *context["rows"]]):
        lowered = field_id.casefold()
        if any(token in lowered for token in (
            "_operating_pressure", "_inlet_temperature", "_outlet_temperature",
            "_inlet_pressure", "_outlet_pressure",
        )):
            result.add(field_id)
    return result


def _design_summary_candidates(context: Mapping[str, Any]) -> set[str]:
    result = set(DESIGN_SUMMARY_FIELDS)
    for field_id in set([*context["values"], *context["rows"]]):
        lowered = field_id.casefold()
        if (
            lowered.startswith("design_")
            or "_design_temperature" in lowered
            or "_design_pressure" in lowered
            or "nominal_pressure" in lowered
            or "allowable_pressure_drop" in lowered
        ):
            result.add(field_id)
    return result


def _key_specification_summary(context: Mapping[str, Any]) -> dict[str, Any]:
    vector = context["package"].get("selection_feature_vector", {})
    values = vector.get("values", {}) if isinstance(vector, Mapping) else {}
    if not isinstance(values, Mapping):
        return {}
    result: dict[str, Any] = {}
    for field_id in sorted(values):
        if not _present(values[field_id]):
            continue
        source = _source_cell(str(field_id), context)
        if (
            "family_tower" in context.get("family_ids", [])
            and _tower_key_summary_field_is_internal_only(
                str(field_id),
                source,
            )
        ):
            continue
        result[str(field_id)] = source or {
            "value": _json_safe(values[field_id]),
            "unit": None,
            "state": "SELECTION_FEATURE",
            "source": {"kind": "selection_feature_vector"},
        }
    return result


def _summary_special_cell(field_id: str, field: Mapping[str, Any], context: Mapping[str, Any]) -> dict[str, Any] | None:
    """Project global customer columns from existing deterministic fields."""

    if field_id == "equipment_tag_or_line_number":
        for source_field in ("equipment_tag", "line_number"):
            source = _source_cell(source_field, context)
            if source is not None:
                return {
                    "field_id": field_id, "label": field.get("label"), "unit": None,
                    "value": source["value"], "state": source["state"], "source_field_id": source_field,
                    "source": source["source"], "equation_chain": None, "formula_chain": None,
                }
        return None
    if field_id == "equipment_family":
        family_ids = list(context["family_ids"])
        value: Any = family_ids[0] if len(family_ids) == 1 else family_ids
        return {
            "field_id": field_id, "label": field.get("label"), "unit": None,
            "value": value or None, "state": "MATCHED" if len(family_ids) == 1 else ("AMBIGUOUS_UNION" if family_ids else "MISSING"),
            "source_field_id": None, "source": {"kind": "deterministic_family_match"},
            "equation_chain": None, "formula_chain": None,
        }
    if field_id == "quantity_and_standby":
        summary = _field_summary(
            {
                "quantity", "count", "quantity_count", "operating_quantity", "standby_quantity",
                "standby_scheme", "standby_configuration", "operating_state", "operating_mode",
                "equipment_arrangement",
            },
            context,
        )
    elif field_id == "material_summary":
        summary = _material_summary(context)
    elif field_id == "operating_condition_summary":
        summary = _field_summary(_operating_summary_candidates(context), context)
    elif field_id == "design_condition_summary":
        summary = _field_summary(_design_summary_candidates(context), context)
    elif field_id == "key_specification_summary":
        summary = _key_specification_summary(context)
    else:
        return None
    return {
        "field_id": field_id, "label": field.get("label"), "unit": None,
        "value": summary or None, "state": "DERIVED_SUMMARY" if summary else "MISSING",
        "source_field_id": None,
        "source": {"kind": "deterministic_projection_of_existing_fields", "source_fields": sorted(summary)},
        "equation_chain": None, "formula_chain": None,
    }


def _standards(context: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    values = context["values"]
    explicit_identity = values.get("standard_identity")
    number = values.get("standard_designation") or values.get("standard_number") or values.get("standard_code")
    version = values.get("standard_version")
    adopted: list[dict[str, Any]] = []
    if _present(explicit_identity):
        identities = explicit_identity if isinstance(explicit_identity, list) else [explicit_identity]
        for identity in identities:
            if isinstance(identity, Mapping):
                adopted.append({**_json_safe(identity), "adoption_state": "EXPLICIT_MATCHER_VALUE"})
            else:
                adopted.append({"identity": _json_safe(identity), "adoption_state": "EXPLICIT_MATCHER_VALUE"})
    if _present(number) or _present(version):
        candidate = {
            "number_or_designation": number,
            "version": version,
            "status": values.get("standard_status"),
            "adoption_state": "EXPLICIT_MATCHER_VALUE",
        }
        if candidate not in adopted:
            adopted.append(candidate)
    pipe_specification = context.get("programmatic_pipe_specification", {})
    standard_selections = (
        pipe_specification.get("standard_selections", {})
        if isinstance(pipe_specification, Mapping)
        else {}
    )
    if isinstance(standard_selections, Mapping):
        for selection_kind in ("wall", "pn"):
            selection = standard_selections.get(selection_kind)
            if not isinstance(selection, Mapping):
                continue
            standard_id = selection.get("standard_id")
            standard_version = selection.get("standard_version")
            if not _present(standard_id):
                continue
            adopted.append({
                "number_or_designation": standard_id,
                "version": standard_version,
                "selection_kind": selection_kind,
                "dataset_id": selection.get("dataset_id"),
                "record_id": selection.get("record_id"),
                "record_sha256": selection.get("record_sha256"),
                "source_pdf_sha256": selection.get("source_pdf_sha256"),
                "physical_page": selection.get("physical_page"),
                "claim_boundary": selection.get("claim_boundary"),
                "adoption_state": "PROGRAMMATIC_VERIFIED_STANDARD_RECORD_SELECTED",
                "program_specification_sha256": (
                    pipe_specification.get("program_specification_sha256")
                    if isinstance(pipe_specification, Mapping)
                    else None
                ),
            })
    adopted = sorted(
        {
            _canonical_json(item): item
            for item in adopted
        }.values(),
        key=lambda item: (
            str(item.get("number_or_designation") or item.get("identity") or ""),
            str(item.get("selection_kind") or ""),
        ),
    )
    routes: list[dict[str, Any]] = []
    for item in context["result"].get("standard_routes", []) if isinstance(context["result"].get("standard_routes"), list) else []:
        if not isinstance(item, Mapping) or item.get("reuse_class") == "forbidden_transfer":
            continue
        routes.append({
            "number": item.get("number"),
            "title": item.get("title"),
            "standard_status": item.get("standard_status"),
            "authority": item.get("authority"),
            "reuse_class": item.get("reuse_class"),
            "node_id": item.get("node_id"),
            "adoption_state": "REFERENCE_ROUTE_NOT_AUTOMATICALLY_ADOPTED",
        })
    routes.sort(key=lambda item: (str(item.get("number") or ""), str(item.get("node_id") or "")))
    return adopted, routes


def _record_id(payload: Mapping[str, Any]) -> str:
    return f"REC-{_sha256_json(payload)[:20]}"


def _evidence_id(payload: Mapping[str, Any]) -> str:
    return f"EVID-{_sha256_json(payload)[:20]}"


def _evidence_records(context: Mapping[str, Any]) -> list[dict[str, Any]]:
    values = context["values"]
    rows = context["rows"]
    path_bases = {field[:-5] for field in set([*values, *rows]) if field.endswith("_path")}
    hash_bases = {field[:-7] for field in set([*values, *rows]) if field.endswith("_sha256")}
    bases = sorted(path_bases | hash_bases)
    records: list[dict[str, Any]] = []
    service_profile = context.get("service_profile", {})
    if isinstance(service_profile, Mapping) and _present(service_profile.get("profile_context_sha256")):
        payload = {
            "equipment_key": context["equipment_key"],
            "evidence_kind": "automatic_service_profile",
            "sha256": str(service_profile.get("profile_context_sha256")).upper(),
            "status": "DETERMINISTIC_DERIVED_CONTEXT",
        }
        records.append({
            **payload,
            "record_id": _record_id(payload),
            "evidence_id": _evidence_id(payload),
            "verification_scope": "MODULE/STREAM/PFD-DERIVED SERVICE CONTEXT; PROPERTY FACTS REMAIN SEPARATELY HASH-BOUND",
        })
    pipe_specification = context.get("programmatic_pipe_specification", {})
    if (
        isinstance(pipe_specification, Mapping)
        and pipe_specification.get("status")
        == "PRELIMINARY_CONCRETE_SPECIFICATION_SELECTED"
        and _present(pipe_specification.get("program_specification_sha256"))
    ):
        standard_selections = (
            pipe_specification.get("standard_selections", {})
            if isinstance(pipe_specification.get("standard_selections"), Mapping)
            else {}
        )
        payload = {
            "equipment_key": context["equipment_key"],
            "evidence_kind": "programmatic_pipe_specification",
            "sha256": str(
                pipe_specification.get("program_specification_sha256")
            ).upper(),
            "status": pipe_specification.get("status"),
            "aspen_export_sha256": (
                pipe_specification.get("source_binding", {}).get(
                    "aspen_export_sha256"
                )
                if isinstance(pipe_specification.get("source_binding"), Mapping)
                else None
            ),
            "standard_record_bindings": [
                {
                    "selection_kind": kind,
                    "standard_id": selection.get("standard_id"),
                    "record_id": selection.get("record_id"),
                    "record_sha256": selection.get("record_sha256"),
                    "source_pdf_sha256": selection.get("source_pdf_sha256"),
                }
                for kind, selection in sorted(standard_selections.items())
                if kind in {"pn", "wall"} and isinstance(selection, Mapping)
            ],
        }
        records.append({
            **payload,
            "record_id": _record_id(payload),
            "evidence_id": _evidence_id(payload),
            "verification_scope": (
                "HASH-VERIFIED PROGRAM-GENERATED PRELIMINARY PIPE DESIGNATION; "
                "FORMAL MATERIAL/P-T/STRESS/SUPPORT/TEST GATES REMAIN OPEN"
            ),
        })
    connection_package = context.get("connection_component_selections", {})
    if isinstance(connection_package, Mapping) and _present(connection_package.get("selection_package_sha256")):
        payload = {
            "equipment_key": context["equipment_key"],
            "evidence_kind": "connection_component_selection_package",
            "sha256": str(connection_package.get("selection_package_sha256")).upper(),
            "status": str(connection_package.get("status") or "UNKNOWN"),
        }
        records.append({
            **payload,
            "record_id": _record_id(payload),
            "evidence_id": _evidence_id(payload),
            "verification_scope": "CONNECTION-SCOPED DETERMINISTIC COMPONENT SELECTION; NOT VENDOR FINAL EVIDENCE",
        })
        for connection in connection_package.get("connections", []) if isinstance(connection_package.get("connections"), list) else []:
            if not isinstance(connection, Mapping) or connection.get("applicability") != "APPLICABLE":
                continue
            component_types = connection.get("component_types")
            if not isinstance(component_types, Mapping):
                continue
            for component_family, selected in sorted(component_types.items()):
                terminal = selected.get("terminal_type") if isinstance(selected, Mapping) else None
                if not isinstance(terminal, Mapping) or not _present(terminal.get("candidate_id")):
                    continue
                component_payload = {
                    "equipment_key": context["equipment_key"],
                    "evidence_kind": "deterministic_connection_component_selection",
                    "connection_id": connection.get("connection_id"),
                    "component_family": component_family,
                    "candidate_id": terminal.get("candidate_id"),
                    "code": terminal.get("code"),
                    "name_zh": terminal.get("name_zh"),
                    "status": selected.get("status"),
                    "selection_package_sha256": str(connection_package.get("selection_package_sha256")).upper(),
                }
                records.append({
                    **component_payload,
                    "record_id": _record_id(component_payload),
                    "evidence_id": _evidence_id(component_payload),
                    "warnings": _json_safe(selected.get("warnings", [])),
                    "source_refs": _json_safe(selected.get("source_refs", [])),
                    "verification_scope": "DETERMINISTIC CONNECTION COMPONENT TYPE; PROVISIONAL UNTIL MATERIAL/P-T/PROJECT GATES CLOSE",
                })
    for estimate in context.get("model_estimate_inputs", []):
        if not isinstance(estimate, Mapping):
            continue
        field_id = str(estimate.get("field_id") or "")
        payload = {
            "equipment_key": context["equipment_key"],
            "evidence_kind": "llm_last_resort_engineering_estimate",
            "field_id": field_id,
            "value": _json_safe(estimate.get("value")),
            "status": str(estimate.get("state") or "PROVISIONAL"),
        }
        records.append({
            **payload,
            "record_id": _record_id(payload),
            "evidence_id": _evidence_id(payload),
            "source_fields": [field_id],
            "verification_scope": (
                "J/PROVISIONAL MODEL ESTIMATE; TYPE_SCREENING ONLY; "
                "REPLACE WITH SAME-CASE EVIDENCE AND REPLAY BEFORE FORMAL PROMOTION"
            ),
            "promotion_cap": estimate.get("promotion_cap") or "TYPE_SCREENING",
            "superseded_by": estimate.get("superseded_by"),
        })
    for base in bases:
        path_field = f"{base}_path"
        hash_field = f"{base}_sha256"
        path_value = values.get(path_field)
        hash_value = values.get(hash_field)
        required = path_field in rows or hash_field in rows
        if not _present(path_value) and not _present(hash_value) and not required:
            continue
        if _present(path_value) and _present(hash_value):
            status = "DECLARED_PATH_HASH_PAIR"
        elif _present(path_value) or _present(hash_value):
            status = "INCOMPLETE_PATH_HASH_PAIR"
        else:
            status = "MISSING_REQUIRED_EVIDENCE"
        payload = {
            "equipment_key": context["equipment_key"],
            "evidence_kind": base,
            "path": path_value,
            "sha256": str(hash_value).upper() if _present(hash_value) else None,
            "status": status,
        }
        record = {
            **payload,
            "record_id": _record_id(payload),
            "evidence_id": _evidence_id(payload) if status == "DECLARED_PATH_HASH_PAIR" else None,
            "source_fields": [path_field, hash_field],
            "verification_scope": "DECLARATION_FROM_DETERMINISTIC_MATCHER; FILE_NOT_REHASHED_BY_EXPORT_ADAPTER",
        }
        if _present(hash_value) and not _HASH_RE.fullmatch(str(hash_value)):
            record["status"] = "INVALID_DECLARED_SHA256"
            record["evidence_id"] = None
        records.append(record)
    reference_fields = sorted({
        field_id
        for field_id in set([*values, *rows])
        if field_id.endswith(("_ref", "_reference"))
    })
    for field_id in reference_fields:
        reference = values.get(field_id)
        if not _present(reference):
            row = rows.get(field_id, {})
            reference = row.get("raw_value") if isinstance(row, Mapping) else None
        if not _present(reference):
            continue
        payload = {
            "equipment_key": context["equipment_key"],
            "evidence_kind": field_id,
            "declared_reference": _json_safe(reference),
        }
        records.append({
            **payload,
            "record_id": _record_id(payload),
            "evidence_id": _evidence_id(payload),
            "status": "DECLARED_EVIDENCE_REFERENCE",
            "verification_scope": "REFERENCE_PRESERVED; CONTENT_NOT_REVERIFIED_BY_EXPORT_ADAPTER",
        })
    result = context["result"]
    for route in result.get("standard_routes", []) if isinstance(result.get("standard_routes"), list) else []:
        if not isinstance(route, Mapping) or route.get("reuse_class") == "forbidden_transfer":
            continue
        source_layer = route.get("source_layer", {}) if isinstance(route.get("source_layer"), Mapping) else {}
        payload = {
            "equipment_key": context["equipment_key"],
            "evidence_kind": "standard_reference_route",
            "node_id": route.get("node_id"),
            "number": route.get("number"),
            "authority": route.get("authority"),
            "reuse_class": route.get("reuse_class"),
            "source_pdf_sha256": source_layer.get("source_pdf_sha256"),
        }
        records.append({
            **payload,
            "record_id": _record_id(payload),
            "evidence_id": _evidence_id(payload),
            "status": "REFERENCE_ROUTE_ONLY",
            "verification_scope": "DOES_NOT_BY_ITSELF_PROVE_SAME_EQUIPMENT_SELECTION",
        })
    model = context["model"]
    basis = model.get("knowledge_basis", {}) if isinstance(model.get("knowledge_basis"), Mapping) else {}
    method_pairs = [
        ("model_rule", basis.get("model_rule_path"), basis.get("model_rule_sha256")),
    ]
    catalog = model.get("pump_standard_lookup", {}).get("catalog", {}) if isinstance(model.get("pump_standard_lookup"), Mapping) else {}
    if isinstance(catalog, Mapping):
        method_pairs.append(("candidate_catalog", catalog.get("path"), catalog.get("sha256")))
    for kind, path_value, hash_value in method_pairs:
        if not _present(path_value) and not _present(hash_value):
            continue
        payload = {
            "equipment_key": context["equipment_key"], "evidence_kind": kind,
            "path": path_value, "sha256": str(hash_value).upper() if _present(hash_value) else None,
        }
        records.append({
            **payload,
            "record_id": _record_id(payload),
            "evidence_id": _evidence_id(payload),
            "status": "DETERMINISTIC_METHOD_AUTHORITY",
            "verification_scope": "METHOD_OR_CANDIDATE_GENERATION_ONLY",
        })
    lineage_payload = {
        "equipment_key": context["equipment_key"],
        "evidence_kind": "normalized_input_digest",
        "sha256": context["input_sha256"],
    }
    records.append({
        **lineage_payload,
        "record_id": _record_id(lineage_payload),
        "evidence_id": _evidence_id(lineage_payload),
        "status": "LINEAGE_DIGEST_NOT_SOURCE_PROVENANCE",
        "verification_scope": "NORMALIZED_MATCHER_INPUT_ONLY",
    })
    unique = {record["record_id"]: record for record in records}
    return sorted(unique.values(), key=lambda item: (
        str(item.get("evidence_kind") or ""), str(item.get("path") or ""),
        str(item.get("number") or ""), str(item.get("record_id") or ""),
    ))


def _evidence_level(context: Mapping[str, Any], evidence_records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    status = _model_status(context)
    if status == "final_model":
        return {"value": "A4", "scope": "FINAL_MODEL", "basis": ["model_status:final_model"]}
    if status == "same_equipment_verified":
        return {"value": "A3", "scope": "SAME_EQUIPMENT_VERIFIED", "basis": ["model_status:same_equipment_verified"]}
    route_levels = [
        str(record.get("authority"))
        for record in evidence_records
        if record.get("evidence_kind") == "standard_reference_route"
        and str(record.get("authority")) in {"A0", "A1", "A2"}
    ]
    if route_levels:
        level = max(route_levels, key=lambda item: int(item[1]))
        return {
            "value": level,
            "scope": "STANDARD_REFERENCE_OR_CANDIDATE_ROUTE_ONLY",
            "basis": sorted(set(f"standard_route:{item}" for item in route_levels)),
        }
    return {
        "value": "UNASSESSED",
        "scope": "NO_A0_A4_LEVEL_ESTABLISHED_BY_MATCHER_OUTPUT",
        "basis": [],
    }


CONNECTION_COMPONENT_FIELD_MAP = {
    "flange_type": ("flange_type", "name_and_code"),
    "flange_face": ("facing", "code"),
    "gasket_type": ("gasket_type", "name_and_code"),
    "gasket_type_code": ("gasket_type", "code"),
    "fastener_type": ("fastener_type", "name_and_code"),
    "fastener_specification": ("fastener_type", "name_and_code"),
}


def _connection_component_cell(
    field: Mapping[str, Any],
    context: Mapping[str, Any],
) -> dict[str, Any] | None:
    mapping = CONNECTION_COMPONENT_FIELD_MAP.get(str(field.get("field_id") or ""))
    component_family, display_mode = mapping if mapping else (None, None)
    package = context.get("connection_component_selections")
    if not component_family or not isinstance(package, Mapping):
        return None
    selections: list[dict[str, Any]] = []
    for connection in package.get("connections", []) if isinstance(package.get("connections"), list) else []:
        if not isinstance(connection, Mapping) or connection.get("applicability") != "APPLICABLE":
            continue
        component_types = connection.get("component_types")
        selected = component_types.get(component_family) if isinstance(component_types, Mapping) else None
        terminal = selected.get("terminal_type") if isinstance(selected, Mapping) else None
        if not isinstance(terminal, Mapping) or not _present(terminal.get("candidate_id")):
            continue
        display_value = terminal.get("code")
        if display_mode == "name_and_code":
            display_value = terminal.get("name_zh") or terminal.get("code")
            if _present(terminal.get("code")) and terminal.get("code") != display_value:
                display_value = f"{display_value} ({terminal.get('code')})"
        selections.append({
            "connection_id": connection.get("connection_id"),
            "value": display_value,
            "candidate_id": terminal.get("candidate_id"),
            "code": terminal.get("code"),
            "name_zh": terminal.get("name_zh"),
            "status": selected.get("status"),
            "warnings": _json_safe(selected.get("warnings", [])),
            "source_refs": _json_safe(selected.get("source_refs", [])),
            "minimum_missing_fields": _json_safe(selected.get("minimum_missing_fields", [])),
        })
    if not selections:
        return None
    distinct = {_token(item.get("value")) for item in selections}
    if len(distinct) == 1:
        value: Any = selections[0]["value"]
        state = str(selections[0].get("status") or "DETERMINISTIC_CONNECTION_SELECTION")
    else:
        value = selections
        state = "MULTIPLE_CONNECTION_SELECTIONS"
    provisional = any("PROVISIONAL" in str(item.get("status") or "") for item in selections)
    return {
        "field_id": field["field_id"],
        "label": field.get("label"),
        "unit": field.get("unit"),
        "value": _json_safe(value),
        "state": state,
        "source_field_id": f"connection_component_selections.{component_family}",
        "source": {
            "kind": "deterministic_connection_selector",
            "evidence_class": "J" if provisional else "D",
            "provisional": provisional,
            "promotion_cap": "TYPE_SCREENING" if provisional else None,
            "selection_package_sha256": package.get("selection_package_sha256"),
            "component_family": component_family,
            "selections": selections,
        },
        "equation_chain": None,
        "formula_chain": None,
    }


RAW_CUSTOMER_GAP_STATES = {
    "MISSING",
    "EXTERNAL_REQUIRED",
    "NOT_EXPLICITLY_ADOPTED",
}
EXPLICIT_OPEN_GATE_STATE = "OPEN_FORMAL_EVIDENCE_GATE"


TOWER_INTERNAL_SCREENING_FIELD_IDS = {
    "tower_diameter_screening_mm",
    "tower_height_screening_mm",
    "tower_internal_height_m",
    "formula_only_shell_thickness_mm",
    "formula_only_head_thickness_mm",
    "nominal_shell_wall_thickness_selected",
    "nominal_head_wall_thickness_selected",
    "inner_diameter_mm",
}
TOWER_FORMAL_GEOMETRY_FIELD_IDS = {
    "diameter_mm",
    "height_mm",
    "tower_total_height_m",
    "nominal_shell_wall_thickness_mm",
    "nominal_head_wall_thickness_mm",
}


def _tower_cell_has_formal_geometry_authority(
    cell: Mapping[str, Any] | None,
) -> bool:
    if not isinstance(cell, Mapping):
        return False
    source = cell.get("source") if isinstance(cell.get("source"), Mapping) else {}
    promotion_cap = str(
        source.get("promotion_cap") or cell.get("promotion_cap") or ""
    ).upper()
    return (
        source.get("formal_design_evidence") is True
        and promotion_cap not in {"TYPE_SCREENING", "NOT_PROMOTABLE"}
        and str(cell.get("state") or "") != EXPLICIT_OPEN_GATE_STATE
    )


def _tower_key_summary_field_is_internal_only(
    field_id: str,
    cell: Mapping[str, Any] | None,
) -> bool:
    if field_id in TOWER_INTERNAL_SCREENING_FIELD_IDS:
        return True
    return (
        field_id in TOWER_FORMAL_GEOMETRY_FIELD_IDS
        and not _tower_cell_has_formal_geometry_authority(cell)
    )


def _screening_only_delivery_cell(cell: Mapping[str, Any]) -> bool:
    """Return whether a value is explicitly capped below formal design use."""

    source = (
        cell.get("source")
        if isinstance(cell.get("source"), Mapping)
        else {}
    )
    state = str(cell.get("state") or "").strip().upper()
    source_kind = str(source.get("kind") or "").strip()
    promotion_cap = str(
        source.get("promotion_cap")
        or cell.get("promotion_cap")
        or ""
    ).strip().upper()
    result_status = str(source.get("result_status") or "").strip().upper()
    return (
        state.startswith("DEFAULTED")
        or state.startswith("RECOMMENDED")
        or state in {
            "PROVISIONAL",
            "PROVISIONAL_SCREENING_VALUE",
            "PRELIMINARY_TYPE_SPECIFICATION",
        }
        or source_kind in {
            "provisional_screening_calculation",
            "registered_final_fallback_default",
        }
        or promotion_cap in {"TYPE_SCREENING", "NOT_PROMOTABLE"}
        or result_status == "PROVISIONAL"
    )


def _tower_formal_geometry_alias_is_screening_only(
    target_field: str,
    source_field: str,
    cell: Mapping[str, Any],
    context: Mapping[str, Any],
) -> bool:
    """Keep tower screening geometry out of formal diameter/height columns.

    Older matcher payloads exposed ``inner_diameter_mm=600`` as a registered
    minimum and ``height_mm`` as a layout screen.  Those values remain
    deliverable through the explicitly named ``tower_*_screening`` fields, but
    they are not allowed to populate the authority table's formal tower
    diameter or total-height cells.
    """

    if "family_tower" not in context.get("family_ids", []):
        return False
    protected_aliases = {
        "diameter_mm": {"diameter_mm", "inner_diameter_mm"},
        "height_mm": {"height_mm"},
        "tower_total_height_m": {
            "height_mm",
            "tower_total_height_m",
        },
    }
    if source_field not in protected_aliases.get(target_field, set()):
        return False
    return (
        _screening_only_delivery_cell(cell)
        or not _tower_cell_has_formal_geometry_authority(cell)
    )


def _explicit_open_gate_cell(
    field: Mapping[str, Any],
    original: Mapping[str, Any],
) -> dict[str, Any]:
    """Represent a true unknown as a visible, non-numeric OPEN cell.

    ``value`` intentionally stays ``None`` so a consumer cannot parse the
    placeholder as an engineering value.  ``display_value`` makes the gap
    visible in the customer table, while the source metadata records why it is
    open and forbids promotion to formal use.
    """

    cell = copy.deepcopy(dict(original))
    field_id = str(field.get("field_id") or cell.get("field_id") or "")
    label = str(field.get("label") or cell.get("label") or field_id)
    original_state = str(cell.get("state") or "MISSING")
    original_source = (
        dict(cell.get("source"))
        if isinstance(cell.get("source"), Mapping)
        else {}
    )
    reason_code = str(
        original_source.get("reason_code")
        or (
            "FORMAL_GEOMETRY_NOT_AVAILABLE_SCREENING_ALIAS_REJECTED"
            if original_source.get("rejected_screening_aliases")
            else "REQUIRED_CUSTOMER_FIELD_NOT_AVAILABLE"
        )
    )
    reason = str(
        original_source.get("reason")
        or (
            "Only a screening/default geometry value was available; it was "
            "not copied into the formal tower geometry field."
            if original_source.get("rejected_screening_aliases")
            else "No deterministic value with adequate field authority is "
            "available in the current input and evidence chain."
        )
    )
    required_action = str(
        original_source.get("required_action")
        or f"Provide and verify {field_id} from the applicable project, "
        "calculation, vendor, or formal design evidence."
    )
    source = {
        **original_source,
        "kind": "registered_formal_evidence_gate",
        "upstream_kind": original_source.get("kind"),
        "evidence_class": "U",
        "reason_code": reason_code,
        "reason": reason,
        "required_action": required_action,
        "promotion_cap": "NOT_PROMOTABLE",
        "formal_design_evidence": False,
        "original_state": original_state,
        "placeholder_is_engineering_value": False,
    }
    # A raw gap token or empty structured placeholder is not an engineering
    # value.  Keep all explanatory detail in ``open_gate``/``source`` and make
    # the machine value unambiguously absent.
    cell["value"] = None
    cell.update({
        "field_id": field_id,
        "label": field.get("label") or cell.get("label"),
        "unit": field.get("unit") or cell.get("unit"),
        "display_value": f"OPEN / 待补：{label}",
        "state": EXPLICIT_OPEN_GATE_STATE,
        "promotion_cap": "NOT_PROMOTABLE",
        "open_gate": {
            "reason_code": reason_code,
            "reason": reason,
            "required_action": required_action,
            "promotion_cap": "NOT_PROMOTABLE",
        },
        "source": source,
    })
    return cell


def _ensure_open_gate_metadata(
    field: Mapping[str, Any],
    original: Mapping[str, Any],
) -> dict[str, Any]:
    """Make an existing OPEN gate self-explanatory without changing its kind."""

    cell = copy.deepcopy(dict(original))
    if str(cell.get("state") or "") != EXPLICIT_OPEN_GATE_STATE:
        return cell
    field_id = str(field.get("field_id") or cell.get("field_id") or "")
    label = str(field.get("label") or cell.get("label") or field_id)
    source = (
        dict(cell.get("source"))
        if isinstance(cell.get("source"), Mapping)
        else {}
    )
    reason_code = str(
        source.get("reason_code")
        or f"FORMAL_EVIDENCE_GATE_OPEN:{field_id}"
    )
    reason = str(
        source.get("reason")
        or source.get("warning")
        or "The current deterministic chain explicitly leaves this formal "
        "field open."
    )
    required_action = str(
        source.get("required_action")
        or f"Close the formal evidence gate for {field_id} and rerun the "
        "deterministic selector."
    )
    upstream_evidence_class = source.get("evidence_class")
    upstream_promotion_cap = (
        source.get("promotion_cap") or cell.get("promotion_cap")
    )
    promotion_cap = "NOT_PROMOTABLE"
    source.update({
        "evidence_class": "U",
        "reason_code": reason_code,
        "reason": reason,
        "required_action": required_action,
        "promotion_cap": promotion_cap,
        "formal_design_evidence": False,
        "placeholder_is_engineering_value": False,
    })
    if upstream_evidence_class not in (None, "", "U"):
        source["upstream_evidence_class"] = upstream_evidence_class
    if upstream_promotion_cap not in (None, "", "NOT_PROMOTABLE"):
        source["upstream_promotion_cap"] = upstream_promotion_cap
    cell.update({
        "value": None,
        "display_value": (
            cell.get("display_value")
            or f"OPEN / 待补：{label}"
        ),
        "promotion_cap": promotion_cap,
        "open_gate": {
            "reason_code": reason_code,
            "reason": reason,
            "required_action": required_action,
            "promotion_cap": promotion_cap,
        },
        "source": source,
    })
    return cell


def _normal_cell(field: Mapping[str, Any], context: Mapping[str, Any]) -> dict[str, Any]:
    component_cell = _connection_component_cell(field, context)
    if component_cell is not None:
        return component_cell
    rows = context["rows"]
    values = context["values"]
    rejected_screening_aliases: list[dict[str, Any]] = []
    for source_field in field.get("source_fields", [field["field_id"]]):
        programmatic_cell = _programmatic_pipe_spec_cell(
            str(source_field),
            context,
        )
        if programmatic_cell is not None:
            return {
                "field_id": field["field_id"],
                "label": field.get("label"),
                "unit": field.get("unit") or programmatic_cell.get("unit"),
                "value": _json_safe(programmatic_cell.get("value")),
                "state": programmatic_cell.get(
                    "state", "PROGRAM_PRELIMINARY_SELECTED"
                ),
                "source_field_id": source_field,
                "source": _json_safe(programmatic_cell.get("source", {})),
                "equation_chain": None,
                "formula_chain": None,
            }
        bound_cell = _source_cell(str(source_field), context)
        if bound_cell is not None:
            if _tower_formal_geometry_alias_is_screening_only(
                str(field.get("field_id") or ""),
                str(source_field),
                bound_cell,
                context,
            ):
                rejected_screening_aliases.append({
                    "source_field_id": str(source_field),
                    "state": bound_cell.get("state"),
                    "source_kind": (
                        bound_cell.get("source", {}).get("kind")
                        if isinstance(bound_cell.get("source"), Mapping)
                        else None
                    ),
                    "promotion_cap": (
                        bound_cell.get("source", {}).get("promotion_cap")
                        if isinstance(bound_cell.get("source"), Mapping)
                        else bound_cell.get("promotion_cap")
                    ),
                })
                continue
            raw_value = bound_cell.get("value")
            if _explicit_not_applicable(field, raw_value):
                return _not_applicable_cell(
                    field,
                    source_field=str(source_field),
                    raw_token=str(raw_value),
                    source=bound_cell.get("source", {}),
                )
            bound_row = rows.get(source_field)
            return {
                "field_id": field["field_id"],
                "label": field.get("label"),
                "unit": field.get("unit") or bound_cell.get("unit"),
                "value": _json_safe(raw_value),
                "state": bound_cell.get("state", "PROVIDED"),
                "source_field_id": source_field,
                "source": _json_safe(bound_cell.get("source", {})),
                "equation_chain": (
                    bound_row.get("equation_chain")
                    if isinstance(bound_row, Mapping)
                    else None
                ),
                "formula_chain": (
                    _json_safe(bound_row.get("formula_chain"))
                    if isinstance(bound_row, Mapping)
                    else None
                ),
            }
        row = rows.get(source_field)
        if row is not None and _present(row.get("raw_value")):
            raw_value = row.get("raw_value")
            if _explicit_not_applicable(field, raw_value):
                return _not_applicable_cell(
                    field,
                    source_field=source_field,
                    raw_token=str(raw_value),
                    source=row.get("source", {}),
                )
            return {
                "field_id": field["field_id"], "label": field.get("label"),
                "unit": field.get("unit") or row.get("unit"), "value": _json_safe(raw_value),
                "state": row.get("state", "PROVIDED"), "source_field_id": source_field,
                "source": _json_safe(row.get("source", {})),
                "equation_chain": row.get("equation_chain"), "formula_chain": _json_safe(row.get("formula_chain")),
            }
        if source_field in values and _present(values.get(source_field)):
            raw_value = values[source_field]
            if _explicit_not_applicable(field, raw_value):
                return _not_applicable_cell(
                    field,
                    source_field=source_field,
                    raw_token=str(raw_value),
                    source={"kind": "deterministic_result_value"},
                )
            state = "CALCULATED" if source_field in context["result"].get("derived_parameters", {}) else "PROVIDED"
            return {
                "field_id": field["field_id"], "label": field.get("label"), "unit": field.get("unit"),
                "value": _json_safe(raw_value), "state": state, "source_field_id": source_field,
                "source": {"kind": "deterministic_result_value", "evidence_class": "D" if state == "CALCULATED" else "U"},
                "equation_chain": None, "formula_chain": None,
            }
    source: dict[str, Any] = {
        "kind": "not_available",
        "evidence_class": "U",
    }
    if rejected_screening_aliases:
        source.update({
            "reason_code": (
                "FORMAL_GEOMETRY_NOT_AVAILABLE_SCREENING_ALIAS_REJECTED"
            ),
            "reason": (
                "A screening/default tower geometry value exists, but the "
                "formal authority field requires independently established "
                "design geometry."
            ),
            "required_action": (
                "Complete tower hydraulic/mechanical design and provide the "
                "formal diameter or total height."
            ),
            "rejected_screening_aliases": rejected_screening_aliases,
        })
    return {
        "field_id": field["field_id"], "label": field.get("label"), "unit": field.get("unit"),
        "value": None, "state": "MISSING", "source_field_id": None,
        "source": source,
        "equation_chain": None, "formula_chain": None,
    }


def _field_cell(
    field: Mapping[str, Any],
    context: Mapping[str, Any],
    *,
    evidence_ids: Sequence[str],
    evidence_level: Mapping[str, Any],
    missing_information: Sequence[str] | None = None,
) -> dict[str, Any]:
    field_id = field["field_id"]
    identity_cell = _programmatic_aspen_overview_identity_cell(field, context)
    summary_cell = _summary_special_cell(field_id, field, context)
    if identity_cell is not None:
        cell = identity_cell
    elif summary_cell is not None:
        cell = summary_cell
    elif field_id == "engineering_adjustment_plan":
        plan = context.get("engineering_adjustment_plan", {})
        value = None
        if isinstance(plan, Mapping) and plan:
            value = {
                "status": plan.get("status"),
                "triggered": bool(plan.get("triggered")),
                "trigger_codes": list(plan.get("trigger_codes", [])),
                "configuration": _json_safe(
                    plan.get("configuration", {})
                ),
                "required_actions": _json_safe(
                    plan.get("required_actions", [])
                ),
                "evidence_boundary": _json_safe(
                    plan.get("evidence_boundary", {})
                ),
                "plan_sha256": plan.get("plan_sha256"),
            }
        cell = {
            "field_id": field_id,
            "label": field.get("label"),
            "unit": None,
            "value": value,
            "state": (
                "PROGRAMMATIC_ALGORITHMIC_MODIFICATION_PLAN"
                if value else "MISSING"
            ),
            "source_field_id": None,
            "source": {
                "kind": "deterministic_engineering_adjustment_plan",
                "program_generated": True,
                "evidence_class": "J",
                "promotion_cap": "TYPE_SCREENING",
                "plan_sha256": (
                    plan.get("plan_sha256")
                    if isinstance(plan, Mapping)
                    else None
                ),
            },
            "equation_chain": None,
            "formula_chain": None,
        }
    elif field_id == "algorithmic_selection_warning":
        plan = context.get("engineering_adjustment_plan", {})
        warning = (
            plan.get("algorithmic_selection_warning")
            if isinstance(plan, Mapping)
            else None
        )
        cell = {
            "field_id": field_id,
            "label": field.get("label"),
            "unit": None,
            "value": warning,
            "state": (
                "MANDATORY_ALGORITHMIC_SCREENING_WARNING"
                if _present(warning) else "MISSING"
            ),
            "source_field_id": None,
            "source": {
                "kind": "deterministic_engineering_adjustment_plan",
                "program_generated": True,
                "evidence_class": "J",
                "promotion_cap": "TYPE_SCREENING",
                "plan_sha256": (
                    plan.get("plan_sha256")
                    if isinstance(plan, Mapping)
                    else None
                ),
            },
            "equation_chain": None,
            "formula_chain": None,
        }
    elif field_id == "selection_agent_control_status":
        control = context.get("selection_agent_control", {})
        calculate = (
            control.get("calculate_before_select", {})
            if isinstance(control, Mapping)
            else {}
        )
        value = (
            {
                "status": control.get("status"),
                "calculation_execution_satisfied": calculate.get(
                    "calculation_execution_satisfied"
                ),
                "unsatisfied_calculation_ids": list(
                    calculate.get(
                        "unsatisfied_calculation_ids", []
                    )
                ),
                "connection_component_status": (
                    control.get(
                        "ambiguous_choice_resolution", {}
                    ).get("connection_components", {}).get("status")
                    if isinstance(
                        control.get(
                            "ambiguous_choice_resolution", {}
                        ),
                        Mapping,
                    )
                    and isinstance(
                        control.get(
                            "ambiguous_choice_resolution", {}
                        ).get("connection_components", {}),
                        Mapping,
                    )
                    else None
                ),
                "agent_control_sha256": control.get(
                    "agent_control_sha256"
                ),
            }
            if isinstance(control, Mapping) and control
            else None
        )
        cell = {
            "field_id": field_id,
            "label": field.get("label"),
            "unit": None,
            "value": value,
            "state": (
                "DETERMINISTIC_AGENT_CONTROL"
                if value else "MISSING"
            ),
            "source_field_id": None,
            "source": {
                "kind": "deterministic_selection_agent_control",
                "program_generated": True,
                "agent_control_sha256": (
                    control.get("agent_control_sha256")
                    if isinstance(control, Mapping)
                    else None
                ),
            },
            "equation_chain": None,
            "formula_chain": None,
        }
    elif field_id in {"model_or_specification", "model_designation"}:
        value, state = _model_value(context)
        candidate_audit = _leading_candidate_audit(context)
        candidate_source_metadata = {
            "candidate_id": candidate_audit.get("candidate_id"),
            "candidate_kind": candidate_audit.get("candidate_kind"),
            "candidate_status": candidate_audit.get("candidate_status"),
            "candidate_eligibility": candidate_audit.get("candidate_eligibility"),
            "candidate_source_kind": candidate_audit.get("candidate_source_kind"),
            "program_origin": candidate_audit.get("program_origin"),
            "standard_scope_state": candidate_audit.get("standard_scope_state"),
            "selection_rule_identity": candidate_audit.get(
                "selection_rule_identity"
            ),
            "candidate_valid_for_specificity": candidate_audit.get(
                "valid_for_specificity"
            ),
        }
        if state == "PROGRAMMATIC_PIPE_ENGINEERING_DESIGNATION":
            pipe_specification = context.get("programmatic_pipe_specification", {})
            model_source = {
                "kind": "deterministic_programmatic_pipe_specification",
                "program_generated": True,
                "program_specification_sha256": (
                    pipe_specification.get("program_specification_sha256")
                    if isinstance(pipe_specification, Mapping)
                    else None
                ),
                **candidate_source_metadata,
            }
        elif state == "PROGRAMMATIC_VALVE_ENGINEERING_DESIGNATION":
            valve_specification = context.get(
                "programmatic_valve_specification", {}
            )
            model_source = {
                "kind": "deterministic_programmatic_valve_specification",
                "program_generated": True,
                "program_specification_sha256": (
                    valve_specification.get(
                        "program_specification_sha256"
                    )
                    if isinstance(valve_specification, Mapping)
                    else None
                ),
                **candidate_source_metadata,
            }
        elif state == "ALGORITHMIC_SYSTEM_MODIFICATION_DESIGNATION":
            adjustment_plan = context.get(
                "engineering_adjustment_plan", {}
            )
            model_source = {
                "kind": "deterministic_engineering_adjustment_plan",
                "program_generated": True,
                "evidence_class": "J",
                "promotion_cap": "TYPE_SCREENING",
                "plan_sha256": (
                    adjustment_plan.get("plan_sha256")
                    if isinstance(adjustment_plan, Mapping)
                    else None
                ),
                **candidate_source_metadata,
            }
        else:
            model_source = {
                "kind": "deterministic_model_recommendation",
                **candidate_source_metadata,
            }
        cell = {"field_id": field_id, "label": field.get("label"), "unit": None, "value": value, "state": state,
                "source_field_id": None, "source": model_source,
                "equation_chain": None, "formula_chain": None}
    elif field_id in {"model_or_specification_status", "model_status"}:
        cell = {"field_id": field_id, "label": field.get("label"), "unit": None, "value": _model_status(context),
                "state": "DETERMINED_STATUS", "source_field_id": None,
                "source": {"kind": "deterministic_model_status"}, "equation_chain": None, "formula_chain": None}
    elif field_id in {"standards_and_versions", "standard_identity"}:
        adopted, routes = _standards(context)
        if (
            field_id == "standard_identity"
            and not adopted
            and routes
            and isinstance(context.get("aspen_source_binding"), Mapping)
            and context.get("aspen_source_binding")
        ):
            value = {
                "adopted": [],
                "conditional_candidates": [
                    {
                        "number": item.get("number"),
                        "title": item.get("title"),
                        "reuse_class": item.get("reuse_class"),
                        "state": "CONDITIONAL_STANDARD_CANDIDATE",
                    }
                    for item in routes
                ],
                "formal_adoption_state": "OPEN_PROJECT_GATE",
            }
            state = "CONDITIONALLY_MATCHED_STANDARD"
            source = {
                "kind": "deterministic_standard_route",
                "reference_route_count": len(routes),
                "evidence_class": "D",
                "warning": (
                    "标准候选已列入程序一览表；正式采用仍须按设备适用性和项目规范确认。"
                ),
            }
        else:
            value = (
                adopted
                if field_id == "standards_and_versions"
                else {"adopted": adopted}
            )
            state = "EXPLICIT" if adopted else "NOT_EXPLICITLY_ADOPTED"
            source = {
                "kind": "deterministic_standard_fields",
                "reference_route_count": len(routes),
            }
        cell = {
            "field_id": field_id,
            "label": field.get("label"),
            "unit": None,
            "value": value,
            "state": state,
            "source_field_id": None,
            "source": source,
            "equation_chain": None,
            "formula_chain": None,
        }
    elif field_id in {"evidence_ids", "software_vendor_evidence_refs"}:
        cell = {"field_id": field_id, "label": field.get("label"), "unit": None, "value": list(evidence_ids),
                "state": "INDEXED" if evidence_ids else "MISSING", "source_field_id": None,
                "source": {"kind": "equipment-evidence-index-v1"}, "equation_chain": None, "formula_chain": None}
    elif field_id in {"evidence_level", "evidence_grade"}:
        cell = {"field_id": field_id, "label": field.get("label"), "unit": None,
                "value": evidence_level.get("value"), "state": "ASSESSED" if evidence_level.get("value") != "UNASSESSED" else "UNASSESSED",
                "source_field_id": None, "source": {"kind": "deterministic_evidence_level_policy", **dict(evidence_level)},
                "equation_chain": None, "formula_chain": None}
    elif field_id in {"missing_information", "pending_evidence"}:
        values = list(missing_information or [])
        cell = {"field_id": field_id, "label": field.get("label"), "unit": None, "value": values,
                "state": "OPEN" if values else "NONE", "source_field_id": None,
                "source": {"kind": "profile_and_matcher_gap_union"}, "equation_chain": None, "formula_chain": None}
    else:
        cell = _normal_cell(field, context)
        if (
            cell.get("state") in RAW_CUSTOMER_GAP_STATES
            and field_id in {"equipment_type", "tower_internal_type"}
            and _present(context.get("model", {}).get("recommended_type"))
        ):
            cell.update({
                "value": context["model"]["recommended_type"],
                "state": "DETERMINISTIC_TERMINAL_TYPE",
                "source_field_id": "model_recommendation.recommended_type",
                "source": {"kind": "deterministic_terminal_selection"},
            })
    if str(cell.get("state") or "") in RAW_CUSTOMER_GAP_STATES:
        cell = _explicit_open_gate_cell(field, cell)
    elif str(cell.get("state") or "") == EXPLICIT_OPEN_GATE_STATE:
        cell = _ensure_open_gate_metadata(field, cell)
    cell.update({
        "requirement": field.get("requirement", "required"),
        "evidence_gate": _json_safe(field.get("evidence_gate")),
        "source_refs": _json_safe(field.get("source_refs", [])),
        "profile_ids": _json_safe(field.get("profile_ids", [])),
    })
    return _json_safe(cell)


def _customer_table_missing(
    fields: Sequence[Mapping[str, Any]],
    cells: Sequence[Mapping[str, Any]],
) -> list[str]:
    missing: set[str] = set()
    excluded = {
        "missing_information", "pending_evidence", "evidence_ids", "software_vendor_evidence_refs",
        "evidence_level", "evidence_grade",
    }
    for field, cell in zip(fields, cells):
        if field["field_id"] in excluded or str(field.get("requirement", "required")) in {"optional", "informational"}:
            continue
        if str(cell.get("state") or "") in {
            *RAW_CUSTOMER_GAP_STATES,
            EXPLICIT_OPEN_GATE_STATE,
        }:
            missing.add(str(field["field_id"]))
    return sorted(missing)


def _customer_full_field_coverage(
    fields: Sequence[Mapping[str, Any]],
    cells: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Audit that every requested customer field has a visible cell.

    This is deliberately a *structure/presentation* gate.  An explicit OPEN
    cell satisfies full-field coverage, but it remains an information and
    formal-readiness blocker elsewhere.
    """

    expected = [str(field.get("field_id") or "") for field in fields]
    emitted = [str(cell.get("field_id") or "") for cell in cells]
    cells_by_id = {str(cell.get("field_id") or ""): cell for cell in cells}
    blocking_reasons: list[str] = []
    if emitted != expected:
        blocking_reasons.append("CUSTOMER_FIELD_ORDER_OR_ID_MISMATCH")
    if len(set(emitted)) != len(emitted):
        blocking_reasons.append("DUPLICATE_CUSTOMER_FIELD_ID")
    missing_cell_ids = [
        field_id for field_id in expected if field_id not in cells_by_id
    ]
    if missing_cell_ids:
        blocking_reasons.append("CUSTOMER_FIELD_CELL_NOT_EMITTED")
    unrepresented_field_ids: list[str] = []
    explicit_open_field_ids: list[str] = []
    not_applicable_field_ids: list[str] = []
    value_field_ids: list[str] = []
    for field_id in expected:
        cell = cells_by_id.get(field_id, {})
        state = str(cell.get("state") or "")
        if (
            state == EXPLICIT_OPEN_GATE_STATE
            and _present(cell.get("display_value"))
            and _present(
                cell.get("source", {}).get("promotion_cap")
                if isinstance(cell.get("source"), Mapping)
                else None
            )
        ):
            explicit_open_field_ids.append(field_id)
            continue
        if _present(cell.get("value")):
            value_field_ids.append(field_id)
            continue
        if state in {"NOT_APPLICABLE", "NONE"}:
            not_applicable_field_ids.append(field_id)
            continue
        unrepresented_field_ids.append(field_id)
    if unrepresented_field_ids:
        blocking_reasons.append(
            "CUSTOMER_FIELD_HAS_NO_VALUE_OPEN_GATE_OR_NOT_APPLICABLE_MARKER"
        )
    return {
        "required": len(expected),
        "emitted": len(emitted),
        "represented": (
            len(expected)
            - len(missing_cell_ids)
            - len(unrepresented_field_ids)
        ),
        "value_fields": value_field_ids,
        "explicit_open_fields": explicit_open_field_ids,
        "not_applicable_fields": not_applicable_field_ids,
        "missing_cell_ids": missing_cell_ids,
        "unrepresented_field_ids": unrepresented_field_ids,
        "blocking_reasons": sorted(set(blocking_reasons)),
        "state": "PASS" if not blocking_reasons else "BLOCKED",
        "claim_boundary": (
            "PASS confirms that every requested field is emitted as a value, "
            "an explicit non-promotable OPEN cell, or an explicit N/A cell; "
            "it does not confirm formal data closure."
        ),
    }


def _missing_union(context: Mapping[str, Any], fields: Sequence[Mapping[str, Any]], cells: Sequence[Mapping[str, Any]]) -> list[str]:
    missing: set[str] = set(_customer_table_missing(fields, cells))
    decision = context["result"].get("model_decision", {})
    if isinstance(decision, Mapping):
        missing.update(str(item) for item in decision.get("verification_missing_fields", []) if _present(item))
        missing.update(str(item) for item in decision.get("sizing_missing_fields", []) if _present(item))
    model = context["model"]
    missing.update(str(item) for item in model.get("minimum_candidate_missing_fields", []) if _present(item))
    vector = context["package"].get("selection_feature_vector", {})
    if isinstance(vector, Mapping):
        missing.update(str(item) for item in vector.get("missing_fields", []) if _present(item))
    for pending in context["result"].get("calculation_pending", []) if isinstance(context["result"].get("calculation_pending"), list) else []:
        if isinstance(pending, Mapping):
            missing.update(str(item) for item in pending.get("missing_fields", []) if _present(item))
    return sorted(missing)


def _equipment_sort_key(context: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        str(context.get("equipment_tag") or context["equipment_key"]).casefold(),
        "|".join(context["family_ids"]),
        context["input_sha256"],
    )


def _attach_programmatic_aspen_overview_identity(
    context: dict[str, Any],
    sequence_number: int,
) -> None:
    """Fill administrative overview cells without inventing project authority.

    Aspen provides physical topology and case identity, but normally does not
    carry the project's 3-2 overview sequence, process-section code, display
    name, installed quantity or standby philosophy.  The program can still
    emit a complete, useful row by binding deterministic display identities to
    the Aspen case/PFD and keeping project quantity/standby authority open.
    Generic non-Aspen matcher calls retain the previous no-invention behavior.
    """

    binding = context.get("aspen_source_binding")
    if not isinstance(binding, Mapping) or not binding:
        return
    values = context.get("values", {})
    rows = context.get("rows", {})
    if not isinstance(values, Mapping) or not isinstance(rows, Mapping):
        return

    case_id = str(binding.get("case_id") or "UNNAMED-ASPEN-CASE")
    tag = str(context.get("equipment_tag") or context["equipment_key"])
    record_kind = str(context.get("record_kind") or "equipment")
    descriptors: dict[str, dict[str, Any]] = {}

    def already_present(field_id: str) -> bool:
        if _present(values.get(field_id)):
            return True
        row = rows.get(field_id)
        return isinstance(row, Mapping) and _present(row.get("raw_value"))

    if not already_present("sequence_number"):
        descriptors["sequence_number"] = {
            "value": sequence_number,
            "unit": None,
            "state": "PROGRAMMATIC_BATCH_SEQUENCE",
            "derivation": "stable_sort_by_equipment_tag_family_and_input_sha256",
            "evidence_class": "D",
            "warning": (
                "该序号由本次程序交付批次稳定排序生成，不替代项目文件的正式序号。"
            ),
        }
    if not already_present("process_section"):
        descriptors["process_section"] = {
            "value": (
                f"Aspen案例全流程：{case_id}"
                "（BKP未提供项目工段编码）"
            ),
            "unit": None,
            "state": "PROGRAMMATIC_CASE_SCOPE_WITH_OPEN_PROJECT_GATE",
            "derivation": "case_id_to_overview_scope_label",
            "evidence_class": "D",
            "warning": (
                "当前值准确标识Aspen案例范围；项目工段编码仍须由项目文件确认。"
            ),
        }
    if not already_present("equipment_name"):
        if record_kind == "piping":
            medium = str(values.get("medium_name") or "").strip()
            primary_medium = medium.split("+", 1)[0].strip()
            primary_medium = re.sub(r"\s*\([^)]*\)\s*$", "", primary_medium)
            display_type = f"{primary_medium or '工艺介质'}管线"
        else:
            display_type = str(
                context.get("model", {}).get("recommended_type")
                or context.get("family_name")
                or "工艺设备"
            )
        descriptors["equipment_name"] = {
            "value": f"{display_type}（{tag}）",
            "unit": None,
            "state": "PROGRAMMATIC_ASPEN_DISPLAY_IDENTITY",
            "derivation": (
                "primary_medium_plus_line_number"
                if record_kind == "piping"
                else "deterministic_terminal_type_plus_equipment_tag"
            ),
            "evidence_class": "D",
            "warning": (
                "该名称用于程序交付表显示；若项目另有正式设备名称，应以项目文件替换并重算。"
            ),
        }
    quantity_sources = {
        "quantity",
        "count",
        "quantity_count",
        "operating_quantity",
        "standby_quantity",
        "standby_scheme",
        "standby_configuration",
    }
    if not any(already_present(field_id) for field_id in quantity_sources):
        adjustment_plan = context.get(
            "engineering_adjustment_plan", {}
        )
        adjustment_configuration = (
            adjustment_plan.get("configuration", {})
            if isinstance(adjustment_plan, Mapping)
            else {}
        )
        if (
            isinstance(adjustment_plan, Mapping)
            and adjustment_plan.get("triggered") is True
            and isinstance(adjustment_configuration, Mapping)
        ):
            descriptors["quantity_and_standby"] = {
                "value": {
                    "aspen_pfd_object_count": 1,
                    "object_kind": "physical_equipment_block",
                    "algorithmic_parallel_train_count_estimate": (
                        adjustment_configuration.get(
                            "parallel_train_count_estimate"
                        )
                    ),
                    "algorithmic_series_units_per_train_estimate": (
                        adjustment_configuration.get(
                            "series_units_per_train_estimate"
                        )
                    ),
                    "algorithmic_operating_unit_count_estimate": (
                        adjustment_configuration.get(
                            "operating_unit_count_estimate"
                        )
                    ),
                    "algorithmic_standby_train_count_recommendation": (
                        adjustment_configuration.get(
                            "standby_train_count_recommendation"
                        )
                    ),
                    "algorithmic_installed_unit_count_estimate": (
                        adjustment_configuration.get(
                            "installed_unit_count_estimate"
                        )
                    ),
                    "arrangement_code": (
                        adjustment_configuration.get(
                            "arrangement_code"
                        )
                    ),
                    "project_installed_quantity": None,
                    "project_operating_quantity": None,
                    "project_standby_quantity": None,
                    "project_confirmation_state": "OPEN",
                    "plan_sha256": adjustment_plan.get(
                        "plan_sha256"
                    ),
                    "statement": (
                        "以上台数及串并联方式为程序算法初筛；"
                        "项目确认数量、可靠性和备用方案仍为OPEN。"
                    ),
                },
                "unit": None,
                "state": (
                    "PROGRAMMATIC_ALGORITHMIC_QUANTITY_ESTIMATE_"
                    "WITH_OPEN_PROJECT_GATE"
                ),
                "derivation": (
                    "verified_engineering_adjustment_plan_configuration"
                ),
                "evidence_class": "J",
                "warning": adjustment_plan.get(
                    "algorithmic_selection_warning"
                ),
            }
        else:
            descriptors["quantity_and_standby"] = {
                "value": {
                    "aspen_pfd_object_count": 1,
                    "object_kind": (
                        "material_stream"
                        if record_kind == "piping"
                        else "physical_equipment_block"
                    ),
                    "project_installed_quantity": None,
                    "project_operating_quantity": None,
                    "project_standby_quantity": None,
                    "standby_configuration": "NOT_MODELED_IN_ASPEN_BKP",
                    "statement": (
                        "本行对应1条Aspen物料流；并联、安装数量及备用方案待项目确认。"
                        if record_kind == "piping"
                        else "本行对应1个Aspen物理设备块；安装数量及备用方案待项目确认。"
                    ),
                },
                "unit": None,
                "state": "PROGRAMMATIC_PFD_COUNT_WITH_OPEN_PROJECT_QUANTITY_GATE",
                "derivation": "one_authority_row_per_verified_aspen_pfd_object",
                "evidence_class": "D",
                "warning": (
                    "1表示本程序表粒度中的Aspen对象数，不表示项目已确认安装台数或备用台数。"
                ),
            }

    if not descriptors:
        return
    identity_basis = {
        "input_sha256": context.get("input_sha256"),
        "record_kind": record_kind,
        "equipment_key": context.get("equipment_key"),
        "case_id": case_id,
        "source_export_sha256": binding.get("source_export_sha256"),
        "pfd_mapping_sha256": binding.get("pfd_mapping_sha256"),
        "descriptors": descriptors,
    }
    identity_sha256 = _sha256_json(identity_basis)
    context["programmatic_aspen_overview_identity"] = {
        field_id: {
            **descriptor,
            "source": {
                "kind": "programmatic_aspen_overview_identity",
                "program_generated": True,
                "input_sha256": context.get("input_sha256"),
                "case_id": case_id,
                "source_export_sha256": binding.get("source_export_sha256"),
                "pfd_mapping_sha256": binding.get("pfd_mapping_sha256"),
                "overview_identity_sha256": identity_sha256,
                "derivation": descriptor.get("derivation"),
                "evidence_class": descriptor.get("evidence_class"),
                "warning": descriptor.get("warning"),
            },
        }
        for field_id, descriptor in descriptors.items()
    }


def _programmatic_aspen_overview_identity_cell(
    field: Mapping[str, Any],
    context: Mapping[str, Any],
) -> dict[str, Any] | None:
    identity = context.get("programmatic_aspen_overview_identity")
    if not isinstance(identity, Mapping):
        return None
    field_id = str(field.get("field_id") or "")
    descriptor = identity.get(field_id)
    if not isinstance(descriptor, Mapping) or not _present(descriptor.get("value")):
        return None
    return {
        "field_id": field_id,
        "label": field.get("label"),
        "unit": field.get("unit") or descriptor.get("unit"),
        "value": _json_safe(descriptor.get("value")),
        "state": str(descriptor.get("state") or "PROGRAMMATIC_ASPEN_OVERVIEW_IDENTITY"),
        "source_field_id": None,
        "source": _json_safe(descriptor.get("source", {})),
        "equation_chain": None,
        "formula_chain": None,
    }


PROVENANCE_ORIGINS = {
    "ASPEN_EXTRACTED",
    "CALCULATED",
    "SELECTOR_RULE",
    "PROJECT_INPUT",
    "DISPLAY_ONLY",
    "OPEN_GATE",
}
ENGINEERING_PROVENANCE_ORIGINS = {
    "ASPEN_EXTRACTED",
    "CALCULATED",
    "SELECTOR_RULE",
    "PROJECT_INPUT",
}
DISPLAY_ONLY_SOURCE_KINDS = {
    "programmatic_aspen_overview_identity",
    "registered_display_fallback",
    "registered_quantity_fallback",
    "registered_3_2_pump_display_fallback",
    "registered_3_2_valve_preliminary_fallback",
    "deterministic_display_composition",
    "tag_quantity_derivation",
}
OPEN_GATE_SOURCE_KINDS = {
    "registered_formal_evidence_gate",
    "not_available",
    "profile_and_matcher_gap_union",
    "fallback_graph_schema",
}
SELECTOR_RULE_SOURCE_KINDS = {
    "deterministic_connection_selector",
    "deterministic_evidence_level_policy",
    "deterministic_family_match",
    "deterministic_model_recommendation",
    "deterministic_model_status",
    "deterministic_programmatic_pipe_specification",
    "deterministic_programmatic_valve_specification",
    "deterministic_projection_of_existing_fields",
    "deterministic_standard_fields",
    "deterministic_terminal_selection",
    "equipment-evidence-index-v1",
    "selection_feature_vector",
    "knowledge_graph_model_rule",
    "bundled_standard_reference_catalog",
}
CALCULATED_SOURCE_KINDS = {
    "deterministic_calculation",
    "provisional_screening_calculation",
}
PROJECT_INPUT_SOURCE_KINDS = {
    "normalized_input",
    "project_input",
    "explicit_not_applicable_token",
}


def _provenance_origin(cell: Mapping[str, Any]) -> str:
    """Classify one cell by the authority that produced its usable value."""

    source = (
        dict(cell.get("source"))
        if isinstance(cell.get("source"), Mapping)
        else {}
    )
    source_kind = str(source.get("kind") or "").strip()
    state = str(cell.get("state") or "").strip().upper()
    if (
        source_kind in DISPLAY_ONLY_SOURCE_KINDS
        or state.startswith("DEFAULTED")
        or state
        in {
            "PROGRAMMATIC_BATCH_SEQUENCE",
            "PROGRAMMATIC_CASE_SCOPE_WITH_OPEN_PROJECT_GATE",
            "PROGRAMMATIC_ASPEN_DISPLAY_IDENTITY",
            "PROGRAMMATIC_PFD_COUNT_WITH_OPEN_PROJECT_QUANTITY_GATE",
        }
    ):
        return "DISPLAY_ONLY"
    if (
        _unverified_cross_standard_source(source)
        or source_kind in OPEN_GATE_SOURCE_KINDS
        or state in {
            "MISSING",
            "EXTERNAL_REQUIRED",
            "NOT_EXPLICITLY_ADOPTED",
            "OPEN_FORMAL_EVIDENCE_GATE",
            "CONDITIONALLY_MATCHED_STANDARD",
        }
    ):
        return "OPEN_GATE"
    if source_kind in SELECTOR_RULE_SOURCE_KINDS:
        return "SELECTOR_RULE"
    if (
        source_kind in CALCULATED_SOURCE_KINDS
        or state in {"CALCULATED", "DERIVED_BY_REGISTERED_FORMULA"}
    ):
        return "CALCULATED"
    if (
        state == "DERIVED_FROM_ASPEN"
        or isinstance(source.get("aspen_parameter_lineage"), Mapping)
    ):
        return "ASPEN_EXTRACTED"
    if (
        source_kind in PROJECT_INPUT_SOURCE_KINDS
        or state in {"PROVIDED", "EXPLICIT"}
    ):
        return "PROJECT_INPUT"
    if source_kind == "deterministic_result_value":
        return "PROJECT_INPUT"
    return "OPEN_GATE"


def _annotate_provenance(cell: dict[str, Any]) -> str:
    origin = _provenance_origin(cell)
    source = (
        dict(cell.get("source"))
        if isinstance(cell.get("source"), Mapping)
        else {}
    )
    source["provenance_origin"] = origin
    cell["source"] = source
    cell["provenance_origin"] = origin
    return origin


def _customer_row_source_binding(context: Mapping[str, Any]) -> dict[str, Any]:
    binding = (
        dict(context.get("aspen_source_binding"))
        if isinstance(context.get("aspen_source_binding"), Mapping)
        else {}
    )
    return {
        "source_chain_binding": _json_safe(binding),
        "source_chain_binding_sha256": _sha256_json(binding),
        "derivation_record_kind": binding.get("derivation_record_kind"),
        "derivation_record_identity": binding.get(
            "derivation_record_identity"
        ),
        "program_generated_record_sha256": binding.get(
            "program_generated_record_sha256"
        ),
        "program_generated_record_binding_sha256": binding.get(
            "program_generated_record_binding_sha256"
        ),
    }


def _customer_cell_source_binding(
    context: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a compact pointer to the row-level source-chain binding."""

    projection = _customer_row_source_binding(context)
    projection.pop("source_chain_binding", None)
    return projection


def _compact_cell_source_binding(
    cell: dict[str, Any],
    context: Mapping[str, Any],
) -> None:
    """Replace a repeated source-chain body with its row-level hash pointer."""

    binding = (
        dict(context.get("aspen_source_binding"))
        if isinstance(context.get("aspen_source_binding"), Mapping)
        else {}
    )
    binding_sha256 = _sha256_json(binding)

    def compact(value: Any) -> None:
        if isinstance(value, dict):
            if "aspen_source_binding" in value:
                embedded = value.pop("aspen_source_binding")
                if (
                    isinstance(embedded, Mapping)
                    and _sha256_json(embedded) != binding_sha256
                ):
                    raise CustomerDeliveryError(
                        "cell source-chain binding does not match its "
                        "row-level binding"
                    )
                value["aspen_source_binding_sha256"] = binding_sha256
                value["aspen_source_binding_scope"] = (
                    "ROW_LEVEL_SOURCE_CHAIN_POINTER"
                )
            for nested in value.values():
                compact(nested)
        elif isinstance(value, list):
            for nested in value:
                compact(nested)

    compact(cell)
    source = (
        dict(cell.get("source"))
        if isinstance(cell.get("source"), Mapping)
        else {}
    )
    source["aspen_source_binding_sha256"] = binding_sha256
    source["aspen_source_binding_scope"] = "ROW_LEVEL_SOURCE_CHAIN_POINTER"
    cell["source"] = source


def _bind_delivery_cells(
    cells: Sequence[Mapping[str, Any]],
    context: Mapping[str, Any],
    *,
    scope: str,
) -> list[dict[str, Any]]:
    """Make every emitted delivery cell independently hash-verifiable."""

    bound: list[dict[str, Any]] = []
    for index, original in enumerate(cells):
        cell = copy.deepcopy(dict(original))
        _annotate_provenance(cell)
        _compact_cell_source_binding(cell, context)
        cell["delivery_field_index"] = index
        cell["delivery_scope"] = scope
        cell["program_generated"] = True
        cell["manual_postprocessing"] = False
        cell.update(_customer_cell_source_binding(context))
        cell["cell_sha256"] = _sha256_json({
            "input_sha256": context.get("input_sha256"),
            "record_kind": context.get("record_kind"),
            "delivery_scope": scope,
            "delivery_field_index": index,
            "field_id": cell.get("field_id"),
            "value": cell.get("value"),
            "display_value": cell.get("display_value"),
            "unit": cell.get("unit"),
            "state": cell.get("state"),
            "promotion_cap": cell.get("promotion_cap"),
            "open_gate": cell.get("open_gate"),
            "source_field_id": cell.get("source_field_id"),
            "source": cell.get("source"),
            "requirement": cell.get("requirement"),
            "evidence_gate": cell.get("evidence_gate"),
            "source_refs": cell.get("source_refs", []),
            "profile_ids": cell.get("profile_ids", []),
            "source_chain_binding_sha256": cell.get(
                "source_chain_binding_sha256"
            ),
            "derivation_record_kind": cell.get("derivation_record_kind"),
            "derivation_record_identity": cell.get(
                "derivation_record_identity"
            ),
            "program_generated_record_sha256": cell.get(
                "program_generated_record_sha256"
            ),
            "program_generated_record_binding_sha256": cell.get(
                "program_generated_record_binding_sha256"
            ),
        })
        bound.append(_json_safe(cell))
    return bound


UNRESOLVED_AUTHORITY_CELL_STATES = {
    *RAW_CUSTOMER_GAP_STATES,
    EXPLICIT_OPEN_GATE_STATE,
}
SPECIFIC_SELECTION_IMPACTS = {
    "identity",
    "calculation_input",
    "candidate_selection",
    "derived_design_parameter",
}
NONCONCRETE_SELECTION_TOKENS = (
    "非标准",
    "非标",
    "未定型",
    "待定",
    "待确认",
    "其他型式",
    "通用型",
    "generic",
    "placeholder",
    "unknown",
)


def _authority_cell_resolved(cell: Mapping[str, Any]) -> bool:
    if (
        not _present(cell.get("value"))
        or str(cell.get("state") or "")
        in UNRESOLVED_AUTHORITY_CELL_STATES
    ):
        return False
    source = (
        cell.get("source")
        if isinstance(cell.get("source"), Mapping)
        else {}
    )
    promotion_cap = str(
        source.get("promotion_cap")
        or cell.get("promotion_cap")
        or ""
    ).strip().upper()
    result_status = str(source.get("result_status") or "").strip().upper()
    if (
        promotion_cap in {"TYPE_SCREENING", "NOT_PROMOTABLE"}
        or result_status == "PROVISIONAL"
        or source.get("formal_design_evidence") is False
    ):
        return False
    return True


def _selection_impact_cell_resolved(cell: Mapping[str, Any]) -> bool:
    return (
        _present(cell.get("value"))
        and str(cell.get("state") or "")
        not in UNRESOLVED_AUTHORITY_CELL_STATES
        and str(cell.get("provenance_origin") or "")
        in ENGINEERING_PROVENANCE_ORIGINS
    )


def _programmatic_valve_preliminary_gate_resolved(
    field_id: str,
    cell: Mapping[str, Any],
    context: Mapping[str, Any],
) -> bool:
    """Allow an explicit *formal* valve gate without erasing type specificity.

    A gas/two-phase valve can have a concrete preliminary construction and
    adjacent-line DN/PN candidate while compressible-flow capacity remains
    deliberately open.  This exception is intentionally narrow: it only
    applies to a verified programmatic valve specification and never resolves
    the formal-readiness gate.
    """

    specification = context.get("programmatic_valve_specification")
    if (
        not isinstance(specification, Mapping)
        or specification.get("status")
        != "PRELIMINARY_CONCRETE_SPECIFICATION_SELECTED"
    ):
        return False
    fields = specification.get("fields")
    descriptor = fields.get(field_id) if isinstance(fields, Mapping) else None
    if (
        not isinstance(descriptor, Mapping)
        or str(descriptor.get("state") or "")
        != "OPEN_FORMAL_EVIDENCE_GATE"
        or not _present(descriptor.get("value"))
        or str(cell.get("state") or "") != "OPEN_FORMAL_EVIDENCE_GATE"
        or str(cell.get("source", {}).get("kind") or "")
        != "deterministic_programmatic_valve_specification"
    ):
        return False

    def field_value(name: str) -> Any:
        item = fields.get(name) if isinstance(fields, Mapping) else None
        return item.get("value") if isinstance(item, Mapping) else None

    if field_id == "pressure_temperature_rating":
        return (
            bool(re.search(r"(?<![A-Za-z0-9])PN\s*\d+", str(field_value("pressure_class") or ""), re.IGNORECASE))
            and _present(field_value("body_material_grade"))
            and _present(field_value("equipment_type"))
        )
    if field_id == "cv":
        process_basis = specification.get("process_basis")
        phase = (
            str(process_basis.get("phase") or "").casefold()
            if isinstance(process_basis, Mapping)
            else ""
        )
        value = str(descriptor.get("value") or "")
        return (
            phase in {"vapor", "mixed"}
            and value
            in {
                "OPEN_GAS_COMPRESSIBLE_AND_CHOKED_FLOW_CAPACITY_GATE",
                "OPEN_TWO_PHASE_SPECIALIST_SIZING_GATE",
            }
        )
    return False


def _concrete_selection_identity(context: Mapping[str, Any]) -> dict[str, Any]:
    model_value, model_value_state = _model_value(context)
    candidate_audit = _leading_candidate_audit(context)
    recommended_type = context.get("model", {}).get("recommended_type")
    pipe_specification = context.get("programmatic_pipe_specification", {})
    pipe_fields = (
        pipe_specification.get("fields", {})
        if isinstance(pipe_specification, Mapping)
        else {}
    )
    pipe_type = (
        pipe_fields.get("equipment_type", {}).get("value")
        if isinstance(pipe_fields, Mapping)
        and isinstance(pipe_fields.get("equipment_type"), Mapping)
        else None
    )
    if _present(pipe_type):
        recommended_type = pipe_type
    valve_specification = context.get(
        "programmatic_valve_specification", {}
    )
    valve_fields = (
        valve_specification.get("fields", {})
        if isinstance(valve_specification, Mapping)
        else {}
    )

    def valve_field_value(field_id: str) -> Any:
        descriptor = (
            valve_fields.get(field_id)
            if isinstance(valve_fields, Mapping)
            else None
        )
        return (
            descriptor.get("value")
            if isinstance(descriptor, Mapping)
            else None
        )

    valve_type = valve_field_value("equipment_type")
    if _present(valve_type):
        recommended_type = valve_type
    identity_text = " | ".join(
        str(value).strip()
        for value in (recommended_type, model_value)
        if _present(value)
    )
    folded = identity_text.casefold()
    prohibited = sorted({
        token for token in NONCONCRETE_SELECTION_TOKENS
        if token.casefold() in folded
    })
    record_kind = str(context.get("record_kind") or "equipment")
    pipe_identity = (
        record_kind == "piping"
        or "family_process_piping" in context.get("family_ids", [])
        or (
            isinstance(pipe_specification, Mapping)
            and pipe_specification.get("status")
            == "PRELIMINARY_CONCRETE_SPECIFICATION_SELECTED"
        )
    )
    detail_checks: dict[str, bool] = {}
    if pipe_identity:
        detail_checks = {
            "leading_candidate_audit_passed": bool(
                candidate_audit.get("valid_for_specificity")
            ),
            "programmatic_pipe_specification_selected": (
                isinstance(pipe_specification, Mapping)
                and pipe_specification.get("status")
                == "PRELIMINARY_CONCRETE_SPECIFICATION_SELECTED"
            ),
            "nominal_size_present": bool(
                re.search(
                    r"(?<![A-Za-z0-9])DN\s*\d+",
                    identity_text,
                    flags=re.IGNORECASE,
                )
            ),
            "outer_diameter_and_wall_present": bool(
                re.search(r"(?:φ|OD\s*)\d", identity_text, flags=re.IGNORECASE)
                and re.search(r"(?:×|[xX])\s*\d", identity_text)
            ),
            "pressure_class_present": bool(
                re.search(
                    r"(?<![A-Za-z0-9])PN\s*\d+",
                    identity_text,
                    flags=re.IGNORECASE,
                )
            ),
            "material_route_present": (
                "钢" in identity_text
                and any(
                    token in identity_text
                    for token in (
                        "20钢",
                        "15CrMo",
                        "S316",
                        "不锈钢",
                        "碳钢板材",
                    )
                )
            ),
            "connection_present": any(
                token in identity_text for token in ("对焊", "法兰", "螺纹")
            ),
            "piping_class_present": "管道等级" in identity_text,
        }
        detailed_designation = (
            _present(model_value)
            and model_value_state != "TYPE_ONLY"
            and all(detail_checks.values())
        )
    elif (
        isinstance(valve_specification, Mapping)
        and valve_specification.get("status")
        == "PRELIMINARY_CONCRETE_SPECIFICATION_SELECTED"
    ):
        adjacent = valve_specification.get("adjacent_line_binding")
        detail_checks = {
            "leading_candidate_audit_passed": bool(
                candidate_audit.get("valid_for_specificity")
            ),
            "programmatic_valve_specification_selected": True,
            "specific_valve_type_present": _present(
                valve_field_value("equipment_type")
            ),
            "body_dn_present": _present(
                valve_field_value("selected_dn")
            ),
            "pressure_series_present": bool(
                re.search(
                    r"(?<![A-Za-z0-9])PN\s*\d+",
                    str(valve_field_value("pressure_class") or ""),
                    flags=re.IGNORECASE,
                )
            ),
            "body_trim_seat_materials_present": all(
                _present(valve_field_value(field_id))
                for field_id in (
                    "body_material_grade",
                    "internals_material_grade",
                    "seat_material_grade",
                )
            ),
            "connection_actuator_and_fail_action_present": all(
                _present(valve_field_value(field_id))
                for field_id in (
                    "connection_type",
                    "actuator_type",
                    "fail_position",
                )
            ),
            "adjacent_line_hash_binding_present": (
                isinstance(adjacent, Mapping)
                and bool(
                    _HASH_RE.fullmatch(
                        str(
                            adjacent.get(
                                "inlet_pipe_specification_sha256"
                            )
                            or ""
                        ).upper()
                    )
                )
                and bool(
                    _HASH_RE.fullmatch(
                        str(
                            adjacent.get(
                                "outlet_pipe_specification_sha256"
                            )
                            or ""
                        ).upper()
                    )
                )
            ),
            "line_transition_plan_present": _present(
                valve_field_value("line_transition_plan")
            ),
        }
        detailed_designation = (
            _present(model_value)
            and model_value_state != "TYPE_ONLY"
            and all(detail_checks.values())
        )
    else:
        structured_pairs = re.findall(
            r"(?:^|\|)\s*[^|=]{1,40}=",
            str(model_value or ""),
        )
        explicit_model_code = bool(
            re.search(
                r"\b[A-Za-z0-9]+(?:[-/][A-Za-z0-9]+){2,}\b",
                str(model_value or ""),
            )
        )
        detail_checks = {
            "leading_candidate_audit_passed": bool(
                candidate_audit.get("valid_for_specificity")
            ),
            "specific_type_present": bool(_present(recommended_type)),
            "sizing_or_model_identity_present": (
                len(structured_pairs) >= 2 or explicit_model_code
            ),
        }
        detailed_designation = (
            _present(model_value)
            and model_value_state != "TYPE_ONLY"
            and all(detail_checks.values())
        )
    detail_blockers = sorted(
        check_id for check_id, passed in detail_checks.items() if not passed
    )
    return {
        "recommended_type": _json_safe(recommended_type),
        "model_or_specification": _json_safe(model_value),
        "model_or_specification_state": model_value_state,
        "concrete_terminal_type": bool(_present(recommended_type) and not prohibited),
        "detailed_designation": bool(detailed_designation and not prohibited),
        "designation_detail_checks": detail_checks,
        "designation_detail_blockers": detail_blockers,
        "prohibited_tokens": prohibited,
        "candidate_id": candidate_audit.get("candidate_id"),
        "candidate_kind": candidate_audit.get("candidate_kind"),
        "candidate_status": candidate_audit.get("candidate_status"),
        "candidate_eligibility": candidate_audit.get("candidate_eligibility"),
        "candidate_source_kind": candidate_audit.get("candidate_source_kind"),
        "eligible_for_leading_candidate": candidate_audit.get(
            "eligible_for_leading_candidate"
        ),
        "program_origin": candidate_audit.get("program_origin"),
        "standard_scope_state": candidate_audit.get("standard_scope_state"),
        "selection_rule_identity": candidate_audit.get(
            "selection_rule_identity"
        ),
        "candidate_validation_checks": candidate_audit.get(
            "validation_checks", {}
        ),
        "candidate_validation_blockers": candidate_audit.get(
            "validation_blockers", []
        ),
    }


def _authority_overview_projection(
    selected_profiles: Sequence[Mapping[str, Any]],
    cells: Sequence[Mapping[str, Any]],
    profiles: Mapping[str, Any],
    context: Mapping[str, Any],
    *,
    evidence_ids: Sequence[str],
    evidence_level: Mapping[str, Any],
    missing_information: Sequence[str],
    customer_table_missing_fields: Sequence[str],
) -> dict[str, Any]:
    """Project one complete 3-2 authority row without splitting its fields."""

    candidates = [
        profile for profile in selected_profiles
        if profile.get("authority_section_id")
        and profile.get("authority_overview_columns")
    ]
    customer_information_excluded = {
        "missing_information",
        "pending_evidence",
        "evidence_ids",
        "software_vendor_evidence_refs",
        "evidence_level",
        "evidence_grade",
    }
    common_required_field_ids = {
        str(field.get("field_id"))
        for field in profiles.get("common_fields", [])
        if isinstance(field, Mapping)
        and str(field.get("requirement", "required"))
        not in {"optional", "informational"}
        and str(field.get("field_id")) not in customer_information_excluded
    }
    customer_table_open_gate_fields = sorted({
        str(field_id)
        for field_id in customer_table_missing_fields
        if _present(field_id)
    })
    customer_information_blockers = sorted({
        str(cell.get("field_id"))
        for cell in cells
        if str(cell.get("field_id")) in common_required_field_ids
        and (
            not _present(cell.get("value"))
            or str(cell.get("state") or "")
            in UNRESOLVED_AUTHORITY_CELL_STATES
        )
    } | set(customer_table_open_gate_fields))
    customer_information_state = (
        "PASS"
        if not customer_information_blockers
        else "PROVISIONAL_WITH_OPEN_GAPS"
    )
    if not candidates:
        all_equipment_fields = _bind_delivery_cells(
            cells,
            context,
            scope="all_equipment_fields",
        )
        all_equipment_fields_sha256 = _sha256_json([
            cell.get("cell_sha256") for cell in all_equipment_fields
        ])
        row_hash = _sha256_json({
            "input_sha256": context.get("input_sha256"),
            "record_kind": context.get("record_kind"),
            "aspen_source_binding": context.get("aspen_source_binding", {}),
            "authority_table_id": None,
            "authority_source": profiles.get("minimum_output_authority", {}),
            "authority_cell_hashes": [],
            "all_equipment_fields_sha256": all_equipment_fields_sha256,
            "information_coverage_state": "NOT_APPLICABLE",
            "customer_information_state": customer_information_state,
            "specificity_state": "NOT_APPLICABLE",
            "formal_gate_blockers": [],
        })
        return {
            "authority_table_id": None,
            "authority_table_title": None,
            "authority_source": _json_safe(profiles.get("minimum_output_authority", {})),
            "authority_columns": [],
            "authority_cells": [],
            "authority_missing_fields": [],
            "authority_completeness": {"required": 0, "populated": 0, "state": "NOT_APPLICABLE"},
            "authority_structural_completeness": {
                "required": 0,
                "emitted": 0,
                "unique": 0,
                "state": "NOT_APPLICABLE",
            },
            "authority_full_field_coverage": {
                "required": 0,
                "emitted": 0,
                "represented": 0,
                "explicit_open_fields": [],
                "blocking_reasons": [],
                "state": "NOT_APPLICABLE",
                "claim_boundary": (
                    "No dedicated authority overview profile applies."
                ),
            },
            "authority_information_coverage": {
                "required": 0,
                "covered": 0,
                "blocking_fields": [],
                "explicit_open_gate_fields": [],
                "customer_table_open_gate_fields": (
                    customer_table_open_gate_fields
                ),
                "state": "NOT_APPLICABLE",
            },
            "customer_information_coverage": {
                "state": customer_information_state,
                "blocking_fields": customer_information_blockers,
                "open_gate_fields": customer_table_open_gate_fields,
            },
            "selection_specificity_gate": {
                "state": "NOT_APPLICABLE",
                "required_fields": [],
                "resolved_fields": [],
                "blocking_fields": [],
                "provenance_blockers": [],
                "selection_identity": _concrete_selection_identity(context),
            },
            "formal_readiness_gate": {
                "state": "NOT_APPLICABLE",
                "required_fields": [],
                "blocking_fields": [],
                "model_status": _model_status(context),
            },
            "program_generated": True,
            "manual_postprocessing": False,
            "record_kind": context.get("record_kind", "equipment"),
            **_customer_row_source_binding(context),
            "source_input_sha256": context.get("input_sha256"),
            "authority_row_sha256": row_hash,
            "all_equipment_fields_sha256": all_equipment_fields_sha256,
            "all_equipment_fields": all_equipment_fields,
        }
    identity_text = " ".join(str(value) for value in [
        *context.get("values", {}).values(),
        context.get("model", {}).get("recommended_type"),
        context.get("family_name"),
    ] if _present(value)).casefold()
    scored: list[tuple[int, str, Mapping[str, Any]]] = []
    for candidate in candidates:
        tokens = [str(item).casefold() for item in candidate.get("subfamily_ids", []) if _present(item)]
        score = sum(1 for item in tokens if item in identity_text)
        table_id = str(candidate.get("authority_section_id"))
        if len(candidates) > 1 and score == 0:
            if "family_storage_vessel" in context.get("family_ids", []) and table_id == "T09":
                score = 1
            elif "family_reactor_vessel_separator" in context.get("family_ids", []) and table_id == "T13":
                score = 1
        scored.append((score, table_id, candidate))
    profile = sorted(scored, key=lambda item: (-item[0], item[1]))[0][2]
    cell_by_id = {str(cell.get("field_id")): cell for cell in cells}
    authority_cells: list[dict[str, Any]] = []
    missing: list[str] = []
    for index, column in enumerate(profile.get("authority_overview_columns", [])):
        field_id = str(column.get("field_id"))
        source = copy.deepcopy(cell_by_id.get(field_id) or _field_cell(
            column,
            context,
            evidence_ids=evidence_ids,
            evidence_level=evidence_level,
            missing_information=missing_information,
        ))
        # A unioned family card may contain an empty canonical placeholder even
        # when the authority column declares a usable alias (for example,
        # shell_material_grade <- material).  Re-evaluate the authority column
        # before treating that placeholder as a real gap.
        if str(source.get("state") or "") in UNRESOLVED_AUTHORITY_CELL_STATES:
            alias_source = _field_cell(
                column,
                context,
                evidence_ids=evidence_ids,
                evidence_level=evidence_level,
                missing_information=missing_information,
            )
            if (
                str(alias_source.get("state") or "")
                not in UNRESOLVED_AUTHORITY_CELL_STATES
                or str(
                    alias_source.get("source", {}).get("reason_code")
                    if isinstance(alias_source.get("source"), Mapping)
                    else ""
                )
                == (
                    "FORMAL_GEOMETRY_NOT_AVAILABLE_"
                    "SCREENING_ALIAS_REJECTED"
                )
            ):
                source = copy.deepcopy(alias_source)
        if str(source.get("state") or "") in UNRESOLVED_AUTHORITY_CELL_STATES:
            if field_id in {"equipment_type", "tower_internal_type"} and _present(context.get("model", {}).get("recommended_type")):
                source.update({
                    "value": context["model"]["recommended_type"],
                    "state": "DETERMINISTIC_TERMINAL_TYPE",
                    "source_field_id": "model_recommendation.recommended_type",
                    "source": {"kind": "deterministic_terminal_selection"},
                })
            elif field_id == "equipment_name":
                tag = context.get("equipment_tag") or context.get("equipment_key")
                source.update({
                    "value": f"{profile.get('title') or context.get('family_name') or '设备'}（{tag}）",
                    "state": "DEFAULTED_DISPLAY_IDENTITY",
                    "source_field_id": None,
                    "source": {
                        "kind": "registered_display_fallback",
                        "evidence_class": "J",
                        "warning": "项目未提供设备名称，按3-2表类别和位号生成显示名称。",
                    },
                })
            elif field_id == "quantity_count":
                tag_text = str(context.get("equipment_tag") or "").upper()
                source = _explicit_open_gate_cell(
                    column,
                    {
                        **source,
                        "value": None,
                        "state": "MISSING",
                        "source_field_id": None,
                        "source": {
                            "kind": "not_available",
                            "evidence_class": "U",
                            "reason_code": (
                                "PROJECT_INSTALLED_AND_STANDBY_QUANTITY_OPEN"
                            ),
                            "reason": (
                                "The Aspen object/tag count does not establish "
                                "project installed, operating, or standby "
                                "quantity."
                            ),
                            "required_action": (
                                "Confirm installed quantity and standby "
                                "philosophy from the project equipment list."
                            ),
                            "observed_equipment_tag": tag_text or None,
                            "aspen_row_object_count": (
                                1
                                if isinstance(
                                    context.get("aspen_source_binding"),
                                    Mapping,
                                )
                                and context.get("aspen_source_binding")
                                else None
                            ),
                        },
                    },
                )
            elif field_id in {"operating_state", "operating_mode"} and profile.get("authority_section_id") == "T01":
                source = _explicit_open_gate_cell(
                    column,
                    {
                        **source,
                        "value": None,
                        "state": "MISSING",
                        "source_field_id": None,
                        "source": {
                            "kind": "not_available",
                            "evidence_class": "U",
                            "reason_code": (
                                "PUMP_OPERATING_DUTY_CONFIGURATION_OPEN"
                            ),
                            "reason": (
                                "Aspen steady-state simulation does not prove "
                                "continuous/intermittent duty or single/parallel "
                                "pump operation."
                            ),
                            "required_action": (
                                "Confirm pump duty cycle, operating arrangement, "
                                "and reliability philosophy from project "
                                "requirements."
                            ),
                        },
                    },
                )
            elif (
                profile.get("authority_section_id") == "X05"
                and field_id in {
                    "dn_nps", "pressure_temperature_rating", "body_material_grade",
                    "internals_material_grade", "seat_material_grade", "connection_type",
                    "leakage_class", "actuator_type", "fail_position",
                    "operating_range_and_rangeability", "flashing_check_ref",
                    "cavitation_check_ref", "noise_check_ref", "vendor_datasheet_ref",
                }
            ):
                material_cell = _source_cell("material", context)
                pressure_class_cell = _source_cell("pressure_class", context)
                design_temperature_cell = _source_cell("design_temperature_c", context)
                cv_cell = _source_cell("cv", context)
                if field_id == "dn_nps":
                    selected_dn = _source_cell("selected_dn", context)
                    if selected_dn is not None:
                        source.update({
                            "value": selected_dn["value"],
                            "state": selected_dn["state"],
                            "source_field_id": "selected_dn",
                            "source": selected_dn["source"],
                        })
                elif field_id == "pressure_temperature_rating":
                    pressure_class = pressure_class_cell["value"] if pressure_class_cell else "PN16"
                    design_temperature = (
                        f"，Tdes={design_temperature_cell['value']:g} °C"
                        if design_temperature_cell and isinstance(design_temperature_cell.get("value"), (int, float))
                        else ""
                    )
                    source.update({
                        "value": f"{pressure_class} 初选{design_temperature}；材料压力-温度额定值待产品标准复核",
                        "state": "DEFAULTED_PRELIMINARY_RATING",
                        "source_field_id": "pressure_class+design_temperature_c",
                        "source": {
                            "kind": "registered_3_2_valve_preliminary_fallback",
                            "evidence_class": "J",
                            "warning": "压力等级已用于预选展示，不表示具体阀体材料的压力-温度额定值已正式通过。",
                        },
                    })
                elif field_id in {"body_material_grade", "internals_material_grade", "seat_material_grade"}:
                    base_material = material_cell["value"] if material_cell else "碳钢预选"
                    suffix = {
                        "body_material_grade": "阀体",
                        "internals_material_grade": "内件",
                        "seat_material_grade": "阀座",
                    }[field_id]
                    source.update({
                        "value": f"{base_material}（{suffix}预选；耐蚀/冲蚀/密封复核待完成）",
                        "state": "DEFAULTED_PRELIMINARY_MATERIAL_ROUTE",
                        "source_field_id": "material" if material_cell else None,
                        "source": {
                            "kind": "registered_3_2_valve_preliminary_fallback",
                            "evidence_class": "J",
                            "warning": "预选材料不替代介质腐蚀、温度、冲蚀及阀内件配副审查。",
                        },
                    })
                elif field_id == "connection_type":
                    source.update({
                        "value": "法兰连接、RF 密封面（预选）",
                        "state": "DEFAULTED",
                        "source_field_id": None,
                        "source": {
                            "kind": "registered_3_2_valve_preliminary_fallback",
                            "evidence_class": "J",
                            "warning": "端连接须与管线等级、口径和压力等级复核。",
                        },
                    })
                elif field_id == "leakage_class":
                    source.update({
                        "value": "ANSI/FCI 70-2 Class IV（单座调节阀预选）",
                        "state": "DEFAULTED",
                        "source_field_id": "valve_function",
                        "source": {
                            "kind": "registered_3_2_valve_preliminary_fallback",
                            "evidence_class": "J",
                            "warning": "泄漏等级须由关断要求和阀座结构确认。",
                        },
                    })
                elif field_id == "actuator_type":
                    source.update({
                        "value": "气动薄膜执行机构（预选）",
                        "state": "DEFAULTED",
                        "source_field_id": "valve_function",
                        "source": {
                            "kind": "registered_3_2_valve_preliminary_fallback",
                            "evidence_class": "J",
                            "warning": "执行机构推力、气源和附件仍需按最大压差及控制要求校核。",
                        },
                    })
                elif field_id == "fail_position":
                    source.update({
                        "value": "FC（故障关，预选）",
                        "state": "DEFAULTED_SAFETY_REVIEW_REQUIRED",
                        "source_field_id": "valve_function",
                        "source": {
                            "kind": "registered_3_2_valve_preliminary_fallback",
                            "evidence_class": "J",
                            "warning": "FC 仅为不中停预选；必须由控制因果表、联锁和 HAZOP 决定 FC/FO/FL。",
                        },
                    })
                elif field_id == "operating_range_and_rangeability":
                    source.update({
                        "value": {
                            "normal_cv": cv_cell["value"] if cv_cell else None,
                            "preliminary_rangeability": "50:1",
                            "status": "TYPE_SCREENING_ONLY",
                        },
                        "state": "DEFAULTED_PRELIMINARY_OPERATING_RANGE",
                        "source_field_id": "cv" if cv_cell else None,
                        "source": {
                            "kind": "registered_3_2_valve_preliminary_fallback",
                            "evidence_class": "J",
                            "warning": "可调比须用最小/正常/最大流量点和厂家特性曲线复核。",
                        },
                    })
                elif field_id in {"flashing_check_ref", "cavitation_check_ref", "noise_check_ref", "vendor_datasheet_ref"}:
                    gate_text = {
                        "flashing_check_ref": "待按同工况饱和蒸汽压与出口压力完成闪蒸校核",
                        "cavitation_check_ref": "待按同工况压力恢复系数与饱和蒸汽压完成空化校核",
                        "noise_check_ref": "待按同工况压差、流量及厂家/适用标准完成噪声校核",
                        "vendor_datasheet_ref": "待取得同工况厂家阀门数据表并回写哈希证据",
                    }[field_id]
                    source.update({
                        "value": gate_text,
                        "state": "OPEN_FORMAL_EVIDENCE_GATE",
                        "source_field_id": None,
                        "source": {
                            "kind": "registered_formal_evidence_gate",
                            "evidence_class": "U",
                            "warning": "该字段已给出明确待办，不得解释为校核通过或厂家型号已确认。",
                        },
                    })
            elif field_id == "technical_specification":
                diameter = _source_cell("diameter_mm", context)
                length = next((
                    _source_cell(candidate, context)
                    for candidate in ("height_mm", "length_mm", "height_or_length_mm")
                    if _source_cell(candidate, context) is not None
                ), None)
                if diameter is not None and length is not None:
                    source.update({
                        "value": f"φ{diameter['value']:g}×{length['value']:g}",
                        "unit": "mm",
                        "state": "COMPOSED_FROM_DETERMINISTIC_GEOMETRY",
                        "source_field_id": "diameter_mm+height_or_length_mm",
                        "source": {"kind": "deterministic_display_composition", "evidence_class": "D"},
                    })
                else:
                    model_value, model_state = _model_value(context)
                    if _present(model_value):
                        source.update({
                            "value": model_value,
                            "unit": None,
                            "state": "PRELIMINARY_TYPE_SPECIFICATION",
                            "source_field_id": "model_or_specification",
                            "source": {
                                "kind": "deterministic_model_recommendation",
                                "evidence_class": "J",
                                "model_state": model_state,
                                "promotion_cap": "TYPE_SCREENING",
                                "warning": "几何尺寸未闭合；本字段仅复用可追溯的预设计型式/规格，不表示机械设计完成。",
                            },
                        })
            elif field_id == "standard_identity":
                _adopted, routes = _standards(context)
                if routes:
                    source.update({
                        "value": [
                            {
                                "number": item.get("number"),
                                "title": item.get("title"),
                                "state": "CONDITIONAL_STANDARD_CANDIDATE",
                                "reuse_class": item.get("reuse_class"),
                            }
                            for item in routes
                        ],
                        "state": "CONDITIONALLY_MATCHED_STANDARD",
                        "source_field_id": "standard_routes",
                        "source": {
                            "kind": "deterministic_standard_route",
                            "warning": "国标候选已用于预选展示；正式采用仍需同设备适用性复核。",
                        },
                    })
        if str(source.get("state") or "") == EXPLICIT_OPEN_GATE_STATE:
            source = _ensure_open_gate_metadata(column, source)
        transform = column.get("value_transform")
        fallback_transform = column.get("fallback_transform")
        numeric = source.get("value")
        if isinstance(numeric, (int, float)) and not isinstance(numeric, bool):
            applied = transform
            if fallback_transform and source.get("source_field_id") in {"height_mm", "length_mm", "height_or_length_mm"}:
                applied = fallback_transform
            if applied == "mpa_to_bar":
                source["value"] = float(numeric) * 10.0
            elif applied == "m3_h_to_m3_min":
                source["value"] = float(numeric) / 60.0
            elif applied == "mm_to_m":
                source["value"] = float(numeric) / 1000.0
            if applied:
                source["source"] = {
                    **dict(source.get("source", {})),
                    "authority_unit_transform": applied,
                }
        source["label"] = column.get("label") or source.get("label") or field_id
        source["unit"] = column.get("unit", source.get("unit"))
        source["authority_column_index"] = index
        source["authority_table_id"] = profile.get("authority_section_id")
        source["selection_impact"] = column.get("selection_impact")
        source["evidence_gate"] = column.get("evidence_gate") or column.get("source_gate")
        source["program_generated"] = True
        source["manual_postprocessing"] = False
        _annotate_provenance(source)
        _compact_cell_source_binding(source, context)
        source.update(_customer_cell_source_binding(context))
        source["cell_sha256"] = _sha256_json({
            "input_sha256": context.get("input_sha256"),
            "record_kind": context.get("record_kind"),
            "authority_table_id": profile.get("authority_section_id"),
            "authority_column_index": index,
            "field_id": field_id,
            "value": source.get("value"),
            "display_value": source.get("display_value"),
            "unit": source.get("unit"),
            "state": source.get("state"),
            "promotion_cap": source.get("promotion_cap"),
            "open_gate": source.get("open_gate"),
            "source_field_id": source.get("source_field_id"),
            "source": source.get("source"),
            "source_chain_binding_sha256": source.get(
                "source_chain_binding_sha256"
            ),
            "derivation_record_kind": source.get(
                "derivation_record_kind"
            ),
            "derivation_record_identity": source.get(
                "derivation_record_identity"
            ),
            "program_generated_record_sha256": source.get(
                "program_generated_record_sha256"
            ),
            "program_generated_record_binding_sha256": source.get(
                "program_generated_record_binding_sha256"
            ),
        })
        authority_cells.append(_json_safe(source))
        if str(source.get("state") or "") in UNRESOLVED_AUTHORITY_CELL_STATES:
            missing.append(field_id)
    required = len(authority_cells)
    populated = sum(
        1
        for cell in authority_cells
        if (
            _present(cell.get("value"))
            or _present(cell.get("display_value"))
            or str(cell.get("state") or "") in {"NOT_APPLICABLE", "NONE"}
        )
    )
    expected_field_ids = [
        str(column.get("field_id"))
        for column in profile.get("authority_overview_columns", [])
    ]
    emitted_field_ids = [str(cell.get("field_id")) for cell in authority_cells]
    structural_blockers: list[str] = []
    if emitted_field_ids != expected_field_ids:
        structural_blockers.append("AUTHORITY_COLUMN_ORDER_OR_ID_MISMATCH")
    if len(set(emitted_field_ids)) != len(emitted_field_ids):
        structural_blockers.append("DUPLICATE_AUTHORITY_FIELD_ID")
    if not all(
        cell.get("program_generated") is True
        and cell.get("manual_postprocessing") is False
        and _present(cell.get("cell_sha256"))
        for cell in authority_cells
    ):
        structural_blockers.append("UNBOUND_OR_NONPROGRAM_AUTHORITY_CELL")
    authority_full_field_coverage = _customer_full_field_coverage(
        profile.get("authority_overview_columns", []),
        authority_cells,
    )
    cells_by_id = {str(cell.get("field_id")): cell for cell in authority_cells}
    information_blockers = [
        field_id
        for field_id in expected_field_ids
        if (
            not _present(cells_by_id.get(field_id, {}).get("value"))
            or str(cells_by_id.get(field_id, {}).get("state") or "")
            in UNRESOLVED_AUTHORITY_CELL_STATES
        )
    ]
    explicit_open_gate_fields = [
        field_id
        for field_id in expected_field_ids
        if (
            str(cells_by_id.get(field_id, {}).get("state") or "")
            == "OPEN_FORMAL_EVIDENCE_GATE"
            and (
                _present(cells_by_id.get(field_id, {}).get("value"))
                or _present(
                    cells_by_id.get(field_id, {}).get("display_value")
                )
            )
        )
    ]
    information_state = (
        "BLOCKED"
        if structural_blockers
        else "PROVISIONAL_WITH_OPEN_GAPS"
        if information_blockers or customer_table_open_gate_fields
        else "PASS"
    )
    specificity_required = [
        str(column.get("field_id"))
        for column in profile.get("authority_overview_columns", [])
        if str(column.get("requirement", "required")) not in {"optional", "informational"}
        and str(column.get("selection_impact") or "") in SPECIFIC_SELECTION_IMPACTS
    ]
    def preliminary_specificity_resolved(field_id: str) -> bool:
        cell = cells_by_id.get(field_id, {})
        return (
            _selection_impact_cell_resolved(cell)
            or _programmatic_valve_preliminary_gate_resolved(
                field_id,
                cell,
                context,
            )
        )

    specificity_blockers = [
        field_id
        for field_id in specificity_required
        if not preliminary_specificity_resolved(field_id)
    ]
    specificity_provenance_blockers = [
        {
            "field_id": field_id,
            "provenance_origin": cells_by_id.get(field_id, {}).get(
                "provenance_origin"
            ),
        }
        for field_id in specificity_required
        if (
            _authority_cell_resolved(cells_by_id.get(field_id, {}))
            and str(
                cells_by_id.get(field_id, {}).get("provenance_origin") or ""
            )
            not in ENGINEERING_PROVENANCE_ORIGINS
            and not _programmatic_valve_preliminary_gate_resolved(
                field_id,
                cells_by_id.get(field_id, {}),
                context,
            )
        )
    ]
    selection_identity = _concrete_selection_identity(context)
    identity_blockers: list[str] = []
    if not selection_identity["concrete_terminal_type"]:
        identity_blockers.append("CONCRETE_TERMINAL_TYPE_NOT_ESTABLISHED")
    if not selection_identity["detailed_designation"]:
        identity_blockers.append("DETAILED_MODEL_OR_ENGINEERING_DESIGNATION_NOT_ESTABLISHED")
        identity_blockers.extend(
            f"DESIGNATION_DETAIL:{item}"
            for item in selection_identity.get(
                "designation_detail_blockers", []
            )
        )
    identity_blockers.extend(
        f"CANDIDATE_AUDIT:{item}"
        for item in selection_identity.get(
            "candidate_validation_blockers", []
        )
    )
    identity_blockers.extend(
        "SELECTION_FIELD_PROVENANCE:"
        f"{item['field_id']}:{item['provenance_origin']}"
        for item in specificity_provenance_blockers
    )
    identity_blockers = sorted(set(identity_blockers))
    specificity_state = (
        "PASS"
        if not specificity_blockers and not identity_blockers and not structural_blockers
        else "BLOCKED"
    )
    formal_required = [
        str(column.get("field_id"))
        for column in profile.get("authority_overview_columns", [])
        if str(column.get("requirement", "required")) not in {"optional", "informational"}
    ]
    formal_blockers = [
        field_id
        for field_id in formal_required
        if (
            not _selection_impact_cell_resolved(
                cells_by_id.get(field_id, {})
            )
            if field_id in specificity_required
            else not _authority_cell_resolved(cells_by_id.get(field_id, {}))
        )
    ]
    model_status = _model_status(context)
    formal_gate_blockers = list(formal_blockers)
    if model_status != "final_model":
        formal_gate_blockers.append("FORMAL_MODEL_NOT_ESTABLISHED")
    if specificity_state != "PASS":
        formal_gate_blockers.append("SPECIFIC_SELECTION_GATE_NOT_PASSED")
    merged_cells_by_id = {
        str(cell.get("field_id")): dict(cell) for cell in cells
    }
    for authority_cell in authority_cells:
        merged_cells_by_id[str(authority_cell.get("field_id"))] = dict(
            authority_cell
        )
    all_equipment_fields = _bind_delivery_cells(
        list(merged_cells_by_id.values()),
        context,
        scope="all_equipment_fields",
    )
    all_equipment_fields_sha256 = _sha256_json([
        cell.get("cell_sha256") for cell in all_equipment_fields
    ])
    row_hash = _sha256_json({
        "input_sha256": context.get("input_sha256"),
        "record_kind": context.get("record_kind"),
        "aspen_source_binding": context.get("aspen_source_binding", {}),
        "authority_table_id": profile.get("authority_section_id"),
        "authority_source": profiles.get("minimum_output_authority", {}),
        "authority_cell_hashes": [cell.get("cell_sha256") for cell in authority_cells],
        "all_equipment_fields_sha256": all_equipment_fields_sha256,
        "information_coverage_state": information_state,
        "customer_information_state": customer_information_state,
        "authority_full_field_coverage_state": (
            authority_full_field_coverage.get("state")
        ),
        "specificity_state": specificity_state,
        "formal_gate_blockers": sorted(set(formal_gate_blockers)),
    })
    return {
        "authority_table_id": profile.get("authority_section_id"),
        "authority_table_title": profile.get("title"),
        "authority_source": _json_safe(profiles.get("minimum_output_authority", {})),
        "authority_columns": _json_safe(profile.get("authority_overview_columns", [])),
        "authority_cells": authority_cells,
        "authority_missing_fields": missing,
        "authority_completeness": {
            "required": required,
            "populated": populated,
            "formally_open": len(missing),
            "state": (
                "COMPLETE"
                if not missing and populated == required
                else "COMPLETE_WITH_EXPLICIT_OPEN_GATES"
                if populated == required
                else "PROVISIONAL_WITH_VISIBLE_GAPS"
            ),
        },
        "authority_structural_completeness": {
            "required": len(expected_field_ids),
            "emitted": len(emitted_field_ids),
            "unique": len(set(emitted_field_ids)),
            "blocking_reasons": structural_blockers,
            "state": "PASS" if not structural_blockers else "BLOCKED",
        },
        "authority_full_field_coverage": authority_full_field_coverage,
        "authority_information_coverage": {
            "required": len(expected_field_ids),
            "covered": len(expected_field_ids) - len(information_blockers),
            "blocking_fields": information_blockers,
            "explicit_open_gate_fields": explicit_open_gate_fields,
            "customer_table_open_gate_fields": (
                customer_table_open_gate_fields
            ),
            "state": information_state,
        },
        "customer_information_coverage": {
            "state": customer_information_state,
            "blocking_fields": customer_information_blockers,
            "open_gate_fields": customer_table_open_gate_fields,
        },
        "selection_specificity_gate": {
            "state": specificity_state,
            "required_fields": specificity_required,
            "resolved_fields": sorted(set(specificity_required) - set(specificity_blockers)),
            "blocking_fields": specificity_blockers,
            "provenance_blockers": specificity_provenance_blockers,
            "blocking_reasons": identity_blockers,
            "selection_identity": selection_identity,
        },
        "formal_readiness_gate": {
            "state": "PASS" if not formal_gate_blockers else "BLOCKED",
            "required_fields": formal_required,
            "blocking_fields": formal_blockers,
            "blocking_reasons": sorted(set(formal_gate_blockers) - set(formal_blockers)),
            "model_status": model_status,
        },
        "program_generated": True,
        "manual_postprocessing": False,
        "record_kind": context.get("record_kind", "equipment"),
        **_customer_row_source_binding(context),
        "source_input_sha256": context.get("input_sha256"),
        "authority_row_sha256": row_hash,
        "all_equipment_fields_sha256": all_equipment_fields_sha256,
        "all_equipment_fields": all_equipment_fields,
    }


def _build_from_contexts(contexts: Sequence[Mapping[str, Any]], profiles: Mapping[str, Any]) -> dict[str, Any]:
    evidence_by_key: dict[str, list[dict[str, Any]]] = {}
    for context in contexts:
        bound_records: list[dict[str, Any]] = []
        for raw_record in _evidence_records(context):
            record = {
                **dict(raw_record),
                "record_kind": context.get("record_kind"),
                "source_input_sha256": context.get("input_sha256"),
                **_customer_row_source_binding(context),
                "program_generated": True,
                "manual_postprocessing": False,
            }
            record["record_sha256"] = _sha256_json(record)
            bound_records.append(_json_safe(record))
        evidence_by_key[context["equipment_key"]] = bound_records
    datasheets: list[dict[str, Any]] = []
    overview_rows: list[dict[str, Any]] = []
    for context in contexts:
        selected = _selected_profiles(context, profiles)
        fields = _union_fields(selected)
        evidence_records = evidence_by_key[context["equipment_key"]]
        evidence_ids = sorted(
            str(record["evidence_id"]) for record in evidence_records if _present(record.get("evidence_id"))
        )
        level = _evidence_level(context, evidence_records)
        provisional_cells = [
            _field_cell(field, context, evidence_ids=evidence_ids, evidence_level=level)
            for field in fields
        ]
        customer_table_missing = _customer_table_missing(fields, provisional_cells)
        missing = _missing_union(context, fields, provisional_cells)
        algorithm_evidence_missing = sorted(set(missing) - set(customer_table_missing))
        cells = _bind_delivery_cells(
            [
                _field_cell(
                    field,
                    context,
                    evidence_ids=evidence_ids,
                    evidence_level=level,
                    missing_information=missing,
                )
                for field in fields
            ],
            context,
            scope="family_datasheet_fields",
        )
        customer_full_field_coverage = _customer_full_field_coverage(
            fields,
            cells,
        )
        cell_by_id = {cell["field_id"]: cell for cell in cells}
        authority_overview = _authority_overview_projection(
            selected,
            cells,
            profiles,
            context,
            evidence_ids=evidence_ids,
            evidence_level=level,
            missing_information=missing,
            customer_table_missing_fields=customer_table_missing,
        )
        adopted, routes = _standards(context)
        model_value, _ = _model_value(context)
        model_status = _model_status(context)
        terminal_selection = context["model"].get("terminal_selection", {})
        if not isinstance(terminal_selection, Mapping):
            terminal_selection = {}
        service_profile = context.get("service_profile", {})
        service_labels = {
            str(item.get("label_id")): item.get("value")
            for item in service_profile.get("service_labels", [])
            if isinstance(service_profile, Mapping)
            and isinstance(item, Mapping)
            and str(item.get("label_id") or "") in {
                "module.intent", "observed.operation.pressure_direction",
                "observed.operation.heat_transfer_mode", "process.phase_set",
                "process.phase_change", "service.corrosive", "safety.toxic",
                "safety.flammable", "safety.explosive", "safety.oxidizing",
            }
        } if isinstance(service_profile, Mapping) else {}
        service_diagnostics = [
            str(item.get("code"))
            for item in service_profile.get("diagnostics", [])
            if isinstance(service_profile, Mapping) and isinstance(item, Mapping) and item.get("code")
        ] if isinstance(service_profile, Mapping) else []
        connection_package = context.get("connection_component_selections", {})
        adjustment_plan = context.get(
            "engineering_adjustment_plan", {}
        )
        adjustment_status = (
            adjustment_plan.get("status")
            if isinstance(adjustment_plan, Mapping)
            else None
        )
        algorithmic_warning = (
            adjustment_plan.get("algorithmic_selection_warning")
            if isinstance(adjustment_plan, Mapping)
            else None
        )
        agent_control = context.get(
            "selection_agent_control", {}
        )
        agent_control_status = (
            agent_control.get("status")
            if isinstance(agent_control, Mapping)
            else None
        )
        delivery_state = (
            "READY"
            if authority_overview.get("formal_readiness_gate", {}).get("state") == "PASS"
            else "NOT_READY"
        )
        datasheet = {
            "equipment_key": context["equipment_key"],
            "equipment_tag": context.get("equipment_tag"),
            "record_kind": context.get("record_kind"),
            "family_ids": context["family_ids"],
            "family_name": context.get("family_name"),
            "profile_ids": [item["profile_id"] for item in selected],
            "profile_resolution": "EXACT_OR_BASE" if len(selected) <= 1 else "MOST_GENERAL_PROFILE_UNION",
            "fields": cells,
            "customer_full_field_coverage": customer_full_field_coverage,
            "customer_table_missing_fields": customer_table_missing,
            "algorithm_evidence_missing_fields": algorithm_evidence_missing,
            "missing_information": missing,
            "evidence_ids": evidence_ids,
            "evidence_level": level,
            "terminal_selection_status": terminal_selection.get("status"),
            "terminal_selection_basis": terminal_selection.get("selection_basis"),
            "terminal_default_applied": bool(terminal_selection.get("default_applied", False)),
            "terminal_rule_id": terminal_selection.get("rule_id"),
            "terminal_assumption": terminal_selection.get("assumption"),
            "service_profile_context_sha256": service_profile.get("profile_context_sha256") if isinstance(service_profile, Mapping) else None,
            "automatic_service_summary": service_labels,
            "automatic_service_diagnostics": sorted(set(service_diagnostics)),
            "connection_selection_package_sha256": connection_package.get("selection_package_sha256") if isinstance(connection_package, Mapping) else None,
            "engineering_adjustment_status": adjustment_status,
            "engineering_adjustment_plan": _json_safe(
                adjustment_plan
            ),
            "algorithmic_selection_warning": algorithmic_warning,
            "selection_agent_control_status": agent_control_status,
            "selection_agent_control": _json_safe(agent_control),
            "llm_used": context["llm_used"],
            "model_estimate_disclosure": context["model_estimate_disclosure"],
            "input_sha256": context["input_sha256"],
            "source_input_sha256": context["input_sha256"],
            **_customer_row_source_binding(context),
            "program_generated": True,
            "manual_postprocessing": False,
        }
        datasheet["datasheet_sha256"] = _sha256_json({
            "equipment_key": datasheet["equipment_key"],
            "record_kind": datasheet["record_kind"],
            "source_input_sha256": datasheet[
                "source_input_sha256"
            ],
            "source_chain_binding_sha256": datasheet[
                "source_chain_binding_sha256"
            ],
            "program_generated_record_sha256": datasheet[
                "program_generated_record_sha256"
            ],
            "field_hashes": [
                cell.get("cell_sha256") for cell in cells
            ],
        })
        datasheets.append(datasheet)
        overview_rows.append({
            "sequence_number": cell_by_id.get("sequence_number", {}).get("value"),
            "process_section": cell_by_id.get("process_section", {}).get("value"),
            "equipment_key": context["equipment_key"],
            "equipment_tag": context.get("equipment_tag"),
            "equipment_name": cell_by_id.get("equipment_name", {}).get("value"),
            "equipment_drawing_number": cell_by_id.get("equipment_drawing_number", {}).get("value"),
            "total_mass_kg": cell_by_id.get("total_mass_kg", {}).get("value"),
            "family_ids": context["family_ids"],
            "family_name": context.get("family_name"),
            "equipment_type": (
                cell_by_id.get("equipment_type", {}).get("value")
                or context.get("model", {}).get("recommended_type")
            ),
            "model_or_specification": model_value,
            "model_or_specification_status": model_status,
            "engineering_adjustment_status": adjustment_status,
            "engineering_adjustment_plan": _json_safe(
                adjustment_plan
            ),
            "algorithmic_selection_warning": algorithmic_warning,
            "selection_agent_control_status": agent_control_status,
            "terminal_selection_status": terminal_selection.get("status"),
            "terminal_selection_basis": terminal_selection.get("selection_basis"),
            "terminal_default_applied": bool(terminal_selection.get("default_applied", False)),
            "terminal_rule_id": terminal_selection.get("rule_id"),
            "terminal_assumption": terminal_selection.get("assumption"),
            "standards_and_versions": adopted,
            "standards_and_versions_state": "EXPLICIT" if adopted else "NOT_EXPLICITLY_ADOPTED",
            "standard_reference_routes": routes,
            "evidence_ids": evidence_ids,
            "customer_table_missing_fields": customer_table_missing,
            "customer_full_field_coverage": (
                customer_full_field_coverage
            ),
            "customer_information_coverage": {
                "state": "PASS" if not customer_table_missing else "BLOCKED",
                "blocking_fields": customer_table_missing,
            },
            "quantity_and_standby": cell_by_id.get(
                "quantity_and_standby", {}
            ).get("value"),
            "algorithm_evidence_missing_fields": algorithm_evidence_missing,
            "missing_information": missing,
            "evidence_level": level,
            "delivery_state": delivery_state,
            "profile_ids": [item["profile_id"] for item in selected],
            "llm_used": context["llm_used"],
            "model_estimate_disclosure": context["model_estimate_disclosure"],
            **authority_overview,
        })
    datasheets.sort(key=lambda item: (str(item.get("equipment_tag") or item["equipment_key"]).casefold(), item["equipment_key"]))
    overview_rows.sort(key=lambda item: (str(item.get("equipment_tag") or item["equipment_key"]).casefold(), item["equipment_key"]))
    evidence_records = [
        record
        for context in contexts
        for record in evidence_by_key[context["equipment_key"]]
    ]
    evidence_records.sort(key=lambda item: (
        str(item.get("equipment_key") or "").casefold(), str(item.get("evidence_kind") or ""),
        str(item.get("record_id") or ""),
    ))
    datasheet_hashes = [
        str(item.get("datasheet_sha256") or "")
        for item in datasheets
    ]
    evidence_record_hashes = [
        str(item.get("record_sha256") or "")
        for item in evidence_records
    ]
    profile_meta = {
        "schema": profiles.get("schema"), "version": profiles.get("version"),
        "source": profiles.get("source"), "fallback": profiles.get("fallback", False),
    }
    llm_used = any(bool(context.get("llm_used")) for context in contexts)
    model_estimate_disclosure = {
        "llm_used": llm_used,
        "status": "PROVISIONAL_ESTIMATES_USED" if any(
            context.get("model_estimate_disclosure", {}).get("applied_model_estimate_fields")
            for context in contexts
        ) else (
            "MODEL_ESTIMATES_SUPERSEDED" if any(
                context.get("model_estimate_disclosure", {}).get("superseded_model_estimate_fields")
                for context in contexts
            ) else "NOT_USED"
        ),
        "equipment": [
            {
                "equipment_key": context["equipment_key"],
                **context["model_estimate_disclosure"],
            }
            for context in contexts
            if context.get("model_estimate_disclosure", {}).get("model_estimate_fields")
        ],
        "statement": (
            "交付内容含已披露的大模型 J/provisional 工程估算；仅限 TYPE_SCREENING，正式选型前必须替换并重算。"
            if llm_used
            else "交付内容未使用大模型工程估算。"
        ),
    }
    overview_table_sha256 = _sha256_json({
        "schema": "equipment-overview-table-v1",
        "authority_contract": str(
            profiles.get("minimum_output_authority", {}).get("schema")
            or "3-2-equipment-selection-overview-v1"
        ),
        "columns": list(OVERVIEW_COLUMNS),
        "profile_authority": profile_meta,
        "row_hashes": [row.get("authority_row_sha256") for row in overview_rows],
        "record_kinds": [row.get("record_kind") for row in overview_rows],
    })
    return {
        "equipment_overview_table": {
            "schema": "equipment-overview-table-v1",
            "authority_contract": str(
                profiles.get("minimum_output_authority", {}).get("schema")
                or "3-2-equipment-selection-overview-v1"
            ),
            "columns": list(OVERVIEW_COLUMNS),
            "row_count": len(overview_rows),
            "rows": overview_rows,
            "profile_authority": profile_meta,
            "deterministic": True,
            "program_generated": True,
            "manual_postprocessing": False,
            "table_sha256": overview_table_sha256,
            "row_hashes": [row.get("authority_row_sha256") for row in overview_rows],
            "llm_used": llm_used,
            "model_estimate_disclosure": model_estimate_disclosure,
        },
        "equipment_family_datasheet": {
            "schema": "equipment-family-datasheet-v1",
            "equipment_count": len(datasheets),
            "equipment": datasheets,
            "datasheet_hashes": datasheet_hashes,
            "datasheet_set_sha256": _sha256_json({
                "schema": "equipment-family-datasheet-v1",
                "equipment_count": len(datasheets),
                "datasheet_hashes": datasheet_hashes,
            }),
            "profile_authority": profile_meta,
            "deterministic": True,
            "llm_used": llm_used,
            "model_estimate_disclosure": model_estimate_disclosure,
        },
        "equipment_evidence_index": {
            "schema": "equipment-evidence-index-v1",
            "equipment_count": len(contexts),
            "record_count": len(evidence_records),
            "records": evidence_records,
            "record_hashes": evidence_record_hashes,
            "index_sha256": _sha256_json({
                "schema": "equipment-evidence-index-v1",
                "equipment_count": len(contexts),
                "record_count": len(evidence_records),
                "record_hashes": evidence_record_hashes,
            }),
            "deterministic": True,
            "llm_used": llm_used,
            "model_estimate_disclosure": model_estimate_disclosure,
        },
    }


def _delivery_cell_expected_sha256(
    cell: Mapping[str, Any],
    *,
    source_input_sha256: Any,
    record_kind: Any,
) -> str:
    return _sha256_json({
        "input_sha256": source_input_sha256,
        "record_kind": record_kind,
        "delivery_scope": cell.get("delivery_scope"),
        "delivery_field_index": cell.get("delivery_field_index"),
        "field_id": cell.get("field_id"),
        "value": cell.get("value"),
        "display_value": cell.get("display_value"),
        "unit": cell.get("unit"),
        "state": cell.get("state"),
        "promotion_cap": cell.get("promotion_cap"),
        "open_gate": cell.get("open_gate"),
        "source_field_id": cell.get("source_field_id"),
        "source": cell.get("source"),
        "requirement": cell.get("requirement"),
        "evidence_gate": cell.get("evidence_gate"),
        "source_refs": cell.get("source_refs", []),
        "profile_ids": cell.get("profile_ids", []),
        "source_chain_binding_sha256": cell.get(
            "source_chain_binding_sha256"
        ),
        "derivation_record_kind": cell.get(
            "derivation_record_kind"
        ),
        "derivation_record_identity": cell.get(
            "derivation_record_identity"
        ),
        "program_generated_record_sha256": cell.get(
            "program_generated_record_sha256"
        ),
        "program_generated_record_binding_sha256": cell.get(
            "program_generated_record_binding_sha256"
        ),
    })


def _authority_cell_expected_sha256(
    cell: Mapping[str, Any],
    *,
    source_input_sha256: Any,
    record_kind: Any,
    authority_table_id: Any,
) -> str:
    return _sha256_json({
        "input_sha256": source_input_sha256,
        "record_kind": record_kind,
        "authority_table_id": authority_table_id,
        "authority_column_index": cell.get(
            "authority_column_index"
        ),
        "field_id": cell.get("field_id"),
        "value": cell.get("value"),
        "display_value": cell.get("display_value"),
        "unit": cell.get("unit"),
        "state": cell.get("state"),
        "promotion_cap": cell.get("promotion_cap"),
        "open_gate": cell.get("open_gate"),
        "source_field_id": cell.get("source_field_id"),
        "source": cell.get("source"),
        "source_chain_binding_sha256": cell.get(
            "source_chain_binding_sha256"
        ),
        "derivation_record_kind": cell.get(
            "derivation_record_kind"
        ),
        "derivation_record_identity": cell.get(
            "derivation_record_identity"
        ),
        "program_generated_record_sha256": cell.get(
            "program_generated_record_sha256"
        ),
        "program_generated_record_binding_sha256": cell.get(
            "program_generated_record_binding_sha256"
        ),
    })


def _source_binding_errors(
    value: Mapping[str, Any],
    *,
    location: str,
    expected_projection: Mapping[str, Any] | None = None,
    require_embedded_binding: bool = True,
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    raw_binding = value.get("source_chain_binding")
    has_embedded_binding = isinstance(raw_binding, Mapping)
    binding = dict(raw_binding) if has_embedded_binding else {}
    declared_binding_sha256 = str(
        value.get("source_chain_binding_sha256") or ""
    ).upper()
    projection_fields = (
        "derivation_record_kind",
        "derivation_record_identity",
        "program_generated_record_sha256",
        "program_generated_record_binding_sha256",
    )
    if has_embedded_binding:
        if declared_binding_sha256 != _sha256_json(binding):
            errors.append({
                "code": "SOURCE_CHAIN_BINDING_SHA256_MISMATCH",
                "location": location,
            })
        for field_id in projection_fields:
            if value.get(field_id) != binding.get(field_id):
                errors.append({
                    "code": "SOURCE_CHAIN_BINDING_PROJECTION_MISMATCH",
                    "location": location,
                    "field_id": field_id,
                })
    elif require_embedded_binding:
        errors.append({
            "code": "SOURCE_CHAIN_BINDING_MISSING",
            "location": location,
        })
    elif expected_projection is None:
        errors.append({
            "code": "SOURCE_CHAIN_BINDING_POINTER_REFERENCE_MISSING",
            "location": location,
        })
    else:
        expected_binding = (
            expected_projection.get("source_chain_binding")
            if isinstance(
                expected_projection.get("source_chain_binding"),
                Mapping,
            )
            else {}
        )
        binding = dict(expected_binding)
        if (
            declared_binding_sha256
            != str(
                expected_projection.get(
                    "source_chain_binding_sha256"
                )
                or ""
            ).upper()
        ):
            errors.append({
                "code": "SOURCE_CHAIN_BINDING_POINTER_SHA256_MISMATCH",
                "location": location,
            })
        for field_id in projection_fields:
            if (
                value.get(field_id)
                != expected_projection.get(field_id)
            ):
                errors.append({
                    "code": "SOURCE_CHAIN_BINDING_POINTER_PROJECTION_MISMATCH",
                    "location": location,
                    "field_id": field_id,
                })
    if binding.get("schema") == "aspen-equipment-derivation-result-v1":
        record_sha256 = str(
            value.get("program_generated_record_sha256") or ""
        ).upper()
        binding_sha256 = str(
            value.get("program_generated_record_binding_sha256")
            or ""
        ).upper()
        if (
            not _HASH_RE.fullmatch(record_sha256)
            or record_sha256 != binding_sha256
            or not _present(value.get("derivation_record_kind"))
            or not _present(value.get("derivation_record_identity"))
        ):
            errors.append({
                "code": "ASPEN_FINAL_ROW_BINDING_INVALID",
                "location": location,
            })
    return errors


def _cell_source_pointer_errors(
    value: Mapping[str, Any],
    *,
    expected_projection: Mapping[str, Any],
    location: str,
) -> list[dict[str, Any]]:
    """Verify that field provenance points to, but does not repeat, the row chain."""

    source = (
        value.get("source")
        if isinstance(value.get("source"), Mapping)
        else {}
    )
    errors: list[dict[str, Any]] = []
    expected_sha256 = str(
        expected_projection.get("source_chain_binding_sha256") or ""
    ).upper()
    if (
        str(source.get("aspen_source_binding_sha256") or "").upper()
        != expected_sha256
    ):
        errors.append({
            "code": "CELL_SOURCE_CHAIN_POINTER_SHA256_MISMATCH",
            "location": location,
        })
    if (
        source.get("aspen_source_binding_scope")
        != "ROW_LEVEL_SOURCE_CHAIN_POINTER"
    ):
        errors.append({
            "code": "CELL_SOURCE_CHAIN_POINTER_SCOPE_INVALID",
            "location": location,
        })

    def inspect(nested: Any, nested_location: str) -> None:
        if isinstance(nested, Mapping):
            if "aspen_source_binding" in nested:
                errors.append({
                    "code": "CELL_SOURCE_EMBEDS_ROW_SOURCE_CHAIN",
                    "location": nested_location,
                })
            if "aspen_source_binding_sha256" in nested:
                if (
                    str(
                        nested.get("aspen_source_binding_sha256")
                        or ""
                    ).upper()
                    != expected_sha256
                ):
                    errors.append({
                        "code": (
                            "NESTED_SOURCE_CHAIN_POINTER_SHA256_MISMATCH"
                        ),
                        "location": nested_location,
                    })
                if (
                    nested.get("aspen_source_binding_scope")
                    != "ROW_LEVEL_SOURCE_CHAIN_POINTER"
                ):
                    errors.append({
                        "code": "NESTED_SOURCE_CHAIN_POINTER_SCOPE_INVALID",
                        "location": nested_location,
                    })
            for key, child in nested.items():
                inspect(child, f"{nested_location}.{key}")
        elif isinstance(nested, list):
            for index, child in enumerate(nested):
                inspect(child, f"{nested_location}[{index}]")

    inspect(value, location)
    return errors


def verify_equipment_overview_table(
    table: Mapping[str, Any],
) -> dict[str, Any]:
    """Recompute every visible overview cell, row and table hash."""

    errors: list[dict[str, Any]] = []
    rows = (
        table.get("rows")
        if isinstance(table.get("rows"), list)
        else []
    )
    if (
        table.get("schema") != "equipment-overview-table-v1"
        or table.get("row_count") != len(rows)
    ):
        errors.append({
            "code": "OVERVIEW_SCHEMA_OR_ROW_COUNT_INVALID",
        })
    equipment_keys: list[str] = []
    for row_index, raw_row in enumerate(rows):
        if not isinstance(raw_row, Mapping):
            errors.append({
                "code": "OVERVIEW_ROW_NOT_OBJECT",
                "row_index": row_index,
            })
            continue
        row = raw_row
        location = f"overview.rows[{row_index}]"
        equipment_keys.append(str(row.get("equipment_key") or ""))
        errors.extend(_source_binding_errors(row, location=location))
        source_input_sha256 = row.get("source_input_sha256")
        record_kind = row.get("record_kind")
        all_fields = (
            row.get("all_equipment_fields")
            if isinstance(row.get("all_equipment_fields"), list)
            else []
        )
        all_field_hashes: list[Any] = []
        for cell_index, raw_cell in enumerate(all_fields):
            if not isinstance(raw_cell, Mapping):
                errors.append({
                    "code": "DELIVERY_CELL_NOT_OBJECT",
                    "location": (
                        f"{location}.all_equipment_fields"
                        f"[{cell_index}]"
                    ),
                })
                continue
            cell_location = (
                f"{location}.all_equipment_fields[{cell_index}]"
            )
            errors.extend(
                _source_binding_errors(
                    raw_cell,
                    location=cell_location,
                    expected_projection=row,
                    require_embedded_binding=False,
                )
            )
            errors.extend(_cell_source_pointer_errors(
                raw_cell,
                expected_projection=row,
                location=cell_location,
            ))
            expected_cell_sha256 = (
                _delivery_cell_expected_sha256(
                    raw_cell,
                    source_input_sha256=source_input_sha256,
                    record_kind=record_kind,
                )
            )
            if raw_cell.get("cell_sha256") != expected_cell_sha256:
                errors.append({
                    "code": "DELIVERY_CELL_SHA256_MISMATCH",
                    "location": cell_location,
                    "field_id": raw_cell.get("field_id"),
                })
            all_field_hashes.append(raw_cell.get("cell_sha256"))
        expected_all_fields_sha256 = _sha256_json(
            all_field_hashes
        )
        if (
            row.get("all_equipment_fields_sha256")
            != expected_all_fields_sha256
        ):
            errors.append({
                "code": "ALL_EQUIPMENT_FIELDS_SHA256_MISMATCH",
                "location": location,
            })
        authority_cells = (
            row.get("authority_cells")
            if isinstance(row.get("authority_cells"), list)
            else []
        )
        authority_cell_hashes: list[Any] = []
        for cell_index, raw_cell in enumerate(authority_cells):
            if not isinstance(raw_cell, Mapping):
                errors.append({
                    "code": "AUTHORITY_CELL_NOT_OBJECT",
                    "location": (
                        f"{location}.authority_cells[{cell_index}]"
                    ),
                })
                continue
            cell_location = (
                f"{location}.authority_cells[{cell_index}]"
            )
            errors.extend(
                _source_binding_errors(
                    raw_cell,
                    location=cell_location,
                    expected_projection=row,
                    require_embedded_binding=False,
                )
            )
            errors.extend(_cell_source_pointer_errors(
                raw_cell,
                expected_projection=row,
                location=cell_location,
            ))
            expected_cell_sha256 = (
                _authority_cell_expected_sha256(
                    raw_cell,
                    source_input_sha256=source_input_sha256,
                    record_kind=record_kind,
                    authority_table_id=row.get(
                        "authority_table_id"
                    ),
                )
            )
            if raw_cell.get("cell_sha256") != expected_cell_sha256:
                errors.append({
                    "code": "AUTHORITY_CELL_SHA256_MISMATCH",
                    "location": cell_location,
                    "field_id": raw_cell.get("field_id"),
                })
            authority_cell_hashes.append(
                raw_cell.get("cell_sha256")
            )
        formal_gate = (
            row.get("formal_readiness_gate")
            if isinstance(
                row.get("formal_readiness_gate"), Mapping
            )
            else {}
        )
        formal_gate_blockers = sorted(set([
            *[
                str(value)
                for value in formal_gate.get(
                    "blocking_fields", []
                )
            ],
            *[
                str(value)
                for value in formal_gate.get(
                    "blocking_reasons", []
                )
            ],
        ]))
        expected_row_payload = {
            "input_sha256": source_input_sha256,
            "record_kind": record_kind,
            "aspen_source_binding": row.get(
                "source_chain_binding", {}
            ),
            "authority_table_id": row.get(
                "authority_table_id"
            ),
            "authority_source": row.get("authority_source", {}),
            "authority_cell_hashes": authority_cell_hashes,
            "all_equipment_fields_sha256": (
                expected_all_fields_sha256
            ),
            "information_coverage_state": (
                row.get("authority_information_coverage", {})
                .get("state")
                if isinstance(
                    row.get("authority_information_coverage"),
                    Mapping,
                )
                else None
            ),
            "customer_information_state": (
                row.get("customer_information_coverage", {})
                .get("state")
                if isinstance(
                    row.get("customer_information_coverage"),
                    Mapping,
                )
                else None
            ),
            "specificity_state": (
                row.get("selection_specificity_gate", {})
                .get("state")
                if isinstance(
                    row.get("selection_specificity_gate"),
                    Mapping,
                )
                else None
            ),
            "formal_gate_blockers": formal_gate_blockers,
        }
        no_authority_profile = (
            row.get("authority_table_id") is None
            and not authority_cells
            and isinstance(
                row.get("authority_structural_completeness"),
                Mapping,
            )
            and row["authority_structural_completeness"].get(
                "state"
            )
            == "NOT_APPLICABLE"
        )
        if not no_authority_profile:
            expected_row_payload[
                "authority_full_field_coverage_state"
            ] = (
                row.get("authority_full_field_coverage", {})
                .get("state")
                if isinstance(
                    row.get("authority_full_field_coverage"),
                    Mapping,
                )
                else None
            )
        expected_row_sha256 = _sha256_json(expected_row_payload)
        if row.get("authority_row_sha256") != expected_row_sha256:
            errors.append({
                "code": "AUTHORITY_ROW_SHA256_MISMATCH",
                "location": location,
            })
    if (
        any(not key for key in equipment_keys)
        or len(set(equipment_keys)) != len(equipment_keys)
    ):
        errors.append({
            "code": "OVERVIEW_EQUIPMENT_GRAIN_INVALID",
        })
    row_hashes = [
        row.get("authority_row_sha256")
        for row in rows
        if isinstance(row, Mapping)
    ]
    if table.get("row_hashes") != row_hashes:
        errors.append({
            "code": "OVERVIEW_ROW_HASH_LIST_MISMATCH",
        })
    expected_table_sha256 = _sha256_json({
        "schema": "equipment-overview-table-v1",
        "authority_contract": table.get("authority_contract"),
        "columns": table.get("columns"),
        "profile_authority": table.get("profile_authority"),
        "row_hashes": row_hashes,
        "record_kinds": [
            row.get("record_kind")
            for row in rows
            if isinstance(row, Mapping)
        ],
    })
    if table.get("table_sha256") != expected_table_sha256:
        errors.append({
            "code": "OVERVIEW_TABLE_SHA256_MISMATCH",
        })
    return {
        "schema": "equipment-overview-verification-v1",
        "status": "PASS" if not errors else "FAIL",
        "row_count": len(rows),
        "error_count": len(errors),
        "errors": errors,
        "verified_table_sha256": expected_table_sha256,
    }


def verify_customer_delivery_bundle(
    bundle: Mapping[str, Any],
) -> dict[str, Any]:
    """Verify the customer overview, datasheets and evidence index."""

    errors: list[dict[str, Any]] = []
    overview = (
        bundle.get("equipment_overview_table")
        if isinstance(
            bundle.get("equipment_overview_table"), Mapping
        )
        else {}
    )
    overview_verification = verify_equipment_overview_table(
        overview
    )
    errors.extend(overview_verification["errors"])
    overview_rows = [
        row
        for row in overview.get("rows", [])
        if isinstance(row, Mapping)
    ]
    overview_bindings = {
        str(row.get("equipment_key") or ""): str(
            row.get("program_generated_record_sha256") or ""
        )
        for row in overview_rows
    }

    datasheet_table = (
        bundle.get("equipment_family_datasheet")
        if isinstance(
            bundle.get("equipment_family_datasheet"), Mapping
        )
        else {}
    )
    datasheets = [
        item
        for item in datasheet_table.get("equipment", [])
        if isinstance(item, Mapping)
    ]
    datasheet_hashes: list[Any] = []
    datasheet_bindings: dict[str, str] = {}
    for sheet_index, sheet in enumerate(datasheets):
        location = f"family_datasheet.equipment[{sheet_index}]"
        errors.extend(_source_binding_errors(
            sheet,
            location=location,
        ))
        fields = [
            cell
            for cell in sheet.get("fields", [])
            if isinstance(cell, Mapping)
        ]
        for cell_index, cell in enumerate(fields):
            cell_location = (
                f"{location}.fields[{cell_index}]"
            )
            errors.extend(_source_binding_errors(
                cell,
                location=cell_location,
                expected_projection=sheet,
                require_embedded_binding=False,
            ))
            errors.extend(_cell_source_pointer_errors(
                cell,
                expected_projection=sheet,
                location=cell_location,
            ))
            expected_cell_sha256 = (
                _delivery_cell_expected_sha256(
                    cell,
                    source_input_sha256=sheet.get(
                        "source_input_sha256"
                    ),
                    record_kind=sheet.get("record_kind"),
                )
            )
            if cell.get("cell_sha256") != expected_cell_sha256:
                errors.append({
                    "code": "DATASHEET_CELL_SHA256_MISMATCH",
                    "location": cell_location,
                    "field_id": cell.get("field_id"),
                })
        expected_datasheet_sha256 = _sha256_json({
            "equipment_key": sheet.get("equipment_key"),
            "record_kind": sheet.get("record_kind"),
            "source_input_sha256": sheet.get(
                "source_input_sha256"
            ),
            "source_chain_binding_sha256": sheet.get(
                "source_chain_binding_sha256"
            ),
            "program_generated_record_sha256": sheet.get(
                "program_generated_record_sha256"
            ),
            "field_hashes": [
                cell.get("cell_sha256") for cell in fields
            ],
        })
        if sheet.get("datasheet_sha256") != expected_datasheet_sha256:
            errors.append({
                "code": "DATASHEET_SHA256_MISMATCH",
                "location": location,
            })
        datasheet_hashes.append(sheet.get("datasheet_sha256"))
        datasheet_bindings[str(sheet.get("equipment_key") or "")] = (
            str(sheet.get("program_generated_record_sha256") or "")
        )
    if (
        datasheet_table.get("equipment_count") != len(datasheets)
        or datasheet_table.get("datasheet_hashes")
        != datasheet_hashes
    ):
        errors.append({
            "code": "DATASHEET_COUNT_OR_HASH_LIST_INVALID",
        })
    expected_datasheet_set_sha256 = _sha256_json({
        "schema": "equipment-family-datasheet-v1",
        "equipment_count": len(datasheets),
        "datasheet_hashes": datasheet_hashes,
    })
    if (
        datasheet_table.get("datasheet_set_sha256")
        != expected_datasheet_set_sha256
    ):
        errors.append({
            "code": "DATASHEET_SET_SHA256_MISMATCH",
        })
    if overview_bindings != datasheet_bindings:
        errors.append({
            "code": "OVERVIEW_DATASHEET_GRAIN_OR_BINDING_MISMATCH",
        })

    evidence_index = (
        bundle.get("equipment_evidence_index")
        if isinstance(
            bundle.get("equipment_evidence_index"), Mapping
        )
        else {}
    )
    evidence_records = [
        record
        for record in evidence_index.get("records", [])
        if isinstance(record, Mapping)
    ]
    evidence_record_hashes: list[Any] = []
    for record_index, record in enumerate(evidence_records):
        location = f"evidence_index.records[{record_index}]"
        errors.extend(_source_binding_errors(
            record,
            location=location,
        ))
        payload = copy.deepcopy(dict(record))
        declared_record_sha256 = payload.pop(
            "record_sha256", None
        )
        expected_record_sha256 = _sha256_json(payload)
        if declared_record_sha256 != expected_record_sha256:
            errors.append({
                "code": "EVIDENCE_RECORD_SHA256_MISMATCH",
                "location": location,
            })
        evidence_record_hashes.append(declared_record_sha256)
    if (
        evidence_index.get("record_count")
        != len(evidence_records)
        or evidence_index.get("record_hashes")
        != evidence_record_hashes
        or evidence_index.get("equipment_count")
        != len(overview_rows)
    ):
        errors.append({
            "code": "EVIDENCE_INDEX_COUNT_OR_HASH_LIST_INVALID",
        })
    expected_evidence_index_sha256 = _sha256_json({
        "schema": "equipment-evidence-index-v1",
        "equipment_count": len(overview_rows),
        "record_count": len(evidence_records),
        "record_hashes": evidence_record_hashes,
    })
    if (
        evidence_index.get("index_sha256")
        != expected_evidence_index_sha256
    ):
        errors.append({
            "code": "EVIDENCE_INDEX_SHA256_MISMATCH",
        })

    expected_bundle_sha256 = _sha256_json({
        "schema": bundle.get("schema"),
        "version": bundle.get("version"),
        "profile_authority": bundle.get("profile_authority"),
        "overview_table_sha256": overview.get("table_sha256"),
        "datasheet_set_sha256": datasheet_table.get(
            "datasheet_set_sha256"
        ),
        "evidence_index_sha256": evidence_index.get(
            "index_sha256"
        ),
    })
    declared_bundle_sha256 = bundle.get("bundle_sha256")
    if (
        declared_bundle_sha256 is not None
        and declared_bundle_sha256 != expected_bundle_sha256
    ):
        errors.append({
            "code": "CUSTOMER_DELIVERY_BUNDLE_SHA256_MISMATCH",
        })
    return {
        "schema": "equipment-customer-delivery-verification-v1",
        "status": "PASS" if not errors else "FAIL",
        "overview": overview_verification,
        "datasheet_count": len(datasheets),
        "evidence_record_count": len(evidence_records),
        "error_count": len(errors),
        "errors": errors,
        "verified_bundle_sha256": expected_bundle_sha256,
    }


def build_customer_delivery(
    deterministic_result: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    parameter_package: Mapping[str, Any] | None = None,
    model_recommendation: Mapping[str, Any] | None = None,
    *,
    profiles: Mapping[str, Any] | None = None,
    profiles_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build all three customer delivery objects from matcher authority state.

    Explicit ``parameter_package`` and ``model_recommendation`` overrides are
    supported for a single result so callers can pass the three matcher nodes
    separately.  Batches use each result's embedded package/recommendation.
    """

    results = _unwrap_results(deterministic_result)
    if len(results) != 1 and (parameter_package is not None or model_recommendation is not None):
        raise CustomerDeliveryError("separate package/model arguments are only valid for one result")
    if profiles is not None and profiles_path is not None:
        raise CustomerDeliveryError("provide profiles or profiles_path, not both")
    profile_contract = (
        normalise_output_profiles(profiles, source={"kind": "in_memory"})
        if profiles is not None else load_customer_output_profiles(profiles_path)
    )
    contexts = [
        _context(
            result,
            parameter_package if len(results) == 1 else None,
            model_recommendation if len(results) == 1 else None,
        )
        for result in results
    ]
    contexts.sort(key=_equipment_sort_key)
    for sequence_number, context in enumerate(contexts, start=1):
        _attach_programmatic_aspen_overview_identity(
            context,
            sequence_number,
        )
    objects = _build_from_contexts(contexts, profile_contract)
    llm_used = bool(objects["equipment_overview_table"].get("llm_used"))
    model_estimate_disclosure = objects["equipment_overview_table"].get(
        "model_estimate_disclosure",
        {"llm_used": False, "status": "NOT_USED", "equipment": [], "statement": "交付内容未使用大模型工程估算。"},
    )
    bundle = {
        "schema": "equipment-customer-delivery-bundle-v1",
        "version": "1.0.0",
        "deterministic": True,
        "llm_used": llm_used,
        "model_estimate_disclosure": model_estimate_disclosure,
        "profile_authority": {
            "schema": profile_contract.get("schema"),
            "version": profile_contract.get("version"),
            "source": profile_contract.get("source"),
            "fallback": profile_contract.get("fallback", False),
        },
        **objects,
    }
    bundle["bundle_sha256"] = _sha256_json({
        "schema": bundle.get("schema"),
        "version": bundle.get("version"),
        "profile_authority": bundle.get("profile_authority"),
        "overview_table_sha256": bundle[
            "equipment_overview_table"
        ].get("table_sha256"),
        "datasheet_set_sha256": bundle[
            "equipment_family_datasheet"
        ].get("datasheet_set_sha256"),
        "evidence_index_sha256": bundle[
            "equipment_evidence_index"
        ].get("index_sha256"),
    })
    verification = verify_customer_delivery_bundle(bundle)
    if verification["status"] != "PASS":
        raise CustomerDeliveryError(
            "generated customer delivery bundle failed its own "
            f"hash verification: {verification['errors']}"
        )
    bundle["verification"] = verification
    return bundle


def build_equipment_overview_table(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return build_customer_delivery(*args, **kwargs)["equipment_overview_table"]


def build_equipment_family_datasheet(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return build_customer_delivery(*args, **kwargs)["equipment_family_datasheet"]


def build_equipment_evidence_index(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return build_customer_delivery(*args, **kwargs)["equipment_evidence_index"]


__all__ = [
    "CustomerDeliveryError",
    "DEFAULT_PROFILE_PATH",
    "build_customer_delivery",
    "build_equipment_evidence_index",
    "build_equipment_family_datasheet",
    "build_equipment_overview_table",
    "fallback_output_profiles",
    "load_customer_output_profiles",
    "normalise_output_profiles",
    "verify_customer_delivery_bundle",
    "verify_equipment_overview_table",
]
