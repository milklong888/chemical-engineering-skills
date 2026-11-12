"""Independent synthetic regression inputs. NOT equipment evidence or design defaults."""
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from engineering_checks import (screen_pipe_candidates, check_exchanger_basis,
                                check_packed_beds, audit_edr_geometry)


def source():
    return dict(id='SYNTHETIC-NOT-ENGINEERING-EVIDENCE', locator='toy-row-1', revision='toy-v1', current_revision='toy-v1')


def status(result, name):
    return next(c['status'] for c in result['checks'] if c['check'] == name)


def pipe():
    # Q = pi/400 m3/s, ID = 0.1m -> exactly 1m/s, independent hand equation.
    return dict(volumetric_flow_m3_s=math.pi/400, flow_unit='m3/s', flow_source=source(),
                velocity_bounds_m_s=dict(min=1, max=1, source=source()),
                catalog=[dict(id='toy-A', od_mm=110, wall_mm=5, dimension_unit='mm', source=source())])


def exchanger():
    side = dict(pin_abs_pa=200000, pout_abs_pa=190000, calculated_dp_pa=10000,
                pressure_unit='Pa', pressure_basis='absolute', source=source(),
                reynolds_endpoints={e: dict(phase='liquid', value=100, source=source()) for e in ('inlet', 'outlet')})
    rule = dict(max_dp_pa=10000, dp_closure_tolerance_pa=0,
                reynolds_endpoints={e: dict(phase='liquid', min=100, max=100) for e in ('inlet', 'outlet')})
    return dict(equipment_id='toy-X', basis_id='toy-basis', source=source(), hot=copy.deepcopy(side), cold=copy.deepcopy(side),
                area=dict(actual=10, required=8, unit='m2', actual_basis='effective', required_basis='effective',
                          actual_condition='fouled', required_condition='fouled', source=source()),
                acceptance_profile=dict(source=source(), basis_id='toy-basis', hot=copy.deepcopy(rule), cold=copy.deepcopy(rule),
                                        area=dict(basis='effective', condition='fouled', min_margin_fraction=0.25)))


def packed():
    return dict(expected_stage_ids=['s1','s2','s3'], stage_source=source(), diameter_m=1, diameter_unit='m', diameter_source=source(),
                stages=[dict(stage_id=f's{i}', fc=0.5, fc_unit='dimensionless', source=source()) for i in (1,2,3)],
                beds=[dict(id='b1', stage_ids=['s1'], height_m=1, height_unit='m', source=source(), hetp_m=1, hetp_unit='m/stage', hetp_source=source()),
                      dict(id='b2', stage_ids=['s2','s3'], height_m=2, height_unit='m', source=source(), hetp_m=1, hetp_unit='m/stage', hetp_source=source())],
                total_packed_height_m=3, total_height_unit='m', total_height_source=source(),
                acceptance_profile=dict(source=source(), fc_min=0.4, fc_max=0.6, fc_unit='dimensionless', height_closure_tolerance_m=0,
                                        height_rules=[dict(diameter_max_inclusive_m=1, max_height_m=2),
                                                      dict(diameter_min_exclusive_m=1, max_height_m=1)],
                                        grading_rule=dict(criterion='nondecreasing_stage_counts', source=source())))


def geometry(orientation='Horizontal'):
    # Explicit expected centers are (0,0),(.04,0),(.08,0); vertical exchanges x/y.
    endx, endy = ('0.08','0') if orientation == 'Horizontal' else ('0','0.08')
    xml = f'''<application><objects><object name="SyntheticLayout"><Exchanger><TubeBundle>
    <tubePitchInLine value="0.04"/><tubeLineOrient value="{orientation}"/><tubeOD value="0.02"/>
    <PassRegion><xMin value="0"/><xMax value="{endx}"/><yMin value="0"/><yMax value="{endy}"/>
    <TubeLine><tubeType value="tlNormal"/>
    <CentrePosition><x value="0"/><y value="0"/></CentrePosition>
    <CentrePosition><x value="{endx}"/><y value="{endy}"/></CentrePosition>
    </TubeLine></PassRegion>
    <TieRod><CentrePosition><x value="1"/><y value="1"/></CentrePosition><diameter value="0.01"/></TieRod>
    </TubeBundle></Exchanger></object></objects></application>'''
    return dict(xml_text=xml, mapping=dict(source=source(), coordinate_unit='m',
                bundle_path="./objects/object[@name='SyntheticLayout']/Exchanger/TubeBundle", endpoint_path='CentrePosition'),
                target_tube_count=3, effective_tube_count=3, count_source=source(), coordinate_tolerance_m=1e-12, coordinate_tolerance_source=source())


