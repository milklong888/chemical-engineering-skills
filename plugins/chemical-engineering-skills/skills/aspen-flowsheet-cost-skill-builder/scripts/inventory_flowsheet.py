from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any


REQUIRED_DATA_FILES = ("method-library.csv", "project-equipment-method-matrix.csv")

REACTOR_TYPES = {
    "RCSTR", "RPLUG", "RBATCH", "RSTOIC", "RYIELD", "REQCSTR",
    "REQUIL", "RGIBBS", "RCONV", "RCONVERSION",
}
LOGICAL_TYPES = {"MIXER", "FSPLIT", "SPLIT", "DUPL", "MULT", "BALANCE", "VALVE"}

METHOD_RULES = {
    "HEATER": ("shell_and_tube_or_service_specific_exchanger", "purchased_equipment_candidate", "HX_Q_U_LMTD_NETL", "NETL_2002_1169"),
    "COOLER": ("shell_and_tube_or_service_specific_exchanger", "purchased_equipment_candidate", "HX_Q_U_LMTD_NETL", "NETL_2002_1169"),
    "HEATX": ("process_process_or_utility_exchanger", "purchased_equipment_candidate", "HX_Q_U_LMTD_NETL", "NETL_2002_1169"),
    "PUMP": ("pump_type_requires_review", "purchased_equipment_candidate", "PUMP_Q_H_NETL", "NETL_2002_1169"),
    "COMPR": ("compressor_or_blower_requires_review", "purchased_equipment_candidate", "COMPRESSOR_Q_POWER_NETL", "NETL_2002_1169"),
    "MCOMPR": ("multistage_compressor_package", "purchased_equipment_candidate", "COMPRESSOR_Q_POWER_NETL", "NETL_2002_1169"),
    "FLASH": ("separator_vessel_or_specialized_separator", "purchased_equipment_candidate", "FLASH_VESSEL_HYDRAULIC_NETL", "NETL_2002_1169"),
    "FLASH2": ("separator_vessel_or_specialized_separator", "purchased_equipment_candidate", "FLASH_VESSEL_HYDRAULIC_NETL", "NETL_2002_1169"),
    "SEP": ("separator_type_requires_service_evidence", "purchased_equipment_candidate", "FLASH_VESSEL_HYDRAULIC_NETL", "NETL_2002_1169"),
    "SEP2": ("separator_type_requires_service_evidence", "purchased_equipment_candidate", "FLASH_VESSEL_HYDRAULIC_NETL", "NETL_2002_1169"),
    "RADFRAC": ("tower_and_physical_auxiliaries", "purchased_equipment_candidate", "COLUMN_HYDRAULIC_PACKAGE_NETL", "NETL_2002_1169"),
    "ABSBR": ("absorber_or_stripper_tower", "purchased_equipment_candidate", "COLUMN_HYDRAULIC_PACKAGE_NETL", "NETL_2002_1169"),
    "CYCLONE": ("gas_solid_cyclone_and_hopper", "purchased_equipment_candidate", "CYCLONE_SOLIDS_PACKAGE", ""),
}


