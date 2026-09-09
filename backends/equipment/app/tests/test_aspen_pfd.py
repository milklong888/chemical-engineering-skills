from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = APP_DIR.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import aspen_pfd


def stream(stream_id: str, pressure_bar: float | None = None, phase: str | None = None, **values: object) -> dict[str, object]:
    row: dict[str, object] = {"stream_id": stream_id}
    if pressure_bar is not None:
        row["pressure_bar"] = pressure_bar
    if phase is not None:
        row["phase"] = phase
    row.update(values)
    return row


def block(block_id: str, block_type: str | None, inlet: list[str], outlet: list[str], **values: object) -> dict[str, object]:
    row: dict[str, object] = {
        "block_id": block_id,
        "inlet_streams": inlet,
        "outlet_streams": outlet,
    }
    if block_type is not None:
        row["block_type"] = block_type
    row.update(values)
    return row


def bundle(blocks: list[dict[str, object]], streams: list[dict[str, object]], equipment_map: list[dict[str, object]] | None = None) -> dict[str, object]:
    result: dict[str, object] = {
        "schema": "aspen-equipment-export-v1",
        "case": {
            "case_id": "PFD-TEST",
            "pressure_basis": "absolute",
            "run_status": {"terminal_errors": 0, "severe_errors": 0, "errors": 0, "warnings": 0},
        },
        "blocks": blocks,
        "streams": streams,
    }
    if equipment_map is not None:
        result["equipment_map"] = equipment_map
    return result


def block_result(result: dict[str, object], block_id: str) -> dict[str, object]:
    return next(item for item in result["blocks"] if item["block_id"] == block_id)  # type: ignore[index,union-attr]


