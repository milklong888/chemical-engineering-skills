#!/usr/bin/env python3
"""Validate the status logic of a structured macro process-design review.

This script checks completeness and non-compensation logic. It does not decide
whether the underlying chemistry or engineering evidence is true.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


HARD_GATES = (
    "objective_boundary_basis",
    "chemistry_route",
    "thermodynamics_phases",
    "conservation_component_fate",
    "flowsheet_topology_sequence",
    "energy_pressure_utilities",
    "operability_plantwide_control",
    "safety_environment_legal",
    "equipment_materials_constructability",
    "model_evidence_robustness",
)

QUALITY_AXES = (
    "product_feed_efficiency",
    "energy_pressure_quality",
    "economics",
    "simplicity_reliability",
    "operability_flexibility",
    "safety_environment",
    "constructability_maintainability",
    "evidence_maturity",
)

GATE_STATES = {"pass", "fail", "unknown"}
DECLARED_STATES = {
    "inadmissible",
    "undemonstrated",
    "feasible",
    "good",
    "preferred",
}


def nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate(review: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not nonempty_text(review.get("design_id")):
        errors.append("design_id must be a non-empty string")

    declared = review.get("declared_status")
    if declared not in DECLARED_STATES:
        errors.append(f"declared_status must be one of {sorted(DECLARED_STATES)}")

    gates = review.get("hard_gates")
    if not isinstance(gates, dict):
        errors.append("hard_gates must be an object")
        gates = {}

    statuses: dict[str, str] = {}
    for name in HARD_GATES:
        gate = gates.get(name)
        if not isinstance(gate, dict):
            errors.append(f"missing hard gate object: {name}")
            continue
        status = gate.get("status")
        statuses[name] = status
        if status not in GATE_STATES:
            errors.append(f"{name}.status must be pass, fail, or unknown")
        if not nonempty_text(gate.get("basis")):
            errors.append(f"{name}.basis must explain the decision or gap")
        evidence = gate.get("evidence")
        if status == "pass" and not (
            isinstance(evidence, list)
            and any(nonempty_text(item) for item in evidence)
        ):
            errors.append(f"{name}: pass requires at least one evidence/derivation reference")
        if status == "unknown" and not nonempty_text(gate.get("next_evidence")):
            errors.append(f"{name}: unknown requires next_evidence")

    extra_gates = sorted(set(gates) - set(HARD_GATES))
    if extra_gates:
        warnings.append(f"unrecognized hard gates retained but not scored: {extra_gates}")

    failed = sorted(name for name, status in statuses.items() if status == "fail")
    unknown = sorted(name for name, status in statuses.items() if status == "unknown")
    missing = sorted(set(HARD_GATES) - set(statuses))

    if failed:
        derived = "inadmissible"
    elif unknown or missing:
        derived = "undemonstrated"
    else:
        derived = "feasible"

    if declared in DECLARED_STATES:
        if derived == "inadmissible" and declared != "inadmissible":
            errors.append("a failed hard gate cannot be compensated by quality scores")
        elif derived == "undemonstrated" and declared != "undemonstrated":
            errors.append("a critical unknown/missing hard gate prevents feasible/good/preferred status")
        elif derived == "feasible" and declared in {"inadmissible", "undemonstrated"}:
            warnings.append("all required hard gates pass but the declared status is more conservative")

    if declared in {"good", "preferred"}:
        alternatives = review.get("alternatives")
        if not isinstance(alternatives, list) or len(alternatives) < 2:
            errors.append("good/preferred requires at least two credible alternatives on a common basis")
        else:
            for index, alternative in enumerate(alternatives):
                if not isinstance(alternative, dict):
                    errors.append(f"alternatives[{index}] must be an object")
                    continue
                if not nonempty_text(alternative.get("id")):
                    errors.append(f"alternatives[{index}].id must be non-empty")
                if not nonempty_text(alternative.get("common_basis")):
                    errors.append(f"alternatives[{index}].common_basis must be non-empty")

        if not nonempty_text(review.get("decision_rule")):
            errors.append("good/preferred requires an explicit decision_rule")
        tradeoffs = review.get("tradeoffs")
        if not isinstance(tradeoffs, list) or not any(nonempty_text(item) for item in tradeoffs):
            errors.append("good/preferred requires material tradeoffs")

        axes = review.get("quality_axes")
        if not isinstance(axes, dict):
            errors.append("good/preferred requires quality_axes")
            axes = {}
        for name in QUALITY_AXES:
            axis = axes.get(name)
            if not isinstance(axis, dict):
                errors.append(f"missing quality axis object: {name}")
                continue
            if not nonempty_text(axis.get("assessment")):
                errors.append(f"{name}.assessment must be non-empty")
            if not nonempty_text(axis.get("basis")):
                errors.append(f"{name}.basis must be non-empty")

    if declared == "preferred" and not nonempty_text(review.get("pareto_or_weighting_basis")):
        errors.append("preferred requires pareto_or_weighting_basis")

    return {
        "ok": not errors,
        "declared_status": declared,
        "derived_hard_gate_state": derived,
        "failed_gates": failed,
        "unknown_gates": unknown,
        "missing_gates": missing,
        "errors": errors,
        "warnings": warnings,
        "note": "This validates review structure/status logic, not chemical truth.",
    }


def complete_gates(status: str = "pass") -> dict[str, dict[str, Any]]:
    gates: dict[str, dict[str, Any]] = {}
    for name in HARD_GATES:
        gate: dict[str, Any] = {
            "status": status,
            "basis": f"test basis for {name}",
            "evidence": [f"D:test:{name}"],
        }
        if status == "unknown":
            gate["next_evidence"] = f"test evidence for {name}"
        gates[name] = gate
    return gates


def complete_axes() -> dict[str, dict[str, str]]:
    return {
        name: {"assessment": "test assessment", "basis": "test common basis"}
        for name in QUALITY_AXES
    }


def self_test() -> int:
    bad = {
        "design_id": "bad-noncompensation",
        "declared_status": "preferred",
        "hard_gates": complete_gates(),
        "alternatives": [
            {"id": "A", "common_basis": "same basis"},
            {"id": "B", "common_basis": "same basis"},
        ],
        "decision_rule": "test",
        "tradeoffs": ["test"],
        "quality_axes": complete_axes(),
        "pareto_or_weighting_basis": "test",
    }
    bad["hard_gates"]["safety_environment_legal"] = {
        "status": "fail",
        "basis": "test hard failure",
        "evidence": ["R:test"],
    }
    bad_result = validate(bad)
    if bad_result["ok"] or bad_result["derived_hard_gate_state"] != "inadmissible":
        print("SELF_TEST_FAIL noncompensation")
        return 1

    unknown = {
        "design_id": "unknown-gate",
        "declared_status": "undemonstrated",
        "hard_gates": complete_gates(),
    }
    unknown["hard_gates"]["thermodynamics_phases"] = {
        "status": "unknown",
        "basis": "binary data absent",
        "evidence": [],
        "next_evidence": "obtain applicable VLE/LLE data",
    }
    unknown_result = validate(unknown)
    if not unknown_result["ok"] or unknown_result["derived_hard_gate_state"] != "undemonstrated":
        print("SELF_TEST_FAIL unknown")
        return 1

    good = {
        "design_id": "good-design",
        "declared_status": "preferred",
        "hard_gates": complete_gates(),
        "alternatives": [
            {"id": "A", "common_basis": "same product/capacity/year/boundary"},
            {"id": "B", "common_basis": "same product/capacity/year/boundary"},
        ],
        "decision_rule": "Pareto screen followed by declared project priorities",
        "tradeoffs": ["A uses less high-grade heat; B has lower capital"],
        "quality_axes": complete_axes(),
        "pareto_or_weighting_basis": "no hard-gate failure; disclosed project priorities",
    }
    good_result = validate(good)
    if not good_result["ok"] or good_result["derived_hard_gate_state"] != "feasible":
        print("SELF_TEST_FAIL preferred")
        print(json.dumps(good_result, ensure_ascii=False, indent=2))
        return 1

    print("SELF_TEST_OK cases=3")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("review", nargs="?", type=Path, help="UTF-8 JSON review file")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if args.review is None:
        parser.error("provide a JSON review file or --self-test")

    try:
        review = json.loads(args.review.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 2
    if not isinstance(review, dict):
        print(json.dumps({"ok": False, "errors": ["review root must be an object"]}, ensure_ascii=False, indent=2))
        return 2

    result = validate(review)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
