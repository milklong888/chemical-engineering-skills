from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
import uuid
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = APP_DIR.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import equipment_design_agent as agent


class AgentPFDTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = PACKAGE_ROOT / "data" / "aspen_equipment_export_sample.json"
        cls.output_root = PACKAGE_ROOT / "outputs" / "app_test_runs"
        cls.output_root.mkdir(parents=True, exist_ok=True)

    def request(self, operation: str, payload: dict[str, object]) -> dict[str, object]:
        return {
            "schema": "equipment-design-agent-request-v1",
            "request_id": f"PFD-{uuid.uuid4().hex[:12]}",
            "operation": operation,
            "payload": payload,
        }

    def test_capabilities_advertise_pfd_operations_schema_and_display_contract(self) -> None:
        response, code = agent.execute_request(self.request("capabilities", {}))
        self.assertEqual(code, 0, response)
        self.assertIn("pfd_build", response["result"]["operations"])
        self.assertIn("pfd_override", response["result"]["operations"])
        self.assertIn("pfd_recalculate", response["result"]["operations"])
        pfd = response["result"]["pfd"]
        self.assertEqual(pfd["operation_aliases"]["aspen.pfd.build"], "pfd_build")
        self.assertEqual(pfd["operation_aliases"]["aspen.pfd.override"], "pfd_override")
        self.assertEqual(pfd["operation_aliases"]["aspen.pfd.recalculate"], "pfd_recalculate")
        self.assertEqual(pfd["display_levels"], ["compact", "standard", "detailed"])
        self.assertEqual(pfd["default_display_level"], "standard")
        self.assertFalse(pfd["parameters_inline_on_canvas"])
        self.assertFalse(pfd["source_bundle_mutation_allowed"])
        self.assertFalse(pfd["model_promotion_allowed"])
        self.assertFalse(pfd["hybrid_or_llm_source_operation_allowed"])
        self.assertIn("deterministic matcher replay", pfd["parameter_recalculation_contract"])
        schema_ids = {item["schema_id"] for item in response["result"]["schemas"]}
        self.assertIn("equipment-design-pfd-mapping-v1", schema_ids)

    def test_schema_get_returns_pfd_mapping_contract(self) -> None:
        response, code = agent.execute_request(self.request(
            "schema_get",
            {"schema_id": "equipment-design-pfd-mapping-v1"},
        ))
        self.assertEqual(code, 0, response)
        self.assertEqual(response["result"]["document"]["$id"], "equipment-design-pfd-mapping-v1")
        self.assertEqual(len(response["result"]["sha256"]), 64)

    def test_mock_aspen_worker_result_exposes_pfd_artifact_and_summary(self) -> None:
        output = self.output_root / f"pfd_worker_{uuid.uuid4().hex[:12]}"
        response, code = agent.execute_request(self.request(
            "aspen_import",
            {
                "mock_fixture": str(APP_DIR / "fixtures" / "mock_aspen_pump.json"),
                "output_dir": str(output),
                "pressure_basis": "absolute",
                "timeout_s": 30,
            },
        ))
        self.assertEqual(code, 0, response)
        result = response["result"]
        self.assertEqual(Path(result["pfd_mapping"]), output / "aspen_pfd_mapping.json")
        self.assertTrue(Path(result["pfd_mapping"]).is_file())
        self.assertEqual(result["mapping_sha256"], result["pfd_summary"]["mapping_sha256"])
        self.assertEqual(result["pfd_summary"]["equipment_node_count"], 1)
        self.assertEqual(result["pfd_summary"]["edge_count"], 2)
        self.assertEqual(result["pfd_summary"]["topology_gate"]["status"], "PASS")
        self.assertEqual(result["pfd_summary"]["default_display_level"], "standard")
        artifact_names = {item["relative_path"] for item in response["artifacts"]}
        self.assertIn("aspen_pfd_mapping.json", artifact_names)

    def test_pfd_build_returns_inline_mapping_without_writing_when_output_is_omitted(self) -> None:
        before = agent.sha256_file(self.source)
        response, code = agent.execute_request(self.request(
            "pfd_build",
            {"bundle_path": str(self.source), "overrides": {}},
        ))
        self.assertEqual(code, 0, response)
        result = response["result"]
        self.assertEqual(result["schema"], "equipment-design-agent-pfd-operation-result-v1")
        self.assertEqual(result["action"], "BUILD_PFD_MAPPING")
        self.assertEqual(result["mapping"]["schema"], "equipment-design-pfd-mapping-v1")
        self.assertEqual(result["summary"]["equipment_node_count"], 1)
        self.assertEqual(result["summary"]["edge_count"], 2)
        self.assertEqual(result["summary"]["default_display_level"], "standard")
        self.assertEqual(result["mapping_sha256"], result["summary"]["mapping_sha256"])
        self.assertIsNone(result["output_path"])
        self.assertEqual(response["artifacts"], [])
        self.assertFalse(result["source_mutated"])
        self.assertFalse(result["summary"]["model_promotion_allowed"])
        self.assertEqual(agent.sha256_file(self.source), before)

    def test_agent_pfd_build_replays_shared_aspen_unit_normalization(self) -> None:
        fixture = json.loads((APP_DIR / "fixtures" / "mock_aspen_pump.json").read_text(encoding="utf-8"))
        bundle = fixture["bundle"]
        bundle["units"].update({
            "block.WNET": "Watt",
            "block.HEAD_CAL": "J/kg",
            "block.CEFF": "fraction",
            "block.DELP_CAL": "bar",
        })
        bundle["blocks"][0].update({
            "WNET": 51645.9043,
            "HEAD_CAL": 2386.01438,
            "CEFF": 0.649309122,
            "DELP_CAL": 20.27825,
        })
        source = self.output_root / f"pfd_units_{uuid.uuid4().hex[:12]}.json"
        source.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            response, code = agent.execute_request(self.request(
                "pfd_build",
                {"bundle_path": str(source)},
            ))
        finally:
            source.unlink(missing_ok=True)
        self.assertEqual(code, 0, response)
        block = next(item for item in response["result"]["mapping"]["blocks"] if item["block_id"] == "P-101")
        rows = {item["field"]: item for item in block["parameters"]}
        self.assertAlmostEqual(
            rows["electrical_power_kw"]["value"],
            51.6459043,
        )
        self.assertNotIn("shaft_power_kw", rows)
        self.assertAlmostEqual(rows["head_m"]["value"], 2386.01438 / 9.80665)
        self.assertAlmostEqual(rows["efficiency_percent"]["value"], 64.9309122)
        self.assertAlmostEqual(rows["pressure_drop_kpa"]["value"], 2027.825)
        self.assertEqual(
            response["result"]["mapping"]["source"]["parameter_binding"]["status"],
            "CANONICAL_DERIVATION_BOUND",
        )

    def test_pfd_build_alias_writes_separate_hashed_artifact(self) -> None:
        output = self.output_root / f"pfd_build_{uuid.uuid4().hex[:12]}.json"
        response, code = agent.execute_request(self.request(
            "aspen.pfd.build",
            {"bundle_path": str(self.source), "output_path": str(output)},
        ))
        self.assertEqual(code, 0, response)
        self.assertEqual(response["operation"], "pfd_build")
        self.assertTrue(output.is_file())
        self.assertEqual(response["result"]["output_path"], str(output.resolve()))
        self.assertEqual(len(response["artifacts"]), 1)
        self.assertEqual(response["artifacts"][0]["sha256"], agent.sha256_file(output))
        written = agent.load_json_file(output)
        self.assertEqual(written["mapping_sha256"], response["result"]["mapping_sha256"])

    def test_pfd_override_is_catalog_validated_and_only_marks_local_dependencies(self) -> None:
        output = self.output_root / f"pfd_override_{uuid.uuid4().hex[:12]}.json"
        before = agent.sha256_file(self.source)
        response, code = agent.execute_request(self.request(
            "pfd_override",
            {
                "bundle_path": str(self.source),
                "overrides": {},
                "block_id": "P-101",
                "selection_id": "block:VALVE",
                "output_path": str(output),
            },
        ))
        self.assertEqual(code, 0, response)
        result = response["result"]
        self.assertEqual(result["action"], "APPLY_USER_TYPE_OVERRIDE")
        self.assertEqual(result["overrides"], {"P-101": "block:VALVE"})
        block = result["mapping"]["blocks"][0]
        self.assertEqual(block["automatic_mapping"]["selection_id"], "block:PUMP")
        self.assertEqual(block["effective_mapping"]["selection_id"], "block:VALVE")
        self.assertEqual(block["effective_mapping"]["evidence_gate"]["status"], "USER_TYPE_OVERRIDE_NOT_MODEL_EVIDENCE")
        self.assertEqual(block["recalculation_status"], "TYPE_CHANGED_PENDING_RECALC")
        self.assertEqual(result["summary"]["override_count"], 1)
        self.assertFalse(result["summary"]["model_promotion_allowed"])
        self.assertEqual(agent.sha256_file(self.source), before)

    def test_pfd_override_auto_restores_automatic_mapping(self) -> None:
        response, code = agent.execute_request(self.request(
            "aspen.pfd.override",
            {
                "bundle_path": str(self.source),
                "overrides": {"P-101": "block:VALVE"},
                "block_id": "P-101",
                "selection_id": "AUTO",
            },
        ))
        self.assertEqual(code, 0, response)
        self.assertEqual(response["operation"], "pfd_override")
        self.assertEqual(response["result"]["action"], "RESTORE_AUTOMATIC_MAPPING")
        self.assertEqual(response["result"]["overrides"], {})
        block = response["result"]["mapping"]["blocks"][0]
        self.assertEqual(block["effective_mapping"]["mode"], "automatic")
        self.assertEqual(block["effective_mapping"]["selection_id"], "block:PUMP")
        self.assertEqual(block["recalculation_status"], "TYPE_CHANGED_PENDING_RECALC")

    def test_pfd_recalculate_merges_per_block_input_without_mutating_bundle(self) -> None:
        before = agent.sha256_file(self.source)
        response, code = agent.execute_request(self.request(
            "pfd_recalculate",
            {
                "bundle_path": str(self.source),
                "overrides": {},
                "parameter_overrides": {},
                "block_id": "P-101",
                "values": {
                    "required_npsh_margin_m": 0.5,
                    "npsha_m": 3.0,
                    "npshr_m": 2.0,
                },
            },
        ))
        self.assertEqual(code, 0, response)
        result = response["result"]
        self.assertEqual(result["schema"], "equipment-design-agent-pfd-recalculation-result-v1")
        self.assertEqual(result["selection_id"], "block:PUMP")
        self.assertEqual(result["recalculation_status"], "RECALCULATED_WAITING_FORMAL_EVIDENCE")
        self.assertTrue(result["formal_evidence_status"]["waiting"])
        self.assertEqual(result["parameter_overrides"]["P-101"]["required_npsh_margin_m"], 0.5)
        self.assertEqual(result["merged_match_input"]["npsha_m"], 3.0)
        self.assertEqual(result["base_canonical_match_input"]["equipment_tag"], "P-101")
        self.assertEqual(result["merged_match_input"]["equipment_tag"], "P-101")
        expected_merged = agent.aspen_pfd.merge_canonical_input_with_parameter_overrides(
            "P-101",
            result["base_canonical_match_input"],
            result["effective_parameter_overrides"],
        )
        self.assertEqual(result["merged_match_input"], expected_merged)
        self.assertEqual(result["deterministic_recalculation"]["schema"], "equipment-design-app-manual-result-v1")
        self.assertFalse(result["source_mutated"])
        self.assertFalse(result["llm_used"])
        self.assertEqual(agent.sha256_file(self.source), before)
        block = result["mapping"]["blocks"][0]
        self.assertEqual(block["recalculation_status"], "RECALCULATED_CURRENT")
        self.assertTrue(all(
            edge["recalculation_status"] == "RELATED_STREAM_PENDING_RECALC"
            for edge in result["mapping"]["pfd"]["edges"]
        ))
        match = result["deterministic_recalculation"]["result"]
        self.assertNotEqual(
            match.get("model_decision", {}).get("model_status"),
            "FINAL_MODEL",
        )

    def test_pfd_recalculate_clear_restores_aspen_input_and_writes_separate_state(self) -> None:
        output = self.output_root / f"pfd_recalc_{uuid.uuid4().hex[:12]}.json"
        response, code = agent.execute_request(self.request(
            "aspen.pfd.recalculate",
            {
                "bundle_path": str(self.source),
                "parameter_overrides": {"P-101": {"required_npsh_margin_m": 0.5}},
                "block_id": "P-101",
                "clear": True,
                "output_path": str(output),
            },
        ))
        self.assertEqual(code, 0, response)
        self.assertEqual(response["operation"], "pfd_recalculate")
        self.assertEqual(response["result"]["action"], "CLEAR_BLOCK_PARAMETER_OVERRIDES")
        self.assertEqual(response["result"]["parameter_overrides"], {})
        self.assertNotIn("required_npsh_margin_m", response["result"]["merged_match_input"])
        self.assertTrue(output.is_file())
        written = agent.load_json_file(output)
        self.assertEqual(written["mapping_sha256"], response["result"]["mapping_sha256"])

    def test_pfd_recalculate_rejects_route_field_and_nested_value(self) -> None:
        response, code = agent.execute_request(self.request(
            "pfd_recalculate",
            {
                "bundle_path": str(self.source),
                "block_id": "P-101",
                "values": {"equipment_family": "family_valve"},
            },
        ))
        self.assertEqual(code, 2)
        self.assertEqual(response["errors"][0]["code"], "PARAMETER_OVERRIDE_ROUTE_FIELD_FORBIDDEN")

        response, code = agent.execute_request(self.request(
            "pfd_recalculate",
            {
                "bundle_path": str(self.source),
                "block_id": "P-101",
                "values": {"head_m": {"value": 40}},
            },
        ))
        self.assertEqual(code, 2)
        self.assertEqual(response["errors"][0]["code"], "INVALID_PARAMETER_OVERRIDE_VALUE")

    def test_invalid_override_returns_mapper_machine_code(self) -> None:
        response, code = agent.execute_request(self.request(
            "pfd_override",
            {
                "bundle_path": str(self.source),
                "overrides": {},
                "block_id": "P-101",
                "selection_id": "block:FORGED-MODEL",
            },
        ))
        self.assertEqual(code, 2)
        self.assertEqual(response["errors"][0]["code"], "INVALID_OVERRIDE_SELECTION")
        self.assertIsNone(response["result"])

    def test_output_cannot_overwrite_source_bundle(self) -> None:
        before = agent.sha256_file(self.source)
        response, code = agent.execute_request(self.request(
            "pfd_build",
            {"bundle_path": str(self.source), "output_path": str(self.source)},
        ))
        self.assertEqual(code, 2)
        self.assertEqual(response["errors"][0]["code"], "PFD_OUTPUT_OVERWRITES_SOURCE_FORBIDDEN")
        self.assertEqual(agent.sha256_file(self.source), before)

    def test_path_and_json_failures_have_specific_machine_codes(self) -> None:
        missing = self.output_root / f"missing_{uuid.uuid4().hex}.json"
        response, code = agent.execute_request(self.request("pfd_build", {"bundle_path": str(missing)}))
        self.assertEqual(code, 2)
        self.assertEqual(response["errors"][0]["code"], "PFD_BUNDLE_FILE_NOT_FOUND")

        wrong_suffix = self.output_root / f"bundle_{uuid.uuid4().hex}.txt"
        wrong_suffix.write_text("{}", encoding="utf-8")
        response, code = agent.execute_request(self.request("pfd_build", {"bundle_path": str(wrong_suffix)}))
        self.assertEqual(code, 2)
        self.assertEqual(response["errors"][0]["code"], "PFD_BUNDLE_PATH_NOT_JSON")

        invalid = self.output_root / f"invalid_{uuid.uuid4().hex}.json"
        invalid.write_text("{not-json", encoding="utf-8")
        response, code = agent.execute_request(self.request("pfd_build", {"bundle_path": str(invalid)}))
        self.assertEqual(code, 2)
        self.assertEqual(response["errors"][0]["code"], "PFD_BUNDLE_JSON_INVALID")

    def test_strict_payload_rejects_unknown_or_nonscalar_override_fields(self) -> None:
        response, code = agent.execute_request(self.request(
            "pfd_build",
            {"bundle_path": str(self.source), "mystery": True},
        ))
        self.assertEqual(code, 2)
        self.assertEqual(response["errors"][0]["code"], "UNEXPECTED_PAYLOAD_FIELDS")

        response, code = agent.execute_request(self.request(
            "pfd_build",
            {"bundle_path": str(self.source), "overrides": {"P-101": 123}},
        ))
        self.assertEqual(code, 2)
        self.assertEqual(response["errors"][0]["code"], "PFD_OVERRIDES_INVALID")

    def test_pfd_build_stdin_stdout_mode_is_replayable(self) -> None:
        request = self.request("pfd_build", {"bundle_path": str(self.source), "overrides": {}})
        completed = subprocess.run(
            [
                sys.executable,
                str(APP_DIR / "equipment_design_agent.py"),
                "--request",
                "-",
                "--output",
                "-",
            ],
            input=(json.dumps(request, ensure_ascii=False) + "\n").encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ.copy(),
            timeout=60,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr.decode("utf-8", errors="replace"))
        response = json.loads(completed.stdout.decode("utf-8"))
        self.assertEqual(response["operation"], "pfd_build")
        self.assertEqual(response["result"]["summary"]["equipment_node_count"], 1)
        self.assertEqual(response["result"]["mapping"]["pfd"]["display_contract"]["default_level"], "standard")

    def test_pfd_override_file_to_file_mode_is_replayable(self) -> None:
        token = uuid.uuid4().hex[:12]
        request_path = self.output_root / f"pfd_request_{token}.json"
        response_path = self.output_root / f"pfd_response_{token}.json"
        mapping_path = self.output_root / f"pfd_mapping_{token}.json"
        request = self.request(
            "pfd_override",
            {
                "bundle_path": str(self.source),
                "overrides": {},
                "block_id": "P-101",
                "selection_id": "block:VALVE",
                "output_path": str(mapping_path),
            },
        )
        agent.atomic_write_json(request_path, request, pretty=True)
        completed = subprocess.run(
            [
                sys.executable,
                str(APP_DIR / "equipment_design_agent.py"),
                "--request",
                str(request_path),
                "--output",
                str(response_path),
                "--pretty",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ.copy(),
            timeout=60,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr.decode("utf-8", errors="replace"))
        response = agent.load_json_file(response_path)
        mapping = agent.load_json_file(mapping_path)
        self.assertEqual(response["operation"], "pfd_override")
        self.assertEqual(response["result"]["mapping_sha256"], mapping["mapping_sha256"])
        self.assertEqual(mapping["overrides"], {"P-101": "block:VALVE"})


if __name__ == "__main__":
    unittest.main()
