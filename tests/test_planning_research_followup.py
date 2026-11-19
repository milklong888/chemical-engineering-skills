"""Planning repair actions stay scoped to the missing source decision."""
import unittest

from tools.design_stage import planning_revision_actions


class PlanningRevisionActionTests(unittest.TestCase):
    contract = {"modules": [
        {"id": "R1", "physical_service": "gas-oil hydrocracking", "thermodynamics": {"components": ["H2", "gas oil"]}},
        {"id": "S1", "physical_service": "remove dissolved acid gas"},
    ]}

    def test_searches_target_the_actual_duty_and_gaps(self):
        needs = [{"code": "PLAN_REACTION_RESEARCH_MISSING", "scope": "module.R1.reaction.planning_research",
                  "detail": "Could not trace rate law"},
                 {"code": "EVIDENCE_UNAVAILABLE", "scope": "module.R1.reaction.planning_research.citation",
                  "detail": "Wrong digest"},
                 {"code": "PLAN_SEPARATION_RESEARCH_MISSING", "scope": "module.S1",
                  "detail": "Net removal target has no physical route"}]
        work = planning_revision_actions(needs + [needs[0]], self.contract)
        self.assertEqual([j["module_id"] for j in work], ["R1", "S1"])
        self.assertEqual(len(work[0]["findings"]), 2)
        self.assertIn("hydrocracking", work[0]["queries_to_run"][0])
        self.assertIn("H2", work[0]["queries_to_run"][0])
        self.assertIn("acid gas", work[1]["queries_to_run"][0])

    def test_fixed_or_unrelated_findings_do_not_trigger_another_search(self):
        self.assertEqual(planning_revision_actions([], self.contract), [])
        self.assertEqual(planning_revision_actions([{"code": "INDEPENDENT_REVIEW_COUNT", "scope": "source"}],
                                                   self.contract), [])

    def test_missing_first_model_data_routes_to_quantitative_basis(self):
        needs = [{"code": "PLAN_FIXED_CONVERSION", "scope": "module.R1.first_model"},
                 {"code": "PLAN_NATIVE_SEP_SPLITS", "scope": "module.S1.first_model"}]
        jobs = planning_revision_actions(needs, self.contract)
        self.assertEqual([(j["module_id"], j["scope"]) for j in jobs], [("R1", "first_model"), ("S1", "first_model")])
        self.assertIn("转化率", jobs[0]["queries_to_run"][0])
        self.assertIn("出口", jobs[1]["next_operation"])
