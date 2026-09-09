from __future__ import annotations

import json
import math
import re
import csv
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from case_profile import CaseGlobal, case_value, require_case_profile, configure_case_profile


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
DATA = ROOT / "data"
CURRENT_DOC_IDS = CaseGlobal("CURRENT_DOC_IDS")


@dataclass
class CalcRow:
    module: str
    item: str
    source_location: str
    formula: str
    input_values: dict[str, Any]
    value: float
    unit: str
    document_value_raw: str = ""
    document_numeric_value: float | None = None
    tolerance: float | None = None
    abs_error: float | None = None
    rel_error: float | None = None
    pass_check: bool | None = None
    reliability_class: str = "A_formula_reproduced"
    status: str = "reproduced"
    note: str = ""


@dataclass
class ParameterLedgerRow:
    chapter: str
    equipment_family: str
    object_id: str
    parameter: str
    value: str
    unit: str
    source_document: str
    source_table: str
    source_location: str
    source_type: str
    evidence_class: str
    action: str
    judgment_links: str
    scriptable_formula: str
    note: str = ""


def pipe_required_diameter(flow_m3_h: float, velocity_m_s: float) -> float:
    return math.sqrt(4 * flow_m3_h / (3600 * math.pi * velocity_m_s))


def pipe_actual_velocity(flow_m3_h: float, od_m: float, thickness_m: float) -> float:
    inner_d = od_m - 2 * thickness_m
    return 4 * flow_m3_h / (3600 * math.pi * inner_d**2)


def design_pressure(operating_pressure: float, factor: float) -> float:
    return operating_pressure * factor


def cylinder_calc_thickness(p_mpa: float, di_mm: float, sigma_mpa: float, weld_eff: float) -> float:
    return p_mpa * di_mm / (2 * sigma_mpa * weld_eff - p_mpa)


def ellipsoidal_head_calc_thickness(
    p_mpa: float, di_mm: float, sigma_mpa: float, weld_eff: float
) -> float:
    return p_mpa * di_mm / (2 * sigma_mpa * weld_eff - 0.5 * p_mpa)


def minimum_nominal_thickness(calc_mm: float, min_calc_mm: float, c1_mm: float, c2_mm: float) -> float:
    return max(calc_mm, min_calc_mm) + c1_mm + c2_mm


def tower_bottom_liquid_height(flow_m3_h: float, hold_minutes: float, diameter_m: float) -> float:
    volume = flow_m3_h * hold_minutes / 60
    area = math.pi * diameter_m**2 / 4
    return volume / area


def source_k_to_aspen(source_value: float, atm_pa: float = 101300.0) -> float:
    """mmol gcat^-1 atm^-0.5 h^-1 -> kmol kgcat^-1 Pa^-0.5 s^-1."""
    return source_value * 1e-3 / 3600 / math.sqrt(atm_pa)


def arrhenius_from_two_points(t1_k: float, k1: float, t2_k: float, k2: float) -> tuple[float, float]:
    """Fit ln(k) = ln(A) - E/(R*T). Returns A and E in kJ/mol."""
    r_j_mol_k = 8.31446261815324
    x1 = 1 / (r_j_mol_k * t1_k)
    x2 = 1 / (r_j_mol_k * t2_k)
    y1 = math.log(k1)
    y2 = math.log(k2)
    slope = (y2 - y1) / (x2 - x1)
    e_j_mol = -slope
    ln_a = y1 + e_j_mol * x1
    return math.exp(ln_a), e_j_mol / 1000


def catalyst_mass(
    tube_count: int, tube_inner_d_m: float, tube_length_m: float, particle_density_kg_m3: float, voidage: float
) -> float:
    bed_volume = tube_count * math.pi * tube_inner_d_m**2 / 4 * tube_length_m
    return bed_volume * particle_density_kg_m3 * (1 - voidage)


def bundle_diameter(tube_count: int, tube_od_mm: float, pitch_factor: float = 1.25, edge_factor: float = 1.5) -> float:
    pitch_mm = pitch_factor * tube_od_mm
    centerline_tubes = 1.1 * math.sqrt(tube_count)
    edge_mm = edge_factor * tube_od_mm
    return (pitch_mm * (centerline_tubes - 1) + 2 * edge_mm) / 1000


def packed_bed_tube_nu(
    particle_d_m: float,
    actual_velocity_m_s: float,
    rho_kg_m3: float,
    mu_pa_s: float,
    cp_j_kg_k: float,
    thermal_w_m_k: float,
    tube_inner_d_m: float,
) -> float:
    re_p = particle_d_m * actual_velocity_m_s * rho_kg_m3 / mu_pa_s
    pr = cp_j_kg_k * mu_pa_s / thermal_w_m_k
    return 2.26 * re_p**0.8 * pr**0.33 * math.exp(-6 * particle_d_m / tube_inner_d_m)


def overall_u_outer_area(
    alpha_i: float,
    alpha_o: float,
    di_m: float,
    do_m: float,
    wall_m: float,
    metal_lambda: float,
    rsi: float,
    rso: float,
) -> float:
    dm_m = (di_m + do_m) / 2
    resistance = (1 / alpha_i) * (do_m / di_m)
    resistance += wall_m / metal_lambda * (do_m / dm_m)
    resistance += 1 / alpha_o
    resistance += rsi * (do_m / di_m)
    resistance += rso
    return 1 / resistance


def ergun_pressure_drop(
    particle_d_m: float,
    superficial_velocity_m_s: float,
    rho_kg_m3: float,
    mu_pa_s: float,
    bed_length_m: float,
    voidage: float,
) -> tuple[float, float, float]:
    rem = particle_d_m * superficial_velocity_m_s * rho_kg_m3 / (mu_pa_s * (1 - voidage))
    friction = 150 / rem + 1.75
    dp_pa = friction * rho_kg_m3 * superficial_velocity_m_s**2 * bed_length_m * (1 - voidage)
    dp_pa /= particle_d_m * voidage**3
    return rem, friction, dp_pa


def numeric_from_raw(raw: str) -> float | None:
    if not raw:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", raw.replace(",", ""))
    return float(match.group(0)) if match else None


def split_value_unit(parameter: str, raw_value: str) -> tuple[str, str]:
    unit = ""
    param = parameter.strip()
    for left, right in (("（", "）"), ("(", ")"), ("／", ""), ("/", "")):
        if left in param and (right in param or not right):
            if right:
                before, after = param.rsplit(left, 1)
                if after.endswith(right):
                    return raw_value.strip(), after[: -len(right)].strip()
            else:
                before, after = param.rsplit(left, 1)
                return raw_value.strip(), after.strip()
    if "/" in param:
        before, after = param.rsplit("/", 1)
        if before and after:
            return raw_value.strip(), after.strip()
    return raw_value.strip(), unit


def parse_cylinder_spec(spec: str) -> tuple[float, float] | None:
    match = re.search(r"Φ\s*(\d+(?:\.\d+)?)\s*[×xX]\s*(\d+(?:\.\d+)?)", spec)
    if not match:
        return None
    return float(match.group(1)) / 1000, float(match.group(2)) / 1000


def parse_pipe_spec(spec: str) -> tuple[float, float] | None:
    match = re.search(r"Φ\s*(\d+(?:\.\d+)?)\s*[×xX]\s*(\d+(?:\.\d+)?)", spec)
    if not match:
        return None
    return float(match.group(1)) / 1000, float(match.group(2)) / 1000


def cylinder_geometry_volume_m3(spec: str) -> float | None:
    parsed = parse_cylinder_spec(spec)
    if not parsed:
        return None
    diameter_m, length_m = parsed
    return math.pi * diameter_m**2 / 4 * length_m


def membrane_area_m2(channel_count: float, inner_d_mm: float, length_m: float, element_count: float = 1.0) -> float:
    return element_count * channel_count * math.pi * inner_d_mm / 1000 * length_m


def pump_hydraulic_power_kw(flow_m3_h: float, head_m: float, rho_kg_m3: float) -> float:
    return rho_kg_m3 * 9.80665 * flow_m3_h / 3600 * head_m / 1000


def pump_shaft_power_kw(flow_m3_h: float, head_m: float, efficiency_percent: float, rho_kg_m3: float) -> float:
    return pump_hydraulic_power_kw(flow_m3_h, head_m, rho_kg_m3) / (efficiency_percent / 100)


def pump_reverse_density_kg_m3(flow_m3_h: float, head_m: float, efficiency_percent: float, power_kw: float) -> float:
    return power_kw * 1000 * (efficiency_percent / 100) / (9.80665 * flow_m3_h / 3600 * head_m)


def pressure_ratio(p_out: float, p_in: float) -> float:
    return p_out / p_in


def read_csv_table(relative_path: str) -> list[list[str]]:
    path = require_case_profile().source_path(relative_path)
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [[cell.strip() for cell in row] for row in csv.reader(f)]


def current_table_count() -> int:
    require_case_profile()
    total = 0
    for doc_id in CURRENT_DOC_IDS:
        total += len(list((require_case_profile().source_root / "data" / "tables" / doc_id).glob("*.csv")))
    return total


def first_row_value(rows: list[list[str]], row_name: str, column_name: str) -> float:
    header = rows[0]
    col_index = header.index(column_name)
    for row in rows[1:]:
        if row and row[0] == row_name:
            return float(row[col_index])
    raise KeyError(f"{row_name=} {column_name=} not found")


def numeric_column(rows: list[list[str]], column_name: str) -> list[float]:
    header = rows[0]
    col_index = header.index(column_name)
    values = []
    for row in rows[1:]:
        if len(row) > col_index and row[col_index]:
            values.append(float(row[col_index]))
    return values


def max_packed_height_by_section(rows: list[list[str]]) -> dict[str, float]:
    header = rows[0]
    section_i = header.index("Section")
    height_i = header.index("Packedheight（meter）")
    result: dict[str, float] = {}
    for row in rows[1:]:
        section = row[section_i]
        height = float(row[height_i])
        result[section] = max(result.get(section, 0.0), height)
    return result


def add(
    rows: list[CalcRow],
    *,
    module: str,
    item: str,
    source_location: str,
    formula: str,
    input_values: dict[str, Any],
    value: float,
    unit: str,
    document_value: str = "",
    tolerance: float | None = None,
    reliability_class: str = "A_formula_reproduced",
    status: str = "reproduced",
    note: str = "",
) -> None:
    doc_num = numeric_from_raw(document_value)
    abs_error = rel_error = None
    pass_check = None
    if doc_num is not None and tolerance is not None:
        abs_error = abs(value - doc_num)
        rel_error = abs_error / abs(doc_num) if doc_num else None
        pass_check = abs_error <= tolerance
        if not pass_check and status == "reproduced":
            status = "review"
    rows.append(
        CalcRow(
            module=module,
            item=item,
            source_location=source_location,
            formula=formula,
            input_values=input_values,
            value=value,
            unit=unit,
            document_value_raw=document_value,
            document_numeric_value=doc_num,
            tolerance=tolerance,
            abs_error=abs_error,
            rel_error=rel_error,
            pass_check=pass_check,
            reliability_class=reliability_class,
            status=status,
            note=note,
        )
    )


def add_condition(
    rows: list[CalcRow],
    *,
    module: str,
    item: str,
    source_location: str,
    formula: str,
    input_values: dict[str, Any],
    value: float,
    unit: str,
    condition_label: str,
    pass_check: bool,
    reliability_class: str = "A_formula_reproduced",
    status: str = "reproduced",
    note: str = "",
) -> None:
    rows.append(
        CalcRow(
            module=module,
            item=item,
            source_location=source_location,
            formula=formula,
            input_values=input_values,
            value=value,
            unit=unit,
            document_value_raw=condition_label,
            document_numeric_value=None,
            tolerance=None,
            abs_error=None,
            rel_error=None,
            pass_check=pass_check,
            reliability_class=reliability_class,
            status=status if pass_check else "review",
            note=note,
        )
    )


def add_nozzle_rows(
    rows: list[CalcRow],
    *,
    module: str,
    source_location: str,
    name: str,
    flow_m3_h: float,
    target_u_m_s: float,
    od_m: float,
    thickness_m: float,
    doc_id_m: str,
    doc_u_m_s: str,
    id_tolerance_m: float = 0.001,
    u_tolerance_m_s: float = 0.03,
    note: str = "",
) -> None:
    add(
        rows,
        module=module,
        item=f"{name} theoretical ID",
        source_location=source_location,
        formula="sqrt(4*V/(3600*pi*u_target))",
        input_values={"flow_m3_h": flow_m3_h, "target_velocity_m_s": target_u_m_s},
        value=pipe_required_diameter(flow_m3_h, target_u_m_s),
        unit="m",
        document_value=doc_id_m,
        tolerance=id_tolerance_m,
        reliability_class="A_formula_reproduced",
        note=note,
    )
    add(
        rows,
        module=module,
        item=f"{name} selected-pipe velocity",
        source_location=source_location,
        formula="4*V/(3600*pi*(OD-2*s)^2)",
        input_values={"flow_m3_h": flow_m3_h, "OD_m": od_m, "wall_thickness_m": thickness_m},
        value=pipe_actual_velocity(flow_m3_h, od_m, thickness_m),
        unit="m/s",
        document_value=doc_u_m_s,
        tolerance=u_tolerance_m_s,
        reliability_class="A_formula_reproduced",
    )


