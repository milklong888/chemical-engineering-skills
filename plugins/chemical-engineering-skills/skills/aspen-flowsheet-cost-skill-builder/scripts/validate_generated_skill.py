from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


QUICK_VALIDATE = Path.home() / ".codex" / "skills" / ".system" / "skill-creator" / "scripts" / "quick_validate.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a generated equipment-cost Skill.")
    parser.add_argument("--skill-dir", type=Path, required=True)
    parser.add_argument("--allow-draft", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    skill = args.skill_dir.resolve()
    structural = subprocess.run([sys.executable, str(QUICK_VALIDATE), str(skill)], check=False)
    method = subprocess.run([sys.executable, str(skill / "scripts" / "audit_generated_method.py")], check=False)
    audit_path = skill / "method_audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.exists() else {}
    comparison_ready = audit.get("comparison_contract_status", "fail") == "pass"
    strict_ready = audit.get("strict_status", "fail") == "pass"
    if structural.returncode == 0 and comparison_ready and strict_ready:
        status = "pass"
    elif structural.returncode == 0 and comparison_ready and args.allow_draft:
        status = "draft"
    else:
        status = "fail"
    report = {
        "status": status,
        "skill_dir": str(skill),
        "structural_validation_returncode": structural.returncode,
        "method_audit_returncode": method.returncode,
        "comparison_contract_status": audit.get("comparison_contract_status", "missing"),
        "strict_status": audit.get("strict_status", "missing"),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if status in {"pass", "draft"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
