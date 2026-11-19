"""Plan inherited finding checks against hash-bound delivery authority."""

from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path
import re


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _scope_tokens(value):
    scopes = [value] if isinstance(value, str) else value
    if not isinstance(scopes, list) or not scopes or not all(_text(scope) for scope in scopes):
        return set()
    return {scope.strip().casefold() for scope in scopes}


def _criterion_key(rule):
    fields = ("path", "unit", "basis")
    if not isinstance(rule, dict) or not all(_text(rule.get(key)) for key in fields):
        raise ValueError("A criterion must specify the exact result path, unit and basis.")
    comparison = rule.get("comparison", "eq")
    if comparison not in ("eq", "ge", "le") or "expected" not in rule:
        raise ValueError("A criterion must specify its expected value and a supported comparison.")
    expected = rule["expected"]
    if type(expected) in (int, float):
        if not math.isfinite(expected):
            raise ValueError("A numerical criterion must be finite.")
        value_key = ("number", expected)
    else:
        value_key = ("json", json.dumps(expected, sort_keys=True, allow_nan=False))
    return (*(rule[key] for key in fields), comparison, value_key)


def _file_key(ref):
    if (not isinstance(ref, dict) or not _text(ref.get("path"))
            or not isinstance(ref.get("sha256"), str)
            or not re.fullmatch(r"[0-9A-Fa-f]{64}", ref["sha256"])):
        raise ValueError("A replacement must reference an original source by exact path and SHA-256.")
    return ref["path"], ref["sha256"].lower()


def _original_record(root, ref, table_ref):
    path, expected_hash = _file_key(ref)
    if not set(ref) <= {"path", "sha256", "pointer"}:
        raise ValueError("A replacement reference cannot contain a caller-declared replacement rule.")
    data = (Path(root) / path).read_bytes()
    if sha256(data).hexdigest() != expected_hash:
        raise ValueError(f"Replacement source hash changed: {path}")
    document = json.loads(data)
    if not isinstance(document, dict):
        raise ValueError("The original approval must be a JSON object.")
    if table_ref is not None and _file_key(table_ref) == (path, expected_hash):
        pointer = ref.get("pointer")
        match = re.fullmatch(r"/finding_criterion_changes/(0|[1-9][0-9]*)", pointer or "")
        if not match or not isinstance(document.get("finding_criterion_changes"), list):
            raise ValueError("Point to an original finding_criterion_changes row in the frozen change-offset table.")
        record = document["finding_criterion_changes"][int(match[1])]
        if not isinstance(record, dict) or record.get("case_id") != document.get("case_id"):
            raise ValueError("The change-offset row and original table must identify the same case.")
        if not _text(record.get("reason")):
            raise ValueError("The approved change-offset row must retain its reason.")
        return record
    if (ref.get("pointer") or document.get("actor") != "user"
            or not all(_text(document.get(key)) for key in ("source_message_id", "source_locator", "user_quote"))):
        raise ValueError("Use the frozen change-offset table or the original confirmed user message record.")
    return document


def _effective_criteria(original, changes):
    """Follow only approved exact-rule replacements, preserving unrelated rules."""
    final = {}
    for old_key, rule in original.items():
        visited = set()
        while old_key in changes:
            if old_key in visited:
                raise ValueError("Cyclic changes cannot establish an effective criterion.")
            visited.add(old_key)
            old_key, rule = changes[old_key]
        final[old_key] = rule
    return list(final.values())


def _out_of_scope(finding_id, issues, items, scopes):
    item = items.get(finding_id, {})
    next_action = item.get("next_action")
    if not _text(next_action):
        actions = [issue.get("next_action") or issue.get("recommended_change") for issue in issues]
        next_action = "\n".join(dict.fromkeys(action for action in actions if _text(action)))
    return {"id": finding_id, "scope": sorted(scopes),
            "next_action": next_action or "Resolve and recheck before delivering the affected scope."}


