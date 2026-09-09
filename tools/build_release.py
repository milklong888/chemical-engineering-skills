#!/usr/bin/env python3
"""Explicit-source stage -> actual-file manifest/SHA -> ZIP; never uploads."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import uuid
import zipfile

TASK_ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("publication_verifier", TASK_ROOT / "tools/verify_release.py")
if spec is None or spec.loader is None:
    raise RuntimeError("Publication verifier is missing")
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


def load_sources(path: Path) -> dict:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != "chemical-publication-sources-v1" or not isinstance(doc.get("files"), list):
        raise v.ReleaseError("Unsupported explicit-source manifest")
    return doc


def reviewed_synthetic_entry(entry: dict, output: bytes) -> list:
    if entry.get("publication_scope") != "synthetic_template":
        return []
    result = [{"path": entry["destination"], "sha256": v.sha256(output), "scope_declaration": entry.get("scope_declaration", "")}]
    v.synthetic_policy(result)
    return result


def source_synthetic_allowlist(path: Path) -> list:
    approved = []
    for entry in load_sources(path)["files"]:
        if entry.get("publication_scope") != "synthetic_template":
            continue
        source = Path(entry["source"])
        v.reject_links(source)
        data = source.read_bytes()
        if v.sha256(data) != entry["source_sha256"].lower():
            raise v.ReleaseError("Synthetic source identity changed before seal")
        text = data.decode("utf-8")
        for replacement in entry.get("replacements", []):
            old, new, count = replacement["old"], replacement["new"], replacement["expected_count"]
            if not old or type(count) is not int or count < 1 or text.count(old) != count:
                raise v.ReleaseError("Synthetic replacement contract mismatch")
            text = text.replace(old, new)
        approved.extend(reviewed_synthetic_entry(entry, text.encode("utf-8")))
    v.synthetic_policy(approved)
    return approved


def sealed_release_metadata(repository: Path) -> tuple[list, list]:
    """Reuse only scope records already bound to the downloaded release."""
    manifest_path = v.safe_target(repository.absolute(), v.MANIFEST)
    if not manifest_path.exists():
        return [], []
    data = manifest_path.read_bytes()
    v.public_text(v.MANIFEST, data)
    manifest = json.loads(data)
    if not isinstance(manifest, dict) or manifest.get("schema") != "chemical-public-release-v1":
        raise v.ReleaseError("Cannot reuse scope from an unsupported release manifest")
    dependencies = manifest.get("external_dependencies", [])
    templates = manifest.get("synthetic_templates", [])
    if not isinstance(dependencies, list) or not isinstance(templates, list):
        raise v.ReleaseError("Sealed dependency/template records must be lists")
    policy = v.synthetic_policy(templates)
    recorded_files = {entry["path"]: entry["sha256"] for entry in manifest.get("files", [])}
    for relative, digest in policy.items():
        if recorded_files.get(relative) != digest:
            raise v.ReleaseError("Synthetic scope is not bound to the existing release file list")
        path = v.safe_target(repository.absolute(), relative)
        if not path.is_file() or v.sha256(path.read_bytes()) != digest:
            raise v.ReleaseError("Synthetic INP changed since the existing release was sealed")
    return dependencies, templates


def stage(sources_path: Path, repository: Path, log_dir: Path) -> dict:
    repository, log_dir = repository.absolute(), log_dir.absolute()
    v.reject_links(repository)
    v.reject_links(log_dir)
    repository, log_dir = repository.resolve(), log_dir.resolve()
    if v.below(log_dir, repository) or v.below(repository, log_dir):
        raise v.ReleaseError("Private mapping logs must be outside the publication repository")
    sources = load_sources(sources_path)
    planned, seen = [], set()
    for entry in sources["files"]:
        source = Path(entry["source"])
        if not source.is_absolute():
            raise v.ReleaseError("Sources must be explicit absolute paths")
        v.reject_links(source)
        if not source.is_file() or v.below(source.resolve(), repository):
            raise v.ReleaseError("Source must be a regular file outside publication repository")
        destination = v.relative_path(entry["destination"])
        if destination in {v.MANIFEST, v.CHECKSUMS}:
            raise v.ReleaseError("Seal-generated paths cannot be stage destinations")
        if destination.casefold() in seen:
            raise v.ReleaseError("Case-insensitive destination collision")
        seen.add(destination.casefold())
        data = source.read_bytes()
        expected = entry.get("source_sha256", "").lower()
        if not re.fullmatch(r"[0-9a-f]{64}", expected) or v.sha256(data) != expected:
            raise v.ReleaseError(f"Source identity mismatch: {destination}")
        text = data.decode("utf-8")
        replacement_log = []
        for replacement in entry.get("replacements", []):
            old, new, count = replacement["old"], replacement["new"], replacement["expected_count"]
            if not isinstance(old, str) or not old or not isinstance(new, str) or type(count) is not int or count < 1 or text.count(old) != count:
                raise v.ReleaseError(f"Replacement count/contract mismatch: {destination}")
            text = text.replace(old, new)
            replacement_log.append({"old": old, "new": new, "count": count})
        output = text.encode("utf-8")
        policy = v.synthetic_policy(reviewed_synthetic_entry(entry, output))
        v.public_text(destination, output, policy)
        target = v.safe_target(repository, destination)
        for parent in target.parents:
            if parent.exists() and not parent.is_dir():
                raise v.ReleaseError("Destination parent is a file")
        if target.exists() and (not target.is_file() or target.read_bytes() != output):
            raise v.ReleaseError(f"Refusing to overwrite another staged/generated file: {destination}")
        planned.append({"source": source, "destination": destination, "target": target, "data": output,
                        "source_sha256": expected, "output_sha256": v.sha256(output), "replacements": replacement_log})
    # No publication-tree mutation until the entire explicit source table passes.
    repository.parent.mkdir(parents=True, exist_ok=True)
    written = []
    with tempfile.TemporaryDirectory(prefix=".public-stage-", dir=repository.parent) as temporary:
        temporary_root = Path(temporary)
        for item in planned:
            tmp = v.safe_target(temporary_root, item["destination"])
            tmp.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_bytes(item["data"])
        # Catch source drift after staging, before committing any copied file.
        for item in planned:
            if v.sha256(item["source"].read_bytes()) != item["source_sha256"]:
                raise v.ReleaseError("Source changed during stage preflight")
        try:
            for item in planned:
                target = v.safe_target(repository, item["destination"])
                if target.exists():
                    if target.read_bytes() != item["data"]:
                        raise v.ReleaseError("Publication collision appeared during staging")
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as handle:
                    handle.write(v.safe_target(temporary_root, item["destination"]).read_bytes())
                written.append(target)
        except BaseException:
            for target in reversed(written):
                target.unlink()
            raise
    log_dir.mkdir(parents=True, exist_ok=True)
    log = {"schema": "private-publication-stage-log-v1", "source_manifest": sources_path.resolve().as_posix(),
           "source_manifest_sha256": v.sha256(sources_path.read_bytes()),
           "created_utc": datetime.now(timezone.utc).isoformat(),
           "files": [{k: (x.as_posix() if isinstance(x, Path) else x) for k, x in item.items() if k not in {"target", "data"}} for item in planned]}
    log_path = log_dir / ("stage-" + uuid.uuid4().hex[:16] + ".json")
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"staged_file_count": len(planned), "new_file_count": len(written), "mapping_log": str(log_path), "source_files_modified": False, "uploaded": False}


def seal(repository: Path, output_dir: Path, release_name: str, release_version: str, *, expected_skill_count: int = 19, external_dependencies: list | None = None, synthetic_templates: list | None = None) -> dict:
    repository, output_dir = repository.absolute(), output_dir.absolute()
    v.reject_links(repository)
    v.reject_links(output_dir)
    repository, output_dir = repository.resolve(), output_dir.resolve()
    if v.below(output_dir, repository) or v.below(repository, output_dir):
        raise v.ReleaseError("Archive output must be outside the repository, not its ancestor")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", release_name) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,39}", release_version):
        raise v.ReleaseError("Unsafe release label")
    name = release_name + "-" + release_version
    archive, sidecar = output_dir / (name + ".zip"), output_dir / (name + ".zip.sha256")
    if archive.exists() or sidecar.exists():
        raise v.ReleaseError("Existing archive/sidecar is not overwritten")
    manifest, checksums = v.make_manifest(repository, release_name=release_name, release_version=release_version,
                                           expected_skill_count=expected_skill_count, external_dependencies=external_dependencies, synthetic_templates=synthetic_templates)
    frozen = {p: b for p, b in v.inventory(repository).items() if p not in {v.MANIFEST, v.CHECKSUMS}}
    generated = {v.MANIFEST: manifest, v.CHECKSUMS: checksums}
    # Existing generated ledgers may be refreshed only through this explicit seal command.
    for relative, data in generated.items():
        v.safe_target(repository, relative).write_bytes(data)
    verified = v.verify(repository)
    actual = v.inventory(repository)
    if {p: b for p, b in actual.items() if p not in generated} != frozen:
        raise v.ReleaseError("Repository changed during sealing")
    output_dir.mkdir(parents=True, exist_ok=True)
    descriptor, tempname = tempfile.mkstemp(prefix=".release-", suffix=".zip", dir=output_dir)
    os.close(descriptor)
    try:
        with zipfile.ZipFile(tempname, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
            for relative, data in actual.items():
                info = zipfile.ZipInfo(name + "/" + relative, date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                bundle.writestr(info, data)
        with zipfile.ZipFile(tempname) as bundle:
            if bundle.testzip() is not None or {p[len(name) + 1:]: bundle.read(p) for p in bundle.namelist()} != actual:
                raise v.ReleaseError("ZIP readback differs from frozen release")
        with archive.open("xb") as handle:
            handle.write(Path(tempname).read_bytes())
        digest = v.sha256(archive.read_bytes())
        with sidecar.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(digest + "  " + archive.name + "\n")
    finally:
        Path(tempname).unlink(missing_ok=True)
    return {"archive": str(archive), "sha256": digest, "sidecar": str(sidecar), "file_count": verified["file_count"], "skill_count": verified["skill_count"], "uploaded": False, "commercial_software_verified": False}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    staging = commands.add_parser("stage")
    staging.add_argument("--sources", type=Path, required=True)
    staging.add_argument("--repository", type=Path, default=TASK_ROOT)
    staging.add_argument("--log-dir", type=Path, required=True, help="Private mapping logs outside the publication repository")
    sealing = commands.add_parser("seal")
    sealing.add_argument("--repository", type=Path, default=TASK_ROOT)
    sealing.add_argument("--output-dir", type=Path, required=True)
    sealing.add_argument("--release-name", required=True)
    sealing.add_argument("--release-version", required=True)
    sealing.add_argument("--expected-skill-count", type=int, default=19)
    sealing.add_argument("--sources", type=Path, help="Explicit reviewed source manifest; otherwise reuse hash-bound scope from the existing release manifest")
    args = parser.parse_args()
    try:
        if args.command == "stage":
            result = stage(args.sources, args.repository, args.log_dir)
        else:
            if args.sources:
                dependencies = load_sources(args.sources).get("external_dependencies", [])
                templates = source_synthetic_allowlist(args.sources)
            else:
                dependencies, templates = sealed_release_metadata(args.repository)
            result = seal(args.repository, args.output_dir, args.release_name, args.release_version, expected_skill_count=args.expected_skill_count, external_dependencies=dependencies, synthetic_templates=templates)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (v.ReleaseError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "refused", "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
