#!/usr/bin/env python3
"""Create document/page inventory and native-text quality metrics for standards PDFs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import fitz


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest().upper()


def read_registry(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    ids = [row["doc_id"] for row in rows]
    rels = [row["relative_path"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate doc_id in registry")
    if len(rels) != len(set(rels)):
        raise ValueError("duplicate relative_path in registry")
    return rows


def union_area(rects: list[fitz.Rect]) -> float:
    if not rects:
        return 0.0
    events: list[tuple[float, int, float, float]] = []
    for rect in rects:
        if rect.width <= 0 or rect.height <= 0:
            continue
        events.append((rect.x0, 1, rect.y0, rect.y1))
        events.append((rect.x1, -1, rect.y0, rect.y1))
    events.sort()
    active: list[tuple[float, float]] = []
    previous_x: float | None = None
    area = 0.0
    for x, event_type, y0, y1 in events:
        if previous_x is not None and x > previous_x and active:
            merged = 0.0
            for start, end in sorted(active):
                if end <= start:
                    continue
                if merged == 0.0:
                    current_start, current_end = start, end
                    merged = -1.0
                elif start > current_end:
                    merged = (0.0 if merged < 0 else merged) + current_end - current_start
                    current_start, current_end = start, end
                else:
                    current_end = max(current_end, end)
            if merged < 0:
                covered_y = current_end - current_start
            else:
                covered_y = merged + current_end - current_start
            area += (x - previous_x) * max(0.0, covered_y)
        if event_type == 1:
            active.append((y0, y1))
        else:
            try:
                active.remove((y0, y1))
            except ValueError:
                pass
        previous_x = x
    return area


def text_metrics(text: str, expected_language: str) -> dict[str, float | int | str]:
    compact = re.sub(r"\s+", "", text)
    char_count = len(compact)
    if char_count == 0:
        return {
            "native_char_count": 0,
            "cjk_count": 0,
            "latin_digit_count": 0,
            "replacement_count": 0,
            "private_use_count": 0,
            "printable_ratio": 0.0,
            "tokenish_ratio": 0.0,
            "native_quality_score": 0.0,
            "native_class": "empty_or_scan",
        }
    cjk = sum("\u3400" <= ch <= "\u9fff" for ch in compact)
    latin_digit = sum(ch.isascii() and ch.isalnum() for ch in compact)
    replacement = compact.count("\ufffd")
    private_use = sum("\ue000" <= ch <= "\uf8ff" for ch in compact)
    printable = sum(ch.isprintable() for ch in compact)
    tokenish = cjk + latin_digit + sum(ch in "，。；：、（）()[]+-×÷/%℃°=<>" for ch in compact)
    printable_ratio = printable / char_count
    tokenish_ratio = tokenish / char_count
    bad_ratio = (replacement + private_use) / char_count
    length_score = min(1.0, math.log1p(char_count) / math.log1p(900))
    score = max(0.0, min(1.0, 0.45 * length_score + 0.3 * printable_ratio + 0.25 * tokenish_ratio - 3 * bad_ratio))
    cjk_ratio = cjk / char_count
    suspect_font_mapping = expected_language == "zh" and char_count >= 100 and cjk_ratio < 0.012
    if suspect_font_mapping:
        score = min(score, 0.25)
    if suspect_font_mapping:
        native_class = "suspect_font_mapping"
    elif char_count >= 80 and score >= 0.72 and bad_ratio < 0.01:
        native_class = "native_text_good"
    elif char_count >= 25 and score >= 0.48 and bad_ratio < 0.05:
        native_class = "native_text_weak"
    elif bad_ratio >= 0.05:
        native_class = "garbled_text"
    else:
        native_class = "empty_or_scan"
    return {
        "native_char_count": char_count,
        "cjk_count": cjk,
        "latin_digit_count": latin_digit,
        "replacement_count": replacement,
        "private_use_count": private_use,
        "printable_ratio": round(printable_ratio, 6),
        "tokenish_ratio": round(tokenish_ratio, 6),
        "cjk_ratio": round(cjk_ratio, 6),
        "suspect_font_mapping": suspect_font_mapping,
        "native_quality_score": round(score, 6),
        "native_class": native_class,
    }


def page_metrics(page: fitz.Page, doc_id: str, page_index: int, expected_language: str) -> dict:
    page_dict = page.get_text("dict", sort=True)
    text_blocks = [block for block in page_dict.get("blocks", []) if block.get("type") == 0]
    text = "\n".join(
        "".join(span.get("text", "") for line in block.get("lines", []) for span in line.get("spans", []))
        for block in text_blocks
    )
    metrics = text_metrics(text, expected_language)
    rects = [fitz.Rect(block["bbox"]) for block in text_blocks if "bbox" in block]
    page_area = max(1.0, page.rect.width * page.rect.height)
    image_count = len(page.get_images(full=True))
    try:
        drawing_count = len(page.get_drawings())
    except Exception:
        drawing_count = -1
    metrics.update(
        {
            "page_id": f"{doc_id}:p{page_index + 1:04d}",
            "doc_id": doc_id,
            "page_1based": page_index + 1,
            "width_pt": round(page.rect.width, 3),
            "height_pt": round(page.rect.height, 3),
            "rotation": page.rotation,
            "text_block_count": len(text_blocks),
            "text_area_ratio": round(min(1.0, union_area(rects) / page_area), 6),
            "image_count": image_count,
            "drawing_count": drawing_count,
            "has_table_caption": bool(re.search(r"(^|\n)\s*表\s*[A-Za-z0-9一二三四五六七八九十.-]+", text)),
            "has_figure_caption": bool(re.search(r"(^|\n)\s*图\s*[A-Za-z0-9一二三四五六七八九十.-]+", text)),
            "needs_ocr": metrics["native_class"] in {"empty_or_scan", "garbled_text", "suspect_font_mapping"},
        }
    )
    return metrics


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if fields:
            writer.writeheader()
            writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    source_root = args.source_root.resolve()
    registry = read_registry(args.registry.resolve())
    out_dir = args.out_dir.resolve()
    documents: list[dict] = []
    pages: list[dict] = []
    for row in registry:
        path = source_root / Path(row["relative_path"])
        if not path.is_file():
            raise FileNotFoundError(path)
        doc_hash = sha256_path(path)
        with fitz.open(path) as doc:
            doc_pages = [page_metrics(doc[index], row["doc_id"], index, row["language"]) for index in range(doc.page_count)]
            pages.extend(doc_pages)
            classes = Counter(page["native_class"] for page in doc_pages)
            documents.append(
                {
                    "doc_id": row["doc_id"],
                    "relative_path": row["relative_path"],
                    "family": row["family"],
                    "source_kind": row["source_kind"],
                    "evidence_default": row["evidence_default"],
                    "duplicate_of": row["duplicate_of"],
                    "language": row["language"],
                    "priority": row["priority"],
                    "size_bytes": path.stat().st_size,
                    "sha256": doc_hash,
                    "page_count": doc.page_count,
                    "native_good_pages": classes["native_text_good"],
                    "native_weak_pages": classes["native_text_weak"],
                    "suspect_font_mapping_pages": classes["suspect_font_mapping"],
                    "empty_or_scan_pages": classes["empty_or_scan"],
                    "garbled_pages": classes["garbled_text"],
                    "needs_ocr_pages": sum(page["needs_ocr"] for page in doc_pages),
                    "table_caption_pages": sum(page["has_table_caption"] for page in doc_pages),
                    "figure_caption_pages": sum(page["has_figure_caption"] for page in doc_pages),
                    "pdf_title": (doc.metadata or {}).get("title", ""),
                    "pdf_author": (doc.metadata or {}).get("author", ""),
                }
            )
        print(f"{row['doc_id']}: {documents[-1]['page_count']} pages, OCR candidates {documents[-1]['needs_ocr_pages']}")

    write_csv(out_dir / "documents.csv", documents)
    write_csv(out_dir / "pages.csv", pages)
    summary = {
        "schema": "design-standards-inventory-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "document_count": len(documents),
        "unique_content_hashes": len({row["sha256"] for row in documents}),
        "page_count": len(pages),
        "native_good_pages": sum(row["native_good_pages"] for row in documents),
        "native_weak_pages": sum(row["native_weak_pages"] for row in documents),
        "suspect_font_mapping_pages": sum(row["suspect_font_mapping_pages"] for row in documents),
        "empty_or_scan_pages": sum(row["empty_or_scan_pages"] for row in documents),
        "garbled_pages": sum(row["garbled_pages"] for row in documents),
        "needs_ocr_pages": sum(row["needs_ocr_pages"] for row in documents),
        "table_caption_pages": sum(row["table_caption_pages"] for row in documents),
        "figure_caption_pages": sum(row["figure_caption_pages"] for row in documents),
    }
    (out_dir / "inventory_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
