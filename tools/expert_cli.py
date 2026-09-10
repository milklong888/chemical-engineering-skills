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
from tools.equipment_gateway import (EquipmentSession, equipment, equipment_batch,
                                     local_environment, describe_policy)

def search(query="", corpus="all", limit=5, vector=False, package_ids=None,
           node_id=None, detail=False, full_text=False, *, equipment_runner=None):
    if (not isinstance(query, str) or type(limit) is not int or not 1 <= limit <= 50
            or bool(query.strip()) == bool(node_id)):
        raise ValueError("Provide exactly one nonempty query or node_id and limit 1..50")
    if node_id is not None and (not isinstance(node_id, str) or not node_id.strip()
            or corpus not in {"all", "chemical_principles", "sun_lanyi", "aspen_v10"}):
        raise ValueError("node_id applies to the bundled concept/method/detail knowledge corpora")
    runner = equipment_runner or equipment
    result = {"query": query, "node_id": node_id, "knowledge": None, "equipment": None}
    if corpus in {"all", "chemical_principles", "sun_lanyi", "aspen_v10"}:
        script = ROOT / "knowledge/scripts/query_knowledge.py"
        arguments = ["--node-id", node_id] if node_id else ["--query", query]
        arguments += (["--detail"] if detail else []) + (["--full-text"] if full_text else [])
        run = subprocess.run([sys.executable, "-X", "utf8", str(script), *arguments,
                              "--corpus", corpus, "--limit", str(limit), "--json", *(["--vector"] if vector else [])],
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
    if not node_id and corpus in {"all", "equipment", "equipment_standards"}:
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
        result["equipment"] = runner({"schema": "equipment-design-agent-request-v1",
            "request_id": "EXPERT-KNOWLEDGE", "operation": "knowledge_search",
            "payload": request_payload})
        result["requested_equipment_packages"] = selected or "backend_default_core_and_model"
    if result["knowledge"] is None and result["equipment"] is None:
        raise ValueError("Unknown corpus")
    result["authority_boundary"] = "Retrieved methods/facts retain scope; not current-project values or engineering acceptance"
    return result


def execute(request, evidence_root, *, equipment_runner=None):
    if not isinstance(request, dict) or not isinstance(request.get("payload", {}), dict):
        raise ValueError("Expert request and payload must be JSON objects")
    runner = equipment_runner or equipment
    operation = request["operation"]
    payload = request.get("payload", {})
    if operation == "solve_route":
        from tools.aspen_tool_router import solve_route
        return solve_route(payload, evidence_root)
    if operation == "design_stage":
        from tools.design_stage import check_stage
        def coordinated(active_runner):
            return check_stage(payload, evidence_root,
                search_runner=lambda **query: search(**query, equipment_runner=active_runner),
                equipment_runner=active_runner)
        if equipment_runner is not None:
            return coordinated(equipment_runner)
        with EquipmentSession() as session:
            return coordinated(session.request)
    if operation == "search":
        if "equipment_runner" in payload:
            raise ValueError("Internal runner cannot be supplied in a request")
        return search(**payload, equipment_runner=runner)
    if operation == "equipment":
        return runner(payload)
    if operation == "equipment_batch":
        requests = payload.get("requests")
        if not isinstance(requests, list) or not requests:
            raise ValueError("equipment_batch requires a nonempty requests array")
        if equipment_runner is None:
            results = equipment_batch(requests)
        else:
            results = []
            for item in requests:
                try:
                    results.append(runner(item))
                except (ValueError, OSError, TypeError, TimeoutError) as exc:
                    results.append({"backend_exit_code": 2, "response": None,
                                    "gateway_error": {"code": type(exc).__name__, "message": str(exc)}})
        return {"results": results, "request_count": len(results), "engineering_accepted": False}
    if operation in {"capabilities", "schema"}:
        from tools.product_contract import describe, schema
        return describe(runner) if operation == "capabilities" else schema(payload["schema_id"], runner)
    if operation == "feedback":
        if not all(key in payload for key in ("selector_request", "context")):
            raise ValueError("feedback requires selector_request and context; use --schema process-feedback and examples/prepare_feedback_case.py")
        calculation = runner(payload["selector_request"])
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
    entry = parser.add_mutually_exclusive_group(required=True)
    entry.add_argument("--request", help="Expert JSON request path, or - for stdin")
    entry.add_argument("--query")
    entry.add_argument("--node-id")
    entry.add_argument("--describe", action="store_true", help="Discover actual local operations, schemas and installed paths")
    entry.add_argument("--schema", help="Product schema ID or an original equipment schema ID")
    entry.add_argument("--session-jsonl", action="store_true", help="One expert request/response per line; one lazy equipment worker")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--evidence-root", type=Path)
    parser.add_argument("--corpus", default="all")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--vector", action="store_true", help="Use the bundled original hash-vector retrieval adapter")
    parser.add_argument("--detail", action="store_true")
    parser.add_argument("--full-text", action="store_true")
    args = parser.parse_args()
    try:
        if args.session_jsonl:
            if args.output:
                raise ValueError("JSONL session writes responses to stdout, not --output")
            with EquipmentSession() as session:
                for line in sys.stdin:
                    if not line.strip():
                        continue
                    try:
                        result = execute(json.loads(line), args.evidence_root or Path.cwd(), equipment_runner=session.request)
                    except (ValueError, OSError, KeyError, TypeError, TimeoutError) as exc:
                        result = {"status": "NOT_COMPLETED", "error": str(exc)}
                    print(json.dumps(result, ensure_ascii=False, allow_nan=False), flush=True)
            return 0
        if args.query or args.node_id:
            result = search(args.query or "", args.corpus, args.limit, args.vector,
                            node_id=args.node_id, detail=args.detail, full_text=args.full_text)
        elif args.describe or args.schema:
            result = execute({"operation": "schema" if args.schema else "capabilities",
                              "payload": {"schema_id": args.schema}}, args.evidence_root or Path.cwd())
        elif args.request:
            request_path = None if args.request == "-" else Path(args.request)
            content = sys.stdin.read() if request_path is None else request_path.read_text(encoding="utf-8-sig")
            result = execute(json.loads(content), args.evidence_root or (request_path.resolve().parent if request_path else Path.cwd()))
        content = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(content)
        else:
            print(content, end="")
        return 0
    except (ValueError, OSError, KeyError, TypeError, TimeoutError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "NOT_COMPLETED", "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
