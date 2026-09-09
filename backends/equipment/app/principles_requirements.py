from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


APP_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = APP_DIR.parent
DEFAULT_GRAPH_DIR = PACKAGE_ROOT / "data" / "principles_equipment_requirements"
GRAPH_SCHEMA = "principles-equipment-requirement-graph-v1"
NODE_TYPES = {"input", "calculation", "decision", "output", "gate"}
RELATIONS = {
    "requires",
    "produces",
    "supports",
    "blocks_when_missing",
    "must_precede",
}
SOURCE_CLASSES = {"PRINCIPLES_METHOD", "ENGINEERING_METHOD"}
SOURCE_ROLE = "METHOD_SOURCE_NOT_PROJECT_VALUE_AUTHORITY"
READINESS_LEVELS = ("screening", "concrete_candidate", "formal_release")


class RequirementGraphError(ValueError):
    pass


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()


def _nonempty_text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise RequirementGraphError(f"{label} must be non-empty")
    return text


def validate_requirement_graph(graph: Any) -> dict[str, Any]:
    if not isinstance(graph, dict):
        raise RequirementGraphError("requirement graph must be an object")
    if graph.get("schema") != GRAPH_SCHEMA:
        raise RequirementGraphError(f"schema must be {GRAPH_SCHEMA}")
    _nonempty_text(graph.get("equipment_family"), "equipment_family")

    source = graph.get("source")
    if not isinstance(source, dict):
        raise RequirementGraphError("source must be an object")
    _nonempty_text(source.get("source_id"), "source.source_id")
    _nonempty_text(source.get("title"), "source.title")
    _nonempty_text(source.get("chapter"), "source.chapter")
    if source.get("source_class") not in SOURCE_CLASSES:
        raise RequirementGraphError("source.source_class is not allowlisted")
    if source.get("source_role") != SOURCE_ROLE:
        raise RequirementGraphError(
            "source.source_role must preserve the method-only claim boundary"
        )
    _nonempty_text(source.get("source_file_name"), "source.source_file_name")
    source_sha256 = str(source.get("source_sha256") or "")
    if len(source_sha256) != 64 or any(
        character not in "0123456789ABCDEF" for character in source_sha256
    ):
        raise RequirementGraphError(
            "source.source_sha256 must be an uppercase SHA-256 digest"
        )

    claim_boundary = graph.get("claim_boundary")
    if not isinstance(claim_boundary, dict):
        raise RequirementGraphError("claim_boundary must be an object")
    for field in (
        "project_values_from_book_forbidden",
        "standard_status_requires_authority_check",
        "formal_release_requires_same_case_evidence",
    ):
        if claim_boundary.get(field) is not True:
            raise RequirementGraphError(f"claim_boundary.{field} must be true")

    nodes = graph.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise RequirementGraphError("nodes must be a non-empty list")
    node_ids: set[str] = set()
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise RequirementGraphError(f"nodes[{index}] must be an object")
        node_id = _nonempty_text(node.get("id"), f"nodes[{index}].id")
        if node_id in node_ids:
            raise RequirementGraphError(f"duplicate node id: {node_id}")
        node_ids.add(node_id)
        if node.get("type") not in NODE_TYPES:
            raise RequirementGraphError(f"nodes[{index}].type is not allowlisted")
        _nonempty_text(node.get("name"), f"nodes[{index}].name")
        _nonempty_text(node.get("description"), f"nodes[{index}].description")
        anchors = node.get("source_anchors")
        if not isinstance(anchors, list) or not anchors:
            raise RequirementGraphError(
                f"nodes[{index}].source_anchors must be non-empty"
            )
        for anchor_index, anchor in enumerate(anchors):
            if not isinstance(anchor, dict):
                raise RequirementGraphError(
                    f"nodes[{index}].source_anchors[{anchor_index}] must be an object"
                )
            _nonempty_text(
                anchor.get("section"),
                f"nodes[{index}].source_anchors[{anchor_index}].section",
            )
        field_ids = node.get("field_ids", [])
        if not isinstance(field_ids, list):
            raise RequirementGraphError(f"nodes[{index}].field_ids must be a list")
        if any(not str(field or "").strip() for field in field_ids):
            raise RequirementGraphError(
                f"nodes[{index}].field_ids cannot contain blank values"
            )
        required_for = node.get("required_for", [])
        if not isinstance(required_for, list) or any(
            level not in READINESS_LEVELS for level in required_for
        ):
            raise RequirementGraphError(
                f"nodes[{index}].required_for contains an invalid readiness level"
            )

    edges = graph.get("edges")
    if not isinstance(edges, list):
        raise RequirementGraphError("edges must be a list")
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            raise RequirementGraphError(f"edges[{index}] must be an object")
        start = _nonempty_text(edge.get("from"), f"edges[{index}].from")
        end = _nonempty_text(edge.get("to"), f"edges[{index}].to")
        if start not in node_ids or end not in node_ids:
            raise RequirementGraphError(
                f"edges[{index}] references an unknown node"
            )
        if edge.get("relation") not in RELATIONS:
            raise RequirementGraphError(
                f"edges[{index}].relation is not allowlisted"
            )

    return graph


