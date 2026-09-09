from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PACKAGE_ROOT / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import customer_delivery


SCHEMA = "stage1-detailed-equipment-and-pipe-reliability-audit-v2"
HASH_PATTERN_LENGTH = 64
NON_CONCRETE_TERMS = (
    "非标准",
    "非标",
    "未定型",
    "待定",
    "待确认",
    "其他型式",
    "通用型",
    "generic",
    "placeholder",
    "unknown",
)


NON_CONCRETE_TERMS = NON_CONCRETE_TERMS + (
    "非标准型",
    "非标准",
    "未定型",
    "待定",
    "待确认",
    "其他型式",
    "通用型",
)
SEVERITY_ORDER = {
    "NONE": 0,
    "INFO": 1,
    "WARNING": 2,
    "ERROR": 3,
    "CRITICAL": 4,
}
ASPEN_SEVERITY_ORDER = {
    "none": 0,
    "warning": 1,
    "error": 2,
    "severe_error": 3,
    "terminal_error": 4,
}
TOWER_BLOCK_TYPES = {
    "RADFRAC",
    "RATEFRAC",
    "DSTWU",
    "ABSBR",
    "EXTRACT",
}
TWO_PHASE_NAMES = {
    "mixed",
    "two_phase",
    "two-phase",
    "two phase",
    "multiphase",
}


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def parse_case_argument(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("--case must use LABEL=PATH")
    label, path_text = value.split("=", 1)
    label = label.strip()
    path = Path(path_text.strip()).expanduser().resolve()
    if not label:
        raise argparse.ArgumentTypeError("--case label must not be empty")
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"case result does not exist: {path}")
    return label, path


def finite_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def concrete_text(value: Any) -> bool:
    text = str(value or "").strip()
    folded = text.casefold()
    return bool(text) and not any(
        token.casefold() in folded for token in NON_CONCRETE_TERMS
    )


def field_value(specification: dict[str, Any], field_id: str) -> Any:
    fields = specification.get("fields")
    descriptor = fields.get(field_id) if isinstance(fields, dict) else None
    return descriptor.get("value") if isinstance(descriptor, dict) else None


def normalised_text(value: Any) -> str:
    return " ".join(str(value or "").split()).casefold()


def same_text(left: Any, right: Any) -> bool:
    return bool(normalised_text(left)) and (
        normalised_text(left) == normalised_text(right)
    )


def contains_any(value: Any, tokens: tuple[str, ...]) -> bool:
    text = normalised_text(value)
    return any(normalised_text(token) in text for token in tokens)


def numeric_equal(
    left: Any,
    right: Any,
    *,
    rel_tol: float = 1.0e-9,
    abs_tol: float = 1.0e-9,
) -> bool:
    left_number = finite_number(left)
    right_number = finite_number(right)
    return (
        left_number is not None
        and right_number is not None
        and math.isclose(
            left_number,
            right_number,
            rel_tol=rel_tol,
            abs_tol=abs_tol,
        )
    )


def normalised_standard_identity(value: Any) -> str:
    return "".join(
        character
        for character in str(value or "").upper()
        if character.isalnum()
    )


