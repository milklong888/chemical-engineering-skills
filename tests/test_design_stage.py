"""Stage routing spies plus guarded real CLI/JSONL calculations; synthetic only."""
from __future__ import annotations
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SOURCE_ROOT = Path(__file__).resolve().parents[1]
ROOT = Path(os.environ.get("STANDALONE_PRODUCT_ROOT", SOURCE_ROOT)).resolve()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SOURCE_ROOT / "tests"))
from tools.design_stage import check_stage
from tools import expert_cli
from test_standalone_entrypoints import GUARD_SOURCE, BOOTSTRAP_SOURCE, CHILD_SOURCE


class DesignStageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="design_stage_synthetic_")
        self.root = Path(self.temp.name)
        self.queries, self.requests = [], []
        self.values = {"heat_duty_kw": 1000, "overall_u_w_m2k": 500, "lmtd_k": 40, "lmtd_correction_factor": 1}
        self.native = {"schema": "equipment-design-agent-request-v1", "request_id": "SYN-STAGE-E1", "operation": "manual_match",
            "payload": {"selection_id": "family:family_fixed_tubesheet_exchanger", "values": {"equipment_tag": "SYN-E1", **self.values}}}
        self.identity = {"case_id": "SYN-STAGE", "run_id": "SYN-CURRENT"}
        self.export = {"schema": "equipment-process-canonical-export-v1", **self.identity, "synthetic": True,
            "equipment": {"SYN-E1": {"family_id": "family_fixed_tubesheet_exchanger", "values": self.values,
                "units": {"heat_duty_kw": "kW", "overall_u_w_m2k": "W/m2/K", "lmtd_k": "K", "lmtd_correction_factor": "1"}}}}
        self.identity["source_export"] = self.put("export.json", self.export)
        self.identity["authority"] = self.put("authority.json", {"schema": "equipment-process-authority-v1",
            "case_id": "SYN-STAGE", "run_id": "SYN-CURRENT", "synthetic": True,
            "required_method": "SYNTHETIC same-input original calculation only", "acceptance_criteria": ["No engineering acceptance"]})
        self.payload = {"stage": "island", "question": "预热 换热器 传热面积 计算", **self.identity,
                        "equipment_requests": [{"equipment_id": "SYN-E1", "request": self.native}]}

    def tearDown(self):
        self.temp.cleanup()

    def put(self, name, value):
        data = json.dumps(value, ensure_ascii=False).encode("utf-8")
        (self.root / name).write_bytes(data)
        return {"path": name, "sha256": hashlib.sha256(data).hexdigest()}

    def search_spy(self, **query):
        self.queries.append(query)
        return {"knowledge": {"mode": "detail" if query["detail"] else "macro_first",
                "results": [{"node_id": query.get("node_id", "SYNTHETIC-ROUTING-SPY"), "knowledge_layer": "L3" if query.get("node_id") else "L2", "content_available": True, "text_is_excerpt": True}]}, "equipment": None}

    def equipment_spy(self, request):
        self.requests.append(request)
        if request.get("operation") == "capabilities":
            return {"backend_exit_code": 0, "response": {"synthetic_routing_spy": True}}
        if not request.get("payload"):
            return {"backend_exit_code": 2, "response": {"errors": [{"code": "SYNTHETIC_MISSING_FIELDS"}]}}
        core = {"equipment_tag": "SYN-E1", "normalized_input": {"equipment_tag": "SYN-E1", **self.values},
            "match": {"family_id": "family_fixed_tubesheet_exchanger"}, "model_decision": {"model_status": "type_screening"},
            "calculation_pending": [], "synthetic_routing_spy": True}
        return {"backend_exit_code": 0, "response": {"result": {"schema": "equipment-design-app-manual-result-v1", "result": core}}}

    def check(self, payload=None, search=None, equipment=None):
        return check_stage(payload or self.payload, self.root, search_runner=search or self.search_spy,
                           equipment_runner=equipment or self.equipment_spy)

    def test_source_without_equipment_invokes_upper_search_and_capabilities_only(self):
        result = self.check({"stage": "source", "question": "高温公用工程 预热 压缩"})
        self.assertEqual([query["detail"] for query in self.queries], [False, False])
        self.assertEqual(self.queries[0]["node_id"], "L3-03")
        self.assertEqual([request["operation"] for request in self.requests], ["capabilities"])
        self.assertEqual(result["equipment"], [])
        self.assertEqual(result["status"], "MODULE_CHECKS_EXECUTED")
        self.assertFalse(result["engineering_accepted"])
        self.assertFalse(result["stage_advanced"])

    def test_detail_is_just_in_time_and_each_device_is_really_dispatched(self):
        result = self.check()
        self.assertEqual([query["detail"] for query in self.queries], [False, True])
        self.assertEqual(self.requests, [self.native])
        self.assertEqual(result["equipment"][0]["feedback"]["result"]["equipment"][0]["binding_gaps"], [])
        self.assertFalse(result["inventory_coverage"]["independently_verified_complete"])
        self.assertIn("result_sha256", result["equipment"][0])

    def test_missing_current_identity_does_not_erase_valid_equipment_calculation(self):
        payload = {key: value for key, value in self.payload.items() if key not in self.identity}
        result = self.check(payload)
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(result["equipment"][0]["result"]["backend_exit_code"], 0)
        self.assertEqual(result["status"], "ACTION_REQUIRED")
        self.assertIn("CURRENT_REFERENCE_REQUIRED", {row["code"] for row in result["needs"]})

    def test_bad_request_does_not_stop_later_device(self):
        payload = copy.deepcopy(self.payload)
        payload["equipment_requests"].insert(0, {"equipment_id": "SYN-BAD", "request": {"operation": "manual_match", "payload": {}}})
        result = self.check(payload)
        self.assertEqual(len(self.requests), 2)
        self.assertEqual([row["result"]["backend_exit_code"] for row in result["equipment"]], [2, 0])
        self.assertEqual(result["status"], "ACTION_REQUIRED")

    def test_unhashable_operation_is_local_and_later_device_executes(self):
        payload = copy.deepcopy(self.payload)
        payload["equipment_requests"].insert(0, {"equipment_id": "SYN-BAD", "request": {"operation": [], "payload": {}}})
        result = self.check(payload)
        self.assertEqual(result["equipment"][0]["status"], "NOT_CALCULATED_OPERATION_NOT_ALLOWED")
        self.assertEqual(result["equipment"][1]["result"]["backend_exit_code"], 0)
        self.assertEqual(self.requests, [self.native])
        self.assertEqual(result["status"], "ACTION_REQUIRED")

    def test_invalid_pressure_check_shapes_do_not_skip_later_valid_check(self):
        valid = {"method": "series_pressure", "input_basis": "Synthetic absolute Pa; not a native-model result",
                 "inputs": {"inlet_pressure_pa": 500000, "losses_pa": [20000, 30000]}}
        bad = [{**valid, "input_basis": True}, {**valid, "method": []}, {**valid, "method": "unknown"},
               {**valid, "inputs": []}, {**valid, "input_basis": " "}, {**valid, "passed": True}]
        result = self.check({**self.payload, "stage": "change", "pressure_checks": bad + [valid]})
        self.assertEqual(result["equipment"][0]["result"]["backend_exit_code"], 0)
        self.assertEqual(len(result["pressure"]), len(bad) + 1)
        self.assertTrue(all(row["status"] == "NOT_EXECUTED_INVALID_INPUT" for row in result["pressure"][:-1]))
        self.assertEqual(result["pressure"][-1]["result"]["checks"][0]["result"]["outlet_pressure_pa"], 450000)
        self.assertEqual(result["status"], "ACTION_REQUIRED")
        self.assertFalse(result["engineering_accepted"])

    def test_missing_inventory_and_lookup_disguised_as_calculation_are_visible(self):
        payload = {**self.payload, "equipment_requests": []}
        result = self.check(payload)
        self.assertIn("PHYSICAL_EQUIPMENT_LIST_REQUIRED", {row["code"] for row in result["needs"]})
        payload["equipment_requests"] = [{"equipment_id": "SYN-E1", "request": {"operation": "catalog", "payload": {}}}]
        result = self.check(payload)
        self.assertIn("PER_DEVICE_CALCULATION_REQUIRED", {row["code"] for row in result["needs"]})
        self.assertEqual(self.requests, [])

    def test_no_knowledge_hits_is_not_hidden(self):
        result = self.check(search=lambda **kwargs: {"knowledge": {"results": []}})
        self.assertEqual(result["status"], "ACTION_REQUIRED")
        self.assertEqual(len([row for row in result["needs"] if row["code"] == "NO_KNOWLEDGE_NODE_HITS"]), 2)
        self.assertEqual(len(self.requests), 1)

    def test_boolean_skip_old_results_and_json_runners_cannot_advance_stage(self):
        for key, value in (("skip", True), ("passed", True), ("results", {"old": "PASS"}),
                           ("search_runner", "replace"), ("equipment_runner", "replace")):
            with self.subTest(field=key), self.assertRaises(ValueError):
                self.check({**self.payload, key: value})

    def test_reconnect_and_change_require_current_pressure_recalculation(self):
        for stage in ("reconnect", "change"):
            with self.subTest(stage=stage):
                result = self.check({**self.payload, "stage": stage})
                self.assertIn("CURRENT_PRESSURE_RECALCULATION_REQUIRED", {row["code"] for row in result["needs"]})
                self.assertEqual(result["equipment"][0]["result"]["backend_exit_code"], 0)
                check = {"method": "series_pressure", "input_basis": "SYNTHETIC absolute Pa, not native simulation",
                         "inputs": {"inlet_pressure_pa": 500000, "losses_pa": [20000, 30000]}}
                result = self.check({**self.payload, "stage": stage, "pressure_checks": [check]})
                self.assertEqual(result["pressure"][0]["result"]["checks"][0]["result"]["outlet_pressure_pa"], 450000)
                self.assertEqual(result["recalculation"]["state"], "NATIVE_FLOWSHEET_RERUN_REQUIRED")
                self.assertFalse(result["engineering_accepted"])

    def test_delivery_runs_existing_replay_validator_and_rejects_boolean_pass(self):
        plan = self.check()["equipment"][0]["feedback"]["result"]
        candidate = self.put("synthetic_not_aspen.json", {"synthetic": True})
        replay = {"case_id": self.identity["case_id"], "run_id": self.identity["run_id"], "source_export": self.identity["source_export"],
                  "candidate": candidate, "plan_sha256": plan["plan_sha256"], "gates": {}, "passed": True}
        result = self.check({**self.payload, "stage": "delivery", "plan": plan, "replay": replay})
        self.assertEqual(result["replay"]["kind"], "process_replay_audit")
        self.assertEqual(len(result["replay"]["result"]["failed_gates"]), 11)
        self.assertFalse(result["engineering_accepted"])
        self.assertEqual(result["status"], "ACTION_REQUIRED")

    def test_delivery_without_changed_topology_does_not_invent_a_feedback_plan(self):
        result = self.check({**self.payload, "stage": "delivery"})
        self.assertEqual(result["replay"]["status"], "NOT_REQUESTED")
        self.assertFalse(any(row["kind"] == "process_replay_audit" for row in result["calls"]))
        self.assertTrue(any("aspen-plus-operations" in row["logical_path"] for row in result["domain_reads"]))
        self.assertFalse(result["engineering_accepted"])

    def test_unrelated_exported_equipment_is_not_forced_into_island_calculation(self):
        exported = copy.deepcopy(self.export)
        exported["equipment"]["SYN-OTHER-ISLAND"] = copy.deepcopy(exported["equipment"]["SYN-E1"])
        result = self.check({**self.payload, "source_export": self.put("fullplant_export.json", exported)})
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(result["inventory_coverage"]["exported_not_requested"], ["SYN-OTHER-ISLAND"])
        self.assertFalse(result["inventory_coverage"]["independently_verified_complete"])
        self.assertFalse(any(row["code"] == "EXPORTED_DEVICES_NOT_REQUESTED" for row in result["needs"]))

    def test_malformed_source_inventory_keeps_unaffected_calculation(self):
        exported = {**self.export, "equipment": ["not a canonical map"]}
        result = self.check({**self.payload, "source_export": self.put("bad_export.json", exported)})
        self.assertEqual(result["equipment"][0]["result"]["backend_exit_code"], 0)
        self.assertEqual(result["status"], "ACTION_REQUIRED")
        self.assertIn("CURRENT_REFERENCE_NOT_BOUND", {row["code"] for row in result["needs"]})

    def test_source_opt_in_detail_preserves_l3_first_and_task_question(self):
        self.check({"stage": "source", "question": "计算换热面积多少", "detail": True})
        self.assertEqual(self.queries[0]["node_id"], "L3-03")
        self.assertEqual([row["detail"] for row in self.queries], [False, False, True])
        self.assertEqual(self.queries[1]["query"], "计算换热面积多少")

    def real_cli(self, requests, *, jsonl=False):
        guard = self.root / "qa_guard.py"
        guard.write_text(GUARD_SOURCE, encoding="utf-8")
        bootstrap = self.root / "bootstrap.py"
        bootstrap.write_text(BOOTSTRAP_SOURCE, encoding="utf-8")
        (self.root / "child_source.txt").write_text(CHILD_SOURCE, encoding="utf-8")
        env = {**os.environ, "ENTRYPOINT_GUARD_DIR": str(self.root), "ENTRYPOINT_FORBIDDEN_ROOTS": os.environ.get("STANDALONE_FORBIDDEN_ROOTS", "[]"),
               "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1", "CODEX_HOME": str(self.root / "empty_codex")}
        env.pop("PYTHONPATH", None)
        args = [sys.executable, "-B", "-X", "utf8", str(bootstrap), str(ROOT), str(guard), str(ROOT / "tools/expert_cli.py"), "--evidence-root", str(self.root)]
        if jsonl:
            args += ["--session-jsonl"]
            content = "\n".join(json.dumps(item) for item in requests) + "\n"
        else:
            args += ["--request", "-"]
            content = json.dumps(requests[0])
        result = subprocess.run(args, input=content, capture_output=True, text=True, encoding="utf-8", timeout=120, env=env, cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        events = [json.loads(line) for path in self.root.glob("guard-*.jsonl") for line in path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([row for row in events if row["kind"].endswith("_blocked") and not row["negative_control"]], [])
        self.assertTrue(any(row["kind"] == "gateway_closed" and row["detail"]["returncode"] == 0 for row in events))
        return [json.loads(line) for line in result.stdout.splitlines()] if jsonl else [json.loads(result.stdout)]

    def test_real_search_gateway_feedback_and_jsonl_entrypoints(self):
        requests = [{"operation": "design_stage", "payload": {"stage": "source", "question": "高温公用工程 预热 压缩"}},
                    {"operation": "design_stage", "payload": self.payload}]
        source, equipped = self.real_cli(requests, jsonl=True)
        self.assertEqual(len(source["queries"]), 2)
        self.assertEqual(source["queries"][0]["returned_nodes"][0]["node_id"], "L3-03")
        self.assertTrue(source["queries"][0]["returned_nodes"])
        core = equipped["equipment"][0]["result"]["response"]["result"]["result"]
        self.assertEqual(core["derived_parameters"]["heat_transfer_area_m2"], 50)
        self.assertTrue(core["calculations"])
        self.assertEqual(equipped["equipment"][0]["feedback"]["result"]["equipment"][0]["binding_gaps"], [])
        worker = equipped["equipment"][0]["result"]["gateway"]["worker_pid"]
        discovery = next(row for row in source["calls"] if row["kind"] == "equipment_capabilities")
        self.assertEqual(discovery["result"]["gateway"]["worker_pid"], worker)
        self.assertNotEqual(source["execution_id"], equipped["execution_id"])
        self.assertFalse(equipped["engineering_accepted"])
        self.assertFalse(equipped["inventory_coverage"]["independently_verified_complete"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
