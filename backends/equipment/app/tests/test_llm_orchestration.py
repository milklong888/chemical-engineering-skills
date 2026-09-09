from __future__ import annotations

import copy
import contextlib
import json
import shutil
import sys
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import app_core
import equipment_design_agent as agent
import llm_bridge
from equipment_design_app import EquipmentDesignApi


@contextlib.contextmanager
def writable_temp_directory():
    """Use the repository ACL instead of tempfile's restrictive Windows ACL."""
    root = APP_DIR / "tests" / f"_asset_bundle_test_{uuid.uuid4().hex}"
    root.mkdir(parents=False, exist_ok=False)
    try:
        yield str(root)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def pump_result() -> dict:
    return app_core.manual_match("block:PUMP", {
        "equipment_tag": "P-HYBRID",
        "phase": "liquid",
        "flow_m3_h": 20,
        "head_m": 45,
        "density_kg_m3": 900,
        "efficiency_percent": 75,
    })


def tower_default_result() -> dict:
    return app_core.manual_match("block:RADFRAC", {
        "equipment_tag": "T-HYBRID",
        "aspen_block_type": "RADFRAC",
        "process_function": "vacuum distillation; low pressure drop; clean non-fouling service",
    })


def empty_output(prepared: dict, injection_point: str = "audit") -> dict:
    output = {
        "schema": llm_bridge.STEP_OUTPUT_SCHEMA,
        "injection_point": injection_point,
        "context_sha256": prepared["context_pack"]["context_sha256"],
        "summary": "checked",
        "citations": [],
        "proposed_changes": [],
        "condition_assessments": [],
        "terminal_selection_assists": [],
        "calculation_assists": [],
        "retrieval_plan": [],
        "ambiguity_decision": None,
        "audit_findings": [],
        "output_composition": {"title": "AI assisted calculation", "blocks": []},
    }
    return organize_output(output)


def organize_output(output: dict) -> dict:
    blocks = []
    for section, operation in llm_bridge.OUTPUT_SECTION_OPERATIONS.items():
        value = output.get(section)
        nonempty = bool(str(value).strip()) if section == "summary" else value is not None and bool(value)
        if nonempty:
            blocks.append({
                "block_id": section,
                "operation": operation,
                "section_ref": section,
                "heading": section.replace("_", " ").title(),
                "citations": ["deterministic_result"],
            })
    output["output_composition"] = {"title": "AI assisted calculation", "blocks": blocks}
    return output


