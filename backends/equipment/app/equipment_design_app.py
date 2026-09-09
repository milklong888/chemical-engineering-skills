from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


FROZEN_ROOT = getattr(sys, "_MEIPASS", None)
if FROZEN_ROOT:
    PACKAGE_ROOT = Path(FROZEN_ROOT).resolve()
    APP_DIR = PACKAGE_ROOT / "app"
    DATA_ROOT = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "EquipmentDesignGraphApp"
    OUTPUT_ROOT = DATA_ROOT / "sessions"
else:
    APP_DIR = Path(__file__).resolve().parent
    PACKAGE_ROOT = APP_DIR.parent
    DATA_ROOT = PACKAGE_ROOT / "outputs"
    OUTPUT_ROOT = DATA_ROOT / "app_sessions"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import app_core  # noqa: E402
import llm_bridge  # noqa: E402


REPORT_STATUS_SCHEMA = "equipment-design-report-status-v1"


def resource_root() -> Path:
    return PACKAGE_ROOT


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _load_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root is not an object: {path}")
    return value


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _path_record(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"path": None, "exists": False, "sha256": None, "size_bytes": 0}
    resolved = path.expanduser().resolve()
    is_file = resolved.is_file()
    return {
        "path": str(resolved),
        "exists": is_file,
        "sha256": _sha256_file(resolved) if is_file else None,
        "size_bytes": int(resolved.stat().st_size) if is_file else 0,
    }


def _report_content_counts(presentation: Mapping[str, Any]) -> dict[str, int]:
    equipment = presentation.get("equipment")
    rows = equipment if isinstance(equipment, list) else []
    return {
        "equipment_count": len(rows),
        "parameter_group_count": sum(
            len(item.get("parameter_groups", []))
            for item in rows
            if isinstance(item, Mapping) and isinstance(item.get("parameter_groups"), list)
        ),
        "calculation_chain_count": sum(
            len(item.get("calculation_chain", []))
            for item in rows
            if isinstance(item, Mapping) and isinstance(item.get("calculation_chain"), list)
        ),
        "candidate_count": sum(
            len(item.get("candidates", []))
            for item in rows
            if isinstance(item, Mapping) and isinstance(item.get("candidates"), list)
        ),
    }


