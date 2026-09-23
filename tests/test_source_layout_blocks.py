"""Portable synthetic source-layout regressions for repository tests/.

Default execution adds 28 tests without repeating the existing source/stage
baseline. Set DOCFLOW_LAYOUT_INCLUDE_BASELINE=1 to replay the complete 67-test
suite against the selected checker.

ROOT defaults to this file's repository root. DOCFLOW_LAYOUT_TEST_ROOT can
explicitly name the source repository when running an isolated candidate file.
STANDALONE_PRODUCT_ROOT retains the existing runtime override convention.
DOCFLOW_LAYOUT_CHECKER optionally selects an isolated checker; fixed sibling
assets still come from product_contract.skill_location(), never caller code.
No workspace search, installation, network, Aspen, or import-time writes.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(os.environ.get("DOCFLOW_LAYOUT_TEST_ROOT", Path(__file__).resolve().parents[1])).resolve()
RUNTIME = Path(os.environ.get("STANDALONE_PRODUCT_ROOT", ROOT)).resolve()
OWNER_RELATIVE = Path("plugins/chemical-engineering-skills/skills/aspen-document-driven-flowsheet")
TEST_SOURCE = ROOT / OWNER_RELATIVE / "scripts/tests/test_source_review.py"
TEST_STAGE = ROOT / "tests/test_stage_source_review.py"
for required in (TEST_SOURCE, TEST_STAGE, RUNTIME / "tools/product_contract.py"):
    if not required.is_file():
        raise RuntimeError(
            f"Portable layout test dependency not found: {required}. "
            "Set DOCFLOW_LAYOUT_TEST_ROOT to the source repository and "
            "STANDALONE_PRODUCT_ROOT to its intended runtime."
        )


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))
from tools import product_contract

location = product_contract.skill_location()
if not location.get("available") or not location.get("path"):
    raise RuntimeError("The explicit product runtime has no registered Skill location")
SKILLS = Path(location["path"]).resolve().parent.parent
CANDIDATE = Path(os.environ.get(
    "DOCFLOW_LAYOUT_CHECKER",
    SKILLS / "aspen-document-driven-flowsheet/scripts/check_flow_handoff.py",
)).resolve()
if not CANDIDATE.is_file():
    raise RuntimeError(f"Selected layout checker does not exist: {CANDIDATE}")

checker = load("portable_layout_checker", CANDIDATE)
baseline = load("portable_source_review_fixtures", TEST_SOURCE)
baseline.checker = checker
baseline.CANDIDATE = CANDIDATE
stage_tests = load("portable_stage_source_review_fixtures", TEST_STAGE)
stage_tests.CHECKER = CANDIDATE


def strict_runtime(test):
    """Use the registered fixed siblings in a disposable owner layout."""
    skills = test.root / "runtime" / "skills"
    target = skills / "aspen-document-driven-flowsheet/scripts/check_flow_handoff.py"
    target.parent.mkdir(parents=True)
    shutil.copyfile(CANDIDATE, target)
    for owner, relative in (
        ("chemical-engineering-expert", "scripts/check_reaction_derivations.py"),
        ("aspen-document-driven-flowsheet", "assets/property_method_names_v14.json"),
    ):
        source = SKILLS / owner / relative
        destination = skills / owner / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    return load("portable_strict_layout_checker", target), target


# This privately loaded baseline class is not the repository discovery module.
# Replace only its old draft-layout asset locator, not any assertions or gates.
baseline.SourceReviewTests.strict_runtime = strict_runtime

class LayoutBlocksTests(unittest.TestCase):
    strict_runtime = strict_runtime

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="layout-v2-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source.md"
        self.set_source("Alpha ordinary line.\nWrapped continuation.\n\nAnother paragraph.\n")

    def set_source(self, value):
        self.raw = value if isinstance(value, bytes) else value.encode("utf-8")
        self.source.write_bytes(self.raw)
        self.documents = [{"id": "synthetic", "path": self.source.name,
                           "sha256": hashlib.sha256(self.raw).hexdigest()}]

    def inventory(self, mode="paragraphs_v1"):
        return checker.source_inventory(self.documents, source_root=self.root, unit_mode=mode)

    def reviewed_handoff(self, mode="paragraphs_v1", explicit=True):
        data = baseline.SourceReviewTests.handoff(self)
        units = self.inventory(mode)
        data["source_review"] = {"documents": copy.deepcopy(self.documents), "units": [
            {"unit_id": row["unit_id"], "disposition": "mapped", "stream_ids": ["S1"],
             "reason": "Synthetic lexical unit linked to a declared edge; no meaning is certified."}
            for row in units]}
        if explicit:
            data["source_review"]["unit_mode"] = mode
        return data

    def strict(self, mode="paragraphs_v1", explicit=True):
        runtime, target = self.strict_runtime()
        data = baseline.SourceReviewTests.strict_handoff(self)
        data["source_review"] = self.reviewed_handoff(mode, explicit)["source_review"]
        return runtime, target, data

    def cli(self, data, *extra, target=CANDIDATE):
        request = self.root / "request.json"
        request.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return subprocess.run([sys.executable, "-B", "-X", "utf8", str(target),
                               "--input", str(request), "--source-root", str(self.root), *extra],
                              capture_output=True, text=True, encoding="utf-8", timeout=30)

    def test_default_old_signature_and_ids_unchanged(self):
        default = checker.source_inventory(self.documents, self.root)
        explicit = self.inventory("paragraphs_v1")
        self.assertEqual(default, explicit)
        first = "Alpha ordinary line.\nWrapped continuation."
        self.assertEqual(default[0]["unit_id"], "synthetic:p0001:" + hashlib.sha256(first.encode()).hexdigest()[:12])
        self.assertEqual(default[0]["text"], first)
        self.assertEqual(len(default), 2)
        self.assertEqual((default[0]["line_start"], default[0]["line_end"]), (1, 2))

    def test_v2_preserves_ordinary_wrapped_lines(self):
        units = self.inventory("layout_blocks_v2")
        self.assertEqual(len(units), 2)
        self.assertEqual(units[0]["text"], "Alpha ordinary line.\nWrapped continuation.")
        self.assertTrue(units[0]["unit_id"].startswith("synthetic:b0001:"))

    def test_adjacent_items_keep_their_continuations(self):
        self.set_source("Introduction.\n- Alpha item.\n  Alpha continuation.\n- Beta item.\n  Beta continuation.\n")
        units = self.inventory("layout_blocks_v2")
        self.assertEqual([x["text"] for x in units], ["Introduction.", "- Alpha item.\n  Alpha continuation.", "- Beta item.\n  Beta continuation."])
        self.assertEqual([(x["line_start"], x["line_end"]) for x in units], [(1, 1), (2, 3), (4, 5)])

    def test_numbered_unicode_and_nested_items(self):
        self.set_source("1. Parent item.\n   * Child item.\n     Child continuation.\n   * Second child.\n2) Next parent.\n\u2022 Final item.\n")
        units = self.inventory("layout_blocks_v2")
        self.assertEqual(len(units), 5)
        self.assertEqual(units[1]["text"], "   * Child item.\n     Child continuation.")
        self.assertEqual([x["line_start"] for x in units], [1, 2, 4, 5, 6])

    def test_atx_heading_starts_block_without_splitting_body(self):
        self.set_source("Opening.\n# Heading\nBody line.\nContinuation.\n## Next heading\nMore body.\n")
        units = self.inventory("layout_blocks_v2")
        self.assertEqual([x["text"] for x in units], ["Opening.", "# Heading\nBody line.\nContinuation.", "## Next heading\nMore body."])

    def test_unmarked_math_negative_decimal_and_rules_are_not_items(self):
        text = "Intro.\n-3.5\n+2.25\n1.25 * x\nx = y + z\n---\n- - -\n***\n* * *\n___\n#hashtag\n####### Not an ATX heading\n"
        self.set_source(text)
        units = self.inventory("layout_blocks_v2")
        self.assertEqual(len(units), 1)
        self.assertEqual(units[0]["text"], text.rstrip("\n"))
        self.assertEqual(checker._legacy_aggregated_list_units(self.inventory()), [])

    def test_marked_equations_are_layout_only_not_semantic_evidence(self):
        self.set_source("- x = y\n- y = z\n")
        data = self.reviewed_handoff("layout_blocks_v2")
        result = checker.check(data, source_root=self.root)
        self.assertEqual(len(result["source_review"]["inventory"]), 2)
        self.assertIn("reading aids, not interpreted functions", result["source_review"]["boundary"])
        for key in ("source_truth_verified", "engineering_accepted", "execution_verified"):
            self.assertIs(result["source_review"][key], False)

    def test_fenced_code_math_and_blank_gaps_remain_opaque(self):
        self.set_source("Intro.\n```text\n- Code item.\n\n- Still code.\n```\n$$\n- Formula row.\n- Other formula.\n$$\n\\[\n# Math row\n\\]\nEnd.\n")
        starts = checker._source_layout_starts(self.raw.decode().split("\n"))
        self.assertEqual(starts, {})
        self.assertEqual(checker._legacy_aggregated_list_units(self.inventory()), [])

    def test_bom_crlf_hashes_and_original_line_numbers(self):
        raw = b"\xef\xbb\xbfIntro.\r\n- Alpha.\r\n  Continued.\r\n- Beta.\r\n"
        self.set_source(raw)
        units = self.inventory("layout_blocks_v2")
        self.assertEqual([(x["line_start"], x["line_end"]) for x in units], [(1, 1), (2, 3), (4, 4)])
        self.assertEqual(units[1]["text"], "- Alpha.\n  Continued.")
        for row in units:
            self.assertEqual(row["document_sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(row["text_sha256"], hashlib.sha256(row["text"].encode()).hexdigest())
        self.assertEqual(self.source.read_bytes(), raw)

    def test_page_formfeed_not_a_semantic_split(self):
        self.set_source("First line.\n\fcontinued text.\n- Alpha.\n- Beta.\n")
        units = self.inventory("layout_blocks_v2")
        self.assertEqual(units[0]["text"], "First line.\n\fcontinued text.")
        self.assertEqual(units[1]["line_start"], 3)

    def test_old_nonstrict_list_record_still_replays(self):
        self.set_source("- Alpha.\n- Beta.\n")
        result = checker.check(self.reviewed_handoff(explicit=False), source_root=self.root)
        self.assertEqual(result["errors"], [])
        self.assertTrue(result["source_review_checked"])
        self.assertEqual(result["source_review"]["unit_mode"], "paragraphs_v1")

    def test_old_strict_record_without_aggregated_list_still_passes(self):
        runtime, _, data = self.strict(explicit=False)
        result = runtime.check(data, require_source_review=True, source_root=self.root)
        self.assertEqual(result["errors"], [])
        self.assertTrue(result["source_review_checked"])

    def test_old_strict_separate_list_paragraphs_still_pass(self):
        self.set_source("- Alpha.\n\n- Beta.\n")
        runtime, _, data = self.strict(explicit=False)
        result = runtime.check(data, require_source_review=True, source_root=self.root)
        self.assertEqual(result["errors"], [])

    def test_old_strict_headings_alone_do_not_trigger_list_migration(self):
        self.set_source("# Alpha heading\nBody.\n## Beta heading\nOther body.\n")
        runtime, _, data = self.strict(explicit=False)
        result = runtime.check(data, require_source_review=True, source_root=self.root)
        self.assertEqual(result["errors"], [])

    def test_old_strict_aggregated_list_requires_explicit_migration(self):
        self.set_source("Intro.\n- Alpha.\n  Continued.\n- Beta.\n")
        runtime, _, data = self.strict(explicit=False)
        result = runtime.check(data, require_source_review=True, source_root=self.root)
        self.assertFalse(result["source_review_checked"])
        self.assertEqual(result["status"], "STRUCTURE_INVALID")
        self.assertIn("layout_blocks_v2", " ".join(result["errors"]))
        self.assertIn("old unit IDs are not remapped", " ".join(result["errors"]))
        blocked = result["source_review"]["layout_migration_required"][0]
        self.assertEqual(blocked["list_item_start_lines"], [2, 4])
        self.assertEqual(blocked["unit_id"], data["source_review"]["units"][0]["unit_id"])

    def test_old_strict_nested_aggregate_is_not_silently_accepted(self):
        self.set_source("- Parent.\n  - Child.\n  - Other child.\n")
        runtime, _, data = self.strict()
        result = runtime.check(data, require_source_review=True, source_root=self.root)
        self.assertIn("multiple explicit list items", " ".join(result["errors"]))

    def test_v2_strict_every_block_requires_disposition(self):
        self.set_source("- Alpha.\n- Beta.\n")
        runtime, _, data = self.strict("layout_blocks_v2")
        valid = runtime.check(data, require_source_review=True, source_root=self.root)
        self.assertEqual(valid["errors"], [])
        data["source_review"]["units"].pop()
        failed = runtime.check(data, require_source_review=True, source_root=self.root)
        self.assertIn("missing source paragraphs", " ".join(failed["errors"]))

    def test_old_ids_in_v2_record_are_rejected_not_remapped(self):
        self.set_source("- Alpha.\n- Beta.\n")
        data = self.reviewed_handoff()
        data["source_review"]["unit_mode"] = "layout_blocks_v2"
        result = checker.check(data, source_root=self.root)
        self.assertIn("unknown source paragraph", " ".join(result["errors"]))

    def test_v2_current_bytes_and_stale_ids_both_fail_closed(self):
        self.set_source("- Alpha.\n- Beta.\n")
        data = self.reviewed_handoff("layout_blocks_v2")
        self.set_source("- Changed alpha.\n- Beta.\n")
        failed_hash = checker.check(data, source_root=self.root)
        self.assertIn("source hash differs", " ".join(failed_hash["errors"]))
        data["source_review"]["documents"] = copy.deepcopy(self.documents)
        failed_id = checker.check(data, source_root=self.root)
        self.assertIn("unknown source paragraph", " ".join(failed_id["errors"]))

    def test_identical_v2_items_still_have_distinct_ids(self):
        self.set_source("- Repeated item.\n- Repeated item.\n")
        units = self.inventory("layout_blocks_v2")
        self.assertNotEqual(units[0]["unit_id"], units[1]["unit_id"])
        self.assertEqual(units[0]["text_sha256"], units[1]["text_sha256"])

    def test_unknown_modes_fail_api_checker_and_cli(self):
        for mode in ("future_mode", None, 2, []):
            with self.subTest(mode=mode):
                with self.assertRaisesRegex(ValueError, "source_review.unit_mode"):
                    self.inventory(mode)
                data = self.reviewed_handoff()
                data["source_review"]["unit_mode"] = mode
                result = checker.check(data, source_root=self.root)
                self.assertIn("source_review.unit_mode", " ".join(result["errors"]))
                run = self.cli(data, "--source-inventory")
                self.assertEqual(run.returncode, 2)
                self.assertIn("source_review.unit_mode", run.stdout)

    def test_cli_inventory_and_check_share_v2_mode_and_ids(self):
        self.set_source("# Heading\n- Alpha.\n  Continued.\n- Beta.\n")
        data = self.reviewed_handoff("layout_blocks_v2")
        run = self.cli(data, "--source-inventory")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        receipt = json.loads(run.stdout)
        self.assertEqual(receipt["unit_mode"], "layout_blocks_v2")
        self.assertEqual(receipt["inventory"], self.inventory("layout_blocks_v2"))
        self.assertFalse((self.root / "review.json").exists())
        output = self.root / "report"
        run = self.cli(data, "--output-dir", str(output))
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        report = json.loads((output / "review.json").read_text(encoding="utf-8"))
        self.assertEqual(report["source_review"]["unit_mode"], "layout_blocks_v2")
        self.assertEqual(report["source_review"]["inventory"], receipt["inventory"])

    def test_default_inventory_cli_reports_legacy_mode(self):
        run = self.cli({"source_review": {"documents": self.documents}}, "--source-inventory")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(json.loads(run.stdout)["unit_mode"], "paragraphs_v1")

    def test_strict_v2_cli_uses_existing_flags_and_preserves_false_truth(self):
        self.set_source("- Alpha.\n- Beta.\n")
        _, target, data = self.strict("layout_blocks_v2")
        run = self.cli(data, "--require-source-review", "--output-dir", str(self.root / "strict-report"), target=target)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        result = json.loads(run.stdout)
        self.assertTrue(result["source_review_checked"])
        self.assertEqual(result["source_review"]["unit_mode"], "layout_blocks_v2")
        for key in ("source_truth_verified", "source_inventory_verified", "engineering_accepted", "execution_verified"):
            self.assertIs(result["source_review"][key], False)

    def test_v2_path_restrictions_are_not_bypassed(self):
        documents = [{**self.documents[0], "path": "https://example.invalid/synthetic.md"}]
        with self.assertRaisesRegex(ValueError, "not allowed"):
            checker.source_inventory(documents, source_root=self.root, unit_mode="layout_blocks_v2")

    def test_v2_count_limit_applies_to_layout_units(self):
        self.set_source("- Alpha.\n" * (checker.SOURCE_MAX_UNITS + 1))
        with self.assertRaisesRegex(ValueError, "exceeds"):
            self.inventory("layout_blocks_v2")


class LayoutStageTests(unittest.TestCase):
    # Reuse current stage fixtures without inheriting its eleven test methods.
    setUp = stage_tests.StageSourceReviewTests.setUp
    documents = stage_tests.StageSourceReviewTests.documents
    inventory_via_cli = stage_tests.StageSourceReviewTests.inventory_via_cli
    declaration = stage_tests.StageSourceReviewTests.declaration
    search = stage_tests.StageSourceReviewTests.search
    equipment = stage_tests.StageSourceReviewTests.equipment
    run_stage = stage_tests.StageSourceReviewTests.run_stage
    assert_rejected = stage_tests.StageSourceReviewTests.assert_rejected

    def test_v2_mode_through_existing_stage_signature(self):
        self.source.write_text("- Alpha unit.\n  Continued.\n- Beta unit.\n", encoding="utf-8")
        mode = "layout_blocks_v2"
        local_checker = load("stage_layout_checker", self.checker)
        units = local_checker.source_inventory(self.documents(), source_root=self.root, unit_mode=mode)
        data = stage_tests.fixtures.fixture()
        data["expert_plan"]["reaction_derivations"] = stage_tests.fixtures.no_reaction()
        data["source_review"] = {"documents": self.documents(), "unit_mode": mode, "units": [
            {"unit_id": row["unit_id"], "disposition": "mapped", "stream_ids": ["feed", "product"],
             "reason": "Synthetic layout-to-edge declaration; no source meaning certified."}
            for row in units]}
        result = self.run_stage(data)
        self.assertEqual(result["status"], "MODULE_CHECKS_EXECUTED", result)
        receipt = result["expert_planning"]["source_review"]
        self.assertEqual(receipt["unit_mode"], mode)
        self.assertEqual(len(receipt["inventory"]), 2)
        self.assertFalse(receipt["source_truth_verified"])

    def test_legacy_aggregated_layout_is_rejected_by_existing_stage(self):
        self.source.write_text("- Alpha unit.\n- Beta unit.\n\nContext.\n", encoding="utf-8")
        result = self.run_stage(self.declaration())
        self.assert_rejected(result)
        self.assertIn("layout_blocks_v2", json.dumps(result))


def load_tests(loader, tests, pattern):
    suite = unittest.TestSuite()
    if os.environ.get("DOCFLOW_LAYOUT_INCLUDE_BASELINE") == "1":
        suite.addTests(loader.loadTestsFromTestCase(baseline.SourceReviewTests))
        suite.addTests(loader.loadTestsFromTestCase(stage_tests.StageSourceReviewTests))
    suite.addTests(loader.loadTestsFromTestCase(LayoutBlocksTests))
    suite.addTests(loader.loadTestsFromTestCase(LayoutStageTests))
    return suite


if __name__ == "__main__":
    unittest.main(verbosity=2)