class AspenPFDMappingTests(unittest.TestCase):
    def test_exact_block_type_has_priority_and_does_not_promote_model(self) -> None:
        source = bundle(
            [block("P-101", "PUMP", ["IN"], ["OUT"], HEAD_CAL=45.0)],
            [stream("IN", 1.2, "liquid"), stream("OUT", 5.0, "liquid")],
        )
        result = aspen_pfd.build_pfd_mapping(source)
        mapped = block_result(result, "P-101")
        automatic = mapped["automatic_mapping"]
        self.assertEqual(automatic["status"], "AUTO_EXACT")
        self.assertEqual(automatic["selection_id"], "block:PUMP")
        self.assertEqual(automatic["confidence_level"], "EXACT")
        self.assertFalse(automatic["evidence_gate"]["model_promotion_allowed"])
        self.assertEqual(result["evidence_gate"]["status"], "PFD_MAPPING_ONLY")

    def test_block_parameter_rows_use_canonical_derivation_not_raw_aspen_alias_values(self) -> None:
        source = bundle(
            [
                block(
                    "P-101",
                    "PUMP",
                    ["IN"],
                    ["OUT"],
                    WNET=51645.9043,
                    HEAD_CAL=2386.01438,
                    CEFF=0.649309122,
                    DELP_CAL=20.27825,
                )
            ],
            [stream("IN", 1.0, "liquid"), stream("OUT", 21.27825, "liquid")],
        )
        canonical = {
            "P-101": {
                "shaft_power_kw": 51.6459043,
                "head_m": 243.30575476844797,
                "efficiency_percent": 64.9309122,
                "pressure_drop_kpa": 2027.825,
            }
        }

        result = aspen_pfd.build_pfd_mapping(
            source,
            canonical_parameters_by_block=canonical,
        )
        rows = {
            item["field"]: item
            for item in block_result(result, "P-101")["parameters"]
        }

        self.assertAlmostEqual(rows["shaft_power_kw"]["value"], 51.6459043)
        self.assertAlmostEqual(rows["head_m"]["value"], 243.30575476844797)
        self.assertAlmostEqual(rows["efficiency_percent"]["value"], 64.9309122)
        self.assertAlmostEqual(rows["pressure_drop_kpa"]["value"], 2027.825)
        self.assertTrue(
            all(
                item["source_status"] == "ASPEN_DERIVED_PROCESS_SIDE"
                for item in rows.values()
            )
        )

    def test_unknown_pump_is_uniquely_inferred_from_head_phase_and_pressure_rise(self) -> None:
        source = bundle(
            [block("B1", "UNKNOWN", ["S1"], ["S2"], HEAD_CAL=38.0, WNET=5.0)],
            [stream("S1", 1.0, "liquid"), stream("S2", 4.5, "liquid")],
        )
        mapped = block_result(aspen_pfd.build_pfd_mapping(source), "B1")["automatic_mapping"]
        self.assertEqual(mapped["status"], "AUTO_INFERRED_UNIQUE")
        self.assertEqual(mapped["selection_id"], "block:PUMP")
        codes = {evidence["code"] for evidence in mapped["candidate_options"][0]["evidence"]}
        self.assertIn("FIELD_HEAD", codes)
        self.assertIn("LIQUID_PRESSURE_RISE", codes)

    def test_unknown_vapor_compression_retains_compressor_subtype_ambiguity(self) -> None:
        source = bundle(
            [block("C1", "UNKNOWN", ["S1"], ["S2"], WNET=140.0, PRES_RATIO=3.0)],
            [stream("S1", 1.0, "vapor"), stream("S2", 3.0, "vapor")],
        )
        mapped = block_result(aspen_pfd.build_pfd_mapping(source), "C1")["automatic_mapping"]
        self.assertEqual(mapped["status"], "AUTO_AMBIGUOUS")
        self.assertIsNone(mapped["selection_id"])
        self.assertEqual(mapped["family_id"], "family_compressor")
        self.assertTrue(mapped["ambiguity_retained"])
        self.assertEqual({item["selection_id"] for item in mapped["candidate_options"][:2]}, {"block:COMPR", "block:MCOMPR"})

    def test_stage_count_routes_to_general_tower_without_choosing_column_subtype(self) -> None:
        source = bundle(
            [block("T1", None, ["F"], ["OV", "BT"], NSTAGE=28)],
            [stream("F"), stream("OV"), stream("BT")],
        )
        mapped = block_result(aspen_pfd.build_pfd_mapping(source), "T1")["automatic_mapping"]
        self.assertEqual(mapped["status"], "AUTO_AMBIGUOUS")
        self.assertEqual(mapped["family_id"], "family_tower")
        self.assertIsNone(mapped["selection_id"])
        self.assertGreaterEqual(len(mapped["candidate_options"]), 5)

    def test_two_side_heat_fields_infer_heatx_but_not_fixed_tubesheet_construction(self) -> None:
        source = bundle(
            [block("E1", "UNKNOWN", ["HIN", "CIN"], ["HOUT", "COUT"], QCALC=-1200.0, AREA=85.0)],
            [stream(item) for item in ("HIN", "CIN", "HOUT", "COUT")],
        )
        mapped = block_result(aspen_pfd.build_pfd_mapping(source), "E1")["automatic_mapping"]
        self.assertEqual(mapped["status"], "AUTO_INFERRED_UNIQUE")
        self.assertEqual(mapped["selection_id"], "block:HEATX")
        self.assertIn("family:family_fixed_tubesheet_exchanger", {item["selection_id"] for item in mapped["candidate_options"]})

    def test_general_column_type_keeps_catalog_subtypes_open(self) -> None:
        source = bundle([block("T1", "COLUMN", ["F"], ["P"])], [stream("F"), stream("P")])
        mapped = block_result(aspen_pfd.build_pfd_mapping(source), "T1")["automatic_mapping"]
        self.assertEqual(mapped["status"], "AUTO_AMBIGUOUS")
        self.assertEqual(mapped["family_id"], "family_tower")
        self.assertIsNone(mapped["selection_id"])

    def test_frozen_cooler_alias_maps_to_heater_module_selection(self) -> None:
        source = bundle([block("E1", "COOLER", ["F"], ["P"])], [stream("F"), stream("P")])
        mapped = block_result(aspen_pfd.build_pfd_mapping(source), "E1")["automatic_mapping"]
        self.assertEqual(mapped["status"], "AUTO_INFERRED_UNIQUE")
        self.assertEqual(mapped["selection_id"], "block:HEATER")
        self.assertEqual(mapped["inference_basis"], "FROZEN_BLOCK_TYPE_ALIAS")

    def test_equipment_map_type_is_used_when_aspen_type_is_unreadable(self) -> None:
        source = bundle(
            [block("P1", "UNKNOWN", ["F"], ["P"])],
            [stream("F"), stream("P")],
            [{"block_id": "P1", "equipment_tag": "P-201", "equipment_type": "PUMP"}],
        )
        mapped = block_result(aspen_pfd.build_pfd_mapping(source), "P1")["automatic_mapping"]
        self.assertEqual(mapped["status"], "AUTO_INFERRED_UNIQUE")
        self.assertEqual(mapped["selection_id"], "block:PUMP")

    def test_no_type_or_features_stays_unresolved(self) -> None:
        source = bundle([block("B1", None, [], [])], [])
        mapped = block_result(aspen_pfd.build_pfd_mapping(source), "B1")["automatic_mapping"]
        self.assertEqual(mapped["status"], "AUTO_UNRESOLVED")
        self.assertIsNone(mapped["selection_id"])
        self.assertEqual(mapped["confidence_level"], "NONE")

    def test_valid_override_is_catalog_bounded_and_keeps_automatic_result(self) -> None:
        source = bundle([block("B1", "UNKNOWN", ["F"], ["P"])], [stream("F"), stream("P")])
        result = aspen_pfd.build_pfd_mapping(source, {"B1": "block:VALVE"})
        mapped = block_result(result, "B1")
        self.assertEqual(mapped["automatic_mapping"]["status"], "AUTO_UNRESOLVED")
        self.assertEqual(mapped["effective_mapping"]["mode"], "user_override")
        self.assertEqual(mapped["effective_mapping"]["selection_id"], "block:VALVE")
        self.assertEqual(mapped["effective_mapping"]["evidence_gate"]["status"], "USER_TYPE_OVERRIDE_NOT_MODEL_EVIDENCE")

    def test_invalid_override_selection_fails_with_machine_code(self) -> None:
        source = bundle([block("B1", "UNKNOWN", [], [])], [])
        with self.assertRaises(aspen_pfd.AspenPFDMappingError) as raised:
            aspen_pfd.build_pfd_mapping(source, {"B1": "block:NOT_REAL"})
        self.assertEqual(raised.exception.code, "INVALID_OVERRIDE_SELECTION")
        self.assertIn("allowed_selection_ids", raised.exception.details)

    def test_unknown_override_block_fails_with_machine_code(self) -> None:
        source = bundle([block("B1", "UNKNOWN", [], [])], [])
        with self.assertRaises(aspen_pfd.AspenPFDMappingError) as raised:
            aspen_pfd.update_type_override(source, {}, "NO-BLOCK", "block:PUMP")
        self.assertEqual(raised.exception.code, "UNKNOWN_OVERRIDE_BLOCK")

    def test_restore_automatic_removes_override_and_marks_change(self) -> None:
        source = bundle([block("P1", "PUMP", ["F"], ["P"])], [stream("F"), stream("P")])
        restored = aspen_pfd.restore_automatic_mapping(source, {"P1": "block:VALVE"}, "P1")
        self.assertEqual(restored["action"], "RESTORE_AUTOMATIC_MAPPING")
        self.assertEqual(restored["overrides"], {})
        mapped = block_result(restored["mapping"], "P1")
        self.assertEqual(mapped["effective_mapping"]["mode"], "automatic")
        self.assertEqual(mapped["effective_mapping"]["selection_id"], "block:PUMP")
        self.assertEqual(mapped["recalculation_status"], "TYPE_CHANGED_PENDING_RECALC")

    def test_simple_pfd_uses_external_boundary_nodes_and_stream_pipelines(self) -> None:
        source = bundle(
            [block("P1", "PUMP", ["FEED"], ["PRODUCT"])],
            [stream("FEED", 1.0, "liquid"), stream("PRODUCT", 3.0, "liquid")],
        )
        pfd = aspen_pfd.build_pfd_mapping(source)["pfd"]
        edges = {item["stream_id"]: item for item in pfd["edges"]}
        self.assertEqual(edges["FEED"]["source_node_id"], "boundary:feed:FEED")
        self.assertEqual(edges["FEED"]["target_node_id"], "block:P1")
        self.assertEqual(edges["PRODUCT"]["source_node_id"], "block:P1")
        self.assertEqual(edges["PRODUCT"]["target_node_id"], "boundary:outlet:PRODUCT")
        self.assertTrue(all(item["kind"] == "process_stream_pipeline" for item in pfd["edges"]))

    def test_pfd_node_interactions_are_declared_for_gui(self) -> None:
        source = bundle([block("P1", "PUMP", [], [])], [])
        pfd = aspen_pfd.build_pfd_mapping(source)["pfd"]
        node = next(item for item in pfd["nodes"] if item["node_id"] == "block:P1")
        self.assertEqual(node["interaction"]["left_click"], "open_block_parameter_detail")
        self.assertEqual(node["interaction"]["right_click"], "open_validated_type_override_menu")
        self.assertEqual(node["interaction"]["restore_automatic_action"], "restore_automatic_mapping")
        self.assertEqual(pfd["display_contract"]["default_level"], "standard")
        self.assertEqual(set(pfd["display_contract"]["levels"]), {"compact", "standard", "detailed"})
        self.assertFalse(node["display"]["parameters_inline_on_canvas"])
        self.assertEqual(
            set(node["display"]["standard"]),
            {"equipment_id", "source_module_type", "mapped_type", "selection_status"},
        )
        self.assertEqual(node["display"]["detailed"]["inline_parameter_fields"], [])

    def test_stream_parameters_are_exposed_with_compact_presentation_only(self) -> None:
        source = bundle(
            [block("P1", "PUMP", ["F"], ["P"])],
            [stream("F", 1.23456789, "liquid", temperature_c=23.456789, mass_flow_kg_h=12345.6789), stream("P")],
        )
        feed = next(item for item in aspen_pfd.build_pfd_mapping(source)["pfd"]["edges"] if item["stream_id"] == "F")
        rows = {item["field"]: item for item in feed["parameters"]}
        self.assertEqual(rows["pressure_bar"]["value"], 1.23456789)
        self.assertNotEqual(rows["pressure_bar"]["display"], str(rows["pressure_bar"]["value"]))
        self.assertFalse(rows["pressure_bar"]["formal_design_evidence"])

    def test_raw_aspen_aliases_without_unit_normalization_are_not_relabelled(self) -> None:
        source = bundle([block("E1", "HEATER", [], [], QCALC=-125.25, AREA=9.75)], [])
        mapped = block_result(aspen_pfd.build_pfd_mapping(source), "E1")
        rows = {item["field"]: item for item in mapped["parameters"]}
        self.assertNotIn("heat_duty_kw", rows)
        self.assertNotIn("heat_transfer_area_m2", rows)

        canonical_source = bundle(
            [block("E1", "HEATER", [], [], heat_duty_kw=-125.25, heat_transfer_area_m2=9.75)],
            [],
        )
        canonical_rows = {
            item["field"]: item
            for item in block_result(aspen_pfd.build_pfd_mapping(canonical_source), "E1")["parameters"]
        }
        self.assertEqual(canonical_rows["heat_duty_kw"]["value"], -125.25)
        self.assertEqual(canonical_rows["heat_transfer_area_m2"]["unit"], "m²")

    def test_structured_canonical_unit_mismatch_is_explicitly_blocked(self) -> None:
        source = bundle([block("E1", "HEATER", [], [], QCALC=-125250.0)], [])
        result = aspen_pfd.build_pfd_mapping(
            source,
            canonical_parameters_by_block={
                "E1": {
                    "heat_duty_kw": {
                        "value": -125250.0,
                        "canonical_unit": "W",
                        "source_field": "QCALC",
                        "raw_value": -125250.0,
                        "raw_unit": "W",
                    }
                }
            },
        )
        row = block_result(result, "E1")["parameters"][0]
        self.assertEqual(row["source_status"], "BLOCKED_UNIT_NORMALIZATION")
        self.assertIsNone(row["value"])
        self.assertEqual(row["expected_canonical_unit"], "kW")

    def test_layout_is_deterministic_when_bundle_list_order_changes(self) -> None:
        source = bundle(
            [block("B1", "HEATER", ["S0"], ["S1"]), block("B2", "HEATER", ["S1"], ["S2"])],
            [stream("S0"), stream("S1"), stream("S2")],
        )
        reversed_source = copy.deepcopy(source)
        reversed_source["blocks"].reverse()
        reversed_source["streams"].reverse()
        left = aspen_pfd.build_pfd_mapping(source)["pfd"]
        right = aspen_pfd.build_pfd_mapping(reversed_source)["pfd"]
        left_geometry = {item["node_id"]: item["geometry"] for item in left["nodes"]}
        right_geometry = {item["node_id"]: item["geometry"] for item in right["nodes"]}
        self.assertEqual(left_geometry, right_geometry)
        left_routes = {item["edge_id"]: item["route"] for item in left["edges"]}
        right_routes = {item["edge_id"]: item["route"] for item in right["edges"]}
        self.assertEqual(left_routes, right_routes)

    def test_parallel_streams_between_same_blocks_use_distinct_lanes(self) -> None:
        source = bundle(
            [
                block("B1", "HEATER", ["F"], ["S1", "S2"]),
                block("B2", "HEATER", ["S1", "S2"], ["P"]),
            ],
            [stream(item) for item in ("F", "S1", "S2", "P")],
        )
        edges = {
            item["stream_id"]: item
            for item in aspen_pfd.build_pfd_mapping(source)["pfd"]["edges"]
            if item["stream_id"] in {"S1", "S2"}
        }
        self.assertNotEqual(edges["S1"]["route"]["points"], edges["S2"]["route"]["points"])
        self.assertEqual(edges["S1"]["route"]["parallel_lane_count"], 2)
        self.assertEqual(edges["S2"]["route"]["parallel_lane_count"], 2)
        self.assertEqual(
            abs(edges["S1"]["route"]["parallel_lane_offset"] - edges["S2"]["route"]["parallel_lane_offset"]),
            12.0,
        )

    def test_identical_input_has_identical_mapping_hash(self) -> None:
        source = bundle([block("P1", "PUMP", ["F"], ["P"])], [stream("F"), stream("P")])
        left = aspen_pfd.build_pfd_mapping(source)
        right = aspen_pfd.build_pfd_mapping(copy.deepcopy(source))
        self.assertEqual(left["mapping_sha256"], right["mapping_sha256"])

    def test_compact_summary_is_shared_machine_projection_not_model_evidence(self) -> None:
        source = bundle([block("P1", "PUMP", ["F"], ["P"])], [stream("F"), stream("P")])
        mapping = aspen_pfd.build_pfd_mapping(source)
        summary = aspen_pfd.summarize_pfd_mapping(mapping)
        self.assertEqual(summary["mapping_sha256"], mapping["mapping_sha256"])
        self.assertEqual(summary["block_count"], 1)
        self.assertEqual(summary["node_count"], 3)
        self.assertEqual(summary["edge_count"], 2)
        self.assertEqual(summary["mapping_status_counts"], {"AUTO_EXACT": 1})
        self.assertFalse(summary["model_promotion_allowed"])

    def test_recycle_is_routed_without_breaking_topology(self) -> None:
        source = bundle(
            [block("B1", "HEATER", ["S21"], ["S12"]), block("B2", "HEATER", ["S12"], ["S21"])],
            [stream("S12"), stream("S21")],
        )
        pfd = aspen_pfd.build_pfd_mapping(source)["pfd"]
        route_kinds = [edge["route"]["kind"] for edge in pfd["edges"]]
        self.assertEqual(route_kinds.count("forward_orthogonal"), 1)
        self.assertEqual(route_kinds.count("recycle_orthogonal"), 1)
        self.assertEqual(pfd["layout"]["scc_count"], 1)
        self.assertEqual(pfd["layout"]["feedback_edge_count"], 1)
        self.assertEqual(pfd["layout"]["recycle_lane_pitch"], 44.0)

    def test_forward_bypass_uses_outer_rail_instead_of_crossing_intermediate_equipment(self) -> None:
        source = bundle(
            [
                block("A", "HEATER", ["F"], ["AB", "AC"]),
                block("B", "HEATER", ["AB"], ["BC"]),
                block("C", "HEATER", ["BC", "AC"], ["P"]),
            ],
            [stream(item) for item in ("F", "AB", "AC", "BC", "P")],
        )
        pfd = aspen_pfd.build_pfd_mapping(source)["pfd"]
        bypass = next(edge for edge in pfd["edges"] if edge["stream_id"] == "AC")
        middle = next(node for node in pfd["nodes"] if node.get("block_id") == "B")["geometry"]
        self.assertEqual(bypass["route"]["kind"], "forward_bypass_orthogonal")
        self.assertGreater(
            bypass["route"]["points"][2][1],
            middle["y"] + middle["height"],
        )
        self.assertEqual(bypass["route"]["source_fan_count"], 2)
        self.assertEqual(bypass["route"]["target_fan_count"], 2)

    def test_real_bkp_feedback_dag_shortens_layout_and_keeps_0205_off_e0101(self) -> None:
        source_path = PACKAGE_ROOT / "outputs" / "bkp_pfd_source_acceptance_20260718_main_elevated" / "aspen_equipment_export.json"
        if not source_path.exists():
            self.skipTest("real BKP acceptance export is unavailable")
        source = json.loads(source_path.read_text(encoding="utf-8"))
        pfd = aspen_pfd.build_pfd_mapping(source)["pfd"]
        stream_0205 = next(edge for edge in pfd["edges"] if edge["stream_id"] == "0205")
        e0101 = next(node for node in pfd["nodes"] if node.get("block_id") == "E0101")["geometry"]

        def segment_hits_box(left: list[float], right: list[float]) -> bool:
            x1, y1 = e0101["x"], e0101["y"]
            x2, y2 = x1 + e0101["width"], y1 + e0101["height"]
            if abs(left[1] - right[1]) < 1e-9:
                low, high = sorted((left[0], right[0]))
                return y1 <= left[1] <= y2 and max(low, x1) <= min(high, x2)
            if abs(left[0] - right[0]) < 1e-9:
                low, high = sorted((left[1], right[1]))
                return x1 <= left[0] <= x2 and max(low, y1) <= min(high, y2)
            return False

        self.assertFalse(any(
            segment_hits_box(left, right)
            for left, right in zip(stream_0205["route"]["points"], stream_0205["route"]["points"][1:])
        ))
        self.assertLessEqual(pfd["layout"]["feedback_edge_count"], 8)
        self.assertLessEqual(pfd["layout"]["canvas"]["height"], 1800.0)
        self.assertEqual(pfd["layout"]["algorithm"], "deterministic-feedback-dag-obstacle-orthogonal-v3")

    def test_multiple_consumers_are_preserved_and_flagged_not_silently_rewired(self) -> None:
        source = bundle(
            [
                block("B1", "HEATER", ["F"], ["S"]),
                block("B2", "HEATER", ["S"], ["P2"]),
                block("B3", "HEATER", ["S"], ["P3"]),
            ],
            [stream(item) for item in ("F", "S", "P2", "P3")],
        )
        pfd = aspen_pfd.build_pfd_mapping(source)["pfd"]
        shared = [edge for edge in pfd["edges"] if edge["stream_id"] == "S"]
        self.assertEqual(len(shared), 2)
        self.assertEqual({edge["target_node_id"] for edge in shared}, {"block:B2", "block:B3"})
        self.assertTrue(all(edge["topology_status"] == "MULTIPLE_CONSUMERS_REVIEW" for edge in shared))
        self.assertEqual(pfd["topology_gate"]["status"], "REVIEW")

    def test_connection_records_are_used_when_port_arrays_are_empty(self) -> None:
        source = bundle(
            [{
                "block_id": "P1",
                "block_type": "PUMP",
                "inlet_streams": [],
                "outlet_streams": [],
                "connections": [
                    {"name": "F", "value": "MATERIAL(IN)"},
                    {"name": "P", "value": "MATERIAL(OUT)"},
                ],
            }],
            [stream("F"), stream("P")],
        )
        result = aspen_pfd.build_pfd_mapping(source)
        mapped = block_result(result, "P1")
        self.assertEqual(mapped["source"]["inlet_streams"], ["F"])
        self.assertEqual(mapped["source"]["outlet_streams"], ["P"])
        self.assertEqual(mapped["source"]["connectivity_source"], "connections/port_detail")

    def test_referenced_stream_without_result_row_is_visible_and_gated(self) -> None:
        source = bundle([block("P1", "PUMP", ["F"], ["P"])], [stream("F")])
        pfd = aspen_pfd.build_pfd_mapping(source)["pfd"]
        self.assertIn("P", pfd["topology_gate"]["referenced_stream_data_missing"])
        self.assertEqual(pfd["topology_gate"]["status"], "REVIEW")
        self.assertTrue(any(edge["stream_id"] == "P" for edge in pfd["edges"]))

    def test_override_change_invalidates_only_local_dependency_neighborhood(self) -> None:
        source = bundle(
            [
                block("B1", "HEATER", ["S0"], ["S1"]),
                block("B2", "HEATER", ["S1"], ["S2"]),
                block("B3", "HEATER", ["S2"], ["S3"]),
                block("B4", "HEATER", ["S3"], ["S4"]),
            ],
            [stream(f"S{index}") for index in range(5)],
        )
        updated = aspen_pfd.update_type_override(source, {}, "B2", "block:VALVE")
        impact = updated["change_impact"]
        self.assertEqual(impact["changed_blocks"], ["B2"])
        self.assertEqual(impact["affected_streams"], ["S1", "S2"])
        self.assertEqual(impact["immediate_upstream_blocks"], ["B1"])
        self.assertEqual(impact["immediate_downstream_blocks"], ["B3"])
        self.assertEqual(impact["unchanged_blocks"], ["B4"])
        states = {item["block_id"]: item["recalculation_status"] for item in updated["mapping"]["blocks"]}
        self.assertEqual(states["B2"], "TYPE_CHANGED_PENDING_RECALC")
        self.assertEqual(states["B1"], "UPSTREAM_RELATED_PENDING_RECALC")
        self.assertEqual(states["B3"], "DOWNSTREAM_RELATED_PENDING_RECALC")
        self.assertEqual(states["B4"], "STABLE")
        edge_states = {item["stream_id"]: item["recalculation_status"] for item in updated["mapping"]["pfd"]["edges"]}
        self.assertEqual(edge_states["S1"], "RELATED_STREAM_PENDING_RECALC")
        self.assertEqual(edge_states["S2"], "RELATED_STREAM_PENDING_RECALC")
        self.assertEqual(edge_states["S3"], "STABLE")

    def test_parameter_override_is_separate_and_marks_only_local_dependencies(self) -> None:
        source = bundle(
            [
                block("B1", "HEATER", ["S0"], ["S1"]),
                block("B2", "FLASH2", ["S1"], ["S2"]),
                block("B3", "HEATER", ["S2"], ["S3"]),
                block("B4", "HEATER", ["S3"], ["S4"]),
            ],
            [stream(f"S{index}") for index in range(5)],
        )
        frozen = copy.deepcopy(source)
        updated = aspen_pfd.update_parameter_override(
            source,
            {},
            {},
            "B2",
            {"design_pressure_mpa_g": 0.8, "head_type": "2:1_ellipsoidal"},
        )

        self.assertEqual(source, frozen)
        self.assertEqual(updated["parameter_overrides"]["B2"]["design_pressure_mpa_g"], 0.8)
        self.assertFalse(updated["parameter_override_evidence_gate"]["formal_design_evidence"])
        self.assertEqual(updated["change_impact"]["change_kind"], "parameter")
        self.assertNotIn("block_type_binding", updated["change_impact"]["invalidated_scopes"])
        states = {item["block_id"]: item["recalculation_status"] for item in updated["mapping"]["blocks"]}
        self.assertEqual(states["B2"], "PARAMETERS_CHANGED_PENDING_RECALC")
        self.assertEqual(states["B1"], "UPSTREAM_RELATED_PENDING_RECALC")
        self.assertEqual(states["B3"], "DOWNSTREAM_RELATED_PENDING_RECALC")
        self.assertEqual(states["B4"], "STABLE")

    def test_parameter_override_clear_restores_empty_layer_and_route_fields_are_forbidden(self) -> None:
        source = bundle([block("P-101", "PUMP", ["F"], ["P"])], [stream("F"), stream("P")])
        cleared = aspen_pfd.update_parameter_override(
            source,
            {},
            {"P-101": {"required_npsh_margin_m": 0.5}},
            "P-101",
            clear=True,
        )
        self.assertEqual(cleared["action"], "CLEAR_BLOCK_PARAMETER_OVERRIDES")
        self.assertEqual(cleared["parameter_overrides"], {})

        with self.assertRaises(aspen_pfd.AspenPFDMappingError) as raised:
            aspen_pfd.update_parameter_override(
                source,
                {},
                {},
                "P-101",
                {"equipment_family": "family_valve"},
            )
        self.assertEqual(raised.exception.code, "PARAMETER_OVERRIDE_ROUTE_FIELD_FORBIDDEN")

    def test_parameter_merge_preserves_trusted_identity_and_removes_only_matcher_route(self) -> None:
        base = {
            "equipment_tag": "P-101",
            "aspen_block_type": "PUMP",
            "phase": "liquid",
            "flow_m3_h": 20.0,
        }
        merged = aspen_pfd.merge_canonical_input_with_parameter_overrides(
            "P-101",
            base,
            {"required_npsh_margin_m": 0.5},
        )
        self.assertEqual(merged["equipment_tag"], "P-101")
        self.assertEqual(merged["phase"], "liquid")
        self.assertEqual(merged["required_npsh_margin_m"], 0.5)
        self.assertNotIn("aspen_block_type", merged)
        self.assertEqual(base["aspen_block_type"], "PUMP")

    def test_catalog_options_expose_only_valid_right_click_choices(self) -> None:
        source = bundle([block("P1", "PUMP", [], [])], [])
        result = aspen_pfd.build_pfd_mapping(source)
        options = result["catalog"]["selection_options"]
        selection_ids = [item["selection_id"] for item in options]
        self.assertEqual(len(selection_ids), result["catalog"]["selection_count"])
        self.assertEqual(len(selection_ids), len(set(selection_ids)))
        self.assertIn("block:PUMP", selection_ids)
        self.assertIn("family:family_process_piping", selection_ids)

    def test_duplicate_block_and_stream_ids_fail_closed(self) -> None:
        duplicate_blocks = bundle([block("B1", "PUMP", [], []), block("B1", "VALVE", [], [])], [])
        with self.assertRaises(aspen_pfd.AspenPFDMappingError) as block_error:
            aspen_pfd.build_pfd_mapping(duplicate_blocks)
        self.assertEqual(block_error.exception.code, "DUPLICATE_BLOCK_ID")

        duplicate_streams = bundle([], [stream("S1"), stream("S1")])
        with self.assertRaises(aspen_pfd.AspenPFDMappingError) as stream_error:
            aspen_pfd.build_pfd_mapping(duplicate_streams)
        self.assertEqual(stream_error.exception.code, "DUPLICATE_STREAM_ID")

    def test_schema_gate_rejects_non_aspen_bundle(self) -> None:
        with self.assertRaises(aspen_pfd.AspenPFDMappingError) as raised:
            aspen_pfd.build_pfd_mapping({"schema": "something-else", "blocks": [], "streams": []})
        self.assertEqual(raised.exception.code, "INVALID_ASPEN_EXPORT_SCHEMA")

    def test_real_sample_bundle_maps_and_serializes_as_json(self) -> None:
        source = json.loads((PACKAGE_ROOT / "data" / "aspen_equipment_export_sample.json").read_text(encoding="utf-8"))
        result = aspen_pfd.build_pfd_mapping(source)
        self.assertEqual(result["schema"], "equipment-design-pfd-mapping-v1")
        self.assertEqual(block_result(result, "P-101")["effective_mapping"]["selection_id"], "block:PUMP")
        encoded = json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False)
        self.assertIn("P-101", encoded)
        self.assertRegex(result["mapping_sha256"], r"^[0-9A-F]{64}$")


if __name__ == "__main__":
    unittest.main()
