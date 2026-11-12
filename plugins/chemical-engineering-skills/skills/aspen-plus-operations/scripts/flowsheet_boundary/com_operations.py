# SPDX-License-Identifier: MIT
"""Bounded callbacks for an already owned Aspen Plus COM session.

This module does not open, attach, run, save, close, or kill an application.
Call it only on a protected copy inside the installed Aspen operations queue.
Caller engineering authority must explicitly identify unnecessary terminal
heaters. A terminal connection alone is not sufficient engineering authority.
Native card mechanics were observed in Aspen Plus V14; other versions need
their own card and exported-input verification.
"""
from __future__ import annotations

import os
import re


def _id(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_$-]+", value):
        raise ValueError("An explicit simple Aspen object ID is required")
    return value


def _find(app, path):
    node = app.Tree.FindNode(path)
    if node is None:
        raise ValueError("Missing native node: " + path)
    return node


def _names(node):
    return [str(child.Name) for child in node.Elements]


def _snapshot(node, path=""):
    """Input-tree values only; no output containers interpreted as numbers."""
    result = {path: node.Value}
    try:
        children = list(node.Elements)
    except Exception:
        children = []
    for child in children:
        result.update(_snapshot(child, path + "\\" + str(child.Name)))
    return result


def remove_terminal_heaters(app, requests, *, input_guard_paths, expected_counts):
    """Remove an explicit, pre-reviewed list of final single-stream heaters.

    requests: nonempty list of {block, inlet, outlet,
      confirmed_no_outlet_conditioning_requirement: True}.
    expected_counts: {blocks_before, streams_before, blocks_after, streams_after}.
    input_guard_paths: existing input roots to compare before/after.

    Every request is checked before the first removal. Reject an outlet used
    by any downstream block, a mismatch of ports, duplicate IDs, absent explicit
    authority, or unexpected object counts. On a COM failure after mutation,
    discard the protected candidate; this is not an in-place rollback engine.
    Reinitialize/run/export/reopen and strict evidence checks remain the caller's
    responsibility. No tolerance or iteration value is written here.
    """
    if not os.environ.get("ASPEN_RUNTIME_OWNER_TOKEN"):
        raise RuntimeError("Use the installed owned-session queue/supervisor")
    if not requests or not input_guard_paths:
        raise ValueError("Requests and input guards must be explicit")
    keys = {"blocks_before", "streams_before", "blocks_after", "streams_after"}
    if set(expected_counts) != keys or any(type(v) is not int or v < 0 for v in expected_counts.values()):
        raise ValueError("Supply all four nonnegative integer object counts")
    blocks = _find(app, r"\Data\Blocks")
    streams = _find(app, r"\Data\Streams")
    if len(_names(blocks)) != expected_counts["blocks_before"] or len(_names(streams)) != expected_counts["streams_before"]:
        raise ValueError("Source object count differs from the frozen contract")
    block_ids, outlet_ids = set(), set()
    planned = []
    for request in requests:
        if request.get("confirmed_no_outlet_conditioning_requirement") is not True:
            raise ValueError("Engineering authority for terminal removal is absent")
        block, inlet, outlet = (_id(request[k]) for k in ("block", "inlet", "outlet"))
        if block in block_ids or outlet in outlet_ids or inlet == outlet:
            raise ValueError("Duplicate or invalid removal request")
        block_ids.add(block); outlet_ids.add(outlet)
        root = "\\Data\\Blocks\\" + block
        kind = _find(app, root).AttributeValue(6)
        if str(kind).upper() != "HEATER":
            raise ValueError("Only native HEATER blocks are covered")
        # Native V14 port IDs include direction in parentheses. A guessed
        # generic IN/OUT path is not the application's connection contract.
        if _names(_find(app, root + "\\Ports\\F(IN)")) != [inlet] or _names(_find(app, root + "\\Ports\\P(OUT)")) != [outlet]:
            raise ValueError("Heater ports differ from the approved stream path")
        for port in _find(app, root + "\\Ports").Elements:
            if str(port.Name) not in {"F(IN)", "P(OUT)"} and _names(port):
                raise ValueError("Additional connected heater port needs separate engineering review")
        _find(app, "\\Data\\Streams\\" + inlet)
        _find(app, "\\Data\\Streams\\" + outlet)
        for other in _names(blocks):
            ports = _find(app, "\\Data\\Blocks\\" + other + "\\Ports")
            for port in ports.Elements:
                if str(port.Name).upper().endswith("(IN)") and outlet in _names(port):
                    raise ValueError("Outlet has a downstream consumer: " + other)
        planned.append({"block": block, "inlet": inlet, "outlet": outlet})
    if len(planned) != expected_counts["blocks_before"] - expected_counts["blocks_after"] or len(planned) != expected_counts["streams_before"] - expected_counts["streams_after"]:
        raise ValueError("Removal count differs from the frozen contract")
    guarded = {path: _snapshot(_find(app, path), path) for path in input_guard_paths}
    if any(value in outlet_ids for tree in guarded.values() for value in tree.values() if isinstance(value, str)):
        raise ValueError("A guarded input still references a proposed dead outlet")
    for row in planned:
        blocks.Elements.Remove(row["block"])
        streams.Elements.Remove(row["outlet"])
    remaining_blocks, remaining_streams = _names(blocks), _names(streams)
    if len(remaining_blocks) != expected_counts["blocks_after"] or len(remaining_streams) != expected_counts["streams_after"]:
        raise RuntimeError("Unexpected post-removal object count; discard candidate")
    for row in planned:
        if row["block"] in remaining_blocks or row["outlet"] in remaining_streams:
            raise RuntimeError("Requested object remains; discard candidate")
    if guarded != {path: _snapshot(_find(app, path), path) for path in input_guard_paths}:
        raise RuntimeError("Guarded input changed; discard candidate")
    return {"removed": planned, "input_guards_equal": True,
            "remaining_blocks": remaining_blocks, "remaining_streams": remaining_streams,
            "precision_inputs_written": False,
            "scope": "native object mutation/readback only; run and exact-file evidence are separate"}


