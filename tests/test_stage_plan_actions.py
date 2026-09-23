"""Synthetic integration of the existing stage entry and optional action checks."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch


TEST_DIRECTORY = Path(__file__).resolve().parent
if os.environ.get("STANDALONE_PRODUCT_ROOT"):
    RUNTIME = Path(os.environ["STANDALONE_PRODUCT_ROOT"]).resolve()
    DRAFT = RUNTIME
elif TEST_DIRECTORY.name == "tests":
    RUNTIME = TEST_DIRECTORY.parent
    DRAFT = RUNTIME
else:
    DRAFT = TEST_DIRECTORY
    RELATIVE_RUNTIME = Path("skill_packages/chemical-engineering-standalone/workspace/chemical-engineering-runtime")
    RUNTIME = next(p / RELATIVE_RUNTIME for p in DRAFT.parents
                   if (p / RELATIVE_RUNTIME / "tools/product_contract.py").is_file())
sys.path.insert(0, str(RUNTIME))
import tools.product_contract as product

if DRAFT == TEST_DIRECTORY:
    CHECKER = DRAFT / "scripts/check_flow_handoff.py"
else:
    CHECKER = Path(product.skill_location()["path"]).parent.parent / "aspen-document-driven-flowsheet/scripts/check_flow_handoff.py"

spec = importlib.util.spec_from_file_location("draft_stage_actions", DRAFT / "tools/design_stage.py")
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


def fixture():
    actions = [{"stream_id": s, "receiver_requirement": "Source-bounded symbolic receiving state",
                "budget_relation": "Pressure difference at this declared edge balances its applicable losses",
                "equipment_action": "Conditional pressure device on this edge only if the documented supply is insufficient",
                "condition_or_basis": "Supply, receiver and applicable loss data remain explicitly unresolved"}
               for s in ("feed", "product")]
    return {
        "schema": "document-flow-handoff-v1", "stage": "source",
        "authority_reference": "Synthetic declaration; no engineering or source truth asserted",
        "nodes": [{"id": "entry", "kind": "external"}, {"id": "unit", "kind": "process"},
                  {"id": "exit", "kind": "external"}],
        "streams": [{"id": "feed", "from": "entry", "to": "unit", "state": "documented", "evidence": "Synthetic", "gap": None},
                    {"id": "product", "from": "unit", "to": "exit", "state": "documented", "evidence": "Synthetic", "gap": None}],
        "control_volumes": [{"id": "scope", "members": ["unit"], "inflows": ["feed"], "outflows": ["product"],
                             "balance_basis": "Synthetic declared boundary", "reaction_terms": "No chemistry asserted"}],
        "placeholders": [], "no_placeholders_reason": "Synthetic identity fixture", "handoffs": [],
        "expert_plan": {
            "methods": [{"node_ids": ["unit"], "method": "Synthetic named model", "phases": ["synthetic"],
                         "applicability": "Only a declaration test", "source": "Synthetic source", "status": "candidate",
                         "unresolved_inputs": ["All engineering parameters unverified"],
                         "named_methods": [{"name": "SYNTHETIC-MODEL", "name_origin": "source_defined",
                                            "source_ref": "Synthetic citation", "definition_ref": "Synthetic definition",
                                            "applies_when": "No actual engineering applicability asserted"}]}],
            "pressure_paths": [{"id": "path", "node_ids": ["unit"], "stream_ids": ["feed", "product"],
                                "state": "symbolic", "method": "Synthetic pressure declaration",
                                "equation_or_reason": "No numerical calculation claimed", "source": "Synthetic",
                                "inputs": [{"name": "receiver_pressure", "unit": "Pa", "gap": "Unknown"}],
                                "refine_trigger": "Obtain applicable source data", "interface_actions": actions}],
            "recycle_plan": [], "no_recycle_reason": "Declared graph is acyclic; not a source certification",
            "reaction_derivations": {"reactions": [], "none_reason": "Synthetic pressure topology has no reaction-derived quantity."},
        },
    }


class StagePlanActionsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="stage-plan-actions-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.skills = self.root / "skills"
        self.owner = self.skills / "aspen-document-driven-flowsheet/scripts/check_flow_handoff.py"
        self.owner.parent.mkdir(parents=True)
        shutil.copy2(CHECKER, self.owner)
        helper = self.skills / "chemical-engineering-expert/scripts/check_reaction_derivations.py"
        helper.parent.mkdir(parents=True)
        shutil.copy2(CHECKER.parents[2] / "chemical-engineering-expert/scripts/check_reaction_derivations.py", helper)
        location = {"available": True, "path": str(self.skills / "chemical-engineering-expert/SKILL.md")}
        self.location_patch = patch.object(product, "skill_location", return_value=location)
        self.location_patch.start()
        self.addCleanup(self.location_patch.stop)

    def call(self, data=None):
        path = self.root / "plan.json"
        data = fixture() if data is None else data
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
        raw = json.dumps(data).encode("utf-8")
        path.write_bytes(raw)
        return stage.check_expert_planning({"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()},
                                          self.root, {"synthetic": True})

    def test_entry_forces_declaration_and_math_checks_and_preserves_uncertainty(self):
        result = self.call()
        self.assertEqual(result["checker_execution_status"], "EXECUTED")
        self.assertEqual(result["status"], "DECLARATIONS_CHECKED_WITH_UNRESOLVED")
        self.assertEqual(result["checker"]["flags"], {"require_expert_plan": True,
                                                     "require_named_methods": True, "require_plan_actions": True,
                                                     "require_reaction_math": True, "require_source_review": True})
        self.assertTrue(result["check_result"]["plan_action_declarations_checked"])
        for key in ("engineering_accepted", "execution_verified", "source_truth_verified", "planning_complete"):
            self.assertIs(result[key], False)

    def test_entry_rejects_missing_actions_without_erasing_uncertainty(self):
        data = fixture()
        del data["expert_plan"]["pressure_paths"][0]["interface_actions"]
        result = self.call(data)
        self.assertEqual(result["status"], "STRUCTURE_INVALID")
        self.assertTrue(result["errors"])
        self.assertIs(result["planning_complete"], False)

    def test_entry_rejects_partial_interface_coverage(self):
        data = fixture()
        data["expert_plan"]["pressure_paths"][0]["interface_actions"].pop()
        result = self.call(data)
        self.assertEqual(result["status"], "STRUCTURE_INVALID")
        self.assertIs(result["engineering_accepted"], False)

    def test_entry_requires_actual_action_check_marker(self):
        fake = {"schema": "document-flow-handoff-check-v1", "errors": [], "unresolved": [],
                "expert_plan_checked": True, "named_method_declarations_checked": True,
                "plan_action_declarations_checked": False}
        self.owner.write_text("def check(*args, **kwargs):\n    return " + repr(fake) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "all required"):
            self.call()


if __name__ == "__main__":
    unittest.main()
