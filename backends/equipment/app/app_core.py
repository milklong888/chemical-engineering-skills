from __future__ import annotations

import importlib.util
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
from contextlib import closing
from functools import lru_cache
from pathlib import Path
from typing import Any


FROZEN_ROOT = getattr(sys, "_MEIPASS", None)
if FROZEN_ROOT:
    PACKAGE_ROOT = Path(FROZEN_ROOT).resolve()
    APP_DIR = PACKAGE_ROOT / "app"
    WORKSPACE_ROOT = Path(os.environ.get("EQUIPMENT_DESIGN_WORKSPACE", Path.cwd())).resolve()
else:
    APP_DIR = Path(__file__).resolve().parent
    PACKAGE_ROOT = APP_DIR.parent
    WORKSPACE_ROOT = PACKAGE_ROOT
SCRIPTS_DIR = PACKAGE_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import equipment_design_match as matcher  # noqa: E402
import equipment_service_profile as service_profile  # noqa: E402
import connection_component_selection as connection_selection  # noqa: E402
import database_authority  # noqa: E402
import runtime_bundle  # noqa: E402
import source_code_manifest  # noqa: E402
import customer_delivery  # noqa: E402

BUNDLED_SELECTION_GRAPH = PACKAGE_ROOT / "equipment_selection_graph" / "equipment_selection_graph_v2.json"
if BUNDLED_SELECTION_GRAPH.is_file():
    matcher.GRAPH_PATH = BUNDLED_SELECTION_GRAPH


@lru_cache(maxsize=1)
def runtime_bundle_verification() -> dict[str, Any]:
    """Verify the exact frozen runtime asset set before it becomes active."""
    return runtime_bundle.verify_runtime_bundle(
        PACKAGE_ROOT,
        required=True,
    )


@lru_cache(maxsize=1)
def source_code_manifest_verification() -> dict[str, Any]:
    """Verify the executable authority source set or its frozen snapshot."""
    return source_code_manifest.verify_current_runtime(
        PACKAGE_ROOT,
        frozen=bool(FROZEN_ROOT),
    )


@lru_cache(maxsize=1)
def standards_database_verification() -> dict[str, Any]:
    """Verify the registry-bound standards retrieval carrier once per process."""
    from projected_standard_store import verification
    return verification(PACKAGE_ROOT)


def require_runtime_bundle() -> dict[str, Any]:
    verification = runtime_bundle_verification()
    if not verification.get("verified"):
        raise runtime_bundle.RuntimeBundleError(
            "运行时知识资产包校验失败："
            + json.dumps(verification.get("issues", []), ensure_ascii=False)
        )
    source_verification = source_code_manifest_verification()
    if not source_verification.get("verified"):
        raise source_code_manifest.SourceCodeManifestError(
            "核心源码权威清单校验失败："
            + json.dumps(source_verification.get("issues", []), ensure_ascii=False)
        )
    return {
        **verification,
        "source_code_manifest": source_verification,
    }


CALCULATION_FIELDS: dict[str, list[str]] = {
    name: list(fields) for name, fields in matcher.CALCULATION_REQUIREMENTS.items()
}
CALCULATION_FIELDS["pressure_ratio"].append("atmospheric_pressure_mpa")
CALCULATION_FIELDS["design_pressure"].append("atmospheric_pressure_mpa")


FIELD_META: dict[str, dict[str, Any]] = {
    "equipment_tag": {"label": "设备位号", "type": "text", "placeholder": "P-101"},
    "equipment_type": {"label": "结构型式（可留空）", "type": "text", "placeholder": "存在多选时保留共同上位型式"},
    "process_function": {"label": "工艺功能", "type": "text", "placeholder": "例如：液体升压"},
    "phase": {"label": "相态", "type": "select", "options": ["", "liquid", "vapor", "mixed", "solid"]},
    "pressure_basis": {"label": "压力基准", "type": "select", "options": ["", "absolute", "gauge"], "placeholder": "必须显式选择 absolute 或 gauge"},
    "design_pressure_basis": {
        "label": "设计压力基准",
        "type": "select",
        "options": ["", "absolute", "gauge"],
        "placeholder": "直接给设计压力时必须声明；厚度和候选统一换算为 gauge",
    },
    "atmospheric_pressure_mpa": {
        "label": "当地大气压",
        "unit": "MPa",
        "type": "number",
        "placeholder": "绝压→表压设计换算，或表压→绝压压比换算时必填；不内置默认值",
    },
    "flow_m3_h": {"label": "体积流量", "unit": "m³/h", "type": "number"},
    "mass_flow_kg_h": {"label": "质量流量", "unit": "kg/h", "type": "number"},
    "head_m": {"label": "扬程", "unit": "m", "type": "number"},
    "density_kg_m3": {"label": "密度", "unit": "kg/m³", "type": "number"},
    "efficiency_percent": {"label": "效率", "unit": "%", "type": "number"},
    "inlet_pressure_mpa": {"label": "入口压力", "unit": "MPa", "type": "number"},
    "outlet_pressure_mpa": {"label": "出口压力", "unit": "MPa", "type": "number"},
    "operating_pressure_mpa": {"label": "操作压力", "unit": "MPa", "type": "number"},
    "design_pressure_mpa": {
        "label": "设计压力值（按所选基准）",
        "unit": "MPa",
        "type": "number",
        "placeholder": "直接输入时同时选设计压力基准；规范化结果会单独显示为表压",
    },
    "design_pressure_factor": {"label": "设计压力系数", "unit": "-", "type": "number"},
    "pressure_drop_kpa": {"label": "压降", "unit": "kPa", "type": "number"},
    "allowable_pressure_drop_kpa": {"label": "允许压降", "unit": "kPa", "type": "number"},
    "temperature_c": {"label": "操作温度", "unit": "°C", "type": "number"},
    "inlet_temperature_c": {"label": "入口温度", "unit": "°C", "type": "number"},
    "design_temperature_c": {"label": "设计温度", "unit": "°C", "type": "number"},
    "heat_duty_kw": {"label": "热负荷", "unit": "kW", "type": "number"},
    "heat_transfer_area_m2": {"label": "换热面积", "unit": "m²", "type": "number"},
    "overall_u_w_m2k": {"label": "总传热系数", "unit": "W/(m²·K)", "type": "number"},
    "lmtd_k": {"label": "对数平均温差", "unit": "K", "type": "number"},
    "lmtd_correction_factor": {"label": "LMTD 修正系数 F", "unit": "-", "type": "number", "placeholder": "必须显式给出；不会默认按 1"},
    "diameter_mm": {"label": "设备直径", "unit": "mm", "type": "number"},
    "height_mm": {"label": "设备高度", "unit": "mm", "type": "number"},
    "inner_diameter_mm": {"label": "计算内径", "unit": "mm", "type": "number"},
    "straight_shell_length_mm": {
        "label": "筒体直段长度",
        "unit": "mm",
        "type": "number",
        "placeholder": "仅用于直筒段几何容积；不能用设备总高代替",
    },
    "volume_m3": {"label": "用户/同工况给定的设计容积", "unit": "m³", "type": "number"},
    "volume_basis": {
        "label": "设计容积基准",
        "type": "select",
        "options": ["", "nominal_total", "effective_working", "geometric_total"],
        "placeholder": "候选使用容积时必须声明；直筒段几何容积不会自动充当设计容积",
    },
    "required_volume_m3": {"label": "最低所需总容积", "unit": "m³", "type": "number"},
    "straight_shell_geometric_volume_m3": {"label": "圆筒直段几何容积", "unit": "m³", "type": "number"},
    "stage_count": {"label": "级数/塔板数", "unit": "个", "type": "number", "integer": True},
    "retention_time_min": {"label": "停留时间", "unit": "min", "type": "number"},
    "fill_fraction": {"label": "装填系数", "unit": "-", "type": "number"},
    "target_velocity_m_s": {"label": "目标流速", "unit": "m/s", "type": "number"},
    "selected_dn": {"label": "公称直径 DN", "unit": "mm", "type": "number"},
    "selected_outer_diameter_mm": {"label": "选定外径", "unit": "mm", "type": "number"},
    "selected_wall_thickness_mm": {"label": "选定壁厚", "unit": "mm", "type": "number"},
    "wall_series": {"label": "壁厚系列", "type": "text"},
    "allowable_stress_mpa": {"label": "许用应力", "unit": "MPa", "type": "number"},
    "weld_efficiency": {"label": "焊接接头系数", "unit": "-", "type": "number"},
    "npsha_m": {"label": "装置汽蚀余量 NPSHa", "unit": "m", "type": "number"},
    "npshr_m": {"label": "泵必需汽蚀余量 NPSHr", "unit": "m", "type": "number"},
    "required_npsh_margin_m": {
        "label": "规定 NPSH 裕量",
        "unit": "m",
        "type": "number",
        "placeholder": "可选；留空时汽蚀裕量约束保持 UNKNOWN",
    },
    "npshr_evidence_scope": {
        "label": "NPSHr 证据适用范围",
        "type": "select",
        "options": ["", "same_duty_vendor_curve"],
        "placeholder": "正式 NPSHr 证据必须来自同工况厂家曲线",
    },
    "gas_molecular_weight": {"label": "气体分子量", "unit": "kg/kmol", "type": "number"},
    "compressibility_factor": {"label": "压缩因子 Z", "unit": "-", "type": "number"},
    "surge_margin_percent": {
        "label": "实际/观测喘振裕量",
        "unit": "%",
        "type": "number",
        "placeholder": "可为负；负值表示工况已越过规定裕量一侧，不作为输入格式错误",
    },
    "required_surge_margin_percent": {
        "label": "规定喘振裕量",
        "unit": "%",
        "type": "number",
        "placeholder": "可选；留空时喘振约束保持 UNKNOWN，不内置默认值",
    },
    "surge_margin_evidence_scope": {
        "label": "喘振裕量证据适用范围",
        "type": "select",
        "options": ["", "same_duty_performance_map"],
        "placeholder": "正式证据必须来自同工况压缩机性能图",
    },
    "rotational_speed_rpm": {"label": "转速", "unit": "rpm", "type": "number"},
    "shaft_power_kw": {"label": "轴功率", "unit": "kW", "type": "number"},
    "pressure_drop_power_component_kw": {"label": "压差功率分量（初筛）", "unit": "kW", "type": "number"},
    "pressure_component_shaft_power_screening_kw": {"label": "压差分量轴功率初筛", "unit": "kW", "type": "number"},
    "pressure_drop_head_component_m": {"label": "压差水头分量（初筛）", "unit": "m", "type": "number"},
    "mixing_metric": {"label": "混合指标", "unit": "-", "type": "text"},
    "membrane_geometry_type": {
        "label": "膜通道几何型式",
        "type": "select",
        "options": ["", "cylindrical_channels", "spiral_wound", "hollow_fiber", "flat_sheet"],
        "placeholder": "当前内置面积式仅支持 cylindrical_channels；其他型式需提供外部面积",
    },
    "element_count": {"label": "元件数", "unit": "个", "type": "number", "integer": True},
    "channel_count": {"label": "通道数", "unit": "个", "type": "number", "integer": True},
    "channel_inner_diameter_mm": {"label": "通道内径", "unit": "mm", "type": "number"},
    "element_length_m": {"label": "元件长度", "unit": "m", "type": "number"},
    "membrane_area_m2": {"label": "膜面积", "unit": "m²", "type": "number"},
    "flux": {"label": "通量", "type": "number"},
    "selectivity": {"label": "选择性", "type": "number"},
    "capacity": {"label": "处理能力", "type": "number"},
    "cycle_time_h": {"label": "循环周期", "unit": "h", "type": "number"},
    "recovery_percent": {"label": "回收率", "unit": "%", "type": "number"},
    "fitting_type": {"label": "管件型式", "type": "text"},
    "connection_type": {"label": "连接型式", "type": "text"},
    "pressure_class": {"label": "压力等级 PN / Class", "type": "text"},
    "flange_face": {"label": "法兰密封面", "type": "text"},
    "gasket_material": {"label": "垫片材料", "type": "text"},
    "valve_function": {"label": "阀门功能", "type": "text"},
    "cv": {"label": "阀门 Cv", "type": "number"},
    "cavitation_margin_m": {"label": "空化裕量", "unit": "m", "type": "number"},
    "candidate_model": {"label": "标准/厂家候选型号", "type": "text", "placeholder": "仅作为候选，不自动定型"},
    "material": {"label": "材料偏好", "type": "text", "placeholder": "可选；留空时由规则给候选或列出缺口"},
    "head_type": {
        "label": "封头型式（2:1_ellipsoidal = 2:1 椭圆封头）",
        "type": "select",
        "options": ["", "2:1_ellipsoidal"],
        "placeholder": "可选方法分支；留空时封头厚度计算等待型式确认",
    },
}


