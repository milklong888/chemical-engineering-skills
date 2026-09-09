import unittest

from reconcile_promoted_figure_manifest import reconcile


class ReconcilePromotedFigureManifestTests(unittest.TestCase):
    def test_reconciles_only_exact_verified_approved_zero_gap_dataset(self):
        manifest = [
            {
                "source_id": "S1",
                "figure_id": "F1",
                "source_pdf_sha256": "ABC",
                "audit_status": "NEEDS_REVIEW",
                "reviewer_note": "",
            },
            {
                "source_id": "S1",
                "figure_id": "F2",
                "source_pdf_sha256": "ABC",
                "audit_status": "NEEDS_REVIEW",
                "reviewer_note": "",
            },
        ]
        registry = [
            {
                "dataset_id": "D1",
                "source_id": "S1",
                "promotion_state": "APPROVED",
                "qa_status": "VERIFIED",
                "unresolved_entities": "0",
                "vision_disabled_replay_status": "PASS",
            },
            {
                "dataset_id": "D2",
                "source_id": "S1",
                "promotion_state": "CANDIDATE",
                "qa_status": "VERIFIED",
                "unresolved_entities": "0",
                "vision_disabled_replay_status": "PASS",
            },
        ]
        records = [
            {
                "dataset_id": "D1",
                "source_id": "S1",
                "figure_id": "F1",
                "source_sha256": "ABC",
                "reuse_class": "DIRECT_REUSE_VERIFIED",
                "qa_status": "VERIFIED",
            },
            {
                "dataset_id": "D2",
                "source_id": "S1",
                "figure_id": "F2",
                "source_sha256": "ABC",
                "reuse_class": "DIRECT_REUSE_VERIFIED",
                "qa_status": "VERIFIED",
            },
        ]

        result, report = reconcile(manifest, registry, records)

        self.assertEqual(result[0]["audit_status"], "DIRECT_REUSE_VERIFIED")
        self.assertEqual(result[0]["structured_dataset_id"], "D1")
        self.assertEqual(result[1]["audit_status"], "NEEDS_REVIEW")
        self.assertEqual(report["reconciled_row_count"], 1)

    def test_hash_mismatch_stays_fail_closed(self):
        manifest = [{
            "source_id": "S1", "figure_id": "F1", "source_pdf_sha256": "ABC",
            "audit_status": "NEEDS_REVIEW", "reviewer_note": "",
        }]
        registry = [{
            "dataset_id": "D1", "source_id": "S1", "promotion_state": "APPROVED",
            "qa_status": "VERIFIED", "unresolved_entities": "0",
            "vision_disabled_replay_status": "PASS",
        }]
        records = [{
            "dataset_id": "D1", "source_id": "S1", "figure_id": "F1",
            "source_sha256": "OTHER", "reuse_class": "DIRECT_REUSE_VERIFIED",
            "qa_status": "VERIFIED",
        }]

        result, report = reconcile(manifest, registry, records)

        self.assertEqual(result[0]["audit_status"], "NEEDS_REVIEW")
        self.assertEqual(report["rejected_counts"], {"SOURCE_HASH_MISMATCH": 1})


if __name__ == "__main__":
    unittest.main()
