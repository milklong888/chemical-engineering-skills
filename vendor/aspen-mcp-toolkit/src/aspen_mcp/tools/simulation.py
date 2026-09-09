"""仿真控制工具：打开、关闭、运行、保存、状态。"""

from __future__ import annotations

from ..com_bridge import aspen
from .analysis import _get_convergence_report

def _walk(root, *parts):
    node = root
    for p in parts:
        try:
            node = node.Elements(p)
        except Exception:
            return None
    return node
def _check_all_uncalculated() -> str | None:
    """Check blocks after run: collect BLKMSG errors.
    In Aspen v15 (41.0), BLKSTAT=0 means "converged", not "uncalculated".
    BLKSTAT=2 means "not converged" (ran but diverged).
    BLKMSG has the actual Aspen error text.
    This function checks BLKMSG and BLKSTAT=2 to find actual problems.
    """
    try:
        def impl():
            tree = aspen._app.RootModel("")
            blks = _walk(tree, "Data", "Blocks")
            if blks is None:
                return None
            issues = []
            for i in range(500):
                try:
                    b = blks.Elements(i)
                except Exception:
                    break
                if b is None:
                    break
                bname = b.Name
                blkstat = _walk(tree, "Data", "Blocks", bname, "Output", "BLKSTAT")
                blkmsg = _walk(tree, "Data", "Blocks", bname, "Output", "BLKMSG")
                if blkmsg is not None and blkmsg.Value:
                    issues.append("  " + bname + ": BLKMSG=" + str(blkmsg.Value))
                elif blkstat is not None and blkstat.Value == 2:
                    issues.append("  " + bname + ": BLKSTAT=2 (not converged)")
            if issues:
                return "Block issues after run:\n" + "\n".join(issues)
            return None
        return aspen.call(impl)
    except Exception:
        return None
def _check_feeds_before_run() -> str | None:
    """Check feed stream inputs before running.
    A feed stream has no upstream block (no SOURCE in Output).
    Those require the user to set TEMP, PRES, and composition.
    Returns an error message if any feed is incomplete, None if all OK.
    """
    try:
        def impl():
            tree = aspen._app.RootModel("")
            streams_node = _walk(tree, "Data", "Streams")
            if streams_node is None:
                return None
            issues = []
            for i in range(500):
                try:
                    s = streams_node.Elements(i)
                except Exception:
                    break
                if s is None:
                    break
                sname = s.Name
                # 检查此流股是否连接在某个模块的输出端口上
                is_output = False
                blks = _walk(tree, "Data", "Blocks")
                if blks is not None:
                    for bi in range(500):
                        try:
                            b2 = blks.Elements(bi)
                        except Exception:
                            break
                        if b2 is None:
                            break
                        ports_node = _walk(tree, "Data", "Blocks", b2.Name, "Ports")
                        if ports_node is not None:
                            for pi in range(50):
                                try:
                                    port = ports_node.Elements(pi)
                                except Exception:
                                    break
                                if port is None:
                                    break
                                if "(OUT)" in port.Name:
                                    for ei in range(port.Elements.Count):
                                        try:
                                            if port.Elements.Item(ei).Name == sname:
                                                is_output = True
                                                break
                                        except Exception:
                                            pass
                                if is_output:
                                    break
                        if is_output:
                            break
                if is_output:
                    continue
                missing = []
                temp = _walk(tree, "Data", "Streams", sname, "Input", "TEMP", "MIXED")
                if temp is None or temp.Value is None:
                    missing.append("TEMP")
                pres = _walk(tree, "Data", "Streams", sname, "Input", "PRES", "MIXED")
                if pres is None or pres.Value is None:
                    missing.append("PRES")
                flow_node = _walk(tree, "Data", "Streams", sname, "Input", "FLOW", "MIXED")
                has_comp = False
                if flow_node is not None:
                    for ci in range(100):
                        try:
                            comp = flow_node.Elements(ci)
                        except Exception:
                            break
                        if comp is None:
                            break
                        if comp.Value is not None and comp.Value > 0:
                            has_comp = True
                            break
                if not has_comp:
                    total = _walk(tree, "Data", "Streams", sname, "Input", "TOTAL", "MIXED")
                    if total is None or total.Value is None or total.Value == 0:
                        missing.append("composition (no component flow or total flow)")
                if missing:
                    issues.append(
                        "  Stream '" + sname + "' missing: " + ", ".join(missing)
                    )
            if issues:
                NL = "\n"
                result = "Feed stream inputs incomplete. "
                result += "Please set these before running:" + NL
                result += NL.join(issues)
                result += NL + NL + "Tip: set_stream_param('name', 'TEMP', value)"
                result += " / set_stream_param('name', 'PRES', value)" + NL
                result += "      set_stream_composition('name', 'component', flow)"
                return result
            return None
        return aspen.call(impl)
    except Exception:
        return None
def tool_status() -> dict:
    """Return the current Aspen Plus connection / engine status."""
    return aspen.status()
