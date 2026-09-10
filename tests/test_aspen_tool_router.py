"""Finite routing invariants and real CLI integration; no live-agent/Aspen claim."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SOURCE_ROOT = Path(__file__).resolve().parents[1]
ROOT = Path(os.environ.get("STANDALONE_PRODUCT_ROOT", SOURCE_ROOT)).resolve()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SOURCE_ROOT / "tests"))
from tools.aspen_tool_router import INTENTS, solve_route
from tools import expert_cli, product_contract
import test_design_stage as stage_fixtures


class AspenToolRouterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="synthetic-solve-route-")
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def route(self, *intents, question="Synthetic routing request", **values):
        return solve_route({"question": question, "intents": list(intents), **values}, self.root)

    def tools(self, result):
        return [tool for route in result["routes"] for tool in route["tools"]]

    def ref(self, name):
        data = b'{"synthetic":true,"not_authorization":true}'
        (self.root / name).write_bytes(data)
        return {"path": name, "sha256": hashlib.sha256(data).hexdigest()}

    def test_read_value_does_not_add_calculator_or_equipment(self):
        with mock.patch.object(expert_cli, "EquipmentSession", side_effect=AssertionError("Unexpected equipment session")):
            result = expert_cli.execute({"operation": "solve_route", "payload": {"question": "读取物流焓", "intents": ["read_value"]}}, self.root,
                equipment_runner=mock.Mock(side_effect=AssertionError("Unexpected equipment call")))
        self.assertIn("EXISTING_OUTPUT_READBACK", self.tools(result))
        self.assertFalse(any("CALCULATOR" in tool for tool in self.tools(result)))
        self.assertFalse(result["native_tools_executed"])

    def test_one_off_algebra_does_not_insert_calculator(self):
        self.assertEqual(self.tools(self.route("derive_once")), ["DETERMINISTIC_DERIVATION"])

    def test_live_relation_routes_to_native_calculator_with_dependency_evidence(self):
        result = self.route("live_relation")
        self.assertEqual(self.tools(result), ["NATIVE_CALCULATOR"])
        self.assertTrue(any("READ-VARS" in item for item in result["routes"][0]["evidence"]))
        self.assertIn("execution point", result["routes"][0]["requires"])

    def test_range_scan_is_native_not_vendor_sweep(self):
        result = self.route("scan_range")
        self.assertEqual(self.tools(result), ["NATIVE_SENSITIVITY"])
        self.assertEqual(result["vendor_sensitivity"]["classification"], "EXTERNAL_POINT_SWEEP_NOT_NATIVE")
        self.assertFalse(result["vendor_sensitivity"]["native_sensitivity_evidence"])

    def test_study_context_same_targets_requires_inner_control_review(self):
        context = {"mode": "same_targets", "varied_variables": ["COMP/PRES"],
                   "fixed_conditions": ["CURRENT_PROPERTY_METHOD"], "maintained_targets": ["product purity"],
                   "inner_controls": []}
        result = self.route("scan_range", study_context=context)
        self.assertEqual(result["study"]["status"], "AGENT_REVIEW_REQUIRED")
        self.assertEqual(result["study"]["comparison_mode"], "same_targets")
        self.assertIn("inner_controls_or_passive_target_justification", result["study"]["missing_parts"])
        self.assertEqual(result["study"]["inner_control_policy"], "CLASSIFY_COMPARISON_FIRST")
        self.assertFalse(result["decision_chain"]["execution_proven"])

    def test_study_context_fixed_controls_does_not_claim_same_target_comparison(self):
        context = {"mode": "fixed_controls", "varied_variables": ["COMP/PRES"],
                   "fixed_conditions": ["S1", "S2"], "maintained_targets": ["power"],
                   "inner_controls": ["none"]}
        result = self.route("scan_range", study_context=context)
        self.assertEqual(result["study"]["comparison_mode"], "fixed_controls")
        self.assertEqual(result["study"]["inner_control_policy"], "KEEP_DECLARED_SETTINGS")
        self.assertNotEqual(result["study"]["inner_control_policy"], "RE_SOLVE_AUTHORIZED_TARGET_CONTROLS")
        self.assertEqual(result["study"]["declaration"], context)

    def test_missing_study_context_is_review_need_not_pass(self):
        result = self.route("match_target")
        self.assertEqual(result["study"]["status"], "AGENT_REVIEW_REQUIRED")
        self.assertIn("study_context", [item["scope"] for item in result["needs"]
                                         if item["code"] == "STUDY_CONTEXT_REVIEW_REQUIRED"])
        self.assertFalse(result["engineering_accepted"])
        self.assertFalse(result["native_tools_executed"])

    def test_illegal_study_context_self_reported_pass_is_rejected(self):
        context = {"mode": "same_targets", "passed": True}
        with self.assertRaises(ValueError):
            self.route("scan_range", study_context=context)

    def test_read_value_uses_pure_lookup_chain_without_study(self):
        result = self.route("read_value")
        self.assertEqual(result["study"]["status"], "NOT_APPLICABLE")
        self.assertEqual([step["id"] for step in result["decision_chain"]["steps"]],
                         ["define_engineering_question", "use_current_results_or_derive"])

    def test_diagnose_orders_failure_classification_before_interface_probe(self):
        result = self.route("diagnose", question="收敛失败，先诊断压缩机")
        ids = [step["id"] for step in result["decision_chain"]["steps"]]
        self.assertLess(ids.index("classify_failure_before_interface_probe"),
                        ids.index("verify_native_definition_and_current_execution"))

    def test_receipt_changes_when_study_context_changes(self):
        base = {"mode": "same_targets", "varied_variables": ["PRES"],
                "fixed_conditions": [], "maintained_targets": ["purity"], "inner_controls": ["reflux"]}
        a = self.route("scan_range", study_context=base)
        b = self.route("scan_range", study_context={**base, "varied_variables": ["TEMPERATURE"]})
        self.assertNotEqual(a["receipt_sha256"], b["receipt_sha256"])

    def test_complete_same_target_declaration_requires_resolve_but_is_not_verified(self):
        result = self.route("scan_range", study_context={"mode": "same_targets",
            "varied_variables": ["pressure"], "fixed_conditions": ["current feed"],
            "maintained_targets": ["contract product requirements"], "inner_controls": ["authorized reflux"]})
        self.assertEqual(result["study"]["inner_control_policy"], "RE_SOLVE_AUTHORIZED_TARGET_CONTROLS")
        self.assertEqual(result["study"]["missing_parts"], [])
        self.assertFalse(result["study"]["semantic_verified"])
        self.assertFalse(result["native_tools_executed"])

    def test_invalid_context_types_and_whitespace_are_rejected(self):
        for value in (None, [], {"mode": True}, {"mode": "approved"}, {"inner_controls": True},
                      {"varied_variables": [3]}, {"maintained_targets": ["  "]}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.route("scan_range", study_context=value)

    def test_control_relationship_question_triggers_engineering_diagnosis_without_tool_name(self):
        result = solve_route({"question": "你看看是不是控制变量缺失"}, self.root)
        self.assertIn("diagnose", result["classification"]["intents"])
        self.assertFalse(result["classification"]["semantic_completeness"])
        self.assertIn("classify_failure_before_interface_probe", [s["id"] for s in result["decision_chain"]["steps"]])

    def test_feedback_is_pending_and_not_injected_into_simple_lookup(self):
        study = self.route("scan_range")
        signals = {row["signal"] for row in study["decision_chain"]["feedback_triggers"]}
        self.assertIn("local_objective_improves_but_required_gate_fails", signals)
        self.assertIn("best_sample_near_failed_boundary", signals)
        self.assertFalse(study["decision_chain"]["feedback_events_evaluated"])
        self.assertEqual(self.route("read_value")["decision_chain"]["feedback_triggers"], [])

    def test_stage_passes_study_context_without_replacing_identity_or_equipment(self):
        fixture = stage_fixtures.DesignStageTests()
        fixture.setUp()
        try:
            fixture.payload["question"] = "扫描操作范围"
            declared = {"mode": "fixed_controls", "varied_variables": ["pressure"], "fixed_conditions": ["reflux"]}
            fixture.payload["solve_request"] = {"intents": ["scan_range"], "study_context": declared}
            result = fixture.check()
            routed = result["solve_route"]["result"]
            self.assertEqual(routed["question"], fixture.payload["question"])
            self.assertEqual(routed["study"]["declaration"], declared)
            self.assertEqual(routed["study"]["inner_control_policy"], "KEEP_DECLARED_SETTINGS")
            self.assertEqual(fixture.requests, [fixture.native])
            self.assertFalse(result["engineering_accepted"])
        finally:
            fixture.tearDown()

    def test_target_match_keeps_bracket_reuse_and_real_vary(self):
        result = self.route("match_target")
        self.assertEqual(self.tools(result), ["REUSE_SAME_CASE_BRACKET_OR_NATIVE_SENSITIVITY", "NATIVE_DESIGN_SPEC_VARY"])
        self.assertIn("target residual/status", result["routes"][0]["evidence"])

    def test_continuous_objective_routes_native_with_inner_quality_specs(self):
        result = self.route("optimize", question="多连续变量目标约束优化")
        self.assertIn("NATIVE_OPTIMIZATION", self.tools(result))
        self.assertIn("INNER_DESIGN_SPECS_WHEN_REQUIRED", self.tools(result))
        self.assertFalse(any(tool.startswith("EXTERNAL") for tool in self.tools(result)))

    def test_multiple_variables_without_objective_requires_classification(self):
        for question in ("多个连续变量复杂调参", "多参数调一调", "几个参数怎么调"):
            result = solve_route({"question": question}, self.root)
            self.assertEqual(result["status"], "AGENT_CLASSIFICATION_REQUIRED")
            self.assertTrue(result["strong_trigger"])
            self.assertEqual(self.tools(result), [])

    def test_finite_chinese_task_examples_route_without_tool_names(self):
        for question, intent in (("查询特殊值", "read_value"), ("第12板温度是多少", "read_value"),
            ("进料变化时自动补充溶剂", "live_relation"), ("补料随进料变", "live_relation"),
            ("找到刚好满足要求的回流", "match_target"), ("比较两种流程与不同并联台数", "discrete_scenarios")):
            with self.subTest(question=question):
                result = solve_route({"question": question}, self.root)
                self.assertIn(intent, result["classification"]["intents"])
                self.assertFalse(result["classification"]["semantic_completeness"])

    def test_read_value_loads_only_relevant_owner_and_operation_graph(self):
        result = self.route("read_value")
        self.assertEqual(len(result["required_reading"]), 2)
        self.assertFalse(any(item["logical_path"].endswith("operations_workflow.md") for item in result["required_reading"]))
        self.assertTrue(all(item["reading_scope"] == "RELEVANT_SECTION" for item in result["required_reading"]))

    def test_discrete_outer_loop_preserves_native_inner_methods(self):
        result = self.route("discrete_scenarios")
        self.assertIn("EXTERNAL_DISCRETE_ORCHESTRATION", self.tools(result))
        self.assertIn("APPLICABLE_NATIVE_TOOLS_WITHIN_EACH_SCENARIO", self.tools(result))
        self.assertFalse(result["external_request"]["execution_authorized"])

    def test_fitting_requires_source_data_and_current_authority(self):
        result = self.route("fit_data")
        self.assertIn("FIT_DATA_AND_AUTHORITY_REQUIRED", [item["code"] for item in result["needs"]])
        self.assertFalse(result["fitting"]["authorized"])

    def test_hash_correct_fake_fit_authority_does_not_authorize(self):
        result = self.route("fit_data", fit_data=self.ref("data.json"), fit_authority=self.ref("authority.json"))
        self.assertTrue(result["fitting"]["fit_authority"]["hash_verified"])
        self.assertFalse(result["fitting"]["authorized"])
        self.assertEqual(result["fitting"]["status"], "DATA_AND_AUTHORITY_SEMANTIC_REVIEW_REQUIRED")

    def test_external_reason_and_correct_hash_never_approve_substitution(self):
        for evidence in ([], [self.ref("external.json")]):
            result = self.route("optimize", external_request={"reason": "Native tools are inconvenient", "evidence": evidence})
            self.assertFalse(result["external_request"]["execution_authorized"])
            self.assertEqual(result["external_request"]["status"], "DOMAIN_REVIEW_REQUIRED")
            self.assertTrue(result["external_request"]["native_assessment_required"])

    def test_no_self_reported_pass_or_runner_or_unknown_intent(self):
        for payload in ({"question": "x", "passed": True}, {"question": "x", "skip": True},
                        {"question": "x", "runner": "custom"}, {"question": "x", "intents": [True]},
                        {"question": "x", "intents": [[]]}, {"question": "x", "intents": ["external_optimizer"]},
                        {"question": "x", "external_request": {"reason": "ok", "evidence": [], "approved": True}}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                solve_route(payload, self.root)

    def test_unknown_language_and_conflicting_explicit_intent_are_not_semantic_proof(self):
        unknown = solve_route({"question": "分析这个事情"}, self.root)
        self.assertEqual(unknown["status"], "AGENT_CLASSIFICATION_REQUIRED")
        conflict = self.route("read_value", question="优化公用工程目标")
        self.assertEqual(conflict["status"], "AGENT_CLASSIFICATION_REQUIRED")
        self.assertIn("optimize", conflict["classification"]["conflicts"])
        self.assertFalse(conflict["classification"]["semantic_completeness"])

    def test_all_routes_are_pending_and_actual_reference_paths_exist(self):
        for intent in INTENTS:
            result = self.route(intent)
            self.assertTrue(all(Path(item["path"]).is_file() for item in result["required_reading"]))
            for key in ("engineering_accepted", "native_tools_created", "native_tools_executed", "native_evidence_verified", "flowsheet_modified", "stage_advanced"):
                self.assertIs(result[key], False)

    def test_contract_is_discoverable_without_backend(self):
        result = product_contract.schema("solve-route", mock.Mock(side_effect=AssertionError("Unexpected backend")))
        self.assertEqual(set(result["properties"]["intents"]["items"]["enum"]), set(INTENTS))
        study = result["properties"]["study_context"]
        self.assertFalse(study["additionalProperties"])
        self.assertEqual(set(study["properties"]), {"mode", "varied_variables", "fixed_conditions", "maintained_targets", "inner_controls"})
        self.assertEqual(product_contract.schema("design-stage", None)["properties"]["solve_request"]["properties"]["study_context"], study)
        self.assertIn("solve_request", product_contract.schema("design-stage", None)["properties"])

    def test_stage_strong_trigger_calls_router_but_keeps_declared_equipment_calls(self):
        fixture = stage_fixtures.DesignStageTests()
        fixture.setUp()
        try:
            fixture.payload["question"] = "达到产品纯度目标"
            result = fixture.check()
            self.assertEqual(result["solve_route"]["status"], "EXECUTED")
            self.assertIn("NATIVE_DESIGN_SPEC_VARY", self.tools(result["solve_route"]["result"]))
            self.assertEqual(fixture.requests, [fixture.native])
            self.assertEqual(len(fixture.queries), 2)
            self.assertIn("SOLVE_TOOL_ACTION_REQUIRED", [item["code"] for item in result["needs"]])
            self.assertTrue(any(item["logical_path"].endswith("aspen_builtin_solve_fit_tools.md") for item in result["domain_reads"]))
        finally:
            fixture.tearDown()

    def test_ordinary_source_not_forced_to_solve_or_fake_equipment(self):
        fixture = stage_fixtures.DesignStageTests()
        fixture.setUp()
        try:
            result = fixture.check({"stage": "source", "question": "文本流程与系统边界"})
            self.assertEqual(result["status"], "MODULE_CHECKS_EXECUTED")
            self.assertEqual(result["equipment"], [])
            self.assertEqual(result["solve_route"]["result"]["status"], "AGENT_CLASSIFICATION_REQUIRED")
            self.assertFalse(any(item["logical_path"].endswith("aspen_builtin_solve_fit_tools.md") for item in result["domain_reads"]))
        finally:
            fixture.tearDown()

    def test_bad_solve_request_is_local_and_cannot_replace_current_question(self):
        fixture = stage_fixtures.DesignStageTests()
        fixture.setUp()
        try:
            for bad in ([], {"question": "other"}, {"skip": True}):
                fixture.payload["solve_request"] = bad
                result = fixture.check()
                self.assertEqual(result["equipment"][0]["status"], "EXECUTED")
                self.assertEqual(result["status"], "ACTION_REQUIRED")
        finally:
            fixture.tearDown()

    def test_real_cli_works_without_equipment_or_com_process(self):
        bootstrap = r'''import json, os, pathlib, runpy, sys
forbidden = [pathlib.Path(p).resolve() for p in json.loads(os.environ.get('STANDALONE_FORBIDDEN_ROOTS', '[]'))]
def audit(event, args):
    if event.startswith('socket.') or event == 'subprocess.Popen': raise PermissionError(event)
    if event == 'import' and str(args[0]).split('.')[0] in {'pythoncom','win32com','comtypes'}: raise PermissionError(event)
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        path = pathlib.Path(os.fsdecode(args[0])).resolve()
        if any(path == p or p in path.parents for p in forbidden): raise PermissionError('Forbidden source')
sys.addaudithook(audit)
for event,args in [('socket.connect',(None,('example.invalid',80))),('import',('pythoncom',None,None,None,None)),('subprocess.Popen',('forbidden',[],None,None))]:
    try: sys.audit(event,*args)
    except PermissionError: pass
    else: raise AssertionError('Guard inactive')
sys.argv=[sys.argv[1], '--request', '-']
runpy.run_path(sys.argv[0],run_name='__main__')
'''
        completed = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", bootstrap, str(ROOT / "tools/expert_cli.py")],
            input=json.dumps({"operation": "solve_route", "payload": {"question": "读取当前物流的焓", "intents": ["read_value"]}}),
            text=True, encoding="utf-8", capture_output=True, cwd=self.root, timeout=20)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertIn("EXISTING_OUTPUT_READBACK", self.tools(result))
        self.assertFalse(result["native_tools_executed"])

    def test_public_example_executes_through_current_cli(self):
        example = SOURCE_ROOT / "examples/solve_route_request.json"
        completed = subprocess.run([sys.executable, "-B", "-X", "utf8", str(ROOT / "tools/expert_cli.py"), "--request", "-"],
            input=example.read_text(encoding="utf-8"), text=True, encoding="utf-8", capture_output=True, cwd=self.root, timeout=20)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["schema"], "aspen-solve-route-v1")
        self.assertTrue(result["routes"])
        self.assertFalse(result["native_tools_executed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
