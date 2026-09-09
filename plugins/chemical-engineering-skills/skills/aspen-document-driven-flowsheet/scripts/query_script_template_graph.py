#!/usr/bin/env python3
"""Query the Aspen script-template knowledge graph."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
GRAPH_PATH = SKILL_DIR / "references" / "script_template_knowledge_graph.json"


def load_graph(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def match_node(node: dict, args: argparse.Namespace) -> bool:
    if args.node_id and node.get("id") != args.node_id:
        return False
    if args.cluster and node.get("cluster") != args.cluster:
        return False
    if args.search:
        haystack = " ".join(str(node.get(key, "")) for key in ("id", "cluster", "name", "base")).lower()
        if args.search.lower() not in haystack:
            return False
    return True


def print_nodes(nodes: list[dict]) -> None:
    for node in nodes:
        next_ids = ",".join(node.get("next", []))
        print(f"{node['id']}\t{node['cluster']}\t{node['name']}\tbase={node['base']}\tnext={next_ids}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Query script template graph nodes and canonical paths.")
    parser.add_argument("--graph", default=str(GRAPH_PATH))
    parser.add_argument("--id", dest="node_id")
    parser.add_argument("--cluster")
    parser.add_argument("--search")
    parser.add_argument("--path-name", help="Print a canonical path such as new_build, repair, tower_island, delivery, script_reuse.")
    parser.add_argument("--json", action="store_true", help="Emit matching nodes as JSON.")
    args = parser.parse_args()

    graph = load_graph(Path(args.graph))
    if args.path_name:
        path = graph.get("canonical_paths", {}).get(args.path_name)
        if path is None:
            choices = ", ".join(sorted(graph.get("canonical_paths", {}).keys()))
            raise SystemExit(f"Unknown path name {args.path_name!r}. Choices: {choices}")
        if args.json:
            print(json.dumps({"path_name": args.path_name, "nodes": path}, ensure_ascii=False, indent=2))
        else:
            print(" -> ".join(path))
        return 0

    nodes = [node for node in graph.get("nodes", []) if match_node(node, args)]
    if args.json:
        print(json.dumps(nodes, ensure_ascii=False, indent=2))
    else:
        print_nodes(nodes)
    return 0 if nodes else 2


if __name__ == "__main__":
    raise SystemExit(main())
