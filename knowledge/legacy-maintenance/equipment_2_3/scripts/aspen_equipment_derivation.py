from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

import equipment_design_match as matcher
import equipment_service_profile as service_profile
import connection_component_selection as connection_selection


SCRIPT_PATH = Path(__file__).resolve()
FROZEN_ROOT = getattr(sys, "_MEIPASS", None)
PACKAGE_ROOT = Path(FROZEN_ROOT).resolve() if FROZEN_ROOT else SCRIPT_PATH.parents[1]
SCHEMA_PATH = PACKAGE_ROOT / "knowledge_graph" / "aspen_equipment_export.schema.json"
ENGINE_VERSION = "1.6.0"
SINGLE_INLET_OUTLET_BLOCKS = {"PUMP", "COMPR", "MCOMPR", "VALVE", "HEATER"}
CLEAN_BLOCK_WORDS = {"0", "ok", "pass", "passed", "converged", "success", "successful", "完成", "正常"}
SIMULATION_LOGIC_BLOCK_TYPES = frozenset({"FSPLIT", "MIXER", "HIERARCHY"})
TOWER_BLOCK_TYPES = frozenset({"RADFRAC", "RATEFRAC", "DSTWU", "ABSBR", "EXTRACT"})
SIMULATION_LOGIC_STATUS = "NOT_APPLICABLE"
SIMULATION_LOGIC_REASON = "NOT_APPLICABLE_SIMULATION_LOGIC_NODE"
FIELD_LOCAL_DIAGNOSTIC_CODES = frozenset({
    "NON_NUMERIC_ASPEN_VALUE",
    "MISSING_EXPLICIT_ASPEN_UNIT",
    "UNSUPPORTED_ASPEN_UNIT",
    "CONFLICTING_ASPEN_ALIASES",
    "ASPEN_VALUE_OUTSIDE_HARD_SANITY_RANGE",
    "ASPEN_MASS_VOLUME_DENSITY_INCONSISTENT",
    "ASPEN_COMPOSITION_FRACTION_INVALID",
    "ASPEN_COMPOSITION_NOT_CLOSED",
    "ASPEN_COMPOSITION_BASIS_CONFLICT",
})


# These are sentinel/failed-run guards, not equipment design limits.  Each
# bound is deliberately many orders of magnitude above a credible single
# chemical-process equipment duty so unusual but finite Aspen placeholders do
# not enter sizing equations or engineering designations.  Values inside the
# bounds still need the ordinary formula, software and vendor evidence gates.
ASPEN_HARD_SANITY_RANGES: dict[str, tuple[float, float]] = {
    "mass_flow_kg_h": (0.0, 1.0e15),
    "volumetric_flow_m3_h": (0.0, 1.0e15),
    "vapor_volumetric_flow_m3_h": (0.0, 1.0e15),
    "liquid_volumetric_flow_m3_h": (0.0, 1.0e15),
    "heat_duty_kw": (-1.0e12, 1.0e12),
    "heat_transfer_area_m2": (0.0, 1.0e12),
    "shaft_power_kw": (-1.0e12, 1.0e12),
    "volume_m3": (0.0, 1.0e12),
    "diameter_mm": (0.0, 1.0e9),
    "height_mm": (0.0, 1.0e9),
}


STREAM_ALIASES: dict[str, list[tuple[str, str | None, bool]]] = {
    "temperature_c": [
        ("temperature_c", "C", False), ("temp_c", "C", False), ("T_C", "C", False),
        ("TEMP_OUT", None, True),
    ],
    "pressure_mpa": [
        ("pressure_mpa", "MPa", False), ("pressure_bar", "bar", False),
        ("pres_bar", "bar", False), ("P_bar", "bar", False), ("PRES_OUT", None, True),
    ],
    "mass_flow_kg_h": [
        ("mass_flow_kg_h", "kg/h", False), ("mass_kg_h", "kg/h", False),
        ("MASSFLMX", None, True),
    ],
    "volumetric_flow_m3_h": [
        ("volumetric_flow_m3_h", "m3/h", False), ("vol_m3_h", "m3/h", False),
        ("VOLFLMX", None, True),
    ],
    "vapor_volumetric_flow_m3_h": [
        ("vapor_volumetric_flow_m3_h", "m3/h", False), ("vol_gas_m3_h", "m3/h", False),
        ("VOLFLMX_GAS", None, True),
    ],
    "liquid_volumetric_flow_m3_h": [
        ("liquid_volumetric_flow_m3_h", "m3/h", False), ("vol_liq_m3_h", "m3/h", False),
        ("VOLFLMX_LIQ", None, True),
    ],
    "density_kg_m3": [
        ("density_kg_m3", "kg/m3", False), ("rho_kg_m3", "kg/m3", False),
    ],
    "vapor_fraction": [
        ("vapor_fraction", "-", False), ("vfrac", "-", False), ("VFRAC_OUT", "-", False),
    ],
    "liquid_fraction": [
        ("liquid_fraction", "-", False), ("lfrac", "-", False), ("LFRAC_OUT", "-", False),
    ],
    "solid_fraction": [
        ("solid_fraction", "-", False), ("sfrac", "-", False),
        ("SFRAC_OUT", "-", False), ("SOLIDFRAC_OUT", "-", False),
    ],
    "molecular_weight": [
        ("molecular_weight", "kg/kmol", False), ("gas_molecular_weight", "kg/kmol", False),
    ],
    "compressibility_factor": [
        ("compressibility_factor", "-", False), ("z_factor", "-", False),
    ],
}


BLOCK_ALIASES: dict[str, list[tuple[str, str | None, bool]]] = {
    "heat_duty_kw": [
        ("heat_duty_kw", "kW", False), ("QCALC", None, True), ("QNET", None, True),
        ("DUTY_OUT", None, True),
    ],
    "heat_transfer_area_m2": [
        ("heat_transfer_area_m2", "m2", False), ("AREA", None, True),
    ],
    "shaft_power_kw": [
        ("shaft_power_kw", "kW", False), ("BRAKE_POWER", None, True),
        ("ELEC_POWER", None, True), ("WNET", None, True),
    ],
    "head_m": [("head_m", "m", False), ("HEAD_CAL", None, True)],
    "npsha_m": [("npsha_m", "m", False), ("NPSHA", None, True)],
    "efficiency_percent": [
        ("efficiency_percent", "percent", False),
        # Aspen pump/compressor Input\SEFF is exported as CEFF with an empty
        # UnitString.  SEFF is a dimensionless efficiency fraction by
        # definition, so it must be converted to percent rather than silently
        # treating the raw value as already-percent.
        ("CEFF", "fraction", False), ("SEFF", "fraction", False),
    ],
    "pressure_drop_kpa": [
        ("pressure_drop_kpa", "kPa", False), ("DELP_CAL", None, True), ("PDRP", None, True),
    ],
    "reported_pressure_ratio": [
        ("pressure_ratio", "-", False), ("PRES_RATIO", "-", False),
    ],
    "stage_count": [("stage_count", "-", False), ("NSTAGE", "-", False)],
    "volume_m3": [("volume_m3", "m3", False), ("VOLUME", None, True)],
    "diameter_mm": [("diameter_mm", "mm", False), ("DIAMETER", None, True)],
    "height_mm": [("height_mm", "mm", False), ("HEIGHT", None, True)],
}


CANONICAL_UNITS = {
    "temperature_c": "C",
    "pressure_mpa": "MPa",
    "mass_flow_kg_h": "kg/h",
    "volumetric_flow_m3_h": "m3/h",
    "vapor_volumetric_flow_m3_h": "m3/h",
    "liquid_volumetric_flow_m3_h": "m3/h",
    "density_kg_m3": "kg/m3",
    "vapor_fraction": "-",
    "liquid_fraction": "-",
    "solid_fraction": "-",
    "molecular_weight": "kg/kmol",
    "compressibility_factor": "-",
    "heat_duty_kw": "kW",
    "heat_transfer_area_m2": "m2",
    "shaft_power_kw": "kW",
    "head_m": "m",
    "npsha_m": "m",
    "efficiency_percent": "percent",
    "pressure_drop_kpa": "kPa",
    "reported_pressure_ratio": "-",
    "stage_count": "-",
    "volume_m3": "m3",
    "diameter_mm": "mm",
    "inner_diameter_mm": "mm",
    "height_mm": "mm",
}


# PFD cards consume these already-normalized projections.  The mapping layer
# must never read an Aspen alias such as WNET/QCALC and then attach a target
# unit to the untouched raw number.  Keeping this projection here makes the
# derivation adapter's single unit registry authoritative for matching, PFD
# display, the Agent protocol and the GUI.
PFD_BLOCK_PARAMETER_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("heat_duty_kw", "heat_duty_kw", "kW"),
    ("heat_transfer_area_m2", "heat_transfer_area_m2", "m²"),
    ("shaft_power_kw", "shaft_power_kw", "kW"),
    ("head_m", "head_m", "m"),
    ("npsha_m", "npsha_m", "m"),
    ("efficiency_percent", "efficiency_percent", "%"),
    ("pressure_drop_kpa", "pressure_drop_kpa", "kPa"),
    ("reported_pressure_ratio", "pressure_ratio", ""),
    ("stage_count", "stage_count", ""),
    ("volume_m3", "volume_m3", "m³"),
    ("diameter_mm", "diameter_mm", "mm"),
    ("height_mm", "height_mm", "mm"),
)

PFD_STREAM_PARAMETER_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("temperature_c", "temperature_c", "°C"),
    ("pressure_mpa", "pressure_mpa", "MPa"),
    ("mass_flow_kg_h", "mass_flow_kg_h", "kg/h"),
    ("volumetric_flow_m3_h", "volumetric_flow_m3_h", "m³/h"),
    ("vapor_fraction", "vapor_fraction", ""),
    ("density_kg_m3", "density_kg_m3", "kg/m³"),
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def finite_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    if isinstance(value, str):
        try:
            parsed = float(value.strip())
        except ValueError:
            return None
        return parsed if math.isfinite(parsed) else None
    return None


