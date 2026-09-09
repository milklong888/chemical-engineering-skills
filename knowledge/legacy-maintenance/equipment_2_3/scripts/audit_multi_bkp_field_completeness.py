from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA = "equipment-design-multi-bkp-field-completeness-v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def unique_strings(values: list[Any]) -> list[str]:
    return sorted({str(value).strip() for value in values if str(value).strip()})


def package_counts(match: dict[str, Any]) -> tuple[int, int, int, list[str]]:
    package = match.get("design_parameter_package")
    if not isinstance(package, dict):
        return 0, 0, 0, []
    rows = [
        row
        for group in package.get("groups", [])
        if isinstance(group, dict)
        for row in group.get("rows", [])
        if isinstance(row, dict)
    ]
    missing = [row for row in rows if row.get("state") == "MISSING"]
    required_missing = [row for row in missing if row.get("required_for")]
    return (
        len(rows),
        len(missing),
        len(required_missing),
        unique_strings([row.get("field_id") for row in required_missing]),
    )


def identity_gaps(match: dict[str, Any]) -> list[str]:
    progress = match.get("progress")
    if not isinstance(progress, dict):
        return []
    gaps: list[str] = []
    for item in progress.get("minimum_missing_sets", []):
        if not isinstance(item, dict) or item.get("goal") != "resolve_identity":
            continue
        alternatives = item.get("alternatives")
        if isinstance(alternatives, list):
            for alternative in alternatives:
                if isinstance(alternative, list):
                    gaps.extend(str(field) for field in alternative)
    return unique_strings(gaps)


def next_fields(match: dict[str, Any]) -> list[str]:
    progress = match.get("progress")
    if not isinstance(progress, dict):
        return []
    rows = progress.get("next_fields")
    if not isinstance(rows, list):
        return []
    return unique_strings([row.get("field") for row in rows if isinstance(row, dict)])