@require_case_profile.guard
def add_t802_union_rows(rows: list[CalcRow]) -> None:
    stream = read_csv_table(case_value('L413C28'))
    summary = read_csv_table(case_value('L414C29'))
    sizing = read_csv_table(case_value('L415C28'))
    rating = read_csv_table(case_value('L416C28'))
    feed_mass = first_row_value(stream, case_value('L418C40'), case_value('L418C56'))
    distillate_mass = first_row_value(stream, case_value('L419C46'), case_value('L419C62'))
    bottoms_mass = first_row_value(stream, case_value('L420C43'), case_value('L420C59'))
    feed_mol = first_row_value(stream, case_value('L421C39'), case_value('L421C55'))
    distillate_mol = first_row_value(stream, case_value('L422C45'), case_value('L422C61'))
    bottoms_mol = first_row_value(stream, case_value('L423C42'), case_value('L423C58'))
    feed_vol = first_row_value(stream, case_value('L424C39'), case_value('L424C55'))
    distillate_vol = first_row_value(stream, case_value('L425C45'), case_value('L425C61'))
    bottoms_vol = first_row_value(stream, case_value('L426C42'), case_value('L426C58'))
    add(rows, module=case_value('L430C15'), item=case_value('L431C13'), source_location=case_value('L432C24'), formula=case_value('L433C16'), input_values={case_value('L434C22'): feed_mass, case_value('L434C46'): distillate_mass, case_value('L434C82'): bottoms_mass}, value=feed_mass - distillate_mass - bottoms_mass, unit=case_value('L436C13'), document_value=case_value('L437C23'), tolerance=case_value('L438C18'), note=case_value('L439C13'))
    add(rows, module=case_value('L443C15'), item=case_value('L444C13'), source_location=case_value('L445C24'), formula=case_value('L446C16'), input_values={case_value('L447C22'): feed_mol, case_value('L447C47'): distillate_mol, case_value('L447C84'): bottoms_mol}, value=feed_mol - distillate_mol - bottoms_mol, unit=case_value('L449C13'), document_value=case_value('L450C23'), tolerance=case_value('L451C18'))
    add(rows, module=case_value('L455C15'), item=case_value('L456C13'), source_location=case_value('L457C24'), formula=case_value('L458C16'), input_values={case_value('L459C22'): feed_vol, case_value('L459C45'): distillate_vol, case_value('L459C80'): bottoms_vol}, value=feed_vol - distillate_vol - bottoms_vol, unit=case_value('L461C13'), document_value=case_value('L462C23'), tolerance=case_value('L463C18'), note=case_value('L464C13'))
    design_temp_c = float(summary[case_value('L468C34')][case_value('L468C37')])
    design_pressure_mpa = float(summary[case_value('L469C40')][case_value('L469C43')])
    theoretical_stages = float(summary[case_value('L470C39')][case_value('L470C42')])
    feed_stage = float(summary[case_value('L471C31')][case_value('L471C34')])
    total_height_m = float(summary[case_value('L472C35')][case_value('L472C38')])
    add(rows, module=case_value('L475C15'), item=case_value('L476C13'), source_location=case_value('L477C24'), formula=case_value('L478C16'), input_values={case_value('L479C22'): design_temp_c}, value=design_temp_c, unit=case_value('L481C13'), document_value=case_value('L482C23'), tolerance=case_value('L483C18'), reliability_class=case_value('L484C26'))
    add(rows, module=case_value('L488C15'), item=case_value('L489C13'), source_location=case_value('L490C24'), formula=case_value('L491C16'), input_values={case_value('L492C22'): design_pressure_mpa}, value=design_pressure_mpa, unit=case_value('L494C13'), document_value=case_value('L495C23'), tolerance=case_value('L496C18'), reliability_class=case_value('L497C26'), note=case_value('L498C13'))
    add(rows, module=case_value('L502C15'), item=case_value('L503C13'), source_location=case_value('L504C24'), formula=case_value('L505C16'), input_values={case_value('L506C22'): theoretical_stages}, value=theoretical_stages, unit=case_value('L508C13'), document_value=case_value('L509C23'), tolerance=case_value('L510C18'), reliability_class=case_value('L511C26'), note=case_value('L512C13'))
    add(rows, module=case_value('L516C15'), item=case_value('L517C13'), source_location=case_value('L518C24'), formula=case_value('L519C16'), input_values={case_value('L520C22'): feed_stage}, value=feed_stage, unit=case_value('L522C13'), document_value=case_value('L523C23'), tolerance=case_value('L524C18'), reliability_class=case_value('L525C26'), note=case_value('L526C13'))
    add(rows, module=case_value('L530C15'), item=case_value('L531C13'), source_location=case_value('L532C24'), formula=case_value('L533C16'), input_values={case_value('L534C22'): total_height_m}, value=total_height_m, unit=case_value('L536C13'), document_value=case_value('L537C23'), tolerance=case_value('L538C18'), reliability_class=case_value('L539C26'))
    sizing_heights = max_packed_height_by_section(sizing)
    rating_heights = max_packed_height_by_section(rating)
    sizing_total_height = sum(sizing_heights.values())
    rating_total_height = sum(rating_heights.values())
    add(rows, module=case_value('L548C15'), item=case_value('L549C13'), source_location=case_value('L550C24'), formula=case_value('L551C16'), input_values=sizing_heights, value=sizing_total_height, unit=case_value('L554C13'), document_value=case_value('L555C23'), tolerance=case_value('L556C18'), note=case_value('L557C13'))
    add(rows, module=case_value('L561C15'), item=case_value('L562C13'), source_location=case_value('L563C24'), formula=case_value('L564C16'), input_values=rating_heights, value=rating_total_height, unit=case_value('L567C13'), document_value=case_value('L568C23'), tolerance=case_value('L569C18'))
    for table_name, table_rows, source in [(case_value('L572C9'), sizing, case_value('L572C39')), (case_value('L573C9'), rating, case_value('L573C27'))]:
        capacities_lv = numeric_column(table_rows, case_value('L575C51'))
        capacities_l = numeric_column(table_rows, case_value('L576C50'))
        pressure_drop = numeric_column(table_rows, case_value('L577C51'))
        add_condition(rows, module=case_value('L580C19'), item=f"{table_name}{case_value('L581C31')}", source_location=source, formula=case_value('L583C20'), input_values={case_value('L584C26'): min(capacities_lv), case_value('L584C53'): max(capacities_lv), case_value('L584C80'): case_value('L584C96')}, value=min(capacities_lv), unit=case_value('L586C17'), condition_label=case_value('L587C28'), pass_check=case_value('L588C23') <= min(capacities_lv) <= case_value('L588C51'), reliability_class=case_value('L589C30'), note=case_value('L590C17'))
        add_condition(rows, module=case_value('L594C19'), item=f"{table_name}{case_value('L595C31')}", source_location=source, formula=case_value('L597C20'), input_values={case_value('L598C26'): min(capacities_lv), case_value('L598C53'): max(capacities_lv), case_value('L598C80'): case_value('L598C96')}, value=max(capacities_lv), unit=case_value('L600C17'), condition_label=case_value('L601C28'), pass_check=case_value('L602C23') <= max(capacities_lv) <= case_value('L602C51'), reliability_class=case_value('L603C30'))
        add_condition(rows, module=case_value('L607C19'), item=f"{table_name}{case_value('L608C31')}", source_location=source, formula=case_value('L610C20'), input_values={case_value('L611C26'): min(capacities_l), case_value('L611C52'): max(capacities_l), case_value('L611C78'): case_value('L611C94')}, value=min(capacities_l), unit=case_value('L613C17'), condition_label=case_value('L614C28'), pass_check=case_value('L615C23') <= min(capacities_l) <= case_value('L615C50'), reliability_class=case_value('L616C30'))
        add_condition(rows, module=case_value('L620C19'), item=f"{table_name}{case_value('L621C31')}", source_location=source, formula=case_value('L623C20'), input_values={case_value('L624C26'): min(pressure_drop), case_value('L624C58'): max(pressure_drop)}, value=max(pressure_drop), unit=case_value('L626C17'), condition_label=case_value('L627C28'), pass_check=max(pressure_drop) < case_value('L628C44'), reliability_class=case_value('L629C30'), note=case_value('L630C17'))


@require_case_profile.guard
def add_supplement3_rows(rows: list[CalcRow]) -> None:
    stream = read_csv_table(case_value('L635C28'))
    design = read_csv_table(case_value('L636C28'))
    sizing = read_csv_table(case_value('L637C28'))
    rating = read_csv_table(case_value('L638C28'))
    exchanger_stream = read_csv_table(case_value('L639C38'))
    exchanger_conditions = read_csv_table(case_value('L640C42'))
    feed_mass = first_row_value(stream, case_value('L642C40'), case_value('L642C56'))
    distillate_mass = first_row_value(stream, case_value('L643C46'), case_value('L643C62'))
    bottoms_mass = first_row_value(stream, case_value('L644C43'), case_value('L644C59'))
    feed_mol = first_row_value(stream, case_value('L645C39'), case_value('L645C55'))
    distillate_mol = first_row_value(stream, case_value('L646C45'), case_value('L646C61'))
    bottoms_mol = first_row_value(stream, case_value('L647C42'), case_value('L647C58'))
    feed_vol = first_row_value(stream, case_value('L648C39'), case_value('L648C55'))
    distillate_vol = first_row_value(stream, case_value('L649C45'), case_value('L649C61'))
    bottoms_vol = first_row_value(stream, case_value('L650C42'), case_value('L650C58'))
    add(rows, module=case_value('L654C15'), item=case_value('L655C13'), source_location=case_value('L656C24'), formula=case_value('L657C16'), input_values={case_value('L658C22'): feed_mass, case_value('L658C46'): distillate_mass, case_value('L658C82'): bottoms_mass}, value=feed_mass - distillate_mass - bottoms_mass, unit=case_value('L660C13'), document_value=case_value('L661C23'), tolerance=case_value('L662C18'), note=case_value('L663C13'))
    add(rows, module=case_value('L667C15'), item=case_value('L668C13'), source_location=case_value('L669C24'), formula=case_value('L670C16'), input_values={case_value('L671C22'): feed_mol, case_value('L671C47'): distillate_mol, case_value('L671C84'): bottoms_mol}, value=feed_mol - distillate_mol - bottoms_mol, unit=case_value('L673C13'), document_value=case_value('L674C23'), tolerance=case_value('L675C18'))
    add(rows, module=case_value('L679C15'), item=case_value('L680C13'), source_location=case_value('L681C24'), formula=case_value('L682C16'), input_values={case_value('L683C22'): feed_vol, case_value('L683C45'): distillate_vol, case_value('L683C80'): bottoms_vol}, value=feed_vol - distillate_vol - bottoms_vol, unit=case_value('L685C13'), reliability_class=case_value('L686C26'), status=case_value('L687C15'), note=case_value('L688C13'))
    design_temp_c = float(design[case_value('L691C33')][case_value('L691C36')])
    design_pressure_mpa = float(design[case_value('L692C39')][case_value('L692C42')])
    theoretical_stages = float(design[case_value('L693C38')][case_value('L693C41')])
    feed_stage = float(design[case_value('L694C30')][case_value('L694C33')])
    total_height_m = float(design[case_value('L695C34')][case_value('L695C37')])
    for item, value, unit, doc_value in [(case_value('L697C9'), design_temp_c, case_value('L697C55'), case_value('L697C60')), (case_value('L698C9'), design_pressure_mpa, case_value('L698C76'), case_value('L698C83')), (case_value('L699C9'), theoretical_stages, case_value('L699C60'), case_value('L699C70')), (case_value('L700C9'), feed_stage, case_value('L700C44'), case_value('L700C53')), (case_value('L701C9'), total_height_m, case_value('L701C56'), case_value('L701C61'))]:
        add(rows, module=case_value('L705C19'), item=item, source_location=case_value('L707C28'), formula=case_value('L708C20'), input_values={case_value('L709C26'): value}, value=value, unit=unit, document_value=doc_value, tolerance=case_value('L713C22'), reliability_class=case_value('L714C30'))
    sizing_heights = max_packed_height_by_section(sizing)
    rating_heights = max_packed_height_by_section(rating)
    for label, table_rows, heights, source in [(case_value('L720C9'), sizing, sizing_heights, case_value('L720C55')), (case_value('L721C9'), rating, rating_heights, case_value('L721C43'))]:
        add(rows, module=case_value('L725C19'), item=f"{label}{case_value('L726C26')}", source_location=source, formula=case_value('L728C20'), input_values=heights, value=sum(heights.values()), unit=case_value('L731C17'), document_value=case_value('L732C27'), tolerance=case_value('L733C22'), reliability_class=case_value('L734C30'))
        capacities_lv = numeric_column(table_rows, case_value('L736C51'))
        capacities_l = numeric_column(table_rows, case_value('L737C50'))
        pressure_drop = numeric_column(table_rows, case_value('L738C51'))
        for item, value, condition in [(f"{label}{case_value('L740C22')}", min(capacities_lv), case_value('L740C63')), (f"{label}{case_value('L741C22')}", max(capacities_lv), case_value('L741C63')), (f"{label}{case_value('L742C22')}", min(capacities_l), case_value('L742C68')), (f"{label}{case_value('L743C22')}", max(pressure_drop), case_value('L743C63'))]:
            pass_check = case_value('L745C25') <= value <= case_value('L745C40') if case_value('L745C46') in item else value < case_value('L745C79')
            add_condition(rows, module=case_value('L748C23'), item=item, source_location=source, formula=case_value('L751C24'), input_values={case_value('L752C30'): value}, value=value, unit=case_value('L754C21') if case_value('L754C28') in item else case_value('L754C53'), condition_label=condition, pass_check=pass_check, reliability_class=case_value('L757C34'), note=case_value('L758C21'))
    for name, flow_m3_s, od_m, thk_m, doc_u in [(case_value('L762C9'), case_value('L762C29'), case_value('L762C35'), case_value('L762C42'), case_value('L762C49')), (case_value('L763C9'), case_value('L763C23'), case_value('L763C32'), case_value('L763C39'), case_value('L763C46')), (case_value('L764C9'), case_value('L764C25'), case_value('L764C34'), case_value('L764C41'), case_value('L764C48')), (case_value('L765C9'), case_value('L765C39'), case_value('L765C48'), case_value('L765C55'), case_value('L765C62')), (case_value('L766C9'), case_value('L766C28'), case_value('L766C34'), case_value('L766C41'), case_value('L766C48'))]:
        add(rows, module=case_value('L770C19'), item=f"{name}{case_value('L771C25')}", source_location=case_value('L772C28'), formula=case_value('L773C20'), input_values={case_value('L774C26'): flow_m3_s, case_value('L774C50'): od_m, case_value('L774C64'): thk_m}, value=pipe_actual_velocity(flow_m3_s * case_value('L775C51'), od_m, thk_m), unit=case_value('L776C17'), document_value=doc_u, tolerance=case_value('L778C22') if float(doc_u) > case_value('L778C44') else case_value('L778C52'))
    add(rows, module=case_value('L783C15'), item=case_value('L784C13'), source_location=case_value('L785C24'), formula=case_value('L786C16'), input_values={case_value('L787C22'): case_value('L787C42'), case_value('L787C51'): case_value('L787C67'), case_value('L787C70'): case_value('L787C90')}, value=tower_bottom_liquid_height(case_value('L788C41') * case_value('L788C51'), case_value('L788C57'), case_value('L788C60')), unit=case_value('L789C13'), reliability_class=case_value('L790C26'), status=case_value('L791C15'), note=case_value('L792C13'))
    tube_p_in = first_row_value(exchanger_stream, case_value('L795C50'), case_value('L795C63'))
    shell_p_in = first_row_value(exchanger_stream, case_value('L796C51'), case_value('L796C64'))
    tube_t_max = max(first_row_value(exchanger_stream, case_value('L797C55'), case_value('L797C68')), first_row_value(exchanger_stream, case_value('L797C119'), case_value('L797C132')))
    shell_t_max = max(first_row_value(exchanger_stream, case_value('L798C56'), case_value('L798C69')), first_row_value(exchanger_stream, case_value('L798C120'), case_value('L798C133')))
    tube_design_p = float(exchanger_conditions[case_value('L799C47')][case_value('L799C50')])
    shell_design_p = float(exchanger_conditions[case_value('L800C48')][case_value('L800C51')])
    tube_allow_dp = float(exchanger_conditions[case_value('L801C47')][case_value('L801C50')])
    shell_allow_dp = float(exchanger_conditions[case_value('L802C48')][case_value('L802C51')])
    tube_design_t = float(exchanger_conditions[case_value('L803C47')][case_value('L803C50')])
    shell_design_t = float(exchanger_conditions[case_value('L804C48')][case_value('L804C51')])
    for side, p_in, doc_p in [(case_value('L806C9'), tube_p_in, tube_design_p), (case_value('L807C9'), shell_p_in, shell_design_p)]:
        add(rows, module=case_value('L811C19'), item=f"{side}{case_value('L812C25')}", source_location=case_value('L813C28'), formula=case_value('L814C20'), input_values={case_value('L815C26'): p_in, case_value('L815C58'): case_value('L815C75')}, value=p_in + case_value('L816C25'), unit=case_value('L817C17'), document_value=str(doc_p), tolerance=case_value('L819C22'), reliability_class=case_value('L820C30'), note=case_value('L821C17'))
    for side, p_in, doc_dp in [(case_value('L824C9'), tube_p_in, tube_allow_dp), (case_value('L825C9'), shell_p_in, shell_allow_dp)]:
        add(rows, module=case_value('L829C19'), item=f"{side}{case_value('L830C25')}", source_location=case_value('L831C28'), formula=case_value('L832C20'), input_values={case_value('L833C26'): p_in, case_value('L833C54'): case_value('L833C64')}, value=case_value('L834C18') * p_in, unit=case_value('L835C17'), document_value=str(doc_dp), tolerance=case_value('L837C22'))
    for side, t_max, doc_t in [(case_value('L840C9'), tube_t_max, tube_design_t), (case_value('L841C9'), shell_t_max, shell_design_t)]:
        add_condition(rows, module=case_value('L845C19'), item=f"{side}{case_value('L846C25')}", source_location=case_value('L847C28'), formula=case_value('L848C20'), input_values={case_value('L849C26'): t_max, case_value('L849C52'): doc_t}, value=doc_t - t_max, unit=case_value('L851C17'), condition_label=case_value('L852C28'), pass_check=case_value('L853C23') <= doc_t - t_max <= case_value('L853C46'), reliability_class=case_value('L854C30'))
    add(rows, module=case_value('L859C15'), item=case_value('L860C13'), source_location=case_value('L861C24'), formula=case_value('L862C16'), input_values={case_value('L863C22'): case_value('L863C38'), case_value('L863C43'): case_value('L863C59')}, value=case_value('L864C14') + case_value('L864C20'), unit=case_value('L865C13'), document_value=case_value('L866C23'), tolerance=case_value('L867C18'), reliability_class=case_value('L868C26'), status=case_value('L869C15'), note=case_value('L870C13'))
    add(rows, module=case_value('L874C15'), item=case_value('L875C13'), source_location=case_value('L876C24'), formula=case_value('L877C16'), input_values={case_value('L878C22'): case_value('L878C38'), case_value('L878C43'): case_value('L878C59')}, value=case_value('L879C14') + case_value('L879C20'), unit=case_value('L880C13'), document_value=case_value('L881C23'), tolerance=case_value('L882C18'), reliability_class=case_value('L883C26'), status=case_value('L884C15'), note=case_value('L885C13'))
    for side, p_op, doc_p, t_op, doc_t in [(case_value('L889C9'), case_value('L889C22'), case_value('L889C27'), case_value('L889C33'), case_value('L889C38')), (case_value('L890C9'), case_value('L890C23'), case_value('L890C28'), case_value('L890C34'), case_value('L890C39'))]:
        add(rows, module=case_value('L894C19'), item=f"{side}{case_value('L895C25')}", source_location=case_value('L896C28'), formula=case_value('L897C20'), input_values={case_value('L898C26'): p_op, case_value('L898C58'): case_value('L898C68')}, value=case_value('L899C18') * p_op, unit=case_value('L900C17'), document_value=str(doc_p), tolerance=case_value('L902C22'))
        add(rows, module=case_value('L906C19'), item=f"{side}{case_value('L907C25')}", source_location=case_value('L908C28'), formula=case_value('L909C20'), input_values={case_value('L910C26'): t_op, case_value('L910C59'): doc_t - t_op}, value=doc_t, unit=case_value('L912C17'), document_value=str(doc_t), tolerance=case_value('L914C22'), reliability_class=case_value('L915C30'), note=case_value('L916C17'))


