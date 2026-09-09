from __future__ import annotations

import copy
import json
import math
import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = APP_DIR.parent
SCRIPTS_DIR = PACKAGE_ROOT / "scripts"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import aspen_equipment_derivation as derivation
import customer_delivery


class RealBkpCustomerDeliveryStage1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        source_root = (
            PACKAGE_ROOT
            / "outputs"
            / "real_bkp_stage1_20260723"
        )
        cls.sources = {
            "MCH": (
                source_root
                / "mch_com_rerun_stage1_v1_8_elevated"
                / "aspen_equipment_export.json"
            ),
            "EX2_4": (
                source_root
                / "exercise2_4_augmented_run"
                / "aspen_equipment_export.json"
            ),
        }
        cls.derivations: dict[str, dict] = {}
        cls.deliveries: dict[str, dict] = {}
        for case_name, source in cls.sources.items():
            bundle = json.loads(source.read_text(encoding="utf-8"))
            result = derivation.derive_bundle(bundle, source)
            if result.get("status") != "DERIVED":
                raise AssertionError(
                    f"{case_name} derivation failed: {result.get('status')}"
                )
            cls.derivations[case_name] = result
            cls.deliveries[case_name] = (
                customer_delivery.build_customer_delivery(result)
            )

    @staticmethod
    def _rows(bundle: dict) -> dict[str, dict]:
        return {
            str(row["equipment_tag"]): row
            for row in bundle["equipment_overview_table"]["rows"]
        }

    @staticmethod
    def _cells(row: dict) -> dict[str, dict]:
        return {
            str(cell["field_id"]): cell
            for cell in row["all_equipment_fields"]
        }

    def test_mch_tower_public_surface_has_no_screening_geometry(
        self,
    ) -> None:
        tower = self._rows(self.deliveries["MCH"])["B1"]
        cells = self._cells(tower)
        forbidden_fields = {
            "tower_diameter_screening_mm",
            "tower_height_screening_mm",
            "formula_only_shell_thickness_mm",
            "formula_only_head_thickness_mm",
            "nominal_shell_wall_thickness_selected",
            "nominal_head_wall_thickness_selected",
            "inner_diameter_mm",
        }
        self.assertTrue(forbidden_fields.isdisjoint(cells))
        for field_id in ("diameter_mm", "height_mm"):
            self.assertIn(field_id, cells)
            self.assertIsNone(cells[field_id]["value"])
            self.assertEqual(
                cells[field_id]["state"],
                "OPEN_FORMAL_EVIDENCE_GATE",
            )
        self.assertEqual(cells["stage_count"]["value"], 22.0)
        self.assertEqual(
            cells["stage_count"]["source"]["evidence_class"],
            "D",
        )
        self.assertIn(
            "N_stage_Aspen=22.0",
            tower["model_or_specification"],
        )
        public_text = json.dumps(
            {
                "model": tower["model_or_specification"],
                "fields": tower["all_equipment_fields"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        for token in (
            "Di_screen=",
            "H_layout_screen=",
            "shell_formula_t=",
        ):
            self.assertNotIn(token, public_text)
        key_summary = cells.get("key_specification_summary", {}).get(
            "value", {}
        )
        key_summary_text = json.dumps(
            key_summary,
            ensure_ascii=False,
            sort_keys=True,
        )
        for field_id in {
            *forbidden_fields,
            "height_mm",
        }:
            self.assertNotIn(f'"{field_id}"', key_summary_text)

    def test_all_six_real_physical_pipes_expose_hydraulics_and_null_open_gates(
        self,
    ) -> None:
        pipe_rows = [
            *[
                row
                for row in self._rows(
                    self.deliveries["MCH"]
                ).values()
                if row["record_kind"] == "piping"
            ],
            *[
                row
                for row in self._rows(
                    self.deliveries["EX2_4"]
                ).values()
                if row["record_kind"] == "piping"
            ],
        ]
        self.assertEqual(len(pipe_rows), 6)
        for row in pipe_rows:
            with self.subTest(equipment_tag=row["equipment_tag"]):
                cells = self._cells(row)
                for field_id in (
                    "actual_velocity_m_s",
                    "reynolds_number",
                    "pressure_gradient_kpa_per_100m",
                ):
                    value = cells[field_id]["value"]
                    self.assertIsInstance(value, (int, float))
                    self.assertTrue(math.isfinite(float(value)))
                    self.assertGreater(float(value), 0.0)
                    self.assertEqual(
                        cells[field_id]["source"]["kind"],
                        "deterministic_programmatic_pipe_specification",
                    )
                for field_id in (
                    "stress_analysis_ref",
                    "support_design_ref",
                ):
                    self.assertIsNone(cells[field_id]["value"])
                    self.assertEqual(
                        cells[field_id]["state"],
                        "OPEN_FORMAL_EVIDENCE_GATE",
                    )

    def test_ex2_4_pump_public_fields_are_complete_and_honest(
        self,
    ) -> None:
        pump = self._rows(self.deliveries["EX2_4"])["PUMP"]
        cells = self._cells(pump)
        expected_numeric = {
            "hydraulic_power_kw": 4.924805054098709,
            "shaft_power_kw": 7.422259785633107,
            "electrical_power_kw": 7.42225979,
            "pump_efficiency_percent": 66.3518281,
            "aspen_flow_m3_h": 25.0,
            "aspen_simulated_head_m": 72.4046713,
            "aspen_configured_shaft_speed_candidate_rpm": 2800.0,
            "pump_candidate_reference_speed_rpm": 2900.0,
            "npsha_pressure_kpa": 97.53,
        }
        for field_id, expected in expected_numeric.items():
            self.assertAlmostEqual(
                float(cells[field_id]["value"]),
                expected,
                places=6,
            )
        self.assertEqual(
            cells["medium_name"]["value"],
            "WATER (100 mol%)",
        )
        self.assertEqual(
            cells["fluid_to_shaft_balance_status"]["value"],
            "PASS",
        )
        self.assertEqual(
            cells["shaft_to_electrical_balance_status"]["value"],
            "OPEN_INCOMPLETE_POWER_BALANCE",
        )
        configured_speed = cells[
            "aspen_configured_shaft_speed_candidate_rpm"
        ]
        self.assertEqual(
            configured_speed["state"],
            "ASPEN_CONFIGURED_INPUT_CANDIDATE_NOT_SOLVED_ACTUAL_SPEED",
        )
        self.assertEqual(
            configured_speed["source"]["evidence_class"],
            "R",
        )
        self.assertEqual(
            configured_speed["source"]["promotion_cap"],
            "TYPE_SCREENING",
        )
        self.assertFalse(
            configured_speed["source"]["formal_design_evidence"]
        )
        for field_id in (
            "driver_efficiency_percent",
            "aspen_actual_shaft_speed_rpm",
        ):
            self.assertIsNone(cells[field_id]["value"])
            self.assertEqual(
                cells[field_id]["state"],
                "OPEN_FORMAL_EVIDENCE_GATE",
            )
        self.assertTrue(
            cells["npsha_raw_unit_semantics"]["value"][
                "legacy_export_unit_reinterpreted_as_kpa"
            ]
        )

    def test_every_open_cell_is_machine_null_with_complete_metadata(
        self,
    ) -> None:
        open_count = 0
        for case_name, bundle in self.deliveries.items():
            for row in bundle["equipment_overview_table"]["rows"]:
                for cell in row["all_equipment_fields"]:
                    if (
                        cell.get("state")
                        != "OPEN_FORMAL_EVIDENCE_GATE"
                    ):
                        continue
                    open_count += 1
                    with self.subTest(
                        case=case_name,
                        tag=row["equipment_tag"],
                        field=cell["field_id"],
                    ):
                        self.assertIsNone(cell["value"])
                        self.assertTrue(cell.get("display_value"))
                        self.assertEqual(
                            cell["source"]["evidence_class"],
                            "U",
                        )
                        self.assertEqual(
                            cell["promotion_cap"],
                            "NOT_PROMOTABLE",
                        )
                        self.assertTrue(
                            cell["open_gate"]["reason"]
                        )
                        self.assertTrue(
                            cell["open_gate"]["required_action"]
                        )
        self.assertGreater(open_count, 0)

    def test_customer_rows_bind_exact_derivation_rows_and_tamper_is_detected(
        self,
    ) -> None:
        def assert_no_embedded_row_binding(value: object) -> None:
            if isinstance(value, dict):
                self.assertNotIn("aspen_source_binding", value)
                for nested in value.values():
                    assert_no_embedded_row_binding(nested)
            elif isinstance(value, list):
                for nested in value:
                    assert_no_embedded_row_binding(nested)

        for case_name, delivery_bundle in self.deliveries.items():
            result = self.derivations[case_name]
            expected = {
                str(
                    item.get("aspen_block_id")
                    or item.get("stream_id")
                    or item.get("equipment_tag")
                ): item["program_generated_record_sha256"]
                for item in [
                    *result["equipment"],
                    *result["piping"],
                ]
                if (
                    item.get("aspen_mapping_status")
                    != "NOT_APPLICABLE_SIMULATION_LOGIC_NODE"
                    and item.get("alias_only") is not True
                )
            }
            verification = (
                customer_delivery.verify_customer_delivery_bundle(
                    delivery_bundle
                )
            )
            self.assertEqual(verification["status"], "PASS")
            for row in delivery_bundle[
                "equipment_overview_table"
            ]["rows"]:
                self.assertEqual(
                    row["program_generated_record_sha256"],
                    expected[str(row["equipment_tag"])],
                )
                self.assertIn("source_chain_binding", row)
                for cell in [
                    *row["all_equipment_fields"],
                    *row["authority_cells"],
                ]:
                    self.assertNotIn("source_chain_binding", cell)
                    assert_no_embedded_row_binding(cell)
                    self.assertNotIn(
                        "aspen_source_binding",
                        cell["source"],
                    )
                    self.assertEqual(
                        cell["source"][
                            "aspen_source_binding_sha256"
                        ],
                        row["source_chain_binding_sha256"],
                    )
                    self.assertEqual(
                        cell["source"][
                            "aspen_source_binding_scope"
                        ],
                        "ROW_LEVEL_SOURCE_CHAIN_POINTER",
                    )
                    for field_id in (
                        "source_chain_binding_sha256",
                        "derivation_record_kind",
                        "derivation_record_identity",
                        "program_generated_record_sha256",
                        "program_generated_record_binding_sha256",
                    ):
                        self.assertEqual(
                            cell.get(field_id),
                            row.get(field_id),
                        )

        tampered = copy.deepcopy(self.deliveries["EX2_4"])
        pump = self._rows(tampered)["PUMP"]
        cells = self._cells(pump)
        cells["hydraulic_power_kw"]["value"] = 999.0
        verification = (
            customer_delivery.verify_customer_delivery_bundle(
                tampered
            )
        )
        self.assertEqual(verification["status"], "FAIL")
        self.assertIn(
            "DELIVERY_CELL_SHA256_MISMATCH",
            {item["code"] for item in verification["errors"]},
        )

        pointer_tampered = copy.deepcopy(self.deliveries["EX2_4"])
        pump = self._rows(pointer_tampered)["PUMP"]
        pump["all_equipment_fields"][0][
            "source_chain_binding_sha256"
        ] = "0" * 64
        verification = (
            customer_delivery.verify_customer_delivery_bundle(
                pointer_tampered
            )
        )
        self.assertEqual(verification["status"], "FAIL")
        self.assertIn(
            "SOURCE_CHAIN_BINDING_POINTER_SHA256_MISMATCH",
            {item["code"] for item in verification["errors"]},
        )


if __name__ == "__main__":
    unittest.main()
