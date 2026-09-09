"""Flowsheet topology and side duty tools.

All COM operations run inside aspen.call() lambdas on the dedicated
COM apartment thread.
"""

from __future__ import annotations

from ..com_bridge import aspen
from ._common import walk


def tool_flowsheet_topology() -> str:
    """Show the flowsheet topology: source --[stream]--> destination.

    Now shows complete bidirectional format: BlockA --[StreamName]--> BlockB.
    Unknown sources/destinations show as (?).
    """
    try:
        def impl():
            tree = aspen._app.RootModel("")
            lines = ["Flowsheet Topology:"]

            # Build full connection map from stream SOURCE/DESTINATION
            streams_node = walk(tree, "Data", "Streams")
            if streams_node is not None:
                for i in range(200):
                    try:
                        s = streams_node.Elements(i)
                    except Exception:
                        break
                    if s is None:
                        break
                    sname = s.Name
                    src = walk(tree, "Data", "Streams", sname, "Output", "SOURCE")
                    dst = walk(tree, "Data", "Streams", sname, "Output", "DESTINATION")
                    src_val = src.Value if src is not None else None
                    dst_val = dst.Value if dst is not None else None
                    if src_val or dst_val:
                        src_str = src_val if src_val else "(?)"
                        dst_str = dst_val if dst_val else "(?)"
                        lines.append(f"  {src_str} --[{sname}]--> {dst_str}")

            if len(lines) == 1:
                return "Flowsheet is empty (no blocks or streams)"
            return "\n".join(lines)
        return aspen.call(impl)
    except Exception as exc:
        return f"Error: {exc}"


def tool_add_side_duty(block_name: str, stage: int, duty: float) -> str:
    """Add/update a side heater/cooler duty on a RadFrac stage."""
    try:
        def impl():
            tree = aspen._app.RootModel("")
            # Navigate to side duties under RadFrac block
            # Path: Data\Blocks\{name}\Input\SIDE_DUTIES\{stage name}\DUTY
            path = walk(tree, "Data", "Blocks", block_name, "Input")
            if path is None:
                return f"Block '{block_name}' Input not found"
            sd_node = walk(tree, "Data", "Blocks", block_name, "Input", "SIDE_DUTIES")
            if sd_node is None:
                return f"No SIDE_DUTIES on block '{block_name}' (is it RadFrac?)"
            # Find or create the stage entry
            stage_name = None
            for i in range(100):
                try:
                    c = sd_node.Elements(i)
                except Exception:
                    break
                if c is None:
                    break
                if c.Name.endswith(str(stage)):
                    stage_name = c.Name
                    break
            if stage_name is None:
                return f"Stage {stage} not found in SIDE_DUTIES"
            duty_node = walk(tree, "Data", "Blocks", block_name, "Input",
                              "SIDE_DUTIES", stage_name, "DUTY")
            if duty_node is None:
                return f"DUTY node not found for stage {stage}"
            duty_node.SetValue(0, duty)
            return f"Side duty set on {block_name} stage {stage} = {duty}"
        return aspen.call(impl)
    except Exception as exc:
        return f"Error: {exc}"


def tool_remove_side_duty(block_name: str, stage: int) -> str:
    """Remove a side duty from a RadFrac stage."""
    try:
        def impl():
            tree = aspen._app.RootModel("")
            sd_node = walk(tree, "Data", "Blocks", block_name, "Input", "SIDE_DUTIES")
            if sd_node is None:
                return f"No SIDE_DUTIES on block '{block_name}'"
            target_idx = None
            for i in range(100):
                try:
                    c = sd_node.Elements(i)
                except Exception:
                    break
                if c is None:
                    break
                if c.Name.endswith(str(stage)):
                    target_idx = i
                    break
            if target_idx is None:
                return f"Stage {stage} not found in SIDE_DUTIES"
            sd_node.Elements.RemoveRow(0, target_idx)
            return f"Side duty removed from {block_name} stage {stage}"
        return aspen.call(impl)
    except Exception as exc:
        return f"Error: {exc}"


def tool_configure_fsplit(block_name: str, outlet_name: str, frac: float) -> str:
    """Add/configure a second product outlet on an FSPLIT block.

    Sets the split fraction for a product outlet. The outlet must
    already exist (use connect_port to connect the stream first).

    Args:
        block_name: FSPLIT block name (e.g. S-1).
        outlet_name: Product stream name (e.g. RECYCLE).
        frac: Split fraction (0.0-1.0) for this outlet; the remainder
              goes to the first outlet automatically.

    Example:
        connect_port("S-1", "P(OUT)", "RECYCLE")
        configure_fsplit("S-1", "RECYCLE", 0.85)
    """
    try:
        def _impl():
            _tree = aspen._app.RootModel("")
            _fp = "\\Data\\Blocks\\" + block_name + "\\Input\\FRAC"
            _frac_node = _tree.FindNode(_fp)
            if _frac_node is None:
                return "FRAC node not found for '" + block_name + "'"
            _frac_els = _frac_node.Elements
            _found = False
            for _i in range(_frac_els.Count):
                try:
                    if _frac_els.Item(_i).Name == outlet_name:
                        _found = True
                        _frac_els.Item(_i).SetValue(0, frac)
                        break
                except Exception:
                    pass
            if not _found:
                return ("Outlet '" + outlet_name + "' not found in FRAC table. "
                        "Connect the stream first with connect_port().")
            return ("FSPLIT '" + block_name + "' outlet '" + outlet_name +
                    "' FRAC=" + str(frac) + ". " + outlet_name + " gets " +
                    str(int(frac*100)) + "% of the inlet flow.")
        return aspen.call(_impl)
    except Exception as _exc:
        return "Error: " + str(_exc)