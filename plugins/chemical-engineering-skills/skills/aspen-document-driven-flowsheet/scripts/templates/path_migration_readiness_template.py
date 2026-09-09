#!/usr/bin/env python3
"""Template: package/path migration readiness gate.

This script performs the deterministic parts: copy, hash/size inventory, and
absolute-path scan. Project adapters must perform Aspen clean reopen/start-run
from the migrated path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


ABS_PATH_PATTERN = re.compile(r"[A-Za-z]:\\[^\s\"'<>|]+")


@dataclass
class FileRecord:
    relative_path: str
    size: int
    sha256: str


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def iter_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    return sorted(path for path in root.rglob("*") if path.is_file())


def inventory(root: Path) -> list[FileRecord]:
    base = root.parent if root.is_file() else root
    records = []
    for path in iter_files(root):
        records.append(FileRecord(path.relative_to(base).as_posix(), path.stat().st_size, sha256(path)))
    return records


def copy_to_migration_path(source: Path, migration_dir: Path) -> Path:
    migration_dir.mkdir(parents=True, exist_ok=True)
    target = migration_dir / source.name
    if target.exists():
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
    if source.is_dir():
        shutil.copytree(source, target)
    else:
        shutil.copy2(source, target)
    return target


def scan_absolute_paths(root: Path, old_root: str | None) -> list[dict[str, object]]:
    hits: list[dict[str, object]] = []
    for path in iter_files(root):
        if path.suffix.lower() in {".bkp", ".apw", ".apwz", ".dll", ".exe", ".zip"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            found = ABS_PATH_PATTERN.findall(line)
            if old_root:
                found.extend([old_root] if old_root in line else [])
            if found:
                hits.append({"file": str(path), "line": line_no, "paths": sorted(set(found)), "text": line.strip()[:240]})
    return hits


def perform_aspen_migrated_probe(migrated_target: Path, out_dir: Path) -> dict[str, object]:
    """Project edit point.

    Implement clean-session Aspen reopen, Required Input check, no-manual-input
    start-run, and same-version export from migrated_target.
    """
    return {
        "implemented": False,
        "clean_session_reopen": "not_checked",
        "required_input_complete": "not_checked",
        "run_can_start_without_manual_input": "not_checked",
        "same_version_export_after_migration": "not_checked",
        "control_panel_or_history": "not_checked",
    }


def write_reports(out_dir: Path, payload: dict[str, object]) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "path_migration_readiness.json"
    md_path = out_dir / "path_migration_readiness.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Path Migration Readiness",
        "",
        f"- decision: `{payload['decision']}`",
        f"- source: `{payload['source']}`",
        f"- migrated_target: `{payload['migrated_target']}`",
        f"- absolute_path_hits: `{len(payload['absolute_path_hits'])}`",
        f"- aspen_probe_implemented: `{payload['aspen_probe'].get('implemented')}`",
        "",
        "Static copy/hash and path scan do not replace migrated Aspen reopen/start-run evidence.",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Copy package to migration path and record portability evidence.")
    parser.add_argument("--source", required=True, help="Final package directory or case file.")
    parser.add_argument("--migration-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--old-root", help="Old workspace path that must not appear in migrated text files.")
    parser.add_argument("--skip-copy", action="store_true")
    args = parser.parse_args()

    source = Path(args.source).resolve()
    migration_dir = Path(args.migration_dir).resolve()
    migrated_target = migration_dir / source.name if args.skip_copy else copy_to_migration_path(source, migration_dir)
    source_records = [asdict(item) for item in inventory(source)]
    migrated_records = [asdict(item) for item in inventory(migrated_target)]
    abs_hits = scan_absolute_paths(migrated_target, args.old_root)
    aspen_probe = perform_aspen_migrated_probe(migrated_target, Path(args.out_dir))
    probe_ready = (
        aspen_probe.get("clean_session_reopen") == "yes"
        and aspen_probe.get("required_input_complete") == "yes"
        and aspen_probe.get("run_can_start_without_manual_input") == "yes"
        and aspen_probe.get("same_version_export_after_migration") == "yes"
    )
    decision = "migration-ready" if not abs_hits and probe_ready else "blocked-portability"
    payload = {
        "created": datetime.now().isoformat(timespec="seconds"),
        "source": str(source),
        "migration_dir": str(migration_dir),
        "migrated_target": str(migrated_target),
        "source_inventory": source_records,
        "migrated_inventory": migrated_records,
        "absolute_path_hits": abs_hits,
        "aspen_probe": aspen_probe,
        "decision": decision,
    }
    json_path, md_path = write_reports(Path(args.out_dir), payload)
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0 if decision == "migration-ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
