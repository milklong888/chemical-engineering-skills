#!/usr/bin/env python3
"""Validate document packages, assets, provenance, and scripted retrieval."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.is_file():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL {path}:{line_no}: {exc}") from exc
    return rows


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest().upper()


def source_state_overrides(source_layer: Path) -> dict[str, dict[str, str]]:
    path = source_layer / "provenance" / "source_state_overrides.csv"
    if not path.is_file():
        return {}
    return {
        row["source_sha256"].upper(): row
        for row in read_csv(path)
        if row.get("source_sha256")
    }


def compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def validate_package(package: Path, registry_row: dict[str, str], source_pdf: Path) -> tuple[list[str], list[str], dict]:
    errors: list[str] = []
    warnings: list[str] = []
    doc_id = registry_row["doc_id"]
    status_path = package / "status.json"
    if not status_path.is_file():
        return errors, warnings, {"doc_id": doc_id, "state": "MISSING"}
    status = json.loads(status_path.read_text(encoding="utf-8"))
    recovery_state = ""
    recovery_method = ""
    if status.get("status") not in {"PASS", "PASS_WITH_REVIEW"}:
        errors.append(f"{doc_id}: package status is {status.get('status')!r}")
    if not source_pdf.is_file():
        errors.append(f"{doc_id}: source PDF missing: {source_pdf}")
    elif sha256_path(source_pdf) != status.get("source_pdf_sha256"):
        errors.append(f"{doc_id}: source PDF hash does not match package")

    pages = read_jsonl(package / "raw_pages.jsonl")
    chunks = read_jsonl(package / "chunks.jsonl")
    tables = read_jsonl(package / "tables.jsonl")
    figures = read_jsonl(package / "figures.jsonl")
    formulas = read_jsonl(package / "formulas.jsonl")
    page_count = int(status.get("page_count", -1))
    page_numbers = [int(row.get("page_1based", -1)) for row in pages]
    if page_numbers != list(range(1, page_count + 1)):
        errors.append(f"{doc_id}: raw page coverage is not exactly 1..{page_count}")
    block_ids = {
        line.get("block_id")
        for page in pages
        for line in page.get("lines", [])
        if line.get("block_id")
    }
    for chunk in chunks:
        missing_refs = [ref for ref in chunk.get("block_ids", []) if ref not in block_ids]
        if missing_refs:
            errors.append(f"{doc_id}: chunk {chunk.get('chunk_id')} has {len(missing_refs)} missing block refs")
    if len(chunks) != int(status.get("chunk_count", -1)):
        errors.append(f"{doc_id}: chunk count disagrees with status")
    if len(tables) != int(status.get("table_count", -1)):
        errors.append(f"{doc_id}: table count disagrees with status")
    if len(figures) != int(status.get("figure_count", -1)):
        errors.append(f"{doc_id}: figure count disagrees with status")

    for table in tables:
        asset = package / table["csv_path"]
        if not asset.is_file():
            errors.append(f"{doc_id}: missing table CSV {table['csv_path']}")
            continue
        with asset.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle))
        actual_rows = len(rows)
        actual_cols = max((len(row) for row in rows), default=0)
        if actual_rows != int(table.get("row_count", -1)) or actual_cols != int(table.get("column_count", -1)):
            errors.append(f"{doc_id}: table shape mismatch for {table.get('table_id')}")
        if not bool(table.get("geometry_preserved", True)):
            warnings.append(f"{doc_id}: detected grid was not preserved for {table.get('table_id')}")
        audit_rel = table.get("cell_audit_csv_path")
        if audit_rel:
            audit_path = package / audit_rel
            if not audit_path.is_file():
                errors.append(f"{doc_id}: missing cell audit CSV {audit_rel}")
            else:
                audit_rows = read_csv(audit_path)
                if len(audit_rows) != actual_rows * actual_cols:
                    errors.append(f"{doc_id}: cell audit count mismatch for {table.get('table_id')}")
        for continuation in table.get("continuations", []):
            continuation_csv = package / continuation["csv_path"]
            continuation_audit = package / continuation["cell_audit_csv_path"]
            if not continuation_csv.is_file():
                errors.append(f"{doc_id}: missing table continuation CSV {continuation['csv_path']}")
            if not continuation_audit.is_file():
                errors.append(f"{doc_id}: missing table continuation cell audit {continuation['cell_audit_csv_path']}")
    for figure in figures:
        asset = package / figure["image_path"]
        if not asset.is_file() or asset.stat().st_size == 0:
            errors.append(f"{doc_id}: missing or empty figure {figure['image_path']}")
        for continuation in figure.get("continuations", []):
            continuation_asset = package / continuation["image_path"]
            if not continuation_asset.is_file() or continuation_asset.stat().st_size == 0:
                errors.append(f"{doc_id}: missing or empty figure continuation {continuation['image_path']}")
    for formula in formulas:
        asset = package / formula["image_path"]
        if not asset.is_file() or asset.stat().st_size == 0:
            errors.append(f"{doc_id}: missing or empty formula image {formula['image_path']}")

    expected_counts = status.get("structure_expected_counts", {})
    if expected_counts:
        if len(tables) != int(expected_counts.get("tables", len(tables))):
            errors.append(f"{doc_id}: visually confirmed table count mismatch")
        if len(figures) != int(expected_counts.get("figures", len(figures))):
            errors.append(f"{doc_id}: visually confirmed figure count mismatch")
        if len(formulas) != int(expected_counts.get("formulas", len(formulas))):
            errors.append(f"{doc_id}: visually confirmed formula count mismatch")

    review_pages = status.get("manual_review_pages", [])
    if review_pages:
        warnings.append(f"{doc_id}: {len(review_pages)} pages require manual review")
    normalized_state = status.get("status", "PASS")
    if normalized_state == "PASS" and review_pages:
        normalized_state = "PASS_WITH_REVIEW"
        warnings.append(
            f"{doc_id}: package state normalized to PASS_WITH_REVIEW because manual-review pages remain"
        )
    empty_chunks = sum(not compact(chunk.get("text", "")) for chunk in chunks)
    if empty_chunks:
        errors.append(f"{doc_id}: {empty_chunks} empty chunks")

    recovery_dir = package.parents[1] / "recovered" / doc_id
    recovery_quality_path = recovery_dir / "content_stream_gbk_quality.json"
    recovery_pages_path = recovery_dir / "content_stream_gbk_pages.jsonl"
    if recovery_quality_path.is_file() or recovery_pages_path.is_file():
        if not recovery_quality_path.is_file() or not recovery_pages_path.is_file():
            errors.append(f"{doc_id}: incomplete legacy text recovery package")
        else:
            recovery_quality = json.loads(recovery_quality_path.read_text(encoding="utf-8"))
            recovered_pages = read_jsonl(recovery_pages_path)
            recovery_state = recovery_quality.get("status", "")
            recovery_method = "pypdf_content_stream_original_bytes_gb18030"
            if recovery_state != "RECOVERED_WITH_LAYOUT_LIMITS":
                errors.append(f"{doc_id}: unexpected legacy recovery status {recovery_state!r}")
            if recovery_quality.get("source_pdf_sha256") != status.get("source_pdf_sha256"):
                errors.append(f"{doc_id}: legacy recovery source hash mismatch")
            recovered_page_numbers = [int(row.get("page_1based", -1)) for row in recovered_pages]
            if recovered_page_numbers != list(range(1, page_count + 1)):
                errors.append(f"{doc_id}: legacy recovery page coverage is not exactly 1..{page_count}")
            if recovery_quality.get("coordinate_boundary", {}).get("status") != "UNRESOLVED":
                errors.append(f"{doc_id}: legacy recovery must declare unresolved glyph coordinates")
            warnings.append(
                f"{doc_id}: recovered legacy text is page-level only; automatic quotation and numeric reuse are forbidden"
            )
    return errors, warnings, {
        "doc_id": doc_id,
        "state": (recovery_state or normalized_state) if not errors else "FAIL",
        "pages": len(pages),
        "chunks": len(chunks),
        "tables": len(tables),
        "figures": len(figures),
        "formulas": len(formulas),
        "manual_review_pages": len(review_pages),
        "recovery_method": recovery_method,
        "location_status": "page_level_only_no_glyph_bbox" if recovery_state else "block_bbox_available",
    }


def smoke_query(connection: sqlite3.Connection, term: str, doc_id: str) -> bool:
    needle = f"%{compact(term)}%"
    chunk = connection.execute(
        "SELECT 1 FROM chunks WHERE doc_id=? AND replace(replace(text,' ',''),char(10),'') LIKE ? LIMIT 1",
        (doc_id, needle),
    ).fetchone()
    table = connection.execute(
        "SELECT 1 FROM tables_data WHERE doc_id=? AND replace(replace(caption || cell_text,' ',''),char(10),'') LIKE ? LIMIT 1",
        (doc_id, needle),
    ).fetchone()
    return bool(chunk or table)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    graph_root = Path(__file__).resolve().parents[1]
    parser.add_argument("--source-root", type=Path, default=graph_root.parents[2] / "设计标准（反应器、塔、换热器、容器等）")
    parser.add_argument("--registry", type=Path, default=graph_root / "source_layer" / "provenance" / "document_registry.csv")
    parser.add_argument("--source-layer", type=Path, default=graph_root / "source_layer")
    parser.add_argument("--allow-incomplete", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    source_root = args.source_root.resolve()
    source_layer = args.source_layer.resolve()
    registry = read_csv(args.registry.resolve())
    by_id = {row["doc_id"]: row for row in registry}
    errors: list[str] = []
    warnings: list[str] = []
    packages: list[dict] = []
    missing: list[str] = []
    blocked: list[str] = []
    state_overrides = source_state_overrides(source_layer)

    ids = [row["doc_id"] for row in registry]
    paths = [row["relative_path"] for row in registry]
    if len(ids) != len(set(ids)):
        errors.append("registry contains duplicate doc_id")
    if len(paths) != len(set(paths)):
        errors.append("registry contains duplicate relative_path")
    for row in registry:
        duplicate_of = row.get("duplicate_of", "")
        canonical_id = duplicate_of or row["doc_id"]
        package = source_layer / "documents" / canonical_id
        source_pdf = source_root / row["relative_path"]
        if duplicate_of:
            if duplicate_of not in by_id:
                errors.append(f"{row['doc_id']}: duplicate_of target not in registry")
            if source_pdf.is_file() and (source_root / by_id[duplicate_of]["relative_path"]).is_file():
                if sha256_path(source_pdf) != sha256_path(source_root / by_id[duplicate_of]["relative_path"]):
                    errors.append(f"{row['doc_id']}: duplicate alias hash differs from canonical PDF")
            if not (package / "status.json").is_file():
                missing.append(row["doc_id"])
            continue
        if not (package / "status.json").is_file() and source_pdf.is_file():
            source_hash = sha256_path(source_pdf)
            override = state_overrides.get(source_hash)
            if (
                override
                and override.get("terminal_class") == "SOURCE_UNREADABLE_BLOCKED"
                and override.get("qa_status") == "VERIFIED"
            ):
                blocked.append(row["doc_id"])
                packages.append(
                    {
                        "doc_id": row["doc_id"],
                        "state": "SOURCE_UNREADABLE_BLOCKED",
                        "pages": 0,
                        "chunks": 1,
                        "tables": 0,
                        "figures": 0,
                        "formulas": 0,
                        "manual_review_pages": 0,
                        "recovery_method": "verified_source_state_override",
                        "location_status": "file_level_boundary_only",
                        "source_pdf_sha256": source_hash,
                        "evidence": override.get("evidence", ""),
                    }
                )
                warnings.append(
                    f"{row['doc_id']}: exact source is verified unreadable; numeric and graphical reuse is forbidden"
                )
                continue
        package_errors, package_warnings, summary = validate_package(package, row, source_pdf)
        errors.extend(package_errors)
        warnings.extend(package_warnings)
        packages.append(summary)
        if summary["state"] == "MISSING":
            missing.append(row["doc_id"])

    db_path = source_layer / "indexes" / "standards_knowledge.sqlite"
    query_checks: list[dict] = []
    if not db_path.is_file():
        errors.append(f"search database missing: {db_path}")
    else:
        connection = sqlite3.connect(db_path)
        try:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                errors.append(f"SQLite integrity_check: {integrity}")
            indexed_ids = {row[0] for row in connection.execute("SELECT doc_id FROM documents")}
            checks = [
                ("固定管板", "std_gb_t_28712_2_2023"),
                ("液压试验", "std_gb_t_12771_2019"),
                ("塔式容器", "std_nb_t_47041_2014"),
                ("公称外径", "std_gb_t_17395_2024"),
            ]
            for term, doc_id in checks:
                if doc_id not in indexed_ids:
                    continue
                passed = smoke_query(connection, term, doc_id)
                query_checks.append({"query": term, "doc_id": doc_id, "status": "PASS" if passed else "FAIL"})
                if not passed:
                    errors.append(f"scripted retrieval regression: {term!r} not found in {doc_id}")
        finally:
            connection.close()

    if missing and not args.allow_incomplete:
        errors.append(f"{len(missing)} registry documents do not have completed canonical packages")
    status = "FAIL" if errors else (
        "INCOMPLETE" if missing else ("PASS_WITH_BLOCKED_SOURCE" if blocked else "PASS")
    )
    report = {
        "schema": "design-standards-source-layer-validation-v1",
        "status": status,
        "registry_documents": len(registry),
        "canonical_documents": len({row.get("duplicate_of") or row["doc_id"] for row in registry}),
        "validated_packages": sum(row.get("state") != "MISSING" for row in packages),
        "missing_documents": missing,
        "blocked_source_documents": blocked,
        "errors": errors,
        "warnings": warnings,
        "query_checks": query_checks,
        "packages": packages,
    }
    report_path = source_layer / "validation_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"status={status} registry={len(registry)} validated={report['validated_packages']} missing={len(missing)}")
        for error in errors:
            print(f"ERROR: {error}")
        for warning in warnings:
            print(f"WARN: {warning}")
        for check in query_checks:
            print(f"QUERY {check['status']}: {check['query']} -> {check['doc_id']}")
        print(f"report={report_path}")
    return 1 if errors else (2 if missing else 0)


if __name__ == "__main__":
    raise SystemExit(main())
