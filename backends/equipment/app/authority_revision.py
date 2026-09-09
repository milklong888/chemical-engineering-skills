from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import app_core  # noqa: E402
import runtime_bundle  # noqa: E402
import source_code_manifest  # noqa: E402


AGENT_PROTOCOL_VERSION = "1.9.0"
AUTHORITY_REVISION_SCHEMA = "equipment-design-authority-revision-v1"
HASH_PATTERN = re.compile(r"^[A-F0-9]{64}$")
CORE_ASSET_KEYS = (
    "rules",
    "model_rules",
    "parameter_templates",
    "customer_output_profiles",
    "pump_standard_points",
    "pipe_standard_dn_od",
    "equipment_selection_graph",
)
REVISION_KEYS = {
    "schema",
    "agent_protocol_version",
    "matcher_engine_version",
    "core_asset_sha256",
    "core_asset_set_sha256",
    "schema_asset_sha256",
    "schema_asset_set_sha256",
    "source_code_sha256",
    "source_code_set_sha256",
    "source_code_manifest",
    "runtime_manifest",
    "authority_revision_sha256",
}
SOURCE_CODE_MANIFEST_KEYS = {
    "status",
    "manifest_sha256",
    "manifest_payload_sha256",
    "path_set_sha256",
    "file_count",
}
RUNTIME_MANIFEST_KEYS = {
    "status",
    "manifest_sha256",
    "bundle_revision",
}


class AuthorityRevisionError(ValueError):
    pass


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _required_file_sha256(path: Any, asset_id: str) -> str:
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        raise AuthorityRevisionError(f"authority asset is missing: {asset_id}")
    return _sha256_file(resolved)


def _current_core_asset_hashes() -> dict[str, str]:
    paths = {
        "rules": app_core.matcher.RULES_PATH,
        "model_rules": app_core.matcher.MODEL_RULES_PATH,
        "parameter_templates": app_core.matcher.PARAMETER_TEMPLATES_PATH,
        "customer_output_profiles": app_core.matcher.CUSTOMER_OUTPUT_PROFILES_PATH,
        "pump_standard_points": app_core.matcher.PUMP_STANDARD_POINTS_PATH,
        "pipe_standard_dn_od": app_core.matcher.PIPE_STANDARD_DN_OD_PATH,
        "equipment_selection_graph": app_core.matcher.GRAPH_PATH,
    }
    return {
        asset_id: _required_file_sha256(paths[asset_id], asset_id)
        for asset_id in CORE_ASSET_KEYS
    }


def _current_schema_asset_hashes() -> dict[str, str]:
    schema_root = Path(app_core.APP_DIR) / "schemas"
    if not schema_root.is_dir():
        raise AuthorityRevisionError("schema asset directory is missing")
    schema_paths = sorted(schema_root.glob("*.json"), key=lambda item: item.name)
    if not schema_paths:
        raise AuthorityRevisionError("schema asset directory is empty")
    return {
        f"app/schemas/{path.name}": _required_file_sha256(
            path,
            f"app/schemas/{path.name}",
        )
        for path in schema_paths
    }


def _source_runtime_revision(
    core_asset_set_sha256: str,
    schema_asset_set_sha256: str,
    source_code_set_sha256: str,
) -> str:
    return canonical_sha256({
        "core_asset_set_sha256": core_asset_set_sha256,
        "schema_asset_set_sha256": schema_asset_set_sha256,
        "source_code_set_sha256": source_code_set_sha256,
    })


def _current_source_code_binding() -> tuple[dict[str, str], str, dict[str, Any]]:
    try:
        verification = source_code_manifest.require_current_runtime(
            Path(app_core.PACKAGE_ROOT),
            frozen=bool(getattr(sys, "_MEIPASS", None)),
        )
    except source_code_manifest.SourceCodeManifestError as exc:
        raise AuthorityRevisionError(str(exc)) from exc
    source_hashes = verification.get("source_code_sha256")
    source_code_set_sha256 = verification.get("source_code_set_sha256")
    if (
        not isinstance(source_hashes, dict)
        or set(source_hashes) != set(source_code_manifest.CORE_SOURCE_PATHS)
        or not isinstance(source_code_set_sha256, str)
        or not HASH_PATTERN.fullmatch(source_code_set_sha256)
    ):
        raise AuthorityRevisionError("verified source code binding is invalid")
    binding = {
        "status": verification["status"],
        "manifest_sha256": verification["manifest_sha256"],
        "manifest_payload_sha256": verification["manifest_payload_sha256"],
        "path_set_sha256": verification["path_set_sha256"],
        "file_count": verification["file_count"],
    }
    return dict(source_hashes), source_code_set_sha256, binding


