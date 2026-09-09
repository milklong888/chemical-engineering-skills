#!/usr/bin/env python3
"""Fail-closed validation for semantic source recovery and quantitative models."""

from __future__ import annotations

import argparse
import ast
import csv
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


SEMANTIC_STATUS = "SEMANTIC_CONTEXT_RESOLVED"
VISUAL_STATUSES = {
    "VISUAL_GLYPH_VERIFIED",
    "VISUAL_GLYPH_CONFIRMED",
    "VISUAL_HEADER_VERIFIED",
}
NONTERMINAL_STATUS_MARKERS = (
    "_CANDIDATE",
    "OPEN",
    "PENDING",
    "AMBIGUOUS",
    "UNREADABLE_BLOCKED",
)
GENERIC_CONTEXT_FRAGMENTS = (
    "same page",
    "same column",
    "adjacent logical row",
    "where applicable",
    "full-page image + same physical merge + row identity",
)
CONCRETE_REF = re.compile(
    r"(?:p\d{3,4}|r\d{1,3}c\d{1,3}|r\d{1,3}:c\d{1,3}|"
    r"table[_ :\-]?\d+|header\s*[:=]|unit\s*[:=]|formula\s*[:=]|bbox\s*[:=])",
    re.IGNORECASE,
)
VALUE_KINDS = {
    "numeric", "range", "enumeration", "categorical", "ordinal",
    "boolean", "formula", "relation",
}
NUMERIC_SOURCE = re.compile(
    r"(?:[<>=≤≥]\s*[-+]?\d|[-+]?\d(?:[.,]\d+)?\s*(?:～|~|\.\.|mPa|Pa|MPa|"
    r"r/min|s\^-?1|m/s|mm|cm|m|°|deg|%))",
    re.IGNORECASE,
)
RANGE_BEARING_SOURCE = re.compile(r"\d(?:[.,]\d+)?\s*(?:～|~|\.\.)\s*\d")
NUMERIC_APPLICABILITY_TEXT = re.compile(
    r"^\s*(?:<=|>=|<|>|=|≤|≥)?\s*[-+]?(?:\d+(?:[.,]\d+)?|[.,]\d+)"
    r"(?:\s*(?:～|~|\.\.)\s*[-+]?(?:\d+(?:[.,]\d+)?|[.,]\d+))?"
    r"(?:\s*\([^)]*\))?\s*$"
)
MACHINE_EXPRESSION = re.compile(r"^[A-Za-z0-9_.,+\-*/()\[\] <>=!]+$")
ALLOWED_FORMULA_FUNCTIONS = {
    "sqrt", "min", "max", "abs", "pow",
    "sin", "cos", "tan", "asin", "acos", "atan",
}
TRIG_FORMULA_FUNCTIONS = {"sin", "cos", "tan", "asin", "acos", "atan"}
ALLOWED_FORMULA_CONSTANTS = {"pi", "e"}
APPLICABILITY_OPERATORS = {"EQ", "NE", "LT", "LE", "GT", "GE", "BETWEEN", "IN"}
OPAQUE_SOURCE_VALUE_REF = re.compile(
    r"^(?:table|figure|formula|row|column)[_:\-]", re.IGNORECASE
)
RELATION_PROVENANCE_ONLY_KEYS = {
    "source_text", "raw_source_retained", "source_fact_id", "source_fact_ids",
    "definition_source_fact_id", "figure_source_fact_id", "relation_cell",
    "table_row", "note", "notes", "display_text",
}
RELATION_PREDICATE_REQUIRED_LIST_KEY = {
    "has_recommended_impeller": "impeller_type_ids",
    "has_evaluation_characteristics": "metric_ids",
    "has_overmixing_effect": "effect_ids",
    "has_circulation_shear_guidance": "guidance_feature_ids",
    "stainless_steel_grade_typical_use": "use_feature_ids",
}
UNIT_ALIASES = {
    "dimensionless": "1", "1": "1", "count": "count", "%": "%",
    "℃": "degC", "°C": "degC", "K": "K",
    "degree": "degree", "deg": "degree", "rad": "rad",
    "mm": "mm", "m": "m", "mm/m": "mm/m",
    "mm/s": "mm/s", "m/s": "m/s",
    "MPa": "MPa", "Pa": "Pa", "N/mm2": "N/mm2",
    "mPa.s": "mPa.s", "Pa.s": "Pa.s",
    "r/min": "r/min", "s^-1": "s^-1",
    "kW/m3": "kW/m3",
    "grade": "grade", "HBW": "HBW", "HRB": "HRB", "HV": "HV",
}
UNIT_DEFINITIONS = {
    "1": ("dimensionless", 1.0, 0.0),
    "%": ("dimensionless", 0.01, 0.0),
    "count": ("count", 1.0, 0.0),
    "degC": ("temperature", 1.0, 273.15),
    "K": ("temperature", 1.0, 0.0),
    "degree": ("angle", math.pi / 180.0, 0.0),
    "rad": ("angle", 1.0, 0.0),
    "mm": ("length", 1.0e-3, 0.0),
    "m": ("length", 1.0, 0.0),
    "mm/m": ("ratio", 1.0e-3, 0.0),
    "mm/s": ("velocity", 1.0e-3, 0.0),
    "m/s": ("velocity", 1.0, 0.0),
    "MPa": ("pressure", 1.0e6, 0.0),
    "Pa": ("pressure", 1.0, 0.0),
    "N/mm2": ("pressure", 1.0e6, 0.0),
    "mPa.s": ("dynamic_viscosity", 1.0e-3, 0.0),
    "Pa.s": ("dynamic_viscosity", 1.0, 0.0),
    "r/min": ("frequency", 1.0 / 60.0, 0.0),
    "s^-1": ("frequency", 1.0, 0.0),
    "kW/m3": ("power_density", 1.0e3, 0.0),
    "grade": ("ordinal_grade", 1.0, 0.0),
    "HBW": ("hardness_hbw", 1.0, 0.0),
    "HRB": ("hardness_hrb", 1.0, 0.0),
    "HV": ("hardness_hv", 1.0, 0.0),
}
ALLOWED_AST_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Compare, ast.Name, ast.Load,
    ast.Constant, ast.Call, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow,
    ast.USub, ast.UAdd, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq, ast.NotEq,
)
BASE_MODEL_FIELDS = (
    "constraint_id", "source_fact_ids", "entity_id", "quantity_id",
    "value_kind", "operator", "applicability_json", "source_label",
    "confidence", "conflict_policy",
)
MOJIBAKE_SIGNATURES = (
    "锛", "銆", "鈥", "鏉愭", "枡绫", "诲埆", "鎸変", "綆娓",
    "╂€", "鍥", "绀烘", "灏哄", "勭", "璇", "鐨", "脳", "鈦",
)
SOURCE_DEFERRED_PLACEHOLDER = re.compile(
    r"(?:(?:见|参见).{0,40}(?:原文|原表|原PDF)|待(?:提取|补录|识别)|"
    r"see.{0,30}(?:original|source)(?:document|table|pdf)?)",
    re.IGNORECASE,
)


def _status(row: dict[str, str]) -> str:
    return (
        row.get("resolution_status")
        or row.get("cell_status")
        or row.get("qa_status")
        or ""
    ).strip()


