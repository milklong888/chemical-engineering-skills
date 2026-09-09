"""Analysis tools: convergence, sensitivity, report, diagnostics.

All COM operations run inside aspen.call() lambdas on the dedicated
COM apartment thread.
"""

from __future__ import annotations

from typing import Any

from ..com_bridge import aspen
from ..knowledge.convergence import search_failures
from ._common import walk


# --- 灵敏度分析 ------------------------------------------------------------


def tool_sensitivity(
    block_name: str,
    variable: str,
    values: list[float],
    unit: str = "",
) -> dict[str, Any]:
    """Manual sensitivity: sweep a block variable and re-run."""
    results: dict[str, Any] = {}
    try:
        for val in values:
            try:
                aspen.set_value(val, "Data", "Blocks", block_name, "Input", variable)
            except Exception as e:
                results[str(val)] = f"set failed: {e}"
                continue
            try:
                aspen.reinit_and_run()
            except Exception as e:
                results[str(val)] = f"run failed: {e}"
                continue
            val_node = aspen.get_value("Data", "Blocks", block_name, "Input", variable)
            results[str(val)] = {"input": val_node}
            for key in ("BLKSTAT", "PER_ERROR"):
                try:
                    out_node = aspen.get_value("Data", "Blocks", block_name, "Output", key)
                    if out_node is not None:
                        results[str(val)][key.lower()] = out_node
                except Exception:
                    pass
        return results
    except Exception as exc:
        return {"error": str(exc)}


# --- 报告导出 --------------------------------------------------------------


def tool_export_report_file(file_path: str) -> str:
    """Export the simulation report using Engine.ExportReport."""
    try:
        aspen.call(lambda: aspen._app.Engine.ExportReport(file_path, 13))
        return f"Report exported to {file_path}"
    except Exception as exc:
        return f"Error: {exc}"


# --- 参数诊断辅助方法 -------------------------------------------------------


_UNIT_HINTS = {
    (22, 4): "\u00b0C", (20, 5): "bar", (20, 10): "kPa",
    (13, 3): "Gcal/hr", (13, 18): "kW",
    (31, 4): "\u00b0C", (49, 3): "kJ/kg-K",
    (75, 5): "bar", (75, 18): "kPa",
    (17, 3): "m", (11, 3): "kg/hr",
}
# --- Smart parameter categorization per block type ---
# For each block type, specify:
#   - mode_param: the param that selects the operating mode (e.g. SPEC_OPT)
#   - mode_map:   {mode_value: [params_required_in_that_mode]}
#   - default_mode: fallback if mode_param has no value yet
#
# To add a new block type: append to _BLOCK_MODES dict below.
# The block type string comes from _get_block_type() which reads blk.Value
# (e.g. "RADFRAC", "HEATX", "VALVE", "MIXER", etc.).

_BLOCK_MODES: dict[str, dict] = {
    "HEATER": {"mode_param": "SPEC_OPT", "default_mode": "TP",
        "mode_map": {"TP": ["TEMP", "PRES"], "TEMP": ["TEMP"], "DUTY": ["DUTY"],
                     "VFRAC": ["VFRAC"], "PRES": ["PRES"]}},
    "V-DRUM1": {"mode_param": "SPEC_OPT", "default_mode": "TP",
        "mode_map": {"TP": ["TEMP", "PRES"], "TEMP": ["TEMP"], "PRES": ["PRES"],
                     "VFRAC": ["VFRAC"], "DUTY": ["DUTY"]}},
    "FLASH2": {"mode_param": "SPEC_OPT", "default_mode": "TP",
        "mode_map": {"TP": ["TEMP", "PRES"], "TEMP": ["TEMP"], "PRES": ["PRES"],
                     "VFRAC": ["VFRAC"], "DUTY": ["DUTY"]}},
    "ICON2": {"mode_param": "SPEC_OPT", "default_mode": "TEMP",
        "mode_map": {"TEMP": ["TEMP"], "DUTY": ["DUTY"]}},
    "COMPR": {"mode_param": "SPEC_OPT", "default_mode": "TEMP",
        "mode_map": {"TEMP": ["TEMP"], "DUTY": ["DUTY"], "PRES": ["PRES"], "DELP": ["DELP"]}},
}


