from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import result_presentation
import app_core


class ResultPresentationTests(unittest.TestCase):
    def test_formula_trace_is_visible_in_html_markdown_and_agent_answer(self) -> None:
        result = app_core.manual_match("block:PUMP", {
            "equipment_tag": "P-REPORT-TRACE",
            "process_function": "liquid pressure boosting",
            "pressure_basis": "absolute",
            "flow_m3_h": 24.0,
            "density_kg_m3": 910.0,
            "inlet_pressure_mpa": 0.15,
            "outlet_pressure_mpa": 0.45,
            "efficiency_percent": 75.0,
        })
        presentation = result_presentation.build_presentation(result)
        html = result_presentation.render_html(presentation)
        self.assertIn("公式可追溯性", html)
        self.assertIn("公式定义 SHA-256", html)
        self.assertIn("本次计算追溯 SHA-256", html)
        self.assertIn("scripts/equipment_design_match.py#run_calculations", html)
        self.assertIn("formula_pump_hydraulic_power", html)

        answer = result_presentation.build_organized_answer(presentation)
        calculations = answer["equipment"][0]["calculations"]
        traced = next(
            item
            for item in calculations
            if item["calculation_id"] == "pump_hydraulic_power"
        )
        self.assertEqual(traced["formula_id"], "A_PUMP_HYDRAULIC_POWER")
        self.assertEqual(
            traced["formula_trace"]["schema"],
            "equipment-formula-trace-v1",
        )
        markdown = result_presentation.render_organized_markdown(answer)
        self.assertIn("公式 ID：`A_PUMP_HYDRAULIC_POWER`", markdown)
        self.assertIn("公式定义 SHA-256", markdown)
        self.assertIn("输入绑定", markdown)
        self.assertIn("公式来源", markdown)
        self.assertIn("追溯缺口", markdown)

    def test_overview_schema_requires_quantity_and_visible_core_columns(self) -> None:
        schema = json.loads(
            (APP_DIR / "schemas" / "equipment_overview_table.schema.json").read_text(
                encoding="utf-8"
            )
        )
        row_schema = schema["properties"]["rows"]["items"]
        self.assertIn("quantity_and_standby", row_schema["required"])
        self.assertIn("quantity_and_standby", row_schema["properties"])
        required_columns = {
            clause["contains"]["const"]
            for clause in schema["properties"]["columns"]["allOf"]
        }
        self.assertTrue({
            "sequence_number",
            "process_section",
            "equipment_tag",
            "equipment_name",
            "quantity_and_standby",
            "equipment_type",
            "model_or_specification",
            "authority_information_coverage",
            "selection_specificity_gate",
            "formal_readiness_gate",
        }.issubset(required_columns))

    def test_authoritative_overview_core_fields_and_gates_are_visible_in_html(self) -> None:
        overview = {
            "sequence_number": 7,
            "process_section": "精馏段",
            "equipment_tag": "P-701",
            "equipment_name": "回流泵",
            "quantity_and_standby": {"installed": 2, "operating": 1, "standby": 1},
            "equipment_type": "卧式离心泵",
            "model_or_specification": "OH2-DN80-32m",
            "model_or_specification_status": "type_selected",
            "authority_structural_completeness": {
                "state": "PASS", "required": 12, "emitted": 12,
            },
            "authority_information_coverage": {
                "state": "BLOCKED",
                "required": 12,
                "covered": 11,
                "blocking_fields": ["seal_plan"],
            },
            "customer_information_coverage": {
                "state": "PASS", "blocking_fields": [],
            },
            "selection_specificity_gate": {
                "state": "PASS",
                "required_fields": ["flow_m3_h"],
                "resolved_fields": ["flow_m3_h"],
                "blocking_fields": [],
            },
            "formal_readiness_gate": {
                "state": "BLOCKED",
                "required_fields": ["vendor_curve_sha256"],
                "blocking_fields": ["vendor_curve_sha256"],
                "model_status": "type_selected",
            },
            "standards_and_versions": ["API 610"],
            "evidence_ids": ["CALC-P-701"],
            "evidence_level": {"value": "A2"},
            "customer_table_missing_fields": [],
            "algorithm_evidence_missing_fields": ["vendor_curve_sha256"],
            "model_estimate_disclosure": {"status": "NOT_USED"},
            "delivery_state": "NOT_READY",
        }
        display_rows = result_presentation.customer_overview_display_rows(overview)
        self.assertEqual(
            [row["field_id"] for row in display_rows],
            [field_id for field_id, _label in result_presentation.CUSTOMER_OVERVIEW_DISPLAY_FIELDS],
        )
        presentation = {
            "schema": "equipment-design-presentation-v1",
            "equipment": [{
                "equipment_id": "P-701",
                "header": {"family_name": "泵"},
                "status_axes": {},
                "parameter_groups": [],
                "calculation_chain": [],
                "candidates": [],
                "issues": {},
                "customer_overview": overview,
            }],
        }
        rendered = result_presentation.render_html(presentation)
        for label in (
            "序号",
            "工艺段 / 装置",
            "设备位号 / 管线号",
            "设备名称",
            "数量及备用",
            "型式 / 结构",
            "型号 / 工程规格",
            "权威表信息覆盖",
            "具体选型门",
            "正式就绪门",
        ):
            self.assertIn(label, rendered)
        for value in (
            "精馏段",
            "P-701",
            "回流泵",
            "OH2-DN80-32m",
            "状态：未通过",
            "已覆盖 11/12",
            "seal_plan",
            "vendor_curve_sha256",
        ):
            self.assertIn(value, rendered)

    def test_compact_status_labels_preserve_machine_codes_outside_the_view(self) -> None:
        self.assertEqual(result_presentation.code_label("MATCHED"), "身份已匹配")
        self.assertEqual(result_presentation.code_label("type_selected"), "型式已确定")
        self.assertEqual(
            result_presentation.code_label("NEAR_STANDARD_DESIGN_POINT"),
            "旧版近标准设计点（已停用）",
        )
        self.assertEqual(
            result_presentation.code_label("HEURISTIC_NEAREST_STANDARD_REFERENCE_POINT"),
            "启发式最近标准参考点（非性能曲线适配）",
        )

    def test_html_uses_structured_engineering_equation_chain_and_compact_numbers(self) -> None:
        presentation = {
            "schema": "equipment-design-presentation-v1",
            "equipment": [{
                "equipment_id": "P-TEST",
                "header": {"family_name": "泵"},
                "status_axes": {},
                "parameter_groups": [{
                    "title": "水力与功率计算",
                    "rows": [{
                        "field_id": "hydraulic_power_kw",
                        "label": "水力功率",
                        "symbol": "Ph",
                        "raw_value": 2.222222222,
                        "display_value": "2.22222",
                        "unit": "kW",
                        "source": {"kind": "deterministic_calculation"},
                        "state": "CALCULATED",
                        "formula_chain": {
                            "target": "hydraulic_power_kw",
                            "formula": "rho*g*Q*H",
                            "substitution": "900*9.80665*(20/3600)*45.3207/1000",
                            "answer": "2.22222 kW",
                        },
                    }],
                }],
                "calculation_chain": [{
                    "target_field": "hydraulic_power_kw",
                    "status": "CALCULATED_WITH_EXPLICIT_INPUTS",
                    "formula_chain": {
                        "target": "hydraulic_power_kw",
                        "formula": "rho*g*Q*H",
                        "substitution": "900*9.80665*(20/3600)*45.3207/1000",
                        "answer": "2.22222 kW",
                    },
                }],
                "candidates": [],
                "issues": {},
            }],
        }
        rendered = result_presentation.render_html(presentation)
        self.assertIn("P<sub>h</sub>", rendered)
        self.assertIn("ρ · g · Q · H", rendered)
        self.assertIn("2.2222", rendered)
        self.assertNotIn("hydraulic_power_kw = hydraulic_power_kw", rendered)

    def test_candidate_gates_are_not_overwritten_by_completeness(self) -> None:
        payload = {
            "schema": "equipment-deterministic-match-result-v1",
            "engine_version": "test",
            "status": "MATCHED",
            "normalized_input": {"equipment_tag": "P-TEST"},
            "match": {"family_id": "family_pump", "family_name": "泵"},
            "model_decision": {"model_status": "type_selected"},
            "model_recommendation": {
                "formal_model_gate": "model-level formal gate",
                "candidates": [
                    {
                        "candidate_id": "candidate-specific",
                        "completeness": {"missing_fields": ["head_m"]},
                        "missing_gates": ["vendor_curve_sha256", "npsha_m", "npshr_m"],
                        "formal_model_gate": "candidate-specific formal gate",
                    },
                    {
                        "candidate_id": "fallback",
                        "completeness": {"missing_fields": ["flow_m3_h"]},
                    },
                    {
                        "candidate_id": "explicit-empty",
                        "completeness": {"missing_fields": ["density_kg_m3"]},
                        "missing_gates": [],
                        "formal_model_gate": "",
                    },
                ],
            },
        }

        candidates = result_presentation.build_presentation(payload)["equipment"][0]["candidates"]
        by_id = {candidate["candidate_id"]: candidate for candidate in candidates}

        self.assertEqual(
            by_id["candidate-specific"]["missing_gates"],
            ["vendor_curve_sha256", "npsha_m", "npshr_m"],
        )
        self.assertEqual(
            by_id["candidate-specific"]["formal_model_gate"],
            "candidate-specific formal gate",
        )
        self.assertEqual(by_id["fallback"]["missing_gates"], ["flow_m3_h"])
        self.assertEqual(by_id["fallback"]["formal_model_gate"], "model-level formal gate")
        self.assertEqual(by_id["explicit-empty"]["missing_gates"], [])
        self.assertEqual(by_id["explicit-empty"]["formal_model_gate"], "")

    def test_terminal_form_source_is_visible_in_card_and_html_without_a_text_box_dump(self) -> None:
        terminal = {
            "status": "DEFAULTED_TERMINAL_TYPE_SELECTED",
            "recommended_type": "单溢流筛板塔",
            "selection_basis": "registered_default",
            "default_applied": True,
            "rule_id": "tower:registered_default:single_pass_sieve_tray",
            "assumption": "未给出专门型式条件，采用设备族登记默认型式。",
            "evidence_class": "J",
            "provisional": True,
        }
        payload = {
            "schema": "equipment-deterministic-match-result-v1",
            "engine_version": "test",
            "status": "MATCHED",
            "normalized_input": {"equipment_tag": "T-DEFAULT", "aspen_block_type": "RADFRAC"},
            "match": {"family_id": "family_tower", "family_name": "塔器"},
            "model_decision": {"model_status": "type_selected"},
            "model_recommendation": {
                "status": "PARTIAL_ENGINEERING_CANDIDATE",
                "recommended_type": "单溢流筛板塔",
                "terminal_selection": terminal,
                "candidates": [],
            },
            "design_parameter_package": {"groups": [], "calculation_chain": []},
        }

        presentation = result_presentation.build_presentation(payload)
        card = presentation["equipment"][0]
        self.assertEqual(card["terminal_selection"], terminal)
        rendered = result_presentation.render_html(presentation)
        self.assertIn("默认选定", rendered)
        self.assertIn("未给出专门型式条件，采用设备族登记默认型式。", rendered)
        self.assertIn("tower:registered_default:single_pass_sieve_tray", rendered)

    def test_hybrid_envelope_renders_only_the_active_recalculation(self) -> None:
        def result(recommended_type: str) -> dict:
            return {
                "schema": "equipment-deterministic-match-result-v1",
                "engine_version": "test",
                "deterministic": True,
                "llm_used": False,
                "status": "MATCHED",
                "normalized_input": {"equipment_tag": "P-HYBRID"},
                "match": {"family_id": "family_pump", "family_name": "泵"},
                "model_decision": {"model_status": "type_selected"},
                "model_recommendation": {
                    "status": "PARTIAL_ENGINEERING_CANDIDATE",
                    "recommended_type": recommended_type,
                    "candidates": [],
                },
                "design_parameter_package": {"groups": [], "calculation_chain": []},
            }

        presentation = result_presentation.build_presentation({
            "schema": "equipment-design-hybrid-result-v2",
            "deterministic_result": result("旧初算型式"),
            "deterministic_recalculation": result("复算生效型式"),
        })
        self.assertEqual(presentation["equipment_count"], 1)
        self.assertEqual(presentation["equipment"][0]["header"]["recommended_type"], "复算生效型式")


if __name__ == "__main__":
    unittest.main()
