"""Check a declared source/scaffold ledger; never run or accept engineering.

Ordinary citations inside JSON remain inert text. Only explicit input/output
paths, explicitly listed root-contained source-review text files and, when
needed, the fixed adjacent name catalog and sibling reaction helper are read.
No imports from a caller path, network calls, commands or Aspen APIs. Source
paragraph coverage and reaction arithmetic are not source truth or engineering
verification.
"""
from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
import math
import ntpath
import re
from pathlib import Path, PureWindowsPath
from types import ModuleType

SCHEMA = "document-flow-handoff-v1"
RETURNS = {"method_basis", "boundary_states", "closure_targets", "execution_evidence"}
EXPERT_SCOPE = (
    "Expert-plan checking covers fields, registered identifiers, and cycle coverage only "
    "on the declared process graph. It does not verify named-method applicability, phases, "
    "units/dimensions, general equations/calculation results, absence reasons, source "
    "inventory, or execution. Only the separately reported reaction-math check can verify "
    "limited declared arithmetic. Other calculated fields remain caller-reported and "
    "unverified, never an actual run."
)
NAMED_METHOD_SCOPE = (
    "Named-method declaration checking verifies field shape and catalog-name membership "
    "only, or the presence of a source-defined name and definition reference. It does "
    "not verify applicability, parameters, source truth, definitions, or execution. "
    "Source references are inert text and are not opened or executed."
)
PLAN_ACTION_SCOPE = (
    "Plan-action declaration checking covers fields, registered stream IDs, pressure-group "
    "coverage and caller-declared recycle dependencies only. Stream endpoints are projected "
    "from the declared graph, not source-verified; unknown endpoints remain unresolved. "
    "It does not verify formulas, units/dimensions, equipment applicability, source truth, "
    "computed seeds, initialization success, engineering acceptance, or execution."
)
METHOD_CATALOG_SCHEMA = "aspen-property-method-name-reference-v1"
REACTION_MATH_SCOPE = (
    "Reaction-math checking executes the fixed sibling helper on explicit formulas, "
    "signed coefficients and charges, and optional same-reaction mass projections. "
    "Its result separately records applicability, arithmetic checked and arithmetic valid. "
    "It does not verify source truth, molecular identity/source-basis alignment, supplied "
    "molar masses, reaction feasibility, whole-process yield bounds, thermodynamics, "
    "kinetics, other equations/units, absence reasons, engineering acceptance or execution. "
    "An explicit not-applicable result is not a mathematical pass. References stay inert."
)


SOURCE_REVIEW_SCOPE = (
    "Checks only explicitly listed local UTF-8 source files, their hashes, nonempty-paragraph "
    "or opt-in layout-block disposition coverage and references to the existing declared streams. "
    "Layout boundaries are reading aids, not interpreted functions. It does not verify "
    "source-set completeness, extraction completeness, sentence meaning, context reasons, "
    "whether every connection in a paragraph is mapped, source truth or engineering acceptance. "
    "Other citations remain inert. Paragraph text uses normalized LF line endings."
)
SOURCE_MAX_DOCUMENTS = 32
SOURCE_MAX_FILE_BYTES = 1_000_000
SOURCE_MAX_TOTAL_BYTES = 4_000_000
SOURCE_MAX_UNITS = 10_000
SOURCE_UNIT_MODES = {"paragraphs_v1", "layout_blocks_v2"}


def _source_unit_mode(value="paragraphs_v1"):
    if not isinstance(value, str) or value not in SOURCE_UNIT_MODES:
        raise ValueError("source_review.unit_mode: paragraphs_v1 or layout_blocks_v2 required")
    return value


def _source_layout_starts(lines):
    """Return lexical list/ATX-heading starts, never source facts or functions.

    Wrapped lines remain intact. Explicit fenced code/math is opaque. A marked
    equation such as '- x = y' is still lexically a list item, not proof of a
    process function. Setext headings and unmarked prose are not inferred.
    """
    starts, fence, math_end = {}, None, None
    for line_number, line in enumerate(lines, 1):
        stripped = line.strip()
        if fence is not None:
            if re.fullmatch(re.escape(fence[0]) + "{" + str(fence[1]) + r",}\s*", stripped):
                fence = None
            continue
        if math_end is not None:
            if stripped == math_end:
                math_end = None
            continue
        match = re.match(r"^[ \t]*(`{3,}|~{3,})(.*)$", line)
        if match:
            fence = (match[1][0], len(match[1]))
            continue
        if stripped in {"$$", r"\["}:
            math_end = "$$" if stripped == "$$" else r"\]"
            continue
        # Markdown thematic breaks are not bullet items, even when spaced.
        if re.fullmatch(r"[ \t]*(?:(?:\*[ \t]*){3,}|(?:-[ \t]*){3,}|(?:_[ \t]*){3,})", line):
            continue
        if re.match(r"^[ ]{0,3}#{1,6}(?:[ \t]+|$)", line):
            starts[line_number] = "heading"
        elif re.match(r"^[ \t]*(?:[-+*\u2022\u2023\u25e6\u25aa\u25ab]|[0-9]{1,9}[.)])[ \t]+\S", line):
            starts[line_number] = "list_item"
    return starts


def _legacy_aggregated_list_units(inventory):
    """Find old paragraphs hiding multiple explicit list starts, without rereading files."""
    documents = {}
    for row in inventory:
        documents.setdefault(row["document_id"], []).append(row)
    aggregated = []
    for document_rows in documents.values():
        # Reconstruct normalized line positions, including blank gaps, so a
        # code/math fence remains opaque even across old paragraph boundaries.
        lines = []
        for row in document_rows:
            lines.extend([""] * (row["line_start"] - 1 - len(lines)))
            lines.extend(row["text"].split("\n"))
        starts = _source_layout_starts(lines)
        for row in document_rows:
            item_lines = [number for number in range(row["line_start"], row["line_end"] + 1)
                          if starts.get(number) == "list_item"]
            if len(item_lines) > 1:
                aggregated.append({"unit_id": row["unit_id"], "path": row["path"],
                                   "line_start": row["line_start"], "line_end": row["line_end"],
                                   "list_item_start_lines": item_lines})
    return aggregated


def _source_local_path(value, where):
    """Reject network/URI/device/ADS paths before filesystem access."""
    if not isinstance(value, (str, Path)) or not str(value).strip():
        raise ValueError(f"{where}: an explicit nonempty local path is required")
    raw = str(value)
    # Windows accepts mixed separators as UNC/device prefixes too. Reject
    # them lexically before Path.resolve can attempt filesystem access.
    if raw.replace("\\", "/").startswith("//") or "://" in raw:
        raise ValueError(f"{where}: network, device or URI paths are not allowed")
    path = Path(raw)
    for part in path.parts:
        reserved = (ntpath.isreserved(part) if hasattr(ntpath, "isreserved")
                    else PureWindowsPath(part).is_reserved())
        if part != path.anchor and reserved:
            raise ValueError(f"{where}: reserved Windows device names are not allowed")
        if part != path.anchor and ":" in part:
            raise ValueError(f"{where}: alternate streams or URI paths are not allowed")
    return path


