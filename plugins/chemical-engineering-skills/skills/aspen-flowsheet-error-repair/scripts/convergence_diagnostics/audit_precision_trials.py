#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Audit caller-supplied precision observations; no solver, defaults or diagnosis.

CLI: --input PATH --output PATH. See examples/precision_trials.json.
Adjacent inner criteria are comparable only when variable, definition, criterion
and unit all match exactly. Relative criteria require the explicit unit "1".
No comparison is made between an inner criterion and an outer product tolerance.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile


class InvalidInput(ValueError):
    """Invalid or unbound caller observations."""


def required_text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise InvalidInput(f"{label}: a nonempty string is required")
    return value


def object_value(value, label):
    if not isinstance(value, dict):
        raise InvalidInput(f"{label}: an object is required")
    return value


def nonempty_list(value, label):
    if not isinstance(value, list) or not value:
        raise InvalidInput(f"{label}: a nonempty array is required")
    return value


def numeric(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
        raise InvalidInput(f"{label}: a finite JSON number is required")
    result = Decimal(value)
    finite_number(result, label)
    return result


def finite_number(value, label):
    try:
        rendered = float(value)
    except (OverflowError, ValueError) as exc:
        raise InvalidInput(f"{label}: numeric overflow") from exc
    if not value.is_finite() or not math.isfinite(rendered):
        raise InvalidInput(f"{label}: non-finite number or numeric overflow")
    if value and rendered == 0:
        raise InvalidInput(f"{label}: numeric underflow")
    return rendered


def quantity(value, label):
    obj = object_value(value, label)
    return numeric(obj.get("value"), label + ".value"), required_text(obj.get("unit"), label + ".unit")


def same_units(quantities, label):
    if len({unit for _, unit in quantities}) != 1:
        raise InvalidInput(f"{label}: units must match exactly; conversion is not performed")


def arithmetic_context(*values):
    # Preserve decimal input significance, including cancellation near a target.
    high = max(v.adjusted() for v in values)
    low = min(v.as_tuple().exponent for v in values)
    return max(50, high - low + 20, *(len(v.as_tuple().digits) + 20 for v in values))


def local_path(value, label):
    value = required_text(str(value) if isinstance(value, Path) else value, label)
    if value.startswith(("\\\\", "//")) or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://", value):
        raise InvalidInput(f"{label}: only local filesystem paths are supported")
    return Path(value)


def load_input(path):
    source = local_path(path, "input").resolve(strict=True)
    local_path(source, "resolved input")
    raw = source.read_bytes()

    def pairs(items):
        obj = {}
        for key, value in items:
            if key in obj:
                raise InvalidInput(f"duplicate JSON key: {key}")
            obj[key] = value
        return obj

    def constant(token):
        raise InvalidInput(f"invalid JSON numeric constant: {token}")

    data = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=pairs,
                      parse_float=Decimal, parse_constant=constant)

    def check(value):
        if isinstance(value, (Decimal, int)) and not isinstance(value, bool):
            numeric(value, "JSON number")
        elif isinstance(value, dict):
            for child in value.values():
                check(child)
        elif isinstance(value, list):
            for child in value:
                check(child)
    check(data)
    return object_value(data, "input"), source, hashlib.sha256(raw).hexdigest()


def guard_output(output, protected):
    resolved = local_path(output, "output").resolve(strict=False)
    local_path(resolved, "resolved output")
    if resolved.exists() and not resolved.is_file():
        raise InvalidInput("output must be a file")
    for path in protected:
        path = Path(path).resolve(strict=False)
        if resolved == path or resolved in path.parents:
            raise InvalidInput("output would overwrite input, code or evidence")
        if resolved.exists() and path.exists() and os.path.samefile(resolved, path):
            raise InvalidInput("output aliases input, code or evidence")
    if not resolved.parent.is_dir():
        raise InvalidInput("output parent directory must already exist")
    return resolved


