"""Block tools: list, get, set params, add, remove, explore.

All COM operations run inside aspen.call() lambdas on the dedicated
COM apartment thread.
"""

from __future__ import annotations

from typing import Any

from ..com_bridge import aspen


def _walk(root, *parts):
    node = root
    for p in parts:
        try:
            node = node.Elements(p)
        except Exception:
            return None
    return node


def _read_block_table_on_com(node: Any) -> dict[str, Any]:
    """Read IHNode tree into a plain dict (called on COM thread)."""
    def _group(n):
        d = {}
        for i in range(10000):
            try:
                c = n.Elements(i)
            except Exception:
                break
            if c is None:
                break
            d[c.Name] = c
        return d

    data: dict[str, Any] = {}
    for child_name, child in _group(node).items():
        if child.ValueType != 0:
            data[child_name] = child.Value
        else:
            sub = _group(child)
            sub_data: dict[str, Any] = {}
            for sn, sv in sub.items():
                if sv.ValueType != 0:
                    sub_data[sn] = sv.Value
            if sub_data:
                data[child_name] = sub_data
            else:
                data[child_name] = {}
    return data


def tool_list_all_blocks() -> list[str]:
    """List all block names in the flowsheet."""
    try:
        def impl():
            tree = aspen._app.RootModel("")
            blk_node = _walk(tree, "Data", "Blocks")
            if blk_node is None:
                return ["(no Blocks node)"]
            comps = []
            for i in range(10000):
                try:
                    c = blk_node.Elements(i)
                except Exception:
                    break
                if c is None:
                    break
                comps.append(c.Name)
            return comps
        return aspen.call(impl)
    except Exception as exc:
        return [f"Error: {exc}"]


def tool_get_block(name: str) -> dict[str, Any]:
    """Read block specifications and key results."""
    try:
        def impl():
            result: dict[str, Any] = {"name": name}
            tree = aspen._app.RootModel("")
            blk = _walk(tree, "Data", "Blocks", name)
            if blk is None:
                return {"error": f"Block '{name}' not found"}
            result["type"] = blk.Value

            for section in ("Input", "Output", "Subobjects", "Connections", "Ports"):
                node = _walk(tree, "Data", "Blocks", name, section)
                if node is not None:
                    result[section.lower()] = _read_block_table_on_com(node)

            return result
        return aspen.call(impl)
    except Exception as exc:
        return {"error": str(exc)}


_VALVE_ALIASES = {
    "PRES": "P_OUT",
    "PRES1": "P_OUT",
}

def tool_set_param(block_name: str, param: str, value: str | float) -> str:
    """Set a block parameter (e.g. TEMP, PRES, DUTY).

    Automatically detects unit and range via AttributeValue metadata.
    Response includes [unit] and range=(min, max) when available.

    Args:
        block_name: Block name (e.g. 'B1', 'E-1').
        param: Parameter name (e.g. 'TEMP', 'PRES', 'SPEC_OPT').
        value: Numeric value or string (e.g. 150, 'TP').

    Returns confirmation with unit hint, or error if param not found.
    Note: Use set_stream_param() for stream parameters, NOT this tool.
    """
    try:
        def impl():
            tree = aspen._app.RootModel("")
            node = _walk(tree, "Data", "Blocks", block_name, "Input", param)
            if node is None:
                alias = _VALVE_ALIASES.get(param)
                if alias:
                    node = _walk(tree, "Data", "Blocks", block_name, "Input", alias)
                    if node is not None:
                        node.SetValue(0, value)
                        return f"Set {block_name}.{alias} = {value} (via alias '{param}')"
                return f"Could not set {block_name}.{param}"
            node.SetValue(0, value)
            
            # Try to read unit info (non-critical)
            context = ""
            try:
                i3 = node.AttributeValue(3)   # unit group code
                i8 = node.AttributeValue(8)   # max
                i9 = node.AttributeValue(9)   # min
                unit_map = {5: "bar", 10: "kPa", 4: "degC", 3: "Gcal/hr",
                            18: "kW", 7: "m", 1: "m3/hr"}
                unit = unit_map.get(i3, "")
                if unit:
                    context = f" [{unit}]"
                    if i9 is not None and i8 is not None:
                        context += f" range=({i9}, {i8})"
            except Exception:
                pass
            
            return f"Set {block_name}.{param} = {value}{context}"
        return aspen.call(impl)
    except Exception as exc:
        exc_str = str(exc)
        if "AE_UNDERSPEC" in exc_str or "MIXED" in exc_str:
            return (
                f"Error: '{param}' may be a stream parameter.\n"
                f"Stream parameters must use set_stream_param(), not set_param().\n"
                f"Example: set_stream_param('{block_name}', '{param}', {value})"
            )
        return f"Error: {exc}"


def _ensure_parent(tree, *parts):
    """Ensure a path exists, creating nodes as needed."""
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