@require_case_profile.guard
def add_late_chapter_audit_rows(rows: list[CalcRow]) -> None:
    vg_m3_h = case_value('L922C14')
    vl_m3_h = case_value('L923C14')
    inlet_mass = case_value('L924C17')
    gas_mass = case_value('L925C15')
    liquid_mass = case_value('L926C18')
    rho_l = case_value('L927C12')
    rho_v = case_value('L928C12')
    diameter_m = case_value('L929C17')
    shell_height_m = case_value('L930C21')
    area_m2 = math.pi * diameter_m ** case_value('L931C36') / case_value('L931C40')
    gas_u = vg_m3_h / case_value('L932C22') / area_m2
    k_required = gas_u / math.sqrt((rho_l - rho_v) / rho_v)
    cyl_volume = area_m2 * shell_height_m
    add(rows, module=case_value('L937C15'), item=case_value('L938C13'), source_location=case_value('L939C24'), formula=case_value('L940C16'), input_values={case_value('L941C22'): inlet_mass, case_value('L941C47'): gas_mass, case_value('L941C69'): liquid_mass}, value=inlet_mass - gas_mass - liquid_mass, unit=case_value('L943C13'), document_value=case_value('L944C23'), tolerance=case_value('L945C18'), reliability_class=case_value('L946C26'), note=case_value('L947C13'))
    add(rows, module=case_value('L951C15'), item=case_value('L952C13'), source_location=case_value('L953C24'), formula=case_value('L954C16'), input_values={case_value('L955C22'): case_value('L955C37'), case_value('L955C47'): case_value('L955C57')}, value=design_pressure(case_value('L956C30'), case_value('L956C40')), unit=case_value('L957C13'), document_value=case_value('L958C23'), tolerance=case_value('L959C18'), reliability_class=case_value('L960C26'))
    add(rows, module=case_value('L964C15'), item=case_value('L965C13'), source_location=case_value('L966C24'), formula=case_value('L967C16'), input_values={case_value('L968C22'): vg_m3_h, case_value('L968C42'): diameter_m}, value=gas_u, unit=case_value('L970C13'), document_value=case_value('L971C23'), reliability_class=case_value('L972C26'), status=case_value('L973C15'), note=case_value('L974C13'))
    add(rows, module=case_value('L978C15'), item=case_value('L979C13'), source_location=case_value('L980C24'), formula=case_value('L981C16'), input_values={case_value('L982C22'): gas_u, case_value('L982C38'): rho_l, case_value('L982C60'): rho_v}, value=k_required, unit=case_value('L984C13'), document_value=case_value('L985C23'), reliability_class=case_value('L986C26'), status=case_value('L987C15'), note=case_value('L988C13'))
    add(rows, module=case_value('L992C15'), item=case_value('L993C13'), source_location=case_value('L994C24'), formula=case_value('L995C16'), input_values={case_value('L996C22'): cyl_volume, case_value('L996C51'): vg_m3_h}, value=cyl_volume / (vg_m3_h / case_value('L997C38')), unit=case_value('L998C13'), document_value=case_value('L999C23'), reliability_class=case_value('L1000C26'), status=case_value('L1001C15'))
    for name, spec, flow, doc_hint in [(case_value('L1004C9'), case_value('L1004C40'), vg_m3_h + vl_m3_h, case_value('L1004C70')), (case_value('L1005C9'), case_value('L1005C45'), vg_m3_h, case_value('L1005C65')), (case_value('L1006C9'), case_value('L1006C48'), vl_m3_h, case_value('L1006C68'))]:
        parsed = parse_pipe_spec(spec)
        if parsed:
            od_m, thk_m = parsed
            add(rows, module=case_value('L1013C23'), item=name, source_location=case_value('L1015C32'), formula=case_value('L1016C24'), input_values={case_value('L1017C30'): spec, case_value('L1017C49'): flow, case_value('L1017C68'): doc_hint}, value=pipe_actual_velocity(flow, od_m, thk_m), unit=case_value('L1019C21'), document_value=case_value('L1020C31'), reliability_class=case_value('L1021C34'), status=case_value('L1022C23'), note=case_value('L1023C21'))
    for tag, pin, pout, source in [(case_value('L1028C9'), case_value('L1028C23'), case_value('L1028C32'), case_value('L1028C37')), (case_value('L1029C9'), case_value('L1029C18'), case_value('L1029C24'), case_value('L1029C30')), (case_value('L1030C9'), case_value('L1030C18'), case_value('L1030C24'), case_value('L1030C30')), (case_value('L1031C9'), case_value('L1031C18'), case_value('L1031C24'), case_value('L1031C30')), (case_value('L1032C9'), case_value('L1032C18'), case_value('L1032C24'), case_value('L1032C30')), (case_value('L1033C9'), case_value('L1033C18'), case_value('L1033C24'), case_value('L1033C30'))]:
        add(rows, module=case_value('L1037C19'), item=f"{tag}{case_value('L1038C24')}", source_location=source, formula=case_value('L1040C20'), input_values={case_value('L1041C26'): pin, case_value('L1041C43'): pout}, value=pressure_ratio(pout, pin), unit=case_value('L1043C17'), document_value=case_value('L1044C27'), reliability_class=case_value('L1045C30'), status=case_value('L1046C19'), note=case_value('L1047C17'))
    for source_table, category in [(case_value('L1052C9'), case_value('L1052C55')), (case_value('L1053C9'), case_value('L1053C55')), (case_value('L1054C9'), case_value('L1054C55'))]:
        table_name = Path(source_table).name
        for row in read_csv_table(source_table)[case_value('L1057C48'):]:
            header = read_csv_table(source_table)[case_value('L1058C50')]
            row_map = dict(zip(header, row))
            tag = row_map.get(case_value('L1060C30'), case_value('L1060C46'))
            nominal = numeric_from_raw(row_map.get(case_value('L1061C51'), row_map.get(case_value('L1061C82'), case_value('L1061C103'))))
            spec = row_map.get(case_value('L1062C31'), row_map.get(case_value('L1062C62'), case_value('L1062C83')))
            geom = cylinder_geometry_volume_m3(spec)
            if tag and nominal is not None and geom:
                add(rows, module=case_value('L1067C27'), item=f"{tag}{case_value('L1068C32')}", source_location=f"{case_value('L1069C38')}{table_name}", formula=case_value('L1070C28'), input_values={case_value('L1071C34'): category, case_value('L1071C56'): nominal, case_value('L1071C79'): spec}, value=nominal / geom, unit=case_value('L1073C25'), document_value=case_value('L1074C35'), reliability_class=case_value('L1075C38'), status=case_value('L1076C27'), note=case_value('L1077C25'))
    for table_no, tag in [(case_value('L1079C27'), case_value('L1079C31')), (case_value('L1079C42'), case_value('L1079C46')), (case_value('L1079C62'), case_value('L1079C66'))]:
        rows_v = read_csv_table(f"{case_value('L1080C34')}{table_no}{case_value('L1080C78')}")
        values = {r[case_value('L1081C20')]: r[case_value('L1081C26')] for r in rows_v[case_value('L1081C45'):] if len(r) >= case_value('L1081C62')}
        nominal = numeric_from_raw(values.get(case_value('L1082C46'), case_value('L1082C65')))
        spec = values.get(case_value('L1083C26'), case_value('L1083C45'))
        geom = cylinder_geometry_volume_m3(spec)
        if nominal is not None and geom:
            add(rows, module=case_value('L1088C23'), item=f"{tag}{case_value('L1089C28')}", source_location=f"{case_value('L1090C34')}{table_no}", formula=case_value('L1091C24'), input_values={case_value('L1092C30'): nominal, case_value('L1092C53'): spec}, value=nominal / geom, unit=case_value('L1094C21'), document_value=case_value('L1095C31'), reliability_class=case_value('L1096C34'), status=case_value('L1097C23'), note=case_value('L1098C21'))
    membrane = read_csv_table(case_value('L1102C30'))
    m_header = membrane[case_value('L1103C24')]
    m_row = dict(zip(m_header, membrane[case_value('L1104C40')]))
    channel_count = float(m_row[case_value('L1105C32')])
    inner_d = float(m_row[case_value('L1106C26')].split(case_value('L1106C67'))[case_value('L1106C72')])
    length_m = float(m_row[case_value('L1107C27')])
    element_count = float(m_row[case_value('L1108C32')])
    area_calc = membrane_area_m2(channel_count, inner_d, length_m, element_count)
    add(rows, module=case_value('L1112C15'), item=case_value('L1113C13'), source_location=case_value('L1114C24'), formula=case_value('L1115C16'), input_values={case_value('L1116C22'): element_count, case_value('L1116C49'): channel_count, case_value('L1116C76'): inner_d, case_value('L1116C99'): length_m}, value=area_calc, unit=case_value('L1118C13'), document_value=m_row[case_value('L1119C29')], tolerance=case_value('L1120C18'), reliability_class=case_value('L1121C26'), note=case_value('L1122C13'))
    pumps = read_csv_table(case_value('L1126C27'))
    header = pumps[case_value('L1127C19')]
    for row in pumps[case_value('L1128C21'):]:
        r = dict(zip(header, row))
        tag = r[case_value('L1130C16')]
        q = numeric_from_raw(r.get(case_value('L1131C35'), case_value('L1131C55')))
        h = numeric_from_raw(r.get(case_value('L1132C35'), case_value('L1132C47')))
        p_kw = numeric_from_raw(r.get(case_value('L1133C38'), case_value('L1133C54')))
        eta = numeric_from_raw(r.get(case_value('L1134C37'), case_value('L1134C48')))
        if None not in (q, h, p_kw, eta) and q and h and eta:
            rho_rev = pump_reverse_density_kg_m3(q, h, eta, p_kw)
            plausible = case_value('L1137C24') <= rho_rev <= case_value('L1137C42')
            add_condition(rows, module=case_value('L1140C23'), item=f"{tag}{case_value('L1141C28')}", source_location=case_value('L1142C32'), formula=case_value('L1143C24'), input_values={case_value('L1144C30'): q, case_value('L1144C46'): h, case_value('L1144C59'): eta, case_value('L1144C86'): p_kw}, value=rho_rev, unit=case_value('L1146C21'), condition_label=case_value('L1147C32'), pass_check=plausible, reliability_class=case_value('L1149C34'), status=case_value('L1150C23'), note=case_value('L1151C21'))
    p0403 = {r[case_value('L1153C15')]: r[case_value('L1153C21')] for r in read_csv_table(case_value('L1153C48'))[case_value('L1153C92'):] if len(r) >= case_value('L1153C109')}
    q = numeric_from_raw(p0403.get(case_value('L1154C35'), case_value('L1154C53')))
    h = numeric_from_raw(p0403.get(case_value('L1155C35'), case_value('L1155C47')))
    eta = numeric_from_raw(p0403.get(case_value('L1156C37'), case_value('L1156C49')))
    p_kw = numeric_from_raw(p0403.get(case_value('L1157C38'), case_value('L1157C54')))
    if None not in (q, h, eta, p_kw) and q and h and eta:
        add(rows, module=case_value('L1161C19'), item=case_value('L1162C17'), source_location=case_value('L1163C28'), formula=case_value('L1164C20'), input_values={case_value('L1165C26'): q, case_value('L1165C42'): h, case_value('L1165C55'): eta, case_value('L1165C82'): case_value('L1165C95')}, value=pump_shaft_power_kw(q, h, eta, case_value('L1166C49')), unit=case_value('L1167C17'), document_value=str(p_kw), reliability_class=case_value('L1169C30'), status=case_value('L1170C19'), note=case_value('L1171C17'))
        add_condition(rows, module=case_value('L1175C19'), item=case_value('L1176C17'), source_location=case_value('L1177C28'), formula=case_value('L1178C20'), input_values={case_value('L1179C26'): q, case_value('L1179C42'): h, case_value('L1179C55'): eta, case_value('L1179C82'): p_kw}, value=pump_reverse_density_kg_m3(q, h, eta, p_kw), unit=case_value('L1181C17'), condition_label=case_value('L1182C28'), pass_check=True, reliability_class=case_value('L1184C30'), status=case_value('L1185C19'), note=case_value('L1186C17'))


JUDGMENT_LINKS = CaseGlobal("JUDGMENT_LINKS")


def ledger_row(
    rows: list[ParameterLedgerRow],
    *,
    chapter: str,
    equipment_family: str,
    object_id: str,
    parameter: str,
    value: str,
    unit: str,
    source_document: str,
    source_table: str,
    source_location: str,
    source_type: str,
    evidence_class: str,
    action: str,
    judgment_links: str,
    scriptable_formula: str,
    note: str = "",
) -> None:
    if value is None or str(value).strip() == "":
        return
    rows.append(
        ParameterLedgerRow(
            chapter=chapter,
            equipment_family=equipment_family,
            object_id=object_id,
            parameter=parameter,
            value=str(value).strip(),
            unit=unit,
            source_document=source_document,
            source_table=source_table,
            source_location=source_location,
            source_type=source_type,
            evidence_class=evidence_class,
            action=action,
            judgment_links=judgment_links,
            scriptable_formula=scriptable_formula,
            note=note,
        )
    )


