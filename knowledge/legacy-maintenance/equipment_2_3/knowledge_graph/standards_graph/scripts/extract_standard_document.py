#!/usr/bin/env python3
"""Extract one standards PDF into a provenance-rich, searchable source package.

One invocation processes exactly one ``doc_id``.  This makes it safe to assign
one PDF to one subagent while the main agent later builds the global index.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import cv2
import fitz
import numpy as np
import pdfplumber
import pytesseract
from PIL import Image
from pytesseract import Output


HEADING_PATTERNS = [
    re.compile(r"^第[一二三四五六七八九十百0-9]+[章节篇部]\s*"),
    re.compile(r"^(?:附录|附件)\s*[A-ZＡ-Ｚ一二三四五六七八九十0-9]+", re.I),
    re.compile(r"^\d+(?:\.\d+){0,5}(?:\s+|　+)[^\d].{0,100}$"),
    re.compile(r"^(?:chapter|part|appendix)\s+[A-Z0-9IVX]+", re.I),
]
TABLE_CAPTION_RE = re.compile(r"^\s*表\s*[A-Za-z0-9一二三四五六七八九十.-]+\s*.*", re.MULTILINE)
FIGURE_CAPTION_RE = re.compile(r"^\s*图\s*[A-Za-z0-9一二三四五六七八九十.-]+\s*.*", re.MULTILINE)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest().upper()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def normalize_space(text: str) -> str:
    text = text.replace("\x00", " ").replace("\u00a0", " ")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return text.strip()


def search_normalize(text: str) -> str:
    """Remove OCR-inserted spaces inside Chinese words while preserving raw evidence elsewhere."""
    previous = None
    text = text.replace("　", " ")
    while text != previous:
        previous = text
        text = re.sub(r"(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])", "", text)
    text = re.sub(r"第\s*([一二三四五六七八九十百0-9]+)\s*([章节篇部])", r"第\1\2", text)
    text = re.sub(r"([表图])\s*([A-Za-z0-9一二三四五六七八九十]+)\s*([.\-－—])\s*([0-9]+)", r"\1\2\3\4", text)
    return normalize_space(text)


def caption_matches(pattern: re.Pattern, text: str) -> bool:
    return bool(pattern.match(search_normalize(text)))


def valid_text_score(text: str, expected_language: str = "") -> float:
    compact = re.sub(r"\s+", "", text)
    if not compact:
        return 0.0
    cjk = sum("\u3400" <= ch <= "\u9fff" for ch in compact)
    latin = sum(ch.isascii() and ch.isalnum() for ch in compact)
    common = sum(ch in "，。；：、（）()[]+-×÷/%℃°=<>.,:;" for ch in compact)
    bad = compact.count("\ufffd") + sum("\ue000" <= ch <= "\uf8ff" for ch in compact)
    length = min(1.0, math.log1p(len(compact)) / math.log1p(900))
    token_ratio = min(1.0, (cjk + latin + common) / len(compact))
    score = max(0.0, min(1.0, 0.55 * length + 0.45 * token_ratio - 4 * bad / len(compact)))
    if expected_language == "zh" and len(compact) >= 100 and cjk / len(compact) < 0.012:
        score = min(score, 0.25)
    return round(score, 6)


def native_mapping_suspect(text: str, expected_language: str) -> bool:
    """Detect unusable embedded-font text before comparing it with OCR."""
    compact = re.sub(r"\s+", "", text)
    if not compact:
        return True
    bad = compact.count("\ufffd") + sum("\ue000" <= ch <= "\uf8ff" for ch in compact)
    if bad / len(compact) >= 0.03:
        return True
    if expected_language == "zh" and len(compact) >= 80:
        cjk = sum("\u3400" <= ch <= "\u9fff" for ch in compact)
        if cjk / len(compact) < 0.012:
            return True
    return False


def native_lines(page: fitz.Page) -> tuple[list[dict], list[dict]]:
    data = page.get_text("dict", sort=True)
    lines: list[dict] = []
    image_blocks: list[dict] = []
    order = 0
    for block in data.get("blocks", []):
        if block.get("type") == 1 and "bbox" in block:
            image_blocks.append({"bbox_pt": [round(float(v), 3) for v in block["bbox"]]})
            continue
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            text = normalize_space("".join(span.get("text", "") for span in spans))
            if not text:
                continue
            bbox = line.get("bbox") or block.get("bbox")
            lines.append(
                {
                    "order": order,
                    "text": text,
                    "bbox_pt": [round(float(v), 3) for v in bbox],
                    "font_size": round(max((float(span.get("size", 0)) for span in spans), default=0.0), 3),
                    "method": "native_text",
                    "confidence": 1.0,
                }
            )
            order += 1
    return lines, image_blocks


def render_page(page: fitz.Page, dpi: int) -> tuple[Image.Image, np.ndarray, float]:
    scale = dpi / 72.0
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), colorspace=fitz.csRGB, alpha=False)
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    array = np.asarray(image)
    return image, array, scale


def detect_rotation(image: Image.Image) -> tuple[int, float]:
    try:
        result = pytesseract.image_to_osd(image, output_type=Output.DICT)
        rotation = int(result.get("rotate", 0)) % 360
        confidence = float(result.get("orientation_conf", 0.0))
        if rotation not in {0, 90, 180, 270}:
            return 0, confidence
        return rotation, confidence
    except Exception:
        return 0, 0.0


def rotate_for_ocr(image: Image.Image, rotation: int) -> Image.Image:
    if rotation == 0:
        return image
    return image.rotate(-rotation, expand=True, fillcolor="white")


def work_bbox_to_original(bbox: list[float], rotation: int, original_width: int, original_height: int) -> list[float]:
    x0, y0, x1, y1 = bbox
    points = [(x0, y0), (x1, y0), (x0, y1), (x1, y1)]
    converted = []
    for x, y in points:
        if rotation == 90:
            converted.append((y, original_height - x))
        elif rotation == 180:
            converted.append((original_width - x, original_height - y))
        elif rotation == 270:
            converted.append((original_width - y, x))
        else:
            converted.append((x, y))
    xs = [point[0] for point in converted]
    ys = [point[1] for point in converted]
    return [min(xs), min(ys), max(xs), max(ys)]


def ocr_page(
    image: Image.Image,
    scale: float,
    language: str,
    rotation: int,
    original_size: tuple[int, int],
) -> tuple[list[dict], list[dict], float]:
    data = pytesseract.image_to_data(
        image,
        lang=language,
        config="--oem 1 --psm 3 -c preserve_interword_spaces=1",
        output_type=Output.DICT,
    )
    grouped: dict[tuple[int, int, int], list[dict]] = defaultdict(list)
    words: list[dict] = []
    confidences: list[float] = []
    count = len(data.get("text", []))
    for i in range(count):
        text = normalize_space(str(data["text"][i]))
        if not text:
            continue
        try:
            confidence = float(data["conf"][i])
        except (TypeError, ValueError):
            confidence = -1.0
        left, top = int(data["left"][i]), int(data["top"][i])
        width, height = int(data["width"][i]), int(data["height"][i])
        bbox_work = [left, top, left + width, top + height]
        bbox_original = work_bbox_to_original(bbox_work, rotation, original_size[0], original_size[1])
        word = {
            "text": text,
            "confidence": confidence,
            "bbox_px": bbox_work,
            "bbox_pt": [round(value / scale, 3) for value in bbox_original],
        }
        words.append(word)
        if confidence >= 0:
            confidences.append(confidence)
        key = (int(data["block_num"][i]), int(data["par_num"][i]), int(data["line_num"][i]))
        grouped[key].append(word)
    lines: list[dict] = []
    for order, (_, line_words) in enumerate(sorted(grouped.items(), key=lambda item: (min(word["bbox_px"][1] for word in item[1]), min(word["bbox_px"][0] for word in item[1])))):
        line_words.sort(key=lambda word: word["bbox_px"][0])
        x0 = min(word["bbox_pt"][0] for word in line_words)
        y0 = min(word["bbox_pt"][1] for word in line_words)
        x1 = max(word["bbox_pt"][2] for word in line_words)
        y1 = max(word["bbox_pt"][3] for word in line_words)
        confs = [word["confidence"] for word in line_words if word["confidence"] >= 0]
        lines.append(
            {
                "order": order,
                "text": normalize_space(" ".join(word["text"] for word in line_words)),
                "bbox_pt": [round(x0, 3), round(y0, 3), round(x1, 3), round(y1, 3)],
                "font_size": 0.0,
                "method": "ocr_text",
                "confidence": round((sum(confs) / len(confs) / 100.0) if confs else 0.0, 6),
            }
        )
    mean_confidence = round(sum(confidences) / len(confidences), 3) if confidences else 0.0
    return lines, words, mean_confidence


def cluster_peak_positions(values: np.ndarray, threshold: float) -> list[int]:
    indices = np.where(values >= threshold)[0].tolist()
    if not indices:
        return []
    groups: list[list[int]] = [[indices[0]]]
    for index in indices[1:]:
        if index <= groups[-1][-1] + 2:
            groups[-1].append(index)
        else:
            groups.append([index])
    return [int(round(sum(group) / len(group))) for group in groups]


def words_to_grid(words: list[dict], x_edges: list[int], y_edges: list[int], offset_x: int, offset_y: int) -> list[list[str]]:
    rows: list[list[str]] = []
    for row_index in range(len(y_edges) - 1):
        cells: list[str] = []
        for col_index in range(len(x_edges) - 1):
            x0, x1 = offset_x + x_edges[col_index], offset_x + x_edges[col_index + 1]
            y0, y1 = offset_y + y_edges[row_index], offset_y + y_edges[row_index + 1]
            selected = []
            for word in words:
                wx0, wy0, wx1, wy1 = word["bbox_px"]
                center_x, center_y = (wx0 + wx1) / 2, (wy0 + wy1) / 2
                if x0 <= center_x <= x1 and y0 <= center_y <= y1:
                    selected.append(word)
            selected.sort(key=lambda word: (word["bbox_px"][1], word["bbox_px"][0]))
            cells.append(normalize_space(" ".join(word["text"] for word in selected)))
        rows.append(cells)
    return rows


def rectangularize(rows: list[list[str]], width: int | None = None) -> list[list[str]]:
    """Preserve detected table geometry, including intentionally empty rows/columns."""
    if not rows:
        return []
    width = width if width is not None else max((len(row) for row in rows), default=0)
    return [list(row[:width]) + [""] * max(0, width - len(row)) for row in rows]


def trim_table(rows: list[list[str]]) -> list[list[str]]:
    if not rows:
        return []
    width = max(len(row) for row in rows)
    padded = [row + [""] * (width - len(row)) for row in rows]
    padded = [row for row in padded if any(cell.strip() for cell in row)]
    if not padded:
        return []
    keep_cols = [index for index in range(width) if any(row[index].strip() for row in padded)]
    return [[row[index] for index in keep_cols] for row in padded]


def scan_grid_tables(
    image_array: np.ndarray,
    words: list[dict],
    scale: float,
    rotation: int,
    original_size: tuple[int, int],
) -> list[dict]:
    gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 31, 15)
    height, width = binary.shape
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(20, width // 35), 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(20, height // 45)))
    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)
    vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)
    grid = cv2.bitwise_or(horizontal, vertical)
    grid = cv2.dilate(grid, np.ones((3, 3), np.uint8), iterations=1)
    contours, _ = cv2.findContours(grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates: list[dict] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w < width * 0.22 or h < height * 0.035 or w * h < width * height * 0.012:
            continue
        if w > width * 0.98 and h > height * 0.95:
            continue
        roi_v = vertical[y : y + h, x : x + w]
        roi_h = horizontal[y : y + h, x : x + w]
        x_edges = cluster_peak_positions((roi_v > 0).sum(axis=0), max(4, h * 0.22))
        y_edges = cluster_peak_positions((roi_h > 0).sum(axis=1), max(4, w * 0.22))
        if len(x_edges) < 3 or len(y_edges) < 3:
            continue
        x_edges = sorted(set([max(0, min(w - 1, value)) for value in x_edges]))
        y_edges = sorted(set([max(0, min(h - 1, value)) for value in y_edges]))
        if x_edges[0] > w * 0.08:
            x_edges.insert(0, 0)
        if x_edges[-1] < w * 0.92:
            x_edges.append(w - 1)
        if y_edges[0] > h * 0.08:
            y_edges.insert(0, 0)
        if y_edges[-1] < h * 0.92:
            y_edges.append(h - 1)
        rows = rectangularize(words_to_grid(words, x_edges, y_edges, x, y), len(x_edges) - 1)
        if len(rows) < 2 or max((len(row) for row in rows), default=0) < 2:
            continue
        nonempty = sum(bool(cell.strip()) for row in rows for cell in row)
        if nonempty < 4:
            continue
        bbox_original = work_bbox_to_original([x, y, x + w, y + h], rotation, original_size[0], original_size[1])
        candidates.append(
            {
                "method": "ocr_grid",
                "bbox_pt": [round(value / scale, 3) for value in bbox_original],
                "rows": rows,
                "grid_row_count": len(y_edges) - 1,
                "grid_column_count": len(x_edges) - 1,
                "cell_records": [],
                "structure_confidence": round(min(1.0, 0.4 + 0.04 * len(x_edges) + 0.03 * len(y_edges)), 3),
            }
        )
    candidates.sort(key=lambda item: (item["bbox_pt"][1], item["bbox_pt"][0]))
    return candidates


def remove_table_grid(image_array: np.ndarray) -> tuple[np.ndarray | None, float]:
    """Remove long horizontal/vertical rules before a second table-focused OCR pass."""
    gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 31, 15)
    height, width = binary.shape
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(25, width // 28), 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(25, height // 34)))
    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)
    vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)
    mask = cv2.bitwise_or(horizontal, vertical)
    line_ratio = float(np.mean(mask > 0))
    if line_ratio < 0.0008:
        return None, round(line_ratio, 8)
    cleaned = image_array.copy()
    expanded = cv2.dilate(mask, np.ones((2, 2), np.uint8), iterations=1)
    cleaned[expanded > 0] = 255
    return cleaned, round(line_ratio, 8)


def bbox_iou(first: Iterable[float], second: Iterable[float]) -> float:
    ax0, ay0, ax1, ay1 = first
    bx0, by0, bx1, by1 = second
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    intersection = max(0.0, ix1 - ix0) * max(0.0, iy1 - iy0)
    if intersection <= 0:
        return 0.0
    area_a = max(0.0, ax1 - ax0) * max(0.0, ay1 - ay0)
    area_b = max(0.0, bx1 - bx0) * max(0.0, by1 - by0)
    return intersection / max(1e-9, area_a + area_b - intersection)


def bbox_containment(first: Iterable[float], second: Iterable[float]) -> float:
    ax0, ay0, ax1, ay1 = first
    bx0, by0, bx1, by1 = second
    intersection = max(0.0, min(ax1, bx1) - max(ax0, bx0)) * max(0.0, min(ay1, by1) - max(ay0, by0))
    area_a = max(0.0, ax1 - ax0) * max(0.0, ay1 - ay0)
    area_b = max(0.0, bx1 - bx0) * max(0.0, by1 - by0)
    return intersection / max(1e-9, min(area_a, area_b))


def dot_mark_confidence(image_array: np.ndarray | None, bbox_pt: tuple[float, float, float, float], scale: float) -> float:
    """Return confidence for an isolated filled circular mark inside a table cell."""
    if image_array is None:
        return 0.0
    x0, y0, x1, y1 = bbox_pt
    pad_x = max(1.0, (x1 - x0) * 0.14)
    pad_y = max(1.0, (y1 - y0) * 0.14)
    px0, py0 = int(max(0, (x0 + pad_x) * scale)), int(max(0, (y0 + pad_y) * scale))
    px1 = int(min(image_array.shape[1], (x1 - pad_x) * scale))
    py1 = int(min(image_array.shape[0], (y1 - pad_y) * scale))
    if px1 - px0 < 5 or py1 - py0 < 5:
        return 0.0
    crop = image_array[py0:py1, px0:px1]
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY) if crop.ndim == 3 else crop
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    count, _, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)
    cell_area = max(1, binary.shape[0] * binary.shape[1])
    best = 0.0
    for index in range(1, count):
        x, y, w, h, area = stats[index]
        if area < max(5, cell_area * 0.001) or area > cell_area * 0.12:
            continue
        aspect = w / max(1, h)
        extent = area / max(1, w * h)
        cx, cy = centroids[index]
        if not (0.18 * binary.shape[1] <= cx <= 0.82 * binary.shape[1] and 0.18 * binary.shape[0] <= cy <= 0.82 * binary.shape[0]):
            continue
        if not (0.58 <= aspect <= 1.72 and extent >= 0.38):
            continue
        confidence = min(1.0, 0.45 * extent + 0.35 * (1.0 - min(1.0, abs(math.log(aspect)))) + 0.2)
        best = max(best, confidence)
    return round(best, 6)


def table_rows_from_ocr(
    table: Any,
    ocr_words: list[dict],
    page_image_array: np.ndarray | None,
    scale: float,
) -> tuple[list[list[str]], list[dict]]:
    rows: list[list[str]] = []
    cell_records: list[dict] = []
    for row_index, table_row in enumerate(table.rows):
        cells: list[str] = []
        for col_index, cell in enumerate(table_row.cells):
            if cell is None:
                cells.append("")
                cell_records.append({"row": row_index + 1, "column": col_index + 1, "raw_text": "", "bbox_pt": None, "ocr_confidence": None, "common_spec": False, "mark_confidence": 0.0, "qa_status": "merged_or_missing_cell"})
                continue
            x0, top, x1, bottom = cell
            selected = []
            for word in ocr_words:
                wx0, wy0, wx1, wy1 = word["bbox_pt"]
                center_x, center_y = (wx0 + wx1) / 2, (wy0 + wy1) / 2
                if x0 <= center_x <= x1 and top <= center_y <= bottom:
                    selected.append(word)
            selected.sort(key=lambda word: (word["bbox_pt"][1], word["bbox_pt"][0]))
            raw_text = normalize_space(" ".join(word["text"] for word in selected))
            confidences = [float(word["confidence"]) for word in selected if float(word.get("confidence", -1)) >= 0]
            marker_like = raw_text.strip() in {"", "e", "E", "@", "o", "O", "0", "•", "·", "."}
            mark_confidence = dot_mark_confidence(page_image_array, cell, scale) if marker_like else 0.0
            common_spec = False
            value = raw_text
            cells.append(value)
            cell_records.append(
                {
                    "row": row_index + 1,
                    "column": col_index + 1,
                    "raw_text": raw_text,
                    "normalized_value": value,
                    "bbox_pt": [round(float(v), 3) for v in cell],
                    "ocr_confidence": round(sum(confidences) / len(confidences), 3) if confidences else None,
                    "common_spec": common_spec,
                    "mark_confidence": mark_confidence,
                    "qa_status": "mark_detected" if common_spec else ("ocr_text" if raw_text else "blank"),
                }
            )
        rows.append(cells)
    width = max((len(row.cells) for row in table.rows), default=0)
    return rectangularize(rows, width), cell_records


def apply_common_spec_semantics(rows: list[list[str]], cell_records: list[dict]) -> bool:
    """Enable dot semantics only after classifying the whole table as a dot matrix."""
    if len(cell_records) < 100 or max((len(row) for row in rows), default=0) < 10:
        return False
    marker_tokens = {"e", "E", "@", "o", "O", "0", "•", "·", "."}
    blank_or_marker = 0
    substantial_numeric = 0
    for record in cell_records:
        raw = str(record.get("raw_text", "")).strip()
        if not raw or raw in marker_tokens:
            blank_or_marker += 1
        if len(raw) >= 2 and re.fullmatch(r"[()<>≤≥+\-]?\d+(?:[.,]\d+)?", raw):
            substantial_numeric += 1
    cell_count = len(cell_records)
    is_dot_matrix = blank_or_marker / cell_count >= 0.58 and substantial_numeric / cell_count < 0.22
    if not is_dot_matrix:
        return False
    for record in cell_records:
        row_index = int(record["row"]) - 1
        col_index = int(record["column"]) - 1
        raw = str(record.get("raw_text", "")).strip()
        common_spec = (not raw or raw in marker_tokens) and float(record.get("mark_confidence") or 0.0) >= 0.67
        record["common_spec"] = common_spec
        if common_spec:
            record["normalized_value"] = "●"
            record["qa_status"] = "mark_detected_matrix"
            rows[row_index][col_index] = "●"
    return True


def native_tables(
    plumber_page: pdfplumber.page.Page,
    page_text: str,
    ocr_words: list[dict] | None = None,
    page_image_array: np.ndarray | None = None,
    scale: float = 1.0,
) -> list[dict]:
    settings_list = [
        {
            "vertical_strategy": "lines_strict",
            "horizontal_strategy": "lines_strict",
            "snap_tolerance": 3,
            "join_tolerance": 3,
            "intersection_tolerance": 4,
        },
        {
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
            "snap_tolerance": 4,
            "join_tolerance": 4,
            "intersection_tolerance": 5,
        },
    ]
    if TABLE_CAPTION_RE.search(page_text) or re.search(r"\b\d+(?:\.\d+)?\s+\d+(?:\.\d+)?\s+\d+(?:\.\d+)?\b", page_text):
        settings_list.append(
            {
                "vertical_strategy": "text",
                "horizontal_strategy": "text",
                "min_words_vertical": 2,
                "min_words_horizontal": 1,
                "text_tolerance": 3,
            }
        )
    found: list[dict] = []
    for settings in settings_list:
        if settings["vertical_strategy"] == "text" and any("lines" in record["method"] for record in found):
            continue
        try:
            tables = plumber_page.find_tables(table_settings=settings)
        except Exception:
            continue
        for table in tables:
            bbox = [round(float(value), 3) for value in table.bbox]
            if any(bbox_iou(bbox, existing["bbox_pt"]) >= 0.75 or bbox_containment(bbox, existing["bbox_pt"]) >= 0.9 for existing in found):
                continue
            try:
                if ocr_words:
                    rows, cell_records = table_rows_from_ocr(table, ocr_words, page_image_array, scale)
                    dot_matrix = apply_common_spec_semantics(rows, cell_records)
                    method = "pdfplumber_" + settings["vertical_strategy"] + "_ocr_words"
                else:
                    extracted = [[normalize_space(cell or "") for cell in row] for row in table.extract()]
                    rows = rectangularize(extracted) if "lines" in settings["vertical_strategy"] else trim_table(extracted)
                    cell_records = []
                    dot_matrix = False
                    method = "pdfplumber_" + settings["vertical_strategy"]
            except Exception:
                continue
            if len(rows) < 2 or max((len(row) for row in rows), default=0) < 2:
                continue
            nonempty = sum(bool(cell.strip()) for row in rows for cell in row)
            if nonempty < 4:
                continue
            found.append(
                {
                    "method": method,
                    "bbox_pt": bbox,
                    "rows": rows,
                    "grid_row_count": len(table.rows),
                    "grid_column_count": max((len(row.cells) for row in table.rows), default=0),
                    "cell_records": cell_records,
                    "dot_matrix": dot_matrix,
                    "structure_confidence": 0.9 if "lines" in settings["vertical_strategy"] else 0.7,
                }
            )
    return sorted(found, key=lambda item: (item["bbox_pt"][1], item["bbox_pt"][0]))


def force_grid_table_from_bbox(
    page_image_array: np.ndarray | None,
    words: list[dict],
    bbox_pt: list[float],
    scale: float,
) -> dict:
    """Extract a visually confirmed table region even when whole-page detection missed it."""
    if page_image_array is None:
        return {"rows": [[""]], "cell_records": [], "grid_row_count": 1, "grid_column_count": 1, "structure_confidence": 0.2}
    x0, y0, x1, y1 = bbox_pt
    px0, py0 = int(max(0, x0 * scale)), int(max(0, y0 * scale))
    px1 = int(min(page_image_array.shape[1], x1 * scale))
    py1 = int(min(page_image_array.shape[0], y1 * scale))
    crop = page_image_array[py0:py1, px0:px1]
    if crop.size == 0:
        return {"rows": [[""]], "cell_records": [], "grid_row_count": 1, "grid_column_count": 1, "structure_confidence": 0.1}
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 31, 15)
    height, width = binary.shape
    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (max(10, width // 12), 1)))
    vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(10, height // 10))))
    x_edges_px = cluster_peak_positions((vertical > 0).sum(axis=0), max(3, height * 0.18))
    y_edges_px = cluster_peak_positions((horizontal > 0).sum(axis=1), max(3, width * 0.18))
    if len(x_edges_px) < 2:
        x_edges_px = [0, max(1, width - 1)]
    if len(y_edges_px) < 2:
        y_edges_px = [0, max(1, height - 1)]
    x_edges = [x0 + value / scale for value in sorted(set(x_edges_px))]
    y_edges = [y0 + value / scale for value in sorted(set(y_edges_px))]
    if x_edges[0] > x0 + (x1 - x0) * 0.05:
        x_edges.insert(0, x0)
    if x_edges[-1] < x1 - (x1 - x0) * 0.05:
        x_edges.append(x1)
    if y_edges[0] > y0 + (y1 - y0) * 0.05:
        y_edges.insert(0, y0)
    if y_edges[-1] < y1 - (y1 - y0) * 0.05:
        y_edges.append(y1)
    rows: list[list[str]] = []
    records: list[dict] = []
    for row_index in range(len(y_edges) - 1):
        row: list[str] = []
        for col_index in range(len(x_edges) - 1):
            cell_bbox = [x_edges[col_index], y_edges[row_index], x_edges[col_index + 1], y_edges[row_index + 1]]
            selected = []
            for word in words:
                wx0, wy0, wx1, wy1 = word["bbox_pt"]
                center_x, center_y = (wx0 + wx1) / 2, (wy0 + wy1) / 2
                if cell_bbox[0] <= center_x <= cell_bbox[2] and cell_bbox[1] <= center_y <= cell_bbox[3]:
                    selected.append(word)
            selected.sort(key=lambda word: (word["bbox_pt"][1], word["bbox_pt"][0]))
            raw = normalize_space(" ".join(word["text"] for word in selected))
            confidences = [float(word["confidence"]) for word in selected if float(word.get("confidence", -1)) >= 0]
            row.append(raw)
            records.append(
                {
                    "row": row_index + 1,
                    "column": col_index + 1,
                    "raw_text": raw,
                    "normalized_value": raw,
                    "bbox_pt": [round(value, 3) for value in cell_bbox],
                    "ocr_confidence": round(sum(confidences) / len(confidences), 3) if confidences else None,
                    "common_spec": False,
                    "mark_confidence": 0.0,
                    "qa_status": "structure_override_ocr" if raw else "structure_override_blank",
                }
            )
        rows.append(row)
    return {
        "rows": rectangularize(rows),
        "cell_records": records,
        "grid_row_count": len(y_edges) - 1,
        "grid_column_count": len(x_edges) - 1,
        "structure_confidence": 0.85 if len(x_edges) >= 3 and len(y_edges) >= 3 else 0.45,
    }


def nearest_caption(lines: list[dict], bbox: list[float], pattern: re.Pattern) -> str:
    candidates = []
    for line in lines:
        if not caption_matches(pattern, line["text"]):
            continue
        line_box = line["bbox_pt"]
        if line_box[3] <= bbox[1] + 18:
            distance = bbox[1] - line_box[3]
        elif line_box[1] >= bbox[3] - 18:
            distance = line_box[1] - bbox[3]
        else:
            distance = 9999
        candidates.append((abs(distance), line["text"]))
    return min(candidates)[1] if candidates else ""


def caption_fallback_tables(lines: list[dict], candidates: list[dict], page_width: float, page_height: float) -> list[dict]:
    """Keep a searchable CSV for captioned weak/no-line tables pending cell reconstruction."""
    caption_lines = [line for line in lines if caption_matches(TABLE_CAPTION_RE, line["text"])]
    fallback: list[dict] = []
    for index, caption_line in enumerate(caption_lines):
        caption_box = caption_line["bbox_pt"]
        next_y = caption_lines[index + 1]["bbox_pt"][1] if index + 1 < len(caption_lines) else page_height
        if any(
            candidate["bbox_pt"][1] >= caption_box[1] - 20
            and candidate["bbox_pt"][1] < next_y
            and candidate["bbox_pt"][3] > caption_box[3]
            for candidate in candidates
        ):
            continue
        selected = [
            line
            for line in lines
            if line["bbox_pt"][1] >= caption_box[1] - 2
            and line["bbox_pt"][1] < next_y
            and not (line is not caption_line and caption_matches(TABLE_CAPTION_RE, line["text"]))
        ]
        if len(selected) < 2:
            continue
        bbox = [
            min(line["bbox_pt"][0] for line in selected),
            min(line["bbox_pt"][1] for line in selected),
            max(line["bbox_pt"][2] for line in selected),
            max(line["bbox_pt"][3] for line in selected),
        ]
        rows = [["line_order", "text"]] + [[str(order + 1), search_normalize(line["text"])] for order, line in enumerate(selected)]
        fallback.append(
            {
                "method": "caption_text_fallback",
                "bbox_pt": [round(value, 3) for value in bbox],
                "rows": rows,
                "grid_row_count": len(rows),
                "grid_column_count": 2,
                "cell_records": [],
                "dot_matrix": False,
                "structure_confidence": 0.3,
                "caption_override": search_normalize(caption_line["text"]),
                "structure_mode": "linearized_text_pending_cell_qa",
            }
        )
    return fallback


def safe_write_csv(path: Path, rows: list[list[str]]) -> None:
    if not path.parent.is_dir():
        raise FileNotFoundError(f"table output directory was not prepared: {path.parent}")
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        csv.writer(handle).writerows(rows)


def safe_write_cell_audit(path: Path, records: list[dict], rows: list[list[str]], table_bbox: list[float]) -> None:
    if not path.parent.is_dir():
        raise FileNotFoundError(f"table output directory was not prepared: {path.parent}")
    if not records:
        records = [
            {
                "row": row_index + 1,
                "column": col_index + 1,
                "raw_text": value,
                "normalized_value": value,
                "bbox_pt": table_bbox,
                "ocr_confidence": None,
                "common_spec": value == "●",
                "mark_confidence": None,
                "qa_status": "table_bbox_only",
            }
            for row_index, row in enumerate(rows)
            for col_index, value in enumerate(row)
        ]
    fields = ["row", "column", "raw_text", "normalized_value", "bbox_pt", "ocr_confidence", "common_spec", "mark_confidence", "qa_status"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            current = dict(record)
            current["bbox_pt"] = json.dumps(current.get("bbox_pt"), ensure_ascii=False)
            writer.writerow({field: current.get(field, "") for field in fields})


def save_clip(page: fitz.Page, bbox_pt: list[float], path: Path, dpi: int = 180) -> None:
    clip = fitz.Rect(bbox_pt) & page.rect
    if clip.is_empty or clip.width < 8 or clip.height < 8:
        return
    if not path.parent.is_dir():
        raise FileNotFoundError(f"figure output directory was not prepared: {path.parent}")
    pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), clip=clip, colorspace=fitz.csRGB, alpha=False)
    pix.save(path)


def process_batch(
    pdf_path: str,
    doc_id: str,
    doc_hash: str,
    page_indices: list[int],
    needs_ocr_map: dict[int, bool],
    ocr_dpi: int,
    ocr_language: str,
    temp_doc_dir: str,
    source_kind: str,
    expected_language: str,
    structure_override: dict | None,
) -> dict:
    pages_out: list[dict] = []
    tables_out: list[dict] = []
    figures_out: list[dict] = []
    formulas_out: list[dict] = []
    temp_root = Path(temp_doc_dir)
    with fitz.open(pdf_path) as document, pdfplumber.open(pdf_path) as plumber:
        for page_index in page_indices:
            page = document[page_index]
            page_id = f"{doc_id}:p{page_index + 1:04d}"
            override_assets = (structure_override or {}).get("assets", [])
            override_tables = [asset for asset in override_assets if asset.get("kind") == "table" and int(asset.get("page_1based", 0)) == page_index + 1]
            override_figures = [asset for asset in override_assets if asset.get("kind") == "figure" and int(asset.get("page_1based", 0)) == page_index + 1]
            override_formulas = [asset for asset in override_assets if asset.get("kind") == "formula" and int(asset.get("page_1based", 0)) == page_index + 1]
            page_override = (structure_override or {}).get("page_overrides", {}).get(str(page_index + 1), {})
            native, image_blocks = native_lines(page)
            native_text = normalize_space("\n".join(line["text"] for line in native))
            native_score = valid_text_score(native_text, expected_language)
            native_suspect = native_mapping_suspect(native_text, expected_language)
            ocr_lines: list[dict] = []
            ocr_words: list[dict] = []
            table_ocr_words: list[dict] = []
            ocr_confidence = 0.0
            table_ocr_confidence = 0.0
            table_grid_line_ratio = 0.0
            image: Image.Image | None = None
            image_array: np.ndarray | None = None
            original_array: np.ndarray | None = None
            scale = ocr_dpi / 72.0
            ocr_rotation = 0
            orientation_confidence = 0.0
            original_image_size = (0, 0)
            ink_ratio = -1.0
            if needs_ocr_map.get(page_index, False):
                original_image, original_array, scale = render_page(page, ocr_dpi)
                original_image_size = original_image.size
                gray = cv2.cvtColor(original_array, cv2.COLOR_RGB2GRAY)
                ink_ratio = round(float(np.mean(gray < 235)), 8)
                if ink_ratio >= 0.0005:
                    if "rotation_override" in page_override:
                        ocr_rotation = int(page_override["rotation_override"])
                        orientation_confidence = 100.0
                    else:
                        ocr_rotation, orientation_confidence = detect_rotation(original_image)
                    image = rotate_for_ocr(original_image, ocr_rotation)
                    image_array = np.asarray(image)
                    ocr_lines, ocr_words, ocr_confidence = ocr_page(
                        image,
                        scale,
                        ocr_language,
                        ocr_rotation,
                        original_image_size,
                    )
                    table_ocr_words = ocr_words
                    cleaned_table_image, table_grid_line_ratio = remove_table_grid(image_array)
                    if cleaned_table_image is not None:
                        _, cleaned_words, cleaned_confidence = ocr_page(
                            Image.fromarray(cleaned_table_image),
                            scale,
                            ocr_language,
                            ocr_rotation,
                            original_image_size,
                        )
                        if cleaned_words:
                            table_ocr_words = cleaned_words
                            table_ocr_confidence = cleaned_confidence
            ocr_text = normalize_space("\n".join(line["text"] for line in ocr_lines))
            ocr_score = valid_text_score(ocr_text, expected_language)
            if ink_ratio >= 0 and ink_ratio < 0.0005 and not native:
                primary_lines = []
                primary_method = "blank_page"
                primary_text = ""
                primary_score = 1.0
            elif ocr_lines and (native_suspect or ocr_score >= native_score + 0.03 or not native):
                primary_lines = ocr_lines
                primary_method = "ocr_text"
                primary_text = ocr_text
                primary_score = ocr_score
            elif native:
                primary_lines = native
                primary_method = "native_text" if not ocr_lines else "hybrid_text_native_primary"
                primary_text = native_text
                primary_score = native_score
            else:
                primary_lines = ocr_lines
                primary_method = "ocr_text"
                primary_text = ocr_text
                primary_score = ocr_score

            table_candidates: list[dict] = []
            if native:
                use_ocr_cells = table_ocr_words if native_suspect or native_score < 0.4 else None
                table_candidates.extend(native_tables(plumber.pages[page_index], native_text, use_ocr_cells, original_array, scale))
            if image_array is not None and table_ocr_words:
                for candidate in scan_grid_tables(
                    image_array,
                    table_ocr_words,
                    scale,
                    ocr_rotation,
                    original_image_size,
                ):
                    if not any(bbox_iou(candidate["bbox_pt"], current["bbox_pt"]) >= 0.7 or bbox_containment(candidate["bbox_pt"], current["bbox_pt"]) >= 0.9 for current in table_candidates):
                        table_candidates.append(candidate)
            if structure_override is None:
                table_candidates.extend(caption_fallback_tables(primary_lines, table_candidates, page.rect.width, page.rect.height))
            if override_tables:
                confirmed_candidates: list[dict] = []
                for asset in override_tables:
                    bbox = [float(value) for value in asset["bbox_pt"]]
                    best = max(table_candidates, key=lambda candidate: bbox_iou(bbox, candidate["bbox_pt"]), default=None)
                    if best is not None and bbox_iou(bbox, best["bbox_pt"]) >= 0.18:
                        candidate = dict(best)
                    else:
                        forced = force_grid_table_from_bbox(original_array, table_ocr_words or ocr_words, bbox, scale)
                        candidate = {
                            "method": "structure_override_grid_ocr",
                            "bbox_pt": bbox,
                            **forced,
                        }
                    candidate["bbox_pt"] = bbox
                    candidate["caption_override"] = asset.get("caption", "")
                    candidate["asset_label"] = asset.get("label", "")
                    candidate["qa_status"] = asset.get("qa_status", "")
                    candidate["structure_override"] = True
                    candidate["continuations_override"] = asset.get("continuations", [])
                    confirmed_candidates.append(candidate)
                table_candidates = confirmed_candidates
            elif structure_override is not None:
                table_candidates = []
            table_candidates.sort(key=lambda item: (item["bbox_pt"][1], item["bbox_pt"][0]))
            for table_order, candidate in enumerate(table_candidates, 1):
                table_id = f"{page_id}:t{table_order:02d}"
                caption = candidate.get("caption_override") or nearest_caption(primary_lines, candidate["bbox_pt"], TABLE_CAPTION_RE)
                filename = f"p{page_index + 1:04d}_t{table_order:02d}.csv"
                cell_filename = f"p{page_index + 1:04d}_t{table_order:02d}_cells.csv"
                safe_write_csv(temp_root / "tables" / filename, candidate["rows"])
                safe_write_cell_audit(temp_root / "tables" / cell_filename, candidate.get("cell_records", []), candidate["rows"], candidate["bbox_pt"])
                continuation_records = []
                for continuation_order, continuation in enumerate(candidate.get("continuations_override", []), 2):
                    continuation_page_index = int(continuation["page_1based"]) - 1
                    continuation_page = document[continuation_page_index]
                    continuation_image, continuation_array, continuation_scale = render_page(continuation_page, ocr_dpi)
                    continuation_page_override = (structure_override or {}).get("page_overrides", {}).get(str(continuation_page_index + 1), {})
                    if "rotation_override" in continuation_page_override:
                        continuation_rotation = int(continuation_page_override["rotation_override"])
                    else:
                        continuation_rotation, _ = detect_rotation(continuation_image)
                    continuation_work_image = rotate_for_ocr(continuation_image, continuation_rotation)
                    _, continuation_words, _ = ocr_page(
                        continuation_work_image,
                        continuation_scale,
                        ocr_language,
                        continuation_rotation,
                        continuation_image.size,
                    )
                    continuation_bbox = [float(value) for value in continuation["bbox_pt"]]
                    continuation_table = force_grid_table_from_bbox(continuation_array, continuation_words, continuation_bbox, continuation_scale)
                    continuation_filename = f"p{page_index + 1:04d}_t{table_order:02d}_cont{continuation_order:02d}.csv"
                    continuation_cell_filename = f"p{page_index + 1:04d}_t{table_order:02d}_cont{continuation_order:02d}_cells.csv"
                    safe_write_csv(temp_root / "tables" / continuation_filename, continuation_table["rows"])
                    safe_write_cell_audit(temp_root / "tables" / continuation_cell_filename, continuation_table.get("cell_records", []), continuation_table["rows"], continuation_bbox)
                    continuation_records.append(
                        {
                            "page_1based": continuation_page_index + 1,
                            "bbox_pt": continuation_bbox,
                            "csv_path": f"tables/{continuation_filename}",
                            "cell_audit_csv_path": f"tables/{continuation_cell_filename}",
                            "row_count": len(continuation_table["rows"]),
                            "column_count": max((len(row) for row in continuation_table["rows"]), default=0),
                            "qa_status": continuation.get("qa_status", ""),
                        }
                    )
                row_count = len(candidate["rows"])
                column_count = max((len(row) for row in candidate["rows"]), default=0)
                grid_rows = int(candidate.get("grid_row_count", row_count))
                grid_columns = int(candidate.get("grid_column_count", column_count))
                table_record = {
                    "table_id": table_id,
                    "doc_id": doc_id,
                    "page_id": page_id,
                    "page_1based": page_index + 1,
                    "table_order": table_order,
                    "method": candidate["method"],
                    "structure_confidence": candidate["structure_confidence"],
                    "bbox_pt": candidate["bbox_pt"],
                    "caption": caption,
                    "row_count": row_count,
                    "column_count": column_count,
                    "grid_row_count": grid_rows,
                    "grid_column_count": grid_columns,
                    "geometry_preserved": row_count == grid_rows and column_count == grid_columns,
                    "nonempty_cells": sum(bool(cell.strip()) for row in candidate["rows"] for cell in row),
                    "common_spec_cells": sum(cell == "●" for row in candidate["rows"] for cell in row),
                    "dot_matrix": bool(candidate.get("dot_matrix", False)),
                    "asset_label": candidate.get("asset_label", ""),
                    "asset_qa_status": candidate.get("qa_status", ""),
                    "structure_override": bool(candidate.get("structure_override", False)),
                    "structure_mode": candidate.get("structure_mode", "cell_grid"),
                    "numeric_reuse_allowed": candidate.get("structure_mode", "cell_grid") == "cell_grid" and candidate["structure_confidence"] >= 0.9 and "ocr" not in candidate["method"],
                    "key_table": bool(caption) or source_kind in {"standard", "construction_standard"},
                    "csv_path": f"tables/{filename}",
                    "cell_audit_csv_path": f"tables/{cell_filename}",
                    "continuations": continuation_records,
                    "source_pdf_sha256": doc_hash,
                }
                tables_out.append(table_record)

            figure_boxes: list[tuple[list[float], str, str, dict | None]] = []
            page_area = max(1.0, page.rect.width * page.rect.height)
            if override_figures:
                for asset in override_figures:
                    figure_boxes.append(([float(value) for value in asset["bbox_pt"]], asset.get("caption", ""), "structure_override_crop", asset))
            elif structure_override is None:
                for block in image_blocks:
                    bbox = block["bbox_pt"]
                    area_ratio = max(0.0, bbox[2] - bbox[0]) * max(0.0, bbox[3] - bbox[1]) / page_area
                    if 0.03 <= area_ratio <= 0.82:
                        figure_boxes.append((bbox, nearest_caption(primary_lines, bbox, FIGURE_CAPTION_RE), "embedded_image", None))
                for line in primary_lines:
                    if not caption_matches(FIGURE_CAPTION_RE, line["text"]):
                        continue
                    caption_bbox = line["bbox_pt"]
                    y1 = max(1.0, caption_bbox[1] - 2)
                    y0 = max(0.0, y1 - page.rect.height * 0.48)
                    bbox = [0.04 * page.rect.width, y0, 0.96 * page.rect.width, y1]
                    if not any(bbox_iou(bbox, current[0]) >= 0.5 for current in figure_boxes):
                        figure_boxes.append((bbox, line["text"], "caption_crop", None))
            for figure_order, (bbox, caption, method, asset) in enumerate(figure_boxes, 1):
                figure_id = f"{page_id}:f{figure_order:02d}"
                filename = f"p{page_index + 1:04d}_f{figure_order:02d}.png"
                save_clip(page, bbox, temp_root / "figures" / filename)
                continuation_records = []
                for continuation_order, continuation in enumerate((asset or {}).get("continuations", []), 2):
                    continuation_page_index = int(continuation["page_1based"]) - 1
                    continuation_filename = f"p{page_index + 1:04d}_f{figure_order:02d}_cont{continuation_order:02d}.png"
                    save_clip(document[continuation_page_index], continuation["bbox_pt"], temp_root / "figures" / continuation_filename)
                    continuation_records.append(
                        {
                            "page_1based": int(continuation["page_1based"]),
                            "bbox_pt": continuation["bbox_pt"],
                            "image_path": f"figures/{continuation_filename}",
                            "qa_status": continuation.get("qa_status", ""),
                        }
                    )
                figures_out.append(
                    {
                        "figure_id": figure_id,
                        "doc_id": doc_id,
                        "page_id": page_id,
                        "page_1based": page_index + 1,
                        "figure_order": figure_order,
                        "method": method,
                        "bbox_pt": bbox,
                        "caption": caption,
                        "key_figure": bool(caption),
                        "image_path": f"figures/{filename}",
                        "asset_label": (asset or {}).get("label", ""),
                        "asset_qa_status": (asset or {}).get("qa_status", ""),
                        "structure_override": asset is not None,
                        "continuations": continuation_records,
                        "source_pdf_sha256": doc_hash,
                    }
                )

            for formula_order, asset in enumerate(override_formulas, 1):
                bbox = [float(value) for value in asset["bbox_pt"]]
                formula_id = f"{page_id}:q{formula_order:02d}"
                filename = f"p{page_index + 1:04d}_q{formula_order:02d}.png"
                save_clip(page, bbox, temp_root / "formulas" / filename, dpi=max(240, ocr_dpi))
                raw_text = search_normalize(
                    " ".join(
                        line["text"]
                        for line in primary_lines
                        if bbox_containment(line["bbox_pt"], bbox) >= 0.45 or bbox_iou(line["bbox_pt"], bbox) > 0
                    )
                )
                formulas_out.append(
                    {
                        "formula_id": formula_id,
                        "doc_id": doc_id,
                        "page_id": page_id,
                        "page_1based": page_index + 1,
                        "formula_order": formula_order,
                        "label": asset.get("label", ""),
                        "caption": asset.get("caption", ""),
                        "bbox_pt": bbox,
                        "raw_text": raw_text,
                        "method": "structure_override_formula_crop",
                        "qa_status": asset.get("qa_status", ""),
                        "image_path": f"formulas/{filename}",
                        "source_pdf_sha256": doc_hash,
                    }
                )

            for order, line in enumerate(primary_lines):
                line["block_id"] = f"{page_id}:b{order + 1:03d}"
            headings = [search_normalize(line["text"]) for line in primary_lines if is_heading(line, primary_lines)]
            pages_out.append(
                {
                    "page_id": page_id,
                    "doc_id": doc_id,
                    "page_1based": page_index + 1,
                    "width_pt": round(page.rect.width, 3),
                    "height_pt": round(page.rect.height, 3),
                    "source_pdf_sha256": doc_hash,
                    "primary_method": primary_method,
                    "primary_quality_score": primary_score,
                    "native_quality_score": native_score,
                    "native_mapping_suspect": native_suspect,
                    "ocr_quality_score": ocr_score,
                    "ocr_mean_confidence": ocr_confidence,
                    "table_ocr_mean_confidence": table_ocr_confidence,
                    "table_grid_line_ratio": table_grid_line_ratio,
                    "ocr_rotation_clockwise": ocr_rotation,
                    "orientation_confidence": round(orientation_confidence, 3),
                    "ink_ratio": ink_ratio,
                    "primary_char_count": len(re.sub(r"\s+", "", primary_text)),
                    "needs_manual_review": primary_method != "blank_page" and (len(re.sub(r"\s+", "", primary_text)) < 20 or primary_score < 0.38 or (primary_method == "ocr_text" and ocr_confidence < 40) or (ink_ratio >= 0.001 and len(re.sub(r"\s+", "", primary_text)) < 20) or (native_suspect and primary_method != "ocr_text") or any(not table.get("geometry_preserved", True) for table in tables_out if table["page_id"] == page_id)),
                    "headings": headings,
                    "table_count": len(table_candidates),
                    "figure_count": len(figure_boxes),
                    "lines": primary_lines,
                    "primary_text": primary_text,
                    "native_text": native_text if primary_method.startswith("ocr") and native_text else "",
                    "ocr_text": ocr_text if not primary_method.startswith("ocr") and ocr_text else "",
                    "text_sha256": sha256_text(primary_text),
                }
            )
    return {"pages": pages_out, "tables": tables_out, "figures": figures_out, "formulas": formulas_out}


def is_heading(line: dict, page_lines: list[dict]) -> bool:
    text = search_normalize(line["text"].strip())
    compact = re.sub(r"\s+", "", text)
    if not text or len(text) > 120 or caption_matches(TABLE_CAPTION_RE, text) or caption_matches(FIGURE_CAPTION_RE, text):
        return False
    if re.match(r"^第[一二三四五六七八九十百0-9]+[章节篇部]", compact):
        return True
    if re.match(r"^(?:附录|附件)[A-ZＡ-Ｚ一二三四五六七八九十0-9]+", compact, re.I):
        return True
    if re.match(r"^(?:chapter|part|appendix)\s+[A-Z0-9IVX]+", text, re.I):
        return True
    numeric = re.match(r"^(\d+(?:\.\d+){0,5})\s+(.+)$", text)
    if numeric:
        body = numeric.group(2).strip()
        letters = sum(ch.isalpha() or "\u3400" <= ch <= "\u9fff" for ch in body)
        if letters >= 2 and not re.search(r"[=×÷∑∫]", body) and not re.match(r"^(?:mm|cm|kg|mpa|pa|n|kn|℃|%)\b", body, re.I):
            return True
    sizes = sorted(candidate.get("font_size", 0.0) for candidate in page_lines if candidate.get("font_size", 0.0) > 0)
    if sizes and line.get("font_size", 0.0) >= sizes[len(sizes) // 2] * 1.28 and len(text) <= 60:
        return True
    return False


def heading_level(text: str) -> int:
    text = search_normalize(text)
    compact = re.sub(r"\s+", "", text)
    if re.match(r"^第[一二三四五六七八九十百0-9]+[篇部章节]", compact):
        return 1
    if re.match(r"^(?:附录|附件)", compact, re.I) or re.match(r"^(?:chapter|part|appendix)", text, re.I):
        return 1
    match = re.match(r"^(\d+(?:\.\d+)*)", text)
    if match:
        return min(6, match.group(1).count(".") + 1)
    return 2


def tail_overlap(units: list[dict], max_chars: int) -> list[dict]:
    result: list[dict] = []
    total = 0
    for unit in reversed(units):
        length = len(unit["text"])
        if result and total + length > max_chars:
            break
        result.append(unit)
        total += length
    return list(reversed(result))


def build_chunks(pages: list[dict], document_row: dict, doc_hash: str, target_chars: int = 1200, overlap_chars: int = 160) -> list[dict]:
    chunks: list[dict] = []
    current: list[dict] = []
    section_stack: list[str] = []

    def flush() -> None:
        nonlocal current
        text = normalize_space("\n".join(unit["text"] for unit in current))
        if not text:
            current = []
            return
        page_numbers = [unit["page_1based"] for unit in current]
        block_ids = [unit["block_id"] for unit in current]
        chunk_order = len(chunks) + 1
        chunks.append(
            {
                "chunk_id": f"{document_row['doc_id']}:c{chunk_order:05d}",
                "doc_id": document_row["doc_id"],
                "chunk_order": chunk_order,
                "relative_path": document_row["relative_path"],
                "family": document_row["family"],
                "source_kind": document_row["source_kind"],
                "evidence_default": document_row["evidence_default"],
                "source_pdf_sha256": doc_hash,
                "page_start": min(page_numbers),
                "page_end": max(page_numbers),
                "block_ids": block_ids,
                "section_path": " > ".join(section_stack),
                "extraction_methods": sorted({unit["method"] for unit in current}),
                "quality_score": round(min(unit["quality"] for unit in current), 6),
                "char_count": len(re.sub(r"\s+", "", text)),
                "text_sha256": sha256_text(text),
                "text": text,
            }
        )
        current = tail_overlap(current, overlap_chars)

    for page in sorted(pages, key=lambda item: item["page_1based"]):
        for line in page["lines"]:
            heading = is_heading(line, page["lines"])
            canonical_heading = search_normalize(line["text"])
            level = heading_level(canonical_heading) if heading else 0
            if heading and current and (level == 1 or sum(len(unit["text"]) for unit in current) >= 240):
                flush()
            if heading:
                section_stack = section_stack[: level - 1]
                while len(section_stack) < level - 1:
                    section_stack.append("未标识层级")
                section_stack.append(canonical_heading)
            current.append(
                {
                    "text": line["text"],
                    "page_1based": page["page_1based"],
                    "block_id": line["block_id"],
                    "method": line["method"],
                    "quality": page["primary_quality_score"],
                }
            )
            length = sum(len(unit["text"]) for unit in current)
            if length >= target_chars and (line["text"].endswith(("。", ".", "；", ";", "：", ":")) or length >= int(target_chars * 1.35)):
                flush()
    if current:
        previous_count = len(chunks)
        flush()
        if len(chunks) == previous_count and current:
            current = []
    return chunks


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def write_catalog_csv(path: Path, rows: list[dict], exclude: set[str] | None = None) -> None:
    exclude = exclude or set()
    flattened: list[dict] = []
    for row in rows:
        flat = {}
        for key, value in row.items():
            if key in exclude:
                continue
            flat[key] = json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value
        flattened.append(flat)
    fields = list(flattened[0]) if flattened else []
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if fields:
            writer.writeheader()
            writer.writerows(flattened)


def retrieval_card(document_row: dict, doc_hash: str, pages: list[dict], chunks: list[dict], tables: list[dict], figures: list[dict], formulas: list[dict]) -> str:
    headings = []
    for page in pages:
        for heading in page["headings"]:
            if heading not in headings:
                headings.append(heading)
    lines = [
        f"# {document_row['doc_id']}",
        "",
        f"- 文件：`{document_row['relative_path']}`",
        f"- SHA-256：`{doc_hash}`",
        f"- 设备族：`{document_row['family']}`",
        f"- 来源性质：`{document_row['source_kind']}`",
        f"- 默认证据等级：`{document_row['evidence_default']}`",
        f"- 页数：{len(pages)}；切片：{len(chunks)}；表格：{len(tables)}；图件：{len(figures)}；公式资产：{len(formulas)}",
        f"- 低质量待复核页：{sum(page['needs_manual_review'] for page in pages)}",
        "- 全文检索：使用 `scripts/query_standard_knowledge.py`，本卡只承担全局向量路由。",
        "",
        "## 章节/条款入口",
        "",
    ]
    lines.extend(f"- {heading}" for heading in headings[:400])
    if tables:
        lines.extend(["", "## 关键表格入口", ""])
        for table in tables:
            if table["key_table"]:
                lines.append(f"- p{table['page_1based']} `{table['table_id']}` {table['caption'] or '(无表题，待复核)'} -> `{table['csv_path']}`")
    if figures:
        lines.extend(["", "## 关键图件入口", ""])
        for figure in figures:
            if figure["key_figure"]:
                lines.append(f"- p{figure['page_1based']} `{figure['figure_id']}` {figure['caption']} -> `{figure['image_path']}`")
    if formulas:
        lines.extend(["", "## 关键公式入口", ""])
        for formula in formulas:
            lines.append(f"- p{formula['page_1based']} `{formula['formula_id']}` {formula['label']} {formula['caption']} -> `{formula['image_path']}`")
    return "\n".join(lines) + "\n"


def partition(indices: list[int], workers: int) -> list[list[int]]:
    workers = max(1, min(workers, len(indices) or 1))
    batches = [[] for _ in range(workers)]
    for index, page_index in enumerate(indices):
        batches[index % workers].append(page_index)
    return [batch for batch in batches if batch]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--inventory-pages", type=Path, required=True)
    parser.add_argument("--out-root", type=Path, required=True)
    parser.add_argument("--doc-id", required=True)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--ocr-dpi", type=int, default=190)
    parser.add_argument("--ocr-language", default="chi_sim+eng")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    registry = {row["doc_id"]: row for row in read_csv(args.registry.resolve())}
    if args.doc_id not in registry:
        raise KeyError(f"unknown doc_id {args.doc_id}")
    row = registry[args.doc_id]
    source_path = (args.source_root.resolve() / Path(row["relative_path"])).resolve()
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    out_root = args.out_root.resolve()
    documents_root = out_root / "documents"
    final_dir = documents_root / args.doc_id
    doc_hash = sha256_path(source_path)
    override_path = out_root / "overrides" / f"{args.doc_id}.json"
    structure_override: dict | None = None
    if override_path.is_file():
        structure_override = json.loads(override_path.read_text(encoding="utf-8"))
        if structure_override.get("doc_id") != args.doc_id:
            raise ValueError(f"structure override doc_id mismatch: {override_path}")
        if structure_override.get("source_pdf_sha256") != doc_hash:
            raise ValueError(f"structure override hash mismatch: {override_path}")
    if final_dir.exists() and not args.force:
        status_path = final_dir / "status.json"
        if status_path.is_file():
            status = json.loads(status_path.read_text(encoding="utf-8"))
            if status.get("source_pdf_sha256") == doc_hash and status.get("status") in {"PASS", "PASS_WITH_REVIEW"}:
                print(json.dumps({"doc_id": args.doc_id, "status": "already_complete", "path": str(final_dir)}, ensure_ascii=False))
                return 0
        raise FileExistsError(f"existing incomplete/different output; rerun with --force: {final_dir}")
    if final_dir.exists() and args.force:
        resolved = final_dir.resolve()
        if resolved.parent != documents_root.resolve():
            raise RuntimeError(f"refusing to replace unsafe output path {resolved}")
    documents_root.mkdir(parents=True, exist_ok=True)
    temp_parent = out_root / "_tmp_documents"
    temp_parent.mkdir(parents=True, exist_ok=True)
    temp_dir = temp_parent / f"{args.doc_id}_{os.getpid()}"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir()
    try:
        (temp_dir / "tables").mkdir()
        (temp_dir / "figures").mkdir()
        (temp_dir / "formulas").mkdir()
        inventory_rows = [page for page in read_csv(args.inventory_pages.resolve()) if page["doc_id"] == args.doc_id]
        needs_ocr = {int(page["page_1based"]) - 1: str(page["needs_ocr"]).strip().lower() in {"1", "true", "yes"} for page in inventory_rows}
        with fitz.open(source_path) as document:
            page_count = document.page_count
        indices = list(range(page_count))
        batches = partition(indices, args.workers)
        results = []
        if len(batches) == 1:
            results.append(process_batch(str(source_path), args.doc_id, doc_hash, batches[0], needs_ocr, args.ocr_dpi, args.ocr_language, str(temp_dir), row["source_kind"], row["language"], structure_override))
        else:
            # Thread workers keep one fitz/pdfplumber handle per batch and avoid
            # Windows multiprocessing named-pipe permission failures.  OCR runs
            # in external Tesseract processes, so the expensive stage still
            # executes concurrently.
            with ThreadPoolExecutor(max_workers=len(batches)) as pool:
                futures = [pool.submit(process_batch, str(source_path), args.doc_id, doc_hash, batch, needs_ocr, args.ocr_dpi, args.ocr_language, str(temp_dir), row["source_kind"], row["language"], structure_override) for batch in batches]
                for future in as_completed(futures):
                    results.append(future.result())
        pages = sorted([page for result in results for page in result["pages"]], key=lambda item: item["page_1based"])
        tables = sorted([table for result in results for table in result["tables"]], key=lambda item: (item["page_1based"], item["table_order"]))
        figures = sorted([figure for result in results for figure in result["figures"]], key=lambda item: (item["page_1based"], item["figure_order"]))
        formulas = sorted([formula for result in results for formula in result["formulas"]], key=lambda item: (item["page_1based"], item["formula_order"]))
        if len(pages) != page_count:
            raise RuntimeError(f"page coverage mismatch {len(pages)} != {page_count}")
        chunks = build_chunks(pages, row, doc_hash)
        write_jsonl(temp_dir / "raw_pages.jsonl", pages)
        write_jsonl(temp_dir / "chunks.jsonl", chunks)
        write_jsonl(temp_dir / "tables.jsonl", tables)
        write_jsonl(temp_dir / "figures.jsonl", figures)
        write_jsonl(temp_dir / "formulas.jsonl", formulas)
        write_catalog_csv(temp_dir / "pages.csv", pages, {"lines", "primary_text", "native_text", "ocr_text", "headings"})
        write_catalog_csv(temp_dir / "chunks.csv", chunks, {"text", "block_ids"})
        write_catalog_csv(temp_dir / "tables.csv", tables)
        write_catalog_csv(temp_dir / "figures.csv", figures)
        write_catalog_csv(temp_dir / "formulas.csv", formulas, {"raw_text"})
        (temp_dir / "retrieval_card.md").write_text(retrieval_card(row, doc_hash, pages, chunks, tables, figures, formulas), encoding="utf-8")
        manual_review_pages = [page["page_1based"] for page in pages if page["needs_manual_review"]]
        geometry_review_tables = [table["table_id"] for table in tables if not table.get("geometry_preserved", True)]
        expected_counts = (structure_override or {}).get("expected_counts", {})
        structure_count_mismatches = []
        if "tables" in expected_counts and len(tables) != int(expected_counts["tables"]):
            structure_count_mismatches.append(f"tables:{len(tables)}!={expected_counts['tables']}")
        if "figures" in expected_counts and len(figures) != int(expected_counts["figures"]):
            structure_count_mismatches.append(f"figures:{len(figures)}!={expected_counts['figures']}")
        if "formulas" in expected_counts and len(formulas) != int(expected_counts["formulas"]):
            structure_count_mismatches.append(f"formulas:{len(formulas)}!={expected_counts['formulas']}")
        status = {
            "schema": "design-standard-document-package-v1",
            "status": "PASS_WITH_REVIEW" if manual_review_pages or geometry_review_tables or structure_count_mismatches else "PASS",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "doc_id": args.doc_id,
            "relative_path": row["relative_path"],
            "source_pdf_sha256": doc_hash,
            "page_count": page_count,
            "covered_pages": len(pages),
            "chunk_count": len(chunks),
            "table_count": len(tables),
            "key_table_count": sum(table["key_table"] for table in tables),
            "figure_count": len(figures),
            "key_figure_count": sum(figure["key_figure"] for figure in figures),
            "formula_count": len(formulas),
            "native_primary_pages": sum(page["primary_method"] == "native_text" for page in pages),
            "hybrid_primary_pages": sum(page["primary_method"].startswith("hybrid") for page in pages),
            "ocr_primary_pages": sum(page["primary_method"] == "ocr_text" for page in pages),
            "manual_review_pages": manual_review_pages,
            "geometry_review_tables": geometry_review_tables,
            "structure_override_path": str(override_path) if structure_override else "",
            "structure_override_sha256": sha256_path(override_path) if structure_override else "",
            "structure_expected_counts": expected_counts,
            "structure_count_mismatches": structure_count_mismatches,
            "mean_primary_quality": round(sum(page["primary_quality_score"] for page in pages) / max(1, len(pages)), 6),
            "ocr_dpi": args.ocr_dpi,
            "ocr_language": args.ocr_language,
        }
        (temp_dir / "status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        previous_dir: Path | None = None
        if final_dir.exists():
            previous_root = out_root / "_previous_documents"
            previous_root.mkdir(parents=True, exist_ok=True)
            previous_dir = previous_root / f"{args.doc_id}_{os.getpid()}"
            if previous_dir.exists():
                raise RuntimeError(f"refusing to overwrite previous-package backup {previous_dir}")
            os.replace(final_dir, previous_dir)
        try:
            os.replace(temp_dir, final_dir)
        except Exception:
            if previous_dir is not None and previous_dir.exists() and not final_dir.exists():
                os.replace(previous_dir, final_dir)
            raise
        if previous_dir is not None and previous_dir.exists():
            shutil.rmtree(previous_dir)
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return 0
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
