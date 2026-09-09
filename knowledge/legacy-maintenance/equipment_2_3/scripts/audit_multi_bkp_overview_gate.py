from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PACKAGE_ROOT / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import customer_delivery


AUTHORITY_CONTRACT = "3-2-equipment-selection-overview-v1"
ALLOWED_TABLE_IDS = frozenset({
    *(f"T{index:02d}" for index in range(1, 15)),
    *(f"X{index:02d}" for index in range(1, 6)),
})
TERMINAL_STATUSES = frozenset({
    "EXPLICIT_TERMINAL_TYPE_SELECTED",
    "CONDITIONED_TERMINAL_TYPE_SELECTED",
    "DEFAULTED_TERMINAL_TYPE_SELECTED",
})
INCOMPLETE_AUTHORITY_STATES = frozenset({
    "MISSING",
    "EXTERNAL_REQUIRED",
    "NOT_EXPLICITLY_ADOPTED",
})


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def present(value: Any) -> bool:
    return value is not None and (not isinstance(value, str) or bool(value.strip()))


def missing_authority_overview_fields(cells: list[Mapping[str, Any]]) -> list[str]:
    """Return authority fields that still lack a visible preliminary-design value."""
    missing: set[str] = set()
    for cell in cells:
        field_id = str(cell.get("field_id") or "").strip()
        if not field_id:
            continue
        state = str(cell.get("state") or "").strip().upper()
        if not present(cell.get("value")) or state in INCOMPLETE_AUTHORITY_STATES:
            missing.add(field_id)
    return sorted(missing)


def discover_result_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    single = root / "equipment_derivation_result.json"
    if single.is_file():
        paths.append(single)
    paths.extend(sorted(root.glob("case_*/equipment_derivation_result.json")))
    return paths


