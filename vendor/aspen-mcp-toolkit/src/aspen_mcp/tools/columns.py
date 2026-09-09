"""Column (RadFrac / ABSBR1) configuration tools.

All COM operations run inside aspen.call() lambdas on the dedicated
COM apartment thread.
"""

from __future__ import annotations

from ..com_bridge import aspen
from ._common import walk


_COLUMN_TYPES = {"FRACT1", "FRACT2", "FRACT3", "FRACT4",
                  "ABSBR1", "ABSBR2", "RADFRAC", "RADFRC",
                  "PETRO", "REFINE",
                  "MULTISTG", "SCFRAC", "EXTRACT"}


def _is_column(tree, name: str) -> bool:
    """Check if block is a column type."""
    blk = walk(tree, "Data", "Blocks", name)
    if blk is None:
        return False
    if blk.Value in _COLUMN_TYPES:
        return True
    # Fresh blocks may have empty Value; check for column-specific params
    nstage = walk(tree, "Data", "Blocks", name, "Input", "NSTAGE")
    if nstage is not None:
        return True
    condenser = walk(tree, "Data", "Blocks", name, "Input", "CONDENSER")
    if condenser is not None:
        return True
    return False


def tool_set_column_stages(block_name: str, nstage: int) -> str:
    """Set the number of stages on a RadFrac / ABSBR1 column."""
    if nstage < 2:
        return "Error: nstage must be >= 2"
    try:
        def impl():
            tree = aspen._app.RootModel("")
            if not _is_column(tree, block_name):
                return "Error: '" + block_name + "' is not a column block"
            node = walk(tree, "Data", "Blocks", block_name, "Input", "NSTAGE")
            if node is None:
                return "Error: NSTAGE not found on '" + block_name + "'"
            node.SetValue(0, nstage)
            return "Set " + block_name + " NSTAGE = " + str(nstage)
        return aspen.call(impl)
    except Exception as exc:
        return "Error: " + str(exc)


def tool_set_condenser_type(block_name: str, condenser_type: str) -> str:
    """Set the condenser type on a RadFrac column."""
    valid = ("NONE", "TOTAL", "PARTIAL-V", "PARTIAL-L", "PARTIAL-VL")
    ct = condenser_type.upper()
    if ct not in valid:
        return "Error: condenser_type must be one of " + str(valid)
    try:
        def impl():
            tree = aspen._app.RootModel("")
            if not _is_column(tree, block_name):
                return "Error: '" + block_name + "' is not a column block"
            node = walk(tree, "Data", "Blocks", block_name, "Input", "CONDENSER")
            if node is None:
                return "Error: CONDENSER not found on '" + block_name + "'"
            node.SetValue(0, ct)
            return "Set " + block_name + " CONDENSER = " + ct
        return aspen.call(impl)
    except Exception as exc:
        return "Error: " + str(exc)


def tool_set_reboiler_type(block_name: str, reboiler_type: str) -> str:
    """Set the reboiler type on a RadFrac column."""
    valid = ("NONE", "KETTLE", "THERMOSIPHON", "INTERNALS", "FIRED")
    rt = reboiler_type.upper()
    if rt not in valid:
        return "Error: reboiler_type must be one of " + str(valid)
    try:
        def impl():
            tree = aspen._app.RootModel("")
            if not _is_column(tree, block_name):
                return "Error: '" + block_name + "' is not a column block"
            node = walk(tree, "Data", "Blocks", block_name, "Input", "REBOILER")
            if node is None:
                return "Error: REBOILER not found on '" + block_name + "'"
            node.SetValue(0, rt)
            return "Set " + block_name + " REBOILER = " + rt
        return aspen.call(impl)
    except Exception as exc:
        return "Error: " + str(exc)


def tool_set_feed_stage(block_name: str, stream_name: str, stage: int) -> str:
    """Set the feed stage for a stream entering a column.

    Handles two Aspen tree layouts:
    1. ABSBR1 style: Data\\Blocks\\{name}\\Input\\FEED_STAGE\\{stream_name}
       (parent node with children named after each feed stream)
    2. RadFrac style: Data\\Blocks\\{name}\\Input\\FEED_STAGES\\{stream}\\STAGE
       (collection table with STAGE column)
    """
    try:
        def impl():
            tree = aspen._app.RootModel("")
            if not _is_column(tree, block_name):
                return "Error: '" + block_name + "' is not a column block"

            # Strategy 1: ABSBR1 style - FEED_STAGE has children by stream name
            fs = walk(tree, "Data", "Blocks", block_name, "Input", "FEED_STAGE")
            if fs is not None:
                try:
                    child = fs.Elements(stream_name)
                    child.SetValue(0, stage)
                    return ("Set " + block_name + " feed '"
                            + stream_name + "' to stage " + str(stage))
                except Exception:
                    pass
                return ("Feed stream '" + stream_name + "' not found under "
                        "FEED_STAGE. Connect it to the column first.")

            # Strategy 2: RadFrac style - FEED_STAGES table
            fs_node = walk(tree, "Data", "Blocks", block_name,
                            "Input", "FEED_STAGES")
            if fs_node is None:
                return ("Error: neither FEED_STAGE nor FEED_STAGES found "
                        "on '" + block_name + "'")
            for i in range(100):
                try:
                    c = fs_node.Elements(i)
                except Exception:
                    break
                if c is None:
                    break
                if c.Name == stream_name:
                    stage_n = walk(
                        tree, "Data", "Blocks", block_name,
                        "Input", "FEED_STAGES", stream_name, "STAGE")
                    if stage_n is not None:
                        stage_n.SetValue(0, stage)
                        return ("Set " + block_name + " feed '"
                                + stream_name + "' to stage " + str(stage))
                    break
            return ("Feed stream '" + stream_name + "' not found in "
                    "FEED_STAGES. Connect it to the column first.")
        return aspen.call(impl)
    except Exception as exc:
        return "Error: " + str(exc)


