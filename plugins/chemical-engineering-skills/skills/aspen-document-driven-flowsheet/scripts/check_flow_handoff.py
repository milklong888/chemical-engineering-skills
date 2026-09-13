"""Check a declared source/scaffold ledger; never run or accept engineering.

References inside JSON are inert text. Only explicit CLI input/output paths are
accessed. No imports from a caller path, network calls, commands or Aspen APIs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SCHEMA = "document-flow-handoff-v1"
RETURNS = {"method_basis", "boundary_states", "closure_targets", "execution_evidence"}


def obj(value, keys, where):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(f"{where}: expected object with fields {', '.join(sorted(keys))}")
    return value


def text(value, where, nullable=False):
    if nullable and value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{where}: nonempty text required")
    return value


def rows(value, where, nonempty=False):
    if not isinstance(value, list) or (nonempty and not value):
        raise ValueError(f"{where}: {'nonempty ' if nonempty else ''}array required")
    return value


def names(value, where, nonempty=False):
    result = [text(x, where) for x in rows(value, where, nonempty)]
    if len(set(result)) != len(result):
        raise ValueError(f"{where}: duplicate identifiers")
    return result


def indexed(values, keys, where):
    result = {}
    for i, value in enumerate(rows(values, where)):
        obj(value, keys, f"{where}[{i}]")
        identifier = text(value["id"], f"{where}[{i}].id")
        if identifier in result:
            raise ValueError(f"{where}: duplicate id {identifier}")
        result[identifier] = value
    return result


def check(data):
    result = {"schema": "document-flow-handoff-check-v1", "status": "STRUCTURE_INVALID",
              "errors": [], "unresolved": [], "boundary_rows": [], "volume_terms": [],
              "handoff_rows": [], "engineering_accepted": False, "execution_verified": False,
              "authority_verified": False, "source_inventory_verified": False,
              "scope": "Declared field/edge consistency only; no source truth, physical or numerical closure, or model execution proof."}
    try:
        _check(data, result)
    except (ValueError, TypeError, KeyError) as exc:
        result["errors"].append(str(exc))
    if not result["errors"]:
        result["status"] = ("STRUCTURE_VALID_WITH_UNRESOLVED" if result["unresolved"]
                            else "STRUCTURE_VALID")
    return result


def _check(data, result):
    obj(data, {"schema", "stage", "authority_reference", "nodes", "streams", "control_volumes",
               "placeholders", "no_placeholders_reason", "handoffs"}, "input")
    if data["schema"] != SCHEMA or data["stage"] not in ("source", "scaffold"):
        raise ValueError("input: expected document-flow-handoff-v1 and source/scaffold stage")
    result["stage"] = data["stage"]
    result["authority_reference"] = text(data["authority_reference"], "authority_reference")
    nodes = indexed(data["nodes"], {"id", "kind"}, "nodes")
    if not nodes:
        raise ValueError("nodes: explicit process/external inventory required")
    for identifier, node in nodes.items():
        if node["kind"] not in ("process", "external"):
            raise ValueError(f"node {identifier}: kind must be process or external")

    streams = indexed(data["streams"], {"id", "from", "to", "state", "evidence", "gap"}, "streams")
    if not streams:
        raise ValueError("streams: explicit inventory, including unresolved streams, required")
    for identifier, stream in streams.items():
        for endpoint in ("from", "to"):
            node = text(stream[endpoint], f"stream {identifier}.{endpoint}", nullable=True)
            if node is not None and node not in nodes:
                raise ValueError(f"stream {identifier}: unregistered {endpoint} endpoint {node}; not assumed external")
        state = stream["state"]
        if state not in ("documented", "proposed", "unresolved"):
            raise ValueError(f"stream {identifier}: unknown connection state")
        text(stream["evidence"], f"stream {identifier}.evidence", nullable=True)
        text(stream["gap"], f"stream {identifier}.gap", nullable=True)
        unknown = stream["from"] is None or stream["to"] is None
        if state == "unresolved":
            if not unknown or stream["gap"] is None:
                raise ValueError(f"stream {identifier}: unresolved needs null endpoint(s) and a precise gap")
        elif unknown or stream["evidence"] is None:
            raise ValueError(f"stream {identifier}: documented/proposed needs known endpoints and evidence/permission citation")
        if state != "documented":
            result["unresolved"].append(f"stream {identifier}: {state}; {stream['gap'] or 'proposal, not observed connectivity'}")

    volumes = indexed(data["control_volumes"],
                      {"id", "members", "inflows", "outflows", "balance_basis", "reaction_terms"}, "control_volumes")
    if not volumes:
        raise ValueError("control_volumes: at least the requested boundary required")
    for identifier, volume in volumes.items():
        members = set(names(volume["members"], f"volume {identifier}.members", True))
        if any(x not in nodes or nodes[x]["kind"] != "process" for x in members):
            raise ValueError(f"volume {identifier}: members must be registered process nodes")
        incoming = names(volume["inflows"], f"volume {identifier}.inflows")
        outgoing = names(volume["outflows"], f"volume {identifier}.outflows")
        text(volume["balance_basis"], f"volume {identifier}.balance_basis")
        text(volume["reaction_terms"], f"volume {identifier}.reaction_terms")
        expected = {"in": [], "out": [], "internal": [], "outside": [], "unresolved": []}
        for stream_id, stream in streams.items():
            a, b = stream["from"], stream["to"]
            if a is None or b is None:
                direction = "unresolved"
            elif a in members and b in members:
                direction = "internal"
            elif a in members:
                direction = "out"
            elif b in members:
                direction = "in"
            else:
                direction = "outside"
            expected[direction].append(stream_id)
            result["boundary_rows"].append({"volume": identifier, "stream": stream_id,
                "from": a, "from_kind": nodes[a]["kind"] if a else "unknown",
                "to": b, "to_kind": nodes[b]["kind"] if b else "unknown",
                "direction": direction, "state": stream["state"],
                "evidence": stream["evidence"], "gap": stream["gap"]})
        for side, declared in (("in", incoming), ("out", outgoing)):
            if set(declared) != set(expected[side]):
                result["errors"].append(f"volume {identifier} {side}: declared {declared}; endpoint-derived {expected[side]}")
        result["volume_terms"].append({"id": identifier, "members": sorted(members),
            **expected, "balance_basis": volume["balance_basis"], "reaction_terms": volume["reaction_terms"]})

    placeholders = indexed(data["placeholders"],
        {"id", "node_ids", "purpose", "valid_scope", "permission_reference"}, "placeholders")
    reason = text(data["no_placeholders_reason"], "no_placeholders_reason", nullable=True)
    if not placeholders and reason is None:
        raise ValueError("placeholders: provide inventory or a source-bound no_placeholders_reason")
    if placeholders and reason is not None:
        raise ValueError("placeholders: inventory contradicts no_placeholders_reason")
    for identifier, row in placeholders.items():
        duty_nodes = names(row["node_ids"], f"placeholder {identifier}.node_ids", True)
        if any(x not in nodes or nodes[x]["kind"] != "process" for x in duty_nodes):
            raise ValueError(f"placeholder {identifier}: must bind to registered process nodes")
        for field in ("purpose", "valid_scope", "permission_reference"):
            text(row[field], f"placeholder {identifier}.{field}")
    handoffs = indexed(data["handoffs"], {"id", "owner", "selection_condition", "inputs",
        "required_returns", "execution_status", "execution_reference"}, "handoffs")
    if set(handoffs) != set(placeholders):
        result["errors"].append(f"handoffs: missing {sorted(set(placeholders)-set(handoffs))}; unexpected {sorted(set(handoffs)-set(placeholders))}")
    for identifier, handoff in handoffs.items():
        owner = text(handoff["owner"], f"handoff {identifier}.owner", nullable=True)
        condition = text(handoff["selection_condition"], f"handoff {identifier}.selection_condition", nullable=True)
        if owner is None:
            if condition is None:
                raise ValueError(f"handoff {identifier}: owner or specific selection condition required now")
            result["unresolved"].append(f"handoff {identifier}: owner pending; {condition}")
        input_names = []
        for i, entry in enumerate(rows(handoff["inputs"], f"handoff {identifier}.inputs", True)):
            obj(entry, {"name", "reference", "gap"}, f"handoff {identifier}.inputs[{i}]")
            input_names.append(text(entry["name"], f"handoff {identifier}.input.name"))
            reference = text(entry["reference"], f"handoff {identifier}.input.reference", nullable=True)
            gap = text(entry["gap"], f"handoff {identifier}.input.gap", nullable=True)
            if (reference is None) == (gap is None):
                raise ValueError(f"handoff {identifier}: each input needs either actual reference/value or missing evidence")
            if gap is not None:
                result["unresolved"].append(f"handoff {identifier} input {entry['name']}: {gap}")
        if len(set(input_names)) != len(input_names):
            raise ValueError(f"handoff {identifier}: duplicate input names")
        obj(handoff["required_returns"], RETURNS, f"handoff {identifier}.required_returns")
        for field in RETURNS:
            text(handoff["required_returns"][field], f"handoff {identifier}.{field}")
        if handoff["execution_status"] not in ("not_executed", "reported_unverified"):
            raise ValueError(f"handoff {identifier}: checker cannot confer accepted/executed status")
        reference = text(handoff["execution_reference"], f"handoff {identifier}.execution_reference", nullable=True)
        if handoff["execution_status"] == "reported_unverified" and reference is None:
            raise ValueError(f"handoff {identifier}: reported execution needs its actual reference")
        if handoff["execution_status"] == "not_executed" and reference is not None:
            raise ValueError(f"handoff {identifier}: not_executed contradicts an execution reference")
        result["handoff_rows"].append({**placeholders.get(identifier, {}), **handoff})
    result["no_placeholders_reason"] = reason
    result["declared_topology"] = {"nodes": list(nodes),
        "edges": [[row["from"], row["to"]] for row in streams.values()
                  if row["from"] is not None and row["to"] is not None],
        "coverage": "DECLARED_PARTIAL" if any(row["state"] == "unresolved" for row in streams.values()) else "DECLARED_ONLY",
        "source_verified": False}


def cell(value):
    return str(value if value is not None else "unknown").replace("|", "\\|").replace("\r", " ").replace("\n", " / ")


def markdown(result):
    lines = ["# Source/scaffold handoff", "", result["status"], "", result["scope"], "",
             f"Declared authority (not verified): {cell(result.get('authority_reference'))}", "",
             f"Input SHA-256: `{result.get('input_sha256', 'unavailable')}`", "",
             "## Boundary edge table", "", "| Control volume | Stream | From (kind) | To (kind) | Direction | State / evidence / gap |",
             "|---|---|---|---|---|---|"]
    for row in result["boundary_rows"]:
        lines.append("| " + " | ".join(cell(x) for x in [row["volume"], row["stream"],
            f"{row['from']} ({row['from_kind']})", f"{row['to']} ({row['to_kind']})",
            row["direction"], f"{row['state']} / {row['evidence']} / {row['gap']}"]) + " |")
    lines += ["", "## Control-volume terms", ""]
    for row in result["volume_terms"]:
        lines += [f"- {cell(row['id'])}; members: {cell(row['members'])}; inflows: {cell(row['in'])}; outflows: {cell(row['out'])}; internal: {cell(row['internal'])}; unresolved: {cell(row['unresolved'])}",
                  f"  Basis: {cell(row['balance_basis'])}; declared reaction terms: {cell(row['reaction_terms'])}"]
    lines += ["", "## Placeholder-to-rigorous handoffs", ""]
    if result.get("no_placeholders_reason"):
        lines += [cell(result["no_placeholders_reason"]), ""]
    for row in result["handoff_rows"]:
        lines += [f"### {cell(row['id'])}", "", f"- Duty nodes: {cell(row.get('node_ids'))}; purpose: {cell(row.get('purpose'))}",
                  f"- Valid scope: {cell(row.get('valid_scope'))}; permission: {cell(row.get('permission_reference'))}",
                  f"- Receiver: {cell(row['owner'])}; selection condition: {cell(row['selection_condition'])}"]
        lines += [f"- Input {cell(x['name'])}: {cell(x['reference'])}; missing evidence: {cell(x['gap'])}" for x in row["inputs"]]
        lines += [f"- Return {key}: {cell(row['required_returns'][key])}" for key in sorted(RETURNS)]
        lines += [f"- Execution: {cell(row['execution_status'])}; reference: {cell(row['execution_reference'])}", ""]
    for key in ("errors", "unresolved"):
        lines += [f"## {key}", ""] + ([f"- {cell(x)}" for x in result[key]] or ["None reported by this structural check."]) + [""]
    lines += ["Engineering accepted: false. Execution verified: false. Source/inventory truth remains unverified.", ""]
    return "\n".join(lines)


def unique_object(pairs):
    obj_value = {}
    for key, value in pairs:
        if key in obj_value:
            raise ValueError(f"Duplicate JSON key: {key}")
        obj_value[key] = value
    return obj_value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True, help="New project output directory; existing directories are not overwritten")
    args = parser.parse_args()
    try:
        if args.input.stat().st_size > 2_000_000:
            raise ValueError("Input exceeds 2 MB")
        raw = args.input.read_bytes()
        data = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique_object)
        result = check(data)
        result["input_sha256"] = hashlib.sha256(raw).hexdigest()
        result["checker_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        args.output_dir.mkdir(parents=True, exist_ok=False)
        (args.output_dir / "review.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (args.output_dir / "handoff.md").write_text(markdown(result), encoding="utf-8")
        print(json.dumps({"status": result["status"], "errors": result["errors"],
                          "unresolved": result["unresolved"], "engineering_accepted": False}, ensure_ascii=False))
        return 2 if result["errors"] else 0
    except (OSError, ValueError, RecursionError) as exc:
        print(json.dumps({"status": "INPUT_OR_OUTPUT_ERROR", "error": str(exc), "engineering_accepted": False}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
