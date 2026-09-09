from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

from equipment_calc import (
    cylinder_calc_thickness,
    design_pressure,
    ellipsoidal_head_calc_thickness,
    membrane_area_m2,
    pipe_actual_velocity,
    pipe_required_diameter,
    pressure_ratio,
    pump_hydraulic_power_kw,
    pump_shaft_power_kw,
    tower_bottom_liquid_height,
)


SCRIPT_PATH = Path(__file__).resolve()
FROZEN_ROOT = getattr(sys, "_MEIPASS", None)
if FROZEN_ROOT:
    PACKAGE_ROOT = Path(FROZEN_ROOT).resolve()
    WORKSPACE_ROOT = PACKAGE_ROOT
else:
    PACKAGE_ROOT = SCRIPT_PATH.parents[1]
    WORKSPACE_ROOT = PACKAGE_ROOT
RULES_PATH = PACKAGE_ROOT / "knowledge_graph" / "equipment_match_rules.json"
MODEL_RULES_PATH = PACKAGE_ROOT / "knowledge_graph" / "equipment_model_recommendation_rules.json"
PARAMETER_TEMPLATES_PATH = PACKAGE_ROOT / "knowledge_graph" / "equipment_parameter_chain_templates.json"
CUSTOMER_OUTPUT_PROFILES_PATH = PACKAGE_ROOT / "knowledge_graph" / "equipment_customer_output_profiles.json"
PUMP_STANDARD_POINTS_PATH = PACKAGE_ROOT / "data" / "pump_gbt5662_2013_design_points.csv"
PIPE_STANDARD_DN_OD_PATH = PACKAGE_ROOT / "data" / "pipe_gbt12459_2025_dn_od_catalog.csv"
INPUT_SCHEMA_PATH = PACKAGE_ROOT / "knowledge_graph" / "equipment_match_input.schema.json"
_GRAPH_PATH_CANDIDATES = (
    PACKAGE_ROOT
    / "equipment_selection_graph"
    / "equipment_selection_graph_v2.json",
    WORKSPACE_ROOT
    / "设备选型一览表_知识图谱重构_20260712"
    / "knowledge_graph"
    / "equipment_selection_graph_v2.json",
    WORKSPACE_ROOT
    / "recovered_equipment_model_authority"
    / "knowledge_graph"
    / "equipment_selection_graph_v2.json",
)
GRAPH_PATH = next(
    (candidate for candidate in _GRAPH_PATH_CANDIDATES if candidate.is_file()),
    _GRAPH_PATH_CANDIDATES[1],
)
SOURCE_LAYER_DOCUMENTS = (
    PACKAGE_ROOT
    / "knowledge_graph"
    / "standards_graph"
    / "source_layer"
    / "documents"
)
ENGINE_VERSION = "2.4.0"
PASS_WORDS = {"pass", "passed", "通过", "合格", "true", "1", "yes"}
APPROVED_WORDS = {"approved", "通过", "批准", "accepted", "final"}
PRESSURE_BASIS_WORDS = {
    "absolute": {"absolute", "abs", "绝压", "绝对压力"},
    "gauge": {"gauge", "gage", "g", "表压", "相对压力"},
}
PHASE_WORDS = {
    "liquid": {"liquid", "liq", "液体", "液相", "水相", "油相"},
    "vapor": {"gas", "vapor", "vapour", "vap", "气体", "气相", "蒸汽"},
    "mixed": {"mixed", "two phase", "two-phase", "multiphase", "混合", "两相", "多相"},
    "solid": {"solid", "固体", "固相", "slurry", "浆液"},
}
PHASE_WORDS["mixed"].update({"slurry", "suspension", "浆液"})
PHASE_WORDS["solid"].difference_update({"slurry", "浆液"})
HEAD_TYPE_WORDS = {
    "2:1_ellipsoidal": {
        "2:1_ellipsoidal", "2:1 ellipsoidal", "2:1 elliptical",
        "2比1椭圆封头", "2:1椭圆封头", "标准椭圆封头",
    },
}
MEMBRANE_GEOMETRY_TYPE_WORDS = {
    "cylindrical_channels": {
        "cylindrical_channels", "cylindrical channels", "tubular channels",
        "tubular", "圆柱通道", "圆管通道", "管式通道", "中空纤维圆柱通道",
    },
    # These are valid membrane construction descriptions but do not share the
    # cylindrical-channel area identity implemented below.  Keeping them as
    # recognized canonical branches lets the calculation layer return an
    # explicit unsupported-formula gate instead of misclassifying good input
    # text as malformed data.
    "spiral_wound": {
        "spiral_wound", "spiral wound", "spiral-wound", "卷式", "螺旋卷式",
    },
    "hollow_fiber": {
        "hollow_fiber", "hollow fiber", "hollow-fiber", "中空纤维",
    },
    "flat_sheet": {
        "flat_sheet", "flat sheet", "flat-sheet", "平板膜", "平板式",
    },
}
VOLUME_BASIS_WORDS = {
    "nominal_total": {"nominal_total", "nominal total", "名义总容积", "选定总容积"},
    "effective_working": {"effective_working", "effective working", "有效工作容积", "工作容积"},
    "geometric_total": {"geometric_total", "geometric total", "几何总容积"},
}
NPSHR_EVIDENCE_SCOPE_WORDS = {
    "same_duty_vendor_curve": {
        "same_duty_vendor_curve", "same duty vendor curve",
        "同工况厂家曲线", "同流量转速介质厂家曲线",
    },
}
COMPATIBLE_FAMILY_PAIRS = {
    frozenset({"family_fixed_tubesheet_exchanger", "family_other_heat_exchanger"})
}
GENERAL_FAMILY_GROUPS = {
    frozenset({"family_fixed_tubesheet_exchanger", "family_other_heat_exchanger"}):
        "family_other_heat_exchanger",
}

# One authoritative dependency table is shared by calculation execution,
# catalog generation, progressive candidate diagnosis, and minimum-missing
# analysis.  The matcher remains deterministic and has no LLM/network path.
CALCULATION_REQUIREMENTS: dict[str, tuple[str, ...]] = {
    "pump_head_from_pressure": ("inlet_pressure_mpa", "outlet_pressure_mpa", "density_kg_m3", "pressure_basis"),
    "pump_hydraulic_power": ("flow_m3_h", "head_m", "density_kg_m3"),
    "pump_shaft_power": ("flow_m3_h", "head_m", "efficiency_percent", "density_kg_m3"),
    "pump_cavitation_margin": ("npsha_m", "npshr_m"),
    "valve_pressure_drop_from_streams": ("inlet_pressure_mpa", "outlet_pressure_mpa", "pressure_basis"),
    "valve_liquid_equivalent_cv_screening": ("flow_m3_h", "density_kg_m3", "pressure_drop_kpa"),
    "valve_maximum_pressure_drop_screening": ("pressure_drop_kpa", "maximum_pressure_drop_factor"),
    "liquid_turbine_pressure_head": ("inlet_pressure_mpa", "outlet_pressure_mpa", "density_kg_m3", "pressure_basis"),
    "liquid_turbine_hydraulic_power": ("flow_m3_h", "inlet_pressure_mpa", "outlet_pressure_mpa", "pressure_basis"),
    "liquid_turbine_shaft_power": ("pressure_drop_power_component_kw", "efficiency_percent"),
    "pressure_ratio": ("inlet_pressure_mpa", "outlet_pressure_mpa", "pressure_basis"),
    "compressor_isentropic_shaft_power": (
        "flow_m3_h", "inlet_pressure_mpa", "outlet_pressure_mpa",
        "pressure_basis", "heat_capacity_ratio_k", "efficiency_percent",
    ),
    "compressor_total_power": (
        "shaft_power_kw", "driver_efficiency_percent", "auxiliary_power_fraction",
    ),
    "pipe_required_diameter": ("flow_m3_h", "target_velocity_m_s"),
    "pipe_standard_dn_selection": ("required_inner_diameter_mm", "selected_wall_thickness_mm"),
    "pipe_actual_velocity": ("flow_m3_h", "selected_outer_diameter_mm", "selected_wall_thickness_mm"),
    "design_pressure_basis_conversion": ("design_pressure_mpa", "design_pressure_basis", "atmospheric_pressure_mpa"),
    "design_pressure": ("operating_pressure_mpa", "design_pressure_factor", "pressure_basis"),
    "cylinder_thickness": ("design_pressure_mpa", "design_pressure_basis", "inner_diameter_mm", "allowable_stress_mpa", "weld_efficiency"),
    "head_thickness": ("design_pressure_mpa", "design_pressure_basis", "inner_diameter_mm", "allowable_stress_mpa", "weld_efficiency", "head_type"),
    "tower_preliminary_diameter": ("flow_m3_h", "tower_design_velocity_m_s"),
    "tower_tray_spacing": ("inner_diameter_mm",),
    "tower_cross_section": ("inner_diameter_mm",),
    "tower_active_area_fraction": ("tower_downcomer_area_fraction", "tower_receiving_area_fraction", "tower_inactive_area_fraction"),
    "tower_active_area": ("tower_cross_section_m2", "tower_active_area_fraction"),
    "tower_hole_area": ("tower_active_area_m2", "tower_open_area_fraction"),
    "tower_actual_superficial_velocity": ("flow_m3_h", "tower_active_area_m2"),
    "tower_preliminary_height": ("stage_count", "tray_spacing_mm", "tower_top_bottom_allowance_mm"),
    "tower_bottom_liquid_height": ("flow_m3_h", "retention_time_min", "inner_diameter_mm"),
    "cylinder_volume": ("inner_diameter_mm", "straight_shell_length_mm"),
    "storage_required_volume": ("flow_m3_h", "retention_time_min", "fill_fraction"),
    "membrane_area": ("membrane_geometry_type", "element_count", "channel_count", "channel_inner_diameter_mm", "element_length_m"),
    "heater_sensible_duty_screening": ("mass_flow_kg_h", "specific_heat_kj_kgk", "inlet_temperature_c", "outlet_temperature_c"),
    "exchanger_area": ("heat_duty_kw", "overall_u_w_m2k", "lmtd_k", "lmtd_correction_factor"),
    "exchanger_tube_count": ("heat_transfer_area_m2", "tube_outer_diameter_mm", "tube_length_mm"),
    "tower_internal_height": ("stage_count", "tray_spacing_mm"),
    "crystallizer_working_volume": ("slurry_flow_m3_h", "retention_time_min"),
    "filter_area_from_cake_flux": ("solids_feed_kg_h", "filtration_flux_kg_m2_h"),
    "dryer_water_evaporation": ("water_component_mapping", "inlet_water_kg_h", "outlet_water_kg_h"),
    "dryer_specific_duty": ("heat_duty_kw", "evaporation_rate_kg_h"),
}

BLOCK_TYPE_CALCULATION_RULES: dict[str, tuple[str, ...]] = {
    "CRYSTALLIZER": ("crystallizer_working_volume",),
    "FILTER": ("filter_area_from_cake_flux",),
    "DRYER": ("dryer_water_evaporation", "dryer_specific_duty"),
}

CALCULATION_OUTPUT_FIELDS: dict[str, str] = {
    "pump_head_from_pressure": "head_m",
    "pump_hydraulic_power": "hydraulic_power_kw",
    "pump_shaft_power": "shaft_power_kw",
    "pump_cavitation_margin": "cavitation_margin_m",
    "valve_pressure_drop_from_streams": "pressure_drop_kpa",
    "valve_liquid_equivalent_cv_screening": "cv",
    "valve_maximum_pressure_drop_screening": "maximum_pressure_drop_kpa",
    "liquid_turbine_pressure_head": "pressure_drop_head_component_m",
    "liquid_turbine_hydraulic_power": "pressure_drop_power_component_kw",
    "liquid_turbine_shaft_power": "pressure_component_shaft_power_screening_kw",
    "compressor_isentropic_shaft_power": "shaft_power_kw",
    "compressor_total_power": "total_power_kw",
    "pipe_required_diameter": "required_inner_diameter_mm",
    "pipe_standard_dn_selection": "selected_dn",
    "pipe_actual_velocity": "actual_velocity_m_s",
    "design_pressure_basis_conversion": "design_pressure_mpa",
    "design_pressure": "design_pressure_mpa",
    "cylinder_thickness": "cylinder_calculated_thickness_mm",
    "head_thickness": "head_calculated_thickness_mm",
    "tower_preliminary_diameter": "inner_diameter_mm",
    "tower_tray_spacing": "tray_spacing_mm",
    "tower_cross_section": "tower_cross_section_m2",
    "tower_active_area_fraction": "tower_active_area_fraction",
    "tower_active_area": "tower_active_area_m2",
    "tower_hole_area": "tower_hole_area_m2",
    "tower_actual_superficial_velocity": "tower_actual_superficial_velocity_m_s",
    "tower_preliminary_height": "height_mm",
    "tower_bottom_liquid_height": "bottom_liquid_height_m",
    "cylinder_volume": "straight_shell_geometric_volume_m3",
    "storage_required_volume": "required_volume_m3",
    "membrane_area": "membrane_area_m2",
    "heater_sensible_duty_screening": "heat_duty_kw",
    "exchanger_area": "heat_transfer_area_m2",
    "exchanger_tube_count": "tube_or_plate_count",
    "tower_internal_height": "tower_internal_height_m",
    "crystallizer_working_volume": "working_volume_m3",
    "filter_area_from_cake_flux": "filter_area_m2",
    "dryer_water_evaporation": "evaporation_rate_kg_h",
    "dryer_specific_duty": "specific_drying_duty_kj_kg",
}

# Formula release policy. Class A is an exact
# identity/geometry/energy relation on its stated basis.  Class B contains a
# design branch or screening assumption and is capped at provisional use. The
# registered fallback layer may supply explicit J/default inputs; their lineage
# is propagated through every dependent formula and can never promote a formal
# model. The
# user-facing notice is mandatory for both classes because the value was
# generated by this application rather than read directly from Aspen/user data.
CALCULATION_POLICIES: dict[str, dict[str, Any]] = {
    "pump_head_from_pressure": {
        "formula_id": "B_PUMP_PRESSURE_HEAD",
        "release_class": "B",
        "evidence_class": "J",
        "result_status": "PROVISIONAL",
        "title": "压差折算压头，不是完整系统总扬程",
        "message": "该结果仅为压力头分量；位差、速度头和管路损失未由本式闭合。",
        "applicability": "单相液体、同一压力基准；只有其余扬程分量已包含或可忽略时，才可用于总扬程初筛。",
        "does_not_prove": ["total_pump_head", "vendor_duty_point", "final_model"],
        "promotion_cap": "TYPE_SCREENING",
        "source_refs": ["knowledge_graph/formula_family_nodes.md#formula_pressure_head_rise"],
    },
    "pump_hydraulic_power": {
        "formula_id": "A_PUMP_HYDRAULIC_POWER",
        "release_class": "A",
        "evidence_class": "D",
        "result_status": "DERIVED",
        "title": "水力功率由内置能量式计算",
        "message": "密度、实际体积流量和总扬程必须来自同一工况；本式不含效率。",
        "applicability": "单相液体，H 为总扬程；不得默认水密度。",
        "does_not_prove": ["shaft_power", "motor_power", "vendor_model"],
        "promotion_cap": "DERIVED_PARAMETER",
        "source_refs": ["knowledge_graph/formula_family_nodes.md#formula_pump_hydraulic_power"],
    },
    "pump_shaft_power": {
        "formula_id": "A_PUMP_SHAFT_POWER",
        "release_class": "A",
        "evidence_class": "D",
        "result_status": "DERIVED",
        "title": "轴功率由显式效率折算",
        "message": "优先使用用户或同工况效率；若使用登记的最终保底效率，本结果自动降为 J/provisional 并保留敏感性警告。",
        "applicability": "单相液体，0 < η ≤ 100%，H 为总扬程。",
        "does_not_prove": ["motor_rating", "bep_match", "vendor_model"],
        "promotion_cap": "DERIVED_PARAMETER",
        "source_refs": ["knowledge_graph/formula_family_nodes.md#formula_pump_shaft_power"],
    },
    "pump_cavitation_margin": {
        "formula_id": "A_PUMP_CAVITATION_DIFFERENCE",
        "release_class": "A",
        "evidence_class": "D",
        "result_status": "DERIVED",
        "title": "NPSH 差值由内置恒等式计算",
        "message": "正差值不自动等于汽蚀校核通过，仍需同工况厂家 NPSHr 和规定裕量。",
        "applicability": "NPSHa 与 NPSHr 必须属于同一流量、转速、介质和基准。",
        "does_not_prove": ["cavitation_pass", "vendor_curve_pass"],
        "promotion_cap": "DERIVED_PARAMETER",
        "source_refs": ["knowledge_graph/formula_family_nodes.md#formula_NPSHa"],
    },
    "valve_pressure_drop_from_streams": {
        "formula_id": "A_VALVE_PRESSURE_DROP_FROM_STREAMS",
        "release_class": "A",
        "evidence_class": "D",
        "result_status": "DERIVED",
        "title": "阀门正常压差由同基准进出口压力计算",
        "message": "本式只闭合正常工况压差；最大压差、关断压差和事故工况需另行定义。",
        "applicability": "同一工况、同一压力基准且 Pin>Pout。",
        "does_not_prove": ["maximum_pressure_drop", "shutoff_pressure", "cavitation_pass", "final_model"],
        "promotion_cap": "DERIVED_PARAMETER",
        "source_refs": ["knowledge_graph/formula_family_nodes.md#formula_valve_pressure_drop"],
    },
    "valve_liquid_equivalent_cv_screening": {
        "formula_id": "B_VALVE_LIQUID_EQUIVALENT_CV_SCREENING",
        "release_class": "B",
        "evidence_class": "J",
        "result_status": "PROVISIONAL",
        "title": "阀门液体等效 Cv 初筛",
        "message": "液相时可作不可压缩液体 Cv 初筛；气相、闪蒸或两相时仅是液体等效占位量，不能替代可压缩流体/阻塞流正式计算。",
        "applicability": "Q 为实际 m3/h、rho 为同工况 kg/m3、dP>0；气体和两相必须保留厂家/适用标准正式计算门。",
        "does_not_prove": ["gas_valve_cv", "choked_flow_pass", "flashing_pass", "cavitation_pass", "noise_pass", "final_model"],
        "promotion_cap": "TYPE_SCREENING",
        "source_refs": ["knowledge_graph/formula_family_nodes.md#formula_valve_cv_screening"],
    },
    "valve_maximum_pressure_drop_screening": {
        "formula_id": "B_VALVE_MAXIMUM_PRESSURE_DROP_SCREENING",
        "release_class": "B",
        "evidence_class": "J",
        "result_status": "PROVISIONAL",
        "title": "阀门最大压差登记裕量初筛",
        "message": "最大压差由正常压差乘登记裕量系数生成，只用于预设计一览表；关断、事故和联锁工况仍需项目确认。",
        "applicability": "正常压差已闭合且最大压差系数为显式输入或登记的可追溯保底值。",
        "does_not_prove": ["shutoff_pressure", "actuator_thrust", "cavitation_pass", "final_model"],
        "promotion_cap": "TYPE_SCREENING",
        "source_refs": ["knowledge_graph/equipment_customer_output_profiles.json#X05"],
    },
    "liquid_turbine_pressure_head": {
        "formula_id": "B_LIQUID_TURBINE_PRESSURE_DROP_HEAD_COMPONENT",
        "release_class": "B",
        "evidence_class": "J",
        "result_status": "PROVISIONAL",
        "title": "液体透平压差水头分量初筛",
        "message": "仅由压差和密度折算压力水头；速度头、位差和管路损失尚未闭合。",
        "applicability": "不可压缩液体、同一压力基准、Pin>Pout 且密度为同工况值。",
        "does_not_prove": ["total_available_head", "cavitation_pass", "vendor_duty_point", "final_model"],
        "promotion_cap": "TYPE_SCREENING",
        "source_refs": ["knowledge_graph/formula_family_nodes.md#formula_liquid_power_recovery"],
    },
    "liquid_turbine_hydraulic_power": {
        "formula_id": "B_LIQUID_TURBINE_PRESSURE_DROP_POWER_COMPONENT",
        "release_class": "B",
        "evidence_class": "J",
        "result_status": "PROVISIONAL",
        "title": "液体透平压差功率分量初筛",
        "message": "ΔP·Q 只闭合压力功分量；进出口速度头与位差尚未计入，不能称为总可回收水力功率。",
        "applicability": "不可压缩液体、同一稳定工况且 Pin>Pout；仅当速度头和位差已另行闭合或可忽略时才可接近总水力功率。",
        "does_not_prove": ["total_hydraulic_power", "recoverable_shaft_power", "generator_power", "vendor_model"],
        "promotion_cap": "TYPE_SCREENING",
        "source_refs": ["knowledge_graph/formula_family_nodes.md#formula_liquid_power_recovery"],
    },
    "liquid_turbine_shaft_power": {
        "formula_id": "B_LIQUID_TURBINE_SHAFT_POWER_FROM_PRESSURE_COMPONENT",
        "release_class": "B",
        "evidence_class": "J",
        "result_status": "PROVISIONAL",
        "title": "由压差功率分量折算的轴功率初筛",
        "message": "优先使用显式效率；若使用登记的最终保底效率，本结果仍不是完整轴系或发电功率。",
        "applicability": "0 < η ≤ 100%，且上游压差功率分量成立；速度头、位差、机械与发电机损失仍需另行闭合。",
        "does_not_prove": ["total_recoverable_shaft_power", "generator_rating", "off_design_curve", "vendor_model"],
        "promotion_cap": "TYPE_SCREENING",
        "source_refs": ["knowledge_graph/formula_family_nodes.md#formula_liquid_power_recovery"],
    },
    "pressure_ratio": {
        "formula_id": "A_PRESSURE_RATIO",
        "release_class": "A",
        "evidence_class": "D",
        "result_status": "DERIVED",
        "title": "压比按绝压基准计算",
        "message": "压比只描述压力关系，不证明功率、级数、温升或设备型式。",
        "applicability": "压力基准和方向明确；表压必须加当地大气压，绝压必须大于零。",
        "does_not_prove": ["compressor_power", "stage_count", "vendor_model"],
        "promotion_cap": "DERIVED_PARAMETER",
        "source_refs": ["knowledge_graph/formula_family_nodes.md#formula_pressure_ratio"],
    },
    "compressor_isentropic_shaft_power": {
        "formula_id": "B_COMPRESSOR_ISENTROPIC_SHAFT_POWER_FROM_ACTUAL_INLET_FLOW",
        "release_class": "B",
        "evidence_class": "J",
        "result_status": "PROVISIONAL",
        "title": "压缩机轴功率按入口实际体积流量等熵初算",
        "message": "使用入口绝压、入口实际体积流量、比热比和等熵效率闭合功率；级间冷却、机械损失和偏离设计点尚未闭合。",
        "applicability": "单相气体，Q 为压缩机入口实际体积流量，Pin/Pout 使用同一压力基准，k>1，0<eta<=100%。",
        "does_not_prove": ["polytropic_power", "driver_rating", "intercooler_duty", "vendor_model"],
        "promotion_cap": "TYPE_SCREENING",
        "source_refs": ["knowledge_graph/formula_family_nodes.md#formula_isentropic_compression_work"],
    },
    "compressor_total_power": {
        "formula_id": "B_COMPRESSOR_TOTAL_INPUT_POWER_SCREENING",
        "release_class": "B",
        "evidence_class": "J",
        "result_status": "PROVISIONAL",
        "title": "压缩机总功率按驱动效率与辅机系数初算",
        "message": "总功率不是轴功率的复制值；程序显式计入驱动损失和登记的辅机功率分率。",
        "applicability": "轴功率已闭合，0<驱动效率<=100%，辅机功率分率>=0；正式电机和辅机负荷表仍需厂家确认。",
        "does_not_prove": ["motor_nameplate_rating", "electrical_load_list", "vendor_model"],
        "promotion_cap": "TYPE_SCREENING",
        "source_refs": ["knowledge_graph/equipment_customer_output_profiles.json#T02"],
    },
    "pipe_required_diameter": {
        "formula_id": "A_PIPE_REQUIRED_ID",
        "release_class": "A",
        "evidence_class": "D",
        "result_status": "DERIVED",
        "title": "理论内径由流量和目标流速计算",
        "message": "优先使用项目目标流速；缺少时可用相态条件化的登记保底值继续预设计，结果必须做压降与经济性敏感性复核。",
        "applicability": "稳态、单相、充满圆管；本式本身只给理论内径，标准 DN 必须由后续国标表选择步骤产生。",
        "does_not_prove": ["selected_dn", "pressure_drop_pass", "erosion_noise_pass"],
        "promotion_cap": "TYPE_SCREENING",
        "source_refs": ["knowledge_graph/formula_family_nodes.md#formula_nozzle_required_diameter"],
    },
    "pipe_standard_dn_selection": {
        "formula_id": "B_PIPE_STANDARD_DN_SELECTION",
        "release_class": "B",
        "evidence_class": "J",
        "result_status": "PROVISIONAL",
        "title": "理论内径按国标 DN—外径表圆整为预选管径",
        "message": "程序从 GB/T 12459-2025 已核验 DN—D 数据中选择首个满足暂定壁厚后内径要求的规格；壁厚、压力等级、材料和压降尚未因此通过。",
        "applicability": "理论内径和暂定壁厚均有效；只用于管径预选，正式管道等级须按设计压力、设计温度、材料许用应力、腐蚀裕量和产品标准复核。",
        "does_not_prove": ["wall_thickness_pass", "pressure_rating_pass", "material_compatibility", "pressure_drop_pass", "final_line_class"],
        "promotion_cap": "TYPE_SCREENING",
        "source_refs": ["GB/T 12459-2025 Table 2", "data/pipe_gbt12459_2025_dn_od_catalog.csv"],
    },
    "pipe_actual_velocity": {
        "formula_id": "A_PIPE_ACTUAL_VELOCITY",
        "release_class": "A",
        "evidence_class": "D",
        "result_status": "DERIVED",
        "title": "实际流速由选定外径和壁厚复算",
        "message": "外径和壁厚仍需标准版本、材料与腐蚀裕量证据。",
        "applicability": "稳态、单相、充满圆管，且 Do - 2t > 0。",
        "does_not_prove": ["pressure_drop_pass", "stress_pass", "selected_material"],
        "promotion_cap": "DERIVED_PARAMETER",
        "source_refs": ["knowledge_graph/formula_family_nodes.md#formula_nozzle_actual_velocity"],
    },
    "design_pressure_basis_conversion": {
        "formula_id": "A_DESIGN_PRESSURE_ABSOLUTE_TO_GAUGE",
        "release_class": "A",
        "evidence_class": "D",
        "result_status": "DERIVED",
        "title": "设计压力由绝压显式换算为表压",
        "message": "原始设计压力与当地大气压必须使用同一单位和参考状态；机械内压公式与候选卡统一消费表压值。",
        "applicability": "design_pressure_basis=absolute 且当地大气压已明确；换算后表压必须大于零，否则转入外压/真空分支。",
        "does_not_prove": ["code_design_pressure", "external_pressure_pass", "mechanical_design"],
        "promotion_cap": "DERIVED_PARAMETER",
        "source_refs": ["knowledge_graph/formula_family_nodes.md#formula_design_pressure_factor"],
    },
    "design_pressure": {
        "formula_id": "B_DESIGN_PRESSURE_FACTOR",
        "release_class": "B",
        "evidence_class": "J",
        "result_status": "PROVISIONAL",
        "title": "设计压力仅按显式系数初筛",
        "message": "优先使用当前项目规范或用户系数；缺少时允许登记的 1.1 最终保底值继续预设计，但不能证明规范设计压力。",
        "applicability": "仅内压初筛；真空、外压、静液柱、泄放和瞬态分支需另行闭合。",
        "does_not_prove": ["code_design_pressure", "external_pressure_pass", "mechanical_design"],
        "promotion_cap": "TYPE_SCREENING",
        "source_refs": ["knowledge_graph/formula_family_nodes.md#formula_design_pressure_factor"],
    },
    "cylinder_thickness": {
        "formula_id": "B_VESSEL_SHELL_THICKNESS",
        "release_class": "B",
        "evidence_class": "J",
        "result_status": "PROVISIONAL",
        "title": "筒体厚度仅为内压基础计算厚度",
        "message": "未包含腐蚀裕量、负偏差、最小厚度、开孔、支座、外压、风震和疲劳。",
        "applicability": "已确认内压圆筒公式分支，设计温度下许用应力和焊接系数有来源。",
        "does_not_prove": ["nominal_thickness", "sw6_pass", "mechanical_design"],
        "promotion_cap": "TYPE_SCREENING",
        "source_refs": ["knowledge_graph/formula_family_nodes.md#formula_cylinder_thickness"],
    },
    "head_thickness": {
        "formula_id": "B_VESSEL_ELLIPSOIDAL_HEAD_THICKNESS",
        "release_class": "B",
        "evidence_class": "J",
        "result_status": "PROVISIONAL",
        "title": "2:1 椭圆封头厚度仅为已选公式分支的基础值",
        "message": "必须显式选择 2:1 椭圆封头；腐蚀裕量、负偏差、成形减薄、外压和局部载荷尚未闭合。",
        "applicability": "仅适用于 head_type=2:1_ellipsoidal 的内压初筛分支。",
        "does_not_prove": ["nominal_thickness", "other_head_types", "sw6_pass"],
        "promotion_cap": "TYPE_SCREENING",
        "source_refs": ["knowledge_graph/formula_family_nodes.md#formula_head_thickness"],
    },
    "tower_preliminary_diameter": {
        "formula_id": "B_TOWER_PRELIMINARY_DIAMETER_FROM_TRAFFIC",
        "release_class": "B",
        "evidence_class": "J",
        "result_status": "PROVISIONAL",
        "title": "塔径由流程体积负荷和登记表观速度初估",
        "message": "当控制板段负荷不可得时可用已导入流程体积流量保底，但它不等同于塔内最大气相交通量。",
        "applicability": "仅用于无 Column Internals/塔盘图时保持预设计链运行；正式塔径需用控制板段气液负荷和液泛关联式复核。",
        "does_not_prove": ["flooding_capacity", "tray_hydraulics_pass", "final_tower_diameter"],
        "promotion_cap": "TYPE_SCREENING",
        "source_refs": ["knowledge_graph/project_overlays/c1_hydraulic_check/01-c1-missing-data-ledger.md"],
    },
    "tower_tray_spacing": {
        "formula_id": "B_TOWER_TRAY_SPACING_SERIES",
        "release_class": "B",
        "evidence_class": "J",
        "result_status": "PROVISIONAL",
        "title": "按塔径系列选取预设计板间距",
        "message": "程序从手册允许系列中选取一个泛用中间值，真实内件、板数和检修要求到位后必须重算塔高。",
        "applicability": "600-4200 mm 板式塔预设计；超出范围仍保留 800 mm 保底并报警。",
        "does_not_prove": ["actual_tray_spacing", "final_tower_height", "internals_design"],
        "promotion_cap": "TYPE_SCREENING",
        "source_refs": ["knowledge_graph/project_overlays/c1_hydraulic_check/11-process-manual-lower-ch48.md"],
    },
    "tower_cross_section": {
        "formula_id": "A_CIRCULAR_CROSS_SECTION",
        "release_class": "A",
        "evidence_class": "D",
        "result_status": "DERIVED",
        "title": "圆形截面积由有效内径计算",
        "message": "该几何量不等于塔板有效鼓泡面积，降液管和无效区需另算。",
        "applicability": "输入直径必须是本设备明确口径的有效内径。",
        "does_not_prove": ["active_tray_area", "flooding_pass", "internals_design"],
        "promotion_cap": "DERIVED_PARAMETER",
        "source_refs": ["knowledge_graph/formula_family_nodes.md#formula_cylindrical_geometry_volume"],
    },
    "tower_active_area_fraction": {
        "formula_id": "B_TOWER_ACTIVE_AREA_CLOSURE",
        "release_class": "B",
        "evidence_class": "J",
        "result_status": "PROVISIONAL",
        "title": "有效鼓泡面积分率扣除降液管、受液区和无效区",
        "message": "面积闭合显式扣除了左/右降液与受液区域及边缘无效区；登记分率仅为无内件图时的保底初值。",
        "applicability": "单溢流或泛用板式塔预设计；真实塔盘流型和几何到位后必须整体重算。",
        "does_not_prove": ["actual_tray_layout", "flooding_pass", "entrainment_pass"],
        "promotion_cap": "TYPE_SCREENING",
        "source_refs": ["knowledge_graph/standards_graph/INDEPENDENT_EXPERT_REVIEW.md", "knowledge_graph/project_overlays/c1_hydraulic_check/11-process-manual-lower-ch48.md"],
    },
    "tower_active_area": {
        "formula_id": "B_TOWER_ACTIVE_AREA",
        "release_class": "B",
        "evidence_class": "J",
        "result_status": "PROVISIONAL",
        "title": "塔板有效鼓泡面积初算",
        "message": "有效面积由全截面积乘有效面积分率得到，不能把全筒面积直接当有效传质面积。",
        "applicability": "面积分率与当前塔盘流型一致时用于预设计。",
        "does_not_prove": ["actual_active_area", "internals_design"],
        "promotion_cap": "TYPE_SCREENING",
        "source_refs": ["knowledge_graph/standards_graph/INDEPENDENT_EXPERT_REVIEW.md"],
    },
    "tower_hole_area": {
        "formula_id": "B_TOWER_HOLE_AREA",
        "release_class": "B",
        "evidence_class": "J",
        "result_status": "PROVISIONAL",
        "title": "塔板总开孔面积初算",
        "message": "开孔率为登记的预设计条件，不能替代真实孔径、孔数、阀型或厂家塔盘数据。",
        "applicability": "筛板/浮阀板的开孔面积初筛。",
        "does_not_prove": ["weeping_pass", "pressure_drop_pass", "tray_vendor_rating"],
        "promotion_cap": "TYPE_SCREENING",
        "source_refs": ["knowledge_graph/project_overlays/c1_hydraulic_check/01-c1-missing-data-ledger.md"],
    },
    "tower_actual_superficial_velocity": {
        "formula_id": "B_TOWER_ACTIVE_AREA_VELOCITY",
        "release_class": "B",
        "evidence_class": "J",
        "result_status": "PROVISIONAL",
        "title": "按有效鼓泡面积折算表观速度",
        "message": "若流量不是控制板段气相体积流量，该速度只能作为流程交通量敏感性基线。",
        "applicability": "流量基准和有效面积口径明确。",
        "does_not_prove": ["flooding_fraction", "entrainment_pass"],
        "promotion_cap": "TYPE_SCREENING",
        "source_refs": ["knowledge_graph/project_overlays/c1_hydraulic_check/01-c1-missing-data-ledger.md"],
    },
    "tower_preliminary_height": {
        "formula_id": "B_TOWER_PRELIMINARY_HEIGHT",
        "release_class": "B",
        "evidence_class": "J",
        "result_status": "PROVISIONAL",
        "title": "塔高由级数、板间距与附加空间初估",
        "message": "板间距和塔顶/塔底附加空间为登记保底条件，不含所有人孔、进料段、除沫器和特殊分段。",
        "applicability": "板式塔预设计；填料塔或分段内件需改用对应高度模型。",
        "does_not_prove": ["final_tower_height", "mechanical_layout"],
        "promotion_cap": "TYPE_SCREENING",
        "source_refs": ["knowledge_graph/project_overlays/c1_hydraulic_check/10-process-manual-upper-ch17.md", "knowledge_graph/project_overlays/c1_hydraulic_check/11-process-manual-lower-ch48.md"],
    },
    "tower_bottom_liquid_height": {
        "formula_id": "B_TOWER_HOLDUP_HEIGHT",
        "release_class": "B",
        "evidence_class": "J",
        "result_status": "PROVISIONAL",
        "title": "塔底持液高度仅为库存初筛",
        "message": "停留时间是显式设计决策；内件、人孔、液位控制和动态裕量未包含。",
        "applicability": "圆形截面、稳态等效体积流量，且停留时间有当前项目依据。",
        "does_not_prove": ["final_bottom_height", "level_control_adequacy", "tower_layout"],
        "promotion_cap": "TYPE_SCREENING",
        "source_refs": ["knowledge_graph/formula_family_nodes.md#formula_tower_holdup"],
    },
    "cylinder_volume": {
        "formula_id": "A_CYLINDER_STRAIGHT_VOLUME",
        "release_class": "A",
        "evidence_class": "D",
        "result_status": "DERIVED",
        "title": "圆筒直段几何容积",
        "message": "结果单独写入直筒段几何容积字段；不含封头、液位、内件和附件占位，绝不自动写成有效或选定总容积。",
        "applicability": "直径为内径，高度为圆筒直段长度。",
        "does_not_prove": ["selected_total_volume", "effective_volume", "working_inventory", "final_vessel_size"],
        "promotion_cap": "DERIVED_PARAMETER",
        "source_refs": ["knowledge_graph/formula_family_nodes.md#formula_cylindrical_geometry_volume"],
    },
    "storage_required_volume": {
        "formula_id": "A_STORAGE_REQUIRED_VOLUME_FROM_RESIDENCE",
        "release_class": "A",
        "evidence_class": "D",
        "result_status": "DERIVED",
        "title": "最低所需总容积由流量、停留时间和装填系数计算",
        "message": "优先使用项目库存策略；缺少时可用登记的停留时间和装填系数保底继续预设计，但必须进行库存、控制与安全敏感性复核。",
        "applicability": "稳态体积流量与停留时间基准一致，0 < fill_fraction ≤ 1。",
        "does_not_prove": ["selected_volume", "diameter_height_pair", "surge_allowance", "mechanical_design"],
        "promotion_cap": "DERIVED_PARAMETER",
        "source_refs": ["knowledge_graph/formula_family_nodes.md#formula_storage_required_volume"],
    },
    "membrane_area": {
        "formula_id": "A_TUBULAR_MEMBRANE_GEOMETRIC_AREA",
        "release_class": "A",
        "evidence_class": "D",
        "result_status": "DERIVED",
        "title": "圆管通道几何膜面积",
        "message": "几何面积不证明通量、选择性、回收率、寿命或厂家性能。",
        "applicability": "已确认圆管通道几何，通道数、内径、长度和元件数均明确。",
        "does_not_prove": ["membrane_performance", "recovery", "vendor_model"],
        "promotion_cap": "DERIVED_PARAMETER",
        "source_refs": ["knowledge_graph/formula_family_nodes.md#formula_membrane_area_geometry"],
    },
    "heater_sensible_duty_screening": {
        "formula_id": "B_HEATER_SENSIBLE_DUTY_SCREENING",
        "release_class": "B",
        "evidence_class": "J",
        "result_status": "PROVISIONAL",
        "title": "HEATER 显热负荷保底初算",
        "message": "当 Aspen 零负荷与非零流量、非零温差冲突时，按质量流量、登记相态比热和温差不中停初算；登记比热不是 Aspen 物性。",
        "applicability": "无显著相变/反应热，质量流量与进出口温度来自同一工况；实际 Cp 到位后必须自动重算。",
        "does_not_prove": ["latent_heat", "reaction_heat", "aspen_energy_balance", "final_heat_duty", "edr_pass"],
        "promotion_cap": "TYPE_SCREENING",
        "source_refs": ["knowledge_graph/formula_family_nodes.md#formula_sensible_heat_screening"],
    },
    "exchanger_area": {
        "formula_id": "B_HEX_LMTD_AREA",
        "release_class": "B",
        "evidence_class": "J",
        "result_status": "PROVISIONAL",
        "title": "换热面积仅为 LMTD 初筛值",
        "message": "U、F、污垢热阻、相变分段、压降和结构尚未由同工况 EDR 闭合。",
        "applicability": "Q、U、F、LMTD 均为同一工况且为正；温度交叉、多程或多相分区需专业模型。",
        "does_not_prove": ["final_area", "edr_pass", "mechanical_design"],
        "promotion_cap": "TYPE_SCREENING",
        "source_refs": [
            "knowledge_graph/formula_family_nodes.md#formula_exchanger_area_screening",
            "knowledge_graph/standards_graph/exchanger_standards_nodes.md"
        ],
    },
    "exchanger_tube_count": {
        "formula_id": "B_HEX_TUBE_COUNT_FROM_AREA",
        "release_class": "B",
        "evidence_class": "J",
        "result_status": "PROVISIONAL",
        "title": "换热管数量由预设计面积和登记管径/管长初算",
        "message": "管径、管长、管程、布管、压降和振动尚未由同工况 EDR 闭合。",
        "applicability": "管壳式换热器按管外表面积初筛，A、do、L 均为正。",
        "does_not_prove": ["tube_layout", "pressure_drop", "vibration", "edr_pass"],
        "promotion_cap": "TYPE_SCREENING",
        "source_refs": ["knowledge_graph/formula_family_nodes.md#formula_exchanger_tube_count_screening"],
    },
    "tower_internal_height": {
        "formula_id": "B_TOWER_ACTIVE_TRAY_HEIGHT",
        "release_class": "B",
        "evidence_class": "J",
        "result_status": "PROVISIONAL",
        "title": "塔板有效高度由级数和板间距初算",
        "message": "进料/采出板、特殊间距、除沫器和气液分布空间尚未闭合。",
        "applicability": "板式塔预设计，按 max(N-1,1) 个板间距计算。",
        "does_not_prove": ["final_internals_layout", "total_tower_height"],
        "promotion_cap": "TYPE_SCREENING",
        "source_refs": ["knowledge_graph/formula_family_nodes.md#formula_tower_preliminary_height"],
    },
}

# The block-specific solid-processing formulas used to execute without a
# registered source policy.  They are intentionally included here so every
# executable calculation rule has an explicit applicability/evidence boundary
# and at least one source route.
CALCULATION_POLICIES.update({
    "crystallizer_working_volume": {
        "formula_id": "A_CRYSTALLIZER_WORKING_VOLUME",
        "release_class": "A",
        "evidence_class": "D",
        "result_status": "DERIVED",
        "title": "结晶器工作容积由浆液流量和显式停留时间计算",
        "message": "本式只闭合工作容积恒等关系；晶体生长、粒度分布、过饱和度和搅拌传热尚未闭合。",
        "applicability": "稳定连续浆液流量，停留时间为当前结晶工艺的显式设计输入。",
        "does_not_prove": ["crystal_size_distribution", "mixing_pass", "heat_transfer_pass", "final_model"],
        "promotion_cap": "DERIVED_PARAMETER",
        "source_refs": ["knowledge_graph/chapter_04_08_late_equipment_graph.md"],
    },
    "filter_area_from_cake_flux": {
        "formula_id": "B_FILTER_AREA_FROM_CAKE_FLUX",
        "release_class": "B",
        "evidence_class": "J",
        "result_status": "PROVISIONAL",
        "title": "过滤面积由固体负荷和显式滤饼通量初算",
        "message": "滤饼通量必须来自同物料试验或项目依据；本式不闭合滤布、压差、周期和洗涤要求。",
        "applicability": "稳定固体进料，过滤通量大于零且适用于当前滤饼和操作周期。",
        "does_not_prove": ["filter_cycle", "cloth_selection", "washing_pass", "final_model"],
        "promotion_cap": "TYPE_SCREENING",
        "source_refs": ["knowledge_graph/chapter_04_08_late_equipment_graph.md"],
    },
    "dryer_water_evaporation": {
        "formula_id": "A_DRYER_WATER_BALANCE",
        "release_class": "A",
        "evidence_class": "D",
        "result_status": "DERIVED",
        "title": "干燥器蒸发水量由明确水组分的进出口质量衡算计算",
        "message": "只有水组分映射和进出口质量流量属于同一边界时，本差值才代表水蒸发量。",
        "applicability": "稳态、同一系统边界，水组分映射明确且无未计水支路。",
        "does_not_prove": ["drying_kinetics", "bound_moisture", "residence_time_pass", "final_model"],
        "promotion_cap": "DERIVED_PARAMETER",
        "source_refs": ["knowledge_graph/chapter_04_08_late_equipment_graph.md"],
    },
    "dryer_specific_duty": {
        "formula_id": "B_DRYER_SPECIFIC_DUTY",
        "release_class": "B",
        "evidence_class": "J",
        "result_status": "PROVISIONAL",
        "title": "干燥器单位蒸发水热耗由总热负荷初算",
        "message": "总热负荷、散热、排风显热和热效率边界必须一致；本值不能替代干燥动力学和厂家热平衡。",
        "applicability": "蒸发水量大于零，热负荷与水衡算属于同一稳定工况和系统边界。",
        "does_not_prove": ["thermal_efficiency", "drying_kinetics", "air_system_design", "final_model"],
        "promotion_cap": "TYPE_SCREENING",
        "source_refs": ["knowledge_graph/chapter_04_08_late_equipment_graph.md"],
    },
})

# The incompressible Cv expression is a liquid-only screening branch.  Keep
# this executable policy explicit so unknown, gas, solid-bearing and
# two-phase services can never be described as a harmless "liquid equivalent"
# placeholder.
CALCULATION_POLICIES["valve_liquid_equivalent_cv_screening"].update({
    "message": (
        "仅当相态明确为单一液相时，程序才运行不可压缩液体 Cv 初筛。气相、"
        "两相、含固或相态未知时必须阻断，且不得生成液体等效 Cv 占位值。"
    ),
    "applicability": (
        "phase=liquid，Q 为同工况实际体积流量，rho 为同工况密度且 dP>0。"
    ),
    "does_not_prove": [
        "gas_valve_cv",
        "choked_flow_pass",
        "flashing_pass",
        "cavitation_pass",
        "noise_pass",
        "final_model",
    ],
})

# A caller may provide a value that the deterministic chain can also derive.
# Such a value is never allowed to suppress the calculation.  The calculated
# value becomes the canonical downstream value and the supplied value is
# cross-checked under these explicit engineering-rounding tolerances.
CALCULATION_TARGET_TOLERANCES: dict[str, tuple[float, float]] = {
    "head_m": (0.005, 0.05),
    "hydraulic_power_kw": (0.005, 0.01),
    "pressure_drop_power_component_kw": (0.005, 0.01),
    "pressure_component_shaft_power_screening_kw": (0.005, 0.01),
    "pressure_drop_head_component_m": (0.005, 0.05),
    "shaft_power_kw": (0.005, 0.01),
    "pressure_drop_kpa": (0.002, 0.01),
    "maximum_pressure_drop_kpa": (0.005, 0.01),
    "cv": (0.005, 0.01),
    "heat_duty_kw": (0.005, 0.01),
    "cavitation_margin_m": (0.005, 0.01),
    "compression_pressure_ratio": (0.002, 0.001),
    "expansion_pressure_ratio": (0.002, 0.001),
    "required_inner_diameter_mm": (0.005, 0.1),
    "actual_velocity_m_s": (0.005, 0.01),
    "design_pressure_mpa": (0.002, 0.001),
    "cylinder_calculated_thickness_mm": (0.005, 0.01),
    "head_calculated_thickness_mm": (0.005, 0.01),
    "tower_cross_section_m2": (0.005, 0.001),
    "inner_diameter_mm": (0.005, 1.0),
    "tray_spacing_mm": (0.005, 1.0),
    "tower_active_area_fraction": (0.005, 0.001),
    "tower_active_area_m2": (0.005, 0.001),
    "tower_hole_area_m2": (0.005, 0.001),
    "tower_actual_superficial_velocity_m_s": (0.005, 0.001),
    "height_mm": (0.005, 1.0),
    "bottom_liquid_height_m": (0.005, 0.001),
    "volume_m3": (0.005, 0.001),
    "required_volume_m3": (0.005, 0.001),
    "straight_shell_geometric_volume_m3": (0.005, 0.001),
    "membrane_area_m2": (0.005, 0.01),
    "heat_transfer_area_m2": (0.005, 0.01),
    "tube_or_plate_count": (0.0, 0.0),
    "tower_internal_height_m": (0.005, 0.001),
}

HARD_CALCULATION_STATUSES = {
    "BLOCKED_PHYSICAL_DIRECTION",
    "BLOCKED_UPSTREAM_CALCULATION",
    "BLOCKED_TARGET_MISMATCH",
    "BLOCKED_EXTERNAL_PRESSURE_BRANCH_REQUIRED",
    "BLOCKED_NONPOSITIVE_DENOMINATOR",
    "BLOCKED_INVALID_INPUT",
    "BLOCKED_ZERO_DUTY_NO_EQUIPMENT_LOAD",
    "BLOCKED_NONPOSITIVE_PRESSURE_DROP",
    "BLOCKED_INVALID_AREA_CLOSURE",
}


def is_hard_calculation_blocker(item: dict[str, Any]) -> bool:
    """Return true only for contradictions/unsafe branches, not missing inputs."""
    return str(item.get("status", "")) in HARD_CALCULATION_STATUSES

# Alternative closure sets account for deterministic upstream derivations.  A
# pump power calculation, for example, can be closed either with a supplied
# head or with the pressure pair from which head is derived.
CALCULATION_INPUT_ALTERNATIVES: dict[str, tuple[tuple[str, ...], ...]] = {
    **{name: (fields,) for name, fields in CALCULATION_REQUIREMENTS.items()},
    "pump_hydraulic_power": (
        ("flow_m3_h", "head_m", "density_kg_m3"),
        ("flow_m3_h", "inlet_pressure_mpa", "outlet_pressure_mpa", "density_kg_m3", "pressure_basis"),
    ),
    "pump_shaft_power": (
        ("flow_m3_h", "head_m", "efficiency_percent", "density_kg_m3"),
        ("flow_m3_h", "inlet_pressure_mpa", "outlet_pressure_mpa", "efficiency_percent", "density_kg_m3", "pressure_basis"),
    ),
}

IDENTITY_FIELDS = {
    "equipment_family", "equipment_type", "aspen_block_type",
    "process_function", "equipment_tag",
}
NON_PROFILE_FIELDS = {
    "candidate_model", "vendor_model", "verification_result", "approval_status",
    "evidence_manifest_path", "evidence_manifest_sha256",
    "audit_approval_path", "audit_approval_sha256",
}

FIELD_UNITS: dict[str, str] = {
    "flow_m3_h": "m3/h",
    "head_m": "m",
    "density_kg_m3": "kg/m3",
    "efficiency_percent": "%",
    "inlet_pressure_mpa": "MPa",
    "outlet_pressure_mpa": "MPa",
    "operating_pressure_mpa": "MPa",
    "design_pressure_mpa": "MPa",
    "pressure_drop_kpa": "kPa",
    "allowable_pressure_drop_kpa": "kPa",
    "maximum_pressure_drop_kpa": "kPa",
    "maximum_pressure_drop_factor": "dimensionless",
    "temperature_c": "degC",
    "inlet_temperature_c": "degC",
    "design_temperature_c": "degC",
    "heat_duty_kw": "kW",
    "specific_heat_kj_kgk": "kJ/(kg*K)",
    "heat_transfer_area_m2": "m2",
    "tube_outer_diameter_mm": "mm",
    "tube_length_mm": "mm",
    "tube_or_plate_count": "count",
    "shell_pass_count": "count",
    "lmtd_correction_factor": "dimensionless",
    "diameter_mm": "mm",
    "height_mm": "mm",
    "straight_shell_length_mm": "mm",
    "volume_m3": "m3",
    "required_volume_m3": "m3",
    "straight_shell_geometric_volume_m3": "m3",
    "retention_time_min": "min",
    "rotational_speed_rpm": "r/min",
    "shaft_power_kw": "kW",
    "hydraulic_power_kw": "kW",
    "pressure_drop_power_component_kw": "kW",
    "pressure_component_shaft_power_screening_kw": "kW",
    "pressure_drop_head_component_m": "m",
    "cavitation_margin_m": "m",
    "required_inner_diameter_mm": "mm",
    "actual_velocity_m_s": "m/s",
    "tower_cross_section_m2": "m2",
    "tower_design_velocity_m_s": "m/s",
    "tower_downcomer_area_fraction": "dimensionless",
    "tower_receiving_area_fraction": "dimensionless",
    "tower_inactive_area_fraction": "dimensionless",
    "tower_active_area_fraction": "dimensionless",
    "tower_active_area_m2": "m2",
    "tower_open_area_fraction": "dimensionless",
    "tower_hole_area_m2": "m2",
    "tower_actual_superficial_velocity_m_s": "m/s",
    "tray_spacing_mm": "mm",
    "tower_top_bottom_allowance_mm": "mm",
    "tower_weir_length_ratio": "dimensionless",
    "tower_weir_height_mm": "mm",
    "tower_downcomer_residence_time_s": "s",
    "bottom_liquid_height_m": "m",
    "tower_internal_height_m": "m",
    "cylinder_calculated_thickness_mm": "mm",
    "head_calculated_thickness_mm": "mm",
    "compression_pressure_ratio": "dimensionless",
    "expansion_pressure_ratio": "dimensionless",
    "heat_capacity_ratio_k": "dimensionless",
    "driver_efficiency_percent": "%",
    "auxiliary_power_fraction": "dimensionless",
    "total_power_kw": "kW",
    "membrane_area_m2": "m2",
    "cycle_time_h": "h",
    "slurry_flow_m3_h": "m3/h",
    "working_volume_m3": "m3",
    "crystal_yield_kg_h": "kg/h",
    "solids_feed_kg_h": "kg/h",
    "filtrate_flow_kg_h": "kg/h",
    "cake_moisture_percent": "%",
    "filtration_flux_kg_m2_h": "kg/(m2*h)",
    "cake_specific_resistance_m_kg": "m/kg",
    "filter_area_m2": "m2",
    "inlet_water_kg_h": "kg/h",
    "outlet_water_kg_h": "kg/h",
    "evaporation_rate_kg_h": "kg/h",
    "allowed_solid_temperature_c": "degC",
    "specific_drying_duty_kj_kg": "kJ/kg",
    "selected_outer_diameter_mm": "mm",
    "selected_wall_thickness_mm": "mm",
    "cv": "dimensionless",
}


FIELD_ALIASES: dict[str, list[str]] = {
    "equipment_tag": ["equipment_tag", "tag", "设备位号", "位号", "设备编号"],
    "equipment_family": ["equipment_family", "family", "设备族", "设备类别id"],
    "equipment_type": ["equipment_type", "type", "设备类型", "设备类别", "型式", "结构型式"],
    "terminal_type_rule_override_id": [
        "terminal_type_rule_override_id", "terminal_rule_id", "终选型式规则id", "条件选型规则id"
    ],
    "aspen_block_type": ["aspen_block_type", "block_type", "aspen类型", "aspen块类型", "模块类型"],
    "process_function": ["process_function", "service", "duty", "工艺功能", "设备作用", "用途", "服务"],
    "phase": ["phase", "相态"],
    "pressure_basis": ["pressure_basis", "压力基准", "压力basis", "absolute_or_gauge"],
    "design_pressure_basis": ["design_pressure_basis", "设计压力基准", "design_pressure_absolute_or_gauge"],
    "material": ["material", "材质", "材料"],
    "flow_m3_h": ["flow_m3_h", "flow_m3_s", "flow_m3_min", "flow_l_s", "volumetric_flow_m3_h", "q_m3_h", "q_m3_s", "体积流量", "流量m3h", "流量"],
    "mass_flow_kg_h": ["mass_flow_kg_h", "mass_flow_kg_s", "mass_flow_t_h", "质量流量", "质量流量kgh"],
    "head_m": ["head_m", "扬程", "扬程m"],
    "density_kg_m3": ["density_kg_m3", "rho_kg_m3", "密度", "密度kgm3"],
    "efficiency_percent": ["efficiency_percent", "efficiency_fraction", "efficiency", "效率", "效率percent"],
    "inlet_pressure_mpa": ["inlet_pressure_mpa", "inlet_pressure_bar", "inlet_pressure_kpa", "inlet_pressure_pa", "pin_mpa", "pin_bar", "进口压力", "入口压力"],
    "outlet_pressure_mpa": ["outlet_pressure_mpa", "outlet_pressure_bar", "outlet_pressure_kpa", "outlet_pressure_pa", "pout_mpa", "pout_bar", "出口压力"],
    "atmospheric_pressure_mpa": ["atmospheric_pressure_mpa", "atmospheric_pressure_bar", "atmospheric_pressure_kpa", "当地大气压", "大气压力"],
    "operating_pressure_mpa": ["operating_pressure_mpa", "operating_pressure_bar", "operating_pressure_kpa", "operating_pressure_pa", "操作压力", "工作压力"],
    "design_pressure_mpa": ["design_pressure_mpa", "design_pressure_bar", "design_pressure_kpa", "design_pressure_pa", "设计压力"],
    "design_pressure_factor": ["design_pressure_factor", "设计压力系数"],
    "pressure_drop_kpa": ["pressure_drop_kpa", "dp_kpa", "压降", "压差"],
    "allowable_pressure_drop_kpa": ["allowable_pressure_drop_kpa", "允许压降"],
    "maximum_pressure_drop_kpa": ["maximum_pressure_drop_kpa", "最大压差"],
    "maximum_pressure_drop_factor": ["maximum_pressure_drop_factor", "最大压差系数"],
    "temperature_c": ["temperature_c", "temperature_k", "温度", "操作温度"],
    "inlet_temperature_c": ["inlet_temperature_c", "inlet_temperature_k", "入口温度", "进口温度"],
    "outlet_temperature_c": ["outlet_temperature_c", "outlet_temperature_k", "出口温度"],
    "design_temperature_c": ["design_temperature_c", "design_temperature_k", "设计温度"],
    "heat_duty_kw": ["heat_duty_kw", "热负荷", "换热负荷", "duty_kw"],
    "specific_heat_kj_kgk": ["specific_heat_kj_kgk", "specific_heat", "cp_kj_kgk", "定压比热", "比热容"],
    "heat_transfer_area_m2": ["heat_transfer_area_m2", "换热面积", "传热面积", "area_m2"],
    "tube_outer_diameter_mm": ["tube_outer_diameter_mm", "换热管外径"],
    "tube_length_mm": ["tube_length_mm", "换热管长度", "管长"],
    "tube_or_plate_count": ["tube_or_plate_count", "换热管数量", "换热管根数", "板片数量"],
    "shell_pass_count": ["shell_pass_count", "壳程数"],
    "tube_material_grade": ["tube_material_grade", "tube_side_material", "管程材料", "换热管材料"],
    "shell_material_grade": ["shell_material_grade", "shell_side_material", "壳程材料", "壳体材料"],
    "overall_u_w_m2k": ["overall_u_w_m2k", "总传热系数", "传热系数"],
    "lmtd_k": ["lmtd_k", "对数平均温差", "lmtd"],
    "lmtd_correction_factor": ["lmtd_correction_factor", "lmtd修正系数", "温差修正系数", "修正系数f"],
    "diameter_mm": ["diameter_mm", "diameter_m", "设备直径", "工程直径", "直径"],
    "height_mm": ["height_mm", "height_m", "设备高度", "总高", "高度"],
    "inner_diameter_mm": ["inner_diameter_mm", "inner_diameter_m", "计算内径", "筒体内径", "塔内径", "塔径", "内径"],
    "straight_shell_length_mm": [
        "straight_shell_length_mm", "straight_shell_length_m", "筒体直段长度",
        "直筒段长度", "筒体长度", "直边段高度",
    ],
    "volume_m3": ["volume_m3", "设计容积", "选定容积", "容积", "体积"],
    "volume_basis": ["volume_basis", "容积基准", "容积类型"],
    "required_volume_m3": ["required_volume_m3", "最低所需总容积", "所需容积"],
    "straight_shell_geometric_volume_m3": ["straight_shell_geometric_volume_m3", "直筒段几何容积"],
    "stage_count": ["stage_count", "理论级数", "塔板数", "级数"],
    "retention_time_min": ["retention_time_min", "停留时间", "持液时间"],
    "fill_fraction": ["fill_fraction", "装填系数", "充装系数"],
    "tower_design_velocity_m_s": ["tower_design_velocity_m_s", "塔径初估表观速度", "塔设计气速"],
    "tower_downcomer_area_fraction": ["tower_downcomer_area_fraction", "降液管面积分率"],
    "tower_receiving_area_fraction": ["tower_receiving_area_fraction", "受液区面积分率"],
    "tower_inactive_area_fraction": ["tower_inactive_area_fraction", "无效区面积分率"],
    "tower_active_area_fraction": ["tower_active_area_fraction", "有效鼓泡面积分率"],
    "tower_active_area_m2": ["tower_active_area_m2", "有效鼓泡面积"],
    "tower_open_area_fraction": ["tower_open_area_fraction", "开孔率"],
    "tower_hole_area_m2": ["tower_hole_area_m2", "总开孔面积"],
    "tower_actual_superficial_velocity_m_s": ["tower_actual_superficial_velocity_m_s", "有效区表观速度"],
    "tray_spacing_mm": ["tray_spacing_mm", "板间距", "塔板间距"],
    "tower_top_bottom_allowance_mm": ["tower_top_bottom_allowance_mm", "塔顶塔底附加空间"],
    "tower_weir_length_ratio": ["tower_weir_length_ratio", "堰长塔径比"],
    "tower_weir_height_mm": ["tower_weir_height_mm", "出口堰高", "堰高"],
    "tower_downcomer_residence_time_s": ["tower_downcomer_residence_time_s", "降液管停留时间"],
    "tower_internal_height_m": ["tower_internal_height_m", "塔板有效高度", "填料高度"],
    "insulation_spec": ["insulation_spec", "insulation_layer", "保温层", "保温规格"],
    "protective_layer": ["protective_layer", "保护层", "外护层"],
    "target_velocity_m_s": ["target_velocity_m_s", "目标流速", "设计流速"],
    "selected_dn": ["selected_dn", "dn", "公称直径"],
    "selected_outer_diameter_mm": ["selected_outer_diameter_mm", "管外径", "外径"],
    "selected_wall_thickness_mm": ["selected_wall_thickness_mm", "壁厚"],
    "wall_series": ["wall_series", "壁厚系列", "sch"],
    "allowable_stress_mpa": ["allowable_stress_mpa", "许用应力"],
    "weld_efficiency": ["weld_efficiency", "焊接接头系数"],
    "cylinder_calculated_thickness_mm": ["cylinder_calculated_thickness_mm", "筒体计算厚度"],
    "head_calculated_thickness_mm": ["head_calculated_thickness_mm", "封头计算厚度"],
    "npsha_m": ["npsha_m", "npsha"],
    "npshr_m": ["npshr_m", "npshr"],
    "required_npsh_margin_m": ["required_npsh_margin_m", "规定npsh裕量", "要求汽蚀裕量"],
    "npshr_evidence_scope": ["npshr_evidence_scope", "npshr证据范围", "npshr同工况证据范围"],
    "head_type": ["head_type", "封头型式", "封头类型"],
    "membrane_geometry_type": ["membrane_geometry_type", "膜几何型式", "膜通道几何"],
    "gas_molecular_weight": ["gas_molecular_weight", "分子量", "气体分子量"],
    "compressibility_factor": ["compressibility_factor", "z", "压缩因子"],
    "heat_capacity_ratio_k": ["heat_capacity_ratio_k", "gas_heat_capacity_ratio", "k", "比热比", "绝热指数"],
    "driver_efficiency_percent": ["driver_efficiency_percent", "motor_efficiency_percent", "驱动效率", "电机效率"],
    "auxiliary_power_fraction": ["auxiliary_power_fraction", "辅机功率分率", "辅助功率比例"],
    "total_power_kw": ["total_power_kw", "总功率", "总输入功率"],
    "surge_margin_percent": ["surge_margin_percent", "喘振裕量"],
    "required_surge_margin_percent": ["required_surge_margin_percent", "规定喘振裕量", "要求喘振裕量"],
    "surge_margin_evidence_scope": ["surge_margin_evidence_scope", "喘振裕量证据范围", "同工况性能图范围"],
    "rotational_speed_rpm": ["rotational_speed_rpm", "转速", "转速rpm"],
    "shaft_power_kw": ["shaft_power_kw", "轴功率", "功率kw"],
    "pressure_drop_power_component_kw": ["pressure_drop_power_component_kw", "压差功率分量"],
    "pressure_component_shaft_power_screening_kw": [
        "pressure_component_shaft_power_screening_kw", "压差分量轴功率初筛",
    ],
    "pressure_drop_head_component_m": ["pressure_drop_head_component_m", "压差水头分量"],
    "mixing_metric": ["mixing_metric", "混合指标", "混合均匀度"],
    "element_count": ["element_count", "元件数", "膜元件数", "混合元件数"],
    "channel_count": ["channel_count", "通道数", "膜丝数"],
    "channel_inner_diameter_mm": ["channel_inner_diameter_mm", "通道内径", "膜丝内径"],
    "element_length_m": ["element_length_m", "元件长度", "膜丝长度"],
    "membrane_area_m2": ["membrane_area_m2", "膜面积"],
    "flux": ["flux", "通量"],
    "selectivity": ["selectivity", "选择性"],
    "recovery_percent": ["recovery_percent", "回收率"],
    "capacity": ["capacity", "处理能力", "容量"],
    "cycle_time_h": ["cycle_time_h", "循环周期", "再生周期"],
    "crystallization_mode": ["crystallization_mode", "结晶模式", "结晶操作模式"],
    "solubility_profile_ref": ["solubility_profile_ref", "溶解度数据引用", "溶解度曲线引用"],
    "solubility_profile_sha256": ["solubility_profile_sha256", "溶解度数据sha256"],
    "crystal_component_mapping": ["crystal_component_mapping", "晶体组分映射"],
    "slurry_flow_m3_h": ["slurry_flow_m3_h", "浆液流量", "结晶浆液体积流量"],
    "working_volume_m3": ["working_volume_m3", "工作容积", "结晶器工作容积"],
    "crystal_yield_kg_h": ["crystal_yield_kg_h", "晶体产量"],
    "separation_type": ["separation_type", "固液分离类型"],
    "solids_feed_kg_h": ["solids_feed_kg_h", "过滤固体负荷"],
    "filtrate_flow_kg_h": ["filtrate_flow_kg_h", "滤液质量流量"],
    "cake_moisture_percent": ["cake_moisture_percent", "滤饼含湿量"],
    "filtration_flux_kg_m2_h": ["filtration_flux_kg_m2_h", "过滤通量"],
    "cake_specific_resistance_m_kg": ["cake_specific_resistance_m_kg", "滤饼比阻"],
    "wash_requirement": ["wash_requirement", "滤饼洗涤要求"],
    "filter_area_m2": ["filter_area_m2", "过滤面积"],
    "dryer_model_kind": ["dryer_model_kind", "干燥模型类型"],
    "moisture_basis": ["moisture_basis", "含湿量基准"],
    "water_component_mapping": ["water_component_mapping", "水组分映射"],
    "inlet_water_kg_h": ["inlet_water_kg_h", "入口水分质量流量"],
    "outlet_water_kg_h": ["outlet_water_kg_h", "出口水分质量流量", "产品残余水分质量流量"],
    "evaporation_rate_kg_h": ["evaporation_rate_kg_h", "水分蒸发量", "蒸发负荷"],
    "allowed_solid_temperature_c": ["allowed_solid_temperature_c", "固体允许最高温度"],
    "heat_source": ["heat_source", "干燥热源"],
    "offgas_route": ["offgas_route", "尾气处理路线"],
    "specific_drying_duty_kj_kg": ["specific_drying_duty_kj_kg", "单位蒸发量热耗"],
    "fitting_type": ["fitting_type", "管件型式"],
    "connection_type": ["connection_type", "连接型式", "连接方式"],
    "pressure_class": ["pressure_class", "压力等级", "pn", "class"],
    "flange_face": ["flange_face", "密封面"],
    "gasket_material": ["gasket_material", "垫片材料"],
    "valve_function": ["valve_function", "阀门功能"],
    "cv": ["cv", "流量系数"],
    "cavitation_margin_m": ["cavitation_margin_m", "空化裕量"],
    "candidate_model": ["candidate_model", "候选型号", "标准候选型号"],
    "vendor_model": ["vendor_model", "厂家型号", "商品型号"],
    "vendor_datasheet_path": ["vendor_datasheet_path", "厂家数据表路径"],
    "vendor_datasheet_sha256": ["vendor_datasheet_sha256", "厂家数据表sha256"],
    "vendor_curve_path": ["vendor_curve_path", "厂家曲线路径"],
    "vendor_curve_sha256": ["vendor_curve_sha256", "厂家曲线sha256"],
    "software_result_path": ["software_result_path", "软件结果路径", "edr结果路径"],
    "software_result_sha256": ["software_result_sha256", "软件结果sha256", "edr结果sha256"],
    "mechanical_result_path": ["mechanical_result_path", "机械计算路径", "sw6结果路径"],
    "mechanical_result_sha256": ["mechanical_result_sha256", "机械计算sha256", "sw6结果sha256"],
    "internals_result_path": ["internals_result_path", "塔内件结果路径", "columninternals结果路径"],
    "internals_result_sha256": ["internals_result_sha256", "塔内件结果sha256", "columninternals结果sha256"],
    "relief_result_path": ["relief_result_path", "泄放计算路径"],
    "relief_result_sha256": ["relief_result_sha256", "泄放计算sha256"],
    "stress_result_path": ["stress_result_path", "应力计算路径"],
    "stress_result_sha256": ["stress_result_sha256", "应力计算sha256"],
    "standard_lookup_path": ["standard_lookup_path", "标准查表路径"],
    "standard_lookup_sha256": ["standard_lookup_sha256", "标准查表sha256"],
    "compatibility_result_path": ["compatibility_result_path", "相容性校核路径"],
    "compatibility_result_sha256": ["compatibility_result_sha256", "相容性校核sha256"],
    "primary_literature_path": ["primary_literature_path", "原始文献路径"],
    "primary_literature_sha256": ["primary_literature_sha256", "原始文献sha256"],
    "process_guarantee_path": ["process_guarantee_path", "性能保证路径"],
    "process_guarantee_sha256": ["process_guarantee_sha256", "性能保证sha256"],
    "formal_calculation_path": ["formal_calculation_path", "正式计算书路径"],
    "formal_calculation_sha256": ["formal_calculation_sha256", "正式计算书sha256"],
    "evidence_manifest_path": ["evidence_manifest_path", "证据清单路径", "证据manifest路径"],
    "evidence_manifest_sha256": ["evidence_manifest_sha256", "证据清单sha256", "证据manifestsha256"],
    "audit_approval_path": ["audit_approval_path", "独立审核批准记录路径", "审核批准路径"],
    "audit_approval_sha256": ["audit_approval_sha256", "独立审核批准记录sha256", "审核批准sha256"],
    "verification_result": ["verification_result", "核验结果", "校核结果"],
    "approval_status": ["approval_status", "批准状态", "审批状态"]
}


STRING_FIELDS = {
    "equipment_tag", "equipment_family", "equipment_type", "terminal_type_rule_override_id", "aspen_block_type",
    "process_function", "phase", "pressure_basis", "design_pressure_basis", "volume_basis",
    "material", "tube_material_grade", "shell_material_grade", "insulation_spec", "protective_layer",
    "wall_series", "fitting_type", "head_type", "membrane_geometry_type",
    "npshr_evidence_scope", "surge_margin_evidence_scope",
    "connection_type", "pressure_class", "flange_face", "gasket_material",
    "valve_function", "candidate_model", "vendor_model", "vendor_datasheet_sha256",
    "vendor_datasheet_path", "vendor_curve_path", "software_result_path", "mechanical_result_path",
    "internals_result_path", "relief_result_path", "stress_result_path", "standard_lookup_path",
    "compatibility_result_path", "primary_literature_path", "process_guarantee_path", "formal_calculation_path",
    "evidence_manifest_path", "audit_approval_path",
    "vendor_curve_sha256", "software_result_sha256", "mechanical_result_sha256",
    "internals_result_sha256", "relief_result_sha256", "stress_result_sha256",
    "standard_lookup_sha256", "compatibility_result_sha256", "primary_literature_sha256",
    "process_guarantee_sha256", "formal_calculation_sha256", "verification_result",
    "evidence_manifest_sha256", "audit_approval_sha256",
    "approval_status", "crystallization_mode", "solubility_profile_ref", "solubility_profile_sha256",
    "crystal_component_mapping", "separation_type", "wash_requirement", "dryer_model_kind",
    "moisture_basis", "water_component_mapping", "heat_source", "offgas_route"
}


EVIDENCE_PAIRS = {
    "vendor_datasheet_sha256": "vendor_datasheet_path",
    "vendor_curve_sha256": "vendor_curve_path",
    "software_result_sha256": "software_result_path",
    "mechanical_result_sha256": "mechanical_result_path",
    "internals_result_sha256": "internals_result_path",
    "relief_result_sha256": "relief_result_path",
    "stress_result_sha256": "stress_result_path",
    "standard_lookup_sha256": "standard_lookup_path",
    "compatibility_result_sha256": "compatibility_result_path",
    "primary_literature_sha256": "primary_literature_path",
    "process_guarantee_sha256": "process_guarantee_path",
    "formal_calculation_sha256": "formal_calculation_path",
    "evidence_manifest_sha256": "evidence_manifest_path",
    "audit_approval_sha256": "audit_approval_path",
}
NUMERIC_FIELDS = set(FIELD_ALIASES) - STRING_FIELDS
EVIDENCE_KIND_BY_HASH_FIELD = {
    "vendor_datasheet_sha256": "vendor_datasheet",
    "vendor_curve_sha256": "vendor_curve",
    "software_result_sha256": "software_result",
    "mechanical_result_sha256": "mechanical_result",
    "internals_result_sha256": "internals_result",
    "relief_result_sha256": "relief_result",
    "stress_result_sha256": "stress_result",
    "standard_lookup_sha256": "standard_lookup",
    "compatibility_result_sha256": "compatibility_result",
    "primary_literature_sha256": "primary_literature",
    "process_guarantee_sha256": "process_guarantee",
    "formal_calculation_sha256": "formal_calculation",
}


class NormalizationError(ValueError):
    def __init__(self, code: str, **details: Any) -> None:
        super().__init__(code)
        self.code = code
        self.details = details


def unit_group(field: str) -> str | None:
    if field.endswith("pressure_mpa"):
        return "pressure"
    if field in {"pressure_drop_kpa", "allowable_pressure_drop_kpa", "maximum_pressure_drop_kpa"}:
        return "pressure_drop"
    if field == "flow_m3_h":
        return "volume_flow"
    if field == "mass_flow_kg_h":
        return "mass_flow"
    if field.endswith("temperature_c") or field == "temperature_c":
        return "temperature"
    if field in {
        "diameter_mm", "height_mm", "inner_diameter_mm", "straight_shell_length_mm",
        "tube_outer_diameter_mm", "tube_length_mm", "selected_outer_diameter_mm",
        "selected_wall_thickness_mm", "channel_inner_diameter_mm",
        "cylinder_calculated_thickness_mm", "head_calculated_thickness_mm",
    }:
        return "length_mm"
    if field in {"efficiency_percent", "recovery_percent", "surge_margin_percent", "required_surge_margin_percent"}:
        return "percent"
    if field in {
        "head_m", "pressure_drop_head_component_m", "npsha_m", "npshr_m",
        "required_npsh_margin_m", "cavitation_margin_m", "tower_internal_height_m",
    }:
        return "length_m"
    if field == "density_kg_m3":
        return "density"
    if field in {
        "heat_duty_kw", "shaft_power_kw", "hydraulic_power_kw",
        "pressure_drop_power_component_kw", "pressure_component_shaft_power_screening_kw",
    }:
        return "power"
    if field in {"heat_transfer_area_m2", "membrane_area_m2"}:
        return "area"
    if field == "retention_time_min":
        return "time_min"
    if field == "target_velocity_m_s":
        return "velocity"
    return None


def declared_unit(text: Any, group: str | None) -> str | None:
    if group is None:
        return None
    raw = str(text).casefold().replace("³", "3").replace("²", "2").replace("·", "").replace("每", "/")
    compact = re.sub(r"\s+", "", raw)
    if group in {"pressure", "pressure_drop"}:
        if "mpa" in compact:
            return "MPa"
        if "kpa" in compact:
            return "kPa"
        if "bar" in compact:
            return "bar"
        if re.search(r"(?:^|[^mk])pa(?:$|[^a-z])", raw):
            return "Pa"
    elif group == "volume_flow":
        if any(item in compact for item in ("m3/min", "m^3/min", "m3_min", "立方米/分钟")):
            return "m3/min"
        if any(item in compact for item in ("m3/s", "m^3/s", "m3_s", "立方米/秒")):
            return "m3/s"
        if any(item in compact for item in ("l/s", "l_s", "升/秒")):
            return "L/s"
        if any(item in compact for item in ("m3/h", "m^3/h", "m3_h", "立方米/小时", "立方米/时")):
            return "m3/h"
    elif group == "mass_flow":
        if any(item in compact for item in ("kg/s", "kg_s", "千克/秒")):
            return "kg/s"
        if any(item in compact for item in ("t/h", "t_h", "吨/小时", "吨/时")):
            return "t/h"
        if any(item in compact for item in ("kg/h", "kg_h", "千克/小时", "千克/时")):
            return "kg/h"
    elif group == "temperature":
        if any(item in compact for item in ("°c", "℃", "degc")) or re.search(r"temperature_?c(?:$|\W)", raw):
            return "C"
        if re.search(r"(?:^|[_\W])k(?:$|[_\W])", raw) or "temperature_k" in raw:
            return "K"
    elif group == "length_mm":
        if "mm" in compact:
            return "mm"
        if re.search(r"(?:^|[_\W])m(?:$|[_\W])", raw) or re.search(r"(?:diameter|height)_?m(?:$|\W)", raw):
            return "m"
    elif group == "length_m":
        if "mm" in compact:
            return "mm"
        if re.search(r"(?:^|[_\W])m(?:$|[_\W])", raw) or raw.rstrip().endswith("_m"):
            return "m"
    elif group == "percent":
        if "%" in raw or "percent" in compact:
            return "percent"
        if "fraction" in compact:
            return "fraction"
    elif group == "density":
        if any(item in compact for item in ("kg/m3", "kg/m^3", "千克/立方米")):
            return "kg/m3"
    elif group == "power":
        if "mw" in compact:
            return "MW"
        if "kw" in compact:
            return "kW"
        if re.search(r"(?:^|[_\W])w(?:$|[_\W])", raw):
            return "W"
    elif group == "area":
        if any(item in compact for item in ("m2", "m^2", "平方米")):
            return "m2"
    elif group == "time_min":
        if any(item in compact for item in ("min", "分钟")):
            return "min"
        if re.search(r"(?:^|[_\W])h(?:$|[_\W])", raw) or "小时" in raw:
            return "h"
        if re.search(r"(?:^|[_\W])s(?:$|[_\W])", raw) or "秒" in raw:
            return "s"
    elif group == "velocity":
        if any(item in compact for item in ("m/s", "米/秒")):
            return "m/s"
    return None


def contains_unit_text(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    remainder = re.sub(r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?(?:[eE][-+]?\d+)?", "", value)
    remainder = re.sub(r"[\s,，.。()（）]+", "", remainder)
    return bool(remainder)


def token(value: Any) -> str:
    text = str(value or "").casefold().strip()
    return re.sub(r"[\s_\-—–·•:：;；,，.。/\\()（）\[\]{}]+", "", text)


def load_customer_output_profiles(
    path: Path = CUSTOMER_OUTPUT_PROFILES_PATH,
    *,
    required: bool = False,
) -> dict[str, Any]:
    """Load the original-artifact-bound customer delivery field profiles.

    The profile is an output/interface authority only.  Its historical example
    values are deliberately absent and it never supplies a design default.
    """
    if not path.is_file():
        if required:
            raise FileNotFoundError(f"customer output profile is missing: {path}")
        return {}
    document = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(document, dict):
        raise ValueError("customer output profile must be a JSON object")
    return document


def _profile_items(document: dict[str, Any]) -> list[dict[str, Any]]:
    raw = document.get("profiles", document.get("families", []))
    if isinstance(raw, dict):
        items = []
        for profile_id, value in raw.items():
            if isinstance(value, dict):
                items.append({"profile_id": profile_id, **value})
        return items
    return [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []


def _profile_field_id(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        for key in ("field_id", "canonical_id", "canonical_field", "id", "name"):
            candidate = str(value.get(key, "")).strip()
            if candidate:
                return candidate
    return None


def _customer_field_definitions(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}

    def merge(field_id: str, value: dict[str, Any], *, prefer_existing: bool = True) -> None:
        existing = dict(result.get(field_id, {}))
        aliases = [str(item).strip() for item in existing.get("aliases", []) if str(item).strip()]
        for label in (existing.get("label"), value.get("label")):
            if isinstance(label, str) and label.strip():
                aliases.append(label.strip())
        aliases.extend(str(item).strip() for item in value.get("aliases", []) if str(item).strip())
        combined = ({**value, **existing} if prefer_existing else {**existing, **value})
        combined["aliases"] = list(dict.fromkeys(aliases))
        result[field_id] = combined

    for key in ("global_output_columns", "common_delivery_fields"):
        raw_global = document.get(key, [])
        if isinstance(raw_global, list):
            for value in raw_global:
                field_id = _profile_field_id(value)
                if field_id and isinstance(value, dict):
                    merge(field_id, value)
    raw_definitions = document.get(
        "field_definitions",
        document.get("canonical_field_definitions", {}),
    )
    if isinstance(raw_definitions, dict):
        for field_id, value in raw_definitions.items():
            if isinstance(value, dict):
                merge(str(field_id), value, prefer_existing=False)
    elif isinstance(raw_definitions, list):
        for value in raw_definitions:
            field_id = _profile_field_id(value)
            if field_id and isinstance(value, dict):
                merge(field_id, value, prefer_existing=False)
    for profile in _profile_items(document):
        for key in ("fields", "required_fields", "output_fields"):
            raw_fields = profile.get(key, [])
            if not isinstance(raw_fields, list):
                continue
            for value in raw_fields:
                field_id = _profile_field_id(value)
                if field_id and isinstance(value, dict):
                    merge(field_id, value)
    return result


CUSTOMER_OUTPUT_PROFILE_DOCUMENT = load_customer_output_profiles()
CUSTOMER_FIELD_DEFINITIONS = _customer_field_definitions(CUSTOMER_OUTPUT_PROFILE_DOCUMENT)
# Some authority-table headers are service-specific labels rather than globally
# interchangeable field names.  A bare Chinese "塔径" denotes the tower shell
# inside diameter in the hydraulic/mechanical chain; it must not be silently
# retained by the earlier generic diameter field merely because the customer
# table historically stored that column under ``diameter_mm``.
CANONICAL_ALIAS_OWNER_OVERRIDES = {
    token("塔径"): "inner_diameter_mm",
}
for _field_id, _meta in CUSTOMER_FIELD_DEFINITIONS.items():
    if bool(_meta.get("output_only", False)):
        continue
    _aliases = [
        str(item).strip()
        for item in _meta.get("aliases", [])
        if str(item).strip()
        and CANONICAL_ALIAS_OWNER_OVERRIDES.get(token(item), _field_id) == _field_id
    ]
    _label = str(_meta.get("label", "")).strip()
    if (
        _label
        and CANONICAL_ALIAS_OWNER_OVERRIDES.get(token(_label), _field_id) == _field_id
    ):
        _aliases.append(_label)
    FIELD_ALIASES.setdefault(_field_id, [])
    FIELD_ALIASES[_field_id] = list(dict.fromkeys([_field_id, *FIELD_ALIASES[_field_id], *_aliases]))
    _declared_type = _meta.get("data_type", _meta.get("type"))
    if _declared_type is not None:
        _data_type = str(_declared_type).casefold()
        if _data_type in {"number", "integer", "float", "decimal"}:
            STRING_FIELDS.discard(_field_id)
            NUMERIC_FIELDS.add(_field_id)
        else:
            STRING_FIELDS.add(_field_id)
            NUMERIC_FIELDS.discard(_field_id)
    elif _field_id not in NUMERIC_FIELDS and _field_id not in STRING_FIELDS:
        STRING_FIELDS.add(_field_id)
    _unit = _meta.get("unit")
    if isinstance(_unit, str) and _unit.strip():
        FIELD_UNITS.setdefault(_field_id, _unit.strip())

for _reserved_alias, _owner in CANONICAL_ALIAS_OWNER_OVERRIDES.items():
    FIELD_ALIASES.setdefault(_owner, [])
    if not any(token(_alias) == _reserved_alias for _alias in FIELD_ALIASES[_owner]):
        FIELD_ALIASES[_owner].append("塔径")


def canonical_phase(value: Any) -> str | None:
    wanted = token(value)
    return next(
        (name for name, aliases in PHASE_WORDS.items() if wanted in {token(alias) for alias in aliases}),
        None,
    )


def _canonical_from_words(value: Any, registry: dict[str, set[str]]) -> str | None:
    wanted = token(value)
    return next(
        (name for name, aliases in registry.items() if wanted in {token(alias) for alias in aliases}),
        None,
    )


ALIAS_TO_FIELD: dict[str, str] = {}
ALIAS_COLLISIONS: list[dict[str, str]] = []
for canonical, aliases in FIELD_ALIASES.items():
    for alias in aliases + [canonical]:
        normalized_alias = token(alias)
        previous = ALIAS_TO_FIELD.get(normalized_alias)
        if previous is not None and previous != canonical:
            ALIAS_COLLISIONS.append({
                "alias": str(alias),
                "normalized_alias": normalized_alias,
                "retained_field": previous,
                "rejected_field": canonical,
            })
            continue
        ALIAS_TO_FIELD[normalized_alias] = canonical


def numeric(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?(?:[eE][-+]?\d+)?", str(value))
    return float(match.group(0).replace(",", "")) if match else None


def convert_numeric(field: str, value: Any, source_key: str) -> Any:
    if isinstance(value, str):
        matches = re.findall(r"(?<![A-Za-z^])[-+]?\d+(?:,\d{3})*(?:\.\d+)?(?:[eE][-+]?\d+)?", value)
        if len(matches) > 1:
            raise NormalizationError("MULTIPLE_NUMERIC_TOKENS", field=field, source_key=source_key, value=value)
    number = numeric(value)
    if number is None:
        return value
    if field == "selected_dn" and isinstance(value, str) and re.fullmatch(r"\s*DN\s*\d+(?:\.\d+)?\s*", value, re.IGNORECASE):
        return int(number) if number.is_integer() else number
    group = unit_group(field)
    key_unit = declared_unit(source_key, group)
    value_unit = declared_unit(value, group)
    if contains_unit_text(value) and value_unit is None:
        raise NormalizationError("UNSUPPORTED_OR_UNRECOGNIZED_UNIT", field=field, source_key=source_key, value=value)
    if key_unit and value_unit and key_unit != value_unit:
        raise NormalizationError("UNIT_CONFLICT", field=field, source_key=source_key, key_unit=key_unit, value_unit=value_unit, value=value)
    active_unit = value_unit or key_unit
    if group == "percent" and active_unit is None and 0 < number <= 1:
        raise NormalizationError("AMBIGUOUS_FRACTION_OR_PERCENT", field=field, source_key=source_key, value=value)
    if field.endswith("pressure_mpa"):
        if active_unit == "kPa":
            return number / 1000.0
        if active_unit == "bar":
            return number / 10.0
        if active_unit == "Pa":
            return number / 1_000_000.0
    if field in {"pressure_drop_kpa", "allowable_pressure_drop_kpa", "maximum_pressure_drop_kpa"}:
        if active_unit == "MPa":
            return number * 1000.0
        if active_unit == "bar":
            return number * 100.0
        if active_unit == "Pa":
            return number / 1000.0
    if field == "flow_m3_h":
        if active_unit == "m3/s":
            return number * 3600.0
        if active_unit == "m3/min":
            return number * 60.0
        if active_unit == "L/s":
            return number * 3.6
    if field == "mass_flow_kg_h":
        if active_unit == "kg/s":
            return number * 3600.0
        if active_unit == "t/h":
            return number * 1000.0
    if field.endswith("temperature_c") or field == "temperature_c":
        if active_unit == "K":
            return number - 273.15
    if field in {
        "diameter_mm", "height_mm", "inner_diameter_mm", "straight_shell_length_mm", "selected_outer_diameter_mm",
        "selected_wall_thickness_mm", "channel_inner_diameter_mm",
        "cylinder_calculated_thickness_mm", "head_calculated_thickness_mm",
    }:
        if active_unit == "m":
            return number * 1000.0
    if field in {"efficiency_percent", "recovery_percent", "surge_margin_percent", "required_surge_margin_percent"}:
        if active_unit == "fraction":
            return number * 100.0
    if field in {"head_m", "pressure_drop_head_component_m", "npsha_m", "npshr_m", "required_npsh_margin_m", "cavitation_margin_m"} and active_unit == "mm":
        return number / 1000.0
    if field in {
        "heat_duty_kw", "shaft_power_kw", "hydraulic_power_kw",
        "pressure_drop_power_component_kw", "pressure_component_shaft_power_screening_kw",
    }:
        if active_unit == "MW":
            return number * 1000.0
        if active_unit == "W":
            return number / 1000.0
    if field == "retention_time_min":
        if active_unit == "h":
            return number * 60.0
        if active_unit == "s":
            return number / 60.0
    return number


def normalize_record(record: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    normalized: dict[str, Any] = {}
    conflicts: list[dict[str, Any]] = []
    unmapped: dict[str, Any] = {}
    for raw_key, raw_value in record.items():
        canonical = ALIAS_TO_FIELD.get(token(raw_key))
        if not canonical:
            unmapped[str(raw_key)] = raw_value
            continue
        try:
            if canonical in STRING_FIELDS:
                if not isinstance(raw_value, str):
                    raise NormalizationError("NON_STRING_VALUE", field=canonical, source_key=str(raw_key), value_type=type(raw_value).__name__)
                value = raw_value.strip()
            else:
                value = convert_numeric(canonical, raw_value, str(raw_key))
            if canonical in {"pressure_basis", "design_pressure_basis"}:
                wanted = token(value)
                normalized_basis = next((name for name, words in PRESSURE_BASIS_WORDS.items() if wanted in {token(word) for word in words}), None)
                value = normalized_basis or value
            elif canonical == "phase":
                value = canonical_phase(value) or value
            elif canonical == "head_type":
                value = _canonical_from_words(value, HEAD_TYPE_WORDS) or value
            elif canonical == "membrane_geometry_type":
                value = _canonical_from_words(value, MEMBRANE_GEOMETRY_TYPE_WORDS) or value
            elif canonical == "volume_basis":
                value = _canonical_from_words(value, VOLUME_BASIS_WORDS) or value
            elif canonical == "npshr_evidence_scope":
                value = _canonical_from_words(value, NPSHR_EVIDENCE_SCOPE_WORDS) or value
        except NormalizationError as exc:
            conflicts.append({"field": canonical, "code": exc.code, **exc.details})
            continue
        if canonical in normalized and normalized[canonical] != value:
            conflicts.append({"field": canonical, "first": normalized[canonical], "second": value, "source_key": str(raw_key)})
        else:
            normalized[canonical] = value
    return normalized, conflicts, unmapped


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_rules(path: Path = RULES_PATH) -> dict[str, Any]:
    return load_json(path)


def load_model_rules(path: Path = MODEL_RULES_PATH) -> dict[str, Any]:
    return load_json(path)


def _profile_family_ids(profile: dict[str, Any]) -> list[str]:
    raw = profile.get(
        "family_ids",
        profile.get("algorithm_family_ids", profile.get("family_id", [])),
    )
    if isinstance(raw, str):
        return [raw]
    return [str(item) for item in raw if str(item).strip()] if isinstance(raw, list) else []


def _profile_field_ids(profile: dict[str, Any]) -> list[str]:
    fields: list[str] = []
    for key in ("fields", "required_fields", "output_fields"):
        raw = profile.get(key, [])
        if not isinstance(raw, list):
            continue
        for item in raw:
            field_id = _profile_field_id(item)
            if field_id:
                fields.append(field_id)
    return list(dict.fromkeys(fields))


def load_parameter_templates(path: Path = PARAMETER_TEMPLATES_PATH) -> dict[str, Any]:
    templates = load_json(path)
    if not isinstance(templates, dict):
        raise ValueError("parameter templates must be a JSON object")
    profiles = load_customer_output_profiles()
    definitions = templates.setdefault("parameter_definitions", {})
    if not isinstance(definitions, dict):
        raise ValueError("parameter_definitions must be an object")
    customer_definitions = _customer_field_definitions(profiles)
    for field_id, meta in customer_definitions.items():
        if bool(meta.get("output_only", False)):
            continue
        definitions[field_id] = {
            **{
                "label": meta.get("label", field_id.replace("_", " ")),
                "symbol": meta.get("symbol", field_id),
                "unit": meta.get("unit"),
                "data_type": meta.get(
                    "data_type",
                    meta.get("type", "number" if field_id in NUMERIC_FIELDS else "string"),
                ),
            },
            **definitions.get(field_id, {}),
        }
    common_fields = []
    raw_common = profiles.get(
        "common_delivery_fields",
        profiles.get("global_output_columns", []),
    ) if isinstance(profiles, dict) else []
    if isinstance(raw_common, list):
        common_fields = [field for item in raw_common if (field := _profile_field_id(item))]
    profile_items = _profile_items(profiles)
    for family in templates.get("families", []):
        if not isinstance(family, dict):
            continue
        family_id = str(family.get("family_id", ""))
        matched_profiles = [
            item for item in profile_items
            if family_id in _profile_family_ids(item)
        ]
        profile_ids = [
            str(item.get("profile_id", item.get("authority_section_id", item.get("id", "")))).strip()
            for item in matched_profiles
            if str(item.get("profile_id", item.get("authority_section_id", item.get("id", "")))).strip()
        ]
        customer_fields = list(common_fields)
        for profile in matched_profiles:
            customer_fields.extend(_profile_field_ids(profile))
        customer_fields = [
            field for field in dict.fromkeys(customer_fields)
            if not bool(customer_definitions.get(field, {}).get("output_only", False))
        ]
        existing_fields = {
            str(field)
            for group in family.get("groups", [])
            if isinstance(group, dict)
            for field in group.get("fields", [])
        }
        customer_fields = [field for field in customer_fields if field not in existing_fields]
        if customer_fields:
            family.setdefault("groups", []).append({
                "id": "customer_delivery",
                "title": "客户权威一览表交付字段",
                "fields": customer_fields,
            })
        family["customer_profile_ids"] = profile_ids
    templates["customer_output_profile"] = {
        "schema": profiles.get("schema") if isinstance(profiles, dict) else None,
        "version": profiles.get("version") if isinstance(profiles, dict) else None,
        "path": CUSTOMER_OUTPUT_PROFILES_PATH.name,
        "profile_count": len(profile_items),
    }
    return templates


def load_pump_standard_points(path: Path = PUMP_STANDARD_POINTS_PATH) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    numeric_fields = {
        "suction_diameter_mm", "discharge_diameter_mm", "impeller_nominal_diameter_mm",
        "speed_rpm", "design_flow_m3_h", "design_head_m",
        "source_pdf_page_1based", "source_printed_page",
    }
    parsed: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        for field in numeric_fields:
            value = item.get(field)
            if value not in (None, ""):
                number = float(value)
                item[field] = int(number) if number.is_integer() else number
        parsed.append(item)
    return parsed


def load_pipe_standard_dn_od(path: Path = PIPE_STANDARD_DN_OD_PATH) -> list[dict[str, Any]]:
    """Load the promoted GB/T 12459 DN-to-outer-diameter catalog.

    The table proves only the printed DN/NPS/D mapping. It does not supply a
    wall thickness, pressure rating, material, or final piping class.
    """
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    required_columns = {
        "dn", "nps", "outer_diameter_mm", "standard_id", "standard_version",
        "source_pdf_sha256", "physical_page", "source_table_asset_id",
        "source_row_1based", "reuse_class", "qa_status", "application_boundary",
    }
    if not rows or not required_columns.issubset(rows[0]):
        raise ValueError("pipe DN/OD catalog is empty or missing required columns")
    parsed: list[dict[str, Any]] = []
    seen_dn: set[float] = set()
    for row in rows:
        if row.get("reuse_class") != "DIRECT_REUSE_VERIFIED":
            raise ValueError("pipe DN/OD catalog contains a non-promoted row")
        dn = float(row["dn"])
        outer_diameter = float(row["outer_diameter_mm"])
        if dn <= 0 or outer_diameter <= 0 or dn in seen_dn:
            raise ValueError("pipe DN/OD catalog contains an invalid or duplicate DN")
        if not re.fullmatch(r"[A-F0-9]{64}", str(row.get("source_pdf_sha256", ""))):
            raise ValueError("pipe DN/OD catalog contains an invalid source hash")
        item = dict(row)
        item["dn"] = int(dn) if dn.is_integer() else dn
        item["outer_diameter_mm"] = outer_diameter
        item["physical_page"] = int(float(row["physical_page"]))
        item["source_row_1based"] = int(float(row["source_row_1based"]))
        parsed.append(item)
        seen_dn.add(dn)
    return sorted(parsed, key=lambda item: (float(item["outer_diameter_mm"]), float(item["dn"])))


def select_pipe_standard_dn(
    required_inner_diameter_mm: float,
    selected_wall_thickness_mm: float,
    catalog: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    required_inner_diameter_mm = float(required_inner_diameter_mm)
    selected_wall_thickness_mm = float(selected_wall_thickness_mm)
    if required_inner_diameter_mm <= 0 or selected_wall_thickness_mm <= 0:
        raise ValueError("required inner diameter and provisional wall thickness must be positive")
    rows = catalog if catalog is not None else load_pipe_standard_dn_od()
    for row in rows:
        available_inner = float(row["outer_diameter_mm"]) - 2.0 * selected_wall_thickness_mm
        if available_inner >= required_inner_diameter_mm:
            return {**row, "available_inner_diameter_mm": available_inner}
    raise ValueError("required inner diameter exceeds the promoted GB/T 12459 DN/OD catalog")


def load_graph(path: Path | None = None) -> dict[str, Any]:
    # Resolve at call time so packaged adapters can point the matcher at the
    # bundled authority graph after module import.
    return load_json(path or GRAPH_PATH)


def load_records(path: Path | None, inline_json: str | None) -> list[dict[str, Any]]:
    if (path is None) == (inline_json is None):
        raise ValueError("exactly one of --input or --json is required")
    if inline_json is not None:
        payload = json.loads(inline_json)
    elif path and path.suffix.casefold() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            return [dict(row) for row in csv.DictReader(stream)]
    else:
        payload = load_json(path)  # type: ignore[arg-type]
    if isinstance(payload, dict) and isinstance(payload.get("equipment"), list):
        payload = payload["equipment"]
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise ValueError("input must be a JSON object, JSON array, {'equipment': [...]}, or CSV")
    return payload


def resolve_family_name(value: str, families: list[dict[str, Any]], graph_nodes: dict[str, dict[str, Any]]) -> str | None:
    wanted = token(value)
    hits: list[str] = []
    for rule in families:
        node = graph_nodes.get(rule["id"], {})
        names = [rule["id"], node.get("name", ""), *rule.get("aliases", [])]
        if any(token(name) == wanted for name in names):
            hits.append(rule["id"])
    return hits[0] if len(set(hits)) == 1 else None


def compatible(left: str, right: str) -> bool:
    return left == right or frozenset({left, right}) in COMPATIBLE_FAMILY_PAIRS


def match_family(params: dict[str, Any], rules: dict[str, Any], graph: dict[str, Any]) -> dict[str, Any]:
    families = rules["families"]
    family_by_id = {rule["id"]: rule for rule in families}
    graph_nodes = {node["id"]: node for node in graph["nodes"]}
    scores: dict[str, int] = {rule["id"]: 0 for rule in families}
    reasons: dict[str, list[str]] = {rule["id"]: [] for rule in families}
    strong_sources: dict[str, str] = {}

    explicit = params.get("equipment_family")
    if explicit:
        family_id = resolve_family_name(str(explicit), families, graph_nodes)
        if not family_id:
            return {"status": "BLOCKED_UNKNOWN_EXPLICIT_FAMILY", "input": explicit, "candidates": []}
        scores[family_id] += 1_000_000
        reasons[family_id].append("explicit_family")
        strong_sources["explicit_family"] = family_id

    equipment_type = token(params.get("equipment_type"))
    exact_type_hits: set[str] = set()
    contained_type_hits: set[str] = set()
    if equipment_type:
        for rule in families:
            aliases = [token(alias) for alias in rule.get("aliases", [])]
            if equipment_type in aliases:
                scores[rule["id"]] += 100_000
                reasons[rule["id"]].append("exact_equipment_type_alias")
                exact_type_hits.add(rule["id"])
            else:
                contained = [alias for alias in aliases if len(alias) >= 2 and alias in equipment_type]
                if contained:
                    scores[rule["id"]] += 10_000 + max(len(alias) for alias in contained)
                    reasons[rule["id"]].append("contained_equipment_type_alias")
                    contained_type_hits.add(rule["id"])
    if len(exact_type_hits) == 1:
        strong_sources["equipment_type"] = next(iter(exact_type_hits))
    elif len(exact_type_hits) > 1:
        return {"status": "BLOCKED_AMBIGUOUS_TYPE_ALIAS", "input": params.get("equipment_type"), "candidates": sorted(exact_type_hits)}
    elif len(contained_type_hits) == 1:
        strong_sources["equipment_type"] = next(iter(contained_type_hits))
    elif len(contained_type_hits) > 1:
        return {"status": "BLOCKED_AMBIGUOUS_TYPE_ALIAS", "input": params.get("equipment_type"), "candidates": sorted(contained_type_hits)}

    block_type = str(params.get("aspen_block_type", "")).strip().upper()
    strong_block_hits: set[str] = set()
    if block_type:
        for rule in families:
            if block_type in {str(item).upper() for item in rule.get("block_types", [])}:
                scores[rule["id"]] += 2500
                reasons[rule["id"]].append("exact_aspen_block_type")
                strong_block_hits.add(rule["id"])
            elif block_type in {str(item).upper() for item in rule.get("weak_block_types", [])}:
                scores[rule["id"]] += 600
                reasons[rule["id"]].append("weak_aspen_block_type_review_only")
    if len(strong_block_hits) == 1:
        strong_sources["aspen_block_type"] = next(iter(strong_block_hits))
    elif len(strong_block_hits) > 1:
        return {"status": "BLOCKED_AMBIGUOUS_BLOCK_TYPE", "input": block_type, "candidates": sorted(strong_block_hits)}

    process_text = token(params.get("process_function"))
    process_hits: set[str] = set()
    if process_text:
        process_lengths: dict[str, int] = {}
        for rule in families:
            hits = [token(word) for word in rule.get("process_keywords", []) if token(word) in process_text]
            if hits:
                process_lengths[rule["id"]] = max(len(hit) for hit in hits)
        if process_lengths:
            most_specific_length = max(process_lengths.values())
            process_hits = {
                family_id for family_id, length in process_lengths.items()
                if length == most_specific_length
            }
            process_anchor = sorted(process_hits)[0]
            incompatible_process_hits = {
                family_id for family_id in process_lengths
                if not compatible(process_anchor, family_id)
            }
            if incompatible_process_hits:
                return {
                    "status": "BLOCKED_AMBIGUOUS_PROCESS_FUNCTION",
                    "input": params.get("process_function"),
                    "candidates": sorted(process_lengths),
                }
            for family_id, length in process_lengths.items():
                if family_id in process_hits:
                    scores[family_id] += 5000 + length
                    reasons[family_id].append("most_specific_process_function_keyword")
                else:
                    scores[family_id] += 500 + length
                    reasons[family_id].append("broader_process_function_keyword")
            if len(process_hits) == 1:
                process_family = next(iter(process_hits))
                strong_sources["process_function"] = process_family
                # Aspen blocks such as HEATX/COMPR are reusable generic
                # mechanisms.  When the selected family explicitly declares
                # that block as weak-compatible, the more specific physical
                # function controls identity and the block remains trace only.
                weak_types = {
                    str(item).upper()
                    for item in family_by_id[process_family].get("weak_block_types", [])
                }
                if block_type in weak_types:
                    strong_sources.pop("aspen_block_type", None)

    # COMPR/MCOMPR can be used as a generic pressure-changing mechanism in
    # source models.  A verified pressure direction must prevent a compressor
    # identity when the actual duty is expansion.  Phase narrows gas versus
    # liquid expansion; without phase, retain both candidates.
    if block_type in {"COMPR", "MCOMPR"} and present(params, "inlet_pressure_mpa") and present(params, "outlet_pressure_mpa"):
        pin = float(params["inlet_pressure_mpa"])
        pout = float(params["outlet_pressure_mpa"])
        if pin > pout:
            strong_sources.pop("aspen_block_type", None)
            phase = canonical_phase(params.get("phase"))
            if phase == "liquid":
                direction_families = ["family_liquid_power_recovery_turbine"]
            elif phase == "vapor":
                direction_families = ["family_gas_expander_turbine"]
            else:
                direction_families = [
                    "family_liquid_power_recovery_turbine",
                    "family_gas_expander_turbine",
                ]
            for family_id in direction_families:
                scores[family_id] += 3200
                reasons[family_id].append("pressure_direction_expansion_hint")
            if len(direction_families) == 1:
                strong_sources["pressure_direction_and_phase"] = direction_families[0]

    tag = str(params.get("equipment_tag", "")).strip().upper()
    if tag:
        for rule in families:
            if any(re.search(pattern, tag, flags=re.IGNORECASE) for pattern in rule.get("tag_patterns", [])):
                scores[rule["id"]] += 100
                reasons[rule["id"]].append("tag_pattern_review_only")

    strong_values = list(strong_sources.values())
    if strong_values:
        anchor = strong_values[0]
        conflicts = {source: family for source, family in strong_sources.items() if not compatible(anchor, family)}
        if conflicts:
            return {"status": "BLOCKED_IDENTITY_CONFLICT", "strong_sources": strong_sources, "candidates": []}

    ranked = sorted(
        (
            {
                "family_id": rule["id"],
                "family_name": graph_nodes.get(rule["id"], {}).get("name", rule["id"]),
                "score": scores[rule["id"]],
                "reasons": reasons[rule["id"]],
                "priority": rule.get("priority", 9999),
            }
            for rule in families if scores[rule["id"]] > 0
        ),
        key=lambda item: (-item["score"], item["priority"], item["family_id"]),
    )
    if not ranked or ranked[0]["score"] < int(rules.get("minimum_decisive_score", 1000)):
        return {"status": "BLOCKED_MISSING_DECISIVE_IDENTITY", "candidates": ranked}
    top_score = ranked[0]["score"]
    top = [item for item in ranked if item["score"] == top_score]
    if len(top) > 1:
        return {"status": "BLOCKED_AMBIGUOUS_MATCH", "candidates": top}
    selected = dict(top[0])
    selected["status"] = "MATCHED"
    selected["candidates"] = ranked
    return selected


def source_doc_id(graph_node_id: str) -> str:
    return re.sub(r"^std_([a-z]+)t_", r"std_\1_t_", graph_node_id)


def standard_routes(family_id: str, graph: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = {node["id"]: node for node in graph["nodes"]}
    routes: list[dict[str, Any]] = []
    edge_pairs: list[tuple[dict[str, Any], dict[str, Any] | None]] = []
    for first in graph["edges"]:
        node = nodes.get(first.get("from", ""))
        if not node or node.get("type") != "standard":
            continue
        if first.get("to") == family_id:
            edge_pairs.append((first, None))
            continue
        for second in graph["edges"]:
            if second.get("from") == first.get("to") and second.get("to") == family_id:
                edge_pairs.append((first, second))
    restriction_order = {"direct_reuse": 0, "method_only": 1, "software_boundary": 2, "vendor_boundary": 3, "forbidden_transfer": 4}
    for edge, second in edge_pairs:
        node = nodes[edge["from"]]
        status = str(node.get("status", "unknown"))
        relation_parts = [str(edge.get("relation", ""))]
        path = [node["id"], edge.get("to")]
        classes = [edge.get("reuse_class")]
        if second:
            relation_parts.append(str(second.get("relation", "")))
            path.append(family_id)
            classes.append(second.get("reuse_class"))
        relation = " -> ".join(part for part in relation_parts if part)
        explicit_classes = [item for item in classes if item]
        reuse_class = max(explicit_classes, key=lambda item: restriction_order.get(item, 99)) if explicit_classes else None
        if not reuse_class:
            if status in {"obsolete", "withdrawn"} or any(word in relation for word in ("obsolete", "historical", "wrong_scope")):
                reuse_class = "forbidden_transfer"
            elif node.get("authority") in {"A2", "A3", "A4"} and status == "current":
                reuse_class = "direct_reuse"
            else:
                reuse_class = "method_only"
        doc_id = source_doc_id(node["id"])
        status_path = SOURCE_LAYER_DOCUMENTS / doc_id / "status.json"
        package: dict[str, Any] = {}
        if status_path.exists():
            raw = load_json(status_path)
            package = {
                "doc_id": raw.get("doc_id"),
                "package_state": raw.get("status"),
                "source_pdf_sha256": raw.get("source_pdf_sha256"),
                "page_count": raw.get("page_count"),
                "manual_review_page_count": len(raw.get("manual_review_pages", [])),
                "status_path": str(status_path),
            }
        routes.append(
            {
                "node_id": node["id"],
                "number": node.get("number"),
                "title": node.get("title"),
                "standard_status": status,
                "authority": node.get("authority"),
                "relation": relation,
                "path": path,
                "reuse_class": reuse_class,
                "automatic_routing_allowed": reuse_class != "forbidden_transfer",
                "automatic_numeric_reuse_allowed": False,
                "does_not_prove": node.get("does_not_prove", []),
                "graph_local_source": node.get("local_source"),
                "source_layer": package or {"doc_id": doc_id, "package_state": "NOT_IN_SOURCE_LAYER"},
            }
        )
    return sorted(routes, key=lambda item: (item["reuse_class"] == "forbidden_transfer", item["number"] or "", item["node_id"], "|".join(str(x) for x in item["path"])))


def vendor_routes(family_id: str, graph: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = {node["id"]: node for node in graph["nodes"]}
    result: list[dict[str, Any]] = []
    for edge in graph["edges"]:
        node = nodes.get(edge.get("from", ""))
        if edge.get("to") != family_id or not node or node.get("type") != "manufacturer_source":
            continue
        result.append(
            {
                "node_id": node["id"],
                "manufacturer": node.get("manufacturer"),
                "scope": node.get("scope"),
                "relation": edge.get("relation"),
                "reuse_class": edge.get("reuse_class", "vendor_boundary"),
                "official_url": node.get("official_url"),
                "local_path": node.get("local_path"),
                "sha256": node.get("sha256"),
            }
        )
    return sorted(result, key=lambda item: item["node_id"])


def present(params: dict[str, Any], field: str) -> bool:
    return field in params and params[field] is not None and str(params[field]).strip() != ""


FALLBACK_PROCESS_FIELDS = {
    "phase", "flow_m3_h", "mass_flow_kg_h", "density_kg_m3",
    "inlet_pressure_mpa", "outlet_pressure_mpa", "operating_pressure_mpa",
    "pressure_basis", "temperature_c", "inlet_temperature_c",
    "gas_molecular_weight", "compressibility_factor", "heat_duty_kw",
    "overall_u_w_m2k", "lmtd_k", "lmtd_correction_factor",
    "allowable_pressure_drop_kpa", "target_velocity_m_s", "efficiency_percent",
}
FALLBACK_CONSTRUCTION_FIELDS = {
    "material", "head_type", "allowable_stress_mpa", "weld_efficiency",
    "fill_fraction", "retention_time_min", "tray_spacing_mm",
    "tower_downcomer_area_fraction", "tower_receiving_area_fraction",
    "tower_inactive_area_fraction", "tower_open_area_fraction",
    "tower_weir_length_ratio", "tower_weir_height_mm",
    "tower_downcomer_residence_time_s", "tower_top_bottom_allowance_mm",
    "tube_outer_diameter_mm", "tube_length_mm", "shell_pass_count",
    "tube_material_grade", "shell_material_grade", "insulation_spec", "protective_layer",
}


def _fallback_context_text(params: dict[str, Any]) -> str:
    return " ".join(
        str(params.get(field, ""))
        for field in (
            "equipment_type", "process_function", "main_medium", "medium",
            "dominant_components", "phase", "aspen_block_type",
        )
        if present(params, field)
    ).casefold()


def _material_fallback(policy: dict[str, Any], params: dict[str, Any]) -> tuple[Any, str, str, list[str]]:
    text = _fallback_context_text(params)
    temperatures = [
        float(params[field])
        for field in ("temperature_c", "inlet_temperature_c", "design_temperature_c")
        if present(params, field) and isinstance(params[field], (int, float))
    ]
    for profile in policy.get("material_profiles", []):
        if not isinstance(profile, dict):
            continue
        markers = [str(item).casefold() for item in profile.get("markers", [])]
        marker_match = bool(markers and any(marker in text for marker in markers))
        low_match = (
            profile.get("temperature_max_c") is not None
            and temperatures
            and min(temperatures) <= float(profile["temperature_max_c"])
        )
        high_match = (
            profile.get("temperature_min_c") is not None
            and temperatures
            and max(temperatures) >= float(profile["temperature_min_c"])
        )
        if marker_match or low_match or high_match:
            return (
                profile.get("recommended_value"),
                "KNOWLEDGE_GRAPH_CONDITIONAL_RECOMMENDATION",
                str(profile.get("warning") or "材料路线仍需同介质相容性与机械设计确认。"),
                [f"material_profile:{profile.get('id', 'unnamed')}", f"context:{text or 'not_provided'}"],
            )
    value = policy.get("common_defaults", {}).get("generic_material", "碳钢（预设计经济基线）")
    return (
        value,
        "EXPLICIT_FINAL_FALLBACK_DEFAULT",
        "介质腐蚀性、洁净要求和温度材料边界尚未闭合；该材料仅是预设计经济基线。",
        ["no_specific_material_profile_matched"],
    )


def _exchanger_u_fallback(params: dict[str, Any], default_value: float) -> tuple[float, list[str]]:
    text = _fallback_context_text(params)
    if any(marker in text for marker in ("冷凝", "condens")):
        return 700.0, ["service_marker:condensing"]
    if any(marker in text for marker in ("再沸", "蒸发", "沸腾", "reboil", "evapor", "boil")):
        return 500.0, ["service_marker:boiling_or_evaporation"]
    if any(marker in text for marker in ("气气", "gas-gas", "gas to gas")):
        return 50.0, ["service_marker:gas_gas"]
    if canonical_phase(params.get("phase")) == "vapor" or any(marker in text for marker in ("气体", "gas")):
        return 100.0, ["service_marker:gas_side_present"]
    return float(default_value), ["service_profile:generic_liquid_or_unknown"]


def apply_design_fallbacks(
    family_id: str,
    params: dict[str, Any],
    rule: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Apply the registered last-resort design basis without disguising it as input.

    Supplied values always win. Every inserted value is J/provisional, carries
    its own warning and is capped at preliminary calculation/type screening.
    """
    model_rules = load_model_rules()
    policy = model_rules.get("design_fallback_policy", {})
    common = policy.get("common_defaults", {}) if isinstance(policy, dict) else {}
    family_defaults = (
        policy.get("family_defaults", {}).get(family_id, {})
        if isinstance(policy.get("family_defaults", {}), dict)
        else {}
    )
    work = dict(params)
    ledger: list[dict[str, Any]] = []
    lineage: dict[str, dict[str, Any]] = {}

    # A complete release package is already the higher authority.  Do not
    # contaminate a machine-evidence review by inserting preliminary defaults;
    # any genuinely missing required field must remain visible to the formal
    # gate.  Fallbacks are for incomplete preliminary design, not for rewriting
    # an approved same-equipment evidence package.
    formal_release_package_supplied = all(
        present(work, field)
        for field in (
            "evidence_manifest_path", "evidence_manifest_sha256",
            "audit_approval_path", "audit_approval_sha256",
        )
    ) and str(work.get("approval_status", "")).strip().casefold() == "approved"
    if formal_release_package_supplied:
        return work, ledger, lineage

    def add(
        field: str,
        value: Any,
        tier: str,
        reason: str,
        warning: str,
        basis: list[str] | None = None,
        equation_chain: str | None = None,
    ) -> None:
        if value in (None, "") or present(work, field):
            return
        work[field] = value
        state = "RECOMMENDED" if tier != "EXPLICIT_FINAL_FALLBACK_DEFAULT" else "DEFAULTED"
        record = {
            "field_id": field,
            "value": value,
            "tier": tier,
            "state": state,
            "source_kind": (
                "registered_final_fallback_default"
                if state == "DEFAULTED"
                else "registered_conditional_recommendation"
            ),
            "reason": reason,
            "basis": list(basis or []),
            "evidence_class": "J",
            "result_status": "PROVISIONAL",
            "promotion_cap": "TYPE_SCREENING",
            "auto_applied": True,
            "overwrite_allowed": False,
            "warning": warning,
            "equation_chain": equation_chain,
        }
        ledger.append(record)
        lineage[field] = {
            "calculation_id": f"fallback:{field}",
            "target_field": field,
            "release_class": "B",
            "evidence_class": "J",
            "result_status": "PROVISIONAL",
            "promotion_cap": "TYPE_SCREENING",
            "fallback_tier": tier,
        }

    operating_pressure_context = any(
        present(work, field)
        for field in ("inlet_pressure_mpa", "outlet_pressure_mpa", "operating_pressure_mpa")
    )
    direct_design_pressure_context = present(work, "design_pressure_mpa")
    pressure_context = operating_pressure_context or direct_design_pressure_context
    if operating_pressure_context and not present(work, "pressure_basis"):
        is_aspen = present(work, "aspen_block_type")
        add(
            "pressure_basis",
            common.get("aspen_pressure_basis" if is_aspen else "manual_pressure_basis", "absolute" if is_aspen else "gauge"),
            "EXPLICIT_FINAL_FALLBACK_DEFAULT",
            "Pressure basis was absent; use the registered source-sensitive fallback to keep preliminary calculations running.",
            "压力基准是最终保底假设；若实际基准不同，所有压比、设计压力和机械初算必须重放。",
            ["aspen_block_present" if is_aspen else "manual_or_unidentified_source"],
        )
    if direct_design_pressure_context and not present(work, "design_pressure_basis"):
        add(
            "design_pressure_basis", common.get("manual_pressure_basis", "gauge"),
            "EXPLICIT_FINAL_FALLBACK_DEFAULT",
            "A direct design-pressure value was supplied without its basis.",
            "直给设计压力缺少基准时暂按表压保底；若原值为绝压，厚度与压力等级必须重算。",
            ["direct_design_pressure_without_basis"],
        )
    needs_atmosphere = (
        (
            any(present(work, field) for field in ("inlet_pressure_mpa", "outlet_pressure_mpa"))
            and work.get("pressure_basis") == "gauge"
        )
        or (
            present(work, "operating_pressure_mpa")
            and work.get("pressure_basis") == "absolute"
        )
    ) or (
        direct_design_pressure_context and work.get("design_pressure_basis") == "absolute"
    )
    if needs_atmosphere and not present(work, "atmospheric_pressure_mpa"):
        add(
            "atmospheric_pressure_mpa", common.get("atmospheric_pressure_mpa", 0.101325),
            "EXPLICIT_FINAL_FALLBACK_DEFAULT",
            "Local atmospheric pressure was absent.",
            "采用标准大气压作最终保底；高海拔或现场气压不同会改变绝压/表压换算。",
            ["standard_atmosphere_fallback"],
        )
    if present(work, "operating_pressure_mpa") and not present(work, "design_pressure_mpa"):
        add(
            "design_pressure_factor", common.get("design_pressure_factor", 1.1),
            "EXPLICIT_FINAL_FALLBACK_DEFAULT",
            "A registered design-pressure multiplier is required by the preliminary pressure formula.",
            "1.1 仅为最终保底系数，不含静液柱、瞬态、真空、泄放和规范最小附加量。",
            ["operating_pressure_available", "design_pressure_not_supplied"],
        )

    if not present(work, "design_temperature_c"):
        temperatures = [
            float(work[field])
            for field in ("temperature_c", "inlet_temperature_c")
            if present(work, field) and isinstance(work[field], (int, float))
        ]
        if temperatures:
            base_temperature = max(temperatures)
            margin = float(common.get("design_temperature_margin_c", 20.0))
            value = base_temperature + margin
            add(
                "design_temperature_c", value,
                "BUILT_IN_RECOMMENDED_FORMULA",
                "Preliminary maximum process temperature plus registered margin.",
                "设计温度初值未覆盖开停车、失控、再生、伴热和最低设计金属温度。",
                [f"maximum_available_process_temperature_c:{base_temperature}", f"margin_c:{margin}"],
                f"design_temperature_c = Tmax + dT = {base_temperature:g} + {margin:g} = {value:g} degC",
            )
        else:
            add(
                "design_temperature_c", common.get("design_temperature_c_when_no_process_temperature", 60.0),
                "EXPLICIT_FINAL_FALLBACK_DEFAULT",
                "No usable process temperature was available.",
                "60 °C 是最终保底值；没有温度基础时只允许生成预设计候选。",
                ["no_process_temperature_available"],
            )

    if not present(work, "material"):
        value, tier, warning, basis = _material_fallback(policy, work)
        add("material", value, tier, "Context-conditioned material route or final economic baseline.", warning, basis)

    pressure_vessel_families = {
        "family_tower", "family_reactor_vessel_separator", "family_storage_vessel",
    }
    exchanger_families = {"family_fixed_tubesheet_exchanger", "family_other_heat_exchanger"}
    if family_id in exchanger_families and present(work, "material"):
        add(
            "tube_material_grade", work["material"], "EXPLICIT_FINAL_FALLBACK_DEFAULT",
            "Use the current preliminary material route for the tube side until corrosion and fabrication split it.",
            "管程材料暂沿用设备材料预设计路线；正式牌号须按冷热侧介质分别做腐蚀、温度和制造复核。",
            ["material_route_inherited_for_preliminary_tube_side"],
        )
        add(
            "shell_material_grade", work["material"], "EXPLICIT_FINAL_FALLBACK_DEFAULT",
            "Use the current preliminary material route for the shell side until corrosion and fabrication split it.",
            "壳程材料暂沿用设备材料预设计路线；正式牌号须按冷热侧介质分别做腐蚀、温度和制造复核。",
            ["material_route_inherited_for_preliminary_shell_side"],
        )
    if family_id in pressure_vessel_families:
        add(
            "head_type", common.get("head_type", "2:1_ellipsoidal"),
            "KNOWLEDGE_GRAPH_CONDITIONAL_RECOMMENDATION",
            "Use the implemented general pressure-vessel head branch for preliminary calculation.",
            "2:1 椭圆封头仅是预设计分支，不能替代设备结构确认。",
            ["implemented_head_formula_branch"],
        )
        add(
            "weld_efficiency", common.get("weld_efficiency", 0.85),
            "EXPLICIT_FINAL_FALLBACK_DEFAULT",
            "Weld joint efficiency was absent but preliminary shell/head thickness should continue.",
            "焊接接头系数必须由制造、无损检测比例和规范重新确认。",
            ["preliminary_internal_pressure_thickness"],
        )
        add(
            "allowable_stress_mpa", common.get("allowable_stress_mpa", 120.0),
            "EXPLICIT_FINAL_FALLBACK_DEFAULT",
            "Allowable stress was absent but preliminary shell/head thickness should continue.",
            "许用应力 120 MPa 是材料未闭合时的最终保底值；正式值必须按材料牌号和设计温度查表。",
            ["generic_carbon_steel_screening_basis"],
        )
        if present(work, "operating_pressure_mpa") and present(work, "pressure_basis"):
            operating_gauge = float(work["operating_pressure_mpa"])
            if work["pressure_basis"] == "absolute" and present(work, "atmospheric_pressure_mpa"):
                operating_gauge -= float(work["atmospheric_pressure_mpa"])
            if operating_gauge <= 0 and not present(work, "design_pressure_mpa"):
                add(
                    "design_pressure_mpa", 0.1, "EXPLICIT_FINAL_FALLBACK_DEFAULT",
                    "Keep an internal-pressure screening value while the separate vacuum/external-pressure branch remains open.",
                    "0.1 MPa(g) 仅为不中停的内压预设计保底；外压稳定性、全真空工况和加强圈设计仍是正式阻断项。",
                    [f"operating_gauge_pressure_mpa:{operating_gauge:g}", "external_pressure_branch_open"],
                )
                add(
                    "design_pressure_basis", "gauge", "EXPLICIT_FINAL_FALLBACK_DEFAULT",
                    "Declare the basis of the preliminary internal-pressure fallback.",
                    "该基准只对应0.1 MPa(g)内压保底，不表示外压/真空校核已经通过。",
                    ["paired_with_internal_pressure_screening_fallback"],
                )

        design_temperature = float(work["design_temperature_c"]) if present(work, "design_temperature_c") else 25.0
        needs_insulation = design_temperature > 60.0 or design_temperature < 5.0
        insulation = (
            "设置保温/保冷层（厚度待热工、防烫/防凝露计算）"
            if needs_insulation
            else "不设保温（预设计默认；防烫、防凝露及最低环境温度待复核）"
        )
        add(
            "insulation_spec", insulation, "KNOWLEDGE_GRAPH_CONDITIONAL_RECOMMENDATION",
            "Select a visible preliminary insulation route from the available design temperature.",
            "保温结论仅用于一览表和初步布置；厚度、材料、防火及经济厚度须按项目环境重新计算。",
            [f"design_temperature_c:{design_temperature:g}", "registered_temperature_condition"],
        )
        protective = (
            "金属外护层（预设计；材质与厚度待环境等级确认）"
            if needs_insulation
            else "涂层防腐保护（预设计；涂层体系待环境等级确认）"
        )
        add(
            "protective_layer", protective, "KNOWLEDGE_GRAPH_CONDITIONAL_RECOMMENDATION",
            "Select a visible preliminary protective-layer route consistent with the insulation branch.",
            "保护层仅为预设计路线，不能替代腐蚀环境等级、保温结构和涂装规范确认。",
            ["paired_with_registered_insulation_route"],
        )

    conditional_defaults = dict(family_defaults) if isinstance(family_defaults, dict) else {}

    # Aspen solid-processing blocks identify the process task but do not prove
    # a mechanical size, cycle, or loading basis.  Keep the terminal type
    # available, while suppressing generic family numbers that would look like
    # a calculated crystallizer/filter/dryer specification.
    block_type = str(work.get("aspen_block_type") or "").strip().upper()
    if block_type == "CRYSTALLIZER":
        for field in (
            "fill_fraction", "retention_time_min", "volume_m3", "volume_basis",
            "diameter_mm", "inner_diameter_mm", "height_mm", "straight_shell_length_mm",
        ):
            conditional_defaults.pop(field, None)
    elif block_type == "RPLUG":
        # Aspen RPLUG identifies an ideal plug-flow process model.  Its
        # DIAMETER belongs to one active process tube and is now retained by
        # the Aspen adapter under a dedicated field.  Never reuse generic
        # vessel geometry defaults here: doing so would mislabel one tube as
        # the reactor shell and trigger false shell/head thickness equations.
        for field in (
            "volume_m3",
            "volume_basis",
            "fill_fraction",
            "retention_time_min",
            "diameter_mm",
            "inner_diameter_mm",
            "height_mm",
            "straight_shell_length_mm",
        ):
            conditional_defaults.pop(field, None)
        # A bare Aspen RPLUG `diameter_mm` input is semantically one active
        # tube.  The generic matcher has no dedicated Aspen-source lineage, so
        # it must not retain that value as a whole-vessel diameter.
        work.pop("diameter_mm", None)
    elif block_type in {"FILTER", "DRYER"}:
        for field in ("capacity", "cycle_time_h", "allowable_pressure_drop_kpa"):
            conditional_defaults.pop(field, None)

    # Family defaults are the terminal safety net, not competitors to a
    # closeable same-case equation.  Remove any fallback target whose exact
    # deterministic inputs are already available so the calculation layer can
    # establish the canonical value and propagate its lineage downstream.
    if present(work, "operating_pressure_mpa"):
        conditional_defaults.pop("design_pressure_mpa", None)
        conditional_defaults.pop("design_pressure_basis", None)
    if family_id == "family_pump" and all(
        present(work, field)
        for field in CALCULATION_REQUIREMENTS["pump_head_from_pressure"]
    ):
        conditional_defaults.pop("head_m", None)
    if family_id == "family_valve" and all(
        present(work, field)
        for field in CALCULATION_REQUIREMENTS["valve_pressure_drop_from_streams"]
    ):
        conditional_defaults.pop("pressure_drop_kpa", None)
    if family_id == "family_process_piping" and all(
        present(work, field) or conditional_defaults.get(field) not in (None, "")
        for field in ("flow_m3_h", "target_velocity_m_s", "selected_wall_thickness_mm")
    ):
        # DN50/60.3 mm is now only the truly non-closeable last tier. When the
        # hydraulic basis can close, the promoted GB/T table owns DN and D.
        conditional_defaults.pop("selected_dn", None)
        conditional_defaults.pop("selected_outer_diameter_mm", None)
    if family_id in {"family_fixed_tubesheet_exchanger", "family_other_heat_exchanger"}:
        default_u = float(conditional_defaults.get("overall_u_w_m2k", 300.0))
        u_value, u_basis = _exchanger_u_fallback(work, default_u)
        conditional_defaults["overall_u_w_m2k"] = u_value
        exchanger_basis = {"overall_u_w_m2k": u_basis}
        sensible_inputs = ("mass_flow_kg_h", "inlet_temperature_c", "outlet_temperature_c")
        if all(present(work, field) for field in sensible_inputs):
            phase = canonical_phase(work.get("phase"))
            cp_value = {
                "liquid": 2.0,
                "vapor": 1.2,
                "mixed": 2.5,
                "solid": 1.0,
            }.get(phase, 2.0)
            conditional_defaults.setdefault("specific_heat_kj_kgk", cp_value)
            # The stream energy balance is a higher deterministic tier than a
            # fixed 100 kW terminal default.  Preserve a supplied nonzero Aspen
            # duty for cross-checking, but do not let the fixed default mask a
            # closeable m*Cp*dT chain.
            conditional_defaults.pop("heat_duty_kw", None)
    else:
        exchanger_basis = {}
    if family_id == "family_tower":
        phase = canonical_phase(work.get("phase"))
        if not present(work, "inner_diameter_mm") and not present(work, "diameter_mm"):
            conditional_defaults["tower_design_velocity_m_s"] = {
                "vapor": 1.5, "mixed": 1.0, "liquid": 0.5,
            }.get(phase, float(conditional_defaults.get("tower_design_velocity_m_s", 1.0)))
            if not present(work, "flow_m3_h"):
                conditional_defaults["inner_diameter_mm"] = float(
                    conditional_defaults.get("minimum_screening_inner_diameter_mm", 600.0)
                )
        else:
            conditional_defaults.pop("tower_design_velocity_m_s", None)
        conditional_defaults.pop("minimum_screening_inner_diameter_mm", None)
        if present(work, "height_mm"):
            conditional_defaults.pop("tower_top_bottom_allowance_mm", None)
        elif (
            (present(work, "stage_count") or conditional_defaults.get("stage_count") not in (None, ""))
            and (
                present(work, "inner_diameter_mm")
                or present(work, "diameter_mm")
                or conditional_defaults.get("inner_diameter_mm") not in (None, "")
                or (
                    (
                        present(work, "flow_m3_h")
                        or conditional_defaults.get("flow_m3_h")
                        not in (None, "")
                    )
                    and (
                        present(work, "tower_design_velocity_m_s")
                        or conditional_defaults.get(
                            "tower_design_velocity_m_s"
                        )
                        not in (None, "")
                    )
                )
            )
            and conditional_defaults.get("tower_top_bottom_allowance_mm") not in (None, "")
        ):
            # Height is a deterministic downstream result once stage count,
            # diameter-derived tray spacing, and the registered allowance are
            # available.  Keep the family height only as the truly final
            # fallback; otherwise it would mask tower_preliminary_height.
            conditional_defaults.pop("height_mm", None)
        gauge_pressure = None
        if present(work, "operating_pressure_mpa"):
            gauge_pressure = float(work["operating_pressure_mpa"])
            if work.get("pressure_basis") == "absolute" and present(work, "atmospheric_pressure_mpa"):
                gauge_pressure -= float(work["atmospheric_pressure_mpa"])
        if gauge_pressure is not None and gauge_pressure < 0:
            conditional_defaults["tower_weir_height_mm"] = 25.0

    for field, value in conditional_defaults.items():
        if field in {"overall_u_w_m2k", "lmtd_k", "lmtd_correction_factor", "tower_design_velocity_m_s"}:
            tier = "BUILT_IN_RECOMMENDED_FORMULA"
        else:
            tier = "EXPLICIT_FINAL_FALLBACK_DEFAULT"
        extra_basis = exchanger_basis.get(field, [])
        add(
            field, value, tier,
            "Registered family fallback selected from the deterministic equipment family and available context.",
            "该值只用于保持预设计与候选生成不中停；替换为同工况数据后必须自动重算。",
            [f"family:{family_id}", *extra_basis],
        )

    if family_id in {"family_process_piping", "family_static_mixer"} and not present(params, "target_velocity_m_s"):
        phase = canonical_phase(work.get("phase"))
        velocity = {"vapor": 15.0, "mixed": 3.0, "liquid": 1.5}.get(phase, 1.5)
        # Replace the generic family fallback with a phase-sensitive value when
        # the field was inserted during this call.
        for item in ledger:
            if item["field_id"] == "target_velocity_m_s":
                work["target_velocity_m_s"] = velocity
                item["value"] = velocity
                item["basis"].append(f"phase:{phase or 'unknown'}")
                break

    return work, ledger, lineage


def build_model_estimate_fallbacks(
    normalized: dict[str, Any],
    estimate_lineage: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Convert already program-validated LLM estimates into visible J lineage.

    The public matcher input cannot create this metadata.  It is supplied only
    by the staged hybrid adapter after missing-only and physical-sanity checks.
    Values still have to survive this matcher's normal validation and every
    calculation/candidate rule.  The records permanently cap the result at
    preliminary type screening.
    """

    if not isinstance(estimate_lineage, dict):
        return [], {}
    forbidden = {
        "equipment_tag", "equipment_family", "equipment_type", "aspen_block_type",
        "candidate_model", "vendor_model", "final_model", "model_status",
        "verification_result", "approval_status", "material",
        # These are deterministic standard/type-selector outputs.  A model may
        # help classify registered conditions, but it may not inject a free
        # component/type label into the matcher.
        "mixing_metric", "wall_series", "fitting_type", "connection_type", "pressure_class",
        "flange_face", "gasket_material", "valve_function",
    }
    ledger: list[dict[str, Any]] = []
    lineage: dict[str, dict[str, Any]] = {}
    for field in sorted(estimate_lineage):
        item = estimate_lineage[field]
        if field in forbidden or field.endswith(("_path", "_sha256", "_ref")):
            raise ValueError(f"model estimate target is forbidden: {field}")
        if field not in normalized or not isinstance(item, dict):
            raise ValueError(f"model estimate lineage/value mismatch: {field}")
        expected = item.get("resolved_value")
        actual = normalized[field]
        if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
            tolerance = max(1e-9, abs(float(expected)) * 1e-9)
            if abs(float(expected) - float(actual)) > tolerance:
                raise ValueError(f"model estimate value changed before replay: {field}")
        elif expected != actual:
            raise ValueError(f"model estimate value changed before replay: {field}")
        record = {
            "field_id": field,
            "value": actual,
            "tier": "LLM_LAST_RESORT_ENGINEERING_ESTIMATE",
            "state": "ESTIMATED",
            "source_kind": "llm_last_resort_engineering_estimate",
            "reason": item.get("detail") or "Structured model estimate used to close preliminary selection.",
            "basis": [
                f"inference_basis:{item.get('inference_basis')}",
                *[f"assumption:{value}" for value in item.get("assumptions", [])],
            ],
            "inference_basis": item.get("inference_basis"),
            "assumptions": list(item.get("assumptions", [])),
            "context_refs": list(item.get("citations", [])),
            "evidence_class": "J",
            "result_status": "PROVISIONAL",
            "promotion_cap": "TYPE_SCREENING",
            "auto_applied": True,
            "overwrite_allowed": False,
            "warning": item.get("warning") or (
                "LLM 末级工程估算，仅用于初步选型；替换为同工况/Aspen/标准/厂家证据后必须重算。"
            ),
            "equation_chain": None,
            "assist_id": item.get("assist_id"),
            "target_unit": item.get("target_unit"),
            "lower_bound": item.get("lower_bound"),
            "upper_bound": item.get("upper_bound"),
            "registered_allowed_values": list(item.get("registered_allowed_values", []))
            if isinstance(item.get("registered_allowed_values"), list) else [],
            "registry_id": item.get("registry_id"),
            "confidence": item.get("confidence"),
            "sensitivity_note": item.get("sensitivity_note"),
        }
        ledger.append(record)
        lineage[field] = {
            "calculation_id": f"llm_estimate:{field}",
            "target_field": field,
            "release_class": "B",
            "evidence_class": "J",
            "result_status": "PROVISIONAL",
            "promotion_cap": "TYPE_SCREENING",
            "fallback_tier": "LLM_LAST_RESORT_ENGINEERING_ESTIMATE",
        }
    return ledger, lineage


def build_missing_field_recommendations(
    family_id: str,
    parameter_package: dict[str, Any],
    fallback_ledger: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return an actionable recommendation for every still-empty package row."""
    items: list[dict[str, Any]] = [
        {
            **item,
            "status": (
                "SUPERSEDED_BY_DETERMINISTIC_CALCULATION"
                if item.get("state") == "SUPERSEDED_BY_DETERMINISTIC_CALCULATION"
                else "APPLIED_PRELIMINARY_FALLBACK"
            ),
            "next_action": (
                "retain_program_calculation_and_disregard_model_target"
                if item.get("state") == "SUPERSEDED_BY_DETERMINISTIC_CALCULATION"
                else "replace_with_same_case_value_then_replay"
            ),
        }
        for item in fallback_ledger
    ]
    seen = {str(item.get("field_id")) for item in items}
    for group in parameter_package.get("groups", []):
        for row in group.get("rows", []):
            field = str(row.get("field_id") or "")
            if not field or field in seen or row.get("state") not in {"MISSING", "EXTERNAL_REQUIRED"}:
                continue
            required_for = list(row.get("required_for", []))
            if row.get("state") == "EXTERNAL_REQUIRED" or group.get("group_id") == "evidence":
                action = "OBTAIN_SAME_EQUIPMENT_SOFTWARE_VENDOR_OR_APPROVAL_EVIDENCE"
                reason = "Preliminary calculation continues, but this evidence is indispensable for formal promotion."
            elif field in FALLBACK_PROCESS_FIELDS:
                action = "READ_FROM_ASPEN_OR_REQUEST_CURRENT_PROCESS_VALUE"
                reason = "Prefer the current case process/property result; no unregistered chemistry value is invented."
            elif field in FALLBACK_CONSTRUCTION_FIELDS or field.endswith("_material"):
                action = "SELECT_FROM_CONTEXT_CONDITIONED_ENGINEERING_CANDIDATES"
                reason = "Retain the most general construction route until service compatibility is confirmed."
            else:
                action = "KEEP_GENERAL_CANDIDATE_AND_REQUEST_MINIMUM_CLOSURE_VALUE"
                reason = "No safe registered numeric fallback exists for this field; unrelated calculations and the general equipment candidate remain available."
            items.append({
                "field_id": field,
                "label": row.get("label"),
                "status": "RECOMMENDATION_OPEN",
                "recommended_action": action,
                "reason": reason,
                "required_for": required_for,
                "priority": "HIGH" if any(value in {"sizing", "candidate_matching"} or str(value).startswith("calculation:") for value in required_for) else "NORMAL",
                "evidence_class": "U",
                "auto_applied": False,
                "does_not_block_unrelated_results": True,
            })
            seen.add(field)
    policy = load_model_rules().get("design_fallback_policy", {})
    return {
        "schema": "equipment-missing-input-recommendations-v1",
        "status": "GENERATED",
        "family_id": family_id,
        "hierarchy": list(policy.get("hierarchy", [])),
        "formal_promotion_allowed": False,
        "applied_fallback_count": len(fallback_ledger),
        "open_recommendation_count": sum(item.get("status") == "RECOMMENDATION_OPEN" for item in items),
        "items": items,
        "deterministic": True,
        "llm_used": False,
    }


def validate_parameters(params: dict[str, Any]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    if present(params, "pressure_basis") and params["pressure_basis"] not in PRESSURE_BASIS_WORDS:
        errors.append({"field": "pressure_basis", "code": "INVALID_PRESSURE_BASIS", "value": params["pressure_basis"], "allowed": sorted(PRESSURE_BASIS_WORDS)})
    if present(params, "design_pressure_basis") and params["design_pressure_basis"] not in PRESSURE_BASIS_WORDS:
        errors.append({"field": "design_pressure_basis", "code": "INVALID_DESIGN_PRESSURE_BASIS", "value": params["design_pressure_basis"], "allowed": sorted(PRESSURE_BASIS_WORDS)})
    if present(params, "membrane_geometry_type") and params["membrane_geometry_type"] not in MEMBRANE_GEOMETRY_TYPE_WORDS:
        errors.append({"field": "membrane_geometry_type", "code": "INVALID_MEMBRANE_GEOMETRY_TYPE", "value": params["membrane_geometry_type"], "allowed": sorted(MEMBRANE_GEOMETRY_TYPE_WORDS)})
    if present(params, "volume_basis") and params["volume_basis"] not in VOLUME_BASIS_WORDS:
        errors.append({"field": "volume_basis", "code": "INVALID_VOLUME_BASIS", "value": params["volume_basis"], "allowed": sorted(VOLUME_BASIS_WORDS)})
    if present(params, "phase") and canonical_phase(params["phase"]) is None:
        errors.append({
            "field": "phase",
            "code": "INVALID_PHASE",
            "value": params["phase"],
            "allowed_canonical": ["liquid", "vapor", "mixed", "solid"],
        })
    # A missing local atmospheric pressure is incomplete physical basis, not a
    # malformed value.  Keep partial input usable and let the calculation/progress
    # layer request the smallest missing fact.
    invalid_numeric: set[str] = set()
    for field in NUMERIC_FIELDS:
        if not present(params, field):
            continue
        value = params[field]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            errors.append({"field": field, "code": "NON_NUMERIC_VALUE", "value": value})
            invalid_numeric.add(field)
        elif not math.isfinite(float(value)):
            errors.append({"field": field, "code": "NON_FINITE_VALUE", "value": value})
            invalid_numeric.add(field)
    for field, value in params.items():
        if field.endswith("_sha256") and present(params, field):
            if not re.fullmatch(r"[0-9A-Fa-f]{64}", str(value).strip()):
                errors.append({"field": field, "code": "INVALID_SHA256", "value": value})
    for hash_field, path_field in EVIDENCE_PAIRS.items():
        has_hash = present(params, hash_field)
        has_path = present(params, path_field)
        if has_hash and not has_path:
            errors.append({"field": path_field, "code": "MISSING_EVIDENCE_PATH", "hash_field": hash_field})
            continue
        if has_path and not has_hash:
            errors.append({"field": hash_field, "code": "MISSING_EVIDENCE_SHA256", "path_field": path_field})
            continue
        if not has_hash:
            continue
        raw_path = Path(str(params[path_field])).expanduser()
        candidates = [raw_path] if raw_path.is_absolute() else [PACKAGE_ROOT / raw_path, Path.cwd() / raw_path]
        evidence_path = next((candidate.resolve() for candidate in candidates if candidate.is_file()), None)
        if evidence_path is None:
            errors.append({"field": path_field, "code": "EVIDENCE_FILE_NOT_FOUND", "value": params[path_field]})
            continue
        digest = hashlib.sha256(evidence_path.read_bytes()).hexdigest().upper()
        if digest != str(params[hash_field]).strip().upper():
            errors.append({"field": hash_field, "code": "EVIDENCE_HASH_MISMATCH", "expected": str(params[hash_field]).strip().upper(), "actual": digest, "path": str(evidence_path)})
    strictly_positive = {
        "flow_m3_h", "mass_flow_kg_h", "density_kg_m3",
        "atmospheric_pressure_mpa", "diameter_mm", "height_mm",
        "inner_diameter_mm", "straight_shell_length_mm", "volume_m3", "required_volume_m3", "straight_shell_geometric_volume_m3",
        "target_velocity_m_s", "heat_transfer_area_m2", "tube_outer_diameter_mm", "tube_length_mm",
        "tube_or_plate_count", "shell_pass_count", "tower_internal_height_m",
        "overall_u_w_m2k", "lmtd_k", "lmtd_correction_factor", "allowable_stress_mpa", "selected_dn",
        "cylinder_calculated_thickness_mm", "head_calculated_thickness_mm",
        "selected_outer_diameter_mm", "selected_wall_thickness_mm", "element_count",
        "channel_count", "channel_inner_diameter_mm", "element_length_m", "cycle_time_h",
        "stage_count", "retention_time_min", "gas_molecular_weight", "compressibility_factor",
        "rotational_speed_rpm", "membrane_area_m2", "flux", "selectivity", "capacity", "cv",
        "specific_heat_kj_kgk", "maximum_pressure_drop_factor",
        "pressure_drop_power_component_kw", "pressure_component_shaft_power_screening_kw",
        "pressure_drop_head_component_m",
    }
    nonnegative = {
        "head_m", "pressure_drop_kpa", "allowable_pressure_drop_kpa", "maximum_pressure_drop_kpa", "npshr_m",
        "required_npsh_margin_m", "required_surge_margin_percent",
    }
    for field in strictly_positive:
        if present(params, field) and field not in invalid_numeric and float(params[field]) <= 0:
            errors.append({"field": field, "code": "MUST_BE_POSITIVE", "value": params[field]})
    for field in nonnegative:
        if present(params, field) and field not in invalid_numeric and float(params[field]) < 0:
            errors.append({"field": field, "code": "MUST_BE_NONNEGATIVE", "value": params[field]})
    if present(params, "maximum_pressure_drop_factor") and "maximum_pressure_drop_factor" not in invalid_numeric and float(params["maximum_pressure_drop_factor"]) < 1.0:
        errors.append({"field": "maximum_pressure_drop_factor", "code": "MUST_BE_AT_LEAST_ONE", "value": params["maximum_pressure_drop_factor"]})
    if present(params, "efficiency_percent") and "efficiency_percent" not in invalid_numeric and not 0 < float(params["efficiency_percent"]) <= 100:
        errors.append({"field": "efficiency_percent", "code": "OUT_OF_RANGE_0_100", "value": params["efficiency_percent"]})
    if present(params, "recovery_percent") and "recovery_percent" not in invalid_numeric and not 0 <= float(params["recovery_percent"]) <= 100:
        errors.append({"field": "recovery_percent", "code": "OUT_OF_RANGE_0_100", "value": params["recovery_percent"]})
    if present(params, "fill_fraction") and "fill_fraction" not in invalid_numeric and not 0 < float(params["fill_fraction"]) <= 1:
        errors.append({"field": "fill_fraction", "code": "OUT_OF_RANGE_0_1", "value": params["fill_fraction"]})
    if present(params, "weld_efficiency") and "weld_efficiency" not in invalid_numeric and not 0 < float(params["weld_efficiency"]) <= 1:
        errors.append({"field": "weld_efficiency", "code": "OUT_OF_RANGE_0_1", "value": params["weld_efficiency"]})
    if present(params, "lmtd_correction_factor") and "lmtd_correction_factor" not in invalid_numeric and not 0 < float(params["lmtd_correction_factor"]) <= 1:
        errors.append({"field": "lmtd_correction_factor", "code": "OUT_OF_RANGE_0_1", "value": params["lmtd_correction_factor"]})
    if (
        present(params, "design_pressure_mpa")
        and "design_pressure_mpa" not in invalid_numeric
        and params.get("design_pressure_basis") == "absolute"
        and float(params["design_pressure_mpa"]) <= 0
    ):
        errors.append({
            "field": "design_pressure_mpa",
            "code": "ABSOLUTE_DESIGN_PRESSURE_MUST_BE_POSITIVE",
            "value": params["design_pressure_mpa"],
        })
    if present(params, "design_pressure_factor") and "design_pressure_factor" not in invalid_numeric and float(params["design_pressure_factor"]) < 1:
        errors.append({"field": "design_pressure_factor", "code": "MUST_BE_AT_LEAST_1", "value": params["design_pressure_factor"]})
    if present(params, "selected_outer_diameter_mm") and present(params, "selected_wall_thickness_mm") and not {"selected_outer_diameter_mm", "selected_wall_thickness_mm"} & invalid_numeric:
        if 2 * float(params["selected_wall_thickness_mm"]) >= float(params["selected_outer_diameter_mm"]):
            errors.append({"field": "selected_wall_thickness_mm", "code": "NO_POSITIVE_INNER_DIAMETER", "value": params["selected_wall_thickness_mm"]})
    for field in ("stage_count", "element_count", "channel_count"):
        if present(params, field) and field not in invalid_numeric and not float(params[field]).is_integer():
            errors.append({"field": field, "code": "MUST_BE_INTEGER", "value": params[field]})
    basis = params.get("pressure_basis")
    for field in ("inlet_pressure_mpa", "outlet_pressure_mpa", "operating_pressure_mpa"):
        if not present(params, field) or field in invalid_numeric:
            continue
        pressure = float(params[field])
        if basis == "absolute" and pressure <= 0:
            errors.append({"field": field, "code": "ABSOLUTE_PRESSURE_MUST_BE_POSITIVE", "value": pressure})
        if basis == "gauge" and present(params, "atmospheric_pressure_mpa") and "atmospheric_pressure_mpa" not in invalid_numeric:
            absolute_pressure = pressure + float(params["atmospheric_pressure_mpa"])
            if absolute_pressure <= 0:
                errors.append({"field": field, "code": "GAUGE_PRESSURE_GIVES_NONPOSITIVE_ABSOLUTE_PRESSURE", "value": pressure, "atmospheric_pressure_mpa": params["atmospheric_pressure_mpa"]})
    return errors


def prepare_family_effective_inputs(
    family_id: str,
    params: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Quarantine unregistered component labels before candidate matching.

    The flange/gasket terminal selector owns the actual paired component type.
    Manual free text may remain visible in the original input, but it cannot
    enter the deterministic parameter package, designation, or completeness
    state as if it were a registered compatibility result.
    """

    effective = dict(params)
    diagnostics: list[dict[str, Any]] = []
    if family_id != "family_flange_gasket":
        return effective, diagnostics

    if present(effective, "gasket_material"):
        effective.pop("gasket_material", None)
        diagnostics.append({
            "field": "gasket_material",
            "code": "UNTRUSTED_COMPONENT_PREFERENCE_QUARANTINED",
            "status": "IGNORED_UNTRUSTED_COMPONENT_PREFERENCE",
            "scope": "TARGET_FIELD_ONLY",
            "downstream_policy": (
                "Preserve the raw preference for audit only; the registered connection-component "
                "selector determines the gasket terminal type and compatibility result."
            ),
        })

    if present(effective, "flange_face"):
        face = str(effective["flange_face"]).strip().upper().replace(" ", "")
        allowed_faces = {"RF", "FF", "FM/M", "T/G", "RJ"}
        if face in allowed_faces:
            effective["flange_face"] = face
        else:
            effective.pop("flange_face", None)
            diagnostics.append({
                "field": "flange_face",
                "code": "UNREGISTERED_FLANGE_FACE_QUARANTINED",
                "status": "IGNORED_UNREGISTERED_MANUAL_MECHANICAL_VALUE",
                "allowed": sorted(allowed_faces),
                "scope": "TARGET_FIELD_ONLY",
                "downstream_policy": "Keep the general pair candidate and request a registered facing.",
            })

    if present(effective, "pressure_class"):
        pressure_text = str(effective["pressure_class"]).strip().upper().replace(" ", "")
        pn_match = re.fullmatch(r"PN(\d+(?:\.\d+)?)", pressure_text)
        class_match = re.fullmatch(r"(?:CLASS|CL)(\d+(?:\.\d+)?)", pressure_text)
        lb_match = re.fullmatch(r"(\d+(?:\.\d+)?)LB", pressure_text)
        rating = pn_match or class_match or lb_match
        rating_value = float(rating.group(1)) if rating else None
        if rating_value is not None and rating_value > 0:
            if pn_match:
                effective["pressure_class"] = f"PN{rating_value:g}"
            else:
                effective["pressure_class"] = f"Class{rating_value:g}"
        else:
            effective.pop("pressure_class", None)
            diagnostics.append({
                "field": "pressure_class",
                "code": "UNREGISTERED_PRESSURE_CLASS_QUARANTINED",
                "status": "IGNORED_UNREGISTERED_MANUAL_MECHANICAL_VALUE",
                "scope": "TARGET_FIELD_ONLY",
                "downstream_policy": "Keep the general pair candidate and request PN or Class rating.",
            })
    return effective, diagnostics


def verified(params: dict[str, Any], verification_fields: list[str]) -> bool:
    if not all(present(params, field) for field in verification_fields):
        return False
    if any(field.endswith("_sha256") and not present(params, EVIDENCE_PAIRS[field]) for field in verification_fields if field in EVIDENCE_PAIRS):
        return False
    return token(params.get("verification_result")) in {token(word) for word in PASS_WORDS}


def resolve_evidence_path(raw_path: Any, *, relative_to: Path | None = None) -> Path | None:
    path = Path(str(raw_path)).expanduser()
    candidates = [path] if path.is_absolute() else [*( [relative_to / path] if relative_to else []), PACKAGE_ROOT / path, Path.cwd() / path]
    return next((candidate.resolve() for candidate in candidates if candidate.is_file()), None)


def audit_evidence_manifest(
    params: dict[str, Any], family_id: str, required_gates: list[str], verification_fields: list[str]
) -> tuple[dict[str, Any] | None, list[str]]:
    blockers: list[str] = []
    if not present(params, "evidence_manifest_path") or not present(params, "evidence_manifest_sha256"):
        return None, ["evidence_manifest_path", "evidence_manifest_sha256"]
    manifest_path = resolve_evidence_path(params["evidence_manifest_path"])
    if manifest_path is None:
        return None, ["evidence_manifest_file_not_found"]
    try:
        manifest = load_json(manifest_path)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None, ["evidence_manifest_invalid_json"]
    if not isinstance(manifest, dict) or manifest.get("schema") != "equipment-evidence-manifest-v1":
        return None, ["evidence_manifest_schema"]
    if str(manifest.get("family_id", "")) != family_id:
        blockers.append("evidence_manifest_family_mismatch")
    input_tag = str(params.get("equipment_tag", "")).strip()
    manifest_tag = str(manifest.get("equipment_tag", "")).strip()
    if not input_tag:
        blockers.append("equipment_tag_required_for_evidence_upgrade")
    elif token(input_tag) != token(manifest_tag):
        blockers.append("evidence_manifest_equipment_tag_mismatch")
    selected_model = str(params.get("vendor_model") or params.get("candidate_model") or "").strip()
    if not selected_model:
        blockers.append("selected_model_required_for_evidence_upgrade")
    elif token(selected_model) != token(manifest.get("selected_model")):
        blockers.append("evidence_manifest_selected_model_mismatch")
    closed_gates = {str(item) for item in manifest.get("closed_gates", []) if str(item).strip()}
    blockers.extend(f"open_graph_gate:{gate}" for gate in required_gates if gate not in closed_gates)
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        return manifest, blockers + ["evidence_manifest_artifacts"]
    required_hash_fields = [field for field in verification_fields if field in EVIDENCE_KIND_BY_HASH_FIELD]
    if present(params, "formal_calculation_sha256"):
        required_hash_fields.append("formal_calculation_sha256")
    bound_artifact_kinds = {EVIDENCE_KIND_BY_HASH_FIELD[field] for field in required_hash_fields}
    gate_evidence = manifest.get("gate_evidence")
    if not isinstance(gate_evidence, dict):
        blockers.append("evidence_manifest_gate_evidence")
        gate_evidence = {}
    for gate in required_gates:
        references = gate_evidence.get(gate)
        if not isinstance(references, list) or not references:
            blockers.append(f"gate_without_machine_evidence:{gate}")
            continue
        for reference in references:
            reference = str(reference)
            if reference.startswith("parameter:"):
                field = reference.split(":", 1)[1]
                if not present(params, field):
                    blockers.append(f"gate_parameter_missing:{gate}:{field}")
            elif reference not in artifacts:
                blockers.append(f"gate_artifact_missing:{gate}:{reference}")
            elif reference not in bound_artifact_kinds:
                blockers.append(f"gate_artifact_not_bound_to_input:{gate}:{reference}")
    seen_paths: dict[str, str] = {}
    seen_hashes: dict[str, str] = {}
    for hash_field in dict.fromkeys(required_hash_fields):
        kind = EVIDENCE_KIND_BY_HASH_FIELD[hash_field]
        path_field = EVIDENCE_PAIRS[hash_field]
        artifact = artifacts.get(kind)
        if not isinstance(artifact, dict):
            blockers.append(f"evidence_manifest_missing_artifact:{kind}")
            continue
        if artifact.get("evidence_kind") != kind:
            blockers.append(f"evidence_manifest_artifact_kind_mismatch:{kind}")
        if token(artifact.get("equipment_tag")) != token(input_tag):
            blockers.append(f"evidence_manifest_artifact_equipment_tag_mismatch:{kind}")
        if str(artifact.get("family_id", "")) != family_id:
            blockers.append(f"evidence_manifest_artifact_family_mismatch:{kind}")
        if token(artifact.get("selected_model")) != token(selected_model):
            blockers.append(f"evidence_manifest_artifact_selected_model_mismatch:{kind}")
        expected_path = resolve_evidence_path(params.get(path_field))
        artifact_path = resolve_evidence_path(artifact.get("path"), relative_to=manifest_path.parent)
        if expected_path is None or artifact_path is None or expected_path != artifact_path:
            blockers.append(f"evidence_manifest_artifact_path_mismatch:{kind}")
        expected_hash = str(params.get(hash_field, "")).strip().upper()
        artifact_hash = str(artifact.get("sha256", "")).strip().upper()
        if expected_hash != artifact_hash:
            blockers.append(f"evidence_manifest_artifact_hash_mismatch:{kind}")
        if artifact_path is not None:
            path_key = str(artifact_path).casefold()
            if path_key in seen_paths:
                blockers.append(f"evidence_artifact_path_reused:{seen_paths[path_key]}:{kind}")
            seen_paths[path_key] = kind
        if artifact_hash:
            if artifact_hash in seen_hashes:
                blockers.append(f"evidence_artifact_content_reused:{seen_hashes[artifact_hash]}:{kind}")
            seen_hashes[artifact_hash] = kind
    if token(manifest.get("verification_result")) not in {token(word) for word in PASS_WORDS}:
        blockers.append("evidence_manifest_verification_not_pass")
    return manifest, sorted(set(blockers))


def audit_final_approval(
    params: dict[str, Any], family_id: str, required_gates: list[str], manifest: dict[str, Any] | None
) -> list[str]:
    if not present(params, "audit_approval_path") or not present(params, "audit_approval_sha256"):
        return ["independent_audit_approval_required"]
    approval_path = resolve_evidence_path(params["audit_approval_path"])
    if approval_path is None:
        return ["independent_audit_approval_file_not_found"]
    try:
        approval = load_json(approval_path)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return ["independent_audit_approval_invalid_json"]
    blockers: list[str] = []
    if not isinstance(approval, dict) or approval.get("schema") != "equipment-audit-approval-v1":
        return ["independent_audit_approval_schema"]
    if not str(approval.get("review_id", "")).strip():
        blockers.append("independent_audit_review_id_missing")
    allowed_roles = {"human_approver", "independent_chemical_engineering_expert", "independent_kg_chemical_expert"}
    if str(approval.get("reviewer_role", "")) not in allowed_roles:
        blockers.append("independent_audit_reviewer_role")
    if token(approval.get("decision")) not in {token(word) for word in PASS_WORDS}:
        blockers.append("independent_audit_decision_not_pass")
    if str(approval.get("family_id", "")) != family_id:
        blockers.append("independent_audit_family_mismatch")
    if token(approval.get("equipment_tag")) != token(params.get("equipment_tag")):
        blockers.append("independent_audit_equipment_tag_mismatch")
    selected_model = params.get("vendor_model") or params.get("candidate_model")
    if token(approval.get("selected_model")) != token(selected_model):
        blockers.append("independent_audit_selected_model_mismatch")
    if str(approval.get("evidence_manifest_sha256", "")).strip().upper() != str(params.get("evidence_manifest_sha256", "")).strip().upper():
        blockers.append("independent_audit_manifest_hash_mismatch")
    reviewed_gates = {str(item) for item in approval.get("reviewed_gates", []) if str(item).strip()}
    blockers.extend(f"independent_audit_gate_not_reviewed:{gate}" for gate in required_gates if gate not in reviewed_gates)
    if token(approval.get("approval_status")) not in {token(word) for word in APPROVED_WORDS}:
        blockers.append("independent_audit_not_approved")
    return sorted(set(blockers))


def determine_model_status(
    rule: dict[str, Any],
    params: dict[str, Any],
    family_node: dict[str, Any],
    sizing_missing: list[str],
    calculation_hard_blockers: list[str],
    calculation_promotion_blockers: list[str],
) -> tuple[str, list[str], dict[str, Any]]:
    policy = rule["model_policy"]
    missing_verification: list[str] = []
    for field in rule.get("verification_fields", []):
        if not present(params, field):
            missing_verification.append(field)
        if field in EVIDENCE_PAIRS and not present(params, EVIDENCE_PAIRS[field]):
            missing_verification.append(EVIDENCE_PAIRS[field])
    evidence_closed = verified(params, rule.get("verification_fields", []))
    manifest, manifest_blockers = audit_evidence_manifest(
        params,
        rule["id"],
        list(family_node.get("required_gates", [])),
        list(rule.get("verification_fields", [])),
    )
    missing_verification.extend(manifest_blockers)
    missing_verification.extend(f"missing_sizing:{field}" for field in sizing_missing)
    missing_verification.extend(calculation_hard_blockers)
    missing_verification.extend(calculation_promotion_blockers)
    supplied_classification = classify_supplied_designation(params)
    selected_model = params.get("vendor_model") or params.get("candidate_model")
    classification_blockers: list[str] = []
    if present(params, "vendor_model") and not supplied_classification["is_vendor_model"]:
        classification_blockers.append(
            f"vendor_model_content_reclassified:{supplied_classification['classification']}"
        )
    missing_verification.extend(classification_blockers)
    vendor_policy = "vendor" in policy
    selected_model_eligible = bool(selected_model) and (
        not vendor_policy or supplied_classification["is_vendor_model"]
    )
    machine_closed = (
        evidence_closed
        and not manifest_blockers
        and not sizing_missing
        and not calculation_hard_blockers
        and not calculation_promotion_blockers
        and not classification_blockers
        and selected_model_eligible
    )
    approval_blockers = audit_final_approval(params, rule["id"], list(family_node.get("required_gates", [])), manifest)
    final_approved = (
        machine_closed
        and present(params, "formal_calculation_sha256")
        and present(params, "formal_calculation_path")
        and token(params.get("approval_status")) in {token(word) for word in APPROVED_WORDS}
        and token((manifest or {}).get("approval_status")) in {token(word) for word in APPROVED_WORDS}
        and not approval_blockers
    )
    if calculation_hard_blockers:
        return "calculation_blocked", sorted(set(missing_verification + approval_blockers)), {
            "status": "BLOCKED_CALCULATION",
            "blockers": sorted(set(calculation_hard_blockers)),
            "final_approval_blockers": approval_blockers,
        }
    if calculation_promotion_blockers:
        return "type_selected", sorted(set(missing_verification + approval_blockers)), {
            "status": "CAPPED_TYPE_SCREENING",
            "promotion_cap": "TYPE_SCREENING",
            "blockers": sorted(set(calculation_promotion_blockers)),
            "final_approval_blockers": approval_blockers,
        }
    if final_approved:
        return "final_model", [], {"status": "CLOSED", "blockers": []}
    if policy == "custom_engineered_equipment":
        return "custom_equipment_no_universal_model", sorted(set(missing_verification + approval_blockers)), {"status": "CLOSED" if machine_closed else "OPEN", "blockers": manifest_blockers, "final_approval_blockers": approval_blockers}
    if machine_closed:
        return "same_equipment_verified", approval_blockers, {"status": "CLOSED", "blockers": [], "final_approval_blockers": approval_blockers}
    if supplied_classification["classification"] == "standard_marking":
        return "standard_candidate", sorted(set(missing_verification)), {"status": "OPEN", "blockers": manifest_blockers}
    if supplied_classification["classification"] in {"engineering_specification", "unclassified_supplied_designation"}:
        return "type_selected", sorted(set(missing_verification)), {"status": "OPEN", "blockers": manifest_blockers}
    if supplied_classification["is_vendor_model"]:
        return "vendor_candidate", sorted(set(missing_verification)), {"status": "OPEN", "blockers": manifest_blockers}
    standard_candidate = present(params, "candidate_model") and present(params, "standard_lookup_sha256") and present(params, "standard_lookup_path")
    if policy.startswith("standard_") or "standard_series" in policy:
        return ("standard_candidate" if standard_candidate else "type_selected"), sorted(set(missing_verification)), {"status": "OPEN", "blockers": manifest_blockers}
    return "type_selected", sorted(set(missing_verification)), {"status": "OPEN", "blockers": manifest_blockers}


_STANDARD_DESIGNATION = re.compile(
    r"(?:^|\b)(?:GB(?:/T|/Z)?|JB(?:/T)?|HG(?:/T)?|SH(?:/T)?|NB(?:/T)?|API|ASME|ISO|EN|DIN|ANSI|IEC)\s*[-/]?\s*\d",
    re.IGNORECASE,
)
_BARE_STANDARD_SIZE_MARK = re.compile(r"^\s*\d{1,4}\s*-\s*\d{1,4}\s*-\s*\d{1,4}(?:\s*@.*)?$", re.IGNORECASE)
_ENGINEERING_SPEC_TOKENS = (
    re.compile(r"(?:^|\b)DN\s*\d+", re.IGNORECASE),
    re.compile(r"(?:^|\b)PN\s*\d+", re.IGNORECASE),
    re.compile(r"(?:^|\b)(?:CLASS|CL)\s*\d+", re.IGNORECASE),
    re.compile(r"(?:^|\b)CV\s*[-:=]?\s*\d+", re.IGNORECASE),
)


def classify_supplied_designation(params: dict[str, Any]) -> dict[str, Any]:
    """Classify content, not merely the caller's field name.

    A standard mark or an engineering specification entered in ``vendor_model``
    remains useful, but is explicitly prevented from becoming a vendor claim.
    A vendor candidate requires a same-record datasheet path/hash pair; formal
    promotion still requires the stricter evidence manifest and audit gates.
    """
    field = "vendor_model" if present(params, "vendor_model") else "candidate_model" if present(params, "candidate_model") else None
    value = str(params.get(field, "")).strip() if field else ""
    if not value:
        return {
            "field": None,
            "value": None,
            "classification": "none",
            "is_vendor_model": False,
            "reasons": ["no_supplied_designation"],
        }
    if _STANDARD_DESIGNATION.search(value) or _BARE_STANDARD_SIZE_MARK.fullmatch(value):
        return {
            "field": field,
            "value": value,
            "classification": "standard_marking",
            "is_vendor_model": False,
            "reasons": ["standard_identifier_or_standard_size_mark_detected"],
        }
    spec_hits = [pattern.pattern for pattern in _ENGINEERING_SPEC_TOKENS if pattern.search(value)]
    if len(spec_hits) >= 2:
        return {
            "field": field,
            "value": value,
            "classification": "engineering_specification",
            "is_vendor_model": False,
            "reasons": ["multiple_engineering_specification_tokens_detected"],
        }
    vendor_evidence_pair = present(params, "vendor_datasheet_path") and present(params, "vendor_datasheet_sha256")
    if field == "vendor_model" and vendor_evidence_pair:
        return {
            "field": field,
            "value": value,
            "classification": "vendor_candidate",
            "is_vendor_model": True,
            "reasons": ["vendor_field_and_datasheet_path_hash_pair_present"],
        }
    if field == "candidate_model" and present(params, "standard_lookup_path") and present(params, "standard_lookup_sha256"):
        return {
            "field": field,
            "value": value,
            "classification": "standard_marking",
            "is_vendor_model": False,
            "reasons": ["candidate_field_and_standard_lookup_path_hash_pair_present"],
        }
    return {
        "field": field,
        "value": value,
        "classification": "unclassified_supplied_designation",
        "is_vendor_model": False,
        "reasons": ["field_name_alone_is_not_vendor_evidence"],
    }


def _engineering_number(value: float) -> str:
    if value == 0:
        return "0"
    return f"{value:.6g}"


# Do not compact digit suffixes embedded in formula/function identifiers such
# as ``ceil_100mm``.  The previous look-behind blocked the first digit after
# ``_`` but then matched the remaining ``00`` and rewrote the label to
# ``ceil_10mm`` even though the numeric calculation still used 100 mm steps.
_SUBSTITUTION_NUMBER = re.compile(r"(?<![A-Za-z0-9_])(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")


def _compact_substitution_numbers(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        token_value = match.group(0)
        try:
            return _engineering_number(float(token_value))
        except ValueError:
            return token_value

    return _SUBSTITUTION_NUMBER.sub(replace, value)


_FORMULA_SOURCE_BINDING_CACHE: dict[str, dict[str, Any]] = {}
_FORMULA_IMPLEMENTATION_BINDING_CACHE: dict[str, Any] | None = None


def _sha256_file_for_formula_trace(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _formula_source_binding(reference: str) -> dict[str, Any]:
    """Bind a formula source route to a local file hash when one is packaged."""

    reference = str(reference).strip()
    cached = _FORMULA_SOURCE_BINDING_CACHE.get(reference)
    if cached is not None:
        return dict(cached)
    relative, separator, anchor = reference.partition("#")
    normalized = relative.replace("\\", "/").lstrip("/")
    local_prefixes = ("knowledge_graph/", "data/", "app/", "scripts/")
    if not normalized.startswith(local_prefixes):
        result = {
            "reference": reference,
            "source_kind": "external_citation",
            "binding_status": "EXTERNAL_DOCUMENT_NOT_PACKAGED",
            "relative_path": None,
            "anchor": anchor or None,
            "source_file_sha256": None,
            "locator_line_1based": None,
        }
        _FORMULA_SOURCE_BINDING_CACHE[reference] = result
        return dict(result)

    path = PACKAGE_ROOT / Path(normalized)
    if not path.is_file():
        result = {
            "reference": reference,
            "source_kind": "registered_local_asset",
            "binding_status": "REGISTERED_ASSET_MISSING",
            "relative_path": normalized,
            "anchor": anchor or None,
            "source_file_sha256": None,
            "locator_line_1based": None,
        }
        _FORMULA_SOURCE_BINDING_CACHE[reference] = result
        return dict(result)

    digest = _sha256_file_for_formula_trace(path)
    locator_line: int | None = None
    anchor_status = "NO_ANCHOR_DECLARED"
    if separator and anchor:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            lines = []
        token = anchor.casefold()
        locator_line = next(
            (index for index, line in enumerate(lines, 1) if token in line.casefold()),
            None,
        )
        anchor_status = "ANCHOR_TOKEN_FOUND" if locator_line is not None else "ANCHOR_TOKEN_NOT_FOUND"
    result = {
        "reference": reference,
        "source_kind": "registered_local_asset",
        "binding_status": (
            "FILE_AND_ANCHOR_BOUND"
            if anchor_status == "ANCHOR_TOKEN_FOUND"
            else "FILE_BOUND_NO_ANCHOR"
            if anchor_status == "NO_ANCHOR_DECLARED"
            else "FILE_BOUND_ANCHOR_OPEN"
        ),
        "relative_path": normalized,
        "anchor": anchor or None,
        "anchor_status": anchor_status,
        "source_file_sha256": digest,
        "locator_line_1based": locator_line,
    }
    _FORMULA_SOURCE_BINDING_CACHE[reference] = result
    return dict(result)


def _formula_implementation_binding() -> dict[str, Any]:
    """Return the source-code-manifest binding for the executable formula branch."""

    global _FORMULA_IMPLEMENTATION_BINDING_CACHE
    if _FORMULA_IMPLEMENTATION_BINDING_CACHE is not None:
        return dict(_FORMULA_IMPLEMENTATION_BINDING_CACHE)
    relative = "scripts/equipment_design_match.py"
    manifest_path = PACKAGE_ROOT / "app" / "source_code_manifest.json"
    manifest: dict[str, Any] = {}
    if manifest_path.is_file():
        try:
            loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest = loaded if isinstance(loaded, dict) else {}
        except (OSError, json.JSONDecodeError):
            manifest = {}
    record = next(
        (
            item
            for item in manifest.get("files", [])
            if isinstance(item, dict) and item.get("source_path") == relative
        ),
        {},
    )
    actual_path = PACKAGE_ROOT / relative
    actual_sha = (
        _sha256_file_for_formula_trace(actual_path)
        if actual_path.is_file()
        else None
    )
    manifest_sha = str(record.get("sha256") or "").strip().upper() or None
    if actual_sha and manifest_sha:
        binding_status = (
            "SOURCE_FILE_MATCHES_MANIFEST"
            if actual_sha == manifest_sha
            else "SOURCE_FILE_MANIFEST_MISMATCH"
        )
    elif manifest_sha:
        binding_status = "PACKAGED_SOURCE_BOUND_BY_MANIFEST"
    else:
        binding_status = "SOURCE_MANIFEST_BINDING_MISSING"
    _FORMULA_IMPLEMENTATION_BINDING_CACHE = {
        "implementation_ref": f"{relative}#run_calculations",
        "branch_key": "calculation_id",
        "engine_version": ENGINE_VERSION,
        "source_file_sha256": manifest_sha or actual_sha,
        "actual_source_file_sha256": actual_sha,
        "source_code_set_sha256": manifest.get("source_code_set_sha256"),
        "source_manifest_payload_sha256": manifest.get("manifest_payload_sha256"),
        "binding_status": binding_status,
    }
    return dict(_FORMULA_IMPLEMENTATION_BINDING_CACHE)


def _formula_input_binding(
    field: str,
    value: Any,
    lineage: dict[str, Any] | None,
) -> dict[str, Any]:
    lineage = dict(lineage or {})
    if lineage.get("calculation_id") and not lineage.get("fallback_tier"):
        source_kind = "upstream_registered_calculation"
        binding_status = "UPSTREAM_CALCULATION_BOUND"
    elif lineage.get("fallback_tier"):
        source_kind = "registered_or_model_fallback"
        binding_status = "PROVISIONAL_FALLBACK_BOUND"
    else:
        source_kind = "normalized_input"
        binding_status = "SOURCE_PROVENANCE_NOT_ESTABLISHED_BY_MATCHER"
    value_binding = {
        "field_id": field,
        "value": value,
        "unit": FIELD_UNITS.get(field),
        "source_kind": source_kind,
        "binding_status": binding_status,
        "evidence_class": lineage.get(
            "evidence_class",
            "U" if source_kind == "normalized_input" else "J",
        ),
        "upstream_calculation_id": lineage.get("calculation_id"),
        "upstream_formula_trace_sha256": lineage.get("formula_trace_sha256"),
        "fallback_tier": lineage.get("fallback_tier"),
    }
    value_binding["field_value_sha256"] = _canonical_sha256({
        "field_id": field,
        "value": value,
        "unit": value_binding["unit"],
        "source_kind": source_kind,
    })
    return value_binding


def _formula_trace(
    calc_id: str,
    target_field: str,
    formula: str,
    substitution: str,
    value: float,
    unit: str,
    input_bindings: list[dict[str, Any]],
    policy: dict[str, Any],
) -> dict[str, Any]:
    source_bindings = [
        _formula_source_binding(reference)
        for reference in policy.get("source_refs", [])
    ]
    implementation = _formula_implementation_binding()
    definition = {
        "calculation_id": calc_id,
        "formula_id": policy.get("formula_id", calc_id),
        "formula_expression": formula,
        "target_field": target_field,
        "output_unit": unit,
        "dependency_fields": [item["field_id"] for item in input_bindings],
        "release_class": policy.get("release_class", "A"),
        "declared_evidence_class": policy.get("evidence_class", "D"),
        "applicability": policy.get("applicability"),
        "does_not_prove": list(policy.get("does_not_prove", [])),
        "promotion_cap": policy.get("promotion_cap", "DERIVED_PARAMETER"),
        "implementation_binding": implementation,
        "source_bindings": source_bindings,
    }
    definition_sha256 = _canonical_sha256(definition)
    open_gaps: list[str] = []
    for item in input_bindings:
        if item.get("binding_status") == "SOURCE_PROVENANCE_NOT_ESTABLISHED_BY_MATCHER":
            open_gaps.append(f"input_source_provenance_open:{item.get('field_id')}")
        elif item.get("binding_status") == "PROVISIONAL_FALLBACK_BOUND":
            open_gaps.append(f"provisional_input:{item.get('field_id')}")
    for item in source_bindings:
        if item.get("binding_status") not in {
            "FILE_AND_ANCHOR_BOUND",
            "FILE_BOUND_NO_ANCHOR",
        }:
            open_gaps.append(
                f"formula_source_open:{item.get('reference')}:{item.get('binding_status')}"
            )
    if implementation.get("binding_status") not in {
        "SOURCE_FILE_MATCHES_MANIFEST",
        "PACKAGED_SOURCE_BOUND_BY_MANIFEST",
    }:
        open_gaps.append(
            f"implementation_binding_open:{implementation.get('binding_status')}"
        )
    trace = {
        "schema": "equipment-formula-trace-v1",
        "traceability_status": (
            "COMPLETE_REPRODUCIBLE_TRACE"
            if not open_gaps
            else "REPRODUCIBLE_TRACE_WITH_OPEN_PROVENANCE"
        ),
        "calculation_id": calc_id,
        "formula_id": definition["formula_id"],
        "formula_definition": definition,
        "formula_definition_sha256": definition_sha256,
        "input_bindings": input_bindings,
        "substitution": substitution,
        "output": {
            "target_field": target_field,
            "value": value,
            "unit": unit,
        },
        "open_traceability_gaps": sorted(set(open_gaps)),
    }
    trace["calculation_trace_sha256"] = _canonical_sha256(trace)
    return trace


def calculation_record(
    calc_id: str,
    formula: str,
    substitution: str,
    value: float,
    unit: str,
    target: str | None = None,
    upstream_formula_lineage: list[dict[str, Any]] | None = None,
    input_bindings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    target_field = target or CALCULATION_OUTPUT_FIELDS.get(calc_id, calc_id)
    substitution = _compact_substitution_numbers(substitution)
    answer = f"{_engineering_number(value)} {unit}".strip()
    policy = dict(CALCULATION_POLICIES.get(calc_id, {}))
    notice = {
        "code": "BUILT_IN_FORMULA_RESULT",
        "severity": "warning",
        "calculation_id": calc_id,
        "formula_id": policy.get("formula_id", calc_id),
        "release_class": policy.get("release_class", "A"),
        "evidence_class": policy.get("evidence_class", "D"),
        "result_status": policy.get("result_status", "DERIVED"),
        "title": policy.get("title", "内置公式计算结果"),
        "message": policy.get(
            "message",
            "该值由应用内置公式生成，并非 Aspen 或用户直接输出；请核对输入和适用条件。",
        ),
        "applicability": policy.get("applicability", "仅在公式输入、单位和物理分支均成立时适用。"),
        "does_not_prove": list(policy.get("does_not_prove", [])),
        "promotion_cap": policy.get("promotion_cap", "DERIVED_PARAMETER"),
        "source_refs": list(policy.get("source_refs", [])),
        "embedded_empirical_default_used": False,
    }
    upstream_formula_lineage = list(upstream_formula_lineage or [])
    provisional_upstream = [
        item
        for item in upstream_formula_lineage
        if item.get("evidence_class") == "J"
        or item.get("result_status") == "PROVISIONAL"
        or item.get("promotion_cap") == "TYPE_SCREENING"
    ]
    notice["declared_formula_evidence_class"] = notice["evidence_class"]
    notice["declared_formula_result_status"] = notice["result_status"]
    notice["declared_formula_promotion_cap"] = notice["promotion_cap"]
    notice["upstream_formula_lineage"] = upstream_formula_lineage
    notice["risk_propagated_from_upstream"] = bool(provisional_upstream)
    if provisional_upstream:
        notice["evidence_class"] = "J"
        notice["result_status"] = "PROVISIONAL"
        notice["promotion_cap"] = "TYPE_SCREENING"
        upstream_ids = ", ".join(
            sorted({str(item.get("calculation_id")) for item in provisional_upstream})
        )
        notice["title"] = f"{notice['title']}（继承上游初筛状态）"
        notice["message"] = (
            f"{notice['message']} 本结果使用了上游初筛公式结果（{upstream_ids}），"
            "因此证据等级继承为 J/provisional，最高只能用于型式初筛。"
        )
    formula_trace = _formula_trace(
        calc_id,
        target_field,
        formula,
        substitution,
        value,
        unit,
        list(input_bindings or []),
        policy,
    )
    notice["source_bindings"] = formula_trace["formula_definition"]["source_bindings"]
    notice["formula_definition_sha256"] = formula_trace["formula_definition_sha256"]
    notice["calculation_trace_sha256"] = formula_trace["calculation_trace_sha256"]
    notice["traceability_status"] = formula_trace["traceability_status"]
    notice["open_traceability_gaps"] = formula_trace["open_traceability_gaps"]
    return {
        "calculation_id": calc_id,
        "target_field": target_field,
        "equation_chain": f"{target_field} = {formula} = {substitution} = {answer}",
        "formula_chain": {
            "target": target_field,
            "formula": formula,
            "substitution": substitution,
            "answer": answer,
            "dependencies": list(CALCULATION_REQUIREMENTS.get(calc_id, ())),
        },
        "value": value,
        "unit": unit,
        "status": (
            "CALCULATED_WITH_PROVISIONAL_UPSTREAM"
            if provisional_upstream
            else "CALCULATED_WITH_EXPLICIT_INPUTS"
        ),
        "evidence_status": "NUMERICALLY_DERIVED_NOT_SOURCE_VERIFIED_BY_MATCHER",
        "calculation_notice": notice,
        "formula_trace": formula_trace,
    }


def run_calculations(
    rule: dict[str, Any],
    params: dict[str, Any],
    fallback_lineage: dict[str, dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    requested = list(rule.get("calculation_rules", []))
    requested.extend(BLOCK_TYPE_CALCULATION_RULES.get(str(params.get("aspen_block_type") or "").strip().upper(), ()))
    requested = list(dict.fromkeys(requested))
    if (
        present(params, "design_pressure_mpa")
        and params.get("design_pressure_basis") == "absolute"
    ):
        requested.insert(0, "design_pressure_basis_conversion")
    work = dict(params)
    comparison_params = dict(params)
    results: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []
    derived: dict[str, Any] = {}
    hard_blocked: set[str] = set()
    unavailable_calculations: set[str] = set()
    formula_lineage_by_field: dict[str, dict[str, Any]] = {
        str(field): dict(item)
        for field, item in (fallback_lineage or {}).items()
    }

    def add_result(
        calc_id: str,
        formula: str,
        substitution: str,
        value: float,
        unit: str,
        target: str | None = None,
        dependency_fields: list[str] | None = None,
    ) -> None:
        active_dependencies = list(
            dependency_fields
            if dependency_fields is not None
            else CALCULATION_REQUIREMENTS.get(calc_id, ())
        )
        if (
            calc_id == "pressure_ratio"
            and work.get("pressure_basis") == "gauge"
            and "atmospheric_pressure_mpa" not in active_dependencies
        ):
            active_dependencies.append("atmospheric_pressure_mpa")
        if (
            calc_id == "design_pressure"
            and work.get("pressure_basis") == "absolute"
            and "atmospheric_pressure_mpa" not in active_dependencies
        ):
            active_dependencies.append("atmospheric_pressure_mpa")
        upstream_formula_lineage = [
            dict(formula_lineage_by_field[field])
            for field in active_dependencies
            if field in formula_lineage_by_field
        ]
        input_bindings = [
            _formula_input_binding(
                field,
                work.get(field),
                formula_lineage_by_field.get(field),
            )
            for field in active_dependencies
            if present(work, field)
        ]
        item = calculation_record(
            calc_id,
            formula,
            substitution,
            value,
            unit,
            target,
            upstream_formula_lineage,
            input_bindings,
        )
        target_field = str(item["target_field"])
        notice = item.get("calculation_notice", {})
        release_class = str(notice.get("release_class", "A"))
        effective_evidence_class = str(notice.get("evidence_class", "D"))
        target_lineage = formula_lineage_by_field.get(target_field, {})
        target_is_model_estimate = (
            target_lineage.get("fallback_tier") == "LLM_LAST_RESORT_ENGINEERING_ESTIMATE"
        )
        preserve_provided_target = (
            release_class == "B" or effective_evidence_class == "J"
        ) and present(comparison_params, target_field) and not target_is_model_estimate
        if present(comparison_params, target_field):
            supplied_value = float(comparison_params[target_field])
            relative_tolerance, absolute_tolerance = CALCULATION_TARGET_TOLERANCES.get(
                target_field, (0.005, 1e-9)
            )
            matched = math.isclose(
                supplied_value,
                value,
                rel_tol=relative_tolerance,
                abs_tol=absolute_tolerance,
            )
            difference = supplied_value - value
            relative_difference = (
                abs(difference) / max(abs(value), absolute_tolerance)
                if value != 0 or absolute_tolerance != 0
                else 0.0
            )
            crosscheck = {
                "status": "PASS" if matched else "FAIL",
                "authority_choice": (
                    "deterministic_calculation_supersedes_model_estimate"
                    if target_is_model_estimate
                    else
                    "provided_target_preserved; built_in_formula_is_provisional_screening"
                    if preserve_provided_target
                    else "deterministic_calculation"
                ),
                "provided_value": supplied_value,
                "calculated_value": value,
                "difference": difference,
                "relative_difference": relative_difference,
                "relative_tolerance": relative_tolerance,
                "absolute_tolerance": absolute_tolerance,
                "unit": unit,
            }
            item["provided_target_crosscheck"] = crosscheck
            if target_is_model_estimate:
                item["status"] = (
                    "CALCULATED_SUPERSEDED_MODEL_ESTIMATE_MATCH"
                    if matched
                    else "CALCULATED_SUPERSEDED_MODEL_ESTIMATE_CONFLICT"
                )
            elif preserve_provided_target:
                item["status"] = (
                    "PROVISIONAL_SCREENING_CROSSCHECK_PASS"
                    if matched
                    else "PROVISIONAL_SCREENING_DIFFERENCE"
                )
            else:
                item["status"] = "CALCULATED_AND_CROSSCHECKED" if matched else "CALCULATED_TARGET_MISMATCH"
            if not matched:
                mismatch = {
                    "calculation_id": calc_id,
                    "target_field": target_field,
                    **crosscheck,
                    "crosscheck_status": crosscheck["status"],
                    "status": (
                        "WARNING_MODEL_ESTIMATE_SUPERSEDED"
                        if target_is_model_estimate
                        else
                        "WARNING_PROVISIONAL_SCREENING_DIFFERENCE"
                        if preserve_provided_target
                        else "BLOCKED_TARGET_MISMATCH"
                    ),
                }
                pending.append(mismatch)
                if not preserve_provided_target and not target_is_model_estimate:
                    hard_blocked.add(calc_id)
        item["adopted_as_canonical"] = not preserve_provided_target
        item["canonical_value"] = (
            comparison_params[target_field]
            if preserve_provided_target
            else value
        )
        results.append(item)
        # Exact class-A identities remain canonical.  A class-B screening
        # formula may fill a missing value, but it never overwrites a supplied
        # same-case value; it remains a visible cross-check instead.
        if preserve_provided_target:
            work[target_field] = comparison_params[target_field]
        else:
            work[target_field] = value
            derived[target_field] = value
            formula_lineage_by_field[target_field] = {
                "calculation_id": calc_id,
                "target_field": target_field,
                "release_class": notice.get("release_class", "A"),
                "evidence_class": notice.get("evidence_class", "D"),
                "result_status": notice.get("result_status", "DERIVED"),
                "promotion_cap": notice.get("promotion_cap", "DERIVED_PARAMETER"),
                "formula_trace_sha256": item.get("formula_trace", {}).get(
                    "calculation_trace_sha256"
                ),
                "traceability_status": item.get("formula_trace", {}).get(
                    "traceability_status"
                ),
            }

    if present(work, "design_pressure_mpa") and not present(work, "design_pressure_basis"):
        pending.append({
            "calculation_id": "design_pressure_basis_conversion",
            "status": "WAITING_PHYSICAL_BASIS",
            "missing_fields": ["design_pressure_basis"],
            "action": "declare whether the supplied design pressure is absolute or gauge",
        })
        # Do not compare or replace an ambiguous direct design-pressure value
        # with an operating-pressure screening formula.  Until its basis is
        # declared, the direct value cannot enter thickness or candidate data.
        unavailable_calculations.add("design_pressure")
    if (
        present(work, "design_pressure_mpa")
        and work.get("design_pressure_basis") == "gauge"
        and float(work["design_pressure_mpa"]) <= 0
    ):
        pending.append({
            "calculation_id": "design_pressure",
            "status": "BLOCKED_EXTERNAL_PRESSURE_BRANCH_REQUIRED",
            "required": "separate vacuum/external-pressure mechanical design branch",
            "design_pressure_gauge_mpa": float(work["design_pressure_mpa"]),
            "action": "provide same-equipment external-pressure design evidence; do not use the internal-pressure thickness formula",
        })
        hard_blocked.add("design_pressure")
        unavailable_calculations.add("design_pressure")

    for calc_id in requested:
        required = list(CALCULATION_REQUIREMENTS[calc_id])
        if (
            calc_id == "design_pressure"
            and present(work, "design_pressure_mpa")
            and not present(work, "design_pressure_basis")
        ):
            continue
        if calc_id == "pressure_ratio" and params.get("pressure_basis") == "gauge":
            required.append("atmospheric_pressure_mpa")
        if calc_id == "design_pressure" and params.get("pressure_basis") == "absolute":
            required.append("atmospheric_pressure_mpa")
        if (
            calc_id == "design_pressure"
            and "design_pressure_basis_conversion" in unavailable_calculations
        ):
            upstream_is_hard = "design_pressure_basis_conversion" in hard_blocked
            pending.append({
                "calculation_id": calc_id,
                "status": (
                    "BLOCKED_UPSTREAM_CALCULATION"
                    if upstream_is_hard
                    else "WAITING_UPSTREAM_CALCULATION"
                ),
                "upstream": "design_pressure_basis_conversion",
            })
            if upstream_is_hard:
                hard_blocked.add(calc_id)
            unavailable_calculations.add(calc_id)
            continue
        if (
            calc_id in {"cylinder_thickness", "head_thickness"}
            and "design_pressure_basis_conversion" in unavailable_calculations
            and not (
                CALCULATION_OUTPUT_FIELDS.get(calc_id)
                and present(work, CALCULATION_OUTPUT_FIELDS[calc_id])
            )
        ):
            upstream_is_hard = "design_pressure_basis_conversion" in hard_blocked
            pending.append({
                "calculation_id": calc_id,
                "status": (
                    "BLOCKED_UPSTREAM_CALCULATION"
                    if upstream_is_hard
                    else "WAITING_UPSTREAM_CALCULATION"
                ),
                "upstream": "design_pressure_basis_conversion",
            })
            if upstream_is_hard:
                hard_blocked.add(calc_id)
            unavailable_calculations.add(calc_id)
            continue
        if calc_id in {"cylinder_thickness", "head_thickness"} and present(work, "design_pressure_basis"):
            if work["design_pressure_basis"] != "gauge":
                pending.append({
                    "calculation_id": calc_id,
                    "status": "WAITING_PHYSICAL_BASIS",
                    "required": "design_pressure_mpa canonicalized to gauge basis",
                    "provided_design_pressure_basis": work["design_pressure_basis"],
                    "missing_fields": ["atmospheric_pressure_mpa"] if not present(work, "atmospheric_pressure_mpa") else [],
                })
                unavailable_calculations.add(calc_id)
                continue
        if calc_id == "pump_head_from_pressure" and present(work, "inlet_pressure_mpa") and present(work, "outlet_pressure_mpa"):
            if float(work["outlet_pressure_mpa"]) <= float(work["inlet_pressure_mpa"]):
                pending.append({"calculation_id": calc_id, "status": "BLOCKED_PHYSICAL_DIRECTION", "required": "Pout > Pin for pump head rise", "inlet_pressure_mpa": work["inlet_pressure_mpa"], "outlet_pressure_mpa": work["outlet_pressure_mpa"]})
                hard_blocked.add(calc_id)
                unavailable_calculations.add(calc_id)
                continue
        if calc_id == "valve_pressure_drop_from_streams" and present(work, "inlet_pressure_mpa") and present(work, "outlet_pressure_mpa"):
            if float(work["inlet_pressure_mpa"]) <= float(work["outlet_pressure_mpa"]):
                pending.append({
                    "calculation_id": calc_id,
                    "status": "BLOCKED_PHYSICAL_DIRECTION",
                    "required": "Pin > Pout for valve pressure drop",
                    "inlet_pressure_mpa": work["inlet_pressure_mpa"],
                    "outlet_pressure_mpa": work["outlet_pressure_mpa"],
                })
                hard_blocked.add(calc_id)
                unavailable_calculations.add(calc_id)
                continue
        if calc_id == "valve_liquid_equivalent_cv_screening":
            valve_phase = canonical_phase(work.get("phase"))
            if valve_phase != "liquid":
                pending.append({
                    "calculation_id": calc_id,
                    "status": "BLOCKED_PHASE_INCOMPATIBLE_FORMULA",
                    "required": (
                        "single-phase liquid for the incompressible Cv equation; "
                        "gas service requires a compressible/critical-flow branch"
                    ),
                    "observed_phase": valve_phase or "unknown",
                    "prohibited_output_field": "cv",
                    "required_gas_fields": [
                        "absolute_inlet_pressure",
                        "absolute_outlet_pressure",
                        "inlet_temperature_k",
                        "gas_molecular_weight",
                        "compressibility_factor",
                        "specific_heat_ratio",
                        "valve_pressure_recovery_xT_or_piping_factor_xTP",
                        "piping_geometry_factor_Fp",
                        "valve_style_modifier_Fd",
                    ],
                })
                hard_blocked.add(calc_id)
                unavailable_calculations.add(calc_id)
                work.pop("cv", None)
                continue
        if calc_id == "valve_liquid_equivalent_cv_screening" and present(work, "pressure_drop_kpa"):
            if float(work["pressure_drop_kpa"]) <= 0.0:
                pending.append({
                    "calculation_id": calc_id,
                    "status": "BLOCKED_NONPOSITIVE_PRESSURE_DROP",
                    "required": "pressure_drop_kpa > 0 for Cv screening",
                    "pressure_drop_kpa": work["pressure_drop_kpa"],
                })
                hard_blocked.add(calc_id)
                unavailable_calculations.add(calc_id)
                continue
        if calc_id in {"liquid_turbine_pressure_head", "liquid_turbine_hydraulic_power"} and present(work, "inlet_pressure_mpa") and present(work, "outlet_pressure_mpa"):
            if float(work["inlet_pressure_mpa"]) <= float(work["outlet_pressure_mpa"]):
                pending.append({
                    "calculation_id": calc_id,
                    "status": "BLOCKED_PHYSICAL_DIRECTION",
                    "required": "Pin > Pout for liquid power recovery",
                    "inlet_pressure_mpa": work["inlet_pressure_mpa"],
                    "outlet_pressure_mpa": work["outlet_pressure_mpa"],
                })
                hard_blocked.add(calc_id)
                unavailable_calculations.add(calc_id)
                continue
        if calc_id == "exchanger_area" and present(work, "heat_duty_kw") and float(work["heat_duty_kw"]) == 0.0:
            pending.append({
                "calculation_id": calc_id,
                "status": "BLOCKED_ZERO_DUTY_NO_EQUIPMENT_LOAD",
                "heat_duty_kw": 0.0,
                "action": "confirm a nonzero same-case heat duty or classify the Aspen node as no-load/not-applicable",
            })
            hard_blocked.add(calc_id)
            unavailable_calculations.add(calc_id)
            continue
        output_field = CALCULATION_OUTPUT_FIELDS.get(calc_id)
        if (
            calc_id in {"pump_hydraulic_power", "pump_shaft_power"}
            and "pump_head_from_pressure" in unavailable_calculations
            and not present(work, "head_m")
            and not (output_field and present(work, output_field))
        ):
            upstream_is_hard = "pump_head_from_pressure" in hard_blocked
            pending.append({
                "calculation_id": calc_id,
                "status": (
                    "BLOCKED_UPSTREAM_CALCULATION"
                    if upstream_is_hard
                    else "WAITING_UPSTREAM_CALCULATION"
                ),
                "upstream": "pump_head_from_pressure",
            })
            if upstream_is_hard:
                hard_blocked.add(calc_id)
            unavailable_calculations.add(calc_id)
            continue
        if (
            calc_id in {"cylinder_thickness", "head_thickness"}
            and "design_pressure" in unavailable_calculations
            and not (output_field and present(work, output_field))
        ):
            upstream_is_hard = "design_pressure" in hard_blocked
            pending.append({
                "calculation_id": calc_id,
                "status": (
                    "BLOCKED_UPSTREAM_CALCULATION"
                    if upstream_is_hard
                    else "WAITING_UPSTREAM_CALCULATION"
                ),
                "upstream": "design_pressure",
            })
            if upstream_is_hard:
                hard_blocked.add(calc_id)
            unavailable_calculations.add(calc_id)
            continue
        if (
            calc_id == "liquid_turbine_shaft_power"
            and "liquid_turbine_hydraulic_power" in unavailable_calculations
            and not (output_field and present(work, output_field))
        ):
            upstream_is_hard = "liquid_turbine_hydraulic_power" in hard_blocked
            pending.append({
                "calculation_id": calc_id,
                "status": (
                    "BLOCKED_UPSTREAM_CALCULATION"
                    if upstream_is_hard
                    else "WAITING_UPSTREAM_CALCULATION"
                ),
                "upstream": "liquid_turbine_hydraulic_power",
            })
            if upstream_is_hard:
                hard_blocked.add(calc_id)
            unavailable_calculations.add(calc_id)
            continue
        if (
            calc_id == "head_thickness"
            and present(work, "head_type")
            and work["head_type"] != "2:1_ellipsoidal"
            and not (output_field and present(work, output_field))
        ):
            pending.append({
                "calculation_id": calc_id,
                "status": "BLOCKED_UNSUPPORTED_FORMULA_BRANCH",
                "provided_head_type": work["head_type"],
                "supported_head_types": ["2:1_ellipsoidal"],
                "action": "select an implemented head formula or provide an externally calculated thickness",
            })
            unavailable_calculations.add(calc_id)
            continue
        if (
            calc_id == "membrane_area"
            and present(work, "membrane_geometry_type")
            and work["membrane_geometry_type"] != "cylindrical_channels"
        ):
            if output_field and present(work, output_field):
                # An externally supplied area is usable for an unsupported
                # geometry branch, but this cylindrical-channel formula must
                # not silently recompute or overwrite it.
                continue
            pending.append({
                "calculation_id": calc_id,
                "status": "BLOCKED_UNSUPPORTED_FORMULA_BRANCH",
                "provided_membrane_geometry_type": work["membrane_geometry_type"],
                "supported_membrane_geometry_types": ["cylindrical_channels"],
                "action": "select an implemented membrane geometry or provide an externally calculated area",
            })
            unavailable_calculations.add(calc_id)
            continue
        missing = [field for field in required if not present(work, field)]
        if missing:
            # A supplied target can still be used when its derivation inputs are
            # unavailable; only a *closeable* deterministic formula overrides it.
            if output_field and present(work, output_field) and calc_id != "design_pressure_basis_conversion":
                continue
            item: dict[str, Any] = {"calculation_id": calc_id, "missing_fields": missing}
            if calc_id in {
                "pressure_ratio", "pump_head_from_pressure", "design_pressure",
                "design_pressure_basis_conversion",
            } and any(
                field in missing for field in ("pressure_basis", "atmospheric_pressure_mpa")
            ):
                item["status"] = "WAITING_PHYSICAL_BASIS"
                unavailable_calculations.add(calc_id)
            elif calc_id == "head_thickness" and "head_type" in missing:
                item["status"] = "WAITING_FORMULA_BRANCH"
                item["supported_head_types"] = ["2:1_ellipsoidal"]
                unavailable_calculations.add(calc_id)
            elif calc_id == "membrane_area" and "membrane_geometry_type" in missing:
                item["status"] = "WAITING_FORMULA_BRANCH"
                item["supported_membrane_geometry_types"] = ["cylindrical_channels"]
                unavailable_calculations.add(calc_id)
            pending.append(item)
            continue
        try:
            if calc_id == "crystallizer_working_volume":
                slurry_flow = float(work["slurry_flow_m3_h"])
                residence_time = float(work["retention_time_min"])
                if slurry_flow <= 0.0 or residence_time <= 0.0:
                    raise ValueError("slurry_flow_m3_h and retention_time_min must be positive")
                value = slurry_flow * residence_time / 60.0
                add_result(
                    calc_id,
                    "Qslurry*tau/60",
                    f"{work['slurry_flow_m3_h']}*{work['retention_time_min']}/60",
                    value,
                    "m3",
                    "working_volume_m3",
                )
            elif calc_id == "filter_area_from_cake_flux":
                solids_load = float(work["solids_feed_kg_h"])
                cake_flux = float(work["filtration_flux_kg_m2_h"])
                if solids_load <= 0.0 or cake_flux <= 0.0:
                    raise ValueError("solids_feed_kg_h and filtration_flux_kg_m2_h must be positive")
                value = solids_load / cake_flux
                add_result(
                    calc_id,
                    "m_cake/J_cake",
                    f"{work['solids_feed_kg_h']}/{work['filtration_flux_kg_m2_h']}",
                    value,
                    "m2",
                    "filter_area_m2",
                )
            elif calc_id == "dryer_water_evaporation":
                inlet_water = float(work["inlet_water_kg_h"])
                outlet_water = float(work["outlet_water_kg_h"])
                if inlet_water < 0.0 or outlet_water < 0.0 or outlet_water > inlet_water:
                    raise ValueError("require 0 <= outlet_water_kg_h <= inlet_water_kg_h")
                value = inlet_water - outlet_water
                add_result(
                    calc_id,
                    "m_water,in-m_water,out",
                    f"{work['inlet_water_kg_h']}-{work['outlet_water_kg_h']}",
                    value,
                    "kg/h",
                    "evaporation_rate_kg_h",
                )
            elif calc_id == "dryer_specific_duty":
                evaporation_rate = float(work["evaporation_rate_kg_h"])
                if evaporation_rate <= 0.0:
                    raise ValueError("evaporation_rate_kg_h must be positive")
                value = abs(float(work["heat_duty_kw"])) * 3600.0 / evaporation_rate
                add_result(
                    calc_id,
                    "abs(Q)*3600/m_evap",
                    f"abs({work['heat_duty_kw']})*3600/{work['evaporation_rate_kg_h']}",
                    value,
                    "kJ/kg",
                    "specific_drying_duty_kj_kg",
                )
            elif calc_id == "pump_head_from_pressure":
                dp = (float(work["outlet_pressure_mpa"]) - float(work["inlet_pressure_mpa"])) * 1_000_000.0
                value = dp / (float(work["density_kg_m3"]) * 9.80665)
                add_result(calc_id, "(Pout-Pin)/(rho*g)", f"({work['outlet_pressure_mpa']}-{work['inlet_pressure_mpa']})*10^6/({work['density_kg_m3']}*9.80665)", value, "m", "head_m")
            elif calc_id == "pump_hydraulic_power":
                value = pump_hydraulic_power_kw(float(work["flow_m3_h"]), float(work["head_m"]), float(work["density_kg_m3"]))
                add_result(calc_id, "rho*g*Q*H", f"{work['density_kg_m3']}*9.80665*({work['flow_m3_h']}/3600)*{work['head_m']}/1000", value, "kW", "hydraulic_power_kw")
            elif calc_id == "pump_shaft_power":
                value = pump_shaft_power_kw(float(work["flow_m3_h"]), float(work["head_m"]), float(work["efficiency_percent"]), float(work["density_kg_m3"]))
                add_result(calc_id, "rho*g*Q*H/eta", f"{work['density_kg_m3']}*9.80665*({work['flow_m3_h']}/3600)*{work['head_m']}/({work['efficiency_percent']}/100)/1000", value, "kW", "shaft_power_kw")
            elif calc_id == "pump_cavitation_margin":
                value = float(work["npsha_m"]) - float(work["npshr_m"])
                add_result(calc_id, "NPSHa-NPSHr", f"{work['npsha_m']}-{work['npshr_m']}", value, "m", "cavitation_margin_m")
            elif calc_id == "valve_pressure_drop_from_streams":
                value = (
                    float(work["inlet_pressure_mpa"])
                    - float(work["outlet_pressure_mpa"])
                ) * 1000.0
                add_result(
                    calc_id,
                    "(Pin-Pout)*1000",
                    f"({work['inlet_pressure_mpa']}-{work['outlet_pressure_mpa']})*1000",
                    value,
                    "kPa",
                    "pressure_drop_kpa",
                )
            elif calc_id == "valve_liquid_equivalent_cv_screening":
                specific_gravity = float(work["density_kg_m3"]) / 1000.0
                value = 11.56 * float(work["flow_m3_h"]) * math.sqrt(
                    specific_gravity / float(work["pressure_drop_kpa"])
                )
                add_result(
                    calc_id,
                    "11.56*Q*sqrt(SG/dP)",
                    (
                        f"11.56*{work['flow_m3_h']}*sqrt("
                        f"({work['density_kg_m3']}/1000)/{work['pressure_drop_kpa']})"
                    ),
                    value,
                    "-",
                    "cv",
                )
                results[-1]["formula_branch"] = {
                    "branch": "incompressible_liquid_or_liquid_equivalent_screening",
                    "phase": canonical_phase(work.get("phase")) or "unknown",
                    "gas_or_two_phase_final_cv_prohibited": canonical_phase(work.get("phase")) in {"vapor", "mixed"},
                }
            elif calc_id == "valve_maximum_pressure_drop_screening":
                value = float(work["pressure_drop_kpa"]) * float(work["maximum_pressure_drop_factor"])
                add_result(
                    calc_id,
                    "dP*kMax",
                    f"{work['pressure_drop_kpa']}*{work['maximum_pressure_drop_factor']}",
                    value,
                    "kPa",
                    "maximum_pressure_drop_kpa",
                )
            elif calc_id == "liquid_turbine_pressure_head":
                value = (
                    (float(work["inlet_pressure_mpa"]) - float(work["outlet_pressure_mpa"]))
                    * 1_000_000.0
                    / (float(work["density_kg_m3"]) * 9.80665)
                )
                add_result(
                    calc_id,
                    "(Pin-Pout)/(rho*g)",
                    f"({work['inlet_pressure_mpa']}-{work['outlet_pressure_mpa']})*10^6/({work['density_kg_m3']}*9.80665)",
                    value,
                    "m",
                    "pressure_drop_head_component_m",
                )
            elif calc_id == "liquid_turbine_hydraulic_power":
                value = (
                    (float(work["inlet_pressure_mpa"]) - float(work["outlet_pressure_mpa"]))
                    * 1_000_000.0
                    * (float(work["flow_m3_h"]) / 3600.0)
                    / 1000.0
                )
                add_result(
                    calc_id,
                    "(Pin-Pout)*Q",
                    f"({work['inlet_pressure_mpa']}-{work['outlet_pressure_mpa']})*10^6*({work['flow_m3_h']}/3600)/1000",
                    value,
                    "kW",
                    "pressure_drop_power_component_kw",
                )
            elif calc_id == "liquid_turbine_shaft_power":
                value = float(work["pressure_drop_power_component_kw"]) * float(work["efficiency_percent"]) / 100.0
                add_result(
                    calc_id,
                    "P_deltaP*eta",
                    f"{work['pressure_drop_power_component_kw']}*({work['efficiency_percent']}/100)",
                    value,
                    "kW",
                    "pressure_component_shaft_power_screening_kw",
                )
            elif calc_id == "pressure_ratio":
                patm = float(work.get("atmospheric_pressure_mpa", 0.0)) if work["pressure_basis"] == "gauge" else 0.0
                pin_abs = float(work["inlet_pressure_mpa"]) + patm
                pout_abs = float(work["outlet_pressure_mpa"]) + patm
                if rule["id"] in {"family_liquid_power_recovery_turbine", "family_gas_expander_turbine"}:
                    if pin_abs <= pout_abs:
                        pending.append({"calculation_id": calc_id, "status": "BLOCKED_PHYSICAL_DIRECTION", "required": "Pin_abs > Pout_abs", "pin_abs_mpa": pin_abs, "pout_abs_mpa": pout_abs})
                        hard_blocked.add(calc_id)
                        unavailable_calculations.add(calc_id)
                        continue
                    value = pin_abs / pout_abs
                    formula = "Pin_abs/Pout_abs"
                    substitution = f"({work['inlet_pressure_mpa']}+{patm})/({work['outlet_pressure_mpa']}+{patm})"
                    target = "expansion_pressure_ratio"
                else:
                    if pout_abs <= pin_abs:
                        pending.append({"calculation_id": calc_id, "status": "BLOCKED_PHYSICAL_DIRECTION", "required": "Pout_abs > Pin_abs", "pin_abs_mpa": pin_abs, "pout_abs_mpa": pout_abs})
                        hard_blocked.add(calc_id)
                        unavailable_calculations.add(calc_id)
                        continue
                    value = pressure_ratio(pout_abs, pin_abs)
                    formula = "Pout_abs/Pin_abs"
                    substitution = f"({work['outlet_pressure_mpa']}+{patm})/({work['inlet_pressure_mpa']}+{patm})"
                    target = "compression_pressure_ratio"
                add_result(calc_id, formula, substitution, value, "-", target)
            elif calc_id == "compressor_isentropic_shaft_power":
                patm = (
                    float(work.get("atmospheric_pressure_mpa", 0.0))
                    if work["pressure_basis"] == "gauge"
                    else 0.0
                )
                pin_abs_mpa = float(work["inlet_pressure_mpa"]) + patm
                pout_abs_mpa = float(work["outlet_pressure_mpa"]) + patm
                heat_capacity_ratio = float(work["heat_capacity_ratio_k"])
                efficiency_fraction = float(work["efficiency_percent"]) / 100.0
                if pin_abs_mpa <= 0.0 or pout_abs_mpa <= pin_abs_mpa:
                    pending.append({
                        "calculation_id": calc_id,
                        "status": "BLOCKED_PHYSICAL_DIRECTION",
                        "required": "Pout_abs > Pin_abs > 0",
                        "pin_abs_mpa": pin_abs_mpa,
                        "pout_abs_mpa": pout_abs_mpa,
                    })
                    hard_blocked.add(calc_id)
                    unavailable_calculations.add(calc_id)
                    continue
                if heat_capacity_ratio <= 1.0 or not 0.0 < efficiency_fraction <= 1.0:
                    pending.append({
                        "calculation_id": calc_id,
                        "status": "BLOCKED_INVALID_INPUT",
                        "required": "heat_capacity_ratio_k > 1 and 0 < efficiency_percent <= 100",
                    })
                    hard_blocked.add(calc_id)
                    unavailable_calculations.add(calc_id)
                    continue
                pressure_ratio_value = pout_abs_mpa / pin_abs_mpa
                value = (
                    pin_abs_mpa * 1_000_000.0
                    * (float(work["flow_m3_h"]) / 3600.0)
                    * heat_capacity_ratio / (heat_capacity_ratio - 1.0)
                    * (
                        pressure_ratio_value
                        ** ((heat_capacity_ratio - 1.0) / heat_capacity_ratio)
                        - 1.0
                    )
                    / efficiency_fraction
                    / 1000.0
                )
                add_result(
                    calc_id,
                    "Pin_abs*Q*k/(k-1)*(PR^((k-1)/k)-1)/eta",
                    (
                        f"({pin_abs_mpa}*10^6)*({work['flow_m3_h']}/3600)*"
                        f"{heat_capacity_ratio}/({heat_capacity_ratio}-1)*"
                        f"(({pout_abs_mpa}/{pin_abs_mpa})^(({heat_capacity_ratio}-1)/"
                        f"{heat_capacity_ratio})-1)/({work['efficiency_percent']}/100)/1000"
                    ),
                    value,
                    "kW",
                    "shaft_power_kw",
                )
                results[-1]["formula_branch"] = {
                    "flow_basis": "actual_inlet_volumetric_flow",
                    "thermodynamic_branch": "ideal_gas_isentropic_screening",
                    "pressure_basis": "absolute_after_normalization",
                }
            elif calc_id == "compressor_total_power":
                driver_efficiency = float(work["driver_efficiency_percent"]) / 100.0
                auxiliary_fraction = float(work["auxiliary_power_fraction"])
                if not 0.0 < driver_efficiency <= 1.0 or auxiliary_fraction < 0.0:
                    pending.append({
                        "calculation_id": calc_id,
                        "status": "BLOCKED_INVALID_INPUT",
                        "required": "0 < driver_efficiency_percent <= 100 and auxiliary_power_fraction >= 0",
                    })
                    hard_blocked.add(calc_id)
                    unavailable_calculations.add(calc_id)
                    continue
                value = (
                    float(work["shaft_power_kw"])
                    / driver_efficiency
                    * (1.0 + auxiliary_fraction)
                )
                add_result(
                    calc_id,
                    "Pshaft/etaDriver*(1+fAux)",
                    (
                        f"{work['shaft_power_kw']}/({work['driver_efficiency_percent']}/100)"
                        f"*(1+{work['auxiliary_power_fraction']})"
                    ),
                    value,
                    "kW",
                    "total_power_kw",
                )
            elif calc_id == "pipe_required_diameter":
                value = pipe_required_diameter(float(work["flow_m3_h"]), float(work["target_velocity_m_s"]))
                add_result(calc_id, "sqrt(4Q/(3600*pi*v))", f"sqrt(4*{work['flow_m3_h']}/(3600*pi*{work['target_velocity_m_s']}))", value * 1000.0, "mm", "required_inner_diameter_mm")
            elif calc_id == "pipe_standard_dn_selection":
                selected = select_pipe_standard_dn(
                    float(work["required_inner_diameter_mm"]),
                    float(work["selected_wall_thickness_mm"]),
                )
                first_result_index = len(results)
                add_result(
                    calc_id,
                    "first DN where D-2t >= d_required",
                    (
                        f"GB/T 12459-2025 table 2: first(D-2*{work['selected_wall_thickness_mm']}"
                        f">={work['required_inner_diameter_mm']})"
                    ),
                    float(selected["dn"]),
                    "DN",
                    "selected_dn",
                )
                add_result(
                    calc_id,
                    "D = table(DN)",
                    f"D = table(DN{selected['dn']})",
                    float(selected["outer_diameter_mm"]),
                    "mm",
                    "selected_outer_diameter_mm",
                )
                source_record = {
                    "catalog_path": PIPE_STANDARD_DN_OD_PATH.relative_to(PACKAGE_ROOT).as_posix(),
                    "catalog_sha256": hashlib.sha256(PIPE_STANDARD_DN_OD_PATH.read_bytes()).hexdigest().upper(),
                    "standard_id": selected["standard_id"],
                    "standard_version": selected["standard_version"],
                    "source_pdf_sha256": selected["source_pdf_sha256"],
                    "physical_page": selected["physical_page"],
                    "source_table_asset_id": selected["source_table_asset_id"],
                    "source_row_1based": selected["source_row_1based"],
                    "nps": selected["nps"],
                    "available_inner_diameter_mm": selected["available_inner_diameter_mm"],
                    "application_boundary": selected["application_boundary"],
                }
                for index in range(first_result_index, len(results)):
                    results[index]["standard_catalog_record"] = dict(source_record)
            elif calc_id == "pipe_actual_velocity":
                value = pipe_actual_velocity(float(work["flow_m3_h"]), float(work["selected_outer_diameter_mm"]) / 1000.0, float(work["selected_wall_thickness_mm"]) / 1000.0)
                add_result(calc_id, "4Q/(3600*pi*(Do-2t)^2)", f"4*{work['flow_m3_h']}/(3600*pi*({work['selected_outer_diameter_mm']}/1000-2*{work['selected_wall_thickness_mm']}/1000)^2)", value, "m/s", "actual_velocity_m_s")
            elif calc_id == "design_pressure_basis_conversion":
                source_design_pressure = float(work["design_pressure_mpa"])
                atmospheric_pressure = float(work["atmospheric_pressure_mpa"])
                value = source_design_pressure - atmospheric_pressure
                if value <= 0:
                    pending.append({
                        "calculation_id": calc_id,
                        "status": "BLOCKED_EXTERNAL_PRESSURE_BRANCH_REQUIRED",
                        "required": "separate vacuum/external-pressure design branch",
                        "design_pressure_input_mpa": source_design_pressure,
                        "design_pressure_input_basis": "absolute",
                        "atmospheric_pressure_mpa": atmospheric_pressure,
                        "design_pressure_gauge_mpa": value,
                    })
                    hard_blocked.add(calc_id)
                    unavailable_calculations.add(calc_id)
                    # The direct design-pressure value is authoritative for
                    # this run.  A separate operating-pressure screening
                    # formula must not bypass a failed absolute-to-gauge
                    # conversion or feed an internal-pressure thickness path.
                    hard_blocked.add("design_pressure")
                    unavailable_calculations.add("design_pressure")
                    continue
                comparison_params["design_pressure_mpa"] = value
                comparison_params["design_pressure_basis"] = "gauge"
                add_result(
                    calc_id,
                    "Pdesign_abs-Patm",
                    f"{source_design_pressure}-{atmospheric_pressure}",
                    value,
                    "MPa(g)",
                    "design_pressure_mpa",
                )
                work["design_pressure_basis"] = "gauge"
                derived["design_pressure_basis"] = "gauge"
                results[-1]["pressure_basis_conversion"] = {
                    "input_basis": "absolute",
                    "output_basis": "gauge",
                    "input_design_pressure_mpa": source_design_pressure,
                    "atmospheric_pressure_mpa": atmospheric_pressure,
                }
            elif calc_id == "design_pressure":
                pressure_basis = str(work["pressure_basis"]).strip().lower()
                operating_pressure = float(work["operating_pressure_mpa"])
                if pressure_basis == "absolute":
                    atmospheric_pressure = float(work["atmospheric_pressure_mpa"])
                    operating_gauge_pressure = operating_pressure - atmospheric_pressure
                    formula = "(Poperating_abs-Patm)*k"
                    substitution = (
                        f"({work['operating_pressure_mpa']}-{work['atmospheric_pressure_mpa']})"
                        f"*{work['design_pressure_factor']}"
                    )
                else:
                    atmospheric_pressure = None
                    operating_gauge_pressure = operating_pressure
                    formula = "Poperating_g*k"
                    substitution = f"{work['operating_pressure_mpa']}*{work['design_pressure_factor']}"
                if operating_gauge_pressure <= 0:
                    pending.append({
                        "calculation_id": calc_id,
                        "status": "BLOCKED_EXTERNAL_PRESSURE_BRANCH_REQUIRED",
                        "required": "separate vacuum/external-pressure design branch",
                        "operating_pressure_mpa": work["operating_pressure_mpa"],
                        "pressure_basis": pressure_basis,
                        "atmospheric_pressure_mpa": atmospheric_pressure,
                        "operating_gauge_pressure_mpa": operating_gauge_pressure,
                    })
                    hard_blocked.add(calc_id)
                    unavailable_calculations.add(calc_id)
                    continue
                value = design_pressure(operating_gauge_pressure, float(work["design_pressure_factor"]))
                add_result(calc_id, formula, substitution, value, "MPa(g)", "design_pressure_mpa")
                if results[-1].get("adopted_as_canonical", True):
                    work["design_pressure_basis"] = "gauge"
                    derived["design_pressure_basis"] = "gauge"
                results[-1]["pressure_basis_conversion"] = {
                    "input_basis": pressure_basis,
                    "output_basis": "gauge",
                    "atmospheric_pressure_mpa": atmospheric_pressure,
                    "operating_gauge_pressure_mpa": operating_gauge_pressure,
                }
            elif calc_id == "cylinder_thickness":
                denominator = 2 * float(work["allowable_stress_mpa"]) * float(work["weld_efficiency"]) - float(work["design_pressure_mpa"])
                if denominator <= 0:
                    pending.append({"calculation_id": calc_id, "status": "BLOCKED_NONPOSITIVE_DENOMINATOR", "denominator": denominator})
                    hard_blocked.add(calc_id)
                    unavailable_calculations.add(calc_id)
                    continue
                value = cylinder_calc_thickness(float(work["design_pressure_mpa"]), float(work["inner_diameter_mm"]), float(work["allowable_stress_mpa"]), float(work["weld_efficiency"]))
                add_result(calc_id, "P*Di/(2*[sigma]*phi-P)", f"{work['design_pressure_mpa']}*{work['inner_diameter_mm']}/(2*{work['allowable_stress_mpa']}*{work['weld_efficiency']}-{work['design_pressure_mpa']})", value, "mm", "cylinder_calculated_thickness_mm")
            elif calc_id == "head_thickness":
                denominator = 2 * float(work["allowable_stress_mpa"]) * float(work["weld_efficiency"]) - 0.5 * float(work["design_pressure_mpa"])
                if denominator <= 0:
                    pending.append({"calculation_id": calc_id, "status": "BLOCKED_NONPOSITIVE_DENOMINATOR", "denominator": denominator})
                    hard_blocked.add(calc_id)
                    unavailable_calculations.add(calc_id)
                    continue
                value = ellipsoidal_head_calc_thickness(float(work["design_pressure_mpa"]), float(work["inner_diameter_mm"]), float(work["allowable_stress_mpa"]), float(work["weld_efficiency"]))
                add_result(calc_id, "P*Di/(2*[sigma]*phi-0.5P)", f"{work['design_pressure_mpa']}*{work['inner_diameter_mm']}/(2*{work['allowable_stress_mpa']}*{work['weld_efficiency']}-0.5*{work['design_pressure_mpa']})", value, "mm", "head_calculated_thickness_mm")
                results[-1]["formula_branch"] = {"head_type": "2:1_ellipsoidal", "status": "EXPLICITLY_SELECTED"}
            elif calc_id == "tower_preliminary_diameter":
                raw_diameter_m = math.sqrt(
                    4.0 * (float(work["flow_m3_h"]) / 3600.0)
                    / (math.pi * float(work["tower_design_velocity_m_s"]))
                )
                # A tower body is a fabricated equipment item; round upward to
                # a stable 100 mm preliminary series and retain at least 600 mm.
                # Keep the formula and substitution labels on that same 100 mm
                # basis; the packaged regression asserts both strings.
                value = max(600.0, math.ceil(raw_diameter_m * 1000.0 / 100.0) * 100.0)
                add_result(
                    calc_id,
                    "ceil_100mm(sqrt(4Q/(3600*pi*uDesign)))",
                    f"ceil_100mm(sqrt(4*{work['flow_m3_h']}/(3600*pi*{work['tower_design_velocity_m_s']})))",
                    value,
                    "mm",
                    "inner_diameter_mm",
                )
                results[-1]["unrounded_diameter_mm"] = raw_diameter_m * 1000.0
            elif calc_id == "tower_tray_spacing":
                diameter = float(work["inner_diameter_mm"])
                if diameter <= 700.0:
                    value = 450.0
                    candidates = [300.0, 350.0, 450.0]
                elif diameter <= 1000.0:
                    value = 450.0
                    candidates = [350.0, 450.0, 500.0, 600.0]
                elif diameter <= 1400.0:
                    value = 500.0
                    candidates = [350.0, 450.0, 500.0, 600.0, 800.0]
                elif diameter <= 3000.0:
                    value = 600.0
                    candidates = [450.0, 500.0, 600.0, 800.0]
                else:
                    value = 800.0
                    candidates = [600.0, 800.0]
                add_result(
                    calc_id,
                    "HT=series(Di)",
                    f"series({diameter:g} mm)->{value:g} mm",
                    value,
                    "mm",
                    "tray_spacing_mm",
                )
                results[-1]["candidate_series_mm"] = candidates
                results[-1]["outside_documented_series"] = diameter < 600.0 or diameter > 4200.0
            elif calc_id == "tower_cross_section":
                value = math.pi * (float(work["inner_diameter_mm"]) / 1000.0) ** 2 / 4.0
                add_result(calc_id, "pi*Di^2/4", f"pi*({work['inner_diameter_mm']}/1000)^2/4", value, "m2", "tower_cross_section_m2")
            elif calc_id == "tower_active_area_fraction":
                value = 1.0 - (
                    float(work["tower_downcomer_area_fraction"])
                    + float(work["tower_receiving_area_fraction"])
                    + float(work["tower_inactive_area_fraction"])
                )
                if value <= 0.0 or value >= 1.0:
                    pending.append({
                        "calculation_id": calc_id,
                        "status": "BLOCKED_INVALID_AREA_CLOSURE",
                        "active_area_fraction": value,
                        "required": "0 < 1-phiDowncomer-phiReceiving-phiInactive < 1",
                    })
                    hard_blocked.add(calc_id)
                    unavailable_calculations.add(calc_id)
                    continue
                add_result(
                    calc_id,
                    "1-phiD-phiR-phiI",
                    f"1-{work['tower_downcomer_area_fraction']}-{work['tower_receiving_area_fraction']}-{work['tower_inactive_area_fraction']}",
                    value,
                    "-",
                    "tower_active_area_fraction",
                )
            elif calc_id == "tower_active_area":
                value = float(work["tower_cross_section_m2"]) * float(work["tower_active_area_fraction"])
                add_result(
                    calc_id,
                    "AT,total*phiA",
                    f"{work['tower_cross_section_m2']}*{work['tower_active_area_fraction']}",
                    value,
                    "m2",
                    "tower_active_area_m2",
                )
            elif calc_id == "tower_hole_area":
                value = float(work["tower_active_area_m2"]) * float(work["tower_open_area_fraction"])
                add_result(
                    calc_id,
                    "Aa*phiO",
                    f"{work['tower_active_area_m2']}*{work['tower_open_area_fraction']}",
                    value,
                    "m2",
                    "tower_hole_area_m2",
                )
            elif calc_id == "tower_actual_superficial_velocity":
                value = (float(work["flow_m3_h"]) / 3600.0) / float(work["tower_active_area_m2"])
                add_result(
                    calc_id,
                    "Q/(3600*Aa)",
                    f"{work['flow_m3_h']}/(3600*{work['tower_active_area_m2']})",
                    value,
                    "m/s",
                    "tower_actual_superficial_velocity_m_s",
                )
            elif calc_id == "tower_internal_height":
                effective_intervals = max(float(work["stage_count"]) - 1.0, 1.0)
                value = effective_intervals * float(work["tray_spacing_mm"]) / 1000.0
                add_result(
                    calc_id,
                    "max(N-1,1)*HT/1000",
                    f"max({work['stage_count']}-1,1)*{work['tray_spacing_mm']}/1000",
                    value,
                    "m",
                    "tower_internal_height_m",
                )
            elif calc_id == "tower_preliminary_height":
                effective_intervals = max(float(work["stage_count"]) - 1.0, 1.0)
                value = effective_intervals * float(work["tray_spacing_mm"]) + float(work["tower_top_bottom_allowance_mm"])
                add_result(
                    calc_id,
                    "max(N-1,1)*HT+Hallow",
                    f"max({work['stage_count']}-1,1)*{work['tray_spacing_mm']}+{work['tower_top_bottom_allowance_mm']}",
                    value,
                    "mm",
                    "height_mm",
                )
            elif calc_id == "tower_bottom_liquid_height":
                value = tower_bottom_liquid_height(float(work["flow_m3_h"]), float(work["retention_time_min"]), float(work["inner_diameter_mm"]) / 1000.0)
                add_result(calc_id, "Q*t/(60*pi*Di^2/4)", f"{work['flow_m3_h']}*{work['retention_time_min']}/(60*pi*({work['inner_diameter_mm']}/1000)^2/4)", value, "m", "bottom_liquid_height_m")
            elif calc_id == "cylinder_volume":
                value = (
                    math.pi
                    * (float(work["inner_diameter_mm"]) / 1000.0) ** 2
                    / 4.0
                    * (float(work["straight_shell_length_mm"]) / 1000.0)
                )
                add_result(
                    calc_id,
                    "pi*Di^2*Lstraight/4",
                    (
                        f"pi*({work['inner_diameter_mm']}/1000)^2*"
                        f"({work['straight_shell_length_mm']}/1000)/4"
                    ),
                    value,
                    "m3",
                    "straight_shell_geometric_volume_m3",
                )
            elif calc_id == "storage_required_volume":
                value = (
                    float(work["flow_m3_h"])
                    * float(work["retention_time_min"])
                    / 60.0
                    / float(work["fill_fraction"])
                )
                add_result(
                    calc_id,
                    "Q*t/(60*fill_fraction)",
                    f"{work['flow_m3_h']}*{work['retention_time_min']}/(60*{work['fill_fraction']})",
                    value,
                    "m3",
                    "required_volume_m3",
                )
            elif calc_id == "membrane_area":
                value = membrane_area_m2(float(work["channel_count"]), float(work["channel_inner_diameter_mm"]), float(work["element_length_m"]), float(work["element_count"]))
                add_result(calc_id, "Ne*Nc*pi*di*L", f"{work['element_count']}*{work['channel_count']}*pi*({work['channel_inner_diameter_mm']}/1000)*{work['element_length_m']}", value, "m2", "membrane_area_m2")
                results[-1]["formula_branch"] = {
                    "membrane_geometry_type": "cylindrical_channels",
                    "status": "EXPLICITLY_SELECTED",
                }
            elif calc_id == "heater_sensible_duty_screening":
                value = (
                    float(work["mass_flow_kg_h"])
                    * float(work["specific_heat_kj_kgk"])
                    * (
                        float(work["outlet_temperature_c"])
                        - float(work["inlet_temperature_c"])
                    )
                    / 3600.0
                )
                add_result(
                    calc_id,
                    "m*Cp*(Tout-Tin)/3600",
                    (
                        f"{work['mass_flow_kg_h']}*{work['specific_heat_kj_kgk']}*"
                        f"({work['outlet_temperature_c']}-{work['inlet_temperature_c']})/3600"
                    ),
                    value,
                    "kW",
                    "heat_duty_kw",
                )
                results[-1]["formula_branch"] = {
                    "branch": "sensible_heat_screening",
                    "phase": canonical_phase(work.get("phase")) or "unknown",
                    "specific_heat_source": "supplied_or_registered_visible_fallback",
                    "latent_or_reaction_heat_included": False,
                }
            elif calc_id == "exchanger_area":
                value = abs(float(work["heat_duty_kw"])) * 1000.0 / (
                    float(work["overall_u_w_m2k"])
                    * float(work["lmtd_correction_factor"])
                    * float(work["lmtd_k"])
                )
                add_result(
                    calc_id,
                    "abs(Q)/(U*F*LMTD)",
                    f"abs({work['heat_duty_kw']})*1000/({work['overall_u_w_m2k']}*{work['lmtd_correction_factor']}*{work['lmtd_k']})",
                    value,
                    "m2",
                    "heat_transfer_area_m2",
                )
            elif calc_id == "exchanger_tube_count":
                value = math.ceil(
                    float(work["heat_transfer_area_m2"])
                    / (
                        math.pi
                        * (float(work["tube_outer_diameter_mm"]) / 1000.0)
                        * (float(work["tube_length_mm"]) / 1000.0)
                    )
                )
                add_result(
                    calc_id,
                    "ceil(A/(pi*do*L))",
                    (
                        f"ceil({work['heat_transfer_area_m2']}/"
                        f"(pi*{work['tube_outer_diameter_mm']}/1000*{work['tube_length_mm']}/1000))"
                    ),
                    float(value),
                    "count",
                    "tube_or_plate_count",
                )
        except (ValueError, ZeroDivisionError, OverflowError) as exc:
            pending.append({"calculation_id": calc_id, "status": "BLOCKED_INVALID_INPUT", "error": str(exc)})
            hard_blocked.add(calc_id)
            unavailable_calculations.add(calc_id)
    return results, pending, derived


def assess_pump_npsh_constraint(params: dict[str, Any]) -> dict[str, Any]:
    """Evaluate the NPSH constraint without turning a failed duty into bad input."""
    required_fields = ["npsha_m", "npshr_m", "required_npsh_margin_m"]
    same_case_evidence_fields = [
        "npshr_evidence_scope", "vendor_curve_path", "vendor_curve_sha256",
        "evidence_manifest_path", "evidence_manifest_sha256",
        "audit_approval_path", "audit_approval_sha256",
        "verification_result", "approval_status",
    ]
    missing = [field for field in required_fields if not present(params, field)]
    evidence_missing = [field for field in same_case_evidence_fields if not present(params, field)]
    base: dict[str, Any] = {
        "criterion": "NPSHa >= NPSHr + required_npsh_margin_m",
        "required_fields": required_fields,
        "same_case_evidence_fields": same_case_evidence_fields,
        "missing_fields": missing,
        "evidence_missing_fields": evidence_missing,
        "does_not_prove": ["vendor_curve_fit", "BEP_proximity", "final_pump_selection"],
    }
    if not present(params, "npsha_m") or not present(params, "npshr_m"):
        return {**base, "status": "UNKNOWN", "evaluation": "NOT_EVALUATED_MISSING_NPSH_VALUES"}

    observed_margin = float(params["npsha_m"]) - float(params["npshr_m"])
    base.update({
        "npsha_m": float(params["npsha_m"]),
        "npshr_m": float(params["npshr_m"]),
        "observed_margin_m": observed_margin,
        "difference_evidence_class": "D",
    })
    if not present(params, "required_npsh_margin_m"):
        return {
            **base,
            "status": "UNKNOWN",
            "evaluation": "SCREENING_ONLY_REQUIRED_MARGIN_NOT_SUPPLIED",
        }

    required_margin = float(params["required_npsh_margin_m"])
    base["required_margin_m"] = required_margin
    if observed_margin < required_margin:
        return {
            **base,
            "status": "FAIL",
            "numeric_status": "FAIL",
            "evaluation": "INSUFFICIENT_AGAINST_EXPLICIT_REQUIRED_MARGIN",
        }

    same_case_scope = params.get("npshr_evidence_scope") == "same_duty_vendor_curve"
    manifest, manifest_blockers = audit_evidence_manifest(
        params,
        "family_pump",
        ["NPSHa_NPSHr"],
        ["vendor_curve_sha256", "verification_result"],
    )
    required_gate_references = {
        "vendor_curve", "parameter:npsha_m", "parameter:npshr_m",
        "parameter:required_npsh_margin_m", "parameter:npshr_evidence_scope",
    }
    actual_gate_references = set()
    if isinstance(manifest, dict):
        references = manifest.get("gate_evidence", {}).get("NPSHa_NPSHr", [])
        if isinstance(references, list):
            actual_gate_references = {str(item) for item in references}
    missing_gate_references = sorted(required_gate_references - actual_gate_references)
    approval_blockers = audit_final_approval(
        params,
        "family_pump",
        ["NPSHa_NPSHr"],
        manifest,
    )
    evidence_blockers = sorted(set([
        *manifest_blockers,
        *approval_blockers,
        *(f"npsh_gate_reference_missing:{item}" for item in missing_gate_references),
    ]))
    evidence_complete = same_case_scope and not evidence_missing and not evidence_blockers
    base.update({
        "npshr_evidence_scope": params.get("npshr_evidence_scope"),
        "numeric_status": "PASS",
        "same_case_evidence_complete": evidence_complete,
        "evidence_blockers": evidence_blockers,
    })
    if not evidence_complete:
        return {
            **base,
            "status": "UNKNOWN",
            "evaluation": "NUMERIC_MARGIN_SUFFICIENT_BUT_MACHINE_AUDITED_SAME_DUTY_EVIDENCE_OPEN",
        }
    return {
        **base,
        "status": "PASS",
        "evaluation": "EXPLICIT_MARGIN_AND_MACHINE_AUDITED_SAME_DUTY_VENDOR_CURVE_CLOSED",
        "constraint_evidence_class": "R+D",
    }


def assess_compressor_surge_constraint(params: dict[str, Any]) -> dict[str, Any]:
    """Evaluate observed compressor surge margin as a constraint, not input validity."""

    required_fields = ["surge_margin_percent", "required_surge_margin_percent"]
    same_case_evidence_fields = [
        "surge_margin_evidence_scope", "vendor_curve_path", "vendor_curve_sha256",
        "evidence_manifest_path", "evidence_manifest_sha256",
        "audit_approval_path", "audit_approval_sha256",
        "verification_result", "approval_status",
    ]
    missing = [field for field in required_fields if not present(params, field)]
    evidence_missing = [field for field in same_case_evidence_fields if not present(params, field)]
    base: dict[str, Any] = {
        "criterion": "surge_margin_percent >= required_surge_margin_percent",
        "required_fields": required_fields,
        "same_case_evidence_fields": same_case_evidence_fields,
        "missing_fields": missing,
        "evidence_missing_fields": evidence_missing,
        "does_not_prove": ["choke_margin", "full_operating_envelope", "anti_surge_control", "final_compressor_selection"],
    }
    if not present(params, "surge_margin_percent"):
        return {**base, "status": "UNKNOWN", "evaluation": "NOT_EVALUATED_MISSING_OBSERVED_SURGE_MARGIN"}

    observed_margin = float(params["surge_margin_percent"])
    base.update({
        "observed_margin_percent": observed_margin,
        "observed_margin_evidence_class": "D_OR_R_PENDING_PROVENANCE",
    })
    if not present(params, "required_surge_margin_percent"):
        return {
            **base,
            "status": "UNKNOWN",
            "evaluation": "SCREENING_ONLY_REQUIRED_SURGE_MARGIN_NOT_SUPPLIED",
        }

    required_margin = float(params["required_surge_margin_percent"])
    base["required_margin_percent"] = required_margin
    if observed_margin < required_margin:
        return {
            **base,
            "status": "FAIL",
            "numeric_status": "FAIL",
            "evaluation": "INSUFFICIENT_AGAINST_EXPLICIT_REQUIRED_SURGE_MARGIN",
        }

    same_case_scope = params.get("surge_margin_evidence_scope") == "same_duty_performance_map"
    manifest, manifest_blockers = audit_evidence_manifest(
        params,
        "family_compressor",
        ["surge_choke_margin"],
        ["vendor_curve_sha256", "verification_result"],
    )
    required_gate_references = {
        "vendor_curve", "parameter:surge_margin_percent",
        "parameter:required_surge_margin_percent", "parameter:surge_margin_evidence_scope",
    }
    actual_gate_references: set[str] = set()
    if isinstance(manifest, dict):
        references = manifest.get("gate_evidence", {}).get("surge_choke_margin", [])
        if isinstance(references, list):
            actual_gate_references = {str(item) for item in references}
    missing_gate_references = sorted(required_gate_references - actual_gate_references)
    approval_blockers = audit_final_approval(
        params,
        "family_compressor",
        ["surge_choke_margin"],
        manifest,
    )
    evidence_blockers = sorted(set([
        *manifest_blockers,
        *approval_blockers,
        *(f"surge_gate_reference_missing:{item}" for item in missing_gate_references),
    ]))
    evidence_complete = same_case_scope and not evidence_missing and not evidence_blockers
    base.update({
        "surge_margin_evidence_scope": params.get("surge_margin_evidence_scope"),
        "numeric_status": "PASS",
        "same_case_evidence_complete": evidence_complete,
        "evidence_blockers": evidence_blockers,
    })
    if not evidence_complete:
        return {
            **base,
            "status": "UNKNOWN",
            "evaluation": "NUMERIC_MARGIN_SUFFICIENT_BUT_MACHINE_AUDITED_SAME_DUTY_MAP_OPEN",
        }
    return {
        **base,
        "status": "PASS",
        "evaluation": "EXPLICIT_MARGIN_AND_MACHINE_AUDITED_SAME_DUTY_PERFORMANCE_MAP_CLOSED",
        "constraint_evidence_class": "R+D",
    }


def assess_storage_volume_constraint(params: dict[str, Any]) -> dict[str, Any]:
    """Compare required total inventory volume with an explicitly selected total volume."""

    required_fields = ["required_volume_m3", "volume_m3", "volume_basis"]
    missing = [field for field in required_fields if not present(params, field)]
    base: dict[str, Any] = {
        "criterion": "selected volume and required volume compared on one explicit basis",
        "required_fields": required_fields,
        "missing_fields": missing,
        "does_not_prove": ["surge_allowance", "dynamic_inventory", "relief_pass", "mechanical_design"],
    }
    if missing:
        return {**base, "status": "UNKNOWN", "evaluation": "NOT_EVALUATED_MISSING_VOLUME_BASIS"}
    selected = float(params["volume_m3"])
    required_total = float(params["required_volume_m3"])
    basis = str(params["volume_basis"])
    if basis in {"nominal_total", "geometric_total"}:
        required = required_total
        comparison_basis = "total_volume"
    elif basis == "effective_working":
        if not present(params, "fill_fraction"):
            return {
                **base,
                "status": "UNKNOWN",
                "evaluation": "WORKING_VOLUME_COMPARISON_REQUIRES_FILL_FRACTION",
                "provided_volume_basis": basis,
                "missing_fields": ["fill_fraction"],
            }
        required = required_total * float(params["fill_fraction"])
        comparison_basis = "effective_working_volume"
    else:
        return {
            **base,
            "status": "UNKNOWN",
            "evaluation": "UNSUPPORTED_VOLUME_COMPARISON_BASIS",
            "provided_volume_basis": basis,
        }
    margin = selected - required
    tolerance = max(1.0, abs(required)) * 1e-9
    result = {
        **base,
        "provided_volume_basis": basis,
        "comparison_basis": comparison_basis,
        "selected_volume_m3": selected,
        "required_volume_m3_on_comparison_basis": required,
        "required_total_volume_m3": required_total,
        "volume_margin_m3": margin,
        "comparison_tolerance_m3": tolerance,
        "constraint_evidence_class": "D",
    }
    if comparison_basis == "total_volume":
        result["selected_total_volume_m3"] = selected
    else:
        result["selected_effective_working_volume_m3"] = selected
        result["required_effective_working_volume_m3"] = required
    if margin < -tolerance:
        return {**result, "status": "FAIL", "evaluation": "SELECTED_VOLUME_BELOW_REQUIRED_ON_COMMON_BASIS"}
    return {**result, "status": "PASS", "evaluation": "SELECTED_VOLUME_MEETS_REQUIRED_ON_COMMON_BASIS"}


FIELD_SYMBOLS: dict[str, str] = {
    "process_function": "service",
    "flow_m3_h": "Q",
    "head_m": "H",
    "density_kg_m3": "rho",
    "efficiency_percent": "eta",
    "inlet_pressure_mpa": "Pin",
    "outlet_pressure_mpa": "Pout",
    "operating_pressure_mpa": "Pop",
    "design_pressure_mpa": "Pdes",
    "design_pressure_basis": "basis_Pdes",
    "pressure_drop_kpa": "dP",
    "allowable_pressure_drop_kpa": "dP_allow",
    "maximum_pressure_drop_kpa": "dP_max",
    "maximum_pressure_drop_factor": "kMax",
    "temperature_c": "T",
    "inlet_temperature_c": "Tin",
    "outlet_temperature_c": "Tout",
    "design_temperature_c": "Tdes",
    "heat_duty_kw": "duty",
    "specific_heat_kj_kgk": "Cp",
    "heat_transfer_area_m2": "A",
    "diameter_mm": "DN_body",
    "height_mm": "H_body",
    "inner_diameter_mm": "Di",
    "straight_shell_length_mm": "Lstraight",
    "volume_m3": "V",
    "volume_basis": "basis_V",
    "required_volume_m3": "Vreq",
    "straight_shell_geometric_volume_m3": "Vstraight",
    "stage_count": "N_stage",
    "rotational_speed_rpm": "n",
    "shaft_power_kw": "Pshaft",
    "pressure_drop_power_component_kw": "P_deltaP",
    "pressure_component_shaft_power_screening_kw": "Pscreen_deltaP",
    "pressure_drop_head_component_m": "H_deltaP",
    "selected_dn": "DN",
    "selected_outer_diameter_mm": "OD",
    "selected_wall_thickness_mm": "t",
    "pressure_class": "PN/Class",
}


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()


def build_design_parameter_package(
    family_id: str,
    normalized: dict[str, Any],
    derived: dict[str, Any],
    rule: dict[str, Any],
    calculations: list[dict[str, Any]],
    pending: list[dict[str, Any]],
    fallback_ledger: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the mandatory calculate-first intermediate object used by selection.

    The package is deliberately presentation-ready and machine-readable.  It
    does not certify the provenance of a caller-provided value; it records that
    distinction explicitly so a UI cannot color all present values as verified.
    """
    templates = load_parameter_templates()
    family_template = next(
        (item for item in templates.get("families", []) if item.get("family_id") == family_id),
        None,
    )
    model_rules = load_model_rules()
    model_rule = next(
        (item for item in model_rules.get("families", []) if item.get("family_id") == family_id),
        {},
    )
    if family_template is None:
        return {
            "schema": "equipment-design-parameter-package-v1",
            "status": "BLOCKED_PARAMETER_TEMPLATE_MISSING",
            "family_id": family_id,
            "groups": [],
            "selection_feature_vector": {"status": "BLOCKED", "values": {}},
        }

    effective = {**normalized, **derived}
    block_type = str(effective.get("aspen_block_type") or "").strip().upper()
    block_overlay = dict(templates.get("block_type_overlays", {}).get(block_type, {}))
    configured_calculation_ids = list(rule.get("calculation_rules", []))
    configured_calculation_ids.extend(BLOCK_TYPE_CALCULATION_RULES.get(block_type, ()))
    configured_calculation_ids = list(dict.fromkeys(str(item) for item in configured_calculation_ids))
    definitions = templates.get("parameter_definitions", {})
    fallback_ledger = list(fallback_ledger or [])
    fallback_by_field = {
        str(item.get("field_id")): dict(item)
        for item in fallback_ledger
        if item.get("field_id")
    }
    completed_by_target = {
        str(item.get("target_field")): item
        for item in calculations
        if item.get("target_field") and item.get("adopted_as_canonical", True)
    }
    pending_by_id = {str(item.get("calculation_id")): item for item in pending}
    calculation_dependencies: dict[str, list[str]] = {}
    for calc_id in configured_calculation_ids:
        for field in CALCULATION_REQUIREMENTS.get(calc_id, ()):
            calculation_dependencies.setdefault(field, []).append(calc_id)

    phase_gate = family_phase_compatibility(family_id, effective)
    selection_required = list(model_rule.get("candidate_required_fields", []))
    if "design_pressure_mpa" in selection_required and "design_pressure_basis" not in selection_required:
        selection_required.append("design_pressure_basis")
    if (
        "design_pressure_mpa" in selection_required
        and effective.get("design_pressure_basis") == "absolute"
        and "atmospheric_pressure_mpa" not in selection_required
    ):
        selection_required.append("atmospheric_pressure_mpa")
    if "volume_m3" in selection_required and "volume_basis" not in selection_required:
        selection_required.append("volume_basis")
    if family_id in PHASE_COMPATIBILITY and "phase" not in selection_required:
        selection_required.append("phase")
    sizing_required = list(rule.get("sizing_fields", []))

    def row_for(field: str, group_id: str, group_title: str) -> dict[str, Any]:
        meta = definitions.get(field, {})
        calc = completed_by_target.get(field)
        required_for: list[str] = []
        if field in sizing_required:
            required_for.append("sizing")
        if field in selection_required:
            required_for.append("candidate_matching")
        if group_id == "customer_delivery":
            required_for.append("customer_authoritative_overview")
        required_for.extend(f"calculation:{calc_id}" for calc_id in calculation_dependencies.get(field, []))
        if field in derived:
            state = "CALCULATED"
            notice = calc.get("calculation_notice", {}) if calc else {}
            release_class = str(notice.get("release_class", "A"))
            source = {
                "kind": (
                    "provisional_screening_calculation"
                    if release_class == "B"
                    else "deterministic_calculation"
                ),
                "evidence_class": notice.get("evidence_class", "D"),
                "formula_release_class": release_class,
                "result_status": notice.get("result_status", "DERIVED"),
                "calculation_id": calc.get("calculation_id") if calc else None,
                "source_verified": False,
            }
            value = derived[field]
        elif present(normalized, field):
            fallback = fallback_by_field.get(field)
            if fallback:
                state = str(fallback.get("state", "DEFAULTED"))
                source = {
                    "kind": fallback.get("source_kind", "registered_final_fallback_default"),
                    "evidence_class": fallback.get("evidence_class", "J"),
                    "source_verified": False,
                    "fallback_tier": fallback.get("tier"),
                    "promotion_cap": "TYPE_SCREENING",
                    "warning": fallback.get("warning"),
                    "basis": fallback.get("basis", []),
                }
            else:
                state = "PROVIDED"
                source = {
                    "kind": "normalized_input",
                    "evidence_class": "U",
                    "source_verified": False,
                }
            value = normalized[field]
        else:
            explicit_gate = meta.get("evidence_gate") or meta.get("closure_gate") or meta.get("source_gate")
            external_only = str(meta.get("source_class", meta.get("source_kind", ""))).casefold() in {
                "software", "vendor", "external", "same_equipment_evidence",
            }
            state = "EXTERNAL_REQUIRED" if group_id == "evidence" or explicit_gate or external_only else "MISSING"
            source = {
                "kind": "same_equipment_evidence_required" if state == "EXTERNAL_REQUIRED" else "not_available",
                "evidence_class": "U",
                "source_verified": False,
                "evidence_gate": explicit_gate,
            }
            value = None
        row_symbol = meta.get("symbol", FIELD_SYMBOLS.get(field, field))
        row_unit = (
            calc.get("unit")
            if calc and state == "CALCULATED" and calc.get("unit")
            else meta.get("unit", FIELD_UNITS.get(field))
        )
        if field == "design_pressure_mpa":
            design_basis = effective.get("design_pressure_basis")
            if design_basis == "absolute":
                row_symbol = "Pdes,abs"
                row_unit = "MPa(abs)"
            elif design_basis == "gauge":
                row_symbol = "Pdes,g"
                row_unit = "MPa(g)"
            else:
                row_symbol = "Pdes"
                row_unit = "MPa"
        return {
            "group_id": group_id,
            "group_title": group_title,
            "field_id": field,
            "label": meta.get("label", field.replace("_", " ")),
            "symbol": row_symbol,
            "raw_value": value,
            "display_value": _display_value(value) if value is not None else "—",
            "unit": row_unit,
            "role": (
                "selection_feature" if group_id == "selection"
                else "customer_delivery" if group_id == "customer_delivery"
                else "derived" if state == "CALCULATED"
                else "input"
            ),
            "state": state,
            "source": source,
            "required_for": sorted(set(required_for)),
            "equation_chain": (
                calc.get("equation_chain") if calc
                else fallback_by_field.get(field, {}).get("equation_chain")
            ),
            "formula_chain": calc.get("formula_chain") if calc else None,
            "calculation_notice": (
                calc.get("calculation_notice") if calc
                else ({
                    "code": (
                        "LLM_PROVISIONAL_ENGINEERING_ESTIMATE"
                        if fallback_by_field.get(field, {}).get("source_kind") == "llm_last_resort_engineering_estimate"
                        else "REGISTERED_DESIGN_FALLBACK"
                    ),
                    "severity": "warning",
                    "evidence_class": "J",
                    "result_status": "PROVISIONAL",
                    "promotion_cap": "TYPE_SCREENING",
                    "title": (
                        "大模型末级工程估算（仅初步选型）"
                        if fallback_by_field.get(field, {}).get("source_kind") == "llm_last_resort_engineering_estimate"
                        else "登记的预设计保底值"
                    ),
                    "message": fallback_by_field.get(field, {}).get("warning"),
                    "fallback_tier": fallback_by_field.get(field, {}).get("tier"),
                    "confidence": fallback_by_field.get(field, {}).get("confidence"),
                    "lower_bound": fallback_by_field.get(field, {}).get("lower_bound"),
                    "upper_bound": fallback_by_field.get(field, {}).get("upper_bound"),
                    "sensitivity_note": fallback_by_field.get(field, {}).get("sensitivity_note"),
                } if field in fallback_by_field else None)
            ),
        }

    groups: list[dict[str, Any]] = []
    all_rows: list[dict[str, Any]] = []
    layout_fields: set[str] = set()
    layout_groups = [*family_template.get("groups", []), *block_overlay.get("groups", [])]
    for group in layout_groups:
        group_id = str(group.get("id", "parameters"))
        group_title = str(group.get("title", group_id))
        fields = [str(field) for field in group.get("fields", [])]
        rows = [row_for(field, group_id, group_title) for field in fields]
        layout_fields.update(fields)
        all_rows.extend(rows)
        groups.append({"group_id": group_id, "title": group_title, "rows": rows})

    family_evidence_fields: list[str] = []
    for field in rule.get("verification_fields", []):
        family_evidence_fields.append(field)
        if field in EVIDENCE_PAIRS:
            family_evidence_fields.append(EVIDENCE_PAIRS[field])
    evidence_fields = family_evidence_fields + [
        "formal_calculation_path", "formal_calculation_sha256",
        "evidence_manifest_path", "evidence_manifest_sha256",
        "audit_approval_path", "audit_approval_sha256", "approval_status",
    ]
    evidence_fields = [field for field in dict.fromkeys(evidence_fields) if field not in layout_fields]
    evidence_rows = [row_for(field, "evidence", "同设备证据与批准") for field in evidence_fields]
    all_rows.extend(evidence_rows)
    groups.append({"group_id": "evidence", "title": "同设备证据与批准", "rows": evidence_rows})

    calculation_chain: list[dict[str, Any]] = []
    completed_by_id = {str(item.get("calculation_id")): item for item in calculations}
    # A caller may supply a design pressure directly on an absolute basis.  Its
    # mandatory absolute-to-gauge normalization is injected by run_calculations
    # rather than configured as a family formula, but it still belongs in the
    # visible calculate-first chain before any thickness equation consumes it.
    injected_calculation_ids = [
        calc_id
        for calc_id in ("design_pressure_basis_conversion",)
        if calc_id not in configured_calculation_ids
        and (calc_id in completed_by_id or calc_id in pending_by_id)
    ]
    for calc_id in [*injected_calculation_ids, *configured_calculation_ids]:
        output_field = CALCULATION_OUTPUT_FIELDS.get(calc_id)
        if calc_id in completed_by_id:
            item = completed_by_id[calc_id]
            calculation_chain.append({
                "calculation_id": calc_id,
                "target_field": item.get("target_field"),
                "status": item.get("status", "CALCULATED"),
                "equation_chain": item.get("equation_chain"),
                "formula_chain": item.get("formula_chain"),
                "calculation_notice": item.get("calculation_notice"),
                "provided_target_crosscheck": item.get("provided_target_crosscheck"),
            })
        elif calc_id in pending_by_id:
            item = pending_by_id[calc_id]
            calculation_chain.append({
                "calculation_id": calc_id,
                "target_field": output_field,
                "status": item.get("status", "MISSING_INPUTS"),
                "missing_fields": item.get("missing_fields", []),
                "required": item.get("required"),
            })
        elif output_field and present(normalized, output_field):
            calculation_chain.append({
                "calculation_id": calc_id,
                "target_field": output_field,
                "status": "SATISFIED_BY_PROVIDED_VALUE",
            })
        else:
            calculation_chain.append({
                "calculation_id": calc_id,
                "target_field": output_field,
                "status": "NOT_EXECUTED",
            })

    selection_values = {
        field: effective[field]
        for field in selection_required
        if present(effective, field)
    }
    selection_missing = [field for field in selection_required if not present(effective, field)]
    phase_blocked = phase_gate["status"] == "BLOCKED_INCOMPATIBLE_PHASE"
    phase_special = phase_gate["status"] == "SPECIAL_DUTY_ROUTE_REQUIRED"
    if phase_special:
        selection_required.append("special_duty_route_definition")
        selection_missing.append("special_duty_route_definition")
    selection_context_fields = set(selection_required)
    selection_context_fields.update(model_rule.get("designation_fields", []))
    selection_context_fields.update({
        "equipment_tag", "equipment_type", "aspen_block_type", "process_function",
        "terminal_type_rule_override_id",
        "phase", "pressure_basis", "design_pressure_basis", "atmospheric_pressure_mpa",
        "volume_basis", "candidate_model", "vendor_model",
        "required_npsh_margin_m", "npshr_evidence_scope",
        "required_surge_margin_percent", "surge_margin_evidence_scope",
    })
    selection_context_fields.update(rule.get("verification_fields", []))
    selection_context_fields.update(
        str(field)
        for group in block_overlay.get("groups", [])
        for field in group.get("fields", [])
    )
    selection_context_fields.update(field for field in effective if field.endswith(("_path", "_sha256")))
    selection_context_fields.update({"verification_result", "approval_status"})
    selection_context = {
        field: effective[field]
        for field in sorted(selection_context_fields)
        if present(effective, field)
    }
    fallback_selection_basis = [
        {
            "field_id": item.get("field_id"),
            "value": item.get("value"),
            "tier": item.get("tier"),
            "evidence_class": item.get("evidence_class"),
            "promotion_cap": item.get("promotion_cap"),
        }
        for item in fallback_ledger
        if str(item.get("field_id")) in selection_context_fields
    ]
    hard_pending = [item for item in pending if is_hard_calculation_blocker(item)]
    checks: list[dict[str, Any]] = [
        {
            "check_id": "calculation_hard_blockers",
            "status": "PASS" if not hard_pending else "FAIL",
            "details": hard_pending,
        },
        {
            "check_id": "candidate_feature_completeness",
            "status": "PASS" if not selection_missing else "UNKNOWN",
            "missing_fields": selection_missing,
        },
        {
            "check_id": "family_phase_compatibility",
            "status": (
                "PASS" if phase_gate["status"] == "PASS"
                else "FAIL" if phase_gate["status"] == "BLOCKED_INCOMPATIBLE_PHASE"
                else "UNKNOWN"
            ),
            "details": phase_gate,
        },
    ]
    if family_id == "family_pump":
        checks.append({
            "check_id": "pump_npsh_margin",
            **assess_pump_npsh_constraint(effective),
        })
    if family_id == "family_compressor":
        checks.append({
            "check_id": "compressor_surge_margin",
            **assess_compressor_surge_constraint(effective),
        })
    if family_id == "family_storage_vessel":
        checks.append({
            "check_id": "storage_required_volume",
            **assess_storage_volume_constraint(effective),
        })

    unique_fields = {row["field_id"]: row for row in all_rows}
    counts = {
        "configured": len(unique_fields),
        "provided": sum(1 for row in unique_fields.values() if row["state"] == "PROVIDED"),
        "calculated": sum(1 for row in unique_fields.values() if row["state"] == "CALCULATED"),
        "recommended": sum(1 for row in unique_fields.values() if row["state"] == "RECOMMENDED"),
        "defaulted": sum(1 for row in unique_fields.values() if row["state"] == "DEFAULTED"),
        "missing": sum(1 for row in unique_fields.values() if row["state"] == "MISSING"),
        "external_required": sum(1 for row in unique_fields.values() if row["state"] == "EXTERNAL_REQUIRED"),
    }
    package_status = (
        "BLOCKED_PHYSICAL_PHASE" if phase_blocked
        else "BLOCKED" if hard_pending
        else "READY_FOR_CANDIDATE_MATCHING" if not selection_missing
        else "PARTIAL_PARAMETERS"
    )
    return {
        "schema": "equipment-design-parameter-package-v1",
        "status": package_status,
        "family_id": family_id,
        "title": family_template.get("title", family_id),
        "block_type_overlay": ({
            "block_type": block_type,
            "title": block_overlay.get("title"),
            "evidence_class": block_overlay.get("evidence_class", "J"),
            "promotion_cap": block_overlay.get("promotion_cap", "TYPE_SCREENING"),
            "formal_gate": block_overlay.get("formal_gate"),
        } if block_overlay else None),
        "template_version": templates.get("version"),
        "template_path": PARAMETER_TEMPLATES_PATH.relative_to(PACKAGE_ROOT).as_posix(),
        "template_sha256": hashlib.sha256(PARAMETER_TEMPLATES_PATH.read_bytes()).hexdigest().upper(),
        "customer_output_profile": {
            **templates.get("customer_output_profile", {}),
            "profile_ids": family_template.get("customer_profile_ids", []),
            "sha256": (
                hashlib.sha256(CUSTOMER_OUTPUT_PROFILES_PATH.read_bytes()).hexdigest().upper()
                if CUSTOMER_OUTPUT_PROFILES_PATH.is_file()
                else None
            ),
        },
        "workflow": templates.get("workflow", []),
        "summary": counts,
        "status_axes": {
            "identity": "MATCHED",
            "calculation": (
                "BLOCKED" if hard_pending
                else "PROVISIONAL_FALLBACK" if fallback_ledger
                else "COMPLETE" if not pending
                else "PARTIAL"
            ),
            "candidate_matching": (
                "BLOCKED_INCOMPATIBLE_PHASE" if phase_blocked
                else "WAITING_SPECIAL_DUTY_ROUTE" if phase_special
                else "BLOCKED_CALCULATION" if hard_pending
                else "READY" if not selection_missing
                else "WAITING_PARAMETERS"
            ),
            "formal_delivery": "PENDING_SAME_EQUIPMENT_EVIDENCE",
        },
        "design_basis_status": "PROVISIONAL_FALLBACK" if fallback_ledger else "DIRECT_OR_DERIVED_ONLY",
        "groups": groups,
        "calculation_chain": calculation_chain,
        "calculation_notices": [
            item["calculation_notice"]
            for item in calculation_chain
            if isinstance(item.get("calculation_notice"), dict)
        ],
        "design_fallbacks": fallback_ledger,
        "design_fallbacks_sha256": _canonical_sha256(fallback_ledger),
        "constraint_checks": checks,
        "phase_compatibility": phase_gate,
        "selection_feature_vector": {
            "status": "BLOCKED" if (hard_pending or phase_blocked) else ("READY" if not selection_missing else "INCOMPLETE"),
            "required_fields": selection_required,
            "values": selection_values,
            "missing_fields": selection_missing,
            "sha256": _canonical_sha256({
                "values": selection_values,
                "fallback_basis": fallback_selection_basis,
            }),
            "fallback_basis": fallback_selection_basis,
        },
        "selection_context": {
            "values": selection_context,
            "sha256": _canonical_sha256({
                "values": selection_context,
                "fallback_basis": fallback_selection_basis,
            }),
            "fallback_basis": fallback_selection_basis,
            "source": "calculated_parameter_package_with_explicit_fallback_lineage",
        },
        "visual_template": templates.get("visual_template", {}),
        "deterministic": True,
        "llm_used": False,
    }


PHASE_COMPATIBILITY: dict[str, set[str]] = {
    "family_pump": {"liquid"},
    "family_liquid_power_recovery_turbine": {"liquid"},
    "family_compressor": {"vapor"},
    "family_gas_expander_turbine": {"vapor"},
}


def family_phase_compatibility(family_id: str, params: dict[str, Any]) -> dict[str, Any]:
    allowed = PHASE_COMPATIBILITY.get(family_id)
    if not allowed:
        return {
            "status": "NOT_APPLICABLE",
            "family_id": family_id,
            "required": False,
            "allowed_phases": [],
        }
    raw_phase = params.get("phase")
    phase = canonical_phase(raw_phase) or str(raw_phase or "").strip().lower()
    if not phase:
        return {
            "status": "WAITING_PHYSICAL_PHASE",
            "family_id": family_id,
            "required": True,
            "allowed_phases": sorted(allowed),
            "observed_phase": None,
        }
    if phase == "mixed":
        return {
            "status": "SPECIAL_DUTY_ROUTE_REQUIRED",
            "family_id": family_id,
            "required": True,
            "allowed_phases": sorted(allowed),
            "observed_phase": phase,
            "selection_effect": "retain general equipment family; disable ordinary catalog ranking until a special-duty route is defined",
        }
    if phase not in allowed:
        return {
            "status": "BLOCKED_INCOMPATIBLE_PHASE",
            "family_id": family_id,
            "required": True,
            "allowed_phases": sorted(allowed),
            "observed_phase": phase,
        }
    return {
        "status": "PASS",
        "family_id": family_id,
        "required": True,
        "allowed_phases": sorted(allowed),
        "observed_phase": phase,
    }


def _display_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return _engineering_number(float(value))
    return str(value).strip()


def _specification(params: dict[str, Any], fields: list[str]) -> dict[str, dict[str, Any]]:
    return {
        field: {
            "value": params[field],
            "unit": FIELD_UNITS.get(field),
            "source": "normalized_or_deterministically_derived_input",
        }
        for field in fields if present(params, field)
    }


def _engineering_designation(type_name: str, specification: dict[str, dict[str, Any]]) -> str:
    parts = [type_name]
    for field, record in specification.items():
        symbol = FIELD_SYMBOLS.get(field, field)
        unit = f" {record['unit']}" if record.get("unit") else ""
        parts.append(f"{symbol}={_display_value(record['value'])}{unit}")
    return " | ".join(parts)


NON_CONCRETE_TYPE_TERMS = (
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


def terminal_type_name_quality(value: Any) -> dict[str, Any]:
    """Report whether a selected equipment form is a concrete engineering type.

    This gate concerns the type name only.  Passing it never promotes an
    engineering type to a standard marking, vendor model, or formal selection.
    """

    text = str(value or "").strip()
    folded = text.casefold()
    prohibited_hits = [
        term for term in NON_CONCRETE_TYPE_TERMS if term.casefold() in folded
    ]
    return {
        "status": "CONCRETE_ENGINEERING_TYPE" if text and not prohibited_hits else "NON_CONCRETE_TYPE_NAME",
        "is_concrete": bool(text) and not prohibited_hits,
        "type_name": text or None,
        "prohibited_term_hits": prohibited_hits,
        "claim_boundary": "type-name quality only; not a standard/vendor/formal-model evidence gate",
    }


def _input_predicate_trace(params: dict[str, Any], fields: list[str], prefix: str) -> list[dict[str, Any]]:
    return [
        {
            "predicate_id": f"{prefix}:input:{field}",
            "field": field,
            "status": "PASS" if present(params, field) else "UNKNOWN",
            "fact": params.get(field),
        }
        for field in fields
    ]


def _pump_standard_pressure_predicate(params: dict[str, Any]) -> dict[str, Any]:
    pressure_fields = [field for field in ("inlet_pressure_mpa", "outlet_pressure_mpa") if present(params, field)]
    basis = str(params.get("pressure_basis", "")).strip()
    if not pressure_fields or basis not in {"absolute", "gauge"}:
        return {
            "predicate_id": "family_pump:gbt5662:max_working_pressure",
            "status": "UNKNOWN",
            "required": ["pressure_basis", "inlet_pressure_mpa", "outlet_pressure_mpa"],
            "standard_limit_mpa": 1.6,
        }
    maximum = max(float(params[field]) for field in pressure_fields)
    if basis == "absolute":
        atmospheric = numeric(params.get("atmospheric_pressure_mpa"))
        if atmospheric is None or atmospheric <= 0:
            return {
                "predicate_id": "family_pump:gbt5662:max_working_pressure",
                "status": "UNKNOWN",
                "observed_maximum_absolute_mpa": maximum,
                "pressure_basis": basis,
                "required": ["atmospheric_pressure_mpa"],
                "standard_limit_mpa_gauge": 1.6,
                "comparison_policy": "absolute_pressure_requires_local_atmospheric_pressure_before_gauge_limit_comparison",
            }
        comparison_pressure = maximum - atmospheric
        comparison_policy = "absolute_to_gauge_then_compare"
    else:
        atmospheric = None
        comparison_pressure = maximum
        comparison_policy = "direct_gauge_comparison"
    status = "PASS" if comparison_pressure <= 1.6 else "FAIL"
    return {
        "predicate_id": "family_pump:gbt5662:max_working_pressure",
        "status": status,
        "observed_maximum_mpa": comparison_pressure,
        "observed_source_maximum_mpa": maximum,
        "pressure_basis": basis,
        "atmospheric_pressure_mpa": atmospheric,
        "standard_limit_mpa_gauge": 1.6,
        "comparison_policy": comparison_policy,
    }


def _pump_standard_candidates(params: dict[str, Any]) -> dict[str, Any]:
    if not present(params, "flow_m3_h") or not present(params, "head_m"):
        return {
            "status": "NEEDS_DUTY_POINT",
            "candidates": [],
            "missing_fields": [field for field in ("flow_m3_h", "head_m") if not present(params, field)],
        }
    flow = float(params["flow_m3_h"])
    head = float(params["head_m"])
    if flow <= 0 or head <= 0:
        return {"status": "INVALID_DUTY_POINT", "candidates": [], "missing_fields": []}
    rows = load_pump_standard_points()
    catalog_sha256 = hashlib.sha256(PUMP_STANDARD_POINTS_PATH.read_bytes()).hexdigest().upper()
    pressure_trace = _pump_standard_pressure_predicate(params)
    npsh_trace = assess_pump_npsh_constraint(params)
    rejection_reasons: list[str] = []
    if pressure_trace["status"] == "FAIL":
        rejection_reasons.append("GB/T_5662_MAX_WORKING_PRESSURE_SCOPE_FAILED")
    if npsh_trace["status"] == "FAIL":
        rejection_reasons.append("PUMP_NPSH_CONSTRAINT_FAILED")
    candidate_status = (
        "REJECTED_STANDARD_SCOPE"
        if pressure_trace["status"] == "FAIL"
        else "REJECTED_CONSTRAINT_FAIL"
        if npsh_trace["status"] == "FAIL"
        else "HEURISTIC_NEAREST_STANDARD_REFERENCE_POINT"
    )
    ranked: list[dict[str, Any]] = []
    for row in rows:
        design_flow = float(row["design_flow_m3_h"])
        design_head = float(row["design_head_m"])
        flow_ratio = flow / design_flow
        head_ratio = head / design_head
        distance = math.hypot(math.log(flow_ratio), math.log(head_ratio))
        marking = str(row["standard_marking"])
        speed = int(row["speed_rpm"])
        candidate = {
            "candidate_id": f"gbt5662:{marking}:{speed}:{_display_value(design_flow)}",
            "candidate_kind": "standard_marking",
            "program_origin": "DETERMINISTIC_STANDARD_CATALOG",
            "designation": f"GB/T 5662-2013 {marking} @ {speed} r/min",
            "standard_marking": marking,
            "recommended_type": "轴向吸入离心泵",
            "type_name_quality": terminal_type_name_quality("轴向吸入离心泵"),
            "standard": row["standard"],
            "speed_rpm": speed,
            "standard_design_point": {"flow_m3_h": design_flow, "head_m": design_head},
            "requested_duty_point": {"flow_m3_h": flow, "head_m": head},
            "flow_ratio_requested_to_design": flow_ratio,
            "head_ratio_requested_to_design": head_ratio,
            "normalized_log_distance": distance,
            "ranking_score": 1.0 / (1.0 + distance),
            "status": candidate_status,
            "candidate_eligibility": (
                "REJECTED" if rejection_reasons else "SCREENING_ONLY_EVIDENCE_OPEN"
            ),
            "candidate_rejection_reasons": list(rejection_reasons),
            "eligible_for_leading_candidate": not rejection_reasons,
            "eligible_for_formal_selection": False,
            "ranking_evidence_class": "J",
            "ranking_method": {
                "metric": "Euclidean distance in ln(Q_requested/Q_reference), ln(H_requested/H_reference)",
                "weights": {"flow_log_ratio": 1.0, "head_log_ratio": 1.0},
                "scope": "all bundled GB/T 5662 reference design points; fixed top 10",
                "does_not_prove": [
                    "pump_curve_fit", "BEP_proximity", "allowable_operating_range",
                    "efficiency", "NPSHr", "vendor_model",
                ],
            },
            "eligible_under_known_standard_scope": pressure_trace["status"] == "PASS",
            "is_vendor_model": False,
            "formal_model": False,
            "predicate_trace": [
                {"predicate_id": "family_pump:identity", "status": "PASS", "fact": "family_pump"},
                {"predicate_id": "family_pump:duty:flow", "status": "PASS", "fact": flow},
                {"predicate_id": "family_pump:duty:head", "status": "PASS", "fact": head},
                dict(pressure_trace),
                {"predicate_id": "family_pump:vendor_curve:Q_H_eta_BEP", "status": "UNKNOWN"},
                {"predicate_id": "family_pump:cavitation:NPSHa_NPSHr", **dict(npsh_trace)},
                {"predicate_id": "family_pump:materials_and_seal", "status": "UNKNOWN"},
            ],
            "source": {
                "kind": "bundled_standard_reference_catalog",
                "catalog_path": PUMP_STANDARD_POINTS_PATH.relative_to(PACKAGE_ROOT).as_posix(),
                "catalog_sha256": catalog_sha256,
                "source_pdf_sha256": row["source_pdf_sha256"],
                "source_pdf_page_1based": row["source_pdf_page_1based"],
                "source_printed_page": row["source_printed_page"],
                "source_table": row["source_table"],
                "reuse_class": row["reuse_class"],
            },
            "vendor_boundary": row["vendor_model_boundary"],
        }
        ranked.append(candidate)
    ranked.sort(key=lambda item: (
        item["normalized_log_distance"], item["standard_marking"], item["speed_rpm"],
        item["standard_design_point"]["flow_m3_h"],
    ))
    shortlist = ranked[:10]
    for rank, item in enumerate(shortlist, 1):
        item["rank"] = rank
    lookup_status = (
        "STANDARD_SCOPE_FAILED"
        if pressure_trace["status"] == "FAIL"
        else "ENGINEERING_CONSTRAINT_FAILED"
        if npsh_trace["status"] == "FAIL"
        else "CANDIDATES_GENERATED"
    )
    return {
        "status": lookup_status,
        "candidate_count": len(shortlist),
        "catalog_row_count": len(rows),
        "candidates": shortlist,
        "pressure_scope": pressure_trace,
        "npsh_constraint": npsh_trace,
        "catalog": {
            "path": PUMP_STANDARD_POINTS_PATH.relative_to(PACKAGE_ROOT).as_posix(),
            "sha256": catalog_sha256,
            "query_policy": "rank every bundled reference point by equal-weight two-dimensional log distance; return fixed top 10",
            "evidence_class": "J",
            "does_not_prove": ["curve_fit", "BEP", "allowable_operating_range", "vendor_model"],
        },
        "missing_fields": [],
    }


ENGINEERING_ADJUSTMENT_SCHEMA = "equipment-engineering-adjustment-plan-v1"
ENGINEERING_ADJUSTMENT_POLICY_ID = "deterministic-nonstandard-adjustment-policy-20260724"
ENGINEERING_ADJUSTMENT_WARNING = (
    "算法初筛警告：台数、串并联方式、单机目标工况和系统候选标记均由程序按固定策略估算；"
    "它不是国标系列覆盖证明、厂家型号、性能曲线、EDR/塔内件水力学或正式机械设计。"
    "用户必须让设备厂家及工艺、机械、管道专业按同一工况复核后再定型。"
)
ENGINEERING_ADJUSTMENT_SUPPORTED_FAMILIES = {
    "family_fixed_tubesheet_exchanger",
    "family_other_heat_exchanger",
    "family_pump",
    "family_tower",
}
EXCHANGER_SINGLE_UNIT_REVIEW_AREA_M2 = 500.0
TOWER_SINGLE_TRAIN_REVIEW_DIAMETER_MM = 4200.0
TOWER_SINGLE_TRAIN_REVIEW_HEIGHT_MM = 60000.0
PUMP_REFERENCE_FIT_LOG_DISTANCE_LIMIT = 0.45
PUMP_MAX_PARALLEL_TRAINS = 12
PUMP_MAX_SERIES_UNITS_PER_TRAIN = 6
PUMP_MAX_TOTAL_OPERATING_UNITS = 24


def _positive_float(value: Any) -> float | None:
    number = numeric(value)
    if number is None or not math.isfinite(number) or number <= 0:
        return None
    return float(number)


def _best_pump_reference_point(
    flow_m3_h: float,
    head_m: float,
) -> dict[str, Any]:
    ranked: list[dict[str, Any]] = []
    for row in load_pump_standard_points():
        reference_flow = float(row["design_flow_m3_h"])
        reference_head = float(row["design_head_m"])
        distance = math.hypot(
            math.log(flow_m3_h / reference_flow),
            math.log(head_m / reference_head),
        )
        ranked.append({
            "standard": str(row["standard"]),
            "standard_marking": str(row["standard_marking"]),
            "speed_rpm": int(row["speed_rpm"]),
            "reference_flow_m3_h": reference_flow,
            "reference_head_m": reference_head,
            "flow_ratio_requested_to_reference": flow_m3_h / reference_flow,
            "head_ratio_requested_to_reference": head_m / reference_head,
            "normalized_log_distance": distance,
        })
    ranked.sort(key=lambda item: (
        item["normalized_log_distance"],
        item["standard_marking"],
        item["speed_rpm"],
        item["reference_flow_m3_h"],
    ))
    if not ranked:
        raise ValueError("pump reference-point catalog is empty")
    return ranked[0]


def _pump_series_parallel_screen(
    flow_m3_h: float,
    head_m: float,
) -> dict[str, Any]:
    """Find a small deterministic series/parallel grid near a reference point.

    This is deliberately a J-class system-screening calculation.  A reference
    design point is not a pump curve, so the result can only propose how the
    duty could be divided before a vendor rerates the complete system.
    """

    candidates: list[dict[str, Any]] = []
    for parallel_count in range(1, PUMP_MAX_PARALLEL_TRAINS + 1):
        for series_count in range(
            1,
            PUMP_MAX_SERIES_UNITS_PER_TRAIN + 1,
        ):
            operating_unit_count = parallel_count * series_count
            if operating_unit_count > PUMP_MAX_TOTAL_OPERATING_UNITS:
                continue
            per_unit_flow = flow_m3_h / parallel_count
            per_unit_head = head_m / series_count
            reference = _best_pump_reference_point(
                per_unit_flow,
                per_unit_head,
            )
            # Prefer a genuinely closer reference point, then fewer installed
            # units and fewer series interfaces.  The penalties only break
            # engineering-screening ties; they do not imply life-cycle cost.
            objective = (
                float(reference["normalized_log_distance"])
                + 0.0125 * (operating_unit_count - 1)
                + 0.01 * (series_count - 1)
            )
            candidates.append({
                "parallel_train_count": parallel_count,
                "series_units_per_train": series_count,
                "operating_unit_count": operating_unit_count,
                "per_unit_flow_m3_h": per_unit_flow,
                "per_unit_head_m": per_unit_head,
                "objective": objective,
                "reference": reference,
            })
    candidates.sort(key=lambda item: (
        item["objective"],
        item["operating_unit_count"],
        item["series_units_per_train"],
        item["parallel_train_count"],
        item["reference"]["standard_marking"],
    ))
    if not candidates:
        raise ValueError("pump series/parallel screening grid is empty")
    return candidates[0]


def _base_engineering_adjustment_plan(
    family_id: str,
    *,
    calculation_audit: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": ENGINEERING_ADJUSTMENT_SCHEMA,
        "policy_id": ENGINEERING_ADJUSTMENT_POLICY_ID,
        "policy_version": "1.0.0",
        "family_id": family_id,
        "status": (
            "NOT_TRIGGERED_WITHIN_SCREENING_POLICY"
            if family_id in ENGINEERING_ADJUSTMENT_SUPPORTED_FAMILIES
            else "NOT_APPLICABLE"
        ),
        "triggered": False,
        "trigger_codes": [],
        "calculation_audit": calculation_audit,
        "configuration": {
            "arrangement_code": "SINGLE_UNIT",
            "parallel_train_count_estimate": 1,
            "series_units_per_train_estimate": 1,
            "operating_unit_count_estimate": 1,
            "standby_train_count_recommendation": 0,
            "installed_unit_count_estimate": 1,
            "load_split_percent_per_parallel_train": 100.0,
            "per_unit_target": {},
            "candidate_equipment_type": None,
            "candidate_standard_marking": None,
            "candidate_model_or_designation": None,
            "model_claim_class": "ALGORITHMIC_ENGINEERING_SCREENING",
            "model_status": "NOT_FORMAL",
        },
        "algorithmic_selection_warning": ENGINEERING_ADJUSTMENT_WARNING,
        "warnings": [
            {
                "code": "ALGORITHMIC_CONFIGURATION_SCREENING_ONLY",
                "severity": "WARNING",
                "message": ENGINEERING_ADJUSTMENT_WARNING,
            },
            {
                "code": "FORMAL_SAME_EQUIPMENT_EVIDENCE_REQUIRED",
                "severity": "WARNING",
                "message": (
                    "正式采用前必须补同设备、同工况的厂家曲线/热工核算/塔内件水力学、"
                    "机械设计及项目可靠性审查；算法结果不得直接转成采购型号。"
                ),
            },
        ],
        "required_actions": [],
        "user_attention": {
            "acknowledgement_required": True,
            "banner_level": "WARNING",
            "banner_text": ENGINEERING_ADJUSTMENT_WARNING,
        },
        "evidence_boundary": {
            "evidence_class": "J",
            "result_status": "PROVISIONAL",
            "promotion_cap": "TYPE_SCREENING",
            "formal_use_allowed": False,
            "vendor_model_claim_allowed": False,
            "standard_series_coverage_proven": False,
        },
        "agent_controls": {
            "calculate_before_adjustment_required": True,
            "calculation_audit_must_be_preserved": True,
            "warning_must_be_preserved": True,
            "ambiguous_material_choice_policy": (
                "use_registered_context_conditioned_route_or_explicit "
                "economic_baseline_with_J_warning"
            ),
            "ambiguous_component_choice_policy": (
                "use_registered_deterministic_connection_component_selector; "
                "never invent a vendor component model"
            ),
            "formal_model_promotion_allowed": False,
            "llm_may_override_counts_or_model": False,
        },
        "deterministic": True,
        "program_generated": True,
        "manual_postprocessing": False,
        "llm_used": False,
    }


def build_engineering_adjustment_plan(
    family_id: str,
    params: dict[str, Any],
    parameter_package: dict[str, Any],
    model_recommendation: dict[str, Any],
    calculations: list[dict[str, Any]],
    pending: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a fixed, warning-bound modification plan after calculations.

    The plan gives a concrete system-screening designation when a single
    standard/reference unit is implausible.  It never fabricates a vendor model
    and never upgrades an algorithmic split into a formal selection.
    """

    hard_pending = [
        item for item in pending if is_hard_calculation_blocker(item)
    ]
    calculation_audit = {
        "status": (
            "BLOCKED_REQUIRED_INPUTS"
            if hard_pending
            else "CALCULATIONS_EXECUTED_OR_NOT_REQUIRED"
        ),
        "calculation_chain_sha256": _canonical_sha256(calculations),
        "calculation_count": len(calculations),
        "pending_count": len(pending),
        "hard_blocker_count": len(hard_pending),
        "hard_blockers": [
            {
                "calculation_id": item.get("calculation_id"),
                "status": item.get("status"),
                "missing_fields": list(item.get("missing_fields", [])),
            }
            for item in hard_pending
        ],
        "parameter_package_context_sha256": (
            parameter_package.get("selection_context", {}).get("sha256")
            if isinstance(
                parameter_package.get("selection_context"),
                dict,
            )
            else None
        ),
    }
    plan = _base_engineering_adjustment_plan(
        family_id,
        calculation_audit=calculation_audit,
    )
    configuration = plan["configuration"]
    recommended_type = str(
        model_recommendation.get("recommended_type") or ""
    ).strip() or None
    configuration["candidate_equipment_type"] = recommended_type

    if family_id not in ENGINEERING_ADJUSTMENT_SUPPORTED_FAMILIES:
        if model_recommendation.get("status") in {
            "STANDARD_SCOPE_FAILED",
            "ENGINEERING_CONSTRAINT_FAILED",
            "CALCULATION_BLOCKED_IDENTITY_CANDIDATE_RETAINED",
            "PHYSICAL_BASIS_BLOCKED_IDENTITY_CANDIDATE_RETAINED",
        }:
            plan["status"] = (
                "REVIEW_REQUIRED_NO_SAFE_AUTOMATIC_CONFIGURATION"
            )
            plan["triggered"] = True
            plan["trigger_codes"] = [
                "GENERIC_SELECTION_OR_CONSTRAINT_GATE_FAILED"
            ]
            configuration["arrangement_code"] = (
                "SPECIAL_DUTY_ENGINEERING_REVIEW"
            )
            configuration["candidate_model_or_designation"] = (
                f"{recommended_type or '专用设备'}（专用设计评审，厂家型号待定）"
            )
            plan["required_actions"] = [
                {
                    "action_code": "DEFINE_SPECIAL_DUTY_ROUTE",
                    "action": (
                        "由工艺、机械及厂家共同定义特殊工况设备路线，"
                        "补齐同设备计算和性能证据后重新运行。"
                    ),
                }
            ]
        plan["plan_sha256"] = _canonical_sha256(plan)
        return plan

    if family_id in {
        "family_fixed_tubesheet_exchanger",
        "family_other_heat_exchanger",
    }:
        area = _positive_float(params.get("heat_transfer_area_m2"))
        duty = _positive_float(params.get("heat_duty_kw"))
        plan["screening_policy"] = {
            "single_unit_review_area_m2": (
                EXCHANGER_SINGLE_UNIT_REVIEW_AREA_M2
            ),
            "threshold_kind": (
                "PROGRAM_REGISTERED_REVIEW_TRIGGER_NOT_NATIONAL_STANDARD_LIMIT"
            ),
            "standard_series_coverage_state": (
                "NOT_PROVEN_NO_BUNDLED_AREA_SERIES_LOOKUP"
            ),
        }
        if area is None:
            plan["status"] = "BLOCKED_REQUIRED_CALCULATION_INPUTS"
            plan["trigger_codes"] = ["HEAT_TRANSFER_AREA_UNAVAILABLE"]
            configuration["arrangement_code"] = (
                "WAITING_THERMAL_CALCULATION"
            )
            configuration["candidate_model_or_designation"] = (
                f"{recommended_type or '换热器'}（面积与分台方案待计算）"
            )
        else:
            unit_count = max(
                1,
                int(
                    math.ceil(
                        area / EXCHANGER_SINGLE_UNIT_REVIEW_AREA_M2
                    )
                ),
            )
            per_unit_area = area / unit_count
            per_unit_duty = duty / unit_count if duty is not None else None
            configuration.update({
                "parallel_train_count_estimate": unit_count,
                "series_units_per_train_estimate": 1,
                "operating_unit_count_estimate": unit_count,
                "standby_train_count_recommendation": 0,
                "installed_unit_count_estimate": unit_count,
                "load_split_percent_per_parallel_train": (
                    100.0 / unit_count
                ),
                "per_unit_target": {
                    "heat_transfer_area_m2": round(per_unit_area, 6),
                    "heat_duty_kw": (
                        round(per_unit_duty, 6)
                        if per_unit_duty is not None
                        else None
                    ),
                },
            })
            if unit_count > 1:
                plan["status"] = (
                    "RECOMMENDED_ALGORITHMIC_MODIFICATION"
                )
                plan["triggered"] = True
                plan["trigger_codes"] = [
                    "EXCHANGER_SINGLE_UNIT_AREA_REVIEW_TRIGGER_EXCEEDED",
                    "STANDARD_AREA_SERIES_COVERAGE_NOT_PROVEN",
                ]
                configuration["arrangement_code"] = (
                    "PARALLEL_EQUAL_DUTY_EXCHANGER_TRAINS"
                )
                configuration["candidate_model_or_designation"] = (
                    f"{unit_count}×{100.0 / unit_count:.1f}%并联 "
                    f"{recommended_type or '管壳式换热器'}"
                    f"（单台A≈{per_unit_area:.3f} m²；"
                    "单台型号由EDR/厂家复核后确定）"
                )
            else:
                leading = model_recommendation.get("leading_candidate")
                configuration["candidate_model_or_designation"] = (
                    leading.get("designation")
                    if isinstance(leading, dict)
                    else recommended_type
                )
        plan["required_actions"] = [
            {
                "action_code": "THERMAL_RATING_AND_SPLIT_REVIEW",
                "action": (
                    "用同工况EDR或等效热工软件复核LMTD/F、污垢热阻、"
                    "壳/管程压降、相变分区及每台面积。"
                ),
            },
            {
                "action_code": "SERIES_PARALLEL_PROCESS_REVIEW",
                "action": (
                    "确认并联均匀分配、隔离阀和清洗切换；若存在温度交叉、"
                    "夹点或分段相变，应比较串联分段方案，不能机械等面积并联。"
                ),
            },
            {
                "action_code": "MECHANICAL_AND_PLOT_REVIEW",
                "action": (
                    "复核管束抽芯空间、运输吊装、热膨胀、振动及GB/T 151/SW6机械设计。"
                ),
            },
        ]

    elif family_id == "family_pump":
        flow = _positive_float(params.get("flow_m3_h"))
        head = _positive_float(params.get("head_m"))
        lookup = (
            model_recommendation.get("pump_standard_lookup")
            if isinstance(
                model_recommendation.get("pump_standard_lookup"),
                dict,
            )
            else {}
        )
        plan["screening_policy"] = {
            "reference_fit_log_distance_limit": (
                PUMP_REFERENCE_FIT_LOG_DISTANCE_LIMIT
            ),
            "maximum_parallel_train_count": PUMP_MAX_PARALLEL_TRAINS,
            "maximum_series_units_per_train": (
                PUMP_MAX_SERIES_UNITS_PER_TRAIN
            ),
            "maximum_total_operating_units": (
                PUMP_MAX_TOTAL_OPERATING_UNITS
            ),
            "threshold_kind": (
                "PROGRAM_REGISTERED_REFERENCE_POINT_SCREENING_NOT_PUMP_CURVE"
            ),
            "catalog_state": lookup.get("status"),
        }
        if flow is None or head is None:
            plan["status"] = "BLOCKED_REQUIRED_CALCULATION_INPUTS"
            plan["trigger_codes"] = ["PUMP_DUTY_POINT_UNAVAILABLE"]
            configuration["arrangement_code"] = (
                "WAITING_FLOW_AND_HEAD"
            )
            configuration["candidate_model_or_designation"] = (
                f"{recommended_type or '泵'}（Q/H与分台方案待计算）"
            )
        else:
            pressure_failed = lookup.get("status") == "STANDARD_SCOPE_FAILED"
            npsh_state = (
                lookup.get("npsh_constraint", {}).get("status")
                if isinstance(lookup.get("npsh_constraint"), dict)
                else None
            )
            npsh_failed = npsh_state == "FAIL"
            catalog_applicable = (
                recommended_type == "轴向吸入离心泵"
                and lookup.get("status")
                != "NOT_APPLICABLE_TERMINAL_TYPE"
            )
            if not catalog_applicable:
                # The terminal pump-form rule has already selected an axial or
                # multistage route.  GB/T 5662 end-suction markings must not be
                # reused across that boundary.  We can still estimate a load
                # split, but the output remains an engineering designation.
                if recommended_type == "轴流泵":
                    parallel_count = max(
                        1,
                        int(math.ceil(flow / 2000.0)),
                    )
                    arrangement_code = (
                        "PARALLEL_AXIAL_FLOW_PUMP_TRAINS_VENDOR_RATING"
                    )
                    route_basis = (
                        "registered axial-flow terminal rule at "
                        "Q >= 2000 m3/h; 2000 m3/h is a split trigger, "
                        "not a certified unit capacity"
                    )
                else:
                    parallel_count = 1
                    arrangement_code = (
                        "MULTISTAGE_OR_SPECIAL_DUTY_PUMP_VENDOR_RATING"
                    )
                    route_basis = (
                        "registered non-GB/T-5662 terminal pump-form rule"
                    )
                plan["triggered"] = True
                plan["trigger_codes"] = [
                    "PUMP_TERMINAL_TYPE_OUTSIDE_GBT5662_CATALOG",
                    *(
                        ["PUMP_NPSH_CONSTRAINT_FAILED"]
                        if npsh_failed
                        else []
                    ),
                ]
                plan["status"] = (
                    "REVIEW_REQUIRED_NO_SAFE_AUTOMATIC_CONFIGURATION"
                    if npsh_failed
                    else "RECOMMENDED_ALGORITHMIC_MODIFICATION"
                )
                per_unit_flow = flow / parallel_count
                configuration.update({
                    "arrangement_code": arrangement_code,
                    "parallel_train_count_estimate": parallel_count,
                    "series_units_per_train_estimate": 1,
                    "operating_unit_count_estimate": parallel_count,
                    "standby_train_count_recommendation": 1,
                    "installed_unit_count_estimate": parallel_count + 1,
                    "load_split_percent_per_parallel_train": (
                        100.0 / parallel_count
                    ),
                    "per_unit_target": {
                        "flow_m3_h": round(per_unit_flow, 6),
                        "head_m": round(head, 6),
                    },
                    "candidate_standard_marking": None,
                    "candidate_model_or_designation": (
                        f"{parallel_count}并联×1串联 "
                        f"{recommended_type or '专用流程泵'}系统"
                        f"（单机Q≈{per_unit_flow:.3f} m³/h，"
                        f"H≈{head:.3f} m；厂家型号待定）"
                    ),
                    "terminal_route_split_basis": route_basis,
                })
            else:
                single = _best_pump_reference_point(flow, head)
                system = _pump_series_parallel_screen(flow, head)
                fit_outside = (
                    float(single["normalized_log_distance"])
                    > PUMP_REFERENCE_FIT_LOG_DISTANCE_LIMIT
                )
                configuration.update({
                    "parallel_train_count_estimate": (
                        system["parallel_train_count"]
                    ),
                    "series_units_per_train_estimate": (
                        system["series_units_per_train"]
                    ),
                    "operating_unit_count_estimate": (
                        system["operating_unit_count"]
                    ),
                    "standby_train_count_recommendation": 1,
                    "installed_unit_count_estimate": (
                        system["operating_unit_count"]
                        + system["series_units_per_train"]
                    ),
                    "load_split_percent_per_parallel_train": (
                        100.0 / system["parallel_train_count"]
                    ),
                    "per_unit_target": {
                        "flow_m3_h": round(
                            system["per_unit_flow_m3_h"],
                            6,
                        ),
                        "head_m": round(
                            system["per_unit_head_m"],
                            6,
                        ),
                    },
                    "reference_fit": {
                        "single_unit_log_distance": round(
                            float(single["normalized_log_distance"]),
                            9,
                        ),
                        "adjusted_per_unit_log_distance": round(
                            float(
                                system["reference"][
                                    "normalized_log_distance"
                                ]
                            ),
                            9,
                        ),
                        "metric": (
                            "Euclidean distance in ln(Q/Qref), ln(H/Href)"
                        ),
                    },
                })
                trigger_codes: list[str] = []
                if fit_outside:
                    trigger_codes.append(
                        "PUMP_SINGLE_REFERENCE_POINT_FIT_OUTSIDE_POLICY"
                    )
                if pressure_failed:
                    trigger_codes.append(
                        "PUMP_GBT5662_PRESSURE_SCOPE_FAILED"
                    )
                if npsh_failed:
                    trigger_codes.append(
                        "PUMP_NPSH_CONSTRAINT_FAILED"
                    )
                multi_unit = (
                    system["parallel_train_count"] > 1
                    or system["series_units_per_train"] > 1
                )
                if multi_unit:
                    trigger_codes.append(
                        "PUMP_SERIES_PARALLEL_DUTY_SPLIT_RECOMMENDED"
                    )
                if trigger_codes:
                    plan["triggered"] = True
                    plan["trigger_codes"] = sorted(set(trigger_codes))
                    plan["status"] = (
                        "REVIEW_REQUIRED_NO_SAFE_AUTOMATIC_CONFIGURATION"
                        if pressure_failed or npsh_failed
                        else "RECOMMENDED_ALGORITHMIC_MODIFICATION"
                    )
                reference = system["reference"]
                parallel_count = system["parallel_train_count"]
                series_count = system["series_units_per_train"]
                if pressure_failed:
                    configuration["arrangement_code"] = (
                        "HIGH_PRESSURE_SPECIAL_DUTY_PUMP_SYSTEM_REVIEW"
                    )
                    configuration["candidate_standard_marking"] = None
                    configuration["candidate_model_or_designation"] = (
                        f"{parallel_count}并联×{series_count}串联 "
                        f"{recommended_type or '专用流程泵'}系统"
                        f"（单机Q≈{system['per_unit_flow_m3_h']:.3f} m³/h，"
                        f"H≈{system['per_unit_head_m']:.3f} m；"
                        "GB/T 5662压力范围不适用，厂家型号待定）"
                    )
                else:
                    configuration["arrangement_code"] = (
                        "PARALLEL_AND_SERIES_PUMP_TRAINS"
                        if multi_unit
                        else "SINGLE_PUMP_REFERENCE_POINT"
                    )
                    marking = (
                        f"{reference['standard']} "
                        f"{reference['standard_marking']} @ "
                        f"{reference['speed_rpm']} r/min"
                    )
                    configuration["candidate_standard_marking"] = marking
                    configuration["candidate_model_or_designation"] = (
                        f"{parallel_count}并联×{series_count}串联：{marking}"
                        f"（单机Q≈{system['per_unit_flow_m3_h']:.3f} m³/h，"
                        f"H≈{system['per_unit_head_m']:.3f} m；"
                        "仅参考点初筛）"
                    )
            if npsh_failed:
                configuration["arrangement_code"] = (
                    "NPSH_HYDRAULIC_REDESIGN_REQUIRED"
                )
                configuration["model_status"] = (
                    "BLOCKED_BY_NPSH_UNTIL_VENDOR_AND_SYSTEM_REVIEW"
                )
        plan["required_actions"] = [
            {
                "action_code": "VENDOR_CURVE_AND_BEP_REVIEW",
                "action": (
                    "按拆分后的每台Q/H向厂家索取完整Q-H-η、BEP、允许连续运行区和功率曲线；"
                    "禁止把GB/T参考点当作厂家性能曲线。"
                ),
            },
            {
                "action_code": "NPSH_AND_SUCTION_SYSTEM_REVIEW",
                "action": (
                    "按最不利液位、温度、汽化压力和吸入管损复核NPSHa/NPSHr；"
                    "不足时比较降低转速、双吸/立式筒袋泵、提高液位或减小吸入损失。"
                ),
            },
            {
                "action_code": "SERIES_PARALLEL_CONTROL_REVIEW",
                "action": (
                    "复核并联泵曲线稳定性、止回阀/最小流量回流、串联泵级间压力、"
                    "启停联锁及一列备用策略；项目应确认是否确需备用列。"
                ),
            },
            {
                "action_code": "MATERIAL_SEAL_DRIVER_REVIEW",
                "action": (
                    "复核介质相容材料、机械密封方案、轴功率裕量、电机和变频/调速要求。"
                ),
            },
        ]

    elif family_id == "family_tower":
        diameter = _positive_float(params.get("inner_diameter_mm"))
        height = _positive_float(params.get("height_mm"))
        diameter_ratio = (
            diameter / TOWER_SINGLE_TRAIN_REVIEW_DIAMETER_MM
            if diameter is not None
            else None
        )
        height_ratio = (
            height / TOWER_SINGLE_TRAIN_REVIEW_HEIGHT_MM
            if height is not None
            else None
        )
        plan["screening_policy"] = {
            "single_train_diameter_review_threshold_mm": (
                TOWER_SINGLE_TRAIN_REVIEW_DIAMETER_MM
            ),
            "single_train_height_review_threshold_mm": (
                TOWER_SINGLE_TRAIN_REVIEW_HEIGHT_MM
            ),
            "threshold_kind": (
                "PROGRAM_REGISTERED_REVIEW_TRIGGER_NOT_FORMAL_TOWER_LIMIT"
            ),
            "public_geometry_policy": (
                "do_not_publish_internal_screening_diameter_or_height_as_formal"
            ),
        }
        if diameter is None and height is None:
            plan["status"] = "BLOCKED_REQUIRED_CALCULATION_INPUTS"
            plan["trigger_codes"] = [
                "TOWER_PRELIMINARY_GEOMETRY_UNAVAILABLE"
            ]
            configuration["arrangement_code"] = (
                "WAITING_TOWER_HYDRAULIC_SCREEN"
            )
            configuration["candidate_model_or_designation"] = (
                f"{recommended_type or '塔器'}（并列方案待水力学计算）"
            )
        else:
            parallel_count = (
                max(1, int(math.ceil(diameter_ratio ** 2)))
                if diameter_ratio is not None
                else 1
            )
            diameter_trigger = (
                diameter_ratio is not None and diameter_ratio > 1.0
            )
            height_trigger = (
                height_ratio is not None and height_ratio > 1.0
            )
            configuration.update({
                "parallel_train_count_estimate": parallel_count,
                "series_units_per_train_estimate": 1,
                "operating_unit_count_estimate": parallel_count,
                "standby_train_count_recommendation": 0,
                "installed_unit_count_estimate": parallel_count,
                "load_split_percent_per_parallel_train": (
                    100.0 / parallel_count
                ),
                "per_unit_target": {
                    "hydraulic_load_fraction": round(
                        1.0 / parallel_count,
                        9,
                    ),
                    "formal_diameter": "OPEN",
                    "formal_height": "OPEN",
                },
                "internal_screening_ratios": {
                    "diameter_to_review_threshold": (
                        round(diameter_ratio, 6)
                        if diameter_ratio is not None
                        else None
                    ),
                    "height_to_review_threshold": (
                        round(height_ratio, 6)
                        if height_ratio is not None
                        else None
                    ),
                    "not_formal_geometry": True,
                },
            })
            trigger_codes = []
            if diameter_trigger:
                trigger_codes.append(
                    "TOWER_SINGLE_TRAIN_DIAMETER_REVIEW_TRIGGER_EXCEEDED"
                )
            if height_trigger:
                trigger_codes.append(
                    "TOWER_SINGLE_TRAIN_HEIGHT_REVIEW_TRIGGER_EXCEEDED"
                )
            if trigger_codes:
                plan["triggered"] = True
                plan["status"] = (
                    "RECOMMENDED_ALGORITHMIC_MODIFICATION"
                )
                plan["trigger_codes"] = trigger_codes
                configuration["arrangement_code"] = (
                    "PARALLEL_TOWER_TRAINS_WITH_SECTIONING_STUDY"
                    if diameter_trigger and height_trigger
                    else "PARALLEL_TOWER_TRAINS"
                    if diameter_trigger
                    else "SECTIONED_COLUMN_OR_ALTERNATE_INTERNALS_STUDY"
                )
                configuration["candidate_model_or_designation"] = (
                    f"{parallel_count}列并联"
                    f"{recommended_type or '塔器'}系统"
                    f"（每列约{100.0 / parallel_count:.1f}%负荷；"
                    "正式塔径/塔高及塔内件水力学 OPEN）"
                )
            else:
                leading = model_recommendation.get("leading_candidate")
                configuration["candidate_model_or_designation"] = (
                    leading.get("designation")
                    if isinstance(leading, dict)
                    else recommended_type
                )
        plan["required_actions"] = [
            {
                "action_code": "CONTROLLING_SECTION_HYDRAULIC_RATING",
                "action": (
                    "按每个控制塔段、气液负荷、物性、泛点率、降液管及压降完成正式塔内件水力学；"
                    "不得用总体平均负荷直接定塔径。"
                ),
            },
            {
                "action_code": "ALTERNATE_INTERNALS_AND_PARALLEL_TRAIN_STUDY",
                "action": (
                    "比较多溢流塔板、高通量塔板、规整填料及并列塔方案，"
                    "校核负荷分配、调节比、开停车和偏流。"
                ),
            },
            {
                "action_code": "MECHANICAL_TRANSPORT_WIND_SEISMIC_REVIEW",
                "action": (
                    "完成分段制造、运输吊装、平台管口、风震、支座和基础联动审查。"
                ),
            },
        ]

    plan["plan_sha256"] = _canonical_sha256(plan)
    return plan


def build_selection_agent_control(
    family_id: str,
    rule: dict[str, Any],
    params: dict[str, Any],
    parameter_package: dict[str, Any],
    model_recommendation: dict[str, Any],
    adjustment_plan: dict[str, Any],
    calculations: list[dict[str, Any]],
    pending: list[dict[str, Any]],
    design_fallbacks: list[dict[str, Any]],
) -> dict[str, Any]:
    """Record how the deterministic Agent enforced calculate-before-select."""

    expected_calculation_ids = list(rule.get("calculation_rules", []))
    attempted_calculation_ids = sorted({
        str(item.get("calculation_id") or "")
        for item in [*calculations, *pending]
        if item.get("calculation_id")
    })
    satisfied_by_existing_target_ids = sorted({
        calc_id
        for calc_id in expected_calculation_ids
        if (
            calc_id not in attempted_calculation_ids
            and CALCULATION_OUTPUT_FIELDS.get(calc_id)
            and present(
                params,
                str(CALCULATION_OUTPUT_FIELDS[calc_id]),
            )
        )
    })
    satisfied_calculation_ids = sorted(set([
        *attempted_calculation_ids,
        *satisfied_by_existing_target_ids,
    ]))
    unsatisfied_calculation_ids = sorted(
        set(expected_calculation_ids) - set(satisfied_calculation_ids)
    )
    hard_pending = [
        item for item in pending if is_hard_calculation_blocker(item)
    ]
    material_fallback = next(
        (
            item for item in design_fallbacks
            if str(item.get("field_id") or "") == "material"
            and item.get("state")
            != "SUPERSEDED_BY_DETERMINISTIC_CALCULATION"
        ),
        None,
    )
    terminal = (
        model_recommendation.get("terminal_selection")
        if isinstance(
            model_recommendation.get("terminal_selection"),
            dict,
        )
        else {}
    )
    control = {
        "schema": "equipment-selection-agent-control-v1",
        "status": (
            "BLOCKED_REQUIRED_CALCULATION_INPUTS"
            if hard_pending
            else "CONTROLLED_WITH_ADJUSTMENT_WARNING"
            if adjustment_plan.get("triggered") is True
            else "CONTROLLED_CALCULATE_THEN_SELECT"
        ),
        "family_id": family_id,
        "calculate_before_select": {
            "required": True,
            "expected_calculation_ids": expected_calculation_ids,
            "attempted_calculation_ids": attempted_calculation_ids,
            "satisfied_by_existing_target_ids": (
                satisfied_by_existing_target_ids
            ),
            "satisfied_calculation_ids": satisfied_calculation_ids,
            "unsatisfied_calculation_ids": unsatisfied_calculation_ids,
            "all_registered_calculations_attempted": set(
                expected_calculation_ids
            ).issubset(set(attempted_calculation_ids)),
            "calculation_execution_satisfied": (
                not unsatisfied_calculation_ids
            ),
            "satisfaction_semantics": (
                "A registered calculation is satisfied when it was attempted "
                "or its canonical target already existed before selection. "
                "A pre-existing target is not falsely reported as an attempted "
                "calculation."
            ),
            "hard_blocker_count": len(hard_pending),
            "parameter_package_context_sha256": (
                parameter_package.get("selection_context", {}).get(
                    "sha256"
                )
                if isinstance(
                    parameter_package.get("selection_context"),
                    dict,
                )
                else None
            ),
        },
        "ambiguous_choice_resolution": {
            "equipment_form": {
                "value": model_recommendation.get("recommended_type"),
                "status": terminal.get("status"),
                "rule_id": terminal.get("rule_id"),
                "default_applied": terminal.get("default_applied"),
                "evidence_class": terminal.get("evidence_class", "J"),
                "warning": terminal.get("assumption"),
            },
            "material": {
                "value": params.get("material"),
                "status": (
                    "REGISTERED_FALLBACK_WITH_WARNING"
                    if material_fallback
                    else "EXPLICIT_OR_DERIVED_INPUT"
                    if present(params, "material")
                    else "OPEN"
                ),
                "fallback_tier": (
                    material_fallback.get("tier")
                    if isinstance(material_fallback, dict)
                    else None
                ),
                "warning": (
                    material_fallback.get("warning")
                    if isinstance(material_fallback, dict)
                    else (
                        "材料仍须按介质腐蚀、温度、冲蚀和制造规范复核。"
                        if present(params, "material")
                        else "材料未闭合；保持OPEN，不由Agent臆造。"
                    )
                ),
            },
            "connection_components": {
                "status": (
                    "DOWNSTREAM_REGISTERED_SELECTOR_REQUIRED"
                ),
                "policy": (
                    "select only registered valve/fitting/flange/gasket "
                    "types from the deterministic connection package"
                ),
                "vendor_model_invention_allowed": False,
            },
        },
        "engineering_adjustment": {
            "status": adjustment_plan.get("status"),
            "triggered": adjustment_plan.get("triggered"),
            "plan_sha256": adjustment_plan.get("plan_sha256"),
            "warning_acknowledgement_required": (
                adjustment_plan.get("user_attention", {}).get(
                    "acknowledgement_required"
                )
                if isinstance(
                    adjustment_plan.get("user_attention"),
                    dict,
                )
                else True
            ),
        },
        "authority": {
            "deterministic_result_authoritative": True,
            "llm_may_review_but_not_override": True,
            "formal_model_promotion_allowed": False,
        },
        "deterministic": True,
        "program_generated": True,
        "llm_used": False,
    }
    control["agent_control_sha256"] = _canonical_sha256(control)
    return control


def _terminal_type_rule_matches(params: dict[str, Any], rule: dict[str, Any]) -> bool:
    """Evaluate one small allowlisted condition rule for equipment-form selection."""

    predicates = rule.get("all", [])
    if not isinstance(predicates, list) or not predicates:
        return False
    for predicate in predicates:
        if not isinstance(predicate, dict):
            return False
        field = str(predicate.get("field") or "")
        operator = str(predicate.get("operator") or "").casefold()
        expected = predicate.get("value")
        actual = params.get(field)
        if operator == "eq":
            if str(actual or "").strip().casefold() != str(expected or "").strip().casefold():
                return False
            continue
        if operator == "in":
            expected_values = expected if isinstance(expected, list) else [expected]
            if str(actual or "").strip().casefold() not in {
                str(item or "").strip().casefold() for item in expected_values
            }:
                return False
            continue
        actual_number = numeric(actual)
        expected_number = numeric(expected)
        if actual_number is None or expected_number is None:
            return False
        if operator == "gt" and not actual_number > expected_number:
            return False
        if operator == "gte" and not actual_number >= expected_number:
            return False
        if operator == "lt" and not actual_number < expected_number:
            return False
        if operator == "lte" and not actual_number <= expected_number:
            return False
        if operator not in {"gt", "gte", "lt", "lte"}:
            return False
    return True


def build_model_recommendation(
    family_id: str,
    parameter_package: dict[str, Any],
    rule: dict[str, Any],
    family_node: dict[str, Any],
    graph: dict[str, Any],
    model_status: str,
    model_blockers: list[str],
) -> dict[str, Any]:
    params = dict(parameter_package.get("selection_context", {}).get("values", {}))
    selection_vector = parameter_package.get("selection_feature_vector", {})
    model_rules = load_model_rules()
    family_rule = next((item for item in model_rules.get("families", []) if item.get("family_id") == family_id), None)
    if family_rule is None:
        return {
            "status": "BLOCKED_MODEL_RULE_MISSING",
            "family_id": family_id,
            "candidates": [],
            "llm_used": False,
        }
    model_rule_sha256 = hashlib.sha256(MODEL_RULES_PATH.read_bytes()).hexdigest().upper()
    knowledge_route = {
        "model_rule_path": MODEL_RULES_PATH.relative_to(PACKAGE_ROOT).as_posix(),
        "model_rule_sha256": model_rule_sha256,
        "graph_model_source_rule": family_node.get("model_source_rule"),
        "graph_required_gates": family_node.get("required_gates", []),
        "standard_routes": standard_routes(family_id, graph),
        "vendor_routes": vendor_routes(family_id, graph),
    }
    phase_gate = parameter_package.get("phase_compatibility", {})
    phase_blocked = phase_gate.get("status") == "BLOCKED_INCOMPATIBLE_PHASE"
    calculation_blocked = (
        parameter_package.get("status") in {"BLOCKED", "BLOCKED_PHYSICAL_PHASE"}
        or selection_vector.get("status") == "BLOCKED"
    )
    block_type = str(params.get("aspen_block_type", "")).strip().upper()
    mapped_type = family_rule.get("block_type_recommended_types", {}).get(block_type)
    explicit_type = str(params.get("equipment_type", "")).strip()
    generic_identity_tokens = {
        token(item) for item in family_rule.get("generic_identity_inputs", [])
        if str(item).strip()
    }
    family_name = str(family_node.get("family_name") or family_node.get("name") or "").strip()
    if family_name:
        generic_identity_tokens.add(token(family_name))
    explicit_type_quality = terminal_type_name_quality(explicit_type)
    explicit_terminal_type = (
        explicit_type
        if (
            explicit_type
            and token(explicit_type) not in generic_identity_tokens
            and explicit_type_quality["is_concrete"]
        )
        else ""
    )
    rejected_non_concrete_explicit_type = (
        explicit_type
        if (
            explicit_type
            and token(explicit_type) not in generic_identity_tokens
            and not explicit_type_quality["is_concrete"]
        )
        else ""
    )
    terminal_default_type = str(family_rule.get("terminal_default_type") or "").strip()
    terminal_condition_registry = [
        item for item in family_rule.get("api_condition_rules", [])
        if isinstance(item, dict)
        and str(item.get("rule_id") or "").strip()
        and str(item.get("recommended_type") or "").strip()
        and str(item.get("condition_text") or "").strip()
    ]
    requested_terminal_rule_id = str(params.get("terminal_type_rule_override_id") or "").strip()
    controlled_terminal_rule = next(
        (
            item for item in terminal_condition_registry
            if str(item.get("rule_id") or "").strip() == requested_terminal_rule_id
        ),
        None,
    )
    block_default = family_rule.get("block_type_default_types", {}).get(block_type)
    if isinstance(block_default, str):
        block_default = {
            "recommended_type": block_default,
            "rule_id": f"{family_id}:aspen_block_default:{block_type}",
            "assumption": "Aspen 模块未给机械构型时采用登记默认实现。",
        }
    matched_terminal_rule = next(
        (
            item for item in family_rule.get("terminal_type_rules", [])
            if isinstance(item, dict) and _terminal_type_rule_matches(params, item)
        ),
        None,
    )
    if explicit_terminal_type:
        recommended_type = explicit_terminal_type
        terminal_selection = {
            "status": "EXPLICIT_TERMINAL_TYPE_SELECTED",
            "recommended_type": recommended_type,
            "selection_basis": "explicit_input",
            "default_applied": False,
            "evidence_class": "A",
            "provisional": False,
            "rule_id": "user_or_same_case:explicit_equipment_type",
            "assumption": None,
            "terminal_scope": "equipment_form",
            "formal_model": False,
            "is_vendor_model": False,
        }
    elif controlled_terminal_rule:
        recommended_type = str(controlled_terminal_rule["recommended_type"])
        terminal_selection = {
            "status": "CONDITIONED_TERMINAL_TYPE_SELECTED",
            "recommended_type": recommended_type,
            "selection_basis": "controlled_registered_condition_rule",
            "default_applied": False,
            "evidence_class": "J",
            "provisional": True,
            "rule_id": str(controlled_terminal_rule["rule_id"]),
            "condition_id": str(
                controlled_terminal_rule.get("condition_id")
                or controlled_terminal_rule["rule_id"]
            ),
            "condition_text": str(controlled_terminal_rule["condition_text"]),
            "assumption": str(
                controlled_terminal_rule.get("assumption")
                or "受控外部条件判断命中登记规则；仍需同设备工程证据闭合。"
            ),
            "terminal_scope": "equipment_form",
            "formal_model": False,
            "is_vendor_model": False,
        }
    elif matched_terminal_rule:
        recommended_type = str(matched_terminal_rule["recommended_type"])
        condition_default_applied = bool(matched_terminal_rule.get("default_applied", False))
        terminal_selection = {
            "status": (
                "DEFAULTED_TERMINAL_TYPE_SELECTED"
                if condition_default_applied else "CONDITIONED_TERMINAL_TYPE_SELECTED"
            ),
            "recommended_type": recommended_type,
            "selection_basis": (
                "condition_rule_with_registered_default"
                if condition_default_applied else "condition_rule"
            ),
            "default_applied": condition_default_applied,
            "evidence_class": "J",
            "provisional": True,
            "rule_id": str(matched_terminal_rule["rule_id"]),
            "assumption": str(matched_terminal_rule.get("assumption") or "登记条件规则命中。"),
            "matched_conditions": matched_terminal_rule.get("all", []),
            "terminal_scope": "equipment_form",
            "formal_model": False,
            "is_vendor_model": False,
        }
    elif isinstance(block_default, dict) and str(block_default.get("recommended_type") or "").strip():
        recommended_type = str(block_default["recommended_type"])
        terminal_selection = {
            "status": "DEFAULTED_TERMINAL_TYPE_SELECTED",
            "recommended_type": recommended_type,
            "selection_basis": "aspen_block_registered_default",
            "default_applied": True,
            "evidence_class": "J",
            "provisional": True,
            "rule_id": str(block_default.get("rule_id") or f"{family_id}:aspen_block_default:{block_type}"),
            "assumption": str(block_default.get("assumption") or "Aspen 模块未给机械构型时采用登记默认实现。"),
            "terminal_scope": "equipment_form",
            "formal_model": False,
            "is_vendor_model": False,
        }
    elif mapped_type:
        recommended_type = str(mapped_type)
        terminal_selection = {
            "status": "CONDITIONED_TERMINAL_TYPE_SELECTED",
            "recommended_type": recommended_type,
            "selection_basis": "aspen_block_rule",
            "default_applied": False,
            "evidence_class": "J",
            "provisional": True,
            "rule_id": f"{family_id}:aspen_block:{block_type}",
            "assumption": "设备型式由 Aspen 模块身份和登记映射确定；未替代同设备机械或厂家证据。",
            "terminal_scope": "equipment_form",
            "formal_model": False,
            "is_vendor_model": False,
        }
    elif terminal_default_type:
        recommended_type = terminal_default_type
        terminal_selection = {
            "status": "DEFAULTED_TERMINAL_TYPE_SELECTED",
            "recommended_type": recommended_type,
            "selection_basis": "registered_default",
            "default_applied": True,
            "evidence_class": "J",
            "provisional": True,
            "rule_id": str(family_rule.get("terminal_default_rule_id") or f"{family_id}:registered_default"),
            "assumption": str(family_rule.get("terminal_default_assumption") or "未给出型式决定条件，采用该设备族登记默认型式。"),
            "terminal_scope": "equipment_form",
            "formal_model": False,
            "is_vendor_model": False,
        }
    else:
        recommended_type = str(family_rule["generic_type"])
        terminal_selection = {
            "status": "LEGACY_GENERIC_TYPE_SELECTED",
            "recommended_type": recommended_type,
            "selection_basis": "legacy_generic_type",
            "default_applied": True,
            "evidence_class": "J",
            "provisional": True,
            "rule_id": f"{family_id}:legacy_generic_type",
            "assumption": "设备族尚未登记终点型式默认值。",
            "terminal_scope": "equipment_form",
            "formal_model": False,
            "is_vendor_model": False,
        }
    terminal_selection["type_name_quality"] = terminal_type_name_quality(recommended_type)
    if rejected_non_concrete_explicit_type:
        terminal_selection["rejected_explicit_type"] = {
            "value": rejected_non_concrete_explicit_type,
            "reason": "NON_CONCRETE_TYPE_NAME",
            "quality": explicit_type_quality,
            "fallback_applied": True,
        }
    defaulted_exchanger_type_screening_only = (
        family_id
        in {
            "family_fixed_tubesheet_exchanger",
            "family_other_heat_exchanger",
        }
        and terminal_selection.get("default_applied") is True
    )
    defaulted_exchanger_open_gates = (
        [
            "exchanger_flow_arrangement_and_pass_configuration",
            "hot_and_cold_side_temperature_pressure_mapping",
            "LMTD_and_correction_factor",
            "fouling_resistances_and_allowable_pressure_drops",
            "phase_change_zoning_if_applicable",
            "thermal_expansion_and_differential_stress",
            "cleanability_and_bundle_removal_space",
            "same_equipment_thermal_rating_or_EDR_evidence",
            "mechanical_design_and_vendor_datasheet",
        ]
        if defaulted_exchanger_type_screening_only
        else []
    )
    required_fields = list(family_rule.get("candidate_required_fields", []))
    designation_fields = list(family_rule.get("designation_fields", []))
    specification = _specification(params, designation_fields)
    missing_candidate_fields = list(selection_vector.get("missing_fields", []))
    engineering_candidate_kind = (
        "component_marking"
        if family_rule["recommendation_class"] == "component_marking"
        else "engineered_designation"
    )
    engineering_candidate = {
        "candidate_id": f"{family_id}:concrete-engineering-type",
        "rank": 1,
        # This row is a concrete terminal engineering type plus the current
        # process/design specification.  It remains deliberately separate from
        # standard markings and vendor models when same-record evidence is open.
        "candidate_kind": engineering_candidate_kind,
        "program_origin": "DETERMINISTIC_ENGINEERING_SELECTOR",
        "target_recommendation_class": family_rule["recommendation_class"],
        "designation": _engineering_designation(recommended_type, specification),
        "recommended_type": recommended_type,
        "designation_scope": "concrete_terminal_engineering_type_with_design_specification",
        "type_name_quality": terminal_type_name_quality(recommended_type),
        "specification": specification,
        "status": (
            "IDENTITY_CANDIDATE_RETAINED_PHYSICAL_BASIS_BLOCKED" if phase_blocked
            else "IDENTITY_CANDIDATE_RETAINED_CALCULATION_BLOCKED" if calculation_blocked
            else "PRELIMINARY_ENGINEERING_CANDIDATE_WITH_DEFAULTED_TYPE"
            if defaulted_exchanger_type_screening_only
            and not missing_candidate_fields
            else "ENGINEERING_CANDIDATE_READY" if not missing_candidate_fields
            else "PARTIAL_ENGINEERING_CANDIDATE"
        ),
        "completeness": {
            "required_count": len(required_fields),
            "present_count": len(required_fields) - len(missing_candidate_fields),
            "missing_fields": missing_candidate_fields,
        },
        "predicate_trace": _input_predicate_trace(params, required_fields, family_id),
        "source": {"kind": "knowledge_graph_model_rule", **knowledge_route},
        "missing_gates": sorted(set(
            missing_candidate_fields
            + model_blockers
            + defaulted_exchanger_open_gates
        )),
        "is_vendor_model": False,
        "formal_model": False,
        "candidate_eligibility": (
            "IDENTITY_ONLY" if calculation_blocked
            else "SCREENING_ONLY_EVIDENCE_OPEN"
            if defaulted_exchanger_type_screening_only
            and not missing_candidate_fields
            else "READY_FOR_ENGINEERING_REVIEW" if not missing_candidate_fields
            else "PARTIAL"
        ),
        "eligible_for_leading_candidate": True,
        "eligible_for_formal_selection": False,
        "terminal_selection": terminal_selection,
    }
    candidates: list[dict[str, Any]] = []
    supplied_classification = classify_supplied_designation(params)
    supplied_model = str(params.get("vendor_model") or params.get("candidate_model") or "").strip()
    if supplied_model:
        classification = supplied_classification["classification"]
        supplied_formal_ready = model_status == "final_model"
        supplied_status = (
            "MACHINE_VERIFIED_SUPPLIED_FINAL_MODEL"
            if supplied_formal_ready
            else {
                "vendor_candidate": "USER_SUPPLIED_VENDOR_CANDIDATE_REQUIRES_MACHINE_EVIDENCE",
                "standard_marking": "USER_SUPPLIED_STANDARD_MARKING_REQUIRES_STANDARD_TRACE",
                "engineering_specification": "USER_SUPPLIED_ENGINEERING_SPECIFICATION_NOT_VENDOR_MODEL",
                "unclassified_supplied_designation": "USER_SUPPLIED_DESIGNATION_UNCLASSIFIED",
            }.get(classification, "USER_SUPPLIED_CANDIDATE_REQUIRES_MACHINE_EVIDENCE")
        )
        supplied_source_kind = (
            "user_supplied_machine_verified_candidate"
            if supplied_formal_ready
            else "user_supplied_unverified_candidate"
        )
        candidates.append({
            "candidate_id": f"{family_id}:supplied:{token(supplied_model)}",
            "rank": 1,
            "candidate_kind": classification,
            "program_origin": (
                "MACHINE_VERIFIED_SUPPLIED_CANDIDATE"
                if supplied_formal_ready
                else "UNVERIFIED_SUPPLIED_INPUT"
            ),
            "designation": supplied_model,
            "recommended_type": recommended_type,
            "status": supplied_status,
            "is_vendor_model": supplied_classification["is_vendor_model"],
            "formal_model": supplied_formal_ready,
            "candidate_eligibility": (
                "FORMAL_READY" if supplied_formal_ready else "EVIDENCE_OPEN"
            ),
            "eligible_for_leading_candidate": supplied_formal_ready,
            "eligible_for_formal_selection": supplied_formal_ready,
            "supplied_designation_classification": supplied_classification,
            "predicate_trace": _input_predicate_trace(params, rule.get("verification_fields", []), family_id),
            "source": {"kind": supplied_source_kind, **knowledge_route},
            "missing_gates": sorted(set(model_blockers)),
        })
    pump_lookup: dict[str, Any] | None = None
    if (
        family_rule.get("candidate_strategy") == "gbt5662_design_point_collect"
        and phase_gate.get("status") == "PASS"
    ):
        if recommended_type == "轴向吸入离心泵":
            pump_lookup = _pump_standard_candidates(params)
        else:
            pump_lookup = {
                "status": "NOT_APPLICABLE_TERMINAL_TYPE",
                "candidates": [],
                "missing_fields": [],
                "terminal_type": recommended_type,
                "reason": "GB/T 5662 轴向吸入离心泵标记表不得用于其他已终选泵型。",
            }
        candidates.extend(pump_lookup.get("candidates", []))
    candidates.append(engineering_candidate)
    npsh_constraint_failed = bool(
        pump_lookup
        and pump_lookup.get("npsh_constraint", {}).get("status") == "FAIL"
    )
    if npsh_constraint_failed:
        constraint_gate = "engineering_constraint_fail:pump_npsh_margin"
        for candidate in candidates:
            if candidate is engineering_candidate:
                candidate["status"] = "ENGINEERING_FAMILY_RETAINED_CONSTRAINT_FAIL"
                candidate["eligible_for_leading_candidate"] = True
                candidate["missing_gates"] = sorted(set([
                    *candidate.get("missing_gates", []), constraint_gate,
                ]))
                continue
            candidate["status"] = "REJECTED_CONSTRAINT_FAIL"
            candidate["candidate_eligibility"] = "REJECTED"
            candidate["eligible_for_leading_candidate"] = False
            candidate["eligible_for_formal_selection"] = False
            candidate["candidate_rejection_reasons"] = sorted(set([
                *candidate.get("candidate_rejection_reasons", []),
                "PUMP_NPSH_CONSTRAINT_FAILED",
            ]))
    surge_constraint_failed = any(
        item.get("check_id") == "compressor_surge_margin" and item.get("status") == "FAIL"
        for item in parameter_package.get("constraint_checks", [])
        if isinstance(item, dict)
    )
    if surge_constraint_failed:
        constraint_gate = "engineering_constraint_fail:compressor_surge_margin"
        for candidate in candidates:
            if candidate is engineering_candidate:
                candidate["status"] = "ENGINEERING_FAMILY_RETAINED_CONSTRAINT_FAIL"
                candidate["candidate_eligibility"] = "CONSTRAINT_FAIL_FAMILY_ONLY"
                candidate["eligible_for_leading_candidate"] = True
                candidate["missing_gates"] = sorted(set([
                    *candidate.get("missing_gates", []), constraint_gate,
                ]))
                continue
            candidate["status"] = "REJECTED_CONSTRAINT_FAIL"
            candidate["candidate_eligibility"] = "REJECTED"
            candidate["eligible_for_leading_candidate"] = False
            candidate["eligible_for_formal_selection"] = False
            candidate["candidate_rejection_reasons"] = sorted(set([
                *candidate.get("candidate_rejection_reasons", []),
                "COMPRESSOR_SURGE_MARGIN_CONSTRAINT_FAILED",
            ]))
    storage_volume_constraint_failed = any(
        item.get("check_id") == "storage_required_volume" and item.get("status") == "FAIL"
        for item in parameter_package.get("constraint_checks", [])
        if isinstance(item, dict)
    )
    if storage_volume_constraint_failed:
        constraint_gate = "engineering_constraint_fail:storage_required_volume"
        for candidate in candidates:
            if candidate is engineering_candidate:
                candidate["status"] = "ENGINEERING_FAMILY_RETAINED_CONSTRAINT_FAIL"
                candidate["candidate_eligibility"] = "CONSTRAINT_FAIL_FAMILY_ONLY"
                candidate["eligible_for_leading_candidate"] = True
                candidate["missing_gates"] = sorted(set([
                    *candidate.get("missing_gates", []), constraint_gate,
                ]))
                continue
            candidate["status"] = "REJECTED_CONSTRAINT_FAIL"
            candidate["candidate_eligibility"] = "REJECTED"
            candidate["eligible_for_leading_candidate"] = False
            candidate["eligible_for_formal_selection"] = False
            candidate["candidate_rejection_reasons"] = sorted(set([
                *candidate.get("candidate_rejection_reasons", []),
                "STORAGE_REQUIRED_VOLUME_CONSTRAINT_FAILED",
            ]))
    for rank, candidate in enumerate(candidates, 1):
        candidate["rank"] = rank
        candidate.setdefault("terminal_selection", terminal_selection)
        candidate.setdefault("knowledge_route", knowledge_route)
        candidate.setdefault("missing_gates", sorted(set(model_blockers)))
        candidate.setdefault("formal_model_gate", family_rule["formal_model_gate"])
        candidate.setdefault("prohibited_claim", family_rule["prohibited_claim"])
        candidate["selection_feature_vector_sha256"] = selection_vector.get("sha256")
    leading = next(
        (
            candidate for candidate in candidates
            if candidate.get("eligible_for_leading_candidate", True)
            and not str(candidate.get("status", "")).startswith("REJECTED_")
        ),
        None,
    )
    screening_candidate_count = sum(
        1 for candidate in candidates
        if candidate.get("candidate_eligibility") in {
            "READY_FOR_ENGINEERING_REVIEW", "SCREENING_ONLY_EVIDENCE_OPEN", "FORMAL_READY"
        }
    )
    formal_ready_candidate_count = sum(
        1 for candidate in candidates
        if candidate.get("eligible_for_formal_selection") is True
        and candidate.get("formal_model") is True
    )
    if model_status == "final_model":
        status = "FINAL_MODEL"
    elif phase_blocked:
        status = "PHYSICAL_BASIS_BLOCKED_IDENTITY_CANDIDATE_RETAINED"
    elif calculation_blocked:
        status = "CALCULATION_BLOCKED_IDENTITY_CANDIDATE_RETAINED"
    elif npsh_constraint_failed or surge_constraint_failed or storage_volume_constraint_failed:
        status = "ENGINEERING_CONSTRAINT_FAILED"
    elif supplied_model:
        status = (
            "SUPPLIED_VENDOR_CANDIDATE_REQUIRES_CLOSURE"
            if supplied_classification["is_vendor_model"]
            else "SUPPLIED_DESIGNATION_RECLASSIFIED"
        )
    elif pump_lookup and pump_lookup.get("status") == "STANDARD_SCOPE_FAILED":
        status = "STANDARD_SCOPE_FAILED"
    elif pump_lookup and pump_lookup.get("candidates"):
        status = "STANDARD_MARKING_CANDIDATES"
    elif missing_candidate_fields:
        status = "PARTIAL_ENGINEERING_CANDIDATE"
    elif defaulted_exchanger_type_screening_only:
        status = "PRELIMINARY_ENGINEERING_CANDIDATE_WITH_DEFAULTED_TYPE"
    else:
        status = "ENGINEERING_CANDIDATE_READY"
    return {
        "schema": "equipment-model-recommendation-v1",
        "status": status,
        "family_id": family_id,
        "recommendation_class": family_rule["recommendation_class"],
        "decision_policy": model_rules.get("decision_policy", "COLLECT"),
        "recommended_type": recommended_type,
        "terminal_selection": terminal_selection,
        "terminal_type_rule_registry": terminal_condition_registry,
        "terminal_type_rule_override_validation": {
            "requested_rule_id": requested_terminal_rule_id or None,
            "status": (
                "APPLIED_REGISTERED_CONDITION_RULE"
                if controlled_terminal_rule is not None
                else "REJECTED_UNKNOWN_RULE_RETAINED_DETERMINISTIC_SELECTION"
                if requested_terminal_rule_id
                else "NOT_REQUESTED"
            ),
        },
        "leading_candidate": leading,
        "candidate_count": len(candidates),
        "screening_candidate_count": screening_candidate_count,
        "formal_ready_candidate_count": formal_ready_candidate_count,
        "candidates": candidates,
        "formal_model": supplied_model if model_status == "final_model" else None,
        "formal_model_status": model_status,
        "minimum_candidate_missing_fields": missing_candidate_fields,
        "selection_execution": {
            "status": (
                "IDENTITY_CANDIDATE_RETAINED_PHYSICAL_BASIS_BLOCKED" if phase_blocked
                else "IDENTITY_CANDIDATE_RETAINED_CALCULATION_BLOCKED" if calculation_blocked
                else "EXECUTED_TYPE_SCREENING_ONLY"
                if defaulted_exchanger_type_screening_only
                and not missing_candidate_fields
                else "EXECUTED" if not missing_candidate_fields
                else "WAITING_CALCULATED_PARAMETERS"
            ),
            "execution_scope": (
                "TYPE_SCREENING_ONLY"
                if defaulted_exchanger_type_screening_only
                else "ENGINEERING_CANDIDATE"
            ),
            "formal_selection_executed": False,
            "parameter_package_schema": parameter_package.get("schema"),
            "feature_vector_sha256": selection_vector.get("sha256"),
            "context_sha256": parameter_package.get("selection_context", {}).get("sha256"),
            "input_contract": model_rules.get("selection_input_contract", "equipment-design-parameter-package-v1"),
        },
        "formal_promotion_blockers": model_blockers,
        "formal_model_gate": family_rule["formal_model_gate"],
        "prohibited_claim": family_rule["prohibited_claim"],
        "knowledge_basis": knowledge_route,
        "pump_standard_lookup": pump_lookup,
        "phase_compatibility": phase_gate,
        "deterministic": True,
        "llm_used": False,
    }


def family_field_roles(rule: dict[str, Any]) -> dict[str, list[str]]:
    """Return the deterministic role of every input field for one family."""
    roles: dict[str, set[str]] = {}

    def add(field: str, role: str) -> None:
        if field in NON_PROFILE_FIELDS or field.endswith("_path") or field.endswith("_sha256"):
            return
        roles.setdefault(field, set()).add(role)

    for field in rule.get("sizing_fields", []):
        add(field, "sizing")
    for field in rule.get("verification_fields", []):
        add(field, "verification")
    for calc_id in rule.get("calculation_rules", []):
        for field in CALCULATION_REQUIREMENTS.get(calc_id, ()):
            add(field, f"calculation_input:{calc_id}")
    return {field: sorted(values) for field, values in sorted(roles.items())}


def calculation_closure_plan(calc_id: str, params: dict[str, Any]) -> dict[str, Any]:
    alternatives: list[dict[str, Any]] = []
    raw_alternatives = CALCULATION_INPUT_ALTERNATIVES.get(
        calc_id, (CALCULATION_REQUIREMENTS.get(calc_id, ()),)
    )
    for fields in raw_alternatives:
        required = list(fields)
        if calc_id == "pressure_ratio" and params.get("pressure_basis") == "gauge":
            required.append("atmospheric_pressure_mpa")
        if calc_id == "design_pressure" and params.get("pressure_basis") == "absolute":
            required.append("atmospheric_pressure_mpa")
        missing = [field for field in required if not present(params, field)]
        alternatives.append({"fields": required, "missing_fields": missing})
    minimum = min((len(item["missing_fields"]) for item in alternatives), default=0)
    minimum_alternatives = [item for item in alternatives if len(item["missing_fields"]) == minimum]
    return {
        "calculation_id": calc_id,
        "ready": minimum == 0,
        "minimum_missing_fields": minimum_alternatives[0]["missing_fields"] if minimum_alternatives else [],
        "minimum_missing_alternatives": [item["missing_fields"] for item in minimum_alternatives],
        "input_alternatives": [item["fields"] for item in alternatives],
    }


def _unmapped_field_suggestions(unmapped: dict[str, Any]) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    alias_rows = [
        (canonical, alias, token(alias))
        for canonical, aliases in FIELD_ALIASES.items()
        for alias in aliases
    ]
    for raw_field in sorted(unmapped):
        wanted = token(raw_field)
        ranked: list[tuple[float, str, str]] = []
        for canonical, alias, normalized_alias in alias_rows:
            ratio = difflib.SequenceMatcher(None, wanted, normalized_alias).ratio()
            if ratio >= 0.45:
                ranked.append((ratio, canonical, alias))
        ranked.sort(key=lambda item: (-item[0], item[1], item[2]))
        unique: list[dict[str, Any]] = []
        seen: set[str] = set()
        for ratio, canonical, alias in ranked:
            if canonical in seen:
                continue
            seen.add(canonical)
            unique.append({"canonical_field": canonical, "matched_alias": alias, "similarity": round(ratio, 6)})
            if len(unique) == 3:
                break
        suggestions.append({"input_field": raw_field, "suggestions": unique})
    return suggestions


def _fuzzy_family_suggestions(
    value: Any, families: list[dict[str, Any]], graph_nodes: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    wanted = token(value)
    if not wanted:
        return []
    ranked: list[tuple[float, int, str, str]] = []
    for rule in families:
        names = [rule["id"], graph_nodes.get(rule["id"], {}).get("name", ""), *rule.get("aliases", [])]
        best_name = ""
        best_ratio = 0.0
        for name in names:
            ratio = difflib.SequenceMatcher(None, wanted, token(name)).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_name = str(name)
        if best_ratio >= 0.4:
            ranked.append((best_ratio, int(rule.get("priority", 9999)), rule["id"], best_name))
    ranked.sort(key=lambda item: (-item[0], item[1], item[2]))
    return [
        {
            "family_id": family_id,
            "family_name": graph_nodes.get(family_id, {}).get("name", family_id),
            "matched_name": name,
            "similarity": round(ratio, 6),
            "confirmation_required": True,
        }
        for ratio, _, family_id, name in ranked[:5]
    ]


def build_progress(
    params: dict[str, Any],
    rules: dict[str, Any],
    graph: dict[str, Any],
    match: dict[str, Any],
    *,
    normalization_conflicts: list[dict[str, Any]] | None = None,
    parameter_errors: list[dict[str, Any]] | None = None,
    unmapped: dict[str, Any] | None = None,
    calculations: list[dict[str, Any]] | None = None,
    pending: list[dict[str, Any]] | None = None,
    model_decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Add a non-terminal, explainable path for partial deterministic input.

    This layer never promotes field compatibility into confirmed identity.  It
    exposes candidates and the smallest next facts while legacy matcher status
    semantics remain unchanged.
    """
    normalization_conflicts = normalization_conflicts or []
    parameter_errors = parameter_errors or []
    unmapped = unmapped or {}
    pending = pending or []
    calculations = calculations or []
    families = rules["families"]
    family_by_id = {rule["id"]: rule for rule in families}
    graph_nodes = {node["id"]: node for node in graph["nodes"]}
    role_maps = {rule["id"]: family_field_roles(rule) for rule in families}
    support_count: dict[str, int] = {}
    for roles in role_maps.values():
        for field in roles:
            support_count[field] = support_count.get(field, 0) + 1

    identity_rows: dict[str, dict[str, Any]] = {}
    for row in match.get("candidates", []) if isinstance(match.get("candidates"), list) else []:
        if isinstance(row, str):
            identity_rows[row] = {"score": 0, "reasons": [match.get("status", "ambiguous_identity")]}
        elif isinstance(row, dict) and row.get("family_id"):
            identity_rows[str(row["family_id"])] = row
    for family_id in (match.get("strong_sources") or {}).values():
        identity_rows.setdefault(str(family_id), {"score": 0, "reasons": ["strong_identity_conflict"]})
    if match.get("status") == "MATCHED" and match.get("family_id"):
        identity_rows[str(match["family_id"])] = {
            "score": match.get("score", 0),
            "reasons": match.get("reasons", []),
        }

    provided_profile_fields = sorted(
        field for field in params
        if field not in IDENTITY_FIELDS
        and field not in NON_PROFILE_FIELDS
        and not field.endswith("_path")
        and not field.endswith("_sha256")
    )
    candidates: list[dict[str, Any]] = []
    confirmed_family_id = str(match.get("family_id", "")) if match.get("status") == "MATCHED" else ""
    for rule in families:
        family_id = rule["id"]
        if confirmed_family_id and family_id != confirmed_family_id:
            continue
        roles = role_maps[family_id]
        matched_fields = [field for field in provided_profile_fields if field in roles]
        identity = identity_rows.get(family_id, {})
        identity_score = int(identity.get("score", 0) or 0)
        specificity_score = sum(max(1, round(1000 / support_count[field])) for field in matched_fields)
        if not identity and not matched_fields:
            continue
        sizing_missing = [field for field in rule.get("sizing_fields", []) if not present(params, field)]
        calculation_plans = [calculation_closure_plan(calc_id, params) for calc_id in rule.get("calculation_rules", [])]
        candidates.append({
            "family_id": family_id,
            "family_name": graph_nodes.get(family_id, {}).get("name", family_id),
            "identity_score": identity_score,
            "identity_evidence": list(identity.get("reasons", [])),
            "field_specificity_score": specificity_score,
            "field_compatibility": [
                {"field": field, "roles": roles[field], "supporting_family_count": support_count[field]}
                for field in matched_fields
            ],
            "sizing_missing_fields": sizing_missing,
            "calculation_closure": calculation_plans,
            "priority": int(rule.get("priority", 9999)),
        })

    fuzzy_suggestions: list[dict[str, Any]] = []
    if match.get("status") == "BLOCKED_UNKNOWN_EXPLICIT_FAMILY":
        fuzzy_suggestions = _fuzzy_family_suggestions(params.get("equipment_family"), families, graph_nodes)
        existing = {item["family_id"] for item in candidates}
        for suggestion in fuzzy_suggestions:
            family_id = suggestion["family_id"]
            if family_id in existing:
                continue
            rule = family_by_id[family_id]
            candidates.append({
                "family_id": family_id,
                "family_name": suggestion["family_name"],
                "identity_score": 0,
                "identity_evidence": ["fuzzy_family_suggestion_confirmation_required"],
                "field_specificity_score": 0,
                "field_compatibility": [],
                "sizing_missing_fields": [field for field in rule.get("sizing_fields", []) if not present(params, field)],
                "calculation_closure": [calculation_closure_plan(calc_id, params) for calc_id in rule.get("calculation_rules", [])],
                "priority": int(rule.get("priority", 9999)),
            })
            existing.add(family_id)

    if not candidates:
        for rule in families:
            candidates.append({
                "family_id": rule["id"],
                "family_name": graph_nodes.get(rule["id"], {}).get("name", rule["id"]),
                "identity_score": 0,
                "identity_evidence": [],
                "field_specificity_score": 0,
                "field_compatibility": [],
                "sizing_missing_fields": [field for field in rule.get("sizing_fields", []) if not present(params, field)],
                "calculation_closure": [calculation_closure_plan(calc_id, params) for calc_id in rule.get("calculation_rules", [])],
                "priority": int(rule.get("priority", 9999)),
            })
    candidates.sort(key=lambda item: (
        -item["identity_score"],
        -item["field_specificity_score"],
        -len(item["field_compatibility"]),
        item["priority"],
        item["family_id"],
    ))
    tie_group_by_key: dict[tuple[int, int, int], int] = {}
    for item in candidates:
        tie_key = (
            item["identity_score"],
            item["field_specificity_score"],
            len(item["field_compatibility"]),
        )
        if tie_key not in tie_group_by_key:
            tie_group_by_key[tie_key] = len(tie_group_by_key) + 1
        item["candidate_tie_group"] = tie_group_by_key[tie_key]
        item["automatic_preference_allowed"] = bool(confirmed_family_id)

    positive_profile_ids = {
        item["family_id"] for item in candidates if item["field_specificity_score"] > 0
    }
    most_general_common: dict[str, Any] | None = None
    for group, general_family in GENERAL_FAMILY_GROUPS.items():
        if positive_profile_ids and positive_profile_ids == set(group):
            most_general_common = {
                "family_id": general_family,
                "family_name": graph_nodes.get(general_family, {}).get("name", general_family),
                "covers_candidates": sorted(group),
                "status": "TYPE_CANDIDATE_CONFIRMATION_REQUIRED",
            }
            break

    legacy_status = str(match.get("status", ""))
    if normalization_conflicts or parameter_errors:
        state = "INVALID_INPUT"
    elif legacy_status == "BLOCKED_IDENTITY_CONFLICT":
        state = "IDENTITY_CONFLICT"
    elif legacy_status != "MATCHED":
        state = "NEEDS_IDENTITY"
    else:
        sizing_missing = list((model_decision or {}).get("sizing_missing_fields", []))
        hard_pending = [item for item in pending if str(item.get("status", "")).startswith("BLOCKED_")]
        model_status = str((model_decision or {}).get("model_status", ""))
        if model_status == "final_model":
            state = "FINAL"
        elif sizing_missing or pending or hard_pending:
            state = "NEEDS_PARAMETER"
        elif (model_decision or {}).get("verification_missing_fields"):
            state = "NEEDS_EVIDENCE"
        else:
            state = "TYPE_SELECTED"

    next_fields: list[dict[str, Any]] = []
    seen_next: set[str] = set()

    def add_next(field: str, reason: str, priority: int, candidate_families: list[str] | None = None) -> None:
        if not field or field in seen_next or present(params, field):
            return
        seen_next.add(field)
        row: dict[str, Any] = {"field": field, "reason": reason, "priority": priority}
        if candidate_families:
            row["candidate_families"] = candidate_families
        next_fields.append(row)

    for conflict in normalization_conflicts:
        add_next(str(conflict.get("field", "")), "repair_normalization_or_unit_conflict", 0)
    for error in parameter_errors:
        code = str(error.get("code", ""))
        if code == "MISSING_EVIDENCE_PATH":
            add_next(str(error.get("field", "")), "complete_evidence_hash_path_pair", 1)
        elif code == "MISSING_EVIDENCE_SHA256":
            add_next(str(error.get("field", "")), "complete_evidence_path_hash_pair", 1)
        else:
            add_next(str(error.get("field", "")), f"repair_invalid_parameter:{code}", 1)
    if params.get("pressure_basis") == "gauge" and not present(params, "atmospheric_pressure_mpa"):
        add_next("atmospheric_pressure_mpa", "close_gauge_to_absolute_pressure_basis", 2)
    if legacy_status != "MATCHED":
        add_next("equipment_type", "confirm_equipment_family_by_exact_alias", 10)
        add_next("aspen_block_type", "confirm_equipment_family_from_aspen_semantic_block_type", 11)
        add_next("process_function", "split_candidates_by_physical_process_function", 12)
        candidate_ids = [item["family_id"] for item in candidates]
        if len(candidates) > 1:
            union_fields = sorted({field for item in candidates for field in role_maps[item["family_id"]]})
            discriminators: list[tuple[int, int, str, list[str]]] = []
            for field in union_fields:
                if present(params, field):
                    continue
                supporters = [family_id for family_id in candidate_ids if field in role_maps[family_id]]
                if 0 < len(supporters) < len(candidate_ids):
                    balance = min(len(supporters), len(candidate_ids) - len(supporters))
                    discriminators.append((-balance, len(supporters), field, supporters))
            discriminators.sort()
            for _, _, field, supporters in discriminators[:5]:
                add_next(field, "maximally_split_current_candidate_set", 20, supporters)
    else:
        for item in pending:
            for field in item.get("missing_fields", []):
                add_next(str(field), f"close_calculation:{item.get('calculation_id')}", 20)
        for field in (model_decision or {}).get("sizing_missing_fields", []):
            add_next(str(field), "complete_direct_sizing_basis", 30)
        if not (model_decision or {}).get("sizing_missing_fields") and not pending:
            for field in (model_decision or {}).get("verification_missing_fields", []):
                if not str(field).startswith(("missing_sizing:", "calculation_hard_blocker:", "gate_", "evidence_", "independent_")):
                    add_next(str(field), "close_same_equipment_verification_gate", 40)
    next_fields.sort(key=lambda item: (item["priority"], item["field"]))

    minimum_missing_sets: list[dict[str, Any]] = []
    if legacy_status != "MATCHED":
        minimum_missing_sets.append({
            "goal": "resolve_identity",
            "alternatives": [["equipment_type"], ["aspen_block_type"], ["process_function"]],
        })
    else:
        for item in pending:
            missing = list(item.get("missing_fields", []))
            if missing:
                minimum_missing_sets.append({
                    "goal": f"close_calculation:{item.get('calculation_id')}",
                    "fields": missing,
                })
        sizing_missing = list((model_decision or {}).get("sizing_missing_fields", []))
        if sizing_missing:
            minimum_missing_sets.append({"goal": "complete_direct_sizing", "fields": sizing_missing})

    conflicts: list[dict[str, Any]] = []
    if legacy_status == "BLOCKED_IDENTITY_CONFLICT":
        conflicts.append({
            "kind": "strong_identity_conflict",
            "severity": "hard",
            "sources": match.get("strong_sources", {}),
        })

    return {
        "schema": "equipment-progressive-match-v1",
        "state": state,
        "terminal": state == "FINAL",
        "deterministic": True,
        "llm_used": False,
        "candidate_count": len(candidates),
        "candidate_families": candidates,
        "most_general_common": most_general_common,
        "minimum_missing_sets": minimum_missing_sets,
        "next_field": next_fields[0] if next_fields else None,
        "next_fields": next_fields,
        "conflicts": conflicts,
        "unmapped_field_suggestions": _unmapped_field_suggestions(unmapped),
        "fuzzy_family_suggestions": fuzzy_suggestions,
        "completed_calculation_ids": [item.get("calculation_id") for item in calculations],
        "policy": {
            "field_compatibility_only_generates_candidates": True,
            "field_compatibility_never_confirms_identity": True,
            "priority_only_stabilizes_order": True,
            "multiple_candidates_retain_most_general_common": True,
        },
    }


def match_one(
    raw: dict[str, Any],
    rules: dict[str, Any],
    graph: dict[str, Any],
    *,
    model_estimate_lineage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized, normalization_conflicts, unmapped = normalize_record(raw)
    canonical = json.dumps(
        {
            "normalized": normalized,
            "model_estimate_lineage": model_estimate_lineage or {},
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    base = {
        "schema": "equipment-deterministic-match-result-v1",
        "engine_version": ENGINE_VERSION,
        "deterministic": True,
        "llm_used": bool(model_estimate_lineage),
        "input_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest().upper(),
        "normalized_input": normalized,
        "unmapped_input_fields": unmapped,
        "normalization_conflicts": normalization_conflicts,
        "input_provenance": {
            "status": "NOT_ESTABLISHED_BY_MATCHER_INPUT",
            "formal_use_allowed_by_this_matcher_alone": False,
            "required_for_formal_use": "same-case source lineage or a calling adapter evidence gate",
        },
    }
    preliminary_match = match_family(normalized, rules, graph)
    if normalization_conflicts:
        base.update({
            "status": "BLOCKED_NORMALIZATION_CONFLICT",
            "match": preliminary_match,
            "review_role": "audit_only",
            "progress": build_progress(
                normalized, rules, graph, preliminary_match,
                normalization_conflicts=normalization_conflicts, unmapped=unmapped,
            ),
        })
        return base
    parameter_errors = validate_parameters(normalized)
    effective_normalized = normalized
    ignored_parameter_diagnostics: list[dict[str, Any]] = []
    if parameter_errors:
        zero_result_fields = {"flow_m3_h", "mass_flow_kg_h", "gas_molecular_weight"}
        localizable_aspen_zero_results = (
            preliminary_match.get("status") == "MATCHED"
            and present(normalized, "aspen_block_type")
            and all(
                error.get("code") == "MUST_BE_POSITIVE"
                and error.get("field") in zero_result_fields
                and isinstance(error.get("value"), (int, float))
                and not isinstance(error.get("value"), bool)
                and float(error["value"]) == 0.0
                for error in parameter_errors
            )
        )
        if not localizable_aspen_zero_results:
            base.update({
                "status": "BLOCKED_INVALID_PARAMETERS",
                "parameter_errors": parameter_errors,
                "match": preliminary_match,
                "review_role": "audit_only",
                "progress": build_progress(
                    normalized, rules, graph, preliminary_match,
                    parameter_errors=parameter_errors, unmapped=unmapped,
                ),
            })
            return base
        effective_normalized = dict(normalized)
        for error in parameter_errors:
            effective_normalized.pop(str(error.get("field") or ""), None)
            ignored_parameter_diagnostics.append({
                **error,
                "status": "IGNORED_INACTIVE_ASPEN_RESULT_FIELD",
                "scope": "TARGET_FIELD_ONLY",
                "downstream_policy": (
                    "Keep exact Aspen equipment identity/type output; exclude the zero result "
                    "from sizing and block only calculations that require this field."
                ),
            })
    match = preliminary_match
    if match.get("status") != "MATCHED":
        base.update({
            "status": match["status"],
            "match": match,
            "review_role": "audit_only",
            "progress": build_progress(normalized, rules, graph, match, unmapped=unmapped),
        })
        return base
    family_id = match["family_id"]
    effective_normalized, family_input_diagnostics = prepare_family_effective_inputs(
        family_id,
        effective_normalized,
    )
    ignored_parameter_diagnostics.extend(family_input_diagnostics)
    rule = next(item for item in rules["families"] if item["id"] == family_id)
    nodes = {node["id"]: node for node in graph["nodes"]}
    family_node = nodes[family_id]
    fallback_normalized, design_fallbacks, fallback_lineage = apply_design_fallbacks(
        family_id,
        effective_normalized,
        rule,
    )
    model_estimate_fallbacks, model_estimate_calculation_lineage = build_model_estimate_fallbacks(
        fallback_normalized,
        model_estimate_lineage,
    )
    design_fallbacks.extend(model_estimate_fallbacks)
    fallback_lineage.update(model_estimate_calculation_lineage)
    calculations, pending, derived = run_calculations(
        rule,
        fallback_normalized,
        fallback_lineage,
    )
    # A model estimate is only a last-resort input.  When the registered
    # matcher can recompute the same target, the program result is canonical
    # even if the model supplied a different number.  Keep the rejected value
    # visible for audit, but never let it feed selection or a promotion gate.
    superseded_model_fields = {
        str(item.get("target_field"))
        for item in calculations
        if item.get("status") in {
            "CALCULATED_SUPERSEDED_MODEL_ESTIMATE_MATCH",
            "CALCULATED_SUPERSEDED_MODEL_ESTIMATE_CONFLICT",
        }
    }
    for item in model_estimate_fallbacks:
        field_id = str(item.get("field_id") or "")
        if field_id not in superseded_model_fields:
            continue
        item["state"] = "SUPERSEDED_BY_DETERMINISTIC_CALCULATION"
        item["auto_applied"] = False
        item["superseded_by"] = "registered_deterministic_calculation"
        item["effective_value"] = derived.get(field_id)
        item["warning"] = (
            "The model estimate was not used: the registered program calculation "
            "recomputed this target and has authority in the selection package."
        )
    effective_parameters = {**fallback_normalized, **derived}
    sizing_missing = [field for field in rule.get("sizing_fields", []) if not present(effective_parameters, field)]
    formal_release_package_supplied = all(
        present(effective_parameters, field)
        for field in (
            "evidence_manifest_path", "evidence_manifest_sha256",
            "audit_approval_path", "audit_approval_sha256",
        )
    ) and str(effective_parameters.get("approval_status", "")).strip().casefold() == "approved"
    calculation_hard_blockers = [
        f"calculation_hard_blocker:{item.get('calculation_id')}:{item.get('status')}"
        for item in pending if is_hard_calculation_blocker(item)
    ]
    calculation_promotion_blockers = sorted({
        (
            f"calculation_promotion_cap:{item.get('calculation_id')}:"
            f"{item.get('calculation_notice', {}).get('promotion_cap')}"
        )
        for item in calculations
        if item.get("target_field") in derived
        and item.get("adopted_as_canonical", True)
        and item.get("calculation_notice", {}).get("promotion_cap") == "TYPE_SCREENING"
    }) if not formal_release_package_supplied else []
    fallback_promotion_blockers = sorted({
        f"design_fallback:{item.get('field_id')}:{item.get('tier')}:TYPE_SCREENING"
        for item in design_fallbacks
        if item.get("state") != "SUPERSEDED_BY_DETERMINISTIC_CALCULATION"
    }) if not formal_release_package_supplied else []
    parameter_package = build_design_parameter_package(
        family_id,
        fallback_normalized,
        derived,
        rule,
        calculations,
        pending,
        design_fallbacks,
    )
    input_recommendations = build_missing_field_recommendations(
        family_id,
        parameter_package,
        design_fallbacks,
    )
    parameter_package["input_recommendations"] = input_recommendations
    engineering_constraint_blockers = sorted({
        (
            f"engineering_constraint_{str(item.get('status', 'UNKNOWN')).lower()}:"
            f"{item.get('check_id')}"
        )
        for item in parameter_package.get("constraint_checks", [])
        if (
            item.get("check_id") in {"pump_npsh_margin", "compressor_surge_margin"}
            and item.get("status") in {"FAIL", "UNKNOWN"}
        ) or (
            item.get("check_id") == "storage_required_volume"
            and item.get("status") == "FAIL"
        )
    })
    model_status, model_blockers, manifest_audit = determine_model_status(
        rule,
        effective_parameters,
        family_node,
        sizing_missing,
        calculation_hard_blockers,
        [
            *calculation_promotion_blockers,
            *fallback_promotion_blockers,
            *engineering_constraint_blockers,
        ],
    )
    phase_gate = parameter_package.get("phase_compatibility", {})
    if phase_gate.get("status") == "BLOCKED_INCOMPATIBLE_PHASE":
        model_status = "physical_basis_blocked"
        model_blockers = sorted(set([
            *model_blockers,
            (
                "physical_phase_incompatible:"
                f"{phase_gate.get('observed_phase')}->"
                f"{','.join(phase_gate.get('allowed_phases', []))}"
            ),
        ]))
    model_recommendation = build_model_recommendation(
        family_id,
        parameter_package,
        rule,
        family_node,
        graph,
        model_status,
        model_blockers,
    )
    engineering_adjustment_plan = build_engineering_adjustment_plan(
        family_id,
        effective_parameters,
        parameter_package,
        model_recommendation,
        calculations,
        pending,
    )
    selection_agent_control = build_selection_agent_control(
        family_id,
        rule,
        effective_parameters,
        parameter_package,
        model_recommendation,
        engineering_adjustment_plan,
        calculations,
        pending,
        design_fallbacks,
    )
    model_recommendation["engineering_adjustment_status"] = (
        engineering_adjustment_plan.get("status")
    )
    model_recommendation["engineering_adjustment_plan_sha256"] = (
        engineering_adjustment_plan.get("plan_sha256")
    )
    model_recommendation["recommended_system_designation"] = (
        engineering_adjustment_plan.get("configuration", {}).get(
            "candidate_model_or_designation"
        )
        if isinstance(
            engineering_adjustment_plan.get("configuration"),
            dict,
        )
        else None
    )
    model_recommendation["selection_agent_control_sha256"] = (
        selection_agent_control.get("agent_control_sha256")
    )
    leading_model_candidate = model_recommendation.get("leading_candidate") or {}
    selection_executed = (
        model_recommendation.get("selection_execution", {}).get("status") == "EXECUTED"
    )
    ready_candidates = [
        item
        for item in model_recommendation.get("candidates", [])
        if isinstance(item, dict)
        and not str(item.get("status", "")).startswith("PARTIAL_")
        and not str(item.get("status", "")).startswith("REJECTED_")
        and "CONSTRAINT_FAIL" not in str(item.get("status", ""))
        and not item.get("completeness", {}).get("missing_fields", [])
    ]
    formal_ready_candidates = [
        item
        for item in model_recommendation.get("candidates", [])
        if isinstance(item, dict)
        and item.get("eligible_for_formal_selection") is True
        and item.get("formal_model") is True
    ]
    generated_model_candidate = next(
        (
            item
            for item in ready_candidates
            if item.get("candidate_kind") in {"standard_marking", "vendor_candidate"}
        ),
        None,
    ) if selection_executed else None
    base.update(
        {
            "status": "MATCHED",
            "match": {
                "family_id": family_id,
                "family_name": match["family_name"],
                "score": match["score"],
                "reasons": match["reasons"],
                "candidate_ranking": match["candidates"],
            },
            "model_decision": {
                "policy": rule["model_policy"],
                "model_status": model_status,
                "candidate_model": effective_normalized.get("candidate_model"),
                "generated_candidate_designation": leading_model_candidate.get("designation"),
                "generated_candidate_kind": leading_model_candidate.get("candidate_kind"),
                "generated_candidate_model": (
                    generated_model_candidate.get("designation")
                    if generated_model_candidate else None
                ),
                "candidate_selection_executed": selection_executed,
                "ready_candidate_count": len(ready_candidates) if selection_executed else 0,
                "ready_candidate_count_semantics": "ready_for_screening_review_not_formal",
                "screening_candidate_count": (
                    model_recommendation.get("screening_candidate_count", 0)
                    if selection_executed else 0
                ),
                "formal_ready_candidate_count": len(formal_ready_candidates),
                "vendor_model": effective_normalized.get("vendor_model"),
                "supplied_designation_classification": classify_supplied_designation(effective_parameters),
                "sizing_missing_fields": sizing_missing,
                "verification_missing_fields": model_blockers,
                "machine_evidence_manifest": manifest_audit,
                "formula_promotion_cap": (
                    "TYPE_SCREENING" if (calculation_promotion_blockers or fallback_promotion_blockers) else None
                ),
                "formula_promotion_blockers": calculation_promotion_blockers,
                "fallback_promotion_blockers": fallback_promotion_blockers,
                "design_basis_status": (
                    "PROVISIONAL_LLM_ESTIMATE"
                    if model_estimate_fallbacks
                    else "PROVISIONAL_FALLBACK" if design_fallbacks
                    else "DIRECT_OR_DERIVED_ONLY"
                ),
                "engineering_constraint_blockers": engineering_constraint_blockers,
                "engineering_adjustment_status": (
                    engineering_adjustment_plan.get("status")
                ),
                "engineering_adjustment_plan_sha256": (
                    engineering_adjustment_plan.get("plan_sha256")
                ),
                "generated_system_designation": (
                    engineering_adjustment_plan.get(
                        "configuration", {}
                    ).get("candidate_model_or_designation")
                    if isinstance(
                        engineering_adjustment_plan.get("configuration"),
                        dict,
                    )
                    else None
                ),
                "selection_agent_control_sha256": (
                    selection_agent_control.get(
                        "agent_control_sha256"
                    )
                ),
                "parameter_package_status": parameter_package.get("status"),
                "selection_feature_vector_sha256": parameter_package.get("selection_feature_vector", {}).get("sha256"),
                "graph_required_gates": family_node.get("required_gates", []),
                "forbidden_action": "do_not_generate_or_upgrade_a_vendor_or_standard_model_without_machine-readable_same-equipment_evidence",
            },
            "model_recommendation": model_recommendation,
            "engineering_adjustment_plan": engineering_adjustment_plan,
            "selection_agent_control": selection_agent_control,
            "standard_routes": standard_routes(family_id, graph),
            "vendor_routes": vendor_routes(family_id, graph),
            "calculations": calculations,
            "calculation_notices": parameter_package.get("calculation_notices", []),
            "calculation_pending": pending,
            "derived_parameters": derived,
            "design_parameter_package": parameter_package,
            "input_recommendations": input_recommendations,
            "design_fallbacks": design_fallbacks,
            "model_estimate_inputs": model_estimate_fallbacks,
            "embedded_formula_policy": {
                "built_in_formula_notice_required": True,
                "embedded_empirical_defaults_enabled": True,
                "fallback_hierarchy": load_model_rules().get("design_fallback_policy", {}).get("hierarchy", []),
                "provisional_screening_enabled_with_explicit_or_registered_fallback_inputs": True,
                "fallback_results_formal_promotion_allowed": False,
                "silent_default_values_allowed": False,
            },
            "pre_fallback_effective_normalized_input": effective_normalized,
            "effective_normalized_input": fallback_normalized,
            "ignored_parameter_diagnostics": ignored_parameter_diagnostics,
            "review_role": "audit_only; reviewer_may_flag_conflicts_but_must_not_replace_the_deterministic_match",
            "multiple_choice_policy": rules.get("multiple_choice_policy", {}),
        }
    )
    base["progress"] = build_progress(
        effective_parameters,
        rules,
        graph,
        match,
        unmapped=unmapped,
        calculations=calculations,
        pending=pending,
        model_decision=base["model_decision"],
    )
    return base


def validate_rules(rules: dict[str, Any], graph: dict[str, Any]) -> dict[str, Any]:
    graph_families = {node["id"] for node in graph["nodes"] if node.get("type") == "equipment_family"}
    rule_families = [item["id"] for item in rules.get("families", [])]
    duplicate_family_ids = sorted({item for item in rule_families if rule_families.count(item) > 1})
    alias_owners: dict[str, list[str]] = {}
    for rule in rules.get("families", []):
        for alias in rule.get("aliases", []):
            alias_owners.setdefault(token(alias), []).append(rule["id"])
    duplicate_aliases = {alias: owners for alias, owners in alias_owners.items() if len(set(owners)) > 1}
    known_calculations = set(CALCULATION_REQUIREMENTS)
    unknown_calculations = sorted(
        {calc for rule in rules.get("families", []) for calc in rule.get("calculation_rules", [])}
        - known_calculations
    )
    try:
        model_rules = load_model_rules()
        model_family_ids = [str(item.get("family_id", "")) for item in model_rules.get("families", [])]
    except (OSError, UnicodeError, json.JSONDecodeError):
        model_rules = {}
        model_family_ids = []
    try:
        parameter_templates = load_parameter_templates()
        parameter_template_family_ids = [
            str(item.get("family_id", "")) for item in parameter_templates.get("families", [])
        ]
    except (OSError, UnicodeError, json.JSONDecodeError):
        parameter_templates = {}
        parameter_template_family_ids = []
    allowed_recommendation_classes = {
        "standard_marking", "vendor_candidate", "engineered_designation", "component_marking",
    }
    invalid_recommendation_classes = sorted({
        str(item.get("recommendation_class"))
        for item in model_rules.get("families", [])
        if item.get("recommendation_class") not in allowed_recommendation_classes
    })
    terminal_default_type_issues = [
        {
            "family_id": str(item.get("family_id", "")),
            "quality": terminal_type_name_quality(item.get("terminal_default_type")),
        }
        for item in model_rules.get("families", [])
        if not terminal_type_name_quality(item.get("terminal_default_type"))["is_concrete"]
    ]
    errors: list[str] = []
    if duplicate_family_ids:
        errors.append(f"duplicate family ids: {duplicate_family_ids}")
    if duplicate_aliases:
        errors.append(f"duplicate exact aliases: {duplicate_aliases}")
    if set(rule_families) != graph_families:
        errors.append(f"family coverage mismatch missing={sorted(graph_families-set(rule_families))} extra={sorted(set(rule_families)-graph_families)}")
    if unknown_calculations:
        errors.append(f"unknown calculations: {unknown_calculations}")
    if not INPUT_SCHEMA_PATH.exists():
        errors.append(f"missing input schema: {INPUT_SCHEMA_PATH}")
    if set(model_family_ids) != graph_families:
        errors.append(f"model recommendation coverage mismatch missing={sorted(graph_families-set(model_family_ids))} extra={sorted(set(model_family_ids)-graph_families)}")
    if len(model_family_ids) != len(set(model_family_ids)):
        errors.append("duplicate model recommendation family ids")
    if invalid_recommendation_classes:
        errors.append(f"invalid recommendation classes: {invalid_recommendation_classes}")
    if terminal_default_type_issues:
        errors.append(
            "missing or non-concrete terminal default types: "
            f"{terminal_default_type_issues}"
        )
    if set(parameter_template_family_ids) != graph_families:
        errors.append(
            "parameter template coverage mismatch "
            f"missing={sorted(graph_families-set(parameter_template_family_ids))} "
            f"extra={sorted(set(parameter_template_family_ids)-graph_families)}"
        )
    if len(parameter_template_family_ids) != len(set(parameter_template_family_ids)):
        errors.append("duplicate parameter template family ids")
    if not PUMP_STANDARD_POINTS_PATH.is_file():
        errors.append(f"missing pump standard design-point catalog: {PUMP_STANDARD_POINTS_PATH}")
    if not PIPE_STANDARD_DN_OD_PATH.is_file():
        errors.append(f"missing pipe DN/OD standard catalog: {PIPE_STANDARD_DN_OD_PATH}")
    else:
        try:
            load_pipe_standard_dn_od()
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(f"invalid pipe DN/OD standard catalog: {exc}")
    return {
        "schema": rules.get("schema"),
        "status": "PASS" if not errors else "FAIL",
        "graph_family_count": len(graph_families),
        "rule_family_count": len(rule_families),
        "model_rule_family_count": len(model_family_ids),
        "parameter_template_family_count": len(parameter_template_family_ids),
        "errors": errors,
    }


def write_output(results: list[dict[str, Any]], output: Path | None, output_format: str) -> None:
    if output_format == "json":
        payload: Any = results[0] if len(results) == 1 else {"equipment": results}
        text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    elif output_format == "jsonl":
        text = "".join(json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for item in results)
    else:
        fields = ["input_sha256", "status", "family_id", "family_name", "model_status", "generated_candidate_model", "recommended_type", "sizing_missing", "verification_missing"]
        rows = []
        for item in results:
            match = item.get("match", {})
            decision = item.get("model_decision", {})
            rows.append(
                {
                    "input_sha256": item.get("input_sha256", ""),
                    "status": item.get("status", ""),
                    "family_id": match.get("family_id", ""),
                    "family_name": match.get("family_name", ""),
                    "model_status": decision.get("model_status", ""),
                    "generated_candidate_model": decision.get("generated_candidate_model", ""),
                    "recommended_type": item.get("model_recommendation", {}).get("recommended_type", ""),
                    "sizing_missing": ";".join(decision.get("sizing_missing_fields", [])),
                    "verification_missing": ";".join(decision.get("verification_missing_fields", [])),
                }
            )
        import io
        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        text = buffer.getvalue()
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic offline equipment-family, standard-route, formula and model-status matcher. No LLM or network is used.")
    sub = parser.add_subparsers(dest="command", required=True)
    match = sub.add_parser("match", help="match one JSON object or a batch JSON/CSV file")
    match.add_argument("--input", type=Path, help="input JSON or CSV")
    match.add_argument("--json", dest="inline_json", help="inline JSON object/array")
    match.add_argument("--output", type=Path)
    match.add_argument("--format", choices=("json", "jsonl", "csv"), default="json")
    match.add_argument("--require-final", action="store_true", help="exit 3 unless every record reaches final_model")
    sub.add_parser("validate-rules", help="validate rule coverage against the machine graph")
    sub.add_parser("input-schema", help="print the canonical offline JSON input schema")
    explain = sub.add_parser("explain-family", help="print one family rule and graph node")
    explain.add_argument("family")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    rules = load_rules()
    graph = load_graph()
    if args.command == "input-schema":
        print(json.dumps(load_json(INPUT_SCHEMA_PATH), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.command == "validate-rules":
        result = validate_rules(rules, graph)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if result["status"] == "PASS" else 2
    if args.command == "explain-family":
        nodes = {node["id"]: node for node in graph["nodes"]}
        family_id = resolve_family_name(args.family, rules["families"], nodes)
        if not family_id:
            print(json.dumps({"status": "NOT_FOUND", "input": args.family}, ensure_ascii=False, indent=2))
            return 2
        rule = next(item for item in rules["families"] if item["id"] == family_id)
        print(json.dumps({"rule": rule, "graph_node": nodes[family_id], "standards": standard_routes(family_id, graph), "vendors": vendor_routes(family_id, graph)}, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    try:
        records = load_records(args.input, args.inline_json)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "INPUT_ERROR", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    results = [match_one(record, rules, graph) for record in records]
    write_output(results, args.output, args.format)
    if any(item.get("status") != "MATCHED" for item in results):
        return 2
    if args.require_final and any(item.get("model_decision", {}).get("model_status") != "final_model" for item in results):
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
