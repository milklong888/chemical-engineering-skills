#!/usr/bin/env python3
"""Build the fail-closed phase-1 executable-data acceptance report."""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def manifest_int(payload: dict, key: str) -> int:
    """Read a required integer without collapsing the valid value zero."""
    value = payload.get(key)
    if value is None or value == "":
        return -1
    return int(value)


def build_report(
    source_inventory: Path,
    table_manifest: Path,
    figure_manifest: Path,
    executable_manifest: Path,
) -> dict:
    sources = read_csv(source_inventory)
    tables = read_csv(table_manifest)
    figures = read_csv(figure_manifest)
    executable = read_json(executable_manifest)
    blockers: list[dict] = []

    unprocessed_sources = [
        row
        for row in sources
        if row.get("digitization_state")
        in {"NOT_EXTRACTED", "NON_PDF_REQUIRES_STRUCTURED_EXTRACTION"}
    ]
    if unprocessed_sources:
        blockers.append(
            {"code": "SOURCE_NOT_PROCESSED", "count": len(unprocessed_sources)}
        )
    unresolved_key_tables = [
        row
        for row in tables
        if str(row.get("key_table_candidate") or "").casefold() == "true"
        and row.get("audit_status") == "NEEDS_REVIEW"
    ]
    if unresolved_key_tables:
        blockers.append(
            {"code": "KEY_TABLE_NEEDS_REVIEW", "count": len(unresolved_key_tables)}
        )
    unresolved_figures = [
        row for row in figures if row.get("audit_status") == "NEEDS_REVIEW"
    ]
    if unresolved_figures:
        blockers.append(
            {"code": "FIGURE_NEEDS_REVIEW", "count": len(unresolved_figures)}
        )
    bad_direct_tables = [
        row
        for row in tables
        if row.get("audit_status") == "DIRECT_REUSE_VERIFIED"
        and row.get("authority_status") != "CURRENT"
    ]
    if bad_direct_tables:
        blockers.append(
            {"code": "DIRECT_TABLE_NOT_CURRENT", "count": len(bad_direct_tables)}
        )
    if executable.get("source_document_runtime_access") != "FORBIDDEN":
        blockers.append({"code": "SOURCE_RUNTIME_ACCESS_NOT_FORBIDDEN", "count": 1})
    if executable.get("source_image_runtime_access") != "FORBIDDEN":
        blockers.append({"code": "IMAGE_RUNTIME_ACCESS_NOT_FORBIDDEN", "count": 1})
    if executable.get("vision_capability") is not False:
        blockers.append({"code": "VISION_CAPABILITY_NOT_FALSE", "count": 1})
    if not executable.get("csv_sqlite_row_count_equal"):
        blockers.append({"code": "STANDARD_CSV_SQLITE_MISMATCH", "count": 1})
    if not executable.get("figure_csv_sqlite_row_count_equal"):
        blockers.append({"code": "FIGURE_CSV_SQLITE_MISMATCH", "count": 1})

    database = Path(executable["sqlite_path"])
    connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
    try:
        quick_check = connection.execute("PRAGMA quick_check").fetchone()[0]
        standard_db_count = connection.execute(
            "SELECT COUNT(*) FROM standard_records"
        ).fetchone()[0]
        figure_db_count = connection.execute(
            "SELECT COUNT(*) FROM figure_records"
        ).fetchone()[0]
    finally:
        connection.close()
    if quick_check != "ok":
        blockers.append({"code": "SQLITE_QUICK_CHECK_FAILED", "count": 1})
    if standard_db_count != manifest_int(executable, "record_count"):
        blockers.append({"code": "STANDARD_MANIFEST_DB_COUNT_MISMATCH", "count": 1})
    if figure_db_count != manifest_int(executable, "figure_record_count"):
        blockers.append({"code": "FIGURE_MANIFEST_DB_COUNT_MISMATCH", "count": 1})

    return {
        "schema": "equipment-executable-data-phase1-acceptance-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if not blockers else "FAIL",
        "blockers": blockers,
        "source_count": len(sources),
        "source_digitization_state_counts": dict(
            sorted(Counter(row.get("digitization_state", "") for row in sources).items())
        ),
        "authority_status_counts": dict(
            sorted(Counter(row.get("authority_status", "") for row in sources).items())
        ),
        "source_unreadable_blocked_count": sum(
            row.get("digitization_state") == "SOURCE_UNREADABLE_BLOCKED" for row in sources
        ),
        "table_count": len(tables),
        "table_status_counts": dict(
            sorted(Counter(row.get("audit_status", "") for row in tables).items())
        ),
        "unresolved_key_table_count": len(unresolved_key_tables),
        "figure_count": len(figures),
        "figure_status_counts": dict(
            sorted(Counter(row.get("audit_status", "") for row in figures).items())
        ),
        "unresolved_figure_count": len(unresolved_figures),
        "executable_standard_record_count": standard_db_count,
        "executable_figure_record_count": figure_db_count,
        "sqlite_quick_check": quick_check,
        "vision_capability": False,
        "note": "Blocked/unresolved authority sources remain queryable boundaries and cannot drive direct reuse.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-inventory", type=Path, required=True)
    parser.add_argument("--table-manifest", type=Path, required=True)
    parser.add_argument("--figure-manifest", type=Path, required=True)
    parser.add_argument("--executable-manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(
        args.source_inventory.resolve(),
        args.table_manifest.resolve(),
        args.figure_manifest.resolve(),
        args.executable_manifest.resolve(),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
