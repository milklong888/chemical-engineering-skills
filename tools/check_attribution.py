# 作者：milklong
# SPDX-FileCopyrightText: 2026 milklong (GitHub: milklong888) and contributors
# SPDX-License-Identifier: MIT
"""Read-only maintenance check for distributed attribution, not engineering gating.

This detects accidental removal or drift of declared notices. It neither prevents
malicious copying nor changes the permissions granted by a license. No repository
files are written, and source contents are not hash-frozen.
"""

import argparse
import json
import os
from pathlib import Path, PureWindowsPath
import re
import stat
import sys


SCHEMA = "milklong-attribution/v1"
AUTHOR = "作者：milklong"
COPYRIGHT = "SPDX-FileCopyrightText: 2026 milklong (GitHub: milklong888) and contributors"
MIT_ID = "SPDX-License-Identifier: MIT"
PROJECT_URL = re.compile(r"https://github\.com/milklong888/[A-Za-z0-9_.-]+/?\Z")
MIT_FRAGMENTS = (
    "Permission is hereby granted, free of charge, to any person obtaining a copy",
    'of this software and associated documentation files (the "Software")',
    "use, copy, modify, merge, publish, distribute, sublicense, and/or sell",
    "subject to the following conditions:",
    "The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.",
    'THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND',
    "IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE",
)
WINDOWS_RESERVED = re.compile(r"(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?\Z", re.I)