def tool_add_block(name: str, block_type: str) -> str:
    """Add a block to the flowsheet.

    Creates a new block of the given type. The block is added with
    default parameters (none set).

    Args:
        name: Block name (e.g. 'B1'). Must be unique.
        block_type: Aspen block type string. Common types:
            HEATER, MIXER, FLASH2, DECANTER, FSFLIT,
            RADFRAC (RadFrac), ABSBR1 (absorber),
            RGIBBS (Gibbs reactor), RSTOIC (stoichiometric),
            COMPR, MCOMPR, VALVE, HEATX,
            ICON1 (pump), ICON2 (compressor),
            TRIANGLE (mixer), V-DRUM1 (flash), VALVE2 (valve).

    Note: RPLUG/RCSTR cannot be fully configured via COM (RXN_ID issue).
    Use RGIBBS for reaction simulations instead.
    """
    try:
        def impl():
            tree = aspen._app.RootModel("")
            blk_node = _walk(tree, "Data", "Blocks")
            if blk_node is None:
                blk_node = _ensure_parent(tree, "Data", "Blocks")
                if blk_node is None:
                    return f"Error: Cannot create Blocks node"
            blk_elems = blk_node.Elements
            blk_elems.Add(f"{name}!{block_type}")
            return f"Block '{name}' (type={block_type}) added"
        return aspen.call(impl)
    except Exception as exc:
        return f"Error: {exc}"


def tool_remove_block(name: str) -> str:
    """Remove a block from the flowsheet.

    IMPORTANT: Disconnect all connected streams first with disconnect(),
    then remove the block. Wrong order can crash the COM server.
    This function has built-in protection: if the block still has
    connected streams, it will REJECT the removal and tell you
    to disconnect() first.
    Use list_block_ports(name) to see active connections.
    """
    try:
        def impl():
            tree = aspen._app.RootModel("")
            # Check for connected streams first
            ports_node = _walk(tree, "Data", "Blocks", name, "Ports")
            if ports_node is not None:
                connected = []
                for i in range(500):
                    try:
                        p = ports_node.Elements(i)
                    except Exception:
                        break
                    if p is None:
                        break
                    # p.Elements is a COM collection property, NOT an IHNode child
                    try:
                        els = p.Elements
                        for j in range(els.Count):
                            try:
                                connected.append(els.Item(j).Name)
                            except Exception:
                                pass
                    except Exception:
                        pass
                if connected:
                    streams = ", ".join(connected)
                    return (
                        f"Block '{name}' has connected streams: {streams}.\n"
                        f"Use disconnect() on each stream first, then retry remove_block().\n"
                        f"Example: disconnect('{connected[0]}')"
                    )
            blk_node = _walk(tree, "Data", "Blocks")
            if blk_node is None:
                return f"Error: Blocks node not found (data tree may be corrupted). Try close_file() then open_file()."
            blk_elems = blk_node.Elements
            try:
                blk_elems.Remove(name)
            except Exception as re:
                return f"Error removing '{name}': {re}. Try close_file() then open_file() to recover."
            return f"Block '{name}' removed"
        return aspen.call(impl)
    except Exception as exc:
        exc_str = str(exc)
        if "RPC" in exc_str:
            return f"COM error while removing block. Try: close_file() then open_file() to recover."
        return f"Error removing '{name}': {exc}"


def _node_info_on_com(node: Any, depth_limit: int = 2, _depth: int = 0) -> dict[str, Any]:
    """Build plain-dict representation of an IHNode (called on COM thread)."""
    if _depth > depth_limit:
        return {"__truncated__": True}
    info: dict[str, Any] = {"name": node.Name}
    try:
        if node.ValueType != 0:
            info["value"] = node.Value
            try:
                info["unit"] = node.UnitString
            except Exception:
                pass
    except Exception:
        pass
    try:
        children = []
        for i in range(10000):
            try:
                c = node.Elements(i)
            except Exception:
                break
            if c is None:
                break
            children.append(_node_info_on_com(c, depth_limit, _depth + 1))
        if children:
            info["children"] = children
    except Exception:
        pass
    return info


def tool_explore(path: str) -> dict[str, Any]:
    """Explore any IHNode path (backslash-delimited, e.g. Data\\Properties)."""
    try:
        def impl():
            tree = aspen._app.RootModel("")
            parts = path.replace("/", "\\").split("\\")
            node = _walk(tree, *parts)
            if node is None:
                return {"error": f"Path '{path}' not found"}
            return _node_info_on_com(node, depth_limit=2)
        return aspen.call(impl)
    except Exception as exc:
        return {"error": str(exc)}


def tool_block_status(name: str) -> dict:
    """读取模块收敛状态和关键指标。

    返回 BLKSTAT、PER_ERROR、PROPSTAT、B_K（来自模块 Output）。
    BLKSTAT 含义见 help("diagnostics")。

    Args:
        name: Block name.

    Returns dict with keys: name, blkstat, per_error, propstat, status.
    If block hasn't been run, returns {"error": "..."}.
    For detailed param diagnostics, use validate_block() instead.
    """
    try:
        def impl():
            result = {"name": name}
            tree = aspen._app.RootModel("")
            out = _walk(tree, "Data", "Blocks", name, "Output")
            if out is None:
                return {"error": f"Block '{name}' has no Output (not yet run)"}

            for key in ("BLKSTAT", "PER_ERROR", "PROPSTAT", "B_K"):
                node = _walk(tree, "Data", "Blocks", name, "Output", key)
                if node is not None:
                    result[key.lower()] = node.Value

            blk = result.get("blkstat")
            if blk == 0:
                result["status"] = "ok (converged)"
            elif blk == 1:
                result["status"] = "converged"
            elif blk == 2:
                result["status"] = "not converged"
            elif blk == 3:
                result["status"] = "warning"

            return result
        return aspen.call(impl)
    except Exception as exc:
        return {"error": str(exc)}
