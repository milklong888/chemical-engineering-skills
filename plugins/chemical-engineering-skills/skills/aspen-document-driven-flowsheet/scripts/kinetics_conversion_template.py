#!/usr/bin/env python3
"""Reusable source-to-Aspen kinetic parameter conversion template.

Use this as a copied/adapted calculator for paper-derived kinetics. The goal is
not to guess a model; it is to make every value reproducible from explicit
source units, dimensional exponents, and destination Aspen units.

Core pattern:
1. Extract the full source equation and identify each parameter's dimensional
   role.
2. Encode the parameter with dimension exponents, source units, Aspen units,
   source locator, and destination card.
3. Run the script and keep its JSON output with the freeze ledger.
4. Independently check one row by hand and compare exported Aspen cards.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping


UNIT_TO_SI = {
    "amount": {
        "mol": 1.0,
        "kmol": 1000.0,
        "lbmol": 453.59237,
    },
    "mass": {
        "g": 1.0e-3,
        "kg": 1.0,
        "lb": 0.45359237,
    },
    "volume": {
        "m3": 1.0,
        "L": 1.0e-3,
        "cm3": 1.0e-6,
    },
    "time": {
        "s": 1.0,
        "min": 60.0,
        "h": 3600.0,
        "day": 86400.0,
    },
    "pressure": {
        "Pa": 1.0,
        "kPa": 1000.0,
        "bar": 100000.0,
        "atm": 101325.0,
        "psi": 6894.757293168,
    },
    "energy": {
        "J": 1.0,
        "kJ": 1000.0,
        "cal": 4.184,
        "kcal": 4184.0,
    },
    "temperature": {
        "K": 1.0,
    },
}

GAS_CONSTANT = {
    "J/mol/K": 8.31446261815324,
    "kJ/mol/K": 8.31446261815324e-3,
    "cal/mol/K": 1.98720425864083,
    "kcal/mol/K": 1.98720425864083e-3,
}


@dataclass(frozen=True)
class Parameter:
    name: str
    value: float
    dimensions: Mapping[str, float]
    source_units: Mapping[str, str]
    aspen_units: Mapping[str, str]
    source: str = ""
    destination: str = ""
    note: str = ""


def unit_factor(family: str, unit: str) -> float:
    try:
        return UNIT_TO_SI[family][unit]
    except KeyError as exc:
        raise KeyError(f"Unknown {family} unit {unit!r}") from exc


def dimensional_factor(
    dimensions: Mapping[str, float],
    source_units: Mapping[str, str],
    aspen_units: Mapping[str, str],
) -> float:
    """Return factor such that value_aspen = value_source * factor."""
    factor = 1.0
    for family, exponent in dimensions.items():
        if abs(exponent) < 1.0e-15:
            continue
        source_unit = source_units.get(family)
        aspen_unit = aspen_units.get(family)
        if source_unit is None or aspen_unit is None:
            raise ValueError(f"Missing units for dimension {family!r}")
        factor *= (unit_factor(family, source_unit) / unit_factor(family, aspen_unit)) ** exponent
    return factor


def convert_parameter(parameter: Parameter) -> Dict[str, Any]:
    factor = dimensional_factor(parameter.dimensions, parameter.source_units, parameter.aspen_units)
    return {
        "name": parameter.name,
        "source_value": parameter.value,
        "factor": factor,
        "aspen_value": parameter.value * factor,
        "dimensions": dict(parameter.dimensions),
        "source_units": dict(parameter.source_units),
        "aspen_units": dict(parameter.aspen_units),
        "source": parameter.source,
        "destination": parameter.destination,
        "note": parameter.note,
        "gate": "check source evidence, one manual row, Aspen card units, exported card",
    }


def activation_energy_from_exp_minus_b_over_t(
    b_temperature: float,
    gas_constant_unit: str = "cal/mol/K",
) -> Dict[str, float]:
    """Convert exp(-B/T) to E for cards that use exp(-E/RT)."""
    r_value = GAS_CONSTANT[gas_constant_unit]
    return {
        "B_K": b_temperature,
        "R": r_value,
        "E": b_temperature * r_value,
    }


def pressure_power_parameter(
    name: str,
    value: float,
    pressure_power: float,
    source_pressure_unit: str,
    aspen_pressure_unit: str,
    source: str,
    destination: str,
    note: str = "",
) -> Parameter:
    """Helper for adsorption constants or pressure-dependent rate constants.

    pressure_power is the exponent of pressure in the parameter units. Example:
    K_ads in 1/bar has pressure_power = -1. A rate constant with units
    mol/(kg_cat h bar^2) has pressure_power = -2 plus amount/mass/time powers.
    """
    return Parameter(
        name=name,
        value=value,
        dimensions={"pressure": pressure_power},
        source_units={"pressure": source_pressure_unit},
        aspen_units={"pressure": aspen_pressure_unit},
        source=source,
        destination=destination,
        note=note,
    )


def load_parameters(spec: Mapping[str, Any]) -> Dict[str, Parameter]:
    parameters: Dict[str, Parameter] = {}
    for row in spec.get("parameters", []):
        parameters[row["name"]] = Parameter(
            name=row["name"],
            value=float(row["value"]),
            dimensions=row["dimensions"],
            source_units=row["source_units"],
            aspen_units=row["aspen_units"],
            source=row.get("source", ""),
            destination=row.get("destination", ""),
            note=row.get("note", ""),
        )
    return parameters


def run_spec(spec: Mapping[str, Any]) -> Dict[str, Any]:
    parameters = load_parameters(spec)
    result = {
        "law_family": spec.get("law_family", "unclassified"),
        "equation_source": spec.get("equation_source", ""),
        "aspen_rate_basis": spec.get("aspen_rate_basis", ""),
        "parameters": [convert_parameter(p) for p in parameters.values()],
        "manual_checks_required": [
            "rendered source row matches typed value",
            "full equation gives listed dimension powers",
            "one converted row is recalculated by hand",
            "one-point rate or stoichiometry probe is plausible",
            "Aspen exported card shows the same value and unit basis",
        ],
    }
    if "arrhenius_B_K" in spec:
        result["activation_energy_from_B"] = activation_energy_from_exp_minus_b_over_t(
            float(spec["arrhenius_B_K"]),
            spec.get("gas_constant_unit", "cal/mol/K"),
        )
    return result


EXAMPLE_SPEC = {
    "law_family": "partial-pressure PowerLaw example",
    "equation_source": "paper page/table/equation locator",
    "aspen_rate_basis": "kmol/(kg_cat h), pressure in bar",
    "parameters": [
        {
            "name": "k_example",
            "value": 1.0,
            "dimensions": {"amount": 1, "mass": -1, "time": -1, "pressure": -1},
            "source_units": {"amount": "mol", "mass": "g", "time": "s", "pressure": "Pa"},
            "aspen_units": {"amount": "kmol", "mass": "kg", "time": "h", "pressure": "bar"},
            "source": "replace with rendered page/table row",
            "destination": "Aspen reaction set / parameter",
            "note": "example only; replace exponents from the full equation",
        }
    ],
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", help="JSON spec file. If omitted, prints an example conversion.")
    parser.add_argument("--example", action="store_true", help="Print example input JSON and exit.")
    args = parser.parse_args()

    if args.example:
        print(json.dumps(EXAMPLE_SPEC, indent=2, ensure_ascii=False))
        return

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8")) if args.spec else EXAMPLE_SPEC
    print(json.dumps(run_spec(spec), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
