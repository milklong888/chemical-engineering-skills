#!/usr/bin/env python3
"""Install only manifest-owned files; no software launch or broad path rewrites."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
import uuid

from verify_release import ReleaseError, SKILLS_PREFIX, below, reject_links, safe_target, sha256, verify


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".chemical-install-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def discovery_tree(path: Path) -> bool:
    parts = [p.casefold() for p in path.parts]
    return any(parts[i] in {".agents", ".codex"} and parts[i + 1] == "skills" for i in range(len(parts) - 1))


def install(repository: Path, workspace_root: Path, skills_root: Path, *, replace: bool = False, backup_root: Path | None = None, dry_run: bool = False) -> dict:
    repository, workspace_root, skills_root = [p.expanduser().absolute() for p in (repository, workspace_root, skills_root)]
    for root in (repository, workspace_root, skills_root):
        reject_links(root)
    repository, workspace_root, skills_root = [p.resolve() for p in (repository, workspace_root, skills_root)]
    if below(workspace_root, repository) or below(skills_root, repository) or below(repository, workspace_root) or below(repository, skills_root):
        raise ReleaseError("Install roots must not overlap the release repository")
    if below(workspace_root, skills_root) or below(skills_root, workspace_root):
        raise ReleaseError("Workspace and skill roots must be disjoint")
    for root in (workspace_root, skills_root):
        if root.exists() and not root.is_dir():
            raise ReleaseError("Target root is not a directory")
    verified = verify(repository)
    planned, collisions, seen = [], [], set()
    tokens = {"{CHEM_WORKSPACE}": workspace_root.as_posix(), "{CHEM_SKILLS}": skills_root.as_posix()}
    for entry in verified["manifest"]["files"]:
        source_rel = entry["path"]
        if source_rel.startswith(SKILLS_PREFIX):
            kind, root, rel = "skills", skills_root, source_rel[len(SKILLS_PREFIX):]
        elif source_rel.startswith("workspace/"):
            kind, root, rel = "workspace", workspace_root, source_rel[len("workspace/"):]
        else:
            continue
        target = safe_target(root, rel)
        for parent in target.parents:
            if parent.exists() and not parent.is_dir():
                raise ReleaseError("A target parent is an existing file")
        if target.exists() and not target.is_file():
            raise ReleaseError("A target file is an existing directory")
        identity = str(target).casefold()
        if identity in seen:
            raise ReleaseError("Install destination collision")
        seen.add(identity)
        source = safe_target(repository, source_rel).read_bytes()
        if sha256(source) != entry["sha256"]:
            raise ReleaseError("Source changed during install preflight")
        text = source.decode("utf-8")
        for token, value in tokens.items():
            text = text.replace(token, value)
        output = text.encode("utf-8")
        old = target.read_bytes() if target.exists() else None
        item = {"kind": kind, "relative": rel, "target": target, "data": output, "old": old}
        planned.append(item)
        if old is not None and old != output:
            collisions.append(item)
    if collisions and not replace:
        raise ReleaseError("Existing files differ; preflight made no changes. Use --replace to back up exact conflicts: " + ", ".join(x["kind"] + "/" + x["relative"] for x in collisions))
    changes = [x for x in planned if x["old"] != x["data"]]
    result = {"status": "dry_run" if dry_run else "installed", "managed_file_count": len(planned), "changed_file_count": len(changes),
              "unchanged_file_count": len(planned) - len(changes), "conflict_count": len(collisions),
              "workspace_root": workspace_root.as_posix(), "skills_root": skills_root.as_posix(),
              "commercial_software_verified": False, "external_dependencies": verified["external_dependencies"]}
    backup = None
    if collisions:
        backup_base = backup_root.expanduser().absolute() if backup_root else workspace_root.parent / ".chemical-engineering-skills-backups"
        reject_links(backup_base)
        backup_base = backup_base.resolve()
        if any(below(backup_base, root) or below(root, backup_base) for root in (workspace_root, skills_root, repository)) or discovery_tree(backup_base):
            raise ReleaseError("Backup root must be outside workspace/repository and all skills discovery trees")
        backup = backup_base / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:12])
        result["backup_root"] = backup.as_posix()
    if dry_run:
        return result
    # Recheck every destination before the first mutation; do not scan/rewrite unrelated files.
    for item in planned:
        reject_links(item["target"])
        now = item["target"].read_bytes() if item["target"].exists() else None
        if now != item["old"]:
            raise ReleaseError("Target changed during preflight; no writes performed")
    if backup:
        backup.mkdir(parents=True, exist_ok=False)
        backup_entries = []
        for item in collisions:
            saved = safe_target(backup, item["kind"] + "/" + item["relative"])
            saved.parent.mkdir(parents=True, exist_ok=True)
            saved.write_bytes(item["old"])
            backup_entries.append({"target": item["target"].as_posix(), "backup": saved.relative_to(backup).as_posix(), "sha256": sha256(item["old"])})
        (backup / "BACKUP_MANIFEST.json").write_text(json.dumps({"files": backup_entries}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    written = []
    try:
        for item in changes:
            reject_links(item["target"])
            atomic_write(item["target"], item["data"])
            written.append(item)
        for item in planned:
            if item["target"].read_bytes() != item["data"]:
                raise ReleaseError("Installed readback mismatch")
    except BaseException:
        for item in reversed(written):
            if item["old"] is None:
                item["target"].unlink()
            else:
                atomic_write(item["target"], item["old"])
        raise
    return result


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("--skills-root", type=Path, default=Path.home() / ".agents" / "skills")
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--backup-root", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(install(args.repository, args.workspace_root, args.skills_root, replace=args.replace, backup_root=args.backup_root, dry_run=args.dry_run), ensure_ascii=False, indent=2))
        return 0
    except (ReleaseError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "refused", "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
