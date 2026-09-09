from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import sys
from contextlib import closing
from pathlib import Path, PurePosixPath
from typing import Any


REGISTRY_SCHEMA = "equipment-database-authority-registry-v1"
AUDIT_SCHEMA = "equipment-database-authority-audit-v1"
REGISTRY_RELATIVE_PATH = "data/database_authority_registry.json"
ACTIVE_STATUS = "ACTIVE"
KNOWN_STATUSES = {"ACTIVE", "QUARANTINED", "INVALID", "CANDIDATE"}
SHA256_PATTERN = re.compile(r"^[A-F0-9]{64}$")
SQL_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class DatabaseAuthorityError(RuntimeError):
    pass


def default_package_root() -> Path:
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        return Path(frozen_root).resolve()
    return Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _safe_runtime_path(root: Path, relative_path: Any, label: str) -> Path:
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise DatabaseAuthorityError(f"{label} must be a nonempty relative path")
    normalized = relative_path.replace("\\", "/")
    relative = PurePosixPath(normalized)
    if relative.is_absolute() or ".." in relative.parts:
        raise DatabaseAuthorityError(f"{label} escapes the package root: {relative_path}")
    if relative.parts and ":" in relative.parts[0]:
        raise DatabaseAuthorityError(f"{label} must not contain a drive prefix: {relative_path}")
    return root.joinpath(*relative.parts)


def _validate_table_contracts(value: Any, database_id: str) -> None:
    if not isinstance(value, dict):
        raise DatabaseAuthorityError(f"{database_id}.table_contracts must be an object")
    for table_name, contract in value.items():
        if (
            not isinstance(table_name, str)
            or not SQL_IDENTIFIER_PATTERN.fullmatch(table_name)
        ):
            raise DatabaseAuthorityError(f"{database_id} contains an invalid table name")
        if not isinstance(contract, dict):
            raise DatabaseAuthorityError(f"{database_id}.{table_name} contract must be an object")
        if set(contract) != {"row_count", "required_columns"}:
            raise DatabaseAuthorityError(
                f"{database_id}.{table_name} contract keys must be row_count and required_columns"
            )
        row_count = contract.get("row_count")
        columns = contract.get("required_columns")
        if not isinstance(row_count, int) or isinstance(row_count, bool) or row_count < 0:
            raise DatabaseAuthorityError(f"{database_id}.{table_name} row_count is invalid")
        if (
            not isinstance(columns, list)
            or not all(
                isinstance(column, str)
                and SQL_IDENTIFIER_PATTERN.fullmatch(column)
                for column in columns
            )
            or len(columns) != len(set(columns))
        ):
            raise DatabaseAuthorityError(
                f"{database_id}.{table_name} required_columns are invalid"
            )