def _row_id(row: dict[str, str], index: int) -> str:
    return (
        row.get("cell_id")
        or row.get("record_id")
        or row.get("source_fact_id")
        or row.get("constraint_id")
        or f"row-{index}"
    )


def _missing(row: dict[str, str], fields: Iterable[str]) -> list[str]:
    return [field for field in fields if not str(row.get(field, "")).strip()]


def _looks_like_mojibake(value: str) -> bool:
    if "\ufffd" in value:
        return True
    hits = sum(value.count(signature) for signature in MOJIBAKE_SIGNATURES)
    return hits >= 2


def validate_semantic_rows(rows: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    semantic_templates: Counter[tuple[str, str]] = Counter()
    for index, row in enumerate(rows, start=1):
        identifier = _row_id(row, index)
        status = _status(row)
        if any(marker in status.upper() for marker in NONTERMINAL_STATUS_MARKERS):
            errors.append(f"{identifier}: non-terminal resolution status {status!r}")
        basis = str(row.get("resolution_basis", "")).strip()
        context = str(
            row.get("context_refs") or row.get("context_cells") or ""
        ).strip()
        for field in (
            "raw_observed", "resolved_value", "raw_printed_glyph",
            "normalized_value", "resolution_basis",
            "context_refs", "context_cells",
        ):
            value = str(row.get(field, ""))
            if value and _looks_like_mojibake(value):
                errors.append(f"{identifier}: mojibake detected in {field}")
            if (
                field in {
                    "raw_observed", "resolved_value", "raw_printed_glyph",
                    "normalized_value",
                }
                and value and SOURCE_DEFERRED_PLACEHOLDER.search(value)
            ):
                errors.append(
                    f"{identifier}: deferred source placeholder in {field}"
                )
        if status == SEMANTIC_STATUS:
            missing = _missing(row, (
                "raw_observed", "resolved_value", "resolution_basis",
                "resolution_confidence",
            ))
            if not context:
                missing.append("context_refs/context_cells")
            if missing:
                errors.append(f"{identifier}: missing semantic fields: {missing}")
                continue
            combined = f"{basis};{context}"
            if not CONCRETE_REF.search(combined):
                errors.append(f"{identifier}: semantic resolution lacks concrete source reference")
            lower = combined.lower()
            if any(fragment in lower for fragment in GENERIC_CONTEXT_FRAGMENTS):
                errors.append(f"{identifier}: generic template cannot prove a unique answer")
            semantic_templates[(basis, context)] += 1
        elif status in VISUAL_STATUSES:
            semantic_wording = f"{basis};{context}".lower()
            if "semantic" in semantic_wording or "context_resolv" in semantic_wording:
                errors.append(
                    f"{identifier}: semantic reconstruction may not masquerade as visual verification"
                )
            if str(row.get("asset_kind", "")) == "table_cell":
                visual_path = str(
                    row.get("visual_evidence_ref")
                    or row.get("source_image")
                    or row.get("source_file")
                    or ""
                ).strip()
                if Path(visual_path).suffix.lower() not in {
                    ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp",
                }:
                    errors.append(
                        f"{identifier}: visual table-cell status needs image evidence"
                    )
    for template, count in semantic_templates.items():
        if count > 3:
            errors.append(
                "semantic resolution reuses one basis/context template "
                f"for {count} cells: {template!r}"
            )
    return errors


def validate_figure_object_rows(rows: list[dict[str, object]]) -> list[str]:
    errors: list[str] = []
    for index, row in enumerate(rows, start=1):
        identifier = str(row.get("figure_id") or f"figure-row-{index}")
        content_kind = str(row.get("content_kind", "")).strip().lower()
        if "CLOSED" not in str(row.get("terminal_status", "")).upper():
            continue
        objects = row.get("objects")
        if content_kind == "quantitative":
            object_ids = (
                [str(item).lower() for item in objects]
                if isinstance(objects, list) else []
            )
            if (
                not any("coordinate" in item or "axis" in item for item in object_ids)
                or not any("curve" in item or "formula" in item for item in object_ids)
            ):
                errors.append(
                    f"{identifier}: closed quantitative figure needs coordinate/curve objects"
                )
            continue
        if content_kind != "structural":
            continue
        edges = row.get("edges")
        detail_fields = (
            row.get("dimensions"), row.get("ports"), edges,
            row.get("conditions"), row.get("legend"),
        )
        string_objects_valid = (
            isinstance(objects, list)
            and bool(objects)
            and all(
                isinstance(item, str)
                and bool(item.strip())
                and not item.startswith("diagram_subject:")
                for item in objects
            )
        )
        structured_objects_valid = (
            isinstance(objects, list)
            and bool(objects)
            and all(
                isinstance(item, dict)
                and bool(str(item.get("object_id", "")).strip())
                and bool(str(item.get("object_kind", "")).strip())
                for item in objects
            )
        )
        generic_object = not (string_objects_valid or structured_objects_valid)
        string_edges_valid = (
            isinstance(edges, list)
            and bool(edges)
            and all(
                isinstance(item, str)
                and bool(item.strip())
                and item.strip() != "diagram declares the captioned subject"
                for item in edges
            )
        )
        structured_edges_valid = (
            isinstance(edges, list)
            and bool(edges)
            and all(
                isinstance(item, dict)
                and bool(str(item.get("edge_id", "")).strip())
                and bool(str(item.get("source_id", "")).strip())
                and bool(str(item.get("target_id", "")).strip())
                for item in edges
            )
        )
        generic_edges = not (string_edges_valid or structured_edges_valid)
        has_detail = any(
            isinstance(items, list)
            and any(str(item).strip() for item in items)
            for items in detail_fields
        )
        if generic_object or generic_edges or not has_detail:
            errors.append(
                f"{identifier}: closed structural figure is a caption-only placeholder"
            )
        if structured_objects_valid and structured_edges_valid:
            object_ids = [str(item["object_id"]).strip() for item in objects]
            object_id_set = set(object_ids)
            if len(object_ids) != len(object_id_set):
                errors.append(f"{identifier}: duplicate structured object_id")
            for item in objects:
                object_id = str(item.get("object_id", "")).strip().lower()
                object_kind = str(item.get("object_kind", "")).strip().lower()
                if object_id.startswith("source_anchor_") or object_kind in {
                    "source_anchor", "generic_anchor", "coverage_anchor",
                }:
                    errors.append(
                        f"{identifier}: synthetic coverage anchor cannot close a source figure"
                    )
            ports = row.get("ports")
            known_ports: set[tuple[str, str]] = set()
            port_ids: list[str] = []
            if not isinstance(ports, list) or not all(
                isinstance(port, dict) for port in ports
            ):
                errors.append(f"{identifier}: structured graph needs structured ports")
            else:
                for port in ports:
                    port_id = str(port.get("port_id", "")).strip()
                    port_object = str(port.get("object_id", "")).strip()
                    port_name = str(port.get("port_name", "")).strip()
                    if not port_id or not port_object or not port_name:
                        errors.append(
                            f"{identifier}: structured port needs port_id/object_id/port_name"
                        )
                        continue
                    port_ids.append(port_id)
                    if port_object not in object_id_set:
                        errors.append(
                            f"{identifier}: port {port_id!r} has unknown object {port_object!r}"
                        )
                    known_ports.add((port_object, port_name))
                if len(port_ids) != len(set(port_ids)):
                    errors.append(f"{identifier}: duplicate structured port_id")
            edge_ids: list[str] = []
            for edge in edges:
                edge_id = str(edge.get("edge_id", "")).strip()
                source_id = str(edge.get("source_id", "")).strip()
                target_id = str(edge.get("target_id", "")).strip()
                source_port = str(edge.get("source_port", "")).strip()
                target_port = str(edge.get("target_port", "")).strip()
                edge_ids.append(edge_id)
                if source_id not in object_id_set:
                    errors.append(
                        f"{identifier}: edge {edge_id!r} has unknown source object {source_id!r}"
                    )
                if target_id not in object_id_set:
                    errors.append(
                        f"{identifier}: edge {edge_id!r} has unknown target object {target_id!r}"
                    )
                if source_port and (source_id, source_port) not in known_ports:
                    errors.append(
                        f"{identifier}: edge {edge_id!r} has unknown source port "
                        f"{source_id}:{source_port}"
                    )
                if target_port and (target_id, target_port) not in known_ports:
                    errors.append(
                        f"{identifier}: edge {edge_id!r} has unknown target port "
                        f"{target_id}:{target_port}"
                    )
            if len(edge_ids) != len(set(edge_ids)):
                errors.append(f"{identifier}: duplicate structured edge_id")
        for coverage_kind in ("label", "edge"):
            printed_key = f"printed_{coverage_kind}_count"
            modelled_key = f"modelled_{coverage_kind}_count"
            try:
                printed_count = int(row[printed_key])
                modelled_count = int(row[modelled_key])
            except (KeyError, TypeError, ValueError):
                errors.append(
                    f"{identifier}: {coverage_kind} coverage counts are required"
                )
                continue
            if printed_count < 0 or modelled_count < 0:
                errors.append(
                    f"{identifier}: {coverage_kind} coverage counts must be nonnegative"
                )
            elif printed_count != modelled_count:
                errors.append(
                    f"{identifier}: {coverage_kind} coverage mismatch "
                    f"printed={printed_count} modelled={modelled_count}"
                )
    return errors


def validate_figure_model_alignment(
    model_rows: list[dict[str, object]],
    figure_rows: list[dict[str, object]],
) -> list[str]:
    """Validate model facts that only become mandatory at figure closure."""
    errors: list[str] = []
    curve_rows_by_subject: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in model_rows:
        if str(row.get("predicate_id", "")).endswith("has_curve_pointsets"):
            curve_rows_by_subject[str(row.get("subject_id", ""))].append(row)

    for index, figure in enumerate(figure_rows, start=1):
        figure_id = str(figure.get("figure_id") or f"figure-row-{index}")
        if "CLOSED" not in str(figure.get("terminal_status", "")).upper():
            continue
        if str(figure.get("content_kind", "")).strip().lower() != "quantitative":
            continue
        if str(figure.get("curve_data_status", "")) != "DIGITIZED_POINT_LEDGER_LINKED":
            continue
        curve_rows = curve_rows_by_subject.get(figure_id, [])
        if not curve_rows:
            errors.append(f"{figure_id}: closed digitized curve needs linked curve pointsets")
            continue
        for row in curve_rows:
            identifier = str(row.get("constraint_id") or figure_id)
            try:
                curve_object = json.loads(str(row.get("object_json", "")))
                domain = json.loads(str(row.get("relation_domain_json", "")))
            except json.JSONDecodeError:
                continue
            interpolation_domain = (
                domain.get("interpolation_x_domain")
                if isinstance(domain, dict) else None
            )
            axis_display_domain = (
                domain.get("axis_display_domain")
                if isinstance(domain, dict) else None
            )
            if not isinstance(axis_display_domain, dict):
                errors.append(
                    f"{identifier}: closed digitized curve needs axis_display_domain"
                )
            if not isinstance(interpolation_domain, dict):
                errors.append(
                    f"{identifier}: closed digitized curve needs interpolation_x_domain"
                )
                continue
            declared_min = _as_float(interpolation_domain.get("value_min"))
            declared_max = _as_float(interpolation_domain.get("value_max"))
            if declared_min is None or declared_max is None or declared_min > declared_max:
                errors.append(
                    f"{identifier}: interpolation_x_domain needs ordered numeric bounds"
                )
                continue
            pointsets = (
                curve_object.get("curve_pointsets")
                if isinstance(curve_object, dict) else None
            )
            if not isinstance(pointsets, dict):
                continue
            for series_id, points in pointsets.items():
                if not isinstance(points, list):
                    continue
                x_values = [
                    _as_float(point[0])
                    for point in points
                    if isinstance(point, list) and len(point) == 2
                ]
                valid_x = [value for value in x_values if value is not None]
                if len(valid_x) < 2:
                    continue
                point_min, point_max = min(valid_x), max(valid_x)
                tolerance = 1e-12 * max(
                    1.0, abs(declared_min), abs(declared_max),
                    abs(point_min), abs(point_max),
                )
                if (
                    declared_min < point_min - tolerance
                    or declared_max > point_max + tolerance
                ):
                    errors.append(
                        f"{identifier}: interpolation_x_domain exceeds pointset "
                        f"coverage for series {series_id!r}"
                    )
    return errors


def _as_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _canonical_unit(value: str) -> str:
    unit = (
        value.strip().replace("·", ".").replace(" ", "")
        .replace("²", "2").replace("³", "3")
    )
    return UNIT_ALIASES.get(unit, unit)


def _converted_value(
    value: float, source_unit: str, normalized_unit: str
) -> tuple[float | None, str | None]:
    source = _canonical_unit(source_unit)
    target = _canonical_unit(normalized_unit)
    if source == target:
        return value, None
    source_definition = UNIT_DEFINITIONS.get(source)
    target_definition = UNIT_DEFINITIONS.get(target)
    if source_definition is None or target_definition is None:
        return None, f"unregistered unit conversion {source_unit!r} -> {normalized_unit!r}"
    source_dimension, source_scale, source_offset = source_definition
    target_dimension, target_scale, target_offset = target_definition
    if source_dimension != target_dimension:
        return None, f"incompatible unit conversion {source_unit!r} -> {normalized_unit!r}"
    base_value = value * source_scale + source_offset
    return (base_value - target_offset) / target_scale, None


def _conversion_error(
    source_value: float,
    normalized_value: float,
    source_unit: str,
    normalized_unit: str,
) -> str | None:
    expected, error = _converted_value(
        source_value, source_unit, normalized_unit
    )
    if error:
        return error
    assert expected is not None
    tolerance = 1.0e-9 * max(1.0, abs(expected))
    if abs(expected - normalized_value) > tolerance:
        if _canonical_unit(source_unit) == _canonical_unit(normalized_unit):
            return "same-unit normalized_value differs from source value"
        return (
            f"unit conversion mismatch: expected {expected:.12g} "
            f"{normalized_unit!r}, got {normalized_value:.12g}"
        )
    return None


def _parse_machine_expression(expression: str) -> tuple[set[str], str | None]:
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        return set(), f"syntax error at column {exc.offset}"
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_AST_NODES):
            return set(), f"unsupported syntax {type(node).__name__}"
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in ALLOWED_FORMULA_FUNCTIONS:
                return set(), "unsupported formula function"
        if (
            isinstance(node, ast.Name)
            and node.id not in ALLOWED_FORMULA_FUNCTIONS
            and node.id not in ALLOWED_FORMULA_CONSTANTS
        ):
            names.add(node.id)
    return names, None


