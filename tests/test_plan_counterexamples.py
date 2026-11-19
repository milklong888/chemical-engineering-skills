"""Engineering counterexamples for the deterministic source-stage checks."""
from tempfile import TemporaryDirectory
import unittest

from test_buildable_plan import ARTICLE, BuildableInputs, IntegratedBuildableFixture
from tools.fullflow_gate import _Gate


class PlanCounterexamples(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.plan = BuildableInputs(directory.name)
        self.article = ARTICLE

    def quantity(self, name, value, unit, excerpt, **details):
        self.article += excerpt + "\n"
        if "comparison" in details or details.get("kind") == "conversion":
            details["acceptance_tolerance"] = self.plan.tolerance
        return {"name": name, "value": value, "unit_or_basis": unit, "source_ref": self.plan.source,
                "basis": excerpt, "article_excerpt": excerpt, **details}

    def evaluate(self):
        gate = self.plan.gate
        gate.needs.clear()
        gate.buildable_plan({"planning_article_ref": self.plan.put("plan.md", self.article)})
        return {item["code"] for item in gate.needs}

    def three_outlet_separator(self, goals):
        module = self.plan.s
        section = module["separation"]
        module["outlets"].append({**module["outlets"][0], "stream_id": "Q", "article_excerpt": "Q leaves S1 as a third product."})
        self.article += module["outlets"][-1]["article_excerpt"] + "\n"
        targets = [self.quantity(f"{outlet} purity", percent, "mol%", f"S1 fixes {outlet} at {percent} mol% A.",
                                 kind="purity", component="A", outlet=outlet, comparison="eq", amount_basis="mole")
                   for outlet, percent in zip("DWQ", goals)]
        targets.append(self.quantity("Q cut", 25, "mol%", "S1 fixes Q at 25 mol% of total feed.",
                                     kind="cut", outlet="Q", comparison="eq", amount_basis="mole"))
        section["targets"] = targets
        section["planning_research"]["target_mappings"] = [
            {"spec_id": f"separation.targets.{i}", "model_use": "verification", "basis": row["basis"]}
            for i, row in enumerate(targets)]
        inputs = [self.quantity(f"{component} split to {outlet}", percent, "%",
                                f"S1 sends {percent} % of feed {component} to {outlet}.",
                                kind="recovery", mode="fixed", component=component, outlet=outlet)
                  for component, outlet, percent in [("A", "D", 60), ("A", "W", 20), ("B", "D", 10), ("B", "W", 60)]]
        for outlet, rates in zip(module["outlets"], [{"A": 0.6, "B": 0.1}, {"A": 0.2, "B": 0.6}, {"A": 0.2, "B": 0.3}]):
            outlet["composition"] = rates
        module["first_model"].update(inputs=inputs, required_inputs=[row["name"] for row in inputs])
        return inputs

    def test_fixed_three_outlet_splits_must_meet_physical_targets(self):
        self.three_outlet_separator([90, 95, 80])
        self.assertEqual(self.evaluate(), {"PLAN_SEP_TARGET_MISMATCH"})
        mismatches = self.plan.gate.needs
        self.assertEqual([row["detail"]["outlet"] for row in mismatches], list("DWQ"))
        self.assertAlmostEqual(mismatches[0]["detail"]["actual_fraction"], 6 / 7)

    def test_feasible_residual_outlet_and_sum_above_one(self):
        inputs = self.three_outlet_separator([600 / 7, 25, 40])
        self.assertEqual(self.evaluate(), set(), self.plan.gate.needs)
        row = inputs[1]
        row.update(value=50, article_excerpt="S1 sends 50 % of feed A to W.")
        self.article += row["article_excerpt"] + "\n"
        self.assertEqual(self.evaluate(), {"PLAN_NATIVE_SEP_SPLITS"})

    def test_native_split_may_exceed_a_lower_limit_and_beat_an_upper_limit(self):
        model = self.plan.s["first_model"]
        model["inputs"] = [self.quantity(f"{component} recovery", percent, "%",
                                         f"S1 starts at {percent} % {component} recovery to D.", mode="fixed",
                                         kind="recovery", component=component, outlet="D")
                           for component, percent in [("A", 95), ("B", 5)]]
        self.plan.s["outlets"][0]["composition"] = {"A": 0.95, "B": 0.05}
        self.plan.s["outlets"][1]["composition"] = {"A": 0.05, "B": 0.95}
        self.assertEqual(self.evaluate(), set(), self.plan.gate.needs)

    def test_native_recovery_duplicate_cannot_override_first_assignment(self):
        inputs = self.three_outlet_separator([600 / 7, 25, 40])
        duplicate = {**inputs[0], "name": "overrides A split to D"}
        inputs.append(duplicate)
        self.plan.s["first_model"]["required_inputs"].append(duplicate["name"])
        self.assertEqual(self.evaluate(), {"PLAN_NATIVE_SEP_SPLITS"})

    def test_three_outlet_plan_cannot_use_a_two_outlet_block(self):
        self.three_outlet_separator([600 / 7, 25, 40])
        self.plan.s["first_model"]["block_type"] = "SEP2"
        self.assertEqual(self.evaluate(), {"PLAN_NATIVE_SEP_OUTLET_COUNT"})

    def test_unresolved_feed_amount_preserves_nominal_splits(self):
        self.three_outlet_separator([600 / 7, 25, 40])
        self.plan.s["inlets"][0]["composition"]["A"] = "set by upstream model"
        self.assertEqual(self.evaluate(), set(), self.plan.gate.needs)

    def test_explicit_outlet_rates_must_match_calculated_net_allocation(self):
        self.three_outlet_separator([600 / 7, 25, 40])
        self.plan.s["outlets"][0]["composition"]["A"] = 0.5
        self.assertEqual(self.evaluate(), {"PLAN_SEP_OUTLET_COMPOSITION_MISMATCH"})
        issue = self.plan.gate.needs[0]
        self.assertEqual(issue["detail"]["calculated_and_declared"], {"A": [0.6, 0.5]})

    def test_connected_module_reports_cannot_disagree_on_same_material_stream(self):
        fixture = IntegratedBuildableFixture(self.plan.root)
        gate = _Gate({}, fixture.root, {})
        gate.modules = {module["id"]: module for module in fixture.modules}
        source = fixture.contract["source_gate"]
        handoff = fixture.read(source["handoff_input_ref"])
        gate.buildable_plan(source)
        self.assertFalse(gate.needs, gate.needs)
        produced = gate.modules["R1"]["outlets"][0]
        produced.update(composition={k: v * 3.6 for k, v in produced["composition"].items()}, basis="kmol/h")
        gate.buildable_interfaces(handoff)
        self.assertFalse(gate.needs, gate.needs)
        del produced["composition"]["H2"]
        gate.buildable_interfaces(handoff)
        self.assertEqual([row["code"] for row in gate.needs], ["PLAN_INTERFACE_COMPOSITION_MISMATCH"])
        self.assertEqual(gate.needs[0]["detail"]["upstream_and_downstream"], {"H2": [0, 13]})

    def test_parallel_rstoic_cannot_use_130_percent_of_original_inlet(self):
        module = self.plan.r
        reaction = module["reaction"]
        equation = "R1 also follows A + H2 -> C."
        reaction["network"].append({**reaction["network"][0], "id": "parallel", "equation": "A + H2 -> C",
                                    "article_excerpt": equation})
        self.article += equation + "\n"
        initial = reaction["extent"][0]
        reaction["extent"].append(self.quantity("parallel conversion", 60, "%",
                                                "R1 directs 60 % of the original inlet A to the parallel reaction.",
                                                kind="conversion", reaction_id="parallel", key_reactant="A", pass_basis="per_pass",
                                                denominator=initial["denominator"]))
        reaction["planning_research"]["target_mappings"].append({"spec_id": "reaction.extent.1", "model_use": "verification",
                                                                 "basis": "Original section-inlet A"})
        module["first_model"]["required_inputs"].append("FRAC-parallel")
        module["first_model"]["inputs"].append({"name": "FRAC-parallel", "spec_id": "reaction.extent.1"})
        self.assertEqual(self.evaluate(), {"PLAN_REACTANT_OVERCONSUMED"})

    def test_preserved_extracts_from_irrelevant_systems_fail(self):
        reactor = self.plan.r["reaction"]["planning_research"]["candidates"][0]
        separator = self.plan.s["separation"]["planning_research"]["candidates"][0]
        reactor["basis"].update(rate_law="r_Z = k*p_Z^2", catalyst="Cat-Q powder", parameters="k = 20 mol/(kg_cat s bar^2)",
                                rate_basis="Z consumption per mass of catalyst", validity="740 to 760 K and 29 to 30 bar")
        separator["basis"].update(phase_data="X/Y relative volatility = 1.0", operating_range="450 to 480 K and 20 to 24 bar")
        for row, statement, mapped in [(reactor, "Pure Z decomposes.", "rate_law"), (separator, "VLE for X/Y only.", "phase_data")]:
            scope = [value for value in row["basis"].values() if isinstance(value, str)]
            excerpt = " ".join([statement, *scope])
            row["evidence"][0].update(source_ref=self.plan.put(mapped + ".txt", excerpt), locator="L1", excerpt=excerpt)
            row["mapped_inputs"][0]["source_basis"] = row["basis"][mapped]
        self.assertEqual(self.evaluate(), {"PLAN_RESEARCH_SYSTEM_MISMATCH", "PLAN_RESEARCH_WINDOW_MISMATCH"})
        self.assertEqual(self.plan.gate.summary["planning_research"]["unresolved_module_ids"], ["R1", "S1"])

    def test_open_kinetic_data_cannot_satisfy_required_response(self):
        research = self.plan.r["reaction"]["planning_research"]
        research["provisional"] = {"unresolved_inputs": ["Catalyst-normalized rate coefficient"],
                                   "refine_trigger": "Read original calibration data", "independent_work": "Use the fixed nominal conversion"}
        self.assertEqual(self.evaluate(), {"PLAN_REACTION_RESEARCH_RESPONSE_OPEN"})
        self.assertEqual(self.plan.gate.summary["planning_research"]["unresolved_module_ids"], ["R1"])

    def test_verified_statement_that_parameters_are_unavailable_is_not_rate_data(self):
        reactor = self.plan.r["reaction"]["planning_research"]["candidates"][0]
        reactor["basis"]["parameters"] = "Rate coefficients were not reported."
        passage = "A and H2 measured. " + " ".join(reactor["basis"].values())
        reactor["evidence"][0].update(source_ref=self.plan.put("incomplete-rates.txt", passage), excerpt=passage)
        self.assertEqual(self.evaluate(), {"PLAN_REACTION_RESEARCH_BASIS"})
