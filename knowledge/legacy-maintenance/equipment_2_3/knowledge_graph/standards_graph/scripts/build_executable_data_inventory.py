#!/usr/bin/env python3
"""Build a source-first inventory for the executable equipment-data layer.

This script does not promote OCR or extracted values.  It inventories every
provided source, deduplicates by SHA-256, joins existing extraction packages,
and makes the remaining digitization debt explicit.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


SUPPORTED_SUFFIXES = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv"}


def sha256_path(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(chunk_size):
            digest.update(block)
    return digest.hexdigest().upper()


def norm_token(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("_", " ")).strip()


def parse_standard_identity(filename: str) -> tuple[str, str, str]:
    stem = Path(filename).stem
    normalized = norm_token(stem)
    patterns = [
        (r"(?i)\bGB\s*[/ ]?\s*T\s*([0-9]+(?:\.[0-9]+)?)\s*[- ]\s*(20\d{2}|19\d{2})", "GB/T"),
        (r"(?i)\bHG\s*[/ ]?\s*T\s*([0-9]+(?:\.[0-9]+)?)\s*[- ]\s*(20\d{2}|19\d{2})", "HG/T"),
        (r"(?i)\bNB\s*[/ ]?\s*T\s*([0-9]+(?:\.[0-9]+)?)\s*[- ]\s*(20\d{2}|19\d{2})", "NB/T"),
        (r"(?i)\bJB\s*[/ ]?\s*T\s*([0-9]+(?:\.[0-9]+)?)\s*[- ]\s*(20\d{2}|19\d{2})", "JB/T"),
        (r"(?i)\bSH\s*[/ ]?\s*T\s*([0-9]+(?:\.[0-9]+)?)\s*[- ]\s*(20\d{2}|19\d{2})", "SH/T"),
        (r"(?i)\bGB\s*([0-9]+(?:\.[0-9]+)?)\s*[- ]\s*(20\d{2}|19\d{2})", "GB"),
        (r"(?i)\bSH\s*([0-9]+(?:\.[0-9]+)?)\s*[- ]\s*(20\d{2}|19\d{2})", "SH"),
        (r"(?i)\bHG\s*([0-9]+(?:\.[0-9]+)?)\s*[- ]\s*(20\d{2}|19\d{2})", "HG"),
        (r"(?i)\bTSG\s*([A-Z0-9. ]+)\s*[- ]\s*(20\d{2}|19\d{2})", "TSG"),
    ]
    for pattern, prefix in patterns:
        match = re.search(pattern, normalized)
        if match:
            number = re.sub(r"\s+", "", match.group(1))
            year = match.group(2)
            return f"{prefix} {number}-{year}", year, stem
    # Combined standard volumes are kept identifiable but are not parsed as a
    # single standard number.
    if re.search(r"(?i)HG\s*[/ ]?\s*T\s*20592.*20635.*2009", normalized):
        return "HG/T 20592~20635-2009", "2009", stem
    return "", "", stem


def source_kind(path: Path) -> str:
    name = path.name.casefold()
    if any(token in name for token in ("教材", "handbook", "手册", "常用标准汇编")):
        return "handbook_or_compilation"
    if any(token in name for token in ("课程设计", "毕业设计", "案例", "case")):
        return "case_or_course_design"
    standard_id, _, _ = parse_standard_identity(path.name)
    if standard_id:
        return "standard"
    return "reference_document"


def family_from_path(relative: Path) -> str:
    text = relative.as_posix()
    if "管道" in text:
        return "piping"
    if "换热" in text:
        return "exchanger"
    if "反应器" in text or "搅拌" in text:
        return "reactor_or_agitator"
    if "塔" in text:
        return "tower"
    if "容器" in text or "储罐" in text or "封头" in text:
        return "vessel_or_storage"
    return "cross_family_or_unassigned"


def file_status_hint(path: Path) -> str:
    name = path.name.casefold()
    if "废止" in name or "作废" in name:
        return "FILE_MARKED_OBSOLETE_FORBIDDEN"
    return "CURRENTNESS_REQUIRES_AUTHORITY_CHECK"


def load_existing_registry(registry: Path, source_root: Path) -> dict[str, dict]:
    by_hash: dict[str, dict] = {}
    if not registry.is_file():
        return by_hash
    with registry.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            candidate = source_root / row.get("relative_path", "")
            if not candidate.is_file():
                continue
            by_hash.setdefault(sha256_path(candidate), row)
    return by_hash


def load_extraction_packages(documents_root: Path) -> dict[str, dict]:
    by_hash: dict[str, dict] = {}
    if not documents_root.is_dir():
        return by_hash
    for status_path in documents_root.glob("*/status.json"):
        try:
            status = json.loads(status_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        source_hash = str(status.get("source_pdf_sha256") or "").upper()
        if not source_hash:
            continue
        table_path = status_path.parent / "tables.csv"
        numeric_reuse_count = 0
        if table_path.is_file():
            with table_path.open("r", encoding="utf-8-sig", newline="") as handle:
                for row in csv.DictReader(handle):
                    if str(row.get("numeric_reuse_allowed", "")).casefold() == "true":
                        numeric_reuse_count += 1
        by_hash[source_hash] = {
            **status,
            "package_path": str(status_path.parent),
            "numeric_reuse_table_count": numeric_reuse_count,
        }
    return by_hash


def load_provenance(manifest_root: Path) -> dict[str, list[dict]]:
    by_hash: dict[str, list[dict]] = defaultdict(list)
    if not manifest_root.is_dir():
        return by_hash
    for path in manifest_root.rglob("source_snapshot_manifest.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        metadata = payload.get("metadata") or {}
        for row in payload.get("files") or []:
            source_hash = str(row.get("sha256") or "").upper()
            if source_hash:
                by_hash[source_hash].append(
                    {
                        "manifest_path": str(path),
                        "zip_path": metadata.get("zip_path", ""),
                        "zip_sha256": metadata.get("zip_sha256", ""),
                        "entry_path": row.get("entry_path", ""),
                    }
                )
    return by_hash


def load_identity_overrides(path: Path | None) -> dict[str, dict]:
    """Load cover/cell-audited identity corrections keyed by source hash.

    A filename is routing evidence only.  An override is accepted only when it
    is hash-bound and explicitly marked VERIFIED; this prevents a correction
    for one physical file from leaking into a different revision.
    """
    if path is None or not path.is_file():
        return {}
    by_hash: dict[str, dict] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            source_hash = str(row.get("source_sha256") or "").strip().upper()
            qa_status = str(row.get("qa_status") or "").strip().upper()
            standard_id = str(row.get("verified_standard_id") or "").strip()
            if source_hash and qa_status == "VERIFIED" and standard_id:
                by_hash[source_hash] = row
    return by_hash


def load_source_state_overrides(path: Path | None) -> dict[str, dict]:
    """Load hash-bound terminal source states such as a verified zero-page PDF."""
    if path is None or not path.is_file():
        return {}
    allowed = {"SOURCE_UNREADABLE_BLOCKED", "NOT_APPLICABLE"}
    by_hash: dict[str, dict] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            source_hash = str(row.get("source_sha256") or "").strip().upper()
            qa_status = str(row.get("qa_status") or "").strip().upper()
            terminal_class = str(row.get("terminal_class") or "").strip().upper()
            if source_hash and qa_status == "VERIFIED" and terminal_class in allowed:
                by_hash[source_hash] = row
    return by_hash


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def registry_doc_id(row: dict) -> str:
    standard_id = str(row.get("standard_id") or "").casefold()
    if standard_id:
        token = re.sub(r"[^a-z0-9]+", "_", standard_id).strip("_")
        return f"std_{token}"
    stem = Path(str(row.get("canonical_relative_path") or "source")).stem
    ascii_slug = re.sub(r"[^a-z0-9]+", "_", stem.casefold()).strip("_")
    if not ascii_slug:
        ascii_slug = "reference"
    return f"ref_{ascii_slug[:48]}_{str(row['sha256'])[:8].casefold()}"


def read_registry_rows(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def registry_candidates(rows: list[dict], existing_ids: set[str] | None = None) -> list[dict]:
    candidates: list[dict] = []
    used_ids: set[str] = set(existing_ids or set())
    for row in rows:
        if row.get("existing_doc_id") or row.get("extension") != ".pdf":
            continue
        doc_id = registry_doc_id(row)
        if doc_id in used_ids:
            doc_id = f"{doc_id}_{str(row['sha256'])[:8].casefold()}"
        used_ids.add(doc_id)
        families = json.loads(row.get("families_json") or "[]")
        family = families[0] if len(families) == 1 else "cross_family"
        obsolete = row.get("authority_status") == "OBSOLETE_FORBIDDEN"
        kind = str(row.get("source_kind") or "reference_document")
        candidates.append(
            {
                "doc_id": doc_id,
                "relative_path": row["canonical_relative_path"],
                "family": family,
                "source_kind": "obsolete_standard" if obsolete and kind == "standard" else kind,
                "evidence_default": "S0" if obsolete else ("S1-S2" if kind == "standard" else "S0-S1"),
                "duplicate_of": "",
                "language": "zh",
                "priority": "low" if obsolete else ("high" if kind == "standard" else "medium"),
                "source_sha256": row["sha256"],
                "registration_state": "CANDIDATE_HASH_VERIFIED",
            }
        )
    return candidates


def build_inventory(
    source_root: Path,
    registry: Path,
    documents_root: Path,
    provenance_root: Path,
    identity_overrides_path: Path | None = None,
    source_state_overrides_path: Path | None = None,
) -> tuple[list[dict], dict]:
    existing = load_existing_registry(registry, source_root)
    packages = load_extraction_packages(documents_root)
    provenance = load_provenance(provenance_root)
    identity_overrides = load_identity_overrides(identity_overrides_path)
    source_state_overrides = load_source_state_overrides(source_state_overrides_path)
    physical: list[dict] = []
    for path in sorted(source_root.rglob("*"), key=lambda item: str(item).casefold()):
        if not path.is_file() or path.suffix.casefold() not in SUPPORTED_SUFFIXES:
            continue
        relative = path.relative_to(source_root)
        source_hash = sha256_path(path)
        standard_id, standard_year, title_hint = parse_standard_identity(path.name)
        filename_standard_id = standard_id
        identity_override = identity_overrides.get(source_hash) or {}
        if identity_override:
            standard_id = str(identity_override["verified_standard_id"]).strip()
            standard_year = str(identity_override.get("verified_standard_year") or "").strip()
        physical.append(
            {
                "path": path,
                "relative_path": relative.as_posix(),
                "sha256": source_hash,
                "size_bytes": path.stat().st_size,
                "extension": path.suffix.casefold(),
                "standard_id": standard_id,
                "filename_standard_id": filename_standard_id,
                "standard_year": standard_year,
                "title_hint": title_hint,
                "source_kind": source_kind(path),
                "family": family_from_path(relative),
                "file_status_hint": file_status_hint(path),
                "identity_qa_status": identity_override.get("qa_status", "FILENAME_ONLY"),
                "identity_evidence": identity_override.get("evidence", ""),
            }
        )

    groups: dict[str, list[dict]] = defaultdict(list)
    for row in physical:
        groups[row["sha256"]].append(row)

    rows: list[dict] = []
    for source_hash, copies in sorted(groups.items()):
        # Prefer a registered path, then the shortest stable relative path.
        registered = existing.get(source_hash) or {}
        preferred_relative = registered.get("relative_path")
        canonical = next(
            (row for row in copies if row["relative_path"] == preferred_relative),
            sorted(copies, key=lambda row: (len(row["relative_path"]), row["relative_path"].casefold()))[0],
        )
        package = packages.get(source_hash) or {}
        origins = provenance.get(source_hash) or []
        families = sorted({row["family"] for row in copies})
        file_statuses = sorted({row["file_status_hint"] for row in copies})
        source_state_override = source_state_overrides.get(source_hash) or {}
        if "FILE_MARKED_OBSOLETE_FORBIDDEN" in file_statuses:
            digitization_state = "OBSOLETE_FORBIDDEN"
            source_terminal_class = "OBSOLETE_FORBIDDEN"
            source_terminal_qa_status = "FILE_MARKED_OBSOLETE"
            source_terminal_evidence = "filename explicitly marks the file obsolete"
        elif source_state_override:
            digitization_state = source_state_override["terminal_class"]
            source_terminal_class = source_state_override["terminal_class"]
            source_terminal_qa_status = source_state_override["qa_status"]
            source_terminal_evidence = source_state_override.get("evidence", "")
        elif package and int(package.get("numeric_reuse_table_count") or 0) > 0:
            # A source-layer flag is extraction metadata only. It is not a
            # cell-audited executable-data approval.
            digitization_state = "RAW_REUSE_FLAG_PENDING_CELL_AUDIT"
            source_terminal_class = ""
            source_terminal_qa_status = ""
            source_terminal_evidence = ""
        elif package:
            digitization_state = "EXTRACTED_NOT_EXECUTABLE"
            source_terminal_class = ""
            source_terminal_qa_status = ""
            source_terminal_evidence = ""
        elif canonical["extension"] == ".pdf":
            digitization_state = "NOT_EXTRACTED"
            source_terminal_class = ""
            source_terminal_qa_status = ""
            source_terminal_evidence = ""
        else:
            digitization_state = "NON_PDF_REQUIRES_STRUCTURED_EXTRACTION"
            source_terminal_class = ""
            source_terminal_qa_status = ""
            source_terminal_evidence = ""
        rows.append(
            {
                "source_id": registered.get("doc_id") or f"src_{source_hash[:12].lower()}",
                "sha256": source_hash,
                "canonical_relative_path": canonical["relative_path"],
                "all_relative_paths_json": json.dumps(
                    [row["relative_path"] for row in copies], ensure_ascii=False
                ),
                "duplicate_copy_count": len(copies),
                "size_bytes": canonical["size_bytes"],
                "extension": canonical["extension"],
                "standard_id": canonical["standard_id"],
                "filename_standard_id": canonical["filename_standard_id"],
                "standard_year": canonical["standard_year"],
                "title_hint": canonical["title_hint"],
                "source_kind": registered.get("source_kind") or canonical["source_kind"],
                "families_json": json.dumps(families, ensure_ascii=False),
                "file_status_hint": ";".join(file_statuses),
                "identity_qa_status": canonical["identity_qa_status"],
                "identity_evidence": canonical["identity_evidence"],
                "authority_status": "OBSOLETE_FORBIDDEN"
                if "FILE_MARKED_OBSOLETE_FORBIDDEN" in file_statuses
                else "UNVERIFIED",
                "existing_doc_id": registered.get("doc_id", ""),
                "extraction_status": package.get("status", "NOT_EXTRACTED"),
                "extracted_page_count": package.get("page_count", 0),
                "extracted_table_count": package.get("table_count", 0),
                "manual_review_page_count": len(package.get("manual_review_pages") or []),
                "numeric_reuse_table_count": package.get("numeric_reuse_table_count", 0),
                "verified_executable_table_count": 0,
                "package_path": package.get("package_path", ""),
                "provenance_json": json.dumps(origins, ensure_ascii=False),
                "digitization_state": digitization_state,
                "source_terminal_class": source_terminal_class,
                "source_terminal_qa_status": source_terminal_qa_status,
                "source_terminal_evidence": source_terminal_evidence,
            }
        )

    counts = Counter(row["digitization_state"] for row in rows)
    summary = {
        "schema": "equipment-executable-source-inventory-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_root": str(source_root),
        "physical_file_count": len(physical),
        "unique_source_count": len(rows),
        "duplicate_physical_file_count": len(physical) - len(rows),
        "standard_source_count": sum(row["source_kind"] == "standard" for row in rows),
        "authority_unverified_count": sum(row["authority_status"] == "UNVERIFIED" for row in rows),
        "digitization_state_counts": dict(sorted(counts.items())),
        "first_stage_pass": False,
        "first_stage_blockers": [
            "all non-obsolete standards require current/withdrawn authority verification",
            "all NOT_EXTRACTED and NON_PDF_REQUIRES_STRUCTURED_EXTRACTION sources must be processed",
            "all key tables must receive a terminal reuse class",
            "all DIRECT_REUSE_VERIFIED tables must have zero unresolved key cells",
            "CSV/SQLite parity and source-folder-offline query tests are not yet complete",
        ],
    }
    return rows, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--documents-root", type=Path, required=True)
    parser.add_argument("--provenance-root", type=Path, required=True)
    parser.add_argument("--identity-overrides", type=Path)
    parser.add_argument("--source-state-overrides", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    rows, summary = build_inventory(
        args.source_root.resolve(),
        args.registry.resolve(),
        args.documents_root.resolve(),
        args.provenance_root.resolve(),
        args.identity_overrides.resolve() if args.identity_overrides else None,
        args.source_state_overrides.resolve() if args.source_state_overrides else None,
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    fields = [
        "source_id",
        "sha256",
        "canonical_relative_path",
        "all_relative_paths_json",
        "duplicate_copy_count",
        "size_bytes",
        "extension",
        "standard_id",
        "filename_standard_id",
        "standard_year",
        "title_hint",
        "source_kind",
        "families_json",
        "file_status_hint",
        "identity_qa_status",
        "identity_evidence",
        "authority_status",
        "existing_doc_id",
        "extraction_status",
        "extracted_page_count",
        "extracted_table_count",
        "manual_review_page_count",
        "numeric_reuse_table_count",
        "verified_executable_table_count",
        "package_path",
        "provenance_json",
        "digitization_state",
        "source_terminal_class",
        "source_terminal_qa_status",
        "source_terminal_evidence",
    ]
    write_csv(args.out_dir / "source_inventory.csv", rows, fields)
    existing_registry_rows = read_registry_rows(args.registry.resolve())
    candidates = registry_candidates(
        rows, {row.get("doc_id", "") for row in existing_registry_rows}
    )
    write_csv(
        args.out_dir / "document_registry_candidates.csv",
        candidates,
        [
            "doc_id",
            "relative_path",
            "family",
            "source_kind",
            "evidence_default",
            "duplicate_of",
            "language",
            "priority",
            "source_sha256",
            "registration_state",
        ],
    )
    registry_fields = [
        "doc_id",
        "relative_path",
        "family",
        "source_kind",
        "evidence_default",
        "duplicate_of",
        "language",
        "priority",
    ]
    write_csv(
        args.out_dir / "document_registry_merged.csv",
        existing_registry_rows + candidates,
        registry_fields,
    )
    (args.out_dir / "source_inventory.json").write_text(
        json.dumps({"summary": summary, "sources": rows}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.out_dir / "inventory_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
