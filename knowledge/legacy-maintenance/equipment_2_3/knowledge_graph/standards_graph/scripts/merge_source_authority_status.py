#!/usr/bin/env python3
"""Join source inventory and independently resolved authority state by hash."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def merge_inventory(source_inventory: Path, authority_status: Path) -> tuple[list[dict], dict]:
    sources = read_csv(source_inventory)
    authority_rows = read_csv(authority_status)
    authority_by_id: dict[str, dict] = {}
    for row in authority_rows:
        source_id = row.get("source_id", "")
        if source_id in authority_by_id:
            raise ValueError(f"duplicate authority row for {source_id}")
        authority_by_id[source_id] = row

    merged: list[dict] = []
    standard_kinds = {"standard", "construction_standard", "obsolete_standard"}
    for source in sources:
        row = dict(source)
        if source.get("source_kind") in standard_kinds:
            authority = authority_by_id.get(source.get("source_id", ""))
            if not authority:
                raise ValueError(f"missing authority row for {source.get('source_id')}")
            if str(authority.get("source_sha256") or "").upper() != str(
                source.get("sha256") or ""
            ).upper():
                raise ValueError(f"authority hash mismatch for {source.get('source_id')}")
            row["authority_status"] = authority.get("authority_state", "UNRESOLVED")
            row["authority_lifecycle_state"] = authority.get("lifecycle_state", "")
            row["authority_verification_status"] = authority.get(
                "verification_status", ""
            )
            row["authority_matched_code"] = authority.get("matched_code", "")
            row["authority_official_url"] = authority.get("official_detail_url", "")
            row["authority_replacement_relation"] = authority.get(
                "replacement_relation", ""
            )
            row["authority_evidence_path"] = authority.get(
                "resolution_evidence_path", ""
            )
            row["authority_evidence_sha256"] = authority.get(
                "resolution_evidence_sha256", ""
            )
        else:
            row["authority_status"] = "NOT_APPLICABLE_SOURCE_KIND"
            row["authority_lifecycle_state"] = "NOT_APPLICABLE_SOURCE_KIND"
            row["authority_verification_status"] = "NOT_APPLICABLE_SOURCE_KIND"
            row["authority_matched_code"] = ""
            row["authority_official_url"] = ""
            row["authority_replacement_relation"] = ""
            row["authority_evidence_path"] = ""
            row["authority_evidence_sha256"] = ""
        merged.append(row)

    counts = Counter(row["authority_status"] for row in merged)
    summary = {
        "schema": "equipment-executable-source-inventory-authority-merge-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_count": len(merged),
        "standard_source_count": sum(
            row.get("source_kind") in standard_kinds for row in merged
        ),
        "authority_status_counts": dict(sorted(counts.items())),
        "unresolved_standard_count": sum(
            row.get("source_kind") in standard_kinds
            and row.get("authority_status") == "UNRESOLVED"
            for row in merged
        ),
        "hash_join_mismatch_count": 0,
    }
    return merged, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-inventory", type=Path, required=True)
    parser.add_argument("--authority-status", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    rows, summary = merge_inventory(
        args.source_inventory.resolve(), args.authority_status.resolve()
    )
    fields = list(rows[0])
    write_csv(args.out_dir / "source_inventory_resolved.csv", rows, fields)
    (args.out_dir / "source_inventory_resolved_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
