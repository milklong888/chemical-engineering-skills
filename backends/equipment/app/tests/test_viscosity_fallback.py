from __future__ import annotations

import math
import unittest

import viscosity_fallback


SOURCE = {
    "source_id": "TEST_SOURCE",
    "citation": "Synthetic regression coefficient record",
    "sha256": "A" * 64,
}


class ViscosityFallbackTests(unittest.TestCase):
    def test_vapor_uses_sutherland_and_wilke_with_warning(self) -> None:
        records = {
            "A": {
                "molecular_weight_kg_kmol": 28.0,
                "source": SOURCE,
                "vapor": {
                    "model": "SUTHERLAND",
                    "mu_ref_pa_s": 1.70e-5,
                    "temperature_ref_k": 300.0,
                    "sutherland_k": 110.0,
                    "temperature_min_k": 200.0,
                    "temperature_max_k": 600.0,
                },
            },
            "B": {
                "molecular_weight_kg_kmol": 44.0,
                "source": SOURCE,
                "vapor": {
                    "model": "SUTHERLAND",
                    "mu_ref_pa_s": 1.45e-5,
                    "temperature_ref_k": 300.0,
                    "sutherland_k": 160.0,
                    "temperature_min_k": 200.0,
                    "temperature_max_k": 600.0,
                },
            },
        }
        result = viscosity_fallback.estimate_stream_viscosity(
            phase="vapor",
            temperature_k=350.0,
            composition=[
                {"component_id": "A", "fraction": 0.3, "basis": "mole_fraction"},
                {"component_id": "B", "fraction": 0.7, "basis": "mole_fraction"},
            ],
            correlation_records=records,
        )
        self.assertEqual(result["status"], "PASS_WITH_WARNING")
        self.assertEqual(result["mixing_rule"], "WILKE_GAS_MIXTURE")
        self.assertGreater(result["dynamic_viscosity_mpa_s"], 0.0)
        self.assertEqual(result["origin"], "INTERNAL_CORRELATION_ESTIMATE")
        self.assertFalse(result["formal_design_evidence"])
        self.assertIn(
            "W_VISCOSITY_NOT_ASPEN_EXTRACTED",
            result["warning_codes"],
        )
        self.assertIn(
            "W_CORRELATION_SOURCE_ASSET_HASH_NOT_LOCALLY_VERIFIED",
            result["warning_codes"],
        )
        self.assertEqual(
            result["pure_component_calculations"][0]["source"]["verification_status"],
            "DECLARED_SOURCE_HASH_FORMAT_VALID_ONLY",
        )
        self.assertEqual(
            result["result_sha256"],
            viscosity_fallback.canonical_sha256({
                key: value
                for key, value in result.items()
                if key != "result_sha256"
            }),
        )

    def test_liquid_uses_mole_log_mixing(self) -> None:
        records = {
            "LIGHT": {
                "molecular_weight_kg_kmol": 20.0,
                "source": SOURCE,
                "liquid": {
                    "model": "ARRHENIUS_TWO_CONSTANT",
                    "A": 1.0e-5,
                    "B_K": 1000.0,
                    "temperature_min_k": 250.0,
                    "temperature_max_k": 450.0,
                },
            },
            "HEAVY": {
                "molecular_weight_kg_kmol": 100.0,
                "source": SOURCE,
                "liquid": {
                    "model": "ARRHENIUS_TWO_CONSTANT",
                    "A": 2.0e-5,
                    "B_K": 1400.0,
                    "temperature_min_k": 250.0,
                    "temperature_max_k": 450.0,
                },
            },
        }
        result = viscosity_fallback.estimate_stream_viscosity(
            phase="liquid",
            temperature_k=330.0,
            composition=[
                {"component_id": "LIGHT", "fraction": 0.5, "basis": "mole_fraction"},
                {"component_id": "HEAVY", "fraction": 0.5, "basis": "mole_fraction"},
            ],
            correlation_records=records,
        )
        self.assertEqual(result["status"], "PASS_WITH_WARNING")
        self.assertEqual(
            result["mixing_rule"],
            "GRUNBERG_NISSAN_IDEAL_MOLE_LOG_LIQUID",
        )
        self.assertAlmostEqual(
            result["mixing_fractions"]["LIGHT"],
            0.5,
        )
        self.assertAlmostEqual(
            result["mixing_fractions"]["HEAVY"],
            0.5,
        )
        pure = [
            row["calculation"]["dynamic_viscosity_pa_s"]
            for row in result["pure_component_calculations"]
        ]
        expected = math.exp(
            0.5 * math.log(pure[0])
            + 0.5 * math.log(pure[1])
        )
        self.assertAlmostEqual(result["dynamic_viscosity_pa_s"], expected)
        self.assertIn(
            "W_GRUNBERG_NISSAN_BINARY_INTERACTION_PARAMETERS_NOT_APPLIED",
            result["warning_codes"],
        )

    def test_liquid_mass_basis_is_converted_to_mole_fractions(self) -> None:
        records = {
            "LIGHT": {
                "molecular_weight_kg_kmol": 20.0,
                "source": SOURCE,
                "liquid": {
                    "model": "ARRHENIUS_TWO_CONSTANT",
                    "A": 1.0e-5,
                    "B_K": 1000.0,
                    "temperature_min_k": 250.0,
                    "temperature_max_k": 450.0,
                },
            },
            "HEAVY": {
                "molecular_weight_kg_kmol": 100.0,
                "source": SOURCE,
                "liquid": {
                    "model": "ARRHENIUS_TWO_CONSTANT",
                    "A": 2.0e-5,
                    "B_K": 1400.0,
                    "temperature_min_k": 250.0,
                    "temperature_max_k": 450.0,
                },
            },
        }
        result = viscosity_fallback.estimate_stream_viscosity(
            phase="liquid",
            temperature_k=330.0,
            composition=[
                {"component_id": "LIGHT", "fraction": 1.0 / 6.0, "basis": "mass_fraction"},
                {"component_id": "HEAVY", "fraction": 5.0 / 6.0, "basis": "mass_fraction"},
            ],
            correlation_records=records,
        )
        self.assertEqual(result["status"], "PASS_WITH_WARNING")
        self.assertAlmostEqual(result["mixing_fractions"]["LIGHT"], 0.5)
        self.assertAlmostEqual(result["mixing_fractions"]["HEAVY"], 0.5)
        self.assertEqual(
            result["basis_conversion"],
            "x_i=(w_i/MW_i)/sum(w_j/MW_j)",
        )

    def test_missing_component_record_blocks_without_default(self) -> None:
        result = viscosity_fallback.estimate_stream_viscosity(
            phase="liquid",
            temperature_k=300.0,
            composition=[
                {"component_id": "UNKNOWN", "fraction": 1.0, "basis": "mole_fraction"},
            ],
            correlation_records={},
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(
            result["code"],
            "BLOCKED_INCOMPLETE_VISCOSITY_CORRELATION_COVERAGE",
        )
        self.assertNotIn("dynamic_viscosity_mpa_s", result)

    def test_out_of_range_and_two_phase_are_blocked(self) -> None:
        record = {
            "A": {
                "molecular_weight_kg_kmol": 18.0,
                "source": SOURCE,
                "liquid": {
                    "model": "ARRHENIUS_TWO_CONSTANT",
                    "A": 1.0e-5,
                    "B_K": 1000.0,
                    "temperature_min_k": 280.0,
                    "temperature_max_k": 320.0,
                },
            },
        }
        composition = [
            {"component_id": "A", "fraction": 1.0, "basis": "mass_fraction"},
        ]
        out_of_range = viscosity_fallback.estimate_stream_viscosity(
            phase="liquid",
            temperature_k=350.0,
            composition=composition,
            correlation_records=record,
        )
        two_phase = viscosity_fallback.estimate_stream_viscosity(
            phase="two_phase",
            temperature_k=300.0,
            composition=composition,
            correlation_records=record,
        )
        self.assertEqual(out_of_range["status"], "BLOCKED")
        self.assertIn(
            "TEMPERATURE_OUTSIDE_MODEL_RANGE",
            " ".join(out_of_range["missing_fields"]),
        )
        self.assertEqual(two_phase["status"], "BLOCKED")
        self.assertEqual(
            two_phase["code"],
            "BLOCKED_VISCOSITY_CORRELATION_PHASE",
        )

    def test_zero_and_negligible_trace_components_do_not_require_correlations(self) -> None:
        records = {
            "MAIN": {
                "molecular_weight_kg_kmol": 18.0,
                "source": SOURCE,
                "liquid": {
                    "model": "ARRHENIUS_TWO_CONSTANT",
                    "A": 1.0e-5,
                    "B_K": 1000.0,
                    "temperature_min_k": 280.0,
                    "temperature_max_k": 320.0,
                },
            },
        }
        result = viscosity_fallback.estimate_stream_viscosity(
            phase="liquid",
            temperature_k=300.0,
            composition=[
                {"component_id": "MAIN", "fraction": 0.999999999999, "basis": "mole_fraction"},
                {"component_id": "ZERO", "fraction": 0.0, "basis": "mole_fraction"},
                {"component_id": "TRACE", "fraction": 1.0e-12, "basis": "mole_fraction"},
            ],
            correlation_records=records,
        )
        self.assertEqual(result["status"], "PASS_WITH_WARNING")
        self.assertEqual(result["component_ids"], ["MAIN"])
        self.assertIn(
            "W_TRACE_COMPONENTS_BELOW_VISCOSITY_THRESHOLD_OMITTED",
            result["warning_codes"],
        )
        omitted = result["composition_normalization"]["omitted_trace_components"]
        self.assertEqual({item["component_id"] for item in omitted}, {"ZERO", "TRACE"})


if __name__ == "__main__":
    unittest.main()