def classify_late_chapter_parameter(*, chapter: str, equipment_family: str, source_table: str, parameter: str, object_id: str) -> tuple[str, str, str, str, str]:
    p = parameter.replace(case_value('L1251C26'), case_value('L1251C33'))
    if source_table in {case_value('L1252C24'), case_value('L1252C40'), case_value('L1252C56'), case_value('L1252C72')}:
        return (case_value('L1254C12'), case_value('L1255C12'), case_value('L1256C12'), JUDGMENT_LINKS[case_value('L1257C27')], case_value('L1258C12'))
    if source_table in {case_value('L1260C24'), case_value('L1260C40'), case_value('L1260C56')}:
        return (case_value('L1262C12'), case_value('L1263C12'), case_value('L1264C12'), JUDGMENT_LINKS[case_value('L1265C27') if case_value('L1265C42') in object_id or source_table in {case_value('L1265C83'), case_value('L1265C99')} else case_value('L1265C120')], case_value('L1266C12'))
    if equipment_family == case_value('L1268C27'):
        if case_value('L1269C11') in p and case_value('L1269C29') in p:
            return (case_value('L1270C20'), case_value('L1270C45'), case_value('L1270C60'), JUDGMENT_LINKS[case_value('L1270C94')], case_value('L1270C108'))
        if any((key in p for key in (case_value('L1271C36'), case_value('L1271C46')))):
            return (case_value('L1272C20'), case_value('L1272C60'), case_value('L1272C78'), JUDGMENT_LINKS[case_value('L1272C134')], case_value('L1272C148'))
        if any((key in p for key in (case_value('L1273C36'), case_value('L1273C46'), case_value('L1273C56'), case_value('L1273C66')))):
            return (case_value('L1274C20'), case_value('L1274C60'), case_value('L1274C75'), JUDGMENT_LINKS[case_value('L1274C134')], case_value('L1274C148'))
        return (case_value('L1275C16'), case_value('L1275C46'), case_value('L1275C59'), JUDGMENT_LINKS[case_value('L1275C117')], case_value('L1275C131'))
    if equipment_family == case_value('L1276C27'):
        if case_value('L1277C11') in p:
            return (case_value('L1278C20'), case_value('L1278C46'), case_value('L1278C61'), JUDGMENT_LINKS[case_value('L1278C113')], case_value('L1278C128'))
        if any((key in p for key in (case_value('L1279C36'), case_value('L1279C46'), case_value('L1279C59')))):
            return (case_value('L1280C20'), case_value('L1280C47'), case_value('L1280C68'), JUDGMENT_LINKS[case_value('L1280C134')], case_value('L1280C149'))
        return (case_value('L1281C16'), case_value('L1281C46'), case_value('L1281C59'), JUDGMENT_LINKS[case_value('L1281C120')], case_value('L1281C135'))
    if equipment_family == case_value('L1282C27'):
        if any((key in p for key in (case_value('L1283C36'), case_value('L1283C52'), case_value('L1283C68')))):
            return (case_value('L1284C20'), case_value('L1284C50'), case_value('L1284C65'), JUDGMENT_LINKS[case_value('L1284C123')], case_value('L1284C135'))
        if case_value('L1285C11') in p:
            return (case_value('L1286C20'), case_value('L1286C53'), case_value('L1286C82'), JUDGMENT_LINKS[case_value('L1286C137')], case_value('L1286C149'))
        if any((key in p for key in (case_value('L1287C36'), case_value('L1287C52')))):
            return (case_value('L1288C20'), case_value('L1288C45'), case_value('L1288C58'), JUDGMENT_LINKS[case_value('L1288C114')], case_value('L1288C126'))
        return (case_value('L1289C16'), case_value('L1289C46'), case_value('L1289C59'), JUDGMENT_LINKS[case_value('L1289C129')], case_value('L1289C141'))
    if equipment_family == case_value('L1290C27'):
        if case_value('L1291C11') in p or case_value('L1291C31') in p or case_value('L1291C48') in p:
            return (case_value('L1292C20'), case_value('L1292C47'), case_value('L1292C62'), JUDGMENT_LINKS[case_value('L1292C117')], case_value('L1292C136'))
        if any((key in p for key in (case_value('L1293C36'), case_value('L1293C46'), case_value('L1293C59')))):
            return (case_value('L1294C20'), case_value('L1294C47'), case_value('L1294C68'), JUDGMENT_LINKS[case_value('L1294C127')], case_value('L1294C146'))
        if any((key in p for key in (case_value('L1295C36'), case_value('L1295C46'), case_value('L1295C56')))):
            return (case_value('L1296C20'), case_value('L1296C56'), case_value('L1296C77'), JUDGMENT_LINKS[case_value('L1296C152')], case_value('L1296C171'))
        return (case_value('L1297C16'), case_value('L1297C46'), case_value('L1297C59'), JUDGMENT_LINKS[case_value('L1297C111')], case_value('L1297C130'))
    if equipment_family == case_value('L1298C27'):
        if any((key in p for key in (case_value('L1299C36'), case_value('L1299C46'), case_value('L1299C56'), case_value('L1299C66')))):
            return (case_value('L1300C20'), case_value('L1300C56'), case_value('L1300C71'), JUDGMENT_LINKS[case_value('L1300C139')], case_value('L1300C148'))
        if case_value('L1301C11') in p:
            return (case_value('L1302C20'), case_value('L1302C47'), case_value('L1302C68'), JUDGMENT_LINKS[case_value('L1302C122')], case_value('L1302C131'))
        return (case_value('L1303C16'), case_value('L1303C46'), case_value('L1303C59'), JUDGMENT_LINKS[case_value('L1303C111')], case_value('L1303C120'))
    if equipment_family == case_value('L1304C27'):
        if any((key in p for key in (case_value('L1305C36'), case_value('L1305C46'), case_value('L1305C56')))):
            return (case_value('L1306C20'), case_value('L1306C56'), case_value('L1306C71'), JUDGMENT_LINKS[case_value('L1306C129')], case_value('L1306C142'))
        return (case_value('L1307C16'), case_value('L1307C46'), case_value('L1307C59'), JUDGMENT_LINKS[case_value('L1307C111')], case_value('L1307C124'))
    return (case_value('L1308C12'), case_value('L1308C42'), case_value('L1308C55'), JUDGMENT_LINKS[case_value('L1308C89')], case_value('L1308C100'))


def add_horizontal_table_ledger(rows: list[ParameterLedgerRow], *, chapter: str, equipment_family: str, source_document: str, table_no: int, table_path: str, tag_column: str='设备位号', object_prefix: str='') -> None:
    table = read_csv_table(table_path)
    header = table[case_value('L1323C19')]
    source_table = f"{case_value('L1324C21')}{table_no:{case_value('L1324C37')}}{case_value('L1324C41')}"
    for row_i, row in enumerate(table[case_value('L1325C38'):], start=case_value('L1325C49')):
        if not any(row):
            continue
        row_map = dict(zip(header, row))
        object_id = row_map.get(tag_column) or row_map.get(case_value('L1329C59')) or row[case_value('L1329C76')]
        if object_prefix:
            object_id = f"{object_prefix}{case_value('L1331C41')}{object_id}"
        for column, raw_value in zip(header, row):
            if not raw_value:
                continue
            value, unit = split_value_unit(column, raw_value)
            source_type, evidence, action, links, formula = classify_late_chapter_parameter(chapter=chapter, equipment_family=equipment_family, source_table=source_table, parameter=column, object_id=object_id)
            note = case_value('L1343C19')
            if object_id == case_value('L1344C28') and source_document == case_value('L1344C59'):
                note = case_value('L1345C23')
            if object_id in {case_value('L1346C29'), case_value('L1346C38')} and source_document == case_value('L1346C70'):
                note = case_value('L1347C23')
            ledger_row(rows, chapter=chapter, equipment_family=equipment_family, object_id=object_id, parameter=column, value=value, unit=unit, source_document=source_document, source_table=source_table, source_location=f"{source_document}{case_value('L1358C51')}{source_table}{case_value('L1358C66')}{row_i}", source_type=source_type, evidence_class=evidence, action=action, judgment_links=links, scriptable_formula=formula, note=note)


def add_matrix_table_ledger(rows: list[ParameterLedgerRow], *, chapter: str, equipment_family: str, source_document: str, table_no: int, table_path: str, object_prefix: str) -> None:
    table = read_csv_table(table_path)
    header = table[case_value('L1379C19')]
    source_table = f"{case_value('L1380C21')}{table_no:{case_value('L1380C37')}}{case_value('L1380C41')}"
    for row_i, row in enumerate(table[case_value('L1381C38'):], start=case_value('L1381C49')):
        if not row:
            continue
        parameter = row[case_value('L1384C24')]
        for col_i, raw_value in enumerate(row[case_value('L1385C46'):], start=case_value('L1385C57')):
            if col_i >= len(header) or not raw_value:
                continue
            object_id = f"{object_prefix}{case_value('L1388C41')}{header[col_i]}"
            value, unit = split_value_unit(parameter, raw_value)
            source_type, evidence, action, links, formula = classify_late_chapter_parameter(chapter=chapter, equipment_family=equipment_family, source_table=source_table, parameter=parameter, object_id=object_id)
            ledger_row(rows, chapter=chapter, equipment_family=equipment_family, object_id=object_id, parameter=parameter, value=value, unit=unit, source_document=source_document, source_table=source_table, source_location=f"{source_document}{case_value('L1407C51')}{source_table}{case_value('L1407C66')}{row_i}", source_type=source_type, evidence_class=evidence, action=action, judgment_links=links, scriptable_formula=formula)


def add_vertical_table_ledger(rows: list[ParameterLedgerRow], *, chapter: str, equipment_family: str, source_document: str, table_no: int, table_path: str, object_id: str) -> None:
    table = read_csv_table(table_path)
    source_table = f"{case_value('L1427C21')}{table_no:{case_value('L1427C37')}}{case_value('L1427C41')}"
    if len(table[case_value('L1428C17')]) >= case_value('L1428C24') and table[case_value('L1428C36')][case_value('L1428C39')] == case_value('L1428C45'):
        object_id = table[case_value('L1429C26')][case_value('L1429C29')]
    for row_i, row in enumerate(table[case_value('L1430C38'):], start=case_value('L1430C49')):
        if len(row) < case_value('L1431C22') or not row[case_value('L1431C35')]:
            continue
        parameter = row[case_value('L1433C24')]
        raw_value = row[case_value('L1434C24')]
        unit = row[case_value('L1435C19')] if len(row) > case_value('L1435C36') else split_value_unit(parameter, raw_value)[case_value('L1435C82')]
        value = raw_value
        source_type, evidence, action, links, formula = classify_late_chapter_parameter(chapter=chapter, equipment_family=equipment_family, source_table=source_table, parameter=parameter, object_id=object_id)
        note = case_value('L1444C15')
        if object_id in {case_value('L1445C25'), case_value('L1445C34')}:
            note = case_value('L1446C19')
        ledger_row(rows, chapter=chapter, equipment_family=equipment_family, object_id=object_id, parameter=parameter, value=value, unit=unit, source_document=source_document, source_table=source_table, source_location=f"{source_document}{case_value('L1457C47')}{source_table}{case_value('L1457C62')}{row_i}", source_type=source_type, evidence_class=evidence, action=action, judgment_links=links, scriptable_formula=formula, note=note)


@require_case_profile.guard
def add_phase_property_table_ledger(rows: list[ParameterLedgerRow]) -> None:
    source_document = case_value('L1468C22')
    source_table = case_value('L1469C19')
    table = read_csv_table(case_value('L1470C27'))
    header = table[case_value('L1471C19')]
    for row_i, row in enumerate(table[case_value('L1472C38'):], start=case_value('L1472C49')):
        for col_i, raw in enumerate(row):
            if col_i >= len(header) or not raw:
                continue
            object_id = f"{case_value('L1476C26')}{header[col_i]}"
            if case_value('L1477C15') in raw:
                parameter, raw_value = raw.split(case_value('L1478C49'), case_value('L1478C54'))
            elif raw.endswith(case_value('L1479C30')):
                parameter, raw_value = (case_value('L1480C39'), raw)
            elif raw.startswith(case_value('L1481C32')) or raw.startswith(case_value('L1481C56')):
                parameter, raw_value = raw.split(case_value('L1482C49'), case_value('L1482C54'))
            else:
                parameter, raw_value = (raw, raw)
            source_type, evidence, action, links, formula = classify_late_chapter_parameter(chapter=case_value('L1486C24'), equipment_family=case_value('L1487C33'), source_table=source_table, parameter=parameter, object_id=object_id)
            ledger_row(rows, chapter=case_value('L1494C24'), equipment_family=case_value('L1495C33'), object_id=object_id, parameter=parameter, value=raw_value, unit=case_value('L1499C21'), source_document=source_document, source_table=source_table, source_location=f"{source_document}{case_value('L1502C51')}{source_table}{case_value('L1502C66')}{row_i}", source_type=source_type, evidence_class=evidence, action=action, judgment_links=links, scriptable_formula=formula)


@require_case_profile.guard
def build_late_chapter_parameter_ledger() -> list[ParameterLedgerRow]:
    rows: list[ParameterLedgerRow] = []
    add_horizontal_table_ledger(rows, chapter=case_value('L1516C16'), equipment_family=case_value('L1517C25'), source_document=case_value('L1518C24'), table_no=case_value('L1519C17'), table_path=case_value('L1520C19'))
    add_matrix_table_ledger(rows, chapter=case_value('L1524C16'), equipment_family=case_value('L1525C25'), source_document=case_value('L1526C24'), table_no=case_value('L1527C17'), table_path=case_value('L1528C19'), object_prefix=case_value('L1529C22'))
    add_phase_property_table_ledger(rows)
    add_vertical_table_ledger(rows, chapter=case_value('L1534C16'), equipment_family=case_value('L1535C25'), source_document=case_value('L1536C24'), table_no=case_value('L1537C17'), table_path=case_value('L1538C19'), object_id=case_value('L1539C18'))
    add_horizontal_table_ledger(rows, chapter=case_value('L1544C16'), equipment_family=case_value('L1545C25'), source_document=case_value('L1546C24'), table_no=case_value('L1547C17'), table_path=case_value('L1548C19'))
    add_horizontal_table_ledger(rows, chapter=case_value('L1552C16'), equipment_family=case_value('L1553C25'), source_document=case_value('L1554C24'), table_no=case_value('L1555C17'), table_path=case_value('L1556C19'), tag_column=case_value('L1557C19'), object_prefix=case_value('L1558C22'))
    add_matrix_table_ledger(rows, chapter=case_value('L1562C16'), equipment_family=case_value('L1563C25'), source_document=case_value('L1564C24'), table_no=case_value('L1565C17'), table_path=case_value('L1566C19'), object_prefix=case_value('L1567C22'))
    add_horizontal_table_ledger(rows, chapter=case_value('L1571C16'), equipment_family=case_value('L1572C25'), source_document=case_value('L1573C24'), table_no=case_value('L1574C17'), table_path=case_value('L1575C19'), tag_column=case_value('L1576C19'), object_prefix=case_value('L1577C22'))
    for table_no, category in [(case_value('L1580C32'), case_value('L1580C36')), (case_value('L1580C48'), case_value('L1580C52')), (case_value('L1580C67'), case_value('L1580C71'))]:
        add_horizontal_table_ledger(rows, chapter=case_value('L1583C20'), equipment_family=case_value('L1584C29'), source_document=case_value('L1585C28'), table_no=table_no, table_path=f"{case_value('L1587C25')}{table_no}{case_value('L1587C71')}", object_prefix=category)
    for table_no, object_id in [(case_value('L1590C33'), case_value('L1590C37')), (case_value('L1590C48'), case_value('L1590C52')), (case_value('L1590C68'), case_value('L1590C72'))]:
        add_vertical_table_ledger(rows, chapter=case_value('L1593C20'), equipment_family=case_value('L1594C29'), source_document=case_value('L1595C28'), table_no=table_no, table_path=f"{case_value('L1597C25')}{table_no}{case_value('L1597C69')}", object_id=object_id)
    add_horizontal_table_ledger(rows, chapter=case_value('L1603C16'), equipment_family=case_value('L1604C25'), source_document=case_value('L1605C24'), table_no=case_value('L1606C17'), table_path=case_value('L1607C19'))
    add_horizontal_table_ledger(rows, chapter=case_value('L1611C16'), equipment_family=case_value('L1612C25'), source_document=case_value('L1613C24'), table_no=case_value('L1614C17'), table_path=case_value('L1615C19'))
    add_horizontal_table_ledger(rows, chapter=case_value('L1619C16'), equipment_family=case_value('L1620C25'), source_document=case_value('L1621C24'), table_no=case_value('L1622C17'), table_path=case_value('L1623C19'), tag_column=case_value('L1624C19'), object_prefix=case_value('L1625C22'))
    add_horizontal_table_ledger(rows, chapter=case_value('L1630C16'), equipment_family=case_value('L1631C25'), source_document=case_value('L1632C24'), table_no=case_value('L1633C17'), table_path=case_value('L1634C19'))
    add_horizontal_table_ledger(rows, chapter=case_value('L1638C16'), equipment_family=case_value('L1639C25'), source_document=case_value('L1640C24'), table_no=case_value('L1641C17'), table_path=case_value('L1642C19'))
    add_horizontal_table_ledger(rows, chapter=case_value('L1646C16'), equipment_family=case_value('L1647C25'), source_document=case_value('L1648C24'), table_no=case_value('L1649C17'), table_path=case_value('L1650C19'))
    add_matrix_table_ledger(rows, chapter=case_value('L1654C16'), equipment_family=case_value('L1655C25'), source_document=case_value('L1656C24'), table_no=case_value('L1657C17'), table_path=case_value('L1658C19'), object_prefix=case_value('L1659C22'))
    add_horizontal_table_ledger(rows, chapter=case_value('L1663C16'), equipment_family=case_value('L1664C25'), source_document=case_value('L1665C24'), table_no=case_value('L1666C17'), table_path=case_value('L1667C19'), tag_column=case_value('L1668C19'), object_prefix=case_value('L1669C22'))
    add_vertical_table_ledger(rows, chapter=case_value('L1673C16'), equipment_family=case_value('L1674C25'), source_document=case_value('L1675C24'), table_no=case_value('L1676C17'), table_path=case_value('L1677C19'), object_id=case_value('L1678C18'))
    return rows


