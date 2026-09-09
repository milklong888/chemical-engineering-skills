from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / "references"
sys.path.insert(0, str(Path(__file__).resolve().parent))

import aspen_offline_sizing as sizing  # noqa: E402
import comparison_cost_completion as comparison  # noqa: E402
import cost_basis_adjustment as adjustment  # noqa: E402
import netl_equipment_cost_estimators as netl  # noqa: E402


def io_path(path: Path) -> Path:
    resolved = path.resolve()
    if os.name != "nt":
        return resolved
    value = str(resolved)
    if value.startswith("\\\\?\\"):
        return resolved
    if value.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + value[2:])
    return Path("\\\\?\\" + value)


def read_csv(path: Path) -> list[dict[str, str]]:
    with io_path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    target = io_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with io_path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def f(params: dict[str, Any], name: str, default: float | None = None) -> float:
    value = params.get(name, default)
    if value in (None, ""):
        raise ValueError(f"missing parameter: {name}")
    return float(value)


def cost_input(method_id: str, params: dict[str, Any]) -> tuple[str, str, str, float | None, dict[str, float], dict[str, Any]]:
    sizing_result: dict[str, Any] = {}
    subtype = str(params.get("subtype", ""))
    variant = str(params.get("variant", ""))
    independent = {key: float(value) for key, value in dict(params.get("independent_values", {})).items()}
    capacity = float(params["capacity_value"]) if params.get("capacity_value") not in (None, "") else None

    if method_id == "HX_Q_U_LMTD_NETL":
        equipment_type = str(params.get("equipment_type", "Shell and Tube Heat Exchanger"))
        if capacity is None:
            sizing_result = sizing.heat_exchanger_area_ft2(
                f(params, "duty_gcal_h"),
                f(params, "process_inlet_c"),
                f(params, "process_outlet_c"),
                f(params, "utility_inlet_c"),
                f(params, "utility_outlet_c"),
                f(params, "overall_u_kcal_h_m2_k"),
                service=str(params.get("service", "")),
                overdesign_factor=f(params, "overdesign_factor", 1.0),
            )
            capacity = sizing_result["design_area_ft2"]
    elif method_id == "PUMP_Q_H_NETL":
        equipment_type = str(params.get("equipment_type", "Centrifugal Pump"))
        inlet_pressure = f(params, "inlet_pressure_bar")
        outlet_pressure = f(params, "outlet_pressure_bar")
        if outlet_pressure <= inlet_pressure:
            raise ValueError("pump topology invalid: outlet_pressure_bar must exceed inlet_pressure_bar")
        f(params, "density_kg_m3")
        efficiency = f(params, "efficiency")
        if not 0 < efficiency <= 1:
            raise ValueError("pump efficiency must be in (0, 1]")
        if capacity is None:
            if params.get("liquid_flow_m3_h") not in (None, ""):
                capacity = f(params, "liquid_flow_m3_h") * 4.402867539
            else:
                capacity = f(params, "liquid_flow_m3_s") * sizing.M3_S_TO_US_GPM
            sizing_result = {"flow_us_gpm": capacity}
    elif method_id == "COMPRESSOR_Q_POWER_NETL":
        equipment_type = str(params.get("equipment_type", "Centrifugal Compressor"))
        independent = {
            "actual_capacity": f(params, "actual_capacity_acfm"),
            "driver_power": f(params, "driver_power_hp"),
        }
        capacity = None
        sizing_result = independent.copy()
    elif method_id == "FLASH_VESSEL_HYDRAULIC_NETL":
        equipment_type = str(params.get("equipment_type", "Horizontal Vessel"))
        capacity = capacity if capacity is not None else f(params, "volume_us_gal")
        variant = variant or str(params.get("pressure_variant", "15 psig"))
        sizing_result = {"volume_us_gal": capacity, "pressure_variant": variant}
    elif method_id == "COLUMN_HYDRAULIC_PACKAGE_NETL":
        equipment_type = str(params.get("equipment_type", "Valve Tray Column"))
        variant = variant or str(params.get("pressure_variant", "15 psig"))
        independent = {"diameter": f(params, "diameter_ft")}
        if equipment_type == "Packed Column":
            independent["packed_height"] = f(params, "packed_height_ft")
        else:
            independent["number_of_trays"] = f(params, "number_of_trays")
        capacity = None
        sizing_result = independent.copy()
    elif method_id == "PACKAGE_BOILER_NETL":
        equipment_type = str(params.get("equipment_type", "Package Steam Boiler"))
        capacity = capacity if capacity is not None else f(params, "steam_kg_h") * 2.20462262185
        sizing_result = {"steam_lb_h": capacity}
    elif method_id == "CYCLONE_SOLIDS_PACKAGE":
        raise ValueError("no approved generic cyclone/package cost method; qualify a service-matched source")
    else:
        raise ValueError(f"unsupported cost method: {method_id}")
    return equipment_type, subtype, variant, capacity, independent, sizing_result


