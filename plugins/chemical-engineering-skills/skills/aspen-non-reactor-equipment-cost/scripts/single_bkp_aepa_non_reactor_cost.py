from __future__ import annotations

import argparse
import csv
import json
import hashlib
import importlib.util
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


# External engines are user-supplied, never discovered in a private workspace.
EXTRACTOR: Path | None = None
GUI_EXECUTOR: Path | None = None
ANCHOR_READER = None

def equipment_anchor_info(scenario_dir: Path) -> dict[str, Any]:
    if ANCHOR_READER is None:
        raise RuntimeError("A user-supplied --anchor-script is required.")
    return ANCHOR_READER(scenario_dir)

def configure_engines(args: argparse.Namespace) -> dict[str, Any]:
    global EXTRACTOR, GUI_EXECUTOR, ANCHOR_READER
    required = {"engine_script": args.engine_script, "anchor_script": args.anchor_script}
    if args.generate_if_missing or args.force_gui:
        required["gui_engine_script"] = args.gui_engine_script
    refs = {}
    for key, value in required.items():
        if value is None or not value.is_absolute() or not value.is_file():
            raise ValueError(f"{key}: supply an explicit existing absolute script path")
        path = value.resolve()
        refs[key] = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest().upper()}
    EXTRACTOR = args.engine_script.resolve()
    GUI_EXECUTOR = args.gui_engine_script.resolve() if args.gui_engine_script else None
    anchor = args.anchor_script.resolve()
    spec = importlib.util.spec_from_file_location("user_supplied_aepa_anchor", anchor)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    reader = getattr(module, "equipment_anchor_info", None)
    if not callable(reader):
        raise ValueError("anchor_script must expose equipment_anchor_info(scenario_dir)")
    if hashlib.sha256(anchor.read_bytes()).hexdigest().upper() != refs["anchor_script"]["sha256"]:
        raise ValueError("anchor_script changed during import")
    ANCHOR_READER = reader
    return refs



def iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def key_path(path: Path | str | None) -> str:
    if not path:
        return ""
    try:
        return str(Path(path).resolve()).casefold()
    except Exception:
        return str(path).casefold()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file() or path.stat().st_size == 0:
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def run_command(cmd: list[str], stdout_path: Path, stderr_path: Path, timeout_s: float | None) -> dict[str, Any]:
    started = datetime.now()
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    with stdout_path.open("w", encoding="utf-8") as stdout_handle, stderr_path.open("w", encoding="utf-8") as stderr_handle:
        proc = subprocess.Popen(cmd, stdout=stdout_handle, stderr=stderr_handle, text=True)
        timed_out = False
        try:
            proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True, text=True, timeout=30)
            except Exception:
                pass
            try:
                proc.wait(timeout=30)
            except Exception:
                pass
    return {
        "cmd": cmd,
        "pid": proc.pid,
        "returncode": proc.returncode,
        "timed_out": timed_out,
        "started_at": started.isoformat(timespec="seconds"),
        "finished_at": iso_now(),
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
    }


def scenario_info(scenario_dir: Path) -> dict[str, Any]:
    szp = scenario_dir / "Scenario1.szp"
    izp = scenario_dir / "Scenario1.izp"
    info: dict[str, Any] = {
        "scenario_dir": str(scenario_dir),
        "scenario_exists": scenario_dir.is_dir(),
        "szp_exists": szp.is_file(),
        "szp_size": szp.stat().st_size if szp.is_file() else None,
        "izp_exists": izp.is_file(),
        "izp_size": izp.stat().st_size if izp.is_file() else None,
    }
    if not scenario_dir.is_dir():
        info["status"] = "missing_cost_dir"
        return info
    info.update(equipment_anchor_info(scenario_dir))
    pair_valid = bool(
        info["szp_exists"]
        and info["izp_exists"]
        and (info["szp_size"] or 0) > 100_000
        and (info["izp_size"] or 0) > 100_000
    )
    info["pair_valid"] = pair_valid
    if pair_valid and info.get("equipment_anchor_ok"):
        info["status"] = "ready_for_equipment_cost_parse"
    elif pair_valid:
        info["status"] = "equipment_sizing_missing"
    elif info["szp_exists"] and not info["izp_exists"]:
        info["status"] = "missing_izp"
    elif info["izp_exists"] and not info["szp_exists"]:
        info["status"] = "missing_szp"
    else:
        info["status"] = "missing_scenario_pair"
    return info


