# SPDX-License-Identifier: MIT
"""Offline synthetic tests for native_results."""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from flowsheet_boundary.native_results import component_flows, heatx_profile, leaf_index, mixed_scalar


OUT = r"\Data\Blocks\HX\Output"


def row(path, value, unit=""):
    return {"path": path, "Value": value, "UnitString": unit}


def profile_rows():
    # Deliberately reverse source order and include parent containers whose
    # Value=1 must never be consumed as a physical data point.
    rows = [
        row(OUT + r"\TEMP_HOT", 1, "C"),
        row(OUT + r"\TEMP_CLD", 1, "C"),
        row(OUT + r"\DUTY_HOT", 1, "Gcal/hr"),
        row(OUT + r"\DUTY_CLD", 1, "Gcal/hr"),
    ]
    values = {
        7: (80.0, 85.0, 0.02, 0.02),  # reverse approach is retained (-5 K)
        2: (100.0, 90.0, 0.01, 0.01),
    }
    for point_id, (th, tc, qh, qc) in values.items():
        for name, value, unit in [
            ("TEMP_HOT", th, "C"), ("TEMP_CLD", tc, "C"),
            ("DUTY_HOT", qh, "Gcal/hr"), ("DUTY_CLD", qc, "Gcal/hr"),
        ]:
            rows.append(row(OUT + f"\\{name}\\INLET\\{point_id}", value, unit))
    return rows


class LeafIndexTests(unittest.TestCase):
    def test_ignores_containers_and_keeps_only_leaves(self):
        rows = [row(r"\Data\C1", 1), row(r"\Data\C1\MIXED", 1), row(r"\Data\C1\MIXED\A", 3)]
        self.assertEqual(set(leaf_index(rows)), {r"\Data\C1\MIXED\A"})

    def test_repeated_path_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate result path"):
            leaf_index([row(r"\Data\C1", 1), row(r"\Data\C1", 2)])

    def test_mixed_scalar_uses_exact_mixed_leaf_not_container(self):
        rows = [row(r"\Data\Streams\S1\Output\TEMP_OUT", 1, "C"), row(r"\Data\Streams\S1\Output\TEMP_OUT\MIXED", 25.5, "C")]
        self.assertEqual(mixed_scalar(rows, r"\Data\Streams\S1\Output\TEMP_OUT"), 25.5)

    def test_missing_mixed_leaf_fails(self):
        with self.assertRaisesRegex(ValueError, "missing mixed scalar leaf"):
            mixed_scalar([row(r"\Data\S\TEMP", 1)], r"\Data\S\TEMP")

    def test_component_flows_only_immediate_component_leaves(self):
        base = r"\Data\Streams\S1\Output\MASSFLOW"
        rows = [
            row(base, 1), row(base + r"\MIXED", 1),
            row(base + r"\MIXED\A", 3.0, "kg/hr"),
            row(base + r"\MIXED\B", 4.0, "kg/hr"),
            row(base + r"\MIXED\SUB\DEEP", 9.0, "kg/hr"),
        ]
        self.assertEqual(component_flows(rows, base), {"A": 3.0, "B": 4.0})


class HeatxProfileTests(unittest.TestCase):
    def test_orders_by_point_id_pairs_by_id_and_preserves_reverse_delta(self):
        out = heatx_profile(profile_rows(), OUT)
        self.assertEqual(out["point_ids"], [2, 7])
        self.assertEqual([p["point_id"] for p in out["points"]], [2, 7])
        self.assertEqual(out["points"][0]["duty_grid_kW"], 11.63)
        self.assertEqual(out["minimum_approach_K"], -5.0)
        self.assertEqual(out["minimum_approach_point_id"], 7)
        # Input duty signs are reported without taking absolute values.
        self.assertEqual(out["points"][1]["duty_hot_Gcal_hr"], 0.02)
        self.assertEqual(out["points"][1]["duty_cold_Gcal_hr"], 0.02)

    def test_empty_or_missing_array_fails(self):
        rows = [r for r in profile_rows() if "DUTY_CLD" not in r["path"]]
        with self.assertRaisesRegex(ValueError, "missing DUTY_CLD"):
            heatx_profile(rows, OUT)

    def test_point_id_set_mismatch_fails(self):
        rows = profile_rows()
        rows = [r for r in rows if r["path"] != OUT + r"\TEMP_CLD\INLET\7"]
        with self.assertRaisesRegex(ValueError, "point IDs for TEMP_CLD differ"):
            heatx_profile(rows, OUT)

    def test_container_value_one_is_not_accepted_as_a_data_point(self):
        rows = [row(OUT + r"\TEMP_HOT", 1, "C"), row(OUT + r"\TEMP_CLD", 1, "C"), row(OUT + r"\DUTY_HOT", 1, "Gcal/hr"), row(OUT + r"\DUTY_CLD", 1, "Gcal/hr")]
        with self.assertRaisesRegex(ValueError, "empty or missing TEMP_HOT"):
            heatx_profile(rows, OUT)

    def test_non_finite_value_fails(self):
        rows = profile_rows()
        target = OUT + r"\TEMP_HOT\INLET\2"
        for item in rows:
            if item["path"] == target:
                item["Value"] = math.inf
        with self.assertRaisesRegex(ValueError, "non-finite value"):
            heatx_profile(rows, OUT)

    def test_wrong_temperature_or_duty_units_fail(self):
        for target, unit, message in [
            (OUT + r"\TEMP_HOT\INLET\2", "K", "must have unit C"),
            (OUT + r"\DUTY_CLD\INLET\2", "kW", "must have unit Gcal/hr"),
        ]:
            rows = profile_rows()
            for item in rows:
                if item["path"] == target:
                    item["UnitString"] = unit
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, message):
                heatx_profile(rows, OUT)

    def test_hot_cold_duty_grid_mismatch_fails(self):
        rows = profile_rows()
        for item in rows:
            if item["path"] == OUT + r"\DUTY_CLD\INLET\7":
                item["Value"] += 1.01e-10
        with self.assertRaisesRegex(ValueError, "duty grid mismatch"):
            heatx_profile(rows, OUT)

    def test_duplicate_point_path_fails(self):
        rows = profile_rows()
        rows.append(row(OUT + r"\TEMP_HOT\INLET\2", 100, "C"))
        with self.assertRaisesRegex(ValueError, "duplicate result path"):
            heatx_profile(rows, OUT)

    def test_non_numeric_value_fails(self):
        rows = profile_rows()
        for item in rows:
            if item["path"] == OUT + r"\DUTY_HOT\INLET\2":
                item["Value"] = "0.01"
        with self.assertRaisesRegex(ValueError, "non-numeric value"):
            heatx_profile(rows, OUT)


if __name__ == "__main__":
    unittest.main()
