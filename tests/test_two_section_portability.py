"""Source-preserved section helpers; no COM, private profile or Aspen run."""
from __future__ import annotations
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

REPO=Path(__file__).resolve().parents[1]
SCRIPTS=REPO/"plugins/chemical-engineering-skills/skills/aspen-two-section-flowsheet/scripts"
SCRIPT=SCRIPTS/"build_two_section_corrected.py"
SPEC=importlib.util.spec_from_file_location("two_section_portable_test",SCRIPT)
MODULE=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=MODULE
SPEC.loader.exec_module(MODULE)


def temporary():
    return tempfile.TemporaryDirectory(prefix="two-section-",dir=os.environ.get("TWO_SECTION_TEST_TMP"))


class TwoSectionPortability(unittest.TestCase):
    def profile(self):
        path=SCRIPTS/"synthetic_profile.json"
        return MODULE.load_profile(path,hashlib.sha256(path.read_bytes()).hexdigest())

    def cli(self,*args,expected=0):
        result=subprocess.run([sys.executable,"-B",str(SCRIPT),*args],capture_output=True,text=True,encoding="utf-8",env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"})
        self.assertEqual(result.returncode,expected,result.stdout+result.stderr)
        return json.loads(result.stdout)

    def test_01_all_original_function_names_retained(self):
        manifest=json.loads((SCRIPTS/"SOURCE_PRESERVATION.json").read_text(encoding="utf-8"))
        actual={node.name for node in ast.parse(SCRIPT.read_text(encoding="utf-8")).body if isinstance(node,ast.FunctionDef)}
        self.assertEqual(manifest["original_function_count"],22)
        self.assertEqual({row["function"] for row in manifest["functions"]}-actual,set())
        self.assertEqual(manifest["public_source_sha256"],hashlib.sha256(SCRIPT.read_bytes()).hexdigest())

    def test_02_explicit_molecular_weight_and_formatting(self):
        self.assertEqual(MODULE.kmol_from_mass({"A":20.,"B":40.},mw={"A":10.,"B":20.}),{"A":2.,"B":2.})
        self.assertEqual(MODULE.mole_frac_lines({"A":2.,"B":2.}),["   MOLE-FRAC A 0.50000000 / B 0.50000000"])
        lines=MODULE.wrap_components(components=[("A","DATABANK-A"),("B","DATABANK-B")])
        self.assertEqual(lines,["COMPONENTS A DATABANK-A / B DATABANK-B"])

    def test_03_missing_and_invalid_values_not_zero(self):
        for call in (lambda:MODULE.mass({},"A",mw={"A":10.}), lambda:MODULE.kmol_from_mass({"A":1.},mw={}),
                     lambda:MODULE.mole_ratio({"mol_A":1.},"A","B"), lambda:MODULE.mole_ratio({"mol_A":1.,"mol_B":0.},"A","B"),
                     lambda:MODULE.mole_frac_lines({"A":0.}),lambda:MODULE.mass({"mol_A":None},"A",mw={"A":10.}),
                     lambda:MODULE.stream_lines_kmol("S",25.,1.,{"A":float("nan")})):
            with self.assertRaises(ValueError):call()

    def test_04_ratios_use_explicit_complete_rows(self):
        row={"mol_A":1.,"mol_B":2.}
        self.assertAlmostEqual(MODULE.mass_frac(row,"A",components=[("A","A"),("B","B")],mw={"A":10.,"B":20.}),.2)
        self.assertEqual(MODULE.mole_ratio(row,"A","B"),.5)

    def test_05_seed_explicit_nonzero(self):
        with self.assertRaises(TypeError):MODULE.blank_stream("S",25.,1.,"X")
        lines=MODULE.blank_stream("S",25.,1.,"X",seed_flow_kmol_h=1e-9)
        self.assertEqual(float(lines[0].split("MOLE-FLOW=")[1]),1e-9)

    def test_06_read_and_status_helpers_preserve_unknown(self):
        fake=SimpleNamespace(Tree=SimpleNamespace(FindNode=lambda path:None))
        units={"temp_C":"C","pressure_bar":"bar","mole_flow_kmol_h":"kmol/hr","mass_flow_kg_h":"kg/hr","mol_X":"kmol/hr"}
        self.assertIsNone(MODULE.read_stream(fake,"S",components=[("X","X")],expected_units=units)["mol_X"])
        with temporary() as dirname:
            p=Path(dirname)/"export.inp";p.write_text("BLOCK A HEATER\nBLOCK A PUMP\nBLOCK B-2 SEP2\n",encoding="utf-8")
            self.assertEqual(MODULE.parse_block_ids(p),["A","B-2"])
            rows=MODULE.block_status_rows(fake,p,calculator_ids=["MYCALC"])
            self.assertEqual(rows[-1]["block"],"CALC:MYCALC")
            self.assertFalse(any(MODULE.is_clean_block(row) for row in rows))

    def test_07_csv_no_overwrite(self):
        with temporary() as dirname:
            p=Path(dirname)/"values.csv"
            MODULE.write_csv([{"stream":"S","known":None}],p)
            original=p.read_bytes()
            with self.assertRaises(FileExistsError):MODULE.write_csv([{"stream":"X","known":0}],p)
            self.assertEqual(p.read_bytes(),original)

    def test_08_profile_hash_and_mutation_gate(self):
        with self.assertRaises(ValueError):MODULE.load_profile(SCRIPTS/"synthetic_profile.json","0"*64)
        profile=self.profile();profile.data["molecular_weights"]["X"]=2.
        with self.assertRaises(ValueError):MODULE.segment_a_lines(profile=profile)
        with self.assertRaises(TypeError):MODULE.segment_a_lines()

    def test_09_real_cli_prepares_only_synthetic_handoff(self):
        profile=SCRIPTS/"synthetic_profile.json";digest=hashlib.sha256(profile.read_bytes()).hexdigest()
        with temporary() as dirname:
            output=Path(dirname)/"new-candidate"
            args=["--profile",str(profile),"--profile-sha256",digest,"--section","a","--output-dir",str(output)]
            result=self.cli(*args)
            self.assertEqual(result["status"],"candidate_input_prepared_not_run")
            self.assertFalse(result["automatic_execution"])
            self.assertFalse(result["delivery_passed"])
            self.assertIn("SYNTHETIC_PROFILE_NOT_AN_ENGINEERING_MODEL",result["execution_blockers"])
            self.assertTrue(Path(result["candidate_file"]).is_file())
            self.assertTrue(any("aspen_operation_template.py" in row["skill_relative_path"] for row in result["runtime_dependencies"]))
            self.cli(*args,expected=2)

    def test_10_section_b_missing_boundary_fails_before_write(self):
        profile=SCRIPTS/"synthetic_profile.json";digest=hashlib.sha256(profile.read_bytes()).hexdigest()
        with temporary() as dirname:
            output=Path(dirname)/"missing-boundary"
            self.cli("--profile",str(profile),"--profile-sha256",digest,"--section","b","--output-dir",str(output),expected=2)
            self.assertFalse(output.exists())
        with self.assertRaises(ValueError):MODULE.segment_b_lines({},profile=self.profile())

    def test_11_no_legacy_project_values_or_com_default(self):
        source=SCRIPT.read_text(encoding="utf-8")
        for forbidden in ("EnsureDispatch","import win32com","PXRAF_MASS =","81_722","145_441","STYPROD","BZ781"):
            self.assertNotIn(forbidden,source)
        fixture=(SCRIPTS/"synthetic_profile.json").read_text(encoding="utf-8")
        for forbidden in ("STYPROD","BZ781","PXRAF","145441","81722"):
            self.assertNotIn(forbidden,fixture)

    def test_12_unit_mismatch_not_relabelled(self):
        fake=SimpleNamespace(Tree=SimpleNamespace(FindNode=lambda path:SimpleNamespace(Value=300.0,UnitString="kPa")))
        units={"temp_C":"C","pressure_bar":"bar","mole_flow_kmol_h":"kmol/hr","mass_flow_kg_h":"kg/hr","mol_X":"kmol/hr"}
        row=MODULE.read_stream(fake,"S",components=[("X","X")],expected_units=units)
        self.assertIsNone(row["pressure_bar"])
        self.assertEqual(row["field_evidence"]["pressure_bar"]["raw_value"],300.0)
        self.assertFalse(row["field_evidence"]["pressure_bar"]["unit_verified"])
        with self.assertRaises(ValueError):MODULE.read_stream(fake,"S",components=[("X","X")],expected_units={})

    def test_13_sep_mutation_requires_supervisor(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaises(RuntimeError):
                MODULE.set_sep2_splits(None,"B","O",{"X":.5},runtime=None,expected_units={},allowed_input_paths=())


if __name__=="__main__":unittest.main(verbosity=2)
