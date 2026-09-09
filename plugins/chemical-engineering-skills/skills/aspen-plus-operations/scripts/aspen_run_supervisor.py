"""External per-phase watchdog. Never kills a process by its executable name."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any
import uuid

from aspen_runtime import DEFAULT_LOCK_PATH, acquire_lock, atomic_json, process_identity, now

DEFAULT_PHASE_TIMEOUTS = {"worker_boot": 30.0, "creating_com": 60.0, "opening": 60.0,
    "running": 1800.0, "exporting": 60.0, "saving": 60.0, "closing": 30.0, "finished": 10.0}


def prepare_owned_command(command: list[str], environment: dict[str, str]):
    """Follow CPython's own Windows-venv spawn route, retaining exact Popen PID.

    Source: CPython v3.14.3 Lib/multiprocessing/popen_spawn_win32.py, bpo-35797.
    Only the current interpreter may be redirected; arbitrary child PIDs or
    other launchers are never adopted as owned workers.
    """
    if not command or not all(isinstance(arg, str) for arg in command):
        raise ValueError("Worker command must be a nonempty string argument list")
    actual, env = list(command), dict(environment)
    base = getattr(sys, "_base_executable", sys.executable)
    same = lambda a, b: os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))
    bypass = (os.name == "nt" and sys.implementation.name == "cpython"
              and not same(sys.executable, base) and same(command[0], sys.executable))
    if bypass:
        if not Path(base).is_file():
            raise FileNotFoundError("Current venv base interpreter missing")
        actual[0] = base
        env["__PYVENV_LAUNCHER__"] = sys.executable
    return actual, env, {"venv_redirector_bypassed": bypass,
                         "requested_executable": command[0], "actual_executable": actual[0],
                         "venv_identity": sys.executable if bypass else None}


def stage_belongs_to_worker(candidate, identity, run_id, owner_token):
    child = candidate.get("process_identity", {})
    return (candidate.get("run_id") == run_id and candidate.get("owner_token") == owner_token
            and candidate.get("pid") == identity.get("pid") and identity.get("verified") is True
            and child.get("verified") is True and child.get("pid") == identity.get("pid")
            and bool(identity.get("start_identity"))
            and child.get("start_identity") == identity["start_identity"])


def run_worker(command: list[str], *, run_dir: Path, stage_timeouts: dict[str, float] | None = None,
               overall_timeout_s: float | None = None, lock_path: Path = DEFAULT_LOCK_PATH,
               lock_wait_s: float = 0, environment: dict[str, str] | None = None,
               worker_can_create_com: bool = True) -> dict[str, Any]:
    """Run one owned worker. Unknown COM ownership retains a blocking owner lease.

    worker_can_create_com=False is for offline worker tests only. It never changes
    any simulation evidence gate or enables a COM command in the production CLI.
    """
    run_dir = run_dir.resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    phase_file = run_dir / "worker_stage.json"
    if phase_file.exists() or (run_dir / "supervisor_result.json").exists():
        raise FileExistsError("Supervisor run directory already contains execution evidence")
    budgets = {**DEFAULT_PHASE_TIMEOUTS, **(stage_timeouts or {})}
    if any(value <= 0 for value in budgets.values()):
        raise ValueError("Stage budgets must be positive")
    if overall_timeout_s is not None and overall_timeout_s <= 0:
        raise ValueError("Overall deadline must be positive")
    run_id = uuid.uuid4().hex
    result: dict[str, Any] = {"schema": "aspen-supervisor-result-v1", "run_id": run_id, "started_utc": now(),
        "command": command, "run_dir": str(run_dir), "stage_timeouts_s": budgets, "status": "initializing",
        "forced_termination": False, "terminated_processes": [], "simulation_clean": None, "delivery_passed": False}
    try:
        lease = acquire_lock(lock_path, owner="aspen-run-supervisor", run_id=run_id, wait_timeout_s=lock_wait_s)
    except TimeoutError as exc:
        result.update({"status": "resource_blocked", "error": str(exc), "next_dispatch_allowed": False})
        atomic_json(run_dir / "supervisor_result.json", result)
        return result
    retained = False
    worker = None
    phase, sequence = "worker_boot", 0
    phase_started = overall_started = time.monotonic()
    overall_budget = overall_timeout_s or sum(budgets.values())
    last_stage: dict[str, Any] = {}
    try:
        env = dict(os.environ)
        env.update(environment or {})
        env.update({"ASPEN_RUNTIME_STAGE_FILE": str(phase_file), "ASPEN_RUNTIME_RUN_ID": run_id,
                    "ASPEN_RUNTIME_OWNER_TOKEN": lease.record["owner_token"], "PYTHONDONTWRITEBYTECODE": "1"})
        actual_command, env, launch_metadata = prepare_owned_command(command, env)
        result["launch"] = launch_metadata
        result["actual_command"] = actual_command
        with (run_dir / "worker_stdout.txt").open("wb") as stdout, (run_dir / "worker_stderr.txt").open("wb") as stderr:
            worker = subprocess.Popen(actual_command, cwd=run_dir, env=env, stdout=stdout, stderr=stderr,
                                      creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            owned_identity = process_identity(worker.pid)
            result["owned_worker"] = owned_identity
            while worker.poll() is None:
                try:
                    candidate = json.loads(phase_file.read_text(encoding="utf-8"))
                    if (stage_belongs_to_worker(candidate, owned_identity, run_id, lease.record["owner_token"])
                            and candidate.get("sequence", 0) > sequence):
                        new_phase = candidate.get("phase")
                        if new_phase not in budgets:
                            raise ValueError(f"Unknown worker phase: {new_phase}")
                        sequence = candidate["sequence"]
                        if new_phase != phase:
                            phase, phase_started = new_phase, time.monotonic()
                        last_stage = candidate
                except (FileNotFoundError, json.JSONDecodeError):
                    pass
                if time.monotonic() - phase_started > budgets[phase] or time.monotonic() - overall_started > overall_budget:
                    # Popen owns the exact process handle. No name scan, no inferred
                    # apmain ownership, no termination of unrelated COM servers.
                    worker.terminate()
                    result["forced_termination"] = True
                    result["terminated_processes"].append({**owned_identity, "basis": "EXACT_POPEN_WORKER_HANDLE"})
                    try:
                        worker.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        worker.kill()
                        worker.wait(timeout=5)
                    result.update({"status": "timeout", "timed_out_phase": phase})
                    break
                time.sleep(.05)
            # A very fast worker may exit between polls: consume its final state.
            if phase_file.is_file():
                candidate = json.loads(phase_file.read_text(encoding="utf-8"))
                if stage_belongs_to_worker(candidate, owned_identity, run_id, lease.record["owner_token"]):
                    last_stage = candidate
            result["worker_exit_code"] = worker.returncode
        if result["status"] != "timeout":
            result["status"] = "completed" if worker.returncode == 0 else "worker_failed"
        lifecycle = last_stage.get("phase") == "finished" and last_stage.get("lifecycle_clean") is True
        result.update({"last_stage": last_stage, "lifecycle_clean": lifecycle and not result["forced_termination"]})
        if worker_can_create_com and not lifecycle:
            retained = True
            lease.mark_resource_blocked("WORKER_ENDED_WITHOUT_PROVEN_COM_CLOSE", {"worker": result.get("owned_worker"), "status": result["status"], "last_stage": last_stage})
    except Exception as exc:
        result.update({"status": "supervisor_error", "error": str(exc)})
        if worker is not None and worker.poll() is None:
            worker.terminate()
            worker.wait(timeout=5)
            result["forced_termination"] = True
        if worker is not None and worker_can_create_com:
            retained = True
            lease.mark_resource_blocked("SUPERVISOR_ERROR_WITH_UNRESOLVED_COM_OWNERSHIP", {"error": str(exc)})
    finally:
        result["lock_retained_for_resource_recovery"] = retained
        result["lock_released"] = lease.release() if not retained else False
        result["next_dispatch_allowed"] = not retained and result["lock_released"]
        result["finished_utc"] = now()
        atomic_json(run_dir / "supervisor_result.json", result)
    return result
