import csv
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from build_phase1_acceptance_report import build_report, manifest_int


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class Phase1AcceptanceReportTests(unittest.TestCase):
    def test_manifest_zero_is_a_valid_integer(self) -> None:
        self.assertEqual(manifest_int({"figure_record_count": 0}, "figure_record_count"), 0)
        self.assertEqual(manifest_int({"figure_record_count": "0"}, "figure_record_count"), 0)
        self.assertEqual(manifest_int({}, "figure_record_count"), -1)

    def test_zero_figure_records_do_not_create_a_false_count_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "sources.csv"
            tables = root / "tables.csv"
            figures = root / "figures.csv"
            database = root / "store.sqlite"
            manifest = root / "manifest.json"

            write_csv(source, ["digitization_state", "authority_status"], [])
            write_csv(tables, ["key_table_candidate", "audit_status", "authority_status"], [])
            write_csv(figures, ["audit_status"], [])
            connection = sqlite3.connect(database)
            try:
                connection.execute("CREATE TABLE standard_records (record_id TEXT)")
                connection.execute("CREATE TABLE figure_records (figure_record_id TEXT)")
                connection.commit()
            finally:
                connection.close()
            manifest.write_text(
                json.dumps(
                    {
                        "sqlite_path": str(database),
                        "record_count": 0,
                        "figure_record_count": 0,
                        "csv_sqlite_row_count_equal": True,
                        "figure_csv_sqlite_row_count_equal": True,
                        "source_document_runtime_access": "FORBIDDEN",
                        "source_image_runtime_access": "FORBIDDEN",
                        "vision_capability": False,
                    }
                ),
                encoding="utf-8",
            )

            report = build_report(source, tables, figures, manifest)

            self.assertEqual(report["status"], "PASS")
            self.assertFalse(
                any(blocker["code"].endswith("COUNT_MISMATCH") for blocker in report["blockers"])
            )


if __name__ == "__main__":
    unittest.main()
