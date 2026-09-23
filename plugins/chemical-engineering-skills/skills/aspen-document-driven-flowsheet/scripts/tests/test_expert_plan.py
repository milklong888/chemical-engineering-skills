"""Source-only planning structure tests using invented, nonengineering fixtures."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "check_flow_handoff.py"
spec = importlib.util.spec_from_file_location("expert_plan_draft", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture(cyclic=True):
    """Names, values and method text are synthetic; no project paper is used."""
    edges = [("arrival", "outside_a", "junction_q"),
             ("q_to_r", "junction_q", "cell_r"),
             ("r_to_s", "cell_r", "split_s"),
             ("departure", "split_s", "outside_z")]
    if cyclic:
        edges.append(("s_to_q", "split_s", "junction_q"))
    process_nodes = ["junction_q", "cell_r", "split_s"]
    data = {
        "schema": module.SCHEMA, "stage": "source",
        "authority_reference": "Invented topology fixture revision beta; not engineering evidence",
        "nodes": [{"id": identifier, "kind": "process"} for identifier in process_nodes]
                 + [{"id": identifier, "kind": "external"} for identifier in ("outside_a", "outside_z")],
        "streams": [{"id": identifier, "from": a, "to": b, "state": "documented",
                     "evidence": "Invented directed-graph fixture", "gap": None}
                    for identifier, a, b in edges],
        "control_volumes": [{"id": "fixture_boundary", "members": process_nodes,
                             "inflows": ["arrival"], "outflows": ["departure"],
                             "balance_basis": "Symbolic bookkeeping fixture only",
                             "reaction_terms": "No chemistry is asserted"}],
        "placeholders": [], "handoffs": [],
        "no_placeholders_reason": "The invented graph specifies no placeholder duties",
        "expert_plan": {
            "methods": [{"node_ids": process_nodes[:], "method": "SYNTHETIC_METHOD_ALPHA",
                         "phases": ["synthetic_phase"], "applicability": "Invented candidate for field validation only",
                         "source": "Synthetic method token; not a real engineering reference",
                         "status": "candidate", "unresolved_inputs": ["Obtain real applicability evidence"]}],
            "pressure_paths": [{"id": "budget_alpha", "node_ids": process_nodes[:],
                                "stream_ids": [edge[0] for edge in edges], "state": "symbolic",
                                "method": "Synthetic pressure-budget token",
                                "equation_or_reason": "P_terminal = P_source - loss_alpha",
                                "source": "Invented equation used only for structure tests",
                                "inputs": [{"name": "P_source", "unit": "kPa", "value_or_reference": 210},
                                           {"name": "loss_alpha", "unit": "kPa", "gap": "Synthetic loss input absent"}],
                                "refine_trigger": "Replace synthetic inputs with the actual scoped source ledger"}],
            "recycle_plan": ([{"stream_id": "s_to_q", "from": "split_s", "to": "junction_q",
                              "initialization_basis": "Future source-bound initial-state ledger; no run performed",
                              "closure_order": 1, "controlled_quantity": "Symbolic return-flow target",
                              "purge_or_terminal_basis": "Departure is the declared terminal; source review remains pending"}]
                             if cyclic else []),
            "no_recycle_reason": None if cyclic else "Invented source graph is a once-through directed chain",
        },
    }
    return data


class ExpertPlanTests(unittest.TestCase):
    def assert_invalid(self, data, fragment=None, required=True):
        result = module.check(data, require_expert_plan=required)
        self.assertEqual(result["status"], "STRUCTURE_INVALID", result)
        self.assertFalse(result["expert_plan_checked"])
        if fragment:
            self.assertIn(fragment, " ".join(result["errors"]))
        return result

    def assert_no_engineering_acceptance(self, result):
        for key in ("engineering_accepted", "execution_verified", "authority_verified", "source_inventory_verified"):
            self.assertIs(result[key], False, key)

    def test_old_mode_still_accepts_original_fields_and_undeclared_cycle(self):
        data = fixture(); del data["expert_plan"]
        result = module.check(data)
        self.assertEqual(result["status"], "STRUCTURE_VALID")
        self.assertFalse(result["expert_plan_checked"])
        self.assertNotIn("expert_plan_rows", result)
        self.assert_no_engineering_acceptance(result)

    def test_required_flag_rejects_missing_expert_plan(self):
        data = fixture(); del data["expert_plan"]
        self.assert_invalid(data, "required by --require-expert-plan")

    def test_optional_present_plan_is_checked_even_without_flag(self):
        data = fixture(); data["expert_plan"]["methods"] = []
        self.assert_invalid(data, "methods", required=False)

    def test_scaffold_cannot_use_source_only_expert_plan(self):
        data = fixture(); data["stage"] = "scaffold"
        self.assert_invalid(data, "source-only")

    def test_method_and_pressure_groups_must_cover_all_process_nodes(self):
        for section in ("methods", "pressure_paths"):
            with self.subTest(section=section):
                data = fixture(); data["expert_plan"][section][0]["node_ids"].remove("cell_r")
                self.assert_invalid(data, "missing process-node coverage ['cell_r']")

    def test_missing_or_blank_method_name_rejected(self):
        for section in ("methods", "pressure_paths"):
            for missing in (True, False):
                with self.subTest(section=section, missing=missing):
                    data = fixture()
                    if missing:
                        del data["expert_plan"][section][0]["method"]
                    else:
                        data["expert_plan"][section][0]["method"] = " "
                    self.assert_invalid(data, "method")

    def test_invalid_node_or_stream_references_rejected(self):
        for section, field, bad in (("methods", "node_ids", "outside_a"),
                                    ("pressure_paths", "node_ids", "missing_node"),
                                    ("pressure_paths", "stream_ids", "missing_stream")):
            with self.subTest(section=section, field=field):
                data = fixture(); data["expert_plan"][section][0][field].append(bad)
                self.assert_invalid(data, "unregistered identifiers")

    def test_duplicate_group_references_and_pressure_ids_rejected(self):
        for mutation in ("method_node", "pressure_stream", "pressure_id"):
            with self.subTest(mutation=mutation):
                data = fixture()
                if mutation == "method_node":
                    data["expert_plan"]["methods"][0]["node_ids"].append("cell_r")
                elif mutation == "pressure_stream":
                    data["expert_plan"]["pressure_paths"][0]["stream_ids"].append("arrival")
                else:
                    data["expert_plan"]["pressure_paths"].append(copy.deepcopy(data["expert_plan"]["pressure_paths"][0]))
                self.assert_invalid(data, "duplicate")

    def test_not_applicable_method_requires_separate_specific_reason(self):
        data = fixture(); row = data["expert_plan"]["methods"][0]
        row["status"] = "not_applicable"; row["phases"] = []
        self.assert_invalid(data, "not_applicable_reason")
        row["not_applicable_reason"] = "Synthetic record explicitly excludes property calculations for this abstract graph"
        result = module.check(data, require_expert_plan=True)
        self.assertTrue(result["expert_plan_checked"])
        self.assert_no_engineering_acceptance(result)

    def test_symbolic_pressure_requires_inputs_and_at_least_one_gap(self):
        for mode in ("empty", "all_known"):
            with self.subTest(mode=mode):
                data = fixture(); row = data["expert_plan"]["pressure_paths"][0]
                if mode == "empty":
                    row["inputs"] = []
                else:
                    row["inputs"][1] = {"name": "loss_alpha", "unit": "kPa", "value_or_reference": "synthetic reference"}
                self.assert_invalid(data, "inputs" if mode == "empty" else "symbolic requires")

    def test_pressure_input_unit_is_required_and_field_name_is_exact(self):
        for replacement in (None, "units", "blank"):
            with self.subTest(replacement=replacement):
                data = fixture(); entry = data["expert_plan"]["pressure_paths"][0]["inputs"][0]
                del entry["unit"]
                if replacement == "units":
                    entry["units"] = "kPa"
                elif replacement == "blank":
                    entry["unit"] = " "
                self.assert_invalid(data, "unit")

    def test_pressure_input_value_or_gap_is_exclusive(self):
        for mode in ("both", "neither", "null_value", "blank_gap"):
            with self.subTest(mode=mode):
                data = fixture(); entry = data["expert_plan"]["pressure_paths"][0]["inputs"][0]
                if mode == "both":
                    entry["gap"] = "Contradictory unresolved input"
                elif mode == "neither":
                    del entry["value_or_reference"]
                elif mode == "null_value":
                    entry["value_or_reference"] = None
                else:
                    del entry["value_or_reference"]; entry["gap"] = " "
                self.assert_invalid(data)

    def test_pressure_duplicate_input_names_rejected(self):
        data = fixture(); inputs = data["expert_plan"]["pressure_paths"][0]["inputs"]
        inputs.append(copy.deepcopy(inputs[0]))
        self.assert_invalid(data, "duplicate input name")

    def test_calculated_remains_unverified_and_rejects_still_missing_inputs(self):
        data = fixture(); row = data["expert_plan"]["pressure_paths"][0]
        row["state"] = "calculated"
        row["result_reference"] = "Invented result ledger row; not verified"
        self.assert_invalid(data, "calculated declaration contradicts")
        row["inputs"][1] = {"name": "loss_alpha", "unit": "kPa", "value_or_reference": 5}
        result = module.check(data, require_expert_plan=True)
        self.assertTrue(result["expert_plan_checked"])
        self.assertFalse(result["expert_plan_rows"]["pressure_paths"][0]["calculation_verified"])
        self.assertIn("caller-reported and unverified", result["scope"])
        self.assertIn("Invented result ledger row; not verified", module.markdown(result))
        self.assert_no_engineering_acceptance(result)

    def test_calculated_requires_nonempty_result_reference_only_in_that_state(self):
        for reference in (None, " "):
            with self.subTest(reference=reference):
                data = fixture(); row = data["expert_plan"]["pressure_paths"][0]
                row["state"] = "calculated"
                row["inputs"][1] = {"name": "loss_alpha", "unit": "kPa", "value_or_reference": 5}
                if reference is not None:
                    row["result_reference"] = reference
                self.assert_invalid(data, "result_reference")
        for state in ("symbolic", "not_applicable"):
            with self.subTest(state=state):
                data = fixture(); row = data["expert_plan"]["pressure_paths"][0]
                row.update({"state": state, "result_reference": "Unsupported calculation reference"})
                self.assert_invalid(data, "allowed only for calculated")

    def test_pressure_group_rejects_unrelated_streams(self):
        data = fixture()
        data["streams"].append({"id": "external_bypass", "from": "outside_a", "to": "outside_z",
                                "state": "documented", "evidence": "Synthetic outside edge", "gap": None})
        data["expert_plan"]["pressure_paths"][0]["stream_ids"].append("external_bypass")
        self.assert_invalid(data, "external_bypass does not touch any node")

    def test_pressure_group_rejects_nodes_untouched_by_its_streams(self):
        data = fixture()
        data["expert_plan"]["pressure_paths"][0]["stream_ids"] = ["arrival", "s_to_q", "departure"]
        self.assert_invalid(data, "group nodes untouched by its streams ['cell_r']")

    def test_pressure_not_applicable_needs_reason_but_no_physics_is_implied(self):
        data = fixture(); row = data["expert_plan"]["pressure_paths"][0]
        row.update({"state": "not_applicable", "inputs": [], "stream_ids": [], "equation_or_reason": " "})
        self.assert_invalid(data, "equation_or_reason")
        row["equation_or_reason"] = "Invented source excludes pressure propagation for this abstract example"
        result = module.check(data, require_expert_plan=True)
        self.assertTrue(result["expert_plan_checked"])
        self.assert_no_engineering_acceptance(result)

    def test_cycle_without_any_plan_fails_even_with_no_recycle_assertion(self):
        data = fixture(); data["expert_plan"]["recycle_plan"] = []
        self.assert_invalid(data, "provide tear plans")
        data["expert_plan"]["no_recycle_reason"] = "Caller says no recycle; this contradicts the declared cycle"
        self.assert_invalid(data, "still contains a cycle")

    def test_second_cycle_left_after_declared_tear_is_detected(self):
        data = fixture()
        data["streams"].append({"id": "r_to_q", "from": "cell_r", "to": "junction_q",
                                "state": "documented", "evidence": "Synthetic second return", "gap": None})
        self.assert_invalid(data, "still contains a cycle")
        data["expert_plan"]["recycle_plan"].append({
            **data["expert_plan"]["recycle_plan"][0], "stream_id": "r_to_q", "from": "cell_r", "closure_order": 2})
        self.assertTrue(module.check(data, require_expert_plan=True)["expert_plan_checked"])

    def test_wrong_recycle_from_or_to_fails(self):
        for endpoint in ("from", "to"):
            with self.subTest(endpoint=endpoint):
                data = fixture(); data["expert_plan"]["recycle_plan"][0][endpoint] = "cell_r"
                self.assert_invalid(data, f"{endpoint} must match actual stream")

    def test_recycle_external_endpoint_is_not_a_process_tear(self):
        data = fixture(); row = data["expert_plan"]["recycle_plan"][0]
        row.update({"stream_id": "arrival", "from": "outside_a", "to": "junction_q"})
        self.assert_invalid(data, "registered process endpoint")

    def test_unregistered_and_duplicate_recycle_streams_fail(self):
        data = fixture(); data["expert_plan"]["recycle_plan"][0]["stream_id"] = "invented_edge"
        self.assert_invalid(data, "unregistered stream")
        data = fixture(); data["expert_plan"]["recycle_plan"].append(copy.deepcopy(data["expert_plan"]["recycle_plan"][0]))
        self.assert_invalid(data, "duplicate tear stream")

    def test_duplicate_real_stream_id_still_fails(self):
        data = fixture(); data["streams"].append(copy.deepcopy(data["streams"][0]))
        self.assert_invalid(data, "duplicate id")

    def test_closure_order_must_be_positive_integer_not_boolean(self):
        for value in (0, -1, True, 1.5, "1"):
            with self.subTest(value=value):
                data = fixture(); data["expert_plan"]["recycle_plan"][0]["closure_order"] = value
                self.assert_invalid(data, "positive integer")

    def test_recycle_plan_cannot_also_assert_no_recycle(self):
        data = fixture(); data["expert_plan"]["no_recycle_reason"] = "Contradictory no-recycle declaration"
        self.assert_invalid(data, "contradict")

    def test_self_reported_verified_or_executed_status_rejected(self):
        for section, field in (("methods", "status"), ("pressure_paths", "state")):
            for value in ("executed", "verified", "accepted", "reported_unverified"):
                with self.subTest(section=section, value=value):
                    data = fixture(); data["expert_plan"][section][0][field] = value
                    self.assert_invalid(data, "no verification/run status")
        data = fixture(); data["expert_plan"]["execution_verified"] = True
        self.assert_invalid(data, "expected object")

    def test_source_only_plan_rejects_even_unverified_reported_handoff_execution(self):
        data = fixture(); data["no_placeholders_reason"] = None
        data["placeholders"] = [{"id": "abstract_duty", "node_ids": ["cell_r"],
            "purpose": "Synthetic placeholder", "valid_scope": "Abstract test", "permission_reference": "Synthetic source"}]
        data["handoffs"] = [{"id": "abstract_duty", "owner": "Synthetic owner", "selection_condition": None,
            "inputs": [{"name": "input", "reference": "synthetic input", "gap": None}],
            "required_returns": {key: "synthetic return" for key in module.RETURNS},
            "execution_status": "reported_unverified", "execution_reference": "Not an actual execution artifact"}]
        self.assert_invalid(data, "self-reported execution")
        del data["expert_plan"]
        self.assertEqual(module.check(data)["status"], "STRUCTURE_VALID")

    def test_valid_acyclic_plan_passes_with_explicit_reason(self):
        result = module.check(fixture(cyclic=False), require_expert_plan=True)
        self.assertTrue(result["expert_plan_checked"], result)
        coverage = result["expert_plan_rows"]["cycle_coverage"]
        self.assertEqual(coverage["tear_stream_ids"], [])
        self.assertEqual(coverage["topological_order_after_tears"], ["junction_q", "cell_r", "split_s"])
        self.assertFalse(coverage["source_cycles_verified"])
        self.assert_no_engineering_acceptance(result)

    def test_valid_symbolic_plan_is_structural_only_and_markdown_shows_fields(self):
        data = fixture(); result = module.check(data, require_expert_plan=True)
        self.assertEqual(result["status"], "STRUCTURE_VALID_WITH_UNRESOLVED", result)
        self.assertTrue(result["expert_plan_checked"])
        self.assert_no_engineering_acceptance(result)
        report = module.markdown(result)
        for token in ("SYNTHETIC_METHOD_ALPHA", "synthetic_phase", "budget_alpha", "P_terminal = P_source - loss_alpha",
                      "P_source", "kPa", "Synthetic loss input absent", "s_to_q", "closure order: 1",
                      "Initialization basis", "Controlled quantity", "Purge or terminal basis", "refinement trigger"):
            self.assertIn(token, report)
        self.assertIn("units/dimensions", report)

    def test_invented_units_or_equations_do_not_get_semantic_verification(self):
        data = fixture(); row = data["expert_plan"]["pressure_paths"][0]
        row["inputs"][0]["unit"] = "arbitrary_unit_token"
        row["equation_or_reason"] = "Deliberately nonphysical text, to test the documented structural boundary"
        result = module.check(data, require_expert_plan=True)
        self.assertTrue(result["expert_plan_checked"])
        self.assert_no_engineering_acceptance(result)
        self.assertIn("does not verify", result["scope"])

    def test_partial_graph_does_not_claim_source_cycle_completeness(self):
        data = fixture(cyclic=False)
        data["streams"].append({"id": "unplaced", "from": None, "to": None, "state": "unresolved",
                                "evidence": None, "gap": "Synthetic omitted connection endpoints"})
        result = module.check(data, require_expert_plan=True)
        self.assertTrue(result["expert_plan_checked"])
        coverage = result["expert_plan_rows"]["cycle_coverage"]
        self.assertEqual(coverage["coverage"], "DECLARED_PARTIAL")
        self.assertFalse(coverage["source_cycles_verified"])

    def test_nonfinite_calculation_values_fail_closed(self):
        for value in (float("inf"), float("nan"), True):
            with self.subTest(value=value):
                data = fixture(); data["expert_plan"]["pressure_paths"][0]["inputs"][0]["value_or_reference"] = value
                self.assert_invalid(data)

    def test_cli_option_reports_boundaries_and_returns_nonzero_when_missing(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as temporary:
            root = Path(temporary); source = root / "input.json"
            for present in (False, True):
                with self.subTest(present=present):
                    data = fixture()
                    if not present:
                        del data["expert_plan"]
                    source.write_text(json.dumps(data), encoding="utf-8")
                    output = root / ("present" if present else "missing")
                    run = subprocess.run([sys.executable, "-B", "-X", "utf8", str(SCRIPT),
                        "--input", str(source), "--output-dir", str(output), "--require-expert-plan"],
                        capture_output=True, text=True, encoding="utf-8")
                    self.assertEqual(run.returncode, 0 if present else 2, run.stdout + run.stderr)
                    summary = json.loads(run.stdout)
                    self.assertEqual(summary["expert_plan_checked"], present)
                    self.assertIn("declared process graph", summary["scope"])
                    report = json.loads((output / "review.json").read_text(encoding="utf-8"))
                    self.assertEqual(report["input_sha256"], module.hashlib.sha256(source.read_bytes()).hexdigest())
                    self.assert_no_engineering_acceptance(report)


if __name__ == "__main__":
    unittest.main()