COMMON_FIELDS = ["equipment_tag", "equipment_name", "equipment_type", "process_function", "phase"]
OPTIONAL_DESIGN_FIELDS = [
    "pressure_basis", "design_pressure_basis", "atmospheric_pressure_mpa", "operating_pressure_mpa",
    "design_pressure_mpa", "design_pressure_factor", "volume_basis", "straight_shell_length_mm", "temperature_c",
    "design_temperature_c", "material", "candidate_model",
]
FORMAL_EVIDENCE_FIELDS = [
    "formal_calculation_path", "formal_calculation_sha256",
    "evidence_manifest_path", "evidence_manifest_sha256",
    "audit_approval_path", "audit_approval_sha256", "approval_status",
]

MANUAL_FAMILY_EXTRA_FIELDS: dict[str, list[str]] = {
    "family_pump": ["required_npsh_margin_m", "npshr_evidence_scope"],
    "family_compressor": ["required_surge_margin_percent", "surge_margin_evidence_scope"],
    "family_tower": ["head_type"],
    "family_reactor_vessel_separator": ["head_type"],
    "family_storage_vessel": ["head_type"],
}

MANUAL_FAMILY_EXTRA_FIELD_GROUPS: dict[tuple[str, str], tuple[str, str]] = {
    ("family_pump", "required_npsh_margin_m"): ("optional_check", "候选/校核可选输入"),
    ("family_pump", "npshr_evidence_scope"): ("evidence", "同设备证据与批准"),
    ("family_compressor", "required_surge_margin_percent"): ("optional_check", "候选/校核可选输入"),
    ("family_compressor", "surge_margin_evidence_scope"): ("evidence", "同设备证据与批准"),
    ("family_tower", "head_type"): ("advanced_design", "高级设计条件"),
    ("family_reactor_vessel_separator", "head_type"): ("advanced_design", "高级设计条件"),
    ("family_storage_vessel", "head_type"): ("advanced_design", "高级设计条件"),
}


# The desktop manual page describes a process task, not a completed equipment
# datasheet.  These are the smallest source/target fields that the current
# deterministic engine can genuinely consume to close its primary calculation
# or candidate path.  Other Aspen-computable properties remain recommended
# inputs; calculated geometry/power/model fields are outputs unless the user
# explicitly opens the advanced "known result" section.
MANUAL_REQUIRED_FIELDS_BY_FAMILY: dict[str, set[str]] = {
    "family_fixed_tubesheet_exchanger": {"heat_duty_kw"},
    "family_other_heat_exchanger": {"heat_duty_kw"},
    "family_pump": {"phase", "flow_m3_h", "density_kg_m3", "inlet_pressure_mpa", "outlet_pressure_mpa", "pressure_basis"},
    "family_compressor": {"phase", "flow_m3_h", "inlet_pressure_mpa", "outlet_pressure_mpa", "pressure_basis", "inlet_temperature_c", "gas_molecular_weight", "compressibility_factor"},
    "family_static_mixer": {"flow_m3_h", "target_velocity_m_s"},
    "family_liquid_power_recovery_turbine": {"phase", "flow_m3_h", "density_kg_m3", "inlet_pressure_mpa", "outlet_pressure_mpa", "pressure_basis"},
    "family_gas_expander_turbine": {"phase", "flow_m3_h", "inlet_pressure_mpa", "outlet_pressure_mpa", "pressure_basis", "inlet_temperature_c"},
    "family_process_piping": {"flow_m3_h", "target_velocity_m_s"},
    "family_pipe_fitting": {"selected_dn", "wall_series", "fitting_type"},
    "family_flange_gasket": {"selected_dn", "pressure_class", "flange_face"},
    "family_valve": {"valve_function", "flow_m3_h", "pressure_drop_kpa"},
}

MANUAL_OPTIONAL_PREFERENCE_FIELDS = {
    "equipment_type", "material", "gasket_material", "seal_type", "operating_mode",
    "standby_configuration", "quantity_and_standby", "orientation", "roof_or_head_type",
    "connection_type", "pressure_class", "flange_face", "wall_series", "fitting_type",
    "valve_function", "allowable_pressure_drop_kpa", "target_velocity_m_s",
    "design_pressure_factor", "fill_fraction", "retention_time_min", "rotational_speed_rpm",
}

MANUAL_TARGET_FIELDS = {
    "outlet_pressure_mpa", "design_temperature_c", "allowable_pressure_drop_kpa",
    "target_velocity_m_s", "capacity", "cycle_time_h", "recovery_percent",
    "retention_time_min", "fill_fraction", "stage_count", "lmtd_correction_factor",
}

MANUAL_ADVANCED_DESIGN_FIELDS = {
    "volume_m3", "volume_basis", "diameter_mm", "height_mm", "inner_diameter_mm",
    "straight_shell_length_mm", "membrane_geometry_type", "element_count",
    "channel_count", "channel_inner_diameter_mm", "element_length_m", "membrane_area_m2",
}

MANUAL_KNOWN_RESULT_FIELDS = {
    *matcher.CALCULATION_OUTPUT_FIELDS.values(),
    "diameter_mm", "height_mm", "inner_diameter_mm", "selected_dn",
    "selected_outer_diameter_mm", "selected_wall_thickness_mm", "pressure_class",
    "impeller_diameter_mm", "bep_duty_point", "allowable_operating_region",
    "heat_transfer_surface_spec", "plate_or_tube_bundle_parameters",
    "candidate_model", "mechanical_design_ref", "thermal_hydraulic_evidence_ref",
}

MANUAL_PROCESS_NAME_MARKERS = (
    "flow", "pressure", "temperature", "density", "viscosity", "molecular_weight",
    "compressibility", "phase", "medium", "composition", "heat_duty", "lmtd",
    "overall_u", "surface_tension", "specific_heat", "thermal_conductivity", "flux",
    "selectivity", "recovery", "capacity", "cycle_time", "npsh", "efficiency",
)


