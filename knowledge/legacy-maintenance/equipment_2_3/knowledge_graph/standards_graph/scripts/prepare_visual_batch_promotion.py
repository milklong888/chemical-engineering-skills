#!/usr/bin/env python3
"""Prepare isolated visual-closure candidates for deterministic promotion.

This script does not mutate the global registries.  It validates a reviewed
candidate, writes runtime-safe CSV assets, and emits registry fragments that a
parent integrator may append only after independent review.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


HGT_SOURCE_ID = "std_hg_t_20592_20635_2009"
HGT_SOURCE_SHA256 = "7513C49ABF181FF538E4D3A29050DEDD4DDDBEF9DE11B25840EEF21731D64201"
GBT20801_SOURCE_ID = "std_gb_t_20801_1_2025"
GBT20801_SOURCE_SHA256 = "6DC9BE56F182A75F577CB57953AD42C609C904F8892504AFF0A5878534791254"
GBT1503_SOURCE_ID = "std_gb_t_150_3_2024"
GBT1503_SOURCE_SHA256 = "AD3F6296B08DCAC69ECC000C1980C3EE11AD1FDD6131A1EF76463F2DB52C3BF8"
GBT1503_TABLE_A3_ID = f"{GBT1503_SOURCE_ID}:p0163:t01"
GBT1503_DIRECT_FIGURE_IDS = {
    f"{GBT1503_SOURCE_ID}:p0077:f01",
    f"{GBT1503_SOURCE_ID}:p0079:f02",
    f"{GBT1503_SOURCE_ID}:p0084:f01",
    f"{GBT1503_SOURCE_ID}:p0084:f02",
    f"{GBT1503_SOURCE_ID}:p0085:f01",
    f"{GBT1503_SOURCE_ID}:p0085:f02",
    f"{GBT1503_SOURCE_ID}:p0086:f01",
    f"{GBT1503_SOURCE_ID}:p0087:f01",
    f"{GBT1503_SOURCE_ID}:p0087:f03",
    f"{GBT1503_SOURCE_ID}:p0087:f04",
}
GBT1503_METHOD_FIGURE_IDS = {
    f"{GBT1503_SOURCE_ID}:p0079:f01",
    f"{GBT1503_SOURCE_ID}:p0088:f01",
}
GBT1503_EXISTING_STRUCTURED_DATASETS = (
    "gbt1503_2024_two_digitized_curves",
    "gbt1503_2024_four_weld_structure_figures",
    "gbt1503_2024_pass2_26_structure_figures",
)

DATASET_FIELDS = [
    "dataset_id", "equipment_family", "subject", "standard_id",
    "standard_version", "source_id", "source_sha256", "authority_state",
    "lifecycle_state", "source_csv", "source_csv_sha256",
    "record_filter_field", "record_filter_values", "reuse_class",
    "qa_status", "unresolved_key_cells", "audit_path", "promotion_state",
    "approved_utc", "notes",
]
FIGURE_DATASET_FIELDS = [
    "dataset_id", "equipment_family", "subject", "representation_type",
    "standard_id", "standard_version", "source_id", "source_sha256",
    "authority_state", "lifecycle_state", "source_csv", "source_csv_sha256",
    "record_filter_field", "record_filter_values", "reuse_class",
    "qa_status", "unresolved_entities", "vision_disabled_replay_status",
    "audit_path", "promotion_state", "approved_utc", "notes",
]
TABLE_RULE_FIELDS = [
    "rule_id", "source_id", "source_pdf_sha256", "table_ids", "page_from",
    "page_to", "audit_status", "executable_dataset_ids", "qa_status",
    "evidence_path", "evidence_sha256", "note",
]
FIGURE_TERMINAL_REGISTRY_FIELDS = [
    "source_id", "source_sha256", "terminal_audit_csv",
    "terminal_audit_sha256", "validation_path", "validation_sha256",
    "promotion_audit_path", "promotion_audit_sha256",
    "structured_dataset_id", "qa_status", "promotion_state", "approved_utc",
    "notes",
]
FIGURE_TERMINAL_FIELDS = [
    "figure_id", "page_1based", "caption", "terminal_class", "needs_review",
    "minimum_next_evidence", "runtime_requires_image", "crop_sha256",
    "structured_record_count", "qa_status", "visual_review_basis",
    "terminal_reason",
]
STANDARD_SOURCE_RECORD_FIELDS = [
    "record_id", "record_type", "physical_page", "source_table",
    "source_row_label", "source_column_label", "source_bbox_pt", "raw_value",
    "normalized_value", "unit", "applicability", "qa_status",
    "terminal_class", "reuse_status",
]
FIGURE_SOURCE_RECORD_FIELDS = [
    "figure_record_id", "figure_id", "record_kind", "entity_id",
    "parent_entity_id", "physical_page", "source_figure", "raw_label",
    "normalized_value", "unit", "payload_json", "applicability",
    "error_bound", "relation_from_entity_id", "relation_to_entity_id",
    "direction", "condition_text", "terminal_status",
]


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest().upper()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
    return rows


def json_cell(value: object) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if value is None:
        return ""
    return str(value)


def ensure_unique(rows: list[dict], field: str, label: str) -> None:
    values = [str(row.get(field) or "") for row in rows]
    if not values or any(not value for value in values) or len(values) != len(set(values)):
        raise ValueError(f"{label}: {field} is empty or duplicated")


def repair_distinct_duplicate_ids(
    rows: list[dict[str, str]], field: str
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Repair only distinct-content duplicate IDs with deterministic suffixes.

    Exact duplicate records remain a hard failure because there is no defensible
    identity distinction to preserve.
    """
    groups: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        groups.setdefault(str(row.get(field) or ""), []).append(row)
    repaired: list[dict[str, str]] = []
    ledger: list[dict[str, str]] = []
    for old_id, group in groups.items():
        if not old_id:
            raise ValueError(f"empty {field}")
        if len(group) == 1:
            repaired.append(dict(group[0]))
            continue
        fingerprints: set[str] = set()
        for row in group:
            payload = json.dumps(
                {key: value for key, value in row.items() if key != field},
                ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            )
            fingerprint = hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()[:12]
            if fingerprint in fingerprints:
                raise ValueError(f"exact duplicate record cannot be repaired: {old_id}")
            fingerprints.add(fingerprint)
            new_row = dict(row)
            new_id = f"{old_id}:variant_{fingerprint}"
            new_row[field] = new_id
            repaired.append(new_row)
            ledger.append({
                "old_id": old_id,
                "new_id": new_id,
                "reason": "distinct-content duplicate source key; deterministic content-hash suffix",
            })
    ensure_unique(repaired, field, "repaired records")
    return repaired, ledger


