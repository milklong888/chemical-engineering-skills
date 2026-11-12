"""Black-box tests for isolated literal-text variant generation.

SPDX-License-Identifier: MIT
Copyright (c) 2026 Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TEST_DIR = Path(__file__).resolve().parent
TOOL_DIR = TEST_DIR.parent
SCRIPT = TOOL_DIR / "make_isolation_variants.py"


def edit(find, replace, expected_count):
    return {"find": find, "replace": replace, "expected_count": expected_count}


def variant(name, edits, **metadata):
    return {"name": name, "edits": edits, **metadata}


class VariantCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SCRIPT.is_file():
            raise unittest.SkipTest("make_isolation_variants.py is not present yet")

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(dir=TEST_DIR)
        self.addCleanup(self._cleanup_checked)
        self.tmp = Path(self._tmp.name).resolve()
        self.assertTrue(self.tmp.is_relative_to(TEST_DIR))

    def _cleanup_checked(self):
        self.assertTrue(Path(self._tmp.name).resolve().is_relative_to(TEST_DIR))
        self._tmp.cleanup()

    def run_cli(self, source, plan, output_dir, *extra):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--source", str(source), "--plan", str(plan),
             "--output-dir", str(output_dir), *extra],
            cwd=str(TOOL_DIR), capture_output=True, text=True, check=False,
        )

    def save_plan(self, name, variants, **extra):
        p = self.tmp / name
        p.write_text(json.dumps({"variants": variants, **extra}, ensure_ascii=False), encoding="utf-8")
        return p

    def test_groups_start_from_source_and_edits_are_sequential_with_manifest_receipts(self):
        source = self.tmp / "sample.dat"
        source.write_bytes(b"alpha beta")
        original = source.read_bytes()
        plan = self.save_plan("plan.json", [
            variant("group_one", [edit("alpha", "one", 1)], caller_group_definition={"group": "one"}),
            variant("group_two", [edit("beta", "two", 1)], caller_group_definition={"group": "two"}),
            variant("sequential", [edit("alpha", "beta", 1), edit("beta", "gamma", 2)],
                    caller_group_definition={"group": "sequential"}),
        ])
        outdir = self.tmp / "generated"
        p = self.run_cli(source, plan, outdir)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(source.read_bytes(), original)
        self.assertEqual((outdir / "group_one.dat").read_bytes(), b"one beta")
        self.assertEqual((outdir / "group_two.dat").read_bytes(), b"alpha two")
        self.assertEqual((outdir / "sequential.dat").read_bytes(), b"gamma gamma")
        manifest = json.loads((outdir / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["source"]["sha256"], hashlib.sha256(original).hexdigest())
        self.assertEqual(manifest["source"]["bytes"], len(original))
        self.assertEqual(Path(manifest["source"]["path"]).resolve(), source.resolve())
        self.assertEqual(manifest["plan"]["sha256"], hashlib.sha256(plan.read_bytes()).hexdigest())
        self.assertEqual(manifest["encoding"], "utf-8")
        self.assertEqual([x["name"] for x in manifest["variants"]],
                         ["group_one", "group_two", "sequential"])
        self.assertEqual(manifest["variants"][0]["caller_group_definition"], {"name": "group_one", "caller_group_definition": {"group": "one"}})
        self.assertEqual(manifest["variants"][0]["edits"][0]["expected_count"], 1)
        self.assertEqual(manifest["variants"][0]["edits"][0]["actual_count"], 1)
        for row in manifest["variants"]:
            product = (outdir / row["file"]).read_bytes()
            self.assertEqual(row["sha256"], hashlib.sha256(product).hexdigest())
            self.assertEqual(row["bytes"], len(product))

    def test_encoding_roundtrip_utf8_bom_cp936_and_utf16(self):
        cases = [
            ("utf8bom", bytes.fromhex("efbbbf") + b"alpha\r\nbeta", "utf-8-sig",
             bytes.fromhex("efbbbf") + b"ONE\r\nbeta"),
            ("cp936", "alpha 你好".encode("cp936"), "cp936", "ONE 你好".encode("cp936")),
            ("utf16", "alpha\r\nbeta".encode("utf-16"), "utf-16", "ONE\r\nbeta".encode("utf-16")),
        ]
        for label, raw, encoding, expected in cases:
            with self.subTest(encoding=encoding):
                source = self.tmp / f"{label}.txt"; source.write_bytes(raw)
                before = source.read_bytes()
                plan = self.save_plan(f"{label}.json", [variant("encoded", [edit("alpha", "ONE", 1)])])
                outdir = self.tmp / f"out_{label}"
                p = self.run_cli(source, plan, outdir, "--encoding", encoding)
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertEqual(source.read_bytes(), before)
                self.assertEqual((outdir / "encoded.txt").read_bytes(), expected)
                m = json.loads((outdir / "manifest.json").read_text(encoding="utf-8"))
                self.assertEqual(m["encoding"], encoding)

    def test_count_errors_are_preflighted_before_output_directory_creation(self):
        source = self.tmp / "input.src"; source.write_text("alpha beta", encoding="utf-8")
        plan = self.save_plan("bad_count.json", [
            variant("first", [edit("alpha", "x", 1)]),
            variant("later_wrong_count", [edit("beta", "y", 2)]),
        ])
        outdir = self.tmp / "must_not_exist"
        before = source.read_bytes()
        p = self.run_cli(source, plan, outdir)
        self.assertNotEqual(p.returncode, 0)
        self.assertFalse(outdir.exists())
        self.assertEqual(source.read_bytes(), before)
        for i, value in enumerate((True, False, -1, 1.0, "1")):
            with self.subTest(expected_count=value):
                plan = self.save_plan(f"bad_type_{i}.json", [variant("x", [edit("alpha", "x", value)])])
                outdir = self.tmp / f"invalid_{i}"
                p = self.run_cli(source, plan, outdir)
                self.assertNotEqual(p.returncode, 0)
                self.assertFalse(outdir.exists())
        missing = self.save_plan("missing_count.json", [variant("x", [{"find": "alpha", "replace": "x"}])])
        outdir = self.tmp / "missing_count_output"
        self.assertNotEqual(self.run_cli(source, missing, outdir).returncode, 0)
        self.assertFalse(outdir.exists())

    def test_rejects_unsafe_reserved_duplicate_and_existing_output_names(self):
        source = self.tmp / "input.src"; source.write_text("alpha", encoding="utf-8")
        plans = [
            [variant("../escape", [edit("alpha", "x", 1)])],
            [variant("CON", [edit("alpha", "x", 1)])],
            [variant("aux.txt", [edit("alpha", "x", 1)])],
            [variant("LPT9.more", [edit("alpha", "x", 1)])],
            [variant("a\\b", [edit("alpha", "x", 1)])],
            [variant("C:escape", [edit("alpha", "x", 1)])],
            [variant("trailing.", [edit("alpha", "x", 1)])],
            [variant("safe", [edit("alpha", "x", 1)]), variant("SAFE", [edit("alpha", "y", 1)])],
        ]
        for i, variants in enumerate(plans):
            with self.subTest(i=i):
                plan = self.save_plan(f"unsafe{i}.json", variants)
                outdir = self.tmp / f"unsafe_out{i}"
                p = self.run_cli(source, plan, outdir)
                self.assertNotEqual(p.returncode, 0)
                self.assertFalse(outdir.exists())
        plan = self.save_plan("existing.json", [variant("ok", [edit("alpha", "x", 1)])])
        existing = self.tmp / "already_here"; existing.mkdir()
        marker = existing / "keep.bin"; marker.write_bytes(b"untouched")
        p = self.run_cli(source, plan, existing)
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(list(existing.iterdir()), [marker])
        self.assertEqual(marker.read_bytes(), b"untouched")
        original = source.read_bytes()
        self.assertNotEqual(self.run_cli(source, plan, source).returncode, 0)
        self.assertEqual(source.read_bytes(), original)

    def test_rejects_duplicate_keys_nan_infinity_and_overflow_exponent(self):
        source = self.tmp / "input.src"; source.write_text("alpha", encoding="utf-8")
        valid_variants = json.dumps([variant("ok", [edit("alpha", "x", 1)])])
        malformed = [
            ("duplicate.json", '{"tag":"first","tag":"second","variants":' + valid_variants + '}'),
            ("nan.json", '{"unused":NaN,"variants":' + valid_variants + '}'),
            ("infinity.json", '{"unused":Infinity,"variants":' + valid_variants + '}'),
            ("overflow.json", '{"unused":1e400,"variants":' + valid_variants + '}'),
        ]
        for name, raw in malformed:
            with self.subTest(name=name):
                plan = self.tmp / name; plan.write_text(raw, encoding="utf-8")
                outdir = self.tmp / (name + "_output")
                before = source.read_bytes()
                p = self.run_cli(source, plan, outdir)
                self.assertNotEqual(p.returncode, 0)
                self.assertFalse(outdir.exists())
                self.assertEqual(source.read_bytes(), before)

    def test_roundtrip_mismatch_and_unencodable_replacement_fail_before_writes(self):
        for label, raw, encoding, replacement in [
            ("bom", b"alpha", "utf-8-sig", "x"),
            ("ascii", b"alpha", "ascii", "\u4e2d"),
        ]:
            with self.subTest(label=label):
                source = self.tmp / (label + ".src"); source.write_bytes(raw)
                plan = self.save_plan(label + ".json", [variant("ok", [edit("alpha", replacement, 1)])])
                output = self.tmp / (label + "_output")
                p = self.run_cli(source, plan, output, "--encoding", encoding)
                self.assertNotEqual(p.returncode, 0)
                self.assertFalse(output.exists())
                self.assertEqual(source.read_bytes(), raw)

    def test_manifest_collision_is_rejected(self):
        source = self.tmp / "source.json"; source.write_bytes(b"alpha")
        plan = self.save_plan("plan.json", [variant("manifest", [edit("alpha", "x", 1)])])
        output = self.tmp / "output"
        self.assertNotEqual(self.run_cli(source, plan, output).returncode, 0)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()


