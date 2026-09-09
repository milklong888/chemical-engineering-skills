from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

try:
    from build_compact_validation_packet import build_validation_packet
except ModuleNotFoundError:
    from scripts.build_compact_validation_packet import build_validation_packet


class CompactValidationPacketTests(unittest.TestCase):
    def test_keeps_decision_formula_and_failure_surfaces_without_candidate_bulk(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result_path = root / "equipment_derivation_result.json"
            gate_path = root / "OVERVIEW_GATE_V2.json"
            result = {
                "case_id": "case-x",
                "deterministic": True,
                "llm_used": False,
                "status": "DERIVED",
                "formal_use_gate": "PROVISIONAL_NOT_FORMAL_PROCESS_BASIS",
                "aspen_run_gate": {"status": "DIRTY_RUN", "counts": {"warnings": 1}},
                "equipment": [
                    {
                        "equipment_tag": "B1",
                        "aspen_block_id": "B1",
                        "aspen_mapping_status": "DERIVED",
                        "canonical_match_input": {"npsha_m": 24.08, "nested": {"omit": True}},
                        "match_result": {
                            "status": "MATCHED",
                            "calculations": [{
                                "calculation_id": "c1",
                                "target_field": "shaft_power_kw",
                                "equation_chain": "shaft_power_kw = rho*g*Q*H/eta = ... = 12 kW",
                                "value": 12,
                                "unit": "kW",
                                "status": "CALCULATED",
                            }],
                            "calculation_pending": [{"target_field": "npshr_m", "status": "VENDOR_REQUIRED"}],
                            "design_parameter_package": {
                                "status": "READY_FOR_CANDIDATE_MATCHING",
                                "groups": [{
                                    "group_id": "construction",
                                    "rows": [{
                                        "field_id": "tube_outer_diameter_mm",
                                        "label": "换热管外径",
                                        "raw_value": 25.0,
                                        "unit": "mm",
                                        "state": "DEFAULTED",
                                        "role": "input",
                                        "source": {
                                            "kind": "registered_final_fallback_default",
                                            "evidence_class": "J",
                                            "fallback_tier": "EXPLICIT_FINAL_FALLBACK_DEFAULT",
                                            "promotion_cap": "TYPE_SCREENING",
                                            "warning": "仅用于预设计初筛。",
                                        },
                                    }],
                                }],
                            },
                            "model_decision": {
                                "generated_candidate_designation": "GB/T 5662 65-40-200",
                                "model_status": "type_selected",
                                "verification_missing_fields": ["vendor_curve"],
                            },
                            "model_recommendation": {
                                "recommended_type": "轴向吸入离心泵",
                                "candidates": [{"very": "large detail must stay in full result"}],
                                "terminal_selection": {"status": "DEFAULTED_TERMINAL_TYPE_SELECTED"},
                            },
                        },
                    },
                    {
                        "equipment_tag": "B7",
                        "aspen_block_id": "B7",
                        "aspen_mapping_status": "NOT_APPLICABLE_SIMULATION_LOGIC_NODE",
                        "match_result": {"status": "NOT_APPLICABLE"},
                    },
                ],
            }
            gate = {
                "schema": "equipment-design-multi-bkp-authority-overview-gate-v2",
                "status": "FAIL",
                "failure_count": 1,
                "cases": [{
                    "failures": [{
                        "equipment": "B1",
                        "code": "AUTHORITY_OVERVIEW_VALUE_MISSING",
                        "fields": ["material"],
                    }]
                }],
            }
            result_path.write_text(json.dumps(result), encoding="utf-8")
            gate_path.write_text(json.dumps(gate), encoding="utf-8")

            authority_rows = [{
                "equipment_key": "B1",
                "equipment_tag": "B1",
                "authority_table_id": "T01",
                "authority_completeness": {
                    "required": 2,
                    "populated": 2,
                    "state": "COMPLETE",
                },
                "authority_missing_fields": [],
                "authority_cells": [
                    {
                        "field_id": "material",
                        "label": "材料",
                        "value": "S30408",
                        "unit": None,
                        "state": "DEFAULTED",
                        "source_field_id": "material",
                        "source": {
                            "kind": "registered_preliminary_fallback",
                            "evidence_class": "J",
                            "fallback_tier": "FINAL_FALLBACK_DEFAULT",
                            "promotion_cap": "TYPE_SCREENING",
                            "warning": "未给材料，采用可见的预选默认值。",
                            "large_internal_detail": {"omit": True},
                        },
                        "equation_chain": None,
                    },
                    {
                        "field_id": "shaft_power_kw",
                        "label": "轴功率",
                        "value": 12,
                        "unit": "kW",
                        "state": "CALCULATED",
                        "source_field_id": "shaft_power_kw",
                        "source": {
                            "kind": "deterministic_calculation",
                            "evidence_class": "D",
                            "calculation_id": "c1",
                        },
                        "equation_chain": "shaft_power_kw = rho*g*Q*H/eta = ... = 12 kW",
                    },
                ],
            }]

            packet = build_validation_packet(
                result,
                gate,
                result_path,
                gate_path,
                authority_rows=authority_rows,
            )

            self.assertEqual(packet["case_summary"]["physical_equipment_count"], 1)
            self.assertEqual(packet["case_summary"]["logic_node_count"], 1)
            self.assertEqual(
                packet["packet_policy"]["validation_surface_index"]["preliminary_completion_inputs"],
                "/equipment_summaries/*/preliminary_completion_inputs",
            )
            self.assertEqual(
                packet["packet_policy"]["validation_surface_index"]["authority_overview_cells"],
                "/equipment_summaries/*/authority_cells",
            )
            b1 = packet["equipment_summaries"][0]
            self.assertEqual(b1["canonical_inputs"]["npsha_m"], 24.08)
            self.assertEqual(b1["selection"]["candidate_designation"], "GB/T 5662 65-40-200")
            self.assertIn("shaft_power_kw =", b1["formula_chains"][0]["equation_chain"])
            self.assertNotIn("candidates", b1["selection"])
            self.assertEqual(b1["authority_table_id"], "T01")
            self.assertEqual(b1["authority_completeness"]["state"], "COMPLETE")
            material = next(
                cell for cell in b1["authority_cells"] if cell["field_id"] == "material"
            )
            self.assertEqual(material["value"], "S30408")
            self.assertEqual(material["state"], "DEFAULTED")
            self.assertEqual(material["source"]["evidence_class"], "J")
            self.assertEqual(material["source"]["promotion_cap"], "TYPE_SCREENING")
            self.assertIn("预选默认值", material["source"]["warning"])
            self.assertNotIn("large_internal_detail", material["source"])
            fallback_input = b1["preliminary_completion_inputs"][0]
            self.assertEqual(fallback_input["field_id"], "tube_outer_diameter_mm")
            self.assertEqual(fallback_input["value"], 25.0)
            self.assertEqual(fallback_input["state"], "DEFAULTED")
            self.assertEqual(fallback_input["source"]["evidence_class"], "J")
            self.assertEqual(fallback_input["source"]["promotion_cap"], "TYPE_SCREENING")
            self.assertEqual(packet["overview_gate"]["failures"][0]["fields"], ["material"])
            self.assertEqual(
                packet["artifacts"]["full_result"]["sha256"],
                hashlib.sha256(result_path.read_bytes()).hexdigest().upper(),
            )


if __name__ == "__main__":
    unittest.main()
