#!/usr/bin/env python3
"""Register every extracted figure and route it to a machine-readable QA target.

The source-layer image is reused as offline audit evidence.  Its existence never
means that the figure has been digitized for a non-visual production runtime.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import struct
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

DATAIZED_TERMINAL_CLASSES = {
    "DIMENSION_STRUCTURE": "DIMENSION_STRUCTURE_DATAIZED",
    "DIMENSION_STRUCTURE_DATAIZED": "DIMENSION_STRUCTURE_DATAIZED",
    "QUANTITATIVE_CURVE": "QUANTITATIVE_CURVE_DATAIZED",
    "QUANTITATIVE_CURVE_DATAIZED": "QUANTITATIVE_CURVE_DATAIZED",
    "PROCESS_LOGIC": "PROCESS_LOGIC_DATAIZED",
    "PROCESS_LOGIC_DATAIZED": "PROCESS_LOGIC_DATAIZED",
    "SYMBOL_ICON": "SYMBOL_ICON_DATAIZED",
    "SYMBOL_ICON_DATAIZED": "SYMBOL_ICON_DATAIZED",
}
ALLOWED_PROMOTED_TERMINALS = set(DATAIZED_TERMINAL_CLASSES) | {
    "NOT_APPLICABLE",
    "METHOD_ONLY",
    "SOFTWARE_BOUNDARY",
    "VENDOR_BOUNDARY",
    "SOURCE_UNREADABLE_BLOCKED",
    "SEMANTIC_TRANSCRIPTION_PENDING",
    "OBSOLETE_FORBIDDEN",
    "FORBIDDEN_TRANSFER",
}

FIGURE_PATTERNS = (
    (
        "QUANTITATIVE_CURVE_NEEDS_DIGITIZATION",
        re.compile(
            r"曲线|关系图|线图|诺模图|坐标图|特性图|性能图|允许应力|压力.?温度|"
            r"温度.?压力|压降|传热系数|摩擦系数|阻力系数|负荷性能|关联图|nomogram|curve",
            re.I,
        ),
    ),
    (
        "PROCESS_LOGIC_NEEDS_GRAPH",
        re.compile(r"流程|工艺流程|流程图|系统图|管路|循环|控制逻辑|flow.?sheet|process", re.I),
    ),
    (
        "SYMBOL_ICON_NEEDS_SEMANTIC_RECORD",
        re.compile(r"图例|符号|图形符号|代号|标志|symbol|legend", re.I),
    ),
    (
        "DIMENSION_STRUCTURE_NEEDS_GRAPH",
        re.compile(
            r"结构|构造|型式|形式|示意|剖面|断面|布置|尺寸|节点|连接|法兰|管板|封头|"
            r"支座|吊耳|塔板|降液管|堰|换热器|容器|反应器|管件|阀门|structure|section",
            re.I,
        ),
    ),
)


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


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def load_terminal_audit_overlays(registry_path: Path | None) -> dict[str, dict]:
    overlays: dict[str, dict] = {}
    if registry_path is None:
        return overlays
    for entry in read_csv(registry_path):
        if entry.get("promotion_state") != "APPROVED":
            continue
        source_id = str(entry.get("source_id") or "").strip()
        if not source_id or source_id in overlays:
            raise ValueError(f"duplicate or empty terminal-audit source_id: {source_id}")
        if entry.get("qa_status") != "VERIFIED":
            raise ValueError(f"{source_id}: terminal audit is not VERIFIED")
        audit_csv = Path(entry["terminal_audit_csv"])
        validation_path = Path(entry["validation_path"])
        promotion_audit = Path(entry["promotion_audit_path"])
        for path, hash_field in (
            (audit_csv, "terminal_audit_sha256"),
            (validation_path, "validation_sha256"),
            (promotion_audit, "promotion_audit_sha256"),
        ):
            if not path.is_file():
                raise FileNotFoundError(path)
            if sha256_path(path) != str(entry.get(hash_field) or "").upper():
                raise ValueError(f"{source_id}: {hash_field} mismatch")
        validation = json.loads(validation_path.read_text(encoding="utf-8"))
        if (
            validation.get("validation") != "PASS"
            or validation.get("failure_count") != 0
            or validation.get("vision_capability") is not False
            or validation.get("source_image_runtime_access") != "FORBIDDEN"
        ):
            raise ValueError(f"{source_id}: terminal audit validation is not a vision-free PASS")
        audit_rows = read_csv(audit_csv)
        by_id = {row.get("figure_id", ""): row for row in audit_rows}
        if not audit_rows or "" in by_id or len(by_id) != len(audit_rows):
            raise ValueError(f"{source_id}: terminal audit figure IDs are empty or duplicated")
        for figure_id, row in by_id.items():
            terminal_class = str(row.get("terminal_class") or "").strip()
            if terminal_class not in ALLOWED_PROMOTED_TERMINALS:
                raise ValueError(f"{source_id}: invalid terminal class for {figure_id}")
            needs_review = str(row.get("needs_review") or "").casefold()
            if terminal_class == "SEMANTIC_TRANSCRIPTION_PENDING":
                if needs_review != "true":
                    raise ValueError(
                        f"{source_id}: readable transcription-pending figure is not open for review: {figure_id}"
                    )
                if not str(row.get("minimum_next_evidence") or "").strip():
                    raise ValueError(
                        f"{source_id}: transcription-pending figure lacks minimum next evidence: {figure_id}"
                    )
            elif needs_review != "false":
                raise ValueError(f"{source_id}: unresolved promoted figure {figure_id}")
            if str(row.get("runtime_requires_image") or "").casefold() != "false":
                raise ValueError(f"{source_id}: promoted figure still requires an image")
        overlays[source_id] = {"entry": entry, "rows": by_id}
    return overlays


def image_dimensions(path: Path) -> tuple[int | str, int | str]:
    """Read dimensions without importing an image/vision dependency."""
    if not path.is_file():
        return "", ""
    with path.open("rb") as handle:
        header = handle.read(24)
    if header.startswith(b"\x89PNG\r\n\x1a\n") and len(header) >= 24:
        width, height = struct.unpack(">II", header[16:24])
        return width, height
    return "", ""


def proposed_figure_target(caption: str) -> str:
    text = str(caption or "").strip()
    for target, pattern in FIGURE_PATTERNS:
        if pattern.search(text):
            return target
    # A weak or empty OCR caption cannot prove that a figure is merely
    # explanatory.  It must remain open for a page-image classification.
    return "UNCLASSIFIED_NEEDS_VISUAL_REVIEW"


def source_boundary(source_kind: str, authority_status: str) -> str:
    if source_kind == "obsolete_standard" or authority_status in {
        "OBSOLETE_FORBIDDEN",
        "WITHDRAWN",
    }:
        return "OBSOLETE_FORBIDDEN"
    if source_kind in NON_TRANSFER_KINDS:
        return "FORBIDDEN_TRANSFER"
    if source_kind in STANDARD_KINDS:
        return "STANDARD_REVIEW_REQUIRED"
    return "METHOD_ONLY"


def build_manifest(
    source_inventory: Path,
    documents_root: Path,
    terminal_audit_registry: Path | None = None,
) -> tuple[list[dict], dict]:
    sources = {row["sha256"].upper(): row for row in read_csv(source_inventory)}
    terminal_overlays = load_terminal_audit_overlays(terminal_audit_registry)
    rows: list[dict] = []
    package_ids: set[str] = set()

    for status_path in sorted(documents_root.glob("*/status.json")):
        try:
            status = json.loads(status_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        package_root = status_path.parent
        source_hash = str(status.get("source_pdf_sha256") or "").upper()
        source = sources.get(source_hash, {})
        source_kind = source.get("source_kind") or "unknown"
        authority_status = source.get("authority_status") or "UNVERIFIED"
        boundary = source_boundary(source_kind, authority_status)
        package_ids.add(str(status.get("doc_id") or package_root.name))

        package_figures = read_csv(package_root / "figures.csv")
        overlay = terminal_overlays.get(str(source.get("source_id") or ""))
        if overlay:
            entry = overlay["entry"]
            if str(entry.get("source_sha256") or "").upper() != source_hash:
                raise ValueError(f"{entry['source_id']}: terminal audit source hash mismatch")
            source_figure_ids = {row.get("figure_id", "") for row in package_figures}
            audit_figure_ids = set(overlay["rows"])
            if source_figure_ids != audit_figure_ids:
                raise ValueError(f"{entry['source_id']}: terminal audit does not cover the exact figure set")

        for figure in package_figures:
            relative_image_path = str(figure.get("image_path") or "")
            image_path = package_root / relative_image_path
            exists = image_path.is_file()
            width, height = image_dimensions(image_path)
            proposed_target = proposed_figure_target(str(figure.get("caption") or ""))

            if not exists:
                terminal_class = "SOURCE_UNREADABLE_BLOCKED"
                audit_status = "SOURCE_UNREADABLE_BLOCKED"
                dataization_state = "BLOCKED_MISSING_AUDIT_IMAGE"
            elif boundary in {"OBSOLETE_FORBIDDEN", "FORBIDDEN_TRANSFER"}:
                terminal_class = boundary
                audit_status = boundary
                dataization_state = "TERMINAL_CLASSIFIED_NOT_TRANSFERABLE"
            elif boundary == "STANDARD_REVIEW_REQUIRED":
                terminal_class = proposed_target
                audit_status = "NEEDS_REVIEW"
                dataization_state = "REGISTERED_IMAGE_NOT_DATAIZED"
            else:
                terminal_class = "METHOD_ONLY"
                audit_status = "METHOD_ONLY"
                dataization_state = "TERMINAL_CLASSIFIED_METHOD_ONLY"

            structured_dataset_id = ""
            structured_record_count = ""
            axis_or_object_qa_status = ""
            error_bound_or_relation_qa = ""
            vision_disabled_replay_status = ""
            reviewer_note = ""
            if overlay:
                promoted = overlay["rows"][figure.get("figure_id", "")]
                if str(promoted.get("crop_sha256") or "").upper() != (
                    sha256_path(image_path) if exists else ""
                ):
                    raise ValueError(f"{figure.get('figure_id')}: promoted crop hash mismatch")
                raw_terminal = str(promoted.get("terminal_class") or "").strip()
                if raw_terminal == "SEMANTIC_TRANSCRIPTION_PENDING":
                    terminal_class = raw_terminal
                    audit_status = "NEEDS_REVIEW"
                    dataization_state = "READABLE_IMAGE_SEMANTIC_TRANSCRIPTION_PENDING"
                else:
                    terminal_class = DATAIZED_TERMINAL_CLASSES.get(raw_terminal, raw_terminal)
                    audit_status = (
                        "DIRECT_REUSE_VERIFIED"
                        if raw_terminal in DATAIZED_TERMINAL_CLASSES
                        else terminal_class
                    )
                    dataization_state = (
                        "TERMINAL_DATAIZED"
                        if raw_terminal in DATAIZED_TERMINAL_CLASSES
                        else f"TERMINAL_CLASSIFIED_{terminal_class}"
                    )
                structured_dataset_id = (
                    overlay["entry"].get("structured_dataset_id", "")
                    if raw_terminal in DATAIZED_TERMINAL_CLASSES
                    else ""
                )
                structured_record_count = promoted.get("structured_record_count", "")
                axis_or_object_qa_status = promoted.get("qa_status", "")
                error_bound_or_relation_qa = promoted.get("visual_review_basis", "")
                vision_disabled_replay_status = "PASS"
                reviewer_note = promoted.get("terminal_reason", "")

            rows.append(
                {
                    "figure_id": figure.get("figure_id", ""),
                    "doc_id": status.get("doc_id", ""),
                    "source_id": source.get("source_id", ""),
                    "source_pdf_sha256": source_hash,
                    "standard_id": source.get("standard_id", ""),
                    "standard_year": source.get("standard_year", ""),
                    "source_kind": source_kind,
                    "families_json": source.get("families_json", "[]"),
                    "authority_status": authority_status,
                    "source_boundary": boundary,
                    "page_1based": figure.get("page_1based", ""),
                    "figure_order": figure.get("figure_order", ""),
                    "caption": figure.get("caption", ""),
                    "bbox_pt": figure.get("bbox_pt", ""),
                    "method": figure.get("method", ""),
                    "extractor_key_figure_flag": figure.get("key_figure", ""),
                    "extractor_asset_qa_status": figure.get("asset_qa_status", ""),
                    "image_path": str(image_path),
                    "image_exists": exists,
                    "image_width_px": width,
                    "image_height_px": height,
                    "image_sha256": sha256_path(image_path) if exists else "",
                    "reused_existing_image_asset": exists,
                    "proposed_dataization_target": proposed_target,
                    "terminal_class": terminal_class,
                    "audit_status": audit_status,
                    "dataization_state": dataization_state,
                    # Until a standard figure is visually classified and
                    # terminally closed, assume that a non-visual runtime
                    # representation is required.  This prevents weak OCR
                    # captions from silently dropping useful figure facts.
                    "machine_representation_required": audit_status == "NEEDS_REVIEW",
                    "structured_dataset_id": structured_dataset_id,
                    "structured_record_count": structured_record_count,
                    "axis_or_object_qa_status": axis_or_object_qa_status,
                    "error_bound_or_relation_qa": error_bound_or_relation_qa,
                    "vision_disabled_replay_status": vision_disabled_replay_status,
                    "reviewer_note": reviewer_note,
                }
            )

    audit_counts = Counter(row["audit_status"] for row in rows)
    target_counts = Counter(row["terminal_class"] for row in rows)
    summary = {
        "schema": "equipment-standard-figure-audit-manifest-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "package_count": len(package_ids),
        "figure_count": len(rows),
        "existing_image_count": sum(bool(row["image_exists"]) for row in rows),
        "reused_existing_image_asset_count": sum(
            bool(row["reused_existing_image_asset"]) for row in rows
        ),
        "extractor_key_figure_count": sum(
            str(row["extractor_key_figure_flag"]).casefold() == "true" for row in rows
        ),
        "audit_status_counts": dict(sorted(audit_counts.items())),
        "terminal_class_counts": dict(sorted(target_counts.items())),
        "machine_representation_required_count": sum(
            bool(row["machine_representation_required"]) for row in rows
        ),
        "machine_representation_closed_count": sum(
            bool(row["structured_dataset_id"])
            and row["vision_disabled_replay_status"] == "PASS"
            for row in rows
        ),
        "unresolved_figure_count": sum(row["audit_status"] == "NEEDS_REVIEW" for row in rows),
        "missing_image_count": sum(not bool(row["image_exists"]) for row in rows),
        "promoted_terminal_source_count": len(terminal_overlays),
        "first_stage_pass": not any(row["audit_status"] == "NEEDS_REVIEW" for row in rows),
        "note": "Image reuse is audit evidence only; runtime vision remains forbidden.",
    }
    return rows, summary


FIELDS = [
    "figure_id",
    "doc_id",
    "source_id",
    "source_pdf_sha256",
    "standard_id",
    "standard_year",
    "source_kind",
    "families_json",
    "authority_status",
    "source_boundary",
    "page_1based",
    "figure_order",
    "caption",
    "bbox_pt",
    "method",
    "extractor_key_figure_flag",
    "extractor_asset_qa_status",
    "image_path",
    "image_exists",
    "image_width_px",
    "image_height_px",
    "image_sha256",
    "reused_existing_image_asset",
    "proposed_dataization_target",
    "terminal_class",
    "audit_status",
    "dataization_state",
    "machine_representation_required",
    "structured_dataset_id",
    "structured_record_count",
    "axis_or_object_qa_status",
    "error_bound_or_relation_qa",
    "vision_disabled_replay_status",
    "reviewer_note",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-inventory", type=Path, required=True)
    parser.add_argument("--documents-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--terminal-audit-registry", type=Path)
    args = parser.parse_args()
    rows, summary = build_manifest(
        args.source_inventory.resolve(),
        args.documents_root.resolve(),
        args.terminal_audit_registry.resolve() if args.terminal_audit_registry else None,
    )
    write_csv(args.out_dir / "figure_audit_manifest.csv", rows, FIELDS)
    (args.out_dir / "figure_audit_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
