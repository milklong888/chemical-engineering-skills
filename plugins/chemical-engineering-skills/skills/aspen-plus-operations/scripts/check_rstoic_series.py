from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


BLOCK_RE = re.compile(
    r"\bBLOCK\s+(\S+)\s+RSTOIC\b(?P<body>.*?)(?=\nBLOCK\s+|\nSTREAM-REPORT|\nEO-CONV|\nEND\b|\Z)",
    re.IGNORECASE | re.DOTALL,
)


def scan_text(text: str, source: str) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    for match in BLOCK_RE.finditer(text):
        block = match.group(1)
        body = match.group("body")
        if not re.search(r"\bSERIES\s*=\s*YES\b", body, re.IGNORECASE):
            continue
        stoic_count = len(re.findall(r"^\s*STOIC\s+\d+\b", body, re.IGNORECASE | re.MULTILINE))
        conv_count = len(re.findall(r"^\s*CONV\s+\d+\b", body, re.IGNORECASE | re.MULTILINE))
        if stoic_count < 2:
            violations.append(
                {
                    "source": source,
                    "block": block,
                    "stoic_count": stoic_count,
                    "conv_count": conv_count,
                    "message": "RStoic SERIES=YES requires at least two STOIC reactions in the same block.",
                }
            )
    return violations


def scan_path(path: Path) -> list[dict[str, Any]]:
    if path.is_dir():
        violations: list[dict[str, Any]] = []
        for child in sorted(path.rglob("*.inp")):
            violations.extend(scan_path(child))
        return violations
    text = path.read_text(encoding="utf-8", errors="ignore")
    return scan_text(text, str(path))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan Aspen .inp files for RStoic SERIES=YES blocks with fewer than two reactions."
    )
    parser.add_argument("paths", nargs="+", help="Aspen .inp file(s) or directories to scan")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    violations: list[dict[str, Any]] = []
    missing: list[str] = []
    for raw in args.paths:
        path = Path(raw)
        if not path.exists():
            missing.append(raw)
            continue
        violations.extend(scan_path(path))

    result = {
        "checked": args.paths,
        "missing": missing,
        "violation_count": len(violations),
        "violations": violations,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 2 if missing or violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
