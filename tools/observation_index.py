#!/usr/bin/env python3
"""Read an explicit evidence manifest into an audit-only observation index."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys


MANIFEST_SCHEMA = "chemical-observation-manifest-v1"
INDEX_SCHEMA = "chemical-observation-index-v1"
MAX_MANIFEST_BYTES = 128 * 1024
MAX_ARTIFACT_BYTES = 1024 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024
MAX_ARTIFACTS = 64
CONTEXT_KEYS = ("experiment_id", "case_family_id", "task_id", "revision")
IDENTITY_KEYS = (*CONTEXT_KEYS, "case_id", "run_id", "execution_id", "case_sha256", "source_sha256")
STATE_KEYS = (
    "status", "ok", "simulation_clean", "delivery_passed", "delivery_verified",
    "strict_delivery_passed", "engineering_passed", "model_run_requested",
    "source_unchanged", "message_count", "error_count", "warning_count",
    "native_created", "native_executed", "native_verified",
)
SCENARIOS = {"normal", "expected_refusal", "injected_fault", "natural_failure"}
MODES = {"real_tool", "offline_stub", "text_only"}
IDENTITY_POINTERS = {
    prefix + key for prefix in ("/", "/identity/") for key in IDENTITY_KEYS
}
MISSING = object()


class ObservationError(ValueError):
    """The explicitly requested input cannot be safely indexed."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def reject_links(path: Path) -> None:
    for part in (path, *path.parents):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if (stat.S_ISLNK(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & 0x400
                or (hasattr(part, "is_junction") and part.is_junction())):
            raise ObservationError("Symlink, junction or reparse point is not allowed")


def absolute_input(value: Path, *, directory: bool) -> Path:
    if not value.is_absolute() or ".." in value.parts:
        raise ObservationError("Manifest and evidence root require absolute, non-parent paths")
    reject_links(value)
    if directory and not value.is_dir():
        raise ObservationError("Evidence root must be an existing regular directory")
    return value.resolve(strict=directory)


def relative_artifact(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > 1024:
        raise ObservationError("Artifact path must be a bounded relative string")
    if "\\" in value or ":" in value or value.startswith("/"):
        raise ObservationError("Artifact path must use portable relative POSIX syntax")
    parts = value.split("/")
    for part in parts:
        if (part in {"", ".", ".."} or part.endswith((".", " "))
                or any(ord(c) < 32 or c in '<>"|?*' for c in part)
                or re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?", part)):
            raise ObservationError("Artifact path contains a forbidden component")
    return PurePosixPath(value).as_posix()


def artifact_target(root: Path, relative: str) -> Path:
    target = root.joinpath(*relative.split("/"))
    reject_links(target)
    if not target.resolve(strict=False).is_relative_to(root):
        raise ObservationError("Artifact path escapes evidence root")
    return target


def read_bounded(path: Path, limit: int) -> bytes:
    reject_links(path)
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode):
        raise ObservationError("Input is not a regular file")
    if before.st_size > limit:
        raise ObservationError("Input exceeds its byte limit")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if (not stat.S_ISREG(opened.st_mode)
                or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino)):
            raise ObservationError("Input identity changed before read")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            data = handle.read(limit + 1)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    reject_links(path)
    current = path.lstat()
    identity = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns)
    if len(data) > limit:
        raise ObservationError("Input exceeds its byte limit")
    if identity(before) != identity(after) or identity(after) != identity(current) or len(data) != after.st_size:
        raise ObservationError("Input changed during read")
    return data


