"""Synthetic standard-library tests; no Aspen, network, or test-case sources."""

import copy
import io
import json
import math
import sys
import unittest
from contextlib import redirect_stdout
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if not (SCRIPT_DIRECTORY / "check_reaction_derivations.py").is_file():
    SCRIPT_DIRECTORY = SCRIPT_DIRECTORY.parent
sys.path.insert(0, str(SCRIPT_DIRECTORY))

from check_reaction_derivations import ELEMENTS, DeclarationError, evaluate, main, parse_formula


def species(sid, formula, coefficient, charge=0):
    return {"id": sid, "formula": formula, "coefficient": coefficient,
            "charge": charge, "basis_ref": "synthetic formula declaration"}


def water(fractional=False):
    return {"id": "water", "scope": "synthetic selected feed contribution only",
            "basis_ref": "synthetic algebra test, not process evidence",
            "species": [species("hydrogen", "H2", -1 if fractional else -2),
                        species("oxygen", "O2", "-1/2" if fractional else -1),
                        species("water", "H2O", 1 if fractional else 2)]}


def projection(feed_value=2, feed_unit="kg/h"):
    return {"reactant_id": "hydrogen", "product_id": "water",
            "feed_mass": {"value": feed_value, "unit": feed_unit,
                          "basis_ref": "synthetic pure selected reactant"},
            "molar_masses": [
                {"species_id": "hydrogen", "value": 2, "unit": "kg/kmol", "basis_ref": "synthetic rounded mass"},
                {"species_id": "water", "value": 18, "unit": "g/mol", "basis_ref": "synthetic rounded mass"}]}


class FormulaTests(unittest.TestCase):
    def test_all_118_symbols_are_recognized(self):
        self.assertEqual(len(ELEMENTS), 118)
        for element in ELEMENTS:
            self.assertEqual(parse_formula(element), {element: 1})

    def test_simple_parentheses_and_square_groups(self):
        for formula, expected in {
            "H2O": {"H": 2, "O": 1},
            "Ca(OH)2": {"Ca": 1, "O": 2, "H": 2},
            "Al2(SO4)3": {"Al": 2, "S": 3, "O": 12},
            "K4[Fe(CN)6]": {"K": 4, "Fe": 1, "C": 6, "N": 6},
            "[Na]Cl": {"Na": 1, "Cl": 1},
        }.items():
            with self.subTest(formula=formula):
                self.assertEqual(parse_formula(formula), expected)

    def test_reject_unsupported_and_malformed_formulas(self):
        bad = ["", None, True, 123, "Xx2", "D2O", "13C", "[13C]", "C-13",
               "CuSO4·5H2O", "CuSO4.5H2O", "(CH2)n", "H0", "H01", "2H2O",
               "H2 O", " H2O", "H2O\n", "NH4+", "Fe^3+", "H₂O", "H１２",
               "()", "[]", "(H2O", "H2O)", "[OH)", "{OH}", "H1000001",
               "(" * 33 + "H" + ")" * 33, "H" * 513, "__import__('os')"]
        for formula in bad:
            with self.subTest(formula=formula):
                self.assertRaises(DeclarationError, parse_formula, formula)


