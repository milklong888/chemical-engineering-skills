from __future__ import annotations

import contextlib
import copy
import json
import shutil
import sqlite3
import sys
import unittest
import uuid
from pathlib import Path
from unittest import mock


APP_DIR = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = APP_DIR.parent
SCRIPTS_DIR = PACKAGE_ROOT / "scripts"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import database_authority
import app_core


@contextlib.contextmanager
def writable_temp_directory():
    root = APP_DIR / "tests" / f"_database_authority_test_{uuid.uuid4().hex}"
    root.mkdir(parents=False, exist_ok=False)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _create_verified_fixture(root: Path) -> dict:
    database_path = root / "database.sqlite"
    manifest_path = root / "build_manifest.json"
    with contextlib.closing(sqlite3.connect(database_path)) as connection:
        connection.execute(
            """
            CREATE TABLE datasets(
                dataset_id TEXT PRIMARY KEY,
                lifecycle_state TEXT NOT NULL,
                reuse_class TEXT NOT NULL,
                qa_status TEXT NOT NULL,
                record_count INTEGER NOT NULL,
                build_id TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO datasets(
                dataset_id, lifecycle_state, reuse_class, qa_status,
                record_count, build_id
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "verified_fixture",
                "CURRENT",
                "DIRECT_REUSE_VERIFIED",
                "VERIFIED",
                1,
                "fixture-build",
            ),
        )
        connection.execute(
            """
            CREATE TABLE standard_records(
                dataset_id TEXT NOT NULL,
                record_id TEXT PRIMARY KEY,
                record_sha256 TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "INSERT INTO standard_records VALUES (?, ?, ?)",
            ("verified_fixture", "row-1", "A" * 64),
        )
        connection.commit()

    database_sha256 = database_authority.sha256_file(database_path)
    manifest_path.write_text(
        json.dumps(
            {
                "build_id": "fixture-build",
                "sqlite_sha256": database_sha256,
            }
        ),
        encoding="utf-8",
    )
    return {
        "database_id": "fixture_database",
        "logical_role": "test",
        "status": "ACTIVE",
        "scope_status": "FIXTURE_ONLY",
        "runtime_use_allowed": True,
        "runtime_required": True,
        "relative_path": "database.sqlite",
        "manifest_relative_path": "build_manifest.json",
        "build_id": "fixture-build",
        "expected_size_bytes": database_path.stat().st_size,
        "expected_sha256": database_sha256,
        "reason": "test fixture",
        "table_contracts": {
            "datasets": {
                "row_count": 1,
                "required_columns": [
                    "dataset_id",
                    "lifecycle_state",
                    "reuse_class",
                    "qa_status",
                    "record_count",
                    "build_id",
                ],
            },
            "standard_records": {
                "row_count": 1,
                "required_columns": [
                    "dataset_id",
                    "record_id",
                    "record_sha256",
                ],
            },
        },
    }


class DatabaseAuthorityTests(unittest.TestCase):
    def test_registry_names_one_active_database_for_each_consumer(self) -> None:
        registry = database_authority.load_registry(PACKAGE_ROOT)
        records = {
            str(item["database_id"]): item for item in registry["databases"]
        }
        bindings = {
            str(item["consumer_id"]): item for item in registry["consumers"]
        }

        self.assertEqual(
            bindings["standards_knowledge_search"]["database_id"],
            "standards_knowledge_authority",
        )
        self.assertEqual(
            bindings["pipe_standard_store"]["database_id"],
            "executable_standard_data_current",
        )
        self.assertIn(
            "build_20260720_visual_batch_v2",
            records["executable_standard_data_current"]["relative_path"],
        )
        self.assertFalse(
            records["executable_standard_data_reconciled_legacy"][
                "runtime_use_allowed"
            ]
        )
        self.assertEqual(
            records["executable_standard_data_reconciled_legacy"]["status"],
            "QUARANTINED",
        )
        self.assertFalse(
            records["gbt17261_delta_v2_candidate"]["runtime_use_allowed"]
        )

    def test_fixture_database_passes_full_read_only_contract(self) -> None:
        with writable_temp_directory() as root:
            record = _create_verified_fixture(root)
            result = database_authority.verify_database_record(
                record,
                root,
                required_dataset_ids=["verified_fixture"],
            )

        self.assertEqual(result["status"], "VERIFIED_ACTIVE_READ_ONLY")
        self.assertEqual(result["quick_check"], "ok")
        self.assertEqual(result["table_counts"]["datasets"], 1)
        self.assertEqual(
            result["required_datasets"]["verified_fixture"]["qa_status"],
            "VERIFIED",
        )

    def test_hash_replacement_and_non_active_database_fail_closed(self) -> None:
        with writable_temp_directory() as root:
            record = _create_verified_fixture(root)
            wrong_hash = copy.deepcopy(record)
            wrong_hash["expected_sha256"] = "B" * 64
            with self.assertRaisesRegex(
                database_authority.DatabaseAuthorityError,
                "SHA-256 mismatch",
            ):
                database_authority.verify_database_record(wrong_hash, root)

            quarantined = copy.deepcopy(record)
            quarantined["status"] = "QUARANTINED"
            quarantined["runtime_use_allowed"] = False
            with self.assertRaisesRegex(
                database_authority.DatabaseAuthorityError,
                "verification forbidden",
            ):
                database_authority.verify_database_record(quarantined, root)

    def test_registry_rejects_path_escape_and_inactive_consumer_binding(self) -> None:
        registry = database_authority.load_registry(PACKAGE_ROOT)

        escaped = copy.deepcopy(registry)
        escaped["databases"][0]["relative_path"] = "../outside.sqlite"
        with self.assertRaisesRegex(
            database_authority.DatabaseAuthorityError,
            "escapes the package root",
        ):
            database_authority.validate_registry(escaped)

        inactive_binding = copy.deepcopy(registry)
        inactive_binding["consumers"][1]["database_id"] = (
            "executable_standard_data_reconciled_legacy"
        )
        with self.assertRaisesRegex(
            database_authority.DatabaseAuthorityError,
            "bound to non-active database",
        ):
            database_authority.validate_registry(inactive_binding)

    def test_pipe_consumer_source_has_no_quarantined_build_path(self) -> None:
        source = (
            PACKAGE_ROOT / "scripts" / "aspen_equipment_derivation.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("build_20260720_reconciled", source)
        self.assertIn("PIPE_STANDARD_CONSUMER_ID", source)
        self.assertIn("verify_consumer_database", source)

    def test_public_sql_contracts_are_executable_and_create_business_tables(self) -> None:
        expected = {
            "standards_knowledge_public_schema.sql": {
                "documents",
                "chunks",
                "tables_data",
                "figures_data",
                "formulas_data",
            },
            "executable_standard_data_public_schema.sql": {
                "datasets",
                "standard_records",
                "figure_datasets",
                "figure_records",
            },
        }
        contract_root = PACKAGE_ROOT / "data" / "database_contracts"
        for filename, expected_tables in expected.items():
            with self.subTest(filename=filename):
                with contextlib.closing(sqlite3.connect(":memory:")) as connection:
                    connection.executescript(
                        (contract_root / filename).read_text(encoding="utf-8")
                    )
                    actual_tables = {
                        str(row[0])
                        for row in connection.execute(
                            "SELECT name FROM sqlite_master WHERE type='table'"
                        )
                    }
                self.assertTrue(expected_tables.issubset(actual_tables))

    def test_rag_authority_failure_is_public_in_search_response(self) -> None:
        selected = [
            {
                "id": "design_standards",
                "root": PACKAGE_ROOT / "missing-rag-root",
                "limitations": "fixture",
            }
        ]
        with (
            mock.patch.object(
                app_core,
                "_selected_knowledge_packages",
                return_value=selected,
            ),
            mock.patch.object(
                app_core,
                "_standards_sqlite_search",
                side_effect=database_authority.DatabaseAuthorityError(
                    "fixture authority failure"
                ),
            ),
            mock.patch.object(app_core, "FROZEN_ROOT", "fixture"),
        ):
            result = app_core.knowledge_search(
                "pump",
                package_ids=["design_standards"],
            )

        self.assertEqual(
            result["standards_database_authority"]["status"],
            "BLOCKED_DATABASE_AUTHORITY",
        )
        self.assertIn(
            "fixture authority failure",
            result["standards_database_authority"]["error"],
        )

    @unittest.skipUnless(
        (
            PACKAGE_ROOT
            / "knowledge_graph"
            / "standards_graph"
            / "executable_data"
            / "build_20260720_visual_batch_v2"
            / "executable_store"
            / "executable_standard_data.sqlite"
        ).is_file(),
        "large release database is intentionally not stored in Git",
    )
    def test_current_pipe_database_payload_matches_public_registry(self) -> None:
        result = database_authority.verify_consumer_database(
            "pipe_standard_store",
            PACKAGE_ROOT,
        )
        self.assertEqual(result["status"], "VERIFIED_ACTIVE_READ_ONLY")
        self.assertEqual(
            set(result["required_datasets"]),
            {
                "gbt1048_nominal_pressure_series",
                "gbt17395_pipe_dimensions_weights",
            },
        )


if __name__ == "__main__":
    unittest.main()
