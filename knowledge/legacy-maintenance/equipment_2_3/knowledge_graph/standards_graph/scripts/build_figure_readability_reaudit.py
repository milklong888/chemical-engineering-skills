#!/usr/bin/env python3
"""Replace false unreadable-figure states with an auditable open-work state.

This adapter never digitizes engineering values.  It preserves already
dataized rows, accepts exact-ID/hash readability classifications, and turns a
readable-but-untranscribed figure into SEMANTIC_TRANSCRIPTION_PENDING so the
Phase-1 gate remains failed until a machine representation is actually closed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest().upper()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            text = line.strip()
            if not text:
                continue
            try:
                rows.append(json.loads(text))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSONL") from exc
    return rows


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def keyed(rows: list[dict], field: str, label: str) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for row in rows:
        key = str(row.get(field) or "").strip()
        if not key or key in result:
            raise ValueError(f"{label}: empty or duplicate {field}: {key!r}")
        result[key] = row
    return result


def build(
    source_audit: Path,
    candidate_jsonl: Path,
    structured_candidate_jsonl: Path,
    out_dir: Path,
) -> dict:
    fields, original_rows = read_csv(source_audit)
    original = keyed(original_rows, "figure_id", "source audit")
    candidates = keyed(read_jsonl(candidate_jsonl), "figure_id", "readability candidate")
    structured = keyed(
        read_jsonl(structured_candidate_jsonl),
        "figure_id",
        "structured candidate",
    )
    if set(original) != set(candidates):
        raise ValueError("candidate does not cover the exact source-audit figure-ID set")

    output_rows: list[dict[str, str]] = []
    changed = Counter()
    source_hashes = {str(row.get("source_pdf_sha256") or "").upper() for row in original_rows}
    if len(source_hashes) != 1 or "" in source_hashes:
        raise ValueError("source audit must bind exactly one non-empty source hash")
    source_hash = next(iter(source_hashes))

    for figure_id in original:
        row = dict(original[figure_id])
        candidate = candidates[figure_id]
        if str(candidate.get("source_pdf_sha256") or "").upper() != source_hash:
            raise ValueError(f"{figure_id}: source hash mismatch")
        if str(candidate.get("crop_sha256") or "").upper() != str(row.get("crop_sha256") or "").upper():
            raise ValueError(f"{figure_id}: crop hash mismatch")

        proposed = str(candidate.get("proposed_terminal_class") or "").strip()
        prior = str(row.get("terminal_class") or "").strip()
        if prior == "SOURCE_UNREADABLE_BLOCKED" and proposed == "NOT_APPLICABLE":
            row.update({
                "engineering_target_class": "NOT_APPLICABLE",
                "terminal_class": "NOT_APPLICABLE",
                "public_promotable": "false",
                "needs_review": "false",
                "runtime_requires_image": "false",
                "structured_dataset_id": "",
                "structured_record_count": "0",
                "record_sha256": "",
                "qa_status": "VERIFIED_NOT_APPLICABLE_READABILITY_REAUDIT",
                "visual_review_basis": "exact figure ID, crop SHA-256, and independent readability/duplicate review",
                "terminal_reason": str(candidate.get("reason") or "Readable duplicate/non-engineering crop."),
                "unresolved_required_fields_json": "[]",
                "minimum_next_evidence": "",
                "source_image_runtime_access": "FORBIDDEN",
            })
            changed["NOT_APPLICABLE"] += 1
        elif prior == "SOURCE_UNREADABLE_BLOCKED" and proposed == "METHOD_ONLY":
            pending = structured.get(figure_id)
            if not pending:
                raise ValueError(f"{figure_id}: pending transcription lacks structured-candidate record")
            unresolved = list(pending.get("unresolved_required_fields") or [])
            if not unresolved:
                raise ValueError(f"{figure_id}: pending transcription has no unresolved field list")
            row.update({
                "engineering_target_class": str(candidate.get("engineering_target_class") or row.get("engineering_target_class") or "UNCLASSIFIED"),
                "terminal_class": "SEMANTIC_TRANSCRIPTION_PENDING",
                "public_promotable": "false",
                "needs_review": "true",
                "runtime_requires_image": "false",
                "structured_dataset_id": "",
                "structured_record_count": "0",
                "record_sha256": "",
                "qa_status": "READABILITY_VERIFIED_TRANSCRIPTION_PENDING",
                "visual_review_basis": "exact figure ID and crop SHA-256; independent readability probe; no numeric value promoted",
                "terminal_reason": str(candidate.get("reason") or "Readable source; machine semantics remain open."),
                "unresolved_required_fields_json": json.dumps(unresolved, ensure_ascii=False),
                "minimum_next_evidence": "Controlled object/axis/dimension/condition transcription plus independent replay QA.",
                "source_image_runtime_access": "FORBIDDEN",
            })
            changed["SEMANTIC_TRANSCRIPTION_PENDING"] += 1
        elif prior == "SOURCE_UNREADABLE_BLOCKED":
            raise ValueError(f"{figure_id}: unsupported readability transition {prior}->{proposed}")
        output_rows.append(row)

    if changed["SEMANTIC_TRANSCRIPTION_PENDING"] != len(structured):
        raise ValueError("structured candidate count does not equal the pending-transition count")

    audit_path = out_dir / "figure_terminal_audit.csv"
    write_csv(audit_path, fields, output_rows)
    terminal_counts = Counter(row["terminal_class"] for row in output_rows)
    validation = {
        "schema": "equipment-standard-figure-readability-reaudit-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "validation": "PASS",
        "failure_count": 0,
        "failures": [],
        "vision_capability": False,
        "source_image_runtime_access": "FORBIDDEN",
        "source_figure_count": len(original_rows),
        "terminal_audit_row_count": len(output_rows),
        "exact_figure_id_set_equal": True,
        "source_pdf_sha256": source_hash,
        "needs_review_count": terminal_counts["SEMANTIC_TRANSCRIPTION_PENDING"],
        "source_unreadable_blocked_count": terminal_counts["SOURCE_UNREADABLE_BLOCKED"],
        "terminal_class_counts": dict(sorted(terminal_counts.items())),
        "no_numeric_values_promoted_by_reaudit": True,
        "candidate_jsonl_sha256": sha256_path(candidate_jsonl),
        "structured_candidate_jsonl_sha256": sha256_path(structured_candidate_jsonl),
        "source_audit_sha256": sha256_path(source_audit),
    }
    validation_path = out_dir / "figure_validation.json"
    validation_path.write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    audit_note_path = out_dir / "independent_reaudit_acceptance.md"
    audit_note_path.write_text(
        "# Figure readability re-audit acceptance\n\n"
        f"- Source SHA-256: `{source_hash}`\n"
        f"- Exact figures: {len(output_rows)}\n"
        f"- Readable but still awaiting semantic transcription: {terminal_counts['SEMANTIC_TRANSCRIPTION_PENDING']}\n"
        f"- Newly classified not applicable: {changed['NOT_APPLICABLE']}\n"
        f"- Remaining source-unreadable rows: {terminal_counts['SOURCE_UNREADABLE_BLOCKED']}\n"
        "- No engineering number was promoted. Pending figures remain Phase-1 blockers.\n"
        "- Runtime access to PDF/images remains forbidden.\n",
        encoding="utf-8",
    )
    registry_row = {
        "source_sha256": source_hash,
        "terminal_audit_csv": str(audit_path.resolve()),
        "terminal_audit_sha256": sha256_path(audit_path),
        "validation_path": str(validation_path.resolve()),
        "validation_sha256": sha256_path(validation_path),
        "promotion_audit_path": str(audit_note_path.resolve()),
        "promotion_audit_sha256": sha256_path(audit_note_path),
        "qa_status": "VERIFIED",
        "promotion_state": "APPROVED",
        "approved_utc": datetime.now(timezone.utc).isoformat(),
        "notes": "Readability taxonomy corrected; semantic transcription remains explicitly open.",
    }
    registry_path = out_dir / "registry_row.json"
    registry_path.write_text(
        json.dumps(registry_row, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {**validation, "registry_row": registry_row}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-audit", type=Path, required=True)
    parser.add_argument("--candidate-jsonl", type=Path, required=True)
    parser.add_argument("--structured-candidate-jsonl", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    result = build(
        args.source_audit.resolve(),
        args.candidate_jsonl.resolve(),
        args.structured_candidate_jsonl.resolve(),
        args.out_dir.resolve(),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
