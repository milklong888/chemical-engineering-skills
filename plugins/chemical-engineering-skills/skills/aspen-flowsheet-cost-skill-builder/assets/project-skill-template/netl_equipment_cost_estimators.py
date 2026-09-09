from __future__ import annotations

import csv
import json
import math
from pathlib import Path


DATA_PATH = Path(__file__).resolve().parents[1] / "extracted_data" / "netl_equipment_cost_points.csv"


def _to_float(value):
    if value in ("", None):
        return None
    return float(value)


def load_points(data_path: Path = DATA_PATH):
    with data_path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["capacity_value"] = _to_float(row["capacity_value"])
        row["purchased_equipment_cost_1998_usd"] = _to_float(row["purchased_equipment_cost_1998_usd"])
        row["installed_cost_1998_usd"] = _to_float(row["installed_cost_1998_usd"])
        row["independent_values"] = json.loads(row["independent_values_json"])
    return rows


def select_group(points, equipment_type, subtype="", variant=""):
    group = [
        row for row in points
        if row["equipment_type"] == equipment_type
        and row["subtype"] == subtype
        and row["variant"] == variant
    ]
    if not group:
        available = sorted({(r["equipment_type"], r["subtype"], r["variant"]) for r in points})
        raise KeyError(f"No NETL cost group for {(equipment_type, subtype, variant)}. Available groups: {available[:20]} ...")
    return group


def exact_anchor_cost(group, independent_values, cost_basis="purchased"):
    key = _cost_key(cost_basis)
    wanted = {}
    for name, value in independent_values.items():
        try:
            wanted[name] = float(value)
        except (TypeError, ValueError):
            continue
    if not wanted:
        return None
    for row in group:
        actual = row["independent_values"]
        numeric_actual = {}
        for name, value in actual.items():
            try:
                numeric_actual[name] = float(value)
            except (TypeError, ValueError):
                continue
        if wanted.keys() <= numeric_actual.keys() and all(abs(numeric_actual[k] - wanted[k]) <= 1e-9 for k in wanted):
            return row[key]
    return None


def _cost_key(cost_basis):
    if cost_basis == "purchased":
        return "purchased_equipment_cost_1998_usd"
    if cost_basis == "installed":
        return "installed_cost_1998_usd"
    raise ValueError("cost_basis must be 'purchased' or 'installed'")


def _log_interp(x, x0, y0, x1, y1):
    if x0 == x1:
        return y0
    fraction = (math.log(x) - math.log(x0)) / (math.log(x1) - math.log(x0))
    return math.exp(math.log(y0) + fraction * (math.log(y1) - math.log(y0)))


def _bracket(values, target, label):
    ordered = sorted(set(float(value) for value in values))
    if target < ordered[0] or target > ordered[-1]:
        raise ValueError(
            f"{label}={target} is outside NETL Appendix B range "
            f"[{ordered[0]}, {ordered[-1]}]; extrapolation requires explicit review"
        )
    lower = max(value for value in ordered if value <= target)
    upper = min(value for value in ordered if value >= target)
    return lower, upper


def piecewise_loglog_1d(group, capacity_value, cost_basis="purchased"):
    """Piecewise log-log interpolation for single-capacity NETL groups.

    This is the default offline estimator because it exactly reproduces Appendix B
    anchor costs at tabulated capacities and avoids mixing installed-cost factors
    into purchased equipment cost.
    """
    key = _cost_key(cost_basis)
    by_capacity = {}
    for row in group:
        if row["capacity_value"] is None or row[key] is None:
            continue
        x = float(row["capacity_value"])
        y = float(row[key])
        if x in by_capacity and abs(by_capacity[x] - y) > 1e-9:
            raise ValueError(
                "capacity_value is not unique in this NETL group; "
                "provide independent_values for multidimensional interpolation"
            )
        by_capacity[x] = y
    points = sorted(by_capacity.items())
    if capacity_value <= 0:
        raise ValueError("capacity_value must be positive for log-log interpolation")
    for x, y in points:
        if abs(x - capacity_value) <= 1e-12:
            return y
    lower = None
    upper = None
    for x, y in points:
        if x < capacity_value:
            lower = (x, y)
        elif x > capacity_value and upper is None:
            upper = (x, y)
            break
    if lower is None or upper is None:
        raise ValueError("capacity_value is outside NETL Appendix B range; extrapolation requires explicit review")
    x0, y0 = lower
    x1, y1 = upper
    return _log_interp(capacity_value, x0, y0, x1, y1)


