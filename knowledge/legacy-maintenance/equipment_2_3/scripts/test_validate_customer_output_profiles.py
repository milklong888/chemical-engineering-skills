from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().with_name("validate_customer_output_profiles.py")
PROFILE_PATH = SCRIPT_PATH.parents[1] / "knowledge_graph" / "equipment_customer_output_profiles.json"
SPEC = importlib.util.spec_from_file_location("validate_customer_output_profiles_under_test", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


class CustomerOutputAuthorityCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))

    def test_frozen_xlsx_docx_ooxml_and_all_header_mappings_pass(self) -> None:
        report = validator.validate_document(copy.deepcopy(self.data), PROFILE_PATH)
        self.assertEqual(report["status"], "PASS", report["errors"])
        self.assertEqual(report["counts"]["authority_header_labels"], 331)
        self.assertEqual(report["counts"]["authority_header_mappings"], 331)
        self.assertTrue(report["checks"]["authority_ooxml_headers_exact"])
        self.assertTrue(report["checks"]["authority_header_mappings_complete"])

    def test_deleting_any_single_header_mapping_fails_profile_local_gate(self) -> None:
        global_fields = {
            field["canonical_id"]: field for field in self.data["global_output_columns"]
        }
        profiles = {
            profile["authority_section_id"]: {
                field["canonical_id"]: field for field in profile["required_fields"]
            }
            for profile in self.data["profiles"]
        }
        checked = 0
        for profile_number in range(1, 15):
            profile_id = f"T{profile_number:02d}"
            source_id = f"SRC_{profile_id}"
            source_set = self.data["authority_source_sets"][source_id]
            available_fields = {**global_fields, **profiles[profile_id]}
            for channel_name in ("excel", "word"):
                channel = source_set[channel_name]
                for mapping_index in range(len(channel["header_mappings"])):
                    with self.subTest(
                        source_id=source_id,
                        channel=channel_name,
                        mapping_index=mapping_index,
                    ):
                        mappings = copy.deepcopy(channel["header_mappings"])
                        mappings.pop(mapping_index)
                        errors: list[str] = []
                        result = validator.validate_header_channel_mapping(
                            source_id=source_id,
                            channel_name=channel_name,
                            declared_headers=channel["header_labels"],
                            actual_headers=channel["header_labels"],
                            mappings=mappings,
                            available_fields=available_fields,
                            errors=errors,
                        )
                        self.assertFalse(result["complete_mapping"])
                        self.assertTrue(
                            any("exactly one" in error or "cover every" in error for error in errors),
                            errors,
                        )
                    checked += 1
        self.assertEqual(checked, 331)

    def test_end_to_end_deleted_mapping_is_fail_not_false_positive(self) -> None:
        mutated = copy.deepcopy(self.data)
        mutated["authority_source_sets"]["SRC_T14"]["excel"]["header_mappings"].pop()
        report = validator.validate_document(mutated, PROFILE_PATH)
        self.assertEqual(report["status"], "FAIL")
        self.assertFalse(report["checks"]["authority_header_mappings_complete"])
        self.assertTrue(any("SRC_T14.excel" in error for error in report["errors"]))

    def test_t10_slash_semantics_are_explicit_and_narrow(self) -> None:
        source = self.data["authority_source_sets"]["SRC_T10"]["excel"]
        rules = {rule["canonical_id"]: rule for rule in source["source_value_state_rules"]}
        self.assertEqual(set(rules), {"loading_coefficient", "rotational_speed_rpm"})
        self.assertTrue(all(rule["source_token"] == "/" for rule in rules.values()))
        self.assertTrue(all(rule["state"] == "NOT_APPLICABLE" for rule in rules.values()))


if __name__ == "__main__":
    unittest.main()
