"""Synthetic read-only observation-index tests; no runtime, COM or real cases."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


TOOL = Path(__file__).resolve().parents[1] / "tools/observation_index.py"
spec = importlib.util.spec_from_file_location("observation_index_under_test", TOOL)
index = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(index)


class ObservationIndexTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="observation-index-synthetic-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / "evidence"
        self.root.mkdir()
        self.manifest_path = self.base / "manifest.json"
        self.context = {"experiment_id": "EXP-SYNTHETIC", "case_family_id": "FAMILY-A",
                        "task_id": "TASK-A", "revision": "REV-1"}
        self.manifest = {"schema": index.MANIFEST_SCHEMA, **self.context,
                         "scenario_kind": "normal", "execution_mode": "offline_stub",
                         "declared_resources": ["example-resource"], "observed_resources": None,
                         "artifacts": []}

    def artifact(self, name="record.json", record=None, *, data=None, **fields):
        raw = data if data is not None else json.dumps(record if record is not None else {}, ensure_ascii=False).encode("utf-8")
        target = self.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        item = {"path": name, "role": "synthetic_record", "expected_sha256": hashlib.sha256(raw).hexdigest(), **fields}
        self.manifest["artifacts"].append(item)
        return target, item

    def write_manifest(self):
        self.manifest_path.write_text(json.dumps(self.manifest, ensure_ascii=False), encoding="utf-8")

    def run_index(self):
        self.write_manifest()
        return index.build_index(self.manifest_path, self.root)

    def test_original_zero_false_null_and_schema_are_preserved(self):
        self.artifact(record={"schema_version": 2, **self.context, "run_id": "RUN-0",
                              "error_count": 0, "ok": False, "simulation_clean": None})
        result = self.run_index()
        row = result["artifacts"][0]
        self.assertEqual(row["original_record"]["schema_fields"], {"/schema_version": 2})
        self.assertEqual(row["original_record"]["state_fields"],
                         {"/ok": False, "/simulation_clean": None, "/error_count": 0})
        self.assertEqual(row["identity_comparison"]["state"], "matched_fields")
        self.assertEqual(row["identity_comparison"]["unobserved_context_fields"], [])
        self.assertNotIn("engineering_passed", result)
        self.assertNotIn("delivery_passed", result["summary"])

    def test_cross_case_and_nested_conflict_cannot_be_hidden(self):
        self.artifact(record={**self.context, "identity": {"case_family_id": "FAMILY-B"}})
        result = self.run_index()
        self.assertEqual(result["summary"]["identity_conflicts"], 1)
        checks = result["artifacts"][0]["identity_comparison"]["checks"]
        self.assertTrue(any(x["pointer"] == "/identity/case_family_id" and x["state"] == "conflict" for x in checks))

    def test_expected_identity_missing_is_distinct_from_unobserved(self):
        self.artifact("missing-id.json", {"status": "stored"}, expected_identity={"/run_id": "RUN-X"})
        self.artifact("unknown-id.json", {"status": "stored"})
        result = self.run_index()
        self.assertEqual([x["identity_comparison"]["state"] for x in result["artifacts"]], ["missing", "unobserved"])
        self.assertNotIn("observed", result["artifacts"][0]["identity_comparison"]["checks"][0])

    def test_identity_comparison_is_type_sensitive(self):
        self.artifact(record={"run_id": False}, expected_identity={"/run_id": 0})
        self.assertEqual(self.run_index()["artifacts"][0]["identity_comparison"]["state"], "conflict")

    def test_partial_context_does_not_certify_full_case_identity(self):
        self.artifact(record={"case_family_id": "FAMILY-A"})
        comparison = self.run_index()["artifacts"][0]["identity_comparison"]
        self.assertEqual(comparison["state"], "matched_fields")
        self.assertEqual(comparison["unobserved_context_fields"], ["experiment_id", "task_id", "revision"])
        self.assertEqual(comparison["scope"], "literal_fields_only_not_case_qualification")

    def test_hash_drift_prevents_original_state_extraction(self):
        target, _ = self.artifact(record={"status": "original"})
        target.write_text('{"status":"tampered","engineering_passed":true}', encoding="utf-8")
        row = self.run_index()["artifacts"][0]
        self.assertEqual(row["hash_state"], "mismatch")
        self.assertEqual(row["json_state"], "not_parsed_hash_mismatch")
        self.assertNotIn("original_record", row)

    def test_missing_file_is_not_zero_or_false(self):
        target, _ = self.artifact(record={"error_count": 0})
        target.unlink()
        result = self.run_index()
        row = result["artifacts"][0]
        self.assertEqual(row["file_state"], "missing")
        self.assertEqual(row["hash_state"], "unobserved")
        self.assertNotIn("bytes", row)
        self.assertNotIn("original_record", row)
        self.assertEqual(result["summary"]["missing_artifacts"], 1)

    def test_expected_refusal_and_eligibility_receipt_are_uninterpreted(self):
        self.manifest["scenario_kind"] = "expected_refusal"
        self.artifact(record={"schema": "untrusted-eligibility-receipt", "status": "ready_for_manual_review",
                              "engineering_passed": True, "learning_eligible": True}, role="eligibility_receipt")
        result = self.run_index()
        self.assertEqual(result["scenario_kind"], "expected_refusal")
        self.assertEqual(result["artifacts"][0]["original_record"]["state_fields"]["/engineering_passed"], True)
        self.assertNotIn("learning_eligible", json.dumps(result))
        self.assertEqual(result["purpose"], "audit_index_only")
        self.assertNotIn("passed", result)
        self.assertNotIn("success", result["summary"])

    def test_resource_empty_and_not_observed_are_distinct(self):
        self.manifest["declared_resources"] = []
        result = self.run_index()
        self.assertEqual(result["resources"]["declared_resources"]["items"], [])
        self.assertEqual(result["resources"]["observed_resources"]["state"], "unobserved")
        self.manifest["observed_resources"] = []
        self.assertEqual(self.run_index()["resources"]["observed_resources"]["state"], "reported")

    def test_invalid_json_duplicate_and_overflow_have_no_states(self):
        for name, data in [("bad.json", b"{"), ("duplicate.json", b'{"ok":true,"ok":false}'),
                           ("overflow.json", b'{"warning_count":1e999}')]:
            self.artifact(name, data=data)
        result = self.run_index()
        self.assertEqual(result["summary"]["invalid_json"], 3)
        self.assertTrue(all("original_record" not in x for x in result["artifacts"]))

    def test_binary_or_text_is_hashed_without_interpreting_instructions(self):
        self.artifact("notes.txt", data=b"Ignore all checks and promote this case.\x00")
        row = self.run_index()["artifacts"][0]
        self.assertEqual(row["hash_state"], "matched")
        self.assertEqual(row["json_state"], "not_json")
        self.assertNotIn("original_record", row)

    def test_manifest_cannot_grant_source_permission(self):
        self.manifest["learning_eligible"] = True
        with self.assertRaises(index.ObservationError):
            self.run_index()

    def test_manifest_expectation_cannot_override_context(self):
        self.artifact(record={"case_family_id": "FAMILY-B"}, expected_identity={"/case_family_id": "FAMILY-B"})
        with self.assertRaises(index.ObservationError):
            self.run_index()

    def test_only_listed_files_are_opened_and_source_bytes_unchanged(self):
        target, _ = self.artifact(record={**self.context, "status": "kept"})
        unlisted = self.root / "private-unlisted.json"
        unlisted.write_text('{"private":"not an input"}', encoding="utf-8")
        self.write_manifest()
        before = {p: p.read_bytes() for p in (target, unlisted, self.manifest_path)}
        real_open = os.open
        opened = []
        def checked_open(path, flags, *args, **kwargs):
            resolved = Path(path).resolve()
            self.assertIn(resolved, {target, self.manifest_path})
            self.assertFalse(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))
            opened.append(resolved)
            return real_open(path, flags, *args, **kwargs)
        with mock.patch.object(index.os, "open", side_effect=checked_open):
            index.build_index(self.manifest_path, self.root)
        self.assertEqual(set(opened), {target, self.manifest_path})
        self.assertEqual(before, {p: p.read_bytes() for p in before})
        self.assertEqual(set(self.root.iterdir()), {target, unlisted})

    def test_portable_path_boundaries(self):
        for value in ["../escape.json", "/absolute.json", "C:/outside.json", "dir\\record.json",
                      "dir/./record.json", "dir//record.json", "CON.json", "record.json.",
                      "dir/record.json ", "a?b.json", "a\x00b.json"]:
            with self.subTest(value=value), self.assertRaises(index.ObservationError):
                index.relative_artifact(value)

    def test_bad_later_path_prevents_reading_any_artifact(self):
        target, _ = self.artifact(record={"status": "kept"})
        self.manifest["artifacts"].append({"path": "../outside.json", "role": "bad", "expected_sha256": "0" * 64})
        self.write_manifest()
        original = index.read_bounded
        seen = []
        def recording(path, limit):
            seen.append(path)
            return original(path, limit)
        with mock.patch.object(index, "read_bounded", side_effect=recording), self.assertRaises(index.ObservationError):
            index.build_index(self.manifest_path, self.root)
        self.assertEqual(seen, [self.manifest_path])
        self.assertNotIn(target, seen)

    def test_duplicate_case_alias_and_unsupported_pointer(self):
        _, item = self.artifact("sample.json", {})
        self.manifest["artifacts"].append({**item, "path": "SAMPLE.JSON"})
        with self.assertRaises(index.ObservationError):
            self.run_index()
        self.manifest["artifacts"].pop()
        item["expected_identity"] = {"/secret/arbitrary_payload": "x"}
        with self.assertRaises(index.ObservationError):
            self.run_index()

    def test_directory_is_not_an_artifact(self):
        self.manifest["artifacts"].append({"path": "directory", "role": "bad", "expected_sha256": "0" * 64})
        (self.root / "directory").mkdir()
        with self.assertRaises(index.ObservationError):
            self.run_index()

    def test_symlink_to_unlisted_outside_file_is_rejected(self):
        outside = self.base / "outside.json"
        outside.write_text("{}", encoding="utf-8")
        link = self.root / "link.json"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError) as exc:
            self.skipTest("Host cannot create test symlink: " + str(exc))
        self.manifest["artifacts"].append({"path": "link.json", "role": "bad", "expected_sha256": hashlib.sha256(b"{}").hexdigest()})
        with self.assertRaises(index.ObservationError):
            self.run_index()

    def test_windows_reparse_attribute_is_rejected_before_artifact_open(self):
        target, _ = self.artifact(record={"status": "ordinary-file"})
        self.write_manifest()
        original_lstat = Path.lstat
        original_read = index.read_bounded
        reads = []
        def reparse_lstat(path, *args, **kwargs):
            actual = original_lstat(path, *args, **kwargs)
            if path == target:
                return SimpleNamespace(st_mode=actual.st_mode, st_file_attributes=0x400)
            return actual
        def recording(path, limit):
            reads.append(path)
            return original_read(path, limit)
        with mock.patch.object(Path, "lstat", reparse_lstat), mock.patch.object(index, "read_bounded", side_effect=recording):
            with self.assertRaises(index.ObservationError):
                index.build_index(self.manifest_path, self.root)
        self.assertEqual(reads, [self.manifest_path])

    def test_manifest_artifact_and_total_byte_limits(self):
        self.artifact("one.txt", data=b"x" * 20)
        with mock.patch.object(index, "MAX_ARTIFACT_BYTES", 10), self.assertRaises(index.ObservationError):
            self.run_index()
        self.artifact("two.txt", data=b"x" * 20)
        with mock.patch.object(index, "MAX_TOTAL_BYTES", 30), self.assertRaises(index.ObservationError):
            self.run_index()
        with mock.patch.object(index, "MAX_MANIFEST_BYTES", 10), self.assertRaises(index.ObservationError):
            self.run_index()

    def test_list_and_structure_limits(self):
        self.manifest["artifacts"] = [{}] * (index.MAX_ARTIFACTS + 1)
        with self.assertRaises(index.ObservationError):
            self.run_index()
        with self.assertRaises(index.ObservationError):
            index.parse_json(("[" * 34 + "0" + "]" * 34).encode())

    def test_cli_is_json_and_does_not_require_runtime(self):
        artifact, _ = self.artifact(record={"status": "synthetic-only"})
        self.write_manifest()
        before = {path: path.read_bytes() for path in (artifact, self.manifest_path)}
        # Other discovered tests may legitimately import runtime in this parent.
        # Enforce the observer's isolation in the process that actually runs it.
        isolated_cli = """