class PipeTests(unittest.TestCase):
    def test_boundary_math(self):
        r = screen_pipe_candidates(pipe())
        self.assertEqual(r['candidates'][0]['inner_diameter_m'], 0.1)
        self.assertAlmostEqual(r['candidates'][0]['velocity_m_s'], 1)
        self.assertEqual(r['feasible_candidate_ids'], ['toy-A'])

    def test_no_roundup_or_catalog_fabrication(self):
        p = pipe(); p['catalog'].append(dict(id='toy-B', od_mm=210, wall_mm=5, dimension_unit='mm', source=source()))
        r = screen_pipe_candidates(p)
        self.assertEqual(r['feasible_candidate_ids'], ['toy-A'])
        self.assertEqual(len(r['candidates']), 2)
        self.assertEqual(r['candidates'][1]['diagnostic_status'], 'fail')

    def test_missing_stale_and_unit(self):
        for mutate in (lambda p: p['catalog'][0].pop('source'),
                       lambda p: p['catalog'][0]['source'].update(current_revision='toy-v2'),
                       lambda p: p.update(flow_unit='m3/h')):
            p = pipe(); mutate(p)
            self.assertEqual(screen_pipe_candidates(p)['diagnostic_status'], 'unverified')
        self.assertEqual(screen_pipe_candidates({})['diagnostic_status'], 'unverified')

    def test_bad_dimensions_and_nonfinite(self):
        p = pipe(); p['catalog'][0]['wall_mm'] = 55
        self.assertEqual(screen_pipe_candidates(p)['candidates'][0]['diagnostic_status'], 'fail')
        for value in (None, float('inf'), float('nan'), -1, True):
            p = pipe(); p['volumetric_flow_m3_s'] = value
            self.assertNotEqual(screen_pipe_candidates(p)['diagnostic_status'], 'pass')
        p = pipe(); p['catalog'][0].update(od_mm=1e-300, wall_mm=1e-303)
        self.assertEqual(screen_pipe_candidates(p)['diagnostic_status'], 'unverified')

    def test_required_unique_catalog_identity(self):
        for invalid in (None, '', '   ', True, 1.0, [], {}):
            p = pipe(); p['catalog'][0]['id'] = invalid
            r = screen_pipe_candidates(p)
            self.assertNotEqual(r['diagnostic_status'], 'pass')
            self.assertEqual(r['feasible_candidate_ids'], [])
        p = pipe(); p['catalog'][0].pop('id')
        r = screen_pipe_candidates(p)
        self.assertEqual(r['diagnostic_status'], 'unverified')
        self.assertEqual(r['feasible_candidate_ids'], [])
        p = pipe(); p['catalog'].append(copy.deepcopy(p['catalog'][0]))
        r = screen_pipe_candidates(p)
        self.assertEqual(status(r, 'catalog_identity'), 'fail')
        self.assertEqual(r['feasible_candidate_ids'], [])
        p = pipe(); p['catalog'][0]['id'] = 0
        self.assertEqual(screen_pipe_candidates(p)['feasible_candidate_ids'], [0])


