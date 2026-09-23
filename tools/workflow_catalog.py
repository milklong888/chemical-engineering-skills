"""Read-only catalog for the bundled chemical-engineering workflow assets."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path
from typing import Any

from tools.product_contract import skill_location

RESOURCE_REGISTRY = {
    "native-tools": "aspen-document-driven-flowsheet/references/aspen_builtin_solve_fit_tools.md",
    "tower-method": "aspen-tower-optimization-workflow/references/tower_optimization_workflow.md",
    "unit-build": "aspen-plus-operations/references/unit_modeling_workflow.md",
    "script-catalog": "aspen-document-driven-flowsheet/references/script_template_catalog.md",
}
OFFICIAL_SKILL_IDS = frozenset({
    "aspen-adaptive-generalization-loop", "aspen-document-driven-flowsheet",
    "aspen-edr-rating-delivery", "aspen-flowsheet-cost-skill-builder",
    "aspen-flowsheet-error-repair", "aspen-heat-pump-distillation-replacement",
    "aspen-kinetics-documentation", "aspen-non-reactor-equipment-cost",
    "aspen-plus-operations", "aspen-plus-template", "aspen-pressure-pfd-delivery",
    "aspen-tower-optimization-workflow", "aspen-two-section-flowsheet",
    "chemical-engineering-expert", "chemical-equipment-selection-audit",
    "chemical-tower-design", "equipment-design-app", "subagent-dispatch",
    "sw6-scripted-equipment-design",
})
SCRIPT_KEYS = {"id", "cluster", "search", "path_name"}
WORKFLOW_KEYS = {"action", "skill_id", "resource", "mode", "id", "cluster", "search", "path_name"}
ACTIONS = {"list", "read", "script"}
MODES = {"skill", "resource"}


def _skills_root() -> Path:
    location = skill_location()
    if not location.get("available") or not location.get("path"):
        raise ValueError("Chemical-engineering skill root is unavailable")
    skill = Path(location["path"]).resolve()
    root = skill.parent.parent.resolve()
    if skill.name != "SKILL.md" or skill.parent.parent != root:
        raise ValueError("Invalid installed skill location")
    if not skill.is_file() or not root.is_dir():
        raise ValueError("Chemical-engineering skill root is unavailable")
    return root


def _safe_file(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError("Only registered relative asset paths are accepted")
    raw = root / relative
    cursor = root
    for part in Path(relative).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError("Symlink assets are not accepted")
    candidate = raw.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("Asset path escapes the registered skill root") from exc
    return candidate


def _asset(path: Path, *, kind: str, name: str) -> dict[str, Any]:
    if not path.is_file():
        return {"name": name, "kind": kind, "available": False, "path": str(path), "sha256": None, "text": None}
    data = path.read_bytes()
    return {"name": name, "kind": kind, "available": True, "path": str(path),
            "sha256": hashlib.sha256(data).hexdigest(), "text": data.decode("utf-8-sig")}


def _skill_ids(root: Path) -> list[str]:
    actual = {p.name for p in root.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()}
    if not OFFICIAL_SKILL_IDS.issubset(actual):
        missing = sorted(OFFICIAL_SKILL_IDS - actual)
        raise ValueError(f"Official skill IDs missing: {missing}")
    return sorted(OFFICIAL_SKILL_IDS)


def _require_text(payload: dict[str, Any], key: str, *, required: bool = False) -> str | None:
    value = payload.get(key)
    if value is None and not required:
        return None
    if type(value) is not str or not value.strip():
        raise ValueError(f"{key} must be a nonempty string")
    return value


def _anchor(root: Path, base: Any) -> dict[str, Any]:
    if type(base) is not str or not re.fullmatch(r"[A-Za-z0-9_-]+\.py", base):
        return {"base": base, "path": None, "exists": False, "registered": False}
    candidates = [
        f"aspen-document-driven-flowsheet/scripts/templates/{base}",
        f"aspen-document-driven-flowsheet/scripts/{base}",
    ]
    for relative in candidates:
        path = _safe_file(root, relative)
        if path.is_file():
            return {"base": base, "path": str(path), "exists": True, "registered": True}
    return {"base": base, "path": None, "exists": False, "registered": False}


def _decorate_node(root: Path, node: dict[str, Any]) -> dict[str, Any]:
    result = dict(node)
    result["anchor"] = _anchor(root, node.get("base"))
    result["adaptation_boundary"] = "Template/action metadata only; not proof of tested native card creation"
    return result


def _graph_query(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    for key in SCRIPT_KEYS:
        if key in payload:
            _require_text(payload, key, required=True)
    if payload.get("path_name") and set(payload) & {"id", "cluster", "search"}:
        raise ValueError("canonical path and node filters are separate query modes")
    graph_path = _safe_file(root, "aspen-document-driven-flowsheet/references/script_template_knowledge_graph.json")
    loader_path = _safe_file(root, "aspen-document-driven-flowsheet/scripts/query_script_template_graph.py")
    spec = importlib.util.spec_from_file_location("workflow_script_graph", loader_path)
    if spec is None or spec.loader is None:
        raise ValueError("Script graph query helper is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    graph = module.load_graph(graph_path)
    if payload.get("path_name"):
        name = payload["path_name"]
        paths = graph.get("canonical_paths", {})
        if name not in paths:
            raise ValueError("Unknown canonical script path")
        nodes_by_id = {node.get("id"): node for node in graph.get("nodes", [])}
        if any(node_id not in nodes_by_id for node_id in paths[name]):
            raise ValueError("Canonical path contains an unresolved graph node")
        expanded = [_decorate_node(root, nodes_by_id[node_id]) for node_id in paths[name]
                    if node_id in nodes_by_id]
        return {"kind": "script_graph_path", "path_name": name, "nodes": expanded,
                "graph_path": str(graph_path),
                "anchor_summary": {"existing": sum(n["anchor"]["exists"] for n in expanded),
                                   "missing": sum(not n["anchor"]["exists"] for n in expanded)},
                "adaptation_boundary": "Canonical template path only; no node or anchor is executable through this API"}
    args = type("Args", (), {"node_id": payload.get("id"), "cluster": payload.get("cluster"),
                              "search": payload.get("search")})()
    nodes = [_decorate_node(root, node) for node in graph.get("nodes", []) if module.match_node(node, args)]
    return {"kind": "script_graph_nodes", "nodes": nodes, "graph_path": str(graph_path),
            "query": {key: payload.get(key) for key in SCRIPT_KEYS if payload.get(key) is not None},
            "anchor_summary": {"existing": sum(n["anchor"]["exists"] for n in nodes),
                               "missing": sum(not n["anchor"]["exists"] for n in nodes)},
            "adaptation_boundary": "Template/action metadata only; no node or anchor is executable through this API"}


def lookup(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict) or set(payload) - WORKFLOW_KEYS:
        raise ValueError("workflow accepts only registered fields")
    action = payload.get("action", "list")
    if type(action) is not str or not action.strip():
        raise ValueError("action must be a nonempty string")
    if action not in ACTIONS:
        raise ValueError("Unknown workflow action")
    root = _skills_root()
    ids = _skill_ids(root)
    if len(ids) != 19:
        raise ValueError(f"Expected 19 registered skills, found {len(ids)}")
    if action == "list":
        if set(payload) != {"action"}:
            raise ValueError("list action accepts only action")
        return {"schema": "chemical-engineering-workflow-catalog-v1", "action": action,
                "skill_ids": ids, "resources": sorted(RESOURCE_REGISTRY),
                "read_only": True, "engineering_accepted": False,
                "boundary": "Read-only guidance/catalog; no skill or script execution"}
    if action == "script":
        if set(payload) - ({"action"} | SCRIPT_KEYS):
            raise ValueError("script action accepts only graph query fields")
        result = _graph_query(root, payload)
        return {"schema": "chemical-engineering-workflow-catalog-v1", "action": action,
                "result": result, "read_only": True, "engineering_accepted": False,
                "boundary": "Read-only graph metadata; no skill or script execution"}
    mode = payload.get("mode", "skill")
    if type(mode) is not str or mode not in MODES:
        raise ValueError("Unknown workflow read mode")
    if mode == "skill":
        skill_id = _require_text(payload, "skill_id", required=True)
        if skill_id not in ids:
            raise ValueError("Unknown skill_id")
        if set(payload) - {"action", "skill_id", "mode"}:
            raise ValueError("skill read accepts only skill_id")
        asset = _asset(_safe_file(root, f"{skill_id}/SKILL.md"), kind="skill", name=skill_id)
    else:
        resource = _require_text(payload, "resource", required=True)
        if resource not in RESOURCE_REGISTRY:
            raise ValueError("Unknown registered resource")
        if set(payload) - {"action", "resource", "mode"}:
            raise ValueError("resource read accepts only resource")
        asset = _asset(_safe_file(root, RESOURCE_REGISTRY[resource]), kind="resource", name=resource)
    return {"schema": "chemical-engineering-workflow-catalog-v1", "action": action,
            "result": asset, "read_only": True, "engineering_accepted": False,
            "boundary": "Read-only guidance; no skill or script execution; does not prove execution or acceptance"}
