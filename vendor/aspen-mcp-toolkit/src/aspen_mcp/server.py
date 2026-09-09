"""
aspen_mcp.server — FastMCP entry point.

Registers all tools and runs the MCP server on stdio.
"""

from __future__ import annotations

import logging
import sys

from fastmcp import FastMCP

from .com_bridge import aspen
from .tools.simulation import (
    tool_status,
    tool_open_file,
    tool_close_file,
    tool_run,
    tool_run_async,
    tool_save,
    tool_reinit,
    tool_reinit_and_run,
    tool_new_simulation,
    tool_stop_simulation,
    tool_visible,
    tool_run_script,
    tool_batch_refresh,
)
from .tools.streams import (
    tool_list_all_streams,
    tool_get_stream,
    tool_get_stream_composition_info,
    tool_set_stream_param,
    tool_set_stream_composition,
    tool_set_stream_composition_batch,
    tool_add_stream,
    tool_remove_stream,
    tool_connect,
    tool_connect_port,
    tool_disconnect,
    tool_list_block_ports,
)
from .tools.blocks import (
    tool_list_all_blocks,
    tool_get_block,
    tool_block_status,
    tool_set_param,
    tool_add_block,
    tool_remove_block,
    tool_explore,
)
from .tools.components import (
    tool_list_components,
    tool_add_component,
    tool_remove_component,
    tool_get_property_method,
    tool_set_property_method,
)
from .tools.reactions import (
    tool_add_reaction_set,
    tool_remove_reaction_set,
    tool_add_reaction,
    tool_remove_reaction,
    tool_list_reaction_sets,
)
from .tools.analysis import (
    tool_sensitivity,
    tool_export_report_file,
    tool_diagnose,
    tool_search_convergence_knowledge,
    tool_generate_input_summary,
    tool_find_incomplete_inputs,
    tool_list_tear_streams,
    tool_set_tear_estimate,
    tool_validate_block,
    tool_simulation_warnings,
)
from .tools.deep_probe import tool_deep_probe
from .tools.fix_trivial import tool_fill_trivial_params
from .tools.flowsheet import (
    tool_flowsheet_topology,
    tool_add_side_duty,
    tool_remove_side_duty,
    tool_configure_fsplit,
)
from .tools.columns import (
    tool_set_column_stages,
    tool_set_condenser_type,
    tool_set_reboiler_type,
    tool_set_feed_stage,
    tool_set_product_stage,
    tool_set_column_pressure,
)
from .tools.sensitivity_advanced import (
    tool_sensitivity,
)
from .tools.utilities import (
    tool_add_utility,
    tool_list_utilities,
    tool_remove_utility,
    tool_get_utility,
    tool_remove_utility,
)

from .tools.paths import (
    tool_get_value,
    tool_set_value,
)

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s  %(name)s  %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("aspen_mcp")

# 在主线程上初始化 COM，这样从 COM 套间线程返回的 COM 代理对象可以正确封送。
try:
    import pythoncom
    pythoncom.CoInitialize()
    logger.info("CoInitialize on main thread")
except Exception:
    pass