class LlmOrchestrationTests(unittest.TestCase):
    def test_verified_recipe_is_program_computed_and_interleaved_in_ai_order(self) -> None:
        prepared = llm_bridge.hybrid_prepare(
            pump_result(), {"status": "NOT_REQUESTED", "hits": []}, "audit"
        )
        output = empty_output(prepared)
        output["calculation_assists"] = [{
            "assist_id": "derive_mass_flow",
            "target_field": "mass_flow_kg_h",
            "target_unit": "kg/h",
            "method": "deterministic_recipe",
            "recipe_id": "mass_flow_from_volume_density",
            "proposed_value": None,
            "certainty": "certain",
            "uncertainty_note": None,
            "reason": "all recipe inputs are already present",
            "citations": ["deterministic_result"],
        }]
        organize_output(output)
        output["output_composition"]["blocks"].reverse()

        result = llm_bridge.hybrid_continue(prepared, output)

        self.assertEqual(result["verified_calculation_inputs"], {"mass_flow_kg_h": 18000.0})
        validation = result["calculation_assist_validation"][0]
        self.assertEqual(validation["status"], "VERIFIED_DETERMINISTIC_DERIVATION")
        self.assertTrue(validation["auto_apply"])
        steps = result["execution_timeline"]["steps"]
        self.assertEqual(
            [step["step_id"] for step in steps],
            [
                "program_deterministic_initial",
                "ai_calculation_assists",
                "ai_summary",
                "program_deterministic_recalculation",
            ],
        )
        self.assertTrue(steps[0]["immutable"])
        self.assertTrue(steps[-1]["immutable"])

    def test_recipe_inputs_are_identical_across_all_context_scopes(self) -> None:
        for scope in ("minimum", "routed", "full_family", "full_bundle"):
            with self.subTest(scope=scope):
                prepared = llm_bridge.hybrid_prepare(
                    pump_result(),
                    {"status": "NOT_REQUESTED", "hits": [], "assets": []},
                    "audit",
                    scope,
                )
                output = empty_output(prepared)
                output["calculation_assists"] = [{
                    "assist_id": "derive_mass_flow",
                    "target_field": "mass_flow_kg_h",
                    "target_unit": "kg/h",
                    "method": "deterministic_recipe",
                    "recipe_id": "mass_flow_from_volume_density",
                    "proposed_value": None,
                    "certainty": "certain",
                    "uncertainty_note": None,
                    "reason": "scope consistency regression",
                    "citations": ["deterministic_result"],
                }]
                organize_output(output)

                result = llm_bridge.hybrid_continue(prepared, output)

                self.assertEqual(
                    result["verified_calculation_inputs"],
                    {"mass_flow_kg_h": 18000.0},
                )

    def test_missing_presentation_block_is_completed_without_dropping_valid_assist(self) -> None:
        prepared = llm_bridge.hybrid_prepare(
            pump_result(), {"status": "NOT_REQUESTED", "hits": []}, "audit"
        )
        output = empty_output(prepared)
        output["calculation_assists"] = [{
            "assist_id": "derive_mass_flow",
            "target_field": "mass_flow_kg_h",
            "target_unit": "kg/h",
            "method": "deterministic_recipe",
            "recipe_id": "mass_flow_from_volume_density",
            "proposed_value": None,
            "certainty": "certain",
            "uncertainty_note": None,
            "reason": "program-verifiable relation",
            "citations": ["deterministic_result"],
        }]
        organize_output(output)
        output["output_composition"]["blocks"] = [
            block
            for block in output["output_composition"]["blocks"]
            if block["section_ref"] != "summary"
        ]

        result = llm_bridge.hybrid_continue(prepared, output)

        self.assertEqual(result["verified_calculation_inputs"], {"mass_flow_kg_h": 18000.0})
        refs = [block["section_ref"] for block in result["output_composition"]["blocks"]]
        self.assertEqual(refs, ["calculation_assists", "summary"])
        self.assertEqual(result["output_composition"]["blocks"][-1]["block_id"], "auto_summary")

    def test_recipe_ignores_model_arithmetic_and_uses_program_value(self) -> None:
        prepared = llm_bridge.hybrid_prepare(
            pump_result(), {"status": "NOT_REQUESTED", "hits": []}, "audit"
        )
        output = empty_output(prepared)
        output["calculation_assists"] = [{
            "assist_id": "derive_mass_flow",
            "target_field": "mass_flow_kg_h",
            "target_unit": "kg/h",
            "method": "deterministic_recipe",
            "recipe_id": "mass_flow_from_volume_density",
            "proposed_value": 999999.0,
            "certainty": "certain",
            "uncertainty_note": None,
            "reason": "select the registered recipe; model arithmetic is non-authoritative",
            "citations": ["deterministic_result"],
        }]
        organize_output(output)

        result = llm_bridge.hybrid_continue(prepared, output)

        self.assertEqual(result["verified_calculation_inputs"], {"mass_flow_kg_h": 18000.0})
        normalized = result["step_output"]["calculation_assists"][0]
        self.assertIsNone(normalized["proposed_value"])
        self.assertNotEqual(result["verified_calculation_inputs"]["mass_flow_kg_h"], 999999.0)

    def test_missing_composition_title_and_blocks_are_program_completed(self) -> None:
        prepared = llm_bridge.hybrid_prepare(
            pump_result(), {"status": "NOT_REQUESTED", "hits": []}, "audit"
        )
        output = empty_output(prepared)
        output["output_composition"] = {}

        result = llm_bridge.hybrid_continue(prepared, output)

        self.assertEqual(result["output_composition"]["title"], "AI assisted equipment reasoning")
        self.assertEqual(
            [item["section_ref"] for item in result["output_composition"]["blocks"]],
            ["summary"],
        )

    def test_bad_recipe_is_nonblocking_and_structured_model_estimate_is_preliminary_only(self) -> None:
        prepared = llm_bridge.hybrid_prepare(
            pump_result(), {"status": "NOT_REQUESTED", "hits": []}, "audit"
        )
        output = empty_output(prepared)
        output["calculation_assists"] = [
            {
                "assist_id": "unknown_recipe",
                "target_field": "mass_flow_kg_h",
                "target_unit": "kg/h",
                "method": "deterministic_recipe",
                "recipe_id": "invented_recipe",
                "proposed_value": None,
                "certainty": "certain",
                "uncertainty_note": None,
                "reason": "test a bad suggestion",
                "citations": ["deterministic_result"],
            },
            {
                "assist_id": "model_guess",
                "target_field": "npshr_m",
                "target_unit": "m",
                "method": "model_inference",
                "recipe_id": None,
                "proposed_value": 3.2,
                "certainty": "uncertain",
                "uncertainty_note": "No vendor curve is present; this is only a provisional screening value.",
                "inference_basis": "conservative_screening_assumption",
                "assumptions": ["single-stage end-suction centrifugal pump screening only"],
                "lower_bound": 2.0,
                "upper_bound": 5.0,
                "confidence": "low",
                "sensitivity_note": "Recheck NPSH margin over the full 2-5 m range and replace with vendor curve data.",
                "requested_preliminary_auto_apply": True,
                "reason": "keep the incomplete record moving without claiming vendor evidence",
                "citations": ["deterministic_result"],
            },
        ]
        organize_output(output)

        result = llm_bridge.hybrid_continue(prepared, output)

        self.assertEqual(result["verified_calculation_inputs"], {})
        statuses = [item["status"] for item in result["calculation_assist_validation"]]
        self.assertEqual(
            statuses,
            ["REJECTED_NONBLOCKING", "VERIFIED_PROVISIONAL_ENGINEERING_ESTIMATE"],
        )
        self.assertEqual(result["verified_model_estimate_inputs"], {"npshr_m": 3.2})
        self.assertTrue(result["apply_contract"]["model_inference_auto_apply_allowed"])
        self.assertEqual(result["apply_contract"]["model_inference_promotion_cap"], "TYPE_SCREENING")

    def test_recipe_catalog_respects_exchanger_correction_factor_and_existing_derived_value(self) -> None:
        recipes = {item["recipe_id"]: item for item in llm_bridge.calculation_recipe_catalog()}
        area_recipe = recipes["heat_transfer_area_from_duty_u_lmtd"]
        self.assertIn("lmtd_correction_factor", area_recipe["inputs"])
        self.assertEqual(
            recipes["pressure_head_component_from_drop_density"]["target_field"],
            "pressure_drop_head_component_m",
        )
        self.assertEqual(
            recipes["pressure_head_component_from_drop_density"]["applicable_family_ids"],
            ["family_liquid_power_recovery_turbine"],
        )
        self.assertNotIn("pressure_drop_from_pressures", recipes)
        self.assertNotIn("heat_duty_from_u_area_lmtd", recipes)

        exchanger = app_core.manual_match("family:family_fixed_tubesheet_exchanger", {
            "equipment_tag": "E-RECIPE",
            "heat_duty_kw": 500,
            "overall_u_w_m2k": 600,
            "lmtd_k": 30,
            "lmtd_correction_factor": 0.9,
        })
        prepared = llm_bridge.hybrid_prepare(
            exchanger, {"status": "NOT_REQUESTED", "hits": []}, "audit"
        )
        output = empty_output(prepared)
        output["calculation_assists"] = [{
            "assist_id": "area_already_calculated",
            "target_field": "heat_transfer_area_m2",
            "target_unit": "m2",
            "method": "deterministic_recipe",
            "recipe_id": "heat_transfer_area_from_duty_u_lmtd",
            "proposed_value": None,
            "certainty": "certain",
            "uncertainty_note": None,
            "reason": "check whether the program has already derived this target",
            "citations": ["deterministic_result"],
        }]
        organize_output(output)

        result = llm_bridge.hybrid_continue(prepared, output)

        self.assertEqual(result["verified_calculation_inputs"], {})
        self.assertEqual(
            result["calculation_assist_validation"][0]["status"],
            "ALREADY_AVAILABLE_CONSISTENT",
        )

    def test_aspen_aggregate_context_includes_equipment_piping_and_calculations(self) -> None:
        pump = pump_result()
        piping = app_core.manual_match("family:family_process_piping", {
            "equipment_tag": "S-HYBRID",
            "equipment_family": "family_process_piping",
            "flow_m3_h": 20,
            "target_velocity_m_s": 2,
            "operating_pressure_mpa": 0.6,
            "pressure_basis": "gauge",
        })
        aggregate = {
            "schema": "aspen-equipment-derivation-result-v1",
            "status": "DERIVED",
            "equipment_count": 1,
            "piping_count": 1,
            "formal_use_gate": "ELIGIBLE_AS_PROCESS_BASIS",
            "formal_use_blockers": [],
            "normalization_diagnostic_count": 0,
            "normalization_diagnostics": [],
            "source_export_sha256": "A" * 64,
            "pfd_mapping_sha256": "B" * 64,
            "equipment": [{
                "aspen_block_id": "P-HYBRID",
                "equipment_tag": "P-HYBRID",
                "aspen_mapping_status": "DERIVED",
                "canonical_match_input": {
                    "aspen_block_type": "PUMP",
                    "flow_m3_h": 20,
                    "head_m": 45,
                },
                "adapter_blockers": [],
                "evidence_boundary": {"status": "PROCESS_DATA_ONLY"},
                "match_result": pump,
            }],
            "piping": [{
                "stream_id": "S-HYBRID",
                "status": "MATCHED",
                "canonical_match_input": {
                    "equipment_family": "family_process_piping",
                    "flow_m3_h": 20,
                },
                "evidence_boundary": {"status": "PROCESS_DATA_ONLY"},
                "match_result": piping,
            }],
        }

        compact = llm_bridge._minimal_deterministic_context(aggregate)
        self.assertEqual(len(compact["equipment"]), 1)
        self.assertEqual(len(compact["piping"]), 1)
        self.assertTrue(
            compact["equipment"][0]["match_summary"]["calculations"]
        )
        registry = llm_bridge.candidate_registry(aggregate)
        self.assertTrue(
            any(
                item["candidate_id"].startswith("family_process_piping:")
                for item in registry
            )
        )
        self.assertTrue(
            any(
                item["candidate_id"].startswith("gbt5662:")
                or item["candidate_id"].startswith("family_pump:")
                for item in registry
            )
        )
        prepared = llm_bridge.build_context_pack(
            aggregate,
            {
                "status": "NOT_REQUESTED",
                "coverage_status": "PARTIAL",
                "hits": [],
                "assets": [],
            },
            "audit",
            "minimum",
        )
        self.assertEqual(len(prepared["sources"][0]["content"]["piping"]), 1)
        self.assertGreaterEqual(len(prepared["candidate_registry"]), 2)

        full_family = EquipmentDesignApi().hybrid_prepare(
            aggregate,
            {"enabled": False},
            "audit",
            "full_family",
        )
        self.assertFalse(full_family["ok"])
        self.assertIn("恰好一个 family_id", full_family["error"])

    def test_zero_heat_duty_area_recipe_is_rejected_without_blocking(self) -> None:
        deterministic = {
            "status": "PARTIAL",
            "match": {"family_id": "family_fixed_tubesheet_exchanger"},
            "normalized_input": {
                "heat_duty_kw": 0.0,
                "overall_u_w_m2k": 600.0,
                "lmtd_correction_factor": 0.9,
                "lmtd_k": 30.0,
            },
            "derived_parameters": {},
        }
        prepared = llm_bridge.hybrid_prepare(
            deterministic, {"status": "NOT_REQUESTED", "hits": []}, "audit"
        )
        output = empty_output(prepared)
        output["calculation_assists"] = [{
            "assist_id": "zero_duty_area",
            "target_field": "heat_transfer_area_m2",
            "target_unit": "m2",
            "method": "deterministic_recipe",
            "recipe_id": "heat_transfer_area_from_duty_u_lmtd",
            "proposed_value": None,
            "certainty": "certain",
            "uncertainty_note": None,
            "reason": "zero-duty hard-gate regression",
            "citations": ["deterministic_result"],
        }]
        organize_output(output)

        result = llm_bridge.hybrid_continue(prepared, output)

        validation = result["calculation_assist_validation"][0]
        self.assertEqual(validation["status"], "REJECTED_NONBLOCKING")
        self.assertIn("heat_duty_kw=0", validation["detail"])
        self.assertEqual(result["verified_calculation_inputs"], {})
        calc_step = next(
            step for step in result["execution_timeline"]["steps"]
            if step.get("payload_ref") == "step_output.calculation_assists"
        )
        self.assertEqual(calc_step["status"], "COMPLETED_WITH_ITEM_DIAGNOSTICS")

    def test_exchanger_recipe_is_rejected_for_radfrac_even_with_stray_heat_fields(self) -> None:
        tower = app_core.manual_match("block:RADFRAC", {
            "equipment_tag": "T-WRONG-SCOPE",
            "heat_duty_kw": 100.0,
            "overall_u_w_m2k": 500.0,
            "lmtd_correction_factor": 1.0,
            "lmtd_k": 20.0,
        })
        prepared = llm_bridge.hybrid_prepare(
            tower, {"status": "NOT_REQUESTED", "hits": []}, "audit"
        )
        output = empty_output(prepared)
        output["calculation_assists"] = [{
            "assist_id": "wrong_scope_area",
            "target_field": "heat_transfer_area_m2",
            "target_unit": "m2",
            "method": "deterministic_recipe",
            "recipe_id": "heat_transfer_area_from_duty_u_lmtd",
            "proposed_value": None,
            "certainty": "certain",
            "uncertainty_note": None,
            "reason": "cross-family stray-field regression",
            "citations": ["deterministic_result"],
        }]
        organize_output(output)

        result = llm_bridge.hybrid_continue(prepared, output)

        validation = result["calculation_assist_validation"][0]
        self.assertEqual(validation["status"], "REJECTED_NONBLOCKING_WRONG_SCOPE")
        self.assertIn("family_tower", validation["detail"])
        self.assertEqual(result["verified_calculation_inputs"], {})

    def test_hybrid_run_auto_recalculates_after_verified_missing_input(self) -> None:
        values = {
            "equipment_tag": "P-AUTO-DERIVE",
            "phase": "liquid",
            "flow_m3_h": 20,
            "head_m": 45,
            "density_kg_m3": 900,
            "efficiency_percent": 75,
        }
        source_input = {
            "operation": "manual_match",
            "payload": {"selection_id": "block:PUMP", "values": values},
        }
        prepare_response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "hybrid_prepare",
            "payload": {
                "input": source_input,
                "knowledge": {"enabled": False},
                "injection_point": "audit",
                "context_scope": "minimum",
            },
        })
        self.assertEqual(code, 0, prepare_response)
        prepared = prepare_response["result"]
        output = empty_output(prepared)
        output["calculation_assists"] = [{
            "assist_id": "derive_mass_flow",
            "target_field": "mass_flow_kg_h",
            "target_unit": "kg/h",
            "method": "deterministic_recipe",
            "recipe_id": "mass_flow_from_volume_density",
            "proposed_value": None,
            "certainty": "certain",
            "uncertainty_note": None,
            "reason": "program-verifiable relation",
            "citations": ["deterministic_result"],
        }]
        organize_output(output)

        response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "hybrid_run",
            "payload": {
                "input": source_input,
                "knowledge": {"enabled": False},
                "injection_point": "audit",
                "context_scope": "minimum",
                "llm": {"enabled": True, "config": {"provider": "mock", "mock_response": output}},
            },
        })

        self.assertEqual(code, 0, response)
        result = response["result"]
        self.assertEqual(result["machine_state"]["state"], "COMPLETED_HYBRID_SELECTION_COMPLETE")
        self.assertEqual(
            result["calculation_assist_application"]["applied_inputs"],
            {"mass_flow_kg_h": 18000.0},
        )
        self.assertIsNotNone(result["deterministic_recalculation"])
        recalculated_input = result["deterministic_recalculation"]["result"]["normalized_input"]
        self.assertEqual(recalculated_input["mass_flow_kg_h"], 18000.0)
        self.assertNotIn("mass_flow_kg_h", result["deterministic_result"]["input"])
        self.assertEqual(
            result["execution_timeline"]["steps"][-1]["status"],
            "COMPLETED_AUTHORITATIVE",
        )

    def test_model_estimates_fill_missing_sizing_fields_and_remain_visible_provisional(self) -> None:
        source_input = {
            "operation": "manual_match",
            "payload": {
                "selection_id": "block:PUMP",
                "values": {"equipment_tag": "P-ESTIMATE", "flow_m3_h": 20},
            },
        }
        prepare_response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "hybrid_prepare",
            "payload": {
                "input": source_input,
                "knowledge": {"enabled": False},
                "injection_point": "audit",
                "context_scope": "minimum",
            },
        })
        self.assertEqual(code, 0, prepare_response)
        prepared = prepare_response["result"]
        registry = {
            item["field_id"]: item
            for item in prepared["context_pack"]["missing_input_registry"]
        }
        self.assertNotIn("head_m", registry)
        self.assertNotIn("density_kg_m3", registry)
        self.assertIn("operating_pressure_mpa", registry)
        output = empty_output(prepared)
        output["calculation_assists"] = [
            {
                "assist_id": "estimate_operating_pressure",
                "target_field": "operating_pressure_mpa",
                "target_unit": registry["operating_pressure_mpa"]["target_unit"],
                "method": "model_inference",
                "recipe_id": None,
                "proposed_value": 0.3,
                "certainty": "uncertain",
                "uncertainty_note": "No operating pressure was supplied; this is a bounded preliminary screening estimate.",
                "inference_basis": "conservative_screening_assumption",
                "assumptions": ["low-pressure liquid service", "pressure remains within the declared range"],
                "lower_bound": 0.1,
                "upper_bound": 0.6,
                "confidence": "low",
                "sensitivity_note": "Design pressure must be replayed at both pressure bounds.",
                "requested_preliminary_auto_apply": True,
                "reason": "close the preliminary design-pressure calculation without claiming an Aspen property",
                "citations": ["deterministic_result"],
            },
        ]
        organize_output(output)
        response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "hybrid_run",
            "payload": {
                "input": source_input,
                "knowledge": {"enabled": False},
                "injection_point": "audit",
                "context_scope": "minimum",
                "llm": {"enabled": True, "config": {"provider": "mock", "mock_response": output}},
            },
        })
        self.assertEqual(code, 0, response)
        result = response["result"]
        self.assertEqual(
            result["machine_state"]["state"],
            "COMPLETED_HYBRID_SELECTION_COMPLETE_PROVISIONAL",
        )
        self.assertEqual(result["selection_completeness"]["acceptance"], "PASS")
        self.assertEqual(
            result["calculation_assist_application"]["applied_model_estimate_inputs"],
            {"operating_pressure_mpa": 0.3},
        )
        recalculated = result["deterministic_recalculation"]["result"]
        self.assertEqual(
            sorted(item["field_id"] for item in recalculated["model_estimate_inputs"]),
            ["operating_pressure_mpa"],
        )
        rows = {
            row["field_id"]: row
            for group in recalculated["design_parameter_package"]["groups"]
            for row in group["rows"]
        }
        self.assertEqual(rows["operating_pressure_mpa"]["state"], "ESTIMATED")
        self.assertEqual(rows["operating_pressure_mpa"]["source"]["evidence_class"], "J")
        self.assertEqual(rows["operating_pressure_mpa"]["source"]["promotion_cap"], "TYPE_SCREENING")
        self.assertEqual(rows["density_kg_m3"]["state"], "DEFAULTED")
        self.assertEqual(rows["head_m"]["state"], "DEFAULTED")

    def test_direct_component_choice_fields_are_excluded_and_registry_summary_is_visible(self) -> None:
        source_input = {
            "operation": "manual_match",
            "payload": {
                "selection_id": "family:family_flange_gasket",
                "values": {"equipment_tag": "FG-ESTIMATE"},
            },
        }
        prepare_response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "hybrid_prepare",
            "payload": {
                "input": source_input,
                "knowledge": {"enabled": False},
                "injection_point": "audit",
                "context_scope": "minimum",
            },
        })
        self.assertEqual(code, 0, prepare_response)
        prepared = prepare_response["result"]
        registry = {
            item["field_id"]: item
            for item in prepared["context_pack"]["missing_input_registry"]
        }
        for field_id in (
            "wall_series", "fitting_type", "connection_type", "pressure_class",
            "flange_face", "gasket_material", "valve_function",
        ):
            self.assertNotIn(field_id, registry)
        deterministic_context = next(
            item["content"] for item in prepared["context_pack"]["sources"]
            if item["context_id"] == "deterministic_result"
        )
        connection_summary = deterministic_context["connection_component_selection_summary"]
        self.assertTrue(connection_summary["selection_package_sha256"])
        selected_components = connection_summary["connections"][0]["component_types"]
        self.assertEqual(selected_components["facing"]["terminal_type"]["candidate_id"], "FACE_RF")
        self.assertEqual(selected_components["gasket_type"]["terminal_type"]["candidate_id"], "G_SPIRAL_D")

        output = empty_output(prepared)
        output["calculation_assists"] = [{
            "assist_id": "invented_gasket",
            "target_field": "gasket_material",
            "target_unit": "dimensionless",
            "method": "model_inference",
            "recipe_id": None,
            "proposed_value": "invented foam gasket",
            "certainty": "uncertain",
            "uncertainty_note": "must not bypass the deterministic HG/T selector",
            "inference_basis": "engineering_requirement",
            "assumptions": ["regression only"],
            "lower_bound": None,
            "upper_bound": None,
            "confidence": "low",
            "sensitivity_note": "must remain rejected",
            "requested_preliminary_auto_apply": True,
            "reason": "negative registry test",
            "citations": ["deterministic_result"],
        }]
        organize_output(output)
        result = llm_bridge.hybrid_continue(prepared, output)
        validation = result["calculation_assist_validation"][0]
        self.assertEqual(
            validation["status"],
            "REJECTED_MODEL_ESTIMATE_TARGET_NOT_REGISTERED_MISSING_INPUT",
        )
        self.assertFalse(validation["auto_apply"])

    def test_unregistered_free_text_metric_is_rejected_nonblocking(self) -> None:
        deterministic = {
            "status": "PARTIAL",
            "match": {"family_id": "family_static_mixer"},
            "normalized_input": {},
            "derived_parameters": {},
            "design_parameter_package": {
                "selection_feature_vector": {"missing_fields": ["mixing_metric"]},
                "groups": [{
                    "group_id": "selection",
                    "rows": [{
                        "field_id": "mixing_metric",
                        "label": "混合指标",
                        "raw_value": None,
                        "unit": None,
                        "state": "MISSING",
                    }],
                }],
            },
            "calculation_pending": [],
            "progress": {"minimum_missing_sets": [], "next_fields": []},
        }
        prepared = llm_bridge.hybrid_prepare(
            deterministic, {"status": "NOT_REQUESTED", "hits": []}, "audit"
        )
        output = empty_output(prepared)
        output["calculation_assists"] = [{
            "assist_id": "unsafe_mixing_metric",
            "target_field": "mixing_metric",
            "target_unit": "dimensionless",
            "method": "model_inference",
            "recipe_id": None,
            "proposed_value": "C:/invented/vendor/file.pdf",
            "certainty": "uncertain",
            "uncertainty_note": "unsafe text guard regression",
            "inference_basis": "conservative_screening_assumption",
            "assumptions": ["regression only"],
            "lower_bound": None,
            "upper_bound": None,
            "confidence": "low",
            "sensitivity_note": "must remain rejected",
            "requested_preliminary_auto_apply": True,
            "reason": "guard regression",
            "citations": ["deterministic_result"],
        }]
        organize_output(output)
        result = llm_bridge.hybrid_continue(prepared, output)
        validation = result["calculation_assist_validation"][0]
        self.assertEqual(
            validation["status"],
            "REJECTED_MODEL_ESTIMATE_TARGET_NOT_REGISTERED_MISSING_INPUT",
        )
        self.assertFalse(validation["auto_apply"])

    def test_recipe_dependency_chain_is_resolved_independent_of_model_order(self) -> None:
        deterministic = {
            "status": "PARTIAL",
            "match": {"family_id": "family_pump"},
            "normalized_input": {
                "flow_m3_h": 20.0,
                "density_kg_m3": 900.0,
                "head_m": 45.0,
                "efficiency_percent": 75.0,
            },
            "derived_parameters": {},
            "design_parameter_package": {
                "selection_feature_vector": {"missing_fields": []},
                "groups": [],
            },
            "calculation_pending": [],
            "progress": {"minimum_missing_sets": [], "next_fields": []},
        }
        prepared = llm_bridge.hybrid_prepare(
            deterministic, {"status": "NOT_REQUESTED", "hits": []}, "audit"
        )
        output = empty_output(prepared)
        output["calculation_assists"] = [
            {
                "assist_id": "shaft_last",
                "target_field": "shaft_power_kw",
                "target_unit": "kW",
                "method": "deterministic_recipe",
                "recipe_id": "pump_shaft_power_from_hydraulic_power",
                "proposed_value": None,
                "certainty": "certain",
                "uncertainty_note": None,
                "reason": "dependent recipe intentionally listed first",
                "citations": ["deterministic_result"],
            },
            {
                "assist_id": "hydraulic_middle",
                "target_field": "hydraulic_power_kw",
                "target_unit": "kW",
                "method": "deterministic_recipe",
                "recipe_id": "pump_hydraulic_power_from_mass_head",
                "proposed_value": None,
                "certainty": "certain",
                "uncertainty_note": None,
                "reason": "second dependency",
                "citations": ["deterministic_result"],
            },
            {
                "assist_id": "mass_first",
                "target_field": "mass_flow_kg_h",
                "target_unit": "kg/h",
                "method": "deterministic_recipe",
                "recipe_id": "mass_flow_from_volume_density",
                "proposed_value": None,
                "certainty": "certain",
                "uncertainty_note": None,
                "reason": "root dependency intentionally listed last",
                "citations": ["deterministic_result"],
            },
        ]
        organize_output(output)
        result = llm_bridge.hybrid_continue(prepared, output)
        self.assertEqual(result["verified_calculation_inputs"]["mass_flow_kg_h"], 18000.0)
        self.assertAlmostEqual(result["verified_calculation_inputs"]["hydraulic_power_kw"], 2.20649625)
        self.assertAlmostEqual(result["verified_calculation_inputs"]["shaft_power_kw"], 2.941995)
        self.assertTrue(all(
            item["status"] == "VERIFIED_DETERMINISTIC_DERIVATION"
            for item in result["calculation_assist_validation"]
        ))

    def test_deterministic_recipe_wins_conflict_with_model_estimate(self) -> None:
        deterministic = {
            "status": "PARTIAL",
            "match": {"family_id": "family_pump"},
            "normalized_input": {"flow_m3_h": 20.0, "density_kg_m3": 900.0},
            "derived_parameters": {},
            "design_parameter_package": {
                "selection_feature_vector": {"missing_fields": ["mass_flow_kg_h"]},
                "groups": [{
                    "group_id": "process",
                    "rows": [{
                        "field_id": "mass_flow_kg_h",
                        "label": "质量流量",
                        "raw_value": None,
                        "unit": "kg/h",
                        "state": "MISSING",
                        "required_for": ["candidate_matching"],
                    }],
                }],
            },
            "calculation_pending": [],
            "progress": {
                "minimum_missing_sets": [{"goal": "candidate_matching", "fields": ["mass_flow_kg_h"]}],
                "next_fields": [{"field": "mass_flow_kg_h", "reason": "candidate_matching"}],
            },
        }
        prepared = llm_bridge.hybrid_prepare(
            deterministic, {"status": "NOT_REQUESTED", "hits": []}, "audit"
        )
        output = empty_output(prepared)
        output["calculation_assists"] = [
            {
                "assist_id": "wrong_model_mass",
                "target_field": "mass_flow_kg_h",
                "target_unit": "kg/h",
                "method": "model_inference",
                "recipe_id": None,
                "proposed_value": 99999.0,
                "certainty": "uncertain",
                "uncertainty_note": "Deliberately conflicting regression value.",
                "inference_basis": "unit_conversion",
                "assumptions": ["incorrect model arithmetic used only to test script priority"],
                "lower_bound": 90000.0,
                "upper_bound": 110000.0,
                "confidence": "low",
                "sensitivity_note": "The program-computed mass balance must replace this value.",
                "requested_preliminary_auto_apply": True,
                "reason": "conflict regression",
                "citations": ["deterministic_result"],
            },
            {
                "assist_id": "script_mass",
                "target_field": "mass_flow_kg_h",
                "target_unit": "kg/h",
                "method": "deterministic_recipe",
                "recipe_id": "mass_flow_from_volume_density",
                "proposed_value": None,
                "certainty": "certain",
                "uncertainty_note": None,
                "reason": "program relation owns the result",
                "citations": ["deterministic_result"],
            },
        ]
        organize_output(output)
        result = llm_bridge.hybrid_continue(prepared, output)
        self.assertEqual(result["verified_calculation_inputs"], {"mass_flow_kg_h": 18000.0})
        self.assertEqual(result["verified_model_estimate_inputs"], {})
        records = {item["assist_id"]: item for item in result["calculation_assist_validation"]}
        self.assertEqual(records["script_mass"]["status"], "VERIFIED_DETERMINISTIC_DERIVATION")
        self.assertEqual(records["wrong_model_mass"]["status"], "REJECTED_EXISTING_VALUE_CONFLICT")

    def test_step_schema_path_uses_packaged_app_schema_directory(self) -> None:
        with writable_temp_directory() as frozen_root, patch.object(
            sys, "_MEIPASS", frozen_root, create=True
        ):
            self.assertEqual(
                llm_bridge._default_step_schema_path(),
                Path(frozen_root).resolve()
                / "app"
                / "schemas"
                / "equipment_design_llm_step_output.schema.json",
            )

    def test_prepare_hashes_context_and_separates_feature_and_context_hashes(self) -> None:
        prepared = llm_bridge.hybrid_prepare(
            pump_result(),
            {"status": "PASS_BUNDLED_GRAPH", "hits": [{"path": "kg/pump.md", "text": "pump gate"}]},
            "audit",
            "routed",
        )
        pack = prepared["context_pack"]
        self.assertEqual(pack["coverage_status"], "ROUTED_HITS")
        self.assertGreater(pack["char_count"], 0)
        self.assertTrue(pack["included_assets"][0]["sha256"])
        self.assertTrue(pack["condition_registry"])
        candidate = pack["candidate_registry"][0]
        self.assertEqual(len(candidate["selection_feature_vector_sha256"]), 64)
        self.assertEqual(len(candidate["selection_context_sha256"]), 64)
        self.assertNotEqual(
            candidate["selection_feature_vector_sha256"],
            candidate["selection_context_sha256"],
        )

    def test_mock_run_is_offline_and_reuses_continue_validator(self) -> None:
        prepared = llm_bridge.hybrid_prepare(pump_result(), {"status": "NOT_REQUESTED", "hits": []}, "audit")
        output = empty_output(prepared)
        output["audit_findings"] = [{
            "finding_id": "audit-1",
            "severity": "warning",
            "message": "vendor evidence remains open",
            "citations": ["deterministic_result"],
        }]
        organize_output(output)
        with patch.object(llm_bridge.urllib.request, "urlopen", side_effect=AssertionError("network forbidden")):
            result = llm_bridge.hybrid_run(
                {"provider": "mock", "model": "offline", "mock_response": output},
                prepared,
            )
        self.assertEqual(result["schema"], llm_bridge.ORCHESTRATION_SCHEMA)
        self.assertEqual(result["provider"], "mock")
        self.assertEqual(result["step_output"]["audit_findings"][0]["finding_id"], "audit-1")

    def test_openai_provider_receives_safe_schema_and_local_contract_stays_complete(self) -> None:
        prepared = llm_bridge.hybrid_prepare(
            pump_result(),
            {"status": "NOT_REQUESTED", "hits": []},
            "audit",
        )
        output = empty_output(prepared)
        response_body = {
            "choices": [{"message": {"content": json.dumps(output)}}],
        }
        captured: dict[str, object] = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            @staticmethod
            def read() -> bytes:
                return json.dumps(response_body).encode("utf-8")

        def fake_urlopen(request, timeout):
            captured["timeout"] = timeout
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse()

        with patch.object(llm_bridge.urllib.request, "urlopen", side_effect=fake_urlopen):
            result = llm_bridge.hybrid_run({
                "provider": "openai",
                "base_url": "https://api.openai.com/v1",
                "model": "review-model",
                "timeout_s": 17,
                "api_key": "TEST-KEY",
            }, prepared)

        provider_schema = captured["payload"]["response_format"]["json_schema"]["schema"]
        full_schema = prepared["output_contract"]["json_schema"]
        self.assertEqual(provider_schema, prepared["output_contract"]["provider_json_schema"])
        self.assertNotEqual(provider_schema, full_schema)
        self.assertIn("allOf", full_schema["properties"]["proposed_changes"]["items"])
        self.assertIn("oneOf", full_schema["properties"]["ambiguity_decision"])

        unsupported: list[str] = []

        def find_unsupported(value) -> None:
            if isinstance(value, list):
                for item in value:
                    find_unsupported(item)
                return
            if not isinstance(value, dict):
                return
            unsupported.extend(
                key for key in value
                if key in {"allOf", "if", "then", "else", "oneOf", "const", "$schema", "$id"}
            )
            for item in value.values():
                find_unsupported(item)

        find_unsupported(provider_schema)
        self.assertEqual(unsupported, [])
        self.assertFalse(provider_schema["additionalProperties"])
        self.assertEqual(provider_schema["properties"]["injection_point"], {"enum": ["audit"]})
        self.assertEqual(
            provider_schema["properties"]["context_sha256"],
            {"enum": [prepared["context_pack"]["context_sha256"]]},
        )
        nested_citations = (
            provider_schema["properties"]["audit_findings"]["items"]
            ["properties"]["citations"]
        )
        self.assertEqual(nested_citations["minItems"], 1)
        self.assertEqual(captured["timeout"], 17)
        self.assertEqual(result["provider"], "openai")
        user_payload = json.loads(captured["payload"]["messages"][1]["content"])
        active_policy = user_payload["active_output_policy"]
        self.assertEqual(active_policy["injection_point"], "audit")
        self.assertEqual(
            active_policy["allowed_sections"],
            ["audit_findings", "calculation_assists"],
        )
        self.assertIn("condition_assessments", active_policy["sections_that_must_be_empty"])
        self.assertEqual(active_policy["empty_value_by_section"]["condition_assessments"], [])

    def test_responses_provider_runs_strict_hybrid_contract_without_storage(self) -> None:
        prepared = llm_bridge.hybrid_prepare(
            pump_result(),
            {"status": "NOT_REQUESTED", "hits": []},
            "audit",
        )
        output = empty_output(prepared)
        response_body = {
            "output": [{
                "type": "message",
                "content": [{
                    "type": "output_text",
                    "text": json.dumps(output, ensure_ascii=False),
                }],
            }],
        }
        captured: dict[str, object] = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            @staticmethod
            def read() -> bytes:
                return json.dumps(response_body, ensure_ascii=False).encode("utf-8")

        def fake_urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse()

        with patch.object(llm_bridge.urllib.request, "urlopen", side_effect=fake_urlopen):
            result = llm_bridge.hybrid_run({
                "provider": "openai_compatible",
                "base_url": "https://example.invalid/v1/chat/completions",
                "model": "reasoning-model",
                "wire_api": "responses",
                "reasoning_effort": "xhigh",
                "disable_response_storage": True,
                "timeout_s": 31,
                "api_key": "TEST-KEY",
            }, prepared)

        payload = captured["payload"]
        self.assertEqual(captured["url"], "https://example.invalid/v1/responses")
        self.assertEqual(captured["timeout"], 31)
        self.assertIn("instructions", payload)
        user_payload = json.loads(payload["input"])
        self.assertEqual(user_payload["active_output_policy"]["injection_point"], "audit")
        self.assertEqual(payload["reasoning"], {"effort": "xhigh"})
        self.assertFalse(payload["store"])
        self.assertNotIn("messages", payload)
        self.assertNotIn("temperature", payload)
        self.assertEqual(result["provider"], "openai_compatible")
        self.assertEqual(result["wire_api"], "responses")
        self.assertEqual(result["reasoning_effort"], "xhigh")
        self.assertTrue(result["response_storage_disabled"])

    def test_nested_claim_requires_nonempty_citation(self) -> None:
        prepared = llm_bridge.hybrid_prepare(pump_result(), {"status": "NOT_REQUESTED", "hits": []}, "audit")
        output = empty_output(prepared)
        output["audit_findings"] = [{
            "finding_id": "audit-1", "severity": "warning", "message": "open", "citations": []
        }]
        with self.assertRaisesRegex(ValueError, "至少需要一个"):
            llm_bridge.hybrid_continue(prepared, output)

    def test_condition_id_must_come_from_deterministic_registry(self) -> None:
        prepared = llm_bridge.hybrid_prepare(
            pump_result(), {"status": "NOT_REQUESTED", "hits": []}, "textual_condition_judgment"
        )
        output = empty_output(prepared, "textual_condition_judgment")
        output["condition_assessments"] = [{
            "condition_id": "llm-invented-condition",
            "status": "unknown",
            "reason": "not in deterministic checks",
            "citations": ["deterministic_result"],
        }]
        with self.assertRaisesRegex(ValueError, "未知 condition_id"):
            llm_bridge.hybrid_continue(prepared, output)

        empty_prepared = llm_bridge.hybrid_prepare(
            {"status": "MATCHED"}, {"status": "NOT_REQUESTED", "hits": []}, "textual_condition_judgment"
        )
        empty_condition_output = empty_output(empty_prepared, "textual_condition_judgment")
        empty_condition_output["condition_assessments"] = [{
            "condition_id": "anything", "status": "unknown", "reason": "unknown",
            "citations": ["deterministic_result"],
        }]
        with self.assertRaisesRegex(ValueError, "condition_registry"):
            llm_bridge.hybrid_continue(empty_prepared, empty_condition_output)

    def test_registered_terminal_condition_selection_upgrades_default_without_free_type_text(self) -> None:
        prepared = llm_bridge.hybrid_prepare(
            tower_default_result(),
            {"status": "NOT_REQUESTED", "hits": []},
            "textual_condition_judgment",
        )
        terminal_rules = {
            item["rule_id"]: item
            for item in prepared["context_pack"]["terminal_type_rule_registry"]
        }
        rule_id = "tower:semantic:vacuum_low_pressure_drop_structured_packing"
        condition_id = "tower_condition:vacuum_low_pressure_drop_clean_service"
        self.assertEqual(terminal_rules[rule_id]["condition_id"], condition_id)

        output = empty_output(prepared, "textual_condition_judgment")
        output["condition_assessments"] = [{
            "condition_id": condition_id,
            "status": "supported",
            "reason": "The deterministic service text states vacuum, low pressure drop and clean service.",
            "citations": ["deterministic_result"],
        }]
        output["terminal_selection_assists"] = [{
            "assist_id": "choose_registered_tower_form",
            "terminal_rule_id": rule_id,
            "condition_id": condition_id,
            "selection_context_sha256": terminal_rules[rule_id]["selection_context_sha256"],
            "reason": "Use the registered structured-packing rule; do not invent a free-text type.",
            "citations": ["deterministic_result"],
        }]
        organize_output(output)

        result = llm_bridge.hybrid_continue(prepared, output)

        self.assertEqual(
            result["verified_terminal_selection_override_id"],
            rule_id,
        )
        validation = result["terminal_selection_assist_validation"][0]
        self.assertEqual(validation["status"], "VERIFIED_REGISTERED_CONDITION_SELECTION")
        self.assertTrue(validation["auto_apply"])

    def test_agent_hybrid_run_replays_registered_terminal_condition_selection_and_preserves_initial_default(self) -> None:
        source_input = {
            "operation": "manual_match",
            "payload": {
                "selection_id": "block:RADFRAC",
                "values": {
                    "equipment_tag": "T-HYBRID-REPLAY",
                    "aspen_block_type": "RADFRAC",
                    "process_function": "vacuum distillation; low pressure drop; clean non-fouling service",
                },
            },
        }
        prepare_response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "hybrid_prepare",
            "payload": {
                "input": source_input,
                "knowledge": {"enabled": False},
                "injection_point": "textual_condition_judgment",
                "context_scope": "minimum",
            },
        })
        self.assertEqual(code, 0, prepare_response)
        prepared = prepare_response["result"]
        rule_id = "tower:semantic:vacuum_low_pressure_drop_structured_packing"
        terminal_rule = next(
            item for item in prepared["context_pack"]["terminal_type_rule_registry"]
            if item["rule_id"] == rule_id
        )
        output = empty_output(prepared, "textual_condition_judgment")
        output["condition_assessments"] = [{
            "condition_id": terminal_rule["condition_id"],
            "status": "supported",
            "reason": "The deterministic service text explicitly supports this registered condition.",
            "citations": ["deterministic_result"],
        }]
        output["terminal_selection_assists"] = [{
            "assist_id": "select_registered_terminal_form",
            "terminal_rule_id": rule_id,
            "condition_id": terminal_rule["condition_id"],
            "selection_context_sha256": terminal_rule["selection_context_sha256"],
            "reason": "Select only the registered rule and let the program replay it.",
            "citations": ["deterministic_result"],
        }]
        organize_output(output)

        response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "hybrid_run",
            "payload": {
                "input": source_input,
                "knowledge": {"enabled": False},
                "injection_point": "textual_condition_judgment",
                "context_scope": "minimum",
                "llm": {
                    "enabled": True,
                    "config": {"provider": "mock", "mock_response": output},
                },
            },
        })

        self.assertEqual(code, 0, response)
        result = response["result"]
        initial = result["deterministic_result"]["result"]["model_recommendation"]
        recalculated = result["deterministic_recalculation"]["result"]["model_recommendation"]
        self.assertEqual(initial["recommended_type"], "单溢流筛板塔")
        self.assertEqual(initial["terminal_selection"]["status"], "DEFAULTED_TERMINAL_TYPE_SELECTED")
        self.assertEqual(recalculated["recommended_type"], "规整填料塔")
        self.assertEqual(recalculated["terminal_selection"]["status"], "CONDITIONED_TERMINAL_TYPE_SELECTED")
        self.assertEqual(
            result["terminal_selection_application"]["applied_rule_id"],
            rule_id,
        )
        self.assertNotIn(
            "terminal_type_rule_override_id",
            result["deterministic_result"]["input"],
        )

    def test_invented_terminal_rule_is_nonblocking_and_cannot_replace_default(self) -> None:
        prepared = llm_bridge.hybrid_prepare(
            tower_default_result(),
            {"status": "NOT_REQUESTED", "hits": []},
            "textual_condition_judgment",
        )
        context_sha256 = prepared["context_pack"]["terminal_type_rule_registry"][0][
            "selection_context_sha256"
        ]
        output = empty_output(prepared, "textual_condition_judgment")
        output["terminal_selection_assists"] = [{
            "assist_id": "invented_type_rule",
            "terminal_rule_id": "tower:model_invented:magic_tray",
            "condition_id": "tower_condition:model_invented",
            "selection_context_sha256": context_sha256,
            "reason": "This rule is not in the frozen registry and must be rejected locally.",
            "citations": ["deterministic_result"],
        }]
        organize_output(output)

        result = llm_bridge.hybrid_continue(prepared, output)

        self.assertIsNone(result["verified_terminal_selection_override_id"])
        self.assertEqual(result["verified_terminal_selection_overrides"], {})
        self.assertEqual(
            result["terminal_selection_assist_validation"][0]["status"],
            "REJECTED_NONBLOCKING_UNKNOWN_RULE",
        )

    def test_candidate_reference_requires_exact_existing_id_designation_and_both_hashes(self) -> None:
        prepared = llm_bridge.hybrid_prepare(
            pump_result(), {"status": "NOT_REQUESTED", "hits": []}, "ambiguity_resolution"
        )
        candidate = prepared["context_pack"]["candidate_registry"][0]
        output = empty_output(prepared, "ambiguity_resolution")
        output["ambiguity_decision"] = {
            "status": "candidate_reference",
            "selected_candidate_id": candidate["candidate_id"],
            "selected_designation": candidate["designation"],
            "selection_feature_vector_sha256": candidate["selection_feature_vector_sha256"],
            "selection_context_sha256": candidate["selection_context_sha256"],
            "reason": "reference only",
            "citations": ["deterministic_result"],
        }
        organize_output(output)
        accepted = llm_bridge.hybrid_continue(prepared, output)
        self.assertEqual(accepted["candidate_reference"]["selected_candidate_id"], candidate["candidate_id"])
        tampered = copy.deepcopy(output)
        tampered["ambiguity_decision"]["selection_context_sha256"] = candidate["selection_feature_vector_sha256"]
        with self.assertRaisesRegex(ValueError, "不一致"):
            llm_bridge.hybrid_continue(prepared, tampered)

    def test_free_text_candidate_model_is_rejected_in_legacy_and_strict_paths(self) -> None:
        legacy = llm_bridge.validate_proposal({
            "changes": [{"field": "candidate_model", "value": "invented-X"}]
        })
        self.assertFalse(legacy["accepted_changes"])
        self.assertEqual(
            legacy["rejected_changes"][0]["reason"],
            "candidate_model_requires_deterministic_candidate_reference",
        )
        prepared = llm_bridge.hybrid_prepare(
            pump_result(), {"status": "NOT_REQUESTED", "hits": []}, "ambiguity_resolution"
        )
        output = empty_output(prepared, "ambiguity_resolution")
        output["proposed_changes"] = [{
            "field": "candidate_model", "value": "invented-X", "reason": "guess",
            "citations": ["deterministic_result"],
        }]
        with self.assertRaisesRegex(ValueError, "candidate_model"):
            llm_bridge.hybrid_continue(prepared, output)

    def test_full_family_loader_returns_whitelisted_hashed_assets_and_partial_on_limit(self) -> None:
        bundle = app_core.knowledge_asset_bundle(
            "full_family", ["equipment_core"], family_id="family_pump", max_chars=10_000
        )
        self.assertTrue(bundle["assets"])
        self.assertEqual(bundle["coverage_status"], "PARTIAL")
        self.assertTrue(bundle["truncated_assets"])
        self.assertLessEqual(bundle["char_count"], bundle["max_chars"])
        self.assertTrue(all(len(item["sha256"]) == 64 for item in bundle["assets"]))
        self.assertTrue(all(item["path"].startswith("equipment_core/") for item in bundle["assets"]))

    def test_full_scope_ignores_caller_claimed_complete_result_and_uses_local_loader(self) -> None:
        fake = {
            "status": "PASS_FULL_ASSET_BUNDLE",
            "coverage_status": "COMPLETE",
            "assets": [{"path": "caller/fake.md", "content": "single fake asset"}],
        }
        local_bundle = {
            "schema": "equipment-design-knowledge-asset-bundle-v1",
            "status": "PASS_FULL_ASSET_BUNDLE",
            "scope": "full_bundle",
            "family_id": None,
            "selected_packages": ["equipment_core"],
            "unavailable_packages": [],
            "coverage_definition": {"basis": "explicit_selected_packages"},
            "coverage_status": "PARTIAL",
            "assets": [{
                "package_id": "equipment_core",
                "path": "equipment_core/local.md",
                "sha256": "A" * 64,
                "source_file_sha256": None,
                "source_file_sha256_status": "NOT_EMITTED_PARTIAL_ASSET",
                "content": "local bounded asset",
                "truncated": True,
                "char_count": 19,
            }],
            "truncated_assets": [{
                "path": "equipment_core/local.md",
                "reason": "asset_truncated_at_19_characters",
            }],
            "char_count": 19,
            "max_chars": 19,
            "asset_count": 1,
            "candidate_asset_count": 2,
        }
        with patch.object(app_core, "knowledge_asset_bundle", return_value=local_bundle) as loader:
            response = EquipmentDesignApi().hybrid_prepare(
                pump_result(),
                {"enabled": False, "result": fake, "package_ids": ["equipment_core"]},
                "audit",
                "full_bundle",
            )
        self.assertTrue(response["ok"], response)
        loader.assert_called_once()
        context = response["knowledge_context"]
        self.assertTrue(context["caller_supplied_result_ignored_for_full_coverage"])
        self.assertEqual(context["coverage_status"], "PARTIAL")
        self.assertEqual(context["assets"][0]["path"], "equipment_core/local.md")
        self.assertNotIn("caller/fake.md", str(response["value"]))
        self.assertEqual(response["value"]["context_pack"]["coverage_status"], "PARTIAL")

    def test_supplied_minimum_or_routed_result_is_context_only(self) -> None:
        fake = {
            "status": "PASS_FULL_ASSET_BUNDLE",
            "coverage_status": "COMPLETE",
            "assets": [{"path": "caller/one.md", "content": "advisory only"}],
        }
        response = EquipmentDesignApi().hybrid_prepare(
            pump_result(),
            {"result": fake},
            "audit",
            "routed",
        )
        self.assertTrue(response["ok"], response)
        context = response["knowledge_context"]
        self.assertEqual(context["status"], "CALLER_SUPPLIED_CONTEXT")
        self.assertEqual(context["coverage_status"], "PARTIAL")
        self.assertEqual(context["caller_declared_coverage_status"], "COMPLETE")
        self.assertNotEqual(response["value"]["context_pack"]["coverage_status"], "COMPLETE")

    def test_implicit_full_bundle_covers_all_available_and_reports_unavailable(self) -> None:
        with writable_temp_directory() as temp_dir:
            root = Path(temp_dir)
            root_a = root / "a"
            root_b = root / "b"
            root_a.mkdir()
            root_b.mkdir()
            (root_a / "a.md").write_text("A", encoding="utf-8")
            (root_b / "b.md").write_text("B", encoding="utf-8")
            registry = {
                "schema": "equipment-design-knowledge-packages-v1",
                "max_selected": 3,
                "packages": [
                    {"id": "a", "root": str(root_a), "available": True, "default_selected": True},
                    {"id": "b", "root": str(root_b), "available": True, "default_selected": False},
                    {"id": "missing", "root": str(root / "missing"), "available": False, "default_selected": False},
                ],
            }
            with patch.object(app_core, "knowledge_packages", return_value=registry):
                implicit = app_core.knowledge_asset_bundle("full_bundle", max_chars=10_000)
                explicit = app_core.knowledge_asset_bundle("full_bundle", ["a"], max_chars=10_000)
        self.assertEqual(implicit["selected_packages"], ["a", "b"])
        self.assertEqual([item["id"] for item in implicit["unavailable_packages"]], ["missing"])
        self.assertEqual(implicit["coverage_definition"]["basis"], "all_registered_packages")
        self.assertEqual(implicit["coverage_status"], "PARTIAL")
        self.assertEqual(explicit["selected_packages"], ["a"])
        self.assertEqual(explicit["unavailable_packages"], [])
        self.assertEqual(explicit["coverage_definition"]["basis"], "explicit_selected_packages")
        self.assertEqual(explicit["coverage_status"], "COMPLETE")

    def test_full_bundle_reads_only_remaining_plus_one_and_stops_at_10k(self) -> None:
        with writable_temp_directory() as temp_dir:
            root = Path(temp_dir)
            (root / "000_large.md").write_text("X" * 200_000, encoding="utf-8")
            for index in range(40):
                (root / f"{index + 1:03d}.md").write_text("tail", encoding="utf-8")
            registry = {
                "schema": "equipment-design-knowledge-packages-v1",
                "max_selected": 3,
                "packages": [
                    {"id": "bounded", "root": str(root), "available": True, "default_selected": True},
                ],
            }
            original_reader = app_core._read_text_prefix
            calls: list[tuple[str, int]] = []

            def observed_reader(path: Path, limit: int) -> tuple[str, bool]:
                calls.append((path.name, limit))
                return original_reader(path, limit)

            started = time.perf_counter()
            with patch.object(app_core, "knowledge_packages", return_value=registry), patch.object(
                app_core, "_read_text_prefix", side_effect=observed_reader
            ):
                bundle = app_core.knowledge_asset_bundle("full_bundle", max_chars=10_000)
            elapsed = time.perf_counter() - started
        self.assertEqual(calls, [("000_large.md", 10_000)])
        self.assertLess(elapsed, 2.0)
        self.assertEqual(bundle["char_count"], 10_000)
        self.assertIsNone(bundle["assets"][0]["source_file_sha256"])
        self.assertEqual(bundle["assets"][0]["source_file_sha256_status"], "NOT_EMITTED_PARTIAL_ASSET")
        summaries = [item for item in bundle["truncated_assets"] if item.get("remaining_asset_count")]
        self.assertEqual(summaries[0]["remaining_asset_count"], 40)

    def test_full_family_content_scan_has_deterministic_budget(self) -> None:
        with writable_temp_directory() as temp_dir:
            root = Path(temp_dir)
            (root / "README.md").write_text("family index", encoding="utf-8")
            (root / "zzz_large.md").write_text("unrelated " * 20_000, encoding="utf-8")
            (root / "zzzz_never_read.md").write_text("family_pump", encoding="utf-8")
            registry = {
                "schema": "equipment-design-knowledge-packages-v1",
                "max_selected": 3,
                "packages": [
                    {"id": "equipment_core", "root": str(root), "available": True, "default_selected": True},
                ],
            }
            original_reader = app_core._read_text_prefix
            calls: list[tuple[str, int]] = []

            def observed_reader(path: Path, limit: int) -> tuple[str, bool]:
                calls.append((path.name, limit))
                return original_reader(path, limit)

            with patch.object(app_core, "knowledge_packages", return_value=registry), patch.object(
                app_core, "_read_text_prefix", side_effect=observed_reader
            ):
                bundle = app_core.knowledge_asset_bundle(
                    "full_family", ["equipment_core"], family_id="family_pump", max_chars=10_000
                )
        self.assertEqual(calls[0], ("README.md", 10_000))
        self.assertEqual(calls[1], ("zzz_large.md", 40_000))
        self.assertEqual(len(calls), 2)
        self.assertEqual(bundle["family_scan_chars"], bundle["family_scan_max_chars"])
        self.assertEqual(bundle["coverage_status"], "PARTIAL")
        self.assertTrue(any("family_content_scan" in item["reason"] for item in bundle["truncated_assets"]))

    def test_agent_prepare_continue_and_mock_run_share_one_contract(self) -> None:
        source_input = {
            "operation": "manual_match",
            "payload": {
                "selection_id": "block:PUMP",
                "values": {
                    "equipment_tag": "P-HYBRID",
                    "phase": "liquid",
                    "flow_m3_h": 20,
                    "head_m": 45,
                    "density_kg_m3": 900,
                    "efficiency_percent": 75,
                },
            },
        }
        prepare_response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "hybrid_prepare",
            "payload": {
                "input": source_input,
                "knowledge": {"enabled": False},
                "injection_point": "audit",
                "context_scope": "minimum",
            },
        })
        self.assertEqual(code, 0, prepare_response)
        prepared = prepare_response["result"]
        output = empty_output(prepared)
        continue_response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "hybrid_continue",
            "payload": {"prepared": prepared, "step_output": output},
        })
        self.assertEqual(code, 0, continue_response)
        with patch.object(llm_bridge.urllib.request, "urlopen", side_effect=AssertionError("network forbidden")):
            run_response, code = agent.execute_request({
                "schema": "equipment-design-agent-request-v1",
                "operation": "hybrid_run",
                "payload": {
                    "input": source_input,
                    "knowledge": {"enabled": False},
                    "injection_point": "audit",
                    "context_scope": "minimum",
                    "llm": {"enabled": True, "config": {"provider": "mock", "mock_response": output}},
                },
            })
        self.assertEqual(code, 0, run_response)
        self.assertEqual(run_response["result"]["orchestration"]["step_output"], continue_response["result"]["step_output"])

    def test_apply_recalculates_and_revalidates_candidate_double_hash(self) -> None:
        values = {
            "equipment_tag": "P-HYBRID",
            "phase": "liquid",
            "flow_m3_h": 20,
            "head_m": 45,
            "density_kg_m3": 900,
            "efficiency_percent": 75,
        }
        source_input = {
            "operation": "manual_match",
            "payload": {"selection_id": "block:PUMP", "values": values},
        }
        prepare_response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "hybrid_prepare",
            "payload": {
                "input": source_input,
                "knowledge": {"enabled": False},
                "injection_point": "ambiguity_resolution",
                "context_scope": "minimum",
            },
        })
        self.assertEqual(code, 0, prepare_response)
        prepared = prepare_response["result"]
        candidate = prepared["context_pack"]["candidate_registry"][0]
        output = empty_output(prepared, "ambiguity_resolution")
        output["ambiguity_decision"] = {
            "status": "candidate_reference",
            "selected_candidate_id": candidate["candidate_id"],
            "selected_designation": candidate["designation"],
            "selection_feature_vector_sha256": candidate["selection_feature_vector_sha256"],
            "selection_context_sha256": candidate["selection_context_sha256"],
            "reason": "reference only",
            "citations": ["deterministic_result"],
        }
        organize_output(output)
        continue_response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "hybrid_continue",
            "payload": {"prepared": prepared, "step_output": output},
        })
        self.assertEqual(code, 0, continue_response)
        orchestration = continue_response["result"]
        response, code = agent.execute_request({
            "schema": "equipment-design-agent-request-v1",
            "operation": "llm_apply",
            "payload": {
                "proposal": orchestration,
                "approval": {
                    "approved": True,
                    "approved_change_ids": [],
                    "approved_by": "unit-test",
                    "context_sha256": orchestration["context_sha256"],
                    "orchestration_sha256": orchestration["orchestration_sha256"],
                },
            },
        })
        self.assertEqual(code, 0, response)
        self.assertEqual(
            response["result"]["candidate_reference_validation"]["status"],
            "PASS_EXACT_DETERMINISTIC_REFERENCE",
        )


if __name__ == "__main__":
    unittest.main()
