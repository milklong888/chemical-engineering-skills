from __future__ import annotations

import argparse
import collections
import hashlib
import json
import time
from pathlib import Path
from typing import Any

from validate_agent_hybrid_protocol import AgentProcess, request


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AGENT = PACKAGE_ROOT / "app" / "equipment_design_agent.py"
DEFAULT_MANIFEST = PACKAGE_ROOT / "data" / "multi_bkp_stability_manifest_20260719.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def counter(values: list[Any]) -> dict[str, int]:
    return dict(sorted(collections.Counter(str(value or "UNKNOWN") for value in values).items()))


def summarize_response(index: int, case: dict[str, Any], response: dict[str, Any], exit_code: int, elapsed_s: float) -> dict[str, Any]:
    worker = response.get("result") if isinstance(response.get("result"), dict) else {}
    derivation = worker.get("result") if isinstance(worker.get("result"), dict) else {}
    equipment = derivation.get("equipment") if isinstance(derivation.get("equipment"), list) else []
    piping = derivation.get("piping") if isinstance(derivation.get("piping"), list) else []
    diagnostics = derivation.get("normalization_diagnostics") if isinstance(derivation.get("normalization_diagnostics"), list) else []
    errors = derivation.get("errors") if isinstance(derivation.get("errors"), list) else []
    match_results = [item.get("match_result", {}) for item in equipment if isinstance(item, dict)]
    calculations = sum(len(item.get("calculations", [])) for item in match_results if isinstance(item.get("calculations"), list))
    candidates = sum(
        len((item.get("model_recommendation") or {}).get("candidates", []))
        for item in match_results
        if isinstance(item.get("model_recommendation"), dict)
    )
    parameter_rows = sum(
        len(group.get("rows", []))
        for item in match_results
        for group in ((item.get("design_parameter_package") or {}).get("groups", []))
        if isinstance(group, dict) and isinstance(group.get("rows"), list)
    )
    field_only_codes = {
        "NON_NUMERIC_ASPEN_VALUE",
        "MISSING_EXPLICIT_ASPEN_UNIT",
        "UNSUPPORTED_ASPEN_UNIT",
        "CONFLICTING_ASPEN_ALIASES",
    }
    error_codes = [str(item.get("code") or "UNKNOWN") for item in errors if isinstance(item, dict)]
    field_only_global_block = (
        derivation.get("status") == "BLOCKED_INVALID_ASPEN_EXPORT"
        and bool(error_codes)
        and set(error_codes).issubset(field_only_codes)
    )
    block_count = int(worker.get("block_count") or 0)
    equipment_count = len(equipment)
    result_present = block_count == 0 or equipment_count > 0
    stable = bool(response.get("ok")) and exit_code == 0 and result_present and not field_only_global_block
    return {
        "index": index,
        "group": case.get("group"),
        "source_path": case.get("path"),
        "source_sha256": worker.get("source_sha256"),
        "response_ok": response.get("ok"),
        "exit_code": exit_code,
        "elapsed_s": round(elapsed_s, 3),
        "worker_status": worker.get("status"),
        "open_method": worker.get("open_method"),
        "progid": worker.get("progid"),
        "aspen_global_unit_set": worker.get("aspen_global_unit_set"),
        "aspen_in_units_card_count": int(worker.get("aspen_in_units_card_count") or 0),
        "aspen_global_in_units_fields": worker.get("aspen_global_in_units_fields") or {},
        "block_count": block_count,
        "stream_count": int(worker.get("stream_count") or 0),
        "derivation_status": derivation.get("status"),
        "formal_use_gate": derivation.get("formal_use_gate"),
        "equipment_count": equipment_count,
        "piping_count": len(piping),
        "normalization_diagnostic_count": len(diagnostics),
        "normalization_diagnostic_codes": counter([item.get("code") for item in diagnostics if isinstance(item, dict)]),
        "structural_error_codes": counter(error_codes),
        "match_status_counts": counter([item.get("status") for item in match_results]),
        "model_status_counts": counter([
            (item.get("model_decision") or {}).get("model_status")
            for item in match_results
            if isinstance(item.get("model_decision"), dict)
        ]),
        "calculation_count": calculations,
        "parameter_row_count": parameter_rows,
        "candidate_count": candidates,
        "result_present": result_present,
        "field_only_global_block": field_only_global_block,
        "stable": stable,
        "history_counts": (worker.get("history_parse") or {}).get("counts"),
    }