def physical_equipment(result: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    for item in result.get("equipment", []) if isinstance(result.get("equipment"), list) else []:
        if not isinstance(item, Mapping):
            continue
        match = item.get("match_result")
        if not isinstance(match, Mapping):
            continue
        if (
            item.get("aspen_mapping_status") == "NOT_APPLICABLE_SIMULATION_LOGIC_NODE"
            or match.get("status") == "NOT_APPLICABLE"
        ):
            continue
        rows.append(item)
    return rows


def audit_case(path: Path, *, write_delivery: bool) -> dict[str, Any]:
    result = json.loads(path.read_text(encoding="utf-8-sig"))
    physical = physical_equipment(result)
    failures: list[dict[str, Any]] = []
    try:
        bundle = customer_delivery.build_customer_delivery(result)
    except Exception as exc:
        return {
            "case_path": str(path),
            "physical_equipment_count": len(physical),
            "overview_row_count": 0,
            "failure_count": 1,
            "failures": [{"code": "CUSTOMER_EXPORT_FAILED", "detail": str(exc)}],
            "status": "FAIL",
        }

    overview = bundle.get("equipment_overview_table", {})
    rows = overview.get("rows", []) if isinstance(overview.get("rows"), list) else []
    if bundle.get("deterministic") is not True or bundle.get("llm_used") is not False:
        failures.append({"code": "NO_LLM_CONTRACT_FAILED"})
    if overview.get("authority_contract") != AUTHORITY_CONTRACT:
        failures.append({
            "code": "AUTHORITY_CONTRACT_MISMATCH",
            "actual": overview.get("authority_contract"),
        })
    if len(rows) != len(physical):
        failures.append({
            "code": "PHYSICAL_EQUIPMENT_ROW_COUNT_MISMATCH",
            "expected": len(physical),
            "actual": len(rows),
        })
    expected_tags = sorted(
        str(item.get("equipment_tag") or item.get("aspen_block_id") or "")
        for item in physical
    )
    actual_tags = sorted(str(row.get("equipment_tag") or "") for row in rows)
    if expected_tags != actual_tags:
        failures.append({
            "code": "PHYSICAL_EQUIPMENT_ROW_IDENTITY_MISMATCH",
            "expected": expected_tags,
            "actual": actual_tags,
        })

    for row in rows:
        equipment = str(row.get("equipment_tag") or row.get("equipment_key") or "")
        table_id = row.get("authority_table_id")
        if table_id not in ALLOWED_TABLE_IDS:
            failures.append({"equipment": equipment, "code": "AUTHORITY_TABLE_NOT_RESOLVED", "actual": table_id})
        columns = row.get("authority_columns", []) if isinstance(row.get("authority_columns"), list) else []
        cells = row.get("authority_cells", []) if isinstance(row.get("authority_cells"), list) else []
        if not columns or len(cells) != len(columns):
            failures.append({
                "equipment": equipment,
                "code": "AUTHORITY_ROW_SHAPE_INCOMPLETE",
                "column_count": len(columns),
                "cell_count": len(cells),
            })
        column_ids = [str(item.get("field_id")) for item in columns if isinstance(item, Mapping)]
        cell_ids = [str(item.get("field_id")) for item in cells if isinstance(item, Mapping)]
        if column_ids != cell_ids:
            failures.append({"equipment": equipment, "code": "AUTHORITY_COLUMN_CELL_ORDER_MISMATCH"})
        for cell in cells:
            if not isinstance(cell, Mapping) or not present(cell.get("field_id")) or not present(cell.get("state")):
                failures.append({"equipment": equipment, "code": "AUTHORITY_CELL_STATE_MISSING"})
                break
        missing_fields = missing_authority_overview_fields([
            cell for cell in cells if isinstance(cell, Mapping)
        ])
        if missing_fields:
            failures.append({
                "equipment": equipment,
                "code": "AUTHORITY_OVERVIEW_VALUE_MISSING",
                "fields": missing_fields,
            })
        if not present(row.get("equipment_type")):
            failures.append({"equipment": equipment, "code": "TERMINAL_EQUIPMENT_TYPE_EMPTY"})
        if not present(row.get("model_or_specification")):
            failures.append({"equipment": equipment, "code": "MODEL_OR_ENGINEERING_SPECIFICATION_EMPTY"})
        if not present(row.get("model_or_specification_status")):
            failures.append({"equipment": equipment, "code": "MODEL_OR_SPECIFICATION_STATUS_EMPTY"})
        if row.get("terminal_selection_status") not in TERMINAL_STATUSES:
            failures.append({
                "equipment": equipment,
                "code": "UNIQUE_TERMINAL_SELECTION_MISSING",
                "actual": row.get("terminal_selection_status"),
            })
        unified_cells = (
            row.get("all_equipment_fields", [])
            if isinstance(row.get("all_equipment_fields"), list)
            else []
        )
        unified_by_id = {
            str(cell.get("field_id")): cell
            for cell in unified_cells
            if isinstance(cell, Mapping) and present(cell.get("field_id"))
        }
        if not unified_cells or len(unified_by_id) != len(unified_cells):
            failures.append({"equipment": equipment, "code": "UNIFIED_FIELD_SET_INVALID"})
        elif any(not present(cell.get("state")) for cell in unified_cells if isinstance(cell, Mapping)):
            failures.append({"equipment": equipment, "code": "UNIFIED_FIELD_STATE_MISSING"})
        unified_type = unified_by_id.get("equipment_type", {})
        if (
            unified_type.get("value") != row.get("equipment_type")
            or unified_type.get("state") in {"MISSING", "NOT_EXPLICITLY_ADOPTED"}
            or "equipment_type" in row.get("customer_table_missing_fields", [])
        ):
            failures.append({
                "equipment": equipment,
                "code": "TERMINAL_TYPE_NOT_PROPAGATED_TO_UNIFIED_OVERVIEW",
                "top_level": row.get("equipment_type"),
                "unified_value": unified_type.get("value"),
                "unified_state": unified_type.get("state"),
            })

    delivery_path = path.with_name("customer_delivery.json")
    if write_delivery:
        delivery_path.write_text(
            json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return {
        "case_path": str(path),
        "source_result_sha256": sha256_file(path),
        "delivery_path": str(delivery_path) if write_delivery else None,
        "delivery_sha256": sha256_file(delivery_path) if write_delivery else None,
        "physical_equipment_count": len(physical),
        "overview_row_count": len(rows),
        "authority_missing_field_count": sum(
            len(row.get("authority_missing_fields", []))
            for row in rows
            if isinstance(row, Mapping) and isinstance(row.get("authority_missing_fields"), list)
        ),
        "failure_count": len(failures),
        "failures": failures,
        "status": "PASS" if not failures else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Require no-LLM Aspen replay to emit one complete 3-2 authority overview row per physical equipment item."
    )
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output")
    parser.add_argument("--write-deliveries", action="store_true")
    args = parser.parse_args()

    root = Path(args.input_dir).expanduser().resolve()
    paths = discover_result_paths(root)
    cases = [audit_case(path, write_delivery=args.write_deliveries) for path in paths]
    report = {
        "schema": "equipment-design-multi-bkp-authority-overview-gate-v2",
        "acceptance_rule": (
            "With LLM/network disabled, every physical Aspen equipment record produces one preliminary-complete row under the "
            "3-2 equipment-selection-overview authority with the same equipment identity. Logic nodes are excluded; "
            "every authority cell has a visible value; warned deterministic defaults/recommendations are allowed at the "
            "preliminary-design gate, while blank, MISSING, EXTERNAL_REQUIRED, and NOT_EXPLICITLY_ADOPTED cells fail. "
            "This gate does not claim vendor/mechanical finalization. Terminal equipment type and model/engineering "
            "specification may not be empty; the terminal type must also be propagated into the unified field set "
            "and may not remain in the customer missing-field list."
        ),
        "deterministic": True,
        "llm_used": False,
        "case_count": len(cases),
        "physical_equipment_count": sum(item["physical_equipment_count"] for item in cases),
        "overview_row_count": sum(item["overview_row_count"] for item in cases),
        "authority_missing_field_count": sum(item.get("authority_missing_field_count", 0) for item in cases),
        "failure_count": sum(item["failure_count"] for item in cases),
        "cases": cases,
    }
    report["status"] = "PASS" if paths and report["failure_count"] == 0 else "FAIL"
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
