from __future__ import annotations

import argparse
import inspect
import json
import os
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


def scalar(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return repr(value)


def dispatch_surface(value: Any) -> dict[str, Any]:
    if value is None:
        return {"exists": False}
    names: list[str] = []
    try:
        names = sorted(
            name
            for name in dir(value)
            if not name.startswith("_")
        )
    except Exception:
        pass
    methods: dict[str, Any] = {}
    for name in (
        "Add",
        "Insert",
        "InsertRow",
        "Item",
        "Remove",
        "RemoveRow",
        "SetItemName",
    ):
        try:
            method = getattr(value, name)
        except Exception:
            continue
        try:
            signature = str(inspect.signature(method))
        except Exception as exc:
            signature = f"UNAVAILABLE:{type(exc).__name__}"
        methods[name] = {
            "signature": signature,
            "doc": getattr(method, "__doc__", None),
            "repr": repr(method),
        }
    return {
        "exists": True,
        "python_type": type(value).__name__,
        "public_names": names,
        "has_add": hasattr(value, "Add"),
        "has_remove": hasattr(value, "Remove"),
        "has_item": hasattr(value, "Item"),
        "has_count": hasattr(value, "Count"),
        "methods": methods,
    }


def walk(root: Any, root_path: str, max_nodes: int) -> list[dict[str, Any]]:
    if root is None:
        return []
    result: list[dict[str, Any]] = []
    stack: list[tuple[Any, str]] = [(root, root_path)]
    while stack and len(result) < max_nodes:
        node, path = stack.pop()
        children = aspen.node_elements(node)
        result.append({
            "path": path,
            "name": aspen.node_name(node),
            "value": scalar(aspen.node_value(node)),
            "unit": aspen.node_unit(node),
            "value_type": aspen.node_value_type(node),
            "child_count": len(children),
        })
        for child in reversed(children):
            name = aspen.node_name(child).strip()
            if name:
                stack.append((child, path + "\\" + name))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only focused probe of Aspen report and property-set COM configuration."
    )
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-nodes-per-root", type=int, default=20000)
    args = parser.parse_args()

    source = args.source.expanduser().resolve()
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if not source.is_file():
        raise SystemExit(f"source does not exist: {source}")

    import pythoncom

    app = None
    previous_cwd = Path.cwd()
    probe_root = Path(tempfile.mkdtemp(prefix="EquipmentDesignAspenConfigProbe_"))
    staged = probe_root / f"SOURCE{source.suffix.lower()}"
    shutil.copy2(source, staged)
    aspen.stage_aspen_sidecars(source, staged)
    lock = aspen.WORKSPACE_ROOT / "_aspen_com_global.lock"
    aspen.WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "schema": "aspen-com-configuration-probe-v1",
        "source_path": str(source),
        "source_sha256": aspen.sha256(source),
        "read_only_source": True,
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
            for root_path in (
                r"\Data\Setup",
                r"\Data\Properties\Prop-Sets",
                r"\Data\Properties\Analysis",
            ):
                root = aspen.find_node(app.Tree, root_path)
                nodes = walk(
                    root,
                    root_path,
                    max(1, int(args.max_nodes_per_root)),
                )
                elements = getattr(root, "Elements", None) if root is not None else None
                result["roots"].append({
                    "path": root_path,
                    "exists": root is not None,
                    "node_count": len(nodes),
                    "truncated": len(nodes) >= max(1, int(args.max_nodes_per_root)),
                    "node_surface": dispatch_surface(root),
                    "elements_surface": dispatch_surface(elements),
                    "nodes": nodes,
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
        "node_count": sum(root["node_count"] for root in result["roots"]),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
