"""Shared COM navigation helpers for tools modules.

All functions must be called ON the COM thread (i.e. inside aspen.call()).
"""

from __future__ import annotations

from typing import Any


def walk(root: Any, *parts: str) -> Any | None:
    """Navigate an IHNode tree by path segments.

    Safe to call from within an aspen.call() lambda on the COM thread.
    """
    node = root
    for p in parts:
        try:
            node = node.Elements(p)
        except Exception:
            return None
        if node is None:
            return None
    return node

def set_table_label(root, path: str, dimension: int, index: int, label: str) -> bool:
    """Set a label on a table-type node via pywin32 wrapper's SetLabel method.
    """
    parts = path.replace("/", "\\").strip("\\").split("\\")
    node = walk(root, *parts)
    if node is None:
        return False
    try:
        els = node.Elements
        els.SetLabel(dimension, index, False, label)
        return True
    except Exception:
        return False


def ensure_parent(tree: Any, *parts: str) -> Any | None:
    """Ensure a path exists, creating intermediate nodes as needed.

    Handles the dummy-node trick for Blocks/Streams containers:
    creating a temporary child forces Aspen to allocate the container node
    when it would otherwise refuse direct .Add().
    """
    node = tree
    for p in parts:
        try:
            n = node.Elements(p)
            if n is None:
                raise Exception("none")
            node = n
        except Exception:
            try:
                node.Elements.Add(p)
                node = node.Elements(p)
            except Exception:
                # Dummy trick for Data-level containers
                name = parts[-1] if len(parts) > 0 else p
                try:
                    if name == "Blocks":
                        node.Elements.Add("_d_!MIXER")
                        node = node.Elements("Blocks")
                        node.Elements.Remove("_d_")
                        return node
                    elif name == "Streams":
                        node.Elements.Add("_d_")
                        node = node.Elements("Streams")
                        node.Elements.Remove("_d_")
                        return node
                except Exception:
                    pass
                return None
    return node


def child_names(root: Any, *parts: str, max_keys: int = 10000) -> list[str]:
    """Return the .Name of every child at *path* under *root*."""
    node = walk(root, *parts) if parts else root
    if node is None:
        return []
    names: list[str] = []
    for i in range(max_keys):
        try:
            child = node.Elements(i)
        except Exception:
            break
        if child is None:
            break
        names.append(child.Name)
    return names


def list_child_names(node: Any, max_items: int = 10000) -> list[str]:
    """Return the .Name of every direct child of *node*."""
    if node is None:
        return []
    names: list[str] = []
    for i in range(max_items):
        try:
            child = node.Elements(i)
        except Exception:
            break
        if child is None:
            break
        names.append(child.Name)
    return names


def read_scalars(node: Any, max_keys: int = 64) -> dict[str, Any]:
    """Read scalar values from a node into {Name: Value} dict.

    Skips children with ValueType == 0 (non-scalar / container nodes).
    """
    if node is None:
        return {}
    data: dict[str, Any] = {}
    seen = 0
    for i in range(10_000):
        try:
            c = node.Elements(i)
        except Exception:
            break
        if c is None:
            break
        if c.ValueType == 0:
            continue
        data[c.Name] = c.Value
        seen += 1
        if seen >= max_keys:
            break
    return data