def read_text(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_inp(path: Path) -> dict[str, Any]:
    text = read_text(path)
    blocks: dict[str, str] = {}
    cards: dict[str, str] = {}
    matches = [
        match for match in re.finditer(r"(?m)^BLOCK\s+([^\s]+)\s+([^\s]+)", text)
        if not match.group(2).upper().startswith("IN=")
    ]
    for index, match in enumerate(matches):
        block_id, block_type = match.group(1), match.group(2).upper()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks.setdefault(block_id, block_type)
        cards.setdefault(block_id, text[match.start():end])

    connections: dict[str, dict[str, list[str]]] = {}
    flow = re.search(r"(?ms)^FLOWSHEET\s*(.*?)(?=^PROPERTIES\b|^NC-COMPS\b|^PROP-DATA\b|^STREAM\b)", text)
    if flow:
        for line in flow.group(1).splitlines():
            match = re.match(r"\s*BLOCK\s+(\S+)\s+IN=(.*?)\s+OUT=(.*)\s*$", line)
            if match:
                connections[match.group(1)] = {
                    "in": match.group(2).split(),
                    "out": match.group(3).split(),
                }

    utilities: dict[str, list[str]] = {}
    for block_id, card in cards.items():
        found = re.findall(r"(?:UTILITY-ID|COND-UTIL|REB-UTIL)\s*=\s*([^\s/]+)", card, re.I)
        if found:
            utilities[block_id] = found
    return {"text": text, "blocks": blocks, "cards": cards, "connections": connections, "utilities": utilities}


def parse_utility_definitions(paths: list[Path]) -> dict[str, dict[str, Any]]:
    definitions: dict[str, dict[str, Any]] = {}
    for path in paths:
        text = read_text(path)
        matches = list(re.finditer(r"(?m)^UTILITY\s+(\S+)\s+GENERAL\b", text))
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            card = text[match.start():end]
            utility_id = match.group(1)

            def number(name: str) -> float | None:
                found = re.search(rf"\b{re.escape(name)}\s*=\s*([-+0-9.Ee]+)", card, re.I)
                return float(found.group(1)) if found else None

            price_basis = ""
            price = None
            for name in ("ENERGY-PRICE", "ELEC-PRICE", "PRICE"):
                price = number(name)
                if price is not None:
                    price_basis = name
                    break
            definitions[utility_id] = {
                "utility_id": utility_id,
                "tin_C": number("TIN"),
                "tout_C": number("TOUT"),
                "configured_price": price,
                "price_basis": price_basis,
                "source_inp": str(path.resolve()),
            }
    return definitions


def load_overrides(path: Path | None) -> dict[str, dict[str, str]]:
    if not path:
        return {}
    return {row["block_id"]: row for row in read_csv(path)}


def classify(block_type: str) -> dict[str, str]:
    upper = block_type.upper()
    if upper in REACTOR_TYPES:
        return {
            "physical_equipment": "reactor_or_internal_chemistry",
            "scope_class": "reactor_excluded",
            "method_id": "LOGICAL_OR_REACTOR_EXCLUSION",
            "source_ids": "",
            "mapping_status": "rule_fixed",
            "decision_gate": "excluded from ordinary non-reactor equipment cost",
        }
    if upper in LOGICAL_TYPES:
        return {
            "physical_equipment": "logical_or_bulk_item",
            "scope_class": "excluded_logical_or_bulk",
            "method_id": "LOGICAL_OR_REACTOR_EXCLUSION",
            "source_ids": "",
            "mapping_status": "candidate_requires_physical_scope_review",
            "decision_gate": "include only with explicit evidence of a physical package",
        }
    if upper in METHOD_RULES:
        equipment, scope, method, source = METHOD_RULES[upper]
        return {
            "physical_equipment": equipment,
            "scope_class": scope,
            "method_id": method,
            "source_ids": source,
            "mapping_status": "candidate_requires_service_review",
            "decision_gate": "confirm physical subtype, service, package boundary, units, range, and source applicability",
        }
    return {
        "physical_equipment": "unresolved_physical_equipment",
        "scope_class": "physical_scope_unresolved",
        "method_id": "METHOD_GAP",
        "source_ids": "",
        "mapping_status": "method_gap_open",
        "decision_gate": "identify physical equipment and acquire a supported sizing/cost method",
    }


def apply_override(mapping: dict[str, str], override: dict[str, str] | None) -> dict[str, str]:
    if not override:
        return mapping
    result = dict(mapping)
    for key in (
        "physical_equipment", "scope_class", "method_id", "source_ids",
        "mapping_status", "decision_gate", "service", "note",
    ):
        if override.get(key, "").strip():
            result[key] = override[key].strip()
    return result


def source_query(mapping: dict[str, str], block_type: str, service: str) -> str:
    equipment = mapping["physical_equipment"].replace("_", " ")
    if mapping["method_id"] == "METHOD_GAP":
        return f'site:osti.gov "{equipment}" "purchased equipment cost"; site:epa.gov "{equipment}" cost manual'
    if "cyclone" in equipment.lower():
        return 'site:osti.gov biomass gasification cyclone hopper purchased equipment cost; vendor budgetary cyclone quote capacity material temperature'
    return f'site:osti.gov "{equipment}" "{service or block_type}" equipment cost capacity'


def catalog_candidates(block_type: str, matrix_rows: list[dict[str, str]]) -> tuple[str, str]:
    upper = block_type.upper()
    matches = []
    source_ids: set[str] = set()
    for row in matrix_rows:
        pattern = row.get("aspen_block_type", "").upper()
        tokens = {token for token in re.split(r"[^A-Z0-9]+", pattern) if token}
        if upper not in tokens:
            continue
        matches.append(
            f"{row.get('stage', '')}:{row.get('project_service_pattern', '')}:"
            f"{row.get('physical_equipment', '')}"
        )
        for field in ("primary_cost_source", "crosscheck_source"):
            for source_id in re.split(r"[;|]", row.get(field, "")):
                candidate = source_id.strip()
                if re.fullmatch(r"[A-Z0-9][A-Z0-9-]+", candidate):
                    source_ids.add(candidate)
    return ";".join(sorted(source_ids)), " | ".join(matches[:12])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inventory an exported Aspen INP for equipment-cost skill generation.")
    parser.add_argument("--template-id", required=True)
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--inp", type=Path, required=True)
    parser.add_argument("--bkp", type=Path, default=None)
    parser.add_argument("--utility-inp", type=Path, action="append", default=[])
    parser.add_argument("--service-overrides", type=Path, default=None)
    parser.add_argument("--data-dir", type=Path, default=None,
                        help="User-reviewed directory containing the method library and equipment method matrix CSVs.")
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data_dir = args.data_dir.resolve() if args.data_dir else None
    data_rows: dict[str, list[dict[str, str]]] = {}
    missing_files: list[str] = []
    for name in REQUIRED_DATA_FILES:
        path = data_dir / name if data_dir else None
        try:
            if path is None or not path.is_file() or path.stat().st_size == 0:
                missing_files.append(name)
                continue
            rows = read_csv(path)
            if not rows:
                missing_files.append(name)
                continue
            data_rows[name] = rows
        except (OSError, UnicodeError, csv.Error):
            missing_files.append(name)
    if missing_files:
        print(json.dumps({
            "status": "dependency_unavailable",
            "dependency": "reviewed_cost_csv_data",
            "required_argument": "--data-dir",
            "missing_or_unusable_files": missing_files,
            "outputs_created": False,
            "costs_calculated": False,
        }, ensure_ascii=False, indent=2))
        return 2

    inp = args.inp.resolve()
    if not inp.exists():
        raise SystemExit(f"INP not found: {inp}")
    bkp = args.bkp.resolve() if args.bkp else None
    if bkp and not bkp.exists():
        raise SystemExit(f"BKP not found: {bkp}")
    utilities_paths = [inp, *[path.resolve() for path in args.utility_inp]]
    for path in utilities_paths:
        if not path.exists():
            raise SystemExit(f"Utility INP not found: {path}")

    out = args.out_dir.resolve()
    parsed = parse_inp(inp)
    utility_definitions = parse_utility_definitions(utilities_paths)
    overrides = load_overrides(args.service_overrides.resolve() if args.service_overrides else None)
    methods = {row["method_id"]: row for row in data_rows["method-library.csv"]}
    matrix_rows = data_rows["project-equipment-method-matrix.csv"]
    out.mkdir(parents=True, exist_ok=True)

    mother = [{
        "template_id": args.template_id,
        "project_name": args.project_name,
        "bkp_path": str(bkp) if bkp else "",
        "bkp_sha256": sha256(bkp) if bkp else "",
        "inp_path": str(inp),
        "inp_sha256": sha256(inp),
        "block_count": len(parsed["blocks"]),
        "utility_definition_count": len(utility_definitions),
        "identity_status": "recorded",
        "note": "Mother identity is separate from any representative-run evidence.",
    }]

    equipment_rows: list[dict[str, Any]] = []
    assignment_rows: list[dict[str, Any]] = []
    missing_rows: list[dict[str, Any]] = []
    source_requests: list[dict[str, Any]] = []

    for block_id, block_type in parsed["blocks"].items():
        connection = parsed["connections"].get(block_id, {"in": [], "out": []})
        mounted = parsed["utilities"].get(block_id, [])
        card_hash = hashlib.sha256(parsed["cards"].get(block_id, "").encode("utf-8")).hexdigest().upper()
        mapping = classify(block_type)
        mapping = apply_override(mapping, overrides.get(block_id))
        service = mapping.get("service") or "unresolved_service"

        equipment_rows.append({
            "template_id": args.template_id,
            "equipment_item_id": block_id,
            "block_id": block_id,
            "aspen_block_type": block_type,
            "inlet_streams": ";".join(connection["in"]),
            "outlet_streams": ";".join(connection["out"]),
            "utility_ids": ";".join(mounted),
            "utility_definition_json": json.dumps({key: utility_definitions.get(key, {}) for key in mounted}, ensure_ascii=False, sort_keys=True),
            "block_card_sha256": card_hash,
            "source_inp": str(inp),
        })

        assignment = {
            "template_id": args.template_id,
            "equipment_item_id": block_id,
            "block_id": block_id,
            "aspen_block_type": block_type,
            "service": service,
            **mapping,
            "source_inp": str(inp),
        }
        assignment_rows.append(assignment)

        contract = methods.get(mapping["method_id"])
        if contract and mapping["method_id"] != "LOGICAL_OR_REACTOR_EXCLUSION":
            try:
                parameters = json.loads(contract.get("parameter_contract_json") or "[]")
            except json.JSONDecodeError:
                parameters = []
            for parameter in parameters:
                missing_rows.append({
                    "template_id": args.template_id,
                    "equipment_item_id": block_id,
                    "method_id": mapping["method_id"],
                    "parameter_name": parameter.get("name", ""),
                    "required_unit": parameter.get("unit", ""),
                    "preferred_source": parameter.get("source", ""),
                    "status": "runtime_required",
                    "blocking_effect": "case calculation remains unresolved until supplied",
                })

        needs_source_request = (
            mapping["scope_class"] != "reactor_excluded"
            and (
                mapping["method_id"] == "METHOD_GAP"
                or not mapping.get("source_ids")
                or mapping["mapping_status"].startswith("candidate")
            )
        )
        if needs_source_request:
            if mapping["scope_class"] == "excluded_logical_or_bulk":
                gap_type = "mapping_evidence"
            else:
                gap_type = "method_source" if mapping["method_id"] == "METHOD_GAP" or not mapping.get("source_ids") else "mapping_evidence"
            candidate_source_ids, candidate_matrix_matches = catalog_candidates(block_type, matrix_rows)
            source_requests.append({
                "gap_id": f"{args.template_id}__{block_id}__{gap_type}",
                "template_id": args.template_id,
                "block_id": block_id,
                "aspen_block_type": block_type,
                "physical_equipment": mapping["physical_equipment"],
                "service": service,
                "gap_type": gap_type,
                "evidence_needed": mapping["decision_gate"],
                "preferred_source_tier": "A_then_B_then_C_then_vendor",
                "catalog_candidate_source_ids": candidate_source_ids,
                "catalog_matrix_matches": candidate_matrix_matches,
                "search_query": source_query(mapping, block_type, service),
                "acceptance_test": "exact locator, scope, capacity variable, units, range, base period, raw extraction, exact-anchor reproduction, target-domain review",
                "status": "open",
                "note": mapping.get("note", ""),
            })

    write_csv(out / "mother_template_inventory.csv", mother, list(mother[0]))
    write_csv(out / "equipment_inventory.csv", equipment_rows, list(equipment_rows[0]) if equipment_rows else [])
    write_csv(out / "equipment_method_assignment.csv", assignment_rows, list(assignment_rows[0]) if assignment_rows else [])
    write_csv(out / "missing_parameter_register.csv", missing_rows, [
        "template_id", "equipment_item_id", "method_id", "parameter_name",
        "required_unit", "preferred_source", "status", "blocking_effect",
    ])
    write_csv(out / "source_request_register.csv", source_requests, [
        "gap_id", "template_id", "block_id", "aspen_block_type",
        "physical_equipment", "service", "gap_type", "evidence_needed",
        "preferred_source_tier", "catalog_candidate_source_ids",
        "catalog_matrix_matches", "search_query", "acceptance_test", "status", "note",
    ])
    write_csv(out / "source_search_log.csv", [], [
        "query_id", "timestamp", "search_tier", "search_root_or_domain",
        "query_pattern", "matched_source_or_file", "line_page_or_table",
        "source_id", "evidence_layer", "equipment_item_id", "evidence_type",
        "extracted_value", "unit", "cost_scope", "confidence", "accepted_for",
        "rejection_reason", "status", "note",
    ])

    spec = {
        "generator": "aspen-flowsheet-cost-skill-builder",
        "project_name": args.project_name,
        "template_id": args.template_id,
        "mother_bkp_path": str(bkp) if bkp else "",
        "mother_bkp_sha256": sha256(bkp) if bkp else "",
        "source_inp_path": str(inp),
        "source_inp_sha256": sha256(inp),
        "block_count": len(equipment_rows),
        "included_candidate_count": sum(row["scope_class"] == "purchased_equipment_candidate" for row in assignment_rows),
        "excluded_count": sum("excluded" in row["scope_class"] for row in assignment_rows),
        "method_gap_count": sum(row["method_id"] == "METHOD_GAP" for row in assignment_rows),
        "open_source_request_count": len(source_requests),
        "status": "draft_requires_mapping_source_and_case_evidence_review",
    }
    (out / "skill_spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "ok", "out_dir": str(out), **spec}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
