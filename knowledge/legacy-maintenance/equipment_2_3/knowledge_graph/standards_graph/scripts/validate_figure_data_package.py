#!/usr/bin/env python3
"""Validate that a figure package is usable without image or vision access."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ALIASES = {
    "QUANTITATIVE_CURVE": "QUANTITATIVE_CURVE_DATAIZED",
    "DIMENSION_STRUCTURE": "DIMENSION_STRUCTURE_DATAIZED",
    "PROCESS_LOGIC": "PROCESS_LOGIC_DATAIZED",
    "SYMBOL_ICON": "SYMBOL_ICON_DATAIZED",
}
TERMINAL_CLASSES = {
    "QUANTITATIVE_CURVE_DATAIZED",
    "DIMENSION_STRUCTURE_DATAIZED",
    "PROCESS_LOGIC_DATAIZED",
    "SYMBOL_ICON_DATAIZED",
    "METHOD_ONLY",
    "NOT_APPLICABLE",
    "SOURCE_UNREADABLE_BLOCKED",
    "OBSOLETE_FORBIDDEN",
    "FORBIDDEN_TRANSFER",
}
RECORD_REQUIRED = TERMINAL_CLASSES - {
    "NOT_APPLICABLE",
    "SOURCE_UNREADABLE_BLOCKED",
    "OBSOLETE_FORBIDDEN",
    "FORBIDDEN_TRANSFER",
}


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest().upper()


def validate_package(
    source_figures_csv: Path,
    terminal_audit_csv: Path,
    figure_records_csv: Path,
    package_root: Path,
) -> dict:
    expected = read_csv(source_figures_csv)
    audit = read_csv(terminal_audit_csv)
    records = read_csv(figure_records_csv)
    expected_ids = {row.get("figure_id", "") for row in expected}
    audit_ids = [row.get("figure_id", "") for row in audit]
    failures: list[str] = []
    if len(audit_ids) != len(set(audit_ids)):
        failures.append("duplicate figure_id in terminal audit")
    if set(audit_ids) != expected_ids:
        failures.append("terminal audit figure-id set differs from source figures.csv")

    expected_by_id = {row.get("figure_id", ""): row for row in expected}
    records_by_figure: dict[str, list[dict]] = defaultdict(list)
    record_keys: set[str] = set()
    for record in records:
        record_id = str(record.get("figure_record_id") or "")
        if not record_id or record_id in record_keys:
            failures.append("blank or duplicate figure_record_id")
        record_keys.add(record_id)
        figure_id = str(record.get("figure_id") or "")
        if figure_id not in expected_ids:
            failures.append(f"record references unknown figure_id: {figure_id}")
        records_by_figure[figure_id].append(record)
        try:
            payload = json.loads(str(record.get("payload_json") or "{}"))
            if not isinstance(payload, (dict, list)):
                raise ValueError
        except (json.JSONDecodeError, ValueError):
            failures.append(f"invalid payload_json: {record_id}")

    class_counts: Counter = Counter()
    blocked_count = 0
    for row in audit:
        figure_id = str(row.get("figure_id") or "")
        terminal = ALIASES.get(
            str(row.get("terminal_class") or "").upper(),
            str(row.get("terminal_class") or "").upper(),
        )
        class_counts[terminal] += 1
        if terminal not in TERMINAL_CLASSES:
            failures.append(f"nonterminal or invalid class: {figure_id}:{terminal}")
        if str(row.get("needs_review") or "").casefold() == "true":
            failures.append(f"needs_review remains: {figure_id}")
        if terminal in RECORD_REQUIRED and not records_by_figure.get(figure_id):
            failures.append(f"machine record missing for {figure_id}:{terminal}")
        declared_count = str(row.get("structured_record_count") or "").strip()
        if declared_count:
            try:
                if int(declared_count) != len(records_by_figure.get(figure_id, [])):
                    failures.append(f"structured record count mismatch: {figure_id}")
            except ValueError:
                failures.append(f"invalid structured record count: {figure_id}")
        expected_row = expected_by_id.get(figure_id, {})
        image_path = package_root / str(expected_row.get("image_path") or "")
        if not image_path.is_file():
            failures.append(f"offline audit image missing: {figure_id}")
        else:
            declared_hash = str(row.get("image_sha256") or "").upper()
            if not declared_hash or declared_hash != sha256_path(image_path):
                failures.append(f"offline audit image hash mismatch: {figure_id}")
        if terminal == "SOURCE_UNREADABLE_BLOCKED":
            blocked_count += 1

    kinds_by_figure = {
        figure_id: {str(record.get("record_kind") or "").casefold() for record in group}
        for figure_id, group in records_by_figure.items()
    }
    for row in audit:
        figure_id = str(row.get("figure_id") or "")
        terminal = ALIASES.get(
            str(row.get("terminal_class") or "").upper(),
            str(row.get("terminal_class") or "").upper(),
        )
        kinds = kinds_by_figure.get(figure_id, set())
        if terminal == "QUANTITATIVE_CURVE_DATAIZED":
            axis_count = sum(kind.startswith("axis") or kind == "axis" for kind in kinds)
            curve_data = bool(kinds & {"point", "curve_point", "segment", "relation"})
            if axis_count < 1 or not curve_data:
                failures.append(f"curve axes/data incomplete: {figure_id}")
            if not any(str(record.get("error_bound") or "").strip() for record in records_by_figure[figure_id]):
                failures.append(f"curve error bound missing: {figure_id}")
        elif terminal == "PROCESS_LOGIC_DATAIZED" and not (
            "node" in kinds and "edge" in kinds
        ):
            failures.append(f"process nodes/edges incomplete: {figure_id}")
        elif terminal == "DIMENSION_STRUCTURE_DATAIZED" and not (
            kinds & {"object", "component", "dimension", "relation", "connection"}
        ):
            failures.append(f"structure objects/relations incomplete: {figure_id}")
        elif terminal == "SYMBOL_ICON_DATAIZED" and not (
            kinds & {"symbol", "semantic", "object"}
        ):
            failures.append(f"symbol semantics missing: {figure_id}")

    return {
        "schema": "equipment-figure-data-package-validation-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_figure_count": len(expected),
        "terminal_audit_count": len(audit),
        "structured_record_count": len(records),
        "terminal_class_counts": dict(sorted(class_counts.items())),
        "source_unreadable_blocked_count": blocked_count,
        "failure_count": len(failures),
        "failures": failures,
        "vision_capability": False,
        "source_image_runtime_access": "FORBIDDEN",
        "validation": "PASS" if not failures else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-figures", type=Path, required=True)
    parser.add_argument("--terminal-audit", type=Path, required=True)
    parser.add_argument("--figure-records", type=Path, required=True)
    parser.add_argument("--package-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = validate_package(
        args.source_figures.resolve(),
        args.terminal_audit.resolve(),
        args.figure_records.resolve(),
        args.package_root.resolve(),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["validation"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
