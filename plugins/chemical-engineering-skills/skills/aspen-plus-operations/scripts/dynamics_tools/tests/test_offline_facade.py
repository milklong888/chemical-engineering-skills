"""Real public-parser bridge and facade regressions; synthetic files only."""
import hashlib
import json
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE.parent))
from dynamics_tools import offline_facade as facade, toolpack


def native_shaped_text():
    # This is synthetic text in a supported shape, never an Aspen run receipt.
    return "\n".join(["Summary of Simulation Errors", "Physical",
                      "Property System Simulation", "Terminal Errors 0 0 0",
                      "Severe Errors 0 0 0", "Errors 0 0 0", "Warnings 0 0 0",
                      "NO ERRORS OR WARNINGS GENERATED", ""])


class FacadeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def file(self, name, content):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def assert_scope(self, result):
        self.assertFalse(result["external_process_started"])
        self.assertFalse(result["strict_simulation_passed"])
        self.assertEqual(result["engineering_acceptance"], "not_assessed")
        self.assertEqual(result["native_calculation_acceptance"], "not_assessed")

    def test_manifest_success_and_invalid(self):
        target = self.file("a.txt", "synthetic")
        manifest = self.file("manifest.json", json.dumps({"files": [{"path": "a.txt",
            "size": target.stat().st_size, "sha256": toolpack.sha256(target)}]}))
        result = facade.verify_package_manifest(str(self.root), str(manifest))
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["matches"]); self.assert_scope(result)
        bad = facade.verify_package_manifest(str(self.root), str(self.root / "missing.json"))
        self.assertEqual(bad["status"], "invalid_or_unavailable"); self.assert_scope(bad)

    def test_grid_success_and_invalid(self):
        csv = self.file("samples.csv", "t,x\n0,1\n2,2\n4,3\n")
        result = facade.check_csv_grid(str(csv), "t", 2, 0, 4, 0, ["x"])
        self.assertTrue(result["matches"]); self.assert_scope(result)
        bad = facade.check_csv_grid(str(csv), "t", 0, 0, 4, 0)
        self.assertEqual(bad["status"], "invalid_or_unavailable"); self.assert_scope(bad)
        bad = facade.check_csv_grid(str(csv), "t", True, 0, 4, 0)
        self.assertEqual(bad["status"], "invalid_or_unavailable")

    def test_grid_subnormal_interval_returns_error_receipt_in_facade_and_cli(self):
        csv = self.file('samples.csv', 't\n0\n1\n')
        result = facade.check_csv_grid(str(csv), 't', 5e-324, 0, 1, 0)
        self.assertEqual(result['status'], 'invalid_or_unavailable')
        self.assert_scope(result)
        output = io.StringIO()
        with patch.object(sys, 'argv', ['toolpack.py', 'grid', str(csv),
                '--time-column', 't', '--interval', '5e-324', '--start', '0',
                '--end', '1', '--time-abs-tol', '0']), contextlib.redirect_stdout(output):
            code = toolpack.main()
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue())['status'], 'invalid_or_unavailable')

    def test_history_success_and_invalid_real_public_owner(self):
        history = self.file("synthetic.his", native_shaped_text())
        result = facade.inspect_history(str(history))
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["matches"])
        self.assertEqual(result["owner_source"], "public_sibling_parser")
        self.assertEqual(Path(result["owner_path"]), toolpack.PUBLIC_PARSER.resolve())
        self.assertEqual(result["owner_sha256"], toolpack.sha256(toolpack.PUBLIC_PARSER))
        self.assertEqual(result["owner_sha256_lf_normalized"], toolpack.PUBLIC_PARSER_SHA256_LF)
        self.assert_scope(result)
        bad = facade.inspect_history(str(self.root / "missing.his"))
        self.assertEqual(bad["status"], "invalid_or_unavailable"); self.assert_scope(bad)

    def test_history_problem_and_incomplete_tables_do_not_pass(self):
        for text in (native_shaped_text() + "* WARNING synthetic problem\n",
                     native_shaped_text().replace("Warnings 0 0 0\n", ""),
                     "NO ERRORS OR WARNINGS GENERATED\n"):
            result = facade.inspect_history(str(self.file("synthetic.his", text)))
            self.assertEqual(result["status"], "ok")
            self.assertFalse(result["matches"]); self.assert_scope(result)

    def test_complete_native_history_without_summary(self):
        text = (" + + ASPEN PLUS CALCULATION HISTORY + +\n"
                " Results generated                     Time =     34.31\n"
                "RUN SAVED\n\n NO ERRORS OR WARNINGS GENERATED\n")
        result = facade.inspect_history(str(self.file("complete.his", text)))
        self.assertTrue(result["matches"])
        self.assert_scope(result)
        with_warning = text.replace("RUN SAVED", "* WARNING IN THE BLOCK\nRUN SAVED")
        self.assertFalse(facade.inspect_history(str(self.file("warning.his", with_warning)))["matches"])

    def test_history_fallback_real_public_source_copy_requires_hash(self):
        history = self.file("synthetic.his", native_shaped_text())
        parser = self.root / "operations/scripts/aspen_evidence.py"
        parser.parent.mkdir(parents=True)
        parser.write_bytes(toolpack.PUBLIC_PARSER.read_bytes())
        with patch.object(toolpack, "PUBLIC_PARSER", self.root / "absent-public-parser.py"):
            missing = facade.inspect_history(str(history))
            self.assertEqual(missing["status"], "invalid_or_unavailable")
            unbound = facade.inspect_history(str(history), str(parser.parents[1]))
            self.assertEqual(unbound["status"], "invalid_or_unavailable")
            result = facade.inspect_history(str(history), str(parser.parents[1]),
                                            expected_owner_sha256=toolpack.sha256(parser))
            self.assertTrue(result["matches"])
            self.assertEqual(result["owner_source"], "explicit_operations_fallback")
            self.assertEqual(result["owner_sha256"], toolpack.sha256(parser))
            self.assert_scope(result)

    def test_history_identity_gate_precedes_import(self):
        history = self.file("synthetic.his", native_shaped_text())
        parser = self.file("untrusted.py", "raise RuntimeError('must not import')\n")
        with patch.object(toolpack, "PUBLIC_PARSER", parser):
            bad = facade.inspect_history(str(history))
            self.assertEqual(bad["status"], "invalid_or_unavailable")
            self.assertIn("pinned public source", bad["error"])
        fallback = self.file("untrusted/scripts/aspen_evidence.py", "raise RuntimeError('must not import')\n")
        with patch.object(toolpack, "PUBLIC_PARSER", self.root / "absent-public-parser.py"):
            bad = facade.inspect_history(str(history), str(fallback.parents[1]),
                                          expected_owner_sha256=toolpack.sha256(fallback))
            self.assertEqual(bad["status"], "invalid_or_unavailable")
            self.assertIn("pinned public source", bad["error"])
        bad = facade.inspect_history(str(history), expected_owner_sha256="0" * 64)
        self.assertEqual(bad["status"], "invalid_or_unavailable")

    def test_catalog_success_and_invalid(self):
        result = facade.list_external_tools()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(result["tools"]), 5); self.assert_scope(result)
        for item in result["tools"]:
            self.assertEqual(item["availability"], "external_dependency")
            self.assertFalse(item["source_included"])
            self.assertEqual(item["verification_state"], "not_verified_by_this_package")
        bad = facade.list_external_tools(str(self.root / "missing.json"))
        self.assertEqual(bad["status"], "invalid_or_unavailable"); self.assert_scope(bad)

    def test_plan_success_and_invalid_never_runs_fixture(self):
        self.file("external/tools/expert_mcp.py", "raise RuntimeError('not executable')\n")
        python = self.file("fixture-python.exe", "synthetic non-executable fixture")
        settings = self.file("settings.json", json.dumps({
            "paths": {"chemical-expert-mcp": str(self.root / "external")},
            "interpreters": {"chemical-expert-mcp": str(python)}}))
        result = facade.plan_external_invocation("chemical-expert-mcp", str(settings))
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["argv"][0], str(python))
        self.assertFalse(result["execution_performed"]); self.assert_scope(result)
        bad = facade.plan_external_invocation("unknown", str(settings))
        self.assertEqual(bad["status"], "invalid_or_unavailable"); self.assert_scope(bad)



if __name__ == "__main__":
    unittest.main()
