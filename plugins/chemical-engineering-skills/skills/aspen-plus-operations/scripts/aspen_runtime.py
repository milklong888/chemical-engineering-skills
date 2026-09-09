"""Shared Aspen operation mechanics. Importing this module never starts COM.

This module has no process-design defaults and cannot grant delivery approval.
Potentially blocking operations must run inside aspen_run_supervisor workers.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
import threading
import time
from typing import Any, Callable
import uuid

RUNTIME_VERSION = "1.0.0-strict-20260909"
DEFAULT_LOCK_PATH = Path(tempfile.gettempdir()) / "CodexAspenRuntime" / "aspen_com.owner.lock"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(data)
    return result.hexdigest().upper()


def artifact(path: Path) -> dict[str, Any]:
    path = path.resolve()
    return {"path": str(path), "exists": path.is_file(), "size": path.stat().st_size if path.is_file() else None,
            "sha256": sha256(path), "mtime_ns": path.stat().st_mtime_ns if path.is_file() else None}


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # A short sibling name avoids exceeding Windows path limits when the final
    # evidence filename is already long. The rename remains same-directory atomic.
    temp = path.with_name("." + uuid.uuid4().hex[:16] + ".tmp")
    try:
        with temp.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def process_identity(pid: int | None = None) -> dict[str, Any]:
    pid = pid or os.getpid()
    result: dict[str, Any] = {"pid": pid, "start_identity": None, "verified": False}
    try:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            kernel.OpenProcess.restype = wintypes.HANDLE
            kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            handle = kernel.OpenProcess(0x1000, False, pid)
            if not handle:
                raise OSError(ctypes.get_last_error(), "OpenProcess")
            try:
                created, exited, system, user = (wintypes.FILETIME() for _ in range(4))
                if not kernel.GetProcessTimes(handle, *(ctypes.byref(v) for v in (created, exited, system, user))):
                    raise OSError(ctypes.get_last_error(), "GetProcessTimes")
                result["start_identity"] = f"windows_filetime:{(created.dwHighDateTime << 32) | created.dwLowDateTime}"
            finally:
                kernel.CloseHandle(handle)
        else:
            stat = Path(f"/proc/{pid}/stat").read_text()
            result["start_identity"] = "proc_start_ticks:" + stat[stat.rfind(")") + 2:].split()[19]
        result["verified"] = True
    except Exception as exc:
        result["error"] = str(exc)
    return result


def _remove_owned_lock_windows(path: Path, expected: dict[str, Any]) -> bool:
    """Validate and delete the same locked file handle, not a replaced pathname."""
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                                  wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.GetFileSizeEx.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_longlong)]
    kernel.ReadFile.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
    kernel.SetFileInformationByHandle.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    # READ + DELETE, sharing READ only. Other writers/renamers cannot swap this
    # file between owner validation and marking this exact handle for deletion.
    handle = kernel.CreateFileW(str(path), 0x80000000 | 0x10000, 0x1, None, 3, 0x80, None)
    if handle == ctypes.c_void_p(-1).value:
        return False
    try:
        size = ctypes.c_longlong()
        if not kernel.GetFileSizeEx(handle, ctypes.byref(size)) or not 0 < size.value <= 1024 * 1024:
            return False
        buffer, count = ctypes.create_string_buffer(size.value), wintypes.DWORD()
        if not kernel.ReadFile(handle, buffer, size.value, ctypes.byref(count), None):
            return False
        current = json.loads(buffer.raw[:count.value].decode("utf-8"))
        if not all(current.get(key) == expected.get(key) for key in ("owner_token", "run_id", "pid", "pid_start_identity")):
            return False
        delete_flag = ctypes.c_ubyte(1)
        return bool(kernel.SetFileInformationByHandle(handle, 4, ctypes.byref(delete_flag), ctypes.sizeof(delete_flag)))
    except (ValueError, UnicodeError):
        return False
    finally:
        kernel.CloseHandle(handle)


@dataclass
class LockLease:
    path: Path
    record: dict[str, Any]
    released: bool = False

    def owns_current_file(self) -> bool:
        try:
            current = json.loads(self.path.read_text(encoding="utf-8"))
            return all(current.get(key) == self.record.get(key) for key in ("owner_token", "run_id", "pid", "pid_start_identity"))
        except (OSError, ValueError):
            return False

    def release(self) -> bool:
        if self.released:
            return False
        current_identity = process_identity()
        if current_identity["pid"] != self.record["pid"] or current_identity["start_identity"] != self.record["pid_start_identity"]:
            return False
        if os.name == "nt":
            if not _remove_owned_lock_windows(self.path, self.record):
                return False
        else:
            if not self.owns_current_file():
                return False
            self.path.unlink()
        self.released = True
        return True

    def mark_resource_blocked(self, reason: str, evidence: dict[str, Any]) -> None:
        if not self.owns_current_file():
            raise RuntimeError("Lock owner changed; refusing to rewrite another lease")
        self.record.update({"status": "RESOURCE_RECOVERY_REQUIRED", "reason": reason, "evidence": evidence})
        atomic_json(self.path, self.record)


def acquire_lock(path: Path = DEFAULT_LOCK_PATH, *, owner: str = "aspen-runtime", run_id: str | None = None,
                 wait_timeout_s: float = 0, owner_token: str | None = None) -> LockLease:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    identity = process_identity()
    if not identity["verified"]:
        raise RuntimeError("Cannot prove current process start identity for lock ownership")
    record = {"schema": "aspen-owner-lock-v1", "owner": owner, "owner_token": owner_token or uuid.uuid4().hex,
              "run_id": run_id or uuid.uuid4().hex, "pid": identity["pid"], "pid_start_identity": identity["start_identity"],
              "created_utc": now(), "status": "OWNED"}
    deadline = time.monotonic() + max(0, wait_timeout_s)
    while True:
        try:
            descriptor = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(record, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            return LockLease(path, record)
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise TimeoutError(f"RESOURCE_BLOCKED: another owner holds {path}")
            time.sleep(min(.1, max(0, deadline - time.monotonic())))


class StageRecorder:
    """Worker heartbeat. Deadlines are enforced by a different process."""
    def __init__(self, path: Path | None = None, run_id: str | None = None, owner_token: str | None = None):
        self.path = path or (Path(os.environ["ASPEN_RUNTIME_STAGE_FILE"]) if os.environ.get("ASPEN_RUNTIME_STAGE_FILE") else None)
        self.run_id = run_id or os.environ.get("ASPEN_RUNTIME_RUN_ID") or uuid.uuid4().hex
        self.owner_token = owner_token or os.environ.get("ASPEN_RUNTIME_OWNER_TOKEN")
        self.sequence = 0
        self.events: list[dict[str, Any]] = []

    def update(self, phase: str, **details: Any) -> dict[str, Any]:
        self.sequence += 1
        row = {"schema": "aspen-worker-stage-v1", "run_id": self.run_id, "owner_token": self.owner_token,
               "pid": os.getpid(), "process_identity": process_identity(), "sequence": self.sequence,
               "phase": phase, "started_epoch": time.time(), "recorded_utc": now(), **details}
        self.events.append(row)
        if self.path:
            atomic_json(self.path, row)
        return row


@dataclass
class AspenSession:
    app: Any
    prog_id: str
    pythoncom: Any
    metadata: dict[str, Any]
    thread_id: int = field(default_factory=threading.get_ident)
    closed: bool = False

    def assert_owner(self) -> None:
        if self.thread_id != threading.get_ident():
            raise RuntimeError("COM objects must remain on their creating thread")
        if self.closed:
            raise RuntimeError("Session is already closed")


def discover_registered_progids() -> list[dict[str, Any]]:
    if os.name != "nt":
        return []
    import winreg
    found = []
    for label, view in (("64bit", winreg.KEY_WOW64_64KEY), ("32bit", winreg.KEY_WOW64_32KEY)):
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "", 0, winreg.KEY_READ | view) as root:
                index = 0
                while True:
                    try:
                        name = winreg.EnumKey(root, index)
                    except OSError:
                        break
                    index += 1
                    if not name.lower().startswith("apwn.document"):
                        continue
                    try:
                        with winreg.OpenKey(root, name + "\\CLSID") as key:
                            clsid = winreg.QueryValue(key, None)
                        found.append({"prog_id": name, "registry_view": label, "clsid": clsid})
                    except OSError:
                        found.append({"prog_id": name, "registry_view": label, "clsid": None})
        except OSError:
            continue
    return found


def select_progid(requested: str, registrations: list[dict[str, Any]], allowed_fallbacks: tuple[str, ...] = ()) -> dict[str, Any]:
    choices = [requested, *allowed_fallbacks]
    registered = {row["prog_id"].lower() for row in registrations if row.get("clsid")}
    for choice in choices:
        if choice.lower() in registered:
            return {"requested": requested, "selected": choice, "fallback_used": choice != requested,
                    "actual_product_version": None, "version_compatibility_proven": False}
    raise RuntimeError(f"Requested COM ProgID not registered: {requested}; no implicit latest-version fallback")


def create_session(prog_id: str = "Apwn.Document", *, dispatch_factory: Callable | None = None,
                   pythoncom_adapter: Any = None) -> AspenSession:
    if pythoncom_adapter is None:
        import pythoncom as pythoncom_adapter
    if dispatch_factory is None:
        import win32com.client
        dispatch_factory = win32com.client.DispatchEx
    pythoncom_adapter.CoInitialize()
    try:
        app = dispatch_factory(prog_id)
    except Exception:
        pythoncom_adapter.CoUninitialize()
        raise
    versions, version_errors = {}, []
    for attribute in ("Version", "VersionNumber"):
        try:
            versions[attribute] = str(getattr(app, attribute))
        except Exception as exc:
            version_errors.append({"attribute": attribute, "error": str(exc)})
    settings = []
    for attribute, value in (("Visible", False), ("SuppressDialogs", True)):
        try:
            setattr(app, attribute, value)
            settings.append({"attribute": attribute, "ok": True})
        except Exception as exc:
            settings.append({"attribute": attribute, "ok": False, "error": str(exc)})
    metadata = {"schema": "aspen-session-v1", "runtime_version": RUNTIME_VERSION, "created_utc": now(),
        "requested_prog_id": prog_id, "actual_dispatch_prog_id": prog_id, "dispatch_method": "DispatchEx",
        "version_readback": versions, "version_readback_errors": version_errors,
        "version_compatibility_proven": False, "settings": settings, "worker_identity": process_identity(),
        "com_server_pid": None, "com_server_process_ownership": "NOT_INFERRED_FROM_NEW_PROCESS_NAME", "coinitialized": True}
    return AspenSession(app, prog_id, pythoncom_adapter, metadata)


def open_case(session: AspenSession, path: Path, *, method: str | None = None) -> dict[str, Any]:
    session.assert_owner()
    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    method = method or ("InitFromFile2" if path.suffix.lower() == ".inp" else "InitFromArchive2")
    if method not in {"InitFromArchive2", "InitFromFile", "InitFromFile2"}:
        raise ValueError("Unregistered open method")
    before = artifact(path)
    started = time.time()
    getattr(session.app, method)(str(path))
    return {"status": "opened", "method": method, "path": str(path), "before": before,
            "after": artifact(path), "started_epoch": started, "finished_epoch": time.time(), "attempt_count": 1}


def read_node(session: AspenSession, path: str) -> dict[str, Any]:
    session.assert_owner()
    row: dict[str, Any] = {"path": path, "exists": False, "value": None, "unit": None}
    try:
        node = session.app.Tree.FindNode(path)
        if node is None:
            return {**row, "status": "missing_node"}
        row.update({"exists": True, "value": node.Value, "status": "read"})
        try:
            row["unit"] = str(node.UnitString)
        except Exception as exc:
            row["unit_error"] = str(exc)
        return row
    except Exception as exc:
        return {**row, "status": "read_error", "error": str(exc)}


def write_input_node(session: AspenSession, path: str, value: Any, *, expected_unit: str | None,
                     allowed_input_paths: tuple[str, ...]) -> dict[str, Any]:
    session.assert_owner()
    if path not in allowed_input_paths or "\\input\\" not in path.lower() or "\\output\\" in path.lower():
        raise ValueError("Only exact caller-authorized input paths can be written")
    before = read_node(session, path)
    if before["status"] != "read":
        raise ValueError("Input node cannot be read before writing")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(value) or expected_unit is None or before["unit"] != expected_unit:
            raise ValueError("Numeric writes require finite values and exact observed units; convert explicitly upstream")
    elif expected_unit is not None and before["unit"] != expected_unit:
        raise ValueError("Unit mismatch")
    session.app.Tree.FindNode(path).Value = value
    after = read_node(session, path)
    return {"status": "written_verified" if after["value"] == value and after["unit"] == before["unit"] else "readback_mismatch",
            "before": before, "requested_value": value, "requested_unit": expected_unit, "conversion": "NONE", "after": after}


def wait_engine_idle(session: AspenSession, timeout_s: float, *, poll_s: float = .1) -> dict[str, Any]:
    session.assert_owner()
    started = time.time()
    deadline = time.monotonic() + timeout_s
    while True:
        try:
            session.pythoncom.PumpWaitingMessages()
            running = session.app.Engine.IsRunning
            if running not in (True, False, 0, 1):
                return {"status": "state_unknown", "state_value": repr(running), "started_epoch": started, "finished_epoch": time.time()}
        except Exception as exc:
            return {"status": "state_unknown", "error": str(exc), "started_epoch": started, "finished_epoch": time.time()}
        if not bool(running):
            return {"status": "completed", "started_epoch": started, "finished_epoch": time.time()}
        if time.monotonic() >= deadline:
            return {"status": "timeout", "started_epoch": started, "finished_epoch": time.time(), "timeout_s": timeout_s}
        time.sleep(min(poll_s, max(0, deadline - time.monotonic())))


def run_case(session: AspenSession, *, timeout_s: float, run_id: str, case_sha256: str | None = None) -> dict[str, Any]:
    session.assert_owner()
    started = time.time()
    try:
        returned = session.app.Engine.Run2(False)
    except Exception as exc:
        return {"status": "com_error", "run_id": run_id, "case_sha256": case_sha256, "started_epoch": started,
                "finished_epoch": time.time(), "error": str(exc), "simulation_clean": None}
    result = wait_engine_idle(session, timeout_s)
    return {**result, "run_id": run_id, "case_sha256": case_sha256, "started_epoch": started,
            "Run2_return": repr(returned), "simulation_clean": None, "delivery_passed": False}


def export_case(session: AspenSession, export_type: int, path: Path) -> dict[str, Any]:
    session.assert_owner()
    path = path.resolve()
    if path.exists():
        raise FileExistsError(f"Export target already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"export_type": export_type, "started_epoch": time.time()}
    try:
        session.app.Export(export_type, str(path))
        row.update({"ok": path.is_file() and path.stat().st_size > 0, "status": "export_returned"})
    except Exception as exc:
        row.update({"ok": False, "status": "export_error", "error": str(exc)})
    return {**row, **artifact(path), "finished_epoch": time.time()}


def close_session(session: AspenSession | None) -> dict[str, Any]:
    if session is None:
        return {"status": "not_created", "closed_cleanly": True, "attempts": []}
    if session.closed:
        return {"status": "already_closed", "closed_cleanly": False, "attempts": []}
    session.assert_owner()
    attempts = []
    try:
        for name, args in (("Close", (False,)), ("Quit", ())):
            started = time.time()
            try:
                getattr(session.app, name)(*args)
                attempts.append({"method": name, "ok": True, "started_epoch": started, "finished_epoch": time.time()})
            except Exception as exc:
                attempts.append({"method": name, "ok": False, "error": str(exc), "started_epoch": started, "finished_epoch": time.time()})
    finally:
        try:
            session.pythoncom.CoUninitialize()
            attempts.append({"method": "CoUninitialize", "ok": True})
        except Exception as exc:
            attempts.append({"method": "CoUninitialize", "ok": False, "error": str(exc)})
        session.closed = True
    return {"status": "closed" if all(row["ok"] for row in attempts) else "close_incomplete",
            "closed_cleanly": all(row["ok"] for row in attempts), "attempts": attempts}


def stage_source(source: Path, run_dir: Path) -> dict[str, Any]:
    """Protect the source and retain same-stem dependencies in a unique worker dir."""
    source, run_dir = source.resolve(), run_dir.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    stage = run_dir / "staged_source"
    stage.mkdir(parents=True, exist_ok=False)
    paths = [source]
    for suffix in (".bkp", ".def", ".appdf", ".ads", ".dlo", ".dll"):
        sibling = source.with_suffix(suffix)
        if sibling != source and sibling.is_file():
            paths.append(sibling)
    rows = []
    for item in paths:
        target = stage / item.name
        shutil.copy2(item, target)
        rows.append({"source": artifact(item), "staged": artifact(target)})
    return {"source": artifact(source), "opened_path": str(stage / source.name), "files": rows,
            "dependency_coverage": "SAME_STEM_KNOWN_SIDECARS_ONLY_CALLER_MUST_DECLARE_OTHER_DEPENDENCIES"}


def snapshot_history(directory: Path) -> dict[str, dict[str, Any]]:
    return {str(p.resolve()): artifact(p) for p in directory.glob("*.his") if p.is_file()}


def capture_history_candidates(directory: Path, before: dict[str, dict[str, Any]], destination: Path,
                               *, run_id: str, case_sha256: str | None) -> list[dict[str, Any]]:
    destination.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in directory.glob("*.his"):
        current = artifact(path)
        old = before.get(str(path.resolve()))
        changed = old is None or old["sha256"] != current["sha256"]
        target = destination / path.name
        if changed and not target.exists():
            shutil.copy2(path, target)
        rows.append({**current, "captured_path": str(target) if target.is_file() else None, "new_or_changed": changed,
            "association": {"verified": False, "run_id": run_id, "case_sha256": case_sha256,
                            "reason": "CHANGED_FILE_CANDIDATE_REQUIRES_SAME_RUN_CONTENT_OR_EVENT_BINDING"}})
    return rows
