#!/usr/bin/env python3
"""Template: delivery hard-gate audit from a project-local manifest.

This checks evidence files and text/JSON gates. It does not run Aspen; pair it
with open-run readiness evidence before calling a case runnable.
"""

from __future__ import annotations

import argparse
import json
import re
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


def get_path(data: Any, dotted: str) -> Any:
    current = data
    for part in dotted.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            current = current[int(part)]
        else:
            return None
    return current


def check_required_files(root: Path, manifest: dict) -> list[dict]:
    rows = []
    for item in manifest.get("required_files", []):
        path = as_path(root, item)
        rows.append({"gate": "required_file", "target": item, "passed": path.exists(), "evidence": str(path)})
    return rows


def check_text(root: Path, manifest: dict) -> list[dict]:
    rows = []
    text_files = manifest.get("text_files", [])
    for rule in manifest.get("forbid_text", []):
        pattern = re.compile(rule["pattern"], re.I | re.M)
        allow_pattern = re.compile(rule["allow_if_pattern"], re.I | re.M) if rule.get("allow_if_pattern") else None
        hits = []
        for item in text_files:
            path = as_path(root, item)
            if not path.exists():
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
        passed = actual == rule.get("equals")
        rows.append(
            {
                "gate": "json_check",
                "target": f"{rule['file']}:{rule['path']}",
                "passed": passed,
                "evidence": {"actual": actual, "expected": rule.get("equals")},
            }
        )
    return rows


def write_reports(out_dir: Path, manifest_path: Path, rows: list[dict]) -> tuple[Path, Path, bool]:
    out_dir.mkdir(parents=True, exist_ok=True)
    passed = all(row["passed"] for row in rows)
    payload = {
        "created": datetime.now().isoformat(timespec="seconds"),
        "manifest": str(manifest_path),
        "passed": passed,
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
    args = parser.parse_args()

    manifest_path = Path(args.manifest_json).resolve()
    manifest = load_json(manifest_path)
    root = rel_root(manifest_path, manifest)
    rows = check_required_files(root, manifest) + check_text(root, manifest) + check_json(root, manifest)
    json_path, md_path, passed = write_reports(Path(args.out_dir), manifest_path, rows)
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
