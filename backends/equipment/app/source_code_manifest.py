from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any


MANIFEST_SCHEMA = "equipment-design-source-code-manifest-v1"
MANIFEST_NAME = "source_code_manifest.json"
SNAPSHOT_ROOT_NAME = "source_code_snapshot"
SHA256_PATTERN = re.compile(r"^[A-F0-9]{64}$")

# This is deliberately a fixed allowlist.  Adding or removing an executable
# authority module is a contract change, not an implicit directory scan.
CORE_SOURCE_PATHS = (
    "app/app_core.py",
    "app/aspen_com_import.py",
    "app/aspen_pfd.py",
    "app/authority_revision.py",
    "app/customer_delivery.py",
    "app/database_authority.py",
    "app/derivation_workbench.py",
    "app/equipment_design_agent.py",
    "app/equipment_design_app.py",
    "app/llm_bridge.py",
    "app/result_presentation.py",
    "app/runtime_bundle.py",
    "app/source_code_manifest.py",
    "app/projected_standard_store.py",
    "app/viscosity_fallback.py",
    "scripts/aspen_equipment_derivation.py",
    "scripts/connection_component_selection.py",
    "scripts/equipment_calc.py",
    "scripts/equipment_design_match.py",
    "scripts/equipment_service_profile.py",
    "scripts/case_profile.py",
)
MANIFEST_KEYS = {
    "schema",
    "source_paths",
    "path_set_sha256",
    "files",
    "source_code_set_sha256",
    "manifest_payload_sha256",
}
FILE_RECORD_KEYS = {"source_path", "size_bytes", "sha256"}


class SourceCodeManifestError(RuntimeError):
    pass


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _manifest_path(root: Path) -> Path:
    return root / "app" / MANIFEST_NAME


def _source_records(root: Path) -> list[dict[str, Any]]:
    resolved_root = root.expanduser().resolve()
    records: list[dict[str, Any]] = []
    for relative in CORE_SOURCE_PATHS:
        path = (resolved_root / Path(relative)).resolve()
        try:
            path.relative_to(resolved_root)
        except ValueError as exc:
            raise SourceCodeManifestError(
                f"core source escapes the declared root: {relative}"
            ) from exc
        if not path.is_file() or path.is_symlink():
            raise SourceCodeManifestError(f"core source is missing: {relative}")
        records.append({
            "source_path": relative,
            "size_bytes": int(path.stat().st_size),
            "sha256": sha256_file(path),
        })
    return records


def _manifest_from_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    source_paths = [str(item["source_path"]) for item in records]
    source_hashes = {
        str(item["source_path"]): str(item["sha256"])
        for item in records
    }
    manifest: dict[str, Any] = {
        "schema": MANIFEST_SCHEMA,
        "source_paths": source_paths,
        "path_set_sha256": canonical_sha256(source_paths),
        "files": records,
        "source_code_set_sha256": canonical_sha256(source_hashes),
    }
    manifest["manifest_payload_sha256"] = canonical_sha256(manifest)
    return manifest


