from __future__ import annotations

import json
import hashlib
import math
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import equipment_design_match as matcher


@contextmanager
def workspace_temporary_directory():
    path = matcher.PACKAGE_ROOT / "outputs" / "core_test_runs" / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=False)
    yield str(path)


class EquipmentDesignMatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rules = matcher.load_rules()
        cls.graph = matcher.load_graph()

    def test_rule_graph_coverage(self) -> None:
        result = matcher.validate_rules(self.rules, self.graph)
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual(result["graph_family_count"], 17)
        self.assertEqual(result["rule_family_count"], 17)

    def test_graph_path_override_is_resolved_at_call_time(self) -> None:
        original = matcher.GRAPH_PATH
        with workspace_temporary_directory() as temp:
            replacement = Path(temp) / "graph.json"
            replacement.write_text('{"nodes": [], "edges": []}', encoding="utf-8")
            try:
                matcher.GRAPH_PATH = replacement
                self.assertEqual(matcher.load_graph(), {"nodes": [], "edges": []})
            finally:
                matcher.GRAPH_PATH = original

    def test_every_family_has_an_exact_deterministic_alias(self) -> None:
        for rule in self.rules["families"]:
            result = matcher.match_one({"equipment_type": rule["aliases"][0]}, self.rules, self.graph)
            self.assertEqual(result["status"], "MATCHED", (rule["id"], result))
            self.assertEqual(result["match"]["family_id"], rule["id"], (rule["id"], result["match"]))

    def test_every_family_returns_a_machine_readable_model_candidate(self) -> None:
        allowed_classes = {"standard_marking", "vendor_candidate", "engineered_designation", "component_marking"}
        for rule in self.rules["families"]:
            with self.subTest(family_id=rule["id"]):
                result = matcher.match_one({"equipment_family": rule["id"]}, self.rules, self.graph)
                recommendation = result["model_recommendation"]
                self.assertIn(recommendation["recommendation_class"], allowed_classes)
                self.assertGreaterEqual(recommendation["candidate_count"], 1)
                self.assertTrue(recommendation["leading_candidate"]["designation"])
                if recommendation["leading_candidate"]["candidate_id"].endswith(":engineering-designation"):
                    self.assertEqual(
                        recommendation["leading_candidate"]["candidate_kind"],
                        "generic_type_placeholder",
                    )
                    self.assertEqual(
                        recommendation["leading_candidate"]["target_recommendation_class"],
                        recommendation["recommendation_class"],
                    )
                    self.assertFalse(recommendation["leading_candidate"]["is_vendor_model"])
                    self.assertFalse(recommendation["leading_candidate"]["formal_model"])
                self.assertFalse(recommendation["llm_used"])
                self.assertEqual(
                    result["model_decision"]["generated_candidate_designation"],
                    recommendation["leading_candidate"]["designation"],
                )

    def test_every_equipment_family_has_a_registered_terminal_form_fallback(self) -> None:
        for rule in self.rules["families"]:
            with self.subTest(family_id=rule["id"]):
                result = matcher.match_one(
                    {"equipment_family": rule["id"]},
                    self.rules,
                    self.graph,
                )
                recommendation = result["model_recommendation"]
                terminal = recommendation["terminal_selection"]
                self.assertIn(
                    terminal["status"],
                    {
                        "CONDITIONED_TERMINAL_TYPE_SELECTED",
                        "DEFAULTED_TERMINAL_TYPE_SELECTED",
                    },
                )
                self.assertNotEqual(terminal["selection_basis"], "legacy_generic_type")
                self.assertEqual(terminal["recommended_type"], recommendation["recommended_type"])
                self.assertTrue(terminal["rule_id"])
                if terminal["default_applied"]:
                    self.assertTrue(terminal["assumption"])
                for unresolved in ("待", "或", "其他", "候选"):
                    self.assertNotIn(unresolved, recommendation["recommended_type"])

    def test_all_family_minimum_meaningful_fixture_executes_registered_formula_chains(self) -> None:
        fixture_path = matcher.PACKAGE_ROOT / "app" / "fixtures" / "all_family_minimum_meaningful_inputs.json"
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        self.assertEqual(fixture["schema"], "equipment-design-all-family-acceptance-fixture-v1")
        self.assertEqual(len(fixture["cases"]), fixture["expected_family_count"])
        calculation_count = 0
        for case in fixture["cases"]:
            with self.subTest(family_id=case["family_id"]):
                result = matcher.match_one(
                    {"equipment_family": case["family_id"], **case["values"]},
                    self.rules,
                    self.graph,
                )
                calculation_ids = [item["calculation_id"] for item in result["calculations"]]
                calculation_count += len(calculation_ids)
                self.assertEqual(calculation_ids, case["expected_calculation_ids"])
                self.assertEqual(result["design_parameter_package"]["status"], "READY_FOR_CANDIDATE_MATCHING")
                self.assertEqual(
                    result["model_recommendation"]["selection_execution"]["status"],
                    "EXECUTED",
                )
                self.assertFalse(result["model_recommendation"]["minimum_candidate_missing_fields"])
                self.assertEqual(
                    result["model_recommendation"]["leading_candidate"]["candidate_kind"],
                    case["expected_candidate_kind"],
                )
                self.assertTrue(result["model_decision"]["candidate_selection_executed"])
                self.assertGreaterEqual(result["model_decision"]["ready_candidate_count"], 1)
                if case["family_id"] == "family_pump":
                    self.assertTrue(result["model_decision"]["generated_candidate_model"])
                else:
                    self.assertIsNone(result["model_decision"]["generated_candidate_model"])
                    self.assertTrue(result["model_decision"]["generated_candidate_designation"])
        self.assertEqual(calculation_count, fixture["expected_total_calculation_count"])

    def test_pump_standard_marking_candidates_are_ranked_from_authority_table(self) -> None:
        result = matcher.match_one({
            "equipment_family": "family_pump",
            "phase": "liquid",
            "pressure_basis": "absolute",
            "atmospheric_pressure_mpa": 0.101325,
            "flow_m3_h": 20,
            "inlet_pressure_mpa": 0.2,
            "outlet_pressure_mpa": 0.6,
            "pressure_basis": "absolute",
            "density_kg_m3": 900,
            "efficiency_percent": 75,
        }, self.rules, self.graph)
        recommendation = result["model_recommendation"]
        self.assertEqual(recommendation["status"], "STANDARD_MARKING_CANDIDATES")
        self.assertEqual(recommendation["leading_candidate"]["standard_marking"], "65-40-200")
        self.assertEqual(recommendation["leading_candidate"]["speed_rpm"], 2900)
        self.assertFalse(recommendation["leading_candidate"]["is_vendor_model"])
        self.assertEqual(
            recommendation["leading_candidate"]["status"],
            "HEURISTIC_NEAREST_STANDARD_REFERENCE_POINT",
        )
        self.assertEqual(recommendation["leading_candidate"]["ranking_evidence_class"], "J")
        self.assertGreaterEqual(recommendation["screening_candidate_count"], 1)
        self.assertEqual(recommendation["formal_ready_candidate_count"], 0)
        self.assertEqual(result["model_decision"]["formal_ready_candidate_count"], 0)
        self.assertEqual(
            result["model_decision"]["ready_candidate_count_semantics"],
            "ready_for_screening_review_not_formal",
        )
        self.assertEqual(recommendation["pump_standard_lookup"]["candidate_count"], 10)
        self.assertIn("equal-weight", recommendation["pump_standard_lookup"]["catalog"]["query_policy"])
        self.assertIn(
            "allowable_operating_range",
            recommendation["leading_candidate"]["ranking_method"]["does_not_prove"],
        )
        trace = {item["predicate_id"]: item["status"] for item in recommendation["leading_candidate"]["predicate_trace"]}
        self.assertEqual(trace["family_pump:gbt5662:max_working_pressure"], "PASS")
        self.assertEqual(trace["family_pump:vendor_curve:Q_H_eta_BEP"], "UNKNOWN")

    def test_design_pressure_converts_absolute_to_gauge_before_screening(self) -> None:
        result = matcher.match_one(
            {
                "equipment_family": "family_storage_vessel",
                "operating_pressure_mpa": 0.2,
                "pressure_basis": "absolute",
                "atmospheric_pressure_mpa": 0.1,
                "design_pressure_factor": 1.1,
            },
            self.rules,
            self.graph,
        )
        calculation = next(
            item for item in result["calculations"]
            if item["calculation_id"] == "design_pressure"
        )
        self.assertAlmostEqual(calculation["value"], 0.11, places=12)
        self.assertEqual(calculation["formula_chain"]["formula"], "(Poperating_abs-Patm)*k")
        self.assertIn("(0.2-0.1)*1.1", calculation["equation_chain"])

    def test_design_pressure_gauge_branch_does_not_require_atmospheric_pressure(self) -> None:
        result = matcher.match_one(
            {
                "equipment_family": "family_storage_vessel",
                "operating_pressure_mpa": 0.2,
                "pressure_basis": "gauge",
                "design_pressure_factor": 1.1,
            },
            self.rules,
            self.graph,
        )
        calculation = next(
            item for item in result["calculations"]
            if item["calculation_id"] == "design_pressure"
        )
        self.assertAlmostEqual(calculation["value"], 0.22, places=12)
        self.assertEqual(calculation["formula_chain"]["formula"], "Poperating_g*k")

    def test_absolute_vacuum_routes_design_pressure_and_thickness_to_external_branch(self) -> None:
        result = matcher.match_one(
            {
                "equipment_family": "family_storage_vessel",
                "operating_pressure_mpa": 0.05,
                "pressure_basis": "absolute",
                "atmospheric_pressure_mpa": 0.101325,
                "design_pressure_factor": 1.1,
                "inner_diameter_mm": 1200,
                "allowable_stress_mpa": 120,
                "weld_efficiency": 0.85,
            },
            self.rules,
            self.graph,
        )
        pending = {item["calculation_id"]: item for item in result["calculation_pending"]}
        self.assertEqual(
            pending["design_pressure"]["status"],
            "BLOCKED_EXTERNAL_PRESSURE_BRANCH_REQUIRED",
        )
        self.assertLess(pending["design_pressure"]["operating_gauge_pressure_mpa"], 0)
        self.assertEqual(pending["cylinder_thickness"]["status"], "BLOCKED_UPSTREAM_CALCULATION")
        self.assertEqual(pending["head_thickness"]["status"], "BLOCKED_UPSTREAM_CALCULATION")
        self.assertNotIn("design_pressure_mpa", result["derived_parameters"])

    def test_design_pressure_missing_basis_or_absolute_atmosphere_uses_visible_fallback(self) -> None:
        missing_basis = matcher.match_one(
            {
                "equipment_family": "family_storage_vessel",
                "operating_pressure_mpa": 0.2,
                "design_pressure_factor": 1.1,
            },
            self.rules,
            self.graph,
        )
        missing_atmosphere = matcher.match_one(
            {
                "equipment_family": "family_storage_vessel",
                "operating_pressure_mpa": 0.2,
                "pressure_basis": "absolute",
                "design_pressure_factor": 1.1,
            },
            self.rules,
            self.graph,
        )
        for result, fallback_field in (
            (missing_basis, "pressure_basis"),
            (missing_atmosphere, "atmospheric_pressure_mpa"),
        ):
            calculated = next(
                item for item in result["calculations"]
                if item["calculation_id"] == "design_pressure"
            )
            self.assertGreater(calculated["value"], 0)
            fallback = next(
                item for item in result["design_fallbacks"]
                if item["field_id"] == fallback_field
            )
            self.assertTrue(fallback["auto_applied"])
            self.assertEqual(fallback["evidence_class"], "J")
            self.assertEqual(fallback["promotion_cap"], "TYPE_SCREENING")

    def test_direct_design_pressure_requires_basis_and_absolute_value_is_normalized_before_thickness(self) -> None:
        common = {
            "equipment_family": "family_storage_vessel",
            "design_pressure_mpa": 1.2,
            "inner_diameter_mm": 1200,
            "allowable_stress_mpa": 120,
            "weld_efficiency": 0.85,
            "head_type": "2:1_ellipsoidal",
        }
        missing_basis = matcher.match_one(common, self.rules, self.graph)
        self.assertEqual(
            missing_basis["effective_normalized_input"]["design_pressure_basis"],
            "gauge",
        )
        self.assertTrue(any(
            item["field_id"] == "design_pressure_basis"
            and item["tier"] == "EXPLICIT_FINAL_FALLBACK_DEFAULT"
            for item in missing_basis["design_fallbacks"]
        ))
        self.assertTrue(any(
            item["calculation_id"] in {"cylinder_thickness", "head_thickness"}
            for item in missing_basis["calculations"]
        ))

        missing_atmosphere = matcher.match_one(
            {**common, "design_pressure_basis": "absolute"},
            self.rules,
            self.graph,
        )
        missing_atmosphere_calculations = {
            item["calculation_id"]: item for item in missing_atmosphere["calculations"]
        }
        self.assertIn("design_pressure_basis_conversion", missing_atmosphere_calculations)
        self.assertIn("cylinder_thickness", missing_atmosphere_calculations)
        self.assertIn("head_thickness", missing_atmosphere_calculations)
        self.assertTrue(any(
            item["field_id"] == "atmospheric_pressure_mpa"
            for item in missing_atmosphere["design_fallbacks"]
        ))
        absolute_rows = {
            row["field_id"]: row
            for group in missing_atmosphere["design_parameter_package"]["groups"]
            for row in group["rows"]
        }
        self.assertEqual(absolute_rows["design_pressure_mpa"]["symbol"], "Pdes,g")
        self.assertEqual(absolute_rows["design_pressure_mpa"]["unit"], "MPa(g)")
        self.assertEqual(absolute_rows["design_pressure_mpa"]["state"], "PROVIDED")

        converted = matcher.match_one(
            {
                **common,
                "design_pressure_basis": "absolute",
                "atmospheric_pressure_mpa": 0.1,
            },
            self.rules,
            self.graph,
        )
        calculations = {item["calculation_id"]: item for item in converted["calculations"]}
        self.assertAlmostEqual(calculations["design_pressure_basis_conversion"]["value"], 1.1)
        self.assertAlmostEqual(converted["derived_parameters"]["design_pressure_mpa"], 1.1)
        self.assertEqual(converted["derived_parameters"]["design_pressure_basis"], "gauge")
        self.assertIn("1.1*1200", calculations["cylinder_thickness"]["equation_chain"])
        chain_ids = [
            item["calculation_id"]
            for item in converted["design_parameter_package"]["calculation_chain"]
        ]
        self.assertLess(
            chain_ids.index("design_pressure_basis_conversion"),
            chain_ids.index("cylinder_thickness"),
        )
        converted_rows = {
            row["field_id"]: row
            for group in converted["design_parameter_package"]["groups"]
            for row in group["rows"]
        }
        converted_pressure_row = converted_rows["design_pressure_mpa"]
        self.assertEqual(converted_pressure_row["symbol"], "Pdes,g")
        self.assertEqual(converted_pressure_row["unit"], "MPa(g)")
        self.assertEqual(converted_pressure_row["state"], "CALCULATED")
        self.assertEqual(
            converted_pressure_row["source"]["calculation_id"],
            "design_pressure_basis_conversion",
        )

    def test_direct_absolute_design_pressure_is_canonical_and_operating_factor_is_crosscheck_only(self) -> None:
        result = matcher.match_one(
            {
                "equipment_family": "family_storage_vessel",
                "operating_pressure_mpa": 1.0,
                "pressure_basis": "absolute",
                "atmospheric_pressure_mpa": 0.1,
                "design_pressure_factor": 1.1,
                "design_pressure_mpa": 1.2,
                "design_pressure_basis": "absolute",
                "volume_m3": 10,
                "volume_basis": "nominal_total",
                "design_temperature_c": 80,
            },
            self.rules,
            self.graph,
        )
        calculations = {item["calculation_id"]: item for item in result["calculations"]}
        converted = calculations["design_pressure_basis_conversion"]
        screened = calculations["design_pressure"]
        self.assertAlmostEqual(converted["value"], 1.1)
        self.assertTrue(converted["adopted_as_canonical"])
        self.assertAlmostEqual(converted["canonical_value"], 1.1)
        self.assertEqual(converted["formula_chain"]["formula"], "Pdesign_abs-Patm")
        self.assertEqual(converted["formula_chain"]["substitution"], "1.2-0.1")
        self.assertAlmostEqual(screened["value"], 0.99)
        self.assertFalse(screened["adopted_as_canonical"])
        self.assertAlmostEqual(screened["canonical_value"], 1.1)
        self.assertEqual(screened["status"], "PROVISIONAL_SCREENING_DIFFERENCE")
        self.assertEqual(
            screened["provided_target_crosscheck"]["authority_choice"],
            "provided_target_preserved; built_in_formula_is_provisional_screening",
        )
        self.assertAlmostEqual(result["derived_parameters"]["design_pressure_mpa"], 1.1)
        self.assertEqual(result["derived_parameters"]["design_pressure_basis"], "gauge")
        self.assertAlmostEqual(
            result["design_parameter_package"]["selection_context"]["values"]["design_pressure_mpa"],
            1.1,
        )
        self.assertEqual(
            result["design_parameter_package"]["selection_context"]["values"]["design_pressure_basis"],
            "gauge",
        )
        pressure_row = next(
            row
            for group in result["design_parameter_package"]["groups"]
            for row in group["rows"]
            if row["field_id"] == "design_pressure_mpa"
        )
        self.assertEqual(pressure_row["source"]["calculation_id"], "design_pressure_basis_conversion")
        self.assertEqual(pressure_row["equation_chain"], converted["equation_chain"])
        self.assertEqual(result["model_decision"]["formula_promotion_cap"], "TYPE_SCREENING")
        self.assertTrue(result["model_decision"]["fallback_promotion_blockers"])
        self.assertEqual(
            result["model_recommendation"]["selection_execution"]["status"],
            "EXECUTED",
        )

    def test_direct_design_pressure_missing_basis_uses_visible_gauge_fallback(self) -> None:
        result = matcher.match_one(
            {
                "equipment_family": "family_storage_vessel",
                "operating_pressure_mpa": 1.0,
                "pressure_basis": "absolute",
                "atmospheric_pressure_mpa": 0.1,
                "design_pressure_factor": 1.1,
                "design_pressure_mpa": 1.2,
                "volume_m3": 10,
                "volume_basis": "nominal_total",
                "design_temperature_c": 80,
            },
            self.rules,
            self.graph,
        )
        self.assertFalse(any(
            item["calculation_id"] == "design_pressure_basis_conversion"
            for item in result["calculations"]
        ))
        self.assertNotIn("design_pressure_mpa", result["derived_parameters"])
        self.assertNotIn("design_pressure_basis", result["derived_parameters"])
        fallback = next(
            item for item in result["design_fallbacks"]
            if item["field_id"] == "design_pressure_basis"
        )
        self.assertEqual(fallback["value"], "gauge")
        self.assertEqual(fallback["tier"], "EXPLICIT_FINAL_FALLBACK_DEFAULT")
        pressure_row = next(
            row
            for group in result["design_parameter_package"]["groups"]
            for row in group["rows"]
            if row["field_id"] == "design_pressure_mpa"
        )
        self.assertEqual(pressure_row["state"], "PROVIDED")
        self.assertEqual(pressure_row["symbol"], "Pdes,g")
        self.assertEqual(pressure_row["unit"], "MPa(g)")
        self.assertEqual(
            result["model_recommendation"]["selection_execution"]["status"],
            "EXECUTED",
        )

    def test_nonpositive_gauge_design_pressure_routes_to_external_pressure_branch(self) -> None:
        result = matcher.match_one(
            {
                "equipment_family": "family_storage_vessel",
                "design_pressure_mpa": -0.05,
                "design_pressure_basis": "gauge",
                "inner_diameter_mm": 1200,
                "allowable_stress_mpa": 120,
                "weld_efficiency": 0.85,
                "head_type": "2:1_ellipsoidal",
                "volume_m3": 10,
                "volume_basis": "nominal_total",
                "design_temperature_c": 80,
            },
            self.rules,
            self.graph,
        )
        pending = {item["calculation_id"]: item for item in result["calculation_pending"]}
        self.assertEqual(
            pending["design_pressure"]["status"],
            "BLOCKED_EXTERNAL_PRESSURE_BRANCH_REQUIRED",
        )
        self.assertEqual(pending["cylinder_thickness"]["status"], "BLOCKED_UPSTREAM_CALCULATION")
        self.assertEqual(pending["head_thickness"]["status"], "BLOCKED_UPSTREAM_CALCULATION")
        self.assertNotIn("cylinder_calculated_thickness_mm", result["derived_parameters"])
        self.assertNotIn("head_calculated_thickness_mm", result["derived_parameters"])
        self.assertEqual(result["design_parameter_package"]["status"], "BLOCKED")
        self.assertEqual(
            result["model_recommendation"]["selection_execution"]["status"],
            "IDENTITY_CANDIDATE_RETAINED_CALCULATION_BLOCKED",
        )
        self.assertGreaterEqual(result["model_recommendation"]["candidate_count"], 1)
        self.assertTrue(result["model_recommendation"]["leading_candidate"]["designation"])

    def test_pump_standard_pressure_limit_uses_gauge_equivalent(self) -> None:
        params = {
            "inlet_pressure_mpa": 1.55,
            "outlet_pressure_mpa": 1.65,
            "pressure_basis": "absolute",
            "atmospheric_pressure_mpa": 0.1,
        }
        converted = matcher._pump_standard_pressure_predicate(params)
        self.assertEqual(converted["status"], "PASS")
        self.assertAlmostEqual(converted["observed_maximum_mpa"], 1.55)
        self.assertEqual(converted["comparison_policy"], "absolute_to_gauge_then_compare")
        unknown = matcher._pump_standard_pressure_predicate({
            key: value for key, value in params.items() if key != "atmospheric_pressure_mpa"
        })
        self.assertEqual(unknown["status"], "UNKNOWN")

    def test_failed_pump_standard_pressure_scope_cannot_be_leading_candidate(self) -> None:
        result = matcher.match_one(
            {
                "equipment_family": "family_pump", "phase": "liquid",
                "pressure_basis": "gauge", "flow_m3_h": 20, "head_m": 20,
                "inlet_pressure_mpa": 0.1, "outlet_pressure_mpa": 2.0,
            },
            self.rules,
            self.graph,
        )
        recommendation = result["model_recommendation"]
        self.assertEqual(recommendation["status"], "STANDARD_SCOPE_FAILED")
        self.assertEqual(recommendation["leading_candidate"]["candidate_kind"], "generic_type_placeholder")
        standard_candidates = [
            item for item in recommendation["candidates"]
            if item.get("candidate_kind") == "standard_marking"
        ]
        self.assertTrue(standard_candidates)
        self.assertTrue(all(item["status"] == "REJECTED_STANDARD_SCOPE" for item in standard_candidates))
        self.assertTrue(all(not item["eligible_for_leading_candidate"] for item in standard_candidates))

    def test_pump_phase_gate_blocks_vapor_before_standard_lookup(self) -> None:
        base = {
            "equipment_family": "family_pump",
            "pressure_basis": "gauge",
            "flow_m3_h": 20,
            "head_m": 45,
            "density_kg_m3": 900,
            "efficiency_percent": 75,
        }
        result = matcher.match_one({**base, "phase": "vapor"}, self.rules, self.graph)
        recommendation = result["model_recommendation"]
        self.assertEqual(result["design_parameter_package"]["status"], "BLOCKED_PHYSICAL_PHASE")
        self.assertEqual(
            recommendation["status"],
            "PHYSICAL_BASIS_BLOCKED_IDENTITY_CANDIDATE_RETAINED",
        )
        self.assertGreaterEqual(recommendation["candidate_count"], 1)
        self.assertTrue(recommendation["leading_candidate"]["designation"])
        self.assertIsNone(recommendation["pump_standard_lookup"])
        self.assertEqual(result["model_decision"]["model_status"], "physical_basis_blocked")
        self.assertFalse(result["model_decision"]["candidate_selection_executed"])

    def test_mixed_or_slurry_pump_retains_family_but_requires_special_duty_route(self) -> None:
        base = {
            "equipment_family": "family_pump",
            "pressure_basis": "gauge",
            "flow_m3_h": 20,
            "head_m": 45,
            "density_kg_m3": 1050,
            "efficiency_percent": 65,
        }
        for phase in ("mixed", "slurry", "浆液"):
            with self.subTest(phase=phase):
                result = matcher.match_one({**base, "phase": phase}, self.rules, self.graph)
                recommendation = result["model_recommendation"]
                self.assertEqual(result["match"]["family_id"], "family_pump")
                self.assertEqual(
                    result["design_parameter_package"]["phase_compatibility"]["status"],
                    "SPECIAL_DUTY_ROUTE_REQUIRED",
                )
                self.assertEqual(
                    recommendation["selection_execution"]["status"],
                    "WAITING_CALCULATED_PARAMETERS",
                )
                self.assertIn(
                    "special_duty_route_definition",
                    recommendation["minimum_candidate_missing_fields"],
                )
                self.assertIsNone(recommendation["pump_standard_lookup"])
                self.assertEqual(recommendation["leading_candidate"]["candidate_kind"], "generic_type_placeholder")

    def test_phase_aliases_are_canonical_before_compatibility_gate(self) -> None:
        pump_base = {
            "equipment_family": "family_pump",
            "pressure_basis": "gauge",
            "flow_m3_h": 20,
            "head_m": 45,
            "density_kg_m3": 900,
            "efficiency_percent": 75,
        }
        for phase in ("liquid", "liq", "液体"):
            result = matcher.match_one({**pump_base, "phase": phase}, self.rules, self.graph)
            self.assertEqual(result["normalized_input"]["phase"], "liquid")
            self.assertEqual(result["design_parameter_package"]["phase_compatibility"]["status"], "PASS")
        compressor_base = {
            "equipment_family": "family_compressor",
            "pressure_basis": "absolute",
            "flow_m3_h": 2000,
            "inlet_pressure_mpa": 0.2,
            "outlet_pressure_mpa": 0.8,
            "gas_molecular_weight": 28,
            "compressibility_factor": 0.98,
        }
        for phase in ("gas", "vapor", "气体"):
            result = matcher.match_one({**compressor_base, "phase": phase}, self.rules, self.graph)
            self.assertEqual(result["normalized_input"]["phase"], "vapor")
            self.assertEqual(result["design_parameter_package"]["phase_compatibility"]["status"], "PASS")

    def test_unknown_pump_phase_uses_visible_liquid_fallback_and_queries_catalog(self) -> None:
        result = matcher.match_one(
            {
                "equipment_family": "family_pump",
                "pressure_basis": "gauge",
                "flow_m3_h": 20,
                "head_m": 45,
                "density_kg_m3": 900,
                "efficiency_percent": 75,
            },
            self.rules,
            self.graph,
        )
        recommendation = result["model_recommendation"]
        self.assertEqual(
            result["design_parameter_package"]["phase_compatibility"]["status"],
            "PASS",
        )
        phase_fallback = next(item for item in result["design_fallbacks"] if item["field_id"] == "phase")
        self.assertEqual(phase_fallback["value"], "liquid")
        self.assertEqual(phase_fallback["evidence_class"], "J")
        self.assertEqual(recommendation["selection_execution"]["status"], "EXECUTED")
        self.assertIsNotNone(recommendation["pump_standard_lookup"])
        self.assertTrue(result["model_decision"]["generated_candidate_model"])

    def test_compatible_liquid_pump_and_vapor_compressor_execute_candidate_matching(self) -> None:
        pump = matcher.match_one(
            {
                "equipment_family": "family_pump",
                "phase": "liquid",
                "pressure_basis": "gauge",
                "flow_m3_h": 20,
                "head_m": 45,
                "density_kg_m3": 900,
                "efficiency_percent": 75,
            },
            self.rules,
            self.graph,
        )
        compressor = matcher.match_one(
            {
                "equipment_family": "family_compressor",
                "phase": "vapor",
                "pressure_basis": "absolute",
                "flow_m3_h": 2000,
                "inlet_pressure_mpa": 0.2,
                "outlet_pressure_mpa": 0.8,
                "gas_molecular_weight": 28,
                "compressibility_factor": 0.98,
            },
            self.rules,
            self.graph,
        )
        for result in (pump, compressor):
            self.assertEqual(result["design_parameter_package"]["phase_compatibility"]["status"], "PASS")
            self.assertEqual(result["model_recommendation"]["selection_execution"]["status"], "EXECUTED")
        self.assertIsNotNone(pump["model_recommendation"]["pump_standard_lookup"])

    def test_complete_compressor_process_basis_calculates_shaft_power_before_selection(self) -> None:
        result = matcher.match_one(
            {
                "equipment_family": "family_compressor",
                "phase": "vapor",
                "pressure_basis": "absolute",
                "flow_m3_h": 3600.0,
                "inlet_pressure_mpa": 0.2,
                "outlet_pressure_mpa": 0.8,
                "heat_capacity_ratio_k": 1.3,
                "efficiency_percent": 75.0,
            },
            self.rules,
            self.graph,
        )

        calculation = next(
            item for item in result["calculations"]
            if item["calculation_id"] == "compressor_isentropic_shaft_power"
        )
        expected = (
            0.2e6 * (3600.0 / 3600.0)
            * 1.3 / (1.3 - 1.0)
            * ((0.8 / 0.2) ** ((1.3 - 1.0) / 1.3) - 1.0)
            / 0.75 / 1000.0
        )
        self.assertAlmostEqual(calculation["value"], expected)
        self.assertEqual(calculation["target_field"], "shaft_power_kw")
        self.assertEqual(
            result["derived_parameters"]["shaft_power_kw"],
            calculation["value"],
        )
        package_row = next(
            row for group in result["design_parameter_package"]["groups"]
            for row in group["rows"]
            if row["field_id"] == "shaft_power_kw"
        )
        self.assertEqual(package_row["state"], "CALCULATED")
        self.assertEqual(package_row["formula_chain"], calculation["formula_chain"])
        self.assertIn("Pshaft=", result["model_recommendation"]["leading_candidate"]["designation"])
        total_power = next(
            item for item in result["calculations"]
            if item["calculation_id"] == "compressor_total_power"
        )
        self.assertEqual(total_power["target_field"], "total_power_kw")
        self.assertGreater(total_power["value"], calculation["value"])
        self.assertEqual(
            result["derived_parameters"]["total_power_kw"],
            total_power["value"],
        )

    def test_liquid_compressor_is_blocked_before_candidate_ranking(self) -> None:
        result = matcher.match_one(
            {
                "aspen_block_type": "COMPR",
                "phase": "liquid",
                "pressure_basis": "absolute",
                "flow_m3_h": 2000,
                "inlet_pressure_mpa": 0.2,
                "outlet_pressure_mpa": 0.8,
                "gas_molecular_weight": 28,
                "compressibility_factor": 0.98,
            },
            self.rules,
            self.graph,
        )
        self.assertEqual(result["match"]["family_id"], "family_compressor")
        self.assertEqual(
            result["model_recommendation"]["status"],
            "PHYSICAL_BASIS_BLOCKED_IDENTITY_CANDIDATE_RETAINED",
        )
        self.assertGreaterEqual(result["model_recommendation"]["candidate_count"], 1)
        self.assertTrue(result["model_recommendation"]["leading_candidate"]["designation"])

    def test_representative_families_return_nonblank_engineering_or_vendor_candidates(self) -> None:
        cases = [
            ("family_fixed_tubesheet_exchanger", {
                "heat_transfer_area_m2": 120, "design_pressure_mpa": 1.2, "design_temperature_c": 160,
            }, "standard_marking"),
            ("family_tower", {
                "diameter_mm": 1600, "height_mm": 18000, "stage_count": 30,
                "design_pressure_mpa": 0.5, "design_temperature_c": 140,
            }, "engineered_designation"),
            ("family_compressor", {
                "flow_m3_h": 2000, "inlet_pressure_mpa": 0.2, "outlet_pressure_mpa": 0.8,
                "pressure_basis": "absolute", "gas_molecular_weight": 28, "compressibility_factor": 0.98,
            }, "vendor_candidate"),
            ("family_valve", {
                "valve_function": "control", "selected_dn": "DN80", "pressure_class": "PN16", "material": "S31603",
            }, "vendor_candidate"),
        ]
        for family_id, values, expected_class in cases:
            with self.subTest(family_id=family_id):
                result = matcher.match_one({"equipment_family": family_id, **values}, self.rules, self.graph)
                recommendation = result["model_recommendation"]
                self.assertEqual(recommendation["recommendation_class"], expected_class)
                self.assertTrue(recommendation["leading_candidate"]["designation"])
                self.assertIsNone(recommendation["formal_model"])

    def test_pump_calculation_uses_explicit_inputs(self) -> None:
        record = {
            "设备类型": "离心泵",
            "体积流量": "36 m3/h",
            "扬程": "45 m",
            "密度": "850 kg/m3",
            "效率": "72 %",
        }
        result = matcher.match_one(record, self.rules, self.graph)
        self.assertEqual(result["match"]["family_id"], "family_pump")
        hydraulic = next(item for item in result["calculations"] if item["calculation_id"] == "pump_hydraulic_power")
        shaft = next(item for item in result["calculations"] if item["calculation_id"] == "pump_shaft_power")
        self.assertAlmostEqual(hydraulic["value"], 3.751043625, places=8)
        self.assertAlmostEqual(shaft["value"], 5.2097828125, places=8)
        self.assertTrue(hydraulic["equation_chain"].startswith("hydraulic_power_kw = rho*g*Q*H"))
        self.assertTrue(shaft["equation_chain"].startswith("shaft_power_kw = rho*g*Q*H/eta"))
        self.assertFalse(result["llm_used"])

    def test_key_encoded_units_are_normalized(self) -> None:
        normalized, conflicts, unmapped = matcher.normalize_record(
            {
                "equipment_type": "压缩机",
                "flow_m3_s": 1.5,
                "inlet_pressure_bar": 1.2,
                "outlet_pressure_kpa": 720,
                "design_temperature_k": 393.15,
                "diameter_m": 1.2,
                "efficiency_fraction": 0.76,
            }
        )
        self.assertFalse(conflicts)
        self.assertFalse(unmapped)
        self.assertAlmostEqual(normalized["flow_m3_h"], 5400.0)
        self.assertAlmostEqual(normalized["inlet_pressure_mpa"], 0.12)
        self.assertAlmostEqual(normalized["outlet_pressure_mpa"], 0.72)
        self.assertAlmostEqual(normalized["design_temperature_c"], 120.0)
        self.assertAlmostEqual(normalized["diameter_mm"], 1200.0)
        self.assertAlmostEqual(normalized["efficiency_percent"], 76.0)

    def test_pressure_ratio_missing_basis_uses_visible_gauge_fallback(self) -> None:
        result = matcher.match_one(
            {"equipment_type": "压缩机", "inlet_pressure_mpa": 0.12, "outlet_pressure_mpa": 0.72},
            self.rules,
            self.graph,
        )
        ratio = next(item for item in result["calculations"] if item["calculation_id"] == "pressure_ratio")
        self.assertAlmostEqual(ratio["value"], (0.72 + 0.101325) / (0.12 + 0.101325))
        fallbacks = {item["field_id"]: item for item in result["design_fallbacks"]}
        self.assertEqual(fallbacks["pressure_basis"]["value"], "gauge")
        self.assertAlmostEqual(fallbacks["atmospheric_pressure_mpa"]["value"], 0.101325)
        chain = next(item for item in result["design_parameter_package"]["calculation_chain"] if item["calculation_id"] == "pressure_ratio")
        self.assertEqual(chain["status"], "CALCULATED_WITH_PROVISIONAL_UPSTREAM")
        self.assertNotIn("pressure_basis", result["design_parameter_package"]["selection_feature_vector"]["missing_fields"])
        self.assertEqual(result["model_recommendation"]["selection_execution"]["status"], "EXECUTED")
        self.assertGreaterEqual(result["model_recommendation"]["candidate_count"], 1)
        self.assertTrue(result["model_decision"]["candidate_selection_executed"])
        self.assertGreaterEqual(result["model_decision"]["ready_candidate_count"], 1)
        self.assertTrue(result["model_decision"]["generated_candidate_designation"])
        self.assertTrue(result["model_decision"]["generated_candidate_designation"])

    def test_pump_pressure_head_missing_basis_uses_visible_gauge_fallback(self) -> None:
        result = matcher.match_one(
            {
                "equipment_type": "泵",
                "flow_m3_h": 20,
                "inlet_pressure_mpa": 0.2,
                "outlet_pressure_mpa": 0.6,
                "density_kg_m3": 900,
                "efficiency_percent": 75,
            },
            self.rules,
            self.graph,
        )
        calculations = {item["calculation_id"]: item for item in result["calculations"]}
        self.assertIn("pump_head_from_pressure", calculations)
        self.assertIn("pump_hydraulic_power", calculations)
        self.assertIn("pump_shaft_power", calculations)
        fallbacks = {item["field_id"]: item for item in result["design_fallbacks"]}
        self.assertEqual(fallbacks["pressure_basis"]["value"], "gauge")
        self.assertAlmostEqual(fallbacks["atmospheric_pressure_mpa"]["value"], 0.101325)
        self.assertEqual(result["model_recommendation"]["selection_execution"]["status"], "EXECUTED")
        self.assertTrue(result["model_decision"]["candidate_selection_executed"])
        self.assertTrue(result["model_decision"]["generated_candidate_model"])

    def test_physical_calculation_blocker_stops_candidate_selection(self) -> None:
        result = matcher.match_one({
            "equipment_type": "压缩机",
            "flow_m3_h": 2000,
            "inlet_pressure_mpa": 0.8,
            "outlet_pressure_mpa": 0.2,
            "pressure_basis": "absolute",
            "gas_molecular_weight": 28,
            "compressibility_factor": 0.98,
            "efficiency_percent": 75,
        }, self.rules, self.graph)
        package = result["design_parameter_package"]
        recommendation = result["model_recommendation"]
        self.assertEqual(package["status"], "BLOCKED")
        self.assertEqual(package["selection_feature_vector"]["status"], "BLOCKED")
        self.assertEqual(package["status_axes"]["candidate_matching"], "BLOCKED_CALCULATION")
        self.assertEqual(result["model_decision"]["model_status"], "calculation_blocked")
        self.assertEqual(recommendation["status"], "CALCULATION_BLOCKED_IDENTITY_CANDIDATE_RETAINED")
        self.assertEqual(
            recommendation["selection_execution"]["status"],
            "IDENTITY_CANDIDATE_RETAINED_CALCULATION_BLOCKED",
        )
        self.assertGreaterEqual(recommendation["candidate_count"], 1)
        self.assertTrue(recommendation["leading_candidate"]["designation"])

    def test_supplied_class_a_target_is_calculated_crosschecked_and_blocks_on_mismatch(self) -> None:
        expected_power = 900.0 * 9.80665 * (20.0 / 3600.0) * 45.0 / 0.75 / 1000.0
        result = matcher.match_one({
            "equipment_type": "泵",
            "flow_m3_h": 20,
            "density_kg_m3": 900,
            "efficiency_percent": 75,
            "head_m": 45,
            "shaft_power_kw": 999,
        }, self.rules, self.graph)
        power = next(item for item in result["calculations"] if item["calculation_id"] == "pump_shaft_power")
        blocker = next(item for item in result["calculation_pending"] if item.get("status") == "BLOCKED_TARGET_MISMATCH")
        self.assertAlmostEqual(power["value"], expected_power)
        self.assertEqual(power["provided_target_crosscheck"]["status"], "FAIL")
        self.assertEqual(power["provided_target_crosscheck"]["authority_choice"], "deterministic_calculation")
        self.assertEqual(blocker["target_field"], "shaft_power_kw")
        self.assertAlmostEqual(result["derived_parameters"]["shaft_power_kw"], expected_power)
        rows = [
            row
            for group in result["design_parameter_package"]["groups"]
            for row in group["rows"]
        ]
        shaft_row = next(row for row in rows if row["field_id"] == "shaft_power_kw")
        self.assertAlmostEqual(shaft_row["raw_value"], expected_power)
        self.assertEqual(shaft_row["source"]["kind"], "deterministic_calculation")
        self.assertEqual(result["design_parameter_package"]["status"], "BLOCKED")
        self.assertGreaterEqual(result["model_recommendation"]["candidate_count"], 1)
        self.assertEqual(
            result["model_recommendation"]["selection_execution"]["status"],
            "IDENTITY_CANDIDATE_RETAINED_CALCULATION_BLOCKED",
        )
        self.assertTrue(result["model_recommendation"]["leading_candidate"]["designation"])

    def test_supplied_class_b_target_difference_preserves_same_case_value(self) -> None:
        result = matcher.match_one({
            "equipment_type": "泵",
            "flow_m3_h": 20,
            "inlet_pressure_mpa": 0.2,
            "outlet_pressure_mpa": 0.6,
            "pressure_basis": "absolute",
            "density_kg_m3": 900,
            "efficiency_percent": 75,
            "head_m": 999,
        }, self.rules, self.graph)
        expected_head = 400000.0 / (900.0 * 9.80665)
        head = next(item for item in result["calculations"] if item["calculation_id"] == "pump_head_from_pressure")
        warning = next(
            item for item in result["calculation_pending"]
            if item.get("status") == "WARNING_PROVISIONAL_SCREENING_DIFFERENCE"
        )
        self.assertAlmostEqual(head["value"], expected_head)
        self.assertEqual(head["status"], "PROVISIONAL_SCREENING_DIFFERENCE")
        self.assertEqual(head["provided_target_crosscheck"]["status"], "FAIL")
        self.assertEqual(
            head["provided_target_crosscheck"]["authority_choice"],
            "provided_target_preserved; built_in_formula_is_provisional_screening",
        )
        self.assertEqual(warning["target_field"], "head_m")
        self.assertNotIn("head_m", result["derived_parameters"])
        self.assertEqual(result["design_parameter_package"]["selection_context"]["values"]["head_m"], 999.0)
        self.assertNotEqual(result["design_parameter_package"]["status"], "BLOCKED")

    def test_supplied_class_b_target_within_tolerance_is_still_preserved(self) -> None:
        calculated_head = 400000.0 / (900.0 * 9.80665)
        supplied_head = round(calculated_head, 2)
        result = matcher.match_one({
            "equipment_type": "泵",
            "flow_m3_h": 20,
            "inlet_pressure_mpa": 0.2,
            "outlet_pressure_mpa": 0.6,
            "pressure_basis": "absolute",
            "density_kg_m3": 900,
            "efficiency_percent": 75,
            "head_m": supplied_head,
        }, self.rules, self.graph)
        head = next(item for item in result["calculations"] if item["calculation_id"] == "pump_head_from_pressure")
        self.assertEqual(head["provided_target_crosscheck"]["status"], "PASS")
        self.assertEqual(head["status"], "PROVISIONAL_SCREENING_CROSSCHECK_PASS")
        self.assertNotIn("head_m", result["derived_parameters"])
        self.assertEqual(result["design_parameter_package"]["selection_context"]["values"]["head_m"], supplied_head)
        self.assertNotEqual(result["model_recommendation"]["selection_execution"]["status"], "BLOCKED_CALCULATION")
        hydraulic = next(
            item for item in result["calculations"]
            if item["calculation_id"] == "pump_hydraulic_power"
        )
        self.assertEqual(hydraulic["calculation_notice"]["evidence_class"], "D")
        self.assertFalse(hydraulic["calculation_notice"]["risk_propagated_from_upstream"])
        self.assertEqual(result["model_decision"]["formula_promotion_cap"], "TYPE_SCREENING")
        self.assertTrue(result["model_decision"]["fallback_promotion_blockers"])

    def test_vendor_model_field_is_content_classified_before_any_vendor_claim(self) -> None:
        standard = matcher.match_one({
            "equipment_type": "泵",
            "flow_m3_h": 20,
            "head_m": 45,
            "density_kg_m3": 900,
            "efficiency_percent": 75,
            "vendor_model": "GB/T 5662-2013 65-40-200",
        }, self.rules, self.graph)
        standard_class = standard["model_decision"]["supplied_designation_classification"]
        self.assertEqual(standard_class["classification"], "standard_marking")
        self.assertFalse(standard_class["is_vendor_model"])
        self.assertNotEqual(standard["model_decision"]["model_status"], "vendor_candidate")
        self.assertFalse(standard["model_recommendation"]["leading_candidate"]["is_vendor_model"])

        specification = matcher.match_one({
            "equipment_type": "调节阀",
            "valve_function": "control",
            "flow_m3_h": 20,
            "pressure_drop_kpa": 80,
            "selected_dn": "DN80",
            "pressure_class": "PN16",
            "material": "S31603",
            "vendor_model": "DN80 PN16",
        }, self.rules, self.graph)
        spec_class = specification["model_decision"]["supplied_designation_classification"]
        self.assertEqual(spec_class["classification"], "engineering_specification")
        self.assertFalse(spec_class["is_vendor_model"])
        self.assertNotEqual(specification["model_decision"]["model_status"], "vendor_candidate")
        self.assertFalse(specification["model_recommendation"]["leading_candidate"]["is_vendor_model"])

    def test_absolute_and_gauge_pressure_ratios_are_not_mixed(self) -> None:
        absolute = matcher.match_one(
            {"equipment_type": "压缩机", "inlet_pressure_mpa": 0.12, "outlet_pressure_mpa": 0.72, "pressure_basis": "absolute"},
            self.rules,
            self.graph,
        )
        gauge = matcher.match_one(
            {
                "equipment_type": "压缩机",
                "inlet_pressure_mpa": 0.12,
                "outlet_pressure_mpa": 0.72,
                "pressure_basis": "gauge",
                "atmospheric_pressure_mpa": 0.101325,
            },
            self.rules,
            self.graph,
        )
        ratio_abs = next(item for item in absolute["calculations"] if item["calculation_id"] == "pressure_ratio")
        ratio_gauge = next(item for item in gauge["calculations"] if item["calculation_id"] == "pressure_ratio")
        self.assertAlmostEqual(ratio_abs["value"], 6.0)
        self.assertAlmostEqual(ratio_gauge["value"], (0.72 + 0.101325) / (0.12 + 0.101325))
        self.assertNotEqual(ratio_abs["value"], ratio_gauge["value"])
        self.assertEqual(ratio_abs["formula_chain"]["substitution"], "(0.72+0)/(0.12+0)")
        self.assertEqual(
            ratio_gauge["formula_chain"]["substitution"],
            "(0.72+0.101325)/(0.12+0.101325)",
        )
        self.assertAlmostEqual(eval(ratio_abs["formula_chain"]["substitution"], {"__builtins__": {}}), ratio_abs["value"])
        self.assertAlmostEqual(eval(ratio_gauge["formula_chain"]["substitution"], {"__builtins__": {}}), ratio_gauge["value"])

    def test_expander_ratio_is_inlet_absolute_over_outlet_absolute(self) -> None:
        result = matcher.match_one(
            {
                "equipment_type": "透平膨胀机",
                "inlet_pressure_mpa": 2.0,
                "outlet_pressure_mpa": 0.5,
                "pressure_basis": "absolute",
            },
            self.rules,
            self.graph,
        )
        ratio = next(item for item in result["calculations"] if item["calculation_id"] == "pressure_ratio")
        self.assertAlmostEqual(ratio["value"], 4.0)
        self.assertTrue(ratio["equation_chain"].startswith("expansion_pressure_ratio = Pin_abs/Pout_abs"))
        self.assertEqual(ratio["formula_chain"]["substitution"], "(2+0)/(0.5+0)")
        self.assertAlmostEqual(
            eval(ratio["formula_chain"]["substitution"], {"__builtins__": {}}),
            ratio["value"],
        )

    def test_negative_gauge_vacuum_is_allowed_when_absolute_pressure_is_positive(self) -> None:
        result = matcher.match_one(
            {
                "equipment_type": "压缩机",
                "inlet_pressure_mpa": -0.08,
                "outlet_pressure_mpa": 0.02,
                "pressure_basis": "gauge",
                "atmospheric_pressure_mpa": 0.101325,
            },
            self.rules,
            self.graph,
        )
        self.assertEqual(result["status"], "MATCHED")
        ratio = next(item for item in result["calculations"] if item["calculation_id"] == "pressure_ratio")
        self.assertGreater(ratio["value"], 1)

    def test_compressor_and_expander_wrong_pressure_directions_are_blocked_pending(self) -> None:
        cases = [
            {"equipment_type": "压缩机", "inlet_pressure_mpa": 1.0, "outlet_pressure_mpa": 0.5, "pressure_basis": "absolute"},
            {"equipment_type": "透平膨胀机", "inlet_pressure_mpa": 0.5, "outlet_pressure_mpa": 1.0, "pressure_basis": "absolute"},
        ]
        for record in cases:
            with self.subTest(record=record):
                result = matcher.match_one(record, self.rules, self.graph)
                blocked = next(item for item in result["calculation_pending"] if item["calculation_id"] == "pressure_ratio")
                self.assertEqual(blocked["status"], "BLOCKED_PHYSICAL_DIRECTION")
                self.assertTrue(any(item.startswith("calculation_hard_blocker:pressure_ratio") for item in result["model_decision"]["verification_missing_fields"]))

    def test_tower_routes_to_current_tower_standard(self) -> None:
        result = matcher.match_one({"设备类型": "精馏塔", "diameter_mm": 1200}, self.rules, self.graph)
        self.assertEqual(result["match"]["family_id"], "family_tower")
        numbers = {item["number"] for item in result["standard_routes"]}
        self.assertIn("NB/T 47041-2014", numbers)
        route = next(item for item in result["standard_routes"] if item["number"] == "NB/T 47041-2014")
        self.assertEqual(route["source_layer"]["package_state"], "PASS")
        self.assertFalse(route["automatic_numeric_reuse_allowed"])

    def test_pump_standards_route_through_freeze_gate(self) -> None:
        result = matcher.match_one({"设备类型": "泵"}, self.rules, self.graph)
        numbers = {item["number"] for item in result["standard_routes"]}
        self.assertIn("GB/T 3215-2025", numbers)
        self.assertIn("GB/T 5662-2013", numbers)
        self.assertTrue(any("gate_pump_freeze_20260712" in item["path"] for item in result["standard_routes"]))

    def test_fixed_tubesheet_beats_generic_heatx_block(self) -> None:
        result = matcher.match_one(
            {"equipment_type": "固定管板式换热器", "aspen_block_type": "HEATX"},
            self.rules,
            self.graph,
        )
        self.assertEqual(result["status"], "MATCHED")
        self.assertEqual(result["match"]["family_id"], "family_fixed_tubesheet_exchanger")

    def test_strong_identity_conflict_blocks(self) -> None:
        result = matcher.match_one(
            {"equipment_type": "泵", "aspen_block_type": "RADFRAC"},
            self.rules,
            self.graph,
        )
        self.assertEqual(result["status"], "BLOCKED_IDENTITY_CONFLICT")

    def test_contained_type_alias_conflicts_with_exact_aspen_block(self) -> None:
        result = matcher.match_one(
            {"equipment_type": "centrifugal pump package", "aspen_block_type": "RADFRAC"},
            self.rules,
            self.graph,
        )
        self.assertEqual(result["status"], "BLOCKED_IDENTITY_CONFLICT")

    def test_process_function_with_two_equipment_identities_blocks(self) -> None:
        result = matcher.match_one(
            {"process_function": "液体升压后进入精馏塔"},
            self.rules,
            self.graph,
        )
        self.assertEqual(result["status"], "BLOCKED_AMBIGUOUS_PROCESS_FUNCTION")

    def test_tag_alone_never_selects_a_family(self) -> None:
        result = matcher.match_one({"equipment_tag": "P-101"}, self.rules, self.graph)
        self.assertEqual(result["status"], "BLOCKED_MISSING_DECISIVE_IDENTITY")
        self.assertFalse(result["progress"]["terminal"])
        self.assertEqual(result["progress"]["candidate_families"][0]["family_id"], "family_pump")
        self.assertIsNotNone(result["progress"]["next_field"])

    def test_single_flow_field_generates_complete_nonempty_candidate_set(self) -> None:
        result = matcher.match_one({"flow_m3_h": 36}, self.rules, self.graph)
        self.assertEqual(result["status"], "BLOCKED_MISSING_DECISIVE_IDENTITY")
        candidates = {item["family_id"] for item in result["progress"]["candidate_families"]}
        self.assertTrue({"family_pump", "family_compressor", "family_process_piping", "family_valve"} <= candidates)
        self.assertTrue(all(item["automatic_preference_allowed"] is False for item in result["progress"]["candidate_families"]))

    def test_single_stage_count_returns_tower_candidate_without_auto_confirmation(self) -> None:
        result = matcher.match_one({"stage_count": 20}, self.rules, self.graph)
        self.assertEqual(result["status"], "BLOCKED_MISSING_DECISIVE_IDENTITY")
        self.assertEqual(result["progress"]["candidate_count"], 1)
        self.assertEqual(result["progress"]["candidate_families"][0]["family_id"], "family_tower")
        self.assertEqual(result["progress"]["state"], "NEEDS_IDENTITY")

    def test_heat_duty_keeps_generic_and_fixed_tubesheet_candidates(self) -> None:
        result = matcher.match_one({"heat_duty_kw": 1000}, self.rules, self.graph)
        candidate_ids = {item["family_id"] for item in result["progress"]["candidate_families"]}
        self.assertEqual(candidate_ids, {"family_fixed_tubesheet_exchanger", "family_other_heat_exchanger"})
        self.assertEqual(result["progress"]["most_general_common"]["family_id"], "family_other_heat_exchanger")

    def test_specific_process_function_beats_generic_heatx_mechanism(self) -> None:
        result = matcher.match_one(
            {"aspen_block_type": "HEATX", "process_function": "固定管板换热"},
            self.rules,
            self.graph,
        )
        self.assertEqual(result["status"], "MATCHED")
        self.assertEqual(result["match"]["family_id"], "family_fixed_tubesheet_exchanger")

    def test_compr_expansion_uses_function_direction_and_phase(self) -> None:
        result = matcher.match_one(
            {
                "aspen_block_type": "COMPR",
                "process_function": "气体膨胀",
                "phase": "gas",
                "pressure_basis": "absolute",
                "inlet_pressure_mpa": 2.0,
                "outlet_pressure_mpa": 0.5,
            },
            self.rules,
            self.graph,
        )
        self.assertEqual(result["status"], "MATCHED")
        self.assertEqual(result["match"]["family_id"], "family_gas_expander_turbine")

    def test_gauge_basis_requests_atmospheric_pressure_instead_of_invalid_input(self) -> None:
        result = matcher.match_one({"pressure_basis": "gauge"}, self.rules, self.graph)
        self.assertNotEqual(result["status"], "BLOCKED_INVALID_PARAMETERS")
        self.assertEqual(result["progress"]["next_field"]["field"], "atmospheric_pressure_mpa")

    def test_nested_or_boolean_string_fields_are_not_stringified_into_identity(self) -> None:
        for malformed in (["pump"], {"x": "pump"}, True):
            with self.subTest(malformed=malformed):
                result = matcher.match_one({"equipment_type": malformed}, self.rules, self.graph)
                self.assertEqual(result["status"], "BLOCKED_NORMALIZATION_CONFLICT")
                self.assertTrue(any(item.get("code") == "NON_STRING_VALUE" for item in result["normalization_conflicts"]))

    def test_invalid_hash_blocks_evidence_upgrade(self) -> None:
        result = matcher.match_one(
            {"equipment_type": "泵", "vendor_model": "X", "vendor_datasheet_sha256": "not-a-hash"},
            self.rules,
            self.graph,
        )
        self.assertEqual(result["status"], "BLOCKED_INVALID_PARAMETERS")

    def test_non_numeric_and_unsupported_or_conflicting_units_block(self) -> None:
        cases = [
            {"equipment_type": "泵", "flow_m3_h": "abc"},
            {"equipment_type": "泵", "flow_m3_h": "36 gallon/min"},
            {"equipment_type": "泵", "efficiency": 0.72},
            {"equipment_type": "泵", "效率": 0.72},
            {"equipment_type": "泵", "flow_m3_h": True},
            {"equipment_type": "泵", "inlet_pressure_bar": "1-2 bar"},
            {"equipment_type": "泵", "inlet_pressure_bar": "120 kPa"},
        ]
        for record in cases:
            with self.subTest(record=record):
                result = matcher.match_one(record, self.rules, self.graph)
                self.assertTrue(result["status"].startswith("BLOCKED_"), result)

    def test_invalid_phase_is_a_hard_input_error(self) -> None:
        result = matcher.match_one(
            {"equipment_type": "泵", "phase": "banana", "flow_m3_h": 20},
            self.rules,
            self.graph,
        )
        self.assertEqual(result["status"], "BLOCKED_INVALID_PARAMETERS")
        self.assertIn("INVALID_PHASE", {item.get("code") for item in result["parameter_errors"]})

    def test_gas_and_vapor_phase_aliases_share_one_canonical_value(self) -> None:
        self.assertEqual(matcher.canonical_phase("gas"), "vapor")
        self.assertEqual(matcher.canonical_phase("vapor"), "vapor")
        for phase in ("gas", "vapor", "气相", "蒸汽"):
            with self.subTest(phase=phase):
                result = matcher.match_one(
                    {"equipment_type": "压缩机", "phase": phase, "flow_m3_h": 20},
                    self.rules,
                    self.graph,
                )
                self.assertNotEqual(result["status"], "BLOCKED_INVALID_PARAMETERS", result)

    def test_npsha_below_npshr_is_constraint_failure_not_invalid_input(self) -> None:
        result = matcher.match_one(
            {
                "equipment_type": "泵",
                "phase": "liquid",
                "flow_m3_h": 20,
                "head_m": 30,
                "npsha_m": 1,
                "npshr_m": 5,
                "required_npsh_margin_m": 0.5,
            },
            self.rules,
            self.graph,
        )
        self.assertNotEqual(result["status"], "BLOCKED_INVALID_PARAMETERS")
        calculation = next(item for item in result["calculations"] if item["calculation_id"] == "pump_cavitation_margin")
        self.assertEqual(calculation["value"], -4.0)
        check = next(item for item in result["design_parameter_package"]["constraint_checks"] if item["check_id"] == "pump_npsh_margin")
        self.assertEqual(check["status"], "FAIL")
        self.assertEqual(check["evaluation"], "INSUFFICIENT_AGAINST_EXPLICIT_REQUIRED_MARGIN")
        rejected_standard = next(
            item for item in result["model_recommendation"]["candidates"]
            if item.get("candidate_kind") == "standard_marking"
        )
        predicate = next(
            item for item in rejected_standard["predicate_trace"]
            if item["predicate_id"] == "family_pump:cavitation:NPSHa_NPSHr"
        )
        self.assertEqual(predicate["status"], "FAIL")
        self.assertEqual(rejected_standard["status"], "REJECTED_CONSTRAINT_FAIL")
        self.assertEqual(
            result["model_recommendation"]["leading_candidate"]["candidate_kind"],
            "generic_type_placeholder",
        )
        self.assertEqual(result["model_recommendation"]["status"], "ENGINEERING_CONSTRAINT_FAILED")
        self.assertTrue(result["model_decision"]["engineering_constraint_blockers"])

    def test_positive_npsh_difference_without_required_margin_remains_unknown(self) -> None:
        result = matcher.match_one(
            {
                "equipment_family": "family_pump", "phase": "liquid",
                "flow_m3_h": 20, "head_m": 30, "npsha_m": 6, "npshr_m": 3,
            },
            self.rules,
            self.graph,
        )
        check = next(item for item in result["design_parameter_package"]["constraint_checks"] if item["check_id"] == "pump_npsh_margin")
        self.assertEqual(check["status"], "UNKNOWN")
        self.assertEqual(check["observed_margin_m"], 3.0)
        self.assertEqual(check["evaluation"], "SCREENING_ONLY_REQUIRED_MARGIN_NOT_SUPPLIED")

    def test_npsh_pass_requires_explicit_margin_and_hashed_same_duty_curve(self) -> None:
        with workspace_temporary_directory() as temporary_directory:
            curve = Path(temporary_directory) / "same-duty-vendor-curve.pdf"
            curve.write_bytes(b"same-duty curve fixture")
            digest = hashlib.sha256(curve.read_bytes()).hexdigest().upper()
            base = {
                "equipment_family": "family_pump", "phase": "liquid",
                "flow_m3_h": 20, "head_m": 30, "npsha_m": 6, "npshr_m": 3,
                "required_npsh_margin_m": 1.0,
                "vendor_curve_path": str(curve), "vendor_curve_sha256": digest,
            }
            open_scope = matcher.match_one(base, self.rules, self.graph)
            open_check = next(item for item in open_scope["design_parameter_package"]["constraint_checks"] if item["check_id"] == "pump_npsh_margin")
            self.assertEqual(open_check["status"], "UNKNOWN")
            closed = matcher.match_one(
                {**base, "npshr_evidence_scope": "same_duty_vendor_curve"},
                self.rules,
                self.graph,
            )
            closed_check = next(item for item in closed["design_parameter_package"]["constraint_checks"] if item["check_id"] == "pump_npsh_margin")
            self.assertEqual(closed_check["status"], "UNKNOWN")
            self.assertEqual(closed_check["numeric_status"], "PASS")
            self.assertFalse(closed_check["same_case_evidence_complete"])
            self.assertIn("machine_audited", closed_check["evaluation"].lower())

    def test_negative_compressor_surge_margin_is_constraint_failure_not_bad_input(self) -> None:
        result = matcher.match_one(
            {
                "equipment_family": "family_compressor",
                "phase": "gas",
                "pressure_basis": "absolute",
                "flow_m3_h": 2000,
                "inlet_pressure_mpa": 0.2,
                "outlet_pressure_mpa": 0.8,
                "gas_molecular_weight": 28,
                "compressibility_factor": 0.98,
                "efficiency_percent": 75,
                "surge_margin_percent": -2.0,
                "required_surge_margin_percent": 10.0,
            },
            self.rules,
            self.graph,
        )
        self.assertEqual(result["status"], "MATCHED")
        check = next(
            item for item in result["design_parameter_package"]["constraint_checks"]
            if item["check_id"] == "compressor_surge_margin"
        )
        self.assertEqual(check["status"], "FAIL")
        self.assertEqual(check["observed_margin_percent"], -2.0)
        self.assertEqual(result["model_recommendation"]["status"], "ENGINEERING_CONSTRAINT_FAILED")
        self.assertEqual(
            result["model_recommendation"]["leading_candidate"]["candidate_kind"],
            "generic_type_placeholder",
        )
        self.assertTrue(result["model_decision"]["engineering_constraint_blockers"])

    def test_compressor_surge_pass_requires_explicit_margin_and_same_duty_map_gate(self) -> None:
        numeric_only = matcher.assess_compressor_surge_constraint({
            "surge_margin_percent": 15.0,
            "required_surge_margin_percent": 10.0,
        })
        self.assertEqual(numeric_only["status"], "UNKNOWN")
        self.assertEqual(numeric_only["numeric_status"], "PASS")

        references = [
            "vendor_curve", "parameter:surge_margin_percent",
            "parameter:required_surge_margin_percent", "parameter:surge_margin_evidence_scope",
        ]
        params = {
            "surge_margin_percent": 15.0,
            "required_surge_margin_percent": 10.0,
            "surge_margin_evidence_scope": "same_duty_performance_map",
            "vendor_curve_path": "curve.pdf",
            "vendor_curve_sha256": "A" * 64,
            "evidence_manifest_path": "manifest.json",
            "evidence_manifest_sha256": "B" * 64,
            "audit_approval_path": "approval.json",
            "audit_approval_sha256": "C" * 64,
            "verification_result": "PASS",
            "approval_status": "approved",
        }
        manifest = {"gate_evidence": {"surge_choke_margin": references}}
        with patch.object(matcher, "audit_evidence_manifest", return_value=(manifest, [])), patch.object(
            matcher, "audit_final_approval", return_value=[]
        ):
            closed = matcher.assess_compressor_surge_constraint(params)
        self.assertEqual(closed["status"], "PASS")
        self.assertTrue(closed["same_case_evidence_complete"])

    def test_pump_pressure_drop_cannot_produce_negative_head_or_power(self) -> None:
        result = matcher.match_one(
            {
                "equipment_type": "泵",
                "flow_m3_h": 36,
                "density_kg_m3": 850,
                "efficiency_percent": 72,
                "inlet_pressure_mpa": 0.5,
                "outlet_pressure_mpa": 0.1,
                "pressure_basis": "absolute",
            },
            self.rules,
            self.graph,
        )
        self.assertFalse(result["calculations"])
        head = next(item for item in result["calculation_pending"] if item["calculation_id"] == "pump_head_from_pressure")
        hydraulic = next(item for item in result["calculation_pending"] if item["calculation_id"] == "pump_hydraulic_power")
        shaft = next(item for item in result["calculation_pending"] if item["calculation_id"] == "pump_shaft_power")
        self.assertEqual(head["status"], "BLOCKED_PHYSICAL_DIRECTION")
        self.assertEqual(hydraulic["status"], "BLOCKED_UPSTREAM_CALCULATION")
        self.assertEqual(shaft["status"], "BLOCKED_UPSTREAM_CALCULATION")
        self.assertTrue(any(item.startswith("calculation_hard_blocker:pump_head_from_pressure") for item in result["model_decision"]["verification_missing_fields"]))

    def test_pump_bad_pressure_direction_does_not_discard_registered_head_power_fallback(self) -> None:
        result = matcher.match_one(
            {
                "equipment_type": "泵",
                "inlet_pressure_mpa": 0.03,
                "outlet_pressure_mpa": 0.015,
                "pressure_basis": "absolute",
            },
            self.rules,
            self.graph,
        )
        self.assertEqual(result["effective_normalized_input"]["head_m"], 30.0)
        self.assertEqual(result["effective_normalized_input"]["density_kg_m3"], 1000.0)
        self.assertIn("hydraulic_power_kw", result["derived_parameters"])
        self.assertIn("shaft_power_kw", result["derived_parameters"])
        head = next(
            item for item in result["calculation_pending"]
            if item["calculation_id"] == "pump_head_from_pressure"
        )
        self.assertEqual(head["status"], "BLOCKED_PHYSICAL_DIRECTION")
        self.assertFalse(any(
            item.get("calculation_id") in {"pump_hydraulic_power", "pump_shaft_power"}
            and item.get("status") == "BLOCKED_UPSTREAM_CALCULATION"
            for item in result["calculation_pending"]
        ))

    def test_provisional_pressure_head_risk_propagates_to_power_chain(self) -> None:
        result = matcher.match_one(
            {
                "equipment_type": "泵",
                "flow_m3_h": 36,
                "density_kg_m3": 850,
                "efficiency_percent": 72,
                "inlet_pressure_mpa": 0.1,
                "outlet_pressure_mpa": 0.5,
                "pressure_basis": "absolute",
            },
            self.rules,
            self.graph,
        )
        calculations = {
            item["calculation_id"]: item for item in result["calculations"]
        }
        for calculation_id in ("pump_hydraulic_power", "pump_shaft_power"):
            with self.subTest(calculation_id=calculation_id):
                notice = calculations[calculation_id]["calculation_notice"]
                self.assertEqual(notice["declared_formula_evidence_class"], "D")
                self.assertEqual(notice["evidence_class"], "J")
                self.assertEqual(notice["result_status"], "PROVISIONAL")
                self.assertEqual(notice["promotion_cap"], "TYPE_SCREENING")
                self.assertTrue(notice["risk_propagated_from_upstream"])
                self.assertIn(
                    "pump_head_from_pressure",
                    {
                        item["calculation_id"]
                        for item in notice["upstream_formula_lineage"]
                    },
                )
        self.assertEqual(result["model_decision"]["formula_promotion_cap"], "TYPE_SCREENING")
        self.assertTrue(
            any(
                blocker.startswith("calculation_promotion_cap:pump_head_from_pressure")
                for blocker in result["model_decision"]["formula_promotion_blockers"]
            )
        )

    def test_type_screening_promotion_cap_prevents_final_model(self) -> None:
        rule = {
            "id": "family_pump",
            "model_policy": "standard_catalog_requires_vendor_curve",
            "verification_fields": [],
        }
        params = {
            "vendor_model": "VENDOR-X",
            "vendor_datasheet_path": "same-case-datasheet.pdf",
            "vendor_datasheet_sha256": "A" * 64,
            "verification_result": "PASS",
            "formal_calculation_path": "same-case-calculation.json",
            "formal_calculation_sha256": "B" * 64,
            "approval_status": "approved",
        }
        family_node = {"required_gates": []}
        manifest = {"approval_status": "approved"}
        with patch.object(matcher, "audit_evidence_manifest", return_value=(manifest, [])), patch.object(
            matcher, "audit_final_approval", return_value=[]
        ):
            uncapped, _, _ = matcher.determine_model_status(
                rule, params, family_node, [], [], []
            )
            capped, blockers, audit = matcher.determine_model_status(
                rule,
                params,
                family_node,
                [],
                [],
                ["calculation_promotion_cap:pump_head_from_pressure:TYPE_SCREENING"],
            )
        self.assertEqual(uncapped, "final_model")
        self.assertEqual(capped, "type_selected")
        self.assertEqual(audit["status"], "CAPPED_TYPE_SCREENING")
        self.assertEqual(audit["promotion_cap"], "TYPE_SCREENING")
        self.assertIn(
            "calculation_promotion_cap:pump_head_from_pressure:TYPE_SCREENING",
            blockers,
        )

    def test_physically_positive_sizing_fields_and_integer_counts_are_enforced(self) -> None:
        positive_fields = (
            "mass_flow_kg_h", "stage_count", "retention_time_min", "gas_molecular_weight",
            "compressibility_factor", "rotational_speed_rpm", "membrane_area_m2",
            "flux", "selectivity", "capacity", "cv",
        )
        for field in positive_fields:
            with self.subTest(field=field):
                result = matcher.match_one({"equipment_type": "泵", field: -1}, self.rules, self.graph)
                self.assertEqual(result["status"], "BLOCKED_INVALID_PARAMETERS")
                self.assertTrue(any(item["field"] == field and item["code"] == "MUST_BE_POSITIVE" for item in result["parameter_errors"]))
        for field in ("stage_count", "element_count", "channel_count"):
            with self.subTest(integer_field=field):
                result = matcher.match_one({"equipment_type": "泵", field: 2.5}, self.rules, self.graph)
                self.assertEqual(result["status"], "BLOCKED_INVALID_PARAMETERS")
                self.assertTrue(any(item["field"] == field and item["code"] == "MUST_BE_INTEGER" for item in result["parameter_errors"]))

    def test_exact_aspen_identity_keeps_type_when_saved_zero_results_are_inactive(self) -> None:
        result = matcher.match_one(
            {
                "aspen_block_type": "PUMP",
                "equipment_tag": "P-ZERO",
                "flow_m3_h": 0.0,
                "mass_flow_kg_h": 0.0,
                "gas_molecular_weight": 0.0,
                "pressure_basis": "absolute",
            },
            self.rules,
            self.graph,
        )
        self.assertEqual(result["status"], "MATCHED")
        self.assertEqual(result["match"]["family_id"], "family_pump")
        self.assertTrue(result["model_decision"]["generated_candidate_designation"])
        self.assertEqual(
            {item["field"] for item in result["ignored_parameter_diagnostics"]},
            {"flow_m3_h", "mass_flow_kg_h", "gas_molecular_weight"},
        )
        self.assertEqual(result["effective_normalized_input"]["flow_m3_h"], 10.0)
        self.assertNotIn("mass_flow_kg_h", result["effective_normalized_input"])
        self.assertNotIn("gas_molecular_weight", result["effective_normalized_input"])
        self.assertIn("flow_m3_h", {item["field_id"] for item in result["design_fallbacks"]})

    def test_free_gasket_material_text_is_quarantined_without_blocking_pair_candidate(self) -> None:
        result = matcher.match_one(
            {
                "equipment_family": "family_flange_gasket",
                "equipment_tag": "FG-QUARANTINE",
                "selected_dn": "DN50",
                "pressure_class": "PN16",
                "flange_face": "RF",
                "gasket_material": "invented foam gasket",
            },
            self.rules,
            self.graph,
        )
        self.assertEqual(result["design_parameter_package"]["status"], "READY_FOR_CANDIDATE_MATCHING")
        self.assertEqual(result["effective_normalized_input"]["gasket_material"], "spiral wound graphite")
        self.assertNotIn(
            "invented foam gasket",
            result["model_recommendation"]["leading_candidate"]["designation"],
        )
        self.assertEqual(
            next(item for item in result["ignored_parameter_diagnostics"] if item["field"] == "gasket_material")["status"],
            "IGNORED_UNTRUSTED_COMPONENT_PREFERENCE",
        )

    def test_thickness_formula_nonpositive_denominators_are_hard_blocked(self) -> None:
        result = matcher.match_one(
            {
                "equipment_type": "精馏塔",
                "design_pressure_mpa": 500,
                "design_pressure_basis": "gauge",
                "inner_diameter_mm": 1200,
                "head_type": "2:1_ellipsoidal",
                "allowable_stress_mpa": 100,
                "weld_efficiency": 1.0,
            },
            self.rules,
            self.graph,
        )
        blocked = {
            item["calculation_id"]: item
            for item in result["calculation_pending"]
            if item.get("status") == "BLOCKED_NONPOSITIVE_DENOMINATOR"
        }
        self.assertEqual(set(blocked), {"cylinder_thickness", "head_thickness"})
        self.assertTrue(any(item.startswith("calculation_hard_blocker:cylinder_thickness") for item in result["model_decision"]["verification_missing_fields"]))

    def test_zero_heat_duty_does_not_create_a_zero_area_equipment_closure(self) -> None:
        result = matcher.match_one(
            {
                "equipment_family": "family_fixed_tubesheet_exchanger",
                "heat_duty_kw": 0,
                "overall_u_w_m2k": 500,
                "lmtd_k": 20,
                "lmtd_correction_factor": 0.9,
            },
            self.rules,
            self.graph,
        )
        pending = next(
            item for item in result["calculation_pending"]
            if item["calculation_id"] == "exchanger_area"
        )
        self.assertEqual(pending["status"], "BLOCKED_ZERO_DUTY_NO_EQUIPMENT_LOAD")
        self.assertNotIn("heat_transfer_area_m2", result["derived_parameters"])
        self.assertEqual(result["design_parameter_package"]["status"], "BLOCKED")
        self.assertFalse(result["model_decision"]["candidate_selection_executed"])

    def test_pump_terminal_fallback_includes_density_and_closes_power_chain(self) -> None:
        result = matcher.match_one(
            {"equipment_family": "family_pump", "equipment_tag": "P-FALLBACK"},
            self.rules,
            self.graph,
        )
        fallbacks = {item["field_id"]: item for item in result["design_fallbacks"]}
        self.assertEqual(fallbacks["density_kg_m3"]["value"], 1000.0)
        self.assertIn("hydraulic_power_kw", result["derived_parameters"])
        self.assertIn("shaft_power_kw", result["derived_parameters"])
        self.assertTrue(any(
            item["calculation_id"] == "pump_shaft_power"
            and item["equation_chain"].startswith("shaft_power_kw = rho*g*Q*H/eta =")
            for item in result["calculations"]
        ))

    def test_valve_derives_pressure_drop_cv_and_maximum_drop_before_selection(self) -> None:
        result = matcher.match_one(
            {
                "equipment_family": "family_valve",
                "equipment_tag": "LV-101",
                "phase": "liquid",
                "flow_m3_h": 100.0,
                "density_kg_m3": 800.0,
                "inlet_pressure_mpa": 0.5,
                "outlet_pressure_mpa": 0.2,
                "pressure_basis": "absolute",
            },
            self.rules,
            self.graph,
        )
        self.assertAlmostEqual(result["derived_parameters"]["pressure_drop_kpa"], 300.0)
        self.assertAlmostEqual(
            result["derived_parameters"]["cv"],
            11.56 * 100.0 * math.sqrt(0.8 / 300.0),
        )
        self.assertAlmostEqual(result["derived_parameters"]["maximum_pressure_drop_kpa"], 375.0)
        calculations = {item["calculation_id"]: item for item in result["calculations"]}
        self.assertIn("pressure_drop_kpa = (Pin-Pout)*1000 =", calculations["valve_pressure_drop_from_streams"]["equation_chain"])
        self.assertIn("cv = 11.56*Q*sqrt(SG/dP) =", calculations["valve_liquid_equivalent_cv_screening"]["equation_chain"])
        self.assertIn("maximum_pressure_drop_kpa = dP*kMax =", calculations["valve_maximum_pressure_drop_screening"]["equation_chain"])

    def test_heater_sensible_duty_fallback_closes_area_from_stream_temperature_change(self) -> None:
        result = matcher.match_one(
            {
                "equipment_family": "family_other_heat_exchanger",
                "aspen_block_type": "HEATER",
                "phase": "liquid",
                "mass_flow_kg_h": 3600.0,
                "inlet_temperature_c": 20.0,
                "outlet_temperature_c": 70.0,
            },
            self.rules,
            self.graph,
        )
        self.assertEqual(result["effective_normalized_input"]["specific_heat_kj_kgk"], 2.0)
        self.assertAlmostEqual(result["derived_parameters"]["heat_duty_kw"], 100.0)
        self.assertGreater(result["derived_parameters"]["heat_transfer_area_m2"], 0.0)
        self.assertGreater(result["derived_parameters"]["tube_or_plate_count"], 0.0)
        duty = next(
            item for item in result["calculations"]
            if item["calculation_id"] == "heater_sensible_duty_screening"
        )
        self.assertEqual(
            duty["equation_chain"],
            "heat_duty_kw = m*Cp*(Tout-Tin)/3600 = 3600*2*(70-20)/3600 = 100 kW",
        )

    def test_exchanger_preliminary_structure_is_completed_by_registered_defaults_and_formula(self) -> None:
        result = matcher.match_one(
            {
                "equipment_family": "family_other_heat_exchanger",
                "heat_duty_kw": 1000.0,
            },
            self.rules,
            self.graph,
        )

        fallbacks = {item["field_id"]: item for item in result["design_fallbacks"]}
        self.assertEqual(fallbacks["tube_outer_diameter_mm"]["value"], 25.0)
        self.assertEqual(fallbacks["tube_length_mm"]["value"], 3000.0)
        self.assertEqual(fallbacks["shell_pass_count"]["value"], 1)
        self.assertEqual(fallbacks["tube_material_grade"]["value"], fallbacks["material"]["value"])
        self.assertEqual(fallbacks["shell_material_grade"]["value"], fallbacks["material"]["value"])
        self.assertEqual(result["derived_parameters"]["tube_or_plate_count"], 833)
        calculation = next(
            item for item in result["calculations"]
            if item["calculation_id"] == "exchanger_tube_count"
        )
        self.assertEqual(
            calculation["equation_chain"],
            "tube_or_plate_count = ceil(A/(pi*do*L)) = ceil(196.078/(pi*25/1000*3000/1000)) = 833 count",
        )

    def test_tower_without_flow_gets_visible_final_geometry_and_construction_fallbacks(self) -> None:
        result = matcher.match_one(
            {
                "equipment_family": "family_tower",
                "aspen_block_type": "RADFRAC",
                "stage_count": 10.0,
                "operating_pressure_mpa": 0.1,
                "pressure_basis": "absolute",
            },
            self.rules,
            self.graph,
        )

        fallbacks = {item["field_id"]: item for item in result["design_fallbacks"]}
        self.assertEqual(fallbacks["inner_diameter_mm"]["value"], 600.0)
        self.assertEqual(fallbacks["design_pressure_mpa"]["value"], 0.1)
        self.assertEqual(fallbacks["design_pressure_basis"]["value"], "gauge")
        self.assertTrue(fallbacks["insulation_spec"]["value"])
        self.assertTrue(fallbacks["protective_layer"]["value"])
        self.assertEqual(result["derived_parameters"]["tray_spacing_mm"], 450.0)
        self.assertEqual(result["derived_parameters"]["tower_internal_height_m"], 4.05)
        self.assertEqual(result["derived_parameters"]["height_mm"], 7050.0)

    def test_storage_required_volume_is_separate_from_selected_and_straight_shell_volumes(self) -> None:
        result = matcher.match_one(
            {
                "equipment_family": "family_storage_vessel",
                "flow_m3_h": 100,
                "retention_time_min": 30,
                "fill_fraction": 0.8,
                "volume_m3": 50,
                "volume_basis": "nominal_total",
                "diameter_mm": 2000,
                "height_mm": 5000,
                "inner_diameter_mm": 1800,
                "straight_shell_length_mm": 4000,
                "design_pressure_mpa": 0.6,
                "design_pressure_basis": "gauge",
                "design_temperature_c": 80,
            },
            self.rules,
            self.graph,
        )
        self.assertAlmostEqual(result["derived_parameters"]["required_volume_m3"], 62.5)
        self.assertAlmostEqual(
            result["derived_parameters"]["straight_shell_geometric_volume_m3"],
            10.17876019763093,
        )
        self.assertNotIn("volume_m3", result["derived_parameters"])
        straight_shell = next(
            item for item in result["calculations"]
            if item["calculation_id"] == "cylinder_volume"
        )
        self.assertEqual(
            straight_shell["formula_chain"]["substitution"],
            "pi*(1800/1000)^2*(4000/1000)/4",
        )
        self.assertNotIn("2000", straight_shell["formula_chain"]["substitution"])
        self.assertNotIn("5000", straight_shell["formula_chain"]["substitution"])
        volume_check = next(
            item for item in result["design_parameter_package"]["constraint_checks"]
            if item["check_id"] == "storage_required_volume"
        )
        self.assertEqual(volume_check["status"], "FAIL")
        self.assertEqual(result["model_recommendation"]["status"], "ENGINEERING_CONSTRAINT_FAILED")

    def test_storage_volume_constraint_compares_nominal_geometric_and_effective_bases_with_tolerance(self) -> None:
        cases = (
            ("nominal_total", 62.5, "total_volume", 62.5),
            ("geometric_total", 62.5, "total_volume", 62.5),
            ("effective_working", 50.0, "effective_working_volume", 50.0),
        )
        for basis, selected, comparison_basis, expected_required in cases:
            with self.subTest(basis=basis):
                check = matcher.assess_storage_volume_constraint({
                    "required_volume_m3": 62.5,
                    "volume_m3": selected,
                    "volume_basis": basis,
                    "fill_fraction": 0.8,
                })
                self.assertEqual(check["status"], "PASS")
                self.assertEqual(check["comparison_basis"], comparison_basis)
                self.assertAlmostEqual(
                    check["required_volume_m3_on_comparison_basis"],
                    expected_required,
                )

        exact = matcher.assess_storage_volume_constraint({
            "required_volume_m3": 62.5,
            "volume_m3": 62.5,
            "volume_basis": "nominal_total",
        })
        tolerance = exact["comparison_tolerance_m3"]
        within_tolerance = matcher.assess_storage_volume_constraint({
            "required_volume_m3": 62.5,
            "volume_m3": 62.5 - tolerance / 2,
            "volume_basis": "nominal_total",
        })
        outside_tolerance = matcher.assess_storage_volume_constraint({
            "required_volume_m3": 62.5,
            "volume_m3": 62.5 - tolerance * 2,
            "volume_basis": "nominal_total",
        })
        self.assertLess(within_tolerance["volume_margin_m3"], 0)
        self.assertEqual(within_tolerance["status"], "PASS")
        self.assertEqual(outside_tolerance["status"], "FAIL")

    def test_straight_shell_length_m_normalizes_to_mm_and_controls_cylinder_volume(self) -> None:
        result = matcher.match_one(
            {
                "equipment_family": "family_storage_vessel",
                "diameter_mm": 2000,
                "height_mm": 5000,
                "inner_diameter_mm": 1800,
                "straight_shell_length_m": 4,
            },
            self.rules,
            self.graph,
        )
        self.assertAlmostEqual(result["normalized_input"]["straight_shell_length_mm"], 4000)
        self.assertAlmostEqual(
            result["derived_parameters"]["straight_shell_geometric_volume_m3"],
            10.17876019763093,
        )
        volume = next(
            item for item in result["calculations"]
            if item["calculation_id"] == "cylinder_volume"
        )
        self.assertEqual(
            volume["formula_chain"]["substitution"],
            "pi*(1800/1000)^2*(4000/1000)/4",
        )

    def test_general_body_diameter_and_height_do_not_close_straight_shell_volume(self) -> None:
        result = matcher.match_one(
            {
                "equipment_family": "family_storage_vessel",
                "diameter_mm": 2000,
                "height_mm": 5000,
            },
            self.rules,
            self.graph,
        )
        self.assertNotIn("straight_shell_geometric_volume_m3", result["derived_parameters"])
        self.assertFalse(any(
            item["calculation_id"] == "cylinder_volume"
            for item in result["calculations"]
        ))
        pending = next(
            item for item in result["calculation_pending"]
            if item["calculation_id"] == "cylinder_volume"
        )
        self.assertEqual(
            pending["missing_fields"],
            ["inner_diameter_mm", "straight_shell_length_mm"],
        )

    def test_explicit_storage_volume_can_route_without_forcing_one_residence_time_formula(self) -> None:
        result = matcher.match_one(
            {
                "equipment_family": "family_storage_vessel",
                "volume_m3": 50,
                "volume_basis": "nominal_total",
                "design_pressure_mpa": 0.6,
                "design_pressure_basis": "gauge",
                "design_temperature_c": 80,
            },
            self.rules,
            self.graph,
        )
        volume_check = next(
            item for item in result["design_parameter_package"]["constraint_checks"]
            if item["check_id"] == "storage_required_volume"
        )
        self.assertEqual(volume_check["status"], "UNKNOWN")
        self.assertEqual(
            result["model_recommendation"]["selection_execution"]["status"],
            "EXECUTED",
        )
        self.assertFalse(any(
            item.startswith("engineering_constraint_unknown:storage_required_volume")
            for item in result["model_decision"]["engineering_constraint_blockers"]
        ))

    def test_liquid_turbine_reports_pressure_drop_component_not_total_hydraulic_power(self) -> None:
        result = matcher.match_one(
            {
                "equipment_family": "family_liquid_power_recovery_turbine",
                "phase": "liquid",
                "flow_m3_h": 50,
                "inlet_pressure_mpa": 2.0,
                "outlet_pressure_mpa": 0.5,
                "pressure_basis": "absolute",
                "density_kg_m3": 1000,
                "efficiency_percent": 80,
            },
            self.rules,
            self.graph,
        )
        calculations = {item["calculation_id"]: item for item in result["calculations"]}
        ratio = calculations["pressure_ratio"]
        head_component = calculations["liquid_turbine_pressure_head"]
        pressure_component = calculations["liquid_turbine_hydraulic_power"]
        shaft = calculations["liquid_turbine_shaft_power"]
        self.assertEqual(head_component["target_field"], "pressure_drop_head_component_m")
        self.assertAlmostEqual(head_component["value"], 152.95743194668924)
        self.assertEqual(pressure_component["target_field"], "pressure_drop_power_component_kw")
        self.assertAlmostEqual(pressure_component["value"], 20.833333333333332)
        self.assertEqual(
            shaft["target_field"],
            "pressure_component_shaft_power_screening_kw",
        )
        self.assertAlmostEqual(shaft["value"], 16.666666666666664)
        for item in (head_component, pressure_component, shaft):
            notice = item["calculation_notice"]
            self.assertEqual(notice["release_class"], "B")
            self.assertEqual(notice["evidence_class"], "J")
            self.assertEqual(notice["result_status"], "PROVISIONAL")
            self.assertEqual(notice["promotion_cap"], "TYPE_SCREENING")
        self.assertIn("pressure_drop_head_component_m", result["derived_parameters"])
        self.assertIn("pressure_drop_power_component_kw", result["derived_parameters"])
        self.assertIn("pressure_component_shaft_power_screening_kw", result["derived_parameters"])
        self.assertNotIn("shaft_power_kw", result["derived_parameters"])
        self.assertIn("pressure_drop_power_component_kw =", pressure_component["equation_chain"])
        self.assertIn(
            "pressure_component_shaft_power_screening_kw =",
            shaft["equation_chain"],
        )
        self.assertEqual(ratio["formula_chain"]["substitution"], "(2+0)/(0.5+0)")
        self.assertAlmostEqual(
            eval(ratio["formula_chain"]["substitution"], {"__builtins__": {}}),
            ratio["value"],
        )

    def test_liquid_turbine_gauge_pressures_use_visible_atmosphere_fallback(self) -> None:
        result = matcher.match_one(
            {
                "equipment_family": "family_liquid_power_recovery_turbine",
                "phase": "liquid",
                "flow_m3_h": 50,
                "inlet_pressure_mpa": 2.0,
                "outlet_pressure_mpa": 0.5,
                "pressure_basis": "gauge",
                "density_kg_m3": 1000,
                "efficiency_percent": 80,
            },
            self.rules,
            self.graph,
        )
        ratio = next(
            item for item in result["calculations"]
            if item["calculation_id"] == "pressure_ratio"
        )
        self.assertAlmostEqual(ratio["value"], (2.0 + 0.101325) / (0.5 + 0.101325))
        atmosphere = next(
            item for item in result["design_fallbacks"]
            if item["field_id"] == "atmospheric_pressure_mpa"
        )
        self.assertEqual(atmosphere["tier"], "EXPLICIT_FINAL_FALLBACK_DEFAULT")
        self.assertIn("expansion_pressure_ratio", result["derived_parameters"])
        self.assertIn("pressure_drop_power_component_kw", result["derived_parameters"])
        self.assertEqual(
            result["model_recommendation"]["selection_execution"]["status"],
            "EXECUTED",
        )
        self.assertTrue(result["model_decision"]["candidate_selection_executed"])

    def test_membrane_area_requires_an_explicit_supported_geometry_branch(self) -> None:
        base = {
            "equipment_family": "family_membrane",
            "element_count": 2,
            "channel_count": 100,
            "channel_inner_diameter_mm": 5,
            "element_length_m": 1,
        }
        missing = matcher.match_one(base, self.rules, self.graph)
        missing_area = next(
            item for item in missing["calculations"]
            if item["calculation_id"] == "membrane_area"
        )
        self.assertEqual(
            missing_area["formula_branch"]["membrane_geometry_type"],
            "cylindrical_channels",
        )
        self.assertEqual(
            next(
                item for item in missing["design_fallbacks"]
                if item["field_id"] == "membrane_geometry_type"
            )["tier"],
            "EXPLICIT_FINAL_FALLBACK_DEFAULT",
        )
        unsupported = matcher.match_one(
            {**base, "membrane_geometry_type": "spiral_wound"},
            self.rules,
            self.graph,
        )
        unsupported_pending = next(
            item for item in unsupported["calculation_pending"]
            if item["calculation_id"] == "membrane_area"
        )
        self.assertEqual(unsupported_pending["status"], "BLOCKED_UNSUPPORTED_FORMULA_BRANCH")
        supported = matcher.match_one(
            {**base, "membrane_geometry_type": "cylindrical_channels"},
            self.rules,
            self.graph,
        )
        area = next(
            item for item in supported["calculations"]
            if item["calculation_id"] == "membrane_area"
        )
        self.assertAlmostEqual(area["value"], 3.1415926535897936)
        self.assertEqual(
            area["formula_branch"]["membrane_geometry_type"],
            "cylindrical_channels",
        )

    def test_unsupported_membrane_geometry_can_use_an_explicit_external_area(self) -> None:
        result = matcher.match_one(
            {
                "equipment_family": "family_membrane",
                "membrane_geometry_type": "spiral_wound",
                "membrane_area_m2": 120,
                "flux": 10,
                "selectivity": 2,
                "recovery_percent": 80,
                "design_pressure_mpa": 1.0,
                "design_pressure_basis": "gauge",
            },
            self.rules,
            self.graph,
        )
        self.assertFalse(any(
            item["calculation_id"] == "membrane_area"
            for item in result["calculations"]
        ))
        self.assertFalse(any(
            item["calculation_id"] == "membrane_area"
            for item in result["calculation_pending"]
        ))
        self.assertNotIn("membrane_area_m2", result["derived_parameters"])
        area_row = next(
            row
            for group in result["design_parameter_package"]["groups"]
            for row in group["rows"]
            if row["field_id"] == "membrane_area_m2"
        )
        self.assertEqual(area_row["state"], "PROVIDED")
        self.assertEqual(area_row["source"]["kind"], "normalized_input")
        self.assertEqual(result["model_decision"]["formula_promotion_cap"], "TYPE_SCREENING")
        self.assertTrue(result["model_decision"]["fallback_promotion_blockers"])
        self.assertEqual(
            result["model_recommendation"]["selection_execution"]["status"],
            "EXECUTED",
        )

    def test_tower_area_and_holdup_use_explicit_inner_diameter(self) -> None:
        result = matcher.match_one(
            {
                "equipment_family": "family_tower",
                "diameter_mm": 2000,
                "inner_diameter_mm": 1000,
                "flow_m3_h": 60,
                "retention_time_min": 10,
            },
            self.rules,
            self.graph,
        )
        self.assertAlmostEqual(result["derived_parameters"]["tower_cross_section_m2"], 0.7853981633974483)
        self.assertAlmostEqual(result["derived_parameters"]["bottom_liquid_height_m"], 12.732395447351628)
        area = next(
            item for item in result["calculations"]
            if item["calculation_id"] == "tower_cross_section"
        )
        self.assertIn("1000/1000", area["formula_chain"]["substitution"])

    def test_tower_preliminary_diameter_formula_and_substitution_use_same_rounding_basis(self) -> None:
        result = matcher.match_one(
            {
                "equipment_family": "family_tower",
                "flow_m3_h": 3600,
                "tower_design_velocity_m_s": 1.5,
            },
            self.rules,
            self.graph,
        )
        calculation = next(
            item for item in result["calculations"]
            if item["calculation_id"] == "tower_preliminary_diameter"
        )
        self.assertEqual(
            calculation["formula_chain"]["formula"],
            "ceil_100mm(sqrt(4Q/(3600*pi*uDesign)))",
        )
        self.assertTrue(
            calculation["formula_chain"]["substitution"].startswith("ceil_100mm("),
            calculation["formula_chain"]["substitution"],
        )

    def test_unspecified_radfrac_terminal_type_uses_registered_default_instead_of_staying_ambiguous(self) -> None:
        result = matcher.match_one(
            {
                "aspen_block_type": "RADFRAC",
                "stage_count": 30,
                "inner_diameter_mm": 1600,
            },
            self.rules,
            self.graph,
        )
        recommendation = result["model_recommendation"]
        terminal = recommendation["terminal_selection"]
        self.assertEqual(recommendation["recommended_type"], "单溢流筛板塔")
        self.assertEqual(terminal["status"], "DEFAULTED_TERMINAL_TYPE_SELECTED")
        self.assertEqual(terminal["selection_basis"], "registered_default")
        self.assertTrue(terminal["default_applied"])
        self.assertEqual(terminal["recommended_type"], recommendation["recommended_type"])
        self.assertNotIn("待", recommendation["recommended_type"])
        self.assertNotIn("或", recommendation["recommended_type"])
        self.assertEqual(
            recommendation["leading_candidate"]["terminal_selection"],
            terminal,
        )

    def test_registered_external_condition_rule_can_upgrade_default_terminal_form_without_free_text_type(self) -> None:
        result = matcher.match_one(
            {
                "equipment_tag": "T-API-CONDITION",
                "aspen_block_type": "RADFRAC",
                "process_function": "vacuum distillation; low pressure drop; clean non-fouling service",
                "terminal_type_rule_override_id": "tower:semantic:vacuum_low_pressure_drop_structured_packing",
            },
            self.rules,
            self.graph,
        )

        terminal = result["model_recommendation"]["terminal_selection"]
        self.assertEqual(terminal["status"], "CONDITIONED_TERMINAL_TYPE_SELECTED")
        self.assertEqual(terminal["recommended_type"], "规整填料塔")
        self.assertEqual(terminal["selection_basis"], "controlled_registered_condition_rule")
        self.assertEqual(
            terminal["rule_id"],
            "tower:semantic:vacuum_low_pressure_drop_structured_packing",
        )
        self.assertFalse(terminal["default_applied"])
        self.assertTrue(terminal["provisional"])
        self.assertNotIn("equipment_type", result["normalized_input"])
        self.assertEqual(
            result["normalized_input"]["terminal_type_rule_override_id"],
            "tower:semantic:vacuum_low_pressure_drop_structured_packing",
        )

    def test_heater_terminal_type_uses_duty_direction_and_never_returns_other_or_pending_type(self) -> None:
        cases = [
            (120.0, "固定管板式管壳加热器", "heat_exchanger:heater_positive_duty"),
            (-120.0, "固定管板式管壳冷却器", "heat_exchanger:heater_negative_duty"),
        ]
        for duty, expected_type, expected_rule in cases:
            with self.subTest(duty=duty):
                result = matcher.match_one(
                    {"aspen_block_type": "HEATER", "heat_duty_kw": duty},
                    self.rules,
                    self.graph,
                )
                recommendation = result["model_recommendation"]
                terminal = recommendation["terminal_selection"]
                self.assertEqual(recommendation["recommended_type"], expected_type)
                self.assertEqual(terminal["status"], "DEFAULTED_TERMINAL_TYPE_SELECTED")
                self.assertEqual(terminal["selection_basis"], "condition_rule_with_registered_default")
                self.assertEqual(terminal["rule_id"], expected_rule)
                self.assertTrue(terminal["default_applied"])
                self.assertNotIn("其他", recommendation["recommended_type"])
                self.assertNotIn("待", recommendation["recommended_type"])

    def test_fixed_bkp_physical_block_types_all_have_unambiguous_terminal_equipment_forms(self) -> None:
        expected = {
            "BATCHSEP": "间歇筛板精馏塔",
            "COMPR": "离心式压缩机",
            "DECANTER": "卧式液液倾析器",
            "FLASH2": "立式气液闪蒸分离罐",
            "FLASH3": "卧式三相分离器",
            "HEATER": "固定管板式管壳加热器",
            "HEATX": "固定管板式管壳流程换热器",
            "MCOMPR": "多级离心式压缩机",
            "PUMP": "轴向吸入离心泵",
            "RADFRAC": "单溢流筛板塔",
            "RCSTR": "连续搅拌釜式反应器",
            "RPLUG": "管式平推流反应器",
            "RSTOIC": "连续搅拌釜式反应器（RSTOIC 默认实现）",
            "SEP": "立式工艺分离罐",
            "VALVE": "单座直通调节阀",
        }
        for block_type, expected_type in expected.items():
            with self.subTest(block_type=block_type):
                result = matcher.match_one(
                    {"aspen_block_type": block_type},
                    self.rules,
                    self.graph,
                )
                recommendation = result["model_recommendation"]
                terminal = recommendation["terminal_selection"]
                self.assertEqual(recommendation["recommended_type"], expected_type)
                self.assertIn(
                    terminal["status"],
                    {
                        "CONDITIONED_TERMINAL_TYPE_SELECTED",
                        "DEFAULTED_TERMINAL_TYPE_SELECTED",
                    },
                )
                self.assertEqual(terminal["terminal_scope"], "equipment_form")
                self.assertTrue(terminal["rule_id"])
                self.assertNotEqual(terminal["selection_basis"], "legacy_generic_type")
                for unresolved in ("待", "或", "其他", "候选"):
                    self.assertNotIn(unresolved, recommendation["recommended_type"])

    def test_generic_family_labels_are_not_mistaken_for_explicit_terminal_forms(self) -> None:
        model_rules = matcher.load_model_rules()
        families = model_rules.get("families", [])
        self.assertTrue(families)
        for family_rule in families:
            family_id = family_rule["family_id"]
            generic_inputs = family_rule.get("generic_identity_inputs", [])
            with self.subTest(family_id=family_id):
                self.assertTrue(generic_inputs, f"{family_id} has no registered generic identity")
                result = matcher.match_one(
                    {
                        "equipment_family": family_id,
                        "equipment_type": generic_inputs[0],
                    },
                    self.rules,
                    self.graph,
                )
                terminal = result["model_recommendation"]["terminal_selection"]
                self.assertEqual(terminal["status"], "DEFAULTED_TERMINAL_TYPE_SELECTED")
                self.assertEqual(terminal["selection_basis"], "registered_default")
                self.assertNotEqual(terminal["recommended_type"], generic_inputs[0])

    def test_condition_selected_pump_form_is_not_overwritten_by_incompatible_standard_marking_route(self) -> None:
        result = matcher.match_one(
            {
                "aspen_block_type": "PUMP",
                "phase": "liquid",
                "flow_m3_h": 50.0,
                "head_m": 300.0,
            },
            self.rules,
            self.graph,
        )
        recommendation = result["model_recommendation"]
        terminal = recommendation["terminal_selection"]
        self.assertEqual(recommendation["recommended_type"], "多级离心泵")
        self.assertEqual(terminal["status"], "CONDITIONED_TERMINAL_TYPE_SELECTED")
        self.assertEqual(terminal["rule_id"], "pump:high_head:multistage_centrifugal")
        self.assertFalse(terminal["default_applied"])
        self.assertEqual(
            recommendation["leading_candidate"]["candidate_id"],
            "family_pump:engineering-designation",
        )
        self.assertEqual(
            recommendation["leading_candidate"]["recommended_type"],
            "多级离心泵",
        )
        self.assertEqual(
            recommendation["pump_standard_lookup"]["status"],
            "NOT_APPLICABLE_TERMINAL_TYPE",
        )

    def test_head_thickness_missing_branch_uses_visible_ellipsoidal_fallback(self) -> None:
        base = {
            "equipment_family": "family_storage_vessel",
            "design_pressure_mpa": 1.0,
            "design_pressure_basis": "gauge",
            "inner_diameter_mm": 1200,
            "allowable_stress_mpa": 120,
            "weld_efficiency": 0.85,
        }
        missing = matcher.match_one(base, self.rules, self.graph)
        calculation = next(item for item in missing["calculations"] if item["calculation_id"] == "head_thickness")
        self.assertEqual(calculation["formula_branch"]["head_type"], "2:1_ellipsoidal")
        self.assertIn("head_calculated_thickness_mm", missing["derived_parameters"])
        head_fallback = next(item for item in missing["design_fallbacks"] if item["field_id"] == "head_type")
        self.assertEqual(head_fallback["tier"], "KNOWLEDGE_GRAPH_CONDITIONAL_RECOMMENDATION")

        unsupported = matcher.match_one({**base, "head_type": "hemispherical"}, self.rules, self.graph)
        unsupported_pending = next(item for item in unsupported["calculation_pending"] if item["calculation_id"] == "head_thickness")
        self.assertEqual(unsupported_pending["status"], "BLOCKED_UNSUPPORTED_FORMULA_BRANCH")

        selected = matcher.match_one({**base, "head_type": "2:1 ellipsoidal"}, self.rules, self.graph)
        calculation = next(item for item in selected["calculations"] if item["calculation_id"] == "head_thickness")
        self.assertEqual(calculation["formula_branch"]["head_type"], "2:1_ellipsoidal")

    def test_external_head_thickness_does_not_require_builtin_head_branch(self) -> None:
        result = matcher.match_one(
            {
                "equipment_family": "family_storage_vessel",
                "head_type": "hemispherical",
                "head_calculated_thickness_mm": 12.0,
            },
            self.rules,
            self.graph,
        )
        self.assertFalse(any(item["calculation_id"] == "head_thickness" for item in result["calculation_pending"]))
        self.assertEqual(result["normalized_input"]["head_calculated_thickness_mm"], 12.0)

    def test_negative_gauge_operating_pressure_uses_external_pressure_branch(self) -> None:
        result = matcher.match_one(
            {
                "equipment_type": "精馏塔",
                "operating_pressure_mpa": -0.05,
                "design_pressure_factor": 1.1,
                "pressure_basis": "gauge",
                "atmospheric_pressure_mpa": 0.101325,
            },
            self.rules,
            self.graph,
        )
        blocked = next(item for item in result["calculation_pending"] if item["calculation_id"] == "design_pressure")
        self.assertEqual(blocked["status"], "BLOCKED_EXTERNAL_PRESSURE_BRANCH_REQUIRED")
        self.assertTrue(any(item.startswith("calculation_hard_blocker:design_pressure") for item in result["model_decision"]["verification_missing_fields"]))

    def test_final_model_requires_full_machine_evidence(self) -> None:
        with workspace_temporary_directory() as temporary_directory:
            evidence = {}
            for name in ("vendor_datasheet", "vendor_curve", "formal_calculation"):
                path = Path(temporary_directory) / f"{name}.txt"
                path.write_text(f"machine-verifiable {name}\n", encoding="utf-8")
                evidence[f"{name}_path"] = str(path)
                evidence[f"{name}_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            manifest_path = Path(temporary_directory) / "evidence_manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "schema": "equipment-evidence-manifest-v1",
                        "equipment_tag": "P-101",
                        "family_id": "family_pump",
                        "selected_model": "VENDOR-VERIFIED-X",
                        "closed_gates": [
                            "Q_H_point", "efficiency", "BEP", "NPSHa_NPSHr",
                            "material_and_seal", "vendor_datasheet",
                            "gate_pump_freeze_20260712", "gate_evidence_reuse_classification",
                        ],
                        "gate_evidence": {
                            "Q_H_point": ["vendor_curve", "parameter:flow_m3_h", "parameter:head_m"],
                            "efficiency": ["vendor_curve", "parameter:efficiency_percent"],
                            "BEP": ["vendor_curve"],
                            "NPSHa_NPSHr": [
                                "vendor_curve", "parameter:npsha_m", "parameter:npshr_m",
                                "parameter:required_npsh_margin_m", "parameter:npshr_evidence_scope",
                            ],
                            "material_and_seal": ["vendor_datasheet"],
                            "vendor_datasheet": ["vendor_datasheet"],
                            "gate_pump_freeze_20260712": ["formal_calculation"],
                            "gate_evidence_reuse_classification": ["formal_calculation"],
                        },
                        "artifacts": {
                            name: {
                                "evidence_kind": name,
                                "equipment_tag": "P-101",
                                "family_id": "family_pump",
                                "selected_model": "VENDOR-VERIFIED-X",
                                "path": evidence[f"{name}_path"],
                                "sha256": evidence[f"{name}_sha256"],
                            }
                            for name in ("vendor_datasheet", "vendor_curve", "formal_calculation")
                        },
                        "verification_result": "PASS",
                        "approval_status": "approved",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            evidence["evidence_manifest_path"] = str(manifest_path)
            evidence["evidence_manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            base_record = {
                "equipment_tag": "P-101",
                "equipment_type": "泵",
                "flow_m3_h": 36,
                "head_m": 45,
                "density_kg_m3": 850,
                "efficiency_percent": 72,
                "npsha_m": 5.2,
                "npshr_m": 3.1,
                "required_npsh_margin_m": 1.0,
                "npshr_evidence_scope": "same_duty_vendor_curve",
                "vendor_model": "VENDOR-VERIFIED-X",
                **evidence,
                "verification_result": "PASS",
                "approval_status": "approved",
            }
            preapproval = matcher.match_one(base_record, self.rules, self.graph)
            self.assertEqual(preapproval["model_decision"]["model_status"], "type_selected")
            preapproval_npsh = next(
                item for item in preapproval["design_parameter_package"]["constraint_checks"]
                if item["check_id"] == "pump_npsh_margin"
            )
            self.assertEqual(preapproval_npsh["status"], "UNKNOWN")
            self.assertIn("audit_approval_path", preapproval_npsh["evidence_missing_fields"])
            approval_path = Path(temporary_directory) / "audit_approval.json"
            approval_path.write_text(
                json.dumps(
                    {
                        "schema": "equipment-audit-approval-v1",
                        "review_id": "TEST-INDEPENDENT-001",
                        "reviewer_role": "independent_kg_chemical_expert",
                        "decision": "PASS",
                        "equipment_tag": "P-101",
                        "family_id": "family_pump",
                        "selected_model": "VENDOR-VERIFIED-X",
                        "evidence_manifest_sha256": evidence["evidence_manifest_sha256"],
                        "reviewed_gates": [
                            "Q_H_point", "efficiency", "BEP", "NPSHa_NPSHr",
                            "material_and_seal", "vendor_datasheet",
                            "gate_pump_freeze_20260712", "gate_evidence_reuse_classification",
                        ],
                        "approval_status": "approved",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            evidence["audit_approval_path"] = str(approval_path)
            evidence["audit_approval_sha256"] = hashlib.sha256(approval_path.read_bytes()).hexdigest()
            result = matcher.match_one({**base_record, **evidence}, self.rules, self.graph)
        self.assertEqual(result["model_decision"]["model_status"], "final_model")
        self.assertEqual(result["model_decision"]["formal_ready_candidate_count"], 1)
        self.assertEqual(result["model_recommendation"]["formal_ready_candidate_count"], 1)
        npsh_check = next(
            item for item in result["design_parameter_package"]["constraint_checks"]
            if item["check_id"] == "pump_npsh_margin"
        )
        self.assertEqual(npsh_check["status"], "PASS")
        self.assertTrue(npsh_check["same_case_evidence_complete"])

    def test_well_formed_hash_without_file_path_cannot_upgrade_evidence(self) -> None:
        result = matcher.match_one(
            {
                "equipment_type": "泵",
                "vendor_model": "UNVERIFIED-X",
                "vendor_datasheet_sha256": "A" * 64,
            },
            self.rules,
            self.graph,
        )
        self.assertEqual(result["status"], "BLOCKED_INVALID_PARAMETERS")
        self.assertTrue(any(item["code"] == "MISSING_EVIDENCE_PATH" for item in result["parameter_errors"]))

    def test_custom_tower_can_reach_final_design_without_claiming_a_universal_vendor_model(self) -> None:
        with workspace_temporary_directory() as temporary_directory:
            root = Path(temporary_directory)
            evidence = {}
            kinds = ("internals_result", "mechanical_result", "formal_calculation")
            for kind in kinds:
                path = root / f"{kind}.txt"
                path.write_text(f"tower-specific {kind}\n", encoding="utf-8")
                evidence[f"{kind}_path"] = str(path)
                evidence[f"{kind}_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            gates = [
                "process_basis", "Column_Internals_or_vendor",
                "mechanical_design", "gate_evidence_reuse_classification",
            ]
            manifest = {
                "schema": "equipment-evidence-manifest-v1",
                "equipment_tag": "T-101",
                "family_id": "family_tower",
                "selected_model": "T-101-CUSTOM-REV-A",
                "closed_gates": gates,
                "gate_evidence": {
                    "process_basis": ["formal_calculation"],
                    "Column_Internals_or_vendor": ["internals_result"],
                    "mechanical_design": ["mechanical_result"],
                    "gate_evidence_reuse_classification": ["formal_calculation"],
                },
                "artifacts": {
                    kind: {
                        "evidence_kind": kind,
                        "equipment_tag": "T-101",
                        "family_id": "family_tower",
                        "selected_model": "T-101-CUSTOM-REV-A",
                        "path": evidence[f"{kind}_path"],
                        "sha256": evidence[f"{kind}_sha256"],
                    }
                    for kind in kinds
                },
                "verification_result": "PASS",
                "approval_status": "approved",
            }
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
            evidence["evidence_manifest_path"] = str(manifest_path)
            evidence["evidence_manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            approval = {
                "schema": "equipment-audit-approval-v1",
                "review_id": "TEST-TOWER-001",
                "reviewer_role": "independent_kg_chemical_expert",
                "decision": "PASS",
                "equipment_tag": "T-101",
                "family_id": "family_tower",
                "selected_model": "T-101-CUSTOM-REV-A",
                "evidence_manifest_sha256": evidence["evidence_manifest_sha256"],
                "reviewed_gates": gates,
                "approval_status": "approved",
            }
            approval_path = root / "approval.json"
            approval_path.write_text(json.dumps(approval, ensure_ascii=False), encoding="utf-8")
            evidence["audit_approval_path"] = str(approval_path)
            evidence["audit_approval_sha256"] = hashlib.sha256(approval_path.read_bytes()).hexdigest()
            result = matcher.match_one(
                {
                    "equipment_tag": "T-101",
                    "equipment_type": "精馏塔",
                    "candidate_model": "T-101-CUSTOM-REV-A",
                    "diameter_mm": 1200,
                    "inner_diameter_mm": 1200,
                    "height_mm": 18000,
                    "stage_count": 40,
                    "design_pressure_mpa": 0.6,
                    "design_pressure_basis": "gauge",
                    "design_temperature_c": 130,
                    **evidence,
                    "verification_result": "PASS",
                    "approval_status": "approved",
                },
                self.rules,
                self.graph,
            )
        self.assertEqual(result["model_decision"]["policy"], "custom_engineered_equipment")
        self.assertEqual(result["model_decision"]["model_status"], "final_model")
        self.assertIsNone(result["model_decision"]["vendor_model"])

    def test_all_family_parameter_templates_build_nonempty_visual_groups(self) -> None:
        for family in self.rules["families"]:
            with self.subTest(family=family["id"]):
                result = matcher.match_one({"equipment_family": family["id"]}, self.rules, self.graph)
                package = result["design_parameter_package"]
                self.assertEqual(package["schema"], "equipment-design-parameter-package-v1")
                self.assertTrue(package["groups"])
                self.assertTrue(any(group["rows"] for group in package["groups"]))
                self.assertFalse(package["llm_used"])

    def test_customer_profile_map_covers_all_algorithm_families_without_alias_collisions(self) -> None:
        profiles = matcher.load_customer_output_profiles(required=True)
        templates = matcher.load_parameter_templates()
        template_map = {
            item["family_id"]: item.get("customer_profile_ids", [])
            for item in templates["families"]
        }
        expected_map = {
            family_id: (
                value.get("profile_ids", []) if isinstance(value, dict) else value
            )
            for family_id, value in profiles["algorithm_family_profile_map"].items()
        }
        self.assertEqual(set(template_map), set(expected_map))
        for family_id, expected in expected_map.items():
            with self.subTest(family_id=family_id):
                self.assertEqual(template_map[family_id], expected)
        self.assertEqual(matcher.ALIAS_COLLISIONS, [])

    def test_equipment_name_never_becomes_equipment_identity_or_type(self) -> None:
        normalized, conflicts, unmapped = matcher.normalize_record({"设备名称": "原料泵"})
        self.assertEqual(normalized, {"equipment_name": "原料泵"})
        self.assertEqual(conflicts, [])
        self.assertEqual(unmapped, {})
        result = matcher.match_one({"设备名称": "原料泵"}, self.rules, self.graph)
        self.assertEqual(result.get("match", {}).get("status"), "BLOCKED_MISSING_DECISIVE_IDENTITY")
        self.assertNotIn("family_id", result.get("match", {}))
        self.assertEqual(result["progress"]["state"], "NEEDS_IDENTITY")

    def test_output_only_customer_fields_cannot_override_model_state(self) -> None:
        normalized, conflicts, unmapped = matcher.normalize_record({
            "型号状态": "final_model",
            "型号/候选标记": "FORGED-MODEL",
            "证据等级": "A4",
        })
        self.assertEqual(normalized, {})
        self.assertEqual(conflicts, [])
        self.assertEqual(set(unmapped), {"型号状态", "型号/候选标记", "证据等级"})

    def test_calculated_outputs_propagate_into_selection_parameter_package(self) -> None:
        result = matcher.match_one({
            "equipment_type": "固定管板式换热器",
            "heat_duty_kw": 1000,
            "overall_u_w_m2k": 500,
            "lmtd_k": 40,
            "lmtd_correction_factor": 1.0,
            "operating_pressure_mpa": 1.0,
            "pressure_basis": "gauge",
            "design_pressure_factor": 1.1,
            "design_temperature_c": 160,
        }, self.rules, self.graph)
        self.assertAlmostEqual(result["derived_parameters"]["heat_transfer_area_m2"], 50.0)
        self.assertAlmostEqual(result["derived_parameters"]["design_pressure_mpa"], 1.1)
        vector = result["design_parameter_package"]["selection_feature_vector"]
        self.assertEqual(vector["status"], "READY")
        self.assertEqual(result["model_recommendation"]["selection_execution"]["feature_vector_sha256"], vector["sha256"])

    def test_required_pipe_diameter_selects_standard_dn_and_recalculates_velocity(self) -> None:
        result = matcher.match_one({
            "equipment_type": "工艺管道",
            "flow_m3_h": 50,
            "target_velocity_m_s": 1.5,
        }, self.rules, self.graph)
        self.assertIn("required_inner_diameter_mm", result["derived_parameters"])
        self.assertEqual(result["derived_parameters"]["selected_dn"], 125.0)
        self.assertEqual(result["derived_parameters"]["selected_outer_diameter_mm"], 141.3)
        self.assertIn("actual_velocity_m_s", result["derived_parameters"])
        self.assertNotIn("selected_dn", result["design_parameter_package"]["selection_feature_vector"]["missing_fields"])
        standard_rows = [
            item for item in result["calculations"]
            if item["calculation_id"] == "pipe_standard_dn_selection"
        ]
        self.assertEqual({item["target_field"] for item in standard_rows}, {"selected_dn", "selected_outer_diameter_mm"})
        self.assertTrue(all(item["standard_catalog_record"]["standard_id"] == "GB/T 12459-2025" for item in standard_rows))

    def test_supplied_pipe_size_is_preserved_and_standard_selection_is_only_crosscheck(self) -> None:
        result = matcher.match_one({
            "equipment_type": "工艺管道",
            "flow_m3_h": 10,
            "target_velocity_m_s": 1.5,
            "selected_dn": "DN80",
            "selected_outer_diameter_mm": 88.9,
            "selected_wall_thickness_mm": 5.0,
        }, self.rules, self.graph)
        self.assertEqual(result["effective_normalized_input"]["selected_dn"], 80)
        self.assertEqual(result["effective_normalized_input"]["selected_outer_diameter_mm"], 88.9)
        standard_rows = [
            item for item in result["calculations"]
            if item["calculation_id"] == "pipe_standard_dn_selection"
        ]
        self.assertTrue(standard_rows)
        self.assertTrue(all(item["adopted_as_canonical"] is False for item in standard_rows))

    def test_every_numeric_calculated_parameter_row_has_unit_and_formula_chain(self) -> None:
        result = matcher.match_one({
            "equipment_type": "泵", "flow_m3_h": 20,
            "inlet_pressure_mpa": 0.2, "outlet_pressure_mpa": 0.6,
            "pressure_basis": "absolute",
            "density_kg_m3": 900, "efficiency_percent": 75,
        }, self.rules, self.graph)
        rows = [row for group in result["design_parameter_package"]["groups"] for row in group["rows"]]
        calculated = [row for row in rows if row["state"] == "CALCULATED"]
        self.assertTrue(calculated)
        self.assertTrue(all(row["unit"] and row["formula_chain"] for row in calculated))

    def test_solids_block_overlays_are_visible_without_invented_values(self) -> None:
        expected_fields = {
            "CRYSTALLIZER": {"solubility_profile_ref", "crystal_component_mapping", "working_volume_m3"},
            "FILTER": {"filtration_flux_kg_m2_h", "cake_specific_resistance_m_kg", "filter_area_m2"},
            "DRYER": {"moisture_basis", "water_component_mapping", "evaporation_rate_kg_h"},
        }
        for block_type, fields in expected_fields.items():
            with self.subTest(block_type=block_type):
                result = matcher.match_one({"aspen_block_type": block_type}, self.rules, self.graph)
                package = result["design_parameter_package"]
                self.assertEqual(package["block_type_overlay"]["block_type"], block_type)
                rows = {
                    row["field_id"]: row
                    for group in package["groups"]
                    for row in group["rows"]
                }
                self.assertTrue(fields.issubset(rows))
                for field in fields:
                    self.assertIn(rows[field]["state"], {"MISSING", "EXTERNAL_REQUIRED"})
                    self.assertIsNone(rows[field]["raw_value"])
                forbidden_generic_defaults = {
                    "CRYSTALLIZER": {"volume_m3", "diameter_mm", "height_mm"},
                    "FILTER": {"capacity", "cycle_time_h", "allowable_pressure_drop_kpa"},
                    "DRYER": {"capacity", "cycle_time_h", "allowable_pressure_drop_kpa"},
                }[block_type]
                applied_fallbacks = {
                    item["field_id"] for item in package.get("design_fallbacks", [])
                }
                self.assertTrue(forbidden_generic_defaults.isdisjoint(applied_fallbacks))

    def test_solids_overlay_formulas_run_only_from_explicit_same_basis_inputs(self) -> None:
        crystallizer = matcher.match_one({
            "aspen_block_type": "CRYSTALLIZER",
            "slurry_flow_m3_h": 12.0,
            "retention_time_min": 30.0,
        }, self.rules, self.graph)
        self.assertAlmostEqual(crystallizer["derived_parameters"]["working_volume_m3"], 6.0)

        filter_result = matcher.match_one({
            "aspen_block_type": "FILTER",
            "solids_feed_kg_h": 240.0,
            "filtration_flux_kg_m2_h": 60.0,
        }, self.rules, self.graph)
        self.assertAlmostEqual(filter_result["derived_parameters"]["filter_area_m2"], 4.0)

        dryer = matcher.match_one({
            "aspen_block_type": "DRYER",
            "water_component_mapping": "WATER->H2O",
            "inlet_water_kg_h": 125.0,
            "outlet_water_kg_h": 25.0,
            "heat_duty_kw": 80.0,
        }, self.rules, self.graph)
        self.assertAlmostEqual(dryer["derived_parameters"]["evaporation_rate_kg_h"], 100.0)
        self.assertAlmostEqual(dryer["derived_parameters"]["specific_drying_duty_kj_kg"], 2880.0)
        chains = {
            item["calculation_id"]: item["equation_chain"]
            for item in dryer["calculations"]
        }
        self.assertIn("dryer_water_evaporation", chains)
        self.assertIn("dryer_specific_duty", chains)

    def test_same_input_has_same_hash_and_result(self) -> None:
        record = {"设备类型": "工艺管道", "flow_m3_h": 50, "target_velocity_m_s": 1.5}
        left = matcher.match_one(record, self.rules, self.graph)
        right = matcher.match_one(record, self.rules, self.graph)
        self.assertEqual(left, right)

    def test_script_has_no_llm_or_network_dependency(self) -> None:
        source = Path(matcher.__file__).read_text(encoding="utf-8")
        for forbidden in ("import openai", "from openai", "import requests", "urllib.request", "httpx"):
            self.assertNotIn(forbidden, source)

    def test_example_batch_matches_all_records(self) -> None:
        payload = json.loads((matcher.PACKAGE_ROOT / "data" / "equipment_match_examples.json").read_text(encoding="utf-8"))
        results = [matcher.match_one(row, self.rules, self.graph) for row in payload["equipment"]]
        self.assertTrue(all(item["status"] == "MATCHED" for item in results), results)


if __name__ == "__main__":
    unittest.main(verbosity=2)
