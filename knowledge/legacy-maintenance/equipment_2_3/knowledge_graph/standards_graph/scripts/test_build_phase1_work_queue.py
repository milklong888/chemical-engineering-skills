import csv
import tempfile
import unittest
from pathlib import Path

from build_phase1_work_queue import build_queue


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class Phase1WorkQueueTests(unittest.TestCase):
    def test_queue_filters_exact_phase1_blockers_and_ranks_current_standards(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = root / "sources.csv"
            tables = root / "tables.csv"
            figures = root / "figures.csv"
            write_csv(
                sources,
                [
                    "source_id",
                    "standard_id",
                    "source_kind",
                    "authority_status",
                    "authority_lifecycle_state",
                    "authority_verification_status",
                    "canonical_relative_path",
                    "sha256",
                ],
                [
                    {
                        "source_id": "std_a",
                        "standard_id": "A",
                        "source_kind": "standard",
                        "authority_status": "CURRENT",
                        "authority_lifecycle_state": "CURRENT",
                        "authority_verification_status": "OFFICIAL_EXACT_MATCH",
                        "canonical_relative_path": "a.pdf",
                        "sha256": "AA",
                    },
                    {
                        "source_id": "book_b",
                        "source_kind": "design_book",
                        "authority_status": "UNRESOLVED",
                        "authority_lifecycle_state": "",
                        "canonical_relative_path": "b.pdf",
                        "sha256": "BB",
                    },
                ],
            )
            write_csv(
                tables,
                [
                    "source_id",
                    "doc_id",
                    "table_id",
                    "key_table_candidate",
                    "audit_status",
                    "page_1based",
                    "families_json",
                    "authority_status",
                    "source_kind",
                ],
                [
                    {
                        "source_id": "std_a",
                        "table_id": "a:t1",
                        "key_table_candidate": "True",
                        "audit_status": "NEEDS_REVIEW",
                        "page_1based": "3",
                        "families_json": '["piping"]',
                        "authority_status": "CURRENT",
                        "source_kind": "standard",
                    },
                    {
                        "source_id": "book_b",
                        "table_id": "b:t1",
                        "key_table_candidate": "False",
                        "audit_status": "NEEDS_REVIEW",
                    },
                ],
            )
            write_csv(
                figures,
                [
                    "source_id",
                    "doc_id",
                    "figure_id",
                    "audit_status",
                    "page_1based",
                    "families_json",
                    "authority_status",
                    "source_kind",
                ],
                [
                    {
                        "source_id": "std_a",
                        "figure_id": "a:f1",
                        "audit_status": "NEEDS_REVIEW",
                        "page_1based": "4",
                        "families_json": '["piping"]',
                        "authority_status": "CURRENT",
                        "source_kind": "standard",
                    },
                    {
                        "source_id": "book_b",
                        "figure_id": "b:f1",
                        "audit_status": "DIRECT_REUSE_VERIFIED",
                    },
                ],
            )

            payload = build_queue(sources, tables, figures)

            self.assertEqual(payload["unresolved_source_count"], 1)
            self.assertEqual(payload["unresolved_key_table_count"], 1)
            self.assertEqual(payload["unresolved_figure_count"], 1)
            record = payload["records"][0]
            self.assertEqual(record["source_id"], "std_a")
            self.assertEqual(record["priority_class"], "P0_CURRENT_STANDARD")
            self.assertEqual(record["unresolved_total"], 2)
            self.assertEqual(record["table_pages"], [3])
            self.assertEqual(record["figure_pages"], [4])


if __name__ == "__main__":
    unittest.main()
