from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def same(value: str, query: str | None) -> bool:
    return query is None or value.casefold() == query.casefold()


def parse_number(value: str) -> float:
    return float(value.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description="Query the generated Aspen BKP field/unit catalog without an LLM.")
    parser.add_argument("--catalog-dir", type=Path, required=True)
    parser.add_argument("--field")
    parser.add_argument("--in-units-field")
    parser.add_argument("--scope", choices=["block", "stream"])
    parser.add_argument("--unit")
    parser.add_argument("--dimension")
    parser.add_argument("--convert", type=float, dest="convert_value")
    parser.add_argument("--from-unit")
    parser.add_argument("--to-unit")
    args = parser.parse_args()

    root = args.catalog_dir.expanduser().resolve()
    usage = read_csv(root / "aspen_bkp_field_unit_usage.csv")
    fields = [
        row for row in usage
        if same(row.get("field", ""), args.field)
        and same(row.get("scope", ""), args.scope)
        and (
            args.unit is None
            or same(row.get("unit_string_as_written", ""), args.unit)
            or same(row.get("effective_unit", ""), args.unit)
            or same(row.get("normalized_unit", ""), args.unit)
        )
    ]

    in_units_catalog_path = root / "aspen_in_units_field_catalog.csv"
    in_units_fields = read_csv(in_units_catalog_path) if in_units_catalog_path.is_file() else []
    unit_set_field_results = [
        row for row in in_units_fields
        if same(row.get("field", ""), args.in_units_field)
        and (args.unit is None or same(row.get("unit", ""), args.unit))
    ]
    bridge_path = root / "equipment_field_to_in_units_key.csv"
    bridges = read_csv(bridge_path) if bridge_path.is_file() else []
    field_bridge_results = [
        row for row in bridges
        if (
            args.field is None
            or same(row.get("raw_equipment_field", ""), args.field)
            or same(row.get("raw_equipment_field", "").split(".")[-1], args.field)
        )
        and same(row.get("in_units_field", ""), args.in_units_field)
    ]

    matrix = read_csv(root / "aspen_unit_conversion_matrix.csv")
    conversions = [
        row for row in matrix
        if same(row.get("dimension", ""), args.dimension)
        and same(row.get("source_unit", ""), args.from_unit)
        and same(row.get("target_unit", ""), args.to_unit)
    ]

    converted: dict[str, Any] | None = None
    if args.convert_value is not None:
        if not args.from_unit or not args.to_unit:
            raise SystemExit("--convert requires --from-unit and --to-unit")
        exact = [
            row for row in matrix
            if same(row.get("source_unit", ""), args.from_unit)
            and same(row.get("target_unit", ""), args.to_unit)
        ]
        if len(exact) != 1:
            raise SystemExit(f"conversion route not found or ambiguous: {args.from_unit} -> {args.to_unit}")
        row = exact[0]
        factor = parse_number(row["factor"])
        offset = parse_number(row["offset"])
        answer = args.convert_value * factor + offset
        calculation = f"{args.convert_value}×{factor}"
        if offset > 0:
            calculation += f"+{offset}"
        elif offset < 0:
            calculation += str(offset)
        converted = {
            "source_value": args.convert_value,
            "source_unit": row["source_unit"],
            "target_unit": row["target_unit"],
            "factor": factor,
            "offset": offset,
            "answer": answer,
            "equation_chain": (
                f"{row['equation_template']}={calculation}={answer} {row['target_unit']}"
            ),
            "basis": row["basis"],
        }

    print(json.dumps({
        "schema": "aspen-bkp-unit-catalog-query-v1",
        "catalog_dir": str(root),
        "field_results": fields,
        "unit_set_field_results": unit_set_field_results,
        "field_bridge_results": field_bridge_results,
        "conversion_results": conversions,
        "converted": converted,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