def build_report_status(
    request_path: Path,
    response_path: Path,
    *,
    process_exit_code: int,
    execution_error: str | None = None,
) -> dict[str, Any]:
    """Build a read-only machine status for a GUI Agent report invocation.

    The sidecar never changes the request, deterministic result, or report. It
    checks independently persisted artifacts so callers do not need to scrape
    the window to distinguish normal content from an empty/failed invocation.
    """

    checks: list[dict[str, Any]] = []

    def check(check_id: str, passed: bool, detail: Any) -> None:
        checks.append({"id": check_id, "pass": bool(passed), "detail": detail})

    request: dict[str, Any] | None = None
    response: dict[str, Any] | None = None
    request_error: str | None = None
    response_error: str | None = None
    try:
        request = _load_json_object(request_path)
    except Exception as exc:
        request_error = str(exc)
    try:
        response = _load_json_object(response_path)
    except Exception as exc:
        response_error = str(exc)

    request_record = _path_record(request_path)
    response_record = _path_record(response_path)
    check(
        "request_readable_render_report",
        request is not None
        and request.get("schema") == "equipment-design-agent-request-v1"
        and request.get("operation") in {"render_report", "report.render"},
        {
            "error": request_error,
            "schema": request.get("schema") if request else None,
            "operation": request.get("operation") if request else None,
        },
    )
    check(
        "response_readable",
        response is not None and response.get("schema") == "equipment-design-agent-response-v1",
        {
            "error": response_error,
            "schema": response.get("schema") if response else None,
        },
    )

    request_sha256 = _canonical_sha256(request) if request is not None else None
    response_request_sha256 = response.get("request_sha256") if response else None
    check(
        "request_response_identity",
        request_sha256 is not None and request_sha256 == response_request_sha256,
        {"request_sha256": request_sha256, "response_request_sha256": response_request_sha256},
    )

    machine_state = response.get("machine_state") if response else None
    check(
        "agent_completed",
        execution_error is None
        and int(process_exit_code) == 0
        and response is not None
        and response.get("ok") is True
        and response.get("status") == "PASS"
        and int(response.get("exit_code", -1)) == 0
        and isinstance(machine_state, Mapping)
        and machine_state.get("deterministic_authority") is True,
        {
            "execution_error": execution_error,
            "process_exit_code": int(process_exit_code),
            "response_exit_code": response.get("exit_code") if response else None,
            "machine_state": machine_state,
        },
    )

    result = response.get("result") if response else None
    presentation = result.get("presentation") if isinstance(result, Mapping) else None
    equipment = presentation.get("equipment") if isinstance(presentation, Mapping) else None
    counts = _report_content_counts(presentation if isinstance(presentation, Mapping) else {})
    check(
        "deterministic_presentation",
        isinstance(presentation, Mapping)
        and presentation.get("schema") == "equipment-design-presentation-v1"
        and presentation.get("deterministic") is True
        and presentation.get("llm_used") is False
        and isinstance(equipment, list)
        and int(presentation.get("equipment_count", -1)) == len(equipment)
        and len(equipment) > 0,
        {
            "schema": presentation.get("schema") if isinstance(presentation, Mapping) else None,
            "deterministic": presentation.get("deterministic") if isinstance(presentation, Mapping) else None,
            "llm_used": presentation.get("llm_used") if isinstance(presentation, Mapping) else None,
            **counts,
        },
    )
    check(
        "normal_equipment_content",
        isinstance(equipment, list)
        and bool(equipment)
        and counts["parameter_group_count"] > 0
        and all(
            isinstance(item, Mapping)
            and bool(str(item.get("equipment_id") or "").strip())
            and isinstance(item.get("header"), Mapping)
            and isinstance(item.get("status_axes"), Mapping)
            and isinstance(item.get("parameter_groups"), list)
            and bool(item.get("parameter_groups"))
            for item in equipment
        ),
        counts,
    )

    output_text = str(result.get("output_path") or "") if isinstance(result, Mapping) else ""
    report_path = Path(output_text).expanduser().resolve() if output_text else None
    report_record = _path_record(report_path)
    report_text = ""
    report_read_error: str | None = None
    if report_path is not None and report_path.is_file():
        try:
            report_text = report_path.read_text(encoding="utf-8")
        except Exception as exc:
            report_read_error = str(exc)
    artifact_hashes = {
        str(item.get("sha256") or "")
        for item in (response.get("artifacts", []) if response else [])
        if isinstance(item, Mapping)
    }
    report_format = str(result.get("format") or "") if isinstance(result, Mapping) else ""
    html_markers_ok = (
        report_format != "html"
        or (
            "<html" in report_text.casefold()
            and "</html>" in report_text.casefold()
            and "eq-answer" in report_text
        )
    )
    check(
        "report_artifact",
        report_path is not None
        and report_record["exists"] is True
        and int(report_record["size_bytes"]) > 0
        and report_record["sha256"] in artifact_hashes
        and report_read_error is None
        and html_markers_ok,
        {
            **report_record,
            "format": report_format,
            "read_error": report_read_error,
            "hash_registered_in_response": report_record["sha256"] in artifact_hashes,
            "html_markers_ok": html_markers_ok,
        },
    )

    passed = bool(checks) and all(item["pass"] for item in checks)
    return {
        "schema": REPORT_STATUS_SCHEMA,
        "status": "PASS" if passed else "FAIL",
        "normal_content": passed,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "diagnostic_channel": "READ_ONLY_AUTOMATION_SIDECAR",
        "security_boundary": (
            "This status file does not bypass runtime verification, authorization, "
            "deterministic calculation, evidence gates, or report generation."
        ),
        "process_exit_code": int(process_exit_code),
        "request": {
            **request_record,
            "request_id": request.get("request_id") if request else None,
            "operation": request.get("operation") if request else None,
            "canonical_sha256": request_sha256,
        },
        "response": {
            **response_record,
            "ok": response.get("ok") if response else None,
            "status": response.get("status") if response else None,
            "exit_code": response.get("exit_code") if response else None,
        },
        "report": report_record,
        "content_summary": counts,
        "check_count": len(checks),
        "checks": checks,
        "errors": [
            item
            for item in (
                {"stage": "execution", "message": execution_error} if execution_error else None,
                {"stage": "request", "message": request_error} if request_error else None,
                {"stage": "response", "message": response_error} if response_error else None,
                {"stage": "report", "message": report_read_error} if report_read_error else None,
            )
            if item is not None
        ],
    }


