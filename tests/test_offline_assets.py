"""Release-level binary and runtime placement regressions; synthetic artifacts."""
import gzip
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import verify_release as v
import install as installer


def encoded(value):
    return (json.dumps(value) + "\n").encode()


class BinaryTests(unittest.TestCase):
    def database(self):
        raw = b"SQLite format 3\x00" + b"SYNTHETIC HEADER TEST; NOT AN ACTUAL DATABASE"
        data = gzip.compress(raw, mtime=0)
        row = {"path": "backends/equipment/data/synthetic.sqlite.gz", "kind": "sqlite_gzip",
               "sha256": v.sha256(data), "bytes": len(data), "uncompressed_sha256": v.sha256(raw),
               "uncompressed_bytes": len(raw), "source_ledger": "backends/equipment/data/synthetic.json",
               "redistribution_basis": "synthetic test bytes", "review_status": "admitted"}
        payload = {row["path"]: data, row["source_ledger"]: b"{}"}
        payload[v.BINARY_LEDGER] = encoded({"schema": "chemical-reviewed-binary-assets-v1", "assets": [row]})
        return payload, row

    def test_explicit_database_identity(self):
        payload, row = self.database()
        self.assertEqual(list(v.binary_policy(payload)), [row["path"]])

    def test_database_compressed_tamper(self):
        payload, row = self.database()
        payload[row["path"]] += b"changed"
        with self.assertRaises(v.ReleaseError):
            v.binary_policy(payload)

    def test_database_expanded_tamper(self):
        payload, row = self.database()
        row["uncompressed_sha256"] = "0" * 64
        payload[v.BINARY_LEDGER] = encoded({"schema": "chemical-reviewed-binary-assets-v1", "assets": [row]})
        with self.assertRaises(v.ReleaseError):
            v.binary_policy(payload)

    def test_unlisted_binary_is_not_ordinary_text(self):
        with self.assertRaises(v.ReleaseError):
            v.public_text("knowledge/unknown.sqlite", b"SQLite format 3\x00")

    def test_bom_csv_preserves_original_bytes(self):
        data = b"\xef\xbb\xbf" + "id,值\nA,1\n".encode()
        self.assertTrue(v.public_text("data/table.csv", data).startswith("id"))
        with self.assertRaises(v.ReleaseError):
            v.public_text("data/config.json", b"\xef\xbb\xbf{}")

    def test_ddl_is_reviewed_text_not_automatic_execution(self):
        self.assertIn("CREATE", v.public_text("data/schema.sql", b"CREATE TABLE example(id INTEGER);"))

    def test_wheel_needs_matching_lock(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as wheel:
            wheel.writestr("demo-1.0.dist-info/METADATA", "Name: demo\nVersion: 1.0\n")
        data = stream.getvalue()
        row = {"path": "runtime/wheelhouse/demo-1.0-py3-none-any.whl", "kind": "python_wheel",
               "sha256": v.sha256(data), "bytes": len(data), "source_ledger": "vendor/demo/lock.json",
               "redistribution_basis": "synthetic wheel", "review_status": "admitted"}
        payload = {row["path"]: data, row["source_ledger"]: encoded({"wheels": []}),
                   v.BINARY_LEDGER: encoded({"schema": "chemical-reviewed-binary-assets-v1", "assets": [row]})}
        with self.assertRaisesRegex(v.ReleaseError, "lock"):
            v.binary_policy(payload)
        payload[row["source_ledger"]] = encoded({"wheels": [{"filename": Path(row["path"]).name,
            "sha256": row["sha256"], "bytes": len(data)}]})
        self.assertEqual(len(v.binary_policy(payload)), 1)

    def test_object_numpy_rejected_even_if_ledger_claims_float(self):
        header = b"{'descr': '|O', 'fortran_order': False, 'shape': (1,)}\n"
        data = b"\x93NUMPY\x01\x00" + len(header).to_bytes(2, "little") + header + b"pickle"
        row = {"path": "knowledge/vectors/x.npy", "kind": "numpy_index", "dtype": "float32",
               "allow_pickle": False, "shape": [1], "sha256": v.sha256(data), "bytes": len(data),
               "source_ledger": "knowledge/config.json", "redistribution_basis": "synthetic", "review_status": "admitted"}
        payload = {row["path"]: data, row["source_ledger"]: b"{}",
                   v.BINARY_LEDGER: encoded({"schema": "chemical-reviewed-binary-assets-v1", "assets": [row]})}
        with self.assertRaisesRegex(v.ReleaseError, "floating"):
            v.binary_policy(payload)

    def test_worktree_git_file_not_published(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".git").write_text("gitdir: private checkout metadata")
            (root / "README.md").write_text("synthetic")
            self.assertEqual(set(v.inventory(root)), {"README.md"})

    def test_installer_keeps_hash_vector_dependency_raw(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            repo, workspace, skills = base / "release", base / "work", base / "skills"
            files = {
                v.SKILLS_PREFIX + "aspen-plus-operations/SKILL.md": b"---\nname: aspen-plus-operations\ndescription: Synthetic test only.\n---\n{CHEM_WORKSPACE}\n",
                v.PLUGIN + "/.codex-plugin/plugin.json": encoded({"name": "chemical-engineering-skills", "version": "0-test", "description": "synthetic", "skills": "./skills/"}),
                "workspace/scripts/retrieval_routes.json": b'{"root":"{CHEM_WORKSPACE}"}',
                "tools/install.py": (ROOT / "tools/install.py").read_bytes(),
                "tools/verify_release.py": (ROOT / "tools/verify_release.py").read_bytes(),
                installer.RUNTIME_VALIDATOR_SOURCE: b'"""synthetic parser identity fixture"""\n',
            }
            for relative, data in files.items():
                path = repo / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            manifest, sums = v.make_manifest(repo, release_name="synthetic", release_version="0", expected_skill_count=1)
            (repo / v.MANIFEST).write_bytes(manifest)
            (repo / v.CHECKSUMS).write_bytes(sums)
            result = installer.install(repo, workspace, skills)
            raw = workspace / "chemical-engineering-runtime/workspace/scripts/retrieval_routes.json"
            self.assertEqual(raw.read_bytes(), files["workspace/scripts/retrieval_routes.json"])
            self.assertNotEqual(raw.read_bytes(), (workspace / "scripts/retrieval_routes.json").read_bytes())
            self.assertEqual(result["status"], "installed")
            validator = workspace / "chemical-engineering-runtime/validators/aspen_evidence.py"
            self.assertEqual(validator.read_bytes(), files[installer.RUNTIME_VALIDATOR_SOURCE])


if __name__ == "__main__":
    unittest.main(verbosity=2)