def tool_open_file(file_path: str) -> str:
    """Open an Aspen Plus simulation .apw file."""
    try:
        aspen.open_file(file_path)
        return "Opened " + file_path
    except Exception as exc:
        exc_str = str(exc)
        if "32" in exc_str and ("being used" in exc_str.lower() or chr(214) in exc_str):
            return "File is locked: " + str(exc) + ". Try close_file() first, then retry open_file()."
        if "RPC" in exc_str:
            return "COM error: " + str(exc) + ". Try close_file() then open_file() again."
        return "Error: " + str(exc)
def tool_close_file() -> str:
    """Close the currently-open simulation file."""
    try:
        aspen.close_file()
        return "File closed"
    except Exception as exc:
        return "Error: " + str(exc)
def tool_run() -> str:
    """Run the simulation (synchronous) and return convergence diagnostics."""
    try:
        feed_ok = _check_feeds_before_run()
        if feed_ok:
            return feed_ok
        aspen.run()
        report = aspen.call(lambda: _get_convergence_report())
        result = "Simulation run completed.\n\n" + (report or "")
        warning = _check_all_uncalculated()
        if warning:
            result += "\n\n" + (warning or "")
        return result
    except Exception as exc:
        exc_str = str(exc)
        if "RPC" in exc_str or chr(26381) in exc_str:
            return "COM error: " + str(exc) + ". Try close_file() then open_file() to recover, then reinit_and_run()."
        return "Error: " + str(exc)
def tool_run_async() -> str:
    """Run the simulation (asynchronous, non-blocking)."""
    try:
        aspen.run_async()
        return "Async simulation started"
    except Exception as exc:
        return "Error: " + str(exc)
def tool_save(file_path: str | None = None) -> str:
    """Save the simulation. Optionally provide SaveAs path."""
    try:
        aspen.save(file_path)
        return "Saved to " + str(file_path) if file_path else "File saved"
    except Exception as exc:
        return "Error: " + str(exc)
def tool_reinit() -> str:
    """Reinitialize the simulation (reset results before re-running)."""
    try:
        aspen.reinit()
        return "Simulation reinitialized"
    except Exception as exc:
        return "Error: " + str(exc)
def tool_reinit_and_run() -> str:
    """Reinitialize then run synchronously.
    Reinit() clears old engine caches so Aspen rebuilds calculation order;
    Run2(0) executes synchronously.
    """
    try:
        feed_ok = _check_feeds_before_run()
        if feed_ok:
            return feed_ok
        aspen.reinit_and_run()
        report = aspen.call(lambda: _get_convergence_report())
        result = "Simulation reinitialized and run completed.\n\n" + (report or "")
        warning = _check_all_uncalculated()
        if warning:
            result += "\n\n" + (warning or "")
        return result
    except Exception as exc:
        exc_str = str(exc)
        if "RPC" in exc_str or chr(26381) in exc_str:
            return "COM error: " + str(exc) + ". Try close_file() then open_file() to recover, then reinit_and_run() again."
        return "Error: " + str(exc)
def tool_new_simulation() -> str:
    """创建一个新的空白模拟。

    使用 Aspen 内置的 InitNew() 创建空白模拟，
    包含 0 个组分和空拓扑。
    无需外部模板文件。
    """
    try:
        try:
            aspen.call(lambda: aspen._app.InitNew())
        except Exception:
            # 如果已初始化（错误 2001），仅执行 reinit
            aspen.reinit()
        return ("New blank simulation created.\n"
                "  - Components: none (add with add_component)\n"
                "  - Property: PENG-ROB (change with set_property_method)\n"
                "  - Topology: empty (add with add_block / add_stream)\n"
                "Tip: run reinit_and_run() before first use to clear old results.")
    except Exception as exc:
        return "Error: " + str(exc)


def tool_stop_simulation() -> str:
    """Stop the currently running simulation."""
    try:
        aspen.stop()
        return "Simulation stopped."
    except Exception as exc:
        return "Error: " + str(exc)
def tool_visible(show: bool) -> str:
    """Show or hide the Aspen Plus GUI window."""
    try:
        aspen.set_visible(show)
        return "Aspen Plus window is now " + ("visible" if show else "hidden") + "."
    except Exception as exc:
        return "Error: " + str(exc)
def tool_run_script(file_path: str) -> str:
    '''Run a Python script inside Aspen Plus.
    The script runs in Aspen's internal Python environment,
    not the MCP host environment.
    '''
    try:
        aspen.run_script(file_path)
        return "Script '" + file_path + "' executed."
    except Exception as exc:
        return "Error: " + str(exc)
def tool_batch_refresh(off: bool) -> str:
    """Disable or re-enable GUI refresh.
    Turn refresh OFF before a series of bulk operations for speed,
    then turn it back ON when done.
    """
    try:
        aspen.set_batch_refresh(off)
        return "GUI refresh " + ("disabled" if off else "enabled") + "."
    except Exception as exc:
        return "Error: " + str(exc)