def create_server() -> FastMCP:
    mcp = FastMCP("Aspen Plus MCP")

    # ── simulation ───────────────────────────────────────────────────────

    @mcp.tool()
    def status() -> dict:
        """获取 Aspen Plus 连接和引擎状态。"""
        return tool_status()

    @mcp.tool()
    def probe() -> dict:
        """Diagnose COM state (app, root, tree access)."""
        try:
            return aspen.probe()
        except Exception as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def open_file(file_path: str) -> str:
        """Open an Aspen Plus .apw simulation file.

        Example: open_file("C:/path/to/simulation.apw")

        Opens the file in the Aspen engine. Call list_all_blocks()
        and list_all_streams() afterward to verify the topology loaded.
        """
        return tool_open_file(file_path)

    @mcp.tool()
    def close_file() -> str:
        """Close the currently open simulation file. mutates=True."""
        return tool_close_file()

    @mcp.tool()
    def run() -> str:
        """Run the simulation. mutates=True.

        Auto-checks feed streams for missing TEMP/PRES/composition.
        30-second timeout — returns error if engine hangs.

        After run, check:
          get_stream("name")           — stream results (T, P, flow, comp)
          block_status("name")          — convergence status
          diagnose(["convergence"])      — failure analysis
        """
        return tool_run()

    @mcp.tool()
    def run_async() -> str:
        """运行模拟（异步）。"""
        return tool_run_async()

    @mcp.tool()
    def save(file_path: str | None = None) -> str:
        """Save the simulation. Optionally provide Save As path.

        save("C:/output.apw")      — save to a new file
        save()                      — overwrite current file
        """
        return tool_save(file_path)

    @mcp.tool()
    def reinit() -> str:
        """重新初始化模拟（重置结果）。"""
        return tool_reinit()

    @mcp.tool()
    def reinit_and_run() -> str:
        """Reinitialize (clear results) then run. mutates=True.

        Equivalent to reinit() + run(). Preferred over run()
        when you have changed parameters and need a clean start.
        """
        return tool_reinit_and_run()

    @mcp.tool()
    def new_simulation() -> str:
        """Create a blank simulation with 0 components and empty topology.

        mutates=True. Creates fresh sim with PENG-ROB property method.

        Typical workflow:
          new_simulation()
          add_component("WATER") -> set_property_method("NRTL")
          add_block("H1","HEATER") -> add_stream("FEED")
          set_stream_param("FEED","TEMP",25) -> run()
        """
        return tool_new_simulation()

    @mcp.tool()
    def stop_simulation() -> str:
        """停止当前运行的模拟。"""
        return tool_stop_simulation()

    @mcp.tool()
    def visible(show: bool) -> str:
        """显示或隐藏 Aspen Plus GUI 窗口。"""
        return tool_visible(show)

    @mcp.tool()
    def run_script(file_path: str) -> str:
        """在 Aspen Plus 内部执行 Python 脚本。"""
        return tool_run_script(file_path)

    @mcp.tool()
    def batch_refresh(off: bool) -> str:
        """禁用或启用 GUI 刷新（加速批量操作）。"""
        return tool_batch_refresh(off)

    # ── streams ──────────────────────────────────────────────────────────

    @mcp.tool()
    def list_all_streams() -> list[str]:
        """List every stream name in the flowsheet.

        Returns: ["FEED","PRODUCT","RECYCLE",...].
        Use get_stream("name") for individual results.
        """
        return tool_list_all_streams()

    @mcp.tool()
    def get_stream(name: str) -> dict:
        """Read stream results after simulation.

        Example: get_stream("PRODUCT")

        Returns: res_temp, res_pres, res_vfrac, res_massflow,
        res_moleflow, res_volflow, mw, comptype,
        mole_frac_liq (liquid composition), mole_frac_vap (vapor).
        """
        return tool_get_stream(name)

    @mcp.tool()
    def get_stream_composition_info(name: str) -> dict:
        """获取流股组成元数据（COMPTYPE、分子量、流量）。"""
        return tool_get_stream_composition_info(name)

    @mcp.tool()
    def set_stream_param(stream_name: str, param: str, value: float, basis: str | None = None) -> str:
        """Set a feed-stream input parameter. mutates=True.

        Examples:
          set_stream_param("FEED", "TEMP", 25)       — temperature
          set_stream_param("FEED", "PRES", 1.5)       — pressure
          set_stream_param("FEED", "TOTAL", 100)      — total molar flow
          set_stream_param("S1", "VFRAC", 0.0)        — vapor fraction

        Value unit follows the current Unit-Set (METCBAR: C/bar/kmol/hr).
        For composition, use set_stream_composition_batch.
        """
        return tool_set_stream_param(stream_name, param, value, basis)

    @mcp.tool()
    def set_stream_composition(stream_name: str, component: str, flow: float) -> str:
        """设置某组分的's 摩尔流量。

        NOTE: IDs over 8 chars get truncated (PROPYLENE -> PROPYLEN).
        Use list_components() to see actual labels.

        Args:
            stream_name: Stream name.
            component: Component label (confirmed via list_components).
            flow: Molar flow (unit depends on Unit-Set).
        """
        return tool_set_stream_composition(stream_name, component, flow)

    @mcp.tool()
    def set_stream_composition_batch(stream_name: str, components: dict[str, float],
                                     basis: str = "MOLE-FLOW",
                                     total_flow: float | None = None) -> str:
        """批量设置流股组成，带 BASIS 控制和可选总流量。

        Handles BASIS switching, all components, and total flow in one call.
        Use this instead of calling set_stream_composition repeatedly.

        Args:
            stream_name: Stream name (e.g. 'FEED').
            components: {component_id: value} dict.
            basis: MOLE-FLOW (default), MASS-FLOW, MOLE-FRAC, MASS-FRAC.
            total_flow: Required when basis is a fraction (e.g. MOLE-FRAC).

        Examples:
            set_stream_composition_batch("FEED", {"ETHANOL": 50, "WATER": 50})
            set_stream_composition_batch("FEED", {"ETHANOL": 0.5, "WATER": 0.5},
                                         basis="MOLE-FRAC", total_flow=100)
        """
        return tool_set_stream_composition_batch(stream_name, components, basis, total_flow)

    @mcp.tool()
    def add_stream(name: str) -> str:
        """Add a new stream to the flowsheet. mutates=True.

        add_stream("FEED")     — create a feed stream
        """
        return tool_add_stream(name)

    @mcp.tool()
    def remove_stream(name: str) -> str:
        """Remove a stream from the flowsheet. mutates=True.

        Disconnect the stream from all ports first with disconnect().
        """
        return tool_remove_stream(name)

    @mcp.tool()
    def connect(source_block: str, dest_block: str, stream_name: str | None = None,
                  source_port: str | None = None, dest_port: str | None = None) -> str:
        """Connect two blocks with a stream. mutates=True.

        Default ports: P(OUT) on source, F(IN) on dest.
        Auto-creates stream if not given (name = "source-dest").

        Examples:
          connect("H1", "F1")                           — heater → flash
          connect("F1", "GAS", source_port="V(OUT)")    — flash vapor outlet
          connect("F1", "LIQ", source_port="L(OUT)")    — flash liquid outlet
          connect("FEED", "H1")                         — feed stream → heater
        """
        return tool_connect(source_block, dest_block, stream_name, source_port, dest_port)

    @mcp.tool()
    def connect_port(block_name: str, port_name: str, stream_name: str) -> str:
        """Connect a stream to a single block port. mutates=True.

        Examples:
          connect_port("F1", "V(OUT)", "VAPOR")    — flash vapor
          connect_port("F1", "L(OUT)", "LIQUID")   — flash liquid
          connect_port("M1", "F(IN)", "FEED2")     — second mixer feed

        Use list_block_ports("name") to see available ports.
        """
        return tool_connect_port(block_name, port_name, stream_name)

    @mcp.tool()
    def disconnect(stream_name: str) -> str:
        """Disconnect a stream from all ports and remove it. mutates=True.

        disconnect("S1")

        Uses snapshot-first algorithm: scans all connections,
        removes from ports, then cleans up the Streams collection.
        Safe to call before remove_block().
        """
        return tool_disconnect(stream_name)

    @mcp.tool()
    def list_block_ports(block_name: str) -> str:
        """List available ports on a block and their connected streams.

        list_block_ports("F1")
          → Ports: F(IN)->[FEED], V(OUT)->[VAPOR], L(OUT)->[LIQUID]
        """
        return tool_list_block_ports(block_name)

    # ── blocks ───────────────────────────────────────────────────────────

    @mcp.tool()
    def list_all_blocks() -> list[str]:
        """List every block name in the flowsheet.

        Returns: ["H1","F1","C1","R1",...].
        Use get_block("name") for individual specifications.
        """
        return tool_list_all_blocks()

    @mcp.tool()
    def get_block(name: str) -> dict:
        """Read block specifications and output results.

        get_block("H1") — returns input specs + output values.
        Use block_status("H1") for convergence status only.
        """
        return tool_get_block(name)

    @mcp.tool()
    def set_param(block_name: str, param: str, value: str | float) -> str:
        """Set a block operating parameter. mutates=True.

        Common params: TEMP, PRES, DUTY, VFRAC, NPHASE.

        Examples:
          set_param("H1", "TEMP", 150)       -- heater outlet T
          set_param("H1", "PRES", 5)         -- operating pressure
          set_param("F1", "TEMP", 80)        -- flash temperature
          set_param("H1", "DUTY", -500)      -- heat duty (neg=cooling)

        For streams, use set_stream_param. Streams and blocks have
        separate parameter trees in the Aspen COM object model.
        """
        return tool_set_param(block_name, param, value)

    @mcp.tool()
    def add_block(name: str, block_type: str) -> str:
        """Add a unit operation block. mutates=True.

        Common types: HEATER, FLASH2, FLASH3, RADFRAC, RPLUG,
        RGIBBS, RSTOIC, MIXER, FSPLIT, PUMP, COMPR, VALVE, HEATX.

        Examples:
          add_block("H1", "HEATER")         — heater/cooler
          add_block("F1", "FLASH2")         — two-phase flash
          add_block("C1", "RADFRAC")        — distillation column
          add_block("R1", "RGIBBS")         — Gibbs reactor (no RXN_ID)

        RPLUG/RCSTR require a reaction set ID (RXN_ID).
        """
        return tool_add_block(name, block_type)

    @mcp.tool()
    def remove_block(name: str) -> str:
        """Delete a block from the flowsheet. mutates=True.

        IMPORTANT: disconnect all connected streams first,
        then remove_block(). Wrong order crashes the COM server.
        Use list_block_ports("name") to check connections.
        """
        return tool_remove_block(name)

    @mcp.tool()
    def block_status(name: str) -> dict:
        """Read block convergence status after run.

        Returns: BLKSTAT (0=OK, 2=not converged), PER_ERROR,
        PROPSTAT, BLKMSG (error text from Aspen).
        """
        return tool_block_status(name)

    @mcp.tool()
    def explore(path: str) -> dict:
        """Explore the Aspen COM object tree.

        explore("Data\\Blocks")      — list block nodes
        explore("Data\\Properties")  — list property nodes
        """
        return tool_explore(path)

    # ── components / property ───────────────────────────────────────────────

    @mcp.tool()
    def list_components() -> list[str]:
        """List all components in the simulation.

        Returns: ["WATER","ETHANOL","..."] — the Aspen-internal labels.
        Use these labels in add_reaction, set_stream_composition, etc.
        """
        return tool_list_components()

    @mcp.tool()
    def add_component(component_id: str) -> str:
        """Add a component from Aspen databank. mutates=True.

        Examples:
          add_component("WATER")        — water
          add_component("ETHANOL")      — ethanol
          add_component("ETHYLBEN")     — ethylbenzene

        IDs over 8 chars get truncated (PROPYLENE→PROPYLEN).
        Call list_components() after to confirm labels.
        Call BEFORE add_block/add_stream — components must exist
        before they can appear in streams.
        """
        return tool_add_component(component_id)

    @mcp.tool()
    def remove_component(component_id: str) -> str:
        """Remove a component from the simulation. mutates=True.

        remove_component("WATER")
        """
        return tool_remove_component(component_id)

    @mcp.tool()
    def get_property_method() -> str:
        """Get the current global property method.

        Returns: "PENG-ROB", "NRTL", "NRTL-RK", etc.
        """
        return tool_get_property_method()

    @mcp.tool()
    def set_property_method(method: str) -> str:
        """Set the global property method. mutates=True.

        set_property_method("NRTL-RK")     — alcohols/water
        set_property_method("PENG-ROB")    — hydrocarbons
        set_property_method("ELECNRTL")    — electrolytes
        """
        return tool_set_property_method(method)

    # ── reactions ───────────────────────────────────────────────────────────

    @mcp.tool()
    def add_reaction_set(name: str, reaction_type: str = "POWERLAW") -> str:
        """Create a reaction set. mutates=True.

        add_reaction_set("R-1")                        — POWERLAW (default)
        add_reaction_set("R-1", "EQUILIBRIUM")         — equilibrium
        """
        return tool_add_reaction_set(name, reaction_type)

    @mcp.tool()
    def remove_reaction_set(name: str) -> str:
        """Delete a reaction set and all its reactions. mutates=True."""
        return tool_remove_reaction_set(name)

    @mcp.tool()
    def add_reaction(
        reaction_set: str,
        reaction_no: int,
        reactants: dict[str, float],
        products: dict[str, float],
        phase: str = "L",
        exponents: dict[str, float] | None = None,
    ) -> str:
        """Add a stoichiometric reaction to a set. mutates=True.

        add_reaction("R-1", 1,
          reactants={"CO2":1,"H2":4}, products={"CH4":1,"H2O":2})

        Note: RXN_ID cannot be set via COM. Use RGIBBS reactor (no RXN_ID).
        """
        return tool_add_reaction(reaction_set, reaction_no, reactants, products, phase, exponents)

    @mcp.tool()
    def remove_reaction(reaction_set: str, reaction_no: int) -> str:
        """Remove a single reaction from a set. mutates=True."""
        return tool_remove_reaction(reaction_set, reaction_no)

    @mcp.tool()
    def list_reaction_sets() -> list[str]:
        """List all reaction sets."""
        return tool_list_reaction_sets()

    # ── flowsheet topology ───────────────────────────────────────────────

    @mcp.tool()
    def flowsheet_topology() -> str:
        """Show flowsheet topology: SOURCE --[stream]--> DEST.

        Returns a text diagram of all block connections.
        """
        return tool_flowsheet_topology()

    @mcp.tool()
    def add_side_duty(block_name: str, stage: int, duty: float) -> str:
        """Add/update side heater/cooler duty on a column stage. mutates=True.

        add_side_duty("C1", 5, -500)    — 500 kW cooling at stage 5
        """
        return tool_add_side_duty(block_name, stage, duty)

    @mcp.tool()
    def remove_side_duty(block_name: str, stage: int) -> str:
        """Remove side duty from a column stage. mutates=True."""
        return tool_remove_side_duty(block_name, stage)

    # ── generic path access ──────────────────────────────────────────────

    @mcp.tool()
    def get_value(path: str) -> str:
        """Read a value by Aspen COM path.

        get_value("\\Data\\Streams\\FEED\\Output\\RES_TEMP")
        """
        return tool_get_value(path)

    @mcp.tool()
    def set_value(path: str, value: str | float, unit: str | None = None) -> str:
        """Write a value by Aspen COM path. mutates=True.

        set_value("\\Data\\Blocks\\H1\\Input\\TEMP", 150)
        """
        return tool_set_value(path, value, unit)

    # ── analysis ─────────────────────────────────────────────────────────

    @mcp.tool()
    def sensitivity(
        block_name: str,
        variable: str,
        values: list[float],
        unit: str = "",
        linked_params: dict[str, float] | None = None,
        targets: list[str] | None = None,
        feed_stream: str | None = None,
        feed_temp: float | None = None,
        feed_pres: float | None = None,
        feed_composition: dict[str, float] | None = None,
        title: str = "",
    ) -> dict:
        """Run sensitivity analysis: vary one parameter, collect results.

        sensitivity("H1","TEMP",[100,150,200,...])
          — vary heater temperature, collect stream results at each value.
        """
        return tool_sensitivity(
            block_name, variable, values, linked_params, targets,
            feed_stream, feed_temp, feed_pres, feed_composition, title,
        )

    @mcp.tool()
    def export_report_file(file_path: str) -> str:
        """Export simulation report as .rep file."""
        return tool_export_report_file(file_path)

    @mcp.tool()
    def diagnose(keywords: list[str]) -> str:
        """Diagnose convergence problems: live status + knowledge search.

        diagnose(["Wegstein"])           — search for solver issues
        diagnose(["COLUMN DRIES UP"])    — search for column failures
        diagnose(["NRTL"])               — search for property issues

        Shows BLKSTAT/PER_ERROR for all blocks, plus knowledge base results.
        """
        return tool_diagnose(keywords)

    @mcp.tool()
    def search_convergence_knowledge(keywords: list[str]) -> list[dict]:
        """Search the convergence knowledge base by keywords.

        Returns ranked knowledge entries. Use diagnose() instead
        for a combined status report + knowledge search.
        """
        return tool_search_convergence_knowledge(keywords)

    @mcp.tool()
    def generate_input_summary(file_path: str) -> str:
        """Export input summary as .bkp file for debugging.

        Writes to a TEMP file — does NOT overwrite your original.
        """
        return tool_generate_input_summary(file_path)

    @mcp.tool()
    def find_incomplete_inputs() -> str:
        """Find incomplete inputs grouped by severity.

        Categories: Critical (must fill) / Mode-irrelevant / Optional.
        Call fill_trivial_params() first to reduce noise.
        """
        return tool_find_incomplete_inputs()

    # -- tear streams -------------------------------------------------------

    @mcp.tool()
    def list_tear_streams() -> list[str]:
        """List all tear streams (recycle loops) in the simulation.

        Each tear stream is Aspen's "guess point" for a recycle loop.
        Use set_tear_estimate() to provide better initial values.
        """
        return tool_list_tear_streams()

    @mcp.tool()
    def set_tear_estimate(stream_name: str, temp: float | None = None,
                           pres: float | None = None,
                           total_flow: float | None = None) -> str:
        """Set initial estimates for a tear (recycle) stream. mutates=True.

        set_tear_estimate("RECYCLE", temp=200, pres=2, total_flow=50)

        Good estimates speed up convergence in recycle loops.
        """
        return tool_set_tear_estimate(stream_name, temp, pres, total_flow)

    # -- simulation warnings -------------------------------------------------

    @mcp.tool()
    def simulation_warnings() -> list[str]:
        """Scan for common issues: pressure mismatches, disconnected feeds.

        Call before run() to catch obvious configuration errors.
        """
        return tool_simulation_warnings()

    @mcp.tool()
    def validate_block(block_name: str) -> str:
        """Check if a block is ready to run.

        validate_block("H1") — returns Engine.Ready status +
        missing input diagnostics.
        """
        return tool_validate_block(block_name)

    @mcp.tool()
    def fill_trivial_params() -> str:
        """Fill harmless active-but-unset params with safe defaults.

        Call BEFORE find_incomplete_inputs() to reduce noise from
        COM infrastructure / UI artifacts / estimation placeholders.
        """
        return tool_fill_trivial_params()

    @mcp.tool()
    def deep_probe(block_name: str = "") -> str:
        """Deep-probe a block's input node attributes for debugging."""
        return tool_deep_probe(block_name)

    # -- fsplit ---------------------------------------------------------------

    @mcp.tool()
    def configure_fsplit(block_name: str, outlet_name: str, frac: float) -> str:
        """Configure a stream splitter outlet. mutates=True.

        configure_fsplit("S-1","RECYCLE",0.3)  — 30% to RECYCLE
        """
        return tool_configure_fsplit(block_name, outlet_name, frac)

    # -- column configuration ---------------------------------------------------

    @mcp.tool()
    def set_column_stages(block_name: str, nstage: int) -> str:
        """Set total stages on a distillation column. mutates=True.

        set_column_stages("C1", 20)    — 20 theoretical stages
        Includes condenser and reboiler. Range: >=2.
        """
        return tool_set_column_stages(block_name, nstage)

    @mcp.tool()
    def set_condenser_type(block_name: str, condenser_type: str) -> str:
        """Set column condenser type. mutates=True.

        set_condenser_type("C1", "TOTAL")     — total condenser
        set_condenser_type("C1", "PARTIAL-V") — partial vapor product
        """
        return tool_set_condenser_type(block_name, condenser_type)

    @mcp.tool()
    def set_reboiler_type(block_name: str, reboiler_type: str) -> str:
        """Set column reboiler type. mutates=True.

        set_reboiler_type("C1", "KETTLE")
        """
        return tool_set_reboiler_type(block_name, reboiler_type)

    @mcp.tool()
    def set_feed_stage(block_name: str, stream_name: str, stage: int) -> str:
        """Set feed stage on a column. mutates=True.

        set_feed_stage("C1", "FEED", 10)    — feed enters at stage 10
        Stream must already be connected via connect()/connect_port().
        """
        return tool_set_feed_stage(block_name, stream_name, stage)

    @mcp.tool()
    def set_product_stage(block_name: str, stream_name: str,
                           stage: int, phase: str = "L") -> str:
        """Set product draw stage and phase on a column. mutates=True.

        set_product_stage("C1", "DIST", 1, phase="L")   — distillate
        set_product_stage("C1", "BOTS", 20, phase="L")  — bottoms
        """
        return tool_set_product_stage(block_name, stream_name, stage, phase)

    @mcp.tool()
    def set_column_pressure(block_name: str, top_pres: float,
                             dp_stage: float | None = None) -> str:
        """Set column pressure profile. mutates=True.

        set_column_pressure("C1", 5.0)               — constant 5 bar
        set_column_pressure("C1", 5.0, dp_stage=0.1) — 5 bar top, 0.1 bar/stage drop
        """
        return tool_set_column_pressure(block_name, top_pres, dp_stage)

    # -- utility tools ------------------------------------------------------------

    @mcp.tool()
    def add_utility(utility_name: str, utility_type: str, block_name: str | None = None, params: dict | None = None) -> str:
        """Add a utility (WATER, STEAM, ELECTRICITY, REFRIGERANT, FUEL, FURNACE)."""
        return tool_add_utility(utility_name, utility_type, block_name, params)

    @mcp.tool()
    def list_utilities() -> list[str]:
        """List all defined utilities."""
        return tool_list_utilities()

    @mcp.tool()
    def remove_utility(name: str) -> str:
        """Remove a utility."""
        return tool_remove_utility(name)

    # -- cache / call log ---------------------------------------------------

    # -- help ----------------------------------------------------------------

    logger.info("All tools registered")
    return mcp


mcp_server = create_server()


def main() -> None:
    """Entry point: connect to Aspen and run the MCP server."""
    mcp_server.run(transport="stdio")


if __name__ == "__main__":
    main()
