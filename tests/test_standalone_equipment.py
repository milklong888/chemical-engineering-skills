"""Original backend through the standalone local gateway; synthetic only."""
from __future__ import annotations
import copy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import equipment_gateway as gateway

SOURCE = {"operation": "manual_match", "payload": {"selection_id": "block:PUMP", "values": {
    "equipment_tag": "SYN-GATEWAY-P", "phase": "liquid", "flow_m3_h": 20,
    "head_m": 45, "density_kg_m3": 900, "efficiency_percent": 75}}}
GUARD = "import sys,runpy\ndef guard(event,args):\n if event.startswith('socket.') or (event=='import' and str(args[0]).split('.')[0] in {'pythoncom','win32com'}): raise RuntimeError('OFFLINE_TEST_FORBIDS_NETWORK_OR_COM')\n if event=='open' and any(part in str(args[0]) for part in ('external_sources','设备设计选型工作包')): raise RuntimeError('OTHER_PRODUCT_SOURCE_FORBIDDEN')\nsys.addaudithook(guard)\nsys.argv=[sys.argv[1],'--session-jsonl']\nrunpy.run_path(sys.argv[0],run_name='__main__')"


def request(operation, payload=None):
    return {"schema": "equipment-design-agent-request-v1", "operation": operation, "payload": payload or {}}


class StandaloneEquipmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="standalone_equipment_synthetic_")
        cls.work = Path(cls.temporary.name)
        cls.bundle = cls.work / "synthetic_export.json"
        bundle = json.loads((gateway.BACKEND / "app/fixtures/mock_aspen_pump.json").read_text(encoding="utf-8"))["bundle"]
        bundle["case"]["case_id"] = "SYN-STANDALONE-EXPORT"
        cls.bundle.write_text(json.dumps(bundle), encoding="utf-8")
        cls.source_hash = hashlib.sha256(cls.bundle.read_bytes()).hexdigest()
        cls.authority_before = gateway._authority_snapshot()
        original_command = gateway._command
        def guarded(environment):
            command = original_command(environment)
            return command[:-2] + ["-c", GUARD, str(gateway.AGENT)]
        cls.command_patch = mock.patch.object(gateway, "_command", side_effect=guarded)
        cls.command_patch.start()
        cls.session = gateway.EquipmentSession(timeout_s=60)

    @classmethod
    def tearDownClass(cls):
        cls.session.close()
        cls.command_patch.stop()
        if gateway._authority_snapshot() != cls.authority_before:
            raise AssertionError("Bundled source/data changed during gateway tests")
        cls.temporary.cleanup()

    def call(self, operation, payload=None):
        response = self.session.request(request(operation, payload))
        self.assertEqual(response["backend_exit_code"], 0, response)
        self.assertFalse(response["gateway"]["network_allowed"])
        self.assertFalse(response["gateway"]["com_allowed"])
        return response["response"]["result"]

    def test_01_discovery_18_local_16_aliases_and_native_24_schemas(self):
        catalog = gateway.available_operations()
        self.assertEqual(len(catalog["operations"]), 18)
        self.assertEqual(len(catalog["operation_aliases"]), 16)
        self.assertTrue(all(value in catalog["operations"] for value in catalog["operation_aliases"].values()))
        capabilities = self.call("system.capabilities")
        self.assertEqual(len(capabilities["operations"]), 21)
        self.assertEqual(len(capabilities["schemas"]), 24)
        self.assertTrue(capabilities["runtime_bundle"]["verified"])
        self.assertFalse(capabilities["gui_required"])

    def test_02_resident_failure_continues_same_pid_and_authority(self):
        rows = self.session.batch([request("manual_match", SOURCE["payload"]), request("manual_match"), request("catalog.get")])
        self.assertEqual([row["backend_exit_code"] for row in rows], [0, 2, 0])
        self.assertEqual(len({row["gateway"]["worker_pid"] for row in rows}), 1)
        self.assertEqual(len({row["gateway"]["authority_sha256"] for row in rows}), 1)
        self.assertEqual(rows[1]["response"]["errors"][0]["code"], "MANUAL_INPUT_INVALID")

    def test_03_reports_customer_and_organized_answer(self):
        path = self.work / "report.html"
        report = self.call("report.render", {"input": SOURCE, "format": "html", "output_path": str(path)})
        self.assertGreater(path.stat().st_size, 100)
        self.assertTrue(report["report_manifest"]["program_generated"])
        self.assertFalse(report["report_manifest"]["llm_used"])
        self.assertEqual(report["report_manifest"]["output_file_sha256"], hashlib.sha256(path.read_bytes()).hexdigest().upper())
        self.assertTrue(self.call("answer.organize", {"input": SOURCE})["organized_answer"])
        delivery = self.call("equipment.customer.export", {"input": SOURCE})["customer_delivery"]
        self.assertEqual(delivery["schema"], "equipment-customer-delivery-bundle-v1")

    def test_04_pfd_build_override_recalculate_and_source_immutability(self):
        common = {"bundle_path": str(self.bundle)}
        built = self.call("aspen.pfd.build", common)
        self.assertFalse(built["source_mutated"])
        overridden = self.call("aspen.pfd.override", {**common, "block_id": "P-101", "selection_id": "block:PUMP"})
        self.assertEqual(overridden["overrides"]["P-101"], "block:PUMP")
        revised = self.call("aspen.pfd.recalculate", {**common, "block_id": "P-101", "values": {"flow_m3_h": 22}})
        self.assertEqual(revised["parameter_overrides"]["P-101"]["flow_m3_h"], 22)
        self.assertFalse(revised["source_mutated"])
        self.assertTrue(revised["change_impact"])
        self.assertEqual(hashlib.sha256(self.bundle.read_bytes()).hexdigest(), self.source_hash)

    def test_05_offline_prepare_continue_apply_and_tamper_rejection(self):
        prepared = self.call("workflow.hybrid.prepare", {"input": SOURCE,
            "knowledge": {"enabled": False}, "injection_point": "semantic_extraction", "context_scope": "minimum"})
        step = {"schema": "equipment-design-llm-step-output-v1", "injection_point": "semantic_extraction",
                "context_sha256": prepared["context_pack"]["context_sha256"], "summary": "Synthetic offline descriptive review",
                "citations": [], "proposed_changes": [{"field": "process_function", "value": "liquid transfer",
                "reason": "Synthetic declared liquid duty", "citations": ["deterministic_result"]}],
                "condition_assessments": [], "calculation_assists": [], "retrieval_plan": [],
                "ambiguity_decision": None, "audit_findings": [], "output_composition": {"title": "Synthetic review", "blocks": [
                    {"block_id": "summary", "operation": "explain_result", "section_ref": "summary", "heading": "Summary", "citations": ["deterministic_result"]},
                    {"block_id": "proposed_changes", "operation": "propose_descriptive_change", "section_ref": "proposed_changes", "heading": "Change", "citations": ["deterministic_result"]}]}}
        proposal = self.call("workflow.hybrid.continue", {"prepared": prepared, "step_output": step})
        rejected = self.session.request(request("review.apply", {"proposal": proposal}))
        self.assertEqual(rejected["response"]["errors"][0]["code"], "EXPLICIT_APPROVAL_REQUIRED")
        applied = self.call("review.apply", {"proposal": proposal, "approval": {"approved": True,
            "approved_change_ids": ["change_001"], "approved_by": "synthetic-unit-test-not-project-authority",
            "context_sha256": proposal["context_sha256"], "orchestration_sha256": proposal["orchestration_sha256"]}})
        self.assertEqual(applied["applied_draft"]["process_function"], "liquid transfer")
        changed = copy.deepcopy(prepared)
        changed["prepared_sha256"] = "0" * 64
        rejected = self.session.request(request("hybrid_continue", {"prepared": changed, "step_output": step}))
        self.assertNotEqual(rejected["backend_exit_code"], 0)
        self.assertIsNotNone(self.call("catalog"))

    def test_06_remote_com_alias_and_nested_call_rejected_before_start(self):
        with gateway.EquipmentSession() as session:
            for operation in ("aspen_import", "aspen.case.import", "hybrid_run", "workflow.hybrid", "llm_review", "review.llm"):
                with self.assertRaises(ValueError):
                    session.request(request(operation))
            with self.assertRaises(ValueError):
                session.request(request("report.render", {"input": {"operation": "aspen.case.import", "payload": {}}}))
            self.assertIsNone(session.pid)

    def test_07_credentials_env_and_product_output_boundary(self):
        with mock.patch.dict(os.environ, {"EQUIPMENT_DESIGN_LLM_API_KEY": "synthetic-not-a-key",
                    "EQUIPMENT_BACKEND_ALLOW_COM": "1", "PYTHONPATH": "synthetic-old-workspace"}):
            env = gateway.local_environment()
            self.assertNotIn("EQUIPMENT_DESIGN_LLM_API_KEY", env)
            self.assertNotIn("EQUIPMENT_BACKEND_ALLOW_COM", env)
            self.assertNotIn("PYTHONPATH", env)
        for payload in ({"api_key": "synthetic-not-a-key"}, {"input": {"base_url": "http://127.0.0.1:1"}},
                        {"output_path": str(ROOT / "must-not-write.json")}):
            with self.assertRaises(ValueError):
                gateway.equipment(request("render_report", payload))
        self.assertFalse((ROOT / "must-not-write.json").exists())

    def test_08_local_policy_error_does_not_stop_batch(self):
        results = self.session.batch([request("workflow.hybrid"), request("capabilities")])
        self.assertEqual([item["backend_exit_code"] for item in results], [2, 0])
        self.assertIsNone(results[0]["response"])

    def test_09_timeout_terminates_only_owned_worker(self):
        unrelated = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(30)"], stdin=subprocess.DEVNULL,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            with mock.patch.object(gateway, "_command", return_value=[sys.executable, "-c", "import time;time.sleep(30)"]):
                session = gateway.EquipmentSession(timeout_s=0.1)
                with self.assertRaises(TimeoutError):
                    session.request(request("capabilities"))
                self.assertIsNotNone(session._process.poll())
                self.assertTrue(session._closed)
                self.assertIsNone(unrelated.poll())
        finally:
            unrelated.terminate()
            unrelated.wait(timeout=5)

    def test_10_authority_drift_closes_session_without_source_mutation(self):
        with gateway.EquipmentSession() as session:
            session.request(request("capabilities"))
            with mock.patch.object(gateway, "_authority_snapshot", side_effect=ValueError("synthetic-source-drift")):
                with self.assertRaises(ValueError):
                    session.request(request("catalog"))
            self.assertTrue(session._closed)
            self.assertIsNotNone(session._process.poll())

    def test_11_eof_closes_normal_resident_child(self):
        session = gateway.EquipmentSession()
        result = session.request(request("capabilities"))
        self.assertEqual(result["backend_exit_code"], 0)
        session.close()
        self.assertEqual(session._process.poll(), 0)

    def test_12_policy_discovery_is_lazy_and_states_separate_boundaries(self):
        with mock.patch.object(subprocess, "Popen", side_effect=AssertionError("Discovery must not start a process")):
            policy = gateway.describe_policy()
            self.assertEqual(len(policy["operations"]), 18)
            self.assertEqual(len(policy["operation_aliases"]), 16)
            self.assertEqual({row["operation"] for row in policy["excluded_operations"]}, {"aspen_import", "hybrid_run", "llm_review"})
            self.assertTrue(all(row["reason"] for row in policy["excluded_operations"]))
            session = gateway.EquipmentSession()
            self.assertIsNone(session.pid)
            session.close()

    def test_13_concurrent_callers_are_serialized_and_response_bound(self):
        requests = [{**request("catalog"), "request_id": "SYN_CONCURRENT_" + str(i)} for i in range(3)]
        with ThreadPoolExecutor(max_workers=3) as executor:
            results = list(executor.map(self.session.request, requests))
        self.assertEqual([row["response"]["request_id"] for row in results], [row["request_id"] for row in requests])
        self.assertEqual({row["gateway"]["worker_pid"] for row in results}, {self.session.pid})

    def test_14_single_call_keeps_exact_legacy_shape(self):
        result = gateway.equipment(request("catalog"))
        self.assertEqual(set(result), {"backend_exit_code", "response"})
        self.assertEqual(result["backend_exit_code"], 0)

    def test_15_every_registered_local_alias_reaches_original_validator(self):
        aliases = gateway.available_operations()["operation_aliases"]
        responses = self.session.batch([request(alias) for alias in aliases])
        for alias, result in zip(aliases, responses):
            self.assertIsInstance(result["response"], dict, (alias, result))
            self.assertEqual(result["response"]["operation"], aliases[alias])
            self.assertNotIn("gateway_error", result)

    def test_16_remaining_local_operations_and_current_export_hash(self):
        self.assertTrue(self.call("schema_get", {"schema_id": "equipment-design-agent-request-v1"})["document"])
        self.assertEqual(self.call("manual_batch", {"items": [SOURCE["payload"], SOURCE["payload"]]})["count"], 2)
        self.assertTrue(self.call("auto_match", {"values": {"equipment_family": "family_pump", **SOURCE["payload"]["values"]}}))
        self.assertTrue(self.call("knowledge_search", {"query": "GB/T 17395", "package_ids": ["design_standards"], "limit": 1})["hits"])
        derived = self.call("aspen_derive", {"export_path": str(self.bundle), "export_sha256": self.source_hash})
        self.assertTrue(derived)
        wrong = self.session.request(request("aspen_derive", {"export_path": str(self.bundle), "export_sha256": "0" * 64}))
        self.assertEqual(wrong["response"]["errors"][0]["code"], "ASPEN_EXPORT_HASH_MISMATCH")

    def test_17_early_alias_validation_failure_retains_native_response(self):
        invalid = {"schema": "equipment-design-agent-request-v1", "operation": "report.render", "payload": []}
        responses = self.session.batch([invalid, request("catalog")])
        self.assertEqual([row["backend_exit_code"] for row in responses], [2, 0])
        self.assertEqual(responses[0]["response"]["errors"][0]["code"], "PAYLOAD_NOT_OBJECT")
        self.assertEqual(responses[0]["gateway"]["worker_pid"], responses[1]["gateway"]["worker_pid"])

    def test_18_backend_is_usable_without_site_packages(self):
        original = gateway._command
        def no_site(environment):
            command = original(environment)
            return [command[0], "-S", *command[1:]]
        with mock.patch.object(gateway, "_command", side_effect=no_site):
            with gateway.EquipmentSession() as session:
                result = session.request(request("manual_match", SOURCE["payload"]))
                self.assertEqual(result["backend_exit_code"], 0, result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
