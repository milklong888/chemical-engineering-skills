from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = APP_DIR.parent
SCRIPTS_DIR = PACKAGE_ROOT / "scripts"
for path in (APP_DIR, SCRIPTS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import app_core
import customer_delivery
import derivation_workbench
import equipment_design_agent
import result_presentation
from equipment_design_app import EquipmentDesignApi


class EngineeringAdjustmentWorkbenchTests(unittest.TestCase):
    def test_large_exchanger_has_concrete_parallel_plan(self) -> None:
        result = app_core.manual_match(
            "block:HEATX",
            {
                "equipment_tag": "E-LARGE",
                "heat_duty_kw": 1000,
                "heat_transfer_area_m2": 1350,
            },
        )["result"]
        plan = result["engineering_adjustment_plan"]
        configuration = plan["configuration"]
        self.assertEqual(
            plan["status"],
            "RECOMMENDED_ALGORITHMIC_MODIFICATION",
        )
        self.assertEqual(
            configuration["parallel_train_count_estimate"],
            3,
        )
        self.assertEqual(
            configuration["operating_unit_count_estimate"],
            3,
        )
        self.assertEqual(
            configuration["per_unit_target"][
                "heat_transfer_area_m2"
            ],
            450.0,
        )
        self.assertIn(
            "3×33.3%并联",
            configuration["candidate_model_or_designation"],
        )
        self.assertNotIn(
            "非标准型",
            configuration["candidate_model_or_designation"],
        )
        self.assertTrue(plan["algorithmic_selection_warning"])

    def test_axial_pump_split_does_not_fabricate_gbt_model(self) -> None:
        result = app_core.manual_match(
            "block:PUMP",
            {
                "equipment_tag": "P-HIGH-FLOW",
                "phase": "liquid",
                "flow_m3_h": 4000,
                "density_kg_m3": 1000,
                "head_m": 60,
            },
        )["result"]
        configuration = result[
            "engineering_adjustment_plan"
        ]["configuration"]
        self.assertEqual(
            configuration["candidate_equipment_type"],
            "轴流泵",
        )
        self.assertEqual(
            configuration["parallel_train_count_estimate"],
            2,
        )
        self.assertEqual(
            configuration["installed_unit_count_estimate"],
            3,
        )
        self.assertIsNone(
            configuration["candidate_standard_marking"]
        )
        designation = configuration[
            "candidate_model_or_designation"
        ]
        self.assertIn("轴流泵系统", designation)
        self.assertNotIn("GB/T 5662", designation)
        self.assertNotIn("非标准型", designation)

    def test_large_tower_plan_keeps_formal_geometry_open(self) -> None:
        result = app_core.manual_match(
            "block:RADFRAC",
            {
                "equipment_tag": "T-LARGE",
                "stage_count": 30,
                "inner_diameter_mm": 6000,
                "height_mm": 70000,
            },
        )["result"]
        plan = result["engineering_adjustment_plan"]
        designation = plan["configuration"][
            "candidate_model_or_designation"
        ]
        self.assertEqual(
            plan["configuration"][
                "parallel_train_count_estimate"
            ],
            3,
        )
        self.assertIn("3列并联", designation)
        self.assertIn("正式塔径/塔高", designation)
        self.assertIn("OPEN", designation)
        self.assertNotIn("6000", designation)
        self.assertNotIn("70000", designation)
        overview = result["customer_delivery"][
            "equipment_overview_table"
        ]["rows"][0]
        self.assertEqual(
            overview["model_or_specification"],
            designation,
        )
        self.assertEqual(
            overview["model_or_specification_status"],
            "algorithmic_modification_screening_only",
        )

    def test_agent_control_distinguishes_existing_target(self) -> None:
        result = app_core.manual_match(
            "block:PUMP",
            {
                "equipment_tag": "P-HEAD",
                "phase": "liquid",
                "flow_m3_h": 40,
                "density_kg_m3": 1000,
                "head_m": 35,
            },
        )["result"]
        calculate = result["selection_agent_control"][
            "calculate_before_select"
        ]
        self.assertIn(
            "pump_head_from_pressure",
            calculate["satisfied_by_existing_target_ids"],
        )
        self.assertFalse(
            calculate["all_registered_calculations_attempted"]
        )
        self.assertTrue(
            calculate["calculation_execution_satisfied"]
        )
        self.assertEqual(
            calculate["unsatisfied_calculation_ids"],
            [],
        )
        components = result["selection_agent_control"][
            "ambiguous_choice_resolution"
        ]["connection_components"]
        self.assertEqual(
            components["status"],
            "COMPLETED_REGISTERED_DETERMINISTIC_SELECTION",
        )
        self.assertTrue(
            components["selection_package_sha256"]
        )

    def test_customer_delivery_rejects_tampered_plan(self) -> None:
        result = app_core.manual_match(
            "block:HEATX",
            {
                "equipment_tag": "E-TAMPER",
                "heat_duty_kw": 1000,
                "heat_transfer_area_m2": 1350,
            },
        )["result"]
        forged = copy.deepcopy(result)
        forged["engineering_adjustment_plan"][
            "configuration"
        ]["parallel_train_count_estimate"] = 99
        with self.assertRaises(customer_delivery.CustomerDeliveryError):
            customer_delivery.build_customer_delivery(forged)

    def test_workbench_has_clickable_chain_and_translated_options(
        self,
    ) -> None:
        result = app_core.manual_match(
            "block:PUMP",
            {
                "equipment_tag": "P-WB",
                "phase": "liquid",
                "flow_m3_h": 4000,
                "density_kg_m3": 1000,
                "head_m": 60,
            },
        )["result"]
        workbench = derivation_workbench.build_workbench(
            result,
            app_core.load_catalog(),
            model_rules=app_core.matcher.load_model_rules(),
            selection_id="block:PUMP",
            overrides={"equipment_type": "轴流泵"},
        )
        self.assertEqual(
            [item["node_id"] for item in workbench["nodes"]],
            [
                "source",
                "template",
                "calculation",
                "terminal",
                "adjustment",
                "delivery",
            ],
        )
        template_field = workbench["nodes"][1][
            "editable_fields"
        ][0]
        self.assertEqual(template_field["edit_kind"], "select")
        self.assertTrue(
            all(
                option["label"]
                and option["internal_code"]
                for option in template_field["options"]
            )
        )
        terminal_fields = workbench["nodes"][3][
            "editable_fields"
        ]
        equipment_type = next(
            item
            for item in terminal_fields
            if item["field_id"] == "equipment_type"
        )
        labels = {
            option["label"]
            for option in equipment_type["options"]
        }
        self.assertIn("轴流泵", labels)
        self.assertIn("多级离心泵", labels)
        self.assertTrue(workbench["controls"][
            "single_equipment_recalculate"
        ])
        self.assertTrue(workbench["controls"][
            "restore_program_defaults"
        ])
        self.assertFalse(workbench["controls"][
            "formal_evidence_gate_overridable"
        ])

    def test_override_audit_preserves_default_and_new_hash(
        self,
    ) -> None:
        baseline = app_core.manual_match(
            "block:PUMP",
            {
                "equipment_tag": "P-AUDIT",
                "phase": "liquid",
                "flow_m3_h": 100,
                "density_kg_m3": 1000,
                "head_m": 40,
            },
        )["result"]
        recalculated = app_core.manual_match(
            "block:PUMP",
            {
                "equipment_tag": "P-AUDIT",
                "phase": "liquid",
                "flow_m3_h": 120,
                "density_kg_m3": 1000,
                "head_m": 40,
            },
        )["result"]
        audit = derivation_workbench.build_override_audit(
            baseline,
            {"flow_m3_h": 120},
            recalculated,
        )
        self.assertEqual(
            audit["status"],
            "USER_SCENARIO_RECALCULATED",
        )
        self.assertNotEqual(
            audit["baseline_result_sha256"],
            audit["recalculated_result_sha256"],
        )
        self.assertEqual(
            audit["changes"][0]["program_default_value"],
            100,
        )
        self.assertEqual(
            audit["changes"][0]["user_override_value"],
            120,
        )
        self.assertFalse(
            audit[
                "formal_model_promotion_allowed_by_override_alone"
            ]
        )

    def test_organized_answer_has_fixed_sections_and_bindings(
        self,
    ) -> None:
        result = app_core.manual_match(
            "block:PUMP",
            {
                "equipment_tag": "P-REPORT",
                "phase": "liquid",
                "flow_m3_h": 4000,
                "density_kg_m3": 1000,
                "head_m": 60,
            },
        )
        answer = result_presentation.build_organized_answer(
            result
        )
        self.assertEqual(
            answer["section_order"],
            [
                "结论",
                "计算",
                "候选与系统修改方案",
                "强制警告",
                "待补证据",
                "下一步",
            ],
        )
        self.assertTrue(
            answer["authority"][
                "deterministic_facts_immutable"
            ]
        )
        self.assertFalse(
            answer["authority"][
                "llm_may_change_counts_models_or_open_gates"
            ]
        )
        equipment = answer["equipment"][0]
        self.assertTrue(
            equipment["mandatory_warnings"]
        )
        self.assertTrue(
            equipment["fact_binding"][
                "engineering_adjustment_plan_sha256"
            ]
        )
        markdown = (
            result_presentation.render_organized_markdown(answer)
        )
        for heading in (
            "### 结论",
            "### 计算",
            "### 候选与系统修改方案",
            "### 强制警告",
            "### 待补证据",
            "### 下一步",
        ):
            self.assertIn(heading, markdown)

    def test_agent_exports_markdown_and_organizes_answer(
        self,
    ) -> None:
        source = {
            "input": {
                "operation": "manual_match",
                "payload": {
                    "selection_id": "block:PUMP",
                    "values": {
                        "equipment_tag": "P-AGENT-REPORT",
                        "phase": "liquid",
                        "flow_m3_h": 4000,
                        "density_kg_m3": 1000,
                        "head_m": 60,
                    },
                },
            },
            "format": "markdown",
        }
        with tempfile.TemporaryDirectory() as temporary:
            output_path = Path(temporary) / "report.md"
            report, artifacts = equipment_design_agent._execute(
                "render_report",
                {
                    **source,
                    "output_path": str(output_path),
                },
                EquipmentDesignApi(),
            )
            self.assertTrue(output_path.is_file())
            self.assertIn(str(output_path), artifacts)
            self.assertEqual(
                report["report_manifest"]["output_file_sha256"],
                equipment_design_agent.sha256_file(output_path),
            )
            self.assertEqual(
                report["organized_answer"]["schema"],
                "equipment-agent-organized-answer-v1",
            )
            organized, _ = equipment_design_agent._execute(
                "organize_answer",
                source,
                EquipmentDesignApi(),
            )
            self.assertTrue(
                organized["markdown"].startswith(
                    "# 设备设计选型报告"
                )
            )
            self.assertEqual(
                organized["organized_answer"][
                    "organized_answer_sha256"
                ],
                report["organized_answer"][
                    "organized_answer_sha256"
                ],
            )

    def test_agent_request_schema_registers_new_operations(
        self,
    ) -> None:
        schema = json.loads(
            equipment_design_agent.REQUEST_SCHEMA.read_text(
                encoding="utf-8"
            )
        )
        operations = schema["properties"]["operation"]["enum"]
        self.assertIn("organize_answer", operations)
        self.assertIn("answer.organize", operations)
        report_rule = next(
            item
            for item in schema["allOf"]
            if "render_report"
            in item["if"]["properties"]["operation"]["enum"]
        )
        formats = report_rule["then"]["properties"]["payload"][
            "properties"
        ]["format"]["enum"]
        self.assertIn("markdown", formats)
        self.assertIn("md", formats)


if __name__ == "__main__":
    unittest.main()
