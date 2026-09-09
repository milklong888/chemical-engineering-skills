from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
PACKAGE_ROOT = SCRIPT_PATH.parents[1]
APP_DIR = PACKAGE_ROOT / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import aspen_com_import as aspen  # noqa: E402


MATCH = re.compile(r"(MUMX|VISC|TXPORT)", re.IGNORECASE)


def node_snapshot(node: Any, path: str) -> dict[str, Any]:
    value = aspen.node_value(node)
    if not isinstance(value, (str, int, float, bool)) and value is not None:
        value = repr(value)
    record_type, record_type_source = aspen.node_record_type(node)
    return {
        "path": path,
        "name": aspen.node_name(node),
        "value": value,
        "unit": aspen.node_unit(node),
        "value_type": aspen.node_value_type(node),
        "record_type": record_type,
        "record_type_source": record_type_source,
        "compstatus": aspen.node_compstatus(node),
    }


def walk_matching_nodes(
    root: Any,
    root_path: str,
    *,
    max_depth: int,
    max_nodes: int,
    max_matches: int,
) -> tuple[list[dict[str, Any]], int, bool]:
    if root is None:
        return [], 0, False
    matches: list[dict[str, Any]] = []
    visited = 0
    truncated = False
    stack: list[tuple[Any, str, int]] = [(root, root_path, 0)]
    while stack:
        node, path, depth = stack.pop()
        visited += 1
        if visited > max_nodes:
            truncated = True
            break
        if MATCH.search(aspen.node_name(node)) or MATCH.search(path):
            matches.append(node_snapshot(node, path))
            if len(matches) >= max_matches:
                truncated = True
                break
        if depth >= max_depth:
            continue
        children = aspen.node_elements(node)
        for child in reversed(children):
            name = aspen.node_name(child).strip()
            if name:
                stack.append((child, path + "\\" + name, depth + 1))
    return matches, visited, truncated


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only Aspen tree probe for transport-property result nodes."
    )
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-depth", type=int, default=12)
    parser.add_argument("--max-nodes", type=int, default=250000)
    args = parser.parse_args()

    source = args.source.expanduser().resolve()
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if not source.is_file():
        raise SystemExit(f"source does not exist: {source}")

    import pythoncom

    app = None
    previous_cwd = Path.cwd()
    probe_root = Path(tempfile.mkdtemp(prefix="EquipmentDesignAspenProbe_"))
    staged = probe_root / f"SOURCE{source.suffix.lower()}"
    shutil.copy2(source, staged)
    aspen.stage_aspen_sidecars(source, staged)
    lock = aspen.WORKSPACE_ROOT / "_aspen_com_global.lock"
    aspen.WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "schema": "aspen-transport-property-tree-probe-v1",
        "source_path": str(source),
        "source_sha256": aspen.sha256(source),
        "read_only_source": True,
        "pattern": MATCH.pattern,
        "roots": [],
    }
    try:
        with aspen.AspenLock(lock):
            pythoncom.CoInitialize()
            os.chdir(probe_root)
            app, progid = aspen.create_aspen()
            open_method, open_errors = aspen.open_case(app, staged)
            result["progid"] = progid
            result["open_method"] = open_method
            result["open_errors"] = open_errors
            root_paths = (
                r"\Data\Streams",
                r"\Data\Results Summary",
                r"\Data\Properties",
                r"\Data",
            )
            for root_path in root_paths:
                root = aspen.find_node(app.Tree, root_path)
                matches, visited, truncated = walk_matching_nodes(
                    root,
                    root_path,
                    max_depth=max(1, int(args.max_depth)),
                    max_nodes=max(1, int(args.max_nodes)),
                    max_matches=2000,
                )
                result["roots"].append({
                    "path": root_path,
                    "exists": root is not None,
                    "top_level_children": [
                        aspen.node_name(child)
                        for child in aspen.node_elements(root)
                        if aspen.node_name(child)
                    ][:500],
                    "visited_nodes": visited,
                    "truncated": truncated,
                    "matches": matches,
                })
    finally:
        aspen.close_aspen(app)
        os.chdir(previous_cwd)
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass
        shutil.rmtree(probe_root, ignore_errors=True)

    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "PASS",
        "output": str(output),
        "match_count": sum(len(root["matches"]) for root in result["roots"]),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
