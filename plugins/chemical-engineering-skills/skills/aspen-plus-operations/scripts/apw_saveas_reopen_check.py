"""SaveAs/APW reopen mechanics under an external owned-worker watchdog.

Legacy CLI flags remain accepted. ``ok`` now explicitly means mechanical
save/reopen/run-return/export only; simulation_clean and delivery_passed are
independent and are never granted by this tool. --skip-reopen-verify is diagnostic.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import traceback
from typing import Any

import aspen_runtime as runtime
from aspen_run_supervisor import run_worker

now, sha256 = runtime.now, runtime.sha256
_SESSIONS: dict[int, runtime.AspenSession] = {}
_LEASES: dict[str, runtime.LockLease] = {}

def acquire_lock(lock_file: Path | None, timeout_s: int) -> bool:
    path = lock_file or runtime.DEFAULT_LOCK_PATH
    try:
        lease = runtime.acquire_lock(path, owner="apw-saveas-compat", wait_timeout_s=timeout_s)
    except TimeoutError:
        return False
    _LEASES[str(path.resolve())] = lease
    return True

def release_lock(lock_file: Path | None) -> bool:
    path = (lock_file or runtime.DEFAULT_LOCK_PATH).resolve()
    lease = _LEASES.get(str(path))
    return lease.release() if lease else False

def create_aspen(prog_id: str = "Apwn.Document") -> tuple[Any, str]:
    session = runtime.create_session(prog_id)
    _SESSIONS[id(session.app)] = session
    return session.app, session.prog_id

def _session(aspen: Any) -> runtime.AspenSession:
    if isinstance(aspen, runtime.AspenSession):
        return aspen
    if id(aspen) not in _SESSIONS:
        raise RuntimeError("Aspen object not owned by this operation; refusing lifecycle control")
    return _SESSIONS[id(aspen)]

def init_case(aspen: Any, path: Path) -> tuple[str, list[str]]:
    result = runtime.open_case(_session(aspen), path)
    return result["method"], []

def export_file(aspen: Any, export_type: int, path: Path) -> dict[str, Any]:
    return runtime.export_case(_session(aspen), export_type, path)

def run_engine(aspen: Any, timeout_s: int) -> str:
    result = runtime.run_case(_session(aspen), timeout_s=timeout_s,
                              run_id=os.environ.get("ASPEN_RUNTIME_RUN_ID", "compat"))
    return "returned" if result["status"] == "completed" else result["status"]

def save_as_apw(aspen: Any, output: Path, *, work_dir: Path | None = None) -> dict[str, Any]:
    session = _session(aspen)
    session.assert_owner()
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to replace existing APW: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix="AspenAPWSave_", dir=work_dir)) if work_dir else Path(tempfile.mkdtemp(prefix="AspenAPWSave_"))
    created = root / "candidate.apw"
    try:
        session.app.SaveAs(str(created))
        if not created.is_file() or created.stat().st_size == 0:
            raise RuntimeError("SaveAs returned without creating a nonempty APW")
        # Exclusive destination creation prevents concurrent commands from silently
        # overwriting each other's result after both passed the initial preflight.
        with created.open("rb") as src, output.open("xb") as dst:
            shutil.copyfileobj(src, dst)
        return {"ok": sha256(created) == sha256(output), "method": "SaveAs(unique_ascii_candidate)",
                "created_path": str(created), **runtime.artifact(output), "sidecars": [runtime.artifact(p) for p in root.iterdir() if p.is_file()],
                "ok_semantics": "MECHANICAL_SAVE_ONLY", "simulation_clean": None, "delivery_passed": False}
    except Exception as exc:
        return {"ok": False, "path": str(output), "created_path": str(created), "errors": [str(exc)],
                "simulation_clean": None, "delivery_passed": False}

def close_aspen(aspen: Any | None) -> dict[str, Any]:
    if aspen is None:
        return runtime.close_session(None)
    session = _session(aspen)
    result = runtime.close_session(session)
    _SESSIONS.pop(id(session.app), None)
    return result

def check_sibling_bkp(outputs: list[Path], allow: bool) -> list[str]:
    warnings = []
    for output in outputs:
        sibling = output.with_suffix(".bkp")
        if sibling.exists():
            message = f"{output} has existing same-stem BKP {sibling}; direct Aspen SaveAs may rewrite siblings."
            if not allow:
                raise RuntimeError(message + " Use a non-colliding APW stem or --allow-sibling-bkp-overwrite.")
            warnings.append(message + " This implementation saves in a unique directory and preserves the original sibling.")
    return warnings

def preflight(source: Path, outputs: list[Path], allow_sibling: bool) -> list[str]:
    if not source.is_file():
        raise FileNotFoundError(source)
    if len(outputs) != len(set(outputs)):
        raise ValueError("Duplicate APW output paths")
    for output in outputs:
        if output == source:
            raise ValueError("Source and APW output must differ")
        if output.suffix.lower() != ".apw":
            raise ValueError("--apw-output must name an APW file")
        if output.exists():
            raise FileExistsError(f"Existing APW output is protected: {output}")
    return check_sibling_bkp(outputs, allow_sibling)

def process_apw(args: argparse.Namespace, *, session_factory=None) -> tuple[dict[str, Any], int]:
    """Worker implementation; injectable session factory is for offline mocks."""
    recorder = runtime.StageRecorder()
    factory = session_factory or runtime.create_session
    source = Path(args.source).resolve()
    outputs = [Path(item).resolve() for item in args.apw_output]
    run_dir = Path(args._run_dir).resolve()
    summary: dict[str, Any] = {"schema": "apw-saveas-reopen-summary-v2", "started": now(), "run_id": recorder.run_id,
        "source": str(source), "source_sha256": sha256(source), "outputs_requested": list(map(str, outputs)),
        "run_before_save": args.run_before_save, "diagnostic_only": bool(args.skip_reopen_verify),
        "ok": False, "ok_semantics": "MECHANICAL_SAVE_REOPEN_RUN_EXPORT_ONLY_NOT_SIMULATION_CLEAN",
        "simulation_clean": None, "delivery_passed": False, "delivery_gate_status": "NOT_EVALUATED_USE_SHARED_CLEAN_AUDIT",
        "precision_policy": "STRICT_NO_MODEL_OR_TOLERANCE_MUTATION", "runtime_identity": runtime.artifact(Path(runtime.__file__))}
    session = None
    creation_in_progress = False
    lifecycles = []
    verification = []
    source_hash = summary["source_sha256"]
    try:
        summary["sibling_bkp_warnings"] = preflight(source, outputs, args.allow_sibling_bkp_overwrite)
        scratch = Path(tempfile.mkdtemp(prefix="AspenAPWWorker_"))
        summary["scratch_directory"] = str(scratch)
        staging = runtime.stage_source(source, scratch)
        summary["staging"] = staging
        opened = Path(staging["opened_path"])
        recorder.update("creating_com", case_sha256=source_hash)
        creation_in_progress = True
        session = factory(args.prog_id)
        creation_in_progress = False
        summary["com_creator"] = session.prog_id
        summary["session"] = session.metadata
        recorder.update("opening", case_sha256=source_hash)
        opening = runtime.open_case(session, opened)
        summary.update({"init_method": opening["method"], "init_errors": [], "open_evidence": opening})
        recorder.update("exporting")
        summary["before_save_inp"] = runtime.export_case(session, 4, run_dir / f"{args.label}_before_save.inp")
        if args.run_before_save:
            history_before = runtime.snapshot_history(opened.parent)
            recorder.update("running")
            status = runtime.run_case(session, timeout_s=args.run_timeout, run_id=recorder.run_id, case_sha256=source_hash)
            summary["run_before_save_status"] = "returned" if status["status"] == "completed" else status["status"]
            summary["run_before_save_evidence"] = status
            recorder.update("exporting")
            summary["after_run_before_save_inp"] = runtime.export_case(session, 4, run_dir / f"{args.label}_after_run_before_save.inp")
            summary["before_save_history_candidates"] = runtime.capture_history_candidates(opened.parent, history_before,
                run_dir / "source_history", run_id=recorder.run_id, case_sha256=source_hash)
            if status["status"] != "completed":
                raise RuntimeError("Pre-save run did not finish with known engine state")
        recorder.update("saving")
        summary["save_as_apw"] = [save_as_apw(session, output) for output in outputs]
        recorder.update("closing")
        lifecycle = runtime.close_session(session)
        lifecycles.append(lifecycle)
        session = None
        if not lifecycle["closed_cleanly"]:
            raise RuntimeError("Source session close is incomplete; no second COM session dispatched")
        if not args.skip_reopen_verify:
            for index, output in enumerate(outputs, 1):
                row: dict[str, Any] = {"source_apw": str(output), "source_apw_sha256": sha256(output), "label": f"{args.label}_VERIFY_{index}",
                    "ok": False, "simulation_clean": None, "delivery_passed": False}
                try:
                    recorder.update("creating_com", case_sha256=row["source_apw_sha256"])
                    creation_in_progress = True
                    session = factory(args.prog_id)
                    creation_in_progress = False
                    row["com_creator"] = session.prog_id
                    row["session"] = session.metadata
                    recorder.update("opening")
                    opened_result = runtime.open_case(session, output)
                    row.update({"init_method": opened_result["method"], "init_errors": [], "open_evidence": opened_result,
                                "exact_output_path_reopened": True})
                    before = runtime.snapshot_history(output.parent)
                    recorder.update("running")
                    run = runtime.run_case(session, timeout_s=args.run_timeout, run_id=f"{recorder.run_id}-verify-{index}", case_sha256=row["source_apw_sha256"])
                    row["run_status"] = "returned" if run["status"] == "completed" else run["status"]
                    row["run_evidence"] = run
                    recorder.update("exporting")
                    row["after_run_inp"] = runtime.export_case(session, 4, run_dir / f"{args.label}_verify_{index}_after_run.inp")
                    row["after_run_bkp"] = runtime.export_case(session, 1, run_dir / f"{args.label}_verify_{index}.bkp")
                    row["history_candidates"] = runtime.capture_history_candidates(output.parent, before,
                        run_dir / f"verify_{index}_history", run_id=run["run_id"], case_sha256=row["source_apw_sha256"])
                    row["run_returned"] = run["status"] == "completed"
                    row["reopen_succeeded"] = True
                except Exception as exc:
                    row.update({"fatal": str(exc), "traceback": traceback.format_exc()})
                finally:
                    recorder.update("closing")
                    lifecycle = runtime.close_session(session)
                    if creation_in_progress:
                        lifecycle.update(closed_cleanly=False, status="COM_CREATION_RESULT_UNPROVEN")
                    lifecycles.append(lifecycle)
                    session = None
                    row["lifecycle"] = lifecycle
                    row["ok"] = (row.get("run_returned") is True and row.get("after_run_inp", {}).get("ok") is True
                                 and row.get("after_run_bkp", {}).get("ok") is True and lifecycle["closed_cleanly"])
                    row["ok_semantics"] = "MECHANICAL_REOPEN_RUN_EXPORT_ONLY"
                    row["output_after_run"] = runtime.artifact(output)
                    verification.append(row)
                if not lifecycle["closed_cleanly"]:
                    raise RuntimeError("Reopen session close incomplete; stopping further COM dispatch")
    except Exception as exc:
        summary.update({"fatal": str(exc), "traceback": traceback.format_exc()})
    finally:
        if session is not None:
            recorder.update("closing")
            lifecycles.append(runtime.close_session(session))
        if creation_in_progress:
            lifecycles.append({"closed_cleanly": False, "status": "COM_CREATION_RESULT_UNPROVEN"})
        lifecycle_clean = all(item["closed_cleanly"] for item in lifecycles)
        summary["reopen_verify"] = verification
        summary["lifecycles"] = lifecycles
        summary["original_source_unchanged"] = sha256(source) == source_hash
        summary["save_succeeded"] = bool(summary.get("save_as_apw")) and all(row["ok"] for row in summary.get("save_as_apw", []))
        summary["reopen_succeeded"] = len(verification) == len(outputs) and all(row.get("reopen_succeeded") for row in verification)
        summary["run_returned"] = bool(verification) and all(row.get("run_returned") for row in verification)
        summary["ok"] = (not args.skip_reopen_verify and summary["save_succeeded"] and len(verification) == len(outputs)
            and all(row["ok"] for row in verification) and lifecycle_clean and summary["original_source_unchanged"] and "fatal" not in summary)
        summary["operation_completed"] = (summary["save_succeeded"] and lifecycle_clean and summary["original_source_unchanged"]
            and "fatal" not in summary and (args.skip_reopen_verify or summary["ok"]))
        summary["finished"] = now()
        path = run_dir / f"{args.label}_apw_saveas_reopen_summary.json"
        runtime.atomic_json(path, summary)
        recorder.update("finished", lifecycle_clean=lifecycle_clean, summary_path=str(path))
    return summary, 0 if summary["operation_completed"] else 3

def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--apw-output", action="append", required=True)
    parser.add_argument("--out-dir", default="apw_saveas_reopen_evidence")
    parser.add_argument("--label", default="APW_SAVEAS_REOPEN")
    parser.add_argument("--run-before-save", action="store_true")
    parser.add_argument("--skip-reopen-verify", action="store_true")
    parser.add_argument("--run-timeout", type=float, default=1800)
    parser.add_argument("--stage-timeout", type=float, default=60)
    parser.add_argument("--lock-file", default="")
    parser.add_argument("--lock-timeout", type=float, default=0)
    parser.add_argument("--allow-sibling-bkp-overwrite", action="store_true")
    parser.add_argument("--prog-id", default="Apwn.Document")
    parser.add_argument("--_worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--_run-dir", default="", help=argparse.SUPPRESS)
    return parser.parse_args()

def main() -> int:
    args = parse_args()
    if Path(args.label).name != args.label or any(character in args.label for character in ':*?"<>|'):
        raise ValueError("Label must be a safe filename component")
    if args._worker:
        if not os.environ.get("ASPEN_RUNTIME_OWNER_TOKEN") or not os.environ.get("ASPEN_RUNTIME_STAGE_FILE"):
            raise RuntimeError("Worker requires external supervisor context")
        return process_apw(args)[1]
    source = Path(args.source).resolve()
    outputs = [Path(item).resolve() for item in args.apw_output]
    preflight(source, outputs, args.allow_sibling_bkp_overwrite)
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(prefix="apw_run_", dir=out_dir))
    # Normalize external paths before changing the worker cwd.
    normalized = ["--source", str(source), "--out-dir", str(out_dir), "--label", args.label,
                  "--run-timeout", str(args.run_timeout), "--stage-timeout", str(args.stage_timeout), "--prog-id", args.prog_id]
    for output in outputs:
        normalized += ["--apw-output", str(output)]
    for enabled, flag in ((args.run_before_save, "--run-before-save"), (args.skip_reopen_verify, "--skip-reopen-verify"),
                          (args.allow_sibling_bkp_overwrite, "--allow-sibling-bkp-overwrite")):
        if enabled:
            normalized.append(flag)
    command = [sys.executable, str(Path(__file__).resolve()), *normalized, "--_worker", "--_run-dir", str(run_dir)]
    budgets = {phase: args.stage_timeout for phase in ("creating_com", "opening", "exporting", "saving", "closing")}
    budgets["running"] = args.run_timeout
    supervised = run_worker(command, run_dir=run_dir, stage_timeouts=budgets,
        overall_timeout_s=(args.run_timeout + 6 * args.stage_timeout) * (len(outputs) + 1),
        lock_path=Path(args.lock_file).resolve() if args.lock_file else runtime.DEFAULT_LOCK_PATH, lock_wait_s=args.lock_timeout)
    path = run_dir / f"{args.label}_apw_saveas_reopen_summary.json"
    code = 0 if supervised["status"] == "completed" and supervised.get("lifecycle_clean") else 3
    print(json.dumps({"return_code": code, "summary": str(path), "supervisor": str(run_dir / "supervisor_result.json"),
                      "diagnostic_only": args.skip_reopen_verify, "delivery_passed": False}, ensure_ascii=False))
    return code

if __name__ == "__main__":
    raise SystemExit(main())