def bilinear_loglog_2d(
    group,
    x_name,
    x_value,
    y_name,
    y_value,
    cost_basis="purchased",
):
    """Interpolate a complete two-dimensional NETL grid in log-cost space."""
    key = _cost_key(cost_basis)
    usable = []
    for row in group:
        values = row["independent_values"]
        if x_name not in values or y_name not in values or row[key] is None:
            continue
        usable.append(
            (
                float(values[x_name]),
                float(values[y_name]),
                float(row[key]),
            )
        )
    if not usable:
        raise ValueError(f"No numeric NETL grid for {x_name} and {y_name}")
    if x_value <= 0 or y_value <= 0:
        raise ValueError("multidimensional interpolation values must be positive")

    x0, x1 = _bracket((row[0] for row in usable), float(x_value), x_name)
    y0, y1 = _bracket((row[1] for row in usable), float(y_value), y_name)
    lookup = {(x, y): cost for x, y, cost in usable}

    corners = {}
    for x in {x0, x1}:
        for y in {y0, y1}:
            if (x, y) not in lookup:
                raise ValueError(
                    f"Incomplete NETL interpolation grid at {x_name}={x}, {y_name}={y}"
                )
            corners[(x, y)] = lookup[(x, y)]

    at_y0 = _log_interp(float(x_value), x0, corners[(x0, y0)], x1, corners[(x1, y0)])
    at_y1 = _log_interp(float(x_value), x0, corners[(x0, y1)], x1, corners[(x1, y1)])
    cost = _log_interp(float(y_value), y0, at_y0, y1, at_y1)
    return {
        "cost_1998_usd": cost,
        "method": "bilinear_loglog_2d",
        "status": "interpolated",
        "bounds": {
            x_name: [x0, x1],
            y_name: [y0, y1],
        },
    }