def public_key_paths(
    value: Any,
    *,
    target_keys: set[str],
    path: str = "$",
) -> list[str]:
    """Find public occurrences of semantically dangerous generic keys.

    Explicit ``pre_boundary``/``quarantine`` branches are audit evidence, not
    customer-facing projections, so they are deliberately excluded here.
    """

    paths: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            folded = key_text.casefold()
            child_path = f"{path}.{key_text}"
            if (
                "pre_boundary" in folded
                or "quarantin" in folded
                or folded.startswith("superseded_")
            ):
                continue
            if key_text in target_keys:
                paths.append(child_path)
            paths.extend(
                public_key_paths(
                    child,
                    target_keys=target_keys,
                    path=child_path,
                )
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            paths.extend(
                public_key_paths(
                    child,
                    target_keys=target_keys,
                    path=f"{path}[{index}]",
                )
            )
    return paths


def lineage_sources_valid(
    entries: list[dict[str, Any]],
    *,
    primary_source_sha256: str,
) -> bool:
    if not entries:
        return False
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        declared = str(entry.get("source_file_sha256") or "").upper()
        if not declared or declared == primary_source_sha256:
            continue
        source_path_text = str(
            entry.get("source_file_path") or ""
        ).strip()
        if not source_path_text:
            return False
        source_path = Path(source_path_text)
        if not source_path.is_absolute():
            source_path = PACKAGE_ROOT / source_path
        if (
            not source_path.is_file()
            or sha256_file(source_path) != declared
        ):
            return False
    return True


def highest_severity(values: list[str]) -> str:
    if not values:
        return "NONE"
    return max(
        (str(value or "NONE").upper() for value in values),
        key=lambda value: SEVERITY_ORDER.get(value, -1),
    )


def highest_aspen_severity(counts: Any) -> str:
    counts = counts if isinstance(counts, dict) else {}
    for count_key, label in (
        ("terminal_errors", "terminal_error"),
        ("severe_errors", "severe_error"),
        ("errors", "error"),
        ("warnings", "warning"),
    ):
        if int(finite_number(counts.get(count_key)) or 0) > 0:
            return label
    return "none"


def lineage_for(
    item: dict[str, Any],
    target_field: str,
) -> list[dict[str, Any]]:
    lineage = item.get("parameter_lineage")
    if not isinstance(lineage, list):
        return []
    return [
        entry
        for entry in lineage
        if isinstance(entry, dict)
        and str(entry.get("target_field") or "") == target_field
    ]


def calculation_by_id(
    match: dict[str, Any],
    calculation_id: str,
) -> dict[str, Any]:
    calculations = match.get("calculations")
    if not isinstance(calculations, list):
        return {}
    for calculation in calculations:
        if (
            isinstance(calculation, dict)
            and calculation.get("calculation_id") == calculation_id
        ):
            return calculation
    return {}


def row_gate_hash_and_identity_valid(
    *,
    gate: dict[str, Any],
    record_kind: str,
    identity: str,
) -> tuple[bool, bool]:
    hash_valid = hash_without_key(gate, "row_gate_sha256")
    bound = gate.get("bound_row")
    if isinstance(bound, dict):
        kind_valid = str(bound.get("record_kind") or "") == record_kind
        identity_valid = str(bound.get("identity") or "") == identity
        return hash_valid, kind_valid and identity_valid
    # Compatibility with an equivalent flat contract is intentional, but a
    # related block list alone is not identity binding for a PFD stream row.
    kind_valid = str(gate.get("bound_record_kind") or "") == record_kind
    identity_valid = str(gate.get("bound_identity") or "") == identity
    return hash_valid, kind_valid and identity_valid


def program_generated_record_binding_valid(
    *,
    item: dict[str, Any],
    record_kind: str,
    identity: str,
    source_export_sha256: str,
) -> tuple[bool, dict[str, Any]]:
    binding = (
        item.get("program_generated_record_binding")
        if isinstance(
            item.get("program_generated_record_binding"),
            dict,
        )
        else {}
    )
    match_result = (
        item.get("match_result")
        if isinstance(item.get("match_result"), dict)
        else {}
    )
    model = (
        match_result.get("model_recommendation")
        if isinstance(
            match_result.get("model_recommendation"),
            dict,
        )
        else {}
    )
    leading = (
        model.get("leading_candidate")
        if isinstance(model.get("leading_candidate"), dict)
        else {}
    )
    decision = (
        match_result.get("model_decision")
        if isinstance(match_result.get("model_decision"), dict)
        else {}
    )
    run_gate = (
        item.get("aspen_run_gate")
        if isinstance(item.get("aspen_run_gate"), dict)
        else {}
    )
    endpoint_audit = (
        item.get("endpoint_pressure_drop_audit")
        if isinstance(item.get("endpoint_pressure_drop_audit"), dict)
        else {}
    )
    lineage = (
        item.get("parameter_lineage")
        if isinstance(item.get("parameter_lineage"), list)
        else []
    )
    derivation_chain = (
        item.get("derivation_chain")
        if isinstance(item.get("derivation_chain"), list)
        else []
    )
    provenance = (
        item.get("input_provenance")
        if isinstance(item.get("input_provenance"), dict)
        else {}
    )
    provenance_payload = dict(provenance)
    declared_provenance_snapshot_sha256 = str(
        provenance_payload.pop("final_snapshot_sha256", "") or ""
    ).upper()
    expected_lineage_sha256 = canonical_sha256(lineage)
    expected_provenance_snapshot_sha256 = canonical_sha256(
        provenance_payload
    )
    provenance_snapshot_valid = (
        bool(provenance)
        and declared_provenance_snapshot_sha256
        == expected_provenance_snapshot_sha256
        and provenance.get("lineage_count") == len(lineage)
        and provenance.get("final_parameter_lineage_count")
        == len(lineage)
        and str(
            provenance.get("final_parameter_lineage_sha256") or ""
        ).upper()
        == expected_lineage_sha256
        and provenance.get(
            "summary_synchronized_after_programmatic_enrichment"
        )
        is True
        and match_result.get("input_provenance") == provenance
    )
    pipe_specification = item.get("programmatic_pipe_specification")
    valve_specification = item.get("programmatic_valve_specification")
    expected_specification_hashes = sorted({
        str(value).upper()
        for value in (
            (
                pipe_specification.get("program_specification_sha256")
                if isinstance(pipe_specification, dict)
                else None
            ),
            (
                valve_specification.get(
                    "program_specification_sha256"
                )
                if isinstance(valve_specification, dict)
                else None
            ),
            decision.get("program_specification_sha256"),
        )
        if value not in (None, "")
    })
    expected_projection = {
        "recommended_type": model.get("recommended_type"),
        "leading_candidate_designation": leading.get("designation"),
        "generated_candidate_designation": decision.get(
            "generated_candidate_designation"
        ),
        "candidate_model": decision.get("candidate_model"),
        "model_status": decision.get("model_status"),
        "selection_execution_status": (
            model.get("selection_execution", {}).get("status")
            if isinstance(model.get("selection_execution"), dict)
            else None
        ),
    }
    binding_sha256 = str(binding.get("binding_sha256") or "").upper()
    alias_contract_valid = True
    if record_kind == "equipment":
        alias_contract_valid = (
            str(
                item.get("equipment_program_specification_sha256")
                or ""
            ).upper()
            == binding_sha256
            and item.get("pipe_program_specification_sha256")
            in (None, "")
            and item.get("state_alias_binding_sha256") in (None, "")
        )
    elif record_kind == "physical_pipe_block":
        alias_contract_valid = (
            str(
                item.get("equipment_program_specification_sha256")
                or ""
            ).upper()
            == binding_sha256
            and str(
                item.get("pipe_program_specification_sha256") or ""
            ).upper()
            == binding_sha256
            and item.get("state_alias_binding_sha256") in (None, "")
        )
    elif record_kind == "piping":
        alias_contract_valid = (
            str(
                item.get("pipe_program_specification_sha256") or ""
            ).upper()
            == binding_sha256
            and item.get("equipment_program_specification_sha256")
            in (None, "")
            and item.get("state_alias_binding_sha256") in (None, "")
        )
    elif record_kind == "pfd_endpoint_state_alias":
        alias_contract_valid = (
            str(item.get("state_alias_binding_sha256") or "").upper()
            == binding_sha256
            and item.get("equipment_program_specification_sha256")
            in (None, "")
            and item.get("pipe_program_specification_sha256")
            in (None, "")
        )
    valid = (
        bool(binding)
        and hash_without_key(binding, "binding_sha256")
        and binding.get("schema")
        == "program-generated-stage1-row-binding-v1"
        and binding.get("deterministic") is True
        and binding.get("llm_used") is False
        and binding.get("program_generated") is True
        and binding.get("bound_row")
        == {"record_kind": record_kind, "identity": identity}
        and str(binding.get("source_export_sha256") or "").upper()
        == source_export_sha256
        and str(binding.get("aspen_row_gate_sha256") or "").upper()
        == str(run_gate.get("row_gate_sha256") or "").upper()
        and str(
            binding.get("canonical_match_input_sha256") or ""
        ).upper()
        == canonical_sha256(item.get("canonical_match_input", {}))
        and str(
            binding.get("parameter_lineage_sha256") or ""
        ).upper()
        == expected_lineage_sha256
        and str(
            binding.get("derivation_chain_sha256") or ""
        ).upper()
        == canonical_sha256(derivation_chain)
        and str(
            binding.get("input_provenance_snapshot_sha256") or ""
        ).upper()
        == declared_provenance_snapshot_sha256
        and provenance_snapshot_valid
        and str(binding.get("match_result_sha256") or "").upper()
        == canonical_sha256(match_result)
        and str(
            binding.get("evidence_boundary_sha256") or ""
        ).upper()
        == canonical_sha256(item.get("evidence_boundary", {}))
        and binding.get("program_specification_sha256s")
        == expected_specification_hashes
        and (
            str(
                binding.get(
                    "endpoint_pressure_drop_audit_sha256"
                )
                or ""
            ).upper()
            == str(endpoint_audit.get("audit_sha256") or "").upper()
        )
        and binding.get("final_type_projection")
        == expected_projection
        and str(
            item.get("program_generated_record_sha256") or ""
        ).upper()
        == binding_sha256
        and alias_contract_valid
    )
    return valid, {
        "record_kind": record_kind,
        "identity": identity,
        "binding_sha256": binding_sha256,
        "bound_row": binding.get("bound_row"),
        "program_specification_sha256s": binding.get(
            "program_specification_sha256s"
        ),
        "expected_program_specification_sha256s": (
            expected_specification_hashes
        ),
        "declared_provenance_snapshot_sha256": (
            declared_provenance_snapshot_sha256
        ),
        "expected_provenance_snapshot_sha256": (
            expected_provenance_snapshot_sha256
        ),
        "provenance_snapshot_valid": provenance_snapshot_valid,
        "alias_contract_valid": alias_contract_valid,
    }


def model_semantic_consistency_issues(
    *,
    row: dict[str, Any],
    match: dict[str, Any],
    model: dict[str, Any],
    leading: dict[str, Any],
    program_specification: dict[str, Any] | None = None,
) -> None:
    decision = (
        match.get("model_decision")
        if isinstance(match.get("model_decision"), dict)
        else {}
    )
    terminal = (
        model.get("terminal_selection")
        if isinstance(model.get("terminal_selection"), dict)
        else {}
    )
    leading_terminal = (
        leading.get("terminal_selection")
        if isinstance(leading.get("terminal_selection"), dict)
        else {}
    )
    decision_terminal = (
        decision.get("terminal_selection")
        if isinstance(decision.get("terminal_selection"), dict)
        else {}
    )
    recommended_surfaces = {
        "model": model.get("recommended_type"),
        "leading_candidate": leading.get("recommended_type"),
        "terminal_selection": terminal.get("recommended_type"),
        "leading_terminal_selection": leading_terminal.get(
            "recommended_type"
        ),
    }
    if decision_terminal:
        recommended_surfaces["decision_terminal_selection"] = (
            decision_terminal.get("recommended_type")
        )
    present_recommended = list(recommended_surfaces.values())
    add_issue(
        row,
        all(value not in (None, "") for value in present_recommended)
        and all(
            same_text(present_recommended[0], value)
            for value in present_recommended[1:]
        ),
        "MODEL_TERMINAL_LEADING_RECOMMENDED_TYPE_MISMATCH",
        severity="CRITICAL",
        context={"surfaces": recommended_surfaces},
    )
    quality_surfaces = [
        ("leading_candidate", leading),
        ("terminal_selection", terminal),
        ("leading_terminal_selection", leading_terminal),
    ]
    if decision_terminal:
        quality_surfaces.append(
            ("decision_terminal_selection", decision_terminal)
        )
    for index, candidate in enumerate(model.get("candidates", [])):
        if (
            isinstance(candidate, dict)
            and not str(candidate.get("status") or "").startswith("REJECTED_")
        ):
            quality_surfaces.append((f"active_candidate_{index}", candidate))
    for surface_name, surface in quality_surfaces:
        if not surface:
            continue
        quality = (
            surface.get("type_name_quality")
            if isinstance(surface.get("type_name_quality"), dict)
            else {}
        )
        add_issue(
            row,
            quality.get("is_concrete") is True
            and str(quality.get("status") or "")
            == "CONCRETE_ENGINEERING_TYPE"
            and same_text(
                quality.get("type_name"),
                surface.get("recommended_type"),
            ),
            f"TYPE_NAME_QUALITY_NOT_BOUND_TO_RECOMMENDATION:{surface_name}",
            severity="ERROR",
        )
    final_designation = leading.get("designation")
    generated_designation = decision.get(
        "generated_candidate_designation"
    )
    add_issue(
        row,
        same_text(final_designation, generated_designation),
        "MODEL_DECISION_GENERATED_DESIGNATION_DIFFERS_FROM_LEADING",
        severity="CRITICAL",
        context={
            "generated": generated_designation,
            "leading": final_designation,
        },
    )
    candidate_model = decision.get("candidate_model")
    if candidate_model not in (None, ""):
        add_issue(
            row,
            same_text(candidate_model, final_designation),
            "MODEL_DECISION_CANDIDATE_MODEL_DIFFERS_FROM_LEADING",
            severity="CRITICAL",
        )
    generated_candidate_model = decision.get("generated_candidate_model")
    if generated_candidate_model not in (None, ""):
        add_issue(
            row,
            same_text(generated_candidate_model, final_designation),
            "MODEL_DECISION_GENERATED_MODEL_DIFFERS_FROM_LEADING",
            severity="CRITICAL",
        )
    pre_boundary_candidate = decision.get("pre_boundary_candidate")
    if isinstance(pre_boundary_candidate, dict) and pre_boundary_candidate:
        add_issue(
            row,
            pre_boundary_candidate.get("role")
            == "SUPERSEDED_INTERNAL_MATCHER_PROJECTION"
            and pre_boundary_candidate.get(
                "not_for_customer_or_formal_use"
            )
            is True,
            "MODEL_DECISION_PREBOUNDARY_CANDIDATE_NOT_QUARANTINED",
            severity="CRITICAL",
        )
    projection = (
        model.get("projection_consistency")
        if isinstance(model.get("projection_consistency"), dict)
        else {}
    )
    if projection:
        add_issue(
            row,
            hash_without_key(projection, "audit_sha256")
            and same_text(
                projection.get("recommended_type"),
                model.get("recommended_type"),
            )
            and same_text(
                projection.get("leading_designation"),
                final_designation,
            )
            and same_text(
                projection.get("decision_designation"),
                generated_designation,
            )
            and projection.get("type_name_quality_consistent") is True
            and projection.get("designation_consistent") is True
            and projection.get("formal_ready") is False,
            "MODEL_BOUNDARY_PROJECTION_CONSISTENCY_INVALID",
            severity="CRITICAL",
        )
    if isinstance(program_specification, dict) and program_specification:
        add_issue(
            row,
            same_text(
                program_specification.get("designation"),
                final_designation,
            ),
            "PROGRAM_SPECIFICATION_DESIGNATION_DIFFERS_FROM_LEADING",
            severity="CRITICAL",
        )
        declared_hash = str(
            program_specification.get("program_specification_sha256")
            or ""
        ).upper()
        for surface_name, surface in (
            ("decision", decision),
            ("terminal", terminal),
            ("leading_terminal", leading_terminal),
        ):
            surface_hash = str(
                surface.get("program_specification_sha256") or ""
            ).upper()
            if surface_hash:
                add_issue(
                    row,
                    bool(declared_hash and surface_hash == declared_hash),
                    (
                        "PROGRAM_SPECIFICATION_HASH_NOT_PROPAGATED:"
                        f"{surface_name}"
                    ),
                    severity="CRITICAL",
                )


def hash_without_key(payload: Any, hash_key: str) -> bool:
    if not isinstance(payload, dict):
        return False
    candidate = copy.deepcopy(payload)
    declared = str(candidate.pop(hash_key, "") or "").upper()
    return (
        len(declared) == HASH_PATTERN_LENGTH
        and declared == canonical_sha256(candidate)
    )


def program_specification_hash_valid(specification: Any) -> bool:
    if not isinstance(specification, dict):
        return False
    candidate = copy.deepcopy(specification)
    declared = str(
        candidate.pop("program_specification_sha256", "") or ""
    ).upper()
    fields = candidate.get("fields")
    if isinstance(fields, dict):
        for descriptor in fields.values():
            if isinstance(descriptor, dict):
                descriptor.pop("program_specification_sha256", None)
    return (
        len(declared) == HASH_PATTERN_LENGTH
        and declared == canonical_sha256(candidate)
    )


def audit_model_source(
    *,
    leading: dict[str, Any],
    program_specification: dict[str, Any] | None,
) -> tuple[bool, str]:
    source = (
        leading.get("source")
        if isinstance(leading.get("source"), dict)
        else {}
    )
    kind = str(source.get("kind") or "")
    if kind in {
        "deterministic_programmatic_pipe_specification",
        "deterministic_programmatic_valve_specification",
    }:
        declared = str(
            source.get("program_specification_sha256") or ""
        ).upper()
        expected = str(
            (program_specification or {}).get(
                "program_specification_sha256"
            )
            or ""
        ).upper()
        return (
            bool(declared and declared == expected),
            kind,
        )
    path_text = source.get("model_rule_path") or source.get("catalog_path")
    declared = (
        source.get("model_rule_sha256")
        or source.get("catalog_sha256")
    )
    if path_text and declared:
        path = Path(str(path_text))
        if not path.is_absolute():
            path = PACKAGE_ROOT / path
        return (
            path.is_file()
            and sha256_file(path) == str(declared).upper(),
            kind,
        )
    return (False, kind or "MISSING_SOURCE")


def base_row(
    *,
    case_name: str,
    record_kind: str,
    identity: str,
    block_type: str | None,
    family_id: str | None,
    recommended_type: str | None,
    designation: str | None,
    run_gate: dict[str, Any],
) -> dict[str, Any]:
    case_gate = (
        run_gate.get("case")
        if isinstance(run_gate.get("case"), dict)
        else {}
    )
    return {
        "case": case_name,
        "record_kind": record_kind,
        "identity": identity,
        "aspen_block_type": block_type,
        "family_id": family_id,
        "recommended_type": recommended_type,
        "designation": designation,
        "aspen_case_status": (
            case_gate.get("status") or run_gate.get("case_status")
        ),
        "aspen_local_status": run_gate.get("local_status"),
        "aspen_case_run_gate_sha256": case_gate.get(
            "run_gate_sha256"
        ),
        "selected_dn": None,
        "outer_diameter_mm": None,
        "wall_thickness_mm": None,
        "pressure_class": None,
        "manufacturing_route": None,
        "pipe_entity_scope": None,
        "pipe_entity_id": None,
        "pipe_entity_role": None,
        "counted_as_physical_pipe": None,
        "alias_only": None,
        "canonical_pipe_entity_ids": None,
        "source_endpoint": None,
        "destination_endpoint": None,
        "endpoint_pressure_drop_status": None,
        "phase": None,
        "actual_velocity_m_s": None,
        "pressure_gradient_kpa_per_100m": None,
        "vacuum_margin_kpa": None,
        "external_pressure_branch": None,
        "program_specification_hash_valid": None,
        "preselection_hash_valid": None,
        "pressure_regime_hash_valid": None,
        "model_source_hash_valid": None,
        "lineage_source_hash_valid": None,
        "row_gate_hash_valid": None,
        "row_gate_identity_bound": None,
        "row_gate_dirty_affects_formal_use": None,
        "program_generated_binding_hash_valid": None,
        "program_generated_record_sha256": None,
        "aspen_configured_shaft_speed_candidate_rpm": None,
        "customer_information_coverage_state": None,
        "customer_missing_field_count": None,
        "customer_temperature_evidence_class": None,
        "highest_issue_severity": "NONE",
        "status": "PASS",
        "issues": [],
        "issue_details": [],
        "review_notes": [],
    }


def add_issue(
    row: dict[str, Any],
    condition: bool,
    code: str,
    *,
    severity: str = "ERROR",
    message: str | None = None,
    context: dict[str, Any] | None = None,
) -> None:
    if not condition:
        row["issues"].append(code)
        row["issue_details"].append({
            "code": code,
            "severity": severity.upper(),
            "message": message or code,
            "context": context or {},
        })
        row["highest_issue_severity"] = highest_severity([
            row.get("highest_issue_severity", "NONE"),
            severity,
        ])


def audit_row_gate(
    *,
    row: dict[str, Any],
    item: dict[str, Any],
) -> None:
    gate = (
        item.get("aspen_run_gate")
        if isinstance(item.get("aspen_run_gate"), dict)
        else {}
    )
    hash_valid, identity_bound = row_gate_hash_and_identity_valid(
        gate=gate,
        record_kind=str(row["record_kind"]),
        identity=str(row["identity"]),
    )
    row["row_gate_hash_valid"] = hash_valid
    row["row_gate_identity_bound"] = identity_bound
    add_issue(
        row,
        hash_valid,
        "ASPEN_ROW_GATE_HASH_INVALID",
        severity="CRITICAL",
    )
    add_issue(
        row,
        identity_bound,
        "ASPEN_ROW_GATE_HASH_NOT_BOUND_TO_ROW_IDENTITY",
        severity="CRITICAL",
    )
    case = gate.get("case") if isinstance(gate.get("case"), dict) else {}
    case_dirty = str(case.get("status") or "") != "CLEAN_RUN"
    boundary = (
        item.get("evidence_boundary")
        if isinstance(item.get("evidence_boundary"), dict)
        else {}
    )
    add_issue(
        row,
        str(boundary.get("aspen_row_gate_sha256") or "").upper()
        == str(gate.get("row_gate_sha256") or "").upper()
        and bool(gate.get("row_gate_sha256")),
        "EVIDENCE_BOUNDARY_ROW_GATE_HASH_LINK_INVALID",
        severity="CRITICAL",
    )
    affects = boundary.get("affects_aspen_formal_use_gate")
    row["row_gate_dirty_affects_formal_use"] = affects
    add_issue(
        row,
        (
            affects is True
            and gate.get("process_values_formally_releasable") is False
        )
        if case_dirty
        else (
            affects is False
            and gate.get("process_values_formally_releasable") is True
        ),
        "ASPEN_DIRTY_AFFECTS_FORMAL_USE_GATE_INCONSISTENT",
        severity="CRITICAL",
        context={
            "case_status": case.get("status"),
            "affects_aspen_formal_use_gate": affects,
            "process_values_formally_releasable": gate.get(
                "process_values_formally_releasable"
            ),
        },
    )
    local_issues = gate.get("local_block_issues")
    local_issues = local_issues if isinstance(local_issues, list) else []
    related_blocks = {
        str(block_id)
        for block_id in gate.get("related_block_ids", [])
    } if isinstance(gate.get("related_block_ids"), list) else set()
    local_issue_blocks = {
        str(issue.get("block_id") or "")
        for issue in local_issues
        if isinstance(issue, dict)
        and str(issue.get("block_id") or "")
    }
    add_issue(
        row,
        local_issue_blocks.issubset(related_blocks),
        "ASPEN_LOCAL_ISSUE_NOT_BOUND_TO_RELATED_BLOCK",
        severity="CRITICAL",
        context={
            "local_issue_blocks": sorted(local_issue_blocks),
            "related_block_ids": sorted(related_blocks),
        },
    )
    local_has_error = any(
        int(finite_number(issue.get("counts", {}).get(name)) or 0) > 0
        for issue in local_issues
        if isinstance(issue, dict)
        for name in ("terminal_errors", "severe_errors", "errors")
    )
    local_has_warning = bool(local_issues) and not local_has_error
    expected_local_status = (
        "LOCAL_ASPEN_BLOCK_ERROR"
        if local_has_error
        else "LOCAL_ASPEN_BLOCK_WARNING"
        if local_has_warning
        else "NO_LOCAL_EVENT_CASE_DIRTY"
        if case_dirty
        else "CLEAN_CASE_NO_LOCAL_EVENT"
    )
    add_issue(
        row,
        gate.get("local_status") == expected_local_status,
        "ASPEN_LOCAL_GATE_STATUS_INCONSISTENT",
        severity="CRITICAL",
        context={
            "expected": expected_local_status,
            "actual": gate.get("local_status"),
        },
    )
    for issue in local_issues:
        if not isinstance(issue, dict):
            continue
        counts = issue.get("counts")
        severity = highest_aspen_severity(counts)
        declared = str(issue.get("highest_severity") or "")
        add_issue(
            row,
            severity == declared,
            "ASPEN_LOCAL_ISSUE_HIGHEST_SEVERITY_MISMATCH",
            severity="CRITICAL",
            context={
                "computed": severity,
                "declared": declared,
                "block_id": issue.get("block_id"),
            },
        )
        if "affects_gate" in issue:
            add_issue(
                row,
                issue.get("affects_gate") is True,
                "DIRTY_ASPEN_EVENT_MARKED_AFFECTS_GATE_FALSE",
                severity="CRITICAL",
            )


def audit_pipe_record(
    *,
    case_name: str,
    record_kind: str,
    identity: str,
    item: dict[str, Any],
    source_export_sha256: str,
) -> dict[str, Any]:
    match = item.get("match_result") if isinstance(
        item.get("match_result"), dict
    ) else {}
    model = match.get("model_recommendation") if isinstance(
        match.get("model_recommendation"), dict
    ) else {}
    leading = model.get("leading_candidate") if isinstance(
        model.get("leading_candidate"), dict
    ) else {}
    record = item.get("canonical_match_input") if isinstance(
        item.get("canonical_match_input"), dict
    ) else {}
    specification = item.get("programmatic_pipe_specification")
    if not isinstance(specification, dict):
        specification = match.get("programmatic_pipe_specification")
    if not isinstance(specification, dict):
        specification = {}
    run_gate = item.get("aspen_run_gate") if isinstance(
        item.get("aspen_run_gate"), dict
    ) else {}
    row = base_row(
        case_name=case_name,
        record_kind=record_kind,
        identity=identity,
        block_type=record.get("aspen_block_type"),
        family_id=match.get("match", {}).get("family_id"),
        recommended_type=model.get("recommended_type"),
        designation=specification.get("designation"),
        run_gate=run_gate,
    )
    binding_valid, binding_context = (
        program_generated_record_binding_valid(
            item=item,
            record_kind=record_kind,
            identity=identity,
            source_export_sha256=source_export_sha256,
        )
    )
    row["program_generated_binding_hash_valid"] = binding_valid
    row["program_generated_record_sha256"] = item.get(
        "program_generated_record_sha256"
    )
    add_issue(
        row,
        binding_valid,
        "PROGRAM_GENERATED_PIPE_ROW_BINDING_INVALID",
        severity="CRITICAL",
        context=binding_context,
    )
    audit_row_gate(row=row, item=item)
    hydraulic = specification.get("hydraulic_calculation")
    hydraulic = hydraulic if isinstance(hydraulic, dict) else {}
    manufacturing = specification.get("manufacturing_route")
    manufacturing = manufacturing if isinstance(manufacturing, dict) else {}
    preselection = record.get("pipe_hydraulic_preselection")
    preselection = preselection if isinstance(preselection, dict) else {}
    pressure_regime = record.get("pipe_pressure_regime_screening")
    pressure_regime = (
        pressure_regime if isinstance(pressure_regime, dict) else {}
    )
    row.update({
        "selected_dn": field_value(specification, "selected_dn"),
        "outer_diameter_mm": field_value(
            specification, "selected_outer_diameter_mm"
        ),
        "wall_thickness_mm": field_value(
            specification, "selected_wall_thickness_mm"
        ),
        "pressure_class": field_value(specification, "pressure_class"),
        "manufacturing_route": manufacturing.get("route_code"),
        "phase": hydraulic.get("phase"),
        "actual_velocity_m_s": hydraulic.get("actual_velocity_m_s"),
        "pressure_gradient_kpa_per_100m": hydraulic.get(
            "pressure_gradient_kpa_per_100m"
        ),
        "vacuum_margin_kpa": pressure_regime.get("vacuum_margin_kpa"),
        "external_pressure_branch": pressure_regime.get(
            "external_pressure_branch"
        ),
    })
    row["program_specification_hash_valid"] = (
        program_specification_hash_valid(specification)
    )
    row["preselection_hash_valid"] = hash_without_key(
        preselection,
        "preselection_sha256",
    )
    row["pressure_regime_hash_valid"] = hash_without_key(
        pressure_regime,
        "pressure_regime_sha256",
    )
    source_ok, source_kind = audit_model_source(
        leading=leading,
        program_specification=specification,
    )
    row["model_source_hash_valid"] = source_ok
    lineage = item.get("parameter_lineage")
    lineage = lineage if isinstance(lineage, list) else []
    row["lineage_source_hash_valid"] = lineage_sources_valid(
        lineage,
        primary_source_sha256=source_export_sha256,
    )
    model_semantic_consistency_issues(
        row=row,
        match=match,
        model=model,
        leading=leading,
        program_specification=specification,
    )

    add_issue(
        row,
        match.get("status") == "MATCHED"
        and row["family_id"] == "family_process_piping",
        "PIPE_FAMILY_NOT_MATCHED",
    )
    add_issue(
        row,
        specification.get("status")
        == "PRELIMINARY_CONCRETE_SPECIFICATION_SELECTED",
        "PROGRAMMATIC_PIPE_SPECIFICATION_NOT_SELECTED",
    )
    add_issue(
        row,
        concrete_text(row["recommended_type"])
        and concrete_text(row["designation"]),
        "PIPE_TYPE_OR_DESIGNATION_NOT_CONCRETE",
    )
    for field_id in (
        "selected_dn",
        "selected_outer_diameter_mm",
        "selected_wall_thickness_mm",
        "pressure_class",
        "material",
        "manufacturing_method",
        "product_standard",
        "piping_class_candidate_code",
        "technical_specification",
    ):
        add_issue(
            row,
            field_value(specification, field_id) not in (None, ""),
            f"PIPE_FIELD_MISSING:{field_id}",
        )
    add_issue(
        row,
        row["program_specification_hash_valid"],
        "PIPE_PROGRAM_SPECIFICATION_HASH_INVALID",
    )
    add_issue(
        row,
        row["preselection_hash_valid"],
        "PIPE_HYDRAULIC_PRESELECTION_HASH_INVALID",
    )
    add_issue(
        row,
        row["pressure_regime_hash_valid"],
        "PIPE_PRESSURE_REGIME_HASH_INVALID",
    )
    add_issue(
        row,
        source_ok,
        f"PIPE_MODEL_SOURCE_HASH_INVALID:{source_kind}",
    )
    add_issue(
        row,
        row["lineage_source_hash_valid"],
        "PIPE_LINEAGE_SOURCE_HASH_INVALID",
    )
    pipe_case_gate = (
        run_gate.get("case")
        if isinstance(run_gate.get("case"), dict)
        else {}
    )
    if pipe_case_gate.get("status") == "DIRTY_RUN":
        execution = (
            model.get("selection_execution")
            if isinstance(model.get("selection_execution"), dict)
            else {}
        )
        add_issue(
            row,
            str(execution.get("status") or "").startswith(
                "TYPE_IDENTITY_ONLY_"
            )
            and execution.get("formal_selection_executed") is False
            and leading.get("eligible_for_formal_selection") is False,
            "DIRTY_ASPEN_PIPE_NOT_CAPPED_TO_TYPE_IDENTITY",
            severity="CRITICAL",
        )
    source_binding = (
        specification.get("source_binding")
        if isinstance(specification.get("source_binding"), dict)
        else {}
    )
    add_issue(
        row,
        str(
            source_binding.get("aspen_export_sha256") or ""
        ).upper()
        == source_export_sha256,
        "PIPE_PROGRAM_SPECIFICATION_SOURCE_BINDING_INVALID",
        severity="CRITICAL",
    )
    selected_dn = finite_number(row["selected_dn"])
    preselected_dn = finite_number(preselection.get("selected_dn_candidate"))
    add_issue(
        row,
        selected_dn is not None
        and preselected_dn is not None
        and math.isclose(selected_dn, preselected_dn, abs_tol=1.0e-9),
        "FINAL_DN_DIFFERS_FROM_HASHED_HYDRAULIC_PRESELECTION",
    )
    outer = finite_number(row["outer_diameter_mm"])
    wall = finite_number(row["wall_thickness_mm"])
    required_id = finite_number(
        preselection.get("controlling_required_inner_diameter_mm")
    )
    final_id = (
        outer - 2.0 * wall
        if outer is not None and wall is not None
        else None
    )
    add_issue(
        row,
        final_id is not None
        and required_id is not None
        and final_id + 1.0e-9 >= required_id,
        "FINAL_WALL_REDUCES_ID_BELOW_HYDRAULIC_REQUIREMENT",
    )
    phase = str(row["phase"] or "").casefold()
    two_phase = phase in TWO_PHASE_NAMES
    gradient = finite_number(row["pressure_gradient_kpa_per_100m"])
    velocity = finite_number(row["actual_velocity_m_s"])
    velocity_limit = {
        "liquid": 1.5,
        "vapor": 15.0,
        "mixed": 3.0,
        "two_phase": 3.0,
    }.get(phase, 1.5)
    add_issue(
        row,
        velocity is not None and velocity <= velocity_limit + 1.0e-9,
        "FINAL_VELOCITY_EXCEEDS_PROGRAM_SCREEN",
    )
    if two_phase:
        add_issue(
            row,
            str(hydraulic.get("status") or "").startswith("ADVISORY_")
            and hydraulic.get("formal_hydraulic_acceptance") is False
            and "PASS" not in str(hydraulic.get("status") or "")
            and "PASS" not in str(
                specification.get("pressure_wall_screening", {}).get(
                    "status"
                )
                or ""
            ),
            "TWO_PHASE_RESULT_NOT_STRICTLY_ADVISORY",
        )
        row["review_notes"].append(
            "Two-phase Darcy result is a homogeneous advisory proxy; "
            "flow regime, holdup, slip, flashing and slugging remain open."
        )
    else:
        add_issue(
            row,
            gradient is not None and gradient <= 50.0 + 1.0e-9,
            "FINAL_SINGLE_PHASE_GRADIENT_EXCEEDS_50_KPA_PER_100M_SCREEN",
        )
    if selected_dn is not None and selected_dn >= 600.0:
        wall_standard = (
            specification.get("standard_selections", {}).get("wall", {})
            if isinstance(specification.get("standard_selections"), dict)
            else {}
        )
        open_gates = manufacturing.get("open_gates")
        open_gates = open_gates if isinstance(open_gates, list) else []
        candidate_code = field_value(
            specification,
            "piping_class_candidate_code",
        )
        material_route = field_value(
            specification,
            "material_route_candidate",
        )
        material_grade = field_value(specification, "material_grade")
        add_issue(
            row,
            manufacturing.get("route_code") == "LSAW_PLATE_ROLLED"
            and manufacturing.get("large_bore_welded_route") is True
            and concrete_text(field_value(specification, "equipment_type"))
            and field_value(specification, "product_standard")
            == "OPEN_PROJECT_WELDED_PIPE_PRODUCT_SPECIFICATION_GATE"
            and manufacturing.get(
                "product_standard_scope_established"
            )
            is False
            and wall_standard.get("usage_role")
            == "GEOMETRY_REFERENCE_ONLY",
            "LARGE_BORE_WELDED_ROUTE_BOUNDARY_INVALID",
            severity="CRITICAL",
        )
        add_issue(
            row,
            wall_standard.get("product_scope_applicable") is False
            and (
                "welded_pipe_product_standard_and_dimensional_tolerances"
                in open_gates
                or "pipe_product_standard_scope_and_manufacturability"
                in open_gates
            ),
            "LSAW_PRODUCT_STANDARD_SCOPE_CONTRADICTION",
            severity="CRITICAL",
        )
        add_issue(
            row,
            material_grade == "OPEN_PROJECT_PLATE_GRADE_GATE",
            "LSAW_PLATE_GRADE_NOT_EXPLICITLY_OPEN",
            severity="CRITICAL",
        )
        add_issue(
            row,
            contains_any(candidate_code, ("LSAW",))
            and not contains_any(
                candidate_code,
                (
                    "CS20",
                    "09MND",
                    "15CRMO",
                    "304",
                    "316",
                    "Q235",
                    "Q345",
                ),
            )
            and not contains_any(
                material_route,
                (
                    "20钢",
                    "09MnD",
                    "15CrMo",
                    "304",
                    "316",
                    "Q235",
                    "Q345",
                ),
            ),
            "LSAW_OPEN_MATERIAL_GATE_CONTRADICTED_BY_CODE_OR_LABEL",
            severity="CRITICAL",
            context={
                "candidate_code": candidate_code,
                "material_route_candidate": material_route,
                "material_grade": material_grade,
            },
        )
        add_issue(
            row,
            normalised_text(wall_standard.get("standard_id"))
            != normalised_text(
                field_value(specification, "product_standard")
            ),
            "LSAW_GEOMETRY_STANDARD_MISREPRESENTED_AS_PRODUCT_STANDARD",
            severity="CRITICAL",
        )
    else:
        add_issue(
            row,
            manufacturing.get("route_code") == "SEAMLESS",
            "SMALL_BORE_MANUFACTURING_ROUTE_NOT_SEAMLESS",
        )
    vacuum_margin = finite_number(row["vacuum_margin_kpa"])
    vacuum_threshold = finite_number(
        pressure_regime.get("vacuum_threshold_kpa")
    )
    expected_external = (
        vacuum_margin is not None
        and vacuum_threshold is not None
        and vacuum_margin >= vacuum_threshold
    )
    add_issue(
        row,
        row["external_pressure_branch"] is expected_external,
        "EXTERNAL_PRESSURE_BRANCH_THRESHOLD_MISMATCH",
    )
    add_issue(
        row,
        specification.get("formal_readiness", {}).get("status")
        == "BLOCKED_PRELIMINARY_ONLY",
        "PIPE_FORMAL_GATE_IMPROPERLY_CLOSED",
    )
    fields = (
        specification.get("fields")
        if isinstance(specification.get("fields"), dict)
        else {}
    )
    product_descriptor = (
        fields.get("product_standard")
        if isinstance(fields.get("product_standard"), dict)
        else {}
    )
    product_evidence = (
        specification.get("product_standard_evidence")
        if isinstance(
            specification.get("product_standard_evidence"),
            dict,
        )
        else {}
    )
    product_evidence_hash = str(
        product_evidence.get("evidence_sha256") or ""
    ).upper()
    add_issue(
        row,
        bool(product_evidence)
        and hash_without_key(product_evidence, "evidence_sha256"),
        "PIPE_PRODUCT_STANDARD_EVIDENCE_MISSING_OR_HASH_INVALID",
        severity="CRITICAL",
    )
    inventory_path_text = str(
        product_evidence.get("inventory_path") or ""
    ).strip()
    inventory_path = Path(inventory_path_text)
    if inventory_path_text and not inventory_path.is_absolute():
        inventory_path = PACKAGE_ROOT / inventory_path
    inventory_sha256 = str(
        product_evidence.get("inventory_sha256") or ""
    ).upper()
    add_issue(
        row,
        bool(inventory_path_text)
        and inventory_path.is_file()
        and bool(inventory_sha256)
        and sha256_file(inventory_path) == inventory_sha256,
        "PIPE_PRODUCT_STANDARD_INVENTORY_FILE_OR_HASH_INVALID",
        severity="CRITICAL",
        context={
            "inventory_path": inventory_path_text,
            "declared_sha256": inventory_sha256,
        },
    )
    product_entry = product_evidence.get("entry")
    product_entry_hash = str(
        product_evidence.get("entry_sha256") or ""
    ).upper()
    source_status = str(product_evidence.get("source_status") or "")
    if source_status == "CATALOG_ENTRY_ONLY_NOT_SCOPE_VERIFIED":
        add_issue(
            row,
            isinstance(product_entry, dict)
            and bool(product_entry)
            and product_entry_hash == canonical_sha256(product_entry),
            "PIPE_PRODUCT_STANDARD_CATALOG_ENTRY_HASH_INVALID",
            severity="CRITICAL",
        )
    else:
        add_issue(
            row,
            product_entry in (None, {})
            and product_entry_hash == ""
            and source_status
            in {
                "PORTABLE_SOURCE_INVENTORY_ENTRY_MISSING",
                "PORTABLE_SOURCE_INVENTORY_FILE_MISSING",
            },
            "PIPE_PRODUCT_STANDARD_SOURCE_STATUS_OR_ENTRY_INCONSISTENT",
            severity="CRITICAL",
        )
    product_standard_value = field_value(
        specification,
        "product_standard",
    )
    standard_identity = product_evidence.get("standard_identity")
    identity_candidate = manufacturing.get(
        "product_standard_identity_candidate"
    )
    if identity_candidate is True:
        add_issue(
            row,
            bool(normalised_standard_identity(standard_identity))
            and normalised_standard_identity(standard_identity)
            == normalised_standard_identity(product_standard_value)
            and product_descriptor.get("state")
            == "PROGRAM_PRELIMINARY_STANDARD_IDENTITY_CANDIDATE"
            and product_descriptor.get("evidence_class") == "J"
            and product_descriptor.get("promotion_cap")
            == "TYPE_SCREENING",
            "PIPE_PRODUCT_STANDARD_IDENTITY_CANDIDATE_BOUNDARY_INVALID",
            severity="CRITICAL",
        )
        if isinstance(product_entry, dict) and product_entry:
            add_issue(
                row,
                normalised_standard_identity(standard_identity)
                in normalised_standard_identity(
                    " ".join(str(value) for value in product_entry.values())
                ),
                "PIPE_PRODUCT_STANDARD_CATALOG_ENTRY_IDENTITY_MISMATCH",
                severity="CRITICAL",
            )
    else:
        add_issue(
            row,
            identity_candidate is False
            and product_descriptor.get("state")
            == "OPEN_FORMAL_EVIDENCE_GATE"
            and product_descriptor.get("evidence_class") == "U"
            and product_descriptor.get("promotion_cap")
            == "NOT_PROMOTABLE",
            "PIPE_OPEN_PRODUCT_STANDARD_GATE_MISREPRESENTED_AS_CANDIDATE",
            severity="CRITICAL",
        )
    manufacturing_open_gates = manufacturing.get("open_gates")
    manufacturing_open_gates = (
        manufacturing_open_gates
        if isinstance(manufacturing_open_gates, list)
        else []
    )
    formal_open_gates = specification.get(
        "formal_readiness",
        {},
    ).get("open_gates")
    formal_open_gates = (
        formal_open_gates if isinstance(formal_open_gates, list) else []
    )
    add_issue(
        row,
        manufacturing.get("product_standard_scope_established") is False
        and product_evidence.get("product_scope_verified") is False
        and product_evidence.get("exact_table_page_verified") is False
        and product_descriptor.get("product_scope_verified") is False
        and product_evidence.get("promotion_cap") == "TYPE_SCREENING"
        and bool(str(product_evidence.get("warning") or "").strip())
        and product_descriptor.get("product_standard_evidence_sha256")
        == product_evidence_hash
        and manufacturing.get("product_standard_evidence_sha256")
        == product_evidence_hash
        and "pipe_product_standard_scope_verification"
        in manufacturing_open_gates
        and "pipe_product_standard_scope_and_manufacturability"
        in formal_open_gates,
        "PIPE_PRODUCT_STANDARD_SCOPE_OR_OPEN_GATE_CONTRADICTION",
        severity="CRITICAL",
    )

    viscosity_diagnostic = item.get("viscosity_fallback_diagnostic")
    if not isinstance(viscosity_diagnostic, dict):
        viscosity_diagnostic = record.get(
            "viscosity_fallback_diagnostic"
        )
    viscosity_diagnostic = (
        viscosity_diagnostic
        if isinstance(viscosity_diagnostic, dict)
        else {}
    )
    if viscosity_diagnostic:
        add_issue(
            row,
            hash_without_key(
                viscosity_diagnostic,
                "diagnostic_sha256",
            )
            and str(
                viscosity_diagnostic.get("source_export_sha256") or ""
            ).upper()
            == source_export_sha256,
            "PIPE_VISCOSITY_DIAGNOSTIC_HASH_OR_SOURCE_INVALID",
            severity="CRITICAL",
        )
    internal_viscosity = (
        viscosity_diagnostic.get("internal_correlation_used") is True
    )
    hydraulic_viscosity_origin = str(
        hydraulic.get("viscosity_origin") or ""
    )
    viscosity_descriptor = (
        fields.get("viscosity_basis_status")
        if isinstance(fields.get("viscosity_basis_status"), dict)
        else {}
    )
    if internal_viscosity:
        mandatory_warnings = {
            "W_VISCOSITY_INTERNAL_CORRELATION_ESTIMATE",
            "W_VISCOSITY_NOT_ASPEN_EXTRACTED",
            "W_VISCOSITY_PRELIMINARY_HYDRAULICS_ONLY",
            "W_CORRELATION_SOURCE_ASSET_HASH_NOT_LOCALLY_VERIFIED",
        }
        warning_codes = {
            str(code)
            for code in viscosity_diagnostic.get("warning_codes", [])
        } if isinstance(
            viscosity_diagnostic.get("warning_codes"),
            list,
        ) else set()
        pure_rows = viscosity_diagnostic.get(
            "pure_component_calculations"
        )
        pure_rows = pure_rows if isinstance(pure_rows, list) else []
        source_bundle_payload = [
            {
                "component_id": pure_row.get("component_id"),
                "source_record_sha256": pure_row.get(
                    "source_record_sha256"
                ),
            }
            for pure_row in pure_rows
            if isinstance(pure_row, dict)
        ]
        estimate_payload = copy.deepcopy(viscosity_diagnostic)
        for added_key in (
            "diagnostic_schema",
            "stream_id",
            "canonical_phase",
            "source_export_sha256",
            "correlation_records_embedded_in_source_export",
            "embedded_correlation_record_set_sha256",
            "correlation_registry",
            "internal_correlation_used",
            "diagnostic_sha256",
        ):
            estimate_payload.pop(added_key, None)
        add_issue(
            row,
            viscosity_diagnostic.get("status") == "PASS_WITH_WARNING"
            and viscosity_diagnostic.get("origin")
            == "INTERNAL_CORRELATION_ESTIMATE"
            and viscosity_diagnostic.get("evidence_class") == "J"
            and viscosity_diagnostic.get("formal_design_evidence") is False
            and viscosity_diagnostic.get("promotion_cap")
            == "TYPE_SCREENING"
            and finite_number(
                viscosity_diagnostic.get(
                    "dynamic_viscosity_mpa_s"
                )
            )
            is not None
            and float(
                viscosity_diagnostic["dynamic_viscosity_mpa_s"]
            )
            > 0.0
            and mandatory_warnings.issubset(warning_codes)
            and bool(
                str(
                    viscosity_diagnostic.get("claim_boundary") or ""
                ).strip()
            )
            and bool(viscosity_diagnostic.get("formula_sources"))
            and bool(pure_rows)
            and str(
                viscosity_diagnostic.get("result_sha256") or ""
            ).upper()
            == canonical_sha256({
                key: value
                for key, value in estimate_payload.items()
                if key != "result_sha256"
            })
            and str(
                viscosity_diagnostic.get("source_bundle_sha256") or ""
            ).upper()
            == canonical_sha256(source_bundle_payload),
            "PIPE_INTERNAL_VISCOSITY_FORMULA_EVIDENCE_INVALID",
            severity="CRITICAL",
        )
        add_issue(
            row,
            hydraulic_viscosity_origin
            == "INTERNAL_CORRELATION_ESTIMATE"
            and hydraulic.get("formal_hydraulic_acceptance") is False
            and "INTERNAL_VISCOSITY_WARNING"
            in str(
                hydraulic.get("hydraulic_acceptance_status") or ""
            )
            and "aspen_or_lab_viscosity_confirmation"
            in hydraulic.get("formal_exclusions", [])
            and viscosity_descriptor.get("state")
            == "OPEN_FORMAL_EVIDENCE_GATE"
            and viscosity_descriptor.get("evidence_class") == "J"
            and viscosity_descriptor.get("promotion_cap")
            == "TYPE_SCREENING"
            and viscosity_descriptor.get("provenance")
            == "INTERNAL_CORRELATION_ESTIMATE"
            and bool(str(viscosity_descriptor.get("warning") or "").strip())
            and "aspen_or_lab_viscosity_confirmation"
            in formal_open_gates,
            "PIPE_INTERNAL_VISCOSITY_WARNING_OR_FORMAL_GATE_MISSING",
            severity="CRITICAL",
        )
        row["review_notes"].append(
            "Dynamic viscosity is a source-bound internal correlation "
            "estimate, not an Aspen observation; formal hydraulics remain open."
        )
    else:
        add_issue(
            row,
            hydraulic_viscosity_origin
            != "INTERNAL_CORRELATION_ESTIMATE",
            "PIPE_VISCOSITY_ORIGIN_CONTRADICTS_DIAGNOSTIC",
            severity="CRITICAL",
        )
    pipe_scope = (
        item.get("pipe_entity_scope")
        or item.get("physical_scope")
        or record.get("pipe_entity_scope")
        or record.get("physical_scope")
    )
    expected_scope = (
        "PFD_MATERIAL_STREAM_SEGMENT"
        if record_kind == "piping"
        else "ASPEN_PHYSICAL_PIPE_BLOCK"
    )
    row["pipe_entity_scope"] = pipe_scope
    declared_pipe_entity_id = (
        item.get("pipe_entity_id")
        or record.get("pipe_entity_id")
    )
    row["pipe_entity_id"] = declared_pipe_entity_id
    pipe_entity_role = (
        item.get("pipe_entity_role")
        or record.get("pipe_entity_role")
    )
    counted_as_physical_pipe = (
        item.get("counted_as_physical_pipe")
        if "counted_as_physical_pipe" in item
        else record.get("counted_as_physical_pipe")
    )
    alias_only = (
        item.get("alias_only")
        if "alias_only" in item
        else record.get("alias_only")
    )
    canonical_pipe_entity_ids = item.get(
        "canonical_pipe_entity_ids"
    )
    if not isinstance(canonical_pipe_entity_ids, list):
        canonical_pipe_entity_ids = record.get(
            "canonical_pipe_entity_ids"
        )
    canonical_pipe_entity_ids = (
        [
            str(entity_id)
            for entity_id in canonical_pipe_entity_ids
            if str(entity_id)
        ]
        if isinstance(canonical_pipe_entity_ids, list)
        else []
    )
    row["pipe_entity_role"] = pipe_entity_role
    row["counted_as_physical_pipe"] = counted_as_physical_pipe
    row["alias_only"] = alias_only
    row["canonical_pipe_entity_ids"] = canonical_pipe_entity_ids
    row["source_endpoint"] = record.get("source_endpoint")
    row["destination_endpoint"] = record.get("destination_endpoint")
    expected_entity_id = (
        f"PFD_STREAM:{identity}"
        if record_kind == "piping"
        else f"ASPEN_PIPE_BLOCK:{identity}"
    )
    expected_entity_role = (
        "CANONICAL_PFD_PIPE_SEGMENT"
        if record_kind == "piping"
        else "CANONICAL_PHYSICAL_PIPE"
    )
    add_issue(
        row,
        str(pipe_scope or "") == expected_scope
        and str(declared_pipe_entity_id or "") == expected_entity_id
        and pipe_entity_role == expected_entity_role
        and counted_as_physical_pipe is True
        and alias_only is False
        and (
            record_kind != "piping"
            or canonical_pipe_entity_ids == [expected_entity_id]
        ),
        "PIPE_PHYSICAL_SCOPE_MISSING_OR_INCORRECT",
        severity="CRITICAL",
        context={
            "expected": expected_scope,
            "actual": pipe_scope,
            "expected_entity_id": expected_entity_id,
            "actual_entity_id": declared_pipe_entity_id,
            "expected_entity_role": expected_entity_role,
            "actual_entity_role": pipe_entity_role,
            "counted_as_physical_pipe": counted_as_physical_pipe,
            "alias_only": alias_only,
        },
    )
    add_issue(
        row,
        bool(str(declared_pipe_entity_id or "").strip()),
        "PIPE_ENTITY_ID_MISSING",
        severity="CRITICAL",
    )
    endpoint_audit = item.get("endpoint_pressure_drop_audit")
    if not isinstance(endpoint_audit, dict):
        endpoint_audit = record.get("endpoint_pressure_drop_audit")
    endpoint_audit = (
        endpoint_audit if isinstance(endpoint_audit, dict) else {}
    )
    endpoint_hash_key = (
        "audit_sha256"
        if "audit_sha256" in endpoint_audit
        else "endpoint_pressure_drop_audit_sha256"
    )
    add_issue(
        row,
        bool(endpoint_audit)
        and hash_without_key(endpoint_audit, endpoint_hash_key),
        "PIPE_ENDPOINT_PRESSURE_DROP_AUDIT_MISSING_OR_HASH_INVALID",
        severity="CRITICAL",
    )
    endpoint_drop = finite_number(
        endpoint_audit.get("endpoint_pressure_drop_kpa")
    )
    if endpoint_drop is None:
        endpoint_drop = finite_number(
            endpoint_audit.get("segment_pressure_drop_kpa")
        )
    if endpoint_drop is None:
        endpoint_drop = finite_number(
            endpoint_audit.get("pressure_drop_kpa")
        )
    endpoint_status = str(endpoint_audit.get("status") or "")
    row["endpoint_pressure_drop_status"] = endpoint_status
    add_issue(
        row,
        endpoint_audit.get("schema")
        == "pipe-endpoint-pressure-drop-audit-v1"
        and endpoint_audit.get("pipe_entity_scope") == pipe_scope
        and endpoint_audit.get("pipe_entity_id")
        == declared_pipe_entity_id
        and str(
            endpoint_audit.get("source_export_sha256") or ""
        ).upper()
        == source_export_sha256
        and endpoint_audit.get("formal_acceptance") is False
        and endpoint_audit.get("formal_ready") is False
        and endpoint_audit.get(
            "independent_friction_loss_reconciliation_complete"
        )
        is False,
        "PIPE_ENDPOINT_PRESSURE_DROP_AUDIT_BOUNDARY_INVALID",
        severity="CRITICAL",
    )
    if record_kind == "physical_pipe_block":
        inlet_pressure = finite_number(
            endpoint_audit.get("inlet_pressure_mpa")
        )
        outlet_pressure = finite_number(
            endpoint_audit.get("outlet_pressure_mpa")
        )
        expected_drop = (
            (inlet_pressure - outlet_pressure) * 1000.0
            if inlet_pressure is not None and outlet_pressure is not None
            else None
        )
        expected_direction = (
            "DROP"
            if expected_drop is not None and expected_drop > 1.0e-9
            else "RISE"
            if expected_drop is not None and expected_drop < -1.0e-9
            else "NEGLIGIBLE"
            if expected_drop is not None
            else "UNKNOWN"
        )
        inlet_binding = endpoint_audit.get("inlet_pressure_binding")
        outlet_binding = endpoint_audit.get("outlet_pressure_binding")
        inlet_binding = (
            inlet_binding if isinstance(inlet_binding, dict) else {}
        )
        outlet_binding = (
            outlet_binding if isinstance(outlet_binding, dict) else {}
        )
        add_issue(
            row,
            endpoint_drop is not None
            and expected_drop is not None
            and math.isclose(
                endpoint_drop,
                expected_drop,
                rel_tol=1.0e-6,
                abs_tol=1.0e-6,
            )
            and endpoint_status
            == "ASPEN_ENDPOINT_PRESSURE_DIFFERENCE_CALCULATED"
            and endpoint_audit.get("endpoint_cardinality_complete") is True
            and endpoint_audit.get("endpoint_pressure_complete") is True
            and endpoint_audit.get("endpoint_complete") is True
            and endpoint_audit.get("pressure_change_direction")
            == expected_direction
            and bool(inlet_binding.get("stream_id"))
            and bool(outlet_binding.get("stream_id"))
            and numeric_equal(
                inlet_binding.get("pressure_mpa"),
                inlet_pressure,
            )
            and numeric_equal(
                outlet_binding.get("pressure_mpa"),
                outlet_pressure,
            )
            and bool(endpoint_audit.get("open_gates")),
            "PHYSICAL_PIPE_ENDPOINT_PRESSURE_DROP_MISSING_OR_INCONSISTENT",
            severity="CRITICAL",
            context={
                "audit_pressure_drop_kpa": endpoint_drop,
                "computed_pressure_drop_kpa": expected_drop,
                "pressure_change_direction": endpoint_audit.get(
                    "pressure_change_direction"
                ),
            },
        )
        published_drop = finite_number(
            record.get("aspen_endpoint_pressure_drop_kpa")
        )
        pressure_drop_lineage = lineage_for(
            item,
            "aspen_endpoint_pressure_drop_kpa",
        )
        add_issue(
            row,
            published_drop is not None
            and endpoint_drop is not None
            and numeric_equal(
                published_drop,
                endpoint_drop,
                rel_tol=1.0e-6,
                abs_tol=1.0e-6,
            )
            and any(
                str(entry.get("evidence_class") or "").upper() == "D"
                and str(
                    entry.get("source_file_sha256") or ""
                ).upper()
                == source_export_sha256
                and numeric_equal(
                    entry.get("value"),
                    endpoint_drop,
                    rel_tol=1.0e-6,
                    abs_tol=1.0e-6,
                )
                for entry in pressure_drop_lineage
            ),
            "PHYSICAL_PIPE_ENDPOINT_DROP_NOT_PUBLISHED_WITH_D_LINEAGE",
            severity="CRITICAL",
        )
    else:
        add_issue(
            row,
            endpoint_drop is None
            and endpoint_status
            == "OPEN_SINGLE_PFD_STREAM_STATE_HAS_NO_ENDPOINT_PAIR"
            and endpoint_audit.get("endpoint_cardinality_complete") is False
            and endpoint_audit.get("endpoint_pressure_complete") is False
            and endpoint_audit.get("endpoint_complete") is False
            and str(
                endpoint_audit.get(
                    "independent_reconciliation_status"
                )
                or ""
            ).startswith("BLOCKED_")
            and bool(endpoint_audit.get("open_gates")),
            "PFD_PIPE_MISSING_ENDPOINT_DROP_NOT_EXPLICITLY_GATED",
            severity="CRITICAL",
        )
        temperature = finite_number(
            record.get("operating_temperature_c")
        )
        temperature_lineage = lineage_for(
            item,
            "operating_temperature_c",
        )
        matching_temperature_lineage = [
            entry
            for entry in temperature_lineage
            if finite_number(entry.get("value")) is not None
            and temperature is not None
            and math.isclose(
                float(entry["value"]),
                temperature,
                rel_tol=1.0e-9,
                abs_tol=1.0e-9,
            )
        ]
        add_issue(
            row,
            temperature is not None
            and bool(matching_temperature_lineage)
            and all(
                str(entry.get("evidence_class") or "").upper() == "D"
                and str(entry.get("source_file_sha256") or "").upper()
                == source_export_sha256
                for entry in matching_temperature_lineage
            ),
            "PFD_PIPE_TEMPERATURE_MISSING_OR_U_EVIDENCE",
            severity="CRITICAL",
        )
    row["review_notes"].append(
        f"Model source={source_kind}; final ID={final_id}; "
        f"hydraulic requirement={required_id}."
    )
    if row["issues"]:
        row["status"] = "FAIL"
    return row


def audit_equipment_record(
    *,
    case_name: str,
    item: dict[str, Any],
    source_export_sha256: str,
) -> dict[str, Any]:
    match = item.get("match_result") if isinstance(
        item.get("match_result"), dict
    ) else {}
    model = match.get("model_recommendation") if isinstance(
        match.get("model_recommendation"), dict
    ) else {}
    leading = model.get("leading_candidate") if isinstance(
        model.get("leading_candidate"), dict
    ) else {}
    record = item.get("canonical_match_input") if isinstance(
        item.get("canonical_match_input"), dict
    ) else {}
    block_type = str(record.get("aspen_block_type") or "")
    identity = str(
        item.get("equipment_tag") or item.get("aspen_block_id") or ""
    )
    run_gate = item.get("aspen_run_gate") if isinstance(
        item.get("aspen_run_gate"), dict
    ) else {}
    logic_node = (
        item.get("aspen_mapping_status")
        == "NOT_APPLICABLE_SIMULATION_LOGIC_NODE"
        or match.get("status") == "NOT_APPLICABLE"
    )
    if logic_node:
        row = base_row(
            case_name=case_name,
            record_kind="logic_node",
            identity=identity,
            block_type=block_type,
            family_id=None,
            recommended_type=model.get("recommended_type"),
            designation=None,
            run_gate=run_gate,
        )
        binding_valid, binding_context = (
            program_generated_record_binding_valid(
                item=item,
                record_kind="logic_node",
                identity=identity,
                source_export_sha256=source_export_sha256,
            )
        )
        row["program_generated_binding_hash_valid"] = binding_valid
        row["program_generated_record_sha256"] = item.get(
            "program_generated_record_sha256"
        )
        add_issue(
            row,
            binding_valid,
            "PROGRAM_GENERATED_LOGIC_ROW_BINDING_INVALID",
            severity="CRITICAL",
            context=binding_context,
        )
        audit_row_gate(row=row, item=item)
        row["review_notes"].append(
            "Simulation logic node is explicitly excluded from independent "
            "physical equipment selection."
        )
        if row["issues"]:
            row["status"] = "FAIL"
        return row
    if block_type == "PIPE":
        return audit_pipe_record(
            case_name=case_name,
            record_kind="physical_pipe_block",
            identity=identity,
            item=item,
            source_export_sha256=source_export_sha256,
        )

    designation = str(
        leading.get("designation")
        or model.get("recommended_type")
        or ""
    )
    family_id = match.get("match", {}).get("family_id")
    row = base_row(
        case_name=case_name,
        record_kind="equipment",
        identity=identity,
        block_type=block_type,
        family_id=family_id,
        recommended_type=model.get("recommended_type"),
        designation=designation,
        run_gate=run_gate,
    )
    binding_valid, binding_context = (
        program_generated_record_binding_valid(
            item=item,
            record_kind="equipment",
            identity=identity,
            source_export_sha256=source_export_sha256,
        )
    )
    row["program_generated_binding_hash_valid"] = binding_valid
    row["program_generated_record_sha256"] = item.get(
        "program_generated_record_sha256"
    )
    add_issue(
        row,
        binding_valid,
        "PROGRAM_GENERATED_EQUIPMENT_ROW_BINDING_INVALID",
        severity="CRITICAL",
        context=binding_context,
    )
    audit_row_gate(row=row, item=item)
    valve_specification = item.get("programmatic_valve_specification")
    if not isinstance(valve_specification, dict):
        valve_specification = None
    source_ok, source_kind = audit_model_source(
        leading=leading,
        program_specification=valve_specification,
    )
    row["model_source_hash_valid"] = source_ok
    lineage = item.get("parameter_lineage")
    lineage = lineage if isinstance(lineage, list) else []
    row["lineage_source_hash_valid"] = lineage_sources_valid(
        lineage,
        primary_source_sha256=source_export_sha256,
    )
    model_semantic_consistency_issues(
        row=row,
        match=match,
        model=model,
        leading=leading,
        program_specification=valve_specification,
    )
    add_issue(
        row,
        match.get("status") == "MATCHED" and bool(family_id),
        "EQUIPMENT_FAMILY_NOT_MATCHED",
    )
    add_issue(
        row,
        concrete_text(row["recommended_type"])
        and concrete_text(row["designation"]),
        "EQUIPMENT_TYPE_OR_DESIGNATION_NOT_CONCRETE",
    )
    add_issue(
        row,
        source_ok,
        f"EQUIPMENT_MODEL_SOURCE_HASH_INVALID:{source_kind}",
    )
    add_issue(
        row,
        row["lineage_source_hash_valid"],
        "EQUIPMENT_LINEAGE_SOURCE_HASH_INVALID",
    )
    add_issue(
        row,
        leading.get("is_vendor_model") is not True
        and leading.get("formal_model") is not True,
        "PRELIMINARY_EQUIPMENT_MISREPRESENTED_AS_FORMAL_VENDOR_MODEL",
    )
    row_case_gate = (
        run_gate.get("case")
        if isinstance(run_gate.get("case"), dict)
        else {}
    )
    if row_case_gate.get("status") == "DIRTY_RUN":
        add_issue(
            row,
            str(
                model.get("selection_execution", {}).get("status") or ""
            ).startswith("TYPE_IDENTITY_ONLY_"),
            "DIRTY_ASPEN_EQUIPMENT_NOT_CAPPED_TO_TYPE_IDENTITY",
        )

    if block_type == "PUMP":
        power = record.get("pump_power_process_audit")
        power = power if isinstance(power, dict) else {}
        add_issue(
            row,
            power.get("schema") == "pump-power-process-audit-v1"
            and hash_without_key(power, "audit_sha256"),
            "PUMP_POWER_PROCESS_AUDIT_HASH_INVALID",
            severity="CRITICAL",
        )
        power_balance_payload = {
            key: power.get(key)
            for key in (
                "hydraulic_power_kw",
                "shaft_power_kw",
                "electrical_power_kw",
                "pump_efficiency_percent",
                "driver_efficiency_percent",
                "calculated_shaft_power_kw",
                "calculated_electrical_power_kw",
            )
        }
        add_issue(
            row,
            str(power.get("power_balance_sha256") or "").upper()
            == canonical_sha256(power_balance_payload),
            "PUMP_POWER_BALANCE_HASH_INVALID",
            severity="CRITICAL",
        )
        add_issue(
            row,
            power.get("wnet_semantic_for_pump")
            == "ELECTRICAL_INPUT_POWER"
            and power.get("formal_ready") is False
            and power.get("formal_driver_selection_complete") is False
            and bool(power.get("open_gates")),
            "PUMP_WNET_SEMANTIC_OR_FORMAL_BOUNDARY_INVALID",
            severity="CRITICAL",
        )
        wnet_lineage = [
            entry
            for entry in lineage
            if isinstance(entry, dict)
            and str(entry.get("source_field") or "").upper() == "WNET"
        ]
        add_issue(
            row,
            all(
                entry.get("target_field") == "electrical_power_kw"
                and entry.get("origin")
                == "ASPEN_PUMP_ELECTRICAL_INPUT_POWER"
                and entry.get("evidence_scope")
                == "PUMP_PROCESS_POWER_BALANCE"
                for entry in wnet_lineage
            ),
            "PUMP_WNET_MAPPED_TO_SHAFT_OR_UNTYPED_POWER",
            severity="CRITICAL",
        )
        hydraulic_power = finite_number(power.get("hydraulic_power_kw"))
        shaft_power = finite_number(power.get("shaft_power_kw"))
        electrical_power = finite_number(
            power.get("electrical_power_kw")
        )
        channel_bindings = (
            (
                "hydraulic_power_kw",
                hydraulic_power,
                record.get("hydraulic_power_kw"),
                "ASPEN_PUMP_FLUID_POWER",
            ),
            (
                "shaft_power_kw",
                shaft_power,
                record.get("shaft_power_kw"),
                "ASPEN_PUMP_BRAKE_POWER",
            ),
            (
                "electrical_power_kw",
                electrical_power,
                record.get("electrical_power_kw"),
                "ASPEN_PUMP_ELECTRICAL_INPUT_POWER",
            ),
            (
                "driver_efficiency_percent",
                finite_number(power.get("driver_efficiency_percent")),
                record.get("driver_efficiency_percent"),
                "ASPEN_PUMP_DRIVER_EFFICIENCY",
            ),
        )
        for (
            target_field,
            audit_value,
            record_value,
            expected_origin,
        ) in channel_bindings:
            if audit_value is None:
                continue
            channel_lineage = lineage_for(item, target_field)
            add_issue(
                row,
                numeric_equal(audit_value, record_value)
                and any(
                    entry.get("origin") == expected_origin
                    and entry.get("evidence_scope")
                    == "PUMP_PROCESS_POWER_BALANCE"
                    and str(
                        entry.get("evidence_class") or ""
                    ).upper()
                    == "D"
                    and entry.get("formal_design_evidence") is False
                    and numeric_equal(entry.get("value"), audit_value)
                    for entry in channel_lineage
                ),
                f"PUMP_POWER_CHANNEL_NOT_BOUND_TO_TYPED_LINEAGE:{target_field}",
                severity="CRITICAL",
            )
        electrical_lineage = lineage_for(
            item,
            "electrical_power_kw",
        )
        if electrical_power is not None:
            add_issue(
                row,
                bool(electrical_lineage)
                and any(
                    entry.get("origin")
                    == "ASPEN_PUMP_ELECTRICAL_INPUT_POWER"
                    and entry.get("evidence_scope")
                    == "PUMP_PROCESS_POWER_BALANCE"
                    for entry in electrical_lineage
                ),
                "PUMP_ELECTRICAL_POWER_LACKS_TYPED_LINEAGE",
                severity="CRITICAL",
            )
        configured_speed = finite_number(
            record.get(
                "aspen_configured_shaft_speed_candidate_rpm"
            )
        )
        row[
            "aspen_configured_shaft_speed_candidate_rpm"
        ] = configured_speed
        if configured_speed is not None:
            configured_speed_lineage = lineage_for(
                item,
                "aspen_configured_shaft_speed_candidate_rpm",
            )
            add_issue(
                row,
                configured_speed > 0.0
                and any(
                    entry.get("origin")
                    == (
                        "ASPEN_PUMP_CONFIGURED_SHAFT_SPEED_"
                        "INPUT_CANDIDATE"
                    )
                    and entry.get("evidence_scope")
                    == "PUMP_CONFIGURED_SPEED_SEARCH_INPUT_ONLY"
                    and entry.get("result_status")
                    == (
                        "ASPEN_CONFIGURED_INPUT_CANDIDATE_"
                        "NOT_SOLVED_ACTUAL_SPEED"
                    )
                    and str(
                        entry.get("evidence_class") or ""
                    ).upper()
                    == "R"
                    and entry.get("promotion_cap")
                    == "TYPE_SCREENING"
                    and entry.get("formal_design_evidence") is False
                    and numeric_equal(
                        entry.get("value"),
                        configured_speed,
                    )
                    for entry in configured_speed_lineage
                ),
                "PUMP_CONFIGURED_SPEED_MISREPRESENTED_AS_ACTUAL_OR_UNBOUND",
                severity="CRITICAL",
                context={
                    "configured_speed_rpm": configured_speed,
                    "lineage_count": len(
                        configured_speed_lineage
                    ),
                },
            )
        pump_efficiency = finite_number(
            power.get("pump_efficiency_percent")
        )
        driver_efficiency = finite_number(
            power.get("driver_efficiency_percent")
        )
        calculated_shaft = finite_number(
            power.get("calculated_shaft_power_kw")
        )
        calculated_electrical = finite_number(
            power.get("calculated_electrical_power_kw")
        )
        shaft_error = finite_number(
            power.get("shaft_power_relative_error")
        )
        electrical_error = finite_number(
            power.get("electrical_power_relative_error")
        )
        add_issue(
            row,
            (
                pump_efficiency is None
                or 0.0 < pump_efficiency <= 100.0
            )
            and (
                driver_efficiency is None
                or 0.0 < driver_efficiency <= 100.0
            )
            and (
                pump_efficiency is None
                or numeric_equal(
                    pump_efficiency,
                    record.get("efficiency_percent"),
                )
            ),
            "PUMP_OR_DRIVER_EFFICIENCY_NONPHYSICAL_OR_UNBOUND",
            severity="CRITICAL",
        )
        if hydraulic_power is not None and shaft_power is not None:
            add_issue(
                row,
                hydraulic_power >= -1.0e-12
                and shaft_power + 1.0e-12 >= hydraulic_power,
                "PUMP_HYDRAULIC_POWER_EXCEEDS_SHAFT_POWER",
                severity="CRITICAL",
            )
        if shaft_power is not None and electrical_power is not None:
            power_hierarchy_tolerance = finite_number(
                power.get("balance_relative_error_tolerance")
            )
            if power_hierarchy_tolerance is None:
                power_hierarchy_tolerance = 0.005
            hierarchy_allowance = (
                max(abs(shaft_power), abs(electrical_power), 1.0)
                * power_hierarchy_tolerance
            )
            add_issue(
                row,
                electrical_power + hierarchy_allowance >= shaft_power,
                "PUMP_SHAFT_POWER_EXCEEDS_ELECTRICAL_POWER",
                severity="CRITICAL",
                context={
                    "shaft_power_kw": shaft_power,
                    "electrical_power_kw": electrical_power,
                    "relative_tolerance": power_hierarchy_tolerance,
                    "absolute_allowance_kw": hierarchy_allowance,
                },
            )
        if (
            hydraulic_power is not None
            and pump_efficiency is not None
            and pump_efficiency > 0.0
        ):
            expected_shaft = hydraulic_power / (
                pump_efficiency / 100.0
            )
            add_issue(
                row,
                calculated_shaft is not None
                and math.isclose(
                    calculated_shaft,
                    expected_shaft,
                    rel_tol=1.0e-9,
                    abs_tol=1.0e-9,
                ),
                "PUMP_CALCULATED_SHAFT_POWER_FORMULA_INCONSISTENT",
                severity="CRITICAL",
            )
        if (
            shaft_power is not None
            and driver_efficiency is not None
            and driver_efficiency > 0.0
        ):
            expected_electrical = shaft_power / (
                driver_efficiency / 100.0
            )
            add_issue(
                row,
                calculated_electrical is not None
                and math.isclose(
                    calculated_electrical,
                    expected_electrical,
                    rel_tol=1.0e-9,
                    abs_tol=1.0e-9,
                ),
                "PUMP_CALCULATED_ELECTRICAL_POWER_FORMULA_INCONSISTENT",
                severity="CRITICAL",
            )
        expected_shaft_error = (
            abs(shaft_power - calculated_shaft)
            / max(
                abs(shaft_power),
                abs(calculated_shaft),
                1.0e-12,
            )
            if shaft_power is not None
            and calculated_shaft is not None
            else None
        )
        expected_electrical_error = (
            abs(electrical_power - calculated_electrical)
            / max(
                abs(electrical_power),
                abs(calculated_electrical),
                1.0e-12,
            )
            if electrical_power is not None
            and calculated_electrical is not None
            else None
        )
        add_issue(
            row,
            (
                shaft_error is None
                and expected_shaft_error is None
                or shaft_error is not None
                and expected_shaft_error is not None
                and numeric_equal(
                    shaft_error,
                    expected_shaft_error,
                )
            )
            and (
                electrical_error is None
                and expected_electrical_error is None
                or electrical_error is not None
                and expected_electrical_error is not None
                and numeric_equal(
                    electrical_error,
                    expected_electrical_error,
                )
            ),
            "PUMP_POWER_BALANCE_RELATIVE_ERROR_INCONSISTENT",
            severity="CRITICAL",
            context={
                "declared_shaft_error": shaft_error,
                "computed_shaft_error": expected_shaft_error,
                "declared_electrical_error": electrical_error,
                "computed_electrical_error": (
                    expected_electrical_error
                ),
            },
        )
        expected_errors = [
            value
            for value in (
                expected_shaft_error,
                expected_electrical_error,
            )
            if value is not None
        ]
        power_channels = {
            "hydraulic_power_kw": hydraulic_power,
            "shaft_power_kw": shaft_power,
            "electrical_power_kw": electrical_power,
            "pump_efficiency_percent": pump_efficiency,
            "driver_efficiency_percent": driver_efficiency,
        }
        expected_missing_channels = sorted(
            channel_name
            for channel_name, value in power_channels.items()
            if value is None
        )
        expected_both_balances_complete = (
            expected_shaft_error is not None
            and expected_electrical_error is not None
            and not expected_missing_channels
        )
        balance_tolerance = 0.005
        expected_power_status = (
            "PASS_ASPEN_POWER_CHANNELS_SEPARATED_AND_BALANCED"
            if expected_both_balances_complete
            and all(
                value <= balance_tolerance
                for value in expected_errors
            )
            else (
                "BLOCKED_PUMP_POWER_BALANCE_MISMATCH"
                if any(
                    value > balance_tolerance
                    for value in expected_errors
                )
                else "OPEN_INCOMPLETE_PUMP_POWER_CHANNELS"
            )
        )
        add_issue(
            row,
            power.get("status") == expected_power_status
            and power.get("required_balance_count") == 2
            and power.get("calculated_balance_count")
            == len(expected_errors)
            and power.get("both_balances_complete")
            is expected_both_balances_complete
            and power.get("missing_power_channels")
            == expected_missing_channels
            and numeric_equal(
                power.get("balance_relative_error_tolerance"),
                balance_tolerance,
            )
            and (
                "complete_Aspen_pump_power_channels_and_both_balances"
                in power.get("open_gates", [])
            )
            is (not expected_both_balances_complete),
            "PUMP_POWER_BALANCE_STATUS_INCONSISTENT",
            severity="CRITICAL",
            context={
                "expected": expected_power_status,
                "actual": power.get("status"),
                "expected_missing_power_channels": (
                    expected_missing_channels
                ),
            },
        )
        if expected_power_status == "BLOCKED_PUMP_POWER_BALANCE_MISMATCH":
            decision = (
                match.get("model_decision")
                if isinstance(match.get("model_decision"), dict)
                else {}
            )
            manifest = (
                decision.get("machine_evidence_manifest")
                if isinstance(
                    decision.get("machine_evidence_manifest"),
                    dict,
                )
                else {}
            )
            add_issue(
                row,
                "BLOCK" in str(manifest.get("status") or "").upper(),
                "PUMP_POWER_MISMATCH_NOT_PROPAGATED_TO_MODEL_GATE",
                severity="CRITICAL",
            )
        npsh = record.get("pump_npsha_process_audit")
        npsh = npsh if isinstance(npsh, dict) else {}
        add_issue(
            row,
            hash_without_key(npsh, "audit_sha256"),
            "PUMP_NPSH_AUDIT_HASH_INVALID",
        )
        npsha = finite_number(npsh.get("npsha_m"))
        upper = finite_number(
            npsh.get("absolute_suction_head_upper_bound_m")
        )
        if npsha is not None and npsha > 0.0:
            add_issue(
                row,
                upper is None or npsha <= upper * (1.0 + 1.0e-6),
                "PUMP_NPSHA_EXCEEDS_PHYSICAL_SUCTION_HEAD",
            )
        else:
            npsh_status = str(npsh.get("status") or "")
            formal_blockers = model.get("formal_promotion_blockers")
            formal_blockers = (
                formal_blockers if isinstance(formal_blockers, list) else []
            )
            execution = (
                model.get("selection_execution")
                if isinstance(model.get("selection_execution"), dict)
                else {}
            )
            expected_npsh_blocker = (
                f"pump_npsha_process_audit:{npsh_status}"
            )
            add_issue(
                row,
                npsh_status.startswith("BLOCKED_")
                and any(
                    str(blocker).startswith(expected_npsh_blocker)
                    for blocker in formal_blockers
                )
                and execution.get("formal_selection_executed") is False
                and str(execution.get("status") or "").startswith(
                    "TYPE_IDENTITY_ONLY"
                ),
                "NONPOSITIVE_NPSHA_NOT_PROPAGATED_TO_MODEL_GATE",
                context={
                    "npsh_status": npsh_status,
                    "expected_blocker_prefix": expected_npsh_blocker,
                    "formal_promotion_blockers": formal_blockers,
                    "selection_execution": execution,
                },
            )
        for entry in lineage_for(item, "npsha_pressure_kpa"):
            declared_export_unit = str(
                entry.get("hash_bound_export_raw_unit") or ""
            ).strip()
            if (
                declared_export_unit
                and normalised_text(declared_export_unit) != "kpa"
            ):
                add_issue(
                    row,
                    entry.get(
                        "legacy_export_unit_reinterpreted_as_kpa"
                    )
                    is True
                    and bool(entry.get("reinterpretation_basis"))
                    and bool(entry.get("production_action"))
                    and "legacy_export_unit_reinterpreted_as_kpa"
                    in normalised_text(entry.get("transform")),
                    "NPSHA_LEGACY_UNIT_REINTERPRETATION_NOT_EXPLICIT",
                    severity="CRITICAL",
                    context={
                        "hash_bound_export_raw_unit": (
                            declared_export_unit
                        ),
                        "source_path": entry.get("source_path"),
                    },
                )
        row["review_notes"].append(
            f"NPSHa status={npsh.get('status')}; NPSHa={npsha} m; "
            f"absolute suction-head bound={upper} m."
        )
    elif block_type in TOWER_BLOCK_TYPES:
        audit = item.get("tower_preliminary_design_audit")
        audit = audit if isinstance(audit, dict) else {}
        add_issue(
            row,
            hash_without_key(audit, "audit_sha256"),
            "TOWER_AUDIT_HASH_INVALID",
        )
        diameter = audit.get("diameter_screening", {})
        mechanical = audit.get("mechanical_thickness_screening", {})
        add_issue(
            row,
            audit.get("status")
            == "TYPE_SELECTED_HYDRAULIC_SIZING_BLOCKED"
            and audit.get("formal_ready") is False
            and same_text(
                audit.get("recommended_type"),
                row["recommended_type"],
            )
            and concrete_text(audit.get("recommended_type")),
            "TOWER_TYPE_OR_GATE_INVALID",
        )
        add_issue(
            row,
            finite_number(diameter.get("value_mm")) is not None
            and diameter.get("controlling_tray_section_selected") is False
            and diameter.get("flooding_capacity_verified") is False,
            "TOWER_DIAMETER_SCREEN_NOT_EXPLICIT_OR_MISSING",
        )
        add_issue(
            row,
            mechanical.get("nominal_shell_thickness_selected") is False
            and mechanical.get("nominal_head_thickness_selected") is False,
            "TOWER_FORMULA_THICKNESS_MISREPRESENTED_AS_NOMINAL",
        )
        derived = (
            match.get("derived_parameters")
            if isinstance(match.get("derived_parameters"), dict)
            else {}
        )
        add_issue(
            row,
            "inner_diameter_mm" not in derived
            and "height_mm" not in derived,
            "TOWER_GENERIC_GEOMETRY_LEAKED_TO_DERIVED_PARAMETERS",
            severity="CRITICAL",
        )
        decision = (
            match.get("model_decision")
            if isinstance(match.get("model_decision"), dict)
            else {}
        )
        public_geometry_leaks = sorted(set([
            *public_key_paths(
                model,
                target_keys={"inner_diameter_mm", "height_mm"},
                path="$.model_recommendation",
            ),
            *public_key_paths(
                decision,
                target_keys={"inner_diameter_mm", "height_mm"},
                path="$.model_decision",
            ),
        ]))
        add_issue(
            row,
            not public_geometry_leaks,
            "TOWER_GENERIC_GEOMETRY_LEAKED_TO_PUBLIC_MODEL_SURFACE",
            severity="CRITICAL",
            context={"paths": public_geometry_leaks},
        )
        binding = item.get("program_generated_record_binding")
        binding = binding if isinstance(binding, dict) else {}
        final_projection = binding.get("final_type_projection")
        final_projection = (
            final_projection
            if isinstance(final_projection, dict)
            else {}
        )
        public_identity_texts = [
            str(candidate.get("designation") or "")
            for candidate in model.get("candidates", [])
            if isinstance(candidate, dict)
            and not str(candidate.get("status") or "").startswith(
                "REJECTED_"
            )
        ]
        public_identity_texts.extend([
            str(leading.get("designation") or ""),
            str(decision.get("candidate_model") or ""),
            str(decision.get("generated_candidate_designation") or ""),
            str(final_projection.get("leading_candidate_designation") or ""),
            str(final_projection.get("generated_candidate_designation") or ""),
            str(final_projection.get("candidate_model") or ""),
        ])
        forbidden_screen_tokens = (
            "Di_screen=",
            "H_layout_screen=",
            "shell_formula_t=",
        )
        public_identity_leaks = sorted({
            token
            for token in forbidden_screen_tokens
            if any(token in text for text in public_identity_texts)
        })
        add_issue(
            row,
            not public_identity_leaks,
            "TOWER_SCREENING_NUMBERS_LEAKED_TO_PUBLIC_IDENTITY",
            severity="CRITICAL",
            context={"tokens": public_identity_leaks},
        )
        quarantined = derived.get(
            "pre_boundary_generic_tower_geometry"
        )
        if isinstance(quarantined, dict) and quarantined:
            add_issue(
                row,
                quarantined.get("role")
                == "SUPERSEDED_BY_EXPLICIT_SCREENING_FIELDS"
                and quarantined.get(
                    "not_for_customer_or_formal_use"
                )
                is True,
                "TOWER_PREBOUNDARY_GENERIC_GEOMETRY_NOT_QUARANTINED",
                severity="CRITICAL",
            )
        candidates = [
            candidate
            for candidate in model.get("candidates", [])
            if isinstance(candidate, dict)
            and not str(candidate.get("status") or "").startswith(
                "REJECTED_"
            )
        ]
        if leading:
            candidates.append(leading)
        leaking_candidate_ids: list[str] = []
        for candidate in candidates:
            candidate_specification = candidate.get("specification")
            candidate_specification = (
                candidate_specification
                if isinstance(candidate_specification, dict)
                else {}
            )
            if any(
                field_id in candidate_specification
                for field_id in ("inner_diameter_mm", "height_mm")
            ):
                leaking_candidate_ids.append(
                    str(candidate.get("candidate_id") or "<unnamed>")
                )
        add_issue(
            row,
            not leaking_candidate_ids,
            "TOWER_GENERIC_GEOMETRY_LEAKED_TO_MODEL_SPECIFICATION",
            severity="CRITICAL",
            context={"candidate_ids": leaking_candidate_ids},
        )
        leading_missing_gates = leading.get("missing_gates")
        leading_missing_gates = (
            leading_missing_gates
            if isinstance(leading_missing_gates, list)
            else []
        )
        formal_open_gates = audit.get("formal_open_gates")
        formal_open_gates = (
            formal_open_gates
            if isinstance(formal_open_gates, list)
            else []
        )
        execution = (
            model.get("selection_execution")
            if isinstance(model.get("selection_execution"), dict)
            else {}
        )
        add_issue(
            row,
            leading.get("eligible_for_formal_selection") is False
            and leading.get("formal_model") is False
            and str(leading.get("candidate_eligibility") or "").startswith(
                "TYPE_IDENTITY_ONLY_"
            )
            and execution.get("formal_selection_executed") is False
            and set(formal_open_gates).issubset(
                set(leading_missing_gates)
            ),
            "TOWER_CUSTOMER_MISSING_FALSE_PASS_BOUNDARY",
            severity="CRITICAL",
        )
        leading_designation = str(leading.get("designation") or "")
        add_issue(
            row,
            "N_stage_Aspen=" in leading_designation
            and "Di_formal=OPEN" in leading_designation
            and "H_formal=OPEN" in leading_designation
            and "Di_screen=" not in leading_designation
            and "H_layout_screen=" not in leading_designation
            and "shell_formula_t=" not in leading_designation
            and " | Di=" not in leading_designation
            and "H_body=" not in leading_designation,
            "TOWER_DESIGNATION_GENERIC_GEOMETRY_LEAK",
            severity="CRITICAL",
        )
        row["review_notes"].append(
            f"Tower diameter screen={diameter.get('value_mm')} mm "
            f"({diameter.get('basis')}); formal tray hydraulics remain open."
        )
    elif block_type == "RPLUG":
        audit = item.get("rplug_preliminary_design_audit")
        audit = audit if isinstance(audit, dict) else {}
        geometry = audit.get("geometry_screening", {})
        add_issue(
            row,
            hash_without_key(audit, "audit_sha256"),
            "RPLUG_AUDIT_HASH_INVALID",
        )
        add_issue(
            row,
            audit.get("status")
            in {
                "TYPE_SELECTED_REACTOR_SIZING_BLOCKED",
                "RPLUG_TYPE_SELECTED_REACTOR_SIZING_BLOCKED",
            }
            and audit.get("formal_ready") is False
            and not audit.get("port_mapping_issues"),
            "RPLUG_PORT_OR_GATE_INVALID",
        )
        add_issue(
            row,
            finite_number(
                geometry.get("active_tube_inner_diameter_mm")
            )
            is not None
            and geometry.get("required_total_reactor_volume_m3") is None
            and geometry.get("selected_tube_count") is None
            and geometry.get("reactor_shell_inner_diameter_mm") is None,
            "RPLUG_ACTIVE_TUBE_MISREPRESENTED_AS_WHOLE_REACTOR",
        )
        row["review_notes"].append(
            "Aspen DIAMETER is retained as one active tube; total volume, "
            "tube count and shell diameter remain open."
        )
    elif block_type in {"HEATER", "HEATX"}:
        audit = item.get("heat_transfer_service_classification")
        audit = audit if isinstance(audit, dict) else {}
        add_issue(
            row,
            hash_without_key(audit, "classification_sha256"),
            "HEAT_TRANSFER_SERVICE_CLASSIFICATION_HASH_INVALID",
        )
        add_issue(
            row,
            audit.get("status")
            == "PRELIMINARY_PHASE_SERVICE_TYPE_SELECTED"
            and audit.get("formal_ready") is False
            and audit.get("recommended_type")
            == row["recommended_type"],
            "HEAT_TRANSFER_PHASE_SERVICE_OR_GATE_INVALID",
        )
        if block_type == "HEATER":
            pressure_screen = audit.get("pressure_drop_screening")
            pressure_screen = (
                pressure_screen
                if isinstance(pressure_screen, dict)
                else {}
            )
            inlet_pressure = finite_number(
                record.get("inlet_pressure_mpa")
            )
            outlet_pressure = finite_number(
                record.get("outlet_pressure_mpa")
            )
            pressure_basis = str(record.get("pressure_basis") or "")
            atmospheric = finite_number(
                record.get("atmospheric_pressure_mpa")
            )
            if atmospheric is None:
                atmospheric = 0.101325
            inlet_absolute = inlet_pressure
            if (
                inlet_absolute is not None
                and pressure_basis.casefold() == "gauge"
            ):
                inlet_absolute += atmospheric
            expected_drop = (
                (inlet_pressure - outlet_pressure) * 1000.0
                if inlet_pressure is not None
                and outlet_pressure is not None
                else None
            )
            expected_ratio = (
                expected_drop / (inlet_absolute * 1000.0)
                if expected_drop is not None
                and inlet_absolute is not None
                and inlet_absolute > 0.0
                else None
            )
            if expected_drop is None or expected_ratio is None:
                expected_status = (
                    "OPEN_MISSING_HEATER_ENDPOINT_PRESSURE"
                )
                expected_review = True
                expected_conflict = False
            elif expected_drop < -1.0e-6:
                expected_status = (
                    "BLOCKED_HEATER_PRESSURE_RISE_REQUIRES_"
                    "SEPARATE_DEVICE"
                )
                expected_review = True
                expected_conflict = True
            elif expected_ratio >= 0.30:
                expected_status = (
                    "BLOCKED_HEAT_TRANSFER_PRESSURE_DROP_"
                    "FUNCTION_CONFLICT"
                )
                expected_review = True
                expected_conflict = True
            elif expected_ratio >= 0.10:
                expected_status = (
                    "REVIEW_HIGH_RELATIVE_HEATER_PRESSURE_DROP"
                )
                expected_review = True
                expected_conflict = False
            else:
                expected_status = (
                    "PASS_PROJECT_PRE_SCREEN_BELOW_REVIEW_THRESHOLD"
                )
                expected_review = False
                expected_conflict = False
            actual_drop = finite_number(
                pressure_screen.get("pressure_drop_kpa")
            )
            actual_ratio = finite_number(
                pressure_screen.get("ratio_to_inlet_absolute")
            )
            add_issue(
                row,
                bool(pressure_screen)
                and (
                    expected_drop is None
                    and actual_drop is None
                    or expected_drop is not None
                    and actual_drop is not None
                    and math.isclose(
                        actual_drop,
                        expected_drop,
                        rel_tol=1.0e-9,
                        abs_tol=1.0e-9,
                    )
                )
                and (
                    expected_ratio is None
                    and actual_ratio is None
                    or expected_ratio is not None
                    and actual_ratio is not None
                    and math.isclose(
                        actual_ratio,
                        expected_ratio,
                        rel_tol=1.0e-9,
                        abs_tol=1.0e-9,
                    )
                ),
                "HEATER_PRESSURE_DROP_SCREEN_MISSING_OR_NUMERICALLY_WRONG",
                severity="CRITICAL",
            )
            add_issue(
                row,
                (
                    inlet_pressure is None
                    and pressure_screen.get("inlet_pressure_mpa") is None
                    or inlet_pressure is not None
                    and numeric_equal(
                        pressure_screen.get("inlet_pressure_mpa"),
                        inlet_pressure,
                    )
                )
                and (
                    outlet_pressure is None
                    and pressure_screen.get("outlet_pressure_mpa") is None
                    or outlet_pressure is not None
                    and numeric_equal(
                        pressure_screen.get("outlet_pressure_mpa"),
                        outlet_pressure,
                    )
                )
                and (
                    inlet_absolute is None
                    and pressure_screen.get(
                        "inlet_pressure_mpa_absolute"
                    )
                    is None
                    or inlet_absolute is not None
                    and numeric_equal(
                        pressure_screen.get(
                            "inlet_pressure_mpa_absolute"
                        ),
                        inlet_absolute,
                    )
                )
                and str(pressure_screen.get("pressure_basis") or "")
                == pressure_basis
                and numeric_equal(
                    pressure_screen.get("review_ratio_threshold"),
                    0.10,
                )
                and numeric_equal(
                    pressure_screen.get(
                        "function_conflict_ratio_threshold"
                    ),
                    0.30,
                )
                and pressure_screen.get("threshold_role")
                == "PROJECT_PRE_SCREEN_NOT_NATIONAL_CODE_ALLOWABLE_LIMIT",
                "HEATER_PRESSURE_DROP_THRESHOLD_OR_BASIS_INVALID",
                severity="CRITICAL",
            )
            formal_open_gates = audit.get("formal_open_gates")
            formal_open_gates = (
                formal_open_gates
                if isinstance(formal_open_gates, list)
                else []
            )
            add_issue(
                row,
                pressure_screen.get("status") == expected_status
                and pressure_screen.get("review_required")
                is expected_review
                and pressure_screen.get("function_conflict")
                is expected_conflict
                and pressure_screen.get(
                    "formal_allowable_confirmed"
                )
                is False
                and (
                    not expected_review
                    or "heater_allowable_process_pressure_drop"
                    in formal_open_gates
                )
                and (
                    not expected_conflict
                    or {
                        (
                            "dedicated_pressure_reduction_device_or_"
                            "process_data_correction"
                        ),
                        (
                            "heat_transfer_and_pressure_reduction_"
                            "function_allocation_review"
                        ),
                    }.issubset(set(formal_open_gates))
                ),
                "HEATER_HIGH_PRESSURE_DROP_NOT_GATED",
                severity="CRITICAL",
                context={
                    "expected_status": expected_status,
                    "actual_status": pressure_screen.get("status"),
                    "ratio": expected_ratio,
                },
            )
            if expected_conflict:
                execution = (
                    model.get("selection_execution")
                    if isinstance(
                        model.get("selection_execution"),
                        dict,
                    )
                    else {}
                )
                add_issue(
                    row,
                    execution.get("formal_selection_executed") is False
                    and "TYPE_IDENTITY_ONLY_" in str(
                        execution.get("status") or ""
                    ),
                    (
                        "HEATER_PRESSURE_DROP_FUNCTION_CONFLICT_NOT_"
                        "PROPAGATED"
                    ),
                    severity="CRITICAL",
                )
        row["review_notes"].append(
            f"Phase service={audit.get('selector_rule_id')}; thermal rating, "
            "arrangement, F-factor and mechanical design remain open."
        )
    elif block_type == "VALVE":
        specification = valve_specification or {}
        row["program_specification_hash_valid"] = (
            program_specification_hash_valid(specification)
        )
        pressure_audit = specification.get(
            "maximum_pressure_drop_screening_audit"
        )
        pressure_audit = (
            pressure_audit if isinstance(pressure_audit, dict) else {}
        )
        requested = finite_number(pressure_audit.get("requested_value_kpa"))
        applied = finite_number(pressure_audit.get("applied_value_kpa"))
        cap = finite_number(pressure_audit.get("physical_upper_bound_kpa"))
        add_issue(
            row,
            specification.get("status")
            == "PRELIMINARY_CONCRETE_SPECIFICATION_SELECTED"
            and row["program_specification_hash_valid"],
            "VALVE_PROGRAM_SPECIFICATION_OR_HASH_INVALID",
        )
        add_issue(
            row,
            applied is not None
            and cap is not None
            and applied <= cap + 1.0e-9
            and pressure_audit.get(
                "formal_shutoff_differential_selected"
            )
            is False,
            "VALVE_MAXIMUM_DP_PHYSICAL_CAP_INVALID",
        )
        add_issue(
            row,
            requested is None
            or applied is None
            or applied <= requested + 1.0e-9,
            "VALVE_APPLIED_DP_EXCEEDS_REQUEST",
        )
        row["review_notes"].append(
            f"Valve screening dP requested={requested} kPa, "
            f"applied={applied} kPa, absolute-zero cap={cap} kPa."
        )
    if row["issues"]:
        row["status"] = "FAIL"
    return row


def audit_case(
    case_name: str,
    path: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    source_export_sha256 = str(
        document.get("source_export_sha256") or ""
    ).upper()
    source_path = Path(str(document.get("source_export_path") or ""))
    case_issues: list[str] = []
    case_issue_details: list[dict[str, Any]] = []

    def add_case_issue(
        condition: bool,
        code: str,
        *,
        severity: str = "CRITICAL",
        context: dict[str, Any] | None = None,
    ) -> None:
        if condition:
            return
        case_issues.append(code)
        case_issue_details.append({
            "code": code,
            "severity": severity,
            "context": context or {},
        })

    add_case_issue(
        source_path.is_file(),
        "SOURCE_EXPORT_FILE_MISSING",
    )
    if source_path.is_file():
        add_case_issue(
            sha256_file(source_path) == source_export_sha256,
            "SOURCE_EXPORT_HASH_MISMATCH",
        )
    run_gate = document.get("aspen_run_gate")
    run_gate = run_gate if isinstance(run_gate, dict) else {}
    add_case_issue(
        hash_without_key(run_gate, "run_gate_sha256"),
        "ASPEN_RUN_GATE_HASH_INVALID",
    )
    run_status_evidence = (
        run_gate.get("run_status_evidence")
        if isinstance(run_gate.get("run_status_evidence"), dict)
        else {}
    )
    run_status_path = Path(
        str(run_status_evidence.get("path") or "")
    )
    add_case_issue(
        run_status_path.is_file()
        and sha256_file(run_status_path)
        == str(run_status_evidence.get("sha256") or "").upper(),
        "ASPEN_RUN_STATUS_EVIDENCE_FILE_OR_HASH_INVALID",
    )
    attribution = run_gate.get("raw_history_attribution")
    attribution = attribution if isinstance(attribution, dict) else {}
    add_case_issue(
        bool(attribution)
        and hash_without_key(attribution, "attribution_sha256"),
        "RAW_HISTORY_ATTRIBUTION_MISSING_OR_HASH_INVALID",
    )
    raw_history_path = Path(
        str(attribution.get("raw_history_path") or "")
    )
    add_case_issue(
        raw_history_path.is_file()
        and sha256_file(raw_history_path)
        == str(attribution.get("raw_history_sha256") or "").upper(),
        "RAW_ASPEN_HISTORY_FILE_OR_HASH_INVALID",
    )
    raw_events = attribution.get("events")
    raw_events = raw_events if isinstance(raw_events, list) else []
    event_records = [
        event for event in raw_events if isinstance(event, dict)
    ]
    add_case_issue(
        len(event_records) == len(raw_events)
        and all(
            hash_without_key(event, "event_sha256")
            for event in event_records
        ),
        "RAW_HISTORY_EVENT_HASH_INVALID",
    )
    event_sha256s = [
        str(event.get("event_sha256") or "").upper()
        for event in event_records
    ]
    event_indices = [event.get("event_index") for event in event_records]
    add_case_issue(
        len(event_sha256s) == len(set(event_sha256s))
        and all(
            len(value) == HASH_PATTERN_LENGTH for value in event_sha256s
        )
        and len(event_indices) == len(set(event_indices)),
        "RAW_HISTORY_EVENT_IDENTITY_NOT_UNIQUE",
    )
    declared_event_count = finite_number(attribution.get("event_count"))
    add_case_issue(
        declared_event_count is not None
        and declared_event_count == int(declared_event_count)
        and int(declared_event_count) == len(event_records),
        "RAW_HISTORY_EVENT_COUNT_FIELD_MISMATCH",
        context={
            "declared_event_count": attribution.get("event_count"),
            "recomputed_event_count": len(event_records),
        },
    )
    add_case_issue(
        all(
            hash_without_key(issue, "issue_sha256")
            for issue in attribution.get("block_issues", [])
            if isinstance(issue, dict)
        ),
        "RAW_HISTORY_BLOCK_ISSUE_HASH_INVALID",
    )
    run_counts = (
        run_gate.get("counts")
        if isinstance(run_gate.get("counts"), dict)
        else {}
    )
    reported_counts = (
        attribution.get("reported_counts")
        if isinstance(attribution.get("reported_counts"), dict)
        else {}
    )
    attributed_counts = (
        attribution.get("attributed_counts")
        if isinstance(attribution.get("attributed_counts"), dict)
        else {}
    )
    severity_count_keys = (
        "warnings",
        "errors",
        "severe_errors",
        "terminal_errors",
    )
    recomputed_attributed_counts = {
        key: 0 for key in severity_count_keys
    }
    unrecognised_event_severities: list[str] = []
    for event in event_records:
        event_severity = str(event.get("severity") or "").casefold()
        if event_severity in recomputed_attributed_counts:
            recomputed_attributed_counts[event_severity] += 1
        else:
            unrecognised_event_severities.append(event_severity)
    add_case_issue(
        not unrecognised_event_severities
        and recomputed_attributed_counts == attributed_counts,
        "ASPEN_RAW_HISTORY_EVENT_SEVERITY_COUNTS_INVALID",
        context={
            "recomputed_attributed_counts": recomputed_attributed_counts,
            "declared_attributed_counts": attributed_counts,
            "unrecognised_event_severities": (
                unrecognised_event_severities
            ),
        },
    )
    add_case_issue(
        run_counts == reported_counts == attributed_counts
        and attribution.get("count_reconciliation_status") == "EXACT",
        "ASPEN_RAW_HISTORY_COUNT_RECONCILIATION_INVALID",
        context={
            "run_counts": run_counts,
            "reported_counts": reported_counts,
            "attributed_counts": attributed_counts,
            "unattributed_counts": attribution.get(
                "unattributed_counts"
            ),
            "count_reconciliation_status": attribution.get(
                "count_reconciliation_status"
            ),
        },
    )
    computed_aspen_highest = highest_aspen_severity(run_counts)
    for block_issue in attribution.get("block_issues", []):
        if not isinstance(block_issue, dict):
            continue
        computed_block_highest = highest_aspen_severity(
            block_issue.get("counts")
        )
        add_case_issue(
            block_issue.get("highest_severity")
            == computed_block_highest,
            "ASPEN_BLOCK_HIGHEST_SEVERITY_MISMATCH",
            context={
                "block_id": block_issue.get("block_id"),
                "computed": computed_block_highest,
                "declared": block_issue.get("highest_severity"),
            },
        )
    viscosity_summary = document.get("viscosity_fallback_summary")
    viscosity_summary = (
        viscosity_summary
        if isinstance(viscosity_summary, dict)
        else {}
    )
    viscosity_diagnostics = [
        diagnostic
        for diagnostic in viscosity_summary.get("diagnostics", [])
        if isinstance(diagnostic, dict)
    ]
    internal_viscosity_diagnostics = [
        diagnostic
        for diagnostic in viscosity_diagnostics
        if diagnostic.get("internal_correlation_used") is True
    ]
    aspen_or_not_needed_count = sum(
        str(diagnostic.get("status") or "").startswith(
            ("NOT_NEEDED_", "ASPEN_PHASE_SPECIFIC_")
        )
        for diagnostic in viscosity_diagnostics
    )
    blocked_viscosity_count = sum(
        diagnostic.get("status") == "BLOCKED"
        or str(diagnostic.get("status") or "").startswith("BLOCKED_")
        for diagnostic in viscosity_diagnostics
    )
    add_case_issue(
        viscosity_summary.get("schema")
        == "viscosity-fallback-summary-v1"
        and viscosity_summary.get("authority_order")
        == [
            "exported_mixture_MUMX",
            "exported_phase_specific_MUMX_for_unambiguous_single_phase",
            "source_bound_internal_correlation",
            "blocked_without_default",
        ]
        and viscosity_summary.get("stream_count")
        == len(viscosity_diagnostics)
        and viscosity_summary.get("internal_correlation_used_count")
        == len(internal_viscosity_diagnostics)
        and viscosity_summary.get("aspen_or_not_needed_count")
        == aspen_or_not_needed_count
        and viscosity_summary.get("blocked_count")
        == blocked_viscosity_count
        and viscosity_summary.get("formal_design_evidence") is False
        and viscosity_summary.get("correlation_promotion_cap")
        == "TYPE_SCREENING"
        and bool(
            str(viscosity_summary.get("mandatory_warning") or "").strip()
        ),
        "VISCOSITY_FALLBACK_SUMMARY_COUNTS_OR_BOUNDARY_INVALID",
    )
    add_case_issue(
        all(
            hash_without_key(diagnostic, "diagnostic_sha256")
            and str(
                diagnostic.get("source_export_sha256") or ""
            ).upper()
            == source_export_sha256
            for diagnostic in viscosity_diagnostics
        ),
        "VISCOSITY_FALLBACK_DIAGNOSTIC_HASH_OR_SOURCE_INVALID",
    )
    mandatory_internal_viscosity_warnings = {
        "W_VISCOSITY_INTERNAL_CORRELATION_ESTIMATE",
        "W_VISCOSITY_NOT_ASPEN_EXTRACTED",
        "W_VISCOSITY_PRELIMINARY_HYDRAULICS_ONLY",
        "W_CORRELATION_SOURCE_ASSET_HASH_NOT_LOCALLY_VERIFIED",
    }
    add_case_issue(
        all(
            diagnostic.get("status") == "PASS_WITH_WARNING"
            and diagnostic.get("origin")
            == "INTERNAL_CORRELATION_ESTIMATE"
            and diagnostic.get("evidence_class") == "J"
            and diagnostic.get("formal_design_evidence") is False
            and diagnostic.get("promotion_cap") == "TYPE_SCREENING"
            and mandatory_internal_viscosity_warnings.issubset({
                str(code)
                for code in diagnostic.get("warning_codes", [])
            })
            and bool(str(diagnostic.get("claim_boundary") or "").strip())
            for diagnostic in internal_viscosity_diagnostics
        ),
        "INTERNAL_VISCOSITY_WARNING_OR_PROMOTION_BOUNDARY_INVALID",
    )
    formal_use_blockers = document.get("formal_use_blockers")
    formal_use_blockers = (
        formal_use_blockers
        if isinstance(formal_use_blockers, list)
        else []
    )
    internal_viscosity_blockers = {
        (
            str(blocker.get("stream_id") or ""),
            str(blocker.get("diagnostic_sha256") or "").upper(),
        )
        for blocker in formal_use_blockers
        if isinstance(blocker, dict)
        and blocker.get("code")
        == "INTERNAL_VISCOSITY_CORRELATION_PRELIMINARY_ONLY"
        and blocker.get("promotion_cap") == "TYPE_SCREENING"
        and bool(blocker.get("warning_codes"))
    }
    expected_internal_viscosity_blockers = {
        (
            str(diagnostic.get("stream_id") or ""),
            str(diagnostic.get("diagnostic_sha256") or "").upper(),
        )
        for diagnostic in internal_viscosity_diagnostics
    }
    add_case_issue(
        internal_viscosity_blockers
        == expected_internal_viscosity_blockers
        and (
            not internal_viscosity_diagnostics
            or document.get("formal_use_gate")
            == "PROVISIONAL_NOT_FORMAL_PROCESS_BASIS"
        ),
        "INTERNAL_VISCOSITY_NOT_PROPAGATED_TO_FORMAL_USE_GATE",
    )
    rows: list[dict[str, Any]] = []
    for item in document.get("equipment", []):
        if isinstance(item, dict):
            rows.append(
                audit_equipment_record(
                    case_name=case_name,
                    item=item,
                    source_export_sha256=source_export_sha256,
                )
            )
    for item in document.get("piping", []):
        if not isinstance(item, dict):
            continue
        rows.append(
            audit_pipe_record(
                case_name=case_name,
                record_kind="piping",
                identity=str(item.get("stream_id") or ""),
                item=item,
                source_export_sha256=source_export_sha256,
            )
        )
    piping_items = [
        item
        for item in document.get("piping", [])
        if isinstance(item, dict)
    ]
    alias_items = [
        item
        for item in document.get("piping_state_aliases", [])
        if isinstance(item, dict)
    ]
    physical_pipe_items = [
        item
        for item in document.get("equipment", [])
        if isinstance(item, dict)
        and item.get("pipe_entity_scope")
        == "ASPEN_PHYSICAL_PIPE_BLOCK"
        and item.get("counted_as_physical_pipe") is True
    ]
    counted_pipe_items = [*physical_pipe_items, *piping_items]
    counted_pipe_entity_ids = [
        str(item.get("pipe_entity_id") or "")
        for item in counted_pipe_items
        if str(item.get("pipe_entity_id") or "")
    ]
    canonical_pipe_entity_ids = sorted(set(counted_pipe_entity_ids))
    add_case_issue(
        len(counted_pipe_entity_ids)
        == len(canonical_pipe_entity_ids)
        == len(counted_pipe_items),
        "COUNTED_PHYSICAL_PIPE_ENTITY_ID_DUPLICATE_OR_MISSING",
        context={
            "counted_pipe_entity_ids": counted_pipe_entity_ids,
            "counted_item_count": len(counted_pipe_items),
        },
    )
    physical_pipe_entity_id_set = {
        str(item.get("pipe_entity_id") or "")
        for item in physical_pipe_items
        if str(item.get("pipe_entity_id") or "")
    }
    piping_stream_ids = {
        str(item.get("stream_id") or "")
        for item in piping_items
        if str(item.get("stream_id") or "")
    }
    alias_reconciliation_rows: list[dict[str, Any]] = []
    for alias in alias_items:
        stream_id = str(alias.get("stream_id") or "")
        alias_entity_id = str(alias.get("pipe_entity_id") or "")
        alias_canonical_ids = alias.get("canonical_pipe_entity_ids")
        alias_canonical_ids = (
            [
                str(entity_id)
                for entity_id in alias_canonical_ids
                if str(entity_id)
            ]
            if isinstance(alias_canonical_ids, list)
            else []
        )
        expected_alias_id = (
            alias_canonical_ids[0]
            if len(alias_canonical_ids) == 1
            else f"PFD_ENDPOINT_STATE:{stream_id}"
        )
        endpoint_audit = alias.get("endpoint_pressure_drop_audit")
        endpoint_audit = (
            endpoint_audit
            if isinstance(endpoint_audit, dict)
            else {}
        )
        alias_gate = alias.get("aspen_run_gate")
        alias_gate = alias_gate if isinstance(alias_gate, dict) else {}
        gate_hash_valid, gate_identity_valid = (
            row_gate_hash_and_identity_valid(
                gate=alias_gate,
                record_kind="piping",
                identity=stream_id,
            )
        )
        alias_boundary = alias.get("evidence_boundary")
        alias_boundary = (
            alias_boundary
            if isinstance(alias_boundary, dict)
            else {}
        )
        alias_case = (
            alias_gate.get("case")
            if isinstance(alias_gate.get("case"), dict)
            else {}
        )
        alias_case_dirty = (
            str(alias_case.get("status") or "") != "CLEAN_RUN"
        )
        alias_binding_valid, alias_binding_context = (
            program_generated_record_binding_valid(
                item=alias,
                record_kind="pfd_endpoint_state_alias",
                identity=stream_id,
                source_export_sha256=source_export_sha256,
            )
        )
        add_case_issue(
            alias_binding_valid,
            "PROGRAM_GENERATED_PFD_ALIAS_ROW_BINDING_INVALID",
            context=alias_binding_context,
        )
        add_case_issue(
            bool(stream_id)
            and stream_id not in piping_stream_ids
            and alias.get("pipe_entity_scope")
            == "ASPEN_PIPE_ENDPOINT_STATE"
            and alias.get("pipe_entity_role") == "ENDPOINT_STATE_ALIAS"
            and alias.get("counted_as_physical_pipe") is False
            and alias.get("alias_only") is True
            and bool(alias_canonical_ids)
            and set(alias_canonical_ids).issubset(
                physical_pipe_entity_id_set
            )
            and alias_entity_id == expected_alias_id,
            "PFD_PIPE_ENDPOINT_STATE_ALIAS_IDENTITY_OR_COUNTING_INVALID",
            context={
                "stream_id": stream_id,
                "pipe_entity_id": alias_entity_id,
                "canonical_pipe_entity_ids": alias_canonical_ids,
            },
        )
        add_case_issue(
            bool(endpoint_audit)
            and hash_without_key(endpoint_audit, "audit_sha256")
            and endpoint_audit.get("schema")
            == "pipe-endpoint-pressure-drop-audit-v1"
            and endpoint_audit.get("status")
            == "NOT_APPLICABLE_ENDPOINT_STATE_ALIAS"
            and endpoint_audit.get("pipe_entity_scope")
            == "ASPEN_PIPE_ENDPOINT_STATE"
            and endpoint_audit.get("pipe_entity_id")
            == alias_entity_id
            and endpoint_audit.get("endpoint_pressure_drop_kpa") is None
            and endpoint_audit.get("endpoint_complete") is False
            and endpoint_audit.get("formal_acceptance") is False
            and endpoint_audit.get("formal_ready") is False
            and endpoint_audit.get("open_gates") == []
            and str(
                endpoint_audit.get("source_export_sha256") or ""
            ).upper()
            == source_export_sha256,
            "PFD_PIPE_ENDPOINT_STATE_ALIAS_PRESSURE_AUDIT_INVALID",
            context={"stream_id": stream_id},
        )
        add_case_issue(
            gate_hash_valid
            and gate_identity_valid
            and str(
                alias_case.get("run_gate_sha256") or ""
            ).upper()
            == str(run_gate.get("run_gate_sha256") or "").upper()
            and str(
                alias_boundary.get("aspen_row_gate_sha256") or ""
            ).upper()
            == str(alias_gate.get("row_gate_sha256") or "").upper()
            and (
                alias_boundary.get(
                    "affects_aspen_formal_use_gate"
                )
                is True
                and alias_gate.get(
                    "process_values_formally_releasable"
                )
                is False
                if alias_case_dirty
                else alias_boundary.get(
                    "affects_aspen_formal_use_gate"
                )
                is False
                and alias_gate.get(
                    "process_values_formally_releasable"
                )
                is True
            ),
            "PFD_PIPE_ENDPOINT_STATE_ALIAS_ROW_GATE_INVALID",
            context={"stream_id": stream_id},
        )
        alias_reconciliation_rows.append({
            "stream_id": stream_id,
            "pipe_entity_id": alias_entity_id,
            "canonical_pipe_entity_ids": alias_canonical_ids,
            "endpoint_pressure_drop_audit_sha256": (
                endpoint_audit.get("audit_sha256")
            ),
        })
    binding_rows: list[tuple[str, str, dict[str, Any]]] = []
    for equipment_item in document.get("equipment", []):
        if not isinstance(equipment_item, dict):
            continue
        equipment_match = (
            equipment_item.get("match_result")
            if isinstance(equipment_item.get("match_result"), dict)
            else {}
        )
        equipment_record = (
            equipment_item.get("canonical_match_input")
            if isinstance(
                equipment_item.get("canonical_match_input"),
                dict,
            )
            else {}
        )
        if (
            equipment_item.get("aspen_mapping_status")
            == "NOT_APPLICABLE_SIMULATION_LOGIC_NODE"
            or equipment_match.get("status") == "NOT_APPLICABLE"
        ):
            binding_record_kind = "logic_node"
        elif str(
            equipment_record.get("aspen_block_type") or ""
        ).upper() == "PIPE":
            binding_record_kind = "physical_pipe_block"
        else:
            binding_record_kind = "equipment"
        binding_rows.append((
            binding_record_kind,
            str(
                equipment_item.get("aspen_block_id")
                or equipment_item.get("equipment_tag")
                or ""
            ),
            equipment_item,
        ))
    binding_rows.extend(
        (
            "piping",
            str(piping_item.get("stream_id") or ""),
            piping_item,
        )
        for piping_item in piping_items
    )
    binding_rows.extend(
        (
            "pfd_endpoint_state_alias",
            str(alias_item.get("stream_id") or ""),
            alias_item,
        )
        for alias_item in alias_items
    )
    expected_binding_summary_rows: list[dict[str, Any]] = []
    expected_lineage_summary_rows: list[dict[str, Any]] = []
    all_binding_contracts_valid = True
    all_binding_contexts: list[dict[str, Any]] = []
    for binding_record_kind, binding_identity, binding_item in binding_rows:
        binding_valid, binding_context = (
            program_generated_record_binding_valid(
                item=binding_item,
                record_kind=binding_record_kind,
                identity=binding_identity,
                source_export_sha256=source_export_sha256,
            )
        )
        all_binding_contracts_valid = (
            all_binding_contracts_valid and binding_valid
        )
        if not binding_valid:
            all_binding_contexts.append(binding_context)
        binding = binding_item.get("program_generated_record_binding")
        binding = binding if isinstance(binding, dict) else {}
        add_case_issue(
            binding.get("engine_version") == document.get("engine_version"),
            "PROGRAM_GENERATED_ROW_BINDING_ENGINE_VERSION_MISMATCH",
            context={
                "record_kind": binding_record_kind,
                "identity": binding_identity,
                "binding_engine_version": binding.get("engine_version"),
                "document_engine_version": document.get("engine_version"),
            },
        )
        expected_binding_summary_rows.append({
            "record_kind": binding_record_kind,
            "identity": binding_identity,
            "program_generated_record_sha256": str(
                binding_item.get("program_generated_record_sha256")
                or ""
            ).upper(),
        })
        provenance = (
            binding_item.get("input_provenance")
            if isinstance(
                binding_item.get("input_provenance"), dict
            )
            else {}
        )
        lineage = (
            binding_item.get("parameter_lineage")
            if isinstance(
                binding_item.get("parameter_lineage"), list
            )
            else []
        )
        expected_lineage_summary_rows.append({
            "record_kind": binding_record_kind,
            "identity": binding_identity,
            "lineage_count": len(lineage),
            "final_parameter_lineage_sha256": str(
                provenance.get("final_parameter_lineage_sha256")
                or ""
            ).upper(),
            "final_snapshot_sha256": str(
                provenance.get("final_snapshot_sha256") or ""
            ).upper(),
        })
    add_case_issue(
        all_binding_contracts_valid,
        "PROGRAM_GENERATED_ROW_BINDING_CONTRACT_INVALID",
        context={"invalid_bindings": all_binding_contexts},
    )
    binding_summary = document.get(
        "program_generated_record_binding_summary"
    )
    binding_summary = (
        binding_summary if isinstance(binding_summary, dict) else {}
    )
    binding_hashes = [
        row["program_generated_record_sha256"]
        for row in expected_binding_summary_rows
    ]
    binding_row_keys = [
        (row["record_kind"], row["identity"])
        for row in expected_binding_summary_rows
    ]
    add_case_issue(
        bool(binding_summary)
        and hash_without_key(binding_summary, "summary_sha256")
        and binding_summary.get("schema")
        == "program-generated-stage1-row-binding-summary-v1"
        and binding_summary.get("status") == "PASS"
        and binding_summary.get("row_count")
        == len(expected_binding_summary_rows)
        and binding_summary.get("unique_binding_count")
        == len(set(binding_hashes))
        == len(binding_hashes)
        and len(set(binding_row_keys)) == len(binding_row_keys)
        and all(identity for _, identity in binding_row_keys)
        and binding_summary.get("rows")
        == expected_binding_summary_rows,
        "PROGRAM_GENERATED_ROW_BINDING_SUMMARY_INVALID",
        context={
            "expected_row_count": len(expected_binding_summary_rows),
            "declared_row_count": binding_summary.get("row_count"),
            "expected_rows": expected_binding_summary_rows,
        },
    )
    lineage_summary = document.get(
        "final_parameter_lineage_summary"
    )
    lineage_summary = (
        lineage_summary if isinstance(lineage_summary, dict) else {}
    )
    lineage_row_keys = [
        (row["record_kind"], row["identity"])
        for row in expected_lineage_summary_rows
    ]
    add_case_issue(
        bool(lineage_summary)
        and hash_without_key(lineage_summary, "summary_sha256")
        and lineage_summary.get("schema")
        == "final-parameter-lineage-summary-v1"
        and lineage_summary.get("status") == "PASS"
        and lineage_summary.get("row_count")
        == len(expected_lineage_summary_rows)
        and len(set(lineage_row_keys)) == len(lineage_row_keys)
        and all(identity for _, identity in lineage_row_keys)
        and lineage_summary.get("rows")
        == expected_lineage_summary_rows,
        "FINAL_PARAMETER_LINEAGE_SUMMARY_INVALID",
        context={
            "expected_row_count": len(
                expected_lineage_summary_rows
            ),
            "declared_row_count": lineage_summary.get("row_count"),
            "expected_rows": expected_lineage_summary_rows,
        },
    )
    add_case_issue(
        not any(
            isinstance(blocker, dict)
            and blocker.get("code")
            == "PROGRAM_GENERATED_ROW_BINDING_FAILED"
            for blocker in formal_use_blockers
        ),
        "PROGRAM_GENERATED_ROW_BINDING_FALSE_FORMAL_BLOCKER",
    )
    pipe_reconciliation = document.get("pipe_entity_reconciliation")
    pipe_reconciliation = (
        pipe_reconciliation
        if isinstance(pipe_reconciliation, dict)
        else {}
    )
    add_case_issue(
        bool(pipe_reconciliation)
        and hash_without_key(
            pipe_reconciliation,
            "reconciliation_sha256",
        ),
        "PIPE_ENTITY_RECONCILIATION_MISSING_OR_HASH_INVALID",
    )
    add_case_issue(
        pipe_reconciliation.get("status")
        == "PASS_NO_ENDPOINT_STATE_DOUBLE_COUNT"
        and pipe_reconciliation.get("aspen_physical_pipe_block_count")
        == len(physical_pipe_items)
        and pipe_reconciliation.get(
            "independent_pfd_pipe_segment_count"
        )
        == len(piping_items)
        and pipe_reconciliation.get("pfd_endpoint_state_alias_count")
        == len(alias_items)
        and pipe_reconciliation.get("physical_pipe_entity_count")
        == len(canonical_pipe_entity_ids)
        and pipe_reconciliation.get(
            "canonical_physical_pipe_entity_ids"
        )
        == canonical_pipe_entity_ids
        and pipe_reconciliation.get("endpoint_state_aliases")
        == alias_reconciliation_rows
        and str(
            pipe_reconciliation.get("source_export_sha256") or ""
        ).upper()
        == source_export_sha256
        and str(
            pipe_reconciliation.get("pfd_mapping_sha256") or ""
        ).upper()
        == str(document.get("pfd_mapping_sha256") or "").upper()
        and document.get("piping_count") == len(piping_items)
        and document.get("piping_state_alias_count") == len(alias_items)
        and document.get("physical_pipe_entity_count")
        == len(canonical_pipe_entity_ids),
        "PIPE_ENTITY_RECONCILIATION_COUNTS_OR_BINDINGS_INVALID",
        context={
            "physical_pipe_block_count": len(physical_pipe_items),
            "independent_pfd_pipe_segment_count": len(piping_items),
            "pfd_endpoint_state_alias_count": len(alias_items),
            "physical_pipe_entity_count": len(
                canonical_pipe_entity_ids
            ),
        },
    )
    physical_rows_for_overview = [
        row for row in rows if row["record_kind"] != "logic_node"
    ]
    for row in rows:
        add_issue(
            row,
            str(
                row.get("aspen_case_run_gate_sha256") or ""
            ).upper()
            == str(run_gate.get("run_gate_sha256") or "").upper()
            and bool(run_gate.get("run_gate_sha256")),
            "ASPEN_ROW_GATE_NOT_LINKED_TO_CASE_GATE",
            severity="CRITICAL",
        )
        if row["issues"]:
            row["status"] = "FAIL"
    detailed_by_overview_key: dict[str, dict[str, Any]] = {}
    for row in physical_rows_for_overview:
        overview_kind = (
            "piping"
            if row["record_kind"]
            in {"piping", "physical_pipe_block"}
            else "equipment"
        )
        detailed_by_overview_key[
            f"{overview_kind}:{row['identity']}"
        ] = row
    overview = customer_delivery.build_equipment_overview_table(document)
    overview_verification = (
        customer_delivery.verify_equipment_overview_table(overview)
    )
    add_case_issue(
        overview_verification.get("status") == "PASS",
        "CUSTOMER_OVERVIEW_SELF_VERIFICATION_FAILED",
        severity="CRITICAL",
        context={
            "errors": overview_verification.get("errors", []),
        },
    )
    overview_rows = [
        overview_row
        for overview_row in overview.get("rows", [])
        if isinstance(overview_row, dict)
    ]
    add_case_issue(
        overview.get("row_count") == len(physical_rows_for_overview)
        and len(overview_rows) == len(physical_rows_for_overview)
        and len({
            str(row.get("equipment_key") or "")
            for row in overview_rows
        })
        == len(overview_rows),
        "CUSTOMER_OVERVIEW_ROW_GRAIN_INVALID",
        context={
            "declared": overview.get("row_count"),
            "actual": len(overview_rows),
            "expected": len(physical_rows_for_overview),
        },
    )
    for overview_row in overview_rows:
        equipment_key = str(
            overview_row.get("equipment_key") or ""
        )
        detailed_row = detailed_by_overview_key.get(equipment_key)
        if detailed_row is None:
            add_case_issue(
                False,
                "CUSTOMER_OVERVIEW_ROW_NOT_BOUND_TO_DERIVATION_ROW",
                context={"equipment_key": equipment_key},
            )
            continue
        add_issue(
            detailed_row,
            str(
                overview_row.get(
                    "program_generated_record_sha256"
                )
                or ""
            ).upper()
            == str(
                detailed_row.get(
                    "program_generated_record_sha256"
                )
                or ""
            ).upper()
            and bool(
                detailed_row.get(
                    "program_generated_record_sha256"
                )
            ),
            "CUSTOMER_OVERVIEW_DERIVATION_ROW_SHA256_MISMATCH",
            severity="CRITICAL",
            context={
                "overview_sha256": overview_row.get(
                    "program_generated_record_sha256"
                ),
                "derivation_sha256": detailed_row.get(
                    "program_generated_record_sha256"
                ),
            },
        )
        coverage = overview_row.get("customer_information_coverage")
        coverage = coverage if isinstance(coverage, dict) else {}
        missing_fields = overview_row.get(
            "customer_table_missing_fields"
        )
        missing_fields = (
            [str(field) for field in missing_fields]
            if isinstance(missing_fields, list)
            else []
        )
        blockers = coverage.get("blocking_fields")
        blockers = (
            [str(field) for field in blockers]
            if isinstance(blockers, list)
            else []
        )
        coverage_state = str(coverage.get("state") or "")
        detailed_row["customer_information_coverage_state"] = (
            coverage_state
        )
        detailed_row["customer_missing_field_count"] = len(
            missing_fields
        )
        if missing_fields:
            add_issue(
                detailed_row,
                coverage_state == "PROVISIONAL_WITH_OPEN_GAPS"
                and set(missing_fields).issubset(set(blockers)),
                "CUSTOMER_MISSING_FIELDS_FALSE_PASS",
                severity="CRITICAL",
                context={
                    "missing_fields": missing_fields,
                    "blocking_fields": blockers,
                    "coverage_state": coverage_state,
                },
            )
        else:
            add_issue(
                detailed_row,
                coverage_state == "PASS" and not blockers,
                "CUSTOMER_COVERAGE_STATE_INCONSISTENT_WITH_NO_GAPS",
                severity="CRITICAL",
            )
        cells = [
            cell
            for cell in overview_row.get("all_equipment_fields", [])
            if isinstance(cell, dict)
        ]
        cells_by_id = {
            str(cell.get("field_id") or ""): cell
            for cell in cells
            if str(cell.get("field_id") or "")
        }
        invalid_open_cells: list[dict[str, Any]] = []
        for cell in cells:
            if (
                str(cell.get("state") or "")
                != "OPEN_FORMAL_EVIDENCE_GATE"
            ):
                continue
            source = (
                cell.get("source")
                if isinstance(cell.get("source"), dict)
                else {}
            )
            open_gate = (
                cell.get("open_gate")
                if isinstance(cell.get("open_gate"), dict)
                else {}
            )
            reason = (
                open_gate.get("reason")
                or source.get("reason")
            )
            required_action = (
                open_gate.get("required_action")
                or source.get("required_action")
            )
            evidence_class = str(
                source.get("evidence_class")
                or source.get("field_evidence_class")
                or ""
            ).upper()
            promotion_cap = str(
                cell.get("promotion_cap")
                or open_gate.get("promotion_cap")
                or source.get("promotion_cap")
                or ""
            ).upper()
            if not (
                cell.get("value") is None
                and bool(str(cell.get("display_value") or "").strip())
                and bool(str(reason or "").strip())
                and bool(str(required_action or "").strip())
                and evidence_class == "U"
                and promotion_cap == "NOT_PROMOTABLE"
            ):
                invalid_open_cells.append({
                    "field_id": cell.get("field_id"),
                    "value": cell.get("value"),
                    "has_display": bool(
                        str(cell.get("display_value") or "").strip()
                    ),
                    "has_reason": bool(str(reason or "").strip()),
                    "has_required_action": bool(
                        str(required_action or "").strip()
                    ),
                    "evidence_class": evidence_class,
                    "promotion_cap": promotion_cap,
                })
        add_issue(
            detailed_row,
            not invalid_open_cells,
            "CUSTOMER_OPEN_GATE_VALUE_OR_METADATA_INVALID",
            severity="CRITICAL",
            context={"invalid_open_cells": invalid_open_cells},
        )
        if detailed_row.get("aspen_block_type") in TOWER_BLOCK_TYPES:
            forbidden_screening_field_ids = {
                "tower_diameter_screening_mm",
                "tower_height_screening_mm",
                "formula_only_shell_thickness_mm",
                "formula_only_head_thickness_mm",
                "inner_diameter_mm",
            }
            leaked_screening_cells = sorted(
                forbidden_screening_field_ids.intersection(
                    cells_by_id
                )
            )
            key_summary = cells_by_id.get(
                "key_specification_summary", {}
            ).get("value")
            key_summary_leaks = public_key_paths(
                key_summary,
                target_keys={
                    *forbidden_screening_field_ids,
                    "height_mm",
                },
                path=(
                    "$.all_equipment_fields."
                    "key_specification_summary"
                ),
            )
            public_model_text = " | ".join([
                str(
                    overview_row.get("model_or_specification") or ""
                ),
                str(
                    overview_row.get(
                        "model_estimate_disclosure"
                    )
                    or ""
                ),
            ])
            public_text_leaks = [
                token
                for token in (
                    "Di_screen=",
                    "H_layout_screen=",
                    "shell_formula_t=",
                )
                if token in public_model_text
            ]
            add_issue(
                detailed_row,
                not leaked_screening_cells
                and not key_summary_leaks
                and not public_text_leaks,
                "TOWER_SCREENING_GEOMETRY_LEAKED_TO_CUSTOMER_OVERVIEW",
                severity="CRITICAL",
                context={
                    "field_ids": leaked_screening_cells,
                    "key_summary_paths": key_summary_leaks,
                    "public_text_tokens": public_text_leaks,
                },
            )
            formal_geometry_cells = {
                field_id: cells_by_id.get(field_id, {})
                for field_id in ("diameter_mm", "height_mm")
            }
            add_issue(
                detailed_row,
                all(
                    bool(formal_geometry_cells[field_id])
                    and formal_geometry_cells[field_id].get("value")
                    is None
                    and formal_geometry_cells[field_id].get("state")
                    == "OPEN_FORMAL_EVIDENCE_GATE"
                    for field_id in ("diameter_mm", "height_mm")
                ),
                "TOWER_FORMAL_GEOMETRY_OPEN_GATE_MISSING_OR_NUMERIC",
                severity="CRITICAL",
            )
        if detailed_row.get("aspen_block_type") == "PUMP":
            required_pump_fields = {
                "hydraulic_power_kw",
                "shaft_power_kw",
                "electrical_power_kw",
                "pump_efficiency_percent",
                "driver_efficiency_percent",
                "fluid_to_shaft_balance_status",
                "fluid_to_shaft_balance_relative_error",
                "shaft_to_electrical_balance_status",
                "shaft_to_electrical_balance_relative_error",
                "pump_power_process_audit_ref",
                "aspen_configured_shaft_speed_candidate_rpm",
                "aspen_actual_shaft_speed_rpm",
                "pump_candidate_reference_speed_rpm",
                "npsha_pressure_kpa",
                "npsha_raw_unit_semantics",
                "pump_npsha_process_audit_ref",
                "aspen_flow_m3_h",
                "aspen_simulated_head_m",
                "medium_name",
            }
            missing_pump_fields = sorted(
                required_pump_fields.difference(cells_by_id)
            )
            add_issue(
                detailed_row,
                not missing_pump_fields,
                "PUMP_CUSTOMER_REQUIRED_FIELDS_MISSING",
                severity="CRITICAL",
                context={
                    "missing_fields": missing_pump_fields,
                },
            )
            known_numeric_fields = (
                "hydraulic_power_kw",
                "shaft_power_kw",
                "electrical_power_kw",
                "pump_efficiency_percent",
                "aspen_flow_m3_h",
                "aspen_simulated_head_m",
            )
            invalid_known_numeric_fields = {
                field_id: cells_by_id.get(field_id, {}).get("value")
                for field_id in known_numeric_fields
                if finite_number(
                    cells_by_id.get(field_id, {}).get("value")
                )
                is None
            }
            add_issue(
                detailed_row,
                not invalid_known_numeric_fields,
                "PUMP_CUSTOMER_KNOWN_PROCESS_OR_POWER_VALUE_MISSING",
                severity="CRITICAL",
                context={
                    "invalid_fields": invalid_known_numeric_fields,
                },
            )
            candidate_speed_cell = cells_by_id.get(
                "pump_candidate_reference_speed_rpm", {}
            )
            add_issue(
                detailed_row,
                finite_number(candidate_speed_cell.get("value"))
                is not None
                or (
                    candidate_speed_cell.get("value") is None
                    and candidate_speed_cell.get("state")
                    == "OPEN_FORMAL_EVIDENCE_GATE"
                ),
                "PUMP_CUSTOMER_CANDIDATE_SPEED_FALSE_VALUE_OR_GATE",
                severity="CRITICAL",
            )
            driver_cell = cells_by_id.get(
                "driver_efficiency_percent", {}
            )
            add_issue(
                detailed_row,
                finite_number(driver_cell.get("value")) is not None
                or (
                    driver_cell.get("value") is None
                    and driver_cell.get("state")
                    == "OPEN_FORMAL_EVIDENCE_GATE"
                ),
                "PUMP_CUSTOMER_DRIVER_EFFICIENCY_FALSE_VALUE_OR_GATE",
                severity="CRITICAL",
            )
            balance_status_fields = (
                "fluid_to_shaft_balance_status",
                "shaft_to_electrical_balance_status",
            )
            invalid_balance_status_fields = {
                field_id: cells_by_id.get(field_id, {}).get("value")
                for field_id in balance_status_fields
                if not str(
                    cells_by_id.get(field_id, {}).get("value")
                    or ""
                ).strip()
            }
            add_issue(
                detailed_row,
                not invalid_balance_status_fields,
                "PUMP_CUSTOMER_POWER_BALANCE_STATUS_MISSING",
                severity="CRITICAL",
                context={
                    "invalid_fields": invalid_balance_status_fields,
                },
            )
            balance_error_fields = (
                "fluid_to_shaft_balance_relative_error",
                "shaft_to_electrical_balance_relative_error",
            )
            invalid_balance_error_fields: dict[str, Any] = {}
            for field_id in balance_error_fields:
                cell = cells_by_id.get(field_id, {})
                if finite_number(cell.get("value")) is not None:
                    continue
                if (
                    cell.get("value") is None
                    and cell.get("state")
                    == "OPEN_FORMAL_EVIDENCE_GATE"
                ):
                    continue
                invalid_balance_error_fields[field_id] = {
                    "value": cell.get("value"),
                    "state": cell.get("state"),
                }
            add_issue(
                detailed_row,
                not invalid_balance_error_fields,
                "PUMP_CUSTOMER_POWER_BALANCE_ERROR_FALSE_VALUE_OR_GATE",
                severity="CRITICAL",
                context={
                    "invalid_fields": invalid_balance_error_fields,
                },
            )
            add_issue(
                detailed_row,
                bool(
                    str(
                        cells_by_id.get(
                            "medium_name", {}
                        ).get("value")
                        or ""
                    ).strip()
                ),
                "PUMP_CUSTOMER_MEDIUM_MISSING",
                severity="CRITICAL",
            )
            power_audit_ref = cells_by_id.get(
                "pump_power_process_audit_ref", {}
            ).get("value")
            add_issue(
                detailed_row,
                isinstance(power_audit_ref, dict)
                and power_audit_ref.get("schema")
                == "pump-power-process-audit-v1"
                and bool(power_audit_ref.get("audit_sha256")),
                "PUMP_CUSTOMER_POWER_AUDIT_REFERENCE_INVALID",
                severity="CRITICAL",
            )
            actual_speed_cell = cells_by_id.get(
                "aspen_actual_shaft_speed_rpm", {}
            )
            configured_speed_cell = cells_by_id.get(
                "aspen_configured_shaft_speed_candidate_rpm", {}
            )
            configured_speed = finite_number(
                detailed_row.get(
                    "aspen_configured_shaft_speed_candidate_rpm"
                )
            )
            if configured_speed is not None:
                configured_source = (
                    configured_speed_cell.get("source")
                    if isinstance(
                        configured_speed_cell.get("source"),
                        dict,
                    )
                    else {}
                )
                add_issue(
                    detailed_row,
                    numeric_equal(
                        configured_speed_cell.get("value"),
                        configured_speed,
                    )
                    and configured_speed_cell.get("state")
                    == (
                        "ASPEN_CONFIGURED_INPUT_CANDIDATE_"
                        "NOT_SOLVED_ACTUAL_SPEED"
                    )
                    and str(
                        configured_source.get("evidence_class")
                        or ""
                    ).upper()
                    == "R"
                    and str(
                        configured_source.get("promotion_cap")
                        or ""
                    ).upper()
                    == "TYPE_SCREENING"
                    and configured_source.get(
                        "formal_design_evidence"
                    )
                    is False,
                    "PUMP_CUSTOMER_CONFIGURED_SPEED_SEMANTICS_INVALID",
                    severity="CRITICAL",
                )
                add_issue(
                    detailed_row,
                    actual_speed_cell.get("value") is None
                    and actual_speed_cell.get("state")
                    == "OPEN_FORMAL_EVIDENCE_GATE",
                    "PUMP_CONFIGURED_SPEED_LEAKED_AS_ACTUAL_SPEED",
                    severity="CRITICAL",
                )
            else:
                add_issue(
                    detailed_row,
                    configured_speed_cell.get("value") is None
                    and configured_speed_cell.get("state")
                    == "OPEN_FORMAL_EVIDENCE_GATE",
                    "PUMP_CUSTOMER_CONFIGURED_SPEED_FALSE_VALUE_OR_GATE",
                    severity="CRITICAL",
                )
            npsha_pressure_cell = cells_by_id.get(
                "npsha_pressure_kpa", {}
            )
            npsha_semantics_cell = cells_by_id.get(
                "npsha_raw_unit_semantics", {}
            )
            npsha_audit_ref = cells_by_id.get(
                "pump_npsha_process_audit_ref", {}
            ).get("value")
            npsha_pressure = finite_number(
                npsha_pressure_cell.get("value")
            )
            add_issue(
                detailed_row,
                npsha_pressure is not None
                or (
                    npsha_pressure_cell.get("value") is None
                    and npsha_pressure_cell.get("state")
                    == "OPEN_FORMAL_EVIDENCE_GATE"
                ),
                "PUMP_CUSTOMER_NPSHA_FALSE_VALUE_OR_GATE",
                severity="CRITICAL",
            )
            if npsha_pressure is not None:
                add_issue(
                    detailed_row,
                    isinstance(
                        npsha_semantics_cell.get("value"), dict
                    )
                    and isinstance(npsha_audit_ref, dict)
                    and npsha_audit_ref.get("schema")
                    == "pump-npsha-process-audit-v1"
                    and bool(npsha_audit_ref.get("audit_sha256")),
                    "PUMP_CUSTOMER_NPSHA_SEMANTIC_REFERENCE_INVALID",
                    severity="CRITICAL",
                )
        if detailed_row["record_kind"] in {
            "piping",
            "physical_pipe_block",
        }:
            hydraulic_customer_fields = {
                field_id: cells_by_id.get(field_id, {})
                for field_id in (
                    "actual_velocity_m_s",
                    "reynolds_number",
                    "pressure_gradient_kpa_per_100m",
                )
            }
            add_issue(
                detailed_row,
                all(
                    finite_number(
                        hydraulic_customer_fields[field_id].get(
                            "value"
                        )
                    )
                    is not None
                    for field_id in hydraulic_customer_fields
                ),
                "PIPE_CUSTOMER_HYDRAULIC_FIELDS_MISSING",
                severity="CRITICAL",
                context={
                    field_id: cell.get("value")
                    for field_id, cell
                    in hydraulic_customer_fields.items()
                },
            )
            pipe_open_fields = {
                field_id: cells_by_id.get(field_id, {})
                for field_id in (
                    "stress_analysis_ref",
                    "support_design_ref",
                )
            }
            add_issue(
                detailed_row,
                all(
                    bool(cell)
                    and cell.get("value") is None
                    and cell.get("state")
                    == "OPEN_FORMAL_EVIDENCE_GATE"
                    for cell in pipe_open_fields.values()
                ),
                "PIPE_CUSTOMER_FORMAL_OPEN_FIELDS_NOT_NULL",
                severity="CRITICAL",
                context={
                    field_id: {
                        "value": cell.get("value"),
                        "state": cell.get("state"),
                    }
                    for field_id, cell in pipe_open_fields.items()
                },
            )
            temperature_cells = [
                cell
                for cell in cells
                if cell.get("field_id")
                in {"temperature_c", "operating_temperature_c"}
                and finite_number(cell.get("value")) is not None
            ]
            temperature_evidence_classes: list[str] = []
            valid_temperature_evidence = False
            for cell in temperature_cells:
                source = (
                    cell.get("source")
                    if isinstance(cell.get("source"), dict)
                    else {}
                )
                source_lineage = (
                    source.get("aspen_parameter_lineage")
                    if isinstance(
                        source.get("aspen_parameter_lineage"),
                        dict,
                    )
                    else {}
                )
                evidence_class = str(
                    source.get("evidence_class")
                    or source.get("field_evidence_class")
                    or source_lineage.get("evidence_class")
                    or ""
                ).upper()
                temperature_evidence_classes.append(evidence_class)
                if (
                    evidence_class == "D"
                    and source_lineage.get("evidence_class") == "D"
                    and str(
                        source_lineage.get("source_file_sha256")
                        or ""
                    ).upper()
                    == source_export_sha256
                ):
                    valid_temperature_evidence = True
            detailed_row[
                "customer_temperature_evidence_class"
            ] = (
                ",".join(sorted(set(temperature_evidence_classes)))
                if temperature_evidence_classes
                else None
            )
            add_issue(
                detailed_row,
                bool(temperature_cells)
                and valid_temperature_evidence,
                "PIPE_CUSTOMER_TEMPERATURE_U_OR_UNBOUND_EVIDENCE",
                severity="CRITICAL",
                context={
                    "evidence_classes": temperature_evidence_classes,
                },
            )
    for overview_key, detailed_row in detailed_by_overview_key.items():
        if not any(
            str(overview_row.get("equipment_key") or "")
            == overview_key
            for overview_row in overview_rows
        ):
            add_issue(
                detailed_row,
                False,
                "DERIVATION_ROW_MISSING_FROM_CUSTOMER_OVERVIEW",
                severity="CRITICAL",
            )
    for row in rows:
        if row["issues"]:
            row["status"] = "FAIL"
    entity_groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if row["record_kind"] not in {
            "piping",
            "physical_pipe_block",
        }:
            continue
        entity_id = str(row.get("pipe_entity_id") or "").strip()
        if entity_id:
            entity_groups.setdefault(entity_id, []).append(row)
    duplicate_entity_groups = {
        entity_id: group
        for entity_id, group in entity_groups.items()
        if len(group) > 1
    }
    for entity_id, group in duplicate_entity_groups.items():
        for row in group:
            add_issue(
                row,
                False,
                "PHYSICAL_PIPE_AND_PFD_PIPE_DUPLICATE_ENTITY_COUNT",
                severity="CRITICAL",
                context={
                    "pipe_entity_id": entity_id,
                    "rows": [
                        {
                            "record_kind": member["record_kind"],
                            "identity": member["identity"],
                        }
                        for member in group
                    ],
                },
            )
            row["status"] = "FAIL"
    failures = [row for row in rows if row["status"] == "FAIL"]
    physical_rows = [
        row for row in rows if row["record_kind"] != "logic_node"
    ]
    report = {
        "case": case_name,
        "status": (
            "PASS"
            if document.get("status") == "DERIVED"
            and not case_issues
            and not failures
            else "FAIL"
        ),
        "source_result_path": str(path),
        "source_result_sha256": sha256_file(path),
        "source_export_path": str(source_path),
        "source_export_sha256": source_export_sha256,
        "engine_version": document.get("engine_version"),
        "aspen_run_status": run_gate.get("status"),
        "aspen_run_counts": run_counts,
        "highest_aspen_severity": computed_aspen_highest,
        "raw_history_block_issue_count": attribution.get(
            "block_issue_count",
            0,
        ),
        "physical_row_count": len(physical_rows),
        "equipment_row_count": sum(
            row["record_kind"] == "equipment" for row in physical_rows
        ),
        "physical_pipe_block_row_count": sum(
            row["record_kind"] == "physical_pipe_block"
            for row in physical_rows
        ),
        "piping_row_count": sum(
            row["record_kind"] == "piping" for row in physical_rows
        ),
        "pfd_endpoint_state_alias_count": len(alias_items),
        "unique_pipe_entity_count": len(entity_groups),
        "duplicate_pipe_entity_count": len(
            duplicate_entity_groups
        ),
        "logic_node_count": sum(
            row["record_kind"] == "logic_node" for row in rows
        ),
        "failed_row_count": len(failures),
        "case_issues": case_issues,
        "case_issue_details": case_issue_details,
        "highest_issue_severity": highest_severity([
            *[
                str(detail.get("severity") or "NONE")
                for detail in case_issue_details
            ],
            *[
                str(row.get("highest_issue_severity") or "NONE")
                for row in rows
            ],
        ]),
    }
    return report, rows


def write_outputs(
    output_dir: Path,
    report: dict[str, Any],
    rows: list[dict[str, Any]],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "STAGE1_DETAILED_RELIABILITY_AUDIT.json"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    fieldnames = [
        "case",
        "record_kind",
        "identity",
        "aspen_block_type",
        "family_id",
        "recommended_type",
        "designation",
        "selected_dn",
        "outer_diameter_mm",
        "wall_thickness_mm",
        "pressure_class",
        "manufacturing_route",
        "pipe_entity_scope",
        "pipe_entity_id",
        "pipe_entity_role",
        "counted_as_physical_pipe",
        "alias_only",
        "canonical_pipe_entity_ids",
        "source_endpoint",
        "destination_endpoint",
        "endpoint_pressure_drop_status",
        "phase",
        "actual_velocity_m_s",
        "pressure_gradient_kpa_per_100m",
        "vacuum_margin_kpa",
        "external_pressure_branch",
        "aspen_case_status",
        "aspen_local_status",
        "aspen_case_run_gate_sha256",
        "program_specification_hash_valid",
        "preselection_hash_valid",
        "pressure_regime_hash_valid",
        "model_source_hash_valid",
        "lineage_source_hash_valid",
        "row_gate_hash_valid",
        "row_gate_identity_bound",
        "row_gate_dirty_affects_formal_use",
        "program_generated_binding_hash_valid",
        "program_generated_record_sha256",
        "aspen_configured_shaft_speed_candidate_rpm",
        "customer_information_coverage_state",
        "customer_missing_field_count",
        "customer_temperature_evidence_class",
        "highest_issue_severity",
        "status",
        "issues",
        "issue_details",
        "review_notes",
    ]
    with (
        output_dir / "STAGE1_DETAILED_RELIABILITY_ROWS.csv"
    ).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            serialised = dict(row)
            serialised["issues"] = json.dumps(
                row["issues"],
                ensure_ascii=False,
                separators=(",", ":"),
            )
            serialised["issue_details"] = json.dumps(
                row["issue_details"],
                ensure_ascii=False,
                separators=(",", ":"),
            )
            serialised["review_notes"] = json.dumps(
                row["review_notes"],
                ensure_ascii=False,
                separators=(",", ":"),
            )
            serialised["canonical_pipe_entity_ids"] = json.dumps(
                row.get("canonical_pipe_entity_ids"),
                ensure_ascii=False,
                separators=(",", ":"),
            )
            writer.writerow(serialised)
    lines = [
        "# 第一阶段设备与管线逐行可靠性审计",
        "",
        f"- 总状态：`{report['status']}`",
        f"- 实际物理行：{report['physical_row_count']}",
        f"- 设备（不含 Aspen PIPE）：{report['equipment_row_count']}",
        f"- Aspen PIPE 物理块：{report['physical_pipe_block_row_count']}",
        f"- PFD 物料管线：{report['piping_row_count']}",
        f"- 流程逻辑节点（N/A）：{report['logic_node_count']}",
        f"- 失败行：{report['failed_row_count']}",
        f"- 单相管线压降最大值：{report['maximum_single_phase_pressure_gradient_kpa_per_100m']:.6g} kPa/100m",
        f"- 显著稳态真空分支：{report['external_pressure_branch_count']}",
        f"- 大口径 LSAW 路线：{report['large_bore_lsa_welded_count']}",
        "",
        "## 案例",
        "",
    ]
    for case in report["cases"]:
        lines.append(
            f"- `{case['case']}`：`{case['status']}`；"
            f"物理行 {case['physical_row_count']}；"
            f"Aspen运行 `{case['aspen_run_status']}`；"
            f"逐行失败 {case['failed_row_count']}"
        )
    lines.extend([
        "",
        "## 结论边界",
        "",
        "- PASS 表示每个物理设备/管线均有具体程序候选，关键数值、标准记录、程序规格、预选、压力工况和来源哈希链相互一致。",
        "- 单相 50 kPa/100m 是程序登记的项目预筛阈值，不是国家标准验收限值。",
        "- 两相管线只验证均相代理始终保持 advisory；正式流型、持液率、滑移、闪蒸、段塞和压降关联式仍开放。",
        "- 塔器、反应器、换热器、泵和阀门仍保留各自的机械、厂家和项目审批门禁；本审计不把预筛提升为正式设计。",
        "",
        "逐行证据见 `STAGE1_DETAILED_RELIABILITY_ROWS.csv`，机器可复核对象见 `STAGE1_DETAILED_RELIABILITY_AUDIT.json`。",
    ])
    lines = [
        "# 第一阶段设备与管线逐行可靠性审计",
        "",
        f"- 总状态：`{report['status']}`",
        f"- 物理行：{report['physical_row_count']}",
        f"- 普通设备：{report['equipment_row_count']}",
        f"- Aspen PIPE 物理块：{report['physical_pipe_block_row_count']}",
        f"- PFD 物料管线：{report['piping_row_count']}",
        f"- 流程逻辑节点（不计入物理设备）：{report['logic_node_count']}",
        f"- 失败行：{report['failed_row_count']}",
        f"- 审计问题最高级别：`{report['highest_issue_severity']}`",
        f"- Aspen 事件最高级别：`{report['highest_aspen_severity']}`",
        f"- 审计严重度汇总：`{json.dumps(report['issue_severity_counts'], ensure_ascii=False, sort_keys=True)}`",
        f"- 唯一管线实体：{report['unique_pipe_entity_count']}",
        f"- 重复管线实体：{report['duplicate_pipe_entity_count']}",
        (
            "- 单相管线压降梯度最大值："
            f"{report['maximum_single_phase_pressure_gradient_kpa_per_100m']:.6g} "
            "kPa/100m"
        ),
        f"- 显著稳态真空分支：{report['external_pressure_branch_count']}",
        f"- 大口径 LSAW 路线：{report['large_bore_lsa_welded_count']}",
        "",
        "## 案例",
        "",
    ]
    for case in report["cases"]:
        lines.append(
            f"- `{case['case']}`：`{case['status']}`；"
            f"物理行 {case['physical_row_count']}；"
            f"Aspen 运行 `{case['aspen_run_status']}`；"
            f"Aspen 最高级别 `{case['highest_aspen_severity']}`；"
            f"逐行失败 {case['failed_row_count']}；"
            f"重复管线实体 {case['duplicate_pipe_entity_count']}"
        )
    lines.extend([
        "",
        "## 审计边界",
        "",
        "- PASS 要求每一行的具体程序候选、模型/终端推荐、关键数值、来源哈希、行身份哈希及正式门禁相互一致。",
        "- 泵的流体功率、轴功率和电功率必须分通道记录；Aspen PUMP 的 WNET 不得冒充轴功率。",
        "- 塔径和塔高只能以明确的 screening 字段出现，不得泄漏为正式 inner_diameter/height。",
        "- PFD 物料流股与 Aspen PIPE 物理块必须有不同的实体身份；缺整段端点压降时必须明确阻断正式水力验收。",
        "- 单相 50 kPa/100m 是程序登记的项目预筛阈值，不是国家标准验收限值；两相结果始终只作 advisory。",
        "- 塔、反应器、换热器、泵、阀门和管道仍保留机械、厂家及项目审批门禁；本审计不把预筛提升为正式设计。",
        "",
        "逐行问题见 `STAGE1_DETAILED_RELIABILITY_ROWS.csv`，完整机器可复核对象见 `STAGE1_DETAILED_RELIABILITY_AUDIT.json`。",
    ])
    (output_dir / "STAGE1_DETAILED_RELIABILITY_AUDIT.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit every Stage-1 physical equipment, physical Aspen PIPE "
            "block and PFD material line, including hydraulic and hash chains."
        )
    )
    parser.add_argument(
        "--case",
        action="append",
        default=[],
        type=parse_case_argument,
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if not args.case:
        raise SystemExit("At least one --case LABEL=PATH is required")
    case_reports: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    labels: set[str] = set()
    for label, path in args.case:
        if label in labels:
            raise SystemExit(f"Duplicate case label: {label}")
        labels.add(label)
        case_report, case_rows = audit_case(label, path)
        case_reports.append(case_report)
        rows.extend(case_rows)
    physical_rows = [
        row for row in rows if row["record_kind"] != "logic_node"
    ]
    single_phase_gradients = [
        float(row["pressure_gradient_kpa_per_100m"])
        for row in physical_rows
        if row["record_kind"] in {"piping", "physical_pipe_block"}
        and str(row.get("phase") or "").casefold()
        not in TWO_PHASE_NAMES
        and finite_number(row.get("pressure_gradient_kpa_per_100m"))
        is not None
    ]
    failed_rows = [
        row for row in physical_rows if row["status"] == "FAIL"
    ]
    issue_counts = Counter(
        issue for row in failed_rows for issue in row["issues"]
    )
    case_issue_counts = Counter(
        issue
        for case in case_reports
        for issue in case.get("case_issues", [])
    )
    audit_issue_details = [
        detail
        for row in rows
        for detail in row.get("issue_details", [])
        if isinstance(detail, dict)
    ]
    case_issue_details = [
        detail
        for case in case_reports
        for detail in case.get("case_issue_details", [])
        if isinstance(detail, dict)
    ]
    severity_counts = Counter(
        str(detail.get("severity") or "NONE").upper()
        for detail in [*audit_issue_details, *case_issue_details]
    )
    overall_highest_issue = highest_severity(
        list(severity_counts.elements())
    )
    overall_highest_aspen = max(
        (
            str(case.get("highest_aspen_severity") or "none")
            for case in case_reports
        ),
        key=lambda value: ASPEN_SEVERITY_ORDER.get(value, -1),
        default="none",
    )
    report = {
        "schema": SCHEMA,
        "status": (
            "PASS"
            if all(case["status"] == "PASS" for case in case_reports)
            and not failed_rows
            else "FAIL"
        ),
        "case_count": len(case_reports),
        "passed_case_count": sum(
            case["status"] == "PASS" for case in case_reports
        ),
        "physical_row_count": len(physical_rows),
        "equipment_row_count": sum(
            row["record_kind"] == "equipment" for row in physical_rows
        ),
        "physical_pipe_block_row_count": sum(
            row["record_kind"] == "physical_pipe_block"
            for row in physical_rows
        ),
        "piping_row_count": sum(
            row["record_kind"] == "piping" for row in physical_rows
        ),
        "pfd_endpoint_state_alias_count": sum(
            int(case.get("pfd_endpoint_state_alias_count") or 0)
            for case in case_reports
        ),
        "logic_node_count": sum(
            row["record_kind"] == "logic_node" for row in rows
        ),
        "passed_row_count": sum(
            row["status"] == "PASS" for row in physical_rows
        ),
        "failed_row_count": len(failed_rows),
        "issue_counts": dict(sorted(issue_counts.items())),
        "case_issue_counts": dict(sorted(case_issue_counts.items())),
        "issue_severity_counts": {
            severity: severity_counts.get(severity, 0)
            for severity in ("CRITICAL", "ERROR", "WARNING", "INFO")
        },
        "highest_issue_severity": overall_highest_issue,
        "highest_aspen_severity": overall_highest_aspen,
        "aspen_severity_case_counts": dict(sorted(Counter(
            str(case.get("highest_aspen_severity") or "none")
            for case in case_reports
        ).items())),
        "unique_pipe_entity_count": sum(
            int(case.get("unique_pipe_entity_count") or 0)
            for case in case_reports
        ),
        "duplicate_pipe_entity_count": sum(
            int(case.get("duplicate_pipe_entity_count") or 0)
            for case in case_reports
        ),
        "maximum_single_phase_pressure_gradient_kpa_per_100m": (
            max(single_phase_gradients)
            if single_phase_gradients
            else 0.0
        ),
        "external_pressure_branch_count": sum(
            row.get("external_pressure_branch") is True
            for row in physical_rows
        ),
        "large_bore_lsa_welded_count": sum(
            row.get("manufacturing_route") == "LSAW_PLATE_ROLLED"
            for row in physical_rows
        ),
        "formal_readiness": (
            "BLOCKED_PRELIMINARY_ONLY_BY_DESIGN"
        ),
        "cases": case_reports,
        "rows": rows,
    }
    write_outputs(args.output_dir.resolve(), report, rows)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