@require_case_profile.guard
def build_calculations() -> list[CalcRow]:
    rows: list[CalcRow] = []
    add(rows, module=case_value('L1689C15'), item=case_value('L1690C13'), source_location=case_value('L1691C24'), formula=case_value('L1692C16'), input_values={case_value('L1693C22'): case_value('L1693C49'), case_value('L1693C55'): case_value('L1693C71'), case_value('L1693C74'): case_value('L1693C94')}, value=tower_bottom_liquid_height(case_value('L1694C41'), case_value('L1694C47'), case_value('L1694C50')), unit=case_value('L1695C13'), document_value=case_value('L1696C23'), tolerance=case_value('L1697C18'))
    add(rows, module=case_value('L1701C15'), item=case_value('L1702C13'), source_location=case_value('L1703C24'), formula=case_value('L1704C16'), input_values={case_value('L1705C22'): case_value('L1705C30'), case_value('L1705C35'): case_value('L1705C43'), case_value('L1705C48'): case_value('L1705C57'), case_value('L1705C62'): case_value('L1705C71'), case_value('L1705C77'): case_value('L1705C90')}, value=case_value('L1706C14') + case_value('L1706C20') + case_value('L1706C26') + case_value('L1706C32') + case_value('L1706C39'), unit=case_value('L1707C13'), document_value=case_value('L1708C23'), tolerance=case_value('L1709C18'))
    add(rows, module=case_value('L1713C15'), item=case_value('L1714C13'), source_location=case_value('L1715C24'), formula=case_value('L1716C16'), input_values={case_value('L1717C22'): case_value('L1717C42'), case_value('L1717C49'): case_value('L1717C67'), case_value('L1717C72'): case_value('L1717C89')}, value=case_value('L1718C14'), unit=case_value('L1719C13'), document_value=case_value('L1720C23'), tolerance=case_value('L1721C18'))
    for name, flow, target_u, od, thk, doc_d, doc_u in [(case_value('L1724C9'), case_value('L1724C25'), case_value('L1724C34'), case_value('L1724C38'), case_value('L1724C45'), case_value('L1724C52'), case_value('L1724C61')), (case_value('L1725C9'), case_value('L1725C20'), case_value('L1725C26'), case_value('L1725C29'), case_value('L1725C36'), case_value('L1725C43'), case_value('L1725C52')), (case_value('L1726C9'), case_value('L1726C22'), case_value('L1726C28'), case_value('L1726C31'), case_value('L1726C38'), case_value('L1726C45'), case_value('L1726C54')), (case_value('L1727C9'), case_value('L1727C31'), case_value('L1727C38'), case_value('L1727C41'), case_value('L1727C48'), case_value('L1727C55'), case_value('L1727C64')), (case_value('L1728C9'), case_value('L1728C29'), case_value('L1728C38'), case_value('L1728C42'), case_value('L1728C49'), case_value('L1728C56'), case_value('L1728C65'))]:
        add_nozzle_rows(rows, module=case_value('L1732C19'), source_location=case_value('L1733C28'), name=name, flow_m3_h=flow, target_u_m_s=target_u, od_m=od, thickness_m=thk, doc_id_m=doc_d, doc_u_m_s=doc_u, id_tolerance_m=case_value('L1741C27'))
    p = case_value('L1744C8')
    cyl = cylinder_calc_thickness(p, case_value('L1745C37'), case_value('L1745C42'), case_value('L1745C47'))
    head = ellipsoidal_head_calc_thickness(p, case_value('L1746C46'), case_value('L1746C51'), case_value('L1746C56'))
    add(rows, module=case_value('L1749C15'), item=case_value('L1750C13'), source_location=case_value('L1751C24'), formula=case_value('L1752C16'), input_values={case_value('L1753C22'): p, case_value('L1753C34'): case_value('L1753C43'), case_value('L1753C48'): case_value('L1753C61'), case_value('L1753C66'): case_value('L1753C78')}, value=cyl, unit=case_value('L1755C13'), document_value=case_value('L1756C23'), tolerance=case_value('L1757C18'))
    add(rows, module=case_value('L1761C15'), item=case_value('L1762C13'), source_location=case_value('L1763C24'), formula=case_value('L1764C16'), input_values={case_value('L1765C22'): p, case_value('L1765C34'): case_value('L1765C43'), case_value('L1765C48'): case_value('L1765C61'), case_value('L1765C66'): case_value('L1765C78')}, value=head, unit=case_value('L1767C13'), document_value=case_value('L1768C23'), tolerance=case_value('L1769C18'))
    add(rows, module=case_value('L1773C15'), item=case_value('L1774C13'), source_location=case_value('L1775C24'), formula=case_value('L1776C16'), input_values={case_value('L1777C22'): cyl, case_value('L1777C50'): case_value('L1777C69'), case_value('L1777C72'): case_value('L1777C97'), case_value('L1777C102'): case_value('L1777C118')}, value=minimum_nominal_thickness(cyl, case_value('L1778C45'), case_value('L1778C48'), case_value('L1778C53')), unit=case_value('L1779C13'), document_value=case_value('L1780C23'), tolerance=None, reliability_class=case_value('L1782C26'), status=case_value('L1783C15'), note=case_value('L1784C13'))
    add(rows, module=case_value('L1790C15'), item=case_value('L1791C13'), source_location=case_value('L1792C24'), formula=case_value('L1793C16'), input_values={case_value('L1794C22'): case_value('L1794C53'), case_value('L1794C59'): case_value('L1794C69')}, value=design_pressure(case_value('L1795C30'), case_value('L1795C36')), unit=case_value('L1796C13'), document_value=case_value('L1797C23'), tolerance=case_value('L1798C18'))
    add(rows, module=case_value('L1802C15'), item=case_value('L1803C13'), source_location=case_value('L1804C24'), formula=case_value('L1805C16'), input_values={case_value('L1806C22'): case_value('L1806C54'), case_value('L1806C60'): case_value('L1806C70')}, value=design_pressure(case_value('L1807C30'), case_value('L1807C36')), unit=case_value('L1808C13'), document_value=case_value('L1809C23'), tolerance=case_value('L1810C18'))
    for name, flow, target_u, od, thk, doc_d, doc_u in [(case_value('L1813C9'), case_value('L1813C23'), case_value('L1813C30'), case_value('L1813C33'), case_value('L1813C40'), case_value('L1813C47'), case_value('L1813C56')), (case_value('L1814C9'), case_value('L1814C24'), case_value('L1814C31'), case_value('L1814C34'), case_value('L1814C41'), case_value('L1814C48'), case_value('L1814C57')), (case_value('L1815C9'), case_value('L1815C24'), case_value('L1815C31'), case_value('L1815C34'), case_value('L1815C41'), case_value('L1815C48'), case_value('L1815C57')), (case_value('L1816C9'), case_value('L1816C25'), case_value('L1816C32'), case_value('L1816C35'), case_value('L1816C42'), case_value('L1816C49'), case_value('L1816C58'))]:
        add_nozzle_rows(rows, module=case_value('L1820C19'), source_location=case_value('L1821C28'), name=name, flow_m3_h=flow, target_u_m_s=target_u, od_m=od, thickness_m=thk, doc_id_m=doc_d, doc_u_m_s=doc_u, id_tolerance_m=case_value('L1829C27'), note=case_value('L1830C17'))
    e_shell = cylinder_calc_thickness(case_value('L1832C38'), case_value('L1832C45'), case_value('L1832C50'), case_value('L1832C55'))
    e_head = ellipsoidal_head_calc_thickness(case_value('L1833C45'), case_value('L1833C52'), case_value('L1833C57'), case_value('L1833C62'))
    add(rows, module=case_value('L1836C15'), item=case_value('L1837C13'), source_location=case_value('L1838C24'), formula=case_value('L1839C16'), input_values={case_value('L1840C22'): case_value('L1840C31'), case_value('L1840C38'): case_value('L1840C47'), case_value('L1840C52'): case_value('L1840C65'), case_value('L1840C70'): case_value('L1840C82')}, value=e_shell, unit=case_value('L1842C13'), document_value=case_value('L1843C23'), tolerance=case_value('L1844C18'))
    add(rows, module=case_value('L1848C15'), item=case_value('L1849C13'), source_location=case_value('L1850C24'), formula=case_value('L1851C16'), input_values={case_value('L1852C22'): case_value('L1852C31'), case_value('L1852C38'): case_value('L1852C47'), case_value('L1852C52'): case_value('L1852C65'), case_value('L1852C70'): case_value('L1852C82')}, value=e_head, unit=case_value('L1854C13'), document_value=case_value('L1855C23'), tolerance=case_value('L1856C18'))
    temps_k = (case_value('L1860C15'), case_value('L1860C23'))
    source_sets = {case_value('L1862C8'): (case_value('L1862C15'), case_value('L1862C19'), case_value('L1862C25'), case_value('L1862C36')), case_value('L1863C8'): (case_value('L1863C15'), case_value('L1863C19'), case_value('L1863C25'), case_value('L1863C35')), case_value('L1864C8'): (case_value('L1864C15'), case_value('L1864C19'), case_value('L1864C24'), case_value('L1864C35'))}
    for kid, (v1, v2, doc_a, doc_e) in source_sets.items():
        k_220 = source_k_to_aspen(v1)
        k_360 = source_k_to_aspen(v2)
        a, e = arrhenius_from_two_points(temps_k[case_value('L1869C49')], k_220, temps_k[case_value('L1869C68')], k_360)
        add(rows, module=case_value('L1872C19'), item=f"{kid}{case_value('L1873C24')}", source_location=case_value('L1874C28'), formula=case_value('L1875C20'), input_values={case_value('L1876C26'): v1, case_value('L1876C42'): case_value('L1876C57')}, value=k_220, unit=case_value('L1878C17'), reliability_class=case_value('L1879C30'), status=case_value('L1880C19'), note=case_value('L1881C17'))
        add(rows, module=case_value('L1885C19'), item=f"{kid}{case_value('L1886C24')}", source_location=case_value('L1887C28'), formula=case_value('L1888C20'), input_values={case_value('L1889C26'): v2, case_value('L1889C42'): case_value('L1889C57')}, value=k_360, unit=case_value('L1891C17'), reliability_class=case_value('L1892C30'), status=case_value('L1893C19'), note=case_value('L1894C17'))
        add(rows, module=case_value('L1898C19'), item=f"{kid}{case_value('L1899C24')}", source_location=case_value('L1900C28'), formula=case_value('L1901C20'), input_values={case_value('L1902C26'): temps_k[case_value('L1902C42')], case_value('L1902C46'): k_220, case_value('L1902C59'): temps_k[case_value('L1902C75')], case_value('L1902C79'): k_360}, value=a, unit=case_value('L1904C17'), document_value=doc_a, tolerance=max(case_value('L1906C26') * float(doc_a), case_value('L1906C47')), reliability_class=case_value('L1907C30'), status=case_value('L1908C19'), note=case_value('L1909C17'))
        add(rows, module=case_value('L1913C19'), item=f"{kid}{case_value('L1914C24')}", source_location=case_value('L1915C28'), formula=case_value('L1916C20'), input_values={case_value('L1917C26'): temps_k[case_value('L1917C42')], case_value('L1917C46'): k_220, case_value('L1917C59'): temps_k[case_value('L1917C75')], case_value('L1917C79'): k_360}, value=e, unit=case_value('L1919C17'), document_value=doc_e, tolerance=case_value('L1921C22'), reliability_class=case_value('L1922C30'), status=case_value('L1923C19'), note=case_value('L1924C17'))
    add(rows, module=case_value('L1930C15'), item=case_value('L1931C13'), source_location=case_value('L1932C24'), formula=case_value('L1933C16'), input_values={case_value('L1934C22'): case_value('L1934C36'), case_value('L1934C42'): case_value('L1934C60'), case_value('L1934C67'): case_value('L1934C84'), case_value('L1934C89'): case_value('L1934C115'), case_value('L1934C121'): case_value('L1934C132')}, value=catalyst_mass(case_value('L1935C28'), case_value('L1935C34'), case_value('L1935C41'), case_value('L1935C46'), case_value('L1935C52')), unit=case_value('L1936C13'), document_value=case_value('L1937C23'), tolerance=case_value('L1938C18'))
    add(rows, module=case_value('L1942C15'), item=case_value('L1943C13'), source_location=case_value('L1944C24'), formula=case_value('L1945C16'), input_values={case_value('L1946C22'): case_value('L1946C36'), case_value('L1946C42'): case_value('L1946C56'), case_value('L1946C60'): case_value('L1946C76'), case_value('L1946C82'): case_value('L1946C97')}, value=bundle_diameter(case_value('L1947C30'), case_value('L1947C36')), unit=case_value('L1948C13'), document_value=case_value('L1949C23'), tolerance=case_value('L1950C18'))
    area = case_value('L1952C11') * math.pi * case_value('L1952C28') * case_value('L1952C36')
    add(rows, module=case_value('L1955C15'), item=case_value('L1956C13'), source_location=case_value('L1957C24'), formula=case_value('L1958C16'), input_values={case_value('L1959C22'): case_value('L1959C36'), case_value('L1959C42'): case_value('L1959C60'), case_value('L1959C67'): case_value('L1959C84')}, value=area, unit=case_value('L1961C13'), document_value=case_value('L1962C23'), tolerance=case_value('L1963C18'), note=case_value('L1964C13'))
    nu = packed_bed_tube_nu(case_value('L1966C28'), case_value('L1966C35'), case_value('L1966C42'), case_value('L1966C48'), case_value('L1966C57'), case_value('L1966C63'), case_value('L1966C71'))
    alpha_i = case_value('L1967C14') / case_value('L1967C23') * nu
    u_overall = overall_u_outer_area(alpha_i, case_value('L1968C46'), case_value('L1968C52'), case_value('L1968C59'), case_value('L1968C66'), case_value('L1968C74'), case_value('L1968C78'), case_value('L1968C87'))
    req_area = case_value('L1969C15') / (case_value('L1969C25') * u_overall)
    add(rows, module=case_value('L1972C15'), item=case_value('L1973C13'), source_location=case_value('L1974C24'), formula=case_value('L1975C16'), input_values={case_value('L1976C22'): case_value('L1976C30'), case_value('L1976C37'): case_value('L1976C46'), case_value('L1976C53'): case_value('L1976C66'), case_value('L1976C72'): case_value('L1976C83'), case_value('L1976C92'): case_value('L1976C105'), case_value('L1976C111'): case_value('L1976C127'), case_value('L1976C135'): case_value('L1976C153')}, value=nu, unit=case_value('L1978C13'), document_value=case_value('L1979C23'), tolerance=case_value('L1980C18'))
    add(rows, module=case_value('L1984C15'), item=case_value('L1985C13'), source_location=case_value('L1986C24'), formula=case_value('L1987C16'), input_values={case_value('L1988C22'): case_value('L1988C38'), case_value('L1988C46'): case_value('L1988C64'), case_value('L1988C71'): nu}, value=alpha_i, unit=case_value('L1990C13'), document_value=case_value('L1991C23'), tolerance=case_value('L1992C18'))
    add(rows, module=case_value('L1996C15'), item=case_value('L1997C13'), source_location=case_value('L1998C24'), formula=case_value('L1999C16'), input_values={case_value('L2000C22'): alpha_i, case_value('L2000C42'): case_value('L2000C53'), case_value('L2000C59'): case_value('L2000C67'), case_value('L2000C74'): case_value('L2000C82'), case_value('L2000C89'): case_value('L2000C99'), case_value('L2000C107'): case_value('L2000C123'), case_value('L2000C127'): case_value('L2000C134'), case_value('L2000C143'): case_value('L2000C150')}, value=u_overall, unit=case_value('L2002C13'), document_value=case_value('L2003C23'), tolerance=case_value('L2004C18'))
    add(rows, module=case_value('L2008C15'), item=case_value('L2009C13'), source_location=case_value('L2010C24'), formula=case_value('L2011C16'), input_values={case_value('L2012C22'): case_value('L2012C29'), case_value('L2012C37'): case_value('L2012C54'), case_value('L2012C59'): u_overall}, value=req_area, unit=case_value('L2014C13'), document_value=case_value('L2015C23'), tolerance=case_value('L2016C18'))
    add(rows, module=case_value('L2020C15'), item=case_value('L2021C13'), source_location=case_value('L2022C24'), formula=case_value('L2023C16'), input_values={case_value('L2024C22'): area, case_value('L2024C46'): req_area}, value=(area - req_area) / req_area * case_value('L2025C45'), unit=case_value('L2026C13'), document_value=case_value('L2027C23'), tolerance=case_value('L2028C18'))
    rem, friction, dp_pa = ergun_pressure_drop(case_value('L2030C47'), case_value('L2030C54'), case_value('L2030C61'), case_value('L2030C67'), case_value('L2030C76'), case_value('L2030C81'))
    add(rows, module=case_value('L2033C15'), item=case_value('L2034C13'), source_location=case_value('L2035C24'), formula=case_value('L2036C16'), input_values={case_value('L2037C22'): case_value('L2037C30'), case_value('L2037C37'): case_value('L2037C46'), case_value('L2037C53'): case_value('L2037C66'), case_value('L2037C72'): case_value('L2037C83'), case_value('L2037C92'): case_value('L2037C103')}, value=rem, unit=case_value('L2039C13'), document_value=case_value('L2040C23'), tolerance=case_value('L2041C18'))
    add(rows, module=case_value('L2045C15'), item=case_value('L2046C13'), source_location=case_value('L2047C24'), formula=case_value('L2048C16'), input_values={case_value('L2049C22'): rem}, value=friction, unit=case_value('L2051C13'), document_value=case_value('L2052C23'), tolerance=case_value('L2053C18'))
    add(rows, module=case_value('L2057C15'), item=case_value('L2058C13'), source_location=case_value('L2059C24'), formula=case_value('L2060C16'), input_values={case_value('L2061C22'): friction, case_value('L2061C44'): case_value('L2061C57'), case_value('L2061C63'): case_value('L2061C72'), case_value('L2061C79'): case_value('L2061C95'), case_value('L2061C100'): case_value('L2061C116'), case_value('L2061C123'): case_value('L2061C134')}, value=dp_pa, unit=case_value('L2063C13'), document_value=case_value('L2064C23'), tolerance=case_value('L2065C18'))
    for name, flow, target_u, od, thk, doc_d, doc_u in [(case_value('L2068C9'), case_value('L2068C21'), case_value('L2068C29'), case_value('L2068C33'), case_value('L2068C40'), case_value('L2068C48'), case_value('L2068C57')), (case_value('L2069C9'), case_value('L2069C23'), case_value('L2069C31'), case_value('L2069C35'), case_value('L2069C42'), case_value('L2069C50'), case_value('L2069C59')), (case_value('L2070C9'), case_value('L2070C30'), case_value('L2070C39'), case_value('L2070C42'), case_value('L2070C49'), case_value('L2070C57'), case_value('L2070C66')), (case_value('L2071C9'), case_value('L2071C31'), case_value('L2071C40'), case_value('L2071C43'), case_value('L2071C50'), case_value('L2071C58'), case_value('L2071C67'))]:
        add_nozzle_rows(rows, module=case_value('L2075C19'), source_location=case_value('L2076C28'), name=name, flow_m3_h=flow, target_u_m_s=target_u, od_m=od, thickness_m=thk, doc_id_m=doc_d, doc_u_m_s=doc_u, id_tolerance_m=case_value('L2084C27'), u_tolerance_m_s=case_value('L2085C28'))
    r_shell = cylinder_calc_thickness(case_value('L2087C38'), case_value('L2087C44'), case_value('L2087C50'), case_value('L2087C57'))
    add(rows, module=case_value('L2090C15'), item=case_value('L2091C13'), source_location=case_value('L2092C24'), formula=case_value('L2093C16'), input_values={case_value('L2094C22'): case_value('L2094C31'), case_value('L2094C37'): case_value('L2094C46'), case_value('L2094C52'): case_value('L2094C65'), case_value('L2094C72'): case_value('L2094C84')}, value=r_shell, unit=case_value('L2096C13'), document_value=case_value('L2097C23'), tolerance=case_value('L2098C18'))
    add(rows, module=case_value('L2102C15'), item=case_value('L2103C13'), source_location=case_value('L2104C24'), formula=case_value('L2105C16'), input_values={case_value('L2106C22'): r_shell, case_value('L2106C43'): case_value('L2106C68'), case_value('L2106C73'): case_value('L2106C89')}, value=r_shell + case_value('L2107C24') + case_value('L2107C30'), unit=case_value('L2108C13'), document_value=case_value('L2109C23'), tolerance=case_value('L2110C18'), reliability_class=case_value('L2111C26'), note=case_value('L2112C13'))
    add_t802_union_rows(rows)
    add_supplement3_rows(rows)
    add_late_chapter_audit_rows(rows)
    return rows


