"""Evaluate supplied F1 tray load boundaries without COM or empirical defaults.

Input curves are caller-supplied piecewise-linear models with explicit source,
units, case and geometry identity. This utility neither loads third-party neural
weights nor certifies their formulas or a tray's real hydraulic performance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

CURVES = ("weeping", "entrainment", "flooding")
SOURCES = ("operating_point", "geometry", "liquid_limits", *CURVES)
UNITS = {"m3/s": 1.0, "m3/h": 1.0 / 3600.0}


def _number(value, label, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label}: finite numeric value required")
    value = float(value)
    if value < 0 or (positive and value <= 0):
        raise ValueError(f"{label}: {'positive' if positive else 'nonnegative'} value required")
    return value


def _sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_sources(payload):
    identities = {}
    for name in SOURCES:
        source = payload.get("sources", {}).get(name)
        if not isinstance(source, dict):
            raise ValueError(f"Missing source identity: {name}")
        for field in ("path", "sha256", "locator", "status", "equipment_tag", "case_id"):
            if not isinstance(source.get(field), str) or not source[field].strip():
                raise ValueError(f"{name}: explicit {field} required")
        if source["equipment_tag"] != payload["equipment_tag"] or source["case_id"] != payload["case_id"]:
            raise ValueError(f"{name}: source belongs to another equipment/case")
        path = Path(source["path"]).resolve()
        actual = _sha(path)
        if actual != source["sha256"].casefold():
            raise ValueError(f"{name}: source hash mismatch")
        identities[name] = {**source, "path": str(path), "actual_sha256": actual,
            "verification_scope": "byte_identity_and_declared_case_only; not independent formula/source-page validation"}
    return identities


def interpolate(points, liquid):
    if liquid < points[0][0] or liquid > points[-1][0]:
        raise ValueError("Query outside supplied curve domain; extrapolation is prohibited")
    for left, right in zip(points, points[1:]):
        if liquid <= right[0]:
            weight = (liquid - left[0]) / (right[0] - left[0])
            return left[1] + weight * (right[1] - left[1])
    return points[-1][1]


def _clip_affine_nonnegative(lo, hi, x0, x1, y0, y1):
    """Intersect [lo, hi] with one affine inequality on [x0, x1]."""
    slope = (y1 - y0) / (x1 - x0)
    if slope == 0:
        return None if y0 < 0 else (lo, hi)
    root = x0 - y0 / slope
    if slope > 0:
        lo = max(lo, root)
    else:
        hi = min(hi, root)
    return (lo, hi) if lo <= hi else None


def feasible_intervals(curves, liquid_min, liquid_max, ray_slope, inclusive):
    knots = sorted({liquid_min, liquid_max, *(x for points in curves.values() for x, _ in points if liquid_min < x < liquid_max)})
    intervals = []
    for x0, x1 in zip(knots, knots[1:]):
        lo, hi = x0, x1
        for name in CURVES:
            y0 = interpolate(curves[name], x0) - ray_slope * x0
            y1 = interpolate(curves[name], x1) - ray_slope * x1
            if name == "weeping":
                y0, y1 = -y0, -y1
            if not inclusive and y0 == 0 and y1 == 0:
                lo, hi = 1.0, 0.0
                break
            clipped = _clip_affine_nonnegative(lo, hi, x0, x1, y0, y1)
            if clipped is None:
                lo, hi = 1.0, 0.0
                break
            lo, hi = clipped
        if lo > hi or (not inclusive and lo == hi):
            continue
        join_margins = [ray_slope * lo - interpolate(curves["weeping"], lo),
                        interpolate(curves["entrainment"], lo) - ray_slope * lo,
                        interpolate(curves["flooding"], lo) - ray_slope * lo]
        joins_strict_interior = all(margin > 1e-12 * max(1.0, abs(ray_slope * lo)) for margin in join_margins)
        if intervals and (inclusive or joins_strict_interior) and math.isclose(intervals[-1][1], lo, rel_tol=1e-12, abs_tol=1e-15):
            intervals[-1][1] = hi
        else:
            intervals.append([lo, hi])
    return intervals, knots


def evaluate(payload):
    if payload.get("schema_version") != "f1-load-performance-boundaries-1.0" or payload.get("tray_family") != "F1_float_valve":
        raise ValueError("Explicit F1 boundary-package schema required")
    for field in ("equipment_tag", "case_id", "geometry_identity", "applicability"):
        if not isinstance(payload.get(field), str) or not payload[field].strip():
            raise ValueError(f"Explicit {field} required")
    inclusive = payload.get("boundary_inclusive")
    if not isinstance(inclusive, bool):
        raise ValueError("boundary_inclusive must be an explicit boolean")
    unit = payload.get("flow_unit")
    if unit not in UNITS:
        raise ValueError("flow_unit must be m3/s or m3/h, on actual operating volume basis")
    if payload.get("flow_basis") != "actual_at_operating_state":
        raise ValueError("Actual volumetric flow basis required; standard volume is not interchangeable")
    if payload.get("interpolation_model") != "piecewise_linear":
        raise ValueError("Only explicit piecewise-linear boundary models are supported")
    factor = UNITS[unit]
    liquid = _number(payload["operating_point"]["liquid"], "operating liquid", positive=True) * factor
    vapor = _number(payload["operating_point"]["vapor"], "operating vapor", positive=True) * factor
    lower = _number(payload["liquid_limits"]["minimum"], "liquid minimum", positive=True) * factor
    upper = _number(payload["liquid_limits"]["maximum"], "liquid maximum", positive=True) * factor
    if lower >= upper:
        raise ValueError("Liquid limits are inverted or degenerate")
    curves = {}
    for name in CURVES:
        raw_points = payload.get("boundaries", {}).get(name)
        if not isinstance(raw_points, list) or len(raw_points) < 2:
            raise ValueError(f"{name}: at least two boundary points required")
        points = []
        for row in raw_points:
            if not isinstance(row, list) or len(row) != 2:
                raise ValueError(f"{name}: each point must be [liquid, vapor]")
            points.append([_number(row[0], name + " liquid") * factor, _number(row[1], name + " vapor") * factor])
        if any(left[0] >= right[0] for left, right in zip(points, points[1:])):
            raise ValueError(f"{name}: strictly increasing liquid coordinates required")
        if points[0][0] > min(lower, liquid) or points[-1][0] < max(upper, liquid):
            raise ValueError(f"{name}: supplied domain must cover liquid limits and operating point")
        curves[name] = points
    sources = verify_sources(payload)
    boundary_values = {name: interpolate(points, liquid) for name, points in curves.items()}
    margins = {"weeping": vapor - boundary_values["weeping"], "entrainment": boundary_values["entrainment"] - vapor,
               "flooding": boundary_values["flooding"] - vapor, "liquid_minimum": liquid - lower, "liquid_maximum": upper - liquid}
    checks = {name: value >= 0 if inclusive else value > 0 for name, value in margins.items()}
    feasible = all(checks.values())
    slope = vapor / liquid
    intervals, knots = feasible_intervals(curves, lower, upper, slope, inclusive)
    containing = next((i for i, (lo, hi) in enumerate(intervals) if lo <= liquid <= hi), None) if feasible else None
    selected = intervals[containing] if containing is not None else None
    elasticity = selected[1] / selected[0] if selected and selected[1] > selected[0] else None
    input_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    return {"schema_version": "f1-load-performance-result-1.0", "status": "PROVISIONAL_SUPPLIED_BOUNDARY_SCREENING",
        "equipment_tag": payload["equipment_tag"], "case_id": payload["case_id"], "geometry_identity": payload["geometry_identity"],
        "input_sha256": hashlib.sha256(input_bytes).hexdigest(), "implementation_sha256": _sha(Path(__file__)),
        "canonical_flow_unit": "m3/s", "flow_basis": payload["flow_basis"], "boundary_inclusive": inclusive,
        "operating_point": {"liquid": liquid, "vapor": vapor}, "boundary_values_at_operating_point": boundary_values,
        "constraint_margins_m3_s": margins, "constraint_passes": checks, "operating_point_feasible_on_supplied_boundaries": feasible,
        "violated_constraints": [name for name, passed in checks.items() if not passed],
        "feasible_ray_intervals": [{"liquid_min": lo, "liquid_max": hi, "vapor_min": slope * lo, "vapor_max": slope * hi,
            "interval_type": "inclusive_admissible_limits" if inclusive else "limiting_values_of_strict_feasible_region"} for lo, hi in intervals],
        "operating_interval_index": containing, "operating_elasticity": elasticity,
        "elasticity_definition": "ratio of maximum/minimum load on the connected supplied-model feasible interval containing the operating point",
        "plot_data": [{"liquid": x, **{name: interpolate(points, x) for name, points in curves.items()}, "operating_ray": slope*x} for x in knots],
        "liquid_limits": {"minimum": lower, "maximum": upper}, "source_identities": sources,
        "applicability": payload["applicability"], "interpolation_model": "piecewise_linear",
        "formal_engineering_acceptance": False, "neural_weights_loaded": False, "aspen_started": False,
        "notice": "Numerically exact for the supplied piecewise-linear model only. Physical correlations, curve uncertainty, F1 geometry applicability and same-equipment software/vendor validation remain separate evidence gates."}


def _new_output(path):
    path = Path(path).resolve()
    if path.exists():
        raise ValueError(f"Output already exists: {path}")
    if "source_snapshot" in {part.casefold() for part in path.parts}:
        raise ValueError("Output must not be written into an immutable source snapshot")
    if not path.parent.is_dir():
        raise ValueError("Output parent must already exist")
    return path


def plot_result(result, path):
    target = _new_output(path)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows = result["plot_data"]
    liquid = [row["liquid"] for row in rows]
    fig, axis = plt.subplots(figsize=(8, 6))
    try:
        for name in CURVES:
            axis.plot(liquid, [row[name] for row in rows], label=name)
        axis.axvline(result["liquid_limits"]["minimum"], color="grey", linestyle=":", label="liquid limits")
        axis.axvline(result["liquid_limits"]["maximum"], color="grey", linestyle=":")
        axis.plot(liquid, [row["operating_ray"] for row in rows], "k--", label="operating ray")
        point = result["operating_point"]
        axis.plot([point["liquid"]], [point["vapor"]], "ko", label="operating point")
        axis.set(xlabel="Liquid actual flow (m³/s)", ylabel="Vapor actual flow (m³/s)", title=f"{result['equipment_tag']} — supplied F1 boundaries (provisional)")
        axis.legend(); axis.grid(alpha=0.2); fig.tight_layout()
        fig.savefig(target, dpi=180)
    finally:
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--plot", type=Path)
    args = parser.parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8-sig"))
        result = evaluate(payload)
        if args.output:
            target = _new_output(args.output)
            with target.open("x", encoding="utf-8") as stream:
                json.dump(result, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        if args.plot:
            plot_result(result, args.plot)
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        parser.exit(2, f"Boundary evidence/input error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
