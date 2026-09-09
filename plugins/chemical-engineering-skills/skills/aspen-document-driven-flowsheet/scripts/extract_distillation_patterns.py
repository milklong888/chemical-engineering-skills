#!/usr/bin/env python
"""Summarize distillation blocks and starts from Aspen .apwz/.bkp files."""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path


BLOCK_TYPES = (
    "RADFRAC",
    "BATCHSEP",
    "MULTIFRAC",
    "DECANTER",
    "FLASH2",
    "FLASH3",
    "COMPR",
    "PUMP",
    "HEATER",
    "HEATX",
    "FSPLIT",
    "MIXER",
    "VALVE",
)

FIELD_PATTERNS = {
    "NSTAGE": r"NSTAGE\s*=\s*([^\s<]+)",
    "COND": r"CONDENSER\s*=\s*([^\s<]+)",
    "VALID": r"VALIDPHASES\s*=\s*([^\s<]+)",
    "FEED": r"FEED-SID\s*=\s*([^\s<]+)",
    "FSTAGE": r"FEED-STAGE\s*=\s*([^\s<]+)",
    "PROD": r"PROD-STREAM\s*=\s*([^\s<]+)",
    "PRES1": r"PRES1\s*=\s*([^\s<]+)",
    "COND-PRES": r"COND-PRES\s*=\s*([^\s<]+)",
    "RR": r"(?:MOLE-RR|MASS-RR|REFLUXRATIO1)\s*=\s*([^\s<]+)",
    "D": r"(?:MOLE-D|MASS-D|DIST-RATE|D:F)\s*=\s*([^\s<]+)",
    "ALG": r"ALGORITHM\s*=\s*([^\s<]+)",
    "INIT": r"INIT-OPTION\s*=\s*([^\s<]+)",
    "CONV": r"CONV-METH\s*=\s*([^\s<]+)",
    "PRES": r"PARAM\s+PRES\s*=\s*([^\s<]+)",
    "PRATIO": r"PRATIO\s*=\s*([^\s<]+)",
}


def decode_bytes(data: bytes) -> str:
    for encoding in ("utf-8", "gb18030", "cp936", "latin1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin1", "ignore")


def read_case(path: Path) -> str:
    if path.suffix.lower() == ".apwz":
        with zipfile.ZipFile(path) as zf:
            parts = []
            for entry in zf.infolist():
                if entry.filename.lower().endswith(".bkp"):
                    parts.append(decode_bytes(zf.read(entry)))
            return "\n".join(parts)
    return decode_bytes(path.read_bytes())


