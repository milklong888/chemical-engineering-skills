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

from radfrac_packed_hydraulic_from_bkp import extract_dset_values

def parse_number(token: str) -> float:
    token = token.strip().replace('D', 'E').replace('d', 'E')
    if token.endswith('.'):
        token += '0'
    return float(token)

def extract_dset_map(text: str, block: str, dataset: str) -> dict[int, list[float]]:
    pattern = re.compile(f'DSET\\s+BLOCK\\s+RADFRAC\\s+{re.escape(block)}\\s+{re.escape(dataset)}\\s+@L_(\\d+)\\s+\\(', re.S)
    values_by_label: dict[int, list[float]] = {}
    for match in pattern.finditer(text):
        end = text.find(')', match.end())
        if end < 0:
            continue
        body = re.sub('<[^>]+>', ' ', text[match.end():end])
        values: list[float] = []
        for token in re.findall('[-+]?(?:\\d+\\.\\d*|\\.\\d+|\\d+)(?:[DdEe][-+]?\\d+)?', body):
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

def infer_profile(text: str, block: str, nstage: int) -> tuple[int, list[float], list[float], list[float], list[float], list[float], list[float]]:
    pro2 = extract_dset_map(text, block, 'RAD_PRO2')
    pr2s = extract_dset_map(text, block, 'RAD_PR2S')
    temp_label = next((label for label in sorted(pro2) if looks_like_temperature(pro2[label], nstage)), None)
    if temp_label is None:
        raise RuntimeError(f'could not infer {block} temperature profile')
    required = {'pressure_bar': (pro2, temp_label + 1), 'vapor_mole': (pro2, temp_label + 3), 'liquid_mole': (pro2, temp_label + 4), 'vapor_mass': (pr2s, temp_label + 15), 'liquid_mass': (pr2s, temp_label + 16)}
    missing = [name for name, (mapping, label) in required.items() if label not in mapping]
    if missing:
        raise RuntimeError(f'could not infer {block} profile after @L_{temp_label}: missing {missing}')
    return (temp_label, pro2[temp_label], pro2[temp_label + 1], pro2[temp_label + 3], pro2[temp_label + 4], pr2s[temp_label + 15], pr2s[temp_label + 16])

def block_body(inp_text: str, block: str) -> str:
    match = re.search(f'^\\s*BLOCK\\s+{re.escape(block)}\\s+RADFRAC\\b(?P<body>.*?)(?=^\\s*BLOCK\\b|\\Z)', inp_text, re.I | re.M | re.S)
    if not match:
        raise RuntimeError(f'missing {block} RadFrac body')
    return match.group('body')

def parse_internals(inp_text: str, block: str) -> list[dict[str, Any]]:
    body = block_body(inp_text, block)
    pattern = re.compile('INTERNALS\\s+(?P<section>\\S+)\\s+STAGE1=(?P<stage1>\\d+)\\s+STAGE2=(?P<stage2>\\d+).*?DIAM=(?P<diam>[0-9.]+).*?PACK-SIZE=\\"(?P<size>[^\\"]+)\\"\\s+PACK-HT=(?P<height>[0-9.]+)', re.I | re.S)
    rows: list[dict[str, Any]] = []
    for match in pattern.finditer(body):
        height = float(match.group('height'))
        diameter = float(match.group('diam'))
        rows.append({'section': match.group('section'), 'stage1': int(match.group('stage1')), 'stage2': int(match.group('stage2')), 'diameter_m': diameter, 'pack_size': match.group('size'), 'packing_height_m': height, 'height_to_diameter': height / diameter if diameter else None})
    if not rows:
        raise RuntimeError(f'missing internals rows in {block}')
    return rows

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

def nozzle_liquid(stream: dict[str, float | str], density_kg_m3: float, velocity_m_s: float) -> dict[str, float]:
    mass_kg_h = float(stream['total_mass_flow_kg_h'])
    q_m3_s = mass_kg_h / 3600.0 / density_kg_m3
    area_m2 = q_m3_s / velocity_m_s
    return {'volumetric_flow_m3_s': q_m3_s, 'velocity_m_s': velocity_m_s, 'diameter_m': math.sqrt(4.0 * area_m2 / math.pi)}

