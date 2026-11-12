"""Synthetic integration checks for the actual professional implementations."""
import json
import hashlib
from pathlib import Path
import tempfile
import unittest

from tools import module_tools
from tools.expert_cli import execute


class NormalizedModulesTests(unittest.TestCase):
    def test_learning_owner_identity_contract_matches_current_public_owners(self):
        contract=json.loads((module_tools.ROOT/"knowledge/learning_owner_contract.json").read_text(encoding="utf-8"))
        for row in contract["files"]:
            owner=module_tools.skills_root()/row["path"]
            self.assertEqual(hashlib.sha256(owner.read_bytes()).hexdigest(),row["sha256"],row["path"])

    def test_catalog_qualified_rules_and_archives(self):
        normal = module_tools.catalog()
        full = module_tools.catalog({"include_archives": True})
        self.assertEqual(len(normal["modules"]), 10)
        self.assertEqual(len(full["modules"]), 12)
        self.assertEqual(len(full["proposal_dispositions"]), 23)
        self.assertEqual(len(full["callable_tools"]), 9)
        archived = [x for x in full["modules"] if x["migration_action"] == "excluded_archive"]
        self.assertEqual(len(archived), 2)
        self.assertTrue(all(x["learning_eligible"] is False and x["default_retrieval_eligible"] is False for x in archived))
        keys = [key for row in full["proposal_dispositions"] for key in row["qualified_rule_ids"]]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(len([x for x in keys if x.endswith("#P0-018")]), 2)
        self.assertTrue(all("#" in x for x in keys))

    def test_registered_owner_files_exist(self):
        for row in module_tools.catalog()["modules"]:
            for relative in row["owner_paths"]:
                self.assertTrue((module_tools.skills_root() / relative).is_file(), relative)

    def test_no_arbitrary_module_or_archive_execution(self):
        for tool in ("../../private.py", "smr-psa-audit.audit", "os.system", "edr.__dict__", None, []):
            with self.subTest(tool=tool), self.assertRaises(ValueError):
                module_tools.call({"tool": tool, "inputs": {}})
        for payload in ({}, {"tool":"edr.check_packed_beds","inputs":[],},
                        {"tool":"edr.check_packed_beds","inputs":{},"path":"untrusted.py"}):
            with self.assertRaises(ValueError):
                module_tools.call(payload)

    def test_catalog_rejects_coercion_and_bad_selection(self):
        for payload in ({"include_archives": "false"}, {"include_archives": 1}, {"module_id": ""},
                        {"module_id": "smr-psa-audit"}, {"exec": True}):
            with self.assertRaises(ValueError):
                module_tools.catalog(payload)

    def test_all_four_edr_examples_call_single_core(self):
        root = module_tools.skills_root()/"aspen-edr-rating-delivery/examples/offline_checks"
        for tool, example in (("screen_pipe_candidates","pipe"),("check_exchanger_basis","exchanger"),
                              ("check_packed_beds","packed"),("audit_edr_geometry","geometry")):
            inputs = json.loads((root/f"{example}.json").read_text(encoding="utf-8"))
            result = execute({"operation":"module_check","payload":{"tool":"edr."+tool,"inputs":inputs}},root)
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["result"]["diagnostic_status"], "pass")
            self.assertEqual(result["engineering_acceptance"], "not_assessed")
            self.assertEqual(result["result"]["native_calculation_acceptance"], "not_assessed")

    def test_dynamics_grid_preserves_numeric_types_and_overflow(self):
        with tempfile.TemporaryDirectory() as directory:
            csv = Path(directory)/"synthetic.csv"
            csv.write_text("time,value\n0,1\n1,2\n2,3\n",encoding="utf-8")
            inputs = dict(csv_path=str(csv),time_column="time",interval=1,start=0,end=2,time_abs_tolerance=0,
                          numeric_columns=["value"])
            valid = module_tools.call({"tool":"dynamics.check_csv_grid","inputs":inputs})
            self.assertTrue(valid["result"]["matches"])
            self.assertFalse(valid["result"]["external_process_started"])
            for value in (True,"1",[],{},None,5e-324):
                bad = module_tools.call({"tool":"dynamics.check_csv_grid","inputs":{**inputs,"interval":value}})
                self.assertEqual(bad["result"]["status"], "invalid_or_unavailable")

    def test_missing_inputs_are_invalid_not_pass(self):
        result=module_tools.call({"tool":"dynamics.check_csv_grid","inputs":{}})
        self.assertEqual(result["status"],"completed")
        self.assertEqual(result["result"]["status"],"invalid_or_unavailable")
        self.assertNotIn("matches",result["result"])

    def test_cli_catalog_and_schema_do_not_need_equipment(self):
        def forbidden(_):
            raise AssertionError("Offline catalog must not invoke the equipment worker")
        result=execute({"operation":"module_catalog","payload":{}},Path.cwd(),equipment_runner=forbidden)
        self.assertEqual(len(result["callable_tools"]),9)
        result=execute({"operation":"schema","payload":{"schema_id":"module-tools"}},Path.cwd(),equipment_runner=forbidden)
        self.assertEqual(len(result["tools"]),9)


if __name__ == "__main__":
    unittest.main()
