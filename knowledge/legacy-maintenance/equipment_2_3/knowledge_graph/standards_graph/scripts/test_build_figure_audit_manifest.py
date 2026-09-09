from __future__ import annotations

import csv
import hashlib
import json
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from build_figure_audit_manifest import build_manifest, source_boundary


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def png_bytes(width: int = 2, height: int = 3) -> bytes:
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr = b"IHDR" + ihdr_data
    ihdr_chunk = struct.pack(">I", len(ihdr_data)) + ihdr + struct.pack(
        ">I", zlib.crc32(ihdr) & 0xFFFFFFFF
    )
    iend = b"IEND"
    iend_chunk = struct.pack(">I", 0) + iend + struct.pack(
        ">I", zlib.crc32(iend) & 0xFFFFFFFF
    )
    return signature + ihdr_chunk + iend_chunk


class FigureAuditManifestTest(unittest.TestCase):
    def test_withdrawn_standard_is_forbidden(self) -> None:
        self.assertEqual(source_boundary("standard", "WITHDRAWN"), "OBSOLETE_FORBIDDEN")

    def test_reuses_images_but_keeps_standard_curve_pending_and_book_forbidden(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            documents = root / "documents"
            sources = []
            figure_fields = [
                "figure_id",
                "page_1based",
                "figure_order",
                "caption",
                "bbox_pt",
                "method",
                "key_figure",
                "asset_qa_status",
                "image_path",
            ]
            for doc_id, source_kind, caption in (
                ("std_curve", "standard", "图 3 压力温度曲线"),
                ("book_structure", "textbook", "图 4 换热器结构"),
            ):
                payload = doc_id.encode("utf-8")
                source_hash = hashlib.sha256(payload).hexdigest().upper()
                sources.append(
                    {
                        "source_id": doc_id,
                        "sha256": source_hash,
                        "standard_id": "GB/T 1-2024" if source_kind == "standard" else "",
                        "standard_year": "2024" if source_kind == "standard" else "",
                        "source_kind": source_kind,
                        "families_json": '["piping"]',
                        "authority_status": "CURRENT",
                    }
                )
                package = documents / doc_id
                package.mkdir(parents=True)
                (package / "status.json").write_text(
                    json.dumps({"doc_id": doc_id, "source_pdf_sha256": source_hash}),
                    encoding="utf-8",
                )
                image = package / "figures" / "p0001_f01.png"
                image.parent.mkdir()
                image.write_bytes(png_bytes())
                write_csv(
                    package / "figures.csv",
                    [
                        {
                            "figure_id": f"{doc_id}:p0001:f01",
                            "page_1based": "1",
                            "figure_order": "1",
                            "caption": caption,
                            "bbox_pt": "[0,0,10,10]",
                            "method": "caption_crop",
                            "key_figure": "True",
                            "asset_qa_status": "",
                            "image_path": "figures/p0001_f01.png",
                        }
                    ],
                    figure_fields,
                )
            source_inventory = root / "source_inventory.csv"
            write_csv(source_inventory, sources, list(sources[0]))

            rows, summary = build_manifest(source_inventory, documents)
            curve = next(row for row in rows if row["doc_id"] == "std_curve")
            book = next(row for row in rows if row["doc_id"] == "book_structure")
            self.assertEqual(curve["audit_status"], "NEEDS_REVIEW")
            self.assertEqual(
                curve["terminal_class"], "QUANTITATIVE_CURVE_NEEDS_DIGITIZATION"
            )
            self.assertTrue(curve["machine_representation_required"])
            self.assertEqual((curve["image_width_px"], curve["image_height_px"]), (2, 3))
            self.assertTrue(curve["image_sha256"])
            self.assertEqual(book["audit_status"], "FORBIDDEN_TRANSFER")
            self.assertEqual(summary["reused_existing_image_asset_count"], 2)
            self.assertEqual(summary["machine_representation_closed_count"], 0)

    def test_missing_standard_image_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_hash = hashlib.sha256(b"missing").hexdigest().upper()
            write_csv(
                root / "source_inventory.csv",
                [
                    {
                        "source_id": "std_missing",
                        "sha256": source_hash,
                        "standard_id": "GB/T 2-2024",
                        "standard_year": "2024",
                        "source_kind": "standard",
                        "families_json": '["vessel"]',
                        "authority_status": "CURRENT",
                    }
                ],
                [
                    "source_id",
                    "sha256",
                    "standard_id",
                    "standard_year",
                    "source_kind",
                    "families_json",
                    "authority_status",
                ],
            )
            package = root / "documents" / "std_missing"
            package.mkdir(parents=True)
            (package / "status.json").write_text(
                json.dumps({"doc_id": "std_missing", "source_pdf_sha256": source_hash}),
                encoding="utf-8",
            )
            write_csv(
                package / "figures.csv",
                [
                    {
                        "figure_id": "std_missing:p1:f1",
                        "page_1based": "1",
                        "figure_order": "1",
                        "caption": "结构图",
                        "bbox_pt": "[]",
                        "method": "caption_crop",
                        "key_figure": "True",
                        "asset_qa_status": "",
                        "image_path": "figures/missing.png",
                    }
                ],
                [
                    "figure_id",
                    "page_1based",
                    "figure_order",
                    "caption",
                    "bbox_pt",
                    "method",
                    "key_figure",
                    "asset_qa_status",
                    "image_path",
                ],
            )
            rows, summary = build_manifest(
                root / "source_inventory.csv", root / "documents"
            )
            self.assertEqual(rows[0]["audit_status"], "SOURCE_UNREADABLE_BLOCKED")
            self.assertEqual(summary["missing_image_count"], 1)

    def test_hash_locked_terminal_audit_closes_structure_and_nonfigure_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_hash = hashlib.sha256(b"promoted").hexdigest().upper()
            source_id = "std_promoted"
            inventory = root / "source_inventory.csv"
            write_csv(
                inventory,
                [{
                    "source_id": source_id,
                    "sha256": source_hash,
                    "standard_id": "GB/T 3-2024",
                    "standard_year": "2024",
                    "source_kind": "standard",
                    "families_json": '["piping"]',
                    "authority_status": "CURRENT",
                }],
                ["source_id", "sha256", "standard_id", "standard_year", "source_kind", "families_json", "authority_status"],
            )
            package = root / "documents" / source_id
            package.mkdir(parents=True)
            (package / "status.json").write_text(
                json.dumps({"doc_id": source_id, "source_pdf_sha256": source_hash}), encoding="utf-8"
            )
            image_hashes = {}
            figure_rows = []
            for order in (1, 2, 3):
                image = package / "figures" / f"p0001_f0{order}.png"
                image.parent.mkdir(exist_ok=True)
                image.write_bytes(png_bytes(order + 1, 3))
                image_hashes[order] = hashlib.sha256(image.read_bytes()).hexdigest().upper()
                figure_rows.append({
                    "figure_id": f"{source_id}:p0001:f0{order}",
                    "page_1based": "1", "figure_order": str(order), "caption": "",
                    "bbox_pt": "[]", "method": "embedded_image", "key_figure": "False",
                    "asset_qa_status": "", "image_path": f"figures/p0001_f0{order}.png",
                })
            write_csv(package / "figures.csv", figure_rows, list(figure_rows[0]))

            terminal_audit = root / "terminal.csv"
            terminal_rows = [
                {"figure_id": figure_rows[0]["figure_id"], "terminal_class": "DIMENSION_STRUCTURE", "crop_sha256": image_hashes[1], "needs_review": "false", "runtime_requires_image": "false", "structured_record_count": "4", "qa_status": "VERIFIED", "visual_review_basis": "direct", "terminal_reason": "dataized", "minimum_next_evidence": ""},
                {"figure_id": figure_rows[1]["figure_id"], "terminal_class": "NOT_APPLICABLE", "crop_sha256": image_hashes[2], "needs_review": "false", "runtime_requires_image": "false", "structured_record_count": "0", "qa_status": "VERIFIED", "visual_review_basis": "direct", "terminal_reason": "page band", "minimum_next_evidence": ""},
                {"figure_id": figure_rows[2]["figure_id"], "terminal_class": "SEMANTIC_TRANSCRIPTION_PENDING", "crop_sha256": image_hashes[3], "needs_review": "true", "runtime_requires_image": "false", "structured_record_count": "0", "qa_status": "READABILITY_VERIFIED_TRANSCRIPTION_PENDING", "visual_review_basis": "exact crop", "terminal_reason": "readable but not dataized", "minimum_next_evidence": "controlled object and dimension transcription"},
            ]
            write_csv(terminal_audit, terminal_rows, list(terminal_rows[0]))
            validation = root / "validation.json"
            validation.write_text(json.dumps({"validation": "PASS", "failure_count": 0, "vision_capability": False, "source_image_runtime_access": "FORBIDDEN"}), encoding="utf-8")
            audit = root / "audit.md"
            audit.write_text("approved", encoding="utf-8")
            registry = root / "registry.csv"
            registry_row = {
                "source_id": source_id,
                "source_sha256": source_hash,
                "terminal_audit_csv": str(terminal_audit),
                "terminal_audit_sha256": hashlib.sha256(terminal_audit.read_bytes()).hexdigest().upper(),
                "validation_path": str(validation),
                "validation_sha256": hashlib.sha256(validation.read_bytes()).hexdigest().upper(),
                "promotion_audit_path": str(audit),
                "promotion_audit_sha256": hashlib.sha256(audit.read_bytes()).hexdigest().upper(),
                "structured_dataset_id": "promoted_figures",
                "qa_status": "VERIFIED",
                "promotion_state": "APPROVED",
            }
            write_csv(registry, [registry_row], list(registry_row))

            rows, summary = build_manifest(inventory, root / "documents", registry)

            self.assertEqual(rows[0]["audit_status"], "DIRECT_REUSE_VERIFIED")
            self.assertEqual(rows[0]["structured_dataset_id"], "promoted_figures")
            self.assertEqual(rows[1]["audit_status"], "NOT_APPLICABLE")
            self.assertEqual(rows[2]["audit_status"], "NEEDS_REVIEW")
            self.assertEqual(rows[2]["terminal_class"], "SEMANTIC_TRANSCRIPTION_PENDING")
            self.assertEqual(summary["unresolved_figure_count"], 1)
            self.assertEqual(summary["machine_representation_closed_count"], 1)


if __name__ == "__main__":
    unittest.main()
