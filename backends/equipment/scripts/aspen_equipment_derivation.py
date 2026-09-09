from __future__ import annotations

import argparse
import csv
import functools
import hashlib
import json
import math
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
FROZEN_ROOT = getattr(sys, "_MEIPASS", None)
PACKAGE_ROOT = Path(FROZEN_ROOT).resolve() if FROZEN_ROOT else SCRIPT_PATH.parents[1]
APP_DIR = PACKAGE_ROOT / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import equipment_design_match as matcher
import equipment_service_profile as service_profile
import connection_component_selection as connection_selection
import database_authority
import viscosity_fallback


SCHEMA_PATH = PACKAGE_ROOT / "knowledge_graph" / "aspen_equipment_export.schema.json"
PIPE_STANDARD_CONSUMER_ID = "pipe_standard_store"
PIPE_STANDARD_DECLARATION = database_authority.declared_database_for_consumer(
    PIPE_STANDARD_CONSUMER_ID,
    PACKAGE_ROOT,
)
PIPE_STANDARD_DB_PATH = Path(PIPE_STANDARD_DECLARATION["database_path"])
PIPE_STANDARD_MANIFEST_PATH = Path(PIPE_STANDARD_DECLARATION["manifest_path"])
PIPE_STANDARD_STORE_DIR = PIPE_STANDARD_DB_PATH.parent
DATABASE_AUTHORITY_REGISTRY_PATH = (
    PACKAGE_ROOT / database_authority.REGISTRY_RELATIVE_PATH
)
STANDARD_SOURCE_INVENTORY_PATH = (
    PACKAGE_ROOT
    / "knowledge_graph"
    / "selection_learning_graph_20260622"
    / "standard_source_inventory.csv"
)
ENGINE_VERSION = "1.9.3"
SINGLE_INLET_OUTLET_BLOCKS = {"PUMP", "COMPR", "MCOMPR", "VALVE", "HEATER", "PIPE"}
CLEAN_BLOCK_WORDS = {"0", "ok", "pass", "passed", "converged", "success", "successful", "完成", "正常"}
SIMULATION_LOGIC_BLOCK_TYPES = frozenset({"FSPLIT", "MIXER", "HIERARCHY"})
PHYSICAL_PIPING_BLOCK_TYPES = frozenset({"PIPE"})
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
    "dynamic_viscosity_mpa_s": (1.0e-12, 1.0e9),
    "liquid_dynamic_viscosity_mpa_s": (1.0e-12, 1.0e9),
    "vapor_dynamic_viscosity_mpa_s": (1.0e-12, 1.0e9),
    "heat_duty_kw": (-1.0e12, 1.0e12),
    "heat_transfer_area_m2": (0.0, 1.0e12),
    "shaft_power_kw": (-1.0e12, 1.0e12),
    "hydraulic_power_kw": (-1.0e12, 1.0e12),
    "electrical_power_kw": (-1.0e12, 1.0e12),
    "driver_efficiency_percent": (0.0, 100.0),
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
    "dynamic_viscosity_mpa_s": [
        ("dynamic_viscosity_mpa_s", "mPa*s", False),
        ("viscosity_mpa_s", "mPa*s", False),
        ("MUMX", None, True),
    ],
    "liquid_dynamic_viscosity_mpa_s": [
        ("liquid_dynamic_viscosity_mpa_s", "mPa*s", False),
        ("MUMX_LIQUID", None, True),
    ],
    "vapor_dynamic_viscosity_mpa_s": [
        ("vapor_dynamic_viscosity_mpa_s", "mPa*s", False),
        ("MUMX_VAPOR", None, True),
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
    ],
    "hydraulic_power_kw": [
        ("hydraulic_power_kw", "kW", False), ("FLUID_POWER", None, True),
    ],
    "electrical_power_kw": [
        ("electrical_power_kw", "kW", False), ("ELEC_POWER", None, True),
    ],
    "driver_efficiency_percent": [
        ("driver_efficiency_percent", "percent", False),
        ("DEFF", "fraction", False),
    ],
    "head_m": [("head_m", "m", False), ("HEAD_CAL", None, True)],
    # ``NPSHA`` is deliberately routed by ``normalize_block`` instead of being
    # assigned a fixed semantic here.  A normal COM observation may be a head
    # with a declared length unit, whereas Aspen's raw ``.his`` UOS field
    # ``NPSH AVAIL`` is a kPa suction-pressure margin.  Treating both as metres
    # caused physically impossible pump results in the real-case audit.
    "npsha_m": [("npsha_m", "m", False)],
    "npsha_pressure_kpa": [("npsha_pressure_kpa", "kPa", False)],
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
    "dynamic_viscosity_mpa_s": "mPa*s",
    "liquid_dynamic_viscosity_mpa_s": "mPa*s",
    "vapor_dynamic_viscosity_mpa_s": "mPa*s",
    "vapor_fraction": "-",
    "liquid_fraction": "-",
    "solid_fraction": "-",
    "molecular_weight": "kg/kmol",
    "compressibility_factor": "-",
    "heat_duty_kw": "kW",
    "heat_transfer_area_m2": "m2",
    "shaft_power_kw": "kW",
    "hydraulic_power_kw": "kW",
    "electrical_power_kw": "kW",
    "driver_efficiency_percent": "percent",
    "head_m": "m",
    "npsha_m": "m",
    "npsha_pressure_kpa": "kPa",
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
    ("hydraulic_power_kw", "hydraulic_power_kw", "kW"),
    ("electrical_power_kw", "electrical_power_kw", "kW"),
    (
        "driver_efficiency_percent",
        "driver_efficiency_percent",
        "%",
    ),
    ("head_m", "head_m", "m"),
    ("npsha_m", "npsha_m", "m"),
    ("npsha_pressure_kpa", "npsha_pressure_kpa", "kPa"),
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
    ("dynamic_viscosity_mpa_s", "dynamic_viscosity_mpa_s", "mPa·s"),
    ("liquid_dynamic_viscosity_mpa_s", "liquid_dynamic_viscosity_mpa_s", "mPa·s"),
    ("vapor_dynamic_viscosity_mpa_s", "vapor_dynamic_viscosity_mpa_s", "mPa·s"),
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
        "f": "F", "°f": "F", "r": "R", "°r": "R",
        "mpa": "MPa", "kpa": "kPa", "pa": "Pa", "bar": "bar", "atm": "atm",
        "psi": "psi", "psia": "psia", "psig": "psig",
        "lbf/sqin": "psi", "lbf/sq.in": "psi",
        "kg/sqcm": "kgf/cm2", "kg/cm2": "kgf/cm2",
        "kgf/sqcm": "kgf/cm2", "kgf/cm2": "kgf/cm2",
        "kg/h": "kg/h", "kg/hr": "kg/h", "kg/s": "kg/s", "t/h": "t/h",
        "tonne/h": "t/h", "tonne/hr": "t/h", "metric ton/hr": "t/h",
        "lb/h": "lb/h", "lb/hr": "lb/h", "lb/s": "lb/s",
        "m3/h": "m3/h", "m^3/h": "m3/h", "cum/hr": "m3/h",
        "m3/s": "m3/s", "m^3/s": "m3/s",
        "l/min": "L/min",
        "cuft/hr": "ft3/h", "ft3/h": "ft3/h", "ft^3/h": "ft3/h",
        "cuft/min": "ft3/min", "cfm": "ft3/min", "ft3/min": "ft3/min",
        "gal/min": "USgal/min", "gpm": "USgal/min",
        "kg/m3": "kg/m3", "kg/m^3": "kg/m3", "kg/cum": "kg/m3",
        "gm/cc": "g/cm3", "g/cm3": "g/cm3", "g/cm^3": "g/cm3",
        "lb/cuft": "lb/ft3", "lb/ft3": "lb/ft3", "lb/ft^3": "lb/ft3",
        "cp": "mPa*s", "centipoise": "mPa*s",
        "mpa-s": "mPa*s", "mpa.s": "mPa*s", "mpa*s": "mPa*s",
        "pa-s": "Pa*s", "pa.s": "Pa*s", "pa*s": "Pa*s",
        "n-sec/sqm": "Pa*s", "n-s/sqm": "Pa*s",
        "kg/m-s": "Pa*s", "kg/m/s": "Pa*s",
        "kw": "kW", "w": "W", "watt": "W", "mw": "MW",
        "hp": "hp", "horsepower": "hp",
        "cal/sec": "cal/s", "cal/s": "cal/s",
        "kcal/h": "kcal/h", "kcal/hr": "kcal/h",
        "gcal/h": "Gcal/h", "gcal/hr": "Gcal/h",
        "btu/h": "Btu/h", "btu/hr": "Btu/h", "btu/sec": "Btu/s", "btu/s": "Btu/s",
        "mmbtu/h": "MMBtu/h", "mmbtu/hr": "MMBtu/h",
        "m2": "m2", "m^2": "m2", "sqm": "m2",
        "sqft": "ft2", "sq.ft": "ft2", "ft2": "ft2", "ft^2": "ft2",
        "m": "m", "meter": "m", "meters": "m", "metre": "m", "metres": "m",
        "ft": "ft", "foot": "ft", "feet": "ft",
        "in": "in", "inch": "in", "inches": "in",
        "mm": "mm", "millimeter": "mm", "millimeters": "mm",
        "millimetre": "mm", "millimetres": "mm", "cum": "m3",
        "cuft": "ft3", "ft3": "ft3", "ft^3": "ft3",
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
        ("F", "C"): (5.0 / 9.0, -160.0 / 9.0, "T_C=(T_F-32)×5/9"),
        ("R", "C"): (5.0 / 9.0, -273.15, "T_C=T_R×5/9-273.15"),
        ("bar", "MPa"): (0.1, 0.0, "P_MPa=P_bar×0.1"),
        ("atm", "MPa"): (0.101325, 0.0, "P_MPa=P_atm×0.101325"),
        ("kPa", "MPa"): (0.001, 0.0, "P_MPa=P_kPa×0.001"),
        ("Pa", "MPa"): (1e-6, 0.0, "P_MPa=P_Pa×10^-6"),
        ("psi", "MPa"): (0.006894757293168, 0.0, "P_MPa=P_psi×0.006894757293168"),
        ("psia", "MPa"): (0.006894757293168, 0.0, "P_MPa=P_psia×0.006894757293168"),
        ("psig", "MPa"): (0.006894757293168, 0.0, "P_MPa=P_psig×0.006894757293168"),
        ("kgf/cm2", "MPa"): (0.0980665, 0.0, "P_MPa=P_kgf/cm2×0.0980665"),
        ("kg/s", "kg/h"): (3600.0, 0.0, "m_kg/h=m_kg/s×3600"),
        ("t/h", "kg/h"): (1000.0, 0.0, "m_kg/h=m_t/h×1000"),
        ("lb/h", "kg/h"): (0.45359237, 0.0, "m_kg/h=m_lb/h×0.45359237"),
        ("lb/s", "kg/h"): (1632.932532, 0.0, "m_kg/h=m_lb/s×0.45359237×3600"),
        ("m3/s", "m3/h"): (3600.0, 0.0, "V_m3/h=V_m3/s×3600"),
        ("L/min", "m3/h"): (0.06, 0.0, "V_m3_per_h=V_L_per_min×0.06"),
        ("ft3/h", "m3/h"): (0.028316846592, 0.0, "V_m3/h=V_ft3/h×0.028316846592"),
        ("ft3/min", "m3/h"): (1.69901079552, 0.0, "V_m3/h=V_ft3/min×0.028316846592×60"),
        ("USgal/min", "m3/h"): (0.22712470704, 0.0, "V_m3/h=V_USgal/min×0.003785411784×60"),
        ("g/cm3", "kg/m3"): (1000.0, 0.0, "rho_kg_per_m3=rho_g_per_cm3×1000"),
        ("lb/ft3", "kg/m3"): (16.01846337396, 0.0, "rho_kg/m3=rho_lb/ft3×16.01846337396"),
        ("Pa*s", "mPa*s"): (1000.0, 0.0, "mu_mPa_s=mu_Pa_s×1000"),
        ("W", "kW"): (0.001, 0.0, "Q_kW=Q_W×0.001"),
        ("MW", "kW"): (1000.0, 0.0, "Q_kW=Q_MW×1000"),
        ("hp", "kW"): (0.745699871582, 0.0, "P_kW=P_hp×0.745699871582"),
        ("cal/s", "kW"): (0.004184, 0.0, "Q_kW=Q_cal_per_s×0.004184"),
        ("kcal/h", "kW"): (4.184 / 3600.0, 0.0, "Q_kW=Q_kcal_per_h×0.00116222222222"),
        ("Gcal/h", "kW"): (4.184e6 / 3600.0, 0.0, "Q_kW=Q_Gcal_per_h×1162.22222222"),
        ("Btu/h", "kW"): (0.000293071070172, 0.0, "Q_kW=Q_Btu/h×0.000293071070172"),
        ("Btu/s", "kW"): (1.05505585262, 0.0, "Q_kW=Q_Btu/s×1.05505585262"),
        ("MMBtu/h", "kW"): (293.071070172, 0.0, "Q_kW=Q_MMBtu/h×293.071070172"),
        ("ft2", "m2"): (0.09290304, 0.0, "A_m2=A_ft2×0.09290304"),
        ("fraction", "percent"): (100.0, 0.0, "eta_percent=eta_fraction×100"),
        ("m-kgf/kg", "m"): (1.0, 0.0, "H_m=E_mkgf_per_kg×9.80665/9.80665"),
        ("J/kg", "m"): (1.0 / 9.80665, 0.0, "H_m=E_J_per_kg/9.80665"),
        ("bar", "kPa"): (100.0, 0.0, "dP_kPa=dP_bar×100"),
        ("atm", "kPa"): (101.325, 0.0, "dP_kPa=dP_atm×101.325"),
        ("psi", "kPa"): (6.894757293168, 0.0, "dP_kPa=dP_psi×6.894757293168"),
        ("psia", "kPa"): (6.894757293168, 0.0, "dP_kPa=dP_psia×6.894757293168"),
        ("psig", "kPa"): (6.894757293168, 0.0, "dP_kPa=dP_psig×6.894757293168"),
        ("kgf/cm2", "kPa"): (98.0665, 0.0, "dP_kPa=dP_kgf/cm2×98.0665"),
        ("ft", "m"): (0.3048, 0.0, "L_m=L_ft×0.3048"),
        ("in", "m"): (0.0254, 0.0, "L_m=L_in×0.0254"),
        ("m", "mm"): (1000.0, 0.0, "L_mm=L_m×1000"),
        ("mm", "m"): (0.001, 0.0, "L_m=L_mm×0.001"),
        ("ft", "mm"): (304.8, 0.0, "L_mm=L_ft×304.8"),
        ("in", "mm"): (25.4, 0.0, "L_mm=L_in×25.4"),
        ("ft3", "m3"): (0.028316846592, 0.0, "V_m3=V_ft3×0.028316846592"),
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
    phase_value = str(result.get("phase") or "").strip()
    phase_source_field = str(result.get("phase_source_field") or "phase").strip()
    if phase_value:
        raw_paths = (
            row.get("aspen_raw_paths")
            if isinstance(row.get("aspen_raw_paths"), dict)
            else {}
        )
        raw_values = (
            row.get("aspen_raw_values")
            if isinstance(row.get("aspen_raw_values"), dict)
            else {}
        )
        phase_source_record = raw_values.get(phase_source_field)
        result["_sources"]["phase"] = {
            "source_field": phase_source_field,
            "source_path": str(
                raw_paths.get(phase_source_field)
                or f"stream:{stream_id}.{phase_source_field}"
            ),
            "raw_value": (
                phase_source_record.get("value")
                if isinstance(phase_source_record, dict)
                else row.get(phase_source_field, phase_value)
            ),
            "source_unit": (
                str(phase_source_record.get("unit") or "-")
                if isinstance(phase_source_record, dict)
                else "-"
            ),
            "transform": str(
                result.get("phase_origin")
                or "ASPEN_EXPORTED_OR_ADAPTER_RAW_FIELD"
            ),
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


def enrich_stream_viscosity(
    stream: dict[str, Any],
    *,
    correlation_records: dict[str, Any],
    correlation_registry: dict[str, Any],
    source_export_sha256: str,
) -> dict[str, Any]:
    """Fill only a missing single-phase mixture viscosity.

    Authority order is fixed:
    1. keep an exported mixture MUMX value;
    2. promote an exported phase-specific MUMX value for an unambiguous
       single-phase stream;
    3. evaluate the source-bound internal correlation;
    4. leave the value absent when any correlation gate is open.

    The correlation branch is evidence class J and is permanently capped at
    preliminary type/hydraulic screening.  It never replaces two-phase
    hydraulics and never claims to be an Aspen property observation.
    """

    stream_id = str(stream.get("stream_id") or "")
    phase = matcher.canonical_phase(stream.get("phase"))
    existing = finite_number(stream.get("dynamic_viscosity_mpa_s"))
    if existing is not None and existing > 0.0:
        source = (
            stream.get("_sources", {}).get("dynamic_viscosity_mpa_s", {})
            if isinstance(stream.get("_sources"), dict)
            else {}
        )
        diagnostic = {
            "schema": "stream-viscosity-fallback-diagnostic-v1",
            "stream_id": stream_id,
            "status": "NOT_NEEDED_EXPORTED_MIXTURE_VISCOSITY_PRESENT",
            "authority": "EXPORTED_MIXTURE_DYNAMIC_VISCOSITY",
            "canonical_phase": phase,
            "dynamic_viscosity_mpa_s": existing,
            "source_field": source.get("source_field"),
            "source_path": source.get("source_path"),
            "source_export_sha256": source_export_sha256,
            "internal_correlation_used": False,
        }
        diagnostic["diagnostic_sha256"] = _canonical_sha256(diagnostic)
        stream["viscosity_fallback_diagnostic"] = diagnostic
        return diagnostic

    phase_field = {
        "liquid": "liquid_dynamic_viscosity_mpa_s",
        "vapor": "vapor_dynamic_viscosity_mpa_s",
    }.get(phase)
    phase_value = finite_number(stream.get(phase_field)) if phase_field else None
    if phase_field and phase_value is not None and phase_value > 0.0:
        source_map = (
            stream.setdefault("_sources", {})
            if isinstance(stream.get("_sources"), dict)
            else {}
        )
        if source_map is not stream.get("_sources"):
            stream["_sources"] = source_map
        phase_source = (
            dict(source_map.get(phase_field, {}))
            if isinstance(source_map.get(phase_field), dict)
            else {}
        )
        phase_source.update({
            "source_field": str(
                phase_source.get("source_field") or phase_field
            ),
            "raw_value": phase_source.get("raw_value", phase_value),
            "source_unit": str(
                phase_source.get("source_unit") or "mPa*s"
            ),
            "transform": (
                "promote_exported_phase_specific_MUMX_for_"
                f"unambiguous_{phase}_stream"
            ),
            "formula": f"mu_mix=mu_{phase}_Aspen_MUMX",
            "origin": "ASPEN_EXTRACTED_PHASE_SPECIFIC_PROMOTION",
            "evidence_class": "D",
            "result_status": "ASPEN_PHASE_SPECIFIC_MUMX_PROMOTED",
            "evidence_scope": "ASPEN_SINGLE_PHASE_PROCESS_PROPERTY",
            "promotion_cap": "PROCESS_SIDE_ONLY",
            "warning": (
                "The exported phase-specific Aspen MUMX value is promoted only "
                f"because the stream is unambiguously {phase}; it remains a "
                "process property, not mechanical-design release evidence."
            ),
            "warning_codes": [
                "W_PHASE_SPECIFIC_MUMX_PROMOTED_FOR_SINGLE_PHASE_STREAM"
            ],
            "formal_design_evidence": False,
        })
        stream["dynamic_viscosity_mpa_s"] = phase_value
        source_map["dynamic_viscosity_mpa_s"] = phase_source
        diagnostic = {
            "schema": "stream-viscosity-fallback-diagnostic-v1",
            "stream_id": stream_id,
            "status": "ASPEN_PHASE_SPECIFIC_MUMX_PROMOTED",
            "authority": "EXPORTED_PHASE_SPECIFIC_ASPEN_MUMX",
            "canonical_phase": phase,
            "promoted_from_field": phase_field,
            "dynamic_viscosity_mpa_s": phase_value,
            "source_path": phase_source.get("source_path"),
            "source_export_sha256": source_export_sha256,
            "internal_correlation_used": False,
            "warning_codes": phase_source["warning_codes"],
        }
        diagnostic["diagnostic_sha256"] = _canonical_sha256(diagnostic)
        stream["viscosity_fallback_diagnostic"] = diagnostic
        return diagnostic

    temperature_c = finite_number(stream.get("temperature_c"))
    estimate = viscosity_fallback.estimate_stream_viscosity(
        phase=phase or str(stream.get("phase") or ""),
        temperature_k=(
            temperature_c + 273.15
            if temperature_c is not None
            else None
        ),
        composition=(
            stream.get("composition", [])
            if isinstance(stream.get("composition"), list)
            else []
        ),
        correlation_records=correlation_records,
    )
    diagnostic = {
        **estimate,
        "diagnostic_schema": "stream-viscosity-fallback-diagnostic-v1",
        "stream_id": stream_id,
        "canonical_phase": phase,
        "source_export_sha256": source_export_sha256,
        "correlation_records_embedded_in_source_export": True,
        "embedded_correlation_record_set_sha256": (
            viscosity_fallback.canonical_sha256(correlation_records)
        ),
        "correlation_registry": dict(correlation_registry),
        "internal_correlation_used": (
            estimate.get("status") == "PASS_WITH_WARNING"
        ),
    }
    diagnostic["diagnostic_sha256"] = _canonical_sha256(diagnostic)
    stream["viscosity_fallback_diagnostic"] = diagnostic
    if estimate.get("status") != "PASS_WITH_WARNING":
        return diagnostic

    value = finite_number(estimate.get("dynamic_viscosity_mpa_s"))
    if value is None or value <= 0.0:
        # Defensive stop: the correlation module should already have rejected
        # this result, but a nonphysical value must never enter hydraulics.
        diagnostic["status"] = "BLOCKED_NONPHYSICAL_VISCOSITY_ESTIMATE"
        diagnostic["internal_correlation_used"] = False
        diagnostic["diagnostic_sha256"] = _canonical_sha256({
            key: item
            for key, item in diagnostic.items()
            if key != "diagnostic_sha256"
        })
        return diagnostic

    warning = (
        "强警告：该黏度由程序内置纯组分关联式与混合规则计算，不是 Aspen "
        "提取值；仅允许单相管径、雷诺数和压降的初步筛选。组分系数来源文件尚未在"
        "本次运行中独立打开核验，液相二元交互参数或气相高压修正也未闭合，严禁"
        "用于正式管道等级、设备定型或设计发布。"
    )
    sources = stream.setdefault("_sources", {})
    sources["dynamic_viscosity_mpa_s"] = {
        "source_field": "INTERNAL_CORRELATION_ESTIMATE",
        "source_path": "#/viscosity_correlation_records",
        "raw_value": value,
        "source_unit": "mPa*s",
        "transform": "source_bound_internal_viscosity_correlation",
        "formula": str(estimate.get("mixing_formula") or ""),
        "origin": "INTERNAL_CORRELATION_ESTIMATE",
        "evidence_class": "J",
        "result_status": "PASS_WITH_WARNING",
        "evidence_scope": "PRELIMINARY_SINGLE_PHASE_HYDRAULICS_ONLY",
        "promotion_cap": "TYPE_SCREENING",
        "warning": warning,
        "warning_codes": list(estimate.get("warning_codes") or []),
        "formal_design_evidence": False,
        "result_sha256": estimate.get("result_sha256"),
        "source_bundle_sha256": estimate.get("source_bundle_sha256"),
        "formula_sources": list(estimate.get("formula_sources") or []),
        "mixing_rule": estimate.get("mixing_rule"),
        "basis_conversion": estimate.get("basis_conversion"),
        "diagnostic_sha256": diagnostic["diagnostic_sha256"],
    }
    stream["dynamic_viscosity_mpa_s"] = value
    return diagnostic


def enrich_stream_viscosities(
    streams: list[dict[str, Any]],
    *,
    bundle: dict[str, Any],
    source_export_sha256: str,
) -> list[dict[str, Any]]:
    records = (
        dict(bundle.get("viscosity_correlation_records") or {})
        if isinstance(bundle.get("viscosity_correlation_records"), dict)
        else {}
    )
    registry = (
        dict(bundle.get("viscosity_correlation_registry") or {})
        if isinstance(bundle.get("viscosity_correlation_registry"), dict)
        else {}
    )
    return [
        enrich_stream_viscosity(
            stream,
            correlation_records=records,
            correlation_registry=registry,
            source_export_sha256=source_export_sha256,
        )
        for stream in streams
    ]


def normalize_block(row: dict[str, Any], units: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    block_id = str(row.get("block_id") or row.get("tag") or row.get("id") or "").strip()
    block_type = str(row.get("block_type") or row.get("type") or row.get("aspen_block_type") or "").strip().upper()
    normalization_row = dict(row)
    normalization_units = dict(units)
    normalization_paths = (
        dict(row.get("aspen_raw_paths") or {})
        if isinstance(row.get("aspen_raw_paths"), dict)
        else {}
    )
    normalization_row["aspen_raw_paths"] = normalization_paths
    npsh_route_error: dict[str, Any] | None = None
    npsh_legacy_export_unit_reinterpretation: dict[str, Any] | None = None
    raw_npsh = finite_number(row.get("NPSHA"))
    if raw_npsh is not None:
        raw_values = (
            row.get("aspen_raw_values", {})
            if isinstance(row.get("aspen_raw_values"), dict)
            else {}
        )
        raw_record = (
            dict(raw_values.get("NPSHA") or {})
            if isinstance(raw_values.get("NPSHA"), dict)
            else {}
        )
        raw_path = str(normalization_paths.get("NPSHA") or "")
        raw_status = str(raw_record.get("status") or "").casefold()
        quantity_kind = str(raw_record.get("quantity_kind") or "").casefold()
        history_pressure_margin = (
            raw_path.casefold().startswith("raw_history:")
            or raw_status.startswith("raw_history")
            or quantity_kind == "available_suction_pressure_margin"
        )
        declared_unit = unit_for(
            normalization_units,
            "block",
            "NPSHA",
            block_id or "<missing>",
        )
        if history_pressure_margin:
            # Legacy exports generated before the importer fix incorrectly
            # labelled this same raw-history observation as metres.  The
            # immutable path/status/quantity metadata takes precedence, so old
            # exports can be repaired offline without rerunning Aspen COM.
            target_field = "npsha_pressure_kpa"
            normalization_row[target_field] = raw_npsh
            normalization_paths[target_field] = raw_path or (
                f"raw_history:{block_id}:NPSH AVAIL"
            )
            normalization_units[f"block.{block_id}.{target_field}"] = "kPa"
            normalization_units[f"block.{target_field}"] = "kPa"
            hash_bound_raw_unit = str(
                raw_record.get("raw_unit")
                or raw_record.get("unit")
                or declared_unit
                or ""
            ).strip()
            if normalize_unit(hash_bound_raw_unit).casefold() not in {
                "kpa",
                "",
            }:
                npsh_legacy_export_unit_reinterpretation = {
                    "legacy_export_unit_reinterpreted_as_kpa": True,
                    "hash_bound_export_raw_value": raw_npsh,
                    "hash_bound_export_raw_unit": hash_bound_raw_unit,
                    "reinterpretation_basis": (
                        "raw_history path/status/quantity identity NPSH AVAIL "
                        "overrides the legacy export's incorrect length label"
                    ),
                    "production_action": (
                        "rerun the corrected COM extractor when Aspen is "
                        "available; until then this remains preliminary"
                    ),
                }
        elif declared_unit:
            routed = False
            for target_field, target_unit in (
                ("npsha_m", "m"),
                ("npsha_pressure_kpa", "kPa"),
            ):
                try:
                    converted, _transform = convert(
                        raw_npsh,
                        declared_unit,
                        target_unit,
                    )
                except ValueError:
                    continue
                normalization_row[target_field] = converted
                normalization_paths[target_field] = (
                    raw_path or f"block:{block_id}.NPSHA"
                )
                normalization_units[
                    f"block.{block_id}.{target_field}"
                ] = target_unit
                routed = True
                break
            if not routed:
                npsh_route_error = {
                    "object": block_id or "<missing>",
                    "field": "NPSHA",
                    "code": "UNSUPPORTED_NPSHA_QUANTITY_UNIT",
                    "raw_value": raw_npsh,
                    "raw_unit": declared_unit,
                    "detail": (
                        "NPSHA must be declared either as a length head or a "
                        "pressure margin; the value was excluded."
                    ),
                }
        else:
            npsh_route_error = {
                "object": block_id or "<missing>",
                "field": "NPSHA",
                "code": "MISSING_EXPLICIT_NPSHA_UNIT_AND_QUANTITY_KIND",
                "raw_value": raw_npsh,
            }
    block_aliases = {
        target: list(candidates)
        for target, candidates in BLOCK_ALIASES.items()
    }
    # Aspen PUMP WNET is the electrical utility demand when a driver
    # efficiency is configured; it is not the pump brake/shaft power.  Other
    # rotating-unit models historically expose WNET as shaft work, so preserve
    # that legacy route only outside PUMP.
    if block_type == "PUMP":
        block_aliases["electrical_power_kw"].append(
            ("WNET", None, True)
        )
    else:
        block_aliases["shaft_power_kw"].append(("WNET", None, True))
    values, sources, errors = extract_numeric_fields(
        normalization_row,
        block_aliases,
        normalization_units,
        "block",
        block_id or "<missing>",
    )
    if npsh_route_error is not None:
        errors.append(npsh_route_error)
    if "npsha_pressure_kpa" in sources:
        source = sources["npsha_pressure_kpa"]
        source.update({
            "source_field": "NPSHA",
            "source_path": str(
                normalization_paths.get("npsha_pressure_kpa")
                or normalization_paths.get("NPSHA")
                or f"block:{block_id}.NPSHA"
            ),
            "transform": (
                "classify_Aspen_history_NPSH_AVAIL_as_pressure_margin_kPa"
            ),
            "origin": "ASPEN_RAW_HISTORY_PRESSURE_MARGIN",
            "evidence_class": "D",
            "result_status": "ASPEN_HISTORY_PRESSURE_MARGIN_NORMALIZED",
            "evidence_scope": "PUMP_SUCTION_PROCESS_SCREENING",
            "promotion_cap": "TYPE_SCREENING",
            "formal_design_evidence": False,
            "warning": (
                "Aspen .his NPSH AVAIL is retained as a kPa suction-pressure "
                "margin. It is converted to metres only after binding the "
                "same pump inlet density; it is not accepted as a direct head."
            ),
        })
        if npsh_legacy_export_unit_reinterpretation is not None:
            source.update(npsh_legacy_export_unit_reinterpretation)
            source["source_unit"] = str(
                npsh_legacy_export_unit_reinterpretation[
                    "hash_bound_export_raw_unit"
                ]
            )
            source["transform"] = (
                "legacy_export_unit_reinterpreted_as_kPa_by_"
                "hash_bound_NPSH_AVAIL_quantity_identity"
            )
    pump_power_semantics = {
        "hydraulic_power_kw": (
            "ASPEN_PUMP_FLUID_POWER",
            "Pump hydraulic power delivered to the fluid.",
        ),
        "shaft_power_kw": (
            "ASPEN_PUMP_BRAKE_POWER",
            "Pump brake/shaft power before driver losses.",
        ),
        "electrical_power_kw": (
            "ASPEN_PUMP_ELECTRICAL_INPUT_POWER",
            "Electrical utility input including configured driver losses.",
        ),
        "efficiency_percent": (
            "ASPEN_PUMP_HYDRAULIC_EFFICIENCY",
            (
                "Pump hydraulic efficiency used only in the fluid-to-shaft "
                "process-power balance; it is distinct from driver efficiency."
            ),
        ),
        "driver_efficiency_percent": (
            "ASPEN_PUMP_DRIVER_EFFICIENCY",
            "Pump driver efficiency, distinct from pump hydraulic efficiency.",
        ),
    }
    if block_type == "PUMP":
        for field_id, (origin, warning) in pump_power_semantics.items():
            source = sources.get(field_id)
            if not isinstance(source, dict):
                continue
            source.update({
                "origin": origin,
                "evidence_class": "D",
                "result_status": "ASPEN_PUMP_POWER_SEMANTIC_NORMALIZED",
                "evidence_scope": "PUMP_PROCESS_POWER_BALANCE",
                "promotion_cap": "TYPE_SCREENING",
                "formal_design_evidence": False,
                "warning": warning,
            })
    result = {
        "block_id": block_id,
        "block_type": block_type,
        "inlet_streams": list_value(row.get("inlet_streams", row.get("in"))),
        "outlet_streams": list_value(row.get("outlet_streams", row.get("out"))),
        "connections": [
            dict(item)
            for item in row.get("connections", [])
            if isinstance(item, dict)
        ] if isinstance(row.get("connections"), list) else [],
        "port_detail": [
            dict(item)
            for item in row.get("port_detail", [])
            if isinstance(item, dict)
        ] if isinstance(row.get("port_detail"), list) else [],
        "block_status": row.get("block_status", row.get("BLKSTAT")),
        "aspen_raw_paths": dict(row.get("aspen_raw_paths") or {})
        if isinstance(row.get("aspen_raw_paths"), dict)
        else {},
        "aspen_raw_values": dict(row.get("aspen_raw_values") or {})
        if isinstance(row.get("aspen_raw_values"), dict)
        else {},
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
    result = {
        "value": value,
        "canonical_unit": canonical_unit,
        "source_field": str(source.get("source_field") or ""),
        "source_path": str(source.get("source_path") or ""),
        "raw_value": source.get("raw_value", value),
        "raw_unit": str(source.get("source_unit") or canonical_unit),
        "transform": transform,
        "source_status": "ASPEN_DERIVED_PROCESS_SIDE",
        "normalization_status": "NORMALIZED",
        "evidence_class": str(
            source.get("evidence_class")
            or ("R" if transform == "identity" else "D")
        ),
        "formal_design_evidence": bool(
            source.get("formal_design_evidence", False)
        ),
    }
    for field_id in (
        "origin",
        "result_status",
        "evidence_scope",
        "promotion_cap",
        "warning",
        "source_file_path",
        "source_file_sha256",
    ):
        if source.get(field_id) not in (None, ""):
            result[field_id] = source[field_id]
    return result


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
        elif source_field == "diameter_mm" and block_type == "RPLUG":
            effective_target = "active_tube_inner_diameter_mm"
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


CONNECTED_STREAM_OBSERVATION_FIELDS: tuple[tuple[str, str], ...] = (
    ("phase", "-"),
    ("temperature_c", "C"),
    ("pressure_mpa", "MPa"),
    ("volumetric_flow_m3_h", "m3/h"),
    ("liquid_volumetric_flow_m3_h", "m3/h"),
    ("vapor_volumetric_flow_m3_h", "m3/h"),
    ("mass_flow_kg_h", "kg/h"),
    ("density_kg_m3", "kg/m3"),
    ("dynamic_viscosity_mpa_s", "mPa*s"),
    ("liquid_dynamic_viscosity_mpa_s", "mPa*s"),
    ("vapor_dynamic_viscosity_mpa_s", "mPa*s"),
)


def build_connected_stream_observations(
    *,
    block: dict[str, Any],
    streams: dict[str, dict[str, Any]],
    source_file: Path,
    source_sha256: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build read-only evidence for every stream attached to a block port.

    Observation lineage is deliberately namespaced and never writes into the
    canonical equipment input record. Inlet values may separately be adopted
    by the existing equipment-input logic; outlet observations remain visible
    without being silently substituted as the equipment's primary input.
    """

    observations: list[dict[str, Any]] = []
    observation_lineage: list[dict[str, Any]] = []
    ports = (
        ("inlet", list(block.get("inlet_streams", []))),
        ("outlet", list(block.get("outlet_streams", []))),
    )
    for port_role, stream_ids in ports:
        for port_index, stream_id_value in enumerate(stream_ids):
            stream_id = str(stream_id_value)
            stream = streams.get(stream_id)
            if not isinstance(stream, dict):
                continue
            sources = (
                stream.get("_sources", {})
                if isinstance(stream.get("_sources"), dict)
                else {}
            )
            field_observations: dict[str, dict[str, Any]] = {}
            item_lineage: list[dict[str, Any]] = []
            for field_id, unit in CONNECTED_STREAM_OBSERVATION_FIELDS:
                value = stream.get(field_id)
                if value in (None, ""):
                    continue
                source = (
                    dict(sources[field_id])
                    if isinstance(sources.get(field_id), dict)
                    else {}
                )
                source_field = str(source.get("source_field") or field_id)
                source_path = str(
                    source.get("source_path")
                    or f"stream:{stream_id}.{source_field}"
                )
                descriptor = {
                    "value": value,
                    "unit": unit,
                    "source_field": source_field,
                    "source_path": source_path,
                    "raw_value": source.get("raw_value", value),
                    "raw_unit": str(source.get("source_unit") or unit),
                    "transform": str(source.get("transform") or "identity"),
                    "origin": str(
                        source.get("origin")
                        or (
                            "ASPEN_EXTRACTED"
                            if str(source.get("transform") or "identity")
                            == "identity"
                            else "ASPEN_DERIVED"
                        )
                    ),
                    "evidence_class": str(
                        source.get("evidence_class")
                        or (
                            "R"
                            if str(source.get("transform") or "identity")
                            == "identity"
                            else "D"
                        )
                    ),
                    "result_status": str(
                        source.get("result_status")
                        or "OBSERVED_NOT_ADOPTED_AS_EQUIPMENT_MAIN_INPUT"
                    ),
                    "evidence_scope": str(
                        source.get("evidence_scope")
                        or "CONNECTED_STREAM_OBSERVATION_ONLY"
                    ),
                    "promotion_cap": str(
                        source.get("promotion_cap")
                        or "PROCESS_SIDE_OBSERVATION_ONLY"
                    ),
                    "warning_codes": list(source.get("warning_codes") or []),
                    "warning": source.get("warning"),
                    "read_only_observation": True,
                    "adopted_as_equipment_main_input": False,
                }
                field_observations[field_id] = descriptor
                observation_formula = str(
                    source.get("formula")
                    or f"Aspen_connected_stream.{source_field}"
                )
                observation_status = str(
                    source.get("result_status")
                    or "OBSERVED_NOT_ADOPTED_AS_EQUIPMENT_MAIN_INPUT"
                )
                observation_warning = str(
                    source.get("warning")
                    or (
                        "Read-only connected-stream evidence; the observation "
                        "package does not adopt this value as the equipment's "
                        "canonical main input."
                    )
                )
                item = lineage(
                    target_field=(
                        "connected_stream_observations."
                        f"{port_role}[{port_index}].{field_id}"
                    ),
                    value=value,
                    unit=unit,
                    source_file=source_file,
                    source_sha256=source_sha256,
                    object_type="connected_stream_observation",
                    object_id=stream_id,
                    source_field=source_field,
                    source_path=source_path,
                    transform="read_only_connected_stream_observation",
                    formula=observation_formula,
                    substitution=json.dumps(
                        {
                            "port_role": port_role,
                            "port_index": port_index,
                            "stream_id": stream_id,
                            "raw_value": source.get("raw_value", value),
                            "source_transform": source.get(
                                "transform", "identity"
                            ),
                        },
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                    evidence_class=str(
                        source.get("evidence_class")
                        or (
                            "R"
                            if str(source.get("transform") or "identity")
                            == "identity"
                            else "D"
                        )
                    ),
                    result_status=observation_status,
                    evidence_scope=str(
                        source.get("evidence_scope")
                        or "CONNECTED_STREAM_OBSERVATION_ONLY"
                    ),
                    promotion_cap=str(
                        source.get("promotion_cap")
                        or "PROCESS_SIDE_OBSERVATION_ONLY"
                    ),
                    warning=observation_warning,
                )
                item["port_role"] = port_role
                item["port_index"] = port_index
                item["read_only_observation"] = True
                item["adopted_as_equipment_main_input"] = False
                item["observation_adoption_status"] = (
                    "NOT_ADOPTED_AS_EQUIPMENT_MAIN_INPUT"
                )
                item["origin"] = descriptor["origin"]
                item["formal_design_evidence"] = bool(
                    source.get("formal_design_evidence", False)
                )
                for metadata_field in (
                    "warning_codes",
                    "result_sha256",
                    "source_bundle_sha256",
                    "formula_sources",
                    "mixing_rule",
                    "basis_conversion",
                    "diagnostic_sha256",
                ):
                    if source.get(metadata_field) not in (None, ""):
                        item[metadata_field] = source[metadata_field]
                item_lineage.append(item)

            composition = (
                list(stream.get("composition", []))
                if isinstance(stream.get("composition"), list)
                else []
            )
            if composition:
                composition_paths = {
                    str(item.get("component_id") or index): str(
                        item.get("source_path")
                        or f"stream:{stream_id}.composition.{index}"
                    )
                    for index, item in enumerate(composition)
                    if isinstance(item, dict)
                }
                field_observations["composition"] = {
                    "value": composition,
                    "basis": str(stream.get("composition_basis") or ""),
                    "source_paths": composition_paths,
                    "read_only_observation": True,
                    "adopted_as_equipment_main_input": False,
                }
                item = lineage(
                    target_field=(
                        "connected_stream_observations."
                        f"{port_role}[{port_index}].composition"
                    ),
                    value=composition,
                    unit="fraction",
                    source_file=source_file,
                    source_sha256=source_sha256,
                    object_type="connected_stream_observation",
                    object_id=stream_id,
                    source_field="composition",
                    source_path=json.dumps(
                        composition_paths,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    transform="read_only_closed_composition_vector_observation",
                    formula="Aspen_connected_stream.composition_vector",
                    substitution=json.dumps(
                        {
                            "port_role": port_role,
                            "port_index": port_index,
                            "stream_id": stream_id,
                            "basis": stream.get("composition_basis"),
                            "components": composition,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    evidence_class="D",
                    result_status=(
                        "OBSERVED_NOT_ADOPTED_AS_EQUIPMENT_MAIN_INPUT"
                    ),
                    evidence_scope="CONNECTED_STREAM_OBSERVATION_ONLY",
                    promotion_cap="PROCESS_SIDE_OBSERVATION_ONLY",
                    warning=(
                        "Read-only connected-stream composition evidence; it "
                        "does not replace the equipment's canonical main input."
                    ),
                )
                item["port_role"] = port_role
                item["port_index"] = port_index
                item["read_only_observation"] = True
                item["adopted_as_equipment_main_input"] = False
                item_lineage.append(item)

            flow_fields = {
                "volumetric_flow_m3_h",
                "liquid_volumetric_flow_m3_h",
                "vapor_volumetric_flow_m3_h",
                "mass_flow_kg_h",
            }
            viscosity_fields = {
                "dynamic_viscosity_mpa_s",
                "liquid_dynamic_viscosity_mpa_s",
                "vapor_dynamic_viscosity_mpa_s",
            }
            required_groups = {
                "phase": "phase" in field_observations,
                "temperature": "temperature_c" in field_observations,
                "pressure": "pressure_mpa" in field_observations,
                "flow": bool(flow_fields.intersection(field_observations)),
                "composition": "composition" in field_observations,
                "viscosity": bool(
                    viscosity_fields.intersection(field_observations)
                ),
            }
            observation = {
                "schema": "connected-stream-observation-v1",
                "block_id": str(block.get("block_id") or ""),
                "port_role": port_role,
                "port_index": port_index,
                "stream_id": stream_id,
                "read_only_observation": True,
                "adopted_as_equipment_main_input": False,
                "fields": dict(sorted(field_observations.items())),
                "required_group_coverage": required_groups,
                "missing_required_groups": sorted(
                    group
                    for group, present_group in required_groups.items()
                    if not present_group
                ),
                "source_file_path": str(source_file),
                "source_file_sha256": source_sha256,
            }
            observation["observation_sha256"] = _canonical_sha256(
                observation
            )
            observations.append(observation)
            observation_lineage.extend(item_lineage)
    return observations, observation_lineage


def build_heatx_side_mapping(
    *,
    block: dict[str, Any],
    streams: dict[str, dict[str, Any]],
    record: dict[str, Any],
    chain: list[dict[str, Any]],
    source_file: Path,
    source_sha256: str,
) -> dict[str, Any]:
    """Bind Aspen HEATX H/C port roles without assuming flow arrangement."""

    if str(block.get("block_type") or "").upper() != "HEATX":
        return {
            "schema": "aspen-heatx-side-mapping-v1",
            "status": "NOT_APPLICABLE",
            "formal_ready": False,
        }
    role_by_port = {
        "H(IN)": "hot_side_inlet",
        "H(OUT)": "hot_side_outlet",
        "C(IN)": "cold_side_inlet",
        "C(OUT)": "cold_side_outlet",
    }
    mapped: dict[str, dict[str, Any]] = {}
    issues: list[dict[str, Any]] = []
    for port_row in block.get("port_detail", []):
        if not isinstance(port_row, dict):
            continue
        port = str(port_row.get("port") or "").strip().upper()
        role = role_by_port.get(port)
        if role is None:
            continue
        stream_ids = list_value(port_row.get("streams"))
        if len(stream_ids) != 1:
            issues.append({
                "code": "HEATX_PORT_STREAM_CARDINALITY",
                "port": port,
                "required": 1,
                "actual": len(stream_ids),
            })
            continue
        stream_id = str(stream_ids[0])
        stream = streams.get(stream_id)
        if not isinstance(stream, dict):
            issues.append({
                "code": "HEATX_PORT_STREAM_NOT_FOUND",
                "port": port,
                "stream_id": stream_id,
            })
            continue
        side: dict[str, Any] = {
            "port": port,
            "stream_id": stream_id,
        }
        record[f"{role}_stream_id"] = stream_id
        chain.append(
            lineage(
                target_field=f"{role}_stream_id",
                value=stream_id,
                unit="-",
                source_file=source_file,
                source_sha256=source_sha256,
                object_type="block_port",
                object_id=str(block.get("block_id") or ""),
                source_field=f"port_detail.{port}.streams",
                source_path=(
                    f"block:{block.get('block_id')}.port_detail.{port}"
                ),
                transform="exact_aspen_HEATX_port_role_binding",
                formula=f"{role}=Aspen_port[{port}]",
                substitution=stream_id,
                evidence_class="D",
                result_status="DERIVED",
                evidence_scope="ASPEN_HEATX_PORT_TOPOLOGY",
                promotion_cap="PROCESS_SIDE_ONLY",
            )
        )
        source_map = (
            stream.get("_sources", {})
            if isinstance(stream.get("_sources"), dict)
            else {}
        )
        phase = matcher.canonical_phase(stream.get("phase"))
        if phase:
            phase_target = f"{role}_phase"
            phase_source = (
                dict(source_map.get("phase", {}))
                if isinstance(source_map.get("phase"), dict)
                else {}
            )
            add_direct(
                record,
                chain,
                phase_target,
                phase,
                "-",
                phase_source,
                source_file,
                source_sha256,
                "stream",
                stream_id,
            )
            side["phase"] = phase
        for source_field, suffix, unit in (
            ("temperature_c", "temperature_c", "C"),
            ("pressure_mpa", "pressure_mpa", "MPa"),
            ("mass_flow_kg_h", "mass_flow_kg_h", "kg/h"),
            ("volumetric_flow_m3_h", "volumetric_flow_m3_h", "m3/h"),
            ("dynamic_viscosity_mpa_s", "dynamic_viscosity_mpa_s", "mPa*s"),
        ):
            value = stream.get(source_field)
            if value is None:
                continue
            target = f"{role}_{suffix}"
            source = (
                dict(source_map.get(source_field, {}))
                if isinstance(source_map.get(source_field), dict)
                else {}
            )
            add_direct(
                record,
                chain,
                target,
                value,
                unit,
                source,
                source_file,
                source_sha256,
                "stream",
                stream_id,
            )
            side[suffix] = value
        mapped[role] = side

    required_roles = set(role_by_port.values())
    missing_roles = sorted(required_roles - set(mapped))
    if missing_roles:
        issues.append({
            "code": "HEATX_REQUIRED_PORT_ROLE_MISSING",
            "roles": missing_roles,
        })

    def positive_lmtd(delta_one: float, delta_two: float) -> float | None:
        if delta_one <= 0.0 or delta_two <= 0.0:
            return None
        if math.isclose(delta_one, delta_two, rel_tol=1.0e-12, abs_tol=1.0e-12):
            return delta_one
        return (delta_one - delta_two) / math.log(delta_one / delta_two)

    lmtd_candidates: dict[str, Any] = {
        "status": "NOT_CALCULABLE",
        "flow_arrangement_selected": False,
        "canonical_lmtd_selected": False,
        "candidates": {},
    }
    if not missing_roles and all(
        finite_number(mapped[role].get("temperature_c")) is not None
        for role in required_roles
    ):
        thi = float(mapped["hot_side_inlet"]["temperature_c"])
        tho = float(mapped["hot_side_outlet"]["temperature_c"])
        tci = float(mapped["cold_side_inlet"]["temperature_c"])
        tco = float(mapped["cold_side_outlet"]["temperature_c"])
        arrangements = {
            "countercurrent": (thi - tco, tho - tci),
            "cocurrent": (thi - tci, tho - tco),
        }
        candidates: dict[str, Any] = {}
        for arrangement, (delta_one, delta_two) in arrangements.items():
            candidates[arrangement] = {
                "terminal_delta_t_1_k": delta_one,
                "terminal_delta_t_2_k": delta_two,
                "lmtd_k": positive_lmtd(delta_one, delta_two),
                "physically_positive_terminal_differences": (
                    delta_one > 0.0 and delta_two > 0.0
                ),
            }
        lmtd_candidates = {
            "status": "ALTERNATIVE_FLOW_ARRANGEMENTS_CALCULATED",
            "flow_arrangement_selected": False,
            "canonical_lmtd_selected": False,
            "candidates": candidates,
            "warning": (
                "Aspen H/C port roles are mapped, but exchanger flow "
                "arrangement and correction factor are not established. "
                "Neither LMTD candidate is adopted as canonical."
            ),
        }
        invalid_arrangements = sorted(
            arrangement
            for arrangement, candidate in candidates.items()
            if not candidate["physically_positive_terminal_differences"]
        )
        lmtd_candidates["invalid_arrangements"] = invalid_arrangements
        lmtd_candidates["arrangement_restriction_status"] = (
            "OPEN_FLOW_ARRANGEMENT_RESTRICTION_GATE"
            if invalid_arrangements
            else "NO_TERMINAL_TEMPERATURE_RESTRICTION_DETECTED"
        )
        if invalid_arrangements:
            lmtd_candidates["warning"] += (
                " The following arrangements have a non-positive terminal "
                "temperature difference and are prohibited by this process "
                f"snapshot: {', '.join(invalid_arrangements)}."
            )

    pressure_drop_candidates: dict[str, Any] = {}
    for side_name in ("hot_side", "cold_side"):
        inlet_pressure = finite_number(
            mapped.get(f"{side_name}_inlet", {}).get("pressure_mpa")
        )
        outlet_pressure = finite_number(
            mapped.get(f"{side_name}_outlet", {}).get("pressure_mpa")
        )
        pressure_drop_kpa = (
            (inlet_pressure - outlet_pressure) * 1000.0
            if inlet_pressure is not None and outlet_pressure is not None
            else None
        )
        relative_drop = (
            pressure_drop_kpa / (inlet_pressure * 1000.0)
            if pressure_drop_kpa is not None
            and inlet_pressure is not None
            and inlet_pressure > 0.0
            else None
        )
        high_relative_drop = (
            relative_drop is not None and relative_drop >= 0.10
        )
        pressure_drop_candidates[side_name] = {
            "inlet_pressure_mpa": inlet_pressure,
            "outlet_pressure_mpa": outlet_pressure,
            "pressure_drop_kpa": pressure_drop_kpa,
            "pressure_drop_ratio_to_inlet_pressure": relative_drop,
            "project_high_relative_drop_screening_threshold": 0.10,
            "project_threshold_is_not_code_acceptance_limit": True,
            "allowable_pressure_drop_confirmed": False,
            "review_required": high_relative_drop,
            "status": (
                "HIGH_RELATIVE_PROCESS_PRESSURE_DROP_REVIEW_REQUIRED"
                if high_relative_drop
                else "DERIVED_PROCESS_PRESSURE_DROP"
                if inlet_pressure is not None
                and outlet_pressure is not None
                and inlet_pressure >= outlet_pressure
                else "UNAVAILABLE_OR_PHYSICALLY_INCONSISTENT"
            ),
        }

    result = {
        "schema": "aspen-heatx-side-mapping-v1",
        "status": (
            "EXPLICIT_ASPEN_PORT_ROLE_MAPPING_COMPLETE"
            if not issues
            else "PARTIAL_OR_BLOCKED_PORT_ROLE_MAPPING"
        ),
        "block_id": str(block.get("block_id") or ""),
        "mapped_roles": mapped,
        "missing_roles": missing_roles,
        "issues": issues,
        "lmtd_candidates": lmtd_candidates,
        "pressure_drop_candidates": pressure_drop_candidates,
        "phase_transition_snapshot": {
            "hot_side": (
                f"{mapped.get('hot_side_inlet', {}).get('phase', 'unknown')}"
                f"->{mapped.get('hot_side_outlet', {}).get('phase', 'unknown')}"
            ),
            "cold_side": (
                f"{mapped.get('cold_side_inlet', {}).get('phase', 'unknown')}"
                f"->{mapped.get('cold_side_outlet', {}).get('phase', 'unknown')}"
            ),
        },
        "formal_ready": False,
        "formal_open_gates": [
            "flow_arrangement_and_pass_configuration",
            "canonical_LMTD_and_F_factor",
            "hot_and_cold_side_allowable_pressure_drop",
            "fouling_resistances",
            "phase_change_zoning_if_applicable",
            "thermal_expansion_and_cleanability",
            "same_equipment_thermal_rating_or_EDR_evidence",
            "mechanical_design_and_vendor_datasheet",
        ],
    }
    result["mapping_sha256"] = _canonical_sha256(result)
    return result


def classify_heat_transfer_service(
    *,
    block_type: str,
    inlets: list[dict[str, Any]],
    outlets: list[dict[str, Any]],
    heatx_side_mapping: dict[str, Any],
    pressure_basis: str = "absolute",
    atmospheric_pressure_mpa: float = 0.101325,
) -> dict[str, Any]:
    """Select a concrete preliminary exchanger form from phase transitions.

    This classifier deliberately stops at equipment-form screening.  Aspen
    stream phases establish process service, but they do not establish the
    exchanger arrangement, passes, area, metallurgy, mechanical design or a
    vendor model.
    """

    canonical_block_type = str(block_type or "").upper()
    if canonical_block_type not in {"HEATER", "HEATX"}:
        return {
            "schema": "heat-transfer-service-classification-v1",
            "status": "NOT_APPLICABLE",
            "formal_ready": False,
        }

    def stream_phase(stream: dict[str, Any] | None) -> str:
        if not isinstance(stream, dict):
            return "unknown"
        return matcher.canonical_phase(stream.get("phase")) or "unknown"

    def transition_kind(phase_in: str, phase_out: str) -> str:
        if phase_in == "vapor" and phase_out == "liquid":
            return "full_condensation"
        if phase_in == "vapor" and phase_out == "mixed":
            return "partial_condensation"
        if phase_in == "mixed" and phase_out == "liquid":
            return "condensation_completion"
        if phase_in == "liquid" and phase_out == "vapor":
            return "full_vaporization"
        if phase_in == "liquid" and phase_out == "mixed":
            return "partial_vaporization"
        if phase_in == "mixed" and phase_out == "vapor":
            return "vaporization_completion_or_superheat"
        if phase_in == phase_out and phase_in in {"liquid", "vapor"}:
            return "single_phase_sensible"
        if "unknown" in {phase_in, phase_out}:
            return "unknown"
        return "other_or_multiphase"

    classification: dict[str, Any] = {
        "schema": "heat-transfer-service-classification-v1",
        "status": "OPEN_PHASE_SERVICE_CLASSIFICATION",
        "block_type": canonical_block_type,
        "recommended_type": None,
        "selector_rule_id": None,
        "phase_transitions": {},
        "evidence_class": "J",
        "result_status": "PROVISIONAL_PHASE_SERVICE_TYPE_SCREENING",
        "promotion_cap": "TYPE_SCREENING",
        "formal_ready": False,
        "formal_open_gates": [
            "utility_or_second_process_side_definition",
            "flow_arrangement_and_pass_configuration",
            "canonical_LMTD_and_F_factor",
            "allowable_pressure_drop_for_each_side",
            "heat_transfer_area_and_fouling_resistances",
            "phase_change_zoning_and_heat_flux_if_applicable",
            "thermal_expansion_cleanability_and_drainability",
            "materials_corrosion_and_mechanical_design",
            "same_equipment_thermal_rating_or_EDR_evidence",
            "vendor_datasheet_and_selected_model",
        ],
        "warning": (
            "程序只依据 Aspen 端口拓扑与进出口相态选择具体的初步设备型式；"
            "它不是热工定型、机械设计或厂家型号。"
        ),
    }

    if canonical_block_type == "HEATER":
        phase_in = stream_phase(inlets[0] if len(inlets) == 1 else None)
        phase_out = stream_phase(outlets[0] if len(outlets) == 1 else None)
        transition = transition_kind(phase_in, phase_out)
        classification["phase_transitions"] = {
            "process_side": {
                "inlet_phase": phase_in,
                "outlet_phase": phase_out,
                "transition_kind": transition,
            }
        }
        heater_type_by_transition = {
            "full_condensation": (
                "单流程卧式管壳式全冷凝器",
                "HEATER_PROCESS_VAPOR_TO_LIQUID_FULL_CONDENSER",
            ),
            "partial_condensation": (
                "单流程卧式管壳式部分冷凝器",
                "HEATER_PROCESS_VAPOR_TO_MIXED_PARTIAL_CONDENSER",
            ),
            "condensation_completion": (
                "单流程卧式管壳式冷凝终冷器",
                "HEATER_PROCESS_MIXED_TO_LIQUID_CONDENSATION_COMPLETION",
            ),
            "full_vaporization": (
                "单流程卧式管壳式工艺汽化器",
                "HEATER_PROCESS_LIQUID_TO_VAPOR_VAPORIZER",
            ),
            "partial_vaporization": (
                "单流程卧式管壳式部分汽化器",
                "HEATER_PROCESS_LIQUID_TO_MIXED_PARTIAL_VAPORIZER",
            ),
            "vaporization_completion_or_superheat": (
                "单流程卧式管壳式汽化终端兼过热器",
                "HEATER_PROCESS_MIXED_TO_VAPOR_VAPORIZATION_SUPERHEAT",
            ),
            "single_phase_sensible": (
                (
                    "单流程卧式管壳式液相显热换热器"
                    if phase_in == "liquid"
                    else "单流程卧式管壳式气相显热换热器"
                    if phase_in == "vapor"
                    else "单流程卧式管壳式显热换热器"
                ),
                "HEATER_SINGLE_PHASE_SENSIBLE_SERVICE",
            ),
        }
        selected = heater_type_by_transition.get(transition)
        if selected is not None:
            classification["recommended_type"], classification[
                "selector_rule_id"
            ] = selected
            classification["status"] = (
                "PRELIMINARY_PHASE_SERVICE_TYPE_SELECTED"
            )
        inlet_pressure = finite_number(
            inlets[0].get("pressure_mpa")
            if len(inlets) == 1
            else None
        )
        outlet_pressure = finite_number(
            outlets[0].get("pressure_mpa")
            if len(outlets) == 1
            else None
        )
        inlet_absolute = inlet_pressure
        if (
            inlet_absolute is not None
            and str(pressure_basis).casefold() == "gauge"
        ):
            inlet_absolute += atmospheric_pressure_mpa
        pressure_drop_kpa = (
            (inlet_pressure - outlet_pressure) * 1000.0
            if inlet_pressure is not None
            and outlet_pressure is not None
            else None
        )
        ratio_to_inlet_absolute = (
            pressure_drop_kpa / (inlet_absolute * 1000.0)
            if pressure_drop_kpa is not None
            and inlet_absolute is not None
            and inlet_absolute > 0.0
            else None
        )
        if pressure_drop_kpa is None or ratio_to_inlet_absolute is None:
            pressure_drop_status = (
                "OPEN_MISSING_HEATER_ENDPOINT_PRESSURE"
            )
            review_required = True
            function_conflict = False
        elif pressure_drop_kpa < -1.0e-6:
            pressure_drop_status = (
                "BLOCKED_HEATER_PRESSURE_RISE_REQUIRES_SEPARATE_DEVICE"
            )
            review_required = True
            function_conflict = True
        elif ratio_to_inlet_absolute >= 0.30:
            pressure_drop_status = (
                "BLOCKED_HEAT_TRANSFER_PRESSURE_DROP_FUNCTION_CONFLICT"
            )
            review_required = True
            function_conflict = True
        elif ratio_to_inlet_absolute >= 0.10:
            pressure_drop_status = (
                "REVIEW_HIGH_RELATIVE_HEATER_PRESSURE_DROP"
            )
            review_required = True
            function_conflict = False
        else:
            pressure_drop_status = (
                "PASS_PROJECT_PRE_SCREEN_BELOW_REVIEW_THRESHOLD"
            )
            review_required = False
            function_conflict = False
        classification["pressure_drop_screening"] = {
            "schema": "heater-pressure-drop-screening-v1",
            "inlet_pressure_mpa": inlet_pressure,
            "outlet_pressure_mpa": outlet_pressure,
            "inlet_pressure_mpa_absolute": inlet_absolute,
            "pressure_basis": pressure_basis,
            "pressure_drop_kpa": pressure_drop_kpa,
            "ratio_to_inlet_absolute": ratio_to_inlet_absolute,
            "review_ratio_threshold": 0.10,
            "function_conflict_ratio_threshold": 0.30,
            "threshold_role": (
                "PROJECT_PRE_SCREEN_NOT_NATIONAL_CODE_ALLOWABLE_LIMIT"
            ),
            "review_required": review_required,
            "function_conflict": function_conflict,
            "status": pressure_drop_status,
            "formal_allowable_confirmed": False,
        }
        if review_required:
            classification["formal_open_gates"].append(
                "heater_allowable_process_pressure_drop"
            )
        if function_conflict:
            classification["formal_open_gates"].extend([
                "dedicated_pressure_reduction_device_or_process_data_correction",
                "heat_transfer_and_pressure_reduction_function_allocation_review",
            ])

    if canonical_block_type == "HEATX":
        mapped = (
            heatx_side_mapping.get("mapped_roles", {})
            if isinstance(heatx_side_mapping, dict)
            else {}
        )
        hot_in = str(
            mapped.get("hot_side_inlet", {}).get("phase") or "unknown"
        )
        hot_out = str(
            mapped.get("hot_side_outlet", {}).get("phase") or "unknown"
        )
        cold_in = str(
            mapped.get("cold_side_inlet", {}).get("phase") or "unknown"
        )
        cold_out = str(
            mapped.get("cold_side_outlet", {}).get("phase") or "unknown"
        )
        hot_transition = transition_kind(hot_in, hot_out)
        cold_transition = transition_kind(cold_in, cold_out)
        classification["phase_transitions"] = {
            "hot_side": {
                "inlet_phase": hot_in,
                "outlet_phase": hot_out,
                "transition_kind": hot_transition,
            },
            "cold_side": {
                "inlet_phase": cold_in,
                "outlet_phase": cold_out,
                "transition_kind": cold_transition,
            },
        }
        condensing = hot_transition in {
            "full_condensation",
            "partial_condensation",
            "condensation_completion",
        }
        boiling = cold_transition in {
            "full_vaporization",
            "partial_vaporization",
            "vaporization_completion_or_superheat",
        }
        if condensing and boiling:
            selected = (
                "冷凝-沸腾耦合卧式管壳换热器",
                "HEATX_HOT_CONDENSING_COLD_BOILING_COUPLED",
            )
        elif condensing:
            selected = (
                "卧式管壳式工艺冷凝器",
                "HEATX_HOT_SIDE_CONDENSING",
            )
        elif boiling:
            selected = (
                "卧式管壳式工艺汽化器",
                "HEATX_COLD_SIDE_BOILING",
            )
        elif (
            hot_transition == "single_phase_sensible"
            and cold_transition == "single_phase_sensible"
        ):
            if {
                hot_in,
                hot_out,
                cold_in,
                cold_out,
            } == {"liquid"}:
                sensible_type = "卧式管壳式液-液显热流程换热器"
            elif {
                hot_in,
                hot_out,
                cold_in,
                cold_out,
            } == {"vapor"}:
                sensible_type = "卧式管壳式气-气显热流程换热器"
            else:
                sensible_type = "卧式管壳式液-气显热流程换热器"
            selected = (
                sensible_type,
                "HEATX_TWO_SIDE_SINGLE_PHASE_SENSIBLE",
            )
        else:
            selected = None
        if selected is not None:
            classification["recommended_type"], classification[
                "selector_rule_id"
            ] = selected
            classification["status"] = (
                "PRELIMINARY_PHASE_SERVICE_TYPE_SELECTED"
            )

        lmtd = (
            heatx_side_mapping.get("lmtd_candidates", {})
            if isinstance(heatx_side_mapping, dict)
            else {}
        )
        invalid_arrangements = [
            str(value)
            for value in lmtd.get("invalid_arrangements", [])
        ]
        if invalid_arrangements:
            classification["formal_open_gates"].append(
                "prohibited_flow_arrangements:"
                + ",".join(sorted(invalid_arrangements))
            )
        pressure_drop = (
            heatx_side_mapping.get("pressure_drop_candidates", {})
            if isinstance(heatx_side_mapping, dict)
            else {}
        )
        for side_name, row in pressure_drop.items():
            if isinstance(row, dict) and row.get("review_required") is True:
                classification["formal_open_gates"].append(
                    f"{side_name}_high_relative_process_pressure_drop_review"
                )

    classification["formal_open_gates"] = sorted(set(
        classification["formal_open_gates"]
    ))
    classification["classification_sha256"] = _canonical_sha256(
        classification
    )
    return classification


def apply_heat_transfer_service_model_gate(
    match_result: dict[str, Any],
    classification: dict[str, Any],
) -> None:
    """Publish the concrete service type without promoting it to a design."""

    if (
        classification.get("status")
        != "PRELIMINARY_PHASE_SERVICE_TYPE_SELECTED"
    ):
        return
    recommended_type = str(classification.get("recommended_type") or "")
    pressure_drop_screening = (
        classification.get("pressure_drop_screening", {})
        if isinstance(
            classification.get("pressure_drop_screening"), dict
        )
        else {}
    )
    function_conflict = bool(
        pressure_drop_screening.get("function_conflict")
    )
    boundary_id = (
        "heat_transfer_phase_service:"
        + str(classification.get("selector_rule_id") or "UNCLASSIFIED")
        + (
            ":PRESSURE_DROP_FUNCTION_CONFLICT"
            if function_conflict
            else ""
        )
    )
    terminal_selection = {
        "status": "PROGRAMMATIC_PHASE_SERVICE_TYPE_SELECTED",
        "recommended_type": recommended_type,
        "selection_basis": "aspen_port_topology_and_phase_transition_rule",
        "default_applied": False,
        "evidence_class": "J",
        "provisional": True,
        "rule_id": str(classification.get("selector_rule_id") or ""),
        "assumption": classification.get("warning"),
        "terminal_scope": "equipment_form_only",
        "formal_model": False,
        "is_vendor_model": False,
        "classification_sha256": classification.get(
            "classification_sha256"
        ),
    }
    apply_model_screening_boundary(
        match_result,
        boundary_id=boundary_id,
        model_status=(
            "HEAT_TRANSFER_TYPE_RETAINED_PRESSURE_DROP_FUNCTION_CONFLICT"
            if function_conflict
            else (
                "HEAT_TRANSFER_SERVICE_TYPE_SELECTED_"
                "THERMAL_MECHANICAL_DESIGN_BLOCKED"
            )
        ),
        candidate_status=(
            "PRELIMINARY_TYPE_IDENTITY_PRESSURE_DROP_CONFLICT"
            if function_conflict
            else "PRELIMINARY_PHASE_SERVICE_TYPE_SELECTED"
        ),
        candidate_eligibility=(
            "TYPE_IDENTITY_ONLY_PRESSURE_DROP_FUNCTION_CONFLICT"
            if function_conflict
            else "TYPE_IDENTITY_ONLY_PHASE_SERVICE_SCREENING"
        ),
        missing_gates=list(classification.get("formal_open_gates") or []),
        execution_status=(
            "TYPE_SELECTED_THERMAL_AND_MECHANICAL_DESIGN_BLOCKED"
        ),
        execution_scope="HEAT_TRANSFER_EQUIPMENT_FORM_SCREENING_ONLY",
        recommended_type=recommended_type,
        terminal_selection=terminal_selection,
        warning=str(classification.get("warning") or ""),
    )
    synchronize_model_boundary_projection(
        match_result,
        boundary_id=boundary_id,
    )


def _calculation_by_id(
    match_result: dict[str, Any],
    calculation_id: str,
) -> dict[str, Any] | None:
    return next(
        (
            row
            for row in match_result.get("calculations", [])
            if isinstance(row, dict)
            and str(row.get("calculation_id") or "") == calculation_id
        ),
        None,
    )


def _fallback_by_field(
    match_result: dict[str, Any],
    field_id: str,
) -> dict[str, Any] | None:
    return next(
        (
            row
            for row in match_result.get("design_fallbacks", [])
            if isinstance(row, dict)
            and str(row.get("field_id") or "") == field_id
        ),
        None,
    )


def build_tower_preliminary_design_audit(
    *,
    record: dict[str, Any],
    chain: list[dict[str, Any]],
    match_result: dict[str, Any],
    source_file: Path,
    source_sha256: str,
) -> dict[str, Any]:
    """Separate tower traffic/strength screening values from selected sizes."""

    block_type = str(record.get("aspen_block_type") or "").upper()
    if block_type not in TOWER_BLOCK_TYPES:
        return {
            "schema": "tower-preliminary-design-audit-v1",
            "status": "NOT_APPLICABLE",
            "formal_ready": False,
        }

    derived = (
        match_result.get("derived_parameters", {})
        if isinstance(match_result.get("derived_parameters"), dict)
        else {}
    )
    diameter_calc = _calculation_by_id(
        match_result, "tower_preliminary_diameter"
    )
    height_calc = _calculation_by_id(
        match_result, "tower_preliminary_height"
    )
    spacing_calc = _calculation_by_id(
        match_result, "tower_tray_spacing"
    )
    shell_calc = _calculation_by_id(
        match_result, "cylinder_thickness"
    )
    head_calc = _calculation_by_id(match_result, "head_thickness")
    velocity_fallback = _fallback_by_field(
        match_result, "tower_design_velocity_m_s"
    )
    diameter_fallback = _fallback_by_field(
        match_result, "inner_diameter_mm"
    )
    allowance_fallback = _fallback_by_field(
        match_result, "tower_top_bottom_allowance_mm"
    )

    diameter_mm = finite_number(derived.get("inner_diameter_mm"))
    if diameter_calc is not None:
        unrounded_mm = finite_number(
            diameter_calc.get("unrounded_diameter_mm")
        )
        diameter_basis = (
            "INLET_LIQUID_TRAFFIC_SURROGATE_NOT_CONTROLLING_TRAY_SECTION"
            if matcher.canonical_phase(record.get("phase")) == "liquid"
            else "CONNECTED_INLET_TRAFFIC_SURROGATE_NOT_FLOODING_CAPACITY"
        )
        diameter_formula = (
            diameter_calc.get("formula_chain", {}).get("formula")
            if isinstance(diameter_calc.get("formula_chain"), dict)
            else None
        )
        minimum_floor_applied = bool(
            diameter_mm is not None
            and unrounded_mm is not None
            and math.isclose(diameter_mm, 600.0, abs_tol=1.0e-9)
            and unrounded_mm < 600.0
        )
    elif diameter_fallback is not None:
        diameter_mm = finite_number(diameter_fallback.get("value"))
        unrounded_mm = None
        diameter_basis = (
            "REGISTERED_600_MM_MINIMUM_WITHOUT_TRAFFIC_FLOW"
        )
        diameter_formula = None
        minimum_floor_applied = True
    elif finite_number(record.get("inner_diameter_mm")) is not None:
        diameter_mm = finite_number(record.get("inner_diameter_mm"))
        unrounded_mm = None
        diameter_basis = (
            "ASPEN_REPORTED_INTERNAL_DIAMETER_NOT_HYDRAULICALLY_VERIFIED"
        )
        diameter_formula = None
        minimum_floor_applied = False
    else:
        unrounded_mm = None
        diameter_basis = "OPEN_NO_DIAMETER_SCREENING_VALUE"
        diameter_formula = None
        minimum_floor_applied = False

    stage_count = finite_number(record.get("stage_count"))
    height_mm = (
        finite_number(height_calc.get("value"))
        if height_calc is not None
        else finite_number(derived.get("height_mm"))
    )
    tray_spacing_mm = (
        finite_number(spacing_calc.get("value"))
        if spacing_calc is not None
        else finite_number(derived.get("tray_spacing_mm"))
    )
    top_bottom_allowance_mm = (
        finite_number(allowance_fallback.get("value"))
        if allowance_fallback is not None
        else None
    )

    audit = {
        "schema": "tower-preliminary-design-audit-v1",
        "status": "TYPE_SELECTED_HYDRAULIC_SIZING_BLOCKED",
        "recommended_type": "单溢流筛板塔",
        "diameter_screening": {
            "value_mm": diameter_mm,
            "unrounded_formula_value_mm": unrounded_mm,
            "basis": diameter_basis,
            "formula": diameter_formula,
            "traffic_flow_m3_h": finite_number(record.get("flow_m3_h")),
            "traffic_phase": (
                matcher.canonical_phase(record.get("phase")) or "unknown"
            ),
            "assumed_screening_velocity_m_s": (
                finite_number(velocity_fallback.get("value"))
                if velocity_fallback is not None
                else None
            ),
            "minimum_600_mm_floor_applied": minimum_floor_applied,
            "controlling_tray_section_selected": False,
            "flooding_capacity_verified": False,
            "claim": "DIAMETER_SCREENING_VALUE_ONLY",
            "evidence_class": "J",
            "promotion_cap": "TYPE_SCREENING",
        },
        "height_screening": {
            "value_mm": height_mm,
            "stage_count": stage_count,
            "tray_spacing_screening_mm": tray_spacing_mm,
            "registered_top_bottom_allowance_mm": (
                top_bottom_allowance_mm
            ),
            "basis": (
                "STAGE_INTERVALS_PLUS_REGISTERED_ALLOWANCE"
                if height_calc is not None
                else "OPEN_OR_FALLBACK_LAYOUT_VALUE"
            ),
            "final_tower_height_selected": False,
            "evidence_class": "J",
            "promotion_cap": "TYPE_SCREENING",
        },
        "mechanical_thickness_screening": {
            "shell_formula_thickness_mm": (
                finite_number(shell_calc.get("value"))
                if shell_calc is not None
                else None
            ),
            "head_formula_thickness_mm": (
                finite_number(head_calc.get("value"))
                if head_calc is not None
                else None
            ),
            "formula_value_includes_corrosion_allowance": False,
            "formula_value_includes_negative_tolerance": False,
            "formula_value_includes_minimum_fabrication_thickness": False,
            "external_pressure_checked": False,
            "loads_and_openings_checked": False,
            "nominal_shell_thickness_selected": False,
            "nominal_head_thickness_selected": False,
            "claim": "FORMULA_THICKNESS_ONLY_NOT_NOMINAL_THICKNESS",
            "evidence_class": "J",
            "promotion_cap": "TYPE_SCREENING",
        },
        "formal_ready": False,
        "formal_open_gates": [
            "controlling_stage_vapor_and_liquid_loads",
            "vapor_liquid_properties_at_controlling_stages",
            "flooding_capacity_and_design_flood_fraction",
            "entrainment_weeping_and_downcomer_backup",
            "tray_pressure_drop_and_operating_range",
            "feed_and_draw_stage_hydraulics",
            "tray_or_packing_internals_rating",
            "top_bottom_disengagement_and_nozzle_layout",
            "wind_seismic_support_and_platform_loads",
            "internal_and_external_pressure_cases",
            "materials_corrosion_allowance_and_MDMT",
            "weld_joint_efficiency_and_nondestructive_examination",
            "nominal_shell_head_and_nozzle_thickness_selection",
            "mechanical_code_calculation_and_fabrication_drawing",
        ],
        "warning": (
            "塔型为程序初选；当前直径最多是入口流量代理值或 600 mm "
            "保底值，不是控制塔板段的泛点水力学结果。壳体/封头厚度仅为"
            "公式计算厚度，不是名义厚度。"
        ),
        "source_binding": {
            "aspen_export_path": str(source_file),
            "aspen_export_sha256": source_sha256,
        },
        "deterministic": True,
        "llm_used": False,
    }
    audit["audit_sha256"] = _canonical_sha256(audit)

    projected_fields = {
        "tower_diameter_screening_mm": (
            diameter_mm,
            "mm",
            "Di_screen",
        ),
        "tower_height_screening_mm": (
            height_mm,
            "mm",
            "H_layout_screen",
        ),
        "formula_only_shell_thickness_mm": (
            audit["mechanical_thickness_screening"][
                "shell_formula_thickness_mm"
            ],
            "mm",
            "t_shell_formula_only",
        ),
        "formula_only_head_thickness_mm": (
            audit["mechanical_thickness_screening"][
                "head_formula_thickness_mm"
            ],
            "mm",
            "t_head_formula_only",
        ),
        "nominal_shell_wall_thickness_selected": (
            False,
            "-",
            "formal_nominal_shell_thickness_selection",
        ),
        "nominal_head_wall_thickness_selected": (
            False,
            "-",
            "formal_nominal_head_thickness_selection",
        ),
    }
    for field_id, (value, unit, formula) in projected_fields.items():
        if value is None:
            continue
        record[field_id] = value
        chain.append(
            lineage(
                target_field=field_id,
                value=value,
                unit=unit,
                source_file=source_file,
                source_sha256=source_sha256,
                object_type="tower_preliminary_design_audit",
                object_id=str(record.get("equipment_tag") or ""),
                source_field=(
                    "tower_preliminary_design_audit."
                    + field_id
                ),
                source_path=(
                    "tower_preliminary_design_audit:"
                    + audit["audit_sha256"]
                ),
                transform="explicit_screening_role_projection",
                formula=formula,
                substitution=str(value),
                evidence_class="J",
                result_status="PROVISIONAL_TYPE_SCREENING",
                evidence_scope="TOWER_SCREENING_ONLY",
                promotion_cap="TYPE_SCREENING",
                warning=audit["warning"],
            )
        )

    terminal_selection = {
        "status": "PROGRAMMATIC_TOWER_FORM_SELECTED",
        "recommended_type": audit["recommended_type"],
        "selection_basis": "registered_preliminary_tray_tower_rule",
        "default_applied": True,
        "evidence_class": "J",
        "provisional": True,
        "rule_id": "tower:programmatic:single_pass_sieve_tray_screen",
        "assumption": audit["warning"],
        "terminal_scope": "equipment_form_only",
        "formal_model": False,
        "is_vendor_model": False,
        "audit_sha256": audit["audit_sha256"],
    }
    apply_model_screening_boundary(
        match_result,
        boundary_id="tower_hydraulic_and_mechanical_open",
        model_status="TOWER_TYPE_SELECTED_HYDRAULIC_SIZING_BLOCKED",
        candidate_status="PRELIMINARY_TOWER_FORM_SELECTED",
        candidate_eligibility="TYPE_IDENTITY_ONLY_TOWER_HYDRAULICS_OPEN",
        missing_gates=audit["formal_open_gates"],
        execution_status="TYPE_SELECTED_TOWER_SIZING_BLOCKED",
        execution_scope="TOWER_FORM_SCREENING_ONLY",
        recommended_type=audit["recommended_type"],
        terminal_selection=terminal_selection,
        warning=audit["warning"],
    )
    model = (
        match_result.get("model_recommendation", {})
        if isinstance(match_result.get("model_recommendation"), dict)
        else {}
    )
    designation = (
        f"{audit['recommended_type']}（程序初选；水力学未闭合）"
        f" | Di_screen={diameter_mm if diameter_mm is not None else 'OPEN'} mm"
        f" | H_layout_screen={height_mm if height_mm is not None else 'OPEN'} mm"
        f" | N_stage={stage_count if stage_count is not None else 'OPEN'}"
        " | shell_formula_t="
        f"{audit['mechanical_thickness_screening']['shell_formula_thickness_mm']}"
        " mm (NOT nominal)"
        " | nominal_shell/head_thickness=OPEN"
    )
    # Public model identity must not repeat generic geometry screens.  Those
    # values remain available only in ``tower_preliminary_design_audit``.
    designation = (
        f"{audit['recommended_type']}（程序设备型式初选；塔内件水力学未闭合）"
        f" | N_stage_Aspen={stage_count if stage_count is not None else 'OPEN'}"
        " | Di_formal=OPEN"
        " | H_formal=OPEN"
        " | nominal_shell/head_thickness=OPEN"
        " | screening_detail_ref=tower_preliminary_design_audit:"
        f"{audit['audit_sha256'][:16]}"
    )
    candidates = [
        item
        for item in model.get("candidates", [])
        if isinstance(item, dict)
    ]
    leading = model.get("leading_candidate")
    if isinstance(leading, dict):
        candidates.append(leading)
    seen: set[int] = set()
    for candidate in candidates:
        if id(candidate) in seen:
            continue
        seen.add(id(candidate))
        if not str(candidate.get("status") or "").startswith("REJECTED_"):
            candidate["designation"] = designation
            candidate["tower_preliminary_design_audit_sha256"] = audit[
                "audit_sha256"
            ]
            specification = candidate.get("specification")
            if isinstance(specification, dict):
                # Generic matcher fallbacks such as 600 mm and a stage-count
                # layout height must never survive on the public model
                # specification surface.  The values remain available only in
                # ``tower_preliminary_design_audit`` under explicitly named
                # screening fields.
                specification.pop("inner_diameter_mm", None)
                specification.pop("height_mm", None)
                specification.update({
                    "formal_tower_diameter_status": (
                        "OPEN_CONTROLLING_SECTION_HYDRAULICS"
                    ),
                    "formal_tower_height_status": (
                        "OPEN_INTERNALS_AND_MECHANICAL_LAYOUT"
                    ),
                    "tower_preliminary_design_audit_sha256": audit[
                        "audit_sha256"
                    ],
                })
    derived_parameters = (
        match_result.get("derived_parameters", {})
        if isinstance(match_result.get("derived_parameters"), dict)
        else {}
    )
    if derived_parameters:
        pre_boundary_geometry = {
            field_id: derived_parameters.pop(field_id)
            for field_id in ("inner_diameter_mm", "height_mm")
            if field_id in derived_parameters
        }
        if pre_boundary_geometry:
            derived_parameters[
                "pre_boundary_generic_tower_geometry"
            ] = {
                **pre_boundary_geometry,
                "role": "SUPERSEDED_BY_EXPLICIT_SCREENING_FIELDS",
                "not_for_customer_or_formal_use": True,
            }
        if diameter_mm is not None:
            derived_parameters[
                "tower_diameter_screening_mm"
            ] = diameter_mm
        if height_mm is not None:
            derived_parameters[
                "tower_height_screening_mm"
            ] = height_mm
    synchronize_model_boundary_projection(
        match_result,
        boundary_id="tower_hydraulic_and_mechanical_open",
    )
    return audit


def build_rplug_preliminary_design_audit(
    *,
    block: dict[str, Any],
    streams: dict[str, dict[str, Any]],
    record: dict[str, Any],
    chain: list[dict[str, Any]],
    match_result: dict[str, Any],
    source_file: Path,
    source_sha256: str,
) -> dict[str, Any]:
    """Describe Aspen RPLUG geometry as one active-tube screen only."""

    if str(block.get("block_type") or "").upper() != "RPLUG":
        return {
            "schema": "rplug-preliminary-design-audit-v1",
            "status": "NOT_APPLICABLE",
            "formal_ready": False,
        }
    role_by_port = {
        "F(IN)": "process_inlet",
        "P(OUT)": "process_outlet",
        "C(IN)": "coolant_inlet",
        "C(OUT)": "coolant_outlet",
    }
    roles: dict[str, Any] = {}
    issues: list[dict[str, Any]] = []
    for port_row in block.get("port_detail", []):
        if not isinstance(port_row, dict):
            continue
        port = str(port_row.get("port") or "").strip().upper()
        role = role_by_port.get(port)
        if role is None:
            continue
        stream_ids = list_value(port_row.get("streams"))
        if len(stream_ids) != 1 or stream_ids[0] not in streams:
            issues.append({
                "code": "RPLUG_PORT_MAPPING_INCOMPLETE",
                "port": port,
                "stream_ids": stream_ids,
            })
            continue
        stream = streams[str(stream_ids[0])]
        composition = (
            stream.get("composition", [])
            if isinstance(stream.get("composition"), list)
            else []
        )
        water_fraction = sum(
            finite_number(item.get("fraction")) or 0.0
            for item in composition
            if isinstance(item, dict)
            and str(item.get("component_id") or "").upper()
            in {"H2O", "WATER"}
        )
        roles[role] = {
            "port": port,
            "stream_id": str(stream_ids[0]),
            "phase": (
                matcher.canonical_phase(stream.get("phase")) or "unknown"
            ),
            "temperature_c": finite_number(stream.get("temperature_c")),
            "pressure_mpa": finite_number(stream.get("pressure_mpa")),
            "mass_flow_kg_h": finite_number(stream.get("mass_flow_kg_h")),
            "volumetric_flow_m3_h": finite_number(
                stream.get("volumetric_flow_m3_h")
            ),
            "water_fraction": water_fraction or None,
        }
    missing_roles = sorted(set(role_by_port.values()) - set(roles))
    if missing_roles:
        issues.append({
            "code": "RPLUG_REQUIRED_PORT_ROLE_MISSING",
            "roles": missing_roles,
        })
    coolant_transition = (
        str(roles.get("coolant_inlet", {}).get("phase") or "unknown")
        + "->"
        + str(roles.get("coolant_outlet", {}).get("phase") or "unknown")
    )
    boiling_water_heat_removal = coolant_transition == "liquid->vapor"
    coolant_outlet = roles.get("coolant_outlet", {})
    coolant_pressure_mpa = finite_number(
        coolant_outlet.get("pressure_mpa")
    )
    coolant_pressure_absolute_mpa = coolant_pressure_mpa
    if (
        coolant_pressure_absolute_mpa is not None
        and str(record.get("pressure_basis") or "").casefold() == "gauge"
    ):
        coolant_pressure_absolute_mpa += (
            finite_number(record.get("atmospheric_pressure_mpa"))
            or 0.101325
        )
    coolant_outlet_temperature_c = finite_number(
        coolant_outlet.get("temperature_c")
    )
    coolant_water_fraction = finite_number(
        coolant_outlet.get("water_fraction")
    )
    water_saturation_temperature_c: float | None = None
    if (
        boiling_water_heat_removal
        and coolant_water_fraction is not None
        and coolant_water_fraction >= 0.95
        and coolant_pressure_absolute_mpa is not None
        and 0.101 <= coolant_pressure_absolute_mpa <= 10.0
    ):
        # Antoine high-temperature water correlation (P in mmHg, T in degC).
        pressure_mmhg = coolant_pressure_absolute_mpa * 7500.616827
        denominator = 8.14019 - math.log10(pressure_mmhg)
        if denominator > 0.0:
            water_saturation_temperature_c = (
                1810.94 / denominator - 244.485
            )
    superheat_margin_c = (
        coolant_outlet_temperature_c - water_saturation_temperature_c
        if coolant_outlet_temperature_c is not None
        and water_saturation_temperature_c is not None
        else None
    )
    steam_superheat_observed = bool(
        superheat_margin_c is not None and superheat_margin_c >= 10.0
    )
    recommended_type = (
        "多管式平推流反应器（壳程蒸汽发生兼过热取热候选）"
        if steam_superheat_observed
        else "多管式平推流反应器（壳程蒸汽发生取热候选）"
        if boiling_water_heat_removal
        else "多管式平推流反应器（外侧换热介质方案候选）"
    )

    active_tube_diameter_mm = finite_number(
        record.get("active_tube_inner_diameter_mm")
    )
    active_tube_length_mm = 3000.0
    one_tube_volume_m3 = (
        math.pi
        * (active_tube_diameter_mm / 1000.0) ** 2
        / 4.0
        * (active_tube_length_mm / 1000.0)
        if active_tube_diameter_mm is not None
        else None
    )
    record["active_tube_length_screening_mm"] = active_tube_length_mm
    chain.append(
        lineage(
            target_field="active_tube_length_screening_mm",
            value=active_tube_length_mm,
            unit="mm",
            source_file=source_file,
            source_sha256=source_sha256,
            object_type="programmatic_RPLUG_geometry_screen",
            object_id=str(block.get("block_id") or ""),
            source_field="registered_active_tube_length_screen",
            source_path=(
                "knowledge_graph/equipment_model_recommendation_rules.json"
                "#RPLUG_active_tube_length_screen"
            ),
            transform="registered_screening_assumption",
            formula="L_active_tube_screen=3000 mm",
            substitution="3000",
            evidence_class="J",
            result_status="PROVISIONAL_SCREENING_ASSUMPTION",
            evidence_scope="ONE_ACTIVE_TUBE_GEOMETRY_SCREEN_ONLY",
            promotion_cap="TYPE_SCREENING",
            warning=(
                "3000 mm 是程序登记的单根有效管长度筛选假设，不是 Aspen "
                "值，也不是反应器总高或正式管长。"
            ),
        )
    )
    if one_tube_volume_m3 is not None:
        record[
            "one_tube_geometric_screening_volume_m3"
        ] = one_tube_volume_m3
        chain.append(
            lineage(
                target_field="one_tube_geometric_screening_volume_m3",
                value=one_tube_volume_m3,
                unit="m3",
                source_file=source_file,
                source_sha256=source_sha256,
                object_type="programmatic_RPLUG_geometry_screen",
                object_id=str(block.get("block_id") or ""),
                source_field=(
                    "active_tube_inner_diameter_mm/"
                    "active_tube_length_screening_mm"
                ),
                source_path=(
                    "programmatic_RPLUG_geometry_screen:"
                    + str(block.get("block_id") or "")
                ),
                transform="one_active_tube_geometric_identity",
                formula="V_1tube=pi*Di_active^2*L_active/4",
                substitution=(
                    f"pi*({active_tube_diameter_mm}/1000)^2*"
                    f"({active_tube_length_mm}/1000)/4"
                ),
                evidence_class="J",
                result_status="PROVISIONAL_ONE_TUBE_GEOMETRY",
                evidence_scope="ONE_ACTIVE_TUBE_GEOMETRY_SCREEN_ONLY",
                promotion_cap="TYPE_SCREENING",
                warning=(
                    "该体积只对应一根假定长度的有效管，不是所需反应器"
                    "总体积。"
                ),
            )
        )
    audit = {
        "schema": "rplug-preliminary-design-audit-v1",
        "status": "TYPE_SELECTED_REACTOR_SIZING_BLOCKED",
        "recommended_type": recommended_type,
        "port_role_mapping": roles,
        "port_mapping_issues": issues,
        "coolant_phase_transition": coolant_transition,
        "boiling_water_heat_removal_observed": (
            boiling_water_heat_removal
        ),
        "coolant_thermal_service_screening": {
            "status": (
                "STEAM_GENERATION_AND_SUPERHEAT_SCREENED"
                if steam_superheat_observed
                else "STEAM_GENERATION_SCREENED"
                if boiling_water_heat_removal
                else "NOT_APPLICABLE_OR_OPEN"
            ),
            "water_fraction": coolant_water_fraction,
            "coolant_pressure_mpa_absolute": (
                coolant_pressure_absolute_mpa
            ),
            "coolant_outlet_temperature_c": (
                coolant_outlet_temperature_c
            ),
            "water_saturation_temperature_c": (
                water_saturation_temperature_c
            ),
            "superheat_margin_c": superheat_margin_c,
            "superheat_screening_threshold_c": 10.0,
            "correlation": (
                "Antoine_water_A8.14019_B1810.94_C244.485"
                if water_saturation_temperature_c is not None
                else None
            ),
            "correlation_role": (
                "PROGRAM_SERVICE_SCREEN_NOT_FORMAL_STEAM_TABLE"
            ),
            "formal_two_zone_rating_complete": False,
            "evidence_class": "J",
            "promotion_cap": "TYPE_SCREENING",
        },
        "geometry_screening": {
            "active_tube_inner_diameter_mm": active_tube_diameter_mm,
            "active_tube_inner_diameter_source": (
                "ASPEN_RPLUG_DIAMETER"
                if active_tube_diameter_mm is not None
                else "OPEN"
            ),
            "active_tube_length_screening_mm": active_tube_length_mm,
            "active_tube_length_source": (
                "REGISTERED_SCREENING_ASSUMPTION"
                if active_tube_length_mm is not None
                else "OPEN"
            ),
            "one_tube_geometric_screening_volume_m3": (
                one_tube_volume_m3
            ),
            "total_reactor_volume_selected": False,
            "required_total_reactor_volume_m3": None,
            "tube_count_selected": False,
            "selected_tube_count": None,
            "shell_inner_diameter_selected": False,
            "reactor_shell_inner_diameter_mm": None,
            "whole_reactor_height_selected": False,
            "nominal_process_tube_wall_thickness_mm": None,
            "nominal_shell_wall_thickness_mm": None,
            "evidence_class": "J",
            "promotion_cap": "TYPE_SCREENING",
            "claim": (
                "ONE_ACTIVE_TUBE_GEOMETRY_SCREEN_ONLY_"
                "NOT_WHOLE_REACTOR_DIMENSIONS"
            ),
        },
        "formal_ready": False,
        "formal_open_gates": [
            "reaction_kinetics_and_rate_law",
            "conversion_selectivity_and_side_reaction_basis",
            "required_residence_time_or_space_velocity",
            "required_total_reactor_volume",
            "catalyst_form_loading_and_deactivation",
            "tube_count_pitch_and_tube_sheet_layout",
            "shell_diameter_baffles_and_circulation",
            "process_and_coolant_side_pressure_drop",
            "heat_release_profile_heat_flux_and_hot_spot",
            "boiling_side circulation_dryout_and_steam_quality",
            "steam_generation_and_superheat_zone_duty_split",
            "steam_outlet_quality_superheat_and_control_basis",
            "thermal_expansion_startup_shutdown_and_control",
            "materials_corrosion_and mechanical_design",
            "relief_runaway_and process_safety_review",
            "vendor_or_same_equipment_thermal_hydraulic_rating",
        ],
        "warning": (
            "Aspen RPLUG 的 DIAMETER 只按单根有效管内径解释；程序假设的"
            "有效管长及由此得到的单管几何体积，都不是反应器总尺寸。"
        ),
        "source_binding": {
            "aspen_export_path": str(source_file),
            "aspen_export_sha256": source_sha256,
        },
        "deterministic": True,
        "llm_used": False,
    }
    audit["audit_sha256"] = _canonical_sha256(audit)

    terminal_selection = {
        "status": "PROGRAMMATIC_RPLUG_FORM_SELECTED",
        "recommended_type": recommended_type,
        "selection_basis": (
            "aspen_RPLUG_identity_port_roles_and_coolant_phase_transition"
        ),
        "default_applied": False,
        "evidence_class": "J",
        "provisional": True,
        "rule_id": (
            "rplug:boiling_water_cooled_multitubular_screen"
            if boiling_water_heat_removal
            else "rplug:multitubular_external_heat_exchange_screen"
        ),
        "assumption": audit["warning"],
        "terminal_scope": "equipment_form_only",
        "formal_model": False,
        "is_vendor_model": False,
        "audit_sha256": audit["audit_sha256"],
    }
    apply_model_screening_boundary(
        match_result,
        boundary_id="rplug_reactor_geometry_and_kinetics_open",
        model_status="RPLUG_TYPE_SELECTED_REACTOR_SIZING_BLOCKED",
        candidate_status="PRELIMINARY_RPLUG_FORM_SELECTED",
        candidate_eligibility="TYPE_IDENTITY_ONLY_REACTOR_DESIGN_OPEN",
        missing_gates=audit["formal_open_gates"],
        execution_status="TYPE_SELECTED_REACTOR_SIZING_BLOCKED",
        execution_scope="RPLUG_EQUIPMENT_FORM_SCREENING_ONLY",
        recommended_type=recommended_type,
        terminal_selection=terminal_selection,
        warning=audit["warning"],
    )
    model = (
        match_result.get("model_recommendation", {})
        if isinstance(match_result.get("model_recommendation"), dict)
        else {}
    )
    designation = (
        f"{recommended_type}（程序初选；反应/热工/机械未闭合）"
        " | active_tube_ID_screen="
        f"{active_tube_diameter_mm if active_tube_diameter_mm is not None else 'OPEN'} mm"
        " | active_tube_L_assumption="
        f"{active_tube_length_mm if active_tube_length_mm is not None else 'OPEN'} mm"
        " | one_tube_geometry="
        f"{one_tube_volume_m3 if one_tube_volume_m3 is not None else 'OPEN'} m3"
        " | total_volume/tube_count/shell_D=OPEN"
    )
    candidates = [
        item
        for item in model.get("candidates", [])
        if isinstance(item, dict)
    ]
    leading = model.get("leading_candidate")
    if isinstance(leading, dict):
        candidates.append(leading)
    seen: set[int] = set()
    for candidate in candidates:
        if id(candidate) in seen:
            continue
        seen.add(id(candidate))
        if not str(candidate.get("status") or "").startswith("REJECTED_"):
            candidate["designation"] = designation
            candidate["rplug_preliminary_design_audit_sha256"] = audit[
                "audit_sha256"
            ]
    synchronize_model_boundary_projection(
        match_result,
        boundary_id="rplug_reactor_geometry_and_kinetics_open",
    )
    return audit


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


def parse_raw_history_pump_power(
    history_text: str,
) -> dict[str, dict[str, Any]]:
    """Parse final Aspen PUMP power channels without conflating semantics."""

    number = (
        r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)"
        r"(?:[Ee][-+]?\d+)?"
    )
    result_header = re.compile(
        r"(?im)^\s*GENERATING\s+RESULTS\s+FOR\s+UOS\s+BLOCK\s+"
        r"(?P<block>\S+)\s+MODEL:\s*PUMP\b"
    )
    result_matches = list(result_header.finditer(history_text))
    parsed: dict[str, dict[str, Any]] = {}
    for index, match in enumerate(result_matches):
        end = (
            result_matches[index + 1].start()
            if index + 1 < len(result_matches)
            else len(history_text)
        )
        segment = history_text[match.end():end]
        power_line = re.search(
            rf"(?im)\bFLUID\s+PWR\s*=\s*(?P<fluid>{number})\s*,"
            rf"\s*BRAKE\s+PWR\s*=\s*(?P<brake>{number})\s*,"
            rf"\s*ELEC\s+PWR\s*=\s*(?P<electric>{number})",
            segment,
        )
        if power_line is None:
            continue
        block_id = match.group("block").strip()
        parsed[block_id] = {
            "hydraulic_power_kw": (
                float(power_line.group("fluid")) / 1000.0
            ),
            "shaft_power_kw": (
                float(power_line.group("brake")) / 1000.0
            ),
            "electrical_power_kw": (
                float(power_line.group("electric")) / 1000.0
            ),
            "power_history_label": "FLUID/BRAKE/ELEC PWR",
            "power_raw_unit": "W",
        }

    input_header = re.compile(
        r"(?im)^\s*(?:\d+\s+)?BLOCK\s+(?P<block>\S+)\s+PUMP\b"
    )
    input_matches = list(input_header.finditer(history_text))
    for index, match in enumerate(input_matches):
        end = (
            input_matches[index + 1].start()
            if index + 1 < len(input_matches)
            else min(len(history_text), match.end() + 4000)
        )
        segment = history_text[match.end():end]
        efficiency = re.search(
            rf"(?im)\bDEFF\s*=\s*(?P<value>{number})",
            segment,
        )
        configured_speed = re.search(
            rf"(?im)\bPERFOR-PARAM\b[^\r\n]*"
            rf"\bACT-SH-SPEED\s*=\s*(?P<value>{number})",
            segment,
        )
        if efficiency is None and configured_speed is None:
            continue
        block_id = match.group("block").strip()
        entry = parsed.setdefault(block_id, {})
        if efficiency is not None:
            raw_fraction = float(efficiency.group("value"))
            entry["driver_efficiency_percent"] = (
                raw_fraction * 100.0
            )
            entry["driver_efficiency_raw_fraction"] = raw_fraction
            entry["driver_efficiency_history_label"] = "DEFF"
        if configured_speed is not None:
            speed_rpm = float(configured_speed.group("value"))
            entry[
                "aspen_configured_shaft_speed_candidate_rpm"
            ] = speed_rpm
            entry["configured_speed_history_label"] = (
                "PERFOR-PARAM ACT-SH-SPEED"
            )
            varied = re.search(
                rf"(?ims)\bVARY\s+BLOCK-VAR\s+"
                rf"BLOCK\s*=\s*{re.escape(block_id)}\s+"
                rf"VARIABLE\s*=\s*ACT-SH-SPEED\b"
                rf"(?P<body>.{{0,600}}?)"
                rf"\bLIMITS\s+\"?(?P<lower>{number})\"?"
                rf"\s+\"?(?P<upper>{number})\"?",
                history_text,
            )
            entry[
                "configured_speed_varied_by_design_spec"
            ] = varied is not None
            entry["configured_speed_uom"] = "rpm"
            if varied is not None:
                entry[
                    "configured_speed_design_spec_lower_limit_rpm"
                ] = float(varied.group("lower"))
                entry[
                    "configured_speed_design_spec_upper_limit_rpm"
                ] = float(varied.group("upper"))
            entry["configured_speed_is_solved_actual"] = False
            entry["configured_speed_semantic_boundary"] = (
                "Hash-bound Aspen input-deck PERFOR-PARAM value"
                + (
                    " and DESIGN-SPEC VARY search bound"
                    if varied is not None
                    else ""
                )
                + "; it is not an independently reported final solved "
                "shaft speed."
            )

    for block_id, entry in parsed.items():
        entry["block_id"] = block_id
        entry["semantic_status"] = (
            "ASPEN_PUMP_POWER_CHANNELS_SEPARATED"
        )
        entry["audit_sha256"] = _canonical_sha256(entry)
    return parsed


def enrich_pump_power_from_verified_run_history(
    blocks: list[dict[str, Any]],
    gate: dict[str, Any],
) -> dict[str, Any]:
    """Add missing pump channels only from gate-verified raw history."""

    attribution = (
        gate.get("raw_history_attribution", {})
        if isinstance(gate.get("raw_history_attribution"), dict)
        else {}
    )
    path_text = str(attribution.get("raw_history_path") or "").strip()
    expected_hash = str(
        attribution.get("raw_history_sha256") or ""
    ).strip().upper()
    report: dict[str, Any] = {
        "schema": "pump-power-history-enrichment-v1",
        "status": "NOT_AVAILABLE",
        "raw_history_path": path_text or None,
        "raw_history_sha256": expected_hash or None,
        "enriched_blocks": [],
    }
    if not path_text or not re.fullmatch(r"[0-9A-F]{64}", expected_hash):
        report["audit_sha256"] = _canonical_sha256(report)
        return report
    history_path = Path(path_text)
    if (
        not history_path.is_file()
        or sha256_file(history_path) != expected_hash
    ):
        report["status"] = "BLOCKED_HISTORY_FILE_OR_HASH_MISMATCH"
        report["audit_sha256"] = _canonical_sha256(report)
        return report

    parsed = parse_raw_history_pump_power(
        history_path.read_text(encoding="utf-8-sig", errors="replace")
    )
    for block in blocks:
        if str(block.get("block_type") or "").upper() != "PUMP":
            continue
        block_id = str(block.get("block_id") or "")
        observation = parsed.get(block_id)
        if not isinstance(observation, dict):
            continue
        enriched_fields: list[str] = []
        sources = block.setdefault("_sources", {})
        descriptors = (
            (
                "hydraulic_power_kw",
                observation.get("hydraulic_power_kw"),
                observation.get("hydraulic_power_kw"),
                "W",
                "FLUID PWR",
            ),
            (
                "shaft_power_kw",
                observation.get("shaft_power_kw"),
                observation.get("shaft_power_kw"),
                "W",
                "BRAKE PWR",
            ),
            (
                "electrical_power_kw",
                observation.get("electrical_power_kw"),
                observation.get("electrical_power_kw"),
                "W",
                "ELEC PWR",
            ),
            (
                "driver_efficiency_percent",
                observation.get("driver_efficiency_percent"),
                observation.get("driver_efficiency_raw_fraction"),
                "fraction",
                "DEFF",
            ),
            (
                "aspen_configured_shaft_speed_candidate_rpm",
                observation.get(
                    "aspen_configured_shaft_speed_candidate_rpm"
                ),
                observation.get(
                    "aspen_configured_shaft_speed_candidate_rpm"
                ),
                "rpm",
                "PERFOR-PARAM ACT-SH-SPEED",
            ),
        )
        typed_origins = {
            "hydraulic_power_kw": "ASPEN_PUMP_FLUID_POWER",
            "shaft_power_kw": "ASPEN_PUMP_BRAKE_POWER",
            "electrical_power_kw": "ASPEN_PUMP_ELECTRICAL_INPUT_POWER",
            "driver_efficiency_percent": "ASPEN_PUMP_DRIVER_EFFICIENCY",
            "aspen_configured_shaft_speed_candidate_rpm": (
                "ASPEN_PUMP_CONFIGURED_SHAFT_SPEED_INPUT_CANDIDATE"
            ),
        }
        for field_id, raw_value, original_value, raw_unit, label in descriptors:
            value = finite_number(raw_value)
            if value is None or finite_number(block.get(field_id)) is not None:
                continue
            if field_id == "driver_efficiency_percent":
                transform = "percent = Aspen_DEFF_fraction * 100"
            elif (
                field_id
                == "aspen_configured_shaft_speed_candidate_rpm"
            ):
                transform = (
                    "identity; configured Aspen input/design-spec "
                    "candidate, not solved actual speed"
                )
            else:
                original_value = value * 1000.0
                transform = "kW = Aspen_history_power_W / 1000"
            block[field_id] = value
            configured_speed_candidate = (
                field_id
                == "aspen_configured_shaft_speed_candidate_rpm"
            )
            sources[field_id] = {
                "source_field": label,
                "source_path": f"raw_history:{block_id}:{label}",
                "raw_value": original_value,
                "source_unit": raw_unit,
                "transform": transform,
                "origin": typed_origins[field_id],
                "transport_origin": "ASPEN_HASH_VERIFIED_RAW_HISTORY",
                "evidence_class": (
                    "R" if configured_speed_candidate else "D"
                ),
                "result_status": (
                    "ASPEN_CONFIGURED_INPUT_CANDIDATE_NOT_SOLVED_ACTUAL_SPEED"
                    if configured_speed_candidate
                    else "ASPEN_PUMP_POWER_SEMANTIC_NORMALIZED"
                ),
                "evidence_scope": (
                    "PUMP_CONFIGURED_SPEED_SEARCH_INPUT_ONLY"
                    if configured_speed_candidate
                    else "PUMP_PROCESS_POWER_BALANCE"
                ),
                "promotion_cap": "TYPE_SCREENING",
                "formal_design_evidence": False,
                "source_file_path": str(history_path),
                "source_file_sha256": expected_hash,
                "warning": (
                    observation.get(
                        "configured_speed_semantic_boundary"
                    )
                    if configured_speed_candidate
                    else (
                        "FLUID PWR, BRAKE PWR and ELEC PWR are distinct "
                        "Aspen quantities; WNET must not be relabelled "
                        "as shaft power."
                    )
                ),
            }
            enriched_fields.append(field_id)
        if enriched_fields:
            block["pump_power_history_audit"] = {
                **observation,
                "source_file_path": str(history_path),
                "source_file_sha256": expected_hash,
                "enriched_fields": sorted(enriched_fields),
            }
            block["pump_power_history_audit"]["audit_sha256"] = (
                _canonical_sha256(
                    block["pump_power_history_audit"]
                )
            )
            report["enriched_blocks"].append({
                "block_id": block_id,
                "fields": sorted(enriched_fields),
                "audit_sha256": block[
                    "pump_power_history_audit"
                ]["audit_sha256"],
            })
    report["status"] = (
        "ENRICHED"
        if report["enriched_blocks"]
        else "VERIFIED_HISTORY_NO_MISSING_PUMP_CHANNELS"
    )
    report["audit_sha256"] = _canonical_sha256(report)
    return report


def parse_raw_history_block_issues(
    history_text: str,
) -> dict[str, Any]:
    """Attribute Aspen history problem headers to exact unit-operation blocks."""

    header_pattern = re.compile(
        r"(?ims)^[ \t]*\*+[ \t]*"
        r"(?P<severity>TERMINAL[ \t]+ERROR|SEVERE[ \t]+ERROR|ERROR|WARNING)"
        r"[ \t]+(?:"
        r"(?:(?:WHILE[ \t]+EXECUTING|IN[ \t]+THE)"
        r"[ \t]+UNIT[ \t]+OPERATIONS[ \t]+BLOCK:[ \t]*"
        r"\"(?P<unit_block>[^\"]+)\""
        r"(?:[ \t]*\(MODEL:[ \t]*(?:\r?\n[ \t]*)?"
        r"\"(?P<unit_model>[^\"]+)\"\))?)"
        r"|(?:IN[ \t]+PHYSICAL[ \t]+PROPERTY[ \t]+SYSTEM"
        r"[ \t]+WHILE[ \t]+INITIALIZING[ \t]+PROPERTY[ \t]+MODELS)"
        r"|(?:WHILE[ \t]+EXECUTING[ \t]+SENSITIVITY[ \t]+BLOCK:[ \t]*"
        r"\"(?P<sensitivity_block>[^\"]+)\")"
        r")"
    )
    matches = list(header_pattern.finditer(history_text))
    events: list[dict[str, Any]] = []
    severity_key = {
        "TERMINAL ERROR": "terminal_errors",
        "SEVERE ERROR": "severe_errors",
        "ERROR": "errors",
        "WARNING": "warnings",
    }
    for index, match in enumerate(matches):
        raw_severity = " ".join(
            str(match.group("severity") or "").upper().split()
        )
        detail_end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else min(len(history_text), match.end() + 2000)
        )
        detail_lines: list[str] = []
        for raw_line in history_text[match.end():detail_end].splitlines():
            line = " ".join(raw_line.strip().split())
            if not line or re.match(r"^\*+\s*(?:WARNING|ERROR|SEVERE)", line):
                continue
            detail_lines.append(line)
            if len(detail_lines) >= 3:
                break
        unit_block = str(match.group("unit_block") or "").strip()
        sensitivity_block = str(
            match.group("sensitivity_block") or ""
        ).strip()
        if unit_block:
            issue_scope = "unit_operation_block"
            block_id = unit_block
            model = str(match.group("unit_model") or "").strip() or None
        elif sensitivity_block:
            issue_scope = "sensitivity_block"
            block_id = sensitivity_block
            model = "SENSITIVITY"
        else:
            issue_scope = "physical_property_system"
            block_id = "__PHYSICAL_PROPERTY_SYSTEM__"
            model = "PROPERTY_SYSTEM"
        event = {
            "event_index": index,
            "severity": severity_key.get(raw_severity, "errors"),
            "severity_label": raw_severity,
            "block_id": block_id,
            "model": model,
            "issue_scope": issue_scope,
            "detail_excerpt": " ".join(detail_lines)[:600],
            "header_offset": match.start(),
        }
        event["event_sha256"] = _canonical_sha256(event)
        events.append(event)

    by_block: dict[str, dict[str, Any]] = {}
    for event in events:
        block_id = event["block_id"]
        row = by_block.setdefault(
            block_id,
            {
                "block_id": block_id,
                "models": [],
                "issue_scopes": [],
                "counts": {
                    "terminal_errors": 0,
                    "severe_errors": 0,
                    "errors": 0,
                    "warnings": 0,
                },
                "event_sha256s": [],
                "detail_excerpts": [],
                "_detail_events": [],
            },
        )
        if event.get("model") and event["model"] not in row["models"]:
            row["models"].append(event["model"])
        if (
            event.get("issue_scope")
            and event["issue_scope"] not in row["issue_scopes"]
        ):
            row["issue_scopes"].append(event["issue_scope"])
        row["counts"][event["severity"]] += 1
        row["event_sha256s"].append(event["event_sha256"])
        if event.get("detail_excerpt"):
            row["_detail_events"].append({
                "severity": event["severity"],
                "event_index": event["event_index"],
                "detail_excerpt": event["detail_excerpt"],
            })
    block_issues: list[dict[str, Any]] = []
    for block_id in sorted(by_block):
        row = by_block[block_id]
        counts = row["counts"]
        row["event_count"] = sum(counts.values())
        row["highest_severity"] = (
            "terminal_error"
            if counts["terminal_errors"]
            else "severe_error"
            if counts["severe_errors"]
            else "error"
            if counts["errors"]
            else "warning"
        )
        row["models"] = sorted(row["models"])
        row["issue_scopes"] = sorted(row["issue_scopes"])
        severity_rank = {
            "terminal_errors": 0,
            "severe_errors": 1,
            "errors": 2,
            "warnings": 3,
        }
        row["detail_excerpts"] = [
            item["detail_excerpt"]
            for item in sorted(
                row.pop("_detail_events"),
                key=lambda item: (
                    severity_rank.get(item["severity"], 99),
                    item["event_index"],
                ),
            )[:5]
        ]
        row["issue_sha256"] = _canonical_sha256(row)
        block_issues.append(row)

    attributed_counts = {
        name: sum(
            int(row["counts"].get(name, 0))
            for row in block_issues
        )
        for name in (
            "terminal_errors",
            "severe_errors",
            "errors",
            "warnings",
        )
    }
    result = {
        "schema": "aspen-raw-history-block-attribution-v1",
        "status": (
            "BLOCK_EVENTS_ATTRIBUTED"
            if events
            else "NO_BLOCK_PROBLEM_HEADERS_FOUND"
        ),
        "event_count": len(events),
        "attributed_counts": attributed_counts,
        "block_issue_count": len(block_issues),
        "block_issues": block_issues,
        "events": events,
    }
    result["attribution_sha256"] = _canonical_sha256(result)
    return result


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
    history_text: str | None = None
    raw_history_path: Path | None = None
    raw_history_hash: str | None = None
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
                        raw_history_path = raw_history.resolve()
                        history_text = raw_history.read_text(encoding="utf-8-sig", errors="replace")
                        raw_counts = parse_raw_history_counts(history_text)
                        problem_patterns = (
                            r"(?im)^\s*\*+\s*WARNING\b",
                            r"(?i)WARNING IN THE",
                            r"(?im)^\s*\*+\s*SEVERE ERROR\b",
                            r"(?im)^\s*\*+\s*ERROR\b",
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
    raw_history_attribution = (
        parse_raw_history_block_issues(history_text)
        if history_text is not None
        else {
            "schema": "aspen-raw-history-block-attribution-v1",
            "status": "RAW_HISTORY_NOT_AVAILABLE_OR_NOT_HASH_VERIFIED",
            "event_count": 0,
            "attributed_counts": {
                name: 0 for name in names
            },
            "block_issue_count": 0,
            "block_issues": [],
            "events": [],
            "attribution_sha256": None,
        }
    )
    if history_text is not None:
        attributed_counts = raw_history_attribution["attributed_counts"]
        raw_history_attribution["reported_counts"] = counts
        raw_history_attribution["unattributed_counts"] = {
            name: (
                counts[name] - attributed_counts[name]
                if counts[name] is not None
                else None
            )
            for name in names
        }
        raw_history_attribution["count_reconciliation_status"] = (
            "EXACT"
            if all(
                counts[name] is not None
                and counts[name] == attributed_counts[name]
                for name in names
            )
            else "PARTIAL_OR_MISMATCH"
        )
        raw_history_attribution["raw_history_path"] = str(
            raw_history_path or ""
        )
        raw_history_attribution["raw_history_sha256"] = raw_history_hash
        raw_history_attribution["attribution_sha256"] = _canonical_sha256(
            {
                key: value
                for key, value in raw_history_attribution.items()
                if key != "attribution_sha256"
            }
        )

    bad_blocks_by_id: dict[str, dict[str, Any]] = {}
    for block in blocks:
        value = block.get("block_status")
        if value in (None, ""):
            continue
        if str(value).casefold().strip() not in CLEAN_BLOCK_WORDS:
            bad_blocks_by_id[str(block["block_id"])] = {
                "block_id": block["block_id"],
                "block_status": value,
                "sources": ["block_status"],
            }
    for issue in raw_history_attribution.get("block_issues", []):
        block_id = str(issue.get("block_id") or "")
        row = bad_blocks_by_id.setdefault(
            block_id,
            {
                "block_id": block_id,
                "block_status": "RAW_HISTORY_PROBLEM_EVENTS",
                "sources": [],
            },
        )
        row["sources"] = sorted(set([
            *row.get("sources", []),
            "raw_history_block_attribution",
        ]))
        row["raw_history_issue"] = issue
    bad_blocks = [
        bad_blocks_by_id[block_id]
        for block_id in sorted(bad_blocks_by_id)
    ]
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
        "raw_history_attribution": raw_history_attribution,
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
    source_path: str | None = None,
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
        "source_path": source_path,
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
    explicit_formula = str(source.get("formula") or "").strip()
    if explicit_formula:
        formula = explicit_formula
        substitution = str(source.get("equation_substitution") or raw_text)
    elif transform == "identity":
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
            source_path=str(
                source.get("source_path")
                or f"{object_type}:{object_id}.{source.get('source_field', target)}"
            ),
            transform=str(transform),
            formula=formula,
            substitution=substitution,
            evidence_class=str(source.get("evidence_class") or "D"),
            result_status=str(source.get("result_status") or "DERIVED"),
            evidence_scope=str(
                source.get("evidence_scope") or "ASPEN_PROCESS_SIDE"
            ),
            promotion_cap=str(
                source.get("promotion_cap") or "PROCESS_SIDE_ONLY"
            ),
            warning=(
                str(source.get("warning"))
                if source.get("warning") not in (None, "")
                else None
            ),
        )
    item["raw_value"] = raw
    item["raw_unit"] = source_unit
    item["origin"] = str(
        source.get("origin")
        or (
            "ASPEN_EXTRACTED"
            if str(transform) == "identity"
            else "ASPEN_DERIVED"
        )
    )
    item["formal_design_evidence"] = bool(
        source.get("formal_design_evidence", False)
    )
    for field in (
        "warning_codes",
        "result_sha256",
        "source_bundle_sha256",
        "formula_sources",
        "mixing_rule",
        "basis_conversion",
        "diagnostic_sha256",
        "legacy_export_unit_reinterpreted_as_kpa",
        "hash_bound_export_raw_value",
        "hash_bound_export_raw_unit",
        "reinterpretation_basis",
        "production_action",
        "source_file_path",
        "source_file_sha256",
    ):
        if source.get(field) not in (None, ""):
            item[field] = source[field]
    chain.append(item)


def apply_model_screening_boundary(
    match_result: dict[str, Any],
    *,
    boundary_id: str,
    model_status: str,
    candidate_status: str,
    candidate_eligibility: str,
    missing_gates: list[str],
    execution_status: str,
    execution_scope: str,
    recommended_type: str | None = None,
    terminal_selection: dict[str, Any] | None = None,
    warning: str,
) -> dict[str, Any]:
    """Keep a concrete type visible while enforcing an open physics gate."""

    model = (
        match_result.get("model_recommendation", {})
        if isinstance(match_result.get("model_recommendation"), dict)
        else {}
    )
    if not model:
        return {}
    if recommended_type:
        model["recommended_type"] = recommended_type
    if terminal_selection is not None:
        terminal = dict(terminal_selection)
        terminal.setdefault(
            "type_name_quality",
            matcher.terminal_type_name_quality(
                str(terminal.get("recommended_type") or recommended_type or "")
            ),
        )
        model["terminal_selection"] = terminal
    else:
        terminal = (
            dict(model.get("terminal_selection") or {})
            if isinstance(model.get("terminal_selection"), dict)
            else {}
        )

    candidates = [
        item
        for item in model.get("candidates", [])
        if isinstance(item, dict)
    ]
    leading = (
        model.get("leading_candidate")
        if isinstance(model.get("leading_candidate"), dict)
        else None
    )
    if leading is not None and all(leading is not item for item in candidates):
        candidates.append(leading)
    seen: set[int] = set()
    for candidate in candidates:
        identity = id(candidate)
        if identity in seen:
            continue
        seen.add(identity)
        if str(candidate.get("status") or "").startswith("REJECTED_"):
            continue
        if recommended_type:
            previous_type = str(candidate.get("recommended_type") or "")
            candidate["recommended_type"] = recommended_type
            candidate["type_name_quality"] = (
                matcher.terminal_type_name_quality(recommended_type)
            )
            designation = str(candidate.get("designation") or "")
            if designation:
                if " | " in designation:
                    candidate["designation"] = (
                        recommended_type + " | " + designation.split(" | ", 1)[1]
                    )
                elif previous_type and designation.startswith(previous_type):
                    candidate["designation"] = (
                        recommended_type + designation[len(previous_type):]
                    )
        candidate["status"] = candidate_status
        candidate["candidate_eligibility"] = candidate_eligibility
        candidate["eligible_for_formal_selection"] = False
        candidate["formal_model"] = False
        candidate["missing_gates"] = sorted(set([
            *candidate.get("missing_gates", []),
            *missing_gates,
        ]))
        candidate["screening_boundary_id"] = boundary_id
        candidate["screening_boundary_warning"] = warning
        if terminal:
            candidate["terminal_selection"] = dict(terminal)

    model["status"] = model_status
    model["formal_ready_candidate_count"] = 0
    model["formal_promotion_blockers"] = sorted(set([
        *model.get("formal_promotion_blockers", []),
        *missing_gates,
    ]))
    execution = (
        model.get("selection_execution")
        if isinstance(model.get("selection_execution"), dict)
        else {}
    )
    model["selection_execution"] = execution
    execution.update({
        "status": execution_status,
        "execution_scope": execution_scope,
        "formal_selection_executed": False,
    })
    boundary = {
        "schema": "model-screening-boundary-v1",
        "boundary_id": boundary_id,
        "model_status": model_status,
        "candidate_status": candidate_status,
        "candidate_eligibility": candidate_eligibility,
        "missing_gates": sorted(set(missing_gates)),
        "warning": warning,
        "formal_selection_executed": False,
    }
    boundary["boundary_sha256"] = _canonical_sha256(boundary)
    model.setdefault("screening_boundaries", []).append(boundary)
    return boundary


def synchronize_model_boundary_projection(
    match_result: dict[str, Any],
    *,
    boundary_id: str,
) -> dict[str, Any]:
    """Make every public model projection agree with the terminal candidate."""

    model = (
        match_result.get("model_recommendation", {})
        if isinstance(match_result.get("model_recommendation"), dict)
        else {}
    )
    leading = (
        model.get("leading_candidate")
        if isinstance(model.get("leading_candidate"), dict)
        else None
    )
    if not model or leading is None:
        return {}
    terminal = (
        model.get("terminal_selection", {})
        if isinstance(model.get("terminal_selection"), dict)
        else {}
    )
    recommended_type = str(
        leading.get("recommended_type")
        or terminal.get("recommended_type")
        or model.get("recommended_type")
        or ""
    )
    designation = str(leading.get("designation") or "")
    if recommended_type:
        quality = matcher.terminal_type_name_quality(recommended_type)
        leading["type_name_quality"] = quality
        for candidate in model.get("candidates", []):
            if (
                isinstance(candidate, dict)
                and not str(candidate.get("status") or "").startswith(
                    "REJECTED_"
                )
            ):
                candidate["type_name_quality"] = dict(quality)
        model["recommended_type"] = recommended_type

    decision = (
        match_result.get("model_decision", {})
        if isinstance(match_result.get("model_decision"), dict)
        else {}
    )
    if decision:
        old_designation = decision.get("generated_candidate_designation")
        if (
            old_designation not in (None, "")
            and old_designation != designation
            and "pre_boundary_candidate" not in decision
        ):
            decision["pre_boundary_candidate"] = {
                "generated_candidate_designation": old_designation,
                "model_status": decision.get("model_status"),
                "role": "SUPERSEDED_INTERNAL_MATCHER_PROJECTION",
                "not_for_customer_or_formal_use": True,
            }
        decision.update({
            "generated_candidate_designation": designation or None,
            "candidate_model": designation or None,
            "generated_candidate_model": None,
            "model_status": model.get("status"),
            "formal_model": False,
            "formal_promotion_blocked": True,
            "post_boundary_projection": True,
            "screening_boundary_id": boundary_id,
        })
        if terminal:
            decision["terminal_selection"] = dict(terminal)

    projection = {
        "schema": "model-boundary-projection-consistency-v1",
        "boundary_id": boundary_id,
        "recommended_type": recommended_type or None,
        "leading_designation": designation or None,
        "model_status": model.get("status"),
        "decision_designation": (
            decision.get("generated_candidate_designation")
            if decision
            else None
        ),
        "type_name_quality_consistent": bool(
            not recommended_type
            or leading.get("type_name_quality", {}).get("type_name")
            == recommended_type
        ),
        "designation_consistent": bool(
            not decision
            or decision.get("generated_candidate_designation")
            == designation
        ),
        "formal_ready": False,
    }
    projection["audit_sha256"] = _canonical_sha256(projection)
    model["projection_consistency"] = projection
    return projection


def apply_pump_npsha_model_gate(
    match_result: dict[str, Any],
    npsha_audit: dict[str, Any],
) -> None:
    status = str(npsha_audit.get("status") or "")
    if status == "SCREENING_VALUE_PHYSICALLY_PLAUSIBLE":
        return
    if status == "OPEN_MISSING_NPSHA":
        candidate_status = "PUMP_TYPE_RETAINED_NPSHA_MISSING"
    elif status == "BLOCKED_NONPOSITIVE_NPSHA":
        candidate_status = "PUMP_TYPE_RETAINED_NONPOSITIVE_NPSHA_RISK"
    else:
        candidate_status = "PUMP_TYPE_RETAINED_NPSHA_PHYSICS_BLOCKED"
    apply_model_screening_boundary(
        match_result,
        boundary_id=f"pump_npsha:{status or 'UNKNOWN'}",
        model_status="PUMP_TYPE_SELECTED_CAVITATION_BASIS_BLOCKED",
        candidate_status=candidate_status,
        candidate_eligibility="TYPE_IDENTITY_ONLY_CAVITATION_GATE_OPEN",
        missing_gates=[
            f"pump_npsha_process_audit:{status or 'UNKNOWN'}",
            *list(npsha_audit.get("open_gates") or []),
        ],
        execution_status="TYPE_RETAINED_CAVITATION_BASIS_BLOCKED",
        execution_scope="PUMP_TYPE_IDENTITY_ONLY",
        warning=(
            "泵型仍由程序保留，但 NPSHa 过程基础缺失、非正或超出吸入口绝对压头"
            "上限；不得显示为工程候选就绪，更不得进行正式泵定型。"
        ),
    )


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
    connected_viscosity_diagnostics = [
        dict(stream["viscosity_fallback_diagnostic"])
        for stream in inlets + outlets
        if isinstance(stream.get("viscosity_fallback_diagnostic"), dict)
    ]
    block_type = block["block_type"]
    (
        connected_stream_observations,
        connected_stream_observation_lineage,
    ) = build_connected_stream_observations(
        block=block,
        streams=streams,
        source_file=source_file,
        source_sha256=source_sha256,
    )
    chain.extend(connected_stream_observation_lineage)
    heatx_side_mapping = build_heatx_side_mapping(
        block=block,
        streams=streams,
        record=record,
        chain=chain,
        source_file=source_file,
        source_sha256=source_sha256,
    )
    heat_transfer_service_classification = classify_heat_transfer_service(
        block_type=block_type,
        inlets=inlets,
        outlets=outlets,
        heatx_side_mapping=heatx_side_mapping,
        pressure_basis=pressure_basis,
        atmospheric_pressure_mpa=(
            finite_number(case.get("atmospheric_pressure_mpa"))
            or 0.101325
        ),
    )
    if block_type in SINGLE_INLET_OUTLET_BLOCKS and (len(inlets) != 1 or len(outlets) != 1):
        blockers.append({"code": "PORT_CARDINALITY_AMBIGUOUS", "required": "one_inlet_one_outlet", "actual": [len(inlets), len(outlets)]})
    if len(inlets) == 1:
        stream = inlets[0]
        preferred_flow = "volumetric_flow_m3_h"
        if block_type in PHYSICAL_PIPING_BLOCK_TYPES:
            preferred_flow = (
                preferred_piping_flow_field(stream)
                or "volumetric_flow_m3_h"
            )
        elif block_type == "PUMP" and stream.get("liquid_volumetric_flow_m3_h") is not None:
            preferred_flow = "liquid_volumetric_flow_m3_h"
        elif block_type in {"COMPR", "MCOMPR"} and stream.get("vapor_volumetric_flow_m3_h") is not None:
            preferred_flow = "vapor_volumetric_flow_m3_h"
        inlet_targets = {
            preferred_flow: ("flow_m3_h", "m3/h"),
            "mass_flow_kg_h": ("mass_flow_kg_h", "kg/h"),
            "density_kg_m3": ("density_kg_m3", "kg/m3"),
            "dynamic_viscosity_mpa_s": ("dynamic_viscosity_mpa_s", "mPa*s"),
            "liquid_dynamic_viscosity_mpa_s": ("liquid_dynamic_viscosity_mpa_s", "mPa*s"),
            "vapor_dynamic_viscosity_mpa_s": ("vapor_dynamic_viscosity_mpa_s", "mPa*s"),
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
    temperatures = [
        (stream["stream_id"], finite_number(stream.get("temperature_c")))
        for stream in connected
        if finite_number(stream.get("temperature_c")) is not None
    ]
    connected_temperature_envelope: dict[str, Any] = {
        "status": "NOT_AVAILABLE",
        "minimum_temperature_c": None,
        "maximum_temperature_c": None,
        "stream_values": [],
    }
    if temperatures:
        minimum_temperature = min(value for _, value in temperatures)
        maximum_temperature = max(value for _, value in temperatures)
        connected_temperature_envelope = {
            "status": "PROVISIONAL_CONNECTED_STREAM_ENVELOPE",
            "minimum_temperature_c": minimum_temperature,
            "maximum_temperature_c": maximum_temperature,
            "stream_values": [
                {"stream_id": stream_id, "temperature_c": value}
                for stream_id, value in temperatures
            ],
            "claim_boundary": (
                "The maximum connected Aspen stream temperature is a "
                "process-side envelope used only to prevent an unsafe generic "
                "design-temperature default. Multi-side equipment still "
                "requires hot/cold-side port mapping, upset/startup/shutdown "
                "cases and a project mechanical design-temperature basis."
            ),
        }
        record["temperature_c"] = maximum_temperature
        chain.append(
            lineage(
                target_field="temperature_c",
                value=maximum_temperature,
                unit="C",
                source_file=source_file,
                source_sha256=source_sha256,
                object_type="connected_stream_set",
                object_id=block["block_id"],
                source_field="temperature_c",
                transform="maximum_connected_stream_temperature_envelope",
                formula="max(T_connected)",
                substitution=(
                    "max("
                    + ",".join(
                        f"{stream_id}:{value:.10g}"
                        for stream_id, value in temperatures
                    )
                    + ")"
                ),
                evidence_class="J",
                result_status="PROVISIONAL_PROCESS_ENVELOPE",
                evidence_scope=(
                    "CONNECTED_STREAM_PROCESS_TEMPERATURE_ENVELOPE"
                ),
                promotion_cap=(
                    "PRELIMINARY_DESIGN_TEMPERATURE_INPUT_ONLY"
                ),
                warning=connected_temperature_envelope["claim_boundary"],
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
        "hydraulic_power_kw": ("hydraulic_power_kw", "kW"),
        "electrical_power_kw": ("electrical_power_kw", "kW"),
        "driver_efficiency_percent": (
            "driver_efficiency_percent",
            "percent",
        ),
        "aspen_configured_shaft_speed_candidate_rpm": (
            "aspen_configured_shaft_speed_candidate_rpm",
            "r/min",
        ),
        "head_m": ("head_m", "m"),
        "npsha_m": ("npsha_m", "m"),
        "npsha_pressure_kpa": ("npsha_pressure_kpa", "kPa"),
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
            elif source_field == "diameter_mm" and block_type == "RPLUG":
                # Aspen RPLUG DIAMETER is one active plug-flow tube geometry,
                # not a reactor shell diameter or whole-equipment DN.
                target = "active_tube_inner_diameter_mm"
            add_direct(record, chain, target, block[source_field], unit, block["_sources"][source_field], source_file, source_sha256, "block", block["block_id"])
    if block_type == "PUMP":
        hydraulic_power_kw = finite_number(
            record.get("hydraulic_power_kw")
        )
        shaft_power_kw = finite_number(record.get("shaft_power_kw"))
        electrical_power_kw = finite_number(
            record.get("electrical_power_kw")
        )
        pump_efficiency_percent = finite_number(
            record.get("efficiency_percent")
        )
        driver_efficiency_percent = finite_number(
            record.get("driver_efficiency_percent")
        )
        calculated_shaft_power_kw = (
            hydraulic_power_kw
            / (pump_efficiency_percent / 100.0)
            if hydraulic_power_kw is not None
            and pump_efficiency_percent is not None
            and pump_efficiency_percent > 0.0
            else None
        )
        calculated_electrical_power_kw = (
            shaft_power_kw
            / (driver_efficiency_percent / 100.0)
            if shaft_power_kw is not None
            and driver_efficiency_percent is not None
            and driver_efficiency_percent > 0.0
            else None
        )

        def relative_error(
            observed: float | None,
            calculated: float | None,
        ) -> float | None:
            if observed is None or calculated is None:
                return None
            return abs(observed - calculated) / max(
                abs(observed),
                abs(calculated),
                1.0e-12,
            )

        shaft_balance_error = relative_error(
            shaft_power_kw,
            calculated_shaft_power_kw,
        )
        electrical_balance_error = relative_error(
            electrical_power_kw,
            calculated_electrical_power_kw,
        )
        available_balances = [
            value
            for value in (
                shaft_balance_error,
                electrical_balance_error,
            )
            if value is not None
        ]
        power_channel_values = {
            "hydraulic_power_kw": hydraulic_power_kw,
            "shaft_power_kw": shaft_power_kw,
            "electrical_power_kw": electrical_power_kw,
            "pump_efficiency_percent": pump_efficiency_percent,
            "driver_efficiency_percent": driver_efficiency_percent,
        }
        missing_power_channels = sorted(
            name
            for name, value in power_channel_values.items()
            if value is None
        )
        both_balances_complete = (
            shaft_balance_error is not None
            and electrical_balance_error is not None
            and not missing_power_channels
        )
        pump_power_status = (
            "PASS_ASPEN_POWER_CHANNELS_SEPARATED_AND_BALANCED"
            if both_balances_complete
            and all(value <= 0.005 for value in available_balances)
            else (
                "BLOCKED_PUMP_POWER_BALANCE_MISMATCH"
                if any(value > 0.005 for value in available_balances)
                else "OPEN_INCOMPLETE_PUMP_POWER_CHANNELS"
            )
        )
        record["pump_power_process_audit"] = {
            "schema": "pump-power-process-audit-v1",
            "status": pump_power_status,
            "hydraulic_power_kw": hydraulic_power_kw,
            "shaft_power_kw": shaft_power_kw,
            "electrical_power_kw": electrical_power_kw,
            "pump_efficiency_percent": pump_efficiency_percent,
            "driver_efficiency_percent": driver_efficiency_percent,
            "calculated_shaft_power_kw": calculated_shaft_power_kw,
            "calculated_electrical_power_kw": (
                calculated_electrical_power_kw
            ),
            "shaft_power_relative_error": shaft_balance_error,
            "electrical_power_relative_error": electrical_balance_error,
            "required_balance_count": 2,
            "calculated_balance_count": len(available_balances),
            "both_balances_complete": both_balances_complete,
            "missing_power_channels": missing_power_channels,
            "balance_relative_error_tolerance": 0.005,
            "wnet_semantic_for_pump": "ELECTRICAL_INPUT_POWER",
            "formal_ready": False,
            "formal_driver_selection_complete": False,
            "open_gates": [
                *(
                    ["complete_Aspen_pump_power_channels_and_both_balances"]
                    if not both_balances_complete
                    else []
                ),
                "motor_service_factor_and_starting_method",
                "motor_efficiency_at_selected_load",
                "coupling_and_auxiliary_losses",
                "vendor_guaranteed_pump_curve_and_power",
            ],
        }
        record["pump_power_process_audit"]["power_balance_sha256"] = (
            _canonical_sha256({
                key: record["pump_power_process_audit"].get(key)
                for key in (
                    "hydraulic_power_kw",
                    "shaft_power_kw",
                    "electrical_power_kw",
                    "pump_efficiency_percent",
                    "driver_efficiency_percent",
                    "calculated_shaft_power_kw",
                    "calculated_electrical_power_kw",
                )
            })
        )
        record["pump_power_process_audit"]["audit_sha256"] = (
            _canonical_sha256(record["pump_power_process_audit"])
        )
        if pump_power_status == "BLOCKED_PUMP_POWER_BALANCE_MISMATCH":
            blockers.append({
                "code": "PUMP_POWER_CHANNEL_BALANCE_MISMATCH",
                "pump_power_process_audit_sha256": record[
                    "pump_power_process_audit"
                ]["audit_sha256"],
            })
        npsha_pressure_kpa = finite_number(record.get("npsha_pressure_kpa"))
        density_kg_m3 = finite_number(record.get("density_kg_m3"))
        if npsha_pressure_kpa is not None:
            if density_kg_m3 is None or density_kg_m3 <= 0.0:
                blockers.append({
                    "code": "NPSHA_PRESSURE_TO_HEAD_REQUIRES_INLET_DENSITY",
                    "npsha_pressure_kpa": npsha_pressure_kpa,
                })
            else:
                gravity_m_s2 = 9.80665
                npsha_m = (
                    npsha_pressure_kpa
                    * 1000.0
                    / (density_kg_m3 * gravity_m_s2)
                )
                record["npsha_m"] = npsha_m
                chain.append(
                    lineage(
                        target_field="npsha_m",
                        value=npsha_m,
                        unit="m",
                        source_file=source_file,
                        source_sha256=source_sha256,
                        object_type="block_plus_inlet_stream",
                        object_id=block["block_id"],
                        source_field="NPSHA/density_kg_m3",
                        source_path=str(
                            block.get("_sources", {})
                            .get("npsha_pressure_kpa", {})
                            .get("source_path")
                            or f"block:{block['block_id']}.NPSHA"
                        ),
                        transform="pressure_margin_to_same_fluid_head",
                        formula="NPSHa_m=deltaP_available_kPa*1000/(rho*g)",
                        substitution=(
                            f"{npsha_pressure_kpa:.10g}*1000/"
                            f"({density_kg_m3:.10g}*{gravity_m_s2:.7g})"
                        ),
                        evidence_class="D",
                        result_status="DERIVED_FROM_ASPEN_HISTORY_PRESSURE_MARGIN",
                        evidence_scope="PUMP_SUCTION_PROCESS_SCREENING",
                        promotion_cap="TYPE_SCREENING",
                        warning=(
                            "NPSHa head is calculated from Aspen .his pressure "
                            "margin and the connected inlet-stream density. "
                            "Formal cavitation acceptance still requires a "
                            "same-duty vendor NPSHr curve and project margin."
                        ),
                    )
                )

        npsha_m = finite_number(record.get("npsha_m"))
        inlet_pressure_mpa = finite_number(record.get("inlet_pressure_mpa"))
        inlet_absolute_mpa: float | None = None
        if inlet_pressure_mpa is not None:
            if pressure_basis == "absolute":
                inlet_absolute_mpa = inlet_pressure_mpa
            elif pressure_basis == "gauge":
                atmospheric_mpa = finite_number(
                    record.get("atmospheric_pressure_mpa")
                )
                if atmospheric_mpa is not None:
                    inlet_absolute_mpa = inlet_pressure_mpa + atmospheric_mpa
        physical_upper_bound_m = (
            inlet_absolute_mpa
            * 1.0e6
            / (density_kg_m3 * 9.80665)
            if inlet_absolute_mpa is not None
            and inlet_absolute_mpa >= 0.0
            and density_kg_m3 is not None
            and density_kg_m3 > 0.0
            else None
        )
        if npsha_m is None:
            npsha_status = "OPEN_MISSING_NPSHA"
        elif npsha_m <= 0.0:
            npsha_status = "BLOCKED_NONPOSITIVE_NPSHA"
            blockers.append({
                "code": "PUMP_NONPOSITIVE_NPSHA_CAVITATION_RISK",
                "npsha_m": npsha_m,
            })
        elif (
            physical_upper_bound_m is not None
            and npsha_m > physical_upper_bound_m * (1.0 + 1.0e-6)
        ):
            npsha_status = "BLOCKED_NPSHA_EXCEEDS_ABSOLUTE_SUCTION_HEAD"
            blockers.append({
                "code": "PUMP_NPSHA_EXCEEDS_PHYSICAL_UPPER_BOUND",
                "npsha_m": npsha_m,
                "absolute_suction_head_upper_bound_m": physical_upper_bound_m,
            })
        else:
            npsha_status = "SCREENING_VALUE_PHYSICALLY_PLAUSIBLE"
        record["pump_npsha_process_audit"] = {
            "schema": "pump-npsha-process-audit-v1",
            "status": npsha_status,
            "npsha_pressure_margin_kpa": npsha_pressure_kpa,
            "npsha_m": npsha_m,
            "inlet_density_kg_m3": density_kg_m3,
            "inlet_pressure_mpa_absolute": inlet_absolute_mpa,
            "absolute_suction_head_upper_bound_m": physical_upper_bound_m,
            "pressure_to_head_formula": (
                "NPSHa_m=deltaP_available_kPa*1000/(rho*9.80665)"
                if npsha_pressure_kpa is not None
                else None
            ),
            "same_duty_npshr_available": bool(record.get("npshr_m")),
            "formal_cavitation_design_complete": False,
            "open_gates": [
                "same_duty_vendor_NPSHr_curve",
                "required_project_NPSH_margin",
                "suction_system_static_and_friction_loss_verification",
                "minimum_liquid_level_and_transient_cases",
            ],
        }
        record["pump_npsha_process_audit"]["audit_sha256"] = (
            _canonical_sha256(record["pump_npsha_process_audit"])
        )
    if block_type in PHYSICAL_PIPING_BLOCK_TYPES and not record.get("equipment_family"):
        # Aspen PIPE is a physical hydraulic pipe module, unlike MIXER/FSPLIT
        # topology nodes.  Its exact block identity is therefore sufficient to
        # route the unit to the deterministic process-piping family.  This does
        # not establish material, mechanical design pressure, or a formal
        # component marking; those remain behind the ordinary evidence gates.
        record["equipment_family"] = "family_process_piping"
        record.setdefault("process_function", "process fluid transport through Aspen PIPE hydraulic block")
        chain.append(
            lineage(
                target_field="equipment_family",
                value="family_process_piping",
                unit="-",
                source_file=source_file,
                source_sha256=source_sha256,
                object_type="block",
                object_id=block["block_id"],
                source_field="block_type",
                transform="exact_aspen_pipe_block_to_process_piping_family",
                formula="Aspen block_type PIPE -> family_process_piping",
                substitution=block_type,
                evidence_class="S",
                result_status="CONFIRMED_SOFTWARE_SEMANTIC",
                evidence_scope="EQUIPMENT_FAMILY_ROUTING_ONLY",
                promotion_cap="TYPE_SCREENING",
                warning=(
                    "Exact Aspen PIPE semantics establish the physical piping family only; "
                    "they do not establish mechanical design conditions, material, or a final model."
                ),
            )
        )
    if block_type in PHYSICAL_PIPING_BLOCK_TYPES:
        endpoint_index = endpoints or {}
        pipe_entity_id = f"ASPEN_PIPE_BLOCK:{block['block_id']}"
        pipe_endpoint_stream_ids = sorted(set(inlet_ids + outlet_ids))
        record.update({
            "pipe_entity_scope": "ASPEN_PHYSICAL_PIPE_BLOCK",
            "pipe_entity_id": pipe_entity_id,
            "pipe_entity_role": "CANONICAL_PHYSICAL_PIPE",
            "counted_as_physical_pipe": True,
            "alias_only": False,
            "classification_complete": True,
            "requires_manual_entity_resolution": False,
            "endpoint_state_stream_ids": pipe_endpoint_stream_ids,
        })
        for target_field, value in (
            ("pipe_entity_scope", record["pipe_entity_scope"]),
            ("pipe_entity_id", pipe_entity_id),
            ("counted_as_physical_pipe", True),
        ):
            chain.append(
                lineage(
                    target_field=target_field,
                    value=value,
                    unit="-",
                    source_file=source_file,
                    source_sha256=source_sha256,
                    object_type="block",
                    object_id=block["block_id"],
                    source_field="block_type/block_id",
                    transform="exact_aspen_pipe_block_physical_entity_identity",
                    formula=(
                        "block_type == PIPE -> canonical physical pipe entity"
                    ),
                    substitution=f"PIPE:{block['block_id']}",
                    evidence_class="S",
                    result_status="CONFIRMED_SOFTWARE_SEMANTIC",
                    evidence_scope="PHYSICAL_PIPE_ENTITY_IDENTITY",
                    promotion_cap="PHYSICAL_ENTITY_COUNTING",
                )
            )
        endpoint_pressure_drop_audit = (
            build_physical_pipe_endpoint_pressure_drop_audit(
                block=block,
                inlets=inlets,
                outlets=outlets,
                source_export_sha256=source_sha256,
                pipe_entity_id=pipe_entity_id,
                pressure_basis=pressure_basis,
            )
        )
        record["endpoint_pressure_drop_audit"] = (
            endpoint_pressure_drop_audit
        )
        record["endpoint_pressure_drop_status"] = (
            endpoint_pressure_drop_audit["status"]
        )
        record["endpoint_pressure_drop_formal_acceptance"] = False
        for target_field, value in (
            (
                "endpoint_pressure_drop_status",
                record["endpoint_pressure_drop_status"],
            ),
            ("endpoint_pressure_drop_formal_acceptance", False),
        ):
            chain.append(
                lineage(
                    target_field=target_field,
                    value=value,
                    unit="-",
                    source_file=source_file,
                    source_sha256=source_sha256,
                    object_type="pipe_endpoint_pressure_drop_audit",
                    object_id=pipe_entity_id,
                    source_field=target_field,
                    source_path=(
                        "endpoint_pressure_drop_audit:"
                        + endpoint_pressure_drop_audit["audit_sha256"]
                    ),
                    transform="hash_bound_endpoint_audit_projection",
                    formula="identity_from_endpoint_pressure_drop_audit",
                    substitution=str(value),
                    evidence_class="D",
                    result_status="DERIVED",
                    evidence_scope="ASPEN_PIPE_BLOCK_ENDPOINT_DELTA_ONLY",
                    promotion_cap="PROCESS_HYDRAULIC_OBSERVATION",
                )
            )
        endpoint_pressure_drop_kpa = finite_number(
            endpoint_pressure_drop_audit.get(
                "endpoint_pressure_drop_kpa"
            )
        )
        if endpoint_pressure_drop_kpa is not None:
            record["aspen_endpoint_pressure_drop_kpa"] = (
                endpoint_pressure_drop_kpa
            )
            inlet_binding = endpoint_pressure_drop_audit.get(
                "inlet_pressure_binding", {}
            )
            outlet_binding = endpoint_pressure_drop_audit.get(
                "outlet_pressure_binding", {}
            )
            chain.append(
                lineage(
                    target_field="aspen_endpoint_pressure_drop_kpa",
                    value=endpoint_pressure_drop_kpa,
                    unit="kPa",
                    source_file=source_file,
                    source_sha256=source_sha256,
                    object_type="physical_pipe_block_endpoints",
                    object_id=block["block_id"],
                    source_field="inlet_pressure_mpa/outlet_pressure_mpa",
                    source_path=(
                        f"{inlet_binding.get('source_path', '')}|"
                        f"{outlet_binding.get('source_path', '')}"
                    ),
                    transform="signed_endpoint_pressure_difference",
                    formula="deltaP_endpoint_kPa=(P_in-P_out)*1000",
                    substitution=(
                        f"({endpoint_pressure_drop_audit['inlet_pressure_mpa']}"
                        f"-{endpoint_pressure_drop_audit['outlet_pressure_mpa']})"
                        "*1000"
                    ),
                    evidence_class="D",
                    result_status="DERIVED_FROM_ASPEN_ENDPOINT_STATES",
                    evidence_scope="ASPEN_PIPE_BLOCK_ENDPOINT_DELTA_ONLY",
                    promotion_cap="PROCESS_HYDRAULIC_OBSERVATION",
                    warning=(
                        "This is the signed pressure difference between the "
                        "Aspen PIPE inlet and outlet states. It is not an "
                        "independent friction-loss reconstruction and does "
                        "not establish line length, diameter, roughness, "
                        "fittings, elevation, or formal hydraulic acceptance."
                    ),
                )
            )
        upstream_blocks = sorted({
            upstream
            for stream_id in inlet_ids
            for upstream in endpoint_index.get(stream_id, {}).get(
                "from_block_ids", []
            )
            if upstream != block["block_id"]
        })
        downstream_blocks = sorted({
            downstream
            for stream_id in outlet_ids
            for downstream in endpoint_index.get(stream_id, {}).get(
                "to_block_ids", []
            )
            if downstream != block["block_id"]
        })
        source_endpoint = (
            ",".join(upstream_blocks) if upstream_blocks else "PFD boundary"
        )
        destination_endpoint = (
            ",".join(downstream_blocks)
            if downstream_blocks
            else "PFD boundary"
        )
        record["line_number"] = record["equipment_tag"]
        record["source_endpoint"] = source_endpoint
        record["destination_endpoint"] = destination_endpoint
        for target_field, value, formula in (
            ("line_number", record["equipment_tag"], "Aspen_PIPE_block_id"),
            (
                "source_endpoint",
                source_endpoint,
                "PIPE_inlet_stream_upstream_block_or_boundary",
            ),
            (
                "destination_endpoint",
                destination_endpoint,
                "PIPE_outlet_stream_downstream_block_or_boundary",
            ),
        ):
            chain.append(
                lineage(
                    target_field=target_field,
                    value=value,
                    unit="-",
                    source_file=source_file,
                    source_sha256=source_sha256,
                    object_type="block_topology",
                    object_id=block["block_id"],
                    source_field=f"PFD.endpoints.{target_field}",
                    transform="deterministic_pipe_block_topology_projection",
                    formula=formula,
                    substitution=str(value),
                    evidence_class="D",
                    result_status="DERIVED",
                    evidence_scope="ASPEN_PFD_TOPOLOGY",
                    promotion_cap="PROCESS_SIDE_ONLY",
                )
            )
        process_stream = inlets[0] if inlets else (outlets[0] if outlets else None)
        if process_stream is not None:
            medium_name, composition_basis, composition_sources = (
                piping_medium_name(process_stream)
            )
            if medium_name:
                record["medium_name"] = medium_name
                record["main_medium"] = medium_name
                chain.append(
                    lineage(
                        target_field="medium_name",
                        value=medium_name,
                        unit="-",
                        source_file=source_file,
                        source_sha256=source_sha256,
                        object_type="stream",
                        object_id=process_stream["stream_id"],
                        source_field="composition",
                        transform="closed_composition_vector_to_medium_label",
                        formula=(
                            "ordered_positive_components_with_fraction_and_basis"
                        ),
                        substitution=json.dumps(
                            {
                                "basis": composition_basis,
                                "source_paths": composition_sources,
                            },
                            ensure_ascii=False,
                            separators=(",", ":"),
                        ),
                        evidence_class="D",
                        result_status="DERIVED",
                        evidence_scope="ASPEN_PROCESS_SIDE",
                        promotion_cap="PROCESS_SIDE_ONLY",
                    )
                )
        operating_temperature = finite_number(
            record.get("inlet_temperature_c")
        )
        if operating_temperature is None:
            operating_temperature = finite_number(
                record.get("outlet_temperature_c")
            )
        if operating_temperature is not None:
            record["temperature_c"] = operating_temperature
            record["operating_temperature_c"] = operating_temperature
            chain.append(
                lineage(
                    target_field="temperature_c",
                    value=operating_temperature,
                    unit="C",
                    source_file=source_file,
                    source_sha256=source_sha256,
                    object_type="block_connected_stream",
                    object_id=block["block_id"],
                    source_field="inlet_temperature_c_or_outlet_temperature_c",
                    transform="pipe_block_operating_temperature_alias",
                    formula="T_operating=T_inlet_else_T_outlet",
                    substitution=str(operating_temperature),
                    evidence_class="D",
                    result_status="DERIVED",
                    evidence_scope="ASPEN_PROCESS_SIDE",
                    promotion_cap="PROCESS_SIDE_ONLY",
                )
            )
    if (
        block_type in PHYSICAL_PIPING_BLOCK_TYPES
        and len(inlets) == 1
    ):
        viscosity_diagnostic = inlets[0].get(
            "viscosity_fallback_diagnostic"
        )
        if isinstance(viscosity_diagnostic, dict):
            record["viscosity_fallback_diagnostic"] = dict(
                viscosity_diagnostic
            )
        apply_two_phase_viscosity_screening(
            record=record,
            chain=chain,
            source_file=source_file,
            source_sha256=source_sha256,
            object_id=str(inlets[0].get("stream_id") or block["block_id"]),
            source_map=dict(inlets[0].get("_sources") or {}),
        )
        apply_pipe_pressure_regime_screening(
            record=record,
            chain=chain,
            source_file=source_file,
            source_sha256=source_sha256,
            object_id=block["block_id"],
        )
        apply_pipe_hydraulic_preselection(
            record=record,
            chain=chain,
            source_file=source_file,
            source_sha256=source_sha256,
            object_id=block["block_id"],
        )
    logic_node = block_type in SIMULATION_LOGIC_BLOCK_TYPES
    matcher_record = (
        {
            key: value
            for key, value in record.items()
            if key
            not in {
                "pipe_hydraulic_preselection",
                "pipe_pressure_regime_screening",
                "viscosity_fallback_diagnostic",
            }
        }
        if block_type in PHYSICAL_PIPING_BLOCK_TYPES
        else record
    )
    match_result = (
        simulation_logic_match_result(record, block)
        if logic_node
        else matcher.match_one(matcher_record, rules, graph)
    )
    if not logic_node:
        apply_heat_transfer_service_model_gate(
            match_result,
            heat_transfer_service_classification,
        )
    tower_preliminary_design_audit = build_tower_preliminary_design_audit(
        record=record,
        chain=chain,
        match_result=match_result,
        source_file=source_file,
        source_sha256=source_sha256,
    )
    rplug_preliminary_design_audit = (
        build_rplug_preliminary_design_audit(
            block=block,
            streams=streams,
            record=record,
            chain=chain,
            match_result=match_result,
            source_file=source_file,
            source_sha256=source_sha256,
        )
    )
    if block_type == "PUMP" and isinstance(
        record.get("pump_npsha_process_audit"), dict
    ):
        apply_pump_npsha_model_gate(
            match_result,
            record["pump_npsha_process_audit"],
        )
    pipe_specification: dict[str, Any] | None = None
    if block_type in PHYSICAL_PIPING_BLOCK_TYPES and not logic_node:
        try:
            pipe_specification = build_programmatic_pipe_specification(
                stream_id=block["block_id"],
                record=record,
                match_result=match_result,
                source_file=source_file,
                source_sha256=source_sha256,
            )
        except Exception as exc:
            pipe_specification = {
                "schema": "programmatic-pipe-specification-v1",
                "status": "BLOCKED_PROGRAMMATIC_PIPE_SPECIFICATION",
                "deterministic": True,
                "llm_used": False,
                "stream_id": block["block_id"],
                "error_code": type(exc).__name__,
                "error": str(exc),
            }
        match_result["programmatic_pipe_specification"] = pipe_specification
        apply_programmatic_pipe_specification(
            record=record,
            chain=chain,
            pipe_specification=pipe_specification,
            source_file=source_file,
            source_sha256=source_sha256,
            object_id=block["block_id"],
        )
        apply_programmatic_pipe_model_boundary(
            match_result,
            pipe_specification,
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
        "status": (
            "ASPEN_WITH_PROGRAMMATIC_PROPERTY_ESTIMATE"
            if any(
                item.get("internal_correlation_used") is True
                for item in connected_viscosity_diagnostics
            )
            else "ASPEN_DERIVED_PROCESS_SIDE"
        ),
        "source_file_path": str(source_file),
        "source_file_sha256": source_sha256,
        "lineage_count": len(chain),
        "evidence_class_counts": {
            evidence_class: sum(1 for item in chain if item.get("evidence_class") == evidence_class)
            for evidence_class in sorted({str(item.get("evidence_class") or "U") for item in chain})
        },
        "formal_use_allowed_by_this_adapter_alone": False,
        "mechanical_design_basis_established": False,
        "boundary": (
            "Aspen/process-side conditions and deterministic unit/identity "
            "derivations; any explicitly identified internal viscosity "
            "correlation remains J/type-screening only"
        ),
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
        "connected_stream_observations": connected_stream_observations,
        "connected_stream_observation_lineage": (
            connected_stream_observation_lineage
        ),
        "connected_stream_viscosity_diagnostics": (
            connected_viscosity_diagnostics
        ),
        "connected_stream_temperature_envelope": (
            connected_temperature_envelope
        ),
        "heatx_side_mapping": heatx_side_mapping,
        "heat_transfer_service_classification": (
            heat_transfer_service_classification
        ),
        "tower_preliminary_design_audit": (
            tower_preliminary_design_audit
        ),
        "rplug_preliminary_design_audit": (
            rplug_preliminary_design_audit
        ),
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
    if pipe_specification is not None:
        result["programmatic_pipe_specification"] = pipe_specification
    if block_type in PHYSICAL_PIPING_BLOCK_TYPES:
        result.update({
            "pipe_entity_scope": record["pipe_entity_scope"],
            "pipe_entity_id": record["pipe_entity_id"],
            "pipe_entity_role": record["pipe_entity_role"],
            "counted_as_physical_pipe": record[
                "counted_as_physical_pipe"
            ],
            "alias_only": record["alias_only"],
            "classification_complete": True,
            "requires_manual_entity_resolution": False,
            "endpoint_state_stream_ids": list(
                record.get("endpoint_state_stream_ids", [])
            ),
            "endpoint_pressure_drop_audit": dict(
                record["endpoint_pressure_drop_audit"]
            ),
        })
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


def _pipe_pressure_binding(
    stream: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return the immutable Aspen pressure identity for one endpoint state."""

    if not isinstance(stream, dict):
        return {
            "stream_id": None,
            "pressure_mpa": None,
            "source_field": None,
            "source_path": None,
            "raw_value": None,
            "source_unit": None,
            "transform": None,
        }
    source = (
        dict(stream.get("_sources", {}).get("pressure_mpa", {}))
        if isinstance(stream.get("_sources"), dict)
        and isinstance(
            stream.get("_sources", {}).get("pressure_mpa"), dict
        )
        else {}
    )
    return {
        "stream_id": stream.get("stream_id"),
        "pressure_mpa": finite_number(stream.get("pressure_mpa")),
        "source_field": source.get("source_field"),
        "source_path": source.get("source_path"),
        "raw_value": source.get("raw_value"),
        "source_unit": source.get("source_unit"),
        "transform": source.get("transform"),
    }


def build_physical_pipe_endpoint_pressure_drop_audit(
    *,
    block: dict[str, Any],
    inlets: list[dict[str, Any]],
    outlets: list[dict[str, Any]],
    source_export_sha256: str,
    pipe_entity_id: str,
    pressure_basis: str,
) -> dict[str, Any]:
    """Bind one Aspen PIPE pressure delta to its two endpoint state records.

    The calculation deliberately stops at ``P_in-P_out``.  It does not claim
    that Aspen exported the physical length, bore, roughness, fittings,
    elevation profile, or enough information for an independent Darcy
    reconciliation.
    """

    inlet = inlets[0] if len(inlets) == 1 else None
    outlet = outlets[0] if len(outlets) == 1 else None
    inlet_binding = _pipe_pressure_binding(inlet)
    outlet_binding = _pipe_pressure_binding(outlet)
    inlet_pressure_mpa = finite_number(
        inlet_binding.get("pressure_mpa")
    )
    outlet_pressure_mpa = finite_number(
        outlet_binding.get("pressure_mpa")
    )
    cardinality_complete = len(inlets) == 1 and len(outlets) == 1
    pressure_complete = (
        inlet_pressure_mpa is not None
        and outlet_pressure_mpa is not None
    )
    endpoint_complete = cardinality_complete and pressure_complete
    endpoint_pressure_drop_kpa = (
        (inlet_pressure_mpa - outlet_pressure_mpa) * 1000.0
        if endpoint_complete
        else None
    )
    if not cardinality_complete:
        status = "BLOCKED_AMBIGUOUS_PIPE_ENDPOINT_CARDINALITY"
    elif not pressure_complete:
        status = "BLOCKED_MISSING_PIPE_ENDPOINT_PRESSURE"
    else:
        status = "ASPEN_ENDPOINT_PRESSURE_DIFFERENCE_CALCULATED"
    if endpoint_pressure_drop_kpa is None:
        pressure_change_direction = "UNKNOWN"
    elif endpoint_pressure_drop_kpa > 1.0e-9:
        pressure_change_direction = "DROP"
    elif endpoint_pressure_drop_kpa < -1.0e-9:
        pressure_change_direction = "RISE"
    else:
        pressure_change_direction = "NEGLIGIBLE"
    audit: dict[str, Any] = {
        "schema": "pipe-endpoint-pressure-drop-audit-v1",
        "status": status,
        "pipe_entity_scope": "ASPEN_PHYSICAL_PIPE_BLOCK",
        "pipe_entity_id": pipe_entity_id,
        "block_id": block.get("block_id"),
        "inlet_stream_ids": [
            str(item.get("stream_id") or "") for item in inlets
        ],
        "outlet_stream_ids": [
            str(item.get("stream_id") or "") for item in outlets
        ],
        "inlet_pressure_binding": inlet_binding,
        "outlet_pressure_binding": outlet_binding,
        "inlet_pressure_mpa": inlet_pressure_mpa,
        "outlet_pressure_mpa": outlet_pressure_mpa,
        "pressure_basis": pressure_basis,
        "endpoint_pressure_drop_kpa": endpoint_pressure_drop_kpa,
        "pressure_change_direction": pressure_change_direction,
        "calculation_formula": (
            "deltaP_endpoint_kPa=(P_inlet_mpa-P_outlet_mpa)*1000"
        ),
        "endpoint_cardinality_complete": cardinality_complete,
        "endpoint_pressure_complete": pressure_complete,
        "endpoint_complete": endpoint_complete,
        "source_export_sha256": source_export_sha256,
        "formal_acceptance": False,
        "formal_ready": False,
        "independent_friction_loss_reconciliation_complete": False,
        "independent_reconciliation_status": (
            "BLOCKED_MISSING_VERIFIED_LENGTH_DIAMETER_ROUGHNESS_"
            "FITTINGS_AND_ELEVATION"
        ),
        "open_gates": [
            "verified_physical_line_length",
            "verified_internal_diameter_and_wall",
            "verified_roughness_and_fitting_equivalent_lengths",
            "elevation_profile_and_static_head_separation",
            "independent_Darcy_friction_loss_reconciliation",
            "project_allowable_total_pressure_drop",
        ],
        "claim_boundary": (
            "The value is only the signed pressure difference between the "
            "two Aspen PIPE endpoint states. It is not a reconstructed "
            "friction-only loss, and no missing geometry is invented."
        ),
    }
    audit["audit_sha256"] = _canonical_sha256(audit)
    return audit


def classify_pfd_stream_pipe_entity(
    *,
    stream_id: str,
    endpoints: dict[str, list[str]],
    physical_pipe_block_ids: set[str],
) -> dict[str, Any]:
    """Classify a PFD material-stream edge without double-counting PIPE nodes."""

    from_blocks = {
        str(value)
        for value in endpoints.get("from_block_ids", [])
        if str(value)
    }
    to_blocks = {
        str(value)
        for value in endpoints.get("to_block_ids", [])
        if str(value)
    }
    adjacent_pipe_blocks = sorted(
        (from_blocks | to_blocks) & physical_pipe_block_ids
    )
    topology_cardinality_unambiguous = (
        len(from_blocks) <= 1 and len(to_blocks) <= 1
    )
    canonical_pipe_entity_ids = [
        f"ASPEN_PIPE_BLOCK:{block_id}"
        for block_id in adjacent_pipe_blocks
    ]
    if adjacent_pipe_blocks:
        classification_complete = (
            len(adjacent_pipe_blocks) == 1
            and topology_cardinality_unambiguous
        )
        return {
            "pipe_entity_scope": "ASPEN_PIPE_ENDPOINT_STATE",
            "pipe_entity_id": (
                canonical_pipe_entity_ids[0]
                if len(canonical_pipe_entity_ids) == 1
                else f"PFD_ENDPOINT_STATE:{stream_id}"
            ),
            "pipe_entity_role": "ENDPOINT_STATE_ALIAS",
            "counted_as_physical_pipe": False,
            "alias_only": True,
            "canonical_pipe_entity_ids": canonical_pipe_entity_ids,
            "adjacent_physical_pipe_block_ids": adjacent_pipe_blocks,
            "classification_complete": classification_complete,
            "requires_manual_entity_resolution": (
                not classification_complete
            ),
            "alias_status": (
                "BOUND_TO_ONE_CANONICAL_PHYSICAL_PIPE"
                if classification_complete
                else (
                    "BLOCKED_MULTIPLE_CANONICAL_PHYSICAL_PIPE_BINDINGS"
                    if len(adjacent_pipe_blocks) > 1
                    else "BLOCKED_AMBIGUOUS_STREAM_ENDPOINT_CARDINALITY"
                )
            ),
            "alias_reason": (
                "This Aspen material stream is an endpoint state of an "
                "explicit physical PIPE block. It remains available for "
                "process-property and topology evidence but is not counted "
                "as another physical pipe."
            ),
        }
    return {
        "pipe_entity_scope": "PFD_MATERIAL_STREAM_SEGMENT",
        "pipe_entity_id": f"PFD_STREAM:{stream_id}",
        "pipe_entity_role": "CANONICAL_PFD_PIPE_SEGMENT",
        "counted_as_physical_pipe": True,
        "alias_only": False,
        "canonical_pipe_entity_ids": [f"PFD_STREAM:{stream_id}"],
        "adjacent_physical_pipe_block_ids": [],
        "classification_complete": (
            topology_cardinality_unambiguous
        ),
        "requires_manual_entity_resolution": (
            not topology_cardinality_unambiguous
        ),
        "alias_status": "NOT_AN_ALIAS",
        "alias_reason": None,
    }


def build_pfd_stream_endpoint_pressure_drop_audit(
    *,
    stream: dict[str, Any],
    pipe_entity: dict[str, Any],
    source_export_sha256: str,
    pressure_basis: str,
) -> dict[str, Any]:
    """Disclose that one Aspen material-stream state cannot prove a line dP."""

    pressure_binding = _pipe_pressure_binding(stream)
    alias_only = pipe_entity.get("alias_only") is True
    audit: dict[str, Any] = {
        "schema": "pipe-endpoint-pressure-drop-audit-v1",
        "status": (
            "NOT_APPLICABLE_ENDPOINT_STATE_ALIAS"
            if alias_only
            else "OPEN_SINGLE_PFD_STREAM_STATE_HAS_NO_ENDPOINT_PAIR"
        ),
        "pipe_entity_scope": pipe_entity.get("pipe_entity_scope"),
        "pipe_entity_id": pipe_entity.get("pipe_entity_id"),
        "stream_id": stream.get("stream_id"),
        "single_state_pressure_binding": pressure_binding,
        "inlet_pressure_mpa": None,
        "outlet_pressure_mpa": None,
        "endpoint_pressure_drop_kpa": None,
        "pressure_basis": pressure_basis,
        "endpoint_cardinality_complete": False,
        "endpoint_pressure_complete": False,
        "endpoint_complete": False,
        "source_export_sha256": source_export_sha256,
        "formal_acceptance": False,
        "formal_ready": False,
        "independent_friction_loss_reconciliation_complete": False,
        "independent_reconciliation_status": (
            "NOT_APPLICABLE_ALIAS_USES_PHYSICAL_PIPE_BLOCK_AUDIT"
            if alias_only
            else "BLOCKED_NO_DISTINCT_UPSTREAM_AND_DOWNSTREAM_PRESSURE_STATES"
        ),
        "open_gates": (
            []
            if alias_only
            else [
                "distinct_upstream_and_downstream_pressure_states",
                "verified_physical_line_length",
                "verified_internal_diameter_and_roughness",
                "fittings_and_elevation_profile",
                "project_allowable_total_pressure_drop",
            ]
        ),
        "claim_boundary": (
            "A PFD material stream carries one thermodynamic state, not two "
            "independent line-end pressures. No whole-line pressure drop is "
            "fabricated from that single state."
        ),
    }
    audit["audit_sha256"] = _canonical_sha256(audit)
    return audit


def _raw_connection_pairs(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    result: list[dict[str, str]] = []
    for row in value:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        role = str(row.get("value") or "").strip()
        if name and role:
            result.append({"name": name, "value": role})
    return result


def _boundary_connection_name(value: str) -> bool:
    return str(value or "").strip().startswith("#")


def bidirectional_topology_integrity(
    raw_stream_rows: list[Any],
    raw_block_rows: list[Any],
    blocks: list[dict[str, Any]],
) -> dict[str, Any]:
    """Cross-check the COM stream connection tree against block port topology.

    Older hand-authored exports do not carry COM ``connections``/``port_detail``
    evidence.  They remain derivable for backwards compatibility, but are
    explicitly labelled as unavailable rather than receiving a false pass.
    """

    raw_streams = [
        row for row in raw_stream_rows
        if isinstance(row, dict) and str(row.get("stream_id") or "").strip()
    ]
    raw_blocks = [
        row for row in raw_block_rows
        if isinstance(row, dict) and str(row.get("block_id") or "").strip()
    ]
    stream_connection_available = any(
        isinstance(row.get("connections"), list) for row in raw_streams
    )
    block_connection_available = any(
        isinstance(row.get("connections"), list) for row in raw_blocks
    )
    block_port_detail_available = any(
        isinstance(row.get("port_detail"), list) for row in raw_blocks
    )
    expected_endpoints = stream_endpoints(blocks)
    raw_stream_map = {
        str(row.get("stream_id") or "").strip(): row for row in raw_streams
    }
    raw_block_map = {
        str(row.get("block_id") or "").strip(): row for row in raw_blocks
    }

    if not stream_connection_available:
        payload: dict[str, Any] = {
            "schema": "aspen-bidirectional-topology-integrity-v1",
            "status": "NOT_AVAILABLE_LEGACY_EXPORT",
            "stream_connection_evidence_available": False,
            "block_connection_evidence_available": block_connection_available,
            "block_port_detail_evidence_available": block_port_detail_available,
            "referenced_stream_count": len(expected_endpoints),
            "validated_stream_count": 0,
            "block_count": len(blocks),
            "validated_block_count": 0,
            "stream_rows": [],
            "block_rows": [],
            "issues": [],
            "claim_boundary": (
                "Endpoints were projected from block inlet/outlet arrays only; "
                "the export has no independent COM stream-connection evidence."
            ),
        }
        payload["topology_sha256"] = connection_selection.canonical_sha256(payload)
        return payload

    issues: list[dict[str, Any]] = []
    stream_rows: list[dict[str, Any]] = []
    for stream_id in sorted(expected_endpoints):
        expected = expected_endpoints[stream_id]
        raw_stream = raw_stream_map.get(stream_id)
        if raw_stream is None:
            issues.append({
                "code": "TOPOLOGY_REFERENCED_STREAM_ROW_MISSING",
                "stream_id": stream_id,
            })
            continue
        pairs = _raw_connection_pairs(raw_stream.get("connections"))
        source_names = sorted(
            row["name"] for row in pairs if row["value"].strip().upper() == "SOURCE"
        )
        destination_names = sorted(
            row["name"] for row in pairs if row["value"].strip().upper() == "DEST"
        )
        expected_source = sorted(expected.get("from_block_ids", []))
        expected_destination = sorted(expected.get("to_block_ids", []))
        actual_source = sorted(
            name for name in source_names if not _boundary_connection_name(name)
        )
        actual_destination = sorted(
            name for name in destination_names if not _boundary_connection_name(name)
        )
        source_boundaries = sorted(
            name for name in source_names if _boundary_connection_name(name)
        )
        destination_boundaries = sorted(
            name for name in destination_names if _boundary_connection_name(name)
        )
        row_issues: list[dict[str, Any]] = []
        if len(source_names) != 1:
            row_issues.append({
                "code": "TOPOLOGY_STREAM_SOURCE_CARDINALITY_INVALID",
                "actual_count": len(source_names),
            })
        if len(destination_names) != 1:
            row_issues.append({
                "code": "TOPOLOGY_STREAM_DESTINATION_CARDINALITY_INVALID",
                "actual_count": len(destination_names),
            })
        if actual_source != expected_source:
            row_issues.append({
                "code": "TOPOLOGY_STREAM_SOURCE_BLOCK_MISMATCH",
                "expected": expected_source,
                "actual": actual_source,
            })
        if actual_destination != expected_destination:
            row_issues.append({
                "code": "TOPOLOGY_STREAM_DESTINATION_BLOCK_MISMATCH",
                "expected": expected_destination,
                "actual": actual_destination,
            })
        if bool(expected_source) == bool(source_boundaries):
            row_issues.append({
                "code": "TOPOLOGY_STREAM_SOURCE_BOUNDARY_MISMATCH",
                "expected_boundary": not bool(expected_source),
                "actual_boundaries": source_boundaries,
            })
        if bool(expected_destination) == bool(destination_boundaries):
            row_issues.append({
                "code": "TOPOLOGY_STREAM_DESTINATION_BOUNDARY_MISMATCH",
                "expected_boundary": not bool(expected_destination),
                "actual_boundaries": destination_boundaries,
            })
        stream_row = {
            "stream_id": stream_id,
            "status": "PASS" if not row_issues else "FAILED",
            "stream_connection_pairs": pairs,
            "expected_from_block_ids": expected_source,
            "expected_to_block_ids": expected_destination,
            "actual_from_block_ids": actual_source,
            "actual_to_block_ids": actual_destination,
            "source_boundary_tokens": source_boundaries,
            "destination_boundary_tokens": destination_boundaries,
            "issues": row_issues,
        }
        stream_row["row_sha256"] = connection_selection.canonical_sha256(stream_row)
        stream_rows.append(stream_row)
        issues.extend({"stream_id": stream_id, **item} for item in row_issues)

    block_rows: list[dict[str, Any]] = []
    for block in sorted(blocks, key=lambda item: str(item.get("block_id") or "")):
        block_id = str(block.get("block_id") or "").strip()
        inlet_streams = sorted(str(value) for value in block.get("inlet_streams", []))
        outlet_streams = sorted(str(value) for value in block.get("outlet_streams", []))
        raw_block = raw_block_map.get(block_id, {})
        pairs = _raw_connection_pairs(raw_block.get("connections"))
        port_detail = (
            raw_block.get("port_detail")
            if isinstance(raw_block.get("port_detail"), list)
            else []
        )
        pair_inlets = sorted({
            row["name"] for row in pairs if "(IN)" in row["value"].upper()
        })
        pair_outlets = sorted({
            row["name"] for row in pairs if "(OUT)" in row["value"].upper()
        })
        detail_inlets = sorted({
            str(stream_id)
            for row in port_detail if isinstance(row, dict)
            and str(row.get("direction") or "").strip().casefold() == "in"
            for stream_id in list_value(row.get("streams"))
        })
        detail_outlets = sorted({
            str(stream_id)
            for row in port_detail if isinstance(row, dict)
            and str(row.get("direction") or "").strip().casefold() == "out"
            for stream_id in list_value(row.get("streams"))
        })
        row_issues: list[dict[str, Any]] = []
        if block_connection_available:
            if not isinstance(raw_block.get("connections"), list):
                row_issues.append({
                    "code": "TOPOLOGY_BLOCK_CONNECTION_EVIDENCE_MISSING",
                })
            elif pair_inlets != inlet_streams or pair_outlets != outlet_streams:
                row_issues.append({
                    "code": "TOPOLOGY_BLOCK_CONNECTION_PORT_MISMATCH",
                    "expected_inlet_streams": inlet_streams,
                    "actual_inlet_streams": pair_inlets,
                    "expected_outlet_streams": outlet_streams,
                    "actual_outlet_streams": pair_outlets,
                })
        if block_port_detail_available:
            if not isinstance(raw_block.get("port_detail"), list):
                row_issues.append({
                    "code": "TOPOLOGY_BLOCK_PORT_DETAIL_EVIDENCE_MISSING",
                })
            elif detail_inlets != inlet_streams or detail_outlets != outlet_streams:
                row_issues.append({
                    "code": "TOPOLOGY_BLOCK_PORT_DETAIL_MISMATCH",
                    "expected_inlet_streams": inlet_streams,
                    "actual_inlet_streams": detail_inlets,
                    "expected_outlet_streams": outlet_streams,
                    "actual_outlet_streams": detail_outlets,
                })
        block_row = {
            "block_id": block_id,
            "status": "PASS" if not row_issues else "FAILED",
            "inlet_streams": inlet_streams,
            "outlet_streams": outlet_streams,
            "connection_pairs": pairs,
            "port_detail_inlet_streams": detail_inlets,
            "port_detail_outlet_streams": detail_outlets,
            "issues": row_issues,
        }
        block_row["row_sha256"] = connection_selection.canonical_sha256(block_row)
        block_rows.append(block_row)
        issues.extend({"block_id": block_id, **item} for item in row_issues)

    payload = {
        "schema": "aspen-bidirectional-topology-integrity-v1",
        "status": "PASS" if not issues else "FAILED",
        "stream_connection_evidence_available": True,
        "block_connection_evidence_available": block_connection_available,
        "block_port_detail_evidence_available": block_port_detail_available,
        "referenced_stream_count": len(expected_endpoints),
        "validated_stream_count": sum(
            row.get("status") == "PASS" for row in stream_rows
        ),
        "block_count": len(blocks),
        "validated_block_count": sum(
            row.get("status") == "PASS" for row in block_rows
        ),
        "stream_rows": stream_rows,
        "block_rows": block_rows,
        "issues": issues,
        "claim_boundary": (
            "PASS proves agreement among COM stream SOURCE/DEST rows, block "
            "inlet/outlet arrays, block connection ports and port_detail for "
            "the exported topology; it does not prove physical line routing."
        ),
    }
    payload["topology_sha256"] = connection_selection.canonical_sha256(payload)
    return payload


def material_stream_for_piping(stream: dict[str, Any]) -> bool:
    """Legacy exports lack record type; explicit non-material types are excluded."""

    return str(stream.get("stream_record_type") or "").strip().upper() in {"", "MATERIAL"}


def preferred_piping_flow_field(stream: dict[str, Any]) -> str | None:
    phase = str(stream.get("phase") or "").strip().casefold()
    if phase in {"liquid", "liq"}:
        candidates = ("liquid_volumetric_flow_m3_h", "volumetric_flow_m3_h")
    elif phase in {"vapor", "vapour", "gas"}:
        candidates = ("vapor_volumetric_flow_m3_h", "volumetric_flow_m3_h")
    elif phase in {"mixed", "two_phase", "two-phase", "two phase", "multiphase"}:
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


PIPE_PHASE_VELOCITY_TARGET_M_S = {
    "liquid": 1.5,
    "vapor": 15.0,
    "mixed": 3.0,
}
PIPE_PRESELECTION_WALL_THICKNESS_MM = 4.0
PIPE_PRESELECTION_ROUGHNESS_MM = 0.045
PIPE_PRESSURE_GRADIENT_SCREEN_KPA_PER_100M = 50.0


def _pipe_hydraulic_screening_metrics(
    *,
    flow_m3_h: float,
    inner_diameter_mm: float,
    density_kg_m3: float | None,
    dynamic_viscosity_mpa_s: float | None,
    roughness_mm: float,
) -> dict[str, Any]:
    """Return one deterministic Darcy-Weisbach screening point.

    The transition interval deliberately takes the larger of the laminar and
    Swamee-Jain estimates.  This avoids a non-conservative discontinuity at
    Re=2300 while keeping the calculation suitable only for preliminary line
    sizing.
    """

    if flow_m3_h <= 0.0 or inner_diameter_mm <= 0.0:
        return {
            "status": "BLOCKED_NONPOSITIVE_FLOW_OR_INNER_DIAMETER",
            "actual_velocity_m_s": None,
            "reynolds_number": None,
            "darcy_friction_factor": None,
            "friction_branch": "blocked_invalid_input",
            "pressure_gradient_kpa_per_100m": None,
        }
    inner_diameter_m = inner_diameter_mm / 1000.0
    actual_velocity = (
        4.0
        * (flow_m3_h / 3600.0)
        / (math.pi * inner_diameter_m**2)
    )
    if (
        density_kg_m3 is None
        or density_kg_m3 <= 0.0
        or dynamic_viscosity_mpa_s is None
        or dynamic_viscosity_mpa_s <= 0.0
    ):
        return {
            "status": "VELOCITY_ONLY_MISSING_DENSITY_OR_VISCOSITY",
            "actual_velocity_m_s": actual_velocity,
            "reynolds_number": None,
            "darcy_friction_factor": None,
            "friction_branch": "blocked_missing_density_or_viscosity",
            "pressure_gradient_kpa_per_100m": None,
        }
    reynolds_number = (
        density_kg_m3
        * actual_velocity
        * inner_diameter_m
        / (dynamic_viscosity_mpa_s / 1000.0)
    )
    laminar_factor = 64.0 / reynolds_number
    relative_roughness = roughness_mm / inner_diameter_mm
    swamee_jain_factor = 0.25 / (
        math.log10(
            relative_roughness / 3.7
            + 5.74 / reynolds_number**0.9
        )
        ** 2
    )
    if reynolds_number < 2300.0:
        darcy_friction_factor = laminar_factor
        friction_branch = "laminar_64_over_re"
    elif reynolds_number < 4000.0:
        darcy_friction_factor = max(
            laminar_factor,
            swamee_jain_factor,
        )
        friction_branch = (
            "transition_conservative_max_64_over_re_swamee_jain"
        )
    else:
        darcy_friction_factor = swamee_jain_factor
        friction_branch = "swamee_jain_screening"
    pressure_gradient = (
        darcy_friction_factor
        * density_kg_m3
        * actual_velocity**2
        / (2.0 * inner_diameter_m)
        * 100.0
        / 1000.0
    )
    return {
        "status": "CALCULATED_DARCY_WEISBACH_SCREENING",
        "actual_velocity_m_s": actual_velocity,
        "reynolds_number": reynolds_number,
        "darcy_friction_factor": darcy_friction_factor,
        "friction_branch": friction_branch,
        "pressure_gradient_kpa_per_100m": pressure_gradient,
    }


def _pipe_pressure_gradient_required_diameter_mm(
    *,
    flow_m3_h: float,
    density_kg_m3: float,
    dynamic_viscosity_mpa_s: float,
    roughness_mm: float,
    limit_kpa_per_100m: float,
) -> float:
    """Solve the continuous ID that meets the registered gradient screen."""

    low_mm = 0.1
    high_mm = 1.0
    while True:
        metrics = _pipe_hydraulic_screening_metrics(
            flow_m3_h=flow_m3_h,
            inner_diameter_mm=high_mm,
            density_kg_m3=density_kg_m3,
            dynamic_viscosity_mpa_s=dynamic_viscosity_mpa_s,
            roughness_mm=roughness_mm,
        )
        gradient = finite_number(
            metrics.get("pressure_gradient_kpa_per_100m")
        )
        if gradient is not None and gradient <= limit_kpa_per_100m:
            break
        high_mm *= 2.0
        if high_mm > 100_000.0:
            raise RuntimeError(
                "BLOCKED_PIPE_PRESSURE_GRADIENT_DIAMETER_SOLVER_RANGE"
            )
    for _ in range(100):
        midpoint_mm = 0.5 * (low_mm + high_mm)
        metrics = _pipe_hydraulic_screening_metrics(
            flow_m3_h=flow_m3_h,
            inner_diameter_mm=midpoint_mm,
            density_kg_m3=density_kg_m3,
            dynamic_viscosity_mpa_s=dynamic_viscosity_mpa_s,
            roughness_mm=roughness_mm,
        )
        gradient = finite_number(
            metrics.get("pressure_gradient_kpa_per_100m")
        )
        if gradient is None or gradient > limit_kpa_per_100m:
            low_mm = midpoint_mm
        else:
            high_mm = midpoint_mm
    return high_mm


def apply_pipe_pressure_regime_screening(
    *,
    record: dict[str, Any],
    chain: list[dict[str, Any]],
    source_file: Path,
    source_sha256: str,
    object_id: str,
) -> dict[str, Any]:
    """Classify meaningful vacuum before the generic matcher is called."""

    operating_pressure = finite_number(record.get("operating_pressure_mpa"))
    pressure_basis = str(record.get("pressure_basis") or "").casefold()
    atmospheric_pressure = finite_number(
        record.get("atmospheric_pressure_mpa")
    )
    if atmospheric_pressure is None or atmospheric_pressure <= 0.0:
        atmospheric_pressure = 0.101325
    operating_gauge_pressure: float | None = None
    if operating_pressure is not None:
        if pressure_basis == "absolute":
            operating_gauge_pressure = (
                operating_pressure - atmospheric_pressure
            )
        elif pressure_basis == "gauge":
            operating_gauge_pressure = operating_pressure
    signed_vacuum_margin_kpa = (
        -operating_gauge_pressure * 1000.0
        if operating_gauge_pressure is not None
        else None
    )
    vacuum_margin_kpa = (
        max(0.0, signed_vacuum_margin_kpa)
        if signed_vacuum_margin_kpa is not None
        else None
    )
    vacuum_threshold_kpa = max(
        5.0,
        0.05 * atmospheric_pressure * 1000.0,
    )
    significant_vacuum = (
        vacuum_margin_kpa is not None
        and vacuum_margin_kpa >= vacuum_threshold_kpa
    )
    near_atmospheric = (
        operating_gauge_pressure is not None
        and abs(operating_gauge_pressure * 1000.0)
        < vacuum_threshold_kpa
    )
    screening_applied = False
    if (
        operating_gauge_pressure is not None
        and (significant_vacuum or near_atmospheric)
        and finite_number(record.get("design_pressure_mpa")) is None
    ):
        record["design_pressure_mpa"] = 0.1
        record["design_pressure_basis"] = "gauge"
        screening_applied = True
        warning = (
            "0.1 MPa(g) is a J-class internal-pressure screening basis only. "
            + (
                "The steady Aspen condition triggers a significant vacuum; "
                "external-pressure buckling remains a formal open gate."
                if significant_vacuum
                else (
                    "The steady Aspen condition does not reach the registered "
                    "significant-vacuum threshold; accident vacuum remains "
                    "project-defined."
                )
            )
        )
        for target_field, value, unit in (
            ("design_pressure_mpa", 0.1, "MPa(g)"),
            ("design_pressure_basis", "gauge", "-"),
        ):
            chain.append(
                lineage(
                    target_field=target_field,
                    value=value,
                    unit=unit,
                    source_file=source_file,
                    source_sha256=source_sha256,
                    object_type="pipe_pressure_regime_selector",
                    object_id=object_id,
                    source_field=(
                        "operating_pressure_mpa,pressure_basis,"
                        "atmospheric_pressure_mpa"
                    ),
                    source_path=(
                        f"pipe_pressure_regime_screening:{object_id}"
                    ),
                    transform=(
                        "registered_near_atmospheric_or_vacuum_"
                        "internal_pressure_screen"
                    ),
                    formula=(
                        "Pscreen=0.1 MPa(g) while external/accident "
                        "vacuum authority remains open"
                    ),
                    substitution=json.dumps(
                        {
                            "operating_gauge_pressure_mpa": (
                                operating_gauge_pressure
                            ),
                            "vacuum_margin_kpa": vacuum_margin_kpa,
                            "vacuum_threshold_kpa": vacuum_threshold_kpa,
                            "significant_vacuum": significant_vacuum,
                        },
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                    evidence_class="J",
                    result_status="PROVISIONAL_PRESSURE_REGIME_SCREEN",
                    evidence_scope=(
                        "PROGRAMMATIC_PRELIMINARY_PIPE_SELECTION"
                    ),
                    promotion_cap="TYPE_SCREENING",
                    warning=warning,
                )
            )
    if operating_gauge_pressure is None:
        status = "BLOCKED_PRESSURE_REGIME_INPUTS"
    elif significant_vacuum:
        status = (
            "SIGNIFICANT_STEADY_STATE_VACUUM_"
            "EXTERNAL_PRESSURE_GATE_OPEN"
        )
    elif near_atmospheric:
        status = (
            "NEAR_ATMOSPHERIC_NO_SIGNIFICANT_STEADY_STATE_VACUUM"
        )
    else:
        status = "POSITIVE_INTERNAL_PRESSURE_REGIME"
    audit = {
        "schema": "pipe-pressure-regime-screening-v1",
        "status": status,
        "pressure_basis": pressure_basis or None,
        "operating_pressure_mpa": operating_pressure,
        "atmospheric_pressure_mpa": atmospheric_pressure,
        "operating_gauge_pressure_mpa": operating_gauge_pressure,
        "signed_vacuum_margin_kpa": signed_vacuum_margin_kpa,
        "vacuum_margin_kpa": vacuum_margin_kpa,
        "vacuum_threshold_kpa": vacuum_threshold_kpa,
        "threshold_basis": (
            "max(5 kPa, 5% of atmospheric pressure); registered project "
            "screening threshold, not a national-code acceptance limit"
        ),
        "significant_steady_state_vacuum": significant_vacuum,
        "near_atmospheric_screening": near_atmospheric,
        "internal_pressure_screening_applied": screening_applied,
        "internal_pressure_screening_mpa_gauge": (
            0.1 if screening_applied else None
        ),
        "external_pressure_branch": significant_vacuum,
        "formal_external_pressure_design_complete": False,
        "accident_vacuum_case_defined": False,
        "claim_boundary": (
            "The threshold classifies the visible steady Aspen condition only. "
            "Accident vacuum, blocked-in cooling, draining, steam-out and "
            "external-pressure stability remain project-defined."
        ),
    }
    audit["pressure_regime_sha256"] = _canonical_sha256(audit)
    record["pipe_pressure_regime_screening"] = audit
    return audit


def apply_pipe_hydraulic_preselection(
    *,
    record: dict[str, Any],
    chain: list[dict[str, Any]],
    source_file: Path,
    source_sha256: str,
    object_id: str,
) -> dict[str, Any]:
    """Make Darcy pressure gradient participate in preliminary DN selection."""

    flow_m3_h = finite_number(record.get("flow_m3_h"))
    density_kg_m3 = finite_number(record.get("density_kg_m3"))
    viscosity_mpa_s = finite_number(
        record.get("dynamic_viscosity_mpa_s")
    )
    phase = matcher.canonical_phase(record.get("phase")) or "unknown"
    two_phase = phase == "mixed"
    phase_velocity_target = PIPE_PHASE_VELOCITY_TARGET_M_S.get(
        phase,
        1.5,
    )
    base: dict[str, Any] = {
        "schema": "pipe-hydraulic-preselection-v1",
        "phase": phase,
        "two_phase_advisory": two_phase,
        "flow_m3_h": flow_m3_h,
        "density_kg_m3": density_kg_m3,
        "dynamic_viscosity_mpa_s": viscosity_mpa_s,
        "phase_velocity_target_m_s": phase_velocity_target,
        "provisional_wall_thickness_mm": (
            PIPE_PRESELECTION_WALL_THICKNESS_MM
        ),
        "roughness_mm": PIPE_PRESELECTION_ROUGHNESS_MM,
        "pressure_gradient_screen_limit_kpa_per_100m": (
            PIPE_PRESSURE_GRADIENT_SCREEN_KPA_PER_100M
        ),
        "pressure_gradient_limit_role": (
            "PROJECT_PRELIMINARY_SCREEN_NOT_NATIONAL_CODE_LIMIT"
            if not two_phase
            else (
                "PROJECT_PRELIMINARY_ADVISORY_NOT_CODE_ACCEPTANCE"
            )
        ),
        "formal_hydraulic_acceptance": False,
        "formal_two_phase_hydraulics_complete": False,
        "open_gates": (
            [
                "flow_regime_map",
                "phase_holdup_and_slip",
                "flashing_and_choking",
                "slugging_and_vibration",
                "validated_two_phase_pressure_drop_correlation",
            ]
            if two_phase
            else [
                "project_line_length_and_fittings",
                "project_pressure_drop_acceptance",
            ]
        ),
    }
    if flow_m3_h is None or flow_m3_h <= 0.0:
        base["status"] = "BLOCKED_MISSING_OR_NONPOSITIVE_FLOW"
        base["preselection_sha256"] = _canonical_sha256(base)
        record["pipe_hydraulic_preselection"] = base
        return base

    velocity_required_id_mm = (
        math.sqrt(
            4.0
            * (flow_m3_h / 3600.0)
            / (math.pi * phase_velocity_target)
        )
        * 1000.0
    )
    pressure_required_id_mm: float | None = None
    if (
        density_kg_m3 is not None
        and density_kg_m3 > 0.0
        and viscosity_mpa_s is not None
        and viscosity_mpa_s > 0.0
    ):
        pressure_required_id_mm = (
            _pipe_pressure_gradient_required_diameter_mm(
                flow_m3_h=flow_m3_h,
                density_kg_m3=density_kg_m3,
                dynamic_viscosity_mpa_s=viscosity_mpa_s,
                roughness_mm=PIPE_PRESELECTION_ROUGHNESS_MM,
                limit_kpa_per_100m=(
                    PIPE_PRESSURE_GRADIENT_SCREEN_KPA_PER_100M
                ),
            )
        )
    controlling_required_id_mm = max(
        value
        for value in (
            velocity_required_id_mm,
            pressure_required_id_mm,
        )
        if value is not None
    )
    if pressure_required_id_mm is None:
        controlling_constraint = (
            "VELOCITY_ONLY_MISSING_DENSITY_OR_VISCOSITY"
        )
    elif pressure_required_id_mm > velocity_required_id_mm * (
        1.0 + 1.0e-9
    ):
        controlling_constraint = (
            "TWO_PHASE_PRESSURE_GRADIENT_PROXY_ADVISORY"
            if two_phase
            else "PRESSURE_GRADIENT_SCREEN"
        )
    elif velocity_required_id_mm > pressure_required_id_mm * (
        1.0 + 1.0e-9
    ):
        controlling_constraint = "VELOCITY_SCREEN"
    else:
        controlling_constraint = "VELOCITY_AND_PRESSURE_GRADIENT"

    catalog = matcher.load_pipe_standard_dn_od()
    selected_row: dict[str, Any] | None = None
    trials: list[dict[str, Any]] = []
    for row in catalog:
        available_inner = (
            float(row["outer_diameter_mm"])
            - 2.0 * PIPE_PRESELECTION_WALL_THICKNESS_MM
        )
        metrics = _pipe_hydraulic_screening_metrics(
            flow_m3_h=flow_m3_h,
            inner_diameter_mm=available_inner,
            density_kg_m3=density_kg_m3,
            dynamic_viscosity_mpa_s=viscosity_mpa_s,
            roughness_mm=PIPE_PRESELECTION_ROUGHNESS_MM,
        )
        trial = {
            "dn": row["dn"],
            "catalog_outer_diameter_mm": row["outer_diameter_mm"],
            "provisional_inner_diameter_mm": available_inner,
            "meets_controlling_required_inner_diameter": (
                available_inner + 1.0e-9
                >= controlling_required_id_mm
            ),
            "actual_velocity_m_s": metrics["actual_velocity_m_s"],
            "pressure_gradient_kpa_per_100m": metrics[
                "pressure_gradient_kpa_per_100m"
            ],
            "friction_branch": metrics["friction_branch"],
        }
        trials.append(trial)
        if trial["meets_controlling_required_inner_diameter"]:
            selected_row = row
            break
    base.update(
        {
            "velocity_required_inner_diameter_mm": (
                velocity_required_id_mm
            ),
            "pressure_gradient_required_inner_diameter_mm": (
                pressure_required_id_mm
            ),
            "controlling_required_inner_diameter_mm": (
                controlling_required_id_mm
            ),
            "controlling_constraint": controlling_constraint,
            "candidate_trials": trials,
        }
    )
    if selected_row is None:
        base["status"] = "BLOCKED_REQUIRED_ID_EXCEEDS_VERIFIED_DN_CATALOG"
        base["preselection_sha256"] = _canonical_sha256(base)
        record["pipe_hydraulic_preselection"] = base
        return base

    effective_target_velocity = (
        4.0
        * (flow_m3_h / 3600.0)
        / (
            math.pi
            * (controlling_required_id_mm / 1000.0) ** 2
        )
    )
    if two_phase:
        status = (
            "ADVISORY_HOMOGENEOUS_PROXY_"
            "FORMAL_TWO_PHASE_GATE_OPEN"
            if pressure_required_id_mm is not None
            else "ADVISORY_VELOCITY_ONLY_TWO_PHASE_PROPERTIES_OPEN"
        )
    elif pressure_required_id_mm is None:
        status = (
            "SELECTED_VELOCITY_ONLY_PRESSURE_GRADIENT_INPUTS_OPEN"
        )
    else:
        status = (
            "SELECTED_SINGLE_PHASE_VELOCITY_AND_"
            "PRESSURE_GRADIENT_SCREEN"
        )
    selected_catalog_record = {
        key: selected_row.get(key)
        for key in (
            "dn",
            "nps",
            "outer_diameter_mm",
            "standard_id",
            "standard_version",
            "source_pdf_sha256",
            "physical_page",
            "source_table_asset_id",
            "source_row_1based",
            "qa_status",
            "reuse_class",
            "application_boundary",
        )
    }
    selected_catalog_record["catalog_path"] = str(
        matcher.PIPE_STANDARD_DN_OD_PATH
    )
    selected_catalog_record["catalog_sha256"] = sha256_file(
        matcher.PIPE_STANDARD_DN_OD_PATH
    )
    selected_catalog_record["record_binding_sha256"] = (
        _canonical_sha256(selected_catalog_record)
    )
    base.update(
        {
            "status": status,
            "matcher_effective_target_velocity_m_s": (
                effective_target_velocity
            ),
            "selected_dn_candidate": selected_row["dn"],
            "selected_catalog_outer_diameter_mm": selected_row[
                "outer_diameter_mm"
            ],
            "selected_provisional_inner_diameter_mm": (
                float(selected_row["outer_diameter_mm"])
                - 2.0 * PIPE_PRESELECTION_WALL_THICKNESS_MM
            ),
            "selected_catalog_record": selected_catalog_record,
            "selection_scope": (
                "IDENTITY_AND_PRELIMINARY_GEOMETRY_ONLY"
            ),
        }
    )
    base["preselection_sha256"] = _canonical_sha256(base)
    record["pipe_hydraulic_preselection"] = base
    record["target_velocity_m_s"] = effective_target_velocity
    wall_was_missing = finite_number(
        record.get("selected_wall_thickness_mm")
    ) is None
    if wall_was_missing:
        record["selected_wall_thickness_mm"] = (
            PIPE_PRESELECTION_WALL_THICKNESS_MM
        )
    chain.append(
        lineage(
            target_field="target_velocity_m_s",
            value=effective_target_velocity,
            unit="m/s",
            source_file=source_file,
            source_sha256=source_sha256,
            object_type="pipe_hydraulic_preselector",
            object_id=object_id,
            source_field=(
                "flow_m3_h,density_kg_m3,dynamic_viscosity_mpa_s,phase"
            ),
            source_path=(
                f"pipe_hydraulic_preselection:"
                f"{base['preselection_sha256']}"
            ),
            transform=(
                "pressure_gradient_and_velocity_required_id_to_"
                "matcher_effective_velocity"
            ),
            formula="vEffective=4*(Q/3600)/(pi*Dcontrolling^2)",
            substitution=(
                f"4*({flow_m3_h:.12g}/3600)/(pi*"
                f"({controlling_required_id_mm:.12g}/1000)^2)"
            ),
            evidence_class="J",
            result_status=status,
            evidence_scope="PROGRAMMATIC_PRELIMINARY_PIPE_SELECTION",
            promotion_cap="TYPE_SCREENING",
            warning=(
                "The 50 kPa/100m screen is a registered project "
                "preselection threshold, not a national-code limit. "
                + (
                    "Two-phase pressure gradient remains an advisory "
                    "homogeneous proxy only."
                    if two_phase
                    else (
                        "Whole-line length, fittings and project pressure-drop "
                        "acceptance remain open."
                    )
                )
            ),
        )
    )
    if wall_was_missing:
        chain.append(
            lineage(
                target_field="selected_wall_thickness_mm",
                value=PIPE_PRESELECTION_WALL_THICKNESS_MM,
                unit="mm",
                source_file=source_file,
                source_sha256=source_sha256,
                object_type="pipe_hydraulic_preselector",
                object_id=object_id,
                source_field="registered_preselection_wall_assumption",
                source_path=(
                    f"pipe_hydraulic_preselection:"
                    f"{base['preselection_sha256']}"
                ),
                transform="registered_preliminary_wall_assumption",
                formula="t_preselection=4 mm",
                substitution="4",
                evidence_class="J",
                result_status="PROVISIONAL_WALL_FOR_DN_PRESELECTION",
                evidence_scope=(
                    "PROGRAMMATIC_PRELIMINARY_PIPE_SELECTION"
                ),
                promotion_cap="TYPE_SCREENING",
                warning=(
                    "The 4 mm wall is used only to map hydraulic ID to a "
                    "catalog DN candidate. The final metric wall is selected "
                    "and hydraulically rechecked downstream."
                ),
            )
        )
    return base


def apply_two_phase_viscosity_screening(
    *,
    record: dict[str, Any],
    chain: list[dict[str, Any]],
    source_file: Path,
    source_sha256: str,
    object_id: str,
    source_map: dict[str, Any],
) -> None:
    """Add a non-physical, conservative viscosity proxy for line screening.

    Aspen correctly exposes separate liquid and vapor MUMX values for a
    two-phase material stream.  The selector must preserve both physical
    properties and must not pretend that Aspen supplied one mixture viscosity.
    For preliminary Reynolds/friction screening only, use the larger phase
    viscosity and keep formal two-phase hydraulics as an explicit open gate.
    """

    phase = str(record.get("phase") or "").strip().casefold()
    if phase not in {
        "two_phase",
        "two-phase",
        "two phase",
        "mixed",
        "multiphase",
    }:
        return
    if finite_number(record.get("dynamic_viscosity_mpa_s")) is not None:
        return
    liquid = finite_number(record.get("liquid_dynamic_viscosity_mpa_s"))
    vapor = finite_number(record.get("vapor_dynamic_viscosity_mpa_s"))
    if liquid is None or liquid <= 0.0 or vapor is None or vapor <= 0.0:
        return
    screening_value = max(liquid, vapor)
    source_paths = {
        field: (source_map.get(field) or {}).get("source_path")
        for field in (
            "liquid_dynamic_viscosity_mpa_s",
            "vapor_dynamic_viscosity_mpa_s",
        )
    }
    basis = {
        "status": "CONSERVATIVE_TWO_PHASE_SCREENING_PROXY",
        "not_an_aspen_mixture_property": True,
        "formula": "mu_screen=max(mu_liquid_Aspen_MUMX,mu_vapor_Aspen_MUMX)",
        "liquid_dynamic_viscosity_mpa_s": liquid,
        "vapor_dynamic_viscosity_mpa_s": vapor,
        "screening_dynamic_viscosity_mpa_s": screening_value,
        "source_paths": source_paths,
        "formal_gate": (
            "two-phase flow-regime, holdup, slip, flashing and pressure-drop "
            "correlation required before formal issue"
        ),
    }
    record["dynamic_viscosity_mpa_s"] = screening_value
    record["two_phase_viscosity_screening_basis"] = basis
    chain.append(
        lineage(
            target_field="dynamic_viscosity_mpa_s",
            value=screening_value,
            unit="mPa*s",
            source_file=source_file,
            source_sha256=source_sha256,
            object_type="two_phase_stream_properties",
            object_id=object_id,
            source_field=(
                "liquid_dynamic_viscosity_mpa_s,"
                "vapor_dynamic_viscosity_mpa_s"
            ),
            source_path=json.dumps(
                source_paths,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ),
            transform="conservative_max_phase_viscosity_for_pipe_screening",
            formula="mu_screen=max(mu_L,mu_V)",
            substitution=f"max({liquid:.12g},{vapor:.12g})",
            evidence_class="J",
            result_status="DERIVED_TWO_PHASE_SCREENING_PROXY",
            evidence_scope="PROGRAMMATIC_PRELIMINARY_PIPE_SELECTION",
            promotion_cap="TYPE_SCREENING",
            warning=(
                "This numeric value is a conservative program screening proxy, "
                "not an Aspen two-phase mixture property; both phase MUMX values "
                "remain separately preserved and formal two-phase hydraulics is open."
            ),
        )
    )


def piping_medium_name(stream: dict[str, Any]) -> tuple[str | None, str | None, list[str]]:
    """Build a deterministic medium label from a closed Aspen composition."""

    composition = stream.get("composition")
    if isinstance(composition, list) and composition:
        positive = [
            item for item in composition
            if isinstance(item, dict)
            and float(item.get("fraction", 0.0)) > 1.0e-12
            and str(item.get("component_id") or "").strip()
        ]
        if positive:
            positive.sort(key=lambda item: (-float(item["fraction"]), str(item["component_id"])))
            basis = str(positive[0].get("basis") or "")
            basis_label = "mol%" if basis == "mole_fraction" else "mass%"
            parts = [
                f"{str(item['component_id']).strip()} ({float(item['fraction']) * 100.0:.6g} {basis_label})"
                for item in positive
            ]
            sources = sorted({
                str(item.get("source_path") or "")
                for item in positive
                if str(item.get("source_path") or "").strip()
            })
            return " + ".join(parts), basis, sources
    dominant = str(stream.get("dominant_components") or "").strip()
    if dominant:
        return dominant, "aspen_dominant_components", []
    return None, None, []


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()


@functools.lru_cache(maxsize=1)
def _load_original_verified_pipe_standard_store() -> dict[str, Any]:
    """Load only QA-promoted pipe records from the immutable local store."""

    try:
        authority_verification = database_authority.verify_consumer_database(
            PIPE_STANDARD_CONSUMER_ID,
            PACKAGE_ROOT,
        )
    except database_authority.DatabaseAuthorityError as exc:
        raise RuntimeError(f"BLOCKED_PIPE_DATABASE_AUTHORITY:{exc}") from exc
    verified_database_path = (
        PACKAGE_ROOT / Path(authority_verification["relative_path"])
    )
    if verified_database_path != PIPE_STANDARD_DB_PATH:
        raise RuntimeError("BLOCKED_PIPE_DATABASE_REGISTRY_PATH_DRIFT")
    manifest = json.loads(PIPE_STANDARD_MANIFEST_PATH.read_text(encoding="utf-8"))
    database_sha256 = str(authority_verification["sha256"])
    expected_sha256 = str(manifest.get("sqlite_sha256") or "").upper()
    if database_sha256 != expected_sha256:
        raise RuntimeError("BLOCKED_PIPE_STANDARD_STORE_HASH_MISMATCH")
    connection = sqlite3.connect(
        f"file:{PIPE_STANDARD_DB_PATH.as_posix()}?mode=ro",
        uri=True,
    )
    connection.row_factory = sqlite3.Row
    try:
        dataset_ids = (
            "gbt1048_nominal_pressure_series",
            "gbt17395_pipe_dimensions_weights",
        )
        datasets = {
            str(row["dataset_id"]): dict(row)
            for row in connection.execute(
                "SELECT * FROM datasets WHERE dataset_id IN (?, ?)",
                dataset_ids,
            )
        }
        for dataset_id in dataset_ids:
            dataset = datasets.get(dataset_id)
            if not dataset:
                raise RuntimeError(
                    f"BLOCKED_PIPE_STANDARD_DATASET_MISSING:{dataset_id}"
                )
            if (
                dataset.get("qa_status") != "VERIFIED"
                or dataset.get("reuse_class") != "DIRECT_REUSE_VERIFIED"
                or dataset.get("lifecycle_state") != "CURRENT"
            ):
                raise RuntimeError(
                    f"BLOCKED_PIPE_STANDARD_DATASET_NOT_PROMOTED:{dataset_id}"
                )

        pn_records = [
            dict(row)
            for row in connection.execute(
                """
                SELECT record_id, raw_value, normalized_number, physical_page,
                       source_table, source_row_label, source_column_label,
                       source_sha256, record_sha256, standard_id,
                       standard_version, qa_status, reuse_class
                FROM standard_records
                WHERE dataset_id = ?
                  AND raw_value LIKE 'PN%'
                  AND qa_status = 'VERIFIED'
                  AND reuse_class = 'DIRECT_REUSE_VERIFIED'
                ORDER BY normalized_number
                """,
                ("gbt1048_nominal_pressure_series",),
            )
        ]
        wall_records: list[dict[str, Any]] = []
        for row in connection.execute(
            """
            SELECT record_id, physical_page, source_table, source_row_label,
                   source_column_label, source_sha256, record_sha256,
                   standard_id, standard_version, normalized_number,
                   source_payload_json, qa_status, reuse_class
            FROM standard_records
            WHERE dataset_id = ?
              AND qa_status = 'VERIFIED'
              AND reuse_class = 'DIRECT_REUSE_VERIFIED'
            """,
            ("gbt17395_pipe_dimensions_weights",),
        ):
            payload = json.loads(str(row["source_payload_json"] or "{}"))
            try:
                outer_diameter = float(payload["nominal_outer_diameter_mm"])
                wall_thickness = float(payload["nominal_wall_thickness_mm"])
            except (KeyError, TypeError, ValueError):
                continue
            wall_records.append({
                **dict(row),
                "outer_diameter_mm": outer_diameter,
                "wall_thickness_mm": wall_thickness,
                "outer_diameter_series": str(
                    payload.get("outer_diameter_series") or ""
                ),
                "wall_thickness_recommended": (
                    str(payload.get("wall_thickness_recommended"))
                    .strip()
                    .casefold()
                    == "true"
                ),
                "unit_mass_kg_m": float(row["normalized_number"]),
                "table_id": payload.get("table_id"),
                "terminal_class": payload.get("terminal_class"),
            })
    finally:
        connection.close()
    if not pn_records or not wall_records:
        raise RuntimeError("BLOCKED_PIPE_STANDARD_STORE_EMPTY")
    return {
        "build_id": manifest.get("build_id"),
        "database_path": str(PIPE_STANDARD_DB_PATH),
        "database_sha256": database_sha256,
        "database_authority_registry_path": str(DATABASE_AUTHORITY_REGISTRY_PATH),
        "database_authority_registry_sha256": sha256_file(
            DATABASE_AUTHORITY_REGISTRY_PATH
        ),
        "database_authority_status": authority_verification["status"],
        "database_scope_status": authority_verification["scope_status"],
        "manifest_path": str(PIPE_STANDARD_MANIFEST_PATH),
        "manifest_sha256": sha256_file(PIPE_STANDARD_MANIFEST_PATH),
        "datasets": datasets,
        "pn_records": pn_records,
        "wall_records": wall_records,
    }


def load_verified_pipe_standard_store() -> dict[str, Any]:
    """Explicit backend data route; original calculation consumers remain unchanged."""
    from projected_standard_store import load_pipe_store
    return load_pipe_store(PACKAGE_ROOT)


def _match_value(match_result: dict[str, Any], field: str) -> Any:
    for container_name in (
        "derived_parameters",
        "effective_normalized_input",
        "normalized_input",
    ):
        container = match_result.get(container_name)
        if isinstance(container, dict) and container.get(field) not in (None, ""):
            return container[field]
    model = match_result.get("model_recommendation")
    leading = model.get("leading_candidate") if isinstance(model, dict) else None
    specification = leading.get("specification") if isinstance(leading, dict) else None
    item = specification.get(field) if isinstance(specification, dict) else None
    if isinstance(item, dict) and item.get("value") not in (None, ""):
        return item["value"]
    return None


def _pipe_dn_standard_catalog_record(
    match_result: dict[str, Any],
) -> dict[str, Any] | None:
    """Return the exact GB/T 12459 record used for the hydraulic DN candidate.

    The matcher emits one calculation row for DN and another for the catalog
    outer diameter. Both rows carry the same source-cell record. Retaining that
    record here prevents the later GB/T 17395 metric OD/wall lookup from being
    misrepresented as one combined standard designation.
    """

    calculations = match_result.get("calculations")
    if not isinstance(calculations, list):
        return None
    for calculation in calculations:
        if not isinstance(calculation, dict):
            continue
        if (
            calculation.get("calculation_id") != "pipe_standard_dn_selection"
            or calculation.get("target_field") != "selected_dn"
        ):
            continue
        source_record = calculation.get("standard_catalog_record")
        if not isinstance(source_record, dict):
            return None
        record = dict(source_record)
        record["selected_dn"] = finite_number(calculation.get("value"))
        record["record_binding_sha256"] = _canonical_sha256(record)
        return record
    return None


@functools.lru_cache(maxsize=16)
def _pipe_product_standard_evidence(
    standard_identity: str,
) -> dict[str, Any]:
    """Bind a product-standard identity to the portable source inventory.

    The inventory proves only that a source was catalogued.  It does not prove
    that a material grade, dimensions, temperature range, or product scope is
    applicable to the selected line, so this evidence can never close the
    formal product-standard gate.
    """

    portable_path = (
        "knowledge_graph/selection_learning_graph_20260622/"
        "standard_source_inventory.csv"
    )
    identity = str(standard_identity or "").strip()
    evidence: dict[str, Any] = {
        "schema": "pipe-product-standard-evidence-v1",
        "standard_identity": identity,
        "source_status": "PORTABLE_SOURCE_INVENTORY_ENTRY_MISSING",
        "inventory_path": portable_path,
        "inventory_sha256": None,
        "entry": None,
        "entry_sha256": None,
        "product_scope_verified": False,
        "exact_table_page_verified": False,
        "evidence_class": "J",
        "promotion_cap": "TYPE_SCREENING",
        "warning": (
            "标准号仅为程序初选身份候选；未完成产品范围、材料牌号、尺寸、公差"
            "及适用温压的逐条核验，不得作为正式采购或制造依据。"
        ),
    }
    if not STANDARD_SOURCE_INVENTORY_PATH.is_file():
        evidence["source_status"] = "PORTABLE_SOURCE_INVENTORY_FILE_MISSING"
        evidence["evidence_sha256"] = _canonical_sha256(evidence)
        return evidence
    evidence["inventory_sha256"] = sha256_file(
        STANDARD_SOURCE_INVENTORY_PATH
    )
    normalized_identity = re.sub(
        r"[^0-9A-Z]",
        "",
        identity.upper(),
    )
    matched_entry: dict[str, Any] | None = None
    with STANDARD_SOURCE_INVENTORY_PATH.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        for row in csv.DictReader(handle):
            row_text = " ".join(str(value or "") for value in row.values())
            normalized_row = re.sub(r"[^0-9A-Z]", "", row_text.upper())
            if normalized_identity and normalized_identity in normalized_row:
                matched_entry = {
                    str(key): str(value or "")
                    for key, value in row.items()
                }
                break
    if matched_entry is not None:
        evidence["source_status"] = (
            "CATALOG_ENTRY_ONLY_NOT_SCOPE_VERIFIED"
        )
        evidence["entry"] = matched_entry
        evidence["entry_sha256"] = _canonical_sha256(matched_entry)
        evidence["evidence_class"] = "S1_S2_CATALOG_ENTRY"
    evidence["evidence_sha256"] = _canonical_sha256(evidence)
    return evidence


def _programmatic_pipe_material(
    medium_name: str,
    preliminary_material: str,
    design_temperature_c: float,
) -> dict[str, Any]:
    text = f"{medium_name} {preliminary_material}".casefold()
    if any(
        marker in text
        for marker in (
            "耐蚀", "316", "chloride", "hcl", "盐酸", "氯化", "氯离子",
            "强酸", "强碱", "洁净", "卫生", "pharma", "sanitary",
        )
    ):
        return {
            "code": "SS316L",
            "material": (
                "S31603（022Cr17Ni12Mo2）不锈钢无缝钢管"
                "（GB/T 14976-2025 产品路线，程序初选）"
            ),
            "material_grade": "S31603（022Cr17Ni12Mo2）",
            "product_standard": "GB/T 14976-2025",
            "product_standard_identity_candidate": True,
            "product_standard_scope_established": False,
            "product_standard_evidence": (
                _pipe_product_standard_evidence("GB/T 14976-2025")
            ),
            "corrosion_allowance_mm": 0.0,
            "roughness_mm": 0.015,
            "wall_table_preference": "table3",
            "selection_basis": "corrosive_or_clean_service_marker",
        }
    if design_temperature_c <= -20.0 or "低温" in text:
        return {
            "code": "LT09MND",
            "material": "09MnD低温钢无缝钢管（程序初选；产品标准与冲击要求待复核）",
            "material_grade": "09MnD",
            "product_standard": "产品标准待项目材料规范确认",
            "product_standard_identity_candidate": False,
            "product_standard_scope_established": False,
            "product_standard_evidence": (
                _pipe_product_standard_evidence("")
            ),
            "corrosion_allowance_mm": 1.5,
            "roughness_mm": 0.045,
            "wall_table_preference": "table1",
            "selection_basis": "low_temperature_route",
        }
    if design_temperature_c >= 400.0 or "耐热" in text:
        return {
            "code": "AS15CRMO",
            "material": "15CrMo合金钢无缝钢管（程序初选；产品标准与高温许用应力待复核）",
            "material_grade": "15CrMo",
            "product_standard": "产品标准待项目材料规范确认",
            "product_standard_identity_candidate": False,
            "product_standard_scope_established": False,
            "product_standard_evidence": (
                _pipe_product_standard_evidence("")
            ),
            "corrosion_allowance_mm": 1.5,
            "roughness_mm": 0.045,
            "wall_table_preference": "table1",
            "selection_basis": "high_temperature_route",
        }
    return {
        "code": "CS20",
        "material": (
            "20钢无缝钢管（GB/T 8163-2018 身份候选，"
            "产品范围未核验，程序初选）"
        ),
        "material_grade": "20钢",
        "product_standard": "GB/T 8163-2018",
        "product_standard_identity_candidate": True,
        "product_standard_scope_established": False,
        "product_standard_evidence": (
            _pipe_product_standard_evidence("GB/T 8163-2018")
        ),
        "corrosion_allowance_mm": 1.5,
        "roughness_mm": 0.045,
        "wall_table_preference": "table1",
        "selection_basis": "registered_carbon_steel_economic_baseline",
    }


def _pipe_manufacturing_route(
    material: dict[str, Any],
    selected_dn: int,
) -> dict[str, Any]:
    """Choose a concrete manufacturing route without inventing a standard."""

    if selected_dn < 600:
        product_standard_scope_established = bool(
            material.get("product_standard_scope_established")
        )
        return {
            **material,
            "large_bore_welded_route": False,
            "equipment_type": "无缝钢制工艺管道",
            "manufacturing_method": "无缝钢管",
            "route_code": "SEAMLESS",
            "material_route_label": material["material_grade"],
            "screening_weld_factor": 1.0,
            "product_standard_scope_established": (
                product_standard_scope_established
            ),
            "manufacturing_open_gates": (
                []
                if product_standard_scope_established
                else [
                    "pipe_product_standard_scope_verification",
                    "pipe_product_standard_and_dimensional_tolerances",
                ]
            ),
        }
    return {
        **material,
        "code": "LSAW-PLATE-GRADE-OPEN",
        "large_bore_welded_route": True,
        "equipment_type": "直缝埋弧焊钢制工艺管道",
        "material": (
            "钢板卷制直缝埋弧焊工艺管道（程序制造路线候选；"
            "板材牌号待项目材料规范批准）"
        ),
        "material_grade": "OPEN_PROJECT_PLATE_GRADE_GATE",
        "material_route_label": "碳钢板材卷制焊管路线",
        "product_standard": (
            "OPEN_PROJECT_WELDED_PIPE_PRODUCT_SPECIFICATION_GATE"
        ),
        "product_standard_identity_candidate": False,
        "product_standard_evidence": (
            _pipe_product_standard_evidence("")
        ),
        "manufacturing_method": (
            "钢板卷制 + 纵向对接焊缝 + 双面埋弧焊候选"
        ),
        "route_code": "LSAW_PLATE_ROLLED",
        "screening_weld_factor": 0.85,
        "product_standard_scope_established": False,
        "selection_basis": (
            "registered_large_bore_DN600_and_above_welded_route"
        ),
        "manufacturing_open_gates": [
            "pipe_product_standard_scope_verification",
            "project_plate_material_grade",
            "welding_filler_metal",
            "code_weld_joint_efficiency",
            "forming_and_postweld_heat_treatment",
            "longitudinal_seam_NDE_method_ratio_and_acceptance_level",
            "welded_pipe_product_standard_and_dimensional_tolerances",
        ],
    }


def _select_verified_pipe_wall(
    store: dict[str, Any],
    *,
    initial_outer_diameter_mm: float,
    minimum_wall_thickness_mm: float,
    required_inner_diameter_mm: float,
    table_preference: str,
) -> dict[str, Any]:
    tolerance = max(0.5, initial_outer_diameter_mm * 0.005)
    candidates: list[dict[str, Any]] = []
    for record in store["wall_records"]:
        outer_diameter = float(record["outer_diameter_mm"])
        wall_thickness = float(record["wall_thickness_mm"])
        if abs(outer_diameter - initial_outer_diameter_mm) > tolerance:
            continue
        if wall_thickness + 1.0e-9 < minimum_wall_thickness_mm:
            continue
        if outer_diameter - 2.0 * wall_thickness + 1.0e-9 < required_inner_diameter_mm:
            continue
        table_id = str(record.get("table_id") or "").casefold()
        table_penalty = 0 if table_preference in table_id else 1
        candidates.append({
            **record,
            "_sort": (
                table_penalty,
                0 if record.get("wall_thickness_recommended") else 1,
                abs(outer_diameter - initial_outer_diameter_mm),
                wall_thickness,
            ),
        })
    if not candidates:
        raise RuntimeError(
            "BLOCKED_NO_GBT17395_WALL_COMBINATION_FOR_REQUIRED_ID"
        )
    selected = min(candidates, key=lambda item: item["_sort"])
    selected.pop("_sort", None)
    return selected


def _select_verified_pn(
    store: dict[str, Any],
    design_pressure_mpa_gauge: float,
) -> dict[str, Any]:
    required_pn = max(16.0, design_pressure_mpa_gauge * 10.0)
    candidates = [
        record
        for record in store["pn_records"]
        if float(record["normalized_number"]) + 1.0e-9 >= required_pn
    ]
    if not candidates:
        raise RuntimeError("BLOCKED_DESIGN_PRESSURE_EXCEEDS_GBT1048_PN_SERIES")
    selected = min(candidates, key=lambda item: float(item["normalized_number"]))
    return {
        **selected,
        "selector_required_pn_number": required_pn,
        "engineering_policy_floor_pn": 16.0,
        "pressure_to_pn_screening_factor": 10.0,
        "selection_provenance": "SELECTOR_RULE/PN_SERIES_MAPPING_ONLY",
    }


def build_programmatic_pipe_specification(
    *,
    stream_id: str,
    record: dict[str, Any],
    match_result: dict[str, Any],
    source_file: Path,
    source_sha256: str,
) -> dict[str, Any]:
    """Build one concrete, auditable preliminary line specification."""

    viscosity_diagnostic = (
        dict(record.get("viscosity_fallback_diagnostic") or {})
        if isinstance(record.get("viscosity_fallback_diagnostic"), dict)
        else {}
    )
    internal_viscosity_estimate = (
        viscosity_diagnostic.get("internal_correlation_used") is True
    )
    selected_dn_value = finite_number(_match_value(match_result, "selected_dn"))
    initial_outer_diameter = finite_number(
        _match_value(match_result, "selected_outer_diameter_mm")
    )
    initial_wall = finite_number(
        _match_value(match_result, "selected_wall_thickness_mm")
    )
    required_inner_diameter = finite_number(
        _match_value(match_result, "required_inner_diameter_mm")
    )
    matcher_design_pressure = finite_number(
        _match_value(match_result, "design_pressure_mpa")
    )
    operating_pressure = finite_number(record.get("operating_pressure_mpa"))
    pressure_basis = str(record.get("pressure_basis") or "").strip().casefold()
    atmospheric_pressure = finite_number(record.get("atmospheric_pressure_mpa"))
    if atmospheric_pressure is None or atmospheric_pressure <= 0.0:
        atmospheric_pressure = 0.101325
    pressure_regime = (
        dict(record.get("pipe_pressure_regime_screening") or {})
        if isinstance(record.get("pipe_pressure_regime_screening"), dict)
        else {}
    )
    signed_vacuum_margin_kpa = finite_number(
        pressure_regime.get("signed_vacuum_margin_kpa")
    )
    if signed_vacuum_margin_kpa is None and (
        pressure_basis == "absolute"
        and operating_pressure is not None
    ):
        signed_vacuum_margin_kpa = (
            atmospheric_pressure - operating_pressure
        ) * 1000.0
    vacuum_margin_kpa = (
        max(0.0, signed_vacuum_margin_kpa)
        if signed_vacuum_margin_kpa is not None
        else None
    )
    vacuum_threshold_kpa = finite_number(
        pressure_regime.get("vacuum_threshold_kpa")
    )
    if vacuum_threshold_kpa is None:
        vacuum_threshold_kpa = max(
            5.0,
            0.05 * atmospheric_pressure * 1000.0,
        )
    external_pressure_branch = bool(
        pressure_regime.get("external_pressure_branch")
    )
    if not pressure_regime:
        external_pressure_branch = (
            vacuum_margin_kpa is not None
            and vacuum_margin_kpa >= vacuum_threshold_kpa
        )
    near_atmospheric_screening = bool(
        pressure_regime.get("near_atmospheric_screening")
    )
    if not pressure_regime and signed_vacuum_margin_kpa is not None:
        near_atmospheric_screening = (
            abs(signed_vacuum_margin_kpa) < vacuum_threshold_kpa
        )
    external_design_pressure_mpa: float | None = (
        atmospheric_pressure if external_pressure_branch else None
    )
    design_pressure = (
        matcher_design_pressure
        if matcher_design_pressure is not None
        else finite_number(record.get("design_pressure_mpa"))
    )
    if (
        (design_pressure is None or design_pressure <= 0.0)
        and pressure_basis == "absolute"
        and operating_pressure is not None
        and (external_pressure_branch or near_atmospheric_screening)
    ):
        design_pressure = 0.1
    design_temperature = finite_number(
        _match_value(match_result, "design_temperature_c")
    )
    preliminary_material = str(_match_value(match_result, "material") or "")
    dn_standard_record = _pipe_dn_standard_catalog_record(match_result)
    required = {
        "selected_dn": selected_dn_value,
        "initial_outer_diameter_mm": initial_outer_diameter,
        "initial_wall_thickness_mm": initial_wall,
        "required_inner_diameter_mm": required_inner_diameter,
        "design_pressure_mpa_gauge": design_pressure,
        "design_temperature_c": design_temperature,
    }
    if any(value is None for value in required.values()):
        return {
            "schema": "programmatic-pipe-specification-v1",
            "status": "BLOCKED_PIPE_SPECIFICATION_INPUTS",
            "deterministic": True,
            "llm_used": False,
            "stream_id": stream_id,
            "missing_inputs": sorted(
                field for field, value in required.items() if value is None
            ),
        }
    assert selected_dn_value is not None
    assert initial_outer_diameter is not None
    assert initial_wall is not None
    assert required_inner_diameter is not None
    assert design_pressure is not None
    assert design_temperature is not None
    if design_pressure <= 0.0:
        return {
            "schema": "programmatic-pipe-specification-v1",
            "status": "BLOCKED_EXTERNAL_PRESSURE_BRANCH",
            "deterministic": True,
            "llm_used": False,
            "stream_id": stream_id,
            "design_pressure_mpa_gauge": design_pressure,
        }

    store = load_verified_pipe_standard_store()
    selected_dn = int(round(selected_dn_value))
    material = _pipe_manufacturing_route(
        _programmatic_pipe_material(
            str(record.get("medium_name") or ""),
            preliminary_material,
            design_temperature,
        ),
        selected_dn,
    )
    corrosion_allowance = float(material["corrosion_allowance_mm"])
    allowable_stress_mpa = 120.0
    weld_factor = float(material["screening_weld_factor"])
    pressure_wall_mm = (
        design_pressure
        * initial_outer_diameter
        / (2.0 * allowable_stress_mpa * weld_factor + design_pressure)
    )
    minimum_preliminary_wall = max(
        initial_wall,
        pressure_wall_mm + corrosion_allowance,
    )
    wall = _select_verified_pipe_wall(
        store,
        initial_outer_diameter_mm=initial_outer_diameter,
        minimum_wall_thickness_mm=minimum_preliminary_wall,
        required_inner_diameter_mm=required_inner_diameter,
        table_preference=str(material["wall_table_preference"]),
    )
    pn = _select_verified_pn(store, design_pressure)
    outer_diameter = float(wall["outer_diameter_mm"])
    wall_thickness = float(wall["wall_thickness_mm"])
    inner_diameter = outer_diameter - 2.0 * wall_thickness
    od_match_tolerance_mm = max(0.5, initial_outer_diameter * 0.005)
    od_difference_mm = outer_diameter - initial_outer_diameter
    od_absolute_difference_mm = abs(od_difference_mm)
    od_exact_match = od_absolute_difference_mm <= 1.0e-9
    cross_standard_pairing = {
        "status": (
            "CROSS_STANDARD_EXACT_OD_MATCH_PRELIMINARY_ONLY"
            if od_exact_match
            else "CROSS_STANDARD_APPROXIMATE_OD_MATCH_PRELIMINARY_ONLY"
        ),
        "hydraulic_dn_candidate": selected_dn,
        "gbt12459_catalog_outer_diameter_mm": initial_outer_diameter,
        "gbt17395_metric_outer_diameter_mm": outer_diameter,
        "gbt17395_metric_wall_thickness_mm": wall_thickness,
        "signed_outer_diameter_difference_mm": od_difference_mm,
        "absolute_outer_diameter_difference_mm": od_absolute_difference_mm,
        "selector_tolerance_mm": od_match_tolerance_mm,
        "within_selector_tolerance": (
            od_absolute_difference_mm <= od_match_tolerance_mm + 1.0e-9
        ),
        "single_standard_combination_claim": False,
        "schedule_system": "NON_SCH_METRIC_OD_X_WALL",
        "formal_release_status": "BLOCKED",
        "manufacturing_route": material["route_code"],
        "gbt17395_usage_role": (
            "GEOMETRY_REFERENCE_ONLY"
            if material["large_bore_welded_route"]
            else "SEAMLESS_PIPE_DIMENSION_CANDIDATE"
        ),
        "gbt17395_product_scope_applicable": (
            not material["large_bore_welded_route"]
        ),
        "claim_boundary": (
            "GB/T 12459 applies to steel butt-welding seamless fittings and "
            "supplies only the referenced DN-to-D candidate cell here; it is "
            "not the pipe product standard. "
            + (
                "For this DN600-and-above welded route, the GB/T 17395 "
                "seamless-pipe cell is retained only as a preliminary metric "
                "OD/wall geometry reference; it is not applicable as the "
                "welded-pipe product standard. "
                if material["large_bore_welded_route"]
                else (
                    "GB/T 17395 independently supplies the seamless "
                    "steel-pipe metric OD/wall/weight candidate. "
                )
            )
            + (
                "The separated records are not one standard-issued pipe "
                "DN/OD/wall or Schedule combination."
            )
        ),
    }

    flow_m3_h = finite_number(record.get("flow_m3_h"))
    density_kg_m3 = finite_number(record.get("density_kg_m3"))
    viscosity_mpa_s = finite_number(record.get("dynamic_viscosity_mpa_s"))
    phase_text = str(record.get("phase") or "").strip().casefold()
    two_phase_screening = phase_text in {
        "two_phase",
        "two-phase",
        "two phase",
        "mixed",
        "multiphase",
    }
    two_phase_viscosity_basis = record.get(
        "two_phase_viscosity_screening_basis"
    )
    final_hydraulic = (
        _pipe_hydraulic_screening_metrics(
            flow_m3_h=flow_m3_h,
            inner_diameter_mm=inner_diameter,
            density_kg_m3=density_kg_m3,
            dynamic_viscosity_mpa_s=viscosity_mpa_s,
            roughness_mm=float(material["roughness_mm"]),
        )
        if flow_m3_h is not None and flow_m3_h > 0.0
        else {
            "status": "BLOCKED_MISSING_FLOW",
            "actual_velocity_m_s": None,
            "reynolds_number": None,
            "darcy_friction_factor": None,
            "friction_branch": "blocked_missing_flow",
            "pressure_gradient_kpa_per_100m": None,
        }
    )
    actual_velocity = finite_number(
        final_hydraulic.get("actual_velocity_m_s")
    )
    reynolds_number = finite_number(
        final_hydraulic.get("reynolds_number")
    )
    darcy_friction_factor = finite_number(
        final_hydraulic.get("darcy_friction_factor")
    )
    pressure_gradient_kpa_100m = finite_number(
        final_hydraulic.get("pressure_gradient_kpa_per_100m")
    )
    friction_branch = str(
        final_hydraulic.get("friction_branch")
        or "blocked_missing_flow"
    )
    phase_velocity_target = PIPE_PHASE_VELOCITY_TARGET_M_S.get(
        matcher.canonical_phase(record.get("phase")) or "unknown",
        1.5,
    )
    final_velocity_within_screen = (
        actual_velocity is not None
        and actual_velocity <= phase_velocity_target + 1.0e-9
    )
    final_gradient_within_screen = (
        pressure_gradient_kpa_100m is not None
        and pressure_gradient_kpa_100m
        <= PIPE_PRESSURE_GRADIENT_SCREEN_KPA_PER_100M + 1.0e-9
    )
    if two_phase_screening:
        friction_branch = (
            "homogeneous_two_phase_preliminary_screening:"
            + friction_branch
        )
        hydraulic_status = (
            "ADVISORY_HOMOGENEOUS_TWO_PHASE_PROXY_"
            "FORMAL_GATE_OPEN"
        )
        hydraulic_acceptance_status = (
            "NOT_EVALUATED_TWO_PHASE_FORMAL_GATE_OPEN"
        )
    elif pressure_gradient_kpa_100m is None:
        hydraulic_status = str(final_hydraulic["status"])
        hydraulic_acceptance_status = (
            "NOT_EVALUATED_MISSING_DENSITY_OR_VISCOSITY"
        )
    elif not (
        final_velocity_within_screen
        and final_gradient_within_screen
    ):
        raise RuntimeError(
            "BLOCKED_FINAL_WALL_HYDRAULIC_SCREEN:"
            f"velocity={actual_velocity}:"
            f"gradient={pressure_gradient_kpa_100m}"
        )
    elif internal_viscosity_estimate:
        friction_branch = (
            "internal_correlation_viscosity_warning:"
            + friction_branch
        )
        hydraulic_status = (
            "CALCULATED_PER_100M_WITH_INTERNAL_VISCOSITY_"
            "CORRELATION_WARNING"
        )
        hydraulic_acceptance_status = (
            "PRELIMINARY_SCREEN_ONLY_INTERNAL_VISCOSITY_WARNING"
        )
    else:
        hydraulic_status = (
            "CALCULATED_SINGLE_PHASE_PER_100M_WITHIN_PROGRAM_SCREEN"
        )
        hydraulic_acceptance_status = (
            "PRELIMINARY_SINGLE_PHASE_PROGRAM_SCREEN_ONLY"
        )

    pn_value = float(pn["normalized_number"])
    pn_text = f"PN{pn_value:g}"
    wall_series = (
        f"GB/T 17395-2024 外径系列"
        f"{wall.get('outer_diameter_series') or '（公制）'}；"
        f"名义OD×t=φ{outer_diameter:g}×{wall_thickness:g} mm；"
        "non-SCH（程序初选）"
    )
    piping_class_candidate_code = (
        f"{material['code']}-{pn_text}-BW-CA{corrosion_allowance:g}"
    )
    if design_temperature < 5.0:
        insulation_spec = (
            "50 mm硬质聚氨酯保冷层+0.6 mm铝合金外护（程序初选）"
        )
        heat_tracing_spec = (
            "自限温电伴热10 W/m（程序初选；介质凝固点与最低环境温度待复核）"
        )
    elif design_temperature <= 60.0:
        insulation_spec = "不设保温/保冷（程序初选）"
        heat_tracing_spec = "不设伴热（程序初选）"
    elif design_temperature <= 200.0:
        insulation_spec = (
            "50 mm岩棉保温层+0.6 mm铝合金外护（程序初选）"
        )
        heat_tracing_spec = "不设伴热（程序初选）"
    else:
        insulation_spec = (
            "80 mm硅酸铝纤维保温层+0.6 mm铝合金外护（程序初选）"
        )
        heat_tracing_spec = "不设伴热（程序初选）"
    protective_layer = (
        "酸洗钝化（程序初选）"
        if material["code"] == "SS316L"
        else "Sa2.5表面处理+环氧富锌底漆/环氧面漆（程序初选）"
    )

    hydraulic_basis = {
        "flow_m3_h": flow_m3_h,
        "density_kg_m3": density_kg_m3,
        "dynamic_viscosity_mpa_s": viscosity_mpa_s,
        "inner_diameter_mm": inner_diameter,
        "actual_velocity_m_s": actual_velocity,
        "reynolds_number": reynolds_number,
        "darcy_friction_factor": darcy_friction_factor,
        "friction_branch": friction_branch,
        "roughness_mm": material["roughness_mm"],
        "pressure_gradient_kpa_per_100m": pressure_gradient_kpa_100m,
        "status": hydraulic_status,
        "hydraulic_acceptance_status": hydraulic_acceptance_status,
        "phase_velocity_screen_m_s": phase_velocity_target,
        "final_velocity_within_program_screen": (
            final_velocity_within_screen
        ),
        "pressure_gradient_screen_limit_kpa_per_100m": (
            PIPE_PRESSURE_GRADIENT_SCREEN_KPA_PER_100M
        ),
        "pressure_gradient_limit_role": (
            "PROJECT_PRELIMINARY_ADVISORY_NOT_CODE_ACCEPTANCE"
            if two_phase_screening
            else "PROJECT_PRELIMINARY_SCREEN_NOT_NATIONAL_CODE_LIMIT"
        ),
        "final_pressure_gradient_within_program_screen": (
            final_gradient_within_screen
        ),
        "formal_hydraulic_acceptance": False,
        "pipe_hydraulic_preselection": record.get(
            "pipe_hydraulic_preselection"
        ),
        "length_basis": "per_100m; total line length not present in Aspen",
        "phase": record.get("phase"),
        "two_phase_screening": two_phase_screening,
        "two_phase_viscosity_screening_basis": two_phase_viscosity_basis,
        "viscosity_origin": (
            "INTERNAL_CORRELATION_ESTIMATE"
            if internal_viscosity_estimate
            else "ASPEN_OR_DIRECT_PROCESS_PROPERTY"
        ),
        "viscosity_fallback_diagnostic": viscosity_diagnostic,
        "formal_exclusions": [
            *(
                [
                    "aspen_or_lab_viscosity_confirmation",
                    "pure_component_coefficient_source_asset_verification",
                    "liquid_binary_interactions_or_high_pressure_gas_correction",
                ]
                if internal_viscosity_estimate
                else []
            ),
            *(
                [
                    "flow_regime_map",
                    "phase_holdup_and_slip",
                    "flashing_and_choking",
                    "slugging_and_vibration",
                    "validated_two_phase_pressure_drop_correlation",
                ]
                if two_phase_screening
                else []
            ),
        ],
    }
    hydraulic_sha256 = _canonical_sha256(hydraulic_basis)
    wall_basis = {
        "formula": "t=P*Do/(2*S*E+P)+CA",
        "design_pressure_mpa_gauge": design_pressure,
        "outer_diameter_mm": outer_diameter,
        "formula_outer_diameter_mm": initial_outer_diameter,
        "selected_metric_outer_diameter_mm": outer_diameter,
        "cross_standard_outer_diameter_difference_mm": od_difference_mm,
        "allowable_stress_mpa": allowable_stress_mpa,
        "weld_factor": weld_factor,
        "pressure_wall_mm_before_ca": pressure_wall_mm,
        "corrosion_allowance_mm": corrosion_allowance,
        "minimum_preliminary_wall_mm": minimum_preliminary_wall,
        "selected_wall_thickness_mm": wall_thickness,
        "status": (
            "INTERNAL_PRESSURE_FORMULA_SCREENING_ONLY_"
            "TWO_PHASE_HYDRAULICS_OPEN"
            if two_phase_screening
            else (
                (
                    "INTERNAL_SCREENING_EXTERNAL_PRESSURE_FORMAL_GATE_OPEN"
                    if external_pressure_branch
                    else "PRELIMINARY_INTERNAL_PRESSURE_SCREEN"
                )
                if wall_thickness + 1.0e-9 >= minimum_preliminary_wall
                else "FAIL_PRELIMINARY_SCREENING"
            )
        ),
        "external_pressure_branch": external_pressure_branch,
        "external_design_pressure_mpa": external_design_pressure_mpa,
        "near_atmospheric_screening": near_atmospheric_screening,
        "vacuum_margin_kpa": vacuum_margin_kpa,
        "vacuum_threshold_kpa": vacuum_threshold_kpa,
        "formal_exclusions": [
            "mill_negative_tolerance",
            "code_allowable_stress_at_temperature",
            "external_pressure",
            "cyclic_and_local_loads",
        ],
    }
    wall_sha256 = _canonical_sha256(wall_basis)
    designation = (
        "程序工程规格候选/程序初选候选（项目正式管道等级待批准）："
        f"{material['equipment_type']}；"
        f"材料路线={material['material_route_label']}；"
        f"制造路线={material['manufacturing_method']}；"
        f"水力DN候选DN{selected_dn}；"
        f"独立公制OD×t候选φ{outer_diameter:g}×{wall_thickness:g} mm"
        f"（non-SCH，跨标准OD差={od_difference_mm:+g} mm）；"
        f"PN系列候选{pn_text}；连接候选=对焊（BW）；"
        f"CA候选={corrosion_allowance:g} mm；"
        f"候选管道等级代码={piping_class_candidate_code}；"
        "正式管道等级=OPEN_PROJECT_AUTHORITY_GATE"
        + (
            f"，内压0.1 MPa(g)初筛/全真空外压"
            f"{external_design_pressure_mpa:g} MPa待校核"
            if external_pressure_branch
            and external_design_pressure_mpa is not None
            else ""
        )
        + (
            "，稳态Aspen工况未触发显著真空；事故真空仍待项目定义"
            if near_atmospheric_screening
            and not external_pressure_branch
            else ""
        )
        + (
            "，两相管均相黏度上限初筛，正式流型/持液率/滑移/压降待校核"
            if two_phase_screening
            else ""
        )
    )

    if internal_viscosity_estimate:
        designation += (
            "；强警告：黏度为程序内置关联式估算，非Aspen提取值；雷诺数与"
            "压降仅供单相初筛，必须由Aspen物性或实验数据复核"
        )

    fields: dict[str, dict[str, Any]] = {
        "equipment_type": {
            "value": material["equipment_type"],
            "unit": None,
        },
        "technical_specification": {"value": designation, "unit": None},
        "selected_dn": {
            "value": selected_dn,
            "unit": "DN",
            "state": "PROGRAM_PRELIMINARY_HYDRAULIC_DN_CANDIDATE",
            "evidence_class": "J",
            "promotion_cap": "TYPE_SCREENING",
            "provenance": (
                "STANDARD_CATALOG_RECORD/SELECTOR_RULE/"
                "HYDRAULIC_DN_CANDIDATE"
            ),
        },
        "hydraulic_dn_candidate": {
            "value": selected_dn,
            "unit": "DN",
            "state": "PROGRAM_PRELIMINARY_HYDRAULIC_DN_CANDIDATE",
            "evidence_class": "J",
            "promotion_cap": "TYPE_SCREENING",
            "provenance": (
                "STANDARD_CATALOG_RECORD/SELECTOR_RULE/"
                "HYDRAULIC_DN_CANDIDATE"
            ),
        },
        "dn_catalog_outer_diameter_mm": {
            "value": initial_outer_diameter,
            "unit": "mm",
            "state": "PROGRAM_PRELIMINARY_HYDRAULIC_DN_CANDIDATE",
            "evidence_class": "J",
            "promotion_cap": "TYPE_SCREENING",
            "provenance": "GB/T_12459_VERIFIED_DN_TO_D_RECORD",
        },
        "selected_outer_diameter_mm": {
            "value": outer_diameter,
            "unit": "mm",
            "state": "PROGRAM_PRELIMINARY_METRIC_OD_WALL_CANDIDATE",
            "evidence_class": "J",
            "promotion_cap": "TYPE_SCREENING",
            "provenance": (
                "GB/T_17395_VERIFIED_DIMENSION_RECORD/"
                "SELECTOR_RULE/METRIC_OD_WALL_CANDIDATE"
            ),
        },
        "selected_wall_thickness_mm": {
            "value": wall_thickness,
            "unit": "mm",
            "state": "PROGRAM_PRELIMINARY_METRIC_OD_WALL_CANDIDATE",
            "evidence_class": "J",
            "promotion_cap": "TYPE_SCREENING",
            "provenance": (
                "GB/T_17395_VERIFIED_DIMENSION_RECORD/"
                "SELECTOR_RULE/METRIC_OD_WALL_CANDIDATE"
            ),
        },
        "inner_diameter_mm": {"value": inner_diameter, "unit": "mm"},
        "wall_series": {
            "value": wall_series,
            "unit": None,
            "state": "PROGRAM_PRELIMINARY_METRIC_OD_WALL_CANDIDATE",
            "evidence_class": "J",
            "promotion_cap": "TYPE_SCREENING",
            "provenance": (
                "GB/T_17395_OUTER_DIAMETER_SERIES/"
                "NON_SCH_METRIC_OD_X_WALL"
            ),
        },
        "schedule_designation": {
            "value": "NON_SCH_METRIC_OD_X_WALL_PRELIMINARY",
            "unit": None,
            "state": "PROGRAM_PRELIMINARY_METRIC_OD_WALL_CANDIDATE",
            "evidence_class": "J",
            "promotion_cap": "TYPE_SCREENING",
            "provenance": "SELECTOR_RULE/NON_SCH_DECLARATION",
        },
        "outer_diameter_series": {
            "value": wall.get("outer_diameter_series") or None,
            "unit": None,
            "state": "PROGRAM_PRELIMINARY_METRIC_OD_WALL_CANDIDATE",
            "evidence_class": "J",
            "promotion_cap": "TYPE_SCREENING",
            "provenance": "GB/T_17395_VERIFIED_DIMENSION_RECORD",
        },
        "dn_od_approximation_mm": {
            "value": od_difference_mm,
            "unit": "mm",
            "state": cross_standard_pairing["status"],
            "evidence_class": "J",
            "promotion_cap": "TYPE_SCREENING",
            "provenance": "SELECTOR_RULE/CROSS_STANDARD_OD_DIFFERENCE",
        },
        "standard_combination_status": {
            "value": cross_standard_pairing["status"],
            "unit": None,
            "state": cross_standard_pairing["status"],
            "evidence_class": "J",
            "promotion_cap": "TYPE_SCREENING",
            "provenance": "SELECTOR_RULE/CROSS_STANDARD_PAIRING_BOUNDARY",
        },
        "material": {
            "value": material["material"],
            "unit": None,
            "provenance": "SELECTOR_RULE/ENGINEERING_MATERIAL_ROUTE_CANDIDATE",
        },
        "material_grade": {
            "value": material["material_grade"],
            "unit": None,
            "provenance": "SELECTOR_RULE/ENGINEERING_MATERIAL_ROUTE_CANDIDATE",
        },
        "material_route_candidate": {
            "value": material["material_route_label"],
            "unit": None,
            "state": "PROGRAM_PRELIMINARY_MATERIAL_ROUTE_CANDIDATE",
            "evidence_class": "J",
            "promotion_cap": "TYPE_SCREENING",
            "provenance": "SELECTOR_RULE/ENGINEERING_MATERIAL_ROUTE_CANDIDATE",
        },
        "manufacturing_method": {
            "value": material["manufacturing_method"],
            "unit": None,
            "state": "PROGRAM_PRELIMINARY_MANUFACTURING_ROUTE_CANDIDATE",
            "evidence_class": "J",
            "promotion_cap": "TYPE_SCREENING",
            "provenance": "SELECTOR_RULE/ENGINEERING_DEFAULT_CANDIDATE",
        },
        "product_standard": {
            "value": material["product_standard"],
            "unit": None,
            "state": (
                "PROGRAM_PRELIMINARY_STANDARD_IDENTITY_CANDIDATE"
                if material["product_standard_identity_candidate"]
                else "OPEN_FORMAL_EVIDENCE_GATE"
            ),
            "evidence_class": (
                "J"
                if material["product_standard_identity_candidate"]
                else "U"
            ),
            "promotion_cap": (
                "TYPE_SCREENING"
                if material["product_standard_identity_candidate"]
                else "NOT_PROMOTABLE"
            ),
            "provenance": (
                "SELECTOR_RULE/PORTABLE_SOURCE_INVENTORY_STANDARD_IDENTITY"
                if material["product_standard_identity_candidate"]
                else "PROJECT_MATERIAL_SPECIFICATION_REQUIRED"
            ),
            "product_scope_verified": False,
            "product_standard_evidence_sha256": material[
                "product_standard_evidence"
            ]["evidence_sha256"],
            "warning": material["product_standard_evidence"]["warning"],
        },
        "manufacturing_route_code": {
            "value": material["route_code"],
            "unit": None,
            "state": "PROGRAM_PRELIMINARY_MANUFACTURING_ROUTE_CANDIDATE",
            "evidence_class": "J",
            "promotion_cap": "TYPE_SCREENING",
            "provenance": "SELECTOR_RULE/DN_DEPENDENT_MANUFACTURING_ROUTE",
        },
        "connection_type": {
            "value": "对焊（BW）",
            "unit": None,
            "state": "PROGRAM_PRELIMINARY_CONNECTION_CANDIDATE",
            "evidence_class": "J",
            "promotion_cap": "TYPE_SCREENING",
            "provenance": "SELECTOR_RULE/ENGINEERING_DEFAULT_CANDIDATE",
        },
        "corrosion_allowance_mm": {
            "value": corrosion_allowance,
            "unit": "mm",
            "state": "PROGRAM_PRELIMINARY_CORROSION_ALLOWANCE_CANDIDATE",
            "evidence_class": "J",
            "promotion_cap": "TYPE_SCREENING",
            "provenance": "SELECTOR_RULE/ENGINEERING_DEFAULT_CANDIDATE",
        },
        "pressure_class": {
            "value": pn_text,
            "unit": None,
            "state": "PROGRAM_PRELIMINARY_PN_SERIES_CANDIDATE",
            "evidence_class": "J",
            "promotion_cap": "TYPE_SCREENING",
            "provenance": (
                "VERIFIED_STANDARD_SERIES_RECORD/"
                "SELECTOR_RULE/PN_SERIES_MAPPING_ONLY"
            ),
            "claim_boundary": (
                "PN series designation candidate only; not a verified "
                "pressure-temperature rating or component pressure class."
            ),
        },
        "piping_class_candidate_code": {
            "value": piping_class_candidate_code,
            "unit": None,
            "state": "PROGRAM_ASSEMBLED_PRELIMINARY_LINE_CLASS",
            "evidence_class": "J",
            "promotion_cap": "TYPE_SCREENING",
            "provenance": (
                "SELECTOR_RULE/"
                "PROGRAM_ASSEMBLED_PRELIMINARY_LINE_CLASS"
            ),
            "claim_boundary": (
                "Program-assembled candidate code only; not a project-issued "
                "piping material class."
            ),
        },
        "piping_class": {
            "value": "OPEN_PROJECT_AUTHORITY_GATE",
            "unit": None,
            "state": "OPEN_PROJECT_AUTHORITY_GATE",
            "evidence_class": "U",
            "promotion_cap": "NOT_PROMOTABLE",
            "provenance": "PROJECT_AUTHORITY_REQUIRED",
            "candidate_code": piping_class_candidate_code,
            "warning": (
                "正式管道等级必须由项目管道材料等级表批准；程序候选代码"
                f"{piping_class_candidate_code}不得冒充正式等级。"
            ),
        },
        "design_pressure_mpa": {"value": design_pressure, "unit": "MPa(g)"},
        "design_pressure_basis": {
            "value": (
                "gauge_internal_screening_plus_full_vacuum_external"
                if external_pressure_branch
                else (
                    "near_atmospheric_internal_screening_no_steady_"
                    "state_vacuum_trigger"
                    if near_atmospheric_screening
                    else "gauge"
                )
            ),
            "unit": None,
        },
        "external_design_pressure_mpa": {
            "value": external_design_pressure_mpa,
            "unit": "MPa",
            "state": (
                "PROGRAM_PRELIMINARY_SELECTED"
                if external_pressure_branch
                else "NOT_APPLICABLE"
            ),
        },
        "external_pressure_design_status": {
            "value": (
                "FORMAL-GATE-OPEN：全真空外压屈曲、椭圆度与加强圈校核"
                if external_pressure_branch
                else (
                    "稳态Aspen未触发显著真空；事故真空仍待项目定义"
                    if near_atmospheric_screening
                    else "稳态为正内压；事故真空仍待项目定义"
                )
            ),
            "unit": None,
            "state": (
                "OPEN_FORMAL_EVIDENCE_GATE"
                if external_pressure_branch
                else "PROGRAM_PRESSURE_REGIME_CLASSIFICATION"
            ),
            "evidence_class": "U" if external_pressure_branch else "J",
            "promotion_cap": (
                "NOT_PROMOTABLE"
                if external_pressure_branch
                else "TYPE_SCREENING"
            ),
        },
        "vacuum_margin_kpa": {
            "value": vacuum_margin_kpa,
            "unit": "kPa",
            "state": "PROGRAM_PRESSURE_REGIME_CLASSIFICATION",
            "evidence_class": "J",
            "promotion_cap": "TYPE_SCREENING",
        },
        "significant_vacuum_threshold_kpa": {
            "value": vacuum_threshold_kpa,
            "unit": "kPa",
            "state": "REGISTERED_PROJECT_SCREENING_THRESHOLD",
            "evidence_class": "J",
            "promotion_cap": "TYPE_SCREENING",
        },
        "design_temperature_c": {"value": design_temperature, "unit": "degC"},
        "actual_velocity_m_s": {"value": actual_velocity, "unit": "m/s"},
        "reynolds_number": {"value": reynolds_number, "unit": None},
        "pressure_gradient_kpa_per_100m": {
            "value": pressure_gradient_kpa_100m,
            "unit": "kPa/100m",
        },
        "pressure_gradient_screen_limit_kpa_per_100m": {
            "value": PIPE_PRESSURE_GRADIENT_SCREEN_KPA_PER_100M,
            "unit": "kPa/100m",
            "state": (
                "PROGRAM_PRELIMINARY_ADVISORY_THRESHOLD"
                if two_phase_screening
                else "PROGRAM_PRELIMINARY_SCREENING_THRESHOLD"
            ),
            "evidence_class": "J",
            "promotion_cap": "TYPE_SCREENING",
            "warning": (
                "50 kPa/100m为本程序登记的项目预筛阈值，不是国标验收限值。"
            ),
        },
        "hydraulic_acceptance_status": {
            "value": hydraulic_acceptance_status,
            "unit": None,
            "state": hydraulic_acceptance_status,
            "evidence_class": "J",
            "promotion_cap": "TYPE_SCREENING",
        },
        "two_phase_hydraulic_status": {
            "value": (
                "FORMAL-GATE-OPEN：程序仅完成均相初筛；流型、持液率、"
                "相间滑移、闪蒸、段塞与两相压降关联式待正式校核"
                if two_phase_screening
                else "NOT_APPLICABLE_SINGLE_PHASE"
            ),
            "unit": None,
            "state": (
                "OPEN_FORMAL_EVIDENCE_GATE"
                if two_phase_screening
                else "NOT_APPLICABLE"
            ),
            "evidence_class": "U" if two_phase_screening else "D",
            "promotion_cap": (
                "NOT_PROMOTABLE"
                if two_phase_screening
                else "NOT_APPLICABLE"
            ),
        },
        "viscosity_basis_status": {
            "value": (
                "强警告：INTERNAL_CORRELATION_ESTIMATE；非Aspen提取；"
                "仅允许单相初步水力筛选"
                if internal_viscosity_estimate
                else (
                    "强警告：TWO_PHASE_SCREENING_PROXY_FROM_PHASE_MUMX；"
                    "取液/气相黏度上限，仅允许均相初筛，非Aspen两相混合黏度"
                    if two_phase_screening
                    else "ASPEN_OR_DIRECT_PROCESS_PROPERTY"
                )
            ),
            "unit": None,
            "state": (
                "OPEN_FORMAL_EVIDENCE_GATE"
                if internal_viscosity_estimate
                else (
                    "PROGRAM_PRELIMINARY_TWO_PHASE_VISCOSITY_PROXY"
                    if two_phase_screening
                    else "PROCESS_PROPERTY_AVAILABLE"
                )
            ),
            "evidence_class": (
                "J"
                if internal_viscosity_estimate or two_phase_screening
                else "D"
            ),
            "promotion_cap": (
                "TYPE_SCREENING"
                if internal_viscosity_estimate or two_phase_screening
                else "PROCESS_SIDE_ONLY"
            ),
            "provenance": (
                "INTERNAL_CORRELATION_ESTIMATE"
                if internal_viscosity_estimate
                else (
                    "CALCULATED_TWO_PHASE_SCREENING_PROXY"
                    if two_phase_screening
                    else "ASPEN_OR_DIRECT_PROCESS_PROPERTY"
                )
            ),
            "warning": (
                viscosity_diagnostic.get("claim_boundary")
                if internal_viscosity_estimate
                else (
                    "The numeric proxy is max(mu_liquid,mu_vapor) from "
                    "separate Aspen phase MUMX values. It is not an Aspen "
                    "two-phase mixture property and cannot close formal "
                    "two-phase hydraulics."
                    if two_phase_screening
                    else None
                )
            ),
        },
        "insulation_spec": {"value": insulation_spec, "unit": None},
        "insulation_layer": {"value": insulation_spec, "unit": None},
        "heat_tracing_spec": {"value": heat_tracing_spec, "unit": None},
        "heat_tracing": {"value": heat_tracing_spec, "unit": None},
        "protective_layer": {"value": protective_layer, "unit": None},
        "test_pressure_mpa": {
            "value": round(1.5 * design_pressure, 6),
            "unit": "MPa(g)",
        },
        "nde_requirement": {
            "value": (
                "100% VT+10% RT/UT（程序初选；正式比例按管道等级、"
                "介质类别和法规复核）"
            ),
            "unit": None,
        },
        "hydraulic_calculation_ref": {
            "value": f"PIPE-HYD-{hydraulic_sha256[:16]}",
            "unit": None,
        },
        "pressure_wall_calculation_ref": {
            "value": f"PIPE-WALL-{wall_sha256[:16]}",
            "unit": None,
        },
        "stress_analysis_ref": {
            "value": None,
            "display_value": "OPEN：尚未完成管系应力分析",
            "unit": None,
            "state": "OPEN_FORMAL_EVIDENCE_GATE",
            "evidence_class": "U",
            "promotion_cap": "NOT_PROMOTABLE",
            "reason": (
                "Aspen 稳态模型不提供完成管系应力分析所需的三维走向、"
                "支吊架布置、位移边界和完整温差工况。"
            ),
            "required_action": (
                "取得管道布置、支吊架、设备管口位移及启停/异常温度工况后，"
                "按适用管道规范完成应力分析并回填报告编号。"
            ),
        },
        "support_design_ref": {
            "value": None,
            "display_value": "OPEN：尚未完成支吊架设计",
            "unit": None,
            "state": "OPEN_FORMAL_EVIDENCE_GATE",
            "evidence_class": "U",
            "promotion_cap": "NOT_PROMOTABLE",
            "reason": (
                "Aspen 稳态模型不包含三维布置、跨距、局部荷载、热位移及"
                "土建接口，不能据此生成正式支吊架方案。"
            ),
            "required_action": (
                "完成三维管道布置和应力分析后，按荷载、跨距与位移要求"
                "设计支吊架并回填图纸或计算书编号。"
            ),
        },
    }
    if material["large_bore_welded_route"]:
        large_bore_open_fields = {
            "plate_material_grade": (
                "OPEN_PROJECT_PLATE_GRADE_GATE",
                "板材牌号须按介质相容性、设计温度、压力规范和采购范围批准。",
            ),
            "welding_filler_metal": (
                "OPEN_PROJECT_WELDING_CONSUMABLE_GATE",
                "焊材须与批准板材、焊接工艺评定及腐蚀要求匹配。",
            ),
            "approved_weld_joint_efficiency": (
                "OPEN_CODE_WELD_JOINT_EFFICIENCY_GATE",
                "0.85仅用于程序壁厚初筛；正式焊接接头系数须由规范和NDE确定。",
            ),
            "forming_heat_treatment_requirement": (
                "OPEN_FORMING_AND_HEAT_TREATMENT_GATE",
                "卷制成形、焊后热处理及尺寸恢复要求须由制造规范批准。",
            ),
            "longitudinal_seam_nde_acceptance": (
                "OPEN_LONGITUDINAL_SEAM_NDE_GATE",
                "纵缝NDE方法、比例、验收级别及返修规则须正式批准。",
            ),
            "welded_pipe_product_specification": (
                "OPEN_PROJECT_WELDED_PIPE_PRODUCT_SPECIFICATION_GATE",
                "现有标准仓没有可直接复用的大口径焊管产品记录。",
            ),
        }
        for field_id, (value, warning) in large_bore_open_fields.items():
            fields[field_id] = {
                "value": value,
                "unit": None,
                "state": "OPEN_PROJECT_AUTHORITY_GATE",
                "evidence_class": "U",
                "promotion_cap": "NOT_PROMOTABLE",
                "provenance": "PROJECT_AUTHORITY_REQUIRED",
                "warning": warning,
            }
        fields["screening_weld_factor"] = {
            "value": weld_factor,
            "unit": None,
            "state": "PROGRAM_PRELIMINARY_SCREENING_ASSUMPTION",
            "evidence_class": "J",
            "promotion_cap": "TYPE_SCREENING",
            "provenance": "SELECTOR_RULE/LARGE_BORE_WELDED_SCREEN",
            "warning": (
                "0.85仅为程序壁厚初筛假设，不是已批准的焊接接头系数。"
            ),
        }
    for field in fields.values():
        field.setdefault("state", "PROGRAM_PRELIMINARY_SELECTED")
        field.setdefault("evidence_class", "J")
        field.setdefault("promotion_cap", "TYPE_SCREENING")
    base = {
        "schema": "programmatic-pipe-specification-v1",
        "version": "1.2.0",
        "status": "PRELIMINARY_CONCRETE_SPECIFICATION_SELECTED",
        "selection_scope": "IDENTITY_AND_PRELIMINARY_GEOMETRY_ONLY",
        "deterministic": True,
        "llm_used": False,
        "program_generated": True,
        "stream_id": stream_id,
        "designation": designation,
        "manufacturing_route": {
            "route_code": material["route_code"],
            "large_bore_welded_route": material[
                "large_bore_welded_route"
            ],
            "equipment_type": material["equipment_type"],
            "manufacturing_method": material["manufacturing_method"],
            "product_standard_scope_established": material[
                "product_standard_scope_established"
            ],
            "product_standard_identity_candidate": material[
                "product_standard_identity_candidate"
            ],
            "product_standard_evidence_sha256": material[
                "product_standard_evidence"
            ]["evidence_sha256"],
            "open_gates": material["manufacturing_open_gates"],
            "manufacturing_open_gates": material[
                "manufacturing_open_gates"
            ],
        },
        "product_standard_evidence": material[
            "product_standard_evidence"
        ],
        "fields": fields,
        "hydraulic_calculation": hydraulic_basis,
        "pressure_wall_screening": wall_basis,
        "cross_standard_pairing": cross_standard_pairing,
        "standard_selections": {
            "dn": {
                "dataset_id": "gbt12459_fitting_dn_od_reference",
                "standard_object": (
                    "steel_butt_welding_seamless_fittings_not_pipe_product"
                ),
                "selected_value": f"DN{selected_dn}",
                "catalog_outer_diameter_mm": initial_outer_diameter,
                "record": dn_standard_record,
                "record_state": (
                    "VERIFIED_SOURCE_CELL_BOUND"
                    if dn_standard_record is not None
                    else "MISSING_MATCHER_STANDARD_RECORD"
                ),
                "claim_boundary": (
                    "GB/T 12459 is a steel butt-welding seamless-fitting "
                    "standard. This source cell is retained only as a "
                    "hydraulic DN-to-D reference candidate; it is not a pipe "
                    "product record and does not establish the independently "
                    "selected GB/T 17395 metric OD/wall record, Schedule, "
                    "pressure rating, material, or project piping class."
                ),
            },
            "pn": {
                "dataset_id": "gbt1048_nominal_pressure_series",
                "selected_value": pn_text,
                "record_id": pn["record_id"],
                "record_sha256": pn["record_sha256"],
                "source_pdf_sha256": pn["source_sha256"],
                "physical_page": pn["physical_page"],
                "standard_id": pn["standard_id"],
                "standard_version": pn["standard_version"],
                "selector_required_pn_number": pn[
                    "selector_required_pn_number"
                ],
                "engineering_policy_floor_pn": pn[
                    "engineering_policy_floor_pn"
                ],
                "pressure_to_pn_screening_factor": pn[
                    "pressure_to_pn_screening_factor"
                ],
                "selection_provenance": pn["selection_provenance"],
                "claim_boundary": (
                    "PN series designation candidate only. The P(g)*10 mapping "
                    "and PN16 floor are selector policy, not a GB/T 1048 "
                    "pressure-temperature rating. Product-standard, material, "
                    "temperature and component verification remain open."
                ),
            },
            "wall": {
                "dataset_id": "gbt17395_pipe_dimensions_weights",
                "standard_object": (
                    "metric_od_wall_geometry_reference_only_not_"
                    "welded_pipe_product"
                    if material["large_bore_welded_route"]
                    else (
                        "seamless_steel_pipe_dimensions_shape_mass_"
                        "and_tolerances"
                    )
                ),
                "usage_role": (
                    "GEOMETRY_REFERENCE_ONLY"
                    if material["large_bore_welded_route"]
                    else "SEAMLESS_PIPE_DIMENSION_CANDIDATE"
                ),
                "product_scope_applicable": (
                    not material["large_bore_welded_route"]
                ),
                "record_id": wall["record_id"],
                "record_sha256": wall["record_sha256"],
                "source_pdf_sha256": wall["source_sha256"],
                "physical_page": wall["physical_page"],
                "standard_id": wall["standard_id"],
                "standard_version": wall["standard_version"],
                "outer_diameter_mm": outer_diameter,
                "wall_thickness_mm": wall_thickness,
                "unit_mass_kg_m": wall["unit_mass_kg_m"],
                "outer_diameter_series": wall["outer_diameter_series"],
                "wall_thickness_recommended": wall[
                    "wall_thickness_recommended"
                ],
                "claim_boundary": (
                    (
                        "For this DN600-and-above LSAW candidate, the verified "
                        "GB/T 17395 seamless-pipe cell is retained only as a "
                        "metric OD/wall geometry reference. Its product scope "
                        "is not applicable to the welded-pipe route and the "
                        "welded product specification remains open. "
                    )
                    if material["large_bore_welded_route"]
                    else (
                        "GB/T 17395 supplies an independent seamless "
                        "steel-pipe metric OD/wall/weight candidate only. "
                    )
                )
                + (
                    "This is non-SCH and not a single-standard pairing with "
                    "the GB/T 12459 fitting-table hydraulic DN candidate. It "
                    "is not a pressure rating or material-compatibility "
                    "acceptance."
                ),
            },
            "cross_standard_pairing": cross_standard_pairing,
            "store": {
                "build_id": store["build_id"],
                "database_path": store["database_path"],
                "database_sha256": store["database_sha256"],
                "manifest_path": store["manifest_path"],
                "manifest_sha256": store["manifest_sha256"],
            },
        },
        "source_binding": {
            "aspen_export_path": str(source_file),
            "aspen_export_sha256": source_sha256,
            "input_fields": {
                "flow_m3_h": flow_m3_h,
                "density_kg_m3": density_kg_m3,
                "dynamic_viscosity_mpa_s": viscosity_mpa_s,
                "liquid_dynamic_viscosity_mpa_s": finite_number(
                    record.get("liquid_dynamic_viscosity_mpa_s")
                ),
                "vapor_dynamic_viscosity_mpa_s": finite_number(
                    record.get("vapor_dynamic_viscosity_mpa_s")
                ),
                "two_phase_viscosity_screening_basis": (
                    two_phase_viscosity_basis
                ),
                "viscosity_fallback_diagnostic": viscosity_diagnostic,
                "target_velocity_m_s": finite_number(
                    _match_value(match_result, "target_velocity_m_s")
                ),
                "required_inner_diameter_mm": required_inner_diameter,
                "initial_wall_thickness_mm": initial_wall,
                "hydraulic_dn_candidate": selected_dn,
                "gbt12459_catalog_outer_diameter_mm": (
                    initial_outer_diameter
                ),
                "gbt17395_metric_outer_diameter_mm": outer_diameter,
                "gbt17395_metric_wall_thickness_mm": wall_thickness,
                "cross_standard_outer_diameter_difference_mm": (
                    od_difference_mm
                ),
                "preliminary_material_input": preliminary_material,
                "material_selector_basis": material["selection_basis"],
                "connection_selector_basis": (
                    "registered_preliminary_butt_weld_default"
                ),
                "corrosion_allowance_selector_basis": (
                    material["selection_basis"]
                ),
                "design_pressure_mpa_gauge": design_pressure,
                "matcher_design_pressure_mpa_gauge": matcher_design_pressure,
                "operating_pressure_mpa": operating_pressure,
                "pressure_basis": pressure_basis,
                "atmospheric_pressure_mpa": atmospheric_pressure,
                "external_pressure_branch": external_pressure_branch,
                "external_design_pressure_mpa": external_design_pressure_mpa,
                "near_atmospheric_screening": near_atmospheric_screening,
                "vacuum_margin_kpa": vacuum_margin_kpa,
                "vacuum_threshold_kpa": vacuum_threshold_kpa,
                "pipe_pressure_regime_screening": pressure_regime,
                "pipe_hydraulic_preselection": record.get(
                    "pipe_hydraulic_preselection"
                ),
                "manufacturing_route": material["route_code"],
                "design_temperature_c": design_temperature,
            },
        },
        "formal_readiness": {
            "status": "BLOCKED_PRELIMINARY_ONLY",
            "open_gates": [
                "project_authority_piping_class",
                "coherent_product_standard_dn_od_wall_mapping",
                "pipe_product_standard_scope_and_manufacturability",
                *material["manufacturing_open_gates"],
                "schedule_or_metric_series_project_acceptance",
                "project_line_length_and_fittings",
                "pressure_drop_acceptance",
                "material_compatibility_and_corrosion_study",
                "code_wall_thickness_and_negative_tolerance",
                "pressure_temperature_rating",
                *(
                    ["external_pressure_buckling_ovality_and_stiffening"]
                    if external_pressure_branch
                    else []
                ),
                "accident_vacuum_case_definition",
                *(
                    [
                        "two_phase_flow_regime_holdup_slip_and_pressure_drop",
                        "flashing_slugging_choking_and_vibration",
                    ]
                    if two_phase_screening
                    else []
                ),
                *(
                    [
                        "aspen_or_lab_viscosity_confirmation",
                        "viscosity_correlation_source_asset_verification",
                        "viscosity_mixing_rule_applicability",
                    ]
                    if internal_viscosity_estimate
                    else []
                ),
                "stress_analysis_and_support_design",
                "test_and_nde_plan_approval",
            ],
        },
    }
    base["program_specification_sha256"] = _canonical_sha256(base)
    for field in fields.values():
        field["program_specification_sha256"] = base[
            "program_specification_sha256"
        ]
    return base


def apply_programmatic_pipe_specification(
    *,
    record: dict[str, Any],
    chain: list[dict[str, Any]],
    pipe_specification: dict[str, Any],
    source_file: Path,
    source_sha256: str,
    object_id: str,
) -> None:
    """Project an auditable preliminary line specification into canonical fields."""

    pipe_fields = (
        pipe_specification.get("fields", {})
        if isinstance(pipe_specification.get("fields"), dict)
        else {}
    )
    pipe_specification_sha256 = str(
        pipe_specification.get("program_specification_sha256") or ""
    )
    standard_selections = (
        pipe_specification.get("standard_selections", {})
        if isinstance(pipe_specification.get("standard_selections"), dict)
        else {}
    )
    dn_selection = (
        standard_selections.get("dn", {})
        if isinstance(standard_selections.get("dn"), dict)
        else {}
    )
    dn_record = (
        dn_selection.get("record", {})
        if isinstance(dn_selection.get("record"), dict)
        else {}
    )
    dn_catalog_path = str(
        dn_record.get("catalog_path")
        or f"programmatic_pipe_specification:{pipe_specification_sha256}:"
        "missing_DN_standard_record"
    )
    for field_id, descriptor in pipe_fields.items():
        if not isinstance(descriptor, dict) or descriptor.get("value") is None:
            continue
        value = descriptor["value"]
        record[field_id] = value
        if field_id in {
            "selected_outer_diameter_mm",
            "selected_wall_thickness_mm",
            "wall_series",
            "outer_diameter_series",
        }:
            source_path = str(PIPE_STANDARD_DB_PATH)
            formula = (
                "GB/T_17395_verified_metric_dimension_record/"
                "program_preliminary_non_SCH_policy"
            )
        elif field_id in {
            "selected_dn",
            "hydraulic_dn_candidate",
            "dn_catalog_outer_diameter_mm",
        }:
            source_path = dn_catalog_path
            formula = (
                "GB/T_12459_verified_DN_to_D_record/"
                "hydraulic_DN_candidate_selector"
            )
        elif field_id == "pressure_class":
            source_path = str(PIPE_STANDARD_DB_PATH)
            formula = (
                "GB/T_1048_verified_PN_series_mapping_only/"
                "program_screening_threshold"
            )
        elif field_id == "piping_class_candidate_code":
            source_path = (
                f"programmatic_pipe_specification:{pipe_specification_sha256}"
            )
            formula = (
                "SELECTOR_RULE/"
                "PROGRAM_ASSEMBLED_PRELIMINARY_LINE_CLASS"
            )
        elif field_id == "piping_class":
            source_path = (
                f"programmatic_pipe_specification:{pipe_specification_sha256}"
            )
            formula = "PROJECT_AUTHORITY_REQUIRED/no_program_formal_class"
        elif field_id in {
            "actual_velocity_m_s",
            "reynolds_number",
            "pressure_gradient_kpa_per_100m",
            "hydraulic_calculation_ref",
        }:
            source_path = (
                f"programmatic_pipe_specification:{pipe_specification_sha256}"
            )
            formula = "Darcy_Weisbach_screening_chain"
        else:
            source_path = (
                f"programmatic_pipe_specification:{pipe_specification_sha256}"
            )
            formula = "registered_preliminary_pipe_selection_policy"
        descriptor_state = str(
            descriptor.get("state") or "PROGRAM_PRELIMINARY_SELECTED"
        )
        evidence_scope = (
            "PROJECT_AUTHORITY_GATE"
            if field_id == "piping_class"
            else "PROGRAMMATIC_PRELIMINARY_PIPE_SELECTION"
        )
        chain.append(
            lineage(
                target_field=field_id,
                value=value,
                unit=str(descriptor.get("unit") or "-"),
                source_file=source_file,
                source_sha256=source_sha256,
                object_type="programmatic_pipe_selector",
                object_id=object_id,
                source_field=(
                    f"programmatic_pipe_specification.fields.{field_id}"
                ),
                source_path=source_path,
                transform="deterministic_preliminary_pipe_specification",
                formula=formula,
                substitution=json.dumps(
                    {
                        "value": value,
                        "program_specification_sha256": (
                            pipe_specification_sha256
                        ),
                        "provenance": descriptor.get("provenance"),
                        "claim_boundary": descriptor.get("claim_boundary"),
                        "dn_record_binding_sha256": dn_record.get(
                            "record_binding_sha256"
                        ),
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                evidence_class=str(descriptor.get("evidence_class") or "J"),
                result_status=descriptor_state,
                evidence_scope=evidence_scope,
                promotion_cap=str(
                    descriptor.get("promotion_cap") or "TYPE_SCREENING"
                ),
                warning=str(
                    descriptor.get("warning")
                    or (
                        "程序已生成具体初选规格；正式材料相容性、压力温度额定值、"
                        "壁厚规范校核、外压屈曲、应力、支吊架、试压和NDE仍须项目确认。"
                    )
                ),
            )
        )


def apply_programmatic_pipe_model_boundary(
    match_result: dict[str, Any],
    pipe_specification: dict[str, Any],
) -> None:
    """Keep the user-visible model candidate identical to the pipe spec."""

    match_result["programmatic_pipe_specification"] = pipe_specification
    if (
        pipe_specification.get("status")
        != "PRELIMINARY_CONCRETE_SPECIFICATION_SELECTED"
    ):
        return
    fields = (
        pipe_specification.get("fields", {})
        if isinstance(pipe_specification.get("fields"), dict)
        else {}
    )
    specification_sha256 = str(
        pipe_specification.get("program_specification_sha256") or ""
    )
    equipment_type = str(
        (fields.get("equipment_type") or {}).get("value") or ""
    )
    designation = str(pipe_specification.get("designation") or "")
    model = (
        match_result.get("model_recommendation")
        if isinstance(match_result.get("model_recommendation"), dict)
        else {}
    )
    leading = (
        model.get("leading_candidate")
        if isinstance(model.get("leading_candidate"), dict)
        else None
    )
    if isinstance(leading, dict):
        leading["designation"] = designation
        leading["candidate_name"] = equipment_type
        leading["program_origin"] = "PROGRAMMATIC_PIPE_SELECTOR"
        leading["source"] = {
            "kind": "deterministic_programmatic_pipe_specification",
            "program_specification_sha256": specification_sha256,
        }
        leading["candidate_eligibility"] = (
            "IDENTITY_AND_PRELIMINARY_GEOMETRY_ONLY"
        )
        leading["eligible_for_formal_selection"] = False
        leading["formal_model"] = False
        leading["missing_gates"] = list(
            pipe_specification.get("formal_readiness", {}).get(
                "open_gates",
                [],
            )
        )
        leading_specification = (
            leading.get("specification")
            if isinstance(leading.get("specification"), dict)
            else {}
        )
        for field_id, descriptor in fields.items():
            if (
                not isinstance(descriptor, dict)
                or descriptor.get("value") is None
            ):
                continue
            leading_specification[field_id] = {
                "value": descriptor["value"],
                "unit": descriptor.get("unit"),
                "state": descriptor.get("state"),
                "evidence_class": descriptor.get("evidence_class"),
                "promotion_cap": descriptor.get("promotion_cap"),
                "program_specification_sha256": specification_sha256,
            }
        leading["specification"] = leading_specification
    terminal_selection = {
        "status": "PROGRAMMATIC_PIPE_ROUTE_AND_GEOMETRY_SELECTED",
        "recommended_type": equipment_type,
        "selection_basis": (
            "deterministic_programmatic_pipe_specification"
        ),
        "default_applied": False,
        "evidence_class": "J",
        "provisional": True,
        "rule_id": "PIPE_HYDRAULIC_AND_MANUFACTURING_SCREEN_V1",
        "assumption": (
            "管型、制造路线、DN及公制OD×t由程序完成预筛；正式管道"
            "等级、产品标准适用性、全线压降、应力和项目审批仍未闭合。"
        ),
        "terminal_scope": (
            "IDENTITY_AND_PRELIMINARY_GEOMETRY_ONLY"
        ),
        "formal_model": False,
        "is_vendor_model": False,
        "program_specification_sha256": specification_sha256,
    }
    apply_model_screening_boundary(
        match_result,
        boundary_id="programmatic_pipe_formal_design_open",
        model_status="PIPE_ROUTE_SELECTED_FORMAL_DESIGN_BLOCKED",
        candidate_status="PRELIMINARY_PROGRAMMATIC_PIPE_ROUTE_SELECTED",
        candidate_eligibility=(
            "IDENTITY_AND_PRELIMINARY_GEOMETRY_ONLY"
        ),
        missing_gates=list(
            pipe_specification.get("formal_readiness", {}).get(
                "open_gates",
                [],
            )
        ),
        execution_status="TYPE_AND_GEOMETRY_SELECTED_PIPE_DESIGN_BLOCKED",
        execution_scope=(
            "PIPE_ROUTE_DN_AND_METRIC_GEOMETRY_SCREENING_ONLY"
        ),
        recommended_type=equipment_type,
        terminal_selection=terminal_selection,
        warning=terminal_selection["assumption"],
    )
    decision = (
        match_result.get("model_decision", {})
        if isinstance(match_result.get("model_decision"), dict)
        else {}
    )
    if decision:
        decision["program_specification_sha256"] = specification_sha256
    synchronize_model_boundary_projection(
        match_result,
        boundary_id="programmatic_pipe_formal_design_open",
    )


def derive_piping(
    stream: dict[str, Any],
    endpoints: dict[str, list[str]],
    case: dict[str, Any],
    source_file: Path,
    source_sha256: str,
    rules: dict[str, Any],
    graph: dict[str, Any],
    pipe_entity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Project one material-stream state into a pipe or endpoint-state record."""

    stream_id = stream["stream_id"]
    pipe_entity = (
        dict(pipe_entity)
        if isinstance(pipe_entity, dict)
        else classify_pfd_stream_pipe_entity(
            stream_id=stream_id,
            endpoints=endpoints,
            physical_pipe_block_ids=set(),
        )
    )
    from_blocks = endpoints.get("from_block_ids", [])
    to_blocks = endpoints.get("to_block_ids", [])
    from_label = ",".join(from_blocks) if from_blocks else "PFD boundary"
    to_label = ",".join(to_blocks) if to_blocks else "PFD boundary"
    pressure_basis = str(case.get("pressure_basis") or "").strip().casefold()
    record: dict[str, Any] = {
        "equipment_tag": stream_id,
        "stream_id": stream_id,
        "line_number": stream_id,
        "source_endpoint": from_label,
        "destination_endpoint": to_label,
        "equipment_family": "family_process_piping",
        "process_function": f"PFD material stream {stream_id}: {from_label} -> {to_label}",
        "pressure_basis": pressure_basis,
        **pipe_entity,
    }
    chain: list[dict[str, Any]] = []
    for target_field in (
        "pipe_entity_scope",
        "pipe_entity_id",
        "counted_as_physical_pipe",
        "alias_only",
    ):
        chain.append(
            lineage(
                target_field=target_field,
                value=record.get(target_field),
                unit="-",
                source_file=source_file,
                source_sha256=source_sha256,
                object_type="stream_topology",
                object_id=stream_id,
                source_field="PFD.adjacent_block_types",
                transform="deterministic_pipe_entity_classification",
                formula=(
                    "adjacent explicit Aspen PIPE -> endpoint-state alias; "
                    "otherwise PFD material-stream pipe segment"
                ),
                substitution=json.dumps(
                    {
                        "from_block_ids": from_blocks,
                        "to_block_ids": to_blocks,
                        "adjacent_physical_pipe_block_ids": (
                            pipe_entity.get(
                                "adjacent_physical_pipe_block_ids", []
                            )
                        ),
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                evidence_class="D",
                result_status="DERIVED",
                evidence_scope="PHYSICAL_PIPE_ENTITY_COUNTING",
                promotion_cap="PHYSICAL_ENTITY_COUNTING",
            )
        )
    endpoint_pressure_drop_audit = (
        build_pfd_stream_endpoint_pressure_drop_audit(
            stream=stream,
            pipe_entity=pipe_entity,
            source_export_sha256=source_sha256,
            pressure_basis=pressure_basis,
        )
    )
    record["endpoint_pressure_drop_audit"] = (
        endpoint_pressure_drop_audit
    )
    record["endpoint_pressure_drop_status"] = (
        endpoint_pressure_drop_audit["status"]
    )
    record["endpoint_pressure_drop_formal_acceptance"] = False
    for target_field, value in (
        (
            "endpoint_pressure_drop_status",
            record["endpoint_pressure_drop_status"],
        ),
        ("endpoint_pressure_drop_formal_acceptance", False),
    ):
        chain.append(
            lineage(
                target_field=target_field,
                value=value,
                unit="-",
                source_file=source_file,
                source_sha256=source_sha256,
                object_type="pipe_endpoint_pressure_drop_audit",
                object_id=str(record["pipe_entity_id"]),
                source_field=target_field,
                source_path=(
                    "endpoint_pressure_drop_audit:"
                    + endpoint_pressure_drop_audit["audit_sha256"]
                ),
                transform="hash_bound_endpoint_audit_projection",
                formula="identity_from_endpoint_pressure_drop_audit",
                substitution=str(value),
                evidence_class="D",
                result_status="DERIVED",
                evidence_scope="PFD_STREAM_PRESSURE_STATE_BOUNDARY",
                promotion_cap="PROCESS_HYDRAULIC_OBSERVATION",
            )
        )
    for target_field, value, formula in (
        ("line_number", stream_id, "Aspen_material_stream_id"),
        ("source_endpoint", from_label, "PFD_upstream_block_ids_or_boundary"),
        ("destination_endpoint", to_label, "PFD_downstream_block_ids_or_boundary"),
    ):
        chain.append(
            lineage(
                target_field=target_field,
                value=value,
                unit="-",
                source_file=source_file,
                source_sha256=source_sha256,
                object_type="stream_topology",
                object_id=stream_id,
                source_field=f"PFD.endpoints.{target_field}",
                transform="deterministic_topology_projection",
                formula=formula,
                substitution=str(value),
                evidence_class="D",
                result_status="DERIVED",
                evidence_scope="ASPEN_PFD_TOPOLOGY",
                promotion_cap="PROCESS_SIDE_ONLY",
            )
        )
    medium_name, composition_basis, composition_sources = piping_medium_name(stream)
    if medium_name:
        record["medium_name"] = medium_name
        record["main_medium"] = medium_name
        chain.append(
            lineage(
                target_field="medium_name",
                value=medium_name,
                unit="-",
                source_file=source_file,
                source_sha256=source_sha256,
                object_type="stream",
                object_id=stream_id,
                source_field="composition",
                transform="closed_composition_vector_to_medium_label",
                formula="ordered_positive_components_with_fraction_and_basis",
                substitution=json.dumps(
                    {
                        "basis": composition_basis,
                        "source_paths": composition_sources,
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                evidence_class="D",
                result_status="DERIVED",
                evidence_scope="ASPEN_PROCESS_SIDE",
                promotion_cap="PROCESS_SIDE_ONLY",
            )
        )
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
        phase_source = (
            stream.get("_sources", {}).get("phase", {})
            if isinstance(stream.get("_sources"), dict)
            else {}
        )
        add_direct(
            record,
            chain,
            "phase",
            stream["phase"],
            "-",
            phase_source,
            source_file,
            source_sha256,
            "stream",
            stream_id,
        )
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
        ("dynamic_viscosity_mpa_s", "dynamic_viscosity_mpa_s", "mPa*s"),
        ("liquid_dynamic_viscosity_mpa_s", "liquid_dynamic_viscosity_mpa_s", "mPa*s"),
        ("vapor_dynamic_viscosity_mpa_s", "vapor_dynamic_viscosity_mpa_s", "mPa*s"),
        ("pressure_mpa", "operating_pressure_mpa", "MPa"),
        ("temperature_c", "operating_temperature_c", "C"),
    ]
    for source_field, target, unit in direct_fields:
        if source_field and stream.get(source_field) is not None:
            add_direct(
                record, chain, target, stream[source_field], unit, stream["_sources"][source_field],
                source_file, source_sha256, "stream", stream_id,
            )
    apply_two_phase_viscosity_screening(
        record=record,
        chain=chain,
        source_file=source_file,
        source_sha256=source_sha256,
        object_id=stream_id,
        source_map=dict(stream.get("_sources") or {}),
    )
    viscosity_diagnostic = (
        dict(stream.get("viscosity_fallback_diagnostic") or {})
        if isinstance(stream.get("viscosity_fallback_diagnostic"), dict)
        else {}
    )
    if viscosity_diagnostic:
        record["viscosity_fallback_diagnostic"] = viscosity_diagnostic
    apply_pipe_pressure_regime_screening(
        record=record,
        chain=chain,
        source_file=source_file,
        source_sha256=source_sha256,
        object_id=stream_id,
    )
    apply_pipe_hydraulic_preselection(
        record=record,
        chain=chain,
        source_file=source_file,
        source_sha256=source_sha256,
        object_id=stream_id,
    )

    # The matcher currently names operating temperature `temperature_c`.
    # Preserve the explicit piping field above while adapting only the matcher
    # call; never map it to design_temperature_c.
    matcher_input = {
        key: value for key, value in record.items()
        if key not in {
            "stream_id",
            "operating_temperature_c",
            "pipe_hydraulic_preselection",
            "pipe_pressure_regime_screening",
            "viscosity_fallback_diagnostic",
        }
    }
    if "operating_temperature_c" in record:
        matcher_input["temperature_c"] = record["operating_temperature_c"]
    match_result = matcher.match_one(matcher_input, rules, graph)
    try:
        pipe_specification = build_programmatic_pipe_specification(
            stream_id=stream_id,
            record=record,
            match_result=match_result,
            source_file=source_file,
            source_sha256=source_sha256,
        )
    except Exception as exc:
        pipe_specification = {
            "schema": "programmatic-pipe-specification-v1",
            "status": "BLOCKED_PROGRAMMATIC_PIPE_SPECIFICATION",
            "deterministic": True,
            "llm_used": False,
            "stream_id": stream_id,
            "error_code": type(exc).__name__,
            "error": str(exc),
        }
    match_result["programmatic_pipe_specification"] = pipe_specification
    apply_programmatic_pipe_specification(
        record=record,
        chain=chain,
        pipe_specification=pipe_specification,
        source_file=source_file,
        source_sha256=source_sha256,
        object_id=stream_id,
    )
    apply_programmatic_pipe_model_boundary(
        match_result,
        pipe_specification,
    )
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
            "stream_id", "line_number", "source_endpoint", "destination_endpoint",
            "medium_name", "phase", "flow_m3_h", "mass_flow_kg_h", "density_kg_m3",
            "dynamic_viscosity_mpa_s", "liquid_dynamic_viscosity_mpa_s",
            "vapor_dynamic_viscosity_mpa_s",
            "operating_pressure_mpa", "operating_temperature_c",
            "selected_dn", "hydraulic_dn_candidate",
            "dn_catalog_outer_diameter_mm", "selected_outer_diameter_mm",
            "selected_wall_thickness_mm", "wall_series",
            "schedule_designation", "outer_diameter_series",
            "dn_od_approximation_mm", "standard_combination_status",
            "material", "corrosion_allowance_mm", "pressure_class",
            "piping_class_candidate_code", "piping_class",
            "design_pressure_mpa", "design_temperature_c",
            "actual_velocity_m_s", "reynolds_number",
            "pressure_gradient_kpa_per_100m", "insulation_spec",
            "heat_tracing_spec", "test_pressure_mpa", "nde_requirement",
        )
        if record.get(field) is not None
    }
    compact_key_values = {
        field: record[field]
        for field in (
            "flow_m3_h", "operating_pressure_mpa", "operating_temperature_c",
            "selected_dn", "selected_outer_diameter_mm",
            "selected_wall_thickness_mm", "pressure_class",
        )
        if record.get(field) is not None
    }
    compact_type_or_model = (
        pipe_specification.get("designation")
        or decision.get("candidate_model")
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
        "pipe_entity_scope": record["pipe_entity_scope"],
        "pipe_entity_id": record["pipe_entity_id"],
        "pipe_entity_role": record["pipe_entity_role"],
        "counted_as_physical_pipe": record[
            "counted_as_physical_pipe"
        ],
        "alias_only": record["alias_only"],
        "canonical_pipe_entity_ids": list(
            record.get("canonical_pipe_entity_ids", [])
        ),
        "classification_complete": record.get(
            "classification_complete"
        ) is True,
        "requires_manual_entity_resolution": record.get(
            "requires_manual_entity_resolution"
        ) is True,
        "alias_status": record.get("alias_status"),
        "endpoint_pressure_drop_audit": (
            endpoint_pressure_drop_audit
        ),
        "status": match_result.get("status"),
        "canonical_match_input": record,
        "programmatic_pipe_specification": pipe_specification,
        "viscosity_fallback_diagnostic": viscosity_diagnostic,
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
            "status": (
                "PRELIMINARY_CONCRETE_PIPE_SPECIFICATION"
                if pipe_specification.get("status")
                == "PRELIMINARY_CONCRETE_SPECIFICATION_SELECTED"
                else "BLOCKED_PIPE_SPECIFICATION"
            ),
            "source_export_sha256": source_sha256,
            "affects_aspen_formal_use_gate": False,
            "program_specification_sha256": (
                pipe_specification.get("program_specification_sha256")
            ),
            "preliminary_fields_established": sorted(
                field_id
                for field_id, descriptor in (
                    pipe_specification.get("fields", {}).items()
                    if isinstance(pipe_specification.get("fields"), dict)
                    else []
                )
                if isinstance(descriptor, dict)
                and not str(descriptor.get("state") or "").startswith("OPEN_")
            ),
            "explicit_open_gate_fields": sorted(
                field_id
                for field_id, descriptor in (
                    pipe_specification.get("fields", {}).items()
                    if isinstance(pipe_specification.get("fields"), dict)
                    else []
                )
                if isinstance(descriptor, dict)
                and str(descriptor.get("state") or "").startswith("OPEN_")
            ),
            "formally_not_established": [
                "single_standard_pipe_DN_OD_wall_combination",
                "project_authority_piping_class",
                "formal_pressure_class_or_pressure_temperature_rating",
                "product_standard_scope_and_manufacturability",
                "whole_line_pressure_drop_acceptance",
                "material_compatibility_and_corrosion_study",
                "code_wall_thickness_and_negative_tolerance",
                "pressure_temperature_rating",
                "mechanical_stress_verification",
                "support_design_approval",
                "test_and_nde_plan_approval",
                "vendor_model",
                *(
                    [
                        "aspen_or_lab_viscosity_confirmation",
                        "viscosity_correlation_source_asset_verification",
                        "viscosity_mixing_rule_applicability",
                    ]
                    if viscosity_diagnostic.get("internal_correlation_used")
                    is True
                    else []
                ),
            ],
        },
    }


def build_programmatic_valve_specification(
    *,
    equipment: dict[str, Any],
    block: dict[str, Any],
    piping_by_stream: dict[str, dict[str, Any]],
    source_file: Path,
    source_sha256: str,
) -> dict[str, Any]:
    """Build one hash-bound valve screening specification from its line context."""

    block_id = str(block.get("block_id") or "")
    inlet_ids = [str(value) for value in block.get("inlet_streams", [])]
    outlet_ids = [str(value) for value in block.get("outlet_streams", [])]
    if len(inlet_ids) != 1 or len(outlet_ids) != 1:
        return {
            "schema": "programmatic-valve-specification-v1",
            "status": "BLOCKED_VALVE_PORT_CARDINALITY",
            "deterministic": True,
            "llm_used": False,
            "program_generated": True,
            "block_id": block_id,
            "required": "one inlet material stream and one outlet material stream",
            "actual": {
                "inlet_streams": inlet_ids,
                "outlet_streams": outlet_ids,
            },
        }
    inlet_pipe = piping_by_stream.get(inlet_ids[0], {})
    outlet_pipe = piping_by_stream.get(outlet_ids[0], {})
    inlet_spec = (
        inlet_pipe.get("programmatic_pipe_specification", {})
        if isinstance(inlet_pipe, dict)
        else {}
    )
    outlet_spec = (
        outlet_pipe.get("programmatic_pipe_specification", {})
        if isinstance(outlet_pipe, dict)
        else {}
    )
    if not (
        isinstance(inlet_spec, dict)
        and isinstance(outlet_spec, dict)
        and inlet_spec.get("status")
        == "PRELIMINARY_CONCRETE_SPECIFICATION_SELECTED"
        and outlet_spec.get("status")
        == "PRELIMINARY_CONCRETE_SPECIFICATION_SELECTED"
    ):
        return {
            "schema": "programmatic-valve-specification-v1",
            "status": "BLOCKED_ADJACENT_PIPE_SPECIFICATION",
            "deterministic": True,
            "llm_used": False,
            "program_generated": True,
            "block_id": block_id,
            "inlet_stream_id": inlet_ids[0],
            "outlet_stream_id": outlet_ids[0],
            "inlet_pipe_status": (
                inlet_spec.get("status")
                if isinstance(inlet_spec, dict)
                else "MISSING"
            ),
            "outlet_pipe_status": (
                outlet_spec.get("status")
                if isinstance(outlet_spec, dict)
                else "MISSING"
            ),
        }

    def pipe_value(specification: dict[str, Any], field: str) -> Any:
        fields = specification.get("fields", {})
        descriptor = fields.get(field) if isinstance(fields, dict) else None
        return descriptor.get("value") if isinstance(descriptor, dict) else None

    inlet_dn = finite_number(pipe_value(inlet_spec, "selected_dn"))
    outlet_dn = finite_number(pipe_value(outlet_spec, "selected_dn"))
    if inlet_dn is None or outlet_dn is None:
        return {
            "schema": "programmatic-valve-specification-v1",
            "status": "BLOCKED_ADJACENT_PIPE_DN",
            "deterministic": True,
            "llm_used": False,
            "program_generated": True,
            "block_id": block_id,
        }
    body_dn = int(round(min(inlet_dn, outlet_dn)))

    def pn_number(value: Any) -> float | None:
        match = re.search(r"(?i)PN\s*([0-9]+(?:\.[0-9]+)?)", str(value or ""))
        return float(match.group(1)) if match else None

    inlet_pn = pn_number(pipe_value(inlet_spec, "pressure_class"))
    outlet_pn = pn_number(pipe_value(outlet_spec, "pressure_class"))
    pn_candidates = [
        value for value in (inlet_pn, outlet_pn) if value is not None
    ]
    pressure_class = (
        f"PN{max(pn_candidates):g}"
        if pn_candidates
        else "OPEN_PRESSURE_CLASS_GATE"
    )

    record = (
        equipment.get("canonical_match_input", {})
        if isinstance(equipment.get("canonical_match_input"), dict)
        else {}
    )
    phase = matcher.canonical_phase(record.get("phase"))
    inlet_pressure = finite_number(record.get("inlet_pressure_mpa"))
    outlet_pressure = finite_number(record.get("outlet_pressure_mpa"))
    pressure_basis = str(record.get("pressure_basis") or "").casefold()
    atmosphere = finite_number(record.get("atmospheric_pressure_mpa"))
    inlet_absolute = inlet_pressure
    outlet_absolute = outlet_pressure
    if pressure_basis == "gauge" and atmosphere is not None:
        inlet_absolute = (
            inlet_pressure + atmosphere
            if inlet_pressure is not None
            else None
        )
        outlet_absolute = (
            outlet_pressure + atmosphere
            if outlet_pressure is not None
            else None
        )
    pressure_drop_kpa = finite_number(record.get("pressure_drop_kpa"))
    if (
        pressure_drop_kpa is None
        and inlet_pressure is not None
        and outlet_pressure is not None
    ):
        pressure_drop_kpa = (inlet_pressure - outlet_pressure) * 1000.0
    old_match_result = (
        equipment.get("match_result", {})
        if isinstance(equipment.get("match_result"), dict)
        else {}
    )
    requested_maximum_pressure_drop_kpa = finite_number(
        _match_value(old_match_result, "maximum_pressure_drop_kpa")
    )
    liquid_cv = finite_number(_match_value(old_match_result, "cv"))
    if (
        requested_maximum_pressure_drop_kpa is None
        and pressure_drop_kpa is not None
    ):
        requested_maximum_pressure_drop_kpa = 1.2 * pressure_drop_kpa
    absolute_zero_pressure_drop_cap_kpa = (
        inlet_absolute * 1000.0
        if inlet_absolute is not None and inlet_absolute >= 0.0
        else None
    )
    if (
        requested_maximum_pressure_drop_kpa is not None
        and absolute_zero_pressure_drop_cap_kpa is not None
    ):
        maximum_pressure_drop_kpa = min(
            requested_maximum_pressure_drop_kpa,
            absolute_zero_pressure_drop_cap_kpa,
        )
    else:
        maximum_pressure_drop_kpa = requested_maximum_pressure_drop_kpa
    maximum_pressure_drop_cap_applied = bool(
        requested_maximum_pressure_drop_kpa is not None
        and maximum_pressure_drop_kpa is not None
        and requested_maximum_pressure_drop_kpa
        > maximum_pressure_drop_kpa + 1.0e-12
    )
    pressure_drop_ratio = (
        pressure_drop_kpa / 1000.0 / inlet_absolute
        if pressure_drop_kpa is not None
        and inlet_absolute is not None
        and inlet_absolute > 0.0
        else None
    )
    high_pressure_drop = (
        pressure_drop_ratio is not None and pressure_drop_ratio >= 0.5
    )
    if phase == "vapor":
        valve_type = (
            "多级降压笼式气体调节阀"
            "（低噪声内件方案候选，噪声未校核）"
            if high_pressure_drop
            else "笼式气体调节阀"
            "（低噪声内件方案候选，噪声未校核）"
        )
        valve_function = "气体减压调节"
        seat_material = "金属硬密封阀座（程序初筛）"
        leakage_class = "Class IV 候选（正式泄漏等级待控制阀标准/厂家确认）"
        capacity_status = (
            "OPEN_GAS_COMPRESSIBLE_AND_CHOKED_FLOW_CAPACITY_GATE"
        )
        inlet_temperature_c = finite_number(
            record.get("inlet_temperature_c")
        )
        phase_capacity_inputs = {
            "absolute_inlet_pressure_mpa": inlet_absolute,
            "absolute_outlet_pressure_mpa": outlet_absolute,
            "inlet_temperature_k": (
                inlet_temperature_c + 273.15
                if inlet_temperature_c is not None
                else None
            ),
            "gas_molecular_weight_kg_kmol": finite_number(
                record.get("gas_molecular_weight")
            ),
            "compressibility_factor": finite_number(
                record.get("compressibility_factor")
            ),
            "specific_heat_ratio": finite_number(
                record.get("specific_heat_ratio")
            ),
            "xT_or_xTP": finite_number(record.get("xT_or_xTP")),
            "Fp": finite_number(record.get("Fp")),
            "Fd": finite_number(record.get("Fd")),
        }
        formal_capacity_calculation_gate = (
            "formal_compressible_gas_capacity_and_choked_flow_check"
        )
    elif phase == "liquid":
        valve_type = (
            "多级抗汽蚀笼式液体调节阀"
            if high_pressure_drop
            else "单座直通液体调节阀"
        )
        valve_function = "液体节流调节"
        seat_material = "增强PTFE软密封阀座（程序初筛）"
        leakage_class = "Class VI 候选（正式泄漏等级待控制阀标准/厂家确认）"
        capacity_status = "LIQUID_CV_SCREENING_EXPECTED"
        phase_capacity_inputs = {
            "vapor_pressure_mpa": finite_number(
                record.get("vapor_pressure_mpa")
            ),
            "critical_pressure_mpa": finite_number(
                record.get("critical_pressure_mpa")
            ),
            "liquid_pressure_recovery_factor_FL": finite_number(
                record.get("liquid_pressure_recovery_factor_FL")
            ),
            "piping_geometry_factor_Fp": finite_number(
                record.get("piping_geometry_factor_Fp")
            ),
        }
        formal_capacity_calculation_gate = (
            "formal_liquid_capacity_flashing_cavitation_check"
        )
    elif phase == "mixed":
        valve_type = "耐冲蚀角式两相流调节阀"
        valve_function = "两相节流调节"
        seat_material = "硬质合金金属阀座（程序初筛）"
        leakage_class = "Class IV 候选（正式泄漏等级待控制阀标准/厂家确认）"
        capacity_status = "OPEN_TWO_PHASE_SPECIALIST_SIZING_GATE"
        phase_capacity_inputs = {
            "flow_regime": record.get("flow_regime"),
            "phase_holdup": finite_number(record.get("phase_holdup")),
            "flashing_assessment": record.get("flashing_assessment"),
            "choking_assessment": record.get("choking_assessment"),
            "erosion_velocity_limit_m_s": finite_number(
                record.get("erosion_velocity_limit_m_s")
            ),
        }
        formal_capacity_calculation_gate = (
            "formal_two_phase_specialist_sizing"
        )
    else:
        return {
            "schema": "programmatic-valve-specification-v1",
            "status": "BLOCKED_UNRESOLVED_VALVE_PHASE",
            "deterministic": True,
            "llm_used": False,
            "program_generated": True,
            "block_id": block_id,
            "phase": phase,
        }

    capacity_input_status: dict[str, dict[str, Any]] = {}
    phase_capacity_fields: list[str] = []
    for field_id, value in phase_capacity_inputs.items():
        available = value not in (None, "")
        capacity_input_status[field_id] = {
            "value": value,
            "status": (
                "AVAILABLE_FROM_ASPEN_OR_DETERMINISTIC_CONVERSION"
                if available
                else "OPEN_FORMAL_EVIDENCE_GATE"
            ),
        }
        if not available:
            phase_capacity_fields.append(field_id)

    cv_value: Any = capacity_status
    cv_state = "OPEN_FORMAL_EVIDENCE_GATE"
    cv_claim_boundary = (
        "No incompressible-liquid Cv is generated for non-liquid service. "
        "Formal flow capacity must use the phase-appropriate control-valve "
        "equation and vendor coefficients."
    )
    capacity_status_state = "OPEN_FORMAL_EVIDENCE_GATE"
    if phase == "liquid" and liquid_cv is not None and liquid_cv > 0.0:
        cv_value = liquid_cv
        cv_state = "PROGRAM_PRELIMINARY_LIQUID_CV_CALCULATED"
        capacity_status = "LIQUID_CV_SCREENING_CALCULATED"
        capacity_status_state = (
            "PROGRAM_PRELIMINARY_LIQUID_CV_CALCULATED"
        )
        cv_claim_boundary = (
            "Incompressible single-liquid Cv screening from Aspen flow, "
            "density and normal pressure drop. Formal sizing still requires "
            "vapor pressure, recovery/piping factors, travel, noise and "
            "vendor coefficients."
        )

    adjacent_materials = " ".join(str(value or "") for value in (
        pipe_value(inlet_spec, "material_grade"),
        pipe_value(outlet_spec, "material_grade"),
        pipe_value(inlet_spec, "material"),
        pipe_value(outlet_spec, "material"),
    )).casefold()
    if "316" in adjacent_materials or "s31603" in adjacent_materials:
        body_material = "CF3M 奥氏体不锈钢铸件（程序初筛）"
    elif "09mnd" in adjacent_materials or "低温" in adjacent_materials:
        body_material = "LCB 低温碳钢铸件（程序初筛）"
    else:
        body_material = "WCB 碳钢铸件（程序初筛）"
    internals_material = (
        "S31603 不锈钢阀芯/阀笼，节流面硬质合金堆焊（程序初筛）"
    )
    line_transition = (
        f"入口DN{int(round(inlet_dn))}→阀体DN{body_dn}；"
        f"阀体DN{body_dn}→出口DN{int(round(outlet_dn))}；"
        "异径件长度和布置待噪声/应力/厂家复核"
    )
    rule_payload = {
        "rule_id": "VALVE_SCREENING_FROM_ADJACENT_LINES_V1",
        "version": "1.0.0",
        "body_dn_rule": "min(inlet_line_DN,outlet_line_DN)",
        "pressure_class_rule": "max(adjacent_programmatic_PN_series_candidates)",
        "type_rule": (
            "phase plus normal_pressure_drop/absolute_inlet_pressure; "
            "ratio>=0.5 selects multistage/high-risk branch"
        ),
        "material_rule": (
            "adjacent line material route: 316L->CF3M, "
            "low-temperature steel->LCB, otherwise WCB"
        ),
        "actuator_rule": (
            "pressure-reduction control service -> pneumatic spring-return "
            "fail-close preliminary candidate"
        ),
        "maximum_pressure_drop_rule": (
            "min(requested_screening_maximum_pressure_drop,"
            "absolute_inlet_pressure_to_zero_absolute_cap)"
        ),
    }
    rule_sha256 = _canonical_sha256(rule_payload)

    def selected(
        value: Any,
        *,
        unit: str | None = None,
        state: str = "PROGRAM_PRELIMINARY_SELECTED",
        claim_boundary: str | None = None,
    ) -> dict[str, Any]:
        return {
            "value": value,
            "unit": unit,
            "state": state,
            "evidence_class": "J",
            "promotion_cap": "TYPE_SCREENING",
            "provenance": "SELECTOR_RULE/PROGRAMMATIC_VALVE_SPECIFICATION",
            "selector_rule_sha256": rule_sha256,
            "claim_boundary": claim_boundary,
        }

    formal_open = (
        "OPEN_FORMAL_EVIDENCE_GATE"
    )
    fields: dict[str, dict[str, Any]] = {
        "equipment_type": selected(valve_type),
        "valve_function": selected(valve_function),
        "selected_dn": selected(body_dn, unit="DN"),
        "dn_nps": selected(f"DN{body_dn}"),
        "pressure_class": selected(
            pressure_class,
            claim_boundary=(
                "Adjacent programmatic PN-series candidates only; not a "
                "verified valve pressure-temperature rating."
            ),
        ),
        "pressure_temperature_rating": selected(
            (
                f"{pressure_class} series candidate; material/temperature "
                "rating curve OPEN"
            ),
            state=formal_open,
        ),
        "cv": selected(
            cv_value,
            state=cv_state,
            claim_boundary=cv_claim_boundary,
        ),
        "pressure_drop_kpa": selected(
            pressure_drop_kpa,
            unit="kPa",
            claim_boundary="Normal Aspen process pressure drop only.",
        ),
        "maximum_pressure_drop_kpa": selected(
            maximum_pressure_drop_kpa,
            unit="kPa",
            claim_boundary=(
                "Program screening envelope capped at the inlet absolute "
                "pressure-to-zero-absolute physical bound. Shutoff and "
                "accident differential pressures remain formal project inputs."
            ),
        ),
        "body_material_grade": selected(body_material),
        "material": selected(body_material),
        "internals_material_grade": selected(internals_material),
        "seat_material_grade": selected(seat_material),
        "connection_type": selected(
            "RF法兰连接，配套入口/出口异径段（程序初筛）"
        ),
        "leakage_class": selected(leakage_class),
        "actuator_type": selected(
            "气动薄膜弹簧复位执行机构（程序初筛）"
        ),
        "fail_position": selected(
            "FC/失气关（减压燃气类服务的程序安全初筛；HAZOP/SIL待确认）"
        ),
        "quantity_count": selected(1, unit="count"),
        "operating_range_and_rangeability": selected(
            {
                "candidate_rangeability": "50:1",
                "formal_status": "OPEN_VENDOR_GATE",
            },
            state=formal_open,
        ),
        "flashing_check_ref": selected(
            (
                "NOT_APPLICABLE_GAS_FLASHING_CHECK"
                if phase == "vapor"
                else "OPEN_FLASHING_CHECK_GATE"
            ),
            state=(
                "NOT_APPLICABLE_PHASE_BRANCH"
                if phase == "vapor"
                else formal_open
            ),
        ),
        "cavitation_check_ref": selected(
            (
                "NOT_APPLICABLE_GAS_CAVITATION_CHECK"
                if phase == "vapor"
                else "OPEN_CAVITATION_CHECK_GATE"
            ),
            state=(
                "NOT_APPLICABLE_PHASE_BRANCH"
                if phase == "vapor"
                else formal_open
            ),
        ),
        "noise_check_ref": selected(
            "OPEN_AERODYNAMIC_OR_HYDRODYNAMIC_NOISE_GATE",
            state=formal_open,
        ),
        "standard_identity": selected(
            {
                "conditional_candidates_not_adopted": [
                    "GB/T 4213-2024 气动控制阀",
                    "GB/T 17213.2-2017 控制阀流通能力计算",
                    "GB/T 17213.15-2017 气动噪声预测",
                    "GB/T 12229-2025 通用阀门碳素钢铸件技术规范",
                ],
                "local_executable_standard_store_status": (
                    "KEY_CONTROL_VALVE_STANDARDS_NOT_IMPORTED"
                ),
            },
            state=formal_open,
        ),
        "vendor_datasheet_ref": selected(
            "OPEN_VENDOR_DATASHEET_GATE",
            state=formal_open,
        ),
        "evidence_grade": selected("J/TYPE_SCREENING"),
        "capacity_input_status": selected(
            capacity_input_status,
            state="PROGRAM_CAPACITY_INPUT_AVAILABILITY_AUDIT",
            claim_boundary=(
                "Available fields are process-basis inputs only; they do not "
                "prove completion of the phase-appropriate capacity equation."
            ),
        ),
        "pending_evidence": selected(
            [
                *phase_capacity_fields,
                formal_capacity_calculation_gate,
                "formal_pressure_temperature_rating",
                "shutoff_pressure_and_actuator_thrust",
                "rangeability_and_leakage_class",
                "noise_prediction",
                "vendor_datasheet_and_selected_model",
                "project_line_class_and_material_compatibility",
            ],
            state=formal_open,
        ),
        "line_transition_plan": selected(line_transition),
        "capacity_sizing_status": selected(
            capacity_status,
            state=capacity_status_state,
        ),
    }
    designation = (
        f"{valve_type}（程序工程规格；厂家系列/型号待容量核验）；阀体DN{body_dn}，"
        f"{pressure_class}系列候选；{body_material}；{internals_material}；"
        f"{seat_material}；RF法兰；气动薄膜弹簧复位，FC候选；"
        f"{line_transition}；容量状态={capacity_status}"
    )
    base = {
        "schema": "programmatic-valve-specification-v1",
        "version": "1.0.0",
        "status": "PRELIMINARY_CONCRETE_SPECIFICATION_SELECTED",
        "deterministic": True,
        "llm_used": False,
        "program_generated": True,
        "block_id": block_id,
        "designation": designation,
        "fields": fields,
        "selector_rule": rule_payload,
        "selector_rule_sha256": rule_sha256,
        "adjacent_line_binding": {
            "inlet_stream_id": inlet_ids[0],
            "inlet_pipe_specification_sha256": inlet_spec.get(
                "program_specification_sha256"
            ),
            "inlet_dn": int(round(inlet_dn)),
            "outlet_stream_id": outlet_ids[0],
            "outlet_pipe_specification_sha256": outlet_spec.get(
                "program_specification_sha256"
            ),
            "outlet_dn": int(round(outlet_dn)),
            "line_transition_plan": line_transition,
        },
        "process_basis": {
            "phase": phase,
            "pressure_basis": pressure_basis,
            "inlet_pressure_mpa_absolute": inlet_absolute,
            "outlet_pressure_mpa_absolute": outlet_absolute,
            "normal_pressure_drop_kpa": pressure_drop_kpa,
            "requested_maximum_pressure_drop_kpa": (
                requested_maximum_pressure_drop_kpa
            ),
            "absolute_zero_pressure_drop_cap_kpa": (
                absolute_zero_pressure_drop_cap_kpa
            ),
            "applied_maximum_pressure_drop_kpa": (
                maximum_pressure_drop_kpa
            ),
            "maximum_pressure_drop_cap_applied": (
                maximum_pressure_drop_cap_applied
            ),
            "normal_pressure_drop_ratio_to_inlet_absolute": (
                pressure_drop_ratio
            ),
            "high_pressure_drop_screen": high_pressure_drop,
            "capacity_input_status": capacity_input_status,
        },
        "maximum_pressure_drop_screening_audit": {
            "schema": "valve-maximum-pressure-drop-screening-audit-v1",
            "requested_value_kpa": requested_maximum_pressure_drop_kpa,
            "physical_upper_bound_kpa": (
                absolute_zero_pressure_drop_cap_kpa
            ),
            "applied_value_kpa": maximum_pressure_drop_kpa,
            "cap_applied": maximum_pressure_drop_cap_applied,
            "status": (
                "CAPPED_AT_ZERO_ABSOLUTE_PHYSICAL_BOUND"
                if maximum_pressure_drop_cap_applied
                else "WITHIN_ZERO_ABSOLUTE_PHYSICAL_BOUND"
                if maximum_pressure_drop_kpa is not None
                and absolute_zero_pressure_drop_cap_kpa is not None
                else "OPEN_ABSOLUTE_PRESSURE_BASIS"
            ),
            "formal_shutoff_differential_selected": False,
            "evidence_class": "J",
            "promotion_cap": "TYPE_SCREENING",
            "warning": (
                "该值只防止程序筛选压差超过入口绝压至零绝压的物理上限；"
                "它不是关断压差、事故压差或执行机构推力设计值。"
            ),
        },
        "source_binding": {
            "aspen_export_path": str(source_file),
            "aspen_export_sha256": source_sha256,
        },
        "formal_readiness": {
            "status": "BLOCKED_PRELIMINARY_ONLY",
            "open_gates": [
                *phase_capacity_fields,
                formal_capacity_calculation_gate,
                "formal_pressure_temperature_rating",
                "formal_body_trim_seat_material_compatibility",
                "shutoff_pressure_and_actuator_thrust",
                "rangeability_and_leakage_class",
                "noise_prediction",
                "vendor_datasheet_and_selected_model",
                "project_line_class_and_reducer_layout",
            ],
        },
    }
    base["program_specification_sha256"] = _canonical_sha256(base)
    for descriptor in fields.values():
        descriptor["program_specification_sha256"] = base[
            "program_specification_sha256"
        ]
    return base


def apply_programmatic_valve_specification(
    *,
    equipment: dict[str, Any],
    specification: dict[str, Any],
    rules: dict[str, Any],
    graph: dict[str, Any],
    source_file: Path,
    source_sha256: str,
) -> None:
    equipment["programmatic_valve_specification"] = specification
    old_match = (
        equipment.get("match_result", {})
        if isinstance(equipment.get("match_result"), dict)
        else {}
    )
    if specification.get("status") != "PRELIMINARY_CONCRETE_SPECIFICATION_SELECTED":
        old_match["programmatic_valve_specification"] = specification
        return
    record = (
        equipment.get("canonical_match_input", {})
        if isinstance(equipment.get("canonical_match_input"), dict)
        else {}
    )
    chain = (
        equipment.get("parameter_lineage", [])
        if isinstance(equipment.get("parameter_lineage"), list)
        else []
    )
    fields = specification.get("fields", {})
    specification_sha256 = str(
        specification.get("program_specification_sha256") or ""
    )
    matcher_projection_fields = {
        "equipment_type",
        "valve_function",
        "selected_dn",
        "pressure_class",
        "material",
        "connection_type",
    }
    for field_id, descriptor in fields.items():
        if not isinstance(descriptor, dict) or descriptor.get("value") is None:
            continue
        value = descriptor["value"]
        record[field_id] = value
        if field_id in matcher_projection_fields:
            record[field_id] = value
        chain.append(
            lineage(
                target_field=field_id,
                value=value,
                unit=str(descriptor.get("unit") or "-"),
                source_file=source_file,
                source_sha256=source_sha256,
                object_type="programmatic_valve_selector",
                object_id=str(equipment.get("aspen_block_id") or ""),
                source_field=f"programmatic_valve_specification.fields.{field_id}",
                source_path=(
                    f"programmatic_valve_specification:{specification_sha256}"
                ),
                transform="deterministic_preliminary_valve_specification",
                formula="VALVE_SCREENING_FROM_ADJACENT_LINES_V1",
                substitution=json.dumps(
                    {
                        "value": value,
                        "selector_rule_sha256": descriptor.get(
                            "selector_rule_sha256"
                        ),
                        "program_specification_sha256": specification_sha256,
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                evidence_class=str(
                    descriptor.get("evidence_class") or "J"
                ),
                result_status=str(
                    descriptor.get("state")
                    or "PROGRAM_PRELIMINARY_SELECTED"
                ),
                evidence_scope="PROGRAMMATIC_PRELIMINARY_VALVE_SELECTION",
                promotion_cap=str(
                    descriptor.get("promotion_cap") or "TYPE_SCREENING"
                ),
                warning=str(
                    descriptor.get("claim_boundary")
                    or (
                        "Program-generated preliminary valve field; formal "
                        "capacity, rating, materials and vendor evidence remain open."
                    )
                ),
            )
        )
    rerun_input = {
        key: value
        for key, value in record.items()
        if key
        not in {
            "cv",
            "pressure_temperature_rating",
            "operating_range_and_rangeability",
            "standard_identity",
            "pending_evidence",
        }
    }
    new_match = matcher.match_one(rerun_input, rules, graph)
    for key in ("input_provenance", "ignored_input_diagnostics"):
        if key in old_match:
            new_match[key] = old_match[key]
    new_match["programmatic_valve_specification"] = specification
    model = new_match.get("model_recommendation")
    leading = (
        model.get("leading_candidate")
        if isinstance(model, dict)
        and isinstance(model.get("leading_candidate"), dict)
        else None
    )
    if isinstance(leading, dict):
        leading["designation"] = specification["designation"]
        leading["program_origin"] = "PROGRAMMATIC_VALVE_SELECTOR"
        leading["source"] = {
            "kind": "deterministic_programmatic_valve_specification",
            "program_specification_sha256": specification_sha256,
            "selector_rule_sha256": specification.get(
                "selector_rule_sha256"
            ),
        }
        leading["candidate_eligibility"] = "SCREENING_ONLY_EVIDENCE_OPEN"
        leading["eligible_for_leading_candidate"] = True
        leading["eligible_for_formal_selection"] = False
        leading["formal_model"] = False
        leading["missing_gates"] = list(
            specification.get("formal_readiness", {}).get("open_gates", [])
        )
    specification_type = str(
        specification.get("fields", {})
        .get("equipment_type", {})
        .get("value")
        or ""
    )
    terminal_selection = {
        "status": "PROGRAMMATIC_VALVE_FORM_SELECTED",
        "recommended_type": specification_type,
        "selection_basis": (
            "deterministic_programmatic_valve_specification"
        ),
        "default_applied": False,
        "evidence_class": "J",
        "provisional": True,
        "rule_id": "VALVE_SCREENING_FROM_ADJACENT_LINES_V1",
        "assumption": (
            "阀型和工程规格由程序按相态、压降及相邻管线初选；容量、"
            "额定值、材料相容性、关断和厂家型号尚未闭合。"
        ),
        "terminal_scope": "equipment_form_only",
        "formal_model": False,
        "is_vendor_model": False,
        "program_specification_sha256": specification_sha256,
    }
    apply_model_screening_boundary(
        new_match,
        boundary_id="programmatic_valve_formal_design_open",
        model_status="VALVE_TYPE_SELECTED_CAPACITY_AND_RATING_BLOCKED",
        candidate_status="PRELIMINARY_PROGRAMMATIC_VALVE_TYPE_SELECTED",
        candidate_eligibility="TYPE_IDENTITY_ONLY_VALVE_DESIGN_OPEN",
        missing_gates=list(
            specification.get("formal_readiness", {}).get("open_gates", [])
        ),
        execution_status="TYPE_SELECTED_VALVE_DESIGN_BLOCKED",
        execution_scope="VALVE_FORM_AND_LINE_BINDING_SCREENING_ONLY",
        recommended_type=specification_type,
        terminal_selection=terminal_selection,
        warning=terminal_selection["assumption"],
    )
    decision = (
        new_match.get("model_decision", {})
        if isinstance(new_match.get("model_decision"), dict)
        else {}
    )
    if decision:
        decision["program_specification_sha256"] = specification_sha256
    synchronize_model_boundary_projection(
        new_match,
        boundary_id="programmatic_valve_formal_design_open",
    )
    equipment["canonical_match_input"] = record
    equipment["parameter_lineage"] = chain
    equipment["derivation_chain"] = [
        item["equation_chain"]
        for item in chain
        if isinstance(item, dict) and item.get("equation_chain")
    ]
    equipment["match_result"] = new_match


def apply_aspen_run_gate_boundaries(
    *,
    equipment: list[dict[str, Any]],
    piping: list[dict[str, Any]],
    gate: dict[str, Any],
) -> None:
    """Attach case/local Aspen health and cap all dirty-run candidates."""

    gate_payload = {
        key: value
        for key, value in gate.items()
        if key != "run_gate_sha256"
    }
    gate["run_gate_sha256"] = _canonical_sha256(gate_payload)
    attribution = (
        gate.get("raw_history_attribution", {})
        if isinstance(gate.get("raw_history_attribution"), dict)
        else {}
    )
    issue_by_block = {
        str(row.get("block_id") or ""): row
        for row in attribution.get("block_issues", [])
        if isinstance(row, dict) and str(row.get("block_id") or "")
    }
    case_dirty = str(gate.get("status") or "") != "CLEAN_RUN"
    case_snapshot = {
        "status": gate.get("status"),
        "counts": gate.get("counts"),
        "run_status_evidence": gate.get("run_status_evidence"),
        "raw_history_attribution_sha256": attribution.get(
            "attribution_sha256"
        ),
        "raw_history_count_reconciliation_status": attribution.get(
            "count_reconciliation_status"
        ),
        "run_gate_sha256": gate["run_gate_sha256"],
    }

    def annotate(
        item: dict[str, Any],
        block_ids: list[str],
        *,
        logic_node: bool,
    ) -> None:
        local_issues = [
            issue_by_block[block_id]
            for block_id in sorted(set(block_ids))
            if block_id in issue_by_block
        ]
        has_error = any(
            int(issue.get("counts", {}).get(name, 0) or 0) > 0
            for issue in local_issues
            for name in ("terminal_errors", "severe_errors", "errors")
        )
        has_warning = bool(local_issues) and not has_error
        if has_error:
            local_status = "LOCAL_ASPEN_BLOCK_ERROR"
        elif has_warning:
            local_status = "LOCAL_ASPEN_BLOCK_WARNING"
        elif case_dirty:
            local_status = "NO_LOCAL_EVENT_CASE_DIRTY"
        else:
            local_status = "CLEAN_CASE_NO_LOCAL_EVENT"
        if logic_node:
            record_kind = "logic_node"
            row_identity = str(
                item.get("aspen_block_id")
                or item.get("equipment_tag")
                or ""
            )
        elif item.get("stream_id") not in (None, ""):
            record_kind = "piping"
            row_identity = str(item.get("stream_id") or "")
        elif str(
            item.get("canonical_match_input", {}).get(
                "aspen_block_type"
            )
            if isinstance(item.get("canonical_match_input"), dict)
            else ""
        ).upper() == "PIPE":
            record_kind = "physical_pipe_block"
            row_identity = str(
                item.get("aspen_block_id")
                or item.get("equipment_tag")
                or ""
            )
        else:
            record_kind = "equipment"
            row_identity = str(
                item.get("aspen_block_id")
                or item.get("equipment_tag")
                or ""
            )
        item["aspen_run_gate"] = {
            "schema": "aspen-row-run-gate-v1",
            "bound_row": {
                "record_kind": record_kind,
                "identity": row_identity,
            },
            "case": case_snapshot,
            "related_block_ids": sorted(set(block_ids)),
            "local_status": local_status,
            "local_block_issues": local_issues,
            "process_values_formally_releasable": not case_dirty,
            "type_identity_may_remain_visible": True,
        }
        item["aspen_run_gate"]["row_gate_sha256"] = _canonical_sha256(
            item["aspen_run_gate"]
        )
        evidence_boundary = (
            item.get("evidence_boundary", {})
            if isinstance(item.get("evidence_boundary"), dict)
            else {}
        )
        if evidence_boundary is not item.get("evidence_boundary"):
            item["evidence_boundary"] = evidence_boundary
        evidence_boundary["aspen_run_gate_status"] = gate.get("status")
        evidence_boundary["aspen_row_gate_sha256"] = item[
            "aspen_run_gate"
        ]["row_gate_sha256"]
        evidence_boundary["affects_aspen_formal_use_gate"] = case_dirty
        if not case_dirty or logic_node:
            return
        if has_error:
            model_status = (
                "TYPE_IDENTITY_RETAINED_LOCAL_ASPEN_RUN_ERROR"
            )
            candidate_status = (
                "PRELIMINARY_TYPE_IDENTITY_LOCAL_ASPEN_ERROR"
            )
            execution_status = (
                "TYPE_IDENTITY_ONLY_LOCAL_ASPEN_ERROR"
            )
            warning = (
                "该设备或相邻管线块在 Aspen 原始历史中有明确错误；"
                "程序仅保留具体类型身份，相关数值不得作为正式过程依据。"
            )
        elif has_warning:
            model_status = (
                "TYPE_IDENTITY_RETAINED_LOCAL_ASPEN_RUN_WARNING"
            )
            candidate_status = (
                "PRELIMINARY_TYPE_IDENTITY_LOCAL_ASPEN_WARNING"
            )
            execution_status = (
                "TYPE_IDENTITY_ONLY_LOCAL_ASPEN_WARNING"
            )
            warning = (
                "该设备或相邻管线块在 Aspen 原始历史中有明确警告；"
                "具体类型可以显示，但工程选型仍受脏运行门禁限制。"
            )
        else:
            model_status = (
                "TYPE_IDENTITY_RETAINED_DIRTY_ASPEN_CASE"
            )
            candidate_status = (
                "PRELIMINARY_CANDIDATE_DIRTY_ASPEN_CASE"
            )
            execution_status = (
                "TYPE_IDENTITY_ONLY_DIRTY_ASPEN_CASE"
            )
            warning = (
                "Aspen 全案例运行非清洁；即使本行没有单独问题头，"
                "程序候选也只能用于类型身份和排查，不能正式释放。"
            )
        missing_gates = [
            f"aspen_case_run_gate:{gate.get('status')}",
            *[
                (
                    "aspen_raw_history_block_issue:"
                    + str(issue.get("block_id") or "")
                    + ":"
                    + str(issue.get("highest_severity") or "")
                )
                for issue in local_issues
            ],
        ]
        apply_model_screening_boundary(
            item.get("match_result", {}),
            boundary_id=(
                "aspen_run_gate:"
                + local_status
            ),
            model_status=model_status,
            candidate_status=candidate_status,
            candidate_eligibility=(
                "TYPE_IDENTITY_ONLY_DIRTY_ASPEN_RUN"
            ),
            missing_gates=missing_gates,
            execution_status=execution_status,
            execution_scope="TYPE_IDENTITY_ONLY_DIRTY_ASPEN_RUN",
            warning=warning,
        )
        synchronize_model_boundary_projection(
            item.get("match_result", {}),
            boundary_id="aspen_run_gate:" + local_status,
        )
        evidence_boundary["status"] = (
            "PRELIMINARY_DIRTY_ASPEN_RUN"
        )

    for item in equipment:
        block_id = str(item.get("aspen_block_id") or "")
        annotate(
            item,
            [block_id] if block_id else [],
            logic_node=is_default_simulation_logic_node(item),
        )
        if case_dirty and not is_default_simulation_logic_node(item):
            item["aspen_mapping_status"] = (
                "PRELIMINARY_DIRTY_ASPEN_RUN"
            )
    for item in piping:
        details = (
            item.get("pfd_edge_label_data", {})
            .get("details", {})
            if isinstance(item.get("pfd_edge_label_data"), dict)
            else {}
        )
        related = [
            *list(details.get("from_block_ids") or []),
            *list(details.get("to_block_ids") or []),
        ]
        annotate(
            item,
            [str(block_id) for block_id in related],
            logic_node=False,
        )


def finalize_program_generated_record_bindings(
    *,
    equipment: list[dict[str, Any]],
    piping: list[dict[str, Any]],
    piping_state_aliases: list[dict[str, Any]],
    source_export_sha256: str,
) -> dict[str, Any]:
    """Bind each final row to its program result, lineage and Aspen run gate."""

    rows: list[tuple[str, str, dict[str, Any]]] = []
    for item in equipment:
        block_type = str(
            item.get("canonical_match_input", {}).get("aspen_block_type")
            if isinstance(item.get("canonical_match_input"), dict)
            else ""
        ).upper()
        if is_default_simulation_logic_node(item):
            record_kind = "logic_node"
        elif block_type == "PIPE":
            record_kind = "physical_pipe_block"
        else:
            record_kind = "equipment"
        rows.append((
            record_kind,
            str(
                item.get("aspen_block_id")
                or item.get("equipment_tag")
                or ""
            ),
            item,
        ))
    rows.extend(
        (
            "piping",
            str(item.get("stream_id") or ""),
            item,
        )
        for item in piping
    )
    rows.extend(
        (
            "pfd_endpoint_state_alias",
            str(item.get("stream_id") or ""),
            item,
        )
        for item in piping_state_aliases
    )

    summary_rows: list[dict[str, Any]] = []
    for record_kind, identity, item in rows:
        match_result = (
            item.get("match_result", {})
            if isinstance(item.get("match_result"), dict)
            else {}
        )
        model = (
            match_result.get("model_recommendation", {})
            if isinstance(
                match_result.get("model_recommendation"), dict
            )
            else {}
        )
        decision = (
            match_result.get("model_decision", {})
            if isinstance(match_result.get("model_decision"), dict)
            else {}
        )
        program_specification_hashes = sorted({
            str(value).upper()
            for value in (
                item.get("programmatic_pipe_specification", {}).get(
                    "program_specification_sha256"
                )
                if isinstance(
                    item.get("programmatic_pipe_specification"), dict
                )
                else None,
                item.get("programmatic_valve_specification", {}).get(
                    "program_specification_sha256"
                )
                if isinstance(
                    item.get("programmatic_valve_specification"), dict
                )
                else None,
                decision.get("program_specification_sha256"),
            )
            if value not in (None, "")
        })
        run_gate = (
            item.get("aspen_run_gate", {})
            if isinstance(item.get("aspen_run_gate"), dict)
            else {}
        )
        endpoint_audit = (
            item.get("endpoint_pressure_drop_audit", {})
            if isinstance(
                item.get("endpoint_pressure_drop_audit"), dict
            )
            else {}
        )
        leading = (
            model.get("leading_candidate", {})
            if isinstance(model.get("leading_candidate"), dict)
            else {}
        )
        binding: dict[str, Any] = {
            "schema": "program-generated-stage1-row-binding-v1",
            "engine_version": ENGINE_VERSION,
            "deterministic": True,
            "llm_used": False,
            "program_generated": True,
            "bound_row": {
                "record_kind": record_kind,
                "identity": identity,
            },
            "source_export_sha256": source_export_sha256,
            "aspen_row_gate_sha256": run_gate.get(
                "row_gate_sha256"
            ),
            "canonical_match_input_sha256": _canonical_sha256(
                item.get("canonical_match_input", {})
            ),
            "parameter_lineage_sha256": _canonical_sha256(
                item.get("parameter_lineage", [])
            ),
            "derivation_chain_sha256": _canonical_sha256(
                item.get("derivation_chain", [])
            ),
            "input_provenance_snapshot_sha256": (
                item.get("input_provenance", {}).get(
                    "final_snapshot_sha256"
                )
                if isinstance(item.get("input_provenance"), dict)
                else None
            ),
            "match_result_sha256": _canonical_sha256(match_result),
            "evidence_boundary_sha256": _canonical_sha256(
                item.get("evidence_boundary", {})
            ),
            "program_specification_sha256s": (
                program_specification_hashes
            ),
            "endpoint_pressure_drop_audit_sha256": (
                endpoint_audit.get("audit_sha256")
            ),
            "final_type_projection": {
                "recommended_type": model.get("recommended_type"),
                "leading_candidate_designation": leading.get(
                    "designation"
                ),
                "generated_candidate_designation": decision.get(
                    "generated_candidate_designation"
                ),
                "candidate_model": decision.get("candidate_model"),
                "model_status": decision.get("model_status"),
                "selection_execution_status": (
                    model.get("selection_execution", {}).get("status")
                    if isinstance(
                        model.get("selection_execution"), dict
                    )
                    else None
                ),
            },
        }
        binding["binding_sha256"] = _canonical_sha256(binding)
        final_sha256 = binding["binding_sha256"]
        item["program_generated_record_binding"] = binding
        item["program_generated_record_sha256"] = final_sha256
        if record_kind in {"equipment", "physical_pipe_block"}:
            item["equipment_program_specification_sha256"] = (
                final_sha256
            )
        if record_kind in {"piping", "physical_pipe_block"}:
            item["pipe_program_specification_sha256"] = final_sha256
        if record_kind == "pfd_endpoint_state_alias":
            item["state_alias_binding_sha256"] = final_sha256
        summary_rows.append({
            "record_kind": record_kind,
            "identity": identity,
            "program_generated_record_sha256": final_sha256,
        })
    summary = {
        "schema": "program-generated-stage1-row-binding-summary-v1",
        "status": (
            "PASS"
            if all(row["identity"] for row in summary_rows)
            and len({
                row["program_generated_record_sha256"]
                for row in summary_rows
            })
            == len(summary_rows)
            else "BLOCKED_MISSING_OR_NONUNIQUE_ROW_BINDING"
        ),
        "row_count": len(summary_rows),
        "unique_binding_count": len({
            row["program_generated_record_sha256"]
            for row in summary_rows
        }),
        "rows": summary_rows,
    }
    summary["summary_sha256"] = _canonical_sha256(summary)
    return summary


def refresh_final_parameter_lineage_snapshots(
    *,
    equipment: list[dict[str, Any]],
    piping: list[dict[str, Any]],
    piping_state_aliases: list[dict[str, Any]],
) -> dict[str, Any]:
    """Synchronize provenance summaries after all deterministic enrichments."""

    rows: list[tuple[str, str, dict[str, Any]]] = []
    for item in equipment:
        block_type = str(
            item.get("canonical_match_input", {}).get("aspen_block_type")
            if isinstance(item.get("canonical_match_input"), dict)
            else ""
        ).upper()
        if is_default_simulation_logic_node(item):
            record_kind = "logic_node"
        elif block_type == "PIPE":
            record_kind = "physical_pipe_block"
        else:
            record_kind = "equipment"
        rows.append((
            record_kind,
            str(
                item.get("aspen_block_id")
                or item.get("equipment_tag")
                or ""
            ),
            item,
        ))
    rows.extend(
        (
            "piping",
            str(item.get("stream_id") or ""),
            item,
        )
        for item in piping
    )
    rows.extend(
        (
            "pfd_endpoint_state_alias",
            str(item.get("stream_id") or ""),
            item,
        )
        for item in piping_state_aliases
    )
    summary_rows: list[dict[str, Any]] = []
    for record_kind, identity, item in rows:
        lineage = (
            item.get("parameter_lineage", [])
            if isinstance(item.get("parameter_lineage"), list)
            else []
        )
        match_result = (
            item.get("match_result", {})
            if isinstance(item.get("match_result"), dict)
            else {}
        )
        previous = dict(
            item.get("input_provenance", {})
            if isinstance(item.get("input_provenance"), dict)
            else {}
        )
        previous.pop("final_snapshot_sha256", None)
        initial_count = previous.get(
            "initial_process_lineage_count",
            previous.get("lineage_count", 0),
        )
        evidence_classes = sorted({
            str(row.get("evidence_class") or "U")
            for row in lineage
            if isinstance(row, dict)
        })
        provenance = {
            **previous,
            "lineage_scope": (
                "FINAL_PARAMETER_LINEAGE_AFTER_ALL_DETERMINISTIC_"
                "PROGRAMMATIC_ENRICHMENTS"
            ),
            "initial_process_lineage_count": initial_count,
            "lineage_count": len(lineage),
            "final_parameter_lineage_count": len(lineage),
            "final_parameter_lineage_sha256": _canonical_sha256(
                lineage
            ),
            "evidence_class_counts": {
                evidence_class: sum(
                    1
                    for row in lineage
                    if isinstance(row, dict)
                    and str(row.get("evidence_class") or "U")
                    == evidence_class
                )
                for evidence_class in evidence_classes
            },
            "summary_synchronized_after_programmatic_enrichment": True,
        }
        provenance["final_snapshot_sha256"] = _canonical_sha256(
            provenance
        )
        item["input_provenance"] = provenance
        match_result["input_provenance"] = dict(provenance)
        calculations = (
            match_result.get("calculations", [])
            if isinstance(match_result.get("calculations"), list)
            else []
        )
        item["derivation_chain"] = [
            row["equation_chain"]
            for row in lineage
            if isinstance(row, dict)
            and isinstance(row.get("equation_chain"), dict)
        ] + [
            row["equation_chain"]
            for row in calculations
            if isinstance(row, dict)
            and isinstance(row.get("equation_chain"), dict)
        ]
        summary_rows.append({
            "record_kind": record_kind,
            "identity": identity,
            "lineage_count": len(lineage),
            "final_parameter_lineage_sha256": provenance[
                "final_parameter_lineage_sha256"
            ],
            "final_snapshot_sha256": provenance[
                "final_snapshot_sha256"
            ],
        })
    summary = {
        "schema": "final-parameter-lineage-summary-v1",
        "status": (
            "PASS"
            if len(summary_rows) == len(rows)
            and all(row["identity"] for row in summary_rows)
            and len({
                (row["record_kind"], row["identity"])
                for row in summary_rows
            })
            == len(summary_rows)
            else "BLOCKED_LINEAGE_SNAPSHOT_INCOMPLETE"
        ),
        "row_count": len(summary_rows),
        "rows": summary_rows,
    }
    summary["summary_sha256"] = _canonical_sha256(summary)
    return summary


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
    raw_stream_rows = (
        bundle.get("streams", []) if isinstance(bundle.get("streams"), list) else []
    )
    raw_block_rows = (
        bundle.get("blocks", []) if isinstance(bundle.get("blocks"), list) else []
    )
    streams_list: list[dict[str, Any]] = []
    stream_error_rows: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    isolated_stream_diagnostics: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_stream_rows):
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
    for raw in raw_block_rows:
        if not isinstance(raw, dict):
            errors.append({"code": "BLOCK_ROW_NOT_OBJECT"})
            continue
        item, item_errors = normalize_block(raw, units)
        blocks.append(item)
        structural, diagnostics = partition_normalization_errors(item_errors)
        errors.extend(structural)
        normalization_diagnostics.extend(diagnostics)
    endpoints = stream_endpoints(blocks)
    topology_integrity = bidirectional_topology_integrity(
        raw_stream_rows,
        raw_block_rows,
        blocks,
    )
    if topology_integrity.get("status") == "FAILED":
        errors.append({
            "code": "ASPEN_BIDIRECTIONAL_TOPOLOGY_INTEGRITY_FAILED",
            "topology_sha256": topology_integrity.get("topology_sha256"),
            "issues": topology_integrity.get("issues", []),
        })
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
        "bidirectional_topology_sha256": topology_integrity.get("topology_sha256"),
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
            "pfd_mapping_sha256": pfd_mapping_sha256,
            "topology_integrity": topology_integrity,
            "normalization_diagnostics": normalization_diagnostics,
            "isolated_stream_diagnostics": isolated_stream_diagnostics,
        }
    viscosity_fallback_diagnostics = enrich_stream_viscosities(
        streams_list,
        bundle=bundle,
        source_export_sha256=source_sha256,
    )
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
    gate = run_gate(case_data, blocks, source_file)
    pump_power_history_enrichment = (
        enrich_pump_power_from_verified_run_history(blocks, gate)
    )
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
    physical_pipe_block_ids = {
        str(block.get("block_id") or "")
        for block in blocks
        if str(block.get("block_type") or "").upper()
        in PHYSICAL_PIPING_BLOCK_TYPES
        and str(block.get("block_id") or "")
    }
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
    all_pfd_piping_records: list[dict[str, Any]] = []
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
        pipe_entity = classify_pfd_stream_pipe_entity(
            stream_id=stream_id,
            endpoints=endpoints[stream_id],
            physical_pipe_block_ids=physical_pipe_block_ids,
        )
        all_pfd_piping_records.append(
            derive_piping(
                stream,
                endpoints[stream_id],
                case_data,
                source_file,
                source_sha256,
                rules,
                graph,
                pipe_entity,
            )
        )
    piping = [
        item
        for item in all_pfd_piping_records
        if item.get("counted_as_physical_pipe") is True
        and item.get("alias_only") is not True
    ]
    piping_state_aliases = [
        item
        for item in all_pfd_piping_records
        if item.get("alias_only") is True
    ]
    piping_by_stream = {
        str(item.get("stream_id") or ""): item
        for item in all_pfd_piping_records
        if str(item.get("stream_id") or "")
    }
    programmatic_valve_specifications: list[dict[str, Any]] = []
    for item in equipment:
        block = blocks_by_id.get(str(item.get("aspen_block_id") or ""), {})
        if str(block.get("block_type") or "").upper() != "VALVE":
            continue
        specification = build_programmatic_valve_specification(
            equipment=item,
            block=block,
            piping_by_stream=piping_by_stream,
            source_file=source_file,
            source_sha256=source_sha256,
        )
        apply_programmatic_valve_specification(
            equipment=item,
            specification=specification,
            rules=rules,
            graph=graph,
            source_file=source_file,
            source_sha256=source_sha256,
        )
        programmatic_valve_specifications.append(specification)
    final_parameter_lineage_summary = (
        refresh_final_parameter_lineage_snapshots(
            equipment=equipment,
            piping=piping,
            piping_state_aliases=piping_state_aliases,
        )
    )
    apply_aspen_run_gate_boundaries(
        equipment=equipment,
        piping=all_pfd_piping_records,
        gate=gate,
    )
    program_generated_record_binding_summary = (
        finalize_program_generated_record_bindings(
            equipment=equipment,
            piping=piping,
            piping_state_aliases=piping_state_aliases,
            source_export_sha256=source_sha256,
        )
    )
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
    if final_parameter_lineage_summary["status"] != "PASS":
        formal_use_blockers.append({
            "code": "FINAL_PARAMETER_LINEAGE_SNAPSHOT_FAILED",
            "status": final_parameter_lineage_summary["status"],
            "summary_sha256": final_parameter_lineage_summary[
                "summary_sha256"
            ],
        })
    if program_generated_record_binding_summary["status"] != "PASS":
        formal_use_blockers.append({
            "code": "PROGRAM_GENERATED_ROW_BINDING_FAILED",
            "status": program_generated_record_binding_summary["status"],
            "summary_sha256": (
                program_generated_record_binding_summary["summary_sha256"]
            ),
        })
    pipe_entity_classification_issues = [
        {
            "stream_id": item.get("stream_id"),
            "pipe_entity_scope": item.get("pipe_entity_scope"),
            "pipe_entity_id": item.get("pipe_entity_id"),
            "alias_status": item.get("alias_status"),
            "canonical_pipe_entity_ids": list(
                item.get("canonical_pipe_entity_ids", [])
            ),
        }
        for item in all_pfd_piping_records
        if item.get("classification_complete") is not True
    ]
    if pipe_entity_classification_issues:
        formal_use_blockers.append({
            "code": "PIPE_ENTITY_CLASSIFICATION_AMBIGUOUS",
            "issues": pipe_entity_classification_issues,
        })
    internal_viscosity_estimates = [
        item
        for item in viscosity_fallback_diagnostics
        if item.get("internal_correlation_used") is True
    ]
    formal_use_blockers.extend({
        "code": "INTERNAL_VISCOSITY_CORRELATION_PRELIMINARY_ONLY",
        "stream_id": item.get("stream_id"),
        "diagnostic_sha256": item.get("diagnostic_sha256"),
        "warning_codes": item.get("warning_codes", []),
        "promotion_cap": item.get("promotion_cap", "TYPE_SCREENING"),
    } for item in internal_viscosity_estimates)
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
    canonical_physical_pipe_entity_ids = sorted({
        *[
            str(item.get("pipe_entity_id") or "")
            for item in equipment
            if item.get("counted_as_physical_pipe") is True
            and str(item.get("pipe_entity_id") or "")
        ],
        *[
            str(item.get("pipe_entity_id") or "")
            for item in piping
            if item.get("counted_as_physical_pipe") is True
            and str(item.get("pipe_entity_id") or "")
        ],
    })
    canonical_physical_pipe_entity_id_set = set(
        canonical_physical_pipe_entity_ids
    )
    orphan_alias_bindings = [
        {
            "stream_id": item.get("stream_id"),
            "missing_canonical_pipe_entity_ids": sorted(
                set(item.get("canonical_pipe_entity_ids", []))
                - canonical_physical_pipe_entity_id_set
            ),
        }
        for item in piping_state_aliases
        if (
            set(item.get("canonical_pipe_entity_ids", []))
            - canonical_physical_pipe_entity_id_set
        )
    ]
    pipe_entity_reconciliation_status = (
        "PASS_NO_ENDPOINT_STATE_DOUBLE_COUNT"
        if not pipe_entity_classification_issues
        and not orphan_alias_bindings
        else "BLOCKED_AMBIGUOUS_OR_ORPHAN_PIPE_ENTITY_BINDING"
    )
    pipe_entity_reconciliation: dict[str, Any] = {
        "schema": "pipe-entity-reconciliation-v1",
        "status": pipe_entity_reconciliation_status,
        "policy": (
            "An explicit Aspen PIPE block is the canonical physical pipe "
            "entity. Any adjacent PFD material stream is retained only as "
            "that block's endpoint-state alias. A PFD material stream not "
            "adjacent to an Aspen PIPE block remains a canonical PFD pipe "
            "segment."
        ),
        "aspen_physical_pipe_block_count": sum(
            item.get("pipe_entity_scope")
            == "ASPEN_PHYSICAL_PIPE_BLOCK"
            and item.get("counted_as_physical_pipe") is True
            for item in equipment
        ),
        "independent_pfd_pipe_segment_count": len(piping),
        "pfd_endpoint_state_alias_count": len(
            piping_state_aliases
        ),
        "physical_pipe_entity_count": len(
            canonical_physical_pipe_entity_ids
        ),
        "canonical_physical_pipe_entity_ids": (
            canonical_physical_pipe_entity_ids
        ),
        "endpoint_state_aliases": [
            {
                "stream_id": item.get("stream_id"),
                "pipe_entity_id": item.get("pipe_entity_id"),
                "canonical_pipe_entity_ids": list(
                    item.get("canonical_pipe_entity_ids", [])
                ),
                "endpoint_pressure_drop_audit_sha256": (
                    item.get("endpoint_pressure_drop_audit", {}).get(
                        "audit_sha256"
                    )
                    if isinstance(
                        item.get("endpoint_pressure_drop_audit"), dict
                    )
                    else None
                ),
            }
            for item in piping_state_aliases
        ],
        "classification_issues": pipe_entity_classification_issues,
        "orphan_alias_bindings": orphan_alias_bindings,
        "source_export_sha256": source_sha256,
        "pfd_mapping_sha256": pfd_mapping_sha256,
    }
    pipe_entity_reconciliation["reconciliation_sha256"] = (
        _canonical_sha256(pipe_entity_reconciliation)
    )
    return {
        "schema": "aspen-equipment-derivation-result-v1",
        "engine_version": ENGINE_VERSION,
        "deterministic": True,
        "llm_used": False,
        "status": "DERIVED",
        "source_export_path": str(source_file),
        "source_export_sha256": source_sha256,
        "pfd_mapping_sha256": pfd_mapping_sha256,
        "topology_integrity": topology_integrity,
        "case_id": bundle.get("case", {}).get("case_id") if isinstance(bundle.get("case"), dict) else None,
        "source_case_evidence": case_evidence,
        "aspen_run_gate": gate,
        "pump_power_history_enrichment": (
            pump_power_history_enrichment
        ),
        "formal_use_gate": process_basis_gate,
        "formal_use_blockers": formal_use_blockers,
        "normalization_diagnostic_count": len(normalization_diagnostics),
        "normalization_diagnostics": normalization_diagnostics,
        "viscosity_fallback_summary": {
            "schema": "viscosity-fallback-summary-v1",
            "authority_order": [
                "exported_mixture_MUMX",
                "exported_phase_specific_MUMX_for_unambiguous_single_phase",
                "source_bound_internal_correlation",
                "blocked_without_default",
            ],
            "stream_count": len(viscosity_fallback_diagnostics),
            "internal_correlation_used_count": len(
                internal_viscosity_estimates
            ),
            "aspen_or_not_needed_count": sum(
                str(item.get("status") or "").startswith(
                    ("NOT_NEEDED_", "ASPEN_PHASE_SPECIFIC_")
                )
                for item in viscosity_fallback_diagnostics
            ),
            "blocked_count": sum(
                item.get("status") == "BLOCKED"
                or str(item.get("status") or "").startswith("BLOCKED_")
                for item in viscosity_fallback_diagnostics
            ),
            "formal_design_evidence": False,
            "correlation_promotion_cap": "TYPE_SCREENING",
            "mandatory_warning": (
                "Internal-correlation viscosity is not Aspen-extracted and is "
                "permitted only for preliminary single-phase hydraulics."
            ),
            "diagnostics": viscosity_fallback_diagnostics,
        },
        "equipment_count": len(equipment),
        "equipment": equipment,
        "piping_count": len(piping),
        "piping": piping,
        "piping_state_alias_count": len(piping_state_aliases),
        "piping_state_aliases": piping_state_aliases,
        "physical_pipe_entity_count": (
            pipe_entity_reconciliation[
                "physical_pipe_entity_count"
            ]
        ),
        "pipe_entity_reconciliation": pipe_entity_reconciliation,
        "program_generated_record_binding_summary": (
            program_generated_record_binding_summary
        ),
        "final_parameter_lineage_summary": (
            final_parameter_lineage_summary
        ),
        "programmatic_valve_specification_summary": {
            "count": len(programmatic_valve_specifications),
            "selected_count": sum(
                item.get("status")
                == "PRELIMINARY_CONCRETE_SPECIFICATION_SELECTED"
                for item in programmatic_valve_specifications
            ),
            "blocked_count": sum(
                item.get("status")
                != "PRELIMINARY_CONCRETE_SPECIFICATION_SELECTED"
                for item in programmatic_valve_specifications
            ),
            "specification_hashes": [
                item.get("program_specification_sha256")
                for item in programmatic_valve_specifications
                if item.get("program_specification_sha256")
            ],
        },
        "isolated_stream_diagnostics": isolated_stream_diagnostics,
        "piping_evidence_boundary": {
            "status": "PROGRAMMATIC_PRELIMINARY_PIPE_SPECIFICATIONS_PROJECTED",
            "affects_aspen_formal_use_gate": (
                process_basis_gate
                != "ELIGIBLE_AS_PROCESS_BASIS"
            ),
            "aspen_formal_use_gate_snapshot": process_basis_gate,
            "preliminary_engineering_policy_applied": True,
            "established_by_program_for_type_screening": [
                "design_pressure_mpa",
                "design_temperature_c",
                "hydraulic_dn_candidate",
                "independent_metric_outer_diameter_candidate",
                "independent_metric_wall_thickness_candidate",
                "non_SCH_metric_OD_x_wall_candidate",
                "material_grade_route",
                "PN_series_candidate",
                "piping_class_candidate_code",
                "corrosion_allowance_candidate",
                "hydraulic_pressure_gradient_per_100m",
                "preliminary_test_and_nde_route",
            ],
            "formal_not_established": [
                "single_standard_pipe_DN_OD_wall_combination",
                "project_authority_piping_class",
                "formal_pressure_class_or_pressure_temperature_rating",
                "product_standard_scope_and_manufacturability",
                "material_compatibility_acceptance",
                "code_wall_thickness_with_negative_tolerance",
                "pressure_temperature_rating_acceptance",
                "total_line_pressure_drop_without_length_and_fittings",
                "mechanical_stress_verification",
                "support_design",
                "formal_test_and_nde_plan",
                "vendor_model",
            ],
        },
        "non_aspen_boundaries": [
            "Aspen process results do not set design pressure or design temperature.",
            (
                "When Aspen MUMX is absent, a source-bound internal viscosity "
                "correlation may fill a single-phase preliminary hydraulic "
                "screen only with evidence class J and a mandatory warning; "
                "it is not Aspen evidence and blocks formal release."
            ),
            "The program may issue a clearly marked J/type-screening pipe specification from registered policies and verified dimension/PN records; Aspen alone does not prove that mechanical selection.",
            "Aspen process results do not prove material compatibility, corrosion allowance acceptance, code wall thickness, internals, vendor model, or performance curve.",
            "Dirty or unverified Aspen runs remain provisional even when a numeric derivation is possible.",
            (
                "PFD material streams provide topology and process properties; "
                "the independent deterministic pipe calculator supplies a "
                "hydraulic DN candidate, a separate non-SCH metric OD/wall "
                "candidate, a program-assembled line-class candidate code, "
                "material route and hydraulics with explicit hashes and open "
                "formal gates. It does not join the GB/T 12459 fitting-table "
                "record and GB/T 17395 pipe-dimension record into one formal "
                "pipe standard conclusion."
            ),
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
