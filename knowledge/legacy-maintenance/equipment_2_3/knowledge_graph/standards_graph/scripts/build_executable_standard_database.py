#!/usr/bin/env python3
"""Build the hash-locked executable standards CSV/SQLite layer.

This offline builder consumes only audited candidate CSV files named in the
promotion registry.  The production query module consumes only the generated
SQLite database and never opens a source PDF/Word/Excel file.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ALLOWED_REUSE_CLASSES = {
    "DIRECT_REUSE_VERIFIED",
    "METHOD_ONLY",
    "SOFTWARE_BOUNDARY",
    "VENDOR_BOUNDARY",
    "OBSOLETE_FORBIDDEN",
    "FORBIDDEN_TRANSFER",
    "NOT_APPLICABLE",
}
ALLOWED_FIGURE_REPRESENTATIONS = {
    "quantitative_curve",
    "dimension_structure",
    "process_logic",
    "symbol_icon",
    "method_only",
    "not_applicable",
}

FIGURE_RECORD_FIELDS = [
    "dataset_id",
    "figure_record_id",
    "figure_id",
    "equipment_family",
    "subject",
    "representation_type",
    "record_kind",
    "entity_id",
    "parent_entity_id",
    "standard_id",
    "standard_version",
    "authority_state",
    "lifecycle_state",
    "source_id",
    "source_sha256",
    "physical_page",
    "source_figure",
    "raw_label",
    "normalized_value",
    "normalized_number",
    "unit",
    "payload_json",
    "applicability",
    "error_bound",
    "relation_from_entity_id",
    "relation_to_entity_id",
    "direction",
    "condition_text",
    "reuse_class",
    "qa_status",
    "audit_path",
    "build_id",
    "record_sha256",
]


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest().upper()


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def record_hash(row: dict) -> str:
    payload = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()


def normalize_payload(value: str) -> tuple[float | None, str]:
    attributes: dict[str, str | bool] = {}
    if ";" in value or "=" in value:
        for part in value.split(";"):
            if "=" not in part:
                continue
            key, raw = part.split("=", 1)
            key = key.strip()
            raw = raw.strip()
            if raw.casefold() in {"true", "false"}:
                attributes[key] = raw.casefold() == "true"
            else:
                attributes[key] = raw
    numeric_candidate = str(attributes.get("value", value))
    try:
        number = float(numeric_candidate)
    except (TypeError, ValueError):
        number = None
    return number, json.dumps(attributes, ensure_ascii=False, sort_keys=True)


def validate_dataset(row: dict) -> None:
    if row.get("promotion_state") != "APPROVED":
        return
    if row.get("reuse_class") not in ALLOWED_REUSE_CLASSES:
        raise ValueError(f"{row.get('dataset_id')}: invalid reuse_class")
    if row.get("qa_status") != "VERIFIED":
        raise ValueError(f"{row.get('dataset_id')}: approved dataset is not VERIFIED")
    if int(row.get("unresolved_key_cells") or -1) != 0:
        raise ValueError(f"{row.get('dataset_id')}: unresolved key cells remain")
    if row.get("reuse_class") == "DIRECT_REUSE_VERIFIED" and row.get("authority_state") != "CURRENT":
        raise ValueError(f"{row.get('dataset_id')}: direct reuse source is not current")


def validate_figure_dataset(row: dict) -> None:
    if row.get("promotion_state") != "APPROVED":
        return
    dataset_id = row.get("dataset_id")
    if row.get("representation_type") not in ALLOWED_FIGURE_REPRESENTATIONS:
        raise ValueError(f"{dataset_id}: invalid figure representation_type")
    if row.get("reuse_class") not in ALLOWED_REUSE_CLASSES:
        raise ValueError(f"{dataset_id}: invalid reuse_class")
    if row.get("qa_status") != "VERIFIED":
        raise ValueError(f"{dataset_id}: approved figure dataset is not VERIFIED")
    if int(row.get("unresolved_entities") or -1) != 0:
        raise ValueError(f"{dataset_id}: unresolved figure entities remain")
    if row.get("vision_disabled_replay_status") != "PASS":
        raise ValueError(f"{dataset_id}: vision-disabled replay has not passed")
    if row.get("reuse_class") == "DIRECT_REUSE_VERIFIED" and row.get("authority_state") != "CURRENT":
        raise ValueError(f"{dataset_id}: direct reuse figure source is not current")


def normalized_json_payload(raw: str) -> str:
    value = str(raw or "").strip() or "{}"
    payload = json.loads(value)
    if not isinstance(payload, (dict, list)):
        raise ValueError("figure payload_json must contain a JSON object or array")
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def first_nonempty(source: dict, *keys: str) -> str:
    for key in keys:
        value = str(source.get(key) or "").strip()
        if value:
            return value
    return ""


def standard_candidate_value(source: dict) -> str:
    """Accept the canonical field first, then audited common candidate aliases."""
    return first_nonempty(
        source,
        "normalized_value",
        "normalized_number",
        "formula_expression",
        "raw_value",
    )


def standard_candidate_applicability(source: dict) -> str:
    explicit = first_nonempty(source, "applicability")
    if explicit:
        return explicit
    parts = []
    for key in ("row_condition", "column_condition", "material", "grade", "note"):
        value = first_nonempty(source, key)
        if value:
            parts.append(f"{key}={value}")
    return "; ".join(parts)


def standard_candidate_physical_page(source: dict) -> str:
    """Return the audited physical-page locator without changing its meaning.

    Candidate builders have historically used a few explicit aliases.  A
    logical table that spans continuation pages may legitimately carry a
    closed locator such as ``117-118`` or ``117|118`` rather than one page.
    """
    return first_nonempty(
        source,
        "physical_page",
        "page_1based",
        "physical_page_1based",
        "source_page",
        "page",
    )


def valid_physical_page_locator(value: str) -> bool:
    """Accept only positive physical page numbers and explicit page chains."""
    locator = str(value or "").strip()
    return bool(
        re.fullmatch(r"[1-9]\d*(?:\s*(?:-|–|—|\||,|;)\s*[1-9]\d*)*", locator)
    )


def source_record_id(source: dict) -> str:
    explicit = str(
        source.get("record_id")
        or source.get("table_record_id")
        or source.get("candidate_record_id")
        or ""
    ).strip()
    if explicit:
        return explicit
    locator = {
        "record_type": source.get("record_type", ""),
        "physical_page": standard_candidate_physical_page(source),
        "source_section": source.get("source_section", ""),
        "source_table": source.get("source_table") or source.get("table_id", ""),
        "source_row": source.get("source_row") or source.get("source_row_label") or source.get("row_key", ""),
        "source_column": source.get("source_column") or source.get("source_column_label") or source.get("column_key", ""),
        "source_bbox_pt": source.get("source_bbox_pt", ""),
        "raw_value": source.get("raw_value", ""),
    }
    digest = hashlib.sha256(
        json.dumps(locator, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()[:24].upper()
    return f"AUTO-{digest}"


def build_database(
    registry_path: Path,
    out_dir: Path,
    build_id: str,
    figure_registry_path: Path | None = None,
) -> dict:
    registry = read_csv(registry_path)
    approved = [row for row in registry if row.get("promotion_state") == "APPROVED"]
    for row in registry:
        validate_dataset(row)
    if not approved:
        raise ValueError("promotion registry contains no approved datasets")

    records: list[dict] = []
    dataset_rows: list[dict] = []
    for dataset in approved:
        source_csv = Path(dataset["source_csv"])
        if not source_csv.is_file():
            raise FileNotFoundError(source_csv)
        actual_hash = sha256_path(source_csv)
        if actual_hash != dataset["source_csv_sha256"].upper():
            raise ValueError(f"{dataset['dataset_id']}: candidate CSV hash mismatch")
        audit_path = Path(dataset["audit_path"])
        if not audit_path.is_file():
            raise FileNotFoundError(audit_path)
        filter_field = dataset["record_filter_field"]
        allowed_values = set(dataset["record_filter_values"].split("|"))
        selected = [row for row in read_csv(source_csv) if row.get(filter_field) in allowed_values]
        if not selected:
            raise ValueError(f"{dataset['dataset_id']}: record filter selected zero rows")
        selected_record_ids = [source_record_id(source) for source in selected]
        if len(selected_record_ids) != len(set(selected_record_ids)):
            raise ValueError(f"{dataset['dataset_id']}: selected record IDs are not unique")
        if dataset["reuse_class"] == "DIRECT_REUSE_VERIFIED":
            for record_id, source in zip(selected_record_ids, selected):
                if not str(source.get("raw_value") or "").strip():
                    raise ValueError(
                        f"{dataset['dataset_id']}:{record_id}: direct record has no raw_value"
                    )
                if not standard_candidate_value(source):
                    raise ValueError(
                        f"{dataset['dataset_id']}:{record_id}: direct record has no normalized value"
                    )
                physical_page = standard_candidate_physical_page(source)
                if not valid_physical_page_locator(physical_page):
                    raise ValueError(
                        f"{dataset['dataset_id']}:{record_id}: direct record has no valid physical_page"
                    )
        dataset_rows.append(
            {
                **dataset,
                "source_csv_actual_sha256": actual_hash,
                "audit_sha256": sha256_path(audit_path),
                "record_count": len(selected),
                "build_id": build_id,
            }
        )
        for source, record_id in zip(selected, selected_record_ids):
            normalized_value = standard_candidate_value(source)
            normalized_number, normalized_attributes_json = normalize_payload(
                normalized_value
            )
            base = {
                "dataset_id": dataset["dataset_id"],
                "record_id": record_id,
                "equipment_family": dataset["equipment_family"],
                "subject": dataset["subject"],
                "source_record_type": first_nonempty(
                    source, "record_type", "table_category", "value_kind"
                ),
                "standard_id": dataset["standard_id"],
                "standard_version": dataset["standard_version"],
                "authority_state": dataset["authority_state"],
                "lifecycle_state": dataset["lifecycle_state"],
                "source_id": dataset["source_id"],
                "source_sha256": dataset["source_sha256"],
                "physical_page": standard_candidate_physical_page(source),
                "source_section": source.get("source_section", ""),
                "source_table": first_nonempty(
                    source, "source_table", "table_id", "logical_table_no"
                ),
                "source_row_label": first_nonempty(
                    source, "source_row_label", "source_row", "row_condition"
                ),
                "source_column_label": first_nonempty(
                    source, "source_column_label", "source_column", "column_condition"
                ),
                "source_bbox_pt": source.get("source_bbox_pt", ""),
                "raw_value": source.get("raw_value", ""),
                "normalized_value": normalized_value,
                "normalized_number": normalized_number,
                "normalized_attributes_json": normalized_attributes_json,
                "unit": source.get("unit", ""),
                "applicability": standard_candidate_applicability(source),
                "source_record_qa_status": source.get("qa_status", ""),
                "source_terminal_class": source.get("terminal_class", ""),
                "source_payload_json": json.dumps(
                    source, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ),
                "reuse_class": dataset["reuse_class"],
                "qa_status": dataset["qa_status"],
                "audit_path": dataset["audit_path"],
                "build_id": build_id,
            }
            base["record_sha256"] = record_hash(base)
            records.append(base)

    figure_registry = read_csv(figure_registry_path) if figure_registry_path else []
    approved_figure_datasets = [
        row for row in figure_registry if row.get("promotion_state") == "APPROVED"
    ]
    for row in figure_registry:
        validate_figure_dataset(row)
    figure_records: list[dict] = []
    figure_dataset_rows: list[dict] = []
    for dataset in approved_figure_datasets:
        source_csv = Path(dataset["source_csv"])
        if not source_csv.is_file():
            raise FileNotFoundError(source_csv)
        actual_hash = sha256_path(source_csv)
        if actual_hash != dataset["source_csv_sha256"].upper():
            raise ValueError(f"{dataset['dataset_id']}: figure candidate CSV hash mismatch")
        audit_path = Path(dataset["audit_path"])
        if not audit_path.is_file():
            raise FileNotFoundError(audit_path)
        filter_field = dataset.get("record_filter_field", "")
        allowed_values = set(str(dataset.get("record_filter_values") or "").split("|"))
        candidate_rows = read_csv(source_csv)
        selected = (
            [row for row in candidate_rows if row.get(filter_field) in allowed_values]
            if filter_field
            else candidate_rows
        )
        if not selected:
            raise ValueError(f"{dataset['dataset_id']}: figure record filter selected zero rows")
        figure_dataset_rows.append(
            {
                **dataset,
                "source_csv_actual_sha256": actual_hash,
                "audit_sha256": sha256_path(audit_path),
                "record_count": len(selected),
                "build_id": build_id,
            }
        )
        for source in selected:
            figure_record_id = str(
                source.get("figure_record_id") or source.get("record_id") or ""
            ).strip()
            figure_id = str(source.get("figure_id") or "").strip()
            record_kind = str(source.get("record_kind") or "").strip()
            if not figure_record_id or not figure_id or not record_kind:
                raise ValueError(
                    f"{dataset['dataset_id']}: figure_record_id, figure_id and record_kind are required"
                )
            normalized_number, _ = normalize_payload(source.get("normalized_value", ""))
            base = {
                "dataset_id": dataset["dataset_id"],
                "figure_record_id": figure_record_id,
                "figure_id": figure_id,
                "equipment_family": dataset["equipment_family"],
                "subject": dataset["subject"],
                "representation_type": dataset["representation_type"],
                "record_kind": record_kind,
                "entity_id": source.get("entity_id", ""),
                "parent_entity_id": source.get("parent_entity_id", ""),
                "standard_id": dataset["standard_id"],
                "standard_version": dataset["standard_version"],
                "authority_state": dataset["authority_state"],
                "lifecycle_state": dataset["lifecycle_state"],
                "source_id": dataset["source_id"],
                "source_sha256": dataset["source_sha256"],
                "physical_page": source.get("physical_page", ""),
                "source_figure": source.get("source_figure", ""),
                "raw_label": source.get("raw_label", ""),
                "normalized_value": source.get("normalized_value", ""),
                "normalized_number": normalized_number,
                "unit": source.get("unit", ""),
                "payload_json": normalized_json_payload(source.get("payload_json", "{}")),
                "applicability": source.get("applicability", ""),
                "error_bound": source.get("error_bound", ""),
                "relation_from_entity_id": source.get("relation_from_entity_id", ""),
                "relation_to_entity_id": source.get("relation_to_entity_id", ""),
                "direction": source.get("direction", ""),
                "condition_text": source.get("condition_text", ""),
                "reuse_class": dataset["reuse_class"],
                "qa_status": dataset["qa_status"],
                "audit_path": dataset["audit_path"],
                "build_id": build_id,
            }
            base["record_sha256"] = record_hash(base)
            figure_records.append(base)

    if len({(row["dataset_id"], row["record_id"]) for row in records}) != len(records):
        raise ValueError("duplicate dataset_id/record_id key")
    if len(
        {(row["dataset_id"], row["figure_record_id"]) for row in figure_records}
    ) != len(figure_records):
        raise ValueError("duplicate dataset_id/figure_record_id key")

    out_dir.mkdir(parents=True, exist_ok=True)
    record_fields = list(records[0])
    csv_path = out_dir / "standard_records.csv"
    write_csv(csv_path, records, record_fields)
    json_path = out_dir / "standard_records.json"
    json_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    figure_csv_path = out_dir / "figure_records.csv"
    write_csv(figure_csv_path, figure_records, FIGURE_RECORD_FIELDS)
    figure_json_path = out_dir / "figure_records.json"
    figure_json_path.write_text(
        json.dumps(figure_records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    db_path = out_dir / "executable_standard_data.sqlite"
    if db_path.exists():
        db_path.unlink()
    connection = sqlite3.connect(db_path)
    try:
        connection.execute(
            "CREATE TABLE datasets (dataset_id TEXT PRIMARY KEY, equipment_family TEXT, subject TEXT, standard_id TEXT, standard_version TEXT, source_id TEXT, source_sha256 TEXT, authority_state TEXT, lifecycle_state TEXT, reuse_class TEXT, qa_status TEXT, record_count INTEGER, source_csv_sha256 TEXT, audit_path TEXT, audit_sha256 TEXT, build_id TEXT)"
        )
        connection.execute(
            "CREATE TABLE standard_records (dataset_id TEXT, record_id TEXT, equipment_family TEXT, subject TEXT, source_record_type TEXT, standard_id TEXT, standard_version TEXT, authority_state TEXT, lifecycle_state TEXT, source_id TEXT, source_sha256 TEXT, physical_page TEXT, source_section TEXT, source_table TEXT, source_row_label TEXT, source_column_label TEXT, source_bbox_pt TEXT, raw_value TEXT, normalized_value TEXT, normalized_number REAL, normalized_attributes_json TEXT, unit TEXT, applicability TEXT, source_record_qa_status TEXT, source_terminal_class TEXT, source_payload_json TEXT, reuse_class TEXT, qa_status TEXT, audit_path TEXT, build_id TEXT, record_sha256 TEXT, PRIMARY KEY(dataset_id, record_id))"
        )
        connection.execute(
            "CREATE TABLE figure_datasets (dataset_id TEXT PRIMARY KEY, equipment_family TEXT, subject TEXT, representation_type TEXT, standard_id TEXT, standard_version TEXT, source_id TEXT, source_sha256 TEXT, authority_state TEXT, lifecycle_state TEXT, reuse_class TEXT, qa_status TEXT, record_count INTEGER, source_csv_sha256 TEXT, audit_path TEXT, audit_sha256 TEXT, vision_disabled_replay_status TEXT, build_id TEXT)"
        )
        connection.execute(
            "CREATE TABLE figure_records (dataset_id TEXT, figure_record_id TEXT, figure_id TEXT, equipment_family TEXT, subject TEXT, representation_type TEXT, record_kind TEXT, entity_id TEXT, parent_entity_id TEXT, standard_id TEXT, standard_version TEXT, authority_state TEXT, lifecycle_state TEXT, source_id TEXT, source_sha256 TEXT, physical_page TEXT, source_figure TEXT, raw_label TEXT, normalized_value TEXT, normalized_number REAL, unit TEXT, payload_json TEXT, applicability TEXT, error_bound TEXT, relation_from_entity_id TEXT, relation_to_entity_id TEXT, direction TEXT, condition_text TEXT, reuse_class TEXT, qa_status TEXT, audit_path TEXT, build_id TEXT, record_sha256 TEXT, PRIMARY KEY(dataset_id, figure_record_id))"
        )
        for dataset in dataset_rows:
            connection.execute(
                "INSERT INTO datasets VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    dataset["dataset_id"], dataset["equipment_family"], dataset["subject"],
                    dataset["standard_id"], dataset["standard_version"], dataset["source_id"],
                    dataset["source_sha256"], dataset["authority_state"], dataset["lifecycle_state"],
                    dataset["reuse_class"], dataset["qa_status"], dataset["record_count"],
                    dataset["source_csv_actual_sha256"], dataset["audit_path"],
                    dataset["audit_sha256"], build_id,
                ),
            )
        columns = record_fields
        placeholders = ",".join("?" for _ in columns)
        for record in records:
            connection.execute(
                f"INSERT INTO standard_records ({','.join(columns)}) VALUES ({placeholders})",
                tuple(record[column] for column in columns),
            )
        for dataset in figure_dataset_rows:
            connection.execute(
                "INSERT INTO figure_datasets VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    dataset["dataset_id"], dataset["equipment_family"], dataset["subject"],
                    dataset["representation_type"], dataset["standard_id"],
                    dataset["standard_version"], dataset["source_id"], dataset["source_sha256"],
                    dataset["authority_state"], dataset["lifecycle_state"],
                    dataset["reuse_class"], dataset["qa_status"], dataset["record_count"],
                    dataset["source_csv_actual_sha256"], dataset["audit_path"],
                    dataset["audit_sha256"], dataset["vision_disabled_replay_status"], build_id,
                ),
            )
        figure_placeholders = ",".join("?" for _ in FIGURE_RECORD_FIELDS)
        for record in figure_records:
            connection.execute(
                f"INSERT INTO figure_records ({','.join(FIGURE_RECORD_FIELDS)}) VALUES ({figure_placeholders})",
                tuple(record[column] for column in FIGURE_RECORD_FIELDS),
            )
        connection.execute("CREATE INDEX idx_standard_records_family ON standard_records(equipment_family, subject, source_record_type)")
        connection.execute("CREATE INDEX idx_figure_records_family ON figure_records(equipment_family, subject, representation_type, record_kind)")
        connection.execute("CREATE INDEX idx_figure_records_figure ON figure_records(figure_id, record_kind)")
        connection.commit()
        db_count = connection.execute("SELECT COUNT(*) FROM standard_records").fetchone()[0]
        db_figure_count = connection.execute("SELECT COUNT(*) FROM figure_records").fetchone()[0]
    finally:
        connection.close()
    if db_count != len(records):
        raise ValueError("CSV/SQLite row-count mismatch")
    if db_figure_count != len(figure_records):
        raise ValueError("figure CSV/SQLite row-count mismatch")
    csv_roundtrip = read_csv(csv_path)
    if len(csv_roundtrip) != len(records):
        raise ValueError("CSV round-trip row-count mismatch")
    if len(read_csv(figure_csv_path)) != len(figure_records):
        raise ValueError("figure CSV round-trip row-count mismatch")

    manifest = {
        "schema": "equipment-executable-standard-data-build-v3",
        "build_id": build_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "registry_path": str(registry_path),
        "registry_sha256": sha256_path(registry_path),
        "dataset_count": len(dataset_rows),
        "record_count": len(records),
        "figure_dataset_count": len(figure_dataset_rows),
        "figure_record_count": len(figure_records),
        "standard_records_csv": str(csv_path),
        "standard_records_csv_sha256": sha256_path(csv_path),
        "standard_records_json": str(json_path),
        "standard_records_json_sha256": sha256_path(json_path),
        "figure_records_csv": str(figure_csv_path),
        "figure_records_csv_sha256": sha256_path(figure_csv_path),
        "figure_records_json": str(figure_json_path),
        "figure_records_json_sha256": sha256_path(figure_json_path),
        "sqlite_path": str(db_path),
        "sqlite_sha256": sha256_path(db_path),
        "csv_sqlite_row_count_equal": True,
        "figure_csv_sqlite_row_count_equal": True,
        "source_document_runtime_access": "FORBIDDEN",
        "source_image_runtime_access": "FORBIDDEN",
        "vision_capability": False,
    }
    (out_dir / "build_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--build-id", required=True)
    parser.add_argument("--figure-registry", type=Path)
    args = parser.parse_args()
    manifest = build_database(
        args.registry.resolve(),
        args.out_dir.resolve(),
        args.build_id,
        args.figure_registry.resolve() if args.figure_registry else None,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