MODULE_ROWS = CaseGlobal("MODULE_ROWS")


ASPEN_SECTIONS = CaseGlobal("ASPEN_SECTIONS")


NONSCRIPT_BOUNDARY_ROWS = CaseGlobal("NONSCRIPT_BOUNDARY_ROWS")


SECTION_RULES = CaseGlobal("SECTION_RULES")


PARAMETER_SOURCE_ROWS = CaseGlobal("PARAMETER_SOURCE_ROWS")


DEVICE_MAPPING_ROWS = CaseGlobal("DEVICE_MAPPING_ROWS")


def reliability_label(code: str) -> str:
    labels = {
        "A_formula_reproduced": "A 公式复算通过",
        "B_document_selection_reproduced": "B 复算到选型前步骤",
        "C_external_software_required": "C 需外部软件证据",
        "D_kinetics_provisional": "D 动力学暂定",
        "E_symbolic_catalog_selection": "E 象征性/目录选型",
    }
    return labels.get(code, code)


def fmt_float(value: float | None, digits: int = 6) -> str:
    if value is None:
        return ""
    return f"{value:.{digits}g}"


def fmt_percent(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.3%}"


def md_cell(value: Any) -> str:
    return str(value).replace("\n", " ").replace("|", "/")


def summarize(rows: list[CalcRow]) -> dict[str, Any]:
    comparable = [row for row in rows if row.pass_check is not None]
    passed = [row for row in comparable if row.pass_check]
    failed = [row for row in comparable if row.pass_check is False]
    by_class: dict[str, int] = {}
    by_module: dict[str, int] = {}
    for row in rows:
        by_class[row.reliability_class] = by_class.get(row.reliability_class, 0) + 1
        by_module[row.module] = by_module.get(row.module, 0) + 1
    return {
        "total_rows": len(rows),
        "comparable_rows": len(comparable),
        "passed_rows": len(passed),
        "failed_rows": len(failed),
        "by_reliability_class": by_class,
        "by_module": by_module,
        "failed_items": [asdict(row) for row in failed],
    }


def failure_category_from_dict(item: dict[str, Any]) -> str:
    module = item.get(case_value('L2637C22'), case_value('L2637C32'))
    if module == case_value('L2638C17'):
        return case_value('L2639C15')
    if module == case_value('L2640C17'):
        return case_value('L2641C15')
    return case_value('L2642C11')


