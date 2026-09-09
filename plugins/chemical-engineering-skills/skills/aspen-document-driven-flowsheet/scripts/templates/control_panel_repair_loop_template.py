#!/usr/bin/env python3
"""Template: Control Panel driven repair loop.

Use one repair family per run. Do not change default/global precision.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


def capture_control_panel(case_file: Path) -> str:
    """Project edit point: capture first limiting Control Panel/history message."""
    raise NotImplementedError


def apply_fix(case_file: Path, out_case_file: Path, repair_family: str) -> list[str]:
    """Project edit point: apply the smallest evidenced fix.

    Return touched cards/files. Do not edit tolerances or unrelated topology.
    """
    raise NotImplementedError


def run_probe(case_file: Path) -> str:
    """Project edit point: run short probe and return status."""
    raise NotImplementedError


def main() -> int:
    parser = argparse.ArgumentParser(description="Control Panel repair loop template.")
    parser.add_argument("--case-file", required=True)
    parser.add_argument("--out-case-file", required=True)
    parser.add_argument("--repair-family", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    case_file = Path(args.case_file)
    out_case_file = Path(args.out_case_file)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    before = capture_control_panel(case_file)
    touched = apply_fix(case_file, out_case_file, args.repair_family)
    status = run_probe(out_case_file)
    after = capture_control_panel(out_case_file)

    record = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "case_file": str(case_file),
        "out_case_file": str(out_case_file),
        "repair_family": args.repair_family,
        "default_precision_lock": "Do not change CONV-OPTIONS PARAM TOL, TOL-SPEC, balance tolerances, or product-spec tolerances.",
        "first_limiting_message_before_fix": before,
        "touched": touched,
        "run_status_after_fix": status,
        "first_limiting_message_after_fix": after,
        "blocker_changed": before != after,
    }

    path = out_dir / "control_panel_repair_loop.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {path}")
    return 0 if before != after else 2


if __name__ == "__main__":
    raise SystemExit(main())

