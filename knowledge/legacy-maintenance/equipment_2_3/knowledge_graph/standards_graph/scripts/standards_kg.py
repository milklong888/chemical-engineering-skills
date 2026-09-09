#!/usr/bin/env python3
"""Single mechanical entry point for standards extraction, indexing, validation, and query."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
GRAPH_ROOT = SCRIPT_DIR.parent
WORKSPACE = GRAPH_ROOT.parents[2]
SOURCE_ROOT = WORKSPACE / "设计标准（反应器、塔、换热器、容器等）"
SOURCE_LAYER = GRAPH_ROOT / "source_layer"
REGISTRY = SOURCE_LAYER / "provenance" / "document_registry.csv"
INVENTORY_PAGES = SOURCE_LAYER / "inventory" / "pages.csv"


def run(script: str, arguments: list[str]) -> int:
    return subprocess.call([sys.executable, str(SCRIPT_DIR / script), *arguments], cwd=WORKSPACE)


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "query" and sys.argv[2] in {"-h", "--help"}:
        return run("query_standard_knowledge.py", ["--help"])
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    query = subparsers.add_parser("query", help="retrieve text/table/figure evidence")
    query.add_argument("arguments", nargs=argparse.REMAINDER)

    extract = subparsers.add_parser("extract", help="extract exactly one registered PDF")
    extract.add_argument("doc_id")
    extract.add_argument("--workers", type=int, default=2)
    extract.add_argument("--ocr-dpi", type=int, default=240)
    extract.add_argument("--force", action="store_true")

    index = subparsers.add_parser("index", help="rebuild the SQLite/CSV catalogs")
    index.add_argument("--allow-incomplete", action="store_true")

    validate = subparsers.add_parser("validate", help="validate provenance, assets, and regression queries")
    validate.add_argument("--allow-incomplete", action="store_true")
    validate.add_argument("--json", action="store_true")

    subparsers.add_parser("status", help="print inventory, search-index, and validation summaries")
    args = parser.parse_args()

    if args.command == "query":
        if not args.arguments:
            parser.error("query requires a search expression")
        return run("query_standard_knowledge.py", args.arguments)
    if args.command == "extract":
        forwarded = [
            "--source-root", str(SOURCE_ROOT),
            "--registry", str(REGISTRY),
            "--inventory-pages", str(INVENTORY_PAGES),
            "--out-root", str(SOURCE_LAYER),
            "--doc-id", args.doc_id,
            "--workers", str(args.workers),
            "--ocr-dpi", str(args.ocr_dpi),
        ]
        if args.force:
            forwarded.append("--force")
        return run("extract_standard_document.py", forwarded)
    if args.command == "index":
        forwarded = ["--source-root", str(SOURCE_ROOT), "--registry", str(REGISTRY), "--source-layer", str(SOURCE_LAYER)]
        if args.allow_incomplete:
            forwarded.append("--allow-incomplete")
        return run("build_standard_search_index.py", forwarded)
    if args.command == "validate":
        forwarded = ["--source-root", str(SOURCE_ROOT), "--registry", str(REGISTRY), "--source-layer", str(SOURCE_LAYER)]
        if args.allow_incomplete:
            forwarded.append("--allow-incomplete")
        if args.json:
            forwarded.append("--json")
        return run("validate_standard_source_layer.py", forwarded)
    if args.command == "status":
        files = [
            SOURCE_LAYER / "inventory" / "inventory_summary.json",
            SOURCE_LAYER / "indexes" / "search_index_summary.json",
            SOURCE_LAYER / "validation_report.json",
        ]
        for path in files:
            print(f"\n## {path.name}")
            if path.is_file():
                print(json.dumps(json.loads(path.read_text(encoding="utf-8")), ensure_ascii=False, indent=2))
            else:
                print("MISSING")
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
