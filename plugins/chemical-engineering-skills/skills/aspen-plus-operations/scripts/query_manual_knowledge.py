#!/usr/bin/env python3
"""Query the Aspen Plus manual-backed operation knowledge graph."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GRAPH_PATH = ROOT / "references" / "manual_knowledge_graph.json"


def load_graph() -> dict[str, Any]:
    with GRAPH_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def node_text(node: dict[str, Any]) -> str:
    parts: list[str] = []
    for key, value in node.items():
        if key == "manual_sources":
            for src in value:
                parts.extend(str(src.get(k, "")) for k in ("path", "title", "evidence"))
        elif isinstance(value, str):
            parts.append(value)
        elif isinstance(value, list):
            parts.append(json.dumps(value, ensure_ascii=False))
        elif isinstance(value, dict):
            parts.append(json.dumps(value, ensure_ascii=False))
    return " ".join(parts).lower()


def find_nodes(graph: dict[str, Any], terms: list[str]) -> list[dict[str, Any]]:
    if not terms:
        return list(graph["nodes"])
    lowered = [t.lower() for t in terms]
    matches = []
    for node in graph["nodes"]:
        haystack = node_text(node)
        node_id = node.get("id", "").lower()
        labels = " ".join(node.get("labels", [])).lower()
        if all(term in haystack or term in node_id or term in labels for term in lowered):
            matches.append(node)
    matches.sort(key=lambda node: (-score_node(node, lowered), node.get("id", "")))
    return matches


def score_node(node: dict[str, Any], terms: list[str]) -> int:
    node_id = node.get("id", "").lower()
    labels = " ".join(node.get("labels", [])).lower()
    applies = " ".join(node.get("applies_to", [])).lower()
    fields = " ".join(node.get("card_fields", [])).lower()
    source_titles = " ".join(
        str(src.get("title", "")) for src in node.get("manual_sources", [])
    ).lower()
    all_text = node_text(node)
    score = 0
    for term in terms:
        if term in node_id:
            score += 30
        if term in labels:
            score += 20
        if term in source_titles:
            score += 12
        if term in applies:
            score += 8
        if term in fields:
            score += 6
        score += min(all_text.count(term), 5)
    return score


def compact_node(node: dict[str, Any]) -> str:
    lines = [f"## {node['id']}"]
    labels = ", ".join(node.get("labels", []))
    if labels:
        lines.append(f"labels: {labels}")
    applies = ", ".join(node.get("applies_to", []))
    if applies:
        lines.append(f"applies_to: {applies}")

    sources = node.get("manual_sources", [])
    if sources:
        lines.append("manual_sources:")
        for src in sources:
            lines.append(f"- {src.get('title', 'source')}: {src.get('path', '')}")
            evidence = src.get("evidence")
            if evidence:
                lines.append(f"  evidence: {evidence}")

    fields = node.get("card_fields", [])
    if fields:
        lines.append("card_fields:")
        lines.extend(f"- {field}" for field in fields)

    meaning = node.get("meaning", {})
    if meaning:
        lines.append("meaning:")
        for key, value in meaning.items():
            lines.append(f"- {key}: {value}")

    units = node.get("units_and_basis", [])
    if units:
        lines.append("units_and_basis:")
        lines.extend(f"- {item}" for item in units)

    required = node.get("required_evidence", [])
    if required:
        lines.append("required_evidence:")
        lines.extend(f"- {item}" for item in required)

    traps = node.get("failure_traps", [])
    if traps:
        lines.append("failure_traps:")
        lines.extend(f"- {item}" for item in traps)

    related = node.get("relationships", [])
    if related:
        lines.append("relationships:")
        for rel in related:
            lines.append(f"- {rel.get('type')}: {rel.get('target')}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Query manual-backed Aspen Plus operation rules."
    )
    parser.add_argument("terms", nargs="*", help="Search terms or node-id fragments")
    parser.add_argument("--json", action="store_true", help="Emit matching nodes as JSON")
    parser.add_argument("--ids", action="store_true", help="Emit only matching node ids")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of matches")
    args = parser.parse_args()

    graph = load_graph()
    matches = find_nodes(graph, args.terms)
    if args.limit:
        matches = matches[: args.limit]
    if args.ids:
        for node in matches:
            print(node["id"])
    elif args.json:
        print(json.dumps(matches, ensure_ascii=False, indent=2))
    else:
        print(f"graph: {GRAPH_PATH}")
        print(f"matches: {len(matches)}")
        for node in matches:
            print()
            print(compact_node(node))
    return 0 if matches else 1


if __name__ == "__main__":
    raise SystemExit(main())