def tool_set_product_stage(block_name: str, stream_name: str,
                           stage: int, phase: str = "L") -> str:
    """Set the product draw stage and phase for a column product stream.

    Handles two Aspen tree layouts:
    1. ABSBR1 style: Data\\Blocks\\{name}\\Input\\PROD_STAGE\\{stream_name}
       + PROD_PHASE\\{stream_name}
    2. RadFrac style: Data\\Blocks\\{name}\\Input\\PROD_STAGES\\{stream}\\STAGE
    """
    phase = phase.upper()
    if phase not in ("L", "V"):
        return "Error: phase must be 'L' (liquid) or 'V' (vapor)"
    try:
        def impl():
            tree = aspen._app.RootModel("")
            if not _is_column(tree, block_name):
                return "Error: '" + block_name + "' is not a column block"

            # Strategy 1: ABSBR1 style - PROD_STAGE child by stream name
            ps = walk(tree, "Data", "Blocks", block_name, "Input", "PROD_STAGE")
            if ps is not None:
                try:
                    child = ps.Elements(stream_name)
                    child.SetValue(0, stage)
                    # Also set phase
                    pp = walk(tree, "Data", "Blocks", block_name,
                               "Input", "PROD_PHASE")
                    if pp is not None:
                        try:
                            pc = pp.Elements(stream_name)
                            pc.SetValue(0, phase)
                        except Exception:
                            pass
                    return ("Set " + block_name + " product '"
                            + stream_name + "' stage=" + str(stage)
                            + " phase=" + phase)
                except Exception:
                    pass
                return ("Product stream '" + stream_name + "' not found under "
                        "PROD_STAGE. Connect it to the column first.")

            # Strategy 2: RadFrac style
            ps_node = walk(tree, "Data", "Blocks", block_name,
                            "Input", "PROD_STAGES")
            if ps_node is None:
                return ("Error: neither PROD_STAGE nor PROD_STAGES found "
                        "on '" + block_name + "'")
            for i in range(100):
                try:
                    c = ps_node.Elements(i)
                except Exception:
                    break
                if c is None:
                    break
                if c.Name == stream_name:
                    stage_n = walk(
                        tree, "Data", "Blocks", block_name,
                        "Input", "PROD_STAGES", stream_name, "STAGE")
                    phase_n = walk(
                        tree, "Data", "Blocks", block_name,
                        "Input", "PROD_STAGES", stream_name, "PHASE")
                    if stage_n is not None:
                        stage_n.SetValue(0, stage)
                    if phase_n is not None:
                        phase_n.SetValue(0, phase)
                    return ("Set " + block_name + " product '"
                            + stream_name + "' stage=" + str(stage)
                            + " phase=" + phase)
            return ("Product stream '" + stream_name + "' not found in "
                    "PROD_STAGES. Connect it to the column first.")
        return aspen.call(impl)
    except Exception as exc:
        return "Error: " + str(exc)


def tool_set_column_pressure(block_name: str, top_pres: float,
                              dp_stage: float | None = None) -> str:
    """Set the column pressure profile."""
    try:
        def impl():
            tree = aspen._app.RootModel("")
            if not _is_column(tree, block_name):
                return "Error: '" + block_name + "' is not a column block"
            pres1 = walk(tree, "Data", "Blocks", block_name,
                          "Input", "PRES1")
            if pres1 is None:
                return "Error: PRES1 not found on '" + block_name + "'"
            pres1.SetValue(0, top_pres)
            msg = "Set " + block_name + " PRES1 (top pressure) = " + str(top_pres)
            if dp_stage is not None:
                dp = walk(tree, "Data", "Blocks", block_name,
                           "Input", "DP_STAGE")
                if dp is not None:
                    dp.SetValue(0, dp_stage)
                    msg += ", DP_STAGE = " + str(dp_stage)
            return msg
        return aspen.call(impl)
    except Exception as exc:
        return "Error: " + str(exc)
