from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = APP_DIR.parent
SCRIPTS_DIR = PACKAGE_ROOT / "scripts"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import build_public_rag_contract_bundle as rag_bundle


class PublicRagContractBundleTests(unittest.TestCase):
    def test_bundle_is_deterministic_and_contains_contracts_not_payloads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="equipment_rag_contract_") as directory:
            root = Path(directory)
            first_path = root / "first.zip"
            second_path = root / "second.zip"
            first = rag_bundle.build_public_rag_bundle(PACKAGE_ROOT, first_path)
            second = rag_bundle.build_public_rag_bundle(PACKAGE_ROOT, second_path)

            self.assertEqual(first["sha256"], second["sha256"])
            self.assertFalse(first["rag_database_payload_included"])
            with zipfile.ZipFile(first_path) as archive:
                names = set(archive.namelist())
                self.assertEqual(
                    len(names),
                    len(rag_bundle.PUBLIC_FILES) + 2,
                )
                self.assertIn("PUBLIC_RAG_BUNDLE_README.md", names)
                self.assertIn("public_rag_bundle_manifest.json", names)
                self.assertTrue(set(rag_bundle.PUBLIC_FILES).issubset(names))
                self.assertFalse(
                    any(
                        Path(name).suffix.casefold()
                        in rag_bundle.FORBIDDEN_PAYLOAD_SUFFIXES
                        for name in names
                    )
                )
                manifest = json.loads(
                    archive.read("public_rag_bundle_manifest.json")
                )
                self.assertEqual(
                    manifest["scope"],
                    "PUBLIC_RAG_CONTRACT_ONLY_NO_DATABASE_OR_COPYRIGHTED_TEXT",
                )
                self.assertEqual(
                    manifest["rag_authority"]["database_id"],
                    "standards_knowledge_authority",
                )
                for record in manifest["files"]:
                    payload = archive.read(record["relative_path"])
                    self.assertEqual(len(payload), record["size_bytes"])
                    self.assertEqual(
                        hashlib.sha256(payload).hexdigest().upper(),
                        record["sha256"],
                    )


if __name__ == "__main__":
    unittest.main()