def compact_text(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\\\s+\\", "\n", text)
    text = re.sub(r"\\\s+", "\n", text)
    text = re.sub(r"\s+\?\s+BLOCK\s+", r"\n? BLOCK ", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text)


def block_counts(text: str) -> Counter[str]:
    seen: set[tuple[str, str]] = set()
    counts: Counter[str] = Counter()
    for match in re.finditer(
        r"BLKTYPE\s*=\s*([A-Z0-9_-]+)|BLOCK\s+BLKID\s*=\s*([A-Z0-9_-]+)\s+BLKTYPE\s*=\s*([A-Z0-9_-]+)",
        text,
        re.IGNORECASE,
    ):
        block_type = (match.group(1) or match.group(3)).upper()
        block_id = match.group(2) or f"unknown-{len(seen)}"
        key = (block_type, block_id.upper())
        if key not in seen:
            seen.add(key)
            counts[block_type] += 1
    for match in re.finditer(
        r"BLOCK\s+(" + "|".join(BLOCK_TYPES) + r")\s+([A-Z0-9_-]+)",
        text,
        re.IGNORECASE,
    ):
        block_type = match.group(1).upper()
        block_id = match.group(2).upper()
        key = (block_type, block_id)
        if key not in seen:
            seen.add(key)
            counts[block_type] += 1
    return counts


def first_values(pattern: str, text: str, limit: int = 3) -> list[str]:
    values: list[str] = []
    for match in re.finditer(pattern, text, re.IGNORECASE):
        value = match.group(1).strip(' "')
        if value and value not in values:
            values.append(value)
        if len(values) >= limit:
            break
    return values


def block_signatures(text: str, limit: int) -> list[dict[str, object]]:
    signatures: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    block_regex = re.compile(
        r"\bBLOCK\s+(" + "|".join(BLOCK_TYPES) + r")\s+([A-Z0-9_-]+)\s+\?",
        re.IGNORECASE,
    )
    matches = list(block_regex.finditer(text))
    for index, match in enumerate(matches):
        block_type = match.group(1).upper()
        block_id = match.group(2)
        key = (block_type, block_id.upper())
        if key in seen:
            continue
        seen.add(key)
        end = matches[index + 1].start() if index + 1 < len(matches) else match.start() + 1800
        snippet = text[match.start() : end]
        fields = {}
        for name, pattern in FIELD_PATTERNS.items():
            values = first_values(pattern, snippet)
            if values:
                fields[name] = values
        signatures.append({"type": block_type, "id": block_id, "fields": fields})
        if len(signatures) >= limit:
            break
    if signatures:
        return signatures
    fallback_regex = re.compile(
        r"BLOCK\s+BLKID\s*=\s*([A-Z0-9_-]+)\s+BLKTYPE\s*=\s*("
        + "|".join(BLOCK_TYPES)
        + r")",
        re.IGNORECASE,
    )
    for match in fallback_regex.finditer(text):
        block_id = match.group(1)
        block_type = match.group(2).upper()
        key = (block_type, block_id.upper())
        if key in seen:
            continue
        seen.add(key)
        signatures.append({"type": block_type, "id": block_id, "fields": {}})
        if len(signatures) >= limit:
            break
    return signatures


def property_methods(text: str) -> list[str]:
    methods: list[str] = []
    for pattern in (
        r"GBASEOPSET\s*=\s*\"?([A-Z0-9_-]+)",
        r"GOPSETNAME\s*=\s*\"?([A-Z0-9_-]+)",
        r'"OPTION-SETS"\s+"?([A-Z0-9_-]+)',
    ):
        for match in re.finditer(pattern, text, re.IGNORECASE):
            method = match.group(1).strip('"').upper()
            if method and method not in methods:
                methods.append(method)
            if len(methods) >= 5:
                return methods
    return methods


def summarize(root: Path, per_file_limit: int) -> dict[str, object]:
    cases = []
    category_counts: dict[str, int] = defaultdict(int)
    category_blocks: dict[str, Counter[str]] = defaultdict(Counter)
    for path in sorted(root.rglob("*")):
        if path.suffix.lower() not in {".apwz", ".bkp"}:
            continue
        try:
            text = compact_text(read_case(path))
        except Exception as exc:  # pragma: no cover - diagnostic output
            cases.append({"path": str(path), "error": str(exc)})
            continue
        rel = path.relative_to(root)
        category = rel.parts[0] if rel.parts else "."
        counts = block_counts(text)
        category_counts[category] += 1
        category_blocks[category].update(counts)
        cases.append(
            {
                "path": str(rel),
                "category": category,
                "blocks": {key: counts[key] for key in sorted(counts)},
                "property_methods": property_methods(text),
                "signatures": block_signatures(text, per_file_limit),
            }
        )
    return {
        "root": str(root),
        "case_count": len([case for case in cases if "error" not in case]),
        "category_counts": dict(sorted(category_counts.items())),
        "category_blocks": {
            key: dict(sorted(counter.items())) for key, counter in sorted(category_blocks.items())
        },
        "cases": cases,
    }


def print_markdown(summary: dict[str, object], max_cases: int | None = None) -> None:
    print(f"# Distillation Pattern Summary\n")
    print(f"Root: `{summary['root']}`")
    print(f"Cases parsed: {summary['case_count']}\n")
    print("## Categories\n")
    category_counts = summary["category_counts"]
    category_blocks = summary["category_blocks"]
    for category, count in category_counts.items():
        blocks = category_blocks.get(category, {})
        interesting = ", ".join(
            f"{name}={blocks[name]}"
            for name in BLOCK_TYPES
            if name in blocks and blocks[name]
        )
        print(f"- {category}: {count} files; {interesting}")
    print("\n## Representative Files\n")
    printed = 0
    for case in summary["cases"]:
        if max_cases is not None and printed >= max_cases:
            remaining = len(summary["cases"]) - printed
            if remaining > 0:
                print(f"\n... {remaining} more case records omitted by --max-cases")
            break
        if "error" in case:
            print(f"- {case['path']}: ERROR {case['error']}")
            printed += 1
            continue
        signatures = case.get("signatures") or []
        if not signatures:
            continue
        print(f"\n### {case['path']}")
        printed += 1
        methods = ", ".join(case.get("property_methods") or [])
        if methods:
            print(f"Property starts: {methods}")
        for sig in signatures[:4]:
            fields = sig.get("fields") or {}
            compact_fields = "; ".join(
                f"{name}={'/'.join(values)}" for name, values in fields.items()
            )
            print(f"- {sig['type']} {sig['id']}: {compact_fields}")


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", help="Directory containing Aspen .apwz/.bkp files")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown")
    parser.add_argument("--max-cases", type=int, help="Limit representative case records in Markdown output")
    parser.add_argument("--per-file-limit", type=int, default=12)
    args = parser.parse_args(argv)

    root = Path(args.root).expanduser().resolve()
    if not root.exists():
        parser.error(f"root does not exist: {root}")
    summary = summarize(root, args.per_file_limit)
    try:
        if args.json:
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        else:
            print_markdown(summary, args.max_cases)
    except BrokenPipeError:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
