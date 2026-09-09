#!/usr/bin/env python3
"""Template: physical plausibility gate for a converged Aspen case.

Feed this script a project-local JSON ledger. It checks declared pass/fail rows
and refuses to call a merely converged but unrealistic model accepted.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


REQUIRED_CHECKS = [
    "source_capacity_and_product_basis",
    "feed_to_product_mass_closure",
    "element_or_key_component_balance",
    "stoichiometric_limit_check",
    "conversion_selectivity_yield_window",
    "raw_material_recovery_and_purge_reason",
    "recycle_closure_and_makeup_logic",
    "property_method_applicability",
    "phase_temperature_pressure_sanity",
    "heating_cooling_duty_sign_and_scale",
    "pressure_device_topology",
    "tower_or_separator_recovery_logic",
    "kinetics_or_surrogate_reactor_status",
    "terminal_stream_classification",
]


def load_ledger(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def normalize_status(value: object) -> str:
    return str(value or "").strip().lower()


def evaluate(ledger: dict) -> tuple[str, list[dict[str, object]]]:
    rows: list[dict[str, object]] = []
    checks = ledger.get("checks", {})
    for key in REQUIRED_CHECKS:
        item = checks.get(key, {})
        status = normalize_status(item.get("status") if isinstance(item, dict) else item)
        passed = status in {"pass", "accepted", "ok", "yes"}
        provisional = status in {"provisional", "partial", "unknown"}
        rows.append(
            {
                "check": key,
                "status": status or "missing",
                "passed": passed,
                "provisional": provisional,
                "evidence": item.get("evidence", "") if isinstance(item, dict) else "",
                "note": item.get("note", "") if isinstance(item, dict) else "",
            }
        )
    if all(row["passed"] for row in rows):
        return "physically-plausible", rows
    if any(row["status"] == "missing" or row["provisional"] for row in rows):
        return "provisional-physical", rows
    return "blocked-physical", rows


def write_reports(out_dir: Path, ledger_path: Path, decision: str, rows: list[dict[str, object]]) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "created": datetime.now().isoformat(timespec="seconds"),
        "ledger": str(ledger_path),
        "decision": decision,
        "rows": rows,
        "warning": "Converged Aspen status is insufficient without this physical plausibility gate.",
    }
    json_path = out_dir / "physical_plausibility_gate.json"
    md_path = out_dir / "physical_plausibility_gate.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Physical Plausibility Gate",
        "",
        f"- decision: `{decision}`",
        "- warning: convergence alone is not acceptance.",
        "",
        "| Check | Status | Evidence |",
        "| --- | --- | --- |",
    ]
    for row in rows:
        lines.append(f"| {row['check']} | `{row['status']}` | {str(row['evidence'])[:240]} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate physical plausibility ledger for a converged Aspen case.")
    parser.add_argument("--ledger-json", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    ledger_path = Path(args.ledger_json).resolve()
    decision, rows = evaluate(load_ledger(ledger_path))
    json_path, md_path = write_reports(Path(args.out_dir), ledger_path, decision, rows)
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0 if decision == "physically-plausible" else 2


if __name__ == "__main__":
    raise SystemExit(main())
