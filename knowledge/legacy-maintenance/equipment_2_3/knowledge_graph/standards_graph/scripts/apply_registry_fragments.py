#!/usr/bin/env python3
"""Atomically merge reviewed registry fragments into standards registries.

Default behavior is insert-only. Existing keys may be replaced only when an
exact ``registry.csv:key`` token is supplied with ``--replace-key``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path


REGISTRY_KEYS = {
    "dataset_registry.csv": "dataset_id",
    "table_promotion_rules.csv": "rule_id",
    "figure_dataset_registry.csv": "dataset_id",
    "figure_terminal_audit_registry.csv": "source_id",
}


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest().upper()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def validate_unique(rows: list[dict[str, str]], key: str, label: str) -> None:
    values = [str(row.get(key) or "") for row in rows]
    if not values or any(not value for value in values) or len(values) != len(set(values)):
        raise ValueError(f"{label}: empty or duplicated {key}")


def collect_fragments(fragment_dirs: list[Path], registry_name: str) -> list[dict[str, str]]:
    fragment_name = registry_name.replace(".csv", ".fragment.csv")
    rows: list[dict[str, str]] = []
    for root in fragment_dirs:
        path = root / fragment_name
        if path.is_file():
            _, part = read_csv(path)
            rows.extend(part)
    return rows


def merge_rows(
    current: list[dict[str, str]], incoming: list[dict[str, str]], key: str,
    replace_keys: set[str], label: str,
) -> tuple[list[dict[str, str]], list[str], list[str]]:
    validate_unique(current, key, f"{label} current")
    if incoming:
        validate_unique(incoming, key, f"{label} fragments")
    by_key = {row[key]: dict(row) for row in current}
    added: list[str] = []
    replaced: list[str] = []
    for row in incoming:
        value = row[key]
        if value in by_key:
            if value not in replace_keys:
                raise ValueError(f"{label}: existing key requires explicit replacement: {value}")
            by_key[value] = dict(row)
            replaced.append(value)
        else:
            by_key[value] = dict(row)
            added.append(value)
    ordered = [by_key[row[key]] for row in current]
    ordered.extend(by_key[value] for value in added)
    validate_unique(ordered, key, f"{label} merged")
    return ordered, added, replaced


def parse_replace(tokens: list[str]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for token in tokens:
        if ":" not in token:
            raise ValueError(f"invalid --replace-key token: {token}")
        registry, value = token.split(":", 1)
        if registry not in REGISTRY_KEYS or not value:
            raise ValueError(f"invalid --replace-key token: {token}")
        result.setdefault(registry, set()).add(value)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry-dir", type=Path, required=True)
    parser.add_argument("--fragment-dir", type=Path, action="append", required=True)
    parser.add_argument("--backup-dir", type=Path, required=True)
    parser.add_argument("--replace-key", action="append", default=[])
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    registry_dir = args.registry_dir.resolve()
    fragment_dirs = [path.resolve() for path in args.fragment_dir]
    backup_dir = args.backup_dir.resolve()
    replacements = parse_replace(args.replace_key)

    plans: list[dict] = []
    staged: list[tuple[Path, Path]] = []
    for registry_name, key in REGISTRY_KEYS.items():
        target = registry_dir / registry_name
        if not target.is_file():
            raise FileNotFoundError(target)
        fields, current = read_csv(target)
        incoming = collect_fragments(fragment_dirs, registry_name)
        if not incoming:
            continue
        fragment_fields = set(incoming[0])
        if fragment_fields != set(fields):
            raise ValueError(f"{registry_name}: fragment header mismatch")
        merged, added, replaced = merge_rows(
            current, incoming, key, replacements.get(registry_name, set()), registry_name
        )
        fd, temp_name = tempfile.mkstemp(prefix=registry_name + ".", suffix=".tmp", dir=registry_dir)
        os.close(fd)
        temp_path = Path(temp_name)
        write_csv(temp_path, fields, merged)
        staged.append((temp_path, target))
        plans.append({
            "registry": registry_name,
            "key": key,
            "before_count": len(current),
            "after_count": len(merged),
            "added_keys": added,
            "replaced_keys": replaced,
            "before_sha256": sha256_path(target),
            "staged_sha256": sha256_path(temp_path),
        })

    if not plans:
        raise ValueError("no registry fragments found")
    result = {"status": "DRY_RUN", "registry_dir": str(registry_dir), "plans": plans}
    if not args.apply:
        for temp_path, _ in staged:
            temp_path.unlink(missing_ok=True)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if backup_dir.exists() and any(backup_dir.iterdir()):
        raise ValueError(f"backup directory is not empty: {backup_dir}")
    backup_dir.mkdir(parents=True, exist_ok=True)
    for plan in plans:
        target = registry_dir / plan["registry"]
        shutil.copy2(target, backup_dir / target.name)
    try:
        for temp_path, target in staged:
            os.replace(temp_path, target)
    except Exception:
        for plan in plans:
            backup = backup_dir / plan["registry"]
            if backup.is_file():
                shutil.copy2(backup, registry_dir / plan["registry"])
        raise
    for plan in plans:
        target = registry_dir / plan["registry"]
        plan["after_sha256"] = sha256_path(target)
        if plan["after_sha256"] != plan["staged_sha256"]:
            raise RuntimeError(f"post-write hash mismatch: {target}")
    result["status"] = "APPLIED"
    result["backup_dir"] = str(backup_dir)
    manifest_path = backup_dir / "registry_merge_manifest.json"
    manifest_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
