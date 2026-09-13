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

    def test_pressure_summary_preserves_request_error_and_later_calculation(self):
        valid = {"method": "series_pressure", "input_basis": "Synthetic absolute Pa; local screen only",
                 "inputs": {"inlet_pressure_pa": 500000, "losses_pa": [20000]}}
        wrong = copy.deepcopy(valid)
        wrong["inputs"]["outlet_pressure_pa"] = 480000
        result = self.check({**self.payload, "stage": "change", "pressure_checks": [wrong, valid]})
        summary = result["execution_summary"]["pressure_checks"]
        self.assertEqual(summary[0]["call_status"], "EXECUTED")
        failed = summary[0]["check_results"][0]
        self.assertEqual(failed["status"], "LOCAL_CALCULATION_GAP")
        self.assertIn("unexpected keyword argument", failed["reason"])
        self.assertIn("outlet_pressure_pa", failed["reason"])
        self.assertEqual(failed["reason"], result["pressure"][0]["result"]["checks"][0]["reason"])
        self.assertFalse(failed["result_present"])
        self.assertTrue(summary[1]["check_results"][0]["result_present"])
        self.assertEqual(result["pressure"][1]["result"]["checks"][0]["result"]["outlet_pressure_pa"], 480000)
        self.assertEqual(result["status"], "ACTION_REQUIRED")
        self.assertFalse(result["engineering_accepted"])

    def test_no_knowledge_hits_is_not_hidden(self):
        result = self.check(search=lambda **kwargs: {"knowledge": {"results": []}})
        self.assertEqual(result["status"], "ACTION_REQUIRED")
        self.assertEqual(len([row for row in result["needs"] if row["code"] == "NO_KNOWLEDGE_NODE_HITS"]), 2)
        self.assertEqual(len(self.requests), 1)

    def test_boolean_skip_old_results_and_json_runners_cannot_advance_stage(self):
        for key, value in (("skip", True), ("passed", True), ("results", {"old": "PASS"}),
                           ("search_runner", "replace"), ("equipment_runner", "replace"),
                           ("approved", True), ("planning_requirements", {"execution_status": "COMPLETED"})):
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

    def test_change_without_model_preserves_needs_without_claiming_a_plan_or_writing_files(self):
        before = {p.name: p.read_bytes() for p in self.root.iterdir() if p.is_file()}
        payload = {"stage": "change", "question": "冷却后相态改变，先核查当前假设"}
        original = copy.deepcopy(payload)
        result = self.check(payload)
        plan = result["planning_requirements"]
        self.assertEqual(plan["status"], "PLANNING_REQUIREMENTS_ONLY")
        self.assertEqual(plan["execution_status"], "NOT_EXECUTED")
        self.assertFalse(plan["authorization_granted_by_receipt"])
        self.assertFalse(plan["project_specific_plan_complete"])
        self.assertEqual(plan["input_identity"], {key: None for key in self.identity})
        self.assertEqual(plan["hash_bound_reference_names"], [])
        self.assertEqual(plan["unresolved_needs"], result["needs"])
        self.assertTrue(plan["unresolved_needs"])
        for field in ("native_baseline", "protected_candidate", "selected_change"):
            self.assertIsNone(plan[field])
        self.assertEqual(result["status"], "ACTION_REQUIRED")
        self.assertEqual([row["kind"] for row in result["calls"]],
                         ["knowledge_search", "knowledge_search", "aspen_solve_route"])
        self.assertEqual(self.requests, [])
        self.assertEqual(payload, original)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir() if p.is_file()})

    def test_change_with_valid_inputs_does_not_turn_planning_into_acceptance(self):
        pressure = {"method": "series_pressure", "input_basis": "SYNTHETIC absolute Pa, not native simulation",
                    "inputs": {"inlet_pressure_pa": 500000, "losses_pa": [20000, 30000]}}
        result = self.check({**self.payload, "stage": "change", "pressure_checks": [pressure]})
        plan = result["planning_requirements"]
        self.assertEqual(plan["input_identity"], self.identity)
        self.assertEqual(plan["hash_bound_reference_names"], ["authority", "source_export"])
        self.assertEqual(plan["identity_status"], "HASH_BOUND_CURRENT_CANONICAL_DOCUMENTS")
        self.assertEqual(plan["stage_execution_id"], result["execution_id"])
        self.assertEqual(plan["unresolved_needs"], result["needs"])
        self.assertEqual(result["equipment"][0]["result"]["backend_exit_code"], 0)
        self.assertEqual(result["pressure"][0]["result"]["checks"][0]["result"]["outlet_pressure_pa"], 450000)
        self.assertFalse(result["engineering_accepted"])
        self.assertFalse(result["flowsheet_modified"])
        self.assertFalse(result["stage_advanced"])
        self.assertFalse(plan["authorization_granted_by_receipt"])
        self.assertIsNone(plan["native_baseline"])
        self.assertEqual(plan["execution_status"], "NOT_EXECUTED")

    def test_unbound_reference_is_not_promoted_by_planning_and_other_stages_do_not_get_it(self):
        bad = {**self.identity["source_export"], "sha256": "0" * 64}
        result = self.check({**self.payload, "stage": "change", "source_export": bad})
        plan = result["planning_requirements"]
        self.assertEqual(plan["input_identity"]["source_export"], bad)
        self.assertEqual(plan["hash_bound_reference_names"], ["authority"])
        self.assertIn("CURRENT_REFERENCE_NOT_BOUND", {n["code"] for n in plan["unresolved_needs"]})
        self.assertEqual(result["status"], "ACTION_REQUIRED")
        for stage in ("source", "scaffold", "island", "reconnect", "delivery"):
            with self.subTest(stage=stage):
                self.assertNotIn("planning_requirements", self.check({**self.payload, "stage": stage}))

    def test_mismatched_question_keeps_failure_and_both_questions_without_auto_retry(self):
        payload = {"stage": "change", "question": "当前相态变化需要诊断",
                   "solve_request": {"question": "另一工况的优化问题", "intents": ["diagnose"]}}
        original = copy.deepcopy(payload)
        result = self.check(payload)
        solve = result["solve_route"]
        summary = result["execution_summary"]
        self.assertEqual(solve["status"], "FAILED")
        self.assertNotIn("result", solve)
        self.assertEqual(solve["request_conflict"]["current_stage_question"], payload["question"])
        self.assertEqual(solve["request_conflict"]["nested_solve_question"], payload["solve_request"]["question"])
        self.assertIn("继承当前阶段问题", solve["request_conflict"]["repair_hint"])
        need = next(n for n in result["needs"] if n["code"] == "SOLVE_REQUEST_INVALID")
        self.assertEqual(need["detail"]["current_stage_question"], payload["question"])
        self.assertEqual(summary["stage_status"], result["status"])
        self.assertEqual(summary["solve_call_status"], "FAILED")
        self.assertEqual(summary["solve_result_status"], "NOT_AVAILABLE")
        self.assertEqual(summary["solve_call_error"], solve["error"])
        self.assertIsNone(summary["solve_result_error"])
        self.assertFalse(any(c["kind"] == "aspen_solve_route" for c in result["calls"]))
        self.assertEqual(payload, original)
        self.assertFalse(result["engineering_accepted"])

    def test_nonobject_solve_request_is_rejected_without_inventing_question_conflict(self):
        result = self.check({"stage": "change", "question": "当前变化诊断", "solve_request": []})
        self.assertEqual(result["status"], "ACTION_REQUIRED")
        self.assertEqual(result["solve_route"]["status"], "FAILED")
        self.assertNotIn("request_conflict", result["solve_route"])
        self.assertEqual(result["execution_summary"]["solve_result_status"], "NOT_AVAILABLE")
        self.assertFalse(any(c["kind"] == "aspen_solve_route" for c in result["calls"]))
        self.assertIn("SOLVE_REQUEST_INVALID", {n["code"] for n in result["needs"]})

    def test_execution_summary_distinguishes_successful_call_from_unresolved_routing(self):
        for question, status in [("读取当前结果与单位", "ACTION_REQUIRED"),
                                 ("读取当前结果，不优化", "AGENT_CLASSIFICATION_REQUIRED")]:
            with self.subTest(question=question):
                result = self.check({"stage": "change", "question": question,
                                     "solve_request": {"intents": ["read_value"]}})
                summary = result["execution_summary"]
                self.assertEqual(summary["stage"], result["stage"])
                self.assertEqual(summary["stage_status"], result["status"])
                self.assertEqual(summary["solve_call_status"], "EXECUTED")
                self.assertEqual(summary["solve_result_status"], status)
                self.assertEqual(summary["solve_result_status"], result["solve_route"]["result"]["status"])
                self.assertIsNone(summary["solve_call_error"])
                self.assertIsNone(summary["solve_result_error"])
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
                    {"operation": "design_stage", "payload": self.payload},
                    {"operation": "design_stage", "payload": {"stage": "change", "question": "冷却后相态改变，先核查当前假设"}}]
        source, equipped, changed = self.real_cli(requests, jsonl=True)
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
        self.assertEqual(changed["status"], "ACTION_REQUIRED")
        self.assertEqual(changed["planning_requirements"]["execution_status"], "NOT_EXECUTED")
        self.assertEqual(changed["planning_requirements"]["unresolved_needs"], changed["needs"])
        self.assertFalse(changed["planning_requirements"]["authorization_granted_by_receipt"])
        self.assertFalse(changed["planning_requirements"]["project_specific_plan_complete"])
        self.assertFalse(changed["engineering_accepted"])
        self.assertEqual(changed["execution_summary"]["stage_status"], changed["status"])
        self.assertEqual(changed["execution_summary"]["solve_call_status"], changed["solve_route"]["status"])
        self.assertEqual(changed["execution_summary"]["solve_result_status"], changed["solve_route"]["result"]["status"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
