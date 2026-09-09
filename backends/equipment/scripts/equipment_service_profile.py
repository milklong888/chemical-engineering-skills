from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Iterable, Mapping


SCHEMA = "equipment-service-profile-v1"
ENGINE_VERSION = "1.1.0"
DIRECT_LABEL_FIELDS = frozenset({
    "service_labels",
    "condition_labels",
    "derived_service_labels",
    "corrosive",
    "corrosivity",
    "toxic",
    "toxicity",
    "flammable",
    "oxidizing",
    "fire_safe_required",
})

NUMERIC_FIELDS: tuple[tuple[str, str], ...] = (
    ("temperature_c", "C"),
    ("pressure_mpa", "MPa"),
    ("mass_flow_kg_h", "kg/h"),
    ("volumetric_flow_m3_h", "m3/h"),
    ("vapor_volumetric_flow_m3_h", "m3/h"),
    ("liquid_volumetric_flow_m3_h", "m3/h"),
    ("density_kg_m3", "kg/m3"),
    ("vapor_fraction", "-"),
    ("liquid_fraction", "-"),
    ("solid_fraction", "-"),
)

MANUAL_FIELD_MAP: tuple[tuple[str, str, str], ...] = (
    ("temperature_c", "temperature_c", "C"),
    ("operating_temperature_c", "temperature_c", "C"),
    ("inlet_temperature_c", "temperature_c", "C"),
    ("outlet_temperature_c", "temperature_c", "C"),
    ("operating_pressure_mpa", "pressure_mpa", "MPa"),
    ("inlet_pressure_mpa", "pressure_mpa", "MPa"),
    ("outlet_pressure_mpa", "pressure_mpa", "MPa"),
    ("flow_m3_h", "volumetric_flow_m3_h", "m3/h"),
    ("mass_flow_kg_h", "mass_flow_kg_h", "kg/h"),
    ("density_kg_m3", "density_kg_m3", "kg/m3"),
    ("vapor_fraction", "vapor_fraction", "-"),
    ("liquid_fraction", "liquid_fraction", "-"),
    ("solid_fraction", "solid_fraction", "-"),
    ("heat_duty_kw", "heat_duty_kw", "kW"),
)

MODULE_TASKS = {
    "PUMP": "liquid_pressure_increase",
    "COMPR": "gas_pressure_increase",
    "MCOMPR": "multistage_gas_pressure_increase",
    "VALVE": "pressure_reduction",
    "HEATER": "one_stream_heat_transfer",
    "HEATX": "two_stream_heat_exchange",
    "RADFRAC": "staged_separation",
    "RATEFRAC": "rate_based_staged_separation",
    "DSTWU": "shortcut_distillation",
    "ABSBR": "absorption_or_stripping",
    "EXTRACT": "liquid_liquid_extraction",
    "FLASH2": "vapor_liquid_flash_separation",
    "FLASH3": "three_phase_flash_separation",
    "DECANTER": "liquid_liquid_separation",
    "SEP": "general_separation",
    "SEP2": "general_separation",
    "BATCHSEP": "batch_separation",
    "CRYSTALLIZER": "solid_crystallization",
    "FILTER": "solid_liquid_filtration",
    "DRYER": "solids_drying",
    "RPLUG": "plug_flow_reaction",
    "RCSTR": "continuous_stirred_tank_reaction",
    "RBATCH": "batch_reaction",
    "RSTOIC": "specified_conversion_reaction",
    "RYIELD": "specified_yield_reaction",
    "RGIBBS": "equilibrium_reaction",
    "FSPLIT": "simulation_flow_split_logic",
    "MIXER": "simulation_mixing_logic",
    "HIERARCHY": "simulation_hierarchy_logic",
}

