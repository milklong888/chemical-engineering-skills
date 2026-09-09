"""Local-only gateway to the bundled original equipment Agent JSON protocol.

No matcher, source data, schema or acceptance rule is reimplemented here.
Remote model calls and live Aspen import remain explicit separate interfaces.
The resident child uses a protocol pipe (never inherited interactive stdin).
"""
from __future__ import annotations

import ast
from collections import deque
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import queue
import subprocess
import sys
import threading
import uuid

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backends/equipment"
AGENT = BACKEND / "app/equipment_design_agent.py"
LOCAL_OPERATIONS = frozenset({
    "capabilities", "schema_get", "catalog", "auto_match", "manual_match",
    "manual_batch", "render_report", "organize_answer", "customer_export",
    "knowledge_search", "aspen_derive", "pfd_build", "pfd_override",
    "pfd_recalculate", "hybrid_prepare", "hybrid_continue", "llm_apply", "selftest",
})
SEPARATE_OPERATIONS = frozenset({"aspen_import", "hybrid_run", "llm_review"})
SECRET_FIELDS = frozenset({"api_key", "api_key_env", "password", "access_token",
                           "llm_config", "endpoint", "base_url", "authorization"})
MAX_RESPONSE_CHARACTERS = 64 * 1024 * 1024


def _registered_aliases():
    tree = ast.parse(AGENT.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "OPERATION_ALIASES" for t in node.targets):
            value = ast.literal_eval(node.value)
            if isinstance(value, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in value.items()):
                return value
    raise ValueError("BUNDLED_OPERATION_REGISTRY_UNAVAILABLE")


def available_operations():
    aliases = _registered_aliases()
    return {"operations": sorted(LOCAL_OPERATIONS),
            "operation_aliases": {k: v for k, v in aliases.items() if v in LOCAL_OPERATIONS},
            "separate_interfaces": sorted(SEPARATE_OPERATIONS),
            "network_allowed": False, "com_allowed": False,
            "authority": "original bundled Agent schemas and validators"}


def describe_policy():
    """Discovery only: no child process, credential lookup or network access."""
    reasons = {
        "aspen_import": "Optional isolated Aspen COM import needs a separately explicit authorization and licensed environment.",
        "hybrid_run": "Provider execution can perform model/network I/O; use local prepare/continue here and a separately authorized provider interface.",
        "llm_review": "Legacy provider-executing compatibility route; local validated continuation/application remain available.",
    }
    aliases = _registered_aliases()
    return {"schema": "equipment-local-gateway-policy-v1", **available_operations(),
            "excluded_operations": [{"operation": operation,
                "aliases": sorted(key for key, value in aliases.items() if value == operation),
                "reason": reasons[operation]} for operation in sorted(SEPARATE_OPERATIONS)],
            "resident_lifecycle": {"construction": "lazy_no_process", "request_order": "serialized_by_instance_lock",
                                   "shutdown": "close_stdin_then_wait_owned_process", "global_process": False}}