def parameter_error_fields(match: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors = match.get("parameter_errors")
    if not isinstance(errors, list):
        return [], []
    return (
        unique_strings([row.get("field") for row in errors if isinstance(row, dict)]),
        unique_strings([row.get("code") for row in errors if isinstance(row, dict)]),
    )


def build(input_dir: Path, output_dir: Path) -> dict[str, Any]:
    source_paths = sorted(input_dir.glob("case_*/equipment_derivation_result.json"))
    if not source_paths:
        raise FileNotFoundError(f"no case_*/equipment_derivation_result.json below {input_dir}")
    equipment_rows: list[dict[str, Any]] = []
    case_rows: list[dict[str, Any]] = []
    for case_index, path in enumerate(source_paths, 1):
        derived = json.loads(path.read_text(encoding="utf-8-sig"))
        equipment = derived.get("equipment") if isinstance(derived.get("equipment"), list) else []
        case_match_status: collections.Counter[str] = collections.Counter()
        case_model_status: collections.Counter[str] = collections.Counter()
        for item in equipment:
            if not isinstance(item, dict):
                continue
            match = item.get("match_result") if isinstance(item.get("match_result"), dict) else {}
            match_identity = match.get("match") if isinstance(match.get("match"), dict) else {}
            model = match.get("model_decision") if isinstance(match.get("model_decision"), dict) else {}
            canonical = item.get("canonical_match_input") if isinstance(item.get("canonical_match_input"), dict) else {}
            parameter_rows, missing_rows, required_missing_rows, required_missing_fields = package_counts(match)
            error_fields, error_codes = parameter_error_fields(match)
            match_status = str(match.get("status") or "UNKNOWN")
            model_status = str(model.get("model_status") or "UNAVAILABLE")
            case_match_status[match_status] += 1
            case_model_status[model_status] += 1
            equipment_rows.append({
                "case_index": case_index,
                "case_directory": path.parent.name,
                "equipment_tag": item.get("equipment_tag"),
                "aspen_block_id": item.get("aspen_block_id"),
                "aspen_block_type": canonical.get("aspen_block_type"),
                "process_function": canonical.get("process_function"),
                "match_status": match_status,
                "family_id": match_identity.get("family_id"),
                "family_name": match_identity.get("family_name"),
                "model_status": model_status,
                "generated_candidate_kind": model.get("generated_candidate_kind"),
                "generated_candidate_designation": model.get("generated_candidate_designation"),
                "vendor_model": model.get("vendor_model"),
                "identity_gap_fields": identity_gaps(match),
                "next_fields": next_fields(match),
                "parameter_error_fields": error_fields,
                "parameter_error_codes": error_codes,
                "sizing_missing_fields": unique_strings(model.get("sizing_missing_fields", [])),
                "verification_missing_fields": unique_strings(model.get("verification_missing_fields", [])),
                "parameter_row_count": parameter_rows,
                "missing_parameter_row_count": missing_rows,
                "required_missing_parameter_row_count": required_missing_rows,
                "required_missing_parameter_fields": required_missing_fields,
                "canonical_input_field_count": len(canonical),
                "canonical_input_fields": sorted(canonical),
                "result_retained": True,
            })
        case_rows.append({
            "case_index": case_index,
            "case_directory": path.parent.name,
            "source_path": str(path),
            "source_sha256": sha256_file(path),
            "equipment_count": len(equipment),
            "match_status_counts": dict(sorted(case_match_status.items())),
            "model_status_counts": dict(sorted(case_model_status.items())),
        })

    match_counts = collections.Counter(str(row["match_status"]) for row in equipment_rows)
    model_counts = collections.Counter(str(row["model_status"]) for row in equipment_rows)
    blocked = [row for row in equipment_rows if row["match_status"].startswith("BLOCKED_")]
    summary = {
        "schema": SCHEMA,
        "source_root": str(input_dir),
        "case_count": len(case_rows),
        "equipment_count": len(equipment_rows),
        "result_retained_count": sum(1 for row in equipment_rows if row["result_retained"]),
        "match_status_counts": dict(sorted(match_counts.items())),
        "model_status_counts": dict(sorted(model_counts.items())),
        "blocked_equipment_count": len(blocked),
        "blocked_equipment": [
            {
                "case_directory": row["case_directory"],
                "equipment_tag": row["equipment_tag"],
                "aspen_block_type": row["aspen_block_type"],
                "match_status": row["match_status"],
                "identity_gap_fields": row["identity_gap_fields"],
                "parameter_error_fields": row["parameter_error_fields"],
                "parameter_error_codes": row["parameter_error_codes"],
                "next_fields": row["next_fields"],
            }
            for row in blocked
        ],
        "equipment_with_required_missing_parameter_rows": sum(
            1 for row in equipment_rows if row["required_missing_parameter_row_count"] > 0
        ),
        "total_required_missing_parameter_rows": sum(
            int(row["required_missing_parameter_row_count"]) for row in equipment_rows
        ),
        "case_results": case_rows,
        "interpretation": {
            "MATCHED": "deterministic equipment family matched; model/type may still be screening-only",
            "NOT_APPLICABLE": "Aspen topology/logic node intentionally not forced into physical equipment",
            "BLOCKED_MISSING_DECISIVE_IDENTITY": "equipment result retained but exact family/type needs a decisive identity field",
            "BLOCKED_INVALID_PARAMETERS": "equipment result retained but listed parameter fields failed validation",
            "type_selected": "generic equipment type selected; not a vendor model",
            "custom_equipment_no_universal_model": "custom equipment designation returned; no universal standard model exists",
            "calculation_blocked": "family is known but the model/type calculation lacks listed sizing inputs",
        },
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "MULTI_BKP_FIELD_COMPLETENESS_REPORT.json"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    csv_rows: list[dict[str, Any]] = []
    for row in equipment_rows:
        csv_rows.append({
            key: " | ".join(str(item) for item in value) if isinstance(value, list) else value
            for key, value in row.items()
        })
    csv_path = output_dir / "MULTI_BKP_EQUIPMENT_FIELD_GAPS.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0]))
        writer.writeheader()
        writer.writerows(csv_rows)
    print(json.dumps({
        "status": "PASS",
        "case_count": summary["case_count"],
        "equipment_count": summary["equipment_count"],
        "blocked_equipment_count": summary["blocked_equipment_count"],
        "match_status_counts": summary["match_status_counts"],
        "model_status_counts": summary["model_status_counts"],
        "json_path": str(json_path),
        "csv_path": str(csv_path),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit retained equipment/model outputs and exact field gaps across a multi-BKP run.")
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    build(args.input_dir.expanduser().resolve(), args.output_dir.expanduser().resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