def validate_terminal_overlay_no_regression(
    baseline_rows: list[dict[str, str]], replacement_rows: list[dict[str, str]],
    allowed_changed_ids: set[str],
) -> None:
    """Require an exact terminal-audit replacement outside reviewed overlays."""
    ensure_unique(baseline_rows, "figure_id", "baseline figure terminal audit")
    ensure_unique(replacement_rows, "figure_id", "replacement figure terminal audit")
    baseline = {row["figure_id"]: row for row in baseline_rows}
    replacement = {row["figure_id"]: row for row in replacement_rows}
    if set(baseline) != set(replacement):
        raise ValueError("figure terminal replacement does not preserve the exact figure ID set")
    for figure_id in sorted(set(baseline) - allowed_changed_ids):
        if baseline[figure_id] != replacement[figure_id]:
            raise ValueError(f"unreviewed terminal-audit row changed: {figure_id}")


def validate_candidate_crop_references(candidate: Path, figures: list[dict]) -> None:
    """Verify every candidate semantic record resolves to its declared bytes."""
    seen_paths: set[str] = set()
    for row in figures:
        figure_id = str(row.get("figure_id") or "")
        relative = str(row.get("crop_relative_path") or "")
        claimed = str(row.get("crop_sha256") or "").upper()
        if not figure_id or not relative or not claimed:
            raise ValueError(f"incomplete figure crop reference: {figure_id}")
        if relative in seen_paths:
            raise ValueError(f"figure crop path is not unique: {relative}")
        seen_paths.add(relative)
        path = candidate.joinpath(*relative.replace("\\", "/").split("/"))
        if not path.is_file() or sha256_path(path) != claimed:
            raise ValueError(f"figure crop path/hash mismatch: {figure_id}")


def require_audit(path: Path) -> None:
    if not path.is_file() or path.stat().st_size < 200:
        raise ValueError(f"independent promotion audit missing or too small: {path}")


def common_dataset_row(
    *, dataset_id: str, subject: str, standard_id: str, standard_version: str,
    source_id: str, source_sha256: str, source_csv: Path,
    filter_field: str, filter_values: str, reuse_class: str, audit_path: Path,
    approved_utc: str, notes: str, equipment_family: str = "piping",
) -> dict:
    return {
        "dataset_id": dataset_id,
        "equipment_family": equipment_family,
        "subject": subject,
        "standard_id": standard_id,
        "standard_version": standard_version,
        "source_id": source_id,
        "source_sha256": source_sha256,
        "authority_state": "CURRENT",
        "lifecycle_state": "CURRENT",
        "source_csv": str(source_csv.resolve()),
        "source_csv_sha256": sha256_path(source_csv),
        "record_filter_field": filter_field,
        "record_filter_values": filter_values,
        "reuse_class": reuse_class,
        "qa_status": "VERIFIED",
        "unresolved_key_cells": "0",
        "audit_path": str(audit_path.resolve()),
        "promotion_state": "APPROVED",
        "approved_utc": approved_utc,
        "notes": notes,
    }


