"""Public delivery regression with a synthetic pressure finding and a report correction."""
import hashlib
from importlib.util import find_spec
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

from tools.review_findings import REGISTER, HISTORY, check_delivery_review, retain_review_findings, verify_scoped_checks
from tools.review_scope_history import SCOPE_HISTORY, remember_scope


class DeliveryFindingsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.id = {"case_id": "P", "run_id": "new-run", "task_revision": "R2"}
        self.product = self.put("final.txt", "Lab course report\nVerified lab case\n")
        self.report_locator = "L2"
        self.report_excerpt = "Verified lab case"
        self.binary_artifact = None
        self.rule = {"path": "DEMO_OUT.pressure", "unit": "bar", "basis": "absolute",
                     "comparison": "eq", "expected": 24}
        self.raw = self.put("old-review.json", {"case_id": "P", "task_revision": "R1",
                "module_reviews": [{"issues": [{"id": "P-DROP", "finding": "Outlet pressure must drop",
                                                "criteria": [self.rule]}]}]})
        self.source = {"scope": ["pressure", "report"], "artifacts": [self.product],
                       "parents": [], "preparer_id": "designer", "review_sources": [self.raw]}
        self.recheck = {"id": "P-DROP", "status": "verified_fixed", "locator": "results.DEMO_OUT.pressure",
                        "observation": "Reviewed pressure at the absorber gas outlet."}

    def put(self, path, obj):
        data = obj if isinstance(obj, bytes) else (obj if isinstance(obj, str) else json.dumps(obj, sort_keys=True)).encode()
        (self.root / path).write_bytes(data)
        return {"path": path, "sha256": hashlib.sha256(data).hexdigest()}

    def build(self, value=24, *, unit="bar", basis="absolute", run="new-run", rechecker="reviewer",
              status="verified_fixed", omit=False, final_scope=None, measurement_artifact=None):
        artifact = self.binary_artifact or self.product
        measure = self.put("readback.json", {**self.id, "run_id": run, "artifact": measurement_artifact or artifact,
                    "results": {"DEMO_OUT": {"pressure": {"value": value, "unit": unit, "basis": basis}}}})
        self.source["artifacts"] = [self.product] + ([self.binary_artifact] if self.binary_artifact else [])
        self.source["evidence_refs"] = [measure]
        pressure_check = {"scope": "pressure", "locator": "results.DEMO_OUT.pressure.value", "observed_value": value,
                          "observation": "Checked the pressure of the current candidate.", "evidence_ref": measure}
        report_check = {"scope": "report", "locator": self.report_locator, "excerpt": self.report_excerpt,
                        "observation": "The delivery report includes the case classification.", "evidence_ref": self.product}
        self.source["scope_evidence"] = {"pressure": [measure], "report": [self.product]}
        if self.binary_artifact:
            self.source["scope_evidence"]["pressure"].append(self.binary_artifact)
            pressure_check["artifact_ref"] = self.binary_artifact
        req = {**self.id, "authority": self.put("auth.json", {**self.id, "delivery_review": self.source})}
        if not (self.root / SCOPE_HISTORY).is_file():
            remember_scope(self.root, self.id, self.source, req["authority"])
        final = {**self.id, "kind": "final_delivery_review", "reviewer_id": rechecker,
                 "call_id": "review-42", "scope": self.source["scope"] if final_scope is None else final_scope,
                 "artifacts": self.source["artifacts"], "checks": [pressure_check, report_check], "issues": [],
                 "finding_rechecks": [] if omit else [{**self.recheck, "observed_value": {"value": value, "unit": unit, "basis": basis}, "evidence_ref": measure}]}
        final_ref = self.put("final-review.json", final)
        self.register = {**self.id, "parents": self.source["parents"], "review_sources": self.source["review_sources"],
                    "items": [] if omit else [{"id": "P-DROP", "status": status}],
                    "final_review_ref": final_ref, "invocation_ref": self.put("call.json",
                    {"call_id": "review-42", "reviewer_id": rechecker, "output_sha256": final_ref["sha256"]})}
        self.put(REGISTER, self.register)
        return req

    def codes(self, req):
        return {n["code"] for n in check_delivery_review(self.root, req)["needs"]}

    def change_final(self, update):
        final = json.loads((self.root / self.register["final_review_ref"]["path"]).read_text(encoding="utf-8"))
        update(final)
        self.register["final_review_ref"] = self.put("final-review.json", final)
        self.register["invocation_ref"] = self.put("call.json", {
            "call_id": final["call_id"], "reviewer_id": final["reviewer_id"],
            "output_sha256": self.register["final_review_ref"]["sha256"],
        })
        self.put(REGISTER, self.register)

    def test_report_cannot_borrow_pressure_evidence_or_quote_wrong_line(self):
        request = self.build()
        self.change_final(lambda f: f["checks"].__setitem__(1, {**f["checks"][0], "scope": "report"}))
        self.assertIn("FINAL_REVIEW_EVIDENCE_REQUIRED", self.codes(request))
        self.report_locator = "L1"
        self.assertIn("FINAL_REVIEW_EVIDENCE_REQUIRED", self.codes(self.build()))

    def test_scope_requires_each_frozen_delivery_artifact_to_have_a_readback(self):
        request = self.build()
        authority = json.loads((self.root / request["authority"]["path"]).read_text(encoding="utf-8"))
        authority["delivery_review"]["scope_evidence"]["report"] = [self.source["evidence_refs"][0]]
        request["authority"] = self.put("auth.json", authority)
        self.assertIn("FINAL_REVIEW_EVIDENCE_REQUIRED", self.codes(request))

    def test_docx_requires_a_real_paragraph_at_the_stated_index(self):
        content = BytesIO()
        with ZipFile(content, "w") as package:
            package.writestr("word/document.xml",
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                '<w:body><w:p><w:r><w:t>Report heading</w:t></w:r></w:p>'
                '<w:p><w:r><w:t>Verified lab case</w:t></w:r></w:p></w:body></w:document>')
        self.product = self.put("report.docx", content.getvalue())
        self.report_locator = "PARA2"
        self.assertEqual(self.codes(self.build()), set())
        self.report_locator = "PARA1"
        self.assertIn("FINAL_REVIEW_EVIDENCE_REQUIRED", self.codes(self.build()))
        self.product = self.put("report.docx", b"Not a Word package")
        self.assertIn("FINAL_REVIEW_EVIDENCE_REQUIRED", self.codes(self.build()))

    @unittest.skipUnless(find_spec("pypdf") and find_spec("reportlab"), "optional PDF tooling unavailable")
    def test_pdf_quote_must_be_on_the_declared_physical_page(self):
        from reportlab.pdfgen.canvas import Canvas
        content = BytesIO()
        output = Canvas(content)
        output.drawString(72, 720, "Report heading")
        output.showPage()
        output.drawString(72, 720, "Verified lab case")
        output.save()
        self.product = self.put("report.pdf", content.getvalue())
        self.report_locator = "P2:L1"
        self.assertEqual(self.codes(self.build()), set())
        self.report_locator = "P1:L1"
        self.assertIn("FINAL_REVIEW_EVIDENCE_REQUIRED", self.codes(self.build()))

    def test_binary_requires_exact_same_run_readable_evidence(self):
        self.binary_artifact = self.put("model.bkp", b"synthetic nonutf8 asset: \x96")
        self.assertEqual(self.codes(self.build()), set())
        self.assertIn("FINAL_REVIEW_EVIDENCE_REQUIRED", self.codes(self.build(run="old-run")))
        other = self.put("other.bkp", b"synthetic different model")
        self.assertIn("FINAL_REVIEW_EVIDENCE_REQUIRED", self.codes(self.build(measurement_artifact=other)))
        request = self.build()
        self.change_final(lambda f: f["checks"][0].update(evidence_ref=self.binary_artifact, excerpt="synthetic",
                                                         locator="anywhere"))
        self.assertIn("FINAL_REVIEW_EVIDENCE_REQUIRED", self.codes(request))

    def native_review_fixture(self):
        model = self.put("model.bkp", b"model archive")
        native_text = "; 输入摘要\r\nWARNING native message\r\n"
        inp = self.put("native.inp", native_text.encode("cp936"))
        his = self.put("native.his", native_text.encode("cp936"))
        rep = self.put("TEST_live.rep", "Aspen report\nActual result\n")
        converted = self.put("native-utf8.txt", native_text)
        identity = {"run_id": self.id["run_id"], "case_sha256": model["sha256"]}
        association = {**identity, "verified": True}
        encoding = {**association, "schema": "aspen-native-history-encoding-evidence-v1",
                    "source": "Windows kernel32.GetACP", "acp": 936, "codec": "cp936"}
        audit = self.put("audit.json", {"schema_version": "aspen_clean_delivery_audit/3", **identity,
                         "source": model["path"], "source_sha256": model["sha256"], "label": "TEST",
                         "run": {**identity, "status": "completed"}, "encoding_evidence": encoding,
                         "open_source_direct": True, "source_unchanged": True, "operation_completed": True,
                         "after_run_inp": {**inp, "association": association, "role": "input_export",
                                           "exists": True, "size": len(native_text.encode("cp936"))},
                         "histories": [{**his, "association": association, "decode_verified": True,
                                         "exists": True, "size": len(native_text.encode("cp936")),
                                        "encoding_evidence": {**encoding, "history_sha256": his["sha256"],
                                                              "fallback_used": True,
                                                              "fallback_eligible_for_current_history": True,
                                                              "fallback_roundtrip_verified": True}}]})
        index = self.put("index.json", {"schema": "aspen-native-review-outputs-v1", **self.id,
                         "native_audit_ref": audit, "model_ref": model,
                         "outputs": [{"raw_ref": inp, "conversion": {"codec": "cp936", "text_ref": converted}},
                                     {"raw_ref": rep}]})
        checks = [{"scope": "native", "locator": "L1", "observation": "Read original bytes",
                   "excerpt": excerpt, "evidence_ref": ref, "native_audit_ref": audit}
                  for ref, excerpt in ((inp, "输入摘要"), (his, "输入摘要"), (rep, "Aspen report"))]
        producer = self.put("TEST_streams_blocks.json", {**identity, "moment": "after Run2 before export and close",
                            "streams": {}, "blocks": {},
                            "rep": {**rep, "exists": True, "size": (self.root / rep["path"]).stat().st_size}})
        checks[0]["native_output_index_ref"] = index
        checks[2].update(native_output_index_ref=index, native_producer_ref=producer)
        return [inp, his, rep], [model, converted, audit, index, producer], checks

    def test_native_original_input_history_and_rep_are_read_at_exact_line(self):
        raw, extra, checks = self.native_review_fixture()
        verify_scoped_checks(self.root, {"native": raw}, ["native"], raw, raw + extra, checks, self.id)

    def test_native_raw_evidence_requires_run_digests_conversion_and_exact_line(self):
        raw, extra, checks = self.native_review_fixture()
        stale = {**self.id, "run_id": "old-run"}
        with self.assertRaisesRegex(ValueError, "native audit"):
            verify_scoped_checks(self.root, {"native": raw}, ["native"], raw, raw + extra, checks, stale)
        for index, change in ((0, {"native_output_index_ref": None}), (1, {"locator": "L2"}),
                              (2, {"native_producer_ref": None})):
            with self.subTest(index=index, change=change), self.assertRaises(ValueError):
                modified = [dict(row) for row in checks]
                modified[index].update(change)
                verify_scoped_checks(self.root, {"native": raw}, ["native"], raw, raw + extra, modified, self.id)
        self.put(extra[1]["path"], "different converted text")
        with self.assertRaisesRegex(ValueError, "File changed"):
            verify_scoped_checks(self.root, {"native": raw}, ["native"], raw, raw + extra, checks, self.id)

    def test_new_native_index_cannot_authorize_an_older_report_or_conflicting_input(self):
        raw, extra, checks = self.native_review_fixture()
        previous_input = self.put("previous.inp", "Aspen old input\n")
        previous_report = self.put("previous.rep", "Aspen old report\n")
        index_payload = json.loads((self.root / extra[3]["path"]).read_text(encoding="utf-8"))
        index_payload["outputs"] = [{"raw_ref": previous_input}, {"raw_ref": previous_report}]
        index = self.put("manual-index.json", index_payload)
        for previous, check_index, excerpt in ((previous_input, 0, "Aspen old input"),
                                               (previous_report, 2, "Aspen old report")):
            with self.subTest(original=previous["path"]), self.assertRaisesRegex(ValueError, "native (audit|producer)"):
                check = {**checks[check_index], "evidence_ref": previous, "excerpt": excerpt,
                         "native_output_index_ref": index}
                verify_scoped_checks(self.root, {"native": [previous]}, ["native"], [previous],
                                     raw + extra + [index, previous], [check], self.id)

    def test_report_producer_run_size_and_native_role_must_agree(self):
        raw, extra, checks = self.native_review_fixture()
        producer_path = self.root / extra[-1]["path"]
        valid = json.loads(producer_path.read_text(encoding="utf-8"))
        for changed in ({**valid, "run_id": "old-run"}, {**valid, "rep": {**valid["rep"], "size": 20}},
                        {**valid, "rep": None, "sum": valid["rep"]}):
            with self.subTest(producer=changed), self.assertRaisesRegex(ValueError, "native producer"):
                producer = self.put(producer_path.name, changed)
                check = {**checks[2], "native_producer_ref": producer}
                verify_scoped_checks(self.root, {"native": [raw[2]]}, ["native"], [raw[2]],
                                     raw + extra[:-1] + [producer], [check], self.id)

    def test_standard_audit_sidecar_attests_native_report_without_special_producer(self):
        raw, extra, checks = self.native_review_fixture()
        model, _, audit_ref, _, _ = extra
        audit = json.loads((self.root / audit_ref["path"]).read_text(encoding="utf-8"))
        rep = self.put("plant-summary.rep", "Native output\n")
        report = {**rep, "exists": True, "size": (self.root / rep["path"]).stat().st_size,
                  "evidence_role": "current_run_candidate",
                  "association": {"verified": True, "run_id": self.id["run_id"], "case_sha256": model["sha256"]}}
        audit_ref = self.put(audit_ref["path"], {**audit, "sidecars": [report]})
        check = {key: value for key, value in checks[2].items()
                 if key not in {"native_output_index_ref", "native_producer_ref"}}
        check.update(evidence_ref=rep, excerpt="Native output", native_audit_ref=audit_ref)
        verify_scoped_checks(self.root, {"native": [rep]}, ["native"], [rep], [rep, model, audit_ref], [check], self.id)
        for change in ({"evidence_role": "stale_excluded"}, {"size": 1},
                       {"association": {**report["association"], "run_id": "old-run"}}):
            with self.subTest(sidecar=change), self.assertRaisesRegex(ValueError, "native audit.*report"):
                audit_ref = self.put(audit_ref["path"], {**audit, "sidecars": [{**report, **change}]})
                check["native_audit_ref"] = audit_ref
                verify_scoped_checks(self.root, {"native": [rep]}, ["native"], [rep],
                                     [rep, model, audit_ref], [check], self.id)

    def test_numeric_finding_uses_actual_case_basis_and_frozen_original_test(self):
        self.assertEqual(self.codes(self.build()), set())
        for changes in ({"value": 25}, {"unit": "kPa"}, {"basis": "gauge"}):
            self.assertIn("FINDING_CRITERION_MISSED", self.codes(self.build(**changes)))
        self.assertIn("FINDING_MEASUREMENT_STALE", self.codes(self.build(run="old-run")))
        self.assertIn("REVIEW_FINDING_OPEN", self.codes(self.build(status="adopted")))

    def test_omitted_findings_and_changed_file_fail(self):
        self.assertIn("REVIEW_FINDING_OMITTED", self.codes(self.build(omit=True)))
        req = self.build()
        self.put("final.txt", "different delivery")
        self.assertIn("FINAL_REVIEW_EVIDENCE_REQUIRED", self.codes(req))

    def test_parallel_branches_and_retries_cannot_remove_prior_finding(self):
        extra = self.put("other.json", {"case_id":"P", "issues":[{"id":"TOTAL-VS-PRODUCT"}]})
        retain_review_findings(self.root, "P", [self.raw, extra, self.raw])
        self.assertEqual(len(list((self.root / HISTORY).glob("*.json"))), 2)
        self.source["review_sources"] = []
        req = self.build(omit=True)
        self.assertEqual({n["scope"] for n in check_delivery_review(self.root, req)["needs"]}, {"P-DROP", "TOTAL-VS-PRODUCT"})
        snap = next((self.root / HISTORY).glob("*.json"))
        snap.write_text("{}", encoding="utf-8")
        self.assertIn("FINAL_REVIEW_EVIDENCE_REQUIRED", self.codes(req))

    def test_other_users_review_all_current_artifacts(self):
        self.assertIn("FINAL_REVIEW_EVIDENCE_REQUIRED", self.codes(self.build(rechecker="designer")))
        self.assertIn("FINAL_REVIEW_EVIDENCE_REQUIRED", self.codes(self.build(final_scope=["pressure"])))
        parent = self.put("branch.json", {"case_id":"P", "task_revision":"R1", "parents":[],
                             "review_sources":[], "items":[{"id":"CHECK-REPORT"}]})
        self.source["parents"] = [parent]
        self.assertIn("REVIEW_FINDING_OMITTED", self.codes(self.build()))

    def template(self, manifest):
        path = self.root / self.put("manifest.json", manifest)["path"]
        tool = (Path(__file__).resolve().parents[1] / "plugins/chemical-engineering-skills/skills/"
                "aspen-document-driven-flowsheet/scripts/templates/delivery_gate_audit_template.py")
        cmd = subprocess.run([sys.executable, "-B", str(tool), "--manifest-json", str(path),
                              "--out-dir", str(self.root / "reports")], capture_output=True)
        data = json.loads((self.root / "reports/delivery_gate_audit.json").read_text(encoding="utf-8"))
        self.assertEqual(cmd.returncode == 0, data["passed"])
        return data

    def test_generic_template_empty_missing_inputs_and_boolean_alias_fail(self):
        self.put("counts.json", {"real": None, "zero": 0})
        for manifest in ({}, {"required_files":["."]},
                         {"text_files":["absent"],"forbid_text":[{"pattern":"error"}]},
                         {"forbid_text":[{"pattern":"error"}]},
                         {"json_checks":[{"file":"counts.json","path":"absent","equals":None}]},
                         {"json_checks":[{"file":"counts.json","path":"absent"}]},
                         {"json_checks":[{"file":"counts.json","path":"zero","equals":False}]}):
            self.assertFalse(self.template(manifest)["passed"],manifest)
        narrow = self.template({"json_checks":[{"file":"counts.json","path":"real","equals":None}]})
        self.assertTrue(narrow["passed"])
        self.assertEqual(narrow["scope"],"declared_file_checks_only")

    def test_formal_packaging_uses_shared_review_and_detects_register_if_flag_removed(self):
        req = self.build()
        self.assertTrue(self.template({"formal_delivery":True, "required_files":["final.txt"],"review_request":req})["passed"])
        self.assertFalse(self.template({"required_files":["final.txt"]})["passed"])
        req = self.build(value=25)
        self.assertFalse(self.template({"review_request":req})["passed"])

    def test_formal_package_replays_fullflow_instead_of_counting_six_references(self):
        one = self.put("one-call.json", {"output_ref": self.raw})
        fake = self.put("fake-flow.json", {**self.id, "source_gate":{"independent_calls":[one] * 3},
                                          "scaffold_gate":{"independent_calls":[one] * 3}})
        self.source["fullflow_contract"] = fake
        req = self.build()
        self.register["review_sources"] += [self.raw] * 6
        self.put(REGISTER, self.register)
        result = self.template({"formal_delivery":True, "review_request":req})
        final = next(row for row in result["rows"] if row["gate"] == "final_review")
        self.assertFalse(result["passed"])
        self.assertIn("execution_id", final["evidence"])
        self.assertTrue(final["evidence"]["needs"])
