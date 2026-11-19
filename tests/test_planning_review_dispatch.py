"""Check verbatim reviewer instructions and substantive source review readbacks."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from test_buildable_review import BuildableReviewFixture
from tools.fullflow_gate import (PLANNING_REVIEW_BRIEF, PLANNING_REVIEW_REFS, _skill_root, check_fullflow,
                                 _same_observed_value, contract_schema, planning_review_layout)


class PlanningReviewDispatchTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.fixture = BuildableReviewFixture(temporary.name)
        self.source = self.fixture.contract["source_gate"]

    def codes(self):
        return {row["code"] for row in self.fixture.run_review_gate().needs}

    def test_source_discovery_returns_real_brief_and_frozen_instructions(self):
        canonical = (_skill_root() / PLANNING_REVIEW_BRIEF).read_text(encoding="utf-8-sig").rstrip()
        self.assertEqual(contract_schema()["planning_review_dispatch"]["brief"], canonical)
        early_result = check_fullflow({"stage": "source", "source_work": "buildable_plan"}, self.fixture.root)
        self.assertEqual(early_result["planning_review_dispatch"]["brief"], canonical)
        self.fixture.contract["planning_scope"] = "buildable_flowsheet"
        ref = self.fixture.put("contract.json", self.fixture.contract)
        result = check_fullflow({"stage": "source", "fullflow_contract": ref}, self.fixture.root)
        prompt = result["planning_review_dispatch"]
        self.assertEqual(prompt["status"], "PLANNING_INPUTS_BLOCKED")
        self.assertTrue(prompt["blocking_checks"])
        self.assertFalse(prompt["source_review_closed"])
        self.assertTrue(prompt["text"].startswith(canonical + "\n\n"))
        self.assertIn(self.fixture.identity["task_revision"], prompt["text"])
        for name in PLANNING_REVIEW_REFS:
            self.assertIn(self.source[name]["path"], prompt["text"])
            self.assertIn(self.source[name]["sha256"], prompt["text"])
        self.assertEqual(prompt["sha256"], hashlib.sha256(prompt["text"].encode("utf-8")).hexdigest())
        packet = json.loads(prompt["text"].rsplit("```json\n", 1)[1].split("\n```", 1)[0])
        root = Path(packet["evidence_root"])
        self.assertEqual(root, self.fixture.root.resolve())
        self.assertNotEqual(Path.cwd(), root)
        for name in PLANNING_REVIEW_REFS:
            self.assertEqual(packet[name], self.source[name])
            self.assertEqual(hashlib.sha256((root / packet[name]["path"]).read_bytes()).hexdigest(), packet[name]["sha256"])
        self.assertIn({"spec_id": "separation.targets.0", "node_id": "S1", "design_context_keys": []},
                      packet["review_specifications"]["S1"])

    def test_packet_status_distinguishes_missing_calls_from_closed_reviews(self):
        closed = self.fixture.run_review_gate().planning_review_dispatch
        self.assertEqual(closed["status"], "REVIEWS_CLOSED")
        self.assertTrue(closed["source_review_closed"])
        self.source["independent_calls"].pop()
        pending = self.fixture.run_review_gate().planning_review_dispatch
        self.assertEqual(pending["status"], "READY_TO_SEND")
        self.assertFalse(pending["source_review_closed"])
        self.assertEqual(pending["text"], closed["text"])

    def test_short_shared_prompt_fails_even_when_all_hashes_agree(self):
        short_text = "Please review numbered items in the official brief."
        self.source["prompt_ref"] = self.fixture.put("short-prompt.txt", short_text)
        digest = self.source["prompt_ref"]["sha256"]
        for i in range(3):
            self.fixture.change_call(
                "source", i, revise_call=lambda x: x.update(prompt_sha256=digest),
                revise_invocation=lambda x: x.update(prompt_sha256=digest, dispatched_prompt=short_text))
        self.assertTrue({"PLANNING_REVIEW_PROMPT_INCOMPLETE", "PLANNING_REVIEW_PROMPT_NOT_SENT"} <= self.codes())

    def test_one_invocation_cannot_omit_the_body_while_reusing_hash(self):
        self.fixture.change_call("source", 2, revise_invocation=lambda x: x.pop("dispatched_prompt"))
        self.assertEqual(self.codes(), {"PLANNING_REVIEW_PROMPT_NOT_SENT"})

    def test_optional_raw_answer_parts_are_checked_when_bound(self):
        raw = self.fixture.put("raw-module-answer.json", {"module_id": "R1"})
        self.fixture.change_call("source", 0, revise_invocation=lambda x: x.update(raw_output_refs=[raw]))
        self.assertEqual(self.codes(), set())
        self.fixture.put(raw["path"], {"module_id": "S1"})
        self.assertEqual(self.codes(), {"EVIDENCE_UNAVAILABLE"})

    def test_cold_reader_can_check_answer_layout_before_submitting(self):
        record = self.fixture.read(self.source["independent_calls"][0])
        answer = self.fixture.read(record["output_ref"])
        self.assertEqual(planning_review_layout(answer), [])
        for key in ("quantitative_extractions", "issues"):
            answer[key] = answer["module_reviews"][0].pop(key)
        problems = planning_review_layout(answer)
        self.assertEqual(len(problems), 4)
        self.assertTrue(any("module_reviews[0].issues" in p for p in problems))

    def test_issue_at_top_level_cannot_be_ignored_even_with_valid_module_arrays(self):
        self.fixture.change_call("source", 1, revise_output=lambda out: out.update(issues=[{"id": "missed"}]))
        self.assertEqual(self.codes(), {"PLANNING_REVIEW_OUTPUT_LAYOUT"})

    def test_readback_preserves_exact_json_value_across_number_formatting(self):
        expected = {"pressure_losses": [0.0, 2]}
        self.assertTrue(_same_observed_value({"pressure_losses": [0, 2.0]}, expected))
        for value in (False, "0", 1e-15, None):
            self.assertFalse(_same_observed_value({"pressure_losses": [value, 2]}, expected))
        self.assertFalse(_same_observed_value({"pressure_losses": [0, 2, 0]}, expected))

    def test_incorrect_article_hash_inside_invocation_counts_as_different_prompt(self):
        text = self.fixture.dispatch["text"]
        stale = text.replace(self.fixture.article["sha256"], "f" * 64)
        self.fixture.change_call("source", 1, revise_invocation=lambda x: x.update(dispatched_prompt=stale))
        self.assertEqual(self.codes(), {"PLANNING_REVIEW_PROMPT_NOT_SENT"})

    def test_planning_review_requires_role_assessments_in_every_call(self):
        def edit(output):
            output["module_reviews"][0]["planning_assessments"].pop("reaction_kinetics")
            output["module_reviews"][1]["planning_assessments"].pop("separation_readiness")

        self.fixture.change_call("source", 2, revise_output=edit)
        self.assertIn("PLANNING_REVIEW_ASSESSMENT_COVERAGE", self.codes())

    def test_assessment_rejects_generic_result_and_action_even_with_correct_readbacks(self):
        def edit(output):
            axes = output["module_reviews"][0]["planning_assessments"]
            axes["physical_feasibility"].update(observed_result="All checks passed.", action="Continue.")

        self.fixture.change_call("source", 1, revise_output=edit)
        errors = self.fixture.run_review_gate().needs
        self.assertEqual({row["code"] for row in errors}, {"REVIEW_ANALYSIS_REQUIRED"})
        self.assertEqual({row["scope"].rsplit(".", 1)[-1] for row in errors}, {"observed_result", "action"})

    def test_actual_selected_candidate_and_same_module_handoff_are_mandatory(self):
        def edit(output):
            r1, s1 = (row["planning_assessments"] for row in output["module_reviews"])
            r1["reaction_kinetics"]["evidence"][-1]["value"]["evidence"] = []
            s1["handoff"]["node_ids"] = ["R1"]
            s1["handoff"]["evidence"] = r1["handoff"]["evidence"]

        self.fixture.change_call("source", 0, revise_output=edit)
        self.assertTrue({"PLANNING_REVIEW_EVIDENCE_MISMATCH", "PLANNING_REVIEW_EVIDENCE_INCOMPLETE",
                         "PLANNING_REVIEW_ASSESSMENT_NODE"} <= self.codes())

    def test_each_module_reads_back_its_incident_topology_and_the_full_chain_once(self):
        call = self.fixture.read(self.source["independent_calls"][0])
        original = self.fixture.read(call["output_ref"])
        handoff = self.fixture.read(self.source["handoff_input_ref"])
        self.assertEqual(len(original["process_chain"]), len(handoff["streams"]))
        row = original["module_reviews"][0]
        observed = row["verification_checks"]["connections_terminals"]["observation"]
        self.assertNotIn("nodes", {readback["value_path"] for readback in observed})
        streams = {readback["value"]["id"] for readback in observed if readback["value_path"].startswith("streams.")}
        self.assertEqual(streams, {"T0", "T1", "T2", "T3"})
        self.assertNotIn("PRODUCT", {readback["value"]["id"] for readback in observed})

        def wrong_module_endpoint(output):
            observations = output["module_reviews"][0]["verification_checks"]["connections_terminals"]["observation"]
            edge = next(readback["value"] for readback in observations if readback["value_path"] == "streams.3")
            edge["to"] = "PRODUCT"

        self.fixture.change_call("source", 0, revise_output=wrong_module_endpoint)
        self.assertEqual(self.codes(), {"VERIFICATION_OBSERVATION_MISMATCH"})
        self.fixture.change_call("source", 0, revise_output=lambda output: output.update(original))

        def wrong_full_chain_endpoint(output):
            output["process_chain"][-1]["to"] = "WASTE"

        self.fixture.change_call("source", 0, revise_output=wrong_full_chain_endpoint)
        self.assertEqual(self.codes(), {"REVIEW_PROCESS_CHAIN_MISMATCH"})

    def test_blocking_engineering_finding_requires_rationale_and_current_disposition(self):
        def edit(output):
            row = output["module_reviews"][0]
            row["planning_assessments"]["physical_feasibility"].update(status="issue", issue_id="PLOSS")
            row["issues"] = [{"id": "PLOSS", "node_id": "R1", "finding": "R1 requires a pressure margin check.",
                              "recommended_change": "Reconcile the available absolute pressure with the downstream minimum.",
                              "rereview_scope": "R1 outlet pressure and the S1 inlet boundary."}]

        self.fixture.change_call("source", 0, revise_output=edit)
        self.assertTrue({"DIFFERENCE_UNRESOLVED", "DIFFERENCE_COVERAGE"} <= self.codes())

        def close(disposition, evidence):
            self.fixture.dispose_issues({
                "issue_id": "PLOSS", "disposition": disposition, "evidence_refs": [evidence],
                "rationale": "The reviewed pressure budget includes the R1 outlet and sufficient minimum head.",
            })

        close("adopt", self.fixture.source)
        self.assertTrue({"PLANNING_REVIEW_CLOSURE_EVIDENCE", "REVIEW_PLAN_REVISION_REQUIRED"} <= self.codes())
        close("adopt", self.source["planning_checks_ref"])
        self.assertEqual(self.codes(), {"REVIEW_PLAN_REVISION_REQUIRED"})
        close("reject", self.source["planning_checks_ref"])
        self.assertEqual(self.codes(), set())

    def test_findings_not_linked_to_an_assessment_still_need_individual_dispositions_and_current_revision(self):
        def edit(output):
            row = output["module_reviews"][0]
            row["issues"] = [
                {"id": "BYPASS", "node_id": "R1", "finding": "The material balance omits the purge bypass.",
                 "recommended_change": "Locate and add the bypass in the handoff.", "rereview_scope": "R1 and product train."},
                {"id": "LOSS", "node_id": "R1", "finding": "A duplicate pressure loss appears in the budget.",
                 "recommended_change": "Reconcile the two drops before editing.", "rereview_scope": "R1 and S1 pressure boundary."},
            ]

        self.fixture.change_call("source", 0, revise_output=edit)
        bypass = {"issue_id": "BYPASS", "disposition": "adopt", "evidence_refs": [self.source["handoff_input_ref"]],
                  "rationale": "R1 purge bypass has no registered endpoint in this version."}
        loss = {"issue_id": "LOSS", "disposition": "reject", "evidence_refs": [self.source["planning_checks_ref"]],
                "rationale": "The two entries are distinct piping and equipment losses on matching bases."}
        self.fixture.dispose_issues(bypass)
        self.assertEqual(self.codes(), {"DIFFERENCE_COVERAGE", "REVIEW_PLAN_REVISION_REQUIRED"})
        self.fixture.dispose_issues(bypass, loss, loss)
        self.assertEqual(self.codes(), {"DIFFERENCE_COVERAGE", "REVIEW_PLAN_REVISION_REQUIRED"})
        self.fixture.dispose_issues(bypass, loss)
        self.assertEqual(self.codes(), {"REVIEW_PLAN_REVISION_REQUIRED"})

    def test_adopted_finding_keeps_old_round_open_and_new_round_uses_corrected_article(self):
        def report_missing_basis(output):
            output["module_reviews"][0]["issues"] = [
                {"id": "RECYCLE", "node_id": "R1", "finding": "The article does not state whether R1 has a recycle inlet.",
                 "recommended_change": "State the once-through boundary and trace the R1 inlet.",
                 "rereview_scope": "R1 inlet, outlet and all recycle connections."},
            ]

        self.fixture.change_call("source", 0, revise_output=report_missing_basis)
        self.fixture.dispose_issues({
            "issue_id": "RECYCLE", "disposition": "adopt", "evidence_refs": [self.fixture.article],
            "rationale": "The old text does not identify the mode, although its handoff shows a single feed path.",
        })
        old_closure = self.fixture.read(self.source["difference_closure_ref"])
        self.assertEqual(self.codes(), {"REVIEW_PLAN_REVISION_REQUIRED"})

        self.fixture.text += "R1 runs once through from the only external feed inlet, with no recycle connection.\n"
        self.fixture.article = self.fixture.put("revised-planning-article.txt", self.fixture.text)
        self.source["planning_article_ref"] = self.fixture.article
        self.assertTrue({"STALE_REVIEW_BASIS", "PLANNING_REVIEW_PROMPT_INCOMPLETE"} <= self.codes())
        self.fixture.put("old-source-closure.json", old_closure)

        def current_no_difference(closure):
            item = closure["comparisons"][0]
            del item["issue_dispositions"]
            item.update(issue_ids=[], disposition="no_difference", evidence_refs=[self.fixture.article],
                        rationale="The corrected text states once-through operation and the handoff shows no recycle inlet.")

        self.fixture.change_call("source", 0, revise_output=lambda output: output["module_reviews"][0].update(issues=[]))
        self.source["difference_closure_ref"] = self.fixture.rewrite(self.source["difference_closure_ref"], current_no_difference)
        self.fixture.annotate_source_reviews()
        self.assertEqual(self.codes(), set())
        recovered = self.fixture.read(self.fixture.reference("old-source-closure.json"))
        self.assertEqual(recovered["comparisons"][0]["issue_dispositions"][0]["disposition"], "adopt")


if __name__ == "__main__":
    unittest.main()
