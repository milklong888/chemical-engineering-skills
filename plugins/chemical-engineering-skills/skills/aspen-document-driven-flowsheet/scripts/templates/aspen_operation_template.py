#!/usr/bin/env python3
"""No-edit Aspen open/run/export compatibility entry with external supervision.

Shared runtime mechanics are loaded from the installed skill. Project-specific
stream tables and product acceptance remain upstream. No operation return value
constitutes simulation or delivery acceptance.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict, dataclass
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any

@dataclass
class Config:
    case_file: Path
    out_dir: Path
    mode: str
    prog_id: str
    run_case: bool
    default_precision_lock: str
    run_timeout: float = 1800
    stage_timeout: float = 60
    lock_file: str = ""
    runtime_path: str = ""
    runtime_sha256: str = ""
    worker: bool = False
    run_dir: str = ""

def load_runtime(config: Config):
    import hashlib
    default = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "skills/aspen-plus-operations/scripts/aspen_runtime.py"
    path = Path(config.runtime_path).resolve() if config.runtime_path else default.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Shared Aspen runtime unavailable: {path}")
    actual = hashlib.sha256(path.read_bytes()).hexdigest().upper()
    if config.runtime_path and not config.runtime_sha256:
        raise ValueError("A custom runtime path requires --runtime-sha256")
    if config.runtime_sha256 and actual != config.runtime_sha256.upper():
        raise ValueError("Shared runtime hash mismatch")
    existing = sys.modules.get("aspen_runtime")
    if existing is not None and Path(existing.__file__).resolve() == path:
        return existing
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("aspen_runtime", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["aspen_runtime"] = module
    spec.loader.exec_module(module)
    return module

def connect_aspen(config: Config) -> Any:
    return load_runtime(config).create_session(config.prog_id)

def open_case(aspen: Any, config: Config) -> dict:
    return load_runtime(config).open_case(aspen, config.case_file)

def run_case(aspen: Any, config: Config) -> dict:
    if not config.run_case:
        return {"status": "not_run", "simulation_clean": None, "delivery_passed": False}
    runtime = load_runtime(config)
    return runtime.run_case(aspen, timeout_s=config.run_timeout,
        run_id=os.environ.get("ASPEN_RUNTIME_RUN_ID", "diagnostic"), case_sha256=runtime.sha256(config.case_file))

def export_case(aspen: Any, config: Config) -> dict:
    runtime = load_runtime(config)
    return {"inp": runtime.export_case(aspen, 4, config.out_dir / "after_run.inp"),
            "bkp": runtime.export_case(aspen, 1, config.out_dir / "after_run.bkp")}

def capture_control_panel(aspen: Any, config: Config) -> str:
    return "not_captured_by_generic_operation_adapter"

def close_aspen(aspen: Any) -> dict:
    return sys.modules["aspen_runtime"].close_session(aspen)

def write_summary(config: Config, status: Any, evidence: dict, control_panel: str, error: str = "", **extra: Any) -> Path:
    runtime = load_runtime(config)
    summary = {"schema": "aspen-operation-summary-v2", "timestamp": runtime.now(),
        "config": {**asdict(config), "case_file": str(config.case_file), "out_dir": str(config.out_dir)},
        "status": status, "control_panel_or_history": control_panel, "evidence": evidence, "error": error,
        "default_precision_lock": config.default_precision_lock, "simulation_clean": None, "delivery_passed": False,
        "precision_policy": "STRICT_NO_MODEL_OR_TOLERANCE_MUTATION", **extra}
    path = config.out_dir / "aspen_operation_summary.json"
    runtime.atomic_json(path, summary)
    return path

def parse_args() -> Config:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-file", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--mode", default="run-export", choices=["open-export", "run-export", "no-run"])
    parser.add_argument("--prog-id", default="Apwn.Document")
    parser.add_argument("--run-case", action="store_true")
    parser.add_argument("--default-precision-lock", default="Do not change CONV-OPTIONS PARAM TOL, TOL-SPEC, balance tolerances, or product-spec tolerances.")
    parser.add_argument("--run-timeout", type=float, default=1800)
    parser.add_argument("--stage-timeout", type=float, default=60)
    parser.add_argument("--lock-file", default="")
    parser.add_argument("--runtime-path", default="")
    parser.add_argument("--runtime-sha256", default="")
    parser.add_argument("--_worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--_run-dir", default="", help=argparse.SUPPRESS)
    args = parser.parse_args()
    return Config(Path(args.case_file).resolve(), Path(args.out_dir).resolve(), args.mode, args.prog_id,
        args.run_case or args.mode == "run-export", args.default_precision_lock, args.run_timeout,
        args.stage_timeout, args.lock_file, args.runtime_path, args.runtime_sha256, args._worker, args._run_dir)

def worker_main(config: Config) -> int:
    if not os.environ.get("ASPEN_RUNTIME_OWNER_TOKEN") or not os.environ.get("ASPEN_RUNTIME_STAGE_FILE"):
        raise RuntimeError("Worker requires its external supervisor context")
    runtime = load_runtime(config)
    recorder = runtime.StageRecorder()
    session = None
    creation_in_progress = False
    status, evidence, error = {"status": "not_started"}, {}, ""
    run_dir = Path(config.run_dir)
    config.out_dir = run_dir
    source = config.case_file
    source_hash = runtime.sha256(source)
    try:
        staging = runtime.stage_source(source, run_dir)
        evidence["staging"] = staging
        config.case_file = Path(staging["opened_path"])
        recorder.update("creating_com", case_sha256=source_hash)
        creation_in_progress = True
        session = runtime.create_session(config.prog_id)
        creation_in_progress = False
        evidence["session"] = session.metadata
        recorder.update("opening", case_sha256=source_hash)
        evidence["open"] = runtime.open_case(session, config.case_file)
        history_before = runtime.snapshot_history(config.case_file.parent)
        recorder.update("running", case_sha256=source_hash)
        status = run_case(session, config)
        recorder.update("exporting", case_sha256=source_hash)
        evidence["exports"] = export_case(session, config)
        evidence["history_candidates"] = runtime.capture_history_candidates(config.case_file.parent, history_before,
            run_dir / "history", run_id=recorder.run_id, case_sha256=source_hash)
    except Exception as exc:
        error = str(exc)
        status = {"status": "operation_error", "error": error}
    finally:
        recorder.update("closing")
        lifecycle = runtime.close_session(session)
        if creation_in_progress:
            lifecycle.update(closed_cleanly=False, status="COM_CREATION_RESULT_UNPROVEN")
        operation_completed = (not error and status.get("status") in {"completed", "not_run"}
            and bool(evidence.get("exports")) and all(row.get("ok") for row in evidence.get("exports", {}).values()) and lifecycle["closed_cleanly"])
        source_unchanged = runtime.sha256(source) == source_hash
        operation_completed = operation_completed and source_unchanged
        path = write_summary(config, status, evidence, "not_captured_by_generic_operation_adapter", error,
            run_id=recorder.run_id, lifecycle=lifecycle, operation_completed=operation_completed,
            original_source_unchanged=source_unchanged, runtime_identity=runtime.artifact(Path(runtime.__file__)),
            acceptance_boundary="Operation only; use the shared evidence audit and project product/equipment gates for acceptance.")
        recorder.update("finished", lifecycle_clean=lifecycle["closed_cleanly"], summary_path=str(path))
    return 0 if operation_completed else 2

def main() -> int:
    config = parse_args()
    runtime = load_runtime(config)
    if config.worker:
        return worker_main(config)
    if not config.case_file.is_file():
        raise FileNotFoundError(config.case_file)
    config.out_dir.mkdir(parents=True, exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(prefix="aspen_operation_", dir=config.out_dir))
    from aspen_run_supervisor import run_worker
    normalized = ["--case-file", str(config.case_file), "--out-dir", str(config.out_dir), "--mode", config.mode,
        "--prog-id", config.prog_id, "--run-timeout", str(config.run_timeout), "--stage-timeout", str(config.stage_timeout),
        "--default-precision-lock", config.default_precision_lock]
    if config.run_case:
        normalized.append("--run-case")
    if config.runtime_path:
        normalized += ["--runtime-path", str(Path(config.runtime_path).resolve())]
    if config.runtime_sha256:
        normalized += ["--runtime-sha256", config.runtime_sha256]
    command = [sys.executable, str(Path(__file__).resolve()), *normalized, "--_worker", "--_run-dir", str(run_dir)]
    budgets = {phase: config.stage_timeout for phase in ("creating_com", "opening", "exporting", "closing")}
    budgets["running"] = config.run_timeout
    result = run_worker(command, run_dir=run_dir, stage_timeouts=budgets,
                        lock_path=Path(config.lock_file) if config.lock_file else runtime.DEFAULT_LOCK_PATH)
    print(json.dumps({"status": result["status"], "summary": str(run_dir / "aspen_operation_summary.json"),
                      "supervisor": str(run_dir / "supervisor_result.json"), "delivery_passed": False}, ensure_ascii=False))
    return 0 if result["status"] == "completed" and result.get("lifecycle_clean") else 2

if __name__ == "__main__":
    raise SystemExit(main())
