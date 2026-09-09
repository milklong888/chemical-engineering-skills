from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PACKAGE_ROOT / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import customer_delivery


SCHEMA = "equipment-design-multi-bkp-authority-overview-gate-v2"
EXPLICIT_OPEN_GATE_STATE = "OPEN_FORMAL_EVIDENCE_GATE"
RAW_CUSTOMER_GAP_STATES = {
    "MISSING",
    "EXTERNAL",
    "EXTERNAL_REQUIRED",
    "NOT_ADOPTED",
    "NOT_EXPLICITLY_ADOPTED",
}
PROVISIONAL_INFORMATION_STATE = "PROVISIONAL_WITH_OPEN_GAPS"
NONCONCRETE_SELECTION_TOKENS = (
    "非标准型",
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
    "unspecified",
)
STAGE1_REAL_CASE_LABELS = {"CUMENE", "EX2_1", "EX2_4", "MCH"}
STAGE1_REAL_CASE_EXPECTED_PHYSICAL_ROWS = 58


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


def _is_logic_node(item: dict[str, Any]) -> bool:
    match = (
        item.get("match_result")
        if isinstance(item.get("match_result"), dict)
        else {}
    )
    return (
        item.get("aspen_mapping_status")
        == "NOT_APPLICABLE_SIMULATION_LOGIC_NODE"
        or match.get("status") == "NOT_APPLICABLE"
    )


def _is_physical_pipe_block(item: dict[str, Any]) -> bool:
    return (
        item.get("pipe_entity_scope") == "ASPEN_PHYSICAL_PIPE_BLOCK"
        and item.get("counted_as_physical_pipe") is True
    )


def _source_input_sha256(item: dict[str, Any]) -> str | None:
    match = (
        item.get("match_result")
        if isinstance(item.get("match_result"), dict)
        else {}
    )
    value = str(match.get("input_sha256") or "").strip().upper()
    return value or None


def physical_source_profile(document: dict[str, Any]) -> dict[str, Any]:
    equipment_count = 0
    piping_count = 0
    logic_count = 0
    alias_count = 0
    expected_bindings: list[tuple[str, str | None]] = []
    for item in document.get("equipment", []):
        if not isinstance(item, dict):
            continue
        if item.get("alias_only") is True:
            alias_count += 1
            continue
        if _is_logic_node(item):
            logic_count += 1
            continue
        record_kind = "piping" if _is_physical_pipe_block(item) else "equipment"
        if record_kind == "piping":
            piping_count += 1
        else:
            equipment_count += 1
        expected_bindings.append((record_kind, _source_input_sha256(item)))
    for item in document.get("piping", []):
        if not isinstance(item, dict):
            continue
        if item.get("alias_only") is True:
            alias_count += 1
            continue
        if _is_logic_node(item):
            logic_count += 1
            continue
        piping_count += 1
        expected_bindings.append(("piping", _source_input_sha256(item)))
    alias_count += sum(
        isinstance(item, dict)
        for item in document.get("piping_state_aliases", [])
    )
    return {
        "equipment_count": equipment_count,
        "piping_count": piping_count,
        "logic_count": logic_count,
        "alias_count": alias_count,
        "expected_bindings": expected_bindings,
    }


def physical_source_count(document: dict[str, Any]) -> tuple[int, int, int]:
    profile = physical_source_profile(document)
    return (
        profile["equipment_count"],
        profile["piping_count"],
        profile["logic_count"],
    )


def cell_hash_check(row: dict[str, Any], cell: dict[str, Any]) -> bool:
    expected = canonical_sha256({
        "input_sha256": row.get("source_input_sha256"),
        "record_kind": row.get("record_kind"),
        "authority_table_id": row.get("authority_table_id"),
        "authority_column_index": cell.get("authority_column_index"),
        "field_id": cell.get("field_id"),
        "value": cell.get("value"),
        "display_value": cell.get("display_value"),
        "unit": cell.get("unit"),
        "state": cell.get("state"),
        "promotion_cap": cell.get("promotion_cap"),
        "open_gate": cell.get("open_gate"),
        "source_field_id": cell.get("source_field_id"),
        "source": cell.get("source"),
        "source_chain_binding_sha256": cell.get(
            "source_chain_binding_sha256"
        ),
        "derivation_record_kind": cell.get(
            "derivation_record_kind"
        ),
        "derivation_record_identity": cell.get(
            "derivation_record_identity"
        ),
        "program_generated_record_sha256": cell.get(
            "program_generated_record_sha256"
        ),
        "program_generated_record_binding_sha256": cell.get(
            "program_generated_record_binding_sha256"
        ),
    })
    return cell.get("cell_sha256") == expected


def delivery_cell_hash_check(row: dict[str, Any], cell: dict[str, Any]) -> bool:
    expected = canonical_sha256({
        "input_sha256": row.get("source_input_sha256"),
        "record_kind": row.get("record_kind"),
        "delivery_scope": cell.get("delivery_scope"),
        "delivery_field_index": cell.get("delivery_field_index"),
        "field_id": cell.get("field_id"),
        "value": cell.get("value"),
        "display_value": cell.get("display_value"),
        "unit": cell.get("unit"),
        "state": cell.get("state"),
        "promotion_cap": cell.get("promotion_cap"),
        "open_gate": cell.get("open_gate"),
        "source_field_id": cell.get("source_field_id"),
        "source": cell.get("source"),
        "requirement": cell.get("requirement"),
        "evidence_gate": cell.get("evidence_gate"),
        "source_refs": cell.get("source_refs", []),
        "profile_ids": cell.get("profile_ids", []),
        "source_chain_binding_sha256": cell.get(
            "source_chain_binding_sha256"
        ),
        "derivation_record_kind": cell.get(
            "derivation_record_kind"
        ),
        "derivation_record_identity": cell.get(
            "derivation_record_identity"
        ),
        "program_generated_record_sha256": cell.get(
            "program_generated_record_sha256"
        ),
        "program_generated_record_binding_sha256": cell.get(
            "program_generated_record_binding_sha256"
        ),
    })
    return (
        cell.get("delivery_scope") == "all_equipment_fields"
        and cell.get("cell_sha256") == expected
    )


def all_equipment_fields_hash_check(row: dict[str, Any]) -> bool:
    cells = [
        cell
        for cell in row.get("all_equipment_fields", [])
        if isinstance(cell, dict)
    ]
    return (
        all(delivery_cell_hash_check(row, cell) for cell in cells)
        and row.get("all_equipment_fields_sha256")
        == canonical_sha256([cell.get("cell_sha256") for cell in cells])
    )