class ReactionTests(unittest.TestCase):
    def assert_invalid(self, payload):
        result = evaluate(payload)
        self.assertFalse(result["math_valid"])
        self.assertTrue(result["errors"])
        json.dumps(result, allow_nan=False)
        return result

    def test_balanced_water_and_exact_fraction(self):
        for fractional in (False, True):
            result = evaluate({"reactions": [water(fractional)]})
            self.assertTrue(result["math_checked"])
            self.assertTrue(result["math_valid"])
            self.assertEqual(result["errors"], [])
            self.assertEqual(result["reactions"][0]["element_residuals"], {"H": "0", "O": "0"})
            self.assertEqual(result["reactions"][0]["charge_residual"], "0")

    def test_parenthesized_neutralization(self):
        rxn = water()
        rxn["species"] = [species("base", "Ca(OH)2", -1), species("acid", "HCl", -2),
                          species("salt", "CaCl2", 1), species("water", "H2O", 2)]
        self.assertTrue(evaluate({"reactions": [rxn]})["math_valid"])

    def test_ions_and_charge_failure_independent_of_elements(self):
        rxn = water()
        rxn["species"] = [species("acid", "H", -1, 1), species("base", "OH", -1, -1),
                          species("water", "H2O", 1)]
        self.assertTrue(evaluate({"reactions": [rxn]})["math_valid"])
        rxn["species"][1]["charge"] = 0
        result = self.assert_invalid({"reactions": [rxn]})
        self.assertTrue(result["math_checked"])
        self.assertEqual(result["reactions"][0]["element_residuals"], {"H": "0", "O": "0"})
        self.assertEqual(result["reactions"][0]["charge_residual"], "-1")

    def test_unbalanced_exact_residual_and_no_projection(self):
        rxn = water(True)
        rxn["species"][1]["coefficient"] = "-1/3"
        rxn["mass_projection"] = projection()
        result = self.assert_invalid({"reactions": [rxn]})
        checked = result["reactions"][0]
        self.assertTrue(checked["math_checked"])
        self.assertEqual(checked["element_residuals"]["O"], "1/3")
        self.assertFalse(checked["mass_projection"]["math_checked"])
        self.assertNotIn("product_mass", checked["mass_projection"])

    def test_json_number_forms_and_exact_strings(self):
        for coefficient in (-0.5, "-0.5", "-5e-1", "-1/2", "1/-2"):
            with self.subTest(coefficient=coefficient):
                rxn = water(True)
                rxn["species"][1]["coefficient"] = coefficient
                self.assertTrue(evaluate({"reactions": [rxn]})["math_valid"])

    def test_invalid_coefficients(self):
        bad = [0, -0.0, "0/2", "-0", math.nan, math.inf, -math.inf,
               True, False, None, [], {}, Fraction(1, 2), "1/0", "nan", "Infinity",
               "1 / 2", "-1/2x", "0.5;print(1)", "1e1001", "1e9999999999999",
               "1" * 129, 1 << 4096]
        for coefficient in bad:
            with self.subTest(coefficient=str(coefficient)[:40]):
                rxn = water()
                rxn["species"][0]["coefficient"] = coefficient
                self.assert_invalid({"reactions": [rxn]})

    def test_extreme_but_supported_fraction_is_exact(self):
        rxn = water(True)
        rxn["species"][0]["coefficient"] = "-1e300"
        rxn["species"][1]["coefficient"] = "-5e299"
        rxn["species"][2]["coefficient"] = "1e300"
        result = evaluate({"reactions": [rxn]})
        self.assertTrue(result["math_valid"])
        json.dumps(result, allow_nan=False)

    def test_bounded_arithmetic_does_not_raise_on_huge_derived_values(self):
        rxn = water()
        rxn["species"][0]["coefficient"] = -(1 << 4095)
        self.assert_invalid({"reactions": [rxn]})
        rxn = water()
        rxn["species"][0]["coefficient"] = "-1e1000"
        rxn["species"][0]["charge"] = 1 << 4095
        self.assert_invalid({"reactions": [rxn]})

    def test_integer_charge_only_and_invalid_types(self):
        for charge in (True, 1.0, "0", None, math.nan, 1 << 4096):
            rxn = water()
            rxn["species"][0]["charge"] = charge
            self.assert_invalid({"reactions": [rxn]})
        for payload in (None, [], "", True, {"reactions": None}, {"reactions": {}},
                        {"reactions": [None]}, {"reactions": [water()], "extra": 1},
                        {"reactions": [], 1: "bad key"}):
            self.assert_invalid(payload)

    def test_required_fields_and_text(self):
        for field in ("id", "scope", "basis_ref", "species"):
            rxn = water()
            del rxn[field]
            self.assert_invalid({"reactions": [rxn]})
        for field in ("id", "formula", "coefficient", "charge", "basis_ref"):
            rxn = water()
            del rxn["species"][0][field]
            self.assert_invalid({"reactions": [rxn]})
        for field in ("id", "scope", "basis_ref"):
            rxn = water()
            rxn[field] = "  "
            self.assert_invalid({"reactions": [rxn]})
        rxn = water()
        rxn["species"][0]["formula"] = "H2O·H2O"
        result = self.assert_invalid({"reactions": [rxn]})
        self.assertFalse(result["math_checked"])

    def test_duplicate_ids_and_one_sided_declarations(self):
        self.assert_invalid({"reactions": [water(), water()]})
        rxn = water()
        rxn["species"][1]["id"] = rxn["species"][0]["id"]
        self.assert_invalid({"reactions": [rxn]})
        for sign in (1, -1):
            rxn = water()
            for row in rxn["species"]:
                row["coefficient"] = sign
            self.assert_invalid({"reactions": [rxn]})

    def test_collection_limits_and_missing_species(self):
        self.assert_invalid({"reactions": [water()] * 257})
        for rows in ([], [species("water", "H2O", 1)], [species("water", "H2O", 1)] * 257, {}):
            rxn = water()
            rxn["species"] = rows
            self.assert_invalid({"reactions": [rxn]})

    def test_no_reactions_is_explicit_not_mathematical_pass(self):
        result = evaluate({"reactions": [], "none_reason": "No molecular reaction used in this synthetic calculation."})
        self.assertEqual(result["status"], "not_applicable")
        self.assertFalse(result["applicable"])
        self.assertFalse(result["math_checked"])
        self.assertFalse(result["math_valid"])
        self.assertFalse(result["errors"])
        for payload in ({"reactions": []}, {"reactions": [], "none_reason": " "},
                        {"reactions": [], "none_reason": True},
                        {"reactions": [water()], "none_reason": ""},
                        {"reactions": [water()], "none_reason": None}):
            self.assert_invalid(payload)

    def test_no_input_mutation_and_engineering_flags_always_false(self):
        rxn = water()
        rxn["mass_projection"] = projection()
        payload = {"reactions": [rxn]}
        before = copy.deepcopy(payload)
        result = evaluate(payload)
        self.assertEqual(payload, before)
        for record in (result, result["reactions"][0], result["reactions"][0]["mass_projection"]):
            for key in ("source_verified", "engineering_accepted", "reaction_feasible"):
                self.assertIs(record[key], False)
        json.dumps(result, allow_nan=False)


