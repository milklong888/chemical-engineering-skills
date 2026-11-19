"""Verify that only explicit row-level permission can authorize publication."""
import unittest

import test_legacy_upload_authorizations as legacy_fixtures
import test_task_closeout as fixtures
from tools.expert_cli import execute
from tools.task_closeout import explicitly_approved_rows


class UploadConsentLanguageTests(unittest.TestCase):
    def test_direct_grants_bind_only_the_named_rows(self):
        for quote, expected in (
            ("本批只同意 A 上传。", {"A"}),
            ("本批只同意 A，按表中署名和许可上传，B 退回修改。", {"A"}),
            ("A 只留本地，批准 B 上传。", {"B"}),
            ("我同意 A 的观点。B 同意上传。", {"B"}),
            ("A 行同意观点、同意上传。", {"A"}),
            ("批准 A 上传，C 等审完再议。", {"A"}),
            ("同意 A 上传。B 暂不投稿。", {"A"}),
            ("同意上传 A 和 B。", {"A", "B"}),
            ("批准 A-1 上传。", {"A-1"}),
            ("I approve A for upload. Do not publish B.", {"A"}),
            ("I authorize publication of A and B.", {"A", "B"}),
            ("我同意上传 A，B 暂时不发。", {"A"}),
            ("A 行同意上传，B 行暂时别发。", {"A"}),
            ("同意上传 A 和 B，B 的投稿先留在本地。", {"A"}),
            ("B 暂时不投稿，批准 A 上传。", {"A"}),
            ("好的，批准 A 上传，谢谢。", {"A"}),
            ("I approve upload of A. Thanks.", {"A"}),
            ("I approve upload of A, B is pending review.", {"A"}),
        ):
            with self.subTest(quote=quote):
                self.assertEqual(explicitly_approved_rows(quote, {"A", "A-1", "B", "C"}), expected)

    def test_words_outside_the_selection_are_not_row_ids(self):
        rows = {"A", "I", "approve", "upload"}
        self.assertEqual(explicitly_approved_rows("I approve A for upload.", rows), {"A"})
        self.assertEqual(explicitly_approved_rows("I approve A for upload. Do not upload.", rows), set())

    def test_non_grants_and_later_veto_cover_their_intended_rows(self):
        for quote in (
            "A 未批准上传。",
            "我还没同意 A 投稿。",
            "A 先不上传。",
            "我同意 A 的观点，投稿另议。",
            "我同意 A 的内容，上传一事下次再决定。",
            "我同意 A 的内容，按表中署名和许可上传。",
            "我同意 A 准备上传。",
            "我同意 A 加入拟上传表。",
            "我同意 A 上传申请。",
            "我同意 A 用来做内部交流。",
            "举例，批准 A 上传。",
            "> 批准 A 上传",
            "转述：『可以。批准 A 上传。』",
            "我同意 A 上传？",
            "如果没有问题，批准 A 上传。",
            "同意 A 上传，但审完以后再上传。",
            "同意 A 上传，等 B 审完再发。",
            "同意 A 上传。等我通知。",
            "同意 A 上传，但是先审核。",
            "同意 A 上传，但是等 B 核完。",
            "我同意上传 A，但暂时不发。",
            "我同意上传 A，不过暂时别发。",
            "我同意上传 A，只是现在别上传。",
            "我同意上传 A，暂时不投稿。",
            "我同意上传 A，但先留在本地。",
            "我同意上传 A，先放着。",
            "批准 A 上传。A 暂时别公开。",
            "批准 A 上传。A 的投稿目前不发。",
            "我同意上传 A，但发送时间另订。",
            "我同意上传 A，不是现在。",
            "I approve upload of A, pending review.",
            "I approve upload of A, hold it for now.",
            "我同意上传 A，时机再商量。",
            "我同意上传 A。执行日期尚待通知。",
            "批准 A 上传。A 暂缓投稿。",
            "批准 A 上传。撤回 A 的批准。",
            "A 和 B 的内容都同意，是否上传待定。",
            "I approve preparing A for upload.",
            "I approve A for upload. Wait until I confirm.",
            "A is not yet approved for upload.",
            "Example: I approve A for upload.",
            "e.g. I approve A for upload.",
        ):
            with self.subTest(quote=quote):
                self.assertEqual(explicitly_approved_rows(quote, {"A", "B"}), set())

    def test_public_entry_does_not_record_ambiguous_consent(self):
        fixture = fixtures.TaskCloseoutTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        task = {"task_id": "approval", "task_revision": 1}

        def run(operation, **fields):
            request = {**task, "operation": operation, **fields}
            return execute({"operation": "task_closeout", "payload": request}, fixture.root)

        def message(name, index, actor, body):
            return fixture.put(name, {
                "actor": actor, "source_message_id": f"{actor}-{index}",
                "source_locator": f"synthetic://chat/{index}",
                "source_conversation_id": "synthetic-approval", "source_message_index": index,
                "message_text" if actor == "assistant" else "user_quote": body,
            })

        draft = "测试交付这一版是否完成，还是有需要修改的地方？"
        run("delivery", subject="测试交付", artifact_refs=fixture.delivery_files,
            draft_ref=fixture.put("draft.md", draft))
        run("delivery_sent", message_ref=message("sent.json", 1, "assistant", draft))
        run("reply", has_change_request=False,
            message_ref=message("closure.json", 2, "user", "这一版完成。"))
        proposed = run("retrospective", **fixture.retrospective_args())
        batch = proposed["batch"]
        table = proposed["upload_table_markdown"]
        run("batch_presented", batch_sha256=batch["sha256"], table_ref=fixture.put("proposed.md", table),
            message_ref=message("presentation.json", 3, "assistant", table))

        rejected = ("A 未批准上传。", "我同意 A 的观点，投稿另议。",
                    "我同意上传 A，但暂时不发。", "批准 A 上传。A 暂时别公开。")
        for i, quote in enumerate(rejected, 4):
            with self.subTest(quote=quote):
                with self.assertRaisesRegex(ValueError, "authorize publication"):
                    run("approve_upload", batch_sha256=batch["sha256"], approved_rows=["A"],
                        message_ref=message(f"rejected-{i}.json", i, "user", quote))
                self.assertEqual(run("status")["batch"]["authorizations"], {})

        result = run("approve_upload", batch_sha256=batch["sha256"], approved_rows=["A"],
                     message_ref=message("approved.json", 8, "user", "我同意上传 A，B 暂时不发。"))
        self.assertEqual(set(result["batch"]["authorizations"]), {"A"})

    def test_historical_delay_is_audit_only_after_replay_even_for_unchanged_row(self):
        fixture = legacy_fixtures.LegacyUploadAuthorizationTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        shown = fixture.history.present()
        stale, grant = fixture.register_legacy_grant(shown, "我同意上传 A，但暂时不发。",
                                                     presentation=shown["batch"]["presentation"])
        stale_ref = fixture.fixture.put("old-ambiguous.json", stale)
        projected = fixture.history.run_event("status", previous_ref=stale_ref)
        self.assertEqual(projected["batch"]["authorizations"], {})
        self.assertEqual(projected["legacy_unverified_authorizations"][0]["grant"], grant)

        fixture.args["batch_version"] = 2
        fixture.args["proposals"][1]["attribution"] = "updated B attribution"
        revised = fixture.history.run_event("retrospective", **fixture.args)
        self.assertEqual(revised["batch"]["rows"]["A"], shown["batch"]["rows"]["A"])
        self.assertEqual(revised["batch"]["authorizations"], {})
        with self.assertRaisesRegex(ValueError, "stale"):
            fixture.history.run_event("status", previous_ref=stale_ref)

    def test_later_explicit_delay_suspends_only_applicable_existing_grants(self):
        fixture = legacy_fixtures.LegacyUploadAuthorizationTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        shown = fixture.history.present()
        batch_sha = shown["batch"]["sha256"]
        old_approval = fixture.fixture.msg("批准 A 和 B 上传。", 4)
        fixture.history.run_event("approve_upload", batch_sha256=batch_sha,
                                  approved_rows=["A", "B"], message_ref=old_approval)
        scoped_stop = fixture.history.run_event("reply", has_change_request=False,
                                               message_ref=fixture.fixture.msg("B 的投稿暂时不发。", 5))
        self.assertEqual(set(scoped_stop["batch"]["authorizations"]), {"A"})
        global_stop = fixture.history.run_event("reply", has_change_request=False,
                                               message_ref=fixture.fixture.msg("暂时别发。", 6))
        self.assertEqual(global_stop["batch"]["authorizations"], {})
        with self.assertRaisesRegex(ValueError, "approval must follow"):
            fixture.history.run_event("approve_upload", batch_sha256=batch_sha,
                                      approved_rows=["A"], message_ref=old_approval)

    def test_later_explicit_withdrawal_and_hold_stop_the_named_row(self):
        for quote in ("A 暂缓投稿。", "撤回 A 的批准。", "A 暂停投稿，B 照原计划。"):
            with self.subTest(quote=quote):
                fixture = legacy_fixtures.LegacyUploadAuthorizationTests()
                fixture.setUp()
                self.addCleanup(fixture.doCleanups)
                batch = fixture.history.present()["batch"]["sha256"]
                approval = fixture.fixture.msg("批准 A 和 B 上传。", 4)
                fixture.history.run_event("approve_upload", batch_sha256=batch,
                                          approved_rows=["A", "B"], message_ref=approval)
                with self.assertRaisesRegex(ValueError, "withdrawal must follow"):
                    fixture.history.run_event("reply", has_change_request=False,
                        message_ref=fixture.fixture.msg(quote, 5, conversation="another-chat"))
                reply = fixture.fixture.msg(quote, 6)
                state = fixture.history.run_event("reply", has_change_request=False, message_ref=reply)
                self.assertEqual(set(state["batch"]["authorizations"]), {"B"})
                self.assertEqual(state["upload_withdrawals"][0]["message_ref"], reply)
                with self.assertRaisesRegex(ValueError, "approval must follow"):
                    fixture.history.run_event("approve_upload", batch_sha256=batch,
                                              approved_rows=["A"], message_ref=approval)
