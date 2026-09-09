from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PACKAGE_ROOT / "scripts" / "audit_multi_bkp_overview_gate.py"
SPEC = importlib.util.spec_from_file_location(
    "audit_multi_bkp_overview_gate_under_test",
    SCRIPT_PATH,
)
assert SPEC is not None and SPEC.loader is not None
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


class MultiBkpOverviewGateTest(unittest.TestCase):
    def test_physical_pipe_block_is_piping_and_aliases_are_excluded(self) -> None:
        document = {
            "equipment": [
                {
                    "match_result": {
                        "status": "MATCHED",
                        "input_sha256": "E" * 64,
                    },
                },
                {
                    "pipe_entity_scope": "ASPEN_PHYSICAL_PIPE_BLOCK",
                    "counted_as_physical_pipe": True,
                    "match_result": {
                        "status": "MATCHED",
                        "input_sha256": "P" * 64,
                    },
                },
                {
                    "aspen_mapping_status": (
                        "NOT_APPLICABLE_SIMULATION_LOGIC_NODE"
                    ),
                    "match_result": {"status": "NOT_APPLICABLE"},
                },
            ],
            "piping": [
                {
                    "match_result": {
                        "status": "MATCHED",
                        "input_sha256": "S" * 64,
                    },
                },
                {
                    "alias_only": True,
                    "match_result": {
                        "status": "MATCHED",
                        "input_sha256": "A" * 64,
                    },
                },
            ],
            "piping_state_aliases": [{"alias_only": True}],
        }
        profile = audit.physical_source_profile(document)
        self.assertEqual(profile["equipment_count"], 1)
        self.assertEqual(profile["piping_count"], 2)
        self.assertEqual(profile["logic_count"], 1)
        self.assertEqual(profile["alias_count"], 2)
        self.assertEqual(
            profile["expected_bindings"],
            [
                ("equipment", "E" * 64),
                ("piping", "P" * 64),
                ("piping", "S" * 64),
            ],
        )

    def test_delivery_cell_hash_covers_visible_open_metadata(self) -> None:
        row = {
            "source_input_sha256": "A" * 64,
            "record_kind": "equipment",
        }
        cell = {
            "delivery_scope": "all_equipment_fields",
            "delivery_field_index": 3,
            "field_id": "diameter_mm",
            "value": None,
            "display_value": "OPEN / 待补：直径",
            "unit": "mm",
            "state": audit.EXPLICIT_OPEN_GATE_STATE,
            "promotion_cap": "NOT_PROMOTABLE",
            "open_gate": {
                "reason": "not available",
                "required_action": "provide diameter",
                "promotion_cap": "NOT_PROMOTABLE",
            },
            "source_field_id": None,
            "source": {
                "kind": "registered_formal_evidence_gate",
                "evidence_class": "U",
            },
            "requirement": "required",
            "evidence_gate": "project_input",
            "source_refs": ["SRC"],
            "profile_ids": ["T11"],
            "source_chain_binding_sha256": "B" * 64,
            "derivation_record_kind": "equipment",
            "derivation_record_identity": "B1",
            "program_generated_record_sha256": "C" * 64,
            "program_generated_record_binding_sha256": "C" * 64,
        }
        cell["cell_sha256"] = audit.canonical_sha256({
            "input_sha256": row["source_input_sha256"],
            "record_kind": row["record_kind"],
            "delivery_scope": cell["delivery_scope"],
            "delivery_field_index": cell["delivery_field_index"],
            "field_id": cell["field_id"],
            "value": cell["value"],
            "display_value": cell["display_value"],
            "unit": cell["unit"],
            "state": cell["state"],
            "promotion_cap": cell["promotion_cap"],
            "open_gate": cell["open_gate"],
            "source_field_id": cell["source_field_id"],
            "source": cell["source"],
            "requirement": cell["requirement"],
            "evidence_gate": cell["evidence_gate"],
            "source_refs": cell["source_refs"],
            "profile_ids": cell["profile_ids"],
            "source_chain_binding_sha256": cell[
                "source_chain_binding_sha256"
            ],
            "derivation_record_kind": cell[
                "derivation_record_kind"
            ],
            "derivation_record_identity": cell[
                "derivation_record_identity"
            ],
            "program_generated_record_sha256": cell[
                "program_generated_record_sha256"
            ],
            "program_generated_record_binding_sha256": cell[
                "program_generated_record_binding_sha256"
            ],
        })
        self.assertTrue(audit.delivery_cell_hash_check(row, cell))
        cell["display_value"] = "tampered"
        self.assertFalse(audit.delivery_cell_hash_check(row, cell))

    def test_row_hash_binds_full_field_coverage_state(self) -> None:
        row = {
            "source_input_sha256": "B" * 64,
            "record_kind": "equipment",
            "source_chain_binding": {"case_id": "CASE"},
            "authority_table_id": "T11",
            "authority_source": {"schema": "authority"},
            "authority_cells": [{"cell_sha256": "C" * 64}],
            "all_equipment_fields_sha256": "D" * 64,
            "authority_information_coverage": {
                "state": audit.PROVISIONAL_INFORMATION_STATE,
            },
            "customer_information_coverage": {
                "state": audit.PROVISIONAL_INFORMATION_STATE,
            },
            "authority_full_field_coverage": {"state": "PASS"},
            "selection_specificity_gate": {"state": "PASS"},
            "formal_readiness_gate": {
                "blocking_fields": ["diameter_mm"],
                "blocking_reasons": ["FORMAL_MODEL_NOT_ESTABLISHED"],
            },
        }
        row["authority_row_sha256"] = audit.canonical_sha256({
            "input_sha256": row["source_input_sha256"],
            "record_kind": row["record_kind"],
            "aspen_source_binding": row["source_chain_binding"],
            "authority_table_id": row["authority_table_id"],
            "authority_source": row["authority_source"],
            "authority_cell_hashes": ["C" * 64],
            "all_equipment_fields_sha256": "D" * 64,
            "information_coverage_state": (
                audit.PROVISIONAL_INFORMATION_STATE
            ),
            "customer_information_state": (
                audit.PROVISIONAL_INFORMATION_STATE
            ),
            "authority_full_field_coverage_state": "PASS",
            "specificity_state": "PASS",
            "formal_gate_blockers": [
                "FORMAL_MODEL_NOT_ESTABLISHED",
                "diameter_mm",
            ],
        })
        self.assertTrue(audit.row_hash_check(row))
        row["authority_full_field_coverage"]["state"] = "BLOCKED"
        self.assertFalse(audit.row_hash_check(row))

    def test_customer_full_field_coverage_is_structural_not_information(self) -> None:
        row = {
            "all_equipment_fields": [
                {"field_id": "equipment_type"},
                {"field_id": "diameter_mm"},
            ],
            "customer_full_field_coverage": {
                "state": "PASS",
                "required": 2,
                "emitted": 2,
                "represented": 2,
                "value_fields": ["equipment_type"],
                "explicit_open_fields": ["diameter_mm"],
                "not_applicable_fields": [],
                "missing_cell_ids": [],
                "unrepresented_field_ids": [],
                "blocking_reasons": [],
            },
        }
        expected_fields = {"equipment_type", "diameter_mm"}
        self.assertEqual(
            audit._full_field_coverage_errors(row, expected_fields),
            [],
        )
        self.assertIn(
            "CUSTOMER_PROFILE_CONTRACT_FIELD_SET_MISMATCH",
            audit._full_field_coverage_errors(
                row,
                expected_fields | {"height_mm"},
            ),
        )
        row["customer_full_field_coverage"]["represented"] = 1
        self.assertIn(
            "CUSTOMER_PROFILE_FIELD_COUNT_MISMATCH",
            audit._full_field_coverage_errors(row),
        )

    def test_true_unknown_requires_complete_u_class_open_contract(self) -> None:
        cell = {
            "field_id": "diameter_mm",
            "value": None,
            "display_value": "OPEN / 待补：直径",
            "state": audit.EXPLICIT_OPEN_GATE_STATE,
            "promotion_cap": "NOT_PROMOTABLE",
            "open_gate": {
                "reason": "not available",
                "required_action": "provide diameter",
                "promotion_cap": "NOT_PROMOTABLE",
            },
            "source": {
                "evidence_class": "U",
                "reason": "not available",
                "required_action": "provide diameter",
                "promotion_cap": "NOT_PROMOTABLE",
                "formal_design_evidence": False,
                "placeholder_is_engineering_value": False,
                "original_state": "MISSING",
            },
        }
        self.assertEqual(audit._open_gate_metadata_errors(cell), [])
        cell["source"]["evidence_class"] = "J"
        self.assertIn(
            "OPEN_EVIDENCE_CLASS_NOT_U",
            audit._open_gate_metadata_errors(cell),
        )
        cell["source"]["evidence_class"] = "U"
        cell["value"] = "placeholder"
        self.assertIn(
            "OPEN_MACHINE_VALUE_NOT_NULL",
            audit._open_gate_metadata_errors(cell),
        )
        self.assertIn(
            "NORMALISED_RAW_GAP_OPEN_VALUE_NOT_NULL",
            audit._open_gate_metadata_errors(cell),
        )

    def test_named_screening_value_can_block_formal_not_identity(self) -> None:
        cell = {
            "field_id": "pressure_temperature_rating",
            "value": "PN16 preliminary; formal rating open",
            "state": "DEFAULTED_PRELIMINARY_RATING",
            "promotion_cap": "TYPE_SCREENING",
            "open_gate": {
                "reason": "product rating table not verified",
                "required_action": "verify product pressure-temperature table",
                "promotion_cap": "TYPE_SCREENING",
            },
            "source": {
                "evidence_class": "J",
                "kind": "registered_preliminary_rating",
            },
        }
        self.assertTrue(audit._selection_screening_gate_valid(cell))
        cell["open_gate"].pop("required_action")
        self.assertFalse(audit._selection_screening_gate_valid(cell))

    def test_generic_type_is_rejected_independently_of_gate_claim(self) -> None:
        row = {
            "equipment_type": "非标准型泵",
            "model_or_specification": "非标准型泵",
            "selection_specificity_gate": {
                "state": "PASS",
                "blocking_fields": [],
                "blocking_reasons": [],
                "selection_identity": {
                    "recommended_type": "非标准型泵",
                    "model_or_specification": "非标准型泵",
                    "concrete_terminal_type": True,
                    "detailed_designation": True,
                    "candidate_validation_blockers": [],
                    "designation_detail_blockers": [],
                },
            },
        }
        reasons = audit._generic_selection_reasons(row)
        self.assertTrue(
            any(reason.startswith("GENERIC_SELECTION_TOKEN") for reason in reasons)
        )

    def test_open_gap_must_not_be_reported_as_information_or_formal_pass(
        self,
    ) -> None:
        false_pass_row = {
            "customer_information_coverage": {"state": "PASS"},
            "authority_information_coverage": {"state": "PASS"},
            "formal_readiness_gate": {"state": "PASS"},
        }
        errors = audit._false_pass_errors(false_pass_row, ["diameter_mm"])
        self.assertIn(
            "FALSE_CUSTOMER_INFORMATION_PASS_WITH_OPEN_GAPS",
            errors,
        )
        self.assertIn(
            "FALSE_AUTHORITY_INFORMATION_PASS_WITH_OPEN_GAPS",
            errors,
        )
        self.assertIn(
            "FALSE_FORMAL_READINESS_PASS_WITH_OPEN_GAPS",
            errors,
        )

        honest_row = {
            "customer_information_coverage": {
                "state": audit.PROVISIONAL_INFORMATION_STATE,
            },
            "authority_information_coverage": {
                "state": audit.PROVISIONAL_INFORMATION_STATE,
            },
            "formal_readiness_gate": {"state": "BLOCKED"},
        }
        self.assertEqual(
            audit._false_pass_errors(honest_row, ["diameter_mm"]),
            [],
        )


if __name__ == "__main__":
    unittest.main()