def load_requirement_graph(
    path: Path | str,
    *,
    validate: bool = True,
) -> dict[str, Any]:
    graph_path = Path(path)
    try:
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RequirementGraphError(
            f"cannot load requirement graph {graph_path}: {exc}"
        ) from exc
    if validate:
        validate_requirement_graph(graph)
    graph = dict(graph)
    graph["graph_path"] = str(graph_path.resolve())
    graph["graph_sha256"] = _canonical_sha256(
        {key: value for key, value in graph.items() if key not in {"graph_path", "graph_sha256"}}
    )
    return graph


def iter_requirement_graph_paths(
    graph_dir: Path | str = DEFAULT_GRAPH_DIR,
) -> Iterable[Path]:
    root = Path(graph_dir)
    if not root.is_dir():
        return ()
    return tuple(
        path
        for path in sorted(root.glob("*_requirement_graph.json"))
        if path.name != "principles_equipment_requirement_graph.schema.json"
    )


def load_requirement_graphs(
    graph_dir: Path | str = DEFAULT_GRAPH_DIR,
) -> list[dict[str, Any]]:
    return [load_requirement_graph(path) for path in iter_requirement_graph_paths(graph_dir)]


def requirement_field_index(graphs: Iterable[dict[str, Any]]) -> dict[str, Any]:
    index: dict[str, dict[str, set[str]]] = {}
    evidence: dict[str, list[dict[str, Any]]] = {}
    for raw_graph in graphs:
        graph = validate_requirement_graph(raw_graph)
        family = str(graph["equipment_family"])
        by_level = index.setdefault(
            family,
            {level: set() for level in READINESS_LEVELS},
        )
        evidence.setdefault(family, []).append(
            {
                "title": graph["source"]["title"],
                "chapter": graph["source"]["chapter"],
                "source_class": graph["source"]["source_class"],
                "source_id": graph["source"]["source_id"],
                "source_sha256": graph["source"]["source_sha256"],
                "graph_sha256": raw_graph.get("graph_sha256")
                or _canonical_sha256(raw_graph),
            }
        )
        for node in graph["nodes"]:
            fields = {
                str(field).strip()
                for field in node.get("field_ids", [])
                if str(field).strip()
            }
            for level in node.get("required_for", []):
                by_level[level].update(fields)
    return {
        "schema": "principles-equipment-requirement-index-v1",
        "families": {
            family: {
                "required_fields": {
                    level: sorted(fields)
                    for level, fields in levels.items()
                },
                "method_sources": evidence.get(family, []),
            }
            for family, levels in sorted(index.items())
        },
        "claim_boundary": {
            "method_sources_never_supply_project_values": True,
            "missing_fields_block_promotion_only_when_graph_marks_them_required": True,
        },
    }


def assess_requirement_coverage(
    equipment_family: str,
    values: dict[str, Any],
    index: dict[str, Any],
) -> dict[str, Any]:
    family = str(equipment_family or "").strip()
    family_entry = (index.get("families") or {}).get(family)
    if not isinstance(family_entry, dict):
        return {
            "schema": "principles-equipment-requirement-coverage-v1",
            "equipment_family": family,
            "status": "NOT_COVERED",
            "covered_by_method_graph": False,
            "highest_ready_level": None,
            "missing_by_level": {},
        }

    required_fields = family_entry.get("required_fields") or {}
    present_fields = {
        str(field)
        for field, value in values.items()
        if value is not None and (not isinstance(value, str) or value.strip())
    }
    missing_by_level: dict[str, list[str]] = {}
    highest_ready_level: str | None = None
    for level in READINESS_LEVELS:
        required = set(required_fields.get(level) or [])
        missing = sorted(required - present_fields)
        missing_by_level[level] = missing
        if not missing:
            highest_ready_level = level

    return {
        "schema": "principles-equipment-requirement-coverage-v1",
        "equipment_family": family,
        "status": (
            "FORMAL_INPUT_SET_COVERED"
            if highest_ready_level == "formal_release"
            else "PRELIMINARY_INPUT_GAPS"
        ),
        "covered_by_method_graph": True,
        "highest_ready_level": highest_ready_level,
        "missing_by_level": missing_by_level,
        "method_sources": family_entry.get("method_sources", []),
        "claim_boundary": (
            "Input coverage does not prove calculations, engineering checks, "
            "standard applicability, vendor performance, or formal release."
        ),
    }
