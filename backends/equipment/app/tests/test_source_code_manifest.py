from __future__ import annotations

import contextlib
import json
import shutil
import sys
import unittest
import uuid
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = APP_DIR.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import source_code_manifest


@contextlib.contextmanager
def isolated_source_tree():
    root = APP_DIR / "tests" / f"_source_manifest_test_{uuid.uuid4().hex}"
    source_root = root / "source"
    snapshot_root = root / "snapshot"
    source_root.mkdir(parents=True, exist_ok=False)
    for relative in source_code_manifest.CORE_SOURCE_PATHS:
        source = PACKAGE_ROOT / Path(relative)
        destination = source_root / Path(relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    try:
        yield source_root, snapshot_root
    finally:
        shutil.rmtree(root, ignore_errors=True)


class SourceCodeManifestTests(unittest.TestCase):
    def test_source_and_exact_packaged_snapshot_verify(self) -> None:
        with isolated_source_tree() as (source_root, snapshot_root):
            manifest_path = source_root / "app" / source_code_manifest.MANIFEST_NAME
            manifest = source_code_manifest.create_manifest(
                source_root,
                output=manifest_path,
                snapshot_root=snapshot_root,
            )
            source = source_code_manifest.verify_manifest(
                source_root,
                manifest_path=manifest_path,
                exact_path_set=False,
                status="SOURCE_TREE_VERIFIED",
            )
            frozen = source_code_manifest.verify_manifest(
                snapshot_root,
                manifest_path=manifest_path,
                exact_path_set=True,
                status="PACKAGED_SNAPSHOT_VERIFIED",
            )
            self.assertTrue(source["verified"], source)
            self.assertTrue(frozen["verified"], frozen)
            self.assertEqual(source["source_code_sha256"], frozen["source_code_sha256"])
            self.assertEqual(
                manifest["source_code_set_sha256"],
                source["source_code_set_sha256"],
            )
            self.assertEqual(
                set(source["source_code_sha256"]),
                set(source_code_manifest.CORE_SOURCE_PATHS),
            )

    def test_missing_or_tampered_manifest_fails(self) -> None:
        with isolated_source_tree() as (source_root, _snapshot_root):
            manifest_path = source_root / "app" / source_code_manifest.MANIFEST_NAME
            missing = source_code_manifest.verify_manifest(
                source_root,
                manifest_path=manifest_path,
                exact_path_set=False,
                status="SOURCE_TREE_VERIFIED",
            )
            self.assertFalse(missing["verified"])
            self.assertEqual(missing["verification_status"], "FAILED_MANIFEST_MISSING")

            source_code_manifest.create_manifest(source_root, output=manifest_path)
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            payload["files"][0]["sha256"] = "A" * 64
            manifest_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            tampered = source_code_manifest.verify_manifest(
                source_root,
                manifest_path=manifest_path,
                exact_path_set=False,
                status="SOURCE_TREE_VERIFIED",
            )
            self.assertFalse(tampered["verified"])
            self.assertEqual(tampered["verification_status"], "FAILED_MANIFEST_INVALID")

    def test_source_change_fails_without_regenerating_manifest(self) -> None:
        with isolated_source_tree() as (source_root, _snapshot_root):
            manifest_path = source_root / "app" / source_code_manifest.MANIFEST_NAME
            source_code_manifest.create_manifest(source_root, output=manifest_path)
            changed_relative = source_code_manifest.CORE_SOURCE_PATHS[-1]
            changed_path = source_root / Path(changed_relative)
            changed_path.write_text(
                changed_path.read_text(encoding="utf-8") + "\n# test drift\n",
                encoding="utf-8",
            )
            verification = source_code_manifest.verify_manifest(
                source_root,
                manifest_path=manifest_path,
                exact_path_set=False,
                status="SOURCE_TREE_VERIFIED",
            )
            self.assertFalse(verification["verified"])
            codes = {item["code"] for item in verification["issues"]}
            self.assertIn("SOURCE_CODE_FILE_HASH_MISMATCH", codes)

    def test_packaged_snapshot_missing_changed_or_extra_file_fails(self) -> None:
        with isolated_source_tree() as (source_root, snapshot_root):
            manifest_path = source_root / "app" / source_code_manifest.MANIFEST_NAME
            source_code_manifest.create_manifest(
                source_root,
                output=manifest_path,
                snapshot_root=snapshot_root,
            )
            missing_path = snapshot_root / Path(source_code_manifest.CORE_SOURCE_PATHS[0])
            missing_path.unlink()
            extra_path = snapshot_root / "extra.py"
            extra_path.write_text("x = 1\n", encoding="utf-8")
            changed_path = snapshot_root / Path(source_code_manifest.CORE_SOURCE_PATHS[1])
            changed_path.write_text("# changed\n", encoding="utf-8")
            verification = source_code_manifest.verify_manifest(
                snapshot_root,
                manifest_path=manifest_path,
                exact_path_set=True,
                status="PACKAGED_SNAPSHOT_VERIFIED",
            )
            self.assertFalse(verification["verified"])
            codes = {item["code"] for item in verification["issues"]}
            self.assertIn("SOURCE_CODE_FILE_MISSING", codes)
            self.assertIn("SOURCE_CODE_FILE_EXTRA", codes)
            self.assertIn("SOURCE_CODE_FILE_HASH_MISMATCH", codes)

    def test_workspace_manifest_is_current(self) -> None:
        verification = source_code_manifest.verify_current_runtime(
            PACKAGE_ROOT,
            frozen=False,
        )
        self.assertTrue(verification["verified"], verification)
        self.assertEqual(verification["status"], "SOURCE_TREE_VERIFIED")


if __name__ == "__main__":
    unittest.main()
