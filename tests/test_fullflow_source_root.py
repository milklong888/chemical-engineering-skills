"""Synthetic adapter regression: real checker and stage caller, no case facts.

Only the gate module under test is replaced in this process. Source assets stay
at the original repository root. No installed/runtime/source files are edited.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
TEST_DIRECTORY = Path(__file__).resolve().parent
# When installed in repository/tests, the normal default is the real repository
# and its tools.fullflow_gate. An isolated draft requires explicit overrides.
REPOSITORY = Path(os.environ.get("FULLFLOW_GATE_REPOSITORY", str(TEST_DIRECTORY.parent))).resolve()
ORIGINAL = REPOSITORY / "tools/fullflow_gate.py"
OWNER = REPOSITORY / "plugins/chemical-engineering-skills/skills/aspen-document-driven-flowsheet/scripts/check_flow_handoff.py"
if not ORIGINAL.is_file() or not OWNER.is_file():
    raise RuntimeError("Run from repository/tests, or explicitly set FULLFLOW_GATE_REPOSITORY for an isolated draft")
sys.path.insert(0, str(REPOSITORY))
sys.path.insert(0, str(REPOSITORY / "tests"))


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def select_gate(path):
    import tools
    module = load_module("tools.fullflow_gate", path)
    tools.fullflow_gate = module
    # A draft is not an installation. Bind only its read-only packaged assets
    # to the same repository used by the baseline; do not widen evidence_root.
    module.ROOT = REPOSITORY
    return module


GATE_PATH = Path(os.environ.get("FULLFLOW_GATE_UNDER_TEST", str(ORIGINAL))).resolve()
if GATE_PATH == ORIGINAL.resolve():
    from tools import fullflow_gate as gate
else:
    gate = select_gate(GATE_PATH)
checker = load_module("r10_adapter_original_checker", OWNER)
import test_fullflow_gate as original_tests
from tools.design_stage import check_stage


class SourceReviewFixture(original_tests.FullflowFixture):
    def write_handoff(self, data):
        source_dir = self.root / "sources"
        source_dir.mkdir(exist_ok=True)
        self.review_source = self.put(
            "sources/synthetic-context.txt",
            "SYNTHETIC adapter test only: declared links in this graph are test data.",
        )
        documents = [{"id": "SYN-DOC", **self.review_source}]
        inventory = checker.source_inventory(documents, source_root=self.root)
        data["source_review"] = {
            "documents": documents,
            "units": [{"unit_id": row["unit_id"], "disposition": "mapped",
                       "stream_ids": [stream["id"] for stream in data["streams"]],
                       "reason": "Synthetic reference mapping; no engineering claim."}
                      for row in inventory],
        }
        input_ref = self.put("handoff-input.json", data)
        result = checker.check(data, source_root=self.root)
        assert result["status"] == "STRUCTURE_VALID", result
        assert result["source_review_checked"] is True, result
        result.update(input_sha256=input_ref["sha256"],
                      checker_sha256=hashlib.sha256(OWNER.read_bytes()).hexdigest())
        return {"handoff_input_ref": input_ref,
                "handoff_review_ref": self.put("handoff-review.json", result)}

    def replace_source_path_preserving_prior_success(self, path, digest):
        source_gate = self.contract["source_gate"]
        data = self.read(source_gate["handoff_input_ref"])
        data["source_review"]["documents"][0].update(path=path, sha256=digest)
        source_gate["handoff_input_ref"] = self.put("handoff-input.json", data)
        report = self.read(source_gate["handoff_review_ref"])
        report["input_sha256"] = source_gate["handoff_input_ref"]["sha256"]
        source_gate["handoff_review_ref"] = self.put("handoff-review.json", report)
        # Keep all observation and review hashes internally current. The stale
        # success label must never override the real source reread.
        source_gate.update(self.reviews("source", 5, {
            "design_basis_sha256": source_gate["design_basis_ref"]["sha256"]}))


class SourceRootAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(
            prefix="r10_adapter_synthetic_", dir=os.environ.get("FULLFLOW_ADAPTER_TMPDIR"))
        self.addCleanup(self.temporary.cleanup)
        self.parent = Path(self.temporary.name)
        self.root = self.parent / "evidence"
        self.root.mkdir()
        self.fixture = SourceReviewFixture(self.root)

    def payload(self, fixture=None):
        fixture = fixture or self.fixture
        return {"stage": "source", "question": "Synthetic explicit fullflow workflow",
                **fixture.identity, "fullflow_contract": fixture.put("contract.json", fixture.contract)}

    def call_gate(self):
        return gate.check_fullflow(self.payload(), self.root)

    def call_stage(self, fixture=None):
        def search_spy(**query):
            return {"knowledge": {"mode": "macro_first", "results": [{
                "node_id": query.get("node_id", "SYN-ADAPTER"),
                "knowledge_layer": "L3" if query.get("node_id") else "L2",
                "content_available": True, "text_is_excerpt": True}]}, "equipment": None}

        def equipment_spy(request):
            self.assertEqual(request["operation"], "capabilities")
            return {"backend_exit_code": 0, "response": {"synthetic": True}}

        # This is the original stage implementation, including its normal import
        # of tools.fullflow_gate. Neither checker nor fullflow result is mocked.
        payload = self.payload(fixture)
        # task_revision belongs to the bound fullflow contract, not to the
        # stage entrypoint's existing public field set.
        payload.pop("task_revision")
        return check_stage(payload, self.root,
                           search_runner=search_spy, equipment_runner=equipment_spy)

    def assert_consistent(self, result):
        self.assertEqual(result["status"], "EVIDENCE_STRUCTURE_CONSISTENT", result["needs"])
        self.assertFalse(result["engineering_accepted"])
        self.assertFalse(result["execution_verified"])
        self.assertFalse(result["stage_advanced"])

    def assert_source_rejected(self, result, message):
        failures = [row for row in result["needs"] if row["code"] == "HANDOFF_INCOMPLETE"]
        self.assertEqual(len(failures), 1, result["needs"])
        errors = failures[0]["detail"]["errors"]
        self.assertTrue(any("source_review" in error and message in error for error in errors), errors)
        self.assertEqual(result["status"], "ACTION_REQUIRED")
        self.assertFalse(result["engineering_accepted"])

    def test_relative_source_path_uses_same_declared_evidence_root(self):
        self.assert_consistent(self.call_gate())

    def test_stage_calls_real_gate_with_relative_source_path(self):
        result = self.call_stage()
        self.assert_consistent(result["fullflow_gate"])
        self.assertEqual(result["status"], "MODULE_CHECKS_EXECUTED", result["needs"])
        self.assertFalse(result["engineering_accepted"])
        self.assertFalse(result["stage_advanced"])

    def test_missing_source_is_rejected_in_gate_and_stage(self):
        (self.root / self.fixture.review_source["path"]).unlink()
        for result in (self.call_gate(), self.call_stage()["fullflow_gate"]):
            self.assert_source_rejected(result, "synthetic-context.txt")

    def test_drifted_source_is_rejected_in_gate_and_stage(self):
        (self.root / self.fixture.review_source["path"]).write_text("SYNTHETIC changed bytes", encoding="utf-8")
        for result in (self.call_gate(), self.call_stage()["fullflow_gate"]):
            self.assert_source_rejected(result, "source hash differs from current bytes")

    def test_parent_relative_source_is_not_auto_trusted_in_gate_or_stage(self):
        outside = self.parent / "outside.txt"
        outside.write_text("SYNTHETIC out-of-root source", encoding="utf-8")
        self.fixture.replace_source_path_preserving_prior_success(
            "../outside.txt", hashlib.sha256(outside.read_bytes()).hexdigest())
        for result in (self.call_gate(), self.call_stage()["fullflow_gate"]):
            self.assert_source_rejected(result, "source leaves explicit source_root")

    def test_absolute_source_outside_root_is_not_auto_trusted(self):
        outside = self.parent / "absolute-outside.txt"
        outside.write_text("SYNTHETIC out-of-root source", encoding="utf-8")
        self.fixture.replace_source_path_preserving_prior_success(
            str(outside), hashlib.sha256(outside.read_bytes()).hexdigest())
        self.assert_source_rejected(self.call_gate(), "source leaves explicit source_root")

    def test_network_source_path_is_rejected_before_open(self):
        self.fixture.replace_source_path_preserving_prior_success("//invalid.example/source.txt", "0" * 64)
        self.assert_source_rejected(self.call_gate(), "network, device or URI paths are not allowed")

    def test_old_handoff_without_source_review_requires_incremental_mapping(self):
        legacy = original_tests.FullflowFixture(self.root)
        source_gate = legacy.contract["source_gate"]
        data = legacy.read(source_gate["handoff_input_ref"])
        del data["source_review"]
        source_gate.update(legacy.write_handoff(data))
        source_gate.update(legacy.reviews("source", 5, {
            "design_basis_sha256": source_gate["design_basis_ref"]["sha256"]}))
        self.assertNotIn("source_review", data)
        checked = gate.check_fullflow(self.payload(legacy), self.root)
        self.assertIn("SOURCE_REVIEW_REQUIRED", {row["code"] for row in checked["needs"]})
        self.assertFalse(checked["engineering_accepted"])
        result = self.call_stage(legacy)
        self.assertIn("SOURCE_REVIEW_REQUIRED", {row["code"] for row in result["fullflow_gate"]["needs"]})
        self.assertEqual(result["status"], "ACTION_REQUIRED")

    def test_report_hash_binding_is_not_relaxed(self):
        reference = self.fixture.contract["source_gate"]["handoff_review_ref"]
        report = self.fixture.read(reference)
        report["input_sha256"] = "0" * 64
        self.fixture.contract["source_gate"]["handoff_review_ref"] = self.fixture.put(reference["path"], report)
        result = self.call_gate()
        self.assertIn("HANDOFF_IDENTITY_MISMATCH", {row["code"] for row in result["needs"]})
        self.assertFalse(result["engineering_accepted"])

    def test_handoff_replay_receives_exact_resolved_root_not_parent_or_cwd(self):
        received = []
        actual_check = checker.check

        def record_check(data, **kwargs):
            received.append(kwargs.get("source_root"))
            return actual_check(data, **kwargs)

        original_loader = importlib.util.module_from_spec

        def module_with_spy(spec):
            module = original_loader(spec)
            original_execute = spec.loader.exec_module

            def execute_then_wrap(loaded):
                original_execute(loaded)
                loaded.check = record_check

            spec.loader.exec_module = execute_then_wrap
            return module

        with patch.object(gate.importlib.util, "module_from_spec", side_effect=module_with_spy):
            result = self.call_gate()
        self.assert_consistent(result)
        self.assertEqual(received, [self.root.resolve()])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--include-existing", action="store_true")
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SourceRootAdapterTests)
    if args.include_existing:
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(original_tests.FullflowGateTests))
        import test_fullflow_stage_integration as integration_tests
        # Run the five declared integration tests; avoid rerunning inherited
        # unrelated CLI/backend tests or creating any install/runtime state.
        for name in integration_tests.FullflowStageIntegration.__dict__:
            if name.startswith("test_"):
                suite.addTest(integration_tests.FullflowStageIntegration(name))
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    text = output.getvalue()
    print(text, end="")
    report = {"synthetic_only": True, "installed": False,
              "gate_path": str(GATE_PATH), "gate_sha256": hashlib.sha256(GATE_PATH.read_bytes()).hexdigest(),
              "original_path": str(ORIGINAL), "original_sha256": hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(),
              "checker_path": str(OWNER), "checker_sha256": hashlib.sha256(OWNER.read_bytes()).hexdigest(),
              "read_only_asset_root": str(REPOSITORY),
              "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
              "skipped": len(result.skipped), "successful": result.wasSuccessful(), "output": text,
              "failure_details": [{"test": str(test), "traceback": detail} for test, detail in result.failures],
              "error_details": [{"test": str(test), "traceback": detail} for test, detail in result.errors]}
    destination = args.report.resolve()
    if not destination.is_relative_to(TEST_DIRECTORY):
        raise ValueError("Report must stay in this draft adapter directory")
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