def row_hash_check(row: dict[str, Any]) -> bool:
    formal = row.get("formal_readiness_gate", {})
    formal_blockers = sorted(set([
        *formal.get("blocking_fields", []),
        *formal.get("blocking_reasons", []),
    ]))
    payload = {
        "input_sha256": row.get("source_input_sha256"),
        "record_kind": row.get("record_kind"),
        "aspen_source_binding": row.get("source_chain_binding", {}),
        "authority_table_id": row.get("authority_table_id"),
        "authority_source": row.get("authority_source", {}),
        "authority_cell_hashes": [
            cell.get("cell_sha256") for cell in row.get("authority_cells", [])
        ],
        "all_equipment_fields_sha256": row.get(
            "all_equipment_fields_sha256"
        ),
        "information_coverage_state": row.get("authority_information_coverage", {}).get("state"),
        "customer_information_state": row.get(
            "customer_information_coverage", {}
        ).get("state"),
        "specificity_state": row.get("selection_specificity_gate", {}).get("state"),
        "formal_gate_blockers": formal_blockers,
    }
    if row.get("authority_table_id") is not None:
        payload["authority_full_field_coverage_state"] = row.get(
            "authority_full_field_coverage", {}
        ).get("state")
    expected = canonical_sha256(payload)
    return row.get("authority_row_sha256") == expected


