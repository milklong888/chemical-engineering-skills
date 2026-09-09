from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping


SCRIPT_PATH = Path(__file__).resolve()
PACKAGE_ROOT = SCRIPT_PATH.parents[1]
APP_DIR = PACKAGE_ROOT / "app"
for path in (APP_DIR, SCRIPT_PATH.parent):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import aspen_equipment_derivation as derivation  # noqa: E402
import aspen_pfd  # noqa: E402


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON 顶层不是对象：{path}")
    return value


def same_value(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return math.isclose(float(left), float(right), rel_tol=1e-10, abs_tol=1e-12)
    return left == right


def compare_parameter_rows(
    object_kind: str,
    object_id: str,
    expected: Mapping[str, Any],
    actual_rows: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    actual = {str(item.get("field")): item for item in actual_rows if item.get("field")}
    mismatches: list[dict[str, Any]] = []
    for field, raw_expected in expected.items():
        if not isinstance(raw_expected, Mapping) or "value" not in raw_expected:
            continue
        row = actual.get(str(field))
        if row is None:
            mismatches.append({
                "object_kind": object_kind,
                "object_id": object_id,
                "field": field,
                "code": "PFD_CANONICAL_FIELD_MISSING",
            })
            continue
        expected_unit = str(raw_expected.get("canonical_unit", ""))
        if not same_value(row.get("value"), raw_expected.get("value")):
            mismatches.append({
                "object_kind": object_kind,
                "object_id": object_id,
                "field": field,
                "code": "PFD_CANONICAL_VALUE_MISMATCH",
                "expected": raw_expected.get("value"),
                "actual": row.get("value"),
            })
        if str(row.get("unit", "")) != expected_unit:
            mismatches.append({
                "object_kind": object_kind,
                "object_id": object_id,
                "field": field,
                "code": "PFD_CANONICAL_UNIT_MISMATCH",
                "expected": expected_unit,
                "actual": row.get("unit"),
            })
        if str(row.get("source_status", "")).startswith("BLOCKED_"):
            mismatches.append({
                "object_kind": object_kind,
                "object_id": object_id,
                "field": field,
                "code": "PFD_PARAMETER_BINDING_BLOCKED",
                "source_status": row.get("source_status"),
            })
    return mismatches


def validate(bundle_path: Path, derivation_path: Path | None, mapping_path: Path | None) -> dict[str, Any]:
    bundle_path = bundle_path.resolve()
    source_hash_before = sha256_file(bundle_path)
    bundle = load_object(bundle_path)
    derived = load_object(derivation_path.resolve()) if derivation_path else derivation.derive_bundle(bundle, bundle_path)
    canonical_blocks = aspen_pfd.canonical_parameters_by_block(derived)
    canonical_streams = aspen_pfd.canonical_parameters_by_stream(derived)
    if mapping_path:
        mapping = load_object(mapping_path.resolve())
    else:
        mapping = aspen_pfd.build_pfd_mapping(
            bundle,
            canonical_parameters_by_block=canonical_blocks,
            canonical_parameters_by_stream=canonical_streams,
            parameter_normalization_issues=(
                derived.get("normalization_diagnostics")
                if isinstance(derived.get("normalization_diagnostics"), list)
                else derived.get("errors") if isinstance(derived.get("errors"), list) else ()
            ),
        )

    block_rows = {
        str(item.get("block_id")): item
        for item in mapping.get("blocks", [])
        if isinstance(item, Mapping) and item.get("block_id")
    }
    stream_rows: dict[str, Mapping[str, Any]] = {}
    pfd = mapping.get("pfd") if isinstance(mapping.get("pfd"), Mapping) else {}
    for item in pfd.get("edges", []) if isinstance(pfd.get("edges"), list) else []:
        if isinstance(item, Mapping) and item.get("stream_id"):
            stream_rows.setdefault(str(item["stream_id"]), item)

    mismatches: list[dict[str, Any]] = []
    compared_block_fields = 0
    for block_id, expected in canonical_blocks.items():
        compared_block_fields += len(expected)
        row = block_rows.get(block_id)
        if row is None:
            mismatches.append({"object_kind": "block", "object_id": block_id, "code": "PFD_BLOCK_MISSING"})
            continue
        parameters = row.get("parameters") if isinstance(row.get("parameters"), list) else []
        mismatches.extend(compare_parameter_rows("block", block_id, expected, parameters))

    compared_stream_fields = 0
    for stream_id, expected in canonical_streams.items():
        compared_stream_fields += len(expected)
        row = stream_rows.get(stream_id)
        if row is None:
            mismatches.append({"object_kind": "stream", "object_id": stream_id, "code": "PFD_STREAM_MISSING"})
            continue
        parameters = row.get("parameters") if isinstance(row.get("parameters"), list) else []
        mismatches.extend(compare_parameter_rows("stream", stream_id, expected, parameters))

    binding = mapping.get("source", {}).get("parameter_binding", {}) if isinstance(mapping.get("source"), Mapping) else {}
    if binding.get("raw_aspen_alias_relabeling_allowed") is not False:
        mismatches.append({"code": "RAW_ASPEN_ALIAS_RELABEL_POLICY_NOT_DISABLED"})
    source_hash_after = sha256_file(bundle_path)
    if source_hash_after != source_hash_before:
        mismatches.append({
            "code": "SOURCE_BUNDLE_MUTATED",
            "before": source_hash_before,
            "after": source_hash_after,
        })

    return {
        "schema": "equipment-design-pfd-parameter-binding-audit-v1",
        "status": "PASS" if not mismatches else "FAIL",
        "bundle_path": str(bundle_path),
        "bundle_sha256": source_hash_after,
        "derivation_path": str(derivation_path.resolve()) if derivation_path else None,
        "mapping_path": str(mapping_path.resolve()) if mapping_path else None,
        "mapping_sha256": mapping.get("mapping_sha256"),
        "compared_block_field_count": compared_block_fields,
        "compared_stream_field_count": compared_stream_fields,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "parameter_binding": binding,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cross-check PFD cards against the shared Aspen unit-normalization result.")
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--derivation")
    parser.add_argument("--mapping")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    result = validate(
        Path(args.bundle),
        Path(args.derivation) if args.derivation else None,
        Path(args.mapping) if args.mapping else None,
    )
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
