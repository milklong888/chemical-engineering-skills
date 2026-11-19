"""Regression cases for delivery finding scope and criterion replacement."""

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest

from tools.review_finding_scope import plan_finding_review


class FindingScopeTests(unittest.TestCase):
    def setUp(self):
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        self.root = Path(workspace.name)
        self.identity = {"case_id": "SYN", "task_revision": "R2", "run_id": "current"}
        self.basis = {"scope": ["pressure"]}
        self.original = {"path": "DEMO_OUT.pressure", "unit": "bar", "basis": "absolute", "expected": 24}
        self.updated = {**self.original, "comparison": "eq", "expected": 25}
        self.purity = {"path": "D.purity", "unit": "mol%", "basis": "A in D", "comparison": "ge", "expected": 99}
        self.issues = {"P-DROP": [{"scope": ["pressure"], "criteria": [self.original, self.purity]},
                                  {"scope": "pressure", "criteria": [self.updated]}]}

    def put(self, path, data):
        data = json.dumps(data, ensure_ascii=False).encode()
        (self.root / path).write_bytes(data)
        return {"path": path, "sha256": sha256(data).hexdigest()}

    def record(self, **changes):
        return {"case_id": "SYN", "task_revision": "R2", "finding_id": "P-DROP", "decision": "approved",
                "old_criterion": self.original, "new_criterion": self.updated, **changes}

    def table(self, *rows):
        return self.put("PROJECT_CHANGE_OFFSET_TABLE.json", {"case_id": "SYN", "finding_criterion_changes": rows})

    def user_record(self, path="user-reply.json", **changes):
        source = {"actor": "user", "source_message_id": "reply-a", "source_locator": "chat-example message 27",
                  "user_quote": "For SYN R2 I approve changing P-DROP from 24 to 25 bar absolute."}
        return self.put(path, {**self.record(), **source, **changes})

    def plan(self, *refs, **kwargs):
        basis = dict(self.basis, criterion_replacements=list(refs))
        baseline = deepcopy((self.issues, basis))
        result = plan_finding_review(self.root, self.identity, basis, self.issues, **kwargs)
        self.assertEqual((self.issues, basis), baseline)
        return result

    def assert_rejected(self, result):
        self.assertTrue(result["needs"])
        self.assertEqual(result["needs"][0]["code"], "FINDING_CRITERION_AUTHORITY_INVALID")
        self.assertEqual(result["criteria_by_id"]["P-DROP"], [self.original, self.purity, self.updated])
        self.assertEqual(result["replacements"], [])

    def test_retains_both_thresholds_without_authority(self):
        self.basis["proposed_criterion"] = self.updated
        result = self.plan()
        self.assertEqual(result["criteria_by_id"]["P-DROP"], [self.original, self.purity, self.updated])
        self.assertEqual(result["blocking_ids"], ["P-DROP"])
        self.assertEqual(result["replacements"], [])

    def test_frozen_matching_change_offset_row_supersedes_only_the_old_rule(self):
        table = self.table(self.record(reason="New pressure basis confirmed from same-case readback."))
        self.basis["change_offset_table_ref"] = table
        pointer = {**table, "pointer": "/finding_criterion_changes/0"}
        result = self.plan(pointer)
        self.assertEqual(result["needs"], [])
        self.assertCountEqual(result["criteria_by_id"]["P-DROP"], [self.updated, self.purity])
        self.assertEqual(result["replacements"], [{"id": "P-DROP", "source_ref": pointer,
                                                    "old_criterion": self.original, "new_criterion": self.updated}])

    def test_user_approval_must_bind_original_decision_and_task(self):
        authenticated = self.user_record()
        result = self.plan(authenticated)
        self.assertCountEqual(result["criteria_by_id"]["P-DROP"], [self.updated, self.purity])
        for wrong_input in ({"actor": "assistant"}, {"decision": "pending"}, {"source_message_id": ""},
                            {"source_locator": ""}, {"user_quote": ""}, {"case_id": "ANOTHER"},
                            {"task_revision": "R1"}, {"finding_id": "OTHER"},
                            {"old_criterion": {**self.original, "basis": "gauge"}}):
            with self.subTest(wrong_input=wrong_input):
                self.assert_rejected(self.plan(self.user_record(**wrong_input)))

    def test_declared_replacement_or_changed_original_file_cannot_be_used(self):
        table = self.table(self.record(reason="Reason shown on the source table."))
        pointer = {**table, "pointer": "/finding_criterion_changes/0"}
        self.assert_rejected(self.plan(pointer))
        self.basis["change_offset_table_ref"] = table
        self.assert_rejected(self.plan({**table, "pointer": "/draft/0"}))
        self.assert_rejected(self.plan({**pointer, "new_criterion": self.updated}))
        self.table(self.record(reason="Edited later."))
        self.assert_rejected(self.plan(pointer))

    def test_narrow_scope_keeps_other_ids_and_actions_for_followup(self):
        self.issues.update({
            "REPORT-1": [{"scope": "report", "recommended_change": "Repair the caption."}],
            "SUCTION": [{"scope": ["mechanical"], "next_action": "Recheck suction."},
                        {"scope": ["PRESSURE"], "criteria": [self.original]}],
            "UNKNOWN": [{"scope": ["report"]}, {}],
            "MALFORMED": [{"scope": ["report", None]}],
        })
        items = [{"id": "REPORT-1", "next_action": "Update the caption after the client reviews it."},
                 {"id": "UNKNOWN", "scope": ["report"]}]
        result = self.plan(carried_ids=["REPORT-1", "CARRIED-ONLY"], current_items=items)
        self.assertEqual(result["blocking_ids"], ["CARRIED-ONLY", "MALFORMED", "P-DROP", "SUCTION", "UNKNOWN"])
        self.assertEqual(result["out_of_scope"], [{"id": "REPORT-1", "scope": ["report"],
                       "next_action": "Update the caption after the client reviews it."}])
        self.assertNotIn("REPORT-1", result["criteria_by_id"])

    def test_original_outside_scope_keeps_followup_without_current_register_row(self):
        self.issues["REPORT-1"] = [{"scope": ["report"], "recommended_change": "Repair the caption."}]
        result = self.plan()
        self.assertEqual(result["out_of_scope"], [{"id": "REPORT-1", "scope": ["report"],
                                                  "next_action": "Repair the caption."}])
        self.assertEqual(result["blocking_ids"], ["P-DROP"])

    def test_conflicting_or_cyclic_confirmations_keep_original_rules(self):
        first = self.user_record("first.json")
        conflict = self.user_record("another.json", new_criterion={**self.updated, "expected": 166})
        self.assert_rejected(self.plan(first, conflict))
        cycle = self.user_record("reverse.json", old_criterion=self.updated, new_criterion=self.original)
        self.assert_rejected(self.plan(first, cycle))


if __name__ == "__main__":
    unittest.main()
