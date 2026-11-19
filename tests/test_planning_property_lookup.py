"""Replay a discovered thermodynamics gap across revisions without re-querying."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tools.fullflow_gate import _Gate, _article_text
from tools.planning_property_lookup import (
    CASE_BASIS,
    PROPERTY_HISTORY,
    check_property_method_basis,
    record_property_selection_issue,
)


class PropertySelectionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.module = {"id": "FLASH", "thermodynamics": {
            "selection_status": "supported", "components": ["A", "B"], "phases": ["liquid", "vapor"],
            "temperature_range": "300–320 K", "pressure_range": "4–5 bar(a)", "method": "SYNTHETIC-PR",
            "applicability": "Eligible project data support the method for this case.",
        }}
        self.thermo = self.module["thermodynamics"]

    def put(self, name, data):
        raw = (data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)).encode("utf-8")
        (self.root / name).write_bytes(raw)
        return {"path": name, "sha256": hashlib.sha256(raw).hexdigest()}

    def check(self, case_id="CASE", module=None):
        gate = _Gate({}, self.root, {})
        gate.identity = {"case_id": case_id, "task_revision": "R2"}
        check_property_method_basis(gate, module or self.module, _article_text)
        return {row["code"] for row in gate.needs}

    def basis(self, **fields):
        return {"citation": "Synthetic technical source", "source_locator": "physical page 17",
                "case_basis": {key: self.thermo[key] for key in CASE_BASIS},
                "conclusion": "The measured interval covers the declared two-phase pressure and temperature range.",
                **fields}

    def test_independent_primary_project_basis_does_not_require_lookup_or_history(self):
        self.thermo.update(selection_question="External TH03 lookup is optional.",
                           applicability="Use current measurements. TH03 无命中。")
        self.assertEqual(self.check(), set())
        self.assertFalse((self.root / PROPERTY_HISTORY).exists())

    def test_naming_a_graph_query_title_cannot_close_selection(self):
        self.thermo["applicability"] = "TH03-A2 query title gives state equation cases."
        self.assertEqual(self.check(), {"PLAN_PROPERTY_BASIS_REQUIRED"})
        title = self.put("TH03-A2.md", "# TH03-A2 State equation cases")
        item = self.basis(source_kind="graph", node_id="TH03-A2", source_ref=title,
                          locator="L1", excerpt="# TH03-A2 State equation cases")
        self.thermo["selection_basis"] = [item]
        self.assertTrue({"PLAN_PROPERTY_SOURCE_NOT_PRIMARY", "PLAN_PROPERTY_BASIS_REQUIRED"} <= self.check())

    def test_lookup_receipt_named_as_source_is_not_independent_property_data(self):
        self.thermo["source_refs"] = [self.put("receipt.json", {
            "schema": "chemical-design-stage-receipt-v1",
            "calls": [{"kind": "external_property_lookup", "result": {"outcome": "no_hits"}}],
        })]
        self.assertEqual(self.check(), {"PLAN_PROPERTY_BASIS_REQUIRED"})

    def test_original_passage_requires_exact_location_and_same_case_basis(self):
        self.thermo["applicability"] = "Source TH03-A2 guides the method comparison."
        quote = "Vapor-liquid data are available in the declared experimental interval."
        evidence = self.put("book-extract.txt", "Retained source extract\n" + quote + "\n")
        item = self.basis(source_kind="graph", node_id="TH03-A2", source_ref=evidence, locator="L2", excerpt=quote)
        self.thermo["selection_basis"] = [item]
        self.assertEqual(self.check(), set())
        item["locator"] = "L1"
        self.assertIn("PLAN_PROPERTY_BASIS_UNVERIFIED", self.check())
        item["locator"] = "L2"
        self.thermo["pressure_range"] = "8–10 bar(a)"
        self.assertIn("PLAN_PROPERTY_BASIS_UNVERIFIED", self.check())

    def test_failed_lookup_survives_removal_of_label_and_can_be_resolved_by_project_data(self):
        self.thermo["selection_status"] = "uncertain"
        lookup = {"status": "FAILED", "error": {"message": "synthetic unavailable adapter"}}
        issue = record_property_selection_issue(self.root, "CASE", "R1", self.module, "phase coverage", lookup)
        self.assertEqual(record_property_selection_issue(self.root, "CASE", "R1", self.module, "phase coverage", lookup), issue)
        self.assertEqual(len(list((self.root / PROPERTY_HISTORY).glob("*/*.json"))), 1)
        self.thermo["selection_status"] = "supported"
        self.thermo["applicability"] = "Edited without retaining any citation."
        self.assertEqual(self.check(), {"PLAN_PROPERTY_BASIS_REQUIRED"})
        self.assertEqual(self.check(case_id="ANOTHER_CASE"), set())
        self.assertEqual(self.check(module={**self.module, "id": "ANOTHER_MODULE"}), set())
        receipt = self.put("lookup.json", {"collection": "external:TH03", "outcome": "no_hits"})
        self.thermo["selection_basis"] = [self.basis(source_kind="project_data", source_ref=receipt,
            locator="outcome", observed_value="no_hits", resolves=[issue["issue_id"]])]
        self.assertIn("PLAN_PROPERTY_BASIS_UNVERIFIED", self.check())
        data = self.put("project-vle.json", {"measured": {"vapor_a": 0.61}})
        self.thermo["selection_basis"] = [self.basis(source_kind="project_data", source_ref=data,
            locator="measured.vapor_a", observed_value=0.61, resolves=[issue["issue_id"]])]
        self.assertEqual(self.check(), set())
        self.put("project-vle.json", {"measured": {"vapor_a": 0.71}})
        self.assertIn("PLAN_PROPERTY_BASIS_UNVERIFIED", self.check())

    def test_explicitly_inherited_legacy_receipt_retains_its_original_scope(self):
        earlier = self.put("legacy-receipt.json", {"identity": {"case_id": "CASE"},
                            "needs": [{"code": "PROPERTY_SELECTION_REVIEW_REQUIRED", "scope": "FLASH"}]})
        self.thermo["prior_selection_issue_ref"] = earlier
        self.assertEqual(self.check(), {"PLAN_PROPERTY_BASIS_REQUIRED"})
        self.assertEqual(self.check(case_id="OTHER"), {"PLAN_PROPERTY_HISTORY_UNAVAILABLE"})

    def test_numeric_readback_treats_equal_numbers_as_equal_but_never_booleans(self):
        data = self.put("property-parameters.json", {"interaction": 0.0})
        item = self.basis(source_kind="project_data", source_ref=data, locator="interaction", observed_value=0)
        self.thermo["selection_basis"] = [item]
        self.assertEqual(self.check(), set())
        item["observed_value"] = False
        self.assertEqual(self.check(), {"PLAN_PROPERTY_BASIS_UNVERIFIED"})


if __name__ == "__main__":
    unittest.main()
