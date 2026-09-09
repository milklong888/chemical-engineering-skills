from __future__ import annotations

import argparse
import collections
import hashlib
import json
import queue
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

try:
    import aspen_equipment_derivation as derivation
except ImportError:  # Packaged delivery intentionally uses the Agent executable.
    derivation = None


FIELD_LOCAL_DIAGNOSTIC_CODES = frozenset({
    "NON_NUMERIC_ASPEN_VALUE",
    "MISSING_EXPLICIT_ASPEN_UNIT",
    "UNSUPPORTED_ASPEN_UNIT",
    "CONFLICTING_ASPEN_ALIASES",
})


class ResidentAgent:
    def __init__(self, agent: Path, working_dir: Path, timeout_s: float) -> None:
        command = [str(agent), "--session-jsonl"]
        if agent.suffix.lower() == ".py":
            command.insert(0, sys.executable)
        self.timeout_s = timeout_s
        self.stderr_lines: list[str] = []
        self.responses: queue.Queue[str | None] = queue.Queue()
        self.process = subprocess.Popen(
            command,
            cwd=str(working_dir),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()

    def _read_stdout(self) -> None:
        assert self.process.stdout is not None
        for line in self.process.stdout:
            if line.strip():
                self.responses.put(line)
        self.responses.put(None)

    def _read_stderr(self) -> None:
        assert self.process.stderr is not None
        for line in self.process.stderr:
            self.stderr_lines.append(line.rstrip())

    def request(self, request: dict[str, Any]) -> dict[str, Any]:
        if self.process.poll() is not None:
            raise RuntimeError(f"Agent exited before request: {self.process.returncode}; stderr={self.stderr_lines[-20:]}")
        assert self.process.stdin is not None
        self.process.stdin.write(json.dumps(request, ensure_ascii=False, separators=(",", ":")) + "\n")
        self.process.stdin.flush()
        try:
            line = self.responses.get(timeout=self.timeout_s)
        except queue.Empty as exc:
            raise TimeoutError(f"Agent response timed out after {self.timeout_s:g} s") from exc
        if line is None:
            raise RuntimeError(f"Agent response stream closed; stderr={self.stderr_lines[-20:]}")
        response = json.loads(line)
        if not isinstance(response, dict):
            raise RuntimeError("Agent response must be a JSON object")
        return response

    def close(self) -> None:
        if self.process.stdin is not None and not self.process.stdin.closed:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=10)

    def __enter__(self) -> "ResidentAgent":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def counts(values: list[Any]) -> dict[str, int]:
    return dict(sorted(collections.Counter(str(value or "UNKNOWN") for value in values).items()))


