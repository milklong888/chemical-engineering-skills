"""Synthetic acceptance obligations checked at source, scaffold and later actual readbacks."""
import copy
from decimal import Decimal
import tempfile
import unittest
from unittest.mock import Mock

from test_buildable_plan import ARTICLE, BuildableInputs, IntegratedBuildableFixture
import test_plan_scope_and_island as island_fixtures
import test_delivery_findings as delivery_fixtures
from tools.design_stage import run_buildable_first_scaffold
from tools.fullflow_gate import _meets_design


def prepare_scaffold(root, *, recovery=90, snapshot_run=None, snapshot_model=None):
    """Public-stage dossier with three frozen source reviews and three post-run export reviews."""
    f = IntegratedBuildableFixture(root)
    source_modules = copy.deepcopy(f.modules)
    for module in source_modules:
        module[module["role"]].setdefault("conditions", [])
    run_ref, run, _ = f.run("scaffold-1", source_modules, scaffold=True)
    f.scaffold_record = run
    stage = f.contract["scaffold_gate"]
    recovered = Decimal(str(recovery)) * 3 / 100
    amounts = {"F": {"A": 10}, "M": {"A": 3, "B": 7, "H2": 13},
               "D": {"A": float(recovered), "B": 0.7, "H2": 13},
               "W": {"A": float(3 - recovered), "B": 6.3, "H2": 0}}
    snapshot = {"run_id": snapshot_run or run["run_id"], "case_sha256": snapshot_model or run["model_ref"]["sha256"],
                "probes": {"streams": [{"path": f"\\Data\\Streams\\{s}\\Output\\MOLEFLOW\\MIXED\\{c}",
                      "Value": v, "UnitString": "mol/s"} for s, rates in amounts.items() for c, v in rates.items()]}}
    snapshot_ref = f.put("scaffold-snapshot.json", snapshot)
    run["native_run_ref"] = f.rewrite(run["native_run_ref"], lambda r: r.update(result_snapshot_ref=snapshot_ref))
    stage["run_ref"] = f.put(run_ref["path"], run)
    stage["cycle_initials_ref"] = f.rewrite(stage["cycle_initials_ref"], lambda r: r.update(
        export_sha256=run["export_ref"]["sha256"], source_refs=[run["export_ref"]]))
    binding = {"run_id": run["run_id"], "export_sha256": run["export_ref"]["sha256"],
               "cycle_initials_sha256": stage["cycle_initials_ref"]["sha256"]}
    stage.update(f.reviews("scaffold", 3, binding))
    for i, summary in enumerate(("Traced the retained A between S1 and D.", "Checked the A fed at F and converted in R1.",
                                 "Compared the final net split against the original product requirement.")):
        def annotated(output):
            for item in output["module_reviews"]:
                item["boundary_summary"] = summary
        f.change_call("scaffold", i, revise_output=annotated,
                      revise_invocation=lambda v: v.update(started_epoch=102, finished_epoch=103))
    stage["difference_closure_ref"] = f.rewrite(stage["difference_closure_ref"], lambda r: r.update(closed_epoch=112))
    return f


class DesignToleranceTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.plan = BuildableInputs(folder.name)

    def freeze(self, *, name="A recovery", target=95, comparison="eq", kind="absolute", value=0.01, unit="百分点", target_unit="%",
               clause="A recovery at D is 95 %; 允许绝对偏差 ±0.01 个百分点。", original=None,
               article=None, outlet=None, metric=None, **extra):
        p = self.plan
        ref = p.put("tolerance-source.txt", original if original is not None else clause)
        tolerance = {"kind": kind, "value": value, "unit": unit, "basis": clause, "source_ref": ref, **extra}
        row = {"name": name, "value": target, "unit_or_basis": target_unit, "comparison": comparison,
               "basis": "A entering S1", "source_ref": ref, "article_excerpt": f"{name} {target} {target_unit} at D.",
               "acceptance_tolerance": tolerance}
        if outlet:
            row["outlet"] = outlet
        if metric:
            row["kind"] = metric
        gate = p.gate
        gate.needs.clear()
        gate.buildable_review_specs, gate.buildable_operating_rules = {"S1": {}}, {"S1": {}}
        gate.buildable_article_text = row["article_excerpt"] + "\n" + (article if article is not None else clause)
        gate.buildable_quantity(row, p.s, "targets.0", "S1")
        return gate.buildable_operating_rules["S1"]["targets.0"], {n["code"] for n in gate.needs}

    def test_absolute_points_on_nominal_and_one_sided_designs(self):
        for comparison, inside, boundary, outside in (("eq", 94.99999995, 94.99, 94.98),
                                                      ("ge", 99, 94.99, 94.98), ("le", 91, 95.01, 95.02)):
            rule, issues = self.freeze(comparison=comparison)
            self.assertFalse(issues)
            self.assertTrue(all(_meets_design(v, 95, rule) for v in (inside, boundary)))
            self.assertFalse(_meets_design(outside, 95, rule))
        rule, issues = self.freeze(target=0.95, target_unit="fraction", clause="A recovery allows ±0.01 percentage points.")
        self.assertFalse(issues)
        self.assertTrue(_meets_design(0.9499, 0.95, rule))
        self.assertFalse(_meets_design(0.94989, 0.95, rule))

    def test_relative_to_declared_nominal_and_source_hard_limits(self):
        rule, issues = self.freeze(kind="relative", value=1, unit="%", reference="target",
                                   clause="For A recovery, allow 1 % of the nominal target.")
        self.assertFalse(issues)
        self.assertTrue(_meets_design(94.05, 95, rule))
        self.assertFalse(_meets_design(94.04999, 95, rule))
        for name, cmp, clause, accepted, rejected in (("A回收率", "ge", "A回收率的硬下限为 95 %。", 95, 94.99999995),
                                                       ("A recovery", "le", "A recovery 不得高于 95 %。", 95, 95.00000001)):
            rule, issues = self.freeze(name=name, comparison=cmp, kind="hard_limit", value=0, clause=clause)
            self.assertFalse(issues)
            self.assertTrue(_meets_design(accepted, 95, rule))
            self.assertFalse(_meets_design(rejected, 95, rule))
            _, issues = self.freeze(name=name, comparison="ge" if cmp == "le" else "le", kind="hard_limit", value=0, clause=clause)
            self.assertIn("PLAN_TOLERANCE_EVIDENCE", issues)

    def test_unit_reference_provenance_and_permission_cannot_be_guessed(self):
        for params in ({"unit": "%"}, {"value": -0.01}, {"kind": "relative", "unit": "%"},
                       {"original": "A different project and different number."}, {"article": ARTICLE},
                       {"clause": "本指标不允许采用 ±0.01 个百分点的容差。"},
                       {"clause": "例如，容差可为 0.01 个百分点。"},
                       {"target": 2, "target_unit": "bar", "unit": "bar", "clause": "两个仪表实测差 0.01 bar。"},
                       {"kind": "hard_limit", "comparison": "ge", "value": 0.01}):
            with self.subTest(params=params):
                self.assertTrue(self.freeze(**params)[1])
        self.assertFalse(self.freeze(clause="A recovery 允许偏差 ±0.01 个百分点。另一个温度指标的硬上限为 350 K。")[1])
        self.assertTrue(self.freeze(clause="A recovery 硬下限为 95 %，允许偏差 0.01 个百分点。")[1])

    def test_acceptance_clause_must_authorize_the_same_target(self):
        for clause in (
            "Only B purity has an allowed tolerance of 2 percentage points.",
            "A recovery does not have an allowed tolerance of 2 percentage points.",
            "A recovery has an allowed tolerance of 2 percentage points only if approved.",
            "A recovery is 95 %; only B purity has an allowed tolerance of 2 percentage points.",
            "A recovery is 95 %; allowed tolerance for B purity is 2 percentage points.",
            "A recovery is 95 %, whereas B purity has an allowed tolerance of 2 percentage points.",
            "A recovery allows B purity a tolerance of 2 percentage points.",
            "A recovery 的验收不采用 2 个百分点的容差。",
            "A recovery 允许偏差 2 个百分点，若业主同意。",
        ):
            with self.subTest(clause=clause):
                rule, issues = self.freeze(value=2, clause=clause)
                self.assertIn("PLAN_TOLERANCE_EVIDENCE", issues)
                self.assertFalse(_meets_design(93, 95, rule))
        for clause in ("Only reactor temperature is subject to zero tolerance.", "B purity must not fall below 95 %."):
            self.assertIn("PLAN_TOLERANCE_EVIDENCE", self.freeze(comparison="ge", kind="hard_limit", value=0, clause=clause)[1])
        self.assertIn("PLAN_TOLERANCE_EVIDENCE", self.freeze(outlet="D", value=2,
                      clause="A recovery allows a tolerance of 2 percentage points at outlet W.")[1])

    def test_quoted_substring_cannot_hide_a_condition_and_other_target_limit_does_not_override(self):
        clause = "A recovery allows 0.01 percentage points."
        for parameter in ("original", "article"):
            _, issues = self.freeze(clause=clause, **{parameter: "If approved, " + clause})
            self.assertIn("PLAN_TOLERANCE_EVIDENCE", issues)
        for clause in (
            "A回收率的验收允许偏差不得超过 0.01 个百分点。",
            "A回收率为95%，验收允许偏差不得超过 0.01 个百分点。",
            "A回收率的验收允许偏差不得超过 0.01 个百分点；B纯度的硬下限为 95 %。",
            "A recovery at D has an allowed tolerance of 0.01 percentage points.",
            "A recovery at D has an allowed tolerance of 0.01 percentage points; B purity has a hard lower limit of 95%.",
            "A recovery allows 0.01 percentage points, B purity must not fall below 95 %.",
        ):
            with self.subTest(clause=clause):
                rule, issues = self.freeze(name="A回收率" if clause.startswith("A回") else "A recovery", clause=clause)
                self.assertFalse(issues)
                self.assertTrue(_meets_design(94.99, 95, rule))

    def test_blanket_allowance_is_limited_to_the_named_metric_class(self):
        for clause in ("所有回收率指标的验收容差统一为 ±0.01 个百分点。",
                       "All recovery targets have a tolerance of ±0.01 percentage points."):
            self.assertFalse(self.freeze(metric="recovery", clause=clause)[1])
            self.assertFalse(self.freeze(clause=clause)[1])
            self.assertFalse(self.freeze(name="A回收率", clause=clause)[1])
            self.assertIn("PLAN_TOLERANCE_EVIDENCE", self.freeze(name="B purity", metric="purity", clause=clause)[1])
            self.assertIn("PLAN_TOLERANCE_EVIDENCE", self.freeze(name="B purity", clause=clause)[1])
            self.assertIn("PLAN_TOLERANCE_EVIDENCE", self.freeze(name="B purity", metric="recovery", clause=clause)[1])
            for name in ("A recovery and B purity", "A recovery or performance", "A performance"):
                self.assertIn("PLAN_TOLERANCE_EVIDENCE", self.freeze(name=name, clause=clause)[1])
        self.assertIn("PLAN_TOLERANCE_EVIDENCE", self.freeze(metric="recovery", clause="所有指标的验收容差统一为 ±0.01 个百分点。")[1])

    def test_missing_only_on_numeric_design_target_and_blocks_native_launch(self):
        f = IntegratedBuildableFixture(self.plan.root)
        f.modules[0]["reaction"]["extent"][0].pop("acceptance_tolerance")
        req = {**f.identity, "fullflow_contract": f.put("contract.json", f.contract)}
        native = Mock()
        response = run_buildable_first_scaffold(req, f.root, run_native=native)
        missing = [n["scope"] for n in response["needs"] if n["code"] == "PLAN_TARGET_TOLERANCE_REQUIRED"]
        self.assertEqual(missing, ["module.R1.reaction.extent.0"])
        native.assert_not_called()

    def test_planned_sep_split_respects_the_inclusive_acceptance_boundary(self):
        p = self.plan
        target = p.s["separation"]["targets"][0]
        target.update(value=95, comparison="eq", article_excerpt="S1 nominally recovers 95 % of A at D.")
        for split, valid in ((94.99, True), (94.98, False)):
            src = f"S1 sets the native recovery of A to D at {split} %."
            p.s["first_model"]["inputs"][0] = {**target, "name": "A recovery", "value": split, "mode": "fixed",
                                              "article_excerpt": src}
            del p.s["first_model"]["inputs"][0]["comparison"]
            del p.s["first_model"]["inputs"][0]["acceptance_tolerance"]
            p.s["outlets"][0]["composition"]["A"] = split / 100
            p.s["outlets"][1]["composition"]["A"] = 1 - split / 100
            p.gate.needs.clear()
            text = ARTICLE + target["article_excerpt"] + "\n" + src
            p.gate.buildable_plan({"planning_article_ref": p.put("plan.md", text)})
            codes = {n["code"] for n in p.gate.needs}
            self.assertEqual(codes, set() if valid else {"PLAN_SEP_TARGET_MISMATCH"}, p.gate.needs)

    def test_scaffold_stage_checks_run_model_and_actual_first_result(self):
        for kw, expected in (({"recovery": 89.99999995}, set()), ({"recovery": 89.99}, set()),
                             ({"recovery": 89.98}, {"FIRST_RUN_MISSES_DESIGN"}),
                             ({"snapshot_run": "old"}, {"NATIVE_DESIGN_RESULT_IDENTITY", "FIRST_RUN_MISSES_DESIGN"}),
                             ({"snapshot_model": "a" * 64}, {"NATIVE_DESIGN_RESULT_IDENTITY", "FIRST_RUN_MISSES_DESIGN"})):
            with self.subTest(kw=kw):
                f = prepare_scaffold(self.plan.root, **kw)
                result = f.check("scaffold")
                self.assertEqual({n["code"] for n in result["needs"]}, expected, result["needs"])

    def test_formal_packaging_replays_frozen_native_target(self):
        delivery = delivery_fixtures.DeliveryFindingsTests()
        delivery.setUp()
        self.addCleanup(delivery.doCleanups)
        f = prepare_scaffold(delivery.root, recovery=89.98)
        delivery.source["fullflow_contract"] = f.put("contract.json", f.contract)
        request = delivery.build()
        result = delivery.template({"formal_delivery": True, "review_request": request})
        final = next(item for item in result["rows"] if item["gate"] == "final_review")
        self.assertFalse(result["passed"])
        self.assertIn("FIRST_RUN_MISSES_DESIGN", {n["code"] for n in final["evidence"]["needs"]})

    def test_generic_scaffold_target_recovers_one_legacy_projection_or_uses_explicit_mapping(self):
        p = self.plan
        self.freeze(name="outlet pressure", target=2, target_unit="bar", unit="bar", clause="The allowable outlet-pressure deviation is ±0.01 bar.")
        gate = p.gate
        gate.require_buildable_plan = True
        spec = gate.buildable_review_specs["S1"]["targets.0"]
        path = r"\Data\Streams\D\Output\PRES_OUT\MIXED"
        projection = {**spec, "native_path": path, "value": 1.999}
        export = {**p.s, "design_readbacks": {"pressure": projection}}
        probes = {path: {"Value": 1.999, "UnitString": "bar"}}
        self.assertTrue(gate.has_scaffold_targets())
        def check():
            gate.needs.clear()
            gate.scaffold_design_targets({"S1": export}, probes)
            return {n["code"] for n in gate.needs}
        self.assertEqual(check(), set())
        export["design_readbacks"]["ambiguous"] = dict(projection)
        self.assertIn("ISLAND_SPEC_READBACK", check())
        export["design_readback_paths"] = {"targets.0": "design_readbacks.pressure"}
        self.assertEqual(check(), set())
        probes[path]["Value"] = 1.98
        self.assertIn("FIRST_RUN_MISSES_DESIGN", check())

    def test_island_and_reconnect_use_frozen_point_allowance_on_native_output(self):
        for reading, passed in ((94.99999995, True), (94.98, False)):
            f = island_fixtures.IslandSpecificationTests()
            f.setUp()
            self.addCleanup(f.doCleanups)
            rule = f.gate.buildable_operating_rules["SEP"][f.recovery]
            rule.update(comparison="eq", acceptance_width=Decimal("0.01"))
            for module, results in ((f.original, f.original_results), (f.refined, f.refined_results)):
                results[f.product_rate]["Value"] = reading
                module["design_readbacks"]["recovery"]["value"] = reading
            self.assertEqual(f.codes(), set() if passed else {"FIRST_RUN_MISSES_DESIGN", "ISLAND_DESIGN_SPEC_MISSED"})
            r = island_fixtures.ReconnectDesignTests()
            r.setUp()
            self.addCleanup(r.doCleanups)
            rule = r.gate.buildable_operating_rules["S1"]["separation.targets.0"]
            rule.update(comparison="eq", acceptance_width=Decimal("0.01"))
            self.assertEqual(r.current(reading, reading), set() if passed else {"RECONNECT_DESIGN_SPEC_MISSED"})
