"""Offline fake-COM and real subprocess fault tests. Never starts real Aspen."""
from __future__ import annotations
import argparse
from datetime import datetime
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import aspen_runtime as rt
import aspen_run_supervisor as supervisor
import apw_saveas_reopen_check as apw
SKILLS = SCRIPTS.parents[1]
sys.path.insert(0, str(SKILLS / 'chemical-engineering-expert/scripts/tests'))
from release_test_support import configure_test_arguments, case_directory_name
ARTIFACT_ROOT = configure_test_arguments('aspen-runtime-regression-').artifact_root
RUN_ROOT = ARTIFACT_ROOT / ("offline_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
RUN_ROOT.mkdir(parents=True)

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result

operation = load_module("runtime_test_operation", SKILLS / "aspen-document-driven-flowsheet/scripts/templates/aspen_operation_template.py")
component = load_module("runtime_test_component", SKILLS / "aspen-plus-template/scripts/create_aspen_template.py")

class FakePythonCom:
    def __init__(self):
        self.initialized = self.uninitialized = self.pumps = 0
    def CoInitialize(self): self.initialized += 1
    def CoUninitialize(self): self.uninitialized += 1
    def PumpWaitingMessages(self): self.pumps += 1

class FakeEngine:
    def __init__(self, mode="completed"):
        self.mode, self.runs = mode, 0
    def Run2(self, sync):
        self.runs += 1
        if self.mode == "run_error": raise RuntimeError("synthetic Run2 COM error")
    @property
    def IsRunning(self):
        if self.mode == "unknown": raise RuntimeError("synthetic status unreadable")
        if self.mode == "unknown_value": return None
        return self.mode == "timeout"

class FakeApp:
    Version = "MOCK_PRODUCT_VERSION_NO_REAL_ASPEN"
    VersionNumber = "MOCK-1"
    def __init__(self, mode="completed", fail_close=False, fail_export=False):
        self.Engine = FakeEngine(mode)
        self.fail_close, self.fail_export = fail_close, fail_export
        self.calls = []
        self.node = types.SimpleNamespace(Value=3.0, UnitString="bar")
        self.Tree = types.SimpleNamespace(FindNode=lambda path: None if path.endswith("MISSING") else self.node)
    def InitFromArchive2(self, path): self.calls.append(("open_archive", path))
    def InitFromFile(self, path): self.calls.append(("open_file", path))
    def InitFromFile2(self, path): self.calls.append(("open_file2", path))
    def Export(self, export_type, path):
        if self.fail_export: raise RuntimeError("synthetic export failure")
        Path(path).write_text("SYNTHETIC EXPORT\nCOMPONENTS CO2 CO2\n\nPROPERTIES NRTL\n", encoding="ascii")
        self.calls.append(("export", path))
    def SaveAs(self, path, *args):
        Path(path).write_bytes(b"SYNTHETIC APW/APWZ; NOT AN ASPEN MODEL")
        self.calls.append(("save", path))
    def Close(self, save):
        self.calls.append(("close", save))
        if self.fail_close: raise RuntimeError("synthetic close failure")
    def Quit(self): self.calls.append(("quit",))

def session(app=None):
    app, pythoncom = app or FakeApp(), FakePythonCom()
    result = rt.create_session("Apwn.Document.TEST", dispatch_factory=lambda _: app, pythoncom_adapter=pythoncom)
    return result

class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix=case_directory_name(self._testMethodName) + "_", dir=RUN_ROOT))

    def test_atomic_owner_token_and_pid_identity(self):
        path = self.root / "owner.lock"
        lease = rt.acquire_lock(path, run_id="SYNTHETIC-RUN")
        foreign = rt.LockLease(path, {**lease.record, "owner_token": "FOREIGN"})
        self.assertFalse(foreign.release())
        self.assertTrue(path.exists())
        self.assertTrue(lease.release())
        self.assertFalse(path.exists())

    def test_two_real_processes_cannot_both_acquire(self):
        lock = self.root / "race.lock"
        code = "import sys,time; from pathlib import Path; sys.path.insert(0,sys.argv[1]); import aspen_runtime as r\ntry:\n l=r.acquire_lock(Path(sys.argv[2])); print('OWNED',flush=True); time.sleep(2); l.release()\nexcept TimeoutError:\n print('BLOCKED',flush=True)"
        processes = [subprocess.Popen([sys.executable, "-c", code, str(SCRIPTS), str(lock)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
        results = [p.communicate(timeout=6)[0].strip() for p in processes]
        self.assertEqual(sorted(results), ["BLOCKED", "OWNED"])
        self.assertFalse(lock.exists())

    def test_replaced_lock_not_released(self):
        path = self.root / "replace.lock"
        lease = rt.acquire_lock(path)
        original = dict(lease.record)
        rt.atomic_json(path, {**original, "owner_token": "OTHER-TASK"})
        self.assertFalse(lease.release())
        self.assertEqual(json.loads(path.read_text())["owner_token"], "OTHER-TASK")
        rt.atomic_json(path, original)  # Restore only this synthetic fixture.
        self.assertTrue(lease.release())

    def test_explicit_version_never_falls_back_silently(self):
        registry = [{"prog_id": "Apwn.Document.40.0", "clsid": "MOCK"}]
        with self.assertRaises(RuntimeError): rt.select_progid("Apwn.Document.38.0", registry)
        decision = rt.select_progid("Apwn.Document.38.0", registry, ("Apwn.Document.40.0",))
        self.assertTrue(decision["fallback_used"])
        self.assertFalse(decision["version_compatibility_proven"])

    def test_com_initialization_and_close_errors_are_visible(self):
        app = FakeApp(fail_close=True)
        item = session(app)
        result = rt.close_session(item)
        self.assertFalse(result["closed_cleanly"])
        self.assertIn(("quit",), app.calls)
        self.assertEqual(item.pythoncom.initialized, item.pythoncom.uninitialized)
        self.assertEqual(item.metadata["version_readback"]["Version"], FakeApp.Version)

    def test_creation_error_uninitializes_com(self):
        pc = FakePythonCom()
        with self.assertRaises(RuntimeError):
            rt.create_session("EXPLICIT", dispatch_factory=mock.Mock(side_effect=RuntimeError("synthetic creation failure")), pythoncom_adapter=pc)
        self.assertEqual(pc.initialized, pc.uninitialized)

    def test_run_status_unknown_timeout_and_error_never_pass(self):
        for mode, expected in (("unknown", "state_unknown"), ("unknown_value", "state_unknown"), ("timeout", "timeout"), ("run_error", "com_error"), ("completed", "completed")):
            with self.subTest(mode=mode):
                item = session(FakeApp(mode))
                result = rt.run_case(item, timeout_s=.03, run_id="SYNTHETIC", case_sha256="A" * 64)
                self.assertEqual(result["status"], expected)
                self.assertIsNone(result["simulation_clean"])
                self.assertFalse(result.get("delivery_passed", False))
                rt.close_session(item)

    def test_exact_input_units_and_output_write_guard(self):
        item = session()
        path = r"\Data\Blocks\P1\Input\PRES"
        with self.assertRaises(ValueError): rt.write_input_node(item, path, 5, expected_unit="MPa", allowed_input_paths=(path,))
        self.assertEqual(item.app.node.Value, 3)
        result = rt.write_input_node(item, path, 5, expected_unit="bar", allowed_input_paths=(path,))
        self.assertEqual(result["status"], "written_verified")
        output = path.replace("Input", "Output")
        with self.assertRaises(ValueError): rt.write_input_node(item, output, 6, expected_unit="bar", allowed_input_paths=(output,))
        self.assertEqual(rt.read_node(item, "MISSING")["status"], "missing_node")
        rt.close_session(item)

    def test_export_does_not_overwrite_and_failure_is_structured(self):
        path = self.root / "已存在.inp"
        path.write_text("USER ARTIFACT", encoding="utf-8")
        item = session()
        with self.assertRaises(FileExistsError): rt.export_case(item, 4, path)
        self.assertEqual(path.read_text(), "USER ARTIFACT")
        rt.close_session(item)
        item = session(FakeApp(fail_export=True))
        result = rt.export_case(item, 4, self.root / "failed.inp")
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "export_error")
        rt.close_session(item)

    def worker_command(self, phase, mode="hang"):
        return [sys.executable, str(SCRIPTS / "tests/runtime_fake_worker.py"), "--runtime-dir", str(SCRIPTS), "--phase", phase, "--mode", mode]

    def test_every_blocking_phase_has_external_timeout(self):
        foreign = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(60)"])
        try:
            for phase in ("worker_boot", "creating_com", "opening", "running", "exporting", "saving", "closing"):
                with self.subTest(phase=phase):
                    result = supervisor.run_worker(self.worker_command(phase), run_dir=self.root / phase,
                        stage_timeouts={name: .25 if name == phase else 2 for name in supervisor.DEFAULT_PHASE_TIMEOUTS},
                        lock_path=self.root / (phase + ".lock"), worker_can_create_com=False)
                    self.assertEqual(result["status"], "timeout")
                    self.assertEqual(result["timed_out_phase"], phase)
                    self.assertFalse(result["lifecycle_clean"])
                    self.assertTrue(result["lock_released"])
                    self.assertIsNone(foreign.poll())
                    self.assertNotEqual(result["terminated_processes"][0]["pid"], foreign.pid)
        finally:
            foreign.terminate()
            foreign.wait(timeout=5)

    def test_unknown_com_cleanup_retains_owner_lock(self):
        lock = self.root / "recovery.lock"
        result = supervisor.run_worker(self.worker_command("creating_com"), run_dir=self.root / "run",
            stage_timeouts={"creating_com": .25}, overall_timeout_s=3, lock_path=lock)
        self.assertTrue(result["lock_retained_for_resource_recovery"])
        self.assertFalse(result["next_dispatch_allowed"])
        record = json.loads(lock.read_text())
        self.assertEqual(record["status"], "RESOURCE_RECOVERY_REQUIRED")
        # This worker was synthetic and never created COM. Release this test lease only.
        self.assertTrue(rt.LockLease(lock, record).release())

    def test_forged_stage_does_not_claim_lifecycle(self):
        result = supervisor.run_worker(self.worker_command("finished", "forged"), run_dir=self.root / "forged",
            stage_timeouts={"worker_boot": .3}, lock_path=self.root / "owner.lock", worker_can_create_com=False)
        self.assertEqual(result["status"], "timeout")
        self.assertFalse(result["lifecycle_clean"])

    def test_normal_worker_finishes_and_releases_lease(self):
        result = supervisor.run_worker(self.worker_command("finished", "normal"), run_dir=self.root / "normal",
                                       lock_path=self.root / "owner.lock")
        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["lifecycle_clean"])
        self.assertTrue(result["next_dispatch_allowed"])

    def apw_args(self, skip=False):
        source = self.root / "源文件.bkp"
        source.write_bytes(b"SYNTHETIC SOURCE, NOT ASPEN")
        out = self.root / "evidence"
        out.mkdir()
        return argparse.Namespace(source=str(source), apw_output=[str(self.root / "result.apw")], _run_dir=str(out),
            run_before_save=False, skip_reopen_verify=skip, allow_sibling_bkp_overwrite=False,
            run_timeout=.1, label="SYNTHETIC", prog_id="MOCK")

    def test_apw_mechanical_ok_never_means_simulation_clean(self):
        args = self.apw_args()
        original_mkdtemp = tempfile.mkdtemp
        with mock.patch.object(apw.tempfile, "mkdtemp", side_effect=lambda *a, **k: original_mkdtemp(prefix="scratch_", dir=self.root)):
            summary, code = apw.process_apw(args, session_factory=lambda _: session())
        self.assertEqual(code, 0)
        self.assertTrue(summary["ok"])
        self.assertIsNone(summary["simulation_clean"])
        self.assertFalse(summary["delivery_passed"])
        self.assertTrue(summary["reopen_verify"][0]["exact_output_path_reopened"])
        self.assertTrue(summary["original_source_unchanged"])

    def test_apw_unknown_status_fails_mechanical_verification(self):
        args = self.apw_args()
        counter = []
        def factory(_):
            counter.append(1)
            return session(FakeApp("unknown" if len(counter) == 2 else "completed"))
        original_mkdtemp = tempfile.mkdtemp
        with mock.patch.object(apw.tempfile, "mkdtemp", side_effect=lambda *a, **k: original_mkdtemp(prefix="scratch_", dir=self.root)):
            summary, code = apw.process_apw(args, session_factory=factory)
        self.assertNotEqual(code, 0)
        self.assertFalse(summary["ok"])
        self.assertEqual(summary["reopen_verify"][0]["run_status"], "state_unknown")

    def test_apw_skip_is_diagnostic_only(self):
        args = self.apw_args(skip=True)
        original_mkdtemp = tempfile.mkdtemp
        with mock.patch.object(apw.tempfile, "mkdtemp", side_effect=lambda *a, **k: original_mkdtemp(prefix="scratch_", dir=self.root)):
            summary, code = apw.process_apw(args, session_factory=lambda _: session())
        self.assertEqual(code, 0)
        self.assertTrue(summary["diagnostic_only"])
        self.assertFalse(summary["ok"])
        self.assertFalse(summary["delivery_passed"])
        self.assertFalse(summary["reopen_succeeded"])

    def test_source_output_and_sibling_collisions_rejected(self):
        source = self.root / "source.apw"
        source.write_bytes(b"USER")
        with self.assertRaises(ValueError): apw.preflight(source, [source], False)
        output = self.root / "candidate.apw"
        output.with_suffix(".bkp").write_bytes(b"PROTECTED")
        with self.assertRaises(RuntimeError): apw.preflight(source, [output], False)
        self.assertTrue(apw.preflight(source, [output], True))

    def test_component_template_uses_two_owned_sessions_and_no_run(self):
        inp = self.root / "components.inp"
        inp.write_text("SYNTHETIC COMPONENT INPUT", encoding="ascii")
        sessions = []
        def factory(_):
            item = session()
            sessions.append(item)
            return item
        paths = component.export_template(inp, "components", self.root, session_factory=factory)
        self.assertEqual(len(sessions), 2)
        self.assertTrue(all(item.closed for item in sessions))
        self.assertTrue(all(item.app.Engine.runs == 0 for item in sessions))
        self.assertTrue(all(path.is_file() for path in paths.values()))
        evidence = json.loads((self.root / "components_runtime_evidence.json").read_text())
        self.assertFalse(evidence["delivery_passed"])

    def test_no_edit_template_is_implemented_with_mock_runtime(self):
        source = self.root / "source.bkp"
        source.write_bytes(b"SYNTHETIC")
        run_dir = self.root / "run"
        run_dir.mkdir()
        config = operation.Config(source, run_dir, "run-export", "MOCK", True, "STRICT", run_timeout=.1, worker=True, run_dir=str(run_dir))
        # Existing explicit dependency contract binds this isolated release,
        # not another skill installation that happens to exist on the host.
        config.runtime_path = str(SCRIPTS / 'aspen_runtime.py')
        config.runtime_sha256 = rt.sha256(SCRIPTS / 'aspen_runtime.py')
        env = {"ASPEN_RUNTIME_OWNER_TOKEN": "MOCK-OWNER", "ASPEN_RUNTIME_RUN_ID": "MOCK-RUN", "ASPEN_RUNTIME_STAGE_FILE": str(self.root / "stage.json")}
        fake_session = session()
        with mock.patch.dict(os.environ, env), mock.patch.object(rt, "create_session", return_value=fake_session):
            self.assertEqual(operation.worker_main(config), 0)
        result = json.loads((run_dir / "aspen_operation_summary.json").read_text())
        self.assertTrue(result["operation_completed"])
        self.assertFalse(result["delivery_passed"])
        self.assertTrue(fake_session.closed)

    def test_old_cli_help_works_from_other_directory_without_com(self):
        paths = [SCRIPTS / "apw_saveas_reopen_check.py", SKILLS / "aspen-document-driven-flowsheet/scripts/templates/aspen_operation_template.py",
                 SKILLS / "aspen-document-driven-flowsheet/scripts/templates/aspen_com_lock_watchdog_template.py", SKILLS / "aspen-plus-template/scripts/create_aspen_template.py"]
        for path in paths:
            result = subprocess.run([sys.executable, str(path), "--help"], cwd=self.root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_packaged_dependencies_ignore_unrelated_codex_home(self):
        with mock.patch.dict(os.environ, {'CODEX_HOME': str(self.root / 'not_an_installation')}):
            current_operation = load_module('public_dependency_operation',
                SKILLS / 'aspen-document-driven-flowsheet/scripts/templates/aspen_operation_template.py')
            current_component = load_module('public_dependency_component',
                SKILLS / 'aspen-plus-template/scripts/create_aspen_template.py')
            current_watchdog = load_module('public_dependency_watchdog',
                SKILLS / 'aspen-document-driven-flowsheet/scripts/templates/aspen_com_lock_watchdog_template.py')
            config = current_operation.Config(self.root / 'not-opened.bkp', self.root,
                'diagnostic', 'MOCK', False, 'STRICT')
            loaded = current_operation.load_runtime(config)
        self.assertEqual(Path(loaded.__file__).resolve(), (SCRIPTS / 'aspen_runtime.py').resolve())
        self.assertEqual(current_component._RUNTIME_DIR.resolve(), SCRIPTS.resolve())
        self.assertEqual(current_watchdog._RUNTIME_DIR.resolve(), SCRIPTS.resolve())
        self.assertIs(current_component.runtime, rt)
        self.assertIs(current_watchdog.runtime, rt)

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(RuntimeTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {"synthetic": True, "real_aspen_started": False, "tests_run": result.testsRun, "failures": len(result.failures),
              "errors": len(result.errors), "passed": result.wasSuccessful(), "artifacts": str(RUN_ROOT)}
    rt.atomic_json(RUN_ROOT / "test_report.json", report)
    print(json.dumps(report, ensure_ascii=False))
    raise SystemExit(0 if result.wasSuccessful() else 1)
