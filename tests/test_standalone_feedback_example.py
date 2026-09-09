"""Execute the standalone synthetic example through its real public CLI.

No Aspen model, vendor limit, or engineering acceptance is supplied by these tests.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SOURCE_ROOT = Path(__file__).resolve().parents[1]
ROOT = Path(os.environ.get("STANDALONE_PRODUCT_ROOT", SOURCE_ROOT)).resolve()
GENERATOR = ROOT / "examples" / "prepare_feedback_case.py"

# Reuse the sibling protocol test's explicit host AND worker bootstrap. The
# production gateway deliberately drops PYTHONPATH, so sitecustomize alone is
# not a child-process guard. This helper has no dependency on this test module.
sys.path.insert(0, str(SOURCE_ROOT / "tests"))
from test_standalone_entrypoints import GUARD_SOURCE, BOOTSTRAP_SOURCE, CHILD_SOURCE


class StandaloneFeedbackExampleTests(unittest.TestCase):
    def setUp(self):
        destination = os.environ.get("STANDALONE_FEEDBACK_REPORT_DIR")
        self.temporary = None
        if destination:
            self.root = Path(destination).resolve() / self._testMethodName
            self.root.mkdir(parents=True, exist_ok=False)
        else:
            self.temporary = tempfile.TemporaryDirectory(prefix="standalone_feedback_synthetic_")
            self.root = Path(self.temporary.name)
        self.case = self.root / "new synthetic case"
        self.guard = self.root / "qa_guard.py"
        self.guard.write_text(GUARD_SOURCE, encoding="utf-8")
        self.bootstrap = self.root / "bootstrap.py"
        self.bootstrap.write_text(BOOTSTRAP_SOURCE, encoding="utf-8")
        self.child = self.root / "child.py"
        self.child.write_text(CHILD_SOURCE, encoding="utf-8")
        (self.root / "child_source.txt").write_text(CHILD_SOURCE, encoding="utf-8")
        self.env = dict(os.environ, PYTHONUTF8="1", ENTRYPOINT_GUARD_DIR=str(self.root),
                        ENTRYPOINT_FORBIDDEN_ROOTS=os.environ.get("STANDALONE_FORBIDDEN_ROOTS", "[]"),
                        PYTHONDONTWRITEBYTECODE="1", CODEX_HOME=str(self.root / "empty_codex"))
        self.env.pop("PYTHONPATH", None)
        for name in tuple(self.env):
            if name.startswith("EQUIPMENT_DESIGN_LLM_") or name == "EQUIPMENT_BACKEND_ALLOW_COM":
                self.env.pop(name)

    def tearDown(self):
        try:
            events = self.guard_records()
            unexpected = [row for row in events if row["kind"].endswith("_blocked") and not row["negative_control"]]
            self.assertEqual(unexpected, [])
        finally:
            if self.temporary:
                self.temporary.cleanup()

    def guard_records(self):
        return [json.loads(line) for path in self.root.glob("guard-*.jsonl")
                for line in path.read_text(encoding="utf-8").splitlines()]

    def command(self, argv):
        target_index = next(index for index, part in enumerate(argv)
                            if str(part) in {str(GENERATOR), str(ROOT / "tools/expert_cli.py")})
        target = Path(argv[target_index])
        if target == GENERATOR:
            guarded = argv[:target_index] + [str(self.child), str(self.guard), *argv[target_index:]]
        else:
            guarded = argv[:target_index] + [str(self.bootstrap), str(ROOT), str(self.guard), *argv[target_index:]]
        return subprocess.run(guarded, cwd=self.root, env=self.env, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, encoding="utf-8", timeout=75)

    def generate(self):
        completed = self.command([sys.executable, "-X", "utf8", str(GENERATOR),
                                  "--output-dir", str(self.case)])
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        return json.loads(completed.stdout)

    def execute(self, summary):
        completed = self.command(summary["next_command_argv"])
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        result = json.loads(Path(summary["result_path"]).read_text(encoding="utf-8"))
        return result

    def test_generated_case_really_calculates_a_conditional_feedback_plan(self):
        summary = self.generate()
        self.assertTrue(summary["synthetic"])
        self.assertFalse(summary["engineering_evidence"])
        self.assertFalse(Path(summary["result_path"]).exists())
        result = self.execute(summary)
        self.assertEqual(result["backend_exit_code"], 0)
        plan = result["plan"]
        self.assertFalse(plan["engineering_accepted"])
        self.assertFalse(plan["flowsheet_modified"])
        row, = plan["equipment"]
        self.assertEqual(row["binding_gaps"], [])
        self.assertEqual(row["constraints"][0]["value"], 50)
        self.assertEqual(row["constraints"][0]["limit"], 30)
        self.assertTrue(row["constraints"][0]["resolved_value_source"]["calculations"])
        self.assertEqual(row["revision"]["preferred_route"], "exchanger_series")
        self.assertIsNone(row["revision"]["unit_count"])
        bound, = row["revision"]["initial_count_bounds"]
        self.assertEqual(bound["count"], 2)
        self.assertEqual(bound["status"], "CONDITIONAL_INITIAL_BOUND_NOT_SELECTED_COUNT")
        self.assertFalse(row["revision"]["automatic_aspen_mutation"])
        check, = row["configuration_calculations"]
        self.assertEqual(check["result"]["outlet_pressure_pa"], 450000)
        self.assertFalse(check["model_implementation_verified"])
        self.assertEqual(row["after_change_state"], "STALE_UNTIL_REPLAYED")
        self.assertEqual(row["affected_consumers"]["equipment"], ["SYN-E1", "SYN-P1", "SYN-S1"])

    def test_existing_empty_or_populated_output_is_never_reused(self):
        self.case.mkdir()
        for populated in (False, True):
            with self.subTest(populated=populated):
                if populated:
                    (self.case / "user-result.txt").write_bytes(b"KEEP ORIGINAL BYTES")
                before = {p.name: p.read_bytes() for p in self.case.iterdir()}
                completed = self.command([sys.executable, str(GENERATOR), "--output-dir", str(self.case)])
                self.assertEqual(completed.returncode, 2)
                self.assertEqual(json.loads(completed.stdout)["status"], "NOT_PREPARED")
                self.assertEqual({p.name: p.read_bytes() for p in self.case.iterdir()}, before)

    def test_tampered_limit_is_not_accepted_as_an_applicable_source(self):
        summary = self.generate()
        path = self.case / "synthetic_single_unit_limit.json"
        limit = json.loads(path.read_text(encoding="utf-8"))
        limit["value"] = 60
        path.write_text(json.dumps(limit), encoding="utf-8")
        completed = self.command(summary["next_command_argv"])
        self.assertEqual(completed.returncode, 2)
        failure = json.loads(completed.stdout)
        self.assertEqual(failure["status"], "NOT_COMPLETED")
        self.assertIn("hash differs", failure["error"])
        self.assertFalse(Path(summary["result_path"]).exists())

    def test_rehashed_wrong_unit_stays_a_local_gap_not_a_split_authorization(self):
        summary = self.generate()

        def rewrite(name, value):
            data = json.dumps(value, ensure_ascii=False).encode("utf-8")
            (self.case / name).write_bytes(data)
            return {"path": name, "sha256": hashlib.sha256(data).hexdigest().upper()}

        limit = json.loads((self.case / "synthetic_single_unit_limit.json").read_text(encoding="utf-8"))
        limit["unit"] = "ft2"
        limit_ref = rewrite("synthetic_single_unit_limit.json", limit)
        review = json.loads((self.case / "constraint_review.json").read_text(encoding="utf-8"))
        review["constraints"][0]["limit_source"] = {**limit_ref, "pointer": "/value"}
        review_ref = rewrite("constraint_review.json", review)
        request = json.loads(Path(summary["request_path"]).read_text(encoding="utf-8"))
        request["payload"]["context"]["constraint_evidence"]["SYN-E1"] = [
            {**review_ref, "pointer": "/constraints/0"}]
        rewrite("feedback_request.json", request)
        result = self.execute(summary)
        row, = result["plan"]["equipment"]
        self.assertIsNone(row["revision"])
        self.assertIn("LIMIT_SOURCE_UNIT_VERSION_OR_APPLICABILITY_MISMATCH", row["binding_gaps"])
        self.assertFalse(result["plan"]["engineering_accepted"])
        core = row["legacy_analysis"]["original_upstream_fields"]["result"]
        self.assertEqual(core["derived_parameters"]["heat_transfer_area_m2"], 50)

    def test_files_bind_one_synthetic_case_run_and_relative_source_pointers(self):
        summary = self.generate()
        for ref in summary["files"]:
            self.assertFalse(Path(ref["path"]).is_absolute())
            data = (self.case / ref["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest().upper(), ref["sha256"])
            value = json.loads(data)
            self.assertTrue(value["synthetic"])
            self.assertFalse(value["engineering_evidence"])
            self.assertEqual(value["case_id"], summary["case_id"])
            self.assertEqual(value["run_id"], summary["run_id"])
        request = json.loads(Path(summary["request_path"]).read_text(encoding="utf-8"))
        context = request["payload"]["context"]
        review_ref, = context["constraint_evidence"]["SYN-E1"]
        self.assertEqual(review_ref["pointer"], "/constraints/0")
        review = json.loads((self.case / review_ref["path"]).read_text(encoding="utf-8"))["constraints"][0]
        self.assertEqual(review["limit_source"]["pointer"], "/value")
        self.assertEqual(review["value_source"], {"kind": "current_selector_derivation", "field": "heat_transfer_area_m2"})

    def test_process_guards_block_network_and_com_without_mocking_the_backend(self):
        self.execute(self.generate())
        records = self.guard_records()
        # The one-shot compatibility response intentionally omits gateway data;
        # bind the actual worker by its explicit target event and shutdown PID.
        worker_targets = [row for row in records if row["kind"] == "guarded_target"
                          and Path(row["detail"]["target"]) == ROOT / "backends/equipment/app/equipment_design_agent.py"]
        self.assertEqual(len(worker_targets), 1)
        worker_pid = worker_targets[0]["pid"]
        ready_pids = {row["pid"] for row in records if row["kind"] == "guard_ready"}
        self.assertIn(worker_pid, ready_pids)
        self.assertGreaterEqual(len(ready_pids), 3)  # generator, expert host, real Agent worker
        for pid in ready_pids:
            with self.subTest(guarded_pid=pid):
                controls = {row["kind"] for row in records if row["pid"] == pid and row["negative_control"]}
                self.assertIn("network_blocked", controls)
                self.assertIn("com_import_blocked", controls)
        self.assertTrue(any(row["pid"] == worker_pid and row["kind"] == "guarded_target"
                            and Path(row["detail"]["target"]) == ROOT / "backends/equipment/app/equipment_design_agent.py"
                            for row in records))
        self.assertTrue(any(row["kind"] == "gateway_closed" and row["detail"] ==
                            {"worker_pid": worker_pid, "returncode": 0} for row in records))


if __name__ == "__main__":
    unittest.main(verbosity=2)
