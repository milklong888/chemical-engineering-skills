"""Error handling decorators for MCP tools.

Provides a single @mcp_tool decorator that catches exceptions and returns
a consistent error format based on the function's return type annotation:

    str  -> "Error: <message>"
    dict -> {"error": "<message>"}
    list -> ["Error: <message>"]

Usage::

    from ._error import mcp_tool

    @mcp_tool
    def tool_my_action(name: str) -> str:
        ...  # no try/except needed for generic errors

Functions with *specific* error handling (e.g. COM recovery hints)
should keep their inner try/except and re-raise for generic cases —
the decorator catches the re-raised exception and formats it.
"""

from __future__ import annotations

from functools import wraps
from typing import Callable, get_origin, get_type_hints


def _is_list_type(tp) -> bool:
    """Check whether a type annotation represents a list type."""
    if tp is list:
        return True
    try:
        return get_origin(tp) is list
    except Exception:
        return False


def _is_dict_type(tp) -> bool:
    """Check whether a type annotation represents a dict type."""
    if tp is dict:
        return True
    try:
        return get_origin(tp) is dict
    except Exception:
        return False


def mcp_tool(fn: Callable) -> Callable:
    """Decorator: catch exceptions and return a consistent error string.

    Inspects the function's return-type annotation to choose the error format:

    * ``-> list`` / ``-> list[...]``  →  ``["Error: <msg>"]``
    * ``-> dict`` / ``-> dict[...]``  →  ``{"error": "<msg>"}``
    * everything else (str, Any, None, …) → ``"Error: <msg>"``

    Preserves the original return type on error so callers are not broken.
    """
    # ── inspect the return-type annotation ──────────────────────────
    try:
        hints = get_type_hints(fn)
        ret_type = hints.get("return", None)
    except Exception:
        ret_type = None

    if _is_list_type(ret_type):
        _error_fmt = lambda exc: [f"Error: {exc}"]
    elif _is_dict_type(ret_type):
        _error_fmt = lambda exc: {"error": str(exc)}
    else:
        _error_fmt = lambda exc: f"Error: {exc}"

    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            return _error_fmt(exc)

    return wrapper
