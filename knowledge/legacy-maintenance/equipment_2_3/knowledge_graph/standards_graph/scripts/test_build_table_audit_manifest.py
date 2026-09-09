from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from build_table_audit_manifest import build_manifest, proposed_class


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class TableAuditManifestTest(unittest.TestCase):
    def test_withdrawn_standard_is_forbidden(self) -> None:
        self.assertEqual(proposed_class("standard", "WITHDRAWN"), "OBSOLETE_FORBIDDEN")

    def test_hash_bound_page_promotion_is_applied(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            documents = root / "documents"
            package = documents / "std_promoted"
            package.mkdir(parents=True)
            payload = b"standard"
            source_hash = hashlib.sha256(payload).hexdigest().upper()
            (package / "status.json").write_text(
                json.dumps({"doc_id": "std_promoted", "source_pdf_sha256": source_hash}),
                encoding="utf-8",
            )
            table_path = package / "tables" / "p0003_t01.csv"
            cells_path = package / "tables" / "p0003_t01_cells.csv"
            write_csv(table_path, [{"DN": "50"}], ["DN"])
            write_csv(cells_path, [{"raw_text": "50", "ocr_confidence": "99"}], ["raw_text", "ocr_confidence"])
            write_csv(
                package / "tables.csv",
                [{
                    "table_id": "std_promoted:p0003:t01", "page_1based": "3", "table_order": "1",
                    "row_count": "1", "column_count": "1", "nonempty_cells": "1", "method": "native",
                    "geometry_preserved": "True", "structure_confidence": "1", "numeric_reuse_allowed": "False",
                    "csv_path": "tables/p0003_t01.csv", "cell_audit_csv_path": "tables/p0003_t01_cells.csv", "caption": "DN",
                }],
                ["table_id", "page_1based", "table_order", "row_count", "column_count", "nonempty_cells", "method", "geometry_preserved", "structure_confidence", "numeric_reuse_allowed", "csv_path", "cell_audit_csv_path", "caption"],
            )
            inventory = root / "inventory.csv"
            write_csv(
                inventory,
                [{"source_id": "std_promoted", "sha256": source_hash, "standard_id": "GB/T X", "standard_year": "2024", "source_kind": "standard", "families_json": '["piping"]', "authority_status": "CURRENT"}],
                ["source_id", "sha256", "standard_id", "standard_year", "source_kind", "families_json", "authority_status"],
            )
            evidence = root / "audit.md"
            evidence.write_text("verified\n", encoding="utf-8")
            rules = root / "rules.csv"
            write_csv(
                rules,
                [{"rule_id": "r1", "source_id": "std_promoted", "source_pdf_sha256": source_hash, "page_from": "3", "page_to": "3", "audit_status": "DIRECT_REUSE_VERIFIED", "executable_dataset_ids": "ds1", "qa_status": "VERIFIED", "evidence_path": str(evidence), "evidence_sha256": hashlib.sha256(evidence.read_bytes()).hexdigest().upper(), "note": "verified"}],
                ["rule_id", "source_id", "source_pdf_sha256", "page_from", "page_to", "audit_status", "executable_dataset_ids", "qa_status", "evidence_path", "evidence_sha256", "note"],
            )
            rows, summary = build_manifest(inventory, documents, rules)
            self.assertEqual(rows[0]["audit_status"], "DIRECT_REUSE_VERIFIED")
            self.assertEqual(rows[0]["executable_dataset_id"], "ds1")
            self.assertEqual(summary["promoted_table_count"], 1)

    def test_exact_table_ids_do_not_promote_neighbor_on_same_page(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            documents = root / "documents"
            package = documents / "std_exact"
            package.mkdir(parents=True)
            source_hash = hashlib.sha256(b"standard").hexdigest().upper()
            (package / "status.json").write_text(
                json.dumps({"doc_id": "std_exact", "source_pdf_sha256": source_hash}),
                encoding="utf-8",
            )
            table_rows = []
            for order in (1, 2):
                table_id = f"std_exact:p0003:t{order:02d}"
                table_path = package / "tables" / f"p0003_t{order:02d}.csv"
                cells_path = package / "tables" / f"p0003_t{order:02d}_cells.csv"
                write_csv(table_path, [{"DN": str(40 + 10 * order)}], ["DN"])
                write_csv(cells_path, [{"raw_text": str(40 + 10 * order), "ocr_confidence": "99"}], ["raw_text", "ocr_confidence"])
                table_rows.append({
                    "table_id": table_id, "page_1based": "3", "table_order": str(order),
                    "row_count": "1", "column_count": "1", "nonempty_cells": "1", "method": "native",
                    "geometry_preserved": "True", "structure_confidence": "1", "numeric_reuse_allowed": "False",
                    "csv_path": f"tables/p0003_t{order:02d}.csv",
                    "cell_audit_csv_path": f"tables/p0003_t{order:02d}_cells.csv", "caption": "DN",
                })
            fields = ["table_id", "page_1based", "table_order", "row_count", "column_count", "nonempty_cells", "method", "geometry_preserved", "structure_confidence", "numeric_reuse_allowed", "csv_path", "cell_audit_csv_path", "caption"]
            write_csv(package / "tables.csv", table_rows, fields)
            inventory = root / "inventory.csv"
            write_csv(
                inventory,
                [{"source_id": "std_exact", "sha256": source_hash, "standard_id": "GB/T X", "standard_year": "2024", "source_kind": "standard", "families_json": '["piping"]', "authority_status": "CURRENT"}],
                ["source_id", "sha256", "standard_id", "standard_year", "source_kind", "families_json", "authority_status"],
            )
            evidence = root / "audit.md"
            evidence.write_text("verified\n", encoding="utf-8")
            rules = root / "rules.csv"
            write_csv(
                rules,
                [{"rule_id": "r_exact", "source_id": "std_exact", "source_pdf_sha256": source_hash, "table_ids": "std_exact:p0003:t01", "page_from": "", "page_to": "", "audit_status": "DIRECT_REUSE_VERIFIED", "executable_dataset_ids": "ds1", "qa_status": "VERIFIED", "evidence_path": str(evidence), "evidence_sha256": hashlib.sha256(evidence.read_bytes()).hexdigest().upper(), "note": "exact"}],
                ["rule_id", "source_id", "source_pdf_sha256", "table_ids", "page_from", "page_to", "audit_status", "executable_dataset_ids", "qa_status", "evidence_path", "evidence_sha256", "note"],
            )
            rows, summary = build_manifest(inventory, documents, rules)
            self.assertEqual(rows[0]["audit_status"], "DIRECT_REUSE_VERIFIED")
            self.assertEqual(rows[1]["audit_status"], "NEEDS_REVIEW")
            self.assertEqual(summary["promoted_table_count"], 1)

    def test_exact_table_id_can_close_superseded_internal_table(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            documents = root / "documents"
            package = documents / "std_exact"
            package.mkdir(parents=True)
            source_hash = hashlib.sha256(b"standard").hexdigest().upper()
            (package / "status.json").write_text(
                json.dumps({"doc_id": "std_exact", "source_pdf_sha256": source_hash}),
                encoding="utf-8",
            )
            write_csv(package / "tables" / "p0010_t01.csv", [{"old": "1"}], ["old"])
            write_csv(
                package / "tables" / "p0010_t01_cells.csv",
                [{"raw_text": "1", "ocr_confidence": "99"}],
                ["raw_text", "ocr_confidence"],
            )
            write_csv(
                package / "tables.csv",
                [{
                    "table_id": "std_exact:p0010:t01", "page_1based": "10", "table_order": "1",
                    "row_count": "1", "column_count": "1", "nonempty_cells": "1", "method": "native",
                    "geometry_preserved": "True", "structure_confidence": "1", "numeric_reuse_allowed": "False",
                    "csv_path": "tables/p0010_t01.csv", "cell_audit_csv_path": "tables/p0010_t01_cells.csv",
                    "caption": "superseded erratum",
                }],
                ["table_id", "page_1based", "table_order", "row_count", "column_count", "nonempty_cells", "method", "geometry_preserved", "structure_confidence", "numeric_reuse_allowed", "csv_path", "cell_audit_csv_path", "caption"],
            )
            inventory = root / "inventory.csv"
            write_csv(
                inventory,
                [{"source_id": "std_exact", "sha256": source_hash, "standard_id": "HG/T X", "standard_year": "2009", "source_kind": "standard", "families_json": '["piping"]', "authority_status": "CURRENT"}],
                ["source_id", "sha256", "standard_id", "standard_year", "source_kind", "families_json", "authority_status"],
            )
            evidence = root / "audit.md"
            evidence.write_text("later confirmed erratum supersedes this table\n", encoding="utf-8")
            rules = root / "rules.csv"
            write_csv(
                rules,
                [{"rule_id": "r_obsolete", "source_id": "std_exact", "source_pdf_sha256": source_hash, "table_ids": "std_exact:p0010:t01", "page_from": "", "page_to": "", "audit_status": "OBSOLETE_FORBIDDEN", "executable_dataset_ids": "", "qa_status": "VERIFIED", "evidence_path": str(evidence), "evidence_sha256": hashlib.sha256(evidence.read_bytes()).hexdigest().upper(), "note": "superseded"}],
                ["rule_id", "source_id", "source_pdf_sha256", "table_ids", "page_from", "page_to", "audit_status", "executable_dataset_ids", "qa_status", "evidence_path", "evidence_sha256", "note"],
            )
            rows, summary = build_manifest(inventory, documents, rules)
            self.assertEqual(rows[0]["audit_status"], "OBSOLETE_FORBIDDEN")
            self.assertEqual(summary["promoted_table_count"], 1)

    def test_standard_table_remains_review_and_book_table_is_forbidden(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            documents = root / "documents"
            sources = []
            for doc_id, source_kind, payload in (
                ("std_pipe", "standard", b"standard"),
                ("book_case", "textbook", b"book"),
            ):
                source_hash = hashlib.sha256(payload).hexdigest().upper()
                sources.append(
                    {
                        "source_id": doc_id,
                        "sha256": source_hash,
                        "standard_id": "GB/T 1-2024" if source_kind == "standard" else "",
                        "standard_year": "2024" if source_kind == "standard" else "",
                        "source_kind": source_kind,
                        "families_json": '["piping"]',
                        "authority_status": "UNVERIFIED",
                    }
                )
                package = documents / doc_id
                package.mkdir(parents=True)
                (package / "status.json").write_text(
                    json.dumps(
                        {
                            "doc_id": doc_id,
                            "source_pdf_sha256": source_hash,
                        }
                    ),
                    encoding="utf-8",
                )
                table_path = package / "tables" / "p0001_t01.csv"
                cells_path = package / "tables" / "p0001_t01_cells.csv"
                write_csv(
                    table_path,
                    [{"尺寸": "DN50", "外径": "60.3"}],
                    ["尺寸", "外径"],
                )
                write_csv(
                    cells_path,
                    [{"raw_text": "60.3", "ocr_confidence": "99"}],
                    ["raw_text", "ocr_confidence"],
                )
                write_csv(
                    package / "tables.csv",
                    [
                        {
                            "table_id": f"{doc_id}:p0001:t01",
                            "page_1based": "1",
                            "table_order": "1",
                            "row_count": "1",
                            "column_count": "2",
                            "nonempty_cells": "2",
                            "method": "native",
                            "geometry_preserved": "True",
                            "structure_confidence": "1.0",
                            "numeric_reuse_allowed": "True",
                            "csv_path": "tables/p0001_t01.csv",
                            "cell_audit_csv_path": "tables/p0001_t01_cells.csv",
                            "caption": "",
                        }
                    ],
                    [
                        "table_id",
                        "page_1based",
                        "table_order",
                        "row_count",
                        "column_count",
                        "nonempty_cells",
                        "method",
                        "geometry_preserved",
                        "structure_confidence",
                        "numeric_reuse_allowed",
                        "csv_path",
                        "cell_audit_csv_path",
                        "caption",
                    ],
                )
            source_inventory = root / "source_inventory.csv"
            write_csv(source_inventory, sources, list(sources[0]))
            rows, summary = build_manifest(source_inventory, documents)
            standard = next(row for row in rows if row["doc_id"] == "std_pipe")
            book = next(row for row in rows if row["doc_id"] == "book_case")
            self.assertEqual(standard["audit_status"], "NEEDS_REVIEW")
            self.assertTrue(standard["key_table_candidate"])
            self.assertEqual(book["audit_status"], "FORBIDDEN_TRANSFER")
            self.assertEqual(summary["direct_reuse_verified_count"], 0)
            self.assertEqual(summary["raw_reuse_flags_ignored_count"], 2)


if __name__ == "__main__":
    unittest.main()
