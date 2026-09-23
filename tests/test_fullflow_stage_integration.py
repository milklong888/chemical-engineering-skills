"""Integration negatives for the whole-flow gate. Synthetic; never runs Aspen."""
from __future__ import annotations
import copy
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_design_stage as stage_tests
from tools.product_contract import schema


class FullflowStageIntegration(stage_tests.DesignStageTests):
    def whole(self, stage="delivery"):
        return {**self.payload, "stage": stage}

    def scope_result(self):
        return {"required": True, "status": "EVIDENCE_STRUCTURE_CONSISTENT",
                "needs": [], "required_reading": [],
                "gate_summary": {"equipment_scope": {"whole_flow_required": True}},
                "engineering_accepted": False}

    def test_fullflow_semantics_without_contract_cannot_report_complete(self):
        result = self.check({"stage": "source", "question": "根据自然语言生成全流程"})
        self.assertTrue(result["fullflow_gate"]["required"])
        self.assertEqual(result["status"], "ACTION_REQUIRED")
        self.assertTrue(result["fullflow_gate"]["needs"])

    def test_fullflow_contract_field_is_discoverable(self):
        self.assertIn("fullflow_contract", schema("design-stage", self.equipment_spy)["properties"])
        self.assertIsInstance(schema("fullflow-contract", self.equipment_spy), dict)

    def test_whole_export_missing_tag_blocks_without_discarding_good_calculation(self):
        exported = copy.deepcopy(self.export)
        exported["equipment"]["SYN-MISSING-PUMP"] = copy.deepcopy(exported["equipment"]["SYN-E1"])
        payload = {**self.whole(), "source_export": self.put("whole-export.json", exported)}
        with patch("tools.fullflow_gate.check_fullflow", return_value=self.scope_result()):
            result = self.check(payload)
        self.assertIn("EXPORTED_DEVICES_NOT_REQUESTED", {x["code"] for x in result["needs"]})
        self.assertEqual(result["equipment"][0]["result"]["backend_exit_code"], 0)
        self.assertEqual(result["status"], "ACTION_REQUIRED")
        self.assertFalse(result["inventory_coverage"]["independently_verified_complete"])

    def test_whole_export_exact_tag_set_is_only_structural_coverage(self):
        with patch("tools.fullflow_gate.check_fullflow", return_value=self.scope_result()):
            result = self.check(self.whole())
        self.assertEqual(result["inventory_coverage"]["scope"], "WHOLE_EXPORTED_PHYSICAL_INVENTORY")
        self.assertTrue(result["inventory_coverage"]["export_request_set_equal"])
        self.assertFalse(result["engineering_accepted"])
        self.assertFalse(result["stage_advanced"])

    def test_stale_workflow_reference_keeps_stage_incomplete(self):
        payload = {**self.payload, "fullflow_contract": {"path": "absent.json", "sha256": "0"*64}}
        result = self.check(payload)
        self.assertEqual(result["fullflow_gate"]["status"], "ACTION_REQUIRED")
        self.assertEqual(result["status"], "ACTION_REQUIRED")
        self.assertEqual(result["equipment"][0]["result"]["backend_exit_code"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