def _read_option_list(param_node):
    '''Read option list from a parameter node.
    For enum-type params (like SPEC_OPT), AttributeValue(5) returns
    the option list node, whose AttributeValue(0) contains
    newline-separated option values.'''
    try:
        opt_node = param_node.AttributeValue(5)
        if opt_node is not None:
            raw = opt_node.AttributeValue(0)
            if raw and isinstance(raw, str):
                return raw.split("\n")
    except Exception:
        pass
    return None


def _get_block_type(tree, block_name):
    '''Get the Aspen block type string (e.g. HEATER, ICON2).'''
    try:
        blk = walk(tree, "Data", "Blocks", block_name)
        if blk is not None:
            return blk.Value
    except Exception:
        pass
    return None


def _read_mode_value(tree, block_name, mode_param):
    '''Read current value of a mode-selector param like SPEC_OPT.'''
    try:
        n = walk(tree, "Data", "Blocks", block_name, "Input", mode_param)
        if n is not None and n.Value:
            return str(n.Value)
    except Exception:
        pass
    return None


def _categorize_block_params(tree, block_name):
    '''Categorize unset-but-active params.

    Returns (critical, irrelevant, optional, mode_info).
    - critical:    need to be filled for current mode
    - irrelevant:  in same or-group but not needed in current mode
    - optional:    not related to any mode
    - mode_info:   human-readable like "SPEC_OPT=TEMP" or None
    '''
    blk_type = _get_block_type(tree, block_name)
    inp = walk(tree, "Data", "Blocks", block_name, "Input")
    if inp is None:
        return [], [], [], None

    mode_config = _BLOCK_MODES.get(blk_type) if blk_type else None
    current_mode = None
    mode_required = set()
    mode_optional = set()

    if mode_config:
        mode_param_name = mode_config["mode_param"]
        current_mode = _read_mode_value(tree, block_name, mode_param_name)
        if not current_mode:
            current_mode = mode_config.get("default_mode")
        mode_map = mode_config.get("mode_map", {})
        if current_mode and current_mode in mode_map:
            mode_required = set(mode_map[current_mode])
        for mode_vals in mode_map.values():
            mode_optional.update(mode_vals)

    mode_info = None
    if mode_config and current_mode:
        mode_info = mode_config["mode_param"] + "=" + current_mode

    _SKIP = frozenset({
        "Unit Set", "User Table", "User Tree",
        "ADDINPUT", "INPUT", "COMPS",
        "DESCRIPTION", "FILE", "COORD",
        "COMMENT", "HEADING", "RESULTS", "REPORT",
        "OPSETNAME", "FRWATEROPSET",
        "SIM_LEVEL", "PROP_LEVEL", "STREAM_LEVEL", "TERM_LEVEL",
    })

    critical = []
    irrelevant = []
    optional = []

    for ii in range(500):
        try:
            n = inp.Elements(ii)
            if n is None:
                break
        except Exception:
            break
        pname = n.Name
        if pname in _SKIP:
            continue
        try:
            i7 = n.AttributeValue(7)
            i11 = n.AttributeValue(11)
            i19 = n.AttributeValue(19)
            i2 = n.AttributeValue(2)
            i3 = n.AttributeValue(3)
        except Exception:
            continue
        if i7 == 0:
            continue
        if i11 == 1:
            continue
        try:
            if n.ValueType != 0 and n.Value is not None:
                continue
        except Exception:
            continue

        line = "    " + pname
        if i19 and str(i19) != pname:
            desc = str(i19)[:60]
            line += "  -- " + desc
        hint = _UNIT_HINTS.get((i2, i3))
        if hint:
            line += "  [" + hint + "]"

        if pname in mode_required:
            critical.append(line)
        elif pname in mode_optional:
            irrelevant.append(line)
        else:
            optional.append(line)

    return critical, irrelevant, optional, mode_info



