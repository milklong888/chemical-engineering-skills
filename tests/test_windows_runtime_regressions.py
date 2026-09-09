"""Narrow runtime regressions: no real COM or engineering software."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "plugins/chemical-engineering-skills/skills/aspen-plus-operations/scripts"
sys.path.insert(0, str(SCRIPTS))
import aspen_runtime as runtime
import aspen_run_supervisor as supervisor


class RuntimeRegressionTests(unittest.TestCase):
    def test_transient_windows_replace_share_conflict(self):
        with tempfile.TemporaryDirectory(prefix="ar-share-") as temporary:
            path = Path(temporary) / "stage.json"
            path.write_text('{"old":true}')
            original = os.replace
            busy = PermissionError("synthetic Windows reader sharing conflict")
            busy.winerror = 5
            attempts = []
            def replace(source, target):
                attempts.append(1)
                if len(attempts) == 1:
                    raise busy
                return original(source, target)
            with mock.patch.object(runtime.os, "replace", side_effect=replace):
                runtime.atomic_json(path, {"new": True})
            self.assertEqual(json.loads(path.read_text()), {"new": True})
            self.assertEqual(len(attempts), 2)

    def test_other_replace_error_is_not_hidden(self):
        with tempfile.TemporaryDirectory(prefix="ar-error-") as temporary:
            path = Path(temporary) / "stage.json"
            error = OSError("synthetic disk failure")
            with mock.patch.object(runtime.os, "replace", side_effect=error) as mocked:
                with self.assertRaises(OSError):
                    runtime.atomic_json(path, {"new": True})
            self.assertEqual(mocked.call_count, 1)
            self.assertFalse(path.exists())

    def test_venv_direct_launch_keeps_context_and_owned_pid(self):
        code = "import json,os,sys;print(json.dumps({'pid':os.getpid(),'prefix':sys.prefix,'executable':sys.executable}))"
        command, env, metadata = supervisor.prepare_owned_command([sys.executable, "-c", code], dict(os.environ))
        process = subprocess.Popen(command, env=env, stdout=subprocess.PIPE, text=True)
        out, _ = process.communicate(timeout=15)
        self.assertEqual(process.returncode, 0)
        row = json.loads(out)
        self.assertEqual(process.pid, row["pid"])
        self.assertEqual(os.path.normcase(sys.prefix), os.path.normcase(row["prefix"]))
        self.assertEqual(os.path.normcase(sys.executable), os.path.normcase(row["executable"]))

    def test_other_executable_is_not_rewritten(self):
        command = [str(SCRIPTS / "not-python.exe"), "--flag"]
        rewritten, env, metadata = supervisor.prepare_owned_command(command, {})
        self.assertEqual(rewritten, command)
        self.assertFalse(metadata["venv_redirector_bypassed"])
        self.assertNotIn("__PYVENV_LAUNCHER__", env)

    def test_stage_start_identity_must_match(self):
        identity = {"pid": 123, "verified": True, "start_identity": "SAME_OS_START"}
        row = {"pid": 123, "run_id": "run", "owner_token": "token", "process_identity": dict(identity)}
        self.assertTrue(supervisor.stage_belongs_to_worker(row, identity, "run", "token"))
        row["process_identity"]["start_identity"] = "ANOTHER_OS_START"
        self.assertFalse(supervisor.stage_belongs_to_worker(row, identity, "run", "token"))
        row["process_identity"] = dict(identity)
        row["pid"] = 999
        self.assertFalse(supervisor.stage_belongs_to_worker(row, identity, "run", "token"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
