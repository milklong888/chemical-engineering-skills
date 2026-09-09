from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


APPROVED_STATES = {"approved", "approved_project_method"}
EXCLUDED_SCOPES = {"reactor_excluded", "excluded_logical_or_bulk", "not_physical_equipment"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit method assignments against qualified source evidence.")
    parser.add_argument("--assignments", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    assignments = read_csv(args.assignments)
    ledger_rows = read_csv(args.ledger)
    ledger = {row["source_id"]: row for row in ledger_rows}
    issues: list[dict[str, Any]] = []

    required_approved = [
        "title", "authors_or_organization", "year", "source_type",
        "authority_tier", "url_or_doi", "equipment_family", "service_scope",
        "cost_scope", "base_period", "formula_or_table_locator",
        "independent_reproduction_status",
    ]
    for row in ledger_rows:
        if row.get("review_status", "").strip().lower() not in APPROVED_STATES:
            continue
        missing = [field for field in required_approved if not row.get(field, "").strip()]
        if missing:
            issues.append({"type": "approved_source_missing_fields", "source_id": row["source_id"], "fields": missing})
        local = row.get("local_path", "").strip()
        expected_hash = row.get("sha256", "").strip().upper()
        if local:
            path = Path(local)
            if not path.exists():
                issues.append({"type": "source_file_missing", "source_id": row["source_id"], "path": local})
            elif not expected_hash:
                issues.append({"type": "source_hash_missing", "source_id": row["source_id"], "path": local})
            elif sha256(path) != expected_hash:
                issues.append({"type": "source_hash_mismatch", "source_id": row["source_id"], "path": local})

    for row in assignments:
        if row.get("scope_class") in EXCLUDED_SCOPES:
            continue
        if row.get("method_id") in {"", "METHOD_GAP"}:
            issues.append({"type": "method_gap", "equipment_item_id": row.get("equipment_item_id")})
            continue
        source_ids = [item.strip() for item in row.get("source_ids", "").split(";") if item.strip()]
        if not source_ids:
            issues.append({"type": "method_source_missing", "equipment_item_id": row.get("equipment_item_id")})
        for source_id in source_ids:
            source = ledger.get(source_id)
            if not source:
                issues.append({"type": "source_id_not_registered", "equipment_item_id": row.get("equipment_item_id"), "source_id": source_id})
            elif source.get("review_status", "").strip().lower() not in APPROVED_STATES:
                issues.append({"type": "source_not_approved", "equipment_item_id": row.get("equipment_item_id"), "source_id": source_id, "status": source.get("review_status")})

    report = {
        "status": "pass" if not issues else "fail",
        "assignment_count": len(assignments),
        "source_count": len(ledger_rows),
        "issue_count": len(issues),
        "issues": issues,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