def candidate_scenarios_from_case_root(case_root: Path) -> list[Path]:
    ordered = [
        case_root / "caseCost" / "Scenario1",
        case_root / "$CASE$backupCost" / "Scenario1",
        case_root / "Cost" / "Scenario1",
    ]
    seen = {key_path(path) for path in ordered}
    for path in sorted(case_root.rglob("Scenario1")) if case_root.is_dir() else []:
        key = key_path(path)
        if key in seen:
            continue
        ordered.append(path)
        seen.add(key)
    return ordered


def choose_best_scenario(paths: list[Path]) -> tuple[Path | None, dict[str, Any] | None]:
    infos = [(path, scenario_info(path)) for path in paths]
    for path, info in infos:
        if info.get("status") == "ready_for_equipment_cost_parse":
            return path, info
    for path, info in infos:
        if info.get("scenario_exists"):
            return path, info
    return None, None


def latest_generated_for_source(batch_root: Path, bkp_path: Path) -> tuple[Path | None, dict[str, Any] | None]:
    target = key_path(bkp_path)
    best_row: dict[str, Any] | None = None
    best_mtime = -1.0
    for summary_path in sorted(batch_root.rglob("summary.json")) if batch_root.is_dir() else []:
        try:
            rows = json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(rows, list):
            continue
        mtime = summary_path.stat().st_mtime
        for row in rows:
            if not isinstance(row, dict):
                continue
            if key_path(row.get("source_bkp")) != target:
                continue
            if mtime >= best_mtime:
                copied = dict(row)
                copied["_summary_path"] = str(summary_path)
                copied["_summary_mtime"] = mtime
                best_row = copied
                best_mtime = mtime
    if not best_row:
        return None, None
    work_dir = Path(str(best_row.get("work_dir", "")))
    scenario = work_dir / "caseCost" / "Scenario1"
    return scenario, best_row


def run_gui_generation(args: argparse.Namespace, run_dir: Path, bkp_path: Path) -> dict[str, Any]:
    selected_path = run_dir / "selected_cases.txt"
    selected_path.write_text(str(bkp_path.resolve()) + "\n", encoding="utf-8")
    gui_out_root = run_dir / "gui"
    cmd = [
        sys.executable,
        str(GUI_EXECUTOR),
        "--selected-cases-file",
        str(selected_path),
        "--out-root",
        str(gui_out_root),
        "--max-cases",
        "1",
        "--precheck-timeout-s",
        str(args.precheck_timeout_s),
        "--launch-timeout-s",
        str(args.launch_timeout_s),
        "--run-timeout-s",
        str(args.run_timeout_s),
        "--save-timeout-s",
        str(args.save_timeout_s),
        "--close-timeout-s",
        str(args.close_timeout_s),
    ]
    if args.compact_paths:
        cmd.append("--compact-paths")
    if args.probe_gui_controls:
        cmd.append("--probe-controls-only")
    result = run_command(
        cmd,
        run_dir / "logs" / "gui_executor.stdout.jsonl",
        run_dir / "logs" / "gui_executor.stderr.txt",
        timeout_s=args.gui_timeout_s,
    )
    scenario, row = latest_generated_for_source(gui_out_root, bkp_path)
    result["selected_cases_file"] = str(selected_path)
    result["gui_out_root"] = str(gui_out_root)
    result["latest_summary_row"] = row or {}
    result["generated_scenario_dir"] = str(scenario) if scenario else ""
    return result


