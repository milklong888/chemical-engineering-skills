from __future__ import annotations

import csv
import argparse
import json
import importlib.util
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def csv_count(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the original cost-method profile against user-provided source CSVs; no data are bundled.")
    parser.add_argument("--data-dir", type=Path, help="Reviewed original-profile cost CSV directory.")
    args = parser.parse_args()
    data_dir = args.data_dir.expanduser().resolve() if args.data_dir else None
    required = ["netl-equipment-cost-points.csv", "method-library.csv", "replacement-cost-library.csv",
                "comparison-service-replacement-library.csv", "comparison-cost-fallback-policy.csv",
                "authoritative-source-catalog.csv", "project-equipment-method-matrix.csv"]
    missing = [name for name in required if data_dir is None or not (data_dir / name).is_file() or (data_dir / name).stat().st_size == 0]
    if missing:
        print(json.dumps({"status": "dependency_unavailable", "required_argument": "--data-dir",
                          "missing_files": missing, "outputs_created": False, "tests_executed": False}, ensure_ascii=False))
        return 2
    inventory = load_module("inventory_flowsheet_self_test", ROOT / "scripts" / "inventory_flowsheet.py")
    assert inventory.classify("RPLUG")["scope_class"] == "reactor_excluded"
    assert inventory.classify("RADFRAC")["method_id"] == "COLUMN_HYDRAULIC_PACKAGE_NETL"
    assert inventory.classify("ROTARY")["method_id"] == "METHOD_GAP"
    cyclone = inventory.classify("CYCLONE")
    assert cyclone["method_id"] == "CYCLONE_SOLIDS_PACKAGE"
    assert cyclone["source_ids"] == ""

    estimator = load_module(
        "netl_equipment_cost_estimators_self_test",
        ROOT / "assets" / "project-skill-template" / "netl_equipment_cost_estimators.py",
    )
    points = estimator.load_points(data_dir / "netl-equipment-cost-points.csv")
    assert len(points) == 664
    exact = estimator.estimate_cost("Shell and Tube Heat Exchanger", capacity_value=100, points=points)
    assert exact["status"] == "exact"
    assert math.isclose(float(exact["cost_1998_usd"]), 13200.0, rel_tol=0, abs_tol=0.01)
    try:
        estimator.estimate_cost("Shell and Tube Heat Exchanger", capacity_value=50, points=points)
    except ValueError as exc:
        assert "outside" in str(exc)
    else:
        raise AssertionError("Out-of-range NETL cost request did not fail")

    comparison = load_module(
        "comparison_cost_completion_self_test",
        ROOT / "assets" / "project-skill-template" / "comparison_cost_completion.py",
    )
    contract = comparison.load_contract(data_dir)
    case = {"target_cost_index": "816"}
    structural = comparison.complete_comparison_cost(
        {},
        {"method_id": "LOGICAL_OR_REACTOR_EXCLUSION", "scope_class": "reactor_excluded"},
        {},
        case,
        contract,
    )
    assert structural["comparison_cost_usd"] == 0
    assert structural["structural_zero"] == "yes"
    letdown = comparison.complete_comparison_cost(
        {},
        {"method_id": "PUMP_Q_H_NETL", "scope_class": "purchased_equipment_candidate"},
        {"inlet_pressure_bar": 10, "outlet_pressure_bar": 5},
        case,
        contract,
    )
    assert letdown["comparison_rule_id"] == "IF_PUMP_IS_LETDOWN"
    assert letdown["comparison_cost_usd"] == 0
    fallback = comparison.complete_comparison_cost(
        {},
        {"method_id": "METHOD_GAP", "scope_class": "physical_scope_unresolved"},
        {},
        case,
        contract,
    )
    assert fallback["comparison_cost_usd"] > 0
    assert fallback["comparison_rule_id"] == "IF_UNKNOWN_PHYSICAL"
    numeric = comparison.complete_comparison_cost(
        {
            "candidate_purchased_cost_target_usd": 12345,
            "selected_after_review": "yes",
            "source_ids": "TEST_SOURCE",
            "method_id": "HX_Q_U_LMTD_NETL",
        },
        {"method_id": "HX_Q_U_LMTD_NETL", "scope_class": "purchased_equipment_candidate"},
        {},
        case,
        contract,
    )
    assert numeric["comparison_cost_usd"] == 12345
    assert numeric["comparison_rule_id"] == "IF_REVIEWED_NUMERIC"

    runner = load_module(
        "run_recipe_batch_self_test",
        ROOT / "assets" / "project-skill-template" / "run_recipe_batch.py",
    )
    try:
        runner.cost_input(
            "PUMP_Q_H_NETL",
            {
                "liquid_flow_m3_h": 10,
                "inlet_pressure_bar": 10,
                "outlet_pressure_bar": 5,
                "density_kg_m3": 1000,
                "efficiency": 0.75,
            },
        )
    except ValueError as exc:
        assert "topology invalid" in str(exc)
    else:
        raise AssertionError("Negative-head pump was accepted as a strict engineering candidate")

    assert csv_count(data_dir / "method-library.csv") == 9
    assert csv_count(data_dir / "replacement-cost-library.csv") >= 8
    assert csv_count(data_dir / "comparison-cost-fallback-policy.csv") == 9
    assert csv_count(data_dir / "authoritative-source-catalog.csv") >= 24
    assert csv_count(data_dir / "project-equipment-method-matrix.csv") >= 30
    print("aspen-flowsheet-cost-skill-builder self-test: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
