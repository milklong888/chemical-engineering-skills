#!/usr/bin/env python3
"""Isolated synthetic publication/install regressions; no installed skills or COM."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

sys.dont_write_bytecode = True
import install as installer
import verify_release as verifier

TOOLS = Path(__file__).resolve().parent


def write(path: Path, data: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data.encode("utf-8") if isinstance(data, str) else data)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        # Prefer the checkout parent; never test against real discovered skill roots.
        self.temporary = tempfile.TemporaryDirectory(prefix=".publication-test-", dir=TOOLS.parents[1])
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.repo = self.base / "release"
        self.workspace = self.base / "目标工程"
        self.skills = self.base / "isolated-skills"
        self.skill_rel = verifier.SKILLS_PREFIX + "example-skill/SKILL.md"
        write(self.repo / self.skill_rel, "---\nname: example-skill\ndescription: Synthetic isolated installation fixture.\n---\nWorkspace: {CHEM_WORKSPACE}\nSkills: {CHEM_SKILLS}\n")
        write(self.repo / verifier.PLUGIN / ".codex-plugin/plugin.json", json.dumps({"name": "chemical-engineering-skills", "version": "0.0.0-test", "description": "Synthetic fixture", "skills": "./skills/"}))
        for name in ("install.py", "verify_release.py", "build_release.py"):
            write(self.repo / "tools" / name, (TOOLS / name).read_bytes())
        write(self.repo / "workspace/config.json", '{"root":"{CHEM_WORKSPACE}","skills":"{CHEM_SKILLS}"}\n')
        self.freeze()

    def freeze(self):
        manifest, sums = verifier.make_manifest(self.repo, release_name="synthetic-release", release_version="0.0.0-test", expected_skill_count=1,
                                                external_dependencies=[{"name": "Commercial simulator", "status": "not_bundled"}])
        write(self.repo / verifier.MANIFEST, manifest)
        write(self.repo / verifier.CHECKSUMS, sums)

    def cli(self, script, *arguments):
        return subprocess.run([sys.executable, "-B", str(self.repo / "tools" / script), *map(str, arguments)], capture_output=True, text=True, encoding="utf-8")

    def builder(self):
        path = TOOLS / "build_release.py"
        if not path.is_file():
            self.fail("The packaged build_release.py is required")
        spec = importlib.util.spec_from_file_location("test_public_builder", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def source_manifest(self, entries):
        path = self.base / "publication_sources.json"
        write(path, json.dumps({"schema": "chemical-publication-sources-v1", "files": entries}))
        return path

    def source(self, name="source.md", destination="workspace/new.md", text="Synthetic source\n"):
        path = self.base / name
        write(path, text)
        return {"source": str(path), "destination": destination, "source_sha256": verifier.sha256(path.read_bytes()), "replacements": []}

    def test_verify_cli_integrity_not_software(self):
        result = self.cli("verify_release.py", "--root", self.repo)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        parsed = json.loads(result.stdout)
        self.assertTrue(parsed["integrity_verified"])
        self.assertFalse(parsed["commercial_software_verified"])
        self.assertFalse(parsed["knowledge_payload_bundled"])

    def test_tamper_refused(self):
        write(self.repo / "workspace/config.json", "{}")
        self.assertEqual(self.cli("verify_release.py", "--root", self.repo).returncode, 2)

    def test_unlisted_file_refused(self):
        write(self.repo / "unexpected.md", "not sealed")
        with self.assertRaises(verifier.ReleaseError):
            verifier.verify(self.repo)

    def test_missing_skill_entrypoint_refused(self):
        (self.repo / self.skill_rel).unlink()
        with self.assertRaises(verifier.ReleaseError):
            self.freeze()

    def test_path_escape_and_windows_alias_refused(self):
        for relative in ("../escape.py", "/escape.py", "C:/escape.py", "dir\\file.py", "dir/./file.py", "CON.txt", "dir/end.\n", "dir/end.", "wild*.md", "name?.md"):
            with self.subTest(relative=relative), self.assertRaises(verifier.ReleaseError):
                verifier.relative_path(relative)

    def test_credentials_and_model_payload_refused(self):
        with self.assertRaises(verifier.ReleaseError):
            verifier.public_text("note.md", ("gh" + "p_" + "x" * 40).encode())
        for name in ("model.bkp", "model.inp", "weights.pth", "book.pdf", "source_pages/page.md", "auth.json", ".git/hooks/hidden.py"):
            with self.subTest(name=name), self.assertRaises(verifier.ReleaseError):
                verifier.public_text(name, b"text disguised as forbidden payload")

    def test_utf8_and_private_path_refused(self):
        for content in (b"\xff", b"\xef\xbb\xbftext", b"a\x00b", "/".join(["C:", "Users", "Example", "private"]).encode()):
            with self.assertRaises(verifier.ReleaseError):
                verifier.public_text("note.md", content)

    def test_dry_run_cli_no_writes(self):
        result = self.cli("install.py", "--workspace-root", self.workspace, "--skills-root", self.skills, "--dry-run")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(self.workspace.exists())
        self.assertFalse(self.skills.exists())

    def test_install_cli_scoped_tokens_and_idempotence(self):
        write(self.workspace / "unowned.md", "Keep {CHEM_WORKSPACE} unchanged")
        args = ("--workspace-root", self.workspace, "--skills-root", self.skills)
        first = self.cli("install.py", *args)
        second = self.cli("install.py", *args)
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual(json.loads(second.stdout)["changed_file_count"], 0)
        config = json.loads((self.workspace / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(config["root"], self.workspace.as_posix())
        self.assertEqual(config["skills"], self.skills.as_posix())
        self.assertEqual((self.workspace / "unowned.md").read_text(), "Keep {CHEM_WORKSPACE} unchanged")
        self.assertFalse((self.workspace / "tools").exists())

    def test_collision_cli_whole_preflight_no_partial_writes(self):
        write(self.workspace / "config.json", "user content")
        result = self.cli("install.py", "--workspace-root", self.workspace, "--skills-root", self.skills)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.skills.exists())
        self.assertEqual((self.workspace / "config.json").read_text(), "user content")

    def test_replace_cli_exact_file_backup(self):
        write(self.workspace / "config.json", "user content")
        write(self.workspace / "unowned.md", "keep")
        result = self.cli("install.py", "--workspace-root", self.workspace, "--skills-root", self.skills, "--replace", "--backup-root", self.base / "backups")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        backup = Path(json.loads(result.stdout)["backup_root"])
        entries = json.loads((backup / "BACKUP_MANIFEST.json").read_text(encoding="utf-8"))["files"]
        self.assertEqual(len(entries), 1)
        self.assertEqual((backup / entries[0]["backup"]).read_text(), "user content")
        self.assertFalse(verifier.below(backup, self.skills))
        self.assertEqual((self.workspace / "unowned.md").read_text(), "keep")

    def test_backup_under_skill_discovery_refused(self):
        write(self.workspace / "config.json", "user content")
        with self.assertRaises(verifier.ReleaseError):
            installer.install(self.repo, self.workspace, self.skills, replace=True, backup_root=self.base / ".agents/skills/backups")
        self.assertFalse(self.skills.exists())

    def test_existing_parent_file_refused_before_writes(self):
        write(self.skills / "example-skill", "not a directory")
        with self.assertRaises(verifier.ReleaseError):
            installer.install(self.repo, self.workspace, self.skills)
        self.assertFalse(self.workspace.exists())

    def test_tampered_release_install_refused(self):
        write(self.repo / "workspace/config.json", "changed")
        with self.assertRaises(verifier.ReleaseError):
            installer.install(self.repo, self.workspace, self.skills)
        self.assertFalse(self.workspace.exists())
        self.assertFalse(self.skills.exists())

    def test_overlapping_roots_refused(self):
        with self.assertRaises(verifier.ReleaseError):
            installer.install(self.repo, self.workspace, self.workspace / "skills")

    def test_builder_stage_source_identity_and_idempotence(self):
        builder = self.builder()
        entry = self.source(text="origin=OLD\n")
        entry["replacements"] = [{"old": "OLD", "new": "{CHEM_WORKSPACE}", "expected_count": 1}]
        source = Path(entry["source"])
        original = source.read_bytes()
        output = self.base / "stage"
        manifest = self.source_manifest([entry])
        first = builder.stage(manifest, output, self.base / "logs")
        second = builder.stage(manifest, output, self.base / "logs")
        self.assertEqual(first["new_file_count"], 1)
        self.assertEqual(second["new_file_count"], 0)
        self.assertEqual(source.read_bytes(), original)
        self.assertIn("{CHEM_WORKSPACE}", (output / "workspace/new.md").read_text())
        self.assertFalse(verifier.below(Path(first["mapping_log"]), output))

    def test_builder_hash_failure_prevents_all_copies(self):
        builder = self.builder()
        good = self.source()
        bad = self.source("bad.md", "workspace/bad.md")
        bad["source_sha256"] = "0" * 64
        output = self.base / "stage"
        with self.assertRaises(ValueError):
            builder.stage(self.source_manifest([good, bad]), output, self.base / "logs")
        self.assertFalse(output.exists())

    def test_builder_replacement_contract_refused(self):
        entry = self.source()
        entry["replacements"] = [{"old": "absent", "new": "replacement", "expected_count": 1}]
        with self.assertRaises(ValueError):
            self.builder().stage(self.source_manifest([entry]), self.base / "stage", self.base / "logs")

    def test_builder_collision_preserves_generated_docs(self):
        output = self.base / "stage"
        write(output / "workspace/new.md", "generated independently")
        with self.assertRaises(ValueError):
            self.builder().stage(self.source_manifest([self.source()]), output, self.base / "logs")
        self.assertEqual((output / "workspace/new.md").read_text(), "generated independently")

    def test_builder_case_collision_and_escape(self):
        builder = self.builder()
        entry = self.source()
        for other_destination in ("workspace/NEW.md", "../escaped.md"):
            other = dict(entry, destination=other_destination)
            with self.subTest(destination=other_destination), self.assertRaises(ValueError):
                builder.stage(self.source_manifest([entry, other]), self.base / "stage", self.base / "logs")

    def test_seal_zip_actual_readback_and_no_overwrite(self):
        builder = self.builder()
        archive_dir = self.base / "archives"
        result = builder.seal(self.repo, archive_dir, "synthetic-release", "0.0.0-test", expected_skill_count=1)
        archive = Path(result["archive"])
        with zipfile.ZipFile(archive) as bundle:
            self.assertIsNone(bundle.testzip())
            self.assertIn("synthetic-release-0.0.0-test/RELEASE_MANIFEST.json", bundle.namelist())
        self.assertEqual(verifier.sha256(archive.read_bytes()), result["sha256"])
        with self.assertRaises(ValueError):
            builder.seal(self.repo, archive_dir, "synthetic-release", "0.0.0-test", expected_skill_count=1)

    def test_seal_rejects_model_before_changing_ledgers(self):
        before = (self.repo / verifier.MANIFEST).read_bytes()
        write(self.repo / "model.bkp", "not public")
        with self.assertRaises(ValueError):
            self.builder().seal(self.repo, self.base / "archives", "synthetic-release", "0.0.0-test", expected_skill_count=1)
        self.assertEqual((self.repo / verifier.MANIFEST).read_bytes(), before)
        self.assertFalse((self.base / "archives").exists())

    def test_explicit_synthetic_inp_allowlist_roundtrip(self):
        builder = self.builder()
        destination = verifier.SKILLS_PREFIX + "example-skill/examples/toy.inp"
        entry = self.source("toy.inp", destination, "; Synthetic empty input template; no process result.\n")
        entry.update(publication_scope="synthetic_template", scope_declaration="Synthetic template; not a project model or accepted process result.")
        sources = self.source_manifest([entry])
        builder.stage(sources, self.repo, self.base / "logs")
        templates = builder.source_synthetic_allowlist(sources)
        builder.seal(self.repo, self.base / "archives", "synthetic-release", "0.0.0-test", expected_skill_count=1, synthetic_templates=templates)
        self.assertTrue(verifier.verify(self.repo)["integrity_verified"])
        installer.install(self.repo, self.workspace, self.skills)
        self.assertEqual((self.skills / "example-skill/examples/toy.inp").read_bytes(), Path(entry["source"]).read_bytes())
        write(self.repo / destination, "; modified outside approved identity")
        with self.assertRaises(verifier.ReleaseError):
            verifier.verify(self.repo)

    def test_synthetic_scope_cannot_allow_bkp_or_missing_declaration(self):
        for path, declaration in (("model.bkp", "Synthetic template; not a project model."), ("toy.inp", "A template")):
            with self.subTest(path=path), self.assertRaises(verifier.ReleaseError):
                verifier.synthetic_policy([{"path": path, "sha256": "0" * 64, "scope_declaration": declaration}])

    def downloaded_release_fixture(self):
        templates = []
        for name in ("toy_pass_after_run", "toy_fail_after_run", "design_spec_patterns", "empty_column_vrc_template"):
            relative = verifier.SKILLS_PREFIX + "example-skill/templates/" + name + ".inp"
            data = ("; Synthetic non-project template: " + name + "\n").encode("utf-8")
            write(self.repo / relative, data)
            templates.append({"path": relative, "sha256": verifier.sha256(data), "scope_declaration": "Synthetic template; not a project model or accepted process result."})
        dependencies = [{"name": "Commercial simulator", "status": "not_bundled"}, {"name": "Licensed knowledge payload", "status": "optional_external"}]
        manifest, sums = verifier.make_manifest(self.repo, release_name="synthetic-release", release_version="0.0.0-test", expected_skill_count=1,
                                                external_dependencies=dependencies, synthetic_templates=templates)
        write(self.repo / verifier.MANIFEST, manifest)
        write(self.repo / verifier.CHECKSUMS, sums)
        return dependencies, templates

    def reseal_cli(self):
        return self.cli("build_release.py", "seal", "--output-dir", self.base / "rebuilt", "--release-name", "synthetic-release", "--release-version", "0.0.1-test", "--expected-skill-count", "1")

    def test_downloaded_release_reseal_cli_without_private_sources(self):
        dependencies, templates = self.downloaded_release_fixture()
        self.assertFalse((self.base / "publication_sources.json").exists())
        result = self.reseal_cli()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        rebuilt = verifier.verify(self.repo)["manifest"]
        self.assertEqual(rebuilt["external_dependencies"], dependencies)
        self.assertEqual(rebuilt["synthetic_templates"], templates)
        archive = Path(json.loads(result.stdout)["archive"])
        with zipfile.ZipFile(archive) as bundle:
            self.assertEqual(sum(name.endswith(".inp") for name in bundle.namelist()), 4)

    def test_downloaded_release_drifted_inp_reseal_refused(self):
        _, templates = self.downloaded_release_fixture()
        before = (self.repo / verifier.MANIFEST).read_bytes()
        write(self.repo / templates[0]["path"], "; changed template")
        result = self.reseal_cli()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertFalse((self.base / "rebuilt").exists())
        self.assertEqual((self.repo / verifier.MANIFEST).read_bytes(), before)

    def test_downloaded_release_unknown_inp_reseal_refused(self):
        self.downloaded_release_fixture()
        before = (self.repo / verifier.MANIFEST).read_bytes()
        write(self.repo / "unreviewed.inp", "; unreviewed file")
        result = self.reseal_cli()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertFalse((self.base / "rebuilt").exists())
        self.assertEqual((self.repo / verifier.MANIFEST).read_bytes(), before)

    def test_downloaded_release_unknown_schema_reseal_refused(self):
        self.downloaded_release_fixture()
        manifest = json.loads((self.repo / verifier.MANIFEST).read_text(encoding="utf-8"))
        manifest["schema"] = "unsupported-schema"
        write(self.repo / verifier.MANIFEST, json.dumps(manifest))
        result = self.reseal_cli()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertFalse((self.base / "rebuilt").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
