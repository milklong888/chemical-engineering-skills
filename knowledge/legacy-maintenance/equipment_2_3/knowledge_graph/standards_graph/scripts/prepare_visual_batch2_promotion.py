#!/usr/bin/env python3
"""Prepare the reviewed 2026-07-20 visual-batch-2 registry fragments.

This is an offline promotion builder.  It never mutates the live registries,
copies no PDF/image path into runtime records, and accepts only the exact
reviewed subsets for GB/T 150.2-2024, HG/T 20569-2013, and GB/T 1220-2007.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path


GBT1502_SOURCE_ID = "std_gb_t_150_2_2024"
GBT1502_SOURCE_SHA = "B4BF3DD5D47E33A82EEBCFEC8CF48C989D0E63A556760E447946FC3F3BD9CAF6"
HGT20569_SOURCE_ID = "std_hg_t_20569_2013"
HGT20569_SOURCE_SHA = "91756DFEE8D8B79F78C04A64EB6B79B5CD4E90C0FC7983B26832813559018751"
GBT1220_SOURCE_ID = "std_gb_t_1220_2007"
GBT1220_SOURCE_SHA = "AD021BF1FF8998FC58080DE43EF442F55E7F513124120E7AE3AEB9D5A98A137E"
GBT1220_TABLE16_FOOTNOTE = (
    "a 电渣钢除表面和尺寸逐根外，其他检验项目的取样数量均为1个。"
    "以自耗电极的熔炼母炉号组批时，除化学成分每个电渣炉号取1个外，"
    "其他检验项目取样数量同表中规定。"
)
GBT1220_TABLE16_FOOTNOTE_NORMALIZED = {
    "conditions": [
        {
            "condition_text": "电渣钢（表面和尺寸除外）",
            "sampling_quantity_printed": "1个",
        },
        {
            "condition_text": "以自耗电极的熔炼母炉号组批",
            "chemical_composition_sampling_quantity_printed": "每个电渣炉号1个",
            "other_inspection_items_sampling_quantity_printed": "同表中规定",
        },
    ]
}
GBT1220_TABLE16_ROWS = [
    ("化学成分", "1", "GB/T 20066", "GB/T 223(见第2章)、GB/T 11170、GB/T 9971—2004的附录A"),
    ("拉伸", "2", "不同根钢棒，GB/T 2975", "GB/T 228"),
    ("冲击", "2", "不同根钢棒，GB/T 2975", "GB/T 229"),
    ("硬度", "2", "不同根钢棒", "GB/T 230.1、GB/T 231.1、GB/T 4340.1"),
    ("晶间腐蚀", "2", "不同根钢棒", "GB/T 4334.1、GB/T 4334.2、GB/T 4334.3、GB/T 4334.5"),
    ("低倍组织", "2", "相当于钢锭头部的不同根钢棒或钢坯；连铸钢在任意不同根钢棒", "GB/T 226、GB/T 1979"),
    ("超声波检验", "2", "整根钢棒", "GB/T 7736"),
    ("热顶锻", "2", "不同根钢棒", "YB/T 5293"),
    ("非金属夹杂物", "2", "不同根钢棒", "GB/T 10561"),
    ("晶粒度", "1", "任一钢棒", "GB/T 6394"),
    ("α相", "1", "任一钢棒", "GB/T 6401—1986、GB/T 13305—1991"),
    ("塔形", "2", "相当于钢锭头部的不同根钢棒或钢坯；连铸钢在任意不同根钢棒", "GB/T 15711、GB/T 10121"),
    ("尺寸", "逐根", "整根钢棒", "卡尺、千分尺"),
    ("表面", "逐根", "整根钢棒", "目视"),
]

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
STANDARD_FIELDS = [
    "record_id", "record_type", "physical_page", "source_section",
    "source_table", "source_row_label", "source_column_label",
    "source_bbox_pt", "raw_value", "normalized_value", "unit",
    "applicability", "qa_status", "terminal_class", "reuse_status",
]
FIGURE_FIELDS = [
    "figure_record_id", "figure_id", "record_kind", "entity_id",
    "parent_entity_id", "physical_page", "source_figure", "raw_label",
    "normalized_value", "unit", "payload_json", "applicability",
    "error_bound", "relation_from_entity_id", "relation_to_entity_id",
    "direction", "condition_text", "terminal_status",
]
FIGURE_TERMINAL_FIELDS = [
    "figure_id", "page_1based", "caption", "terminal_class", "needs_review",
    "minimum_next_evidence", "runtime_requires_image", "crop_sha256",
    "structured_record_count", "qa_status", "visual_review_basis",
    "terminal_reason",
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


def require_file(path: Path, minimum_bytes: int = 1) -> None:
    if not path.is_file() or path.stat().st_size < minimum_bytes:
        raise ValueError(f"required reviewed artifact missing or too small: {path}")


def require_unique(rows: list[dict[str, str]], field: str, label: str) -> None:
    values = [str(row.get(field) or "").strip() for row in rows]
    if not values or any(not value for value in values) or len(values) != len(set(values)):
        raise ValueError(f"{label}: {field} is blank or duplicated")


def require_runtime_safe(path: Path) -> None:
    text = path.read_text(encoding="utf-8-sig").casefold()
    forbidden = (
        "source_image_path", "crop_relative_path", "evidence_figure",
        ".png", ".jpg", ".jpeg", ".pdf",
    )
    leaked = [token for token in forbidden if token in text]
    if leaked:
        raise ValueError(f"runtime source/image reference leaked into {path}: {leaked}")


def page_ok(value: str) -> bool:
    return bool(re.fullmatch(r"[1-9]\d*(?:\s*(?:-|–|—|\||,|;)\s*[1-9]\d*)*", value.strip()))


def dataset_row(
    *, dataset_id: str, family: str, subject: str, standard_id: str,
    version: str, source_id: str, source_sha: str, source_csv: Path,
    filter_field: str, filter_values: str, reuse_class: str, audit: Path,
    approved_utc: str, notes: str,
) -> dict[str, str]:
    return {
        "dataset_id": dataset_id,
        "equipment_family": family,
        "subject": subject,
        "standard_id": standard_id,
        "standard_version": version,
        "source_id": source_id,
        "source_sha256": source_sha,
        "authority_state": "CURRENT",
        "lifecycle_state": "CURRENT",
        "source_csv": str(source_csv.resolve()),
        "source_csv_sha256": sha256_path(source_csv),
        "record_filter_field": filter_field,
        "record_filter_values": filter_values,
        "reuse_class": reuse_class,
        "qa_status": "VERIFIED",
        "unresolved_key_cells": "0",
        "audit_path": str(audit.resolve()),
        "promotion_state": "APPROVED",
        "approved_utc": approved_utc,
        "notes": notes,
    }


def figure_dataset_row(
    *, dataset_id: str, subject: str, representation: str, source_csv: Path,
    filter_values: str, reuse_class: str, audit: Path, approved_utc: str,
    notes: str,
) -> dict[str, str]:
    return {
        "dataset_id": dataset_id,
        "equipment_family": "reactor_or_agitator",
        "subject": subject,
        "representation_type": representation,
        "standard_id": "HG/T 20569-2013",
        "standard_version": "2013",
        "source_id": HGT20569_SOURCE_ID,
        "source_sha256": HGT20569_SOURCE_SHA,
        "authority_state": "CURRENT",
        "lifecycle_state": "CURRENT",
        "source_csv": str(source_csv.resolve()),
        "source_csv_sha256": sha256_path(source_csv),
        "record_filter_field": "terminal_status",
        "record_filter_values": filter_values,
        "reuse_class": reuse_class,
        "qa_status": "VERIFIED",
        "unresolved_entities": "0",
        "vision_disabled_replay_status": "PASS",
        "audit_path": str(audit.resolve()),
        "promotion_state": "APPROVED",
        "approved_utc": approved_utc,
        "notes": notes,
    }


def prepare_gbt1502(candidate: Path, out: Path, audit: Path, approved_utc: str) -> dict:
    require_file(audit, 200)
    source = candidate / "candidate_data" / "gbt1502_table_8_candidate_records.csv"
    require_file(source)
    if sha256_path(source) != "6FD2E1B90C72F56CE9365DF23425A3C699DD1CAAC419C2668CD7C213514DDFEB":
        raise ValueError("GB/T 150.2 candidate hash changed")
    all_rows = read_csv(source)
    require_unique(all_rows, "record_id", "GB/T 150.2 grid")
    if len(all_rows) != 95:
        raise ValueError(f"GB/T 150.2 grid count changed: {len(all_rows)}")
    allowed_types = {"table_header", "material_grade_status_temperature_range", "footnote"}
    rows = [row for row in all_rows if row.get("record_type") in allowed_types]
    if len(rows) != 80:
        raise ValueError(f"GB/T 150.2 selected count changed: {len(rows)}")
    runtime: list[dict[str, str]] = []
    table_ids: set[str] = set()
    for row in rows:
        record_id = row["record_id"]
        match = re.match(r"^(.*:p\d{4}:t\d{2}):r\d{3}:c\d{3}$", record_id)
        if not match:
            raise ValueError(f"GB/T 150.2 unstable record locator: {record_id}")
        table_ids.add(match.group(1))
        if not row.get("raw_value") or not row.get("normalized_value") or not page_ok(row.get("physical_page", "")):
            raise ValueError(f"GB/T 150.2 incomplete direct record: {record_id}")
        runtime.append({
            "record_id": record_id,
            "record_type": row["record_type"],
            "physical_page": row["physical_page"],
            "source_section": "Table 8",
            "source_table": match.group(1),
            "source_row_label": row.get("source_row_label", ""),
            "source_column_label": row.get("source_column_label", ""),
            "source_bbox_pt": row.get("source_bbox_pt", ""),
            "raw_value": row["raw_value"],
            "normalized_value": row["normalized_value"],
            "unit": row.get("unit", ""),
            "applicability": row.get("applicability", ""),
            "qa_status": "VERIFIED",
            "terminal_class": "DIRECT_REUSE_VERIFIED",
            "reuse_status": "DIRECT_REUSE_VERIFIED",
        })
    expected_tables = {
        f"{GBT1502_SOURCE_ID}:p0023:t03", f"{GBT1502_SOURCE_ID}:p0024:t01"
    }
    if table_ids != expected_tables:
        raise ValueError(f"GB/T 150.2 table chain changed: {sorted(table_ids)}")
    runtime_path = out / "gbt1502_table8_records.csv"
    write_csv(runtime_path, runtime, STANDARD_FIELDS)
    require_runtime_safe(runtime_path)
    datasets = [dataset_row(
        dataset_id="gbt1502_table_8_bolt_nut_steel",
        family="vessel_or_storage",
        subject="bolt_nut_steel_grade_standard_state_temperature_range",
        standard_id="GB/T 150.2-2024", version="2024",
        source_id=GBT1502_SOURCE_ID, source_sha=GBT1502_SOURCE_SHA,
        source_csv=runtime_path, filter_field="reuse_status",
        filter_values="DIRECT_REUSE_VERIFIED", reuse_class="DIRECT_REUSE_VERIFIED",
        audit=audit, approved_utc=approved_utc,
        notes="Closed Table 8 continuation chain p23-p24; 80 nonempty printed records; table-level bbox only",
    )]
    write_csv(out / "dataset_registry.fragment.csv", datasets, DATASET_FIELDS)
    audit_sha = sha256_path(audit)
    rules = [{
        "rule_id": "gbt1502_table_8_closed_chain",
        "source_id": GBT1502_SOURCE_ID,
        "source_pdf_sha256": GBT1502_SOURCE_SHA,
        "table_ids": "|".join(sorted(expected_tables)),
        "page_from": "23", "page_to": "24",
        "audit_status": "DIRECT_REUSE_VERIFIED",
        "executable_dataset_ids": "gbt1502_table_8_bolt_nut_steel",
        "qa_status": "VERIFIED",
        "evidence_path": str(audit.resolve()), "evidence_sha256": audit_sha,
        "note": "Exact Table 8 first/continuation pages only; remaining GB/T 150.2 key tables stay blocked",
    }]
    write_csv(out / "table_promotion_rules.fragment.csv", rules, TABLE_RULE_FIELDS)
    return {"batch": "gbt1502", "status": "PASS", "records": len(runtime), "tables": 2}


def validate_figure_graph(rows: list[dict[str, str]]) -> None:
    for figure_id in sorted({row["figure_id"] for row in rows}):
        group = [row for row in rows if row["figure_id"] == figure_id]
        entities = {row["entity_id"] for row in group if row.get("entity_id")}
        if len(entities) != len([row for row in group if row.get("entity_id")]):
            raise ValueError(f"duplicate entity_id in figure {figure_id}")
        for row in group:
            for field in ("parent_entity_id", "relation_from_entity_id", "relation_to_entity_id"):
                value = row.get(field, "")
                if value and value not in entities:
                    raise ValueError(f"dangling {field}={value} in figure {figure_id}")


def prepare_hgt20569(candidate: Path, out: Path, audit: Path, approved_utc: str) -> dict:
    require_file(audit, 200)
    candidate_fragments = read_csv(candidate / "dataset_registry.fragment.csv")
    expected_datasets = {
        "hgt20569_2013_blade_width_coefficients_c1121",
        "hgt20569_2013_internal_correction_ki_c425",
        "hgt20569_2013_dished_head_flange_applicability_b53",
    }
    if {row["dataset_id"] for row in candidate_fragments} != expected_datasets:
        raise ValueError("HG/T 20569 reviewed direct-table dataset set changed")
    runtime_paths: dict[str, Path] = {}
    total_direct = 0
    for fragment in candidate_fragments:
        if fragment.get("source_id") != HGT20569_SOURCE_ID or fragment.get("source_sha256") != HGT20569_SOURCE_SHA:
            raise ValueError("HG/T 20569 source identity changed")
        source = Path(fragment["source_csv"])
        if sha256_path(source) != fragment["source_csv_sha256"]:
            raise ValueError(f"HG/T 20569 source table hash mismatch: {source}")
        rows = [row for row in read_csv(source) if row.get("terminal_class") == "DIRECT_REUSE_VERIFIED"]
        require_unique(rows, "record_id", fragment["dataset_id"])
        runtime: list[dict[str, str]] = []
        for row in rows:
            if not row.get("raw_value") or not row.get("normalized_value") or not page_ok(row.get("physical_page", "")):
                raise ValueError(f"HG/T 20569 incomplete direct record: {row.get('record_id')}")
            runtime.append({
                field: row.get(field, "") for field in STANDARD_FIELDS
            } | {
                "qa_status": "VERIFIED",
                "terminal_class": "DIRECT_REUSE_VERIFIED",
                "reuse_status": "DIRECT_REUSE_VERIFIED",
            })
        total_direct += len(runtime)
        runtime_path = out / f"{fragment['dataset_id']}.csv"
        write_csv(runtime_path, runtime, STANDARD_FIELDS)
        require_runtime_safe(runtime_path)
        runtime_paths[fragment["dataset_id"]] = runtime_path
    if total_direct != 34:
        raise ValueError(f"HG/T 20569 direct record count changed: {total_direct}")

    subject_by_id = {row["dataset_id"]: row["subject"] for row in candidate_fragments}
    datasets = [dataset_row(
        dataset_id=dataset_id, family="reactor_or_agitator",
        subject=subject_by_id[dataset_id], standard_id="HG/T 20569-2013",
        version="2013", source_id=HGT20569_SOURCE_ID, source_sha=HGT20569_SOURCE_SHA,
        source_csv=runtime_paths[dataset_id], filter_field="reuse_status",
        filter_values="DIRECT_REUSE_VERIFIED", reuse_class="DIRECT_REUSE_VERIFIED",
        audit=audit, approved_utc=approved_utc,
        notes="Exact visually verified printed table records; no service/material inference beyond the recorded applicability",
    ) for dataset_id in sorted(expected_datasets)]

    # The four-page appendix is a blank input template.  Expose its method and
    # minimum inputs, but never expose a default or copied numeric value.
    method_source = read_csv(candidate / "method_only_selection_rules.csv")
    appendix_rows = [
        row for row in method_source
        if row.get("rule_id") == "appendix_a_explicit_input_only"
    ]
    if len(appendix_rows) != 1:
        raise ValueError("HG/T 20569 appendix-A method route changed")
    method = appendix_rows[0]
    method_runtime = [{
        "record_id": f"{HGT20569_SOURCE_ID}:p0038:t01:method_only_route",
        "record_type": "method_only_input_template",
        "physical_page": method["physical_pages"],
        "source_section": "Appendix A",
        "source_table": f"{HGT20569_SOURCE_ID}:p0038:t01",
        "source_row_label": "", "source_column_label": "", "source_bbox_pt": "",
        "raw_value": method["raw_statement"],
        "normalized_value": method["normalized_value"], "unit": "",
        "applicability": f"minimum_missing_inputs={method['minimum_missing_inputs']}",
        "qa_status": "VERIFIED", "terminal_class": "METHOD_ONLY",
        "reuse_status": "METHOD_ONLY",
    }]
    if not page_ok(method_runtime[0]["physical_page"]):
        raise ValueError("HG/T 20569 appendix-A page chain invalid")
    method_path = out / "hgt20569_2013_appendix_a_method_only.csv"
    write_csv(method_path, method_runtime, STANDARD_FIELDS)
    require_runtime_safe(method_path)
    datasets.append(dataset_row(
        dataset_id="hgt20569_2013_appendix_a_method_only",
        family="reactor_or_agitator", subject="agitator_datasheet_required_input_method",
        standard_id="HG/T 20569-2013", version="2013",
        source_id=HGT20569_SOURCE_ID, source_sha=HGT20569_SOURCE_SHA,
        source_csv=method_path, filter_field="reuse_status", filter_values="METHOD_ONLY",
        reuse_class="METHOD_ONLY", audit=audit, approved_utc=approved_utc,
        notes="Four-page blank user-input template; queryable method only; no numeric defaults",
    ))
    write_csv(out / "dataset_registry.fragment.csv", datasets, DATASET_FIELDS)

    figures = read_csv(candidate / "figure_semantic_records.csv")
    require_unique(figures, "figure_record_id", "HG/T 20569 figure records")
    direct_ids = {f"{HGT20569_SOURCE_ID}:p0075:f01", f"{HGT20569_SOURCE_ID}:p0083:f01"}
    direct = [row for row in figures if row.get("terminal_status") == "DIMENSION_STRUCTURE_DATAIZED"]
    method_figures = [row for row in figures if row.get("terminal_status") == "METHOD_ONLY"]
    if {row["figure_id"] for row in direct} != direct_ids or len(direct) != 8 or len(method_figures) != 37:
        raise ValueError("HG/T 20569 figure scope/count changed")
    validate_figure_graph(direct)
    p75 = next(row for row in direct if row["figure_id"].endswith("p0075:f01") and row["record_kind"] == "dimension")
    forbidden_adjacent = {"k0", "k1", "k10", "ki", "θ", "β", "DJ", "S", "π", "r3", "r9"}
    if not {"b", "r"}.issubset(set(re.split(r"[、,，\s]+", p75["raw_label"]))) or any(token in p75["raw_label"].split("、") for token in forbidden_adjacent):
        raise ValueError("HG/T 20569 p75 figure symbols are incomplete or contaminated by adjacent table/formulas")
    allowed_origins = {
        "source_printed", "deterministic_geometry", "engineering_normalization"
    }
    figure_runtime: list[dict[str, str]] = []
    for row in figures:
        payload = json.loads(row.get("payload_json") or "{}")
        if row.get("statement_origin") not in allowed_origins or payload.get("statement_origin") not in allowed_origins:
            raise ValueError(f"HG/T 20569 statement origin invalid: {row['figure_record_id']}")
        source_page = str(row.get("physical_page") or "").strip()
        if not source_page.isdigit() or int(source_page) <= 0:
            raise ValueError(f"HG/T 20569 invalid figure page: {row['figure_record_id']}")
        # The raw printed title and the normalized explanatory statement can
        # have different origins; preserve both explicitly in runtime JSON.
        payload["raw_label_statement_origin"] = row["statement_origin"]
        payload["normalized_statement_origin"] = payload["statement_origin"]
        runtime_row = {field: row.get(field, "") for field in FIGURE_FIELDS}
        runtime_row["physical_page"] = str(int(source_page))
        runtime_row["payload_json"] = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        figure_runtime.append(runtime_row)
    figure_path = out / "hgt20569_2013_figure_semantics.csv"
    write_csv(figure_path, figure_runtime, FIGURE_FIELDS)
    require_runtime_safe(figure_path)
    figure_datasets = [
        figure_dataset_row(
            dataset_id="hgt20569_2013_two_dimension_structures",
            subject="propeller_and_inclined_blade_dimension_symbols",
            representation="dimension_structure", source_csv=figure_path,
            filter_values="DIMENSION_STRUCTURE_DATAIZED",
            reuse_class="DIRECT_REUSE_VERIFIED", audit=audit,
            approved_utc=approved_utc,
            notes="Two exact figures exposed as closed text-only entity/relation records; no image required at runtime",
        ),
        figure_dataset_row(
            dataset_id="hgt20569_2013_37_method_only_figures",
            subject="mechanical_agitator_figure_navigation_methods",
            representation="method_only", source_csv=figure_path,
            filter_values="METHOD_ONLY", reuse_class="METHOD_ONLY",
            audit=audit, approved_utc=approved_utc,
            notes="37 exact figure IDs retain titles and method navigation only; no numeric or geometry transfer",
        ),
    ]
    write_csv(out / "figure_dataset_registry.fragment.csv", figure_datasets, FIGURE_DATASET_FIELDS)

    terminal_source = candidate / "figure_terminal_audit.csv"
    terminal = read_csv(terminal_source)
    require_unique(terminal, "figure_id", "HG/T 20569 terminal figures")
    if len(terminal) != 39 or {row["figure_id"] for row in terminal} != {row["figure_id"] for row in figures}:
        raise ValueError("HG/T 20569 terminal figure ID set changed")
    terminal_runtime = []
    for row in terminal:
        runtime_row = {field: row.get(field, "") for field in FIGURE_TERMINAL_FIELDS}
        runtime_row["crop_sha256"] = row.get("crop_sha256") or row.get("image_sha256", "")
        terminal_runtime.append(runtime_row)
    if any(row["runtime_requires_image"].casefold() != "false" for row in terminal_runtime):
        raise ValueError("HG/T 20569 runtime image dependency is not closed")
    terminal_path = out / "hgt20569_2013_figure_terminal_audit.csv"
    write_csv(terminal_path, terminal_runtime, FIGURE_TERMINAL_FIELDS)
    require_runtime_safe(terminal_path)
    validation = {
        "schema": "vision-free-figure-terminal-validation-v1",
        "validation": "PASS", "failure_count": 0,
        "vision_capability": False, "source_image_runtime_access": "FORBIDDEN",
        "source_id": HGT20569_SOURCE_ID, "source_pdf_sha256": HGT20569_SOURCE_SHA,
        "terminal_figure_count": 39, "dimension_structure_count": 2,
        "method_only_count": 37, "structured_record_count": len(figures),
        "terminal_audit_sha256": sha256_path(terminal_path),
        "figure_runtime_sha256": sha256_path(figure_path),
    }
    validation_path = out / "hgt20569_2013_figure_validation.json"
    validation_path.write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    audit_sha = sha256_path(audit)
    candidate_rules = read_csv(candidate / "table_promotion_rules.fragment.csv")
    if len(candidate_rules) != 3:
        raise ValueError("HG/T 20569 direct table rule count changed")
    rules: list[dict[str, str]] = []
    for row in candidate_rules:
        if row.get("source_id") != HGT20569_SOURCE_ID or row.get("source_pdf_sha256") != HGT20569_SOURCE_SHA:
            raise ValueError("HG/T 20569 table rule source identity changed")
        rules.append({
            **{field: row.get(field, "") for field in TABLE_RULE_FIELDS},
            "qa_status": "VERIFIED", "evidence_path": str(audit.resolve()),
            "evidence_sha256": audit_sha,
            "note": "Exact reviewed direct table only; no inference beyond recorded applicability",
        })
    rules.append({
        "rule_id": "hgt20569_appendix_a_method_only_closed_chain",
        "source_id": HGT20569_SOURCE_ID, "source_pdf_sha256": HGT20569_SOURCE_SHA,
        "table_ids": f"{HGT20569_SOURCE_ID}:p0038:t01", "page_from": "37", "page_to": "40",
        "audit_status": "METHOD_ONLY",
        "executable_dataset_ids": "hgt20569_2013_appendix_a_method_only",
        "qa_status": "VERIFIED", "evidence_path": str(audit.resolve()),
        "evidence_sha256": audit_sha,
        "note": "Closed four-page blank input template; method route only; numeric defaults forbidden",
    })
    # The source-layer detector emitted a p130 table-shaped asset for a
    # narrative/reference region.  Parent visual review confirmed that it has
    # no table grid or executable cells.  Close that exact extraction artifact
    # as NOT_APPLICABLE instead of leaving it in the real-table work queue.
    rules.append({
        "rule_id": "hgt20569_p0130_non_table_extraction_artifact",
        "source_id": HGT20569_SOURCE_ID, "source_pdf_sha256": HGT20569_SOURCE_SHA,
        "table_ids": f"{HGT20569_SOURCE_ID}:p0130:t01", "page_from": "130", "page_to": "130",
        "audit_status": "NOT_APPLICABLE", "executable_dataset_ids": "",
        "qa_status": "VERIFIED", "evidence_path": str(audit.resolve()),
        "evidence_sha256": audit_sha,
        "note": "Verified non-table narrative/reference extraction artifact; no grid, cells, values, or executable dataset",
    })
    write_csv(out / "table_promotion_rules.fragment.csv", rules, TABLE_RULE_FIELDS)
    registry = [{
        "source_id": HGT20569_SOURCE_ID, "source_sha256": HGT20569_SOURCE_SHA,
        "terminal_audit_csv": str(terminal_path.resolve()),
        "terminal_audit_sha256": sha256_path(terminal_path),
        "validation_path": str(validation_path.resolve()),
        "validation_sha256": sha256_path(validation_path),
        "promotion_audit_path": str(audit.resolve()),
        "promotion_audit_sha256": audit_sha,
        "structured_dataset_id": "hgt20569_2013_two_dimension_structures|hgt20569_2013_37_method_only_figures",
        "qa_status": "VERIFIED", "promotion_state": "APPROVED",
        "approved_utc": approved_utc,
        "notes": "Exact 39-ID terminal set: 2 dataized dimension structures and 37 method-only figure routes",
    }]
    write_csv(out / "figure_terminal_audit_registry.fragment.csv", registry, FIGURE_TERMINAL_REGISTRY_FIELDS)
    return {
        "batch": "hgt20569", "status": "PASS", "direct_table_records": total_direct,
        "table_datasets": len(datasets), "table_promotion_rules": len(rules), "direct_figures": 2,
        "method_only_figures": 37, "figure_records": len(figures),
    }


def prepare_gbt1220(candidate: Path, out: Path, audit: Path, approved_utc: str) -> dict:
    require_file(audit, 200)
    source = candidate / "audit" / "figure_terminal_audit.csv"
    rows = read_csv(source)
    require_unique(rows, "figure_id", "GB/T 1220 terminal figures")
    if len(rows) != 39 or any(
        row.get("terminal_class") != "NOT_APPLICABLE"
        or row.get("qa_status") != "VERIFIED_NOT_APPLICABLE"
        or row.get("runtime_requires_image", "").casefold() != "false"
        or row.get("structured_record_count") != "0"
        for row in rows
    ):
        raise ValueError("GB/T 1220 terminal figure classification changed")
    runtime = [{field: row.get(field, "") for field in FIGURE_TERMINAL_FIELDS} for row in rows]
    terminal_path = out / "gbt1220_2007_figure_terminal_audit.csv"
    write_csv(terminal_path, runtime, FIGURE_TERMINAL_FIELDS)
    require_runtime_safe(terminal_path)
    validation = {
        "schema": "vision-free-figure-terminal-validation-v1",
        "validation": "PASS", "failure_count": 0,
        "vision_capability": False, "source_image_runtime_access": "FORBIDDEN",
        "source_id": GBT1220_SOURCE_ID, "source_pdf_sha256": GBT1220_SOURCE_SHA,
        "terminal_figure_count": 39, "not_applicable_count": 39,
        "structured_dataset_count": 0,
        "terminal_audit_sha256": sha256_path(terminal_path),
    }
    validation_path = out / "gbt1220_2007_figure_validation.json"
    validation_path.write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    audit_sha = sha256_path(audit)
    registry = [{
        "source_id": GBT1220_SOURCE_ID, "source_sha256": GBT1220_SOURCE_SHA,
        "terminal_audit_csv": str(terminal_path.resolve()),
        "terminal_audit_sha256": sha256_path(terminal_path),
        "validation_path": str(validation_path.resolve()),
        "validation_sha256": sha256_path(validation_path),
        "promotion_audit_path": str(audit.resolve()),
        "promotion_audit_sha256": audit_sha,
        "structured_dataset_id": "", "qa_status": "VERIFIED",
        "promotion_state": "APPROVED", "approved_utc": approved_utc,
        "notes": "All 39 extracted figure assets are verified page/table/watermark fragments; no figure dataset promoted",
    }]
    write_csv(out / "figure_terminal_audit_registry.fragment.csv", registry, FIGURE_TERMINAL_REGISTRY_FIELDS)
    return {"batch": "gbt1220", "status": "PASS", "terminal_figures": 39, "figure_datasets": 0}


def prepare_gbt1220_table(candidate: Path, out: Path, audit: Path, approved_utc: str) -> dict:
    """Prepare the exact reviewed GB/T 1220-2007 Table 16 record set."""
    require_file(audit, 200)
    source = candidate / "candidate_data" / "gbt1220_table16_records.csv"
    require_file(source)
    rows = read_csv(source)
    if len(rows) != 15:
        raise ValueError(f"GB/T 1220 Table 16 must contain exactly 15 records: {len(rows)}")
    for row in rows:
        if (
            not row.get("raw_value", "").strip()
            or not row.get("normalized_value", "").strip()
            or not page_ok(row.get("physical_page", ""))
        ):
            raise ValueError(f"GB/T 1220 Table 16 incomplete direct record: {row.get('record_id', '')}")
    expected_body_ids = {
        f"{GBT1220_SOURCE_ID}:p0019:t01:r{index:02d}" for index in range(1, 15)
    }
    body_rows = [row for row in rows if row.get("record_id") in expected_body_ids]
    if len(body_rows) != 14:
        raise ValueError(f"GB/T 1220 Table 16 must contain exactly 14 body rows: {len(body_rows)}")
    if any(row.get("record_type") not in {"table_row", "inspection_sampling_rule"} for row in body_rows):
        raise ValueError("GB/T 1220 Table 16 body record type changed")
    row_semantic_keys = {
        "inspection_item", "sampling_quantity_printed",
        "sampling_location_printed", "test_method_printed", "inheritance_flags",
    }
    inheritance_keys = {"sampling_quantity", "sampling_location", "test_method"}
    inherited_location_rows = {3, 5, 9, 11, 14}
    for row in body_rows:
        try:
            normalized_row = json.loads(row["normalized_value"])
        except json.JSONDecodeError as exc:
            raise ValueError(f"GB/T 1220 Table 16 row semantics invalid JSON: {row['record_id']}") from exc
        flags = normalized_row.get("inheritance_flags")
        if (
            set(normalized_row) != row_semantic_keys
            or not isinstance(flags, dict)
            or set(flags) != inheritance_keys
            or any(not isinstance(value, bool) for value in flags.values())
        ):
            raise ValueError(f"GB/T 1220 Table 16 row semantics incomplete: {row['record_id']}")
        row_number = int(row["record_id"].rsplit("r", 1)[1])
        expected_flags = {
            "sampling_quantity": False,
            "sampling_location": row_number in inherited_location_rows,
            "test_method": False,
        }
        if flags != expected_flags:
            raise ValueError(f"GB/T 1220 Table 16 source-verified merge pattern changed: {row['record_id']}")
    footnotes = [
        row for row in rows
        if row.get("record_id") == f"{GBT1220_SOURCE_ID}:p0019:t01:footnote:a"
        and row.get("record_type") == "table_footnote"
    ]
    if len(footnotes) != 1 or footnotes[0].get("raw_value", "").strip() != GBT1220_TABLE16_FOOTNOTE:
        raise ValueError("GB/T 1220 Table 16 printed footnote is missing or changed")
    try:
        normalized_footnote = json.loads(footnotes[0].get("normalized_value", ""))
    except json.JSONDecodeError as exc:
        raise ValueError("GB/T 1220 Table 16 structured footnote is invalid JSON") from exc
    if normalized_footnote != GBT1220_TABLE16_FOOTNOTE_NORMALIZED:
        raise ValueError("GB/T 1220 Table 16 structured footnote conditions are missing or changed")
    for row in body_rows:
        row_number = int(row["record_id"].rsplit("r", 1)[1])
        normalized_row = json.loads(row["normalized_value"])
        expected_values = GBT1220_TABLE16_ROWS[row_number - 1]
        actual_values = (
            normalized_row["inspection_item"],
            normalized_row["sampling_quantity_printed"],
            normalized_row["sampling_location_printed"],
            normalized_row["test_method_printed"],
        )
        if actual_values != expected_values:
            raise ValueError(f"GB/T 1220 Table 16 printed row semantics changed: {row['record_id']}")
    if {row["record_id"] for row in body_rows} != expected_body_ids:
        raise ValueError("GB/T 1220 Table 16 body record ID set changed")
    require_unique(rows, "record_id", "GB/T 1220 Table 16")
    expected_table_id = f"{GBT1220_SOURCE_ID}:p0019:t01"
    for row in rows:
        if (
            row.get("physical_page") != "19"
            or not row.get("source_table", "").strip()
            or not row.get("source_section", "").strip()
            or not row.get("source_row_label", "").strip()
            or not row.get("source_column_label", "").strip()
            or not row.get("source_bbox_pt", "").strip()
            or row.get("qa_status") not in {"VERIFIED", "VERIFIED_PRINTED_GLYPH"}
            or row.get("terminal_class", "") not in {"", "DIRECT_REUSE_VERIFIED"}
            or row.get("reuse_status") != "DIRECT_REUSE_VERIFIED"
        ):
            raise ValueError(f"GB/T 1220 Table 16 source/status fields changed: {row['record_id']}")

    out.mkdir(parents=True, exist_ok=True)
    runtime = [
        {field: row.get(field, "") for field in STANDARD_FIELDS} | {
            "source_table": expected_table_id,
            "qa_status": "VERIFIED",
            "terminal_class": "DIRECT_REUSE_VERIFIED",
            "reuse_status": "DIRECT_REUSE_VERIFIED",
        }
        for row in rows
    ]
    runtime_path = out / "gbt1220_2007_table16_records.csv"
    write_csv(runtime_path, runtime, STANDARD_FIELDS)
    require_runtime_safe(runtime_path)
    dataset_id = "gbt1220_2007_table16_inspection_sampling"
    datasets = [dataset_row(
        dataset_id=dataset_id,
        family="material_or_general_equipment",
        subject="steel_bar_inspection_sampling_and_test_method",
        standard_id="GB/T 1220-2007", version="2007",
        source_id=GBT1220_SOURCE_ID, source_sha=GBT1220_SOURCE_SHA,
        source_csv=runtime_path, filter_field="reuse_status",
        filter_values="DIRECT_REUSE_VERIFIED", reuse_class="DIRECT_REUSE_VERIFIED",
        audit=audit, approved_utc=approved_utc,
        notes="Exact Table 16: 14 printed inspection rows plus the material sampling footnote; merged-cell inheritance remains explicit",
    )]
    write_csv(out / "dataset_registry.fragment.csv", datasets, DATASET_FIELDS)
    audit_sha = sha256_path(audit)
    rules = [{
        "rule_id": "gbt1220_table_16_closed",
        "source_id": GBT1220_SOURCE_ID,
        "source_pdf_sha256": GBT1220_SOURCE_SHA,
        "table_ids": expected_table_id,
        "page_from": "19", "page_to": "19",
        "audit_status": "DIRECT_REUSE_VERIFIED",
        "executable_dataset_ids": dataset_id,
        "qa_status": "VERIFIED",
        "evidence_path": str(audit.resolve()),
        "evidence_sha256": audit_sha,
        "note": "Exact printed Table 16 including footnote a; remaining GB/T 1220 key tables stay blocked",
    }]
    write_csv(out / "table_promotion_rules.fragment.csv", rules, TABLE_RULE_FIELDS)
    return {
        "batch": "gbt1220_table", "status": "PASS", "records": len(runtime),
        "table_datasets": len(datasets), "table_promotion_rules": len(rules),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "batch", choices=("gbt1502", "hgt20569", "gbt1220", "gbt1220_table")
    )
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--promotion-audit", type=Path, required=True)
    parser.add_argument("--approved-utc", required=True)
    args = parser.parse_args()
    candidate = args.candidate_dir.resolve()
    out = args.out_dir.resolve()
    audit = args.promotion_audit.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if args.batch == "gbt1502":
        result = prepare_gbt1502(candidate, out, audit, args.approved_utc)
    elif args.batch == "hgt20569":
        result = prepare_hgt20569(candidate, out, audit, args.approved_utc)
    elif args.batch == "gbt1220_table":
        result = prepare_gbt1220_table(candidate, out, audit, args.approved_utc)
    else:
        result = prepare_gbt1220(candidate, out, audit, args.approved_utc)
    result["output_dir"] = str(out)
    result["promotion_audit_sha256"] = sha256_path(audit)
    summary = out / "promotion_prepare_summary.json"
    summary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