def _json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _link_or_junction(path):
    if path.is_symlink() or bool(getattr(path, "is_junction", lambda: False)()):
        return True
    # Python versions without Path.is_junction must still reject Windows
    # directory junctions and other reparse points rather than traverse them.
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except FileNotFoundError:
        return False
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def check(root):
    """Return a JSON-serializable report without modifying the repository."""
    errors = []
    checked = set()

    def error(code, path, message):
        errors.append({"code": code, "path": str(path), "message": message})

    def result():
        return {
            "schema": "milklong-attribution-check/v1",
            "pass": not errors,
            "root": str(repo),
            "files_checked": len(checked),
            "errors": errors,
            "scope": "Read-only attribution maintenance; not engineering acceptance, a restriction on licensed use, or protection against malicious copying.",
        }

    repo = Path(os.path.abspath(os.fspath(root)))
    # Inspect the supplied root and its ancestors before resolving any links.
    try:
        for item in reversed((repo, *repo.parents)):
            if _link_or_junction(item):
                error("symlink", item, "Repository root must not traverse a symbolic link or junction")
                return result()
        if not repo.is_dir():
            error("missing_root", repo, "Repository root is not an existing directory")
            return result()
        repo = repo.resolve(strict=True)
    except (OSError, ValueError) as exc:
        error("root_error", repo, str(exc))
        return result()

    def relative(value, label):
        if not isinstance(value, str) or not value.strip():
            error("unsafe_path", label, "Expected a nonempty relative path")
            return None
        parts = value.split("/")
        if (
            "\\" in value
            or PureWindowsPath(value).drive
            or any(part in ("", ".", "..") for part in parts)
            or any(any(ord(c) < 32 or c in ':<>"|?*' for c in part) for part in parts)
            or any(part.endswith((" ", ".")) or WINDOWS_RESERVED.fullmatch(part) for part in parts)
        ):
            error("unsafe_path", label, "Use canonical slash-separated relative paths without traversal, drives, or unsafe components")
            return None
        return value

    def target(value, kind="file"):
        current = repo
        try:
            for part in value.split("/"):
                current = current / part
                mode = current.lstat().st_mode
                if stat.S_ISLNK(mode) or _link_or_junction(current):
                    error("symlink", value, "Referenced paths must not traverse symbolic links or junctions")
                    return None
            resolved = current.resolve(strict=True)
            if not resolved.is_relative_to(repo):
                error("path_escape", value, "Resolved path escapes the repository")
                return None
            if not (current.is_dir() if kind == "directory" else current.is_file()):
                error("wrong_type", value, f"Expected an existing {kind}")
                return None
            return current
        except (OSError, ValueError) as exc:
            error("missing_or_unreadable_path", value, str(exc))
            return None

    def read(value):
        path = target(value)
        if path is None:
            return None
        try:
            text = path.read_text(encoding="utf-8-sig")
            checked.add(value)
            return text
        except (OSError, UnicodeError) as exc:
            error("unreadable_text", value, str(exc))
            return None

    raw = read("ATTRIBUTION.json")
    if raw is None:
        return result()
    try:
        manifest = json.loads(raw, object_pairs_hook=_json_object)
    except (ValueError, RecursionError) as exc:
        error("invalid_manifest", "ATTRIBUTION.json", str(exc))
        return result()
    if not isinstance(manifest, dict):
        error("invalid_manifest", "ATTRIBUTION.json", "Manifest must be a JSON object")
        return result()
    if manifest.get("schema") != SCHEMA:
        error("schema", "ATTRIBUTION.json", f"Expected schema {SCHEMA}")
    if manifest.get("author") != "milklong":
        error("author", "ATTRIBUTION.json", "Expected author milklong")
    url = manifest.get("project_url")
    if not isinstance(url, str) or not PROJECT_URL.fullmatch(url) or url.rstrip("/").split("/")[-1] in (".", ".."):
        error("project_url", "ATTRIBUTION.json", "Expected an HTTPS GitHub project URL under milklong888")
        url = None

    seen = {}

    def declare(value, label):
        path = relative(value, label)
        if path is None:
            return None
        # Casefold also catches names that collide when a repository moves to Windows.
        key = path.casefold()
        if key in seen:
            error("duplicate_path", label, f"Path already declared by {seen[key]}")
        else:
            seen[key] = label
        return path

    skill_root = relative(manifest.get("skill_root"), "skill_root")
    skill_dir = target(skill_root, "directory") if skill_root is not None else None
    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        error("entries", "ATTRIBUTION.json", "entries must be a nonempty array")
        entries = []
    covered = set()
    for index, entry in enumerate(entries):
        label = f"entries[{index}]"
        if not isinstance(entry, dict):
            error("entry", label, "Expected an object with path and sidecar")
            continue
        path = declare(entry.get("path"), label + ".path")
        sidecar = declare(entry.get("sidecar"), label + ".sidecar")
        if path is not None:
            if target(path) is not None:
                checked.add(path)
            covered.add(path)
        if path is not None and sidecar is not None and sidecar != path + ".license":
            error("sidecar_name", label, "sidecar must equal path + '.license' exactly")
        if sidecar is not None:
            text = read(sidecar)
            if text is not None:
                lines = text.splitlines()
                required = [AUTHOR, COPYRIGHT, MIT_ID]
                if url is not None:
                    required.append("Source: " + url)
                for line in required:
                    if line not in lines:
                        error("sidecar_line", sidecar, f"Missing exact line: {line}")

    if skill_dir is not None:
        try:
            for child in sorted(skill_dir.iterdir()):
                if _link_or_junction(child):
                    error("symlink", child.relative_to(repo), "Direct skill children must not be symbolic links or junctions")
                    continue
                if not child.is_dir():
                    continue
                skill = child / "SKILL.md"
                if skill.exists() or skill.is_symlink():
                    rel = skill.relative_to(repo).as_posix()
                    target(rel)
                    if rel not in covered:
                        error("uncovered_skill", rel, "Direct child skill SKILL.md is missing from entries")
        except OSError as exc:
            error("skill_discovery", skill_root, str(exc))

    for field in ("policy_files", "license_files"):
        values = manifest.get(field)
        if not isinstance(values, list) or not values:
            error("manifest_array", field, "Expected a nonempty array of relative file paths")
            continue
        for index, value in enumerate(values):
            path = declare(value, f"{field}[{index}]")
            text = read(path) if path is not None else None
            if text is None:
                continue
            if field == "policy_files":
                for fragment in [AUTHOR, "AI辅助编辑"] + ([url] if url is not None else []):
                    if fragment not in text:
                        error("policy_content", path, f"Missing policy text: {fragment}")
            else:
                normalized = " ".join(text.split()).casefold()
                if not re.search(r"\bcopyright\s*(?:\(c\)|©)?\s*\d{4}\b", text, re.I):
                    error("license_content", path, "Missing a copyright notice with a year")
                for fragment in MIT_FRAGMENTS:
                    if " ".join(fragment.split()).casefold() not in normalized:
                        error("license_content", path, f"Missing MIT permission/notice/warranty fragment: {fragment}")
    return result()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="Repository to inspect without modifying it")
    args = parser.parse_args(argv)
    report = check(args.root)
    # ASCII JSON is a UTF-8 subset and stays machine-readable even when Windows
    # stdout uses a legacy code page. JSON escapes preserve all Unicode values.
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