def _param_diagnostics(tree, block_name: str, max_lines: int = 10) -> list[str]:
    """Scan a block's Input params and return diagnostic lines for unset but active params.
    Uses smart categorization (critical vs irrelevant vs optional) based on SPEC_OPT mode."""
    critical, irrelevant, optional, mode_info = _categorize_block_params(tree, block_name)
    
    result = []
    if mode_info:
        result.append("    [Mode: " + mode_info + "]")
    
    if critical:
        result.append("    == Critical (current mode) ==")
        result.extend(critical[:max_lines])
        if len(critical) > max_lines:
            result.append("      ... and " + str(len(critical) - max_lines) + " more")
    
    if irrelevant:
        result.append("    -- Mode-irrelevant --")
        result.extend(irrelevant[:max(max_lines, 5)])
        if len(irrelevant) > max(max_lines, 5):
            result.append("      ... and " + str(len(irrelevant) - max(max_lines, 5)) + " more")
    
    if optional and len(result) < max_lines:
        remaining = max_lines - len(result)
        if remaining > 0:
            result.append("    .. Optional ..")
            result.extend(optional[:remaining])
            if len(optional) > remaining:
                result.append("      ... and " + str(len(optional) - remaining) + " more")
    
    if not result:
        result.append("  (all active params have values)")
    
    return result

def _get_convergence_report() -> str:
    """Build a convergence report from current simulation state (on COM thread)."""
    tree = aspen._app.RootModel("")
    lines: list[str] = []
    blocks_node = walk(tree, "Data", "Blocks")
    if blocks_node is not None:
        block_lines = []
        blocks_with_issues = []
        for i in range(200):
            try:
                block = blocks_node.Elements(i)
            except Exception:
                break
            if block is None:
                break
            bname = block.Name
            blkstat = walk(tree, "Data", "Blocks", bname, "Output", "BLKSTAT")
            perror = walk(tree, "Data", "Blocks", bname, "Output", "PER_ERROR")
            propstat = walk(tree, "Data", "Blocks", bname, "Output", "PROPSTAT")
            blkmsg = walk(tree, "Data", "Blocks", bname, "Output", "BLKMSG")
            msg = f"  {bname}"
            if blkstat is not None:
                stat_map = {0: "OK", 1: "converged", 2: "not converged", 3: "warning"}
                msg += f"  BLKSTAT={blkstat.Value} ({stat_map.get(blkstat.Value, '?')})"
                if blkstat.Value not in (0, 1, None):
                    blocks_with_issues.append(bname)
            if perror is not None:
                msg += f"  PER_ERROR={perror.Value}"
            if propstat is not None:
                msg += f"  PROPSTAT={propstat.Value}"
            if blkmsg is not None and blkmsg.Value:
                msg += f"  BLKMSG={blkmsg.Value}"
            block_lines.append(msg)
        if block_lines:
            lines.append("Block convergence status:")
            lines.extend(block_lines)
        if blocks_with_issues:
            lines.append("")
            lines.append("Parameter diagnostics (unset params in troubled blocks):")
            for bname in blocks_with_issues:
                diag = _param_diagnostics(tree, bname)
                if diag:
                    lines.append(f"  [{bname}]:")
                    lines.extend(diag)
    return "\n".join(lines)
