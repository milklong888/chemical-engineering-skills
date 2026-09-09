from __future__ import annotations

import unittest

from build_full_source_clearance_ledger import build_clearance_rows


class FullSourceClearanceLedgerTests(unittest.TestCase):
    def test_only_formal_zero_counts_close_a_source(self) -> None:
        queue = [
            {
                "queue_rank": "1", "source_id": "a", "standard_id": "A",
                "unresolved_key_table_count": "0", "unresolved_figure_count": "0",
                "unresolved_total": "0", "canonical_relative_path": "a.pdf",
            },
            {
                "queue_rank": "2", "source_id": "b", "standard_id": "B",
                "unresolved_key_table_count": "3", "unresolved_figure_count": "2",
                "unresolved_total": "5", "canonical_relative_path": "b.pdf",
            },
        ]
        rows = build_clearance_rows(
            queue,
            assignments={"b": "agent-b"},
            model_gates={"a": "PASS"},
            supplemental_obligations={},
        )
        self.assertEqual(rows[0]["clearance_status"], "FORMAL_CLOSED")
        self.assertEqual(rows[0]["model_gate_status"], "PASS")
        self.assertEqual(rows[1]["clearance_status"], "IN_PROGRESS")
        self.assertEqual(rows[1]["assignee"], "agent-b")

    def test_unassigned_unresolved_source_stays_pending(self) -> None:
        rows = build_clearance_rows(
            [{
                "queue_rank": "4", "source_id": "c", "standard_id": "C",
                "unresolved_key_table_count": "1", "unresolved_figure_count": "0",
                "unresolved_total": "1", "canonical_relative_path": "c.pdf",
            }],
            assignments={}, model_gates={}, supplemental_obligations={},
        )
        self.assertEqual(rows[0]["clearance_status"], "PENDING")
        self.assertEqual(
            rows[0]["closure_rule"],
            "FORMAL_COUNTS_ZERO_AND_QUANT_MODEL_GATE_PASS",
        )

    def test_zero_source_counts_without_model_gate_stays_open(self) -> None:
        rows = build_clearance_rows(
            [{
                "queue_rank": "1", "source_id": "a", "standard_id": "A",
                "unresolved_key_table_count": "0", "unresolved_figure_count": "0",
                "unresolved_total": "0", "canonical_relative_path": "a.pdf",
            }],
            assignments={},
            model_gates={},
            supplemental_obligations={},
        )
        self.assertEqual(rows[0]["clearance_status"], "MODEL_GATE_PENDING")
        self.assertEqual(rows[0]["model_gate_status"], "NOT_ASSESSED")

    def test_discovered_supplemental_assets_prevent_false_closure(self) -> None:
        rows = build_clearance_rows(
            [{
                "queue_rank": "1", "source_id": "a", "standard_id": "A",
                "unresolved_key_table_count": "0", "unresolved_figure_count": "0",
                "unresolved_total": "0", "canonical_relative_path": "a.pdf",
            }],
            assignments={},
            model_gates={"a": "PASS"},
            supplemental_obligations={"a": (2, 1)},
        )
        self.assertEqual(rows[0]["clearance_status"], "PENDING")
        self.assertEqual(rows[0]["supplemental_unresolved_key_tables"], 2)
        self.assertEqual(rows[0]["supplemental_unresolved_figures"], 1)
        self.assertEqual(rows[0]["effective_unresolved_total"], 3)


if __name__ == "__main__":
    unittest.main()
