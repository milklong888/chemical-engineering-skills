"""Portable backend tests: synthetic inputs, source-fact parity, no COM/network."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

BACKEND = Path(__file__).resolve().parents[1] / "backends/equipment"


def canonical(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest().upper()


def call(operation, payload=None, *, root=BACKEND):
    environment = dict(os.environ)
    for key in list(environment):
        if key.startswith("EQUIPMENT_DESIGN_LLM_") or key == "EQUIPMENT_BACKEND_ALLOW_COM":
            environment.pop(key)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    request = {"schema": "equipment-design-agent-request-v1", "request_id": "PORTABLE_SYNTHETIC_TEST", "operation": operation, "payload": payload or {}}
    result = subprocess.run([sys.executable, "-B", "-X", "utf8", str(root / "app/equipment_design_agent.py")],
                            input=json.dumps(request), capture_output=True, text=True, encoding="utf-8", env=environment,
                            cwd=root, timeout=90)
    return result.returncode, json.loads(result.stdout), result.stderr


class EquipmentBackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(BACKEND / "app"))
        sys.path.insert(0, str(BACKEND / "scripts"))
        import app_core, projected_standard_store, source_code_manifest, runtime_bundle, equipment_calc
        cls.core, cls.projection, cls.sources, cls.assets, cls.calc = app_core, projected_standard_store, source_code_manifest, runtime_bundle, equipment_calc
        cls.golden = json.loads((BACKEND / "app/fixtures/original_2_4_0_backend_golden.json").read_text(encoding="utf-8"))

    def test_01_original_selftest(self):
        code, response, stderr = call("selftest")
        self.assertEqual((code, stderr), (0, ""))
        self.assertEqual(response["result"]["check_count"], 17)
        self.assertTrue(all(row["pass"] for row in response["result"]["checks"]))

    def test_02_all_original_synthetic_family_outputs(self):
        fixture = json.loads((BACKEND / "app/fixtures/all_family_minimum_meaningful_inputs.json").read_text(encoding="utf-8"))
        actual = []
        for case in fixture["cases"]:
            result = self.core.auto_match({"equipment_family": case["family_id"], **case.get("values", {})})["result"]
            leading = result.get("model_recommendation", {}).get("leading_candidate") or {}
            actual.append({"family_id": case["family_id"], "derived_parameters": result.get("derived_parameters"),
                "calculations": [{k: x.get(k) for k in ("calculation_id", "target_field", "value", "unit", "formula", "equation_chain")} for x in result.get("calculations", [])],
                "leading": {k: leading.get(k) for k in ("candidate_kind", "designation", "recommended_type", "specification")},
                "status": result.get("status"), "terminal_selection": result.get("terminal_selection")})
        self.assertEqual(actual, self.golden["family_rows"])

    def test_03_all_pipe_rows_match_original_fields(self):
        store = self.projection.load_pipe_store(BACKEND)
        for name, expected_count in (("pn", 12), ("wall", 5620)):
            rows = store[name + "_records"]
            actual = {row["record_id"]: canonical({k: v for k, v in row.items() if k != "source_payload_json"}) for row in rows}
            self.assertEqual(len(actual), expected_count)
            self.assertEqual(actual, self.golden[name + "_record_hashes"])
        for key, expected in self.golden["datasets"].items():
            self.assertEqual({field: store["datasets"][key].get(field) for field in expected}, expected)

    def test_04_fact_and_figure_counts_and_qualifications(self):
        result = self.projection.verification(BACKEND)
        self.assertEqual(result["counts"], {"datasets": 24, "standard_records": 24887, "figure_datasets": 14, "figure_records": 1844})
        self.assertNotEqual(result["projection_sha256"], result["parent_database_sha256"])
        connection, _manifest = self.projection.verified_store(BACKEND)
        for table in ("standard_records", "figure_records"):
            for (text,) in connection.execute(f'SELECT record_json FROM "{table}"'):
                row = json.loads(text)
                self.assertEqual(row["projection_role"], "source_fact_not_automatic_design_evidence")
                self.assertEqual(len(row["record_sha256"]), 64)
                self.assertNotIn("audit_path", row)
                self.assertNotIn("source_payload_json", row)

    def test_05_fact_query_protocol(self):
        code, response, _ = call("knowledge_search", {"query": "GB/T 17395", "limit": 2, "package_ids": ["design_standards"]})
        self.assertEqual(code, 0)
        hits = response["result"]["hits"]
        self.assertEqual(len(hits), 2)
        self.assertTrue(all(row["numeric_reuse_allowed"] is False for row in hits))
        self.assertTrue(all(row["parent_database_sha256"] == self.projection.PARENT_DATABASE_SHA256 for row in hits))
        self.assertTrue(all("gbt17395" in row["source_path"] for row in hits))

    def test_06_source_and_runtime_manifests(self):
        self.assertTrue(self.sources.verify_current_runtime(BACKEND, frozen=False)["verified"])
        self.assertTrue(self.assets.verify_runtime_bundle(BACKEND, required=True)["verified"])
        self.assertNotIn("app/tk_gui.py", self.sources.CORE_SOURCE_PATHS)
        self.assertIn("app/aspen_com_import.py", self.sources.CORE_SOURCE_PATHS)

    def test_16_original_method_graph_anchors_restored_without_invented_nodes(self):
        graph = BACKEND / "knowledge_graph"
        provenance = json.loads((graph / "RESTORATION_PROVENANCE.json").read_text(encoding="utf-8"))
        text = (graph / "formula_family_nodes.md").read_text(encoding="utf-8")
        refs = set(re.findall(r"knowledge_graph/formula_family_nodes.md#([A-Za-z0-9_]+)", (BACKEND / "scripts/equipment_design_match.py").read_text(encoding="utf-8")))
        gaps = set(provenance["original_node_gaps_not_invented"])
        self.assertEqual(len(gaps), 5)
        for node in refs - gaps:
            self.assertTrue(f'id="{node}"' in text or f"## {node}\n" in text, node)
        for node in gaps:
            self.assertNotIn(f'id="{node}"', text)
        self.assertIn("A=Q/(U*F*DeltaT_lm)", text)
        self.assertTrue((graph / "standards_graph/exchanger_standards_nodes.md").is_file())
        for item in provenance["files"]:
            self.assertEqual(hashlib.sha256((BACKEND / item["runtime_path"]).read_bytes()).hexdigest().upper(), item["sha256"])
        authority = json.loads((BACKEND / "equipment_selection_graph/equipment_selection_graph_v2.json").read_text(encoding="utf-8"))
        for node in authority["nodes"]:
            for key in ("relative_path", "absolute_path"):
                value = (node.get("local_source") or {}).get(key)
                if value:
                    self.assertTrue(value.startswith("source://"))

    def test_07_source_tamper_refused(self):
        with tempfile.TemporaryDirectory(prefix="equipment_source_tamper_") as tmp:
            root = Path(tmp) / "backend"
            shutil.copytree(BACKEND, root, ignore=shutil.ignore_patterns("__pycache__"))
            path = root / "scripts/equipment_design_match.py"
            path.write_bytes(path.read_bytes() + b"\n# synthetic tamper\n")
            code, response, _ = call("catalog", root=root)
            self.assertNotEqual(code, 0)
            self.assertFalse(response["ok"])

    def test_08_data_tamper_refused(self):
        with tempfile.TemporaryDirectory(prefix="equipment_data_tamper_") as tmp:
            root = Path(tmp) / "backend"
            shutil.copytree(BACKEND, root, ignore=shutil.ignore_patterns("__pycache__"))
            path = root / "data/standard_facts.sqlite.gz"
            content = bytearray(path.read_bytes()); content[-9] ^= 1; path.write_bytes(content)
            code, response, _ = call("catalog", root=root)
            self.assertNotEqual(code, 0)
            self.assertFalse(response["ok"])

    def test_09_missing_data_refused_not_rebuilt(self):
        with tempfile.TemporaryDirectory(prefix="equipment_data_missing_") as tmp:
            root = Path(tmp) / "backend"
            shutil.copytree(BACKEND, root, ignore=shutil.ignore_patterns("__pycache__"))
            path = root / "data/standard_facts.sqlite.gz"; path.unlink()
            code, response, _ = call("catalog", root=root)
            self.assertNotEqual(code, 0)
            self.assertFalse(response["ok"])
            self.assertFalse(path.exists())

    def test_10_com_requires_explicit_permission(self):
        code, response, _ = call("aspen_import", {"source_path": "SYNTHETIC_NOT_A_REAL_CASE.bkp", "pressure_basis": "absolute"})
        self.assertNotEqual(code, 0)
        self.assertIn("COM_EXECUTION_NOT_AUTHORIZED", json.dumps(response, ensure_ascii=False))
        self.assertTrue((BACKEND / "app/aspen_com_import.py").is_file())

    def test_11_case_audit_missing_profile_no_outputs(self):
        result = subprocess.run([sys.executable, "-B", "-X", "utf8", str(BACKEND / "scripts/equipment_calc.py")],
                                capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["status"], "dependency_unavailable")
        self.assertFalse(json.loads(result.stdout)["outputs_created"])
        self.assertAlmostEqual(self.calc.pump_hydraulic_power_kw(36, 10, 1000), 0.980665)

    def test_12_no_gui_files(self):
        self.assertFalse((BACKEND / "app/tk_gui.py").exists())
        self.assertFalse((BACKEND / "app/pfd_canvas.py").exists())
        self.assertFalse(list(BACKEND.rglob("*.exe")))

    def test_13_json_export_derivation_is_available(self):
        path = BACKEND / "app/fixtures/mock_aspen_pump.json"
        code, response, _ = call("aspen_derive", {"export_path": str(path), "export_sha256": hashlib.sha256(path.read_bytes()).hexdigest().upper()})
        self.assertEqual(code, 0)
        self.assertIsInstance(response["result"], dict)
        self.assertNotEqual(response["result"].get("formal_use_gate"), "ELIGIBLE_AS_PROCESS_BASIS")

    def test_14_hgt_computational_projection(self):
        result = subprocess.run([sys.executable, "-B", "-X", "utf8", str(BACKEND / "knowledge_graph/type_selection/hgt20592_20635/validate_package.py"), "--runtime-only", "--json"], capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "PASS_RUNTIME_ONLY")
        self.assertFalse(report["formal_engineering_acceptance"])

    def test_15_hgt_raw_source_not_falsely_passed(self):
        result = subprocess.run([sys.executable, "-B", "-X", "utf8", str(BACKEND / "knowledge_graph/type_selection/hgt20592_20635/validate_package.py"), "--json"], capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source_text_dependency_unavailable", result.stdout)


if __name__ == "__main__":
    unittest.main()
