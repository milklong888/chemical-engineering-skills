from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

try:
    from audit_multi_bkp_overview_gate import discover_result_paths, missing_authority_overview_fields
except ModuleNotFoundError:
    from scripts.audit_multi_bkp_overview_gate import discover_result_paths, missing_authority_overview_fields


class MultiBkpOverviewGateTests(unittest.TestCase):
    def test_preliminary_overview_rejects_blank_or_external_only_cells(self) -> None:
        fields = missing_authority_overview_fields([
            {"field_id": "equipment_tag", "value": "P-101", "state": "PROVIDED"},
            {"field_id": "equipment_type", "value": "轴向吸入离心泵", "state": "DETERMINISTIC_TERMINAL_TYPE"},
            {"field_id": "material", "value": None, "state": "MISSING"},
            {"field_id": "efficiency_percent", "value": None, "state": "EXTERNAL_REQUIRED"},
            {"field_id": "quantity_count", "value": 1, "state": "DEFAULTED"},
        ])

        self.assertEqual(fields, ["efficiency_percent", "material"])

    def test_preliminary_overview_accepts_visible_warned_defaults(self) -> None:
        fields = missing_authority_overview_fields([
            {"field_id": "material", "value": "碳钢（预设计基线）", "state": "DEFAULTED"},
            {"field_id": "quantity_count", "value": 1, "state": "DEFAULTED"},
        ])

        self.assertEqual(fields, [])

    def test_discovers_single_replay_and_batch_case_results(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            single = root / "equipment_derivation_result.json"
            batch = root / "case_001" / "equipment_derivation_result.json"
            single.write_text("{}", encoding="utf-8")
            batch.parent.mkdir()
            batch.write_text("{}", encoding="utf-8")

            self.assertEqual(discover_result_paths(root), [single, batch])


if __name__ == "__main__":
    unittest.main()
