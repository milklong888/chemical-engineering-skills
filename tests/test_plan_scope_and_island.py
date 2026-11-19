"""First-model planning and island acceptance. All values are synthetic."""
import copy
import tempfile
import unittest

from tools.design_stage import check_stage
from tools.fullflow_gate import _Gate, buildable_plan_requested, check_fullflow
from test_buildable_plan import ARTICLE, BuildableInputs
from test_fullflow_gate import FullflowFixture


class PlanScopeTests(unittest.TestCase):
    def test_model_ready_article_requires_review_even_without_running_aspen(self):
        for question in ("写一篇可直接建模的工艺文章，不启动 Aspen", "完整流程规划",
                         "首版工艺流程方案", "第一版流程的全部参数", "Aspen Plus 建立简化稳态模型",
                         "prepare the build-ready flowsheet",
                         "帮我从头设计一套乙醇精制装置，先把各单元首轮输入和物流写清楚，暂时不跑 Aspen",
                         "按题书整理一篇工艺文章，给出的条件要足够让别人直接在 Aspen 里把第一版搭出来"):
            with self.subTest(question=question), tempfile.TemporaryDirectory() as root:
                result = check_fullflow({"stage": "source", "question": question}, root)
                self.assertTrue(result["buildable_plan_required"])
                self.assertEqual(result["status"], "ACTION_REQUIRED")

    def test_stage_preserves_the_actual_scope_of_the_current_work(self):
        cases = [
            ("source", "先画一张全流程方案图，不用定各单元参数", "expert_plan", "expert_plan"),
            ("source", "只讨论全流程方案，不做可直接建模的规划", "expert_plan", "expert_plan"),
            ("source", "准备一份能直接建模的单塔方案，只有 C1", "expert_plan", "expert_plan"),
            ("island", "已有精馏岛，规划可直接建模的 RadFrac 调整", None, None),
            ("island", "校核现有塔岛优化是否符合整厂原目标", None, None),
            ("source", "从题书编写完整流程规划，只交文字，不启动 Aspen", None, "buildable_plan"),
            ("source", "准备可直接建模的完整工艺文章，只交规划", "expert_plan", "buildable_plan"),
        ]
        for stage, question, declared, expected in cases:
            with self.subTest(question=question), tempfile.TemporaryDirectory() as root:
                payload = {"stage": stage, "question": question}
                if declared:
                    payload["source_work"] = declared
                result = check_stage(payload, root, search_runner=lambda **_: {"knowledge": {"results": []}},
                                     equipment_runner=lambda _: {"backend_exit_code": 0})
                self.assertEqual(result["stage"], stage)
                self.assertEqual(result.get("source_work"), expected)
                self.assertEqual(result["fullflow_gate"]["required"], expected == "buildable_plan")

    def test_narrow_work_and_frozen_project_scope(self):
        for question in ("只要一张工艺路线图", "先画一张全流程方案图", "仅解释全流程构建方法",
                         "explain full-flow modeling", "read temperatures from the full flowsheet model"):
            self.assertFalse(buildable_plan_requested({"question": question}), question)
        self.assertTrue(buildable_plan_requested({"question": "沿用上版，准备切岛"},
                                                 {"planning_scope": "buildable_flowsheet"}))
        with tempfile.TemporaryDirectory() as root:
            result = check_fullflow({"stage": "island", "question": "已有塔岛，先优化这一段"}, root,
                                    {"authority": {"workflow_profile": "fullflow_generation"}})
        self.assertTrue(result["buildable_plan_required"])

    def test_quantitative_targets_on_any_module_enter_the_frozen_design_readback(self):
        with tempfile.TemporaryDirectory() as root:
            fixture = BuildableInputs(root)
            excerpt = "At D the maximum accepted pressure is 2 bar."
            fixture.s["targets"] = [{"name": "outlet pressure limit", "value": 2, "unit_or_basis": "bar", "comparison": "le",
                                     "acceptance_tolerance": {"kind": "hard_limit", "value": 0, "unit": "bar",
                                                              "basis": excerpt, "source_ref": fixture.put("limit.txt", excerpt)},
                                     "basis": "pressure at D", "article_excerpt": excerpt, "source_ref": fixture.source}]
            fixture.gate.buildable_plan({"planning_article_ref": fixture.put("plan.md", ARTICLE + excerpt + "\n")})
            self.assertFalse(fixture.gate.needs, fixture.gate.needs)
            self.assertTrue(fixture.gate.buildable_operating_rules["S1"]["targets.0"]["design_target"])

    def test_reported_decimals_must_be_explicit_for_the_same_nominal_target(self):
        clause = "A recovery 90 % at D; for acceptance round half up to 3 decimal places."
        for cmp, excerpt, expected in (("eq", clause, True), ("eq", "A recovery 为90%，验收时四舍五入保留三位小数。", True), ("ge", clause, False),
                                      ("eq", "A recovery 90 % at D.", False),
                                      ("eq", "A recovery 为90%，验收时不得四舍五入保留三位小数。", False),
                                      ("eq", "Example: " + clause, False),
                                      ("eq", clause.replace("3 decimal", "2 decimal"), False)):
            with self.subTest(comparison=cmp, excerpt=excerpt), tempfile.TemporaryDirectory() as root:
                fixture = BuildableInputs(root)
                target = fixture.s["separation"]["targets"][0]
                target.pop("acceptance_tolerance")
                target.update(name="A recovery", comparison=cmp, article_excerpt=excerpt, acceptance_excerpt=excerpt,
                              acceptance_decimals=3)
                fixture.gate.buildable_plan({"planning_article_ref": fixture.put("plan.md", ARTICLE + excerpt + "\n")})
                rule = fixture.gate.buildable_operating_rules["S1"]["separation.targets.0"]
                self.assertEqual(rule.get("acceptance_decimals"), 3 if expected else None)
                self.assertEqual(any(n["code"] == "PLAN_ACCEPTANCE_PRECISION" for n in fixture.gate.needs), not expected)


class IslandSpecificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.gate = _Gate({"stage": "island"}, self.temp.name, {})
        self.gate.buildable_article_ref = {"sha256": "a" * 64}
        self.recovery = "separation.targets.0"
        self.context = {"kind": "recovery", "component": "A", "outlet": "D", "denominator": "all A in M"}
        self.gate.buildable_review_specs = {"SEP": {
            self.recovery: {"value": 95, "unit_or_basis": "%", "basis": "A in net feed", "design_context": self.context},
            "pressure": {"value": 4, "unit_or_basis": "bar(a)", "basis": "gas outlet"},
            "temperature": {"value": "feed flash calculation", "unit_or_basis": "K", "basis": "gas outlet"}}}
        self.gate.buildable_operating_rules = {"SEP": {
            self.recovery: {"mode": "fixed", "comparison": "ge", "design_target": True},
            "pressure": {"mode": "adjustable", "comparison": "eq", "bounds": {"lower": 3, "upper": 5}},
            "temperature": {"mode": "determined", "comparison": "eq"}}}
        self.product_rate = r"\Data\Streams\D\Output\MOLEFLOW\MIXED\A"
        self.feed_rate = r"\Data\Streams\M\Output\MOLEFLOW\MIXED\A"
        self.pressure = r"\Data\Streams\D\Output\PRES_OUT\MIXED"
        self.temperature = r"\Data\Streams\D\Output\TEMP_OUT\MIXED"
        self.original = {"node_ids": ["SEP-1"], "inlets": [{"stream_id": "M"}], "outlets": [{"stream_id": "D"}],
                         "design_readbacks": {
                             "recovery": {"value": 96, "unit_or_basis": "%", "basis": "A in net feed", "design_context": self.context},
                             "pressure": {"value": 4, "unit_or_basis": "bar(a)", "basis": "gas outlet", "native_path": self.pressure},
                             "temperature": {"value": 310, "unit_or_basis": "K", "basis": "gas outlet", "native_path": self.temperature,
                                             "governing_relation": "feed flash calculation"}}}
        self.refined = copy.deepcopy(self.original)
        self.refined["design_readbacks"]["recovery"]["value"] = 95
        self.refined["design_readbacks"]["pressure"]["value"] = 3.5
        self.refined["design_readbacks"]["temperature"]["value"] = 313
        self.original_results = self.snapshot(96, 4, 310)
        self.refined_results = self.snapshot(95, 3.5, 313)
        self.fields = {key: {"baseline_path": f"design_readbacks.{name}", "refined_path": f"design_readbacks.{name}"}
                       for key, name in [(self.recovery, "recovery"), ("pressure", "pressure"), ("temperature", "temperature")]}
        self.fields["pressure"]["use"] = "vary"
        self.boundary = {"inlets": self.original["inlets"], "outlets": self.original["outlets"],
                         "design_specifications": {"article_sha256": "a" * 64, "parameters": self.fields}}

    def snapshot(self, recovery, pressure, temperature):
        return {p: {"path": p, "Value": value, "UnitString": unit}
                for p, value, unit in [(self.feed_rate, 100, "kmol/hr"), (self.product_rate, recovery, "kmol/hr"),
                                       (self.pressure, pressure, "bar"), (self.temperature, temperature, "K")]}

    def codes(self):
        self.gate.island_design_specs("SEP", self.boundary, self.original, self.refined, self.original_results, self.refined_results)
        return {need["code"] for need in self.gate.needs}

    def test_whole_separation_island_preserves_net_target(self):
        self.assertEqual(self.codes(), set())

    def test_limits_use_the_native_observation_even_for_a_nearly_matching_written_value(self):
        for comparison, limit, declared, actual in [("ge", 95, 95, 94.99999995), ("ge", 95, 94.99999999999, 94.99999999999),
                                                  ("le", 96, 96, 96.00000000001)]:
            with self.subTest(comparison=comparison, actual=actual):
                self.gate.needs.clear()
                self.gate.buildable_operating_rules["SEP"][self.recovery]["comparison"] = comparison
                self.gate.buildable_review_specs["SEP"][self.recovery]["value"] = limit
                self.refined_results[self.product_rate]["Value"] = actual
                self.refined["design_readbacks"]["recovery"]["value"] = declared
                self.assertIn("ISLAND_DESIGN_SPEC_MISSED", self.codes())

    def test_nominal_reporting_precision_requires_a_frozen_rule_and_never_rounds_a_limit(self):
        rule = self.gate.buildable_operating_rules["SEP"][self.recovery]
        rule["comparison"] = "eq"
        self.original_results[self.product_rate]["Value"] = 95.00000007
        self.refined_results[self.product_rate]["Value"] = 94.99999993
        self.original["design_readbacks"]["recovery"]["value"] = 95.00000007
        self.refined["design_readbacks"]["recovery"]["value"] = 94.99999993
        self.assertIn("ISLAND_DESIGN_SPEC_MISSED", self.codes())
        self.gate.needs.clear()
        rule["acceptance_decimals"] = 3
        self.assertFalse(self.codes())
        self.gate.needs.clear()
        rule["comparison"] = "ge"
        self.assertIn("ISLAND_DESIGN_SPEC_MISSED", self.codes())
        rule["comparison"] = "eq"
        self.gate.needs.clear()
        self.refined_results[self.product_rate]["Value"] = 94.9994
        self.refined["design_readbacks"]["recovery"]["value"] = 94.9994
        self.assertIn("ISLAND_DESIGN_SPEC_MISSED", self.codes())

    def test_first_sep_component_allocation_uses_each_net_outlet_after_replacement(self):
        key = "first_model.inputs.0"
        self.gate.modules["SEP"] = {"role": "separation", "first_model": {"block_type": "SEP"}}
        context = {"kind": "recovery", "component": "A", "outlet": "D"}
        spec = {"value": 96, "unit_or_basis": "%", "basis": "A in total feed", "design_context": context}
        self.gate.buildable_review_specs["SEP"][key] = spec
        self.gate.buildable_operating_rules["SEP"][key] = {"mode": "fixed", "comparison": "eq", "design_target": True}
        self.fields[key] = {"baseline_path": "design_readbacks.allocation", "refined_path": "design_readbacks.allocation"}
        tails = r"\Data\Streams\W\Output\MOLEFLOW\MIXED\A"
        unrelated = r"\Data\Streams\D\Output\MOLEFRAC\MIXED\A"
        for module, results in [(self.original, self.original_results), (self.refined, self.refined_results)]:
            module["outlets"].append({"stream_id": "W"})
            module["design_readbacks"]["allocation"] = {**spec, "native_path": unrelated}
            module["design_readbacks"]["recovery"]["value"] = 96
            results[self.product_rate]["Value"] = 96
            results[tails] = {"Value": 4, "UnitString": "kmol/hr"}
            results[unrelated] = {"Value": 0.96, "UnitString": "mole fraction"}
        self.assertEqual(self.codes(), set())
        for missing in (False, True):
            with self.subTest(missing=missing):
                self.gate.needs.clear()
                if missing:
                    self.refined_results.pop(tails)
                else:
                    self.refined_results[tails]["Value"] = 2
                self.assertIn("DESIGN_RESULT_NOT_VERIFIED", self.codes())

        self.refined_results[tails] = {"Value": 6, "UnitString": "kmol/hr"}
        self.refined_results[self.product_rate]["Value"] = 94
        self.refined["design_readbacks"]["recovery"]["value"] = 94
        self.gate.needs.clear()
        self.gate.island_design_specs("SEP", self.boundary, {}, self.refined, {}, self.refined_results, stage="reconnect")
        self.assertIn("DESIGN_RESULT_NOT_VERIFIED", {need["code"] for need in self.gate.needs})

    def test_target_drift_or_dropped_field_cannot_pass(self):
        self.refined["design_readbacks"]["recovery"]["value"] = 92
        self.refined_results[self.product_rate]["Value"] = 92
        del self.fields["temperature"]
        self.assertTrue({"ISLAND_PLAN_COVERAGE", "ISLAND_DESIGN_SPEC_MISSED"} <= self.codes())

    def test_wrong_unit_and_attempt_to_vary_product_spec(self):
        self.fields[self.recovery]["use"] = "vary"
        self.refined["design_readbacks"]["pressure"]["unit_or_basis"] = "bar(g)"
        self.assertTrue({"ISLAND_VARY_OUTSIDE_PLAN", "ISLAND_SPEC_READBACK"} <= self.codes())

    def test_wrong_first_run_and_calculation_basis(self):
        self.original["design_readbacks"]["recovery"]["value"] = 90
        self.original_results[self.product_rate]["Value"] = 90
        del self.refined["design_readbacks"]["temperature"]["governing_relation"]
        self.assertTrue({"FIRST_RUN_MISSES_DESIGN", "ISLAND_SOLVED_BASIS"} <= self.codes())

    def test_same_numerical_value_with_a_different_denominator_fails(self):
        self.refined["design_readbacks"]["recovery"]["design_context"]["denominator"] = "dry product A"
        self.assertEqual(self.codes(), {"ISLAND_SPEC_READBACK"})

    def test_input_declaration_or_solve_target_cannot_replace_achieved_recovery(self):
        self.fields[self.recovery]["use"] = "solve_target"
        self.refined_results[self.product_rate]["Value"] = 89
        self.assertEqual(self.codes(), {"DESIGN_RESULT_NOT_VERIFIED"})
        self.gate.needs.clear()
        self.refined["input_cards"] = {"requested_recovery": self.refined["design_readbacks"]["recovery"]}
        self.fields[self.recovery]["refined_path"] = "input_cards.requested_recovery"
        self.assertEqual(self.codes(), {"ISLAND_SPEC_READBACK"})

    def test_permissive_vary_range_cannot_override_frozen_target(self):
        rule = self.gate.buildable_operating_rules["SEP"][self.recovery]
        rule.update(mode="adjustable", bounds={"lower": 90, "upper": 98})
        self.fields[self.recovery]["use"] = "vary"
        self.refined_results[self.product_rate]["Value"] = 91
        self.refined["design_readbacks"]["recovery"]["value"] = 91
        self.assertEqual(self.codes(), {"ISLAND_VARY_OUTSIDE_PLAN"})

    def test_marking_a_target_as_model_determined_keeps_its_numeric_threshold(self):
        self.gate.buildable_operating_rules["SEP"][self.recovery]["mode"] = "determined"
        for export in (self.original, self.refined):
            export["design_readbacks"]["recovery"]["governing_relation"] = 95
        self.refined_results[self.product_rate]["Value"] = 91
        self.refined["design_readbacks"]["recovery"]["value"] = 91
        self.assertEqual(self.codes(), {"ISLAND_DESIGN_SPEC_MISSED"})

    def test_single_reaction_conversion_is_replayed_on_the_actual_per_pass_boundary(self):
        key = "reaction.extent.0"
        context = {"kind": "conversion", "reaction_id": "rx", "key_reactant": "A", "pass_basis": "per_pass",
                   "denominator": "A entering R1 in F"}
        self.gate.modules["R1"] = {"reaction": {"network": [{"id": "rx", "equation": "A -> B"}]}}
        self.gate.buildable_review_specs["R1"] = {key: {"value": 70, "unit_or_basis": "%", "basis": "per-pass conversion",
                                                        "design_context": context}}
        self.gate.buildable_operating_rules["R1"] = {key: {"mode": "fixed", "comparison": "eq", "design_target": True}}
        readback = {"value": 70, "unit_or_basis": "%", "basis": "per-pass conversion", "design_context": context}
        reactor = {"node_ids": ["R1"], "inlets": [{"stream_id": "F"}], "outlets": [{"stream_id": "M"}],
                   "design_readbacks": {"conversion": readback}}
        boundary = {"inlets": reactor["inlets"], "outlets": reactor["outlets"], "design_specifications": {
            "article_sha256": "a" * 64, "parameters": {key: {"baseline_path": "design_readbacks.conversion",
                                                            "refined_path": "design_readbacks.conversion"}}}}
        actual = {f"\\Data\\Streams\\{tag}\\Output\\MOLEFLOW\\MIXED\\A": {"Value": value, "UnitString": "mol/s"}
                  for tag, value in [("F", 100), ("M", 30)]}
        self.gate.island_design_specs("R1", boundary, reactor, reactor, actual, actual)
        self.assertFalse(self.gate.needs, self.gate.needs)
        refined = copy.deepcopy(actual)
        refined[r"\Data\Streams\M\Output\MOLEFLOW\MIXED\A"]["Value"] = 50
        self.gate.island_design_specs("R1", boundary, reactor, reactor, actual, refined)
        self.assertEqual({row["code"] for row in self.gate.needs}, {"DESIGN_RESULT_NOT_VERIFIED"})

    def test_same_run_result_on_a_different_net_inlet_fails(self):
        self.refined["inlets"][0]["stream_id"] = "UNRELATED"
        self.refined_results[r"\Data\Streams\UNRELATED\Output\MOLEFLOW\MIXED\A"] = self.refined_results[self.feed_rate]
        self.assertEqual(self.codes(), {"DESIGN_RESULT_BOUNDARY_MISMATCH"})


class ReconnectDesignTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.fixture = FullflowFixture(temp.name)
        self.fixture.add_reconnect(("S1",))
        self.gate = _Gate({"stage": "reconnect", "run_id": "current-1"}, temp.name, {})
        self.gate.identity = self.fixture.identity
        self.gate.require_buildable_plan = True
        self.gate.modules = {m["id"]: m for m in self.fixture.modules}
        self.gate.scope = ["S1"]
        self.gate.buildable_article_ref = {"sha256": "a" * 64}
        spec = "separation.targets.0"
        self.context = {"kind": "recovery", "component": "A", "outlet": "S1-OUT", "denominator": "A in S1-IN"}
        self.gate.buildable_review_specs = {"S1": {spec: {"value": 95, "unit_or_basis": "%", "basis": "same net recovery",
                                                         "design_context": self.context}}}
        self.gate.buildable_operating_rules = {"S1": {spec: {"mode": "fixed", "comparison": "ge", "design_target": True}}}
        self.gate.island_design_boundaries = {"S1": {"inlets": [{"stream_id": "S1-IN"}], "outlets": [{"stream_id": "S1-OUT"}],
            "design_specifications": {"article_sha256": "a" * 64,
             "parameters": {spec: {"refined_path": "design_readbacks.actual", "use": "solve_target"}}}}}

    def current(self, declared, actual, snapshot_run="current-1"):
        fixture = self.fixture
        reference = fixture.contract["current_run_ref"]
        run = fixture.read(reference)
        def record_snapshot(data):
            data["result_snapshot_ref"] = fixture.put("current-probes.json", {"run_id": snapshot_run,
                "case_sha256": run["model_ref"]["sha256"],
                "probes": {"boundary": [{"path": f"\\Data\\Streams\\S1-{tag}\\Output\\MOLEFLOW\\MIXED\\A",
                    "Value": value, "UnitString": "kmol/hr"} for tag, value in [("IN", 100), ("OUT", actual)]]}})
        run["native_run_ref"] = fixture.rewrite(run["native_run_ref"], record_snapshot)
        def record_projection(data):
            data["modules"][1]["design_readbacks"] = {"actual": {"value": declared, "unit_or_basis": "%",
                    "basis": "same net recovery", "design_context": self.context}}
        run["export_ref"] = fixture.rewrite(run["export_ref"], record_projection)
        fixture.contract["current_run_ref"] = fixture.put(reference["path"], run)
        self.gate.needs.clear()
        self.gate.reconnect(fixture.contract, {"S1": {"run_id": "S1-island"}})
        return {need["code"] for need in self.gate.needs}

    def test_reconnect_requires_same_case_achieved_target_even_after_island(self):
        self.assertEqual(self.current(declared=96, actual=96), set())
        self.assertEqual(self.current(declared=91, actual=91), {"RECONNECT_DESIGN_SPEC_MISSED"})
        self.assertEqual(self.current(declared=96, actual=91), {"DESIGN_RESULT_NOT_VERIFIED"})

    def test_reconnect_does_not_accept_a_snapshot_from_the_island(self):
        self.assertEqual(self.current(declared=96, actual=96, snapshot_run="S1-island"),
                         {"NATIVE_DESIGN_RESULT_IDENTITY", "DESIGN_RESULT_NOT_VERIFIED"})
