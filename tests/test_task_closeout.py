"""Replay delivery and actual-reply shapes without a remote submission."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.task_closeout import STATE_SCHEMA, TARGET_REPO, inspect_closeout


class TaskCloseoutTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.delivery_files = [self.put("report.md", "Synthetic reviewed engineering work")]
        self.state = None
        self.sequence = 0

    def put(self, name, content):
        data = (content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)).encode("utf-8")
        (self.root / name).write_bytes(data)
        return {"path": name, "sha256": hashlib.sha256(data).hexdigest()}

    def event(self, operation, *, revision=1, **fields):
        request = {"operation": operation, "task_id": "synthetic", "task_revision": revision, **fields}
        if self.state is not None:
            self.sequence += 1
            request["previous_ref"] = self.put(f"state-{self.sequence}.json", self.state)
        self.state = inspect_closeout(request, self.root)
        return self.state

    def draft(self, body="合成试例：压力核查这一版是否完成，还是有需要修改的地方？", *, revision=1):
        draft = self.put(f"draft-{revision}.md", body)
        return self.event("delivery", subject="合成试例：压力核查", artifact_refs=self.delivery_files,
                          draft_ref=draft, revision=revision)

    def sent(self, *, revision=1, body=None, index=5):
        draft = (self.root / self.state["draft_ref"]["path"]).read_text(encoding="utf-8")
        message = self.put(f"delivery-message-{revision}.json",
                           {"actor": "assistant", "source_message_id": f"delivery-{revision}",
                            "source_locator": f"synthetic://chat/delivery-{revision}",
                            "source_conversation_id": "synthetic-chat", "source_message_index": index,
                            "message_text": draft if body is None else body})
        return self.event("delivery_sent", revision=revision, message_ref=message)

    def msg(self, quote, number, actor="user", *, index=None, conversation="synthetic-chat"):
        return self.put(f"message-{number}.json", {"actor": actor, "user_quote": quote,
                                                   "source_message_id": str(number),
                                                   "source_locator": f"synthetic://chat/{number}",
                                                   "source_conversation_id": conversation,
                                                   "source_message_index": number * 10 if index is None else index})

    def confirmed(self):
        self.draft()
        self.sent()
        return self.event("reply", has_change_request=False, message_ref=self.msg("这一版完成。", 1))

    def test_only_later_same_chat_reply_can_close_this_revision(self):
        self.draft()
        self.sent(index=20)
        for message in (
            self.msg("确认完成。", 1),
            self.msg("确认完成。", 2),
            self.msg("确认完成。", 3, conversation="other-chat"),
            self.put("no-host-order.json", {"actor": "user", "source_message_id": "no-order",
                     "source_locator": "synthetic://chat/no-order", "user_quote": "确认完成。"}),
        ):
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, "same conversation|actual host conversation ID"):
                    self.event("reply", has_change_request=False, message_ref=message)
                self.assertEqual(self.state["status"], "DELIVERED_AWAITING_FEEDBACK")
        continuing = self.event("reply", has_change_request=False,
                                message_ref=self.msg("这版完成了，不过压力仍需补充。", 4))
        self.assertEqual(continuing["status"], "DELIVERED_AWAITING_FEEDBACK")
        closed = self.event("reply", has_change_request=False,
                            message_ref=self.msg("这版确认完成，谢谢。", 5))
        self.assertEqual(closed["status"], "RETROSPECTIVE_REQUIRED")
        self.assertEqual(closed["closure_event"]["source_message_id"], "5")

    def retrospective_args(self):
        review = self.put("review.md", "The original route lacked a split outlet. The after-change check covered the purge.")
        material = self.put("material.md", "Feed, outlet and pressure balance settings with an independent check.")
        named = self.put("named.json", {"items": [{"id": "P", "summary": "Pressure and discharge",
                                                  "source_locator": "synthetic://chat/original-request"}]})
        rows = []
        for id_ in ("A", "B"):
            public = self.put(f"public-{id_}.md", f"Independently checkable reusable material {id_}")
            rows.append({"id": id_, "entry_id": f"EXP-20261119-test-{id_.lower()}",
                         "title": f"Material {id_}", "category": "material_structure_reference",
                         "public_ref": public, "disclosure_basis": "New synthetic example",
                         "scope": "Subtype and boundary", "verification": "Independent hand calculation",
                         "new_value": "Reports sealing check", "target_repo": TARGET_REPO,
                         "attribution": "test-contributor", "license": "CC BY 4.0"})
        return {"review_ref": review, "professional_materials": [{"title": "Pressure notes", "scope": "Gas split",
                "body_ref": material, "source_refs": self.delivery_files, "verification": "Sum checked"}],
                "named_items_ref": named, "named_item_outcomes": [
                    {"id": "P", "disposition": "local_only", "reason": "Project-specific data", "evidence_refs": [review]}],
                "batch_id": "test-batch", "batch_version": 1, "proposals": rows}

    def presentation_args(self, state, index=15, *, linked=False, actual_text=None, table_text=None):
        table = state["upload_table_markdown"]
        table_ref = self.put(f"table-{index}.md", table if table_text is None else table_text)
        if actual_text is None:
            actual_text = f"[拟上传表](<{(self.root / table_ref['path']).as_posix()}>)" if linked else table
        message_ref = self.put(f"batch-presentation-{index}.json", {
            "actor": "assistant", "message_text": actual_text,
            "source_message_id": f"present-{index}", "source_locator": f"synthetic://chat/{index}",
            "source_conversation_id": "synthetic-chat", "source_message_index": index})
        return {"table_ref": table_ref, "batch_sha256": state["batch"]["sha256"], "message_ref": message_ref}

    def present(self, index=15, **fields):
        return self.event("batch_presented", **self.presentation_args(self.state, index, **fields))

    def test_actual_draft_and_sent_reply_require_the_same_question(self):
        self.assertEqual(self.draft("工程报告已核对。")["status"], "DELIVERY_QUESTION_MISSING")
        self.assertIn("这一版是否完成", self.state["question"])
        self.assertEqual(self.draft()["status"], "DELIVERY_DRAFT_READY")
        with self.assertRaisesRegex(ValueError, "sent reply differs"):
            self.sent(body="已交付。")
        with self.assertRaises(ValueError):
            self.event("reply", has_change_request=False, message_ref=self.msg("这一版完成", 1))
        self.assertEqual(self.sent()["status"], "DELIVERED_AWAITING_FEEDBACK")
        self.assertEqual(self.event("reply", has_change_request=False,
                                   message_ref=self.msg("这一版完成", 2))["status"], "RETROSPECTIVE_REQUIRED")

    def test_acknowledgment_approval_to_start_and_ordinary_feedback_do_not_close(self):
        self.draft()
        self.sent()
        for i, reply in enumerate(("收到", "同意开始实施", "项目完成了吗？", "这版完成，不过压力还有问题",
                                   "这版预计后天完成", "下一版完成后再发", "这版完成不了。",
                                   "本次完成局部复核。", "请在这版结束"), 1):
            with self.subTest(reply=reply):
                result = self.event("reply", has_change_request=False, message_ref=self.msg(reply, i))
                self.assertEqual(result["status"], "DELIVERED_AWAITING_FEEDBACK")
        revision = self.event("reply", has_change_request=True, message_ref=self.msg("压力还有问题", 20))
        self.assertEqual(revision["status"], "WORKING")
        self.assertNotIn("closure_event", revision)
        self.assertEqual(self.event("reply", has_change_request=False,
                                   message_ref=self.msg("这版完成", 21))["status"], "WORKING")

    def test_closeout_records_material_and_every_named_item_before_proposing_rows(self):
        result = self.confirmed()
        self.assertEqual(result["closure_event"]["source_message_id"], "1")
        self.assertIsNone(result["batch"])
        self.assertEqual(self.event("reply", has_change_request=False,
                                   message_ref=self.msg("这一版完成。", 1)), result)
        args = self.retrospective_args()
        missing = {**args, "named_item_outcomes": []}
        with self.assertRaisesRegex(ValueError, "Missing: P"):
            self.event("retrospective", **missing)
        args["professional_materials"][0]["body_ref"] = self.put("only-model.bkp", "synthetic binary name")
        with self.assertRaisesRegex(ValueError, "reviewable UTF-8 prose"):
            self.event("retrospective", **args)
        stored = self.event("retrospective", **self.retrospective_args())
        self.assertEqual(stored["batch"]["authorizations"], {})
        self.assertIn("public-A.md", stored["upload_table_markdown"])
        self.assertIn("public-B.md", stored["upload_table_markdown"])

    def test_only_approved_row_authorized_and_any_changed_row_requires_approval(self):
        self.confirmed()
        args = self.retrospective_args()
        self.event("retrospective", **args)
        self.present()
        batch_hash = self.state["batch"]["sha256"]
        with self.assertRaisesRegex(ValueError, "does not approve"):
            self.event("approve_upload", batch_sha256=batch_hash, approved_rows=["A"],
                       message_ref=self.msg("这一版完成。", 1))
        with self.assertRaisesRegex(ValueError, "authorize publication"):
            self.event("approve_upload", batch_sha256=batch_hash, approved_rows=["A", "B"],
                       message_ref=self.msg("本批只同意 A，按表中署名和许可上传，B 退回修改。", 2))
        approval = self.msg("本批只同意 A，按表中署名和许可上传，B 退回修改。", 2)
        selected = self.event("approve_upload", batch_sha256=batch_hash, approved_rows=["A"], message_ref=approval)
        self.assertEqual(set(selected["batch"]["authorizations"]), {"A"})
        self.assertEqual(self.event("approve_upload", batch_sha256=batch_hash, approved_rows=["A"],
                                   message_ref=approval), selected)
        with self.assertRaisesRegex(ValueError, "authorize publication"):
            self.event("approve_upload", batch_sha256=batch_hash, approved_rows=["A"],
                       message_ref=self.msg("A 只留本地，批准 B 上传。", 3))
        args["batch_version"] = 2
        args["proposals"][1]["attribution"] = "revised-B-contributor"
        self.assertEqual(set(self.event("retrospective", **args)["batch"]["authorizations"]), {"A"})
        self.assertNotIn("presentation", self.state["batch"])
        self.assertEqual(self.state["batch"]["authorizations"]["A"]["presentation"], selected["batch"]["presentation"])
        with self.assertRaisesRegex(ValueError, "exact displayed upload batch"):
            self.event("approve_upload", batch_sha256=batch_hash, approved_rows=["B"],
                       message_ref=self.msg("批准 B 上传。", 4))
        args["batch_version"] = 3
        args["proposals"][0]["public_ref"] = self.put("public-A-updated.md", "Corrected public text.")
        self.assertEqual(self.event("retrospective", **args)["batch"]["authorizations"], {})
        self.present(35)
        with self.assertRaisesRegex(ValueError, "earlier approval"):
            self.event("approve_upload", batch_sha256=self.state["batch"]["sha256"], approved_rows=["A"],
                       message_ref=approval)

    def test_approval_requires_actual_exact_presentation_and_strictly_later_host_reply(self):
        self.confirmed()
        table = self.event("retrospective", **self.retrospective_args())
        batch = table["batch"]["sha256"]
        approval = self.msg("批准 A 上传。", 2)
        with self.assertRaisesRegex(ValueError, "actual presentation"):
            self.event("approve_upload", batch_sha256=batch, approved_rows=["A"], message_ref=approval)
        with self.assertRaisesRegex(ValueError, "exact upload table"):
            self.present(actual_text="表已经展示")
        with self.assertRaisesRegex(ValueError, "match the current proposed table exactly"):
            self.present(table_text=table["upload_table_markdown"].replace("CC BY 4.0", "CC BY-SA 4.0"), linked=True)
        with self.assertRaisesRegex(ValueError, "after this revision closed"):
            self.present(index=9)
        self.present(linked=True)
        for reply in (self.msg("批准 A 上传。", 3, index=14), self.msg("批准 A 上传。", 4, index=15),
                      self.msg("批准 A 上传。", 5, conversation="another-chat")):
            with self.assertRaisesRegex(ValueError, "must follow the displayed table"):
                self.event("approve_upload", batch_sha256=batch, approved_rows=["A"], message_ref=reply)
        self.assertEqual(self.state["batch"]["authorizations"], {})
        self.assertEqual(set(self.event("approve_upload", batch_sha256=batch, approved_rows=["A"],
                                        message_ref=approval)["batch"]["authorizations"]), {"A"})

    def test_presentation_and_approval_recheck_the_exact_public_source_text(self):
        self.confirmed()
        args = self.retrospective_args()
        table = self.event("retrospective", **args)
        self.put("public-B.md", "Changed without revising the batch")
        with self.assertRaisesRegex(ValueError, "Referenced bytes changed"):
            self.present()
        self.put("public-B.md", "Independently checkable reusable material B")
        self.present()
        presentation = self.state["batch"]["presentation"]
        args["proposals"].reverse()
        self.event("retrospective", **args)
        self.assertEqual(self.state["batch"]["presentation"], presentation)
        self.assertEqual(self.state["upload_table_markdown"], table["upload_table_markdown"])
        self.put("public-B.md", "Changed after the user saw the batch")
        with self.assertRaisesRegex(ValueError, "Referenced bytes changed"):
            self.event("approve_upload", batch_sha256=table["batch"]["sha256"], approved_rows=["A"],
                       message_ref=self.msg("批准 A 上传。", 2))

    def test_reopening_invalidates_this_revision_closure_and_preserves_immutable_history(self):
        self.confirmed()
        stored = self.event("retrospective", **self.retrospective_args())
        original = self.put("history.json", stored)
        reopened = self.event("reply", has_change_request=True, message_ref=self.msg("继续处理压降", 2))
        self.assertEqual(reopened["status"], "WORKING")
        self.assertNotIn("closure_event", reopened)
        self.assertIsNone(reopened["batch"])
        self.assertEqual(hashlib.sha256((self.root / "history.json").read_bytes()).hexdigest(), original["sha256"])
        self.assertEqual(self.draft(revision=2)["status"], "DELIVERY_DRAFT_READY")
        self.sent(revision=2)
        with self.assertRaisesRegex(ValueError, "this revision"):
            self.event("reply", revision=1, has_change_request=False, message_ref=self.msg("这一版完成", 3))

    def test_cli_runs_real_local_delivery_preflight(self):
        draft = self.put("draft.md", "Only a delivery link")
        request = self.put("request.json", {"operation": "delivery", "task_id": "synthetic", "task_revision": 1,
                           "subject": "压力核查", "artifact_refs": self.delivery_files, "draft_ref": draft})
        script = Path(__file__).resolve().parents[1] / "tools/task_closeout.py"
        result = subprocess.run([sys.executable, "-B", str(script), "--request", str(self.root / request["path"]),
                                 "--evidence-root", str(self.root), "--output", str(self.root / "receipt.json")],
                                capture_output=True, check=True)
        self.assertEqual(result.stdout, b"")
        receipt = json.loads((self.root / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["schema"], STATE_SCHEMA)
        self.assertEqual(receipt["status"], "DELIVERY_QUESTION_MISSING")


if __name__ == "__main__":
    unittest.main()