def _canonical_operator(value: str) -> str:
    operator = value.strip().upper()
    return {
        "=": "EQ", "==": "EQ", "ASSIGN": "EQ",
        ">=": "GE", "≤": "LE", "<=": "LE", "≥": "GE",
        ">": "GT", "<": "LT", "!=": "NE",
    }.get(operator, operator)


def _expression_operator(expression: str) -> str | None:
    try:
        body = ast.parse(expression, mode="eval").body
    except SyntaxError:
        return None
    if not isinstance(body, ast.Compare):
        return "EQ"
    if len(body.ops) != 1:
        return "COMPOUND"
    return {
        ast.Eq: "EQ", ast.NotEq: "NE", ast.GtE: "GE",
        ast.LtE: "LE", ast.Gt: "GT", ast.Lt: "LT",
    }.get(type(body.ops[0]))


def _is_non_executable(
    row: dict[str, str], applicability: dict[str, object] | list[object] | None
) -> bool:
    confidence = str(row.get("confidence", "")).strip().lower()
    operator = str(row.get("operator", "")).strip().lower()
    conflict = str(row.get("conflict_policy", "")).strip().lower()
    if confidence.startswith("low") or "blocked" in confidence:
        return True
    if operator in {"source_cell_text", "source_cell_blank_candidate", "unparsed"}:
        return True
    if "not_executable" in conflict or "blocked" in conflict:
        return True
    if isinstance(applicability, dict):
        gate = str(applicability.get("execution_gate", "")).strip().lower()
        if (
            "not_executable" in gate or "visual_cell_qa" in gate
            or "blocked" in gate or gate.startswith("pending")
        ):
            return True
    return False


