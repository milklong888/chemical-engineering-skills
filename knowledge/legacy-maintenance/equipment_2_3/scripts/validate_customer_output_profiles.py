#!/usr/bin/env python3
"""Validate the authority-only customer equipment output profile contract.

The validator deliberately uses only the Python standard library.  It checks
the profile schema, authority provenance, deterministic family coverage,
canonical aliases, evidence gates, source-file identities, and the absence of
embedded project-instance values.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "equipment-customer-output-profiles-v1"
EXPECTED_PROFILE_IDS = [
    *(f"T{i:02d}" for i in range(1, 15)),
    *(f"X{i:02d}" for i in range(1, 6)),
]
EXPECTED_FAMILIES = [
    "family_fixed_tubesheet_exchanger",
    "family_other_heat_exchanger",
    "family_tower",
    "family_reactor_vessel_separator",
    "family_storage_vessel",
    "family_pump",
    "family_compressor",
    "family_agitator",
    "family_static_mixer",
    "family_membrane",
    "family_package_equipment",
    "family_liquid_power_recovery_turbine",
    "family_gas_expander_turbine",
    "family_process_piping",
    "family_pipe_fitting",
    "family_flange_gasket",
    "family_valve",
]
EXPECTED_EMPTY_FAMILIES = {
    "family_agitator",
    "family_membrane",
    "family_package_equipment",
}
EXPECTED_T_EXCEL = {
    "T01": ("泵", "A2:R2"),
    "T02": ("压缩机", "A2:J2"),
    "T03": ("其余设备", "A2:K2"),
    "T04": ("其余设备", "A2:K2"),
    "T05": ("换热器", "A2:J2"),
    "T06": ("罐", "A2:O2"),
    "T07": ("罐", "A18:O18"),
    "T08": ("罐", "A37:O37"),
    "T09": ("罐", "A37:O37"),
    "T10": ("其余设备", "M36:W36"),
    "T11": ("精馏塔", "A1:P1"),
    "T12": ("反应器", "N2:AB2"),
    "T13": ("气液分离器", "A2:M2"),
    "T14": ("换热器", "A2:J2"),
}
EXPECTED_HASHES = {
    "original_excel": "43929D47045F7F149819B7C8F80B37EA90BDD5A9FB8BEF6767652E29BCD46290",
    "reference_word": "DC21DAB39B0ECA91F206D701B631E61994EEA709B7467B480BC97D9D4008FE9C",
}
REQUIRED_OUTPUT_ONLY = {
    "equipment_drawing_number",
    "motor_power_kw",
    "model_designation",
    "model_status",
    "key_specification_summary",
    "operating_condition_summary",
    "design_condition_summary",
    "material_summary",
    "software_vendor_evidence_refs",
    "total_mass_kg",
    "total_power_kw",
    "tubesheet_thickness_mm",
    "evidence_grade",
    "pending_evidence",
}
HEADER_DISPOSITIONS = {"CANONICAL_OUTPUT", "NOT_APPLICABLE"}
EXPECTED_T10_NOT_APPLICABLE_FIELDS = {"loading_coefficient", "rotational_speed_rpm"}
FIELD_KEYS = {
    "canonical_id",
    "label",
    "unit",
    "source_gate",
    "selection_impact",
    "authority_sources",
    "data_type",
    "aliases",
    "evidence_gate",
    "output_only",
    "input_allowed",
}
DEFINITION_KEYS = {
    "canonical_id",
    "label",
    "unit",
    "data_type",
    "aliases",
    "authority_sources",
    "evidence_gates",
    "selection_impacts",
    "profile_ids",
    "output_only",
    "input_allowed",
}
DATA_TYPES = {"string", "number", "integer", "boolean", "object", "array"}
FORBIDDEN_INSTANCE_KEYS = {
    "value",
    "values",
    "default",
    "defaults",
    "example",
    "examples",
    "instance",
    "instances",
    "legacy_value",
    "old_value",
    "project_value",
    "input_value",
    "output_value",
    "model_value",
    "selected_model",
    "vendor_model",
}
SNAKE_CASE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
CELL_REFERENCE = re.compile(r"^([A-Z]+)([1-9][0-9]*)$")
XLSX_NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def normalize_alias(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).casefold().strip()
    return re.sub(r"[\s_\-./]+", "", text)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _column_number(letters: str) -> int:
    number = 0
    for character in letters:
        number = number * 26 + ord(character) - 64
    return number


def _parse_cell_reference(reference: str) -> tuple[int, int]:
    match = CELL_REFERENCE.fullmatch(reference)
    if match is None:
        raise ValueError(f"invalid OOXML cell reference {reference!r}")
    return _column_number(match.group(1)), int(match.group(2))


def extract_xlsx_header_labels(path: Path, sheet_name: str, header_range: str) -> list[str]:
    """Read the nonblank header cells directly from the frozen XLSX OOXML."""

    try:
        start_reference, end_reference = header_range.split(":", 1)
    except ValueError as exc:
        raise ValueError(f"invalid XLSX header range {header_range!r}") from exc
    start_column, start_row = _parse_cell_reference(start_reference)
    end_column, end_row = _parse_cell_reference(end_reference)
    if start_column > end_column or start_row > end_row:
        raise ValueError(f"reversed XLSX header range {header_range!r}")

    with zipfile.ZipFile(path) as archive:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            for shared_item in shared_root.findall("m:si", XLSX_NS):
                shared_strings.append(
                    "".join(node.text or "" for node in shared_item.findall(".//m:t", XLSX_NS))
                )
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        relationship_targets = {
            node.attrib["Id"]: node.attrib["Target"]
            for node in relationships
        }
        worksheet_target: str | None = None
        relationship_attribute = f"{{{XLSX_NS['r']}}}id"
        for sheet in workbook.findall("m:sheets/m:sheet", XLSX_NS):
            if sheet.attrib.get("name") == sheet_name:
                worksheet_target = relationship_targets[sheet.attrib[relationship_attribute]].lstrip("/")
                break
        if worksheet_target is None:
            raise ValueError(f"XLSX sheet {sheet_name!r} not found")
        if not worksheet_target.startswith("xl/"):
            worksheet_target = "xl/" + worksheet_target
        worksheet = ET.fromstring(archive.read(worksheet_target))
        cell_text: dict[tuple[int, int], str] = {}
        for cell in worksheet.findall("m:sheetData/m:row/m:c", XLSX_NS):
            column, row = _parse_cell_reference(cell.attrib["r"])
            if not (start_column <= column <= end_column and start_row <= row <= end_row):
                continue
            cell_type = cell.attrib.get("t")
            value_node = cell.find("m:v", XLSX_NS)
            inline_node = cell.find("m:is", XLSX_NS)
            text = ""
            if cell_type == "s" and value_node is not None:
                text = shared_strings[int(value_node.text or "0")]
            elif cell_type == "inlineStr" and inline_node is not None:
                text = "".join(
                    node.text or "" for node in inline_node.findall(".//m:t", XLSX_NS)
                )
            elif value_node is not None:
                text = value_node.text or ""
            cell_text[(column, row)] = text.strip()
        return [
            cell_text.get((column, row), "")
            for row in range(start_row, end_row + 1)
            for column in range(start_column, end_column + 1)
            if cell_text.get((column, row), "").strip()
        ]


def extract_docx_table_header_labels(path: Path, table_id: str) -> list[str]:
    """Read one first-row Word table header directly from document.xml."""

    match = re.fullmatch(r"T([0-9]{2})", table_id)
    if match is None:
        raise ValueError(f"invalid Word table_id {table_id!r}")
    table_index = int(match.group(1)) - 1
    with zipfile.ZipFile(path) as archive:
        document = ET.fromstring(archive.read("word/document.xml"))
    tables = document.findall(".//" + WORD_NS + "tbl")
    if not 0 <= table_index < len(tables):
        raise ValueError(f"Word table {table_id!r} not found; document has {len(tables)} tables")
    first_row = tables[table_index].find("./" + WORD_NS + "tr")
    if first_row is None:
        raise ValueError(f"Word table {table_id!r} has no rows")
    labels = []
    for cell in first_row.findall("./" + WORD_NS + "tc"):
        text = "".join(node.text or "" for node in cell.findall(".//" + WORD_NS + "t")).strip()
        if text:
            labels.append(text)
    return labels


def validate_header_channel_mapping(
    *,
    source_id: str,
    channel_name: str,
    declared_headers: Any,
    actual_headers: list[str],
    mappings: Any,
    available_fields: dict[str, dict[str, Any]],
    errors: list[str],
) -> dict[str, Any]:
    """Require a one-to-one authority header -> output/N-A ledger.

    This is deliberately profile-local. A matching alias somewhere else in the
    document cannot satisfy a missing mapping for this source channel.
    """

    location = f"authority_source_sets.{source_id}.{channel_name}"
    declared = declared_headers if isinstance(declared_headers, list) else []
    add_error(
        errors,
        bool(declared) and all(isinstance(label, str) and label.strip() for label in declared),
        f"{location}.header_labels must be a non-empty exact OOXML string list",
    )
    add_error(
        errors,
        declared == actual_headers,
        f"{location}.header_labels do not exactly match frozen OOXML: "
        f"declared={declared!r}, actual={actual_headers!r}",
    )
    mapping_rows = mappings if isinstance(mappings, list) else []
    add_error(errors, isinstance(mappings, list), f"{location}.header_mappings must be an array")
    add_error(
        errors,
        len(mapping_rows) == len(declared),
        f"{location}.header_mappings must contain exactly one row per header label",
    )
    mapped_labels: list[str] = []
    for index, mapping in enumerate(mapping_rows):
        mapping_location = f"{location}.header_mappings[{index}]"
        if not isinstance(mapping, dict):
            errors.append(f"{mapping_location}: mapping must be an object")
            continue
        label = mapping.get("header_label")
        if isinstance(label, str):
            mapped_labels.append(label)
        add_error(
            errors,
            isinstance(label, str) and label in declared,
            f"{mapping_location}: header_label must be one declared OOXML header",
        )
        disposition = mapping.get("disposition")
        add_error(
            errors,
            disposition in HEADER_DISPOSITIONS,
            f"{mapping_location}: disposition must be CANONICAL_OUTPUT or NOT_APPLICABLE",
        )
        canonical_id = mapping.get("canonical_id")
        if disposition == "CANONICAL_OUTPUT":
            add_error(
                errors,
                isinstance(canonical_id, str) and canonical_id in available_fields,
                f"{mapping_location}: canonical_id must exist in profile/global output fields",
            )
            add_error(
                errors,
                "reason_code" not in mapping,
                f"{mapping_location}: canonical output may not carry an N/A reason_code",
            )
        elif disposition == "NOT_APPLICABLE":
            add_error(
                errors,
                canonical_id is None,
                f"{mapping_location}: NOT_APPLICABLE may not claim a canonical output",
            )
            add_error(
                errors,
                isinstance(mapping.get("reason_code"), str) and bool(mapping["reason_code"].strip()),
                f"{mapping_location}: NOT_APPLICABLE requires a non-empty reason_code",
            )
    add_error(
        errors,
        Counter(mapped_labels) == Counter(declared),
        f"{location}: header mappings do not cover every declared label exactly once",
    )
    return {
        "source_id": source_id,
        "channel": channel_name,
        "declared_header_count": len(declared),
        "actual_header_count": len(actual_headers),
        "mapping_count": len(mapping_rows),
        "exact_ooxml_match": declared == actual_headers,
        "complete_mapping": Counter(mapped_labels) == Counter(declared),
    }


def duplicate_values(items: Iterable[str]) -> list[str]:
    counts = Counter(items)
    return sorted(value for value, count in counts.items() if count > 1)


def resolve_reference(base: Path, raw: Any) -> Path | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    return (base / raw).resolve()


def add_error(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def validate_field(
    field: Any,
    location: str,
    source_sets: set[str],
    gates: set[str],
    impacts: set[str],
    errors: list[str],
) -> None:
    if not isinstance(field, dict):
        errors.append(f"{location}: field must be an object")
        return
    missing = FIELD_KEYS - set(field)
    if missing:
        errors.append(f"{location}: missing field keys {sorted(missing)}")
    canonical_id = field.get("canonical_id")
    add_error(errors, isinstance(canonical_id, str) and bool(SNAKE_CASE.fullmatch(canonical_id)),
              f"{location}: canonical_id must be lower snake_case")
    add_error(errors, isinstance(field.get("label"), str) and bool(field["label"].strip()),
              f"{location}: label must be non-empty")
    add_error(errors, field.get("unit") is None or isinstance(field.get("unit"), str),
              f"{location}: unit must be a string or null")
    add_error(errors, field.get("data_type") in DATA_TYPES,
              f"{location}: unsupported data_type {field.get('data_type')!r}")
    aliases = field.get("aliases")
    add_error(errors, isinstance(aliases, list) and bool(aliases) and
              all(isinstance(item, str) and item.strip() for item in aliases),
              f"{location}: aliases must be a non-empty string list")
    if isinstance(aliases, list) and isinstance(canonical_id, str):
        add_error(errors, canonical_id in aliases,
                  f"{location}: aliases must contain canonical_id {canonical_id!r}")
        if isinstance(field.get("label"), str):
            add_error(errors, field["label"] in aliases,
                      f"{location}: aliases must contain the displayed label")
    refs = field.get("authority_sources")
    add_error(errors, isinstance(refs, list) and bool(refs) and
              all(isinstance(item, str) and item in source_sets for item in refs),
              f"{location}: authority_sources must be non-empty known source-set references")
    add_error(errors, field.get("source_gate") in gates,
              f"{location}: unknown source_gate {field.get('source_gate')!r}")
    add_error(errors, field.get("evidence_gate") == field.get("source_gate"),
              f"{location}: evidence_gate must equal source_gate")
    add_error(errors, field.get("selection_impact") in impacts,
              f"{location}: unknown selection_impact {field.get('selection_impact')!r}")
    add_error(errors, isinstance(field.get("output_only"), bool) and
              isinstance(field.get("input_allowed"), bool),
              f"{location}: output_only and input_allowed must be booleans")
    if isinstance(field.get("output_only"), bool) and isinstance(field.get("input_allowed"), bool):
        add_error(errors, field["output_only"] != field["input_allowed"],
                  f"{location}: exactly one of output_only/input_allowed must be true")


def validate_no_instance_values(node: Any, errors: list[str], path: str = "$") -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            normalized = key.casefold().strip()
            if normalized in FORBIDDEN_INSTANCE_KEYS:
                errors.append(f"{path}.{key}: forbidden project-instance value key")
            validate_no_instance_values(value, errors, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            validate_no_instance_values(value, errors, f"{path}[{index}]")
    elif isinstance(node, (int, float)) and not isinstance(node, bool):
        errors.append(f"{path}: numeric primitive is forbidden in an authority-only field contract")


def validate_document(data: Any, input_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return {"status": "FAIL", "input": str(input_path), "errors": ["root must be an object"]}

    add_error(errors, data.get("schema") == SCHEMA,
              f"schema must equal {SCHEMA!r}")
    for key in (
        "version", "scope", "source_artifacts", "authority_graph_sources",
        "source_gate_vocabulary", "selection_impact_vocabulary",
        "global_output_columns", "authority_source_sets",
        "algorithm_family_profile_map", "canonical_field_definitions", "profiles",
    ):
        add_error(errors, key in data, f"root missing {key!r}")

    source_artifacts = data.get("source_artifacts", {})
    graph_sources = data.get("authority_graph_sources", {})
    source_sets_obj = data.get("authority_source_sets", {})
    source_sets = set(source_sets_obj) if isinstance(source_sets_obj, dict) else set()
    gates_obj = data.get("source_gate_vocabulary", {})
    gates = set(gates_obj) if isinstance(gates_obj, dict) else set()
    impacts_obj = data.get("selection_impact_vocabulary", {})
    impacts = set(impacts_obj) if isinstance(impacts_obj, dict) else set()
    base = input_path.parent

    artifact_report: list[dict[str, Any]] = []
    artifact_paths: dict[str, Path] = {}
    add_error(errors, isinstance(source_artifacts, dict), "source_artifacts must be an object")
    if isinstance(source_artifacts, dict):
        add_error(errors, set(source_artifacts) == set(EXPECTED_HASHES),
                  "source_artifacts must contain exactly original_excel and reference_word")
        for artifact_id, expected_hash in EXPECTED_HASHES.items():
            artifact = source_artifacts.get(artifact_id)
            location = f"source_artifacts.{artifact_id}"
            if not isinstance(artifact, dict):
                errors.append(f"{location}: missing artifact object")
                continue
            declared_hash = artifact.get("sha256")
            add_error(errors, declared_hash == expected_hash,
                      f"{location}: declared SHA-256 is not the frozen authority hash")
            path = resolve_reference(base, artifact.get("path"))
            exists = bool(path and path.is_file())
            add_error(errors, exists, f"{location}: source file does not exist at {path}")
            actual_hash = sha256_file(path) if exists and path is not None else None
            add_error(errors, actual_hash == expected_hash,
                      f"{location}: source file SHA-256 mismatch ({actual_hash})")
            artifact_report.append({
                "artifact_id": artifact_id,
                "path": str(path) if path else None,
                "exists": exists,
                "declared_sha256": declared_hash,
                "actual_sha256": actual_hash,
                "hash_match": actual_hash == expected_hash,
            })
            if exists and path is not None:
                artifact_paths[artifact_id] = path

    add_error(errors, isinstance(graph_sources, dict), "authority_graph_sources must be an object")
    expected_graph_ids = {"field_schema", "output_interface", "piping_interface"}
    if isinstance(graph_sources, dict):
        add_error(errors, set(graph_sources) == expected_graph_ids,
                  f"authority_graph_sources must contain exactly {sorted(expected_graph_ids)}")
        for source_id in expected_graph_ids:
            path = resolve_reference(base, graph_sources.get(source_id))
            add_error(errors, bool(path and path.is_file()),
                      f"authority_graph_sources.{source_id}: graph file not found at {path}")

    add_error(errors, isinstance(source_sets_obj, dict), "authority_source_sets must be an object")
    expected_source_sets = {"GLOBAL_INTERFACE", *(f"SRC_{pid}" for pid in EXPECTED_PROFILE_IDS)}
    add_error(errors, source_sets == expected_source_sets,
              f"authority_source_sets must contain exactly {sorted(expected_source_sets)}")
    if isinstance(source_sets_obj, dict):
        for source_id, source_set in source_sets_obj.items():
            if not isinstance(source_set, dict):
                errors.append(f"authority_source_sets.{source_id}: must be an object")
                continue
            graph_refs = source_set.get("graphs")
            graph_ids = {
                entry.get("source_id") for entry in graph_refs
                if isinstance(entry, dict)
            } if isinstance(graph_refs, list) else set()
            add_error(errors, {"field_schema", "output_interface"} <= graph_ids,
                      f"authority_source_sets.{source_id}: field_schema and output_interface are required")
            for graph_id in graph_ids:
                add_error(errors, graph_id in expected_graph_ids,
                          f"authority_source_sets.{source_id}: unknown graph source {graph_id!r}")

        for profile_id, (sheet, header_range) in EXPECTED_T_EXCEL.items():
            source_id = f"SRC_{profile_id}"
            source_set = source_sets_obj.get(source_id, {})
            excel = source_set.get("excel", {}) if isinstance(source_set, dict) else {}
            word = source_set.get("word", {}) if isinstance(source_set, dict) else {}
            add_error(errors, excel.get("artifact_id") == "original_excel",
                      f"{source_id}: Excel artifact_id must be original_excel")
            add_error(errors, isinstance(excel.get("source_status"), str) and
                      excel.get("source_status", "").startswith("present"),
                      f"{source_id}: Excel source_status must explicitly be present")
            add_error(errors, (excel.get("sheet"), excel.get("header_range")) == (sheet, header_range),
                      f"{source_id}: expected Excel {sheet}!{header_range}")
            add_error(errors, isinstance(excel.get("header_labels"), list) and bool(excel["header_labels"]),
                      f"{source_id}: authoritative Excel header_labels must be present")
            add_error(errors, isinstance(excel.get("header_mappings"), list) and bool(excel["header_mappings"]),
                      f"{source_id}: authoritative Excel header_mappings must be present")
            add_error(errors, word.get("artifact_id") == "reference_word" and
                      word.get("source_status") == "present_method_only" and
                      word.get("table_id") == profile_id,
                      f"{source_id}: Word method-only table reference must be {profile_id}")
            add_error(errors, isinstance(word.get("header_labels"), list) and bool(word["header_labels"]),
                      f"{source_id}: authoritative Word header_labels must be present")
            add_error(errors, isinstance(word.get("header_mappings"), list) and bool(word["header_mappings"]),
                      f"{source_id}: authoritative Word header_mappings must be present")

        for profile_id in (f"X{i:02d}" for i in range(1, 6)):
            source_id = f"SRC_{profile_id}"
            source_set = source_sets_obj.get(source_id, {})
            excel = source_set.get("excel", {}) if isinstance(source_set, dict) else {}
            word = source_set.get("word", {}) if isinstance(source_set, dict) else {}
            graph_refs = source_set.get("graphs", []) if isinstance(source_set, dict) else []
            graph_ids = {entry.get("source_id") for entry in graph_refs if isinstance(entry, dict)}
            add_error(errors, excel.get("source_status") == "not_present_in_original_excel" and
                      excel.get("sheet") is None and excel.get("header_range") is None,
                      f"{source_id}: Excel absence must be explicit; no synthetic sheet/range allowed")
            add_error(errors, word.get("source_status") == "not_present_in_reference_word" and
                      word.get("table_id") is None,
                      f"{source_id}: Word absence must be explicit; no synthetic table allowed")
            add_error(errors, "piping_interface" in graph_ids,
                      f"{source_id}: piping_interface graph reference is required")

    profiles = data.get("profiles", [])
    add_error(errors, isinstance(profiles, list), "profiles must be an array")
    profile_ids = [item.get("authority_section_id") for item in profiles if isinstance(item, dict)] \
        if isinstance(profiles, list) else []
    add_error(errors, len(profiles) == len(EXPECTED_PROFILE_IDS), "profiles must contain 19 sections")
    add_error(errors, profile_ids == EXPECTED_PROFILE_IDS,
              "profiles must be ordered exactly T01-T14 then X01-X05")
    add_error(errors, not duplicate_values(profile_ids), "profile section IDs must be unique")

    occurrence_by_id: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    profile_fields_by_id: dict[str, dict[str, dict[str, Any]]] = {}
    profile_rows: list[dict[str, Any]] = []
    if isinstance(profiles, list):
        for index, profile in enumerate(profiles):
            location = f"profiles[{index}]"
            if not isinstance(profile, dict):
                errors.append(f"{location}: profile must be an object")
                continue
            profile_id = profile.get("authority_section_id")
            add_error(errors, profile_id in EXPECTED_PROFILE_IDS,
                      f"{location}: unknown authority_section_id {profile_id!r}")
            add_error(errors, isinstance(profile.get("title"), str) and bool(profile["title"].strip()),
                      f"{location}: title must be non-empty")
            add_error(errors, profile.get("family_id") in EXPECTED_FAMILIES,
                      f"{location}: unknown family_id {profile.get('family_id')!r}")
            tokens = profile.get("conditional_subtype_tokens")
            add_error(errors, isinstance(tokens, list) and bool(tokens) and
                      all(isinstance(token, str) and token.strip() for token in tokens),
                      f"{location}: conditional_subtype_tokens must be non-empty")
            fields = profile.get("required_fields")
            add_error(errors, isinstance(fields, list) and bool(fields),
                      f"{location}: required_fields must be non-empty")
            field_ids: list[str] = []
            if isinstance(fields, list):
                for field_index, field in enumerate(fields):
                    field_location = f"{location}.required_fields[{field_index}]"
                    validate_field(field, field_location, source_sets, gates, impacts, errors)
                    if isinstance(field, dict):
                        canonical_id = field.get("canonical_id")
                        if isinstance(canonical_id, str):
                            field_ids.append(canonical_id)
                            occurrence_by_id[canonical_id].append((str(profile_id), field))
                        refs = field.get("authority_sources")
                        if isinstance(profile_id, str) and isinstance(refs, list):
                            add_error(errors, f"SRC_{profile_id}" in refs,
                                      f"{field_location}: must cite SRC_{profile_id}")
            duplicates = duplicate_values(field_ids)
            add_error(errors, not duplicates,
                      f"{location}: duplicate canonical fields {duplicates}")
            if isinstance(profile_id, str):
                profile_fields_by_id[profile_id] = {
                    field["canonical_id"]: field
                    for field in fields
                    if isinstance(field, dict) and isinstance(field.get("canonical_id"), str)
                } if isinstance(fields, list) else {}

            routes = profile.get("deterministic_input_routes", [])
            if routes:
                add_error(errors, isinstance(routes, list),
                          f"{location}: deterministic_input_routes must be an array")
                if isinstance(routes, list):
                    for route_index, route in enumerate(routes):
                        route_location = f"{location}.deterministic_input_routes[{route_index}]"
                        if not isinstance(route, dict):
                            errors.append(f"{route_location}: route must be an object")
                            continue
                        aliases = route.get("source_aliases")
                        branches = route.get("routes")
                        add_error(errors, isinstance(aliases, list) and bool(aliases) and
                                  all(isinstance(alias, str) and alias.strip() for alias in aliases),
                                  f"{route_location}: source_aliases must be non-empty")
                        add_error(errors, route.get("on_no_match") ==
                                  "reject_ambiguous_input_and_require_explicit_canonical_field",
                                  f"{route_location}: ambiguous input must be rejected")
                        add_error(errors, isinstance(branches, list) and len(branches) >= 2,
                                  f"{route_location}: at least two deterministic routes are required")
                        if isinstance(branches, list):
                            target_ids: list[str] = []
                            for branch_index, branch in enumerate(branches):
                                branch_location = f"{route_location}.routes[{branch_index}]"
                                if not isinstance(branch, dict):
                                    errors.append(f"{branch_location}: branch must be an object")
                                    continue
                                target = branch.get("canonical_id")
                                target_ids.append(target) if isinstance(target, str) else None
                                add_error(errors, target in field_ids,
                                          f"{branch_location}: target must be a required field")
                                add_error(errors, branch.get("match_type") == "fullmatch_regex",
                                          f"{branch_location}: only fullmatch_regex is deterministic here")
                                try:
                                    re.compile(branch.get("pattern", ""))
                                except (re.error, TypeError) as exc:
                                    errors.append(f"{branch_location}: invalid regex: {exc}")
                            add_error(errors, not duplicate_values(target_ids),
                                      f"{route_location}: route targets must be unique")

            profile_rows.append({
                "profile_id": profile_id,
                "title": profile.get("title"),
                "family_id": profile.get("family_id"),
                "required_field_count": len(fields) if isinstance(fields, list) else 0,
                "source_set": f"SRC_{profile_id}",
            })

    global_fields = data.get("global_output_columns", [])
    add_error(errors, isinstance(global_fields, list) and bool(global_fields),
              "global_output_columns must be a non-empty array")
    global_ids: list[str] = []
    if isinstance(global_fields, list):
        for index, field in enumerate(global_fields):
            location = f"global_output_columns[{index}]"
            validate_field(field, location, source_sets, gates, impacts, errors)
            if isinstance(field, dict):
                canonical_id = field.get("canonical_id")
                if isinstance(canonical_id, str):
                    global_ids.append(canonical_id)
                    occurrence_by_id[canonical_id].append(("GLOBAL_INTERFACE", field))
                refs = field.get("authority_sources")
                if isinstance(refs, list):
                    add_error(errors, "GLOBAL_INTERFACE" in refs,
                              f"{location}: must cite GLOBAL_INTERFACE")
    add_error(errors, not duplicate_values(global_ids), "global_output_columns canonical IDs must be unique")

    authority_header_report: list[dict[str, Any]] = []
    global_field_map = {
        field["canonical_id"]: field
        for field in global_fields
        if isinstance(field, dict) and isinstance(field.get("canonical_id"), str)
    } if isinstance(global_fields, list) else {}
    excel_authority_path = artifact_paths.get("original_excel")
    word_authority_path = artifact_paths.get("reference_word")
    for profile_id in (f"T{i:02d}" for i in range(1, 15)):
        source_id = f"SRC_{profile_id}"
        source_set = source_sets_obj.get(source_id, {}) if isinstance(source_sets_obj, dict) else {}
        profile_fields = profile_fields_by_id.get(profile_id, {})
        available_fields = {**global_field_map, **profile_fields}
        excel = source_set.get("excel", {}) if isinstance(source_set, dict) else {}
        word = source_set.get("word", {}) if isinstance(source_set, dict) else {}
        actual_excel_headers: list[str] = []
        if excel_authority_path is not None:
            try:
                actual_excel_headers = extract_xlsx_header_labels(
                    excel_authority_path,
                    str(excel.get("sheet") or ""),
                    str(excel.get("header_range") or ""),
                )
            except (OSError, ValueError, KeyError, IndexError, zipfile.BadZipFile, ET.ParseError) as exc:
                errors.append(f"{source_id}.excel: cannot extract frozen OOXML headers: {exc}")
        authority_header_report.append(validate_header_channel_mapping(
            source_id=source_id,
            channel_name="excel",
            declared_headers=excel.get("header_labels"),
            actual_headers=actual_excel_headers,
            mappings=excel.get("header_mappings"),
            available_fields=available_fields,
            errors=errors,
        ))
        actual_word_headers: list[str] = []
        if word_authority_path is not None:
            try:
                actual_word_headers = extract_docx_table_header_labels(
                    word_authority_path,
                    str(word.get("table_id") or ""),
                )
            except (OSError, ValueError, KeyError, IndexError, zipfile.BadZipFile, ET.ParseError) as exc:
                errors.append(f"{source_id}.word: cannot extract frozen OOXML headers: {exc}")
        authority_header_report.append(validate_header_channel_mapping(
            source_id=source_id,
            channel_name="word",
            declared_headers=word.get("header_labels"),
            actual_headers=actual_word_headers,
            mappings=word.get("header_mappings"),
            available_fields=available_fields,
            errors=errors,
        ))

        value_rules = excel.get("source_value_state_rules", [])
        if profile_id == "T10":
            rule_ids = {
                rule.get("canonical_id")
                for rule in value_rules
                if isinstance(rule, dict)
            } if isinstance(value_rules, list) else set()
            add_error(
                errors,
                rule_ids == EXPECTED_T10_NOT_APPLICABLE_FIELDS,
                "SRC_T10.excel.source_value_state_rules must explicitly cover loading_coefficient "
                "and rotational_speed_rpm",
            )
            for index, rule in enumerate(value_rules if isinstance(value_rules, list) else []):
                location = f"authority_source_sets.SRC_T10.excel.source_value_state_rules[{index}]"
                if not isinstance(rule, dict):
                    errors.append(f"{location}: rule must be an object")
                    continue
                canonical_id = rule.get("canonical_id")
                field = profile_fields.get(str(canonical_id), {})
                add_error(errors, canonical_id in EXPECTED_T10_NOT_APPLICABLE_FIELDS,
                          f"{location}: unexpected canonical_id")
                add_error(errors, rule.get("source_token") == "/" and
                          rule.get("state") == "NOT_APPLICABLE",
                          f"{location}: source '/' must map to NOT_APPLICABLE")
                add_error(errors, field.get("not_applicable_allowed") is True and
                          "/" in field.get("not_applicable_tokens", []) and
                          field.get("not_applicable_state") == "NOT_APPLICABLE",
                          f"{location}: profile field must expose the same explicit N/A semantics")
        else:
            add_error(errors, not value_rules,
                      f"{source_id}.excel: unexpected source_value_state_rules")

    family_map = data.get("algorithm_family_profile_map", {})
    add_error(errors, isinstance(family_map, dict), "algorithm_family_profile_map must be an object")
    mapped_profile_ids: list[str] = []
    if isinstance(family_map, dict):
        add_error(errors, set(family_map) == set(EXPECTED_FAMILIES),
                  "algorithm_family_profile_map must contain exactly the 17 algorithm families")
        for family_id in EXPECTED_FAMILIES:
            entry = family_map.get(family_id)
            if not isinstance(entry, dict):
                errors.append(f"algorithm_family_profile_map.{family_id}: missing mapping object")
                continue
            ids = entry.get("profile_ids")
            add_error(errors, isinstance(ids, list) and
                      all(profile_id in EXPECTED_PROFILE_IDS for profile_id in ids),
                      f"algorithm_family_profile_map.{family_id}: invalid profile_ids")
            if not isinstance(ids, list):
                continue
            mapped_profile_ids.extend(ids)
            if family_id in EXPECTED_EMPTY_FAMILIES:
                add_error(errors, ids == [] and entry.get("delivery_status") ==
                          "no_dedicated_T01_T14_or_X01_X05_authority_profile",
                          f"algorithm_family_profile_map.{family_id}: must explicitly state no dedicated profile")
            else:
                add_error(errors, bool(ids) and entry.get("delivery_status") ==
                          "mapped_to_authority_profiles",
                          f"algorithm_family_profile_map.{family_id}: must map to at least one authority profile")
            for profile_id in ids:
                profile = next((item for item in profiles if isinstance(item, dict) and
                                item.get("authority_section_id") == profile_id), None)
                add_error(errors, bool(profile and profile.get("family_id") == family_id),
                          f"{profile_id}: profile family_id disagrees with algorithm mapping")
        add_error(errors, sorted(mapped_profile_ids) == sorted(EXPECTED_PROFILE_IDS),
                  "the 17-family map must cover each of the 19 profiles exactly once")
        add_error(errors, not duplicate_values(mapped_profile_ids),
                  "a delivery profile may not be mapped to more than one algorithm family")

    definitions = data.get("canonical_field_definitions", [])
    add_error(errors, isinstance(definitions, list) and bool(definitions),
              "canonical_field_definitions must be a non-empty array")
    definition_by_id: dict[str, dict[str, Any]] = {}
    if isinstance(definitions, list):
        definition_ids = [item.get("canonical_id") for item in definitions if isinstance(item, dict)]
        add_error(errors, not duplicate_values(definition_ids),
                  f"canonical definitions must be unique: {duplicate_values(definition_ids)}")
        for index, definition in enumerate(definitions):
            location = f"canonical_field_definitions[{index}]"
            if not isinstance(definition, dict):
                errors.append(f"{location}: definition must be an object")
                continue
            missing = DEFINITION_KEYS - set(definition)
            if missing:
                errors.append(f"{location}: missing definition keys {sorted(missing)}")
            canonical_id = definition.get("canonical_id")
            if not isinstance(canonical_id, str) or not SNAKE_CASE.fullmatch(canonical_id):
                errors.append(f"{location}: canonical_id must be lower snake_case")
                continue
            definition_by_id[canonical_id] = definition
            add_error(errors, isinstance(definition.get("label"), str) and bool(definition["label"].strip()),
                      f"{location}: label must be non-empty")
            add_error(errors, definition.get("unit") is None or isinstance(definition.get("unit"), str),
                      f"{location}: unit must be a string or null")
            add_error(errors, definition.get("data_type") in DATA_TYPES,
                      f"{location}: unsupported data_type")
            aliases = definition.get("aliases")
            add_error(errors, isinstance(aliases, list) and bool(aliases) and canonical_id in aliases and
                      all(isinstance(alias, str) and alias.strip() for alias in aliases),
                      f"{location}: aliases must be non-empty and include canonical_id")
            refs = definition.get("authority_sources")
            add_error(errors, isinstance(refs, list) and bool(refs) and
                      all(ref in source_sets for ref in refs),
                      f"{location}: authority_sources must be known and non-empty")
            evidence_gates = definition.get("evidence_gates")
            add_error(errors, isinstance(evidence_gates, list) and bool(evidence_gates) and
                      all(gate in gates for gate in evidence_gates),
                      f"{location}: evidence_gates must be known and non-empty")
            selection_impacts = definition.get("selection_impacts")
            add_error(errors, isinstance(selection_impacts, list) and bool(selection_impacts) and
                      all(impact in impacts for impact in selection_impacts),
                      f"{location}: selection_impacts must be known and non-empty")
            definition_profiles = definition.get("profile_ids")
            add_error(errors, isinstance(definition_profiles, list) and bool(definition_profiles) and
                      all(pid == "GLOBAL_INTERFACE" or pid in EXPECTED_PROFILE_IDS
                          for pid in definition_profiles),
                      f"{location}: profile_ids must be known and non-empty")
            add_error(errors, isinstance(definition.get("output_only"), bool) and
                      isinstance(definition.get("input_allowed"), bool) and
                      definition.get("output_only") != definition.get("input_allowed"),
                      f"{location}: exactly one of output_only/input_allowed must be true")

        occurrence_ids = set(occurrence_by_id)
        add_error(errors, set(definition_by_id) == occurrence_ids,
                  "canonical definitions must exactly cover global/profile field occurrences")
        for canonical_id, occurrences in occurrence_by_id.items():
            definition = definition_by_id.get(canonical_id)
            if not definition:
                continue
            expected_refs = sorted({ref for _, field in occurrences for ref in field["authority_sources"]})
            expected_gates = sorted({field["source_gate"] for _, field in occurrences})
            expected_impacts = sorted({field["selection_impact"] for _, field in occurrences})
            expected_profiles = sorted({profile_id for profile_id, _ in occurrences})
            expected_aliases = {alias for _, field in occurrences for alias in field["aliases"]}
            expected_types = {field["data_type"] for _, field in occurrences}
            expected_units = {field["unit"] for _, field in occurrences}
            expected_flags = {(field["output_only"], field["input_allowed"]) for _, field in occurrences}
            add_error(errors, sorted(definition.get("authority_sources", [])) == expected_refs,
                      f"definition {canonical_id}: authority_sources do not equal occurrence union")
            add_error(errors, sorted(definition.get("evidence_gates", [])) == expected_gates,
                      f"definition {canonical_id}: evidence_gates do not equal occurrence union")
            add_error(errors, sorted(definition.get("selection_impacts", [])) == expected_impacts,
                      f"definition {canonical_id}: selection_impacts do not equal occurrence union")
            add_error(errors, sorted(definition.get("profile_ids", [])) == expected_profiles,
                      f"definition {canonical_id}: profile_ids do not equal occurrence union")
            add_error(errors, expected_aliases <= set(definition.get("aliases", [])),
                      f"definition {canonical_id}: aliases do not cover occurrence aliases")
            add_error(errors, expected_types == {definition.get("data_type")},
                      f"definition {canonical_id}: inconsistent data_type across occurrences")
            add_error(errors, expected_units == {definition.get("unit")},
                      f"definition {canonical_id}: inconsistent unit across occurrences")
            add_error(errors, expected_flags == {(definition.get("output_only"), definition.get("input_allowed"))},
                      f"definition {canonical_id}: input/output flags disagree with occurrences")

    alias_owners: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for canonical_id, definition in definition_by_id.items():
        if not definition.get("input_allowed"):
            continue
        raw_aliases = [canonical_id, definition.get("label", ""), *definition.get("aliases", [])]
        for alias in raw_aliases:
            if isinstance(alias, str) and normalize_alias(alias):
                alias_owners[normalize_alias(alias)][canonical_id].add(alias)
    for normalized, owners in sorted(alias_owners.items()):
        if len(owners) > 1:
            detail = {owner: sorted(values) for owner, values in owners.items()}
            errors.append(f"input alias collision {normalized!r}: {detail}")

    for canonical_id in sorted(REQUIRED_OUTPUT_ONLY):
        definition = definition_by_id.get(canonical_id)
        add_error(errors, bool(definition and definition.get("output_only") is True and
                      definition.get("input_allowed") is False),
                  f"{canonical_id}: must be output_only=true and input_allowed=false")
        for profile_id, field in occurrence_by_id.get(canonical_id, []):
            add_error(errors, field.get("output_only") is True and field.get("input_allowed") is False,
                      f"{profile_id}.{canonical_id}: must remain output-only")

    standard_definition = definition_by_id.get("standard_identity")
    add_error(errors, bool(standard_definition and standard_definition.get("output_only") is False and
                  standard_definition.get("input_allowed") is True and
                  standard_definition.get("may_affect_deterministic_model_status") is False),
              "standard_identity must be input-allowed but may not affect deterministic model status")
    for profile_id, field in occurrence_by_id.get("standard_identity", []):
        add_error(errors, field.get("may_affect_deterministic_model_status") is False,
                  f"{profile_id}.standard_identity: deterministic model status flag must be false")

    validate_no_instance_values(data, errors)
    errors = list(dict.fromkeys(errors))
    family_unmapped = [family_id for family_id in EXPECTED_FAMILIES
                       if not isinstance(family_map.get(family_id), dict) or
                       not family_map[family_id].get("profile_ids")]
    return {
        "status": "PASS" if not errors else "FAIL",
        "schema": data.get("schema"),
        "input": str(input_path),
        "counts": {
            "profiles": len(profiles) if isinstance(profiles, list) else 0,
            "profile_required_fields": sum(row["required_field_count"] for row in profile_rows),
            "global_output_columns": len(global_fields) if isinstance(global_fields, list) else 0,
            "canonical_field_definitions": len(definitions) if isinstance(definitions, list) else 0,
            "algorithm_families": len(family_map) if isinstance(family_map, dict) else 0,
            "mapped_profiles": len(mapped_profile_ids),
            "authority_header_labels": sum(
                row["declared_header_count"] for row in authority_header_report
            ),
            "authority_header_mappings": sum(
                row["mapping_count"] for row in authority_header_report
            ),
            "errors": len(errors),
        },
        "profiles": profile_rows,
        "family_coverage": {
            "mapped_profile_ids": mapped_profile_ids,
            "families_without_dedicated_authority_profile": family_unmapped,
        },
        "source_artifacts": artifact_report,
        "authority_header_coverage": authority_header_report,
        "checks": {
            "exact_19_profile_coverage": profile_ids == EXPECTED_PROFILE_IDS,
            "exact_17_family_contract": isinstance(family_map, dict) and
                                        set(family_map) == set(EXPECTED_FAMILIES),
            "canonical_definitions_cover_occurrences": set(definition_by_id) == set(occurrence_by_id),
            "input_aliases_unique": not any(len(owners) > 1 for owners in alias_owners.values()),
            "required_output_only_boundary": all(
                definition_by_id.get(cid, {}).get("output_only") is True and
                definition_by_id.get(cid, {}).get("input_allowed") is False
                for cid in REQUIRED_OUTPUT_ONLY
            ),
            "standard_identity_non_deterministic": bool(
                standard_definition and
                standard_definition.get("may_affect_deterministic_model_status") is False
            ),
            "authority_files_hash_matched": bool(artifact_report) and
                                             all(item["hash_match"] for item in artifact_report),
            "authority_ooxml_headers_exact": len(authority_header_report) == 28 and all(
                row["exact_ooxml_match"] for row in authority_header_report
            ),
            "authority_header_mappings_complete": len(authority_header_report) == 28 and all(
                row["complete_mapping"] and
                row["mapping_count"] == row["declared_header_count"]
                for row in authority_header_report
            ),
            "instance_values_absent": not any("instance" in error or "numeric primitive" in error
                                               for error in errors),
        },
        "errors": errors,
    }


def render_markdown(report: dict[str, Any]) -> str:
    counts = report.get("counts", {})
    lines = [
        f"# Customer output profile validation: {report.get('status')}",
        "",
        f"- Input: `{report.get('input')}`",
        f"- Profiles: {counts.get('profiles')} (required: 19)",
        f"- Profile required-field occurrences: {counts.get('profile_required_fields')}",
        f"- Global output columns: {counts.get('global_output_columns')}",
        f"- Canonical field definitions: {counts.get('canonical_field_definitions')}",
        f"- Algorithm families: {counts.get('algorithm_families')} (required: 17)",
        f"- Mapped delivery profiles: {counts.get('mapped_profiles')} (required: 19)",
        f"- Frozen OOXML header labels: {counts.get('authority_header_labels')}",
        f"- Explicit header mappings: {counts.get('authority_header_mappings')}",
        f"- Errors: {counts.get('errors')}",
        "",
        "## Gate summary",
        "",
        "| Gate | Result |",
        "|---|---|",
    ]
    for name, passed in report.get("checks", {}).items():
        lines.append(f"| `{name}` | {'PASS' if passed else 'FAIL'} |")
    lines.extend([
        "",
        "## Profile coverage",
        "",
        "| ID | Authority title | Algorithm family | Required fields | Source set |",
        "|---|---|---|---:|---|",
    ])
    for row in report.get("profiles", []):
        lines.append(
            f"| {row.get('profile_id')} | {row.get('title')} | `{row.get('family_id')}` | "
            f"{row.get('required_field_count')} | `{row.get('source_set')}` |"
        )
    lines.extend(["", "## Authority artifacts", ""])
    for artifact in report.get("source_artifacts", []):
        lines.append(
            f"- `{artifact.get('artifact_id')}`: "
            f"{'SHA-256 PASS' if artifact.get('hash_match') else 'SHA-256 FAIL'} — "
            f"`{artifact.get('path')}`"
        )
    unmapped = report.get("family_coverage", {}).get(
        "families_without_dedicated_authority_profile", []
    )
    lines.extend([
        "",
        "## Families without a dedicated authority profile",
        "",
        *(f"- `{family_id}`" for family_id in unmapped),
    ])
    errors = report.get("errors", [])
    if errors:
        lines.extend(["", "## Errors", ""])
        lines.extend(f"- {error}" for error in errors)
    return "\n".join(lines).rstrip() + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    default_input = (
        Path(__file__).resolve().parents[1]
        / "knowledge_graph"
        / "equipment_customer_output_profiles.json"
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=default_input,
                        help="profile JSON path (defaults to the package contract)")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--output", type=Path,
                        help="optional report path; otherwise write to stdout")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    input_path = args.input.expanduser().resolve()
    try:
        data = json.loads(input_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        report = {"status": "FAIL", "input": str(input_path), "errors": [str(exc)]}
        text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.expanduser().resolve().write_text(text, encoding="utf-8", newline="\n")
        else:
            sys.stdout.write(text)
        return 1

    report = validate_document(data, input_path)
    text = (json.dumps(report, ensure_ascii=False, indent=2) + "\n"
            if args.format == "json" else render_markdown(report))
    if args.output:
        output_path = args.output.expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(text)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