def tool_diagnose(keywords: list[str]) -> str:
    """Diagnose convergence issues: live status + knowledge base search.

Shows live block convergence status (BLKSTAT, PER_ERROR, BLKMSG)
for all blocks. For blocks with BLKSTAT=2 (not converged), also
shows parameter diagnostics with Chinese descriptions + unit hints.

Then searches the built-in knowledge base for matching keywords.

Args:
    keywords: List of keywords to search (e.g. ["Wegstein"],
              ["COLUMN DRIES UP"], ["NRTL"], ["convergence"]).

Use validate_block(name) for focused analysis of ONE block.
Use find_incomplete_inputs() for pre-run check of all blocks.
"""
    sections: list[str] = []

    # 实时收敛数据
    try:
        report = aspen.call(lambda: _get_convergence_report())
        sections.append("=== Live Convergence Status ===\n" + report)
    except Exception as exc:
        sections.append(f"(live status unavailable: {exc})")

    # 知识库匹配结果
    if keywords:
        sections.append("\n=== Knowledge Base Matches ===\n")
        for keyword in keywords:
            try:
                entries = search_failures([keyword])
                for e in entries[:3]:
                    if 'note' in e:
                        sections.append(f"  ({e['note']})")
                    else:
                        sections.append(f"  [{e.get('title', '?')}] {e.get('description', '')[:200]}")
                        if e.get('fixes'):
                            sections.append(f"    Suggestion: {e['fixes'][0][:200]}")
            except Exception:
                pass

        return "\n".join(sections)


def tool_search_convergence_knowledge(keywords: list[str]) -> list[dict]:
    """Diagnose convergence issues: live status + knowledge base search.

Shows live block convergence status (BLKSTAT, PER_ERROR, BLKMSG)
for all blocks. For blocks with BLKSTAT=2 (not converged), also
shows parameter diagnostics with Chinese descriptions + unit hints.

Then searches the built-in knowledge base for matching keywords.

Args:
    keywords: List of keywords to search (e.g. ["Wegstein"],
              ["COLUMN DRIES UP"], ["NRTL"], ["convergence"]).

Use validate_block(name) for focused analysis of ONE block.
Use find_incomplete_inputs() for pre-run check of all blocks.
"""
    results: list[dict] = []
    for keyword in keywords:
        for entry in search_failures([keyword]):
            text = entry.get('title', '') + ': ' + entry.get('description', '')
            results.append({"keyword": keyword, "type": "failure", "text": text})
            for fix in entry.get('fixes', []):
                results.append({"keyword": keyword, "type": "fix", "text": fix})
    return results


def tool_generate_input_summary(file_path: str) -> str:
    """Generate a .bkp input summary."""
    try:
        aspen.generate_input_summary(file_path)
        return f"Input summary written to {file_path}"
    except Exception as exc:
        return f"Error: {exc}"


def tool_list_tear_streams() -> list[str]:
    """List all tear streams in the simulation (recycle loops)."""
    try:
        def impl():
            tree = aspen._app.RootModel("")
            # 尝试多种可能的撕裂流股路径
            paths = [
                ("Data", "Convergence", "Tear", "Input", "STREAMS"),
                ("Data", "Convergence", "Tear", "Streams"),
                ("Data", "Convergence", "Conv-Options", "Input", "TEAR_STREAMS"),
            ]
            for parts in paths:
                tear = walk(tree, *parts)
                if tear is not None:
                    streams = []
                    for i in range(200):
                        try:
                            s = tear.Elements(i)
                        except Exception:
                            break
                        if s is None:
                            break
                        val = s.Value if hasattr(s, "Value") else str(s)
                        if val:
                            streams.append(str(val))
                    if streams:
                        return streams
                    # 尝试作为 2D 表使用 GetLabel
                    try:
                        els = tear.Elements if hasattr(tear, "Elements") else tear
                        for i in range(els.Count):
                            try:
                                lab = els.GetLabel(0, i)
                                if lab:
                                    streams.append(lab)
                            except Exception:
                                try:
                                    lab = els.Item(i).Name
                                    if lab:
                                        streams.append(lab)
                                except Exception:
                                    pass
                    except Exception:
                        pass
                    if streams:
                        return streams
            # 回退方案：扫描 Convergence Tear Output
            tear_out = walk(tree, "Data", "Convergence", "Tear", "Output")
            if tear_out is not None:
                for i in range(200):
                    try:
                        s = tear_out.Elements(i)
                    except Exception:
                        break
                    if s is None:
                        break
                    if s.Name and "STREAM" in s.Name.upper():
                        vs = s.Value
                        if vs:
                            return [str(vs)]
            return []
        return aspen.call(impl)
    except Exception:
        return []


