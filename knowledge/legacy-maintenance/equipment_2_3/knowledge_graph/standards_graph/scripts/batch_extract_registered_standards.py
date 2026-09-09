#!/usr/bin/env python3
"""Resume-safe mechanical extraction of registered standards, one PDF per process."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def completed(package: Path) -> bool:
    status_path = package / "status.json"
    if not status_path.is_file():
        return False
    status = json.loads(status_path.read_text(encoding="utf-8"))
    return status.get("status") in {"PASS", "PASS_WITH_REVIEW"}


def recommended_dpi(inventory: dict[str, str], default_dpi: int) -> int:
    pages = int(inventory.get("page_count", 0) or 0)
    ocr_pages = int(inventory.get("needs_ocr_pages", 0) or 0)
    if ocr_pages <= 3:
        return 240
    if pages >= 400:
        return min(default_dpi, 220)
    if pages >= 200:
        return min(default_dpi, 240)
    return default_dpi


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    graph_root = Path(__file__).resolve().parents[1]
    source_layer = graph_root / "source_layer"
    parser.add_argument("--registry", type=Path, default=source_layer / "provenance" / "document_registry.csv")
    parser.add_argument("--inventory", type=Path, default=source_layer / "inventory" / "documents.csv")
    parser.add_argument("--family", action="append", default=[])
    parser.add_argument("--doc-id", action="append", default=[])
    parser.add_argument("--exclude-doc-id", action="append", default=[])
    parser.add_argument("--max-documents", type=int)
    parser.add_argument("--workers-per-doc", type=int, default=2)
    parser.add_argument("--ocr-dpi", type=int, default=300)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--skip-index", action="store_true")
    args = parser.parse_args()

    registry = read_csv(args.registry.resolve())
    inventory = {row["doc_id"]: row for row in read_csv(args.inventory.resolve())}
    documents_root = source_layer / "documents"
    selected = []
    for row in registry:
        if row.get("duplicate_of"):
            continue
        if args.family and row["family"] not in set(args.family):
            continue
        if args.doc_id and row["doc_id"] not in set(args.doc_id):
            continue
        if row["doc_id"] in set(args.exclude_doc_id):
            continue
        if not args.force and completed(documents_root / row["doc_id"]):
            continue
        selected.append(row)
    selected.sort(key=lambda row: (int(inventory.get(row["doc_id"], {}).get("needs_ocr_pages", 0) or 0), int(inventory.get(row["doc_id"], {}).get("page_count", 0) or 0)))
    if args.max_documents is not None:
        selected = selected[: args.max_documents]

    log_path = source_layer / "batch_extraction_log.jsonl"
    failures = []
    print(f"selected={len(selected)}")
    for index, row in enumerate(selected, 1):
        doc_id = row["doc_id"]
        dpi = recommended_dpi(inventory.get(doc_id, {}), args.ocr_dpi)
        command = [
            sys.executable,
            str(Path(__file__).resolve().with_name("standards_kg.py")),
            "extract",
            doc_id,
            "--workers",
            str(args.workers_per_doc),
            "--ocr-dpi",
            str(dpi),
        ]
        if args.force:
            command.append("--force")
        print(f"[{index}/{len(selected)}] {doc_id} dpi={dpi}", flush=True)
        started = datetime.now(timezone.utc)
        result = subprocess.run(command, cwd=graph_root.parents[2], text=True, encoding="utf-8", errors="replace")
        record = {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "doc_id": doc_id,
            "ocr_dpi": dpi,
            "returncode": result.returncode,
            "elapsed_seconds": round((datetime.now(timezone.utc) - started).total_seconds(), 3),
        }
        with log_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
        if result.returncode != 0:
            failures.append(doc_id)
            if not args.continue_on_error:
                break

    if not args.skip_index:
        subprocess.run(
            [sys.executable, str(Path(__file__).resolve().with_name("standards_kg.py")), "index", "--allow-incomplete"],
            cwd=graph_root.parents[2],
        )
        subprocess.run(
            [sys.executable, str(Path(__file__).resolve().with_name("standards_kg.py")), "validate", "--allow-incomplete"],
            cwd=graph_root.parents[2],
        )
    print(json.dumps({"selected": len(selected), "failures": failures, "log": str(log_path)}, ensure_ascii=False, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