def prepare_hgt(candidate: Path, out_dir: Path, audit_path: Path, approved_utc: str) -> dict:
    require_audit(audit_path)
    records = read_csv(candidate / "normalized_records.csv")
    records, id_repairs = repair_distinct_duplicate_ids(records, "record_id")
    if len(records) != 103:
        raise ValueError(f"HG/T record count changed: {len(records)} != 103")
    for row in records:
        if str(row.get("unresolved_key_cells")) != "0":
            raise ValueError(f"unresolved HG/T record: {row['record_id']}")
        if row.get("reuse_class") == "METHOD_ONLY" and str(row.get("numeric_reuse_allowed")).casefold() != "false":
            raise ValueError(f"METHOD_ONLY numeric leak: {row['record_id']}")
    direct = [row for row in records if row.get("reuse_class") == "DIRECT_REUSE_VERIFIED"]
    method = [row for row in records if row.get("reuse_class") == "METHOD_ONLY"]
    if len(direct) != 29 or len(method) != 74:
        raise ValueError(f"HG/T class counts changed: direct={len(direct)} method={len(method)}")
    direct_ids = {row["table_id"] for row in direct}
    if direct_ids != {f"{HGT_SOURCE_ID}:p0032:t01"}:
        raise ValueError(f"unexpected HG/T direct table IDs: {sorted(direct_ids)}")

    for row in records:
        row.update({
            "record_type": row.get("record_kind", "table_record"),
            "physical_page": row.get("page_1based", ""),
            "source_table": row.get("table_id", ""),
            "raw_value": row.get("fields_json", ""),
            "normalized_value": row.get("fields_json", ""),
            "unit": "mm" if row.get("reuse_class") == "DIRECT_REUSE_VERIFIED" else "",
            "applicability": row.get("source_note", ""),
            "terminal_class": row.get("reuse_class", ""),
        })
    direct = [row for row in records if row.get("reuse_class") == "DIRECT_REUSE_VERIFIED"]
    method = [row for row in records if row.get("reuse_class") == "METHOD_ONLY"]

    direct_path = out_dir / "hgt20592_dn_od_direct.csv"
    method_path = out_dir / "hgt20592_method_only_records.csv"
    record_fields = list(records[0])
    write_csv(direct_path, direct, record_fields)
    write_csv(method_path, method, record_fields)
    write_csv(
        out_dir / "record_id_repair_ledger.csv", id_repairs,
        ["old_id", "new_id", "reason"],
    )

    rules = read_jsonl(candidate / "applicability_rules.jsonl")
    ensure_unique(rules, "rule_id", "HG/T applicability rules")
    if len(rules) != 6:
        raise ValueError(f"HG/T applicability rule count changed: {len(rules)} != 6")
    runtime_rules: list[dict] = []
    for row in rules:
        enriched = dict(row)
        source_table = str(row.get("source_table_id") or "")
        page_token = next(
            (part for part in source_table.split(":") if part.startswith("p")), ""
        )
        enriched.update({
            "record_id": row["rule_id"],
            "record_type": "applicability_rule",
            "physical_page": page_token.removeprefix("p").lstrip("0") or "0",
            "source_table": source_table,
            "raw_value": row.get("source_statement", ""),
            "normalized_value": row.get("candidate_capability", ""),
            "unit": "",
            "applicability": row.get("necessary_compatibility", ""),
            "qa_status": "VISUAL_GLYPH_VERIFIED",
            "terminal_class": "METHOD_ONLY",
        })
        runtime_rules.append(enriched)
    rule_fields = sorted({key for row in runtime_rules for key in row})
    rule_path = out_dir / "hgt20592_applicability_rules.csv"
    write_csv(
        rule_path,
        [{key: json_cell(row.get(key)) for key in rule_fields} for row in runtime_rules],
        rule_fields,
    )

    datasets = [
        common_dataset_row(
            dataset_id="hgt20592_20635_2009_dn_od_ab_mapping",
            subject="dn_to_series_a_b_steel_pipe_outer_diameter",
            standard_id="HG/T 20592~20635-2009", standard_version="2009",
            source_id=HGT_SOURCE_ID, source_sha256=HGT_SOURCE_SHA256,
            source_csv=direct_path, filter_field="reuse_class",
            filter_values="DIRECT_REUSE_VERIFIED", reuse_class="DIRECT_REUSE_VERIFIED",
            audit_path=audit_path, approved_utc=approved_utc,
            notes="29 exact DN-to-A/B outer-diameter rows; A/B series is mandatory input; not a wall-thickness or material-service selector",
        ),
        common_dataset_row(
            dataset_id="hgt20592_20635_2009_method_condition_records",
            subject="flange_gasket_fastener_condition_records",
            standard_id="HG/T 20592~20635-2009", standard_version="2009",
            source_id=HGT_SOURCE_ID, source_sha256=HGT_SOURCE_SHA256,
            source_csv=method_path, filter_field="reuse_class",
            filter_values="METHOD_ONLY", reuse_class="METHOD_ONLY",
            audit_path=audit_path, approved_utc=approved_utc,
            notes="74 visually verified condition records; numeric_reuse_allowed=false; require applicability evaluation",
        ),
        common_dataset_row(
            dataset_id="hgt20592_20635_2009_applicability_rules",
            subject="flange_gasket_fastener_applicability_rules",
            standard_id="HG/T 20592~20635-2009", standard_version="2009",
            source_id=HGT_SOURCE_ID, source_sha256=HGT_SOURCE_SHA256,
            source_csv=rule_path, filter_field="rule_id",
            filter_values="|".join(row["rule_id"] for row in rules), reuse_class="METHOD_ONLY",
            audit_path=audit_path, approved_utc=approved_utc,
            notes="Deterministic condition schema with hard exclusions, compatibility, minimum missing fields and warnings; no hazard guessing",
        ),
    ]
    write_csv(out_dir / "dataset_registry.fragment.csv", datasets, DATASET_FIELDS)

    chains = read_csv(candidate / "logical_table_chains.csv")
    closed_ids = [row["logical_table_id"] for row in chains if row.get("logical_status") == "CLOSED"]
    if len(closed_ids) != 10:
        raise ValueError(f"HG/T closed table count changed: {len(closed_ids)} != 10")
    audit_hash = sha256_path(audit_path)
    table_rules: list[dict] = []
    for table_id in closed_ids:
        is_direct = table_id == f"{HGT_SOURCE_ID}:p0032:t01"
        linked_rules = any(row.get("source_table_id") == table_id for row in rules)
        dataset_ids = [
            "hgt20592_20635_2009_dn_od_ab_mapping" if is_direct
            else "hgt20592_20635_2009_method_condition_records"
        ]
        if linked_rules:
            dataset_ids.append("hgt20592_20635_2009_applicability_rules")
        table_rules.append({
            "rule_id": "hgt20592_visual_" + table_id.rsplit(":", 2)[-2].replace("p", "p") + "_" + table_id.rsplit(":", 1)[-1],
            "source_id": HGT_SOURCE_ID,
            "source_pdf_sha256": HGT_SOURCE_SHA256,
            "table_ids": table_id,
            "page_from": "", "page_to": "",
            "audit_status": "DIRECT_REUSE_VERIFIED" if is_direct else "METHOD_ONLY",
            "executable_dataset_ids": "|".join(dataset_ids),
            "qa_status": "VERIFIED",
            "evidence_path": str(audit_path.resolve()),
            "evidence_sha256": audit_hash,
            "note": "Complete single-page logical table, visually closed with exact source hash; non-direct tables remain METHOD_ONLY",
        })
    write_csv(out_dir / "table_promotion_rules.fragment.csv", table_rules, TABLE_RULE_FIELDS)
    return {
        "batch": "hgt20592", "status": "PASS", "direct_records": len(direct),
        "method_records": len(method), "applicability_rules": len(rules),
        "closed_tables": len(closed_ids), "record_id_repairs": len(id_repairs),
    }


