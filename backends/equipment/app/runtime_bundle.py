from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


MANIFEST_SCHEMA = "equipment-design-runtime-asset-manifest-v1"
MANIFEST_NAME = "runtime_asset_manifest.json"
SHA256_PATTERN = re.compile(r"^[0-9A-F]{64}$")
RUNTIME_ROOTS = (
    "knowledge_graph",
    "equipment_selection_graph",
    "data",
    "app/schemas",
)
STANDARDS_SQLITE_PATH = "data/standard_facts.sqlite.gz"
EXECUTABLE_STANDARD_SQLITE_PATH = (
    "knowledge_graph/standards_graph/executable_data/"
    "build_20260720_visual_batch_v2/executable_store/"
    "executable_standard_data.sqlite"
)
EXECUTABLE_STANDARD_MANIFEST_PATH = (
    "knowledge_graph/standards_graph/executable_data/"
    "build_20260720_visual_batch_v2/executable_store/build_manifest.json"
)
REQUIRED_RUNTIME_PATHS = {
    "knowledge_graph/equipment_match_rules.json",
    "knowledge_graph/equipment_model_recommendation_rules.json",
    "knowledge_graph/equipment_parameter_chain_templates.json",
    "knowledge_graph/equipment_customer_output_profiles.json",
    "knowledge_graph/equipment_design_parameter_package.schema.json",
    "knowledge_graph/equipment_connection_selection_package.schema.json",
    "knowledge_graph/equipment_service_label_derivation_contract.md",
    "knowledge_graph/equipment_service_profile.schema.json",
    "knowledge_graph/aspen_equipment_export.schema.json",
    "knowledge_graph/equipment_type_applicability_contract.md",
    "knowledge_graph/equipment_type_applicability_graph.schema.json",
    "knowledge_graph/equipment_type_applicability_label_catalog.json",
    "knowledge_graph/type_selection/hgt20592_20635/hash_manifest.csv",
    "knowledge_graph/type_selection/hgt20592_20635/select_terminal_type.py",
    "knowledge_graph/type_selection/hgt20592_20635/type_catalog.csv",
    "knowledge_graph/type_selection/hgt20592_20635/hard_exclusions.csv",
    "knowledge_graph/type_selection/hgt20592_20635/compatibility_matrix.csv",
    "knowledge_graph/type_selection/hgt20592_20635/selection_rules.csv",
    "knowledge_graph/type_selection/hgt20592_20635/warning_templates.csv",
    STANDARDS_SQLITE_PATH,
    "data/standard_facts_manifest.json",
    "equipment_selection_graph/equipment_selection_graph_v2.json",
    "equipment_selection_graph/00-authority-registry.md",
    "equipment_selection_graph/20-model-determination-card.md",
    "data/pump_gbt5662_2013_design_points.csv",
    "data/pipe_gbt12459_2025_dn_od_catalog.csv",
    "data/database_authority_registry.json",
    "data/database_contracts/standards_knowledge_public_schema.sql",
    "data/database_contracts/executable_standard_data_public_schema.sql",
    "app/schemas/equipment_design_agent_request.schema.json",
    "app/schemas/equipment_design_agent_response.schema.json",
    "app/schemas/equipment_design_authority_revision.schema.json",
    "app/schemas/equipment_design_source_code_manifest.schema.json",
    "app/schemas/equipment_design_presentation.schema.json",
    "app/schemas/equipment_design_report_status.schema.json",
    "app/schemas/equipment_design_llm_context_pack.schema.json",
    "app/schemas/equipment_design_llm_step_output.schema.json",
    "app/schemas/equipment_design_llm_prepared.schema.json",
    "app/schemas/equipment_design_llm_orchestration.schema.json",
    "app/schemas/equipment_design_hybrid_result.schema.json",
    "app/schemas/equipment_customer_output_profiles.schema.json",
    "app/schemas/equipment_customer_delivery_bundle.schema.json",
    "app/schemas/equipment_overview_table.schema.json",
    "app/schemas/equipment_family_datasheet.schema.json",
    "app/schemas/equipment_evidence_index.schema.json",
    "app/schemas/equipment_database_authority_registry.schema.json",
}
SQLITE_COUNT_TABLES = (
    "documents",
    "chunks",
    "tables_data",
    "figures_data",
    "formulas_data",
)


