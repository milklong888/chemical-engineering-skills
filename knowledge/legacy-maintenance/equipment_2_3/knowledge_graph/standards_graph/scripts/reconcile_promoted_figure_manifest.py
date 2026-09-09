#!/usr/bin/env python3
"""Reconcile an audit manifest with already approved executable figure data.

The extractor manifest is intentionally fail-closed.  A later, independently
audited promotion can therefore leave an old ``NEEDS_REVIEW`` row behind even
though the same exact figure is already present in the production executable
store.  This script closes only that bookkeeping gap.  It never promotes a
candidate package and never reads a source PDF or image.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def approved_datasets(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    approved: dict[str, dict[str, str]] = {}
    for row in rows:
        if row.get("promotion_state") != "APPROVED":
            continue
        if row.get("qa_status") != "VERIFIED":
            continue
        if int(row.get("unresolved_entities") or -1) != 0:
            continue
        if row.get("vision_disabled_replay_status") != "PASS":
            continue
        approved[row["dataset_id"]] = row
    return approved


def reconcile(
    manifest_rows: list[dict[str, str]],
    registry_rows: list[dict[str, str]],
    record_rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], dict]:
    approved = approved_datasets(registry_rows)
    records_by_figure: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in record_rows:
        if row.get("dataset_id") not in approved:
            continue
        if row.get("qa_status") != "VERIFIED":
            continue
        if not row.get("source_id") or not row.get("figure_id"):
            continue
        records_by_figure[(row["source_id"], row["figure_id"])].append(row)

    output: list[dict[str, str]] = []
    reconciled: list[dict[str, object]] = []
    rejected = Counter()
    for original in manifest_rows:
        row = dict(original)
        key = (row.get("source_id", ""), row.get("figure_id", ""))
        records = records_by_figure.get(key, [])
        if row.get("audit_status") != "NEEDS_REVIEW" or not records:
            output.append(row)
            continue

        if any(record.get("source_sha256") != row.get("source_pdf_sha256") for record in records):
            rejected["SOURCE_HASH_MISMATCH"] += 1
            output.append(row)
            continue
        dataset_ids = sorted({record["dataset_id"] for record in records})
        if any(approved[dataset_id].get("source_id") not in {"", row.get("source_id")} for dataset_id in dataset_ids):
            rejected["REGISTRY_SOURCE_ID_MISMATCH"] += 1
            output.append(row)
            continue
        reuse_classes = sorted({record.get("reuse_class", "") for record in records})
        if reuse_classes == ["DIRECT_REUSE_VERIFIED"]:
            terminal_status = "DIRECT_REUSE_VERIFIED"
        else:
            # Approved non-direct datasets are terminal boundaries, not direct facts.
            terminal_status = "EXECUTABLE_BOUNDARY_VERIFIED"

        row["audit_status"] = terminal_status
        row["dataization_state"] = "EXECUTABLE_STRUCTURED_DATASET"
        row["structured_dataset_id"] = "|".join(dataset_ids)
        row["structured_record_count"] = str(len(records))
        row["axis_or_object_qa_status"] = "VERIFIED"
        row["error_bound_or_relation_qa"] = "VERIFIED"
        row["vision_disabled_replay_status"] = "PASS"
        note = row.get("reviewer_note", "").strip()
        reconciliation_note = (
            "Reconciled from approved executable figure dataset; exact source_id, "
            "figure_id and source SHA-256 matched; no source PDF/image opened."
        )
        row["reviewer_note"] = f"{note} {reconciliation_note}".strip()
        output.append(row)
        reconciled.append(
            {
                "source_id": key[0],
                "figure_id": key[1],
                "dataset_ids": dataset_ids,
                "record_count": len(records),
                "reuse_classes": reuse_classes,
                "terminal_status": terminal_status,
            }
        )

    report = {
        "schema": "promoted-figure-manifest-reconciliation-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "input_row_count": len(manifest_rows),
        "approved_dataset_count": len(approved),
        "reconciled_row_count": len(reconciled),
        "rejected_counts": dict(sorted(rejected.items())),
        "remaining_needs_review_count": sum(
            row.get("audit_status") == "NEEDS_REVIEW" for row in output
        ),
        "reconciled_rows": reconciled,
        "boundary": (
            "Only exact figures already present in an APPROVED, VERIFIED, zero-unresolved, "
            "vision-disabled executable dataset are reconciled. Candidate packages are ignored."
        ),
    }
    return output, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--figure-manifest", type=Path, required=True)
    parser.add_argument("--figure-registry", type=Path, required=True)
    parser.add_argument("--figure-records", type=Path, required=True)
    parser.add_argument("--out-manifest", type=Path, required=True)
    parser.add_argument("--out-report", type=Path, required=True)
    args = parser.parse_args()

    manifest_rows = read_csv(args.figure_manifest.resolve())
    registry_rows = read_csv(args.figure_registry.resolve())
    record_rows = read_csv(args.figure_records.resolve())
    fields = list(manifest_rows[0])
    output, report = reconcile(manifest_rows, registry_rows, record_rows)
    write_csv(args.out_manifest.resolve(), output, fields)
    args.out_report.resolve().parent.mkdir(parents=True, exist_ok=True)
    args.out_report.resolve().write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