def write_report(output_dir: Path, manifest_path: Path, rows: list[dict[str, Any]], process_mode: str, resident_pid: int | None, started: float) -> dict[str, Any]:
    report = {
        "schema": "equipment-design-multi-bkp-stability-report-v1",
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "agent_process_mode": process_mode,
        "resident_session_pid": resident_pid,
        "case_count": len(rows),
        "stable_count": sum(1 for row in rows if row.get("stable")),
        "failed_count": sum(1 for row in rows if not row.get("stable")),
        "field_only_global_block_count": sum(1 for row in rows if row.get("field_only_global_block")),
        "total_elapsed_s": round(time.monotonic() - started, 3),
        "status": "PASS" if rows and all(row.get("stable") for row in rows) else "FAIL",
        "cases": rows,
    }
    (output_dir / "MULTI_BKP_STABILITY_REPORT.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# 十个 BKP 顺序导入稳定性",
        "",
        f"- 状态：`{report['status']}`",
        f"- 常驻模式：`{process_mode}`；PID：`{resident_pid}`",
        f"- 稳定：{report['stable_count']}/{report['case_count']}；字段级全局阻断：{report['field_only_global_block_count']}",
        f"- 总耗时：{report['total_elapsed_s']} s",
        "",
        "| # | 分组 | 打开/推导 | 模块/流股 | 设备/管线 | 计算/参数/候选 | 忽略字段 | 稳定 |",
        "| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['index']} | {row['group']} | {row['worker_status']} / {row['derivation_status']} | "
            f"{row['block_count']}/{row['stream_count']} | {row['equipment_count']}/{row['piping_count']} | "
            f"{row['calculation_count']}/{row['parameter_row_count']}/{row['candidate_count']} | "
            f"{row['normalization_diagnostic_count']} | {'PASS' if row['stable'] else 'FAIL'} |"
        )
    (output_dir / "MULTI_BKP_STABILITY_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Sequentially import multiple BKP files through one resident Agent process.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--agent", type=Path, default=DEFAULT_AGENT)
    parser.add_argument("--timeout", type=int, default=1200)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--limit", type=int, help="Run only the first N manifest cases (smoke/debug use).")
    args = parser.parse_args()

    manifest_path = args.manifest.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise SystemExit(
            f"output directory must be empty to prevent stale-result contamination: {output_dir}"
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    cases = manifest.get("cases") if isinstance(manifest, dict) else None
    if not isinstance(cases, list) or not cases:
        raise SystemExit("manifest.cases must be a non-empty array")
    if args.limit is not None:
        if args.limit <= 0:
            raise SystemExit("--limit must be greater than zero")
        cases = cases[: args.limit]

    agent = AgentProcess(args.agent, PACKAGE_ROOT, timeout_s=args.timeout, persistent=True)
    rows: list[dict[str, Any]] = []
    started = time.monotonic()
    resident_pid: int | None = None
    try:
        for index, raw_case in enumerate(cases, 1):
            if not isinstance(raw_case, dict):
                continue
            source = Path(str(raw_case.get("path") or "")).expanduser().resolve()
            case_dir = output_dir / f"case_{index:02d}"
            value = request("aspen_import", {
                "source_path": str(source),
                "output_dir": str(case_dir),
                "pressure_basis": "absolute",
                "timeout_s": args.timeout,
                "run": bool(args.run),
            }, request_id=f"BKP-STABILITY-{index:02d}")
            one_started = time.monotonic()
            try:
                response, exit_code = agent.call(value)
                resident_pid = resident_pid or agent.session_pid
                (case_dir / "agent_response.json").write_text(
                    json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                row = summarize_response(index, raw_case, response, exit_code, time.monotonic() - one_started)
            except Exception as exc:
                row = {
                    "index": index,
                    "group": raw_case.get("group"),
                    "source_path": str(source),
                    "elapsed_s": round(time.monotonic() - one_started, 3),
                    "stable": False,
                    "field_only_global_block": False,
                    "runner_error": f"{type(exc).__name__}: {exc}",
                }
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False, separators=(",", ":")), flush=True)
    finally:
        process_mode = agent.process_mode
        resident_pid = resident_pid or agent.session_pid
        agent.close()

    report = write_report(output_dir, manifest_path, rows, process_mode, resident_pid, started)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
