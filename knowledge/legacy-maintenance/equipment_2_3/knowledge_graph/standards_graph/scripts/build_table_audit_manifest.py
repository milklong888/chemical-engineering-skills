#!/usr/bin/env python3
"""Enumerate extracted tables without promoting them to executable data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


NON_TRANSFER_KINDS = {
    "textbook",
    "design_book",
    "handbook",
    "handbook_or_compilation",
    "graduation_case",
    "course_textbook",
    "course_case",
    "case_or_course_design",
}
STANDARD_KINDS = {"standard", "construction_standard"}
RELEVANCE_PATTERNS = {
    "dimension_series": re.compile(r"公称|外径|内径|壁厚|尺寸|系列|规格|直径|长度|DN|NPS", re.I),
    "pressure_temperature": re.compile(r"压力|温度|PN|Class|压力.?温度", re.I),
    "material_property": re.compile(r"材料|材质|牌号|许用应力|屈服|抗拉|化学成分|密度", re.I),
    "type_basic_parameter": re.compile(r"型式|类型|基本参数|型号|标记|公称容积|换热面积|管程|壳程", re.I),
    "coefficient_or_limit": re.compile(r"系数|允许|极限|偏差|裕量|最大|最小", re.I),
    "connection_component": re.compile(r"法兰|垫片|螺栓|螺母|管件|弯头|三通|阀门|连接", re.I),
}


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest().upper()


def read_csv(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_promotion_rules(path: Path | None) -> list[dict]:
    if path is None or not path.is_file():
        return []
    rules = read_csv(path)
    allowed = {
        "DIRECT_REUSE_VERIFIED",
        "METHOD_ONLY",
        "NOT_APPLICABLE",
        "OBSOLETE_FORBIDDEN",
    }
    for rule in rules:
        if rule.get("qa_status") != "VERIFIED":
            raise ValueError(f"{rule.get('rule_id')}: promotion rule is not VERIFIED")
        if rule.get("audit_status") not in allowed:
            raise ValueError(f"{rule.get('rule_id')}: invalid promoted audit status")
        evidence = Path(rule["evidence_path"])
        if not evidence.is_file() or sha256_path(evidence) != rule["evidence_sha256"].upper():
            raise ValueError(f"{rule.get('rule_id')}: promotion evidence hash mismatch")
    return rules


def matching_promotion_rule(
    rules: list[dict],
    doc_id: str,
    source_hash: str,
    table_id: str,
    page_1based: str,
) -> dict | None:
    try:
        page = int(page_1based)
    except (TypeError, ValueError):
        return None
    matches: list[dict] = []
    for rule in rules:
        if rule.get("source_id") != doc_id:
            continue
        if rule.get("source_pdf_sha256", "").upper() != source_hash.upper():
            continue
        exact_ids = {
            item.strip()
            for item in str(rule.get("table_ids") or "").split("|")
            if item.strip()
        }
        if exact_ids:
            if table_id in exact_ids:
                matches.append(rule)
            continue
        if int(rule.get("page_from") or -1) <= page <= int(rule.get("page_to") or -1):
            matches.append(rule)
    if len(matches) > 1:
        raise ValueError(f"{doc_id} page {page}: overlapping promotion rules")
    return matches[0] if matches else None


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def numeric_like(value: str) -> bool:
    text = value.strip().replace(",", "")
    return bool(re.fullmatch(r"[-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?", text))


def table_text_and_stats(table_csv: Path, cells_csv: Path) -> tuple[str, dict]:
    table_rows = read_csv(table_csv)
    text_parts: list[str] = []
    numeric_cells = 0
    for row in table_rows:
        for value in row.values():
            value = str(value or "").strip()
            if value:
                text_parts.append(value)
                numeric_cells += int(numeric_like(value))
    low_confidence = 0
    nonblank_audit_cells = 0
    for row in read_csv(cells_csv):
        raw = str(row.get("raw_text") or "").strip()
        if not raw:
            continue
        nonblank_audit_cells += 1
        confidence = str(row.get("ocr_confidence") or "").strip()
        if confidence:
            try:
                low_confidence += float(confidence) < 80.0
            except ValueError:
                low_confidence += 1
    return " ".join(text_parts), {
        "numeric_cell_count": numeric_cells,
        "nonblank_audit_cell_count": nonblank_audit_cells,
        "low_confidence_nonblank_cell_count": low_confidence,
    }


def proposed_class(source_kind: str, authority_status: str) -> str:
    if source_kind == "obsolete_standard" or authority_status in {
        "OBSOLETE_FORBIDDEN",
        "WITHDRAWN",
    }:
        return "OBSOLETE_FORBIDDEN"
    if source_kind in NON_TRANSFER_KINDS:
        return "FORBIDDEN_TRANSFER"
    if source_kind in STANDARD_KINDS:
        return "NEEDS_REVIEW"
    return "METHOD_ONLY"


def build_manifest(
    source_inventory: Path,
    documents_root: Path,
    promotion_rules_path: Path | None = None,
) -> tuple[list[dict], dict]:
    sources = {row["sha256"].upper(): row for row in read_csv(source_inventory)}
    promotion_rules = load_promotion_rules(promotion_rules_path)
    rows: list[dict] = []
    for package in sorted(documents_root.glob("*/status.json")):
        try:
            status = json.loads(package.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        source_hash = str(status.get("source_pdf_sha256") or "").upper()
        source = sources.get(source_hash, {})
        package_root = package.parent
        for table in read_csv(package_root / "tables.csv"):
            table_csv = package_root / str(table.get("csv_path") or "")
            cells_csv = package_root / str(table.get("cell_audit_csv_path") or "")
            text, stats = table_text_and_stats(table_csv, cells_csv)
            tags = [name for name, pattern in RELEVANCE_PATTERNS.items() if pattern.search(text)]
            source_kind = source.get("source_kind") or "unknown"
            authority_status = source.get("authority_status") or "UNVERIFIED"
            reuse = proposed_class(source_kind, authority_status)
            key_candidate = bool(tags) and stats["numeric_cell_count"] > 0
            promotion = matching_promotion_rule(
                promotion_rules,
                str(status.get("doc_id") or ""),
                source_hash,
                str(table.get("table_id") or ""),
                str(table.get("page_1based") or ""),
            )
            audit_status = reuse if reuse != "NEEDS_REVIEW" else "NEEDS_REVIEW"
            executable_dataset_id = ""
            reviewer_note = ""
            promotion_rule_id = ""
            promotion_evidence_sha256 = ""
            if promotion:
                audit_status = promotion["audit_status"]
                reuse = promotion["audit_status"]
                executable_dataset_id = promotion.get("executable_dataset_ids", "")
                reviewer_note = promotion.get("note", "")
                promotion_rule_id = promotion.get("rule_id", "")
                promotion_evidence_sha256 = promotion.get("evidence_sha256", "")
                if audit_status == "DIRECT_REUSE_VERIFIED" and authority_status != "CURRENT":
                    raise ValueError(
                        f"{table.get('table_id')}: direct promotion source is not current"
                    )
            rows.append(
                {
                    "table_id": table.get("table_id", ""),
                    "doc_id": status.get("doc_id", ""),
                    "source_id": source.get("source_id", ""),
                    "source_pdf_sha256": source_hash,
                    "standard_id": source.get("standard_id", ""),
                    "standard_year": source.get("standard_year", ""),
                    "source_kind": source_kind,
                    "families_json": source.get("families_json", "[]"),
                    "authority_status": authority_status,
                    "page_1based": table.get("page_1based", ""),
                    "table_order": table.get("table_order", ""),
                    "caption": table.get("caption", ""),
                    "row_count": table.get("row_count", ""),
                    "column_count": table.get("column_count", ""),
                    "nonempty_cells": table.get("nonempty_cells", ""),
                    "numeric_cell_count": stats["numeric_cell_count"],
                    "nonblank_audit_cell_count": stats["nonblank_audit_cell_count"],
                    "low_confidence_nonblank_cell_count": stats[
                        "low_confidence_nonblank_cell_count"
                    ],
                    "method": table.get("method", ""),
                    "geometry_preserved": table.get("geometry_preserved", ""),
                    "structure_confidence": table.get("structure_confidence", ""),
                    "raw_numeric_reuse_flag": table.get("numeric_reuse_allowed", ""),
                    "relevance_tags_json": json.dumps(tags, ensure_ascii=False),
                    "key_table_candidate": key_candidate,
                    "proposed_reuse_class": reuse,
                    "audit_status": audit_status,
                    "table_csv_path": str(table_csv),
                    "table_csv_sha256": sha256_path(table_csv) if table_csv.is_file() else "",
                    "cell_audit_csv_path": str(cells_csv),
                    "cell_audit_csv_sha256": sha256_path(cells_csv) if cells_csv.is_file() else "",
                    "executable_dataset_id": executable_dataset_id,
                    "promotion_rule_id": promotion_rule_id,
                    "promotion_evidence_sha256": promotion_evidence_sha256,
                    "reviewer_note": reviewer_note,
                }
            )
    counts = Counter(row["audit_status"] for row in rows)
    summary = {
        "schema": "equipment-standard-table-audit-manifest-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "package_count": len({row["doc_id"] for row in rows}),
        "table_count": len(rows),
        "key_table_candidate_count": sum(bool(row["key_table_candidate"]) for row in rows),
        "audit_status_counts": dict(sorted(counts.items())),
        "raw_reuse_flags_ignored_count": sum(
            str(row["raw_numeric_reuse_flag"]).casefold() == "true" for row in rows
        ),
        "direct_reuse_verified_count": sum(
            row["audit_status"] == "DIRECT_REUSE_VERIFIED" for row in rows
        ),
        "promotion_rule_count": len(promotion_rules),
        "promoted_table_count": sum(bool(row["promotion_rule_id"]) for row in rows),
        "unresolved_standard_table_count": sum(
            row["audit_status"] == "NEEDS_REVIEW" for row in rows
        ),
        "first_stage_pass": not any(
            bool(row["key_table_candidate"]) and row["audit_status"] == "NEEDS_REVIEW"
            for row in rows
        ),
    }
    return rows, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-inventory", type=Path, required=True)
    parser.add_argument("--documents-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--promotion-rules", type=Path)
    args = parser.parse_args()
    rows, summary = build_manifest(
        args.source_inventory.resolve(),
        args.documents_root.resolve(),
        args.promotion_rules.resolve() if args.promotion_rules else None,
    )
    fields = [
        "table_id",
        "doc_id",
        "source_id",
        "source_pdf_sha256",
        "standard_id",
        "standard_year",
        "source_kind",
        "families_json",
        "authority_status",
        "page_1based",
        "table_order",
        "caption",
        "row_count",
        "column_count",
        "nonempty_cells",
        "numeric_cell_count",
        "nonblank_audit_cell_count",
        "low_confidence_nonblank_cell_count",
        "method",
        "geometry_preserved",
        "structure_confidence",
        "raw_numeric_reuse_flag",
        "relevance_tags_json",
        "key_table_candidate",
        "proposed_reuse_class",
        "audit_status",
        "table_csv_path",
        "table_csv_sha256",
        "cell_audit_csv_path",
        "cell_audit_csv_sha256",
        "executable_dataset_id",
        "promotion_rule_id",
        "promotion_evidence_sha256",
        "reviewer_note",
    ]
    write_csv(args.out_dir / "table_audit_manifest.csv", rows, fields)
    (args.out_dir / "table_audit_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
