"""Component and property method tools."""

from __future__ import annotations

from ..com_bridge import aspen
from ._common import walk


# All COM operations must run inside aspen.call() lambdas so they
# execute on the dedicated COM apartment thread (STA).


def tool_list_components() -> list[str]:
    """List all components in the simulation."""
    try:
        def impl():
            tree = aspen._app.RootModel("")
            node = walk(tree, "Data", "Components", "Specifications", "Input", "TYPE")
            if node is None:
                return ["(components node not found)"]
            elems = node.Elements
            comps = []
            for i in range(elems.Count):
                try:
                    comps.append(elems.Item(i).Name)
                except Exception:
                    break
            return comps
        return aspen.call(impl)
    except Exception as exc:
        return [f"Error: {exc}"]


def tool_add_component(component_id: str) -> str:
    """Add a component to the simulation by name/ID.

    Accepts short IDs (e.g. WATER, ETHANOL) or long names.
    Long names (>8 chars) auto-generate a short label and
    write the full name to ANAME for databank resolution.
    """
    try:
        def impl():
            tree = aspen._app.RootModel("")
            node = walk(tree, "Data", "Components", "Specifications", "Input", "TYPE")
            if node is None:
                return "Error: components node not found"
            elems = node.Elements

            # Check for duplicates
            existing = set()
            for i in range(elems.Count):
                existing.add(elems.Item(i).Name.upper())

            needs_aname = len(component_id) > 8
            if needs_aname:
                label = component_id.upper().replace(" ", "").replace("-", "")[:8]
            else:
                label = component_id.upper()

            if label in existing:
                base = label[:6]
                for suffix in range(1, 100):
                    candidate = f"{base}{suffix}"[:8]
                    if candidate.upper() not in existing:
                        label = candidate
                        break
                else:
                    return f"Error: cannot generate unique label for '{component_id}'"

            # Insert row (2-column table: [Label, Type])
            elems.InsertRow(0, 0)
            elems.SetLabel(0, 0, False, label)

            # For long names, write ANAME for databank resolution
            if needs_aname:
                try:
                    aname_node = walk(tree, "Data", "Components", "Specifications",
                                       "Input", "ANAME", label)
                    if aname_node is not None:
                        aname_node.Value = component_id
                except Exception:
                    pass

            # Read back what Aspen resolved
            resolved = ""
            try:
                aname_node = walk(tree, "Data", "Components", "Specifications",
                                   "Input", "ANAME", label)
                dbname_node = walk(tree, "Data", "Components", "Specifications",
                                    "Input", "DBNAME", label)
                if aname_node and aname_node.Value:
                    resolved += f", alias={aname_node.Value}"
                if dbname_node and dbname_node.Value:
                    resolved += f", dbname={dbname_node.Value}"
            except Exception:
                pass

            return f"Component '{label}' added{resolved}."

        return aspen.call(impl)
    except Exception as exc:
        exc_str = str(exc)
        if "already specified" in exc_str.lower():
            return (
                f"Component '{component_id}' already exists in the simulation.\n"
                f"Use list_components() to see existing components, "
                f"or use a different ID."
            )
        return f"Error adding component '{component_id}': {exc}"


def tool_remove_component(component_id: str) -> str:
    """Remove a component from the simulation by its ID/label."""
    try:
        def impl():
            tree = aspen._app.RootModel("")
            node = walk(tree, "Data", "Components", "Specifications", "Input", "TYPE")
            if node is None:
                return "Error: components node not found"
            elems = node.Elements

            target_idx = None
            for i in range(elems.Count):
                if elems.Item(i).Name.upper() == component_id.upper():
                    target_idx = i
                    break

            if target_idx is None:
                return f"Component '{component_id}' not found."

            elems.RemoveRow(0, target_idx)
            return f"Component '{component_id}' removed."
        return aspen.call(impl)
    except Exception as exc:
        return f"Error removing component '{component_id}': {exc}"


# --- Property method --------------------------------------------------------


def tool_get_property_method() -> str:
    """Get the current global property method (e.g. PENG-ROB, NRTL)."""
    try:
        def impl():
            tree = aspen._app.RootModel("")
            gops = walk(tree, "Data", "Properties", "Specifications", "Input", "GOPSETNAME")
            if gops is None:
                return "(property method node not found)"
            return str(gops.Value)
        return aspen.call(impl)
    except Exception as exc:
        return f"Error: {exc}"


def tool_set_property_method(method: str) -> str:
    """Set the global property method (e.g. NRTL, PENG-ROB, UNIQUAC, IDEAL)."""
    try:
        def impl():
            tree = aspen._app.RootModel("")
            gbase = walk(tree, "Data", "Properties", "Specifications", "Input", "GBASEOPSET")
            gops = walk(tree, "Data", "Properties", "Specifications", "Input", "GOPSETNAME")
            if gbase is None or gops is None:
                return "Error: property method node not found"
            gbase.SetValue(0, method)
            gops.SetValue(0, method)
            return f"Property method set to '{method}'."
        return aspen.call(impl)
    except Exception as exc:
        return f"Error setting property method: {exc}"
