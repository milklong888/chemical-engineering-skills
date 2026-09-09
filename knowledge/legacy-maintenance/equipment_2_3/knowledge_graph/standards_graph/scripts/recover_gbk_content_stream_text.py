#!/usr/bin/env python3
"""Recover legacy GBK/GB18030 text directly from PDF content streams.

This utility is intentionally separate from the normal OCR extractor.  It is
for old PDFs whose native text is mojibake and whose missing Chinese font maps
cause rendered OCR to recognise substituted glyphs instead of the source text.

The script reads the original bytes carried by PDF ``Tj``/``TJ`` operators,
decodes them with GB18030 in content-stream order, and writes one UTF-8 JSONL
record per physical page plus a deterministic quality report.  It does not
rewrite the PDF and it does not mutate an existing standards document package.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from pypdf import PdfReader
from pypdf.generic import ContentStream


SCHEMA = "legacy-gbk-content-stream-recovery-v1"
REPORT_SCHEMA = "legacy-gbk-content-stream-quality-v1"
CN_NUMERALS = "一二三四五六七八九十百"
CHAPTER_RE = re.compile(rf"第[{CN_NUMERALS}]+章")
SECTION_RE = re.compile(rf"第[{CN_NUMERALS}]+节")
APPENDIX_RE = re.compile(rf"附录[{CN_NUMERALS}A-Z0-9]+")
CLAUSE_RE = re.compile(r"(?:第)?([1-9]\d*(?:\.[0-9]+){1,2})条")
TABLE_RE = re.compile(r"(?:附)?表([0-9]+(?:\.[0-9]+){1,2}(?:[—－-][0-9]+)?)")
FIGURE_RE = re.compile(r"(?:附)?图([0-9]+(?:\.[0-9]+){1,2}(?:[—－-][0-9]+)?)")


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def original_bytes(value: Any) -> bytes | None:
    raw = getattr(value, "original_bytes", None)
    if raw is not None:
        return bytes(raw)
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    return None


def iter_text_operands(content: ContentStream) -> Iterable[tuple[int, str, int, bytes]]:
    """Yield operator order, operator name, item order, and original bytes."""
    for operation_index, (operands, operator) in enumerate(content.operations):
        if operator == b"Tj":
            raw = original_bytes(operands[0])
            if raw is not None:
                yield operation_index, "Tj", 0, raw
        elif operator == b"TJ":
            for item_index, item in enumerate(operands[0]):
                raw = original_bytes(item)
                if raw is not None:
                    yield operation_index, "TJ", item_index, raw


def decode_segment(raw: bytes, encoding: str) -> tuple[str, str]:
    try:
        return raw.decode(encoding), "strict"
    except UnicodeDecodeError:
        return raw.decode(encoding, errors="replace"), "replacement"


def image_xobject_count(page: Any) -> int:
    try:
        resources = page.get("/Resources")
        if resources is None:
            return 0
        resources = resources.get_object()
        xobjects = resources.get("/XObject")
        if xobjects is None:
            return 0
        xobjects = xobjects.get_object()
        return sum(
            1
            for reference in xobjects.values()
            if reference.get_object().get("/Subtype") == "/Image"
        )
    except Exception:
        return 0


def compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def cjk_count(text: str) -> int:
    return sum("\u3400" <= character <= "\u9fff" for character in text)


def occurrences(pattern: re.Pattern[str], page_records: list[dict[str, Any]], span: int) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    seen: set[tuple[int, str, int]] = set()
    for page in page_records:
        text = page["search_text"]
        for match in pattern.finditer(text):
            key = (page["page_1based"], match.group(0), match.start())
            if key in seen:
                continue
            seen.add(key)
            found.append(
                {
                    "page_1based": page["page_1based"],
                    "match": match.group(0),
                    "snippet": text[max(0, match.start() - 8) : match.start() + span],
                }
            )
    return found


def labelled_occurrences(pattern: re.Pattern[str], page_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, set[int]] = defaultdict(set)
    for page in page_records:
        for match in pattern.finditer(page["search_text"]):
            grouped[match.group(1)].add(page["page_1based"])
    return [
        {"label": label, "pages": sorted(pages)}
        for label, pages in sorted(grouped.items(), key=lambda item: item[0])
    ]


def clause_audit(page_records: list[dict[str, Any]]) -> dict[str, Any]:
    by_prefix: dict[str, set[int]] = defaultdict(set)
    clause_pages: dict[str, set[int]] = defaultdict(set)
    for page in page_records:
        for clause_id in CLAUSE_RE.findall(page["search_text"]):
            prefix, last = clause_id.rsplit(".", 1)
            by_prefix[prefix].add(int(last))
            clause_pages[clause_id].add(page["page_1based"])

    groups: list[dict[str, Any]] = []
    for prefix in sorted(by_prefix, key=lambda item: tuple(int(part) for part in item.split("."))):
        values = sorted(by_prefix[prefix])
        missing = sorted(set(range(1, max(values) + 1)) - set(values)) if values else []
        groups.append(
            {
                "prefix": prefix,
                "count": len(values),
                "minimum": min(values) if values else None,
                "maximum": max(values) if values else None,
                "missing": missing,
            }
        )

    return {
        "unique_clause_count": len(clause_pages),
        "continuous": bool(groups) and all(not group["missing"] and group["minimum"] == 1 for group in groups),
        "groups": groups,
        "clause_pages": [
            {"clause_id": clause_id, "pages": sorted(pages)}
            for clause_id, pages in sorted(
                clause_pages.items(), key=lambda item: tuple(int(part) for part in item[0].split("."))
            )
        ],
    }


def atomic_write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    temporary.replace(path)


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True, type=Path, help="Source PDF; never modified")
    parser.add_argument("--doc-id", required=True, help="Stable registry document id")
    parser.add_argument("--output", required=True, type=Path, help="UTF-8 page JSONL output")
    parser.add_argument("--report", type=Path, help="Quality JSON; defaults beside --output")
    parser.add_argument("--encoding", default="gb18030", help="Source byte encoding (default: gb18030)")
    parser.add_argument("--expected-pages", type=int)
    parser.add_argument("--expected-clause-count", type=int)
    parser.add_argument("--expected-xobjects", type=int)
    parser.add_argument("--expected-term", action="append", default=[])
    parser.add_argument("--force", action="store_true", help="Replace only prior recovery outputs")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pdf_path = args.pdf.resolve()
    output_path = args.output.resolve()
    report_path = (args.report or args.output.with_suffix(".quality.json")).resolve()

    if not pdf_path.is_file():
        raise SystemExit(f"Source PDF not found: {pdf_path}")
    if pdf_path in {output_path, report_path}:
        raise SystemExit("Recovery outputs must not overwrite the source PDF")
    for path in (output_path, report_path):
        if path.exists() and not args.force:
            raise SystemExit(f"Output exists; use --force only for recovery outputs: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)

    logging.getLogger("pypdf").setLevel(logging.ERROR)
    reader = PdfReader(str(pdf_path), strict=False)
    source_hash = sha256_path(pdf_path)
    created_utc = datetime.now(timezone.utc).isoformat()
    pages: list[dict[str, Any]] = []

    for page_index, page in enumerate(reader.pages):
        content = ContentStream(page.get_contents(), reader)
        segments: list[dict[str, Any]] = []
        ordered_text: list[str] = []
        replacement_segments = 0
        for sequence, (operation_index, operator, item_index, raw) in enumerate(iter_text_operands(content), 1):
            decoded, status = decode_segment(raw, args.encoding)
            replacement_segments += int(status != "strict")
            ordered_text.append(decoded)
            segments.append(
                {
                    "sequence": sequence,
                    "operation_index": operation_index,
                    "operator": operator,
                    "item_index": item_index,
                    "raw_hex": raw.hex().upper(),
                    "decoded_text": decoded,
                    "decode_status": status,
                }
            )

        text = "".join(ordered_text)
        search_text = compact(text)
        mediabox = page.mediabox
        pages.append(
            {
                "schema": SCHEMA,
                "doc_id": args.doc_id,
                "source_pdf": str(pdf_path),
                "source_pdf_sha256": source_hash,
                "page_1based": page_index + 1,
                "width_pt": round(float(mediabox.width), 6),
                "height_pt": round(float(mediabox.height), 6),
                "pdf_rotation": int(page.get("/Rotate", 0) or 0),
                "method": f"pypdf_content_stream_original_bytes_{args.encoding}",
                "segment_count": len(segments),
                "replacement_segment_count": replacement_segments,
                "character_count": len(text),
                "cjk_character_count": cjk_count(text),
                "image_xobject_count": image_xobject_count(page),
                "text_in_operation_order": text,
                "search_text": search_text,
                "segments": segments,
            }
        )

    all_text = "".join(page["text_in_operation_order"] for page in pages)
    all_search_text = "".join(page["search_text"] for page in pages)
    clause_result = clause_audit(pages)
    total_xobjects = sum(page["image_xobject_count"] for page in pages)
    expected_terms = [
        {"term": term, "found": term in all_search_text}
        for term in args.expected_term
    ]
    expectation_checks = {
        "page_count": {
            "expected": args.expected_pages,
            "observed": len(pages),
            "pass": args.expected_pages is None or args.expected_pages == len(pages),
        },
        "clause_count": {
            "expected": args.expected_clause_count,
            "observed": clause_result["unique_clause_count"],
            "pass": args.expected_clause_count is None
            or args.expected_clause_count == clause_result["unique_clause_count"],
        },
        "image_xobjects": {
            "expected": args.expected_xobjects,
            "observed": total_xobjects,
            "pass": args.expected_xobjects is None or args.expected_xobjects == total_xobjects,
        },
        "terms": expected_terms,
    }
    checks_pass = (
        expectation_checks["page_count"]["pass"]
        and expectation_checks["clause_count"]["pass"]
        and expectation_checks["image_xobjects"]["pass"]
        and all(item["found"] for item in expected_terms)
        and clause_result["continuous"]
    )

    report = {
        "schema": REPORT_SCHEMA,
        "created_utc": created_utc,
        "doc_id": args.doc_id,
        "source_pdf": str(pdf_path),
        "source_pdf_sha256": source_hash,
        "encoding": args.encoding,
        "status": "RECOVERED_WITH_LAYOUT_LIMITS" if checks_pass else "RECOVERED_REVIEW_REQUIRED",
        "promotion_status": "QUARANTINED_FROM_CANONICAL_PACKAGE",
        "page_count": len(pages),
        "covered_pages": len(pages),
        "total_segments": sum(page["segment_count"] for page in pages),
        "replacement_segments": sum(page["replacement_segment_count"] for page in pages),
        "character_count": len(all_text),
        "cjk_character_count": cjk_count(all_text),
        "cjk_ratio": round(cjk_count(all_text) / max(1, len(compact(all_text))), 6),
        "image_xobject_count": total_xobjects,
        "image_xobjects_by_page": [
            {"page_1based": page["page_1based"], "count": page["image_xobject_count"]}
            for page in pages
            if page["image_xobject_count"]
        ],
        "chapters": occurrences(CHAPTER_RE, pages, 28),
        "sections": occurrences(SECTION_RE, pages, 24),
        "appendices": occurrences(APPENDIX_RE, pages, 34),
        "clauses": clause_result,
        "table_labels": labelled_occurrences(TABLE_RE, pages),
        "figure_labels": labelled_occurrences(FIGURE_RE, pages),
        "expectation_checks": expectation_checks,
        "coordinate_boundary": {
            "status": "UNRESOLVED",
            "reason": "Tj/TJ operation order and physical page are preserved, but this recovery does not yet map each decoded byte string back to glyph-level PDF bboxes or table cells.",
            "allowed_use": "full-text retrieval, chapter/section/clause routing, caption discovery, and re-extraction planning",
            "forbidden_use": "automatic numeric reuse or clause quotation without source-page/bbox visual confirmation",
        },
    }

    atomic_write_jsonl(output_path, pages)
    atomic_write_json(report_path, report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "doc_id": args.doc_id,
                "source_pdf_sha256": source_hash,
                "pages": len(pages),
                "segments": report["total_segments"],
                "characters": report["character_count"],
                "cjk_ratio": report["cjk_ratio"],
                "unique_clauses": clause_result["unique_clause_count"],
                "clause_continuity": clause_result["continuous"],
                "image_xobjects": total_xobjects,
                "output": str(output_path),
                "report": str(report_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if checks_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