def _manual_field_contract(family_id: str, field: dict[str, Any]) -> dict[str, Any]:
    name = str(field["name"])
    group_id = str(field.get("group_id", ""))
    required = name in MANUAL_REQUIRED_FIELDS_BY_FAMILY.get(family_id, set())

    if group_id == "evidence" or name in FORMAL_EVIDENCE_FIELDS:
        role = "advanced_evidence"
        group_title = "正式证据（正式定型必需，基础计算可选）"
        blank_behavior = "没有同一台设备的正式文件时请留空；它不影响基础计算。"
    elif name in MANUAL_OPTIONAL_PREFERENCE_FIELDS:
        # An explicit user preference remains visible and clearly optional even
        # when its source template groups it under construction/selection.
        # In particular, material is a selectable constraint, not a mandatory
        # mechanical-design input and not a hidden calculated output.
        role = "optional_preference"
        group_title = "可选限制与偏好"
        blank_behavior = "留空不算漏填；系统保留泛用候选，或把需正式确认的内容列为缺口。"
    elif group_id in {"advanced_design", "construction"} or name in MANUAL_ADVANCED_DESIGN_FIELDS:
        role = "advanced_design_input"
        group_title = "高级设计条件（可选）"
        blank_behavior = (
            "可以留空；方法分支保持待确认。封头型式留空时，封头厚度计算等待型式确认，"
            "不作为输入错误。"
        )
    elif group_id == "optional_check":
        role = "optional_input"
        group_title = "候选/校核可选输入"
        blank_behavior = "可以留空；依赖它的候选或校核约束保持 UNKNOWN，不伪造通过结论。"
    elif group_id == "customer_delivery" and not any(marker in name for marker in MANUAL_PROCESS_NAME_MARKERS) and name not in MANUAL_OPTIONAL_PREFERENCE_FIELDS:
        role = "delivery_output"
        group_title = "客户交付结果"
        blank_behavior = "由结果页生成，不在普通手动输入中填写。"
    elif required:
        role = "required_input"
        group_title = "目标条件" if name in MANUAL_TARGET_FIELDS else "入口流股 / Aspen 物性"
        blank_behavior = "缺少时只阻断依赖它的计算或候选，不影响其他已知结果。"
    elif name in MANUAL_KNOWN_RESULT_FIELDS or group_id == "calculated_design":
        role = "known_result"
        group_title = "已有计算或规格（高级，可选）"
        blank_behavior = "通常由算法、Aspen、专业软件或厂家结果给出；只有已有权威值时才覆盖。"
    elif group_id == "selection":
        role = "optional_preference"
        group_title = "可选限制与偏好"
        blank_behavior = "留空不算漏填；系统保留泛用候选，或把需正式确认的内容列为缺口。"
    elif group_id == "identity":
        role = "optional_input" if name in {"equipment_tag", "process_function", "phase", "aspen_block_type"} else "optional_preference"
        group_title = "工艺任务"
        blank_behavior = "可以留空；填写后便于识别服务和结果。"
    elif any(marker in name for marker in MANUAL_PROCESS_NAME_MARKERS) or group_id not in {"additional", "customer_delivery"}:
        role = "recommended_input"
        group_title = "目标条件" if name in MANUAL_TARGET_FIELDS else "入口流股 / Aspen 物性"
        blank_behavior = (
            "建议从 Aspen 或工艺数据填写；留空时算法先用已登记的条件推荐/保底值继续预设计，"
            "并在结果中标出来源、警告和需替换项。"
        )
    else:
        role = "optional_input"
        group_title = "其他可选输入"
        blank_behavior = "可以留空；不会被当作必填项。"

    return {
        **field,
        "required": role == "required_input",
        "manual_role": role,
        "manual_group_title": group_title,
        "manual_blank_behavior": blank_behavior,
        "manual_default_visible": role in {"required_input", "recommended_input", "optional_input", "optional_preference"},
    }


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


@lru_cache(maxsize=1)
def _parameter_field_definitions() -> dict[str, dict[str, Any]]:
    document = matcher.load_parameter_templates()
    raw = document.get("parameter_definitions", {})
    return {
        str(field_id): dict(meta)
        for field_id, meta in raw.items()
        if isinstance(meta, dict)
    } if isinstance(raw, dict) else {}


def _field_descriptor(name: str, required: bool) -> dict[str, Any]:
    if name.endswith("_sha256"):
        fallback = {"label": f"{name[:-7].replace('_', ' ')} SHA-256", "type": "text"}
    elif name.endswith("_path"):
        fallback = {"label": f"{name[:-5].replace('_', ' ')} 文件路径", "type": "text"}
    else:
        fallback = {"label": name.replace("_", " "), "type": "text"}
    definition = _parameter_field_definitions().get(name, {})
    data_type = str(definition.get("data_type", definition.get("type", "string"))).casefold()
    from_definition = {
        "label": definition.get("label", fallback["label"]),
        "type": "number" if data_type in {"number", "integer", "float", "decimal"} else "text",
    }
    if definition.get("unit") not in (None, ""):
        from_definition["unit"] = definition.get("unit")
    if data_type == "integer":
        from_definition["integer"] = True
    meta = {**fallback, **from_definition, **FIELD_META.get(name, {})}
    meta.update({"name": name, "required": required})
    return meta


