"""Synthetic declaration tests only; no project answer or engineering result is used.

Run with Python -B so the isolated draft does not create bytecode files.
CLI tests mock all output writes and use only in-memory synthetic input.
"""
import copy
import importlib.util
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch


TEST_DIRECTORY = Path(__file__).resolve().parent
SCRIPT = ((TEST_DIRECTORY.parent if TEST_DIRECTORY.name == "tests" else TEST_DIRECTORY)
          / "check_flow_handoff.py")
spec = importlib.util.spec_from_file_location("plan_actions_draft", SCRIPT)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def action(stream_id):
    return {
        "stream_id": stream_id,
        "receiver_requirement": "Synthetic receiver condition; not engineering evidence",
        "budget_relation": "Synthetic symbolic relation; no formula is verified",
        "equipment_action": "Conditional symbolic action, not a selected real device",
        "condition_or_basis": "Invented declaration for this test only",
    }


def startup(seed, dependencies):
    return {
        "temporary_boundary": "Synthetic temporary boundary declaration",
        "forward_pass": "Synthetic forward-pass description; not actually executed",
        "seed_outlet_stream_id": seed,
        "depends_on_recycles": list(dependencies),
        "closure_reason": "Synthetic dependency basis; not an engineering conclusion",
    }


def fixture():
    process = ["A", "B", "C"]
    edges = [("feed", "IN", "A"), ("ab", "A", "B"), ("bc", "B", "C"),
             ("product", "C", "OUT"), ("r1", "B", "A"), ("r2", "C", "A")]
    return {
        "schema": checker.SCHEMA, "stage": "source",
        "authority_reference": "Synthetic action-declaration fixture; no project authority",
        "nodes": [{"id": value, "kind": "process"} for value in process]
                 + [{"id": value, "kind": "external"} for value in ("IN", "OUT")],
        "streams": [{"id": identifier, "from": source, "to": target,
                     "state": "documented", "evidence": "Invented graph edge", "gap": None}
                    for identifier, source, target in edges],
        "control_volumes": [{"id": "whole", "members": process[:],
                             "inflows": ["feed"], "outflows": ["product"],
                             "balance_basis": "Synthetic symbolic basis",
                             "reaction_terms": "No chemistry is asserted"}],
        "placeholders": [], "no_placeholders_reason": "Synthetic graph has no placeholder duty",
        "handoffs": [],
        "expert_plan": {
            "methods": [{"node_ids": process[:], "method": "Synthetic method",
                         "phases": ["synthetic_phase"], "applicability": "Invented applicability",
                         "source": "Invented source", "status": "candidate", "unresolved_inputs": [],
                         "named_methods": [{"name": "SYNTHETIC_SOURCE_DEFINED_MODEL",
                                            "name_origin": "source_defined",
                                            "source_ref": "Synthetic source token",
                                            "applies_when": "Only an invented structural test",
                                            "definition_ref": "Synthetic definition token"}]}],
            "pressure_paths": [{"id": "branch_group", "node_ids": process[:],
                                "stream_ids": [edge[0] for edge in edges], "state": "symbolic",
                                "method": "Synthetic pressure declaration",
                                "equation_or_reason": "Symbolic statement, not a checked equation",
                                "source": "Synthetic source", "refine_trigger": "Obtain real evidence",
                                "inputs": [{"name": "unknown_parameter", "unit": "synthetic_unit",
                                            "gap": "Synthetic unresolved input"}],
                                "interface_actions": [action(edge[0]) for edge in edges]}],
            "recycle_plan": [{"stream_id": "r1", "from": "B", "to": "A",
                              "initialization_basis": "Synthetic opening basis, not a result",
                              "closure_order": 10, "controlled_quantity": "Synthetic controlled item",
                              "purge_or_terminal_basis": "Synthetic terminal declaration",
                              "startup_plan": startup("r1", [])},
                             {"stream_id": "r2", "from": "C", "to": "A",
                              "initialization_basis": "Synthetic opening basis, not a result",
                              "closure_order": 20, "controlled_quantity": "Synthetic controlled item",
                              "purge_or_terminal_basis": "Synthetic terminal declaration",
                              "startup_plan": startup("product", ["r1"])}],
            "no_recycle_reason": None,
        },
    }


def pressure(data):
    return data["expert_plan"]["pressure_paths"][0]


def recycle(data, index=0):
    return data["expert_plan"]["recycle_plan"][index]


def without_actions(data):
    for row in data["expert_plan"]["pressure_paths"]:
        row.pop("interface_actions", None)
    for row in data["expert_plan"]["recycle_plan"]:
        row.pop("startup_plan", None)
    return data