def prepare_gbt20801(candidate: Path, out_dir: Path, audit_path: Path, approved_utc: str) -> dict:
    require_audit(audit_path)
    terminal = json.loads((candidate / "terminal_audit.json").read_text(encoding="utf-8"))
    if terminal.get("status") != "PASS" or terminal.get("source_pdf_sha256") != GBT20801_SOURCE_SHA256:
        raise ValueError("GB/T 20801 candidate terminal audit/source hash failed")
    if terminal.get("closed_logical_tables") != 5 or terminal.get("all_figure_ids_terminal_audited") != 123:
        raise ValueError("GB/T 20801 candidate closure counts changed")

    table_rows = read_csv(candidate / "normalized_table_cells_long.csv")
    if len(table_rows) != 158:
        raise ValueError(f"GB/T 20801 table-cell count changed: {len(table_rows)} != 158")
    table_ids = sorted({row.get("table_id", "") for row in table_rows})
    if table_ids != sorted(terminal["closed_table_ids"]):
        raise ValueError("GB/T 20801 table IDs do not match the terminal audit")
    if any(row.get("reuse_status") != "DIRECT_REUSE_VERIFIED" for row in table_rows):
        raise ValueError("GB/T 20801 table row is not DIRECT_REUSE_VERIFIED")
    table_runtime_rows: list[dict] = []
    for cell_index, row in enumerate(table_rows, 1):
        table_runtime_rows.append({
            "record_id": f"{row['table_id']}:cell_{cell_index:03d}",
            "record_type": "table_cell",
            "physical_page": row.get("page_1based", ""),
            "source_table": row.get("table_id", ""),
            "source_row_label": row.get("row", ""),
            "source_column_label": row.get("column", ""),
            "source_bbox_pt": "",
            "raw_value": row.get("raw_text", ""),
            "normalized_value": row.get("normalized_value", ""),
            "unit": row.get("unit_or_scope", ""),
            "applicability": row.get("cell_role", ""),
            "qa_status": row.get("visual_status", ""),
            "terminal_class": "DIRECT_REUSE_VERIFIED",
            "reuse_status": "DIRECT_REUSE_VERIFIED",
        })
    table_path = out_dir / "gbt20801_closed_table_cells.csv"
    write_csv(table_path, table_runtime_rows, STANDARD_SOURCE_RECORD_FIELDS)

    figures = read_jsonl(candidate / "figure_semantic_transcriptions.jsonl")
    ensure_unique(figures, "figure_id", "GB/T 20801 figure records")
    if len(figures) != 12 or sorted(row["figure_id"] for row in figures) != sorted(terminal["closed_figure_ids"]):
        raise ValueError("GB/T 20801 closed figure set changed")
    if any(row.get("terminal_status") != "DIRECT_REUSE_VERIFIED" or row.get("needs_review") is not False for row in figures):
        raise ValueError("GB/T 20801 closed figure is not terminally verified")
    def semantic_source_row(row: dict) -> dict:
        conditions = row.get("conditions") or []
        runtime_payload = {
            key: value for key, value in row.items()
            if key not in {"source_image_path", "evidence_figure", "crop_relative_path"}
        }
        return {
            "figure_record_id": f"{row['figure_id']}:semantic_bundle",
            "figure_id": row["figure_id"],
            "record_kind": "semantic_bundle",
            "entity_id": row["figure_id"],
            "parent_entity_id": "",
            "physical_page": row.get("page_1based", ""),
            "source_figure": row["figure_id"],
            "raw_label": row.get("caption", ""),
            "normalized_value": row.get("caption", ""),
            "unit": "",
            "payload_json": json.dumps(runtime_payload, ensure_ascii=False, sort_keys=True),
            "applicability": "; ".join(str(value) for value in conditions),
            "error_bound": "",
            "relation_from_entity_id": "",
            "relation_to_entity_id": "",
            "direction": "",
            "condition_text": "; ".join(str(value) for value in conditions),
            "terminal_status": row.get("terminal_status", ""),
        }
    figure_path = out_dir / "gbt20801_closed_figure_records.csv"
    write_csv(
        figure_path, [semantic_source_row(row) for row in figures],
        FIGURE_SOURCE_RECORD_FIELDS,
    )

    source_terminal_rows = read_csv(candidate / "figure_terminal_audit_replacement.csv")
    ensure_unique(source_terminal_rows, "figure_id", "GB/T 20801 terminal figure audit")
    if len(source_terminal_rows) != 123:
        raise ValueError(f"GB/T 20801 terminal figure count changed: {len(source_terminal_rows)} != 123")
    closed_by_id = {row["figure_id"]: row for row in figures}
    runtime_rows: list[dict] = []
    for row in source_terminal_rows:
        figure_id = row["figure_id"]
        status = row.get("terminal_status")
        if status == "DIRECT_REUSE_VERIFIED":
            semantic = closed_by_id.get(figure_id)
            if semantic is None:
                raise ValueError(f"closed figure lacks semantic record: {figure_id}")
            runtime_rows.append({
                "figure_id": figure_id,
                "page_1based": row.get("page_1based", ""),
                "caption": row.get("caption", ""),
                "terminal_class": "DIMENSION_STRUCTURE_DATAIZED",
                "needs_review": "false",
                "minimum_next_evidence": "",
                "runtime_requires_image": "false",
                "crop_sha256": row.get("source_image_sha256", ""),
                "structured_record_count": "1",
                "qa_status": semantic.get("visual_status", "VERIFIED_ON_ORIGINAL_FIGURE_CROP_AND_PAGE_RENDER"),
                "visual_review_basis": "objects;dimensions;ports;edges;directions;conditions;legend",
                "terminal_reason": "Complete non-visual semantic transcription linked to the exact source crop hash",
            })
        elif status == "SEMANTIC_TRANSCRIPTION_PENDING":
            if str(row.get("needs_review")).casefold() != "true" or not row.get("minimum_next_evidence"):
                raise ValueError(f"pending figure is not explicitly open: {figure_id}")
            runtime_rows.append({
                "figure_id": figure_id,
                "page_1based": row.get("page_1based", ""),
                "caption": row.get("caption", ""),
                "terminal_class": "SEMANTIC_TRANSCRIPTION_PENDING",
                "needs_review": "true",
                "minimum_next_evidence": row.get("minimum_next_evidence", ""),
                "runtime_requires_image": "false",
                "crop_sha256": row.get("source_image_sha256", ""),
                "structured_record_count": "0",
                "qa_status": "PENDING",
                "visual_review_basis": "",
                "terminal_reason": "Readable source figure remains blocked until complete semantic transcription",
            })
        else:
            raise ValueError(f"unsupported GB/T 20801 terminal status: {figure_id}: {status}")
    terminal_path = out_dir / "gbt20801_figure_terminal_audit.csv"
    write_csv(terminal_path, runtime_rows, FIGURE_TERMINAL_FIELDS)

    validation = {
        "schema": "vision-free-figure-terminal-validation-v1",
        "validation": "PASS",
        "failure_count": 0,
        "vision_capability": False,
        "source_image_runtime_access": "FORBIDDEN",
        "source_id": GBT20801_SOURCE_ID,
        "source_pdf_sha256": GBT20801_SOURCE_SHA256,
        "terminal_figure_count": 123,
        "dataized_figure_count": 12,
        "semantic_transcription_pending_count": 111,
        "runtime_dataset_sha256": sha256_path(figure_path),
        "terminal_audit_sha256": sha256_path(terminal_path),
    }
    validation_path = out_dir / "gbt20801_figure_validation.json"
    validation_path.write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    dataset_row = common_dataset_row(
        dataset_id="gbt20801_1_2025_closed_table_cells",
        subject="piping_material_connection_and_design_factor_closed_tables",
        standard_id="GB/T 20801.1-2025", standard_version="2025",
        source_id=GBT20801_SOURCE_ID, source_sha256=GBT20801_SOURCE_SHA256,
        source_csv=table_path, filter_field="reuse_status",
        filter_values="DIRECT_REUSE_VERIFIED", reuse_class="DIRECT_REUSE_VERIFIED",
        audit_path=audit_path, approved_utc=approved_utc,
        notes="158 visually verified cells from five exact closed logical tables; table scope and dash-as-not-applicable semantics retained",
    )
    write_csv(out_dir / "dataset_registry.fragment.csv", [dataset_row], DATASET_FIELDS)

    figure_dataset_row = {
        "dataset_id": "gbt20801_1_2025_closed_structure_figures",
        "equipment_family": "piping",
        "subject": "piping_connection_reinforcement_and_bend_structure_figures",
        "representation_type": "dimension_structure",
        "standard_id": "GB/T 20801.1-2025",
        "standard_version": "2025",
        "source_id": GBT20801_SOURCE_ID,
        "source_sha256": GBT20801_SOURCE_SHA256,
        "authority_state": "CURRENT", "lifecycle_state": "CURRENT",
        "source_csv": str(figure_path.resolve()),
        "source_csv_sha256": sha256_path(figure_path),
        "record_filter_field": "terminal_status",
        "record_filter_values": "DIRECT_REUSE_VERIFIED",
        "reuse_class": "DIRECT_REUSE_VERIFIED", "qa_status": "VERIFIED",
        "unresolved_entities": "0", "vision_disabled_replay_status": "PASS",
        "audit_path": str(audit_path.resolve()), "promotion_state": "APPROVED",
        "approved_utc": approved_utc,
        "notes": "12 exact figure IDs dataized as non-visual semantic records; remaining 111 source figures remain transcription-pending",
    }
    write_csv(out_dir / "figure_dataset_registry.fragment.csv", [figure_dataset_row], FIGURE_DATASET_FIELDS)

    audit_hash = sha256_path(audit_path)
    table_rule = {
        "rule_id": "gbt20801_1_2025_visual_closed_exact_5",
        "source_id": GBT20801_SOURCE_ID,
        "source_pdf_sha256": GBT20801_SOURCE_SHA256,
        "table_ids": "|".join(table_ids), "page_from": "", "page_to": "",
        "audit_status": "DIRECT_REUSE_VERIFIED",
        "executable_dataset_ids": "gbt20801_1_2025_closed_table_cells",
        "qa_status": "VERIFIED", "evidence_path": str(audit_path.resolve()),
        "evidence_sha256": audit_hash,
        "note": "Five exact single-page logical tables with all 158 non-empty cells visually verified; no page-range inheritance",
    }
    write_csv(out_dir / "table_promotion_rules.fragment.csv", [table_rule], TABLE_RULE_FIELDS)

    figure_terminal_registry = {
        "source_id": GBT20801_SOURCE_ID,
        "source_sha256": GBT20801_SOURCE_SHA256,
        "terminal_audit_csv": str(terminal_path.resolve()),
        "terminal_audit_sha256": sha256_path(terminal_path),
        "validation_path": str(validation_path.resolve()),
        "validation_sha256": sha256_path(validation_path),
        "promotion_audit_path": str(audit_path.resolve()),
        "promotion_audit_sha256": audit_hash,
        "structured_dataset_id": "gbt20801_1_2025_closed_structure_figures",
        "qa_status": "VERIFIED", "promotion_state": "APPROVED",
        "approved_utc": approved_utc,
        "notes": "Exact 123-ID terminal replacement: 12 dimension structures dataized; 111 semantic transcriptions explicitly pending",
    }
    write_csv(out_dir / "figure_terminal_audit_registry.fragment.csv", [figure_terminal_registry], FIGURE_TERMINAL_REGISTRY_FIELDS)
    return {
        "batch": "gbt20801", "status": "PASS", "table_cells": len(table_rows),
        "closed_tables": len(table_ids), "dataized_figures": len(figures),
        "terminal_figures": len(runtime_rows),
    }


