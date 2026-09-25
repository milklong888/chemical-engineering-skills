"""Read-only publication identity and routing checks; no engineering software.

These tests check the declared publication surface, not legal compliance or
engineering acceptance. Dependency bytes retain their original licenses.
"""
from __future__ import annotations

import ast
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins/chemical-engineering-skills/skills"
ARCHIVE = ROOT / "docs/archive"
LICENSE_DOC = ROOT / "docs/第三方依赖许可清单.md"
NOTICE_PREFIXES = ("LICENSE", "LICENCE", "COPYING", "NOTICE", "COPYRIGHT")
EXPECTED_TOOLS = {
    "knowledge_search", "equipment_calculate", "equipment_batch",
    "product_describe", "pressure_calculate", "process_feedback",
    "process_replay_audit", "aspen_solve_route", "workflow_lookup",
    "design_stage_check",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def portable_path(value: str) -> PurePosixPath:
    if (not isinstance(value, str) or not value or "\\" in value or ":" in value
            or any(part in {"", ".", ".."} for part in value.split("/"))):
        raise ValueError("Expected an exact portable relative path")
    result = PurePosixPath(value)
    if result.is_absolute():
        raise ValueError("Absolute publication path is invalid")
    return result


def read_wheel_evidence(path: Path) -> dict:
    with zipfile.ZipFile(path) as wheel:
        metadata = [name for name in wheel.namelist()
                    if name.endswith(".dist-info/METADATA")]
        if len(metadata) != 1:
            raise ValueError("Expected one distribution METADATA: " + path.name)
        raw = wheel.read(metadata[0])
        message = BytesParser().parsebytes(raw)
        notices = []
        for name in sorted(wheel.namelist()):
            if (not name.endswith("/") and
                    PurePosixPath(name).name.upper().startswith(NOTICE_PREFIXES)):
                notices.append({"path": name, "sha256": sha256(wheel.read(name))})
        return {
            "wheel": path.relative_to(ROOT).as_posix(),
            "sha256": sha256(path.read_bytes()),
            "name": message.get("Name"), "version": message.get("Version"),
            "metadata_path": metadata[0], "metadata_sha256": sha256(raw),
            "license_expression": message.get("License-Expression"),
            "license": message.get("License"),
            "license_files_declared": message.get_all("License-File", []),
            "license_classifiers": [item for item in message.get_all("Classifier", [])
                                    if item.startswith("License ::")],
            "notice_files": notices,
        }


class PublicationContractTests(unittest.TestCase):
    def test_root_mit_license_and_third_party_notice_are_present(self):
        license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("MIT License", license_text)
        self.assertIn("Permission is hereby granted, free of charge", license_text)
        self.assertIn("THE SOFTWARE IS PROVIDED", license_text)
        notice = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
        self.assertTrue(notice.strip(), "Third-party scope cannot be an empty stub")
        self.assertIn("vendor/aspen-mcp-toolkit", notice)
        self.assertIn("第三方依赖许可清单.md", notice)

    def test_all_71_wheels_match_observed_metadata_and_license_files(self):
        text = LICENSE_DOC.read_text(encoding="utf-8")
        match = re.search(
            r"<!-- WHEEL_LICENSE_AUDIT_BEGIN -->\s*```json\s*(\{.*?\})\s*```"
            r"\s*<!-- WHEEL_LICENSE_AUDIT_END -->", text, re.S)
        self.assertIsNotNone(match, "Machine-readable source identity block is missing")
        declared = json.loads(match.group(1))
        self.assertEqual(declared["schema"], "bundled-wheel-license-audit-v1")
        self.assertEqual(declared["scope"],
                         "third_party_dependency_metadata_and_file_identity_not_relicense")
        wheels = sorted((ROOT / "runtime/wheelhouse").rglob("*.whl"))
        self.assertEqual(len(wheels), 71)
        actual = [read_wheel_evidence(path) for path in wheels]
        self.assertEqual(declared["wheel_count"], len(actual))
        self.assertEqual(declared["wheels"], actual)
        self.assertEqual([row["name"] for row in actual if not row["notice_files"]],
                         ["fastmcp-slim"])
        binary = json.loads((ROOT / "BINARY_ASSETS.json").read_text(encoding="utf-8"))
        binary_wheels = {row["path"]: row["sha256"].lower()
                         for row in binary["assets"] if row["kind"] == "python_wheel"}
        self.assertEqual({row["wheel"]: row["sha256"] for row in actual}, binary_wheels)

    def test_fastmcp_slim_external_license_is_same_package_and_fixed_source(self):
        folder = ROOT / "vendor/aspen-mcp-toolkit/third_party/fastmcp-slim"
        evidence = json.loads((folder / "PROVENANCE.json").read_text(encoding="utf-8"))
        self.assertEqual(evidence["package"], "fastmcp-slim")
        self.assertEqual(evidence["version"], "3.4.2")
        self.assertEqual(evidence["license_expression_in_fixed_source"], "Apache-2.0")
        self.assertRegex(evidence["commit_sha"], r"^[0-9a-f]{40}$")
        self.assertFalse(evidence["wheel_modified"])
        self.assertIn("Apache License", (folder / "LICENSE").read_text(encoding="utf-8"))
        for row in evidence["files"]:
            with self.subTest(file=row["path"]):
                path = folder.joinpath(*portable_path(row["path"]).parts)
                data = path.read_bytes()
                self.assertEqual(sha256(data), row["sha256"].lower())
                self.assertEqual(len(data), row["bytes"])
        wheel = ROOT / "runtime/wheelhouse/fastmcp_slim-3.4.2-py3-none-any.whl"
        self.assertEqual(sha256(wheel.read_bytes()), evidence["wheel_sha256"].lower())

    def test_archive_manifest_preserves_each_historical_file_identity(self):
        self.assertTrue((ARCHIVE / "README.md").is_file())
        document = json.loads((ARCHIVE / "archive_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(document["schema"], "documentation-archive-v1")
        self.assertRegex(document["baseline_commit"], r"^[0-9a-fA-F]{40}$")
        self.assertIsInstance(document["entries"], list)
        self.assertTrue(document["entries"], "Archive must identify the preserved files")
        original_paths, archived_paths = set(), set()
        for row in document["entries"]:
            with self.subTest(path=row.get("archived_path")):
                original = portable_path(row["original_path"])
                archived = portable_path(row["archived_path"])
                self.assertNotIn(str(original).casefold(), original_paths)
                self.assertNotIn(str(archived).casefold(), archived_paths)
                original_paths.add(str(original).casefold())
                archived_paths.add(str(archived).casefold())
                self.assertEqual(archived.parts[:2], ("docs", "archive"))
                self.assertEqual(row["status"], "historical")
                self.assertRegex(row["sha256"], r"^[0-9a-fA-F]{64}$")
                path = ROOT.joinpath(*archived.parts)
                self.assertTrue(path.resolve().is_relative_to(ARCHIVE.resolve()))
                self.assertTrue(path.is_file())
                self.assertFalse(path.is_symlink())
                self.assertEqual(sha256(path.read_bytes()), row["sha256"].lower())
        actual = {p.relative_to(ROOT).as_posix().casefold() for p in ARCHIVE.rglob("*")
                  if p.is_file() and p.name not in {"README.md", "archive_manifest.json"}}
        self.assertEqual(actual, archived_paths, "Every historical file needs an identity row")

    def test_archive_is_not_a_skill_entry_or_default_knowledge_record(self):
        plugin = json.loads((ROOT / "plugins/chemical-engineering-skills/.codex-plugin/plugin.json")
                            .read_text(encoding="utf-8"))
        self.assertEqual(plugin["skills"], "./skills/")
        entries = list(SKILLS.rglob("SKILL.md"))
        self.assertEqual(len(entries), 19)
        for path in entries:
            self.assertEqual(len(path.relative_to(SKILLS).parts), 2,
                             "Nested backup/archived Skill entry can be rediscovered")
            self.assertFalse(path.resolve().is_relative_to(ARCHIVE.resolve()))
        for line in (ROOT / "knowledge/records.jsonl").read_text(encoding="utf-8").splitlines():
            if not line:
                continue
            row = json.loads(line)
            for field in ("public_path", "path"):
                value = row.get(field)
                if isinstance(value, str):
                    parts = {part.casefold() for part in PurePosixPath(value.replace("\\", "/")).parts}
                    self.assertFalse(parts & {"archive", "archives"}, (row.get("node_id"), value))

    def test_expert_mcp_retains_ten_tools_and_workflow_lookup(self):
        tree = ast.parse((ROOT / "tools/expert_mcp.py").read_text(encoding="utf-8"))
        tools = {}
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            decorated = any(isinstance(decorator, ast.Call)
                            and isinstance(decorator.func, ast.Attribute)
                            and isinstance(decorator.func.value, ast.Name)
                            and decorator.func.value.id == "mcp"
                            and decorator.func.attr == "tool"
                            for decorator in node.decorator_list)
            if decorated:
                tools[node.name] = node
        self.assertEqual(set(tools), EXPECTED_TOOLS)
        workflow = tools["workflow_lookup"]
        calls = [node for node in ast.walk(workflow) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Name) and node.func.id == "execute"]
        self.assertEqual(len(calls), 1)
        request = calls[0].args[0]
        self.assertIsInstance(request, ast.Dict)
        fields = {key.value: value for key, value in zip(request.keys, request.values)
                  if isinstance(key, ast.Constant)}
        self.assertIsInstance(fields["operation"], ast.Constant)
        self.assertEqual(fields["operation"].value, "workflow")
        self.assertIsInstance(fields["payload"], ast.Name)
        self.assertEqual(fields["payload"].id, "payload")


if __name__ == "__main__":
    unittest.main(verbosity=2)
