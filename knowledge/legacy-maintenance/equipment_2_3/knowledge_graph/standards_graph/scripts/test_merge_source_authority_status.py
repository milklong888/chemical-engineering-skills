from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from merge_source_authority_status import merge_inventory


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class SourceAuthorityMergeTest(unittest.TestCase):
    def test_hash_join_and_nonstandard_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sources = [
                {"source_id": "std_a", "sha256": "A" * 64, "source_kind": "standard", "authority_status": "UNVERIFIED"},
                {"source_id": "book_b", "sha256": "B" * 64, "source_kind": "textbook", "authority_status": "UNVERIFIED"},
            ]
            authority = [
                {
                    "source_id": "std_a", "source_sha256": "A" * 64,
                    "authority_state": "CURRENT", "lifecycle_state": "CURRENT",
                    "verification_status": "OFFICIAL_EXACT_MATCH", "matched_code": "GB/T A",
                    "official_detail_url": "https://example.invalid/a",
                    "replacement_relation": "", "resolution_evidence_path": "",
                    "resolution_evidence_sha256": "",
                }
            ]
            source_path = root / "sources.csv"
            authority_path = root / "authority.csv"
            write_csv(source_path, sources, list(sources[0]))
            write_csv(authority_path, authority, list(authority[0]))
            rows, summary = merge_inventory(source_path, authority_path)
            self.assertEqual(rows[0]["authority_status"], "CURRENT")
            self.assertEqual(rows[1]["authority_status"], "NOT_APPLICABLE_SOURCE_KIND")
            self.assertEqual(summary["unresolved_standard_count"], 0)

    def test_hash_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_path = root / "sources.csv"
            authority_path = root / "authority.csv"
            write_csv(
                source_path,
                [{"source_id": "std_a", "sha256": "A" * 64, "source_kind": "standard"}],
                ["source_id", "sha256", "source_kind"],
            )
            write_csv(
                authority_path,
                [{"source_id": "std_a", "source_sha256": "B" * 64}],
                ["source_id", "source_sha256"],
            )
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                merge_inventory(source_path, authority_path)


if __name__ == "__main__":
    unittest.main()
