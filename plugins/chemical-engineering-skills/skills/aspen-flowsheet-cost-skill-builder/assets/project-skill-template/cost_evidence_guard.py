"""Shared, deterministic source-identity and procurement-boundary gates.

Approval labels are review metadata; current original bytes must also match.
No network, price inference, or source approval is performed here.
"""
from __future__ import annotations

import csv
import hashlib
import re
from collections import Counter
from pathlib import Path

APPROVED = {"approved", "approved_project_method"}
EXCLUDED_SCOPES = {"reactor_excluded", "excluded_logical_or_bulk", "not_physical_equipment", "included_in_package_excluded"}
ACTIVE_SCOPES = {"purchased_equipment_candidate", "utility_opex_separate"}
KNOWN_SCOPES = EXCLUDED_SCOPES | ACTIVE_SCOPES
REPRODUCED = {"pass", "passed", "reproduced", "verified", "success"}
REQUIRED_FIELDS = (
    "title", "authors_or_organization", "year", "source_type", "authority_tier",
    "url_or_doi", "equipment_family", "service_scope", "cost_scope", "base_period",
    "formula_or_table_locator", "independent_reproduction_status", "local_path", "sha256",
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def tokens(value: str) -> list[str]:
    return [part.strip() for part in value.split(";") if part.strip()]


def audit_equipment_coverage(equipment: list[dict[str, str]], assignments: list[dict[str, str]]) -> list[dict]:
    """Require one assignment for every inventory ID and no unlisted charges.

    Validate raw rows before any dictionary can silently discard duplicates.
    This is a shared cost-entry gate, independent of strict method readiness.
    """
    issues: list[dict] = []
    identities = {}
    for label, rows in (("inventory", equipment), ("assignment", assignments)):
        if not rows:
            issues.append({"type": f"empty_equipment_{label}"})
        ids = []
        for index, row in enumerate(rows, start=2):
            raw = row.get("equipment_item_id") or ""
            eid = raw.strip()
            if not eid or raw != eid:
                issues.append({"type": f"invalid_equipment_{label}_id", "row": index, "equipment_item_id": raw})
            if eid:
                ids.append(eid)
        for eid, count in sorted(Counter(ids).items()):
            if count > 1:
                issues.append({"type": f"duplicate_equipment_{label}", "equipment_item_id": eid, "count": count})
        identities[label] = set(ids)
    for eid in sorted(identities["inventory"] - identities["assignment"]):
        issues.append({"type": "equipment_without_assignment", "equipment_item_id": eid})
    for eid in sorted(identities["assignment"] - identities["inventory"]):
        issues.append({"type": "assignment_without_equipment", "equipment_item_id": eid})
    return issues


def audit_sources(assignments: list[dict[str, str]], ledger_path: Path,
                  extra_source_ids: list[str] | None = None) -> list[dict]:
    issues: list[dict] = []
    try:
        rows = read_csv(ledger_path)
    except (OSError, csv.Error) as exc:
        return [{"type": "source_ledger_unreadable", "error": str(exc)}]
    sources: dict[str, dict] = {}
    for row in rows:
        sid = row.get("source_id", "").strip()
        if not sid or sid in sources:
            issues.append({"type": "source_id_missing_or_duplicate", "source_id": sid})
        sources[sid] = row
    required = set(extra_source_ids or [])
    for row in assignments:
        scope = row.get("scope_class", "")
        if scope not in KNOWN_SCOPES:
            issues.append({"type": "scope_unknown_or_unresolved", "equipment_item_id": row.get("equipment_item_id"), "scope_class": scope})
        if row.get("method_id") == "LOGICAL_OR_REACTOR_EXCLUSION" and scope not in EXCLUDED_SCOPES:
            issues.append({"type": "exclusion_method_scope_conflict", "equipment_item_id": row.get("equipment_item_id")})
        method = row.get("method_id", "")
        if (method == "UTILITY_OPEX") != (scope == "utility_opex_separate"):
            issues.append({"type": "utility_method_scope_conflict", "equipment_item_id": row.get("equipment_item_id"),
                           "scope_class": scope, "method_id": method})
        if scope in EXCLUDED_SCOPES and method != "LOGICAL_OR_REACTOR_EXCLUSION":
            issues.append({"type": "excluded_scope_method_conflict", "equipment_item_id": row.get("equipment_item_id"),
                           "scope_class": scope, "method_id": method})
        required.update(tokens(row.get("package_scope_source_ids", "")))
        if scope in EXCLUDED_SCOPES:
            continue
        ids = tokens(row.get("source_ids", ""))
        if not ids:
            issues.append({"type": "source_missing", "equipment_item_id": row.get("equipment_item_id")})
        required.update(ids)
    # Check referenced sources, plus every source the ledger itself calls approved.
    required.update(sid for sid, row in sources.items()
                    if row.get("review_status", "").strip().lower() in APPROVED)
    for sid in sorted(required):
        row = sources.get(sid)
        if row is None:
            issues.append({"type": "source_not_registered", "source_id": sid})
            continue
        if row.get("review_status", "").strip().lower() not in APPROVED:
            issues.append({"type": "source_not_approved", "source_id": sid})
        missing = [field for field in REQUIRED_FIELDS if not row.get(field, "").strip()]
        if missing:
            issues.append({"type": "source_missing_fields", "source_id": sid, "fields": missing})
        if row.get("independent_reproduction_status", "").strip().lower() not in REPRODUCED:
            issues.append({"type": "source_reproduction_not_passed", "source_id": sid})
        local, expected = row.get("local_path", "").strip(), row.get("sha256", "").strip().lower()
        if not local:
            continue
        path = Path(local)
        if not path.is_absolute():
            path = ledger_path.parent / path
        try:
            observed = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            issues.append({"type": "source_file_unreadable", "source_id": sid, "path": str(path), "error": str(exc)})
            continue
        if not re.fullmatch(r"[0-9a-f]{64}", expected) or observed != expected:
            issues.append({"type": "source_hash_mismatch", "source_id": sid,
                           "path": str(path), "expected": expected, "observed": observed})
    return issues


def audit_procurement(assignments: list[dict[str, str]]) -> list[dict]:
    """Keep physical inventory separate from separately chargeable quote lines."""
    issues: list[dict] = []
    items = {row.get("equipment_item_id", ""): row for row in assignments}
    coverage: dict[str, str] = {}
    for row in assignments:
        eid = row.get("equipment_item_id", "")
        role = row.get("procurement_role", "").strip()
        if row.get("scope_class") == "included_in_package_excluded" and role != "included_in_package":
            issues.append({"type": "package_exclusion_without_parent_role", "equipment_item_id": eid})
        signal = " ".join(row.get(key, "") for key in ("method_id", "physical_equipment")).lower()
        relevant = role or row.get("quote_id") or any(word in signal for word in ("package", "column", "tower", "成套", "塔"))
        if not relevant or (row.get("scope_class", "") in EXCLUDED_SCOPES and role != "included_in_package"):
            continue
        if role not in {"standalone", "package", "included_in_package"}:
            issues.append({"type": "procurement_boundary_unresolved", "equipment_item_id": eid})
            continue
        if row.get("package_scope_status") != "reviewed" or not row.get("package_scope_source_ids", "").strip() or not row.get("package_scope_locator", "").strip():
            issues.append({"type": "procurement_boundary_evidence_missing", "equipment_item_id": eid})
        if role == "package":
            covered = tokens(row.get("covered_equipment_ids", ""))
            if eid not in covered:
                issues.append({"type": "package_coverage_missing_self", "equipment_item_id": eid})
            for child in covered:
                if child in coverage and coverage[child] != eid:
                    issues.append({"type": "overlapping_package_coverage", "equipment_item_id": child, "packages": [coverage[child], eid]})
                coverage[child] = eid
                item = items.get(child)
                if item is None:
                    issues.append({"type": "package_coverage_unknown_item", "equipment_item_id": eid, "covered_item": child})
                elif child != eid and (item.get("procurement_role") != "included_in_package" or item.get("parent_package_id") != eid or item.get("scope_class") != "included_in_package_excluded"):
                    issues.append({"type": "package_item_separately_chargeable", "equipment_item_id": child, "package_id": eid})
    for row in assignments:
        if row.get("procurement_role") == "included_in_package":
            eid = row.get("equipment_item_id", "")
            if not row.get("parent_package_id") or coverage.get(eid) != row.get("parent_package_id"):
                issues.append({"type": "package_parent_coverage_missing", "equipment_item_id": eid})
    return issues
