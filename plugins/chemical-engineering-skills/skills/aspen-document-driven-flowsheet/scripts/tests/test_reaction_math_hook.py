"""Isolated hook tests; only synthetic water/acid-base chemistry is used.

Run with Python -B. The fixed helper-file boundary uses the sibling owner's
real bytes, with a layout-checked fallback for the isolated draft. Evaluate and
its arithmetic are never mocked in integration cases. CLI writes are captured.
"""
import copy
import hashlib
import importlib.util
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "check_flow_handoff.py"
FIXED_HELPER = (SCRIPT.resolve().parents[2] / "chemical-engineering-expert"
                / "scripts" / "check_reaction_derivations.py")
DRAFT_HELPER = SCRIPT.parent.parent / "chemical-expert-scripts" / "check_reaction_derivations.py"
HELPER = FIXED_HELPER
if not FIXED_HELPER.is_file() and SCRIPT.parent.name == "docflow-scripts" and DRAFT_HELPER.is_file():
    HELPER = DRAFT_HELPER
spec = importlib.util.spec_from_file_location("reaction_math_hook_draft", SCRIPT)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
HELPER_BYTES = HELPER.read_bytes()


def fixture():
    edges = [("feed", "IN", "UNIT"), ("product", "UNIT", "OUT")]
    return {
        "schema": checker.SCHEMA, "stage": "source",
        "authority_reference": "Synthetic structural fixture, not project authority",
        "nodes": [{"id": x, "kind": "process" if x == "UNIT" else "external"}
                  for x in ("IN", "UNIT", "OUT")],
        "streams": [{"id": sid, "from": a, "to": b, "state": "documented",
                     "evidence": "Synthetic edge", "gap": None} for sid, a, b in edges],
        "control_volumes": [{"id": "boundary", "members": ["UNIT"],
                             "inflows": ["feed"], "outflows": ["product"],
                             "balance_basis": "Synthetic boundary",
                             "reaction_terms": "Separate synthetic arithmetic declaration"}],
        "placeholders": [], "no_placeholders_reason": "Synthetic fixture has no placeholders",
        "handoffs": [],
        "expert_plan": {
            "methods": [{"node_ids": ["UNIT"], "method": "Synthetic source-defined model",
                         "phases": ["synthetic_phase"], "applicability": "Test only",
                         "source": "Synthetic source", "status": "candidate", "unresolved_inputs": [],
                         "named_methods": [{"name": "SYNTHETIC_MODEL", "name_origin": "source_defined",
                                            "source_ref": "Synthetic source", "applies_when": "Test only",
                                            "definition_ref": "Synthetic definition"}]}],
            "pressure_paths": [{"id": "path", "node_ids": ["UNIT"],
                                "stream_ids": ["feed", "product"], "state": "symbolic",
                                "method": "Synthetic pressure declaration", "equation_or_reason": "Symbolic",
                                "source": "Synthetic source", "refine_trigger": "Obtain real evidence",
                                "inputs": [{"name": "loss", "unit": "test_unit", "gap": "Synthetic gap"}],
                                "interface_actions": [{"stream_id": sid, "receiver_requirement": "Synthetic",
                                                       "budget_relation": "Symbolic", "equipment_action": "Pending",
                                                       "condition_or_basis": "Synthetic only"} for sid, _, _ in edges]}],
            "recycle_plan": [], "no_recycle_reason": "Synthetic feed-forward graph has no recycle",
        },
    }


def water():
    return {"reactions": [{"id": "water", "scope": "Synthetic equation, not engineering feasibility",
                           "basis_ref": "Synthetic molecular basis",
                           "species": [{"id": sid, "formula": formula, "coefficient": coefficient,
                                        "charge": 0, "basis_ref": "Synthetic molecular declaration"}
                                       for sid, formula, coefficient in
                                       (("hydrogen", "H2", -2), ("oxygen", "O2", -1), ("water", "H2O", 2))]}]}


def no_reaction():
    return {"reactions": [], "none_reason": "Synthetic scope includes no reaction-derived quantity"}