def write_output(output, payload, protected):
    protected = [*protected, Path(__file__), Path(__file__).with_name("audit_cold_starts.py")]
    destination = guard_output(output, protected)
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    descriptor, temporary = tempfile.mkstemp(prefix=".trial-audit-", suffix=".tmp", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        # Resolve aliases again immediately before the atomic replacement.
        if guard_output(output, protected) != destination:
            raise InvalidInput("output path changed during write")
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def audit(data, input_sha256):
    if data.get("schema") != "precision-trials-v1":
        raise InvalidInput("schema must be precision-trials-v1")
    rows, criteria, seen = [], [], set()
    for item in nonempty_list(data.get("trials"), "trials"):
        item = object_value(item, "trial")
        trial_id = required_text(item.get("id"), "trial.id")
        if trial_id in seen:
            raise InvalidInput("duplicate trial id")
        seen.add(trial_id)
        outer = object_value(item.get("outer"), "outer")
        variable = required_text(outer.get("variable"), "outer.variable")
        definition = required_text(outer.get("definition"), "outer.definition")
        target = quantity(outer.get("target"), "outer.target")
        tolerance = quantity(outer.get("absolute_tolerance"), "outer.absolute_tolerance")
        observed = quantity(outer.get("observed"), "outer.observed")
        same_units([target, tolerance, observed], "outer")
        if tolerance[0] < 0:
            raise InvalidInput("outer.absolute_tolerance must be nonnegative")
        inner = object_value(item.get("inner"), "inner")
        criterion = {
            "variable": required_text(inner.get("variable"), "inner.variable"),
            "definition": required_text(inner.get("definition"), "inner.definition"),
            "criterion": required_text(inner.get("criterion"), "inner.criterion"),
            "unit": required_text(inner.get("unit"), "inner.unit"),
        }
        if criterion["criterion"] not in {"relative", "absolute"}:
            raise InvalidInput("inner.criterion must be relative or absolute")
        if criterion["criterion"] == "relative" and criterion["unit"] != "1":
            raise InvalidInput("relative inner criteria require unit 1")
        inner_tolerance = numeric(inner.get("tolerance"), "inner.tolerance")
        if inner_tolerance <= 0:
            raise InvalidInput("inner.tolerance must be positive")
        with localcontext() as ctx:
            ctx.prec = arithmetic_context(target[0], tolerance[0], observed[0])
            residual = observed[0] - target[0]
            relative_scale = tolerance[0] / abs(target[0]) if target[0] else None
            met = abs(residual) <= tolerance[0]
        rows.append({"id": trial_id, "outer_variable": variable, "outer_definition": definition,
                     "outer_unit": target[1], "outer_residual": finite_number(residual, "outer residual"),
                     "outer_target_met": met,
                     "outer_relative_tolerance_scale": finite_number(relative_scale, "relative scale") if relative_scale is not None else None,
                     "relative_scale_note": "Descriptive abs_tol/abs(target) only; undefined at zero target; never compared to the inner criterion.",
                     "inner": {**criterion, "tolerance": finite_number(inner_tolerance, "inner tolerance")}})
        criteria.append((trial_id, criterion, inner_tolerance))
    comparisons = []
    for previous, current in zip(criteria, criteria[1:]):
        differences = [k for k in previous[1] if previous[1][k] != current[1][k]]
        change = "not_comparable"
        if not differences:
            change = "tightened" if current[2] < previous[2] else "loosened" if current[2] > previous[2] else "unchanged"
        comparisons.append({"from_trial": previous[0], "to_trial": current[0], "comparable": not differences,
                            "change": change, "different_fields": differences})
    return {"schema": "precision-trial-audit-v1", "input_sha256": input_sha256,
            "observation_authority": "caller-supplied observations, not native proof",
            "trials": rows, "inner_comparisons": comparisons,
            "comparison_scope": "adjacent trials; exact criterion identity only",
            "inner_outer_tolerances_compared": False, "root_cause_evaluated": False,
            "recommended_tolerance": None, "native_cleanliness_evaluated": False, "strict_accepted": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        data, source, digest = load_input(args.input)
        write_output(args.output, audit(data, digest), [args.input, source])
    except (ValueError, OSError, ArithmeticError, RecursionError) as exc:
        print(f"invalid_input: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
