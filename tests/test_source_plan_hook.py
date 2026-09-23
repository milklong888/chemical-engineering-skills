"""Isolated source-planning hook tests: existing checker, synthetic inputs, no Aspen."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


TEST_DIRECTORY = Path(__file__).resolve().parent
SOURCE_ROOT = Path(__file__).resolve().parents[1]
if os.environ.get("STANDALONE_PRODUCT_ROOT"):
    # Same installed-tree override as the existing repository regression suite.
    RUNTIME = Path(os.environ["STANDALONE_PRODUCT_ROOT"]).resolve()
    DRAFT = RUNTIME
elif TEST_DIRECTORY.name == "tests":
    RUNTIME = SOURCE_ROOT
    DRAFT = RUNTIME
else:
    # An isolated draft has only patched tools; resolve its existing runtime
    # from a real ancestor asset instead of assuming a fixed directory depth.
    DRAFT = TEST_DIRECTORY
    relative_runtime = Path("skill_packages/chemical-engineering-standalone/workspace/chemical-engineering-runtime")
    RUNTIME = next((parent / relative_runtime for parent in TEST_DIRECTORY.parents
                    if (parent / relative_runtime / "backends/process/feedback.py").is_file()), None)
    if RUNTIME is None:
        raise RuntimeError("Set STANDALONE_PRODUCT_ROOT or place the draft below its existing workspace runtime")
sys.path.insert(0, str(RUNTIME))

import tools
import tools.aspen_tool_router as solve_owner
import tools.fullflow_gate as fullflow_owner
import tools.product_contract as original_product


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


design = load("draft_source_design_stage", DRAFT / "tools/design_stage.py")
product = load("draft_source_product_contract", DRAFT / "tools/product_contract.py")
design.ROOT = RUNTIME
product.ROOT = RUNTIME
SKILL_LOCATION = original_product.skill_location()
SKILLS = Path(SKILL_LOCATION["path"]).parent.parent
CHECKER = SKILLS / "aspen-document-driven-flowsheet/scripts/check_flow_handoff.py"


def synthetic_handoff():
    return {
        "schema": "document-flow-handoff-v1", "stage": "source",
        "authority_reference": "Synthetic source declaration, not engineering evidence",
        "nodes": [{"id": "entry", "kind": "external"}, {"id": "unit", "kind": "process"},
                  {"id": "exit", "kind": "external"}],
        "streams": [{"id": "feed", "from": "entry", "to": "unit", "state": "documented", "evidence": "Synthetic source edge", "gap": None},
                    {"id": "product", "from": "unit", "to": "exit", "state": "documented", "evidence": "Synthetic source edge", "gap": None}],
        "control_volumes": [{"id": "boundary", "members": ["unit"], "inflows": ["feed"], "outflows": ["product"],
                             "balance_basis": "Synthetic symbolic basis", "reaction_terms": "No chemistry asserted"}],
        "placeholders": [], "handoffs": [], "no_placeholders_reason": "Synthetic graph has no placeholder",
        "expert_plan": {
            "methods": [{"node_ids": ["unit"], "method": "Named candidate only", "phases": ["synthetic_phase"],
                         "applicability": "For structure testing only", "source": "Synthetic locator", "status": "candidate",
                         "unresolved_inputs": ["No engineering parameter evidence"],
                         "named_methods": [{"name": "NRTL", "name_origin": "aspen_v14_catalog", "source_ref": "Synthetic name-only fixture",
                                            "applies_when": "Applicability is explicitly not asserted"}]}],
            "pressure_paths": [{"id": "identity", "node_ids": ["unit"], "stream_ids": [], "state": "not_applicable",
                                "method": "Synthetic identity", "equation_or_reason": "No pressure calculation asserted",
                                "source": "Synthetic definition", "inputs": [], "refine_trigger": "Replace with real evidence before engineering"}],
            "recycle_plan": [], "no_recycle_reason": "Synthetic acyclic graph only",
            "reaction_derivations": {"reactions": [], "none_reason": "Synthetic topology fixture uses no reaction-derived quantity."},
        },
    }


def synthetic_action_handoff():
    """Add a declared return and symbolic interfaces, not engineering results."""
    data = synthetic_handoff()
    data["nodes"].append({"id": "recovery", "kind": "process"})
    data["streams"][1]["from"] = "recovery"
    data["streams"] += [
        {"id": "forward", "from": "unit", "to": "recovery", "state": "documented",
         "evidence": "Synthetic forward edge", "gap": None},
        {"id": "return", "from": "recovery", "to": "unit", "state": "documented",
         "evidence": "Synthetic return edge", "gap": None},
    ]
    data["control_volumes"][0]["members"].append("recovery")
    plan = data["expert_plan"]
    plan["methods"][0]["node_ids"].append("recovery")
    plan["pressure_paths"][0].update(
        node_ids=["unit", "recovery"], stream_ids=[row["id"] for row in data["streams"]],
        state="symbolic", method="Synthetic interface-budget declaration",
        equation_or_reason="Endpoint relation remains conditional on source data",
        inputs=[{"name": "receiver_pressure", "unit": "Pa", "gap": "Synthetic unresolved input"}],
        interface_actions=[{
            "stream_id": row["id"], "receiver_requirement": "Synthetic receiving-state condition",
            "budget_relation": "Symbolic endpoint relation; no calculation asserted",
            "equipment_action": "Conditional action only if the receiving requirement is unmet",
            "condition_or_basis": "Synthetic conditional basis; no physical applicability asserted",
        } for row in data["streams"]])
    plan["recycle_plan"] = [{
        "stream_id": "return", "from": "recovery", "to": "unit", "closure_order": 10,
        "initialization_basis": "Future source-bounded forward-pass seed; not yet computed",
        "controlled_quantity": "Synthetic return quantity", "purge_or_terminal_basis": "Synthetic product outlet",
        "startup_plan": {
            "temporary_boundary": "Source-bounded conditional inlet; no value invented",
            "forward_pass": "Calculate unit then recovery with the declared return open",
            "seed_outlet_stream_id": "return", "depends_on_recycles": [],
            "closure_reason": "Only one declared return; no preceding closure dependency",
        },
    }]
    plan["no_recycle_reason"] = None
    return data


class SourcePlanHookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="source-plan-hook-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.search_calls, self.equipment_calls = [], []
        self.addCleanup(mock.patch.stopall)
        mock.patch.dict(sys.modules, {"tools.product_contract": product, "tools.design_stage": design}).start()
        mock.patch.object(tools, "product_contract", product).start()
        mock.patch.object(product, "skill_location", return_value=copy.deepcopy(SKILL_LOCATION)).start()
        self.solve = mock.patch.object(solve_owner, "solve_route", return_value={"status": "AGENT_CLASSIFICATION_REQUIRED", "strong_trigger": False}).start()

    def search(self, **request):
        self.search_calls.append(request)
        node = request.get("node_id", "SYNTHETIC-HIT")
        return {"knowledge": {"results": [{"node_id": node, "knowledge_layer": "L3", "corpus": "chemical_principles",
                 "knowledge_status": "synthetic", "content_available": True}], "mode": "synthetic_stub"}}

    def equipment(self, request):
        self.equipment_calls.append(request)
        return {"backend_exit_code": 0, "response": {}}

    def run_stage(self, **extra):
        payload = {"stage": "source", "question": "Synthetic planning service"}
        payload.update(extra)
        return design.check_stage(payload, self.root, search_runner=self.search, equipment_runner=self.equipment)

    def reference(self, data=None, name="handoff.json"):
        path = self.root / name
        data = synthetic_handoff() if data is None else data
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
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        path.write_bytes(raw)
        return {"path": name, "sha256": hashlib.sha256(raw).hexdigest()}

    def assert_queries_preserved(self, result):
        self.assertEqual(len(result["queries"]), 2)
        self.assertTrue(all(row["status"] == "EXECUTED" for row in result["queries"]))
        self.assertEqual(len(self.search_calls), 2)
        self.assertEqual(len(self.equipment_calls), 1)

    def need_codes(self, result):
        return {row["code"] for row in result["needs"]}

    def test_narrow_source_remains_compatible(self):
        result = self.run_stage()
        self.assertEqual(result["status"], "MODULE_CHECKS_EXECUTED", result["needs"])
        self.assertNotIn("expert_planning", result)
        self.assertNotIn("source_work", result)
        self.assert_queries_preserved(result)

    def test_source_work_only_permitted_at_source(self):
        for stage in ("scaffold", "island", "reconnect", "change", "delivery"):
            with self.subTest(stage=stage), self.assertRaises(ValueError):
                self.run_stage(stage=stage, source_work="expert_plan")

    def test_unknown_source_work_is_not_silent_narrow_mode(self):
        for mode in ("planning", "", None, True, []):
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                self.run_stage(source_work=mode)

    def test_handoff_cannot_be_smuggled_without_mode(self):
        with self.assertRaises(ValueError):
            self.run_stage(planning_handoff=self.reference())

    def test_handoff_cannot_be_used_at_later_stage(self):
        with self.assertRaises(ValueError):
            self.run_stage(stage="scaffold", planning_handoff=self.reference())

    def test_missing_reference_keeps_queries_and_requests_real_handoff(self):
        result = self.run_stage(source_work="expert_plan")
        self.assertEqual(result["status"], "ACTION_REQUIRED")
        self.assertIn("EXPERT_PLAN_HANDOFF_REQUIRED", self.need_codes(result))
        self.assertEqual(result["expert_planning"]["checker_execution_status"], "NOT_EXECUTED")
        self.assertFalse(result["expert_planning"]["planning_complete"])
        self.assert_queries_preserved(result)

    def test_expert_reads_are_direct_even_without_fullflow_keyword(self):
        result = self.run_stage(source_work="expert_plan")
        reads = {row["logical_path"] for row in result["domain_reads"]}
        for name in ("aspen-document-driven-flowsheet/references/fullflow_generation_workflow.md",
                     "aspen-document-driven-flowsheet/references/source_scaffold_handoff.md", "aspen-pressure-pfd-delivery/SKILL.md"):
            self.assertIn(name, reads)
        self.assertIn("临时替代", result["next_action"])
        self.assertIn("planning_handoff", result["next_action"])

    def test_bad_hash_is_local_failure_and_keeps_queries(self):
        reference = self.reference()
        reference["sha256"] = "0" * 64
        result = self.run_stage(source_work="expert_plan", planning_handoff=reference)
        self.assertIn("EXPERT_PLAN_HANDOFF_INVALID", self.need_codes(result))
        self.assertEqual(result["expert_planning"]["status"], "CHECK_FAILED")
        self.assert_queries_preserved(result)

    def test_missing_file_is_local_failure(self):
        result = self.run_stage(source_work="expert_plan", planning_handoff={"path": "absent.json", "sha256": "0" * 64})
        self.assertIn("EXPERT_PLAN_HANDOFF_INVALID", self.need_codes(result))
        self.assert_queries_preserved(result)

    def test_wrong_schema_or_non_source_handoff_is_local_failure(self):
        for field, value in (("schema", "wrong"), ("stage", "scaffold")):
            self.search_calls.clear()
            self.equipment_calls.clear()
            data = synthetic_handoff()
            data[field] = value
            result = self.run_stage(source_work="expert_plan", planning_handoff=self.reference(data))
            self.assertIn("EXPERT_PLAN_HANDOFF_INVALID", self.need_codes(result))
            self.assert_queries_preserved(result)

    def test_malformed_json_is_local_failure(self):
        raw = b'{"bad":'
        (self.root / "bad.json").write_bytes(raw)
        result = self.run_stage(source_work="expert_plan", planning_handoff={"path": "bad.json", "sha256": hashlib.sha256(raw).hexdigest()})
        self.assertIn("EXPERT_PLAN_HANDOFF_INVALID", self.need_codes(result))
        self.assert_queries_preserved(result)

    def test_actual_checker_requires_expert_plan_not_legacy_mode(self):
        data = synthetic_handoff()
        del data["expert_plan"]
        result = self.run_stage(source_work="expert_plan", planning_handoff=self.reference(data))
        self.assertIn("EXPERT_PLAN_STRUCTURE_INVALID", self.need_codes(result))
        self.assertIn("--require-expert-plan", " ".join(result["expert_planning"]["errors"]))
        self.assertEqual(result["expert_planning"]["checker"]["flags"], {"require_expert_plan": True, "require_named_methods": True, "require_plan_actions": True, "require_reaction_math": True, "require_source_review": True})

    def test_actual_checker_requires_named_methods(self):
        data = synthetic_handoff()
        del data["expert_plan"]["methods"][0]["named_methods"]
        result = self.run_stage(source_work="expert_plan", planning_handoff=self.reference(data))
        self.assertIn("EXPERT_PLAN_STRUCTURE_INVALID", self.need_codes(result))
        self.assertIn("--require-named-methods", " ".join(result["expert_planning"]["errors"]))

    def test_expert_plan_stage_rejects_missing_pressure_interface_actions(self):
        data = synthetic_action_handoff()
        del data["expert_plan"]["pressure_paths"][0]["interface_actions"]
        result = self.run_stage(source_work="expert_plan", planning_handoff=self.reference(data))
        planning = result["expert_planning"]
        self.assertEqual(result["status"], "ACTION_REQUIRED")
        self.assertIn("EXPERT_PLAN_STRUCTURE_INVALID", self.need_codes(result))
        self.assertEqual(planning["checker_execution_status"], "EXECUTED")
        self.assertEqual(planning["status"], "STRUCTURE_INVALID")
        self.assertIn("interface_actions: required by --require-plan-actions", " ".join(planning["errors"]))
        self.assertIs(planning["check_result"]["plan_action_declarations_checked"], False)
        self.assertIs(result["engineering_accepted"], False)
        self.assertIs(planning["engineering_accepted"], False)
        self.assertIs(planning["planning_complete"], False)
        self.assert_queries_preserved(result)

    def test_expert_plan_stage_rejects_missing_recycle_startup_plan(self):
        data = synthetic_action_handoff()
        del data["expert_plan"]["recycle_plan"][0]["startup_plan"]
        result = self.run_stage(source_work="expert_plan", planning_handoff=self.reference(data))
        planning = result["expert_planning"]
        self.assertEqual(result["status"], "ACTION_REQUIRED")
        self.assertIn("EXPERT_PLAN_STRUCTURE_INVALID", self.need_codes(result))
        self.assertEqual(planning["checker_execution_status"], "EXECUTED")
        self.assertEqual(planning["status"], "STRUCTURE_INVALID")
        self.assertIn("startup_plan: required by --require-plan-actions", " ".join(planning["errors"]))
        self.assertIs(planning["check_result"]["plan_action_declarations_checked"], False)
        self.assertIs(result["engineering_accepted"], False)
        self.assertIs(planning["engineering_accepted"], False)
        self.assertIs(planning["planning_complete"], False)
        self.assert_queries_preserved(result)

    def test_expert_plan_stage_accepts_complete_actions_without_engineering_pass(self):
        data = synthetic_action_handoff()
        result = self.run_stage(source_work="expert_plan", planning_handoff=self.reference(data))
        planning = result["expert_planning"]
        checked = planning["check_result"]
        self.assertEqual(result["status"], "MODULE_CHECKS_EXECUTED", result["needs"])
        self.assertEqual(planning["checker_execution_status"], "EXECUTED")
        self.assertEqual(planning["status"], "DECLARATIONS_CHECKED_WITH_UNRESOLVED")
        self.assertEqual(checked["errors"], [])
        self.assertTrue(checked["unresolved"])
        for flag in ("expert_plan_checked", "named_method_declarations_checked", "plan_action_declarations_checked", "reaction_derivations_checked", "source_review_checked"):
            self.assertIs(checked[flag], True)
        for record in (result, planning, checked):
            self.assertIs(record["engineering_accepted"], False)
        for flag in ("execution_verified", "source_truth_verified", "planning_complete"):
            self.assertIs(planning[flag], False)
        self.assertIs(result["stage_advanced"], False)
        self.assertIs(checked["execution_verified"], False)
        actions = checked["expert_plan_rows"]["pressure_paths"][0]["interface_actions"]
        self.assertEqual({row["stream_id"]: (row["from"], row["to"]) for row in actions},
                         {row["id"]: (row["from"], row["to"]) for row in data["streams"]})
        self.assertEqual(checked["expert_plan_rows"]["recycle_plan"][0]["startup_plan"],
                         data["expert_plan"]["recycle_plan"][0]["startup_plan"])
        self.assert_queries_preserved(result)

    def test_valid_unresolved_candidates_are_kept_without_engineering_pass(self):
        result = self.run_stage(source_work="expert_plan", planning_handoff=self.reference(), case_id="case-a", run_id="source-only")
        planning = result["expert_planning"]
        self.assertEqual(result["status"], "MODULE_CHECKS_EXECUTED", result["needs"])
        self.assertEqual(planning["status"], "DECLARATIONS_CHECKED_WITH_UNRESOLVED")
        self.assertTrue(planning["unresolved"])
        self.assertFalse(planning["engineering_accepted"])
        self.assertFalse(planning["execution_verified"])
        self.assertFalse(planning["source_truth_verified"])
        self.assertFalse(planning["planning_complete"])
        self.assertFalse(result["engineering_accepted"])
        self.assertFalse(result["stage_advanced"])
        self.assertEqual(planning["input_identity"]["case_id"], "case-a")
        self.assertTrue(any(row["kind"] == "source_expert_planning" and row["status"] == "EXECUTED" for row in result["calls"]))

    def test_checker_input_catalog_and_runtime_hashes_are_traceable(self):
        reference = self.reference()
        result = self.run_stage(source_work="expert_plan", planning_handoff=reference)
        planning = result["expert_planning"]
        self.assertEqual(planning["input_reference"]["sha256"], reference["sha256"])
        self.assertEqual(planning["checker"]["sha256"], hashlib.sha256(CHECKER.read_bytes()).hexdigest())
        catalog = planning["named_method_catalog"]
        self.assertEqual(catalog["sha256"], hashlib.sha256(Path(catalog["path"]).read_bytes()).hexdigest())
        files = {row["path"]: row for row in result["implementation"]}
        for name in ("design_stage.py", "product_contract.py"):
            self.assertEqual(files["tools/" + name]["sha256"], hashlib.sha256((DRAFT / "tools" / name).read_bytes()).hexdigest())

    def test_explicit_fullflow_missing_contract_is_not_waived(self):
        result = self.run_stage(source_work="expert_plan", planning_handoff=self.reference(), question="建立全流程规划")
        self.assertTrue(result["fullflow_gate"]["required"])
        self.assertTrue(result["fullflow_gate"]["needs"])
        self.assertEqual(result["status"], "ACTION_REQUIRED")
        self.assertEqual(result["expert_planning"]["status"], "DECLARATIONS_CHECKED_WITH_UNRESOLVED")
        for need in result["fullflow_gate"]["needs"]:
            self.assertIn(need["code"], self.need_codes(result))

    def test_formal_fullflow_five_review_need_remains_even_after_planning_check(self):
        formal = {"required": True, "status": "ACTION_REQUIRED", "required_reading": [], "gate_summary": {},
                  "needs": [{"code": "FORMAL_SOURCE_FIVE_REVIEW_REQUIRED", "scope": "source", "detail": "Synthetic existing-owner need"}]}
        with mock.patch.object(fullflow_owner, "check_fullflow", return_value=formal) as original_gate:
            result = self.run_stage(source_work="expert_plan", planning_handoff=self.reference(), fullflow_contract={"path": "formal.json", "sha256": "0" * 64})
        original_gate.assert_called_once()
        self.assertIn("FORMAL_SOURCE_FIVE_REVIEW_REQUIRED", self.need_codes(result))
        self.assertEqual(result["status"], "ACTION_REQUIRED")

    def test_mvr_evaporation_uses_macro_heat_pressure_not_distillation(self):
        names = {row["logical_path"] for row in design.domain_reads("source", "浓盐水 MVR 蒸发回收热量")}
        self.assertNotIn("aspen-heat-pump-distillation-replacement/SKILL.md", names)
        self.assertIn("chemical-engineering-expert/references/MACRO_DESIGN_QUALITY.md", names)
        self.assertIn("aspen-pressure-pfd-delivery/SKILL.md", names)

    def test_heat_pump_distillation_keeps_distillation_route(self):
        for question in ("塔顶蒸汽再压缩热泵精馏", "MVR distillation", "VRC distillation", "MVR/VRC distillation",
                         "heat-pump distillation", "heat pump distillation column", "精馏热泵"):
            with self.subTest(question=question):
                names = {row["logical_path"] for row in design.domain_reads("source", question)}
                self.assertIn("aspen-heat-pump-distillation-replacement/SKILL.md", names)

    def test_whole_flow_distillation_and_unrelated_mvr_evaporation_do_not_combine(self):
        question = "完整流程含精馏和RO，MVR用于浓盐水蒸发"
        names = {row["logical_path"] for row in design.domain_reads("source", question)}
        self.assertNotIn("aspen-heat-pump-distillation-replacement/SKILL.md", names)
        self.assertIn("aspen-tower-optimization-workflow/SKILL.md", names)
        self.assertIn("chemical-engineering-expert/references/MACRO_DESIGN_QUALITY.md", names)
        self.assertIn("aspen-pressure-pfd-delivery/SKILL.md", names)

    def test_generic_english_column_does_not_imply_distillation(self):
        names = {row["logical_path"] for row in design.domain_reads("source", "MVR evaporation and a report column")}
        self.assertNotIn("aspen-heat-pump-distillation-replacement/SKILL.md", names)
        self.assertNotIn("aspen-tower-optimization-workflow/SKILL.md", names)

    def test_distant_english_heat_pump_and_distillation_are_not_service_phrase(self):
        names = {row["logical_path"] for row in design.domain_reads("source", "distillation recovery, RO and a heat pump for evaporation")}
        self.assertNotIn("aspen-heat-pump-distillation-replacement/SKILL.md", names)

    def test_keyword_route_explicitly_does_not_certify_service_semantics(self):
        rows = design.domain_reads("source", "MVR evaporation")
        self.assertTrue(all("reading hint" in row["routing_boundary"] for row in rows))

    def test_checker_loading_failure_is_local(self):
        with mock.patch.object(design.importlib.util, "spec_from_file_location", side_effect=ImportError("synthetic import failure")):
            result = self.run_stage(source_work="expert_plan", planning_handoff=self.reference())
        self.assertIn("EXPERT_PLAN_HANDOFF_INVALID", self.need_codes(result))
        self.assert_queries_preserved(result)

    def test_checker_return_failure_is_local(self):
        with mock.patch.object(design, "check_expert_planning", side_effect=RuntimeError("synthetic checker failure")):
            result = self.run_stage(source_work="expert_plan", planning_handoff=self.reference())
        self.assertIn("MODULE_CALL_FAILED", self.need_codes(result))
        self.assert_queries_preserved(result)

    def test_checker_is_fixed_and_caller_injection_is_rejected(self):
        reference = self.reference()
        reference["checker"] = "caller-owned.py"
        result = self.run_stage(source_work="expert_plan", planning_handoff=reference)
        self.assertIn("EXPERT_PLAN_HANDOFF_INVALID", self.need_codes(result))
        with self.assertRaises(ValueError):
            self.run_stage(source_work="expert_plan", checker="caller-owned.py")

    def test_unavailable_registered_checker_has_no_fallback(self):
        with mock.patch.object(product, "skill_location", return_value={"available": False, "path": None}):
            result = self.run_stage(source_work="expert_plan", planning_handoff=self.reference())
        self.assertIn("EXPERT_PLAN_HANDOFF_INVALID", self.need_codes(result))
        self.assert_queries_preserved(result)

    def test_reference_shape_does_not_allow_pointer_or_runner(self):
        for field in ("pointer", "runner"):
            reference = self.reference()
            reference[field] = "ignored?"
            result = self.run_stage(source_work="expert_plan", planning_handoff=reference)
            self.assertIn("EXPERT_PLAN_HANDOFF_INVALID", self.need_codes(result))

    def test_schema_declares_source_only_mode_and_strict_reference(self):
        schema = product.schema("design-stage", lambda request: {})
        self.assertEqual(schema["properties"]["source_work"]["enum"], ["expert_plan"])
        self.assertFalse(schema["$defs"]["planning_reference"]["additionalProperties"])
        self.assertEqual(schema["allOf"][0]["then"]["properties"]["stage"]["const"], "source")
        self.assertIn("source_work", schema["allOf"][1]["then"]["required"])


if __name__ == "__main__":
    unittest.main()
