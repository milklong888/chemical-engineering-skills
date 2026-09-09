#!/usr/bin/env python3
"""Query the executable standards database without source-document access."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path


def install_source_access_guard(denied_prefix: str) -> None:
    prefix = os.path.normcase(os.path.abspath(denied_prefix))

    def guard(event: str, args: tuple) -> None:
        if event != "open" or not args:
            return
        candidate = args[0]
        if not isinstance(candidate, (str, bytes, os.PathLike)):
            return
        path = os.path.normcase(os.path.abspath(os.fsdecode(candidate)))
        if path == prefix or path.startswith(prefix + os.sep):
            raise PermissionError(f"production query attempted forbidden source access: {path}")

    sys.addaudithook(guard)


class ExecutableStandardStore:
    def __init__(self, database: Path):
        self.database = database
        self.connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
        self.connection.row_factory = sqlite3.Row
        self._cache: dict[tuple, list[dict]] = {}

    def close(self) -> None:
        self.connection.close()

    def query(self, family: str, dataset_id: str = "", record_type: str = "") -> list[dict]:
        key = (family, dataset_id, record_type)
        if key in self._cache:
            return self._cache[key]
        clauses = ["equipment_family = ?"]
        values: list[str] = [family]
        if dataset_id:
            clauses.append("dataset_id = ?")
            values.append(dataset_id)
        if record_type:
            clauses.append("source_record_type = ?")
            values.append(record_type)
        sql = "SELECT * FROM standard_records WHERE " + " AND ".join(clauses) + " ORDER BY dataset_id, record_id"
        result = [dict(row) for row in self.connection.execute(sql, values)]
        self._cache[key] = result
        return result

    def query_figures(
        self,
        family: str,
        dataset_id: str = "",
        figure_id: str = "",
        record_kind: str = "",
    ) -> list[dict]:
        key = ("figure", family, dataset_id, figure_id, record_kind)
        if key in self._cache:
            return self._cache[key]
        clauses = ["equipment_family = ?"]
        values: list[str] = [family]
        if dataset_id:
            clauses.append("dataset_id = ?")
            values.append(dataset_id)
        if figure_id:
            clauses.append("figure_id = ?")
            values.append(figure_id)
        if record_kind:
            clauses.append("record_kind = ?")
            values.append(record_kind)
        sql = (
            "SELECT * FROM figure_records WHERE "
            + " AND ".join(clauses)
            + " ORDER BY dataset_id, figure_id, figure_record_id"
        )
        result = [dict(row) for row in self.connection.execute(sql, values)]
        self._cache[key] = result
        return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--family", required=True)
    parser.add_argument("--dataset-id", default="")
    parser.add_argument("--record-type", default="")
    parser.add_argument("--scope", choices=("standard", "figure", "all"), default="standard")
    parser.add_argument("--figure-id", default="")
    parser.add_argument("--record-kind", default="")
    parser.add_argument("--deny-source-root", default="")
    parser.add_argument("--deny-image-root", default="")
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()
    if args.deny_source_root:
        install_source_access_guard(args.deny_source_root)
    if args.deny_image_root:
        install_source_access_guard(args.deny_image_root)
    store = ExecutableStandardStore(args.db.resolve())
    try:
        standard_rows = (
            store.query(args.family, args.dataset_id, args.record_type)
            if args.scope in {"standard", "all"}
            else []
        )
        figure_rows = (
            store.query_figures(
                args.family, args.dataset_id, args.figure_id, args.record_kind
            )
            if args.scope in {"figure", "all"}
            else []
        )
    finally:
        store.close()
    rows = standard_rows if args.scope == "standard" else figure_rows
    payload = {
        "scope": args.scope,
        "row_count": len(standard_rows) + len(figure_rows),
        "standard_row_count": len(standard_rows),
        "figure_row_count": len(figure_rows),
        "vision_capability": False,
        "denied_source_root": bool(args.deny_source_root),
        "denied_image_root": bool(args.deny_image_root),
    }
    if not args.summary_only:
        if args.scope == "standard":
            payload["records"] = standard_rows
        elif args.scope == "figure":
            payload["records"] = figure_rows
        else:
            payload["standard_records"] = standard_rows
            payload["figure_records"] = figure_rows
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
