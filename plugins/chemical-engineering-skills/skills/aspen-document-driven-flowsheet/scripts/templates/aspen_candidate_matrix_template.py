#!/usr/bin/env python3
"""Template: text-input candidate matrix generation and run queue.

Project values belong in the JSON spec. This template only supplies the
repeatable structure: patch candidates, static sidecars, optional runner queue,
and summaries.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class StaticCheck:
    name: str
    passed: bool
    evidence: str


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def load_spec(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def apply_patches(text: str, case: dict) -> tuple[str, list[StaticCheck]]:
    checks: list[StaticCheck] = []
    for patch in case.get("patches", []):
        pattern = patch["pattern"]
        replacement = patch["replacement"]
        count = int(patch.get("count", 0))
        new_text, changed = re.subn(pattern, replacement, text, count=count, flags=re.M | re.S)
        checks.append(StaticCheck(f"patch:{pattern}", changed > 0, f"changed={changed}"))
        text = new_text
    return text, checks


def static_checks(text: str, case: dict) -> list[StaticCheck]:
    checks: list[StaticCheck] = []
    for pattern in case.get("expect_pattern", []):
        found = bool(re.search(pattern, text, re.I | re.M | re.S))
        checks.append(StaticCheck(f"expect:{pattern}", found, "found" if found else "missing"))
    for pattern in case.get("forbid_pattern", []):
        found = bool(re.search(pattern, text, re.I | re.M | re.S))
        checks.append(StaticCheck(f"forbid:{pattern}", not found, "absent" if not found else "forbidden_match"))
    return checks


def generate_cases(spec: dict, spec_path: Path, out_dir: Path, limit: int | None) -> list[dict]:
    base_file = (spec_path.parent / spec["base_file"]).resolve()
    base_text = base_file.read_text(encoding=spec.get("encoding", "utf-8"), errors="replace")
    cases = spec.get("cases", [])
    if limit:
        cases = cases[:limit]

    generated: list[dict] = []
    out_dir.mkdir(parents=True, exist_ok=True)
    for case in cases:
        case_id = case["case"]
        text, patch_checks = apply_patches(base_text, case)
        checks = patch_checks + static_checks(text, case)
        output_name = case.get("output", f"{case_id}.inp")
        output_path = out_dir / output_name
        output_path.write_text(text, encoding=spec.get("encoding", "utf-8"), newline="\n")
        sidecar = {
            "case": case_id,
            "created": now(),
            "purpose": case.get("purpose", ""),
            "base_file": str(base_file),
            "output": str(output_path),
            "static_ok": all(check.passed for check in checks),
            "checks": [asdict(check) for check in checks],
            "delivery_warning": "Generated candidates are not accepted until Aspen run/export evidence passes.",
        }
        sidecar_path = out_dir / f"{case_id}_sidecar.json"
        sidecar_path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        generated.append({**case, "source": str(output_path), "sidecar": str(sidecar_path), "static_ok": sidecar["static_ok"]})
    return generated


def render_command(template: str, row: dict) -> str:
    return template.format(**row)


def run_queue(rows: list[dict], runner_template: str, out_dir: Path, stop_on_fail: bool) -> tuple[int, list[dict]]:
    queue_path = out_dir / "candidate_matrix_queue.json"
    records: list[dict] = []
    rc = 0
    for row in rows:
        command = render_command(runner_template, row)
        started = time.strftime("%Y-%m-%dT%H:%M:%S")
        proc = subprocess.run(command, shell=True, cwd=str(out_dir), capture_output=True, text=True, check=False)
        record = {
            "case": row.get("case"),
            "source": row.get("source"),
            "command": command,
            "started": started,
            "finished": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "returncode": proc.returncode,
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-4000:],
        }
        records.append(record)
        queue_path.write_text(json.dumps({"records": records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if proc.returncode != 0:
            rc = proc.returncode
            if stop_on_fail:
                break
    return rc, records


def write_manifest(out_dir: Path, generated: list[dict], run_records: list[dict]) -> tuple[Path, Path]:
    manifest = {
        "created": now(),
        "generated_cases": generated,
        "run_records": run_records,
        "promotion_rule": "Promote only from same-version Aspen evidence, not from static generation success.",
    }
    json_path = out_dir / "candidate_matrix_manifest.json"
    md_path = out_dir / "candidate_matrix_manifest.md"
    json_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Candidate Matrix Manifest",
        "",
        f"- created: `{manifest['created']}`",
        f"- generated_cases: `{len(generated)}`",
        f"- run_records: `{len(run_records)}`",
        "- promotion_rule: promote only from same-version Aspen evidence.",
        "",
        "| Case | Static OK | Source | Run RC |",
        "| --- | --- | --- | --- |",
    ]
    rc_by_case = {record.get("case"): record.get("returncode") for record in run_records}
    for row in generated:
        lines.append(f"| {row.get('case')} | {str(row.get('static_ok')).lower()} | `{row.get('source')}` | {rc_by_case.get(row.get('case'), 'not_run')} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate and optionally run project-local Aspen text candidates.")
    parser.add_argument("--spec-json", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--mode", choices=["generate", "generate-run"], default="generate")
    parser.add_argument("--runner-template", help="Shell command with {source} and {case} placeholders.")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--stop-on-fail", action="store_true")
    args = parser.parse_args()

    spec_path = Path(args.spec_json).resolve()
    out_dir = Path(args.out_dir).resolve()
    spec = load_spec(spec_path)
    generated = generate_cases(spec, spec_path, out_dir, args.limit)
    run_records: list[dict] = []
    rc = 0
    if args.mode == "generate-run":
        if not args.runner_template:
            raise SystemExit("--runner-template is required for generate-run")
        rc, run_records = run_queue(generated, args.runner_template, out_dir, args.stop_on_fail)
    json_path, md_path = write_manifest(out_dir, generated, run_records)
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    if any(not row.get("static_ok") for row in generated):
        return 2
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
