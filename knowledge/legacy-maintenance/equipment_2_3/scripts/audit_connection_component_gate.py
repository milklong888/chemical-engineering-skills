from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


LOGIC_BLOCK_TYPES = frozenset({"FSPLIT", "MIXER", "HIERARCHY"})
COMPONENT_FAMILIES = frozenset({"flange_type", "facing", "gasket_type", "fastener_type"})


def audit_case(path: Path) -> dict[str, Any]:
    result = json.loads(path.read_text(encoding="utf-8-sig"))
    failures: list[dict[str, Any]] = []
    equipment_count = 0
    physical_count = 0
    applicable_connections = 0
    terminal_components = 0
    unknown_property_labels = 0
    for equipment in result.get("equipment", []):
        equipment_count += 1
        tag = str(equipment.get("equipment_tag") or equipment.get("aspen_block_id") or "")
        block_type = str(equipment.get("canonical_match_input", {}).get("aspen_block_type") or "").upper()
        if block_type in LOGIC_BLOCK_TYPES:
            continue
        physical_count += 1
        match_result = equipment.get("match_result", {})
        expected_parent = (
            match_result.get("design_parameter_package", {})
            .get("selection_context", {})
            .get("sha256", "")
        )
        profile = equipment.get("service_profile", {})
        if profile.get("schema") != "equipment-service-profile-v1":
            failures.append({"equipment": tag, "code": "SERVICE_PROFILE_MISSING"})
        if profile.get("runtime_contract", {}).get("vision_capability") is not False:
            failures.append({"equipment": tag, "code": "SERVICE_PROFILE_VISION_NOT_DISABLED"})
        package = equipment.get("connection_component_selections", {})
        if package.get("schema") != "equipment-connection-selection-package-v1":
            failures.append({"equipment": tag, "code": "CONNECTION_PACKAGE_MISSING"})
            continue
        if package.get("status") == "LOCAL_SELECTION_PACKAGE_FAILED":
            failures.append({"equipment": tag, "code": "CONNECTION_PACKAGE_FAILED", "detail": package.get("diagnostics")})
        if package.get("parent_selection_context_sha256") != expected_parent:
            failures.append({"equipment": tag, "code": "PARENT_CONTEXT_HASH_MISMATCH"})
        if package.get("source_export_sha256") != result.get("source_export_sha256"):
            failures.append({"equipment": tag, "code": "SOURCE_EXPORT_HASH_MISMATCH"})
        if package.get("pfd_mapping_sha256") != result.get("pfd_mapping_sha256"):
            failures.append({"equipment": tag, "code": "PFD_MAPPING_HASH_MISMATCH"})
        if package.get("llm_used") is not False or package.get("runtime_vision") is not False or package.get("runtime_source_access") is not False:
            failures.append({"equipment": tag, "code": "OFFLINE_RUNTIME_CONTRACT_FAILED"})
        for connection in package.get("connections", []):
            if connection.get("applicability") != "APPLICABLE":
                continue
            applicable_connections += 1
            components = connection.get("component_types", {})
            if set(components) != COMPONENT_FAMILIES:
                failures.append({
                    "equipment": tag,
                    "connection": connection.get("connection_id"),
                    "code": "COMPONENT_FAMILY_SET_MISMATCH",
                    "actual": sorted(components),
                })
                continue
            accepted = connection.get("accepted_property_facts", [])
            accepted_names = {str(item.get("fact") or "") for item in accepted}
            for family, selected in components.items():
                terminal_components += 1
                if selected.get("terminal_count") != 1 or not selected.get("terminal_type", {}).get("candidate_id"):
                    failures.append({
                        "equipment": tag,
                        "connection": connection.get("connection_id"),
                        "family": family,
                        "code": "UNIQUE_TERMINAL_TYPE_FAILED",
                    })
                labels = selected.get("normalized_service_labels", {})
                for property_name in ("corrosivity", "toxicity", "flammability", "explosivity", "oxidizing"):
                    if property_name not in accepted_names and labels.get(property_name) != "unknown":
                        failures.append({
                            "equipment": tag,
                            "connection": connection.get("connection_id"),
                            "family": family,
                            "code": "PROPERTY_LABEL_WITHOUT_ACCEPTED_FACT",
                            "property": property_name,
                            "value": labels.get(property_name),
                        })
                    elif labels.get(property_name) == "unknown":
                        unknown_property_labels += 1
    return {
        "case_path": str(path.resolve()),
        "case_id": result.get("case_id"),
        "equipment_count": equipment_count,
        "physical_equipment_count": physical_count,
        "applicable_connection_count": applicable_connections,
        "terminal_component_count": terminal_components,
        "unknown_property_label_observation_count": unknown_property_labels,
        "failure_count": len(failures),
        "failures": failures,
        "status": "PASS" if not failures else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit automatic service profiles and HG/T connection-component terminal selections.")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    root = Path(args.input_dir).expanduser().resolve()
    paths = sorted(root.glob("case_*/equipment_derivation_result.json"))
    cases = [audit_case(path) for path in paths]
    report = {
        "schema": "equipment-connection-selection-batch-audit-v1",
        "deterministic": True,
        "llm_used": False,
        "case_count": len(cases),
        "physical_equipment_count": sum(item["physical_equipment_count"] for item in cases),
        "applicable_connection_count": sum(item["applicable_connection_count"] for item in cases),
        "terminal_component_count": sum(item["terminal_component_count"] for item in cases),
        "failure_count": sum(item["failure_count"] for item in cases),
        "cases": cases,
    }
    report["status"] = "PASS" if paths and report["failure_count"] == 0 else "FAIL"
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
