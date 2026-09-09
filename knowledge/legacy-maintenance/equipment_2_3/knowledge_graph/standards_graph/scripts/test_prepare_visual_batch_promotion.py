import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("prepare_visual_batch_promotion.py")
SPEC = importlib.util.spec_from_file_location("prepare_visual_batch_promotion", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class PrepareVisualBatchPromotionTests(unittest.TestCase):
    def test_unique_rejects_duplicate(self):
        with self.assertRaises(ValueError):
            MODULE.ensure_unique([{"id": "A"}, {"id": "A"}], "id", "sample")

    def test_common_dataset_hashes_source_csv(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.csv"
            source.write_text("kind,value\nx,1\n", encoding="utf-8")
            audit = root / "audit.md"
            audit.write_text("x" * 250, encoding="utf-8")
            row = MODULE.common_dataset_row(
                dataset_id="d", subject="s", standard_id="std",
                standard_version="1", source_id="source", source_sha256="A" * 64,
                source_csv=source, filter_field="kind", filter_values="x",
                reuse_class="METHOD_ONLY", audit_path=audit,
                approved_utc="2026-07-20T00:00:00Z", notes="n",
            )
            self.assertEqual(row["source_csv_sha256"], MODULE.sha256_path(source))
            self.assertEqual(row["promotion_state"], "APPROVED")

    def test_json_cell_is_deterministic(self):
        self.assertEqual(MODULE.json_cell({"b": 2, "a": 1}), '{"a": 1, "b": 2}')

    def test_distinct_duplicate_ids_get_stable_suffixes(self):
        rows = [
            {"record_id": "A", "value": "organic"},
            {"record_id": "A", "value": "inorganic"},
        ]
        repaired1, ledger1 = MODULE.repair_distinct_duplicate_ids(rows, "record_id")
        repaired2, ledger2 = MODULE.repair_distinct_duplicate_ids(rows, "record_id")
        self.assertEqual(repaired1, repaired2)
        self.assertEqual(ledger1, ledger2)
        self.assertEqual(len({row["record_id"] for row in repaired1}), 2)
        self.assertTrue(all(":variant_" in row["record_id"] for row in repaired1))

    def test_exact_duplicate_ids_remain_failure(self):
        rows = [
            {"record_id": "A", "value": "same"},
            {"record_id": "A", "value": "same"},
        ]
        with self.assertRaises(ValueError):
            MODULE.repair_distinct_duplicate_ids(rows, "record_id")

    def test_terminal_overlay_preserves_nonreviewed_rows(self):
        baseline = [
            {"figure_id": "A", "terminal_class": "SEMANTIC_TRANSCRIPTION_PENDING"},
            {"figure_id": "B", "terminal_class": "METHOD_ONLY"},
        ]
        replacement = [
            {"figure_id": "A", "terminal_class": "DIMENSION_STRUCTURE"},
            {"figure_id": "B", "terminal_class": "METHOD_ONLY"},
        ]
        MODULE.validate_terminal_overlay_no_regression(baseline, replacement, {"A"})
        replacement[1]["terminal_class"] = "DIMENSION_STRUCTURE"
        with self.assertRaises(ValueError):
            MODULE.validate_terminal_overlay_no_regression(baseline, replacement, {"A"})

    def test_candidate_crop_references_require_unique_exact_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            crop = root / "evidence" / "p0001_f01.png"
            crop.parent.mkdir()
            crop.write_bytes(b"exact-crop")
            row = {
                "figure_id": "source:p0001:f01",
                "crop_relative_path": "evidence/p0001_f01.png",
                "crop_sha256": MODULE.sha256_path(crop),
            }
            MODULE.validate_candidate_crop_references(root, [row])
            with self.assertRaises(ValueError):
                MODULE.validate_candidate_crop_references(root, [row, dict(row)])

    def test_common_dataset_allows_nonpiping_family(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.csv"
            source.write_text("kind,value\nx,1\n", encoding="utf-8")
            audit = root / "audit.md"
            audit.write_text("x" * 250, encoding="utf-8")
            row = MODULE.common_dataset_row(
                dataset_id="d", subject="s", standard_id="std",
                standard_version="1", source_id="source", source_sha256="A" * 64,
                source_csv=source, filter_field="kind", filter_values="x",
                reuse_class="DIRECT_REUSE_VERIFIED", audit_path=audit,
                approved_utc="2026-07-20T00:00:00Z", notes="n",
                equipment_family="vessel_or_storage",
            )
            self.assertEqual(row["equipment_family"], "vessel_or_storage")


if __name__ == "__main__":
    unittest.main()