def _runtime_manifest_binding(source_runtime_revision: str) -> dict[str, Any]:
    manifest_path = Path(app_core.PACKAGE_ROOT) / runtime_bundle.MANIFEST_NAME
    packaged = bool(getattr(sys, "_MEIPASS", None))
    if not packaged:
        return {
            "status": "NOT_PACKAGED",
            "manifest_sha256": None,
            "bundle_revision": source_runtime_revision,
        }
    if not manifest_path.is_file():
        raise AuthorityRevisionError("packaged runtime manifest is missing")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthorityRevisionError(f"packaged runtime manifest is invalid: {exc}") from exc
    if manifest.get("schema") != runtime_bundle.MANIFEST_SCHEMA:
        raise AuthorityRevisionError("packaged runtime manifest schema is invalid")
    bundle_revision = str(manifest.get("bundle_revision", "")).strip().upper()
    if not HASH_PATTERN.fullmatch(bundle_revision):
        raise AuthorityRevisionError("packaged runtime bundle revision is invalid")
    return {
        "status": "PACKAGED",
        "manifest_sha256": _sha256_file(manifest_path),
        "bundle_revision": bundle_revision,
    }


def current_authority_revision() -> dict[str, Any]:
    core_assets = _current_core_asset_hashes()
    core_asset_set_sha256 = canonical_sha256(core_assets)
    schema_assets = _current_schema_asset_hashes()
    schema_asset_set_sha256 = canonical_sha256(schema_assets)
    source_code_assets, source_code_set_sha256, source_code_binding = (
        _current_source_code_binding()
    )
    source_runtime_revision = _source_runtime_revision(
        core_asset_set_sha256,
        schema_asset_set_sha256,
        source_code_set_sha256,
    )
    revision: dict[str, Any] = {
        "schema": AUTHORITY_REVISION_SCHEMA,
        "agent_protocol_version": AGENT_PROTOCOL_VERSION,
        "matcher_engine_version": str(
            getattr(app_core.matcher, "ENGINE_VERSION", "unknown")
        ),
        "core_asset_sha256": core_assets,
        "core_asset_set_sha256": core_asset_set_sha256,
        "schema_asset_sha256": schema_assets,
        "schema_asset_set_sha256": schema_asset_set_sha256,
        "source_code_sha256": source_code_assets,
        "source_code_set_sha256": source_code_set_sha256,
        "source_code_manifest": source_code_binding,
        "runtime_manifest": _runtime_manifest_binding(source_runtime_revision),
    }
    revision["authority_revision_sha256"] = canonical_sha256(revision)
    return revision


