"""Fill trivial/meaningless active-but-unset params so diagnostics show only what matters."""
from __future__ import annotations
from ..com_bridge import aspen
from ._common import walk


# Params that are safe to fill — they have NO engineering impact.
# These are COM infrastructure, UI artifacts, estimation placeholders,
# or dynamic/holdup params irrelevant in steady-state.
_TRIVIAL_PARAMS: dict[str, int | str] = {
    # --- Safety valve / UI artifacts ---
    "PSVBY": "",
    "PSVLABELBOX": "",
    "PSVROUTE0": "",
    "PSVROUTE1": "",
    "PSVROUTE2": "",
    "PSVROUTE3": "",
    "PSVROUTE4": "",
    "PSVROUTE5": "",
    "PSVBX": "",
    # --- XML / serialization junk ---
    "SSXML": "",
    # --- Passthrough / dummy ---
    "THRU": "",
    # --- User script method (not using custom scripts → irrelevant) ---
    "USER_METHOD": "",
    "GLOBALSCRIPT": "",
    "LOCALSCRIPT": "",
    "LSSOURCE": "",
    "INIT_SCRIPT": "",
    # --- Flash estimation (Aspen auto-calculates these) ---
    "P_EST": 0,
    "T_EST": 0,
    # --- Dynamic / holdup params (steady-state only → 0 is fine) ---
    "MEIN": 0,
    "MEOUT": 0,
    "V_IN": 0,
    "V_OUT": 0,
    "HOLDUP_MED": 0,
    "MASSEQP": 0,
    # --- Form / scaling ---
    "FORMSCALE": "",
    # --- Derivative method (auto-detect) ---
    "DERIV_METHOD": "",
    # --- Solver method (auto) ---
    "SOLVE_METHOD": "",
    "SOLVE_OPEN": "",
    "SPARSITY": "",
    # --- Misc infrastructure ---
    "BOUND_TYPE": "",
    "AUTO_COMPS": "",
    "HIERARCHY": "",
    "INTERACTIVE": "",
    "RAMPED": "",
    "RESTART": "",
    "SBWEIGHT": "",
    "SC_METHOD": "",
    "SC_TYPE": "",
    "THRESHOLD": "",
    "UTILITY_ID": "",
    "IDESCRIPTION": "",
    # --- Equation-oriented infrastructure (not used in SM) ---
    "EOVAR_TYPE": "",
    "EO_COMPS": "",
    "EO_DEP_COMPS": "",
    "EO_FORM": "",
    "EO_HEAVY_KEY": "",
    "EO_L2_COMP": "",
    "EO_LIGHT_KEY": "",
    "EO_PT_COMP": "",
    "EO_PT_PHASE": "",
    "EO_PT_PHYSQT": "",
    "EO_PT_TYPE": "",
    "EO_PT_UOM": "",
    "EO_PT_VALUE": 0,
    # --- Spec group infrastructure ---
    "IVENABLED": "",
    "IVLOWER": 0,
    "IVNAME": "",
    "IVSCALE": 1.0,
    "IVSPEC": "",
    "IVSTEP": 0,
    "IVUPPER": 0,
    "IVVALUE": 0,
    "SG_LOWER": 0,
    "SG_PHYS_QTY": "",
    "SG_SPEC": "",
    "SG_UOM": "",
    "SG_UPPER": 0,
    "SG_VALUE": 0,
    # --- Tables/curves (only relevant if INDEP_VAR is set) ---
    "NPOINTS": 0,
    "INCR": 0,
    "INDEP_VAR": "",
    "LINES": 0,
    "WIDE": 0,
    # --- PSD (particle size distribution — not relevant for most) ---
    "CUMFRAC": 0,
    "CUM_SUBSATT": 0,
    "DUM_CUMATT": 0,
    "DUM_INTERVAL": 0,
    "DUM_LOWER": 0,
    "DUM_SUBSATT": 0,
    "DUM_UPPER": 0,
    "FAKEINT": 0,
    "INTERVAL": 0,
    "LIMUNITS": 0,
    "LOWER": 0,
    "OV_ATTR": 0,
    "OV_D50": 0,
    "OV_D63": 0,
    "OV_DIAM": 0,
    "OV_DISTFUN": 0,
    "OV_FRACTION": 0,
    "OV_GGSN": 0,
    "OV_GMDEV": 0,
    "OV_PSDID": 0,
    "OV_RRSBN": 0,
    "OV_STDDEV": 0,
    "OV_STEEPNES": 0,
    "POINTNO": 0,
    "PSDID": 0,
    "SUBBYPASS": 0,
    "SUBSATT": 0,
    "SUB_D50": 0,
    "SUB_D63": 0,
    "SUB_DIAM": 0,
    "SUB_GGSN": 0,
    "SUB_GMDEV": 0,
    "SUB_RRSBN": 0,
    "SUB_STDDEV": 0,
    "SUB_STEEPNES": 0,
    "S_CUMFRAC": 0,
    "S_DISTFUN": 0,
    "S_FRACTION": 0,
    "S_MESHOPT": 0,
    "S_OPT": 0,
    "UPPER": 0,
    "USER_OVLOWER": 0,
    "USER_OVUPPER": 0,
    "USER_OVVALUE": 0,
    "USER_SLOWER": 0,
    "USER_SUPPER": 0,
    "USER_SVALUE": 0,
    "REBWIZ": "",
    "CHEMISTRY": "",
    "ENABLED": "",
    "PHASE": "",
    "PHYS_QTY": "",
    "PROPERTIES": "",
    "UOM": "",
    "FLASH_METHOD": "",
    "FVC_ID1": "",
    "FVC_ID2": "",
    "FVC_SENTENCE": "",
    "FVC_VARIABLE": "",
    "FVN": 0,
    "FVN_ELEM": 0,
    "FVN_ID1": 0,
    "FVN_ID2": 0,
    "FVN_ID3": 0,
    "FVN_SENTENCE": "",
    "FVN_VARIABLE": "",
    "FVN_VARTYPE": 0,
    "HENRY_COMPS": "",
}