def calculate_item(assignment: dict[str, str], input_row: dict[str, str], case: dict[str, str], points: list[dict[str, Any]]) -> dict[str, Any]:
    equipment_id = assignment["equipment_item_id"]
    method_id = assignment["method_id"]
    result: dict[str, Any] = {
        "case_id": case["case_id"],
        "template_id": case.get("template_id", assignment.get("template_id", "")),
        "chain_id": case.get("chain_id", ""),
        "stage": case.get("stage", ""),
        "equipment_item_id": equipment_id,
        "block_id": assignment.get("block_id", equipment_id),
        "aspen_block_type": assignment.get("aspen_block_type", ""),
        "physical_equipment": assignment.get("physical_equipment", ""),
        "method_id": method_id,
        "source_ids": assignment.get("source_ids", ""),
        "candidate_purchased_cost_base_usd": "",
        "candidate_purchased_cost_target_usd": "",
        "utility_cost_usd_h": "",
        "utility_cost_usd_y": "",
        "selected_after_review": input_row.get("selected_after_review", "no"),
        "selection_reason": input_row.get("selection_reason", ""),
        "status": "",
        "sizing_json": "",
        "cost_detail_json": "",
        "error": "",
        "note": input_row.get("note", ""),
    }
    if "excluded" in assignment.get("scope_class", ""):
        result["status"] = "excluded_not_zero"
        return result
    try:
        params = json.loads(input_row.get("parameters_json") or "{}")
        if input_row.get("method_id") and input_row["method_id"] != method_id:
            raise ValueError("input method_id differs from reviewed assignment")
        if method_id == "UTILITY_OPEX":
            quantity = f(params, "utility_quantity")
            price = f(params, "configured_price")
            hours = f(params, "operating_hours_per_year", float(case.get("operating_hours_per_year") or 0))
            result["utility_cost_usd_h"] = quantity * price
            result["utility_cost_usd_y"] = quantity * price * hours
            result["status"] = "utility_opex_calculated_separate"
            return result

        equipment_type, subtype, variant, capacity, independent, sizing_result = cost_input(method_id, params)
        estimate = netl.estimate_cost(
            equipment_type,
            capacity_value=capacity,
            subtype=subtype,
            variant=variant,
            independent_values=independent or None,
            cost_basis="purchased",
            points=points,
        )
        base_cost = float(estimate["cost_1998_usd"])
        result["candidate_purchased_cost_base_usd"] = base_cost
        result["sizing_json"] = json.dumps(sizing_result, sort_keys=True)
        result["cost_detail_json"] = json.dumps(estimate, sort_keys=True)

        base_index = case.get("base_cost_index", "")
        target_index = case.get("target_cost_index", "")
        provenance = [case.get(name, "") for name in ("index_name", "base_period", "target_period", "index_source")]
        if not base_index or not target_index or not all(str(value).strip() for value in provenance):
            result["status"] = "base_cost_only_target_basis_unresolved"
            return result
        adjusted = adjustment.adjust_purchased_equipment_cost(
            base_cost,
            base_cost_index=float(base_index),
            target_cost_index=float(target_index),
            index_name=case["index_name"],
            base_period=case["base_period"],
            target_period=case["target_period"],
            index_source=case["index_source"],
            material_factor=f(params, "material_factor", 1.0),
            pressure_factor=f(params, "pressure_factor", 1.0),
            design_factor=f(params, "design_factor", 1.0),
            quantity=int(f(params, "quantity", 1.0)),
        )
        result["candidate_purchased_cost_target_usd"] = adjusted["adjusted_total_purchased_equipment_cost_usd"]
        result["cost_detail_json"] = json.dumps({"source_estimate": estimate, "adjustment": adjusted}, sort_keys=True)
        result["status"] = "calculated_candidate"
    except Exception as exc:
        result["status"] = "unresolved"
        result["error"] = str(exc)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run strict and comparison equipment-cost layers.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--allow-draft", action="store_true", help="Deprecated compatibility flag; comparison output is always enabled.")
    parser.add_argument("--strict-engineering", action="store_true", help="Return nonzero unless every strict engineering row is reviewed and numeric.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = subprocess.run(
        [sys.executable, str(Path(__file__).with_name("audit_generated_method.py"))],
        check=False,
        capture_output=True,
        text=True,
    )
    audit_path = ROOT / "method_audit.json"
    audit_report = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.exists() else {}
    method_ready = audit_report.get("strict_status") == "pass" or audit.returncode == 0
    comparison_contract_ready = audit_report.get("comparison_contract_status", "pass" if audit.returncode == 0 else "fail") == "pass"
    if not comparison_contract_ready:
        if audit.stdout:
            print(audit.stdout, end="")
        if audit.stderr:
            print(audit.stderr, file=sys.stderr, end="")
        return audit.returncode or 1

    assignments = read_csv(REFS / "equipment-method-assignment.csv")
    points = netl.load_points(REFS / "netl-equipment-cost-points.csv")
    comparison_contract = comparison.load_contract(REFS)
    cases = [row for row in read_csv(args.manifest.resolve()) if truthy(row.get("enabled", "yes"))]
    batch_rows: list[dict[str, Any]] = []
    output_root = io_path(args.out_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    fields = [
        "case_id", "template_id", "chain_id", "stage", "equipment_item_id",
        "block_id", "aspen_block_type", "physical_equipment", "method_id",
        "source_ids", "candidate_purchased_cost_base_usd",
        "candidate_purchased_cost_target_usd", "utility_cost_usd_h",
        "utility_cost_usd_y", "selected_after_review", "selection_reason",
        "status", "sizing_json", "cost_detail_json", "error", "note",
        *comparison.COMPARISON_FIELDS,
    ]
    for case in cases:
        case_id = case["case_id"]
        case_dir = output_root / re.sub(r"[^A-Za-z0-9_.-]+", "_", case_id)
        case_dir.mkdir(parents=True, exist_ok=True)
        blocked: list[str] = []
        bkp_text = case.get("bkp_path", "").strip()
        if bkp_text:
            bkp = Path(bkp_text)
            if not io_path(bkp).exists():
                blocked.append("bkp_missing")
            elif case.get("expected_bkp_sha256", "").strip() and sha256(bkp) != case["expected_bkp_sha256"].strip().upper():
                blocked.append("bkp_sha256_mismatch")
        input_path = Path(case["equipment_input_csv"])
        if not io_path(input_path).exists():
            blocked.append("equipment_input_csv_missing")
            inputs: dict[str, dict[str, str]] = {}
        else:
            inputs = {row["equipment_item_id"]: row for row in read_csv(input_path)}

        item_rows: list[dict[str, Any]] = []
        comparison_errors: list[str] = []
        for assignment in assignments:
            input_row = inputs.get(assignment["equipment_item_id"], {})
            item = calculate_item(assignment, input_row, case, points)
            try:
                params = json.loads(input_row.get("parameters_json") or "{}")
                if not isinstance(params, dict):
                    raise ValueError("parameters_json must contain one JSON object")
            except Exception:
                params = {}
            try:
                item.update(comparison.complete_comparison_cost(item, assignment, params, case, comparison_contract))
            except Exception as exc:
                comparison_errors.append(f"{item['equipment_item_id']}:{exc}")
            item_rows.append(item)
            if assignment.get("scope_class") == "purchased_equipment_candidate":
                if item["status"] != "calculated_candidate":
                    blocked.append(f"{item['equipment_item_id']}:{item['status']}")
                if not truthy(item["selected_after_review"]):
                    blocked.append(f"{item['equipment_item_id']}:not_selected_after_review")

        write_csv(case_dir / "equipment_cost_candidates.csv", item_rows, fields)
        write_csv(case_dir / "comparison_equipment_cost_inventory.csv", item_rows, fields)
        selected_total = ""
        if method_ready and not blocked:
            selected_total = sum(float(row["candidate_purchased_cost_target_usd"]) for row in item_rows if row["candidate_purchased_cost_target_usd"] != "")
        comparison_complete = not comparison_errors and all(row.get("comparison_cost_usd", "") != "" for row in item_rows)
        if comparison_complete:
            for row in item_rows:
                central = float(row["comparison_cost_usd"])
                low = float(row["comparison_cost_low_usd"])
                high = float(row["comparison_cost_high_usd"])
                if not (0 <= low <= central <= high):
                    comparison_errors.append(f"{row['equipment_item_id']}:invalid_interval")
                if row.get("structural_zero") != "yes" and central <= 0:
                    comparison_errors.append(f"{row['equipment_item_id']}:nonstructural_cost_not_positive")
                if not str(row.get("comparison_source_id", "")).strip():
                    comparison_errors.append(f"{row['equipment_item_id']}:comparison_source_missing")
            comparison_complete = not comparison_errors
        comparison_total = sum(float(row["comparison_cost_usd"]) for row in item_rows) if comparison_complete else ""
        comparison_low = sum(float(row["comparison_cost_low_usd"]) for row in item_rows) if comparison_complete else ""
        comparison_high = sum(float(row["comparison_cost_high_usd"]) for row in item_rows) if comparison_complete else ""
        fallback_cost = sum(
            float(row["comparison_cost_usd"])
            for row in item_rows
            if comparison_complete and row.get("comparison_generation_tier") in {"C", "D", "E"}
        )
        case_audit = {
            "case_id": case_id,
            "method_ready": method_ready,
            "strict_status": "selected_total_available" if selected_total != "" else "blocked",
            "comparison_status": "pass" if comparison_complete else "fail",
            "selected_purchased_equipment_total_usd": selected_total,
            "comparison_purchased_equipment_total_usd": comparison_total,
            "comparison_purchased_equipment_low_usd": comparison_low,
            "comparison_purchased_equipment_high_usd": comparison_high,
            "comparison_fallback_share": fallback_cost / comparison_total if comparison_complete and comparison_total else 0.0,
            "blocked_reasons": sorted(set(blocked)),
            "comparison_errors": sorted(set(comparison_errors)),
            "candidate_count": sum(row["status"] == "calculated_candidate" for row in item_rows),
            "unresolved_count": sum(row["status"] == "unresolved" for row in item_rows),
            "comparison_item_count": len(item_rows),
            "comparison_nonnull_count": sum(row.get("comparison_cost_usd", "") != "" for row in item_rows),
        }
        (case_dir / "case_audit.json").write_text(json.dumps(case_audit, ensure_ascii=False, indent=2), encoding="utf-8")
        batch_rows.append(case_audit)

    write_csv(output_root / "batch_summary.csv", batch_rows, [
        "case_id", "method_ready", "strict_status", "comparison_status",
        "selected_purchased_equipment_total_usd", "comparison_purchased_equipment_total_usd",
        "comparison_purchased_equipment_low_usd", "comparison_purchased_equipment_high_usd",
        "comparison_fallback_share", "blocked_reasons", "comparison_errors",
        "candidate_count", "unresolved_count", "comparison_item_count", "comparison_nonnull_count",
    ])
    comparison_pass = bool(batch_rows) and all(row["comparison_status"] == "pass" for row in batch_rows)
    strict_pass = method_ready and bool(batch_rows) and all(row["strict_status"] == "selected_total_available" for row in batch_rows)
    batch_audit = {
        "status": "pass" if comparison_pass and (strict_pass or not args.strict_engineering) else "fail",
        "method_ready": method_ready,
        "comparison_contract_ready": comparison_contract_ready,
        "strict_status": "pass" if strict_pass else "blocked",
        "comparison_status": "pass" if comparison_pass else "fail",
        "strict_engineering_requested": args.strict_engineering,
        "case_count": len(batch_rows),
        "selected_case_count": sum(row["strict_status"] == "selected_total_available" for row in batch_rows),
        "comparison_complete_case_count": sum(row["comparison_status"] == "pass" for row in batch_rows),
    }
    (output_root / "batch_audit.json").write_text(json.dumps(batch_audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(batch_audit, ensure_ascii=False, indent=2))
    return 0 if batch_audit["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
