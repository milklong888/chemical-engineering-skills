from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


SCHEMA = "equipment-design-multi-bkp-model-gate-v4"
NON_CONCRETE_TYPE_TERMS = (
    "非标准",
    "非标",
    "未定型",
    "待定",
    "待确认",
    "其他型式",
    "通用型",
    "generic",
    "placeholder",
    "unknown",
)
INELIGIBLE_CANDIDATE_KINDS = {"", "generic_type_placeholder"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def has_non_concrete_wording(value: Any) -> bool:
    text = str(value or "").strip().casefold()
    return not text or any(term.casefold() in text for term in NON_CONCRETE_TYPE_TERMS)


def is_logic_node(item: dict[str, Any], match: dict[str, Any]) -> bool:
    applicability = item.get("equipment_applicability")
    return (
        isinstance(applicability, dict)
        and applicability.get("status") == "NOT_APPLICABLE"
        and applicability.get("reason_code") == "NOT_APPLICABLE_SIMULATION_LOGIC_NODE"
        and applicability.get("independent_equipment_model_applicable_by_default") is False
        and match.get("status") == "NOT_APPLICABLE"
    )


def selection_row(
    *,
    case_name: str,
    record_kind: str,
    identity: str,
    item: dict[str, Any],
) -> dict[str, Any]:
    match = item.get("match_result") if isinstance(item.get("match_result"), dict) else {}
    excluded = record_kind == "equipment" and is_logic_node(item, match)
    recommendation = (
        match.get("model_recommendation")
        if isinstance(match.get("model_recommendation"), dict)
        else {}
    )
    candidates = [
        candidate
        for candidate in recommendation.get("candidates", [])
        if isinstance(candidate, dict)
    ]
    leading = (
        recommendation.get("leading_candidate")
        if isinstance(recommendation.get("leading_candidate"), dict)
        else candidates[0] if candidates else {}
    )
    terminal = (
        recommendation.get("terminal_selection")
        if isinstance(recommendation.get("terminal_selection"), dict)
        else {}
    )
    family = match.get("match") if isinstance(match.get("match"), dict) else {}
    recommended_type = str(recommendation.get("recommended_type") or "").strip()
    designation = str(
        leading.get("designation")
        or leading.get("display_name")
        or leading.get("model")
        or ""
    ).strip()
    candidate_kind = str(leading.get("candidate_kind") or "").strip()
    execution = (
        recommendation.get("selection_execution")
        if isinstance(recommendation.get("selection_execution"), dict)
        else {}
    )
    type_quality = (
        leading.get("type_name_quality")
        if isinstance(leading.get("type_name_quality"), dict)
        else {}
    )
    checks = {
        "matched_family": match.get("status") == "MATCHED" and bool(family.get("family_id")),
        "recommended_type_present": bool(recommended_type),
        "recommended_type_is_concrete": not has_non_concrete_wording(recommended_type),
        "candidate_present": bool(candidates),
        "candidate_kind_is_specific": candidate_kind not in INELIGIBLE_CANDIDATE_KINDS,
        "designation_present": bool(designation),
        "designation_is_concrete": not has_non_concrete_wording(designation),
        "deterministic_no_llm": match.get("deterministic") is True and match.get("llm_used") is False,
        "terminal_type_present": bool(str(terminal.get("recommended_type") or recommended_type).strip()),
        "type_quality_not_rejected": type_quality.get("status") != "REJECTED_NON_CONCRETE_TYPE_NAME",
        "not_vendor_model_claim": leading.get("is_vendor_model") is not True,
    }
    passed = excluded or all(checks.values())
    canonical = (
        item.get("canonical_match_input")
        if isinstance(item.get("canonical_match_input"), dict)
        else {}
    )
    return {
        "case": case_name,
        "record_kind": record_kind,
        "identity": identity,
        "aspen_block_type": canonical.get("aspen_block_type"),
        "applicability": (
            "NOT_APPLICABLE_SIMULATION_LOGIC_NODE" if excluded else "PHYSICAL_SELECTION_RECORD"
        ),
        "gate_status": "N/A" if excluded else "PASS" if passed else "FAIL",
        "match_status": match.get("status"),
        "family_id": family.get("family_id"),
        "recommended_type": recommended_type,
        "candidate_kind": candidate_kind,
        "designation": designation,
        "selection_execution_status": execution.get("status"),
        "formal_model": bool(leading.get("formal_model")),
        "is_vendor_model": bool(leading.get("is_vendor_model")),
        "candidate_eligibility": leading.get("candidate_eligibility"),
        "missing_gate_count": len(leading.get("missing_gates") or []),
        "checks": checks,
    }


def audit_case(case_name: str, result_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    document = json.loads(result_path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for item in document.get("equipment", []):
        if isinstance(item, dict):
            rows.append(selection_row(
                case_name=case_name,
                record_kind="equipment",
                identity=str(item.get("equipment_tag") or item.get("aspen_block_id") or ""),
                item=item,
            ))
    for item in document.get("piping", []):
        if isinstance(item, dict):
            rows.append(selection_row(
                case_name=case_name,
                record_kind="piping",
                identity=str(item.get("stream_id") or ""),
                item=item,
            ))

    physical = [row for row in rows if row["gate_status"] != "N/A"]
    failures = [row for row in physical if row["gate_status"] != "PASS"]
    equipment_physical = [
        row for row in physical if row["record_kind"] == "equipment"
    ]
    piping = [row for row in physical if row["record_kind"] == "piping"]
    run_gate = (
        document.get("aspen_run_gate")
        if isinstance(document.get("aspen_run_gate"), dict)
        else {}
    )
    formal_gate = str(document.get("formal_use_gate") or "")
    formal_gate_honest = (
        not formal_gate.startswith("FORMAL")
        if run_gate.get("status") != "CLEAN_RUN" or document.get("formal_use_blockers")
        else True
    )
    normalization_count = int(
        document.get("normalization_diagnostic_count")
        or len(document.get("normalization_diagnostics") or [])
    )
    status = (
        "PASS"
        if document.get("status") == "DERIVED"
        and not failures
        and normalization_count == 0
        and formal_gate_honest
        else "FAIL"
    )
    source_case = (
        document.get("source_case_evidence")
        if isinstance(document.get("source_case_evidence"), dict)
        else {}
    )
    return ({
        "case": case_name,
        "status": status,
        "source_result_path": str(result_path),
        "source_result_sha256": sha256_file(result_path),
        "source_case_path": source_case.get("source_case_path"),
        "source_case_sha256": source_case.get("source_case_sha256"),
        "source_export_sha256": document.get("source_export_sha256"),
        "derivation_status": document.get("status"),
        "engine_version": document.get("engine_version"),
        "aspen_run_status": run_gate.get("status"),
        "aspen_run_counts": run_gate.get("counts") or {},
        "formal_use_gate": formal_gate,
        "formal_gate_honest": formal_gate_honest,
        "formal_blocker_count": len(document.get("formal_use_blockers") or []),
        "normalization_diagnostic_count": normalization_count,
        "equipment_or_logic_count": sum(row["record_kind"] == "equipment" for row in rows),
        "physical_equipment_count": len(equipment_physical),
        "logic_node_count": sum(row["gate_status"] == "N/A" for row in rows),
        "piping_count": len(piping),
        "concrete_equipment_candidate_count": sum(row["gate_status"] == "PASS" for row in equipment_physical),
        "concrete_piping_candidate_count": sum(row["gate_status"] == "PASS" for row in piping),
        "selection_execution_status_counts": dict(sorted(Counter(
            str(row["selection_execution_status"] or "UNKNOWN") for row in physical
        ).items())),
        "recommended_type_counts": dict(sorted(Counter(
            str(row["recommended_type"]) for row in physical
        ).items())),
        "candidate_kind_counts": dict(sorted(Counter(
            str(row["candidate_kind"] or "UNKNOWN") for row in physical
        ).items())),
        "failure_count": len(failures),
    }, rows)


def parse_case_argument(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("--case must use LABEL=PATH")
    label, path_text = value.split("=", 1)
    label = label.strip()
    path = Path(path_text.strip()).expanduser().resolve()
    if not label:
        raise argparse.ArgumentTypeError("--case label must not be empty")
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"case result does not exist: {path}")
    return label, path


def discover_cases(input_dir: Path) -> list[tuple[str, Path]]:
    return [
        (case_dir.name, case_dir / "equipment_derivation_result.json")
        for case_dir in sorted(input_dir.glob("case_*"))
        if (case_dir / "equipment_derivation_result.json").is_file()
    ]


def write_outputs(output_dir: Path, report: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "MULTI_BKP_MODEL_GATE_REPORT.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    fieldnames = [
        "case", "record_kind", "identity", "aspen_block_type", "applicability",
        "gate_status", "match_status", "family_id", "recommended_type",
        "candidate_kind", "designation", "selection_execution_status",
        "formal_model", "is_vendor_model", "candidate_eligibility", "missing_gate_count",
    ]
    with (output_dir / "MULTI_BKP_MODEL_GATE_ROWS.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# 真实 Aspen BKP 自动选型可靠性门槛",
        "",
        f"- 总状态：`{report['status']}`",
        f"- BKP：{report['passed_case_count']}/{report['case_count']} 通过",
        f"- 物理设备：{report['concrete_equipment_candidate_count']}/{report['physical_equipment_count']} 有具体候选",
        f"- 管线：{report['concrete_piping_candidate_count']}/{report['piping_count']} 有具体候选",
        f"- 流程逻辑节点：{report['logic_node_count']} 个明确标记 N/A",
        f"- 非具体/缺失候选：{report['failure_count']}",
        "",
        "| BKP | Aspen运行 | 设备候选 | 管线候选 | 逻辑N/A | 单位诊断 | 正式门槛 | 状态 |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for case in report["cases"]:
        lines.append(
            f"| {case['case']} | {case['aspen_run_status']} | "
            f"{case['concrete_equipment_candidate_count']}/{case['physical_equipment_count']} | "
            f"{case['concrete_piping_candidate_count']}/{case['piping_count']} | "
            f"{case['logic_node_count']} | {case['normalization_diagnostic_count']} | "
            f"{case['formal_use_gate']} | {case['status']} |"
        )
    lines.extend([
        "",
        "## 具体型式覆盖",
        "",
    ])
    for case in report["cases"]:
        type_summary = "；".join(
            f"{name} × {count}"
            for name, count in case["recommended_type_counts"].items()
        )
        lines.append(f"- `{case['case']}`：{type_summary}")
    lines.extend([
        "",
        "每一台设备和每一条管线的完整工程规格、候选种类、执行状态与证据门槛见 `MULTI_BKP_MODEL_GATE_ROWS.csv`。",
        "",
        "通过含义：每个物理设备记录和每条物料管线都有确定性、非占位的具体工程型式或标准规格候选。",
        "该门槛不把工程候选冒充厂家最终型号；Aspen 脏运行、真空外压、机械设计或厂家证据不足时，正式使用门槛继续保持阻断。",
    ])
    (output_dir / "MULTI_BKP_MODEL_GATE_REPORT.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit concrete deterministic candidates for every physical Aspen equipment "
            "record and every material-stream piping record."
        )
    )
    parser.add_argument("--case", action="append", default=[], type=parse_case_argument)
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    cases: list[tuple[str, Path]] = list(args.case)
    if args.input_dir:
        cases.extend(discover_cases(args.input_dir.expanduser().resolve()))
    deduplicated: dict[str, Path] = {}
    for label, path in cases:
        if label in deduplicated and deduplicated[label] != path:
            raise SystemExit(f"duplicate case label with different paths: {label}")
        deduplicated[label] = path
    if not deduplicated:
        raise SystemExit("No derivation results supplied")

    case_reports: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for label, path in sorted(deduplicated.items()):
        case_report, case_rows = audit_case(label, path)
        case_reports.append(case_report)
        rows.extend(case_rows)

    report = {
        "schema": SCHEMA,
        "status": "PASS" if all(case["status"] == "PASS" for case in case_reports) else "FAIL",
        "case_count": len(case_reports),
        "passed_case_count": sum(case["status"] == "PASS" for case in case_reports),
        "physical_equipment_count": sum(case["physical_equipment_count"] for case in case_reports),
        "concrete_equipment_candidate_count": sum(
            case["concrete_equipment_candidate_count"] for case in case_reports
        ),
        "piping_count": sum(case["piping_count"] for case in case_reports),
        "concrete_piping_candidate_count": sum(
            case["concrete_piping_candidate_count"] for case in case_reports
        ),
        "logic_node_count": sum(case["logic_node_count"] for case in case_reports),
        "failure_count": sum(case["failure_count"] for case in case_reports),
        "non_concrete_type_terms": list(NON_CONCRETE_TYPE_TERMS),
        "acceptance_rule": (
            "Every non-N/A physical equipment record and every material-stream piping record "
            "must expose a deterministic MATCHED family and a concrete, non-placeholder type/specification candidate."
        ),
        "formal_model_boundary": (
            "Candidate continuity does not promote a result to a final vendor model. Dirty Aspen "
            "runs, calculation blockers, mechanical design, material, and vendor evidence remain gated."
        ),
        "cases": case_reports,
    }
    write_outputs(args.output_dir.expanduser().resolve(), report, rows)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