def nozzle_vapor(stream: dict[str, float | str], velocity_m_s: float) -> dict[str, float]:
    temp_c = float(stream['temp_C'])
    pressure_bar = float(stream['pressure_bar'])
    mass_kg_h = float(stream['total_mass_flow_kg_h'])
    mole_kmol_h = float(stream['total_mole_flow_kmol_h'])
    mw_kg_kmol = mass_kg_h / mole_kmol_h
    density = pressure_bar * 100000.0 * (mw_kg_kmol / 1000.0) / (R_GAS * (temp_c + 273.15))
    q_m3_s = mass_kg_h / 3600.0 / density
    area_m2 = q_m3_s / velocity_m_s
    return {'mw_kg_kmol': mw_kg_kmol, 'density_kg_m3': density, 'volumetric_flow_m3_s': q_m3_s, 'velocity_m_s': velocity_m_s, 'diameter_m': math.sqrt(4.0 * area_m2 / math.pi)}

def build_block_design(bkp_text: str, inp_text: str, streams: dict[str, dict[str, float | str]], block: str, args: argparse.Namespace) -> dict[str, Any]:
    temp_c, pressure_bar, vapor_mole, liquid_mole, vapor_mass, liquid_mass, profile_labels = profiles_tuple(args.validated_profile_values, args)
    temp_label = profile_labels['temperature']
    internals = ensure_uniform_internals(parse_internals(inp_text, block), args)
    selected_diameter = float(internals[0]['diameter_m'])
    selected_area = math.pi * selected_diameter ** 2 / 4.0
    stage_rows: list[dict[str, Any]] = []
    for idx in range(args.nstage):
        mw = vapor_mass[idx] / vapor_mole[idx] if vapor_mole[idx] > 0 else math.nan
        rho_v = pressure_bar[idx] * 100000.0 * (mw / 1000.0) / (R_GAS * (temp_c[idx] + 273.15)) if vapor_mole[idx] > 0 else math.nan
        qv = vapor_mass[idx] / 3600.0 / rho_v if rho_v > 0 else math.nan
        u = qv / selected_area if selected_area > 0 else math.nan
        f_factor = u * math.sqrt(rho_v) if rho_v > 0 else math.nan
        stage_rows.append({'block': block, 'stage': idx + 1, 'temp_C': temp_c[idx], 'pressure_bar': pressure_bar[idx], 'vapor_mole_kmol_h': vapor_mole[idx], 'liquid_mole_kmol_h': liquid_mole[idx], 'vapor_mass_kg_h': vapor_mass[idx], 'liquid_mass_kg_h': liquid_mass[idx], 'vapor_mw_kg_kmol': mw, 'vapor_density_kg_m3': rho_v, 'vapor_volumetric_flow_m3_s': qv, 'selected_diameter_m': selected_diameter, 'superficial_vapor_velocity_m_s': u, 'actual_f_factor': f_factor, 'actual_capacity_factor_fraction': f_factor / args.flooding_f_factor if args.flooding_f_factor else math.nan})
    packed_rows = [row for row in stage_rows if 2 <= int(row['stage']) <= args.nstage - 1]
    max_capacity = max(packed_rows, key=lambda row: float(row['actual_capacity_factor_fraction']))
    min_capacity = min(packed_rows, key=lambda row: float(row['actual_capacity_factor_fraction']))
    max_height = max((float(row['packing_height_m']) for row in internals))
    return {'block': block, 'profile_temperature_label': temp_label, 'selected_diameter_m': selected_diameter, 'selected_area_m2': selected_area, 'internals': internals, 'height_gate_source': 'UNKNOWN' if args.max_bed_height_m is None else 'PASS' if max_height <= args.max_bed_height_m else 'FAIL', 'max_packing_height_m': max_height, 'max_actual_capacity_factor': max_capacity, 'min_actual_capacity_factor': min_capacity, 'capacity_factor_gate': 'PASS' if args.capacity_factor_min <= float(min_capacity['actual_capacity_factor_fraction']) <= args.capacity_factor_max and args.capacity_factor_min <= float(max_capacity['actual_capacity_factor_fraction']) <= args.capacity_factor_max else 'FAIL', 'stage_profile': stage_rows, 'nozzles': build_nozzles(args, streams, nozzle_liquid, nozzle_vapor)}

def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

def read_text(path: Path) -> str:
    return read_verified_text(path)

def main() -> int:
    return cli(sys.modules[__name__], 'parallel')

if __name__ == '__main__':
    raise SystemExit(main())