class ExchangerTests(unittest.TestCase):
    def test_independent_basis_math_and_no_universal_re(self):
        r = check_exchanger_basis(exchanger())
        self.assertEqual(r['diagnostic_status'], 'pass')
        self.assertEqual(status(r, 'hot.Re_inlet'), 'pass')  # 100 is authority-bound, no universal 6000.
        self.assertEqual(next(c['margin_fraction'] for c in r['checks'] if c['check']=='area_margin'), .25)
        self.assertEqual(r['engineering_acceptance'], 'not_assessed')

    def test_negative_absolute_pressure(self):
        p = exchanger(); p['hot']['pin_abs_pa'] = -1
        self.assertEqual(status(check_exchanger_basis(p), 'hot.absolute_pressure'), 'fail')

    def test_missing_calculated_not_inferred(self):
        p = exchanger(); p['hot'].pop('calculated_dp_pa')
        r = check_exchanger_basis(p)
        self.assertEqual(status(r, 'hot.calculated_dp'), 'unverified')
        self.assertEqual(status(r, 'hot.dp_basis_closure'), 'unverified')

    def test_dp_closure_and_allowance_independent(self):
        p = exchanger(); p['hot']['calculated_dp_pa'] = 9000
        r = check_exchanger_basis(p)
        self.assertEqual(status(r, 'hot.dp_basis_closure'), 'fail')
        self.assertEqual(status(r, 'hot.dp_allowance'), 'pass')

    def test_area_units_condition_basis_and_stale(self):
        for field, value in (('unit','ft2'), ('required_basis','gross'), ('required_condition','clean')):
            p = exchanger(); p['area'][field] = value
            self.assertEqual(status(check_exchanger_basis(p), 'area_margin'), 'unverified')
        p = exchanger(); p['acceptance_profile']['source']['stale'] = True
        self.assertEqual(check_exchanger_basis(p)['diagnostic_status'], 'unverified')
        p = exchanger(); p['area'].update(actual=1e308, required=1e-308)
        self.assertEqual(status(check_exchanger_basis(p), 'area_margin'), 'unverified')

    def test_phase_endpoints_and_nonfinite(self):
        p = exchanger(); p['hot']['reynolds_endpoints']['outlet']['phase'] = 'two_phase'
        self.assertEqual(status(check_exchanger_basis(p), 'hot.Re_outlet'), 'unverified')
        for value in (None, float('inf'), float('nan')):
            p = exchanger(); p['cold']['pout_abs_pa'] = value
            self.assertNotEqual(check_exchanger_basis(p)['diagnostic_status'], 'pass')

    def test_area_upper_margin_authority(self):
        p = exchanger(); p['area'].update(actual=16, required=10)
        p['acceptance_profile']['area'].update(min_margin_fraction=.3, max_margin_fraction=.5)
        self.assertEqual(status(check_exchanger_basis(p), 'area_margin'), 'fail')
        p['area']['actual'] = 15
        self.assertEqual(status(check_exchanger_basis(p), 'area_margin'), 'pass')
        p['acceptance_profile']['area']['max_margin_fraction'] = None
        self.assertEqual(status(check_exchanger_basis(p), 'area_margin'), 'unverified')
        p['acceptance_profile']['area'].update(min_margin_fraction=.6, max_margin_fraction=.5)
        self.assertEqual(status(check_exchanger_basis(p), 'area_margin'), 'unverified')

    def test_re_inclusive_and_exclusive_endpoints(self):
        p = exchanger(); p['hot']['reynolds_endpoints']['inlet']['value'] = 6000
        rule = p['acceptance_profile']['hot']['reynolds_endpoints']['inlet']
        rule.clear(); rule.update(phase='liquid', min_exclusive=6000)
        self.assertEqual(status(check_exchanger_basis(p), 'hot.Re_inlet'), 'fail')
        p['hot']['reynolds_endpoints']['inlet']['value'] = 6001
        self.assertEqual(status(check_exchanger_basis(p), 'hot.Re_inlet'), 'pass')
        rule.clear(); rule.update(phase='liquid', max_exclusive=6001)
        self.assertEqual(status(check_exchanger_basis(p), 'hot.Re_inlet'), 'fail')
        rule.clear(); rule.update(phase='liquid', min=6001, max=6001)
        self.assertEqual(status(check_exchanger_basis(p), 'hot.Re_inlet'), 'pass')
        rule['min_exclusive'] = 6001
        self.assertEqual(status(check_exchanger_basis(p), 'hot.Re_inlet'), 'unverified')