def tool_set_tear_estimate(stream_name: str, temp: float | None = None,
                            pres: float | None = None,
                            total_flow: float | None = None) -> str:
    """Set initial estimate for a tear (recycle) stream.

    Args:
        stream_name: Tear stream name.
        temp: Estimated temperature (C).
        pres: Estimated pressure (bar).
        total_flow: Estimated total molar flow (kmol/hr).
    """
    try:
        parts = []
        if temp is not None:
            aspen.set_value(temp, "Data", "Streams", stream_name, "Input", "TEMP", "MIXED")
            parts.append(f"TEMP={temp}")
        if pres is not None:
            aspen.set_value(pres, "Data", "Streams", stream_name, "Input", "PRES", "MIXED")
            parts.append(f"PRES={pres}")
        if total_flow is not None:
            aspen.set_value(total_flow, "Data", "Streams", stream_name, "Input", "TOTAL", "MIXED")
            parts.append(f"TOTAL={total_flow}")
        if parts:
            return f"Tear stream '{stream_name}' estimate set: {', '.join(parts)}"
        return f"No values provided for tear stream '{stream_name}'."
    except Exception as exc:
        return f"Error: {exc}"



# --- 查找未完成输入 ---------------------------------------------------------


def tool_find_incomplete_inputs() -> str:
    """Scan the simulation for incomplete input nodes.

    Uses smart categorization per block type:
    - For known block types (HEATER, ICON2, V-DRUM1, etc.), reads SPEC_OPT
      to determine which params are truly required vs optional in current mode.
    - Unknown block types: list all active-but-unset params (traditional).
    """
    try:
        def impl():
            tree = aspen._app.RootModel("")
            blks = walk(tree, "Data", "Blocks")
            if blks is None:
                return "No Blocks node found"

            results = []
            for bi in range(500):
                try:
                    blk = blks.Elements(bi)
                except Exception:
                    break
                if blk is None:
                    break
                blk_name = blk.Name
                blk_type = _get_block_type(tree, blk_name)

                critical, irrelevant, optional, mode_info = _categorize_block_params(tree, blk_name)

                if not (critical or irrelevant or optional):
                    continue

                header = "  [" + blk_name
                if blk_type:
                    header += " (" + blk_type + ")"
                if mode_info:
                    header += "]  Current mode: " + mode_info
                else:
                    header += "]"
                results.append(header)

                if critical:
                    results.append("    == Critical (needed for current mode) ==")
                    results.extend(critical)

                if irrelevant:
                    results.append("    -- Mode-irrelevant (needed if mode changes) --")
                    shown = irrelevant[:5]
                    for item in shown:
                        results.append(item)
                    if len(irrelevant) > 5:
                        results.append("      ... and " + str(len(irrelevant) - 5) + " more")

                if optional:
                    results.append("    .. Other optional params ..")
                    shown = optional[:5]
                    for item in shown:
                        results.append(item)
                    if len(optional) > 5:
                        results.append("      ... and " + str(len(optional) - 5) + " more")

                results.append("")

            if not results:
                return "All inputs appear complete."
            return "Params likely needing input:\n" + "\n".join(results).rstrip("\n\n")
        return aspen.call(impl)
    except Exception as exc:
        return f"Error: {exc}"

