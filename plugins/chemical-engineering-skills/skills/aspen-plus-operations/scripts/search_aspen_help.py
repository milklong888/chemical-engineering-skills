#!/usr/bin/env python3
"""Search local Aspen Plus V14 HtmlHelp pages for card-rule evidence."""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path


DEFAULT_ROOT = Path(
    "C:/ProgramData/AspenTech/Aspen Plus V14.0/HtmlHelp/Subsystems"
)


def clean_text(raw: str) -> str:
    raw = re.sub(r"<(script|style)\b.*?</\1>", " ", raw, flags=re.I | re.S)
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    raw = re.sub(r"\s+", " ", raw)
    return raw.strip()


def title_from(raw: str, path: Path) -> str:
    match = re.search(r"<title>(.*?)</title>", raw, flags=re.I | re.S)
    if match:
        return clean_text(match.group(1))
    match = re.search(r"<h[1-3][^>]*>(.*?)</h[1-3]>", raw, flags=re.I | re.S)
    if match:
        return clean_text(match.group(1))
    return path.stem


def snippets(text: str, terms: list[str], limit: int) -> list[str]:
    lowered = text.lower()
    spans: list[tuple[int, int]] = []
    for term in terms:
        idx = lowered.find(term.lower())
        if idx >= 0:
            spans.append((max(0, idx - 120), min(len(text), idx + len(term) + 160)))
    out: list[str] = []
    for start, end in sorted(spans)[:limit]:
        snippet = text[start:end].strip()
        if snippet and snippet not in out:
            out.append(snippet)
    return out


def score_page(path: Path, title: str, text: str, terms: list[str]) -> int:
    blob = f"{path.as_posix()} {title} {text}".lower()
    title_blob = title.lower()
    path_blob = path.as_posix().lower()
    score = 0
    for term in terms:
        t = term.lower()
        if t in title_blob:
            score += 12
        if t in path_blob:
            score += 8
        score += min(blob.count(t), 8)
    return score


def search(root: Path, terms: list[str], max_results: int, snippet_count: int) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for path in root.rglob("*.htm"):
        try:
            raw = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        text = clean_text(raw)
        title = title_from(raw, path)
        if not all(term.lower() in f"{path} {title} {text}".lower() for term in terms):
            continue
        score = score_page(path, title, text, terms)
        if score <= 0:
            continue
        results.append(
            {
                "score": score,
                "title": title,
                "path": path.as_posix(),
                "snippets": snippets(text, terms, snippet_count),
            }
        )
    results.sort(key=lambda row: (-int(row["score"]), str(row["path"]).lower()))
    return results[:max_results]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Search local Aspen Plus V14 HtmlHelp pages."
    )
    parser.add_argument("terms", nargs="+", help="Terms that must all match")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="HtmlHelp root")
    parser.add_argument("--max", type=int, default=12, help="Maximum results")
    parser.add_argument("--snippets", type=int, default=2, help="Snippets per result")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args()

    if not args.root.exists():
        raise SystemExit(f"ERROR: help root not found: {args.root}")

    matches = search(args.root, args.terms, args.max, args.snippets)
    if args.json:
        print(json.dumps(matches, ensure_ascii=False, indent=2))
    else:
        print(f"root: {args.root}")
        print(f"matches: {len(matches)}")
        for item in matches:
            print()
            print(f"## {item['title']}")
            print(f"score: {item['score']}")
            print(f"path: {item['path']}")
            for snippet in item["snippets"]:
                print(f"- {snippet}")
    return 0 if matches else 1


if __name__ == "__main__":
    raise SystemExit(main())
