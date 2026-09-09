from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path



APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import customer_delivery as delivery


CONTEXT_SHA = "A" * 64
EVIDENCE_SHA = "B" * 64


def attach_derivation_row_binding(
    item: dict,
    *,
    record_kind: str,
    identity: str,
) -> dict:
    """Make a synthetic Aspen row satisfy the real final-row contract."""

    binding = {
        "schema": "program-generated-stage1-row-binding-v1",
        "engine_version": "test",
        "deterministic": True,
        "llm_used": False,
        "program_generated": True,
        "bound_row": {
            "record_kind": record_kind,
            "identity": identity,
        },
    }
    binding["binding_sha256"] = delivery._sha256_json(binding)
    item["program_generated_record_binding"] = binding
    item["program_generated_record_sha256"] = binding[
        "binding_sha256"
    ]
    return item


def generated_profile_contract() -> dict:
    """Use the generated-profile key names agreed by the application contract."""

    return {
        "schema": "equipment-customer-output-profiles-v1",
        "version": "test-1",
        "source_artifacts": ["authoritative-original-template"],
        "authority_graph_sources": ["13-overview-table-field-schema", "30-overview-table-interface"],
        "global_output_columns": [
            {"canonical_id": "equipment_tag"},
            {"canonical_id": "equipment_name"},
            {"canonical_id": "model_or_specification"},
            {"canonical_id": "model_or_specification_status"},
            {"canonical_id": "standards_and_versions"},
            {"canonical_id": "evidence_ids"},
            {"canonical_id": "missing_information"},
            {"canonical_id": "evidence_level"},
        ],
        "canonical_field_definitions": {
            "equipment_tag": {"label": "设备位号", "requirement": "required"},
            "equipment_name": {"label": "设备名称", "requirement": "required"},
            "model_or_specification": {"label": "型号/规格", "requirement": "required"},
            "model_or_specification_status": {"label": "型号/规格状态", "requirement": "required"},
            "standards_and_versions": {"label": "采用标准及版本", "requirement": "required"},
            "evidence_ids": {"label": "证据号", "requirement": "required"},
            "missing_information": {"label": "待补资料", "requirement": "required"},
            "evidence_level": {"label": "证据等级", "requirement": "required"},
            "flow_m3_h": {"label": "流量", "unit": "m³/h", "requirement": "required"},
            "head_m": {"label": "扬程", "unit": "m", "requirement": "required"},
            "quantity": {"label": "台数", "requirement": "required"},
        },
        "algorithm_family_profile_map": {"family_pump": ["T01-PUMP"]},
        "profiles": [
            {
                "authority_section_id": "T01-PUMP",
                "title": "泵客户交付字段",
                "family_id": "family_pump",
                "conditional_subtype_tokens": [],
                "required_fields": [
                    {"canonical_id": "flow_m3_h", "source_gate": "process_basis", "selection_impact": "required"},
                    {"canonical_id": "head_m", "source_gate": "calculation_or_input", "selection_impact": "required"},
                    {"canonical_id": "quantity", "source_gate": "same_case_pfd", "selection_impact": "delivery_only"},
                ],
                "authority_sources": ["original-table:T01"],
            }
        ],
    }


def pump_result(tag: str = "P-200", *, include_evidence: bool = True) -> dict:
    evidence_rows = []
    normalized = {
        "equipment_tag": tag,
        "equipment_type": "离心泵",
        "flow_m3_h": 20.0,
        "head_m": 45.0,
    }
    if include_evidence:
        normalized.update({
            "formal_calculation_path": "evidence/formal-calculation.json",
            "formal_calculation_sha256": EVIDENCE_SHA,
        })
        evidence_rows = [
            {
                "field_id": "formal_calculation_path", "raw_value": "evidence/formal-calculation.json",
                "state": "PROVIDED", "source": {"kind": "normalized_input", "evidence_class": "U"},
            },
            {
                "field_id": "formal_calculation_sha256", "raw_value": EVIDENCE_SHA,
                "state": "PROVIDED", "source": {"kind": "normalized_input", "evidence_class": "U"},
            },
        ]
    package = {
        "schema": "equipment-design-parameter-package-v1",
        "deterministic": True,
        "llm_used": False,
        "status": "READY_FOR_CANDIDATE_MATCHING",
        "family_id": "family_pump",
        "groups": [
            {
                "group_id": "identity",
                "rows": [
                    {"field_id": "equipment_tag", "raw_value": tag, "state": "PROVIDED", "unit": None,
                     "source": {"kind": "normalized_input", "evidence_class": "U"}},
                    {"field_id": "equipment_type", "raw_value": "离心泵", "state": "PROVIDED", "unit": None,
                     "source": {"kind": "normalized_input", "evidence_class": "U"}},
                ],
            },
            {
                "group_id": "hydraulic",
                "rows": [
                    {"field_id": "flow_m3_h", "raw_value": 20.0, "state": "PROVIDED", "unit": "m³/h",
                     "source": {"kind": "normalized_input", "evidence_class": "U"}},
                    {"field_id": "head_m", "raw_value": 45.0, "state": "CALCULATED", "unit": "m",
                     "source": {"kind": "deterministic_calculation", "evidence_class": "D"},
                     "equation_chain": "H = ΔP/(ρg) = 45 = 45 m"},
                ],
            },
            {"group_id": "evidence", "rows": evidence_rows},
        ],
        "selection_context": {"values": normalized, "sha256": CONTEXT_SHA},
        "selection_feature_vector": {"missing_fields": [], "sha256": "C" * 64},
    }
    model = {
        "schema": "equipment-model-recommendation-v1",
        "deterministic": True,
        "llm_used": False,
        "family_id": "family_pump",
        "status": "STANDARD_MARKING_CANDIDATES",
        "formal_model_status": "type_selected",
        "formal_model": None,
        "recommended_type": "轴向吸入离心泵",
        "terminal_selection": {
            "status": "DEFAULTED_TERMINAL_TYPE_SELECTED",
            "selection_basis": "registered_default",
            "default_applied": True,
            "rule_id": "pump:registered_default:end_suction_centrifugal",
            "assumption": "未给专门泵型条件，采用登记默认型式。",
        },
        "leading_candidate": {"designation": "65-40-200", "formal_model": False},
        "minimum_candidate_missing_fields": [],
        "selection_execution": {"context_sha256": CONTEXT_SHA},
        "knowledge_basis": {
            "model_rule_path": "knowledge_graph/equipment_model_recommendation_rules.json",
            "model_rule_sha256": "D" * 64,
        },
    }
    return {
        "schema": "equipment-deterministic-match-result-v1",
        "deterministic": True,
        "llm_used": False,
        "status": "MATCHED",
        "input_sha256": hashlib_for(tag),
        "normalized_input": normalized,
        "derived_parameters": {"head_m": 45.0},
        "match": {"family_id": "family_pump", "family_name": "泵"},
        "model_decision": {
            "model_status": "type_selected",
            "verification_missing_fields": [],
            "sizing_missing_fields": [],
        },
        "standard_routes": [
            {
                "node_id": "std_gb_t_5662_2013",
                "number": "GB/T 5662-2013",
                "title": "轴向吸入离心泵标记、性能和尺寸",
                "standard_status": "current",
                "authority": "A2",
                "reuse_class": "direct_reuse",
                "source_layer": {"source_pdf_sha256": "E" * 64},
            }
        ],
        "design_parameter_package": package,
        "model_recommendation": model,
        "calculation_pending": [],
    }


