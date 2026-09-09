#!/usr/bin/env python3
"""Verify a text-only release. Integrity is not commercial-software validation."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys

MANIFEST = "RELEASE_MANIFEST.json"
CHECKSUMS = "SHA256SUMS.txt"
PLUGIN = "plugins/chemical-engineering-skills"
SKILLS_PREFIX = PLUGIN + "/skills/"
IGNORED_DIRS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
TEXT_SUFFIXES = {".md", ".py", ".ps1", ".cmd", ".bat", ".json", ".jsonl", ".yaml", ".yml", ".toml", ".txt", ".csv", ".tsv", ".html", ".css", ".js", ".mjs", ".xml", ".ini", ".cfg", ".rst"}
TEXT_NAMES = {"LICENSE", "NOTICE", ".gitignore", ".gitattributes"}
FORBIDDEN_PARTS = {"source_pages", "rendered_pages", "raw_l0", "rawl0", "prior_state", "source_snapshot", "node_modules", ".venv", ".env", "credentials", "error_memory_events"}
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{30,}\b"),
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"(?i)(?:api_key|access_token|password)\s*[:=]\s*[\"'][A-Za-z0-9_+/=-]{24,}[\"']"),
]
PRIVATE_PATH = re.compile(r"(?i)(?:[A-Z]:[/\\]+Users[/\\]+[^/\\\s\"'<>]+|/(?:home|Users)/[^/\s\"'<>]+)")


class ReleaseError(ValueError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def relative_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ReleaseError("Expected a nonempty portable relative path")
    p = PurePosixPath(value)
    if p.is_absolute() or any(x in {"", ".", ".."} for x in value.split("/")):
        raise ReleaseError(f"Unsafe relative path: {value}")
    if any(any(ord(c) < 32 or c in '<>"|?*' for c in part) or part.endswith((".", " ")) for part in p.parts):
        raise ReleaseError(f"Nonportable path: {value}")
    if any(re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?", part) for part in p.parts):
        raise ReleaseError(f"Reserved path: {value}")
    return p.as_posix()


def below(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def reject_links(path: Path) -> None:
    for part in [path, *path.parents]:
        if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
            raise ReleaseError(f"Symlink/junction not accepted: {part}")
        try:
            attributes = getattr(part.lstat(), "st_file_attributes", 0)
        except FileNotFoundError:
            continue
        if attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
            raise ReleaseError(f"Reparse point not accepted: {part}")


def safe_target(root: Path, relative: str) -> Path:
    root = root.absolute()
    reject_links(root)
    target = root.joinpath(*PurePosixPath(relative_path(relative)).parts)
    reject_links(target)
    if not below(target.resolve(), root.resolve()):
        raise ReleaseError("Resolved path escapes root")
    return target


def synthetic_policy(entries: list | None) -> dict[str, str]:
    policy = {}
    for entry in entries or []:
        path = relative_path(entry["path"])
        declaration = entry.get("scope_declaration", "")
        digest = entry.get("sha256", "")
        if (PurePosixPath(path).suffix.lower() != ".inp" or path in policy
                or not re.fullmatch(r"[0-9a-f]{64}", digest)
                or not isinstance(declaration, str)
                or not (("synthetic" in declaration.lower() and "not a project" in declaration.lower())
                        or ("合成" in declaration and "非项目" in declaration))):
            raise ReleaseError("Synthetic INP allowlist needs exact path/hash and explicit non-project scope")
        policy[path] = digest
    return policy


def public_text(relative: str, data: bytes, synthetic_templates: dict[str, str] | None = None) -> str:
    p = PurePosixPath(relative_path(relative))
    if any(part.casefold() in FORBIDDEN_PARTS | IGNORED_DIRS for part in p.parts):
        raise ReleaseError(f"Excluded source/cache/credential directory: {relative}")
    if p.name.casefold() in {"auth.json", "credentials.json", "secrets.json", ".env", "id_rsa", "id_ed25519"}:
        raise ReleaseError(f"Credential filename rejected: {relative}")
    synthetic_inp = p.suffix.lower() == ".inp" and (synthetic_templates or {}).get(relative) == sha256(data)
    if p.suffix.lower() not in TEXT_SUFFIXES and p.name not in TEXT_NAMES and not synthetic_inp:
        raise ReleaseError(f"Non-text/model/document payload rejected: {relative}")
    if any(word in p.name for word in ("化工原理", "Pdg2Pic", "z-library", "z-lib.sk")):
        raise ReleaseError(f"Textbook payload filename rejected: {relative}")
    if data.startswith(b"\xef\xbb\xbf") or b"\x00" in data:
        raise ReleaseError(f"BOM or binary bytes rejected: {relative}")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ReleaseError(f"Not UTF-8: {relative}") from exc
    if "\ufffd" in text:
        raise ReleaseError(f"Replacement glyph rejected: {relative}")
    if any(pattern.search(text) for pattern in SECRET_PATTERNS):
        raise ReleaseError(f"Possible credential rejected: {relative}")
    if PRIVATE_PATH.search(text):
        raise ReleaseError(f"Unresolved private home path rejected: {relative}")
    return text


def inventory(root: Path) -> dict[str, bytes]:
    reject_links(root)
    if not root.is_dir():
        raise ReleaseError("Release directory is missing")
    result: dict[str, bytes] = {}
    folded: set[str] = set()
    for current, directories, filenames in os.walk(root, followlinks=False):
        directories[:] = sorted(d for d in directories if d not in IGNORED_DIRS)
        for d in directories:
            reject_links(Path(current) / d)
        for name in sorted(filenames):
            path = Path(current) / name
            reject_links(path)
            rel = relative_path(path.relative_to(root).as_posix())
            if rel.casefold() in folded:
                raise ReleaseError(f"Case-insensitive collision: {rel}")
            folded.add(rel.casefold())
            result[rel] = path.read_bytes()
    return dict(sorted(result.items()))


def structure(payload: dict[str, bytes], expected_skill_count: int | None = None) -> list[str]:
    manifest_path = PLUGIN + "/.codex-plugin/plugin.json"
    if manifest_path not in payload:
        raise ReleaseError("Plugin manifest is missing")
    try:
        plugin = json.loads(payload[manifest_path])
    except (ValueError, TypeError) as exc:
        raise ReleaseError("Invalid plugin JSON") from exc
    if plugin.get("name") != "chemical-engineering-skills" or plugin.get("skills") != "./skills/":
        raise ReleaseError("Plugin name/skills path does not match the public layout")
    if not plugin.get("version") or not plugin.get("description"):
        raise ReleaseError("Plugin version/description is required")
    skill_names = sorted({PurePosixPath(p[len(SKILLS_PREFIX):]).parts[0] for p in payload if p.startswith(SKILLS_PREFIX)})
    if not skill_names or (expected_skill_count is not None and len(skill_names) != expected_skill_count):
        raise ReleaseError("Skill count differs from the frozen release contract")
    for name in skill_names:
        skill_path = SKILLS_PREFIX + name + "/SKILL.md"
        if skill_path not in payload:
            raise ReleaseError(f"Missing SKILL.md: {name}")
        text = payload[skill_path].decode("utf-8")
        header = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", text, re.S)
        if not header or not re.search(r"(?m)^name:\s*[\"']?" + re.escape(name) + r"[\"']?\s*$", header[1]) or not re.search(r"(?m)^description:\s*\S", header[1]):
            raise ReleaseError(f"Skill frontmatter/name is invalid: {name}")
    for needed in ("tools/install.py", "tools/verify_release.py"):
        if needed not in payload:
            raise ReleaseError(f"Missing required release tool: {needed}")
    return skill_names


def make_manifest(root: Path, *, release_name: str, release_version: str, expected_skill_count: int, external_dependencies: list | None = None, synthetic_templates: list | None = None) -> tuple[bytes, bytes]:
    payload = {p: b for p, b in inventory(root).items() if p not in {MANIFEST, CHECKSUMS}}
    policy = synthetic_policy(synthetic_templates)
    if any(path not in payload or sha256(payload[path]) != digest for path, digest in policy.items()):
        raise ReleaseError("Synthetic INP differs from reviewed output identity")
    for path, data in payload.items():
        public_text(path, data, policy)
    skills = structure(payload, expected_skill_count)
    dependencies = external_dependencies or []
    for dep in dependencies:
        if not isinstance(dep, dict) or dep.get("status") not in {"not_bundled", "not_verified", "optional_external"}:
            raise ReleaseError("External dependencies must be explicitly unverified/not bundled")
    manifest = {"schema": "chemical-public-release-v1", "release_name": release_name, "release_version": release_version,
                "scope": "reviewed_text_rules_and_scripts_only", "skill_names": skills, "skill_count": len(skills),
                "external_dependencies": dependencies, "commercial_software_verified": False, "knowledge_payload_bundled": False,
                "synthetic_templates": synthetic_templates or [],
                "files": [{"path": p, "sha256": sha256(b), "bytes": len(b)} for p, b in payload.items()]}
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    public_text(MANIFEST, manifest_bytes)
    sums = {p: sha256(b) for p, b in payload.items()}
    sums[MANIFEST] = sha256(manifest_bytes)
    checksum_bytes = "".join(f"{digest}  {path}\n" for path, digest in sorted(sums.items())).encode("utf-8")
    return manifest_bytes, checksum_bytes


def verify(root: Path) -> dict:
    all_files = inventory(root)
    if MANIFEST not in all_files or CHECKSUMS not in all_files:
        raise ReleaseError("Release must be sealed: manifest/checksums missing")
    public_text(MANIFEST, all_files[MANIFEST])
    manifest = json.loads(all_files[MANIFEST])
    policy = synthetic_policy(manifest.get("synthetic_templates", []))
    if any(path not in all_files or sha256(all_files[path]) != digest for path, digest in policy.items()):
        raise ReleaseError("Synthetic INP allowlist identity mismatch")
    for path, data in all_files.items():
        public_text(path, data, policy)
    if manifest.get("schema") != "chemical-public-release-v1" or manifest.get("commercial_software_verified") is not False or manifest.get("knowledge_payload_bundled") is not False:
        raise ReleaseError("Unsupported release schema or misleading external-validation state")
    for dependency in manifest.get("external_dependencies", []):
        if not isinstance(dependency, dict) or dependency.get("status") not in {"not_bundled", "not_verified", "optional_external"}:
            raise ReleaseError("Unverified external dependency cannot be labeled validated")
    expected: dict[str, str] = {}
    folded: set[str] = set()
    for entry in manifest.get("files", []):
        p = relative_path(entry["path"])
        if p in {MANIFEST, CHECKSUMS} or p.casefold() in folded:
            raise ReleaseError("Duplicate/reserved manifest entry")
        folded.add(p.casefold())
        b = all_files.get(p)
        if b is None or entry.get("bytes") != len(b) or entry.get("sha256") != sha256(b):
            raise ReleaseError(f"Missing or changed payload: {p}")
        expected[p] = sha256(b)
    if set(all_files) != set(expected) | {MANIFEST, CHECKSUMS}:
        raise ReleaseError("Actual inventory differs from sealed file list")
    skills = structure({p: all_files[p] for p in expected}, manifest.get("skill_count"))
    if skills != manifest.get("skill_names"):
        raise ReleaseError("Skill inventory differs from manifest")
    expected[MANIFEST] = sha256(all_files[MANIFEST])
    parsed: dict[str, str] = {}
    for line in all_files[CHECKSUMS].decode("utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match or match[2] in parsed:
            raise ReleaseError("Malformed or duplicate checksum line")
        parsed[relative_path(match[2])] = match[1]
    if parsed != expected:
        raise ReleaseError("Checksum ledger differs from actual payload/manifest")
    return {"integrity_verified": True, "utf8_verified": True, "structure_verified": True,
            "file_count": len(expected) - 1, "skill_count": len(skills),
            "commercial_software_verified": False, "knowledge_payload_bundled": False,
            "external_dependencies": manifest.get("external_dependencies", []), "manifest": manifest}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", "--root", dest="repository", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        result = verify(args.repository.resolve())
        result.pop("manifest")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ReleaseError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"integrity_verified": False, "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