class ProjectionTests(unittest.TestCase):
    def checked(self, raw=None):
        rxn = water()
        rxn["mass_projection"] = projection() if raw is None else raw
        return evaluate({"reactions": [rxn]})

    def test_mass_ratio_and_equal_molar_mass_units(self):
        result = self.checked()
        item = result["reactions"][0]["mass_projection"]
        self.assertTrue(result["math_valid"])
        self.assertEqual(item["coefficient_ratio"], "1")
        self.assertEqual(item["mass_ratio"], "9")
        self.assertEqual(item["product_mass"], {"value": "18", "unit": "kg/h"})
        self.assertFalse(item["molar_masses_verified"])
        self.assertFalse(item["basis_alignment_verified"])
        self.assertIn("co-reactants", " ".join(item["assumptions"]))
        self.assertIn("not actual yield", " ".join(item["assumptions"]))
        for units in (("g/mol", "g/mol"), ("kg/kmol", "kg/kmol"), ("g/mol", "kg/kmol")):
            raw = projection()
            for row, unit in zip(raw["molar_masses"], units):
                row["unit"] = unit
            self.assertEqual(self.checked(raw)["reactions"][0]["mass_projection"]["mass_ratio"], "9")

    def test_fixed_mass_and_flow_units_preserve_time_basis(self):
        for unit in ("mg", "g", "kg", "t", "g/s", "kg/min", "kg/h", "t/d", "kg/day"):
            item = self.checked(projection("1/3", unit))["reactions"][0]["mass_projection"]
            self.assertEqual(item["product_mass"], {"value": "3", "unit": unit})

    def test_nonunit_coefficient_ratio(self):
        rxn = water()
        raw = projection()
        raw["reactant_id"] = "oxygen"
        raw["feed_mass"]["value"] = 32
        raw["molar_masses"][0].update(species_id="oxygen", value=32)
        rxn["mass_projection"] = raw
        item = evaluate({"reactions": [rxn]})["reactions"][0]["mass_projection"]
        self.assertEqual(item["coefficient_ratio"], "2")
        self.assertEqual(item["mass_ratio"], "9/8")
        self.assertEqual(item["product_mass"]["value"], "36")

    def test_bad_mass_values_units_and_fields(self):
        for value in (0, -1, True, math.inf, math.nan, "NaN", "1/0", None):
            for field in ("feed", "molar"):
                raw = projection()
                target = raw["feed_mass"] if field == "feed" else raw["molar_masses"][0]
                target["value"] = value
                result = self.checked(raw)
                self.assertTrue(result["errors"])
                self.assertFalse(result["math_valid"])
                json.dumps(result, allow_nan=False)
        for unit in ("kmol/h", "L/h", "kg/year", "kg/hr", "KG", "kg / h", True):
            self.assertTrue(self.checked(projection(1, unit))["errors"])
        for unit in ("kg/mol", "g/kmol", "lb/lbmol", "", True):
            raw = projection()
            raw["molar_masses"][0]["unit"] = unit
            self.assertTrue(self.checked(raw)["errors"])
        for field in ("reactant_id", "product_id", "feed_mass", "molar_masses"):
            raw = projection()
            del raw[field]
            self.assertTrue(self.checked(raw)["errors"])

    def test_mass_species_alignment_and_cardinality(self):
        for field, sid in (("reactant_id", "water"), ("product_id", "hydrogen"),
                           ("reactant_id", "absent"), ("product_id", "absent")):
            raw = projection()
            raw[field] = sid
            self.assertTrue(self.checked(raw)["errors"])

        for rows in (None, [], projection()["molar_masses"][:1], projection()["molar_masses"] * 2):
            raw = projection()
            raw["molar_masses"] = rows
            self.assertTrue(self.checked(raw)["errors"])
        for sid in ("hydrogen", "oxygen", "absent"):
            raw = projection()
            raw["molar_masses"][1]["species_id"] = sid
            self.assertTrue(self.checked(raw)["errors"])

    def test_huge_projection_rejected_without_overflow(self):
        raw = projection("1e1000")
        raw["molar_masses"][1]["value"] = "1e1000"
        result = self.checked(raw)
        self.assertTrue(result["errors"])
        self.assertFalse(result["math_valid"])
        json.dumps(result, allow_nan=False)