def write_report_status(
    status_path: Path,
    request_path: Path,
    response_path: Path,
    *,
    process_exit_code: int,
    execution_error: str | None = None,
) -> dict[str, Any]:
    status = build_report_status(
        request_path,
        response_path,
        process_exit_code=process_exit_code,
        execution_error=execution_error,
    )
    _atomic_write_json(status_path.expanduser().resolve(), status)
    return status


def _argument_path(flag: str) -> Path | None:
    if flag not in sys.argv:
        return None
    index = sys.argv.index(flag) + 1
    if index >= len(sys.argv):
        raise ValueError(f"{flag} requires a file path.")
    return Path(sys.argv[index]).expanduser().resolve()


class EquipmentDesignApi:
    def __init__(self) -> None:
        self.window: Any | None = None
        self._worker_lock = threading.RLock()
        self._active_workers: dict[int, subprocess.Popen[str]] = {}
        self._agent_protocol_lock = threading.RLock()

    def bind_window(self, window: Any) -> None:
        self.window = window

    @staticmethod
    def _ok(value: Any = None, **extra: Any) -> dict[str, Any]:
        return {"ok": True, "value": value, **extra}

    @staticmethod
    def _error(exc: Exception) -> dict[str, Any]:
        return {"ok": False, "error": str(exc)}

    def bootstrap(self) -> dict[str, Any]:
        try:
            bundle_verification = app_core.require_runtime_bundle()
            return self._ok({
                "catalog": app_core.load_catalog(),
                "com": app_core.com_capability(),
                "skill": app_core.skill_entry(),
                "runtime_bundle": bundle_verification,
                "knowledge_packages": app_core.knowledge_packages(),
                "llm_providers": llm_bridge.provider_catalog(),
                "hybrid": {
                    "available": True,
                    "deterministic_authority": True,
                    "fallback": "preserve_deterministic_result",
                },
            })
        except Exception as exc:
            return self._error(exc)

    def test_llm_connection(self, config: dict[str, Any]) -> dict[str, Any]:
        """Return a safe, machine-readable provider connectivity result."""
        try:
            return self._ok(llm_bridge.test_provider_connection(config))
        except Exception as exc:
            return self._error(exc)

    def knowledge_catalog(self) -> dict[str, Any]:
        """Return the deterministic family/topic field directory."""
        try:
            return self._ok(app_core.knowledge_catalog())
        except Exception as exc:
            return self._error(exc)

    def choose_aspen_file(self) -> dict[str, Any]:
        return self._error(RuntimeError("GUI_NOT_DISTRIBUTED: supply an explicit file path"))
        try:
            from tkinter import filedialog

            path = filedialog.askopenfilename(filetypes=[("Aspen files", "*.bkp *.apw *.inp"), ("All files", "*.*")])
            return self._ok(path)
        except Exception as exc:
            return self._error(exc)

    def manual_match(self, selection_id: str, values: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._ok(app_core.manual_match(selection_id, values))
        except Exception as exc:
            return self._error(exc)

    def _worker_command(self, args: list[str]) -> list[str]:
        if getattr(sys, "frozen", False):
            return [sys.executable, "--aspen-worker", *args]
        return [sys.executable, str(APP_DIR / "equipment_design_app.py"), "--aspen-worker", *args]

    @staticmethod
    def _kill_worker_tree(process: subprocess.Popen[str]) -> None:
        if process.poll() is not None:
            return
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
                text=True,
                check=False,
            )
        else:
            process.kill()

    def _register_worker(self, process: subprocess.Popen[str]) -> None:
        with self._worker_lock:
            self._active_workers[int(process.pid)] = process

    def _unregister_worker(self, process: subprocess.Popen[str]) -> None:
        with self._worker_lock:
            self._active_workers.pop(int(process.pid), None)

    def active_worker_count(self) -> int:
        with self._worker_lock:
            return sum(1 for process in self._active_workers.values() if process.poll() is None)

    def cancel_active_operations(self) -> dict[str, Any]:
        """Terminate only worker trees created by this API instance."""
        with self._worker_lock:
            workers = list(self._active_workers.values())
        terminated: list[int] = []
        for process in workers:
            if process.poll() is None:
                self._kill_worker_tree(process)
                terminated.append(int(process.pid))
        return {
            "ok": True,
            "terminated_worker_pids": terminated,
            "scope": "only subprocess trees created by this EquipmentDesignApi instance",
            "preexisting_user_aspen_processes_touched": False,
        }

    def import_aspen(self, config: dict[str, Any]) -> dict[str, Any]:
        try:
            if not config.get("mock_fixture") and os.environ.get("EQUIPMENT_BACKEND_ALLOW_COM") != "1":
                raise RuntimeError("COM_EXECUTION_NOT_AUTHORIZED: pass --allow-com or explicitly set EQUIPMENT_BACKEND_ALLOW_COM=1; manual and exported-JSON routes remain available")
            mock_text = str(config.get("mock_fixture", "")).strip()
            mock_fixture = Path(mock_text).expanduser().resolve() if mock_text else None
            source_text = str(config.get("source_path", "")).strip()
            source = Path(source_text).expanduser().resolve() if source_text else None
            if mock_fixture is not None:
                if not mock_fixture.is_file():
                    raise FileNotFoundError(f"Aspen 模拟导出不存在：{mock_fixture}")
            elif source is None or not source.is_file():
                raise FileNotFoundError(f"Aspen 文件不存在：{source or source_text}")
            timeout_s = max(10, min(int(config.get("timeout_s", 900)), 7200))
            pressure_basis = str(config.get("pressure_basis", "")).strip()
            if pressure_basis not in {"absolute", "gauge"}:
                raise ValueError("压力基准必须由用户或 Aspen 导出显式给出 absolute 或 gauge；程序不默认。")
            atmospheric = config.get("atmospheric_pressure_mpa")
            if pressure_basis == "gauge" and atmospheric in (None, ""):
                raise ValueError("表压必须填写当地大气压。")
            atmospheric_value: float | None = None
            if atmospheric not in (None, ""):
                try:
                    atmospheric_value = float(atmospheric)
                except (TypeError, ValueError) as exc:
                    raise ValueError("当地大气压必须是正数 MPa 值。") from exc
                if atmospheric_value <= 0:
                    raise ValueError("当地大气压必须大于 0 MPa。")
            requested_output = str(config.get("output_dir", "")).strip()
            if requested_output:
                session = Path(requested_output).expanduser().resolve()
                session.parent.mkdir(parents=True, exist_ok=True)
            else:
                OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
                session = OUTPUT_ROOT / f"{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            session.mkdir(parents=True, exist_ok=False)
            args = [
                "--out-dir", str(session),
                "--pressure-basis", pressure_basis,
                "--timeout", str(timeout_s),
            ]
            if mock_fixture is not None:
                args.extend(["--mock-fixture", str(mock_fixture)])
            else:
                args.extend(["--source", str(source)])
            if bool(config.get("run", True)):
                args.append("--run")
                if bool(config.get("ensure_stream_transport", True)):
                    args.append("--ensure-stream-transport")
            if atmospheric_value is not None:
                args.extend(["--atmospheric-pressure-mpa", str(atmospheric_value)])
            command = self._worker_command(args)
            creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
            process = subprocess.Popen(
                command,
                cwd=str(PACKAGE_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags,
                env={
                    key: value
                    for key, value in os.environ.items()
                    if not any(marker in key.upper() for marker in ("API_KEY", "SECRET", "PASSWORD", "AUTH_TOKEN", "ACCESS_TOKEN"))
                },
            )
            self._register_worker(process)
            try:
                try:
                    stdout, stderr = process.communicate(timeout=timeout_s + 120)
                except subprocess.TimeoutExpired:
                    self._kill_worker_tree(process)
                    stdout, stderr = process.communicate(timeout=10)
                    return {
                        "ok": False,
                        "error": f"Aspen COM 子进程超过 {timeout_s + 120} 秒，已终止其进程树。可改用手动或 LLM 模式。",
                        "session_dir": str(session),
                        "stdout": stdout[-2000:],
                        "stderr": stderr[-2000:],
                    }
                result_path = session / "worker_result.json"
                if not result_path.is_file():
                    raise RuntimeError(f"Aspen worker 未生成结果文件（returncode={process.returncode}）：{stderr[-1500:]}")
                result = json.loads(result_path.read_text(encoding="utf-8"))
                return {
                    "ok": process.returncode == 0,
                    "value": result,
                    "error": None if process.returncode == 0 else result.get("error", "Aspen 自动导入失败，可切换其他模式。"),
                    "session_dir": str(session),
                    "returncode": process.returncode,
                    "stdout": stdout[-2000:],
                    "stderr": stderr[-2000:],
                }
            finally:
                self._unregister_worker(process)
        except Exception as exc:
            return self._error(exc)

    def llm_review(self, config: dict[str, Any], deterministic_result: dict[str, Any]) -> dict[str, Any]:
        """Compatibility entry that is intentionally routed through strict staging."""
        return self.staged_hybrid_run(
            config,
            deterministic_result,
            {"enabled": False},
            "audit",
            "minimum",
        )

    def hybrid_prepare(
        self,
        deterministic_result: dict[str, Any],
        knowledge_config: dict[str, Any] | None = None,
        injection_point: str = "audit",
        context_scope: str = "minimum",
    ) -> dict[str, Any]:
        """Freeze deterministic/KG context for either an external or built-in Agent."""
        try:
            if not isinstance(deterministic_result, dict):
                raise ValueError("hybrid_prepare 需要确定性结果对象。")
            knowledge_config = knowledge_config if isinstance(knowledge_config, dict) else {}

            def family_ids(value: Any) -> set[str]:
                found: set[str] = set()
                if isinstance(value, list):
                    for item in value:
                        found.update(family_ids(item))
                elif isinstance(value, dict):
                    match = value.get("match")
                    if isinstance(match, dict) and str(match.get("family_id", "")).strip():
                        found.add(str(match["family_id"]).strip())
                    for key in ("result", "items", "equipment", "piping", "match_result"):
                        if isinstance(value.get(key), (dict, list)):
                            found.update(family_ids(value[key]))
                return found

            normalized_scope = {"full": "full_bundle"}.get(context_scope, context_scope)
            supplied = knowledge_config.get("result")
            if supplied is not None and normalized_scope in {"minimum", "routed"}:
                if not isinstance(supplied, dict):
                    raise ValueError("knowledge.result 必须是对象。")
                # Caller-supplied material is advisory context, never proof of
                # exhaustive coverage of an allowlisted local package.
                knowledge_context = dict(supplied)
                declared_status = knowledge_context.get("status")
                declared_coverage = knowledge_context.get("coverage_status")
                limitations = knowledge_context.get("limitations", [])
                limitations = list(limitations) if isinstance(limitations, list) else []
                limitations.append(
                    "caller-supplied knowledge.result is advisory context only and cannot prove complete coverage"
                )
                knowledge_context.update({
                    "status": "CALLER_SUPPLIED_CONTEXT",
                    "coverage_status": "PARTIAL",
                    "caller_declared_status": declared_status,
                    "caller_declared_coverage_status": declared_coverage,
                    "limitations": limitations,
                })
            elif normalized_scope in {"full_family", "full_bundle"}:
                families = family_ids(deterministic_result)
                if normalized_scope == "full_family" and len(families) != 1:
                    raise ValueError("full_family 需要确定性结果中恰好一个 family_id。")
                package_ids = knowledge_config.get("package_ids")
                bundle = app_core.knowledge_asset_bundle(
                    normalized_scope,
                    package_ids=package_ids,
                    family_id=next(iter(families)) if families else None,
                    max_chars=int(knowledge_config.get("max_chars", 1_500_000)),
                )
                if bool(knowledge_config.get("enabled", True)) and bundle["selected_packages"]:
                    query = str(knowledge_config.get("query", "")).strip() or "设备选型 公式 证据门 型号状态"
                    retrieval = app_core.knowledge_search(
                        query,
                        limit=int(knowledge_config.get("limit", 8)),
                        package_ids=bundle["selected_packages"],
                    )
                else:
                    retrieval = {
                        "hits": [],
                        "result_count": 0,
                        "status": (
                            "NOT_REQUESTED"
                            if not bool(knowledge_config.get("enabled", True))
                            else "NO_AVAILABLE_KNOWLEDGE_PACKAGES"
                        ),
                    }
                knowledge_context = {
                    **retrieval,
                    "status": bundle["status"],
                    "coverage_status": bundle["coverage_status"],
                    "selected_packages": bundle["selected_packages"],
                    "unavailable_packages": bundle["unavailable_packages"],
                    "coverage_definition": bundle["coverage_definition"],
                    "assets": bundle["assets"],
                    "truncated_assets": bundle["truncated_assets"],
                    "caller_supplied_result_ignored_for_full_coverage": supplied is not None,
                    "asset_bundle": {
                        key: value for key, value in bundle.items()
                        if key not in {"assets", "truncated_assets"}
                    },
                }
            elif bool(knowledge_config.get("enabled", False)):
                query = str(knowledge_config.get("query", "")).strip() or "设备选型 公式 证据门 型号状态"
                package_ids = knowledge_config.get("package_ids")
                if package_ids is not None and (
                    not isinstance(package_ids, list)
                    or not all(isinstance(item, str) for item in package_ids)
                ):
                    raise ValueError("knowledge.package_ids 必须是字符串数组。")
                knowledge_context = app_core.knowledge_search(
                    query,
                    limit=int(knowledge_config.get("limit", 8)),
                    package_ids=package_ids,
                )
            else:
                knowledge_context = {
                    "status": "NOT_REQUESTED",
                    "coverage_status": "PARTIAL",
                    "selected_packages": [],
                    "result_count": 0,
                    "hits": [],
                    "assets": [],
                    "limitations": ["未启用知识包检索；上下文不得声称完整覆盖。"],
                }
            prepared = llm_bridge.hybrid_prepare(
                deterministic_result,
                knowledge_context,
                injection_point,
                context_scope,
            )
            return self._ok(prepared, knowledge_context=knowledge_context)
        except Exception as exc:
            return self._error(exc)

    def hybrid_continue(self, prepared: dict[str, Any], step_output: dict[str, Any]) -> dict[str, Any]:
        """Validate an external Agent response against the immutable prepared context."""
        try:
            return self._ok(llm_bridge.hybrid_continue(prepared, step_output))
        except Exception as exc:
            return self._error(exc)

    def hybrid_run(self, config: dict[str, Any], prepared: dict[str, Any]) -> dict[str, Any]:
        """Use a configured provider, then reuse hybrid_continue's exact validator."""
        try:
            return self._ok(llm_bridge.hybrid_run(config, prepared))
        except Exception as exc:
            return self._error(exc)

    def staged_hybrid_run(
        self,
        config: dict[str, Any],
        source_input: dict[str, Any],
        knowledge_config: dict[str, Any] | None = None,
        injection_point: str = "audit",
        context_scope: str = "minimum",
    ) -> dict[str, Any]:
        """Compatibility name for the Agent protocol-1.8 GUI bridge.

        ``source_input`` must be a replayable ``operation + payload`` object.
        Naked deterministic results are deliberately rejected so the GUI cannot
        bypass the same replay, authority-revision and strict-output validator
        used by the Agent/CLI surface.
        """
        return self.agent_hybrid_run(
            source_input,
            config,
            knowledge_config,
            injection_point,
            context_scope,
        )

    def agent_hybrid_run(
        self,
        source_input: dict[str, Any],
        config: dict[str, Any],
        knowledge_config: dict[str, Any] | None = None,
        injection_point: str = "audit",
        context_scope: str = "minimum",
    ) -> dict[str, Any]:
        """Run GUI review through Agent ``hybrid_run`` and return v2 only."""
        runtime_key = str(config.get("api_key", "")) if isinstance(config, dict) else ""
        try:
            if not isinstance(source_input, dict) or not isinstance(source_input.get("operation"), str) or not isinstance(source_input.get("payload"), dict):
                raise ValueError(
                    "Agent 协同需要可重放的 input.operation + input.payload；不接受裸确定性结果。"
                )
            if not isinstance(config, dict):
                raise ValueError("Agent 协同 config 必须是对象。")
            knowledge = knowledge_config if isinstance(knowledge_config, dict) else {}
            provider = str(config.get("provider", "openai_compatible")).strip()
            provider_config = {
                key: value
                for key, value in config.items()
                if key not in {"enabled", "api_key", "base_url"}
            }
            provider_config["provider"] = provider
            runtime_base_url = str(config.get("base_url", "")).strip()
            if provider == "local_openai_compatible" and runtime_base_url:
                provider_config["base_url"] = runtime_base_url
            payload = {
                "input": json.loads(json.dumps(source_input, ensure_ascii=False)),
                "knowledge": json.loads(json.dumps(knowledge, ensure_ascii=False)),
                "injection_point": injection_point,
                "context_scope": context_scope,
                "llm": {
                    "enabled": bool(config.get("enabled", True)),
                    "config": provider_config,
                },
            }
            with self._agent_protocol_lock:
                key_name = "EQUIPMENT_DESIGN_LLM_API_KEY"
                base_name = "EQUIPMENT_DESIGN_LLM_BASE_URL"
                old_key = os.environ.get(key_name)
                old_base = os.environ.get(base_name)
                try:
                    if runtime_key:
                        os.environ[key_name] = runtime_key
                    if provider == "openai_compatible":
                        if runtime_base_url:
                            os.environ[base_name] = runtime_base_url
                    from equipment_design_agent import execute_operation

                    value, artifacts = execute_operation("hybrid_run", payload, self)
                finally:
                    if old_key is None:
                        os.environ.pop(key_name, None)
                    else:
                        os.environ[key_name] = old_key
                    if old_base is None:
                        os.environ.pop(base_name, None)
                    else:
                        os.environ[base_name] = old_base
            if not isinstance(value, dict) or value.get("schema") != "equipment-design-hybrid-result-v2":
                raise RuntimeError("Agent hybrid_run 未返回协议 1.9 规定的 v2 结果。")
            if runtime_key:
                def redact_secret(item: Any) -> Any:
                    if isinstance(item, str):
                        return item.replace(runtime_key, "[REDACTED]")
                    if isinstance(item, list):
                        return [redact_secret(child) for child in item]
                    if isinstance(item, dict):
                        return {key: redact_secret(child) for key, child in item.items()}
                    return item

                value = redact_secret(value)
            return self._ok(value, artifacts=artifacts)
        except Exception as exc:
            message = str(exc)
            if runtime_key:
                message = message.replace(runtime_key, "[REDACTED]")
            return self._error(RuntimeError(message))

    def hybrid_review(
        self,
        config: dict[str, Any],
        source_input: dict[str, Any],
        knowledge_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Deprecated compatibility alias for the strict staged wrapper."""
        return self.staged_hybrid_run(config, source_input, knowledge_config)

    def apply_llm_proposal(self, current: dict[str, Any], proposal: dict[str, Any]) -> dict[str, Any]:
        return self._error(
            ValueError(
                "legacy 草案应用已禁用；请使用 agent_llm_apply，并显式绑定 context_sha256 与 orchestration_sha256。"
            )
        )

    def agent_llm_apply(self, proposal: dict[str, Any], approval: dict[str, Any]) -> dict[str, Any]:
        """Apply an orchestration through the Agent's exact ``llm_apply`` gate."""
        try:
            from equipment_design_agent import execute_operation

            with self._agent_protocol_lock:
                value, artifacts = execute_operation(
                    "llm_apply",
                    {"proposal": proposal, "approval": approval},
                    self,
                )
            return self._ok(value, artifacts=artifacts)
        except Exception as exc:
            return self._error(exc)

    def search_knowledge(self, query: str, package_ids: list[str] | None = None) -> dict[str, Any]:
        try:
            return self._ok(app_core.knowledge_search(query, package_ids=package_ids))
        except Exception as exc:
            return self._error(exc)

    def save_json(self, payload: Any, suggested_name: str = "equipment_design_result.json") -> dict[str, Any]:
        try:
            from tkinter import filedialog

            path_text = filedialog.asksaveasfilename(defaultextension=".json", initialfile=Path(suggested_name).name, filetypes=[("JSON", "*.json"), ("All files", "*.*")])
            if not path_text:
                return self._ok("")
            path = Path(path_text)
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            return self._ok(str(path))
        except Exception as exc:
            return self._error(exc)

    def open_folder(self, path: str) -> dict[str, Any]:
        return self._error(RuntimeError("GUI_NOT_DISTRIBUTED: use returned artifact paths"))
        try:
            target = Path(path).resolve()
            if not target.is_dir():
                raise FileNotFoundError(target)
            if os.name == "nt":
                os.startfile(str(target))  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", str(target)])
            return self._ok(str(target))
        except Exception as exc:
            return self._error(exc)


def run_gui() -> int:
    raise RuntimeError("GUI_NOT_DISTRIBUTED: use equipment_design_agent.py for the preserved backend protocol")


def main() -> int:
    # A frozen executable may only activate the bundled rules, graph, data and
    # schemas after the exact manifest path/size/hash set has been verified.
    app_core.require_runtime_bundle()
    if "--aspen-worker" in sys.argv:
        index = sys.argv.index("--aspen-worker")
        worker_args = sys.argv[index + 1 :]
        import aspen_com_import

        return aspen_com_import.main(worker_args)
    if "--agent-request" in sys.argv:
        request_index = sys.argv.index("--agent-request") + 1
        if request_index >= len(sys.argv):
            raise ValueError("--agent-request 需要 JSON 文件路径。")
        agent_args = ["--request", sys.argv[request_index]]
        if "--agent-response" in sys.argv:
            response_index = sys.argv.index("--agent-response") + 1
            if response_index >= len(sys.argv):
                raise ValueError("--agent-response 需要 JSON 文件路径。")
            agent_args.extend(["--output", sys.argv[response_index]])
        else:
            raise ValueError("窗口版 EXE 的 Agent 调用必须提供 --agent-response 文件路径。")
        agent_args.append("--pretty")
        import equipment_design_agent

        request_path = Path(sys.argv[request_index]).expanduser().resolve()
        response_path = Path(sys.argv[response_index]).expanduser().resolve()
        report_status_path = _argument_path("--report-status")
        exit_code = 8
        execution_error: str | None = None
        try:
            exit_code = equipment_design_agent.main(agent_args)
        except Exception as exc:
            execution_error = str(exc)
            if report_status_path is None:
                raise
        if report_status_path is not None:
            status = write_report_status(
                report_status_path,
                request_path,
                response_path,
                process_exit_code=exit_code,
                execution_error=execution_error,
            )
            if execution_error is not None:
                raise RuntimeError(execution_error)
            if status["normal_content"] is not True and exit_code == 0:
                return 3
        return exit_code
    if "--report-status" in sys.argv:
        raise ValueError("--report-status is only valid with --agent-request and --agent-response.")
    if "--self-test" in sys.argv:
        payload = {
            "runtime_bundle": app_core.runtime_bundle_verification(),
            "catalog": len(app_core.load_catalog()["selections"]),
            "com": app_core.com_capability(),
            "skill": app_core.skill_entry(),
            "knowledge_search": app_core.knowledge_search("泵 压力基准", limit=3),
            "manual_match_status": app_core.manual_match("block:PUMP", {
                "equipment_tag": "P-SELFTEST",
                "phase": "liquid",
                "pressure_basis": "absolute",
                "inlet_pressure_mpa": 0.2,
                "outlet_pressure_mpa": 0.6,
                "density_kg_m3": 900,
                "flow_m3_h": 20,
                "efficiency_percent": 75,
            })["result"]["status"],
        }
        rendered = json.dumps(payload, ensure_ascii=False, indent=2)
        if "--self-test-output" in sys.argv:
            output_index = sys.argv.index("--self-test-output") + 1
            if output_index >= len(sys.argv):
                raise ValueError("--self-test-output 需要文件路径。")
            output_path = Path(sys.argv[output_index]).expanduser().resolve()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered + "\n", encoding="utf-8")
        else:
            print(rendered)
        return 0
    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
