# SPDX-License-Identifier: MIT
"""Compare native result snapshots with an explicit external heat boundary.

No engineering thresholds, savings acceptance, or automatic heater deletion.
The caller supplies retained streams and external heat fields; excluded internal
exchange and changed product-state boundaries must be reviewed by the owner.
"""
from __future__ import annotations

import argparse
import json
import math
if __package__:
    from .native_results import leaf_index
else:
    from native_results import leaf_index

ASPEN_GCAL_H_TO_KW = 1163.0  # cal (not tcal) = 4.1868 J.


def _value(rows, suffix, expected_unit):
    found = [r for r in leaf_index(rows).values() if r["path"].endswith(suffix)]
    if len(found) != 1:
        raise ValueError("Missing or duplicated numeric leaf: " + suffix)
    row = found[0]
    value = row.get("Value")
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("Numeric finite leaf required")
    if row.get("UnitString", "") != expected_unit:
        raise ValueError("Unexpected native unit")
    return value


def compare_retained_streams(before, after, stream_ids):
    """Return actual unequal values; exact equality is not inferred from hashes."""
    differences = []
    fields = {"TEMP_OUT": "C", "PRES_OUT": "bar", "MASSFLMX": "kg/hr", "VFRAC_OUT": ""}
    if not stream_ids or len(set(stream_ids)) != len(stream_ids):
        raise ValueError("Explicit unique retained streams required")
    for sid in stream_ids:
        old, new = before["streams"][sid], after["streams"][sid]
        for key, unit in fields.items():
            values = [_value(record[key], "\\" + key + "\\MIXED", unit) for record in (old, new)]
            if values[0] != values[1]:
                differences.append({"stream": sid, "field": key, "before": values[0], "after": values[1]})
        components = []
        for record in (old, new):
            values = {}
            for row in leaf_index(record["MASSFLOW"]).values():
                if "\\MASSFLOW\\MIXED\\" not in row["path"]:
                    continue
                component = row["path"].split("\\MASSFLOW\\MIXED\\", 1)[1]
                if "\\" in component or not component:
                    continue
                if component in values:
                    raise ValueError("Duplicate component")
                if row.get("UnitString") != "kg/hr" or type(row.get("Value")) not in (int, float) or not math.isfinite(row["Value"]):
                    raise ValueError("Unexpected component value/unit")
                values[component] = row["Value"]
            if not values:
                raise ValueError("Component leaves missing")
            components.append(values)
        if components[0].keys() != components[1].keys():
            raise ValueError("Component identities differ")
        for component in components[0]:
            a, b = (x[component] for x in components)
            if a != b:
                differences.append({"stream": sid, "field": "MASSFLOW." + component, "before": a, "after": b})
    return differences


def utility_totals(results, *, external_heat_fields, shaft_blocks):
    """Sum only explicitly reviewed services; an internal HeatX is not added.

    external_heat_fields: list of unique (block, output-field) pairs, units Gcal/hr.
    shaft_blocks: explicit list of blocks whose WNET is in kW.
    Results are heat, cooling magnitude and shaft separately. No money, motor
    electrical input, primary-energy or same-product savings claim is generated.
    """
    pairs = [tuple(row) for row in external_heat_fields]
    if len(pairs) != len(set(pairs)) or len(shaft_blocks) != len(set(shaft_blocks)):
        raise ValueError("Duplicate utility service")
    heat = []
    for block, key in pairs:
        heat.append(_value(results["blocks"][block][key], "\\" + key, "Gcal/hr"))
    power = [_value(results["blocks"][b]["WNET"], "\\WNET", "kW") for b in shaft_blocks]
    return {"external_heating_kW": sum(max(q, 0) for q in heat) * ASPEN_GCAL_H_TO_KW,
            "external_cooling_kW": -sum(min(q, 0) for q in heat) * ASPEN_GCAL_H_TO_KW,
            "shaft_kW": sum(power), "Gcal_h_to_kW": ASPEN_GCAL_H_TO_KW,
            "boundary_review_required": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before"); parser.add_argument("after"); parser.add_argument("contract")
    args = parser.parse_args()
    with open(args.before, encoding="utf-8-sig") as f: old = json.load(f)
    with open(args.after, encoding="utf-8-sig") as f: new = json.load(f)
    with open(args.contract, encoding="utf-8-sig") as f: contract = json.load(f)
    old, new = old["results"], new["results"]
    output = {"retained_stream_differences": compare_retained_streams(old, new, contract["retained_streams"]),
              "before_utilities": utility_totals(old, **contract["before_utilities"]),
              "after_utilities": utility_totals(new, **contract["after_utilities"]),
              "scope": "readback arithmetic only; product-boundary review and strict engineering acceptance are separate"}
    print(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