def table_hash_check(table: dict[str, Any]) -> bool:
    expected = canonical_sha256({
        "schema": "equipment-overview-table-v1",
        "authority_contract": table.get("authority_contract"),
        "columns": table.get("columns", []),
        "profile_authority": table.get("profile_authority", {}),
        "row_hashes": [row.get("authority_row_sha256") for row in table.get("rows", [])],
        "record_kinds": [row.get("record_kind") for row in table.get("rows", [])],
    })
    return table.get("table_sha256") == expected


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def _cell_scope_pairs(row: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    pairs: list[tuple[str, dict[str, Any]]] = []
    for scope in ("authority_cells", "all_equipment_fields"):
        pairs.extend(
            (scope, cell)
            for cell in row.get(scope, [])
            if isinstance(cell, dict)
        )
    return pairs


def _generic_selection_reasons(row: dict[str, Any]) -> list[str]:
    specificity = (
        row.get("selection_specificity_gate")
        if isinstance(row.get("selection_specificity_gate"), dict)
        else {}
    )
    identity = (
        specificity.get("selection_identity")
        if isinstance(specificity.get("selection_identity"), dict)
        else {}
    )
    recommended_type = str(
        identity.get("recommended_type") or row.get("equipment_type") or ""
    ).strip()
    designation = str(
        identity.get("model_or_specification")
        or row.get("model_or_specification")
        or ""
    ).strip()
    reasons: list[str] = []
    if not recommended_type:
        reasons.append("CONCRETE_TERMINAL_TYPE_EMPTY")
    if not designation:
        reasons.append("DETAILED_MODEL_OR_ENGINEERING_DESIGNATION_EMPTY")
    for field_name, value in (
        ("recommended_type", recommended_type),
        ("model_or_specification", designation),
    ):
        folded = value.casefold()
        for token in NONCONCRETE_SELECTION_TOKENS:
            if token.casefold() in folded:
                reasons.append(
                    f"GENERIC_SELECTION_TOKEN:{field_name}:{token}"
                )
    if identity.get("concrete_terminal_type") is not True:
        reasons.append("CONCRETE_TERMINAL_TYPE_NOT_ESTABLISHED")
    if identity.get("detailed_designation") is not True:
        reasons.append("DETAILED_DESIGNATION_NOT_ESTABLISHED")
    if identity.get("candidate_validation_blockers"):
        reasons.append("SELECTION_CANDIDATE_VALIDATION_BLOCKERS_PRESENT")
    if identity.get("designation_detail_blockers"):
        reasons.append("DESIGNATION_DETAIL_BLOCKERS_PRESENT")
    return sorted(set(reasons))


def _open_gate_metadata_errors(cell: dict[str, Any]) -> list[str]:
    if str(cell.get("state") or "").upper() != EXPLICIT_OPEN_GATE_STATE:
        return []
    source = cell.get("source") if isinstance(cell.get("source"), dict) else {}
    open_gate = (
        cell.get("open_gate")
        if isinstance(cell.get("open_gate"), dict)
        else {}
    )
    errors: list[str] = []
    display_value = str(cell.get("display_value") or "").strip()
    if not display_value.upper().startswith("OPEN"):
        errors.append("OPEN_DISPLAY_VALUE_MISSING")
    if not _present(open_gate.get("reason")):
        errors.append("OPEN_REASON_MISSING")
    if not _present(open_gate.get("required_action")):
        errors.append("OPEN_REQUIRED_ACTION_MISSING")
    if not _present(source.get("reason")):
        errors.append("OPEN_SOURCE_REASON_MISSING")
    if not _present(source.get("required_action")):
        errors.append("OPEN_SOURCE_REQUIRED_ACTION_MISSING")
    if source.get("formal_design_evidence") is not False:
        errors.append("OPEN_FORMAL_DESIGN_EVIDENCE_NOT_FALSE")
    if source.get("placeholder_is_engineering_value") is not False:
        errors.append("OPEN_PLACEHOLDER_ENGINEERING_VALUE_BOUNDARY_MISSING")

    cell_cap = str(cell.get("promotion_cap") or "").upper()
    source_cap = str(source.get("promotion_cap") or "").upper()
    gate_cap = str(open_gate.get("promotion_cap") or "").upper()
    effective_evidence_class = str(
        source.get("evidence_class")
        or source.get("field_evidence_class")
        or ""
    ).upper()
    # OPEN is the machine representation of an unknown formal value.  Keeping
    # explanatory/screening tokens in ``value`` lets downstream consumers
    # misparse them as engineering data, so all explanations belong in
    # display/source/open_gate and the machine value must remain null.
    if cell.get("value") is not None:
        errors.append("OPEN_MACHINE_VALUE_NOT_NULL")
    if (
        cell_cap != "NOT_PROMOTABLE"
        or source_cap != "NOT_PROMOTABLE"
        or gate_cap != "NOT_PROMOTABLE"
    ):
        errors.append("OPEN_PROMOTION_CAP_NOT_NOT_PROMOTABLE")
    if effective_evidence_class != "U":
        errors.append("OPEN_EVIDENCE_CLASS_NOT_U")
    if str(source.get("original_state") or "").upper() in RAW_CUSTOMER_GAP_STATES:
        if cell.get("value") is not None:
            errors.append("NORMALISED_RAW_GAP_OPEN_VALUE_NOT_NULL")
    return sorted(set(errors))


def _full_field_coverage_errors(
    row: dict[str, Any],
    expected_profile_field_ids: set[str] | None = None,
) -> list[str]:
    coverage = (
        row.get("customer_full_field_coverage")
        if isinstance(row.get("customer_full_field_coverage"), dict)
        else {}
    )
    errors: list[str] = []
    if coverage.get("state") != "PASS":
        errors.append("CUSTOMER_FULL_FIELD_COVERAGE_NOT_PASS")
    required = coverage.get("required")
    emitted = coverage.get("emitted")
    represented = coverage.get("represented")
    if not (
        isinstance(required, int)
        and required == emitted
        and required == represented
    ):
        errors.append("CUSTOMER_PROFILE_FIELD_COUNT_MISMATCH")
    if coverage.get("blocking_reasons"):
        errors.append("CUSTOMER_FULL_FIELD_BLOCKING_REASONS_PRESENT")
    if coverage.get("missing_cell_ids"):
        errors.append("CUSTOMER_PROFILE_FIELDS_NOT_EMITTED")
    if coverage.get("unrepresented_field_ids"):
        errors.append("CUSTOMER_PROFILE_FIELDS_UNREPRESENTED")
    represented_ids = [
        str(field_id)
        for key in (
            "value_fields",
            "explicit_open_fields",
            "not_applicable_fields",
        )
        for field_id in coverage.get(key, [])
    ]
    if len(represented_ids) != len(set(represented_ids)):
        errors.append("CUSTOMER_PROFILE_FIELD_REPRESENTATION_DUPLICATED")
    if isinstance(required, int) and len(represented_ids) != required:
        errors.append("CUSTOMER_PROFILE_FIELD_REPRESENTATION_COUNT_MISMATCH")
    emitted_ids = {
        str(cell.get("field_id"))
        for cell in row.get("all_equipment_fields", [])
        if isinstance(cell, dict)
    }
    if not set(represented_ids).issubset(emitted_ids):
        errors.append("CUSTOMER_PROFILE_FIELD_NOT_IN_ALL_EQUIPMENT_FIELDS")
    if expected_profile_field_ids is not None:
        represented_set = set(represented_ids)
        if represented_set != expected_profile_field_ids:
            errors.append(
                "CUSTOMER_PROFILE_CONTRACT_FIELD_SET_MISMATCH"
            )
        if (
            isinstance(required, int)
            and required != len(expected_profile_field_ids)
        ):
            errors.append(
                "CUSTOMER_PROFILE_CONTRACT_FIELD_COUNT_MISMATCH"
            )
    return sorted(set(errors))


def _selection_screening_gate_valid(cell: dict[str, Any]) -> bool:
    """Accept a visible preliminary value without mistaking it for closure.

    A concrete type/designation can remain usable for preliminary selection
    even when one adjacent candidate field (for example the pressure-
    temperature rating) is a J-class screening value.  Such a value is not an
    unknown, so it need not be converted to ``value=None``; it must still carry
    a visible open-gate reason/action and a TYPE_SCREENING-or-lower cap.
    """

    source = cell.get("source") if isinstance(cell.get("source"), dict) else {}
    open_gate = (
        cell.get("open_gate")
        if isinstance(cell.get("open_gate"), dict)
        else {}
    )
    state = str(cell.get("state") or "").upper()
    cell_cap = str(cell.get("promotion_cap") or "").upper()
    gate_cap = str(open_gate.get("promotion_cap") or "").upper()
    evidence_class = str(
        source.get("evidence_class")
        or source.get("field_evidence_class")
        or ""
    ).upper()
    preliminary_state = (
        state.startswith("DEFAULTED")
        or state.startswith("PROVISIONAL")
        or state.startswith("PRELIMINARY")
        or state.startswith("CONDITIONALLY")
        or state.startswith("RECOMMENDED")
    )
    return (
        _present(cell.get("value"))
        and state not in RAW_CUSTOMER_GAP_STATES
        and state != EXPLICIT_OPEN_GATE_STATE
        and preliminary_state
        and cell_cap in {"TYPE_SCREENING", "NOT_PROMOTABLE"}
        and gate_cap in {"TYPE_SCREENING", "NOT_PROMOTABLE"}
        and evidence_class in {"J", "U"}
        and _present(open_gate.get("reason"))
        and _present(open_gate.get("required_action"))
    )


def _false_pass_errors(
    row: dict[str, Any],
    explicit_open_field_ids: list[str],
) -> list[str]:
    customer_information = (
        row.get("customer_information_coverage")
        if isinstance(row.get("customer_information_coverage"), dict)
        else {}
    )
    authority_information = (
        row.get("authority_information_coverage")
        if isinstance(row.get("authority_information_coverage"), dict)
        else {}
    )
    formal = (
        row.get("formal_readiness_gate")
        if isinstance(row.get("formal_readiness_gate"), dict)
        else {}
    )
    errors: list[str] = []
    has_open = bool(explicit_open_field_ids)
    customer_state = str(customer_information.get("state") or "")
    authority_state = str(authority_information.get("state") or "")
    formal_state = str(formal.get("state") or "")
    if has_open:
        if customer_state != PROVISIONAL_INFORMATION_STATE:
            errors.append("FALSE_CUSTOMER_INFORMATION_PASS_WITH_OPEN_GAPS")
        if authority_state not in {
            PROVISIONAL_INFORMATION_STATE,
            "NOT_APPLICABLE",
        }:
            errors.append("FALSE_AUTHORITY_INFORMATION_PASS_WITH_OPEN_GAPS")
        if formal_state != "BLOCKED":
            errors.append("FALSE_FORMAL_READINESS_PASS_WITH_OPEN_GAPS")
    else:
        if customer_state == PROVISIONAL_INFORMATION_STATE:
            errors.append("CUSTOMER_PROVISIONAL_STATE_WITHOUT_EXPLICIT_OPEN_CELL")
        if authority_state == PROVISIONAL_INFORMATION_STATE:
            errors.append("AUTHORITY_PROVISIONAL_STATE_WITHOUT_EXPLICIT_OPEN_CELL")
    if customer_state not in {"PASS", PROVISIONAL_INFORMATION_STATE}:
        errors.append("CUSTOMER_INFORMATION_STATE_INVALID")
    if authority_state not in {
        "PASS",
        PROVISIONAL_INFORMATION_STATE,
        "NOT_APPLICABLE",
    }:
        errors.append("AUTHORITY_INFORMATION_STATE_INVALID")
    if formal_state not in {"PASS", "BLOCKED", "NOT_APPLICABLE"}:
        errors.append("FORMAL_READINESS_STATE_INVALID")
    return sorted(set(errors))


def audit_case(
    case_name: str,
    result_path: Path,
    output_dir: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    document = json.loads(result_path.read_text(encoding="utf-8"))
    table = customer_delivery.build_equipment_overview_table(document)
    case_table_path = output_dir / f"{case_name}_PROGRAM_GENERATED_OVERVIEW.json"
    case_table_path.write_text(
        json.dumps(table, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    source_profile = physical_source_profile(document)
    expected_equipment = int(source_profile["equipment_count"])
    expected_piping = int(source_profile["piping_count"])
    logic_count = int(source_profile["logic_count"])
    alias_count = int(source_profile["alias_count"])
    profile_contract = customer_delivery.load_customer_output_profiles()
    profile_fields_by_id = {
        str(profile.get("profile_id")): {
            str(field.get("field_id"))
            for field in profile.get("fields", [])
            if isinstance(field, dict) and _present(field.get("field_id"))
        }
        for profile in profile_contract.get("profiles", [])
        if isinstance(profile, dict) and _present(profile.get("profile_id"))
    }
    row_audits: list[dict[str, Any]] = []
    for row in table.get("rows", []):
        cells = [
            cell for cell in row.get("authority_cells", [])
            if isinstance(cell, dict)
        ]
        all_equipment_cells = [
            cell for cell in row.get("all_equipment_fields", [])
            if isinstance(cell, dict)
        ]
        cell_hashes_valid = all(cell_hash_check(row, cell) for cell in cells)
        all_equipment_fields_hash_valid = all_equipment_fields_hash_check(row)
        source_binding_valid = (
            row.get("source_chain_binding_sha256")
            == canonical_sha256(row.get("source_chain_binding", {}))
        )
        generated_contract_valid = (
            row.get("program_generated") is True
            and row.get("manual_postprocessing") is False
            and all(
                cell.get("program_generated") is True
                and cell.get("manual_postprocessing") is False
                for cell in cells
            )
            and all(
                cell.get("program_generated") is True
                and cell.get("manual_postprocessing") is False
                for cell in all_equipment_cells
            )
        )
        authority_structural = (
            row.get("authority_structural_completeness")
            if isinstance(row.get("authority_structural_completeness"), dict)
            else {}
        )
        authority_full_coverage = (
            row.get("authority_full_field_coverage")
            if isinstance(row.get("authority_full_field_coverage"), dict)
            else {}
        )
        information = (
            row.get("authority_information_coverage")
            if isinstance(row.get("authority_information_coverage"), dict)
            else {}
        )
        customer_information = (
            row.get("customer_information_coverage")
            if isinstance(row.get("customer_information_coverage"), dict)
            else {}
        )
        specificity = (
            row.get("selection_specificity_gate")
            if isinstance(row.get("selection_specificity_gate"), dict)
            else {}
        )
        formal = (
            row.get("formal_readiness_gate")
            if isinstance(row.get("formal_readiness_gate"), dict)
            else {}
        )

        raw_gap_occurrences = sorted({
            f"{scope}:{cell.get('field_id')}:{str(cell.get('state') or '').upper()}"
            for scope, cell in _cell_scope_pairs(row)
            if str(cell.get("state") or "").upper()
            in RAW_CUSTOMER_GAP_STATES
        })
        open_occurrences = [
            (scope, cell)
            for scope, cell in _cell_scope_pairs(row)
            if str(cell.get("state") or "").upper()
            == EXPLICIT_OPEN_GATE_STATE
        ]
        explicit_open_field_ids = sorted({
            str(cell.get("field_id"))
            for _, cell in open_occurrences
        })
        strict_unknown_open_field_ids = sorted({
            str(cell.get("field_id"))
            for _, cell in open_occurrences
            if cell.get("value") is None
        })
        non_null_open_machine_value_field_ids = sorted({
            str(cell.get("field_id"))
            for _, cell in open_occurrences
            if cell.get("value") is not None
        })
        open_metadata_errors = sorted({
            f"{scope}:{cell.get('field_id')}:{error}"
            for scope, cell in open_occurrences
            for error in _open_gate_metadata_errors(cell)
        })
        row_profile_ids = [
            str(profile_id)
            for profile_id in row.get("profile_ids", [])
        ]
        unknown_profile_ids = sorted(
            set(row_profile_ids) - set(profile_fields_by_id)
        )
        expected_profile_field_ids = set().union(*(
            profile_fields_by_id.get(profile_id, set())
            for profile_id in row_profile_ids
        ))
        full_field_coverage_errors = _full_field_coverage_errors(
            row,
            expected_profile_field_ids,
        )
        if unknown_profile_ids:
            full_field_coverage_errors.append(
                "CUSTOMER_PROFILE_ID_UNKNOWN_TO_AUDIT_CONTRACT"
            )
        if not row_profile_ids:
            full_field_coverage_errors.append(
                "CUSTOMER_PROFILE_ID_NOT_EMITTED"
            )
        full_field_coverage_errors = sorted(
            set(full_field_coverage_errors)
        )
        generic_selection_reasons = _generic_selection_reasons(row)
        false_pass_errors = _false_pass_errors(
            row,
            explicit_open_field_ids,
        )

        specificity_state = str(specificity.get("state") or "")
        specificity_blocking_fields = sorted({
            str(field)
            for field in specificity.get("blocking_fields", [])
        })
        all_equipment_cells_by_id = {
            str(cell.get("field_id")): cell
            for cell in all_equipment_cells
        }
        specificity_screening_gate_fields = sorted(
            field_id
            for field_id in specificity_blocking_fields
            if _selection_screening_gate_valid(
                all_equipment_cells_by_id.get(field_id, {})
            )
        )
        unresolved_nonopen_specificity_fields = sorted(
            set(specificity_blocking_fields)
            - set(explicit_open_field_ids)
            - set(specificity_screening_gate_fields)
        )
        specificity_contract_errors: list[str] = []
        if specificity_state not in {"PASS", "BLOCKED"}:
            specificity_contract_errors.append(
                "SELECTION_SPECIFICITY_STATE_INVALID"
            )
        if (
            specificity_state == "PASS"
            and (
                specificity_blocking_fields
                or specificity.get("blocking_reasons")
            )
        ):
            specificity_contract_errors.append(
                "FALSE_SELECTION_SPECIFICITY_PASS_WITH_BLOCKERS"
            )
        if unresolved_nonopen_specificity_fields:
            specificity_contract_errors.append(
                "SPECIFICITY_BLOCKER_NOT_EXPLICIT_OPEN"
            )

        authority_structure_valid = (
            authority_structural.get("state") == "PASS"
            and authority_full_coverage.get("state") == "PASS"
            and authority_structural.get("required") == len(cells)
            and authority_structural.get("emitted") == len(cells)
            and authority_structural.get("unique") == len(cells)
            and not authority_structural.get("blocking_reasons")
            and not authority_full_coverage.get("blocking_reasons")
            and not authority_full_coverage.get("missing_cell_ids")
            and not authority_full_coverage.get("unrepresented_field_ids")
        )
        row_hash_valid = row_hash_check(row)
        row_structure_valid = (
            authority_structure_valid
            and generated_contract_valid
            and cell_hashes_valid
            and all_equipment_fields_hash_valid
            and source_binding_valid
            and row_hash_valid
            and not full_field_coverage_errors
        )
        identity_valid = (
            not generic_selection_reasons
            and not specificity_contract_errors
        )
        information_contract_valid = (
            not raw_gap_occurrences
            and not open_metadata_errors
            and not false_pass_errors
        )
        acceptance_failure_reasons: list[str] = []
        if not authority_structure_valid:
            acceptance_failure_reasons.append(
                "AUTHORITY_PROFILE_STRUCTURE_OR_COVERAGE_INVALID"
            )
        if not generated_contract_valid:
            acceptance_failure_reasons.append(
                "PROGRAM_GENERATION_CONTRACT_INVALID"
            )
        if not cell_hashes_valid:
            acceptance_failure_reasons.append(
                "AUTHORITY_CELL_HASH_INVALID"
            )
        if not all_equipment_fields_hash_valid:
            acceptance_failure_reasons.append(
                "ALL_EQUIPMENT_FIELDS_HASH_INVALID"
            )
        if not source_binding_valid:
            acceptance_failure_reasons.append(
                "SOURCE_CHAIN_BINDING_HASH_INVALID"
            )
        if not row_hash_valid:
            acceptance_failure_reasons.append("AUTHORITY_ROW_HASH_INVALID")
        acceptance_failure_reasons.extend(full_field_coverage_errors)
        acceptance_failure_reasons.extend(generic_selection_reasons)
        acceptance_failure_reasons.extend(specificity_contract_errors)
        if raw_gap_occurrences:
            acceptance_failure_reasons.append(
                "RAW_CUSTOMER_GAP_STATE_EXPOSED"
            )
        if open_metadata_errors:
            acceptance_failure_reasons.append(
                "EXPLICIT_OPEN_GATE_METADATA_INVALID"
            )
        acceptance_failure_reasons.extend(false_pass_errors)
        acceptance_failure_reasons = sorted(
            set(acceptance_failure_reasons)
        )
        row_accepted = not acceptance_failure_reasons
        row_has_explicit_gaps = (
            bool(explicit_open_field_ids)
            or information.get("state") == PROVISIONAL_INFORMATION_STATE
            or customer_information.get("state")
            == PROVISIONAL_INFORMATION_STATE
            or formal.get("state") == "BLOCKED"
            or specificity_state == "BLOCKED"
        )
        row_status = (
            "FAIL"
            if not row_accepted
            else "PASS_WITH_EXPLICIT_OPEN_GAPS"
            if row_has_explicit_gaps
            else "PASS"
        )
        combined_information_blockers = sorted(set([
            *information.get("blocking_fields", []),
            *customer_information.get("blocking_fields", []),
        ]))
        row_audits.append({
            "case": case_name,
            "equipment_key": row.get("equipment_key"),
            "equipment_tag": row.get("equipment_tag"),
            "record_kind": row.get("record_kind"),
            "source_input_sha256": row.get("source_input_sha256"),
            "family_ids": row.get("family_ids", []),
            "authority_table_id": row.get("authority_table_id"),
            "authority_cell_count": len(cells),
            "authority_required_count": authority_structural.get("required"),
            "structural_state": authority_structural.get("state"),
            "authority_full_field_coverage_state": (
                authority_full_coverage.get("state")
            ),
            "customer_full_field_coverage_state": row.get(
                "customer_full_field_coverage", {}
            ).get("state"),
            "customer_profile_required_count": row.get(
                "customer_full_field_coverage", {}
            ).get("required"),
            "customer_profile_emitted_count": row.get(
                "customer_full_field_coverage", {}
            ).get("emitted"),
            "customer_profile_represented_count": row.get(
                "customer_full_field_coverage", {}
            ).get("represented"),
            "expected_customer_profile_field_count": len(
                expected_profile_field_ids
            ),
            "unknown_customer_profile_ids": unknown_profile_ids,
            "information_coverage_state": (
                "PASS_WITH_EXPLICIT_OPEN_GAPS"
                if row_has_explicit_gaps
                else "PASS"
            ),
            "authority_information_coverage_state": information.get("state"),
            "customer_information_coverage_state": customer_information.get("state"),
            "information_blocking_fields": combined_information_blockers,
            "explicit_open_gate_fields": explicit_open_field_ids,
            "strict_unknown_open_fields": strict_unknown_open_field_ids,
            "non_null_open_machine_value_fields": (
                non_null_open_machine_value_field_ids
            ),
            "raw_gap_occurrences": raw_gap_occurrences,
            "open_metadata_errors": open_metadata_errors,
            "customer_full_field_coverage_errors": (
                full_field_coverage_errors
            ),
            "specificity_state": specificity_state,
            "specificity_blocking_fields": specificity_blocking_fields,
            "specificity_blocking_reasons": specificity.get("blocking_reasons", []),
            "specificity_screening_gate_fields": (
                specificity_screening_gate_fields
            ),
            "unresolved_nonopen_specificity_fields": (
                unresolved_nonopen_specificity_fields
            ),
            "generic_selection_reasons": generic_selection_reasons,
            "specificity_contract_errors": specificity_contract_errors,
            "formal_state": formal.get("state"),
            "formal_blocking_fields": formal.get("blocking_fields", []),
            "formal_blocking_reasons": formal.get("blocking_reasons", []),
            "recommended_type": specificity.get("selection_identity", {}).get("recommended_type"),
            "model_or_specification": specificity.get("selection_identity", {}).get("model_or_specification"),
            "row_acceptance_status": row_status,
            "row_acceptance_failure_reasons": (
                acceptance_failure_reasons
            ),
            "row_structure_valid": row_structure_valid,
            "selection_identity_valid": identity_valid,
            "information_contract_valid": information_contract_valid,
            "program_generation_contract_valid": generated_contract_valid,
            "cell_hashes_valid": cell_hashes_valid,
            "all_equipment_fields_hash_valid": all_equipment_fields_hash_valid,
            "source_binding_hash_valid": source_binding_valid,
            "row_hash_valid": row_hash_valid,
            "authority_row_sha256": row.get("authority_row_sha256"),
        })

    expected_rows = expected_equipment + expected_piping
    table_rows = [
        row for row in table.get("rows", []) if isinstance(row, dict)
    ]
    expected_bindings = Counter(
        (str(kind), str(source_sha or "").upper())
        for kind, source_sha in source_profile["expected_bindings"]
    )
    actual_bindings = Counter(
        (
            str(row.get("record_kind") or ""),
            str(row.get("source_input_sha256") or "").upper(),
        )
        for row in table_rows
    )
    grain_failure_reasons: list[str] = []
    if table.get("row_count") != expected_rows:
        grain_failure_reasons.append("DECLARED_ROW_COUNT_MISMATCH")
    if len(table_rows) != expected_rows:
        grain_failure_reasons.append("EMITTED_ROW_COUNT_MISMATCH")
    if (
        len({row.get("equipment_key") for row in table_rows})
        != expected_rows
    ):
        grain_failure_reasons.append("EQUIPMENT_KEY_GRAIN_NOT_UNIQUE")
    if (
        sum(row.get("record_kind") == "equipment" for row in table_rows)
        != expected_equipment
    ):
        grain_failure_reasons.append(
            "PHYSICAL_EQUIPMENT_RECORD_KIND_COUNT_MISMATCH"
        )
    if (
        sum(row.get("record_kind") == "piping" for row in table_rows)
        != expected_piping
    ):
        grain_failure_reasons.append(
            "PHYSICAL_PIPING_RECORD_KIND_COUNT_MISMATCH"
        )
    if any(not source_sha for _, source_sha in expected_bindings):
        grain_failure_reasons.append(
            "PHYSICAL_SOURCE_MATCH_INPUT_SHA256_MISSING"
        )
    if actual_bindings != expected_bindings:
        grain_failure_reasons.append(
            "PHYSICAL_SOURCE_TO_OVERVIEW_BINDING_MISMATCH"
        )
    grain_failure_reasons = sorted(set(grain_failure_reasons))
    grain_valid = not grain_failure_reasons
    table_contract_valid = (
        table.get("program_generated") is True
        and table.get("manual_postprocessing") is False
        and table_hash_check(table)
        and table.get("row_hashes")
        == [row.get("authority_row_sha256") for row in table_rows]
    )
    structural_pass = (
        grain_valid
        and table_contract_valid
        and all(
            row["row_structure_valid"]
            for row in row_audits
        )
    )
    information_contract_pass = structural_pass and all(
        row["information_contract_valid"] for row in row_audits
    )
    specificity_pass = structural_pass and all(
        row["selection_identity_valid"] for row in row_audits
    )
    acceptance_pass = (
        structural_pass
        and information_contract_pass
        and specificity_pass
        and all(
            row["row_acceptance_status"] != "FAIL"
            for row in row_audits
        )
    )
    formal_pass = acceptance_pass and all(
        row["formal_state"] == "PASS" for row in row_audits
    )
    explicit_open_field_count = sum(
        len(row["explicit_open_gate_fields"]) for row in row_audits
    )
    has_explicit_open_gaps = (
        explicit_open_field_count > 0
        or any(
            row["row_acceptance_status"]
            == "PASS_WITH_EXPLICIT_OPEN_GAPS"
            for row in row_audits
        )
    )
    case_status = (
        "FAIL"
        if not acceptance_pass
        else "PASS_WITH_EXPLICIT_OPEN_GAPS"
        if has_explicit_open_gaps
        else "PASS"
    )
    case_report = {
        "case": case_name,
        "status": case_status,
        "source_result_path": str(result_path),
        "source_result_sha256": sha256_file(result_path),
        "source_export_sha256": document.get("source_export_sha256"),
        "source_case_evidence": document.get("source_case_evidence", {}),
        "engine_version": document.get("engine_version"),
        "aspen_run_gate": document.get("aspen_run_gate", {}),
        "expected_physical_equipment_rows": expected_equipment,
        "expected_piping_rows": expected_piping,
        "logic_node_count": logic_count,
        "excluded_endpoint_state_alias_count": alias_count,
        "overview_row_count": table.get("row_count"),
        "grain_valid": grain_valid,
        "grain_failure_reasons": grain_failure_reasons,
        "physical_source_binding_valid": (
            actual_bindings == expected_bindings
        ),
        "table_program_generation_contract_valid": table_contract_valid,
        "table_hash_valid": table_hash_check(table),
        "table_sha256": table.get("table_sha256"),
        "structural_status": "PASS" if structural_pass else "FAIL",
        "information_coverage_status": (
            "FAIL"
            if not information_contract_pass
            else "PASS_WITH_EXPLICIT_OPEN_GAPS"
            if has_explicit_open_gaps
            else "PASS"
        ),
        "specificity_status": (
            "FAIL"
            if not specificity_pass
            else "PASS_WITH_EXPLICIT_OPEN_GAPS"
            if any(row["specificity_state"] == "BLOCKED" for row in row_audits)
            else "PASS"
        ),
        "formal_readiness_status": "PASS" if formal_pass else "BLOCKED",
        "accepted_row_count": sum(
            row["row_acceptance_status"] != "FAIL"
            for row in row_audits
        ),
        "failed_row_count": sum(
            row["row_acceptance_status"] == "FAIL"
            for row in row_audits
        ),
        "explicit_open_field_count": explicit_open_field_count,
        "strict_unknown_open_field_count": sum(
            len(row["strict_unknown_open_fields"])
            for row in row_audits
        ),
        "non_null_open_machine_value_field_count": sum(
            len(row["non_null_open_machine_value_fields"])
            for row in row_audits
        ),
        "raw_gap_occurrence_count": sum(
            len(row["raw_gap_occurrences"]) for row in row_audits
        ),
        "open_metadata_error_count": sum(
            len(row["open_metadata_errors"]) for row in row_audits
        ),
        "generic_selection_failure_count": sum(
            bool(row["generic_selection_reasons"])
            for row in row_audits
        ),
        "false_pass_error_count": sum(
            any(
                "FALSE_" in reason
                for reason in row["row_acceptance_failure_reasons"]
            )
            for row in row_audits
        ),
        "row_acceptance_failure_counts": dict(sorted(Counter(
            reason
            for row in row_audits
            for reason in row["row_acceptance_failure_reasons"]
        ).items())),
        "specificity_blocking_field_counts": dict(sorted(Counter(
            field
            for row in row_audits
            for field in row["specificity_blocking_fields"]
        ).items())),
        "information_blocking_field_counts": dict(sorted(Counter(
            field
            for row in row_audits
            for field in row["information_blocking_fields"]
        ).items())),
        "formal_blocking_field_counts": dict(sorted(Counter(
            field
            for row in row_audits
            for field in row["formal_blocking_fields"]
        ).items())),
        "authority_table_counts": dict(sorted(Counter(
            str(row["authority_table_id"]) for row in row_audits
        ).items())),
        "overview_path": str(case_table_path),
        "overview_sha256": sha256_file(case_table_path),
    }
    return case_report, row_audits


def write_reports(
    output_dir: Path,
    report: dict[str, Any],
    rows: list[dict[str, Any]],
) -> None:
    report_path = output_dir / "MULTI_BKP_AUTHORITY_OVERVIEW_GATE_REPORT.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    columns = [
        "case",
        "equipment_key",
        "equipment_tag",
        "record_kind",
        "source_input_sha256",
        "authority_table_id",
        "authority_cell_count",
        "authority_required_count",
        "structural_state",
        "authority_full_field_coverage_state",
        "customer_full_field_coverage_state",
        "customer_profile_required_count",
        "customer_profile_emitted_count",
        "customer_profile_represented_count",
        "expected_customer_profile_field_count",
        "unknown_customer_profile_ids",
        "information_coverage_state",
        "authority_information_coverage_state",
        "customer_information_coverage_state",
        "specificity_state",
        "formal_state",
        "recommended_type",
        "model_or_specification",
        "row_acceptance_status",
        "row_structure_valid",
        "selection_identity_valid",
        "information_contract_valid",
        "program_generation_contract_valid",
        "cell_hashes_valid",
        "all_equipment_fields_hash_valid",
        "source_binding_hash_valid",
        "row_hash_valid",
        "authority_row_sha256",
        "row_acceptance_failure_reasons",
        "generic_selection_reasons",
        "specificity_contract_errors",
        "specificity_blocking_fields",
        "specificity_blocking_reasons",
        "specificity_screening_gate_fields",
        "unresolved_nonopen_specificity_fields",
        "information_blocking_fields",
        "explicit_open_gate_fields",
        "strict_unknown_open_fields",
        "non_null_open_machine_value_fields",
        "raw_gap_occurrences",
        "open_metadata_errors",
        "customer_full_field_coverage_errors",
        "formal_blocking_fields",
        "formal_blocking_reasons",
    ]
    list_columns = {
        "row_acceptance_failure_reasons",
        "generic_selection_reasons",
        "specificity_contract_errors",
        "specificity_blocking_fields",
        "specificity_blocking_reasons",
        "specificity_screening_gate_fields",
        "unresolved_nonopen_specificity_fields",
        "information_blocking_fields",
        "explicit_open_gate_fields",
        "strict_unknown_open_fields",
        "non_null_open_machine_value_fields",
        "raw_gap_occurrences",
        "open_metadata_errors",
        "customer_full_field_coverage_errors",
        "unknown_customer_profile_ids",
        "formal_blocking_fields",
        "formal_blocking_reasons",
    }
    rows_path = output_dir / "MULTI_BKP_AUTHORITY_OVERVIEW_GATE_ROWS.csv"
    with rows_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=columns,
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            serialized = dict(row)
            for field in list_columns:
                serialized[field] = "|".join(
                    str(item) for item in row.get(field, [])
                )
            writer.writerow(serialized)

    lines = [
        "# 真实 Aspen BKP 设备选型一览表验收",
        "",
        f"- 第一阶段一览表验收：`{report['status']}`",
        f"- 结构、粒度与程序生成链：`{report['structural_status']}`",
        f"- 字段信息语义：`{report['information_coverage_status']}`",
        f"- 具体类型与工程规格：`{report['specificity_status']}`",
        f"- 正式设计放行：`{report['formal_readiness_status']}`",
        (
            f"- 案例：{report['passed_case_count']}/"
            f"{report['case_count']} 通过一览表验收"
        ),
        (
            f"- 物理客户行：{report['overview_row_count']}，其中设备 "
            f"{report['equipment_row_count']}、管线 "
            f"{report['piping_row_count']}；排除端点状态别名 "
            f"{report['excluded_endpoint_state_alias_count']}"
        ),
        (
            f"- 显式 OPEN 字段：{report['explicit_open_field_count']}；"
            f"原始缺口状态：{report['raw_gap_occurrence_count']}；"
            f"OPEN 元数据错误：{report['open_metadata_error_count']}"
        ),
        "",
        (
            "`PASS_WITH_EXPLICIT_OPEN_GAPS` 表示：每个物理设备/管线均有"
            "程序生成的具体类型和详细工程规格，全部客户字段均已出现；尚未"
            "取得的正式设计数据以 value=null、可见 display、原因、补充动作、"
            "U 级证据和 NOT_PROMOTABLE 上限的 OPEN 单元格公开呈现，因此"
            "不能解释为正式设计完整。"
        ),
        "",
        (
            "只有原始 MISSING/EXTERNAL_REQUIRED/NOT_EXPLICITLY_ADOPTED "
            "泄漏、OPEN 元数据不完整、泛型选型、虚假 PASS、物理行/哈希/"
            "粒度或程序生成链失败，才判定本验收 FAIL。"
        ),
        "",
        (
            "| BKP | 设备行 | 管线行 | 排除别名 | 结构链 | 字段信息 | "
            "具体选型 | 正式放行 | 结果 |"
        ),
        "| --- | ---: | ---: | ---: | --- | --- | --- | --- | --- |",
    ]
    for case in report["cases"]:
        lines.append(
            f"| {case['case']} | "
            f"{case['expected_physical_equipment_rows']} | "
            f"{case['expected_piping_rows']} | "
            f"{case['excluded_endpoint_state_alias_count']} | "
            f"{case['structural_status']} | "
            f"{case['information_coverage_status']} | "
            f"{case['specificity_status']} | "
            f"{case['formal_readiness_status']} | "
            f"{case['status']} |"
        )
    if report["row_acceptance_failure_counts"]:
        lines.extend(["", "## 一览表验收失败项", ""])
        for reason, count in report[
            "row_acceptance_failure_counts"
        ].items():
            lines.append(f"- `{reason}`：{count} 行")
    lines.extend([
        "",
        (
            "逐行证据见 `MULTI_BKP_AUTHORITY_OVERVIEW_GATE_ROWS.csv`；"
            "每个案例的完整程序生成一览表见同目录 "
            "`*_PROGRAM_GENERATED_OVERVIEW.json`。"
        ),
    ])
    (output_dir / "MULTI_BKP_AUTHORITY_OVERVIEW_GATE_REPORT.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit program-generated customer overview rows for real Aspen "
            "derivation results, accepting honest explicit OPEN gates without "
            "claiming formal completeness."
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
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    case_reports: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    labels: set[str] = set()
    for label, path in args.case:
        if label in labels:
            raise SystemExit(f"Duplicate case label: {label}")
        labels.add(label)
        case_report, case_rows = audit_case(label, path, output_dir)
        case_reports.append(case_report)
        rows.extend(case_rows)

    expected_physical_rows = sum(
        int(case["expected_physical_equipment_rows"])
        + int(case["expected_piping_rows"])
        for case in case_reports
    )
    stage1_suite_contract_applicable = labels == STAGE1_REAL_CASE_LABELS
    stage1_suite_row_count_valid = (
        not stage1_suite_contract_applicable
        or (
            expected_physical_rows
            == STAGE1_REAL_CASE_EXPECTED_PHYSICAL_ROWS
            and len(rows) == STAGE1_REAL_CASE_EXPECTED_PHYSICAL_ROWS
        )
    )
    structural_pass = (
        stage1_suite_row_count_valid
        and all(
            case["structural_status"] == "PASS"
            for case in case_reports
        )
    )
    information_pass = structural_pass and all(
        case["information_coverage_status"] != "FAIL"
        for case in case_reports
    )
    specificity_pass = structural_pass and all(
        case["specificity_status"] != "FAIL"
        for case in case_reports
    )
    acceptance_pass = (
        information_pass
        and specificity_pass
        and all(case["status"] != "FAIL" for case in case_reports)
    )
    has_explicit_open_gaps = any(
        case["status"] == "PASS_WITH_EXPLICIT_OPEN_GAPS"
        for case in case_reports
    )
    formal_pass = acceptance_pass and all(
        case["formal_readiness_status"] == "PASS"
        for case in case_reports
    )
    status = (
        "FAIL"
        if not acceptance_pass
        else "PASS_WITH_EXPLICIT_OPEN_GAPS"
        if has_explicit_open_gaps
        else "PASS"
    )
    report = {
        "schema": SCHEMA,
        "status": status,
        "structural_status": "PASS" if structural_pass else "FAIL",
        "information_coverage_status": (
            "FAIL"
            if not information_pass
            else "PASS_WITH_EXPLICIT_OPEN_GAPS"
            if has_explicit_open_gaps
            else "PASS"
        ),
        "specificity_status": (
            "FAIL"
            if not specificity_pass
            else "PASS_WITH_EXPLICIT_OPEN_GAPS"
            if any(
                case["specificity_status"]
                == "PASS_WITH_EXPLICIT_OPEN_GAPS"
                for case in case_reports
            )
            else "PASS"
        ),
        "formal_readiness_status": (
            "PASS" if formal_pass else "BLOCKED"
        ),
        "case_count": len(case_reports),
        "passed_case_count": sum(
            case["status"] != "FAIL" for case in case_reports
        ),
        "overview_row_count": len(rows),
        "expected_physical_row_count": expected_physical_rows,
        "equipment_row_count": sum(
            row["record_kind"] == "equipment" for row in rows
        ),
        "piping_row_count": sum(
            row["record_kind"] == "piping" for row in rows
        ),
        "excluded_endpoint_state_alias_count": sum(
            case["excluded_endpoint_state_alias_count"]
            for case in case_reports
        ),
        "accepted_row_count": sum(
            row["row_acceptance_status"] != "FAIL" for row in rows
        ),
        "failed_row_count": sum(
            row["row_acceptance_status"] == "FAIL" for row in rows
        ),
        "customer_full_field_coverage_pass_row_count": sum(
            row["customer_full_field_coverage_state"] == "PASS"
            for row in rows
        ),
        "explicit_open_field_count": sum(
            len(row["explicit_open_gate_fields"]) for row in rows
        ),
        "strict_unknown_open_field_count": sum(
            len(row["strict_unknown_open_fields"]) for row in rows
        ),
        "non_null_open_machine_value_field_count": sum(
            len(row["non_null_open_machine_value_fields"])
            for row in rows
        ),
        "raw_gap_occurrence_count": sum(
            len(row["raw_gap_occurrences"]) for row in rows
        ),
        "open_metadata_error_count": sum(
            len(row["open_metadata_errors"]) for row in rows
        ),
        "generic_selection_failure_count": sum(
            bool(row["generic_selection_reasons"]) for row in rows
        ),
        "false_pass_error_count": sum(
            any(
                "FALSE_" in reason
                for reason in row["row_acceptance_failure_reasons"]
            )
            for row in rows
        ),
        "stage1_real_case_suite_contract_applicable": (
            stage1_suite_contract_applicable
        ),
        "stage1_real_case_expected_physical_rows": (
            STAGE1_REAL_CASE_EXPECTED_PHYSICAL_ROWS
            if stage1_suite_contract_applicable
            else None
        ),
        "stage1_real_case_row_count_valid": (
            stage1_suite_row_count_valid
        ),
        "row_acceptance_failure_counts": dict(sorted(Counter(
            reason
            for row in rows
            for reason in row["row_acceptance_failure_reasons"]
        ).items())),
        "specificity_blocking_field_counts": dict(sorted(Counter(
            field
            for row in rows
            for field in row["specificity_blocking_fields"]
        ).items())),
        "information_blocking_field_counts": dict(sorted(Counter(
            field
            for row in rows
            for field in row["information_blocking_fields"]
        ).items())),
        "formal_blocking_field_counts": dict(sorted(Counter(
            field
            for row in rows
            for field in row["formal_blocking_fields"]
        ).items())),
        "acceptance_rule": (
            "Every physical equipment and pipe row must exist at exact source "
            "grain, be program-generated and hash-bound, expose every customer "
            "profile field, and carry a concrete non-generic type plus detailed "
            "designation. Unknown values are acceptable only as complete "
            "explicit OPEN gates with value=null, U evidence and a "
            "NOT_PROMOTABLE cap. Honest provisional information and BLOCKED "
            "formal readiness produce PASS_WITH_EXPLICIT_OPEN_GAPS, never a "
            "claim of formal completeness. Raw gap states, incomplete OPEN "
            "metadata, generic identities, false PASS states, or grain/hash "
            "failures produce FAIL."
        ),
        "manual_postprocessing_allowed": False,
        "cases": case_reports,
    }
    write_reports(output_dir, report, rows)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
