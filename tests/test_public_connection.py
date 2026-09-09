"""Public query routing and an actual bundled standards-database read."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("public_expert_cli", ROOT / "tools/expert_cli.py")
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


class PublicConnectionTests(unittest.TestCase):
    def routed(self, query, **kwargs):
        with patch.object(cli, "equipment", return_value={"backend_exit_code": 0, "response": {}}) as call:
            cli.search(query, corpus="equipment", **kwargs)
            return call.call_args.args[0]["payload"]

    def test_standard_code_reaches_database(self):
        for query in ("GB/T 17395", "HG/T 20592", "PN16 法兰", "管壁厚度"):
            with self.subTest(query=query):
                self.assertIn("design_standards", self.routed(query)["package_ids"])

    def test_generic_equipment_keeps_original_defaults(self):
        self.assertNotIn("package_ids", self.routed("heat exchanger"))

    def test_explicit_registered_scope_is_preserved(self):
        self.assertEqual(self.routed("GB/T 17395", package_ids=["equipment_core"])["package_ids"], ["equipment_core"])

    def test_unknown_scope_rejected_before_backend(self):
        with patch.object(cli, "equipment") as call:
            with self.assertRaises(ValueError):
                cli.search("pipe", corpus="equipment", package_ids=["private_project"])
            call.assert_not_called()

    def test_readonly_query_does_not_inherit_mcp_protocol_stdin(self):
        response = cli.subprocess.CompletedProcess([], 0, stdout='{"hits":[]}', stderr="")
        with patch.object(cli.subprocess, "run", return_value=response) as call:
            cli.search("heat", corpus="chemical_principles")
            self.assertEqual(call.call_args.kwargs["stdin"], cli.subprocess.DEVNULL)

    def test_actual_public_database_hit_retains_scope(self):
        result = cli.search("GB/T 17395", corpus="equipment_standards", limit=1)
        self.assertEqual(result["equipment"]["backend_exit_code"], 0)
        body = json.dumps(result["equipment"]["response"], ensure_ascii=False)
        self.assertIn("gbt17395_dimension_weight_tolerances", body)
        self.assertIn("numeric_reuse_allowed", body)
        self.assertIn("METHOD_ONLY", body)
        self.assertEqual(result["requested_equipment_packages"], ["design_standards"])


if __name__ == "__main__":
    unittest.main()
