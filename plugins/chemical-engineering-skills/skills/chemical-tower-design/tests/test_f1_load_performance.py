"""Analytic oracle and negative-evidence tests; no Aspen, chart weights or defaults."""
import copy
import hashlib
import importlib.util
import math
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/f1_load_performance.py"
spec = importlib.util.spec_from_file_location("f1_boundary_test", SCRIPT)
f1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f1)


def fixture():
    source = Path(__file__).resolve()
    metadata = {"path": str(source), "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "locator": "fixture: independently constructed affine bounds, not engineering data", "status": "synthetic_mathematical_test_only",
        "equipment_tag": "SYNTHETIC-F1", "case_id": "analytic-oracle"}
    return {"schema_version": "f1-load-performance-boundaries-1.0", "tray_family": "F1_float_valve",
        "equipment_tag": "SYNTHETIC-F1", "case_id": "analytic-oracle", "geometry_identity": "synthetic-no-real-geometry",
        "applicability": "Mathematical regression only; no equipment selection or physical correlation claim",
        "boundary_inclusive": True, "flow_unit": "m3/s", "flow_basis": "actual_at_operating_state",
        "interpolation_model": "piecewise_linear", "operating_point": {"liquid": 2.0, "vapor": 4.0},
        "liquid_limits": {"minimum": 1.0, "maximum": 10.0},
        "boundaries": {"weeping": [[1.,2.],[10.,2.]], "entrainment": [[1.,20.],[10.,20.]], "flooding": [[1.,12.],[10.,12.]]},
        "sources": {name: dict(metadata) for name in f1.SOURCES}}


class F1BoundariesTests(unittest.TestCase):
    def test_analytic_connected_range_and_elasticity(self):
        result = f1.evaluate(fixture())
        interval = result["feasible_ray_intervals"][0]
        self.assertEqual((interval["liquid_min"], interval["liquid_max"]), (1.,6.))
        self.assertEqual(result["operating_elasticity"], 6.)
        self.assertTrue(result["operating_point_feasible_on_supplied_boundaries"])
        self.assertFalse(result["formal_engineering_acceptance"])

    def test_real_flood_constraint_not_entrainment_substitute(self):
        payload = fixture()
        payload["operating_point"] = {"liquid":5., "vapor":6.}
        payload["boundaries"]["entrainment"] = [[1.,10.],[10.,10.]]
        payload["boundaries"]["flooding"] = [[1.,4.],[10.,4.]]
        result = f1.evaluate(payload)
        self.assertFalse(result["constraint_passes"]["flooding"])
        self.assertTrue(result["constraint_passes"]["entrainment"])
        self.assertIsNone(result["operating_elasticity"])

    def test_no_intersection_uses_actual_liquid_limit(self):
        payload=fixture()
        payload["boundaries"]["flooding"]=[[1.,1000.],[10.,1000.]]
        payload["boundaries"]["entrainment"]=[[1.,1000.],[10.,1000.]]
        result=f1.evaluate(payload)
        self.assertEqual(result["feasible_ray_intervals"][0]["liquid_max"],10.)
        self.assertEqual(result["operating_elasticity"],10.)

    def test_empty_feasible_domain_not_positive_elasticity(self):
        payload=fixture()
        payload["boundaries"]["weeping"]=[[1.,30.],[10.,30.]]
        result=f1.evaluate(payload)
        self.assertEqual(result["feasible_ray_intervals"],[])
        self.assertIsNone(result["operating_elasticity"])

    def test_disconnected_domain_uses_only_operating_component(self):
        payload=fixture()
        payload["operating_point"]={"liquid":5.,"vapor":10.}
        payload["boundaries"]["flooding"]=[[1.,12.],[3.,1.],[5.,12.],[10.,12.]]
        result=f1.evaluate(payload)
        self.assertEqual(len(result["feasible_ray_intervals"]),2)
        self.assertEqual(result["operating_interval_index"],1)
        self.assertLess(result["operating_elasticity"],2.)

    def test_strict_touching_point_does_not_join_open_intervals(self):
        curves={"weeping":[[1.,0.],[3.,0.]],"entrainment":[[1.,10.],[3.,10.]],"flooding":[[1.,4.],[2.,2.],[3.,4.]]}
        strict,_=f1.feasible_intervals(curves,1.,3.,1.,False)
        inclusive,_=f1.feasible_intervals(curves,1.,3.,1.,True)
        self.assertEqual(len(strict),2)
        self.assertEqual(len(inclusive),1)

    def test_equal_boundary_policy_is_explicit(self):
        payload=fixture(); payload["operating_point"]={"liquid":6.,"vapor":12.}
        self.assertTrue(f1.evaluate(payload)["operating_point_feasible_on_supplied_boundaries"])
        payload["boundary_inclusive"]=False
        self.assertFalse(f1.evaluate(payload)["operating_point_feasible_on_supplied_boundaries"])
        del payload["boundary_inclusive"]
        with self.assertRaises(ValueError): f1.evaluate(payload)

    def test_unit_conversion_invariance(self):
        payload=fixture(); payload["flow_unit"]="m3/h"
        payload["operating_point"]={key:value*3600 for key,value in payload["operating_point"].items()}
        payload["liquid_limits"]={key:value*3600 for key,value in payload["liquid_limits"].items()}
        payload["boundaries"]={key:[[x*3600,y*3600] for x,y in points] for key,points in payload["boundaries"].items()}
        self.assertAlmostEqual(f1.evaluate(payload)["operating_elasticity"],6.)
        payload["flow_basis"]="standard_volume"
        with self.assertRaises(ValueError): f1.evaluate(payload)

    def test_nonfinite_zero_wrong_domain_duplicate_x_rejected(self):
        for change in ("nan","zero","outside","duplicate"):
            payload=fixture()
            if change=="nan": payload["boundaries"]["flooding"][0][1]=math.nan
            if change=="zero": payload["operating_point"]["liquid"]=0
            if change=="outside": payload["operating_point"]["liquid"]=11
            if change=="duplicate": payload["boundaries"]["flooding"][1][0]=1
            with self.subTest(change=change),self.assertRaises(ValueError): f1.evaluate(payload)

    def test_source_hash_and_other_case_rejected(self):
        for change in ("hash","case","missing"):
            payload=fixture()
            if change=="hash":payload["sources"]["flooding"]["sha256"]="0"*64
            if change=="case":payload["sources"]["flooding"]["case_id"]="OTHER"
            if change=="missing":del payload["sources"]["weeping"]
            with self.subTest(change=change),self.assertRaises(ValueError): f1.evaluate(payload)

    def test_existing_output_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/"existing.json"; path.write_text("keep",encoding="utf-8")
            with self.assertRaises(ValueError):f1._new_output(path)
            self.assertEqual(path.read_text(encoding="utf-8"),"keep")


if __name__=="__main__":unittest.main(verbosity=2)
