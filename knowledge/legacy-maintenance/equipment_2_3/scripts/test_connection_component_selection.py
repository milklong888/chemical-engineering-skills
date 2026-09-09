from __future__ import annotations

import copy
import json
import unittest
from unittest.mock import patch

import aspen_equipment_derivation as adapter
import connection_component_selection as connection_selection
import equipment_service_profile as service_profile


class ConnectionComponentSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sample_path = adapter.PACKAGE_ROOT / "data" / "aspen_equipment_export_sample.json"
        cls.sample = json.loads(cls.sample_path.read_text(encoding="utf-8"))
        cls.result = adapter.derive_bundle(cls.sample, cls.sample_path)

    def test_every_material_connection_has_four_unique_registered_types(self) -> None:
        package = self.result["equipment"][0]["connection_component_selections"]
        self.assertEqual(package["schema"], "equipment-connection-selection-package-v1")
        self.assertEqual(package["status"], "DERIVED")
        self.assertFalse(package["llm_used"])
        self.assertFalse(package["runtime_vision"])
        self.assertFalse(package["runtime_source_access"])
        self.assertEqual(package["selector_manifest_sha256"], "7C3B3D9670941A0474B62802175F02EDD1E4AF4423A3253CA7873F48654EF8E2")
        for connection in package["connections"]:
            self.assertEqual(connection["applicability"], "APPLICABLE")
            self.assertEqual(set(connection["component_types"]), set(connection_selection.COMPONENT_FAMILIES))
            for selected in connection["component_types"].values():
                self.assertEqual(selected["terminal_count"], 1)
                self.assertTrue(selected["terminal_type"]["candidate_id"])

    def test_manual_dn_rating_facing_and_phase_bridge_into_registered_selector(self) -> None:
        raw = {
            "selected_dn": "DN50",
            "pressure_class": "PN16",
            "flange_face": "RF",
            "gasket_material": "invented foam gasket",
            "phase": "liquid",
        }
        profile = service_profile.build_manual_service_profile(
            raw,
            equipment_id="FG-MANUAL",
            equipment_family="family_flange_gasket",
        )
        package = connection_selection.build_manual_connection_component_selections(
            raw,
            match_result=self.result["equipment"][0]["match_result"],
            equipment_id="FG-MANUAL",
            service_profile=profile,
        )
        inlet = package["connections"][0]
        gasket = inlet["component_types"]["gasket_type"]
        labels = gasket["normalized_service_labels"]
        self.assertEqual(labels["system_series"], "PN")
        self.assertEqual(labels["pn"], 16.0)
        self.assertEqual(labels["dn_mm"], 50.0)
        self.assertEqual(labels["current_facing"], "RF")
        self.assertEqual(labels["phase"], "liquid")
        self.assertEqual(gasket["terminal_type"]["candidate_id"], "G_SPIRAL_D")
        ignored = {
            item["field"]: item["status"]
            for item in package["manual_mechanical_input_ledger"]
            if item.get("field")
        }
        self.assertEqual(ignored["gasket_material"], "IGNORED_UNTRUSTED_COMPONENT_PREFERENCE")

    def test_parent_equipment_terminal_selection_is_unchanged(self) -> None:
        equipment = self.result["equipment"][0]
        before = copy.deepcopy(equipment["match_result"]["model_recommendation"]["terminal_selection"])
        package = equipment["connection_component_selections"]
        after = equipment["match_result"]["model_recommendation"]["terminal_selection"]
        self.assertEqual(before, after)
        self.assertEqual(
            package["parent_selection_context_sha256"],
            equipment["match_result"]["design_parameter_package"]["selection_context"]["sha256"],
        )
        self.assertEqual(package["source_export_sha256"], self.result["source_export_sha256"])
        self.assertEqual(package["pfd_mapping_sha256"], self.result["pfd_mapping_sha256"])

    def test_direct_hazard_labels_are_ignored_and_do_not_change_selection(self) -> None:
        equipment = self.result["equipment"][0]
        block = adapter.normalize_block(self.sample["blocks"][0], self.sample.get("units", {}))[0]
        streams = {
            item["stream_id"]: item
            for item in (
                adapter.normalize_stream(raw, self.sample.get("units", {}))[0]
                for raw in self.sample["streams"]
            )
        }
        common = {
            "block": block,
            "streams": streams,
            "match_result": equipment["match_result"],
            "source_export_sha256": self.result["source_export_sha256"],
            "pfd_mapping_sha256": self.result["pfd_mapping_sha256"],
            "endpoints": adapter.stream_endpoints([block]),
        }
        clean = connection_selection.build_aspen_connection_component_selections(**common)
        poisoned = connection_selection.build_aspen_connection_component_selections(
            **common,
            mechanical_context={"toxicity": "high", "corrosivity": "severe"},
        )
        for left, right in zip(clean["connections"], poisoned["connections"]):
            for family in connection_selection.COMPONENT_FAMILIES:
                self.assertEqual(
                    left["component_types"][family]["terminal_type"],
                    right["component_types"][family]["terminal_type"],
                )
                warning_ids = {
                    item["warning_id"]
                    for item in right["component_types"][family]["warnings"]
                }
                self.assertIn("W_DERIVED_INPUT_IGNORED", warning_ids)

    def test_component_name_or_unbound_fact_cannot_create_hazard_label(self) -> None:
        block = adapter.normalize_block(self.sample["blocks"][0], self.sample.get("units", {}))[0]
        streams = {
            item["stream_id"]: item
            for item in (
                adapter.normalize_stream(raw, self.sample.get("units", {}))[0]
                for raw in self.sample["streams"]
            )
        }
        streams["S-IN"]["composition"] = [
            {
                "component_id": "COMP-A",
                "fraction": 1.0,
                "basis": "mole_fraction",
                "source_path": "fixture:S-IN:COMP-A",
            }
        ]
        streams["S-IN"]["phase"] = "liquid"
        streams["S-IN"]["vapor_fraction"] = 0.0
        with patch.object(connection_selection, "_fact_exists_in_graph_asset", return_value=True):
            package = connection_selection.build_aspen_connection_component_selections(
                block=block,
                streams=streams,
                match_result=self.result["equipment"][0]["match_result"],
                source_export_sha256=self.result["source_export_sha256"],
                pfd_mapping_sha256=self.result["pfd_mapping_sha256"],
                endpoints=adapter.stream_endpoints([block]),
                property_evidence=[{
                    "fact": "toxicity",
                    "value": "high",
                    "source_id": "component-fact",
                    "source_asset_path": "knowledge_graph/property_registry.json",
                    "source_asset_sha256": "A" * 64,
                    "source_record_sha256": "B" * 64,
                    "qa_status": "VALIDATED",
                    "subject_scope": "component",
                    "component_id": "COMP-A",
                }],
            )
        inlet = next(item for item in package["connections"] if item["stream_id"] == "S-IN")
        self.assertEqual(inlet["rejected_property_facts"][0]["reason"], "hazard_fact_requires_exact_mixture_scope")
        for selected in inlet["component_types"].values():
            self.assertEqual(selected["normalized_service_labels"]["toxicity"], "unknown")

    def test_exact_hash_locked_mixture_fact_can_create_label(self) -> None:
        block = adapter.normalize_block(self.sample["blocks"][0], self.sample.get("units", {}))[0]
        streams = {
            item["stream_id"]: item
            for item in (
                adapter.normalize_stream(raw, self.sample.get("units", {}))[0]
                for raw in self.sample["streams"]
            )
        }
        streams["S-IN"]["composition"] = [
            {
                "component_id": "COMP-A",
                "fraction": 1.0,
                "basis": "mole_fraction",
                "source_path": "fixture:S-IN:COMP-A",
            }
        ]
        streams["S-IN"]["phase"] = "liquid"
        streams["S-IN"]["vapor_fraction"] = 0.0
        composition_sha256 = connection_selection.composition_context_sha256(streams["S-IN"])
        with patch.object(connection_selection, "_fact_exists_in_graph_asset", return_value=True):
            package = connection_selection.build_aspen_connection_component_selections(
                block=block,
                streams=streams,
                match_result=self.result["equipment"][0]["match_result"],
                source_export_sha256=self.result["source_export_sha256"],
                pfd_mapping_sha256=self.result["pfd_mapping_sha256"],
                endpoints=adapter.stream_endpoints([block]),
                property_evidence=[{
                    "fact": "toxicity",
                    "value": "high",
                    "source_id": "mixture-fact",
                    "source_asset_path": "knowledge_graph/property_registry.json",
                    "source_asset_sha256": "B" * 64,
                    "source_record_sha256": "C" * 64,
                    "qa_status": "PROMOTED",
                    "subject_scope": "mixture",
                    "stream_id": "S-IN",
                    "composition_sha256": composition_sha256,
                    "valid_phases": ["liquid"],
                }],
            )
        inlet = next(item for item in package["connections"] if item["stream_id"] == "S-IN")
        self.assertEqual(inlet["accepted_property_facts"][0]["fact"], "toxicity")
        for selected in inlet["component_types"].values():
            self.assertEqual(selected["normalized_service_labels"]["toxicity"], "high")

    def test_nonclosing_composition_cannot_bind_a_mixture_fact(self) -> None:
        block = adapter.normalize_block(self.sample["blocks"][0], self.sample.get("units", {}))[0]
        streams = {
            item["stream_id"]: item
            for item in (
                adapter.normalize_stream(raw, self.sample.get("units", {}))[0]
                for raw in self.sample["streams"]
            )
        }
        streams["S-IN"]["composition"] = [
            {"component_id": "COMP-A", "fraction": 0.8, "basis": "mole_fraction", "source_path": "fixture:A"},
            {"component_id": "COMP-B", "fraction": 0.6, "basis": "mole_fraction", "source_path": "fixture:B"},
        ]
        forged_hash = connection_selection.canonical_sha256([
            {"component_id": "COMP-A", "fraction": 0.8, "basis": "mole_fraction"},
            {"component_id": "COMP-B", "fraction": 0.6, "basis": "mole_fraction"},
        ])
        with patch.object(connection_selection, "_fact_exists_in_graph_asset", return_value=True):
            package = connection_selection.build_aspen_connection_component_selections(
                block=block,
                streams=streams,
                match_result=self.result["equipment"][0]["match_result"],
                source_export_sha256=self.result["source_export_sha256"],
                pfd_mapping_sha256=self.result["pfd_mapping_sha256"],
                endpoints=adapter.stream_endpoints([block]),
                property_evidence=[{
                    "fact": "toxicity",
                    "value": "high",
                    "source_id": "bad-mixture-fact",
                    "source_asset_path": "knowledge_graph/property_registry.json",
                    "source_asset_sha256": "D" * 64,
                    "source_record_sha256": "E" * 64,
                    "qa_status": "VALIDATED",
                    "subject_scope": "mixture",
                    "stream_id": "S-IN",
                    "composition_sha256": forged_hash,
                }],
            )
        inlet = next(item for item in package["connections"] if item["stream_id"] == "S-IN")
        self.assertEqual(connection_selection.composition_context_sha256(streams["S-IN"]), "")
        self.assertEqual(inlet["rejected_property_facts"][0]["reason"], "mixture_composition_not_closed")

    def test_mixture_fact_phase_scope_must_cover_current_stream_phase(self) -> None:
        block = adapter.normalize_block(self.sample["blocks"][0], self.sample.get("units", {}))[0]
        streams = {
            item["stream_id"]: item
            for item in (
                adapter.normalize_stream(raw, self.sample.get("units", {}))[0]
                for raw in self.sample["streams"]
            )
        }
        streams["S-IN"].update({
            "composition": [{
                "component_id": "COMP-A",
                "fraction": 1.0,
                "basis": "mole_fraction",
                "source_path": "fixture:S-IN:COMP-A",
            }],
            "phase": "vapor",
            "vapor_fraction": 1.0,
        })
        composition_sha256 = connection_selection.composition_context_sha256(streams["S-IN"])
        with patch.object(connection_selection, "_fact_exists_in_graph_asset", return_value=True):
            package = connection_selection.build_aspen_connection_component_selections(
                block=block,
                streams=streams,
                match_result=self.result["equipment"][0]["match_result"],
                source_export_sha256=self.result["source_export_sha256"],
                pfd_mapping_sha256=self.result["pfd_mapping_sha256"],
                endpoints=adapter.stream_endpoints([block]),
                property_evidence=[{
                    "fact": "toxicity",
                    "value": "high",
                    "source_id": "liquid-only-fact",
                    "source_asset_path": "knowledge_graph/property_registry.json",
                    "source_asset_sha256": "F" * 64,
                    "source_record_sha256": "A" * 64,
                    "qa_status": "VALIDATED",
                    "subject_scope": "mixture",
                    "stream_id": "S-IN",
                    "composition_sha256": composition_sha256,
                    "valid_phases": ["liquid"],
                }],
            )
        inlet = next(item for item in package["connections"] if item["stream_id"] == "S-IN")
        self.assertEqual(inlet["rejected_property_facts"][0]["reason"], "outside_phase_applicability")

    def test_fact_with_temperature_range_requires_current_stream_temperature(self) -> None:
        block = adapter.normalize_block(self.sample["blocks"][0], self.sample.get("units", {}))[0]
        streams = {
            item["stream_id"]: item
            for item in (
                adapter.normalize_stream(raw, self.sample.get("units", {}))[0]
                for raw in self.sample["streams"]
            )
        }
        streams["S-IN"].update({
            "composition": [{
                "component_id": "COMP-A",
                "fraction": 1.0,
                "basis": "mole_fraction",
                "source_path": "fixture:S-IN:COMP-A",
            }],
            "phase": "liquid",
            "vapor_fraction": 0.0,
        })
        streams["S-IN"].pop("temperature_c", None)
        composition_sha256 = connection_selection.composition_context_sha256(streams["S-IN"])
        with patch.object(connection_selection, "_fact_exists_in_graph_asset", return_value=True):
            package = connection_selection.build_aspen_connection_component_selections(
                block=block,
                streams=streams,
                match_result=self.result["equipment"][0]["match_result"],
                source_export_sha256=self.result["source_export_sha256"],
                pfd_mapping_sha256=self.result["pfd_mapping_sha256"],
                endpoints=adapter.stream_endpoints([block]),
                property_evidence=[{
                    "fact": "toxicity",
                    "value": "high",
                    "source_id": "bounded-fact",
                    "source_asset_path": "knowledge_graph/property_registry.json",
                    "source_asset_sha256": "B" * 64,
                    "source_record_sha256": "C" * 64,
                    "qa_status": "VALIDATED",
                    "subject_scope": "mixture",
                    "stream_id": "S-IN",
                    "composition_sha256": composition_sha256,
                    "valid_phases": ["liquid"],
                    "valid_temperature_min_c": -20.0,
                    "valid_temperature_max_c": 120.0,
                }],
            )
        inlet = next(item for item in package["connections"] if item["stream_id"] == "S-IN")
        self.assertEqual(
            inlet["rejected_property_facts"][0]["reason"],
            "current_temperature_missing_for_fact_range",
        )

    def test_pressure_range_fact_requires_matching_pressure_basis(self) -> None:
        block = adapter.normalize_block(self.sample["blocks"][0], self.sample.get("units", {}))[0]
        streams = {
            item["stream_id"]: item
            for item in (
                adapter.normalize_stream(raw, self.sample.get("units", {}))[0]
                for raw in self.sample["streams"]
            )
        }
        streams["S-IN"].update({
            "composition": [{
                "component_id": "COMP-A",
                "fraction": 1.0,
                "basis": "mole_fraction",
                "source_path": "fixture:S-IN:COMP-A",
            }],
            "phase": "liquid",
            "vapor_fraction": 0.0,
            "pressure_mpa": 0.4,
        })
        composition_sha256 = connection_selection.composition_context_sha256(streams["S-IN"])
        with patch.object(connection_selection, "_fact_exists_in_graph_asset", return_value=True):
            package = connection_selection.build_aspen_connection_component_selections(
                block=block,
                streams=streams,
                match_result=self.result["equipment"][0]["match_result"],
                source_export_sha256=self.result["source_export_sha256"],
                pfd_mapping_sha256=self.result["pfd_mapping_sha256"],
                endpoints=adapter.stream_endpoints([block]),
                pressure_basis="gauge",
                property_evidence=[{
                    "fact": "toxicity",
                    "value": "high",
                    "source_id": "absolute-pressure-fact",
                    "source_asset_path": "knowledge_graph/property_registry.json",
                    "source_asset_sha256": "D" * 64,
                    "source_record_sha256": "E" * 64,
                    "qa_status": "VALIDATED",
                    "subject_scope": "mixture",
                    "stream_id": "S-IN",
                    "composition_sha256": composition_sha256,
                    "valid_phases": ["liquid"],
                    "valid_pressure_min_mpa": 0.1,
                    "valid_pressure_max_mpa": 1.0,
                    "pressure_basis": "absolute",
                }],
            )
        inlet = next(item for item in package["connections"] if item["stream_id"] == "S-IN")
        self.assertEqual(inlet["rejected_property_facts"][0]["reason"], "pressure_basis_mismatch")

    def test_mixture_hazard_fact_requires_explicit_phase_applicability(self) -> None:
        block = adapter.normalize_block(self.sample["blocks"][0], self.sample.get("units", {}))[0]
        streams = {
            item["stream_id"]: item
            for item in (
                adapter.normalize_stream(raw, self.sample.get("units", {}))[0]
                for raw in self.sample["streams"]
            )
        }
        streams["S-IN"].update({
            "composition": [{
                "component_id": "COMP-A",
                "fraction": 1.0,
                "basis": "mole_fraction",
                "source_path": "fixture:S-IN:COMP-A",
            }],
            "phase": "liquid",
            "vapor_fraction": 0.0,
        })
        composition_sha256 = connection_selection.composition_context_sha256(streams["S-IN"])
        with patch.object(connection_selection, "_fact_exists_in_graph_asset", return_value=True):
            package = connection_selection.build_aspen_connection_component_selections(
                block=block,
                streams=streams,
                match_result=self.result["equipment"][0]["match_result"],
                source_export_sha256=self.result["source_export_sha256"],
                pfd_mapping_sha256=self.result["pfd_mapping_sha256"],
                endpoints=adapter.stream_endpoints([block]),
                property_evidence=[{
                    "fact": "toxicity",
                    "value": "high",
                    "source_id": "phase-free-fact",
                    "source_asset_path": "knowledge_graph/property_registry.json",
                    "source_asset_sha256": "A" * 64,
                    "source_record_sha256": "B" * 64,
                    "qa_status": "VALIDATED",
                    "subject_scope": "mixture",
                    "stream_id": "S-IN",
                    "composition_sha256": composition_sha256,
                }],
            )
        inlet = next(item for item in package["connections"] if item["stream_id"] == "S-IN")
        self.assertEqual(
            inlet["rejected_property_facts"][0]["reason"],
            "fact_phase_applicability_missing",
        )

    def test_forged_source_id_and_hash_text_is_rejected(self) -> None:
        block = adapter.normalize_block(self.sample["blocks"][0], self.sample.get("units", {}))[0]
        streams = {
            item["stream_id"]: item
            for item in (
                adapter.normalize_stream(raw, self.sample.get("units", {}))[0]
                for raw in self.sample["streams"]
            )
        }
        package = connection_selection.build_aspen_connection_component_selections(
            block=block,
            streams=streams,
            match_result=self.result["equipment"][0]["match_result"],
            source_export_sha256=self.result["source_export_sha256"],
            pfd_mapping_sha256=self.result["pfd_mapping_sha256"],
            endpoints=adapter.stream_endpoints([block]),
            property_evidence=[{
                "fact": "toxicity",
                "value": "high",
                "source_id": "invented-by-caller",
                "source_asset_path": "knowledge_graph/does-not-exist.json",
                "source_asset_sha256": "A" * 64,
                "source_record_sha256": "B" * 64,
                "qa_status": "PROMOTED",
                "subject_scope": "project_requirement",
                "block_id": block["block_id"],
            }],
        )
        inlet = next(item for item in package["connections"] if item["stream_id"] == "S-IN")
        self.assertEqual(inlet["rejected_property_facts"][0]["reason"], "source_fact_not_in_verified_graph_asset")
        self.assertTrue(all(
            selected["normalized_service_labels"]["toxicity"] == "unknown"
            for selected in inlet["component_types"].values()
        ))

    def test_project_requirement_cannot_replace_mixture_hazard_evidence(self) -> None:
        block = adapter.normalize_block(self.sample["blocks"][0], self.sample.get("units", {}))[0]
        streams = {
            item["stream_id"]: item
            for item in (
                adapter.normalize_stream(raw, self.sample.get("units", {}))[0]
                for raw in self.sample["streams"]
            )
        }
        with patch.object(connection_selection, "_fact_exists_in_graph_asset", return_value=True):
            package = connection_selection.build_aspen_connection_component_selections(
                block=block,
                streams=streams,
                match_result=self.result["equipment"][0]["match_result"],
                source_export_sha256=self.result["source_export_sha256"],
                pfd_mapping_sha256=self.result["pfd_mapping_sha256"],
                endpoints=adapter.stream_endpoints([block]),
                property_evidence=[{
                    "fact": "flammability",
                    "value": "highly_flammable",
                    "source_id": "project-text",
                    "source_asset_path": "knowledge_graph/property_registry.json",
                    "source_asset_sha256": "A" * 64,
                    "source_record_sha256": "B" * 64,
                    "qa_status": "VALIDATED",
                    "subject_scope": "project_requirement",
                    "block_id": block["block_id"],
                }],
            )
        inlet = next(item for item in package["connections"] if item["stream_id"] == "S-IN")
        self.assertEqual(inlet["rejected_property_facts"][0]["reason"], "hazard_fact_requires_exact_mixture_scope")
        self.assertTrue(all(
            selected["normalized_service_labels"]["flammability"] == "unknown"
            for selected in inlet["component_types"].values()
        ))

    def test_missing_rating_and_dn_default_visibly_without_stopping(self) -> None:
        package = self.result["equipment"][0]["connection_component_selections"]
        for connection in package["connections"]:
            for selected in connection["component_types"].values():
                self.assertEqual(selected["status"], "DEFAULTED_PROVISIONAL")
                warning_ids = {item["warning_id"] for item in selected["warnings"]}
                self.assertIn("W_RATING_MISSING", warning_ids)
                self.assertIn("W_DEFAULTED", warning_ids)

    def test_one_component_selector_failure_is_local(self) -> None:
        equipment = self.result["equipment"][0]
        block = adapter.normalize_block(self.sample["blocks"][0], self.sample.get("units", {}))[0]
        streams = {
            item["stream_id"]: item
            for item in (
                adapter.normalize_stream(raw, self.sample.get("units", {}))[0]
                for raw in self.sample["streams"]
            )
        }
        selector = connection_selection._selector_module()
        original = selector._select_verified

        def selective_failure(raw, **kwargs):
            if raw.get("object_family") == "gasket_type":
                raise RuntimeError("fixture-local-failure")
            return original(raw, **kwargs)

        with patch.object(selector, "_select_verified", side_effect=selective_failure):
            package = connection_selection.build_aspen_connection_component_selections(
                block=block,
                streams=streams,
                match_result=equipment["match_result"],
                source_export_sha256=self.result["source_export_sha256"],
                pfd_mapping_sha256=self.result["pfd_mapping_sha256"],
                endpoints=adapter.stream_endpoints([block]),
            )
        self.assertEqual(package["status"], "DERIVED_WITH_LOCAL_DIAGNOSTICS")
        for connection in package["connections"]:
            self.assertEqual(connection["component_types"]["gasket_type"]["status"], "LOCAL_SELECTION_FAILED")
            for family in {"flange_type", "facing", "fastener_type"}:
                self.assertEqual(connection["component_types"][family]["terminal_count"], 1)

    def test_selector_tables_are_cached_after_first_equipment_load(self) -> None:
        selector = connection_selection._selector_module()
        before = selector.read_csv.cache_info()
        adapter.derive_bundle(self.sample, self.sample_path)
        after = selector.read_csv.cache_info()
        self.assertEqual(after.misses, before.misses)
        self.assertGreater(after.hits, before.hits)

    def test_heat_work_and_logic_connections_are_local_not_applicable(self) -> None:
        block = {
            "block_id": "M-1",
            "block_type": "MIXER",
            "inlet_streams": ["S-MAT", "Q-1"],
            "outlet_streams": ["S-OUT"],
        }
        streams = {
            "S-MAT": {"stream_id": "S-MAT", "stream_record_type": "MATERIAL"},
            "Q-1": {"stream_id": "Q-1", "stream_record_type": "HEAT"},
            "S-OUT": {"stream_id": "S-OUT", "stream_record_type": "MATERIAL"},
        }
        package = connection_selection.build_aspen_connection_component_selections(
            block=block,
            streams=streams,
            match_result={},
            source_export_sha256="C" * 64,
            pfd_mapping_sha256="D" * 64,
            endpoints=adapter.stream_endpoints([block]),
        )
        self.assertEqual(package["status"], "NOT_APPLICABLE")
        self.assertTrue(all(item["applicability"] == "NOT_APPLICABLE" for item in package["connections"]))
        self.assertTrue(all(item["component_types"] == {} for item in package["connections"]))

    def test_branch_stream_ids_remain_connection_end_specific(self) -> None:
        stream = {"stream_id": "S-BRANCH", "stream_record_type": "MATERIAL", "temperature_c": 40.0, "pressure_mpa": 0.3}
        blocks = [
            {"block_id": "E-1", "block_type": "HEATER", "inlet_streams": ["S-BRANCH"], "outlet_streams": []},
            {"block_id": "V-1", "block_type": "FLASH2", "inlet_streams": ["S-BRANCH"], "outlet_streams": []},
        ]
        endpoints = adapter.stream_endpoints(blocks)
        ids = []
        for block in blocks:
            package = connection_selection.build_aspen_connection_component_selections(
                block=block,
                streams={"S-BRANCH": stream},
                match_result=self.result["equipment"][0]["match_result"],
                source_export_sha256="E" * 64,
                pfd_mapping_sha256="F" * 64,
                endpoints=endpoints,
            )
            ids.append(package["connections"][0]["connection_id"])
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids, ["E-1:INLET:1:S-BRANCH", "V-1:INLET:1:S-BRANCH"])

    def test_double_replay_is_byte_stable(self) -> None:
        left = self.result["equipment"][0]["connection_component_selections"]
        right = adapter.derive_bundle(self.sample, self.sample_path)["equipment"][0]["connection_component_selections"]
        self.assertEqual(left, right)

    def test_explicit_raw_phase_is_normalized_by_wrapper_before_selector(self) -> None:
        block = {"block_id": "H-1", "block_type": "HEATER", "inlet_streams": ["S-1"], "outlet_streams": []}
        stream = {"stream_id": "S-1", "stream_record_type": "MATERIAL", "phase": "liquid", "temperature_c": 25.0, "pressure_mpa": 0.2}
        package = connection_selection.build_aspen_connection_component_selections(
            block=block,
            streams={"S-1": stream},
            match_result=self.result["equipment"][0]["match_result"],
            source_export_sha256="A" * 64,
            pfd_mapping_sha256="B" * 64,
        )
        connection = package["connections"][0]
        self.assertEqual(connection["raw_service_context"]["normalized_phase"], "liquid")
        for selected in connection["component_types"].values():
            self.assertEqual(selected["normalized_service_labels"]["phase"], "liquid")

    def test_public_inner_selector_rejects_direct_property_evidence(self) -> None:
        selector = connection_selection._selector_module()
        selected = selector.select({
            "object_family": "gasket_type",
            "system_series": "PN",
            "property_evidence": [{"fact": "toxicity", "value": "high", "source_id": "FORGED"}],
            "phase": "liquid",
        })
        self.assertEqual(selected["normalized_service_labels"]["toxicity"], "unknown")
        self.assertEqual(selected["normalized_service_labels"]["phase"], "unknown")
        self.assertEqual(selected["rejected_property_facts"][0]["reason"], "untrusted_direct_property_evidence_input")

    def test_invalid_property_value_and_invalid_phase_are_rejected(self) -> None:
        block = {"block_id": "P-1", "block_type": "PUMP", "inlet_streams": ["S-1"], "outlet_streams": []}
        stream = {
            "stream_id": "S-1", "stream_record_type": "MATERIAL", "phase": "liquid",
            "composition": [{"component_id": "A", "fraction": 1.0, "basis": "mole_fraction"}],
        }
        composition_sha256 = connection_selection.composition_context_sha256(stream)
        common = {
            "fact": "flammability", "source_asset_path": "knowledge_graph/facts.json",
            "source_asset_sha256": "C" * 64, "qa_status": "VALIDATED",
            "subject_scope": "mixture", "stream_id": "S-1", "composition_sha256": composition_sha256,
        }
        evidence = [{
            **common,
            "fact": "flammability", "value": "banana", "source_id": "F-1",
            "source_record_sha256": "D" * 64, "qa_status": "VALIDATED",
            "valid_phases": ["liquid"],
        }, {
            **common,
            "value": "flammable", "source_id": "F-2", "source_record_sha256": "E" * 64,
            "valid_phases": ["banana"],
        }]
        with patch.object(connection_selection, "_fact_exists_in_graph_asset", side_effect=lambda fact: dict(fact)):
            package = connection_selection.build_aspen_connection_component_selections(
                block=block, streams={"S-1": stream}, match_result=self.result["equipment"][0]["match_result"],
                source_export_sha256="E" * 64, pfd_mapping_sha256="F" * 64, property_evidence=evidence,
            )
        connection = package["connections"][0]
        self.assertEqual(connection["accepted_property_facts"], [])
        self.assertEqual(
            {item["reason"] for item in connection["rejected_property_facts"]},
            {"fact_phase_applicability_invalid", "property_fact_enum_value_invalid"},
        )

    def test_conflicting_same_connection_facts_are_order_independent_and_not_promoted(self) -> None:
        block = {"block_id": "P-1", "block_type": "PUMP", "inlet_streams": ["S-1"], "outlet_streams": []}
        stream = {
            "stream_id": "S-1", "stream_record_type": "MATERIAL", "phase": "liquid",
            "composition": [{"component_id": "A", "fraction": 1.0, "basis": "mole_fraction"}],
        }
        composition_sha256 = connection_selection.composition_context_sha256(stream)
        base = {
            "fact": "flammability", "source_asset_path": "knowledge_graph/facts.json",
            "source_asset_sha256": "A" * 64, "qa_status": "VALIDATED", "subject_scope": "mixture",
            "stream_id": "S-1", "composition_sha256": composition_sha256, "valid_phases": ["liquid"],
        }
        facts = [
            {**base, "value": "nonflammable", "source_id": "F-1", "source_record_sha256": "B" * 64},
            {**base, "value": "flammable", "source_id": "F-2", "source_record_sha256": "C" * 64},
        ]
        outputs = []
        with patch.object(connection_selection, "_fact_exists_in_graph_asset", side_effect=lambda fact: dict(fact)):
            for ordered in (facts, list(reversed(facts))):
                package = connection_selection.build_aspen_connection_component_selections(
                    block=block, streams={"S-1": stream}, match_result=self.result["equipment"][0]["match_result"],
                    source_export_sha256="D" * 64, pfd_mapping_sha256="E" * 64, property_evidence=ordered,
                )
                connection = package["connections"][0]
                outputs.append((connection["accepted_property_facts"], connection["rejected_property_facts"]))
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(outputs[0][0], [])
        self.assertEqual({item["reason"] for item in outputs[0][1]}, {"property_fact_conflict"})

    def test_composition_hash_is_case_and_order_stable_but_duplicate_is_rejected(self) -> None:
        left = {"composition": [
            {"component_id": "a", "fraction": 0.4, "basis": "mole_fraction"},
            {"component_id": "B", "fraction": 0.6, "basis": "mole_fraction"},
        ]}
        right = {"composition": [
            {"component_id": "b", "fraction": 0.6, "basis": "mole_fraction"},
            {"component_id": "A", "fraction": 0.4, "basis": "mole_fraction"},
        ]}
        self.assertEqual(connection_selection.composition_context_sha256(left), connection_selection.composition_context_sha256(right))
        duplicate = {"composition": [
            {"component_id": "A", "fraction": 0.5, "basis": "mole_fraction"},
            {"component_id": "a", "fraction": 0.5, "basis": "mole_fraction"},
        ]}
        self.assertEqual(connection_selection.composition_context_sha256(duplicate), "")

    def test_connection_requirement_must_bind_exact_connection(self) -> None:
        block = {"block_id": "P-1", "block_type": "PUMP", "inlet_streams": ["S-1"], "outlet_streams": ["S-2"]}
        streams = {
            "S-1": {"stream_id": "S-1", "stream_record_type": "MATERIAL", "phase": "liquid"},
            "S-2": {"stream_id": "S-2", "stream_record_type": "MATERIAL", "phase": "liquid"},
        }
        fact = {
            "fact": "current_facing", "value": "RF", "source_id": "REQ-1",
            "source_asset_path": "knowledge_graph/facts.json", "source_asset_sha256": "A" * 64,
            "source_record_sha256": "B" * 64, "qa_status": "VALIDATED",
            "subject_scope": "connection_requirement", "connection_id": "P-1:INLET:1:S-1",
        }
        with patch.object(connection_selection, "_fact_exists_in_graph_asset", side_effect=lambda row: dict(row)):
            package = connection_selection.build_aspen_connection_component_selections(
                block=block, streams=streams, match_result=self.result["equipment"][0]["match_result"],
                source_export_sha256="C" * 64, pfd_mapping_sha256="D" * 64, property_evidence=[fact],
            )
        inlet, outlet = package["connections"]
        self.assertEqual(inlet["accepted_property_facts"][0]["value"], "RF")
        self.assertEqual(outlet["accepted_property_facts"], [])
        self.assertEqual(outlet["rejected_property_facts"][0]["reason"], "different_connection_requirement")

    def test_caller_cannot_widen_or_promote_hash_locked_graph_record_metadata(self) -> None:
        block = {"block_id": "P-1", "block_type": "PUMP", "inlet_streams": ["S-1"], "outlet_streams": []}
        stream = {
            "stream_id": "S-1", "stream_record_type": "MATERIAL", "phase": "liquid",
            "composition": [{"component_id": "A", "fraction": 1.0, "basis": "mole_fraction"}],
        }
        request = {
            "fact": "toxicity", "value": "high", "source_id": "FACT-1",
            "source_asset_path": "knowledge_graph/facts.json", "source_asset_sha256": "A" * 64,
            "source_record_sha256": "B" * 64, "qa_status": "VALIDATED", "subject_scope": "mixture",
            "stream_id": "S-1", "composition_sha256": connection_selection.composition_context_sha256(stream),
            "valid_phases": ["liquid"],
        }
        authoritative_record = {**request, "qa_status": "CANDIDATE", "valid_phases": ["vapor"]}
        authoritative_record.pop("source_asset_path")
        authoritative_record.pop("source_asset_sha256")
        authoritative_record.pop("source_record_sha256")
        with patch.object(connection_selection, "_fact_exists_in_graph_asset", return_value=authoritative_record):
            package = connection_selection.build_aspen_connection_component_selections(
                block=block, streams={"S-1": stream}, match_result=self.result["equipment"][0]["match_result"],
                source_export_sha256="C" * 64, pfd_mapping_sha256="D" * 64, property_evidence=[request],
            )
        connection = package["connections"][0]
        self.assertEqual(connection["accepted_property_facts"], [])
        self.assertEqual(connection["rejected_property_facts"][0]["reason"], "caller_fact_metadata_conflicts_with_graph_record")

    def test_out_of_range_phase_fraction_cannot_create_phase_label(self) -> None:
        block = {"block_id": "H-1", "block_type": "HEATER", "inlet_streams": ["S-1"], "outlet_streams": []}
        stream = {"stream_id": "S-1", "stream_record_type": "MATERIAL", "vapor_fraction": 2.0}
        package = connection_selection.build_aspen_connection_component_selections(
            block=block, streams={"S-1": stream}, match_result=self.result["equipment"][0]["match_result"],
            source_export_sha256="E" * 64, pfd_mapping_sha256="F" * 64,
        )
        connection = package["connections"][0]
        self.assertIsNone(connection["raw_service_context"]["normalized_phase"])
        for selected in connection["component_types"].values():
            self.assertEqual(selected["normalized_service_labels"]["phase"], "unknown")


if __name__ == "__main__":
    unittest.main(verbosity=2)
