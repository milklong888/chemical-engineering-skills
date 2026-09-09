from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import principles_requirements as req


def sample_graph() -> dict:
    return {
        "schema": "principles-equipment-requirement-graph-v1",
        "equipment_family": "family_test_pump",
        "source": {
            "source_id": "chemical_engineering_principles_upper",
            "title": "化工原理 上册",
            "chapter": "第2章 流体流动与输送设备",
            "source_class": "PRINCIPLES_METHOD",
            "source_file_name": "化工原理 上.pdf",
            "source_sha256": "B" * 64,
            "source_role": "METHOD_SOURCE_NOT_PROJECT_VALUE_AUTHORITY",
        },
        "nodes": [
            {
                "id": "duty_input",
                "type": "input",
                "name": "泵工况",
                "description": "流量和扬程是候选泵工况点的基础输入。",
                "field_ids": ["flow_m3_h", "head_m"],
                "required_for": ["screening", "concrete_candidate"],
                "source_anchors": [
                    {"section": "2.8.1 离心泵", "printed_page": 65, "pdf_page": 76}
                ],
                "forbidden_promotions": ["final_vendor_model"],
            },
            {
                "id": "vendor_curve_gate",
                "type": "gate",
                "name": "同工况厂家曲线",
                "description": "正式放行需要同转速、同介质工况曲线。",
                "field_ids": ["vendor_curve_evidence"],
                "required_for": ["formal_release"],
                "source_anchors": [
                    {"section": "2.8.1 离心泵", "printed_page": 80, "pdf_page": 91}
                ],
            },
        ],
        "edges": [
            {
                "from": "duty_input",
                "to": "vendor_curve_gate",
                "relation": "must_precede",
            }
        ],
        "claim_boundary": {
            "project_values_from_book_forbidden": True,
            "standard_status_requires_authority_check": True,
            "formal_release_requires_same_case_evidence": True,
        },
    }


class PrinciplesRequirementGraphTests(unittest.TestCase):
    def test_validate_and_load_hash_bound_graph(self) -> None:
        graph = sample_graph()
        req.validate_requirement_graph(graph)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pump_requirement_graph.json"
            path.write_text(json.dumps(graph, ensure_ascii=False), encoding="utf-8")
            loaded = req.load_requirement_graph(path)
        self.assertEqual(loaded["equipment_family"], "family_test_pump")
        self.assertRegex(loaded["graph_sha256"], r"^[0-9A-F]{64}$")

    def test_invalid_edge_and_claim_boundary_are_rejected(self) -> None:
        graph = sample_graph()
        graph["edges"][0]["to"] = "missing_node"
        with self.assertRaises(req.RequirementGraphError):
            req.validate_requirement_graph(graph)
        graph = sample_graph()
        graph["claim_boundary"]["project_values_from_book_forbidden"] = False
        with self.assertRaises(req.RequirementGraphError):
            req.validate_requirement_graph(graph)

    def test_coverage_does_not_promote_without_formal_evidence(self) -> None:
        graph = sample_graph()
        graph["graph_sha256"] = "A" * 64
        index = req.requirement_field_index([graph])
        coverage = req.assess_requirement_coverage(
            "family_test_pump",
            {"flow_m3_h": 10.0, "head_m": 30.0},
            index,
        )
        self.assertEqual(coverage["highest_ready_level"], "concrete_candidate")
        self.assertEqual(
            coverage["missing_by_level"]["formal_release"],
            ["vendor_curve_evidence"],
        )
        self.assertIn("does not prove", coverage["claim_boundary"])

    def test_uncovered_family_is_explicit(self) -> None:
        coverage = req.assess_requirement_coverage(
            "family_unknown",
            {},
            {"families": {}},
        )
        self.assertEqual(coverage["status"], "NOT_COVERED")
        self.assertFalse(coverage["covered_by_method_graph"])


if __name__ == "__main__":
    unittest.main()