HAZARD_UNKNOWN_LABELS: tuple[tuple[str, str], ...] = (
    ("service.corrosive", "W_PROPERTY_CORROSIVITY_UNKNOWN"),
    ("safety.toxic", "W_PROPERTY_TOXICITY_UNKNOWN"),
    ("safety.flammable", "W_PROPERTY_FLAMMABILITY_UNKNOWN"),
    ("safety.explosive", "W_PROPERTY_EXPLOSIVITY_UNKNOWN"),
    ("safety.oxidizing", "W_PROPERTY_OXIDIZING_UNKNOWN"),
)
PROPERTY_FACT_LABELS = {
    "corrosivity": "service.corrosive",
    "toxicity": "safety.toxic",
    "flammability": "safety.flammable",
    "explosivity": "safety.explosive",
    "oxidizing": "safety.oxidizing",
    "crevice_corrosion_risk": "service.crevice_corrosion_risk",
    "severe_corrosion": "service.severe_corrosion",
    "cleanliness": "service.cleanliness",
    "leak_tightness": "service.leak_tightness",
    "vacuum_level": "process.vacuum_level",
    "severe_cyclic": "mechanical.severe_cyclic",
    "thermal_shock": "mechanical.thermal_shock",
    "utility_service": "service.utility_service",
    "instrument_service": "service.instrument_service",
    "low_sealing_demand": "service.low_sealing_demand",
    "lining_material": "material.lining_material",
    "flange_material_group": "material.flange_material_group",
    "mating_material_group": "material.mating_material_group",
    "current_facing": "connection.current_facing",
    "ring_joint_required": "connection.ring_joint_required",
    "core_corrosion_risk": "service.core_corrosion_risk",
    "fire_safe_required": "safety.fire_safe_required",
    "cleanability_required": "service.cleanability_required",
    "jacketed_pipe": "connection.jacketed_pipe",
    "orifice_service": "connection.orifice_service",
    "closure_required": "connection.closure_required",
    "internal_component_connection": "connection.internal_component_connection",
}

BOOL_PROPERTY_FACTS = frozenset({
    "oxidizing", "crevice_corrosion_risk", "severe_corrosion", "severe_cyclic",
    "thermal_shock", "utility_service", "instrument_service", "low_sealing_demand",
    "ring_joint_required", "core_corrosion_risk", "fire_safe_required",
    "cleanability_required", "jacketed_pipe", "orifice_service", "closure_required",
    "internal_component_connection",
})
PROPERTY_SEVERITY_ORDER = {
    "corrosivity": ("none", "low", "moderate", "high", "severe"),
    "toxicity": ("normal", "moderate", "high", "extreme"),
    "flammability": ("nonflammable", "flammable", "highly_flammable"),
    "explosivity": ("none", "possible", "explosive"),
    "cleanliness": ("ordinary", "clean", "high_purity", "sterile"),
    "leak_tightness": ("ordinary", "enhanced", "high", "zero_emission"),
    "vacuum_level": ("none", "vacuum", "high_vacuum"),
}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest().upper()


def _label_key(value: Any) -> str:
    text = str(value or "").strip().casefold()
    normalized = "".join(
        character if character.isascii() and character.isalnum() else "_"
        for character in text
    )
    return normalized.strip("_") or "unknown"


