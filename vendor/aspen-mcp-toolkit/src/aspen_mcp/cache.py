"""JSON cache + tool call log for Aspen Plus MCP.

Stores sensitivity results and tool call history in a local JSON file.
No external dependencies — uses only Python standard library.
Path: aspen_mcp_cache.json in the plugin root directory.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..")
_CACHE_FILE = os.path.join(_CACHE_DIR, "aspen_mcp_cache.json")


def _load() -> dict[str, Any]:
    """Load the full cache dict from disk."""
    if not os.path.exists(_CACHE_FILE):
        return {"sensitivity": [], "calls": [], "snapshots": {}}
    try:
        with open(_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"sensitivity": [], "calls": [], "snapshots": {}}


def _save(data: dict[str, Any]) -> None:
    """Write the full cache dict to disk."""
    try:
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError:
        pass  # silently ignore write errors


# --- Tool call log -----------------------------------------------------------


def log_call(tool_name: str, args: dict[str, Any], result_summary: str,
             ok: bool = True) -> None:
    """Record one tool invocation to the call log."""
    data = _load()
    entry = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tool": tool_name,
        "args": {k: str(v) for k, v in sorted(args.items())},
        "result": result_summary[:200],
        "ok": ok,
    }
    data["calls"].append(entry)
    # Keep last 200 calls
    if len(data["calls"]) > 200:
        data["calls"] = data["calls"][-200:]
    _save(data)


def get_call_log(limit: int = 20) -> list[dict[str, Any]]:
    """Return the most recent tool calls."""
    data = _load()
    return data["calls"][-limit:]


def clear_call_log() -> str:
    """Clear the call log."""
    data = _load()
    data["calls"] = []
    _save(data)
    return "Call log cleared."


# --- Sensitivity results cache -----------------------------------------------


def save_sensitivity(title: str, variable: str, linked_params: dict[str, float],
                     results: list[dict[str, Any]]) -> None:
    """Save a sensitivity analysis run to cache."""
    data = _load()
    entry = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "title": title,
        "variable": variable,
        "linked_params": linked_params,
        "results": results,
    }
    data["sensitivity"].append(entry)
    _save(data)


def get_sensitivity_history() -> list[dict[str, Any]]:
    """Return all saved sensitivity runs."""
    data = _load()
    return data["sensitivity"]


def clear_sensitivity() -> str:
    """Clear all cached sensitivity results."""
    data = _load()
    data["sensitivity"] = []
    _save(data)
    return "Sensitivity cache cleared."