class PackedTests(unittest.TestCase):
    def test_stage_identity_does_not_alias_boolean_to_integer(self):
        p = packed(); p['expected_stage_ids'] = [1,2,3]
        for i, stage in enumerate(p['stages'], 1):
            stage['stage_id'] = i
        p['beds'][0]['stage_ids'] = [1]; p['beds'][1]['stage_ids'] = [2,3]
        self.assertEqual(check_packed_beds(p)['diagnostic_status'], 'pass')
        for invalid in (True, 1.0, '', '  ', None, [], {}):
            changed = copy.deepcopy(p)
            changed['stages'][0]['stage_id'] = invalid
            self.assertNotEqual(check_packed_beds(changed)['diagnostic_status'], 'pass')
            changed = copy.deepcopy(p)
            changed['beds'][0]['stage_ids'] = [invalid]
            self.assertNotEqual(check_packed_beds(changed)['diagnostic_status'], 'pass')
            changed = copy.deepcopy(p)
            changed['expected_stage_ids'][0] = invalid
            self.assertNotEqual(check_packed_beds(changed)['diagnostic_status'], 'pass')
        p['stages'][0]['stage_id'] = True; p['beds'][0]['stage_ids'] = [True]
        r = check_packed_beds(p)
        self.assertEqual(status(r, 'actual_stage_ids'), 'unverified')
        self.assertEqual(status(r, 'bed_stage_ids'), 'unverified')

    def test_diameter_equality_and_sum(self):
        p = packed(); r = check_packed_beds(p)
        self.assertEqual(r['diagnostic_status'], 'pass')
        p['diameter_m'] = 1.00001
        self.assertEqual(status(check_packed_beds(p), 'bed_1.height_limit'), 'fail')

    def test_bad_stage_cannot_hide_in_mean(self):
        p = packed(); p['stages'][0]['fc'] = .1; p['stages'][1]['fc'] = .9
        self.assertEqual(status(check_packed_beds(p), 'stage_0.FC'), 'fail')

    def test_missing_extra_duplicate(self):
        p = packed(); p['stages'].pop()
        self.assertEqual(status(check_packed_beds(p), 'stage_coverage'), 'fail')
        p = packed(); p['stages'].append(copy.deepcopy(p['stages'][0]))
        self.assertEqual(status(check_packed_beds(p), 'stage_coverage'), 'fail')
        p = packed(); p['stages'][0]['stage_id'] = 'extra'
        self.assertEqual(status(check_packed_beds(p), 'stage_coverage'), 'fail')
        p = packed(); p['beds'][1]['stage_ids'][0] = 's1'
        self.assertEqual(status(check_packed_beds(p), 'bed_stage_coverage'), 'fail')

    def test_no_default_hetp_or_height(self):
        p = packed(); p['beds'][0].pop('hetp_source')
        self.assertEqual(status(check_packed_beds(p), 'bed_0.HETP_closure'), 'unverified')
        p = packed(); p['total_packed_height_m'] = 4
        self.assertEqual(status(check_packed_beds(p), 'bed_height_sum'), 'fail')
        p = packed(); p['acceptance_profile'].pop('height_rules')
        self.assertEqual(status(check_packed_beds(p), 'bed_0.height_limit'), 'unverified')


