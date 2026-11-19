"""Replay old SQLite grants without treating them as current publication authority."""
from contextlib import closing
import copy
import sqlite3
import unittest

import test_task_closeout_history as fixtures
from backends.process.feedback import canonical_sha
from tools.task_closeout_history import HISTORY, _digest, _json, advance_closeout


class LegacyUploadAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.history = fixtures.TaskCloseoutHistoryTests()
        self.history.setUp()
        self.addCleanup(self.history.doCleanups)
        self.root = self.history.root
        self.fixture = self.history.fixture
        self.history.close()
        self.args = self.fixture.retrospective_args()
        self.table = self.history.run_event("retrospective", **self.args)

    def register_legacy_grant(self, state, quote, *, presentation=None):
        original = copy.deepcopy(state)
        batch = original["batch"]
        message = self.fixture.msg(quote, 4)
        grant = {"row_sha256": canonical_sha(batch["rows"]["A"]), "batch_sha256": batch["sha256"],
                 "message_ref": message, "source_message_id": "4"}
        if presentation is not None:
            grant["presentation"] = presentation
        batch["authorizations"]["A"] = grant
        original["publication_approval_messages"]["4"] = {
            "message_sha256": message["sha256"], "batch_sha256": batch["sha256"]
        }
        with closing(sqlite3.connect(self.root / HISTORY)) as db, db:
            db.execute("UPDATE task_heads SET state=?, state_sha256=? WHERE task_id=?",
                       (_json(original), _digest(original), original["task_id"]))
        return original, grant

    def test_old_grant_without_display_stays_audit_only_and_new_approval_works(self):
        original, grant = self.register_legacy_grant(self.table, "A 未批准上传。")
        original_ref = self.fixture.put("old-receipt.json", original)
        with closing(sqlite3.connect(self.root / HISTORY)) as db:
            projection = self.history.run_event("status", previous_ref=original_ref)
            self.assertEqual(db.execute("SELECT state FROM task_heads").fetchone()[0], _json(original))
        self.assertEqual(projection["batch"]["authorizations"], {})
        self.assertEqual(projection["legacy_unverified_authorizations"][0]["grant"], grant)
        self.assertIn("lacks a bound presentation", projection["legacy_unverified_authorizations"][0]["reason"])
        projection_ref = self.fixture.put("effective-receipt.json", projection)
        self.assertEqual(self.history.run_event("status", previous_ref=projection_ref), projection)

        display_request = self.history.request(
            "batch_presented", previous_ref=projection_ref, **self.fixture.presentation_args(projection, 45)
        )
        shown = advance_closeout(display_request, self.root)
        self.assertEqual(advance_closeout(display_request, self.root), shown)
        with self.assertRaisesRegex(ValueError, "stale"):
            self.history.run_event("status", previous_ref=original_ref)
        with self.assertRaisesRegex(ValueError, "must follow the displayed table"):
            self.history.run_event("approve_upload", batch_sha256=shown["batch"]["sha256"], approved_rows=["A"],
                                   message_ref=grant["message_ref"])
        self.assertEqual(self.history.status()["batch"]["authorizations"], {})

        result = self.history.run_event("approve_upload", batch_sha256=shown["batch"]["sha256"], approved_rows=["A"],
                                        message_ref=self.fixture.msg("批准 A 上传。", 5))
        self.assertEqual(result["batch"]["authorizations"]["A"]["source_message_id"], "5")
        self.assertEqual(result["legacy_unverified_authorizations"], projection["legacy_unverified_authorizations"])
        new_rows = copy.deepcopy(self.args)
        new_rows["batch_version"] = 2
        new_rows["proposals"][1]["attribution"] = "changed-B-attribution"
        self.history.run_event("retrospective", **new_rows)
        readback = self.history.status()
        self.assertEqual(set(readback["batch"]["authorizations"]), {"A"})
        self.assertEqual(readback["batch"]["authorizations"]["A"]["presentation"], shown["batch"]["presentation"])

    def test_old_parser_grant_is_revalidated_even_when_a_display_exists(self):
        shown = self.history.present()
        _, grant = self.register_legacy_grant(shown, "我同意 A 的观点，投稿另议。",
                                              presentation=shown["batch"]["presentation"])
        readback = self.history.status()
        self.assertEqual(readback["batch"]["authorizations"], {})
        self.assertEqual(readback["legacy_unverified_authorizations"][0]["grant"], grant)
        self.assertIn("does not authorize publication", readback["legacy_unverified_authorizations"][0]["reason"])

    def test_latest_actual_withdrawal_disables_only_that_row_and_blocks_approval_replay(self):
        shown = self.history.present()
        batch_sha = shown["batch"]["sha256"]
        original = self.fixture.msg("同意 A 和 B 上传。", 4)
        newer = self.fixture.msg("批准 A 上传。", 6)
        self.history.run_event("approve_upload", batch_sha256=batch_sha, approved_rows=["A", "B"],
                               message_ref=original)
        self.history.run_event("approve_upload", batch_sha256=batch_sha, approved_rows=["A"],
                               message_ref=newer)
        with self.assertRaisesRegex(ValueError, "withdrawal must follow"):
            self.history.run_event("reply", has_change_request=False,
                                   message_ref=self.fixture.msg("撤回 A 的上传授权。", 5))
        withdrawal = self.fixture.msg("撤回 A 的上传授权。", 7)
        state = self.history.run_event("reply", has_change_request=False, message_ref=withdrawal)
        self.assertEqual(set(state["batch"]["authorizations"]), {"B"})
        self.assertEqual(state["upload_withdrawals"][0]["grant"]["message_ref"], newer)
        self.assertEqual(state["upload_withdrawals"][0]["message_ref"], withdrawal)
        self.assertEqual(self.history.run_event("reply", has_change_request=False, message_ref=withdrawal), state)
        with self.assertRaisesRegex(ValueError, "approval must follow the withdrawal"):
            self.history.run_event("approve_upload", batch_sha256=batch_sha, approved_rows=["A"],
                                   message_ref=newer)
        self.assertEqual(self.history.status(), state)
        restored = self.history.run_event("approve_upload", batch_sha256=batch_sha, approved_rows=["A"],
                                          message_ref=self.fixture.msg("批准 A 上传。", 8))
        self.assertEqual(set(restored["batch"]["authorizations"]), {"A", "B"})
