# 作者：milklong
# SPDX-FileCopyrightText: 2026 milklong (GitHub: milklong888) and contributors
# SPDX-License-Identifier: MIT
"""Synthetic, isolated filesystem regressions; no production files or network."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import check_attribution as checker


MIT = '''MIT License

Copyright (c) 2024 Original Upstream Contributors
Copyright (c) 2026 milklong and contributors

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
'''


class AttributionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="attribution-synthetic-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "repo"
        self.root.mkdir()
        self.url = "https://github.com/milklong888/synthetic-test-project"
        self.manifest = {
            "schema": "milklong-attribution/v1",
            "author": "milklong",
            "project_url": self.url,
            "skill_root": "skills",
            "entries": [],
            "policy_files": ["AUTHORSHIP.md"],
            "license_files": ["LICENSE"],
        }
        for name in ("alpha", "乙技能"):
            path = f"skills/{name}/SKILL.md"
            self.write(path, f"# Original synthetic skill {name}\n")
            self.write(path + ".license", "\n".join((checker.AUTHOR, checker.COPYRIGHT, checker.MIT_ID, "Source: " + self.url)) + "\n")
            self.manifest["entries"].append({"path": path, "sidecar": path + ".license"})
        self.write("AUTHORSHIP.md", f"作者：milklong\n项目：{self.url}\nAI辅助编辑\n")
        self.write("LICENSE", MIT)
        self.save()

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def save(self):
        self.write("ATTRIBUTION.json", json.dumps(self.manifest, ensure_ascii=False))

    def failed(self, code):
        report = checker.check(self.root)
        self.assertFalse(report["pass"], report)
        self.assertIn(code, [entry["code"] for entry in report["errors"]], report)
        return report

    def link(self, link, dest, directory=False):
        try:
            link.symlink_to(dest, target_is_directory=directory)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"OS does not permit synthetic symlink creation: {exc}")

    def junction(self, link, dest):
        if os.name != "nt":
            self.skipTest("Windows junction regression; ordinary symlinks cover other systems")
        # A junction can be created without the symbolic-link privilege. This
        # OS-builtin creates only a link between two synthetic test directories.
        command = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(dest)], capture_output=True)
        if command.returncode:
            self.skipTest(f"OS cannot create synthetic junction: returncode {command.returncode}")

    def test_valid_cli_json_and_read_only_with_existing_upstream_copyright(self):
        def snapshot():
            return {p.relative_to(self.root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.rglob("*") if p.is_file()}
        before = snapshot()
        process = subprocess.run([sys.executable, "-B", str(Path(checker.__file__)), "--root", str(self.root)], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertTrue(json.loads(process.stdout)["pass"])
        self.assertEqual(snapshot(), before)
        self.assertIn("Original Upstream Contributors", (self.root / "LICENSE").read_text("utf-8"))

    def test_source_content_can_change_without_hash_freeze(self):
        self.write("skills/alpha/SKILL.md", "Completely revised synthetic engineering-independent content\n")
        self.assertTrue(checker.check(self.root)["pass"])

    def test_deleted_sidecar_fails_cli_with_json(self):
        (self.root / self.manifest["entries"][0]["sidecar"]).unlink()
        env = os.environ.copy()
        env.pop("PYTHONUTF8", None)
        env.pop("PYTHONIOENCODING", None)
        process = subprocess.run([sys.executable, "-B", str(Path(checker.__file__)), "--root", str(self.root)], capture_output=True, text=True, encoding="utf-8", env=env)
        self.assertNotEqual(process.returncode, 0)
        self.assertFalse(json.loads(process.stdout)["pass"])
        self.assertTrue(process.stdout.isascii())

    def test_non_ascii_error_path_survives_cli_without_utf8_environment(self):
        sidecar = self.manifest["entries"][1]["sidecar"]
        (self.root / sidecar).unlink()
        env = os.environ.copy()
        env.pop("PYTHONUTF8", None)
        env.pop("PYTHONIOENCODING", None)
        process = subprocess.run([sys.executable, "-B", str(Path(checker.__file__)), "--root", str(self.root)], capture_output=True, text=True, encoding="utf-8", env=env)
        self.assertNotEqual(process.returncode, 0)
        self.assertTrue(process.stdout.isascii())
        report = json.loads(process.stdout)
        self.assertFalse(report["pass"])
        self.assertIn(sidecar, [error["path"] for error in report["errors"]])

    def test_wrong_sidecar_author(self):
        path = self.manifest["entries"][0]["sidecar"]
        self.write(path, (self.root / path).read_text("utf-8").replace("作者：milklong", "作者：another"))
        self.failed("sidecar_line")

    def test_sidecar_requires_exact_lines_not_substrings(self):
        path = self.manifest["entries"][0]["sidecar"]
        self.write(path, (self.root / path).read_text("utf-8").replace(checker.AUTHOR, checker.AUTHOR + "-renamed"))
        self.failed("sidecar_line")

    def test_sidecar_requires_copyright_mit_and_project_source(self):
        path = self.manifest["entries"][0]["sidecar"]
        original = (self.root / path).read_text("utf-8")
        for line in (checker.COPYRIGHT, checker.MIT_ID, "Source: " + self.url):
            with self.subTest(line=line):
                self.write(path, original.replace(line, "ALTERED NOTICE"))
                self.failed("sidecar_line")

    def test_missing_direct_child_skill_coverage(self):
        self.manifest["entries"].pop()
        self.save()
        self.failed("uncovered_skill")

    def test_empty_entries(self):
        self.manifest["entries"] = []
        self.save()
        self.failed("entries")

    def test_unsafe_source_paths(self):
        for path in ("../outside", "/absolute", "C:/outside", "C:relative", "skills/../LICENSE", "skills\\alpha\\SKILL.md", "skills//alpha/SKILL.md", "skills/alpha/SKILL.md:ads", "NUL", "skills/alpha/."):
            with self.subTest(path=path):
                self.manifest["entries"][0]["path"] = path
                self.save()
                self.failed("unsafe_path")

    def test_unsafe_sidecar_paths(self):
        for path in ("../outside.license", "/absolute.license", "C:/outside.license", "skills/alpha/../../outside.license"):
            with self.subTest(path=path):
                self.manifest["entries"][0]["sidecar"] = path
                self.save()
                self.failed("unsafe_path")

    def test_skill_root_and_policy_and_license_paths_are_also_safe(self):
        for field, value in (("skill_root", "../skills"), ("policy_files", ["../policy"]), ("license_files", ["C:/LICENSE"])):
            with self.subTest(field=field):
                old = self.manifest[field]
                self.manifest[field] = value
                self.save()
                self.failed("unsafe_path")
                self.manifest[field] = old

    def test_sidecar_name_must_correspond_exactly(self):
        self.write("wrong.license", (self.root / self.manifest["entries"][0]["sidecar"]).read_text("utf-8"))
        self.manifest["entries"][0]["sidecar"] = "wrong.license"
        self.save()
        self.failed("sidecar_name")

    def test_duplicate_entries_and_cross_role_paths(self):
        self.manifest["entries"].append(dict(self.manifest["entries"][0]))
        self.save()
        self.failed("duplicate_path")
        self.manifest["entries"].pop()
        self.manifest["license_files"].append("AUTHORSHIP.md")
        self.save()
        self.failed("duplicate_path")

    def test_license_deleted(self):
        (self.root / "LICENSE").unlink()
        self.failed("missing_or_unreadable_path")

    def test_mit_conditions_must_not_be_removed(self):
        self.write("LICENSE", MIT.replace("The above copyright notice and this permission notice", "Notice omitted"))
        self.failed("license_content")

    def test_policy_deleted(self):
        (self.root / "AUTHORSHIP.md").unlink()
        self.failed("missing_or_unreadable_path")

    def test_policy_and_license_arrays_cannot_be_cleared(self):
        for field in ("policy_files", "license_files"):
            with self.subTest(field=field):
                original = self.manifest[field]
                self.manifest[field] = []
                self.save()
                self.failed("manifest_array")
                self.manifest[field] = original

    def test_policy_requires_author_url_and_ai_note(self):
        for fragment in (checker.AUTHOR, self.url, "AI辅助编辑"):
            with self.subTest(fragment=fragment):
                self.write("AUTHORSHIP.md", f"{checker.AUTHOR}\n{self.url}\nAI辅助编辑\n".replace(fragment, "REMOVED"))
                self.failed("policy_content")

    def test_missing_source_file(self):
        (self.root / self.manifest["entries"][0]["path"]).unlink()
        self.failed("missing_or_unreadable_path")

    def test_invalid_manifest_and_duplicate_json_key(self):
        for raw in ("{", "[]", '{"schema":"one","schema":"two"}'):
            with self.subTest(raw=raw):
                self.write("ATTRIBUTION.json", raw)
                self.failed("invalid_manifest")

    def test_wrong_manifest_author_or_url_or_schema(self):
        for field, value, code in (("author", "someone", "author"), ("project_url", "https://github.com/attacker/repo", "project_url"), ("schema", "unknown", "schema")):
            with self.subTest(field=field):
                old = self.manifest[field]
                self.manifest[field] = value
                self.save()
                self.failed(code)
                self.manifest[field] = old

    def test_source_symlink_outside_root_rejected(self):
        outside = self.base / "outside.md"
        outside.write_text("not a repository file", encoding="utf-8")
        path = self.root / self.manifest["entries"][0]["path"]
        path.unlink()
        self.link(path, outside)
        self.failed("symlink")

    def test_sidecar_symlink_inside_root_rejected(self):
        path = self.root / self.manifest["entries"][0]["sidecar"]
        original = path.read_text("utf-8")
        path.unlink()
        self.write("other-notice", original)
        self.link(path, self.root / "other-notice")
        self.failed("symlink")

    def test_direct_skill_directory_symlink_rejected_even_without_entry(self):
        outside = self.base / "outside-skill"
        outside.mkdir()
        (outside / "SKILL.md").write_text("synthetic", encoding="utf-8")
        self.link(self.root / "skills" / "linked", outside, directory=True)
        self.failed("symlink")

    def test_symlinked_manifest_rejected(self):
        manifest_path = self.root / "ATTRIBUTION.json"
        outside = self.base / "manifest.json"
        outside.write_bytes(manifest_path.read_bytes())
        manifest_path.unlink()
        self.link(manifest_path, outside)
        self.failed("symlink")

    def test_symlinked_root_rejected(self):
        alias = self.base / "alias"
        self.link(alias, self.root, directory=True)
        report = checker.check(alias)
        self.assertFalse(report["pass"])
        self.assertIn("symlink", [entry["code"] for entry in report["errors"]])

    def test_junction_in_source_parent_cannot_escape(self):
        outside = self.base / "outside-source-parent"
        outside.mkdir()
        (outside / "source.md").write_text("synthetic outside repository", encoding="utf-8")
        self.junction(self.root / "linked-source", outside)
        self.manifest["entries"][0] = {"path": "linked-source/source.md", "sidecar": "linked-source/source.md.license"}
        self.save()
        self.failed("symlink")

    def test_junction_in_sidecar_and_policy_parents_cannot_escape(self):
        outside = self.base / "outside-notice-parent"
        outside.mkdir()
        self.junction(self.root / "linked-notices", outside)
        self.manifest["entries"][0]["sidecar"] = "linked-notices/notice.license"
        self.manifest["policy_files"] = ["linked-notices/policy.md"]
        self.save()
        report = self.failed("symlink")
        blocked = {entry["path"] for entry in report["errors"] if entry["code"] == "symlink"}
        self.assertIn("linked-notices/notice.license", blocked)
        self.assertIn("linked-notices/policy.md", blocked)

    def test_junction_direct_child_skill_is_not_silently_omitted(self):
        outside = self.base / "outside-junction-skill"
        outside.mkdir()
        (outside / "SKILL.md").write_text("synthetic", encoding="utf-8")
        self.junction(self.root / "skills" / "linked", outside)
        self.failed("symlink")

    def test_junction_root_cannot_alias_repository(self):
        alias = self.base / "junction-alias"
        self.junction(alias, self.root)
        report = checker.check(alias)
        self.assertFalse(report["pass"])
        self.assertIn("symlink", [entry["code"] for entry in report["errors"]])


if __name__ == "__main__":
    unittest.main()
