from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from build_executable_standard_database import (
    build_database,
    source_record_id,
    standard_candidate_applicability,
    standard_candidate_physical_page,
    standard_candidate_value,
    valid_physical_page_locator,
)
from query_executable_standard_data import ExecutableStandardStore


class ExecutableStandardDatabaseTest(unittest.TestCase):
    def test_table_record_id_is_preserved_as_explicit_record_id(self) -> None:
        self.assertEqual(
            source_record_id(
                {
                    "table_record_id": "TABLE-ROW-001",
                    "table_id": "std:p0001:t01",
                    "row_key": "DN50",
                    "column_key": "OD",
                }
            ),
            "TABLE-ROW-001",
        )

    def test_audited_table_candidate_aliases_map_to_runtime_fields(self) -> None:
        source = {
            "table_category": "wall_thickness_tolerance",
            "normalized_number": "0.25",
            "row_condition": "wall_mm=3~4",
            "column_condition": "grade=high",
            "material": "copper",
        }
        self.assertEqual(standard_candidate_value(source), "0.25")
        self.assertEqual(
            standard_candidate_applicability(source),
            "row_condition=wall_mm=3~4; column_condition=grade=high; material=copper",
        )

    def test_physical_page_alias_and_closed_page_chain_are_preserved(self) -> None:
        self.assertEqual(
            standard_candidate_physical_page({"page_1based": "23"}),
            "23",
        )
        self.assertTrue(valid_physical_page_locator("117-118"))
        self.assertTrue(valid_physical_page_locator("37|38|39|40"))
        self.assertFalse(valid_physical_page_locator("p23"))
        self.assertFalse(valid_physical_page_locator("0"))

    def test_build_hash_lock_and_query_after_inputs_removed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "candidate.csv"
            with source.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "record_id", "record_type", "physical_page", "source_section",
                        "source_table", "source_row_label", "source_column_label", "raw_value",
                        "normalized_value", "unit", "applicability",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "record_id": "dn_001", "record_type": "preferred_dn_series_value",
                        "physical_page": "3", "source_section": "3.1", "raw_value": "DN 6",
                        "normalized_value": "6", "unit": "dimensionless_designation",
                        "applicability": "test",
                    }
                )
            audit = root / "audit.md"
            audit.write_text("verified\n", encoding="utf-8")
            source_hash = hashlib.sha256(source.read_bytes()).hexdigest().upper()
            registry = root / "registry.csv"
            fields = [
                "dataset_id", "equipment_family", "subject", "standard_id", "standard_version",
                "source_id", "source_sha256", "authority_state", "lifecycle_state", "source_csv",
                "source_csv_sha256", "record_filter_field", "record_filter_values", "reuse_class",
                "qa_status", "unresolved_key_cells", "audit_path", "promotion_state", "approved_utc", "notes",
            ]
            with registry.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow(
                    {
                        "dataset_id": "test_dn", "equipment_family": "piping", "subject": "dn",
                        "standard_id": "GB/T TEST", "standard_version": "1", "source_id": "test",
                        "source_sha256": "A" * 64, "authority_state": "CURRENT", "lifecycle_state": "CURRENT",
                        "source_csv": str(source), "source_csv_sha256": source_hash,
                        "record_filter_field": "record_type", "record_filter_values": "preferred_dn_series_value",
                        "reuse_class": "DIRECT_REUSE_VERIFIED", "qa_status": "VERIFIED",
                        "unresolved_key_cells": "0", "audit_path": str(audit), "promotion_state": "APPROVED",
                    }
                )
            out = root / "out"
            manifest = build_database(registry, out, "test-build")
            self.assertEqual(manifest["record_count"], 1)
            source.unlink()
            audit.unlink()
            store = ExecutableStandardStore(out / "executable_standard_data.sqlite")
            try:
                rows = store.query("piping", "test_dn", "preferred_dn_series_value")
                cached_rows = store.query("piping", "test_dn", "preferred_dn_series_value")
            finally:
                store.close()
            self.assertEqual(len(rows), 1)
            self.assertIs(rows, cached_rows)
            self.assertEqual(rows[0]["normalized_number"], 6.0)

    def test_semicolon_attributes_expose_numeric_value_and_flags(self) -> None:
        from build_executable_standard_database import normalize_payload

        number, payload = normalize_payload("value=400;recommended=false;footnote=a")
        self.assertEqual(number, 400.0)
        self.assertEqual(
            payload,
            '{"footnote": "a", "recommended": false, "value": "400"}',
        )

    def test_structured_figure_records_survive_without_images_or_candidate_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            candidate = root / "figure_candidate.csv"
            fields = [
                "figure_record_id", "figure_id", "record_kind", "entity_id",
                "parent_entity_id", "physical_page", "source_figure", "raw_label",
                "normalized_value", "unit", "payload_json", "applicability", "error_bound",
                "relation_from_entity_id", "relation_to_entity_id", "direction", "condition_text",
            ]
            with candidate.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow(
                    {
                        "figure_record_id": "fig1-edge1",
                        "figure_id": "std:p0003:f01",
                        "record_kind": "edge",
                        "entity_id": "edge1",
                        "physical_page": "3",
                        "source_figure": "图 1",
                        "raw_label": "入口至塔体",
                        "payload_json": json.dumps({"ports": ["feed", "nozzle_n1"]}, ensure_ascii=False),
                        "applicability": "test",
                        "relation_from_entity_id": "feed",
                        "relation_to_entity_id": "tower",
                        "direction": "forward",
                    }
                )
            audit = root / "figure_audit.md"
            audit.write_text("verified\n", encoding="utf-8")
            registry = root / "figure_registry.csv"
            registry_fields = [
                "dataset_id", "equipment_family", "subject", "representation_type",
                "standard_id", "standard_version", "source_id", "source_sha256",
                "authority_state", "lifecycle_state", "source_csv", "source_csv_sha256",
                "record_filter_field", "record_filter_values", "reuse_class", "qa_status",
                "unresolved_entities", "vision_disabled_replay_status", "audit_path",
                "promotion_state",
            ]
            with registry.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=registry_fields)
                writer.writeheader()
                writer.writerow(
                    {
                        "dataset_id": "test_figure",
                        "equipment_family": "tower",
                        "subject": "feed_connection",
                        "representation_type": "process_logic",
                        "standard_id": "GB/T TEST",
                        "standard_version": "1",
                        "source_id": "std_test",
                        "source_sha256": "B" * 64,
                        "authority_state": "CURRENT",
                        "lifecycle_state": "CURRENT",
                        "source_csv": str(candidate),
                        "source_csv_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest().upper(),
                        "reuse_class": "DIRECT_REUSE_VERIFIED",
                        "qa_status": "VERIFIED",
                        "unresolved_entities": "0",
                        "vision_disabled_replay_status": "PASS",
                        "audit_path": str(audit),
                        "promotion_state": "APPROVED",
                    }
                )

            standard_candidate = root / "standard_candidate.csv"
            with standard_candidate.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "record_id", "record_type", "physical_page", "source_section",
                        "source_table", "source_row_label", "source_column_label", "raw_value",
                        "normalized_value", "unit", "applicability",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "record_id": "one",
                        "record_type": "rule",
                        "physical_page": "3",
                        "raw_value": "1",
                        "normalized_value": "1",
                    }
                )
            standard_audit = root / "standard_audit.md"
            standard_audit.write_text("verified\n", encoding="utf-8")
            standard_registry = root / "standard_registry.csv"
            standard_fields = [
                "dataset_id", "equipment_family", "subject", "standard_id", "standard_version",
                "source_id", "source_sha256", "authority_state", "lifecycle_state", "source_csv",
                "source_csv_sha256", "record_filter_field", "record_filter_values", "reuse_class",
                "qa_status", "unresolved_key_cells", "audit_path", "promotion_state",
            ]
            with standard_registry.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=standard_fields)
                writer.writeheader()
                writer.writerow(
                    {
                        "dataset_id": "one", "equipment_family": "tower", "subject": "rule",
                        "standard_id": "GB/T TEST", "standard_version": "1", "source_id": "std_test",
                        "source_sha256": "B" * 64, "authority_state": "CURRENT", "lifecycle_state": "CURRENT",
                        "source_csv": str(standard_candidate),
                        "source_csv_sha256": hashlib.sha256(standard_candidate.read_bytes()).hexdigest().upper(),
                        "record_filter_field": "record_type", "record_filter_values": "rule",
                        "reuse_class": "DIRECT_REUSE_VERIFIED", "qa_status": "VERIFIED",
                        "unresolved_key_cells": "0", "audit_path": str(standard_audit),
                        "promotion_state": "APPROVED",
                    }
                )
            out = root / "out"
            manifest = build_database(
                standard_registry, out, "figure-test", figure_registry_path=registry
            )
            self.assertEqual(manifest["figure_record_count"], 1)
            candidate.unlink()
            audit.unlink()
            store = ExecutableStandardStore(out / "executable_standard_data.sqlite")
            try:
                rows = store.query_figures("tower", figure_id="std:p0003:f01")
                cached = store.query_figures("tower", figure_id="std:p0003:f01")
            finally:
                store.close()
            self.assertIs(rows, cached)
            self.assertEqual(rows[0]["relation_from_entity_id"], "feed")
            self.assertEqual(json.loads(rows[0]["payload_json"])["ports"][1], "nozzle_n1")

    def test_direct_reuse_rejects_missing_printed_raw_value(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "candidate.csv"
            with source.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["record_id", "record_type", "raw_value", "normalized_value"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "record_id": "cell-1",
                        "record_type": "table_cell",
                        "raw_value": "",
                        "normalized_value": "350",
                    }
                )
            audit = root / "audit.md"
            audit.write_text("verified\n", encoding="utf-8")
            registry = root / "registry.csv"
            fields = [
                "dataset_id", "equipment_family", "subject", "standard_id", "standard_version",
                "source_id", "source_sha256", "authority_state", "lifecycle_state", "source_csv",
                "source_csv_sha256", "record_filter_field", "record_filter_values", "reuse_class",
                "qa_status", "unresolved_key_cells", "audit_path", "promotion_state",
            ]
            with registry.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow(
                    {
                        "dataset_id": "missing_raw",
                        "equipment_family": "vessel_or_storage",
                        "subject": "material_limit",
                        "standard_id": "GB/T TEST",
                        "standard_version": "1",
                        "source_id": "std_test",
                        "source_sha256": "C" * 64,
                        "authority_state": "CURRENT",
                        "lifecycle_state": "CURRENT",
                        "source_csv": str(source),
                        "source_csv_sha256": hashlib.sha256(source.read_bytes()).hexdigest().upper(),
                        "record_filter_field": "record_type",
                        "record_filter_values": "table_cell",
                        "reuse_class": "DIRECT_REUSE_VERIFIED",
                        "qa_status": "VERIFIED",
                        "unresolved_key_cells": "0",
                        "audit_path": str(audit),
                        "promotion_state": "APPROVED",
                    }
                )
            with self.assertRaisesRegex(ValueError, "direct record has no raw_value"):
                build_database(registry, root / "out", "missing-raw-test")


if __name__ == "__main__":
    unittest.main()
