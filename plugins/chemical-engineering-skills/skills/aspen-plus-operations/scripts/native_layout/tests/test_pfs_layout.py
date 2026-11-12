"""Public synthetic tests. Fixtures are invented text, never project models."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from native_layout import pfs_layout as pfs, private_integration


SECONDARY = "At 0 0\nLabel At 0 0\nROUTE 0 1\n$ $ 0.0 0.0\nROUTE 1 1\n$ $ 0.0 0.0\nAt 0 0\nLabel At 0 0\nROUTE 0 2\n$ $ 0.0 0.0\nROUTE 1 2\n$ $ 0.0 0.0\n"


def fixed_route(side, root, endpoint=None, direction=None):
    if endpoint is None:
        return f"ROUTE {side} 0\n$ $ 0.0 0.0\n"
    return f"ROUTE {side} 0\nr r {root[0]} {root[1]} 0\nt {direction} {endpoint[0]} {endpoint[1]} 0\n$ C 1.000000 0.0\n$ $ 0.0 0.0\n"


def fixture():
    physical = ("TITLE Synthetic only\nFLOWSHEET\n"
                "    BLOCK HX.A IN=FUEL.IN WATER.IN OUT=LINK WATER.OUT\n"
                "    BLOCK PUMP-B IN=LINK OUT=PROD.OUT\n"
                "PROPERTIES SYNTHETIC\nPARAM TOL= 1.000E-6\n")
    config = ";PFS V 5.00\n;settings_keep_this 314\n;#APWNLIB\n;startlibrary\n;endlibrary\n;#APWNBLOCK\n;2\n;>VERSION 0\n;HX.A\n;HeatX\n;Built-In\n;HEATX\n;>VERSION 0\n;PUMP-B\n;Pump\n;Built-In\n;PUMP\n"
    graph = "PFSVData\n# of PFS Objects = 8\nSIZE -8 8 -5 5\n"
    for name, x, icon in [("HX.A", 0, "GEN-HS"), ("PUMP-B", 4, "ICONX")]:
        graph += f'BLOCK\nID: {name}\nVersion: 1\nICON: "{icon}"\nFlag 0\nSection GLOBAL\nAt {x} 0\nLabel At 0 1\nScale 1E+0 Modifier 0\n'
    for name, terminal, root, start, end, sd, ed in [
        ("FUEL.IN", 1, (-3, 0), None, (-.4, 0), None, "l"),
        ("LINK", 0, (2, 0), (.4, 0), (3.7, 0), "r", "l"),
        ("PROD.OUT", 2, (6, 0), (4.3, 0), None, "r", None),
        ("WATER.IN", 1, (.2, -2), None, (.2, -.3), None, "d"),
        ("WATER.OUT", 2, (-.2, 2), (-.2, .3), None, "u", None),
    ]:
        graph += f"STREAM\nID: {name}\nVersion: 2\nFlag 0\nTYPE 0 TERMINAL {terminal}\nAt {root[0]} {root[1]}\nLabel At 0 .2\n"
        graph += fixed_route(0, root, start, sd) + fixed_route(1, root, end, ed) + SECONDARY
    graph += "LEGEND\nVersion: 2\nUnfixed\n# of PFS Objects = 0\nVIEWPORT -8 5 8 -5\nLAYOUT\nTableFormat 1\nPages 1 1 1 1\nPAGESETUP\nSCALE 1\n"
    raw = (physical + "".join(";" + x + "\n" for x in graph.splitlines()) + "STREAM-REPOR MOLEFLOW\n" + config + "E_LINK\n").encode("ascii")
    ref = (physical + "STREAM-REPOR MOLEFLOW\n").encode("ascii")
    return raw, ref


def plan():
    return {"version": 1, "blocks": {"HX.A": {"at": [1, 1], "scale": 2, "modifier": 3, "label": [-1, .5]}}, "streams": {
        "FUEL.IN": {"path": [[-3, 2], [.5, 2]], "ports": {"1": {"direction": "l"}}, "label": [0, .2]},
        "LINK": {"path": [[1.5, 2], [2.5, 2], [2.5, 0], [3.7, 0]], "ports": {"0": {"direction": "r"}, "1": {"direction": "l"}}, "label": [0, .2]},
        "WATER.IN": {"path": [[.4, -2], [.4, .4], [.6, .4]], "ports": {"1": {"direction": "l"}}, "label": [0, .2]},
        "WATER.OUT": {"path": [[1.4, 2.5], [1.4, 4]], "ports": {"0": {"direction": "u"}}, "label": [0, .2]},
    }, "size": [-8, 8, -5, 5]}


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.raw, self.ref = fixture()

    def test_synthetic_arbitrary_names_and_bindings(self):
        doc = pfs.Document(self.raw)
        self.assertEqual(set(doc.blocks), {"HX.A", "PUMP-B"})
        self.assertEqual(doc.anchors["FUEL.IN", 1]["canonical"], (-.4, 0))
        self.assertEqual(doc.inspect()['size'], (-8, 8, -5, 5))
        self.assertEqual(doc.inspect()['streams']['LINK']['label'], (0, .2))

    def test_all_eight_modifiers_invert(self):
        self.assertEqual(pfs.mv(pfs.MATRICES[3], (2, 5)), (-5, 2))
        self.assertEqual(pfs.mv(pfs.MATRICES[4], (2, 5)), (5, -2))
        for matrix in pfs.MATRICES.values():
            self.assertEqual(pfs.mv(pfs.inverse(matrix), pfs.mv(matrix, (2, 5))), (2, 5))

    def test_apply_preserves_every_physical_card_config_and_icons(self):
        output = pfs.apply_layout(self.raw, self.ref, plan())
        self.assertEqual(pfs.physical_tokens(output), pfs.physical_tokens(self.ref))
        self.assertIn(b"STREAM-REPOR MOLEFLOW", output)
        self.assertIn(b";settings_keep_this 314", output)
        self.assertIn(b";#APWNBLOCK", output)
        self.assertNotIn(b"\nE_LINK", output)

    def test_rotated_scaled_dual_water_anchors_and_dragged_d(self):
        output = pfs.apply_layout(self.raw, self.ref, plan())
        doc = pfs.Document(output)
        self.assertEqual(doc.blocks["HX.A"].modifier, 3)
        for key, expected in [(('FUEL.IN', 1), (-.4, 0)), (('LINK', 0), (.4, 0)), (('WATER.IN', 1), (.2, -.3)), (('WATER.OUT', 0), (-.2, .3))]:
            self.assertLess(pfs.math.dist(doc.anchors[key]['canonical'], expected), 1e-8)
        route = doc.streams['FUEL.IN'].routes[1]
        self.assertEqual(route.displacement, (-.5, 1.8))
        self.assertEqual(route.direction, 'l')
        self.assertEqual(route.connection, 0)

    def test_inverse_existing_modifier_with_d(self):
        changed = pfs.apply_layout(self.raw, self.ref, plan())
        p = plan(); p['blocks']['HX.A'].update(modifier=7, scale=.7, at=[-1, 2])
        twice = pfs.Document(pfs.apply_layout(changed, self.ref, p))
        self.assertLess(pfs.math.dist(twice.anchors['WATER.IN', 1]['canonical'], (.2, -.3)), 1e-8)

    def test_verified_identical_offline_readback(self):
        output = pfs.apply_layout(self.raw, self.ref, plan())
        self.assertTrue(pfs.verify_layout(output, output, self.ref)['offline_graphic_readback_pass'])

    def test_private_runner_never_requires_public_case_paths(self):
        output = pfs.apply_layout(self.raw, self.ref, plan())
        receipt = private_integration.run_case(self.raw, self.ref, plan(), output)
        self.assertTrue(receipt['native_export_readback_compared'])
        self.assertNotIn('path', json.dumps(receipt))

    def test_genuine_cards_before_or_after_graphics(self):
        lines = self.raw.splitlines(keepends=True)
        physical = [x for x in lines if not x.startswith(b';') and x.strip() != b'E_LINK']
        comments = [x for x in lines if x.startswith(b';')]
        reordered = b''.join(comments + physical)
        output = pfs.apply_layout(reordered, self.ref, plan())
        self.assertEqual(pfs.physical_tokens(output), pfs.physical_tokens(self.ref))

    def test_scientific_source_numbers(self):
        raw = self.raw.replace(b';Scale 1E+0 Modifier', b';Scale 1.0D+00 Modifier').replace(b';At 4 0', b';At 4.0E+00 0.0e0')
        self.assertEqual(pfs.Document(raw).blocks['PUMP-B'].at, (4, 0))

    def test_missing_route_for_changed_block_rejected(self):
        p = plan(); del p['streams']['WATER.IN']
        with self.assertRaisesRegex(pfs.LayoutError, 'Missing route'):
            pfs.apply_layout(self.raw, self.ref, p)

    def test_missing_config_rejected(self):
        with self.assertRaises(pfs.LayoutError):
            pfs.Document(self.raw.replace(b';PFS V 5.00\n', b''))

    def test_missing_icon_definition_rejected(self):
        with self.assertRaisesRegex(pfs.LayoutError, 'icon block definitions'):
            pfs.Document(self.raw.replace(b';>VERSION 0\n;PUMP-B\n;Pump\n;Built-In\n;PUMP\n', b''))

    def test_config_mutation_readback_rejected(self):
        output = pfs.apply_layout(self.raw, self.ref, plan())
        with self.assertRaisesRegex(pfs.LayoutError, 'config records'):
            pfs.verify_layout(output, output.replace(b';settings_keep_this 314', b';settings_keep_this 315'), self.ref)

    def test_size_and_viewport_clipping_rejected(self):
        output = pfs.apply_layout(self.raw, self.ref, plan())
        for bad in [output.replace(b';SIZE -8.000000000 8.000000000 -5.000000000 5.000000000', b';SIZE -800 -799 -400 -399'),
                    output.replace(b';VIEWPORT -8.000000000 5.000000000 8.000000000 -5.000000000', b';VIEWPORT -800 -399 -799 -400')]:
            with self.assertRaisesRegex(pfs.LayoutError, 'frame'):
                pfs.verify_layout(output, bad, self.ref)

    def test_legend_print_setting_change_rejected(self):
        output = pfs.apply_layout(self.raw, self.ref, plan())
        with self.assertRaisesRegex(pfs.LayoutError, 'LEGEND frame'):
            pfs.verify_layout(output, output.replace(b';SCALE 1', b';SCALE 2'), self.ref)

    def test_legend_order_and_numeric_spelling_equivalent(self):
        output = pfs.apply_layout(self.raw, self.ref, plan())
        changed = output.replace(b';TableFormat 1\r\n;Pages 1 1 1 1', b';Pages 1.0 1E0 1 1\r\n;TableFormat 1.000')
        self.assertTrue(pfs.verify_layout(output, changed, self.ref)['frame_and_legend_equal'])

    def test_duplicate_or_missing_or_unknown_legend_fields_rejected(self):
        for bad in [self.raw.replace(b';SCALE 1', b';SCALE 1\n;SCALE 1'),
                    self.raw.replace(b';SCALE 1\n', b''),
                    self.raw.replace(b';SCALE 1', b';UNKNOWN_FRAME 2\n;SCALE 1')]:
            with self.assertRaises(pfs.LayoutError):
                pfs.Document(bad)

    def test_unknown_object_rejected(self):
        with self.assertRaises(pfs.LayoutError):
            pfs.Document(self.raw.replace(b';LEGEND\n', b';RECTANGLE\n;At 1 1\n;LEGEND\n'))

    def test_duplicate_id_rejected(self):
        with self.assertRaisesRegex(pfs.LayoutError, 'Duplicate graphic BLOCK'):
            pfs.Document(self.raw.replace(b';ID: PUMP-B', b';ID: HX.A'))

    def test_wrong_physical_endpoint_role_rejected(self):
        p = plan(); p['streams']['WATER.IN']['ports'] = {'0': {'direction': 'l'}}
        with self.assertRaisesRegex(pfs.LayoutError, 'Physical endpoint role'):
            pfs.apply_layout(self.raw, self.ref, p)

    def test_direction_mismatch_rejected(self):
        p = plan(); p['streams']['WATER.IN']['ports']['1']['direction'] = 'u'
        with self.assertRaisesRegex(pfs.LayoutError, 'direction mismatch'):
            pfs.apply_layout(self.raw, self.ref, p)

    def test_nonorthogonal_path_rejected(self):
        p = plan(); p['streams']['WATER.IN']['path'] = [[0, -2], [.6, .4]]
        with self.assertRaisesRegex(pfs.LayoutError, 'Nonorthogonal'):
            pfs.apply_layout(self.raw, self.ref, p)

    def test_overlapping_streams_rejected(self):
        p = plan(); p['streams']['WATER.IN'].update(path=[[-3, 2], [.5, 2]])
        with self.assertRaisesRegex(pfs.LayoutError, 'overlap'):
            pfs.apply_layout(self.raw, self.ref, p)

    def test_coincident_blocks_rejected(self):
        p = plan(); p['blocks']['HX.A']['at'] = [4, 0]
        with self.assertRaisesRegex(pfs.LayoutError, 'Coincident'):
            pfs.apply_layout(self.raw, self.ref, p)

    def test_genuine_report_card_omission_rejected(self):
        with self.assertRaisesRegex(pfs.LayoutError, 'complete Export4'):
            pfs.apply_layout(self.raw, self.ref.replace(b'STREAM-REPOR MOLEFLOW\n', b''), plan())

    def test_physical_tolerance_change_rejected(self):
        with self.assertRaises(pfs.LayoutError):
            pfs.apply_layout(self.raw.replace(b'1.000E-6', b'1.000E-5'), self.ref, plan())

    def test_numeric_card_spelling_does_not_relax_value(self):
        self.assertEqual(pfs.physical_tokens(self.ref), pfs.physical_tokens(self.ref.replace(b'1.000E-6', b'0.000001')))
        self.assertNotEqual(pfs.physical_tokens(self.ref), pfs.physical_tokens(self.ref.replace(b'1.000E-6', b'0.00000101')))
        self.assertEqual(pfs.physical_tokens(b'PARAM PRES=8.1250 ID=A-2'), pfs.physical_tokens(b'PARAM PRES=8.125 ID=A-2'))
        self.assertNotEqual(pfs.physical_tokens(b'ID=A-2'), pfs.physical_tokens(b'ID=A-2.0'))

    def test_numeric_values_never_context_round(self):
        self.assertNotEqual(pfs.physical_tokens(b'PRES=1.000000000000000000000000000001'), pfs.physical_tokens(b'PRES=1.0'))
        self.assertEqual(pfs.physical_tokens(b'PRES=1.0000000000000000000000000000010'), pfs.physical_tokens(b'PRES=1.000000000000000000000000000001'))
        self.assertEqual(pfs.physical_tokens(b'X=1.2300D-199'), pfs.physical_tokens(b'X=123E-201'))

    def test_keyed_quoted_strings_are_opaque(self):
        for quote in [b'"', b"'"]:
            self.assertNotEqual(pfs.physical_tokens(b'TITLE='+quote+b'case 2.000'+quote), pfs.physical_tokens(b'TITLE='+quote+b'case 2'+quote))
            self.assertNotEqual(pfs.physical_tokens(b'TITLE='+quote+b'case  2'+quote), pfs.physical_tokens(b'TITLE='+quote+b'case 2'+quote))
        self.assertNotEqual(pfs.physical_tokens(b'TITLE="case ""nested 2.000"""'), pfs.physical_tokens(b'TITLE="case ""nested 2"""'))
        self.assertEqual(pfs.physical_tokens(b'TITLE="case 2.000" X=2.000'), pfs.physical_tokens(b'TITLE="case 2.000" X=2'))

    def test_unterminated_quote_rejected(self):
        with self.assertRaisesRegex(pfs.LayoutError, 'Unterminated'):
            pfs.physical_tokens(b'TITLE="case 2.000')

    def test_immediate_backtracking_rejected(self):
        with self.assertRaisesRegex(pfs.LayoutError, 'backtracking'):
            pfs.validate_path([[0, 0], [2, 0], [1, 0]], 'invented')

    def test_same_direction_consecutive_segments_supported(self):
        self.assertEqual(pfs.validate_path([[0, 0], [1, 0], [2, 0]], 'invented'), [(0, 0), (1, 0), (2, 0)])

    def test_endpoint_mutation_readback_rejected(self):
        output = pfs.apply_layout(self.raw, self.ref, plan())
        bad = output.replace(b';t l 0.500000000 2.000000000', b';t l 0.600000000 2.000000000')
        with self.assertRaises(pfs.LayoutError):
            pfs.verify_layout(output, bad, self.ref)

    def test_d_requires_c_zero(self):
        with self.assertRaisesRegex(pfs.LayoutError, 'requires witnessed'):
            pfs.parse_route('r r 0 0 0\nt r 1 0 0\n$ D .5 0\n$ C 1 0\n$ $ 0.0 0.0\n')

    def test_elink_must_be_export18_final_boundary(self):
        with self.assertRaisesRegex(pfs.LayoutError, 'final genuine'):
            pfs.apply_layout(self.raw + b'PARAM EXTRA=2\n', self.ref, plan())

    def test_output_cannot_overwrite_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            src = Path(folder)/'synthetic.inp'; src.write_bytes(self.raw)
            self.assertEqual(pfs.main(['inspect', str(src), '--output', str(src)]), 2)
            self.assertEqual(src.read_bytes(), self.raw)


if __name__ == '__main__':
    unittest.main()
