#!/usr/bin/env python3
"""Local stdio MCP surface for knowledge, equipment, pressure and process plans.

No GUI, remote model calls or automatic Aspen launch. Reuses expert_cli and the
existing equipment/knowledge implementations instead of a separate matcher.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys

os.environ["FASTMCP_CHECK_FOR_UPDATES"] = "off"
os.environ["FASTMCP_SHOW_SERVER_BANNER"] = "false"
os.environ["FASTMCP_ENV_FILE"] = os.devnull
sys.dont_write_bytecode = True

from fastmcp import FastMCP
from expert_cli import search, equipment, execute

mcp = FastMCP("chemical-engineering-expert-local")


@mcp.tool()
def knowledge_search(query: str, corpus: str = "all", limit: int = 5, vector: bool = False, package_ids: list[str] | None = None) -> dict:
    """Search bundled original concept/method cards and equipment facts with scope."""
    return search(query, corpus, limit, vector, package_ids)


@mcp.tool()
def equipment_calculate(request: dict) -> dict:
    """Run the original deterministic JSON equipment backend; no COM/LLM/GUI."""
    return equipment(request)


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
    return execute({"operation": "feedback", "payload": payload}, Path(evidence_root))


@mcp.tool()
def process_replay_audit(payload: dict, evidence_root: str) -> dict:
    """Audit exact model/source/plan linkage of downstream domain validation receipts."""
    return execute({"operation": "replay_audit", "payload": payload}, Path(evidence_root))


if __name__ == "__main__":
    mcp.run(transport="stdio")