def unique_object(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ObservationError("Duplicate JSON keys are not allowed")
        result[key] = value
    return result


def parse_json(data: bytes) -> object:
    def bad_constant(value: str):
        raise ObservationError("Non-finite JSON number is not allowed")
    try:
        result = json.loads(data.decode("utf-8-sig"), object_pairs_hook=unique_object,
                            parse_constant=bad_constant)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ObservationError("Invalid or excessive JSON structure") from exc
    stack = [(result, 0)]
    nodes = 0
    while stack:
        value, depth = stack.pop()
        nodes += 1
        if depth > 32 or nodes > 50000:
            raise ObservationError("JSON structure exceeds limits")
        if isinstance(value, float) and not math.isfinite(value):
            raise ObservationError("Non-finite JSON number is not allowed")
        if isinstance(value, dict):
            stack.extend((item, depth + 1) for item in value.values())
        elif isinstance(value, list):
            stack.extend((item, depth + 1) for item in value)
    return result


def bounded_string(value: object, name: str, maximum: int = 512) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or any(ord(c) < 32 for c in value):
        raise ObservationError(name + " must be a bounded nonempty string")
    return value


def scalar(value: object) -> bool:
    return value is None or type(value) in (str, bool, int, float)


def validate_manifest(value: object) -> dict:
    allowed = {"schema", *CONTEXT_KEYS, "scenario_kind", "execution_mode",
               "declared_resources", "observed_resources", "artifacts"}
    if not isinstance(value, dict) or set(value) - allowed or value.get("schema") != MANIFEST_SCHEMA:
        raise ObservationError("Unsupported manifest schema or fields")
    for key in CONTEXT_KEYS:
        bounded_string(value.get(key), key)
    if (not isinstance(value.get("scenario_kind"), str) or value["scenario_kind"] not in SCENARIOS
            or not isinstance(value.get("execution_mode"), str) or value["execution_mode"] not in MODES):
        raise ObservationError("Unsupported scenario_kind or execution_mode")
    for key in ("declared_resources", "observed_resources"):
        items = value.get(key)
        if items is None:
            continue
        if not isinstance(items, list) or len(items) > 64:
            raise ObservationError("Resource declarations must be bounded lists or null")
        for item in items:
            bounded_string(item, key)
    artifacts = value.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) > MAX_ARTIFACTS:
        raise ObservationError("artifacts must be a bounded explicit list")
    seen = set()
    for item in artifacts:
        if not isinstance(item, dict) or set(item) - {"path", "role", "expected_sha256", "expected_identity"}:
            raise ObservationError("Unsupported artifact fields")
        path = relative_artifact(item.get("path"))
        if path.casefold() in seen:
            raise ObservationError("Duplicate or case-aliased artifact path")
        seen.add(path.casefold())
        bounded_string(item.get("role"), "role", 128)
        if not isinstance(item.get("expected_sha256"), str) or not re.fullmatch(r"[0-9a-fA-F]{64}", item["expected_sha256"]):
            raise ObservationError("Each artifact requires an exact SHA256")
        expected = item.get("expected_identity", {})
        if not isinstance(expected, dict) or set(expected) - IDENTITY_POINTERS:
            raise ObservationError("expected_identity requires supported literal identity pointers")
        for pointer, val in expected.items():
            if not scalar(val) or (isinstance(val, str) and len(val) > 512):
                raise ObservationError("Expected identity values must be bounded JSON scalars")
            key = pointer.rsplit("/", 1)[-1]
            if key in CONTEXT_KEYS and (type(val) is not str or val != value[key]):
                raise ObservationError("Expected identity contradicts manifest context")
    return value


def pointer_value(record: dict, pointer: str) -> object:
    value = record
    for part in pointer.split("/")[1:]:
        if not isinstance(value, dict) or part not in value:
            return MISSING
        value = value[part]
    return value


def extract_record(record: dict, manifest: dict, item: dict) -> tuple[dict, dict]:
    original = {"schema_fields": {}, "identity_fields": {}, "state_fields": {}, "omitted_non_scalar_or_large": []}
    selectors = {
        "schema_fields": ("/schema", "/schema_version"),
        "identity_fields": sorted(IDENTITY_POINTERS),
        "state_fields": ["/" + key for key in STATE_KEYS] + ["/run/status"],
    }
    for group, pointers in selectors.items():
        for pointer in pointers:
            value = pointer_value(record, pointer)
            if value is MISSING:
                continue
            if not scalar(value) or (isinstance(value, str) and len(value) > 4096):
                original["omitted_non_scalar_or_large"].append(pointer)
                continue
            original[group][pointer] = value

    checks = []
    observed_context = []
    for key in CONTEXT_KEYS:
        for prefix in ("/", "/identity/"):
            pointer = prefix + key
            actual = pointer_value(record, pointer)
            if actual is not MISSING:
                observed_context.append(key)
                checks.append(compare(pointer, manifest[key], actual, "manifest_context"))
    for pointer, expected in item.get("expected_identity", {}).items():
        checks.append(compare(pointer, expected, pointer_value(record, pointer), "explicit_expectation"))
    states = {check["state"] for check in checks}
    state = ("conflict" if "conflict" in states else "missing" if "missing" in states
             else "matched_fields" if checks else "unobserved")
    identity = {"state": state, "checks": checks,
                "unobserved_context_fields": [key for key in CONTEXT_KEYS if key not in observed_context],
                "scope": "literal_fields_only_not_case_qualification"}
    return original, identity