def failed_category_counts(summary: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in summary.get("failed_items", []):
        category = failure_category_from_dict(item)
        counts[category] = counts.get(category, 0) + 1
    return counts


def failed_category_lines(summary: dict[str, Any]) -> list[str]:
    counts = failed_category_counts(summary)
    if not counts:
        return ["- 无需复核项。"]
    return [f"- {category}：{count} 行" for category, count in sorted(counts.items())]


@require_case_profile.guard
def write_calculation_outputs(rows: list[CalcRow], summary: dict[str, Any]) -> None:
    payload = [asdict(row) for row in rows]
    (DATA / case_value('L2662C12')).write_text(json.dumps(payload, ensure_ascii=False, indent=case_value('L2662C98')), encoding=case_value('L2662C111'))
    (DATA / case_value('L2663C12')).write_text(json.dumps(summary, ensure_ascii=False, indent=case_value('L2663C98')), encoding=case_value('L2663C111'))
    lines = [case_value('L2666C8'), case_value('L2667C8'), case_value('L2668C8'), case_value('L2669C8'), f"{case_value('L2670C10')}{summary[case_value('L2670C36')]}", f"{case_value('L2671C10')}{summary[case_value('L2671C48')]}", f"{case_value('L2672C10')}{summary[case_value('L2672C39')]}", f"{case_value('L2673C10')}{summary[case_value('L2673C33')]}", case_value('L2674C8'), case_value('L2675C8'), case_value('L2676C8')]
    for row in rows:
        inputs = json.dumps(row.input_values, ensure_ascii=False, separators=(case_value('L2679C78'), case_value('L2679C83')))
        if len(inputs) > case_value('L2680C25'):
            inputs = inputs[:case_value('L2681C29')] + case_value('L2681C36')
        lines.append(case_value('L2683C12') + case_value('L2684C14').join([row.module, row.item, row.source_location, f"{case_value('L2689C22')}{row.formula}{case_value('L2689C36')}", f"{case_value('L2690C22')}{inputs}{case_value('L2690C31')}", fmt_float(row.value), row.unit, row.document_value_raw, fmt_float(row.abs_error), fmt_float(row.tolerance), reliability_label(row.reliability_class), row.status, row.note.replace(case_value('L2698C37'), case_value('L2698C42'))]) + case_value('L2701C14'))
    (OUT / case_value('L2703C11')).write_text(case_value('L2703C53').join(lines) + case_value('L2703C72'), encoding=case_value('L2703C87'))


@require_case_profile.guard
def write_module_report() -> None:
    lines = [case_value('L2708C8'), case_value('L2709C8'), case_value('L2710C8'), case_value('L2711C8'), case_value('L2712C8'), case_value('L2713C8')]
    for module, coverage, task in MODULE_ROWS:
        lines.append(f"{case_value('L2716C23')}{module}{case_value('L2716C33')}{coverage}{case_value('L2716C46')}{task}{case_value('L2716C55')}")
    lines.extend([case_value('L2719C12'), case_value('L2720C12'), case_value('L2721C12'), case_value('L2722C12'), case_value('L2723C12'), case_value('L2724C12'), case_value('L2725C12'), case_value('L2726C12'), case_value('L2727C12')])
    (OUT / case_value('L2730C11')).write_text(case_value('L2730C56').join(lines) + case_value('L2730C75'), encoding=case_value('L2730C90'))


@require_case_profile.guard
def write_aspen_report() -> None:
    lines = [case_value('L2735C8'), case_value('L2736C8'), case_value('L2737C8'), case_value('L2738C8'), case_value('L2739C8'), case_value('L2740C8')]
    for group, equipment, params in ASPEN_SECTIONS:
        lines.append(f"{case_value('L2743C23')}{group}{case_value('L2743C32')}{equipment}{case_value('L2743C46')}{params}{case_value('L2743C57')}")
    lines.extend([case_value('L2746C12'), case_value('L2747C12'), case_value('L2748C12'), case_value('L2749C12'), case_value('L2750C12'), case_value('L2751C12'), case_value('L2752C12'), case_value('L2753C12'), case_value('L2754C12'), case_value('L2755C12'), case_value('L2756C12'), case_value('L2757C12'), case_value('L2758C12'), case_value('L2759C12'), case_value('L2760C12'), case_value('L2761C12')])
    (OUT / case_value('L2764C11')).write_text(case_value('L2764C55').join(lines) + case_value('L2764C74'), encoding=case_value('L2764C89'))


@require_case_profile.guard
def write_reliability_report(rows: list[CalcRow], summary: dict[str, Any]) -> None:
    class_lines = []
    for code, count in sorted(summary[case_value('L2769C38')].items()):
        class_lines.append(f"{case_value('L2770C29')}{reliability_label(code)}{case_value('L2770C56')}{count}{case_value('L2770C66')}")
    failed = summary[case_value('L2771C21')]
    failed_lines = [case_value('L2772C20')] if not failed else [f"{case_value('L2772C52')}{item[case_value('L2772C60')]}{case_value('L2772C70')}{item[case_value('L2772C79')]}{case_value('L2772C87')}{item[case_value('L2772C106')]}{case_value('L2772C115')}{item[case_value('L2772C134')]}{case_value('L2772C156')}" for item in failed]
    lines = [case_value('L2774C8'), case_value('L2775C8'), case_value('L2776C8'), case_value('L2777C8'), f"{case_value('L2778C10')}{summary[case_value('L2778C35')]}{case_value('L2778C49')}{summary[case_value('L2778C72')]}{case_value('L2778C91')}{summary[case_value('L2778C137')]}{case_value('L2778C152')}{summary[case_value('L2778C192')]}{case_value('L2778C207')}", case_value('L2779C8'), case_value('L2780C8'), case_value('L2781C8'), case_value('L2782C8'), case_value('L2783C8'), *class_lines, case_value('L2785C8'), case_value('L2786C8'), case_value('L2787C8'), case_value('L2788C8'), case_value('L2789C8'), f"{case_value('L2790C10')}{current_table_count()}{case_value('L2790C53')}", case_value('L2791C8'), case_value('L2792C8'), case_value('L2793C8'), case_value('L2794C8'), case_value('L2795C8'), case_value('L2796C8'), case_value('L2797C8'), case_value('L2798C8'), *failed_category_lines(summary), case_value('L2800C8'), case_value('L2801C8'), case_value('L2802C8'), *failed_lines, case_value('L2804C8'), case_value('L2805C8'), case_value('L2806C8'), case_value('L2807C8'), case_value('L2808C8'), case_value('L2809C8'), case_value('L2810C8'), case_value('L2811C8')]
    (OUT / case_value('L2813C11')).write_text(case_value('L2813C50').join(lines) + case_value('L2813C69'), encoding=case_value('L2813C84'))


@require_case_profile.guard
def write_boundary_report() -> None:
    lines = [case_value('L2818C8'), case_value('L2819C8'), case_value('L2820C8'), case_value('L2821C8'), case_value('L2822C8'), case_value('L2823C8')]
    for item, source, cls, judgement, evidence in NONSCRIPT_BOUNDARY_ROWS:
        lines.append(f"{case_value('L2826C23')}{item}{case_value('L2826C31')}{source}{case_value('L2826C42')}{reliability_label(cls)}{case_value('L2826C69')}{judgement}{case_value('L2826C83')}{evidence}{case_value('L2826C96')}")
    (OUT / case_value('L2827C11')).write_text(case_value('L2827C56').join(lines) + case_value('L2827C75'), encoding=case_value('L2827C90'))


@require_case_profile.guard
def write_script_manual(summary: dict[str, Any]) -> None:
    lines = [case_value('L2832C8'), case_value('L2833C8'), case_value('L2834C8'), case_value('L2835C8'), case_value('L2836C8'), case_value('L2837C8'), case_value('L2838C8'), case_value('L2839C8'), case_value('L2840C8'), case_value('L2841C8'), case_value('L2842C8'), case_value('L2843C8'), case_value('L2844C8'), case_value('L2845C8'), case_value('L2846C8'), case_value('L2847C8'), case_value('L2848C8'), case_value('L2849C8'), case_value('L2850C8'), case_value('L2851C8'), case_value('L2852C8'), case_value('L2853C8'), case_value('L2854C8'), case_value('L2855C8'), case_value('L2856C8'), case_value('L2857C8'), case_value('L2858C8'), case_value('L2859C8'), case_value('L2860C8'), case_value('L2861C8'), case_value('L2862C8'), case_value('L2863C8'), case_value('L2864C8'), f"{case_value('L2865C10')}{summary[case_value('L2865C36')]}", f"{case_value('L2866C10')}{summary[case_value('L2866C49')]}", f"{case_value('L2867C10')}{summary[case_value('L2867C33')]}", f"{case_value('L2868C10')}{summary[case_value('L2868C36')]}", case_value('L2869C8'), case_value('L2870C8'), case_value('L2871C8'), case_value('L2872C8'), case_value('L2873C8'), case_value('L2874C8'), case_value('L2875C8'), case_value('L2876C8'), case_value('L2877C8'), case_value('L2878C8'), case_value('L2879C8'), case_value('L2880C8')]
    (OUT / case_value('L2882C11')).write_text(case_value('L2882C53').join(lines) + case_value('L2882C72'), encoding=case_value('L2882C87'))


@require_case_profile.guard
def write_section_precision_report(rows: list[CalcRow], summary: dict[str, Any]) -> None:
    lines = [case_value('L2887C8'), case_value('L2888C8'), case_value('L2889C8'), case_value('L2890C8'), f"{case_value('L2891C10')}{summary[case_value('L2891C39')]}", f"{case_value('L2892C10')}{summary[case_value('L2892C49')]}", f"{case_value('L2893C10')}{summary[case_value('L2893C33')]}", f"{case_value('L2894C10')}{summary[case_value('L2894C36')]}", case_value('L2895C8'), case_value('L2896C8'), case_value('L2897C8')]
    section_rows: dict[str, list[CalcRow]] = {}
    for section_id, section_name, modules, precision_rule, source_logic in SECTION_RULES:
        matched = [row for row in rows if row.module in modules]
        section_rows[section_id] = matched
        comparable = [row for row in matched if row.pass_check is not None]
        passed = [row for row in comparable if row.pass_check]
        failed = [row for row in comparable if row.pass_check is False]
        max_abs = max((row.abs_error for row in matched if row.abs_error is not None), default=None)
        max_rel = max((row.rel_error for row in matched if row.rel_error is not None), default=None)
        module_text = case_value('L2908C22').join(modules) if modules else case_value('L2908C58')
        lines.append(case_value('L2910C12') + case_value('L2911C14').join([f"{section_id}{case_value('L2913C34')}{section_name}", module_text, str(len(matched)), str(len(comparable)), str(len(passed)), str(len(failed)), fmt_float(max_abs), fmt_percent(max_rel), md_cell(precision_rule), md_cell(source_logic)]) + case_value('L2925C14'))
    lines.extend([case_value('L2930C12'), case_value('L2931C12'), case_value('L2932C12'), case_value('L2933C12')])
    for section_id, section_name, modules, _precision_rule, _source_logic in SECTION_RULES:
        matched = section_rows[section_id]
        lines.extend([case_value('L2938C22'), f"{case_value('L2938C28')}{section_id}{case_value('L2938C44')}{section_name}", case_value('L2938C62')])
        if not matched:
            if section_id == case_value('L2940C29'):
                lines.append(case_value('L2941C29'))
            else:
                lines.append(case_value('L2943C29'))
            continue
        lines.extend([case_value('L2947C16'), case_value('L2948C16')])
        for row in matched:
            lines.append(case_value('L2953C16') + case_value('L2954C18').join([md_cell(row.module), md_cell(row.item), fmt_float(row.value), md_cell(row.unit), md_cell(row.document_value_raw), fmt_float(row.abs_error), fmt_float(row.tolerance), md_cell(row.status), reliability_label(row.reliability_class)]) + case_value('L2967C18'))
    (OUT / case_value('L2969C11')).write_text(case_value('L2969C53').join(lines) + case_value('L2969C72'), encoding=case_value('L2969C87'))


@require_case_profile.guard
def write_section_parameter_source_report() -> None:
    section_names = {section_id: section_name for section_id, section_name, *_rest in SECTION_RULES}
    source_counts: dict[str, int] = {}
    by_section: dict[str, list[tuple[str, str, str, str, str, str]]] = {}
    for section_id, parameter, value, unit, source_type, source_note, destination in PARAMETER_SOURCE_ROWS:
        source_counts[source_type] = source_counts.get(source_type, case_value('L2977C68')) + case_value('L2977C73')
        by_section.setdefault(section_id, []).append((parameter, value, unit, source_type, source_note, destination))
    lines = [case_value('L2981C8'), case_value('L2982C8'), case_value('L2983C8'), case_value('L2984C8'), case_value('L2985C8'), case_value('L2986C8')]
    for source_type, count in sorted(source_counts.items()):
        lines.append(f"{case_value('L2989C23')}{md_cell(source_type)}{case_value('L2989C47')}{count}{case_value('L2989C57')}")
    for section_id, section_name, *_rest in SECTION_RULES:
        rows = by_section.get(section_id, [])
        lines.extend([case_value('L2993C22'), f"{case_value('L2993C28')}{section_id}{case_value('L2993C43')}{section_name}", case_value('L2993C61')])
        if not rows:
            lines.append(case_value('L2995C25'))
            continue
        lines.extend([case_value('L2999C16'), case_value('L3000C16')])
        for parameter, value, unit, source_type, source_note, destination in rows:
            lines.append(case_value('L3005C16') + case_value('L3006C18').join([md_cell(parameter), md_cell(value), md_cell(unit), md_cell(source_type), md_cell(source_note), md_cell(destination)]) + case_value('L3016C18'))
    orphan_sections = sorted(set(by_section) - set(section_names))
    if orphan_sections:
        lines.extend([case_value('L3021C22'), case_value('L3021C26'), case_value('L3021C48')])
        for section_id in orphan_sections:
            lines.append(f"{case_value('L3023C27')}{section_id}")
    (OUT / case_value('L3024C11')).write_text(case_value('L3024C53').join(lines) + case_value('L3024C72'), encoding=case_value('L3024C87'))


def is_manual_source(source_type: str) -> bool:
    manual_markers = ("人工设定", "人工圆整", "软件校核", "规范+人工", "规范/人工")
    return any(marker in source_type for marker in manual_markers)


@require_case_profile.guard
def write_manual_parameter_report() -> None:
    section_names = {section_id: section_name for section_id, section_name, *_rest in SECTION_RULES}
    manual_rows = [row for row in PARAMETER_SOURCE_ROWS if is_manual_source(row[case_value('L3035C69')])]
    lines = [case_value('L3038C8'), case_value('L3039C8'), case_value('L3040C8'), case_value('L3041C8'), case_value('L3042C8'), case_value('L3043C8'), f"{case_value('L3044C10')}{len(manual_rows)}", case_value('L3045C8'), case_value('L3046C8')]
    for section_id, section_name, *_rest in SECTION_RULES:
        rows = [row for row in manual_rows if row[case_value('L3050C50')] == section_id]
        if not rows:
            continue
        lines.extend([f"{case_value('L3053C24')}{section_id}{case_value('L3053C39')}{section_name}", case_value('L3053C57')])
        lines.extend([case_value('L3056C16'), case_value('L3057C16')])
        for _section_id, parameter, value, unit, source_type, source_note, destination in rows:
            lines.append(case_value('L3062C16') + case_value('L3063C18').join([md_cell(parameter), md_cell(value), md_cell(unit), md_cell(source_type), md_cell(source_note), md_cell(destination)]) + case_value('L3073C18'))
        lines.append(case_value('L3075C21'))
    lines.extend([case_value('L3079C12'), case_value('L3080C12'), case_value('L3081C12'), case_value('L3082C12'), case_value('L3083C12'), case_value('L3084C12'), case_value('L3085C12'), case_value('L3086C12'), case_value('L3087C12'), case_value('L3088C12'), case_value('L3089C12'), case_value('L3090C12'), case_value('L3091C12'), case_value('L3092C12'), case_value('L3093C12'), case_value('L3094C12'), case_value('L3095C12'), case_value('L3096C12'), case_value('L3097C12'), case_value('L3098C12'), case_value('L3099C12'), case_value('L3100C12'), case_value('L3101C12'), case_value('L3102C12'), case_value('L3103C12'), case_value('L3104C12')])
    (OUT / case_value('L3107C11')).write_text(case_value('L3107C59').join(lines) + case_value('L3107C78'), encoding=case_value('L3107C93'))


@require_case_profile.guard
def write_device_mapping_report() -> None:
    lines = [case_value('L3112C8'), case_value('L3113C8'), case_value('L3114C8'), case_value('L3115C8'), case_value('L3116C8'), case_value('L3117C8')]
    for family, tag, source, role, available, transferable, forbidden, status in DEVICE_MAPPING_ROWS:
        lines.append(case_value('L3121C12') + case_value('L3122C14').join([md_cell(family), md_cell(tag), md_cell(source), md_cell(role), md_cell(available), md_cell(transferable), md_cell(forbidden), md_cell(status)]) + case_value('L3134C14'))
    lines.extend([case_value('L3138C12'), case_value('L3139C12'), case_value('L3140C12'), case_value('L3141C12'), case_value('L3142C12'), case_value('L3143C12'), case_value('L3144C12')])
    (OUT / case_value('L3147C11')).write_text(case_value('L3147C50').join(lines) + case_value('L3147C69'), encoding=case_value('L3147C84'))


@require_case_profile.guard
def write_audit_gap_report(rows: list[CalcRow], summary: dict[str, Any]) -> None:
    all_modules = {row.module for row in rows}
    covered_modules = {module for _sid, _name, modules, _precision, _source in SECTION_RULES for module in modules}
    unmatched_modules = sorted(all_modules - covered_modules)
    parameter_sections = {row[case_value('L3154C30')] for row in PARAMETER_SOURCE_ROWS}
    rule_sections = {section_id for section_id, *_rest in SECTION_RULES}
    parameter_sections_without_rule = sorted(parameter_sections - rule_sections)
    no_parameter_sections = [f"{section_id}{case_value('L3158C22')}{section_name}" for section_id, section_name, *_rest in SECTION_RULES if section_id not in parameter_sections]
    stale_table_dirs = sorted((p.name for p in (DATA / case_value('L3163C32')).iterdir() if p.is_dir() and p.name not in CURRENT_DOC_IDS))
    source_counts: dict[str, int] = {}
    for _section_id, _parameter, _value, _unit, source_type, _source_note, _destination in PARAMETER_SOURCE_ROWS:
        source_counts[source_type] = source_counts.get(source_type, case_value('L3167C68')) + case_value('L3167C73')
    lines = [case_value('L3170C8'), case_value('L3171C8'), case_value('L3172C8'), case_value('L3173C8'), f"{case_value('L3174C10')}{len(CURRENT_DOC_IDS)}{case_value('L3174C58')}", f"{case_value('L3175C10')}{current_table_count()}{case_value('L3175C59')}", f"{case_value('L3176C10')}{summary[case_value('L3176C40')]}{case_value('L3176C54')}{summary[case_value('L3176C97')]}{case_value('L3176C116')}{summary[case_value('L3176C141')]}{case_value('L3176C156')}{summary[case_value('L3176C181')]}{case_value('L3176C196')}", f"{case_value('L3177C10')}{(case_value('L3177C34') if not unmatched_modules else case_value('L3177C91'))}{case_value('L3177C121')}", f"{case_value('L3178C10')}{(case_value('L3178C34') if not parameter_sections_without_rule else case_value('L3178C105'))}{case_value('L3178C135')}", case_value('L3179C8'), case_value('L3180C8'), case_value('L3181C8'), case_value('L3182C8'), f"{case_value('L3183C10')}{current_table_count()}{case_value('L3183C142')}", case_value('L3184C8'), case_value('L3185C8'), case_value('L3186C8'), case_value('L3187C8'), case_value('L3188C8'), case_value('L3189C8'), case_value('L3190C8'), case_value('L3191C8'), case_value('L3192C8'), case_value('L3193C8'), case_value('L3194C8'), case_value('L3195C8'), case_value('L3196C8'), case_value('L3197C8'), case_value('L3198C8'), case_value('L3199C8'), case_value('L3200C8'), case_value('L3201C8'), case_value('L3202C8'), f"{case_value('L3203C10')}{(case_value('L3203C55') if not unmatched_modules else case_value('L3203C94') + case_value('L3203C108').join(unmatched_modules))}{case_value('L3203C137')}", f"{case_value('L3204C10')}{(case_value('L3204C52') if not parameter_sections_without_rule else case_value('L3204C105') + case_value('L3204C119').join(parameter_sections_without_rule))}{case_value('L3204C162')}", f"{case_value('L3205C10')}{(case_value('L3205C40').join(no_parameter_sections) if no_parameter_sections else case_value('L3205C103'))}{case_value('L3205C109')}", f"{case_value('L3206C10')}{(case_value('L3206C40').join(stale_table_dirs) if stale_table_dirs else case_value('L3206C93'))}{case_value('L3206C99')}", case_value('L3207C8'), case_value('L3208C8'), case_value('L3209C8'), case_value('L3210C8'), case_value('L3211C8'), case_value('L3212C8'), case_value('L3213C8')]
    for source_type, count in sorted(source_counts.items()):
        lines.append(f"{case_value('L3216C23')}{md_cell(source_type)}{case_value('L3216C47')}{count}{case_value('L3216C57')}")
    lines.extend([case_value('L3219C12'), case_value('L3220C12'), case_value('L3221C12'), f"{case_value('L3222C14')}{summary[case_value('L3222C117')]}{case_value('L3222C136')}{summary[case_value('L3222C175')]}{case_value('L3222C190')}{summary[case_value('L3222C211')]}{case_value('L3222C226')}"])
    (OUT / case_value('L3225C11')).write_text(case_value('L3225C56').join(lines) + case_value('L3225C75'), encoding=case_value('L3225C90'))


@require_case_profile.guard
def write_formula_reliability_report(rows: list[CalcRow], summary: dict[str, Any]) -> None:
    doc_groups = [(case_value('L3231C12'), [case_value('L3232C13'), case_value('L3232C28'), case_value('L3232C44'), case_value('L3232C62'), case_value('L3232C81'), case_value('L3232C97'), case_value('L3232C115'), case_value('L3232C133'), case_value('L3232C150'), case_value('L3232C173'), case_value('L3232C196'), case_value('L3232C212'), case_value('L3232C230')]), (case_value('L3235C12'), [case_value('L3236C13'), case_value('L3236C33')]), (case_value('L3239C12'), [case_value('L3240C13'), case_value('L3240C34'), case_value('L3240C58'), case_value('L3240C79'), case_value('L3240C103'), case_value('L3240C133')]), (case_value('L3243C12'), [case_value('L3244C13'), case_value('L3244C36'), case_value('L3244C60'), case_value('L3244C89'), case_value('L3244C111')])]
    lines = [case_value('L3249C8'), case_value('L3250C8'), case_value('L3251C8'), case_value('L3252C8'), f"{case_value('L3253C10')}{summary[case_value('L3253C43')]}", f"{case_value('L3254C10')}{summary[case_value('L3254C57')]}", f"{case_value('L3255C10')}{summary[case_value('L3255C36')]}", f"{case_value('L3256C10')}{summary[case_value('L3256C49')]}", case_value('L3257C8'), case_value('L3258C8'), case_value('L3259C8'), case_value('L3260C8'), case_value('L3261C8')]
    for doc_name, modules in doc_groups:
        matched = [row for row in rows if row.module in modules]
        comparable = [row for row in matched if row.pass_check is not None]
        passed = [row for row in comparable if row.pass_check]
        failed = [row for row in comparable if row.pass_check is False]
        max_rel = max((row.rel_error for row in matched if row.rel_error is not None), default=None)
        if failed:
            conclusion = case_value('L3270C25')
        elif any((row.status == case_value('L3271C31') for row in matched)):
            conclusion = case_value('L3272C25')
        else:
            conclusion = case_value('L3274C25')
        lines.append(case_value('L3276C12') + case_value('L3277C14').join([doc_name, case_value('L3280C20').join(modules), str(len(matched)), str(len(comparable)), str(len(passed)), str(len(failed)), fmt_percent(max_rel), conclusion]) + case_value('L3289C14'))
    lines.extend([case_value('L3294C12'), case_value('L3295C12'), case_value('L3296C12'), case_value('L3297C12'), case_value('L3298C12'), case_value('L3299C12'), case_value('L3300C12'), case_value('L3301C12'), case_value('L3302C12'), case_value('L3303C12'), case_value('L3304C12'), case_value('L3305C12'), case_value('L3306C12'), case_value('L3307C12'), case_value('L3308C12'), *failed_category_lines(summary), case_value('L3310C12'), case_value('L3311C12'), case_value('L3312C12')])
    review_rows = [row for row in rows if row.pass_check is False or row.status == case_value('L3315C83')]
    if not review_rows:
        lines.append(case_value('L3317C21'))
    else:
        lines.extend([case_value('L3321C16'), case_value('L3322C16')])
        for row in review_rows:
            lines.append(case_value('L3327C16') + case_value('L3328C18').join([md_cell(row.module), md_cell(row.item), fmt_float(row.value), md_cell(row.unit), md_cell(row.document_value_raw), fmt_float(row.abs_error), md_cell(row.status), md_cell(row.note)]) + case_value('L3340C18'))
    lines.extend([case_value('L3345C12'), case_value('L3346C12'), case_value('L3347C12'), case_value('L3348C12'), case_value('L3349C12'), case_value('L3350C12')])
    (OUT / case_value('L3353C11')).write_text(case_value('L3353C62').join(lines) + case_value('L3353C81'), encoding=case_value('L3353C96'))


@require_case_profile.guard
def write_supplement3_inclusion_report(summary: dict[str, Any]) -> None:
    lines = [case_value('L3358C8'), case_value('L3359C8'), case_value('L3360C8'), case_value('L3361C8'), case_value('L3362C8'), case_value('L3363C8'), case_value('L3364C8'), case_value('L3365C8'), case_value('L3366C8'), case_value('L3367C8'), case_value('L3368C8'), case_value('L3369C8'), case_value('L3370C8'), f"{case_value('L3371C10')}{summary[case_value('L3371C51')]}{case_value('L3371C65')}{summary[case_value('L3371C94')]}{case_value('L3371C113')}{summary[case_value('L3371C153')]}{case_value('L3371C168')}{summary[case_value('L3371C190')]}{case_value('L3371C205')}", case_value('L3372C8'), case_value('L3373C8'), case_value('L3374C8'), case_value('L3375C8'), case_value('L3376C8'), case_value('L3377C8'), case_value('L3378C8'), case_value('L3379C8'), case_value('L3380C8'), case_value('L3381C8'), case_value('L3382C8'), case_value('L3383C8'), case_value('L3384C8'), case_value('L3385C8'), case_value('L3386C8'), case_value('L3387C8'), case_value('L3388C8'), case_value('L3389C8'), case_value('L3390C8'), case_value('L3391C8'), case_value('L3392C8'), case_value('L3393C8'), case_value('L3394C8')]
    (OUT / case_value('L3396C11')).write_text(case_value('L3396C54').join(lines) + case_value('L3396C73'), encoding=case_value('L3396C88'))


@require_case_profile.guard
def write_mismatch_root_cause_report() -> None:
    low_220_k = case_value('L3400C16') + case_value('L3400C22')
    low_280_k = case_value('L3401C16') + case_value('L3401C22')
    high_k = case_value('L3402C13') + case_value('L3402C19')
    r_j_mol_k = case_value('L3403C16')
    k_low = {case_value('L3405C8'): source_k_to_aspen(case_value('L3405C32')), case_value('L3406C8'): source_k_to_aspen(case_value('L3406C32')), case_value('L3407C8'): source_k_to_aspen(case_value('L3407C32'))}
    k_high = {case_value('L3410C8'): source_k_to_aspen(case_value('L3410C32')), case_value('L3411C8'): source_k_to_aspen(case_value('L3411C32')), case_value('L3412C8'): source_k_to_aspen(case_value('L3412C32'))}
    doc_fit = {case_value('L3415C8'): (case_value('L3415C15'), case_value('L3415C24')), case_value('L3416C8'): (case_value('L3416C15'), case_value('L3416C23')), case_value('L3417C8'): (case_value('L3417C15'), case_value('L3417C24'))}
    pump_failed = [(case_value('L3420C9'), case_value('L3420C21'), case_value('L3420C31')), (case_value('L3421C9'), case_value('L3421C21'), case_value('L3421C30')), (case_value('L3422C9'), case_value('L3422C21'), case_value('L3422C30')), (case_value('L3423C9'), case_value('L3423C21'), case_value('L3423C30')), (case_value('L3424C9'), case_value('L3424C21'), case_value('L3424C30')), (case_value('L3425C9'), case_value('L3425C21'), case_value('L3425C31')), (case_value('L3426C9'), case_value('L3426C21'), case_value('L3426C30')), (case_value('L3427C9'), case_value('L3427C21'), case_value('L3427C30')), (case_value('L3428C9'), case_value('L3428C21'), case_value('L3428C30')), (case_value('L3429C9'), case_value('L3429C21'), case_value('L3429C30')), (case_value('L3430C9'), case_value('L3430C21'), case_value('L3430C30')), (case_value('L3431C9'), case_value('L3431C21'), case_value('L3431C30')), (case_value('L3432C9'), case_value('L3432C21'), case_value('L3432C30')), (case_value('L3433C9'), case_value('L3433C21'), case_value('L3433C30'))]
    lines = [case_value('L3437C8'), case_value('L3438C8'), case_value('L3439C8'), case_value('L3440C8'), case_value('L3441C8'), case_value('L3442C8'), case_value('L3443C8'), case_value('L3444C8'), case_value('L3445C8'), case_value('L3446C8'), case_value('L3447C8'), case_value('L3448C8'), case_value('L3449C8'), case_value('L3450C8'), case_value('L3451C8'), case_value('L3452C8'), case_value('L3453C8'), case_value('L3454C8'), case_value('L3455C8'), case_value('L3456C8'), case_value('L3457C8'), case_value('L3458C8'), case_value('L3459C8'), case_value('L3460C8'), case_value('L3461C8'), case_value('L3462C8'), f"{case_value('L3463C10')}{fmt_float(low_220_k)}{case_value('L3463C105')}", f"{case_value('L3464C10')}{fmt_float(low_280_k)}{case_value('L3464C109')}", f"{case_value('L3465C10')}{fmt_float(high_k)}{case_value('L3465C89')}", f"{case_value('L3466C10')}{fmt_float(case_value('L3466C68') / (r_j_mol_k * low_280_k))}{case_value('L3466C93')}", f"{case_value('L3467C10')}{fmt_float(case_value('L3467C70') / (r_j_mol_k * low_220_k))}{case_value('L3467C95')}", case_value('L3468C8'), case_value('L3469C8'), case_value('L3470C8'), case_value('L3471C8'), case_value('L3472C8'), case_value('L3473C8'), case_value('L3474C8')]
    for low_c, t_low in [(case_value('L3476C26'), low_220_k), (case_value('L3476C44'), low_280_k)]:
        for key in (case_value('L3477C20'), case_value('L3477C26'), case_value('L3477C32')):
            a_fit, e_fit = arrhenius_from_two_points(t_low, k_low[key], high_k, k_high[key])
            doc_a, doc_e = doc_fit[key]
            a_rel = (a_fit - doc_a) / doc_a
            e_rel = (e_fit - doc_e) / doc_e
            lines.append(case_value('L3483C16') + case_value('L3484C18').join([f"{low_c}{case_value('L3486C33')}", key, fmt_float(a_fit), fmt_float(doc_a), fmt_percent(a_rel), fmt_float(e_fit), fmt_float(doc_e), fmt_percent(e_rel)]) + case_value('L3496C18'))
    lines.extend([case_value('L3501C12'), case_value('L3502C12'), case_value('L3503C12'), case_value('L3504C12'), case_value('L3505C12'), case_value('L3506C12'), case_value('L3507C12'), case_value('L3508C12'), case_value('L3509C12'), case_value('L3510C12'), case_value('L3511C12'), case_value('L3512C12'), case_value('L3513C12'), case_value('L3514C12'), case_value('L3515C12'), case_value('L3516C12'), case_value('L3517C12'), case_value('L3518C12'), case_value('L3519C12'), case_value('L3520C12'), case_value('L3521C12'), case_value('L3522C12'), case_value('L3523C12')])
    for tag, rho, inputs in pump_failed:
        lines.append(f"{case_value('L3527C23')}{tag}{case_value('L3527C30')}{rho:{case_value('L3527C38')}}{case_value('L3527C42')}{inputs}{case_value('L3527C53')}")
    lines.extend([case_value('L3530C12'), case_value('L3531C12'), case_value('L3532C12'), case_value('L3533C12'), case_value('L3534C12'), case_value('L3535C12')])
    (OUT / case_value('L3538C11')).write_text(case_value('L3538C53').join(lines) + case_value('L3538C72'), encoding=case_value('L3538C87'))


@require_case_profile.guard
def write_generalization_decision_report(summary: dict[str, Any]) -> None:
    lines = [case_value('L3543C8'), case_value('L3544C8'), case_value('L3545C8'), case_value('L3546C8'), case_value('L3547C8'), case_value('L3548C8'), case_value('L3549C8'), case_value('L3550C8'), case_value('L3551C8'), case_value('L3552C8'), f"{case_value('L3553C10')}{summary[case_value('L3553C44')]}{case_value('L3553C58')}{summary[case_value('L3553C81')]}{case_value('L3553C100')}{summary[case_value('L3553C140')]}{case_value('L3553C155')}{summary[case_value('L3553C177')]}{case_value('L3553C192')}", case_value('L3554C8'), case_value('L3555C8'), case_value('L3556C8'), case_value('L3557C8'), case_value('L3558C8'), case_value('L3559C8'), case_value('L3560C8'), case_value('L3561C8'), case_value('L3562C8'), case_value('L3563C8'), case_value('L3564C8'), case_value('L3565C8'), case_value('L3566C8'), case_value('L3567C8'), case_value('L3568C8'), case_value('L3569C8'), case_value('L3570C8'), case_value('L3571C8'), case_value('L3572C8'), case_value('L3573C8'), case_value('L3574C8'), case_value('L3575C8'), case_value('L3576C8'), case_value('L3577C8'), case_value('L3578C8'), case_value('L3579C8'), case_value('L3580C8'), case_value('L3581C8'), case_value('L3582C8'), case_value('L3583C8'), case_value('L3584C8'), case_value('L3585C8'), case_value('L3586C8'), case_value('L3587C8'), case_value('L3588C8'), case_value('L3589C8'), case_value('L3590C8'), case_value('L3591C8'), case_value('L3592C8'), case_value('L3593C8'), case_value('L3594C8'), case_value('L3595C8'), case_value('L3596C8'), case_value('L3597C8'), case_value('L3598C8'), case_value('L3599C8'), case_value('L3600C8'), case_value('L3601C8'), case_value('L3602C8'), case_value('L3603C8'), case_value('L3604C8'), case_value('L3605C8'), case_value('L3606C8'), case_value('L3607C8'), case_value('L3608C8'), case_value('L3609C8'), case_value('L3610C8'), case_value('L3611C8'), case_value('L3612C8'), case_value('L3613C8')]
    (OUT / case_value('L3615C11')).write_text(case_value('L3615C62').join(lines) + case_value('L3615C81'), encoding=case_value('L3615C96'))


@require_case_profile.guard
def write_late_chapter_parameter_ledger() -> None:
    rows = build_late_chapter_parameter_ledger()
    payload = [asdict(row) for row in rows]
    (DATA / case_value('L3621C12')).write_text(json.dumps(payload, ensure_ascii=False, indent=case_value('L3622C55')), encoding=case_value('L3622C68'))
    csv_path = DATA / case_value('L3624C22')
    with csv_path.open(case_value('L3625C23'), encoding=case_value('L3625C37'), newline=case_value('L3625C58')) as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(rows[case_value('L3626C63')]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))
    by_chapter: dict[str, int] = {}
    by_action: dict[str, int] = {}
    by_evidence: dict[str, int] = {}
    for row in rows:
        by_chapter[row.chapter] = by_chapter.get(row.chapter, case_value('L3635C62')) + case_value('L3635C67')
        by_action[row.action] = by_action.get(row.action, case_value('L3636C58')) + case_value('L3636C63')
        by_evidence[row.evidence_class] = by_evidence.get(row.evidence_class, case_value('L3637C78')) + case_value('L3637C83')
    lines = [case_value('L3640C8'), case_value('L3641C8'), case_value('L3642C8'), case_value('L3643C8'), f"{case_value('L3644C10')}{len(rows)}", f"{case_value('L3645C10')}", f"{case_value('L3646C10')}", case_value('L3647C8'), case_value('L3648C8'), case_value('L3649C8'), case_value('L3650C8'), case_value('L3651C8')]
    for chapter, count in sorted(by_chapter.items()):
        lines.append(f"{case_value('L3654C23')}{chapter}{case_value('L3654C34')}{count}{case_value('L3654C44')}")
    lines.extend([case_value('L3655C18'), case_value('L3655C22'), case_value('L3655C50'), case_value('L3655C54'), case_value('L3655C83')])
    for action, count in sorted(by_action.items()):
        lines.append(f"{case_value('L3657C23')}{action}{case_value('L3657C33')}{count}{case_value('L3657C43')}")
    lines.extend([case_value('L3658C18'), case_value('L3658C22'), case_value('L3658C50'), case_value('L3658C54'), case_value('L3658C83')])
    for evidence, count in sorted(by_evidence.items()):
        lines.append(f"{case_value('L3660C23')}{evidence}{case_value('L3660C35')}{count}{case_value('L3660C45')}")
    lines.extend([case_value('L3664C12'), case_value('L3665C12'), case_value('L3666C12'), case_value('L3667C12'), case_value('L3668C12'), case_value('L3669C12'), case_value('L3670C12'), case_value('L3671C12'), case_value('L3672C12'), case_value('L3673C12')])
    lines.extend([case_value('L3679C12'), case_value('L3680C12'), case_value('L3681C12'), case_value('L3682C12'), case_value('L3683C12')])
    for row in rows:
        lines.append(case_value('L3688C12') + case_value('L3689C14').join([md_cell(row.chapter), md_cell(row.equipment_family), md_cell(row.object_id), md_cell(row.parameter), md_cell(row.value), md_cell(row.unit), md_cell(f"{row.source_document}{case_value('L3697C51')}{row.source_table}"), md_cell(row.source_type), md_cell(row.evidence_class), md_cell(row.action), md_cell(row.judgment_links), md_cell(row.scriptable_formula), md_cell(row.note)]) + case_value('L3706C14'))
    (OUT / case_value('L3708C11')).write_text(case_value('L3708C62').join(lines) + case_value('L3708C81'), encoding=case_value('L3708C96'))


