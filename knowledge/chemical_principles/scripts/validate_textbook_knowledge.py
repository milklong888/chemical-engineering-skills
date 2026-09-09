# -*- coding: utf-8 -*-
"""Deterministically validate the local Chemical Principles textbook store.

The default run writes ``extraction/validation_report.json`` and returns zero
only when every mandatory gate passes.  Validation is read-only except for the
final atomic report write.  Use ``--stdout-only`` for a no-write audit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = ROOT.parent
DEFAULT_REPORT = ROOT / "extraction" / "validation_report.json"

EXPECTED_SOURCE_COUNT = 2
EXPECTED_TOTAL_PAGES = 687
REGISTRY_SCHEMA = "chemical-principles-source-registry-v1"
PAGE_SCHEMA = "chemical-principles-page-ocr-v1"
MANIFEST_REPORT_SCHEMA = "chemical-principles-ocr-build-report-v1"
INDEX_SUMMARY_SCHEMA = "chemical-principles-evidence-index-v1"
CHAPTER_MAP_SCHEMA = "chemical-principles-chapter-map-v1"
L0_LAYER = "L0_source_detail"
ALLOWED_PAGE_STATUSES = {
    "ocr_candidate",
    "ocr_low_confidence",
    "blank_or_nontext_page",
}
MAX_REPORTED_ISSUES = 200


class Issues:
    """Accumulate deterministic errors without making reports unbounded."""

    def __init__(self) -> None:
        self.count = 0
        self.items: list[str] = []

    def add(self, message: str) -> None:
        self.count += 1
        if len(self.items) < MAX_REPORTED_ISSUES:
            self.items.append(str(message))

    def extend(self, messages: list[str]) -> None:
        for message in messages:
            self.add(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_registry(issues: Issues) -> dict[str, Any]:
    path = ROOT / "source_registry.json"
    if not path.is_file():
        issues.add(f"missing source registry: {path}")
        return {}
    try:
        registry = read_json(path)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        issues.add(f"invalid source registry: {type(exc).__name__}: {exc}")
        return {}
    if registry.get("schema") != REGISTRY_SCHEMA:
        issues.add(
            f"source registry schema mismatch: expected={REGISTRY_SCHEMA} "
            f"actual={registry.get('schema')!r}"
        )
    sources = registry.get("sources")
    if not isinstance(sources, list):
        issues.add("source registry 'sources' must be a list")
        registry["sources"] = []
    return registry


def normalized_sources(
    registry: dict[str, Any], issues: Issues
) -> list[dict[str, Any]]:
    sources = registry.get("sources", [])
    if len(sources) != EXPECTED_SOURCE_COUNT:
        issues.add(
            f"source count mismatch: expected={EXPECTED_SOURCE_COUNT} "
            f"actual={len(sources)}"
        )
    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_volumes: set[str] = set()
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            issues.add(f"source[{index}] is not an object")
            continue
        source_id = str(source.get("source_id", "")).strip()
        volume = str(source.get("volume", "")).strip()
        if not source_id:
            issues.add(f"source[{index}] has no source_id")
        elif source_id in seen_ids:
            issues.add(f"duplicate source_id: {source_id}")
        seen_ids.add(source_id)
        if volume not in {"upper", "lower"}:
            issues.add(f"{source_id or index}: invalid volume {volume!r}")
        elif volume in seen_volumes:
            issues.add(f"duplicate volume: {volume}")
        seen_volumes.add(volume)
        try:
            expected_pages = int(source.get("expected_pages"))
        except (TypeError, ValueError):
            issues.add(f"{source_id or index}: expected_pages is not an integer")
            continue
        if expected_pages <= 0:
            issues.add(f"{source_id or index}: expected_pages must be positive")
        expected_hash = str(source.get("sha256", "")).upper()
        if not re.fullmatch(r"[0-9A-F]{64}", expected_hash):
            issues.add(f"{source_id or index}: invalid SHA256 in registry")
        source_path = str(source.get("path", ""))
        if not source_path:
            issues.add(f"{source_id or index}: source path is empty")
        normalized.append(
            {
                **source,
                "source_id": source_id,
                "volume": volume,
                "expected_pages": expected_pages,
                "sha256": expected_hash,
                "path": source_path,
            }
        )
    total = sum(int(source["expected_pages"]) for source in normalized)
    if total != EXPECTED_TOTAL_PAGES:
        issues.add(
            f"registered page total mismatch: expected={EXPECTED_TOTAL_PAGES} "
            f"actual={total}"
        )
    if {source["volume"] for source in normalized} != {"upper", "lower"}:
        issues.add("registry must contain exactly one upper and one lower volume")
    return sorted(normalized, key=lambda item: item["volume"])


def make_result(
    check_id: str, issues: Issues, details: dict[str, Any]
) -> dict[str, Any]:
    return {
        "id": check_id,
        "status": "PASS" if issues.count == 0 else "FAIL",
        "error_count": issues.count,
        "errors": issues.items,
        "errors_truncated": issues.count > len(issues.items),
        "details": details,
    }


def run_check(
    check_id: str, function: Callable[[], tuple[Issues, dict[str, Any]]]
) -> dict[str, Any]:
    try:
        issues, details = function()
        return make_result(check_id, issues, details)
    except Exception as exc:  # Report unexpected validator defects as a failed gate.
        issues = Issues()
        issues.add(f"internal validator error: {type(exc).__name__}: {exc}")
        return make_result(check_id, issues, {})


def check_sources_and_pdfs() -> tuple[Issues, dict[str, Any]]:
    issues = Issues()
    registry = load_registry(issues)
    sources = normalized_sources(registry, issues)
    rows: list[dict[str, Any]] = []
    try:
        import fitz  # type: ignore
    except ImportError as exc:
        fitz = None
        issues.add(f"PyMuPDF is required for direct PDF page counts: {exc}")

    for source in sources:
        source_id = source["source_id"]
        path = Path(source["path"])
        row: dict[str, Any] = {
            "source_id": source_id,
            "volume": source["volume"],
            "path": str(path),
            "expected_sha256": source["sha256"],
            "expected_pages": source["expected_pages"],
            "exists": path.is_file(),
        }
        if not path.is_file():
            issues.add(f"{source_id}: source PDF does not exist: {path}")
            rows.append(row)
            continue
        try:
            actual_hash = sha256_file(path)
            row["actual_sha256"] = actual_hash
            if actual_hash != source["sha256"]:
                issues.add(
                    f"{source_id}: source SHA256 mismatch: "
                    f"expected={source['sha256']} actual={actual_hash}"
                )
        except OSError as exc:
            issues.add(f"{source_id}: cannot hash source PDF: {exc}")
        if fitz is not None:
            try:
                with fitz.open(path) as document:
                    actual_pages = int(document.page_count)
                row["actual_pages"] = actual_pages
                if actual_pages != source["expected_pages"]:
                    issues.add(
                        f"{source_id}: PDF page count mismatch: "
                        f"expected={source['expected_pages']} actual={actual_pages}"
                    )
            except Exception as exc:
                issues.add(
                    f"{source_id}: cannot read direct PDF page count: "
                    f"{type(exc).__name__}: {exc}"
                )
        rows.append(row)
    return issues, {
        "registry_schema": registry.get("schema"),
        "source_count": len(sources),
        "registered_pages": sum(
            int(source["expected_pages"]) for source in sources
        ),
        "sources": rows,
    }


def expected_page_records(
    sources: list[dict[str, Any]]
) -> dict[tuple[str, int], dict[str, Any]]:
    expected: dict[tuple[str, int], dict[str, Any]] = {}
    for source in sources:
        for page in range(1, int(source["expected_pages"]) + 1):
            stem = f"page_{page:04d}"
            expected[(source["source_id"], page)] = {
                "source": source,
                "page": page,
                "text_path": ROOT / "source_pages" / source["volume"] / f"{stem}.txt",
                "json_path": ROOT / "source_pages" / source["volume"] / f"{stem}.json",
                "text_relative": f"source_pages/{source['volume']}/{stem}.txt",
                "json_relative": f"source_pages/{source['volume']}/{stem}.json",
            }
    return expected


def parse_text_header(text: str) -> tuple[dict[str, str], bool]:
    header: dict[str, str] = {}
    terminated = False
    for line in text.splitlines():
        if not line.strip():
            terminated = True
            break
        if ":" not in line:
            break
        key, value = line.split(":", 1)
        key = key.strip()
        header[key] = value.strip()
        # The builder places the OCR body immediately after this final header
        # field; a second blank separator line is not required.
        if key == "numeric_formula_notice":
            terminated = True
            break
    return header, terminated


def check_page_packages() -> tuple[Issues, dict[str, Any]]:
    issues = Issues()
    registry = load_registry(issues)
    sources = normalized_sources(registry, issues)
    expected = expected_page_records(sources)
    expected_txt = {item["text_path"].resolve() for item in expected.values()}
    expected_json = {item["json_path"].resolve() for item in expected.values()}
    page_root = ROOT / "source_pages"
    actual_txt = (
        {path.resolve() for path in page_root.rglob("*.txt")}
        if page_root.is_dir()
        else set()
    )
    actual_json = (
        {path.resolve() for path in page_root.rglob("*.json")}
        if page_root.is_dir()
        else set()
    )
    for missing in sorted(expected_txt - actual_txt, key=str):
        issues.add(f"missing page text: {missing}")
    for missing in sorted(expected_json - actual_json, key=str):
        issues.add(f"missing page metadata: {missing}")
    for extra in sorted(actual_txt - expected_txt, key=str):
        issues.add(f"unexpected page text: {extra}")
    for extra in sorted(actual_json - expected_json, key=str):
        issues.add(f"unexpected page metadata: {extra}")

    status_counts: Counter[str] = Counter()
    signature_counts: Counter[str] = Counter()
    checked = 0
    for key in sorted(expected):
        item = expected[key]
        source = item["source"]
        page = item["page"]
        text_path: Path = item["text_path"]
        meta_path: Path = item["json_path"]
        if not text_path.is_file() or not meta_path.is_file():
            continue
        try:
            raw_text = text_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            issues.add(f"{item['text_relative']}: unreadable UTF-8 text: {exc}")
            continue
        try:
            metadata = read_json(meta_path)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            issues.add(f"{item['json_relative']}: invalid UTF-8 JSON: {exc}")
            continue
        checked += 1
        expected_values = {
            "schema": PAGE_SCHEMA,
            "source_id": source["source_id"],
            "volume": source["volume"],
            "pdf_page": page,
            "source_path": source["path"],
            "source_sha256": source["sha256"],
            "text_path": item["text_relative"],
            "knowledge_layer": L0_LAYER,
        }
        for field, expected_value in expected_values.items():
            actual_value = metadata.get(field)
            if actual_value != expected_value:
                issues.add(
                    f"{item['json_relative']}: {field} mismatch: "
                    f"expected={expected_value!r} actual={actual_value!r}"
                )
        actual_text_hash = sha256_file(text_path)
        if metadata.get("text_sha256") != actual_text_hash:
            issues.add(
                f"{item['json_relative']}: text_sha256 mismatch: "
                f"metadata={metadata.get('text_sha256')!r} actual={actual_text_hash}"
            )
        status = str(metadata.get("status", ""))
        status_counts[status] += 1
        if status not in ALLOWED_PAGE_STATUSES:
            issues.add(f"{item['json_relative']}: invalid status {status!r}")
        signature = str(metadata.get("ocr_signature", ""))
        signature_counts[signature] += 1
        if not signature:
            issues.add(f"{item['json_relative']}: missing ocr_signature")

        header, terminated = parse_text_header(raw_text)
        if not terminated:
            issues.add(f"{item['text_relative']}: metadata header is not terminated")
        header_expected = {
            "source_id": source["source_id"],
            "volume": source["volume"],
            "pdf_page": str(page),
            "source_sha256": source["sha256"],
            "evidence_status": status,
            "knowledge_layer": L0_LAYER,
        }
        for field, expected_value in header_expected.items():
            if header.get(field) != expected_value:
                issues.add(
                    f"{item['text_relative']}: header {field} mismatch: "
                    f"expected={expected_value!r} actual={header.get(field)!r}"
                )
        if not header.get("numeric_formula_notice"):
            issues.add(
                f"{item['text_relative']}: missing numeric_formula_notice"
            )
    if checked != EXPECTED_TOTAL_PAGES:
        issues.add(
            f"validated page-pair count mismatch: "
            f"expected={EXPECTED_TOTAL_PAGES} actual={checked}"
        )
    if len(signature_counts) != 1:
        issues.add(
            f"L0 metadata must use one OCR signature; found={dict(signature_counts)}"
        )
    return issues, {
        "expected_page_pairs": EXPECTED_TOTAL_PAGES,
        "validated_page_pairs": checked,
        "txt_files": len(actual_txt),
        "json_files": len(actual_json),
        "status_counts": dict(sorted(status_counts.items())),
        "ocr_signatures": dict(sorted(signature_counts.items())),
        "knowledge_layer": L0_LAYER,
    }


def read_jsonl(path: Path, issues: Issues, label: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        issues.add(f"missing {label}: {path}")
        return rows
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        issues.add(f"unreadable {label}: {exc}")
        return rows
    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            issues.add(f"{label} line {line_number}: blank JSONL record")
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            issues.add(f"{label} line {line_number}: invalid JSON: {exc}")
            continue
        if not isinstance(row, dict):
            issues.add(f"{label} line {line_number}: record is not an object")
            continue
        rows.append(row)
    return rows


def check_manifest_and_build_report() -> tuple[Issues, dict[str, Any]]:
    issues = Issues()
    registry = load_registry(issues)
    sources = normalized_sources(registry, issues)
    expected = expected_page_records(sources)
    expected_keys = set(expected)

    manifest_path = ROOT / "extraction" / "page_manifest.jsonl"
    manifest = read_jsonl(manifest_path, issues, "page manifest")
    manifest_by_key: dict[tuple[str, int], dict[str, Any]] = {}
    for index, row in enumerate(manifest, 1):
        source_id = str(row.get("source_id", ""))
        try:
            page = int(row.get("pdf_page"))
        except (TypeError, ValueError):
            issues.add(f"page manifest record {index}: invalid pdf_page")
            continue
        key = (source_id, page)
        if key in manifest_by_key:
            issues.add(f"duplicate page manifest identity: {key}")
            continue
        manifest_by_key[key] = row
    for missing in sorted(expected_keys - set(manifest_by_key)):
        issues.add(f"page manifest missing identity: {missing}")
    for extra in sorted(set(manifest_by_key) - expected_keys):
        issues.add(f"page manifest has unexpected identity: {extra}")

    status_counts: Counter[str] = Counter()
    action_counts: Counter[str] = Counter()
    manifest_signatures: Counter[str] = Counter()
    for key in sorted(expected_keys & set(manifest_by_key)):
        item = expected[key]
        row = manifest_by_key[key]
        try:
            metadata = read_json(item["json_path"])
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            issues.add(f"{item['json_relative']}: cannot compare to manifest: {exc}")
            continue
        fields = (
            "schema",
            "source_id",
            "volume",
            "pdf_page",
            "source_path",
            "source_sha256",
            "ocr_signature",
            "ocr_language",
            "ocr_config",
            "extraction_method",
            "status",
            "text_sha256",
            "text_path",
            "knowledge_layer",
        )
        for field in fields:
            if row.get(field) != metadata.get(field):
                issues.add(
                    f"manifest {key}: {field} differs from page JSON: "
                    f"manifest={row.get(field)!r} metadata={metadata.get(field)!r}"
                )
        status_counts[str(row.get("status", ""))] += 1
        action_counts[str(row.get("build_action", ""))] += 1
        manifest_signatures[str(row.get("ocr_signature", ""))] += 1

    build_path = ROOT / "extraction" / "build_report.json"
    try:
        build = read_json(build_path)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        issues.add(f"invalid build report: {exc}")
        build = {}
    expected_build_fields = {
        "schema": MANIFEST_REPORT_SCHEMA,
        "registry": "source_registry.json",
        "selected_source": "all",
        "selected_pages": "all",
        "full_run": True,
        "page_records": EXPECTED_TOTAL_PAGES,
        "complete_for_selected_scope": True,
    }
    for field, expected_value in expected_build_fields.items():
        if build.get(field) != expected_value:
            issues.add(
                f"build report {field} mismatch: "
                f"expected={expected_value!r} actual={build.get(field)!r}"
            )
    if build.get("status_counts") != dict(status_counts):
        issues.add(
            f"build report status_counts mismatch: "
            f"expected={dict(status_counts)} actual={build.get('status_counts')!r}"
        )
    if build.get("action_counts") != dict(action_counts):
        issues.add(
            f"build report action_counts mismatch: "
            f"expected={dict(action_counts)} actual={build.get('action_counts')!r}"
        )
    if len(manifest_signatures) != 1:
        issues.add(
            f"manifest must contain one OCR signature; "
            f"found={dict(manifest_signatures)}"
        )
    elif build.get("ocr_signature") not in manifest_signatures:
        issues.add("build report OCR signature differs from page manifest")

    verification = build.get("source_verification", {})
    if not isinstance(verification, dict):
        issues.add("build report source_verification must be an object")
        verification = {}
    for source in sources:
        row = verification.get(source["source_id"])
        if not isinstance(row, dict):
            issues.add(
                f"build report missing source verification: {source['source_id']}"
            )
            continue
        for field, expected_value in {
            "path": source["path"],
            "sha256": source["sha256"],
            "pages": source["expected_pages"],
        }.items():
            if row.get(field) != expected_value:
                issues.add(
                    f"build source {source['source_id']} {field} mismatch: "
                    f"expected={expected_value!r} actual={row.get(field)!r}"
                )

    candidate_counts: dict[str, int] = {}
    for name, report_field in (
        ("heading_candidates.jsonl", "heading_candidates"),
        ("caption_candidates.jsonl", "caption_candidates"),
    ):
        candidate_issues = Issues()
        rows = read_jsonl(
            ROOT / "extraction" / name, candidate_issues, name
        )
        issues.extend(candidate_issues.items)
        if candidate_issues.count > len(candidate_issues.items):
            for _ in range(candidate_issues.count - len(candidate_issues.items)):
                issues.add(f"{name}: additional omitted JSONL error")
        candidate_counts[report_field] = len(rows)
        if build.get(report_field) != len(rows):
            issues.add(
                f"build report {report_field} mismatch: "
                f"expected={len(rows)} actual={build.get(report_field)!r}"
            )
    return issues, {
        "manifest_records": len(manifest),
        "unique_manifest_pages": len(manifest_by_key),
        "status_counts": dict(sorted(status_counts.items())),
        "action_counts": dict(sorted(action_counts.items())),
        **candidate_counts,
        "build_report_schema": build.get("schema"),
    }


def table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {
        str(row[1])
        for row in connection.execute(f'PRAGMA table_info("{table}")').fetchall()
    }


def check_sqlite_index() -> tuple[Issues, dict[str, Any]]:
    issues = Issues()
    registry = load_registry(issues)
    sources = normalized_sources(registry, issues)
    source_by_id = {source["source_id"]: source for source in sources}
    database = ROOT / "indexes" / "chemical_principles_evidence.sqlite"
    summary_path = ROOT / "indexes" / "search_index_summary.json"
    details: dict[str, Any] = {"database": str(database)}
    if not database.is_file():
        issues.add(f"missing SQLite evidence index: {database}")
        return issues, details
    try:
        summary = read_json(summary_path)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        issues.add(f"invalid search index summary: {exc}")
        summary = {}
    if summary.get("schema") != INDEX_SUMMARY_SCHEMA:
        issues.add(
            f"search summary schema mismatch: "
            f"expected={INDEX_SUMMARY_SCHEMA} actual={summary.get('schema')!r}"
        )

    connection: sqlite3.Connection | None = None
    try:
        uri = database.resolve().as_uri() + "?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        connection.execute("PRAGMA query_only=ON")
        integrity = [
            str(row[0])
            for row in connection.execute("PRAGMA integrity_check").fetchall()
        ]
        details["integrity_check"] = integrity
        if integrity != ["ok"]:
            issues.add(f"SQLite integrity_check failed: {integrity}")
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        required_tables = {"documents", "pages", "chunks"}
        missing_tables = sorted(required_tables - tables)
        for table in missing_tables:
            issues.add(f"SQLite missing table: {table}")
        if missing_tables:
            return issues, details

        required_columns = {
            "documents": {
                "source_id",
                "volume",
                "source_pdf_path",
                "source_pdf_sha256",
                "expected_pages",
            },
            "pages": {
                "page_id",
                "source_id",
                "volume",
                "pdf_page",
                "knowledge_layer",
                "source_pdf_sha256",
                "source_text_path",
                "source_metadata_path",
                "text_sha256",
            },
            "chunks": {
                "chunk_id",
                "page_id",
                "source_id",
                "knowledge_layer",
            },
        }
        columns_ok = True
        for table, required in required_columns.items():
            missing = sorted(required - table_columns(connection, table))
            for column in missing:
                issues.add(f"SQLite {table} missing column: {column}")
                columns_ok = False
        if not columns_ok:
            return issues, details

        counts = {
            table: int(
                connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            )
            for table in ("documents", "pages", "chunks")
        }
        details["counts"] = counts
        if counts["documents"] != EXPECTED_SOURCE_COUNT:
            issues.add(
                f"SQLite documents count mismatch: "
                f"expected={EXPECTED_SOURCE_COUNT} actual={counts['documents']}"
            )
        if counts["pages"] != EXPECTED_TOTAL_PAGES:
            issues.add(
                f"SQLite pages count mismatch: "
                f"expected={EXPECTED_TOTAL_PAGES} actual={counts['pages']}"
            )
        if counts["chunks"] <= 0:
            issues.add("SQLite chunks table is empty")

        document_rows = connection.execute(
            "SELECT source_id,volume,source_pdf_path,source_pdf_sha256,"
            "expected_pages FROM documents ORDER BY source_id"
        ).fetchall()
        document_ids: set[str] = set()
        for row in document_rows:
            source_id = str(row[0])
            document_ids.add(source_id)
            source = source_by_id.get(source_id)
            if source is None:
                issues.add(f"SQLite documents has unknown source_id: {source_id}")
                continue
            expected_values = (
                source["volume"],
                source["path"],
                source["sha256"],
                source["expected_pages"],
            )
            if tuple(row[1:]) != expected_values:
                issues.add(
                    f"SQLite document mismatch for {source_id}: "
                    f"expected={expected_values!r} actual={tuple(row[1:])!r}"
                )
        for source_id in sorted(set(source_by_id) - document_ids):
            issues.add(f"SQLite documents missing source_id: {source_id}")

        page_rows = connection.execute(
            "SELECT page_id,source_id,volume,pdf_page,knowledge_layer,"
            "source_pdf_sha256,source_text_path,source_metadata_path,text_sha256 "
            "FROM pages ORDER BY source_id,pdf_page"
        ).fetchall()
        seen_page_keys: set[tuple[str, int]] = set()
        for row in page_rows:
            source_id = str(row[1])
            try:
                page = int(row[3])
            except (TypeError, ValueError):
                issues.add(f"SQLite page has invalid pdf_page: {row!r}")
                continue
            key = (source_id, page)
            if key in seen_page_keys:
                issues.add(f"SQLite duplicate page identity: {key}")
            seen_page_keys.add(key)
            source = source_by_id.get(source_id)
            if source is None:
                issues.add(f"SQLite page has unknown source_id: {source_id}")
                continue
            expected_page_id = f"{source_id}:p{page:04d}"
            expected_text = f"source_pages/{source['volume']}/page_{page:04d}.txt"
            expected_meta = f"source_pages/{source['volume']}/page_{page:04d}.json"
            text_path = ROOT / expected_text
            expected_hash = (
                sha256_file(text_path) if text_path.is_file() else None
            )
            expected_values = (
                expected_page_id,
                source["volume"],
                L0_LAYER,
                source["sha256"],
                expected_text,
                expected_meta,
                expected_hash,
            )
            actual_values = (
                row[0],
                row[2],
                row[4],
                row[5],
                row[6],
                row[7],
                row[8],
            )
            if actual_values != expected_values:
                issues.add(
                    f"SQLite page mismatch for {key}: "
                    f"expected={expected_values!r} actual={actual_values!r}"
                )
        registered_page_keys = {
            (source["source_id"], page)
            for source in sources
            for page in range(1, int(source["expected_pages"]) + 1)
        }
        for missing in sorted(registered_page_keys - seen_page_keys):
            issues.add(f"SQLite pages missing identity: {missing}")
        for extra in sorted(seen_page_keys - registered_page_keys):
            issues.add(f"SQLite pages has unexpected identity: {extra}")

        bad_chunk_layers = int(
            connection.execute(
                "SELECT COUNT(*) FROM chunks "
                "WHERE knowledge_layer IS NULL OR knowledge_layer<>?",
                (L0_LAYER,),
            ).fetchone()[0]
        )
        orphan_chunks = int(
            connection.execute(
                "SELECT COUNT(*) FROM chunks c LEFT JOIN pages p "
                "ON p.page_id=c.page_id WHERE p.page_id IS NULL"
            ).fetchone()[0]
        )
        inconsistent_chunks = int(
            connection.execute(
                "SELECT COUNT(*) FROM chunks c JOIN pages p "
                "ON p.page_id=c.page_id "
                "WHERE c.source_id<>p.source_id"
            ).fetchone()[0]
        )
        details["bad_chunk_layers"] = bad_chunk_layers
        details["orphan_chunks"] = orphan_chunks
        details["inconsistent_chunks"] = inconsistent_chunks
        if bad_chunk_layers:
            issues.add(f"SQLite chunks with non-L0 layer: {bad_chunk_layers}")
        if orphan_chunks:
            issues.add(f"SQLite orphan chunks: {orphan_chunks}")
        if inconsistent_chunks:
            issues.add(
                f"SQLite chunks with source/page inconsistency: "
                f"{inconsistent_chunks}"
            )

        summary_expected = {
            "documents": counts["documents"],
            "expected_pages": EXPECTED_TOTAL_PAGES,
            "indexed_pages": counts["pages"],
            "indexed_chunks": counts["chunks"],
            "knowledge_layer": L0_LAYER,
        }
        for field, expected_value in summary_expected.items():
            if summary.get(field) != expected_value:
                issues.add(
                    f"search summary {field} mismatch: "
                    f"expected={expected_value!r} actual={summary.get(field)!r}"
                )
        database_statuses = {
            str(status): int(count)
            for status, count in connection.execute(
                "SELECT evidence_status,COUNT(*) FROM pages "
                "GROUP BY evidence_status"
            ).fetchall()
        }
        details["status_counts"] = dict(sorted(database_statuses.items()))
        if summary.get("status_counts") != database_statuses:
            issues.add(
                f"search summary status_counts mismatch: "
                f"expected={database_statuses} "
                f"actual={summary.get('status_counts')!r}"
            )
    except sqlite3.Error as exc:
        issues.add(f"SQLite validation error: {exc}")
    finally:
        if connection is not None:
            connection.close()
    return issues, details


def parse_page_range(
    row: dict[str, Any], label: str, issues: Issues
) -> tuple[int, int] | None:
    value = row.get("pdf_pages")
    if (
        not isinstance(value, list)
        or len(value) != 2
        or not all(isinstance(item, int) for item in value)
    ):
        issues.add(f"{label}: pdf_pages must be [integer, integer]")
        return None
    start, end = int(value[0]), int(value[1])
    if start < 1 or end < start:
        issues.add(f"{label}: invalid pdf_pages range {value!r}")
        return None
    return start, end


def check_chapter_coverage() -> tuple[Issues, dict[str, Any]]:
    issues = Issues()
    registry = load_registry(issues)
    sources = normalized_sources(registry, issues)
    try:
        chapter_map = read_json(ROOT / "chapter_map.json")
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        issues.add(f"invalid chapter map: {exc}")
        chapter_map = {}
    if chapter_map.get("schema") != CHAPTER_MAP_SCHEMA:
        issues.add(
            f"chapter map schema mismatch: expected={CHAPTER_MAP_SCHEMA} "
            f"actual={chapter_map.get('schema')!r}"
        )
    chapters = chapter_map.get("chapters", [])
    supplements = chapter_map.get("supplementary_ranges", [])
    frontmatter_present = "frontmatter_ranges" in chapter_map
    frontmatter = chapter_map.get("frontmatter_ranges", [])
    for field, value in (
        ("chapters", chapters),
        ("supplementary_ranges", supplements),
        ("frontmatter_ranges", frontmatter),
    ):
        if not isinstance(value, list):
            issues.add(f"chapter map {field} must be a list")
    if not isinstance(chapters, list):
        chapters = []
    if not isinstance(supplements, list):
        supplements = []
    if not isinstance(frontmatter, list):
        frontmatter = []

    chapter_ids: set[str] = set()
    intervals: dict[str, list[dict[str, Any]]] = {
        source["volume"]: [] for source in sources
    }
    for kind, rows in (
        ("chapter", chapters),
        ("supplement", supplements),
        ("frontmatter", frontmatter),
    ):
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                issues.add(f"{kind}[{index}] is not an object")
                continue
            label = f"{kind}[{index}]"
            volume = str(row.get("volume", ""))
            if volume not in intervals:
                issues.add(f"{label}: unknown volume {volume!r}")
                continue
            parsed = parse_page_range(row, label, issues)
            if parsed is None:
                continue
            start, end = parsed
            intervals[volume].append(
                {
                    "kind": kind,
                    "start": start,
                    "end": end,
                    "label": str(
                        row.get("chapter_id")
                        or row.get("title")
                        or f"{kind}[{index}]"
                    ),
                }
            )
            if kind == "chapter":
                chapter_id = str(row.get("chapter_id", ""))
                if not chapter_id:
                    issues.add(f"{label}: missing chapter_id")
                elif chapter_id in chapter_ids:
                    issues.add(f"duplicate chapter_id: {chapter_id}")
                chapter_ids.add(chapter_id)

    coverage_details: dict[str, Any] = {}
    for source in sources:
        volume = source["volume"]
        total = int(source["expected_pages"])
        rows = sorted(
            intervals.get(volume, []),
            key=lambda row: (row["start"], row["end"], row["kind"], row["label"]),
        )
        owners: dict[int, str] = {}
        for row in rows:
            if row["end"] > total:
                issues.add(
                    f"{volume} {row['label']}: range ends outside 1..{total}"
                )
            for page in range(row["start"], min(row["end"], total) + 1):
                previous = owners.get(page)
                if previous is not None:
                    issues.add(
                        f"{volume} page {page}: overlapping mappings "
                        f"{previous!r} and {row['label']!r}"
                    )
                else:
                    owners[page] = row["label"]

        missing = [page for page in range(1, total + 1) if page not in owners]
        implicit_frontmatter: list[int] = []
        if missing and not frontmatter_present and rows:
            first_start = min(row["start"] for row in rows)
            permitted = list(range(1, first_start))
            if missing[: len(permitted)] == permitted:
                implicit_frontmatter = permitted
                for page in permitted:
                    owners[page] = "implicit_frontmatter"
                missing = [
                    page for page in range(1, total + 1) if page not in owners
                ]
        if missing:
            preview = ",".join(str(page) for page in missing[:30])
            suffix = "..." if len(missing) > 30 else ""
            issues.add(
                f"{volume}: unmapped pages after frontmatter/supplement handling: "
                f"{preview}{suffix}"
            )
        coverage_details[volume] = {
            "expected_pages": total,
            "explicit_intervals": rows,
            "implicit_frontmatter": (
                [implicit_frontmatter[0], implicit_frontmatter[-1]]
                if implicit_frontmatter
                else None
            ),
            "covered_pages": len(owners),
            "unmapped_pages": missing,
        }
    return issues, {
        "schema": chapter_map.get("schema"),
        "chapter_count": len(chapters),
        "supplementary_range_count": len(supplements),
        "frontmatter_mode": (
            "explicit" if frontmatter_present else "leading_prefix_implicit_allowed"
        ),
        "volumes": coverage_details,
    }


FIELD_PATTERN = re.compile(
    r"(?mi)^[ \t]*[-*]?[ \t]*`(?P<name>knowledge_layer|status)`"
    r"[ \t]*:[ \t]*(?P<value>[^\r\n]+)$"
)
FILENAME_LAYER_PATTERN = re.compile(r"^(L[123])(?:[-_])", re.IGNORECASE)
DOWNSTREAM_SECTION_PATTERN = re.compile(
    r"(?ims)^##[ \t]+(?:下行证据|下行源锚|来源锚点|来源与边界|"
    r"L0[ \t]+锚点(?:与禁转)?|downstream evidence|source anchors?)"
    r"[ \t]*\r?\n(?P<body>.*?)(?=^##[ \t]+|\Z)"
)
SOURCE_ID_PATTERN = re.compile(r"\b(CEPR-[A-Z0-9-]+)\b")
PDF_PAGE_PATTERN = re.compile(
    r"PDF[ \t]*p(?:age)?[ \t]*(\d+)"
    r"(?:[ \t]*[–—-][ \t]*(\d+))?",
    re.IGNORECASE,
)
SOURCE_PAGE_PATH_PATTERN = re.compile(
    r"(?P<path>(?:\.\./)+source_pages/"
    r"(?P<volume>upper|lower)/page_(?P<page>\d{4})\.(?:txt|json))",
    re.IGNORECASE,
)


def extract_node_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for match in FIELD_PATTERN.finditer(text):
        fields[match.group("name").lower()] = match.group("value").strip()
    return fields


def check_graph_nodes() -> tuple[Issues, dict[str, Any]]:
    issues = Issues()
    registry = load_registry(issues)
    sources = normalized_sources(registry, issues)
    source_by_id = {source["source_id"]: source for source in sources}
    source_by_volume = {source["volume"]: source for source in sources}
    graph_root = ROOT / "knowledge_graph"
    formal_rows: list[dict[str, Any]] = []
    skipped_candidates: list[str] = []
    for path in sorted(graph_root.rglob("*.md"), key=lambda item: item.as_posix()):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            issues.add(f"{path.relative_to(ROOT).as_posix()}: unreadable node: {exc}")
            continue
        fields = extract_node_fields(text)
        filename_match = FILENAME_LAYER_PATTERN.match(path.stem)
        declared_layer = fields.get("knowledge_layer", "")
        declared_prefix_match = re.match(r"^(L[123])(?:[_-]|$)", declared_layer)
        if filename_match is None and declared_prefix_match is None:
            continue
        status = fields.get("status", "")
        if re.search(
            r"candidate|draft|quarantined|superseded", status, re.IGNORECASE
        ):
            skipped_candidates.append(path.relative_to(ROOT).as_posix())
            continue

        relative = path.relative_to(ROOT).as_posix()
        expected_prefix = (
            filename_match.group(1).upper()
            if filename_match is not None
            else declared_prefix_match.group(1).upper()
        )
        row: dict[str, Any] = {
            "path": relative,
            "expected_layer": expected_prefix,
            "knowledge_layer": declared_layer or None,
            "status": status or None,
        }
        if not declared_layer:
            issues.add(f"{relative}: formal node lacks knowledge_layer")
        elif declared_prefix_match is None:
            issues.add(
                f"{relative}: invalid knowledge_layer {declared_layer!r}"
            )
        elif declared_prefix_match.group(1).upper() != expected_prefix:
            issues.add(
                f"{relative}: filename layer {expected_prefix} conflicts with "
                f"knowledge_layer {declared_layer!r}"
            )

        section_match = DOWNSTREAM_SECTION_PATTERN.search(text)
        if section_match is None:
            issues.add(f"{relative}: formal node lacks a downstream source section")
            row["source_anchor_count"] = 0
            formal_rows.append(row)
            continue
        body = section_match.group("body")
        normalized_body = body.replace("\\", "/")
        # A formal card may declare its source identity in the metadata block
        # and put exact page/file anchors in the downward section.
        all_cepr_ids = set(SOURCE_ID_PATTERN.findall(text))
        cited_ids = sorted(all_cepr_ids & set(source_by_id))
        unknown_ids = sorted(
            source_id
            for source_id in all_cepr_ids - set(source_by_id)
            if source_id.startswith(("CEPR-UPPER-", "CEPR-LOWER-"))
        )
        for source_id in unknown_ids:
            issues.add(f"{relative}: unknown source anchor {source_id}")

        valid_anchor_count = 0
        for line in text.splitlines():
            line_ids = SOURCE_ID_PATTERN.findall(line)
            page_matches = list(PDF_PAGE_PATTERN.finditer(line))
            for source_id in line_ids:
                source = source_by_id.get(source_id)
                if source is None:
                    continue
                for page_match in page_matches:
                    start = int(page_match.group(1))
                    end = int(page_match.group(2) or start)
                    if (
                        start < 1
                        or end < start
                        or end > int(source["expected_pages"])
                    ):
                        issues.add(
                            f"{relative}: source anchor {source_id} has invalid "
                            f"PDF page range {start}-{end}"
                        )
                    else:
                        valid_anchor_count += 1

        source_page_paths: list[str] = []
        for match in SOURCE_PAGE_PATH_PATTERN.finditer(normalized_body):
            reference = match.group("path")
            volume = match.group("volume").lower()
            page = int(match.group("page"))
            source = source_by_volume.get(volume)
            if source is None or not (1 <= page <= int(source["expected_pages"])):
                issues.add(
                    f"{relative}: invalid source page anchor {reference}"
                )
                continue
            resolved = (path.parent / reference).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                issues.add(
                    f"{relative}: source page anchor escapes graph root: {reference}"
                )
                continue
            if not resolved.is_file():
                issues.add(
                    f"{relative}: source page anchor does not exist: {reference}"
                )
                continue
            source_page_paths.append(reference)
            valid_anchor_count += 1
        if not cited_ids:
            issues.add(f"{relative}: downstream section lacks a registered source_id")
        if valid_anchor_count == 0:
            issues.add(
                f"{relative}: downstream section lacks a valid page-level source anchor"
            )
        row["source_ids"] = cited_ids
        row["source_page_paths"] = sorted(source_page_paths)
        row["source_anchor_count"] = valid_anchor_count
        formal_rows.append(row)
    if not formal_rows:
        issues.add("no formal L3/L2/L1 graph nodes were found")
    return issues, {
        "formal_node_count": len(formal_rows),
        "formal_nodes": formal_rows,
        "nonformal_candidate_count": len(skipped_candidates),
        "nonformal_candidates": skipped_candidates,
    }


def load_vector_config(issues: Issues) -> tuple[Path, dict[str, Any]]:
    index_dir = WORKSPACE_ROOT / "knowledge_vector_index"
    config_path = index_dir / "vector_index_config.json"
    if not config_path.is_file():
        return index_dir, {}
    try:
        config = read_json(config_path)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        issues.add(f"invalid global vector config: {exc}")
        return index_dir, {}
    if not isinstance(config, dict):
        issues.add("global vector config must be an object")
        return index_dir, {}
    return index_dir, config


def check_global_records_boundary() -> tuple[Issues, dict[str, Any]]:
    issues = Issues()
    index_dir, config = load_vector_config(issues)
    configured = config.get("records_jsonl", "records.jsonl")
    records_path = Path(str(configured))
    if not records_path.is_absolute():
        records_path = index_dir / records_path
    details: dict[str, Any] = {
        "records_path": str(records_path),
        "present": records_path.is_file(),
    }
    if not records_path.is_file():
        details["records_checked"] = 0
        return issues, details

    forbidden: list[dict[str, Any]] = []
    record_count = 0
    try:
        with records_path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    issues.add(
                        f"global records line {line_number}: blank JSONL record"
                    )
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    issues.add(
                        f"global records line {line_number}: invalid JSON: {exc}"
                    )
                    continue
                if not isinstance(record, dict):
                    issues.add(
                        f"global records line {line_number}: record is not an object"
                    )
                    continue
                record_count += 1
                serialized = re.sub(
                    r"/+",
                    "/",
                    json.dumps(record, ensure_ascii=False).replace("\\", "/"),
                )
                explicit_forbidden = (
                    "chemical_principles_knowledge/source_pages/"
                    in serialized.lower()
                )
                source_group = str(record.get("source_group", "")).lower()
                structured_paths = [
                    re.sub(
                        r"/+",
                        "/",
                        str(record.get(field, "")).replace("\\", "/"),
                    ).lower()
                    for field in ("source_path", "extract_path", "path")
                ]
                structured_forbidden = (
                    source_group == "chemical_principles_knowledge"
                    and any(
                        path == "source_pages"
                        or path.startswith("source_pages/")
                        or "/source_pages/" in path
                        for path in structured_paths
                    )
                )
                if explicit_forbidden or structured_forbidden:
                    vector_id = record.get("vector_id") or record.get("id")
                    forbidden.append(
                        {
                            "line": line_number,
                            "vector_id": vector_id,
                            "source_group": record.get("source_group"),
                            "source_path": record.get("source_path"),
                        }
                    )
                    issues.add(
                        f"global records line {line_number}: raw Chemical "
                        f"Principles source_pages entered the global index"
                    )
    except (OSError, UnicodeError) as exc:
        issues.add(f"cannot read global records: {exc}")
    configured_count = config.get("record_count")
    if configured_count is not None and configured_count != record_count:
        issues.add(
            f"global record count mismatch: config={configured_count!r} "
            f"actual={record_count}"
        )
    details["records_checked"] = record_count
    details["configured_record_count"] = configured_count
    details["forbidden_record_count"] = len(forbidden)
    details["forbidden_records"] = forbidden[:50]
    return issues, details


def check_retrieval_route() -> tuple[Issues, dict[str, Any]]:
    issues = Issues()
    _, config = load_vector_config(issues)
    configured = config.get(
        "retrieval_routes_path",
        str(WORKSPACE_ROOT / "scripts" / "retrieval_routes.json"),
    )
    route_path = Path(str(configured))
    if not route_path.is_absolute():
        route_path = WORKSPACE_ROOT / route_path
    details: dict[str, Any] = {"route_path": str(route_path)}
    if not route_path.is_file():
        issues.add(f"missing retrieval route config: {route_path}")
        return issues, details
    try:
        config_data = read_json(route_path)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        issues.add(f"invalid retrieval route config: {exc}")
        return issues, details
    routes = config_data.get("routes", [])
    if not isinstance(routes, list):
        issues.add("retrieval route config 'routes' must be a list")
        return issues, details
    matches = [
        route
        for route in routes
        if isinstance(route, dict) and route.get("name") == "aspen_error_repair"
    ]
    if len(matches) != 1:
        issues.add(
            f"expected exactly one aspen_error_repair route; found={len(matches)}"
        )
        return issues, details
    triggers = matches[0].get("triggers", [])
    if not isinstance(triggers, list):
        issues.add("aspen_error_repair triggers must be a list")
        return issues, details
    forbidden = [
        trigger
        for trigger in triggers
        if isinstance(trigger, str)
        and "化工原理" in re.sub(r"\s+", "", trigger)
    ]
    for trigger in forbidden:
        issues.add(
            f"aspen_error_repair must not trigger Chemical Principles: {trigger!r}"
        )
    details["aspen_error_repair_trigger_count"] = len(triggers)
    details["forbidden_triggers"] = forbidden
    return issues, details


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    text = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    temporary.write_text(text, encoding="utf-8", newline="\n")
    temporary.replace(path)


def build_report() -> dict[str, Any]:
    checks = [
        run_check("source_registry_and_direct_pdfs", check_sources_and_pdfs),
        run_check("l0_page_packages", check_page_packages),
        run_check(
            "page_manifest_and_build_report",
            check_manifest_and_build_report,
        ),
        run_check("sqlite_evidence_index", check_sqlite_index),
        run_check("chapter_map_coverage", check_chapter_coverage),
        run_check("formal_graph_nodes", check_graph_nodes),
        run_check("global_records_l0_boundary", check_global_records_boundary),
        run_check(
            "aspen_error_repair_route_boundary",
            check_retrieval_route,
        ),
    ]
    failed = [check["id"] for check in checks if check["status"] != "PASS"]
    return {
        "schema": "chemical-principles-validation-report-v1",
        "root": str(ROOT),
        "status": "PASS" if not failed else "FAIL",
        "expectations": {
            "source_count": EXPECTED_SOURCE_COUNT,
            "page_count": EXPECTED_TOTAL_PAGES,
            "page_layer": L0_LAYER,
            "global_raw_page_policy": (
                "chemical_principles_knowledge/source_pages excluded"
            ),
            "route_policy": (
                "aspen_error_repair triggers must not contain 化工原理"
            ),
        },
        "summary": {
            "check_count": len(checks),
            "passed": len(checks) - len(failed),
            "failed": len(failed),
            "failed_checks": failed,
        },
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT,
        help="JSON report path; defaults to extraction/validation_report.json",
    )
    parser.add_argument(
        "--stdout-only",
        action="store_true",
        help="run every check and print JSON without writing a report",
    )
    args = parser.parse_args()

    report = build_report()
    if not args.stdout_only:
        report_path = args.report
        if not report_path.is_absolute():
            report_path = (Path.cwd() / report_path).resolve()
        atomic_write_json(report_path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