def compressor_capacity_power_interpolation(
    group,
    actual_capacity,
    driver_power,
    cost_basis="purchased",
):
    """Interpolate centrifugal-compressor service curves.

    NETL Appendix B contains several costs at the same actual inlet flow. They
    represent distinct specific-power services, so flow-only interpolation is
    ambiguous. Rows are clustered by driver_power / actual_capacity, each
    service curve is interpolated in capacity, and intermediate specific power
    is interpolated between adjacent service curves.
    """
    key = _cost_key(cost_basis)
    actual_capacity = float(actual_capacity)
    driver_power = float(driver_power)
    if actual_capacity <= 0 or driver_power <= 0:
        raise ValueError("compressor actual_capacity and driver_power must be positive")

    usable = []
    for row in group:
        values = row["independent_values"]
        if "actual_capacity" not in values or "driver_power" not in values or row[key] is None:
            continue
        capacity = float(values["actual_capacity"])
        power = float(values["driver_power"])
        usable.append(
            {
                "specific_power": power / capacity,
                "capacity": capacity,
                "cost": float(row[key]),
            }
        )
    if not usable:
        raise ValueError("No NETL compressor capacity-power anchors are available")

    clusters = []
    for point in sorted(usable, key=lambda item: item["specific_power"]):
        if not clusters:
            clusters.append([point])
            continue
        previous_max = max(item["specific_power"] for item in clusters[-1])
        if point["specific_power"] / previous_max > 1.5:
            clusters.append([point])
        else:
            clusters[-1].append(point)

    service_curves = []
    for cluster in clusters:
        ratios = sorted(item["specific_power"] for item in cluster)
        median_ratio = ratios[len(ratios) // 2]
        curve = sorted((item["capacity"], item["cost"]) for item in cluster)
        capacities = [item[0] for item in curve]
        if actual_capacity < min(capacities) or actual_capacity > max(capacities):
            continue
        by_capacity = {capacity: cost for capacity, cost in curve}
        lower, upper = _bracket(capacities, actual_capacity, "actual_capacity")
        curve_cost = _log_interp(
            actual_capacity,
            lower,
            by_capacity[lower],
            upper,
            by_capacity[upper],
        )
        service_curves.append((median_ratio, curve_cost))

    if not service_curves:
        raise ValueError(
            "actual_capacity is outside all NETL compressor service-curve ranges; "
            "extrapolation requires explicit review"
        )

    target_ratio = driver_power / actual_capacity
    ratios = [ratio for ratio, _ in service_curves]
    lower_ratio, upper_ratio = _bracket(ratios, target_ratio, "specific_power")
    cost_by_ratio = dict(service_curves)
    cost = _log_interp(
        target_ratio,
        lower_ratio,
        cost_by_ratio[lower_ratio],
        upper_ratio,
        cost_by_ratio[upper_ratio],
    )
    return {
        "cost_1998_usd": cost,
        "method": "compressor_capacity_power_loglog",
        "status": "interpolated",
        "bounds": {
            "specific_power_hp_per_acfm": [lower_ratio, upper_ratio],
            "actual_capacity_ft3_per_min": actual_capacity,
        },
    }


def _preferred_2d_axes(independent_values):
    candidates = (
        ("diameter", "number_of_trays"),
        ("diameter", "packed_height"),
    )
    for x_name, y_name in candidates:
        if x_name in independent_values and y_name in independent_values:
            return x_name, y_name
    return None


def estimate_cost(equipment_type, capacity_value=None, subtype="", variant="", independent_values=None, cost_basis="purchased", points=None):
    points = points or load_points()
    group = select_group(points, equipment_type, subtype=subtype, variant=variant)
    if independent_values:
        exact = exact_anchor_cost(group, independent_values, cost_basis=cost_basis)
        if exact is not None:
            return {"cost_1998_usd": exact, "method": "exact_appendix_b_anchor", "status": "exact"}
        if equipment_type == "Centrifugal Compressor":
            if "actual_capacity" not in independent_values or "driver_power" not in independent_values:
                raise ValueError(
                    "Centrifugal Compressor requires actual_capacity and driver_power; "
                    "flow alone is ambiguous across NETL service curves"
                )
            return compressor_capacity_power_interpolation(
                group,
                independent_values["actual_capacity"],
                independent_values["driver_power"],
                cost_basis=cost_basis,
            )
        axes = _preferred_2d_axes(independent_values)
        if axes:
            x_name, y_name = axes
            return bilinear_loglog_2d(
                group,
                x_name,
                float(independent_values[x_name]),
                y_name,
                float(independent_values[y_name]),
                cost_basis=cost_basis,
            )
    if capacity_value is None:
        raise ValueError(
            "capacity_value or supported independent_values are required; "
            "columns require diameter plus trays or packed height"
        )
    key = _cost_key(cost_basis)
    for row in group:
        if row["capacity_value"] is None or row[key] is None:
            continue
        if abs(float(row["capacity_value"]) - float(capacity_value)) <= 1e-12:
            return {
                "cost_1998_usd": float(row[key]),
                "method": "exact_appendix_b_capacity_anchor",
                "status": "exact",
            }
    return {
        "cost_1998_usd": piecewise_loglog_1d(group, float(capacity_value), cost_basis=cost_basis),
        "method": "piecewise_loglog_1d",
        "status": "interpolated",
    }
