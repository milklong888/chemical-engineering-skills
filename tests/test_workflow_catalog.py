from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import expert_cli, product_contract
from tools.workflow_catalog import lookup


class WorkflowCatalogTests(unittest.TestCase):
    def test_cli_lists_exactly_nineteen_registered_skills(self):
        result = expert_cli.execute({"operation": "workflow", "payload": {"action": "list"}}, ROOT)
        self.assertEqual(result["schema"], "chemical-engineering-workflow-catalog-v1")
        self.assertEqual(len(result["skill_ids"]), 19)
        self.assertIn("chemical-engineering-expert", result["skill_ids"])
        self.assertIn("aspen-non-reactor-equipment-cost", result["skill_ids"])
        self.assertIn("aspen-flowsheet-cost-skill-builder", result["skill_ids"])
        self.assertNotIn("aspen-project-equipment-cost-batch", result["skill_ids"])
        self.assertIn("script-catalog", result["resources"])

    def test_real_skill_read_returns_path_hash_and_full_text(self):
        result = expert_cli.execute({"operation": "workflow", "payload": {
            "action": "read", "mode": "skill", "skill_id": "chemical-engineering-expert"}}, ROOT)
        asset = result["result"]
        data = Path(asset["path"]).read_bytes()
        self.assertTrue(asset["available"])
        self.assertEqual(asset["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(asset["text"], data.decode("utf-8-sig"))
        self.assertIn("SKILL", asset["text"])

    def test_registered_resource_read_and_script_graph_preserve_base_next(self):
        resource = lookup({"action": "read", "mode": "resource", "resource": "script-catalog"})
        self.assertTrue(resource["result"]["available"])
        graph = lookup({"action": "script", "search": "tower"})
        self.assertGreaterEqual(graph["result"]["anchor_summary"]["existing"], 0)
        self.assertTrue(graph["result"]["nodes"])
        self.assertTrue(all("base" in node and "next" in node and "anchor" in node for node in graph["result"]["nodes"]))
        self.assertIn("adaptation_boundary", graph["result"])

    def test_tower_path_routes_child_shortcut_then_discrete_candidates_without_false_execution(self):
        route = lookup({"action": "script", "path_name": "tower_island"})
        nodes = route["result"]["nodes"]
        ids = [node["id"] for node in nodes]
        self.assertLess(ids.index("SEP-03"), ids.index("BUILD-07"))
        self.assertLess(ids.index("BUILD-07"), ids.index("SEP-01"))
        self.assertLess(ids.index("SEP-01"), ids.index("SEP-02"))
        self.assertNotIn("BUILD-06", ids)  # Calculator is conditional, not an ordinary tower default.
        self.assertNotIn("SEP-08", ids)  # Native Optimization is an optional qualified branch.
        self.assertIn("does not create child model", nodes[ids.index("SEP-03")]["execution_boundary"])
        self.assertIn("separate version-qualified implementation", nodes[ids.index("SEP-02")]["execution_boundary"])
        self.assertTrue(route["read_only"])
        self.assertFalse(route["engineering_accepted"])

    def test_unknown_ids_paths_and_extra_fields_are_rejected(self):
        with self.assertRaises(ValueError):
            lookup({"action": "read", "mode": "skill", "skill_id": "../../secret"})
        with self.assertRaises(ValueError):
            lookup({"action": "read", "mode": "skill", "skill_id": "aspen-project-equipment-cost-batch"})
        with self.assertRaises(ValueError):
            lookup({"action": "read", "mode": "resource", "resource": "../../secret"})
        with self.assertRaises(ValueError):
            lookup({"action": "read", "mode": "skill", "skill_id": "chemical-engineering-expert", "path": "x"})
        with self.assertRaises(ValueError):
            lookup({"action": "script", "path_name": "../../secret"})
        with self.assertRaises(ValueError):
            lookup({"action": "list", "skill_id": "chemical-engineering-expert"})
        for value in (True, 1, [], ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                lookup({"action": "read", "mode": "skill", "skill_id": value})

    def test_official_id_set_rejects_same_count_stranger_directory(self):
        import tools.workflow_catalog as catalog
        original = catalog.OFFICIAL_SKILL_IDS
        try:
            catalog.OFFICIAL_SKILL_IDS = frozenset((*original, "stranger-skill"))
            with self.assertRaises(ValueError):
                lookup({"action": "list"})
        finally:
            catalog.OFFICIAL_SKILL_IDS = original

    def test_workflow_contract_is_discoverable_without_backend(self):
        contract = product_contract.schema("workflow-catalog", lambda request: request)
        self.assertEqual(contract["mcp_tool"], "workflow_lookup")
        self.assertTrue(contract["read_only"])


if __name__ == "__main__":
    unittest.main()
