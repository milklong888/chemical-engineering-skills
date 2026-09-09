#!/usr/bin/env python3
"""Audit a project-local source/taskbook gate ledger.

Copy this template into the active project before adding project-specific
document parsers. The generic template only checks ledger completeness and gate
status; it does not extract values from source files by itself.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


REQUIRED_CATEGORIES = [
    "document_inventory",
    "source_route_and_block_intent",
    "feeds_and_capacity_basis",
    "products_byproducts_waste_and_purity_targets",
    "reaction_network_and_conversion_or_kinetics_requirements",
    "separation_targets_and_equipment_family_requirements",
    "recycle_purge_makeup_and_solvent_logic",
    "pressure_temperature_utility_and_material_constraints",
    "tower_hydraulic_or_equipment_design_requirements",
    "property_method_freeze_rows",
    "deliverables_and_grading_gates",
    "user_adjustments_and_approved_offsets",
    "ambiguous_missing_or_unread_items",
]

PASS_STATUSES = {"accepted", "not-applicable"}
OPEN_STATUSES = {"provisional", "blocked", "missing", "unread", "conflict"}


@dataclass
class CategoryResult:
    category: str
    status: str
    evidence: str
    next_allowed_action: str

    @property
    def passed(self) -> bool:
        return self.status in PASS_STATUSES


def load_ledger(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Ledger not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Ledger is not valid JSON: {path}: {exc}") from exc


def coerce_rows(ledger: dict[str, Any]) -> dict[str, Any]:
    if isinstance(ledger.get("categories"), dict):
        return dict(ledger["categories"])
    if isinstance(ledger.get("checks"), dict):
        return dict(ledger["checks"])
    rows: dict[str, Any] = {}
    if isinstance(ledger.get("checks"), list):
        for item in ledger["checks"]:
            if isinstance(item, dict) and item.get("category"):
                rows[str(item["category"])] = item
    return rows


def evaluate_category(category: str, raw: Any) -> CategoryResult:
    if raw is None:
        return CategoryResult(category, "missing", "", "extract this category from the source/taskbook")
    if isinstance(raw, str):
        status = raw.strip().lower() or "missing"
        return CategoryResult(category, status, "", "supply evidence and next action")
    if not isinstance(raw, dict):
        return CategoryResult(category, "blocked", "", "replace malformed ledger row with a structured object")

    status = str(raw.get("status") or "").strip().lower()
    if not status:
        status = "accepted" if raw.get("evidence") else "missing"
    evidence = str(raw.get("evidence") or raw.get("source") or "")
    next_action = str(raw.get("next_allowed_action") or raw.get("next_action") or "")
    if status in PASS_STATUSES and not evidence and category != "ambiguous_missing_or_unread_items":
        status = "provisional"
        next_action = next_action or "attach source/page/evidence before promotion"
    if not next_action and status in OPEN_STATUSES:
        next_action = "resolve before Aspen mutation or final delivery"
    return CategoryResult(category, status, evidence, next_action)


def evaluate(ledger: dict[str, Any]) -> dict[str, Any]:
    rows = coerce_rows(ledger)
    results = [evaluate_category(category, rows.get(category)) for category in REQUIRED_CATEGORIES]

    blocked = [item for item in results if item.status == "blocked"]
    open_items = [item for item in results if not item.passed]
    decision = "accepted" if not open_items else "provisional"
    if blocked:
        decision = "blocked"

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project": ledger.get("project") or "",
        "source_ledger": ledger.get("source_ledger") or "",
        "decision": decision,
        "required_categories": REQUIRED_CATEGORIES,
        "results": [item.__dict__ | {"passed": item.passed} for item in results],
        "open_categories": [item.category for item in open_items],
        "blocked_categories": [item.category for item in blocked],
        "policy": {
            "aspen_mutation_allowed": decision == "accepted",
            "final_delivery_allowed": decision == "accepted",
            "property_method_changes_require_offset": True,
            "control_panel_remains_primary_for_failed_runs": True,
        },
    }


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Source Taskbook Gate Audit",
        "",
        f"- Generated: `{summary['generated_at']}`",
        f"- Project: `{summary.get('project', '')}`",
        f"- Decision: `{summary['decision']}`",
        "",
        "| Category | Status | Evidence | Next allowed action |",
        "| --- | --- | --- | --- |",
    ]
    for row in summary["results"]:
        lines.append(
            f"| `{row['category']}` | `{row['status']}` | {row['evidence'] or ''} | "
            f"{row['next_allowed_action'] or ''} |"
        )
    lines.extend(
        [
            "",
            "## Gate Statement",
            "",
            "- Aspen mutation is allowed only when every required source/taskbook row is accepted or not-applicable.",
            "- User adjustments must be represented in the change-offset table before they change Aspen inputs.",
            "- This audit supports source completeness; it does not replace Aspen Required Input, Control Panel, or physical-plausibility evidence.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit an Aspen source/taskbook gate ledger.")
    parser.add_argument("--ledger-json", required=True, help="Project-local JSON ledger to audit.")
    parser.add_argument("--out-dir", required=True, help="Directory for summary JSON/MD.")
    args = parser.parse_args()

    ledger_path = Path(args.ledger_json).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = evaluate(load_ledger(ledger_path))
    json_path = out_dir / "source_taskbook_gate_audit.json"
    md_path = out_dir / "source_taskbook_gate_audit.md"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(summary), encoding="utf-8")
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0 if summary["decision"] == "accepted" else 2


if __name__ == "__main__":
    raise SystemExit(main())