def validate_authority_revision(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AuthorityRevisionError("authority_revision must be an object")
    unknown = set(value) - REVISION_KEYS
    missing = REVISION_KEYS - set(value)
    if unknown or missing:
        raise AuthorityRevisionError(
            f"authority_revision keys are invalid: missing={sorted(missing)}, unknown={sorted(unknown)}"
        )
    if value.get("schema") != AUTHORITY_REVISION_SCHEMA:
        raise AuthorityRevisionError("authority_revision schema is invalid")
    if not str(value.get("agent_protocol_version", "")).strip():
        raise AuthorityRevisionError("agent_protocol_version is empty")
    if not str(value.get("matcher_engine_version", "")).strip():
        raise AuthorityRevisionError("matcher_engine_version is empty")
    core_assets = value.get("core_asset_sha256")
    if not isinstance(core_assets, dict) or set(core_assets) != set(CORE_ASSET_KEYS):
        raise AuthorityRevisionError("core_asset_sha256 keys are invalid")
    if not all(
        isinstance(core_assets[key], str) and HASH_PATTERN.fullmatch(core_assets[key])
        for key in CORE_ASSET_KEYS
    ):
        raise AuthorityRevisionError("core_asset_sha256 contains an invalid hash")
    claimed_asset_set = str(value.get("core_asset_set_sha256", "")).strip().upper()
    actual_asset_set = canonical_sha256(core_assets)
    if claimed_asset_set != actual_asset_set:
        raise AuthorityRevisionError(
            f"core asset set hash mismatch: expected={claimed_asset_set}, actual={actual_asset_set}"
        )
    schema_assets = value.get("schema_asset_sha256")
    if not isinstance(schema_assets, dict) or not schema_assets:
        raise AuthorityRevisionError("schema_asset_sha256 must be a nonempty object")
    for relative_path, digest in schema_assets.items():
        if (
            not isinstance(relative_path, str)
            or not re.fullmatch(r"app/schemas/[^/\\]+\.json", relative_path)
        ):
            raise AuthorityRevisionError("schema_asset_sha256 contains an invalid relative path")
        if not isinstance(digest, str) or not HASH_PATTERN.fullmatch(digest):
            raise AuthorityRevisionError("schema_asset_sha256 contains an invalid hash")
    claimed_schema_set = str(value.get("schema_asset_set_sha256", "")).strip().upper()
    actual_schema_set = canonical_sha256(schema_assets)
    if claimed_schema_set != actual_schema_set:
        raise AuthorityRevisionError(
            f"schema asset set hash mismatch: expected={claimed_schema_set}, actual={actual_schema_set}"
        )
    source_code_assets = value.get("source_code_sha256")
    if (
        not isinstance(source_code_assets, dict)
        or set(source_code_assets) != set(source_code_manifest.CORE_SOURCE_PATHS)
    ):
        raise AuthorityRevisionError("source_code_sha256 keys are invalid")
    if not all(
        isinstance(source_code_assets[path], str)
        and HASH_PATTERN.fullmatch(source_code_assets[path])
        for path in source_code_manifest.CORE_SOURCE_PATHS
    ):
        raise AuthorityRevisionError("source_code_sha256 contains an invalid hash")
    claimed_source_code_set = str(
        value.get("source_code_set_sha256", "")
    ).strip().upper()
    actual_source_code_set = canonical_sha256(source_code_assets)
    if claimed_source_code_set != actual_source_code_set:
        raise AuthorityRevisionError(
            "source code set hash mismatch: "
            f"expected={claimed_source_code_set}, actual={actual_source_code_set}"
        )
    source_binding = value.get("source_code_manifest")
    if (
        not isinstance(source_binding, dict)
        or set(source_binding) != SOURCE_CODE_MANIFEST_KEYS
    ):
        raise AuthorityRevisionError("source_code_manifest keys are invalid")
    if source_binding.get("status") not in {
        "SOURCE_TREE_VERIFIED",
        "PACKAGED_SNAPSHOT_VERIFIED",
    }:
        raise AuthorityRevisionError("source_code_manifest.status is invalid")
    for key in (
        "manifest_sha256",
        "manifest_payload_sha256",
        "path_set_sha256",
    ):
        if not isinstance(source_binding.get(key), str) or not HASH_PATTERN.fullmatch(
            source_binding[key]
        ):
            raise AuthorityRevisionError(f"source_code_manifest.{key} is invalid")
    if source_binding["path_set_sha256"] != canonical_sha256(
        list(source_code_manifest.CORE_SOURCE_PATHS)
    ):
        raise AuthorityRevisionError("source_code_manifest path-set hash is invalid")
    if source_binding.get("file_count") != len(source_code_manifest.CORE_SOURCE_PATHS):
        raise AuthorityRevisionError("source_code_manifest file count is invalid")
    runtime_manifest = value.get("runtime_manifest")
    if not isinstance(runtime_manifest, dict) or set(runtime_manifest) != RUNTIME_MANIFEST_KEYS:
        raise AuthorityRevisionError("runtime_manifest keys are invalid")
    status = runtime_manifest.get("status")
    manifest_sha256 = runtime_manifest.get("manifest_sha256")
    bundle_revision = runtime_manifest.get("bundle_revision")
    if status == "PACKAGED":
        if source_binding.get("status") != "PACKAGED_SNAPSHOT_VERIFIED":
            raise AuthorityRevisionError(
                "packaged runtime must bind a verified packaged source snapshot"
            )
        if not isinstance(manifest_sha256, str) or not HASH_PATTERN.fullmatch(manifest_sha256):
            raise AuthorityRevisionError("packaged runtime manifest hash is invalid")
        if not isinstance(bundle_revision, str) or not HASH_PATTERN.fullmatch(bundle_revision):
            raise AuthorityRevisionError("packaged runtime bundle revision is invalid")
    elif status == "NOT_PACKAGED":
        if source_binding.get("status") != "SOURCE_TREE_VERIFIED":
            raise AuthorityRevisionError(
                "source runtime must bind a verified source tree"
            )
        if manifest_sha256 is not None:
            raise AuthorityRevisionError("source runtime must not claim a packaged manifest hash")
        expected_source_revision = _source_runtime_revision(
            claimed_asset_set,
            claimed_schema_set,
            claimed_source_code_set,
        )
        if bundle_revision != expected_source_revision:
            raise AuthorityRevisionError(
                "source runtime revision must equal the combined core, schema and source-code set hash"
            )
    else:
        raise AuthorityRevisionError("runtime_manifest.status is invalid")
    claimed_revision = str(value.get("authority_revision_sha256", "")).strip().upper()
    unhashed = {
        key: item
        for key, item in value.items()
        if key != "authority_revision_sha256"
    }
    actual_revision = canonical_sha256(unhashed)
    if claimed_revision != actual_revision:
        raise AuthorityRevisionError(
            f"authority revision hash mismatch: expected={claimed_revision}, actual={actual_revision}"
        )
    return json.loads(json.dumps(value, ensure_ascii=False))
