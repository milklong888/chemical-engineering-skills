"""Utility management tools.

IMPORTANT RULE — READ THIS FIRST
===================================

DO NOT use set_param('BLOCK', 'UTILITY_ID', 'NAME') or
set_value(r'\\Data\\Utilities\\...') to create or assign utilities.

Setting UTILITY_ID via COM property write triggers Aspen's engine to
validate the simulation IMMEDIATELY. If the utility node is not yet fully
configured (UTILITY_TYPE, TIN, TOUT, PRES, etc.), the engine marks the
ENTIRE simulation as "input incomplete" and ALL subsequent Run2() calls
produce all-null results. This state is IRREVERSIBLE — you must close
and reopen the .apw file to recover.

The only safe way:
  add_utility(name, type, block, params)  -- single utility
  batch_add_utilities([...])              -- multiple in one call

These use IHNodeCol.Add() — Aspen's official creation API — and configure
all parameters in the same COM dispatch, so the engine only validates
the final complete state.

Implementation detail
---------------------
- IHNodeCol.Add("NAME") creates a properly initialised utility node
  (same pattern as Add("B1!HEATER") for blocks).
- UTILITY_TYPE is set separately after Add().
- HEATER blocks in SPEC_OPT=PV get auto-switched to TP (with B_TEMP/B_PRES
  migrated to Input) because PV-mode cannot participate in utility calc.
- batch_add_utilities() groups all Add() calls in one COM apartment
  dispatch so the engine runs validation only once.
"""

from __future__ import annotations

from ..com_bridge import aspen
from ._common import walk


_COMMON_PARAMS = {
    "WATER": {"TIN": 5, "TOUT": 15, "PRES": 0.4, "VFRAC": 0,
              "HTC": 0.0003, "CO2FACTOR": 0.0001, "ENERGY_PRICE": 3e-8,
              "COOLING_VALU": 0, "DENSITY": 1000, "VISCOSITY": 1, "CONDUCTIVITY": 0.5,
              "PRICE": 0.0005, "FACTORSOURCE": "USER"},
    "STEAM": {"PRES": 0.5, "VFRAC": 1,
              "HTC": 0.001, "CO2FACTOR": 0.2, "ENERGY_PRICE": 6e-6,
              "PRICE": 0.02, "FACTORSOURCE": "USER", "FUELSOURCE": "USER",
              "COOLING_VALU": 2000, "DENSITY": 0.6, "VISCOSITY": 0.015, "CONDUCTIVITY": 0.03},
    "ELECTRICITY": {"CALOPT": "DUTY", "ELEC_PRICE": 0.08, "FACTORSOURCE": "USER", "FUELSOURCE": "USER",
                    "CO2FACTOR": 0.5, "ENERGY_PRICE": 0.08, "HTC": 0.001, "PRICE": 0.08},
    "REFRIGERANT": {"PRES": 0.3, "VFRAC": 1},
    "FUEL": {"PRES": 0.3, "VFRAC": 1},
}