@lru_cache(maxsize=1)
def _matcher_runtime_authority() -> tuple[dict[str, Any], dict[str, Any]]:
    """Load immutable matching authority once for the resident process."""
    return matcher.load_json(matcher.RULES_PATH), matcher.load_graph()


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, Any]:
    rules, graph = _matcher_runtime_authority()
    model_rules = matcher.load_model_rules()
    parameter_templates = matcher.load_parameter_templates()
    model_rule_by_family = {item["family_id"]: item for item in model_rules.get("families", [])}
    parameter_template_by_family = {item["family_id"]: item for item in parameter_templates.get("families", [])}
    names = {node["id"]: node.get("name", node["id"]) for node in graph.get("nodes", [])}
    selections: list[dict[str, Any]] = []
    for family in rules["families"]:
        model_rule = model_rule_by_family.get(family["id"], {})
        parameter_template = parameter_template_by_family.get(family["id"], {})
        calculation_fields = [
            field
            for calc_id in family.get("calculation_rules", [])
            for field in CALCULATION_FIELDS.get(calc_id, [])
        ]
        sizing = list(family.get("sizing_fields", []))
        model_candidate_fields = list(model_rule.get("candidate_required_fields", [])) + list(model_rule.get("designation_fields", []))
        verification = list(family.get("verification_fields", []))
        verification_with_pairs: list[str] = []
        for field in verification:
            verification_with_pairs.append(field)
            paired_path = matcher.EVIDENCE_PAIRS.get(field)
            if paired_path:
                verification_with_pairs.append(paired_path)
        template_fields = [
            field
            for group in parameter_template.get("groups", [])
            for field in group.get("fields", [])
        ]
        family_extra_fields = MANUAL_FAMILY_EXTRA_FIELDS.get(str(family["id"]), [])
        field_names = _dedupe(COMMON_FIELDS + template_fields + sizing + model_candidate_fields + calculation_fields + verification_with_pairs + family_extra_fields + OPTIONAL_DESIGN_FIELDS + FORMAL_EVIDENCE_FIELDS)
        fields = [_field_descriptor(field, field in sizing) for field in field_names]
        field_groups: dict[str, tuple[str, str]] = {}
        for group in parameter_template.get("groups", []):
            for field in group.get("fields", []):
                field_groups.setdefault(field, (str(group.get("id", "parameters")), str(group.get("title", "参数"))))
        for field in fields:
            group_id, group_title = MANUAL_FAMILY_EXTRA_FIELD_GROUPS.get(
                (str(family["id"]), str(field["name"])),
                field_groups.get(field["name"], ("evidence", "同设备证据与批准") if field["name"] in verification_with_pairs + FORMAL_EVIDENCE_FIELDS else ("additional", "补充设计参数")),
            )
            field["group_id"] = group_id
            field["group_title"] = group_title
        fields = [_manual_field_contract(family["id"], field) for field in fields]
        for field in fields:
            name = str(field["name"])
            field["calculation_consumers"] = [
                calc_id
                for calc_id in family.get("calculation_rules", [])
                if name in CALCULATION_FIELDS.get(calc_id, [])
            ]
            field["candidate_required"] = name in model_rule.get("candidate_required_fields", [])
            field["sizing_required"] = name in sizing
            field["built_in_formula_output"] = name in matcher.CALCULATION_OUTPUT_FIELDS.values()
            field["primary_calculation_required"] = field.get("manual_role") == "required_input"
            field["candidate_closure_required"] = bool(field["candidate_required"])
            field["formal_evidence_input"] = field.get("manual_role") == "advanced_evidence"
            field["manual_requirement_tiers"] = [
                tier
                for tier, active in (
                    ("primary_calculation_required", field["primary_calculation_required"]),
                    ("candidate_closure_required", field["candidate_closure_required"]),
                    ("formal_evidence_required_for_release", field["formal_evidence_input"]),
                )
                if active
            ]
        manual_input_contract = {
            "schema": "equipment-design-manual-input-contract-v1",
            "primary_calculation_required_fields": [
                field["name"] for field in fields if field["primary_calculation_required"]
            ],
            "candidate_closure_required_fields": [
                field["name"] for field in fields if field["candidate_closure_required"]
            ],
            "candidate_fields_may_be_blank": True,
            "candidate_blank_behavior": (
                "可留空；算法先保留已知计算，并按已登记层级生成可追溯的预设计值或最泛用规格候选。"
                "不能安全补齐的字段仍列为缺口，但不会抹掉其他设备或整单输出。"
            ),
            "formal_release_requires_evidence": bool(model_rule.get("formal_model_gate")),
            "formal_evidence_gate": model_rule.get("formal_model_gate"),
            "formal_evidence_fields": [
                field["name"] for field in fields if field["formal_evidence_input"]
            ],
            "formal_evidence_blank_behavior": (
                "基础计算和候选筛选阶段可以留空；缺少同设备正式证据时不能宣称正式定型。"
            ),
        }
        block_types = family.get("block_types", []) or [""]
        for block_type in block_types:
            block_overlay = dict(parameter_templates.get("block_type_overlays", {}).get(str(block_type).upper(), {}))
            overlay_groups = list(block_overlay.get("groups", []))
            block_fields = [dict(field) for field in fields]
            existing_field_names = {str(field["name"]) for field in block_fields}
            block_calculation_ids = list(matcher.BLOCK_TYPE_CALCULATION_RULES.get(str(block_type).upper(), ()))
            for overlay_group in overlay_groups:
                group_id = str(overlay_group.get("id", "additional"))
                group_title = str(overlay_group.get("title", "专属预设计参数"))
                for overlay_field_name in overlay_group.get("fields", []):
                    name = str(overlay_field_name)
                    if name in existing_field_names:
                        for existing in block_fields:
                            if existing["name"] == name:
                                existing["group_id"] = group_id
                                existing["group_title"] = group_title
                        continue
                    descriptor = _field_descriptor(name, False)
                    descriptor["group_id"] = group_id
                    descriptor["group_title"] = group_title
                    descriptor = _manual_field_contract(family["id"], descriptor)
                    descriptor["calculation_consumers"] = [
                        calc_id for calc_id in block_calculation_ids
                        if name in matcher.CALCULATION_REQUIREMENTS.get(calc_id, ())
                    ]
                    descriptor["candidate_required"] = False
                    descriptor["sizing_required"] = False
                    descriptor["built_in_formula_output"] = name in matcher.CALCULATION_OUTPUT_FIELDS.values()
                    descriptor["primary_calculation_required"] = False
                    descriptor["candidate_closure_required"] = False
                    descriptor["formal_evidence_input"] = False
                    descriptor["manual_requirement_tiers"] = []
                    block_fields.append(descriptor)
                    existing_field_names.add(name)
            selections.append({
                "selection_id": f"block:{block_type}" if block_type else f"family:{family['id']}",
                "block_type": block_type or None,
                "family_id": family["id"],
                "family_name": names.get(family["id"], family["id"]),
                "display_name": f"{block_type} · {names.get(family['id'], family['id'])}" if block_type else names.get(family["id"], family["id"]),
                "model_policy": family.get("model_policy"),
                "model_recommendation": {
                    "recommendation_class": model_rule.get("recommendation_class"),
                    "generic_type": model_rule.get("generic_type"),
                    "candidate_required_fields": model_rule.get("candidate_required_fields", []),
                    "formal_model_gate": model_rule.get("formal_model_gate"),
                },
                "calculation_rules": [*family.get("calculation_rules", []), *block_calculation_ids],
                "parameter_template": {
                    "title": parameter_template.get("title"),
                    "visual_groups": [*parameter_template.get("groups", []), *overlay_groups],
                    "block_type_overlay": ({
                        "title": block_overlay.get("title"),
                        "formal_gate": block_overlay.get("formal_gate"),
                        "promotion_cap": block_overlay.get("promotion_cap"),
                    } if block_overlay else None),
                },
                "manual_input_contract": manual_input_contract,
                "fields": block_fields,
            })
    selections.sort(key=lambda item: (item["family_name"], item.get("block_type") or ""))
    return {
        "schema": "equipment-design-app-catalog-v1",
        "rule_version": rules.get("version"),
        "model_rule_version": model_rules.get("version"),
        "parameter_template_version": parameter_templates.get("version"),
        "multiple_choice_policy": rules.get("multiple_choice_policy", {}),
        "progressive_matching": {
            "available": True,
            "llm_required": False,
            "selection_id_required": False,
            "partial_input_returns_candidates_and_next_field": True,
        },
        "model_recommendations": {
            "available_for_all_families": len(model_rule_by_family) == len(rules.get("families", [])),
            "decision_policy": model_rules.get("decision_policy"),
            "formal_model_requires_evidence": True,
            "candidate_generation_requires_llm": False,
        },
        "parameter_packages": {
            "available_for_all_families": len(parameter_template_by_family) == len(rules.get("families", [])),
            "workflow": parameter_templates.get("workflow", []),
            "visual_template": parameter_templates.get("visual_template", {}),
            "customer_output_profile": parameter_templates.get("customer_output_profile", {}),
        },
        "customer_delivery_profiles": {
            "schema": matcher.CUSTOMER_OUTPUT_PROFILE_DOCUMENT.get("schema"),
            "version": matcher.CUSTOMER_OUTPUT_PROFILE_DOCUMENT.get("version"),
            "profile_count": len(matcher._profile_items(matcher.CUSTOMER_OUTPUT_PROFILE_DOCUMENT)),
            "profiles": [
                {
                    "profile_id": item.get("profile_id", item.get("authority_section_id", item.get("id"))),
                    "title": item.get("title", item.get("name")),
                    "family_ids": matcher._profile_family_ids(item),
                    "field_ids": matcher._profile_field_ids(item),
                }
                for item in matcher._profile_items(matcher.CUSTOMER_OUTPUT_PROFILE_DOCUMENT)
            ],
        },
        "selections": selections,
    }


def knowledge_catalog() -> dict[str, Any]:
    """Expose the deterministic field catalog as a query-oriented directory."""
    grouped: dict[str, dict[str, Any]] = {}
    for selection in load_catalog()["selections"]:
        family_id = str(selection["family_id"])
        family = grouped.setdefault(family_id, {
            "family_id": family_id,
            "label": selection["family_name"],
            "topics": {},
        })
        for field in selection["fields"]:
            topic_id = str(field.get("group_id", "additional"))
            topic = family["topics"].setdefault(topic_id, {
                "topic_id": topic_id,
                "label": field.get("group_title", topic_id),
                "fields": {},
            })
            canonical_id = str(field["name"])
            topic["fields"].setdefault(canonical_id, {
                "label": str(field.get("label", canonical_id)),
                "canonical_id": canonical_id,
                "unit": field.get("unit"),
                "manual_role": field.get("manual_role"),
                "evidence_boundary": (
                    "formal_evidence_required_for_release" if field.get("formal_evidence_input")
                    else "deterministic_or_user_input; not vendor-final evidence"
                ),
                "aliases": _dedupe([canonical_id, str(field.get("label", "")).strip()]),
                "query_template": f"{selection['family_name']} {field.get('label', canonical_id)} {canonical_id}",
            })
    families = []
    for family in grouped.values():
        topics = []
        for topic in family["topics"].values():
            topics.append({**topic, "fields": sorted(topic["fields"].values(), key=lambda item: item["canonical_id"])})
        families.append({"family_id": family["family_id"], "label": family["label"], "topics": sorted(topics, key=lambda item: item["topic_id"])})
    return {
        "schema": "equipment-design-knowledge-catalog-v1",
        "source_schema": load_catalog()["schema"],
        "families": sorted(families, key=lambda item: item["family_id"]),
    }


def _selection(catalog: dict[str, Any], selection_id: str) -> dict[str, Any]:
    for item in catalog["selections"]:
        if item["selection_id"] == selection_id:
            return item
    raise ValueError(f"未知模块/设备族选择：{selection_id}")