class CliTests(unittest.TestCase):
    def call(self, source, output=False, write_error=None):
        stdout = io.StringIO()
        arguments = ["--input", "synthetic.json"]
        if output:
            arguments += ["--output", "synthetic-result.json"]
        with patch.object(Path, "read_text", return_value=source), patch.object(Path, "write_text", side_effect=write_error) as writer, redirect_stdout(stdout):
            code = main(arguments)
        return code, json.loads(stdout.getvalue()), writer

    def test_cli_json_and_optional_output_without_disk_writes(self):
        source = json.dumps({"reactions": [water()]})
        code, result, writer = self.call(source)
        self.assertEqual(code, 0)
        self.assertTrue(result["math_valid"])
        writer.assert_not_called()
        code, result, writer = self.call(source, output=True)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(writer.call_args.args[0]), result)
        self.assertEqual(writer.call_args.kwargs["encoding"], "utf-8")

    def test_cli_invalid_json_duplicate_keys_and_nonfinite(self):
        for source in ("{", '{"reactions": [], "reactions": []}', '{"reactions": NaN}',
                       '{"reactions": Infinity}', '{"reactions": -Infinity}'):
            code, result, _ = self.call(source)
            self.assertEqual(code, 2)
            self.assertTrue(result["errors"])
            self.assertFalse(result["math_valid"])

    def test_cli_io_failure_is_json_not_traceback(self):
        code, result, _ = self.call(json.dumps({"reactions": [water()]}), True, OSError("synthetic output failure"))
        self.assertEqual(code, 2)
        self.assertTrue(any("output:" in item for item in result["errors"]))
        stdout = io.StringIO()
        with patch.object(Path, "read_text", side_effect=OSError("synthetic input failure")), redirect_stdout(stdout):
            self.assertEqual(main(["--input", "synthetic.json"]), 2)
        self.assertIn("input:", json.loads(stdout.getvalue())["errors"][0])


if __name__ == "__main__":
    unittest.main()
