"""Read-only engineering diagnostics. No defaults grant engineering acceptance.

CLI: python engineering_checks.py TOOL --input request.json
Use --input - for UTF-8 JSON stdin. Four public functions take one JSON object.
Canonical units are explicit; unsupported units/bases remain unverified.
Tests use synthetic data only, never engineering evidence.
"""
from __future__ import annotations

import argparse
from collections import Counter
from functools import wraps
import hashlib
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


def finite(value, *, minimum=None, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(value) and (minimum is None or value >= minimum) and (not positive or value > 0)


def source_ok(source):
    """Caller metadata completeness/currentness only; not source authenticity."""
    return (isinstance(source, dict)
            and all(isinstance(source.get(k), str) and source[k].strip() for k in ('id', 'locator', 'revision'))
            and ('stale' not in source or isinstance(source['stale'], bool) and source['stale'] is False)
            and ('current_revision' not in source
                 or isinstance(source['current_revision'], str) and bool(source['current_revision'].strip())
                 and source['revision'] == source['current_revision']))


def valid_id(value):
    """JSON identity: integer or nonblank string; never bool/float/coercion."""
    return (isinstance(value, int) and not isinstance(value, bool)
            or isinstance(value, str) and bool(value.strip()))


class Checks:
    def __init__(self, tool):
        self.tool, self.items = tool, []

    def add(self, name, outcome=None, **detail):
        self.items.append(dict(check=name, status='unverified' if outcome is None else ('pass' if outcome else 'fail'), **detail))

    def result(self, **detail):
        states = {item['status'] for item in self.items}
        status = 'fail' if 'fail' in states else ('unverified' if 'unverified' in states or not states else 'pass')
        return dict(tool=self.tool, diagnostic_status=status, engineering_acceptance='not_assessed',
                    native_calculation_acceptance='not_assessed', checks=self.items, **detail)


def _shape_errors(value, shape, path='request'):
    if isinstance(shape, dict):
        if not isinstance(value, dict):
            return [path + ' must be a JSON object']
        return [error for key, child in shape.items() if key in value
                for error in _shape_errors(value[key], child, path+'.'+key)]
    if not isinstance(value, list):
        return [path + ' must be a JSON array']
    return [error for index, item in enumerate(value)
            for error in _shape_errors(item, shape[0], f'{path}[{index}]')] if shape else []


def _safe_request(shape):
    """Keep malformed nested JSON diagnostic-only across Python, CLI and MCP."""
    def decorate(function):
        @wraps(function)
        def checked(request: dict):
            errors = _shape_errors(request, shape)
            if errors:
                result = Checks(function.__name__)
                result.add('invalid_request', None, reasons=errors)
                return result.result()
            try:
                return function(request)
            except (ValueError, TypeError, KeyError, AttributeError, OverflowError, SyntaxError) as exc:
                result = Checks(function.__name__)
                result.add('invalid_request', None, reason=f'{type(exc).__name__}: {exc}')
                return result.result()
        return checked
    return decorate


_ENDPOINT_SHAPE = {'source': {}}
_SIDE_SHAPE = {'source': {}, 'reynolds_endpoints': {'inlet': _ENDPOINT_SHAPE, 'outlet': _ENDPOINT_SHAPE}}


@_safe_request({'flow_source': {}, 'velocity_bounds_m_s': {'source': {}}, 'catalog': [{'source': {}}]})
def screen_pipe_candidates(request: dict):
    """Screen caller catalog rows at Q/A. No catalog, nominal-size inference or roundup."""
    c = Checks('screen_pipe_candidates')
    q, bounds = request.get('volumetric_flow_m3_s'), request.get('velocity_bounds_m_s', {})
    lo, hi = bounds.get('min'), bounds.get('max')
    flow_ok = finite(q, minimum=0) and request.get('flow_unit') == 'm3/s' and source_ok(request.get('flow_source'))
    bound_ok = finite(lo, minimum=0) and finite(hi, positive=True) and lo <= hi and source_ok(bounds.get('source'))
    c.add('flow_basis', True if flow_ok else None)
    c.add('velocity_authority', True if bound_ok else None)
    rows = request.get('catalog', [])
    c.add('catalog_present', True if isinstance(rows, list) and rows else None)
    row_ids = [row.get('id') for row in rows]
    id_counts = Counter(value for value in row_ids if valid_id(value))
    c.add('catalog_identity', len(id_counts) == len(rows) if rows and all(valid_id(v) for v in row_ids) else None,
          duplicate_ids=[value for value, count in id_counts.items() if count > 1])
    results = []
    for i, row in enumerate(rows if isinstance(rows, list) else []):
        r = Checks('pipe_row')
        od, wall = row.get('od_mm'), row.get('wall_mm')
        identity = row.get('id')
        r.add('catalog_id', True if valid_id(identity) else None)
        r.add('unique_catalog_id', id_counts[identity] == 1 if valid_id(identity) else None)
        r.add('catalog_source', True if source_ok(row.get('source')) else None)
        dims = finite(od, positive=True) and finite(wall, positive=True)
        r.add('dimensions', (od > 2 * wall) if dims else None)
        r.add('dimension_unit', True if row.get('dimension_unit') == 'mm' else None)
        diameter, velocity = None, None
        if dims and od > 2 * wall and row.get('dimension_unit') == 'mm':
            diameter = (od - 2 * wall) / 1000
            if finite(q, minimum=0) and request.get('flow_unit') == 'm3/s':
                area = (math.pi / 4) * diameter * diameter
                if finite(area, positive=True):
                    computed = q / area
                    velocity = computed if finite(computed, minimum=0) else None
        r.add('velocity_bounds', lo <= velocity <= hi if velocity is not None and bound_ok and flow_ok else None)
        result = r.result(index=i, catalog_id=row.get('id'), inner_diameter_m=diameter, velocity_m_s=velocity,
                          source=row.get('source'))
        results.append(result)
        c.add(f'row_{i}', None if result['diagnostic_status'] == 'unverified' else result['diagnostic_status'] == 'pass')
    # Infeasible rows are reported individually; they do not erase feasible alternatives.
    return c.result(candidates=results, feasible_candidate_ids=[r['catalog_id'] for r in results if r['diagnostic_status'] == 'pass'],
                    selection='caller_decision_required')


@_safe_request({'source': {}, 'hot': _SIDE_SHAPE, 'cold': _SIDE_SHAPE, 'area': {'source': {}},
                'acceptance_profile': {'source': {}, 'hot': _SIDE_SHAPE, 'cold': _SIDE_SHAPE, 'area': {}}})
def check_exchanger_basis(request: dict):
    """Check caller-authorized pressure, area and phase endpoint Re criteria."""
    c = Checks('check_exchanger_basis')
    profile = request.get('acceptance_profile', {})
    authority = source_ok(profile.get('source'))
    c.add('acceptance_profile_source', True if authority else None)
    c.add('same_equipment_basis', True if source_ok(request.get('source')) and valid_id(request.get('equipment_id'))
          and valid_id(request.get('basis_id')) and valid_id(profile.get('basis_id'))
          and request['basis_id'] == profile['basis_id'] else None)
    for side in ('hot', 'cold'):
        s, p = request.get(side, {}), profile.get(side, {})
        pin, pout, calc = s.get('pin_abs_pa'), s.get('pout_abs_pa'), s.get('calculated_dp_pa')
        valid = all(finite(v, positive=True) for v in (pin, pout))
        c.add(f'{side}.absolute_pressure', valid if all(finite(v) for v in (pin, pout)) else None)
        units = s.get('pressure_unit') == 'Pa' and s.get('pressure_basis') == 'absolute'
        c.add(f'{side}.pressure_units', True if units else None)
        c.add(f'{side}.side_source', True if source_ok(s.get('source')) else None)
        if valid and units:
            delta = pin - pout
            c.add(f'{side}.pressure_direction', delta >= 0, pin_minus_pout_pa=delta)
        else:
            delta = None
        c.add(f'{side}.calculated_dp', calc >= 0 if finite(calc) else None, calculated_dp_pa=calc)
        tol, allowance = p.get('dp_closure_tolerance_pa'), p.get('max_dp_pa')
        tol_ok = authority and finite(tol, minimum=0)
        c.add(f'{side}.dp_basis_closure', abs(calc-delta) <= tol if tol_ok and delta is not None and finite(calc, minimum=0) else None,
              pin_minus_pout_pa=delta, calculated_dp_pa=calc, tolerance_pa=tol)
        c.add(f'{side}.dp_allowance', calc <= allowance if authority and finite(allowance, minimum=0)
              and finite(calc, minimum=0) and valid and units else None, allowed_dp_pa=allowance, calculated_dp_pa=calc)
        endpoint_rules = p.get('reynolds_endpoints', {})
        endpoints = s.get('reynolds_endpoints', {})
        for end in ('inlet', 'outlet'):
            actual, rule = endpoints.get(end, {}), endpoint_rules.get(end, {})
            re = actual.get('value')
            minimum = rule.get('min_exclusive', rule.get('min'))
            maximum = rule.get('max_exclusive', rule.get('max'))
            exclusive_min, exclusive_max = 'min_exclusive' in rule, 'max_exclusive' in rule
            phase_ok = bool(actual.get('phase')) and actual.get('phase') == rule.get('phase')
            bounds_ok = ((minimum is not None or maximum is not None)
                         and not ('min' in rule and exclusive_min) and not ('max' in rule and exclusive_max)
                         and all(finite(rule[key], minimum=0) for key in ('min', 'max', 'min_exclusive', 'max_exclusive') if key in rule)
                         and (minimum is None or finite(minimum, minimum=0))
                         and (maximum is None or finite(maximum, minimum=0))
                         and (minimum is None or maximum is None or (minimum < maximum if exclusive_min or exclusive_max else minimum <= maximum)))
            known = authority and phase_ok and bounds_ok and source_ok(actual.get('source')) and finite(re, minimum=0)
            lower_ok = minimum is None or ((re > minimum if exclusive_min else re >= minimum) if known else False)
            upper_ok = maximum is None or ((re < maximum if exclusive_max else re <= maximum) if known else False)
            c.add(f'{side}.Re_{end}', lower_ok and upper_ok if known else None,
                  phase=actual.get('phase'), value=re, bounds=rule)
    area, rule = request.get('area', {}), profile.get('area', {})
    actual, required = area.get('actual'), area.get('required')
    coherent = (area.get('unit') == 'm2' and area.get('actual_basis') in ('gross', 'effective')
                and area.get('actual_basis') == area.get('required_basis') == rule.get('basis')
                and area.get('actual_condition') in ('clean', 'fouled')
                and area.get('actual_condition') == area.get('required_condition') == rule.get('condition')
                and source_ok(area.get('source')))
    c.add('area_basis', True if coherent else None)
    margin, min_margin, max_margin = None, rule.get('min_margin_fraction'), rule.get('max_margin_fraction')
    if finite(actual, positive=True) and finite(required, positive=True):
        computed = actual / required - 1
        margin = computed if finite(computed) else None
    margin_rule_ok = finite(min_margin) and ('max_margin_fraction' not in rule or finite(max_margin) and min_margin <= max_margin)
    c.add('area_margin', margin >= min_margin and (max_margin is None or margin <= max_margin)
          if coherent and authority and margin is not None and margin_rule_ok else None,
          margin_fraction=margin, required_margin_fraction=min_margin, max_margin_fraction=max_margin)
    return c.result()


@_safe_request({'stage_source': {}, 'diameter_source': {}, 'total_height_source': {}, 'expected_stage_ids': [],
                'stages': [{'source': {}}], 'beds': [{'source': {}, 'hetp_source': {}, 'stage_ids': []}],
                'acceptance_profile': {'source': {}, 'height_rules': [{}], 'grading_rule': {'source': {}}}})
def check_packed_beds(request: dict):
    """Per-stage FC and source-bound bed height/coverage checks; no averaged pass."""
    c = Checks('check_packed_beds')
    profile, stages, beds = request.get('acceptance_profile', {}), request.get('stages', []), request.get('beds', [])
    authority = source_ok(profile.get('source'))
    c.add('acceptance_profile_source', True if authority else None)
    expected = request.get('expected_stage_ids')
    valid_expected = isinstance(expected, list) and bool(expected) and all(valid_id(s) for s in expected)
    c.add('expected_stage_source', True if valid_expected and source_ok(request.get('stage_source')) else None)
    expected = expected if valid_expected else []
    c.add('unique_expected_stages', len(expected) == len(set(expected)) if valid_expected else None)
    ids = [s.get('stage_id') for s in stages]
    valid_actual = all(valid_id(s) for s in ids)
    c.add('actual_stage_ids', True if valid_actual and stages else None)
    c.add('stage_coverage', set(ids) == set(expected) and len(ids) == len(set(ids)) if valid_expected and valid_actual else None,
          missing=list(set(expected)-set(ids)) if valid_actual else None,
          extra=list(set(ids)-set(expected)) if valid_actual else None,
          duplicates=[k for k,v in Counter(ids).items() if v > 1] if valid_actual else None)
    lo, hi = profile.get('fc_min'), profile.get('fc_max')
    fc_rule = authority and finite(lo, minimum=0) and finite(hi, minimum=0) and lo <= hi and profile.get('fc_unit') == 'dimensionless'
    for i, stage in enumerate(stages):
        fc = stage.get('fc')
        known = fc_rule and finite(fc, minimum=0) and stage.get('fc_unit') == 'dimensionless' and source_ok(stage.get('source'))
        c.add(f'stage_{i}.FC', lo <= fc <= hi if known else None, stage_id=stage.get('stage_id'), fc=fc)
    bed_ids = [b.get('id') for b in beds]
    c.add('unique_bed_ids', len(bed_ids) == len(set(bed_ids)) if beds and all(valid_id(s) for s in bed_ids) else None)
    assigned = [s for b in beds for s in b.get('stage_ids', [])]
    valid_assigned = all(valid_id(s) for s in assigned)
    c.add('bed_stage_ids', True if valid_assigned and beds else None)
    c.add('bed_stage_coverage', set(assigned) == set(expected) and len(assigned) == len(set(assigned)) if valid_expected and beds and valid_assigned else None,
          missing=list(set(expected)-set(assigned)) if valid_assigned else None,
          extra=list(set(assigned)-set(expected)) if valid_assigned else None)
    diam = request.get('diameter_m')
    diameter_ok = finite(diam, positive=True) and request.get('diameter_unit') == 'm' and source_ok(request.get('diameter_source'))
    c.add('diameter_basis', True if diameter_ok else None)
    heights = []
    for i, bed in enumerate(beds):
        height, hetp = bed.get('height_m'), bed.get('hetp_m')
        heights.append(height)
        known = finite(height, positive=True) and bed.get('height_unit') == 'm' and source_ok(bed.get('source'))
        rules = [r for r in profile.get('height_rules', []) if diameter_ok
                 and (r.get('diameter_min_exclusive_m') is None or finite(r['diameter_min_exclusive_m'], minimum=0) and diam > r['diameter_min_exclusive_m'])
                 and (r.get('diameter_max_inclusive_m') is None or finite(r['diameter_max_inclusive_m'], positive=True) and diam <= r['diameter_max_inclusive_m'])]
        limit = rules[0].get('max_height_m') if len(rules) == 1 else None
        c.add(f'bed_{i}.height_limit', height <= limit if known and authority and finite(limit, positive=True) else None,
              height_m=height, selected_limit_m=limit, matching_rules=len(rules))
        stage_ids = bed.get('stage_ids', [])
        valid_hetp = finite(hetp, positive=True) and source_ok(bed.get('hetp_source')) and bed.get('hetp_unit') == 'm/stage'
        tolerance = profile.get('height_closure_tolerance_m')
        c.add(f'bed_{i}.HETP_closure', abs(height-hetp*len(stage_ids)) <= tolerance if known and valid_hetp
              and authority and finite(tolerance, minimum=0) and stage_ids else None,
              height_m=height, hetp_m=hetp, stage_count=len(stage_ids), derived_height_m=hetp*len(stage_ids) if valid_hetp else None)
    total = request.get('total_packed_height_m')
    tol = profile.get('height_closure_tolerance_m')
    c.add('bed_height_sum', abs(sum(heights)-total) <= tol if beds and all(finite(h, positive=True) for h in heights)
          and finite(total, positive=True) and request.get('total_height_unit') == 'm'
          and source_ok(request.get('total_height_source')) and authority and finite(tol, minimum=0) else None,
          sum_height_m=sum(heights) if heights and all(finite(h, positive=True) for h in heights) else None, reported_total_m=total)
    grading = profile.get('grading_rule')
    if grading is not None:
        criterion = grading.get('criterion')
        counts = [len(b.get('stage_ids', [])) for b in beds]
        known = authority and source_ok(grading.get('source')) and bool(beds) and criterion in ('nondecreasing_stage_counts', 'nonincreasing_stage_counts')
        ok = all(a <= b for a,b in zip(counts, counts[1:])) if criterion == 'nondecreasing_stage_counts' else all(a >= b for a,b in zip(counts, counts[1:]))
        c.add('bed_grading', ok if known else None, stage_counts=counts)
    return c.result()


def _value(node, path):
    child = node.find(path)
    return None if child is None else child.get('value', child.text)


def _number(node, path):
    try:
        value = float(_value(node, path))
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def _point(node, path):
    return (_number(node, path+'/x'), _number(node, path+'/y'))


def _mapped_diameter(root, mapping, kind):
    path = mapping.get(kind+'_diameter_path')
    if not isinstance(path, str) or not path:
        return None
    node = root.find(path)
    if node is None:
        return None
    unit = node.get('uom', mapping.get(kind+'_diameter_unit'))
    value = _number(root, path)
    return value * {'m': 1, 'mm': .001}[unit] if finite(value, positive=True) and unit in ('m', 'mm') else None


@_safe_request({'mapping': {'source': {}}, 'count_source': {}, 'coordinate_tolerance_source': {}})
def audit_edr_geometry(request: dict):
    """Read XML only. Native mapping is caller-confirmed, never a native run claim.

    Accept xml_path or xml_text (one only). XML schema details are explicitly
    supplied under mapping; unsupported/missing layouts stay unverified.
    """
    c = Checks('audit_edr_geometry')
    if bool(request.get('xml_path')) == bool(request.get('xml_text')):
        c.add('XML_input', None, reason='Supply exactly one of xml_path or xml_text')
        return c.result()
    try:
        raw = Path(request['xml_path']).read_bytes() if request.get('xml_path') else request['xml_text'].encode('utf-8')
        if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
            raise ValueError('DTD/entity declarations are unsupported')
        root = ET.fromstring(raw)
    except (OSError, ValueError, ET.ParseError) as exc:
        c.add('XML_input', None, reason=str(exc))
        return c.result()
    mapping = request.get('mapping', {})
    mapped = source_ok(mapping.get('source')) and mapping.get('coordinate_unit') == 'm'
    c.add('version_schema_mapping', True if mapped else None)
    bundle_path = mapping.get('bundle_path')
    bundles = root.findall(bundle_path) if isinstance(bundle_path, str) and bundle_path else []
    c.add('unique_bundle', True if len(bundles) == 1 else None, matched=len(bundles))
    if len(bundles) != 1:
        return c.result(xml_sha256=hashlib.sha256(raw).hexdigest())
    bundle = bundles[0]
    unit_conflicts = [node.tag for node in bundle.iter()
                      if node.tag in ('x', 'y', 'xMin', 'xMax', 'yMin', 'yMax', 'tubePitchInLine', 'tubeOD', 'diameter')
                      and node.get('uom') not in (None, 'm')]
    c.add('native_coordinate_dimension_units', True if not unit_conflicts and mapped else None,
          conflicting_fields=unit_conflicts)
    mapped = mapped and not unit_conflicts
    pitch = _number(bundle, 'tubePitchInLine')
    orient = _value(bundle, 'tubeLineOrient')
    c.add('native_pitch_orientation', True if finite(pitch, positive=True) and orient in ('Horizontal', 'Vertical') else None,
          pitch_m=pitch, orientation=orient)
    tubes, normals, rods, regions = [], [], [], []
    complete = True
    tolerance = request.get('coordinate_tolerance_m')
    tol_ok = finite(tolerance, minimum=0) and source_ok(request.get('coordinate_tolerance_source'))
    for region in bundle.findall('PassRegion'):
        current = []
        for line in region.findall('TubeLine'):
            endpoint_path = mapping.get('endpoint_path')
            endpoints = line.findall(endpoint_path) if isinstance(endpoint_path, str) and endpoint_path else []
            points = [(_number(p, 'x'), _number(p, 'y')) for p in endpoints]
            valid = (len(points) == 2 and all(finite(v) for p in points for v in p)
                     and finite(pitch, positive=True) and orient in ('Horizontal', 'Vertical') and tol_ok)
            if not valid:
                complete = False
                continue
            origin, end = points
            axis, other = (0, 1) if orient == 'Horizontal' else (1, 0)
            span = end[axis] - origin[axis]
            ratio = span / pitch
            if not finite(ratio):
                complete = False
                continue
            steps = round(ratio)
            if (span < 0 or abs(end[other] - origin[other]) > tolerance
                    or abs(span - steps*pitch) > tolerance or steps > 100000):
                complete = False
                continue
            count = steps + 1
            kind = _value(line, 'tubeType')
            if kind not in ('tlNormal', 'tlTieRod', 'tlSpacer'):
                complete = False
                continue
            for i in range(int(count)):
                point = (origin[0] + (pitch*i if orient == 'Horizontal' else 0), origin[1] + (pitch*i if orient == 'Vertical' else 0))
                if kind == 'tlNormal':
                    tubes.append(point); normals.append(point); current.append(point)
                else:
                    diameter = _mapped_diameter(root, mapping, 'spacer' if kind == 'tlSpacer' else 'rod')
                    rods.append((kind, point, diameter))
        regions.append((region, current))
    for rod in bundle.findall('TieRod'):
        point, diameter = _point(rod, 'CentrePosition'), _number(rod, 'diameter')
        if all(finite(v) for v in point):
            rods.append(('TieRod', point, diameter))
        else:
            complete = False
    c.add('decoded_layout_complete', True if complete and tubes and mapped else None)
    duplicates = [list(k) for k,v in Counter(tubes).items() if v > 1]
    rod_duplicates = [list(k) for k,v in Counter(p for _,p,_ in rods).items() if v > 1]
    c.add('unique_tube_coordinates', not duplicates if complete and tubes else None, duplicates=duplicates)
    c.add('unique_rod_coordinates', not rod_duplicates if rods else None, duplicates=rod_duplicates)
    actual = len(set(tubes)) if complete and tubes else None
    target, effective = request.get('target_tube_count'), request.get('effective_tube_count')
    if target is None and mapping.get('target_count_path'):
        target = _number(root, mapping['target_count_path'])
        node = root.find(mapping['target_count_path'])
        if node is not None and node.get('uom') not in (None, '', 'dimensionless'):
            target = None
    if effective is None and mapping.get('effective_count_path'):
        effective = _number(root, mapping['effective_count_path'])
        node = root.find(mapping['effective_count_path'])
        if node is not None and node.get('uom') not in (None, '', 'dimensionless'):
            effective = None
    counts_ok = all(finite(v, minimum=1) and v == int(v) for v in (target, effective)) and source_ok(request.get('count_source'))
    c.add('tube_count_closure', actual == target == effective if actual is not None and counts_ok and mapped else None,
          target_count=target, effective_count=effective, actual_unique_count=actual)
    for i,(region, points) in enumerate(regions):
        bounds = [_number(region,k) for k in ('xMin','xMax','yMin','yMax')]
        observed = [min(p[0] for p in points), max(p[0] for p in points), min(p[1] for p in points), max(p[1] for p in points)] if points else None
        c.add(f'pass_region_{i}.normal_center_bounds', all(abs(a-b) <= tolerance for a,b in zip(bounds, observed))
              if complete and observed and all(finite(v) for v in bounds) and tol_ok and mapped else None,
              stored_bounds_m=bounds, actual_normal_bounds_m=observed)
    tube_od = _number(bundle, 'tubeOD')
    collisions, dimensions_complete = [], finite(tube_od, positive=True)
    for kind, point, diameter in rods:
        if not finite(diameter, positive=True):
            dimensions_complete = False
            continue
        if finite(tube_od, positive=True):
            for tube in set(tubes):
                distance = math.hypot(tube[0]-point[0], tube[1]-point[1])
                if distance < (tube_od+diameter)/2:
                    collisions.append(dict(kind=kind, rod_center_m=list(point), tube_center_m=list(tube), center_distance_m=distance))
    c.add('rod_spacer_circle_collision', not collisions if dimensions_complete and complete and rods and tubes and mapped else None,
          collisions=collisions, scope='cross_section_circles_only; no support, clearance or vibration acceptance')
    return c.result(xml_sha256=hashlib.sha256(raw).hexdigest(), decoded_tube_centers_m=[list(p) for p in tubes],
                    limitations=['Version mapping and source authenticity require independent review.', 'No EDR execution, pressure model, vibration or mechanical acceptance is inferred.'])


TOOLS = {f.__name__: f for f in (screen_pipe_candidates, check_exchanger_basis, check_packed_beds, audit_edr_geometry)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tool', choices=TOOLS)
    parser.add_argument('--input', required=True, help='JSON filename or - for stdin')
    args = parser.parse_args()
    try:
        payload = json.loads(sys.stdin.read() if args.input == '-' else Path(args.input).read_text(encoding='utf-8-sig'),
                             parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON number: '+value)))
        if not isinstance(payload, dict):
            raise ValueError('Request must be a JSON object')
        result = TOOLS[args.tool](payload)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
    except (ValueError, TypeError, KeyError, AttributeError, OSError) as exc:
        print(json.dumps({'error': str(exc), 'engineering_acceptance': 'not_assessed'}))
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
