"""Check the actual planning validation before handing an authorized run to Aspen."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from test_buildable_plan import IntegratedBuildableFixture
from tools.design_stage import check_stage, run_buildable_first_scaffold
from tools.fullflow_gate import _Gate, _pressure_reading


class HandoffConsistencyTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.case = IntegratedBuildableFixture(self.root)

    def stage(self, payload):
        def knowledge(**request):
            return {"knowledge": {"results": [{"node_id": request.get("node_id", "test-node"), "knowledge_layer": "L3"}]}}

        return check_stage(payload, self.root, search_runner=knowledge,
                           equipment_runner=lambda request: {"backend_exit_code": 0, "response": {"result": {}}})

    def both(self):
        payload = {"stage": "source", "source_work": "buildable_plan", "question": "核对工程规划",
                   "fullflow_contract": self.case.put("case.json", self.case.contract)}
        normal = self.stage(payload)
        native = Mock(return_value="test callback")
        with patch("tools.expert_cli.execute", side_effect=lambda request, root: self.stage(request["payload"])):
            first = run_buildable_first_scaffold(payload, self.root, run_native=native)
        self.assertEqual(normal["status"], first["planning_stage_status"])
        return normal, first, native

    def test_one_bound_handoff_and_planning_limit_are_enough(self):
        normal, first, native = self.both()
        self.assertFalse(normal["needs"], normal["needs"])
        self.assertTrue(normal["fullflow_gate"]["gate_summary"]["planning_verification_limits"])
        self.assertTrue(normal["expert_planning"]["check_result"]["reaction_derivations_checked"])
        native.assert_called_once_with()

    def test_absent_expert_sections_do_not_pass_either_entry(self):
        gate = self.case.contract["source_gate"]
        data = self.case.read(gate["handoff_input_ref"])
        del data["expert_plan"]
        gate["handoff_input_ref"] = self.case.put("handoff-input.json", data)
        normal, first, native = self.both()
        self.assertIn("BUILDABLE_HANDOFF_CHECK_INCOMPLETE", {n["code"] for n in normal["needs"]})
        self.assertFalse(first["native_run_invoked"])
        native.assert_not_called()

    def test_explicitly_future_study_keeps_route_and_does_not_require_a_study_run(self):
        p = {"stage": "source", "source_work": "buildable_plan", "question": "完整流程规划，后续切岛优化温度，本次只交规划文章",
             "fullflow_contract": self.case.put("case.json", self.case.contract)}
        result = self.stage(p)
        self.assertEqual(result["solve_route"].get("execution_scope"), "AFTER_FIRST_MODEL")
        self.assertFalse(result["needs"], result["needs"])
        p["question"] += "；现在要执行参数扫描"
        self.assertIn("SOLVE_TOOL_ACTION_REQUIRED", {n["code"] for n in self.stage(p)["needs"]})

    def test_malformed_optional_module_data_keeps_actionable_diagnostics(self):
        self.case.contract["modules"] = None
        normal, first, native = self.both()
        self.assertEqual(normal["status"], "ACTION_REQUIRED")
        self.assertTrue(first["needs"])
        native.assert_not_called()

    def test_direct_feed_requires_sufficient_pressure_on_same_basis(self):
        module = {"id": "R", "role": "reaction", "node_ids": ["R"], "first_model": {"block_type": "RStoic"},
                  "reaction": {"conditions": [{"name": "pressure", "unit_or_basis": "MPa(a)", "value": 0.4}]},
                  "auxiliary_requirements": {key: {"state": "not_required"}
                                             for key in ("compression", "pumping", "pressure_control")}}
        gate = _Gate({}, self.root, {})
        for pressure in ({"value": 4, "unit_or_basis": "bar(a)"}, {"value": 350, "unit_or_basis": "kPa(g)"}):
            gate.check_direct_reactor_pressure(module, pressure, "R", "external-feed")
        self.assertFalse(gate.needs)
        gate.check_direct_reactor_pressure(module, {"value": 300, "unit_or_basis": "kPa(a)"}, "R", "external-feed")
        self.assertEqual([item["code"] for item in gate.needs], ["PLAN_FEED_PRESSURE_SHORTFALL"])
        self.assertEqual(_pressure_reading({"value": 3, "unit_or_basis": "bar(g)"}), (300000, "gauge"))