def manual_requirement_status(
    selection: dict[str, Any],
    values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the three manual-input requirement layers without running matching.

    Candidate fields are input-side gaps only: a later deterministic calculation
    may derive them.  Formal evidence fields are reported as evidence inputs, not
    as an assertion that every listed file is simultaneously mandatory.
    """

    supplied = values or {}
    fields = {
        str(field.get("name")): field
        for field in selection.get("fields", [])
        if isinstance(field, dict) and field.get("name")
    }
    contract = selection.get("manual_input_contract", {})

    def present(name: str) -> bool:
        value = supplied.get(name)
        return value is not None and (not isinstance(value, str) or bool(value.strip()))

    def describe(names: list[str]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for name in names:
            field = fields.get(str(name), {"name": name, "label": name})
            rows.append({
                "name": str(name),
                "label": str(field.get("label") or name),
                "unit": field.get("unit"),
                "manual_role": field.get("manual_role"),
                "provided": present(str(name)),
            })
        return rows

    primary = describe(list(contract.get("primary_calculation_required_fields", [])))
    candidate = describe(list(contract.get("candidate_closure_required_fields", [])))
    evidence = describe(list(contract.get("formal_evidence_fields", [])))
    return {
        "schema": "equipment-design-manual-requirement-status-v1",
        "primary_calculation": {
            "required_fields": primary,
            "missing_fields": [row for row in primary if not row["provided"]],
        },
        "candidate_closure": {
            "required_fields": candidate,
            "input_side_gaps": [row for row in candidate if not row["provided"]],
            "fields_may_be_blank": bool(contract.get("candidate_fields_may_be_blank", True)),
            "blank_behavior": contract.get("candidate_blank_behavior"),
        },
        "formal_evidence": {
            "required_for_release": bool(contract.get("formal_release_requires_evidence")),
            "gate": contract.get("formal_evidence_gate"),
            "evidence_input_fields": evidence,
            "provided_fields": [row for row in evidence if row["provided"]],
            "blank_behavior": contract.get("formal_evidence_blank_behavior"),
        },
    }


def clean_record(values: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in values.items():
        if value is None:
            continue
        if isinstance(value, str):
            value = value.strip()
            if value == "":
                continue
        cleaned[str(key)] = value
    return cleaned


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def attach_connection_agent_control(
    result: dict[str, Any],
    connection_component_selections: dict[str, Any],
) -> dict[str, Any]:
    """Close the Agent's downstream component-selection audit.

    The matcher creates the calculate-before-select control before the
    deterministic connection selector runs.  This downstream step records
    the actual selected terminal families without changing any engineering
    calculation, equipment model, or formal evidence gate.
    """

    raw_control = result.get("selection_agent_control")
    if not isinstance(raw_control, dict):
        return result
    control = json.loads(
        json.dumps(raw_control, ensure_ascii=False)
    )
    selected_terminals: list[dict[str, Any]] = []
    connections = connection_component_selections.get("connections", [])
    for connection in connections if isinstance(connections, list) else []:
        if not isinstance(connection, dict):
            continue
        component_types = connection.get("component_types", {})
        if not isinstance(component_types, dict):
            continue
        for component_family, selection in sorted(component_types.items()):
            if not isinstance(selection, dict):
                continue
            terminal = selection.get("terminal_type")
            terminal = terminal if isinstance(terminal, dict) else {}
            selected_terminals.append({
                "connection_id": connection.get("connection_id"),
                "component_family": component_family,
                "status": selection.get("status"),
                "candidate_id": terminal.get("candidate_id"),
                "code": terminal.get("code"),
                "name_zh": terminal.get("name_zh"),
                "minimum_missing_fields": list(
                    selection.get("minimum_missing_fields", [])
                ),
            })
    choice = (
        control.setdefault("ambiguous_choice_resolution", {})
        .setdefault("connection_components", {})
    )
    choice.update({
        "status": (
            "COMPLETED_REGISTERED_DETERMINISTIC_SELECTION"
            if selected_terminals
            else str(
                connection_component_selections.get("status")
                or "NO_APPLICABLE_CONNECTION_TERMINALS"
            )
        ),
        "selection_package_sha256": (
            connection_component_selections.get(
                "selection_package_sha256"
            )
        ),
        "connection_count": len(connections)
        if isinstance(connections, list)
        else 0,
        "selected_terminal_count": len(selected_terminals),
        "selected_terminals": selected_terminals,
        "vendor_model_invention_allowed": False,
    })
    control["agent_control_sha256"] = None
    control.pop("agent_control_sha256", None)
    control["agent_control_sha256"] = _canonical_sha256(control)
    enriched = dict(result)
    enriched["selection_agent_control"] = control
    if isinstance(enriched.get("model_recommendation"), dict):
        enriched["model_recommendation"] = {
            **enriched["model_recommendation"],
            "selection_agent_control_sha256": (
                control["agent_control_sha256"]
            ),
        }
    if isinstance(enriched.get("model_decision"), dict):
        enriched["model_decision"] = {
            **enriched["model_decision"],
            "selection_agent_control_sha256": (
                control["agent_control_sha256"]
            ),
        }
    return enriched


def attach_customer_delivery(result: dict[str, Any]) -> dict[str, Any]:
    """Attach authority-bound overview/datasheet/evidence projections.

    The projection reads the frozen matcher result only.  It performs no
    calculation or model promotion and therefore remains downstream of the
    calculate-before-select chain.
    """
    if result.get("schema") != "equipment-deterministic-match-result-v1":
        return result
    if not isinstance(result.get("design_parameter_package"), dict):
        return result
    enriched = dict(result)
    enriched["customer_delivery"] = customer_delivery.build_customer_delivery(result)
    return enriched


def manual_match(
    selection_id: str,
    values: dict[str, Any],
    *,
    model_estimate_lineage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    catalog = load_catalog()
    selected = _selection(catalog, selection_id)
    record = clean_record(values)
    if selected.get("block_type"):
        record["aspen_block_type"] = selected["block_type"]
    else:
        record["equipment_family"] = selected["family_id"]
    rules, graph = _matcher_runtime_authority()
    result = matcher.match_one(
        record,
        rules,
        graph,
        model_estimate_lineage=model_estimate_lineage,
    )
    derived_service_profile = service_profile.build_manual_service_profile(
        record,
        equipment_id=str(record.get("equipment_tag") or "MANUAL-EQUIPMENT"),
        equipment_family=str(selected.get("family_id") or ""),
        block_type=str(selected.get("block_type") or ""),
    )
    connection_component_selections = connection_selection.build_manual_connection_component_selections(
        record,
        match_result=result,
        equipment_id=str(record.get("equipment_tag") or "MANUAL-EQUIPMENT"),
        block_type=str(selected.get("block_type") or ""),
        service_profile=derived_service_profile,
    )
    derived_service_profile = service_profile.enrich_with_connection_property_facts(
        derived_service_profile,
        connection_component_selections,
    )
    result = attach_connection_agent_control(
        result,
        connection_component_selections,
    )
    result = {
        **result,
        "_aspen_service_profile": derived_service_profile,
        "_aspen_connection_component_selections": connection_component_selections,
        "connection_component_selections": connection_component_selections,
    }
    result = attach_customer_delivery(result)
    return {
        "schema": "equipment-design-app-manual-result-v1",
        "selection": selected,
        "input": record,
        "result": result,
        "service_profile": derived_service_profile,
        "connection_component_selections": connection_component_selections,
        "input_provenance": {
            "status": (
                "MIXED_USER_AND_LLM_PROVISIONAL_ESTIMATES"
                if model_estimate_lineage else "USER_ENTERED_UNVERIFIED"
            ),
            "formal_use": False,
            "model_estimate_fields": sorted(model_estimate_lineage or {}),
        },
        "decision_boundary": "LLM may review or propose allowlisted draft changes; deterministic blockers and evidence/model gates remain authoritative.",
    }


def auto_match(
    values: dict[str, Any],
    *,
    model_estimate_lineage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Match arbitrary partial fields without a prior family/module choice."""
    record = clean_record(values)
    rules, graph = _matcher_runtime_authority()
    result = matcher.match_one(
        record,
        rules,
        graph,
        model_estimate_lineage=model_estimate_lineage,
    )
    derived_service_profile = service_profile.build_manual_service_profile(
        record,
        equipment_id=str(record.get("equipment_tag") or "MANUAL-EQUIPMENT"),
        equipment_family=str(result.get("match", {}).get("family_id") or record.get("equipment_family") or ""),
        block_type=str(record.get("aspen_block_type") or ""),
    )
    connection_component_selections = connection_selection.build_manual_connection_component_selections(
        record,
        match_result=result,
        equipment_id=str(record.get("equipment_tag") or "MANUAL-EQUIPMENT"),
        block_type=str(record.get("aspen_block_type") or ""),
        service_profile=derived_service_profile,
    )
    derived_service_profile = service_profile.enrich_with_connection_property_facts(
        derived_service_profile,
        connection_component_selections,
    )
    result = attach_connection_agent_control(
        result,
        connection_component_selections,
    )
    result = {
        **result,
        "_aspen_service_profile": derived_service_profile,
        "_aspen_connection_component_selections": connection_component_selections,
        "connection_component_selections": connection_component_selections,
    }
    result = attach_customer_delivery(result)
    return {
        "schema": "equipment-design-app-progressive-result-v1",
        "input": record,
        "result": result,
        "service_profile": derived_service_profile,
        "connection_component_selections": connection_component_selections,
        "progress": result.get("progress"),
        "input_provenance": {
            "status": (
                "MIXED_USER_AND_LLM_PROVISIONAL_ESTIMATES"
                if model_estimate_lineage else "USER_ENTERED_UNVERIFIED"
            ),
            "formal_use": False,
            "model_estimate_fields": sorted(model_estimate_lineage or {}),
        },
        "decision_boundary": (
            "Field compatibility generates candidates only. Exact identity or an explicit physical route "
            "is required before family confirmation; LLM and network are not used."
        ),
    }


def com_capability() -> dict[str, Any]:
    on_windows = os.name == "nt"
    win32 = importlib.util.find_spec("win32com") is not None
    pythoncom = importlib.util.find_spec("pythoncom") is not None
    return {
        "available": bool(on_windows and win32 and pythoncom),
        "platform": sys.platform,
        "win32com": win32,
        "pythoncom": pythoncom,
        "optional": True,
        "unavailable_behavior": "manual_and_llm_modes_remain_available",
    }


def skill_entry() -> dict[str, Any]:
    global_skill = PACKAGE_ROOT.parents[1] / "plugins" / "chemical-engineering-skills" / "skills" / "equipment-design-app" / "SKILL.md"
    project_skill = WORKSPACE_ROOT / "skills" / "equipment-design-app" / "SKILL.md"
    return {
        "skill_name": "equipment-design-app",
        "global_skill_path": str(global_skill),
        "global_skill_installed": global_skill.is_file(),
        "project_skill_path": str(project_skill),
        "project_skill_available": project_skill.is_file(),
        "graph_entry": str(PACKAGE_ROOT / "knowledge_graph" / "README.md"),
        "aspen_chain": str(PACKAGE_ROOT / "knowledge_graph" / "aspen_equipment_derivation_chain.md"),
        "prompt": "Use $equipment-design-app to import Aspen equipment data or audit a manual equipment selection through the deterministic knowledge-graph workflow.",
    }


def knowledge_packages() -> dict[str, Any]:
    definitions = [
        {
            "id": "equipment_core",
            "label": "设备设计核心图谱",
            "root": PACKAGE_ROOT / "knowledge_graph",
            "default_selected": True,
            "scope": "17族参数、公式、证据边界与设备设计路由",
            "excluded_subtrees": ["standards_graph"],
            "limitations": "提供方法、规则和当前输入的推导边界；不自动提供项目值或厂家最终型号。",
        },
        {
            "id": "equipment_model_authority",
            "label": "设备型号权威图谱",
            "root": (
                PACKAGE_ROOT / "equipment_selection_graph"
                if (PACKAGE_ROOT / "equipment_selection_graph").is_dir()
                else Path(matcher.GRAPH_PATH).resolve().parent
            ),
            "default_selected": True,
            "scope": "设备族、标准系列、型号状态机和厂家证据门",
            "limitations": "候选不等于正式型号；旧项目型号和跨位号数值不得迁移。",
        },
        {
            "id": "design_standards",
            "label": "设计标准结构化事实与来源锚",
            "root": PACKAGE_ROOT / "knowledge_graph" / "standards_graph",
            "default_selected": False,
            "scope": "24887条标准事实与1844条图关系；量值、单位、适用条件和原记录来源锚；不含原文载体",
            "limitations": "标准方法、部件或命名规则不能替代同设备软件结果和厂家性能证据。",
        },
    ]
    packages = [
        {
            **{key: value for key, value in item.items() if key != "root"},
            "available": item["root"].is_dir(),
            "root": str(item["root"]),
        }
        for item in definitions
    ]
    return {
        "schema": "equipment-design-knowledge-packages-v1",
        "max_selected": 3,
        "max_hits": 20,
        "packages": packages,
        "selection_policy": "allowlisted_local_packages_only",
        "authority_boundary": "retrieval_context_never_overrides_deterministic_state_or_promotes_evidence",
    }


def _selected_knowledge_packages(package_ids: list[str] | None) -> list[dict[str, Any]]:
    registry = knowledge_packages()
    available = {item["id"]: item for item in registry["packages"] if item["available"]}
    selected_ids = package_ids if package_ids is not None else [
        item["id"] for item in registry["packages"] if item["default_selected"] and item["available"]
    ]
    if not isinstance(selected_ids, list) or not selected_ids or not all(isinstance(item, str) for item in selected_ids):
        raise ValueError("knowledge package_ids 必须是非空字符串数组。")
    selected_ids = list(dict.fromkeys(item.strip() for item in selected_ids if item.strip()))
    if len(selected_ids) > int(registry["max_selected"]):
        raise ValueError(f"知识包最多选择 {registry['max_selected']} 个。")
    known_ids = {item["id"] for item in registry["packages"]}
    unknown = sorted(set(selected_ids) - known_ids)
    if unknown:
        raise ValueError(f"未知知识包：{', '.join(unknown)}")
    unavailable = sorted(set(selected_ids) - set(available))
    if unavailable:
        raise ValueError(f"当前运行包不含知识包：{', '.join(unavailable)}")
    return [available[item] for item in selected_ids]


def _knowledge_package_for_source(source_path: str, selected: list[dict[str, Any]]) -> str | None:
    normalized = str(source_path).replace("\\", "/").casefold()
    selected_ids = {item["id"] for item in selected}
    # standards_graph is a distinct opt-in package even though it is physically
    # nested below the core graph directory.
    if "standards_graph/" in normalized:
        return "design_standards" if "design_standards" in selected_ids else None
    for item in selected:
        package_id = item["id"]
        if package_id == "equipment_model_authority" and (
            "设备选型一览表_知识图谱重构_20260712/knowledge_graph/" in normalized
            or "equipment_selection_graph/" in normalized
            or "recovered_equipment_model_authority/knowledge_graph/" in normalized
        ):
            return package_id
        if package_id == "equipment_core" and (
            "设备设计选型工作包/knowledge_graph/" in normalized
            or normalized.startswith("knowledge_graph/")
        ):
            return package_id
    return None


def _asset_bundle_package_selection(
    scope: str,
    package_ids: list[str] | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Resolve asset-bundle coverage without weakening normal search defaults.

    ``knowledge_search`` intentionally keeps its default-selected-package
    behavior.  An implicit ``full_bundle`` request is different: it means all
    packages that the current runtime can actually expose, while still
    reporting registered packages that are absent from this runtime.
    """
    registry = knowledge_packages()
    registered = list(registry.get("packages", []))
    registered_ids = [str(item.get("id", "")) for item in registered]
    if scope == "full_bundle" and package_ids is None:
        selected_ids = [
            str(item["id"])
            for item in registered
            if item.get("available") is True and str(item.get("id", "")).strip()
        ]
        available_by_id = {
            str(item["id"]): item
            for item in registered
            if item.get("available") is True and str(item.get("id", "")).strip()
        }
        selected = [available_by_id[item_id] for item_id in selected_ids]
        unavailable = [
            {
                "id": str(item.get("id", "")),
                "label": item.get("label"),
                "root": item.get("root"),
                "reason": "registered_package_unavailable_in_current_runtime",
            }
            for item in registered
            if item.get("available") is not True
        ]
        definition = {
            "basis": "all_registered_packages",
            "implicit_selection": True,
            "registered_package_ids": registered_ids,
            "selected_available_package_ids": selected_ids,
            "complete_requires": (
                "every registered package available and every allowlisted asset "
                "included without bundle or scan truncation"
            ),
        }
        return selected, unavailable, definition

    selected = _selected_knowledge_packages(package_ids)
    selected_ids = [str(item["id"]) for item in selected]
    definition = {
        "basis": "explicit_selected_packages" if package_ids is not None else "default_selected_packages",
        "implicit_selection": package_ids is None,
        "registered_package_ids": registered_ids,
        "selected_available_package_ids": selected_ids,
        "complete_requires": (
            "every allowlisted in-scope asset in the selected packages included "
            "without bundle or scan truncation"
        ),
    }
    return selected, [], definition


def _read_text_prefix(path: Path, max_chars: int) -> tuple[str, bool]:
    """Read at most ``max_chars + 1`` decoded characters from one asset.

    The boolean is true only when EOF was observed, which lets callers emit a
    full-source hash only for a file that was actually read in full.
    """
    bounded = max(0, int(max_chars))
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        observed = handle.read(bounded + 1)
    return observed[:bounded], len(observed) <= bounded


def _asset_truncation_summary(
    candidates: list[dict[str, Any]],
    start_index: int,
    reason: str,
) -> dict[str, Any] | None:
    remaining = candidates[start_index:]
    if not remaining:
        return None
    return {
        "path": None,
        "reason": reason,
        "remaining_asset_count": len(remaining),
        "first_remaining_path": remaining[0]["bundle_path"],
        "last_remaining_path": remaining[-1]["bundle_path"],
    }


def knowledge_asset_bundle(
    scope: str,
    package_ids: list[str] | None = None,
    *,
    family_id: str | None = None,
    max_chars: int = 1_500_000,
) -> dict[str, Any]:
    """Load allowlisted local KG assets with explicit coverage and truncation metadata."""
    if scope not in {"full_family", "full_bundle"}:
        raise ValueError("knowledge asset bundle scope 只能是 full_family 或 full_bundle。")
    family_id = str(family_id or "").strip()
    if scope == "full_family" and not family_id:
        raise ValueError("full_family 需要确定性 family_id。")
    selected, unavailable_packages, coverage_definition = _asset_bundle_package_selection(
        scope,
        package_ids,
    )
    bounded_max = max(10_000, min(int(max_chars), 5_000_000))
    allowed_suffixes = {".md", ".json", ".csv"}
    family_core_names = {
        "README.md", "00_ERROR_MEMORY.md", "unknowns_router.md",
        "equipment_match_rules.json", "equipment_model_recommendation_rules.json",
        "equipment_parameter_chain_templates.json", "equipment_graph_index.md",
        "formula_family_nodes.md", "parameter_source_nodes.md",
        "evidence_boundary_nodes.md", "manual_decision_gates.md",
    }
    family_core_names_folded = {item.casefold() for item in family_core_names}
    candidates: list[dict[str, Any]] = []
    for package in selected:
        root = Path(package["root"]).resolve()
        excluded = {str(item).casefold() for item in package.get("excluded_subtrees", [])}
        for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
            if not path.is_file() or path.suffix.casefold() not in allowed_suffixes:
                continue
            relative = path.relative_to(root)
            if any(part.casefold() in {"__pycache__", ".git", "scripts"} for part in relative.parts):
                continue
            if relative.parts and relative.parts[0].casefold() in excluded:
                continue
            resolved = path.resolve()
            try:
                resolved.relative_to(root)
            except ValueError:
                continue
            candidates.append({
                "package_id": package["id"],
                "root": root,
                "path": resolved,
                "relative": relative.as_posix(),
                "bundle_path": f"{package['id']}/{relative.as_posix()}",
            })

    assets: list[dict[str, Any]] = []
    truncated_assets: list[dict[str, Any]] = []
    used_chars = 0
    scanned_asset_count = 0
    matched_asset_count = 0
    family_scan_chars = 0
    # Family discovery is separately bounded.  This prevents an opt-in
    # standards tree from being fully scanned merely to discover that most
    # files do not mention the deterministic family id.
    family_scan_max_chars = max(10_000, min(1_000_000, bounded_max * 4))

    def append_asset(candidate: dict[str, Any], content: str, source_complete: bool) -> bool:
        """Append one already-bounded asset; return true when output is exhausted."""
        nonlocal used_chars, matched_asset_count
        remaining = bounded_max - used_chars
        if remaining <= 0:
            return True
        included = content[:remaining]
        emitted_complete = source_complete and len(content) <= remaining
        used_chars += len(included)
        matched_asset_count += 1
        assets.append({
            "package_id": candidate["package_id"],
            "path": candidate["bundle_path"],
            "sha256": hashlib.sha256(included.encode("utf-8")).hexdigest().upper(),
            # A partial asset deliberately has no full-source hash.  Hashing
            # its prefix as though it were the complete source is forbidden.
            "source_file_sha256": (
                hashlib.sha256(content.encode("utf-8")).hexdigest().upper()
                if emitted_complete else None
            ),
            "source_file_sha256_status": (
                "COMPLETE_SOURCE" if emitted_complete else "NOT_EMITTED_PARTIAL_ASSET"
            ),
            "content": included,
            "truncated": not emitted_complete,
            "char_count": len(included),
        })
        if not emitted_complete:
            truncated_assets.append({
                "path": candidate["bundle_path"],
                "reason": f"asset_truncated_at_{remaining}_characters",
            })
        return used_chars >= bounded_max

    family_token = family_id.casefold()
    for index, candidate in enumerate(candidates):
        remaining = bounded_max - used_chars
        if remaining <= 0:
            summary = _asset_truncation_summary(
                candidates,
                index,
                "bundle_character_limit_exhausted",
            )
            if summary:
                truncated_assets.append(summary)
            break

        path = candidate["path"]
        if scope == "full_bundle":
            try:
                content, source_complete = _read_text_prefix(path, remaining)
            except OSError:
                truncated_assets.append({
                    "path": candidate["bundle_path"],
                    "reason": "asset_read_failed",
                })
                continue
            scanned_asset_count += 1
            exhausted = append_asset(candidate, content, source_complete)
            if exhausted:
                summary = _asset_truncation_summary(
                    candidates,
                    index + 1,
                    "bundle_character_limit_exhausted",
                )
                if summary:
                    truncated_assets.append(summary)
                break
            continue

        is_family_core = path.name.casefold() in family_core_names_folded
        if is_family_core:
            try:
                content, source_complete = _read_text_prefix(path, remaining)
            except OSError:
                truncated_assets.append({
                    "path": candidate["bundle_path"],
                    "reason": "asset_read_failed",
                })
                continue
            scanned_asset_count += 1
            exhausted = append_asset(candidate, content, source_complete)
            if exhausted:
                summary = _asset_truncation_summary(
                    candidates,
                    index + 1,
                    "bundle_character_limit_exhausted",
                )
                if summary:
                    truncated_assets.append(summary)
                break
            continue

        scan_remaining = family_scan_max_chars - family_scan_chars
        if scan_remaining <= 0:
            summary = _asset_truncation_summary(
                candidates,
                index,
                "family_content_scan_budget_exhausted",
            )
            if summary:
                truncated_assets.append(summary)
            break
        try:
            scanned_content, scan_complete = _read_text_prefix(path, scan_remaining)
        except OSError:
            truncated_assets.append({
                "path": candidate["bundle_path"],
                "reason": "family_content_scan_read_failed",
            })
            continue
        scanned_asset_count += 1
        family_scan_chars += len(scanned_content)
        family_match = family_token in scanned_content.casefold()
        if not scan_complete and not family_match:
            truncated_assets.append({
                "path": candidate["bundle_path"],
                "reason": "family_content_scan_truncated_before_match_decision",
            })
            summary = _asset_truncation_summary(
                candidates,
                index + 1,
                "family_content_scan_budget_exhausted",
            )
            if summary:
                truncated_assets.append(summary)
            break
        if not family_match:
            continue

        if scan_complete:
            content, source_complete = scanned_content, True
        else:
            # The family token was found inside the bounded scan, but the
            # output itself must still obey the independent bundle limit.
            try:
                content, source_complete = _read_text_prefix(path, remaining)
            except OSError:
                truncated_assets.append({
                    "path": candidate["bundle_path"],
                    "reason": "asset_read_failed_after_family_match",
                })
                continue
        exhausted = append_asset(candidate, content, source_complete)
        if exhausted:
            summary = _asset_truncation_summary(
                candidates,
                index + 1,
                "bundle_character_limit_exhausted",
            )
            if summary:
                truncated_assets.append(summary)
            break

    coverage_complete = bool(assets) and not truncated_assets and not unavailable_packages
    return {
        "schema": "equipment-design-knowledge-asset-bundle-v1",
        "status": "PASS_FULL_ASSET_BUNDLE" if assets else "NO_ASSETS",
        "scope": scope,
        "family_id": family_id or None,
        "selected_packages": [item["id"] for item in selected],
        "unavailable_packages": unavailable_packages,
        "coverage_definition": coverage_definition,
        "coverage_status": "COMPLETE" if coverage_complete else "PARTIAL",
        "assets": assets,
        "truncated_assets": truncated_assets,
        "char_count": used_chars,
        "max_chars": bounded_max,
        "asset_count": len(assets),
        "candidate_asset_count": len(candidates),
        "scanned_asset_count": scanned_asset_count,
        "matched_asset_count": matched_asset_count,
        "family_scan_chars": family_scan_chars if scope == "full_family" else None,
        "family_scan_max_chars": family_scan_max_chars if scope == "full_family" else None,
    }


def _search_terms(query: str) -> list[str]:
    terms = re.findall(r"[A-Za-z][A-Za-z0-9_.+/-]*|\d+(?:\.\d+)*|[\u3400-\u9fff]{2,}", query)
    return list(dict.fromkeys(term.strip() for term in terms if term.strip()))[:12] or [query]


def _compact_excerpt(text: str, terms: list[str], width: int = 360) -> str:
    compact = re.sub(r"\s+", " ", str(text)).strip()
    folded = compact.casefold()
    positions = [folded.find(term.casefold()) for term in terms]
    positions = [position for position in positions if position >= 0]
    if not positions:
        return compact[:width] + ("…" if len(compact) > width else "")
    start = max(0, min(positions) - width // 3)
    end = min(len(compact), start + width)
    return ("…" if start else "") + compact[start:end] + ("…" if end < len(compact) else "")


def _standards_sqlite_search(query: str, limit: int, root: Path) -> list[dict[str, Any]]:
    """Query the compact standards authority carrier without loading render PNGs."""
    from projected_standard_store import search_facts
    return search_facts(PACKAGE_ROOT, query, limit)


def _original_standards_sqlite_search(query: str, limit: int, root: Path) -> list[dict[str, Any]]:
    """Preserved original full-text carrier reader; not the backend projection route."""
    authority = standards_database_verification()
    database = PACKAGE_ROOT / Path(authority["relative_path"])
    registered_standards_root = database.parent.parent.parent
    if registered_standards_root.resolve() != root.resolve():
        raise database_authority.DatabaseAuthorityError(
            "selected standards root does not match the registered RAG database"
        )
    if not database.is_file():
        raise database_authority.DatabaseAuthorityError(
            "registered standards RAG database is missing"
        )
    terms = _search_terms(query)
    bounded_limit = max(1, min(int(limit), 20))
    like_values = [f"%{term}%" for term in terms]
    scope_queries = [
        {
            "scope": "chunk",
            "id": "c.chunk_id",
            "page": "c.page_start",
            "text": "c.text",
            "from": "chunks c JOIN documents d ON d.doc_id=c.doc_id",
            "where": " OR ".join("c.text LIKE ?" for _ in terms),
            "asset": "NULL",
            "location": "c.location_status",
        },
        {
            "scope": "table",
            "id": "t.table_id",
            "page": "t.page_1based",
            "text": "COALESCE(t.caption,'') || char(10) || COALESCE(t.cell_text,'')",
            "from": "tables_data t JOIN documents d ON d.doc_id=t.doc_id",
            "where": " OR ".join("(COALESCE(t.caption,'') || char(10) || COALESCE(t.cell_text,'')) LIKE ?" for _ in terms),
            "asset": "t.csv_path",
            "location": "'table_bbox_available'",
        },
        {
            "scope": "figure",
            "id": "f.figure_id",
            "page": "f.page_1based",
            "text": "COALESCE(f.caption,'')",
            "from": "figures_data f JOIN documents d ON d.doc_id=f.doc_id",
            "where": " OR ".join("COALESCE(f.caption,'') LIKE ?" for _ in terms),
            "asset": "f.image_path",
            "location": "'figure_bbox_metadata_only'",
        },
        {
            "scope": "formula",
            "id": "q.formula_id",
            "page": "q.page_1based",
            "text": "COALESCE(q.label,'') || char(10) || COALESCE(q.caption,'') || char(10) || COALESCE(q.raw_text,'')",
            "from": "formulas_data q JOIN documents d ON d.doc_id=q.doc_id",
            "where": " OR ".join("(COALESCE(q.label,'') || char(10) || COALESCE(q.caption,'') || char(10) || COALESCE(q.raw_text,'')) LIKE ?" for _ in terms),
            "asset": "q.image_path",
            "location": "'formula_bbox_metadata_only'",
        },
    ]
    rows: list[dict[str, Any]] = []
    uri = f"file:{database.resolve().as_posix()}?mode=ro"
    try:
        # sqlite3.Connection's context manager commits/rolls back but does not
        # close the handle.  Explicitly close it so repeated Agent/GUI graph
        # queries cannot leak frozen-bundle file descriptors.
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            connection.row_factory = sqlite3.Row
            for definition in scope_queries:
                statement = f"""
                    SELECT {definition['id']} AS record_id,
                           {definition['page']} AS page_1based,
                           {definition['text']} AS searchable_text,
                           {definition['asset']} AS logical_asset_path,
                           {definition['location']} AS location_status,
                           d.doc_id, d.relative_path AS document_path,
                           d.source_pdf_sha256, d.family, d.source_kind,
                           d.evidence_default, d.package_status
                    FROM {definition['from']}
                    WHERE {definition['where']}
                    LIMIT ?
                """
                for item in connection.execute(statement, [*like_values, bounded_limit * 3]):
                    text = str(item["searchable_text"] or "")
                    folded = text.casefold()
                    score = sum(2 if term.casefold() in folded else 0 for term in terms)
                    scope = str(definition["scope"])
                    logical_asset = str(item["logical_asset_path"] or "")
                    packaged_asset = None
                    if scope == "table" and logical_asset:
                        packaged_asset = (
                            f"knowledge_graph/standards_graph/source_layer/documents/"
                            f"{item['doc_id']}/{logical_asset.replace(chr(92), '/')}"
                        )
                    source_kind = str(item["source_kind"] or "")
                    package_status = str(item["package_status"] or "")
                    if scope in {"figure", "formula"}:
                        reuse_boundary = "routing_metadata_only; visual crop excluded from compact runtime bundle"
                    elif package_status != "PASS":
                        reuse_boundary = "review_required_before_quote_or_design_reuse"
                    elif source_kind in {"design_book", "handbook", "course_design", "case"}:
                        reuse_boundary = "method_or_routing_only; no_project_value_transfer"
                    else:
                        reuse_boundary = "source_evidence; applicability_and_clause_or_cell_check_required"
                    rows.append({
                        "score": max(1, score),
                        "package_id": "design_standards",
                        "source": "standards_sqlite_authority",
                        "scope": scope,
                        "record_id": item["record_id"],
                        "doc_id": item["doc_id"],
                        "path": f"standards_sqlite/{item['doc_id']}/{scope}/{item['record_id']}",
                        "line": int(item["page_1based"] or 0),
                        "page_1based": int(item["page_1based"] or 0),
                        "document_path": item["document_path"],
                        "source_pdf_sha256": item["source_pdf_sha256"],
                        "family": item["family"],
                        "source_kind": source_kind,
                        "evidence_default": item["evidence_default"],
                        "package_status": package_status,
                        "location_status": item["location_status"],
                        "logical_asset_path": logical_asset or None,
                        "packaged_asset_path": packaged_asset,
                        "render_asset_in_bundle": scope not in {"figure", "formula"},
                        "reuse_boundary": reuse_boundary,
                        "text": _compact_excerpt(text, terms),
                    })
    except (sqlite3.Error, OSError) as exc:
        raise database_authority.DatabaseAuthorityError(
            f"registered standards RAG query failed: {exc}"
        ) from exc
    rows.sort(key=lambda item: (-int(item["score"]), str(item["path"])))
    return rows[:bounded_limit]


def knowledge_search(query: str, limit: int = 8, package_ids: list[str] | None = None) -> dict[str, Any]:
    query = str(query).strip()[:500]
    if not query:
        return {"status": "EMPTY_QUERY", "text": ""}
    selected = _selected_knowledge_packages(package_ids)
    selected_ids = [item["id"] for item in selected]
    bounded_limit = max(1, min(int(limit), 20))
    vector_query_candidates = (
        WORKSPACE_ROOT / "scripts" / "query_workspace_vectors.py",
        WORKSPACE_ROOT / "workspace_support" / "scripts" / "query_workspace_vectors.py",
    )
    script = next(
        (candidate for candidate in vector_query_candidates if candidate.is_file()),
        vector_query_candidates[0],
    )
    if script.is_file() and not FROZEN_ROOT:
        try:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    query,
                    "--limit",
                    "20",
                    "--json",
                ],
                cwd=str(WORKSPACE_ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {"status": "TIMEOUT", "text": "知识图谱检索超过 30 秒。"}
        if completed.returncode == 0 and completed.stdout.strip():
            try:
                vector_hits = json.loads(completed.stdout)
            except json.JSONDecodeError:
                vector_hits = None
            if isinstance(vector_hits, list) and all(isinstance(item, dict) for item in vector_hits):
                filtered_hits: list[dict[str, Any]] = []
                for item in vector_hits:
                    package_id = _knowledge_package_for_source(str(item.get("source_path", "")), selected)
                    if package_id:
                        filtered_hits.append({"package_id": package_id, **item})
                    if len(filtered_hits) >= bounded_limit:
                        break
                if filtered_hits:
                    return {
                        "status": "PASS_VECTOR_INDEX",
                        "returncode": completed.returncode,
                        "text": "\n".join(
                            f"[{item.get('source_path', 'unknown')}] {item.get('title', '')}" for item in filtered_hits
                        ),
                        "stderr": completed.stderr.strip(),
                        "result_count": len(filtered_hits),
                        "mode": "deterministic_workspace_vector_index",
                        "selected_packages": selected_ids,
                        "hits": [
                            {"rank": index + 1, "source": "workspace_vector_index", **item}
                            for index, item in enumerate(filtered_hits)
                        ],
                        "limitations": [item["limitations"] for item in selected],
                    }

    terms = [part.casefold() for part in query.replace("，", " ").replace(",", " ").split() if part]
    if not terms:
        terms = [query.casefold()]
    standards_hits: list[dict[str, Any]] = []
    standards_authority: dict[str, Any] = {"status": "NOT_SELECTED"}
    for item in selected:
        if item["id"] == "design_standards":
            try:
                standards_hits = _standards_sqlite_search(
                    query,
                    bounded_limit,
                    Path(item["root"]),
                )
                verified = standards_database_verification()
                standards_authority = {
                    "status": verified["status"],
                    "database_id": verified["database_id"],
                    "relative_path": verified["relative_path"],
                    "sha256": verified["sha256"],
                    "scope_status": verified["scope_status"],
                }
            except database_authority.DatabaseAuthorityError as exc:
                standards_authority = {
                    "status": "BLOCKED_DATABASE_AUTHORITY",
                    "error": str(exc),
                }
            break
    search_roots = [
        (item["id"], Path(item["root"]))
        for item in selected
        if item["id"] != "design_standards" or not standards_hits
    ]
    candidates: list[tuple[int, str, str, int, str]] = []
    seen_roots: set[Path] = set()
    for package_id, root in search_roots:
        resolved_root = root.resolve()
        if resolved_root in seen_roots:
            continue
        seen_roots.add(resolved_root)
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in {".md", ".json", ".csv"}:
                continue
            if package_id == "equipment_core":
                try:
                    relative_to_package = path.relative_to(root)
                except ValueError:
                    continue
                if relative_to_package.parts and relative_to_package.parts[0].casefold() == "standards_graph":
                    continue
            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            try:
                relative = path.relative_to(PACKAGE_ROOT).as_posix()
            except ValueError:
                relative = f"{package_id}/{path.relative_to(root).as_posix()}"
            filename = relative.casefold()
            for line_no, line in enumerate(lines, 1):
                compact = line.strip()
                if not compact:
                    continue
                haystack = f"{filename} {compact.casefold()}"
                score = sum(2 if term in compact.casefold() else 1 if term in filename else 0 for term in terms)
                if score:
                    candidates.append((score, package_id, relative, line_no, compact[:360]))
    candidates.sort(key=lambda row: (-row[0], row[2], row[3]))
    rows = candidates[:bounded_limit]
    local_hits = [
        {"score": score, "package_id": package_id, "path": path, "line": line_no, "text": line}
        for score, package_id, path, line_no, line in rows
    ]
    combined_hits = sorted(
        [*standards_hits, *local_hits],
        key=lambda item: (-int(item.get("score", 0)), str(item.get("path", ""))),
    )[:bounded_limit]
    text_result = "\n".join(
        f"[{item.get('path')}:{item.get('line', 0)}] {item.get('text', '')}"
        for item in combined_hits
    )
    return {
        "status": "PASS_BUNDLED_GRAPH" if combined_hits else "NO_MATCH",
        "text": text_result,
        "query_terms": terms,
        "result_count": len(combined_hits),
        "mode": (
            "deterministic_standards_sqlite_and_local_search"
            if standards_hits else "deterministic_local_search"
        ),
        "selected_packages": selected_ids,
        "standards_database_authority": standards_authority,
        "limitations": [item["limitations"] for item in selected],
        "hits": [
            {"rank": index + 1, **item}
            for index, item in enumerate(combined_hits)
        ],
    }


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
