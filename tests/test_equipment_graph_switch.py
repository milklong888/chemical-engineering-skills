"""The project equipment graph setting applies only to general searches."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from tools import expert_cli


class EquipmentGraphSwitchTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name) / "project"
        self.other_project = Path(temporary.name) / "other-project"
        self.project.mkdir()
        self.other_project.mkdir()

        self.knowledge_result = {"results": [{"node_id": "L3-03"}]}
        patcher = patch.object(
            expert_cli.subprocess,
            "run",
            return_value=subprocess.CompletedProcess(
                [], 0, stdout='{"results": [{"node_id": "L3-03"}]}', stderr=""
            ),
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.equipment_result = {"backend_exit_code": 0, "response": {"result": {"hits": []}}}
        self.equipment_runner = Mock(return_value=self.equipment_result)

    def execute(self, operation, payload, project=None):
        return expert_cli.execute(
            {"operation": operation, "payload": payload},
            project or self.project,
            equipment_runner=self.equipment_runner,
        )

    def search(self, project=None, **scope):
        return self.execute("search", {"query": "GB/T 17395", **scope}, project)

    def test_default_search_skips_equipment_even_for_standard_number(self):
        self.assertIs(self.execute("equipment_graph", {})["enabled"], False)
        for scope in ({}, {"corpus": "all"}):
            with self.subTest(scope=scope):
                result = self.search(**scope)
                self.assertEqual(result["knowledge"], self.knowledge_result)
                self.assertIsNone(result["equipment"])
        self.equipment_runner.assert_not_called()

    def test_project_setting_persists_across_requests_and_can_be_disabled(self):
        self.assertIs(self.execute("equipment_graph", {"enabled": True})["enabled"], True)
        self.equipment_runner.assert_not_called()
        self.assertIs(self.execute("equipment_graph", {})["enabled"], True)

        result = self.search(corpus="all")
        self.assertEqual(result["knowledge"], self.knowledge_result)
        self.assertEqual(result["equipment"], self.equipment_result)
        self.equipment_runner.assert_called_once()
        self.assertEqual(
            self.equipment_runner.call_args.args[0]["operation"], "knowledge_search"
        )

        self.assertIs(self.execute("equipment_graph", {"enabled": False})["enabled"], False)
        self.assertIs(self.execute("equipment_graph", {})["enabled"], False)
        self.assertIsNone(self.search(corpus="all")["equipment"])
        self.equipment_runner.assert_called_once()

    def test_switch_is_isolated_between_project_roots(self):
        self.execute("equipment_graph", {"enabled": True})

        self.assertIs(self.execute("equipment_graph", {}, self.other_project)["enabled"], False)
        self.assertIsNone(self.search(self.other_project, corpus="all")["equipment"])
        self.equipment_runner.assert_not_called()
        self.assertEqual(self.search(corpus="all")["equipment"], self.equipment_result)
        self.equipment_runner.assert_called_once()

    def test_explicit_equipment_corpora_query_without_changing_project_setting(self):
        for corpus in ("equipment", "equipment_standards"):
            with self.subTest(corpus=corpus):
                self.equipment_runner.reset_mock()
                result = self.search(corpus=corpus)
                self.assertEqual(result["equipment"], self.equipment_result)
                self.equipment_runner.assert_called_once()
                request = self.equipment_runner.call_args.args[0]
                self.assertEqual(request["operation"], "knowledge_search")
                if corpus == "equipment_standards":
                    self.assertEqual(request["payload"]["package_ids"], ["design_standards"])
                self.assertIs(self.execute("equipment_graph", {})["enabled"], False)
                self.assertIsNone(self.search(corpus="all")["equipment"])
                self.equipment_runner.assert_called_once()

    def test_explicit_equipment_calculation_works_when_search_is_disabled(self):
        request = {
            "schema": "equipment-design-agent-request-v1",
            "request_id": "P-101",
            "operation": "manual_match",
            "payload": {"equipment": {"equipment_tag": "P-101", "equipment_type": "pump"}},
        }
        self.assertIs(self.execute("equipment_graph", {})["enabled"], False)
        self.assertEqual(self.execute("equipment", request), self.equipment_result)
        self.equipment_runner.assert_called_once_with(request)
        self.assertIs(self.execute("equipment_graph", {})["enabled"], False)


if __name__ == "__main__":
    unittest.main()
