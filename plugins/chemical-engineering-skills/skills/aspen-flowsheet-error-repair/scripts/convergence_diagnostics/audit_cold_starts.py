#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Audit declared starts, target/movement separately, and evidence bytes offline.

CLI: --input PATH --output PATH. See examples/startup_trials.json.
Artifact paths are relative to the input directory. Their bytes are SHA256
checked, never parsed as native results. Initialization labels and observations
remain caller declarations; a matching hash does not authenticate observations.
"""
from __future__ import annotations

import argparse
from decimal import localcontext
import hashlib
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
if __package__:
    from .audit_precision_trials import (InvalidInput, arithmetic_context, finite_number,
        load_input, local_path, nonempty_list, numeric, object_value, quantity,
        required_text, same_units, write_output)
else:
    from audit_precision_trials import (InvalidInput, arithmetic_context, finite_number,
        load_input, local_path, nonempty_list, numeric, object_value, quantity,
        required_text, same_units, write_output)


KINDS = ("cold", "warm", "bounded_perturbation", "exact_reopen")


def audit(data, source, input_sha256):
    if data.get("schema") != "startup-trials-v1":
        raise InvalidInput("schema must be startup-trials-v1")
    target = object_value(data.get("target"), "target")
    target_value = numeric(target.get("value"), "target.value")
    tolerance = numeric(target.get("absolute_tolerance"), "target.absolute_tolerance")
    unit = required_text(target.get("unit"), "target.unit")
    if tolerance < 0:
        raise InvalidInput("target.absolute_tolerance must be nonnegative")
    rows, protected, seen = [], [source], set()
    coverage = {kind: False for kind in KINDS}
    for case in nonempty_list(data.get("cases"), "cases"):
        case = object_value(case, "case")
        case_id = required_text(case.get("id"), "case.id")
        if case_id in seen:
            raise InvalidInput("duplicate case id")
        seen.add(case_id)
        kind = required_text(case.get("initialization_kind"), "initialization_kind")
        if kind not in KINDS:
            raise InvalidInput("unsupported initialization_kind")
        coverage[kind] = True
        observed = quantity(case.get("observed"), "observed")
        same_units([(target_value, unit), observed], "target/observed")
        manipulated = object_value(case.get("manipulated"), "manipulated")
        variable = required_text(manipulated.get("variable"), "manipulated.variable")
        initial = quantity(manipulated.get("initial"), "manipulated.initial")
        final = quantity(manipulated.get("final"), "manipulated.final")
        minimum = quantity(manipulated.get("minimum_movement"), "manipulated.minimum_movement")
        same_units([initial, final, minimum], "manipulated quantities")
        if minimum[0] < 0:
            raise InvalidInput("minimum_movement must be nonnegative")
        with localcontext() as ctx:
            ctx.prec = arithmetic_context(target_value, tolerance, observed[0], initial[0], final[0], minimum[0])
            residual = observed[0] - target_value
            movement = abs(final[0] - initial[0])
            met = abs(residual) <= tolerance
            moved = movement > minimum[0]
        artifacts = []
        for artifact in nonempty_list(case.get("artifacts"), "artifacts"):
            artifact = object_value(artifact, "artifact")
            role = required_text(artifact.get("role"), "artifact.role")
            declared = local_path(artifact.get("path"), "artifact.path")
            path = declared if declared.is_absolute() else source.parent / declared
            resolved = path.resolve(strict=True)
            local_path(resolved, "resolved artifact")
            expected = required_text(artifact.get("sha256"), "artifact.sha256")
            if re.fullmatch(r"[0-9a-fA-F]{64}", expected) is None:
                raise InvalidInput("artifact.sha256 must have 64 hexadecimal characters")
            digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
            if digest != expected.lower():
                raise InvalidInput(f"artifact SHA256 mismatch for role {role}")
            protected.extend([path, resolved])
            artifacts.append({"role": role, "path": str(declared), "sha256": digest,
                              "bytes_verified": True, "contents_interpreted": False})
        rows.append({"id": case_id, "initialization_kind": kind, "initialization_kind_verified": False,
                     "target_residual": finite_number(residual, "target residual"), "target_unit": unit,
                     "target_met": met, "manipulated_variable": variable,
                     "absolute_movement": finite_number(movement, "movement"), "movement_unit": initial[1],
                     "minimum_movement": finite_number(minimum[0], "minimum movement"),
                     "movement_exceeds_threshold": moved, "artifacts": artifacts})
    report = {"schema": "startup-trial-audit-v1", "input_sha256": input_sha256,
              "observation_authority": "caller-supplied observations, not native proof",
              "artifact_binding_note": "Hashes identify bytes only; they do not prove observations came from those bytes. native_receipt contents are not interpreted.",
              "cases": rows, "declared_initialization_coverage": coverage,
              "initialization_coverage_verified": False,
              "bounded_perturbation_with_reported_movement": any(x["initialization_kind"] == "bounded_perturbation" and x["movement_exceeds_threshold"] for x in rows),
              "target_and_movement_evaluated_separately": True,
              "native_cleanliness_evaluated": False, "strict_accepted": False}
    return report, protected


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        data, source, digest = load_input(args.input)
        report, protected = audit(data, source, digest)
        write_output(args.output, report, [args.input, *protected])
    except (ValueError, OSError, ArithmeticError, RecursionError) as exc:
        print(f"invalid_input: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
