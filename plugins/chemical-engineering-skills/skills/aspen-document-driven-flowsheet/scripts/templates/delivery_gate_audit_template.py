#!/usr/bin/env python3
"""Template: delivery hard-gate audit from a project-local manifest.

This checks evidence files and text/JSON gates. It does not run Aspen; pair it
with open-run readiness evidence before calling a case runnable.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def rel_root(manifest_path: Path, manifest: dict) -> Path:
    root = manifest.get("project_root", ".")
    return (manifest_path.parent / root).resolve()


def as_path(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


MISSING = object()


def equal_json(a: Any, b: Any) -> bool:
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(equal_json(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(equal_json(x, y) for x, y in zip(a, b))
    if type(a) in (int, float) and type(b) in (int, float):
        return a == b
    return type(a) is type(b) and a == b


def get_path(data: Any, dotted: str) -> Any:
    current = data
    for part in dotted.split("."):
        if isinstance(current, dict):
            current = current.get(part, MISSING)
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return MISSING
    return current


def check_required_files(root: Path, manifest: dict) -> list[dict]:
    rows = []
    for item in manifest.get("required_files", []):
        path = as_path(root, item)
        rows.append({"gate": "required_file", "target": item, "passed": path.is_file(), "evidence": str(path)})
    return rows


def check_text(root: Path, manifest: dict) -> list[dict]:
    rows = []
    text_files = manifest.get("text_files", [])
    for rule in manifest.get("forbid_text", []):
        pattern = re.compile(rule["pattern"], re.I | re.M)
        allow_pattern = re.compile(rule["allow_if_pattern"], re.I | re.M) if rule.get("allow_if_pattern") else None
        hits = []
        if not text_files:
            hits.append({"problem": "No input file for this text rule."})
        for item in text_files:
            path = as_path(root, item)
            if not path.is_file():
                hits.append({"file": item, "problem": "Missing input file."})
                continue
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            for line_no, line in enumerate(text.splitlines(), start=1):
                if pattern.search(line) and not (allow_pattern and allow_pattern.search(line)):
                    hits.append({"file": item, "line": line_no, "text": line.strip()[:240]})
        rows.append({"gate": "forbid_text", "target": rule.get("name", rule["pattern"]), "passed": not hits, "evidence": hits})
    return rows


def check_json(root: Path, manifest: dict) -> list[dict]:
    rows = []
    for rule in manifest.get("json_checks", []):
        path = as_path(root, rule["file"])
        if not path.exists():
            rows.append({"gate": "json_check", "target": f"{rule['file']}:{rule['path']}", "passed": False, "evidence": "missing_file"})
            continue
        data = load_json(path)
        actual = get_path(data, rule["path"])
        expected = rule.get("equals", MISSING)
        passed = actual is not MISSING and expected is not MISSING and equal_json(actual, expected)
        rows.append(
            {
                "gate": "json_check",
                "target": f"{rule['file']}:{rule['path']}",
                "passed": passed,
                "evidence": {"actual": "<missing path>" if actual is MISSING else actual,
                             "expected": "<missing equals>" if expected is MISSING else expected},
            }
        )
    return rows


def write_reports(out_dir: Path, manifest_path: Path, rows: list[dict]) -> tuple[Path, Path, bool]:
    out_dir.mkdir(parents=True, exist_ok=True)
    if not rows:
        rows = [{"gate": "manifest", "target": "delivery checks", "passed": False, "evidence": "Empty check list."}]
    passed = all(row["passed"] for row in rows)
    payload = {
        "created": datetime.now().isoformat(timespec="seconds"),
        "manifest": str(manifest_path),
        "passed": passed,
        "scope": "files_and_final_review" if any(row["gate"] == "final_review" for row in rows) else "declared_file_checks_only",
        "engineering_accepted": False,
        "rows": rows,
        "warning": "Delivery audit is not open-run readiness; clean reopen and start-run evidence are separate hard gates.",
    }
    json_path = out_dir / "delivery_gate_audit.json"
    md_path = out_dir / "delivery_gate_audit.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Delivery Gate Audit",
        "",
        f"- passed: `{str(passed).lower()}`",
        "- warning: this audit does not replace open-run readiness.",
        "",
        "| Gate | Target | Passed | Evidence |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        evidence = json.dumps(row["evidence"], ensure_ascii=False)
        lines.append(f"| {row['gate']} | `{row['target']}` | {str(row['passed']).lower()} | `{evidence[:240]}` |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path, passed


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit delivery files, text gates, and JSON gates from a manifest.")
    parser.add_argument("--manifest-json", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--runtime-root", type=Path, help="Installed engineering runtime for formal delivery review.")
    args = parser.parse_args()

    manifest_path = Path(args.manifest_json).resolve()
    manifest = load_json(manifest_path)
    root = rel_root(manifest_path, manifest)
    try:
        rows = check_required_files(root, manifest) + check_text(root, manifest) + check_json(root, manifest)
    except (OSError, ValueError, TypeError, KeyError, re.error) as exc:
        rows = [{"gate": "manifest", "target": "declared file checks", "passed": False, "evidence": str(exc)}]
    if (manifest.get("formal_delivery") or "review_request" in manifest
            or (root / "PROJECT_REVIEW_FINDINGS.json").exists() or (root / "PROJECT_REVIEW_HISTORY").is_dir()
            or (root / "PROJECT_REVIEW_SCOPE_HISTORY.sqlite3").is_file()):
        try:
            if args.runtime_root:
                sys.path.insert(0, str(args.runtime_root.resolve()))
            else:
                for parent in Path(__file__).resolve().parents:
                    candidates = (parent, parent / "workspace/chemical-engineering-runtime")
                    located = next((p for p in candidates if (p / "tools/review_findings.py").is_file()), None)
                    if located is not None:
                        sys.path.insert(0, str(located))
                        break
            from backends.process.feedback import read_reference
            from tools.fullflow_gate import buildable_plan_requested
            from tools.review_findings import check_delivery_review, remember_stage
            request = dict(manifest["review_request"], stage="delivery")
            authority = read_reference(root, request["authority"])
            frozen_contract = authority.get("delivery_review", {}).get("fullflow_contract")
            if frozen_contract:
                request.setdefault("fullflow_contract", frozen_contract)
            if "fullflow_contract" in request or buildable_plan_requested(request, authority):
                from tools.expert_cli import execute
                request.setdefault("question", "核验当前整套工艺流程的工程交付与遗留问题")
                stage = execute({"operation": "design_stage", "payload": request}, root)
                outcome = {"status": stage["status"], "needs": stage["needs"],
                           "execution_id": stage["execution_id"], "receipt_sha256": stage["receipt_sha256"],
                           "engineering_accepted": False}
                if stage["status"] != "MODULE_CHECKS_EXECUTED" and not outcome["needs"]:
                    outcome["needs"] = [{"code": "DELIVERY_STAGE_INCOMPLETE", "detail": stage["status"]}]
            else:
                remember_stage(root, request)
                outcome = check_delivery_review(root, request)
            rows.append({"gate": "final_review", "target": "current delivery files", "passed": not outcome["needs"], "evidence": outcome})
        except (ImportError, OSError, ValueError, TypeError, AttributeError, KeyError) as exc:
            rows.append({"gate": "final_review", "target": "current delivery files", "passed": False, "evidence": str(exc)})
    json_path, md_path, passed = write_reports(Path(args.out_dir), manifest_path, rows)
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
