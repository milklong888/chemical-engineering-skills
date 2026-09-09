#!/usr/bin/env python3
"""Extract fail-closed cell geometry and OCR candidates from ruled table images.

The script is an offline evidence builder.  OCR output is always a candidate;
it never assigns a direct-reuse or printed-glyph verification status.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


ROTATIONS = {"none", "clockwise90", "counterclockwise90", "rotate180"}
GRAYSCALE_MODES = {"cv2-gray", "max-channel"}


def black_text_grayscale(image: np.ndarray, *, mode: str) -> np.ndarray:
    """Build grayscale evidence while optionally suppressing chromatic marks.

    ``max-channel`` turns saturated coloured pixels white while retaining black
    printed strokes.  It is intended for black engineering print obscured by a
    red/blue watermark; it does not verify OCR glyphs.
    """
    if mode not in GRAYSCALE_MODES:
        raise ValueError(f"unsupported grayscale mode: {mode}")
    if image.ndim == 2:
        return image.copy()
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("image must be grayscale or three-channel BGR")
    if mode == "max-channel":
        return image.max(axis=2).astype(np.uint8)
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def rotate_image(image: np.ndarray, rotation: str) -> np.ndarray:
    if rotation not in ROTATIONS:
        raise ValueError(f"unsupported rotation: {rotation}")
    if rotation == "clockwise90":
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    if rotation == "counterclockwise90":
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    if rotation == "rotate180":
        return cv2.rotate(image, cv2.ROTATE_180)
    return image.copy()


def rotated_bbox_to_original(
    bbox: tuple[int, int, int, int],
    *,
    rotation: str,
    original_width: int,
    original_height: int,
) -> tuple[int, int, int, int]:
    """Map an axis-aligned pixel box from the rotated image to the source image."""
    if rotation not in ROTATIONS:
        raise ValueError(f"unsupported rotation: {rotation}")
    if original_width < 1 or original_height < 1:
        raise ValueError("original image dimensions must be positive")
    x1, y1, x2, y2 = bbox
    rotated_width, rotated_height = (
        (original_height, original_width)
        if rotation in {"clockwise90", "counterclockwise90"}
        else (original_width, original_height)
    )
    if not (0 <= x1 < x2 <= rotated_width and 0 <= y1 < y2 <= rotated_height):
        raise ValueError("rotated bbox is empty or outside the rotated image")
    if rotation == "clockwise90":
        mapped = (y1, original_height - x2, y2, original_height - x1)
    elif rotation == "counterclockwise90":
        mapped = (original_width - y2, x1, original_width - y1, x2)
    elif rotation == "rotate180":
        mapped = (
            original_width - x2,
            original_height - y2,
            original_width - x1,
            original_height - y1,
        )
    else:
        mapped = bbox
    ox1, oy1, ox2, oy2 = mapped
    if not (0 <= ox1 < ox2 <= original_width and 0 <= oy1 < oy2 <= original_height):
        raise ValueError("mapped bbox is empty or outside the original image")
    return mapped


def _clusters(projection: np.ndarray, threshold: float) -> list[tuple[int, int, float]]:
    indexes = np.flatnonzero(projection >= threshold)
    if not len(indexes):
        return []
    groups: list[tuple[int, int, float]] = []
    start = previous = int(indexes[0])
    for raw in indexes[1:]:
        current = int(raw)
        if current > previous + 1:
            segment = projection[start:previous + 1]
            groups.append((start, previous, float(segment.max())))
            start = current
        previous = current
    segment = projection[start:previous + 1]
    groups.append((start, previous, float(segment.max())))
    return groups


def _line_positions(
    binary: np.ndarray, *, vertical: bool, expected_count: int
) -> list[int]:
    height, width = binary.shape
    kernel_length = max(8, (height // 45) if vertical else (width // 30))
    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (1, kernel_length) if vertical else (kernel_length, 1)
    )
    lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    projection = lines.sum(axis=0 if vertical else 1) / 255.0
    span = height if vertical else width
    exact: list[tuple[float, list[tuple[int, int, float]]]] = []
    for fraction in (0.04, 0.06, 0.08, 0.10, 0.12, 0.15, 0.18, 0.22, 0.25, 0.30, 0.35, 0.40):
        groups = _clusters(projection, span * fraction)
        if len(groups) == expected_count:
            exact.append((fraction, groups))
    if not exact:
        raise ValueError(
            f"ruled-grid boundary count did not close: expected {expected_count} "
            f"{'vertical' if vertical else 'horizontal'} lines"
        )
    # Prefer the strictest threshold that still preserves every expected line;
    # this rejects short text strokes that survive at permissive thresholds.
    _, groups = max(exact, key=lambda item: item[0])
    positions: list[int] = []
    for start, end, _ in groups:
        segment = projection[start:end + 1]
        positions.append(start + int(np.argmax(segment)))
    return positions


def detect_grid_lines(
    gray_image: np.ndarray, *, expected_rows: int, expected_columns: int
) -> tuple[list[int], list[int]]:
    """Return horizontal and vertical boundary coordinates for an exact grid."""
    if gray_image.ndim != 2 or not gray_image.size:
        raise ValueError("gray_image must be a nonempty two-dimensional array")
    if expected_rows < 1 or expected_columns < 1:
        raise ValueError("expected_rows and expected_columns must be positive")
    _, binary = cv2.threshold(
        gray_image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )
    horizontal = _line_positions(
        binary, vertical=False, expected_count=expected_rows + 1
    )
    vertical = _line_positions(
        binary, vertical=True, expected_count=expected_columns + 1
    )
    return horizontal, vertical


def cell_bboxes(
    *, horizontal: list[int], vertical: list[int]
) -> list[tuple[int, int, int, int]]:
    """Return row-major cell rectangles from closed boundary coordinates."""
    if len(horizontal) < 2 or len(vertical) < 2:
        raise ValueError("at least two horizontal and vertical boundaries are required")
    if horizontal != sorted(set(horizontal)) or vertical != sorted(set(vertical)):
        raise ValueError("grid boundaries must be strictly increasing and unique")
    return [
        (vertical[column], horizontal[row], vertical[column + 1], horizontal[row + 1])
        for row in range(len(horizontal) - 1)
        for column in range(len(vertical) - 1)
    ]


def build_geometry_records(
    *,
    horizontal: list[int],
    vertical: list[int],
    rotation: str = "none",
    original_width: int | None = None,
    original_height: int | None = None,
) -> list[dict[str, str | int]]:
    boxes = cell_bboxes(horizontal=horizontal, vertical=vertical)
    if original_width is None or original_height is None:
        if rotation != "none":
            raise ValueError("rotated geometry requires original image dimensions")
        original_width = vertical[-1]
        original_height = horizontal[-1]
    columns = len(vertical) - 1
    records: list[dict[str, str | int]] = []
    for index, box in enumerate(boxes):
        row, column = divmod(index, columns)
        original_box = rotated_bbox_to_original(
            box,
            rotation=rotation,
            original_width=original_width,
            original_height=original_height,
        )
        records.append({
            "cell_id": f"r{row + 1:03d}:c{column + 1:03d}",
            "row": row + 1,
            "column": column + 1,
            "rotated_bbox_px": json.dumps(box, separators=(",", ":")),
            "original_bbox_px": json.dumps(original_box, separators=(",", ":")),
            "raw_printed_glyph": "",
            "normalized_value": "",
            "qa_status": "GEOMETRY_ONLY_OCR_NOT_VERIFIED",
        })
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--expected-rows", type=int)
    parser.add_argument("--expected-columns", type=int)
    parser.add_argument("--rotation", choices=sorted(ROTATIONS), default="none")
    parser.add_argument(
        "--grayscale-mode", choices=sorted(GRAYSCALE_MODES), default="cv2-gray"
    )
    parser.add_argument("--out-csv", type=Path)
    parser.add_argument("--out-preprocessed-image", type=Path)
    parser.add_argument("--preprocess-only", action="store_true")
    args = parser.parse_args()
    image_path = args.image.resolve()
    payload = np.fromfile(image_path, dtype=np.uint8)
    original_color = cv2.imdecode(payload, cv2.IMREAD_COLOR)
    if original_color is None:
        raise ValueError(f"cannot decode image: {args.image}")
    original_image = black_text_grayscale(original_color, mode=args.grayscale_mode)
    original_height, original_width = original_image.shape
    image = rotate_image(original_image, args.rotation)
    result = {
        "schema": "ruled-table-cell-geometry-candidate-v1",
        "image": str(image_path),
        "image_sha256": hashlib.sha256(image_path.read_bytes()).hexdigest().upper(),
        "rotation": args.rotation,
        "grayscale_mode": args.grayscale_mode,
        "original_width_px": int(original_width),
        "original_height_px": int(original_height),
        "rotated_width_px": int(image.shape[1]),
        "rotated_height_px": int(image.shape[0]),
        "qa_status": "PREPROCESSING_ONLY_NOT_GLYPH_VERIFIED",
    }
    if args.out_preprocessed_image:
        rendered = args.out_preprocessed_image.resolve()
        rendered.parent.mkdir(parents=True, exist_ok=True)
        suffix = rendered.suffix.casefold() or ".png"
        encoded_ok, encoded = cv2.imencode(suffix, image)
        if not encoded_ok:
            raise ValueError(f"cannot encode preprocessed image as {suffix}")
        rendered.write_bytes(encoded.tobytes())
        result["preprocessed_image"] = str(rendered)
        result["preprocessed_image_sha256"] = hashlib.sha256(
            rendered.read_bytes()
        ).hexdigest().upper()
    if args.preprocess_only:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.expected_rows is None or args.expected_columns is None:
        raise ValueError("grid extraction requires expected rows and columns")
    horizontal, vertical = detect_grid_lines(
        image, expected_rows=args.expected_rows, expected_columns=args.expected_columns
    )
    records = build_geometry_records(
        horizontal=horizontal,
        vertical=vertical,
        rotation=args.rotation,
        original_width=int(original_width),
        original_height=int(original_height),
    )
    result.update({
        "horizontal_boundaries_px": horizontal,
        "vertical_boundaries_px": vertical,
        "cell_count": len(records),
        "qa_status": "GEOMETRY_ONLY_OCR_NOT_VERIFIED",
    })
    if args.out_csv:
        output = args.out_csv.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        fields = list(records[0])
        with output.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(records)
        result["output_csv"] = str(output)
        result["output_csv_sha256"] = hashlib.sha256(output.read_bytes()).hexdigest().upper()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