def enable_hcurves(app, specifications):
    """Enable native duty-dependent H-curves without changing physical inputs.

    Each caller-supplied item has block, kind, curve_id, points. kind is one of
    condenser, reboiler, heater_or_flash. The caller must verify the requested
    service exists (for example, an empty tower has no condenser service).
    Refuse an existing curve rather than silently overwrite analysis settings.
    All card paths are preflighted after creating the analysis object. On an
    error discard the protected candidate. Native calculation is still required.
    """
    if not os.environ.get("ASPEN_RUNTIME_OWNER_TOKEN"):
        raise RuntimeError("Use the installed owned-session queue/supervisor")
    if not specifications:
        raise ValueError("At least one explicitly selected service is required")
    layouts = {
        "condenser": ("Condenser Hcurves", "CH_", "OPT_RANGE", "CH_PRES_PROF"),
        "reboiler": ("Reboiler Hcurves", "RH_", "OPT_RANGE2", "RH_PRES_PROF"),
        "heater_or_flash": ("Hcurves", "", "OPT_RANGE", "PRES_PROFILE"),
    }
    planned, identities = [], set()
    for spec in specifications:
        block, curve = _id(spec["block"]), _id(str(spec["curve_id"]))
        kind = spec["kind"]
        if kind not in layouts or type(spec["points"]) is not int or spec["points"] < 2:
            raise ValueError("Unsupported curve kind or invalid point count")
        group, prefix, range_key, pressure_key = layouts[kind]
        root = "\\Data\\Blocks\\" + block
        parent = _find(app, root + "\\Subobjects\\" + group)
        identity = (block, group, curve)
        if identity in identities or curve in _names(parent):
            raise ValueError("Curve already exists or is duplicated")
        identities.add(identity)
        planned.append((parent, curve, root, [(prefix + "INDEP_VAR", "DUTY"),
            (range_key, "NPOINT"), (prefix + "NPOINTS", spec["points"]), (pressure_key, "CONSTANT")]))
    writes = []
    for parent, curve, root, fields in planned:
        parent.Elements.Add(curve)
        nodes = [(_find(app, root + "\\Input\\" + key + "\\" + curve), key, value) for key, value in fields]
        for node, key, value in nodes:
            node.Value = value
            if node.Value != value:
                raise RuntimeError("Native card readback mismatch")
            writes.append({"path": root + "\\Input\\" + key + "\\" + curve, "value": node.Value})
    return {"writes": writes, "physical_inputs_written": False,
            "scope": "analysis-card creation/readback; not proof of a computed curve"}
