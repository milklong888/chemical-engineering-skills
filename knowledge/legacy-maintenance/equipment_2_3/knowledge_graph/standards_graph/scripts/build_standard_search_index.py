#!/usr/bin/env python3
"""Aggregate per-PDF packages into deterministic catalogs and SQLite FTS."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_csv(path: Path, rows: list[dict], exclude: set[str] | None = None) -> None:
    exclude = exclude or set()
    output = []
    fields: list[str] = []
    for row in rows:
        flat = {}
        for key, value in row.items():
            if key in exclude:
                continue
            flat[key] = json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value
            if key not in fields:
                fields.append(key)
        output.append(flat)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if fields:
            writer.writeheader()
            writer.writerows(output)


def table_text(document_dir: Path, record: dict) -> str:
    paths = [document_dir / record["csv_path"]] + [document_dir / item["csv_path"] for item in record.get("continuations", [])]
    parts = []
    for path in paths:
        if not path.is_file():
            continue
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            parts.append("\n".join(" | ".join(row) for row in csv.reader(handle)))
    return "\n".join(parts)


def search_text(text: str) -> str:
    previous = None
    while text != previous:
        previous = text
        text = re.sub(r"(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])", "", text)
    return text


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


def blocked_source_record(
    row: dict[str, str], source_pdf: Path, source_hash: str, override: dict[str, str]
) -> tuple[dict, dict]:
    state = override["terminal_class"]
    note = override.get("evidence", "")
    text = (
        f"源文件边界记录：{row['relative_path']}。"
        f"状态：{state}。{note}。"
        "该文件不得作为数值、公式、图表或选型依据；取得完整可读的同版原文后必须重新抽取。"
    )
    document = {
        **row,
        "canonical_doc_id": row["doc_id"],
        "source_pdf_path": str(source_pdf.resolve()),
        "source_pdf_sha256": source_hash,
        "page_count": 0,
        "chunk_count": 1,
        "table_count": 0,
        "figure_count": 0,
        "manual_review_page_count": 0,
        "package_status": state,
        "package_path": "",
    }
    chunk = {
        "chunk_id": f"{row['doc_id']}:source_boundary",
        "doc_id": row["doc_id"],
        "chunk_order": 1,
        "relative_path": row["relative_path"],
        "source_pdf_path": str(source_pdf.resolve()),
        "source_pdf_sha256": source_hash,
        "family": row["family"],
        "source_kind": row["source_kind"],
        "evidence_default": row["evidence_default"],
        "page_start": 0,
        "page_end": 0,
        "section_path": "源文件边界/损坏或不可读",
        "extraction_methods": ["verified_source_state_override"],
        "quality_score": 1.0,
        "char_count": len(text),
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest().upper(),
        "block_refs": [],
        "text": text,
        "location_status": "file_level_boundary_only",
    }
    return document, chunk


def recovered_content_chunks(source_layer: Path, row: dict, source_pdf: Path, doc_hash: str) -> list[dict] | None:
    path = source_layer / "recovered" / row["doc_id"] / "content_stream_gbk_pages.jsonl"
    if not path.is_file():
        return None
    pages = read_jsonl(path)
    chunks = []
    for page in pages:
        text = page.get("text_in_operation_order", "").strip()
        if not text:
            continue
        for part_index, start in enumerate(range(0, len(text), 1400), 1):
            part = text[start : start + 1550]
            chunk_id = f"{row['doc_id']}:recovered:p{int(page['page_1based']):04d}:c{part_index:02d}"
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "doc_id": row["doc_id"],
                    "chunk_order": len(chunks) + 1,
                    "relative_path": row["relative_path"],
                    "source_pdf_path": str(source_pdf.resolve()),
                    "source_pdf_sha256": doc_hash,
                    "family": row["family"],
                    "source_kind": row["source_kind"],
                    "evidence_default": row["evidence_default"],
                    "page_start": int(page["page_1based"]),
                    "page_end": int(page["page_1based"]),
                    "section_path": "GB18030原始内容流恢复（页级定位）",
                    "extraction_methods": [page.get("method", "pypdf_content_stream_original_bytes_gb18030")],
                    "quality_score": 0.9,
                    "char_count": len(part),
                    "text_sha256": hashlib.sha256(part.encode("utf-8")).hexdigest().upper(),
                    "block_refs": [],
                    "text": part,
                    "location_status": "page_level_only_no_glyph_bbox",
                }
            )
    return chunks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--source-layer", type=Path, required=True)
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()

    source_root = args.source_root.resolve()
    source_layer = args.source_layer.resolve()
    documents_root = source_layer / "documents"
    indexes_root = source_layer / "indexes"
    indexes_root.mkdir(parents=True, exist_ok=True)
    registry = read_csv(args.registry.resolve())
    registry_by_id = {row["doc_id"]: row for row in registry}
    documents: list[dict] = []
    chunks: list[dict] = []
    tables: list[dict] = []
    figures: list[dict] = []
    formulas: list[dict] = []
    missing: list[str] = []
    blocked: list[str] = []
    state_overrides = source_state_overrides(source_layer)

    for row in registry:
        doc_id = row["doc_id"]
        duplicate_of = row.get("duplicate_of", "")
        package_id = duplicate_of or doc_id
        package_dir = documents_root / package_id
        status_path = package_dir / "status.json"
        source_pdf = source_root / Path(row["relative_path"])
        if not status_path.is_file():
            if source_pdf.is_file():
                source_hash = sha256_path(source_pdf)
                override = state_overrides.get(source_hash)
                if override and override.get("terminal_class") == "SOURCE_UNREADABLE_BLOCKED" and not duplicate_of:
                    document, chunk = blocked_source_record(row, source_pdf, source_hash, override)
                    documents.append(document)
                    chunks.append(chunk)
                    blocked.append(doc_id)
                    continue
            missing.append(doc_id)
            continue
        status = json.loads(status_path.read_text(encoding="utf-8"))
        if status.get("status") not in {"PASS", "PASS_WITH_REVIEW"}:
            missing.append(doc_id)
            continue
        manual_review_pages = status.get("manual_review_pages", [])
        package_status = status["status"]
        if package_status == "PASS" and manual_review_pages:
            package_status = "PASS_WITH_REVIEW"
        recovery_quality_path = (
            source_layer / "recovered" / doc_id / "content_stream_gbk_quality.json"
        )
        if recovery_quality_path.is_file():
            recovery_quality = json.loads(recovery_quality_path.read_text(encoding="utf-8"))
            package_status = recovery_quality.get("status", package_status)
        documents.append(
            {
                **row,
                "canonical_doc_id": package_id,
                "source_pdf_path": str(source_pdf.resolve()),
                "source_pdf_sha256": status["source_pdf_sha256"] if not duplicate_of else status["source_pdf_sha256"],
                "page_count": status["page_count"],
                "chunk_count": status["chunk_count"],
                "table_count": status["table_count"],
                "figure_count": status["figure_count"],
                "manual_review_page_count": len(manual_review_pages),
                "package_status": package_status,
                "package_path": str(package_dir.resolve()),
            }
        )
        if duplicate_of:
            continue
        pages = read_jsonl(package_dir / "raw_pages.jsonl")
        block_map = {
            line["block_id"]: {
                "block_id": line["block_id"],
                "page_1based": page["page_1based"],
                "bbox_pt": line["bbox_pt"],
                "method": line["method"],
                "text": line.get("text", ""),
            }
            for page in pages
            for line in page.get("lines", [])
        }
        recovered_chunks = recovered_content_chunks(source_layer, row, source_pdf, status["source_pdf_sha256"])
        if recovered_chunks is not None:
            for chunk in recovered_chunks:
                chunk["package_path"] = str(package_dir.resolve())
                chunks.append(chunk)
        else:
            for chunk in read_jsonl(package_dir / "chunks.jsonl"):
                chunk["block_refs"] = [block_map[block_id] for block_id in chunk.get("block_ids", []) if block_id in block_map]
                chunk["source_pdf_path"] = str(source_pdf.resolve())
                chunk["package_path"] = str(package_dir.resolve())
                chunks.append(chunk)
        for table in read_jsonl(package_dir / "tables.jsonl"):
            table["cell_text"] = table_text(package_dir, table)
            table["source_pdf_path"] = str(source_pdf.resolve())
            table["csv_absolute_path"] = str((package_dir / table["csv_path"]).resolve())
            table["cell_audit_absolute_path"] = str((package_dir / table["cell_audit_csv_path"]).resolve()) if table.get("cell_audit_csv_path") else ""
            tables.append(table)
        for table in read_jsonl(package_dir / "derived_assets.jsonl"):
            table["cell_text"] = table_text(package_dir, table)
            table["source_pdf_path"] = str(source_pdf.resolve())
            table["csv_absolute_path"] = str((package_dir / table["csv_path"]).resolve())
            table["cell_audit_absolute_path"] = str((package_dir / table["cell_audit_csv_path"]).resolve()) if table.get("cell_audit_csv_path") else ""
            tables.append(table)
        for figure in read_jsonl(package_dir / "figures.jsonl"):
            figure["source_pdf_path"] = str(source_pdf.resolve())
            figure["image_absolute_path"] = str((package_dir / figure["image_path"]).resolve())
            figures.append(figure)
        for formula in read_jsonl(package_dir / "formulas.jsonl"):
            formula["source_pdf_path"] = str(source_pdf.resolve())
            formula["image_absolute_path"] = str((package_dir / formula["image_path"]).resolve())
            formulas.append(formula)

    if missing and not args.allow_incomplete:
        raise RuntimeError("missing or failed document packages: " + ", ".join(missing))

    write_csv(indexes_root / "documents.csv", documents)
    write_csv(indexes_root / "chunk_catalog.csv", chunks, {"text", "block_ids", "block_refs"})
    write_csv(indexes_root / "table_catalog.csv", tables, {"cell_text"})
    write_csv(indexes_root / "figure_catalog.csv", figures)
    write_csv(indexes_root / "formula_catalog.csv", formulas, {"raw_text"})

    db_path = indexes_root / "standards_knowledge.sqlite"
    temp_db = indexes_root / ".standards_knowledge.sqlite.tmp"
    temp_db.unlink(missing_ok=True)
    connection = sqlite3.connect(temp_db)
    try:
        connection.executescript(
            """
            PRAGMA journal_mode=OFF;
            PRAGMA synchronous=OFF;
            CREATE TABLE documents(
              doc_id TEXT PRIMARY KEY, canonical_doc_id TEXT, relative_path TEXT,
              source_pdf_path TEXT, source_pdf_sha256 TEXT, family TEXT,
              source_kind TEXT, evidence_default TEXT, duplicate_of TEXT,
              language TEXT, priority TEXT, page_count INTEGER, chunk_count INTEGER,
              table_count INTEGER, figure_count INTEGER, manual_review_page_count INTEGER,
              package_status TEXT, package_path TEXT
            );
            CREATE TABLE chunks(
              chunk_id TEXT PRIMARY KEY, doc_id TEXT, chunk_order INTEGER,
              relative_path TEXT, source_pdf_path TEXT, source_pdf_sha256 TEXT,
              family TEXT, source_kind TEXT, evidence_default TEXT,
              page_start INTEGER, page_end INTEGER, section_path TEXT,
              extraction_methods TEXT, quality_score REAL, char_count INTEGER,
              text_sha256 TEXT, block_refs_json TEXT, location_status TEXT, text TEXT
            );
            CREATE TABLE tables_data(
              table_id TEXT PRIMARY KEY, doc_id TEXT, page_id TEXT, page_1based INTEGER,
              table_order INTEGER, method TEXT, structure_confidence REAL,
              bbox_json TEXT, caption TEXT, row_count INTEGER, column_count INTEGER,
              nonempty_cells INTEGER, key_table INTEGER, csv_path TEXT,
              csv_absolute_path TEXT, source_pdf_path TEXT, source_pdf_sha256 TEXT,
              cell_text TEXT, structure_mode TEXT, numeric_reuse_allowed INTEGER,
              geometry_preserved INTEGER, common_spec_cells INTEGER,
              cell_audit_absolute_path TEXT, asset_label TEXT, asset_qa_status TEXT,
              structure_override INTEGER
            );
            CREATE TABLE figures_data(
              figure_id TEXT PRIMARY KEY, doc_id TEXT, page_id TEXT, page_1based INTEGER,
              figure_order INTEGER, method TEXT, bbox_json TEXT, caption TEXT,
              key_figure INTEGER, image_path TEXT, image_absolute_path TEXT,
              source_pdf_path TEXT, source_pdf_sha256 TEXT
            );
            CREATE TABLE formulas_data(
              formula_id TEXT PRIMARY KEY, doc_id TEXT, page_id TEXT, page_1based INTEGER,
              formula_order INTEGER, label TEXT, caption TEXT, bbox_json TEXT,
              raw_text TEXT, method TEXT, qa_status TEXT, image_path TEXT,
              image_absolute_path TEXT, source_pdf_path TEXT, source_pdf_sha256 TEXT
            );
            CREATE VIRTUAL TABLE chunks_fts USING fts5(
              chunk_id UNINDEXED, doc_id UNINDEXED, section_path, text,
              tokenize='unicode61 remove_diacritics 2'
            );
            CREATE VIRTUAL TABLE tables_fts USING fts5(
              table_id UNINDEXED, doc_id UNINDEXED, caption, cell_text,
              tokenize='unicode61 remove_diacritics 2'
            );
            CREATE VIRTUAL TABLE figures_fts USING fts5(
              figure_id UNINDEXED, doc_id UNINDEXED, caption,
              tokenize='unicode61 remove_diacritics 2'
            );
            CREATE VIRTUAL TABLE formulas_fts USING fts5(
              formula_id UNINDEXED, doc_id UNINDEXED, label, caption, raw_text,
              tokenize='unicode61 remove_diacritics 2'
            );
            CREATE VIRTUAL TABLE chunks_trigram USING fts5(
              chunk_id UNINDEXED, doc_id UNINDEXED, text, tokenize='trigram'
            );
            CREATE VIRTUAL TABLE tables_trigram USING fts5(
              table_id UNINDEXED, doc_id UNINDEXED, text, tokenize='trigram'
            );
            CREATE VIRTUAL TABLE figures_trigram USING fts5(
              figure_id UNINDEXED, doc_id UNINDEXED, text, tokenize='trigram'
            );
            CREATE VIRTUAL TABLE formulas_trigram USING fts5(
              formula_id UNINDEXED, doc_id UNINDEXED, text, tokenize='trigram'
            );
            """
        )
        connection.executemany(
            "INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                (
                    row["doc_id"], row["canonical_doc_id"], row["relative_path"],
                    row["source_pdf_path"], row["source_pdf_sha256"], row["family"],
                    row["source_kind"], row["evidence_default"], row.get("duplicate_of", ""),
                    row["language"], row["priority"], int(row["page_count"]), int(row["chunk_count"]),
                    int(row["table_count"]), int(row["figure_count"]), int(row["manual_review_page_count"]),
                    row["package_status"], row["package_path"],
                )
                for row in documents
            ],
        )
        connection.executemany(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                (
                    row["chunk_id"], row["doc_id"], row["chunk_order"], row["relative_path"],
                    row["source_pdf_path"], row["source_pdf_sha256"], row["family"], row["source_kind"],
                    row["evidence_default"], row["page_start"], row["page_end"], row["section_path"],
                    json.dumps(row["extraction_methods"], ensure_ascii=False), row["quality_score"], row["char_count"],
                    row["text_sha256"], json.dumps(row["block_refs"], ensure_ascii=False), row.get("location_status", "block_bbox_available"), row["text"],
                )
                for row in chunks
            ],
        )
        connection.executemany(
            "INSERT INTO chunks_fts(chunk_id,doc_id,section_path,text) VALUES (?,?,?,?)",
            [(row["chunk_id"], row["doc_id"], row["section_path"], row["text"]) for row in chunks],
        )
        connection.executemany(
            "INSERT INTO chunks_trigram(chunk_id,doc_id,text) VALUES (?,?,?)",
            [(row["chunk_id"], row["doc_id"], search_text(row["section_path"] + "\n" + row["text"])) for row in chunks],
        )
        connection.executemany(
            "INSERT INTO tables_data VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                (
                    row["table_id"], row["doc_id"], row["page_id"], row["page_1based"], row["table_order"],
                    row["method"], row["structure_confidence"], json.dumps(row["bbox_pt"]), row["caption"],
                    row["row_count"], row["column_count"], row["nonempty_cells"], int(row["key_table"]),
                    row["csv_path"], row["csv_absolute_path"], row["source_pdf_path"], row["source_pdf_sha256"],
                    row["cell_text"], row.get("structure_mode", "cell_grid"), int(bool(row.get("numeric_reuse_allowed", False))),
                    int(bool(row.get("geometry_preserved", True))), int(row.get("common_spec_cells", 0)),
                    row.get("cell_audit_absolute_path", ""), row.get("asset_label", ""), row.get("asset_qa_status", ""),
                    int(bool(row.get("structure_override", False))),
                )
                for row in tables
            ],
        )
        connection.executemany(
            "INSERT INTO tables_fts(table_id,doc_id,caption,cell_text) VALUES (?,?,?,?)",
            [(row["table_id"], row["doc_id"], row["caption"], row["cell_text"]) for row in tables],
        )
        connection.executemany(
            "INSERT INTO tables_trigram(table_id,doc_id,text) VALUES (?,?,?)",
            [(row["table_id"], row["doc_id"], search_text(row["caption"] + "\n" + row["cell_text"])) for row in tables],
        )
        connection.executemany(
            "INSERT INTO figures_data VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                (
                    row["figure_id"], row["doc_id"], row["page_id"], row["page_1based"], row["figure_order"],
                    row["method"], json.dumps(row["bbox_pt"]), row["caption"], int(row["key_figure"]),
                    row["image_path"], row["image_absolute_path"], row["source_pdf_path"], row["source_pdf_sha256"],
                )
                for row in figures
            ],
        )
        connection.executemany(
            "INSERT INTO figures_fts(figure_id,doc_id,caption) VALUES (?,?,?)",
            [(row["figure_id"], row["doc_id"], row["caption"]) for row in figures],
        )
        connection.executemany(
            "INSERT INTO figures_trigram(figure_id,doc_id,text) VALUES (?,?,?)",
            [(row["figure_id"], row["doc_id"], search_text(row["caption"])) for row in figures],
        )
        connection.executemany(
            "INSERT INTO formulas_data VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                (
                    row["formula_id"], row["doc_id"], row["page_id"], row["page_1based"], row["formula_order"],
                    row.get("label", ""), row.get("caption", ""), json.dumps(row["bbox_pt"]), row.get("raw_text", ""),
                    row["method"], row.get("qa_status", ""), row["image_path"], row["image_absolute_path"],
                    row["source_pdf_path"], row["source_pdf_sha256"],
                )
                for row in formulas
            ],
        )
        connection.executemany(
            "INSERT INTO formulas_fts(formula_id,doc_id,label,caption,raw_text) VALUES (?,?,?,?,?)",
            [(row["formula_id"], row["doc_id"], row.get("label", ""), row.get("caption", ""), row.get("raw_text", "")) for row in formulas],
        )
        connection.executemany(
            "INSERT INTO formulas_trigram(formula_id,doc_id,text) VALUES (?,?,?)",
            [(row["formula_id"], row["doc_id"], search_text(row.get("label", "") + "\n" + row.get("caption", "") + "\n" + row.get("raw_text", ""))) for row in formulas],
        )
        connection.commit()
        check = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if check != "ok":
            raise RuntimeError(f"SQLite integrity check failed: {check}")
    finally:
        connection.close()
    temp_db.replace(db_path)

    summary = {
        "schema": "design-standards-search-index-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "INCOMPLETE" if missing else ("PASS_WITH_BLOCKED_SOURCE" if blocked else "PASS"),
        "registry_documents": len(registry),
        "indexed_document_aliases": len(documents),
        "indexed_canonical_documents": len({row["canonical_doc_id"] for row in documents}),
        "chunks": len(chunks),
        "tables": len(tables),
        "key_tables": sum(bool(row["key_table"]) for row in tables),
        "figures": len(figures),
        "key_figures": sum(bool(row["key_figure"]) for row in figures),
        "formulas": len(formulas),
        "missing_documents": missing,
        "blocked_source_documents": blocked,
        "database": str(db_path),
    }
    (indexes_root / "search_index_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not missing else 2


if __name__ == "__main__":
    raise SystemExit(main())
