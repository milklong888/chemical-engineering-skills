#!/usr/bin/env python3
"""Build a non-numeric, source-bound table router dataset.

This adapter deliberately exposes only table identity, caption, page and audit
locators.  It rejects any record that claims numeric runtime reuse.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest().upper()


def false_string(value: str) -> bool:
    return str(value or "").strip().casefold() in {"false", "0", "no"}


def build_rows(rows: list[dict[str, str]], expected_source_sha256: str) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        record_id = str(row.get("record_id") or "").strip()
        table_id = str(row.get("table_id") or "").strip()
        caption = str(row.get("caption") or "").strip()
        page = str(row.get("physical_page") or "").strip()
        if not record_id or not table_id or not caption or not page:
            raise ValueError("method router record lacks identity, caption or page")
        if record_id in seen:
            raise ValueError(f"duplicate record_id: {record_id}")
        seen.add(record_id)
        if row.get("source_pdf_sha256", "").upper() != expected_source_sha256.upper():
            raise ValueError(f"{record_id}: source SHA-256 mismatch")
        if row.get("reuse_class") != "METHOD_ONLY":
            raise ValueError(f"{record_id}: reuse_class must be METHOD_ONLY")
        if not false_string(row.get("numeric_cells_exposed", "")):
            raise ValueError(f"{record_id}: numeric cells must remain hidden")
        if not false_string(row.get("runtime_numeric_reuse_allowed", "")):
            raise ValueError(f"{record_id}: runtime numeric reuse must be forbidden")
        output.append(
            {
                **row,
                "record_type": "table_router_metadata",
                "source_table": table_id,
                "raw_value": caption,
                "normalized_value": caption,
                "applicability": str(row.get("query_payload") or "").strip(),
                "qa_status": "VERIFIED_METADATA_ONLY",
                "terminal_class": "METHOD_ONLY_ROUTER",
            }
        )
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--expected-source-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    with args.input.open("r", encoding="utf-8-sig", newline="") as handle:
        source_rows = list(csv.DictReader(handle))
    rows = build_rows(source_rows, args.expected_source_sha256)
    fields = list(rows[0])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    report = {
        "schema": "method-only-table-router-build-v1",
        "input_sha256": sha256_path(args.input),
        "output_sha256": sha256_path(args.output),
        "record_count": len(rows),
        "numeric_cells_exposed": False,
        "runtime_numeric_reuse_allowed": False,
        "boundary": "Metadata routing only; no table cell, limit, dimension or coefficient is exposed.",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
