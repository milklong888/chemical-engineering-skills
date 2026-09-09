#!/usr/bin/env python3
"""Locate the active workspace and run the provenance-rich standards query."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def find_workspace(start: Path) -> Path:
    candidates = [start.resolve(), *start.resolve().parents, Path.cwd().resolve(), *Path.cwd().resolve().parents]
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if (candidate / "LOCAL_KNOWLEDGE_GRAPH_LINKS.md").is_file():
            return candidate
    raise FileNotFoundError("workspace root with LOCAL_KNOWLEDGE_GRAPH_LINKS.md was not found")


def main() -> int:
    workspace = find_workspace(Path(__file__))
    query_script = workspace / "设备设计选型工作包" / "knowledge_graph" / "standards_graph" / "scripts" / "query_standard_knowledge.py"
    if not query_script.is_file():
        raise FileNotFoundError(query_script)
    forwarded = list(sys.argv[1:])
    if "--family" not in forwarded:
        forwarded.extend(["--family", "tower"])
    return subprocess.call([sys.executable, str(query_script), *forwarded], cwd=workspace)


if __name__ == "__main__":
    raise SystemExit(main())
