#!/usr/bin/env python3
"""Build a deterministic, source-grouped queue for unresolved phase-1 work.

The queue is planning metadata only.  It never changes a table/figure audit
status and therefore cannot promote OCR/candidate content into executable data.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def is_true(value: object) -> bool:
    return str(value or "").strip().casefold() == "true"


def parse_families(value: str) -> list[str]:
    try:
        parsed = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []
    return sorted({str(item) for item in parsed if str(item).strip()})


def _page(value: object) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def build_queue(
    source_inventory_path: Path,
    table_manifest_path: Path,
    figure_manifest_path: Path,
) -> dict:
    sources = read_csv(source_inventory_path)
    tables = read_csv(table_manifest_path)
    figures = read_csv(figure_manifest_path)

    source_by_id = {row.get("source_id", ""): row for row in sources}
    grouped: dict[str, dict] = defaultdict(
        lambda: {
            "unresolved_key_table_ids": [],
            "unresolved_figure_ids": [],
            "table_pages": set(),
            "figure_pages": set(),
            "families": set(),
            "row_authority_statuses": set(),
            "row_source_kinds": set(),
        }
    )

    for row in tables:
        if not is_true(row.get("key_table_candidate")):
            continue
        if row.get("audit_status") != "NEEDS_REVIEW":
            continue
        source_id = row.get("source_id") or row.get("doc_id") or ""
        item = grouped[source_id]
        item["unresolved_key_table_ids"].append(row.get("table_id", ""))
        page = _page(row.get("page_1based"))
        if page is not None:
            item["table_pages"].add(page)
        item["families"].update(parse_families(row.get("families_json", "")))
        if row.get("authority_status"):
            item["row_authority_statuses"].add(row["authority_status"])
        if row.get("source_kind"):
            item["row_source_kinds"].add(row["source_kind"])

    for row in figures:
        if row.get("audit_status") != "NEEDS_REVIEW":
            continue
        source_id = row.get("source_id") or row.get("doc_id") or ""
        item = grouped[source_id]
        item["unresolved_figure_ids"].append(row.get("figure_id", ""))
        page = _page(row.get("page_1based"))
        if page is not None:
            item["figure_pages"].add(page)
        item["families"].update(parse_families(row.get("families_json", "")))
        if row.get("authority_status"):
            item["row_authority_statuses"].add(row["authority_status"])
        if row.get("source_kind"):
            item["row_source_kinds"].add(row["source_kind"])

    records: list[dict] = []
    for source_id, item in grouped.items():
        source = source_by_id.get(source_id, {})
        authority = (
            source.get("authority_lifecycle_state")
            or source.get("authority_status")
            or (sorted(item["row_authority_statuses"])[0] if item["row_authority_statuses"] else "")
        )
        source_kind = source.get("source_kind") or (
            sorted(item["row_source_kinds"])[0] if item["row_source_kinds"] else ""
        )
        table_ids = sorted(filter(None, item["unresolved_key_table_ids"]))
        figure_ids = sorted(filter(None, item["unresolved_figure_ids"]))
        current_standard = authority == "CURRENT" and source_kind == "standard"
        if current_standard:
            priority_class = "P0_CURRENT_STANDARD"
        elif authority == "CURRENT":
            priority_class = "P1_CURRENT_OTHER"
        else:
            priority_class = "P2_AUTHORITY_OR_SCOPE_REVIEW"
        records.append(
            {
                "source_id": source_id,
                "standard_id": source.get("standard_id", ""),
                "source_kind": source_kind,
                "authority_status": authority,
                "authority_verification_status": source.get(
                    "authority_verification_status", ""
                ),
                "canonical_relative_path": source.get("canonical_relative_path", ""),
                "source_pdf_sha256": source.get("sha256", ""),
                "families": sorted(item["families"]),
                "priority_class": priority_class,
                "unresolved_key_table_count": len(table_ids),
                "unresolved_figure_count": len(figure_ids),
                "unresolved_total": len(table_ids) + len(figure_ids),
                "table_pages": sorted(item["table_pages"]),
                "figure_pages": sorted(item["figure_pages"]),
                "unresolved_key_table_ids": table_ids,
                "unresolved_figure_ids": figure_ids,
            }
        )

    class_rank = {
        "P0_CURRENT_STANDARD": 0,
        "P1_CURRENT_OTHER": 1,
        "P2_AUTHORITY_OR_SCOPE_REVIEW": 2,
    }
    records.sort(
        key=lambda row: (
            class_rank[row["priority_class"]],
            -row["unresolved_total"],
            row["source_id"],
        )
    )
    for index, row in enumerate(records, start=1):
        row["queue_rank"] = index

    return {
        "schema": "equipment-standard-phase1-work-queue-v1",
        "purpose": "planning_only_no_promotion_authority",
        "input_sha256": {
            "source_inventory": sha256_file(source_inventory_path),
            "table_manifest": sha256_file(table_manifest_path),
            "figure_manifest": sha256_file(figure_manifest_path),
        },
        "unresolved_source_count": len(records),
        "unresolved_key_table_count": sum(
            row["unresolved_key_table_count"] for row in records
        ),
        "unresolved_figure_count": sum(
            row["unresolved_figure_count"] for row in records
        ),
        "records": records,
    }


def write_queue_csv(path: Path, records: list[dict]) -> None:
    fieldnames = [
        "queue_rank",
        "priority_class",
        "source_id",
        "standard_id",
        "source_kind",
        "authority_status",
        "authority_verification_status",
        "families_json",
        "unresolved_key_table_count",
        "unresolved_figure_count",
        "unresolved_total",
        "canonical_relative_path",
        "source_pdf_sha256",
        "table_pages_json",
        "figure_pages_json",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in records:
            writer.writerow(
                {
                    "queue_rank": row["queue_rank"],
                    "priority_class": row["priority_class"],
                    "source_id": row["source_id"],
                    "standard_id": row["standard_id"],
                    "source_kind": row["source_kind"],
                    "authority_status": row["authority_status"],
                    "authority_verification_status": row[
                        "authority_verification_status"
                    ],
                    "families_json": json.dumps(
                        row["families"], ensure_ascii=False, separators=(",", ":")
                    ),
                    "unresolved_key_table_count": row[
                        "unresolved_key_table_count"
                    ],
                    "unresolved_figure_count": row["unresolved_figure_count"],
                    "unresolved_total": row["unresolved_total"],
                    "canonical_relative_path": row["canonical_relative_path"],
                    "source_pdf_sha256": row["source_pdf_sha256"],
                    "table_pages_json": json.dumps(row["table_pages"]),
                    "figure_pages_json": json.dumps(row["figure_pages"]),
                }
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-inventory", type=Path, required=True)
    parser.add_argument("--table-manifest", type=Path, required=True)
    parser.add_argument("--figure-manifest", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-csv", type=Path, required=True)
    args = parser.parse_args()

    payload = build_queue(
        args.source_inventory.resolve(),
        args.table_manifest.resolve(),
        args.figure_manifest.resolve(),
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_queue_csv(args.out_csv, payload["records"])
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