def _resolved_sidecar(parent: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (parent / path).resolve()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def stage_replay_bundle(source: Path, case_dir: Path) -> tuple[Path, dict[str, Any]]:
    """Create a self-contained deterministic replay input with hashed run evidence."""
    source = source.expanduser().resolve()
    case_dir.mkdir(parents=True, exist_ok=True)
    staged_export = case_dir / source.name
    bundle = json.loads(source.read_text(encoding="utf-8-sig"))
    if not isinstance(bundle, dict):
        raise ValueError(f"Aspen export must be a JSON object: {source}")
    case = bundle.get("case")
    if not isinstance(case, dict):
        case = {}
        bundle["case"] = case

    issues: list[str] = []
    artifacts: list[dict[str, Any]] = []
    evidence_source = _resolved_sidecar(source.parent, case.get("run_status_evidence_path"))
    if evidence_source is None or not evidence_source.is_file():
        issues.append("RUN_STATUS_EVIDENCE_FILE_NOT_FOUND")
    else:
        expected_evidence_hash = str(case.get("run_status_evidence_sha256") or "").strip().upper()
        observed_evidence_hash = sha256_file(evidence_source)
        if expected_evidence_hash and expected_evidence_hash != observed_evidence_hash:
            issues.append("RUN_STATUS_EVIDENCE_HASH_MISMATCH")
        try:
            evidence = json.loads(evidence_source.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            evidence = None
            issues.append("RUN_STATUS_EVIDENCE_INVALID_JSON")
        if isinstance(evidence, dict):
            history_source = _resolved_sidecar(evidence_source.parent, evidence.get("raw_history_path"))
            if history_source is None or not history_source.is_file():
                issues.append("RAW_HISTORY_FILE_NOT_FOUND")
            else:
                expected_history_hash = str(evidence.get("raw_history_sha256") or "").strip().upper()
                observed_history_hash = sha256_file(history_source)
                if expected_history_hash and expected_history_hash != observed_history_hash:
                    issues.append("RAW_HISTORY_HASH_MISMATCH")
                history_target = case_dir / history_source.name
                if history_source != history_target.resolve():
                    shutil.copy2(history_source, history_target)
                evidence["raw_history_path"] = history_target.name
                evidence["raw_history_sha256"] = sha256_file(history_target)
                artifacts.append({
                    "role": "raw_aspen_history",
                    "path": history_target.name,
                    "sha256": sha256_file(history_target),
                    "size_bytes": history_target.stat().st_size,
                })

            evidence_target = case_dir / evidence_source.name
            _write_json(evidence_target, evidence)
            case["run_status_evidence_path"] = evidence_target.name
            case["run_status_evidence_sha256"] = sha256_file(evidence_target)
            artifacts.append({
                "role": "aspen_run_status_evidence",
                "path": evidence_target.name,
                "sha256": sha256_file(evidence_target),
                "size_bytes": evidence_target.stat().st_size,
            })

    _write_json(staged_export, bundle)
    artifacts.insert(0, {
        "role": "staged_aspen_equipment_export",
        "path": staged_export.name,
        "sha256": sha256_file(staged_export),
        "size_bytes": staged_export.stat().st_size,
    })
    manifest = {
        "schema": "equipment-design-replay-evidence-bundle-v1",
        "status": "COMPLETE" if not issues else "EVIDENCE_NOT_BUNDLED",
        "issues": sorted(set(issues)),
        "source_export_path": str(source),
        "source_export_sha256": sha256_file(source),
        "staged_export_path": str(staged_export),
        "staged_export_sha256": sha256_file(staged_export),
        "artifacts": artifacts,
    }
    return staged_export, manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay already extracted BKP JSON bundles after deterministic engine changes; never opens Aspen.")
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--agent", type=Path, help="Packaged CLI EXE or source equipment_design_agent.py. Uses one resident JSONL process.")
    parser.add_argument("--working-dir", type=Path, default=Path.cwd())
    parser.add_argument("--timeout-s", type=float, default=240.0)
    args = parser.parse_args()
    input_dir = args.input_dir.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    sources = sorted(input_dir.glob("case_*/aspen_equipment_export.json"))
    if not sources:
        raise SystemExit("no case_*/aspen_equipment_export.json files found")
    agent = args.agent.expanduser().resolve() if args.agent else None
    packaged_sibling = Path(__file__).resolve().parent.parent / "EquipmentDesignAgentCLI.exe"
    if agent is None and packaged_sibling.is_file():
        agent = packaged_sibling
    if agent is not None and not agent.is_file():
        raise SystemExit(f"agent not found: {agent}")
    if agent is None and derivation is None:
        raise SystemExit("No packaged Agent executable or source derivation module is available.")
    working_dir = args.working_dir.expanduser().resolve()
    if not working_dir.is_dir():
        raise SystemExit(f"working directory not found: {working_dir}")

    rows: list[dict[str, Any]] = []
    session = ResidentAgent(agent, working_dir, args.timeout_s) if agent is not None else None
    try:
        for index, source in enumerate(sources, 1):
            case_dir = output_dir / source.parent.name
            case_dir.mkdir(parents=True, exist_ok=True)
            staged_source, evidence_bundle = stage_replay_bundle(source, case_dir)
            _write_json(case_dir / "replay_evidence_bundle_manifest.json", evidence_bundle)
            result_path = case_dir / "equipment_derivation_result.json"
            if session is not None:
                response = session.request({
                    "schema": "equipment-design-agent-request-v1",
                    "request_id": f"multi-bkp-replay-{index:02d}",
                    "operation": "aspen_derive",
                    "payload": {
                        "export_path": str(staged_source),
                        "export_sha256": sha256_file(staged_source),
                        "output_path": str(result_path),
                    },
                })
                if not response.get("ok") or int(response.get("exit_code", 1)) != 0:
                    raise RuntimeError(f"Agent derivation failed for {source.parent.name}: {response}")
                result = response.get("result")
                if not isinstance(result, dict):
                    raise RuntimeError(f"Agent returned no derivation object for {source.parent.name}")
            else:
                assert derivation is not None
                bundle = json.loads(staged_source.read_text(encoding="utf-8-sig"))
                result = derivation.derive_bundle(bundle, staged_source)
                result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            if not result_path.is_file():
                raise RuntimeError(f"derivation result was not written: {result_path}")
            equipment = result.get("equipment") if isinstance(result.get("equipment"), list) else []
            matches = [item.get("match_result", {}) for item in equipment if isinstance(item, dict)]
            ignored_parameter_diagnostics = [
                diagnostic
                for match in matches
                for diagnostic in match.get("ignored_parameter_diagnostics", [])
                if isinstance(diagnostic, dict)
            ]
            row = {
            "index": index,
            "case_directory": source.parent.name,
            "source_path": str(source),
            "source_sha256": sha256_file(source),
            "staged_source_path": str(staged_source),
            "staged_source_sha256": sha256_file(staged_source),
            "evidence_bundle_status": evidence_bundle["status"],
            "evidence_bundle_issues": evidence_bundle["issues"],
            "engine_version": result.get("engine_version"),
            "status": result.get("status"),
            "equipment_count": len(equipment),
            "piping_count": len(result.get("piping") or []),
            "normalization_diagnostic_count": int(result.get("normalization_diagnostic_count") or 0),
            "match_status_counts": counts([match.get("status") for match in matches]),
            "model_status_counts": counts([
                (match.get("model_decision") or {}).get("model_status")
                for match in matches
                if isinstance(match.get("model_decision"), dict)
            ]),
            "ignored_parameter_diagnostic_count": len(ignored_parameter_diagnostics),
            "ignored_parameter_fields": sorted({
                str(item.get("field")) for item in ignored_parameter_diagnostics if item.get("field")
            }),
            "field_only_global_block": (
                result.get("status") == "BLOCKED_INVALID_ASPEN_EXPORT"
                and bool(result.get("errors"))
                and all(
                    str(item.get("code")) in FIELD_LOCAL_DIAGNOSTIC_CODES
                    for item in result.get("errors", [])
                    if isinstance(item, dict)
                )
            ),
            "result_sha256": sha256_file(result_path),
            }
            rows.append(row)
            print(json.dumps(row, ensure_ascii=False, separators=(",", ":")), flush=True)
    finally:
        if session is not None:
            session.close()
    report = {
        "schema": "equipment-design-multi-bkp-derivation-replay-v1",
        "mode": "NO_COM_NO_LLM_DETERMINISTIC_REPLAY",
        "execution_mode": "PACKAGED_RESIDENT_AGENT" if agent is not None else "SOURCE_DIRECT",
        "agent": str(agent) if agent is not None else None,
        "case_count": len(rows),
        "derived_count": sum(1 for row in rows if row["status"] == "DERIVED"),
        "field_only_global_block_count": sum(1 for row in rows if row["field_only_global_block"]),
        "equipment_count": sum(row["equipment_count"] for row in rows),
        "piping_count": sum(row["piping_count"] for row in rows),
        "normalization_diagnostic_count": sum(row["normalization_diagnostic_count"] for row in rows),
        "ignored_parameter_diagnostic_count": sum(row["ignored_parameter_diagnostic_count"] for row in rows),
        "status": "PASS" if all(row["status"] == "DERIVED" and not row["field_only_global_block"] for row in rows) else "FAIL",
        "cases": rows,
    }
    report_path = output_dir / "MULTI_BKP_DERIVATION_REPLAY_REPORT.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
