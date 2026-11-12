"""Discover normalized modules and call nine explicit offline diagnostics."""
from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
TOOLS = {
    **{f"dynamics.{name}": ("aspen-plus-operations", "scripts/dynamics_tools/offline_facade.py", name, "kwargs")
       for name in ("verify_package_manifest", "check_csv_grid", "inspect_history", "list_external_tools", "plan_external_invocation")},
    **{f"edr.{name}": ("aspen-edr-rating-delivery", "scripts/engineering_checks.py", name, "request")
       for name in ("screen_pipe_candidates", "check_exchanger_basis", "check_packed_beds", "audit_edr_geometry")},
}


def skills_root() -> Path:
    bundled = ROOT / "plugins/chemical-engineering-skills/skills"
    if bundled.is_dir():
        return bundled
    receipt = ROOT.parent / "CHEMICAL_SKILLS_INSTALLATION.json"
    if receipt.is_file():
        data = json.loads(receipt.read_text(encoding="utf-8-sig"))
        if (data.get("schema") == "chemical-skills-installation-paths-v1"
                and Path(data.get("runtime_root", "")).resolve() == ROOT.resolve()
                and Path(data.get("workspace_root", "")).resolve() == ROOT.parent.resolve()):
            return Path(data["skills_root"]).resolve()
    raise ValueError("No verified bundled or explicit installed skills root")


def catalog(payload: dict | None = None) -> dict:
    payload = {} if payload is None else payload
    if not isinstance(payload, dict) or set(payload) - {"module_id", "include_archives"}:
        raise ValueError("Catalog accepts module_id and include_archives only")
    if type(payload.get("include_archives", False)) is not bool:
        raise ValueError("include_archives must be boolean")
    if "module_id" in payload and (not isinstance(payload["module_id"], str) or not payload["module_id"].strip()):
        raise ValueError("module_id must be nonblank")
    data = json.loads((ROOT / "runtime/module_catalog.json").read_text(encoding="utf-8"))
    rows = data["modules"]
    if not payload.get("include_archives", False):
        rows = [row for row in rows if row["migration_action"] != "excluded_archive"]
    if "module_id" in payload:
        rows = [row for row in rows if row["id"] == payload["module_id"]]
        if not rows:
            raise ValueError("Unknown or excluded module_id")
    return {"schema": data["schema"], "modules": rows,
            "proposal_dispositions": data["proposal_dispositions"],
            "callable_tools": {key: {"owner": value[0], "function": value[2], "input_mode": value[3]}
                               for key, value in TOOLS.items()},
            "native_calculation_acceptance": "not_assessed", "engineering_acceptance": "not_assessed"}


def _load(owner: str, relative: str):
    file = skills_root() / owner / relative
    if not file.is_file():
        raise ValueError("Declared professional tool is not installed")
    identity = hashlib.sha256(str(file.resolve()).encode("utf-8")).hexdigest()[:16]
    package_name = "_chemical_module_" + identity
    if relative.endswith("offline_facade.py"):
        # A unique namespace keeps source and installed copies separate in tests.
        if package_name not in sys.modules:
            package = ModuleType(package_name)
            package.__path__ = [str(file.parent)]
            sys.modules[package_name] = package
        return importlib.import_module(package_name + ".offline_facade")
    if package_name not in sys.modules:
        spec = importlib.util.spec_from_file_location(package_name, file)
        if spec is None or spec.loader is None:
            raise ValueError("Professional implementation cannot be loaded")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules[package_name] = module
    return sys.modules[package_name]


def call(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != {"tool", "inputs"}:
        raise ValueError("module_check requires exactly tool and inputs")
    if not isinstance(payload["tool"], str) or payload["tool"] not in TOOLS:
        raise ValueError("Tool is not in the offline allowlist")
    if not isinstance(payload["inputs"], dict):
        raise ValueError("inputs must be an object")
    owner, relative, function, mode = TOOLS[payload["tool"]]
    implementation = getattr(_load(owner, relative), function)
    try:
        result = implementation(payload["inputs"]) if mode == "request" else implementation(**payload["inputs"])
    except (TypeError, ValueError, OverflowError) as exc:
        return {"tool": payload["tool"], "status": "invalid_input", "error": str(exc),
                "native_calculation_acceptance": "not_assessed", "engineering_acceptance": "not_assessed"}
    return {"tool": payload["tool"], "status": "completed", "result": result,
            "native_calculation_acceptance": "not_assessed", "engineering_acceptance": "not_assessed"}


def schema() -> dict:
    return {"schema": "module-tools", "catalog_operation": "module_catalog",
            "check_operation": "module_check", "required_payload": ["tool", "inputs"],
            "tools": catalog()["callable_tools"],
            "input_contract": "Dynamics uses named arguments; EDR uses its documented request object. No numeric coercion is performed.",
            "acceptance": "Read-only diagnostics; external plans are never executed; not native simulation or engineering acceptance"}