def _finite(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _phase(value: Any, vapor_fraction: Any = None, solid_fraction: Any = None) -> tuple[str | None, str]:
    solid = _finite(solid_fraction)
    if solid is not None and 0.0 <= solid <= 1.0 and solid > 1.0e-9:
        return "solid_bearing", "solid_fraction>1e-9"
    vapor = _finite(vapor_fraction)
    if vapor is not None and 0.0 <= vapor <= 1.0:
        if vapor <= 1.0e-9:
            return "liquid", "vapor_fraction<=1e-9"
        if vapor >= 1.0 - 1.0e-9:
            return "vapor", "vapor_fraction>=1-1e-9"
        return "two_phase", "1e-9<vapor_fraction<1-1e-9"
    text = str(value or "").strip().casefold().replace("_", " ")
    aliases = {
        "liquid": "liquid", "liq": "liquid",
        "vapor": "vapor", "vapour": "vapor", "gas": "vapor",
        "mixed": "two_phase", "two phase": "two_phase", "two-phase": "two_phase",
        "multiphase": "two_phase", "solid": "solid_bearing", "solid bearing": "solid_bearing",
    }
    if text in aliases:
        return aliases[text], "explicit_phase"
    return None, "phase_unavailable"


def _stream_kind(stream: Mapping[str, Any]) -> str:
    record_type = str(stream.get("stream_record_type") or "").strip().upper()
    if record_type in {"", "MATERIAL"}:
        return "material"
    if record_type in {"HEAT", "ENERGY", "QSTREAM"}:
        return "heat"
    if record_type in {"WORK", "WSTREAM"}:
        return "work"
    return "unknown"


def _source_path(stream: Mapping[str, Any], field: str) -> str:
    source = stream.get("_sources", {}).get(field, {}) if isinstance(stream.get("_sources"), Mapping) else {}
    if isinstance(source, Mapping) and source.get("source_path"):
        return str(source["source_path"])
    source_field = str(source.get("source_field") or field) if isinstance(source, Mapping) else field
    return f"stream:{stream.get('stream_id', '<unknown>')}.{source_field}"


def _label(
    label_id: str,
    value: Any,
    origin: str,
    evidence_state: str,
    derivation_id: str,
    observation_ids: Iterable[str],
    formula_chain: str,
    *,
    unit: str = "",
    basis: str = "",
    property_record_ids: Iterable[str] = (),
    warning_codes: Iterable[str] = (),
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "label_id": label_id,
        "value": value,
        "unit": unit,
        "basis": basis,
        "label_origin": origin,
        "evidence_state": evidence_state,
        "derivation_id": derivation_id,
        "input_observation_ids": sorted(set(observation_ids)),
        "property_graph_record_ids": sorted(set(property_record_ids)),
        "formula_chain": formula_chain,
        "warning_codes": sorted(set(warning_codes)),
    }
    payload["label_context_sha256"] = _sha256(payload)
    return payload


def _observation(
    observation_id: str,
    field: str,
    value: Any,
    unit: str,
    source_path: str,
    origin: str,
    *,
    stream_id: str = "",
    basis: str = "",
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "observation_id": observation_id,
        "field": field,
        "value": value,
        "unit": unit,
        "basis": basis,
        "source_path": source_path,
        "label_origin": origin,
        "qa_status": "USABLE",
    }
    if stream_id:
        row["stream_id"] = stream_id
    return row


def _composition_rows(stream: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = stream.get("composition")
    if not isinstance(rows, list):
        return []
    result: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        component_id = str(row.get("component_id") or row.get("component") or "").strip().upper()
        fraction = _finite(row.get("fraction", row.get("value")))
        basis = str(row.get("basis") or stream.get("composition_basis") or "").strip().casefold()
        if component_id and fraction is not None and 0.0 <= fraction <= 1.0 and basis in {"mole_fraction", "mass_fraction"}:
            result.append({
                "component_id": component_id,
                "fraction": fraction,
                "basis": basis,
                "source_path": str(row.get("source_path") or f"stream:{stream.get('stream_id')}.composition.{component_id}"),
            })
    return sorted(result, key=lambda item: (item["basis"], item["component_id"]))


def _common_profile(
    *,
    equipment_id: str,
    equipment_family: str,
    block_id: str,
    block_type: str,
    source_bundle_sha256: str,
    boundary_streams: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    direct_label_fields: Iterable[str],
    phase_facts: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    labels: list[dict[str, Any]] = []
    unknowns: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    direct = sorted(set(direct_label_fields))
    if direct:
        diagnostics.append({
            "code": "DIRECT_SERVICE_LABEL_INPUT_IGNORED",
            "scope": "equipment",
            "severity": "warning",
            "detail": "Direct service/condition labels are not authoritative and were ignored: " + ", ".join(direct),
        })

    if block_type:
        labels.append(_label(
            "module.block_type", block_type, "MODULE_TOPOLOGY", "D",
            "module_block_type_identity", (), f"module.block_type = {block_type}",
        ))
        task = MODULE_TASKS.get(block_type, "unregistered_module_task")
        labels.append(_label(
            "module.intent", task, "MODULE_TOPOLOGY", "D" if block_type in MODULE_TASKS else "U",
            "module_task_registry_v2", (), f"module.intent = registry[{block_type}] = {task}",
            warning_codes=() if block_type in MODULE_TASKS else ("W_MODULE_TASK_UNREGISTERED",),
        ))

    by_field: dict[str, list[dict[str, Any]]] = {}
    for observation in observations:
        by_field.setdefault(str(observation["field"]), []).append(observation)

    for field, label_base, unit in (
        ("temperature_c", "process.operating_temperature", "C"),
        ("pressure_mpa", "process.operating_pressure", "MPa"),
    ):
        available = [item for item in by_field.get(field, []) if _finite(item.get("value")) is not None]
        if not available:
            unknowns.append({
                "label_id": label_base + "_envelope",
                "reason": f"No usable connected-stream {field} observation.",
                "minimum_missing_fields": [field],
                "warning_code": "W_TEMPERATURE_ENVELOPE_UNKNOWN" if field == "temperature_c" else "W_PRESSURE_ENVELOPE_UNKNOWN",
            })
            continue
        values = [float(item["value"]) for item in available]
        ids = [str(item["observation_id"]) for item in available]
        substitution = ", ".join(f"{item.get('stream_id', '?')}:{float(item['value']):.12g}" for item in available)
        labels.extend((
            _label(
                label_base + "_min", min(values), "EXACT_DERIVATION", "D", f"{field}_minimum_connected",
                ids, f"{label_base}_min = min({substitution}) = {min(values):.12g} {unit}", unit=unit,
                basis="connected_stream_process_side",
            ),
            _label(
                label_base + "_max", max(values), "EXACT_DERIVATION", "D", f"{field}_maximum_connected",
                ids, f"{label_base}_max = max({substitution}) = {max(values):.12g} {unit}", unit=unit,
                basis="connected_stream_process_side",
            ),
        ))

    phase_fact_rows = [dict(item) for item in phase_facts]
    for fact in phase_fact_rows:
        labels.append(_label(
            f"process.stream_phase.{_label_key(fact.get('direction'))}.{_label_key(fact.get('stream_id'))}",
            str(fact["phase"]), "EXACT_DERIVATION", "D", "stream_phase_normalization_v1",
            fact.get("input_observation_ids", []),
            f"stream_phase = {fact.get('method')} = {fact['phase']}",
        ))
    phases = sorted({str(item["phase"]) for item in phase_fact_rows if item.get("phase")})
    if phases:
        labels.append(_label(
            "process.phase_set", phases, "EXACT_DERIVATION", "D", "connected_phase_union",
            [str(observation_id) for item in phase_fact_rows for observation_id in item.get("input_observation_ids", [])],
            "process.phase_set = sorted(unique(connected material-stream phases)) = " + ",".join(phases),
        ))
    else:
        unknowns.append({
            "label_id": "process.phase_set",
            "reason": "No usable explicit phase or phase-fraction observation.",
            "minimum_missing_fields": ["phase or vapor_fraction"],
            "warning_code": "W_PHASE_UNKNOWN",
        })

    inlet_phases = {str(item["phase"]) for item in phase_fact_rows if item.get("direction") == "inlet"}
    outlet_phases = {str(item["phase"]) for item in phase_fact_rows if item.get("direction") == "outlet"}
    phase_change = None
    if len(inlet_phases) == 1 and len(outlet_phases) == 1:
        before = next(iter(inlet_phases))
        after = next(iter(outlet_phases))
        phase_change = {
            ("liquid", "vapor"): "vaporizing",
            ("liquid", "two_phase"): "partial_vaporizing_or_flashing",
            ("vapor", "liquid"): "condensing",
            ("vapor", "two_phase"): "partial_condensing",
        }.get((before, after), "none" if before == after else "other_phase_transition")
        labels.append(_label(
            "process.phase_change", phase_change, "EXACT_DERIVATION", "D", "inlet_outlet_phase_comparison",
            [str(observation_id) for item in phase_fact_rows for observation_id in item.get("input_observation_ids", [])],
            f"process.phase_change = compare({before},{after}) = {phase_change}",
        ))
    else:
        unknowns.append({
            "label_id": "process.phase_change",
            "reason": "Inlet/outlet phase sets do not each close to one state.",
            "minimum_missing_fields": ["unambiguous inlet phase", "unambiguous outlet phase"],
            "warning_code": "W_PHASE_CHANGE_UNKNOWN",
        })

    inlet_p = [float(item["value"]) for item in observations if item["field"] == "pressure_mpa" and ":inlet:" in item["observation_id"]]
    outlet_p = [float(item["value"]) for item in observations if item["field"] == "pressure_mpa" and ":outlet:" in item["observation_id"]]
    observed_pressure_direction: str | None = None
    if len(inlet_p) == 1 and len(outlet_p) == 1:
        delta = outlet_p[0] - inlet_p[0]
        direction = "increase" if delta > 1.0e-12 else "decrease" if delta < -1.0e-12 else "unchanged"
        observed_pressure_direction = direction
        ids = [item["observation_id"] for item in observations if item["field"] == "pressure_mpa"]
        labels.append(_label(
            "observed.operation.pressure_direction", direction, "EXACT_DERIVATION", "D", "single_inlet_outlet_pressure_delta",
            ids, f"observed_pressure_direction = sign(P_out-P_in) = sign({outlet_p[0]:.12g}-{inlet_p[0]:.12g}) = {direction}", unit="MPa",
        ))

    expected_pressure_direction = {
        "PUMP": "increase", "COMPR": "increase", "MCOMPR": "increase", "VALVE": "decrease",
    }.get(block_type)
    if (
        expected_pressure_direction
        and observed_pressure_direction
        and observed_pressure_direction != expected_pressure_direction
    ):
        diagnostics.append({
            "code": "MODULE_STREAM_CONDITION_CONFLICT",
            "scope": "equipment",
            "severity": "local_blocker",
            "detail": (
                f"module.intent expects pressure {expected_pressure_direction}, but connected-stream "
                f"observed.operation is {observed_pressure_direction}; both observations remain traceable, "
                "but the service profile is not clean for formal use."
            ),
        })

    inlet_t = [float(item["value"]) for item in observations if item["field"] == "temperature_c" and ":inlet:" in item["observation_id"]]
    outlet_t = [float(item["value"]) for item in observations if item["field"] == "temperature_c" and ":outlet:" in item["observation_id"]]
    observed_heat_mode: str | None = None
    heat_ids: list[str] = []
    heat_formula = ""
    if len(inlet_t) == 1 and len(outlet_t) == 1:
        delta_t = outlet_t[0] - inlet_t[0]
        observed_heat_mode = "heating" if delta_t > 1.0e-9 else "cooling" if delta_t < -1.0e-9 else "isothermal"
        heat_ids = [str(item["observation_id"]) for item in observations if item["field"] == "temperature_c"]
        heat_formula = f"observed_heat_mode = sign(T_out-T_in) = sign({outlet_t[0]:.12g}-{inlet_t[0]:.12g}) = {observed_heat_mode}"
    elif block_type == "HEATER":
        duties = [item for item in observations if item["field"] == "heat_duty_kw" and _finite(item.get("value")) is not None]
        if len(duties) == 1:
            duty = float(duties[0]["value"])
            observed_heat_mode = "heating" if duty > 1.0e-12 else "cooling" if duty < -1.0e-12 else "zero_duty_unresolved"
            heat_ids = [str(duties[0]["observation_id"])]
            heat_formula = f"observed_heat_mode = Aspen_Q_sign({duty:.12g} kW) = {observed_heat_mode}"
    if observed_heat_mode:
        labels.append(_label(
            "observed.operation.heat_transfer_mode", observed_heat_mode, "EXACT_DERIVATION", "D",
            "temperature_delta_then_aspen_duty_sign_v1", heat_ids, heat_formula,
        ))

    composition_rows = [item for item in observations if item["field"] == "composition_fraction"]
    component_ids = sorted({str(item["basis"]).split("component:", 1)[-1] for item in composition_rows if "component:" in str(item.get("basis"))})
    if component_ids:
        labels.append(_label(
            "composition.component_ids", component_ids, "EXACT_DERIVATION", "D", "full_connected_composition_component_union",
            [str(item["observation_id"]) for item in composition_rows],
            "composition.component_ids = sorted(unique(all nonnegative exported component IDs))",
        ))

    for label_id, warning_code in HAZARD_UNKNOWN_LABELS:
        unknowns.append({
            "label_id": label_id,
            "reason": "No hash-locked property/compatibility graph join was supplied by the trusted runtime.",
            "minimum_missing_fields": [
                "closed full composition",
                "validated property/compatibility records covering the current composition, phase, temperature and pressure",
            ],
            "warning_code": warning_code,
        })
    diagnostics.append({
        "code": "PROPERTY_LABELS_NOT_GUESSED_FROM_COMPONENT_NAMES",
        "scope": "property_join",
        "severity": "info",
        "detail": "Hazard, corrosivity and material-compatibility labels remain UNKNOWN until a trusted property graph closes them.",
    })

    profile: dict[str, Any] = {
        "schema": SCHEMA,
        "equipment_id": equipment_id,
        "equipment_family": equipment_family,
        "aspen_block_id": block_id,
        "aspen_block_type": block_type,
        "source_bundle_sha256": source_bundle_sha256,
        "boundary_streams": boundary_streams,
        "raw_observations": observations,
        "service_labels": sorted(labels, key=lambda item: item["label_id"]),
        "unknown_labels": sorted(unknowns, key=lambda item: item["label_id"]),
        "diagnostics": diagnostics,
        "runtime_contract": {
            "pdf_access": "FORBIDDEN",
            "image_access": "FORBIDDEN",
            "vision_capability": False,
            "labels_rebuilt_from_raw_input": True,
        },
    }
    profile["profile_context_sha256"] = _sha256(profile)
    return profile


def build_aspen_service_profile(
    *,
    equipment_id: str,
    equipment_family: str,
    block: Mapping[str, Any],
    streams: Mapping[str, Mapping[str, Any]],
    source_bundle_sha256: str,
    raw_direct_label_fields: Iterable[str] = (),
) -> dict[str, Any]:
    block_id = str(block.get("block_id") or equipment_id)
    block_type = str(block.get("block_type") or "").strip().upper()
    boundary: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    phase_facts: list[dict[str, Any]] = []
    for direction, ids in (("inlet", block.get("inlet_streams", [])), ("outlet", block.get("outlet_streams", []))):
        for stream_id_value in ids if isinstance(ids, list) else []:
            stream_id = str(stream_id_value)
            stream = streams.get(stream_id)
            if not isinstance(stream, Mapping):
                continue
            kind = _stream_kind(stream)
            role = "feed" if kind == "material" and direction == "inlet" else "product" if kind == "material" else "utility" if kind in {"heat", "work"} else "unknown"
            boundary.append({"stream_id": stream_id, "stream_kind": kind, "role": role, "direction": direction})
            if kind != "material":
                continue
            for field, unit in NUMERIC_FIELDS:
                value = _finite(stream.get(field))
                if value is None:
                    continue
                observation_id = f"{block_id}:{direction}:{stream_id}:{field}"
                observations.append(_observation(
                    observation_id, field, value, unit, _source_path(stream, field), "ASPEN_RAW_FIELD",
                    stream_id=stream_id,
                ))
            explicit_phase = (
                None
                if str(stream.get("phase_origin") or "").startswith("EXACT_DERIVATION")
                else stream.get("phase")
            )
            phase, method = _phase(explicit_phase, stream.get("vapor_fraction"), stream.get("solid_fraction"))
            if phase:
                input_ids = [
                    str(item["observation_id"])
                    for item in observations
                    if item.get("stream_id") == stream_id
                    and item.get("field") in {"vapor_fraction", "solid_fraction"}
                ]
                if method == "explicit_phase":
                    phase_observation_id = f"{block_id}:{direction}:{stream_id}:phase"
                    observations.append(_observation(
                        phase_observation_id, "phase", phase, "", _source_path(stream, "phase"),
                        "ASPEN_RAW_FIELD", stream_id=stream_id, basis="explicit_aspen_phase_field",
                    ))
                    input_ids.append(phase_observation_id)
                phase_facts.append({
                    "stream_id": stream_id,
                    "direction": direction,
                    "phase": phase,
                    "method": method,
                    "input_observation_ids": input_ids,
                })
            for index, composition in enumerate(_composition_rows(stream)):
                observations.append(_observation(
                    f"{block_id}:{direction}:{stream_id}:composition:{index}",
                    "composition_fraction", composition["fraction"], "-", composition["source_path"],
                    "ASPEN_RAW_FIELD", stream_id=stream_id,
                    basis=f"{composition['basis']};component:{composition['component_id']}",
                ))
    heat_duty = _finite(block.get("heat_duty_kw"))
    if heat_duty is not None:
        block_sources = block.get("_sources") if isinstance(block.get("_sources"), Mapping) else {}
        duty_source = block_sources.get("heat_duty_kw", {}) if isinstance(block_sources, Mapping) else {}
        source_field = str(duty_source.get("source_field") or "heat_duty_kw") if isinstance(duty_source, Mapping) else "heat_duty_kw"
        observations.append(_observation(
            f"{block_id}:block:{block_id}:heat_duty_kw",
            "heat_duty_kw",
            heat_duty,
            "kW",
            str(duty_source.get("source_path") or f"block:{block_id}.{source_field}") if isinstance(duty_source, Mapping) else f"block:{block_id}.{source_field}",
            "ASPEN_RAW_FIELD",
            basis="Aspen block duty; positive sign means heat added by the block",
        ))
    return _common_profile(
        equipment_id=equipment_id,
        equipment_family=equipment_family,
        block_id=block_id,
        block_type=block_type,
        source_bundle_sha256=source_bundle_sha256,
        boundary_streams=boundary,
        observations=observations,
        direct_label_fields=raw_direct_label_fields,
        phase_facts=phase_facts,
    )


def build_manual_service_profile(
    raw: Mapping[str, Any],
    *,
    equipment_id: str = "MANUAL-EQUIPMENT",
    equipment_family: str = "",
    block_type: str = "",
) -> dict[str, Any]:
    source_hash = _sha256(raw)
    direct = [field for field in raw if field in DIRECT_LABEL_FIELDS]
    observations: list[dict[str, Any]] = []
    phase_facts: list[dict[str, Any]] = []
    seen_targets: set[str] = set()
    for source_field, target_field, unit in MANUAL_FIELD_MAP:
        if source_field in seen_targets or source_field not in raw:
            continue
        value = _finite(raw.get(source_field))
        if value is None:
            continue
        seen_targets.add(source_field)
        role = "inlet" if source_field.startswith("inlet_") else "outlet" if source_field.startswith("outlet_") else "unknown"
        observations.append(_observation(
            f"{equipment_id}:{role}:MANUAL:{source_field}", target_field, value, unit,
            f"manual_input.{source_field}", "MANUAL_RAW_FIELD", stream_id="MANUAL", basis="user_supplied_raw_process_field",
        ))
    for direction in ("inlet", "outlet"):
        prefix = direction + "_"
        has_directional = any(
            field in raw
            for field in (
                prefix + "temperature_c",
                prefix + "pressure_mpa",
                prefix + "phase",
                prefix + "vapor_fraction",
                prefix + "solid_fraction",
            )
        )
        if direction != "inlet" and not has_directional:
            continue
        phase, method = _phase(
            raw.get(prefix + "phase", raw.get("phase")),
            raw.get(prefix + "vapor_fraction", raw.get("vapor_fraction")),
            raw.get(prefix + "solid_fraction", raw.get("solid_fraction")),
        )
        if not phase:
            continue
        stream_id = f"MANUAL:{direction.upper()}"
        phase_observation_id = f"{equipment_id}:{direction}:{stream_id}:phase"
        observations.append(_observation(
            phase_observation_id,
            "phase",
            phase,
            "",
            f"manual_input.{prefix}phase_or_fraction",
            "MANUAL_RAW_FIELD",
            stream_id=stream_id,
            basis=method,
        ))
        phase_facts.append({
            "stream_id": stream_id,
            "direction": direction,
            "phase": phase,
            "method": method,
            "input_observation_ids": [phase_observation_id],
        })
    effective_block_type = str(block_type or raw.get("aspen_block_type") or "").strip().upper()
    effective_family = str(equipment_family or raw.get("equipment_family") or "")
    return _common_profile(
        equipment_id=equipment_id,
        equipment_family=effective_family,
        block_id="",
        block_type=effective_block_type,
        source_bundle_sha256=source_hash,
        boundary_streams=[],
        observations=observations,
        direct_label_fields=direct,
        phase_facts=phase_facts,
    )


def enrich_with_connection_property_facts(
    profile: Mapping[str, Any],
    connection_package: Mapping[str, Any],
) -> dict[str, Any]:
    """Merge only facts already accepted by the deterministic connection join."""

    enriched = json.loads(json.dumps(profile, ensure_ascii=False))
    if (
        connection_package.get("schema") != "equipment-connection-selection-package-v1"
        or connection_package.get("deterministic") is not True
        or connection_package.get("source_export_sha256") != profile.get("source_bundle_sha256")
    ):
        return enriched
    grouped: dict[str, list[dict[str, Any]]] = {}
    for connection in connection_package.get("connections", []):
        if not isinstance(connection, Mapping):
            continue
        for fact in connection.get("accepted_property_facts", []):
            if not isinstance(fact, Mapping):
                continue
            fact_name = str(fact.get("fact") or "")
            label_id = PROPERTY_FACT_LABELS.get(fact_name)
            if not label_id:
                continue
            if not all(str(fact.get(field) or "") for field in (
                "source_id", "source_asset_sha256", "source_record_sha256",
            )):
                continue
            grouped.setdefault(fact_name, []).append({
                "connection_id": connection.get("connection_id"),
                "label_id": label_id,
                **dict(fact),
            })
    if not grouped:
        return enriched
    base_label_ids = {str(rows[0]["label_id"]) for rows in grouped.values() if rows}
    labels = [
        item for item in enriched.get("service_labels", [])
        if isinstance(item, dict) and item.get("label_id") not in base_label_ids
    ]
    unknowns = [
        item for item in enriched.get("unknown_labels", [])
        if isinstance(item, dict) and item.get("label_id") not in base_label_ids
    ]
    diagnostics = list(enriched.get("diagnostics", []))

    def record_ids(rows: Iterable[Mapping[str, Any]]) -> list[str]:
        return sorted({
            f"{item.get('source_id')}:{item.get('source_record_sha256')}"
            for item in rows
            if item.get("source_id") and item.get("source_record_sha256")
        })

    def distinct_values(rows: Iterable[Mapping[str, Any]]) -> list[Any]:
        values: dict[str, Any] = {}
        for item in rows:
            value = item.get("value")
            values[_canonical(value)] = value
        return [values[key] for key in sorted(values)]

    for fact_name, facts in sorted(grouped.items()):
        label_id = str(facts[0]["label_id"])
        by_connection: dict[str, list[dict[str, Any]]] = {}
        for fact in facts:
            by_connection.setdefault(str(fact.get("connection_id") or "UNKNOWN"), []).append(fact)
        usable_connection_values: list[Any] = []
        for connection_id, connection_facts in sorted(by_connection.items()):
            values = distinct_values(connection_facts)
            scoped_label_id = f"connection.{_label_key(connection_id)}.{label_id}"
            if len(values) != 1:
                diagnostics.append({
                    "code": "PROPERTY_FACT_CONFLICT",
                    "scope": "property_join",
                    "severity": "local_blocker",
                    "detail": f"Conflicting {fact_name} facts remain on connection {connection_id}; no connection label was promoted.",
                })
                continue
            value = values[0]
            usable_connection_values.append(value)
            sources = sorted({str(item["source_id"]) for item in connection_facts})
            labels.append(_label(
                scoped_label_id,
                value,
                "PROPERTY_GRAPH_JOIN",
                "D",
                "hash_locked_connection_property_join_v2",
                (),
                f"{scoped_label_id} = validated_property_join(connection={connection_id};sources={','.join(sources)}) = {value}",
                basis="exact_connection_composition_phase_temperature_pressure",
                property_record_ids=record_ids(connection_facts),
            ))

        if not usable_connection_values:
            unknowns.append({
                "label_id": label_id,
                "reason": "No conflict-free connection-scoped property fact remained after evidence binding.",
                "minimum_missing_fields": ["conflict-free connection-scoped property evidence"],
                "warning_code": "W_PROPERTY_FACT_CONFLICT",
            })
            continue

        envelope_value: Any | None = None
        envelope_method = ""
        if fact_name in BOOL_PROPERTY_FACTS and all(isinstance(value, bool) for value in usable_connection_values):
            envelope_value = any(usable_connection_values)
            envelope_method = "conservative_boolean_any_true"
        elif fact_name in PROPERTY_SEVERITY_ORDER:
            order = PROPERTY_SEVERITY_ORDER[fact_name]
            if all(str(value) in order for value in usable_connection_values):
                envelope_value = max(usable_connection_values, key=lambda value: order.index(str(value)))
                envelope_method = "most_restrictive_registered_severity"
        else:
            values = {_canonical(value): value for value in usable_connection_values}
            if len(values) == 1:
                envelope_value = next(iter(values.values()))
                envelope_method = "identical_across_connections"
        if envelope_value is None:
            diagnostics.append({
                "code": "PROPERTY_FACT_EQUIPMENT_ENVELOPE_CONFLICT",
                "scope": "property_join",
                "severity": "local_blocker",
                "detail": f"Connection-scoped {fact_name} values cannot be conservatively aggregated to one equipment label.",
            })
            unknowns.append({
                "label_id": label_id,
                "reason": "Connection-scoped facts differ and no registered conservative aggregation exists.",
                "minimum_missing_fields": ["engineering ruling for connection-to-equipment aggregation"],
                "warning_code": "W_PROPERTY_EQUIPMENT_ENVELOPE_CONFLICT",
            })
            continue
        labels.append(_label(
            label_id,
            envelope_value,
            "PROPERTY_GRAPH_JOIN",
            "D",
            "connection_to_equipment_property_envelope_v1",
            (),
            f"{label_id} = {envelope_method}(connection-scoped {fact_name}) = {envelope_value}",
            basis="equipment_envelope_from_exact_connection_facts",
            property_record_ids=record_ids(facts),
        ))
    enriched["service_labels"] = sorted(labels, key=lambda item: item["label_id"])
    enriched["unknown_labels"] = sorted(unknowns, key=lambda item: item["label_id"])
    enriched["diagnostics"] = diagnostics
    enriched["accepted_connection_property_facts"] = [
        item for label_id in sorted(grouped) for item in grouped[label_id]
    ]
    enriched["profile_context_sha256"] = _sha256({
        key: value for key, value in enriched.items() if key != "profile_context_sha256"
    })
    return enriched


__all__ = [
    "DIRECT_LABEL_FIELDS",
    "ENGINE_VERSION",
    "build_aspen_service_profile",
    "build_manual_service_profile",
    "enrich_with_connection_property_facts",
]
