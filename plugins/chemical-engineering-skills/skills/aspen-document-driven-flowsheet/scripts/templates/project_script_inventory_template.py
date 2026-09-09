#!/usr/bin/env python3
"""Template: crawl project folders and summarize reusable script families.

Use this before promoting scripts into a skill. It inventories names, prefixes,
repeated basenames, and content keywords without importing project code.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


PREFIXES = [
    "build",
    "run",
    "probe",
    "audit",
    "verify",
    "validate",
    "generate",
    "summarize",
    "write",
    "repair",
    "inspect",
    "merge",
    "package",
    "scale",
    "create",
    "extract",
    "derive",
    "compute",
    "update",
    "convert",
    "make",
    "scan",
    "watchdog",
]

KEYWORDS = {
    "aspen_com_tree_run_export": re.compile(r"win32com|Apwn\.Document|Engine\.Run2|InitFromArchive|Tree\.FindNode", re.I),
    "control_panel_history": re.compile(r"Control Panel|ControlPanel|OnControlPanelMessage|BLKMSG|RunStatus", re.I),
    "required_input_open_readiness": re.compile(r"Required Input|required input|clean session|reopen|manual input", re.I),
    "watchdog_lock_timeout": re.compile(r"watchdog|global.*lock|timeout|Stop-Process|taskkill|psutil", re.I),
    "candidate_matrix_sweep": re.compile(r"matrix|sweep|candidate|grid|bounds|optimization", re.I),
    "audit_gate_status": re.compile(r"audit|gate|status|summary|json|csv", re.I),
    "kinetics_unit_ledger": re.compile(r"kinetic|Arrhenius|POWERLAW|LHHW|unit conversion|conversion ledger", re.I),
    "package_delivery_manifest": re.compile(r"package|delivery|portable|zip|manifest", re.I),
}


@dataclass
class ScriptItem:
    path: str
    top_folder: str
    stem: str
    suffix: str
    prefix: str
    keyword_tags: list[str]


def should_skip(path: Path, exclude_parts: set[str]) -> bool:
    parts = set(path.parts)
    return bool(parts & exclude_parts)


def classify_prefix(stem: str) -> str:
    for prefix in PREFIXES:
        if stem.startswith(prefix):
            return prefix
    return "other"


def keyword_tags(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    return [name for name, pattern in KEYWORDS.items() if pattern.search(text)]


def collect(root: Path, suffixes: set[str], exclude_parts: set[str]) -> list[ScriptItem]:
    items: list[ScriptItem] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in suffixes:
            continue
        if should_skip(path, exclude_parts):
            continue
        rel = path.relative_to(root)
        top = rel.parts[0] if len(rel.parts) > 1 else "<root>"
        stem = path.stem
        items.append(
            ScriptItem(
                path=rel.as_posix(),
                top_folder=top,
                stem=stem,
                suffix=path.suffix.lower(),
                prefix=classify_prefix(stem),
                keyword_tags=keyword_tags(path),
            )
        )
    return items


def top_counts(counter: Counter[str], limit: int) -> list[dict[str, object]]:
    return [{"name": name, "count": count} for name, count in counter.most_common(limit)]


def write_reports(root: Path, out_dir: Path, items: list[ScriptItem], limit: int) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    by_top = Counter(item.top_folder for item in items)
    by_prefix = Counter(item.prefix for item in items)
    by_suffix = Counter(item.suffix for item in items)
    by_keyword: Counter[str] = Counter(tag for item in items for tag in item.keyword_tags)
    by_stem: defaultdict[str, list[str]] = defaultdict(list)
    for item in items:
        by_stem[item.stem].append(item.path)

    repeated = [
        {"stem": stem, "count": len(paths), "examples": paths[:8]}
        for stem, paths in sorted(by_stem.items(), key=lambda pair: len(pair[1]), reverse=True)
        if len(paths) > 1
    ][:limit]

    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "root": str(root),
        "total_scripts": len(items),
        "top_folders": top_counts(by_top, limit),
        "prefix_counts": top_counts(by_prefix, limit),
        "suffix_counts": top_counts(by_suffix, limit),
        "keyword_counts": top_counts(by_keyword, limit),
        "repeated_basenames": repeated,
        "promotion_warning": "Inventory is discovery only; inspect and parameterize before promoting any script.",
    }

    json_path = out_dir / "project_script_inventory.json"
    md_path = out_dir / "project_script_inventory.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Project Script Inventory",
        "",
        f"- root: `{root}`",
        f"- total_scripts: `{len(items)}`",
        "- warning: inventory is discovery only; no script is reusable until inspected and parameterized.",
        "",
        "## Top Folders",
        "",
    ]
    lines.extend(f"- `{row['name']}`: {row['count']}" for row in payload["top_folders"])
    lines.extend(["", "## Prefix Counts", ""])
    lines.extend(f"- `{row['name']}`: {row['count']}" for row in payload["prefix_counts"])
    lines.extend(["", "## Keyword Counts", ""])
    lines.extend(f"- `{row['name']}`: {row['count']}" for row in payload["keyword_counts"])
    lines.extend(["", "## Repeated Basenames", ""])
    for row in repeated:
        lines.append(f"- `{row['stem']}`: {row['count']} examples; first: `{row['examples'][0]}`")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory project script families for reuse review.")
    parser.add_argument("--root", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--suffix", action="append", default=[".py", ".ps1", ".bat", ".cmd"])
    parser.add_argument("--exclude-part", action="append", default=[".git", "__pycache__", "node_modules"])
    parser.add_argument("--limit", type=int, default=30)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    items = collect(root, {item.lower() for item in args.suffix}, set(args.exclude_part))
    json_path, md_path = write_reports(root, Path(args.out_dir), items, args.limit)
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
