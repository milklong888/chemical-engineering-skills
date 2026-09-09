from __future__ import annotations

import json
import hashlib
import math
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path

import aspen_equipment_derivation as adapter


@contextmanager
def workspace_temporary_directory():
    """Keep test writes inside the managed workspace instead of system TEMP."""
    path = adapter.PACKAGE_ROOT / "outputs" / "derivation_test_runs" / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=False)
    yield str(path)


class AspenEquipmentDerivationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sample_path = adapter.PACKAGE_ROOT / "data" / "aspen_equipment_export_sample.json"
        cls.sample = json.loads(cls.sample_path.read_text(encoding="utf-8"))

    def test_clean_sample_derives_pump_family_and_complete_source_chain(self) -> None:
        result = adapter.derive_bundle(self.sample, self.sample_path)
        self.assertEqual(result["status"], "DERIVED")
        self.assertEqual(result["formal_use_gate"], "ELIGIBLE_AS_PROCESS_BASIS")
        self.assertEqual(result["aspen_run_gate"]["run_status_evidence"]["status"], "VERIFIED")
        self.assertTrue(result["aspen_run_gate"]["run_status_evidence"]["raw_history_required"])
        equipment = result["equipment"][0]
        self.assertEqual(equipment["match_result"]["match"]["family_id"], "family_pump")
        self.assertEqual(equipment["match_result"]["model_decision"]["model_status"], "type_selected")
        self.assertFalse(equipment["match_result"]["llm_used"])
        head = next(item for item in equipment["match_result"]["calculations"] if item["calculation_id"] == "pump_head_from_pressure")
        self.assertAlmostEqual(head["value"], 45.5873130508, places=8)
        self.assertFalse(equipment["match_result"]["model_decision"]["sizing_missing_fields"])
        source_hash = result["source_export_sha256"]
        self.assertTrue(equipment["parameter_lineage"])
        self.assertTrue(all(item["source_file_sha256"] == source_hash for item in equipment["parameter_lineage"]))
        self.assertEqual(equipment["input_provenance"]["status"], "ASPEN_DERIVED_PROCESS_SIDE")
        self.assertEqual(equipment["match_result"]["input_provenance"]["status"], "ASPEN_DERIVED_PROCESS_SIDE")
        self.assertFalse(equipment["input_provenance"]["mechanical_design_basis_established"])
        self.assertFalse(equipment["evidence_boundary"]["mechanical_design_pressure_established"])
        pressure_envelope = next(
            item for item in equipment["parameter_lineage"]
            if item["target_field"] == "operating_pressure_mpa"
        )
        self.assertEqual(pressure_envelope["evidence_class"], "J")
        self.assertEqual(pressure_envelope["result_status"], "PROVISIONAL")
        self.assertEqual(pressure_envelope["promotion_cap"], "PROCESS_SIDE_ENVELOPE_ONLY")
        self.assertIn("not mechanical design pressure", pressure_envelope["warning"])
        density_lineage = next(
            item for item in equipment["parameter_lineage"]
            if item["target_field"] == "density_kg_m3"
        )
        self.assertEqual(density_lineage["evidence_class"], "D")
        self.assertIn(
            "inlet_pressure_mpa = P_bar×0.1 = 1.2×0.1 = 0.12 MPa",
            equipment["derivation_chain"],
        )

    def test_radfrac_diameter_maps_only_to_inner_diameter_and_drives_tower_area(self) -> None:
        payload = json.loads(json.dumps(self.sample))
        payload["blocks"][0].update({
            "block_id": "T-101",
            "block_type": "RADFRAC",
            "DIAMETER": 2.4,
        })
        payload["blocks"][0].pop("efficiency_percent", None)
        payload["equipment_map"][0].update({
            "block_id": "T-101",
            "equipment_tag": "T-101",
            "process_function": "distillation column",
        })
        payload["units"] = {"block.DIAMETER": "m"}

        with workspace_temporary_directory() as directory:
            path = Path(directory) / "radfrac_diameter.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = adapter.derive_bundle(payload, path)

        self.assertEqual(result["status"], "DERIVED", result.get("errors"))
        equipment = result["equipment"][0]
        canonical = equipment["canonical_match_input"]
        self.assertEqual(equipment["match_result"]["match"]["family_id"], "family_tower")
        self.assertAlmostEqual(canonical["inner_diameter_mm"], 2400.0, places=12)
        self.assertNotIn("diameter_mm", canonical)

        diameter_lineage = next(
            item for item in equipment["parameter_lineage"]
            if item["target_field"] == "inner_diameter_mm"
        )
        self.assertEqual(diameter_lineage["source_field"], "DIAMETER")
        self.assertEqual(diameter_lineage["source_object_type"], "block")
        self.assertEqual(diameter_lineage["source_object_id"], "T-101")
        self.assertEqual(diameter_lineage["source_file_path"], str(path.resolve()))
        self.assertEqual(diameter_lineage["transform"], "L_mm=L_m×1000")
        self.assertEqual(diameter_lineage["unit"], "mm")

        area = next(
            item for item in equipment["match_result"]["calculations"]
            if item["calculation_id"] == "tower_cross_section"
        )
        expected_area = math.pi * 2.4**2 / 4.0
        self.assertEqual(area["target_field"], "tower_cross_section_m2")
        self.assertAlmostEqual(area["value"], expected_area, places=12)
        self.assertIn("2400/1000", area["formula_chain"]["substitution"])
        self.assertAlmostEqual(
            equipment["match_result"]["derived_parameters"]["tower_cross_section_m2"],
            expected_area,
            places=12,
        )

    def test_flash_vessel_diameter_stays_generic_and_never_becomes_inner_diameter(self) -> None:
        payload = json.loads(json.dumps(self.sample))
        payload["blocks"][0].update({
            "block_id": "V-101",
            "block_type": "FLASH2",
            "DIAMETER": 1.8,
        })
        payload["blocks"][0].pop("efficiency_percent", None)
        payload["equipment_map"][0].update({
            "block_id": "V-101",
            "equipment_tag": "V-101",
            "process_function": "gas-liquid separator",
        })
        payload["units"] = {"block.DIAMETER": "m"}

        with workspace_temporary_directory() as directory:
            path = Path(directory) / "flash_vessel_diameter.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = adapter.derive_bundle(payload, path)

        self.assertEqual(result["status"], "DERIVED", result.get("errors"))
        equipment = result["equipment"][0]
        canonical = equipment["canonical_match_input"]
        self.assertEqual(
            equipment["match_result"]["match"]["family_id"],
            "family_reactor_vessel_separator",
        )
        self.assertAlmostEqual(canonical["diameter_mm"], 1800.0, places=12)
        self.assertNotIn("inner_diameter_mm", canonical)

        diameter_lineage = next(
            item for item in equipment["parameter_lineage"]
            if item["target_field"] == "diameter_mm"
        )
        self.assertEqual(diameter_lineage["source_field"], "DIAMETER")
        self.assertEqual(diameter_lineage["source_object_type"], "block")
        self.assertEqual(diameter_lineage["source_object_id"], "V-101")
        self.assertEqual(diameter_lineage["source_file_path"], str(path.resolve()))
        self.assertEqual(diameter_lineage["transform"], "L_mm=L_m×1000")
        self.assertFalse(any(
            item["target_field"] == "inner_diameter_mm"
            for item in equipment["parameter_lineage"]
        ))
        self.assertFalse(any(
            item["calculation_id"] == "tower_cross_section"
            for item in equipment["match_result"]["calculations"]
        ))

    def test_absolute_atmosphere_propagates_to_equipment_piping_and_design_pressure(self) -> None:
        payload = json.loads(json.dumps(self.sample))
        payload["case"]["pressure_basis"] = "absolute"
        payload["case"]["atmospheric_pressure_mpa"] = 0.101325
        with workspace_temporary_directory() as directory:
            path = Path(directory) / "absolute_with_atmosphere.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = adapter.derive_bundle(payload, path)

        equipment = result["equipment"][0]
        canonical = equipment["canonical_match_input"]
        self.assertEqual(canonical["pressure_basis"], "absolute")
        self.assertAlmostEqual(canonical["atmospheric_pressure_mpa"], 0.101325)
        atmosphere_lineage = next(
            item for item in equipment["parameter_lineage"]
            if item["target_field"] == "atmospheric_pressure_mpa"
        )
        self.assertEqual(atmosphere_lineage["source_field"], "case.atmospheric_pressure_mpa")
        for pipe in result["piping"]:
            self.assertAlmostEqual(pipe["canonical_match_input"]["atmospheric_pressure_mpa"], 0.101325)
            self.assertTrue(any(
                item["target_field"] == "atmospheric_pressure_mpa"
                for item in pipe["parameter_lineage"]
            ))

        rules = adapter.matcher.load_json(adapter.matcher.RULES_PATH)
        graph = adapter.matcher.load_graph()
        storage = adapter.matcher.match_one(
            {
                "equipment_family": "family_storage_vessel",
                "operating_pressure_mpa": canonical["operating_pressure_mpa"],
                "pressure_basis": canonical["pressure_basis"],
                "atmospheric_pressure_mpa": canonical["atmospheric_pressure_mpa"],
                "design_pressure_factor": 1.1,
            },
            rules,
            graph,
        )
        pressure = next(
            item for item in storage["calculations"]
            if item["calculation_id"] == "design_pressure"
        )
        self.assertAlmostEqual(pressure["value"], (0.5 - 0.101325) * 1.1, places=10)
        self.assertEqual(pressure["pressure_basis_conversion"]["output_basis"], "gauge")

    def test_absolute_without_atmosphere_uses_visible_fallback_but_gauge_remains_explicit(self) -> None:
        rules = adapter.matcher.load_json(adapter.matcher.RULES_PATH)
        graph = adapter.matcher.load_graph()
        absolute = adapter.matcher.match_one(
            {
                "equipment_family": "family_storage_vessel",
                "operating_pressure_mpa": 0.5,
                "pressure_basis": "absolute",
                "design_pressure_factor": 1.1,
            },
            rules,
            graph,
        )
        pressure = next(
            item for item in absolute["calculations"]
            if item["calculation_id"] == "design_pressure"
        )
        self.assertAlmostEqual(pressure["value"], (0.5 - 0.101325) * 1.1)
        atmosphere = next(
            item for item in absolute["design_fallbacks"]
            if item["field_id"] == "atmospheric_pressure_mpa"
        )
        self.assertEqual(atmosphere["evidence_class"], "J")
        self.assertEqual(atmosphere["promotion_cap"], "TYPE_SCREENING")
        self.assertIn("design_pressure_mpa", absolute["derived_parameters"])

        gauge = adapter.matcher.match_one(
            {
                "equipment_family": "family_storage_vessel",
                "operating_pressure_mpa": 0.5,
                "pressure_basis": "gauge",
                "atmospheric_pressure_mpa": 0.101325,
                "design_pressure_factor": 1.1,
            },
            rules,
            graph,
        )
        gauge_pressure = next(
            item for item in gauge["calculations"]
            if item["calculation_id"] == "design_pressure"
        )
        self.assertAlmostEqual(gauge_pressure["value"], 0.55)
        self.assertEqual(gauge_pressure["pressure_basis_conversion"]["input_basis"], "gauge")

    def test_referenced_material_streams_generate_independent_piping_matches_with_visible_fallbacks(self) -> None:
        result = adapter.derive_bundle(self.sample, self.sample_path)
        self.assertEqual(result["status"], "DERIVED")
        self.assertEqual(result["formal_use_gate"], "ELIGIBLE_AS_PROCESS_BASIS")
        self.assertEqual(result["piping_count"], 2)
        self.assertFalse(result["piping_evidence_boundary"]["affects_aspen_formal_use_gate"])
        self.assertEqual(
            result["piping_evidence_boundary"]["aspen_formal_use_gate_snapshot"],
            result["formal_use_gate"],
        )

        piping = {item["stream_id"]: item for item in result["piping"]}
        self.assertEqual(set(piping), {"S-IN", "S-OUT"})
        forbidden_defaults = {
            "design_temperature_c", "target_velocity_m_s", "material", "selected_dn",
            "selected_outer_diameter_mm", "selected_wall_thickness_mm", "wall_series",
        }
        for stream_id, pipe in piping.items():
            canonical = pipe["canonical_match_input"]
            self.assertEqual(canonical["equipment_tag"], stream_id)
            self.assertEqual(canonical["stream_id"], stream_id)
            self.assertEqual(canonical["equipment_family"], "family_process_piping")
            for field in (
                "process_function", "phase", "pressure_basis", "flow_m3_h", "mass_flow_kg_h",
                "density_kg_m3", "operating_pressure_mpa", "operating_temperature_c",
            ):
                self.assertIn(field, canonical)
            self.assertFalse(forbidden_defaults & set(canonical))

            match_result = pipe["match_result"]
            self.assertEqual(match_result["status"], "MATCHED")
            self.assertEqual(match_result["match"]["family_id"], "family_process_piping")
            self.assertEqual(match_result["design_parameter_package"]["status"], "READY_FOR_CANDIDATE_MATCHING")
            self.assertEqual(
                match_result["model_recommendation"]["selection_execution"]["status"],
                "EXECUTED",
            )
            terminal = match_result["model_recommendation"]["terminal_selection"]
            self.assertEqual(terminal["status"], "DEFAULTED_TERMINAL_TYPE_SELECTED")
            self.assertEqual(terminal["selection_basis"], "registered_default")
            self.assertEqual(terminal["recommended_type"], "无缝钢制工艺管道")
            label_data = pipe["pfd_edge_label_data"]
            self.assertEqual(label_data["default_view"], "compact_label")
            compact = label_data["compact_label"]
            self.assertEqual(compact["stream_id"], stream_id)
            self.assertEqual(compact["type_or_model"], "无缝钢制工艺管道")
            self.assertEqual(compact["status"], "EXECUTED")
            self.assertLessEqual(len(compact["key_values"]), 3)
            self.assertTrue(
                set(compact["key_values"]).issubset({
                    "flow_m3_h", "operating_pressure_mpa", "operating_temperature_c",
                })
            )
            self.assertFalse({
                "values", "next_fields", "minimum_missing_sets", "from_block_ids", "to_block_ids",
            } & set(compact))
            self.assertFalse(forbidden_defaults & set(compact["key_values"]))
            details = label_data["details"]
            missing = {item["field"] for item in details["next_fields"]}
            self.assertFalse({"selected_outer_diameter_mm", "selected_wall_thickness_mm"} & missing)
            self.assertEqual(details["values"]["operating_temperature_c"], canonical["operating_temperature_c"])
            self.assertFalse(forbidden_defaults & set(match_result["normalized_input"]))
            fallback_fields = {item["field_id"] for item in match_result["design_fallbacks"]}
            self.assertTrue({"target_velocity_m_s", "design_temperature_c", "material"}.issubset(fallback_fields))
            self.assertTrue(forbidden_defaults & set(match_result["effective_normalized_input"]))
            self.assertIn("required_inner_diameter_mm", match_result["derived_parameters"])
            self.assertIn("selected_outer_diameter_mm", match_result["derived_parameters"])
            self.assertIn(
                "pipe_standard_dn_selection",
                {item["calculation_id"] for item in match_result["calculations"]},
            )
            self.assertEqual(pipe["evidence_boundary"]["status"], "PROCESS_DATA_ONLY")
            self.assertFalse(pipe["evidence_boundary"]["affects_aspen_formal_use_gate"])

        self.assertEqual(piping["S-IN"]["pfd_edge_label_data"]["details"]["from_block_ids"], [])
        self.assertEqual(piping["S-IN"]["pfd_edge_label_data"]["details"]["to_block_ids"], ["P-101"])
        self.assertEqual(piping["S-OUT"]["pfd_edge_label_data"]["details"]["from_block_ids"], ["P-101"])
        self.assertEqual(piping["S-OUT"]["pfd_edge_label_data"]["details"]["to_block_ids"], [])

    def test_unreferenced_and_empty_placeholder_stream_errors_are_isolated(self) -> None:
        payload = json.loads(json.dumps(self.sample))
        payload["streams"].extend([
            {
                "stream_id": "UNUSED-PLACEHOLDER",
                "stream_record_type": "MATERIAL",
                "VOLFLMX": 123.0,
            },
            {
                "stream_id": "",
                "stream_record_type": "UNKNOWN",
                "VOLFLMX": 456.0,
            },
        ])
        payload["units"] = {"stream.VOLFLMX": "unknown-placeholder-unit"}
        with workspace_temporary_directory() as directory:
            path = Path(directory) / "isolated_placeholders.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = adapter.derive_bundle(payload, path)

        self.assertEqual(result["status"], "DERIVED", result.get("errors"))
        self.assertEqual({item["stream_id"] for item in result["piping"]}, {"S-IN", "S-OUT"})
        diagnostics = result["isolated_stream_diagnostics"]
        self.assertTrue(any(item.get("stream_id") == "UNUSED-PLACEHOLDER" for item in diagnostics))
        self.assertTrue(any(item.get("stream_id") == "" for item in diagnostics))
        self.assertTrue(any(
            error.get("code") == "UNSUPPORTED_ASPEN_UNIT"
            for item in diagnostics
            for error in item.get("errors", [])
        ))

    def test_dirty_run_remains_provisional(self) -> None:
        payload = json.loads(json.dumps(self.sample))
        payload["case"]["run_status"]["warnings"] = 1
        with workspace_temporary_directory() as directory:
            path = Path(directory) / "dirty.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = adapter.derive_bundle(payload, path)
        self.assertEqual(result["aspen_run_gate"]["status"], "DIRTY_RUN")
        self.assertEqual(result["formal_use_gate"], "PROVISIONAL_NOT_FORMAL_PROCESS_BASIS")

    def test_fractional_run_counts_are_not_truncated_to_clean(self) -> None:
        payload = json.loads(json.dumps(self.sample))
        payload["case"]["run_status"]["warnings"] = 0.5
        with workspace_temporary_directory() as directory:
            path = Path(directory) / "fractional_count.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = adapter.derive_bundle(payload, path)
        self.assertEqual(result["aspen_run_gate"]["status"], "UNVERIFIED_RUN_STATUS")
        self.assertEqual(result["formal_use_gate"], "PROVISIONAL_NOT_FORMAL_PROCESS_BASIS")

    def test_real_aspen_clean_statement_is_accepted_as_zero_counts(self) -> None:
        self.assertEqual(
            adapter.parse_raw_history_counts("NO ERRORS OR WARNINGS GENERATED\n"),
            {"terminal_errors": 0, "severe_errors": 0, "errors": 0, "warnings": 0},
        )

    def test_real_aspen_summary_table_sums_each_error_row(self) -> None:
        history = """*** SUMMARY OF ERRORS ***
                 PHYSICAL
                 PROPERTY  SYSTEM  SIMULATION
TERMINAL ERRORS      0        0         0
  SEVERE ERRORS      0        0         1
         ERRORS      0        0         2
       WARNINGS      1        0         3
"""
        self.assertEqual(
            adapter.parse_raw_history_counts(history),
            {"terminal_errors": 0, "severe_errors": 1, "errors": 2, "warnings": 4},
        )

    def test_zero_count_json_cannot_hide_raw_history_warning(self) -> None:
        payload = json.loads(json.dumps(self.sample))
        with workspace_temporary_directory() as directory:
            root = Path(directory)
            history = root / "warning.his"
            history.write_text(
                "TERMINAL ERRORS: 0\nSEVERE ERRORS: 0\nERRORS: 0\nWARNINGS: 0\n* WARNING IN THE TEST BLOCK\n",
                encoding="utf-8",
            )
            status_evidence = {
                "schema": "aspen-run-status-evidence-v1",
                "case_id": payload["case"]["case_id"],
                "run_status": payload["case"]["run_status"],
                "raw_history_path": history.name,
                "raw_history_sha256": hashlib.sha256(history.read_bytes()).hexdigest(),
            }
            evidence_path = root / "run_status.json"
            evidence_path.write_text(json.dumps(status_evidence, ensure_ascii=False), encoding="utf-8")
            payload["case"]["run_status_evidence_path"] = evidence_path.name
            payload["case"]["run_status_evidence_sha256"] = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
            bundle_path = root / "bundle.json"
            bundle_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = adapter.derive_bundle(payload, bundle_path)
        self.assertEqual(result["aspen_run_gate"]["run_status_evidence"]["status"], "RAW_HISTORY_PROBLEM_LINES")
        self.assertEqual(result["aspen_run_gate"]["status"], "UNVERIFIED_RUN_STATUS_EVIDENCE")
        self.assertEqual(result["formal_use_gate"], "PROVISIONAL_NOT_FORMAL_PROCESS_BASIS")

    def test_zero_count_json_cannot_hide_raw_history_terminal_error_count(self) -> None:
        payload = json.loads(json.dumps(self.sample))
        with workspace_temporary_directory() as directory:
            root = Path(directory)
            history = root / "terminal_error.his"
            history.write_text(
                "TERMINAL ERRORS: 1\nSEVERE ERRORS: 0\nERRORS: 0\nWARNINGS: 0\n",
                encoding="utf-8",
            )
            status_evidence = {
                "schema": "aspen-run-status-evidence-v1",
                "case_id": payload["case"]["case_id"],
                "run_status": payload["case"]["run_status"],
                "raw_history_path": history.name,
                "raw_history_sha256": hashlib.sha256(history.read_bytes()).hexdigest(),
            }
            evidence_path = root / "run_status.json"
            evidence_path.write_text(json.dumps(status_evidence, ensure_ascii=False), encoding="utf-8")
            payload["case"]["run_status_evidence_path"] = evidence_path.name
            payload["case"]["run_status_evidence_sha256"] = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
            bundle_path = root / "bundle.json"
            bundle_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = adapter.derive_bundle(payload, bundle_path)
        self.assertEqual(result["aspen_run_gate"]["run_status_evidence"]["status"], "RAW_HISTORY_COUNT_MISMATCH")
        self.assertEqual(result["formal_use_gate"], "PROVISIONAL_NOT_FORMAL_PROCESS_BASIS")

    def test_pressure_direction_disambiguates_compr_to_recovery_turbine(self) -> None:
        payload = json.loads(json.dumps(self.sample))
        payload["blocks"][0]["block_type"] = "COMPR"
        payload["streams"][0]["pressure_bar"] = 5.0
        payload["streams"][1]["pressure_bar"] = 1.2
        with workspace_temporary_directory() as directory:
            path = Path(directory) / "wrong_direction.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = adapter.derive_bundle(payload, path)
        self.assertEqual(result["formal_use_gate"], "PROVISIONAL_NOT_FORMAL_PROCESS_BASIS")
        match_result = result["equipment"][0]["match_result"]
        self.assertEqual(match_result["match"]["family_id"], "family_liquid_power_recovery_turbine")
        self.assertFalse(any(item["code"] == "CALCULATION_HARD_BLOCKER" for item in result["formal_use_blockers"]))

    def test_pump_pressure_drop_blocker_propagates_to_formal_use_gate(self) -> None:
        payload = json.loads(json.dumps(self.sample))
        payload["streams"][0]["pressure_bar"] = 5.0
        payload["streams"][1]["pressure_bar"] = 1.2
        with workspace_temporary_directory() as directory:
            path = Path(directory) / "pump_wrong_direction.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = adapter.derive_bundle(payload, path)
        self.assertEqual(result["formal_use_gate"], "PROVISIONAL_NOT_FORMAL_PROCESS_BASIS")
        self.assertTrue(any(item["code"] == "CALCULATION_HARD_BLOCKER" for item in result["formal_use_blockers"]))

    def test_reported_pressure_ratio_mismatch_propagates_to_formal_use_gate(self) -> None:
        payload = json.loads(json.dumps(self.sample))
        payload["blocks"][0]["block_type"] = "COMPR"
        payload["blocks"][0]["pressure_ratio"] = 99.0
        with workspace_temporary_directory() as directory:
            path = Path(directory) / "ratio_mismatch.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = adapter.derive_bundle(payload, path)
        self.assertEqual(result["formal_use_gate"], "PROVISIONAL_NOT_FORMAL_PROCESS_BASIS")
        self.assertTrue(any(item["code"] == "ASPEN_RECONCILIATION_FAIL" for item in result["formal_use_blockers"]))

    def test_raw_aspen_field_without_explicit_unit_is_skipped_locally(self) -> None:
        payload = json.loads(json.dumps(self.sample))
        payload["blocks"][0]["QCALC"] = 1000
        with workspace_temporary_directory() as directory:
            path = Path(directory) / "missing_unit.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = adapter.derive_bundle(payload, path)
        self.assertEqual(result["status"], "DERIVED")
        self.assertTrue(any(
            item["code"] == "MISSING_EXPLICIT_ASPEN_UNIT"
            for item in result["normalization_diagnostics"]
        ))
        self.assertEqual(result["equipment_count"], 1)

    def test_common_real_aspen_units_and_ceff_fraction_are_normalized_with_lineage(self) -> None:
        payload = json.loads(json.dumps(self.sample))
        inlet = payload["streams"][0]
        inlet.pop("volumetric_flow_m3_h")
        inlet.pop("liquid_volumetric_flow_m3_h")
        inlet["VOLFLMX"] = 600.0
        inlet["VOLFLMX_LIQ"] = 600.0
        for stream in payload["streams"]:
            stream["density_kg_m3"] = 0.85

        block = payload["blocks"][0]
        block.pop("efficiency_percent")
        block.update({
            "QCALC": 1000.0,
            "HEAD_CAL": 1163.65253,
            "CEFF": 0.723,
            "DELP_CAL": 0.138,
        })
        payload["units"] = {
            "stream.VOLFLMX": "l/min",
            "stream.VOLFLMX_LIQ": "L/min",
            "stream.density_kg_m3": "gm/cc",
            "block.QCALC": "cal/sec",
            "block.HEAD_CAL": "m-kgf/kg",
            "block.CEFF": "",
            "block.DELP_CAL": "bar",
        }

        with workspace_temporary_directory() as directory:
            path = Path(directory) / "real_aspen_units.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = adapter.derive_bundle(payload, path)

        self.assertEqual(result["status"], "DERIVED", result.get("errors"))
        equipment = result["equipment"][0]
        normalized = equipment["canonical_match_input"]
        self.assertAlmostEqual(normalized["flow_m3_h"], 36.0, places=12)
        self.assertAlmostEqual(normalized["density_kg_m3"], 850.0, places=12)
        self.assertAlmostEqual(normalized["heat_duty_kw"], 4.184, places=12)
        self.assertAlmostEqual(normalized["head_m"], 1163.65253, places=12)
        self.assertAlmostEqual(normalized["efficiency_percent"], 72.3, places=12)
        self.assertAlmostEqual(normalized["pressure_drop_kpa"], 13.8, places=12)

        lineage = {item["target_field"]: item for item in equipment["parameter_lineage"]}
        self.assertEqual(lineage["flow_m3_h"]["transform"], "V_m3_per_h=V_L_per_min×0.06")
        self.assertEqual(
            lineage["density_kg_m3"]["transform"],
            "rho_kg_per_m3=rho_g_per_cm3×1000",
        )
        self.assertEqual(lineage["heat_duty_kw"]["transform"], "Q_kW=Q_cal_per_s×0.004184")
        self.assertEqual(
            lineage["head_m"]["transform"],
            "H_m=E_mkgf_per_kg×9.80665/9.80665",
        )
        self.assertEqual(lineage["pressure_drop_kpa"]["transform"], "dP_kPa=dP_bar×100")
        self.assertEqual(lineage["efficiency_percent"]["source_field"], "CEFF")
        self.assertEqual(lineage["efficiency_percent"]["transform"], "eta_percent=eta_fraction×100")
        self.assertIn("eta_fraction", lineage["efficiency_percent"]["equation_chain"])
        self.assertIn("0.723×100", lineage["efficiency_percent"]["equation_chain"])

    def test_supported_calorie_aliases_have_explicit_physical_conversions(self) -> None:
        cases = (
            (1000.0, "cal/sec", 4.184),
            (1000.0, "cal/s", 4.184),
            (3600.0, "kcal/h", 4.184),
            (1.0, "Gcal/hr", 1162.2222222222222),
        )
        for value, source_unit, expected in cases:
            with self.subTest(source_unit=source_unit):
                converted, transform = adapter.convert(value, source_unit, "kW")
                self.assertAlmostEqual(converted, expected, places=12)
                self.assertNotEqual(transform, "identity")

        converted, transform = adapter.convert(12.5, "meter", "m")
        self.assertEqual(converted, 12.5)
        self.assertEqual(transform, "identity")

        converted, transform = adapter.convert(1.0, "atm", "kPa")
        self.assertAlmostEqual(converted, 101.325, places=12)
        self.assertEqual(transform, "dP_kPa=dP_atm×101.325")

        converted, transform = adapter.convert(1.0, "atm", "MPa")
        self.assertAlmostEqual(converted, 0.101325, places=12)
        self.assertEqual(transform, "P_MPa=P_atm×0.101325")

    def test_supported_aspen_density_aliases_convert_to_kg_m3(self) -> None:
        for source_unit in ("gm/cc", "g/cm3", "g/cm^3"):
            with self.subTest(source_unit=source_unit):
                converted, transform = adapter.convert(0.85, source_unit, "kg/m3")
                self.assertAlmostEqual(converted, 850.0, places=12)
                self.assertEqual(transform, "rho_kg_per_m3=rho_g_per_cm3×1000")

    def test_same_case_aspen_unit_symbols_are_normalized_without_defaults(self) -> None:
        """Symbols are exact UnitString values observed on the real V14 case."""
        identity_cases = (
            (12.5, "cum/hr", "m3/h"),
            (850.0, "kg/cum", "kg/m3"),
            (3.2, "sqm", "m2"),
            (4.7, "cum", "m3"),
        )
        for value, source_unit, target_unit in identity_cases:
            with self.subTest(source_unit=source_unit):
                converted, transform = adapter.convert(value, source_unit, target_unit)
                self.assertEqual(converted, value)
                self.assertEqual(transform, "identity")

        converted, transform = adapter.convert(1000.0, "Watt", "kW")
        self.assertAlmostEqual(converted, 1.0, places=12)
        self.assertEqual(transform, "Q_kW=Q_W×0.001")

        converted, transform = adapter.convert(98.0665, "J/kg", "m")
        self.assertAlmostEqual(converted, 10.0, places=12)
        self.assertEqual(transform, "H_m=E_J_per_kg/9.80665")

    def test_exact_simulation_logic_blocks_are_not_forced_into_equipment_models(self) -> None:
        for block_type in ("FSPLIT", "MIXER", "HIERARCHY"):
            with self.subTest(block_type=block_type):
                payload = json.loads(json.dumps(self.sample))
                payload["case"]["run_status_evidence_path"] = str(
                    adapter.PACKAGE_ROOT / "data" / "aspen_run_status_clean_sample.json"
                )
                payload["blocks"][0]["block_type"] = block_type
                payload["blocks"][0].pop("efficiency_percent", None)
                payload["equipment_map"][0]["process_function"] = "simulation topology logic"
                with workspace_temporary_directory() as directory:
                    path = Path(directory) / f"logic_{block_type}.json"
                    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
                    result = adapter.derive_bundle(payload, path)

                self.assertEqual(result["status"], "DERIVED")
                self.assertEqual(result["formal_use_gate"], "ELIGIBLE_AS_PROCESS_BASIS")
                self.assertFalse(any(
                    item.get("code") == "EQUIPMENT_MATCH_NOT_CLOSED"
                    for item in result["formal_use_blockers"]
                ))
                equipment = result["equipment"][0]
                self.assertEqual(equipment["canonical_match_input"]["aspen_block_type"], block_type)
                self.assertEqual(equipment["match_result"]["status"], "NOT_APPLICABLE")
                self.assertEqual(
                    equipment["match_result"]["status_reason"],
                    "NOT_APPLICABLE_SIMULATION_LOGIC_NODE",
                )
                self.assertEqual(equipment["match_result"]["model_recommendation"]["candidates"], [])
                self.assertIsNone(equipment["match_result"]["model_decision"]["candidate_model"])
                applicability = equipment["equipment_applicability"]
                self.assertFalse(applicability["independent_equipment_model_applicable_by_default"])
                self.assertFalse(applicability["physical_equipment_or_model_inferred"])
                self.assertTrue(applicability["pfd_node_retained"])
                self.assertTrue(applicability["user_type_override_allowed"])
                self.assertEqual(equipment["connectivity"]["inlet_streams"], ["S-IN"])
                self.assertEqual(equipment["connectivity"]["outlet_streams"], ["S-OUT"])

    def test_nonlogic_unclosed_block_still_blocks_formal_equipment_gate(self) -> None:
        payload = json.loads(json.dumps(self.sample))
        payload["blocks"].append({
            "block_id": "U-LOGIC-LIKE",
            "block_type": "USER2",
            "inlet_streams": [],
            "outlet_streams": [],
            "block_status": 0,
        })
        payload["equipment_map"].append({
            "block_id": "U-LOGIC-LIKE",
            "equipment_tag": "U-LOGIC-LIKE",
            "process_function": "unresolved user block",
        })
        with workspace_temporary_directory() as directory:
            path = Path(directory) / "nonlogic_unclosed.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = adapter.derive_bundle(payload, path)

        self.assertEqual(result["formal_use_gate"], "PROVISIONAL_NOT_FORMAL_PROCESS_BASIS")
        blocker = next(
            item for item in result["formal_use_blockers"]
            if item.get("code") == "EQUIPMENT_MATCH_NOT_CLOSED"
        )
        self.assertEqual(blocker["equipment"][0]["aspen_block_id"], "U-LOGIC-LIKE")
        self.assertEqual(blocker["equipment"][0]["match_status"], "BLOCKED_MISSING_DECISIVE_IDENTITY")

    def test_unknown_raw_aspen_unit_is_ignored_without_discarding_equipment(self) -> None:
        payload = json.loads(json.dumps(self.sample))
        payload["blocks"][0]["QCALC"] = 1.0
        payload["units"] = {"block.QCALC": "energy-widget/fortnight"}
        with workspace_temporary_directory() as directory:
            path = Path(directory) / "unknown_unit.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = adapter.derive_bundle(payload, path)
        self.assertEqual(result["status"], "DERIVED")
        self.assertEqual(result["equipment_count"], 1)
        unsupported = [
            item for item in result["normalization_diagnostics"]
            if item["code"] == "UNSUPPORTED_ASPEN_UNIT"
        ]
        self.assertTrue(unsupported)
        self.assertIn("energy-widget/fortnight", unsupported[0]["detail"])
        self.assertEqual(unsupported[0]["status"], "IGNORED_FIELD_UNAVAILABLE")
        self.assertNotIn("heat_duty_kw", result["equipment"][0]["canonical_match_input"])

    def test_extreme_aspen_numeric_sentinels_are_isolated_without_losing_candidate(self) -> None:
        payload = json.loads(json.dumps(self.sample))
        for stream in payload["streams"]:
            stream["mass_flow_kg_h"] = 3.8336983e21
            stream["volumetric_flow_m3_h"] = 2.35989128e21
            stream["liquid_volumetric_flow_m3_h"] = 2.35989128e21
        payload["blocks"][0]["heat_duty_kw"] = -4.3846002528888888e20
        payload["blocks"][0]["heat_transfer_area_m2"] = 2.59344323e14

        with workspace_temporary_directory() as directory:
            path = Path(directory) / "extreme_numeric_sentinels.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = adapter.derive_bundle(payload, path)

        self.assertEqual(result["status"], "DERIVED", result.get("errors"))
        diagnostics = [
            item for item in result["normalization_diagnostics"]
            if item["code"] == "ASPEN_VALUE_OUTSIDE_HARD_SANITY_RANGE"
        ]
        self.assertGreaterEqual(len(diagnostics), 8)
        equipment = result["equipment"][0]
        canonical = equipment["canonical_match_input"]
        for field in ("flow_m3_h", "mass_flow_kg_h", "heat_duty_kw", "heat_transfer_area_m2"):
            self.assertNotIn(field, canonical)
        self.assertTrue(equipment["ignored_input_diagnostics"])
        candidates = equipment["match_result"]["model_recommendation"]["candidates"]
        self.assertTrue(candidates)
        designation = candidates[0]["designation"]
        self.assertNotIn("e+20", designation.casefold())
        self.assertNotIn("e+21", designation.casefold())
        self.assertNotIn("e+14", designation.casefold())

    def test_mass_volume_density_order_of_magnitude_conflict_is_local_to_density(self) -> None:
        payload = json.loads(json.dumps(self.sample))
        payload["streams"][0]["density_kg_m3"] = 1.0

        with workspace_temporary_directory() as directory:
            path = Path(directory) / "mass_volume_density_conflict.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = adapter.derive_bundle(payload, path)

        self.assertEqual(result["status"], "DERIVED", result.get("errors"))
        diagnostic = next(
            item for item in result["normalization_diagnostics"]
            if item["code"] == "ASPEN_MASS_VOLUME_DENSITY_INCONSISTENT"
        )
        self.assertEqual(diagnostic["canonical_field"], "density_kg_m3")
        self.assertAlmostEqual(diagnostic["implied_density_kg_m3"], 850.0)
        canonical = result["equipment"][0]["canonical_match_input"]
        self.assertNotIn("density_kg_m3", canonical)
        self.assertEqual(canonical["flow_m3_h"], 36.0)
        self.assertEqual(canonical["mass_flow_kg_h"], 30600.0)
        self.assertTrue(result["equipment"][0]["match_result"]["model_recommendation"]["candidates"])

    def test_unknown_density_unit_is_local_to_dependent_targets(self) -> None:
        payload = json.loads(json.dumps(self.sample))
        payload["units"] = {"stream.density_kg_m3": "density-widget/box"}
        with workspace_temporary_directory() as directory:
            path = Path(directory) / "unknown_density_unit.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = adapter.derive_bundle(payload, path)
        self.assertEqual(result["status"], "DERIVED")
        unsupported = [
            item for item in result["normalization_diagnostics"]
            if item["code"] == "UNSUPPORTED_ASPEN_UNIT" and item["field"] == "density_kg_m3"
        ]
        self.assertTrue(unsupported)
        self.assertIn("density-widget/box", unsupported[0]["detail"])
        self.assertIn("piping", result)

    def test_real_aspen_gcal_and_meter_units_do_not_block_bundle(self) -> None:
        payload = json.loads(json.dumps(self.sample))
        payload["blocks"][0]["QCALC"] = 1.5
        payload["blocks"][0]["HEAD_CAL"] = 12.0
        payload["units"] = {
            "block.QCALC": "Gcal/hr",
            "block.HEAD_CAL": "meter",
        }
        with workspace_temporary_directory() as directory:
            path = Path(directory) / "real_aspen_units.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = adapter.derive_bundle(payload, path)

        self.assertEqual(result["status"], "DERIVED")
        normalized = result["equipment"][0]["canonical_match_input"]
        self.assertAlmostEqual(normalized["heat_duty_kw"], 1743.3333333333333, places=9)
        self.assertAlmostEqual(normalized["head_m"], 12.0, places=12)
        self.assertEqual(result["normalization_diagnostic_count"], 0)

    def test_conflicting_aspen_aliases_are_not_first_value_wins(self) -> None:
        payload = json.loads(json.dumps(self.sample))
        payload["streams"][0]["pressure_mpa"] = 0.1
        with workspace_temporary_directory() as directory:
            path = Path(directory) / "conflicting_aliases.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = adapter.derive_bundle(payload, path)
        self.assertEqual(result["status"], "DERIVED")
        self.assertTrue(any(
            item["code"] == "CONFLICTING_ASPEN_ALIASES"
            for item in result["normalization_diagnostics"]
        ))
        self.assertNotIn("inlet_pressure_mpa", result["equipment"][0]["canonical_match_input"])

    def test_duplicate_or_nonobject_equipment_map_rows_block(self) -> None:
        cases = []
        duplicate = json.loads(json.dumps(self.sample))
        duplicate["equipment_map"].append(dict(duplicate["equipment_map"][0]))
        cases.append((duplicate, "DUPLICATE_EQUIPMENT_MAP_BLOCK_ID"))
        nonobject = json.loads(json.dumps(self.sample))
        nonobject["equipment_map"].append("P-101")
        cases.append((nonobject, "EQUIPMENT_MAP_ROW_NOT_OBJECT"))
        for payload, code in cases:
            with self.subTest(code=code), workspace_temporary_directory() as directory:
                path = Path(directory) / "bad_map.json"
                path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
                result = adapter.derive_bundle(payload, path)
                self.assertEqual(result["status"], "BLOCKED_INVALID_ASPEN_EXPORT")
                self.assertTrue(any(item["code"] == code for item in result["errors"]))

    def test_one_in_one_out_block_with_ambiguous_ports_is_not_formal(self) -> None:
        payload = json.loads(json.dumps(self.sample))
        payload["blocks"][0]["inlet_streams"] = ["S-IN", "S-OUT"]
        with workspace_temporary_directory() as directory:
            path = Path(directory) / "ambiguous_ports.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = adapter.derive_bundle(payload, path)
        self.assertEqual(result["formal_use_gate"], "PROVISIONAL_NOT_FORMAL_PROCESS_BASIS")
        self.assertEqual(result["equipment"][0]["aspen_mapping_status"], "PROVISIONAL_AMBIGUOUS_CONNECTION")

    def test_zero_heater_duty_conflicting_with_stream_delta_t_uses_visible_energy_fallback(self) -> None:
        payload = json.loads(json.dumps(self.sample))
        payload["blocks"][0] = {
            "block_id": "H-101",
            "block_type": "HEATER",
            "inlet_streams": ["S-IN"],
            "outlet_streams": ["S-OUT"],
            "heat_duty_kw": 0.0,
        }
        payload["equipment_map"][0].update({
            "block_id": "H-101",
            "equipment_tag": "H-101",
            "equipment_family": "family_other_heat_exchanger",
        })
        payload["streams"][0]["temperature_c"] = 20.0
        payload["streams"][1]["temperature_c"] = 70.0
        payload["streams"][0]["mass_flow_kg_h"] = 3600.0
        payload["streams"][1]["mass_flow_kg_h"] = 3600.0

        with workspace_temporary_directory() as directory:
            path = Path(directory) / "zero_duty_conflict.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = adapter.derive_bundle(payload, path)

        equipment = result["equipment"][0]
        self.assertNotEqual(equipment["canonical_match_input"].get("heat_duty_kw"), 0.0)
        self.assertEqual(equipment["canonical_match_input"]["outlet_temperature_c"], 70.0)
        self.assertTrue(any(
            item["code"] == "ZERO_ASPEN_DUTY_CONFLICTS_WITH_STREAM_TEMPERATURE_CHANGE"
            for item in equipment["adapter_blockers"]
        ))
        self.assertGreater(equipment["match_result"]["derived_parameters"]["heat_transfer_area_m2"], 0.0)
        self.assertEqual(result["formal_use_gate"], "PROVISIONAL_NOT_FORMAL_PROCESS_BASIS")

    def test_same_file_has_byte_stable_result(self) -> None:
        left = adapter.derive_bundle(self.sample, self.sample_path)
        right = adapter.derive_bundle(self.sample, self.sample_path)
        self.assertEqual(left, right)

    def test_every_equipment_and_piping_record_has_program_derived_service_profile(self) -> None:
        result = adapter.derive_bundle(self.sample, self.sample_path)
        equipment_profile = result["equipment"][0]["service_profile"]
        self.assertEqual(equipment_profile["schema"], "equipment-service-profile-v1")
        self.assertTrue(equipment_profile["runtime_contract"]["labels_rebuilt_from_raw_input"])
        self.assertFalse(equipment_profile["runtime_contract"]["vision_capability"])
        labels = {item["label_id"]: item for item in equipment_profile["service_labels"]}
        self.assertEqual(labels["module.intent"]["value"], "liquid_pressure_increase")
        self.assertIn("process.operating_pressure_max", labels)
        self.assertTrue(result["piping"])
        self.assertTrue(all(item["service_profile"]["schema"] == "equipment-service-profile-v1" for item in result["piping"]))

    def test_bad_composition_is_local_and_cannot_create_hazard_labels(self) -> None:
        payload = json.loads(json.dumps(self.sample))
        payload["streams"][0]["composition"] = [
            {"component_id": "A", "fraction": 0.6, "basis": "mole_fraction", "source_path": "fixture:A"},
            {"component_id": "B", "fraction": 0.2, "basis": "mole_fraction", "source_path": "fixture:B"},
        ]
        with workspace_temporary_directory() as directory:
            path = Path(directory) / "bad_composition.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = adapter.derive_bundle(payload, path)
        self.assertEqual(result["status"], "DERIVED")
        self.assertTrue(any(item["code"] == "ASPEN_COMPOSITION_NOT_CLOSED" for item in result["normalization_diagnostics"]))
        profile = result["equipment"][0]["service_profile"]
        labels = {item["label_id"] for item in profile["service_labels"]}
        self.assertNotIn("safety.flammable", labels)
        self.assertIn("safety.flammable", {item["label_id"] for item in profile["unknown_labels"]})

    def test_in_memory_bundle_must_equal_the_hashed_source_file(self) -> None:
        mutated = json.loads(json.dumps(self.sample))
        mutated["streams"][0]["pressure_bar"] = 9.9
        result = adapter.derive_bundle(mutated, self.sample_path)
        self.assertEqual(result["status"], "BLOCKED_SOURCE_BUNDLE_CONTENT_MISMATCH")
        self.assertTrue(any(item["code"] == "SOURCE_BUNDLE_CONTENT_MISMATCH" for item in result["errors"]))

    def test_adapter_has_no_llm_or_network_dependency(self) -> None:
        source = Path(adapter.__file__).read_text(encoding="utf-8")
        for forbidden in ("import openai", "from openai", "import requests", "urllib.request", "httpx"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
