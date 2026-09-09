from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import aspen_equipment_derivation as derivation


SCHEMA = "aspen-bkp-field-unit-catalog-v1"


# Each definition maps a unit to a common base by:
#     base_value = source_value * factor_to_base + offset_to_base
# The catalog generator expands these definitions into a deterministic
# pairwise matrix.  Unknown dimensions are catalogued but never converted.
COMMON_UNIT_GROUPS: dict[str, dict[str, Any]] = {
    "temperature": {
        "base_unit": "K",
        "units": {
            "C": (1.0, 273.15),
            "K": (1.0, 0.0),
        },
        "basis": "K = C + 273.15",
    },
    "pressure": {
        "base_unit": "Pa",
        "units": {
            "Pa": (1.0, 0.0),
            "kPa": (1_000.0, 0.0),
            "MPa": (1_000_000.0, 0.0),
            "bar": (100_000.0, 0.0),
            "atm": (101_325.0, 0.0),
        },
        "basis": "1 bar = 100000 Pa; 1 atm = 101325 Pa",
    },
    "mass_flow": {
        "base_unit": "kg/s",
        "units": {
            "kg/s": (1.0, 0.0),
            "kg/h": (1.0 / 3600.0, 0.0),
            "t/h": (1000.0 / 3600.0, 0.0),
        },
        "basis": "1 h = 3600 s; 1 t = 1000 kg",
    },
    "volumetric_flow": {
        "base_unit": "m3/s",
        "units": {
            "m3/s": (1.0, 0.0),
            "m3/h": (1.0 / 3600.0, 0.0),
            "L/min": (0.001 / 60.0, 0.0),
        },
        "basis": "1 L = 0.001 m3; 1 min = 60 s; 1 h = 3600 s",
    },
    "density": {
        "base_unit": "kg/m3",
        "units": {
            "kg/m3": (1.0, 0.0),
            "g/cm3": (1000.0, 0.0),
        },
        "basis": "1 g/cm3 = 1000 kg/m3",
    },
    "power_or_heat_rate": {
        "base_unit": "W",
        "units": {
            "W": (1.0, 0.0),
            "kW": (1000.0, 0.0),
            "MW": (1_000_000.0, 0.0),
            "cal/s": (4.184, 0.0),
            "kcal/h": (4184.0 / 3600.0, 0.0),
            "Gcal/h": (4.184e9 / 3600.0, 0.0),
        },
        "basis": "thermochemical calorie: 1 cal = 4.184 J",
    },
    "length": {
        "base_unit": "m",
        "units": {
            "m": (1.0, 0.0),
            "mm": (0.001, 0.0),
        },
        "basis": "1 mm = 0.001 m",
    },
    "dimensionless": {
        "base_unit": "fraction",
        "units": {
            "fraction": (1.0, 0.0),
            "percent": (0.01, 0.0),
            "-": (1.0, 0.0),
        },
        "basis": "1 percent = 0.01 fraction; '-' is dimensionless and is not automatically percent",
    },
    "specific_energy_or_head": {
        "base_unit": "J/kg",
        "units": {
            "J/kg": (1.0, 0.0),
            "m": (9.80665, 0.0),
            "m-kgf/kg": (9.80665, 0.0),
        },
        "basis": "head conversion at standard gravity g0 = 9.80665 m/s2",
    },
    "area": {
        "base_unit": "m2",
        "units": {"m2": (1.0, 0.0)},
        "basis": "SI area identity",
    },
    "volume": {
        "base_unit": "m3",
        "units": {"m3": (1.0, 0.0)},
        "basis": "SI volume identity",
    },
    "molecular_weight": {
        "base_unit": "kg/kmol",
        "units": {"kg/kmol": (1.0, 0.0)},
        "basis": "Aspen molecular-weight basis used by the equipment export",
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def discover_exports(inputs: list[Path]) -> list[Path]:
    found: set[Path] = set()
    for raw in inputs:
        path = raw.expanduser().resolve()
        if path.is_file():
            found.add(path)
        elif path.is_dir():
            found.update(item.resolve() for item in path.rglob("aspen_equipment_export.json"))
        else:
            raise FileNotFoundError(path)
    return sorted(found, key=lambda item: str(item).casefold())


def load_export(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict) or value.get("schema") != "aspen-equipment-export-v1":
        raise ValueError(f"not an aspen-equipment-export-v1 file: {path}")
    return value


def field_target_map() -> dict[tuple[str, str], tuple[str, str]]:
    result: dict[tuple[str, str], tuple[str, str]] = {}
    for scope, aliases in (("stream", derivation.STREAM_ALIASES), ("block", derivation.BLOCK_ALIASES)):
        for canonical_field, candidates in aliases.items():
            target_unit = derivation.CANONICAL_UNITS[canonical_field]
            for source_field, _declared_unit, _raw in candidates:
                result[(scope, source_field)] = (canonical_field, target_unit)
    return result


def conversion_probe(source_unit: str, target_unit: str) -> dict[str, Any]:
    if not source_unit or not target_unit:
        return {
            "supported": False,
            "factor": None,
            "offset": None,
            "transform": None,
        }
    try:
        at_zero, transform_zero = derivation.convert(0.0, source_unit, target_unit)
        at_one, transform_one = derivation.convert(1.0, source_unit, target_unit)
    except (TypeError, ValueError):
        return {
            "supported": False,
            "factor": None,
            "offset": None,
            "transform": None,
        }
    return {
        "supported": True,
        "factor": at_one - at_zero,
        "offset": at_zero,
        "transform": transform_one if transform_one != "identity" else transform_zero,
    }


def format_number(value: float) -> str:
    if value == 0:
        return "0"
    return f"{value:.15g}"


def equation_template(source: str, target: str, factor: float, offset: float) -> str:
    if factor == 1.0 and offset == 0.0:
        return f"value_{target}=value_{source}"
    expression = f"value_{source}×{format_number(factor)}"
    if offset > 0:
        expression += f"+{format_number(offset)}"
    elif offset < 0:
        expression += format_number(offset)
    return f"value_{target}={expression}"


def matrix_rows(observed_counts: collections.Counter[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for dimension, group in COMMON_UNIT_GROUPS.items():
        units = group["units"]
        for source_unit, (source_factor, source_offset) in units.items():
            for target_unit, (target_factor, target_offset) in units.items():
                factor = source_factor / target_factor
                offset = (source_offset - target_offset) / target_factor
                direct = conversion_probe(source_unit, target_unit)
                rows.append({
                    "dimension": dimension,
                    "source_unit": source_unit,
                    "target_unit": target_unit,
                    "factor": factor,
                    "offset": offset,
                    "equation_template": equation_template(source_unit, target_unit, factor, offset),
                    "basis": group["basis"],
                    "source_observed_count": observed_counts[source_unit],
                    "target_observed_count": observed_counts[target_unit],
                    "core_derivation_direct_support": direct["supported"],
                    "core_transform": direct["transform"],
                })
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_catalog(exports: list[Path], output_dir: Path) -> dict[str, Any]:
    targets = field_target_map()
    declared_rows: list[dict[str, Any]] = []
    usage: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    source_rows: list[dict[str, Any]] = []
    observed_counts: collections.Counter[str] = collections.Counter()

    for path in exports:
        bundle = load_export(path)
        case = bundle.get("case") if isinstance(bundle.get("case"), dict) else {}
        case_id = str(case.get("case_id") or path.parent.name)
        source_rows.append({
            "case_id": case_id,
            "export_path": str(path),
            "export_sha256": sha256_file(path),
            "bkp_source_path": str(case.get("source_case_path") or ""),
            "bkp_source_sha256": str(case.get("source_case_sha256") or ""),
            "block_count": len(bundle.get("blocks") or []),
            "stream_count": len(bundle.get("streams") or []),
        })
        units = bundle.get("units") if isinstance(bundle.get("units"), dict) else {}
        for qualified_field, raw_unit_value in sorted(units.items()):
            scope, separator, field = str(qualified_field).partition(".")
            if not separator:
                scope, field = "unknown", str(qualified_field)
            raw_unit = str(raw_unit_value or "").strip()
            normalized = derivation.normalize_unit(raw_unit) if raw_unit else ""
            canonical_field, canonical_unit = targets.get((scope, field), ("", ""))
            probe = conversion_probe(normalized, canonical_unit)
            declared_rows.append({
                "case_id": case_id,
                "scope": scope,
                "field": field,
                "unit_as_written": raw_unit,
                "normalized_unit": normalized,
                "canonical_field": canonical_field,
                "canonical_unit": canonical_unit,
                "conversion_supported": probe["supported"],
                "conversion_factor": probe["factor"],
                "conversion_offset": probe["offset"],
                "conversion_transform": probe["transform"],
                "export_path": str(path),
            })
            if normalized:
                observed_counts[normalized] += 1

        for scope, collection_name, object_id_field in (
            ("stream", "streams", "stream_id"),
            ("block", "blocks", "block_id"),
        ):
            records = bundle.get(collection_name)
            if not isinstance(records, list):
                continue
            for record in records:
                if not isinstance(record, dict):
                    continue
                object_id = str(record.get(object_id_field) or "")
                raw_values = record.get("aspen_raw_values")
                if not isinstance(raw_values, dict):
                    continue
                for field, raw_value in raw_values.items():
                    if not isinstance(raw_value, dict):
                        continue
                    unit_string = str(raw_value.get("unit") or "").strip()
                    declared_unit = str(units.get(f"{scope}.{field}") or "").strip()
                    effective_unit = unit_string or declared_unit
                    normalized = derivation.normalize_unit(effective_unit) if effective_unit else ""
                    unit_evidence = "RAW_UNIT_STRING" if unit_string else "BUNDLE_DECLARED_FALLBACK"
                    key = (scope, str(field), unit_string, effective_unit, unit_evidence)
                    item = usage.setdefault(key, {
                        "scope": scope,
                        "field": str(field),
                        "unit_string_as_written": unit_string,
                        "effective_unit": effective_unit,
                        "normalized_unit": normalized,
                        "unit_evidence": unit_evidence,
                        "occurrence_count": 0,
                        "defined_count": 0,
                        "cases": set(),
                        "objects": set(),
                        "paths": set(),
                    })
                    item["occurrence_count"] += 1
                    if str(raw_value.get("status") or "").casefold() == "defined":
                        item["defined_count"] += 1
                    item["cases"].add(case_id)
                    if object_id:
                        item["objects"].add(object_id)
                    raw_path = str(raw_value.get("path") or "")
                    if raw_path:
                        item["paths"].add(raw_path)
                    if normalized:
                        observed_counts[normalized] += 1

    usage_rows: list[dict[str, Any]] = []
    for key in sorted(usage, key=lambda item: tuple(part.casefold() for part in item)):
        item = usage[key]
        canonical_field, canonical_unit = targets.get((item["scope"], item["field"]), ("", ""))
        probe = conversion_probe(item["normalized_unit"], canonical_unit)
        usage_rows.append({
            "scope": item["scope"],
            "field": item["field"],
            "unit_string_as_written": item["unit_string_as_written"],
            "effective_unit": item["effective_unit"],
            "normalized_unit": item["normalized_unit"],
            "unit_evidence": item["unit_evidence"],
            "canonical_field": canonical_field,
            "canonical_unit": canonical_unit,
            "conversion_supported": probe["supported"],
            "conversion_factor": probe["factor"],
            "conversion_offset": probe["offset"],
            "conversion_transform": probe["transform"],
            "occurrence_count": item["occurrence_count"],
            "defined_count": item["defined_count"],
            "case_count": len(item["cases"]),
            "sample_cases": " | ".join(sorted(item["cases"])[:5]),
            "sample_objects": " | ".join(sorted(item["objects"])[:8]),
            "sample_paths": " | ".join(sorted(item["paths"])[:3]),
        })

    unit_set_rows: list[dict[str, Any]] = []
    for dimension, group in COMMON_UNIT_GROUPS.items():
        for unit, (factor, offset) in group["units"].items():
            unit_set_rows.append({
                "dimension": dimension,
                "unit": unit,
                "base_unit": group["base_unit"],
                "factor_to_base": factor,
                "offset_to_base": offset,
                "basis": group["basis"],
                "observed_in_bkp": observed_counts[unit] > 0,
                "observed_count": observed_counts[unit],
            })

    conversions = matrix_rows(observed_counts)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "aspen_bkp_sources.csv", source_rows, list(source_rows[0]))
    write_csv(output_dir / "aspen_bkp_declared_field_units.csv", declared_rows, list(declared_rows[0]))
    write_csv(output_dir / "aspen_bkp_field_unit_usage.csv", usage_rows, list(usage_rows[0]))
    write_csv(output_dir / "aspen_common_unit_set.csv", unit_set_rows, list(unit_set_rows[0]))
    write_csv(output_dir / "aspen_unit_conversion_matrix.csv", conversions, list(conversions[0]))

    summary = {
        "schema": SCHEMA,
        "source_count": len(source_rows),
        "source_manifest_sha256": canonical_json_sha256(source_rows),
        "declared_field_unit_row_count": len(declared_rows),
        "field_unit_usage_row_count": len(usage_rows),
        "unique_qualified_fields": sorted({f"{row['scope']}.{row['field']}" for row in usage_rows}),
        "unique_units_as_written": sorted({row["effective_unit"] for row in usage_rows if row["effective_unit"]}),
        "unique_normalized_units": sorted({row["normalized_unit"] for row in usage_rows if row["normalized_unit"]}),
        "unsupported_canonical_routes": [
            {
                "scope": row["scope"],
                "field": row["field"],
                "effective_unit": row["effective_unit"],
                "canonical_unit": row["canonical_unit"],
                "occurrence_count": row["occurrence_count"],
            }
            for row in usage_rows
            if row["canonical_unit"] and not row["conversion_supported"]
        ],
        "common_unit_group_count": len(COMMON_UNIT_GROUPS),
        "conversion_matrix_row_count": len(conversions),
        "files": {},
    }
    for name in (
        "aspen_bkp_sources.csv",
        "aspen_bkp_declared_field_units.csv",
        "aspen_bkp_field_unit_usage.csv",
        "aspen_common_unit_set.csv",
        "aspen_unit_conversion_matrix.csv",
    ):
        path = output_dir / name
        summary["files"][name] = {
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
        }
    summary_path = output_dir / "aspen_bkp_unit_catalog_summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract actual Aspen field/unit strings from COM-derived BKP exports and build a common conversion matrix."
    )
    parser.add_argument("--input", action="append", type=Path, required=True, help="Export JSON or directory to scan; repeatable.")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    exports = discover_exports(args.input)
    if not exports:
        raise SystemExit("no aspen_equipment_export.json files found")
    summary = build_catalog(exports, args.output_dir.expanduser().resolve())
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
