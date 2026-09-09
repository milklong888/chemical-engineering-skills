#!/usr/bin/env python3
"""Template: static Aspen INP support audit.

This is a support check only. A passing static audit never proves Required
Input completeness or runnable delivery; clean-session Aspen reopen and
start-run evidence still control delivery readiness.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class CheckResult:
    kind: str
    target: str
    passed: bool
    evidence: str


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def find_keyword_id(text: str, keyword: str, value: str) -> CheckResult:
    pattern = re.compile(rf"(?im)^\s*{re.escape(keyword)}\s+{re.escape(value)}\b")
    if pattern.search(text):
        return CheckResult(keyword.lower(), value, True, f"line starts with {keyword} {value}")

    word_pattern = re.compile(rf"(?i)\b{re.escape(value)}\b")
    found = bool(word_pattern.search(text))
    return CheckResult(
        keyword.lower(),
        value,
        found,
        "identifier appears in file" if found else "identifier not found",
    )


def find_pattern(text: str, pattern_text: str) -> CheckResult:
    pattern = re.compile(pattern_text, re.I | re.M)
    found = bool(pattern.search(text))
    return CheckResult("expect_pattern", pattern_text, found, "regex matched" if found else "regex not found")


def forbid_pattern(text: str, pattern_text: str) -> CheckResult:
    pattern = re.compile(pattern_text, re.I | re.M)
    found = bool(pattern.search(text))
    return CheckResult("forbid_pattern", pattern_text, not found, "regex absent" if not found else "forbidden regex matched")


def write_outputs(inp_file: Path, out_dir: Path, checks: list[CheckResult]) -> tuple[Path, Path, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    passed = all(item.passed for item in checks)
    decision = "support_pass" if passed else "blocked"
    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "inp_file": str(inp_file),
        "decision": decision,
        "delivery_warning": (
            "Static INP audit is support evidence only; it cannot replace Aspen clean-session "
            "reopen, Required Input completeness, start-run, or same-version export evidence."
        ),
        "checks": [asdict(item) for item in checks],
    }

    json_path = out_dir / "static_inp_audit.json"
    md_path = out_dir / "static_inp_audit.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Static INP Audit",
        "",
        f"- inp_file: `{inp_file}`",
        f"- decision: `{decision}`",
        "- warning: static audit is support evidence only; Aspen reopen/start-run still controls delivery.",
        "",
        "| Kind | Target | Passed | Evidence |",
        "| --- | --- | --- | --- |",
    ]
    for item in checks:
        lines.append(f"| {item.kind} | `{item.target}` | {str(item.passed).lower()} | {item.evidence} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path, decision


def main() -> int:
    parser = argparse.ArgumentParser(description="Static support audit for an exported Aspen INP file.")
    parser.add_argument("--inp-file", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--expect-block", action="append", default=[])
    parser.add_argument("--expect-stream", action="append", default=[])
    parser.add_argument("--expect-pattern", action="append", default=[])
    parser.add_argument("--forbid-pattern", action="append", default=[])
    args = parser.parse_args()

    inp_file = Path(args.inp_file)
    text = read_text(inp_file)

    checks: list[CheckResult] = []
    checks.extend(find_keyword_id(text, "BLOCK", block) for block in args.expect_block)
    checks.extend(find_keyword_id(text, "STREAM", stream) for stream in args.expect_stream)
    checks.extend(find_pattern(text, pattern) for pattern in args.expect_pattern)
    checks.extend(forbid_pattern(text, pattern) for pattern in args.forbid_pattern)

    json_path, md_path, decision = write_outputs(inp_file, Path(args.out_dir), checks)
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0 if decision == "support_pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
