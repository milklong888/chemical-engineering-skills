"""Synthetic tests for the independent review records, with no external calls."""
from __future__ import annotations

import tempfile
import unittest
from unittest.mock import Mock, patch

from test_fullflow_gate import FullflowFixture
from tools.design_stage import run_buildable_first_scaffold
from tools.fullflow_gate import PLANNING_REVIEW_REFS, _Gate, _article_text, build_planning_review_prompt


class BuildableReviewFixture(FullflowFixture):
    def write_handoff(self, data):
        process = [n["id"] for n in data["nodes"] if n["kind"] == "process"]
        streams = data["streams"]
        # Supply the actual expert-planning sections checked by the public entry.
        data["expert_plan"] = {
            "methods": [{"node_ids": process, "method": "SYNTHETIC-METHOD",
                "phases": ["synthetic process phase"], "applicability": "Defined for the synthetic test state only",
                "source": "Synthetic reference definition", "status": "source_fixed", "unresolved_inputs": [],
                "named_methods": [{"name": "SYNTHETIC-METHOD", "name_origin": "source_defined",
                    "source_ref": "Synthetic reference definition", "applies_when": "Synthetic test mixture",
                    "definition_ref": "Synthetic method of the test dossier"}]}],
            "pressure_paths": [{"id": "interfaces", "node_ids": process, "stream_ids": [s["id"] for s in streams],
                "state": "calculated", "method": "Terminal-to-terminal budget", "source": "Synthetic source only",
                "result_reference": "Specified zero connector loss in this disposable case",
                "equation_or_reason": "P at receiver = P at supply minus connector loss",
                "inputs": [{"name": "connector loss", "unit": "bar", "value_or_reference": 0.0}],
                "refine_trigger": "Replace the synthetic connector allowance when real geometry is available",
                "interface_actions": [{"stream_id": s["id"], "receiver_requirement": "Check the state at " + s["to"],
                    "budget_relation": f"P({s['to']}.in) = P({s['from']}.out) for this test connector",
                    "equipment_action": "Direct connector for " + s["id"],
                    "condition_or_basis": "Zero connector loss was specified for this synthetic check"} for s in streams]}],
            "recycle_plan": [], "no_recycle_reason": "This synthetic graph is single-pass.",
            "reaction_derivations": {"reactions": [], "none_reason": "Lumped test species A and B have no molecular formula; the test prescribes a per-pass conversion."},
        }
        return super().write_handoff(data)

    def __init__(self, root):
        super().__init__(root)
        self.text = ("Synthetic article\nR1 conversion is 70% per pass.\nS1 recovers 90% of its inlet A in product.\n"
                     "The rejected alternate case assumed 65% R1 conversion per pass.\n")
        self.article = self.put("planning-article.txt", self.text)
        self.specs = {
            "R1": {"reaction.extent.0": {"node_id": "R1", "value": 70, "unit_or_basis": "%",
                                         "basis": "per-pass conversion of A at R1", "article_locator": "L2",
                                         "article_excerpt": self.text.splitlines()[1]}},
            "S1": {"separation.targets.0": {"node_id": "S1", "value": 90, "unit_or_basis": "%",
                                             "basis": "inlet A recovered in S1 product", "article_locator": "L3",
                                             "article_excerpt": self.text.splitlines()[2],
                                             "design_context": {"outlet": "product", "component": "A", "kind": "recovery"}}},
        }
        for i, module in enumerate(self.modules, 1):
            role, tag = module["role"], module["id"]
            module.update(physical_service=f"Synthetic {role} at {tag}", article_excerpt=self.text.splitlines()[i])
            module["first_model"] = {"block_type": "RStoic" if role == "reaction" else "SEP"}
            module[role]["planning_research"] = {
                "selected_candidate_id": "synthetic-role-basis",
                "candidates": [{"id": "synthetic-role-basis", "basis": {"reference": "Synthetic candidate basis only"},
                                "evidence": [{"source_ref": self.source, "excerpt": "synthetic method evidence"}]}],
                "target_mappings": [{"spec_id": next(iter(self.specs[tag]))}],
            }
        self.rebuild_source()
        self.bindings = {"source": {"design_basis_sha256": self.contract["source_gate"]["design_basis_ref"]["sha256"]},
                         "scaffold": {"run_id": self.scaffold_record["run_id"],
                                      "export_sha256": self.scaffold_record["export_ref"]["sha256"],
                                      "cycle_initials_sha256": self.contract["scaffold_gate"]["cycle_initials_ref"]["sha256"]}}
        self.annotate_source_reviews()
        scaffold = self.contract["scaffold_gate"]
        scaffold.update(self.reviews("scaffold", 3, self.bindings["scaffold"]))
        authored = ["Identified the inlet assay and basis of each current product target.",
                    "Traced the reacting component and the retained product component using the inlet IDs.",
                    "Compared each process edge, including the chemical and separation boundaries."]
        for index, observation in enumerate(authored):
            def annotate_output(output):
                for row in output["module_reviews"]:
                    row["boundary_summary"] = observation

            self.change_call("scaffold", index, revise_output=annotate_output,
                             revise_call=lambda x: x.update(model_id="synthetic-reviewer", reasoning_effort="high"),
                             revise_invocation=lambda x: x.update(model_id="synthetic-reviewer", reasoning_effort="high",
                                                                  started_epoch=102, finished_epoch=103))
        scaffold["difference_closure_ref"] = self.rewrite(scaffold["difference_closure_ref"], lambda x: x.update(closed_epoch=112))

    def annotate_source_reviews(self):
        source = self.contract["source_gate"]
        source["planning_article_ref"] = self.article
        self.text = _article_text(self.root / self.article["path"])
        gate = _Gate({}, self.root, {})
        gate.buildable_review_specs = self.specs
        self.dispatch = build_planning_review_prompt(
            **self.identity, evidence_root=self.root, review_specifications=gate.review_specification_index(),
            **{name: source[name] for name in PLANNING_REVIEW_REFS})
        source["prompt_ref"] = self.put("source-prompt.txt", self.dispatch["text"])
        handoff_ref = source["handoff_input_ref"]
        handoff = self.read(handoff_ref)
        modules = {module["id"]: module for module in self.modules}

        def annotate_output(output):
            output["planning_article_sha256"] = self.article["sha256"]
            for row in output["module_reviews"]:
                tag = row["module_id"]
                row["quantitative_extractions"] = [{**entry, "spec_id": key, "comparison": "match"}
                                                   for key, entry in self.specs[tag].items()]
                row["planning_assessments"] = self.assessments(source, tag)
                paths = gate.review_connection_paths(handoff, modules[tag])
                row["verification_checks"]["connections_terminals"] = {
                    "observation": [{"evidence_ref": handoff_ref, "value_path": path, "value": gate.at_path(handoff, path)}
                                    for path in paths],
                    "evidence_refs": [handoff_ref],
                }

        for i in range(3):
            self.change_call("source", i, revise_output=annotate_output,
                             revise_call=lambda x: x.update(prompt_sha256=self.dispatch["sha256"]),
                             revise_invocation=lambda x: x.update(prompt_sha256=self.dispatch["sha256"],
                                                                  dispatched_prompt=self.dispatch["text"],
                                                                  started_epoch=20, finished_epoch=21))
        source["difference_closure_ref"] = self.rewrite(source["difference_closure_ref"], lambda x: x.update(closed_epoch=30))

    def assessments(self, source, tag):
        basis, handoff, checks = (source[key] for key in ("design_basis_ref", "handoff_input_ref", "planning_checks_ref"))
        index, module = next((i, m) for i, m in enumerate(self.modules) if m["id"] == tag)
        prefix = f"modules.{index}."
        nodes = module["node_ids"]
        nearby = set(nodes) | {aux["node_id"] for aux in module["auxiliaries"]}
        candidate_prefix = prefix + module["role"] + ".planning_research."
        research = module[module["role"]]["planning_research"]
        candidate = next(i for i, row in enumerate(research["candidates"]) if row["id"] == research["selected_candidate_id"])
        selected_path = candidate_prefix + f"candidates.{candidate}"

        def observed(ref, path):
            value = self.read(ref)
            for field in path.split("."):
                value = value[int(field) if isinstance(value, list) else field]
            return {"evidence_ref": ref, "value_path": path, "value": value}

        def assessment(evidence, result, action):
            return {"node_ids": nodes, "evidence": evidence, "observed_result": result, "action": action, "status": "adequate"}

        checks_evidence = [observed(checks, f"{category}.{i}") for category in ("pressure_budget", "heat_strategy", "compression_decisions")
                           for i, row in enumerate(self.read(checks)[category]) if tag in row["module_ids"]]
        article_quote = module["article_excerpt"]
        locator = f"L{self.text.splitlines().index(article_quote.splitlines()[0]) + 1}"
        article_evidence = {"evidence_ref": self.article, "article_locator": locator, "article_excerpt": article_quote}
        specialist = "reaction_kinetics" if module["role"] == "reaction" else "separation_readiness"
        specialist_evidence = [observed(basis, candidate_prefix + field)
                               for field in ("selected_candidate_id", "target_mappings")]
        specialist_evidence.append(observed(basis, selected_path))
        if "kinetics_exclusion" in research:
            specialist_evidence.append(observed(basis, candidate_prefix + "kinetics_exclusion"))
        handoff_doc = self.read(handoff)
        return {
            "physical_feasibility": assessment(
                [observed(basis, prefix + field) for field in ("inlets", "outlets")] + checks_evidence,
                f"{tag} material interfaces follow the stated assay and the planning pressure budget names this module.",
                f"Carry {tag}'s pressure losses into first-pass outlet checks."),
            "design_depth": assessment(
                [observed(basis, prefix + field) for field in ("physical_service", "first_model")]
                + [observed(basis, candidate_prefix + "selected_candidate_id"), article_evidence],
                f"{tag} physical duty is specified separately from the selected first-model approximation.",
                f"Keep {tag}'s stated service and replace the placeholder during isolated refinement."),
            specialist: assessment(
                specialist_evidence,
                f"The selected candidate's explicit scope supports {tag}'s nominal target and target mapping.",
                f"Compare {tag}'s product-side result against the candidate's validity limits in the specialist step."),
            "evidence_applicability": assessment(
                [observed(basis, prefix + "thermodynamics"), observed(basis, selected_path + ".evidence")],
                f"The cited candidate and property-method record declare the component and phase basis for {tag}.",
                f"Carry {tag}'s listed T/P validity limits into subsequent model comparison."),
            "handoff": assessment(
                [observed(handoff, f"streams.{i}") for i, row in enumerate(handoff_doc["streams"])
                 if row["from"] in nearby or row["to"] in nearby]
                + [observed(handoff, f"handoffs.{i}") for i, row in enumerate(handoff_doc["handoffs"]) if row["id"] in nearby],
                f"{tag}'s incident streams and specialist return contract retain the required boundary interfaces.",
                f"Reconcile {tag}'s return-stream assay on the same basis before reinserting any refinement."),
        }

    def change_call(self, stage, index, *, revise_output=None, revise_call=None, revise_invocation=None):
        gate = self.contract[stage + "_gate"]
        calls = gate["independent_calls"]
        call = self.read(calls[index])
        invocation = self.read(call["invocation_ref"])
        if revise_output:
            previous_output = call["output_ref"]
            call["output_ref"] = self.rewrite(previous_output, revise_output)
            invocation["output_sha256"] = call["output_ref"]["sha256"]
            closure = self.read(gate["difference_closure_ref"])
            for row in closure["comparisons"]:
                if row["call_id"] == call["call_id"]:
                    row["output_sha256"] = call["output_ref"]["sha256"]
                    if "evidence_refs" in row:
                        row["evidence_refs"] = [call["output_ref"] if ref == previous_output else ref for ref in row["evidence_refs"]]
            gate["difference_closure_ref"] = self.put(gate["difference_closure_ref"]["path"], closure)
        if revise_invocation:
            revise_invocation(invocation)
        if revise_call:
            revise_call(call)
        call["invocation_ref"] = self.put(call["invocation_ref"]["path"], invocation)
        calls[index] = self.put(calls[index]["path"], call)

    def dispose_issues(self, *dispositions, index=0):
        source = self.contract["source_gate"]

        def update(closure):
            comparison = closure["comparisons"][index]
            for field in ("issue_ids", "disposition", "rationale", "evidence_refs"):
                comparison.pop(field, None)
            comparison["issue_dispositions"] = list(dispositions)

        source["difference_closure_ref"] = self.rewrite(source["difference_closure_ref"], update)

    def run_review_gate(self, stage="source"):
        gate = _Gate({"stage": stage}, self.root, {})
        gate.contract = self.contract
        gate.identity = self.identity
        gate.modules = {row["id"]: row for row in self.modules}
        gate.require_buildable_plan = True
        gate.buildable_article_ref = self.article
        gate.buildable_article_text = self.text
        gate.buildable_review_specs = self.specs
        gate.reviews(self.contract[stage + "_gate"], stage, 3, bindings=self.bindings[stage])
        return gate


class BuildableReviewTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.fixture = BuildableReviewFixture(temporary.name)

    def codes(self, stage="source"):
        return {need["code"] for need in self.fixture.run_review_gate(stage).needs}

    def test_three_full_chain_reviews_precede_run_and_three_more_follow_it(self):
        source = self.fixture.run_review_gate()
        self.assertEqual(source.needs, [])
        self.assertEqual(source.summary["buildable_review_epochs"]["source_closed_epoch"], 30)
        scaffold = self.fixture.run_review_gate("scaffold")
        self.assertEqual(scaffold.needs, [])
        self.assertEqual(scaffold.summary["buildable_review_epochs"]["scaffold_closed_epoch"], 112)

    def test_two_or_five_source_calls_do_not_satisfy_current_policy(self):
        calls = self.fixture.contract["source_gate"]["independent_calls"]
        original = calls[:]
        for count in (2, 5):
            with self.subTest(count=count):
                calls[:] = (original + original)[:count]
                self.assertIn("INDEPENDENT_REVIEW_COUNT", self.codes())

    def test_same_actual_model_and_effort_within_each_group(self):
        for stage, field, alternative in (("source", "model_id", "other-model"),
                                           ("scaffold", "reasoning_effort", "low")):
            with self.subTest(stage=stage, field=field):
                def revise(record):
                    record[field] = alternative

                self.fixture.change_call(stage, 0, revise_call=revise, revise_invocation=revise)
                self.assertIn("REVIEW_CAPABILITY_MISMATCH", self.codes(stage))

    def test_reviewer_must_check_every_module_and_quantitative_spec(self):
        def revise(output):
            output["module_reviews"].pop()
            output["module_reviews"][0]["quantitative_extractions"] = []

        self.fixture.change_call("source", 0, revise_output=revise)
        self.assertTrue({"REVIEW_MODULE_COVERAGE", "REVIEW_QUANTITY_COVERAGE"} <= self.codes())

    def test_reviewers_may_agree_while_actual_evidence_cannot_be_reused(self):
        gate = self.fixture.contract["source_gate"]
        other_ref = self.fixture.read(gate["independent_calls"][1])["output_ref"]
        other = self.fixture.read(other_ref)
        self.fixture.change_call("source", 0, revise_output=lambda x: x.update(module_reviews=other["module_reviews"]))
        self.assertEqual(self.codes(), set())
        self.fixture.change_call("source", 0, revise_call=lambda x: x.update(output_ref=other_ref))
        self.assertIn("REUSED_REVIEW_EVIDENCE", self.codes())

    def test_quantity_claim_must_match_plan_and_actual_article_line(self):
        def revise(output):
            extraction = output["module_reviews"][0]["quantitative_extractions"][0]
            extraction.update(value=65, article_locator="L3")

        self.fixture.change_call("source", 0, revise_output=revise)
        self.assertTrue({"REVIEW_QUANTITY_COMPARISON", "REVIEW_ARTICLE_ANCHOR", "REVIEW_ARTICLE_VALUE"} <= self.codes())

    def test_net_split_requires_independent_product_destination_readback(self):
        def revise(output):
            extraction = output["module_reviews"][1]["quantitative_extractions"][0]
            extraction["design_context"]["outlet"] = "waste"

        self.fixture.change_call("source", 0, revise_output=revise)
        self.assertTrue({"REVIEW_ARTICLE_DESIGN_CONTEXT", "REVIEW_QUANTITY_COMPARISON"} <= self.codes())

    def test_reviewer_must_read_the_allowance_without_being_given_its_value(self):
        gate = self.fixture.run_review_gate()
        spec = gate.buildable_review_specs["S1"]["separation.targets.0"]
        for key, frozen, wrong in [
            ("acceptance_tolerance", {"kind": "absolute", "value": 0.01, "unit": "百分点"},
             {"kind": "relative", "value": 0.01, "unit": "%", "reference": "target"}),
            ("acceptance_decimals", 3, True),
        ]:
            with self.subTest(key=key):
                spec[key] = frozen
                advertised = gate.review_specification_index()["S1"][0]
                self.assertEqual(advertised["acceptance_field"], key)
                self.assertNotIn(key, advertised)
                entry = {**spec, "spec_id": "separation.targets.0", "comparison": "match"}
                row = {"quantitative_extractions": [entry]}
                gate.needs.clear()
                gate.review_extractions(row, "S1", {}, "source.review")
                self.assertFalse(gate.needs)
                for missing in (False, True):
                    if missing:
                        del entry[key]
                    else:
                        entry[key] = wrong
                    gate.needs.clear()
                    gate.review_extractions(row, "S1", {}, "source.review")
                    self.assertIn("REVIEW_ACCEPTANCE_RULE", {need["code"] for need in gate.needs})
                del spec[key]

    def test_generic_checkmarks_do_not_count_as_authored_analysis(self):
        def revise(output):
            output["module_reviews"][0]["boundary_summary"] = "OK."

        self.fixture.change_call("source", 0, revise_output=revise)
        self.assertIn("REVIEW_ANALYSIS_REQUIRED", self.codes())

    def test_reviewer_and_main_comparison_cannot_hide_mismatch(self):
        def revise(output):
            row = output["module_reviews"][0]
            row["quantitative_extractions"][0].update(value=65, comparison="difference", issue_id="D-1",
                                                      article_locator="L4", article_excerpt=self.fixture.text.splitlines()[3])
            row["issues"] = [{"id": "D-1", "node_id": "R1", "finding": "Reviewer read 65% on R1's basis.",
                              "recommended_change": "Resolve which value controls R1 conversion.",
                              "rereview_scope": "R1 conversion and the immediately downstream inlet."}]

        self.fixture.change_call("source", 0, revise_output=revise)
        for disposition, cite, code in (("no_difference", False, "DIFFERENCE_UNRESOLVED"),
                                        ("adopt", True, "REVIEW_PLAN_REVISION_REQUIRED"),
                                        ("reject", True, None)):
            with self.subTest(disposition=disposition):
                self.fixture.dispose_issues({
                    "issue_id": "D-1", "disposition": disposition,
                    "rationale": "R1's controlling article line states 70% on the stated per-pass basis.",
                    "evidence_refs": [self.fixture.article if cite else self.fixture.source],
                })
                if code:
                    self.assertIn(code, self.codes())
                else:
                    self.assertEqual(self.codes(), set())

    def test_source_closure_after_first_run_start_fails(self):
        gate = self.fixture.contract["source_gate"]
        gate["difference_closure_ref"] = self.fixture.rewrite(gate["difference_closure_ref"], lambda x: x.update(closed_epoch=101))
        self.assertIn("SOURCE_REVIEW_AFTER_NATIVE_START", self.codes())

    def test_post_run_review_cannot_start_before_completed_scaffold(self):
        self.fixture.change_call("scaffold", 0, revise_invocation=lambda x: x.update(started_epoch=99))
        self.assertIn("REVIEW_BEFORE_NATIVE_RUN", self.codes("scaffold"))

    def test_first_scaffold_dispatch_checks_current_reviews_before_calling_native_runner(self):
        f = self.fixture
        contract = {key: value for key, value in f.contract.items() if key != "scaffold_gate"}
        contract["planning_scope"] = "buildable_flowsheet"
        source_gate = contract["source_gate"]
        source_gate["planning_article_ref"] = f.article
        calls = source_gate["independent_calls"]
        last = calls.pop()
        native = Mock(return_value={"status": "synthetic-done"})

        def plan_fixture(gate, source):
            gate.buildable_article_ref = source["planning_article_ref"]
            gate.buildable_article_text = f.text
            gate.buildable_review_specs = f.specs

        def dispatch():
            payload = {**f.identity, "fullflow_contract": f.put("contract.json", contract)}
            return run_buildable_first_scaffold(payload, f.root, run_native=native)

        with patch.object(_Gate, "buildable_plan", plan_fixture), patch.object(_Gate, "buildable_interfaces"):
            blocked = dispatch()
            self.assertEqual(blocked["status"], "ACTION_REQUIRED")
            self.assertIn("INDEPENDENT_REVIEW_COUNT", {row["code"] for row in blocked["needs"]})
            native.assert_not_called()
            calls.append(last)
            with patch("time.time", return_value=25):
                premature = dispatch()
                self.assertIn("FIRST_SCAFFOLD_REVIEW_ORDER", {row["code"] for row in premature["needs"]})
                native.assert_not_called()
            ready = dispatch()
            self.assertEqual(ready["status"], "NATIVE_RUN_DELEGATED", ready["needs"])
        native.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
