from __future__ import annotations

import copy
import unittest

import equipment_service_profile as service_profile


class EquipmentServiceProfileTests(unittest.TestCase):
    def test_aspen_profile_derives_boundary_envelope_task_and_phase(self) -> None:
        streams = {
            "S-IN": {
                "stream_id": "S-IN",
                "stream_record_type": "MATERIAL",
                "temperature_c": 25.0,
                "pressure_mpa": 0.2,
                "vapor_fraction": 0.0,
                "phase": "liquid",
                "phase_origin": "EXACT_DERIVATION_FROM_VFRAC_OUT",
                "composition": [
                    {"component_id": "A", "fraction": 0.7, "basis": "mole_fraction", "source_path": "aspen:A"},
                    {"component_id": "B", "fraction": 0.3, "basis": "mole_fraction", "source_path": "aspen:B"},
                ],
                "_sources": {
                    "temperature_c": {"source_field": "TEMP_OUT", "source_path": "aspen:S-IN:TEMP_OUT"},
                    "pressure_mpa": {"source_field": "PRES_OUT", "source_path": "aspen:S-IN:PRES_OUT"},
                    "vapor_fraction": {"source_field": "VFRAC_OUT", "source_path": "aspen:S-IN:VFRAC_OUT"},
                },
            },
            "S-OUT": {
                "stream_id": "S-OUT",
                "stream_record_type": "MATERIAL",
                "temperature_c": 31.0,
                "pressure_mpa": 0.8,
                "vapor_fraction": 0.0,
                "phase": "liquid",
                "phase_origin": "EXACT_DERIVATION_FROM_VFRAC_OUT",
                "_sources": {
                    "temperature_c": {"source_field": "TEMP_OUT", "source_path": "aspen:S-OUT:TEMP_OUT"},
                    "pressure_mpa": {"source_field": "PRES_OUT", "source_path": "aspen:S-OUT:PRES_OUT"},
                    "vapor_fraction": {"source_field": "VFRAC_OUT", "source_path": "aspen:S-OUT:VFRAC_OUT"},
                },
            },
        }
        profile = service_profile.build_aspen_service_profile(
            equipment_id="P-101",
            equipment_family="family_pump",
            block={"block_id": "P-101", "block_type": "PUMP", "inlet_streams": ["S-IN"], "outlet_streams": ["S-OUT"]},
            streams=streams,
            source_bundle_sha256="A" * 64,
        )
        labels = {item["label_id"]: item for item in profile["service_labels"]}
        self.assertEqual(labels["module.intent"]["value"], "liquid_pressure_increase")
        self.assertEqual(labels["process.operating_pressure_min"]["value"], 0.2)
        self.assertEqual(labels["process.operating_pressure_max"]["value"], 0.8)
        self.assertEqual(labels["observed.operation.pressure_direction"]["value"], "increase")
        self.assertEqual(labels["process.phase_set"]["value"], ["liquid"])
        self.assertEqual(labels["composition.component_ids"]["value"], ["A", "B"])
        unknown = {item["label_id"] for item in profile["unknown_labels"]}
        self.assertIn("safety.flammable", unknown)
        self.assertTrue(any(item["code"] == "PROPERTY_LABELS_NOT_GUESSED_FROM_COMPONENT_NAMES" for item in profile["diagnostics"]))

    def test_direct_labels_are_ignored_and_recorded(self) -> None:
        profile = service_profile.build_manual_service_profile({
            "aspen_block_type": "PUMP",
            "phase": "liquid",
            "inlet_pressure_mpa": 0.1,
            "outlet_pressure_mpa": 0.5,
            "service_labels": ["safety.flammable"],
            "flammable": True,
        })
        labels = {item["label_id"] for item in profile["service_labels"]}
        self.assertNotIn("safety.flammable", labels)
        diagnostic = next(item for item in profile["diagnostics"] if item["code"] == "DIRECT_SERVICE_LABEL_INPUT_IGNORED")
        self.assertIn("flammable", diagnostic["detail"])
        self.assertIn("service_labels", diagnostic["detail"])

    def test_manual_raw_fields_still_create_program_labels(self) -> None:
        profile = service_profile.build_manual_service_profile({
            "aspen_block_type": "VALVE",
            "phase": "vapor",
            "inlet_pressure_mpa": 1.2,
            "outlet_pressure_mpa": 0.3,
            "inlet_temperature_c": 120.0,
            "outlet_temperature_c": 85.0,
        })
        labels = {item["label_id"]: item for item in profile["service_labels"]}
        self.assertEqual(labels["module.intent"]["value"], "pressure_reduction")
        self.assertEqual(labels["observed.operation.pressure_direction"]["value"], "decrease")
        self.assertTrue(all(item["label_origin"] != "REGISTERED_PROVISIONAL_FALLBACK" for item in labels.values()))

    def test_profile_is_deterministic_and_input_sensitive(self) -> None:
        raw = {"aspen_block_type": "HEATER", "phase": "liquid", "temperature_c": 40.0}
        left = service_profile.build_manual_service_profile(raw)
        right = service_profile.build_manual_service_profile(copy.deepcopy(raw))
        self.assertEqual(left, right)
        changed = service_profile.build_manual_service_profile({**raw, "temperature_c": 41.0})
        self.assertNotEqual(left["profile_context_sha256"], changed["profile_context_sha256"])

    def test_numeric_phase_fraction_overrides_conflicting_free_text_phase(self) -> None:
        profile = service_profile.build_aspen_service_profile(
            equipment_id="E-2",
            equipment_family="family_heat_exchanger",
            block={
                "block_id": "E-2",
                "block_type": "HEATER",
                "inlet_streams": ["S-1"],
                "outlet_streams": [],
            },
            streams={
                "S-1": {
                    "stream_id": "S-1",
                    "stream_record_type": "MATERIAL",
                    "phase": "vapor",
                    "vapor_fraction": 0.0,
                    "solid_fraction": 0.0,
                    "_sources": {},
                }
            },
            source_bundle_sha256="A" * 64,
        )
        labels = {item["label_id"]: item for item in profile["service_labels"]}
        self.assertEqual(labels["process.stream_phase.inlet.s_1"]["value"], "liquid")
        self.assertEqual(labels["process.phase_set"]["value"], ["liquid"])

    def test_only_connection_join_accepted_property_facts_replace_unknown_labels(self) -> None:
        profile = service_profile.build_manual_service_profile({
            "equipment_tag": "P-1",
            "temperature_c": 25.0,
        })
        enriched = service_profile.enrich_with_connection_property_facts(profile, {
            "schema": "equipment-connection-selection-package-v1",
            "deterministic": True,
            "source_export_sha256": profile["source_bundle_sha256"],
            "connections": [{
                "connection_id": "P-1:INLET:1:S-1",
                "accepted_property_facts": [{
                    "fact": "toxicity",
                    "value": "high",
                    "source_id": "FACT-1",
                    "source_asset_sha256": "A" * 64,
                    "source_record_sha256": "B" * 64,
                }],
            }],
        })
        labels = {item["label_id"]: item for item in enriched["service_labels"]}
        self.assertEqual(labels["safety.toxic"]["value"], "high")
        self.assertEqual(labels["safety.toxic"]["label_origin"], "PROPERTY_GRAPH_JOIN")
        self.assertNotIn("safety.toxic", {item["label_id"] for item in enriched["unknown_labels"]})
        unchanged = service_profile.enrich_with_connection_property_facts(profile, {
            "schema": "equipment-connection-selection-package-v1",
            "deterministic": True,
            "source_export_sha256": "C" * 64,
            "connections": [],
        })
        self.assertEqual(unchanged, profile)

    def test_batchsep_has_registered_module_intent(self) -> None:
        profile = service_profile.build_aspen_service_profile(
            equipment_id="B-SEP",
            equipment_family="family_reactor_vessel_separator",
            block={"block_id": "B-SEP", "block_type": "BATCHSEP", "inlet_streams": [], "outlet_streams": []},
            streams={},
            source_bundle_sha256="D" * 64,
        )
        labels = {item["label_id"]: item for item in profile["service_labels"]}
        self.assertEqual(labels["module.intent"]["value"], "batch_separation")
        self.assertEqual(labels["module.intent"]["evidence_state"], "D")

    def test_solids_modules_have_registered_module_intents(self) -> None:
        cases = {
            "CRYSTALLIZER": "solid_crystallization",
            "FILTER": "solid_liquid_filtration",
            "DRYER": "solids_drying",
        }
        for block_type, expected_intent in cases.items():
            with self.subTest(block_type=block_type):
                profile = service_profile.build_aspen_service_profile(
                    equipment_id=f"TEST-{block_type}",
                    equipment_family=(
                        "family_reactor_vessel_separator"
                        if block_type == "CRYSTALLIZER"
                        else "family_package_equipment"
                    ),
                    block={
                        "block_id": f"TEST-{block_type}",
                        "block_type": block_type,
                        "inlet_streams": [],
                        "outlet_streams": [],
                    },
                    streams={},
                    source_bundle_sha256="E" * 64,
                )
                labels = {item["label_id"]: item for item in profile["service_labels"]}
                self.assertEqual(labels["module.intent"]["value"], expected_intent)
                self.assertEqual(labels["module.intent"]["evidence_state"], "D")
                self.assertNotIn(
                    "W_MODULE_TASK_UNREGISTERED",
                    labels["module.intent"].get("warning_codes", []),
                )

    def test_module_intent_conflict_with_observed_pressure_is_a_local_blocker(self) -> None:
        profile = service_profile.build_aspen_service_profile(
            equipment_id="P-BAD",
            equipment_family="family_pump",
            block={"block_id": "P-BAD", "block_type": "PUMP", "inlet_streams": ["IN"], "outlet_streams": ["OUT"]},
            streams={
                "IN": {"stream_id": "IN", "stream_record_type": "MATERIAL", "pressure_mpa": 2.0, "phase": "liquid", "_sources": {}},
                "OUT": {"stream_id": "OUT", "stream_record_type": "MATERIAL", "pressure_mpa": 1.0, "phase": "liquid", "_sources": {}},
            },
            source_bundle_sha256="E" * 64,
        )
        labels = {item["label_id"]: item for item in profile["service_labels"]}
        self.assertEqual(labels["module.intent"]["value"], "liquid_pressure_increase")
        self.assertEqual(labels["observed.operation.pressure_direction"]["value"], "decrease")
        conflicts = [item for item in profile["diagnostics"] if item["code"] == "MODULE_STREAM_CONDITION_CONFLICT"]
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["severity"], "local_blocker")

    def test_heater_operation_is_derived_from_temperature_delta(self) -> None:
        profile = service_profile.build_aspen_service_profile(
            equipment_id="H-1",
            equipment_family="family_other_heat_exchanger",
            block={"block_id": "H-1", "block_type": "HEATER", "inlet_streams": ["IN"], "outlet_streams": ["OUT"]},
            streams={
                "IN": {"stream_id": "IN", "stream_record_type": "MATERIAL", "temperature_c": 20.0, "phase": "liquid", "_sources": {}},
                "OUT": {"stream_id": "OUT", "stream_record_type": "MATERIAL", "temperature_c": 80.0, "phase": "liquid", "_sources": {}},
            },
            source_bundle_sha256="F" * 64,
        )
        labels = {item["label_id"]: item for item in profile["service_labels"]}
        self.assertEqual(labels["observed.operation.heat_transfer_mode"]["value"], "heating")


if __name__ == "__main__":
    unittest.main()
