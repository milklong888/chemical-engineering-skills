from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "assets" / "project-skill-template"))
from cost_evidence_guard import APPROVED as APPROVED_STATES, EXCLUDED_SCOPES, audit_procurement, audit_sources, read_csv


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit current source originals and procurement boundaries.")
    parser.add_argument("--assignments", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    assignments = read_csv(args.assignments)
    issues = audit_sources(assignments, args.ledger.resolve()) + audit_procurement(assignments)
    for row in assignments:
        if row.get("scope_class", "") not in EXCLUDED_SCOPES and row.get("method_id", "") in {"", "METHOD_GAP"}:
            issues.append({"type": "method_gap", "equipment_item_id": row.get("equipment_item_id")})
    source_count = len(read_csv(args.ledger)) if args.ledger.is_file() else 0
    report = {"status": "pass" if not issues else "fail", "assignment_count": len(assignments), "source_count": source_count,
              "issue_count": len(issues), "issues": issues}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
