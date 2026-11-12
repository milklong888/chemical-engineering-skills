"""Synthetic offline file checks. These tests never launch Aspen or a service."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "toolpack.py"
spec = importlib.util.spec_from_file_location("tested_toolpack", SCRIPT)
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class FileChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def csv(self, text):
        file = self.root / "samples.csv"
        file.write_text(text, encoding="utf-8")
        return file

    def grid(self, text, **kwargs):
        return tool.check_grid(self.csv(text), time_column="t", interval=2,
                               start=0, end=4, tolerance=0, **kwargs)

    def manifest(self, **replace):
        target = self.root / "a.txt"; target.write_bytes(b"abc")
        row = {"path": "a.txt", "size": 3, "sha256": hashlib.sha256(b"abc").hexdigest()}
        row.update(replace)
        file = self.root / "manifest.json"
        file.write_text(json.dumps({"files": [row]}), encoding="utf-8")
        return file

    def test_grid_valid(self):
        out = self.grid("t,x\n0,1\n2,3\n4,5\n", numeric_columns=["x"])
        self.assertTrue(out["matches"])
        self.assertFalse(out["native_provenance_verified"])

    def test_grid_missing_sample(self):
        self.assertFalse(self.grid("t\n0\n4\n")["matches"])

    def test_grid_shifted(self):
        self.assertFalse(self.grid("t\n1\n3\n5\n")["matches"])

    def test_grid_duplicate_time(self):
        with self.assertRaises(ValueError): self.grid("t\n0\n0\n4\n")

    def test_grid_nan(self):
        with self.assertRaises(ValueError): self.grid("t,x\n0,1\n2,nan\n4,5\n", numeric_columns=["x"])

    def test_grid_infinite_argument(self):
        with self.assertRaises(ValueError):
            tool.check_grid(self.csv("t\n0\n2\n"), time_column="t", interval=float("inf"), start=0, end=2, tolerance=0)

    def test_grid_ragged(self):
        with self.assertRaises(ValueError): self.grid("t,x\n0\n2,1\n4,1\n")

    def test_grid_duplicate_headers(self):
        with self.assertRaises(ValueError): self.grid("t,t\n0,0\n2,2\n4,4\n")

    def test_grid_missing_column(self):
        with self.assertRaises(ValueError): self.grid("time\n0\n2\n4\n")

    def test_grid_noninteger_horizon(self):
        out = tool.check_grid(self.csv("t\n0\n2\n4\n"), time_column="t", interval=2, start=0, end=5, tolerance=0)
        self.assertFalse(out["matches"])

    def test_manifest_valid(self):
        self.assertTrue(tool.verify_manifest(self.root, self.manifest())["matches"])

    def test_manifest_changed_bytes(self):
        m = self.manifest(); (self.root / "a.txt").write_bytes(b"abd")
        self.assertFalse(tool.verify_manifest(self.root, m)["matches"])

    def test_manifest_boolean_size(self):
        with self.assertRaises(ValueError): tool.verify_manifest(self.root, self.manifest(size=True))

    def test_manifest_traversal(self):
        with self.assertRaises(ValueError): tool.verify_manifest(self.root, self.manifest(path="../outside.txt"))

    def test_manifest_windows_drive(self):
        with self.assertRaises(ValueError): tool.verify_manifest(self.root, self.manifest(path="C:/outside.txt"))

    def test_manifest_unsafe_aliases(self):
        for path in ["/a.txt", "./a.txt", "a//b", "a\\b", "a.txt:stream"]:
            with self.subTest(path=path), self.assertRaises(ValueError):
                tool.contained_file(self.root, path)

    def test_manifest_bad_digest(self):
        with self.assertRaises(ValueError): tool.verify_manifest(self.root, self.manifest(sha256="z" * 64))

    def test_manifest_duplicate_file(self):
        m = self.manifest(); obj = json.loads(m.read_text()); obj["files"] *= 2
        m.write_text(json.dumps(obj))
        with self.assertRaises(ValueError): tool.verify_manifest(self.root, m)

    def test_json_duplicate_key(self):
        p = self.root / "bad.json"; p.write_text('{"a":1,"a":2}')
        with self.assertRaises(ValueError): tool.load_json(p)

    def test_json_nonfinite(self):
        p = self.root / "bad.json"; p.write_text('{"a":NaN}')
        with self.assertRaises(ValueError): tool.load_json(p)

    def test_json_overflow_number(self):
        p = self.root / "bad.json"; p.write_text('{"a":1e999}')
        with self.assertRaises(ValueError): tool.load_json(p)

    def test_plan_uses_declared_environment_python(self):
        entry = self.root / "tools" / "expert_mcp.py"
        entry.parent.mkdir(); entry.write_text("# fixture; not executed")
        interpreter = self.root / "environment-python.exe"
        interpreter.write_bytes(b"synthetic file; never executed")
        settings = self.root / "settings.json"
        settings.write_text(json.dumps({"paths": {"chemical-expert-mcp": str(self.root)},
                                        "interpreters": {"chemical-expert-mcp": str(interpreter)}}))
        plan = tool.invocation_plan("chemical-expert-mcp", settings)
        self.assertEqual(plan["argv"][0], str(interpreter))
        self.assertFalse(plan["execution_performed"])

    def test_plan_does_not_substitute_global_python(self):
        entry = self.root / "tools" / "expert_mcp.py"
        entry.parent.mkdir(); entry.write_text("# fixture; not executed")
        settings = self.root / "settings.json"
        settings.write_text(json.dumps({"paths": {"chemical-expert-mcp": str(self.root)}}))
        with self.assertRaises(ValueError): tool.invocation_plan("chemical-expert-mcp", settings)

    def test_catalog_without_settings_does_not_launch(self):
        self.assertIn("tools", tool.local_catalog())

    def test_unknown_plan(self):
        with self.assertRaises(ValueError): tool.invocation_plan("unknown")

    def test_library_has_no_executable_plan(self):
        entry = self.root / "scripts" / "aspen_evidence.py"
        entry.parent.mkdir(); entry.write_text("# synthetic library")
        settings = self.root / "settings.json"
        settings.write_text(json.dumps({"paths": {"operations-evidence": str(self.root)}}))
        with self.assertRaises(ValueError): tool.invocation_plan("operations-evidence", settings)


if __name__ == "__main__":
    unittest.main()