class RuntimeBundleError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def _absolute_without_resolving_links(path: Path) -> Path:
    """Return a normalized absolute path while preserving a short/junction path.

    The release builder may intentionally enter the project through a short
    junction to stay below the legacy Windows path limit.  ``Path.resolve()``
    expands that junction back to the long source path, after which deep
    standards-audit files can silently disappear from traversal.  ``abspath``
    normalizes ``.``/``..`` without changing the caller-visible root.
    """

    return Path(os.path.abspath(os.fspath(path.expanduser())))


def _is_link_or_junction(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    return bool(is_junction and is_junction())


def _walk_regular_files(root: Path) -> Iterable[Path]:
    pending = [root]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            ordered = sorted(entries, key=lambda entry: entry.name.casefold())
        child_directories: list[Path] = []
        for entry in ordered:
            path = Path(entry.path)
            if _is_link_or_junction(path):
                continue
            if entry.is_dir(follow_symlinks=False):
                child_directories.append(path)
            elif entry.is_file(follow_symlinks=False):
                yield path
        # LIFO traversal with reversed insertion preserves ascending order.
        pending.extend(reversed(child_directories))


def _runtime_files(root: Path) -> Iterable[tuple[str, Path]]:
    absolute_root = _absolute_without_resolving_links(root)
    for relative_root in RUNTIME_ROOTS:
        asset_root = absolute_root / Path(relative_root)
        if not asset_root.is_dir() or _is_link_or_junction(asset_root):
            continue
        for path in _walk_regular_files(asset_root):
            try:
                relative = path.relative_to(absolute_root).as_posix()
            except ValueError:
                continue
            yield relative, path


def _asset_class(relative: str) -> str:
    if relative.startswith("knowledge_graph/standards_graph/"):
        return "design_standards"
    if relative.startswith("knowledge_graph/"):
        return "equipment_core"
    if relative.startswith("equipment_selection_graph/"):
        return "equipment_model_authority"
    if relative.startswith("app/schemas/"):
        return "protocol_schemas"
    if relative.startswith("data/"):
        return "deterministic_data"
    return "unclassified"


def _sqlite_status(path: Path) -> dict[str, Any]:
    if path.name == "standard_facts.sqlite.gz":
        try:
            from projected_standard_store import verification
            return verification(path.parents[1])
        except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
            return {"status": "FAILED", "quick_check": None, "counts": {}, "error": str(exc)}
    if not path.is_file():
        return {"status": "MISSING", "quick_check": None, "counts": {}}
    uri = f"file:{path.as_posix()}?mode=ro"
    try:
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            quick_check = str(connection.execute("PRAGMA quick_check").fetchone()[0])
            counts = {
                table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
                for table in SQLITE_COUNT_TABLES
            }
    except (sqlite3.Error, OSError) as exc:
        return {
            "status": "FAILED",
            "quick_check": None,
            "counts": {},
            "error": str(exc),
        }
    return {
        "status": "PASS" if quick_check.casefold() == "ok" else "FAILED",
        "quick_check": quick_check,
        "counts": counts,
    }


def _records(root: Path) -> list[dict[str, Any]]:
    return [
        {
            "runtime_path": relative,
            "asset_class": _asset_class(relative),
            "size_bytes": int(path.stat().st_size),
            "sha256": sha256_file(path),
        }
        for relative, path in _runtime_files(root)
    ]


def create_manifest(root: Path, output: Path | None = None) -> dict[str, Any]:
    root = _absolute_without_resolving_links(root)
    output = _absolute_without_resolving_links(output or root / MANIFEST_NAME)
    records = _records(root)
    paths = {item["runtime_path"] for item in records}
    missing = sorted(REQUIRED_RUNTIME_PATHS - paths)
    if missing:
        raise RuntimeBundleError(f"runtime bundle is missing required assets: {missing}")
    sqlite_status = _sqlite_status(root / STANDARDS_SQLITE_PATH)
    if sqlite_status.get("status") != "PASS":
        raise RuntimeBundleError(f"standards SQLite validation failed: {sqlite_status}")
    package_counts: dict[str, int] = {}
    package_sizes: dict[str, int] = {}
    for record in records:
        asset_class = str(record["asset_class"])
        package_counts[asset_class] = package_counts.get(asset_class, 0) + 1
        package_sizes[asset_class] = package_sizes.get(asset_class, 0) + int(record["size_bytes"])
    revision_basis = [
        {
            "runtime_path": item["runtime_path"],
            "size_bytes": item["size_bytes"],
            "sha256": item["sha256"],
        }
        for item in records
    ]
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "bundle_revision": _canonical_sha256(revision_basis),
        "runtime_roots": list(RUNTIME_ROOTS),
        "total_files": len(records),
        "total_size_bytes": sum(int(item["size_bytes"]) for item in records),
        "package_counts": dict(sorted(package_counts.items())),
        "package_size_bytes": dict(sorted(package_sizes.items())),
        "standards_sqlite": {
            "runtime_path": STANDARDS_SQLITE_PATH,
            **sqlite_status,
        },
        "coverage_definition": {
            "status_claim": "BACKEND_STRUCTURED_FACT_PROJECTION",
            "complete_requires": [
                "exact manifest path set, size and SHA-256 verification",
                "all registered runtime packages present",
                "SQLite PRAGMA quick_check=ok and frozen table counts unchanged",
                "all bundled CSV/Markdown/JSON audit and routing assets present",
            ],
            "included": [
                "equipment core Markdown/JSON/CSV",
                "authority model graph Markdown/JSON",
                "separately identified structured standard and figure facts; no full-text source carrier",
                "original calculation rules and source locator metadata",
                "deterministic pump data and all Agent/LLM/presentation schemas",
            ],
            "excluded_with_reason": {
                "png": "rendering duplicates; figure captions, page/bbox metadata and source hashes remain queryable in SQLite",
                "jsonl": "redundant extraction carrier superseded by the verified SQLite authority carrier",
                "parser_cache_or_temp": "non-canonical build/cache/quarantine material",
                "source_paragraphs": "not included; original source hashes and projection exclusions retained",
            },
            "not_claimed": [
                "embedded source PDFs",
                "embedded PNG visual crops",
                "automatic engineering-value promotion from retrieval hits",
            ],
        },
        "files": records,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def verify_runtime_bundle(root: Path, *, required: bool = False) -> dict[str, Any]:
    root = _absolute_without_resolving_links(root)
    manifest_path = root / MANIFEST_NAME
    if not manifest_path.is_file():
        return {
            "verification_status": "FAILED_MANIFEST_MISSING" if required else "NOT_APPLICABLE_SOURCE_TREE",
            "verified": not required,
            "required": required,
            "bundle_revision": None,
            "manifest_sha256": None,
            "manifest_path": str(manifest_path),
            "issues": ([{"code": "RUNTIME_MANIFEST_MISSING", "path": str(manifest_path)}] if required else []),
        }
    issues: list[dict[str, Any]] = []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        manifest = {}
        issues.append({"code": "RUNTIME_MANIFEST_INVALID", "message": str(exc)})
    if manifest.get("schema") != MANIFEST_SCHEMA:
        issues.append({"code": "RUNTIME_MANIFEST_SCHEMA_INVALID", "actual": manifest.get("schema")})
    if manifest.get("runtime_roots") != list(RUNTIME_ROOTS):
        issues.append({
            "code": "RUNTIME_MANIFEST_ROOTS_INVALID",
            "expected": list(RUNTIME_ROOTS),
            "actual": manifest.get("runtime_roots"),
        })
    expected_records = manifest.get("files")
    if not isinstance(expected_records, list) or not all(isinstance(item, dict) for item in expected_records):
        expected_records = []
        issues.append({"code": "RUNTIME_MANIFEST_FILES_INVALID"})
    expected_by_path: dict[str, dict[str, Any]] = {}
    for item in expected_records:
        relative = str(item.get("runtime_path", ""))
        if not relative or relative in expected_by_path or relative.startswith(("/", "\\")) or ".." in Path(relative).parts:
            issues.append({"code": "RUNTIME_MANIFEST_PATH_INVALID", "path": relative})
            continue
        size = item.get("size_bytes")
        digest = str(item.get("sha256", "")).upper()
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            issues.append({
                "code": "RUNTIME_MANIFEST_SIZE_INVALID",
                "path": relative,
                "actual": size,
            })
        if not SHA256_PATTERN.fullmatch(digest):
            issues.append({
                "code": "RUNTIME_MANIFEST_HASH_INVALID",
                "path": relative,
                "actual": item.get("sha256"),
            })
        if item.get("asset_class") != _asset_class(relative):
            issues.append({
                "code": "RUNTIME_MANIFEST_ASSET_CLASS_INVALID",
                "path": relative,
                "expected": _asset_class(relative),
                "actual": item.get("asset_class"),
            })
        expected_by_path[relative] = item
    required_missing_from_manifest = sorted(REQUIRED_RUNTIME_PATHS - set(expected_by_path))
    for relative in required_missing_from_manifest:
        issues.append({"code": "RUNTIME_REQUIRED_ASSET_UNMANIFESTED", "path": relative})
    actual_by_path = dict(_runtime_files(root))
    expected_paths = set(expected_by_path)
    actual_paths = set(actual_by_path)
    for relative in sorted(expected_paths - actual_paths):
        issues.append({"code": "RUNTIME_ASSET_MISSING", "path": relative})
    for relative in sorted(actual_paths - expected_paths):
        issues.append({"code": "RUNTIME_ASSET_UNMANIFESTED", "path": relative})
    for relative in sorted(expected_paths & actual_paths):
        expected = expected_by_path[relative]
        path = actual_by_path[relative]
        actual_size = int(path.stat().st_size)
        expected_size = expected.get("size_bytes")
        if not isinstance(expected_size, int) or isinstance(expected_size, bool):
            continue
        if actual_size != expected_size:
            issues.append({
                "code": "RUNTIME_ASSET_SIZE_MISMATCH",
                "path": relative,
                "expected": expected.get("size_bytes"),
                "actual": actual_size,
            })
            continue
        actual_hash = sha256_file(path)
        if actual_hash != str(expected.get("sha256", "")).upper():
            issues.append({
                "code": "RUNTIME_ASSET_HASH_MISMATCH",
                "path": relative,
                "expected": expected.get("sha256"),
                "actual": actual_hash,
            })
    revision_basis = [
        {
            "runtime_path": item.get("runtime_path"),
            "size_bytes": item.get("size_bytes"),
            "sha256": item.get("sha256"),
        }
        for item in expected_records
    ]
    actual_revision = _canonical_sha256(revision_basis)
    if actual_revision != manifest.get("bundle_revision"):
        issues.append({
            "code": "RUNTIME_BUNDLE_REVISION_MISMATCH",
            "expected": manifest.get("bundle_revision"),
            "actual": actual_revision,
        })
    if not SHA256_PATTERN.fullmatch(str(manifest.get("bundle_revision", "")).upper()):
        issues.append({
            "code": "RUNTIME_BUNDLE_REVISION_INVALID",
            "actual": manifest.get("bundle_revision"),
        })
    calculated_total_size = sum(
        int(item.get("size_bytes", 0))
        for item in expected_records
        if isinstance(item.get("size_bytes"), int) and not isinstance(item.get("size_bytes"), bool)
    )
    calculated_package_counts: dict[str, int] = {}
    calculated_package_sizes: dict[str, int] = {}
    for relative, item in expected_by_path.items():
        asset_class = _asset_class(relative)
        calculated_package_counts[asset_class] = calculated_package_counts.get(asset_class, 0) + 1
        size = item.get("size_bytes")
        if isinstance(size, int) and not isinstance(size, bool):
            calculated_package_sizes[asset_class] = calculated_package_sizes.get(asset_class, 0) + size
    manifest_summary_checks = (
        ("RUNTIME_MANIFEST_TOTAL_FILES_MISMATCH", manifest.get("total_files"), len(expected_records)),
        ("RUNTIME_MANIFEST_TOTAL_SIZE_MISMATCH", manifest.get("total_size_bytes"), calculated_total_size),
        (
            "RUNTIME_MANIFEST_PACKAGE_COUNTS_MISMATCH",
            manifest.get("package_counts"),
            dict(sorted(calculated_package_counts.items())),
        ),
        (
            "RUNTIME_MANIFEST_PACKAGE_SIZES_MISMATCH",
            manifest.get("package_size_bytes"),
            dict(sorted(calculated_package_sizes.items())),
        ),
    )
    for code, actual, expected in manifest_summary_checks:
        if actual != expected:
            issues.append({"code": code, "expected": expected, "actual": actual})
    coverage = manifest.get("coverage_definition", {})
    if not isinstance(coverage, dict) or coverage.get("status_claim") != "BACKEND_STRUCTURED_FACT_PROJECTION":
        issues.append({
            "code": "RUNTIME_MANIFEST_COVERAGE_INVALID",
            "actual": coverage.get("status_claim") if isinstance(coverage, dict) else coverage,
        })
    sqlite_status = _sqlite_status(root / STANDARDS_SQLITE_PATH)
    expected_sqlite = manifest.get("standards_sqlite", {})
    if sqlite_status.get("status") != "PASS":
        issues.append({"code": "RUNTIME_STANDARDS_SQLITE_FAILED", "detail": sqlite_status})
    if sqlite_status.get("counts") != expected_sqlite.get("counts"):
        issues.append({
            "code": "RUNTIME_STANDARDS_SQLITE_COUNTS_MISMATCH",
            "expected": expected_sqlite.get("counts"),
            "actual": sqlite_status.get("counts"),
        })
    verified = not issues
    return {
        "verification_status": "PASS" if verified else "FAILED",
        "verified": verified,
        "required": required,
        "bundle_revision": manifest.get("bundle_revision"),
        "manifest_sha256": sha256_file(manifest_path),
        "manifest_path": str(manifest_path),
        "total_files": manifest.get("total_files"),
        "total_size_bytes": manifest.get("total_size_bytes"),
        "package_counts": manifest.get("package_counts", {}),
        "package_size_bytes": manifest.get("package_size_bytes", {}),
        "coverage_definition": manifest.get("coverage_definition", {}),
        "standards_sqlite": sqlite_status,
        "issues": issues,
    }


def require_runtime_bundle(root: Path, *, required: bool) -> dict[str, Any]:
    verification = verify_runtime_bundle(root, required=required)
    if not verification.get("verified"):
        raise RuntimeBundleError(
            "runtime asset bundle verification failed: "
            + json.dumps(verification.get("issues", []), ensure_ascii=False)
        )
    return verification


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create or verify the packaged runtime asset manifest.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create")
    create.add_argument("--root", required=True)
    create.add_argument("--output")
    verify = subparsers.add_parser("verify")
    verify.add_argument("--root", required=True)
    verify.add_argument("--required", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "create":
        manifest = create_manifest(
            Path(args.root),
            Path(args.output) if args.output else None,
        )
        result = {
            "status": "PASS",
            "bundle_revision": manifest["bundle_revision"],
            "total_files": manifest["total_files"],
            "total_size_bytes": manifest["total_size_bytes"],
            "package_counts": manifest["package_counts"],
            "standards_sqlite": manifest["standards_sqlite"],
        }
    else:
        result = verify_runtime_bundle(Path(args.root), required=bool(args.required))
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("status") == "PASS" or result.get("verified") is True else 3


if __name__ == "__main__":
    raise SystemExit(main())
