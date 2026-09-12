"""Synthetic regression for stage reads; no project cases, subprocesses or COM.

Run directly with the repository's Python, or discover this file with unittest.
The runtime is imported only for ordinary Python helpers; every worker, lease
and process identity used below is an in-memory double.
"""
from __future__ import annotations

from contextlib import ExitStack
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


SCRIPTS = (
    Path(__file__).resolve().parents[1]
    / "plugins/chemical-engineering-skills/skills/aspen-plus-operations/scripts"
)


def _load_local_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


_runtime = _load_local_module(
    "_stage_read_retry_runtime", SCRIPTS / "aspen_runtime.py"
)
with patch.dict(sys.modules, {"aspen_runtime": _runtime}):
    supervisor = _load_local_module(
        "_stage_read_retry_supervisor", SCRIPTS / "aspen_run_supervisor.py"
    )


def win_error(code, *, permission=False, errno=13):
    # Setting winerror explicitly works on non-Windows Python too.
    error = PermissionError(errno, "synthetic access conflict") if permission else OSError()
    error.errno = errno
    error.winerror = code
    return error


class FakeClock:
    def __init__(self):
        self.value = 0.0
        self.sleeps = []

    def monotonic(self):
        return self.value

    def sleep(self, seconds):
        if seconds <= 0 or len(self.sleeps) >= 100:
            raise AssertionError("Invalid sleep or unbounded retry in synthetic test")
        self.sleeps.append(seconds)
        self.value += seconds


class StageReadRetryTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.clock_patch = patch.object(supervisor, "time", self.clock)
        self.clock_patch.start()
        self.addCleanup(self.clock_patch.stop)
        self.path = Path("synthetic-stage.json")

    def test_winerror_whitelist_and_precedence_over_permission_errno(self):
        for code in (5, 32, 33):
            with self.subTest(allowed=code):
                self.assertTrue(supervisor._retryable_stage_read_error(win_error(code)))
        for code in (0, 2, 6, 13, 87):
            with self.subTest(rejected=code):
                self.assertFalse(supervisor._retryable_stage_read_error(win_error(code)))
                # A present non-whitelisted winerror must not fall back to errno.
                self.assertFalse(supervisor._retryable_stage_read_error(
                    win_error(code, permission=True, errno=13)
                ))

    def test_permission_fallback_requires_type_and_allowed_errno(self):
        for number in (5, 13, 32, 33):
            with self.subTest(allowed=number):
                error = PermissionError()
                error.errno = number
                self.assertTrue(supervisor._retryable_stage_read_error(error))
                ordinary = OSError()
                ordinary.errno = number
                self.assertFalse(supervisor._retryable_stage_read_error(ordinary))
        for number in (None, 0, 2, 22):
            with self.subTest(rejected=number):
                error = PermissionError()
                error.errno = number
                self.assertFalse(supervisor._retryable_stage_read_error(error))

    def test_first_read_success_has_no_retry_or_new_evidence(self):
        evidence = [{"preexisting": True}]
        with patch.object(Path, "read_text", return_value='{"sequence": 4}') as read:
            result = supervisor._read_stage_json_with_retry(
                self.path, retry_evidence=evidence
            )
        self.assertEqual(result, {"sequence": 4})
        read.assert_called_once_with(encoding="utf-8")
        self.assertEqual(evidence, [{"preexisting": True}])
        self.assertEqual(self.clock.sleeps, [])

    def test_transient_conflicts_recover_and_preserve_evidence(self):
        evidence = [{"preexisting": True}]
        payload = {"phase": "running", "sequence": 2, "nested": {"value": None}}
        with patch.object(Path, "read_text", side_effect=[
            win_error(32), win_error(5), json.dumps(payload)
        ]) as read:
            result = supervisor._read_stage_json_with_retry(
                self.path, retry_evidence=evidence
            )
        self.assertEqual(result, payload)
        self.assertEqual(read.call_count, 3)
        self.assertEqual(evidence[0], {"preexisting": True})
        self.assertEqual(len(evidence), 2)
        event = evidence[1]
        self.assertEqual(event["path"], str(self.path))
        self.assertEqual(event["outcome"], "succeeded")
        self.assertEqual(event["retries"], 2)
        self.assertAlmostEqual(event["elapsed_s"], sum(self.clock.sleeps))
        self.assertGreater(event["elapsed_s"], 0)

    def test_retry_evidence_is_optional(self):
        with patch.object(Path, "read_text", side_effect=[win_error(33), '{"ok": true}']):
            self.assertEqual(
                supervisor._read_stage_json_with_retry(self.path), {"ok": True}
            )

    def test_persistent_conflict_raises_original_error_at_bounded_fake_deadline(self):
        error, evidence = win_error(33), []
        with patch.object(Path, "read_text", side_effect=error) as read:
            with self.assertRaises(OSError) as caught:
                supervisor._read_stage_json_with_retry(
                    self.path, retry_evidence=evidence,
                    retry_window_s=1.0, retry_interval_s=.4
                )
        self.assertIs(caught.exception, error)
        self.assertEqual(read.call_count, 4)
        self.assertAlmostEqual(self.clock.value, 1.0)
        self.assertLessEqual(max(self.clock.sleeps), .4)
        self.assertAlmostEqual(self.clock.sleeps[-1], .2)
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0]["outcome"], "exhausted")
        self.assertEqual(evidence[0]["retries"], read.call_count)
        self.assertEqual(evidence[0]["winerror"], 33)
        self.assertEqual(evidence[0]["error"], repr(error))
        self.assertAlmostEqual(evidence[0]["elapsed_s"], 1.0)

    def test_non_retryable_oserror_propagates_without_sleep_or_evidence(self):
        for error in (FileNotFoundError("missing"), win_error(2), OSError(22, "invalid")):
            with self.subTest(error=repr(error)):
                evidence = []
                with patch.object(Path, "read_text", side_effect=error) as read:
                    with self.assertRaises(OSError) as caught:
                        supervisor._read_stage_json_with_retry(
                            self.path, retry_evidence=evidence
                        )
                self.assertIs(caught.exception, error)
                read.assert_called_once_with(encoding="utf-8")
                self.assertEqual(evidence, [])
        self.assertEqual(self.clock.sleeps, [])

    def test_bad_json_is_not_retried_or_replaced_by_empty_stage(self):
        for conflict_first in (False, True):
            with self.subTest(conflict_first=conflict_first):
                evidence = []
                reads = [win_error(32), "{bad-json"] if conflict_first else ["{bad-json"]
                before = len(self.clock.sleeps)
                with patch.object(Path, "read_text", side_effect=reads) as read:
                    with self.assertRaises(json.JSONDecodeError):
                        supervisor._read_stage_json_with_retry(
                            self.path, retry_evidence=evidence
                        )
                self.assertEqual(read.call_count, len(reads))
                self.assertEqual(len(self.clock.sleeps) - before, int(conflict_first))
                if not conflict_first:
                    self.assertEqual(evidence, [])