class GeometryTests(unittest.TestCase):
    def test_horizontal_vertical_and_native_nonclaim(self):
        for orient, points in [('Horizontal', [[0,0],[.04,0],[.08,0]]), ('Vertical', [[0,0],[0,.04],[0,.08]])]:
            r = audit_edr_geometry(geometry(orient))
            self.assertEqual(r['decoded_tube_centers_m'], points)
            self.assertEqual(r['diagnostic_status'], 'pass')
            self.assertEqual(r['native_calculation_acceptance'], 'not_assessed')

    def test_singleton_and_duplicate(self):
        p = geometry(); p['xml_text'] = p['xml_text'].replace('value="0.08"','value="0"')
        p['target_tube_count'] = p['effective_tube_count'] = 1
        self.assertEqual(audit_edr_geometry(p)['decoded_tube_centers_m'], [[0,0]])
        p = geometry(); line = p['xml_text'].split('<TubeLine>')[1].split('</TubeLine>')[0]
        p['xml_text'] = p['xml_text'].replace('</PassRegion>', '<TubeLine>'+line+'</TubeLine></PassRegion>')
        r = audit_edr_geometry(p)
        self.assertEqual(status(r, 'unique_tube_coordinates'), 'fail')
        self.assertEqual(next(c['actual_unique_count'] for c in r['checks'] if c['check']=='tube_count_closure'), 3)

    def test_missing_pitch_type_mapping_count_and_invalid_span(self):
        for mutate in (lambda p: p.update(xml_text=p['xml_text'].replace('<tubePitchInLine value="0.04"/>','')),
                       lambda p: p.update(xml_text=p['xml_text'].replace('<tubeType value="tlNormal"/>','')),
                       lambda p: p['mapping'].pop('source'),
                       lambda p: p.pop('effective_tube_count'),
                       lambda p: p.update(xml_text=p['xml_text'].replace('value="0.08"','value="0.09"'))):
            p = geometry(); mutate(p)
            self.assertEqual(audit_edr_geometry(p)['diagnostic_status'], 'unverified')
        p = geometry(); p['xml_text'] = p['xml_text'].replace('<tubePitchInLine value="0.04"/>','<tubePitchInLine value="0.04" uom="mm"/>')
        self.assertEqual(audit_edr_geometry(p)['diagnostic_status'], 'unverified')

    def test_bounds_and_circle_collision(self):
        p = geometry(); p['xml_text'] = p['xml_text'].replace('<xMax value="0.08"/>','<xMax value="0.1"/>')
        self.assertEqual(status(audit_edr_geometry(p), 'pass_region_0.normal_center_bounds'), 'fail')
        p = geometry(); p['xml_text'] = p['xml_text'].replace('<x value="1"/><y value="1"/>','<x value="0.005"/><y value="0"/>')
        self.assertEqual(status(audit_edr_geometry(p), 'rod_spacer_circle_collision'), 'fail')
        p['xml_text'] = p['xml_text'].replace('<diameter value="0.01"/>','')
        self.assertEqual(status(audit_edr_geometry(p), 'rod_spacer_circle_collision'), 'unverified')

    def test_count_disagreement_and_duplicate_rods(self):
        p = geometry(); p['effective_tube_count'] = 2
        self.assertEqual(status(audit_edr_geometry(p), 'tube_count_closure'), 'fail')
        p = geometry(); rod = p['xml_text'].split('<TieRod>')[1].split('</TieRod>')[0]
        p['xml_text'] = p['xml_text'].replace('</TubeBundle>', '<TieRod>'+rod+'</TieRod></TubeBundle>')
        self.assertEqual(status(audit_edr_geometry(p), 'unique_rod_coordinates'), 'fail')

    def test_spacer_mm_conversion(self):
        p = geometry()
        p['xml_text'] = p['xml_text'].replace('</TubeBundle>', '''<PassRegion><TubeLine>
            <CentrePosition><x value="0.005"/><y value="0"/></CentrePosition>
            <CentrePosition><x value="0.005"/><y value="0"/></CentrePosition>
            <tubeType value="tlSpacer"/></TubeLine></PassRegion></TubeBundle>''')
        p['xml_text'] = p['xml_text'].replace('</application>', '<SpacerOD value="10" uom="mm"/></application>')
        p['mapping']['spacer_diameter_path'] = './SpacerOD'
        r = audit_edr_geometry(p)
        self.assertEqual(status(r, 'rod_spacer_circle_collision'), 'fail')

    def test_readonly_hash_and_unknown_schema(self):
        p = geometry()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'toy.xml'; path.write_text(p.pop('xml_text'), encoding='utf-8')
            before = hashlib.sha256(path.read_bytes()).hexdigest(); p['xml_path'] = str(path)
            r = audit_edr_geometry(p)
            self.assertEqual(before, hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(before, r['xml_sha256'])
        self.assertEqual(audit_edr_geometry(dict(xml_text='<unknown/>'))['diagnostic_status'], 'unverified')
        self.assertEqual(audit_edr_geometry(dict(xml_text='<!DOCTYPE a><a/>'))['diagnostic_status'], 'unverified')


class InterfaceTests(unittest.TestCase):
    def test_metadata_types_are_explicit_not_coerced(self):
        for key, values in [('stale', [1, 0, 'true', 'false', None, [], {}]),
                            ('id', [1, True, [], {}, '', '  ']),
                            ('locator', [1, True, [], {}, '', '  ']),
                            ('revision', [1, True, [], {}, '', '  ']),
                            ('current_revision', [1, True, [], {}, None, '', '  '])]:
            for value in values:
                with self.subTest(field=key, value=value):
                    p = pipe(); p['flow_source'][key] = value
                    self.assertEqual(screen_pipe_candidates(p)['diagnostic_status'], 'unverified')
        p = pipe(); p['flow_source'].pop('current_revision')
        self.assertEqual(screen_pipe_candidates(p)['diagnostic_status'], 'pass')
        p['flow_source']['stale'] = False
        self.assertEqual(screen_pipe_candidates(p)['diagnostic_status'], 'pass')
        p['flow_source']['stale'] = True
        self.assertEqual(screen_pipe_candidates(p)['diagnostic_status'], 'unverified')

    def test_exchanger_identity_types_are_not_dict_equality(self):
        for value in (True, False, {}, {'toy':'same'}, [], ['toy'], 1.0, '', '  ', None):
            p = exchanger(); p['equipment_id'] = copy.deepcopy(value)
            self.assertEqual(status(check_exchanger_basis(p), 'same_equipment_basis'), 'unverified')
            p = exchanger(); p['basis_id'] = copy.deepcopy(value)
            p['acceptance_profile']['basis_id'] = copy.deepcopy(value)
            self.assertEqual(status(check_exchanger_basis(p), 'same_equipment_basis'), 'unverified')
        p = exchanger(); p['equipment_id'] = 0; p['basis_id'] = 0; p['acceptance_profile']['basis_id'] = 0
        self.assertEqual(check_exchanger_basis(p)['diagnostic_status'], 'pass')

    def test_malformed_nested_requests_are_structured(self):
        cases = [(screen_pipe_candidates, {'catalog':[None]}),
                 (screen_pipe_candidates, {'velocity_bounds_m_s': []}),
                 (check_exchanger_basis, {'acceptance_profile': None}),
                 (check_exchanger_basis, {'acceptance_profile': []}),
                 (check_exchanger_basis, {'hot': {'reynolds_endpoints': {'inlet': None}}}),
                 (check_packed_beds, {'stages': 'not-a-list'}),
                 (check_packed_beds, {'beds': [{'stage_ids': None}]}),
                 (audit_edr_geometry, {'mapping': None}),
                 (audit_edr_geometry, None)]
        for function, request in cases:
            with self.subTest(tool=function.__name__, request=request):
                result = function(request)
                self.assertEqual(result['diagnostic_status'], 'unverified')
                self.assertEqual(result['engineering_acceptance'], 'not_assessed')
                self.assertEqual(status(result, 'invalid_request'), 'unverified')

    def test_cli_json_and_nonfinite_rejection(self):
        script = Path(__file__).resolve().parents[1] / 'scripts' / 'engineering_checks.py'
        response = subprocess.run([sys.executable, str(script), 'screen_pipe_candidates', '--input', '-'],
                                  input=json.dumps(pipe()), text=True, capture_output=True, timeout=10)
        self.assertEqual(response.returncode, 0, response.stderr)
        self.assertEqual(json.loads(response.stdout)['feasible_candidate_ids'], ['toy-A'])
        response = subprocess.run([sys.executable, str(script), 'screen_pipe_candidates', '--input', '-'],
                                  input='{"volumetric_flow_m3_s":NaN}', text=True, capture_output=True, timeout=10)
        self.assertEqual(response.returncode, 2)
        self.assertIn('Nonfinite JSON number', json.loads(response.stdout)['error'])

    @unittest.skipUnless(importlib.util.find_spec('mcp'), 'Optional mcp SDK is not installed in this interpreter')
    def test_real_stdio_mcp(self):
        import anyio
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        async def exercise():
            script = Path(__file__).resolve().parents[1] / 'scripts' / 'checks_mcp.py'
            params = StdioServerParameters(command=sys.executable, args=[str(script)])
            with anyio.fail_after(30):
                async with stdio_client(params) as (read, write):
                    async with ClientSession(read, write) as session:
                        response = await session.initialize()
                        self.assertTrue(response.protocolVersion)
                        listing = await session.list_tools()
                        self.assertEqual({t.name for t in listing.tools}, {'screen_pipe_candidates', 'check_exchanger_basis', 'check_packed_beds', 'audit_edr_geometry'})
                        for name, fixture in [('screen_pipe_candidates',pipe), ('check_exchanger_basis',exchanger),
                                              ('check_packed_beds',packed), ('audit_edr_geometry',geometry)]:
                            result = await session.call_tool(name, {'request': fixture()})
                            self.assertFalse(result.isError)
                            data = result.structuredContent or json.loads(next(c.text for c in result.content if c.type=='text'))
                            self.assertEqual(data['diagnostic_status'], 'pass')
                            self.assertEqual(data['engineering_acceptance'], 'not_assessed')
                            if name == 'audit_edr_geometry':
                                self.assertEqual(data['decoded_tube_centers_m'], [[0,0],[.04,0],[.08,0]])
                        for name, request in [('check_exchanger_basis', {'acceptance_profile': None}),
                                              ('screen_pipe_candidates', {'catalog': [None]}),
                                              ('check_packed_beds', {'stages': {}})]:
                            result = await session.call_tool(name, {'request': request})
                            self.assertFalse(result.isError)
                            data = result.structuredContent or json.loads(next(c.text for c in result.content if c.type=='text'))
                            self.assertEqual(data['diagnostic_status'], 'unverified')
                            self.assertEqual(status(data, 'invalid_request'), 'unverified')
        anyio.run(exercise)


if __name__ == '__main__':
    unittest.main(verbosity=2)
