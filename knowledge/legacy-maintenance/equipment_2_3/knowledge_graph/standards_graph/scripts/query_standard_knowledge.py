#!/usr/bin/env python3
"""Query standard source chunks, table CSVs, and figure assets with provenance."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import sys
from pathlib import Path


def excerpt(text: str, query: str, width: int = 220) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    index = compact.casefold().find(query.casefold())
    if index < 0:
        cjk = re.findall(r"[\u3400-\u9fff]", query)
        if len(cjk) >= 2:
            match = re.search(r"\s*".join(map(re.escape, cjk)), compact)
            if match:
                index = match.start()
    if index < 0:
        terms = [term for term in re.findall(r"[A-Za-z0-9_.+/-]+|[\u4e00-\u9fff]{2,}", query) if term]
        for term in terms:
            index = compact.casefold().find(term.casefold())
            if index >= 0:
                break
    if index < 0:
        return compact[:width] + ("…" if len(compact) > width else "")
    start = max(0, index - width // 2)
    end = min(len(compact), start + width)
    return ("…" if start else "") + compact[start:end] + ("…" if end < len(compact) else "")


def normalized_match_text(text: str) -> str:
    return re.sub(r"\s+", "", text).casefold()


def matching_block_refs(block_refs: list[dict], query: str) -> list[dict]:
    """Return the smallest useful source locations for a chunk hit."""
    needle = normalized_match_text(query)
    if not needle:
        return block_refs[:1]
    exact = [ref for ref in block_refs if needle in normalized_match_text(ref.get("text", ""))]
    if exact:
        return exact
    terms = [term for term in re.findall(r"[A-Za-z0-9_.+/-]+|[\u3400-\u9fff]{2,}", query) if term]
    partial = [
        ref
        for ref in block_refs
        if any(normalized_match_text(term) in normalized_match_text(ref.get("text", "")) for term in terms)
    ]
    return partial or block_refs[:1]


def fts_expression(query: str) -> str:
    terms = re.findall(r"[A-Za-z][A-Za-z0-9_.+/-]*|\d+(?:\.\d+)*|[\u4e00-\u9fff]{2,}", query)
    if not terms:
        return '"' + query.replace('"', '""') + '"'
    return " OR ".join('"' + term.replace('"', '""') + '"' for term in terms[:12])


def compact_query(query: str) -> str:
    return re.sub(r"\s+", "", query).replace('"', '""')


def use_trigram(query: str) -> bool:
    return bool(re.search(r"[\u3400-\u9fff]", query)) and len(compact_query(query)) >= 3


def governance_fields(item: dict, scope: str) -> dict[str, object]:
    package_state = item.get("document_package_state", "UNKNOWN")
    manual_review_pages = int(item.get("document_manual_review_page_count", 0) or 0)
    if package_state == "PASS" and manual_review_pages:
        package_state = "PASS_WITH_REVIEW"

    location_status = item.get("location_status", "block_bbox_available")
    if location_status == "page_level_only_no_glyph_bbox":
        extraction_status = "legacy_text_recovered_page_level_only"
        reuse_boundary = "routing_only; visual_page_check_required; no_auto_quote_or_numeric_reuse"
    elif scope == "table":
        extraction_status = item.get("asset_qa_status") or item.get("structure_mode") or "table_extracted_unverified"
        if not bool(item.get("numeric_reuse_allowed", False)):
            reuse_boundary = "table_structure_or_routing_only; inspect_cell_audit_and_original_page; no_automatic_numeric_reuse"
        elif package_state != "PASS":
            reuse_boundary = "review_required_before_quote_or_design_reuse"
        else:
            reuse_boundary = "source_table_evidence; applicability_and_cell_check_required"
    elif scope == "figure":
        extraction_status = item.get("asset_qa_status") or "figure_crop_extracted_unverified"
        reuse_boundary = "visual_routing_asset; verify_original_page_and_project_applicability_before_reuse"
    elif scope == "formula":
        extraction_status = item.get("qa_status") or item.get("asset_qa_status") or "formula_crop_extracted_unverified"
        reuse_boundary = "formula_image_evidence; verify_symbols_units_scope_and_original_page_before_use"
    else:
        extraction_status = "text_extracted_with_block_bbox"
        source_kind = str(item.get("document_source_kind", ""))
        evidence = str(item.get("document_evidence", ""))
        if package_state != "PASS":
            reuse_boundary = "review_required_before_quote_or_design_reuse"
        elif source_kind in {"design_book", "handbook", "course_design", "case"} or evidence.startswith("S0"):
            reuse_boundary = "method_or_routing_only; no_project_value_transfer"
        else:
            reuse_boundary = "source_text_evidence; applicability_and_clause_check_required"

    return {
        "package_state": package_state,
        "manual_review_page_count": manual_review_pages,
        "extraction_status": extraction_status,
        "reuse_boundary": reuse_boundary,
    }


def filters(args: argparse.Namespace, alias: str) -> tuple[str, list]:
    clauses = []
    values = []
    if args.doc_id:
        clauses.append(f"{alias}.doc_id = ?")
        values.append(args.doc_id)
    if args.family:
        clauses.append(f"d.family = ?")
        values.append(args.family)
    if args.source_kind:
        clauses.append(f"d.source_kind = ?")
        values.append(args.source_kind)
    if args.evidence:
        clauses.append(f"d.evidence_default LIKE ?")
        values.append("%" + args.evidence + "%")
    return (" AND " + " AND ".join(clauses) if clauses else ""), values


def query_chunks(connection: sqlite3.Connection, args: argparse.Namespace) -> list[dict]:
    where, values = filters(args, "c")
    page_filter = ""
    if args.page:
        page_filter = " AND c.page_start <= ? AND c.page_end >= ?"
        values.extend([args.page, args.page])
    exact_like = "%" + compact_query(args.query) + "%"
    rows = []
    sql_exact = f"""
      SELECT c.*, d.relative_path AS document_path, d.family AS document_family,
             d.source_kind AS document_source_kind, d.evidence_default AS document_evidence,
             d.package_status AS document_package_state,
             d.manual_review_page_count AS document_manual_review_page_count
      FROM chunks c JOIN documents d ON d.doc_id=c.doc_id
      WHERE replace(replace(replace(c.text,' ',''),char(10),''),'　','') LIKE ? {where} {page_filter}
      LIMIT ?
    """
    exact_values = [exact_like] + values + [args.limit]
    for row in connection.execute(sql_exact, exact_values):
        item = dict(row)
        item["search_score"] = 1000.0
        rows.append(item)
    if len(rows) < args.limit and not args.exact:
        fts_table = "chunks_trigram" if use_trigram(args.query) else "chunks_fts"
        fts_match = '"' + compact_query(args.query) + '"' if fts_table == "chunks_trigram" else fts_expression(args.query)
        sql_fts = f"""
          SELECT c.*, d.relative_path AS document_path, d.family AS document_family,
                 d.source_kind AS document_source_kind, d.evidence_default AS document_evidence,
                 d.package_status AS document_package_state,
                 d.manual_review_page_count AS document_manual_review_page_count,
                 bm25({fts_table}) AS fts_rank
          FROM {fts_table}
          JOIN chunks c ON c.chunk_id={fts_table}.chunk_id
          JOIN documents d ON d.doc_id=c.doc_id
          WHERE {fts_table} MATCH ? {where} {page_filter}
          ORDER BY fts_rank LIMIT ?
        """
        fts_values = [fts_match] + values + [args.limit * 2]
        for row in connection.execute(sql_fts, fts_values):
            item = dict(row)
            if any(current["chunk_id"] == item["chunk_id"] for current in rows):
                continue
            item["search_score"] = max(0.0, 100.0 - abs(float(item.get("fts_rank", 0.0))))
            rows.append(item)
            if len(rows) >= args.limit:
                break
    output = []
    for item in rows[: args.limit]:
        block_refs = json.loads(item["block_refs_json"])
        hit_refs = matching_block_refs(block_refs, args.query)
        output.append(
            {
                "scope": "chunk",
                "score": round(item["search_score"], 6),
                "doc_id": item["doc_id"],
                "path": item["document_path"],
                "source_pdf_path": item["source_pdf_path"],
                "source_pdf_sha256": item["source_pdf_sha256"],
                "family": item["document_family"],
                "source_kind": item["document_source_kind"],
                "evidence_default": item["document_evidence"],
                **governance_fields(item, "chunk"),
                "chunk_id": item["chunk_id"],
                "pages": [item["page_start"], item["page_end"]],
                "section_path": item["section_path"],
                "quality_score": item["quality_score"],
                "extraction_methods": json.loads(item["extraction_methods"]),
                "hit_locations": [
                    {
                        "page": ref.get("page_1based"),
                        "bbox_pt": ref.get("bbox_pt"),
                        "method": ref.get("method"),
                    }
                    for ref in hit_refs
                ],
                "location_status": item.get("location_status", "block_bbox_available"),
                "excerpt": excerpt(item["text"], args.query, args.context_chars),
            }
        )
        if args.include_block_refs:
            output[-1]["block_refs"] = block_refs
    return output


def query_assets(connection: sqlite3.Connection, args: argparse.Namespace, scope: str) -> list[dict]:
    if scope == "table":
        data_table, fts_table, id_col = "tables_data", "tables_fts", "table_id"
        text_cols = "t.caption || char(10) || t.cell_text"
        extra = "t.csv_absolute_path AS asset_path, t.bbox_json, t.structure_confidence AS quality_score, t.method, t.structure_mode, t.numeric_reuse_allowed, t.geometry_preserved, t.common_spec_cells, t.cell_audit_absolute_path, t.asset_label, t.asset_qa_status, t.structure_override"
    else:
        data_table, fts_table, id_col = "figures_data", "figures_fts", "figure_id"
        text_cols = "t.caption"
        extra = "t.image_absolute_path AS asset_path, t.bbox_json, 0.5 AS quality_score, t.method"
    where, values = filters(args, "t")
    page_filter = ""
    if args.page:
        page_filter = " AND t.page_1based = ?"
        values.append(args.page)
    exact_sql = f"""
      SELECT t.*, d.relative_path AS document_path, d.family AS document_family,
             d.source_kind AS document_source_kind, d.evidence_default AS document_evidence,
             d.package_status AS document_package_state,
             d.manual_review_page_count AS document_manual_review_page_count,
             {extra}
      FROM {data_table} t JOIN documents d ON d.doc_id=t.doc_id
      WHERE replace(replace(replace(({text_cols}),' ',''),char(10),''),'　','') LIKE ? {where} {page_filter} LIMIT ?
    """
    rows = [dict(row) for row in connection.execute(exact_sql, ["%" + compact_query(args.query) + "%"] + values + [args.limit])]
    if len(rows) < args.limit and not args.exact:
        trigram_table = "tables_trigram" if scope == "table" else "figures_trigram"
        active_fts = trigram_table if use_trigram(args.query) else fts_table
        fts_match = '"' + compact_query(args.query) + '"' if active_fts == trigram_table else fts_expression(args.query)
        fts_sql = f"""
          SELECT t.*, d.relative_path AS document_path, d.family AS document_family,
                 d.source_kind AS document_source_kind, d.evidence_default AS document_evidence,
                 d.package_status AS document_package_state,
                 d.manual_review_page_count AS document_manual_review_page_count,
                 {extra}, bm25({active_fts}) AS fts_rank
          FROM {active_fts}
          JOIN {data_table} t ON t.{id_col}={active_fts}.{id_col}
          JOIN documents d ON d.doc_id=t.doc_id
          WHERE {active_fts} MATCH ? {where} {page_filter}
          ORDER BY fts_rank LIMIT ?
        """
        for row in connection.execute(fts_sql, [fts_match] + values + [args.limit * 2]):
            item = dict(row)
            if any(current[id_col] == item[id_col] for current in rows):
                continue
            rows.append(item)
            if len(rows) >= args.limit:
                break
    output = []
    for item in rows[: args.limit]:
        text = item.get("caption", "") + ("\n" + item.get("cell_text", "") if scope == "table" else "")
        output.append(
            {
                "scope": scope,
                "doc_id": item["doc_id"],
                "path": item["document_path"],
                "source_pdf_path": item["source_pdf_path"],
                "source_pdf_sha256": item["source_pdf_sha256"],
                "family": item["document_family"],
                "source_kind": item["document_source_kind"],
                "evidence_default": item["document_evidence"],
                **governance_fields(item, scope),
                "asset_id": item[id_col],
                "page": item["page_1based"],
                "bbox_pt": json.loads(item["bbox_json"]),
                "location_status": "asset_bbox_available",
                "method": item["method"],
                "quality_score": item["quality_score"],
                "asset_path": item["asset_path"],
                "cell_audit_path": item.get("cell_audit_absolute_path", ""),
                "structure_mode": item.get("structure_mode", ""),
                "numeric_reuse_allowed": bool(item.get("numeric_reuse_allowed", False)),
                "geometry_preserved": bool(item.get("geometry_preserved", True)),
                "common_spec_cells": int(item.get("common_spec_cells", 0) or 0),
                "asset_label": item.get("asset_label", ""),
                "asset_qa_status": item.get("asset_qa_status", ""),
                "structure_override": bool(item.get("structure_override", False)),
                "excerpt": excerpt(text, args.query, args.context_chars),
            }
        )
    return output


def query_formulas(connection: sqlite3.Connection, args: argparse.Namespace) -> list[dict]:
    where, values = filters(args, "t")
    page_filter = ""
    if args.page:
        page_filter = " AND t.page_1based = ?"
        values.append(args.page)
    text_cols = "t.label || char(10) || t.caption || char(10) || t.raw_text"
    exact_sql = f"""
      SELECT t.*, d.relative_path AS document_path, d.family AS document_family,
             d.source_kind AS document_source_kind, d.evidence_default AS document_evidence,
             d.package_status AS document_package_state,
             d.manual_review_page_count AS document_manual_review_page_count
      FROM formulas_data t JOIN documents d ON d.doc_id=t.doc_id
      WHERE replace(replace(replace(({text_cols}),' ',''),char(10),''),'　','') LIKE ? {where} {page_filter} LIMIT ?
    """
    rows = [dict(row) for row in connection.execute(exact_sql, ["%" + compact_query(args.query) + "%"] + values + [args.limit])]
    if len(rows) < args.limit and not args.exact:
        active_fts = "formulas_trigram" if use_trigram(args.query) else "formulas_fts"
        fts_match = '"' + compact_query(args.query) + '"' if active_fts == "formulas_trigram" else fts_expression(args.query)
        fts_sql = f"""
          SELECT t.*, d.relative_path AS document_path, d.family AS document_family,
                 d.source_kind AS document_source_kind, d.evidence_default AS document_evidence,
                 d.package_status AS document_package_state,
                 d.manual_review_page_count AS document_manual_review_page_count,
                 bm25({active_fts}) AS fts_rank
          FROM {active_fts}
          JOIN formulas_data t ON t.formula_id={active_fts}.formula_id
          JOIN documents d ON d.doc_id=t.doc_id
          WHERE {active_fts} MATCH ? {where} {page_filter}
          ORDER BY fts_rank LIMIT ?
        """
        for row in connection.execute(fts_sql, [fts_match] + values + [args.limit * 2]):
            item = dict(row)
            if any(current["formula_id"] == item["formula_id"] for current in rows):
                continue
            rows.append(item)
            if len(rows) >= args.limit:
                break
    return [
        {
            "scope": "formula",
            "doc_id": item["doc_id"],
            "path": item["document_path"],
            "source_pdf_path": item["source_pdf_path"],
            "source_pdf_sha256": item["source_pdf_sha256"],
            "family": item["document_family"],
            "source_kind": item["document_source_kind"],
            "evidence_default": item["document_evidence"],
            **governance_fields(item, "formula"),
            "asset_id": item["formula_id"],
            "page": item["page_1based"],
            "bbox_pt": json.loads(item["bbox_json"]),
            "location_status": "asset_bbox_available",
            "method": item["method"],
            "quality_score": 1.0 if str(item.get("qa_status", "")).startswith("visually_confirmed") else 0.5,
            "asset_path": item["image_absolute_path"],
            "asset_label": item.get("label", ""),
            "asset_qa_status": item.get("qa_status", ""),
            "excerpt": excerpt(item.get("caption", "") + "\n" + item.get("raw_text", ""), args.query, args.context_chars),
        }
        for item in rows[: args.limit]
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query")
    parser.add_argument("--db", type=Path, default=Path(__file__).resolve().parents[1] / "source_layer" / "indexes" / "standards_knowledge.sqlite")
    parser.add_argument("--scope", choices=["all", "chunks", "tables", "figures", "formulas"], default="all")
    parser.add_argument("--doc-id")
    parser.add_argument("--family")
    parser.add_argument("--source-kind")
    parser.add_argument("--evidence")
    parser.add_argument("--page", type=int)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--context-chars", type=int, default=240)
    parser.add_argument("--exact", action="store_true")
    parser.add_argument("--format", choices=["text", "json", "jsonl", "csv"], default="text")
    parser.add_argument("--json", action="store_true", help="Deprecated alias for --format json")
    parser.add_argument("--include-block-refs", action="store_true", help="Include every source block in JSON output")
    args = parser.parse_args()
    if not args.db.is_file():
        raise FileNotFoundError(f"search database not built: {args.db}")
    connection = sqlite3.connect(args.db)
    connection.row_factory = sqlite3.Row
    try:
        if args.doc_id:
            resolved = connection.execute(
                "SELECT canonical_doc_id FROM documents WHERE doc_id COLLATE NOCASE = ?",
                (args.doc_id,),
            ).fetchone()
            if not resolved:
                legacy_doc_id = re.sub(
                    r"^(std_[a-z]+_t)(?=\d)", r"\1_", args.doc_id.casefold()
                )
                resolved = connection.execute(
                    "SELECT canonical_doc_id FROM documents WHERE doc_id = ?",
                    (legacy_doc_id,),
                ).fetchone()
            if resolved:
                args.doc_id = resolved["canonical_doc_id"]
        results = []
        if args.scope in {"all", "chunks"}:
            results.extend(query_chunks(connection, args))
        if args.scope in {"all", "tables"}:
            results.extend(query_assets(connection, args, "table"))
        if args.scope in {"all", "figures"}:
            results.extend(query_assets(connection, args, "figure"))
        if args.scope in {"all", "formulas"}:
            results.extend(query_formulas(connection, args))
    finally:
        connection.close()
    results = results[: args.limit] if args.scope == "all" else results
    if args.json:
        args.format = "json"
    if args.format == "json":
        print(json.dumps({"query": args.query, "count": len(results), "results": results}, ensure_ascii=False, indent=2))
    elif args.format == "jsonl":
        for item in results:
            print(json.dumps(item, ensure_ascii=False, separators=(",", ":")))
    elif args.format == "csv":
        fields = [
            "scope", "doc_id", "family", "source_kind", "evidence_default", "package_state",
            "manual_review_page_count", "extraction_status", "reuse_boundary", "page", "bbox_pt",
            "asset_or_chunk_id", "method", "quality_score", "source_pdf_path", "source_pdf_sha256",
            "asset_path", "cell_audit_path", "structure_mode", "numeric_reuse_allowed", "geometry_preserved",
            "location_status", "excerpt",
        ]
        writer = csv.DictWriter(sys.stdout, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for item in results:
            locations = item.get("hit_locations") or []
            writer.writerow(
                {
                    "scope": item["scope"],
                    "doc_id": item["doc_id"],
                    "family": item["family"],
                    "source_kind": item["source_kind"],
                    "evidence_default": item["evidence_default"],
                    "package_state": item.get("package_state", ""),
                    "manual_review_page_count": item.get("manual_review_page_count", ""),
                    "extraction_status": item.get("extraction_status", ""),
                    "reuse_boundary": item.get("reuse_boundary", ""),
                    "page": item.get("page", (locations[0].get("page") if locations else item.get("pages"))),
                    "bbox_pt": json.dumps(item.get("bbox_pt", locations[0].get("bbox_pt") if locations else None), ensure_ascii=False),
                    "asset_or_chunk_id": item.get("asset_id", item.get("chunk_id", "")),
                    "method": item.get("method", json.dumps(item.get("extraction_methods", []), ensure_ascii=False)),
                    "quality_score": item.get("quality_score"),
                    "source_pdf_path": item["source_pdf_path"],
                    "source_pdf_sha256": item["source_pdf_sha256"],
                    "asset_path": item.get("asset_path", ""),
                    "cell_audit_path": item.get("cell_audit_path", ""),
                    "structure_mode": item.get("structure_mode", ""),
                    "numeric_reuse_allowed": item.get("numeric_reuse_allowed", ""),
                    "geometry_preserved": item.get("geometry_preserved", ""),
                    "location_status": item.get("location_status", ""),
                    "excerpt": item["excerpt"],
                }
            )
    else:
        print(f"query={args.query!r} results={len(results)}")
        for index, item in enumerate(results, 1):
            page = item.get("page", item.get("pages"))
            print(f"\n[{index}] {item['scope']} {item['doc_id']} p{page} {item.get('asset_id', item.get('chunk_id', ''))}")
            print(f"    evidence={item['evidence_default']} method={item.get('method', item.get('extraction_methods'))} quality={item.get('quality_score')}")
            print(f"    package_state={item.get('package_state')} extraction_status={item.get('extraction_status')}")
            print(f"    reuse_boundary={item.get('reuse_boundary')}")
            print(f"    source={item['source_pdf_path']}")
            print(f"    sha256={item['source_pdf_sha256']}")
            if item.get("bbox_pt") is not None:
                print(f"    bbox_pt={item['bbox_pt']}")
            elif item.get("hit_locations"):
                locations = item["hit_locations"]
                rendered = "; ".join(f"p{loc['page']} {loc['bbox_pt']}" for loc in locations[:4])
                print(f"    hit_locations={rendered}")
            elif item.get("location_status"):
                print(f"    location_status={item['location_status']}")
            if item.get("asset_path"):
                print(f"    asset={item['asset_path']}")
            if item.get("cell_audit_path"):
                print(f"    cell_audit={item['cell_audit_path']}")
            if item["scope"] == "table":
                print(f"    structure_mode={item.get('structure_mode')} numeric_reuse_allowed={item.get('numeric_reuse_allowed')} geometry_preserved={item.get('geometry_preserved')}")
            print("    " + item["excerpt"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
