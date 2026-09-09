#!/usr/bin/env python3
"""Headless link between original knowledge, deterministic equipment and feedback."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backends.process.feedback import build_plan, audit_replay
from backends.process import pressure

EQUIPMENT_OPERATIONS = {"schema_get", "capabilities", "catalog", "manual_match", "manual_batch",
                        "aspen_derive", "knowledge_search", "auto_match", "selftest"}


def local_environment():
    env = dict(os.environ)
    for key in list(env):
        if key.startswith("EQUIPMENT_DESIGN_LLM_") or key == "EQUIPMENT_BACKEND_ALLOW_COM":
            env.pop(key)
    env.update(PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
    return env


def reject_remote(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower().replace("-", "_") in {"api_key", "password", "access_token", "llm_config", "endpoint", "base_url"}:
                raise ValueError("This local entry does not accept remote model/secret fields")
            reject_remote(child)
    elif isinstance(value, list):
        for child in value:
            reject_remote(child)


def equipment(request):
    reject_remote(request)
    if request.get("operation") not in EQUIPMENT_OPERATIONS:
        raise ValueError("Operation not allowed here; live Aspen import requires the explicit backend --allow-com path")
    run = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "backends/equipment/app/equipment_design_agent.py"),
                          "--request", "-", "--output", "-"],
                         input=json.dumps(request, ensure_ascii=False, allow_nan=False),
                         capture_output=True, text=True, encoding="utf-8", timeout=300,
                         cwd=ROOT, env=local_environment())
    try:
        response = json.loads(run.stdout)
    except ValueError as exc:
        diagnostic = run.stderr[-2400:]
        diagnostic = re.sub(r"(?:gh[pousr]_|github_pat_|sk-(?:proj-)?)[A-Za-z0-9_-]{20,}", "[redacted]", diagnostic)
        raise ValueError(f"Equipment backend returned no JSON (exit {run.returncode}): {diagnostic}") from exc
    return {"backend_exit_code": run.returncode, "response": response}


def search(query, corpus="all", limit=5, vector=False, package_ids=None):
    if not isinstance(query, str) or not query.strip() or not 1 <= limit <= 50:
        raise ValueError("Provide a nonempty query and limit 1..50")
    result = {"query": query, "knowledge": None, "equipment": None}
    if corpus in {"all", "chemical_principles", "sun_lanyi", "aspen_v10"}:
        script = ROOT / "knowledge/scripts/query_knowledge.py"
        run = subprocess.run([sys.executable, "-X", "utf8", str(script), "--query", query,
                              "--corpus", corpus, "--limit", str(limit), "--json", *( ["--vector"] if vector else [])],
                             stdin=subprocess.DEVNULL,
                             capture_output=True, text=True, encoding="utf-8", timeout=90,
                             cwd=ROOT, env=local_environment())
        if run.returncode not in {0, 1}:
            raise ValueError("Bundled knowledge query failed; inspect its own query command")
        try:
            result["knowledge"] = json.loads(run.stdout)
        except ValueError as exc:
            diagnostic = re.sub(r"(?:gh[pousr]_|github_pat_|sk-(?:proj-)?)[A-Za-z0-9_-]{20,}", "[redacted]", run.stderr[-2400:])
            raise ValueError(f"Knowledge query returned no JSON (exit {run.returncode}): {diagnostic}") from exc
    if corpus in {"all", "equipment", "equipment_standards"}:
        if package_ids is not None and (not isinstance(package_ids, list)
                or not package_ids or any(p not in {"equipment_core", "equipment_model_authority", "design_standards"} for p in package_ids)):
            raise ValueError("Choose registered public equipment packages")
        selected = package_ids
        if corpus == "equipment_standards":
            selected = ["design_standards"]
        elif selected is None and re.search(r"(?i)\b(?:GB|HG|SH|JB|NB)(?:[ /T-]|\d)|\b(?:PN|DN)\s*\d|标准|法兰|管壁|壁厚", query):
            selected = ["equipment_core", "equipment_model_authority", "design_standards"]
        request_payload = {"query": query, "limit": limit}
        if selected is not None:
            request_payload["package_ids"] = selected
        result["equipment"] = equipment({"schema": "equipment-design-agent-request-v1",
            "request_id": "EXPERT-KNOWLEDGE", "operation": "knowledge_search",
            "payload": request_payload})
        result["requested_equipment_packages"] = selected or "backend_default_core_and_model"
    if result["knowledge"] is None and result["equipment"] is None:
        raise ValueError("Unknown corpus")
    result["authority_boundary"] = "Retrieved methods/facts retain scope; not current-project values or engineering acceptance"
    return result


def execute(request, evidence_root):
    operation = request["operation"]
    payload = request.get("payload", {})
    if operation == "search":
        return search(**payload)
    if operation == "equipment":
        return equipment(payload)
    if operation == "feedback":
        calculation = equipment(payload["selector_request"])
        if calculation["backend_exit_code"] != 0:
            return {**calculation, "plan": None, "status": "BACKEND_REQUEST_NOT_COMPLETED"}
        plan = build_plan(calculation["response"], payload["context"], evidence_root)
        return {**calculation, "plan": plan}
    if operation == "replay_audit":
        return audit_replay(payload["plan"], payload["replay"], evidence_root)
    if operation == "pressure":
        functions = {name: getattr(pressure, name) for name in (
            "liquid_pipe_loss", "series_pressure", "compressor_train",
            "equal_ratio_initializer", "parallel_distribution")}
        if payload["method"] not in functions:
            raise ValueError("Unregistered pressure method")
        return functions[payload["method"]](**payload["inputs"])
    raise ValueError("Unknown expert operation")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--evidence-root", type=Path)
    parser.add_argument("--query")
    parser.add_argument("--corpus", default="all")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--vector", action="store_true", help="Use the bundled original hash-vector retrieval adapter")
    args = parser.parse_args()
    try:
        if args.query:
            result = search(args.query, args.corpus, args.limit, args.vector)
        elif args.request:
            result = execute(json.loads(args.request.read_text(encoding="utf-8-sig")),
                             args.evidence_root or args.request.resolve().parent)
        else:
            parser.error("--request or --query is required")
        content = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(content)
        else:
            print(content, end="")
        return 0
    except (ValueError, OSError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "NOT_COMPLETED", "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
