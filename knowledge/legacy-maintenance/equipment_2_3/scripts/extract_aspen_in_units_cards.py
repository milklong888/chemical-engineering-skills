from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import re
import shlex
import sys
from pathlib import Path
from typing import Any


SCHEMA = "aspen-in-units-card-catalog-v1"
CARD_START = re.compile(r"^(?P<indent>\s*)IN-UNITS\b", re.IGNORECASE)
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PACKAGE_ROOT / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from aspen_com_import import RAW_FIELD_TO_IN_UNITS_KEY as RAW_FIELD_KEY_ONLY  # noqa: E402


# The runtime registry is keyed by the raw Aspen field name.  Add scope here
# only to make the generated audit bridge unambiguous to callers.
RAW_FIELD_TO_IN_UNITS_KEY = {
    f"{scope}.{field}": unit_key
    for field, unit_key in RAW_FIELD_KEY_ONLY.items()
    for scope in (
        ["stream"] if field in {
            "TEMP_OUT", "PRES_OUT", "MASSFLMX", "VOLFLMX", "VOLFLMX_LIQ",
            "VOLFLMX_GAS", "density_kg_m3", "molecular_weight",
        } else ["block"]
    )
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def discover_inputs(inputs: list[Path]) -> list[Path]:
    found: set[Path] = set()
    for raw in inputs:
        path = raw.expanduser().resolve()
        if path.is_file():
            found.add(path)
        elif path.is_dir():
            found.update(item.resolve() for item in path.rglob("after_run_or_current.inp"))
        else:
            raise FileNotFoundError(path)
    return sorted(found, key=lambda item: str(item).casefold())


def logical_card(lines: list[str], start: int) -> tuple[str, int]:
    parts: list[str] = []
    index = start
    while index < len(lines):
        text = lines[index].strip()
        continued = text.endswith("&")
        if continued:
            text = text[:-1].rstrip()
        parts.append(text)
        index += 1
        if not continued:
            break
    return " ".join(part for part in parts if part), index


def parse_card(card: str) -> tuple[str, dict[str, str]]:
    tokens = shlex.split(card, posix=True)
    if len(tokens) < 2 or tokens[0].upper() != "IN-UNITS":
        raise ValueError(f"invalid IN-UNITS card: {card}")
    unit_set = tokens[1]
    fields: dict[str, str] = {}
    for token in tokens[2:]:
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        key = key.strip().upper()
        value = value.strip()
        if not key or not value:
            continue
        if key in fields and fields[key] != value:
            raise ValueError(f"conflicting IN-UNITS field in one card: {key}")
        fields[key] = value
    return unit_set, fields


def nearest_context(lines: list[str], start: int) -> str:
    for index in range(start - 1, -1, -1):
        text = lines[index].strip()
        if not text or text.startswith(";") or text.startswith("&"):
            continue
        if not lines[index][:1].isspace():
            return text[:240]
    return "FILE_GLOBAL"


def extract_cards(path: Path) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    cards: list[dict[str, Any]] = []
    index = 0
    while index < len(lines):
        match = CARD_START.match(lines[index])
        if match is None:
            index += 1
            continue
        card, next_index = logical_card(lines, index)
        unit_set, fields = parse_card(card)
        indent = len(match.group("indent").replace("\t", "    "))
        cards.append({
            "line_number": index + 1,
            "indent": indent,
            "scope": "GLOBAL" if indent == 0 else "LOCAL_CARD",
            "context": "FILE_GLOBAL" if indent == 0 else nearest_context(lines, index),
            "unit_set": unit_set,
            "fields": fields,
            "field_count": len(fields),
            "raw_card": card,
        })
        index = next_index
    return cards


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build(inputs: list[Path], output_dir: Path) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    cards_out: list[dict[str, Any]] = []
    field_rows: list[dict[str, Any]] = []
    global_rows: list[dict[str, Any]] = []
    aggregate: dict[tuple[str, str], dict[str, Any]] = {}

    for path in inputs:
        cards = extract_cards(path)
        files.append({
            "input_path": str(path),
            "input_sha256": sha256_file(path),
            "card_count": len(cards),
            "global_card_count": sum(1 for card in cards if card["scope"] == "GLOBAL"),
        })
        for card_index, card in enumerate(cards, 1):
            card_id = f"{path.parent.name}:{card_index}"
            cards_out.append({
                "card_id": card_id,
                "input_path": str(path),
                **card,
            })
            if card["scope"] == "GLOBAL":
                global_rows.append({
                    "case_directory": path.parent.name,
                    "input_path": str(path),
                    "line_number": card["line_number"],
                    "unit_set": card["unit_set"],
                    "field_count": card["field_count"],
                    "fields_json": json.dumps(card["fields"], ensure_ascii=False, sort_keys=True),
                })
            for field, unit in sorted(card["fields"].items()):
                field_rows.append({
                    "card_id": card_id,
                    "case_directory": path.parent.name,
                    "scope": card["scope"],
                    "context": card["context"],
                    "unit_set": card["unit_set"],
                    "field": field,
                    "unit": unit,
                    "line_number": card["line_number"],
                    "input_path": str(path),
                })
                key = (field, unit)
                item = aggregate.setdefault(key, {
                    "field": field,
                    "unit": unit,
                    "card_count": 0,
                    "global_card_count": 0,
                    "local_card_count": 0,
                    "cases": set(),
                    "unit_sets": set(),
                })
                item["card_count"] += 1
                item["global_card_count"] += int(card["scope"] == "GLOBAL")
                item["local_card_count"] += int(card["scope"] != "GLOBAL")
                item["cases"].add(path.parent.name)
                item["unit_sets"].add(card["unit_set"])

    aggregate_rows = [
        {
            "field": item["field"],
            "unit": item["unit"],
            "card_count": item["card_count"],
            "global_card_count": item["global_card_count"],
            "local_card_count": item["local_card_count"],
            "case_count": len(item["cases"]),
            "unit_sets": " | ".join(sorted(item["unit_sets"])),
            "sample_cases": " | ".join(sorted(item["cases"])[:10]),
        }
        for item in sorted(aggregate.values(), key=lambda row: (row["field"], row["unit"]))
    ]
    bridge_rows = [
        {
            "raw_equipment_field": raw_field,
            "in_units_field": unit_field,
            "observed_units": " | ".join(sorted({
                row["unit"] for row in aggregate_rows if row["field"] == unit_field
            })),
            "mapping_status": "DETERMINISTIC_FALLBACK_AUDIT_ONLY",
            "live_unit_string_priority": "IHNode.UnitString first",
        }
        for raw_field, unit_field in sorted(RAW_FIELD_TO_IN_UNITS_KEY.items())
    ]

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "aspen_in_units_cards.json").write_text(
        json.dumps({"schema": SCHEMA, "files": files, "cards": cards_out}, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_csv(output_dir / "aspen_in_units_field_occurrences.csv", field_rows, [
        "card_id", "case_directory", "scope", "context", "unit_set", "field", "unit", "line_number", "input_path",
    ])
    write_csv(output_dir / "aspen_in_units_field_catalog.csv", aggregate_rows, [
        "field", "unit", "card_count", "global_card_count", "local_card_count", "case_count", "unit_sets", "sample_cases",
    ])
    write_csv(output_dir / "aspen_global_unit_sets.csv", global_rows, [
        "case_directory", "input_path", "line_number", "unit_set", "field_count", "fields_json",
    ])
    write_csv(output_dir / "equipment_field_to_in_units_key.csv", bridge_rows, [
        "raw_equipment_field", "in_units_field", "observed_units", "mapping_status", "live_unit_string_priority",
    ])

    summary = {
        "schema": SCHEMA,
        "input_file_count": len(files),
        "card_count": len(cards_out),
        "global_card_count": len(global_rows),
        "unique_unit_set_names": sorted({row["unit_set"] for row in cards_out}),
        "unique_field_names": sorted({row["field"] for row in aggregate_rows}),
        "unique_field_count": len({row["field"] for row in aggregate_rows}),
        "field_unit_pair_count": len(aggregate_rows),
        "equipment_bridge_count": len(bridge_rows),
        "files": {},
    }
    for name in (
        "aspen_in_units_cards.json",
        "aspen_in_units_field_occurrences.csv",
        "aspen_in_units_field_catalog.csv",
        "aspen_global_unit_sets.csv",
        "equipment_field_to_in_units_key.csv",
    ):
        artifact = output_dir / name
        summary["files"][name] = {
            "sha256": sha256_file(artifact),
            "size_bytes": artifact.stat().st_size,
        }
    (output_dir / "aspen_in_units_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract IN-UNITS unit-set field names and values from Aspen INP exports created from BKP files."
    )
    parser.add_argument("--input", action="append", type=Path, required=True, help="INP file or directory; repeatable.")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    inputs = discover_inputs(args.input)
    if not inputs:
        raise SystemExit("no after_run_or_current.inp files found")
    summary = build(inputs, args.output_dir.expanduser().resolve())
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
