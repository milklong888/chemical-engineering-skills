from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from build_executable_data_inventory import build_inventory, registry_candidates


class ExecutableDataInventoryTest(unittest.TestCase):
    def test_hash_dedup_obsolete_and_unextracted_states(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            source.mkdir()
            (source / "管道设计").mkdir()
            (source / "塔设备设计").mkdir()
            payload = b"same-pdf"
            (source / "管道设计" / "GB_T1047-2019管道元件.pdf").write_bytes(payload)
            (source / "塔设备设计" / "GB_T1047-2019副本.pdf").write_bytes(payload)
            (source / "管道设计" / "GB_T5780-2000废止.pdf").write_bytes(b"old")

            registry = root / "registry.csv"
            with registry.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["doc_id", "relative_path"])
                writer.writeheader()
                writer.writerow(
                    {
                        "doc_id": "std_gb_t_1047_2019",
                        "relative_path": "管道设计/GB_T1047-2019管道元件.pdf",
                    }
                )

            rows, summary = build_inventory(
                source, registry, root / "documents", root / "provenance"
            )
            self.assertEqual(summary["physical_file_count"], 3)
            self.assertEqual(summary["unique_source_count"], 2)
            current = next(row for row in rows if row["standard_id"] == "GB/T 1047-2019")
            self.assertEqual(current["duplicate_copy_count"], 2)
            self.assertEqual(current["existing_doc_id"], "std_gb_t_1047_2019")
            self.assertEqual(current["digitization_state"], "NOT_EXTRACTED")
            obsolete = next(row for row in rows if "5780" in row["standard_id"])
            self.assertEqual(obsolete["authority_status"], "OBSOLETE_FORBIDDEN")
            self.assertEqual(obsolete["digitization_state"], "OBSOLETE_FORBIDDEN")
            candidates = registry_candidates(rows)
            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0]["source_kind"], "obsolete_standard")
            self.assertEqual(candidates[0]["evidence_default"], "S0")

    def test_existing_package_does_not_become_executable_without_reuse_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            source.mkdir()
            pdf = source / "GB_T17395-2024钢管尺寸.pdf"
            pdf.write_bytes(b"pdf")
            import hashlib

            source_hash = hashlib.sha256(b"pdf").hexdigest().upper()
            documents = root / "documents" / "std_gb_t_17395_2024"
            documents.mkdir(parents=True)
            (documents / "status.json").write_text(
                json.dumps(
                    {
                        "status": "PASS_WITH_REVIEW",
                        "source_pdf_sha256": source_hash,
                        "page_count": 55,
                        "table_count": 78,
                        "manual_review_pages": [8],
                    }
                ),
                encoding="utf-8",
            )
            with (documents / "tables.csv").open(
                "w", encoding="utf-8-sig", newline=""
            ) as handle:
                writer = csv.DictWriter(
                    handle, fieldnames=["table_id", "numeric_reuse_allowed"]
                )
                writer.writeheader()
                writer.writerow(
                    {"table_id": "t1", "numeric_reuse_allowed": "False"}
                )
            registry = root / "registry.csv"
            registry.write_text("doc_id,relative_path\n", encoding="utf-8-sig")
            rows, _ = build_inventory(source, registry, documents.parent, root / "provenance")
            self.assertEqual(rows[0]["digitization_state"], "EXTRACTED_NOT_EXECUTABLE")
            self.assertEqual(rows[0]["numeric_reuse_table_count"], 0)
            self.assertEqual(rows[0]["verified_executable_table_count"], 0)

    def test_raw_reuse_flag_is_not_promoted_to_verified_executable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            source.mkdir()
            pdf = source / "GB_T150.2-2024材料.pdf"
            pdf.write_bytes(b"pdf-with-raw-reuse-flag")
            import hashlib

            source_hash = hashlib.sha256(b"pdf-with-raw-reuse-flag").hexdigest().upper()
            documents = root / "documents" / "std_gb_t_150_2_2024"
            documents.mkdir(parents=True)
            (documents / "status.json").write_text(
                json.dumps(
                    {
                        "status": "PASS_WITH_REVIEW",
                        "source_pdf_sha256": source_hash,
                        "page_count": 10,
                        "table_count": 1,
                        "manual_review_pages": [],
                    }
                ),
                encoding="utf-8",
            )
            with (documents / "tables.csv").open(
                "w", encoding="utf-8-sig", newline=""
            ) as handle:
                writer = csv.DictWriter(
                    handle, fieldnames=["table_id", "numeric_reuse_allowed"]
                )
                writer.writeheader()
                writer.writerow(
                    {"table_id": "t1", "numeric_reuse_allowed": "True"}
                )
            registry = root / "registry.csv"
            registry.write_text("doc_id,relative_path\n", encoding="utf-8-sig")
            rows, _ = build_inventory(source, registry, documents.parent, root / "provenance")
            self.assertEqual(
                rows[0]["digitization_state"], "RAW_REUSE_FLAG_PENDING_CELL_AUDIT"
            )
            self.assertEqual(rows[0]["numeric_reuse_table_count"], 1)
            self.assertEqual(rows[0]["verified_executable_table_count"], 0)

    def test_hash_bound_verified_cover_identity_overrides_filename_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            source.mkdir()
            payload = b"gbt-151-cover"
            (source / "GB151-2014热交换器.pdf").write_bytes(payload)
            import hashlib

            source_hash = hashlib.sha256(payload).hexdigest().upper()
            overrides = root / "identity_overrides.csv"
            with overrides.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "source_sha256",
                        "verified_standard_id",
                        "verified_standard_year",
                        "qa_status",
                        "evidence",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "source_sha256": source_hash,
                        "verified_standard_id": "GB/T 151-2014",
                        "verified_standard_year": "2014",
                        "qa_status": "VERIFIED",
                        "evidence": "cover page 1",
                    }
                )
            registry = root / "registry.csv"
            registry.write_text("doc_id,relative_path\n", encoding="utf-8-sig")
            rows, _ = build_inventory(
                source,
                registry,
                root / "documents",
                root / "provenance",
                overrides,
            )
            self.assertEqual(rows[0]["filename_standard_id"], "GB 151-2014")
            self.assertEqual(rows[0]["standard_id"], "GB/T 151-2014")
            self.assertEqual(rows[0]["identity_qa_status"], "VERIFIED")

    def test_hash_bound_zero_page_override_terminally_blocks_only_that_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            source.mkdir()
            payload = b"zero-page-pdf-container"
            (source / "reference.pdf").write_bytes(payload)
            import hashlib

            source_hash = hashlib.sha256(payload).hexdigest().upper()
            overrides = root / "source_state_overrides.csv"
            with overrides.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["source_sha256", "terminal_class", "qa_status", "evidence"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "source_sha256": source_hash,
                        "terminal_class": "SOURCE_UNREADABLE_BLOCKED",
                        "qa_status": "VERIFIED",
                        "evidence": "PyMuPDF page_count=0",
                    }
                )
            registry = root / "registry.csv"
            registry.write_text("doc_id,relative_path\n", encoding="utf-8-sig")
            rows, _ = build_inventory(
                source,
                registry,
                root / "documents",
                root / "provenance",
                None,
                overrides,
            )
            self.assertEqual(rows[0]["digitization_state"], "SOURCE_UNREADABLE_BLOCKED")
            self.assertEqual(rows[0]["source_terminal_qa_status"], "VERIFIED")


if __name__ == "__main__":
    unittest.main()
