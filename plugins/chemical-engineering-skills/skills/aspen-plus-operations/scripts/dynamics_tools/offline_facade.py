"""Typed, read-only facade over toolpack. No independent checking algorithms."""
from __future__ import annotations

from functools import wraps
from typing import Any

if __package__:
    from . import toolpack
else:
    import toolpack


def _diagnostic(function):
    @wraps(function)
    def checked(*args, **kwargs):
        try:
            result = function(*args, **kwargs)
            return {**result, "status": "ok", "external_process_started": False,
                    "strict_simulation_passed": False,
                    "native_calculation_acceptance": "not_assessed",
                    "engineering_acceptance": "not_assessed"}
        except (OSError, ValueError, TypeError, KeyError, ImportError, AttributeError, OverflowError) as exc:
            return {"status": "invalid_or_unavailable", "error": str(exc),
                    "external_process_started": False, "strict_simulation_passed": False,
                    "native_calculation_acceptance": "not_assessed",
                    "engineering_acceptance": "not_assessed"}
    return checked


def _path(value, label, optional=False):
    if optional and value is None:
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + " must be a nonblank path string")
    return value


@_diagnostic
def verify_package_manifest(root: str, manifest_path: str) -> dict[str, Any]:
    """Check only listed file bytes; no dependency completeness or native run."""
    return toolpack.verify_manifest(_path(root, "root"), _path(manifest_path, "manifest_path"))


@_diagnostic
def check_csv_grid(csv_path: str, time_column: str, interval: float, start: float,
                   end: float, time_abs_tolerance: float,
                   numeric_columns: list[str] | None = None) -> dict[str, Any]:
    """Check a supplied CSV grid with explicit caller units and time tolerance."""
    _path(csv_path, "csv_path")
    if not isinstance(time_column, str) or not time_column.strip():
        raise ValueError("time_column must be nonblank")
    if numeric_columns is not None and (not isinstance(numeric_columns, list)
            or any(not isinstance(x, str) or not x.strip() for x in numeric_columns)):
        raise ValueError("numeric_columns must be a list of nonblank column names")
    for value in (interval, start, end, time_abs_tolerance):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Grid numbers must be JSON numbers, not booleans or strings")
    return toolpack.check_grid(csv_path, time_column=time_column, interval=interval,
                              start=start, end=end, tolerance=time_abs_tolerance,
                              numeric_columns=numeric_columns or ())


@_diagnostic
def inspect_history(history_path: str, operations_root: str | None = None,
                    verified_encoding: str | None = None,
                    expected_owner_sha256: str | None = None) -> dict[str, Any]:
    """Delegate to the public parser; fallback requires an explicit raw SHA256."""
    _path(history_path, "history_path")
    _path(operations_root, "operations_root", optional=True)
    if verified_encoding is not None and (not isinstance(verified_encoding, str) or not verified_encoding.strip()):
        raise ValueError("verified_encoding must be an independently verified nonblank encoding name")
    return toolpack.history_report(history_path, operations_root, verified_encoding,
                                   expected_owner_sha256)


@_diagnostic
def list_external_tools(settings_path: str | None = None) -> dict[str, Any]:
    """List external dependencies and path existence; never start a service."""
    return toolpack.local_catalog(_path(settings_path, "settings_path", optional=True))


@_diagnostic
def plan_external_invocation(tool_id: str, settings_path: str | None = None) -> dict[str, Any]:
    """Print argv/cwd only. File existence is not an import or service test."""
    if not isinstance(tool_id, str) or not tool_id.strip():
        raise ValueError("tool_id must be a nonblank string")
    return toolpack.invocation_plan(tool_id, _path(settings_path, "settings_path", optional=True))


TOOLS = (verify_package_manifest, check_csv_grid, inspect_history,
         list_external_tools, plan_external_invocation)