def validate_registry(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DatabaseAuthorityError("database authority registry must be an object")
    required_top = {
        "schema",
        "revision",
        "policy",
        "consumers",
        "databases",
        "non_sql_catalogs",
    }
    if set(value) != required_top:
        raise DatabaseAuthorityError(
            "database authority registry top-level keys are invalid: "
            f"missing={sorted(required_top - set(value))}, "
            f"unknown={sorted(set(value) - required_top)}"
        )
    if value.get("schema") != REGISTRY_SCHEMA:
        raise DatabaseAuthorityError("database authority registry schema is invalid")
    if not isinstance(value.get("revision"), str) or not re.fullmatch(
        r"^20[0-9]{2}-[0-9]{2}-[0-9]{2}$",
        value["revision"],
    ):
        raise DatabaseAuthorityError("database authority registry revision is invalid")
    policy = value.get("policy")
    if not isinstance(policy, dict):
        raise DatabaseAuthorityError("database authority registry policy is invalid")
    if policy.get("active_database_resolution") != "registry_only":
        raise DatabaseAuthorityError("database resolution must be registry_only")
    if policy.get("access_mode") != "read_only":
        raise DatabaseAuthorityError("database access mode must be read_only")

    databases = value.get("databases")
    if not isinstance(databases, list) or not databases:
        raise DatabaseAuthorityError("database authority registry has no databases")
    database_map: dict[str, dict[str, Any]] = {}
    for record in databases:
        if not isinstance(record, dict):
            raise DatabaseAuthorityError("database record must be an object")
        required_record = {
            "database_id",
            "logical_role",
            "status",
            "scope_status",
            "runtime_use_allowed",
            "runtime_required",
            "relative_path",
            "manifest_relative_path",
            "build_id",
            "expected_size_bytes",
            "expected_sha256",
            "reason",
            "table_contracts",
        }
        if set(record) != required_record:
            database_id = str(record.get("database_id") or "unknown")
            raise DatabaseAuthorityError(
                f"{database_id} keys are invalid: "
                f"missing={sorted(required_record - set(record))}, "
                f"unknown={sorted(set(record) - required_record)}"
            )
        database_id = record.get("database_id")
        if not isinstance(database_id, str) or not database_id:
            raise DatabaseAuthorityError("database_id must be a nonempty string")
        if database_id in database_map:
            raise DatabaseAuthorityError(f"duplicate database_id: {database_id}")
        status = record.get("status")
        if status not in KNOWN_STATUSES:
            raise DatabaseAuthorityError(f"{database_id} has an invalid status: {status}")
        runtime_allowed = record.get("runtime_use_allowed")
        runtime_required = record.get("runtime_required")
        if not isinstance(runtime_allowed, bool) or not isinstance(runtime_required, bool):
            raise DatabaseAuthorityError(f"{database_id} runtime flags must be boolean")
        if status == ACTIVE_STATUS and not runtime_allowed:
            raise DatabaseAuthorityError(f"{database_id} is ACTIVE but runtime use is disabled")
        if status != ACTIVE_STATUS and runtime_allowed:
            raise DatabaseAuthorityError(
                f"{database_id} is {status} but runtime use is enabled"
            )
        expected_size = record.get("expected_size_bytes")
        expected_sha256 = record.get("expected_sha256")
        if (
            not isinstance(expected_size, int)
            or isinstance(expected_size, bool)
            or expected_size <= 0
        ):
            raise DatabaseAuthorityError(f"{database_id} expected size is invalid")
        if not isinstance(expected_sha256, str) or not SHA256_PATTERN.fullmatch(
            expected_sha256
        ):
            raise DatabaseAuthorityError(f"{database_id} expected SHA-256 is invalid")
        _safe_runtime_path(Path("."), record.get("relative_path"), f"{database_id}.relative_path")
        manifest_relative = record.get("manifest_relative_path")
        if manifest_relative is not None:
            _safe_runtime_path(
                Path("."),
                manifest_relative,
                f"{database_id}.manifest_relative_path",
            )
        _validate_table_contracts(record.get("table_contracts"), database_id)
        database_map[database_id] = record

    consumers = value.get("consumers")
    if not isinstance(consumers, list) or not consumers:
        raise DatabaseAuthorityError("database authority registry has no consumers")
    consumer_ids: set[str] = set()
    bound_database_ids: set[str] = set()
    for consumer in consumers:
        if not isinstance(consumer, dict):
            raise DatabaseAuthorityError("database consumer must be an object")
        required_consumer = {
            "consumer_id",
            "database_id",
            "code_path",
            "access_mode",
            "allowed_scope",
            "required_dataset_ids",
        }
        if set(consumer) != required_consumer:
            raise DatabaseAuthorityError("database consumer keys are invalid")
        consumer_id = consumer.get("consumer_id")
        database_id = consumer.get("database_id")
        if not isinstance(consumer_id, str) or not consumer_id:
            raise DatabaseAuthorityError("consumer_id must be a nonempty string")
        if consumer_id in consumer_ids:
            raise DatabaseAuthorityError(f"duplicate consumer_id: {consumer_id}")
        consumer_ids.add(consumer_id)
        record = database_map.get(str(database_id))
        if record is None:
            raise DatabaseAuthorityError(
                f"{consumer_id} references an unknown database: {database_id}"
            )
        if record.get("status") != ACTIVE_STATUS or not record.get("runtime_use_allowed"):
            raise DatabaseAuthorityError(
                f"{consumer_id} is bound to non-active database {database_id}"
            )
        if consumer.get("access_mode") != "read_only":
            raise DatabaseAuthorityError(f"{consumer_id} access mode must be read_only")
        required_dataset_ids = consumer.get("required_dataset_ids")
        if (
            not isinstance(required_dataset_ids, list)
            or not all(
                isinstance(dataset_id, str) and dataset_id
                for dataset_id in required_dataset_ids
            )
            or len(required_dataset_ids) != len(set(required_dataset_ids))
        ):
            raise DatabaseAuthorityError(
                f"{consumer_id} required_dataset_ids are invalid"
            )
        bound_database_ids.add(str(database_id))

    unbound_active = {
        database_id
        for database_id, record in database_map.items()
        if record.get("status") == ACTIVE_STATUS and database_id not in bound_database_ids
    }
    if unbound_active:
        raise DatabaseAuthorityError(
            f"active databases have no declared consumer: {sorted(unbound_active)}"
        )
    if not isinstance(value.get("non_sql_catalogs"), list):
        raise DatabaseAuthorityError("non_sql_catalogs must be an array")
    return value


def load_registry(package_root: Path | None = None) -> dict[str, Any]:
    root = (package_root or default_package_root()).resolve()
    registry_path = _safe_runtime_path(root, REGISTRY_RELATIVE_PATH, "registry path")
    try:
        value = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DatabaseAuthorityError(
            f"cannot load database authority registry: {registry_path}"
        ) from exc
    return validate_registry(value)


def _database_map(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(record["database_id"]): record
        for record in registry["databases"]
    }


def declared_database_for_consumer(
    consumer_id: str,
    package_root: Path | None = None,
) -> dict[str, Any]:
    root = (package_root or default_package_root()).resolve()
    registry = load_registry(root)
    binding = next(
        (
            consumer
            for consumer in registry["consumers"]
            if consumer.get("consumer_id") == consumer_id
        ),
        None,
    )
    if not isinstance(binding, dict):
        raise DatabaseAuthorityError(f"unknown database consumer: {consumer_id}")
    record = _database_map(registry)[str(binding["database_id"])]
    if record.get("status") != ACTIVE_STATUS or not record.get("runtime_use_allowed"):
        raise DatabaseAuthorityError(
            f"consumer {consumer_id} is bound to forbidden database "
            f"{record.get('database_id')} ({record.get('status')})"
        )
    database_path = _safe_runtime_path(
        root,
        record["relative_path"],
        f"{record['database_id']}.relative_path",
    )
    manifest_path = None
    if record.get("manifest_relative_path"):
        manifest_path = _safe_runtime_path(
            root,
            record["manifest_relative_path"],
            f"{record['database_id']}.manifest_relative_path",
        )
    return {
        "registry": registry,
        "binding": binding,
        "database": record,
        "database_path": database_path,
        "manifest_path": manifest_path,
    }


def verify_database_record(
    record: dict[str, Any],
    package_root: Path,
    *,
    required_dataset_ids: list[str] | None = None,
) -> dict[str, Any]:
    root = package_root.resolve()
    database_id = str(record["database_id"])
    if record.get("status") != ACTIVE_STATUS or not record.get("runtime_use_allowed"):
        raise DatabaseAuthorityError(
            f"runtime verification forbidden for {database_id} ({record.get('status')})"
        )
    database_path = _safe_runtime_path(
        root,
        record["relative_path"],
        f"{database_id}.relative_path",
    )
    if not database_path.is_file():
        raise DatabaseAuthorityError(f"database is missing: {record['relative_path']}")
    actual_size = int(database_path.stat().st_size)
    if actual_size != record["expected_size_bytes"]:
        raise DatabaseAuthorityError(
            f"{database_id} size mismatch: "
            f"expected={record['expected_size_bytes']}, actual={actual_size}"
        )
    actual_sha256 = sha256_file(database_path)
    if actual_sha256 != record["expected_sha256"]:
        raise DatabaseAuthorityError(
            f"{database_id} SHA-256 mismatch: "
            f"expected={record['expected_sha256']}, actual={actual_sha256}"
        )

    uri = f"file:{database_path.resolve().as_posix()}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as connection:
        quick_check = str(connection.execute("PRAGMA quick_check").fetchone()[0])
        if quick_check != "ok":
            raise DatabaseAuthorityError(
                f"{database_id} SQLite quick_check failed: {quick_check}"
            )
        actual_tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        table_counts: dict[str, int] = {}
        for table_name, contract in record["table_contracts"].items():
            if table_name not in actual_tables:
                raise DatabaseAuthorityError(
                    f"{database_id} is missing required table {table_name}"
                )
            actual_columns = {
                str(row[1])
                for row in connection.execute(f'PRAGMA table_info("{table_name}")')
            }
            missing_columns = set(contract["required_columns"]) - actual_columns
            if missing_columns:
                raise DatabaseAuthorityError(
                    f"{database_id}.{table_name} is missing columns "
                    f"{sorted(missing_columns)}"
                )
            row_count = int(
                connection.execute(
                    f'SELECT COUNT(*) FROM "{table_name}"'
                ).fetchone()[0]
            )
            if row_count != contract["row_count"]:
                raise DatabaseAuthorityError(
                    f"{database_id}.{table_name} row count mismatch: "
                    f"expected={contract['row_count']}, actual={row_count}"
                )
            table_counts[table_name] = row_count

        dataset_status: dict[str, dict[str, Any]] = {}
        for dataset_id in required_dataset_ids or []:
            if "datasets" not in actual_tables:
                raise DatabaseAuthorityError(
                    f"{database_id} cannot validate dataset {dataset_id}: "
                    "datasets table is missing"
                )
            cursor = connection.execute(
                "SELECT dataset_id, lifecycle_state, reuse_class, qa_status, "
                "record_count, build_id FROM datasets WHERE dataset_id = ?",
                (dataset_id,),
            )
            columns = [item[0] for item in cursor.description]
            row = cursor.fetchone()
            if row is None:
                raise DatabaseAuthorityError(
                    f"{database_id} is missing required dataset {dataset_id}"
                )
            dataset = dict(zip(columns, row))
            if (
                dataset.get("lifecycle_state") != "CURRENT"
                or dataset.get("reuse_class") != "DIRECT_REUSE_VERIFIED"
                or dataset.get("qa_status") != "VERIFIED"
            ):
                raise DatabaseAuthorityError(
                    f"{database_id} dataset {dataset_id} is not promoted for "
                    "bounded direct reuse"
                )
            dataset_status[dataset_id] = dataset

    manifest_status: dict[str, Any] | None = None
    manifest_relative = record.get("manifest_relative_path")
    if manifest_relative:
        manifest_path = _safe_runtime_path(
            root,
            manifest_relative,
            f"{database_id}.manifest_relative_path",
        )
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DatabaseAuthorityError(
                f"{database_id} build manifest cannot be loaded"
            ) from exc
        if manifest.get("build_id") != record["build_id"]:
            raise DatabaseAuthorityError(
                f"{database_id} build_id mismatch: "
                f"expected={record['build_id']}, actual={manifest.get('build_id')}"
            )
        manifest_sha = str(manifest.get("sqlite_sha256") or "").upper()
        if manifest_sha != actual_sha256:
            raise DatabaseAuthorityError(
                f"{database_id} build manifest SQLite SHA-256 mismatch"
            )
        manifest_status = {
            "relative_path": manifest_relative,
            "build_id": manifest.get("build_id"),
            "sqlite_sha256": manifest_sha,
        }

    return {
        "database_id": database_id,
        "status": "VERIFIED_ACTIVE_READ_ONLY",
        "scope_status": record["scope_status"],
        "relative_path": record["relative_path"],
        "size_bytes": actual_size,
        "sha256": actual_sha256,
        "quick_check": "ok",
        "table_counts": table_counts,
        "required_datasets": dataset_status,
        "manifest": manifest_status,
    }


def verify_consumer_database(
    consumer_id: str,
    package_root: Path | None = None,
) -> dict[str, Any]:
    root = (package_root or default_package_root()).resolve()
    declaration = declared_database_for_consumer(consumer_id, root)
    verification = verify_database_record(
        declaration["database"],
        root,
        required_dataset_ids=list(
            declaration["binding"].get("required_dataset_ids") or []
        ),
    )
    return {
        "schema": AUDIT_SCHEMA,
        "consumer_id": consumer_id,
        "code_path": declaration["binding"]["code_path"],
        "access_mode": declaration["binding"]["access_mode"],
        "allowed_scope": declaration["binding"]["allowed_scope"],
        **verification,
    }


def audit_active_databases(package_root: Path | None = None) -> dict[str, Any]:
    root = (package_root or default_package_root()).resolve()
    registry = load_registry(root)
    results = [
        verify_consumer_database(str(consumer["consumer_id"]), root)
        for consumer in registry["consumers"]
    ]
    return {
        "schema": AUDIT_SCHEMA,
        "status": "PASS",
        "registry_schema": registry["schema"],
        "registry_revision": registry["revision"],
        "active_consumer_count": len(results),
        "results": results,
    }


def registry_inventory(package_root: Path | None = None) -> dict[str, Any]:
    root = (package_root or default_package_root()).resolve()
    registry = load_registry(root)
    return {
        "schema": AUDIT_SCHEMA,
        "status": "INVENTORY_ONLY",
        "registry_schema": registry["schema"],
        "registry_revision": registry["revision"],
        "consumers": registry["consumers"],
        "databases": [
            {
                "database_id": record["database_id"],
                "logical_role": record["logical_role"],
                "status": record["status"],
                "scope_status": record["scope_status"],
                "runtime_use_allowed": record["runtime_use_allowed"],
                "runtime_required": record["runtime_required"],
                "relative_path": record["relative_path"],
                "build_id": record["build_id"],
                "expected_size_bytes": record["expected_size_bytes"],
                "expected_sha256": record["expected_sha256"],
                "reason": record["reason"],
                "tables": sorted(record["table_contracts"]),
            }
            for record in registry["databases"]
        ],
        "non_sql_catalogs": registry["non_sql_catalogs"],
    }
