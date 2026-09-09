"""Synthetic logic tests only; none are current-project engineering inputs."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from backends.process.pressure import (liquid_pipe_loss, series_pressure, compressor_train,
                                      equal_ratio_initializer, parallel_distribution)
from backends.process.feedback import build_plan, audit_replay, affected_consumers
from expert_cli import equipment


class PressureTests(unittest.TestCase):
    def test_laminar_known_solution(self):
        args = dict(density_kg_m3=1000, viscosity_pa_s=0.1, flow_m3_s=0.001,
                    diameter_m=0.1, length_m=10, minor_k=2, elevation_change_m=2)
        result = liquid_pipe_loss(**args)
        import math
        expected = 128 * args["viscosity_pa_s"] * args["length_m"] * args["flow_m3_s"] / (math.pi * args["diameter_m"] ** 4)
        self.assertAlmostEqual(result["friction_pa"], expected)
        self.assertAlmostEqual(result["static_pressure_pa"], 19613.3)

    def test_no_hidden_turbulent_correlation(self):
        with self.assertRaisesRegex(ValueError, "Darcy"):
            liquid_pipe_loss(density_kg_m3=1000, viscosity_pa_s=.001, flow_m3_s=.01,
                             diameter_m=.1, length_m=10, minor_k=0, elevation_change_m=0)

    def test_zero_flow(self):
        result = liquid_pipe_loss(density_kg_m3=1000, viscosity_pa_s=.001, flow_m3_s=0,
                                  diameter_m=.1, length_m=10, minor_k=0, elevation_change_m=-2)
        self.assertEqual(result["irreversible_loss_pa"], 0)
        self.assertLess(result["inlet_minus_outlet_pressure_pa"], 0)

    def test_series_losses_are_added(self):
        result = series_pressure(500000, [10000, 2000, 8000])
        self.assertEqual(result["outlet_pressure_pa"], 480000)
        self.assertEqual(result["stages"][1]["inlet_pressure_pa"], 490000)

    def test_impossible_pressure_rejected(self):
        with self.assertRaises(ValueError):
            series_pressure(10000, [20000])

    def test_compressor_losses_change_initializer(self):
        ideal = equal_ratio_initializer(inlet_pressure_pa=100000, delivery_pressure_pa=900000,
                                        after_losses_pa=[0, 0])
        losses = equal_ratio_initializer(inlet_pressure_pa=100000, delivery_pressure_pa=900000,
                                         after_losses_pa=[10000, 20000])
        self.assertAlmostEqual(ideal["common_pressure_ratio"], 3)
        self.assertGreater(losses["common_pressure_ratio"], 3)
        self.assertAlmostEqual(losses["delivery_pressure_pa"], 900000)
        self.assertEqual(losses["status"], "INITIAL_GUESS_NOT_OPTIMUM")

    def test_compressor_each_stage(self):
        result = compressor_train(inlet_pressure_pa=100000, mass_flow_kg_s=1,
            cp_j_kg_k=1000, heat_capacity_ratio=1.4, property_basis="synthetic ideal gas",
            stages=[dict(suction_temperature_k=300, isentropic_efficiency=.8, pressure_ratio=3,
                         after_loss_pa=10000, phase="vapor"),
                    dict(suction_temperature_k=310, isentropic_efficiency=.75, pressure_ratio=3,
                         after_loss_pa=20000, phase="vapor")])
        self.assertEqual(result["stages"][1]["suction_pressure_pa"], 290000)
        self.assertEqual(result["delivery_pressure_pa"], 850000)
        self.assertGreater(result["gas_power_w"], 0)
        self.assertEqual(result["status"], "IDEAL_GAS_SCREENING_NOT_RATING")

    def test_wet_compression_is_local_boundary(self):
        with self.assertRaisesRegex(ValueError, "wet"):
            compressor_train(inlet_pressure_pa=100000, mass_flow_kg_s=1,
                cp_j_kg_k=1000, heat_capacity_ratio=1.4, property_basis="synthetic",
                stages=[dict(suction_temperature_k=300, isentropic_efficiency=.8,
                             pressure_ratio=3, after_loss_pa=0, phase="vapor-liquid")])

    def test_parallel_unequal_split_common_dp(self):
        result = parallel_distribution(30, [
            dict(id="A", source="synthetic curve A", points=[[0, 0], [20, 10000]]),
            dict(id="B", source="synthetic curve B", points=[[0, 0], [10, 10000]])], flow_unit="m3/h")
        self.assertAlmostEqual(result["common_pressure_difference_pa"], 10000)
        self.assertAlmostEqual(result["branches"][0]["flow"], 20)
        self.assertAlmostEqual(result["branches"][1]["flow"], 10)
        self.assertAlmostEqual(result["flow_residual"], 0)

    def test_parallel_does_not_extrapolate(self):
        with self.assertRaises(ValueError):
            parallel_distribution(100, [
                dict(id="A", source="synthetic", points=[[0, 0], [20, 10000]]),
                dict(id="B", source="synthetic", points=[[0, 0], [10, 10000]])], flow_unit="m3/h")

    def test_nan_and_bool_rejected(self):
        for value in (True, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                series_pressure(value, [1])


class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="chemical-feedback-test-")
        self.root = Path(self.temporary.name)
        self.response = {"result": {"model_decision": {"model_status": "type_screening"},
            "equipment_tag": "E1", "normalized_input": {"heat_transfer_area_m2": 2000, "flow_m3_h": 100},
            "match": {"family_id": "family_fixed_tubesheet_exchanger"}}}
        self.export = {"schema": "equipment-process-canonical-export-v1", "case_id": "SYNTHETIC-NOT-A-PROJECT", "run_id": "SYNTHETIC-CURRENT",
            "equipment": {"E1": {"family_id": "family_fixed_tubesheet_exchanger", "values": {"heat_transfer_area_m2": 2000, "flow_m3_h": 100}, "units": {"heat_transfer_area_m2": "m2", "flow_m3_h": "m3/h"}}}}
        self.context = {"case_id": "SYNTHETIC-NOT-A-PROJECT", "run_id": "SYNTHETIC-CURRENT",
            "source_export": self.put("export.json", self.export),
            "authority": self.put("authority.json", {"schema": "equipment-process-authority-v1", "case_id": "SYNTHETIC-NOT-A-PROJECT", "run_id": "SYNTHETIC-CURRENT", "required_method": "synthetic contract",
                "acceptance_criteria": ["strict zero errors warnings"]}),
            "topology": {"nodes": ["P1", "E1", "C1"], "edges": [["P1", "E1"], ["E1", "C1"]]}}

    def tearDown(self):
        self.temporary.cleanup()

    def put(self, name, value):
        data = json.dumps(value).encode()
        (self.root / name).write_bytes(data)
        return {"path": name, "sha256": hashlib.sha256(data).hexdigest().upper()}

    def constraint(self, quantity="area", value=2000, limit=1000):
        field = {"area": "heat_transfer_area_m2", "flow": "flow_m3_h"}.get(quantity, quantity)
        unit = {"heat_transfer_area_m2": "m2", "flow_m3_h": "m3/h"}[field]
        self.export["equipment"]["E1"]["values"][field] = value
        self.response["result"]["normalized_input"][field] = value
        actual = self.put("actual.json", self.export)
        self.context["source_export"] = actual
        maximum = self.put("limit.json", {"schema": "equipment-process-limit-v1", "quantity": field,
            "value": limit, "unit": unit, "source_id": "SYNTHETIC-NOT-A-STANDARD", "version": "TEST_ONLY", "locator": "test row",
            "applicability": {"equipment_id": "E1", "family_id": "family_fixed_tubesheet_exchanger"}})
        row = {"equipment_id": "E1", "status": "verified_applicable", "quantity": quantity,
               "unit": unit, "applicability": "synthetic test only", "relation": "max",
               "value": value, "limit": limit,
               "value_source": {**actual, "pointer": f"/equipment/E1/values/{field}"},
               "limit_source": {**maximum, "pointer": "/value"}}
        ref = self.put("constraint.json", row)
        self.context["constraint_evidence"] = {"E1": [ref]}

    def test_catalog_gap_does_not_split(self):
        result = build_plan(self.response, self.context, self.root)
        self.assertIsNone(result["equipment"][0]["revision"])
        self.assertFalse(result["engineering_accepted"])

    def test_real_limit_proposes_series_and_stales_component(self):
        self.constraint()
        result = build_plan(self.response, self.context, self.root)
        record = result["equipment"][0]
        self.assertEqual(record["revision"]["preferred_route"], "exchanger_series")
        self.assertEqual(record["affected_consumers"]["equipment"], ["C1", "E1", "P1"])
        self.assertIsNone(record["revision"]["unit_count"])
        self.assertEqual(record["revision"]["initial_count_bounds"][0]["count"], 2)

    def test_series_does_not_fix_flow_limit(self):
        self.constraint(quantity="flow", value=100, limit=50)
        record = build_plan(self.response, self.context, self.root)["equipment"][0]
        self.assertTrue(record["revision"]["cannot_claim_limit_resolved"])

    def test_pressure_calculation_is_connected_to_feedback(self):
        self.context["configuration_checks"] = {"E1": [{"method": "series_pressure",
            "input_basis": "Synthetic same-side losses, Pa, not EDR rating",
            "inputs": {"inlet_pressure_pa": 500000, "losses_pa": [20000, 30000]}}]}
        row = build_plan(self.response, self.context, self.root)["equipment"][0]
        self.assertEqual(row["configuration_calculations"][0]["result"]["outlet_pressure_pa"], 450000)
        self.assertFalse(row["configuration_calculations"][0]["model_implementation_verified"])

    def test_forged_constraint_value_rejected(self):
        self.constraint()
        self.put("actual.json", {"value": 100})
        with self.assertRaisesRegex(ValueError, "hash"):
            build_plan(self.response, self.context, self.root)

    def test_source_comparison_not_just_label(self):
        self.constraint(value=500, limit=1000)
        result = build_plan(self.response, self.context, self.root)
        self.assertIsNone(result["equipment"][0]["revision"])

    def test_replay_wrong_plan_rejected(self):
        plan = build_plan(self.response, self.context, self.root)
        with self.assertRaisesRegex(ValueError, "another"):
            audit_replay(plan, {"plan_sha256": "wrong", "case_id": self.context["case_id"]}, self.root)

    def test_naked_pass_not_complete(self):
        plan = build_plan(self.response, self.context, self.root)
        candidate = self.put("candidate.json", {"synthetic": "not Aspen"})
        replay = {"plan_sha256": plan["plan_sha256"], "case_id": self.context["case_id"],
                  "candidate": candidate, "source_export": self.context["source_export"],
                  "gates": {}}
        result = audit_replay(plan, replay, self.root)
        self.assertFalse(result["evidence_chain_complete"])
        self.assertEqual(len(result["failed_gates"]), 11)

    def test_original_backend_is_actually_called(self):
        result = equipment({"schema": "equipment-design-agent-request-v1", "request_id": "SYNTHETIC",
            "operation": "manual_match", "payload": {"selection_id": "family:family_fixed_tubesheet_exchanger",
            "values": {"equipment_tag": "E1", "heat_duty_kw": 1000, "overall_u_w_m2k": 500,
                       "lmtd_k": 40, "lmtd_correction_factor": 1}}})
        self.assertEqual(result["backend_exit_code"], 0)
        plan = build_plan(result["response"], self.context, self.root)
        self.assertEqual(len(plan["equipment"]), 1)
        self.assertTrue(plan["equipment"][0]["legacy_analysis"]["calculation_trace"])


if __name__ == "__main__":
    unittest.main()