def tool_fill_trivial_params() -> str:
    """Fill trivial/meaningless active-but-unset params across all blocks.

    Many parameters show up in find_incomplete_inputs() because they are
    "active" (i7=1) but never filled — they are COM infrastructure, UI
    artifacts, estimation placeholders, or dynamic/holdup params irrelevant
    to steady-state simulation. This function fills them with safe defaults
    (0 for numbers, "" for strings) so that subsequent diagnostics only
    show the truly important missing parameters.

    Returns a report of what was filled, per block.
    """
    def impl():
        tree = aspen._app.RootModel("")
        blks = walk(tree, "Data", "Blocks")
        if blks is None:
            return "No Blocks node found"
        
        lines = []
        total_filled = 0
        
        for bi in range(500):
            try:
                b = blks.Elements(bi)
            except Exception:
                break
            if b is None:
                break
            
            bname = b.Name
            inp = walk(tree, "Data", "Blocks", bname, "Input")
            if inp is None:
                continue
            
            filled = []
            for ii in range(500):
                try:
                    n = inp.Elements(ii)
                except Exception:
                    break
                if n is None:
                    break
                
                pname = n.Name
                if pname not in _TRIVIAL_PARAMS:
                    continue
                
                # Only fill if active (i7=1) and not user-set (i11=0)
                try:
                    i7 = n.AttributeValue(7)
                    i11 = n.AttributeValue(11)
                except Exception:
                    continue
                
                if i7 != 1 or i11 != 0:
                    continue
                
                # Check if already has a value
                try:
                    if n.ValueType != 0 and n.Value is not None:
                        if n.Value != 0 and n.Value != "":
                            continue
                except Exception:
                    pass
                
                # Fill it
                default_val = _TRIVIAL_PARAMS[pname]
                try:
                    n.SetValue(0, default_val)
                    filled.append(pname)
                    total_filled += 1
                except Exception:
                    pass
            
            if filled:
                lines.append(f"  [{bname}]: {', '.join(filled)}")
        
        if not lines:
            return "No trivial params found to fill."
        
        report = f"Filled {total_filled} trivial params across {len(lines)} blocks:\n"
        report += "\n".join(lines)
        report += "\n\nNow run find_incomplete_inputs() to see what's truly missing."
        return report
    
    return aspen.call(impl)


if __name__ == "__main__":
    # Allow direct call for testing
    result = tool_fill_trivial_params()
    print(result)
