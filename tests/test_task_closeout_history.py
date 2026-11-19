"""Regress preparation, real-message evidence and obsolete closeout replay."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest

import test_task_closeout as fixtures
from tools.task_closeout import inspect_closeout
from tools.task_closeout_history import HISTORY, _digest, _json, advance_closeout


class TaskCloseoutHistoryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.TaskCloseoutTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root

    def request(self, operation, revision=1, **fields):
        return {"operation": operation, "task_id": "synthetic", "task_revision": revision, **fields}

    def run_event(self, operation, revision=1, **fields):
        return advance_closeout(self.request(operation, revision, **fields), self.root)

    def draft_request(self, revision=1):
        question = "本任务压力核查这一版是否完成？"
        draft = self.fixture.put(f"draft-{revision}.md", question)
        return self.request("delivery", revision, subject="本任务压力核查", draft_ref=draft,
                            artifact_refs=self.fixture.delivery_files, feedback_question=question)

    def sent_ref(self, revision=1):
        return self.fixture.put(f"delivery-{revision}.json", {"actor": "assistant", "source_message_id": f"send-{revision}",
            "source_locator": f"synthetic://assistant/{revision}", "message_text": "本任务压力核查这一版是否完成？",
            "source_conversation_id": "synthetic-chat", "source_message_index": 5 if revision == 1 else 55})

    def close(self, revision=1, number=3):
        advance_closeout(self.draft_request(revision), self.root)
        self.run_event("delivery_sent", revision, message_ref=self.sent_ref(revision))
        return self.run_event("reply", revision, message_ref=self.fixture.msg("这一版完成。", number), has_change_request=False)

    def status(self):
        return advance_closeout({"operation": "status", "task_id": "synthetic"}, self.root)

    def present(self, revision=1, index=35):
        return self.run_event("batch_presented", revision, **self.fixture.presentation_args(self.status(), index))

    def test_status_uses_current_local_task_and_absence_is_read_only(self):
        self.assertEqual(self.status()["status"], "NO_CLOSEOUT_STATE")
        self.assertFalse((self.root / HISTORY).exists())
        draft = advance_closeout(self.draft_request(), self.root)
        self.assertEqual(self.status(), draft)
        self.assertEqual(advance_closeout({"operation": "status", "task_id": "other"}, self.root)["status"], "NO_CLOSEOUT_STATE")
        with self.assertRaises(ValueError):
            self.run_event("delivery_sent")
        with self.assertRaisesRegex(ValueError, "draft first"):
            self.run_event("reply", message_ref=self.fixture.msg("这一版完成。", 1), has_change_request=False)
        self.assertEqual(self.status()["status"], "DELIVERY_DRAFT_READY")
        self.assertEqual(self.run_event("delivery_sent", message_ref=self.sent_ref())["status"], "DELIVERED_AWAITING_FEEDBACK")

    def test_original_closeout_pure_validator_would_allow_replay_after_reopen(self):
        self.close()
        self.run_event("retrospective", **self.fixture.retrospective_args())
        stored = self.present()
        old = self.fixture.put("obsolete-receipt.json", stored)
        reopened = self.run_event("reply", message_ref=self.fixture.msg("请重做。", 4), has_change_request=True)
        approval = self.fixture.msg("批准 A 上传。", 5)
        stale = self.request("approve_upload", previous_ref=old, batch_sha256=stored["batch"]["sha256"],
                             approved_rows=["A"], message_ref=approval)
        self.assertIn("A", inspect_closeout(stale, self.root)["batch"]["authorizations"])
        with self.assertRaisesRegex(ValueError, "stale"):
            advance_closeout(stale, self.root)
        del stale["previous_ref"]
        with self.assertRaisesRegex(ValueError, "exact displayed upload batch"):
            advance_closeout(stale, self.root)
        self.assertEqual(self.status(), reopened)

    def test_review_and_approval_retry_identical_then_both_go_stale(self):
        closure = self.close()
        initial = self.fixture.put("confirmed.json", closure)
        table_request = self.request("retrospective", previous_ref=initial, **self.fixture.retrospective_args())
        table = advance_closeout(table_request, self.root)
        self.assertEqual(advance_closeout(table_request, self.root), table)
        presentation = self.request("batch_presented", previous_ref=self.fixture.put("unshown.json", table),
                                    **self.fixture.presentation_args(table, 35))
        table = advance_closeout(presentation, self.root)
        self.assertEqual(advance_closeout(presentation, self.root), table)
        base = self.fixture.put("table.json", table)
        approval = self.request("approve_upload", previous_ref=base, batch_sha256=table["batch"]["sha256"],
                               approved_rows=["A"], message_ref=self.fixture.msg("批准 A 上传。", 5))
        granted = advance_closeout(approval, self.root)
        self.assertEqual(advance_closeout(approval, self.root), granted)
        with self.assertRaisesRegex(ValueError, "stale"):
            advance_closeout(table_request, self.root)
        self.run_event("reply", message_ref=self.fixture.msg("请改。", 6), has_change_request=True)
        with self.assertRaisesRegex(ValueError, "stale"):
            advance_closeout(approval, self.root)

    def test_obsolete_batch_cannot_become_current_again_via_retrospective(self):
        self.close()
        old_args = self.fixture.retrospective_args()
        old = self.run_event("retrospective", **old_args)
        self.present()
        self.run_event("approve_upload", batch_sha256=old["batch"]["sha256"], approved_rows=["A"],
                       message_ref=self.fixture.msg("批准 A 上传。", 4))
        new = self.run_event("retrospective", **{**old_args, "batch_id": "different-batch"})
        self.assertFalse(new["batch"]["authorizations"])
        with self.assertRaisesRegex(ValueError, "older displayed batch"):
            self.run_event("retrospective", **old_args)
        self.assertEqual(self.status(), new)

    def test_old_sent_and_grant_messages_do_not_replay_for_new_revision(self):
        self.close()
        args = self.fixture.retrospective_args()
        batch = self.run_event("retrospective", **args)["batch"]["sha256"]
        self.present()
        approved = self.fixture.msg("批准 A 上传。", 4)
        self.run_event("approve_upload", batch_sha256=batch, approved_rows=["A"], message_ref=approved)
        self.run_event("reply", message_ref=self.fixture.msg("请改。", 5), has_change_request=True)
        advance_closeout(self.draft_request(2), self.root)
        with self.assertRaisesRegex(ValueError, "different revision"):
            self.run_event("delivery_sent", 2, message_ref=self.sent_ref())
        self.close(2, number=6)
        self.assertEqual(self.run_event("retrospective", 2, **args)["batch"]["sha256"], batch)
        with self.assertRaisesRegex(ValueError, "actual presentation"):
            self.run_event("approve_upload", 2, batch_sha256=batch, approved_rows=["A"], message_ref=approved)
        self.present(2, index=65)
        with self.assertRaisesRegex(ValueError, "must follow the displayed table"):
            self.run_event("approve_upload", 2, batch_sha256=batch, approved_rows=["A"], message_ref=approved)
        self.assertEqual(self.status()["batch"]["authorizations"], {})
        current = self.run_event("approve_upload", 2, batch_sha256=batch, approved_rows=["A"],
                                 message_ref=self.fixture.msg("批准 A 上传。", 7))
        self.assertEqual(set(current["batch"]["authorizations"]), {"A"})

    def test_historical_table_with_no_presentation_requires_actual_display_to_proceed(self):
        advance_closeout(self.draft_request(), self.root)
        self.run_event("delivery_sent", message_ref=self.sent_ref())
        self.run_event("reply", message_ref=self.fixture.msg("这一版完成。", 3), has_change_request=False)
        table = self.run_event("retrospective", **self.fixture.retrospective_args())
        self.assertEqual(self.status(), table)
        approval = self.fixture.msg("批准 A 上传。", 4)
        request = self.request("approve_upload", batch_sha256=table["batch"]["sha256"], approved_rows=["A"],
                               message_ref=approval)
        with self.assertRaisesRegex(ValueError, "actual presentation"):
            advance_closeout(request, self.root)
        self.assertEqual(self.status(), table)
        presentation = self.request("batch_presented", **self.fixture.presentation_args(table, 35, linked=True))
        script = Path(__file__).resolve().parents[1] / "tools/task_closeout.py"
        request_path = self.root / self.fixture.put("present-upload.json", presentation)["path"]
        run = subprocess.run([sys.executable, "-B", str(script), "--request", str(request_path)],
                             capture_output=True, check=True)
        shown = json.loads(run.stdout)
        self.assertEqual(self.status(), shown)
        self.assertIn("presentation", shown["batch"])
        self.assertEqual(set(advance_closeout(request, self.root)["batch"]["authorizations"]), {"A"})

    def test_legacy_closure_without_verified_order_preserves_audit_only(self):
        self.close()
        self.run_event("retrospective", **self.fixture.retrospective_args())
        shown = self.present()
        first_approval = self.fixture.msg("批准 A 上传。", 4)
        historical = self.run_event("approve_upload", batch_sha256=shown["batch"]["sha256"],
                                    approved_rows=["A"], message_ref=first_approval)
        historical["closure_message_ref"] = self.fixture.put("historical-closure.json", {
            "actor": "user", "source_message_id": "3", "source_locator": "synthetic://chat/3",
            "user_quote": "这一版完成。"})
        with closing(sqlite3.connect(self.root / HISTORY)) as db, db:
            db.execute("UPDATE task_heads SET state=?, state_sha256=? WHERE task_id=?",
                       (_json(historical), _digest(historical), historical["task_id"]))
        audited = self.status()
        self.assertEqual(audited["status"], "DELIVERED_AWAITING_FEEDBACK")
        self.assertIsNone(audited["batch"])
        self.assertEqual(audited["legacy_unverified_closures"][0]["batch"], historical["batch"])
        with closing(sqlite3.connect(self.root / HISTORY)) as db:
            self.assertEqual(db.execute("SELECT state FROM task_heads").fetchone()[0], _json(historical))
        with self.assertRaisesRegex(ValueError, "Explicit user closure"):
            self.run_event("retrospective", **self.fixture.retrospective_args())
        with self.assertRaisesRegex(ValueError, "exact displayed upload batch"):
            self.run_event("approve_upload", batch_sha256=shown["batch"]["sha256"],
                           approved_rows=["A"], message_ref=first_approval)
        revised = self.run_event("reply", message_ref=self.fixture.msg("这版确认完成。", 5),
                                 has_change_request=False)
        self.assertEqual(revised["status"], "RETROSPECTIVE_REQUIRED")
        self.assertEqual(revised["legacy_unverified_closures"], audited["legacy_unverified_closures"])

    def test_concurrent_same_transition_has_one_effect(self):
        draft = advance_closeout(self.draft_request(), self.root)
        explicit = self.fixture.put("base.json", draft)
        request = self.request("delivery_sent", previous_ref=explicit, message_ref=self.sent_ref())
        with ThreadPoolExecutor(max_workers=8) as pool:
            receipts = list(pool.map(lambda _: advance_closeout(request, self.root), range(16)))
        self.assertTrue(all(receipt == receipts[0] for receipt in receipts))
        self.assertEqual(self.status()["history_sequence"], draft["history_sequence"] + 1)

    def test_unregistered_external_receipt_cannot_initialize_local_task(self):
        draft = inspect_closeout(self.draft_request(), self.root)
        prev = self.fixture.put("unregistered.json", draft)
        with self.assertRaisesRegex(ValueError, "not a registered task head"):
            self.run_event("delivery_sent", previous_ref=prev, message_ref=self.sent_ref())
        self.assertEqual(self.status()["status"], "NO_CLOSEOUT_STATE")

    def test_cli_and_api_share_current_closeout_and_preserve_active_state_on_bad_draft(self):
        original = advance_closeout(self.draft_request(), self.root)
        request = self.draft_request(2)
        request["draft_ref"] = self.fixture.put("missing.md", "无结束问题")
        self.assertEqual(advance_closeout(request, self.root)["status"], "DELIVERY_QUESTION_MISSING")
        script = Path(__file__).resolve().parents[1] / "tools/task_closeout.py"
        query = self.fixture.put("status.json", {"operation": "status", "task_id": "synthetic"})
        run = subprocess.run([sys.executable, "-B", str(script), "--request", str(self.root / query["path"])],
                             capture_output=True, check=True)
        self.assertEqual(json.loads(run.stdout), original)
