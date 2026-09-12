from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / "references"
sys.path.insert(0, str(Path(__file__).resolve().parent))

import netl_equipment_cost_estimators as netl  # noqa: E402
from cost_evidence_guard import EXCLUDED_SCOPES, audit_sources, audit_procurement, audit_equipment_coverage, audit_input_contract  # noqa: E402


APPROVED_SOURCES = {"approved", "approved_project_method"}
REVIEWED_MAPPINGS = {"reviewed", "rule_fixed"}


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


def read_csv(name: str) -> list[dict[str, str]]:
    with io_path(REFS / name).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with io_path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def main() -> int:
    issues: list[dict[str, object]] = []
    comparison_issues: list[dict[str, object]] = []
    assignments = read_csv("equipment-method-assignment.csv")
    equipment = read_csv("equipment-inventory.csv")
    methods = {row["method_id"] for row in read_csv("method-library.csv")}
    sources = {row["source_id"]: row for row in read_csv("source-evidence-ledger.csv")}
    requests = read_csv("source-request-register.csv")
    extra_sources = []
    point_source_issues = []
    for index, row in enumerate(read_csv("netl-equipment-cost-points.csv"), start=2):
        ids = [part.strip() for part in (row.get("source_id") or "").split(";") if part.strip()]
        if not ids:
            point_source_issues.append({"type": "cost_point_source_missing", "row": index})
        extra_sources.extend(ids)
    for filename in ("replacement-cost-library.csv", "comparison-service-replacement-library.csv"):
        extra_sources.extend(row.get("source_id", "").strip() for row in read_csv(filename)
                             if row.get("source_id", "").strip())
    source_issues = point_source_issues + audit_sources(assignments, REFS / "source-evidence-ledger.csv", extra_sources)
    procurement_issues = audit_procurement(assignments)
    coverage_issues = audit_equipment_coverage(equipment, assignments)
    input_issues = audit_input_contract(equipment, assignments)
    issues.extend(source_issues)
    issues.extend(procurement_issues)
    issues.extend(coverage_issues)
    issues.extend(input_issues)

    for row in assignments:
        equipment_id = row["equipment_item_id"]
        if row.get("mapping_status") not in REVIEWED_MAPPINGS:
            issues.append({"type": "mapping_not_reviewed", "equipment_item_id": equipment_id, "status": row.get("mapping_status")})
        method_id = row.get("method_id", "")
        if method_id not in methods:
            issues.append({"type": "unknown_method", "equipment_item_id": equipment_id, "method_id": method_id})
        if row.get("scope_class", "") in EXCLUDED_SCOPES:
            continue
        source_ids = [item.strip() for item in row.get("source_ids", "").split(";") if item.strip()]
        if not source_ids:
            issues.append({"type": "source_missing", "equipment_item_id": equipment_id})
        for source_id in source_ids:
            source = sources.get(source_id)
            if not source:
                issues.append({"type": "source_not_registered", "equipment_item_id": equipment_id, "source_id": source_id})
                continue
            if source.get("review_status", "").strip().lower() not in APPROVED_SOURCES:
                issues.append({"type": "source_not_approved", "equipment_item_id": equipment_id, "source_id": source_id})

    for row in requests:
        if row.get("status", "").strip().lower() not in {"resolved", "closed", "not_applicable"}:
            issues.append({"type": "open_source_or_mapping_request", "gap_id": row.get("gap_id"), "block_id": row.get("block_id")})

    anchor_failures = []
    try:
        points = netl.load_points(REFS / "netl-equipment-cost-points.csv")
        for row in points:
            cost = row.get("purchased_equipment_cost_1998_usd")
            values = row.get("independent_values") or {}
            if cost is None or not values:
                continue
            group = netl.select_group(points, row["equipment_type"], row["subtype"], row["variant"])
            reproduced = netl.exact_anchor_cost(group, values, cost_basis="purchased")
            if reproduced is None or abs(float(reproduced) - float(cost)) > 1e-7:
                anchor_failures.append({"equipment_type": row["equipment_type"], "row_index": row.get("row_index")})
                if len(anchor_failures) >= 20:
                    break
    except Exception as exc:  # deterministic audit must preserve the exact error
        anchor_failures.append({"error": str(exc)})
    if anchor_failures:
        issues.append({"type": "source_anchor_reproduction_failed", "detail": anchor_failures})

    required_rules = {
        "IF_STRUCTURAL_ZERO",
        "IF_PUMP_IS_LETDOWN",
        "IF_REVIEWED_NUMERIC",
        "IF_NUMERIC_CANDIDATE",
        "IF_METHOD_PROXY_AVAILABLE",
        "IF_CYCLONE_PROXY_AVAILABLE",
        "IF_CYCLONE_NO_PROXY",
        "IF_METHOD_NO_PROXY",
        "IF_UNKNOWN_PHYSICAL",
    }
    try:
        policy_rows = read_csv("comparison-cost-fallback-policy.csv")
        policy = {row["rule_id"]: row for row in policy_rows}
        missing_rules = sorted(required_rules - set(policy))
        if missing_rules:
            comparison_issues.append({"type": "comparison_policy_rules_missing", "rule_ids": missing_rules})
        priorities = []
        for row in policy_rows:
            priorities.append(int(row["priority"]))
            low = float(row["low_factor"])
            high = float(row["high_factor"])
            structural_rule = row.get("rule_id") in {"IF_STRUCTURAL_ZERO", "IF_PUMP_IS_LETDOWN"}
            invalid_interval = low < 0 or low > high
            if structural_rule:
                invalid_interval = invalid_interval or low != 0 or high != 0
            else:
                invalid_interval = invalid_interval or low > 1 or high < 1
            if invalid_interval:
                comparison_issues.append({"type": "comparison_policy_interval_invalid", "rule_id": row.get("rule_id")})
        if len(priorities) != len(set(priorities)) or priorities != sorted(priorities):
            comparison_issues.append({"type": "comparison_policy_priority_invalid"})
    except Exception as exc:
        comparison_issues.append({"type": "comparison_policy_unreadable", "error": str(exc)})

    try:
        replacements = {row["method_id"]: row for row in read_csv("replacement-cost-library.csv")}
        required_methods = methods - {"LOGICAL_OR_REACTOR_EXCLUSION", "UTILITY_OPEX"}
        missing_methods = sorted(required_methods - set(replacements))
        if missing_methods:
            comparison_issues.append({"type": "comparison_method_replacement_missing", "method_ids": missing_methods})
        if "*" not in replacements:
            comparison_issues.append({"type": "comparison_universal_replacement_missing"})
        for method_id, row in replacements.items():
            try:
                cost = float(row["reference_cost_usd_at_index"])
                index = float(row["reference_cost_index"])
                exponent = float(row["scaling_exponent"])
                if cost <= 0 or index <= 0 or exponent <= 0:
                    raise ValueError("nonpositive replacement parameter")
                if not row.get("source_id", "").strip() or not row.get("source_locator", "").strip():
                    raise ValueError("source or locator missing")
            except Exception as exc:
                comparison_issues.append({"type": "comparison_method_replacement_invalid", "method_id": method_id, "error": str(exc)})
    except Exception as exc:
        comparison_issues.append({"type": "comparison_method_library_unreadable", "error": str(exc)})

    try:
        for row in read_csv("comparison-service-replacement-library.csv"):
            if not row.get("service", "").strip() or not row.get("method_id", "").strip():
                raise ValueError("service or method_id missing")
            if float(row["reference_cost_usd_at_index"]) <= 0 or float(row["reference_cost_index"]) <= 0:
                raise ValueError("nonpositive service replacement parameter")
            if not row.get("source_id", "").strip() or not row.get("source_locator", "").strip():
                raise ValueError("service source or locator missing")
    except Exception as exc:
        comparison_issues.append({"type": "comparison_service_library_invalid", "error": str(exc)})

    report = {
        "status": "pass" if not issues and not comparison_issues else "fail",
        "strict_status": "pass" if not issues else "fail",
        "comparison_contract_status": "pass" if not comparison_issues else "fail",
        "source_identity_status": "pass" if not source_issues else "fail",
        "procurement_boundary_status": "pass" if not procurement_issues else "fail",
        "equipment_coverage_status": "pass" if not coverage_issues else "fail",
        "input_contract_status": "pass" if not input_issues else "fail",
        "input_contract_issues": input_issues,
        "equipment_coverage_issues": coverage_issues,
        "equipment_count": len(equipment),
        "assignment_count": len(assignments),
        "method_count": len(methods),
        "source_count": len(sources),
        "issue_count": len(issues) + len(comparison_issues),
        "strict_issue_count": len(issues),
        "comparison_contract_issue_count": len(comparison_issues),
        "issues": issues,
        "comparison_contract_issues": comparison_issues,
    }
    output = ROOT / "method_audit.json"
    io_path(output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not issues and not comparison_issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