def source_inventory(documents, source_root=None, unit_mode="paragraphs_v1"):
    """Read only the listed, root-contained, hash-bound .txt/.md files.

    Returns default paragraphs or opt-in layout blocks, not interpreted facts. No citation resolution, glob,
    recursive discovery, subprocess, network request or external extraction.
    """
    unit_mode = _source_unit_mode(unit_mode)
    root = _source_local_path(source_root, "source_root").resolve(strict=True)
    _source_local_path(root, "resolved source_root")
    if not root.is_dir():
        raise ValueError("source_root: an existing directory is required")
    document_rows = rows(documents, "source_review.documents", True)
    if len(document_rows) > SOURCE_MAX_DOCUMENTS:
        raise ValueError(f"source_review.documents: exceeds {SOURCE_MAX_DOCUMENTS} documents")
    identifiers, paths, inventory = set(), set(), []
    total_bytes = 0
    for index, document in enumerate(document_rows):
        where = f"source_review.documents[{index}]"
        obj(document, {"id", "path", "sha256"}, where)
        identifier = text(document["id"], where + ".id")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", identifier):
            raise ValueError(f"{where}.id: use 1-80 ASCII identifier characters")
        if identifier in identifiers:
            raise ValueError(f"{where}.id: duplicate document id {identifier}")
        identifiers.add(identifier)
        digest = document["sha256"]
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
            raise ValueError(f"{where}.sha256: exact SHA-256 is required")
        path = _source_local_path(document["path"], where + ".path")
        path = (path if path.is_absolute() else root / path).resolve(strict=True)
        _source_local_path(path, where + ".resolved_path")
        if not path.is_relative_to(root):
            raise ValueError(f"{where}.path: source leaves explicit source_root")
        if path.suffix.lower() not in {".txt", ".md"} or not path.is_file():
            raise ValueError(f"{where}.path: existing local .txt/.md file required")
        if path in paths:
            raise ValueError(f"{where}.path: duplicate source file")
        paths.add(path)
        if path.stat().st_size > SOURCE_MAX_FILE_BYTES:
            raise ValueError(f"{where}: source exceeds {SOURCE_MAX_FILE_BYTES} bytes")
        with path.open("rb") as source:
            raw = source.read(SOURCE_MAX_FILE_BYTES + 1)
        if len(raw) > SOURCE_MAX_FILE_BYTES:
            raise ValueError(f"{where}: source exceeds {SOURCE_MAX_FILE_BYTES} bytes")
        total_bytes += len(raw)
        if total_bytes > SOURCE_MAX_TOTAL_BYTES:
            raise ValueError(f"source_review.documents: exceeds {SOURCE_MAX_TOTAL_BYTES} total bytes")
        actual_digest = hashlib.sha256(raw).hexdigest()
        if actual_digest != digest.lower():
            raise ValueError(f"{where}.sha256: source hash differs from current bytes")
        try:
            content = raw.decode("utf-8-sig")
        except UnicodeError as exc:
            raise ValueError(f"{where}: source is not valid UTF-8") from exc
        if "\x00" in content:
            raise ValueError(f"{where}: NUL is not permitted in source text")
        lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        layout_starts = _source_layout_starts(lines) if unit_mode == "layout_blocks_v2" else {}
        start, paragraph, count = None, [], 0
        for line_number, line in enumerate(lines + [""], 1):
            if line.strip() and not (paragraph and line_number in layout_starts):
                if start is None:
                    start = line_number
                paragraph.append(line)
                continue
            if not paragraph:
                continue
            count += 1
            paragraph_text = "\n".join(paragraph)
            paragraph_digest = hashlib.sha256(paragraph_text.encode("utf-8")).hexdigest()
            inventory.append({
                "unit_id": f"{identifier}:{'p' if unit_mode == 'paragraphs_v1' else 'b'}{count:04d}:{paragraph_digest[:12]}",
                "document_id": identifier, "path": str(path),
                "document_sha256": actual_digest,
                "line_start": start, "line_end": line_number - 1,
                "text": paragraph_text, "text_sha256": paragraph_digest,
            })
            if len(inventory) > SOURCE_MAX_UNITS:
                raise ValueError(f"source_review: exceeds {SOURCE_MAX_UNITS} nonempty paragraphs")
            start, paragraph = None, []
            if line.strip():
                start, paragraph = line_number, [line]
        if not count:
            raise ValueError(f"{where}: source contains no nonempty paragraphs")
    return inventory


def obj(value, keys, where, optional=()):
    if (not isinstance(value, dict) or not set(keys).issubset(value)
            or not set(value).issubset(set(keys) | set(optional))):
        suffix = f"; optional {', '.join(sorted(optional))}" if optional else ""
        raise ValueError(f"{where}: expected object with fields {', '.join(sorted(keys))}{suffix}")
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


def indexed(values, keys, where, optional=()):
    result = {}
    for i, value in enumerate(rows(values, where)):
        obj(value, keys, f"{where}[{i}]", optional)
        identifier = text(value["id"], f"{where}[{i}].id")
        if identifier in result:
            raise ValueError(f"{where}: duplicate id {identifier}")
        result[identifier] = value
    return result


def _has_named_methods(data):
    plan = data.get("expert_plan") if isinstance(data, dict) else None
    method_rows = plan.get("methods") if isinstance(plan, dict) else None
    return isinstance(method_rows, list) and any(
        isinstance(row, dict) and "named_methods" in row for row in method_rows)


def _has_plan_actions(data):
    plan = data.get("expert_plan") if isinstance(data, dict) else None
    if not isinstance(plan, dict):
        return False
    for field, declaration in (("pressure_paths", "interface_actions"),
                               ("recycle_plan", "startup_plan")):
        entries = plan.get(field)
        if isinstance(entries, list) and any(
                isinstance(row, dict) and declaration in row for row in entries):
            return True
    return False


def method_name(value, where):
    value = text(value, where)
    if len(value) > 80 or any(char in value for char in "\r\n\v\f\x1c\x1d\x1e\x85\u2028\u2029"):
        raise ValueError(f"{where}: a single-line name of at most 80 characters is required")
    return value


