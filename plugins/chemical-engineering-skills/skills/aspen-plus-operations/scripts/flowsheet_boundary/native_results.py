# SPDX-License-Identifier: MIT
"""Small, offline helpers for reading Aspen native result snapshots.

This module only reads result-tree rows. It does not run Aspen, estimate
properties, perform EDR rating, calculate whole-plant pinch targets, or assert
engineering acceptance.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

KW_PER_GCAL_HR = 1163.0  # Aspen calorie basis: 4.1868 J/cal.


def _validate_path(path: Any) -> str:
    if not isinstance(path, str) or not path:
        raise ValueError("each result row must contain a non-empty string path")
    return path


def leaf_index(rows: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """Return rows keyed by path, retaining only paths with no child nodes.

    Repeated paths are rejected, including duplicate containers, so callers
    cannot silently select an arbitrary row from an ambiguous snapshot.
    """
    by_path: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("each result row must be a mapping")
        path = _validate_path(row.get("path"))
        if path in by_path:
            raise ValueError(f"duplicate result path: {path}")
        by_path[path] = dict(row)

    has_child: set[str] = set()
    for path in by_path:
        parent = path
        while "\\" in parent:
            parent = parent.rsplit("\\", 1)[0]
            if parent in by_path:
                has_child.add(parent)
    return {path: row for path, row in by_path.items() if path not in has_child}


def mixed_scalar(rows: Iterable[Mapping[str, Any]], field_path: str) -> Any:
    """Return the exact ``field_path + '\\MIXED'`` leaf value."""
    if not isinstance(field_path, str) or not field_path:
        raise ValueError("field_path must be a non-empty string")
    target = field_path.rstrip("\\") + "\\MIXED"
    row = leaf_index(rows).get(target)
    if row is None:
        raise ValueError(f"missing mixed scalar leaf: {target}")
    return row.get("Value")


def component_flows(rows: Iterable[Mapping[str, Any]], field_path: str) -> dict[str, Any]:
    """Return immediate component leaves under ``field_path\\MIXED`` only."""
    if not isinstance(field_path, str) or not field_path:
        raise ValueError("field_path must be a non-empty string")
    root = field_path.rstrip("\\") + "\\MIXED\\"
    leaves = leaf_index(rows)
    result: dict[str, Any] = {}
    for path, row in leaves.items():
        if path.startswith(root):
            component = path[len(root):]
            if component and "\\" not in component:
                result[component] = row.get("Value")
    return result


def _number(row: Mapping[str, Any], path: str) -> float:
    value = row.get("Value")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"non-numeric value at {path}: {value!r}")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"non-finite value at {path}: {value!r}")
    return value


def heatx_profile(
    rows: Iterable[Mapping[str, Any]], output_path: str
) -> dict[str, Any]:
    """Build a paired native hot/cold profile from four INLET point arrays.

    Requires matching point IDs, finite numeric values, temperature units ``C``,
    duty units ``Gcal/hr``, and matching hot/cold cumulative-duty grids within
    absolute tolerance 1e-10 Gcal/hr. Duty signs and temperature order are kept
    exactly as received; pairing is by point ID, never temperature sorting.
    """
    if not isinstance(output_path, str) or not output_path:
        raise ValueError("output_path must be a non-empty string")
    root = output_path.rstrip("\\")
    leaves = leaf_index(rows)
    pattern = re.compile(
        re.escape(root) + r"\\(TEMP_HOT|TEMP_CLD|DUTY_HOT|DUTY_CLD)\\INLET\\([0-9]+)$"
    )
    arrays: dict[str, dict[int, dict[str, Any]]] = {
        key: {} for key in ("TEMP_HOT", "TEMP_CLD", "DUTY_HOT", "DUTY_CLD")
    }
    for path, row in leaves.items():
        match = pattern.fullmatch(path)
        if not match:
            continue
        key, raw_id = match.groups()
        point_id = int(raw_id)
        if point_id in arrays[key]:
            raise ValueError(f"duplicate {key} point ID: {point_id}")
        arrays[key][point_id] = row

    expected = set(arrays["TEMP_HOT"])
    if not expected:
        raise ValueError(f"empty or missing TEMP_HOT points under {root}")
    for key, values in arrays.items():
        if not values:
            raise ValueError(f"empty or missing {key} points under {root}")
        if set(values) != expected:
            raise ValueError(
                f"point IDs for {key} differ from TEMP_HOT: "
                f"expected {sorted(expected)}, got {sorted(values)}"
            )

    for key in ("TEMP_HOT", "TEMP_CLD"):
        for point_id, row in arrays[key].items():
            path = f"{root}\\{key}\\INLET\\{point_id}"
            if row.get("UnitString") != "C":
                raise ValueError(f"{key} point {point_id} must have unit C")
            _number(row, path)
    for key in ("DUTY_HOT", "DUTY_CLD"):
        for point_id, row in arrays[key].items():
            path = f"{root}\\{key}\\INLET\\{point_id}"
            if row.get("UnitString") != "Gcal/hr":
                raise ValueError(f"{key} point {point_id} must have unit Gcal/hr")
            _number(row, path)

    point_ids = sorted(expected)
    points: list[dict[str, Any]] = []
    for point_id in point_ids:
        hot_duty = _number(arrays["DUTY_HOT"][point_id], f"{root}\\DUTY_HOT\\INLET\\{point_id}")
        cold_duty = _number(arrays["DUTY_CLD"][point_id], f"{root}\\DUTY_CLD\\INLET\\{point_id}")
        if abs(hot_duty - cold_duty) > 1e-10:
            raise ValueError(
                f"hot/cold duty grid mismatch at point {point_id}: "
                f"{hot_duty} vs {cold_duty} Gcal/hr"
            )
        hot_temp = _number(arrays["TEMP_HOT"][point_id], f"{root}\\TEMP_HOT\\INLET\\{point_id}")
        cold_temp = _number(arrays["TEMP_CLD"][point_id], f"{root}\\TEMP_CLD\\INLET\\{point_id}")
        points.append({
            "point_id": point_id,
            "temperature_hot_C": hot_temp,
            "temperature_cold_C": cold_temp,
            "duty_hot_Gcal_hr": hot_duty,
            "duty_cold_Gcal_hr": cold_duty,
            "duty_grid_Gcal_hr": hot_duty,
            "duty_grid_kW": hot_duty * KW_PER_GCAL_HR,
            "approach_K": hot_temp - cold_temp,
        })
    minimum_point = min(points, key=lambda point: point["approach_K"])
    return {
        "output_path": root,
        "point_count": len(points),
        "point_ids": point_ids,
        "duty_grid_tolerance_Gcal_hr": 1e-10,
        "kw_per_Gcal_hr": KW_PER_GCAL_HR,
        "minimum_approach_K": minimum_point["approach_K"],
        "minimum_approach_point_id": minimum_point["point_id"],
        "points": points,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, help="JSON snapshot containing a probes mapping")
    parser.add_argument("--heatx-output", required=True, help="exact Aspen output tree path")
    args = parser.parse_args()
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    probes = snapshot.get("probes")
    if not isinstance(probes, Mapping) or args.heatx_output not in probes:
        raise SystemExit(f"snapshot has no probes rows for {args.heatx_output!r}")
    summary = heatx_profile(probes[args.heatx_output], args.heatx_output)
    summary["scope"] = (
        "Native paired profile only; not a whole-plant pinch analysis, "
        "EDR rating, or strict engineering acceptance."
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