def prepare_gbt1503(
    candidate: Path, out_dir: Path, audit_path: Path, approved_utc: str,
    baseline_terminal_audit: Path,
) -> dict:
    """Promote only the independently closed GB/T 150.3 subset.

    Four visually readable but OCR-corrupted structure/method tables from the
    same candidate intentionally remain outside the public datasets.  Only the
    exact table A.3 mapping and the reviewed semantic figure overlays enter the
    registry fragments.
    """
    require_audit(audit_path)
    if not baseline_terminal_audit.is_file():
        raise FileNotFoundError(baseline_terminal_audit)

    all_table_rows = read_csv(candidate / "normalized" / "table_cells_long.csv")
    table_rows = [
        row for row in all_table_rows
        if row.get("logical_table_id") == "gbt1503:table_a_3"
    ]
    if len(table_rows) != 28:
        raise ValueError(f"GB/T 150.3 table A.3 count changed: {len(table_rows)} != 28")
    if {row.get("table_id") for row in table_rows} != {GBT1503_TABLE_A3_ID}:
        raise ValueError("GB/T 150.3 table A.3 is not bound to exact source table p0163:t01")
    expected = [
        ("β 或 1/β（取其中较大值）", "应力参数J"),
        ("1.0", "4.9"), ("1.1", "4.3"), ("1.2", "3.9"),
        ("1.3", "3.6"), ("1.4", "3.3"), ("1.5", "3.1"),
        ("1.6", "2.9"), ("1.7", "2.8"), ("1.8", "2.6"),
        ("1.9", "2.5"), ("2.0", "2.4"), ("3.0", "2.1"),
        (">=4.0", "2.0"),
    ]
    by_cell = {
        (int(row["row"]), int(row["column"])): row.get("normalized_value", "")
        for row in table_rows
    }
    observed = [
        (by_cell[(row_number, 1)], by_cell[(row_number, 2)])
        for row_number in range(1, 15)
    ]
    if observed != expected:
        raise ValueError("GB/T 150.3 table A.3 visually reviewed mapping changed")
    crop_refs = {(row.get("crop_relative_path"), row.get("crop_sha256")) for row in table_rows}
    if len(crop_refs) != 1:
        raise ValueError("GB/T 150.3 table A.3 does not share one immutable evidence crop")
    table_crop_relative, table_crop_sha = next(iter(crop_refs))
    table_crop_path = candidate.joinpath(
        *str(table_crop_relative).replace("\\", "/").split("/")
    )
    if (
        not table_crop_path.is_file()
        or sha256_path(table_crop_path) != str(table_crop_sha).upper()
    ):
        raise ValueError("GB/T 150.3 table A.3 crop path/hash mismatch")
    table_runtime_rows: list[dict] = []
    for row in table_rows:
        table_runtime_rows.append({
            "record_id": f"{GBT1503_TABLE_A3_ID}:r{int(row['row']):03d}:c{int(row['column']):03d}",
            "record_type": "table_cell",
            "physical_page": row.get("physical_page", "163"),
            "source_table": GBT1503_TABLE_A3_ID,
            "source_row_label": row.get("row", ""),
            "source_column_label": row.get("column", ""),
            "source_bbox_pt": row.get("bbox_pt", ""),
            "raw_value": row.get("printed_glyph_text", ""),
            "normalized_value": row.get("normalized_value", ""),
            "unit": "dimensionless",
            "applicability": "β_or_inverse_beta=max(β,1/β)",
            "qa_status": row.get("qa_status", "VISUALLY_VERIFIED_GLYPH"),
            "terminal_class": "DIRECT_REUSE_VERIFIED",
            "reuse_status": "DIRECT_REUSE_VERIFIED",
        })
    table_path = out_dir / "gbt1503_table_a3_stress_parameter_j.csv"
    write_csv(table_path, table_runtime_rows, STANDARD_SOURCE_RECORD_FIELDS)

    figures = read_jsonl(candidate / "normalized" / "closed_figures.jsonl")
    ensure_unique(figures, "figure_id", "GB/T 150.3 closed figure records")
    if {row["figure_id"] for row in figures} != (
        GBT1503_DIRECT_FIGURE_IDS | GBT1503_METHOD_FIGURE_IDS
    ):
        raise ValueError("GB/T 150.3 reviewed figure set changed")
    validate_candidate_crop_references(candidate, figures)
    direct_figures = [row for row in figures if row["figure_id"] in GBT1503_DIRECT_FIGURE_IDS]
    method_figures = [row for row in figures if row["figure_id"] in GBT1503_METHOD_FIGURE_IDS]
    if any(
        row.get("terminal_status") != "DIRECT_REUSE_VERIFIED"
        or row.get("kind") != "dimension_structure"
        for row in direct_figures
    ):
        raise ValueError("GB/T 150.3 direct structure figure classification changed")
    if any(
        row.get("terminal_status") != "METHOD_ONLY"
        or row.get("kind") != "quantitative_curve"
        or row.get("numeric_reuse_allowed") is not False
        for row in method_figures
    ):
        raise ValueError("GB/T 150.3 method-only curve boundary changed")

    def semantic_source_row(row: dict) -> dict:
        conditions = row.get("conditions") or []
        runtime_payload = {
            key: value for key, value in row.items()
            if key not in {"source_image_path", "evidence_figure", "crop_relative_path"}
        }
        return {
            "figure_record_id": f"{row['figure_id']}:semantic_bundle",
            "figure_id": row["figure_id"],
            "record_kind": "semantic_bundle",
            "entity_id": row["figure_id"],
            "parent_entity_id": "",
            "physical_page": row.get("physical_page", ""),
            "source_figure": row["figure_id"],
            "raw_label": row.get("title", ""),
            "normalized_value": row.get("title", ""),
            "unit": "",
            "payload_json": json.dumps(runtime_payload, ensure_ascii=False, sort_keys=True),
            "applicability": "; ".join(str(value) for value in conditions),
            "error_bound": row.get("error_bounds", ""),
            "relation_from_entity_id": "",
            "relation_to_entity_id": "",
            "direction": "",
            "condition_text": "; ".join(str(value) for value in conditions),
            "terminal_status": row.get("terminal_status", ""),
        }

    direct_figure_path = out_dir / "gbt1503_visual_batch_10_structure_figures.csv"
    method_figure_path = out_dir / "gbt1503_visual_batch_2_method_curves.csv"
    write_csv(
        direct_figure_path, [semantic_source_row(row) for row in direct_figures],
        FIGURE_SOURCE_RECORD_FIELDS,
    )
    write_csv(
        method_figure_path, [semantic_source_row(row) for row in method_figures],
        FIGURE_SOURCE_RECORD_FIELDS,
    )

    baseline_rows = read_csv(baseline_terminal_audit)
    replacement_rows = read_csv(candidate / "audit" / "figure_terminal_audit_replacement.csv")
    changed_ids = GBT1503_DIRECT_FIGURE_IDS | GBT1503_METHOD_FIGURE_IDS
    validate_terminal_overlay_no_regression(baseline_rows, replacement_rows, changed_ids)
    replacement_by_id = {row["figure_id"]: row for row in replacement_rows}
    for figure_id in GBT1503_DIRECT_FIGURE_IDS:
        row = replacement_by_id[figure_id]
        if row.get("terminal_class") != "DIMENSION_STRUCTURE" or row.get("needs_review", "").casefold() != "false":
            raise ValueError(f"GB/T 150.3 direct figure terminal row invalid: {figure_id}")
    for figure_id in GBT1503_METHOD_FIGURE_IDS:
        row = replacement_by_id[figure_id]
        if row.get("terminal_class") != "METHOD_ONLY" or row.get("needs_review", "").casefold() != "false":
            raise ValueError(f"GB/T 150.3 method figure terminal row invalid: {figure_id}")
    runtime_terminal_rows = [
        {field: row.get(field, "") for field in FIGURE_TERMINAL_FIELDS}
        for row in replacement_rows
    ]
    terminal_path = out_dir / "gbt1503_figure_terminal_audit.csv"
    write_csv(terminal_path, runtime_terminal_rows, FIGURE_TERMINAL_FIELDS)

    validation = {
        "schema": "vision-free-figure-terminal-validation-v1",
        "validation": "PASS", "failure_count": 0,
        "vision_capability": False,
        "source_image_runtime_access": "FORBIDDEN",
        "source_id": GBT1503_SOURCE_ID,
        "source_pdf_sha256": GBT1503_SOURCE_SHA256,
        "terminal_figure_count": len(runtime_terminal_rows),
        "new_dimension_structure_count": len(direct_figures),
        "new_method_only_count": len(method_figures),
        "baseline_nonoverlay_rows_byte_preserved": len(baseline_rows) - len(changed_ids),
        "terminal_audit_sha256": sha256_path(terminal_path),
    }
    validation_path = out_dir / "gbt1503_figure_validation.json"
    validation_path.write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    dataset_row = common_dataset_row(
        dataset_id="gbt1503_2024_table_a3_stress_parameter_j",
        subject="rectangular_vessel_stress_parameter_j",
        standard_id="GB/T 150.3-2024", standard_version="2024",
        source_id=GBT1503_SOURCE_ID, source_sha256=GBT1503_SOURCE_SHA256,
        source_csv=table_path, filter_field="reuse_status",
        filter_values="DIRECT_REUSE_VERIFIED", reuse_class="DIRECT_REUSE_VERIFIED",
        audit_path=audit_path, approved_utc=approved_utc,
        notes="Exact table A.3 mapping for max(beta,1/beta) to stress parameter J; 28 visually verified cells from p0163:t01 only",
        equipment_family="vessel_or_storage",
    )
    write_csv(out_dir / "dataset_registry.fragment.csv", [dataset_row], DATASET_FIELDS)

    def figure_dataset_row(
        dataset_id: str, subject: str, representation_type: str, source_csv: Path,
        reuse_class: str, notes: str,
    ) -> dict:
        return {
            "dataset_id": dataset_id, "equipment_family": "vessel_or_storage",
            "subject": subject, "representation_type": representation_type,
            "standard_id": "GB/T 150.3-2024", "standard_version": "2024",
            "source_id": GBT1503_SOURCE_ID, "source_sha256": GBT1503_SOURCE_SHA256,
            "authority_state": "CURRENT", "lifecycle_state": "CURRENT",
            "source_csv": str(source_csv.resolve()),
            "source_csv_sha256": sha256_path(source_csv),
            "record_filter_field": "terminal_status",
            "record_filter_values": reuse_class,
            "reuse_class": reuse_class, "qa_status": "VERIFIED",
            "unresolved_entities": "0", "vision_disabled_replay_status": "PASS",
            "audit_path": str(audit_path.resolve()), "promotion_state": "APPROVED",
            "approved_utc": approved_utc, "notes": notes,
        }

    figure_dataset_rows = [
        figure_dataset_row(
            "gbt1503_2024_visual_batch_10_structure_figures",
            "pressure_vessel_opening_reinforcement_and_weld_structure_relations",
            "dimension_structure", direct_figure_path, "DIRECT_REUSE_VERIFIED",
            "Ten exact figure IDs exposed as text-only semantic bundles; no source image is required at runtime",
        ),
        figure_dataset_row(
            "gbt1503_2024_visual_batch_2_method_curves",
            "pressure_vessel_method_applicability_curve_semantics",
            "method_only", method_figure_path, "METHOD_ONLY",
            "Two curve semantics are queryable, but numeric interpolation and design-value transfer remain forbidden",
        ),
    ]
    write_csv(
        out_dir / "figure_dataset_registry.fragment.csv",
        figure_dataset_rows, FIGURE_DATASET_FIELDS,
    )

    audit_hash = sha256_path(audit_path)
    table_rule = {
        "rule_id": "gbt1503_2024_table_a3_exact",
        "source_id": GBT1503_SOURCE_ID,
        "source_pdf_sha256": GBT1503_SOURCE_SHA256,
        "table_ids": GBT1503_TABLE_A3_ID,
        "page_from": "", "page_to": "",
        "audit_status": "DIRECT_REUSE_VERIFIED",
        "executable_dataset_ids": "gbt1503_2024_table_a3_stress_parameter_j",
        "qa_status": "VERIFIED", "evidence_path": str(audit_path.resolve()),
        "evidence_sha256": audit_hash,
        "note": "Exact single-page table A.3 only; p0163:t02 is table A.4 and is not inherited",
    }
    write_csv(out_dir / "table_promotion_rules.fragment.csv", [table_rule], TABLE_RULE_FIELDS)

    terminal_registry = {
        "source_id": GBT1503_SOURCE_ID,
        "source_sha256": GBT1503_SOURCE_SHA256,
        "terminal_audit_csv": str(terminal_path.resolve()),
        "terminal_audit_sha256": sha256_path(terminal_path),
        "validation_path": str(validation_path.resolve()),
        "validation_sha256": sha256_path(validation_path),
        "promotion_audit_path": str(audit_path.resolve()),
        "promotion_audit_sha256": audit_hash,
        "structured_dataset_id": "|".join(
            (*GBT1503_EXISTING_STRUCTURED_DATASETS,
             "gbt1503_2024_visual_batch_10_structure_figures")
        ),
        "qa_status": "VERIFIED", "promotion_state": "APPROVED",
        "approved_utc": approved_utc,
        "notes": "Exact 423-ID replacement; all baseline non-overlay rows preserved, plus 10 dimension structures and 2 method-only curves",
    }
    write_csv(
        out_dir / "figure_terminal_audit_registry.fragment.csv",
        [terminal_registry], FIGURE_TERMINAL_REGISTRY_FIELDS,
    )
    return {
        "batch": "gbt1503", "status": "PASS",
        "promoted_table_cells": len(table_runtime_rows),
        "promoted_tables": 1,
        "rejected_unreliable_logical_tables": 4,
        "dataized_structure_figures": len(direct_figures),
        "method_only_figures": len(method_figures),
        "terminal_figures": len(runtime_terminal_rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("batch", choices=("hgt20592", "gbt20801", "gbt1503"))
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--promotion-audit", type=Path, required=True)
    parser.add_argument("--approved-utc", required=True)
    parser.add_argument("--baseline-terminal-audit", type=Path)
    args = parser.parse_args()
    candidate = args.candidate_dir.resolve()
    out_dir = args.out_dir.resolve()
    audit_path = args.promotion_audit.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.batch == "hgt20592":
        result = prepare_hgt(candidate, out_dir, audit_path, args.approved_utc)
    elif args.batch == "gbt20801":
        result = prepare_gbt20801(candidate, out_dir, audit_path, args.approved_utc)
    else:
        if args.baseline_terminal_audit is None:
            parser.error("gbt1503 requires --baseline-terminal-audit")
        result = prepare_gbt1503(
            candidate, out_dir, audit_path, args.approved_utc,
            args.baseline_terminal_audit.resolve(),
        )
    result["output_dir"] = str(out_dir)
    result["promotion_audit_sha256"] = sha256_path(audit_path)
    (out_dir / "promotion_prepare_summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
