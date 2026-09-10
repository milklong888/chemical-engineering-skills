#!/usr/bin/env python3
"""Local stdio MCP surface for knowledge, equipment, pressure and process plans.

No GUI, remote model calls or automatic Aspen launch. Reuses expert_cli and the
existing equipment/knowledge implementations instead of a separate matcher.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
from contextlib import asynccontextmanager

os.environ["FASTMCP_CHECK_FOR_UPDATES"] = "off"
os.environ["FASTMCP_SHOW_SERVER_BANNER"] = "false"
os.environ["FASTMCP_ENV_FILE"] = os.devnull
sys.dont_write_bytecode = True

from fastmcp import FastMCP
from expert_cli import search, execute, EquipmentSession

_session = None


@asynccontextmanager
async def lifespan(server):
    global _session
    with EquipmentSession() as session:
        _session = session
        try:
            yield {}
        finally:
            _session = None


def equipment_runner(request):
    if _session is None:
        raise ValueError("MCP equipment session is outside its active lifespan")
    return _session.request(request)


mcp = FastMCP("chemical-engineering-expert-local", lifespan=lifespan)


@mcp.tool()
def knowledge_search(query: str = "", corpus: str = "all", limit: int = 5, vector: bool = False,
                     package_ids: list[str] | None = None, node_id: str | None = None,
                     detail: bool = False, full_text: bool = False) -> dict:
    """Search bundled original concept/method cards and equipment facts with scope."""
    return search(query, corpus, limit, vector, package_ids, node_id, detail, full_text,
                  equipment_runner=equipment_runner)


@mcp.tool()
def equipment_calculate(request: dict) -> dict:
    """Run the original deterministic JSON equipment backend; no COM/LLM/GUI."""
    return equipment_runner(request)


@mcp.tool()
def equipment_batch(requests: list[dict]) -> dict:
    """Process ordered local equipment requests using the same resident worker; retain per-request failures."""
    return execute({"operation": "equipment_batch", "payload": {"requests": requests}}, Path.cwd(), equipment_runner=equipment_runner)


@mcp.tool()
def product_describe(schema_id: str | None = None) -> dict:
    """Discover actual bundled capabilities, installed Skill paths and input schemas; no remote software launch."""
    return execute({"operation": "schema" if schema_id else "capabilities", "payload": {"schema_id": schema_id}}, Path.cwd(), equipment_runner=equipment_runner)


@mcp.tool()
def pressure_calculate(method: str, inputs: dict) -> dict:
    """Calculate declared-basis loss/staging/branch identities, not software rating."""
    return execute({"operation": "pressure", "payload": {"method": method, "inputs": inputs}}, Path.cwd())


@mcp.tool()
def process_feedback(payload: dict, evidence_root: str) -> dict:
    """Calculate equipment and return evidence-bound model revision/replay steps.

    evidence_root is explicitly supplied by the caller for this task's hash-bound
    JSON artifacts. This tool never changes or runs an Aspen model.
    """
    return execute({"operation": "feedback", "payload": payload}, Path(evidence_root), equipment_runner=equipment_runner)


@mcp.tool()
def process_replay_audit(payload: dict, evidence_root: str) -> dict:
    """Audit exact model/source/plan linkage of downstream domain validation receipts."""
    return execute({"operation": "replay_audit", "payload": payload}, Path(evidence_root))


@mcp.tool()
def aspen_solve_route(payload: dict, evidence_root: str) -> dict:
    """Choose existing native solve/read/fit methods; never creates, runs or accepts Aspen.

    Payload: current question and optional registered intents. Does not require
    an equipment inventory. Discover the contract with schema_id='solve-route'.
    Finite language rules are hints; unrecognized intent requires agent review.
    """
    return execute({"operation": "solve_route", "payload": payload}, Path(evidence_root))


@mcp.tool()
def design_stage_check(payload: dict, evidence_root: str) -> dict:
    """Run current-stage knowledge/equipment modules; return needs, never engineering acceptance.

    Discover payload fields through product_describe(schema_id="design-stage").
    Source can start with only stage/question. Later stages require current
    source/authority identity and per-physical-device requests for coverage.
    """
    return execute({"operation": "design_stage", "payload": payload}, Path(evidence_root), equipment_runner=equipment_runner)


if __name__ == "__main__":
    mcp.run(transport="stdio")
