from __future__ import annotations

import contextlib
import json
import sqlite3
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import runtime_bundle


@contextlib.contextmanager
def writable_temp_directory():
    # Use the system temp root because the current executable-database build
    # path is intentionally descriptive and can exceed legacy Windows MAX_PATH
    # when nested under this repository's long Chinese workspace path.
    with tempfile.TemporaryDirectory(
        prefix=f"equipment_runtime_bundle_{uuid.uuid4().hex}_"
    ) as directory:
        yield Path(directory)


def _create_standards_sqlite(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with contextlib.closing(sqlite3.connect(path)) as connection:
        for table in runtime_bundle.SQLITE_COUNT_TABLES:
            connection.execute(f"CREATE TABLE {table}(record_id TEXT PRIMARY KEY)")
            connection.execute(f"INSERT INTO {table}(record_id) VALUES (?)", (f"{table}-1",))
        connection.commit()


def _create_minimum_bundle(root: Path) -> None:
    for relative in sorted(runtime_bundle.REQUIRED_RUNTIME_PATHS):
        path = root / Path(relative)
        if relative == runtime_bundle.STANDARDS_SQLITE_PATH:
            _create_standards_sqlite(path)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix.casefold() == ".json":
            payload = "{}\n"
        elif path.suffix.casefold() == ".csv":
            payload = "key,value\nfixture,1\n"
        else:
            payload = "# runtime fixture\n"
        path.write_text(payload, encoding="utf-8")


class RuntimeBundleTests(unittest.TestCase):
    def test_manifest_traversal_preserves_caller_visible_root(self) -> None:
        with writable_temp_directory() as root:
            _create_minimum_bundle(root)
            with mock.patch.object(
                Path,
                "resolve",
                side_effect=AssertionError("runtime bundle traversal must not resolve links"),
            ):
                runtime_bundle.create_manifest(root)
                verification = runtime_bundle.verify_runtime_bundle(root, required=True)

        self.assertEqual(verification["verification_status"], "PASS", verification)

    def test_create_and_verify_exact_bundle(self) -> None:
        with writable_temp_directory() as root:
            _create_minimum_bundle(root)
            manifest = runtime_bundle.create_manifest(root)
            verification = runtime_bundle.verify_runtime_bundle(root, required=True)

        self.assertEqual(verification["verification_status"], "PASS", verification)
        self.assertTrue(verification["verified"])
        self.assertEqual(len(verification["bundle_revision"]), 64)
        self.assertEqual(len(verification["manifest_sha256"]), 64)
        self.assertEqual(manifest["coverage_definition"]["status_claim"], "COMPLETE_QUERYABLE_COMPACT_BUNDLE")
        self.assertEqual(
            manifest["standards_sqlite"]["counts"],
            {table: 1 for table in runtime_bundle.SQLITE_COUNT_TABLES},
        )

    def test_same_size_asset_tamper_fails_closed(self) -> None:
        with writable_temp_directory() as root:
            _create_minimum_bundle(root)
            runtime_bundle.create_manifest(root)
            target = root / "knowledge_graph" / "equipment_match_rules.json"
            original = target.read_bytes()
            target.write_bytes(b"X" * len(original))
            verification = runtime_bundle.verify_runtime_bundle(root, required=True)

        self.assertFalse(verification["verified"])
        self.assertIn(
            "RUNTIME_ASSET_HASH_MISMATCH",
            {item["code"] for item in verification["issues"]},
        )

    def test_unmanifested_asset_and_manifest_record_removal_fail(self) -> None:
        with writable_temp_directory() as root:
            _create_minimum_bundle(root)
            runtime_bundle.create_manifest(root)
            extra = root / "data" / "unexpected.csv"
            extra.write_text("unexpected\n", encoding="utf-8")
            extra_verification = runtime_bundle.verify_runtime_bundle(root, required=True)
            extra.unlink()

            manifest_path = root / runtime_bundle.MANIFEST_NAME
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            removed_path = "app/schemas/equipment_design_agent_request.schema.json"
            manifest["files"] = [
                item for item in manifest["files"] if item["runtime_path"] != removed_path
            ]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            removed_verification = runtime_bundle.verify_runtime_bundle(root, required=True)

        self.assertIn(
            "RUNTIME_ASSET_UNMANIFESTED",
            {item["code"] for item in extra_verification["issues"]},
        )
        self.assertIn(
            "RUNTIME_REQUIRED_ASSET_UNMANIFESTED",
            {item["code"] for item in removed_verification["issues"]},
        )

    def test_missing_manifest_is_only_allowed_for_source_tree(self) -> None:
        with writable_temp_directory() as root:
            source = runtime_bundle.verify_runtime_bundle(root, required=False)
            frozen = runtime_bundle.verify_runtime_bundle(root, required=True)

        self.assertTrue(source["verified"])
        self.assertEqual(source["verification_status"], "NOT_APPLICABLE_SOURCE_TREE")
        self.assertFalse(frozen["verified"])
        self.assertEqual(frozen["verification_status"], "FAILED_MANIFEST_MISSING")


if __name__ == "__main__":
    unittest.main()
