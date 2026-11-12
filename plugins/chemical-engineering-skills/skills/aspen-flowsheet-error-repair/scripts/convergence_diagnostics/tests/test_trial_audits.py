# SPDX-License-Identifier: MIT
"""Synthetic black-box CLI tests. No native simulator or acceptance evidence."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1]


def q(value, unit="kg/h"):
    return {"value": value, "unit": unit}


def precision():
    first = {"id": "a", "outer": {"variable": "rate", "definition": "synthetic rate",
        "target": q(1), "absolute_tolerance": q(0.1), "observed": q(1.1)},
        "inner": {"variable": "return", "definition": "relative update",
        "criterion": "relative", "tolerance": 0.02, "unit": "1"}}
    second = copy.deepcopy(first)
    second["id"] = "b"
    second["outer"]["observed"]["value"] = 1.3
    second["inner"]["tolerance"] = 0.002
    return {"schema": "precision-trials-v1", "trials": [first, second]}


class TrialAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.evidence = self.base / "receipt.json"
        self.evidence.write_text('{"synthetic":true,"untrusted_status":"success"}\n', encoding="utf-8")
        self.digest = hashlib.sha256(self.evidence.read_bytes()).hexdigest()

    def startup(self, kind="cold", initial=3, final=3, minimum=0):
        return {"schema": "startup-trials-v1", "target": {"value": 10, "absolute_tolerance": 0.1, "unit": "kg/h"},
            "cases": [{"id": "one", "initialization_kind": kind, "observed": q(10.05),
                "manipulated": {"variable": "feed", "initial": q(initial, "mol/s"),
                    "final": q(final, "mol/s"), "minimum_movement": q(minimum, "mol/s")},
                "artifacts": [{"role": "native_receipt", "path": "receipt.json", "sha256": self.digest}]}]}

    def invoke(self, tool, data=None, raw=None, output=None):
        source = self.base / "input.json"
        source.write_text(raw if raw is not None else json.dumps(data, allow_nan=True), encoding="utf-8")
        destination = Path(output) if output is not None else self.base / "output.json"
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
        result = subprocess.run([sys.executable, "-B", str(TOOLS / tool), "--input", str(source),
                                 "--output", str(destination)], capture_output=True, text=True, env=env, timeout=15)
        return result, source, destination

    def success(self, tool, data):
        result, source, dest = self.invoke(tool, data)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(dest.read_text(encoding="utf-8"))
        self.assertEqual(report["input_sha256"], hashlib.sha256(source.read_bytes()).hexdigest())
        self.assertFalse(report["native_cleanliness_evaluated"])
        self.assertFalse(report["strict_accepted"])
        self.assertEqual(report["observation_authority"], "caller-supplied observations, not native proof")
        return report

    def invalid(self, tool, data=None, raw=None):
        result, _, dest = self.invoke(tool, data, raw)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse(dest.exists())

    def test_precision_decimal_boundary_and_failure(self):
        report = self.success("audit_precision_trials.py", precision())
        self.assertEqual([x["outer_target_met"] for x in report["trials"]], [True, False])
        self.assertAlmostEqual(report["trials"][0]["outer_residual"], 0.1)
        self.assertEqual(report["inner_comparisons"][0]["change"], "tightened")
        self.assertFalse(report["inner_outer_tolerances_compared"])
        self.assertFalse(report["root_cause_evaluated"])
        self.assertIsNone(report["recommended_tolerance"])

    def test_precision_not_comparable_identity_fields(self):
        for field, value in [("variable", "other"), ("definition", "another definition"),
                             ("criterion", "absolute"), ("unit", "kg/h")]:
            with self.subTest(field=field):
                data = precision()
                inner = data["trials"][1]["inner"]
                if field == "unit":
                    for trial in data["trials"]:
                        trial["inner"]["criterion"] = "absolute"
                inner[field] = value
                report = self.success("audit_precision_trials.py", data)
                self.assertFalse(report["inner_comparisons"][0]["comparable"])
                self.assertEqual(report["inner_comparisons"][0]["change"], "not_comparable")

    def test_precision_unchanged_and_loosened(self):
        for value, expected in [(0.02, "unchanged"), (0.2, "loosened")]:
            data = precision(); data["trials"][1]["inner"]["tolerance"] = value
            self.assertEqual(self.success("audit_precision_trials.py", data)["inner_comparisons"][0]["change"], expected)

    def test_zero_target_has_no_relative_scale(self):
        data = precision(); data["trials"][0]["outer"]["target"]["value"] = 0
        self.assertIsNone(self.success("audit_precision_trials.py", data)["trials"][0]["outer_relative_tolerance_scale"])

    def test_outer_unit_mismatch_and_missing(self):
        for unit in ["g/h", None, ""]:
            data = precision(); data["trials"][0]["outer"]["observed"]["unit"] = unit
            self.invalid("audit_precision_trials.py", data)

    def test_relative_inner_requires_explicit_dimensionless_unit(self):
        data = precision(); data["trials"][0]["inner"]["unit"] = "kg/h"
        self.invalid("audit_precision_trials.py", data)

    def test_precision_missing_or_nonpositive_tolerance(self):
        for value in [None, 0, -0.1, True]:
            data = precision(); data["trials"][0]["inner"]["tolerance"] = value
            self.invalid("audit_precision_trials.py", data)

    def test_duplicate_keys_and_non_json_constants(self):
        for raw in ['{"schema":"x","schema":"y"}', '{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}', '{"x":1e400}', '{"x":1e-400}']:
            for tool in ["audit_precision_trials.py", "audit_cold_starts.py"]:
                with self.subTest(raw=raw, tool=tool): self.invalid(tool, raw=raw)

    def test_bool_null_and_string_are_not_numbers(self):
        for value in [True, None, "1.1"]:
            data = precision(); data["trials"][0]["outer"]["observed"]["value"] = value
            self.invalid("audit_precision_trials.py", data)
            data = self.startup(); data["cases"][0]["observed"]["value"] = value
            self.invalid("audit_cold_starts.py", data)

    def test_arithmetic_overflow_is_rejected(self):
        data = precision(); outer = data["trials"][0]["outer"]
        outer["target"]["value"] = -1e308; outer["observed"]["value"] = 1e308
        self.invalid("audit_precision_trials.py", data)

    def test_duplicate_trial_and_case_ids(self):
        data = precision(); data["trials"][1]["id"] = "a"
        self.invalid("audit_precision_trials.py", data)
        data = self.startup(); data["cases"].append(copy.deepcopy(data["cases"][0]))
        self.invalid("audit_cold_starts.py", data)

    def test_cold_can_meet_target_without_movement(self):
        report = self.success("audit_cold_starts.py", self.startup())
        self.assertTrue(report["cases"][0]["target_met"])
        self.assertFalse(report["cases"][0]["movement_exceeds_threshold"])
        self.assertTrue(report["declared_initialization_coverage"]["cold"])
        self.assertFalse(report["initialization_coverage_verified"])
        self.assertFalse(report["cases"][0]["artifacts"][0]["contents_interpreted"])

    def test_warm_does_not_cover_cold(self):
        report = self.success("audit_cold_starts.py", self.startup("warm"))
        self.assertTrue(report["declared_initialization_coverage"]["warm"])
        self.assertFalse(report["declared_initialization_coverage"]["cold"])
        self.assertFalse(report["bounded_perturbation_with_reported_movement"])

    def test_bounded_perturbation_moves_but_target_can_fail(self):
        data = self.startup("bounded_perturbation", 3, 4, 0.1)
        data["cases"][0]["observed"]["value"] = 12
        report = self.success("audit_cold_starts.py", data)
        self.assertTrue(report["cases"][0]["movement_exceeds_threshold"])
        self.assertFalse(report["cases"][0]["target_met"])
        self.assertTrue(report["bounded_perturbation_with_reported_movement"])

    def test_movement_must_strictly_exceed_threshold(self):
        for initial, final, threshold in [(3, 3, 0), (3, 4, 1), (3, 3.1, 0.1)]:
            report = self.success("audit_cold_starts.py", self.startup(initial=initial, final=final, minimum=threshold))
            self.assertFalse(report["cases"][0]["movement_exceeds_threshold"])

    def test_startup_units_and_threshold_required(self):
        data = self.startup(); data["cases"][0]["observed"]["unit"] = "g/h"
        self.invalid("audit_cold_starts.py", data)
        data = self.startup(); data["cases"][0]["manipulated"]["final"]["unit"] = "kg/s"
        self.invalid("audit_cold_starts.py", data)
        data = self.startup(); del data["cases"][0]["manipulated"]["minimum_movement"]
        self.invalid("audit_cold_starts.py", data)

    def test_missing_or_tampered_artifacts(self):
        data = self.startup(); data["cases"][0]["artifacts"][0]["path"] = "absent.json"
        self.invalid("audit_cold_starts.py", data)
        data = self.startup(); data["cases"][0]["artifacts"][0]["sha256"] = "0" * 64
        self.invalid("audit_cold_starts.py", data)

    def test_artifact_hash_does_not_certify_native_receipt_contents(self):
        report = self.success("audit_cold_starts.py", self.startup("exact_reopen"))
        self.assertFalse(report["strict_accepted"])
        self.assertTrue(report["declared_initialization_coverage"]["exact_reopen"])
        self.assertFalse(report["cases"][0]["initialization_kind_verified"])

    def test_output_input_overwrite_rejected(self):
        for tool, data in [("audit_precision_trials.py", precision()), ("audit_cold_starts.py", self.startup())]:
            result, source, _ = self.invoke(tool, data, output=self.base / "input.json")
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(source.read_text(encoding="utf-8")), data)

    def test_output_evidence_overwrite_rejected(self):
        original = self.evidence.read_bytes()
        result, _, _ = self.invoke("audit_cold_starts.py", self.startup(), output=self.evidence)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.evidence.read_bytes(), original)

    def test_output_hardlink_evidence_overwrite_rejected(self):
        alias = self.base / "alias.json"
        try: os.link(self.evidence, alias)
        except OSError as exc: self.skipTest(str(exc))
        result, _, _ = self.invoke("audit_cold_starts.py", self.startup(), output=alias)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(hashlib.sha256(self.evidence.read_bytes()).hexdigest(), self.digest)

    def test_output_ancestor_symlink_alias_rejected(self):
        real = self.base / "real"; real.mkdir()
        nested_evidence = real / "receipt.json"; nested_evidence.write_bytes(self.evidence.read_bytes())
        alias = self.base / "alias"
        junction = False
        try:
            alias.symlink_to(real, target_is_directory=True)
        except OSError as exc:
            if os.name != "nt":
                self.skipTest(str(exc))
            # A directory junction exercises the same resolved-ancestor alias
            # without requiring Windows' symbolic-link creation privilege.
            created = subprocess.run(["cmd", "/c", "mklink", "/J", str(alias), str(real)],
                                     capture_output=True, timeout=15)
            if created.returncode:
                self.skipTest("neither symlink nor directory junction available")
            junction = True
        data = self.startup(); data["cases"][0]["artifacts"][0]["path"] = "real/receipt.json"
        try:
            result, _, _ = self.invoke("audit_cold_starts.py", data, output=alias / "receipt.json")
            self.assertEqual(result.returncode, 2)
            self.assertEqual(hashlib.sha256(nested_evidence.read_bytes()).hexdigest(), self.digest)
        finally:
            if junction:
                os.rmdir(alias)  # Remove only the junction, never its target.

    def test_tool_code_output_overwrite_rejected(self):
        sandbox = self.base / "tools"; sandbox.mkdir()
        for name in ["audit_precision_trials.py", "audit_cold_starts.py"]:
            shutil.copyfile(TOOLS / name, sandbox / name)
        source = self.base / "input.json"
        source.write_text(json.dumps(precision()), encoding="utf-8")
        destination = sandbox / "audit_cold_starts.py"
        before = destination.read_bytes()
        result = subprocess.run([sys.executable, "-B", str(sandbox / "audit_precision_trials.py"),
            "--input", str(source), "--output", str(destination)], capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(destination.read_bytes(), before)

    def test_invalid_input_does_not_replace_existing_output(self):
        destination = self.base / "output.json"; destination.write_text("sentinel", encoding="utf-8")
        result, _, _ = self.invoke("audit_precision_trials.py", raw='{"x":NaN}')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(destination.read_text(encoding="utf-8"), "sentinel")

    def test_examples_execute_as_synthetic_fixtures(self):
        for tool, example in [("audit_precision_trials.py", "precision_trials.json"),
                              ("audit_cold_starts.py", "startup_trials.json")]:
            dest = self.base / (example + ".out.json")
            result = subprocess.run([sys.executable, "-B", str(TOOLS / tool), "--input", str(TOOLS / "examples" / example),
                "--output", str(dest)], capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(json.loads(dest.read_text(encoding="utf-8"))["strict_accepted"])


if __name__ == "__main__":
    unittest.main()