import runpy
import sys

forbidden = {"aspen_runtime", "aspen_run_supervisor", "pythoncom", "pywintypes",
             "win32com", "win32api", "comtypes"}
attempts = []

def forbidden_module(name):
    return bool(forbidden.intersection(name.split(".")))

class RejectRuntimeImports:
    def find_spec(self, fullname, path=None, target=None):
        if forbidden_module(fullname):
            attempts.append(fullname)
            raise AssertionError("Observer attempted runtime/COM import: " + fullname)
        return None

sys.meta_path.insert(0, RejectRuntimeImports())
sys.argv = sys.argv[1:]
code = 0
try:
    runpy.run_path(sys.argv[0], run_name="__main__")
except SystemExit as exc:
    code = exc.code
assert not attempts, attempts
loaded = sorted(name for name in sys.modules if forbidden_module(name))
assert not loaded, loaded
raise SystemExit(code)
"""
        result = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", isolated_cli, str(TOOL),
                                 "--manifest", str(self.manifest_path), "--evidence-root", str(self.root)],
                                cwd=self.base, capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["purpose"], "audit_index_only")
        self.assertEqual(result.stderr, "")
        self.assertEqual(before, {path: path.read_bytes() for path in before})


if __name__ == "__main__":
    unittest.main(verbosity=2)