def run_extraction(args: argparse.Namespace, run_dir: Path, scenario_dir: Path, bkp_path: Path) -> dict[str, Any]:
    extract_dir = run_dir / "extract"
    cmd = [
        sys.executable,
        str(EXTRACTOR),
        "--root",
        str(scenario_dir),
        "--out-dir",
        str(extract_dir),
        "--chain-id",
        args.chain_id,
        "--stage",
        args.stage,
        "--product",
        args.product,
        "--route",
        args.route,
        "--bkp-path",
        str(bkp_path.resolve()),
    ]
    result = run_command(
        cmd,
        run_dir / "logs" / "extract.stdout.json",
        run_dir / "logs" / "extract.stderr.txt",
        timeout_s=300,
    )
    result["extract_dir"] = str(extract_dir)
    return result


def summarize_extract(extract_dir: Path) -> dict[str, Any]:
    raw_rows = read_csv(extract_dir / "aepa_report_raw_value_inventory.csv")
    candidate_rows = read_csv(extract_dir / "non_reactor_selected_basis_candidates.csv")
    item_rows = read_csv(extract_dir / "aepa_report_equipment_item_inventory.csv")
    raw = raw_rows[0] if raw_rows else {}
    return {
        "parse_status": raw.get("parse_status", ""),
        "parse_error": raw.get("parse_error", ""),
        "non_reactor_equipment_cost_sum_usd": raw.get("non_reactor_equipment_cost_sum_usd", ""),
        "equipment_item_cost_sum_usd": raw.get("equipment_item_cost_sum_usd", ""),
        "purchased_equipment_usd": raw.get("purchased_equipment_usd", ""),
        "total_project_capital_cost_usd": raw.get("total_project_capital_cost_usd", ""),
        "report_consistency_status": raw.get("report_consistency_status", ""),
        "equipment_item_rows": len(item_rows),
        "candidate_rows": len(candidate_rows),
        "reactor_excluded_rows": sum(1 for row in item_rows if str(row.get("is_reactor", "")).lower() == "true"),
        "selected_candidate_sum_usd": sum(
            float(row.get("candidate_cost_usd") or 0)
            for row in candidate_rows
            if str(row.get("status", "")) == "parsed" and str(row.get("selected_for_review", "")).lower() == "true"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bkp-path", type=Path, required=True)
    parser.add_argument("--out-root", type=Path, required=True)
    parser.add_argument("--batch-root", type=Path, default=None)
    parser.add_argument("--engine-script", type=Path, help="User-supplied extract_aepa_report_costs-compatible engine; absolute path.")
    parser.add_argument("--anchor-script", type=Path, help="User-supplied helper exporting equipment_anchor_info; absolute path.")
    parser.add_argument("--gui-engine-script", type=Path, help="Optional user-supplied GUI generation engine; required only for requested generation.")
    parser.add_argument("--chain-id", default="")
    parser.add_argument("--stage", default="")
    parser.add_argument("--product", default="")
    parser.add_argument("--route", default="")
    parser.add_argument("--generate-if-missing", action="store_true")
    parser.add_argument("--force-gui", action="store_true")
    parser.add_argument("--compact-paths", action="store_true")
    parser.add_argument(
        "--probe-gui-controls",
        action="store_true",
        help="Open a copied BKP and verify AEPA Economics controls without running simulation or cost generation.",
    )
    parser.add_argument("--precheck-timeout-s", type=float, default=240.0)
    parser.add_argument("--launch-timeout-s", type=float, default=150.0)
    parser.add_argument("--run-timeout-s", type=float, default=360.0)
    parser.add_argument("--save-timeout-s", type=float, default=240.0)
    parser.add_argument("--close-timeout-s", type=float, default=20.0)
    parser.add_argument("--gui-timeout-s", type=float, default=1200.0)
    args = parser.parse_args()

    try:
        engine_refs = configure_engines(args)
    except Exception as exc:
        print(json.dumps({"status": "dependency_unavailable", "error": str(exc), "cost_extraction_performed": False, "aspen_started_by_adapter": False}, ensure_ascii=False))
        return 2

    bkp_path = args.bkp_path
    if not bkp_path.is_file():
        raise SystemExit(f"BKP not found: {bkp_path}")

    run_dir = args.out_root / (f"r{stamp()}" if args.compact_paths else f"single_{stamp()}")
    run_dir.mkdir(parents=True, exist_ok=False)
    summary: dict[str, Any] = {
        "started_at": iso_now(),
        "bkp_path": str(bkp_path.resolve()),
        "case_root": str(bkp_path.parent.resolve()),
        "run_dir": str(run_dir),
        "status": "started",
        "external_engines": engine_refs,
        "distribution_boundary": "User-provided engines and licensed software; no engine/data supplied by this adapter.",
        "existing_scenario_info": {},
        "generated_scenario_info": {},
        "gui_generation": {},
        "extraction": {},
        "extract_summary": {},
    }

    scenario, info = choose_best_scenario(candidate_scenarios_from_case_root(bkp_path.parent))
    if scenario is None and args.batch_root is not None:
        generated_scenario, generated_row = latest_generated_for_source(args.batch_root, bkp_path)
        if generated_scenario:
            scenario = generated_scenario
            info = scenario_info(generated_scenario)
            summary["previous_generated_summary_row"] = generated_row or {}
    summary["existing_scenario_info"] = info or {}

    needs_gui = args.force_gui or not info or info.get("status") != "ready_for_equipment_cost_parse"
    if needs_gui and (args.generate_if_missing or args.force_gui):
        gui_result = run_gui_generation(args, run_dir, bkp_path)
        summary["gui_generation"] = gui_result
        if args.probe_gui_controls:
            probe_status = str((gui_result.get("latest_summary_row") or {}).get("status", ""))
            summary["status"] = "gui_probe_completed" if probe_status.startswith("probe_controls") else "gui_probe_failed"
            summary["finished_at"] = iso_now()
            write_json(run_dir / "single_bkp_non_reactor_cost_summary.json", summary)
            print(json.dumps(summary, ensure_ascii=False), flush=True)
            return 0 if summary["status"] == "gui_probe_completed" else 4
        generated_scenario = Path(str(gui_result.get("generated_scenario_dir", "")))
        if generated_scenario:
            scenario = generated_scenario
            info = scenario_info(generated_scenario)
            summary["generated_scenario_info"] = info
    elif needs_gui:
        summary["status"] = "needs_gui_generation"
        summary["finished_at"] = iso_now()
        write_json(run_dir / "single_bkp_non_reactor_cost_summary.json", summary)
        print(json.dumps(summary, ensure_ascii=False), flush=True)
        return 2

    if not scenario or not info:
        summary["status"] = "missing_cost_dir"
        summary["finished_at"] = iso_now()
        write_json(run_dir / "single_bkp_non_reactor_cost_summary.json", summary)
        print(json.dumps(summary, ensure_ascii=False), flush=True)
        return 3

    extraction = run_extraction(args, run_dir, scenario, bkp_path)
    summary["extraction"] = extraction
    summary["extract_summary"] = summarize_extract(Path(str(extraction["extract_dir"])))
    if info.get("status") == "ready_for_equipment_cost_parse" and summary["extract_summary"].get("equipment_item_rows", 0):
        summary["status"] = "parsed"
    else:
        summary["status"] = str(info.get("status", "stage_exists_but_value_unresolved"))
    summary["finished_at"] = iso_now()
    write_json(run_dir / "single_bkp_non_reactor_cost_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return 0 if summary["status"] == "parsed" else 4


if __name__ == "__main__":
    raise SystemExit(main())

