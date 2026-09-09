from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


LOGIC_MAPPING_STATUS = "NOT_APPLICABLE_SIMULATION_LOGIC_NODE"
COMPACT_AUTHORITY_SOURCE_FIELDS = (
    "kind",
    "evidence_class",
    "fallback_tier",
    "promotion_cap",
    "warning",
    "calculation_id",
    "authority_unit_transform",
    "basis",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def artifact(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def scalar_surface(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {
        str(key): item
        for key, item in value.items()
        if item is not None and isinstance(item, (str, int, float, bool))
    }


def diagnostic_counts(items: Any) -> dict[str, int]:
    if not isinstance(items, list):
        return {}
    counter = collections.Counter(
        str(item.get("code") or "UNKNOWN")
        for item in items
        if isinstance(item, Mapping)
    )
    return dict(sorted(counter.items()))


def compact_authority_cell(cell: Mapping[str, Any]) -> dict[str, Any]:
    source = cell.get("source") if isinstance(cell.get("source"), Mapping) else {}
    compact_source = {
        field: source.get(field)
        for field in COMPACT_AUTHORITY_SOURCE_FIELDS
        if source.get(field) is not None
    }
    return {
        "field_id": cell.get("field_id"),
        "label": cell.get("label"),
        "value": cell.get("value"),
        "unit": cell.get("unit"),
        "state": cell.get("state"),
        "source_field_id": cell.get("source_field_id"),
        "source": compact_source,
        "equation_chain": cell.get("equation_chain"),
    }


def compact_preliminary_completion_inputs(package: Mapping[str, Any]) -> list[dict[str, Any]]:
    compact_rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    groups = package.get("groups") if isinstance(package.get("groups"), list) else []
    for group in groups:
        if not isinstance(group, Mapping):
            continue
        rows = group.get("rows") if isinstance(group.get("rows"), list) else []
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            field_id = str(row.get("field_id") or "").strip()
            source = row.get("source") if isinstance(row.get("source"), Mapping) else {}
            if (
                not field_id
                or field_id in seen
                or row.get("state") not in {"DEFAULTED", "RECOMMENDED"}
                or source.get("evidence_class") != "J"
                or row.get("raw_value") is None
            ):
                continue
            seen.add(field_id)
            compact_rows.append({
                "field_id": field_id,
                "label": row.get("label"),
                "value": row.get("raw_value"),
                "unit": row.get("unit"),
                "state": row.get("state"),
                "role": row.get("role"),
                "group_id": row.get("group_id") or group.get("group_id"),
                "source": {
                    field: source.get(field)
                    for field in COMPACT_AUTHORITY_SOURCE_FIELDS
                    if source.get(field) is not None
                },
                "equation_chain": row.get("equation_chain"),
            })
    return compact_rows


def authority_row_index(rows: Sequence[Mapping[str, Any]] | None) -> dict[str, Mapping[str, Any]]:
    indexed: dict[str, Mapping[str, Any]] = {}
    for row in rows or []:
        if not isinstance(row, Mapping):
            continue
        for identity in (row.get("equipment_tag"), row.get("equipment_key")):
            token = str(identity or "").strip().casefold()
            if token:
                indexed[token] = row
    return indexed


def compact_equipment(
    item: Mapping[str, Any],
    index: int,
    authority_row: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    match = item.get("match_result") if isinstance(item.get("match_result"), Mapping) else {}
    decision = match.get("model_decision") if isinstance(match.get("model_decision"), Mapping) else {}
    recommendation = (
        match.get("model_recommendation")
        if isinstance(match.get("model_recommendation"), Mapping)
        else {}
    )
    terminal = (
        recommendation.get("terminal_selection")
        if isinstance(recommendation.get("terminal_selection"), Mapping)
        else {}
    )
    package = (
        match.get("design_parameter_package")
        if isinstance(match.get("design_parameter_package"), Mapping)
        else {}
    )
    calculations = match.get("calculations") if isinstance(match.get("calculations"), list) else []
    pending = match.get("calculation_pending") if isinstance(match.get("calculation_pending"), list) else []
    verification_missing = decision.get("verification_missing_fields")
    if not isinstance(verification_missing, list):
        verification_missing = []
    mapping_status = str(item.get("aspen_mapping_status") or "")
    match_status = str(match.get("status") or "")
    authority_row = authority_row or {}
    authority_cells = (
        authority_row.get("authority_cells")
        if isinstance(authority_row.get("authority_cells"), list)
        else []
    )
    return {
        "equipment_tag": item.get("equipment_tag"),
        "aspen_block_id": item.get("aspen_block_id"),
        "physical_equipment": not (
            mapping_status == LOGIC_MAPPING_STATUS or match_status == "NOT_APPLICABLE"
        ),
        "mapping_status": mapping_status,
        "match_status": match_status,
        "full_result_pointer": f"/equipment/{index}",
        "selection": {
            "recommended_type": recommendation.get("recommended_type") or terminal.get("recommended_type"),
            "terminal_selection_status": terminal.get("status"),
            "candidate_designation": (
                decision.get("generated_candidate_designation")
                or decision.get("generated_candidate_model")
                or decision.get("candidate_model")
            ),
            "model_status": decision.get("model_status"),
            "design_basis_status": decision.get("design_basis_status"),
            "promotion_cap": (
                (decision.get("machine_evidence_manifest") or {}).get("promotion_cap")
                if isinstance(decision.get("machine_evidence_manifest"), Mapping)
                else decision.get("formula_promotion_cap")
            ),
            "parameter_package_status": package.get("status"),
            "verification_missing_fields": [str(value) for value in verification_missing],
        },
        "canonical_inputs": scalar_surface(item.get("canonical_match_input")),
        "formula_chains": [
            {
                key: calculation.get(key)
                for key in (
                    "calculation_id",
                    "target_field",
                    "status",
                    "value",
                    "canonical_value",
                    "unit",
                    "equation_chain",
                    "evidence_status",
                    "adopted_as_canonical",
                )
                if calculation.get(key) is not None
            }
            for calculation in calculations
            if isinstance(calculation, Mapping)
        ],
        "calculation_pending": [
            scalar_surface(value) for value in pending if isinstance(value, Mapping)
        ],
        "preliminary_completion_inputs": compact_preliminary_completion_inputs(package),
        "diagnostic_counts": {
            "ignored_input": diagnostic_counts(item.get("ignored_input_diagnostics")),
            "ignored_parameters": diagnostic_counts(match.get("ignored_parameter_diagnostics")),
        },
        "authority_table_id": authority_row.get("authority_table_id"),
        "authority_completeness": authority_row.get("authority_completeness"),
        "authority_missing_fields": list(authority_row.get("authority_missing_fields") or []),
        "authority_cells": [
            compact_authority_cell(cell)
            for cell in authority_cells
            if isinstance(cell, Mapping)
        ],
    }


def flatten_gate_failures(gate: Mapping[str, Any]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    cases = gate.get("cases") if isinstance(gate.get("cases"), list) else []
    for case_index, case in enumerate(cases):
        if not isinstance(case, Mapping):
            continue
        case_failures = case.get("failures") if isinstance(case.get("failures"), list) else []
        for failure in case_failures:
            if not isinstance(failure, Mapping):
                continue
            compact = dict(failure)
            compact["gate_case_index"] = case_index
            failures.append(compact)
    return failures


def build_validation_packet(
    result: Mapping[str, Any],
    overview_gate: Mapping[str, Any],
    result_path: Path,
    gate_path: Path,
    *,
    authority_rows: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    equipment = result.get("equipment") if isinstance(result.get("equipment"), list) else []
    rows_by_identity = authority_row_index(authority_rows)
    summaries = [
        compact_equipment(
            item,
            index,
            rows_by_identity.get(str(item.get("equipment_tag") or "").strip().casefold())
            or rows_by_identity.get(str(item.get("aspen_block_id") or "").strip().casefold()),
        )
        for index, item in enumerate(equipment)
        if isinstance(item, Mapping)
    ]
    physical_count = sum(1 for item in summaries if item["physical_equipment"])
    logic_count = len(summaries) - physical_count
    failures = flatten_gate_failures(overview_gate)
    return {
        "schema": "equipment-design-compact-validation-packet-v2",
        "packet_policy": {
            "mode": "SUMMARY_FIRST_HASH_BOUND_DRILLDOWN",
            "effectiveness_contract": (
                "The full deterministic result remains authoritative. This packet exposes every decision, canonical "
                "scalar, formula chain, pending target, authority overview cell, and overview failure needed for "
                "first-pass validation."
            ),
            "read_full_result_only_when": [
                "a packet assertion fails",
                "a listed failure needs lineage or candidate-detail diagnosis",
                "artifact hash verification fails",
            ],
            "validation_surface_index": {
                "case_and_run_status": "/case_summary",
                "selection_summary": "/equipment_summaries/*/selection",
                "formula_chains": "/equipment_summaries/*/formula_chains",
                "preliminary_completion_inputs": "/equipment_summaries/*/preliminary_completion_inputs",
                "authority_overview_cells": "/equipment_summaries/*/authority_cells",
                "local_pending_and_diagnostics": "/equipment_summaries/*/calculation_pending",
                "overview_gate": "/overview_gate",
            },
            "candidate_bulk_intentionally_deferred": True,
        },
        "artifacts": {
            "full_result": artifact(result_path),
            "overview_gate": artifact(gate_path),
        },
        "case_summary": {
            "case_id": result.get("case_id"),
            "engine_version": result.get("engine_version"),
            "status": result.get("status"),
            "deterministic": result.get("deterministic"),
            "llm_used": result.get("llm_used"),
            "formal_use_gate": result.get("formal_use_gate"),
            "physical_equipment_count": physical_count,
            "logic_node_count": logic_count,
            "aspen_run_gate": result.get("aspen_run_gate"),
        },
        "diagnostic_digest": {
            "normalization_diagnostic_count": result.get("normalization_diagnostic_count", 0),
            "normalization_codes": diagnostic_counts(result.get("normalization_diagnostics")),
            "formal_use_blocker_count": len(result.get("formal_use_blockers") or []),
        },
        "equipment_summaries": summaries,
        "overview_gate": {
            "schema": overview_gate.get("schema"),
            "status": overview_gate.get("status"),
            "failure_count": overview_gate.get("failure_count"),
            "authority_missing_field_count": overview_gate.get("authority_missing_field_count"),
            "failures": failures,
            "full_gate_pointer": "/",
        },
    }


def build_authority_rows(result: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    app_dir = Path(__file__).resolve().parents[1] / "app"
    app_dir_text = str(app_dir)
    if app_dir_text not in sys.path:
        sys.path.insert(0, app_dir_text)
    from customer_delivery import build_customer_delivery

    delivery = build_customer_delivery(result)
    overview = delivery.get("equipment_overview_table")
    rows = overview.get("rows") if isinstance(overview, Mapping) else None
    if not isinstance(rows, list):
        raise ValueError("customer delivery did not return equipment_overview_table.rows")
    return [row for row in rows if isinstance(row, Mapping)]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a compact, hash-bound equipment-validation packet.")
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--overview-gate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result_path = args.result.expanduser().resolve()
    gate_path = args.overview_gate.expanduser().resolve()
    output = args.output.expanduser().resolve()
    result = json.loads(result_path.read_text(encoding="utf-8-sig"))
    gate = json.loads(gate_path.read_text(encoding="utf-8-sig"))
    packet = build_validation_packet(
        result,
        gate,
        result_path,
        gate_path,
        authority_rows=build_authority_rows(result),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "PASS",
        "output": str(output),
        "sha256": sha256_file(output),
        "size_bytes": output.stat().st_size,
        "full_result_size_bytes": result_path.stat().st_size,
    }, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
