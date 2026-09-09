"""Real hash-bound synthetic files; never evidence for an actual process."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backends.process import feedback as f

class FeedbackIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="feedback_integrity_synthetic_")
        self.root = Path(self.tmp.name)
        self.family = "family_fixed_tubesheet_exchanger"
        self.export = {"schema":"equipment-process-canonical-export-v1","case_id":"SYNTHETIC","run_id":"RUN_CURRENT",
            "equipment":{"E1":{"family_id":self.family,"values":{"heat_transfer_area_m2":2000,"flow_m3_h":100},"units":{"heat_transfer_area_m2":"m2","flow_m3_h":"m3/h"}}}}
        self.context = {"case_id":"SYNTHETIC","run_id":"RUN_CURRENT",
            "source_export":self.put("export.json",self.export),
            "authority":self.put("authority.json",{"schema":"equipment-process-authority-v1","case_id":"SYNTHETIC","run_id":"RUN_CURRENT","required_method":"SYNTHETIC_SOURCE_METHOD","acceptance_criteria":["synthetic checks, not engineering"]})}
        self.response = {"result":{"equipment_tag":"E1","normalized_input":copy.deepcopy(self.export["equipment"]["E1"]["values"]),"model_decision":{"model_status":"type_screening"},"match":{"family_id":self.family}}}

    def tearDown(self): self.tmp.cleanup()
    def put(self,name,value):
        data=json.dumps(value,sort_keys=True).encode()
        (self.root/name).write_bytes(data)
        return {"path":name,"sha256":hashlib.sha256(data).hexdigest().upper()}

    def put_raw(self,name,text):
        data=text.encode("utf-8");(self.root/name).write_bytes(data)
        return {"path":name,"sha256":hashlib.sha256(data).hexdigest().upper()}

    def replay_fixture(self):
        plan=f.build_plan(self.response,self.context,self.root)
        candidate=self.put("candidate.json",{"synthetic":"NOT ASPEN"})
        replay={"case_id":self.context["case_id"],"run_id":self.context["run_id"],"plan_sha256":plan["plan_sha256"],
            "candidate":candidate,"source_export":self.context["source_export"],"gates":{}}
        return plan,replay

    def receipt(self,plan,replay,gate,native,validator):
        return {"schema":"equipment-process-domain-receipt-v1","gate":gate,"case_id":self.context["case_id"],
            "run_id":self.context["run_id"],"plan_sha256":plan["plan_sha256"],"candidate_sha256":replay["candidate"]["sha256"],
            "source_export_sha256":replay["source_export"]["sha256"],"status":"strict_passed", "validator":validator,
            "checks":[{"id":gate+"_result","passed":True}],"native_result":native,"evidence":[native,replay["candidate"]]}

    def native_receipt(self, *, warning=False):
        plan,replay=self.replay_fixture()
        cp=self.put_raw("control.txt","Summary of Simulation Errors\nPhysical\nProperty System Simulation\nTerminal Errors 0 0 0\nSevere Errors 0 0 0\nErrors 0 0 0\nWarnings 0 0 0\n")
        his=self.put_raw("run.his",("* WARNING SYNTHETIC REAL DIAGNOSTIC\n" if warning else "")+"NO ERRORS OR WARNINGS GENERATED\n")
        association={"verified":True,"run_id":self.context["run_id"],"case_sha256":replay["candidate"]["sha256"]}
        native={"schema_version":"aspen_clean_delivery_audit/2","passed":True,"simulation_clean":True,
            "source_unchanged":True,"source_sha256":replay["candidate"]["sha256"],
            "run":{"run_id":self.context["run_id"],"case_sha256":replay["candidate"]["sha256"],"started_epoch":1,"finished_epoch":2,"status":"completed"},
            "control_panel":{**cp,"association":association},"histories":[{**his,"association":association}],"block_statuses":[{"block":"E1","blkstat":0}]}
        native_ref=self.put("native.json",native)
        validator={"id":"aspen_summary_history_v2","sha256":f.TRUSTED_REPLAY_VALIDATORS["aspen_summary_history_v2"]["implementation_sha256"]}
        record=self.receipt(plan,replay,"strict_run_status",native_ref,validator)
        replay["gates"]["strict_run_status"]=self.put("strict_receipt.json",record)
        return plan,replay,record

    def constraint(self,quantity="heat_transfer_area_m2",value=2000,limit=1000,unit="m2", *, old=False):
        actual = self.context["source_export"]
        if old:
            oldexport=copy.deepcopy(self.export);oldexport["case_id"]="OTHER_OLD_CASE"
            actual=self.put("old_export.json",oldexport)
        source_limit=self.put("limit.json",{"schema":"equipment-process-limit-v1","quantity":quantity,"value":limit,"unit":unit,
            "source_id":"SYNTHETIC-NOT-A-STANDARD","version":"TEST_ONLY","locator":"synthetic row",
            "applicability":{"equipment_id":"E1","family_id":self.family}})
        row={"equipment_id":"E1","status":"verified_applicable","quantity":quantity,"value":value,"limit":limit,"unit":unit,
             "applicability":"synthetic current-duty review","relation":"max",
             "value_source":dict(actual,pointer=f"/equipment/E1/values/{quantity}"),"limit_source":dict(source_limit,pointer="/value")}
        self.context["constraint_evidence"]={"E1":[self.put("constraint.json",row)]}

    def test_current_export_and_selector_mismatch_is_local_gap(self):
        self.constraint()
        self.response["result"]["normalized_input"]["heat_transfer_area_m2"]=2500
        plan=f.build_plan(self.response,self.context,self.root)
        self.assertIsNone(plan["equipment"][0]["revision"])
        self.assertTrue(plan["equipment"][0]["binding_gaps"])
        self.assertIn("legacy_analysis",plan["equipment"][0])

    def test_old_case_actual_cannot_generate_current_count(self):
        self.constraint(old=True)
        plan=f.build_plan(self.response,self.context,self.root)
        self.assertIsNone(plan["equipment"][0]["revision"])
        self.assertTrue(plan["equipment"][0]["binding_gaps"])

    def test_limit_wrong_unit_is_local_gap(self):
        self.constraint()
        row=json.loads((self.root/"constraint.json").read_text())
        limit=json.loads((self.root/"limit.json").read_text());limit["unit"]="ft2"
        row["limit_source"]=dict(self.put("limit.json",limit),pointer="/value")
        self.context["constraint_evidence"]["E1"]=[self.put("constraint.json",row)]
        plan=f.build_plan(self.response,self.context,self.root)
        self.assertIsNone(plan["equipment"][0]["revision"])
        self.assertTrue(plan["equipment"][0]["binding_gaps"])

    def test_canonical_flow_alias_is_not_resolved_by_series(self):
        self.constraint("flow_m3_h",100,50,"m3/h")
        row=f.build_plan(self.response,self.context,self.root)["equipment"][0]
        self.assertTrue(row["revision"]["cannot_claim_limit_resolved"])
        self.assertIn("flow_m3_h",row["revision"]["unresolved_by_this_topology"])

    def test_same_revision_area_positive(self):
        self.constraint()
        row=f.build_plan(self.response,self.context,self.root)["equipment"][0]
        self.assertEqual(row["binding_gaps"],[])
        self.assertEqual(row["revision"]["initial_count_bounds"][0]["count"],2)
        self.assertFalse(row["revision"]["automatic_aspen_mutation"])

    def test_unknown_export_keeps_calculation_but_not_constraint_plan(self):
        self.constraint()
        self.export["schema"]="unknown_format"
        self.context["source_export"]=self.put("export.json",self.export)
        row=f.build_plan(self.response,self.context,self.root)["equipment"][0]
        self.assertIsNone(row["revision"])
        self.assertTrue(row["binding_gaps"])
        self.assertEqual(row["legacy_analysis"]["original_upstream_fields"],self.response["result"])

    def test_failed_checks_and_one_receipt_for_all_gates_not_complete(self):
        plan=f.build_plan(self.response,self.context,self.root)
        candidate=self.put("candidate.json",{"synthetic":"NOT ASPEN"})
        receipt={"schema":"untrusted_receipt","case_id":self.context["case_id"],"candidate_sha256":candidate["sha256"],
            "source_export_sha256":self.context["source_export"]["sha256"],"plan_sha256":plan["plan_sha256"],
            "status":"strict_passed","validator":"arbitrary_name","checks":[{"passed":False}],"evidence":[candidate]}
        ref=self.put("receipt.json",receipt)
        replay={"case_id":self.context["case_id"],"plan_sha256":plan["plan_sha256"],"candidate":candidate,
            "source_export":self.context["source_export"],"gates":{name:ref for name in plan["required_replay_gates"]}}
        result=f.audit_replay(plan,replay,self.root)
        self.assertFalse(result["evidence_chain_complete"])
        self.assertEqual(len(result["failed_gates"]),11)

    def test_production_native_parser_actually_rechecks_raw_files(self):
        plan,replay,_=self.native_receipt()
        result=f.audit_replay(plan,replay,self.root)
        self.assertTrue(next(row for row in result["receipts"] if row["gate"]=="strict_run_status")["valid"])
        self.assertEqual(len(result["failed_gates"]),10)
        self.assertFalse(result["engineering_accepted"])

    def test_native_self_claim_pass_does_not_hide_raw_warning(self):
        plan,replay,_=self.native_receipt(warning=True)
        result=f.audit_replay(plan,replay,self.root)
        self.assertFalse(result["receipts"][0]["valid"])
        self.assertEqual(len(result["failed_gates"]),11)

    def test_native_validator_hash_and_gate_scope_required(self):
        plan,replay,row=self.native_receipt()
        row["validator"]["sha256"]="0"*64
        replay["gates"]["strict_run_status"]=self.put("strict_receipt.json",row)
        self.assertFalse(f.audit_replay(plan,replay,self.root)["receipts"][0]["valid"])
        row["validator"]["sha256"]=f.TRUSTED_REPLAY_VALIDATORS["aspen_summary_history_v2"]["implementation_sha256"]
        row["gate"]="product_targets"
        replay["gates"]={"product_targets":self.put("wrong_scope.json",row)}
        self.assertFalse(f.audit_replay(plan,replay,self.root)["receipts"][0]["valid"])

    def test_full_synthetic_chain_only_with_test_owned_oracle(self):
        plan,replay=self.replay_fixture()
        implementation=Path(__file__).resolve()
        implementation_hash=hashlib.sha256(implementation.read_bytes()).hexdigest().upper()
        def oracle(native,receipt,root,candidate,path):
            raw=f.read_reference(root,native["observation"])
            return (native["gate"]==receipt["gate"] and native["run_id"]==receipt["run_id"]
                    and raw["case_id"]==receipt["case_id"] and raw["run_id"]==receipt["run_id"]
                    and raw["observed"]==1 and raw["candidate_sha256"]==candidate["sha256"])
        registry={"test_only_synthetic_oracle":{"implementation_sha256":implementation_hash,"implementation_paths":(str(implementation),),
            "native_schema":"test-only-domain-observation-v1","native_schema_field":"schema", "gates":frozenset(f.REPLAY_GATES),"recheck":oracle}}
        for gate in f.REPLAY_GATES:
            raw=self.put(gate+"_observation.json",{"case_id":self.context["case_id"],"run_id":self.context["run_id"],"observed":1,"candidate_sha256":replay["candidate"]["sha256"]})
            native=self.put(gate+"_native.json",{"schema":"test-only-domain-observation-v1","gate":gate,"run_id":self.context["run_id"],"observation":raw})
            receipt=self.receipt(plan,replay,gate,native,{"id":"test_only_synthetic_oracle","sha256":implementation_hash,"path":str(implementation)})
            replay["gates"][gate]=self.put(gate+"_receipt.json",receipt)
        self.assertFalse(f.audit_replay(plan,replay,self.root)["evidence_chain_complete"])
        with patch.dict(f.TRUSTED_REPLAY_VALIDATORS,registry,clear=True):
            result=f.audit_replay(plan,replay,self.root)
            self.assertTrue(result["evidence_chain_complete"])
            self.assertFalse(result["engineering_accepted"])
            # Re-labeling a real failed check cannot bypass the independent oracle.
            gate=f.REPLAY_GATES[0]
            raw=self.put(gate+"_observation.json",{"case_id":self.context["case_id"],"run_id":self.context["run_id"],"observed":0,"candidate_sha256":replay["candidate"]["sha256"]})
            native=self.put(gate+"_native.json",{"schema":"test-only-domain-observation-v1","gate":gate,"run_id":self.context["run_id"],"observation":raw})
            receipt=self.receipt(plan,replay,gate,native,{"id":"test_only_synthetic_oracle","sha256":implementation_hash,"path":str(implementation)})
            replay["gates"][gate]=self.put(gate+"_receipt.json",receipt)
            self.assertFalse(f.audit_replay(plan,replay,self.root)["evidence_chain_complete"])

    def test_current_derived_area_has_real_input_binding(self):
        values={"heat_duty_kw":1000,"overall_u_w_m2k":500,"lmtd_k":40,"lmtd_correction_factor":1}
        self.export["equipment"]["E1"]["values"]=values
        self.export["equipment"]["E1"]["units"]={name:f.FIELD_UNITS[name] for name in values}
        self.context["source_export"]=self.put("export.json",self.export)
        self.response["result"]["normalized_input"]=values
        self.response["result"]["derived_parameters"]={"heat_transfer_area_m2":50}
        self.response["result"]["calculations"]=[{"target_field":"heat_transfer_area_m2","value":50,"formula":"Q/(U*F*LMTD)","evidence":"SYNTHETIC ALGORITHM TEST"}]
        self.constraint(value=50,limit=25)
        row=json.loads((self.root/"constraint.json").read_text())
        row["value_source"]={"kind":"current_selector_derivation","field":"heat_transfer_area_m2"}
        self.context["constraint_evidence"]["E1"]=[self.put("constraint.json",row)]
        plan=f.build_plan(self.response,self.context,self.root)
        self.assertEqual(plan["equipment"][0]["binding_gaps"],[])
        self.assertEqual(plan["equipment"][0]["revision"]["initial_count_bounds"][0]["count"],2)

if __name__ == "__main__": unittest.main(verbosity=2)
