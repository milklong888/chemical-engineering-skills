"""Real stage -> checker -> helper integration in a disposable skills layout.

Only synthetic structural/water fixtures are used. The actual isolated checker
and helper are copied, not mocked; product.skill_location redirects lookup to
the temporary layout. Knowledge/equipment responses are inert test runners.
The deployed runtime's unrelated coordinators are read/imported without edits.
Run with Python -B so imports cannot create bytecode outside temporary files.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


TEST_DIRECTORY = Path(__file__).resolve().parent
ISOLATED_DRAFT = not os.environ.get("STANDALONE_PRODUCT_ROOT") and TEST_DIRECTORY.name != "tests"
if os.environ.get("STANDALONE_PRODUCT_ROOT"):
    RUNTIME = Path(os.environ["STANDALONE_PRODUCT_ROOT"]).resolve()
elif TEST_DIRECTORY.name == "tests":
    RUNTIME = TEST_DIRECTORY.parent
else:
    # Resolve an existing ancestor asset; there is no fixed user/workspace path.
    relative = Path("skill_packages/chemical-engineering-standalone/workspace/chemical-engineering-runtime")
    RUNTIME = next((parent / relative for parent in TEST_DIRECTORY.parents
                    if (parent / relative / "backends/process/feedback.py").is_file()), None)
    if RUNTIME is None:
        raise RuntimeError("Set STANDALONE_PRODUCT_ROOT or place the isolated draft below its existing runtime workspace")
DRAFT = TEST_DIRECTORY.parent
STAGE_SOURCE = DRAFT / "runtime-tools" / "design_stage.py" if ISOLATED_DRAFT else RUNTIME / "tools" / "design_stage.py"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sys.path.insert(0, str(RUNTIME))
try:
    stage = load_module("stage_reaction_math_candidate", STAGE_SOURCE)
    from tools import product_contract
finally:
    sys.path.pop(0)
location = product_contract.skill_location()
if not location.get("available"):
    raise RuntimeError("The selected runtime must expose its registered skills location")
SKILLS = Path(location["path"]).parent.parent
CHECKER_SOURCE = (DRAFT / "docflow-scripts" / "check_flow_handoff.py" if ISOLATED_DRAFT
                  else SKILLS / "aspen-document-driven-flowsheet" / "scripts" / "check_flow_handoff.py")
HELPER_SOURCE = (DRAFT / "chemical-expert-scripts" / "check_reaction_derivations.py" if ISOLATED_DRAFT
                 else SKILLS / "chemical-engineering-expert" / "scripts" / "check_reaction_derivations.py")
CATALOG_SOURCE = SKILLS / "aspen-document-driven-flowsheet" / "assets" / "property_method_names_v14.json"


fixture_candidates = [
    CHECKER_SOURCE.parent / "tests" / "test_reaction_math_hook.py",
    # Packaged runtimes may omit tests; use the fixed repository test owner,
    # not another runtime or a caller-supplied executable path.
    TEST_DIRECTORY.parent / "plugins" / "chemical-engineering-skills" / "skills" /
    "aspen-document-driven-flowsheet" / "scripts" / "tests" / "test_reaction_math_hook.py",
]
FIXTURE_SOURCE = next((path for path in fixture_candidates if path.is_file()), None)
if FIXTURE_SOURCE is None:
    raise RuntimeError("Synthetic hook fixtures missing from the selected skills or repository plugin test layout")
fixtures = load_module("stage_synthetic_handoff_fixtures", FIXTURE_SOURCE)
fixture, water, no_reaction = fixtures.fixture, fixtures.water, fixtures.no_reaction


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class StageReactionMathTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="stage-reaction-math-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.skills = self.root / "skills"
        self.checker = self.skills / "aspen-document-driven-flowsheet" / "scripts" / "check_flow_handoff.py"
        self.helper = self.skills / "chemical-engineering-expert" / "scripts" / "check_reaction_derivations.py"
        self.catalog = self.skills / "aspen-document-driven-flowsheet" / "assets" / CATALOG_SOURCE.name
        for source, destination in ((CHECKER_SOURCE, self.checker), (HELPER_SOURCE, self.helper),
                                    (CATALOG_SOURCE, self.catalog)):
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())
        # These fixtures establish only file presence/hash obligations, never
        # claim that test text is chemical knowledge or real process authority.
        for name in (
            "chemical-engineering-expert/SKILL.md",
            "chemical-engineering-expert/references/DESIGN_STAGE_ROUTING.md",
            "aspen-document-driven-flowsheet/SKILL.md",
            "aspen-document-driven-flowsheet/references/fullflow_generation_workflow.md",
            "aspen-document-driven-flowsheet/references/source_scaffold_handoff.md",
            "aspen-pressure-pfd-delivery/SKILL.md",
        ):
            target = self.skills / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("Synthetic test presence marker; not engineering authority.\n", encoding="utf-8")
        location = {"available": True, "path": str(self.skills / "chemical-engineering-expert" / "SKILL.md")}
        patcher = patch.object(product_contract, "skill_location", return_value=location)
        patcher.start()
        self.addCleanup(patcher.stop)
        # The candidate file remains the stage implementation hashed by check_stage;
        # its unchanged supporting runtime files stay in the actual runtime root.
        root_patcher = patch.object(stage, "ROOT", RUNTIME)
        root_patcher.start()
        self.addCleanup(root_patcher.stop)
        self.knowledge_calls = []
        self.equipment_calls = []

    def search(self, **request):
        self.knowledge_calls.append(copy.deepcopy(request))
        return {"knowledge": {"mode": "synthetic_test", "results": [{
            "node_id": request.get("node_id", "SYNTHETIC-CONSTRAINT"),
            "corpus": "chemical_principles", "knowledge_layer": "L3",
            "knowledge_status": "synthetic_test", "content_available": True,
            "text_is_excerpt": False, "public_path": None,
        }]}}

    def equipment(self, request):
        self.equipment_calls.append(copy.deepcopy(request))
        if request.get("operation") != "capabilities":
            raise AssertionError("Source-only tests must not execute equipment calculation")
        return {"backend_exit_code": 0, "response": {"result": {"synthetic_test": True}}}

    def declaration(self, reaction_payload=None):
        data = fixture()
        data["expert_plan"]["reaction_derivations"] = water() if reaction_payload is None else reaction_payload
        return data

    def reference(self, data):
        path = self.root / "synthetic-planning.json"
        source = self.root / "source-fixture.txt"
        body = b"Synthetic source paragraph for declared graph references only."
        source.write_bytes(body + b"\n")
        source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
        unit_id = "fixture:p0001:" + hashlib.sha256(body).hexdigest()[:12]
        data = copy.deepcopy(data)
        data["source_review"] = {
            "documents": [{"id": "fixture", "path": source.name, "sha256": source_digest}],
            "units": [{"unit_id": unit_id, "disposition": "mapped",
                       "stream_ids": [row["id"] for row in data["streams"]],
                       "reason": "Synthetic mapping only; source semantics are not certified."}],
        }
        path.write_text(json.dumps(data, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        return {"path": path.name, "sha256": sha(path)}

    def run_stage(self, data, *, reference_override=None):
        payload = {"stage": "source", "question": "Synthetic source declaration only",
                   "source_work": "expert_plan", "planning_handoff": self.reference(data)}
        if reference_override is not None:
            payload["planning_handoff"] = reference_override
        before = copy.deepcopy(payload)
        result = stage.check_stage(payload, self.root, search_runner=self.search, equipment_runner=self.equipment)
        self.assertEqual(payload, before)
        for flag in ("engineering_accepted", "flowsheet_modified", "stage_advanced"):
            self.assertIs(result[flag], False)
        for flag in ("engineering_accepted", "execution_verified", "source_truth_verified", "planning_complete"):
            self.assertIs(result["expert_planning"][flag], False)
        json.dumps(result, allow_nan=False)
        return result

    def require_stage_rejection(self, result):
        self.assertEqual(result["status"], "ACTION_REQUIRED")
        self.assertTrue(any(item["code"] in {"EXPERT_PLAN_STRUCTURE_INVALID", "EXPERT_PLAN_HANDOFF_INVALID"}
                            for item in result["needs"]))

    def corrupt_checker_result(self, statements):
        """Model a broken owner response after real checking, not caller injection."""
        extra = ("\n_original_test_check = check\n"
                 "def check(*args, **kwargs):\n"
                 "    result = _original_test_check(*args, **kwargs)\n"
                 + "".join("    " + statement + "\n" for statement in statements)
                 + "    return result\n")
        self.checker.write_text(CHECKER_SOURCE.read_text(encoding="utf-8") + extra, encoding="utf-8")

    def test_real_balanced_water_runs_fixed_sibling_and_preserves_hashes(self):
        result = self.run_stage(self.declaration())
        self.assertEqual(result["status"], "MODULE_CHECKS_EXECUTED")
        plan = result["expert_planning"]
        self.assertEqual(plan["errors"], [])
        self.assertEqual(plan["checker_execution_status"], "EXECUTED")
        self.assertEqual(plan["checker"]["path"], str(self.checker.resolve()))
        self.assertEqual(plan["checker"]["sha256"], sha(self.checker))
        self.assertEqual(plan["checker"]["flags"], {
            "require_expert_plan": True, "require_named_methods": True,
            "require_plan_actions": True, "require_reaction_math": True, "require_source_review": True,
        })
        self.assertIs(plan["check_result"]["reaction_derivations_checked"], True)
        math = plan["reaction_math"]
        self.assertEqual(math, plan["check_result"]["reaction_math"])
        self.assertEqual(math["helper"], {"path": str(self.helper), "sha256": sha(self.helper)})
        self.assertIs(math["result"]["math_checked"], True)
        self.assertIs(math["result"]["math_valid"], True)
        self.assertEqual(math["result"]["reactions"][0]["element_residuals"], {"H": "0", "O": "0"})
        for flag in ("source_verified", "engineering_accepted", "reaction_feasible"):
            self.assertIs(math["result"][flag], False)
        self.assertEqual([row["operation"] for row in self.equipment_calls], ["capabilities"])
        self.assertEqual(len(self.knowledge_calls), 2)
        self.assertFalse(result["fullflow_gate"]["required"])
        implementation = next(row for row in result["implementation"] if row["path"] == "tools/design_stage.py")
        self.assertEqual(implementation["sha256"], sha(STAGE_SOURCE))

    def test_real_unbalanced_water_rejects_and_preserves_exact_residuals(self):
        reaction = water()
        reaction["reactions"][0]["species"][2]["coefficient"] = 1
        result = self.run_stage(self.declaration(reaction))
        self.require_stage_rejection(result)
        plan = result["expert_planning"]
        self.assertEqual(plan["status"], "STRUCTURE_INVALID")
        self.assertIs(plan["check_result"]["reaction_derivations_checked"], True)
        math = plan["reaction_math"]["result"]
        self.assertIs(math["math_checked"], True)
        self.assertIs(math["math_valid"], False)
        self.assertEqual(math["reactions"][0]["element_residuals"], {"H": "-2", "O": "-1"})
        self.assertTrue(plan["errors"])

    def test_explicit_empty_is_legitimate_na_not_arithmetic_pass(self):
        result = self.run_stage(self.declaration(no_reaction()))
        self.assertEqual(result["status"], "MODULE_CHECKS_EXECUTED")
        plan = result["expert_planning"]
        self.assertIs(plan["check_result"]["reaction_derivations_checked"], True)
        outcome = plan["reaction_math"]["result"]
        self.assertEqual(outcome["status"], "not_applicable")
        self.assertEqual(outcome["reactions"], [])
        self.assertTrue(outcome["none_reason"].strip())
        for flag in ("applicable", "math_checked", "math_valid"):
            self.assertIs(outcome[flag], False)

    def test_missing_declaration_does_not_become_silent_na(self):
        result = self.run_stage(fixture())
        self.require_stage_rejection(result)
        self.assertFalse(result["expert_planning"]["check_result"]["reaction_derivations_checked"])
        self.assertIn("require-reaction-math", " ".join(result["expert_planning"]["errors"]))

    def test_empty_without_reason_and_malformed_formula_are_rejected(self):
        for reaction in ({"reactions": []}, {"reactions": [], "none_reason": " "}):
            with self.subTest(reaction=reaction):
                self.require_stage_rejection(self.run_stage(self.declaration(reaction)))
        reaction = water()
        reaction["reactions"][0]["species"][0]["formula"] = "H2·H2O"
        self.require_stage_rejection(self.run_stage(self.declaration(reaction)))

    def test_other_root_structure_errors_still_block_balanced_math(self):
        data = self.declaration()
        data["nodes"] = []
        result = self.run_stage(data)
        self.require_stage_rejection(result)
        self.assertTrue(result["expert_planning"]["reaction_math"]["result"]["math_valid"])
        self.assertTrue(result["expert_planning"]["errors"])

    def test_actual_catalog_layout_and_name_check_are_preserved(self):
        data = self.declaration()
        data["expert_plan"]["methods"][0]["named_methods"] = [{
            "name": "NRTL", "name_origin": "aspen_v14_catalog",
            "source_ref": "Synthetic name-presence declaration", "applies_when": "Not evaluated in this test",
        }]
        result = self.run_stage(data)
        self.assertEqual(result["status"], "MODULE_CHECKS_EXECUTED")
        catalog = result["expert_planning"]["named_method_catalog"]
        self.assertEqual(catalog["path"], str(self.catalog))
        self.assertEqual(catalog["sha256"], sha(CATALOG_SOURCE))

    def test_missing_fixed_helper_does_not_accept_numeric_declaration(self):
        self.helper.unlink()
        result = self.run_stage(self.declaration())
        self.require_stage_rejection(result)
        self.assertFalse(result["expert_planning"]["check_result"]["reaction_derivations_checked"])
        self.assertIsNone(result["expert_planning"]["reaction_math"]["result"])

    def test_handoff_hash_mismatch_keeps_original_failure_path(self):
        result = self.run_stage(self.declaration(), reference_override={"path": "synthetic-planning.json", "sha256": "0" * 64})
        self.require_stage_rejection(result)
        self.assertEqual(result["expert_planning"]["status"], "CHECK_FAILED")
        self.assertEqual(result["expert_planning"]["checker_execution_status"], "FAILED")

    def test_no_errors_cannot_hide_missing_arithmetic_execution(self):
        self.corrupt_checker_result(["result['reaction_derivations_checked'] = False"])
        result = self.run_stage(self.declaration())
        self.require_stage_rejection(result)
        self.assertEqual(result["expert_planning"]["status"], "CHECK_FAILED")

    def test_no_errors_cannot_hide_invalid_math_or_engineering_promotion(self):
        mutations = [
            "result['reaction_math']['result']['math_valid'] = False",
            "result['reaction_math']['result']['math_checked'] = 1",
            "result['reaction_math']['result']['errors'] = ['Synthetic arithmetic error']",
            "result['reaction_math']['result']['engineering_accepted'] = True",
            "result['reaction_math']['result']['reactions'] = []",
            "result['reaction_math']['helper']['sha256'] = 'not-a-hash'",
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.corrupt_checker_result([mutation])
                result = self.run_stage(self.declaration())
                self.require_stage_rejection(result)
                self.assertEqual(result["expert_planning"]["status"], "CHECK_FAILED")

    def test_na_receipt_must_be_explicit_and_internally_consistent(self):
        mutations = [
            "result['reaction_math']['result']['none_reason'] = ''",
            "result['reaction_math']['result']['math_valid'] = True",
            "result['reaction_math']['result']['applicable'] = 0",
            "result['reaction_math']['result']['reactions'] = [{}]",
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.corrupt_checker_result([mutation])
                result = self.run_stage(self.declaration(no_reaction()))
                self.require_stage_rejection(result)
                self.assertEqual(result["expert_planning"]["status"], "CHECK_FAILED")

    def test_narrow_source_without_expert_plan_does_not_require_reaction_math(self):
        self.helper.unlink()
        payload = {"stage": "source", "question": "Synthetic source declaration only"}
        result = stage.check_stage(payload, self.root, search_runner=self.search, equipment_runner=self.equipment)
        self.assertEqual(result["status"], "MODULE_CHECKS_EXECUTED")
        self.assertNotIn("expert_planning", result)
        self.assertFalse(any(row["kind"] == "source_expert_planning" for row in result["calls"]))
        self.assertFalse(result["engineering_accepted"])

    def test_expert_source_still_requires_hash_bound_handoff(self):
        payload = {"stage": "source", "question": "Synthetic source declaration only", "source_work": "expert_plan"}
        result = stage.check_stage(payload, self.root, search_runner=self.search, equipment_runner=self.equipment)
        self.assertEqual(result["status"], "ACTION_REQUIRED")
        self.assertEqual(result["expert_planning"]["checker_execution_status"], "NOT_EXECUTED")
        self.assertTrue(any(row["code"] == "EXPERT_PLAN_HANDOFF_REQUIRED" for row in result["needs"]))


if __name__ == "__main__":
    unittest.main()