def compare(pointer: str, expected: object, actual: object, basis: str) -> dict:
    result = {"pointer": pointer, "basis": basis, "expected": expected}
    if actual is MISSING:
        result["state"] = "missing"
    elif not scalar(actual) or (isinstance(actual, str) and len(actual) > 4096):
        result.update(state="conflict", observed_value="omitted_non_scalar_or_large")
    else:
        result["observed"] = actual
        result["state"] = "match" if type(actual) is type(expected) and actual == expected else "conflict"
    return result


def build_index(manifest_path: Path, evidence_root: Path) -> dict:
    root = absolute_input(evidence_root, directory=True)
    manifest_path = absolute_input(manifest_path, directory=False)
    manifest_bytes = read_bounded(manifest_path, MAX_MANIFEST_BYTES)
    manifest = validate_manifest(parse_json(manifest_bytes))
    # Validate every explicit target before reading any artifact, never enumerate a tree.
    targets = [(item, artifact_target(root, item["path"])) for item in manifest["artifacts"]]
    records = []
    total_bytes = 0
    for item, target in targets:
        row = {"path": item["path"], "role": item["role"],
               "expected_sha256": item["expected_sha256"].lower(),
               "file_state": "missing", "hash_state": "unobserved", "json_state": "unobserved",
               "identity_comparison": {"state": "unobserved"}}
        try:
            data = read_bounded(target, min(MAX_ARTIFACT_BYTES, MAX_TOTAL_BYTES - total_bytes))
        except FileNotFoundError:
            records.append(row)
            continue
        total_bytes += len(data)
        row.update(file_state="read", observed_sha256=digest(data), bytes=len(data))
        row["hash_state"] = "matched" if row["observed_sha256"] == row["expected_sha256"] else "mismatch"
        if row["hash_state"] == "mismatch":
            row["json_state"] = "not_parsed_hash_mismatch"
        elif target.suffix.lower() != ".json":
            row["json_state"] = "not_json"
        else:
            try:
                record = parse_json(data)
                if not isinstance(record, dict):
                    raise ObservationError("JSON evidence requires an object record")
            except ObservationError:
                row["json_state"] = "invalid"
            else:
                row["json_state"] = "parsed"
                row["original_record"], row["identity_comparison"] = extract_record(record, manifest, item)
        records.append(row)
    resources = {}
    for key in ("declared_resources", "observed_resources"):
        value = manifest.get(key)
        resources[key] = {"state": "unobserved" if value is None else "reported",
                          "items": value, "basis": "manifest_statement_not_independent_execution_proof"}
    return {
        "schema": INDEX_SCHEMA,
        "purpose": "audit_index_only",
        "interpretation": "No engineering acceptance, learning eligibility or permission is evaluated; original fields remain uninterpreted.",
        "manifest": {"path": str(manifest_path), "sha256": digest(manifest_bytes)},
        "evidence_root": str(root),
        "context": {key: manifest[key] for key in CONTEXT_KEYS},
        "scenario_kind": manifest["scenario_kind"], "execution_mode": manifest["execution_mode"],
        "resources": resources, "artifacts": records,
        "summary": {
            "listed_artifacts": len(records), "read_artifacts": sum(x["file_state"] == "read" for x in records),
            "missing_artifacts": sum(x["file_state"] == "missing" for x in records),
            "hash_mismatches": sum(x["hash_state"] == "mismatch" for x in records),
            "identity_conflicts": sum(x["identity_comparison"]["state"] == "conflict" for x in records),
            "identity_missing": sum(x["identity_comparison"]["state"] == "missing" for x in records),
            "identity_unobserved": sum(x["identity_comparison"]["state"] == "unobserved" for x in records),
            "invalid_json": sum(x["json_state"] == "invalid" for x in records), "bytes_read": total_bytes,
        },
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        output = build_index(args.manifest, args.evidence_root)
        code = 0
    except (ObservationError, OSError, TypeError, ValueError) as exc:
        output = {"schema": INDEX_SCHEMA, "purpose": "audit_index_only", "input_error": str(exc)}
        code = 2
    print(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