def nonnegative_integer(value: Any) -> int | None:
    number = finite_number(value)
    if number is None or number < 0 or not number.is_integer():
        return None
    return int(number)


def normalize_unit(unit: str) -> str:
    text = unit.strip().casefold().replace("³", "3").replace("²", "2").replace("·", "")
    aliases = {
        "c": "C", "°c": "C", "℃": "C", "k": "K",
        "mpa": "MPa", "kpa": "kPa", "pa": "Pa", "bar": "bar", "atm": "atm",
        "kg/h": "kg/h", "kg/hr": "kg/h", "kg/s": "kg/s", "t/h": "t/h",
        "m3/h": "m3/h", "m^3/h": "m3/h", "cum/hr": "m3/h",
        "m3/s": "m3/s", "m^3/s": "m3/s",
        "l/min": "L/min",
        "kg/m3": "kg/m3", "kg/m^3": "kg/m3", "kg/cum": "kg/m3",
        "gm/cc": "g/cm3", "g/cm3": "g/cm3", "g/cm^3": "g/cm3",
        "kw": "kW", "w": "W", "watt": "W", "mw": "MW",
        "cal/sec": "cal/s", "cal/s": "cal/s",
        "kcal/h": "kcal/h", "kcal/hr": "kcal/h",
        "gcal/h": "Gcal/h", "gcal/hr": "Gcal/h",
        "m2": "m2", "m^2": "m2", "sqm": "m2",
        "m": "m", "meter": "m", "meters": "m", "metre": "m", "metres": "m",
        "mm": "mm", "millimeter": "mm", "millimeters": "mm",
        "millimetre": "mm", "millimetres": "mm", "cum": "m3",
        "m-kgf/kg": "m-kgf/kg", "j/kg": "J/kg",
        "%": "percent", "percent": "percent", "fraction": "fraction",
        "-": "-", "1": "-", "kg/kmol": "kg/kmol",
    }
    return aliases.get(text, unit.strip())


def convert(value: float, source_unit: str, target_unit: str) -> tuple[float, str]:
    source = normalize_unit(source_unit)
    target = normalize_unit(target_unit)
    if source == target:
        return value, "identity"
    conversions: dict[tuple[str, str], tuple[float, float, str]] = {
        ("K", "C"): (1.0, -273.15, "T_C=T_K-273.15"),
        ("bar", "MPa"): (0.1, 0.0, "P_MPa=P_bar×0.1"),
        ("atm", "MPa"): (0.101325, 0.0, "P_MPa=P_atm×0.101325"),
        ("kPa", "MPa"): (0.001, 0.0, "P_MPa=P_kPa×0.001"),
        ("Pa", "MPa"): (1e-6, 0.0, "P_MPa=P_Pa×10^-6"),
        ("kg/s", "kg/h"): (3600.0, 0.0, "m_kg/h=m_kg/s×3600"),
        ("t/h", "kg/h"): (1000.0, 0.0, "m_kg/h=m_t/h×1000"),
        ("m3/s", "m3/h"): (3600.0, 0.0, "V_m3/h=V_m3/s×3600"),
        ("L/min", "m3/h"): (0.06, 0.0, "V_m3_per_h=V_L_per_min×0.06"),
        ("g/cm3", "kg/m3"): (1000.0, 0.0, "rho_kg_per_m3=rho_g_per_cm3×1000"),
        ("W", "kW"): (0.001, 0.0, "Q_kW=Q_W×0.001"),
        ("MW", "kW"): (1000.0, 0.0, "Q_kW=Q_MW×1000"),
        ("cal/s", "kW"): (0.004184, 0.0, "Q_kW=Q_cal_per_s×0.004184"),
        ("kcal/h", "kW"): (4.184 / 3600.0, 0.0, "Q_kW=Q_kcal_per_h×0.00116222222222"),
        ("Gcal/h", "kW"): (4.184e6 / 3600.0, 0.0, "Q_kW=Q_Gcal_per_h×1162.22222222"),
        ("fraction", "percent"): (100.0, 0.0, "eta_percent=eta_fraction×100"),
        ("m-kgf/kg", "m"): (1.0, 0.0, "H_m=E_mkgf_per_kg×9.80665/9.80665"),
        ("J/kg", "m"): (1.0 / 9.80665, 0.0, "H_m=E_J_per_kg/9.80665"),
        ("bar", "kPa"): (100.0, 0.0, "dP_kPa=dP_bar×100"),
        ("atm", "kPa"): (101.325, 0.0, "dP_kPa=dP_atm×101.325"),
        ("m", "mm"): (1000.0, 0.0, "L_mm=L_m×1000"),
        ("mm", "m"): (0.001, 0.0, "L_m=L_mm×0.001"),
    }
    spec = conversions.get((source, target))
    if spec is None:
        raise ValueError(f"unsupported unit conversion: {source_unit} -> {target_unit}")
    factor, offset, formula = spec
    return value * factor + offset, formula


