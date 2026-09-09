"""Evidence-bound equipment feedback; produces plans, never fabricated Aspen results."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from pathlib import Path

from .selector_analysis import canonical_sha, equipment_records, feedback_record
from . import pressure
from .pressure import number

PREFERRED = {"family_heat_exchanger": "exchanger_series", "family_exchanger": "exchanger_series",
             "family_compressor": "compressor_stages_series", "family_tower": "tower_parallel",
             "family_column": "tower_parallel"}
REPLAY_GATES = ["native_model_topology", "material_component_balance", "energy_balance",
                "pressure_network", "phase_and_temperature_approach", "product_targets",
                "equipment_reselection", "operability_control", "safety_and_materials",
                "strict_run_status", "exact_delivery_reopen"]

# Explicit canonical projection, not an arbitrary Aspen export parser.
FIELD_UNITS = {"heat_transfer_area_m2": "m2", "flow_m3_h": "m3/h", "mass_flow_kg_h": "kg/h",
    "heat_duty_kw": "kW", "overall_u_w_m2k": "W/m2/K", "lmtd_k": "K", "lmtd_correction_factor": "1",
    "pressure_ratio": "1", "compression_pressure_ratio": "1", "velocity_m_s": "m/s",
    "inlet_pressure_mpa": "MPa", "outlet_pressure_mpa": "MPa", "pressure_drop_pa": "Pa",
    "pressure_drop_mpa": "MPa", "head_m": "m", "density_kg_m3": "kg/m3", "efficiency": "1",
    "temperature_c": "C", "inlet_temperature_c": "C", "outlet_temperature_c": "C"}
QUANTITY_ALIASES = {"area": "heat_transfer_area_m2", "flow": "flow_m3_h", "feed_flow": "flow_m3_h",
    "velocity": "velocity_m_s", "inlet_pressure": "inlet_pressure_mpa", "pressure_drop": "pressure_drop_pa"}
THROUGHFLOW_QUANTITIES = {"flow_m3_h", "mass_flow_kg_h", "velocity_m_s", "inlet_pressure_mpa", "pressure_drop_pa", "pressure_drop_mpa"}

class BindingGap(ValueError):
    """A missing applicable link blocks only this configuration conclusion."""

def canonical_quantity(name):
    return QUANTITY_ALIASES.get(name, name)

def current_input_binding(export, authority, context, tag, wrapper, core):
    gaps = []
    run = context.get("run_id")
    if not run or export.get("schema") != "equipment-process-canonical-export-v1":
        gaps.append("CURRENT_CANONICAL_EXPORT_AND_RUN_REQUIRED")
    if authority.get("schema") != "equipment-process-authority-v1":
        gaps.append("CURRENT_AUTHORITY_SCHEMA_REQUIRED")
    if any(value.get("case_id") != context["case_id"] or value.get("run_id") != run for value in (export, authority)):
        gaps.append("CASE_OR_RUN_IDENTITY_MISMATCH")
    equipment = export.get("equipment", {}).get(tag, {})
    authorized = authority.get("equipment", {}).get(tag, {})
    family = core.get("match", {}).get("family_id") or core.get("design_parameter_package", {}).get("family_id")
    if equipment.get("family_id") != family:
        gaps.append("CURRENT_EXPORT_EQUIPMENT_FAMILY_MISMATCH")
    direct = core.get("normalized_input") or wrapper.get("input") or {}
    if not direct:
        gaps.append("SELECTOR_INPUT_VALUES_NOT_AVAILABLE")
    bound = {}
    for field, value in direct.items():
        if field in {"equipment_tag", "equipment_family"}:
            continue
        choices = [("source_export", equipment), ("authority", authorized)]
        found = False
        for origin, record in choices:
            if field not in record.get("values", {}):
                continue
            unit = record.get("units", {}).get(field)
            expected = FIELD_UNITS.get(field)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                try:
                    number(value, field)
                except ValueError:
                    continue
                if not expected or unit != expected:
                    continue
            if record["values"][field] == value:
                bound[field] = {"value": value, "unit": unit, "origin": origin,
                                "source": context[origin], "pointer": f"/equipment/{tag}/values/{field}"}
                found = True
                break
        if not found:
            gaps.append("UNBOUND_OR_CONFLICTING_SELECTOR_INPUT:" + field)
    return {"status": "BOUND_CURRENT_INPUTS" if not gaps else "LOCAL_BINDING_GAP",
            "bound_fields": bound, "gaps": gaps,
            "schema_boundary": "Only explicit canonical equipment values/units, not arbitrary Aspen JSON"}


def count_bound(route, constraints):
    """Derive available count bounds without promoting a sizing assumption."""
    bounds = []
    for row in constraints:
        if row["relation"] != "max" or row["limit"] <= 0:
            continue
        quantity = row["quantity"]
        value, limit = row["value"], row["limit"]
        n, assumption, formula = None, None, None
        if route == "exchanger_series" and quantity in {"area", "heat_transfer_area_m2"}:
            n = math.ceil(value / limit)
            formula = "ceil(A_total_current/A_max_per_unit)"
            assumption = "Current total area held fixed for initial bound; segment thermal states may change required total area"
        elif route == "compressor_stages_series" and quantity in {"pressure_ratio", "compression_pressure_ratio"} and limit > 1 and value > 1:
            n = math.ceil(math.log(value) / math.log(limit) - 1e-12)
            formula = "ceil(log(overall_absolute_ratio)/log(applicable_stage_ratio_limit))"
            assumption = "Same applicable ratio limit each stage, no interstage loss; positive losses may increase needed stage count"
        elif route == "tower_parallel" and quantity in {"flow", "flow_m3_h", "mass_flow_kg_h", "feed_flow"}:
            n = math.ceil(value / limit)
            formula = "ceil(total_feed/applicable_per_train_capacity)"
            assumption = "Equivalent branch separation and capacity basis; pressure distribution and each tower still require calculation"
        if n is not None:
            bounds.append({"count": n, "formula": formula, "assumption": assumption,
                           "source_constraint": row["review_record"], "status": "CONDITIONAL_INITIAL_BOUND_NOT_SELECTED_COUNT"})
    return bounds


def configuration_checks(checks):
    """Execute explicitly requested pressure screens as part of the feedback record."""
    methods = {name: getattr(pressure, name) for name in ("liquid_pipe_loss", "series_pressure",
               "compressor_train", "equal_ratio_initializer", "parallel_distribution")}
    results = []
    for check in checks:
        if check.get("method") not in methods or not check.get("input_basis"):
            results.append({"status": "NOT_CALCULATED", "reason": "registered method and explicit input basis required"})
            continue
        try:
            result = methods[check["method"]](**check["inputs"])
        except (ValueError, KeyError, TypeError) as exc:
            results.append({"method": check["method"], "status": "LOCAL_CALCULATION_GAP", "reason": str(exc)})
            continue
        results.append({"method": check["method"], "input_basis": check["input_basis"],
                        "inputs_sha256": canonical_sha(check["inputs"]), "result": result,
                        "model_implementation_verified": False})
    return results


def digest_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def read_reference(root, reference):
    """Read only explicit hash-bound input; never infer a hidden project path."""
    path = Path(reference["path"])
    path = path if path.is_absolute() else Path(root) / path
    if digest_file(path) != str(reference["sha256"]).upper():
        raise ValueError("Source artifact hash differs from the declared authority")
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    pointer = reference.get("pointer", "")
    if pointer and not pointer.startswith("/"):
        raise ValueError("Source pointer must be an RFC 6901 JSON pointer")
    for part in pointer.split("/")[1:]:
        part = part.replace("~1", "/").replace("~0", "~")
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def exceeded_constraint(root, reference, equipment_id, *, context=None, binding=None, core=None):
    row = read_reference(root, reference)
    if (row.get("equipment_id") != equipment_id or row.get("status") != "verified_applicable"
            or not row.get("unit") or not row.get("applicability")
            or not row.get("value_source") or not row.get("limit_source")):
        raise ValueError("Constraint lacks equipment identity, units, applicable review or source links")
    # Both readings must really be present in separately hash-bound evidence.
    if not context or not binding or binding["gaps"]:
        raise BindingGap("CURRENT_SELECTOR_INPUT_BINDING_REQUIRED")
    quantity = canonical_quantity(row.get("quantity"))
    expected_unit = FIELD_UNITS.get(quantity)
    if not expected_unit or row.get("unit") != expected_unit:
        raise BindingGap("UNKNOWN_QUANTITY_OR_NONCANONICAL_UNIT")
    source = row["value_source"]
    if source.get("kind") == "current_selector_derivation":
        if source.get("field") != quantity or quantity not in core.get("derived_parameters", {}):
            raise BindingGap("CURRENT_SELECTOR_DERIVATION_MISSING")
        actual = core["derived_parameters"][quantity]
        row["resolved_value_source"] = {"kind": "current_selector_derivation", "field": quantity,
            "core_sha256": canonical_sha(core), "bound_inputs": binding["bound_fields"], "calculations": core.get("calculations", [])}
        if not row["resolved_value_source"]["calculations"]:
            raise BindingGap("DERIVATION_TRACE_MISSING")
    else:
        matched_origin = next((origin for origin in ("source_export", "authority")
            if str(source.get("sha256", "")).upper() == str(context[origin]["sha256"]).upper()
            and source.get("pointer") == f"/equipment/{equipment_id}/values/{quantity}"), None)
        if matched_origin is None:
            raise BindingGap("VALUE_SOURCE_NOT_CURRENT_EXPORT_OR_AUTHORITY")
        document = read_reference(root, {**source, "pointer": ""})
        record = document.get("equipment", {}).get(equipment_id, {})
        if (document.get("case_id") != context["case_id"] or document.get("run_id") != context["run_id"]
                or record.get("units", {}).get(quantity) != expected_unit):
            raise BindingGap("VALUE_IDENTITY_OR_UNIT_MISMATCH")
        actual = read_reference(root, source)
        current = binding["bound_fields"].get(quantity)
        derived = core.get("derived_parameters", {})
        if not ((current and current["value"] == actual) or derived.get(quantity) == actual):
            raise BindingGap("CONSTRAINT_VALUE_NOT_CURRENT_SELECTOR_VALUE")
    limit_document = read_reference(root, {**row["limit_source"], "pointer": ""})
    limit = read_reference(root, row["limit_source"])
    applies = limit_document.get("applicability", {})
    family = core.get("match", {}).get("family_id") or core.get("design_parameter_package", {}).get("family_id")
    if (limit_document.get("schema") != "equipment-process-limit-v1"
            or canonical_quantity(limit_document.get("quantity")) != quantity or limit_document.get("unit") != expected_unit
            or not all(limit_document.get(key) for key in ("source_id", "version", "locator"))
            or applies.get("equipment_id") != equipment_id or applies.get("family_id") != family):
        raise BindingGap("LIMIT_SOURCE_UNIT_VERSION_OR_APPLICABILITY_MISMATCH")
    if row["limit_source"].get("pointer") != "/value" or limit_document.get("value") != limit:
        raise BindingGap("LIMIT_VALUE_POINTER_REQUIRED")
    if actual != row["value"] or limit != row["limit"]:
        raise ValueError("Constraint value/limit differs from its source pointer")
    actual, limit = number(actual, "constraint value"), number(limit, "constraint limit")
    relation = row["relation"]
    if relation not in {"max", "min"}:
        raise ValueError("Only explicit max/min constraint comparisons are supported")
    return {**row, "quantity": quantity, "exceeded": actual > limit if relation == "max" else actual < limit,
            "review_record": reference,
            "review_boundary": "Source identity and comparison checked; applicability review remains cited engineering authority"}


def affected_consumers(tag, topology):
    nodes = set(topology.get("nodes", []))
    edges = topology.get("edges", [])
    if tag not in nodes:
        return {"coverage": "TOPOLOGY_NOT_PROVIDED", "equipment": [tag]}
    if any(len(edge) != 2 or edge[0] not in nodes or edge[1] not in nodes for edge in edges):
        raise ValueError("Topology has an unknown endpoint")
    # Pressure and recycle effects can propagate upstream as well as downstream.
    found = {tag}
    while True:
        previous = set(found)
        for a, b in edges:
            if a in found or b in found:
                found.update((a, b))
        if previous == found:
            break
    return {"coverage": "DECLARED_CONNECTED_COMPONENT", "equipment": sorted(found)}


def build_plan(selector_response, context, root):
    if not context.get("case_id") or not context.get("source_export") or not context.get("authority"):
        raise ValueError("case_id, source_export and current authority references required")
    export = read_reference(root, context["source_export"])
    authority = read_reference(root, context["authority"])
    if not authority.get("required_method") or not authority.get("acceptance_criteria"):
        raise ValueError("Freeze method and acceptance before creating feedback")
    records = []
    for pointer, wrapper, core in equipment_records(selector_response.get("result", {})):
        old = feedback_record(pointer, wrapper, core, context)
        tag, family = old["equipment_id"], old.get("family_id")
        binding = current_input_binding(export, authority, context, tag, wrapper, core)
        binding_gaps = list(binding["gaps"])
        constraints = []
        if not binding_gaps:
            for ref in context.get("constraint_evidence", {}).get(tag, []):
                try:
                    constraints.append(exceeded_constraint(root, ref, tag, context=context, binding=binding, core=core))
                except BindingGap as exc:
                    binding_gaps.append(str(exc))
        exceeded = [row for row in constraints if row["exceeded"]]
        plan = None
        if old.get("physical_equipment") and old.get("primary_feedback_category") != "basis_invalid" and exceeded and not binding_gaps:
            route = PREFERRED.get(family)
            if route is None and "exchanger" in str(family):
                route = "exchanger_series"
            if route is None and any(word in str(family) for word in ("column", "tower")):
                route = "tower_parallel"
            if route:
                unresolved = []
                if route == "exchanger_series":
                    unresolved = [r["quantity"] for r in exceeded
                                  if r["quantity"] in THROUGHFLOW_QUANTITIES or r["quantity"] != "heat_transfer_area_m2"]
                instructions = {
                    "exchanger_series": ["Keep through-flow; each segment outlet feeds the next inlet.",
                        "Solve heat/phase state and area in each segment; do not divide duty or area equally by default.",
                        "Add each side pressure drop and interconnecting losses; compare remaining driving force."],
                    "compressor_stages_series": ["Choose candidate stage count from applicable gas/vendor limits.",
                        "Recompute suction after each cooler, separator and pipe loss; check phase and carryover.",
                        "Recompute discharge temperature, shaft power and operating map for every stage."],
                    "tower_parallel": ["Divide feed, not equilibrium stages; retain separation requirements per branch.",
                        "Solve common-boundary branch flow and pressure difference, not the sum of branch drops.",
                        "Recalculate separation, internal traffic, hydraulics, utilities and product mixing."]}[route]
                plan = {"preferred_route": route, "status": "REVIEW_CANDIDATE",
                        "unit_count": None, "unresolved_by_this_topology": unresolved,
                        "initial_count_bounds": count_bound(route, exceeded),
                        "cannot_claim_limit_resolved": bool(unresolved), "instructions": instructions,
                        "reason": "hash-bound applicable limit exceeded",
                        "automatic_aspen_mutation": False,
                        "requires_authority_change_before_implementation": True}
        records.append({"legacy_analysis": old, "equipment_id": tag, "family_id": family,
                        "current_input_binding": binding, "binding_gaps": binding_gaps,
                        "constraints": constraints, "revision": plan,
                        "configuration_calculations": configuration_checks(context.get("configuration_checks", {}).get(tag, [])),
                        "affected_consumers": affected_consumers(tag, context.get("topology", {})),
                        "after_change_state": "STALE_UNTIL_REPLAYED" if plan else "NO_TOPOLOGY_CHANGE_AUTHORIZED",
                        "missing_data_policy": "retain all derivable results; catalog absence alone never authorizes splitting"})
    if not records:
        raise ValueError("No recognized equipment records in selector response")
    result = {"schema": "equipment-process-plan-v2", "case_id": context["case_id"],
              "run_id": context.get("run_id"),
              "source_export": context["source_export"], "source_export_content_sha256": canonical_sha(export),
              "authority": context["authority"], "selector_response_sha256": canonical_sha(selector_response),
              "equipment": records, "required_replay_gates": REPLAY_GATES,
              "flowsheet_modified": False, "engineering_accepted": False,
              "next_action": "Review candidate, update project authority, implement via domain skill, export exact new model and reselect"}
    result["plan_sha256"] = canonical_sha(result)
    return result


def _read_artifact_bytes(root, ref):
    path = Path(ref["path"])
    path = path if path.is_absolute() else Path(root) / path
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest().upper() != str(ref["sha256"]).upper():
        raise ValueError("Domain artifact hash mismatch")
    return data


def _recheck_aspen_summary(native, receipt, root, candidate, implementation):
    """Reuse the frozen pure native parser against raw text, never launch COM."""
    spec = importlib.util.spec_from_file_location("feedback_verified_aspen_evidence", implementation)
    parser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parser)
    if (native.get("schema_version") != "aspen_clean_delivery_audit/2" or native.get("passed") is not True
            or native.get("simulation_clean") is not True or native.get("source_unchanged") is not True
            or str(native.get("source_sha256", "")).upper() != candidate["sha256"].upper()
            or native.get("run", {}).get("run_id") != receipt.get("run_id")
            or str(native.get("run", {}).get("case_sha256", "")).upper() != candidate["sha256"].upper()):
        return False
    control = native.get("control_panel", {})
    text = _read_artifact_bytes(root, control).decode("utf-8-sig", errors="strict")
    summary = parser.parse_summary_counts(text)
    histories = []
    for record in native.get("histories", []):
        raw = _read_artifact_bytes(root, record)
        decoded = parser.decode_history_bytes(raw)
        if decoded.get("verified") is not True:
            # Do not infer another machine's ACP from a self-labeled encoding.
            return False
        history = parser.inspect_history_text(decoded["text"], source=record["path"], source_sha256=record["sha256"])
        histories.append({**record, **history, "decode_verified": True, "size": len(raw)})
    gate = parser.evaluate_clean_gate(run=native["run"], summary=summary,
        control_messages=parser.find_hard_messages(text), histories=histories,
        control_association=control.get("association"), block_statuses=native.get("block_statuses"))
    return gate.get("passed") is True and gate.get("simulation_clean") is True


# This is a code-owned registry, not supplied by replay/CLI. The exact pure
# implementation may reside in the installed skill or the source package;
# content identity is fixed and checked before importing, regardless of path.
TRUSTED_REPLAY_VALIDATORS = {
    "aspen_summary_history_v2": {
        "implementation_sha256": "A2AF20FB4444DDE9DBCBD69E343F01D3AA908265BF7EFE764D3422505ACF7A27",
        "implementation_paths": ("plugins/chemical-engineering-skills/skills/aspen-plus-operations/scripts/aspen_evidence.py", "validators/aspen_evidence.py"),
        "native_schema": "aspen_clean_delivery_audit/2", "native_schema_field": "schema_version",
        "gates": frozenset({"strict_run_status"}), "recheck": _recheck_aspen_summary,
    }
}


def validate_domain_receipt(receipt, gate, root, candidate):
    if receipt.get("schema") != "equipment-process-domain-receipt-v1" or receipt.get("gate") != gate:
        return False, "UNKNOWN_RECEIPT_SCHEMA_OR_WRONG_GATE"
    checks = receipt.get("checks")
    if (not isinstance(checks, list) or not checks or any(not isinstance(row, dict)
            or not row.get("id") or row.get("passed") is not True for row in checks)
            or len({row["id"] for row in checks}) != len(checks)):
        return False, "FAILED_UNKNOWN_OR_DUPLICATE_CHECKS"
    validator = receipt.get("validator")
    if not isinstance(validator, dict):
        return False, "TRUSTED_VALIDATOR_IDENTITY_REQUIRED"
    registered = TRUSTED_REPLAY_VALIDATORS.get(validator.get("id"))
    if not registered or gate not in registered["gates"]:
        return False, "VALIDATOR_NOT_REGISTERED_FOR_GATE"
    if str(validator.get("sha256", "")).upper() != registered["implementation_sha256"]:
        return False, "VALIDATOR_IMPLEMENTATION_NOT_TRUSTED"
    runtime_root = Path(__file__).resolve().parents[2]
    allowed = [(Path(value) if Path(value).is_absolute() else runtime_root / value).resolve()
               for value in registered["implementation_paths"]]
    if validator.get("path"):
        implementation = Path(validator["path"])
        implementation = (implementation if implementation.is_absolute() else Path(root) / implementation).resolve()
        if implementation not in allowed:
            return False, "VALIDATOR_PATH_OUTSIDE_FIXED_RUNTIME_DEPENDENCIES"
    else:
        implementation = next((path for path in allowed if path.is_file()), allowed[0])
    if implementation.is_symlink() or digest_file(implementation) != registered["implementation_sha256"]:
        return False, "VALIDATOR_IMPLEMENTATION_HASH_MISMATCH"
    native_ref = receipt.get("native_result")
    if not isinstance(native_ref, dict):
        return False, "NATIVE_RESULT_REQUIRED"
    native = read_reference(root, native_ref)
    if not isinstance(native, dict) or native.get(registered["native_schema_field"]) != registered["native_schema"]:
        return False, "NATIVE_RESULT_SCHEMA_OUTSIDE_VALIDATOR_SCOPE"
    checked = registered["recheck"](native, receipt, root, candidate, implementation)
    return checked is True, "INDEPENDENT_NATIVE_RECHECK" if checked is True else "NATIVE_RECHECK_FAILED_OR_UNSUPPORTED"


def audit_replay(plan, replay, root):
    """Bind all replay receipts to one new model and to this exact change plan.

    A valid receipt is inspectable evidence, not a naked passed=true. Underlying
    domain validators own their engineering meaning. This does not call Aspen.
    """
    original = dict(plan)
    given = original.pop("plan_sha256")
    if canonical_sha(original) != given:
        raise ValueError("Plan content drift")
    if replay.get("plan_sha256") != given or replay.get("case_id") != plan["case_id"]:
        raise ValueError("Replay belongs to another plan/case")
    candidate = replay["candidate"]
    candidate_path = Path(candidate["path"])
    candidate_path = candidate_path if candidate_path.is_absolute() else Path(root) / candidate_path
    if digest_file(candidate_path) != str(candidate["sha256"]).upper():
        raise ValueError("Exact candidate file differs from replay")
    export = read_reference(root, replay["source_export"])
    if canonical_sha(export) == plan["source_export_content_sha256"] and any(r["revision"] for r in plan["equipment"]):
        raise ValueError("Changed topology cannot reuse the old export unchanged")
    receipts, failed, used_receipts = [], [], set()
    if any(row.get("legacy_analysis", {}).get("physical_equipment") is not False
           and (row.get("binding_gaps") or row.get("current_input_binding", {}).get("status") != "BOUND_CURRENT_INPUTS")
           for row in plan["equipment"]):
        failed.append({"gate": "current_plan_input_binding", "reason": "PLAN_HAS_UNRESOLVED_INPUT_BINDING"})
    for gate in plan["required_replay_gates"]:
        reference = replay.get("gates", {}).get(gate)
        if not reference:
            failed.append({"gate": gate, "reason": "missing_receipt"})
            continue
        try:
            receipt = read_reference(root, reference)
        except (ValueError, KeyError, OSError, TypeError) as exc:
            failed.append({"gate": gate, "reason": "RECEIPT_UNREADABLE_OR_DRIFTED", "details": str(exc)})
            continue
        receipt_id = canonical_sha(receipt)
        duplicate = receipt_id in used_receipts
        used_receipts.add(receipt_id)
        identity_ok = (receipt.get("case_id") == plan["case_id"]
                       and receipt.get("candidate_sha256", "").upper() == candidate["sha256"].upper()
                       and receipt.get("source_export_sha256", "").upper() == replay["source_export"]["sha256"].upper()
                       and receipt.get("plan_sha256") == given
                       and bool(replay.get("run_id")) and receipt.get("run_id") == replay.get("run_id")
                       and export.get("case_id") == plan["case_id"] and export.get("run_id") == replay.get("run_id")
                       and export.get("schema") == "equipment-process-canonical-export-v1")
        # Every gate has artifacts which must still exist unchanged. Domain
        # validators supply method/result; self-labeled Boolean alone is denied.
        evidence = receipt.get("evidence", [])
        evidence_ok = bool(evidence)
        reason = "IDENTITY_EVIDENCE_OR_DOMAIN_GATE_NOT_CLOSED"
        try:
            for item in evidence:
                _read_artifact_bytes(root, item)
            domain_ok, reason = validate_domain_receipt(receipt, gate, root, candidate)
        except (ValueError, OSError, KeyError, TypeError) as exc:
            domain_ok, reason = False, "DOMAIN_RECHECK_ERROR: " + str(exc)
        valid = identity_ok and evidence_ok and not duplicate and receipt.get("status") == "strict_passed" and domain_ok
        if not valid:
            failed.append({"gate": gate, "reason": "DUPLICATE_RECEIPT_REUSED_FOR_DIFFERENT_GATE" if duplicate else reason})
        receipts.append({"gate": gate, "valid": valid, "reference": reference})
    return {"schema": "equipment-process-replay-audit-v2", "case_id": plan["case_id"],
            "plan_sha256": given, "candidate": candidate, "receipts": receipts,
            "failed_gates": failed, "evidence_chain_complete": not failed,
            "engineering_accepted": False,
            "boundary": "Checks identity/continuity of domain receipts; does not independently rerun or certify engineering results"}
