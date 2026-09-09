"""Original DSET and hydraulic algorithms; case configuration is explicit.

Label inference helpers are diagnostic only. This module never executes Aspen
and never validates a software hydraulic rating or full-flow delivery.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from packed_hydraulic_contract import (build_nozzles, cli, ensure_uniform_internals, profiles_tuple, read_verified_text)
R_GAS = 8.314462618

def parse_number(token: str) -> float:
    token = token.strip().replace('D', 'E').replace('d', 'E')
    if token in {'*', ''}:
        return math.nan
    if token.endswith('.'):
        token += '0'
    return float(token)

def extract_dset_values(text: str, block: str, dataset: str, item: str) -> list[float]:
    pattern = re.compile(f'DSET\\s+BLOCK\\s+RADFRAC\\s+{re.escape(block)}\\s+{re.escape(dataset)}\\s+{re.escape(item)}\\s+\\(', re.S)
    match = pattern.search(text)
    if not match:
        raise RuntimeError(f'missing {block} {dataset} {item}')
    end = text.find(')', match.end())
    if end < 0:
        raise RuntimeError(f'unterminated {block} {dataset} {item}')
    body = re.sub('<[^>]+>', ' ', text[match.end():end])
    values: list[float] = []
    for token in re.findall('\\*|[-+]?(?:\\d+\\.\\d*|\\.\\d+|\\d+)(?:[DdEe][-+]?\\d+)?', body):
        if token == '*':
            continue
        values.append(parse_number(token))
    return values

def extract_dset_map(text: str, block: str, dataset: str) -> dict[int, list[float]]:
    pattern = re.compile(f'DSET\\s+BLOCK\\s+RADFRAC\\s+{re.escape(block)}\\s+{re.escape(dataset)}\\s+@L_(\\d+)\\s+\\(', re.S)
    values_by_label: dict[int, list[float]] = {}
    for match in pattern.finditer(text):
        end = text.find(')', match.end())
        if end < 0:
            continue
        body = re.sub('<[^>]+>', ' ', text[match.end():end])
        values: list[float] = []
        for token in re.findall('\\*|[-+]?(?:\\d+\\.\\d*|\\.\\d+|\\d+)(?:[DdEe][-+]?\\d+)?', body):
            if token == '*':
                continue
            values.append(parse_number(token))
        values_by_label[int(match.group(1))] = values
    return values_by_label

def looks_like_temperature(values: list[float], nstage: int) -> bool:
    if len(values) < nstage:
        return False
    stage_values = values[:nstage]
    if not all((20.0 <= value <= 300.0 for value in stage_values)):
        return False
    increases = sum((1 for left, right in zip(stage_values, stage_values[1:]) if right >= left))
    return increases >= max(1, nstage - 3)

def infer_radfrac_profile_values(text: str, block: str, nstage: int) -> tuple[list[float], list[float], list[float], list[float], list[float], list[float], dict[str, str]]:
    pro2 = extract_dset_map(text, block, 'RAD_PRO2')
    pr2s = extract_dset_map(text, block, 'RAD_PR2S')
    temp_label = next((label for label in sorted(pro2) if looks_like_temperature(pro2[label], nstage)), None)
    if temp_label is None:
        raise RuntimeError(f'could not infer {block} RAD_PRO2 temperature profile')
    required = {'pressure_bar': (pro2, temp_label + 1), 'vapor_mole': (pro2, temp_label + 3), 'liquid_mole': (pro2, temp_label + 4), 'vapor_mass': (pr2s, temp_label + 15), 'liquid_mass': (pr2s, temp_label + 16)}
    missing = [name for name, (mapping, label) in required.items() if label not in mapping]
    if missing:
        raise RuntimeError(f"could not infer {block} profile columns after temperature label @L_{temp_label}: missing {', '.join(missing)}")
    labels = {'temperature': f'@L_{temp_label}', 'pressure': f'@L_{temp_label + 1}', 'vapor_mole': f'@L_{temp_label + 3}', 'liquid_mole': f'@L_{temp_label + 4}', 'vapor_mass': f'@L_{temp_label + 15}', 'liquid_mass': f'@L_{temp_label + 16}'}
    return (pro2[temp_label], pro2[temp_label + 1], pro2[temp_label + 3], pro2[temp_label + 4], pr2s[temp_label + 15], pr2s[temp_label + 16], labels)

def load_streams(path: Path) -> dict[str, dict[str, float | str]]:
    rows: dict[str, dict[str, float | str]] = {}
    with path.open('r', encoding='utf-8-sig', newline='') as handle:
        for row in csv.DictReader(handle):
            converted: dict[str, float | str] = {}
            for key, value in row.items():
                if value is None or value == '':
                    converted[key] = ''
                    continue
                try:
                    converted[key] = float(value)
                except ValueError:
                    converted[key] = value
            rows[str(row['stream'])] = converted
    return rows

def round_up(value: float, step: float) -> float:
    return math.ceil(value / step) * step

def split_section(name: str, stages: int, hetp_m: float, max_bed_height_m: float) -> list[dict[str, float | int | str]]:
    height = stages * hetp_m
    bed_count = max(1, math.ceil(height / max_bed_height_m))
    bed_height = height / bed_count
    return [{'section': name, 'bed_no': idx + 1, 'theoretical_stages': stages / bed_count, 'packing_height_m': bed_height} for idx in range(bed_count)]

def stream_nozzle_liquid(stream: dict[str, float | str], density_kg_m3: float, velocity_m_s: float) -> dict[str, float]:
    mass_kg_h = float(stream['total_mass_flow_kg_h'])
    q_m3_s = mass_kg_h / 3600.0 / density_kg_m3
    area_m2 = q_m3_s / velocity_m_s
    diameter_m = math.sqrt(4.0 * area_m2 / math.pi)
    return {'volumetric_flow_m3_s': q_m3_s, 'velocity_m_s': velocity_m_s, 'diameter_m': diameter_m}

def stream_nozzle_vapor(stream: dict[str, float | str], velocity_m_s: float) -> dict[str, float]:
    temp_c = float(stream['temp_C'])
    pressure_bar = float(stream['pressure_bar'])
    mass_kg_h = float(stream['total_mass_flow_kg_h'])
    mole_kmol_h = float(stream['total_mole_flow_kmol_h'])
    mw_kg_kmol = mass_kg_h / mole_kmol_h
    rho = pressure_bar * 100000.0 * (mw_kg_kmol / 1000.0) / (R_GAS * (temp_c + 273.15))
    q_m3_s = mass_kg_h / 3600.0 / rho
    area_m2 = q_m3_s / velocity_m_s
    diameter_m = math.sqrt(4.0 * area_m2 / math.pi)
    return {'mw_kg_kmol': mw_kg_kmol, 'density_kg_m3': rho, 'volumetric_flow_m3_s': q_m3_s, 'velocity_m_s': velocity_m_s, 'diameter_m': diameter_m}

def build_design(args: argparse.Namespace) -> dict[str, object]:
    text = read_verified_text(Path(args.bkp), args.bkp_encoding)
    streams = load_streams(Path(args.streams))
    temp_c, pressure_bar, vapor_mole, liquid_mole, vapor_mass, liquid_mass, profile_labels = profiles_tuple(args.validated_profile_values, args)
    profile_source = 'explicit_source_bound_DSET_labels'
    available = min(len(temp_c), len(pressure_bar), len(vapor_mole), len(liquid_mole), len(vapor_mass), len(liquid_mass))
    if available < args.nstage:
        raise RuntimeError(f'expected at least {args.nstage} RadFrac stages, got {available}')
    n = args.nstage
    target_f_factor = args.flooding_f_factor * args.capacity_factor_target
    stage_rows: list[dict[str, float | int]] = []
    for idx in range(n):
        mw = vapor_mass[idx] / vapor_mole[idx] if vapor_mole[idx] > 0 else math.nan
        rho_v = pressure_bar[idx] * 100000.0 * (mw / 1000.0) / (R_GAS * (temp_c[idx] + 273.15)) if vapor_mole[idx] > 0 else math.nan
        qv = vapor_mass[idx] / 3600.0 / rho_v if rho_v > 0 else math.nan
        u_design = target_f_factor / math.sqrt(rho_v) if rho_v > 0 else math.nan
        area_req = qv / u_design if u_design > 0 else math.nan
        diameter_req = math.sqrt(4.0 * area_req / math.pi) if area_req > 0 else math.nan
        stage_rows.append({'stage': idx + 1, 'temp_C': temp_c[idx], 'pressure_bar': pressure_bar[idx], 'vapor_mole_kmol_h': vapor_mole[idx], 'liquid_mole_kmol_h': liquid_mole[idx], 'vapor_mass_kg_h': vapor_mass[idx], 'liquid_mass_kg_h': liquid_mass[idx], 'vapor_mw_kg_kmol': mw, 'vapor_density_kg_m3': rho_v, 'vapor_volumetric_flow_m3_s': qv, 'required_diameter_m_at_target_capacity': diameter_req})
    controlling = max(stage_rows, key=lambda row: float(row['required_diameter_m_at_target_capacity']))
    selected_diameter = round_up(float(controlling['required_diameter_m_at_target_capacity']), args.diameter_round_step_m)
    selected_area = math.pi * selected_diameter ** 2 / 4.0
    for row in stage_rows:
        rho_v = float(row['vapor_density_kg_m3'])
        qv = float(row['vapor_volumetric_flow_m3_s'])
        actual_u = qv / selected_area
        actual_f = actual_u * math.sqrt(rho_v)
        row['selected_diameter_m'] = selected_diameter
        row['actual_superficial_vapor_velocity_m_s'] = actual_u
        row['actual_f_factor'] = actual_f
        row['actual_capacity_factor_fraction'] = actual_f / args.flooding_f_factor
    packed_stage_rows = [row for row in stage_rows if 2 <= int(row['stage']) <= args.nstage - 1]
    max_capacity = max(packed_stage_rows, key=lambda row: float(row['actual_capacity_factor_fraction']))
    min_capacity = min(packed_stage_rows, key=lambda row: float(row['actual_capacity_factor_fraction']))
    top_stages = args.feed_stage - 2
    bottom_stages = args.nstage - args.feed_stage
    beds = []
    if args.hetp_m is not None and args.max_bed_height_m is not None:
        beds = split_section('rectifying_above_feed', top_stages, args.hetp_m, args.max_bed_height_m)
        beds += split_section('stripping_below_feed', bottom_stages, args.hetp_m, args.max_bed_height_m)
    for bed in beds:
        bed['height_to_diameter'] = float(bed['packing_height_m']) / selected_diameter
        bed['segment_height_gate'] = 'PASS' if float(bed['packing_height_m']) <= args.max_bed_height_m else 'FAIL'
    liquid_density = args.liquid_density_kg_m3
    nozzles = build_nozzles(args, streams, stream_nozzle_liquid, stream_nozzle_vapor)
    return {'generated': datetime.now().isoformat(timespec='seconds'), 'source_bkp': str(Path(args.bkp)), 'source_streams': str(Path(args.streams)), 'tower': {'tag': args.tower_config.get('tag', args.block), 'aspen_block': args.block, 'nstage': args.nstage, 'feed_stage': args.feed_stage, 'service': args.tower_config.get('service')}, 'profile_extraction': {'source': profile_source, 'labels': profile_labels}, 'taskbook_constraints': {'capacity_factor_required_range': [args.capacity_factor_min, args.capacity_factor_max], 'max_bed_height_m': args.max_bed_height_m, 'source': args.config.get('parameters')}, 'design_assumptions': {'classification': 'preliminary course-design sizing; Column Internals/vendor evidence boundary remains open', 'packing_type': args.packing_type, 'hetp_m': args.hetp_m, 'effective_theoretical_stages_excluding_condenser_and_reboiler': top_stages + bottom_stages, 'flooding_f_factor': args.flooding_f_factor, 'target_capacity_factor_fraction': args.capacity_factor_target}, 'hydraulic_sizing': {'target_operating_f_factor': target_f_factor, 'controlling_stage_at_target_capacity': controlling, 'selected_inside_diameter_m': selected_diameter, 'selected_area_m2': selected_area, 'max_actual_capacity_factor': max_capacity, 'min_actual_capacity_factor': min_capacity, 'capacity_factor_gate': 'PASS' if args.capacity_factor_min <= float(max_capacity['actual_capacity_factor_fraction']) <= args.capacity_factor_max and args.capacity_factor_min <= float(min_capacity['actual_capacity_factor_fraction']) <= args.capacity_factor_max else 'REVIEW'}, 'packing_beds': beds, 'nozzle_predesign': nozzles, 'stage_profile': stage_rows}

def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

def read_text(path: Path) -> str:
    return read_verified_text(path)

def main() -> int:
    return cli(sys.modules[__name__], 'single')

if __name__ == '__main__':
    raise SystemExit(main())
