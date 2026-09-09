from __future__ import annotations

import sys
import math
import unittest
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PACKAGE_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import equipment_design_match as matcher


class EquipmentDesignMatchConstraintSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rules = matcher.load_rules()
        cls.graph = matcher.load_graph()

    def _match_constraint_failure(
        self,
        raw: dict[str, Any],
        *,
        constraint_gate: str,
        rejected_reason: str,
    ) -> dict[str, Any]:
        result = matcher.match_one(raw, self.rules, self.graph)
        recommendation = result["model_recommendation"]

        self.assertEqual(
            recommendation["status"],
            "ENGINEERING_CONSTRAINT_FAILED",
        )
        self.assertEqual(recommendation["formal_ready_candidate_count"], 0)

        leading = recommendation["leading_candidate"]
        self.assertEqual(leading["candidate_kind"], "engineered_designation")
        self.assertEqual(
            leading["status"],
            "ENGINEERING_FAMILY_RETAINED_CONSTRAINT_FAIL",
        )
        self.assertTrue(leading["eligible_for_leading_candidate"])
        self.assertFalse(leading["eligible_for_formal_selection"])
        self.assertFalse(leading["formal_model"])
        self.assertIn(constraint_gate, leading["missing_gates"])

        non_engineering_candidates = [
            candidate
            for candidate in recommendation["candidates"]
            if candidate["candidate_kind"] != "engineered_designation"
        ]
        for candidate in non_engineering_candidates:
            self.assertEqual(candidate["status"], "REJECTED_CONSTRAINT_FAIL")
            self.assertEqual(candidate["candidate_eligibility"], "REJECTED")
            self.assertFalse(candidate["eligible_for_leading_candidate"])
            self.assertFalse(candidate["eligible_for_formal_selection"])
            self.assertIn(
                rejected_reason,
                candidate["candidate_rejection_reasons"],
            )

        return recommendation

    def test_pump_npsh_failure_retains_family_and_rejects_standard_candidates(
        self,
    ) -> None:
        recommendation = self._match_constraint_failure(
            {
                "aspen_block_type": "PUMP",
                "phase": "liquid",
                "flow_m3_h": 20,
                "head_m": 30,
                "npsha_m": 2,
                "npshr_m": 3,
                "required_npsh_margin_m": 0.5,
            },
            constraint_gate="engineering_constraint_fail:pump_npsh_margin",
            rejected_reason="PUMP_NPSH_CONSTRAINT_FAILED",
        )

        standard_candidates = [
            candidate
            for candidate in recommendation["candidates"]
            if candidate["candidate_kind"] == "standard_marking"
        ]
        self.assertTrue(standard_candidates)
        self.assertTrue(
            all(
                candidate["candidate_rejection_reasons"]
                for candidate in standard_candidates
            )
        )

    def test_compressor_surge_failure_retains_family_without_formal_selection(
        self,
    ) -> None:
        recommendation = self._match_constraint_failure(
            {
                "aspen_block_type": "COMPR",
                "phase": "vapor",
                "flow_m3_h": 2000,
                "suction_pressure_mpa": 0.1,
                "discharge_pressure_mpa": 0.5,
                "surge_margin_percent": 5,
                "required_surge_margin_percent": 10,
            },
            constraint_gate=(
                "engineering_constraint_fail:compressor_surge_margin"
            ),
            rejected_reason="COMPRESSOR_SURGE_MARGIN_CONSTRAINT_FAILED",
        )

        self.assertEqual(
            recommendation["leading_candidate"]["candidate_eligibility"],
            "CONSTRAINT_FAIL_FAMILY_ONLY",
        )

    def test_storage_volume_failure_retains_family_without_formal_selection(
        self,
    ) -> None:
        recommendation = self._match_constraint_failure(
            {
                "equipment_family": "family_storage_vessel",
                "equipment_type": "立式储罐",
                "flow_m3_h": 10,
                "retention_time_min": 60,
                "fill_fraction": 0.8,
                "volume_m3": 5,
                "volume_basis": "nominal_total",
            },
            constraint_gate=(
                "engineering_constraint_fail:storage_required_volume"
            ),
            rejected_reason="STORAGE_REQUIRED_VOLUME_CONSTRAINT_FAILED",
        )

        self.assertEqual(
            recommendation["leading_candidate"]["candidate_eligibility"],
            "CONSTRAINT_FAIL_FAMILY_ONLY",
        )

    def test_only_liquid_valve_uses_the_incompressible_liquid_cv_formula(
        self,
    ) -> None:
        rule = next(
            item
            for item in self.rules["families"]
            if item["id"] == "family_valve"
        )

        for phase in ("vapor", "mixed", "solid", "unknown", None):
            with self.subTest(phase=phase):
                calculations, pending, derived = matcher.run_calculations(
                    rule,
                    {
                        "aspen_block_type": "VALVE",
                        "phase": phase,
                        "flow_m3_h": 100.0,
                        "density_kg_m3": 6.0,
                        "inlet_pressure_mpa": 1.2,
                        "outlet_pressure_mpa": 0.12,
                        "pressure_drop_kpa": 1080.0,
                    },
                )

                self.assertNotIn("cv", derived)
                self.assertFalse(
                    any(
                        item.get("target_field") == "cv"
                        for item in calculations
                    )
                )
                blocker = next(
                    item
                    for item in pending
                    if item.get("calculation_id")
                    == "valve_liquid_equivalent_cv_screening"
                )
                self.assertEqual(
                    blocker["status"],
                    "BLOCKED_PHASE_INCOMPATIBLE_FORMULA",
                )
                self.assertEqual(
                    blocker["prohibited_output_field"],
                    "cv",
                )

        liquid_calculations, liquid_pending, liquid_derived = (
            matcher.run_calculations(
                rule,
                {
                    "aspen_block_type": "VALVE",
                    "phase": "liquid",
                    "flow_m3_h": 100.0,
                    "density_kg_m3": 1_000.0,
                    "inlet_pressure_mpa": 1.2,
                    "outlet_pressure_mpa": 0.12,
                    "pressure_drop_kpa": 1080.0,
                },
            )
        )
        self.assertIn("cv", liquid_derived)
        self.assertTrue(
            any(
                item.get("target_field") == "cv"
                for item in liquid_calculations
            )
        )
        self.assertFalse(
            any(
                item.get("status") == "BLOCKED_PHASE_INCOMPATIBLE_FORMULA"
                for item in liquid_pending
            )
        )

    def test_rplug_never_relabels_one_tube_diameter_as_whole_vessel(
        self,
    ) -> None:
        result = matcher.match_one(
            {
                "aspen_block_type": "RPLUG",
                "diameter_mm": 76.3,
                "operating_pressure_mpa": 2.45,
                "pressure_basis": "absolute",
                "atmospheric_pressure_mpa": 0.101325,
            },
            self.rules,
            self.graph,
        )
        values = result["design_parameter_package"]["selection_context"]["values"]
        for forbidden_field in (
            "diameter_mm",
            "inner_diameter_mm",
            "height_mm",
            "straight_shell_length_mm",
            "volume_m3",
            "volume_basis",
        ):
            self.assertNotIn(forbidden_field, values)
        calculation_ids = {
            row["calculation_id"]
            for row in result["calculations"]
        }
        self.assertNotIn("cylinder_volume", calculation_ids)
        self.assertNotIn("cylinder_thickness", calculation_ids)
        self.assertNotIn("head_thickness", calculation_ids)

    def test_tower_total_height_is_derived_from_stages_not_generic_default(
        self,
    ) -> None:
        result = matcher.match_one(
            {
                "aspen_block_type": "RADFRAC",
                "phase": "liquid",
                "flow_m3_h": 120.0,
                "stage_count": 30,
                "operating_pressure_mpa": 0.2,
                "pressure_basis": "absolute",
                "atmospheric_pressure_mpa": 0.101325,
            },
            self.rules,
            self.graph,
        )
        calculations = {
            item["calculation_id"]: item
            for item in result["calculations"]
        }
        internal_height = calculations["tower_internal_height"]["value"]
        total_height = calculations["tower_preliminary_height"]["value"]
        values = result["design_parameter_package"]["selection_context"]["values"]

        self.assertEqual(total_height, 16_050.0)
        self.assertEqual(values["height_mm"], total_height)
        self.assertEqual(values["inner_diameter_mm"], 600.0)
        self.assertNotIn(
            "diameter_mm",
            result["model_decision"]["sizing_missing_fields"],
        )
        self.assertGreaterEqual(total_height, internal_height * 1000.0)
        self.assertFalse(
            any(
                item["field_id"] == "height_mm"
                for item in result["design_fallbacks"]
            )
        )


if __name__ == "__main__":
    unittest.main()
