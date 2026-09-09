# -*- coding: utf-8 -*-
"""Build a recoverable page-level OCR/RAG layer for supplied textbooks.

The original PDFs remain immutable external sources. OCR text is candidate
retrieval evidence, not a verified transcription of numbers, equations, tables,
or figures.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import io
import json
import os
import re
import statistics
import subprocess
import sys
import threading
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import fitz
import pytesseract
from PIL import Image, ImageOps
from pytesseract import Output


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "source_registry.json"
SOURCE_PAGES = ROOT / "source_pages"
EXTRACTION = ROOT / "extraction"
PAGE_MANIFEST = EXTRACTION / "page_manifest.jsonl"
BUILD_REPORT = EXTRACTION / "build_report.json"
HEADING_CANDIDATES = EXTRACTION / "heading_candidates.jsonl"
CAPTION_CANDIDATES = EXTRACTION / "caption_candidates.jsonl"

OCR_LANGUAGE = "chi_sim+eng"
OCR_CONFIG = "--oem 1 --psm 3 -c preserve_interword_spaces=1"
OCR_SCHEMA = "chemical-principles-page-ocr-v1"
LOW_CONFIDENCE_THRESHOLD = 65.0
LOW_TOKEN_CONFIDENCE = 45.0
MIN_TEXT_CHARS = 80

_THREAD_LOCAL = threading.local()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(text, encoding="utf-8", newline="\n")
    temp.replace(path)


def atomic_write_json(path: Path, payload: Any) -> None:
    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def load_registry() -> dict[str, Any]:
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if data.get("schema") != "chemical-principles-source-registry-v1":
        raise RuntimeError("unsupported source registry schema")
    return data


def parse_pages(value: str | None, total: int) -> list[int]:
    if not value:
        return list(range(total))
    pages: set[int] = set()
    for part in value.split(","):
        token = part.strip()
        if not token:
            continue
        if "-" in token:
            left, right = token.split("-", 1)
            start, end = int(left), int(right)
            if end < start:
                start, end = end, start
            pages.update(range(start - 1, end))
        else:
            pages.add(int(token) - 1)
    invalid = sorted(page + 1 for page in pages if page < 0 or page >= total)
    if invalid:
        raise ValueError(f"page selection outside 1..{total}: {invalid}")
    return sorted(pages)


def verify_source(source: dict[str, Any]) -> dict[str, Any]:
    path = Path(source["path"])
    if not path.is_file():
        raise FileNotFoundError(path)
    actual_hash = sha256_file(path)
    if actual_hash != source["sha256"].upper():
        raise RuntimeError(
            f"source hash mismatch for {source['source_id']}: "
            f"expected {source['sha256']} actual {actual_hash}"
        )
    with fitz.open(path) as document:
        pages = len(document)
        metadata = document.metadata
    if pages != int(source["expected_pages"]):
        raise RuntimeError(
            f"page-count mismatch for {source['source_id']}: "
            f"expected {source['expected_pages']} actual {pages}"
        )
    return {
        "path": str(path),
        "sha256": actual_hash,
        "pages": pages,
        "pdf_metadata": metadata,
    }


def ocr_signature() -> str:
    payload = {
        "schema": OCR_SCHEMA,
        "language": OCR_LANGUAGE,
        "config": OCR_CONFIG,
        "tesseract": str(pytesseract.get_tesseract_version()).splitlines()[0],
        "pytesseract": getattr(pytesseract, "__version__", "unknown"),
        "pymupdf": getattr(fitz, "__version__", "unknown"),
        "pillow": getattr(Image, "__version__", "unknown"),
    }
    return sha256_text(json.dumps(payload, sort_keys=True))


def get_document(path: str) -> fitz.Document:
    cache = getattr(_THREAD_LOCAL, "documents", None)
    if cache is None:
        cache = {}
        _THREAD_LOCAL.documents = cache
    document = cache.get(path)
    if document is None or document.is_closed:
        document = fitz.open(path)
        cache[path] = document
    return document


def page_image(document: fitz.Document, page_index: int) -> tuple[Image.Image, dict[str, Any]]:
    page = document[page_index]
    images = page.get_images(full=True)
    chosen: dict[str, Any] = {}
    if images:
        ranked = sorted(images, key=lambda row: int(row[2]) * int(row[3]), reverse=True)
        xref, _, width, height, bpc, colorspace = ranked[0][:6]
        if int(width) >= 1000 and int(height) >= 1000:
            extracted = document.extract_image(int(xref))
            image = Image.open(io.BytesIO(extracted["image"]))
            chosen = {
                "method": "embedded_page_image",
                "xref": int(xref),
                "width": int(width),
                "height": int(height),
                "bpc": int(bpc),
                "colorspace": str(colorspace),
                "extension": extracted.get("ext", ""),
            }
            return image.convert("L"), chosen

    pixmap = page.get_pixmap(dpi=300, colorspace=fitz.csGRAY, alpha=False)
    image = Image.frombytes("L", (pixmap.width, pixmap.height), pixmap.samples)
    chosen = {
        "method": "render_300dpi",
        "width": pixmap.width,
        "height": pixmap.height,
        "bpc": 8,
        "colorspace": "DeviceGray",
        "extension": "render",
    }
    return image, chosen


def reconstruct_text(data: dict[str, list[Any]]) -> tuple[str, list[float], int]:
    lines: dict[tuple[int, int, int], list[tuple[int, str]]] = defaultdict(list)
    confidences: list[float] = []
    low_count = 0
    length = len(data.get("text", []))
    for index in range(length):
        text = str(data["text"][index]).strip()
        if not text:
            continue
        try:
            confidence = float(data["conf"][index])
        except (TypeError, ValueError):
            confidence = -1.0
        if confidence >= 0:
            confidences.append(confidence)
            if confidence < LOW_TOKEN_CONFIDENCE:
                low_count += 1
        key = (
            int(data["block_num"][index]),
            int(data["par_num"][index]),
            int(data["line_num"][index]),
        )
        lines[key].append((int(data["word_num"][index]), text))

    ordered: list[str] = []
    previous_block_par: tuple[int, int] | None = None
    for key in sorted(lines):
        block_par = key[:2]
        if previous_block_par is not None and block_par != previous_block_par:
            ordered.append("")
        words = [text for _, text in sorted(lines[key])]
        line = " ".join(words)
        line = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", line)
        ordered.append(line.rstrip())
        previous_block_par = block_par
    text = "\n".join(ordered).strip()
    return text, confidences, low_count


def existing_page_valid(meta_path: Path, source_hash: str, signature: str) -> bool:
    if not meta_path.is_file():
        return False
    try:
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return (
        metadata.get("source_sha256") == source_hash
        and metadata.get("ocr_signature") == signature
        and metadata.get("schema") == OCR_SCHEMA
    )


def process_page(job: dict[str, Any]) -> dict[str, Any]:
    source = job["source"]
    page_index = int(job["page_index"])
    output_dir = SOURCE_PAGES / source["volume"]
    text_path = output_dir / f"page_{page_index + 1:04d}.txt"
    meta_path = output_dir / f"page_{page_index + 1:04d}.json"
    signature = job["ocr_signature"]

    if not job["force"] and text_path.is_file() and existing_page_valid(
        meta_path, source["sha256"].upper(), signature
    ):
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        metadata["knowledge_layer"] = "L0_source_detail"
        existing_text = text_path.read_text(encoding="utf-8")
        if "knowledge_layer: L0_source_detail\n" not in existing_text:
            marker = f"evidence_status: {metadata.get('status', 'ocr_candidate')}\n"
            if marker in existing_text:
                existing_text = existing_text.replace(
                    marker,
                    marker + "knowledge_layer: L0_source_detail\n",
                    1,
                )
                atomic_write_text(text_path, existing_text)
                metadata["text_sha256"] = sha256_text(existing_text)
                atomic_write_json(meta_path, metadata)
        metadata["build_action"] = "reused"
        return metadata

    document = get_document(source["path"])
    page = document[page_index]
    image, image_metadata = page_image(document, page_index)
    image = ImageOps.autocontrast(image)

    os.environ.setdefault("OMP_THREAD_LIMIT", "1")
    data = pytesseract.image_to_data(
        image,
        lang=OCR_LANGUAGE,
        config=OCR_CONFIG,
        output_type=Output.DICT,
        timeout=180,
    )
    text, confidences, low_count = reconstruct_text(data)
    text_layer = page.get_text("text").strip()
    extraction_method = "tesseract_ocr"
    if len(text) < 20 and len(text_layer) > len(text):
        text = text_layer
        extraction_method = "pdf_text_layer_fallback"

    mean_conf = round(statistics.fmean(confidences), 2) if confidences else None
    median_conf = round(statistics.median(confidences), 2) if confidences else None
    low_ratio = round(low_count / len(confidences), 4) if confidences else None
    if len(text) < 20:
        status = "blank_or_nontext_page"
    elif len(text) < MIN_TEXT_CHARS or (mean_conf is not None and mean_conf < LOW_CONFIDENCE_THRESHOLD):
        status = "ocr_low_confidence"
    else:
        status = "ocr_candidate"

    header = "\n".join(
        [
            f"source_id: {source['source_id']}",
            f"volume: {source['volume']}",
            f"pdf_page: {page_index + 1}",
            f"source_sha256: {source['sha256'].upper()}",
            f"evidence_status: {status}",
            "knowledge_layer: L0_source_detail",
            "numeric_formula_notice: OCR numbers, equations, tables, and figure labels require visual verification.",
            "",
        ]
    )
    page_text = header + text.strip() + "\n"
    metadata = {
        "schema": OCR_SCHEMA,
        "source_id": source["source_id"],
        "volume": source["volume"],
        "pdf_page": page_index + 1,
        "source_path": source["path"],
        "source_sha256": source["sha256"].upper(),
        "ocr_signature": signature,
        "ocr_language": OCR_LANGUAGE,
        "ocr_config": OCR_CONFIG,
        "extraction_method": extraction_method,
        "image": image_metadata,
        "text_chars": len(text),
        "text_tokens": len([token for token in re.split(r"\s+", text) if token]),
        "mean_confidence": mean_conf,
        "median_confidence": median_conf,
        "low_confidence_ratio": low_ratio,
        "status": status,
        "knowledge_layer": "L0_source_detail",
        "text_sha256": sha256_text(page_text),
        "text_path": str(text_path.relative_to(ROOT)).replace("\\", "/"),
        "build_action": "generated",
    }
    atomic_write_text(text_path, page_text)
    atomic_write_json(meta_path, metadata)
    return metadata


HEADING_PATTERNS = [
    re.compile(r"第\s*[一二三四五六七八九十百0-9]+\s*章[^\n]{0,80}"),
    re.compile(r"^\s*\d{1,2}(?:\.\d{1,2}){0,3}\s+[^\n]{2,80}$", re.MULTILINE),
]
CAPTION_PATTERN = re.compile(
    r"^\s*(图|表)\s*\d{1,2}(?:\s*[-－—.]\s*\d{1,3})+(?:\s+|　*)[^\n]{0,100}$",
    re.MULTILINE,
)


def candidate_records(manifest: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    headings: list[dict[str, Any]] = []
    captions: list[dict[str, Any]] = []
    for page in manifest:
        text_path = ROOT / page["text_path"]
        text = text_path.read_text(encoding="utf-8")
        body = text.split("\n\n", 1)[-1]
        seen_headings: set[str] = set()
        for pattern in HEADING_PATTERNS:
            for match in pattern.finditer(body):
                value = re.sub(r"\s+", " ", match.group(0)).strip()
                if value and value not in seen_headings:
                    headings.append(
                        {
                            "source_id": page["source_id"],
                            "volume": page["volume"],
                            "pdf_page": page["pdf_page"],
                            "raw_heading": value,
                            "status": "ocr_candidate",
                            "source_text_path": page["text_path"],
                        }
                    )
                    seen_headings.add(value)
        for match in CAPTION_PATTERN.finditer(body):
            value = re.sub(r"\s+", " ", match.group(0)).strip()
            captions.append(
                {
                    "source_id": page["source_id"],
                    "volume": page["volume"],
                    "pdf_page": page["pdf_page"],
                    "kind": "figure" if match.group(1) == "图" else "table",
                    "raw_caption": value,
                    "status": "ocr_candidate_requires_visual_verification",
                    "source_text_path": page["text_path"],
                }
            )
    return headings, captions


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    text = "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows)
    atomic_write_text(path, text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=["all", "upper", "lower"], default="all")
    parser.add_argument("--pages", help="1-based page list/ranges, e.g. 1-20,35")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    registry = load_registry()
    selected = [
        source
        for source in registry["sources"]
        if args.source == "all" or source["volume"] == args.source
    ]
    if not selected:
        raise RuntimeError("no sources selected")

    signature = ocr_signature()
    verification = {source["source_id"]: verify_source(source) for source in selected}
    jobs: list[dict[str, Any]] = []
    full_run = args.pages is None
    for source in selected:
        pages = parse_pages(args.pages, int(source["expected_pages"]))
        for page_index in pages:
            jobs.append(
                {
                    "source": source,
                    "page_index": page_index,
                    "ocr_signature": signature,
                    "force": args.force,
                }
            )

    print(
        f"OCR_START sources={len(selected)} pages={len(jobs)} "
        f"workers={args.workers} signature={signature[:12]}"
    )
    results: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(process_page, job): job for job in jobs}
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            completed += 1
            if completed % 20 == 0 or completed == len(jobs):
                print(f"OCR_PROGRESS {completed}/{len(jobs)}")

    results.sort(key=lambda row: (row["volume"], int(row["pdf_page"])))
    if full_run and args.source == "all":
        expected_total = sum(int(source["expected_pages"]) for source in selected)
        if len(results) != expected_total:
            raise RuntimeError(f"coverage mismatch expected={expected_total} actual={len(results)}")

    write_jsonl(PAGE_MANIFEST, results)
    headings, captions = candidate_records(results)
    write_jsonl(HEADING_CANDIDATES, headings)
    write_jsonl(CAPTION_CANDIDATES, captions)

    status_counts = Counter(row["status"] for row in results)
    action_counts = Counter(row["build_action"] for row in results)
    confidence_values = [
        float(row["mean_confidence"])
        for row in results
        if row.get("mean_confidence") is not None
    ]
    report = {
        "schema": "chemical-principles-ocr-build-report-v1",
        "registry": str(REGISTRY_PATH.relative_to(ROOT)).replace("\\", "/"),
        "source_verification": verification,
        "ocr_signature": signature,
        "ocr_language": OCR_LANGUAGE,
        "ocr_config": OCR_CONFIG,
        "selected_source": args.source,
        "selected_pages": args.pages or "all",
        "full_run": full_run,
        "page_records": len(results),
        "status_counts": dict(status_counts),
        "action_counts": dict(action_counts),
        "mean_of_page_mean_confidence": (
            round(statistics.fmean(confidence_values), 2) if confidence_values else None
        ),
        "heading_candidates": len(headings),
        "caption_candidates": len(captions),
        "numeric_formula_policy": "ocr_candidate_requires_visual_verification",
        "complete_for_selected_scope": len(results) == len(jobs),
    }
    atomic_write_json(BUILD_REPORT, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