def validate_manifest(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SourceCodeManifestError("source code manifest must be an object")
    unknown = set(value) - MANIFEST_KEYS
    missing = MANIFEST_KEYS - set(value)
    if unknown or missing:
        raise SourceCodeManifestError(
            "source code manifest keys are invalid: "
            f"missing={sorted(missing)}, unknown={sorted(unknown)}"
        )
    if value.get("schema") != MANIFEST_SCHEMA:
        raise SourceCodeManifestError("source code manifest schema is invalid")
    source_paths = value.get("source_paths")
    if source_paths != list(CORE_SOURCE_PATHS):
        raise SourceCodeManifestError("source code manifest path set is invalid")
    expected_path_set = canonical_sha256(list(CORE_SOURCE_PATHS))
    if value.get("path_set_sha256") != expected_path_set:
        raise SourceCodeManifestError("source code manifest path-set hash mismatch")
    files = value.get("files")
    if not isinstance(files, list) or len(files) != len(CORE_SOURCE_PATHS):
        raise SourceCodeManifestError("source code manifest file records are invalid")
    actual_paths: list[str] = []
    source_hashes: dict[str, str] = {}
    for record in files:
        if not isinstance(record, dict) or set(record) != FILE_RECORD_KEYS:
            raise SourceCodeManifestError("source code manifest file record is invalid")
        relative = record.get("source_path")
        size_bytes = record.get("size_bytes")
        digest = record.get("sha256")
        if not isinstance(relative, str):
            raise SourceCodeManifestError("source code manifest contains an invalid path")
        if not isinstance(size_bytes, int) or isinstance(size_bytes, bool) or size_bytes < 0:
            raise SourceCodeManifestError(
                f"source code manifest contains an invalid size: {relative}"
            )
        if not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest):
            raise SourceCodeManifestError(
                f"source code manifest contains an invalid hash: {relative}"
            )
        actual_paths.append(relative)
        source_hashes[relative] = digest
    if actual_paths != list(CORE_SOURCE_PATHS):
        raise SourceCodeManifestError("source code manifest file order/path set is invalid")
    if value.get("source_code_set_sha256") != canonical_sha256(source_hashes):
        raise SourceCodeManifestError("source code set hash mismatch")
    expected_payload_hash = canonical_sha256({
        key: item
        for key, item in value.items()
        if key != "manifest_payload_sha256"
    })
    if value.get("manifest_payload_sha256") != expected_payload_hash:
        raise SourceCodeManifestError("source code manifest payload hash mismatch")
    return json.loads(json.dumps(value, ensure_ascii=False))