def local_environment():
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("EQUIPMENT_DESIGN_LLM_")
           and k not in {"EQUIPMENT_BACKEND_ALLOW_COM", "PYTHONPATH", "PYTHONHOME", "PYTHONINSPECT", "PYTHONSTARTUP"}}
    env.update(PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
    return env


def _command(environment):
    executable = sys.executable
    # CPython's Windows venv redirector has a different PID from its worker.
    # Use the same direct-base-executable contract as multiprocessing does.
    if os.name == "nt" and sys.prefix != sys.base_prefix:
        base = getattr(sys, "_base_executable", None)
        if not base or not Path(base).is_file():
            raise ValueError("VENV_DIRECT_WORKER_EXECUTABLE_UNAVAILABLE")
        environment["__PYVENV_LAUNCHER__"] = sys.executable
        executable = base
    return [executable, "-B", "-X", "utf8", str(AGENT), "--session-jsonl"]


def _canonical_hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                   separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest().upper()


def _authority_snapshot():
    """Detect drift for one resident process; native startup verification stays on."""
    identities = {}
    for relative, path_key in (("app/source_code_manifest.json", "source_path"),
                               ("runtime_asset_manifest.json", "runtime_path")):
        manifest_path = BACKEND / relative
        raw = manifest_path.read_bytes()
        identities[relative] = hashlib.sha256(raw).hexdigest().upper()
        manifest = json.loads(raw)
        for row in manifest["files"]:
            locator = row[path_key]
            path = PurePosixPath(locator)
            if not isinstance(locator, str) or path.is_absolute() or ".." in path.parts or ":" in locator or "\\" in locator:
                raise ValueError("INVALID_BUNDLED_AUTHORITY_PATH")
            resolved = (BACKEND / locator).resolve()
            if not resolved.is_relative_to(BACKEND.resolve()):
                raise ValueError("AUTHORITY_PATH_ESCAPES_BACKEND")
            data = resolved.read_bytes()
            digest = hashlib.sha256(data).hexdigest().upper()
            if digest != str(row["sha256"]).upper() or len(data) != row["size_bytes"]:
                raise ValueError("BUNDLED_AUTHORITY_FILE_MISMATCH: " + locator)
            identities[locator] = digest
    return _canonical_hash(identities)


def _validate_request(request):
    if not isinstance(request, dict):
        raise ValueError("REQUEST_MUST_BE_OBJECT")
    aliases = _registered_aliases()
    requested = str(request.get("operation", "")).strip()
    operation = aliases.get(requested, requested)
    if operation not in LOCAL_OPERATIONS:
        raise ValueError("OPERATION_NOT_LOCAL: use its explicitly authorized separate interface")

    def inspect(value):
        if isinstance(value, dict):
            for key, child in value.items():
                normalized = str(key).casefold().replace("-", "_")
                if normalized in SECRET_FIELDS or normalized.startswith("equipment_design_llm_"):
                    raise ValueError("REMOTE_OR_CREDENTIAL_FIELD_FORBIDDEN")
                if normalized == "operation" and aliases.get(str(child).strip(), str(child).strip()) in SEPARATE_OPERATIONS:
                    raise ValueError("NESTED_REMOTE_OR_COM_OPERATION_FORBIDDEN")
                if normalized in {"output_path", "output_dir"} and child:
                    if Path(str(child)).expanduser().resolve().is_relative_to(ROOT.resolve()):
                        raise ValueError("OUTPUT_MUST_NOT_MUTATE_PRODUCT_TREE")
                inspect(child)
        elif isinstance(value, list):
            for child in value:
                inspect(child)
    inspect(request)
    # Detached prepared/step/proposal files are the same explicit input surface.
    payload = request.get("payload")
    for key in ("prepared_path", "step_output_path", "proposal_path"):
        raw = payload.get(key) if isinstance(payload, dict) else None
        if raw:
            inspect(json.loads(Path(str(raw)).expanduser().read_text(encoding="utf-8-sig")))
    copied = json.loads(json.dumps(request, ensure_ascii=False, allow_nan=False))
    if not copied.get("request_id"):
        copied["request_id"] = "GATEWAY_" + uuid.uuid4().hex
    return copied, operation


class EquipmentSession:
    """One owned original Agent process, sequential requests and immutable authority."""
    def __init__(self, timeout_s=300):
        if not isinstance(timeout_s, (int, float)) or not 0 < timeout_s <= 7200:
            raise ValueError("timeout_s must be in (0, 7200]")
        self.timeout_s = timeout_s
        self._process = None
        self._closed = False
        self._lock = threading.RLock()
        self._authority = None
        self._stderr = deque(maxlen=8)
        self._stderr_thread = None

    @property
    def pid(self):
        return self._process.pid if self._process else None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _start(self):
        if self._closed:
            raise ValueError("SESSION_CLOSED")
        if self._process is None:
            self._authority = _authority_snapshot()
            env = local_environment()
            self._process = subprocess.Popen(_command(env), stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                errors="strict", cwd=ROOT, env=env, bufsize=1)
            def drain():
                try:
                    while chunk := self._process.stderr.read(4096):
                        self._stderr.append(chunk)
                except (OSError, ValueError):
                    pass
            self._stderr_thread = threading.Thread(target=drain, daemon=True)
            self._stderr_thread.start()

    def request(self, request):
        copied, operation = _validate_request(request)
        with self._lock:
            self._start()
            self._check_authority()
            result_queue = queue.Queue(maxsize=1)
            def exchange():
                try:
                    self._process.stdin.write(json.dumps(copied, ensure_ascii=False, allow_nan=False) + "\n")
                    self._process.stdin.flush()
                    line = self._process.stdout.readline(MAX_RESPONSE_CHARACTERS + 1)
                    if not line or not line.endswith("\n") or len(line) > MAX_RESPONSE_CHARACTERS:
                        raise ValueError("INVALID_OR_INCOMPLETE_AGENT_RESPONSE")
                    result_queue.put(json.loads(line))
                except Exception as exc:
                    result_queue.put(exc)
            worker = threading.Thread(target=exchange, daemon=True)
            worker.start()
            try:
                response = result_queue.get(timeout=self.timeout_s)
            except queue.Empty:
                self.close(force=True)
                worker.join(timeout=1)
                raise TimeoutError("OWNED_EQUIPMENT_WORKER_TIMEOUT") from None
            if isinstance(response, Exception):
                self.close(force=True)
                raise ValueError("EQUIPMENT_PROTOCOL_FAILED") from response
            worker.join(timeout=1)
            self._check_authority()
            aliases = _registered_aliases()
            response_operation = str(response.get("operation", "")).strip() if isinstance(response, dict) else ""
            if (not isinstance(response, dict)
                    or response.get("schema") != "equipment-design-agent-response-v1"
                    or response.get("request_id") != str(copied["request_id"])
                    or response.get("request_sha256") != _canonical_hash(copied)
                    or aliases.get(response_operation, response_operation) != operation
                    or type(response.get("exit_code")) is not int):
                self.close(force=True)
                raise ValueError("AGENT_RESPONSE_IDENTITY_MISMATCH")
            return {"backend_exit_code": response["exit_code"], "response": response,
                    "gateway": {"worker_pid": self.pid, "authority_sha256": self._authority,
                                "network_allowed": False, "com_allowed": False}}

    def _check_authority(self):
        try:
            if _authority_snapshot() != self._authority:
                raise ValueError("RESIDENT_AUTHORITY_CHANGED")
        except (ValueError, OSError, KeyError, TypeError):
            self.close(force=True)
            raise

    def batch(self, requests):
        results = []
        with self._lock:
            for request in requests:
                try:
                    results.append(self.request(request))
                except (ValueError, OSError, TimeoutError, TypeError) as exc:
                    results.append({"backend_exit_code": 2, "response": None,
                                    "gateway_error": {"code": type(exc).__name__, "message": str(exc)}})
        return results

    def close(self, force=False):
        with self._lock:
            self._closed = True
            process = self._process
            if process is None:
                return
            if process.poll() is None:
                if force:
                    process.terminate()  # This Popen handle only; never image-name/taskkill.
                else:
                    try:
                        process.stdin.close()  # Original resident Agent exits on EOF.
                    except (OSError, ValueError):
                        pass
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()  # Still only this owned process handle.
                    process.wait(timeout=5)
            for stream in (process.stdin, process.stdout, process.stderr):
                try:
                    stream.close()
                except (OSError, ValueError):
                    pass
            if self._stderr_thread is not None:
                self._stderr_thread.join(timeout=1)


def equipment(request, timeout_s=300):
    with EquipmentSession(timeout_s=timeout_s) as session:
        result = session.request(request)
        return {"backend_exit_code": result["backend_exit_code"], "response": result["response"]}


def equipment_batch(requests, timeout_s=300):
    with EquipmentSession(timeout_s=timeout_s) as session:
        return session.batch(requests)
