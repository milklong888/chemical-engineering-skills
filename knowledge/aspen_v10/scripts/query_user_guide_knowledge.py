# -*- coding: utf-8 -*-
"""Query the Aspen Plus V10 user-guide chapter graph."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "manifest.json"
DETAIL_RECORDS_PATH = ROOT / "knowledge_graph" / "operation_detail_records.json"


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold())


def score_chapter(chapter: dict, terms: list[str]) -> tuple[int, list[str]]:
    haystack_parts = [
        chapter.get("node_id", ""),
        chapter.get("title", ""),
        " ".join(chapter.get("routes", [])),
        " ".join(chapter.get("triggers", [])),
        " ".join(chapter.get("headings", [])),
    ]
    haystack = normalize(" ".join(haystack_parts))
    score = 0
    matches: list[str] = []
    for raw_term in terms:
        term = normalize(raw_term)
        if not term:
            continue
        if re.fullmatch(r"[a-z0-9_+-]{1,3}", term):
            count = len(re.findall(rf"(?<![a-z0-9_+-]){re.escape(term)}(?![a-z0-9_+-])", haystack))
        else:
            count = haystack.count(term)
        if count:
            score += count * (4 if term in normalize(chapter.get("title", "")) else 1)
            matches.append(raw_term)
    return score, matches


def score_text(haystack_text: str, title_text: str, terms: list[str]) -> tuple[int, list[str]]:
    haystack = normalize(haystack_text)
    title = normalize(title_text)
    score = 0
    matches: list[str] = []
    for raw_term in terms:
        term = normalize(raw_term)
        if not term:
            continue
        if re.fullmatch(r"[a-z0-9_+-]{1,3}", term):
            count = len(re.findall(rf"(?<![a-z0-9_+-]){re.escape(term)}(?![a-z0-9_+-])", haystack))
        else:
            count = haystack.count(term)
        if count:
            score += count * (4 if term in title else 1)
            matches.append(raw_term)
    if matches and len(matches) == len([term for term in terms if normalize(term)]):
        score += len(matches) * 3
    return score, matches


def score_detail(record: dict, terms: list[str]) -> tuple[int, list[str]]:
    haystack_parts = [
        record.get("node_id", ""),
        record.get("chapter_node_id", ""),
        record.get("chapter_title", ""),
        " ".join(record.get("kind", [])),
        " ".join(record.get("routes", [])),
        " ".join(record.get("keywords", [])),
        record.get("text", ""),
    ]
    score, matches = score_text(" ".join(haystack_parts), record.get("chapter_title", ""), terms)
    if "page-source-fallback" in record.get("kind", []):
        score = max(score // 4, 1) if score > 0 else 0
    return score, matches


def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        raise SystemExit(f"Missing manifest. Rebuild first: {ROOT / 'scripts' / 'build_user_guide_graph.py'}")
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def load_detail_records() -> list[dict]:
    if not DETAIL_RECORDS_PATH.exists():
        return []
    return json.loads(DETAIL_RECORDS_PATH.read_text(encoding="utf-8"))


def compact_text(text: str, limit: int = 280) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("terms", nargs="*", help="Keywords, operation routes, or Chinese terms to search.")
    parser.add_argument("--ids", action="store_true", help="Print only matching node IDs.")
    parser.add_argument("--json", action="store_true", help="Print JSON results.")
    parser.add_argument("--limit", type=int, default=10, help="Maximum matches to show.")
    parser.add_argument(
        "--scope",
        choices=["all", "details", "chapters"],
        default="all",
        help="Search detail records, chapter records, or both.",
    )
    args = parser.parse_args()

    if not args.terms:
        parser.print_help()
        return 2

    manifest = load_manifest()
    results = []

    if args.scope in {"all", "details"}:
        for record in load_detail_records():
            score, matches = score_detail(record, args.terms)
            if score <= 0:
                continue
            results.append(
                {
                    "scope": "detail",
                    "score": score,
                    "matches": matches,
                    "node_id": record["node_id"],
                    "chapter_node_id": record["chapter_node_id"],
                    "title": record["chapter_title"],
                    "page": record["page"],
                    "kind": record.get("kind", []),
                    "routes": record.get("routes", []),
                    "keywords": record.get("keywords", []),
                    "text": compact_text(record.get("text", "")),
                    "detail_index": record.get("detail_index", ""),
                    "extract_file": record.get("source_extract", ""),
                }
            )

    if args.scope in {"all", "chapters"}:
        for chapter in manifest.get("chapters", []):
            score, matches = score_chapter(chapter, args.terms)
            if score <= 0:
                continue
            results.append(
                {
                    "scope": "chapter",
                    "score": score,
                    "matches": matches,
                    "node_id": chapter["node_id"],
                    "title": chapter["title"],
                    "pages": f"{chapter['start_page']}-{chapter['end_page']}",
                    "routes": chapter.get("routes", []),
                    "node_file": chapter["node_file"],
                    "extract_file": chapter["extract_file"],
                }
            )
    results.sort(key=lambda item: (-item["score"], item["node_id"]))
    results = results[: max(args.limit, 1)]

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0
    if args.ids:
        print("\n".join(item["node_id"] for item in results))
        return 0

    for item in results:
        if item["scope"] == "detail":
            print(f"{item['node_id']} | page {item['page']} | score {item['score']} | detail")
            print(f"  chapter: {item['chapter_node_id']} {item['title']}")
            print(f"  kinds: {', '.join(item['kind'])}")
            print(f"  routes: {', '.join(item['routes'])}")
            print(f"  detail_index: {item['detail_index']}")
            print(f"  extract: {item['extract_file']}")
            print(f"  text: {item['text']}")
            print(f"  matches: {', '.join(item['matches'])}")
        else:
            print(f"{item['node_id']} | pages {item['pages']} | score {item['score']} | chapter")
            print(f"  title: {item['title']}")
            print(f"  routes: {', '.join(item['routes'])}")
            print(f"  node: {item['node_file']}")
            print(f"  extract: {item['extract_file']}")
            print(f"  matches: {', '.join(item['matches'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
