"""Isolated name-declaration tests; synthetic fixtures are not engineering evidence."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "check_flow_handoff.py"
spec = importlib.util.spec_from_file_location("named_methods_draft", SCRIPT)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
CATALOG = {
    "schema": "aspen-property-method-name-reference-v1",
    "version": "synthetic-catalog-test-only",
    "groups": [{"source": "not-a-real-source", "names": ["SYNTHETIC_METHOD_ONE", "SYNTHETIC_METHOD_TWO"]}],
}
CATALOG_BYTES = json.dumps(CATALOG).encode("utf-8")
FIXED_CATALOG = SCRIPT.parent.parent / "assets" / "property_method_names_v14.json"


def fixture():
    return {
        "schema": checker.SCHEMA,
        "stage": "source",
        "authority_reference": "Synthetic structure fixture; no engineering assertion",
        "nodes": [{"id": "entry", "kind": "external"}, {"id": "unit", "kind": "process"},
                  {"id": "exit", "kind": "external"}],
        "streams": [{"id": "feed", "from": "entry", "to": "unit", "state": "documented",
                     "evidence": "Synthetic edge", "gap": None},
                    {"id": "product", "from": "unit", "to": "exit", "state": "documented",
                     "evidence": "Synthetic edge", "gap": None}],
        "control_volumes": [{"id": "boundary", "members": ["unit"], "inflows": ["feed"],
                             "outflows": ["product"], "balance_basis": "Synthetic symbolic basis",
                             "reaction_terms": "No chemistry asserted"}],
        "placeholders": [], "handoffs": [],
        "no_placeholders_reason": "Synthetic abstract graph has no placeholder duty",
        "expert_plan": {
            "methods": [{"node_ids": ["unit"], "method": "Legacy synthetic method text",
                         "phases": ["synthetic_phase"], "applicability": "Synthetic service declaration",
                         "source": "Synthetic source", "status": "candidate",
                         "unresolved_inputs": ["Parameter evidence not yet available"]}],
            "pressure_paths": [{"id": "identity", "node_ids": ["unit"], "stream_ids": [],
                                "state": "not_applicable", "method": "Synthetic abstract identity",
                                "equation_or_reason": "This abstract fixture asserts no pressure calculation",
                                "source": "Synthetic definition", "inputs": [],
                                "refine_trigger": "Replace this synthetic fixture before engineering use"}],
            "recycle_plan": [], "no_recycle_reason": "The declared synthetic chain is once-through",
        },
    }


def declaration(origin="aspen_v14_catalog", name="SYNTHETIC_METHOD_ONE"):
    value = {"name": name, "name_origin": origin, "source_ref": "Synthetic source locator",
             "applies_when": "Synthetic condition; applicability remains unverified"}
    if origin == "source_defined":
        value["definition_ref"] = "Synthetic definition locator"
    return value


def named_fixture(origin="aspen_v14_catalog"):
    data = fixture()
    data["expert_plan"]["methods"][0]["named_methods"] = [declaration(origin)]
    return data


class NamedMethodsTests(unittest.TestCase):
    def assert_unverified(self, result):
        for key in ("engineering_accepted", "execution_verified", "authority_verified", "source_inventory_verified"):
            self.assertIs(result[key], False, key)

    def assert_valid(self, result, named=True):
        self.assertNotEqual(result["status"], "STRUCTURE_INVALID", result)
        self.assertEqual(result["errors"], [])
        self.assertIs(result["named_method_declarations_checked"], named)
        self.assert_unverified(result)

    def assert_invalid(self, result, fragment):
        self.assertEqual(result["status"], "STRUCTURE_INVALID", result)
        self.assertFalse(result["named_method_declarations_checked"])
        self.assertIn(fragment, " ".join(result["errors"]))
        self.assert_unverified(result)

    def test_legacy_inputs_and_positional_expert_call_do_not_read_catalog(self):
        with patch.object(checker.Path, "read_bytes", side_effect=AssertionError("Unexpected catalog read")):
            data = fixture()
            self.assert_valid(checker.check(data, True), named=False)
            del data["expert_plan"]
            result = checker.check(data)
            self.assert_valid(result, named=False)
            self.assertFalse(result["expert_plan_checked"])

    def test_named_flag_implies_expert_plan(self):
        data = fixture(); del data["expert_plan"]
        self.assert_invalid(checker.check(data, require_named_methods=True), "expert_plan")

    def test_named_flag_requires_declarations_in_every_method_row(self):
        self.assert_invalid(checker.check(fixture(), require_named_methods=True), "named_methods: required")
        data = named_fixture("source_defined")
        data["expert_plan"]["methods"].append(copy.deepcopy(fixture()["expert_plan"]["methods"][0]))
        self.assert_invalid(checker.check(data, require_named_methods=True), "methods[1].named_methods")

    def test_explicit_candidate_with_unverified_parameters_passes_name_check(self):
        data = named_fixture()
        with patch.object(checker.Path, "read_bytes", autospec=True, return_value=CATALOG_BYTES) as read:
            result = checker.check(data, require_named_methods=True)
        self.assert_valid(result)
        self.assertEqual(result["status"], "STRUCTURE_VALID_WITH_UNRESOLVED")
        self.assertTrue(any("Parameter evidence" in value for value in result["unresolved"]))
        read.assert_called_once_with(FIXED_CATALOG)
        self.assertEqual(result["named_method_catalog"]["version"], CATALOG["version"])
        self.assertEqual(result["named_method_catalog"]["sha256"], hashlib.sha256(CATALOG_BYTES).hexdigest())

    def test_catalog_rejects_family_or_deferred_text_without_guessing(self):
        for name in ("EOS", "activity model", "choose later"):
            with self.subTest(name=name), patch.object(checker.Path, "read_bytes", return_value=CATALOG_BYTES):
                data = named_fixture(); data["expert_plan"]["methods"][0]["named_methods"][0]["name"] = name
                self.assert_invalid(checker.check(data, require_named_methods=True), "not in the fixed V14 name catalog")

    def test_present_optional_declarations_are_checked_without_new_flag(self):
        with patch.object(checker.Path, "read_bytes", return_value=CATALOG_BYTES):
            self.assert_valid(checker.check(named_fixture()))
            data = named_fixture(); data["expert_plan"]["methods"][0]["named_methods"][0]["name"] = "UNKNOWN_TOKEN"
            self.assert_invalid(checker.check(data), "not in the fixed V14 name catalog")

    def test_n_a_accepts_empty_or_legacy_absence_but_not_named_candidate(self):
        data = fixture(); row = data["expert_plan"]["methods"][0]
        row.update(status="not_applicable", phases=[], not_applicable_reason="Synthetic logic-only service")
        with patch.object(checker.Path, "read_bytes", side_effect=AssertionError("N/A must not need catalog")):
            self.assert_valid(checker.check(data), named=False)
            self.assert_invalid(checker.check(data, require_named_methods=True), "named_methods: required")
            row["named_methods"] = []
            self.assert_valid(checker.check(data, require_named_methods=True))
            row["named_methods"] = [declaration()]
            self.assert_invalid(checker.check(data), "not_applicable permits only []")

    def test_n_a_still_requires_original_absence_reason(self):
        data = fixture(); row = data["expert_plan"]["methods"][0]
        row.update(status="not_applicable", phases=[], named_methods=[])
        self.assert_invalid(checker.check(data, require_named_methods=True), "not_applicable_reason")

    def test_non_n_a_requires_nonempty_candidates_in_strict_mode(self):
        data = fixture(); data["expert_plan"]["methods"][0]["named_methods"] = []
        self.assert_invalid(checker.check(data, require_named_methods=True), "nonempty array")
        self.assert_valid(checker.check(data))
        for value in (None, {}, "METHOD"):
            with self.subTest(value=value):
                data["expert_plan"]["methods"][0]["named_methods"] = value
                self.assert_invalid(checker.check(data), "array required")

    def test_source_defined_accepts_catalog_unknown_names_without_catalog_io(self):
        data = named_fixture("source_defined")
        data["expert_plan"]["methods"][0]["named_methods"][0]["name"] = "Defined model outside this catalog"
        with patch.object(checker.Path, "read_bytes", side_effect=FileNotFoundError("No catalog")) as read:
            result = checker.check(data, require_named_methods=True)
        self.assert_valid(result)
        read.assert_not_called()
        self.assertNotIn("named_method_catalog", result)

    def test_source_defined_requires_nonempty_definition_reference(self):
        for missing in (True, False):
            with self.subTest(missing=missing):
                data = named_fixture("source_defined"); item = data["expert_plan"]["methods"][0]["named_methods"][0]
                if missing:
                    del item["definition_ref"]
                else:
                    item["definition_ref"] = " "
                self.assert_invalid(checker.check(data, require_named_methods=True), "definition_ref")

    def test_catalog_definition_reference_and_unrecognized_fields_rejected(self):
        for field in ("definition_ref", "catalog_path", "verified"):
            with self.subTest(field=field):
                data = named_fixture(); data["expert_plan"]["methods"][0]["named_methods"][0][field] = "caller value"
                self.assert_invalid(checker.check(data, require_named_methods=True), "definition_ref" if field == "definition_ref" else "expected object")

    def test_required_declaration_fields_and_origin_are_checked(self):
        for field in ("name", "name_origin", "source_ref", "applies_when"):
            with self.subTest(field=field):
                data = named_fixture("source_defined"); del data["expert_plan"]["methods"][0]["named_methods"][0][field]
                self.assert_invalid(checker.check(data, require_named_methods=True), "expected object")
        for field in ("source_ref", "applies_when"):
            data = named_fixture("source_defined"); data["expert_plan"]["methods"][0]["named_methods"][0][field] = " "
            self.assert_invalid(checker.check(data), field)
        data = named_fixture("source_defined"); data["expert_plan"]["methods"][0]["named_methods"][0]["name_origin"] = "user_claim"
        self.assert_invalid(checker.check(data), "name_origin")

    def test_name_is_nonempty_single_line_maximum_eighty_characters(self):
        for value in ("", " ", "x" * 81, "model\n", "model\rname", "model\u2028name", "model\vname", None, 8):
            with self.subTest(value=value):
                data = named_fixture("source_defined"); data["expert_plan"]["methods"][0]["named_methods"][0]["name"] = value
                self.assert_invalid(checker.check(data), ".name")
        data = named_fixture("source_defined"); data["expert_plan"]["methods"][0]["named_methods"][0]["name"] = "x" * 80
        self.assert_valid(checker.check(data))

    def test_all_source_references_are_inert(self):
        data = named_fixture("source_defined"); item = data["expert_plan"]["methods"][0]["named_methods"][0]
        item["source_ref"] = "https://invalid.example/never-fetch"
        item["definition_ref"] = "__import__('pathlib').Path('never-create').write_text('not executed')"
        with patch.object(checker.Path, "read_bytes", side_effect=AssertionError("Do not read a source")), \
             patch.object(checker.Path, "read_text", side_effect=AssertionError("Do not read a source")), \
             patch.object(checker.Path, "write_text", side_effect=AssertionError("Do not execute a source")):
            result = checker.check(data, require_named_methods=True)
        self.assert_valid(result)
        self.assertIn("not opened or executed", result["scope"])
        self.assertEqual(result["expert_plan_rows"]["methods"][0]["named_methods"][0]["definition_ref"], item["definition_ref"])

    def test_catalog_reads_fixed_path_once_and_never_group_source(self):
        data = named_fixture(); row = data["expert_plan"]["methods"][0]
        row["named_methods"].append(declaration(name="SYNTHETIC_METHOD_TWO"))
        data["expert_plan"]["methods"].append(copy.deepcopy(row))
        with patch.object(checker.Path, "read_bytes", autospec=True, return_value=CATALOG_BYTES) as read:
            result = checker.check(data, require_named_methods=True)
        self.assert_valid(result)
        read.assert_called_once_with(FIXED_CATALOG)

    def test_catalog_missing_and_unreadable_are_local_diagnostics(self):
        for error in (FileNotFoundError("synthetic missing file"), PermissionError("synthetic access denied")):
            with self.subTest(error=str(error)), patch.object(checker.Path, "read_bytes", side_effect=error):
                result = checker.check(named_fixture(), require_named_methods=True)
                self.assert_invalid(result, "named-method catalog unavailable or invalid")
                self.assertIn("methods[0].named_methods[0]", result["errors"][0])
                self.assertTrue(result["expert_plan_rows"]["pressure_paths"])
                self.assertTrue(result["expert_plan_rows"]["cycle_coverage"])

    def test_catalog_corruption_is_reported_not_raised(self):
        broken = [b"not json", b"\xff", b"[]", b"{}", b'{"version":"one","version":"two"}',
                  json.dumps({**CATALOG, "version": " "}).encode(),
                  json.dumps({**CATALOG, "groups": []}).encode(),
                  json.dumps({**CATALOG, "groups": [{"names": ["bad\nname"]}]}).encode(),
                  json.dumps({**CATALOG, "groups": [{"names": []}]}).encode(),
                  json.dumps({**CATALOG, "groups": [{"names": ["same", "same"]}]}).encode()]
        for value in broken:
            with self.subTest(value=value), patch.object(checker.Path, "read_bytes", return_value=value):
                self.assert_invalid(checker.check(named_fixture(), require_named_methods=True), "catalog unavailable or invalid")

    def test_provided_catalog_loads_with_its_actual_identity(self):
        registered, metadata = checker._load_method_catalog()
        self.assertTrue(registered)
        self.assertEqual(metadata["path"], str(FIXED_CATALOG))
        raw = FIXED_CATALOG.read_bytes()
        provided = json.loads(raw.decode("utf-8-sig"))
        self.assertEqual(metadata["version"], provided["version"])
        self.assertEqual(metadata["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(registered, {name for group in provided["groups"] for name in group["names"]})

    def test_markdown_shows_declarations_and_nonengineering_boundary(self):
        with patch.object(checker.Path, "read_bytes", return_value=CATALOG_BYTES):
            result = checker.check(named_fixture(), require_named_methods=True)
        report = checker.markdown(result)
        for token in ("Named-method declarations checked: true", "SYNTHETIC_METHOD_ONE", CATALOG["version"],
                      "does not verify", "Engineering accepted: false", "Source references are inert"):
            self.assertIn(token, report)

    def test_cli_flag_implies_expert_plan_and_reports_check_boundary(self):
        with tempfile.TemporaryDirectory(prefix="named_method_test_") as temporary:
            root = Path(temporary)
            for present in (False, True):
                data = named_fixture("source_defined")
                if not present:
                    del data["expert_plan"]
                source = root / ("input_present.json" if present else "input_absent.json")
                source.write_text(json.dumps(data), encoding="utf-8")
                output = root / ("present" if present else "absent")
                run = subprocess.run([sys.executable, "-B", "-X", "utf8", str(SCRIPT), "--input", str(source),
                                      "--output-dir", str(output), "--require-named-methods"],
                                     capture_output=True, text=True, encoding="utf-8", timeout=30)
                self.assertEqual(run.returncode, 0 if present else 2, run.stdout + run.stderr)
                result = json.loads(run.stdout)
                self.assertEqual(result["named_method_declarations_checked"], present)
                self.assertEqual(result["expert_plan_checked"], present)
                self.assertIn("Named-method declaration checking", result["scope"])
                self.assert_unverified(result)


if __name__ == "__main__":
    unittest.main()