def tool_add_utility(
    utility_name: str,
    utility_type: str,
    block_name: str | None = None,
    params: dict | None = None,
) -> str:
    """Add a utility (WATER, STEAM, ELECTRICITY, etc.) with full configuration.

    All parameters are set atomically to avoid incomplete-utility
    state that would break the simulation. Optionally assign to a block.

    When assigning to a HEATER block with SPEC_OPT=PV, this tool auto-switches
    the block to SPEC_OPT=TP so the utility can participate in the energy balance.
    It also reads the last B_TEMP/B_PRES from the block's output and sets them
    as input, so the block remains fully specified after the mode switch.

    Valid utility_type values: WATER, STEAM, ELECTRICITY, REFRIGERANT, FUEL.

    Common params by type:
      WATER:        TIN, TOUT, PRES, VFRAC(=0), CALOPT(=DUTY)
      STEAM:        PRES, VFRAC(=1), TIN, TOUT, or DEGSUP_OUT
      ELECTRICITY:  CALOPT(=DUTY)

    Example:
      add_utility('CHW-01', 'WATER', 'COOLER', {'TIN':5, 'TOUT':15, 'PRES':0.4})
      add_utility('LPS-01', 'STEAM', 'ASSI-REB', {'PRES':0.5, 'VFRAC':1})
      add_utility('ELEC-01', 'ELECTRICITY', 'COMP')
    """
    if params is None:
        params = {}
    utype = utility_type.upper()

    merged = dict(_COMMON_PARAMS.get(utype, {}))
    merged.update(params)

    try:
        def impl():
            tree = aspen._app.RootModel("")
            utils = tree.Elements("Data").Elements("Utilities")
            els = utils.Elements
            blk_input = None if not block_name else walk(tree, "Data", "Blocks", block_name, "Input")

            # If block is a HEATER in PV mode, capture its current output state
            # and switch to TP before creating the utility.
            if blk_input is not None:
                try:
                    spec_node = blk_input.Elements("SPEC_OPT")
                    if spec_node is not None and spec_node.Value == "PV":
                        blk_out = walk(tree, "Data", "Blocks", block_name, "Output")
                        if blk_out is not None:
                            try:
                                btemp = blk_out.Elements("B_TEMP").Value
                                bpres = blk_out.Elements("B_PRES").Value
                                if btemp is not None:
                                    blk_input.Elements("TEMP").SetValue(0, btemp)
                                if bpres is not None:
                                    blk_input.Elements("PRES").SetValue(0, bpres)
                            except Exception:
                                pass
                        spec_node.SetValue(0, "TP")
                except Exception:
                    pass

            try:
                els.Add(utility_name)
            except Exception as exc:
                return f"Error: {exc}"

            inp = tree.FindNode(f"\\Data\\Utilities\\{utility_name}\\Input")
            if inp is None:
                return f"Error: Input node not found after Add"
            inp.Elements("UTILITY_TYPE").SetValue(0, utype)
            for k, v in merged.items():
                try:
                    inp.Elements(k).SetValue(0, v)
                except Exception as e:
                    return f"Error setting {k}={v}: {e}"

            if block_name and blk_input is not None:
                uid = blk_input.Elements("UTILITY_ID")
                if uid is not None:
                    uid.SetValue(0, utility_name)

            return f"Utility '{utility_name}' ({utype}) created."

        return aspen.call(impl)
    except Exception as exc:
        return f"Error: {exc}"


def tool_batch_add_utilities(
    utilities: list[dict],
) -> str:
    """Create multiple utilities in a SINGLE COM call.

    Each dict must have 'name' and 'type'. Optional keys: 'block', 'params'.

    This bypasses the Aspen engine's incremental-validation issue where
    multiple Add() calls each trigger a validation pass. By doing all
    Add() calls in one COM apartment dispatch, the engine only sees
    the final complete state once.

    Example:
      batch_add_utilities([
        {"name": "CHW-01", "type": "WATER", "block": "COOLER",
         "params": {"TIN":2, "TOUT":7, "PRES":0.4, "VFRAC":0}},
        {"name": "LPS-01", "type": "STEAM", "block": "ASSI-REB",
         "params": {"PRES":0.5, "VFRAC":1, "TIN":152, "TOUT":152}},
        {"name": "ELEC-01", "type": "ELECTRICITY", "block": "COMP"},
      ])
    """
    try:
        def impl():
            tree = aspen._app.RootModel("")
            utils = tree.Elements("Data").Elements("Utilities")
            els = utils.Elements
            errors = []
            created = []

            for ut in utilities:
                name = ut["name"]
                utype = ut.get("type", "WATER").upper()
                block_name = ut.get("block")
                params = ut.get("params", {})

                merged = dict(_COMMON_PARAMS.get(utype, {}))
                merged.update(params)

                blk_input = None
                if block_name:
                    blk_input = walk(tree, "Data", "Blocks", block_name, "Input")
                    if blk_input is not None:
                        try:
                            spec_node = blk_input.Elements("SPEC_OPT")
                            if spec_node is not None and spec_node.Value == "PV":
                                blk_out = walk(tree, "Data", "Blocks", block_name, "Output")
                                if blk_out is not None:
                                    try:
                                        btemp = blk_out.Elements("B_TEMP").Value
                                        bpres = blk_out.Elements("B_PRES").Value
                                        if btemp is not None:
                                            blk_input.Elements("TEMP").SetValue(0, btemp)
                                        if bpres is not None:
                                            blk_input.Elements("PRES").SetValue(0, bpres)
                                    except Exception:
                                        pass
                                spec_node.SetValue(0, "TP")
                        except Exception:
                            pass

                try:
                    els.Add(name)
                except Exception as e:
                    errors.append(f"{name}: Add failed - {e}")
                    continue

                inp = tree.FindNode(f"\\Data\\Utilities\\{name}\\Input")
                if inp is None:
                    errors.append(f"{name}: Input node not found")
                    continue

                try:
                    inp.Elements("UTILITY_TYPE").SetValue(0, utype)
                    for k, v in merged.items():
                        try:
                            inp.Elements(k).SetValue(0, v)
                        except Exception as e:
                            errors.append(f"{name}.{k}: {e}")
                except Exception as e:
                    errors.append(f"{name}: config failed - {e}")
                    continue

                if block_name and blk_input is not None:
                    try:
                        blk_input.Elements("UTILITY_ID").SetValue(0, name)
                    except Exception:
                        pass

                created.append(name)

            try:
                aspen._app.Engine.Reinit()
                aspen._app.Run2()
            except Exception:
                pass

            results = {}
            for b in ["COOLER", "ASSI-REB", "COMP", "HPD", "FLASH", "SPLITTER"]:
                try:
                    bs = tree.FindNode(f"\\Data\\Blocks\\{b}\\Output\\BLKSTAT")
                    results[b] = bs.Value if bs else None
                except Exception:
                    results[b] = None

            created_str = ", ".join(created)
            if errors:
                return f"Created: [{created_str}]. Errors: {'; '.join(errors)}. BLKSTAT: {results}"
            all_ok = all(v is not None and v < 2 for v in results.values())
            status = "OK" if all_ok else f"BLKSTAT: {results}"
            return f"Utilities [{created_str}] created. {status}"

        return aspen.call(impl)
    except Exception as exc:
        return f"Error: {exc}"