def hashlib_for(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


class CustomerDeliveryTests(unittest.TestCase):
    def test_programmatic_gas_valve_formal_capacity_gate_does_not_erase_type_specificity(
        self,
    ) -> None:
        specification_sha256 = "A" * 64
        selector_rule_sha256 = "B" * 64
        fields = {
            "equipment_type": {"value": "多级降压低噪声笼式气体调节阀"},
            "selected_dn": {"value": 20},
            "pressure_class": {"value": "PN16"},
            "pressure_temperature_rating": {
                "value": "PN16系列候选；材料/温度额定曲线待正式核验",
                "state": "OPEN_FORMAL_EVIDENCE_GATE",
            },
            "cv": {
                "value": "OPEN_GAS_COMPRESSIBLE_AND_CHOKED_FLOW_CAPACITY_GATE",
                "state": "OPEN_FORMAL_EVIDENCE_GATE",
            },
            "body_material_grade": {"value": "WCB碳钢铸件"},
            "internals_material_grade": {
                "value": "S31603阀芯/阀笼，硬质合金堆焊"
            },
            "seat_material_grade": {"value": "金属硬密封阀座"},
            "connection_type": {"value": "RF法兰"},
            "actuator_type": {"value": "气动薄膜弹簧复位"},
            "fail_position": {"value": "FC/失气关候选"},
            "line_transition_plan": {
                "value": "入口DN20→阀体DN20→出口DN65"
            },
        }
        context = {
            "record_kind": "equipment",
            "family_ids": ["family_valve"],
            "programmatic_valve_specification": {
                "status": "PRELIMINARY_CONCRETE_SPECIFICATION_SELECTED",
                "program_specification_sha256": specification_sha256,
                "designation": (
                    "多级降压低噪声笼式气体调节阀；阀体DN20；"
                    "PN16；WCB；RF法兰；气动薄膜；FC"
                ),
                "fields": fields,
                "process_basis": {"phase": "vapor"},
                "adjacent_line_binding": {
                    "inlet_pipe_specification_sha256": "C" * 64,
                    "outlet_pipe_specification_sha256": "D" * 64,
                },
            },
            "model": {
                "recommended_type": "多级降压低噪声笼式气体调节阀",
                "leading_candidate": {
                    "candidate_id": "valve:programmatic:V-1",
                    "candidate_kind": "engineered_designation",
                    "status": "ENGINEERING_CANDIDATE_READY",
                    "candidate_eligibility": "SCREENING_ONLY_EVIDENCE_OPEN",
                    "eligible_for_leading_candidate": True,
                    "designation": (
                        "多级降压低噪声笼式气体调节阀；阀体DN20；"
                        "PN16；WCB；RF法兰；气动薄膜；FC"
                    ),
                    "program_origin": "PROGRAMMATIC_VALVE_SELECTOR",
                    "source": {
                        "kind": (
                            "deterministic_programmatic_valve_specification"
                        ),
                        "program_specification_sha256": (
                            specification_sha256
                        ),
                        "selector_rule_sha256": selector_rule_sha256,
                    },
                },
            },
        }
        cv_cell = {
            "value": fields["cv"]["value"],
            "state": "OPEN_FORMAL_EVIDENCE_GATE",
            "source": {
                "kind": "deterministic_programmatic_valve_specification"
            },
        }
        rating_cell = {
            "value": fields["pressure_temperature_rating"]["value"],
            "state": "OPEN_FORMAL_EVIDENCE_GATE",
            "source": {
                "kind": "deterministic_programmatic_valve_specification"
            },
        }

        self.assertTrue(
            delivery._programmatic_valve_preliminary_gate_resolved(
                "cv", cv_cell, context
            )
        )
        self.assertTrue(
            delivery._programmatic_valve_preliminary_gate_resolved(
                "pressure_temperature_rating",
                rating_cell,
                context,
            )
        )
        identity = delivery._concrete_selection_identity(context)
        self.assertTrue(identity["concrete_terminal_type"])
        self.assertTrue(identity["detailed_designation"])

        liquid_context = copy.deepcopy(context)
        liquid_context["programmatic_valve_specification"][
            "process_basis"
        ]["phase"] = "liquid"
        self.assertFalse(
            delivery._programmatic_valve_preliminary_gate_resolved(
                "cv", cv_cell, liquid_context
            )
        )

    def test_pipe_dn_and_pn_are_detected_after_chinese_text(self) -> None:
        designation = (
            "程序初选候选：20钢无缝工艺管道；水力DN候选DN80；"
            "独立公制OD×t候选OD89 x 4 mm；PN系列候选PN16；"
            "连接候选=对焊（BW）；候选管道等级代码=CS20-PN16-BW-CA1.5"
        )
        context = {
            "record_kind": "piping",
            "family_ids": ["family_process_piping"],
            "programmatic_pipe_specification": {
                "status": "PRELIMINARY_CONCRETE_SPECIFICATION_SELECTED",
                "designation": designation,
                "fields": {
                    "equipment_type": {"value": "20钢无缝工艺管道"},
                },
            },
            "model": {
                "recommended_type": "20钢无缝工艺管道",
                "leading_candidate": {
                    "candidate_id": "pipe:test",
                    "candidate_kind": "engineered_designation",
                    "status": "ENGINEERING_CANDIDATE_READY",
                    "candidate_eligibility": "READY_FOR_ENGINEERING_REVIEW",
                    "eligible_for_leading_candidate": True,
                    "designation": designation,
                    "source": {
                        "kind": "knowledge_graph_model_rule",
                        "model_rule_path": "knowledge_graph/rules.json",
                        "model_rule_sha256": "A" * 64,
                    },
                },
            },
        }

        identity = delivery._concrete_selection_identity(context)

        self.assertTrue(identity["designation_detail_checks"]["nominal_size_present"])
        self.assertTrue(identity["designation_detail_checks"]["pressure_class_present"])
        self.assertTrue(identity["detailed_designation"])

    def test_verified_scope_standard_design_point_is_a_specific_screening_candidate(
        self,
    ) -> None:
        context = {
            "model": {
                "leading_candidate": {
                    "candidate_id": "gbt5662:65-40-250:2900:25",
                    "candidate_kind": "standard_marking",
                    "status": "HEURISTIC_NEAREST_STANDARD_REFERENCE_POINT",
                    "candidate_eligibility": "SCREENING_ONLY_EVIDENCE_OPEN",
                    "eligible_for_leading_candidate": True,
                    "eligible_for_formal_selection": False,
                    "eligible_under_known_standard_scope": True,
                    "designation": "GB/T 5662-2013 65-40-250 @ 2900 r/min",
                    "source": {
                        "kind": "bundled_standard_reference_catalog",
                        "reuse_class": "direct_reuse_standard_design_point",
                        "catalog_path": "data/pump_gbt5662_2013_design_points.csv",
                        "catalog_sha256": "B" * 64,
                    },
                },
            },
        }

        audit = delivery._leading_candidate_audit(context)

        self.assertTrue(audit["valid_for_specificity"])
        self.assertEqual(audit["standard_scope_state"], "VERIFIED_STANDARD_SCOPE")
        self.assertEqual(
            audit["program_origin"],
            "DETERMINISTIC_STANDARD_CATALOG",
        )

    def test_aspen_piping_is_program_generated_as_a_complete_x01_row(self) -> None:
        match = pump_result("S-100")
        pipe_values = {
            "equipment_tag": "S-100",
            "line_number": "S-100",
            "source_endpoint": "P-100",
            "destination_endpoint": "E-100",
            "medium_name": "WATER (100 mol%)",
            "phase": "liquid",
            "flow_m3_h": 25.0,
            "temperature_c": 20.0,
            "operating_pressure_mpa": 0.8,
            "density_kg_m3": 998.0,
            "selected_dn": 80,
            "selected_outer_diameter_mm": 88.9,
            "selected_wall_thickness_mm": 4.0,
            "actual_velocity_m_s": 1.25,
            "reynolds_number": 138_900.0,
            "pressure_gradient_kpa_per_100m": 2.45,
        }
        match["normalized_input"] = dict(pipe_values)
        match["match"] = {
            "family_id": "family_process_piping",
            "family_name": "工业管道",
        }
        match["design_parameter_package"]["family_id"] = "family_process_piping"
        match["design_parameter_package"]["selection_context"]["values"] = dict(pipe_values)
        match["model_recommendation"]["family_id"] = "family_process_piping"
        match["model_recommendation"]["recommended_type"] = "无缝钢制工艺管道"
        match["model_recommendation"]["leading_candidate"] = {
            "designation": "DN80 / OD88.9 x 4.0 mm preliminary process pipe",
            "formal_model": False,
        }
        piping_item = attach_derivation_row_binding(
            {
                "stream_id": "S-100",
                "canonical_match_input": dict(pipe_values),
                "parameter_lineage": [{
                    "target_field": "flow_m3_h",
                    "source_file_sha256": "1" * 64,
                    "source_object_type": "stream",
                    "source_object_id": "S-100",
                    "source_field": "VOLFLMX",
                    "transform": "identity",
                    "evidence_class": "R",
                    "equation_chain": (
                        "flow_m3_h = Aspen[S-100].VOLFLMX = 25 m3/h"
                    ),
                }],
                "pfd_edge_label_data": {
                    "details": {
                        "from_block_ids": ["P-100"],
                        "to_block_ids": ["E-100"],
                    }
                },
                "match_result": match,
            },
            record_kind="piping",
            identity="S-100",
        )
        aggregate = {
            "schema": "aspen-equipment-derivation-result-v1",
            "deterministic": True,
            "llm_used": False,
            "engine_version": "test",
            "case_id": "CASE-X01",
            "source_export_path": "case-export.json",
            "source_export_sha256": "1" * 64,
            "pfd_mapping_sha256": "2" * 64,
            "equipment": [],
            "piping": [piping_item],
        }

        table = delivery.build_equipment_overview_table(aggregate)
        row = table["rows"][0]
        cells = {cell["field_id"]: cell for cell in row["authority_cells"]}

        self.assertEqual(table["row_count"], 1)
        self.assertEqual(row["record_kind"], "piping")
        self.assertEqual(row["authority_table_id"], "X01")
        self.assertEqual(len(row["authority_cells"]), 30)
        self.assertEqual(row["authority_structural_completeness"]["state"], "PASS")
        self.assertTrue(row["program_generated"])
        self.assertFalse(row["manual_postprocessing"])
        self.assertRegex(row["authority_row_sha256"], r"^[0-9A-F]{64}$")
        self.assertRegex(
            row["all_equipment_fields_sha256"],
            r"^[0-9A-F]{64}$",
        )
        self.assertRegex(table["table_sha256"], r"^[0-9A-F]{64}$")
        all_fields = {
            cell["field_id"]: cell for cell in row["all_equipment_fields"]
        }
        self.assertEqual(
            all_fields["actual_velocity_m_s"]["value"],
            1.25,
        )
        self.assertEqual(
            all_fields["reynolds_number"]["value"],
            138_900.0,
        )
        self.assertEqual(
            all_fields["pressure_gradient_kpa_per_100m"]["value"],
            2.45,
        )
        self.assertEqual(all_fields["sequence_number"]["value"], 1)
        self.assertIn(
            "CASE-X01",
            all_fields["process_section"]["value"],
        )
        self.assertEqual(
            all_fields["equipment_name"]["value"],
            "WATER管线（S-100）",
        )
        self.assertEqual(
            all_fields["quantity_and_standby"]["value"][
                "aspen_pfd_object_count"
            ],
            1,
        )
        self.assertEqual(
            all_fields["quantity_and_standby"]["value"][
                "standby_configuration"
            ],
            "NOT_MODELED_IN_ASPEN_BKP",
        )
        for field_id in (
            "sequence_number",
            "process_section",
            "equipment_name",
            "quantity_and_standby",
        ):
            self.assertNotIn(field_id, row["customer_table_missing_fields"])
        self.assertTrue(all(
            cell["program_generated"]
            and not cell["manual_postprocessing"]
            and len(cell["cell_sha256"]) == 64
            for cell in row["all_equipment_fields"]
        ))
        self.assertEqual(cells["line_number"]["value"], "S-100")
        self.assertEqual(cells["source_endpoint"]["value"], "P-100")
        self.assertEqual(cells["destination_endpoint"]["value"], "E-100")
        self.assertTrue(all(cell["program_generated"] for cell in row["authority_cells"]))
        self.assertTrue(all(not cell["manual_postprocessing"] for cell in row["authority_cells"]))
        self.assertEqual(row["selection_specificity_gate"]["state"], "BLOCKED")
        self.assertIn(
            "dynamic_viscosity_mpa_s",
            row["selection_specificity_gate"]["blocking_fields"],
        )

    def test_3_2_authority_row_keeps_the_complete_pump_table_together(self) -> None:
        source = pump_result("P-3-2-001")
        values = {
            "equipment_name": "工艺液输送泵",
            "operating_state": "连续",
            "operating_mode": "单泵",
            "shaft_power_kw": 3.5,
            "efficiency_percent": 72.0,
            "material": "S31603",
            "quantity_count": 2,
        }
        source["normalized_input"].update(values)
        source["design_parameter_package"]["selection_context"]["values"].update(values)

        table = delivery.build_equipment_overview_table(source)
        row = table["rows"][0]

        self.assertEqual(table["authority_contract"], "3-2-equipment-selection-overview-v1")
        self.assertEqual(row["authority_table_id"], "T01")
        self.assertEqual(row["authority_table_title"], "泵")
        self.assertEqual(row["authority_source"]["name"], "3-2 设备选型一览表.docx")
        self.assertEqual(
            row["authority_source"]["sha256"],
            "DC21DAB39B0ECA91F206D701B631E61994EEA709B7467B480BC97D9D4008FE9C",
        )
        self.assertEqual(row["authority_source"]["authority_state"], "SOLE_MINIMUM_OUTPUT_AUTHORITY")
        self.assertEqual(
            [cell["label"] for cell in row["authority_cells"]],
            [
                "设备位号", "名称", "型号", "类型", "流量 / （m3/h）", "扬程 / (m)",
                "状态", "方式", "轴功率 / （KW）", "效率%", "材质", "台数",
            ],
        )
        values_by_label = {cell["label"]: cell["value"] for cell in row["authority_cells"]}
        self.assertEqual(values_by_label["设备位号"], "P-3-2-001")
        self.assertEqual(values_by_label["型号"], "65-40-200")
        self.assertEqual(values_by_label["类型"], "离心泵")
        self.assertEqual(values_by_label["流量 / （m3/h）"], 20.0)
        self.assertEqual(values_by_label["扬程 / (m)"], 45.0)
        self.assertEqual(values_by_label["材质"], "S31603")
        self.assertEqual(values_by_label["台数"], 2)
        self.assertEqual(row["authority_missing_fields"], [])
        self.assertTrue(row["all_equipment_fields"])

    def test_pump_unknown_duty_and_quantity_are_open_not_defaulted(self) -> None:
        row = delivery.build_equipment_overview_table(
            pump_result("P-OPEN"),
        )["rows"][0]
        cells = {
            cell["field_id"]: cell for cell in row["authority_cells"]
        }

        for field_id, reason_code in (
            (
                "operating_state",
                "PUMP_OPERATING_DUTY_CONFIGURATION_OPEN",
            ),
            (
                "operating_mode",
                "PUMP_OPERATING_DUTY_CONFIGURATION_OPEN",
            ),
            (
                "quantity_count",
                "PROJECT_INSTALLED_AND_STANDBY_QUANTITY_OPEN",
            ),
        ):
            with self.subTest(field_id=field_id):
                cell = cells[field_id]
                self.assertIsNone(cell["value"])
                self.assertEqual(
                    cell["state"],
                    "OPEN_FORMAL_EVIDENCE_GATE",
                )
                self.assertIn("OPEN / 待补", cell["display_value"])
                self.assertEqual(
                    cell["source"]["reason_code"],
                    reason_code,
                )
                self.assertEqual(
                    cell["source"]["promotion_cap"],
                    "NOT_PROMOTABLE",
                )
                self.assertFalse(
                    cell["source"]["placeholder_is_engineering_value"],
                )
        self.assertEqual(
            row["authority_full_field_coverage"]["state"],
            "PASS",
        )
        self.assertEqual(
            row["authority_information_coverage"]["state"],
            "PROVISIONAL_WITH_OPEN_GAPS",
        )
        self.assertEqual(row["formal_readiness_gate"]["state"], "BLOCKED")

    def test_authority_alias_value_replaces_a_missing_placeholder_cell(self) -> None:
        contract = generated_profile_contract()
        contract["canonical_field_definitions"].update({
            "material": {"label": "通用材料"},
            "shell_material_grade": {"label": "壳体材料"},
        })
        contract["profiles"] = [{
            "authority_section_id": "T99",
            "title": "别名投影测试",
            "family_id": "family_pump",
            "required_fields": [
                {"canonical_id": "shell_material_grade"},
                {"canonical_id": "material"},
            ],
            "authority_overview_columns": [
                {"canonical_id": "shell_material_grade", "source_fields": ["shell_material_grade", "material"]},
            ],
        }]
        contract["algorithm_family_profile_map"] = {"family_pump": ["T99"]}
        source = pump_result("P-ALIAS")
        source["normalized_input"]["material"] = "S31603"
        source["design_parameter_package"]["selection_context"]["values"]["material"] = "S31603"

        row = delivery.build_equipment_overview_table(source, profiles=contract)["rows"][0]
        cell = row["authority_cells"][0]

        self.assertEqual(cell["field_id"], "shell_material_grade")
        self.assertEqual(cell["value"], "S31603")
        self.assertEqual(cell["source_field_id"], "material")
        self.assertNotIn("shell_material_grade", row["authority_missing_fields"])

    def test_generated_profile_shape_builds_three_serializable_objects(self) -> None:
        bundle = delivery.build_customer_delivery(
            pump_result(),
            profiles=generated_profile_contract(),
        )
        self.assertEqual(bundle["schema"], "equipment-customer-delivery-bundle-v1")
        self.assertEqual(bundle["equipment_overview_table"]["schema"], "equipment-overview-table-v1")
        self.assertEqual(bundle["equipment_family_datasheet"]["schema"], "equipment-family-datasheet-v1")
        self.assertEqual(bundle["equipment_evidence_index"]["schema"], "equipment-evidence-index-v1")
        json.dumps(bundle, ensure_ascii=False, sort_keys=True)
        self.assertFalse(bundle["llm_used"])

    def test_authority_global_ids_project_existing_matcher_values_without_false_missing(self) -> None:
        contract = generated_profile_contract()
        global_ids = [
            "equipment_tag_or_line_number", "equipment_name", "model_designation", "model_status", "standard_identity",
            "software_vendor_evidence_refs", "evidence_grade", "pending_evidence",
            "quantity_and_standby", "material_summary", "operating_condition_summary",
            "design_condition_summary", "key_specification_summary",
        ]
        contract["global_output_columns"] = [
            {"canonical_id": field_id} for field_id in global_ids
        ]
        contract["canonical_field_definitions"].update({
            field_id: {"label": field_id, "requirement": "required"}
            for field_id in global_ids
        })
        source = pump_result()
        extra = {
            "quantity": 2,
            "standby_scheme": "one-duty-one-standby",
            "material": "MATERIAL-GRADE-X",
            "design_pressure_mpa": 1.0,
        }
        source["normalized_input"].update(extra)
        source["design_parameter_package"]["selection_context"]["values"].update(extra)
        source["design_parameter_package"]["selection_feature_vector"]["values"] = {
            "flow_m3_h": 20.0,
            "head_m": 45.0,
        }
        sheet = delivery.build_equipment_family_datasheet(source, profiles=contract)["equipment"][0]
        fields = {item["field_id"]: item for item in sheet["fields"]}
        self.assertEqual(fields["equipment_tag_or_line_number"]["value"], "P-200")
        self.assertEqual(fields["model_designation"]["value"], "65-40-200")
        self.assertEqual(fields["model_status"]["value"], "type_selected")
        self.assertTrue(fields["software_vendor_evidence_refs"]["value"])
        self.assertEqual(fields["evidence_grade"]["value"], "A2")
        self.assertEqual(fields["quantity_and_standby"]["value"]["quantity"]["value"], 2)
        self.assertEqual(fields["material_summary"]["value"]["material"]["value"], "MATERIAL-GRADE-X")
        self.assertEqual(fields["operating_condition_summary"]["value"]["flow_m3_h"]["value"], 20.0)
        self.assertEqual(fields["design_condition_summary"]["value"]["design_pressure_mpa"]["value"], 1.0)
        self.assertEqual(fields["key_specification_summary"]["value"]["head_m"]["value"], 45.0)
        self.assertEqual(
            fields["standard_identity"]["state"],
            "OPEN_FORMAL_EVIDENCE_GATE",
        )
        self.assertIsNone(fields["standard_identity"]["value"])
        self.assertIn("OPEN / 待补", fields["standard_identity"]["display_value"])
        self.assertEqual(
            fields["standard_identity"]["source"]["promotion_cap"],
            "NOT_PROMOTABLE",
        )
        self.assertIn("equipment_name", fields["pending_evidence"]["value"])

    def test_profile_fields_are_retained_when_missing_and_no_value_is_invented(self) -> None:
        bundle = delivery.build_customer_delivery(pump_result(), profiles=generated_profile_contract())
        sheet = bundle["equipment_family_datasheet"]["equipment"][0]
        row = bundle["equipment_overview_table"]["rows"][0]
        fields = {item["field_id"]: item for item in sheet["fields"]}
        self.assertEqual(fields["flow_m3_h"]["value"], 20.0)
        self.assertEqual(fields["head_m"]["state"], "CALCULATED")
        self.assertIsNone(fields["equipment_name"]["value"])
        self.assertEqual(
            fields["equipment_name"]["state"],
            "OPEN_FORMAL_EVIDENCE_GATE",
        )
        self.assertIn("OPEN / 待补", fields["equipment_name"]["display_value"])
        self.assertEqual(
            fields["equipment_name"]["source"]["reason_code"],
            "REQUIRED_CUSTOMER_FIELD_NOT_AVAILABLE",
        )
        self.assertEqual(
            fields["equipment_name"]["source"]["promotion_cap"],
            "NOT_PROMOTABLE",
        )
        self.assertIsNone(fields["quantity"]["value"])
        self.assertEqual(
            fields["quantity"]["state"],
            "OPEN_FORMAL_EVIDENCE_GATE",
        )
        self.assertIn("equipment_name", sheet["missing_information"])
        self.assertIn("quantity", sheet["missing_information"])
        self.assertEqual(
            sheet["customer_full_field_coverage"]["state"],
            "PASS",
        )
        self.assertEqual(
            row["customer_full_field_coverage"]["state"],
            "PASS",
        )
        self.assertEqual(
            row["customer_information_coverage"]["state"],
            "PROVISIONAL_WITH_OPEN_GAPS",
        )
        self.assertNotEqual(
            row["formal_readiness_gate"]["state"],
            "PASS",
        )

    def test_customer_table_and_algorithm_evidence_gaps_are_separated(self) -> None:
        source = pump_result()
        source["model_recommendation"]["minimum_candidate_missing_fields"] = ["vendor_curve_sha256"]
        bundle = delivery.build_customer_delivery(source, profiles=generated_profile_contract())
        sheet = bundle["equipment_family_datasheet"]["equipment"][0]
        row = bundle["equipment_overview_table"]["rows"][0]
        self.assertIn("equipment_name", sheet["customer_table_missing_fields"])
        self.assertIn("quantity", sheet["customer_table_missing_fields"])
        self.assertNotIn("vendor_curve_sha256", sheet["customer_table_missing_fields"])
        self.assertEqual(sheet["algorithm_evidence_missing_fields"], ["vendor_curve_sha256"])
        self.assertEqual(row["customer_table_missing_fields"], sheet["customer_table_missing_fields"])
        self.assertEqual(row["algorithm_evidence_missing_fields"], ["vendor_curve_sha256"])
        self.assertEqual(
            set(sheet["missing_information"]),
            set(sheet["customer_table_missing_fields"]) | set(sheet["algorithm_evidence_missing_fields"]),
        )
        self.assertEqual(
            row["customer_information_coverage"]["state"],
            "PROVISIONAL_WITH_OPEN_GAPS",
        )
        self.assertEqual(
            row["customer_information_coverage"]["blocking_fields"],
            sheet["customer_table_missing_fields"],
        )
        self.assertNotEqual(
            row["authority_information_coverage"]["state"],
            "PASS",
        )
        self.assertEqual(
            row["authority_information_coverage"][
                "customer_table_open_gate_fields"
            ],
            sheet["customer_table_missing_fields"],
        )

    def test_overview_distinguishes_reference_route_from_adopted_standard(self) -> None:
        overview = delivery.build_equipment_overview_table(
            pump_result(), profiles=generated_profile_contract()
        )
        row = overview["rows"][0]
        self.assertEqual(row["standards_and_versions"], [])
        self.assertEqual(row["standards_and_versions_state"], "NOT_EXPLICITLY_ADOPTED")
        self.assertEqual(row["standard_reference_routes"][0]["number"], "GB/T 5662-2013")
        self.assertEqual(row["evidence_level"]["value"], "A2")
        self.assertEqual(row["model_or_specification_status"], "type_selected")
        self.assertEqual(row["terminal_selection_status"], "DEFAULTED_TERMINAL_TYPE_SELECTED")
        self.assertEqual(row["terminal_selection_basis"], "registered_default")
        self.assertTrue(row["terminal_default_applied"])
        self.assertEqual(row["terminal_rule_id"], "pump:registered_default:end_suction_centrifugal")
        self.assertEqual(row["terminal_assumption"], "未给专门泵型条件，采用登记默认型式。")
        self.assertEqual(row["model_or_specification"], "65-40-200")
        self.assertEqual(row["delivery_state"], "NOT_READY")

    def test_evidence_index_assigns_ids_only_to_present_or_reference_records(self) -> None:
        index = delivery.build_equipment_evidence_index(
            pump_result(), profiles=generated_profile_contract()
        )
        calculation = next(
            item for item in index["records"]
            if item["evidence_kind"] == "formal_calculation"
        )
        self.assertEqual(calculation["status"], "DECLARED_PATH_HASH_PAIR")
        self.assertTrue(calculation["evidence_id"].startswith("EVID-"))
        self.assertEqual(calculation["sha256"], EVIDENCE_SHA)
        self.assertTrue(all(item["record_id"].startswith("REC-") for item in index["records"]))

    def test_output_is_stably_sorted_and_repeatable(self) -> None:
        inputs = [pump_result("P-900"), pump_result("P-100")]
        first = delivery.build_customer_delivery(inputs, profiles=generated_profile_contract())
        second = delivery.build_customer_delivery(copy.deepcopy(inputs), profiles=generated_profile_contract())
        self.assertEqual(first, second)
        tags = [row["equipment_tag"] for row in first["equipment_overview_table"]["rows"]]
        self.assertEqual(tags, ["P-100", "P-900"])

    def test_separate_package_and_model_nodes_are_supported_and_hash_bound(self) -> None:
        source = pump_result()
        package = source.pop("design_parameter_package")
        model = source.pop("model_recommendation")
        bundle = delivery.build_customer_delivery(
            source,
            package,
            model,
            profiles=generated_profile_contract(),
        )
        self.assertEqual(bundle["equipment_overview_table"]["row_count"], 1)
        bad_model = copy.deepcopy(model)
        bad_model["selection_execution"]["context_sha256"] = "F" * 64
        with self.assertRaises(delivery.CustomerDeliveryError):
            delivery.build_customer_delivery(
                source, package, bad_model, profiles=generated_profile_contract()
            )

    def test_ambiguous_subtype_profiles_are_unioned_instead_of_selected(self) -> None:
        contract = generated_profile_contract()
        contract["algorithm_family_profile_map"] = {
            "family_pump": ["PUMP-A", "PUMP-B"],
        }
        contract["profiles"] = [
            {
                "authority_section_id": "PUMP-A", "family_id": "family_pump",
                "conditional_subtype_tokens": ["type-a"],
                "required_fields": [{"canonical_id": "field_a", "label": "A"}],
            },
            {
                "authority_section_id": "PUMP-B", "family_id": "family_pump",
                "conditional_subtype_tokens": ["type-b"],
                "required_fields": [{"canonical_id": "field_b", "label": "B"}],
            },
        ]
        source = pump_result()
        source["normalized_input"].pop("equipment_type")
        source["design_parameter_package"]["groups"][0]["rows"] = [
            source["design_parameter_package"]["groups"][0]["rows"][0]
        ]
        sheet = delivery.build_equipment_family_datasheet(source, profiles=contract)["equipment"][0]
        field_ids = {item["field_id"] for item in sheet["fields"]}
        self.assertIn("field_a", field_ids)
        self.assertIn("field_b", field_ids)
        self.assertEqual(sheet["profile_resolution"], "MOST_GENERAL_PROFILE_UNION")

    def test_non_deterministic_or_llm_result_is_rejected(self) -> None:
        source = pump_result()
        source["llm_used"] = True
        with self.assertRaises(delivery.CustomerDeliveryError):
            delivery.build_customer_delivery(source, profiles=generated_profile_contract())

    def test_controlled_model_estimate_is_fully_disclosed_and_schema_valid(self) -> None:
        source = pump_result()
        source["llm_used"] = True
        source["model_estimate_inputs"] = [{
            "field_id": "efficiency_percent",
            "value": 70.0,
            "tier": "LLM_LAST_RESORT_ENGINEERING_ESTIMATE",
            "state": "ESTIMATED",
            "source_kind": "llm_last_resort_engineering_estimate",
            "inference_basis": "conservative_screening_assumption",
            "assumptions": ["Preliminary clean-liquid service only."],
            "context_refs": ["ctx:missing_input_registry"],
            "evidence_class": "J",
            "result_status": "PROVISIONAL",
            "promotion_cap": "TYPE_SCREENING",
            "auto_applied": True,
            "overwrite_allowed": False,
            "target_unit": "%",
            "lower_bound": 50.0,
            "upper_bound": 85.0,
            "registered_allowed_values": [],
            "registry_id": None,
            "confidence": "low",
            "sensitivity_note": "Recalculate power across the stated efficiency bounds.",
            "warning": "Model estimate for preliminary screening only.",
        }]
        bundle = delivery.build_customer_delivery(source, profiles=generated_profile_contract())
        estimate = bundle["equipment_family_datasheet"]["equipment"][0]["model_estimate_disclosure"]["estimates"][0]
        self.assertTrue(bundle["llm_used"])
        self.assertEqual(estimate["evidence_class"], "J")
        self.assertEqual(estimate["result_status"], "PROVISIONAL")
        self.assertEqual((estimate["lower_bound"], estimate["upper_bound"]), (50.0, 85.0))
        self.assertEqual(estimate["context_refs"], ["ctx:missing_input_registry"])
        for schema_name in (
            "equipment_customer_delivery_bundle.schema.json",
            "equipment_overview_table.schema.json",
            "equipment_family_datasheet.schema.json",
            "equipment_evidence_index.schema.json",
        ):
            schema = json.loads((APP_DIR / "schemas" / schema_name).read_text(encoding="utf-8"))
            required = set(schema["$defs"]["estimate"]["required"])
            self.assertTrue({
                "evidence_class", "result_status", "promotion_cap", "inference_basis",
                "assumptions", "context_refs", "lower_bound", "upper_bound",
                "registered_allowed_values", "registry_id", "confidence", "sensitivity_note",
            }.issubset(required))

    def test_fallback_profiles_cover_all_current_algorithm_families(self) -> None:
        fallback = delivery.normalise_output_profiles(delivery.fallback_output_profiles())
        family_ids = {
            family_id
            for profile in fallback["profiles"]
            for family_id in profile["family_ids"]
        }
        self.assertEqual(family_ids, set(delivery.FALLBACK_FAMILY_FIELDS))
        self.assertEqual(len(family_ids), 17)

    def test_current_canonical_profile_file_is_compatible_when_present(self) -> None:
        if not delivery.DEFAULT_PROFILE_PATH.is_file():
            self.skipTest("canonical profile file has not been generated yet")
        frozen_raw = json.loads(delivery.DEFAULT_PROFILE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(len(frozen_raw["profiles"]), 19)
        self.assertEqual(len(frozen_raw["canonical_field_definitions"]), 248)
        self.assertEqual(len(frozen_raw["algorithm_family_profile_map"]), 17)
        frozen_profile = delivery.load_customer_output_profiles()
        self.assertEqual(len(frozen_profile["profiles"]), 20)
        self.assertEqual(len(frozen_profile["field_definitions"]), 248)
        sheet = delivery.build_equipment_family_datasheet(pump_result())["equipment"][0]
        fields = {item["field_id"]: item for item in sheet["fields"]}
        self.assertEqual(sheet["profile_ids"], ["T01"])
        self.assertNotEqual(fields["model_designation"]["state"], "MISSING")
        self.assertNotEqual(fields["model_status"]["state"], "MISSING")
        self.assertIn("software_vendor_evidence_refs", fields)
        self.assertIn("pending_evidence", fields)

    def test_default_profiles_deliver_tower_and_rplug_screening_fields(
        self,
    ) -> None:
        if not delivery.DEFAULT_PROFILE_PATH.is_file():
            self.skipTest("canonical profile file has not been generated yet")

        def equipment_item(
            tag: str,
            family_id: str,
            values: dict,
        ) -> dict:
            match = pump_result(tag)
            delivered_values = dict(values)
            if family_id == "family_tower":
                # Reproduce the legacy leakage risk: a registered 600 mm
                # default and a preliminary layout height existed beside the
                # explicitly named tower screening fields.
                delivered_values.update({
                    "inner_diameter_mm": 600.0,
                    "height_mm": values["tower_height_screening_mm"],
                })
            match["normalized_input"] = {
                "equipment_tag": tag,
                **delivered_values,
            }
            match["match"] = {
                "family_id": family_id,
                "family_name": family_id,
            }
            match["design_parameter_package"]["family_id"] = family_id
            match["design_parameter_package"]["selection_context"][
                "values"
            ] = {
                "equipment_tag": tag,
                **delivered_values,
            }
            match["model_recommendation"]["family_id"] = family_id
            item = {
                "aspen_block_id": tag,
                "canonical_match_input": {
                    "equipment_tag": tag,
                    **delivered_values,
                },
                "parameter_lineage": [
                    {
                        "target_field": field_id,
                        "source_file_sha256": "1" * 64,
                        "source_object_type": (
                            "tower_preliminary_designer"
                            if family_id == "family_tower"
                            else "rplug_preliminary_designer"
                        ),
                        "source_object_id": tag,
                        "source_field": "programmatic_screening",
                        "transform": "deterministic_preliminary_screening",
                        "evidence_class": "J",
                        "promotion_cap": "TYPE_SCREENING",
                        "equation_chain": (
                            f"{field_id}=programmatic_screening"
                        ),
                    }
                    for field_id in delivered_values
                ],
                "match_result": match,
            }
            return attach_derivation_row_binding(
                item,
                record_kind="equipment",
                identity=tag,
            )

        tower_values = {
            "tower_diameter_screening_mm": 1800.0,
            "tower_height_screening_mm": 22500.0,
            "formula_only_shell_thickness_mm": 8.2,
            "formula_only_head_thickness_mm": 7.9,
            "nominal_shell_wall_thickness_selected": False,
            "nominal_head_wall_thickness_selected": False,
        }
        rplug_values = {
            "active_tube_inner_diameter_mm": 76.3,
            "active_tube_length_screening_mm": 3000.0,
            "one_tube_geometric_screening_volume_m3": 0.0137,
        }
        aggregate = {
            "schema": "aspen-equipment-derivation-result-v1",
            "deterministic": True,
            "llm_used": False,
            "engine_version": "test",
            "case_id": "CASE-SUPPLEMENTAL-DELIVERY",
            "source_export_path": "case-export.json",
            "source_export_sha256": "1" * 64,
            "pfd_mapping_sha256": "2" * 64,
            "equipment": [
                equipment_item("T-1", "family_tower", tower_values),
                equipment_item(
                    "R-1",
                    "family_reactor_vessel_separator",
                    rplug_values,
                ),
            ],
            "piping": [],
        }

        sheets = delivery.build_equipment_family_datasheet(aggregate)[
            "equipment"
        ]
        by_tag = {sheet["equipment_tag"]: sheet for sheet in sheets}
        tower_fields = {
            item["field_id"]: item for item in by_tag["T-1"]["fields"]
        }
        reactor_fields = {
            item["field_id"]: item for item in by_tag["R-1"]["fields"]
        }
        for field_id in tower_values:
            self.assertNotIn(field_id, tower_fields)
        for field_id, value in rplug_values.items():
            self.assertIn(field_id, reactor_fields)
            self.assertEqual(reactor_fields[field_id]["value"], value)
        self.assertEqual(
            tower_fields["diameter_mm"]["state"],
            "OPEN_FORMAL_EVIDENCE_GATE",
        )
        self.assertIsNone(tower_fields["diameter_mm"]["value"])
        self.assertEqual(
            tower_fields["height_mm"]["state"],
            "OPEN_FORMAL_EVIDENCE_GATE",
        )
        self.assertIsNone(tower_fields["height_mm"]["value"])
        self.assertEqual(
            tower_fields["height_mm"]["source"]["reason_code"],
            "FORMAL_GEOMETRY_NOT_AVAILABLE_SCREENING_ALIAS_REJECTED",
        )
        self.assertEqual(
            reactor_fields["diameter_mm"]["state"],
            "OPEN_FORMAL_EVIDENCE_GATE",
        )
        self.assertEqual(
            reactor_fields["required_total_reactor_volume_m3"]["state"],
            "OPEN_FORMAL_EVIDENCE_GATE",
        )
        overview = delivery.build_equipment_overview_table(aggregate)
        tower_row = next(
            row for row in overview["rows"]
            if row["equipment_tag"] == "T-1"
        )
        self.assertTrue(tower_row["customer_table_missing_fields"])
        self.assertEqual(
            tower_row["customer_information_coverage"]["state"],
            "PROVISIONAL_WITH_OPEN_GAPS",
        )
        self.assertNotEqual(
            tower_row["authority_information_coverage"]["state"],
            "PASS",
        )
        self.assertEqual(
            tower_row["authority_information_coverage"][
                "customer_table_open_gate_fields"
            ],
            tower_row["customer_table_missing_fields"],
        )
        authority_cells = {
            cell["field_id"]: cell
            for cell in tower_row["authority_cells"]
        }
        self.assertIsNone(authority_cells["diameter_mm"]["value"])
        self.assertEqual(
            authority_cells["diameter_mm"]["state"],
            "OPEN_FORMAL_EVIDENCE_GATE",
        )
        self.assertEqual(
            authority_cells["diameter_mm"]["source"]["reason_code"],
            "FORMAL_GEOMETRY_NOT_AVAILABLE_SCREENING_ALIAS_REJECTED",
        )
        self.assertIsNone(authority_cells["tower_total_height_m"]["value"])
        self.assertEqual(
            authority_cells["tower_total_height_m"]["state"],
            "OPEN_FORMAL_EVIDENCE_GATE",
        )
        self.assertEqual(
            tower_row["authority_full_field_coverage"]["state"],
            "PASS",
        )
        self.assertEqual(
            tower_row["customer_full_field_coverage"]["state"],
            "PASS",
        )
        self.assertEqual(
            tower_row["formal_readiness_gate"]["state"],
            "BLOCKED",
        )

    def test_pfd_temperature_alias_keeps_aspen_d_lineage_in_customer_cell(
        self,
    ) -> None:
        match = pump_result("S-1")
        values = {
            "equipment_tag": "S-1",
            "line_number": "S-1",
            "equipment_type": "碳钢无缝工艺管道",
            "temperature_c": 104.44444444444446,
        }
        match["normalized_input"] = dict(values)
        match["design_parameter_package"]["family_id"] = (
            "family_process_piping"
        )
        match["design_parameter_package"]["selection_context"]["values"] = (
            dict(values)
        )
        match["model_recommendation"]["family_id"] = (
            "family_process_piping"
        )
        match["match"] = {
            "family_id": "family_process_piping",
            "family_name": "工艺管道",
        }
        lineage = {
            "target_field": "operating_temperature_c",
            "value": 104.44444444444446,
            "unit": "C",
            "source_path": r"\Data\Streams\S-1\Output\TEMP_OUT\MIXED",
            "source_file_path": "case-export.json",
            "source_file_sha256": "1" * 64,
            "source_object_type": "stream",
            "source_object_id": "S-1",
            "source_field": "TEMP_OUT",
            "origin": "ASPEN_DERIVED",
            "evidence_scope": "ASPEN_PROCESS_SIDE",
            "evidence_class": "D",
            "promotion_cap": "PROCESS_SIDE_ONLY",
            "result_status": "DERIVED",
        }
        piping_item = attach_derivation_row_binding(
            {
                "stream_id": "S-1",
                "canonical_match_input": dict(values),
                "parameter_lineage": [lineage],
                "match_result": match,
            },
            record_kind="piping",
            identity="S-1",
        )
        aggregate = {
            "schema": "aspen-equipment-derivation-result-v1",
            "deterministic": True,
            "llm_used": False,
            "engine_version": "test",
            "case_id": "CASE-PFD-LINEAGE",
            "source_export_path": "case-export.json",
            "source_export_sha256": "1" * 64,
            "pfd_mapping_sha256": "2" * 64,
            "equipment": [],
            "piping": [piping_item],
        }
        contract = generated_profile_contract()
        contract["algorithm_family_profile_map"] = {
            "family_process_piping": ["T-PIPE"],
        }
        contract["profiles"] = [{
            "authority_section_id": "T-PIPE",
            "title": "管线客户字段",
            "family_id": "family_process_piping",
            "conditional_subtype_tokens": [],
            "required_fields": [{
                "canonical_id": "temperature_c",
                "aliases": [
                    "temperature_c",
                    "operating_temperature_c",
                ],
                "source_gate": "process_basis",
                "selection_impact": "candidate_selection",
            }],
            "authority_sources": ["test:T-PIPE"],
        }]

        sheet = delivery.build_equipment_family_datasheet(
            aggregate,
            profiles=contract,
        )["equipment"][0]
        temperature = next(
            cell for cell in sheet["fields"]
            if cell["field_id"] == "temperature_c"
        )
        self.assertEqual(temperature["value"], 104.44444444444446)
        self.assertEqual(temperature["state"], "DERIVED_FROM_ASPEN")
        self.assertEqual(
            temperature["source"]["kind"],
            "aspen_parameter_lineage_projection",
        )
        self.assertEqual(temperature["source"]["evidence_class"], "D")
        self.assertEqual(
            temperature["source"]["promotion_cap"],
            "PROCESS_SIDE_ONLY",
        )
        self.assertEqual(
            temperature["source"]["source_path"],
            r"\Data\Streams\S-1\Output\TEMP_OUT\MIXED",
        )
        self.assertEqual(
            temperature["source"]["lineage_target_field"],
            "operating_temperature_c",
        )
        self.assertEqual(
            temperature["source"]["lineage_projection_kind"],
            "REGISTERED_CANONICAL_ALIAS",
        )
        self.assertEqual(
            temperature["source"]["aspen_parameter_lineage"],
            lineage,
        )

    def test_package_row_evidence_is_capped_by_aspen_lineage(self) -> None:
        lineage = {
            "target_field": "head_m",
            "evidence_class": "J",
            "promotion_cap": "TYPE_SCREENING",
            "equation_chain": "head_m=program_screen",
        }
        cell = delivery._source_cell(
            "head_m",
            {
                "rows": {
                    "head_m": {
                        "raw_value": 45.0,
                        "unit": "m",
                        "state": "CALCULATED",
                        "source": {
                            "kind": "design_parameter_package",
                            "evidence_class": "D",
                            "promotion_cap": "FORMAL",
                        },
                    },
                },
                "values": {"head_m": 45.0},
                "result": {"derived_parameters": {"head_m": 45.0}},
                "aspen_parameter_lineage": {"head_m": lineage},
                "aspen_source_binding": {},
                "aspen_delivery_values": {},
                "programmatic_pipe_specification": {},
                "programmatic_valve_specification": {},
            },
        )
        self.assertIsNotNone(cell)
        assert cell is not None
        self.assertEqual(cell["source"]["evidence_class"], "J")
        self.assertEqual(
            cell["source"]["promotion_cap"],
            "TYPE_SCREENING",
        )
        self.assertEqual(
            cell["source"]["upstream_evidence_class"],
            "D",
        )

    def test_family_without_dedicated_authority_profile_keeps_global_columns(self) -> None:
        if not delivery.DEFAULT_PROFILE_PATH.is_file():
            self.skipTest("canonical profile file has not been generated yet")
        source = pump_result()
        source["match"] = {"family_id": "family_agitator", "family_name": "搅拌设备"}
        source["design_parameter_package"]["family_id"] = "family_agitator"
        source["model_recommendation"]["family_id"] = "family_agitator"
        sheet = delivery.build_equipment_family_datasheet(source)["equipment"][0]
        self.assertEqual(sheet["profile_ids"], ["__common_delivery__"])
        self.assertTrue(sheet["fields"])
        self.assertIn("model_designation", {item["field_id"] for item in sheet["fields"]})

    def test_frozen_meipass_root_loads_bundled_profile(self) -> None:
        """PyInstaller must resolve graph assets from sys._MEIPASS, not source paths."""

        frozen_root = delivery.PACKAGE_ROOT
        profile_path = frozen_root / "knowledge_graph" / "equipment_customer_output_profiles.json"
        module_name = "customer_delivery_frozen_path_test"
        previous_meipass = getattr(sys, "_MEIPASS", None)
        had_meipass = hasattr(sys, "_MEIPASS")
        try:
            sys._MEIPASS = str(frozen_root)
            spec = importlib.util.spec_from_file_location(module_name, delivery.__file__)
            self.assertIsNotNone(spec)
            self.assertIsNotNone(spec.loader)
            frozen_delivery = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = frozen_delivery
            spec.loader.exec_module(frozen_delivery)

            self.assertEqual(frozen_delivery.PACKAGE_ROOT, frozen_root)
            self.assertEqual(frozen_delivery.APP_DIR, frozen_root / "app")
            self.assertEqual(frozen_delivery.DEFAULT_PROFILE_PATH, profile_path)
            loaded = frozen_delivery.load_customer_output_profiles()
            self.assertEqual(loaded["schema"], "equipment-customer-output-profiles-v1")
            self.assertEqual(len(loaded["profiles"]), 20)
            self.assertEqual(len(loaded["field_definitions"]), 248)
        finally:
            sys.modules.pop(module_name, None)
            if had_meipass:
                sys._MEIPASS = previous_meipass
            else:
                delattr(sys, "_MEIPASS")

    def test_module_contains_no_reference_project_values(self) -> None:
        source = Path(delivery.__file__).read_text(encoding="utf-8")
        self.assertNotIn("DMSO", source)
        self.assertNotIn("P0101", source)

    def test_authoritative_profile_has_reviewed_missing_output_fields(self) -> None:
        raw = json.loads(delivery.DEFAULT_PROFILE_PATH.read_text(encoding="utf-8"))
        profiles = {
            profile["authority_section_id"]: {
                field["canonical_id"] for field in profile["required_fields"]
            }
            for profile in raw["profiles"]
        }
        required = {
            "T01": {"special_requirements"},
            "T02": {"motor_power_kw", "total_power_kw", "shaft_power_kw"},
            "T07": {"protective_layer", "total_mass_kg"},
            "T08": {"protective_layer", "total_mass_kg"},
            "T09": {"protective_layer", "total_mass_kg"},
            "T10": {"loading_coefficient", "rotational_speed_rpm", "total_mass_kg"},
            "T11": {"equipment_drawing_number", "total_mass_kg"},
            "T12": {"equipment_drawing_number", "tubesheet_thickness_mm", "total_mass_kg"},
            "T13": {"total_mass_kg"},
            "T14": {"equipment_drawing_number", "tube_or_plate_count", "shell_pass_count"},
        }
        for profile_id, field_ids in required.items():
            with self.subTest(profile_id=profile_id):
                self.assertLessEqual(field_ids, profiles[profile_id])

    def test_compressor_motor_and_total_power_never_fall_back_to_shaft_power(self) -> None:
        source = pump_result("C-200")
        source["match"] = {"family_id": "family_compressor", "family_name": "压缩机"}
        source["normalized_input"].update({
            "equipment_type": "离心式压缩机",
            "shaft_power_kw": 12.5,
        })
        source["design_parameter_package"]["family_id"] = "family_compressor"
        source["design_parameter_package"]["selection_context"]["values"].update({
            "equipment_type": "离心式压缩机",
            "shaft_power_kw": 12.5,
        })
        source["model_recommendation"]["family_id"] = "family_compressor"
        sheet = delivery.build_equipment_family_datasheet(source)["equipment"][0]
        fields = {field["field_id"]: field for field in sheet["fields"]}
        self.assertEqual(fields["shaft_power_kw"]["value"], 12.5)
        self.assertEqual(
            fields["motor_power_kw"]["state"],
            "OPEN_FORMAL_EVIDENCE_GATE",
        )
        self.assertIsNone(fields["motor_power_kw"]["value"])
        self.assertIn(
            "OPEN / 待补",
            fields["motor_power_kw"]["display_value"],
        )
        self.assertEqual(
            fields["total_power_kw"]["state"],
            "OPEN_FORMAL_EVIDENCE_GATE",
        )
        self.assertIsNone(fields["total_power_kw"]["value"])
        self.assertEqual(
            sheet["customer_full_field_coverage"]["state"],
            "PASS",
        )

    def test_static_mixer_slash_tokens_are_explicit_not_applicable(self) -> None:
        source = pump_result("M-200")
        source["match"] = {"family_id": "family_static_mixer", "family_name": "静态混合器"}
        source["normalized_input"].update({
            "equipment_type": "静态混合器",
            "loading_coefficient": "/",
            "rotational_speed_rpm": "/",
        })
        source["design_parameter_package"]["family_id"] = "family_static_mixer"
        source["design_parameter_package"]["selection_context"]["values"].update({
            "equipment_type": "静态混合器",
            "loading_coefficient": "/",
            "rotational_speed_rpm": "/",
        })
        source["model_recommendation"]["family_id"] = "family_static_mixer"
        sheet = delivery.build_equipment_family_datasheet(source)["equipment"][0]
        fields = {field["field_id"]: field for field in sheet["fields"]}
        for field_id in ("loading_coefficient", "rotational_speed_rpm"):
            with self.subTest(field_id=field_id):
                self.assertEqual(fields[field_id]["state"], "NOT_APPLICABLE")
                self.assertIsNone(fields[field_id]["value"])
                self.assertEqual(
                    fields[field_id]["source"]["declared_not_applicable_token"], "/"
                )
                self.assertNotIn(field_id, sheet["customer_table_missing_fields"])

    def test_drawing_number_and_total_mass_are_projected_to_datasheet_and_overview(self) -> None:
        source = pump_result("R-200")
        source["match"] = {
            "family_id": "family_reactor_vessel_separator",
            "family_name": "反应器/容器/分离器",
        }
        values = {
            "equipment_type": "列管式反应器",
            "equipment_drawing_number": "DWG-CURRENT-001",
            "tubesheet_thickness_mm": 32.0,
            "total_mass_kg": 1200.0,
        }
        source["normalized_input"].update(values)
        source["design_parameter_package"]["family_id"] = "family_reactor_vessel_separator"
        source["design_parameter_package"]["selection_context"]["values"].update(values)
        source["model_recommendation"]["family_id"] = "family_reactor_vessel_separator"
        bundle = delivery.build_customer_delivery(source)
        sheet = bundle["equipment_family_datasheet"]["equipment"][0]
        fields = {field["field_id"]: field for field in sheet["fields"]}
        self.assertEqual(fields["equipment_drawing_number"]["value"], "DWG-CURRENT-001")
        self.assertEqual(fields["tubesheet_thickness_mm"]["value"], 32.0)
        self.assertEqual(fields["total_mass_kg"]["value"], 1200.0)
        overview = bundle["equipment_overview_table"]
        self.assertIn("equipment_drawing_number", overview["columns"])
        self.assertIn("total_mass_kg", overview["columns"])
        self.assertEqual(overview["rows"][0]["equipment_drawing_number"], "DWG-CURRENT-001")
        self.assertEqual(overview["rows"][0]["total_mass_kg"], 1200.0)

    def test_terminal_type_populates_the_unified_overview_field_when_raw_type_is_absent(self) -> None:
        source = pump_result("P-TERMINAL-ONLY")
        source["normalized_input"].pop("equipment_type")
        source["design_parameter_package"]["selection_context"]["values"].pop("equipment_type", None)
        source["design_parameter_package"]["groups"][0]["rows"] = [
            row
            for row in source["design_parameter_package"]["groups"][0]["rows"]
            if row.get("field_id") != "equipment_type"
        ]

        bundle = delivery.build_customer_delivery(source)
        sheet = bundle["equipment_family_datasheet"]["equipment"][0]
        fields = {field["field_id"]: field for field in sheet["fields"]}
        overview_row = bundle["equipment_overview_table"]["rows"][0]
        unified_fields = {
            field["field_id"]: field for field in overview_row["all_equipment_fields"]
        }

        self.assertEqual(fields["equipment_type"]["value"], "轴向吸入离心泵")
        self.assertEqual(fields["equipment_type"]["state"], "DETERMINISTIC_TERMINAL_TYPE")
        self.assertNotIn("equipment_type", sheet["customer_table_missing_fields"])
        self.assertEqual(unified_fields["equipment_type"]["value"], "轴向吸入离心泵")
        self.assertEqual(overview_row["equipment_type"], "轴向吸入离心泵")


if __name__ == "__main__":
    unittest.main()