def _numeric_applicability_text_paths(
    value: object, path: str = "$"
) -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "unit":
                continue
            paths.extend(_numeric_applicability_text_paths(item, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            paths.extend(_numeric_applicability_text_paths(item, f"{path}[{index}]"))
    elif isinstance(value, str) and NUMERIC_APPLICABILITY_TEXT.fullmatch(value):
        paths.append(path)
    return paths


def _validate_applicability_conditions(
    applicability: dict[str, object] | list[object]
) -> list[str]:
    if not isinstance(applicability, dict) or "conditions" not in applicability:
        return []
    conditions = applicability["conditions"]
    if not isinstance(conditions, list) or not conditions:
        return ["applicability conditions must be a nonempty list"]
    errors: list[str] = []
    condition_logic = str(applicability.get("condition_logic", "")).strip().upper()
    if condition_logic not in {"ALL", "ANY"}:
        errors.append("applicability conditions require condition_logic=ALL or ANY")
    for index, condition in enumerate(conditions):
        prefix = f"applicability condition {index}"
        if not isinstance(condition, dict):
            errors.append(f"{prefix} must be an object")
            continue
        quantity_id = str(condition.get("quantity_id", "")).strip()
        operator = _canonical_operator(str(condition.get("operator", "")))
        if not quantity_id:
            errors.append(f"{prefix} needs quantity_id")
        if operator not in APPLICABILITY_OPERATORS:
            errors.append(f"{prefix} has unsupported operator {operator!r}")
            continue
        if operator in {"LT", "LE", "GT", "GE"}:
            if _as_float(condition.get("value")) is None:
                errors.append(f"{prefix} needs numeric value")
            if not str(condition.get("unit", "")).strip():
                errors.append(f"{prefix} condition needs unit")
        elif operator == "BETWEEN":
            lower = _as_float(condition.get("value_min"))
            upper = _as_float(condition.get("value_max"))
            if lower is None or upper is None:
                errors.append(f"{prefix} BETWEEN needs numeric value_min/value_max")
            elif lower > upper:
                errors.append(f"{prefix} value_min exceeds value_max")
            if not str(condition.get("unit", "")).strip():
                errors.append(f"{prefix} condition needs unit")
        elif operator == "IN":
            values = condition.get("value_list")
            if not isinstance(values, list) or not values:
                errors.append(f"{prefix} IN needs nonempty value_list")
            elif any(isinstance(value, (int, float)) for value in values):
                if not str(condition.get("unit", "")).strip():
                    errors.append(f"{prefix} condition needs unit")
        else:
            if "value_ref" in condition:
                value_ref = condition.get("value_ref")
                if not isinstance(value_ref, dict):
                    errors.append(f"{prefix} value_ref must be an object")
                else:
                    if not str(value_ref.get("quantity_id", "")).strip():
                        errors.append(f"{prefix} value_ref needs quantity_id")
                    source_refs = value_ref.get("source_fact_ids")
                    if (
                        not isinstance(source_refs, list)
                        or not source_refs
                        or any(
                            not isinstance(item, str) or not item.strip()
                            for item in source_refs
                        )
                    ):
                        errors.append(
                            f"{prefix} value_ref needs nonempty source_fact_ids"
                        )
                    if not str(value_ref.get("unit", "")).strip():
                        errors.append(f"{prefix} value_ref needs unit")
            elif "value" not in condition:
                errors.append(f"{prefix} needs value")
            elif isinstance(condition.get("value"), (int, float)):
                if not str(condition.get("unit", "")).strip():
                    errors.append(f"{prefix} condition needs unit")
            elif OPAQUE_SOURCE_VALUE_REF.match(
                str(condition.get("value", "")).strip()
            ):
                errors.append(
                    f"{prefix} source-dependent value must use a structured value_ref"
                )
    return errors


def _validate_decision_rules(object_json: dict[str, object]) -> list[str]:
    if "decision_rules" not in object_json:
        return []
    rules = object_json.get("decision_rules")
    if not isinstance(rules, list) or not rules:
        return ["structured decision conditions require a nonempty decision_rules list"]
    errors: list[str] = []
    for rule_index, rule in enumerate(rules):
        prefix = f"decision rule {rule_index}"
        if not isinstance(rule, dict):
            errors.append(f"{prefix} must be an object with structured decision conditions")
            continue
        if str(rule.get("when", "")).strip():
            errors.append(f"{prefix} must use structured decision conditions, not free-text when")
        logic = str(rule.get("condition_logic", "")).strip().upper()
        conditions = rule.get("conditions")
        if logic not in {"ALL", "ANY"}:
            errors.append(f"{prefix} structured decision conditions require condition_logic=ALL or ANY")
        if not isinstance(conditions, list) or not conditions:
            errors.append(f"{prefix} structured decision conditions require a nonempty conditions list")
            continue
        result_id = str(rule.get("result_id") or rule.get("zone_id") or "").strip()
        if not result_id:
            errors.append(f"{prefix} needs result_id or zone_id")
        for condition_index, condition in enumerate(conditions):
            condition_prefix = f"{prefix} condition {condition_index}"
            if not isinstance(condition, dict):
                errors.append(f"{condition_prefix} must be an object")
                continue
            if not str(condition.get("quantity_id", "")).strip():
                errors.append(f"{condition_prefix} needs quantity_id")
            operator = _canonical_operator(str(condition.get("operator", "")))
            if operator not in APPLICABILITY_OPERATORS:
                errors.append(f"{condition_prefix} has unsupported operator {operator!r}")
                continue
            curve_ref = condition.get("curve_value_ref")
            if curve_ref is not None:
                if not isinstance(curve_ref, dict):
                    errors.append(f"{condition_prefix} curve_value_ref must be an object")
                    continue
                if not str(curve_ref.get("constraint_id", "")).strip():
                    errors.append(f"{condition_prefix} curve_value_ref needs constraint_id")
                inputs = curve_ref.get("input_quantity_ids")
                if (
                    not isinstance(inputs, list)
                    or not inputs
                    or any(not isinstance(item, str) or not item.strip() for item in inputs)
                ):
                    errors.append(f"{condition_prefix} curve_value_ref needs input_quantity_ids")
                if not str(curve_ref.get("output_unit", "")).strip():
                    errors.append(f"{condition_prefix} curve_value_ref needs output_unit")
                continue
            if operator in {"LT", "LE", "GT", "GE"}:
                if _as_float(condition.get("value")) is None:
                    errors.append(f"{condition_prefix} needs numeric value or curve_value_ref")
                if not str(condition.get("unit", "")).strip():
                    errors.append(f"{condition_prefix} needs unit")
            elif operator == "BETWEEN":
                lower = _as_float(condition.get("value_min"))
                upper = _as_float(condition.get("value_max"))
                if lower is None or upper is None:
                    errors.append(f"{condition_prefix} BETWEEN needs numeric value_min/value_max")
                elif lower > upper:
                    errors.append(f"{condition_prefix} value_min exceeds value_max")
                if not str(condition.get("unit", "")).strip():
                    errors.append(f"{condition_prefix} needs unit")
            elif operator == "IN":
                if not isinstance(condition.get("value_list"), list) or not condition.get("value_list"):
                    errors.append(f"{condition_prefix} IN needs nonempty value_list")
            elif "value" not in condition:
                errors.append(f"{condition_prefix} needs value")
    return errors


def validate_model_rows(rows: list[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for index, row in enumerate(rows, start=1):
        identifier = _row_id(row, index)
        missing = _missing(row, BASE_MODEL_FIELDS)
        if missing:
            errors.append(f"{identifier}: missing model fields: {missing}")
            continue
        if identifier in seen:
            errors.append(f"{identifier}: duplicate constraint_id")
        seen.add(identifier)
        kind = row["value_kind"].strip().lower()
        if kind not in VALUE_KINDS:
            errors.append(f"{identifier}: unsupported value_kind {kind!r}")
            continue
        applicability: dict[str, object] | list[object] | None = None
        try:
            applicability = json.loads(row["applicability_json"])
        except json.JSONDecodeError as exc:
            errors.append(f"{identifier}: invalid applicability_json: {exc.msg}")
        else:
            if not isinstance(applicability, (dict, list)):
                errors.append(f"{identifier}: applicability_json must be object or list")
            else:
                for path in _numeric_applicability_text_paths(applicability):
                    errors.append(
                        f"{identifier}: numeric applicability at {path} must use a structured condition"
                    )
                for error in _validate_applicability_conditions(applicability):
                    errors.append(f"{identifier}: {error}")
        if _is_non_executable(row, applicability):
            errors.append(
                f"{identifier}: non-executable placeholder may not pass as a model constraint"
            )
        if (
            str(row.get("predicate_id", "")).strip() == "has_source_cell_semantic"
            or str(row.get("quantity_id", "")).strip() == "source_table_cell_semantic"
        ):
            errors.append(
                f"{identifier}: opaque source-cell placeholder is not a modeled table meaning"
            )
        if str(row.get("quantity_id", "")).strip() in {
            "source_table_cell_numeric",
            "source_table_cell_range",
            "table_cell_numeric_value",
            "table_cell_range_value",
        }:
            errors.append(
                f"{identifier}: unkeyed generic table quantity lacks row/column semantics"
            )

        if kind == "range":
            lower_text = str(row.get("value_min", "")).strip()
            upper_text = str(row.get("value_max", "")).strip()
            lower = _as_float(lower_text) if lower_text else None
            upper = _as_float(upper_text) if upper_text else None
            if lower is None and upper is None:
                errors.append(f"{identifier}: range needs value_min and/or value_max")
            if lower_text and lower is None:
                errors.append(f"{identifier}: value_min is not numeric")
            if upper_text and upper is None:
                errors.append(f"{identifier}: value_max is not numeric")
            if lower is not None and upper is not None and lower > upper:
                errors.append(f"{identifier}: value_min exceeds value_max")
            if _missing(row, ("source_unit", "normalized_unit")):
                errors.append(f"{identifier}: quantitative range needs source and normalized units")
            normalized_lower_text = str(row.get("normalized_value_min", "")).strip()
            normalized_upper_text = str(row.get("normalized_value_max", "")).strip()
            normalized_lower = _as_float(normalized_lower_text) if normalized_lower_text else None
            normalized_upper = _as_float(normalized_upper_text) if normalized_upper_text else None
            if lower is not None and normalized_lower is None:
                errors.append(f"{identifier}: range needs numeric normalized_value_min")
            if upper is not None and normalized_upper is None:
                errors.append(f"{identifier}: range needs numeric normalized_value_max")
            if (
                normalized_lower is not None and normalized_upper is not None
                and normalized_lower > normalized_upper
            ):
                errors.append(
                    f"{identifier}: normalized_value_min exceeds normalized_value_max"
                )
            if lower is not None and normalized_lower is not None:
                conversion_error = _conversion_error(
                    lower,
                    normalized_lower,
                    str(row.get("source_unit", "")),
                    str(row.get("normalized_unit", "")),
                )
                if conversion_error:
                    errors.append(
                        f"{identifier}: normalized_value_min unit conversion error: {conversion_error}"
                    )
            if upper is not None and normalized_upper is not None:
                conversion_error = _conversion_error(
                    upper,
                    normalized_upper,
                    str(row.get("source_unit", "")),
                    str(row.get("normalized_unit", "")),
                )
                if conversion_error:
                    errors.append(
                        f"{identifier}: normalized_value_max unit conversion error: {conversion_error}"
                    )
        elif kind == "numeric":
            source_numeric = _as_float(str(row.get("value", "")).strip())
            normalized_numeric = _as_float(
                str(row.get("normalized_value", "")).strip()
            )
            if source_numeric is None:
                errors.append(f"{identifier}: numeric value is missing or invalid")
            if _missing(row, ("source_unit", "normalized_unit", "normalized_value")):
                errors.append(f"{identifier}: numeric constraint lacks unit normalization")
            elif normalized_numeric is None:
                errors.append(f"{identifier}: normalized_value is not numeric")
            elif source_numeric is not None:
                conversion_error = _conversion_error(
                    source_numeric,
                    normalized_numeric,
                    str(row.get("source_unit", "")),
                    str(row.get("normalized_unit", "")),
                )
                if conversion_error:
                    errors.append(
                        f"{identifier}: normalized_value unit conversion error: {conversion_error}"
                    )
        elif kind == "enumeration":
            value_list_text = str(row.get("value_list", "")).strip()
            if not value_list_text:
                errors.append(f"{identifier}: enumeration needs value_list")
            else:
                try:
                    values = json.loads(value_list_text)
                except json.JSONDecodeError:
                    errors.append(f"{identifier}: enumeration value_list must be JSON")
                else:
                    if not isinstance(values, list) or not values:
                        errors.append(f"{identifier}: enumeration value_list must be a nonempty list")
                    elif NUMERIC_SOURCE.search(row.get("source_label", "")):
                        if any(_as_float(str(item)) is None for item in values):
                            errors.append(
                                f"{identifier}: numeric enumeration must contain numeric values"
                            )
                        if _missing(row, ("source_unit", "normalized_unit")):
                            errors.append(
                                f"{identifier}: numeric enumeration needs source and normalized units"
                            )
            if RANGE_BEARING_SOURCE.search(row.get("source_label", "")):
                errors.append(
                    f"{identifier}: range-bearing source must be split into range and optional preferred enumeration"
                )
        elif kind == "ordinal":
            if not str(row.get("model_mapping_version", "")).strip():
                errors.append(f"{identifier}: ordinal requires model_mapping_version")
            if _as_float(str(row.get("normalized_value", "")).strip()) is None:
                errors.append(f"{identifier}: ordinal requires numeric normalized_value")
        elif kind in {"categorical", "boolean", "formula", "relation"}:
            if not (str(row.get("value", "")).strip() or str(row.get("value_list", "")).strip()):
                errors.append(f"{identifier}: {kind} needs value or value_list")
            if kind == "categorical" and NUMERIC_SOURCE.search(row.get("source_label", "")):
                errors.append(
                    f"{identifier}: numeric-looking source label may not be downgraded to categorical"
                )
            if kind == "formula":
                expression = str(row.get("normalized_expression", "")).strip()
                formula_missing = _missing(row, (
                    "normalized_expression", "output_quantity_id",
                    "input_quantity_ids", "symbol_bindings_json",
                    "formula_domain_json",
                ))
                if formula_missing:
                    errors.append(
                        f"{identifier}: formula missing machine fields: {formula_missing}"
                    )
                elif not MACHINE_EXPRESSION.fullmatch(expression):
                    errors.append(
                        f"{identifier}: normalized_expression must use canonical machine syntax"
                    )
                else:
                    _, expression_error = _parse_machine_expression(expression)
                    if expression_error:
                        errors.append(
                            f"{identifier}: normalized_expression is not safely parseable: {expression_error}"
                        )
                    else:
                        expression_operator = _expression_operator(expression)
                        if expression_operator == "COMPOUND":
                            errors.append(
                                f"{identifier}: normalized_expression must contain one atomic comparison"
                            )
                        elif expression_operator != _canonical_operator(str(row.get("operator", ""))):
                            errors.append(
                                f"{identifier}: operator does not match normalized_expression comparison"
                            )
                try:
                    inputs = json.loads(str(row.get("input_quantity_ids", "")))
                except json.JSONDecodeError:
                    errors.append(f"{identifier}: input_quantity_ids must be JSON")
                else:
                    if not isinstance(inputs, list) or not inputs:
                        errors.append(
                            f"{identifier}: input_quantity_ids must be a nonempty list"
                        )
                try:
                    bindings = json.loads(str(row.get("symbol_bindings_json", "")))
                except json.JSONDecodeError:
                    errors.append(f"{identifier}: symbol_bindings_json must be JSON")
                else:
                    if not isinstance(bindings, dict) or not bindings:
                        errors.append(
                            f"{identifier}: symbol_bindings_json must be a nonempty object"
                        )
                    elif expression and MACHINE_EXPRESSION.fullmatch(expression):
                        expression_names, expression_error = _parse_machine_expression(expression)
                        if not expression_error:
                            missing_symbols = sorted(expression_names - set(bindings))
                            if missing_symbols:
                                errors.append(
                                    f"{identifier}: unbound expression symbols {missing_symbols}"
                                )
                try:
                    domain = json.loads(str(row.get("formula_domain_json", "")))
                except json.JSONDecodeError:
                    errors.append(f"{identifier}: formula_domain_json must be JSON")
                else:
                    if not isinstance(domain, (dict, list)):
                        errors.append(
                            f"{identifier}: formula_domain_json must be object or list"
                        )
                    elif isinstance(domain, dict):
                        for domain_error in _validate_applicability_conditions(domain):
                            errors.append(f"{identifier}: formula domain {domain_error}")
                        free_domain = domain.get("domain")
                        if isinstance(free_domain, str) and re.search(
                            r"(?:\d|(?:^|_)(?:lt|le|gt|ge|between)(?:_|$))",
                            free_domain,
                            re.IGNORECASE,
                        ):
                            errors.append(
                                f"{identifier}: numeric formula domain must use structured conditions"
                            )
                        if any(
                            re.search(rf"\b{function}\s*\(", expression)
                            for function in TRIG_FORMULA_FUNCTIONS
                        ) and str(domain.get("angle_unit", "")).lower() not in {
                            "rad", "radian", "radians",
                        }:
                            errors.append(
                                f"{identifier}: trigonometric formula requires angle_unit=rad"
                            )
                        if "extrapolat" in str(
                            row.get("conflict_policy", "")
                        ).lower():
                            if (
                                not isinstance(domain.get("conditions"), list)
                                or not domain.get("conditions")
                            ):
                                errors.append(
                                    f"{identifier}: source-figure formula domain conditions must be explicit"
                                )
                            if domain.get("extrapolation_policy") != "forbidden":
                                errors.append(
                                    f"{identifier}: extrapolation_policy must be 'forbidden'"
                                )
                source_formula = str(row.get("source_label") or row.get("value") or "")
                comparison_count = len(re.findall(r"(?:<=|>=|≤|≥|(?<![<>=])<(?![=])|(?<![<>=])>(?![=])|(?<![<>=])=(?![=]))", source_formula))
                if comparison_count > 1:
                    errors.append(
                        f"{identifier}: compound formula must be split into atomic constraints"
                    )
            if kind == "relation":
                relation_missing = _missing(row, (
                    "predicate_id", "subject_id", "object_json",
                    "relation_domain_json",
                ))
                if relation_missing:
                    errors.append(
                        f"{identifier}: relation missing controlled predicate contract: {relation_missing}"
                    )
                relation_text = f"{row.get('source_label', '')};{row.get('value', '')}"
                if NUMERIC_SOURCE.search(relation_text) or re.search(r"[<>≤≥]", relation_text):
                    errors.append(
                        f"{identifier}: numeric relation must be decomposed into range/formula constraints"
                    )
                for field in ("object_json", "relation_domain_json"):
                    try:
                        relation_object = json.loads(str(row.get(field, "")))
                    except json.JSONDecodeError:
                        errors.append(f"{identifier}: {field} must be JSON")
                    else:
                        if not isinstance(relation_object, (dict, list)):
                            errors.append(
                                f"{identifier}: {field} must be object or list"
                            )
                        elif field == "object_json":
                            if isinstance(relation_object, dict):
                                predicate_id = str(row.get("predicate_id", "")).strip()
                                payload_keys = {
                                    key for key, value in relation_object.items()
                                    if key not in RELATION_PROVENANCE_ONLY_KEYS
                                    and value not in (None, "", [], {})
                                }
                                if not payload_keys:
                                    errors.append(
                                        f"{identifier}: object_json needs a controlled machine payload beyond source text/provenance"
                                    )
                                for decision_error in _validate_decision_rules(relation_object):
                                    errors.append(f"{identifier}: {decision_error}")
                                required_key = RELATION_PREDICATE_REQUIRED_LIST_KEY.get(
                                    predicate_id
                                )
                                if required_key:
                                    atomic_ids = relation_object.get(required_key)
                                    if (
                                        not isinstance(atomic_ids, list)
                                        or not atomic_ids
                                        or any(
                                            not isinstance(item, str) or not item.strip()
                                            for item in atomic_ids
                                        )
                                    ):
                                        errors.append(
                                            f"{identifier}: predicate {row.get('predicate_id')} requires nonempty atomic {required_key}"
                                        )
                                if predicate_id == "heat_treatment_group_options":
                                    group_ids = relation_object.get("group_ids")
                                    if (
                                        not isinstance(group_ids, list)
                                        or not group_ids
                                        or any(
                                            not isinstance(group_id, str)
                                            or not re.fullmatch(r"group_[0-9]+", group_id)
                                            for group_id in group_ids
                                        )
                                    ):
                                        errors.append(
                                            f"{identifier}: heat-treatment group options require controlled string group_ids"
                                        )
                                if predicate_id == "stainless_steel_grade_typical_use":
                                    use_ids = relation_object.get("use_ids")
                                    feature_ids = relation_object.get("use_feature_ids")
                                    combined_ids = []
                                    if isinstance(use_ids, list):
                                        combined_ids.extend(use_ids)
                                    if isinstance(feature_ids, list):
                                        combined_ids.extend(feature_ids)
                                    if any(
                                        isinstance(item, str) and item.startswith("use_same_as_")
                                        for item in combined_ids
                                    ):
                                        reference_grade_ids = relation_object.get("reference_grade_ids")
                                        reference_source_fact_ids = relation_object.get("reference_source_fact_ids")
                                        if (
                                            not isinstance(reference_grade_ids, list)
                                            or not reference_grade_ids
                                            or any(
                                                not isinstance(item, str) or not item.strip()
                                                for item in reference_grade_ids
                                            )
                                        ):
                                            errors.append(
                                                f"{identifier}: same-as typical-use relation requires nonempty reference_grade_ids"
                                            )
                                        if (
                                            not isinstance(reference_source_fact_ids, list)
                                            or not reference_source_fact_ids
                                            or any(
                                                not isinstance(item, str) or not item.strip()
                                                for item in reference_source_fact_ids
                                            )
                                        ):
                                            errors.append(
                                                f"{identifier}: same-as typical-use relation requires nonempty reference_source_fact_ids"
                                            )
                                if predicate_id.startswith("heat_treatment_"):
                                    group_id = relation_object.get("group_id")
                                    if group_id is not None and (
                                        not isinstance(group_id, str)
                                        or not re.fullmatch(r"group_[0-9]+", group_id)
                                    ):
                                        errors.append(
                                            f"{identifier}: heat-treatment relation requires controlled string group_id"
                                        )
                                if predicate_id == "default_heat_treatment_group_when_contract_unspecified":
                                    default_group_id = relation_object.get("default_group_id")
                                    if (
                                        not isinstance(default_group_id, str)
                                        or not re.fullmatch(r"group_[0-9]+", default_group_id)
                                    ):
                                        errors.append(
                                            f"{identifier}: default heat-treatment relation requires controlled string group_id"
                                        )
                            elif not relation_object:
                                errors.append(
                                    f"{identifier}: object_json needs a controlled machine payload"
                                )
                if str(row.get("predicate_id", "")).endswith("has_curve_pointsets"):
                    try:
                        curve_object = json.loads(str(row.get("object_json", "")))
                        curve_domain = json.loads(
                            str(row.get("relation_domain_json", ""))
                        )
                    except json.JSONDecodeError:
                        pass
                    else:
                        pointsets = (
                            curve_object.get("curve_pointsets")
                            if isinstance(curve_object, dict) else None
                        )
                        if not isinstance(pointsets, dict) or not pointsets:
                            errors.append(
                                f"{identifier}: curve relation needs nonempty curve_pointsets"
                            )
                            series_x_ranges: dict[str, tuple[float, float]] = {}
                        else:
                            series_x_ranges = {}
                            interpolation = str(
                                curve_domain.get("interpolation", "")
                            ) if isinstance(curve_domain, dict) else ""
                            for series_id, points in pointsets.items():
                                if not str(series_id).strip():
                                    errors.append(
                                        f"{identifier}: curve series id may not be empty"
                                    )
                                if not isinstance(points, list) or len(points) < 2:
                                    errors.append(
                                        f"{identifier}: curve series {series_id!r} needs at least two points"
                                    )
                                    continue
                                previous_x: float | None = None
                                valid_x_values: list[float] = []
                                for point in points:
                                    if not isinstance(point, list) or len(point) != 2:
                                        errors.append(
                                            f"{identifier}: curve series {series_id!r} has invalid point"
                                        )
                                        continue
                                    x_value = _as_float(point[0])
                                    y_value = _as_float(point[1])
                                    if (
                                        x_value is None or y_value is None
                                        or not math.isfinite(x_value)
                                        or not math.isfinite(y_value)
                                    ):
                                        errors.append(
                                            f"{identifier}: curve series {series_id!r} points must be finite numeric pairs"
                                        )
                                        continue
                                    if previous_x is not None and x_value <= previous_x:
                                        errors.append(
                                            f"{identifier}: curve series {series_id!r} x values must be strictly increasing"
                                        )
                                    previous_x = x_value
                                    valid_x_values.append(x_value)
                                    if "log10" in interpolation and (
                                        x_value <= 0 or y_value <= 0
                                    ):
                                        errors.append(
                                            f"{identifier}: log10 curve points must be positive"
                                        )
                                if len(valid_x_values) >= 2:
                                    series_x_ranges[str(series_id)] = (
                                        min(valid_x_values), max(valid_x_values)
                                    )
                        if not isinstance(curve_domain, dict):
                            errors.append(
                                f"{identifier}: curve relation_domain_json must be an object"
                            )
                        else:
                            for field in (
                                "interpolation", "x_unit", "y_unit",
                                "relative_error_max", "extrapolation_policy",
                            ):
                                if field not in curve_domain or curve_domain[field] in (None, ""):
                                    errors.append(
                                        f"{identifier}: curve relation domain needs {field}"
                                    )
                            if curve_domain.get("extrapolation_policy") != "forbidden":
                                errors.append(
                                    f"{identifier}: extrapolation_policy must be 'forbidden'"
                                )
                            error_bound = _as_float(
                                curve_domain.get("relative_error_max")
                            )
                            if error_bound is None or not 0 <= error_bound <= 1:
                                errors.append(
                                    f"{identifier}: relative_error_max must be within [0,1]"
                                )
                            if (
                                curve_domain.get("extrapolation_policy") == "forbidden"
                                and series_x_ranges
                            ):
                                x_unit = str(curve_domain.get("x_unit", "")).strip()
                                conditions = curve_domain.get("conditions")
                                if isinstance(conditions, list):
                                    for condition in conditions:
                                        if not isinstance(condition, dict):
                                            continue
                                        if (
                                            _canonical_operator(str(condition.get("operator", "")))
                                            != "BETWEEN"
                                            or str(condition.get("unit", "")).strip() != x_unit
                                        ):
                                            continue
                                        declared_min = _as_float(condition.get("value_min"))
                                        declared_max = _as_float(condition.get("value_max"))
                                        if declared_min is None or declared_max is None:
                                            continue
                                        for series_id, (point_min, point_max) in series_x_ranges.items():
                                            tolerance = 1e-12 * max(
                                                1.0, abs(declared_min), abs(declared_max),
                                                abs(point_min), abs(point_max),
                                            )
                                            if (
                                                declared_min < point_min - tolerance
                                                or declared_max > point_max + tolerance
                                            ):
                                                errors.append(
                                                    f"{identifier}: declared x domain exceeds pointset coverage for series {series_id!r}"
                                                )
                if str(row.get("predicate_id", "")).endswith("has_scatter_pointset"):
                    try:
                        scatter_object = json.loads(str(row.get("object_json", "")))
                        scatter_domain = json.loads(
                            str(row.get("relation_domain_json", ""))
                        )
                    except json.JSONDecodeError:
                        pass
                    else:
                        pointsets = (
                            scatter_object.get("scatter_pointsets")
                            if isinstance(scatter_object, dict) else None
                        )
                        if not isinstance(pointsets, dict) or not pointsets:
                            errors.append(
                                f"{identifier}: scatter relation needs nonempty scatter_pointsets"
                            )
                        else:
                            for series_id, points in pointsets.items():
                                if not str(series_id).strip():
                                    errors.append(
                                        f"{identifier}: scatter series id may not be empty"
                                    )
                                if not isinstance(points, list) or not points:
                                    errors.append(
                                        f"{identifier}: scatter series {series_id!r} needs points"
                                    )
                                    continue
                                for point in points:
                                    if not isinstance(point, list) or len(point) != 2:
                                        errors.append(
                                            f"{identifier}: scatter series {series_id!r} has invalid point"
                                        )
                                        continue
                                    x_value = _as_float(point[0])
                                    y_value = _as_float(point[1])
                                    if (
                                        x_value is None or y_value is None
                                        or not math.isfinite(x_value)
                                        or not math.isfinite(y_value)
                                    ):
                                        errors.append(
                                            f"{identifier}: scatter points must be finite numeric pairs"
                                        )
                        if not isinstance(scatter_domain, dict):
                            errors.append(
                                f"{identifier}: scatter relation_domain_json must be an object"
                            )
                        else:
                            for field in (
                                "x_unit", "y_unit", "relative_error_max",
                                "interpolation_policy",
                            ):
                                if field not in scatter_domain or scatter_domain[field] in (None, ""):
                                    errors.append(
                                        f"{identifier}: scatter relation domain needs {field}"
                                    )
                            if scatter_domain.get("interpolation_policy") != "forbidden":
                                errors.append(
                                    f"{identifier}: interpolation_policy must be 'forbidden'"
                                )
                            error_bound = _as_float(
                                scatter_domain.get("relative_error_max")
                            )
                            if error_bound is None or not 0 <= error_bound <= 1:
                                errors.append(
                                    f"{identifier}: relative_error_max must be within [0,1]"
                                )
    return errors


def _split_refs(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[|;]", value) if item.strip()]


def _nested_source_refs(value: object) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).endswith("source_fact_ids"):
                if isinstance(item, list):
                    refs.update(
                        str(ref).strip() for ref in item if str(ref).strip()
                    )
                elif isinstance(item, str):
                    refs.update(_split_refs(item))
            refs.update(_nested_source_refs(item))
    elif isinstance(value, list):
        for item in value:
            refs.update(_nested_source_refs(item))
    return refs


def validate_package_links(
    source_rows: list[dict[str, str]], model_rows: list[dict[str, str]]
) -> list[str]:
    errors: list[str] = []
    source_by_id = {
        _row_id(row, index): row for index, row in enumerate(source_rows, start=1)
    }
    model_by_id = {
        _row_id(row, index): row for index, row in enumerate(model_rows, start=1)
    }
    has_source_backlinks = any("model_constraint_ids" in row for row in source_rows)

    for model_id, row in model_by_id.items():
        declared_source_ids = set(_split_refs(str(row.get("source_fact_ids", ""))))
        nested_source_ids: set[str] = set()
        for field in ("applicability_json", "object_json", "relation_domain_json"):
            payload = str(row.get(field, "")).strip()
            if not payload:
                continue
            try:
                nested_source_ids.update(_nested_source_refs(json.loads(payload)))
            except json.JSONDecodeError:
                continue
        for nested_source_id in sorted(nested_source_ids - declared_source_ids):
            errors.append(
                f"{model_id}: nested source reference is absent from source_fact_ids: "
                f"{nested_source_id!r}"
            )
        for source_id in declared_source_ids:
            if source_id not in source_by_id:
                errors.append(
                    f"{model_id}: unknown source_fact_id {source_id!r}"
                )
                continue
            if has_source_backlinks:
                backlinks = _split_refs(
                    str(source_by_id[source_id].get("model_constraint_ids", ""))
                )
                if model_id not in backlinks:
                    errors.append(
                        f"{model_id}: missing source backlink from {source_id!r}"
                    )
    if has_source_backlinks:
        for source_id, row in source_by_id.items():
            for model_id in _split_refs(str(row.get("model_constraint_ids", ""))):
                if model_id not in model_by_id:
                    errors.append(
                        f"{source_id}: unknown model_constraint_id {model_id!r}"
                    )
    return errors


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"JSONL line {line_number} must be an object")
            rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--semantic-csv", type=Path)
    parser.add_argument("--model-csv", type=Path)
    parser.add_argument("--figure-jsonl", type=Path)
    parser.add_argument("--out-report", type=Path, required=True)
    args = parser.parse_args()
    if not args.semantic_csv and not args.model_csv and not args.figure_jsonl:
        parser.error("provide --semantic-csv, --model-csv, and/or --figure-jsonl")
    semantic_rows = _read_csv(args.semantic_csv.resolve()) if args.semantic_csv else []
    model_rows = _read_csv(args.model_csv.resolve()) if args.model_csv else []
    figure_rows = _read_jsonl(args.figure_jsonl.resolve()) if args.figure_jsonl else []
    semantic_errors = validate_semantic_rows(semantic_rows) if args.semantic_csv else []
    model_errors = validate_model_rows(model_rows) if args.model_csv else []
    figure_errors = validate_figure_object_rows(figure_rows) if args.figure_jsonl else []
    if args.figure_jsonl and args.model_csv:
        figure_errors.extend(validate_figure_model_alignment(model_rows, figure_rows))
    link_errors = (
        validate_package_links(semantic_rows, model_rows)
        if args.semantic_csv and args.model_csv else []
    )
    report = {
        "schema": "semantic-model-validation-v7",
        "validator_contract": "source-fact-quant-model-2026-07-20-v7",
        "status": (
            "PASS" if not semantic_errors and not model_errors and not link_errors
            and not figure_errors
            else "FAIL"
        ),
        "semantic_errors": semantic_errors,
        "model_errors": model_errors,
        "link_errors": link_errors,
        "figure_errors": figure_errors,
    }
    output = args.out_report.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
