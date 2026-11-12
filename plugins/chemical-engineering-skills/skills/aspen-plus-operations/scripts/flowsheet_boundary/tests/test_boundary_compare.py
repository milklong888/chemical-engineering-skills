# SPDX-License-Identifier: MIT
import copy
import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from flowsheet_boundary.boundary_compare import compare_retained_streams, utility_totals


def rows(key, value, unit):
    path = "\\Data\\Streams\\S\\Output\\" + key
    return [{"path": path, "Value": 1, "UnitString": unit}, {"path": path + "\\MIXED", "Value": value, "UnitString": unit}]


def fixture():
    s = {key: rows(key, value, unit) for key, value, unit in [("TEMP_OUT", 30, "C"), ("PRES_OUT", 2, "bar"), ("MASSFLMX", 10, "kg/hr"), ("VFRAC_OUT", 0, "")]}
    s["MASSFLOW"] = [{"path": r"\Data\Streams\S\Output\MASSFLOW\MIXED\A", "Value": 10, "UnitString": "kg/hr"}]
    b = {key: {field: [{"path": "\\Data\\Blocks\\" + key + "\\Output\\" + field, "Value": val, "UnitString": unit}]} for key, field, val, unit in [("HT", "QCALC", 1, "Gcal/hr"), ("CL", "QCALC", -0.5, "Gcal/hr"), ("HX", "HX_DUTY", 3, "Gcal/hr"), ("K", "WNET", 7, "kW")]}
    return {"streams": {"S": s}, "blocks": b}


class CompareTests(unittest.TestCase):
    def test_leaf_not_container(self):
        x = fixture(); self.assertEqual(compare_retained_streams(x, copy.deepcopy(x), ["S"]), [])
    def test_actual_component_difference(self):
        a = fixture(); b = copy.deepcopy(a); b["streams"]["S"]["MASSFLOW"][0]["Value"] = 9
        delta = compare_retained_streams(a, b, ["S"])
        self.assertEqual(delta, [{"stream": "S", "field": "MASSFLOW.A", "before": 10, "after": 9}])
    def test_temperature_boundary_change_is_visible(self):
        a = fixture(); b = copy.deepcopy(a); b["streams"]["S"]["TEMP_OUT"][1]["Value"] = 70
        self.assertEqual(compare_retained_streams(a, b, ["S"])[0]["field"], "TEMP_OUT")
    def test_missing_component_is_not_equality(self):
        a = fixture(); b = copy.deepcopy(a); b["streams"]["S"]["MASSFLOW"] = []
        with self.assertRaises(ValueError): compare_retained_streams(a, b, ["S"])
    def test_nonfinite_rejected(self):
        a = fixture(); a["streams"]["S"]["TEMP_OUT"][1]["Value"] = math.inf
        with self.assertRaises(ValueError): compare_retained_streams(a, a, ["S"])
    def test_gcal_uses_aspen_cal_and_internal_hx_excluded(self):
        out = utility_totals(fixture(), external_heat_fields=[("HT", "QCALC"), ("CL", "QCALC")], shaft_blocks=["K"])
        self.assertEqual(out["external_heating_kW"], 1163)
        self.assertEqual(out["external_cooling_kW"], 581.5)
        self.assertEqual(out["shaft_kW"], 7)
        self.assertTrue(out["boundary_review_required"])
    def test_duplicate_heat_not_counted_twice(self):
        with self.assertRaises(ValueError): utility_totals(fixture(), external_heat_fields=[("HT", "QCALC"), ("HT", "QCALC")], shaft_blocks=[])
    def test_wrong_unit_rejected(self):
        x = fixture(); x["blocks"]["K"]["WNET"][0]["UnitString"] = "hp"
        with self.assertRaises(ValueError): utility_totals(x, external_heat_fields=[], shaft_blocks=["K"])
    def test_container_duty_value_one_is_rejected(self):
        x = fixture(); x["blocks"]["HT"]["QCALC"].append({"path": r"\Data\Blocks\HT\Output\QCALC\INLET\1", "Value": 0.02, "UnitString": "Gcal/hr"})
        with self.assertRaises(ValueError): utility_totals(x, external_heat_fields=[("HT", "QCALC")], shaft_blocks=[])
    def test_component_container_is_rejected(self):
        x = fixture(); x["streams"]["S"]["MASSFLOW"].append({"path": r"\Data\Streams\S\Output\MASSFLOW\MIXED\A\PHASE", "Value": 10, "UnitString": "kg/hr"})
        with self.assertRaises(ValueError): compare_retained_streams(x, x, ["S"])


if __name__ == "__main__": unittest.main()
