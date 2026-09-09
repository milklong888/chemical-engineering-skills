#!/usr/bin/env python3
"""Validate the Aspen Plus manual-backed operation knowledge graph."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GRAPH_PATH = ROOT / "references" / "manual_knowledge_graph.json"
REQUIRED_NODE_KEYS = {
    "id",
    "labels",
    "applies_to",
    "manual_sources",
    "card_fields",
    "meaning",
    "required_evidence",
    "failure_traps",
}


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def load_graph() -> dict[str, Any]:
    with GRAPH_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    graph = load_graph()
    nodes = graph.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        fail("graph.nodes must be a non-empty list")

    ids: set[str] = set()
    missing_paths: list[tuple[str, str]] = []
    missing_keys: list[tuple[str, str]] = []
    dangling: list[tuple[str, str]] = []

    for node in nodes:
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id:
            fail("every node must have a non-empty string id")
        if node_id in ids:
            fail(f"duplicate node id: {node_id}")
        ids.add(node_id)

        for key in sorted(REQUIRED_NODE_KEYS):
            if key not in node:
                missing_keys.append((node_id, key))

        for source in node.get("manual_sources", []):
            source_path = source.get("path")
            if source_path and not Path(source_path).exists():
                missing_paths.append((node_id, source_path))

    for node in nodes:
        node_id = node["id"]
        for rel in node.get("relationships", []):
            target = rel.get("target")
            if target not in ids:
                dangling.append((node_id, str(target)))

    if missing_keys:
        fail("missing keys: " + ", ".join(f"{n}:{k}" for n, k in missing_keys))
    if missing_paths:
        fail("missing manual paths: " + ", ".join(f"{n}:{p}" for n, p in missing_paths))
    if dangling:
        fail("dangling relationships: " + ", ".join(f"{n}->{t}" for n, t in dangling))

    print(f"OK nodes={len(nodes)} graph={GRAPH_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