@require_case_profile.guard
def write_late_chapter_coverage_report() -> None:
    rows = build_late_chapter_parameter_ledger()
    chapter_counts: dict[str, int] = {}
    for row in rows:
        chapter_counts[row.chapter] = chapter_counts.get(row.chapter, case_value('L3715C70')) + case_value('L3715C75')
    lines = [case_value('L3717C8'), case_value('L3718C8'), case_value('L3719C8'), case_value('L3720C8'), case_value('L3721C8'), case_value('L3722C8'), case_value('L3723C8'), case_value('L3724C8'), case_value('L3725C8'), case_value('L3726C8'), case_value('L3727C8'), case_value('L3728C8'), f"{case_value('L3729C10')}{chapter_counts.get(case_value('L3729C66'), case_value('L3729C95'))}{case_value('L3729C98')}", f"{case_value('L3730C10')}{chapter_counts.get(case_value('L3730C60'), case_value('L3730C83'))}{case_value('L3730C86')}", f"{case_value('L3731C10')}{chapter_counts.get(case_value('L3731C71'), case_value('L3731C111'))}{case_value('L3731C114')}", f"{case_value('L3732C10')}{chapter_counts.get(case_value('L3732C58'), case_value('L3732C85'))}{case_value('L3732C88')}", f"{case_value('L3733C10')}{chapter_counts.get(case_value('L3733C65'), case_value('L3733C82')) + chapter_counts.get(case_value('L3733C106'), case_value('L3733C140'))}{case_value('L3733C143')}", case_value('L3734C8'), case_value('L3735C8'), case_value('L3736C8'), case_value('L3737C8'), case_value('L3738C8'), case_value('L3739C8'), case_value('L3740C8'), case_value('L3741C8'), case_value('L3742C8'), case_value('L3743C8'), case_value('L3744C8'), case_value('L3745C8'), case_value('L3746C8'), case_value('L3747C8'), case_value('L3748C8'), case_value('L3749C8'), case_value('L3750C8')]
    (OUT / case_value('L3752C11')).write_text(case_value('L3752C62').join(lines) + case_value('L3752C81'), encoding=case_value('L3752C96'))


@require_case_profile.guard
def write_outputs(rows: list[CalcRow]) -> None:
    OUT.mkdir(exist_ok=True)
    DATA.mkdir(exist_ok=True)
    summary = summarize(rows)
    write_calculation_outputs(rows, summary)
    write_module_report()
    write_aspen_report()
    write_reliability_report(rows, summary)
    write_boundary_report()
    write_script_manual(summary)
    write_section_precision_report(rows, summary)
    write_section_parameter_source_report()
    write_manual_parameter_report()
    write_device_mapping_report()
    write_audit_gap_report(rows, summary)
    write_formula_reliability_report(rows, summary)
    write_supplement3_inclusion_report(summary)
    write_mismatch_root_cause_report()
    write_generalization_decision_report(summary)
    write_late_chapter_parameter_ledger()
    write_late_chapter_coverage_report()


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description='Original document audit with explicit user-owned case inputs.')
    parser.add_argument('--case-profile', type=Path)
    parser.add_argument('--case-profile-sha256')
    parser.add_argument('--source-root', type=Path)
    parser.add_argument('--output-root', type=Path)
    args = parser.parse_args()
    try:
        profile = configure_case_profile(args.case_profile, args.case_profile_sha256, args.source_root, args.output_root)
    except (OSError, ValueError) as exc:
        print(json.dumps({'status': 'dependency_unavailable', 'reason': str(exc), 'outputs_created': False}))
        raise SystemExit(2)
    global ROOT, OUT, DATA
    ROOT, OUT, DATA = profile.source_root, profile.output_root, profile.output_root / 'data'
    rows = build_calculations()
    write_outputs(rows)
    summary = summarize(rows)
    print(f"wrote {summary['total_rows']} calculation rows")
    print(f"comparable={summary['comparable_rows']} passed={summary['passed_rows']} failed={summary['failed_rows']}")
    print(OUT / "计算脚本复算结果.md")
    print(OUT / "模块拆分与任务清单.md")
    print(OUT / "Aspen需提供参数清单.md")
    print(OUT / "计算可靠性证明.md")
    print(OUT / "选型可靠性边界清单.md")
    print(OUT / "完善脚本内容说明.md")
    print(OUT / "小节级计算精度表.md")
    print(OUT / "小节级参数来源表.md")
    print(OUT / "三文档计算式可靠性审计.md")
    print(OUT / "复核审计与缺漏清单.md")
    print(OUT / "设备位号映射表.md")
    print(OUT / "补充资料3纳入说明.md")
    print(OUT / "不匹配项根因审查.md")
    print(OUT / "泛化计算与人工判定规则.md")
    print(OUT / "第4-8章全量参数来源ledger.md")
    print(OUT / "知识图谱第4-8章覆盖说明.md")


if __name__ == "__main__":
    main()