class PlanActionTests(unittest.TestCase):
    def assert_unverified(self, result):
        for flag in ("engineering_accepted", "execution_verified", "authority_verified",
                     "source_inventory_verified"):
            self.assertIs(result[flag], False, flag)
        if result.get("expert_plan_rows", {}).get("cycle_coverage"):
            self.assertIs(result["expert_plan_rows"]["cycle_coverage"]["source_cycles_verified"], False)

    def valid(self, data, strict=True):
        before = copy.deepcopy(data)
        result = checker.check(data, require_plan_actions=strict)
        self.assertEqual(result["errors"], [])
        self.assertNotEqual(result["status"], "STRUCTURE_INVALID")
        self.assert_unverified(result)
        self.assertEqual(data, before, "The checker must not mutate the input ledger")
        return result

    def invalid(self, data, expected, strict=True):
        result = checker.check(data, require_plan_actions=strict)
        self.assertEqual(result["status"], "STRUCTURE_INVALID")
        self.assertTrue(result["errors"])
        self.assertIn(expected, " ".join(result["errors"]))
        self.assertIs(result["plan_action_declarations_checked"], False)
        self.assert_unverified(result)
        rendered = checker.markdown(result)
        self.assertIn("Engineering accepted: false", rendered)
        return result

    def test_strict_success_flags_and_inert_boundaries(self):
        result = self.valid(fixture())
        for flag in ("expert_plan_checked", "named_method_declarations_checked",
                     "plan_action_declarations_checked"):
            self.assertIs(result[flag], True)
        self.assertEqual(result["status"], "STRUCTURE_VALID_WITH_UNRESOLVED")
        self.assertIn("units/dimensions", result["scope"])
        self.assertIn("computed seeds", result["scope"])

    def test_projected_endpoints_and_markdown(self):
        result = self.valid(fixture())
        row = result["expert_plan_rows"]["pressure_paths"][0]["interface_actions"][1]
        self.assertEqual((row["stream_id"], row["from"], row["to"]), ("ab", "A", "B"))
        rendered = checker.markdown(result)
        self.assertIn("Interface action ab: A -> B", rendered)
        self.assertIn("Temporary boundary:", rendered)
        self.assertIn("Declared seed outlet (not computed or verified):", rendered)
        self.assertIn("Plan-action declarations checked: true", rendered)

    def test_ordinary_legacy_record_compatible(self):
        data = fixture()
        del data["expert_plan"]
        result = self.valid(data, strict=False)
        self.assertIs(result["plan_action_declarations_checked"], False)
        self.assertIs(result["expert_plan_checked"], False)

    def test_expert_legacy_record_and_named_mode_compatible(self):
        data = without_actions(fixture())
        result = checker.check(data, require_named_methods=True)
        self.assertEqual(result["errors"], [])
        self.assertIs(result["named_method_declarations_checked"], True)
        self.assertIs(result["plan_action_declarations_checked"], False)
        del data["expert_plan"]["methods"][0]["named_methods"]
        result = checker.check(data, require_expert_plan=True)
        self.assertEqual(result["errors"], [])
        self.assertIs(result["expert_plan_checked"], True)
        self.assertIs(result["named_method_declarations_checked"], False)

    def test_strict_mode_implies_both_existing_requirements(self):
        data = fixture()
        del data["expert_plan"]
        self.invalid(data, "expert_plan: required")
        data = fixture()
        del data["expert_plan"]["methods"][0]["named_methods"]
        self.invalid(data, "named_methods: required")

    def test_strict_mode_requires_pressure_and_startup_actions(self):
        for field in ("interface_actions", "startup_plan"):
            with self.subTest(field=field):
                data = fixture()
                row = pressure(data) if field == "interface_actions" else recycle(data)
                del row[field]
                self.invalid(data, field + ": required")

    def test_optional_actions_are_checked_without_activating_named_requirement(self):
        data = without_actions(fixture())
        del data["expert_plan"]["methods"][0]["named_methods"]
        pressure(data)["interface_actions"] = [action(sid) for sid in pressure(data)["stream_ids"]]
        result = self.valid(data, strict=False)
        self.assertIs(result["plan_action_declarations_checked"], True)
        self.assertIs(result["named_method_declarations_checked"], False)
        pressure(data)["interface_actions"][0]["receiver_requirement"] = " "
        self.invalid(data, "receiver_requirement", strict=False)

    def test_optional_startup_shape_is_checked(self):
        data = without_actions(fixture())
        recycle(data)["startup_plan"] = startup("r1", [])
        self.valid(data, strict=False)
        recycle(data)["startup_plan"] = "not an object"
        self.invalid(data, "expected object", strict=False)

    def test_missing_extra_duplicate_and_unknown_action_streams(self):
        data = fixture()
        pressure(data)["interface_actions"].pop()
        self.invalid(data, "missing ['r2']")
        data = fixture()
        pressure(data)["stream_ids"].remove("product")
        self.invalid(data, "unexpected ['product']")
        data = fixture()
        pressure(data)["interface_actions"].append(action("feed"))
        self.invalid(data, "duplicate identifiers")
        data = fixture()
        pressure(data)["interface_actions"].append(action("unknown"))
        self.invalid(data, "unregistered identifiers")

    def test_empty_pressure_descriptions_rejected(self):
        for field in ("receiver_requirement", "budget_relation", "equipment_action", "condition_or_basis"):
            for blank in (None, "", " \n "):
                with self.subTest(field=field, blank=blank):
                    data = fixture()
                    pressure(data)["interface_actions"][0][field] = blank
                    self.invalid(data, field)

    def test_action_shapes_and_duplicate_endpoints_rejected(self):
        for value in (None, "actions", {}, [None]):
            with self.subTest(value=value):
                data = fixture()
                pressure(data)["interface_actions"] = value
                self.invalid(data, "interface_actions")
        data = fixture()
        pressure(data)["interface_actions"][0]["from"] = "IN"
        self.invalid(data, "expected object")

    def test_na_allows_omitted_or_empty_actions_but_not_nonempty(self):
        for include_empty in (False, True):
            with self.subTest(include_empty=include_empty):
                data = fixture()
                row = pressure(data)
                row.update(state="not_applicable", stream_ids=[], inputs=[])
                row.pop("interface_actions")
                if include_empty:
                    row["interface_actions"] = []
                self.valid(data)
        data = fixture()
        pressure(data).update(state="not_applicable", stream_ids=[], inputs=[])
        self.invalid(data, "not_applicable permits only []")

    def test_empty_startup_descriptions_rejected(self):
        for field in ("temporary_boundary", "forward_pass", "closure_reason"):
            with self.subTest(field=field):
                data = fixture()
                recycle(data)["startup_plan"][field] = " "
                self.invalid(data, field)

    def test_startup_shape_requires_exact_fields(self):
        for mutation in ("missing", "extra"):
            data = fixture()
            row = recycle(data)["startup_plan"]
            if mutation == "missing":
                del row["closure_reason"]
            else:
                row["executed"] = True
            self.invalid(data, "expected object")

    def test_seed_must_exist_and_leave_the_tear_source(self):
        for seed, expected in (("unknown", "unregistered stream"),
                               ("feed", "seed stream from must match"),
                               ("ab", "seed stream from must match")):
            with self.subTest(seed=seed):
                data = fixture()
                recycle(data)["startup_plan"]["seed_outlet_stream_id"] = seed
                self.invalid(data, expected)

    def test_seed_may_be_tear_itself_or_another_outlet(self):
        for seed in ("r1", "bc"):
            with self.subTest(seed=seed):
                data = fixture()
                recycle(data)["startup_plan"]["seed_outlet_stream_id"] = seed
                self.valid(data)

    def test_invalid_unknown_non_tear_duplicate_and_self_dependencies(self):
        for deps, expected in (("r1", "array required"),
                               (["unknown"], "unregistered identifiers"),
                               (["feed"], "unregistered identifiers"),
                               (["r1", "r1"], "duplicate identifiers"),
                               (["r2"], "self-dependency")):
            with self.subTest(deps=deps):
                data = fixture()
                recycle(data, 1)["startup_plan"]["depends_on_recycles"] = deps
                self.invalid(data, expected)

    def test_same_or_later_order_dependency_rejected(self):
        for dependency_order in (20, 30):
            data = fixture()
            recycle(data)["closure_order"] = dependency_order
            self.invalid(data, "strictly smaller closure_order")

    def test_independent_recycles_can_close_in_parallel(self):
        data = fixture()
        recycle(data, 1)["closure_order"] = 10
        recycle(data, 1)["startup_plan"]["depends_on_recycles"] = []
        self.valid(data)

    def test_no_recycles_requires_no_invented_startup_plan(self):
        data = fixture()
        data["streams"] = [row for row in data["streams"] if row["id"] not in ("r1", "r2")]
        pressure(data)["stream_ids"] = [row["id"] for row in data["streams"]]
        pressure(data)["interface_actions"] = [action(sid) for sid in pressure(data)["stream_ids"]]
        data["expert_plan"]["recycle_plan"] = []
        data["expert_plan"]["no_recycle_reason"] = "The synthetic declared graph is acyclic"
        result = self.valid(data)
        self.assertEqual(result["expert_plan_rows"]["recycle_plan"], [])

    def test_closure_order_is_not_required_to_be_contiguous_or_list_sorted(self):
        data = fixture()
        recycle(data, 1)["closure_order"] = 900
        data["expert_plan"]["recycle_plan"].reverse()
        self.valid(data)

    def test_branched_pressure_group_does_not_require_linear_order(self):
        data = fixture()
        pressure(data)["stream_ids"].reverse()
        pressure(data)["node_ids"].reverse()
        pressure(data)["interface_actions"] = pressure(data)["interface_actions"][2:] + pressure(data)["interface_actions"][:2]
        self.valid(data)

    def test_unknown_endpoint_stays_unresolved_without_inventing_destination(self):
        data = fixture()
        data["streams"].append({"id": "unknown_outlet", "from": "C", "to": None,
                                "state": "unresolved", "evidence": None,
                                "gap": "Synthetic destination is unknown"})
        pressure(data)["stream_ids"].append("unknown_outlet")
        pressure(data)["interface_actions"].append(action("unknown_outlet"))
        recycle(data, 1)["startup_plan"]["seed_outlet_stream_id"] = "unknown_outlet"
        result = self.valid(data)
        row = result["expert_plan_rows"]["pressure_paths"][0]["interface_actions"][-1]
        self.assertIsNone(row["to"])
        self.assertEqual(result["declared_topology"]["coverage"], "DECLARED_PARTIAL")
        self.assertTrue(any("unknown_outlet" in item for item in result["unresolved"]))

    def test_original_positive_order_and_cycle_coverage_checks_remain(self):
        data = fixture()
        recycle(data)["closure_order"] = True
        self.invalid(data, "positive integer required")
        data = fixture()
        data["expert_plan"]["recycle_plan"].pop()
        self.invalid(data, "still contains a cycle")

    def test_symbolic_unit_and_formula_text_do_not_imply_physical_verification(self):
        data = fixture()
        pressure(data)["inputs"][0]["unit"] = "UNVERIFIED_UNIT_TOKEN"
        pressure(data)["interface_actions"][0]["budget_relation"] = "UNVERIFIED_RELATION_TOKEN"
        result = self.valid(data)
        self.assertIs(result["expert_plan_rows"]["pressure_paths"][0]["calculation_verified"], False)

    def run_cli_in_memory(self, data):
        payload = json.dumps(data).encode("utf-8")
        writes = {}
        stdout = io.StringIO()

        def read_bytes(path):
            return payload if path == Path("synthetic-input.json") else b"synthetic-checker-content"

        def write_text(path, content, encoding=None):
            writes[path.name] = content
            return len(content)

        with patch.object(sys, "argv", [str(SCRIPT), "--input", "synthetic-input.json",
                                       "--output-dir", "synthetic-output", "--require-plan-actions"]), \
                patch.object(Path, "stat", return_value=SimpleNamespace(st_size=len(payload))), \
                patch.object(Path, "read_bytes", autospec=True, side_effect=read_bytes), \
                patch.object(Path, "mkdir"), \
                patch.object(Path, "write_text", autospec=True, side_effect=write_text), \
                redirect_stdout(stdout):
            exit_code = checker.main()
        return exit_code, writes, json.loads(stdout.getvalue())

    def test_cli_switch_passes_and_reports_new_flag_without_disk_writes(self):
        exit_code, writes, terminal = self.run_cli_in_memory(fixture())
        self.assertEqual(exit_code, 0)
        review = json.loads(writes["review.json"])
        for result in (review, terminal):
            for flag in ("expert_plan_checked", "named_method_declarations_checked",
                         "plan_action_declarations_checked"):
                self.assertIs(result[flag], True)
            self.assert_unverified(result)
        self.assertIn("Plan-action declarations checked: true", writes["handoff.md"])

    def test_cli_invalid_actions_return_nonzero_and_never_report_pass(self):
        data = fixture()
        pressure(data)["interface_actions"] = [None]
        exit_code, writes, terminal = self.run_cli_in_memory(data)
        self.assertEqual(exit_code, 2)
        for result in (json.loads(writes["review.json"]), terminal):
            self.assertEqual(result["status"], "STRUCTURE_INVALID")
            self.assertIs(result["plan_action_declarations_checked"], False)
            self.assertTrue(result["errors"])
            self.assert_unverified(result)
        self.assertIn("Plan-action declarations checked: false", writes["handoff.md"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