def create_manifest(
    root: Path,
    *,
    output: Path | None = None,
    snapshot_root: Path | None = None,
) -> dict[str, Any]:
    resolved_root = root.expanduser().resolve()
    manifest = _manifest_from_records(_source_records(resolved_root))
    output_path = (output or _manifest_path(resolved_root)).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if snapshot_root is not None:
        snapshot = snapshot_root.expanduser().resolve()
        snapshot.mkdir(parents=True, exist_ok=True)
        for relative in CORE_SOURCE_PATHS:
            source = resolved_root / Path(relative)
            destination = snapshot / Path(relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        verification = verify_manifest(
            snapshot,
            manifest_path=output_path,
            exact_path_set=True,
            status="PACKAGED_SNAPSHOT_VERIFIED",
        )
        if not verification.get("verified"):
            raise SourceCodeManifestError(
                "generated source snapshot failed verification: "
                + json.dumps(verification.get("issues", []), ensure_ascii=False)
            )
    return manifest


def _actual_snapshot_paths(root: Path) -> set[str]:
    paths: set[str] = set()
    for path in root.rglob("*"):
        if path.is_file() or path.is_symlink():
            paths.add(path.relative_to(root).as_posix())
    return paths


def verify_manifest(
    content_root: Path,
    *,
    manifest_path: Path,
    exact_path_set: bool,
    status: str,
) -> dict[str, Any]:
    root = content_root.expanduser().resolve()
    manifest_path = manifest_path.expanduser().resolve()
    issues: list[dict[str, Any]] = []
    if not manifest_path.is_file():
        return {
            "verification_status": "FAILED_MANIFEST_MISSING",
            "verified": False,
            "status": status,
            "manifest_path": str(manifest_path),
            "manifest_sha256": None,
            "manifest_payload_sha256": None,
            "path_set_sha256": canonical_sha256(list(CORE_SOURCE_PATHS)),
            "source_code_set_sha256": None,
            "source_code_sha256": {},
            "file_count": 0,
            "issues": [{"code": "SOURCE_CODE_MANIFEST_MISSING", "path": str(manifest_path)}],
        }
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest = validate_manifest(raw)
    except (OSError, json.JSONDecodeError, SourceCodeManifestError) as exc:
        return {
            "verification_status": "FAILED_MANIFEST_INVALID",
            "verified": False,
            "status": status,
            "manifest_path": str(manifest_path),
            "manifest_sha256": sha256_file(manifest_path),
            "manifest_payload_sha256": None,
            "path_set_sha256": canonical_sha256(list(CORE_SOURCE_PATHS)),
            "source_code_set_sha256": None,
            "source_code_sha256": {},
            "file_count": 0,
            "issues": [{"code": "SOURCE_CODE_MANIFEST_INVALID", "detail": str(exc)}],
        }
    if exact_path_set:
        actual_paths = _actual_snapshot_paths(root) if root.is_dir() else set()
        expected_paths = set(CORE_SOURCE_PATHS)
        for relative in sorted(expected_paths - actual_paths):
            issues.append({"code": "SOURCE_CODE_FILE_MISSING", "path": relative})
        for relative in sorted(actual_paths - expected_paths):
            issues.append({"code": "SOURCE_CODE_FILE_EXTRA", "path": relative})
    records = {item["source_path"]: item for item in manifest["files"]}
    for relative in CORE_SOURCE_PATHS:
        path = root / Path(relative)
        if not path.is_file() or path.is_symlink():
            if not any(
                issue.get("code") == "SOURCE_CODE_FILE_MISSING"
                and issue.get("path") == relative
                for issue in issues
            ):
                issues.append({"code": "SOURCE_CODE_FILE_MISSING", "path": relative})
            continue
        record = records[relative]
        actual_size = int(path.stat().st_size)
        if actual_size != record["size_bytes"]:
            issues.append({
                "code": "SOURCE_CODE_FILE_SIZE_MISMATCH",
                "path": relative,
                "expected": record["size_bytes"],
                "actual": actual_size,
            })
        actual_hash = sha256_file(path)
        if actual_hash != record["sha256"]:
            issues.append({
                "code": "SOURCE_CODE_FILE_HASH_MISMATCH",
                "path": relative,
                "expected": record["sha256"],
                "actual": actual_hash,
            })
    source_hashes = {
        relative: str(records[relative]["sha256"])
        for relative in CORE_SOURCE_PATHS
    }
    return {
        "verification_status": "PASS" if not issues else "FAILED",
        "verified": not issues,
        "status": status,
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "manifest_payload_sha256": manifest["manifest_payload_sha256"],
        "path_set_sha256": manifest["path_set_sha256"],
        "source_code_set_sha256": manifest["source_code_set_sha256"],
        "source_code_sha256": source_hashes,
        "file_count": len(CORE_SOURCE_PATHS),
        "issues": issues,
    }


def verify_current_runtime(package_root: Path, *, frozen: bool) -> dict[str, Any]:
    root = package_root.expanduser().resolve()
    manifest_path = _manifest_path(root)
    if frozen:
        return verify_manifest(
            root / SNAPSHOT_ROOT_NAME,
            manifest_path=manifest_path,
            exact_path_set=True,
            status="PACKAGED_SNAPSHOT_VERIFIED",
        )
    return verify_manifest(
        root,
        manifest_path=manifest_path,
        exact_path_set=False,
        status="SOURCE_TREE_VERIFIED",
    )


def require_current_runtime(package_root: Path, *, frozen: bool) -> dict[str, Any]:
    verification = verify_current_runtime(package_root, frozen=frozen)
    if not verification.get("verified"):
        raise SourceCodeManifestError(
            "source code authority verification failed: "
            + json.dumps(verification.get("issues", []), ensure_ascii=False)
        )
    return verification


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create or verify the fixed equipment-design core source manifest."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    create_parser = subparsers.add_parser("create")
    create_parser.add_argument("--root", required=True)
    create_parser.add_argument("--output")
    create_parser.add_argument("--snapshot-root")
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--root", required=True)
    verify_parser.add_argument("--manifest", required=True)
    verify_parser.add_argument("--snapshot", action="store_true")
    args = parser.parse_args()
    if args.command == "create":
        manifest = create_manifest(
            Path(args.root),
            output=Path(args.output) if args.output else None,
            snapshot_root=Path(args.snapshot_root) if args.snapshot_root else None,
        )
        print(json.dumps({
            "status": "CREATED",
            "source_code_set_sha256": manifest["source_code_set_sha256"],
            "file_count": len(manifest["files"]),
        }, ensure_ascii=False, sort_keys=True))
        return 0
    result = verify_manifest(
        Path(args.root),
        manifest_path=Path(args.manifest),
        exact_path_set=bool(args.snapshot),
        status=("PACKAGED_SNAPSHOT_VERIFIED" if args.snapshot else "SOURCE_TREE_VERIFIED"),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("verified") else 1


if __name__ == "__main__":
    raise SystemExit(main())