def _load_method_catalog():
    """Read only our fixed local asset, on demand; never a caller-supplied path."""
    path = Path(__file__).resolve().parent.parent / "assets" / "property_method_names_v14.json"
    try:
        raw = path.read_bytes()
        if len(raw) > 2_000_000:
            raise ValueError("catalog exceeds 2 MB")
        catalog = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique_object)
        if not isinstance(catalog, dict) or catalog.get("schema") != METHOD_CATALOG_SCHEMA:
            raise ValueError(f"expected catalog schema {METHOD_CATALOG_SCHEMA}")
        version = text(catalog.get("version"), "catalog.version")
        registered = set()
        for index, group in enumerate(rows(catalog.get("groups"), "catalog.groups", True)):
            if not isinstance(group, dict):
                raise ValueError(f"catalog.groups[{index}]: object required")
            for name in names(group.get("names"), f"catalog.groups[{index}].names", True):
                registered.add(method_name(name, f"catalog.groups[{index}].name"))
    except (OSError, UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise ValueError(f"named-method catalog unavailable or invalid at {path}: {exc}") from exc
    return registered, {"version": version, "sha256": hashlib.sha256(raw).hexdigest(),
                        "path": str(path), "scope": "Non-exhaustive name reference only; no engineering verification."}


def _check_named_methods(row, where, result, required, catalog_state):
    """Validate declarations, without interpreting or dereferencing their sources."""
    if "named_methods" not in row:
        if required:
            raise ValueError(f"{where}.named_methods: required by --require-named-methods; use [] for not_applicable")
        return
    declarations = rows(row["named_methods"], where + ".named_methods",
                        required and row["status"] != "not_applicable")
    if row["status"] == "not_applicable" and declarations:
        raise ValueError(f"{where}.named_methods: not_applicable permits only []")
    for index, declaration in enumerate(declarations):
        location = f"{where}.named_methods[{index}]"
        obj(declaration, {"name", "name_origin", "source_ref", "applies_when"},
            location, optional={"definition_ref"})
        name = method_name(declaration["name"], location + ".name")
        for field in ("source_ref", "applies_when"):
            text(declaration[field], location + "." + field)
        origin = declaration["name_origin"]
        if origin == "source_defined":
            text(declaration.get("definition_ref"), location + ".definition_ref")
        elif origin == "aspen_v14_catalog":
            if "definition_ref" in declaration:
                raise ValueError(f"{location}: aspen_v14_catalog must not carry definition_ref")
            if not catalog_state:
                try:
                    registered, metadata = _load_method_catalog()
                    catalog_state.update(names=registered)
                    result["named_method_catalog"] = metadata
                except ValueError as exc:
                    catalog_state["error"] = str(exc)
            if "error" in catalog_state:
                raise ValueError(f"{location}: {catalog_state['error']}")
            if name not in catalog_state["names"]:
                raise ValueError(f"{location}.name: {name!r} is not in the fixed V14 name catalog; "
                                 "a separately defined method requires source_defined and definition_ref")
        else:
            raise ValueError(f"{location}.name_origin: aspen_v14_catalog or source_defined required")


def _has_reaction_derivations(data):
    plan = data.get("expert_plan") if isinstance(data, dict) else None
    return isinstance(plan, dict) and "reaction_derivations" in plan


def _check_reaction_math(data, result, required=False):
    """Execute only the fixed sibling owner; JSON cannot select code or imports."""
    path = (Path(__file__).resolve().parents[2] / "chemical-engineering-expert"
            / "scripts" / "check_reaction_derivations.py")
    receipt = {"helper": {"path": str(path), "sha256": None}, "result": None}
    result["reaction_math"] = receipt
    if not _has_reaction_derivations(data):
        if required:
            result["errors"].append("expert_plan.reaction_derivations: required by "
                                    "--require-reaction-math; no reaction derivation may "
                                    "use reactions=[] with a source-bound none_reason")
        return
    payload = data["expert_plan"]["reaction_derivations"]
    try:
        raw = path.read_bytes()
        receipt["helper"]["sha256"] = hashlib.sha256(raw).hexdigest()
        if len(raw) > 2_000_000:
            raise ValueError("fixed helper exceeds 2 MB")
        # Compile the exact hashed trusted file, not a bytecode cache or JSON text.
        helper = ModuleType("_flow_handoff_fixed_reaction_math")
        helper.__file__ = str(path)
        exec(compile(raw, str(path), "exec"), helper.__dict__)
        evaluate = getattr(helper, "evaluate", None)
        if not callable(evaluate):
            raise ValueError("fixed helper has no callable evaluate")
        outcome = evaluate(payload)
        if not isinstance(outcome, dict) or outcome.get("schema") != "reaction-derivations-check-v1":
            raise ValueError("invalid helper return: expected reaction-derivations-check-v1 object")
        errors = outcome.get("errors")
        if not isinstance(errors, list) or any(not isinstance(item, str) or not item.strip() for item in errors):
            raise ValueError("invalid helper return: errors must be an array of nonempty strings")
        for flag in ("math_checked", "math_valid"):
            if type(outcome.get(flag)) is not bool:
                raise ValueError(f"invalid helper return: {flag} must be a boolean")
        for flag in ("source_verified", "engineering_accepted", "reaction_feasible"):
            if outcome.get(flag) is not False:
                raise ValueError(f"invalid helper return: {flag} must remain false")
        applicable = outcome.get("applicable")
        if applicable is not None and type(applicable) is not bool:
            raise ValueError("invalid helper return: applicable must be a boolean or null")
        status = outcome.get("status")
        if status == "not_applicable":
            if (applicable is not False or outcome["math_checked"] or outcome["math_valid"]
                    or errors or not isinstance(payload, dict) or payload.get("reactions") != []
                    or not isinstance(payload.get("none_reason"), str) or not payload["none_reason"].strip()):
                raise ValueError("invalid helper return: inconsistent not_applicable result")
        elif status == "checked":
            if (applicable is not True or not outcome["math_checked"] or not outcome["math_valid"]
                    or errors or not isinstance(payload, dict)
                    or not isinstance(payload.get("reactions"), list) or not payload["reactions"]):
                raise ValueError("invalid helper return: inconsistent checked result")
        elif status == "invalid":
            if not errors or outcome["math_valid"]:
                raise ValueError("invalid helper return: invalid status needs errors and math_valid=false")
        else:
            raise ValueError("invalid helper return: unknown status")
        # Preserve the owner's complete calculation output, but require JSON-safe data.
        json.dumps(outcome, allow_nan=False)
        receipt["result"] = outcome
        result["reaction_derivations_checked"] = True
        result["errors"].extend(f"expert_plan.reaction_derivations: {error}" for error in errors)
    except (Exception, SystemExit) as exc:
        result["errors"].append(f"expert_plan.reaction_derivations: fixed helper unavailable "
                                f"or invalid at {path}: {type(exc).__name__}: {exc}")


def _check_source_review(data, result, source_root=None, required=False):
    """Validate dispositions of source units, never their interpretation."""
    receipt = {"inventory": [], "rows": [], "errors": [], "boundary": SOURCE_REVIEW_SCOPE,
               "unit_mode": "paragraphs_v1",
               "source_inventory_verified": False, "source_truth_verified": False,
               "engineering_accepted": False, "execution_verified": False}
    result["source_review"] = receipt
    try:
        if not isinstance(data, dict) or "source_review" not in data:
            if required:
                raise ValueError("source_review: required by --require-source-review")
            return
        review = obj(data["source_review"], {"documents", "units"}, "source_review", optional={"unit_mode"})
        unit_mode = _source_unit_mode(review.get("unit_mode", "paragraphs_v1"))
        receipt["unit_mode"] = unit_mode
        inventory = source_inventory(review["documents"], source_root=source_root, unit_mode=unit_mode)
        receipt["inventory"] = inventory
        if required and unit_mode == "paragraphs_v1":
            aggregated = _legacy_aggregated_list_units(inventory)
            if aggregated:
                receipt["layout_migration_required"] = aggregated
                locations = "; ".join(f"{row['unit_id']} at {row['path']} lines "
                                      f"{row['list_item_start_lines']}" for row in aggregated)
                raise ValueError("strict source review found multiple explicit list items in a legacy "
                                 f"paragraph: {locations}. Set source_review.unit_mode='layout_blocks_v2' "
                                 "and regenerate inventory and dispositions; old unit IDs are not remapped.")
        expected = {row["unit_id"]: row for row in inventory}
        dispositions = rows(review["units"], "source_review.units", True)
        if len(dispositions) > SOURCE_MAX_UNITS:
            raise ValueError(f"source_review.units: exceeds {SOURCE_MAX_UNITS} rows")
        streams = indexed(data.get("streams"), {"id", "from", "to", "state", "evidence", "gap"}, "streams")
        seen, dispositions_by_id = set(), {}
        for index, row in enumerate(dispositions):
            where = f"source_review.units[{index}]"
            obj(row, {"unit_id", "disposition", "stream_ids", "reason"}, where)
            unit_id = text(row["unit_id"], where + ".unit_id")
            if unit_id not in expected:
                raise ValueError(f"{where}.unit_id: unknown source paragraph {unit_id}")
            if unit_id in seen:
                raise ValueError(f"{where}.unit_id: duplicate source paragraph {unit_id}")
            seen.add(unit_id)
            disposition = row["disposition"]
            if disposition not in {"mapped", "context", "unresolved"}:
                raise ValueError(f"{where}.disposition: mapped, context or unresolved required")
            text(row["reason"], where + ".reason")
            stream_ids = names(row["stream_ids"], where + ".stream_ids", disposition == "mapped")
            if disposition == "context" and stream_ids:
                raise ValueError(f"{where}: context requires empty stream_ids")
            unknown = set(stream_ids) - set(streams)
            if unknown:
                raise ValueError(f"{where}.stream_ids: unregistered streams {sorted(unknown)}")
            projected = {**expected[unit_id], "disposition": disposition,
                         "stream_ids": stream_ids, "reason": row["reason"],
                         "streams": [{"stream_id": sid, "from": streams[sid]["from"],
                                      "to": streams[sid]["to"], "state": streams[sid]["state"]}
                                     for sid in stream_ids]}
            dispositions_by_id[unit_id] = projected
        missing = set(expected) - seen
        if missing:
            raise ValueError(f"source_review.units: missing source paragraphs {sorted(missing)}")
        receipt["rows"] = [dispositions_by_id[row["unit_id"]] for row in inventory]
        for row in receipt["rows"]:
            if row["disposition"] == "unresolved":
                result["unresolved"].append(f"source paragraph {row['unit_id']}: {row['reason']}")
        result["source_review_checked"] = True
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        message = f"source_review: {exc}"
        receipt["errors"].append(message)
        result["errors"].append(message)


def check(data, require_expert_plan=False, require_named_methods=False, require_plan_actions=False,
           require_reaction_math=False, require_source_review=False, source_root=None):
    require_reaction_math = require_reaction_math or require_source_review
    require_plan_actions = require_plan_actions or require_reaction_math
    require_named_methods = require_named_methods or require_plan_actions
    require_expert_plan = require_expert_plan or require_named_methods
    result = {"schema": "document-flow-handoff-check-v1", "status": "STRUCTURE_INVALID",
              "errors": [], "unresolved": [], "boundary_rows": [], "volume_terms": [],
              "node_interface_rows": [],
              "handoff_rows": [], "engineering_accepted": False, "execution_verified": False,
              "authority_verified": False, "source_inventory_verified": False,
              "expert_plan_checked": False,
              "source_review_checked": False,
              "named_method_declarations_checked": False,
              "plan_action_declarations_checked": False,
              "reaction_derivations_checked": False,
              "scope": "Declared field/edge consistency; limited reaction arithmetic only when separately reported. No source truth, whole-process physical/numerical closure, or model execution proof."}
    if require_expert_plan or isinstance(data, dict) and "expert_plan" in data:
        result["scope"] += " " + EXPERT_SCOPE
    if require_named_methods or _has_named_methods(data):
        result["scope"] += " " + NAMED_METHOD_SCOPE
    if require_plan_actions or _has_plan_actions(data):
        result["scope"] += " " + PLAN_ACTION_SCOPE
    if require_reaction_math or _has_reaction_derivations(data):
        result["scope"] += " " + REACTION_MATH_SCOPE
        _check_reaction_math(data, result, require_reaction_math)
    try:
        _check(data, result, require_expert_plan, require_named_methods, require_plan_actions)
    except (ValueError, TypeError, KeyError) as exc:
        result["errors"].append(str(exc))
    if require_source_review or isinstance(data, dict) and "source_review" in data:
        result["scope"] += " " + SOURCE_REVIEW_SCOPE
        _check_source_review(data, result, source_root, require_source_review)
    if not result["errors"]:
        result["status"] = ("STRUCTURE_VALID_WITH_UNRESOLVED" if result["unresolved"]
                            else "STRUCTURE_VALID")
    return result


def _check(data, result, require_expert_plan=False, require_named_methods=False, require_plan_actions=False):
    obj(data, {"schema", "stage", "authority_reference", "nodes", "streams", "control_volumes",
               "placeholders", "no_placeholders_reason", "handoffs"}, "input", optional={"expert_plan", "source_review"})
    if data["schema"] != SCHEMA or data["stage"] not in ("source", "scaffold"):
        raise ValueError("input: expected document-flow-handoff-v1 and source/scaffold stage")
    result["stage"] = data["stage"]
    result["authority_reference"] = text(data["authority_reference"], "authority_reference")
    nodes = indexed(data["nodes"], {"id", "kind"}, "nodes",
                    optional={"no_inflow_reason", "no_outflow_reason"})
    if not nodes:
        raise ValueError("nodes: explicit process/external inventory required")
    for identifier, node in nodes.items():
        if node["kind"] not in ("process", "external"):
            raise ValueError(f"node {identifier}: kind must be process or external")
        for key in ("no_inflow_reason", "no_outflow_reason"):
            reason = text(node.get(key), f"node {identifier}.{key}", nullable=True)
            if node["kind"] == "external" and reason is not None:
                raise ValueError(f"node {identifier}: absence reasons apply only to process nodes")

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

    for identifier, node in nodes.items():
        if node["kind"] != "process":
            continue
        record = {"node": identifier, "missing": [], "declared_absent": {}}
        for side, endpoint, other, reason_key in (
                ("in", "to", "from", "no_inflow_reason"),
                ("out", "from", "to", "no_outflow_reason")):
            connected = [sid for sid, stream in streams.items()
                         if stream[endpoint] == identifier and stream[other] != identifier]
            record[side] = connected
            reason = node.get(reason_key)
            if connected and reason is not None:
                result["errors"].append(f"node {identifier} {side}: {reason_key} contradicts declared streams {connected}")
            elif not connected and reason is None:
                record["missing"].append(side)
                result["errors"].append(
                    f"node {identifier} {side}: missing process interface; declare its stream "
                    f"(use a null other endpoint with a precise gap if unknown), or give a "
                    f"source-bound {reason_key} only if this interface is actually absent")
            elif reason is not None:
                record["declared_absent"][side] = reason
        result["node_interface_rows"].append(record)

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
    if require_expert_plan and "expert_plan" not in data:
        raise ValueError("expert_plan: required by --require-expert-plan")
    if "expert_plan" in data:
        _check_expert_plan(data, nodes, streams, result, require_named_methods, require_plan_actions)
        result["expert_plan_checked"] = not result["errors"]


def registered_names(value, registry, where, nonempty=True):
    identifiers = names(value, where, nonempty)
    unknown = set(identifiers) - set(registry)
    if unknown:
        raise ValueError(f"{where}: unregistered identifiers {sorted(unknown)}")
    return identifiers


def topological_order(process_ids, streams, tears):
    """Kahn check of declared process edges only; unknown endpoints are excluded."""
    successors = {identifier: [] for identifier in process_ids}
    indegrees = dict.fromkeys(process_ids, 0)
    for identifier, stream in streams.items():
        a, b = stream["from"], stream["to"]
        if identifier not in tears and a in indegrees and b in indegrees:
            successors[a].append(b)
            indegrees[b] += 1
    ready = deque(sorted(identifier for identifier, degree in indegrees.items() if degree == 0))
    order = []
    while ready:
        identifier = ready.popleft()
        order.append(identifier)
        for target in successors[identifier]:
            indegrees[target] -= 1
            if indegrees[target] == 0:
                ready.append(target)
    if len(order) != len(process_ids):
        raise ValueError("expert_plan.recycle_plan: declared process graph still contains a cycle "
                         "after removing declared tear streams; recycle coverage incomplete")
    return order


def _check_expert_plan(data, nodes, streams, result, require_named_methods=False, require_plan_actions=False):
    if data["stage"] != "source":
        raise ValueError("expert_plan: source-only; scaffold stage is not allowed")
    plan = obj(data["expert_plan"], {"methods", "pressure_paths", "recycle_plan", "no_recycle_reason"},
               "expert_plan", optional={"reaction_derivations"})
    if any(row["execution_status"] != "not_executed" for row in data["handoffs"]):
        raise ValueError("expert_plan: source-only planning cannot include self-reported execution")
    process_ids = {identifier for identifier, node in nodes.items() if node["kind"] == "process"}
    if not process_ids:
        raise ValueError("expert_plan: at least one declared process node required")
    projection = {"methods": [], "pressure_paths": [], "recycle_plan": [],
                  "no_recycle_reason": None, "cycle_coverage": {}}
    result["expert_plan_rows"] = projection
    covered = set()
    catalog_state = {}
    named_checks_ok = True
    for index, row in enumerate(rows(plan["methods"], "expert_plan.methods", True)):
        where = f"expert_plan.methods[{index}]"
        obj(row, {"node_ids", "method", "phases", "applicability", "source", "status", "unresolved_inputs"},
            where, optional={"not_applicable_reason", "named_methods"})
        covered.update(registered_names(row["node_ids"], process_ids, where + ".node_ids"))
        for field in ("method", "applicability", "source"):
            text(row[field], where + "." + field)
        status = row["status"]
        if status not in ("source_fixed", "candidate", "not_applicable"):
            raise ValueError(f"{where}.status: source_fixed, candidate or not_applicable required; no verification/run status allowed")
        names(row["phases"], where + ".phases", status != "not_applicable")
        reason = text(row.get("not_applicable_reason"), where + ".not_applicable_reason", nullable=True)
        if status == "not_applicable" and reason is None:
            raise ValueError(f"{where}: not_applicable requires its specific not_applicable_reason")
        if status != "not_applicable" and reason is not None:
            raise ValueError(f"{where}: not_applicable_reason contradicts method status")
        gaps = names(row["unresolved_inputs"], where + ".unresolved_inputs")
        result["unresolved"].extend(f"{where} input: {gap}" for gap in gaps)
        if status != "source_fixed":
            result["unresolved"].append(f"{where}: {status} declaration; applicability is unverified")
        try:
            _check_named_methods(row, where, result, require_named_methods, catalog_state)
        except (ValueError, TypeError, KeyError) as exc:
            result["errors"].append(str(exc))
            named_checks_ok = False
        projection["methods"].append(dict(row))
    if covered != process_ids:
        raise ValueError(f"expert_plan.methods: missing process-node coverage {sorted(process_ids - covered)}")
    result["named_method_declarations_checked"] = (
        (require_named_methods or _has_named_methods(data)) and named_checks_ok)

    covered = set()
    pressure_paths = indexed(plan["pressure_paths"], {"id", "node_ids", "stream_ids", "state", "method",
        "equation_or_reason", "source", "inputs", "refine_trigger"}, "expert_plan.pressure_paths",
        optional={"result_reference", "interface_actions"})
    for identifier, row in pressure_paths.items():
        where = f"expert_plan.pressure_paths[{identifier}]"
        path_nodes = set(registered_names(row["node_ids"], process_ids, where + ".node_ids"))
        covered.update(path_nodes)
        state = row["state"]
        if state not in ("symbolic", "calculated", "not_applicable"):
            raise ValueError(f"{where}.state: symbolic, calculated or not_applicable required; no verification/run status allowed")
        path_streams = registered_names(row["stream_ids"], streams, where + ".stream_ids", state != "not_applicable")
        if state != "not_applicable":
            touched = set()
            for stream_id in path_streams:
                stream = streams[stream_id]
                incident = path_nodes.intersection((stream["from"], stream["to"]))
                if not incident:
                    raise ValueError(f"{where}: stream {stream_id} does not touch any node in this group")
                touched.update(incident)
            if touched != path_nodes:
                raise ValueError(f"{where}: group nodes untouched by its streams {sorted(path_nodes - touched)}")
        if state == "calculated":
            text(row.get("result_reference"), where + ".result_reference")
        elif "result_reference" in row:
            raise ValueError(f"{where}: result_reference is allowed only for calculated declarations")
        for field in ("method", "equation_or_reason", "source", "refine_trigger"):
            text(row[field], where + "." + field)
        input_names = set()
        gaps = []
        for index, entry in enumerate(rows(row["inputs"], where + ".inputs", state != "not_applicable")):
            input_where = f"{where}.inputs[{index}]"
            obj(entry, {"name", "unit"}, input_where, optional={"value_or_reference", "gap"})
            name = text(entry["name"], input_where + ".name")
            text(entry["unit"], input_where + ".unit")
            if name in input_names:
                raise ValueError(f"{where}: duplicate input name {name}")
            input_names.add(name)
            if ("value_or_reference" in entry) == ("gap" in entry):
                raise ValueError(f"{input_where}: exactly one of value_or_reference or gap is required")
            if "gap" in entry:
                gaps.append(text(entry["gap"], input_where + ".gap"))
            else:
                value = entry["value_or_reference"]
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    if isinstance(value, float) and not math.isfinite(value):
                        raise ValueError(f"{input_where}.value_or_reference: finite value required")
                else:
                    text(value, input_where + ".value_or_reference")
        if state == "symbolic" and not gaps:
            raise ValueError(f"{where}: symbolic requires at least one explicit input gap")
        if state == "calculated" and gaps:
            raise ValueError(f"{where}: calculated declaration contradicts unresolved input gaps; use symbolic")
        result["unresolved"].extend(f"{where} input: {gap}" for gap in gaps)
        result["unresolved"].append(f"{where}: {state} declaration only; calculation/absence unverified")
        projection["pressure_paths"].append({
            **{key: value for key, value in row.items() if key != "interface_actions"},
            "calculation_verified": False})
    if covered != process_ids:
        raise ValueError(f"expert_plan.pressure_paths: missing process-node coverage {sorted(process_ids - covered)}")

    tears = set()
    recycle_rows = rows(plan["recycle_plan"], "expert_plan.recycle_plan")
    no_recycle_reason = text(plan["no_recycle_reason"], "expert_plan.no_recycle_reason", nullable=True)
    if not recycle_rows and no_recycle_reason is None:
        raise ValueError("expert_plan.recycle_plan: provide tear plans or a source-bound no_recycle_reason")
    if recycle_rows and no_recycle_reason is not None:
        raise ValueError("expert_plan.recycle_plan: tear plans contradict no_recycle_reason")
    for index, row in enumerate(recycle_rows):
        where = f"expert_plan.recycle_plan[{index}]"
        obj(row, {"stream_id", "from", "to", "initialization_basis", "closure_order",
                  "controlled_quantity", "purge_or_terminal_basis"}, where, optional={"startup_plan"})
        stream_id = text(row["stream_id"], where + ".stream_id")
        if stream_id not in streams:
            raise ValueError(f"{where}: unregistered stream {stream_id}")
        if stream_id in tears:
            raise ValueError(f"{where}: duplicate tear stream {stream_id}")
        for endpoint in ("from", "to"):
            value = text(row[endpoint], where + "." + endpoint)
            if value not in process_ids or streams[stream_id][endpoint] != value:
                raise ValueError(f"{where}: {endpoint} must match actual stream {stream_id} registered process endpoint")
        for field in ("initialization_basis", "controlled_quantity", "purge_or_terminal_basis"):
            text(row[field], where + "." + field)
        if type(row["closure_order"]) is not int or row["closure_order"] <= 0:
            raise ValueError(f"{where}.closure_order: positive integer required")
        tears.add(stream_id)
        projection["recycle_plan"].append({key: value for key, value in row.items() if key != "startup_plan"})
    projection["no_recycle_reason"] = no_recycle_reason
    projection["cycle_coverage"] = {
        "tear_stream_ids": sorted(tears),
        "topological_order_after_tears": topological_order(process_ids, streams, tears),
        "declared_graph_acyclic_after_tears": True,
        "coverage": result["declared_topology"]["coverage"],
        "source_cycles_verified": False,
        "scope": "Declared process edges only; unknown endpoints and omitted source edges are not proven absent."}
    _check_plan_actions(plan, streams, projection, require_plan_actions)
    result["plan_action_declarations_checked"] = (
        (require_plan_actions or _has_plan_actions(data)) and not result["errors"])


def _check_plan_actions(plan, streams, projection, required=False):
    """Check optional declarations only; do not compute pressures or recycle seeds."""
    projected_pressure = {row["id"]: row for row in projection["pressure_paths"]}
    for row in plan["pressure_paths"]:
        where = f"expert_plan.pressure_paths[{row['id']}].interface_actions"
        if "interface_actions" not in row:
            if required and row["state"] != "not_applicable":
                raise ValueError(f"{where}: required by --require-plan-actions")
            continue
        actions = rows(row["interface_actions"], where)
        if row["state"] == "not_applicable":
            if actions:
                raise ValueError(f"{where}: not_applicable permits only [] or omission")
            projected_pressure[row["id"]]["interface_actions"] = []
            continue
        action_ids = []
        action_projection = []
        for index, action in enumerate(actions):
            location = f"{where}[{index}]"
            obj(action, {"stream_id", "receiver_requirement", "budget_relation",
                         "equipment_action", "condition_or_basis"}, location)
            stream_id = text(action["stream_id"], location + ".stream_id")
            action_ids.append(stream_id)
            for field in ("receiver_requirement", "budget_relation",
                          "equipment_action", "condition_or_basis"):
                text(action[field], location + "." + field)
        registered_names(action_ids, streams, where + ".stream_ids", nonempty=False)
        if set(action_ids) != set(row["stream_ids"]):
            missing = sorted(set(row["stream_ids"]) - set(action_ids))
            unexpected = sorted(set(action_ids) - set(row["stream_ids"]))
            raise ValueError(f"{where}: must exactly cover group stream_ids; "
                             f"missing {missing}; unexpected {unexpected}")
        for action in actions:
            stream = streams[action["stream_id"]]
            action_projection.append({**action, "from": stream["from"], "to": stream["to"]})
        projected_pressure[row["id"]]["interface_actions"] = action_projection

    recycle_by_stream = {row["stream_id"]: row for row in plan["recycle_plan"]}
    projected_recycle = {row["stream_id"]: row for row in projection["recycle_plan"]}
    for row in plan["recycle_plan"]:
        where = f"expert_plan.recycle_plan[{row['stream_id']}].startup_plan"
        if "startup_plan" not in row:
            if required:
                raise ValueError(f"{where}: required by --require-plan-actions")
            continue
        startup = obj(row["startup_plan"],
                      {"temporary_boundary", "forward_pass", "seed_outlet_stream_id",
                       "depends_on_recycles", "closure_reason"}, where)
        for field in ("temporary_boundary", "forward_pass", "closure_reason"):
            text(startup[field], where + "." + field)
        seed_id = text(startup["seed_outlet_stream_id"], where + ".seed_outlet_stream_id")
        if seed_id not in streams:
            raise ValueError(f"{where}.seed_outlet_stream_id: unregistered stream {seed_id}")
        if streams[seed_id]["from"] != row["from"]:
            raise ValueError(f"{where}.seed_outlet_stream_id: seed stream from must match "
                             f"tear stream source node {row['from']}")
        dependencies = registered_names(startup["depends_on_recycles"], recycle_by_stream,
                                        where + ".depends_on_recycles", nonempty=False)
        for dependency in dependencies:
            if dependency == row["stream_id"]:
                raise ValueError(f"{where}.depends_on_recycles: self-dependency is not allowed")
            if recycle_by_stream[dependency]["closure_order"] >= row["closure_order"]:
                raise ValueError(f"{where}.depends_on_recycles: dependency {dependency} "
                                 "must have a strictly smaller closure_order")
        projected_recycle[row["stream_id"]]["startup_plan"] = dict(startup)


def cell(value):
    return str(value if value is not None else "unknown").replace("|", "\\|").replace("\r", " ").replace("\n", " / ")


def expert_plan_markdown(result):
    if "expert_plan_rows" not in result:
        return []
    plan = result["expert_plan_rows"]
    lines = ["", "## Source-only expert plan", "", EXPERT_SCOPE, "",
             f"Expert plan structurally checked: {str(result['expert_plan_checked']).lower()}", "",
             "### Method groups", "",
             "| Process nodes | Method | Phases | Status | Applicability | Source | Unresolved inputs | Not-applicable reason |",
             "|---|---|---|---|---|---|---|---|"]
    for row in plan["methods"]:
        lines.append("| " + " | ".join(cell(row.get(key)) for key in (
            "node_ids", "method", "phases", "status", "applicability", "source",
            "unresolved_inputs", "not_applicable_reason")) + " |")
    if NAMED_METHOD_SCOPE in result["scope"]:
        lines += ["", "### Named-method declarations", "", NAMED_METHOD_SCOPE, "",
                  f"Named-method declarations checked: {str(result['named_method_declarations_checked']).lower()}"]
        if "named_method_catalog" in result:
            catalog = result["named_method_catalog"]
            lines += [f"- Fixed name catalog version: {cell(catalog['version'])}; SHA-256: {catalog['sha256']}"]
        for row in plan["methods"]:
            if "named_methods" in row:
                lines += [f"- Nodes {cell(row['node_ids'])}; declared names (sources unverified): {cell(row['named_methods'])}"]
    if PLAN_ACTION_SCOPE in result["scope"]:
        lines += ["", "### Plan-action declarations", "", PLAN_ACTION_SCOPE, "",
                  f"Plan-action declarations checked: {str(result['plan_action_declarations_checked']).lower()}"]
    lines += ["", "### Pressure paths", ""]
    for row in plan["pressure_paths"]:
        lines += [f"#### {cell(row['id'])}", "",
                  f"- Process nodes: {cell(row['node_ids'])}; streams: {cell(row['stream_ids'])}",
                  f"- Declared state: {cell(row['state'])}; calculation verified: false",
                  f"- Method: {cell(row['method'])}; equation or absence reason: {cell(row['equation_or_reason'])}",
                  f"- Source: {cell(row['source'])}; refinement trigger: {cell(row['refine_trigger'])}"]
        if "result_reference" in row:
            lines += [f"- Declared calculation result reference (not opened or verified): {cell(row['result_reference'])}"]
        for entry in row["inputs"]:
            lines += [f"- Input {cell(entry['name'])} [{cell(entry['unit'])}]: "
                      f"{cell(entry.get('value_or_reference'))}; gap: {cell(entry.get('gap'))}"]
        for action in row.get("interface_actions", []):
            lines += [f"- Interface action {cell(action['stream_id'])}: "
                      f"{cell(action.get('from'))} -> {cell(action.get('to'))} "
                      "(endpoints projected from declared streams)",
                      f"  Receiver requirement: {cell(action['receiver_requirement'])}",
                      f"  Budget relation: {cell(action['budget_relation'])}",
                      f"  Equipment action: {cell(action['equipment_action'])}",
                      f"  Condition or basis: {cell(action['condition_or_basis'])}"]
        lines.append("")
    lines += ["### Recycle initialization and closure plan", ""]
    if plan["no_recycle_reason"]:
        lines += [f"Declared no-recycle reason (unverified): {cell(plan['no_recycle_reason'])}", ""]
    for row in plan["recycle_plan"]:
        lines += [f"- Tear {cell(row['stream_id'])}: {cell(row['from'])} -> {cell(row['to'])}; closure order: {row['closure_order']}",
                  f"  Initialization basis: {cell(row['initialization_basis'])}",
                  f"  Controlled quantity: {cell(row['controlled_quantity'])}",
                  f"  Purge or terminal basis: {cell(row['purge_or_terminal_basis'])}"]
        if "startup_plan" in row:
            startup = row["startup_plan"]
            lines += [f"  Temporary boundary: {cell(startup['temporary_boundary'])}",
                      f"  Forward pass: {cell(startup['forward_pass'])}",
                      f"  Declared seed outlet (not computed or verified): {cell(startup['seed_outlet_stream_id'])}",
                      f"  Declared recycle dependencies: {cell(startup['depends_on_recycles'])}",
                      f"  Closure reason: {cell(startup['closure_reason'])}"]
    if plan["cycle_coverage"]:
        lines += ["", f"Declared process topological order after tears: {cell(plan['cycle_coverage']['topological_order_after_tears'])}",
                  cell(plan["cycle_coverage"]["scope"])]
    return lines + [""]


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
    lines += ["", "## Process-node interface coverage", "",
              "Declared connections or absence reasons only; absence reasons require source/phase review, not verified by this checker. No physical closure is proven.", "",
              "| Process node | Inlet streams | Outlet streams | Missing interfaces | Declared absence reason |",
              "|---|---|---|---|---|"]
    for row in result["node_interface_rows"]:
        lines.append("| " + " | ".join(cell(row[key]) for key in
                     ("node", "in", "out", "missing", "declared_absent")) + " |")
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
    lines += expert_plan_markdown(result)
    if "reaction_math" in result:
        receipt = result["reaction_math"]
        helper = receipt["helper"]
        outcome = receipt["result"]
        lines += ["", "## Reaction arithmetic", "", REACTION_MATH_SCOPE, "",
                  f"Helper return protocol checked: {str(result['reaction_derivations_checked']).lower()}",
                  f"Fixed helper: {cell(helper['path'])}; SHA-256: {cell(helper['sha256'])}"]
        if outcome is not None:
            lines += [f"Status: {cell(outcome['status'])}; applicable: {cell(outcome['applicable'])}; "
                      f"math checked: {cell(outcome['math_checked'])}; math valid: {cell(outcome['math_valid'])}",
                      "", "Complete deterministic helper output:", "", "```json",
                      json.dumps(outcome, ensure_ascii=False, indent=2), "```", ""]
    for key in ("errors", "unresolved"):
        lines += [f"## {key}", ""] + ([f"- {cell(x)}" for x in result[key]] or ["None reported by this structural check."]) + [""]
    lines += ["Engineering accepted: false. Execution verified: false. Source/inventory truth remains unverified.", ""]
    if "source_review" in result:
        lines += ["## Source paragraph dispositions and declared stream endpoints", "",
                  SOURCE_REVIEW_SCOPE, "",
                  f"Source review mechanically checked: {str(result['source_review_checked']).lower()}",
                  "", "```json", json.dumps(result["source_review"], ensure_ascii=False, indent=2), "```", ""]
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
    parser.add_argument("--output-dir", type=Path, help="New project output directory; required except in source-inventory mode; existing directories are not overwritten")
    parser.add_argument("--source-root", type=Path, help="Explicit local root for listed source-review .txt/.md files; never defaults to cwd")
    parser.add_argument("--source-inventory", action="store_true",
                        help="Read input.source_review.documents using optional unit_mode and print inventory only; no disposition or engineering check")
    parser.add_argument("--require-source-review", action="store_true",
                        help="Require explicit-source paragraph coverage and stream references; implies all four prior strict checks; not source truth")
    parser.add_argument("--require-expert-plan", action="store_true",
                        help="Require source-only expert planning fields; checks structure, not method/equation/engineering validity")
    parser.add_argument("--require-named-methods", action="store_true",
                        help="Require named method declarations; implies --require-expert-plan; no applicability or source-truth verification")
    parser.add_argument("--require-plan-actions", action="store_true",
                        help="Require plan-action declarations; implies both expert-plan and named-method requirements; no engineering verification")
    parser.add_argument("--require-reaction-math", action="store_true",
                        help="Require actual reaction-math checking or explicit not-applicable declaration; implies all three existing requirements; not engineering verification")
    args = parser.parse_args()
    if args.source_inventory and (args.output_dir is not None or args.require_source_review
            or args.require_reaction_math or args.require_plan_actions or args.require_named_methods or args.require_expert_plan):
        parser.error("--source-inventory is a read-only inventory mode; do not combine it with output-dir or strict checker flags")
    if not args.source_inventory and args.output_dir is None:
        parser.error("--output-dir is required for handoff checking")
    try:
        if args.input.stat().st_size > 2_000_000:
            raise ValueError("Input exceeds 2 MB")
        raw = args.input.read_bytes()
        data = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique_object)
        if args.source_inventory:
            review = data.get("source_review") if isinstance(data, dict) else None
            if not isinstance(review, dict) or "documents" not in review:
                raise ValueError("source-inventory mode requires input.source_review.documents")
            unit_mode = _source_unit_mode(review.get("unit_mode", "paragraphs_v1"))
            inventory = source_inventory(review["documents"], source_root=args.source_root, unit_mode=unit_mode)
            print(json.dumps({"schema": "document-flow-source-inventory-v1",
                              "status": "SOURCE_PARAGRAPHS_READ", "inventory": inventory,
                              "unit_mode": unit_mode,
                              "input_sha256": hashlib.sha256(raw).hexdigest(),
                              "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                              "source_review_checked": False, "source_inventory_verified": False,
                              "source_truth_verified": False, "engineering_accepted": False,
                              "execution_verified": False, "authority_verified": False,
                              "boundary": SOURCE_REVIEW_SCOPE}, ensure_ascii=False))
            return 0
        result = check(data, require_expert_plan=args.require_expert_plan,
                       require_named_methods=args.require_named_methods,
                       require_plan_actions=args.require_plan_actions,
                       require_reaction_math=args.require_reaction_math,
                       require_source_review=args.require_source_review, source_root=args.source_root)
        result["input_sha256"] = hashlib.sha256(raw).hexdigest()
        result["checker_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        args.output_dir.mkdir(parents=True, exist_ok=False)
        (args.output_dir / "review.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (args.output_dir / "handoff.md").write_text(markdown(result), encoding="utf-8")
        print(json.dumps({"status": result["status"], "errors": result["errors"],
                          "unresolved": result["unresolved"], "engineering_accepted": False,
                          "execution_verified": False, "authority_verified": False,
                          "source_inventory_verified": False,
                          "source_review_checked": result["source_review_checked"],
                          "source_review": result.get("source_review"),
                          "expert_plan_checked": result["expert_plan_checked"],
                          "named_method_declarations_checked": result["named_method_declarations_checked"],
                          "plan_action_declarations_checked": result["plan_action_declarations_checked"],
                          "reaction_derivations_checked": result["reaction_derivations_checked"],
                          "reaction_math": result.get("reaction_math"),
                          "named_method_catalog": result.get("named_method_catalog"),
                          "scope": result["scope"]}, ensure_ascii=False))
        return 2 if result["errors"] else 0
    except (OSError, ValueError, RecursionError) as exc:
        print(json.dumps({"status": "INPUT_OR_OUTPUT_ERROR", "error": str(exc), "engineering_accepted": False}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