class WorkerStageReadEvidenceTests(unittest.TestCase):
    def run_synthetic_worker(self, *, exit_after_poll=2, faults=None, persistent=None):
        """Exercise real run_worker/read logic, replacing all process-side effects."""
        clock = FakeClock()
        identity = {"pid": 424242, "verified": True, "start_identity": "synthetic-start"}
        lease = SimpleNamespace(
            record={"owner_token": "synthetic-owner"},
            release=Mock(return_value=True), mark_resource_blocked=Mock()
        )
        faults = {name: list(values) for name, values in (faults or {}).items()}
        reads = {"poll": 0, "final": 0}
        original_read_text = Path.read_text
        processes = []

        class SyntheticProcess:
            pid = identity["pid"]

            def __init__(self, environment):
                self.returncode = None
                self.polls = 0
                self.terminated = False
                self.environment = environment
                self.stage_path = Path(environment["ASPEN_RUNTIME_STAGE_FILE"])
                self.write_stage("running", sequence=1)

            def write_stage(self, phase, *, sequence):
                self.stage_path.write_text(json.dumps({
                    "run_id": self.environment["ASPEN_RUNTIME_RUN_ID"],
                    "owner_token": self.environment["ASPEN_RUNTIME_OWNER_TOKEN"],
                    "pid": self.pid, "process_identity": identity,
                    "phase": phase, "sequence": sequence,
                    "lifecycle_clean": phase == "finished"
                }), encoding="utf-8")

            def poll(self):
                self.polls += 1
                if self.polls > 10:
                    raise AssertionError("Unbounded synthetic worker polling")
                if (self.returncode is None and exit_after_poll is not None
                        and self.polls >= exit_after_poll):
                    self.returncode = 0
                    self.write_stage("finished", sequence=2)
                return self.returncode

            def terminate(self):
                self.terminated = True
                self.returncode = -15

            def kill(self):
                raise AssertionError("Synthetic terminate should be sufficient")

            def wait(self, timeout=None):
                return self.returncode

        def spawn(command, **kwargs):
            process = SyntheticProcess(kwargs["env"])
            processes.append(process)
            return process

        def read_with_fault(path, *args, **kwargs):
            if processes and path == processes[0].stage_path:
                location = "final" if processes[0].returncode is not None else "poll"
                reads[location] += 1
                if persistent == location:
                    raise win_error(32)
                if faults.get(location):
                    value = faults[location].pop(0)
                    if isinstance(value, BaseException):
                        raise value
                    return value
            return original_read_text(path, *args, **kwargs)

        popen = Mock(side_effect=spawn)
        fake_subprocess = SimpleNamespace(
            Popen=popen, CREATE_NO_WINDOW=0, TimeoutExpired=subprocess.TimeoutExpired
        )
        with tempfile.TemporaryDirectory(prefix="stage-retry-test-") as temporary:
            directory = Path(temporary)
            with ExitStack() as stack:
                stack.enter_context(patch.object(supervisor, "time", clock))
                stack.enter_context(patch.object(supervisor, "acquire_lock", return_value=lease))
                stack.enter_context(patch.object(supervisor, "process_identity", return_value=identity))
                stack.enter_context(patch.object(supervisor, "prepare_owned_command",
                    side_effect=lambda command, env: (command, env, {"synthetic": True})))
                stack.enter_context(patch.object(supervisor, "subprocess", fake_subprocess))
                stack.enter_context(patch.object(Path, "read_text", new=read_with_fault))
                result = supervisor.run_worker(
                    ["synthetic-worker-never-executed"],
                    run_dir=directory, lock_path=directory / "synthetic.lock",
                    overall_timeout_s=5.0
                )
            persisted = json.loads(original_read_text(
                directory / "supervisor_result.json", encoding="utf-8"
            ))
        popen.assert_called_once()
        self.assertEqual(result, persisted)
        return result, reads, lease, processes[0], clock

    def test_poll_and_final_recovery_both_survive_in_persisted_result(self):
        result, reads, lease, process, _ = self.run_synthetic_worker(
            faults={"poll": [win_error(32)], "final": [win_error(5)]}
        )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["last_stage"]["phase"], "finished")
        self.assertTrue(result["lifecycle_clean"])
        self.assertEqual(reads, {"poll": 2, "final": 2})
        evidence = result["stage_read_retry_evidence"]
        self.assertEqual([event["outcome"] for event in evidence], ["succeeded", "succeeded"])
        self.assertEqual([event["retries"] for event in evidence], [1, 1])
        self.assertTrue(all(event["path"].endswith("worker_stage.json") for event in evidence))
        self.assertTrue(result["lock_released"])
        self.assertFalse(process.terminated)
        lease.mark_resource_blocked.assert_not_called()

    def test_fast_exit_still_retries_final_snapshot_and_preserves_evidence(self):
        result, reads, _, _, _ = self.run_synthetic_worker(
            exit_after_poll=1, faults={"final": [win_error(33)]}
        )
        self.assertEqual(reads, {"poll": 0, "final": 2})
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["last_stage"]["phase"], "finished")
        self.assertEqual(result["stage_read_retry_evidence"][0]["outcome"], "succeeded")

    def test_exhaustion_at_either_call_site_survives_and_retains_unresolved_lease(self):
        for location in ("poll", "final"):
            with self.subTest(location=location):
                result, reads, lease, process, clock = self.run_synthetic_worker(
                    exit_after_poll=None if location == "poll" else 1,
                    persistent=location
                )
                self.assertEqual(result["status"], "supervisor_error")
                evidence = result["stage_read_retry_evidence"]
                self.assertEqual(len(evidence), 1)
                self.assertEqual(evidence[0]["outcome"], "exhausted")
                self.assertEqual(evidence[0]["retries"], reads[location])
                self.assertAlmostEqual(evidence[0]["elapsed_s"], 1.0)
                self.assertAlmostEqual(clock.value, 1.0)
                self.assertTrue(result["lock_retained_for_resource_recovery"])
                self.assertFalse(result["next_dispatch_allowed"])
                lease.release.assert_not_called()
                lease.mark_resource_blocked.assert_called_once()
                self.assertEqual(process.terminated, location == "poll")

    def test_bad_json_keeps_existing_poll_vs_final_failure_behavior(self):
        for location in ("poll", "final"):
            with self.subTest(location=location):
                result, reads, lease, _, _ = self.run_synthetic_worker(
                    exit_after_poll=2 if location == "poll" else 1,
                    faults={location: ["{bad-json"]}
                )
                self.assertNotIn("stage_read_retry_evidence", result)
                self.assertEqual(reads[location], 1)
                if location == "poll":
                    # The polling site already tolerates one incomplete JSON snapshot.
                    self.assertEqual(result["status"], "completed")
                    self.assertEqual(result["last_stage"]["phase"], "finished")
                    lease.mark_resource_blocked.assert_not_called()
                else:
                    # The final site does not silently replace malformed final state.
                    self.assertEqual(result["status"], "supervisor_error")
                    self.assertFalse(result["next_dispatch_allowed"])
                    lease.mark_resource_blocked.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
