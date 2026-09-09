# -*- coding: utf-8 -*-
"""Query L0 textbook OCR evidence after selecting an upper graph concept/method."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "indexes" / "chemical_principles_evidence.sqlite"


def query_terms(text: str) -> list[str]:
    terms = [
        part.strip()
        for part in re.split(r"[\s,，;；。！？、/]+", text)
        if len(part.strip()) >= 2
    ]
    return terms[:12] or [text.strip()]


def fts_expression(terms: list[str], operator: str) -> str:
    quoted = ['"' + term.replace('"', '""') + '"' for term in terms if len(term) >= 3]
    return f" {operator} ".join(quoted)


def run_query(
    connection: sqlite3.Connection,
    text: str,
    *,
    limit: int,
    volume: str | None,
    chapter: str | None,
) -> list[dict]:
    terms = query_terms(text)
    has_trigram = (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='chunks_trigram'"
        ).fetchone()
        is not None
    )
    filters = []
    parameters: list[object] = []
    if volume:
        filters.append("c.volume = ?")
        parameters.append(volume)
    if chapter:
        filters.append("(c.chapter_id = ? OR c.chapter_title LIKE ?)")
        parameters.extend([chapter, f"%{chapter}%"])
    filter_sql = " AND " + " AND ".join(filters) if filters else ""

    if has_trigram:
        for operator in ("AND", "OR"):
            expression = fts_expression(terms, operator)
            if not expression:
                break
            rows = connection.execute(
                f"""
                SELECT c.chunk_id,c.page_id,c.source_id,c.volume,c.pdf_page,
                       c.chapter_id,c.chapter_title,c.knowledge_layer,
                       c.evidence_status,c.mean_confidence,c.source_pdf_path,
                       c.source_pdf_sha256,c.source_text_path,c.text,
                       bm25(chunks_trigram) AS rank
                FROM chunks_trigram f
                JOIN chunks c ON c.chunk_id=f.chunk_id
                WHERE chunks_trigram MATCH ? {filter_sql}
                ORDER BY rank,c.volume,c.pdf_page,c.chunk_order
                LIMIT ?
                """,
                [expression, *parameters, limit],
            ).fetchall()
            if rows:
                return [
                    {
                        "chunk_id": row[0],
                        "page_id": row[1],
                        "source_id": row[2],
                        "volume": row[3],
                        "pdf_page": row[4],
                        "chapter_id": row[5],
                        "chapter_title": row[6],
                        "knowledge_layer": row[7],
                        "evidence_status": row[8],
                        "mean_confidence": row[9],
                        "source_pdf_path": row[10],
                        "source_pdf_sha256": row[11],
                        "source_text_path": row[12],
                        "text": row[13],
                        "rank": row[14],
                        "numeric_formula_notice": "visual verification required before formal numeric/formula reuse",
                    }
                    for row in rows
                ]

    like_clauses = ["c.search_text LIKE ?" for _ in terms]
    like_values = [f"%{term}%" for term in terms]
    match_count_sql = " + ".join(
        "CASE WHEN c.search_text LIKE ? THEN 1 ELSE 0 END" for _ in terms
    )
    rows = connection.execute(
        f"""
        SELECT c.chunk_id,c.page_id,c.source_id,c.volume,c.pdf_page,
               c.chapter_id,c.chapter_title,c.knowledge_layer,
               c.evidence_status,c.mean_confidence,c.source_pdf_path,
               c.source_pdf_sha256,c.source_text_path,c.text,
               ({match_count_sql}) AS term_match_count
        FROM chunks c
        WHERE ({" OR ".join(like_clauses)}) {filter_sql}
        ORDER BY term_match_count DESC,c.volume,c.pdf_page,c.chunk_order
        LIMIT ?
        """,
        [*like_values, *like_values, *parameters, limit],
    ).fetchall()
    return [
        {
            "chunk_id": row[0],
            "page_id": row[1],
            "source_id": row[2],
            "volume": row[3],
            "pdf_page": row[4],
            "chapter_id": row[5],
            "chapter_title": row[6],
            "knowledge_layer": row[7],
            "evidence_status": row[8],
            "mean_confidence": row[9],
            "source_pdf_path": row[10],
            "source_pdf_sha256": row[11],
            "source_text_path": row[12],
            "text": row[13],
            "rank": -row[14],
            "term_match_count": row[14],
            "numeric_formula_notice": "visual verification required before formal numeric/formula reuse",
        }
        for row in rows
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("terms", nargs="+")
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--volume", choices=["upper", "lower"])
    parser.add_argument("--chapter", help="Chapter ID or title.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not DATABASE.is_file():
        raise SystemExit(
            "Evidence index missing. Build it first with "
            "python chemical_principles_knowledge\\scripts\\build_textbook_search_index.py"
        )
    connection = sqlite3.connect(DATABASE)
    try:
        results = run_query(
            connection,
            " ".join(args.terms),
            limit=max(1, args.limit),
            volume=args.volume,
            chapter=args.chapter,
        )
    finally:
        connection.close()

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for index, result in enumerate(results, 1):
            snippet = re.sub(r"\s+", " ", result["text"]).strip()[:320]
            print(
                f"[{index}] {result['chapter_id']} {result['chapter_title']} "
                f"{result['volume']} PDF p.{result['pdf_page']} "
                f"{result['evidence_status']} conf={result['mean_confidence']}"
            )
            print(f"    {snippet}")
            print(f"    {result['source_text_path']}")
    return 0 if results else 1


if __name__ == "__main__":
    raise SystemExit(main())