def tool_validate_block(block_name: str) -> str:
    """Check block validation status with parameter-level diagnostics.

    Reports Engine.Ready, block status, and scans active unset params
    with Chinese descriptions and unit hints.
    """
    try:
        def impl():
            lines = []
            try:
                eng = aspen._app.Engine
                lines.append(f"Engine.Ready = {eng.Ready}")
                lines.append(f"Engine.IsRunning = {eng.IsRunning}")
            except Exception as e:
                lines.append(f"Engine error: {e}")

            tree = aspen._app.RootModel("")
            blk = walk(tree, "Data", "Blocks", block_name)
            if blk is not None:
                lines.append(f"Block type = {blk.Value}")

                # 运行收敛信息
                out = walk(tree, "Data", "Blocks", block_name, "Output")
                if out is not None:
                    blkstat = walk(tree, "Data", "Blocks", block_name, "Output", "BLKSTAT")
                    blkmsg = walk(tree, "Data", "Blocks", block_name, "Output", "BLKMSG")
                    perror = walk(tree, "Data", "Blocks", block_name, "Output", "PER_ERROR")
                    if blkstat is not None:
                        smap = {0: "OK", 1: "converged", 2: "not converged", 3: "warning"}
                        lines.append(f"BLKSTAT = {blkstat.Value} ({smap.get(blkstat.Value, '?')})")
                    if perror is not None:
                        lines.append(f"PER_ERROR = {perror.Value}")
                    if blkmsg is not None and blkmsg.Value:
                        lines.append(f"BLKMSG = {blkmsg.Value}")

                # 参数诊断
                lines.append("")
                lines.append("Parameter diagnostics (active but unset):")
                diag = _param_diagnostics(tree, block_name, max_lines=15)
                if diag:
                    lines.extend(diag)
                else:
                    lines.append("  (all active params have values)")

            return "\n".join(lines)
        return aspen.call(impl)
    except Exception as exc:
        return f"Error: {exc}"



def tool_simulation_warnings() -> list[str]:
    """Scan for common config issues and return warnings."""
    try:
        def impl():
            tree = aspen._app.RootModel("")
            warnings: list[str] = []

            # 检查连接模块之间的压力不匹配
            blks = walk(tree, "Data", "Blocks")
            if blks is not None:
                for i in range(200):
                    try:
                        b = blks.Elements(i)
                    except Exception:
                        break
                    if b is None:
                        break
                    bname = b.Name
                    bin_pres = walk(tree, "Data", "Blocks", bname, "Input", "PRES")
                    if bin_pres is None:
                        bin_pres = walk(tree, "Data", "Blocks", bname, "Input", "P_OUT")
                    ports = walk(tree, "Data", "Blocks", bname, "Ports")
                    if ports is not None:
                        for pi in range(30):
                            try:
                                p = ports.Elements(pi)
                            except Exception:
                                break
                            if p is None:
                                break
                            if "(IN)" in p.Name:
                                try:
                                    els = p.Elements
                                    for ei in range(els.Count):
                                        try:
                                            sname = els.Item(ei).Name
                                            sp = walk(tree, "Data", "Streams", sname, "Output", "PRES_OUT")
                                            if sp is not None and sp.Value:
                                                if bin_pres is not None and sp.Value and abs(float(sp.Value) - float(bin_pres.Value)) > 10:
                                                    warnings.append(
                                                        f"Pressure mismatch: Stream '{sname}' enters '{bname}' "
                                                        f"at {sp.Value} bar, block expects ~{bin_pres.Value} bar"
                                                    )
                                        except Exception:
                                            pass
                                except Exception:
                                    pass

            # 检查未连接的进料流股
            streams = walk(tree, "Data", "Streams")
            if streams is not None:
                for si in range(200):
                    try:
                        s = streams.Elements(si)
                    except Exception:
                        break
                    if s is None:
                        break
                    sname = s.Name
                    dest = walk(tree, "Data", "Streams", sname, "Output", "DESTINATION")
                    if dest is None or not dest.Value:
                        src = walk(tree, "Data", "Streams", sname, "Output", "SOURCE")
                        if src is None or not src.Value:
                            temp = walk(tree, "Data", "Streams", sname, "Input", "TEMP", "MIXED")
                            if temp is not None and temp.Value:
                                warnings.append(
                                    f"Unconnected stream '{sname}' has TEMP set but no destination"
                                )

            return warnings
        return aspen.call(impl)
    except Exception:
        return []
