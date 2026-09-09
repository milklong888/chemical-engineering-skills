from __future__ import annotations

import math
import re


M2_TO_FT2 = 10.7639104167
M3_S_TO_US_GPM = 15850.323141489
FT_PER_M = 3.280839895
R_BAR_M3_PER_KMOL_K = 0.08314462618


def aspen_float(value: str) -> float:
    return float(str(value).replace(",", "").strip())


def lmtd(delta_a: float, delta_b: float) -> float:
    if delta_a <= 0 or delta_b <= 0:
        raise ValueError("terminal temperature differences must be positive")
    if abs(delta_a - delta_b) <= 1e-12:
        return delta_a
    return (delta_a - delta_b) / math.log(delta_a / delta_b)


def heat_exchanger_area_ft2(
    duty_gcal_h: float,
    process_inlet_c: float,
    process_outlet_c: float,
    utility_inlet_c: float,
    utility_outlet_c: float,
    overall_u_kcal_h_m2_k: float,
    *,
    service: str,
    overdesign_factor: float = 1.0,
) -> dict[str, float]:
    if overall_u_kcal_h_m2_k <= 0 or overdesign_factor <= 0:
        raise ValueError("overall U and overdesign factor must be positive")
    if service == "cooling":
        delta_a = process_inlet_c - utility_outlet_c
        delta_b = process_outlet_c - utility_inlet_c
    elif service == "heating":
        delta_a = utility_inlet_c - process_outlet_c
        delta_b = utility_outlet_c - process_inlet_c
    else:
        raise ValueError("service must be 'cooling' or 'heating'")
    mean_delta = lmtd(delta_a, delta_b)
    bare_area_m2 = abs(duty_gcal_h) * 1_000_000.0 / (
        overall_u_kcal_h_m2_k * mean_delta
    )
    design_area_m2 = bare_area_m2 * overdesign_factor
    return {
        "delta_a_c": delta_a,
        "delta_b_c": delta_b,
        "lmtd_c": mean_delta,
        "bare_area_m2": bare_area_m2,
        "design_area_m2": design_area_m2,
        "design_area_ft2": design_area_m2 * M2_TO_FT2,
    }


def ideal_gas_volume_m3_s(
    molar_flow_kmol_h: float,
    temperature_c: float,
    pressure_bar_abs: float,
) -> float:
    if molar_flow_kmol_h <= 0 or pressure_bar_abs <= 0:
        raise ValueError("molar flow and absolute pressure must be positive")
    return (
        molar_flow_kmol_h
        * R_BAR_M3_PER_KMOL_K
        * (temperature_c + 273.15)
        / pressure_bar_abs
        / 3600.0
    )


def column_diameter_ft(vapor_volume_m3_s: float, superficial_velocity_m_s: float) -> float:
    if vapor_volume_m3_s <= 0 or superficial_velocity_m_s <= 0:
        raise ValueError("vapor volume and superficial velocity must be positive")
    area_m2 = vapor_volume_m3_s / superficial_velocity_m_s
    return math.sqrt(4.0 * area_m2 / math.pi) * FT_PER_M


def round_up_standard(value: float, increment: float, minimum: float) -> float:
    if value <= 0 or increment <= 0 or minimum <= 0:
        raise ValueError("value, increment, and minimum must be positive")
    return max(minimum, math.ceil(value / increment - 1e-12) * increment)


def split_aspen_report_by_block(report_text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current = ""
    for line in report_text.splitlines():
        match = re.search(r"\bBLOCK:\s+(\S+)\s+MODEL:\s+(\S+)", line)
        if match:
            current = match.group(1)
        if current:
            sections.setdefault(current, []).append(line)
    return {block: "\n".join(lines) for block, lines in sections.items()}


def _read_named_value(section: str, label: str) -> float | None:
    match = re.search(
        rf"^[ \t]*{re.escape(label)}"
        rf"(?:[ \t]+[A-Za-z][A-Za-z0-9()/.-]*)*"
        rf"[ \t]+([-+]?\d[\d,.]*(?:E[-+]?\d+)?)[ \t]*$",
        section,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    return aspen_float(match.group(1)) if match else None


def parse_radfrac_results(report_text: str) -> dict[str, dict[str, float]]:
    results: dict[str, dict[str, float]] = {}
    for block, section in split_aspen_report_by_block(report_text).items():
        if not re.search(rf"BLOCK:\s+{re.escape(block)}\s+MODEL:\s+RADFRAC", section):
            continue
        fields = {
            "number_of_stages": "NUMBER OF STAGES",
            "pressure_bar": "P-SPEC",
            "top_temperature_c": "TOP STAGE TEMPERATURE",
            "bottom_temperature_c": "BOTTOM STAGE TEMPERATURE",
            "top_liquid_kmol_h": "TOP STAGE LIQUID FLOW",
            "bottom_liquid_kmol_h": "BOTTOM STAGE LIQUID FLOW",
            "top_vapor_kmol_h": "TOP STAGE VAPOR FLOW",
            "boilup_vapor_kmol_h": "BOILUP VAPOR FLOW",
            "condenser_duty_gcal_h": "CONDENSER DUTY (W/O SUBCOOL)",
            "reboiler_duty_gcal_h": "REBOILER DUTY",
            "molar_reflux_ratio": "MOLAR REFLUX RATIO",
        }
        parsed = {}
        for name, label in fields.items():
            if name == "pressure_bar":
                match = re.search(
                    r"P-SPEC\s+STAGE\s+\d+\s+PRES,\s*BAR\s+([-+]?\d[\d,.]*(?:E[-+]?\d+)?)",
                    section,
                    flags=re.IGNORECASE,
                )
                value = aspen_float(match.group(1)) if match else None
            else:
                value = _read_named_value(section, label)
            if value is not None:
                parsed[name] = value
        if parsed:
            results[block] = parsed
    return results


def parse_pump_results(report_text: str) -> dict[str, dict[str, float]]:
    results: dict[str, dict[str, float]] = {}
    for block, section in split_aspen_report_by_block(report_text).items():
        if not re.search(rf"BLOCK:\s+{re.escape(block)}\s+MODEL:\s+PUMP", section):
            continue
        labels = {
            "pressure_change_bar": "PRESSURE CHANGE",
            "fluid_power_kw": "FLUID POWER",
            "brake_power_kw": "BRAKE POWER",
            "electricity_kw": "ELECTRICITY",
            "pump_efficiency": "PUMP EFFICIENCY USED",
            "head_m": "HEAD DEVELOPED",
        }
        parsed = {}
        flow_match = re.search(
            r"^[ \t]*VOLUMETRIC FLOW RATE[ \t]+(CUM/HR|CUM/SEC)"
            r"[ \t]+([-+]?\d[\d,.]*(?:E[-+]?\d+)?)[ \t]*$",
            section,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        if flow_match:
            flow_value = aspen_float(flow_match.group(2))
            flow_unit = flow_match.group(1).upper()
            flow_m3_s = flow_value / 3600.0 if flow_unit == "CUM/HR" else flow_value
            parsed["volumetric_flow_report_value"] = flow_value
            parsed["volumetric_flow_report_unit"] = flow_unit
            parsed["volumetric_flow_m3_s"] = flow_m3_s
            parsed["volumetric_flow_us_gpm"] = flow_m3_s * M3_S_TO_US_GPM
        for name, label in labels.items():
            value = _read_named_value(section, label)
            if value is not None:
                parsed[name] = value
        if parsed:
            results[block] = parsed
    return results
