# -*- coding: utf-8 -*-
"""Query the local vector index for the Aspen Plus V10 user-guide graph."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

from vectorize_user_guide_graph import (
    VECTOR_DIR,
    VECTORS_NPY,
    RECORDS_JSONL,
    CONFIG_PATH,
    document_text,
    normalize_text,
    tokenise,
    vectorize_text,
)


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def load_records(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def compact(text: str, limit: int = 320) -> str:
    text = re.sub(r"\s+", " ", str(text)).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def ensure_index() -> None:
    if VECTORS_NPY.exists() and RECORDS_JSONL.exists() and CONFIG_PATH.exists():
        return
    raise SystemExit(
        "Vector index is missing. Build it first:\n"
        "python aspen_user_guide_v10_knowledge\\scripts\\vectorize_user_guide_graph.py"
    )


def lexical_bonus(query: str, record: dict) -> float:
    haystack = normalize_text(
        " ".join(
            [
                str(record.get("node_id", "")),
                str(record.get("title", "")),
                " ".join(record.get("routes", [])),
                " ".join(record.get("kind", [])),
                " ".join(record.get("keywords", [])),
                str(record.get("text", "")),
            ]
        )
    )
    query_norm = normalize_text(query)
    bonus = 0.0
    if query_norm and query_norm in haystack:
        bonus += 0.08
    seen = set()
    for token in tokenise(query_norm):
        token_norm = normalize_text(token)
        if not token_norm or token_norm in seen:
            continue
        seen.add(token_norm)
        if token_norm in haystack:
            bonus += 0.018 if len(token_norm) <= 3 else 0.03
    return min(bonus, 0.22)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("terms", nargs="*", help="Query terms.")
    parser.add_argument("--limit", type=int, default=10, help="Maximum results.")
    parser.add_argument("--json", action="store_true", help="Print JSON results.")
    parser.add_argument("--ids", action="store_true", help="Print only vector/node IDs.")
    parser.add_argument(
        "--scope",
        choices=["all", "chapter", "detail", "page-fallback"],
        default="all",
        help="Restrict result scope.",
    )
    args = parser.parse_args()

    if not args.terms:
        parser.print_help()
        return 2

    ensure_index()
    query = " ".join(args.terms)
    records = load_records(RECORDS_JSONL)
    vectors = np.load(VECTORS_NPY)
    if len(records) != vectors.shape[0]:
        raise SystemExit(f"Index mismatch: {len(records)} records but {vectors.shape[0]} vectors")

    qvec = vectorize_text(query, dim=vectors.shape[1])
    scores = vectors @ qvec

    results = []
    for idx, score in enumerate(scores.tolist()):
        record = records[idx]
        if args.scope != "all" and record.get("scope") != args.scope:
            continue
        adjusted = float(score) + lexical_bonus(query, record)
        if record.get("scope") == "detail":
            adjusted += 0.015
        elif record.get("scope") == "chapter":
            adjusted += 0.005
        elif record.get("scope") == "page-fallback":
            adjusted -= 0.01
        result = dict(record)
        result["score"] = adjusted
        result["raw_cosine"] = float(score)
        results.append(result)

    results.sort(key=lambda item: item["score"], reverse=True)
    results = results[: max(args.limit, 1)]

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0
    if args.ids:
        print("\n".join(str(item["node_id"]) for item in results))
        return 0

    for item in results:
        print(f"{item['node_id']} | score {item['score']:.4f} | cosine {item['raw_cosine']:.4f} | {item['scope']}")
        if item.get("chapter_node_id"):
            print(f"  chapter: {item['chapter_node_id']} {item['title']}")
        else:
            print(f"  title: {item['title']}")
        print(f"  page: {item.get('page', '')}")
        print(f"  routes: {', '.join(item.get('routes', []))}")
        print(f"  kind: {', '.join(item.get('kind', []))}")
        print(f"  source: {item.get('source', '')}")
        print(f"  extract: {item.get('extract', '')}")
        print(f"  text: {compact(item.get('text', ''))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
