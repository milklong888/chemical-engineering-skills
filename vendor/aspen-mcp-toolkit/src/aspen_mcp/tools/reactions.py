"""Reaction set and kinetics tools.

All COM operations run inside aspen.call() lambdas on the dedicated
COM apartment thread.
"""

from __future__ import annotations

from ..com_bridge import aspen
from ._common import walk

_REACTIONS_BASE = r"\Data\Reactions\Reactions"


def _label_from_path(root, path):
    """Return the label of the last path segment's parent row."""
    parts = path.replace("/", "\\").strip("\\").split("\\")
    node = walk(root, *parts)
    return node.Name if node is not None else None


def _create_2d_table_labels(root, table_path, components, substream="MIXED"):
    """Create component labels in a 2D (component x substream) table.

    *root* and all *table_path* navigation use walk() — must be called
    from within aspen.call() on the COM thread.
    """
    parts = table_path.replace("/", "\\").strip("\\").split("\\")
    node = walk(root, *parts)
    if node is None:
        return f"Node not found: {table_path}"

    els = node.Elements
    _max_el_iter = 10000
    for _ in range(_max_el_iter):
        if els.Count == 0:
            break
        els.RemoveRow(0, 0)

    for idx, comp in enumerate(components):
        if idx == 0:
            els.InsertRow(0, 0)
        else:
            if els.Count <= idx:
                els.InsertRow(0, els.Count)

        if idx == 0:
            target_idx = 0
        else:
            target_idx = None
            for i in range(els.Count):
                try:
                    l0 = els.GetLabel(0, i)
                    if l0 == "":
                        target_idx = i
                        break
                except Exception:
                    continue
            if target_idx is None:
                continue

        els.SetLabel(0, target_idx, False, comp)
        try:
            els.SetLabel(1, target_idx, False, substream)
        except Exception:
            pass

    return None


def _set_2d_table_value(root, table_path, comp, value, substream="MIXED"):
    """Set a single value in a 2D table (on COM thread)."""
    value_path = f"{table_path}\\{comp}\\{substream}"
    parts = value_path.replace("/", "\\").strip("\\").split("\\")
    node = walk(root, *parts)
    if node is not None:
        node.SetValue(0, value)
        return True
    return False


def tool_add_reaction_set(name: str, reaction_type: str = "POWERLAW") -> str:
    """Create a new reaction set.

    Args:
        name: Reaction set name (e.g. R-1, RXN1).
        reaction_type: POWERLAW, LHHW, GENERAL, or EQUILIBRIUM.
    """
    try:
        def impl():
            root = aspen._app.RootModel("")
            rxns = walk(root, "Data", "Reactions", "Reactions")
            if rxns is None:
                return "Error: Reactions node not found"

            els = rxns.Elements
            for i in range(els.Count):
                try:
                    if els.Item(i).Name.upper() == name.upper():
                        return f"Reaction set '{name}' already exists."
                except Exception:
                    break

            rtype = reaction_type.upper()
            els.Add(f"{name}!{rtype}")

            # Verify creation
            new_node = walk(root, "Data", "Reactions", "Reactions", name)
            if new_node is None:
                return f"Failed to create reaction set '{name}'."

            return f"Reaction set '{name}' created (type={rtype}). Use add_reaction to add reactions."
        return aspen.call(impl)
    except Exception as exc:
        return f"Error: {exc}"


def tool_remove_reaction_set(name: str) -> str:
    """Remove a reaction set and all its reactions."""
    try:
        def impl():
            root = aspen._app.RootModel("")
            rxns = walk(root, "Data", "Reactions", "Reactions")
            if rxns is None:
                return "Error: Reactions node not found"

            els = rxns.Elements
            for i in range(els.Count):
                try:
                    if els.Item(i).Name.upper() == name.upper():
                        els.RemoveRow(0, i)
                        return f"Reaction set '{name}' removed."
                except Exception:
                    break
            return f"Reaction set '{name}' not found."
        return aspen.call(impl)
    except Exception as exc:
        return f"Error: {exc}"


