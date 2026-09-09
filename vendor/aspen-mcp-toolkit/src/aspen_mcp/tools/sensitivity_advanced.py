"""Enhanced sensitivity analysis tool for Aspen Plus MCP.

Features:
  - Sweep a block variable and re-run
  - Auto-adjust linked params (e.g. FEED_STAGE when NSTAGE changes)
  - Read stream/block results after each run
  - Return structured results table (CSV-ready)
  - Auto-save results to JSON cache
"""

from __future__ import annotations

from typing import Any

from ..com_bridge import aspen
from .. import cache
from ._common import walk


def _com_read(path: str) -> Any:
    """Read a value from COM by backslash path (inside aspen.call)."""
    # path like "Data\\Blocks\\HPD\\Input\\NSTAGE"
    parts = path.replace("/", "\\").split("\\")
    node = walk(aspen._app.RootModel(""), *parts)
    if node is None:
        return None
    try:
        return node.Value
    except Exception:
        return str(node)


def _com_read_stream_mf(stream_name: str, component: str) -> float | None:
    """Read a component's mole fraction from a stream output (on COM thread)."""
    node = walk(aspen._app.RootModel(""),
                 "Data", "Streams", stream_name, "Output",
                 "MOLEFRAC", "MIXED", component)
    if node is None:
        return None
    try:
        return float(node.Value)
    except (ValueError, TypeError):
        return None


def tool_sensitivity(
    block_name: str,
    variable: str,
    values: list[float],
    linked_params: dict[str, float] | None = None,
    targets: list[str] | None = None,
    feed_stream: str | None = None,
    feed_temp: float | None = None,
    feed_pres: float | None = None,
    feed_composition: dict[str, float] | None = None,
    title: str = "",
) -> dict[str, Any]:
    """Sweep a block variable with linked params and collect results.

    Args:
        block_name: Block name, e.g. "HPD".
        variable: Input variable name, e.g. "NSTAGE".
        values: List of values to sweep, e.g. [100, 130, 160, 182].
        linked_params: Params to update proportionally, e.g.
            {"HPD\\\\FEED_STAGE\\\\FEED": 0.764,
             "HPD\\\\FEED_STAGE\\\\FLA-OUT": 1.0}
            Key = Data\\Blocks\\{block_name}\\Input\\{path} (relative to block)
            Value = multiplier (linked_param_value = variable_value * multiplier)
        targets: Paths to read results from after each run, e.g.
            ["Streams\\\\PRO-D\\\\MOLEFRAC\\\\MIXED\\\\PROPYLEN",
             "Streams\\\\PRO-B\\\\MOLEFRAC\\\\MIXED\\\\PROPANE",
             "Blocks\\\\COMP\\\\Output\\\\BRAKE_POWER",
             "Blocks\\\\HPD\\\\Output\\\\BOTTOM_TEMP",
             "Blocks\\\\HPD\\\\Output\\\\TOP_TEMP"]
        feed_stream: Name of feed stream to restore after each open.
        feed_temp: Feed temperature to restore.
        feed_pres: Feed pressure to restore.
        feed_composition: {component: flow} feed composition to restore.
        title: Optional label for this sensitivity run.

    Returns:
        {summary: "...", table: [{var, target1, target2, ...}], errors: [...]}
    """
    results_table: list[dict[str, Any]] = []
    errors: list[str] = []
    base_path = f"Data\\Blocks\\{block_name}\\Input\\"

    # Resolve linked param multipliers
    linked_mult: dict[str, float] = {}
    for param_path, mult in (linked_params or {}).items():
        full_path = f"Data\\Blocks\\{block_name}\\Input\\{param_path}"
        linked_mult[full_path] = mult

    # Resolve target paths
    target_labels: list[str] = []
    for t in (targets or []):
        label = t.split("\\")[-1]
        target_labels.append(label)

    for val in values:
        row: dict[str, Any] = {"var": val}

        try:
            # --- Set main variable ---
            def set_main():
                node = walk(aspen._app.RootModel(""),
                             "Data", "Blocks", block_name, "Input", variable)
                if node:
                    node.SetValue(0, val)
                # Set linked params
                for full_path, mult in linked_mult.items():
                    linked_val = val * mult
                    parts = full_path.split("\\")
                    ln = walk(aspen._app.RootModel(""), *parts)
                    if ln:
                        ln.SetValue(0, linked_val)
            aspen.call(set_main)
            row["var_set"] = "OK"

            # --- Run ---
            try:
                aspen.reinit_and_run()
                row["run"] = "OK"
            except TimeoutError as e:
                row["run"] = f"TIMEOUT"
                errors.append(f"val={val}: run timed out")
                results_table.append(row)
                continue
            except Exception as e:
                row["run"] = f"FAIL"
                errors.append(f"val={val}: run failed: {e}")
                results_table.append(row)
                continue

            # --- Read targets ---
            def read_targets():
                t_results = {}
                root = aspen._app.RootModel("")
                for t_path in (targets or []):
                    label = t_path.split("\\")[-1]
                    parts = t_path.split("\\")
                    if parts[0] == "Streams":
                        full = ["Data", "Streams", parts[1], "Output"] + parts[2:]
                    elif parts[0] == "Blocks":
                        full = ["Data", "Blocks", parts[1], "Output"] + parts[2:]
                    else:
                        full = ["Data"] + parts
                    node = walk(root, *full)
                    if node is not None:
                        try:
                            t_results[label] = node.Value
                        except Exception:
                            t_results[label] = str(node)[:60]
                    else:
                        t_results[label] = None
                # Read block status
                for key in ("BLKSTAT", "PER_ERROR"):
                    nd = walk(aspen._app.RootModel(""),
                               "Data", "Blocks", block_name, "Output", key)
                    if nd:
                        t_results[f"{block_name}_{key}"] = nd.Value
                return t_results

            target_results = aspen.call(read_targets)
            row.update(target_results)

        except Exception as e:
            row["error"] = str(e)[:100]
            errors.append(f"val={val}: {e}")

        results_table.append(row)

    # --- Build summary ---
    summary_lines = [
        f"Sensitivity: {block_name}.{variable}",
        f"  Values: {values}",
    ]
    if linked_params:
        summary_lines.append(f"  Linked params: {dict(linked_params)}")
    summary_lines.append(f"  Runs: {len(results_table)}, Errors: {len(errors)}")

    # Build text table
    if results_table:
        cols = list(results_table[0].keys())
        summary_lines.append("")
        summary_lines.append("  {:<8s}".format(cols[0]) + " ".join(f"{c:>14s}" for c in cols[1:]))
        summary_lines.append("  " + "-" * (8 + 15 * (len(cols) - 1)))
        for row in results_table:
            vals = [str(row.get(c, ""))[:12] for c in cols]
            summary_lines.append("  {:<8s}".format(vals[0]) + " ".join(f"{v:>14s}" for v in vals[1:]))

    # --- Save to cache ---
    try:
        cache.save_sensitivity(
            title=title or f"{block_name}.{variable}",
            variable=f"{block_name}.{variable}",
            linked_params=linked_params or {},
            results=results_table,
        )
    except Exception:
        pass

    return {
        "summary": "\n".join(summary_lines),
        "table": results_table,
        "errors": errors,
    }
