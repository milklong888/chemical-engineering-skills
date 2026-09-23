"""Synthetic dossiers only. No provider calls, network, COM, or Aspen execution.

FullflowFixture documents a complete minimum contract. Its deliberately fake
engine/provider records test structural checks, never genuine execution.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.fullflow_gate import AUXILIARIES, SCHEMA, _canonical, check_fullflow, contract_schema


class FullflowFixture:
    """Build a small two-module source/scaffold dossier with hash-bound records."""
    def __init__(self, root):
        self.root = Path(root)
        self.identity = {"case_id": "SYN-FLOW", "task_revision": "requirements-1"}
        self.source = self.put("source.txt", "SYNTHETIC source values, not design advice or an actual source.")
        self.modules = [self.module("R1", "reaction"), self.module("S1", "separation")]
        self.contract = {"schema": SCHEMA, **self.identity, "scope": {"mode": "fullflow"}, "modules": self.modules}
        self.rebuild_source()
        run_ref, record, exported = self.run("scaffold-1", self.modules, scaffold=True)
        self.scaffold_record = record
        cycle = {"schema": "fullflow-cycle-initials-v1", **self.identity, "run_id": "scaffold-1",
                 "export_sha256": record["export_ref"]["sha256"], "mode": "no_recycle", "streams": [],
                 "basis": "Synthetic open-flow topology has no recycle", "source_refs": [record["export_ref"]]}
        cycle_ref = self.put("cycle.json", cycle)
        self.contract["scaffold_gate"] = {"run_ref": run_ref, "cycle_initials_ref": cycle_ref,
            **self.reviews("scaffold", 3, {"run_id": "scaffold-1", "export_sha256": record["export_ref"]["sha256"],
                                         "cycle_initials_sha256": cycle_ref["sha256"]})}

    def put(self, name, value):
        path = self.root / name
        data = value.encode("utf-8") if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
        path.write_bytes(data)
        return {"path": name, "sha256": hashlib.sha256(data).hexdigest()}

    def read(self, reference):
        return json.loads((self.root / reference["path"]).read_text(encoding="utf-8"))

    def reference(self, name):
        return {"path": name, "sha256": hashlib.sha256((self.root / name).read_bytes()).hexdigest()}

    def rewrite(self, reference, update):
        value = self.read(reference)
        update(value)
        return self.put(reference["path"], value)

    def quantity(self, name="target"):
        return {"name": name, "value": "sourced symbolic relation", "unit_or_basis": "declared test basis", "source_ref": self.source}

    def stream(self, tag):
        return {"stream_id": tag, "composition": {"A": 1.0}, "basis": "mole fraction", "source_ref": self.source}

    def module(self, tag, role):
        thermo = {"components": ["A"], "temperature_range": "synthetic T range", "pressure_range": "synthetic P range",
                  "phases": ["vapor"], "method": "SYNTHETIC-METHOD", "applicability": "synthetic source comparison only",
                  "source_refs": [self.source]}
        requirements = {kind: {"state": "not_required", "basis": "Sourced synthetic no-service condition", "source_ref": self.source}
                        for kind in AUXILIARIES}
        auxiliaries = []
        if tag == "R1":
            for kind, node in (("heating", "H1"), ("compression", "P1")):
                requirements[kind]["state"] = "required"
                auxiliaries.append({"node_id": node, "kind": kind, "source_ref": self.source})
        module = {"id": tag, "module_revision": "module-1", "role": role, "purpose": "Synthetic module duty",
                  "node_ids": [tag], "inlets": [self.stream(tag + "-IN")], "outlets": [self.stream(tag + "-OUT")],
                  "targets": [self.quantity()], "thermodynamics": thermo, "auxiliary_requirements": requirements,
                  "auxiliaries": auxiliaries, "unknowns": []}
        module[role] = {"conditions": [self.quantity("conditions")],
                        "extent" if role == "reaction" else "targets": [self.quantity("extent or separation target")]}
        return module

    def source_review(self):
        owner = ROOT / "plugins/chemical-engineering-skills/skills/aspen-document-driven-flowsheet/scripts/check_flow_handoff.py"
        spec = importlib.util.spec_from_file_location("synthetic_source_inventory", owner)
        checker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(checker)
        documents = [{"id": "current-source", **self.source}]
        inventory = checker.source_inventory(documents, source_root=self.root, unit_mode="layout_blocks_v2")
        return {"documents": documents, "unit_mode": "layout_blocks_v2",
                "units": [{"unit_id": row["unit_id"], "disposition": "mapped",
                           "stream_ids": ["T0"],
                           "reason": "Synthetic source-to-edge declaration; source meaning is not certified"}
                          for row in inventory]}

    def handoff(self):
        process = ["H1", "R1", "P1", "S1"]
        chain = ["FEED", *process, "PRODUCT"]
        data = {"schema": "document-flow-handoff-v1", "stage": "source", "authority_reference": "Synthetic requirements-1",
                "nodes": [{"id": x, "kind": "process" if x in process else "external"} for x in chain],
                "streams": [{"id": f"T{i}", "from": a, "to": b, "state": "documented", "evidence": "synthetic source", "gap": None}
                            for i, (a, b) in enumerate(zip(chain, chain[1:]))],
                "control_volumes": [{"id": "whole", "members": process, "inflows": ["T0"], "outflows": ["T4"],
                                     "balance_basis": "synthetic molar basis", "reaction_terms": "explicit symbolic generation/consumption"}],
                "placeholders": [{"id": x, "node_ids": [x], "purpose": "synthetic duty", "valid_scope": "scaffold only",
                                  "permission_reference": "synthetic stage contract, not a user relaxation"} for x in ("R1", "S1")],
                "no_placeholders_reason": None,
                "handoffs": [{"id": x, "owner": "aspen-document-driven-flowsheet", "selection_condition": None,
                              "inputs": [{"name": "feed", "reference": "synthetic source", "gap": None}],
                              "required_returns": {key: "Concrete synthetic " + key for key in
                                                   ("method_basis", "boundary_states", "closure_targets", "execution_evidence")},
                              "execution_status": "not_executed", "execution_reference": None} for x in ("R1", "S1")]}
        data["source_review"] = self.source_review()
        return self.write_handoff(data)

    def write_handoff(self, data):
        input_ref = self.put("handoff-input.json", data)
        owner = ROOT / "plugins/chemical-engineering-skills/skills/aspen-document-driven-flowsheet/scripts/check_flow_handoff.py"
        spec = importlib.util.spec_from_file_location("synthetic_handoff_fixture", owner)
        checker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(checker)
        result = checker.check(data, source_root=self.root)
        assert result["status"] != "STRUCTURE_INVALID", result
        result.update(input_sha256=input_ref["sha256"], checker_sha256=hashlib.sha256(owner.read_bytes()).hexdigest())
        return {"handoff_input_ref": input_ref, "handoff_review_ref": self.put("handoff-review.json", result)}

    def rebuild_source(self):
        basis = {**self.identity, "modules": [{k: copy.deepcopy(v) for k, v in x.items() if k != "module_revision"} for x in self.modules]}
        basis_ref = self.put("design-basis.json", basis)
        self.contract["source_gate"] = {"design_basis_ref": basis_ref, **self.handoff(),
            **self.reviews("source", 5, {"design_basis_sha256": basis_ref["sha256"]})}
        self.contract["source_gate"]["planning_checks_ref"] = self.planning()

    def planning(self):
        module_ids = [x["id"] for x in self.modules]
        calculation = self.put("planning-pressure-calculation.json", {"method": "synthetic declared method", "pressure_drop_pa": 1000, "synthetic": True})
        common = {"module_ids": module_ids, "method": "Sourced synthetic planning method", "input_basis": "Synthetic common flow and pressure basis", "evidence_refs": [self.source]}
        record = {"schema": "fullflow-planning-checks-v1", **self.identity,
            "pressure_budget": [{**common, "state": "calculated", "calculation_ref": calculation, "result_path": "pressure_drop_pa", "unit": "Pa"}],
            "heat_strategy": [{**common, "state": "reasoned", "method": "Reduce duty, then recover compatible heat before external utility"}],
            "compression_decisions": [{**common, "state": "reasoned", "method": "Compare required pressure levels and downstream losses; avoid unnecessary repeated compression"}]}
        return self.put("planning-checks.json", record)

    def reviews(self, stage, count, bindings):
        prompt = self.put(stage + "-prompt.txt", "SYNTHETIC identical independent-review prompt " + stage)
        calls, comparisons = [], []
        for i in range(count):
            call_id = f"{stage}-call-{i}"
            if stage == "source":
                chain = [{"stream_id": x["id"], "from": x["from"], "to": x["to"]}
                         for x in self.read(self.reference("handoff-input.json"))["streams"]]
            else:
                chain = self.read(self.scaffold_record["export_ref"])["connections"]
            output = {"schema": "fullflow-independent-review-v1", **self.identity, "call_id": call_id, **bindings,
                      "process_chain": chain,
                      "module_reviews": [{"module_id": x["id"], "role_summary": x["role"], "boundary_summary": "synthetic inlet/outlet restatement",
                                          "thermodynamics_summary": "synthetic components/TP/phases/method review",
                                          "reaction_or_separation_summary": "synthetic duty, conditions and target", "issues": [],
                                          "verification_checks": self.verifications(stage, j, x)} for j, x in enumerate(self.modules)]}
            output_ref = self.put(call_id + "-output.json", output)
            record = {"schema": "fullflow-agent-call-v1", **self.identity, "stage": stage, "call_id": call_id,
                      "independent_context_id": call_id + "-context", "model_id": "gpt-6-luna" if stage == "source" else "synthetic-other-model",
                      "prompt_sha256": prompt["sha256"], "output_ref": output_ref}
            invocation = {**self.identity, **{k: record[k] for k in ("call_id", "independent_context_id", "model_id", "prompt_sha256")},
                          "invocation_id": call_id + "-invocation", "output_sha256": output_ref["sha256"], "synthetic": True}
            record["invocation_ref"] = self.put(call_id + "-invocation.json", invocation)
            calls.append(self.put(call_id + ".json", record))
            comparisons += [{"call_id": call_id, "module_id": x["id"], "output_sha256": output_ref["sha256"],
                             "issue_ids": [], "disposition": "no_difference", "rationale": "synthetic source-by-source comparison; no vote",
                             "evidence_refs": [self.source, output_ref]} for x in self.modules]
        closure = {"schema": "fullflow-difference-closure-v1", **self.identity, "reviewer_id": "synthetic-main-reviewer", "comparisons": comparisons}
        return {"prompt_ref": prompt, "independent_calls": calls, "difference_closure_ref": self.put(stage + "-closure.json", closure)}

    def verifications(self, stage, index, module):
        basis = self.reference("design-basis.json")
        handoff = self.reference("handoff-input.json")
        prefix = f"modules.{index}."
        anchors = {
            "module_purpose": [(basis, prefix + "role"), (basis, prefix + "purpose")],
            "inlet_outlet_composition": [(basis, prefix + "inlets"), (basis, prefix + "outlets")],
            "reaction_or_separation_basis": [(basis, prefix + module["role"])],
            "thermodynamic_basis": [(basis, prefix + "thermodynamics")],
            "heat_pressure_auxiliaries": [(basis, prefix + "auxiliary_requirements"), (basis, prefix + "auxiliaries")],
            "connections_terminals": [(handoff, "nodes"), (handoff, "streams")],
        }
        if stage == "scaffold":
            export = self.scaffold_record["export_ref"]
            cycle = self.reference("cycle.json")
            anchors.update({
                "actual_block_parameters": [(export, prefix + "block_type"), (export, prefix + "parameters")],
                "omitted_components": [(basis, "modules"), (export, "modules"), (export, "auxiliary_nodes")],
                "cycle_initials": [(cycle, "mode"), (cycle, "streams"), (export, "recycle_stream_ids")],
                "current_export_binding": [(export, "run_id"), (export, "model_sha256"), (export, "raw_export_ref")],
            })
        checks = {}
        for name, pairs in anchors.items():
            observations = []
            refs = []
            for reference, path in pairs:
                value = self.read(reference)
                for part in path.split("."):
                    value = value[int(part)] if isinstance(value, list) else value[part]
                observations.append({"evidence_ref": reference, "value_path": path, "value": copy.deepcopy(value)})
                if reference not in refs:
                    refs.append(reference)
            checks[name] = {"observation": observations, "evidence_refs": refs}
        return checks

    def run(self, run_id, modules, *, scaffold=False, module=None, boundary_hash=None):
        model = self.put(run_id + ".inp", "SYNTHETIC NOT ASPEN: " + run_id)
        native = {"status": "completed", "run_id": run_id, "case_sha256": model["sha256"],
                  "started_epoch": 100, "finished_epoch": 101, "synthetic": True}
        raw_export = self.put(run_id + "-raw.txt", "SYNTHETIC exporter test, not an Aspen output")
        exported = {"schema": "fullflow-model-export-v1", **self.identity, "run_id": run_id, "model_sha256": model["sha256"],
                    "raw_export_ref": raw_export, "recycle_stream_ids": [],
                    "modules": [{"module_id": x["id"], "module_revision": x["module_revision"], "original_node_ids": x["node_ids"],
                                 "node_ids": [x["id"] + "-RIGOROUS"], "block_type": ("RStoic" if x["role"] == "reaction" else "SEP") if scaffold else "RIGOROUS",
                                 "inlets": x["inlets"], "outlets": x["outlets"], "thermodynamics": x["thermodynamics"],
                                 "physical_equipment_ids": [x["id"] + "-E1"]} for x in modules],
                    "auxiliary_nodes": [{"node_id": row["node_id"], "block_type": "SYN-AUX"} for x in modules for row in x["auxiliaries"]]}
        exported["connections"] = [{"stream_id": x["id"], "from": x["from"], "to": x["to"]}
                                   for x in self.read(self.reference("handoff-input.json"))["streams"]]
        record = {"schema": "fullflow-run-evidence-v1", **self.identity, "run_id": run_id, "model_ref": model,
                  "native_run_ref": self.put(run_id + "-native.json", native)}
        if module:
            for obj in (record, exported):
                obj.update(module_id=module["id"], module_revision=module["module_revision"], boundary_sha256=boundary_hash)
        for row, source_module in zip(exported["modules"], modules):
            row["targets"] = source_module["targets"]
            row["parameters"] = {"source_conditions": source_module[source_module["role"]]["conditions"],
                                 "extent_or_targets": source_module[source_module["role"]].get("extent", source_module["role"])}
        record["export_ref"] = self.put(run_id + "-export.json", exported)
        return self.put(run_id + "-record.json", record), record, exported

    def add_islands(self, ids=("R1", "S1")):
        rows = []
        for tag in ids:
            module = next(x for x in self.modules if x["id"] == tag)
            boundary = {**self.identity, "module_id": tag, "module_revision": module["module_revision"], "original_node_ids": module["node_ids"],
                        "from_run_id": "scaffold-1", "from_export_ref": self.scaffold_record["export_ref"],
                        "from_run_ref": self.contract["scaffold_gate"]["run_ref"],
                        "inlets": module["inlets"], "outlets": module["outlets"], "targets": module["targets"]}
            boundary_ref = self.put(tag + "-boundary.json", boundary)
            route = {**self.identity, "module_id": tag, "module_revision": module["module_revision"], "boundary_sha256": boundary_ref["sha256"],
                     "owner": "aspen-document-driven-flowsheet", "method": "synthetic rigorous method", "source_refs": [self.source]}
            run_ref, run_record, run_export = self.run(tag + "-island", [module], module=module, boundary_hash=boundary_ref["sha256"])
            device = tag + "-E1"
            canonical = {"schema": "equipment-process-canonical-export-v1", "case_id": self.identity["case_id"],
                         "run_id": run_record["run_id"], "model_sha256": run_record["model_ref"]["sha256"],
                         "raw_export_sha256": run_export["raw_export_ref"]["sha256"],
                         "equipment": {device: {"family_id": "synthetic", "values": {"flow_m3_h": 1},
                                                "units": {"flow_m3_h": "m3/h"}}}}
            canonical_ref = self.put(tag + "-equipment-export.json", canonical)
            authority_ref = self.put(tag + "-equipment-authority.json", {"schema": "equipment-process-authority-v1",
                "case_id": self.identity["case_id"], "run_id": run_record["run_id"],
                "required_method": "synthetic selector test", "acceptance_criteria": ["no engineering acceptance"]})
            equipment_receipt = {"schema": "chemical-design-stage-receipt-v1", "stage": "island",
                "status": "MODULE_CHECKS_EXECUTED", "needs": [], "identity": {"case_id": self.identity["case_id"],
                    "run_id": run_record["run_id"], "source_export": canonical_ref, "authority": authority_ref},
                "inventory_coverage": {"declared_ids": [device]},
                "equipment": [{"equipment_id": device, "status": "EXECUTED", "result": {"backend_exit_code": 0},
                               "feedback": {"status": "EXECUTED", "result": {"equipment": [
                                   {"equipment_id": device, "binding_gaps": [], "revision": None}]}}}]}
            equipment_receipt["receipt_sha256"] = _canonical(equipment_receipt)
            rows.append({"module_id": tag, "module_revision": module["module_revision"], "boundary_ref": boundary_ref,
                         "specialist_route_ref": self.put(tag + "-route.json", route), "run_ref": run_ref,
                         "equipment_gate_ref": self.put(tag + "-equipment-receipt.json", equipment_receipt)})
        self.contract["islands"] = rows

    def add_reconnect(self, ids=("R1", "S1")):
        self.add_islands(ids)
        current, _, _ = self.run("current-1", self.modules)
        self.contract["current_run_ref"] = current
        replacements = []
        for tag in ids:
            module = next(x for x in self.modules if x["id"] == tag)
            row = {"module_id": tag, "module_revision": module["module_revision"], "island_run_id": tag + "-island",
                   "original_node_ids": module["node_ids"], "replacement_node_ids": [tag + "-RIGOROUS"], "installed_run_id": "current-1"}
            row["evidence_ref"] = self.put(tag + "-replacement.json", {**self.identity, **row})
            replacements.append(row)
        self.contract["replacements"] = replacements

    def check(self, stage="source", **kwargs):
        payload = {"stage": stage, "question": "Synthetic explicit fullflow workflow", **self.identity,
                   "run_id": "current-1", "fullflow_contract": self.put("contract.json", self.contract), **kwargs}
        return check_fullflow(payload, self.root)


class FullflowGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fullflow_gate_synthetic_")
        self.f = FullflowFixture(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def codes(self, result):
        return {row["code"] for row in result["needs"]}

    def consistent(self, result):
        self.assertEqual(result["status"], "EVIDENCE_STRUCTURE_CONSISTENT", result["needs"])
        self.assertFalse(result["engineering_accepted"])
        self.assertFalse(result["execution_verified"])
        self.assertFalse(result["stage_advanced"])

    def test_complete_source_is_structure_only_and_does_not_write(self):
        ref = self.f.put("contract.json", self.f.contract)
        before = {p.name: p.read_bytes() for p in self.f.root.iterdir()}
        self.consistent(check_fullflow({"stage": "source", "fullflow_contract": ref}, self.f.root))
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.f.root.iterdir()})

    def test_explicit_intent_or_authority_missing_contract_fails_closed(self):
        for payload, documents in (({"stage": "source", "question": "建立全流程模型"}, {}),
                                   ({"stage": "delivery"}, {"authority": {"workflow_profile": "fullflow_generation"}}),
                                   ({"stage": "island", "fullflow_contract": None}, {})):
            result = check_fullflow(payload, self.f.root, documents)
            self.assertTrue(result["required"])
            self.assertEqual(result["status"], "ACTION_REQUIRED")

    def test_narrow_unrelated_task_does_not_trigger(self):
        result = check_fullflow({"stage": "source", "question": "读取物流焓"}, self.f.root)
        self.assertEqual(result["status"], "NOT_APPLICABLE")

    def test_source_requires_five_not_four(self):
        self.f.contract["source_gate"]["independent_calls"].pop()
        self.assertIn("INDEPENDENT_REVIEW_COUNT", self.codes(self.f.check()))

    def test_scaffold_requires_three_not_two(self):
        self.f.contract["scaffold_gate"]["independent_calls"].pop()
        self.assertIn("INDEPENDENT_REVIEW_COUNT", self.codes(self.f.check("scaffold")))

    def test_duplicate_call_identity_does_not_count_twice(self):
        rows = self.f.contract["source_gate"]["independent_calls"]
        rows[1] = rows[0]
        codes = self.codes(self.f.check())
        self.assertIn("DUPLICATE_CALL_ID", codes)
        self.assertIn("NONINDEPENDENT_REVIEW", codes)

    def test_source_wrong_model_is_not_luna(self):
        rows = self.f.contract["source_gate"]["independent_calls"]
        rows[0] = self.f.rewrite(rows[0], lambda x: x.update(model_id="gpt-5.6-sol"))
        self.assertIn("REVIEW_MODEL_MISMATCH", self.codes(self.f.check()))

    def test_prior_luna_model_does_not_count_for_current_source_gate(self):
        rows = self.f.contract["source_gate"]["independent_calls"]
        row = self.f.read(rows[0])
        invocation = self.f.read(row["invocation_ref"])
        invocation["model_id"] = "gpt-5.6-luna"
        row["invocation_ref"] = self.f.put(row["invocation_ref"]["path"], invocation)
        row["model_id"] = "gpt-5.6-luna"
        rows[0] = self.f.put(rows[0]["path"], row)
        self.assertIn("REVIEW_MODEL_MISMATCH", self.codes(self.f.check()))

    def test_old_prompt_rejected(self):
        self.f.contract["source_gate"]["prompt_ref"] = self.f.put("new-prompt.txt", "different prompt")
        self.assertIn("REVIEW_PROMPT_MISMATCH", self.codes(self.f.check()))

    def test_missing_invocation_is_not_a_real_call_record(self):
        rows = self.f.contract["source_gate"]["independent_calls"]
        rows[0] = self.f.rewrite(rows[0], lambda x: x.pop("invocation_ref"))
        self.assertIn("EVIDENCE_UNAVAILABLE", self.codes(self.f.check()))

    def test_each_module_needs_thermodynamic_sources(self):
        self.f.modules[0]["thermodynamics"]["source_refs"] = []
        self.f.rebuild_source()
        self.assertEqual(self.f.check()["status"], "ACTION_REQUIRED")

    def test_empty_composition_is_not_complete(self):
        self.f.modules[0]["inlets"][0]["composition"] = {}
        self.f.rebuild_source()
        self.assertIn("EMPTY_OR_INVALID_COMPOSITION", self.codes(self.f.check()))

    def test_required_heat_and_pressure_nodes_cannot_be_omitted(self):
        self.f.modules[0]["auxiliaries"] = []
        self.f.rebuild_source()
        self.assertIn("REQUIRED_AUXILIARY_MISSING", self.codes(self.f.check()))

    def test_unknown_requires_external_search_record_and_fallback_source(self):
        self.f.modules[0]["unknowns"] = [{"question": "unknown mechanism", "resolution": "claimed resolved"}]
        self.f.rebuild_source()
        self.assertEqual(self.f.check()["status"], "ACTION_REQUIRED")

    def test_no_hit_lookup_with_sourced_fallback_is_allowed(self):
        response = self.f.put("lookup-response.txt", "SYNTHETIC lookup found no result")
        lookup = {**self.f.identity, "query": "specific mechanism", "source_scope": "declared external monograph",
                  "response_ref": response, "result": "no_hits"}
        self.f.modules[0]["unknowns"] = [{"question": "specific mechanism", "external_search_ref": self.f.put("lookup.json", lookup),
            "fallback_reason": "No hit; derive from the independently sourced balance", "resolution": "bounded sourced derivation",
            "resolution_sources": [self.f.source]}]
        self.f.rebuild_source()
        self.consistent(self.f.check())

    def test_complete_scaffold_allows_other_review_models_and_no_recycle(self):
        self.consistent(self.f.check("scaffold"))

    def test_missing_run_cannot_be_replaced_with_pass_flag(self):
        self.f.contract["scaffold_gate"]["run_ref"] = self.f.put("false-run.json", {"passed": True})
        result = self.f.check("scaffold")
        self.assertIn("RUN_RECORD_REQUIRED", self.codes(result))

    def test_old_scaffold_review_run_is_rejected(self):
        rows = self.f.contract["scaffold_gate"]["independent_calls"]
        record = self.f.read(rows[0])
        record["output_ref"] = self.f.rewrite(record["output_ref"], lambda x: x.update(run_id="older-run"))
        rows[0] = self.f.put(rows[0]["path"], record)
        self.assertIn("STALE_REVIEW_BASIS", self.codes(self.f.check("scaffold")))

    def test_scaffold_default_block_types_are_checked(self):
        ref = self.f.contract["scaffold_gate"]["run_ref"]
        record = self.f.read(ref)
        record["export_ref"] = self.f.rewrite(record["export_ref"], lambda x: x["modules"][0].update(block_type="RYIELD"))
        self.f.contract["scaffold_gate"]["run_ref"] = self.f.put(ref["path"], record)
        self.assertIn("SCAFFOLD_MODEL_TYPE", self.codes(self.f.check("scaffold")))

    def test_missing_exported_auxiliaries_are_reported(self):
        ref = self.f.contract["scaffold_gate"]["run_ref"]
        record = self.f.read(ref)
        record["export_ref"] = self.f.rewrite(record["export_ref"], lambda x: x.update(auxiliary_nodes=[]))
        self.f.contract["scaffold_gate"]["run_ref"] = self.f.put(ref["path"], record)
        self.assertIn("SCAFFOLD_AUXILIARY_MISSING", self.codes(self.f.check("scaffold")))

    def test_handoff_review_does_not_override_actual_structure(self):
        gate = self.f.contract["source_gate"]
        gate["handoff_input_ref"] = self.f.rewrite(gate["handoff_input_ref"], lambda x: x["streams"][0].update(to="S1"))
        self.assertIn("HANDOFF_INCOMPLETE", self.codes(self.f.check()))

    def test_difference_closure_must_cover_every_call_module(self):
        gate = self.f.contract["source_gate"]
        gate["difference_closure_ref"] = self.f.rewrite(gate["difference_closure_ref"], lambda x: x["comparisons"].pop())
        self.assertIn("DIFFERENCE_COVERAGE", self.codes(self.f.check()))

    def test_module_island_does_not_require_other_islands_or_replacements(self):
        self.f.contract["scope"] = {"mode": "module", "module_ids": ["R1"]}
        self.f.add_islands(["R1"])
        result = self.f.check("island")
        self.consistent(result)
        self.assertFalse(result["gate_summary"]["equipment_scope"]["whole_flow_required"])
        self.assertEqual(result["gate_summary"]["equipment_scope"]["module_ids"], ["R1"])

    def test_each_refined_island_must_pass_equipment_gate_before_reconnect(self):
        self.f.contract["scope"] = {"mode": "module", "module_ids": ["R1"]}
        self.f.add_islands(["R1"])
        self.f.contract["islands"][0].pop("equipment_gate_ref")
        self.assertIn("ISLAND_EQUIPMENT_GATE_REQUIRED", self.codes(self.f.check("island")))
        self.assertIn("ISLAND_EQUIPMENT_GATE_REQUIRED", self.codes(self.f.check("reconnect")))

    def test_island_selector_must_match_full_physical_inventory(self):
        self.f.contract["scope"] = {"mode": "module", "module_ids": ["R1"]}
        self.f.add_islands(["R1"])
        row = self.f.contract["islands"][0]
        def omit_device(receipt):
            receipt["inventory_coverage"]["declared_ids"] = []
            receipt["receipt_sha256"] = _canonical({k: v for k, v in receipt.items() if k != "receipt_sha256"})
        row["equipment_gate_ref"] = self.f.rewrite(row["equipment_gate_ref"], omit_device)
        self.assertIn("ISLAND_EQUIPMENT_COVERAGE", self.codes(self.f.check("island")))

    def test_island_accepts_existing_stage_receipt_uppercase_digest(self):
        self.f.contract["scope"] = {"mode": "module", "module_ids": ["R1"]}
        self.f.add_islands(["R1"])
        row = self.f.contract["islands"][0]
        row["equipment_gate_ref"] = self.f.rewrite(row["equipment_gate_ref"],
            lambda receipt: receipt.update(receipt_sha256=receipt["receipt_sha256"].upper()))
        self.consistent(self.f.check("island"))

    def test_island_equipment_candidate_is_not_a_completed_module(self):
        self.f.contract["scope"] = {"mode": "module", "module_ids": ["R1"]}
        self.f.add_islands(["R1"])
        row = self.f.contract["islands"][0]
        def leave_limit(receipt):
            receipt["equipment"][0]["feedback"]["result"]["equipment"][0]["revision"] = {
                "preferred_route": "pump_series", "status": "REVIEW_CANDIDATE"}
            receipt["receipt_sha256"] = _canonical({k: v for k, v in receipt.items() if k != "receipt_sha256"})
        row["equipment_gate_ref"] = self.f.rewrite(row["equipment_gate_ref"], leave_limit)
        self.assertIn("ISLAND_EQUIPMENT_PENDING", self.codes(self.f.check("island")))

    def test_stale_equipment_run_cannot_close_current_island(self):
        self.f.contract["scope"] = {"mode": "module", "module_ids": ["R1"]}
        self.f.add_islands(["R1"])
        row = self.f.contract["islands"][0]
        def old_run(receipt):
            receipt["identity"]["run_id"] = "old-island-run"
            receipt["receipt_sha256"] = _canonical({k: v for k, v in receipt.items() if k != "receipt_sha256"})
        row["equipment_gate_ref"] = self.f.rewrite(row["equipment_gate_ref"], old_run)
        self.assertIn("ISLAND_EQUIPMENT_RUN_MISMATCH", self.codes(self.f.check("island")))

    def test_island_still_requires_source_and_scaffold_gates(self):
        self.f.contract["scope"] = {"mode": "module", "module_ids": ["R1"]}
        self.f.add_islands(["R1"])
        self.f.contract.pop("scaffold_gate")
        self.assertEqual(self.f.check("island")["status"], "ACTION_REQUIRED")

    def test_module_revision_invalidates_only_its_island_not_source_scaffold(self):
        self.f.contract["scope"] = {"mode": "module", "module_ids": ["R1"]}
        self.f.add_islands(["R1"])
        self.f.modules[0]["module_revision"] = "module-2"
        result = self.f.check("island")
        self.assertIn("STALE_ISLAND_REVISION", self.codes(result))
        self.assertEqual(result["gate_summary"]["source"]["status"], "STRUCTURE_CONSISTENT")
        self.assertEqual(result["gate_summary"]["scaffold"]["status"], "STRUCTURE_CONSISTENT")
        self.f.add_islands(["R1"])
        self.consistent(self.f.check("island"))

    def test_partial_reconnect_preserves_untouched_modules(self):
        self.f.contract["scope"] = {"mode": "module", "module_ids": ["R1"]}
        self.f.add_reconnect(["R1"])
        self.consistent(self.f.check("reconnect"))

    def test_full_delivery_requires_replacement_coverage_despite_local_scope(self):
        self.f.contract["scope"] = {"mode": "module", "module_ids": ["R1"]}
        self.f.add_reconnect(["R1"])
        result = self.f.check("delivery")
        self.assertEqual(result["status"], "ACTION_REQUIRED")
        self.assertTrue(result["gate_summary"]["equipment_scope"]["whole_flow_required"])

    def test_complete_delivery_is_not_engineering_acceptance(self):
        self.f.add_reconnect()
        self.consistent(self.f.check("delivery"))

    def test_wrong_current_run_cannot_reuse_reconnection(self):
        self.f.add_reconnect()
        result = self.f.check("delivery", run_id="newer-run")
        self.assertIn("STALE_CURRENT_RUN", self.codes(result))

    def test_contract_hash_or_task_revision_drift_fails_closed(self):
        ref = self.f.put("contract.json", self.f.contract)
        (self.f.root / ref["path"]).write_text("{}", encoding="utf-8")
        self.assertIn("EVIDENCE_UNAVAILABLE", self.codes(check_fullflow({"fullflow_contract": ref}, self.f.root)))
        self.assertIn("CONTRACT_CURRENT_IDENTITY", self.codes(self.f.check(task_revision="requirements-2")))

    def test_bad_shape_returns_local_needs_not_an_exception(self):
        self.f.contract["modules"] = [{"id": "R1", "role": []}]
        result = self.f.check()
        self.assertEqual(result["status"], "ACTION_REQUIRED")
        self.assertTrue(result["needs"])

    def test_schema_is_discoverable_and_no_extra_model_service_is_required(self):
        self.assertEqual(contract_schema()["schema"], SCHEMA)
        self.assertFalse(contract_schema()["engineering_accepted"])

    def test_source_never_requires_a_full_equipment_inventory(self):
        result = self.f.check("source")
        self.consistent(result)
        self.assertFalse(result["gate_summary"]["equipment_scope"]["whole_flow_required"])

    def test_formal_source_requires_source_to_topology_review(self):
        gate = self.f.contract["source_gate"]
        handoff = self.f.read(gate["handoff_input_ref"])
        del handoff["source_review"]
        gate.update(self.f.write_handoff(handoff))
        gate.update(self.f.reviews("source", 5, {"design_basis_sha256": gate["design_basis_ref"]["sha256"]}))
        result = self.f.check("source")
        self.assertIn("SOURCE_REVIEW_REQUIRED", self.codes(result))
        self.assertFalse(result["engineering_accepted"])

    def test_delivery_intent_triggers_without_a_contract_but_explanation_does_not(self):
        for question in ("全流程接回后交付", "校核全流程设备", "repair the full flowsheet", "deliver full-flow results"):
            result = check_fullflow({"stage": "delivery", "question": question}, self.f.root)
            self.assertTrue(result["required"], question)
            self.assertEqual(result["status"], "ACTION_REQUIRED")
            self.assertTrue(result["gate_summary"]["equipment_scope"]["whole_flow_required"])
        for question in ("仅解释全流程构建方法", "改写全流程建模说明", "explain full-flow modeling", "全流程图示对照"):
            self.assertFalse(check_fullflow({"stage": "source", "question": question}, self.f.root)["required"], question)

    def test_authorized_proposed_source_edge_is_not_observed_connectivity(self):
        gate = self.f.contract["source_gate"]
        data = self.f.read(gate["handoff_input_ref"])
        data["streams"][0]["state"] = "proposed"
        gate.update(self.f.write_handoff(data))
        gate.update(self.f.reviews("source", 5, {"design_basis_sha256": gate["design_basis_ref"]["sha256"]}))
        self.assertIn("HANDOFF_INCOMPLETE", self.codes(self.f.check()))
        approval = {**self.f.identity, "stream_ids": ["T0"], "basis": "Synthetic permitted auxiliary connection", "authority_ref": self.f.source}
        gate["proposal_authorizations"] = [self.f.put("proposal-approval.json", approval)]
        self.consistent(self.f.check())
        self.assertEqual(self.f.read(gate["handoff_review_ref"])["status"], "STRUCTURE_VALID_WITH_UNRESOLVED")

    def test_wrong_island_origin_run_and_boundary_values_fail(self):
        self.f.contract["scope"] = {"mode": "module", "module_ids": ["R1"]}
        self.f.add_islands(["R1"])
        row = self.f.contract["islands"][0]
        row["boundary_ref"] = self.f.rewrite(row["boundary_ref"], lambda x: x.update(from_run_id="some-other-run"))
        self.assertIn("ISLAND_ORIGIN_RUN_MISMATCH", self.codes(self.f.check("island")))
        self.f.add_islands(["R1"])
        row = self.f.contract["islands"][0]
        row["boundary_ref"] = self.f.rewrite(row["boundary_ref"], lambda x: x["inlets"][0].update(composition={"B": 1}))
        self.assertIn("ISLAND_BOUNDARY_STATE_MISMATCH", self.codes(self.f.check("island")))

    def mutate_export(self, record_ref, change):
        record = self.f.read(record_ref)
        record["export_ref"] = self.f.rewrite(record["export_ref"], change)
        return self.f.put(record_ref["path"], record)

    def test_island_export_property_basis_cannot_disappear(self):
        self.f.contract["scope"] = {"mode": "module", "module_ids": ["R1"]}
        self.f.add_islands(["R1"])
        row = self.f.contract["islands"][0]
        row["run_ref"] = self.mutate_export(row["run_ref"], lambda x: x["modules"][0].pop("thermodynamics"))
        self.assertIn("ISLAND_PROPERTY_MISMATCH", self.codes(self.f.check("island")))

    def test_reconnection_property_basis_cannot_change_silently(self):
        self.f.add_reconnect()
        self.f.contract["current_run_ref"] = self.mutate_export(self.f.contract["current_run_ref"],
            lambda x: x["modules"][0]["thermodynamics"].update(method="WRONG-METHOD"))
        self.assertIn("RECONNECT_PROPERTY_MISMATCH", self.codes(self.f.check("delivery")))

    def test_duplicate_current_export_module_is_not_overwritten(self):
        self.f.add_reconnect()
        self.f.contract["current_run_ref"] = self.mutate_export(self.f.contract["current_run_ref"],
            lambda x: x["modules"].append(copy.deepcopy(x["modules"][0])))
        self.assertIn("RECONNECT_MODULE_DUPLICATE_OR_INVALID", self.codes(self.f.check("delivery")))

    def test_current_equipment_export_needs_exact_model_and_raw_export_binding(self):
        self.f.add_reconnect()
        record = self.f.read(self.f.contract["current_run_ref"])
        exported = self.f.read(record["export_ref"])
        source = {"case_id": self.f.identity["case_id"], "run_id": "current-1", "model_sha256": record["model_ref"]["sha256"],
                  "raw_export_sha256": exported["raw_export_ref"]["sha256"]}
        payload = {"stage": "delivery", **self.f.identity, "run_id": "current-1", "fullflow_contract": self.f.put("contract.json", self.f.contract)}
        self.consistent(check_fullflow(payload, self.f.root, {"source_export": source}))
        source["model_sha256"] = "0" * 64
        self.assertIn("CURRENT_EXPORT_MODEL_BINDING", self.codes(check_fullflow(payload, self.f.root, {"source_export": source})))

    def test_authorized_module_property_change_preserves_source_reviews(self):
        from tools.fullflow_gate import _canonical
        self.f.contract["scope"] = {"mode": "module", "module_ids": ["R1"]}
        self.f.add_islands(["R1"])
        row = self.f.contract["islands"][0]
        changed = copy.deepcopy(self.f.modules[0]["thermodynamics"])
        changed["method"] = "SYN-REVIEWED-ALTERNATIVE"
        approval = {**self.f.identity, "module_id": "R1", "module_revision": "module-1",
                    "prior_thermodynamics_sha256": _canonical(self.f.modules[0]["thermodynamics"]),
                    "basis": "Synthetic explicit physical reason and project change authorization",
                    "authority_ref": self.f.source, "thermodynamics": changed}
        row["thermodynamics_change_ref"] = self.f.put("R1-property-change.json", approval)
        row["run_ref"] = self.mutate_export(row["run_ref"], lambda x: x["modules"][0].update(thermodynamics=changed))
        self.consistent(self.f.check("island"))

    def test_source_planning_pressure_cannot_be_deferred_to_final_selection(self):
        self.f.contract["source_gate"].pop("planning_checks_ref")
        result = self.f.check("source")
        self.assertEqual(result["status"], "ACTION_REQUIRED")
        self.assertTrue(any("planning_checks_ref" in row["scope"] for row in result["needs"]))

    def test_pressure_planning_pass_boolean_is_not_a_calculation(self):
        gate = self.f.contract["source_gate"]
        record = self.f.read(gate["planning_checks_ref"])
        record["pressure_budget"][0]["calculation_ref"] = self.f.put("fake-pressure.json", {"pressure_drop_pa": True})
        gate["planning_checks_ref"] = self.f.put("planning-checks.json", record)
        self.assertIn("PLANNING_CALCULATION_EVIDENCE_REQUIRED", self.codes(self.f.check()))

    def test_provisional_planning_bounds_keep_geometry_gap_and_refine_trigger(self):
        gate = self.f.contract["source_gate"]
        record = self.f.read(gate["planning_checks_ref"])
        row = record["pressure_budget"][0]
        row.update(state="provisional_bounds", bounds={"lower": 500, "upper": 1500, "unit": "Pa", "source_ref": self.f.source},
                   unresolved_inputs=["same-device exchanger geometry"], refine_trigger="Recalculate when source-authorized geometry is available")
        gate["planning_checks_ref"] = self.f.put("planning-checks.json", record)
        result = self.f.check()
        self.consistent(result)
        self.assertEqual(result["gate_summary"]["planning_records"][0]["state"], "provisional_bounds")
        row.pop("refine_trigger")
        gate["planning_checks_ref"] = self.f.put("planning-checks.json", record)
        self.assertEqual(self.f.check()["status"], "ACTION_REQUIRED")

    def test_planning_not_applicable_is_sourced_and_blocked_is_local(self):
        gate = self.f.contract["source_gate"]
        record = self.f.read(gate["planning_checks_ref"])
        record["compression_decisions"][0]["module_ids"] = ["R1"]
        record["compression_decisions"].append({**record["compression_decisions"][0], "module_ids": ["S1"],
            "state": "not_applicable", "reason": "This source module has no compression service"})
        gate["planning_checks_ref"] = self.f.put("planning-checks.json", record)
        self.consistent(self.f.check())
        record["pressure_budget"][0].update(state="blocked", reason="No sourced pressure-loss inputs or bounds available")
        gate["planning_checks_ref"] = self.f.put("planning-checks.json", record)
        result = self.f.check()
        self.assertIn("PLANNING_ITEM_UNRESOLVED", self.codes(result))
        self.assertEqual(len(result["gate_summary"]["planning_records"]), 4)

    def change_review(self, stage, change):
        gate = self.f.contract[stage + "_gate"]
        record = self.f.read(gate["independent_calls"][0])
        old_output = record["output_ref"]
        record["output_ref"] = self.f.rewrite(old_output, change)
        record["invocation_ref"] = self.f.rewrite(record["invocation_ref"], lambda x: x.update(output_sha256=record["output_ref"]["sha256"]))
        gate["independent_calls"][0] = self.f.put(gate["independent_calls"][0]["path"], record)
        closure = self.f.read(gate["difference_closure_ref"])
        for comparison in closure["comparisons"]:
            if comparison["call_id"] == record["call_id"]:
                comparison["output_sha256"] = record["output_ref"]["sha256"]
                comparison["evidence_refs"] = [record["output_ref"] if r == old_output else r for r in comparison["evidence_refs"]]
        gate["difference_closure_ref"] = self.f.put(gate["difference_closure_ref"]["path"], closure)

    def test_four_summaries_do_not_replace_complete_source_verification(self):
        self.change_review("source", lambda x: x["module_reviews"][0].pop("verification_checks"))
        self.assertIn("VERIFICATION_CHECK_COVERAGE", self.codes(self.f.check()))

    def test_observed_ok_text_is_not_actual_parameter_evidence(self):
        def change(data):
            data["module_reviews"][0]["verification_checks"]["thermodynamic_basis"]["observation"][0]["value"] = "已考虑 OK"
        self.change_review("source", change)
        self.assertIn("VERIFICATION_OBSERVATION_MISMATCH", self.codes(self.f.check()))

    def test_observation_preserves_json_value_types(self):
        def change(data):
            observation = data["module_reviews"][0]["verification_checks"]["inlet_outlet_composition"]["observation"][0]
            observation["value"][0]["composition"]["A"] = True
        self.change_review("source", change)
        self.assertIn("VERIFICATION_OBSERVATION_MISMATCH", self.codes(self.f.check()))

    def test_scaffold_restatement_cannot_skip_cycle_or_actual_parameters(self):
        self.change_review("scaffold", lambda x: x["module_reviews"][0]["verification_checks"].pop("cycle_initials"))
        self.assertIn("VERIFICATION_CHECK_COVERAGE", self.codes(self.f.check("scaffold")))

    def test_generic_process_sentence_is_not_complete_flow_chain(self):
        self.change_review("source", lambda x: x.update(process_chain=["所有模块已经检查"]))
        self.assertIn("REVIEW_PROCESS_CHAIN_MISMATCH", self.codes(self.f.check()))

    def test_discovery_covers_installed_nested_records_without_test_fixture(self):
        discovered = contract_schema()
        self.assertTrue(discovered["discovery_only"])
        self.assertIn("verification_check", discovered["nested_fields"])
        self.assertIn("fullflow-planning-checks-v1", discovered["record_schemas"])
        self.assertIn("from_run_ref", discovered["nested_fields"]["island_boundary"])
        self.assertIn("evidence_ref", discovered["nested_fields"]["observation"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
