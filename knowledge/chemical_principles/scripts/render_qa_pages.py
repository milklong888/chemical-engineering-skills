# -*- coding: utf-8 -*-
"""Render representative source pages for visual OCR/layout quality review."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import fitz


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
OUTPUT = WORKSPACE / "tmp" / "pdfs" / "chemical_principles_qa_20260724"
SAMPLES = [
    ("upper", 14),
    ("upper", 41),
    ("upper", 221),
    ("upper", 304),
    ("lower", 4),
    ("lower", 14),
    ("lower", 151),
    ("lower", 202),
    ("lower", 245),
    ("lower", 275),
    ("lower", 311),
    ("lower", 314),
    ("lower", 316),
]


def main() -> int:
    registry = json.loads((ROOT / "source_registry.json").read_text(encoding="utf-8"))
    sources = {source["volume"]: source["path"] for source in registry["sources"]}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    documents: dict[str, fitz.Document] = {}
    try:
        for volume, page_number in SAMPLES:
            document = documents.setdefault(volume, fitz.open(sources[volume]))
            output = OUTPUT / f"{volume}_p{page_number:04d}.png"
            document[page_number - 1].get_pixmap(dpi=140, alpha=False).save(output)
            print(output)
    finally:
        for document in documents.values():
            document.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
