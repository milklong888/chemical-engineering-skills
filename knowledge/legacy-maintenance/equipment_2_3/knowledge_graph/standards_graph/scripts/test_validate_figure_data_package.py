from __future__ import annotations

import csv
import hashlib
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from validate_figure_data_package import validate_package


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def png_bytes() -> bytes:
    signature = b"\x89PNG\r\n\x1a\n"
    data = struct.pack(">IIBBBBB", 2, 3, 8, 2, 0, 0, 0)
    body = b"IHDR" + data
    ihdr = struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
    iend_body = b"IEND"
    iend = struct.pack(">I", 0) + iend_body + struct.pack(">I", zlib.crc32(iend_body) & 0xFFFFFFFF)
    return signature + ihdr + iend


class FigurePackageValidationTest(unittest.TestCase):
    def test_text_only_curve_package_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image_dir = root / "figures"
            image_dir.mkdir()
            image = image_dir / "f1.png"
            image.write_bytes(png_bytes())
            source = root / "figures.csv"
            write_csv(source, [{"figure_id": "f1", "image_path": "figures/f1.png"}], ["figure_id", "image_path"])
            audit = root / "audit.csv"
            write_csv(
                audit,
                [{"figure_id": "f1", "terminal_class": "QUANTITATIVE_CURVE_DATAIZED", "needs_review": "False", "structured_record_count": "2", "image_sha256": hashlib.sha256(image.read_bytes()).hexdigest().upper()}],
                ["figure_id", "terminal_class", "needs_review", "structured_record_count", "image_sha256"],
            )
            records = root / "records.csv"
            fields = ["figure_record_id", "figure_id", "record_kind", "payload_json", "error_bound"]
            write_csv(
                records,
                [
                    {"figure_record_id": "axis", "figure_id": "f1", "record_kind": "axis_x", "payload_json": '{"unit":"mm"}', "error_bound": "±0.1"},
                    {"figure_record_id": "point", "figure_id": "f1", "record_kind": "point", "payload_json": '{"x":1,"y":2}', "error_bound": "±0.1"},
                ],
                fields,
            )
            report = validate_package(source, audit, records, root)
            self.assertEqual(report["validation"], "PASS")
            self.assertFalse(report["vision_capability"])

    def test_image_only_claim_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = root / "f1.png"
            image.write_bytes(png_bytes())
            source = root / "figures.csv"
            write_csv(source, [{"figure_id": "f1", "image_path": "f1.png"}], ["figure_id", "image_path"])
            audit = root / "audit.csv"
            write_csv(
                audit,
                [{"figure_id": "f1", "terminal_class": "DIMENSION_STRUCTURE_DATAIZED", "needs_review": "False", "structured_record_count": "0", "image_sha256": hashlib.sha256(image.read_bytes()).hexdigest().upper()}],
                ["figure_id", "terminal_class", "needs_review", "structured_record_count", "image_sha256"],
            )
            records = root / "records.csv"
            write_csv(records, [], ["figure_record_id", "figure_id", "record_kind", "payload_json", "error_bound"])
            report = validate_package(source, audit, records, root)
            self.assertEqual(report["validation"], "FAIL")
            self.assertTrue(any("machine record missing" in item for item in report["failures"]))


if __name__ == "__main__":
    unittest.main()