class ReactionMathHookTests(unittest.TestCase):
    def run_check(self, data, *, helper_bytes=HELPER_BYTES, strict=False):
        observed = []

        def read_bytes(path):
            observed.append(path)
            if path != FIXED_HELPER:
                raise AssertionError(f"Unexpected file read: {path}")
            if helper_bytes is None:
                raise FileNotFoundError("Synthetic missing sibling helper")
            return helper_bytes

        before = copy.deepcopy(data)
        with patch.object(Path, "read_bytes", read_bytes):
            result = checker.check(data, require_reaction_math=strict)
        self.assertEqual(data, before, "The ledger must remain unchanged")
        for flag in ("engineering_accepted", "execution_verified", "authority_verified",
                     "source_inventory_verified"):
            self.assertIs(result[flag], False)
        return result, observed

    def with_payload(self, payload):
        data = fixture()
        data["expert_plan"]["reaction_derivations"] = payload
        return data

    def test_real_helper_balanced_water_and_hash_bound_receipt(self):
        result, reads = self.run_check(self.with_payload(water()), strict=True)
        self.assertEqual(result["errors"], [])
        self.assertTrue(result["reaction_derivations_checked"])
        self.assertEqual(reads, [FIXED_HELPER])
        receipt = result["reaction_math"]
        self.assertEqual(receipt["helper"], {"path": str(FIXED_HELPER),
                                            "sha256": hashlib.sha256(HELPER_BYTES).hexdigest()})
        self.assertEqual(receipt["result"]["status"], "checked")
        self.assertTrue(receipt["result"]["applicable"])
        self.assertTrue(receipt["result"]["math_checked"])
        self.assertTrue(receipt["result"]["math_valid"])
        self.assertEqual(receipt["result"]["reactions"][0]["element_residuals"], {"H": "0", "O": "0"})
        self.assertIn("whole-process yield bounds", result["scope"])
        self.assertIn(hashlib.sha256(HELPER_BYTES).hexdigest(), checker.markdown(result))

    def test_real_helper_unbalanced_water_rejected_even_without_flag(self):
        payload = water()
        payload["reactions"][0]["species"][2]["coefficient"] = 1
        result, _ = self.run_check(self.with_payload(payload))
        self.assertEqual(result["status"], "STRUCTURE_INVALID")
        self.assertTrue(result["reaction_derivations_checked"])
        outcome = result["reaction_math"]["result"]
        self.assertTrue(outcome["math_checked"])
        self.assertFalse(outcome["math_valid"])
        self.assertEqual(outcome["reactions"][0]["element_residuals"], {"H": "-2", "O": "-1"})
        self.assertTrue(result["errors"])

    def test_real_acid_base_charge_balance_and_charge_mismatch(self):
        payload = water()
        payload["reactions"][0]["species"] = [
            {"id": sid, "formula": formula, "coefficient": coefficient,
             "charge": charge, "basis_ref": "Synthetic ionic basis"}
            for sid, formula, coefficient, charge in (("acid", "H", -1, 1),
                                                      ("base", "OH", -1, -1), ("water", "H2O", 1, 0))]
        result, _ = self.run_check(self.with_payload(payload))
        self.assertEqual(result["errors"], [])
        payload["reactions"][0]["species"][1]["charge"] = 0
        result, _ = self.run_check(self.with_payload(payload))
        self.assertEqual(result["status"], "STRUCTURE_INVALID")
        self.assertEqual(result["reaction_math"]["result"]["reactions"][0]["charge_residual"], "-1")

    def test_real_explicit_empty_is_checked_not_applicable_and_not_math_pass(self):
        result, _ = self.run_check(self.with_payload(no_reaction()), strict=True)
        self.assertEqual(result["errors"], [])
        self.assertTrue(result["reaction_derivations_checked"])
        outcome = result["reaction_math"]["result"]
        self.assertEqual(outcome["status"], "not_applicable")
        for flag in ("applicable", "math_checked", "math_valid"):
            self.assertIs(outcome[flag], False)
        self.assertIn("not_applicable", checker.markdown(result))

    def test_real_optional_mass_projection_is_preserved_and_unit_error_rejected(self):
        payload = water()
        payload["reactions"][0]["mass_projection"] = {
            "reactant_id": "hydrogen", "product_id": "water",
            "feed_mass": {"value": 4, "unit": "kg/h", "basis_ref": "Synthetic mass input"},
            "molar_masses": [{"species_id": sid, "value": value, "unit": "kg/kmol",
                              "basis_ref": "Synthetic arithmetic values; not verified molar masses"}
                             for sid, value in (("hydrogen", 2), ("water", 18))],
        }
        result, _ = self.run_check(self.with_payload(payload))
        self.assertEqual(result["errors"], [])
        projection = result["reaction_math"]["result"]["reactions"][0]["mass_projection"]
        self.assertEqual(projection["product_mass"], {"value": "36", "unit": "kg/h"})
        self.assertFalse(projection["molar_masses_verified"])
        self.assertFalse(projection["basis_alignment_verified"])
        self.assertTrue(projection["assumptions"])
        payload["reactions"][0]["mass_projection"]["feed_mass"]["unit"] = "mol/h"
        result, _ = self.run_check(self.with_payload(payload))
        self.assertEqual(result["status"], "STRUCTURE_INVALID")
        self.assertFalse(result["reaction_math"]["result"]["math_valid"])

    def test_real_empty_without_reason_and_malformed_payload_fail(self):
        for payload in ({"reactions": []}, {"reactions": [], "none_reason": " "}, None, [],
                        {"reactions": [], "none_reason": "Reason", "helper_path": "not-trusted.py"}):
            with self.subTest(payload=payload):
                result, reads = self.run_check(self.with_payload(payload))
                self.assertEqual(result["status"], "STRUCTURE_INVALID")
                self.assertEqual(reads, [FIXED_HELPER])
                self.assertFalse(result["reaction_math"]["result"]["math_valid"])

    def test_missing_helper_is_fail_closed(self):
        result, _ = self.run_check(self.with_payload(water()), helper_bytes=None)
        self.assertEqual(result["status"], "STRUCTURE_INVALID")
        self.assertFalse(result["reaction_derivations_checked"])
        self.assertIsNone(result["reaction_math"]["helper"]["sha256"])
        self.assertIn("FileNotFoundError", " ".join(result["errors"]))

    def test_required_payload_missing_is_not_silent_not_applicable(self):
        result, reads = self.run_check(fixture(), strict=True)
        self.assertEqual(result["status"], "STRUCTURE_INVALID")
        self.assertEqual(reads, [])
        self.assertFalse(result["reaction_derivations_checked"])
        self.assertIn("required by --require-reaction-math", " ".join(result["errors"]))

    def test_strict_flag_implies_each_previous_requirement(self):
        for missing in ("expert_plan", "named_methods", "interface_actions"):
            with self.subTest(missing=missing):
                data = self.with_payload(no_reaction())
                if missing == "expert_plan":
                    del data["expert_plan"]
                elif missing == "named_methods":
                    del data["expert_plan"]["methods"][0][missing]
                else:
                    del data["expert_plan"]["pressure_paths"][0][missing]
                result, _ = self.run_check(data, strict=True)
                self.assertEqual(result["status"], "STRUCTURE_INVALID")
                self.assertIn(missing, " ".join(result["errors"]))

    def test_declared_math_executes_even_if_other_structure_is_invalid(self):
        data = self.with_payload(water())
        data["nodes"] = []
        result, reads = self.run_check(data)
        self.assertEqual(result["status"], "STRUCTURE_INVALID")
        self.assertEqual(reads, [FIXED_HELPER])
        self.assertTrue(result["reaction_derivations_checked"])
        self.assertTrue(result["reaction_math"]["result"]["math_valid"])

    def test_source_references_are_inert_not_import_paths(self):
        payload = water()
        payload["reactions"][0]["basis_ref"] = "../../not-a-module.py $(not-a-command) https://invalid.example/"
        result, reads = self.run_check(self.with_payload(payload))
        self.assertEqual(result["errors"], [])
        self.assertEqual(reads, [FIXED_HELPER])

    def test_illegal_helper_return_or_failure_never_claims_checked(self):
        good = {"schema": "reaction-derivations-check-v1", "status": "checked", "errors": [],
                "applicable": True, "math_checked": True, "math_valid": True,
                "source_verified": False, "engineering_accepted": False, "reaction_feasible": False}
        bad_returns = [None, [], {}, {**good, "schema": "wrong"}, {**good, "errors": "bad"},
                       {**good, "errors": [None]}, {**good, "math_checked": 1},
                       {**good, "applicable": 1}, {**good, "math_valid": False},
                       {**good, "engineering_accepted": True}, {**good, "status": "unknown"},
                       {**good, "status": "invalid"},
                       {**good, "status": "not_applicable", "applicable": False,
                        "math_checked": False, "math_valid": False}]
        programs = [f"def evaluate(payload):\n    return {value!r}\n".encode() for value in bad_returns]
        programs += [b"def evaluate(payload):\n    raise RuntimeError('Synthetic failure')\n",
                     b"def evaluate(payload):\n    raise SystemExit(7)\n", b"# No evaluate\n",
                     b"invalid python here\n",
                     ("def evaluate(payload):\n    return " + repr(good)[:-1]
                      + ", 'unsafe': float('nan')}\n").encode()]
        for program in programs:
            with self.subTest(program=program):
                result, _ = self.run_check(self.with_payload(water()), helper_bytes=program)
                self.assertEqual(result["status"], "STRUCTURE_INVALID")
                self.assertFalse(result["reaction_derivations_checked"])
                self.assertIsNone(result["reaction_math"]["result"])
                self.assertEqual(result["reaction_math"]["helper"]["sha256"], hashlib.sha256(program).hexdigest())

    def test_old_check_api_and_three_strict_flags_do_not_require_new_payload(self):
        for flags in ((), (True,), (True, True), (True, True, True)):
            with self.subTest(flags=flags):
                data = fixture()
                if not flags:
                    del data["expert_plan"]
                with patch.object(Path, "read_bytes", side_effect=AssertionError("No helper needed")):
                    result = checker.check(data, *flags)
                self.assertEqual(result["errors"], [])
                self.assertFalse(result["reaction_derivations_checked"])
                self.assertNotIn("reaction_math", result)
        data = fixture()
        del data["expert_plan"]["methods"][0]["named_methods"]
        del data["expert_plan"]["pressure_paths"][0]["interface_actions"]
        self.assertEqual(checker.check(data, True)["errors"], [])

    def run_cli(self, data, flags):
        source, output = Path("synthetic-input.json"), Path("synthetic-output")
        writes, stdout = {}, io.StringIO()
        raw = json.dumps(data).encode("utf-8")
        script_bytes = SCRIPT.read_bytes()

        def read_bytes(path):
            if path == source:
                return raw
            if path == FIXED_HELPER:
                return HELPER_BYTES
            if path == SCRIPT:
                return script_bytes
            raise AssertionError(f"Unexpected CLI read: {path}")

        def write_text(path, content, encoding=None):
            writes[str(path)] = content
            return len(content)

        # resolve() uses stat() on some Python versions; preserve actual stats except input.
        real_stat = Path.stat

        def stat(path, *args, **kwargs):
            return SimpleNamespace(st_size=len(raw)) if path == source else real_stat(path, *args, **kwargs)

        with patch.object(sys, "argv", [str(SCRIPT), "--input", str(source), "--output-dir", str(output), *flags]), \
                patch.object(Path, "read_bytes", read_bytes), patch.object(Path, "write_text", write_text), \
                patch.object(Path, "stat", stat), patch.object(Path, "mkdir"), redirect_stdout(stdout):
            code = checker.main()
        return code, json.loads(stdout.getvalue()), json.loads(writes[str(output / "review.json")]), writes

    def test_cli_real_hook_reports_results_and_nonzero_for_unbalanced(self):
        for balanced in (True, False):
            with self.subTest(balanced=balanced):
                payload = water()
                if not balanced:
                    payload["reactions"][0]["species"][2]["coefficient"] = 1
                code, terminal, report, writes = self.run_cli(self.with_payload(payload), ["--require-reaction-math"])
                self.assertEqual(code, 0 if balanced else 2)
                self.assertEqual(terminal["reaction_math"], report["reaction_math"])
                self.assertEqual(report["reaction_math"]["result"]["math_valid"], balanced)
                self.assertFalse(report["engineering_accepted"])
                self.assertEqual(report["checker_sha256"], hashlib.sha256(SCRIPT.read_bytes()).hexdigest())
                self.assertIn("Reaction arithmetic", writes[str(Path("synthetic-output") / "handoff.md")])

    def test_cli_empty_and_legacy_modes(self):
        code, _, report, _ = self.run_cli(self.with_payload(no_reaction()), ["--require-reaction-math"])
        self.assertEqual(code, 0)
        self.assertEqual(report["reaction_math"]["result"]["status"], "not_applicable")
        for flag in ([], ["--require-expert-plan"], ["--require-named-methods"], ["--require-plan-actions"]):
            with self.subTest(flag=flag):
                code, _, report, _ = self.run_cli(fixture(), flag)
                self.assertEqual(code, 0)
                self.assertFalse(report["reaction_derivations_checked"])


if __name__ == "__main__":
    unittest.main()
