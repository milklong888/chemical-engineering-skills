"""Persistent exact-scope history used by the independent delivery review."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from tools.review_scope_history import SCOPE_HISTORY, ScopeHistoryError, check_scope, remember_scope


class ScopeHistoryTests(unittest.TestCase):
    def setUp(self):
        work = TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.root = Path(work.name)
        self.pressure = self.put("pressure.json", {"pressure": 140})
        self.report = self.put("report.txt", "Frozen report")
        self.basis = {"scope": ["pressure", "report"], "scope_evidence": {"pressure": self.pressure, "report": [self.report]}}

    def put(self, name, value):
        if isinstance(value, dict):
            value = json.dumps(value, ensure_ascii=False, sort_keys=True)
        raw = value.encode("utf-8") if isinstance(value, str) else value
        (self.root / name).write_bytes(raw)
        return {"path": name, "sha256": hashlib.sha256(raw).hexdigest()}

    def request(self, revision="R1", basis=None, *, case="P", name=None, run="run-1"):
        basis = self.basis if basis is None else basis
        identity = {"case_id": case, "task_revision": revision, "run_id": run}
        authority = self.put(name or f"{case}-{revision}.json", {**identity, "delivery_review": basis})
        return self.root, identity, basis, authority

    def assert_rejected(self, args, code):
        with self.assertRaises(ScopeHistoryError) as found:
            remember_scope(*args)
        self.assertEqual(found.exception.code, code)

    def assert_needs(self, result, code):
        self.assertEqual(result["status"], "ACTION_REQUIRED")
        self.assertEqual([row["code"] for row in result["needs"]], [code])

    def test_read_only_status_without_preregistered_scope(self):
        self.assertEqual(check_scope(self.root, {"case_id": "P"}, None, None)["status"], "NOT_APPLICABLE")
        self.assert_needs(check_scope(*self.request()), "DELIVERY_SCOPE_HISTORY_REQUIRED")
        self.assertFalse((self.root / SCOPE_HISTORY).exists())

    def test_same_revision_scope_removal_or_replacement_cannot_rewrite_history(self):
        original = remember_scope(*self.request())
        for item in ("pressure", "solvent quality"):
            altered = {"scope": [item], "scope_evidence": {item: self.pressure}}
            args = self.request(basis=altered)
            self.assert_rejected(args, "DELIVERY_SCOPE_REVISION_DRIFT")
            self.assert_needs(check_scope(*args), "DELIVERY_SCOPE_REVISION_DRIFT")
        restored = self.request()
        self.assertEqual(check_scope(*restored)["snapshot_id"], original["snapshot_id"])
        self.assert_needs(check_scope(self.root, restored[1], None, None), "DELIVERY_SCOPE_REMOVED")
        self.assertEqual(check_scope(self.root, {"case_id": "OTHER"}, None, None)["status"], "NOT_APPLICABLE")

    def test_same_revision_wrong_file_and_mutated_original_are_distinct(self):
        original = self.request()
        remember_scope(*original)
        replacing = self.put("easier.json", {"pressure_limit": 90})
        altered = {**self.basis, "scope_evidence": {**self.basis["scope_evidence"], "pressure": replacing}}
        self.assert_rejected(self.request(basis=altered), "DELIVERY_SCOPE_REVISION_DRIFT")
        original = self.request()
        self.put("pressure.json", {"pressure": 170})
        self.assert_needs(check_scope(*original), "DELIVERY_SCOPE_ORIGINAL_CHANGED")

    def test_revision_retains_scope_and_accepts_new_exact_same_path_readback(self):
        first = self.request()
        original = remember_scope(*first)
        new = self.put("pressure.json", {"pressure": 141})
        revised = {**self.basis, "scope_evidence": {**self.basis["scope_evidence"], "pressure": new}}
        current = self.request("R2", revised, run="run-2")
        saved = remember_scope(*current)
        self.assertEqual(saved["scope_parents"], [original["snapshot_id"]])
        self.assertEqual(check_scope(*current)["status"], "SCOPE_HISTORY_CHECKED")
        self.assert_needs(check_scope(*first), "DELIVERY_SCOPE_REVISION_STALE")

    def test_same_scope_fork_and_identical_file_rename_inherit_without_approval(self):
        saved = remember_scope(*self.request())
        equal = self.put("copied-report.txt", "Frozen report")
        fork = {**self.basis, "scope_branch": "process-work", "scope_parents": [saved["snapshot_id"]],
                "scope_evidence": {**self.basis["scope_evidence"], "report": [equal]}}
        args = self.request("fork-1", fork)
        self.assertEqual(remember_scope(*args)["scope_parents"], fork["scope_parents"])
        self.assertEqual(check_scope(*args)["status"], "SCOPE_HISTORY_CHECKED")
        self.assertEqual(check_scope(*self.request())["status"], "SCOPE_HISTORY_CHECKED")

    def test_unapproved_reduction_does_not_disappear_through_revision_or_branch(self):
        saved = remember_scope(*self.request())
        reduced = {"scope": ["report"], "scope_evidence": {"report": self.report}}
        self.assert_rejected(self.request("R2", reduced), "DELIVERY_SCOPE_CHANGE_UNAPPROVED")
        branch = {**reduced, "scope_branch": "new-branch"}
        self.assert_rejected(self.request("branch-1", branch), "DELIVERY_SCOPE_CHANGE_UNAPPROVED")
        branch["scope_parents"] = [saved["snapshot_id"]]
        self.assert_rejected(self.request("branch-1", branch), "DELIVERY_SCOPE_CHANGE_UNAPPROVED")

    def test_merge_preserves_scope_from_each_current_parent(self):
        main = remember_scope(*self.request())
        control = self.put("control.txt", "Control test results")
        expanded = {"scope": [*self.basis["scope"], "control"],
                    "scope_evidence": {**self.basis["scope_evidence"], "control": control}}
        fork = remember_scope(*self.request("fork-1", {**expanded, "scope_branch": "controls",
                                                        "scope_parents": [main["snapshot_id"]]}))
        parents = [main["snapshot_id"], fork["snapshot_id"]]
        self.assert_rejected(self.request("merge-1", {**self.basis, "scope_parents": parents}),
                             "DELIVERY_SCOPE_CHANGE_UNAPPROVED")
        current = self.request("merge-1", {**expanded, "scope_parents": parents})
        self.assertEqual(remember_scope(*current)["scope_parents"], sorted(parents))
        self.assertEqual(check_scope(*current)["status"], "SCOPE_HISTORY_CHECKED")

    def test_proven_rebinding_is_a_technical_revision_without_fresh_user_approval(self):
        saved = remember_scope(*self.request())
        new = self.put("pressure-summary-v2.json", {"pressure": 142})
        basis = {**self.basis, "scope_parents": [saved["snapshot_id"]],
                 "scope_evidence": {"pressure": new, "report": self.report}}
        self.assert_rejected(self.request("R2", basis), "DELIVERY_SCOPE_REBINDING_REQUIRED")
        excerpt = "R2 preserves the outlet pressure test and records it in pressure-summary-v2.json."
        source = self.put("change-offset.json", {"case_id": "P", "task_revision": "R2", "passage": excerpt})
        row = {"schema": "delivery-scope-revision-v1", "case_id": "P", "task_revision": "R2", "scope_branch": "main",
               **basis, "reason": "Version the same pressure calculation output", "source_ref": source, "source_excerpt": excerpt,
               "rebindings": [{"parent_snapshot_id": saved["snapshot_id"], "scope": "pressure", "from": self.pressure, "to": new}]}
        basis["scope_revision_ref"] = self.put("scope-technical-revision.json", row)
        args = self.request("R2", basis)
        self.assertEqual(remember_scope(*args)["scope_revision_ref"], basis["scope_revision_ref"])
        self.assertEqual(check_scope(*args)["status"], "SCOPE_HISTORY_CHECKED")

    def test_sourced_explicit_reduction_keeps_original_scope_and_approval(self):
        saved = remember_scope(*self.request(name="authority.json"))
        reduced = {"scope": ["report"], "scope_evidence": {"report": [self.report]}, "scope_parents": [saved["snapshot_id"]]}
        excerpt = "P R2 deliver the report only. Release the previously required pressure assessment."
        approval = self.put("approval.json", {"case_id": "P", "task_revision": "R2", "user_message": excerpt})
        reduced["scope_decision_ref"] = self.put("scope-decision.json", {"schema": "delivery-scope-decision-v1", "case_id": "P",
            "task_revision": "R2", "scope_branch": "main", **reduced, "decision": "approved", "approved_by": "project owner",
            "reason": "User directed a report-only handover", "approval_source_ref": approval, "approval_excerpt": excerpt})
        current = self.request("R2", reduced, name="authority.json")
        remember_scope(*current)
        with closing(sqlite3.connect(self.root / SCOPE_HISTORY)) as db:
            previous = db.execute("SELECT content FROM originals WHERE sha256=?", (saved["authority_ref"]["sha256"],)).fetchone()[0]
            self.assertEqual(json.loads(previous)["delivery_review"]["scope"], ["pressure", "report"])
            self.assertIsNotNone(db.execute("SELECT content FROM originals WHERE sha256=?", (approval["sha256"],)).fetchone())
        self.assertEqual(check_scope(*current)["status"], "SCOPE_HISTORY_CHECKED")

    def test_each_scope_requires_all_originals_even_with_supplemental_evidence(self):
        basis = {**self.basis, "scope_evidence": {"pressure": [self.pressure, self.report], "report": self.report}}
        args = self.request(basis=basis)
        remember_scope(*args)
        checks = [{"scope": scope, "evidence_ref": ref} for scope, ref in [("pressure", self.pressure), ("report", self.report)]]
        self.assert_needs(check_scope(*args, final_checks=checks), "DELIVERY_SCOPE_FINAL_EVIDENCE_MISSING")
        checks.append({"scope": "pressure", "evidence_ref": self.report})
        self.assertEqual(check_scope(*args, final_checks=checks)["status"], "SCOPE_HISTORY_CHECKED")

    def test_concurrent_same_revision_is_idempotent_and_conflicting_freezes_are_serialized(self):
        first = self.request(name="first.json")
        substitute = {"scope": ["report"], "scope_evidence": {"report": self.report}}
        competitor = self.request(basis=substitute, name="second.json")
        def write(args):
            try:
                return remember_scope(*args)["snapshot_id"]
            except ScopeHistoryError as exc:
                return exc.code
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(write, [first, competitor] * 4))
        self.assertEqual(results.count("DELIVERY_SCOPE_REVISION_DRIFT"), 4)
        self.assertEqual(len(set(results)), 2)
        with closing(sqlite3.connect(self.root / SCOPE_HISTORY)) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM snapshots").fetchone()[0], 1)

    def test_large_binary_is_hash_checked_without_duplication_in_the_database(self):
        binary = self.put("plant.bkp", b"\x93\x4a\x00\x8f" * (1024 * 1024))
        args = self.request(basis={"scope": ["native model"], "scope_evidence": {"native model": binary}})
        saved = remember_scope(*args)
        self.assertEqual(saved["scope_evidence"]["native model"], [binary])
        database = self.root / SCOPE_HISTORY
        self.assertLess(database.stat().st_size, 128 * 1024)
        with closing(sqlite3.connect(database)) as db:
            self.assertIsNone(db.execute("SELECT 1 FROM originals WHERE sha256=?", (binary["sha256"],)).fetchone())
        self.assertEqual(check_scope(*args)["status"], "SCOPE_HISTORY_CHECKED")
        self.put("plant.bkp", b"different bytes")
        self.assert_needs(check_scope(*args), "DELIVERY_SCOPE_ORIGINAL_CHANGED")
