# -*- coding: utf-8 -*-
"""Build the local page/chunk evidence index for the chemical-principles books.

The global workspace vector index receives only concept, mechanism, and method
cards. Full OCR text remains here as L0 source evidence so detail volume cannot
displace the engineering worldview layer.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "source_registry.json"
CHAPTER_MAP_PATH = ROOT / "chapter_map.json"
SOURCE_PAGES = ROOT / "source_pages"
INDEXES = ROOT / "indexes"
DATABASE = INDEXES / "chemical_principles_evidence.sqlite"
SUMMARY = INDEXES / "search_index_summary.json"
PAGE_CATALOG = INDEXES / "page_catalog.csv"
CHUNK_CATALOG = INDEXES / "chunk_catalog.csv"

TARGET_CHARS = 1050
OVERLAP_CHARS = 150


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def body_text(page_text: str) -> str:
    marker = "numeric_formula_notice:"
    lines = page_text.splitlines()
    for index, line in enumerate(lines):
        if line.startswith(marker):
            return "\n".join(lines[index + 1 :]).strip()
    return page_text.strip()


def normalize_search_text(text: str) -> str:
    previous = None
    while previous != text:
        previous = text
        text = re.sub(r"(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])", "", text)
    return re.sub(r"\s+", " ", text).strip()


def split_chunks(text: str) -> list[str]:
    """Make deterministic page-local chunks without crossing source pages."""
    text = text.strip()
    if not text:
        return []
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > TARGET_CHARS * 2:
            if current:
                chunks.append(current)
                current = ""
            start = 0
            while start < len(paragraph):
                end = min(start + TARGET_CHARS, len(paragraph))
                chunks.append(paragraph[start:end].strip())
                if end >= len(paragraph):
                    break
                start = max(end - OVERLAP_CHARS, start + 1)
            continue
        candidate = paragraph if not current else current + "\n\n" + paragraph
        if len(candidate) <= TARGET_CHARS:
            current = candidate
            continue
        if current:
            chunks.append(current)
        carry = chunks[-1][-OVERLAP_CHARS:] if chunks else ""
        current = (carry + "\n" + paragraph).strip() if carry else paragraph
    if current:
        chunks.append(current)
    return [chunk for chunk in chunks if chunk]


def chapter_for(volume: str, page: int, chapter_map: dict[str, Any]) -> dict[str, Any]:
    for chapter in chapter_map["chapters"]:
        start, end = chapter["pdf_pages"]
        if chapter["volume"] == volume and int(start) <= page <= int(end):
            return chapter
    for supplement in chapter_map.get("supplementary_ranges", []):
        start, end = supplement["pdf_pages"]
        if supplement["volume"] == volume and int(start) <= page <= int(end):
            return {
                "chapter_id": f"CEPR-{volume.upper()}-SUPPLEMENT",
                "title": supplement["title"],
                "themes": [],
            }
    return {"chapter_id": "CEPR-FRONTMATTER", "title": "书前页", "themes": []}


def write_csv(path: Path, rows: list[dict[str, Any]], excluded: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    flattened: list[dict[str, Any]] = []
    for row in rows:
        item: dict[str, Any] = {}
        for key, value in row.items():
            if key in excluded:
                continue
            item[key] = json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value
            if key not in fields:
                fields.append(key)
        flattened.append(item)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(flattened)


def collect_records() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    registry = read_json(REGISTRY_PATH)
    chapter_map = read_json(CHAPTER_MAP_PATH)
    documents: list[dict[str, Any]] = []
    pages: list[dict[str, Any]] = []
    chunks: list[dict[str, Any]] = []

    for source in registry["sources"]:
        source_id = source["source_id"]
        volume = source["volume"]
        expected_pages = int(source["expected_pages"])
        documents.append(
            {
                "source_id": source_id,
                "volume": volume,
                "title": source["title"],
                "authors": source.get("authors_as_supplied", []),
                "source_pdf_path": source["path"],
                "source_pdf_sha256": source["sha256"].upper(),
                "expected_pages": expected_pages,
                "authority_tier": registry["authority_policy"]["tier"],
                "evidence_class": registry["authority_policy"]["evidence_class"],
                "distribution": registry["distribution"],
            }
        )
        for page_number in range(1, expected_pages + 1):
            stem = f"page_{page_number:04d}"
            text_path = SOURCE_PAGES / volume / f"{stem}.txt"
            meta_path = SOURCE_PAGES / volume / f"{stem}.json"
            if not text_path.is_file() or not meta_path.is_file():
                raise RuntimeError(f"missing page package: {volume} page {page_number}")
            metadata = read_json(meta_path)
            if metadata.get("source_sha256") != source["sha256"].upper():
                raise RuntimeError(f"source hash mismatch in {meta_path}")
            if int(metadata.get("pdf_page", -1)) != page_number:
                raise RuntimeError(f"page identity mismatch in {meta_path}")

            raw_text = text_path.read_text(encoding="utf-8")
            text = body_text(raw_text)
            chapter = chapter_for(volume, page_number, chapter_map)
            page_id = f"{source_id}:p{page_number:04d}"
            search_text = normalize_search_text(
                "\n".join(
                    [
                        source["title"],
                        chapter["title"],
                        " ".join(chapter.get("themes", [])),
                        text,
                    ]
                )
            )
            page = {
                "page_id": page_id,
                "source_id": source_id,
                "volume": volume,
                "pdf_page": page_number,
                "chapter_id": chapter["chapter_id"],
                "chapter_title": chapter["title"],
                "themes": chapter.get("themes", []),
                "knowledge_layer": "L0_source_detail",
                "evidence_status": metadata.get("status", "ocr_candidate"),
                "mean_confidence": metadata.get("mean_confidence"),
                "low_confidence_ratio": metadata.get("low_confidence_ratio"),
                "extraction_method": metadata.get("extraction_method", "tesseract_ocr"),
                "source_pdf_path": source["path"],
                "source_pdf_sha256": source["sha256"].upper(),
                "source_text_path": str(text_path.relative_to(ROOT)).replace("\\", "/"),
                "source_metadata_path": str(meta_path.relative_to(ROOT)).replace("\\", "/"),
                "text_sha256": sha256_text(raw_text),
                "text": text,
                "search_text": search_text,
                "numeric_formula_policy": "visual_verification_required_before_formal_numeric_reuse",
            }
            pages.append(page)
            for chunk_order, chunk_text in enumerate(split_chunks(text), 1):
                chunk_id = f"{page_id}:c{chunk_order:02d}"
                chunks.append(
                    {
                        "chunk_id": chunk_id,
                        "page_id": page_id,
                        "source_id": source_id,
                        "volume": volume,
                        "pdf_page": page_number,
                        "chapter_id": chapter["chapter_id"],
                        "chapter_title": chapter["title"],
                        "chunk_order": chunk_order,
                        "knowledge_layer": "L0_source_detail",
                        "evidence_status": metadata.get("status", "ocr_candidate"),
                        "mean_confidence": metadata.get("mean_confidence"),
                        "source_pdf_path": source["path"],
                        "source_pdf_sha256": source["sha256"].upper(),
                        "source_text_path": page["source_text_path"],
                        "text_sha256": sha256_text(chunk_text),
                        "text": chunk_text,
                        "search_text": normalize_search_text(
                            chapter["title"] + "\n" + " ".join(chapter.get("themes", [])) + "\n" + chunk_text
                        ),
                    }
                )
    return documents, pages, chunks


def build_database(
    documents: list[dict[str, Any]],
    pages: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
) -> bool:
    INDEXES.mkdir(parents=True, exist_ok=True)
    temp_path = DATABASE.with_suffix(".sqlite.tmp")
    temp_path.unlink(missing_ok=True)
    connection = sqlite3.connect(temp_path)
    trigram_available = True
    try:
        connection.executescript(
            """
            PRAGMA journal_mode=OFF;
            PRAGMA synchronous=OFF;
            CREATE TABLE documents(
              source_id TEXT PRIMARY KEY, volume TEXT, title TEXT, authors_json TEXT,
              source_pdf_path TEXT, source_pdf_sha256 TEXT, expected_pages INTEGER,
              authority_tier TEXT, evidence_class TEXT, distribution TEXT
            );
            CREATE TABLE pages(
              page_id TEXT PRIMARY KEY, source_id TEXT, volume TEXT, pdf_page INTEGER,
              chapter_id TEXT, chapter_title TEXT, themes_json TEXT, knowledge_layer TEXT,
              evidence_status TEXT, mean_confidence REAL, low_confidence_ratio REAL,
              extraction_method TEXT, source_pdf_path TEXT, source_pdf_sha256 TEXT,
              source_text_path TEXT, source_metadata_path TEXT, text_sha256 TEXT,
              numeric_formula_policy TEXT, text TEXT, search_text TEXT
            );
            CREATE TABLE chunks(
              chunk_id TEXT PRIMARY KEY, page_id TEXT, source_id TEXT, volume TEXT,
              pdf_page INTEGER, chapter_id TEXT, chapter_title TEXT, chunk_order INTEGER,
              knowledge_layer TEXT, evidence_status TEXT, mean_confidence REAL,
              source_pdf_path TEXT, source_pdf_sha256 TEXT, source_text_path TEXT,
              text_sha256 TEXT, text TEXT, search_text TEXT
            );
            CREATE INDEX pages_chapter_idx ON pages(chapter_id,pdf_page);
            CREATE INDEX chunks_chapter_idx ON chunks(chapter_id,pdf_page,chunk_order);
            CREATE VIRTUAL TABLE pages_fts USING fts5(
              page_id UNINDEXED, source_id UNINDEXED, chapter_title, text,
              tokenize='unicode61'
            );
            CREATE VIRTUAL TABLE chunks_fts USING fts5(
              chunk_id UNINDEXED, source_id UNINDEXED, chapter_title, text,
              tokenize='unicode61'
            );
            """
        )
        try:
            connection.executescript(
                """
                CREATE VIRTUAL TABLE pages_trigram USING fts5(
                  page_id UNINDEXED, source_id UNINDEXED, text, tokenize='trigram'
                );
                CREATE VIRTUAL TABLE chunks_trigram USING fts5(
                  chunk_id UNINDEXED, source_id UNINDEXED, text, tokenize='trigram'
                );
                """
            )
        except sqlite3.OperationalError:
            trigram_available = False

        connection.executemany(
            "INSERT INTO documents VALUES (?,?,?,?,?,?,?,?,?,?)",
            [
                (
                    row["source_id"],
                    row["volume"],
                    row["title"],
                    json.dumps(row["authors"], ensure_ascii=False),
                    row["source_pdf_path"],
                    row["source_pdf_sha256"],
                    row["expected_pages"],
                    row["authority_tier"],
                    row["evidence_class"],
                    row["distribution"],
                )
                for row in documents
            ],
        )
        connection.executemany(
            "INSERT INTO pages VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                (
                    row["page_id"], row["source_id"], row["volume"], row["pdf_page"],
                    row["chapter_id"], row["chapter_title"],
                    json.dumps(row["themes"], ensure_ascii=False), row["knowledge_layer"],
                    row["evidence_status"], row["mean_confidence"], row["low_confidence_ratio"],
                    row["extraction_method"], row["source_pdf_path"], row["source_pdf_sha256"],
                    row["source_text_path"], row["source_metadata_path"], row["text_sha256"],
                    row["numeric_formula_policy"], row["text"], row["search_text"],
                )
                for row in pages
            ],
        )
        connection.executemany(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                (
                    row["chunk_id"], row["page_id"], row["source_id"], row["volume"],
                    row["pdf_page"], row["chapter_id"], row["chapter_title"], row["chunk_order"],
                    row["knowledge_layer"], row["evidence_status"], row["mean_confidence"],
                    row["source_pdf_path"], row["source_pdf_sha256"], row["source_text_path"],
                    row["text_sha256"], row["text"], row["search_text"],
                )
                for row in chunks
            ],
        )
        connection.executemany(
            "INSERT INTO pages_fts(page_id,source_id,chapter_title,text) VALUES (?,?,?,?)",
            [(row["page_id"], row["source_id"], row["chapter_title"], row["search_text"]) for row in pages],
        )
        connection.executemany(
            "INSERT INTO chunks_fts(chunk_id,source_id,chapter_title,text) VALUES (?,?,?,?)",
            [(row["chunk_id"], row["source_id"], row["chapter_title"], row["search_text"]) for row in chunks],
        )
        if trigram_available:
            connection.executemany(
                "INSERT INTO pages_trigram(page_id,source_id,text) VALUES (?,?,?)",
                [(row["page_id"], row["source_id"], row["search_text"]) for row in pages],
            )
            connection.executemany(
                "INSERT INTO chunks_trigram(chunk_id,source_id,text) VALUES (?,?,?)",
                [(row["chunk_id"], row["source_id"], row["search_text"]) for row in chunks],
            )
        connection.commit()
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("SQLite integrity check failed")
    finally:
        connection.close()
    temp_path.replace(DATABASE)
    return trigram_available


def main() -> int:
    documents, pages, chunks = collect_records()
    expected = sum(row["expected_pages"] for row in documents)
    if len(pages) != expected:
        raise RuntimeError(f"page coverage mismatch expected={expected} actual={len(pages)}")
    trigram_available = build_database(documents, pages, chunks)
    write_csv(PAGE_CATALOG, pages, {"text", "search_text"})
    write_csv(CHUNK_CATALOG, chunks, {"text", "search_text"})

    statuses = Counter(row["evidence_status"] for row in pages)
    confidence_values = [
        float(row["mean_confidence"])
        for row in pages
        if row["mean_confidence"] is not None
    ]
    summary = {
        "schema": "chemical-principles-evidence-index-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS_WITH_REVIEW",
        "reason": "all pages are indexed; OCR numbers, equations, tables, figures, and low-confidence pages require visual verification",
        "documents": len(documents),
        "expected_pages": expected,
        "indexed_pages": len(pages),
        "indexed_chunks": len(chunks),
        "status_counts": dict(statuses),
        "mean_of_page_mean_confidence": (
            round(sum(confidence_values) / len(confidence_values), 2)
            if confidence_values
            else None
        ),
        "knowledge_layer": "L0_source_detail",
        "trigram_fts": trigram_available,
        "database": str(DATABASE.resolve()),
        "global_vector_boundary": "raw OCR pages excluded; only L3/L2/L1 graph cards enter workspace vector index",
        "numeric_formula_policy": "visual_verification_required_before_formal_numeric_reuse",
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
