#!/usr/bin/env python3
"""Safely merge a standards ZIP snapshot into the workspace source directory.

The script never overwrites a different existing file.  Every ZIP member is
hashed and recorded so later page/chunk/table evidence can point back to an
immutable source snapshot.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


def sha256_path(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(chunk_size):
            digest.update(block)
    return digest.hexdigest().upper()


def sha256_member(archive: zipfile.ZipFile, info: zipfile.ZipInfo) -> str:
    digest = hashlib.sha256()
    with archive.open(info, "r") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest().upper()


def safe_relative_path(member_name: str, strip_prefix: str | None) -> Path:
    normalized = member_name.replace("\\", "/")
    pure = PurePosixPath(normalized)
    parts = list(pure.parts)
    if strip_prefix and parts and parts[0] == strip_prefix:
        parts = parts[1:]
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"unsafe archive path: {member_name!r}")
    if pure.is_absolute() or ":" in parts[0]:
        raise ValueError(f"absolute archive path: {member_name!r}")
    return Path(*parts)


def common_top_level(infos: list[zipfile.ZipInfo]) -> str | None:
    roots: set[str] = set()
    for info in infos:
        parts = PurePosixPath(info.filename.replace("\\", "/")).parts
        if not parts:
            continue
        roots.add(parts[0])
    return next(iter(roots)) if len(roots) == 1 else None


def write_outputs(records: list[dict], metadata: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "source_snapshot_manifest.json"
    csv_path = output_dir / "source_snapshot_manifest.csv"
    payload = {"metadata": metadata, "files": records}
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    fieldnames = [
        "entry_path",
        "relative_path",
        "target_path",
        "size_bytes",
        "sha256",
        "status",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows({key: row.get(key, "") for key in fieldnames} for row in records)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("zip_path", type=Path)
    parser.add_argument("target_root", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()

    zip_path = args.zip_path.resolve()
    target_root = args.target_root.resolve()
    output_dir = args.output_dir.resolve()
    if not zip_path.is_file():
        raise FileNotFoundError(zip_path)
    target_root.mkdir(parents=True, exist_ok=True)

    zip_hash = sha256_path(zip_path)
    records: list[dict] = []
    with zipfile.ZipFile(zip_path) as archive:
        infos = [
            info
            for info in archive.infolist()
            if not info.is_dir() and info.filename.lower().endswith(".pdf")
        ]
        prefix = common_top_level(infos)
        for info in sorted(infos, key=lambda item: item.filename.casefold()):
            relative = safe_relative_path(info.filename, prefix)
            target = (target_root / relative).resolve()
            if target_root != target and target_root not in target.parents:
                raise ValueError(f"archive escape attempt: {info.filename!r}")
            source_hash = sha256_member(archive, info)
            if target.exists():
                current_hash = sha256_path(target)
                status = (
                    "identical_existing"
                    if current_hash == source_hash
                    else "conflict_existing_not_overwritten"
                )
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                fd, temp_name = tempfile.mkstemp(prefix=".ingest_", dir=target.parent)
                os.close(fd)
                temp_path = Path(temp_name)
                try:
                    with archive.open(info, "r") as source, temp_path.open("wb") as dest:
                        shutil.copyfileobj(source, dest, length=1024 * 1024)
                    if sha256_path(temp_path) != source_hash:
                        raise IOError(f"hash mismatch after extraction: {info.filename}")
                    os.replace(temp_path, target)
                    status = "extracted_new"
                finally:
                    temp_path.unlink(missing_ok=True)
            records.append(
                {
                    "entry_path": info.filename,
                    "relative_path": relative.as_posix(),
                    "target_path": str(target),
                    "size_bytes": info.file_size,
                    "sha256": source_hash,
                    "status": status,
                }
            )

    metadata = {
        "schema": "design-standards-source-snapshot-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "zip_path": str(zip_path),
        "zip_size_bytes": zip_path.stat().st_size,
        "zip_sha256": zip_hash,
        "target_root": str(target_root),
        "pdf_count": len(records),
        "status_counts": {
            status: sum(row["status"] == status for row in records)
            for status in sorted({row["status"] for row in records})
        },
    }
    write_outputs(records, metadata, output_dir)
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    if any(row["status"].startswith("conflict_") for row in records):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
