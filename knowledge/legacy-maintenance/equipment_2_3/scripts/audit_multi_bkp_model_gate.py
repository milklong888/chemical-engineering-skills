from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any


SCHEMA = "equipment-design-multi-bkp-model-gate-v3"
TERMINAL_SELECTION_STATUSES = {
    "EXPLICIT_TERMINAL_TYPE_SELECTED",
    "CONDITIONED_TERMINAL_TYPE_SELECTED",
    "DEFAULTED_TERMINAL_TYPE_SELECTED",
}
UNRESOLVED_TYPE_MARKERS = ("待", "或", "其他", "候选")


def hard_sanity_issue(field: str, value: Any) -> dict[str, Any] | None:
    """Detect only impossible/sentinel-scale values, never ordinary design limits."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number):
        return {"field": field, "value": value, "reason": "NON_FINITE"}
    name = re.sub(r"[^a-z0-9_]+", "", str(field).casefold())
    lower: float | None = None
    upper: float | None = None
    if name.endswith("_m3_h") or name.endswith("_kg_h"):
        lower, upper = 0.0, 1.0e15
    elif name.endswith("_kw"):
        lower, upper = -1.0e12, 1.0e12
    elif name.endswith("_m2"):
        lower, upper = 0.0, 1.0e12
    elif name.endswith("_mm"):
        lower, upper = 0.0, 1.0e9
    if lower is None or upper is None or lower <= number <= upper:
        return None
    return {
        "field": field,
        "value": number,
        "hard_min": lower,
        "hard_max": upper,
        "reason": "OUTSIDE_HARD_SANITY_RANGE",
    }


def equipment_hard_sanity_issues(
    canonical: dict[str, Any],
    match: dict[str, Any],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for field, value in canonical.items():
        issue = hard_sanity_issue(str(field), value)
        if issue:
            issues.append({"location": "canonical_match_input", **issue})
    derived = match.get("derived_parameters") if isinstance(match.get("derived_parameters"), dict) else {}
    for field, value in derived.items():
        issue = hard_sanity_issue(str(field), value)
        if issue:
            issues.append({"location": "derived_parameters", **issue})
    for calculation in match.get("calculations", []):
        if not isinstance(calculation, dict):
            continue
        field = str(calculation.get("target_field") or calculation.get("calculation_id") or "")
        issue = hard_sanity_issue(field, calculation.get("value"))
        if issue:
            issues.append({"location": "calculations", **issue})
    return issues


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def is_not_applicable(match: dict[str, Any]) -> bool:
    return (
        match.get("status") == "NOT_APPLICABLE"
        or (match.get("model_decision") or {}).get("model_status") == "NOT_APPLICABLE"
    )


def audit_case(case_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    result_path = case_dir / "equipment_derivation_result.json"
    document = json.loads(result_path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for equipment in document.get("equipment", []):
        if not isinstance(equipment, dict):
            continue
        match = equipment.get("match_result") if isinstance(equipment.get("match_result"), dict) else {}
        decision = match.get("model_decision") if isinstance(match.get("model_decision"), dict) else {}
        recommendation = (
            match.get("model_recommendation")
            if isinstance(match.get("model_recommendation"), dict)
            else {}
        )
        leading = (
            recommendation.get("leading_candidate")
            if isinstance(recommendation.get("leading_candidate"), dict)
            else {}
        )
        terminal = (
            recommendation.get("terminal_selection")
            if isinstance(recommendation.get("terminal_selection"), dict)
            else {}
        )
        canonical = (
            equipment.get("canonical_match_input")
            if isinstance(equipment.get("canonical_match_input"), dict)
            else {}
        )
        excluded = is_not_applicable(match)
        hard_sanity_issues = equipment_hard_sanity_issues(canonical, match)
        recommended_type = str(recommendation.get("recommended_type") or "").strip()
        terminal_type = str(terminal.get("recommended_type") or "").strip()
        checks = {
            "matched_family": match.get("status") == "MATCHED" and bool((match.get("match") or {}).get("family_id")),
            "recommended_type_present": bool(recommended_type),
            "candidate_present": int(recommendation.get("candidate_count") or 0) > 0 and bool(recommendation.get("candidates")),
            "designation_present": bool(str(leading.get("designation") or "").strip()),
            "deterministic_no_llm": match.get("deterministic") is True and match.get("llm_used") is False,
            "no_unisolated_hard_sanity_outlier": not hard_sanity_issues,
            "terminal_selection_present": terminal.get("status") in TERMINAL_SELECTION_STATUSES,
            "terminal_scope_is_equipment_form": terminal.get("terminal_scope") == "equipment_form",
            "terminal_type_matches_recommendation": bool(terminal_type) and terminal_type == recommended_type,
            "terminal_rule_trace_present": bool(str(terminal.get("rule_id") or "").strip()),
            "no_legacy_generic_selection": terminal.get("selection_basis") != "legacy_generic_type",
            "no_unresolved_type_wording": not any(marker in recommended_type for marker in UNRESOLVED_TYPE_MARKERS),
            "default_is_explicitly_marked": (
                not bool(terminal.get("default_applied"))
                or (
                    terminal.get("status") == "DEFAULTED_TERMINAL_TYPE_SELECTED"
                    and bool(str(terminal.get("assumption") or "").strip())
                )
            ),
            "leading_candidate_carries_terminal_selection": (
                isinstance(leading.get("terminal_selection"), dict)
                and leading.get("terminal_selection") == terminal
            ),
        }
        passed = excluded or all(checks.values())
        rows.append({
            "case": case_dir.name,
            "equipment_tag": equipment.get("equipment_tag"),
            "aspen_block_type": canonical.get("aspen_block_type"),
            "process_function": canonical.get("process_function"),
            "applicability": "NOT_APPLICABLE_SIMULATION_LOGIC_NODE" if excluded else "PHYSICAL_EQUIPMENT",
            "gate_status": "N/A" if excluded else "PASS" if passed else "FAIL",
            "match_status": match.get("status"),
            "family_id": (match.get("match") or {}).get("family_id"),
            "model_status": decision.get("model_status"),
            "recommendation_status": recommendation.get("status"),
            "recommended_type": recommendation.get("recommended_type"),
            "terminal_selection_status": terminal.get("status"),
            "terminal_selection_basis": terminal.get("selection_basis"),
            "terminal_default_applied": bool(terminal.get("default_applied")),
            "terminal_rule_id": terminal.get("rule_id"),
            "terminal_assumption": terminal.get("assumption"),
            "candidate_count": int(recommendation.get("candidate_count") or 0),
            "candidate_kind": leading.get("candidate_kind"),
            "designation": leading.get("designation"),
            "formal_model": bool(leading.get("formal_model")),
            "provisional_warning_required": not excluded and not bool(leading.get("formal_model")),
            "missing_gate_count": len(leading.get("missing_gates") or []),
            "design_fallback_count": len(match.get("design_fallbacks") or []),
            "hard_sanity_issue_count": len(hard_sanity_issues),
            "hard_sanity_issues": hard_sanity_issues,
            "checks": checks,
        })

    physical = [row for row in rows if row["applicability"] == "PHYSICAL_EQUIPMENT"]
    failures = [row for row in physical if row["gate_status"] != "PASS"]
    return ({
        "case": case_dir.name,
        "source_result_path": str(result_path.resolve()),
        "source_result_sha256": sha256_file(result_path),
        "derivation_status": document.get("status"),
        "equipment_or_module_count": len(rows),
        "physical_equipment_count": len(physical),
        "not_applicable_count": len(rows) - len(physical),
        "model_or_specification_candidate_count": sum(row["gate_status"] == "PASS" for row in physical),
        "failure_count": len(failures),
        "status": "PASS" if document.get("status") == "DERIVED" and not failures else "FAIL",
        "model_status_counts": dict(sorted(Counter(str(row["model_status"] or "UNKNOWN") for row in physical).items())),
        "terminal_selection_status_counts": dict(sorted(Counter(
            str(row["terminal_selection_status"] or "UNKNOWN") for row in physical
        ).items())),
    }, rows)


def write_outputs(output_dir: Path, report: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "MULTI_BKP_MODEL_GATE_REPORT.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    csv_path = output_dir / "MULTI_BKP_MODEL_GATE_ROWS.csv"
    fieldnames = [
        "case", "equipment_tag", "aspen_block_type", "process_function", "applicability",
        "gate_status", "match_status", "family_id", "model_status", "recommendation_status",
        "recommended_type", "candidate_count", "candidate_kind", "designation", "formal_model",
        "terminal_selection_status", "terminal_selection_basis", "terminal_default_applied",
        "terminal_rule_id", "terminal_assumption",
        "provisional_warning_required", "missing_gate_count", "design_fallback_count",
        "hard_sanity_issue_count",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# 十 BKP 设备型号/规格候选门槛",
        "",
        f"- 总状态：`{report['status']}`",
        f"- BKP：{report['passed_case_count']}/{report['case_count']} 通过",
        f"- 物理设备：{report['candidate_pass_count']}/{report['physical_equipment_count']} 输出非空型号/规格候选",
        f"- 非设备流程逻辑节点：{report['not_applicable_count']}，明确记为 N/A",
        f"- 失败设备：{report['failure_count']}",
        "",
        "| BKP | 物理设备 | 有候选 | N/A | 失败 | 状态 |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for case in report["cases"]:
        lines.append(
            f"| {case['case']} | {case['physical_equipment_count']} | "
            f"{case['model_or_specification_candidate_count']} | {case['not_applicable_count']} | "
            f"{case['failure_count']} | {case['status']} |"
        )
    lines.extend([
        "",
        "说明：该门槛只要求每台物理设备持续输出确定性的型号/工程规格候选。",
        "候选若缺 EDR、Column Internals、SW6、厂家曲线或同设备批准，仍保持 provisional，不能冒充最终厂家型号。",
    ])
    (output_dir / "MULTI_BKP_MODEL_GATE_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Require every physical equipment record in replayed BKP cases to expose a deterministic model or engineering-specification candidate."
    )
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    input_dir = args.input_dir.expanduser().resolve()
    output_dir = (args.output_dir or input_dir).expanduser().resolve()
    case_dirs = sorted(
        path for path in input_dir.glob("case_*")
        if (path / "equipment_derivation_result.json").is_file()
    )
    if not case_dirs:
        raise SystemExit("No case_*/equipment_derivation_result.json files found")

    cases: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for case_dir in case_dirs:
        case_report, case_rows = audit_case(case_dir)
        cases.append(case_report)
        rows.extend(case_rows)

    physical = [row for row in rows if row["applicability"] == "PHYSICAL_EQUIPMENT"]
    failures = [row for row in physical if row["gate_status"] != "PASS"]
    report = {
        "schema": SCHEMA,
        "status": "PASS" if cases and all(case["status"] == "PASS" for case in cases) else "FAIL",
        "input_dir": str(input_dir),
        "case_count": len(cases),
        "passed_case_count": sum(case["status"] == "PASS" for case in cases),
        "equipment_or_module_count": len(rows),
        "physical_equipment_count": len(physical),
        "candidate_pass_count": sum(row["gate_status"] == "PASS" for row in physical),
        "not_applicable_count": len(rows) - len(physical),
        "failure_count": len(failures),
        "failure_rows": failures,
        "terminal_selection_status_counts": dict(sorted(Counter(
            str(row["terminal_selection_status"] or "UNKNOWN") for row in physical
        ).items())),
        "acceptance_rule": (
            "Every non-N/A physical equipment record must be MATCHED and deterministically pushed to one "
            "unambiguous terminal equipment form. Missing type conditions must use a registered, visibly marked "
            "default instead of leaving alternatives pending. Every record must still expose a candidate list and "
            "leading designation; sentinel-scale values must be isolated before selection."
        ),
        "formal_model_boundary": (
            "A preliminary model/specification candidate satisfies this continuity gate but is not a final vendor model; "
            "same-equipment specialist-software/vendor/mechanical evidence remains mandatory for formal promotion."
        ),
        "cases": cases,
    }
    write_outputs(output_dir, report, rows)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
