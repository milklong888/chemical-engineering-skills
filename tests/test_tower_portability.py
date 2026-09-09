"""Self-contained synthetic DSET/INP checks; no real project/Aspen execution."""
from __future__ import annotations
import copy
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "plugins/chemical-engineering-skills/skills/aspen-tower-optimization-workflow/scripts"
sys.path.insert(0, str(SCRIPTS))
import packed_hydraulic_contract as contract
import radfrac_packed_hydraulic_from_bkp as single
import parallel_radfrac_packed_hydraulic_from_bkp as parallel

def source(**values):
    return {"source": "SYNTHETIC_UNIT_TEST_NOT_ENGINEERING_AUTHORITY", "locator": "fixture-row", "basis": "explicit synthetic software oracle", **values}

def create_fixture(root, mode="single"):
    blocks = ["COL_A", "COL_B"] if mode == "parallel" else ["COL_A"]
    columns = {"temperature": [80,85,90,95,100,105], "pressure": [2]*6,
               "vapor_mole": [500,520,540,560,580,600], "liquid_mole": [600]*6,
               "vapor_mass": [15000,15600,16200,16800,17400,18000], "liquid_mass": [18000]*6}
    labels = dict(zip(contract.PROFILE, ("@L_301","@L_302","@L_304","@L_305","@L_316","@L_317")))
    text = []
    for block in blocks:
        for key, values in columns.items():
            if block == "COL_B" and key in {"vapor_mass", "vapor_mole"}:
                values = [v*.6 for v in values]
            dataset, unit = contract.PROFILE[key]
            text.append(f"DSET BLOCK RADFRAC {block} {dataset} {labels[key]} ( " + " ".join(str(v) for v in values) + " )")
    (root/"synthetic.bkp").write_text("\n".join(text), encoding="utf-8")
    (root/"synthetic.csv").write_text("stream,total_mass_flow_kg_h,total_mole_flow_kmol_h,temp_C,pressure_bar\nFEED,9000,300,85,2\nVAPOR,9000,300,100,2\n", encoding="utf-8")
    inp = "\n".join(f'BLOCK {block} RADFRAC\n INTERNALS UPPER STAGE1=2 STAGE2=3 DIAM=2.0 PACK-SIZE="SYNTHETIC-PACK" PACK-HT=1.2\n INTERNALS LOWER STAGE1=4 STAGE2=5 DIAM=2.0 PACK-SIZE="SYNTHETIC-PACK" PACK-HT=1.2' for block in blocks)
    (root/"synthetic.inp").write_text(inp, encoding="utf-8")
    values = {"hetp_m": .45, "flooding_f_factor": 3.2, "capacity_factor_target": .62,
              "capacity_factor_min": .05, "capacity_factor_max": .9, "max_bed_height_m": 2,
              "diameter_round_step_m": .1, "packing_type": "SYNTHETIC-PACK"}
    config = {"schema": "packed-hydraulic-case-config-v1", "mode": mode, "run_id": "SYNTHETIC-RUN", "artifacts": {},
              "property_method": source(method="synthetic_fixture_only"),
              "vapor_density_model": source(method="ideal_gas", accepted_for_preliminary=True),
              "parameters": {key: source(value=v, unit=contract.PARAM_UNITS[key]) for key,v in values.items()}, "towers": []}
    for key,name in (("bkp","synthetic.bkp"),("streams","synthetic.csv"),("inp","synthetic.inp")):
        config["artifacts"][key] = source(path=name, sha256=contract.sha(root/name), run_id=config["run_id"], encoding="utf-8")
    for block in blocks:
        config["towers"].append(source(block=block, nstage=6, feed_stage=4,
            profiles={key: source(label=labels[key], dataset=dataset, unit=unit) for key,(dataset,unit) in contract.PROFILE.items()},
            internals_units=source(unit="m"), nozzles=[
                source(service="feed", stream="FEED", phase="liquid", velocity=source(value=1.3,unit="m/s"), density=source(value=920,unit="kg/m3")),
                source(service="overhead", stream="VAPOR", phase="vapor", velocity=source(value=17,unit="m/s"))]))
    path = root/"config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return config, path

class TowerPortabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="tower_synthetic_")
        self.root = Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()
    def run_config(self, config, path):
        path.write_text(json.dumps(config), encoding="utf-8")
        return contract.execute(parallel if config["mode"] == "parallel" else single, contract.load_config(path, config["mode"]))

    def test_single_original_equations_and_beds(self):
        cfg,path = create_fixture(self.root)
        result = self.run_config(cfg,path)
        row = result["towers"][0]["stage_profile"][2]
        rho = 2e5*.030/(8.314462618*(90+273.15))
        self.assertAlmostEqual(row["vapor_density_kg_m3"],rho)
        self.assertAlmostEqual(row["vapor_volumetric_flow_m3_s"],16200/3600/rho)
        self.assertEqual([v["packing_height_m"] for v in result["towers"][0]["packing_beds"]],[.9,.9])
        self.assertEqual(result["local_calculation_gate"],"PASS")
        self.assertFalse(result["engineering_accepted"])
        self.assertFalse(result["software_rating_verified"])

    def test_parallel_independent_loads_no_equal_split(self):
        cfg,path = create_fixture(self.root,"parallel")
        result = self.run_config(cfg,path)
        a,b = result["towers"]
        self.assertAlmostEqual(b["stage_profile"][2]["actual_f_factor"] / a["stage_profile"][2]["actual_f_factor"],.6)
        self.assertFalse(result["parallel_distribution_verified"])
        self.assertEqual(result["local_calculation_gate"],"PASS")

    def test_missing_HETP_preserves_diameter(self):
        cfg,path = create_fixture(self.root)
        del cfg["parameters"]["hetp_m"]
        result = self.run_config(cfg,path)
        self.assertGreater(result["towers"][0]["hydraulic_sizing"]["selected_inside_diameter_m"],0)
        self.assertEqual(result["towers"][0]["packing_beds"],[])
        self.assertEqual(result["local_calculation_gate"],"REVIEW")

    def test_missing_nozzle_property_blocks_only_nozzle(self):
        cfg,path = create_fixture(self.root)
        del cfg["towers"][0]["nozzles"][0]["density"]
        result = self.run_config(cfg,path)
        nozzles = result["towers"][0]["nozzle_predesign"]
        self.assertEqual(nozzles["feed"]["status"],"BLOCKED_NOZZLE_ONLY")
        self.assertEqual(nozzles["overhead"]["status"],"CALCULATED_PRELIMINARY")
        self.assertGreater(result["towers"][0]["hydraulic_sizing"]["selected_inside_diameter_m"],0)

    def test_missing_capacity_preserves_density_and_nozzles(self):
        cfg,path = create_fixture(self.root)
        del cfg["parameters"]["flooding_f_factor"]
        result = self.run_config(cfg,path)
        self.assertIn("vapor_density_kg_m3",result["towers"][0]["stage_profile"][0])
        self.assertEqual(result["towers"][0]["nozzles"]["feed"]["status"],"CALCULATED_PRELIMINARY")

    def test_missing_liquid_profile_does_not_erase_vapor_calculation(self):
        cfg,path = create_fixture(self.root)
        del cfg["towers"][0]["profiles"]["liquid_mass"]
        result = self.run_config(cfg,path)
        self.assertIsNone(result["towers"][0]["stage_profile"][0]["liquid_mass_kg_h"])
        self.assertGreater(result["towers"][0]["hydraulic_sizing"]["selected_inside_diameter_m"],0)
        self.assertEqual(result["local_calculation_gate"],"REVIEW")

    def test_hash_drift_and_old_run_refused(self):
        cfg,path = create_fixture(self.root)
        cfg["artifacts"]["bkp"]["run_id"] = "OLD"
        with self.assertRaises(contract.BasisError): self.run_config(cfg,path)
        cfg["artifacts"]["bkp"]["run_id"] = "SYNTHETIC-RUN"
        cfg["artifacts"]["bkp"]["sha256"] = "0"*64
        with self.assertRaises(contract.BasisError): self.run_config(cfg,path)

    def test_wrong_units_do_not_guess_labels(self):
        cfg,path = create_fixture(self.root)
        cfg["towers"][0]["profiles"]["pressure"]["unit"] = "bar_gauge"
        result = self.run_config(cfg,path)
        self.assertEqual(result["local_calculation_gate"],"REVIEW")
        self.assertNotIn("vapor_density_kg_m3",result["towers"][0]["stage_profile"][0])

    def test_missing_marker_and_short_profile_refused(self):
        cfg,path = create_fixture(self.root)
        bkp = self.root/"synthetic.bkp"
        original = bkp.read_text(encoding="utf-8")
        for replacement in ("80 * 90", "80 90"):
            bkp.write_text(original.replace("80 85 90",replacement),encoding="utf-8")
            cfg["artifacts"]["bkp"]["sha256"] = contract.sha(bkp)
            with self.assertRaises(contract.BasisError): self.run_config(cfg,path)

    def test_parallel_geometry_gap_retains_other_tower(self):
        cfg,path = create_fixture(self.root,"parallel")
        inp = self.root/"synthetic.inp"
        inp.write_text(inp.read_text().replace("DIAM=2.0", "DIAM=2.7",1),encoding="utf-8")
        cfg["artifacts"]["inp"]["sha256"] = contract.sha(inp)
        result = self.run_config(cfg,path)
        self.assertEqual(result["towers"][0]["status"],"PARTIAL_RELATED_COMPUTATIONS_ONLY")
        self.assertIn("selected_diameter_m",result["towers"][1])
        self.assertEqual(result["local_calculation_gate"],"REVIEW")

    def test_unsupported_INP_geometry_token_not_silently_truncated(self):
        cfg,path = create_fixture(self.root,"parallel")
        inp = self.root/"synthetic.inp"
        inp.write_text(inp.read_text().replace("DIAM=2.0", "DIAM=2E1",1),encoding="utf-8")
        cfg["artifacts"]["inp"]["sha256"] = contract.sha(inp)
        result = self.run_config(cfg,path)
        self.assertEqual(result["towers"][0]["status"],"PARTIAL_RELATED_COMPUTATIONS_ONLY")
        self.assertNotIn("selected_diameter_m",result["towers"][0])
        self.assertEqual(result["towers"][1]["selected_diameter_m"],2.0)

    def test_real_CLI_reports_no_unconditional_acceptance(self):
        cfg,path = create_fixture(self.root)
        prefix = self.root/"out/result"
        result = subprocess.run([sys.executable,"-B",str(SCRIPTS/"radfrac_packed_hydraulic_from_bkp.py"),"--config",str(path),"--out-prefix",str(prefix)],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn("not an Aspen hydraulic rating",prefix.with_suffix(".md").read_text())
        again = subprocess.run([sys.executable,"-B",str(SCRIPTS/"radfrac_packed_hydraulic_from_bkp.py"),"--config",str(path),"--out-prefix",str(prefix)],capture_output=True,text=True,timeout=20)
        self.assertEqual(again.returncode,2)

    def test_invalid_CLI_creates_no_output_directory(self):
        cfg,path = create_fixture(self.root)
        cfg["vapor_density_model"]["accepted_for_preliminary"] = False
        path.write_text(json.dumps(cfg),encoding="utf-8")
        result = subprocess.run([sys.executable,"-B",str(SCRIPTS/"radfrac_packed_hydraulic_from_bkp.py"),"--config",str(path),"--out-prefix",str(self.root/"absent/result")],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,2)
        self.assertFalse((self.root/"absent").exists())

    def test_parallel_height_fail_and_real_CLI_review(self):
        cfg,path = create_fixture(self.root,"parallel")
        cfg["parameters"]["max_bed_height_m"]["value"] = .8
        path.write_text(json.dumps(cfg),encoding="utf-8")
        prefix = self.root/"parallel/result"
        result = subprocess.run([sys.executable,"-B",str(SCRIPTS/"parallel_radfrac_packed_hydraulic_from_bkp.py"),"--config",str(path),"--out-prefix",str(prefix)],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,1,result.stdout+result.stderr)
        data = json.loads(prefix.with_suffix(".json").read_text())
        self.assertEqual(data["towers"][0]["height_gate_source"],"FAIL")
        self.assertIn("Local calculation gate: REVIEW",prefix.with_suffix(".md").read_text())

    def test_schema_is_local_and_no_case_defaults(self):
        schema = json.loads((SCRIPTS/"packed_hydraulic_config.schema.json").read_text())
        self.assertEqual(schema["properties"]["schema"]["const"],"packed-hydraulic-case-config-v1")
        for name in ("radfrac_packed_hydraulic_from_bkp.py","parallel_radfrac_packed_hydraulic_from_bkp.py","packed_hydraulic_contract.py"):
            source_text = (SCRIPTS/name).read_text(encoding="utf-8")
            for forbidden in ("T401", "ESTYFD", "STYPRD", "C:/Users", "AUTH_DIR"):
                self.assertNotIn(forbidden,source_text)

    def test_original_DSET_D_exponents_and_diagnostic_inference(self):
        text = "DSET BLOCK RADFRAC X RAD_PRO2 @L_1 ( 1.0D+1 2.0D+1 )"
        self.assertEqual(single.extract_dset_values(text,"X","RAD_PRO2","@L_1"),[10,20])
        cfg,path = create_fixture(self.root)
        values = single.infer_radfrac_profile_values((self.root/"synthetic.bkp").read_text(),"COL_A",6)
        self.assertEqual(values[0],[80,85,90,95,100,105])

if __name__ == "__main__": unittest.main()
