#!/usr/bin/env python3
"""Check explicitly declared reaction arithmetic; do not infer chemistry.

Public API: evaluate({"reactions": [reaction, ...]}) -> JSON-safe dict.
An empty list instead requires a nonempty, mutually exclusive ``none_reason``.
Each reaction requires id, scope, basis_ref and species; each species requires
id, formula, coefficient and integer charge, plus basis_ref. Coefficients are
signed (reactants negative), nonzero JSON numbers or exact numeric strings.
Decimal floats are interpreted by their decimal repr; rational strings avoid
roundoff, e.g. "-1/2". Results use canonical Fraction strings, never floats.

Optional mass_projection requires reactant_id, product_id, feed_mass
{value, unit, basis_ref}, and exactly two molar_masses records
{species_id, value, unit, basis_ref}. Molar mass units are kg/kmol or g/mol
(numerically equivalent). Supported mass units: mg, g, kg, t; optionally /s,
/min, /h, /d or /day. The feed unit is retained without changing its time basis.
Only complete-consumption hypothetical contributions are calculated. Molecular
weights and source/entity alignment remain caller-supplied, unverified data.

Formula grammar: actual element symbols, positive integer subscripts, nested
() and [] groups. Hydrate dots, isotopes, embedded charge, variable repeats,
whitespace, leading coefficients and other syntax are explicitly unsupported.
Limits bound work on malformed inputs: 256 reactions/species, formula length
512, nesting 32, subscript 1,000,000; numeric strings 128 chars, exponent 1,000,
and rational numerator/denominator 4,096 bits. No network, Aspen or eval.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from fractions import Fraction
from pathlib import Path


ELEMENTS = frozenset("H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og".split())
MASS_UNITS = frozenset(
    [mass for mass in ("mg", "g", "kg", "t")]
    + [f"{mass}/{time}" for mass in ("mg", "g", "kg", "t")
       for time in ("s", "min", "h", "d", "day")]
)
NUMBER = re.compile(r"[+-]?(?:[0-9]+/[+-]?[0-9]+|(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?)\Z")
BOUNDARY = ("Mathematical consistency only. False engineering/source flags mean "
            "not established, not a finding of chemical infeasibility.")


class DeclarationError(ValueError):
    """Unsupported or invalid explicit declaration."""


def _flags():
    return {"source_verified": False, "engineering_accepted": False,
            "reaction_feasible": False}


def _text(value, path):
    if not isinstance(value, str) or not value.strip() or len(value) > 4096:
        raise DeclarationError(f"{path}: requires nonempty text of at most 4096 characters")
    return value


def _fields(value, required, optional, path):
    if type(value) is not dict:
        raise DeclarationError(f"{path}: requires an object")
    if any(not isinstance(key, str) for key in value):
        raise DeclarationError(f"{path}: object keys must be strings")
    missing = set(required) - set(value)
    extra = set(value) - set(required) - set(optional)
    if missing or extra:
        raise DeclarationError(f"{path}: missing fields {sorted(missing)}; unsupported fields {sorted(extra)}")


def _number(value, path, *, positive=False, nonzero=False):
    if type(value) is int:
        if value.bit_length() > 4096:
            raise DeclarationError(f"{path}: integer exceeds 4096-bit safety limit")
        result = Fraction(value)
    elif type(value) is float:
        if not math.isfinite(value):
            raise DeclarationError(f"{path}: number must be finite")
        result = Fraction(str(value))
    elif type(value) is str:
        if len(value) > 128 or not NUMBER.fullmatch(value):
            raise DeclarationError(f"{path}: unsupported numeric syntax or length")
        if "e" in value.lower() and abs(int(value.lower().split("e")[1])) > 1000:
            raise DeclarationError(f"{path}: exponent exceeds 1000 safety limit")
        try:
            if "/" in value:
                numerator, denominator = value.split("/")
                result = Fraction(int(numerator), int(denominator))
            else:
                result = Fraction(value)
        except (ValueError, ZeroDivisionError) as exc:
            raise DeclarationError(f"{path}: invalid finite rational number") from exc
    else:
        raise DeclarationError(f"{path}: requires an int, finite float or exact numeric string; bool is not numeric")
    _bounded(result, path)
    if positive and result <= 0:
        raise DeclarationError(f"{path}: must be strictly positive")
    if nonzero and result == 0:
        raise DeclarationError(f"{path}: zero coefficient is not allowed")
    return result


def _bounded(value, path):
    if max(value.numerator.bit_length(), value.denominator.bit_length()) > 4096:
        raise DeclarationError(f"{path}: rational arithmetic exceeds 4096-bit safety limit")
    return value


def parse_formula(formula):
    """Return element -> integer count, or reject the entire unsupported string."""
    if type(formula) is not str or not formula or len(formula) > 512:
        raise DeclarationError("formula: requires a nonempty string of at most 512 characters")
    position = 0

    def count():
        nonlocal position
        start = position
        while position < len(formula) and formula[position] in "0123456789":
            position += 1
        if position == start:
            return 1
        digits = formula[start:position]
        if digits.startswith("0") or len(digits) > 7 or int(digits) > 1000000:
            raise DeclarationError("formula: subscripts must be positive integers <= 1000000 without leading zeros")
        return int(digits)

    def group(closing=None, depth=0):
        nonlocal position
        if depth > 32:
            raise DeclarationError("formula: nesting exceeds 32 safety limit")
        atoms = {}
        terms = 0
        while position < len(formula):
            char = formula[position]
            if char in ")]":
                if char != closing:
                    raise DeclarationError(f"formula: unmatched closing bracket at offset {position}")
                if not terms:
                    raise DeclarationError("formula: empty groups are not supported")
                position += 1
                return atoms
            if char in "([":
                position += 1
                inner = group(")" if char == "(" else "]", depth + 1)
                multiplier = count()
                for element, amount in inner.items():
                    atoms[element] = atoms.get(element, 0) + multiplier * amount
            elif "A" <= char <= "Z":
                start = position
                position += 1
                if position < len(formula) and "a" <= formula[position] <= "z":
                    position += 1
                element = formula[start:position]
                if element not in ELEMENTS:
                    raise DeclarationError(f"formula: unknown element {element!r}")
                atoms[element] = atoms.get(element, 0) + count()
            else:
                raise DeclarationError(f"formula: unsupported character/syntax {char!r} at offset {position}; no characters were discarded")
            terms += 1
        if closing is not None:
            raise DeclarationError(f"formula: missing closing bracket {closing!r}")
        if not terms:
            raise DeclarationError("formula: empty formula")
        return atoms

    return group()


def _mass_projection(raw, species, reaction, path):
    result = {"status": "invalid", "math_checked": False, "math_valid": False,
              "errors": [], "scope": reaction["scope"], "basis_ref": reaction["basis_ref"],
              "quantity_kind": "hypothetical_stoichiometric_contribution",
              "molar_masses_verified": False, "basis_alignment_verified": False,
              **_flags()}
    try:
        _fields(raw, {"reactant_id", "product_id", "feed_mass", "molar_masses"}, set(), path)
        reactant = _text(raw["reactant_id"], path + ".reactant_id")
        product = _text(raw["product_id"], path + ".product_id")
        if reactant not in species or species[reactant]["coefficient"] >= 0:
            raise DeclarationError(f"{path}.reactant_id: must name a declared negative-coefficient species")
        if product not in species or species[product]["coefficient"] <= 0:
            raise DeclarationError(f"{path}.product_id: must name a declared positive-coefficient species")
        feed = raw["feed_mass"]
        _fields(feed, {"value", "unit", "basis_ref"}, set(), path + ".feed_mass")
        mass = _number(feed["value"], path + ".feed_mass.value", positive=True)
        unit = _text(feed["unit"], path + ".feed_mass.unit")
        if unit not in MASS_UNITS:
            raise DeclarationError(f"{path}.feed_mass.unit: unsupported fixed mass or mass-flow unit {unit!r}")
        _text(feed["basis_ref"], path + ".feed_mass.basis_ref")
        rows = raw["molar_masses"]
        if type(rows) is not list or len(rows) != 2:
            raise DeclarationError(f"{path}.molar_masses: requires exactly two records")
        masses = {}
        normalized = []
        for index, row in enumerate(rows):
            where = f"{path}.molar_masses[{index}]"
            _fields(row, {"species_id", "value", "unit", "basis_ref"}, set(), where)
            sid = _text(row["species_id"], where + ".species_id")
            if sid not in {reactant, product} or sid in masses:
                raise DeclarationError(f"{where}.species_id: must name each selected species exactly once")
            mw_unit = _text(row["unit"], where + ".unit")
            if mw_unit not in {"kg/kmol", "g/mol"}:
                raise DeclarationError(f"{where}.unit: only kg/kmol and g/mol are supported")
            value = _number(row["value"], where + ".value", positive=True)
            _text(row["basis_ref"], where + ".basis_ref")
            masses[sid] = value
            normalized.append({**row, "value": str(value)})
        if not reaction["math_valid"]:
            raise DeclarationError(f"{path}: no projection from an unbalanced reaction")
        coefficient_ratio = _bounded(species[product]["coefficient"] / -species[reactant]["coefficient"], path)
        mass_ratio = _bounded(coefficient_ratio * masses[product] / masses[reactant], path)
        product_mass = _bounded(mass * mass_ratio, path)
        result.update({
            "status": "checked", "math_checked": True, "math_valid": True,
            "reactant_id": reactant, "product_id": product,
            "coefficient_ratio": str(coefficient_ratio), "mass_ratio": str(mass_ratio),
            "feed_mass": {**feed, "value": str(mass)}, "molar_masses": normalized,
            "product_mass": {"value": str(product_mass), "unit": unit},
            "assumptions": [
                "The full declared feed mass is the selected reactant on its declared molecular/repeat-unit basis; source/entity alignment was not verified.",
                "The selected basis reactant is completely consumed by this one declared reaction.",
                "All co-reactants are available in sufficient quantities; their availability was not verified.",
                "No side reactions, process losses, or actual conversion/recovery are modeled.",
                "Caller-supplied molar masses are not independently derived from elemental atomic weights.",
                "This is only the declared scope's hypothetical contribution, not actual yield, plant capacity, or a whole-plant bound.",
            ],
        })
    except DeclarationError as exc:
        result["errors"].append(str(exc))
    return result


def _reaction(raw, path, seen_ids):
    result = {"id": None, "status": "invalid", "math_checked": False,
              "math_valid": False, "element_residuals": None, "charge_residual": None,
              "errors": [], **_flags()}
    try:
        _fields(raw, {"id", "scope", "basis_ref", "species"}, {"mass_projection"}, path)
        rid = _text(raw["id"], path + ".id")
        result["id"] = rid
        if rid in seen_ids:
            raise DeclarationError(f"{path}.id: duplicate reaction ID {rid!r}")
        seen_ids.add(rid)
        result["scope"] = _text(raw["scope"], path + ".scope")
        result["basis_ref"] = _text(raw["basis_ref"], path + ".basis_ref")
        rows = raw["species"]
        if type(rows) is not list or not 2 <= len(rows) <= 256:
            raise DeclarationError(f"{path}.species: requires 2 to 256 records")
        species = {}
        for index, row in enumerate(rows):
            where = f"{path}.species[{index}]"
            _fields(row, {"id", "formula", "coefficient", "charge", "basis_ref"}, set(), where)
            sid = _text(row["id"], where + ".id")
            if sid in species:
                raise DeclarationError(f"{where}.id: duplicate species ID {sid!r}")
            coefficient = _number(row["coefficient"], where + ".coefficient", nonzero=True)
            charge = row["charge"]
            if type(charge) is not int or charge.bit_length() > 4096:
                raise DeclarationError(f"{where}.charge: requires an integer (not bool), within 4096 bits")
            _text(row["basis_ref"], where + ".basis_ref")
            try:
                elements = parse_formula(row["formula"])
            except DeclarationError as exc:
                raise DeclarationError(f"{where}.{exc}") from exc
            species[sid] = {**row, "coefficient": coefficient, "elements": elements}
        if not any(row["coefficient"] < 0 for row in species.values()) or not any(row["coefficient"] > 0 for row in species.values()):
            raise DeclarationError(f"{path}.species: requires at least one reactant and one product")
        residuals = {}
        charge_residual = Fraction(0)
        for row in species.values():
            for element, count in row["elements"].items():
                residuals[element] = _bounded(residuals.get(element, Fraction(0)) + row["coefficient"] * count, path)
            charge_residual = _bounded(charge_residual + row["coefficient"] * row["charge"], path)
        result["math_checked"] = True
        result["element_residuals"] = {key: str(value) for key, value in sorted(residuals.items())}
        result["charge_residual"] = str(charge_residual)
        result["species"] = [{**row, "coefficient": str(row["coefficient"])} for row in species.values()]
        for element, residual in sorted(residuals.items()):
            if residual:
                result["errors"].append(f"{path}: element {element} residual is {residual} (products minus reactants)")
        if charge_residual:
            result["errors"].append(f"{path}: charge residual is {charge_residual} (products minus reactants)")
        result["math_valid"] = not result["errors"]
        if "mass_projection" in raw:
            projection = _mass_projection(raw["mass_projection"], species, result, path + ".mass_projection")
            result["mass_projection"] = projection
            result["errors"].extend(projection["errors"])
            result["math_valid"] = not result["errors"]
        result["status"] = "checked" if result["math_valid"] else "invalid"
    except DeclarationError as exc:
        result["errors"].append(str(exc))
    return result


def evaluate(payload):
    """Validate declarations and exact arithmetic without changing the payload."""
    result = {"schema": "reaction-derivations-check-v1", "status": "invalid",
              "applicable": None, "math_checked": False, "math_valid": False,
              "errors": [], "reactions": [], "boundary": BOUNDARY, **_flags()}
    try:
        _fields(payload, {"reactions"}, {"none_reason"}, "payload")
        reactions = payload["reactions"]
        if type(reactions) is not list or len(reactions) > 256:
            raise DeclarationError("payload.reactions: requires a list of at most 256 reactions")
        result["applicable"] = bool(reactions)
        if not reactions:
            result["none_reason"] = _text(payload.get("none_reason"), "payload.none_reason")
            result["status"] = "not_applicable"
            return result
        if "none_reason" in payload:
            raise DeclarationError("payload.none_reason: mutually exclusive with nonempty reactions")
        seen_ids = set()
        for index, raw in enumerate(reactions):
            reaction = _reaction(raw, f"reactions[{index}]", seen_ids)
            result["reactions"].append(reaction)
            result["errors"].extend(reaction["errors"])
        result["math_checked"] = all(row["math_checked"] for row in result["reactions"])
        result["math_valid"] = result["math_checked"] and not result["errors"]
        result["status"] = "checked" if result["math_valid"] else "invalid"
    except DeclarationError as exc:
        result["errors"].append(str(exc))
    return result


def _json_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise DeclarationError(f"input JSON: duplicate object key {key!r}")
        value[key] = item
    return value


def _bad_constant(value):
    raise DeclarationError(f"input JSON: nonfinite constant {value!r} is not permitted")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Explicit reaction JSON declarations")
    parser.add_argument("--output", type=Path, help="Optional JSON result path; parent directory must exist")
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8-sig"),
                             object_pairs_hook=_json_pairs, parse_constant=_bad_constant)
        result = evaluate(payload)
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        result = evaluate(None)
        result["errors"] = [f"input: {exc}"]
    serialized = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.output:
        try:
            args.output.write_text(serialized, encoding="utf-8")
        except OSError as exc:
            result["errors"].append(f"output: {exc}")
            result["status"] = "invalid"
            result["math_valid"] = False
            serialized = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    print(serialized, end="")
    return 0 if not result["errors"] else 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
