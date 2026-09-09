#!/usr/bin/env python3
"""Compatibility owner-lock probe using the shared runtime. COM execution needs
aspen_run_supervisor: an in-thread idle loop cannot bound blocked COM startup.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import time
from typing import Any

_RUNTIME_DIR = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "skills/aspen-plus-operations/scripts"
if not (_RUNTIME_DIR / "aspen_runtime.py").is_file():
    raise ImportError(f"Shared Aspen runtime missing: {_RUNTIME_DIR}")
sys.path.insert(0, str(_RUNTIME_DIR))
import aspen_runtime as runtime
_LEASES: dict[str, runtime.LockLease] = {}

def existing_aspen_pids() -> list[int]:
    """Diagnostic inventory only; never termination ownership proof."""
    try:
        import psutil
        return [row.info["pid"] for row in psutil.process_iter(["pid", "name"])
                if str(row.info.get("name", "")).lower() in {"apmain.exe", "apwn.exe", "aspenplus.exe"}]
    except ImportError:
        raise RuntimeError("Process inventory unavailable; cannot assume no Aspen processes")

def acquire_lock(lock_path: Path, owner: str, allow_existing_apmain: bool) -> dict[str, Any]:
    running = existing_aspen_pids()
    if running and not allow_existing_apmain:
        raise RuntimeError(f"Existing Aspen processes require explicit isolation review: {running}")
    lease = runtime.acquire_lock(lock_path, owner=owner)
    _LEASES[str(lock_path.resolve())] = lease
    return {**lease.record, "existing_aspen_pids_at_lock": running,
            "existing_processes_are_not_owned": True, "runtime_version": runtime.RUNTIME_VERSION}

def release_lock(lock_path: Path) -> bool:
    lease = _LEASES.get(str(lock_path.resolve()))
    return lease.release() if lease else False

def wait_engine_idle(aspen: Any, timeout_s: int, pump_messages: Any | None = None) -> str:
    class Adapter:
        @staticmethod
        def PumpWaitingMessages():
            if pump_messages:
                pump_messages()
    session = aspen if isinstance(aspen, runtime.AspenSession) else runtime.AspenSession(aspen, "LEGACY_BORROWED_IDLE_PROBE", Adapter(), {"owned": False})
    result = runtime.wait_engine_idle(session, timeout_s)
    return {"completed": "engine_idle", "state_unknown": "engine_state_unknown", "timeout": f"engine_timeout_after_{timeout_s}s"}.get(result["status"], result["status"])

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock-path", required=True)
    parser.add_argument("--owner", default="project-aspen-script")
    parser.add_argument("--allow-existing-apmain", action="store_true")
    parser.add_argument("--hold-seconds", type=float, default=0)
    args = parser.parse_args()
    lock_path = Path(args.lock_path)
    record = acquire_lock(lock_path, args.owner, args.allow_existing_apmain)
    try:
        print(json.dumps({"acquired": record}, ensure_ascii=False))
        time.sleep(max(0, args.hold_seconds))
    finally:
        released = release_lock(lock_path)
        print(json.dumps({"released": released}, ensure_ascii=False))
    return 0 if released else 2

if __name__ == "__main__":
    raise SystemExit(main())