def tool_add_reaction(
    reaction_set: str,
    reaction_no: int,
    reactants: dict[str, float],
    products: dict[str, float],
    phase: str = "L",
    exponents: dict[str, float] | None = None,
) -> str:
    """Add a reaction with stoichiometry to an existing reaction set.

    Creates reaction number *reaction_no* in the set and populates:
      - REACTYPE (KINETIC)
      - COEF / COEF1 (stoichiometry)
      - PHASE
      - EXPONENT (concentration exponents)

    Args:
        reaction_set: Name of the reaction set (e.g. R-1).
        reaction_no: Reaction number (usually 1).
        reactants: {component_id: coefficient}, e.g. {"ETHYLENE": 1, "WATER": 1}
        products: {component_id: coefficient}, e.g. {"ETHANOL": 1}
        phase: 'L' (liquid) or 'V' (vapor).
        exponents: {component_id: exponent}. If None, uses abs(reactant coeff).
    """
    base = f"{_REACTIONS_BASE}\\{reaction_set}\\Input"
    rxn = str(reaction_no)

    try:
        # Compute exp_entries outside impl() to avoid closure reassignment issue
        coef_entries = [(comp, abs(coef)) for comp, coef in reactants.items()]
        coef1_entries = [(comp, abs(coef)) for comp, coef in products.items()]
        exp_map = exponents if exponents is not None else {comp: abs(coef) for comp, coef in reactants.items()}
        exp_entries = list(exp_map.items())

        def impl():
            root = aspen._app.RootModel("")
            inp_node = walk(root, "Data", "Reactions", "Reactions",
                             reaction_set, "Input")
            if inp_node is None:
                return f"Reaction set '{reaction_set}' not found."

            # Step 1: Set REACTYPE
            rt_node = walk(root, "Data", "Reactions", "Reactions",
                            reaction_set, "Input", "REACTYPE")
            if rt_node is None:
                return "REACTYPE node not found."
            rt_els = rt_node.Elements

            existing = False
            for i in range(rt_els.Count):
                try:
                    if rt_els.Item(i).Name == rxn:
                        existing = True
                        break
                except Exception:
                    break

            if not existing:
                rt_els.InsertRow(0, rt_els.Count)
                rt_els.SetLabel(0, rt_els.Count - 1, False, rxn)
                rt_val = walk(root, "Data", "Reactions", "Reactions",
                               reaction_set, "Input", "REACTYPE", rxn)
                if rt_val:
                    rt_val.SetValue(0, "KINETIC")

            # Step 2: Set PHASE
            ph_node = walk(root, "Data", "Reactions", "Reactions",
                            reaction_set, "Input", "PHASE", rxn)
            if ph_node:
                ph_node.SetValue(0, phase)

            # Phase A: Create labels
            base_dr = f"Data\\Reactions\\Reactions\\{reaction_set}\\Input"
            for table_rel, comps in [
                (f"{base_dr}\\COEF\\{rxn}", [c for c, _ in coef_entries]),
                (f"{base_dr}\\COEF1\\{rxn}", [c for c, _ in coef1_entries]),
                (f"{base_dr}\\EXPONENT\\{rxn}", [c for c, _ in exp_entries]),
            ]:
                err = _create_2d_table_labels(root, table_rel, comps)
                if err:
                    return f"Failed creating labels: {err}"

            # Phase B: Set values
            for comp, val in coef_entries:
                _set_2d_table_value(root, f"{base_dr}\\COEF\\{rxn}", comp, val)
            for comp, val in coef1_entries:
                _set_2d_table_value(root, f"{base_dr}\\COEF1\\{rxn}", comp, val)
            for comp, val in exp_entries:
                _set_2d_table_value(root, f"{base_dr}\\EXPONENT\\{rxn}", comp, val)

            lines = [f"Reaction {rxn} added to '{reaction_set}':"]
            lines.append(f"  Phase: {phase}")
            lines.append(f"  Reactants: {dict(reactants)}")
            lines.append(f"  Products: {dict(products)}")
            lines.append(f"  Exponents: {dict(exp_map)}")
            return "\n".join(lines)

        return aspen.call(impl)
    except Exception as exc:
        return f"Error adding reaction: {exc}"


def tool_remove_reaction(reaction_set: str, reaction_no: int) -> str:
    """Remove a single reaction from a reaction set."""
    rxn = str(reaction_no)

    try:
        def impl():
            root = aspen._app.RootModel("")
            base_dr = f"Data\\Reactions\\Reactions\\{reaction_set}\\Input"

            rt_node = walk(root, *base_dr.split("\\"), "REACTYPE")
            if rt_node is None:
                return f"Reaction set '{reaction_set}' not found."
            rt_els = rt_node.Elements

            target_idx = None
            for i in range(rt_els.Count):
                try:
                    if rt_els.Item(i).Name == rxn:
                        target_idx = i
                        break
                except Exception:
                    break

            if target_idx is None:
                return f"Reaction {rxn} not found in '{reaction_set}'."

            rt_els.RemoveRow(0, target_idx)

            for table in ["COEF", "COEF1", "EXPONENT", "EXPONENT1",
                          "PRE_EXP", "ACT_ENERGY"]:
                tbl_node = walk(root, *base_dr.split("\\"), table)
                if tbl_node is None:
                    continue
                els = tbl_node.Elements
                for i in range(els.Count):
                    try:
                        if els.Item(i).Name == rxn:
                            els.RemoveRow(0, i)
                            break
                    except Exception:
                        break

            return f"Reaction {rxn} removed from '{reaction_set}'."
        return aspen.call(impl)
    except Exception as exc:
        return f"Error: {exc}"


def tool_list_reaction_sets() -> list[str]:
    """List all reaction sets."""
    try:
        def impl():
            root = aspen._app.RootModel("")
            rxns = walk(root, "Data", "Reactions", "Reactions")
            if rxns is None:
                return []
            sets = []
            for i in range(100):
                try:
                    c = rxns.Elements(i)
                    if c is None:
                        break
                    sets.append(c.Name)
                except Exception:
                    break
            return sets
        return aspen.call(impl)
    except Exception:
        return []
