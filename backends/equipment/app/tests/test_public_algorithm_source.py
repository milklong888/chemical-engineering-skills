from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = APP_DIR.parent
SCRIPTS_DIR = PACKAGE_ROOT / "scripts"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import equipment_design_match as matcher


PUBLIC_ALGORITHM_ASSETS = (
    "knowledge_graph/equipment_match_rules.json",
    "knowledge_graph/equipment_model_recommendation_rules.json",
    "knowledge_graph/equipment_parameter_chain_templates.json",
    "knowledge_graph/equipment_customer_output_profiles.json",
    "knowledge_graph/equipment_match_input.schema.json",
    "knowledge_graph/equipment_design_parameter_package.schema.json",
    "knowledge_graph/equipment_connection_selection_package.schema.json",
    "knowledge_graph/equipment_service_profile.schema.json",
    "knowledge_graph/equipment_type_applicability_graph.schema.json",
    "knowledge_graph/equipment_type_applicability_label_catalog.json",
    "equipment_selection_graph/equipment_selection_graph_v2.json",
)


class PublicAlgorithmSourceTests(unittest.TestCase):
    def test_public_source_contains_executable_rules_and_model_graph(self) -> None:
        for relative_path in PUBLIC_ALGORITHM_ASSETS:
            with self.subTest(relative_path=relative_path):
                path = PACKAGE_ROOT / relative_path
                self.assertTrue(path.is_file(), relative_path)
                value = json.loads(path.read_text(encoding="utf-8"))
                self.assertIsInstance(value, dict)

        rules = matcher.load_rules(
            PACKAGE_ROOT / "knowledge_graph" / "equipment_match_rules.json"
        )
        model_rules = matcher.load_model_rules(
            PACKAGE_ROOT
            / "knowledge_graph"
            / "equipment_model_recommendation_rules.json"
        )
        parameter_templates = matcher.load_parameter_templates(
            PACKAGE_ROOT
            / "knowledge_graph"
            / "equipment_parameter_chain_templates.json"
        )
        graph = matcher.load_graph(
            PACKAGE_ROOT
            / "equipment_selection_graph"
            / "equipment_selection_graph_v2.json"
        )
        validation = matcher.validate_rules(rules, graph)

        self.assertEqual(validation["status"], "PASS", validation)
        self.assertEqual(validation["rule_family_count"], 17)
        self.assertEqual(validation["model_rule_family_count"], 17)
        self.assertEqual(validation["parameter_template_family_count"], 17)
        self.assertEqual(len(model_rules["families"]), 17)
        self.assertEqual(len(parameter_templates["families"]), 17)
        self.assertGreaterEqual(len(graph["nodes"]), 17)


if __name__ == "__main__":
    unittest.main()