def partition_normalization_errors(
    items: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Keep field-level Aspen oddities local; structural identity errors still fail closed."""

    structural: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    for item in items:
        if str(item.get("code") or "") in FIELD_LOCAL_DIAGNOSTIC_CODES:
            diagnostics.append({
                **item,
                "status": "IGNORED_FIELD_UNAVAILABLE",
                "scope": "TARGET_FIELD_ONLY",
                "downstream_policy": (
                    "Ignore this source field; continue every other equipment/parameter calculation. "
                    "Only conclusions that require the unavailable canonical target remain open."
                ),
            })
        else:
            structural.append(item)
    return structural, diagnostics


def unit_for(
    units: dict[str, Any],
    scope: str,
    field: str,
    object_id: str | None = None,
) -> str | None:
    keys: list[str] = []
    if object_id:
        keys.append(f"{scope}.{object_id}.{field}")
    keys.extend((f"{scope}.{field}", field))
    for key in keys:
        if key in units and str(units[key]).strip():
            return str(units[key]).strip()
    return None


def extract_numeric_fields(
    row: dict[str, Any],
    aliases: dict[str, list[tuple[str, str | None, bool]]],
    units: dict[str, Any],
    scope: str,
    object_id: str,
) -> tuple[dict[str, float], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    values: dict[str, float] = {}
    sources: dict[str, dict[str, Any]] = {}
    errors: list[dict[str, Any]] = []
    for target, candidates in aliases.items():
        observations: list[tuple[float, dict[str, Any]]] = []
        target_failed = False
        for source_field, default_unit, needs_declared_unit in candidates:
            if source_field not in row or row[source_field] in (None, ""):
                continue
            raw = finite_number(row[source_field])
            if raw is None:
                errors.append({"object": object_id, "field": source_field, "code": "NON_NUMERIC_ASPEN_VALUE", "value": row[source_field]})
                target_failed = True
                continue
            source_unit = unit_for(units, scope, source_field, object_id) or default_unit
            if needs_declared_unit and source_unit is None:
                errors.append({"object": object_id, "field": source_field, "code": "MISSING_EXPLICIT_ASPEN_UNIT"})
                target_failed = True
                continue
            try:
                converted, transform = convert(raw, source_unit or CANONICAL_UNITS[target], CANONICAL_UNITS[target])
            except ValueError as exc:
                errors.append({"object": object_id, "field": source_field, "code": "UNSUPPORTED_ASPEN_UNIT", "detail": str(exc)})
                target_failed = True
                continue
            hard_range = ASPEN_HARD_SANITY_RANGES.get(target)
            if hard_range is not None and not (hard_range[0] <= converted <= hard_range[1]):
                errors.append({
                    "object": object_id,
                    "field": source_field,
                    "canonical_field": target,
                    "code": "ASPEN_VALUE_OUTSIDE_HARD_SANITY_RANGE",
                    "raw_value": raw,
                    "raw_unit": normalize_unit(source_unit or CANONICAL_UNITS[target]),
                    "canonical_value": converted,
                    "canonical_unit": CANONICAL_UNITS[target],
                    "hard_min": hard_range[0],
                    "hard_max": hard_range[1],
                    "detail": (
                        "Finite Aspen value exceeds the non-design sentinel guard and is excluded "
                        "from the effective parameter package."
                    ),
                })
                target_failed = True
                continue
            observations.append((converted, {
                    "source_field": source_field,
                    "source_path": str(
                        (row.get("aspen_raw_paths") or {}).get(source_field)
                        if isinstance(row.get("aspen_raw_paths"), dict)
                        else ""
                    ) or f"{scope}:{object_id}.{source_field}",
                    "raw_value": raw,
                    "source_unit": normalize_unit(source_unit or CANONICAL_UNITS[target]),
                    "transform": transform,
                }))
        if target_failed or not observations:
            continue
        reference = observations[0][0]
        if any(not math.isclose(reference, value, rel_tol=1e-9, abs_tol=1e-12) for value, _ in observations[1:]):
            errors.append({
                "object": object_id,
                "field": target,
                "code": "CONFLICTING_ASPEN_ALIASES",
                "observations": [
                    {"source_field": source["source_field"], "canonical_value": value, "canonical_unit": CANONICAL_UNITS[target]}
                    for value, source in observations
                ],
            })
            continue
        values[target] = reference
        sources[target] = {
            **observations[0][1],
            "corroborating_aliases": [source["source_field"] for _, source in observations[1:]],
        }
    return values, sources, errors


def list_value(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value in (None, ""):
        return []
    return [item.strip() for item in str(value).replace("；", ",").replace(";", ",").split(",") if item.strip()]


def normalize_composition(row: dict[str, Any], stream_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Normalize a complete composition vector and isolate bad vectors locally."""

    errors: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    raw_list = row.get("composition")
    if isinstance(raw_list, list):
        candidates.extend(dict(item) for item in raw_list if isinstance(item, dict))
    else:
        for key, basis in (
            ("component_mole_fractions", "mole_fraction"),
            ("mole_fractions", "mole_fraction"),
            ("component_mass_fractions", "mass_fraction"),
            ("mass_fractions", "mass_fraction"),
        ):
            values = row.get(key)
            if not isinstance(values, dict):
                continue
            candidates.extend({
                "component_id": str(component_id),
                "fraction": fraction,
                "basis": basis,
                "source_path": f"stream:{stream_id}.{key}.{component_id}",
            } for component_id, fraction in values.items())
            break
    if not candidates:
        return [], errors

    normalized: list[dict[str, Any]] = []
    bases: set[str] = set()
    for item in candidates:
        component_id = str(item.get("component_id") or item.get("component") or "").strip().upper()
        fraction = finite_number(item.get("fraction", item.get("value")))
        basis = str(item.get("basis") or row.get("composition_basis") or "").strip().casefold()
        if not component_id or fraction is None or not 0.0 <= fraction <= 1.0 or basis not in {"mole_fraction", "mass_fraction"}:
            errors.append({
                "object": stream_id,
                "field": "composition",
                "code": "ASPEN_COMPOSITION_FRACTION_INVALID",
                "component_id": component_id,
                "value": item.get("fraction", item.get("value")),
                "basis": basis,
            })
            continue
        bases.add(basis)
        normalized.append({
            "component_id": component_id,
            "fraction": fraction,
            "basis": basis,
            "source_path": str(item.get("source_path") or f"stream:{stream_id}.composition.{component_id}"),
        })
    if errors:
        return [], errors
    if len(bases) != 1:
        return [], [{
            "object": stream_id,
            "field": "composition",
            "code": "ASPEN_COMPOSITION_BASIS_CONFLICT",
            "bases": sorted(bases),
        }]
    component_ids = [str(item["component_id"]) for item in normalized]
    if len(component_ids) != len(set(component_ids)):
        return [], [{
            "object": stream_id,
            "field": "composition",
            "code": "ASPEN_COMPOSITION_COMPONENT_ID_DUPLICATE",
            "component_ids": sorted(component_ids),
        }]
    total = sum(float(item["fraction"]) for item in normalized)
    if not math.isclose(total, 1.0, rel_tol=1.0e-6, abs_tol=1.0e-8):
        return [], [{
            "object": stream_id,
            "field": "composition",
            "code": "ASPEN_COMPOSITION_NOT_CLOSED",
            "fraction_sum": total,
            "tolerance": {"relative": 1.0e-6, "absolute": 1.0e-8},
        }]
    return sorted(normalized, key=lambda item: item["component_id"]), []


def normalize_stream(row: dict[str, Any], units: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    stream_id = str(row.get("stream_id") or row.get("stream") or row.get("id") or "").strip()
    values, sources, errors = extract_numeric_fields(row, STREAM_ALIASES, units, "stream", stream_id or "<missing>")
    composition, composition_errors = normalize_composition(row, stream_id or "<missing>")
    errors.extend(composition_errors)
    for fraction_field in ("vapor_fraction", "liquid_fraction", "solid_fraction"):
        value = values.get(fraction_field)
        if value is None or 0.0 <= float(value) <= 1.0:
            continue
        source = sources.get(fraction_field, {})
        errors.append({
            "object": stream_id or "<missing>",
            "field": str(source.get("source_field") or fraction_field),
            "canonical_field": fraction_field,
            "code": "ASPEN_PHASE_FRACTION_OUT_OF_RANGE",
            "value": value,
            "allowed_range": [0.0, 1.0],
            "detail": "Invalid phase fraction is isolated locally and cannot create a phase/service label.",
        })
        values.pop(fraction_field, None)
        sources.pop(fraction_field, None)
    result = {
        "stream_id": stream_id,
        **values,
        "stream_record_type": str(row.get("stream_record_type") or "").strip().upper(),
        "stream_record_type_source": row.get("stream_record_type_source"),
        "phase": row.get("phase") or row.get("comptype") or "",
        "phase_origin": row.get("phase_origin") or "ASPEN_EXPORTED_OR_ADAPTER_RAW_FIELD",
        "phase_source_field": row.get("phase_source_field") or "phase",
        "dominant_components": row.get("dominant_components") or row.get("dominant") or "",
        "composition": composition,
        "composition_basis": composition[0]["basis"] if composition else "",
        "_sources": sources,
    }
    if not stream_id:
        errors.append({"object": "<stream>", "field": "stream_id", "code": "MISSING_STREAM_ID"})
    if "density_kg_m3" not in result:
        mass = result.get("mass_flow_kg_h")
        volume = result.get("volumetric_flow_m3_h")
        if mass is not None and volume and volume > 0:
            result["density_kg_m3"] = mass / volume
            result["_sources"]["density_kg_m3"] = {
                "source_field": "mass_flow_kg_h/volumetric_flow_m3_h",
                "raw_value": [mass, volume],
                "source_unit": "kg/h,m3/h",
                "transform": "rho=m_dot/V_dot",
            }
    else:
        mass = result.get("mass_flow_kg_h")
        volume = result.get("volumetric_flow_m3_h")
        density = result.get("density_kg_m3")
        if mass is not None and volume is not None and volume > 0 and density is not None and density > 0:
            implied_density = mass / volume
            ratio = implied_density / density
            if ratio < 0.1 or ratio > 10.0:
                source = result.get("_sources", {}).get("density_kg_m3", {})
                errors.append({
                    "object": stream_id or "<missing>",
                    "field": str(source.get("source_field") or "density_kg_m3"),
                    "canonical_field": "density_kg_m3",
                    "code": "ASPEN_MASS_VOLUME_DENSITY_INCONSISTENT",
                    "mass_flow_kg_h": mass,
                    "volumetric_flow_m3_h": volume,
                    "reported_density_kg_m3": density,
                    "implied_density_kg_m3": implied_density,
                    "ratio_implied_to_reported": ratio,
                    "detail": (
                        "Reported density differs from mass_flow/volumetric_flow by more than one "
                        "order of magnitude; density is excluded while the two direct flow values remain visible."
                    ),
                })
                result.pop("density_kg_m3", None)
                result.get("_sources", {}).pop("density_kg_m3", None)
    return result, errors


def normalize_block(row: dict[str, Any], units: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    block_id = str(row.get("block_id") or row.get("tag") or row.get("id") or "").strip()
    block_type = str(row.get("block_type") or row.get("type") or row.get("aspen_block_type") or "").strip().upper()
    values, sources, errors = extract_numeric_fields(row, BLOCK_ALIASES, units, "block", block_id or "<missing>")
    result = {
        "block_id": block_id,
        "block_type": block_type,
        "inlet_streams": list_value(row.get("inlet_streams", row.get("in"))),
        "outlet_streams": list_value(row.get("outlet_streams", row.get("out"))),
        "block_status": row.get("block_status", row.get("BLKSTAT")),
        **values,
        "_sources": sources,
    }
    if not block_id:
        errors.append({"object": "<block>", "field": "block_id", "code": "MISSING_BLOCK_ID"})
    if not block_type:
        errors.append({"object": block_id or "<block>", "field": "block_type", "code": "MISSING_BLOCK_TYPE"})
    return result, errors


def _pfd_parameter_entry(value: Any, canonical_unit: str, source: dict[str, Any]) -> dict[str, Any]:
    transform = str(source.get("transform") or "identity")
    return {
        "value": value,
        "canonical_unit": canonical_unit,
        "source_field": str(source.get("source_field") or ""),
        "raw_value": source.get("raw_value", value),
        "raw_unit": str(source.get("source_unit") or canonical_unit),
        "transform": transform,
        "source_status": "ASPEN_DERIVED_PROCESS_SIDE",
        "normalization_status": "NORMALIZED",
        "evidence_class": "R" if transform == "identity" else "D",
        "formal_design_evidence": False,
    }


def block_pfd_parameters(block: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return display-safe block fields from the shared unit-normalization path."""

    sources = block.get("_sources") if isinstance(block.get("_sources"), dict) else {}
    block_type = str(block.get("block_type") or "").upper()
    result: dict[str, dict[str, Any]] = {}
    for source_field, target_field, canonical_unit in PFD_BLOCK_PARAMETER_FIELDS:
        if block.get(source_field) is None or not isinstance(sources.get(source_field), dict):
            continue
        effective_target = target_field
        if source_field == "diameter_mm" and block_type in TOWER_BLOCK_TYPES:
            effective_target = "inner_diameter_mm"
        result[effective_target] = _pfd_parameter_entry(
            block[source_field],
            canonical_unit,
            dict(sources[source_field]),
        )
    return dict(sorted(result.items()))


def stream_pfd_parameters(stream: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return display-safe stream fields without relabelling raw Aspen values."""

    sources = stream.get("_sources") if isinstance(stream.get("_sources"), dict) else {}
    result: dict[str, dict[str, Any]] = {}
    for source_field, target_field, canonical_unit in PFD_STREAM_PARAMETER_FIELDS:
        if stream.get(source_field) is None or not isinstance(sources.get(source_field), dict):
            continue
        result[target_field] = _pfd_parameter_entry(
            stream[source_field],
            canonical_unit,
            dict(sources[source_field]),
        )
    for field in ("phase", "dominant_components"):
        if stream.get(field) in (None, ""):
            continue
        result[field] = {
            "value": stream[field],
            "canonical_unit": "",
            "source_field": field,
            "raw_value": stream[field],
            "raw_unit": "",
            "transform": "identity",
            "source_status": "ASPEN_EXPORTED_VALUE",
            "normalization_status": "IDENTITY",
            "evidence_class": "R",
            "formal_design_evidence": False,
        }
    return dict(sorted(result.items()))


def parse_raw_history_counts(history_text: str) -> dict[str, int | None]:
    names = ("terminal_errors", "severe_errors", "errors", "warnings")
    direct_patterns = {
        "terminal_errors": r"(?im)^\s*TERMINAL\s+ERRORS?\s*[:=]\s*(\d+)\s*$",
        "severe_errors": r"(?im)^\s*SEVERE\s+ERRORS?\s*[:=]\s*(\d+)\s*$",
        "errors": r"(?im)^\s*ERRORS?\s*[:=]\s*(\d+)\s*$",
        "warnings": r"(?im)^\s*WARNINGS?\s*[:=]\s*(\d+)\s*$",
    }
    direct = {
        name: int(match.group(1)) if (match := re.search(pattern, history_text)) else None
        for name, pattern in direct_patterns.items()
    }
    if all(value is not None for value in direct.values()):
        return direct

    chunks = list(re.finditer(
        r"(?:SUMMARY OF ERRORS|Summary of Simulation Errors)(.*?)(?:\f|\Z)",
        history_text,
        flags=re.S | re.I,
    ))
    if chunks:
        chunk = chunks[-1].group(1)
        labels = {
            "terminal_errors": "TERMINAL ERRORS",
            "severe_errors": "SEVERE ERRORS",
            "errors": "ERRORS",
            "warnings": "WARNINGS",
        }
        parsed: dict[str, int | None] = {}
        for name, label in labels.items():
            match = re.search(rf"(?im)^\s*{label}\s+((?:\d+\s+)+\d+)\s*$", chunk)
            parsed[name] = sum(int(value) for value in re.findall(r"\d+", match.group(1))) if match else None
        if all(value is not None for value in parsed.values()):
            return parsed

    if re.search(r"NO ERRORS OR WARNINGS (?:GENERATED|WERE ISSUED)", history_text, flags=re.I):
        return {name: 0 for name in names}
    return {name: None for name in names}


def run_gate(case: dict[str, Any], blocks: list[dict[str, Any]], source_file: Path) -> dict[str, Any]:
    raw = case.get("run_status")
    names = ("terminal_errors", "severe_errors", "errors", "warnings")
    if not isinstance(raw, dict) or any(nonnegative_integer(raw.get(name)) is None for name in names):
        status = "UNVERIFIED_RUN_STATUS"
        counts = {name: None for name in names}
    else:
        counts = {name: nonnegative_integer(raw[name]) for name in names}
        status = "CLEAN_RUN" if all(value == 0 for value in counts.values()) else "DIRTY_RUN"
    evidence_status = "MISSING"
    evidence_path_value = case.get("run_status_evidence_path")
    evidence_hash_value = str(case.get("run_status_evidence_sha256", "")).strip().upper()
    evidence_path: Path | None = None
    if evidence_path_value and evidence_hash_value:
        evidence_path = Path(str(evidence_path_value)).expanduser()
        if not evidence_path.is_absolute():
            evidence_path = source_file.parent / evidence_path
        if not evidence_path.is_file():
            evidence_status = "FILE_NOT_FOUND"
        elif sha256_file(evidence_path) != evidence_hash_value:
            evidence_status = "HASH_MISMATCH"
        else:
            try:
                evidence = json.loads(evidence_path.read_text(encoding="utf-8-sig"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                evidence_status = "INVALID_JSON"
            else:
                evidence_counts = evidence.get("run_status") if isinstance(evidence, dict) else None
                if not isinstance(evidence, dict) or evidence.get("schema") != "aspen-run-status-evidence-v1" or not isinstance(evidence_counts, dict):
                    evidence_status = "INVALID_SCHEMA"
                elif any(nonnegative_integer(evidence_counts.get(name)) is None for name in names):
                    evidence_status = "MISSING_COUNTS"
                elif {name: nonnegative_integer(evidence_counts[name]) for name in names} != counts:
                    evidence_status = "COUNT_MISMATCH"
                elif str(evidence.get("case_id", "")) != str(case.get("case_id", "")):
                    evidence_status = "CASE_ID_MISMATCH"
                else:
                    raw_history_value = evidence.get("raw_history_path")
                    raw_history_hash = str(evidence.get("raw_history_sha256", "")).strip().upper()
                    raw_history = Path(str(raw_history_value)).expanduser() if raw_history_value else None
                    if raw_history is not None and not raw_history.is_absolute():
                        raw_history = evidence_path.parent / raw_history
                    if raw_history is None or not raw_history.is_file():
                        evidence_status = "RAW_HISTORY_FILE_NOT_FOUND"
                    elif not re.fullmatch(r"[0-9A-F]{64}", raw_history_hash):
                        evidence_status = "RAW_HISTORY_HASH_INVALID"
                    elif sha256_file(raw_history) != raw_history_hash:
                        evidence_status = "RAW_HISTORY_HASH_MISMATCH"
                    else:
                        history_text = raw_history.read_text(encoding="utf-8-sig", errors="replace")
                        raw_counts = parse_raw_history_counts(history_text)
                        problem_patterns = (
                            r"(?im)^\s*\*\s*WARNING\b",
                            r"(?i)WARNING IN THE",
                            r"(?im)^\s*SEVERE ERROR\b",
                            r"(?i)ERROR IN THE",
                            r"(?i)CHECK THE RUN STATUS",
                        )
                        if any(value is None for value in raw_counts.values()):
                            evidence_status = "RAW_HISTORY_COUNTS_NOT_FOUND"
                        elif raw_counts != counts:
                            evidence_status = "RAW_HISTORY_COUNT_MISMATCH"
                        elif any(value != 0 for value in raw_counts.values()):
                            evidence_status = "RAW_HISTORY_NONZERO_COUNTS"
                        elif any(re.search(pattern, history_text) for pattern in problem_patterns):
                            evidence_status = "RAW_HISTORY_PROBLEM_LINES"
                        else:
                            evidence_status = "VERIFIED"
    if status == "CLEAN_RUN" and evidence_status != "VERIFIED":
        status = "UNVERIFIED_RUN_STATUS_EVIDENCE"
    bad_blocks = []
    for block in blocks:
        value = block.get("block_status")
        if value in (None, ""):
            continue
        if str(value).casefold().strip() not in CLEAN_BLOCK_WORDS:
            bad_blocks.append({"block_id": block["block_id"], "block_status": value})
    if bad_blocks and status == "CLEAN_RUN":
        status = "DIRTY_BLOCK_STATUS"
    return {
        "status": status,
        "counts": counts,
        "bad_blocks": bad_blocks,
        "run_status_evidence": {
            "status": evidence_status,
            "path": str(evidence_path.resolve()) if evidence_path and evidence_path.is_file() else str(evidence_path_value or ""),
            "sha256": evidence_hash_value or None,
            "raw_history_required": True,
        },
    }


def lineage(
    *,
    target_field: str,
    value: Any,
    unit: str,
    source_file: Path,
    source_sha256: str,
    object_type: str,
    object_id: str,
    source_field: str,
    transform: str,
    formula: str,
    substitution: str,
    evidence_class: str = "D",
    result_status: str = "DERIVED",
    evidence_scope: str = "ASPEN_PROCESS_SIDE",
    promotion_cap: str = "PROCESS_SIDE_ONLY",
    warning: str | None = None,
) -> dict[str, Any]:
    answer = f"{value:.10g}" if isinstance(value, (int, float)) else str(value)
    return {
        "target_field": target_field,
        "value": value,
        "unit": unit,
        "source_file_path": str(source_file),
        "source_file_sha256": source_sha256,
        "source_object_type": object_type,
        "source_object_id": object_id,
        "source_field": source_field,
        "transform": transform,
        "evidence_class": evidence_class,
        "result_status": result_status,
        "evidence_scope": evidence_scope,
        "promotion_cap": promotion_cap,
        "warning": warning,
        "equation_chain": f"{target_field} = {formula} = {substitution} = {answer} {unit}".strip(),
    }


def add_direct(
    record: dict[str, Any],
    chain: list[dict[str, Any]],
    target: str,
    value: Any,
    unit: str,
    source: dict[str, Any],
    source_file: Path,
    source_sha256: str,
    object_type: str,
    object_id: str,
) -> None:
    record[target] = value
    raw = source.get("raw_value")
    raw_text = json.dumps(raw, ensure_ascii=False, separators=(",", ":")) if isinstance(raw, list) else str(raw)
    source_unit = source.get("source_unit", unit)
    transform = source.get("transform", "identity")
    if transform == "identity":
        formula = f"Aspen[{object_id}].{source.get('source_field', target)}"
        substitution = raw_text
    elif "=" in str(transform):
        formula = str(transform).split("=", 1)[1]
        if isinstance(raw, list) and len(raw) == 2 and "/" in formula:
            substitution = f"{raw[0]}/{raw[1]}"
        else:
            substitution = re.sub(r"^[A-Za-z_]+", raw_text, formula)
    else:
        formula = str(transform)
        substitution = raw_text
    item = lineage(
            target_field=target,
            value=value,
            unit=unit,
            source_file=source_file,
            source_sha256=source_sha256,
            object_type=object_type,
            object_id=object_id,
            source_field=str(source.get("source_field", target)),
            transform=str(transform),
            formula=formula,
            substitution=substitution,
        )
    item["raw_value"] = raw
    item["raw_unit"] = source_unit
    chain.append(item)


def simulation_logic_match_result(
    record: dict[str, Any],
    block: dict[str, Any],
) -> dict[str, Any]:
    """Classify exact Aspen topology blocks without inventing equipment.

    FSPLIT, MIXER, and HIERARCHY express simulation topology by default. They
    may be overridden by a user to a physical equipment family in the separate
    PFD override layer, but the raw Aspen block type alone does not prove an
    independent device, equipment family, engineering specification, or model.
    """

    return {
        "schema": "aspen-simulation-logic-node-classification-v1",
        "status": SIMULATION_LOGIC_STATUS,
        "status_reason": SIMULATION_LOGIC_REASON,
        "deterministic": True,
        "llm_used": False,
        "normalized_input": dict(record),
        "match": {
            "status": SIMULATION_LOGIC_STATUS,
            "family_id": None,
            "family_name": "模拟流程逻辑节点",
            "source": "exact_aspen_block_type",
            "aspen_block_type": block["block_type"],
        },
        "model_recommendation": {
            "status": SIMULATION_LOGIC_STATUS,
            "recommended_type": "模拟流程逻辑节点（默认无独立设备型号）",
            "candidates": [],
            "formal_model": None,
            "selection_execution": {
                "status": SIMULATION_LOGIC_STATUS,
                "reason": SIMULATION_LOGIC_REASON,
            },
            "prohibited_claim": "Aspen logic block does not establish independent physical equipment or a product model.",
        },
        "model_decision": {
            "model_status": SIMULATION_LOGIC_STATUS,
            "reason_code": SIMULATION_LOGIC_REASON,
            "candidate_model": None,
            "formal_model": None,
        },
        "calculations": [],
        "derived_parameters": {},
        "calculation_pending": [],
        "normalization_conflicts": [],
        "parameter_errors": [],
        "progress": {
            "state": SIMULATION_LOGIC_STATUS,
            "terminal": True,
            "next_fields": [],
            "minimum_missing_sets": [],
        },
    }


def is_default_simulation_logic_node(item: dict[str, Any]) -> bool:
    applicability = item.get("equipment_applicability", {})
    return (
        str(item.get("canonical_match_input", {}).get("aspen_block_type", "")).upper()
        in SIMULATION_LOGIC_BLOCK_TYPES
        and applicability.get("status") == SIMULATION_LOGIC_STATUS
        and applicability.get("reason_code") == SIMULATION_LOGIC_REASON
        and applicability.get("independent_equipment_model_applicable_by_default") is False
    )


def derive_equipment(
    block: dict[str, Any],
    mapping: dict[str, Any],
    streams: dict[str, dict[str, Any]],
    case: dict[str, Any],
    source_file: Path,
    source_sha256: str,
    rules: dict[str, Any],
    graph: dict[str, Any],
    endpoints: dict[str, dict[str, list[str]]] | None = None,
    pfd_mapping_sha256: str = "",
    property_evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "equipment_tag": str(mapping.get("equipment_tag") or block["block_id"]),
        "aspen_block_type": block["block_type"],
    }
    for field in ("equipment_family", "equipment_type", "process_function"):
        if mapping.get(field):
            record[field] = mapping[field]
    chain: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    pressure_basis = str(case.get("pressure_basis", "")).strip().casefold()
    if pressure_basis in {"absolute", "gauge"}:
        record["pressure_basis"] = pressure_basis
        chain.append(
            lineage(
                target_field="pressure_basis",
                value=pressure_basis,
                unit="-",
                source_file=source_file,
                source_sha256=source_sha256,
                object_type="case",
                object_id=str(case.get("case_id", "")),
                source_field="case.pressure_basis",
                transform="identity",
                formula="Aspen_case_pressure_basis",
                substitution=pressure_basis,
            )
        )
        atmospheric = finite_number(case.get("atmospheric_pressure_mpa"))
        if pressure_basis == "gauge" and (atmospheric is None or atmospheric <= 0):
            blockers.append({"code": "GAUGE_PRESSURE_REQUIRES_ATMOSPHERIC_PRESSURE_MPA"})
        elif atmospheric is not None and atmospheric > 0:
            record["atmospheric_pressure_mpa"] = atmospheric
            chain.append(
                lineage(
                    target_field="atmospheric_pressure_mpa",
                    value=atmospheric,
                    unit="MPa",
                    source_file=source_file,
                    source_sha256=source_sha256,
                    object_type="case",
                    object_id=str(case.get("case_id", "")),
                    source_field="case.atmospheric_pressure_mpa",
                    transform="identity",
                    formula="Aspen_case_atmospheric_pressure",
                    substitution=str(atmospheric),
                )
            )
    inlet_ids = block["inlet_streams"]
    outlet_ids = block["outlet_streams"]
    missing_streams = [sid for sid in inlet_ids + outlet_ids if sid not in streams]
    if missing_streams:
        blockers.append({"code": "CONNECTED_STREAM_NOT_FOUND", "stream_ids": missing_streams})
    inlets = [streams[sid] for sid in inlet_ids if sid in streams]
    outlets = [streams[sid] for sid in outlet_ids if sid in streams]
    block_type = block["block_type"]
    if block_type in SINGLE_INLET_OUTLET_BLOCKS and (len(inlets) != 1 or len(outlets) != 1):
        blockers.append({"code": "PORT_CARDINALITY_AMBIGUOUS", "required": "one_inlet_one_outlet", "actual": [len(inlets), len(outlets)]})
    if len(inlets) == 1:
        stream = inlets[0]
        preferred_flow = "volumetric_flow_m3_h"
        if block_type == "PUMP" and stream.get("liquid_volumetric_flow_m3_h") is not None:
            preferred_flow = "liquid_volumetric_flow_m3_h"
        elif block_type in {"COMPR", "MCOMPR"} and stream.get("vapor_volumetric_flow_m3_h") is not None:
            preferred_flow = "vapor_volumetric_flow_m3_h"
        inlet_targets = {
            preferred_flow: ("flow_m3_h", "m3/h"),
            "mass_flow_kg_h": ("mass_flow_kg_h", "kg/h"),
            "density_kg_m3": ("density_kg_m3", "kg/m3"),
            "pressure_mpa": ("inlet_pressure_mpa", "MPa"),
            "temperature_c": ("inlet_temperature_c", "C"),
            "molecular_weight": ("gas_molecular_weight", "kg/kmol"),
            "compressibility_factor": ("compressibility_factor", "-"),
        }
        for source_field, (target, unit) in inlet_targets.items():
            if stream.get(source_field) is not None:
                add_direct(record, chain, target, stream[source_field], unit, stream["_sources"][source_field], source_file, source_sha256, "stream", stream["stream_id"])
        if stream.get("phase"):
            record["phase"] = stream["phase"]
    if len(outlets) == 1 and outlets[0].get("pressure_mpa") is not None:
        stream = outlets[0]
        add_direct(record, chain, "outlet_pressure_mpa", stream["pressure_mpa"], "MPa", stream["_sources"]["pressure_mpa"], source_file, source_sha256, "stream", stream["stream_id"])
    if len(outlets) == 1 and outlets[0].get("temperature_c") is not None:
        stream = outlets[0]
        add_direct(record, chain, "outlet_temperature_c", stream["temperature_c"], "C", stream["_sources"]["temperature_c"], source_file, source_sha256, "stream", stream["stream_id"])
    connected = inlets + outlets
    pressures = [(stream["stream_id"], stream.get("pressure_mpa")) for stream in connected if stream.get("pressure_mpa") is not None]
    if pressures:
        maximum = max(value for _, value in pressures)
        record["operating_pressure_mpa"] = maximum
        substitution = "max(" + ",".join(f"{sid}:{value:.10g}" for sid, value in pressures) + ")"
        chain.append(
            lineage(
                target_field="operating_pressure_mpa",
                value=maximum,
                unit="MPa",
                source_file=source_file,
                source_sha256=source_sha256,
                object_type="connected_stream_set",
                object_id=block["block_id"],
                source_field="pressure_mpa",
                transform="maximum_connected_stream_operating_pressure",
                formula="max(P_connected)",
                substitution=substitution,
                evidence_class="J",
                result_status="PROVISIONAL",
                evidence_scope="CONNECTED_STREAM_PROCESS_PRESSURE_ENVELOPE",
                promotion_cap="PROCESS_SIDE_ENVELOPE_ONLY",
                warning=(
                    "This is the maximum connected Aspen stream pressure used as a process-side "
                    "envelope. It is not mechanical design pressure and cannot establish pressure "
                    "allowance, external-pressure cases, material, thickness, or a final model."
                ),
            )
        )
    zero_duty_temperature_conflict = False
    if block_type == "HEATER" and finite_number(block.get("heat_duty_kw")) == 0.0 and len(inlets) == 1 and len(outlets) == 1:
        inlet_temperature = finite_number(inlets[0].get("temperature_c"))
        outlet_temperature = finite_number(outlets[0].get("temperature_c"))
        inlet_mass_flow = finite_number(inlets[0].get("mass_flow_kg_h"))
        outlet_mass_flow = finite_number(outlets[0].get("mass_flow_kg_h"))
        mass_scale = max(abs(inlet_mass_flow or 0.0), abs(outlet_mass_flow or 0.0), 1.0)
        mass_is_consistent = (
            inlet_mass_flow is not None
            and outlet_mass_flow is not None
            and inlet_mass_flow > 0.0
            and outlet_mass_flow > 0.0
            and abs(inlet_mass_flow - outlet_mass_flow) / mass_scale <= 0.01
        )
        zero_duty_temperature_conflict = (
            inlet_temperature is not None
            and outlet_temperature is not None
            and abs(outlet_temperature - inlet_temperature) > 0.05
            and mass_is_consistent
        )
        if zero_duty_temperature_conflict:
            blockers.append({
                "code": "ZERO_ASPEN_DUTY_CONFLICTS_WITH_STREAM_TEMPERATURE_CHANGE",
                "heat_duty_kw": 0.0,
                "inlet_temperature_c": inlet_temperature,
                "outlet_temperature_c": outlet_temperature,
                "mass_flow_kg_h": inlet_mass_flow,
                "action": (
                    "zero Aspen duty was excluded from sizing; continue with the visible "
                    "m*Cp*dT preliminary fallback and retain the Aspen/formal evidence gate"
                ),
            })
    block_targets = {
        "heat_duty_kw": ("heat_duty_kw", "kW"),
        "heat_transfer_area_m2": ("heat_transfer_area_m2", "m2"),
        "shaft_power_kw": ("shaft_power_kw", "kW"),
        "head_m": ("head_m", "m"),
        "npsha_m": ("npsha_m", "m"),
        "efficiency_percent": ("efficiency_percent", "percent"),
        "pressure_drop_kpa": ("pressure_drop_kpa", "kPa"),
        "stage_count": ("stage_count", "-"),
        "volume_m3": ("volume_m3", "m3"),
        "diameter_mm": ("diameter_mm", "mm"),
        "height_mm": ("height_mm", "mm"),
    }
    for source_field, (target, unit) in block_targets.items():
        if block.get(source_field) is not None:
            if source_field == "heat_duty_kw" and zero_duty_temperature_conflict:
                continue
            if source_field == "diameter_mm" and block_type in TOWER_BLOCK_TYPES:
                # Aspen column DIAMETER is an internal column diameter on this
                # routed block family.  Preserve that semantic explicitly;
                # never copy a generic vessel diameter into inner diameter.
                target = "inner_diameter_mm"
            add_direct(record, chain, target, block[source_field], unit, block["_sources"][source_field], source_file, source_sha256, "block", block["block_id"])
    logic_node = block_type in SIMULATION_LOGIC_BLOCK_TYPES
    match_result = (
        simulation_logic_match_result(record, block)
        if logic_node
        else matcher.match_one(record, rules, graph)
    )
    matched_family = match_result.get("match", {}).get("family_id")
    derived_service_profile = service_profile.build_aspen_service_profile(
        equipment_id=record["equipment_tag"],
        equipment_family=str(matched_family or record.get("equipment_family") or ""),
        block=block,
        streams=streams,
        source_bundle_sha256=source_sha256,
    )
    if matched_family in {"family_compressor", "family_liquid_power_recovery_turbine", "family_gas_expander_turbine"} and pressure_basis not in {"absolute", "gauge"}:
        blockers.append({"code": "PRESSURE_BASIS_REQUIRED_FOR_GAS_OR_EXPANSION_PRESSURE_RATIO"})
    reconciliation: list[dict[str, Any]] = []
    reported_ratio = block.get("reported_pressure_ratio")
    if reported_ratio is not None:
        calculated = next((item for item in match_result.get("calculations", []) if item["calculation_id"] == "pressure_ratio"), None)
        if calculated:
            delta = abs(float(calculated["value"]) - float(reported_ratio))
            tolerance = max(1e-6, 1e-4 * abs(float(reported_ratio)))
            reconciliation.append({
                "quantity": "pressure_ratio",
                "aspen_reported": reported_ratio,
                "derived_from_streams": calculated["value"],
                "absolute_difference": delta,
                "status": "PASS" if delta <= tolerance else "FAIL",
                "tolerance": tolerance,
            })
    derivation_chain = [item["equation_chain"] for item in chain]
    derivation_chain.extend(item["equation_chain"] for item in match_result.get("calculations", []))
    process_input_provenance = {
        "schema": "aspen-derived-process-input-provenance-v1",
        "status": "ASPEN_DERIVED_PROCESS_SIDE",
        "source_file_path": str(source_file),
        "source_file_sha256": source_sha256,
        "lineage_count": len(chain),
        "evidence_class_counts": {
            evidence_class: sum(1 for item in chain if item.get("evidence_class") == evidence_class)
            for evidence_class in sorted({str(item.get("evidence_class") or "U") for item in chain})
        },
        "formal_use_allowed_by_this_adapter_alone": False,
        "mechanical_design_basis_established": False,
        "boundary": "Aspen/process-side conditions and deterministic unit/identity derivations only",
    }
    match_result = dict(match_result)
    match_result["input_provenance"] = process_input_provenance
    mechanical_context = (
        mapping.get("connection_design_context")
        if isinstance(mapping.get("connection_design_context"), dict)
        else {}
    )
    try:
        connection_component_selections = connection_selection.build_aspen_connection_component_selections(
            block=block,
            streams=streams,
            match_result=match_result,
            source_export_sha256=source_sha256,
            pfd_mapping_sha256=pfd_mapping_sha256,
            endpoints=endpoints,
            mechanical_context=mechanical_context,
            property_evidence=property_evidence or [],
            pressure_basis=str(case.get("pressure_basis") or ""),
            service_profile=derived_service_profile,
        )
    except Exception as exc:
        connection_component_selections = {
            "schema": "equipment-connection-selection-package-v1",
            "engine_version": connection_selection.ENGINE_VERSION,
            "status": "LOCAL_SELECTION_PACKAGE_FAILED",
            "deterministic": True,
            "llm_used": False,
            "runtime_vision": False,
            "runtime_source_access": False,
            "parent_selection_context_sha256": (
                match_result.get("design_parameter_package", {})
                .get("selection_context", {})
                .get("sha256", "")
            ),
            "source_export_sha256": source_sha256,
            "pfd_mapping_sha256": pfd_mapping_sha256,
            "connections": [],
            "diagnostics": [{
                "code": "CONNECTION_COMPONENT_PACKAGE_FAILED",
                "detail": str(exc),
                "scope": "connection_component_selections_only",
            }],
        }
    derived_service_profile = service_profile.enrich_with_connection_property_facts(
        derived_service_profile,
        connection_component_selections,
    )
    result = {
        "equipment_tag": record["equipment_tag"],
        "aspen_block_id": block["block_id"],
        "aspen_mapping_status": (
            SIMULATION_LOGIC_REASON
            if logic_node and not blockers
            else "DERIVED" if not blockers
            else "PROVISIONAL_AMBIGUOUS_CONNECTION"
        ),
        "adapter_blockers": blockers,
        "canonical_match_input": record,
        "pfd_parameters": block_pfd_parameters(block),
        "parameter_lineage": chain,
        "derivation_chain": derivation_chain,
        "aspen_reconciliation": reconciliation,
        "input_provenance": process_input_provenance,
        "service_profile": derived_service_profile,
        "connection_component_selections": connection_component_selections,
        "evidence_boundary": {
            "status": "PROCESS_DATA_ONLY",
            "process_side_values_allowed": True,
            "mechanical_design_pressure_established": False,
            "material_established": False,
            "vendor_model_established": False,
            "connected_stream_pressure_role": "PROVISIONAL_PROCESS_SIDE_ENVELOPE_NOT_MECHANICAL_DESIGN_PRESSURE",
        },
        "match_result": match_result,
    }
    if logic_node:
        result["equipment_applicability"] = {
            "status": SIMULATION_LOGIC_STATUS,
            "reason_code": SIMULATION_LOGIC_REASON,
            "classification_basis": {
                "kind": "exact_aspen_block_type",
                "value": block_type,
                "allowed_values": sorted(SIMULATION_LOGIC_BLOCK_TYPES),
            },
            "independent_equipment_model_applicable_by_default": False,
            "physical_equipment_or_model_inferred": False,
            "pfd_node_retained": True,
            "connectivity_retained": True,
            "user_type_override_allowed": True,
            "override_effect": "separate PFD override triggers deterministic recalculation; source Aspen bundle is unchanged",
        }
        result["connectivity"] = {
            "inlet_streams": list(inlet_ids),
            "outlet_streams": list(outlet_ids),
        }
    return result


def stream_endpoints(blocks: list[dict[str, Any]]) -> dict[str, dict[str, list[str]]]:
    """Return deterministic PFD endpoints for every stream named on a block port."""

    endpoints: dict[str, dict[str, list[str]]] = {}
    for block in blocks:
        block_id = str(block.get("block_id") or "").strip()
        if not block_id:
            continue
        for stream_id in block.get("outlet_streams", []):
            entry = endpoints.setdefault(stream_id, {"from_block_ids": [], "to_block_ids": []})
            entry["from_block_ids"].append(block_id)
        for stream_id in block.get("inlet_streams", []):
            entry = endpoints.setdefault(stream_id, {"from_block_ids": [], "to_block_ids": []})
            entry["to_block_ids"].append(block_id)
    for entry in endpoints.values():
        entry["from_block_ids"] = sorted(set(entry["from_block_ids"]))
        entry["to_block_ids"] = sorted(set(entry["to_block_ids"]))
    return endpoints


def material_stream_for_piping(stream: dict[str, Any]) -> bool:
    """Legacy exports lack record type; explicit non-material types are excluded."""

    return str(stream.get("stream_record_type") or "").strip().upper() in {"", "MATERIAL"}


def preferred_piping_flow_field(stream: dict[str, Any]) -> str | None:
    phase = str(stream.get("phase") or "").strip().casefold()
    if phase in {"liquid", "liq"}:
        candidates = ("liquid_volumetric_flow_m3_h", "volumetric_flow_m3_h")
    elif phase in {"vapor", "vapour", "gas"}:
        candidates = ("vapor_volumetric_flow_m3_h", "volumetric_flow_m3_h")
    elif phase in {"mixed", "two-phase", "two phase", "multiphase"}:
        candidates = ("volumetric_flow_m3_h",)
    else:
        candidates = ("volumetric_flow_m3_h",)
        phase_fields = [
            field for field in ("liquid_volumetric_flow_m3_h", "vapor_volumetric_flow_m3_h")
            if stream.get(field) is not None
        ]
        if len(phase_fields) == 1:
            candidates = (*candidates, phase_fields[0])
    return next((field for field in candidates if stream.get(field) is not None), None)


def derive_piping(
    stream: dict[str, Any],
    endpoints: dict[str, list[str]],
    case: dict[str, Any],
    source_file: Path,
    source_sha256: str,
    rules: dict[str, Any],
    graph: dict[str, Any],
) -> dict[str, Any]:
    """Project a referenced material stream into an independent piping match."""

    stream_id = stream["stream_id"]
    from_blocks = endpoints.get("from_block_ids", [])
    to_blocks = endpoints.get("to_block_ids", [])
    from_label = ",".join(from_blocks) if from_blocks else "PFD boundary"
    to_label = ",".join(to_blocks) if to_blocks else "PFD boundary"
    pressure_basis = str(case.get("pressure_basis") or "").strip().casefold()
    record: dict[str, Any] = {
        "equipment_tag": stream_id,
        "stream_id": stream_id,
        "equipment_family": "family_process_piping",
        "process_function": f"PFD material stream {stream_id}: {from_label} -> {to_label}",
        "pressure_basis": pressure_basis,
    }
    chain: list[dict[str, Any]] = []
    if pressure_basis in {"absolute", "gauge"}:
        chain.append(
            lineage(
                target_field="pressure_basis",
                value=pressure_basis,
                unit="-",
                source_file=source_file,
                source_sha256=source_sha256,
                object_type="case",
                object_id=str(case.get("case_id", "")),
                source_field="case.pressure_basis",
                transform="identity",
                formula="Aspen_case_pressure_basis",
                substitution=pressure_basis,
            )
        )
    if stream.get("phase") not in (None, ""):
        record["phase"] = stream["phase"]
    atmospheric = finite_number(case.get("atmospheric_pressure_mpa"))
    if atmospheric is not None and atmospheric > 0:
        record["atmospheric_pressure_mpa"] = atmospheric
        chain.append(
            lineage(
                target_field="atmospheric_pressure_mpa",
                value=atmospheric,
                unit="MPa",
                source_file=source_file,
                source_sha256=source_sha256,
                object_type="case",
                object_id=str(case.get("case_id", "")),
                source_field="case.atmospheric_pressure_mpa",
                transform="identity",
                formula="Aspen_case_atmospheric_pressure",
                substitution=str(atmospheric),
            )
        )
    flow_field = preferred_piping_flow_field(stream)
    direct_fields: list[tuple[str | None, str, str]] = [
        (flow_field, "flow_m3_h", "m3/h"),
        ("mass_flow_kg_h", "mass_flow_kg_h", "kg/h"),
        ("density_kg_m3", "density_kg_m3", "kg/m3"),
        ("pressure_mpa", "operating_pressure_mpa", "MPa"),
        ("temperature_c", "operating_temperature_c", "C"),
    ]
    for source_field, target, unit in direct_fields:
        if source_field and stream.get(source_field) is not None:
            add_direct(
                record, chain, target, stream[source_field], unit, stream["_sources"][source_field],
                source_file, source_sha256, "stream", stream_id,
            )

    # The matcher currently names operating temperature `temperature_c`.
    # Preserve the explicit piping field above while adapting only the matcher
    # call; never map it to design_temperature_c.
    matcher_input = {
        key: value for key, value in record.items()
        if key not in {"stream_id", "operating_temperature_c"}
    }
    if "operating_temperature_c" in record:
        matcher_input["temperature_c"] = record["operating_temperature_c"]
    match_result = matcher.match_one(matcher_input, rules, graph)
    derived_service_profile = service_profile.build_aspen_service_profile(
        equipment_id=stream_id,
        equipment_family="family_process_piping",
        block={
            "block_id": f"PIPE:{stream_id}",
            "block_type": "PFD_MATERIAL_STREAM",
            "inlet_streams": [stream_id],
            "outlet_streams": [],
        },
        streams={stream_id: stream},
        source_bundle_sha256=source_sha256,
    )
    progress = match_result.get("progress", {})
    model = match_result.get("model_recommendation", {})
    decision = match_result.get("model_decision", {})
    edge_values = {
        field: record.get(field)
        for field in (
            "stream_id", "phase", "flow_m3_h", "mass_flow_kg_h", "density_kg_m3",
            "operating_pressure_mpa", "operating_temperature_c",
        )
        if record.get(field) is not None
    }
    compact_key_values = {
        field: record[field]
        for field in (
            "flow_m3_h", "operating_pressure_mpa", "operating_temperature_c",
        )
        if record.get(field) is not None
    }
    compact_type_or_model = (
        decision.get("candidate_model")
        or decision.get("generated_candidate_model")
        or model.get("recommended_type")
        or match_result.get("match", {}).get("family_name")
    )
    compact_status = (
        model.get("selection_execution", {}).get("status")
        or decision.get("model_status")
        or model.get("status")
        or match_result.get("status")
    )
    return {
        "stream_id": stream_id,
        "status": match_result.get("status"),
        "canonical_match_input": record,
        "pfd_parameters": stream_pfd_parameters(stream),
        "parameter_lineage": chain,
        "derivation_chain": [item["equation_chain"] for item in chain],
        "match_result": match_result,
        "service_profile": derived_service_profile,
        "pfd_edge_label_data": {
            "default_view": "compact_label",
            "compact_label": {
                "stream_id": stream_id,
                "type_or_model": compact_type_or_model,
                "status": compact_status,
                "key_values": compact_key_values,
            },
            "details": {
                "from_block_ids": from_blocks,
                "to_block_ids": to_blocks,
                "values": edge_values,
                "match_status": match_result.get("status"),
                "parameter_package_status": match_result.get("design_parameter_package", {}).get("status"),
                "selection_execution_status": model.get("selection_execution", {}).get("status"),
                "model_status": decision.get("model_status"),
                "next_fields": progress.get("next_fields", []),
                "minimum_missing_sets": progress.get("minimum_missing_sets", []),
            },
        },
        "evidence_boundary": {
            "status": "PROCESS_DATA_ONLY",
            "source_export_sha256": source_sha256,
            "affects_aspen_formal_use_gate": False,
            "not_established": [
                "design_temperature_c", "target_velocity_m_s", "material", "selected_dn",
                "selected_outer_diameter_mm", "selected_wall_thickness_mm", "wall_series",
                "mechanical_stress_verification", "vendor_model",
            ],
        },
    }


def derive_bundle(bundle: dict[str, Any], source_file: Path) -> dict[str, Any]:
    source_file = source_file.resolve()
    try:
        source_bytes = source_file.read_bytes()
        source_sha256 = hashlib.sha256(source_bytes).hexdigest().upper()
        parsed_source = json.loads(source_bytes.decode("utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {
            "schema": "aspen-equipment-derivation-result-v1",
            "engine_version": ENGINE_VERSION,
            "deterministic": True,
            "llm_used": False,
            "status": "BLOCKED_SOURCE_EXPORT_READ",
            "source_export_path": str(source_file),
            "errors": [{"code": "SOURCE_EXPORT_READ_FAILED", "detail": str(exc)}],
        }
    if parsed_source != bundle:
        return {
            "schema": "aspen-equipment-derivation-result-v1",
            "engine_version": ENGINE_VERSION,
            "deterministic": True,
            "llm_used": False,
            "status": "BLOCKED_SOURCE_BUNDLE_CONTENT_MISMATCH",
            "source_export_path": str(source_file),
            "source_export_sha256": source_sha256,
            "errors": [{"code": "SOURCE_BUNDLE_CONTENT_MISMATCH"}],
        }
    errors: list[dict[str, Any]] = []
    normalization_diagnostics: list[dict[str, Any]] = []
    if bundle.get("schema") != "aspen-equipment-export-v1":
        errors.append({"code": "UNSUPPORTED_SCHEMA", "value": bundle.get("schema")})
    case_data = bundle.get("case") if isinstance(bundle.get("case"), dict) else {}
    pressure_basis = str(case_data.get("pressure_basis", "")).strip().casefold()
    if pressure_basis not in {"absolute", "gauge"}:
        errors.append({"code": "MISSING_OR_INVALID_PRESSURE_BASIS", "allowed": ["absolute", "gauge"]})
    if pressure_basis == "gauge" and (finite_number(case_data.get("atmospheric_pressure_mpa")) is None or float(case_data.get("atmospheric_pressure_mpa", 0)) <= 0):
        errors.append({"code": "GAUGE_PRESSURE_REQUIRES_ATMOSPHERIC_PRESSURE_MPA"})
    units = bundle.get("units") if isinstance(bundle.get("units"), dict) else {}
    streams_list: list[dict[str, Any]] = []
    stream_error_rows: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    isolated_stream_diagnostics: list[dict[str, Any]] = []
    for index, raw in enumerate(bundle.get("streams", []) if isinstance(bundle.get("streams"), list) else []):
        if not isinstance(raw, dict):
            isolated_stream_diagnostics.append({
                "stream_id": "",
                "status": "IGNORED_NONOBJECT_PLACEHOLDER",
                "row_index": index,
                "errors": [{"code": "STREAM_ROW_NOT_OBJECT"}],
            })
            continue
        item, item_errors = normalize_stream(raw, units)
        streams_list.append(item)
        stream_error_rows.append((item, item_errors))
    blocks: list[dict[str, Any]] = []
    for raw in bundle.get("blocks", []) if isinstance(bundle.get("blocks"), list) else []:
        if not isinstance(raw, dict):
            errors.append({"code": "BLOCK_ROW_NOT_OBJECT"})
            continue
        item, item_errors = normalize_block(raw, units)
        blocks.append(item)
        structural, diagnostics = partition_normalization_errors(item_errors)
        errors.extend(structural)
        normalization_diagnostics.extend(diagnostics)
    endpoints = stream_endpoints(blocks)
    pfd_mapping_sha256 = connection_selection.canonical_sha256({
        "blocks": [
            {
                "block_id": block.get("block_id"),
                "block_type": block.get("block_type"),
                "inlet_streams": list(block.get("inlet_streams", [])),
                "outlet_streams": list(block.get("outlet_streams", [])),
            }
            for block in sorted(blocks, key=lambda item: str(item.get("block_id") or ""))
        ],
        "endpoints": endpoints,
    })
    referenced_stream_ids = set(endpoints)
    for stream, stream_errors in stream_error_rows:
        stream_id = stream["stream_id"]
        if stream_id and stream_id in referenced_stream_ids:
            structural, diagnostics = partition_normalization_errors(stream_errors)
            errors.extend(structural)
            normalization_diagnostics.extend(diagnostics)
        elif stream_errors or stream_id:
            isolated_stream_diagnostics.append({
                "stream_id": stream_id,
                "status": "IGNORED_UNREFERENCED_OR_EMPTY_STREAM",
                "errors": stream_errors,
            })
    stream_ids = [item["stream_id"] for item in streams_list if item["stream_id"]]
    block_ids = [item["block_id"] for item in blocks if item["block_id"]]
    duplicate_referenced_stream_ids = sorted({
        stream_id for stream_id in referenced_stream_ids
        if stream_ids.count(stream_id) > 1
    })
    if duplicate_referenced_stream_ids:
        errors.append({"code": "DUPLICATE_STREAM_ID", "stream_ids": duplicate_referenced_stream_ids})
    if len(block_ids) != len(set(block_ids)):
        errors.append({"code": "DUPLICATE_BLOCK_ID"})
    raw_mapping_rows = bundle.get("equipment_map", [])
    mapping_rows: list[dict[str, Any]] = []
    if not isinstance(raw_mapping_rows, list):
        errors.append({"code": "EQUIPMENT_MAP_NOT_ARRAY"})
    else:
        for index, item in enumerate(raw_mapping_rows):
            if not isinstance(item, dict):
                errors.append({"code": "EQUIPMENT_MAP_ROW_NOT_OBJECT", "index": index})
                continue
            if not str(item.get("block_id", "")).strip():
                errors.append({"code": "EQUIPMENT_MAP_MISSING_BLOCK_ID", "index": index})
                continue
            mapping_rows.append(item)
        mapping_ids = [str(item["block_id"]).strip() for item in mapping_rows]
        if len(mapping_ids) != len(set(mapping_ids)):
            errors.append({"code": "DUPLICATE_EQUIPMENT_MAP_BLOCK_ID"})
    if errors:
        return {
            "schema": "aspen-equipment-derivation-result-v1",
            "engine_version": ENGINE_VERSION,
            "deterministic": True,
            "llm_used": False,
            "status": "BLOCKED_INVALID_ASPEN_EXPORT",
            "source_export_path": str(source_file),
            "source_export_sha256": source_sha256,
            "errors": errors,
            "normalization_diagnostics": normalization_diagnostics,
            "isolated_stream_diagnostics": isolated_stream_diagnostics,
        }
    stream_map = {item["stream_id"]: item for item in streams_list}
    map_by_block = {str(item.get("block_id", "")).strip(): item for item in mapping_rows if isinstance(item, dict)}
    unknown_mappings = sorted(set(map_by_block) - set(block_ids))
    if unknown_mappings:
        return {
            "schema": "aspen-equipment-derivation-result-v1",
            "engine_version": ENGINE_VERSION,
            "deterministic": True,
            "llm_used": False,
            "status": "BLOCKED_INVALID_ASPEN_EXPORT",
            "source_export_path": str(source_file),
            "source_export_sha256": source_sha256,
            "errors": [{"code": "EQUIPMENT_MAP_BLOCK_NOT_FOUND", "block_ids": unknown_mappings}],
        }
    rules = matcher.load_rules()
    graph = matcher.load_graph()
    property_evidence = [
        dict(item)
        for item in bundle.get("property_evidence", [])
        if isinstance(item, dict)
    ] if isinstance(bundle.get("property_evidence"), list) else []
    equipment = [
        derive_equipment(
            block,
            map_by_block.get(block["block_id"], {}),
            stream_map,
            case_data,
            source_file,
            source_sha256,
            rules,
            graph,
            endpoints,
            pfd_mapping_sha256,
            property_evidence,
        )
        for block in blocks
    ]
    diagnostics_by_object: dict[str, list[dict[str, Any]]] = {}
    for diagnostic in normalization_diagnostics:
        diagnostics_by_object.setdefault(str(diagnostic.get("object") or ""), []).append(diagnostic)
    blocks_by_id = {block["block_id"]: block for block in blocks}
    for item in equipment:
        block = blocks_by_id.get(str(item.get("aspen_block_id") or ""), {})
        related_ids = {
            str(item.get("aspen_block_id") or ""),
            *[str(value) for value in block.get("inlet_streams", [])],
            *[str(value) for value in block.get("outlet_streams", [])],
        }
        local_diagnostics = [
            diagnostic
            for object_id in sorted(related_ids)
            for diagnostic in diagnostics_by_object.get(object_id, [])
        ]
        item["ignored_input_diagnostics"] = local_diagnostics
        if isinstance(item.get("match_result"), dict):
            item["match_result"]["ignored_input_diagnostics"] = local_diagnostics
    piping: list[dict[str, Any]] = []
    for stream_id in sorted(referenced_stream_ids):
        stream = stream_map.get(stream_id)
        if stream is None:
            isolated_stream_diagnostics.append({
                "stream_id": stream_id,
                "status": "REFERENCED_STREAM_NOT_FOUND",
                "errors": [{"code": "CONNECTED_STREAM_NOT_FOUND"}],
            })
            continue
        if not material_stream_for_piping(stream):
            isolated_stream_diagnostics.append({
                "stream_id": stream_id,
                "status": "REFERENCED_NON_MATERIAL_STREAM_EXCLUDED_FROM_PIPING",
                "stream_record_type": stream.get("stream_record_type"),
                "errors": [],
            })
            continue
        piping.append(
            derive_piping(
                stream, endpoints[stream_id], case_data, source_file, source_sha256, rules, graph,
            )
        )
    gate = run_gate(case_data, blocks, source_file)
    unclosed_equipment = [
        {
            "equipment_tag": item["equipment_tag"],
            "aspen_block_id": item["aspen_block_id"],
            "aspen_block_type": item.get("canonical_match_input", {}).get("aspen_block_type"),
            "match_status": item["match_result"].get("status"),
        }
        for item in equipment
        if item["match_result"].get("status") != "MATCHED"
        and not is_default_simulation_logic_node(item)
    ]
    matched = not unclosed_equipment
    no_connection_blockers = all(not item["adapter_blockers"] for item in equipment)
    calculation_hard_blockers = [
        {"equipment_tag": item["equipment_tag"], **pending}
        for item in equipment
        for pending in item["match_result"].get("calculation_pending", [])
        if str(pending.get("status", "")).startswith("BLOCKED_")
    ]
    reconciliation_failures = [
        {"equipment_tag": item["equipment_tag"], **check}
        for item in equipment
        for check in item.get("aspen_reconciliation", [])
        if check.get("status") == "FAIL"
    ]
    formal_use_blockers: list[Any] = []
    com_extraction_blockers = case_data.get("com_extraction_blockers", [])
    if isinstance(com_extraction_blockers, list):
        formal_use_blockers.extend(
            {"code": "COM_EXTRACTION_BLOCKER", "detail": item}
            for item in com_extraction_blockers
        )
    if gate["status"] != "CLEAN_RUN":
        formal_use_blockers.append({"code": "ASPEN_RUN_GATE_NOT_CLEAN", "status": gate["status"]})
    if not matched:
        formal_use_blockers.append({
            "code": "EQUIPMENT_MATCH_NOT_CLOSED",
            "equipment": unclosed_equipment,
        })
    if not no_connection_blockers:
        formal_use_blockers.append({"code": "ADAPTER_CONNECTION_BLOCKER"})
    formal_use_blockers.extend({"code": "CALCULATION_HARD_BLOCKER", "detail": item} for item in calculation_hard_blockers)
    formal_use_blockers.extend({"code": "ASPEN_RECONCILIATION_FAIL", "detail": item} for item in reconciliation_failures)
    process_basis_gate = (
        "ELIGIBLE_AS_PROCESS_BASIS"
        if not formal_use_blockers
        else "PROVISIONAL_NOT_FORMAL_PROCESS_BASIS"
    )
    case_path = bundle.get("case", {}).get("source_case_path") if isinstance(bundle.get("case"), dict) else None
    case_evidence: dict[str, Any] = {"source_case_path": case_path, "source_case_sha256": None, "status": "NOT_PROVIDED"}
    if case_path:
        resolved = Path(str(case_path)).expanduser()
        if not resolved.is_absolute():
            resolved = source_file.parent / resolved
        if resolved.is_file():
            case_evidence = {"source_case_path": str(resolved.resolve()), "source_case_sha256": sha256_file(resolved), "status": "HASHED"}
        else:
            case_evidence["status"] = "FILE_NOT_FOUND"
            process_basis_gate = "PROVISIONAL_NOT_FORMAL_PROCESS_BASIS"
            formal_use_blockers.append({"code": "SOURCE_CASE_FILE_NOT_FOUND", "path": str(case_path)})
    return {
        "schema": "aspen-equipment-derivation-result-v1",
        "engine_version": ENGINE_VERSION,
        "deterministic": True,
        "llm_used": False,
        "status": "DERIVED",
        "source_export_path": str(source_file),
        "source_export_sha256": source_sha256,
        "pfd_mapping_sha256": pfd_mapping_sha256,
        "case_id": bundle.get("case", {}).get("case_id") if isinstance(bundle.get("case"), dict) else None,
        "source_case_evidence": case_evidence,
        "aspen_run_gate": gate,
        "formal_use_gate": process_basis_gate,
        "formal_use_blockers": formal_use_blockers,
        "normalization_diagnostic_count": len(normalization_diagnostics),
        "normalization_diagnostics": normalization_diagnostics,
        "equipment_count": len(equipment),
        "equipment": equipment,
        "piping_count": len(piping),
        "piping": piping,
        "isolated_stream_diagnostics": isolated_stream_diagnostics,
        "piping_evidence_boundary": {
            "status": "INDEPENDENT_PFD_PROCESS_DATA_PROJECTION",
            "affects_aspen_formal_use_gate": False,
            "aspen_formal_use_gate_snapshot": process_basis_gate,
            "mechanical_design_defaults_applied": False,
            "not_established": [
                "design_temperature_c", "target_velocity_m_s", "material", "selected_dn",
                "selected_outer_diameter_mm", "selected_wall_thickness_mm", "wall_series",
                "mechanical_stress_verification", "vendor_model",
            ],
        },
        "non_aspen_boundaries": [
            "Aspen process results do not set design pressure or design temperature.",
            "Aspen process results do not prove material, corrosion allowance, mechanical thickness, internals, vendor model, or performance curve.",
            "Dirty or unverified Aspen runs remain provisional even when a numeric derivation is possible.",
            "PFD piping records expose process-side edge data and missing gates only; they do not establish line class, DN, wall thickness, material, or design temperature.",
        ],
        "review_role": "LLM audit only; deterministic adapter and matcher remain primary.",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert an Aspen export bundle into deterministic equipment derivation chains.")
    parser.add_argument("--input", required=True, type=Path, help="JSON file following aspen-equipment-export-v1")
    parser.add_argument("--output", type=Path, help="Output JSON path; stdout when omitted")
    parser.add_argument("--require-clean", action="store_true", help="Return exit code 4 unless the clean-run formal process-basis gate passes")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        bundle = json.loads(args.input.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "BLOCKED_INPUT_READ", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    if not isinstance(bundle, dict):
        print(json.dumps({"status": "BLOCKED_INPUT_SHAPE", "error": "top-level JSON must be an object"}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    result = derive_bundle(bundle, args.input)
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    if result["status"].startswith("BLOCKED_"):
        return 2
    if args.require_clean and result.get("formal_use_gate") != "ELIGIBLE_AS_PROCESS_BASIS":
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
