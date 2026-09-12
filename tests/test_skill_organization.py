"""Dependency, caller and filesystem-boundary tests; no Aspen/agent evaluation."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT))
from tools import skill_organization as organization

PREFIX = organization.SKILLS_PREFIX


class OrganizationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="synthetic-organization-")
        self.root = Path(self.temporary.name)
        self.alpha = PREFIX + "alpha/"
        self.beta = PREFIX + "beta/"
        self.put(self.alpha + "SKILL.md", "---\nname: alpha\n---\n[method](references/method.md)\n")
        self.put(self.alpha + "references/method.md", "[worker](../scripts/worker.py)\n")
        self.put(self.alpha + "scripts/worker.py", "from tools import shared\n")
        self.put(self.beta + "SKILL.md", "---\nname: beta\n---\nIndependent synthetic Skill.\n")
        self.put("tools/shared.py", "from tools import leaf\n")
        self.put("tools/leaf.py", "VALUE = 1\n")

    def tearDown(self):
        self.temporary.cleanup()

    def put(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")
        return path

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.root.rglob("*") if p.is_file()}

    def test_transitive_import_and_markdown_propagation_excludes_unrelated_skill(self):
        result = organization.impact(self.root, ["tools/leaf.py"])
        self.assertEqual(result["related_skills"], ["alpha"])
        self.assertIn("tools/shared.py", result["affected_files"])
        self.assertIn(self.alpha + "SKILL.md", result["affected_files"])
        self.assertNotIn(self.beta + "SKILL.md", result["affected_files"])
        self.assertEqual({e["type"] for e in result["propagation_witnesses"]},
                         {"markdown_link", "python_import"})
        self.assertFalse(result["complete_dependency_graph"])
        self.assertFalse(result["execution_proven"])

    def test_cycles_terminate_without_duplicate_affected_files(self):
        self.put("tools/leaf.py", "from tools import shared\n")
        result = organization.impact(self.root, ["tools/shared.py"])
        self.assertIn("tools/leaf.py", result["affected_files"])
        self.assertEqual(len(result["affected_files"]), len(set(result["affected_files"])))

    def test_literal_missing_reference_supports_deleted_file_impact(self):
        self.put(self.alpha + "references/method.md", "[missing](../../../../../docs/gone.md)\n")
        result = organization.impact(self.root, ["docs/gone.md"])
        self.assertEqual(result["changed_missing"], ["docs/gone.md"])
        self.assertIn("alpha", result["related_skills"])
        self.assertTrue(any(e["target"] == "docs/gone.md" and e["status"] == "missing"
                            for e in result["unresolved_edges"]))

    def test_relative_import_and_file_anchored_read_are_distinct_edges(self):
        self.put("tools/shared.py", "from pathlib import Path\nfrom . import leaf\nROOT = Path(__file__).resolve().parents[1]\nDATA = ROOT / 'docs/data.json'\ndef read():\n    return DATA.read_text()\n")
        self.put("docs/data.json", '{"synthetic":true}')
        result = organization.impact(self.root, ["docs/data.json"])
        self.assertIn("tools/shared.py", result["affected_files"])
        self.assertIn("alpha", result["related_skills"])
        self.assertTrue(any(e["type"] == "python_file_reference" and e["target"] == "docs/data.json"
                            for e in result["edges"]))
        self.assertTrue(any(e["type"] == "python_import" and e["target"] == "tools/leaf.py"
                            for e in result["edges"]))

    def test_dynamic_cwd_import_and_parse_failures_remain_visible(self):
        self.put("tools/shared.py", "from nowhere import missing\nimport importlib\ndef read(path):\n    importlib.import_module(path)\n    return open(path).read()\n")
        self.put("tools/broken.py", "this is not valid python !\n")
        result = organization.inventory(self.root)
        reasons = {edge["reason"] for edge in result["unresolved_edges"]}
        self.assertIn("external_or_unresolved_import", reasons)
        self.assertIn("dynamic_import_not_resolved", reasons)
        self.assertIn("dynamic_path_or_runtime_cwd_required", reasons)
        self.assertTrue(any(issue["code"] == "python_parse_failed" for issue in result["issues"]))

    def test_ambiguous_import_does_not_guess_runtime_sys_path(self):
        self.put("tools/shared.py", "import helper\n")
        self.put("helper.py", "X=1\n")
        self.put("tools/helper.py", "X=2\n")
        result = organization.inventory(self.root)
        edge = next(e for e in result["edges"] if e["source"] == "tools/shared.py")
        self.assertIsNone(edge["target"])
        self.assertEqual(edge["reason"], "ambiguous_local_import")
        self.assertIn("tools/helper.py", edge["candidate_targets"])
        impact = organization.impact(self.root, ["helper.py"])
        self.assertNotIn("tools/shared.py", impact["affected_files"])
        self.assertTrue(impact["possible_consumers_from_unresolved_edges"])

    def test_package_initializers_are_possible_import_consumers(self):
        self.put("tools/__init__.py", "# synthetic package initialization\n")
        result = organization.impact(self.root, ["tools/__init__.py"])
        self.assertIn("alpha", result["related_skills"])
        self.assertTrue(any(edge["type"] == "python_package_init" for edge in result["direct_consumers"]))

    def test_deleted_submodule_is_not_hidden_by_existing_initializer(self):
        self.put("tools/__init__.py", "# no leaf export\n")
        (self.root / "tools/leaf.py").unlink()
        result = organization.impact(self.root, ["tools/leaf.py"])
        possible = [edge for edge in result["possible_consumers_from_unresolved_edges"]
                    if edge["source"] == "tools/shared.py"]
        self.assertTrue(possible)
        self.assertTrue(any(edge["type"] == "python_import_member"
                            and edge["reason"] == "exported_attribute_or_missing_submodule_unresolved"
                            and edge["target"] is None for edge in possible))
        self.assertEqual(result["changed_missing"], ["tools/leaf.py"])

    def test_each_import_member_retains_its_own_unresolved_candidates(self):
        self.put("tools/__init__.py", "# attributes are not statically inferred\n")
        self.put("tools/shared.py", "from tools import leaf, missing\n")
        result = organization.impact(self.root, ["tools/missing.py"])
        self.assertTrue(any(edge["source"] == "tools/shared.py"
                            and "tools/missing.py" in edge["candidate_targets"]
                            for edge in result["possible_consumers_from_unresolved_edges"]))
        self.assertTrue(any(edge["source"] == "tools/shared.py" and edge["target"] == "tools/leaf.py"
                            for edge in result["edges"]))

    def test_rebound_path_read_does_not_use_future_assignment_as_resolved(self):
        self.put("tools/shared.py", "from pathlib import Path\nROOT=Path(__file__).parent/'a'\n(ROOT/'x.json').read_text()\nROOT=Path(__file__).parent/'b'\n")
        self.put("tools/a/x.json", "{}")
        self.put("tools/b/x.json", "{}")
        for changed in ("tools/a/x.json", "tools/b/x.json"):
            with self.subTest(changed=changed):
                result = organization.impact(self.root, [changed])
                reads = [edge for edge in result["edges"] if edge["source"] == "tools/shared.py"
                         and edge["line"] == 3 and edge["type"] == "python_file_reference"]
                self.assertEqual(len(reads), 1)
                self.assertIsNone(reads[0]["target"])
                self.assertEqual(reads[0]["reason"], "rebound_path_or_dependent_alias")
                self.assertEqual(reads[0]["candidate_targets"], ["tools/a/x.json", "tools/b/x.json"])
                self.assertNotIn("tools/shared.py", result["affected_files"])
                self.assertTrue(result["possible_consumers_from_unresolved_edges"])

    def test_alias_of_rebound_path_stays_unresolved(self):
        self.put("tools/shared.py", "from pathlib import Path\nROOT=Path(__file__).parent/'a'\nROOT=Path(__file__).parent/'b'\nDATA=ROOT/'x.json'\nDATA.read_text()\n")
        result = organization.impact(self.root, ["tools/a/x.json"])
        read = next(edge for edge in result["edges"] if edge["source"] == "tools/shared.py"
                    and edge["type"] == "python_file_reference" and edge["line"] == 5)
        self.assertIsNone(read["target"])
        self.assertEqual(read["reason"], "rebound_path_or_dependent_alias")
        self.assertIn("tools/a/x.json", read["candidate_targets"])
        self.assertTrue(result["possible_consumers_from_unresolved_edges"])

    def test_function_shadow_does_not_borrow_global_path_identity(self):
        self.put("tools/shared.py", "from pathlib import Path\nROOT=Path(__file__).resolve().parents[1]\ndef read(ROOT):\n    return (ROOT/'docs/data.json').read_text()\n")
        self.put("docs/data.json", "{}")
        result = organization.impact(self.root, ["docs/data.json"])
        self.assertNotIn("tools/shared.py", result["affected_files"])
        self.assertTrue(any(e["source"] == "tools/shared.py" and e["reason"] == "dynamic_path_or_runtime_cwd_required"
                            for e in result["unresolved_edges"]))

    def test_markdown_reference_code_path_fragment_and_fenced_example(self):
        self.put(self.alpha + "references/method.md", "[reference][m]\n[m]: ../scripts/worker.py#part\n`../scripts/worker.py`\n```text\n[ignored](fake.md)\n```\n")
        result = organization.inventory(self.root)
        kinds = {e["type"] for e in result["edges"] if e["source"] == self.alpha + "references/method.md"}
        self.assertEqual(kinds, {"markdown_reference_definition", "markdown_code_path"})
        self.assertFalse(any(e["reference"] == "fake.md" for e in result["edges"]))

    def test_prose_code_paths_expose_root_convention_and_ambiguity(self):
        self.put(self.alpha + "references/method.md", "`tools/shared.py`\n")
        result = organization.impact(self.root, ["tools/shared.py"])
        edge = next(e for e in result["direct_consumers"] if e["type"] == "markdown_code_path")
        self.assertEqual(edge["reason"], "static_code_path_candidate")
        self.put(self.alpha + "references/tools/shared.py", "# different local path\n")
        result = organization.inventory(self.root)
        edge = next(e for e in result["edges"] if e["source"] == self.alpha + "references/method.md")
        self.assertIsNone(edge["target"])
        self.assertEqual(edge["reason"], "ambiguous_code_path")

    def test_uppercase_markdown_suffix_is_parsed_as_markdown(self):
        upper = self.alpha + "references/UPPER.MD"
        self.put(upper, "[script](../scripts/worker.py)\n")
        result = organization.impact(self.root, [self.alpha + "scripts/worker.py"])
        self.assertIn(upper, result["affected_files"])
        self.assertTrue(any(edge["source"] == upper and edge["type"] == "markdown_link"
                            for edge in result["edges"]))
        self.assertFalse(any(issue["source"] == upper for issue in result["issues"]))

    def test_inventory_and_impact_do_not_write_or_execute_scanned_code(self):
        self.put("tools/leaf.py", "raise RuntimeError('MUST NEVER EXECUTE')\n")
        before = self.snapshot()
        organization.inventory(self.root)
        organization.impact(self.root, ["tools/leaf.py"])
        self.assertEqual(before, self.snapshot())

    def test_changed_path_boundary_and_excluded_tree(self):
        for path in ["../outside.py", "/absolute.py", "C:/outside.py", "tools\\leaf.py",
                     "tools/../leaf.py", "tools/leaf.py:stream", "NUL.py", ".git/config",
                     "tools/a?.py", "tools/a\x00.py", "tools/", "tools"]:
            with self.subTest(path=repr(path)), self.assertRaises(organization.ReleaseError):
                organization.impact(self.root, [path])
        with self.assertRaises(organization.ReleaseError):
            organization.impact(self.root, [])

    def test_unsafe_markdown_is_reported_without_reading_outside(self):
        self.put(self.alpha + "SKILL.md", "---\nname: alpha\n---\n[outside](../../../../../../../../outside.md)\n[encoded](%2e%2e/%2e%2e/%2e%2e/%2e%2e/%2e%2e/%2e%2e/%2e%2e/outside.md)\n")
        result = organization.inventory(self.root)
        self.assertEqual(sum(e["reason"] == "unsafe_reference_rejected" for e in result["edges"]), 2)

    def test_link_rejection_is_enforced_even_for_excluded_names(self):
        path = self.root / ".git"
        path.mkdir()
        original = Path.lstat
        with mock.patch.object(Path, "lstat", lambda candidate: mock.Mock(st_mode=stat.S_IFLNK, st_file_attributes=0) if candidate == path else original(candidate)):
            with self.assertRaises(organization.ReleaseError):
                organization.inventory(self.root)

    def test_root_symlink_is_rejected_before_inventory(self):
        original = Path.is_symlink
        with mock.patch.object(Path, "is_symlink", lambda candidate: candidate == self.root or original(candidate)):
            with self.assertRaises(organization.ReleaseError):
                organization.inventory(self.root)

    def test_source_limits_remain_visible_and_do_not_imply_complete_coverage(self):
        self.put("tools/large.py", "#" * 1025)
        with mock.patch.object(organization, "MAX_FILE_BYTES", 1024):
            result = organization.inventory(self.root)
        self.assertTrue(any(issue == {"source": "tools/large.py", "code": "text_size_limit_not_parsed"}
                            for issue in result["issues"]))
        self.assertFalse(result["complete_dependency_graph"])

    def test_runtime_only_or_empty_product_root_is_an_error_not_zero_skills(self):
        runtime = self.root / "runtime-only"
        runtime.mkdir()
        with self.assertRaisesRegex(organization.ReleaseError, "product skills directory"):
            organization.inventory(runtime)
        (runtime / PREFIX).mkdir(parents=True)
        with self.assertRaisesRegex(organization.ReleaseError, "No Skill entries"):
            organization.inventory(runtime)

    def test_real_file_symlink_is_rejected(self):
        link = self.root / "tools/linked.py"
        try:
            link.symlink_to(self.root / "tools/leaf.py")
        except (OSError, NotImplementedError):
            self.skipTest("Host does not permit symlink creation; rejection branch tested with mock")
        with self.assertRaises(organization.ReleaseError):
            organization.inventory(self.root)
        with self.assertRaises(organization.ReleaseError):
            organization.impact(self.root, ["tools/linked.py"])

    def test_cli_json_from_unrelated_cwd_without_seal_is_read_only(self):
        before = self.snapshot()
        result = subprocess.run([sys.executable, "-B", "-X", "utf8",
                                 str(SOURCE_ROOT / "tools/skill_organization.py"), "impact",
                                 "--root", str(self.root), "--changed", "tools/leaf.py"],
                                cwd=self.temporary.name, capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["related_skills"], ["alpha"])
        self.assertEqual(before, self.snapshot())
        failed = subprocess.run([sys.executable, "-B", str(SOURCE_ROOT / "tools/skill_organization.py"),
                                 "impact", "--root", str(self.root), "--changed", "../outside.py"],
                                capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(failed.returncode, 2)
        self.assertTrue(json.loads(failed.stdout)["read_only"])

    def test_actual_product_inventory_covers_existing_nineteen_entries(self):
        result = organization.inventory(SOURCE_ROOT)
        self.assertEqual(result["skill_count"], 19)
        ids = {skill["skill_id"] for skill in result["skills"]}
        self.assertIn("subagent-dispatch", ids)
        self.assertNotIn("nylon-thigh-high-photo-edit", ids)
        self.assertFalse(any(issue["code"] == "skill_name_missing_or_mismatched" for issue in result["issues"]))
        self.assertTrue(all(not Path(node["path"]).is_absolute() for node in result["files"]))


if __name__ == "__main__":
    unittest.main()
