"""Real source stage -> registered checker -> source text and reaction helper.

Synthetic text/graph only; no test exercise, Aspen, network or equipment run.
Knowledge/capability calls are inert spies; the checker and source reads are real.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
IS_DRAFT = HERE.name != "tests"
if IS_DRAFT:
    marker = Path("skill_packages/chemical-engineering-standalone/workspace/chemical-engineering-runtime")
    WORKSPACE = next(p for p in HERE.parents if (p / marker / "tools/design_stage.py").is_file())
    REPO = WORKSPACE / "_skill_refactor/fullflow_gate_20260918/repository"
    RUNTIME = WORKSPACE / marker
else:
    REPO = HERE.parent
    RUNTIME = Path(os.environ.get("STANDALONE_PRODUCT_ROOT", REPO)).resolve()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sys.path.insert(0, str(RUNTIME))
from tools import product_contract
stage = load("stage_source_review_candidate", HERE / "runtime-tools/design_stage.py"
             if IS_DRAFT else RUNTIME / "tools/design_stage.py")
location = product_contract.skill_location()
SKILLS = Path(location["path"]).parent.parent
CHECKER = HERE / "check_flow_handoff.py" if IS_DRAFT else SKILLS / "aspen-document-driven-flowsheet/scripts/check_flow_handoff.py"
HELPER = SKILLS / "chemical-engineering-expert/scripts/check_reaction_derivations.py"
CATALOG = SKILLS / "aspen-document-driven-flowsheet/assets/property_method_names_v14.json"
fixtures = load("source_review_synthetic_fixtures", REPO / "plugins/chemical-engineering-skills/skills/aspen-document-driven-flowsheet/scripts/tests/test_reaction_math_hook.py")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class StageSourceReviewTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="stage-source-review-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.skills = self.root / "skills"
        self.checker = self.skills / "aspen-document-driven-flowsheet/scripts/check_flow_handoff.py"
        for src, dst in ((CHECKER, self.checker),
                         (HELPER, self.skills / "chemical-engineering-expert/scripts/check_reaction_derivations.py"),
                         (CATALOG, self.skills / "aspen-document-driven-flowsheet/assets/property_method_names_v14.json")):
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
        for name in ("chemical-engineering-expert/SKILL.md",
                     "chemical-engineering-expert/references/DESIGN_STAGE_ROUTING.md",
                     "aspen-document-driven-flowsheet/SKILL.md",
                     "aspen-document-driven-flowsheet/references/fullflow_generation_workflow.md",
                     "aspen-document-driven-flowsheet/references/source_scaffold_handoff.md",
                     "aspen-pressure-pfd-delivery/SKILL.md"):
            p = self.skills / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("Synthetic presence marker, not engineering authority.\n", encoding="utf-8")
        self.source = self.root / "current-source.txt"
        self.source.write_text("原料从外部进入处理节点。\n处理后流到产品边界。\n\n这是合成测试的背景，不是工程数据。\n", encoding="utf-8")
        replacement = {"available": True, "path": str(self.skills / "chemical-engineering-expert/SKILL.md")}
        p = patch.object(product_contract, "skill_location", return_value=replacement)
        p.start()
        self.addCleanup(p.stop)
        p = patch.object(stage, "ROOT", RUNTIME)
        p.start()
        self.addCleanup(p.stop)
        self.search_calls, self.equipment_calls = [], []

    def documents(self):
        return [{"id": "synthetic-source", "path": self.source.name, "sha256": sha(self.source)}]

    def inventory_via_cli(self):
        path = self.root / "source-inventory-request.json"
        path.write_text(json.dumps({"source_review": {"documents": self.documents()}}, ensure_ascii=False), encoding="utf-8")
        proc = subprocess.run([sys.executable, "-B", "-X", "utf8", str(self.checker),
                               "--input", str(path), "--source-inventory", "--source-root", str(self.root)],
                              capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        report = json.loads(proc.stdout)
        self.assertEqual(report["schema"], "document-flow-source-inventory-v1")
        self.assertEqual(len(report["inventory"]), 2)
        return report["inventory"]

    def declaration(self):
        data = fixtures.fixture()
        data["expert_plan"]["reaction_derivations"] = fixtures.water()
        units = self.inventory_via_cli()
        data["source_review"] = {"documents": self.documents(), "units": [
            {"unit_id": units[0]["unit_id"], "disposition": "mapped", "stream_ids": ["feed", "product"],
             "reason": "The synthetic paragraph has both declared flow edges."},
            {"unit_id": units[1]["unit_id"], "disposition": "context", "stream_ids": [],
             "reason": "Synthetic test-only context, no additional flow statement."}]}
        return data

    def search(self, **request):
        self.search_calls.append(copy.deepcopy(request))
        return {"knowledge": {"mode": "synthetic", "results": [{"node_id": request.get("node_id", "SYNTHETIC"),
                 "corpus": "chemical_principles", "knowledge_layer": "L3", "knowledge_status": "synthetic",
                 "content_available": True, "text_is_excerpt": False, "public_path": None}]}}

    def equipment(self, request):
        self.equipment_calls.append(copy.deepcopy(request))
        self.assertEqual(request["operation"], "capabilities")
        return {"backend_exit_code": 0, "response": {"result": {"synthetic": True}}}

    def run_stage(self, data=None):
        payload = {"stage": "source", "question": "Synthetic source planning"}
        if data is not None:
            path = self.root / "handoff.json"
            path.write_text(json.dumps(data, ensure_ascii=False, allow_nan=False), encoding="utf-8")
            payload.update(source_work="expert_plan", planning_handoff={"path": path.name, "sha256": sha(path)})
        before = copy.deepcopy(payload)
        result = stage.check_stage(payload, self.root, search_runner=self.search, equipment_runner=self.equipment)
        self.assertEqual(before, payload)
        for flag in ("engineering_accepted", "flowsheet_modified", "stage_advanced"):
            self.assertIs(result[flag], False)
        self.assertTrue(all(row["status"] == "EXECUTED" for row in result["queries"]))
        if data is not None:
            ep = result["expert_planning"]
            for flag in ("engineering_accepted", "execution_verified", "source_truth_verified", "planning_complete"):
                self.assertIs(ep[flag], False)
        return result

    def assert_rejected(self, result):
        self.assertEqual(result["status"], "ACTION_REQUIRED", result)
        ep = result["expert_planning"]
        self.assertTrue(ep.get("errors") or ep.get("error"), ep)

    def test_actual_inventory_then_stage_checker_and_helper(self):
        result = self.run_stage(self.declaration())
        self.assertEqual(result["status"], "MODULE_CHECKS_EXECUTED", result["needs"])
        ep = result["expert_planning"]
        self.assertTrue(ep["checker"]["flags"]["require_source_review"])
        self.assertTrue(ep["check_result"]["source_review_checked"])
        self.assertFalse(ep["check_result"]["source_inventory_verified"])
        self.assertEqual(len(ep["source_review"]["inventory"]), 2)
        self.assertTrue(ep["reaction_math"]["result"]["math_valid"])
        self.assertEqual(ep["checker"]["sha256"], sha(self.checker))

    def test_narrow_source_unaffected(self):
        result = self.run_stage()
        self.assertEqual(result["status"], "MODULE_CHECKS_EXECUTED")
        self.assertNotIn("expert_planning", result)

    def test_missing_source_review_does_not_silently_pass(self):
        data = self.declaration()
        del data["source_review"]
        self.assert_rejected(self.run_stage(data))

    def test_missing_paragraph_disposition(self):
        data = self.declaration()
        data["source_review"]["units"].pop()
        self.assert_rejected(self.run_stage(data))

    def test_unknown_stream_cannot_fill_mapping(self):
        data = self.declaration()
        data["source_review"]["units"][0]["stream_ids"] = ["not-in-graph"]
        self.assert_rejected(self.run_stage(data))

    def test_current_source_drift_is_not_hidden_by_handoff_hash(self):
        data = self.declaration()
        self.source.write_text("Changed source\n", encoding="utf-8")
        self.assert_rejected(self.run_stage(data))

    def test_outside_declared_root_rejected(self):
        data = self.declaration()
        with tempfile.TemporaryDirectory(prefix="outside-source-review-") as td:
            outside = Path(td) / "source.txt"
            outside.write_text("Not in the declared evidence root.\n", encoding="utf-8")
            data["source_review"]["documents"][0].update(path=str(outside), sha256=sha(outside))
            self.assert_rejected(self.run_stage(data))

    def test_source_coverage_does_not_disable_reaction_gate(self):
        data = self.declaration()
        data["expert_plan"]["reaction_derivations"]["reactions"][0]["species"][0]["coefficient"] = -1
        self.assert_rejected(self.run_stage(data))

    def test_explicit_no_reaction_is_not_math_pass(self):
        data = self.declaration()
        data["expert_plan"]["reaction_derivations"] = fixtures.no_reaction()
        result = self.run_stage(data)
        self.assertEqual(result["status"], "MODULE_CHECKS_EXECUTED", result["needs"])
        arithmetic = result["expert_planning"]["reaction_math"]["result"]
        self.assertEqual(arithmetic["status"], "not_applicable")
        self.assertFalse(arithmetic["math_valid"])

    def test_checked_boolean_without_source_receipt_rejected(self):
        data = self.declaration()
        checked = self.run_stage(data)["expert_planning"]["check_result"]
        checked.pop("source_review")
        # A corrupt fixed checker in the disposable layout must not be
        # accepted merely because it returns source_review_checked=True.
        self.checker.write_text("def check(*args, **kwargs):\n    return " + repr(checked) + "\n", encoding="utf-8")
        self.assert_rejected(self.run_stage(data))

    def test_receipt_cannot_promote_source_truth(self):
        data = self.declaration()
        checked = self.run_stage(data)["expert_planning"]["check_result"]
        checked["source_review"]["source_truth_verified"] = True
        self.checker.write_text("def check(*args, **kwargs):\n    return " + repr(checked) + "\n", encoding="utf-8")
        self.assert_rejected(self.run_stage(data))


if __name__ == "__main__":
    unittest.main()