def plan_finding_review(root, identity, basis, issues_by_id, *, carried_ids=(), current_items=()):
    """Return effective criteria and scope for a frozen delivery_review object.

    The caller retains every finding ID and validates authority and scope
    authorization independently. The source references must originate from the
    actual change-offset table or captured user reply, not from reviewer prose.
    """
    delivery_scope = _scope_tokens(basis.get("scope"))
    if not delivery_scope or not all(_text(identity.get(key)) for key in ("case_id", "task_revision")):
        raise ValueError("Bind the case, task revision and delivery scope before planning finding checks.")
    items = {row["id"]: row for row in current_items}
    criteria_by_id, out_of_scope, replacements, needs = {}, [], [], []
    blocking_ids = set()
    originals = {}
    for finding_id in sorted(set(issues_by_id) | set(carried_ids) | set(items)):
        issues = issues_by_id.get(finding_id, [])
        declared = [_scope_tokens(issue.get("scope")) for issue in issues]
        combined = set().union(*declared)
        if declared and all(declared) and combined.isdisjoint(delivery_scope):
            out_of_scope.append(_out_of_scope(finding_id, issues, items, combined))
            continue
        blocking_ids.add(finding_id)
        rules = [rule for issue in issues for rule in issue.get("criteria", [])]
        originals[finding_id] = {_criterion_key(rule): rule for rule in rules}
        criteria_by_id[finding_id] = list(originals[finding_id].values())

    refs = basis.get("criterion_replacements", [])
    if not isinstance(refs, list):
        raise ValueError("Frozen criterion_replacements must be a list of original record references.")
    changes_by_id, applied_by_id, invalid_ids = {}, {}, set()
    scoped_out = {row["id"] for row in out_of_scope}
    for ref in refs:
        finding_id = None
        try:
            record = _original_record(root, ref, basis.get("change_offset_table_ref"))
            if any(record.get(key) != identity[key] for key in ("case_id", "task_revision")):
                raise ValueError("Replacement belongs to another case or task revision.")
            finding_id = record.get("finding_id")
            if not _text(finding_id) or finding_id not in blocking_ids | scoped_out:
                raise ValueError("Replacement must identify a retained finding ID.")
            if finding_id in scoped_out:
                continue
            if record.get("decision") != "approved":
                raise ValueError("The original record does not approve this criterion change.")
            old_rule, new_rule = record["old_criterion"], record["new_criterion"]
            old_key, new_key = _criterion_key(old_rule), _criterion_key(new_rule)
            if old_key == new_key or old_key not in originals[finding_id]:
                raise ValueError("The original criterion must match the retained rule and the new rule must change it.")
            changes = changes_by_id.setdefault(finding_id, {})
            if old_key in changes and changes[old_key][0] != new_key:
                raise ValueError("Conflicting replacements for the same original criterion.")
            changes[old_key] = new_key, new_rule
            applied_by_id.setdefault(finding_id, []).append(
                {"id": finding_id, "source_ref": ref, "old_criterion": old_rule, "new_criterion": new_rule})
        except (OSError, ValueError, TypeError, KeyError, IndexError, OverflowError) as exc:
            if _text(finding_id):
                invalid_ids.add(finding_id)
            needs.append({"code": "FINDING_CRITERION_AUTHORITY_INVALID", "scope": finding_id or "delivery",
                          "detail": str(exc)})

    for finding_id, changes in changes_by_id.items():
        if finding_id in invalid_ids:
            continue
        try:
            criteria_by_id[finding_id] = _effective_criteria(originals[finding_id], changes)
        except ValueError as exc:
            needs.append({"code": "FINDING_CRITERION_AUTHORITY_INVALID", "scope": finding_id,
                          "detail": str(exc)})
        else:
            replacements.extend(applied_by_id[finding_id])
    return {"criteria_by_id": criteria_by_id, "blocking_ids": sorted(blocking_ids),
            "out_of_scope": out_of_scope, "replacements": replacements, "needs": needs}