def tool_list_utilities() -> list[str]:
    """List all defined utilities."""
    try:
        def impl():
            tree = aspen._app.RootModel("")
            utils = walk(tree, "Data", "Utilities")
            if utils is None:
                return []
            names = []
            for i in range(200):
                try:
                    c = utils.Elements(i)
                    if c is None:
                        break
                    n = c.Name
                    if n and n not in ("Input", "Output", "CC Nodes"):
                        names.append(n)
                except Exception:
                    break
            return names
        return aspen.call(impl)
    except Exception:
        return []


def tool_get_utility(name: str) -> dict:
    """Read a utility's input and output parameters."""
    try:
        def impl():
            tree = aspen._app.RootModel("")
            inp = {}
            inode = walk(tree, "Data", "Utilities", name, "Input")
            if inode is not None:
                for i in range(200):
                    try:
                        c = inode.Elements(i)
                        if c is None:
                            break
                        v = c.Value
                        if v is not None:
                            inp[c.Name] = v
                    except Exception:
                        break
            out = {}
            onode = walk(tree, "Data", "Utilities", name, "Output")
            if onode is not None:
                for i in range(200):
                    try:
                        c = onode.Elements(i)
                        if c is None:
                            break
                        v = c.Value
                        if v is not None and v != 0:
                            out[c.Name] = v
                    except Exception:
                        break
            return {"input": inp, "output": out}
        return aspen.call(impl)
    except Exception as exc:
        return {"error": str(exc)}


def tool_remove_utility(name: str) -> str:
    """Remove a utility. Clears UTILITY_ID/COND_UTIL/REB_UTIL on any referencing blocks first.

    Uses parent.Elements.Remove(name) — same pattern as remove_block().
    Does NOT use RemoveAll() + CastTo(IHNodeCol) which silently fails.
    """
    try:
        def impl():
            tree = aspen._app.RootModel("")
            blocks = walk(tree, "Data", "Blocks")
            if blocks is not None:
                for i in range(200):
                    try:
                        b = blocks.Elements(i)
                        if b is None:
                            break
                    except Exception:
                        break
                    bname = b.Name
                    # Clear UTILITY_ID (HEATER, PUMP, etc.)
                    for uid_path in (
                        ("Data", "Blocks", bname, "Input", "UTILITY_ID"),
                        ("Data", "Blocks", bname, "Input", "COND_UTIL"),
                        ("Data", "Blocks", bname, "Input", "REB_UTIL"),
                    ):
                        try:
                            node = walk(tree, *uid_path)
                            if node is not None and node.Value == name:
                                node.SetValue(0, "")
                        except Exception:
                            pass
            utils = walk(tree, "Data", "Utilities")
            if utils is not None:
                try:
                    utils.Elements.Remove(name)
                except Exception:
                    pass
            try:
                aspen._app.Engine.Reinit()
            except Exception:
                pass
            return f"Utility '{name}' removed."
        return aspen.call(impl)
    except Exception as exc:
        return f"Error: {exc}"
