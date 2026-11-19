"""Structural checks on invented, editable text. No real chemistry or simulator calls."""
import hashlib
from importlib.util import find_spec
from io import BytesIO
import tempfile
import unittest
from pathlib import Path
import os
import subprocess
from zipfile import ZipFile
from unittest.mock import patch

from test_buildable_review import BuildableReviewFixture
from tools.fullflow_gate import _Gate, check_fullflow
from tools.planning_research import _pdf_text


ARTICLE = """First-pass synthetic model
R1 hydrogenates A in feed F to product M with A + H2 -> B.
R1 starts at 310 K within 300 to 320 K.
R1 operates at 4 bar.
R1 consumes 70 % of A entering in F per pass.
F supplies 2 mol/mol H2 per A.
S1 separates A and B from M into D and W.
S1 temperature is 300 K.
S1 pressure is 2 bar.
S1 sends 90 % of feed A to D.
S1 sends 10 % of feed B to D.
The flash calculates the split by fugacity equality.
The outlet pressure follows inlet minus line loss, assessed in bar.
R1 retains pressure-law kinetics for the reactor island because its catalyst and operating window match the study.
S1 retains A-enriching rectification for the separation island because the measured volatility favors A in the vapor.
For this synthetic balance exercise the accepted absolute deviation on each conversion, recovery, purity or cut is 0.01 percentage points.
"""


class BuildableInputs:
    def __init__(self, root):
        self.root = Path(root)
        self.article = self.put("plan.md", ARTICLE)
        self.source = self.put("requirements.txt", "Invented test-only model input basis.")
        lines = ARTICLE.splitlines()
        self.tolerance = {"kind": "absolute", "value": 0.01, "unit": "percentage_point", "basis": lines[-1],
                          "source_ref": self.put("synthetic-acceptance.txt", lines[-1])}

        def quantity(name, value, unit, line, **more):
            return {"name": name, "value": value, "unit_or_basis": unit, "basis": lines[line],
                    "article_excerpt": lines[line], "source_ref": self.source, **more}

        def stream(tag, components):
            return {"stream_id": tag, "composition": {c: 1 for c in components}, "basis": "mol/s", "source_ref": self.source}

        def first(block, specs):
            return {"block_type": block, "source_ref": self.source, "required_inputs": list(specs),
                    "inputs": [{"name": name, "spec_id": spec} for name, spec in specs.items()]}

        self.r = {"id": "R1", "node_ids": ["R1"], "role": "reaction", "physical_service": "hydrogenates A",
                  "article_excerpt": lines[1], "inlets": [stream("F", ["A", "H2"])], "outlets": [stream("M", ["A", "B"])],
                  "reaction": {
                      "network": [{"id": "rx", "equation": "A + H2 -> B", "article_excerpt": lines[1], "source_ref": self.source}],
                      "conditions": [quantity("temperature", 310, "K", 2, mode="adjustable", bounds={"lower": 300, "upper": 320}),
                                     quantity("pressure", 4, "bar", 3, mode="fixed")],
                      "extent": [quantity("conversion", 70, "%", 4, kind="conversion", reaction_id="rx", key_reactant="A",
                                          denominator="A entering R1 in F", pass_basis="per_pass", acceptance_tolerance=self.tolerance)],
                      "hydrogen_basis": quantity("H2 feed ratio", 2, "mol/mol", 5, mode="fixed")},
                  "first_model": first("RStoic", {"FRAC": "reaction.extent.0", "T": "reaction.conditions.0",
                                                  "P": "reaction.conditions.1"})}
        product = {**stream("D", ["A", "B"]), "composition": {"A": 0.9, "B": 0.1}}
        residue = {**stream("W", ["A", "B"]), "composition": {"A": 0.1, "B": 0.9}}
        self.s = {"id": "S1", "node_ids": ["S1"], "role": "separation", "physical_service": "separates A and B",
                   "article_excerpt": lines[6], "inlets": [stream("M", ["A", "B"])], "outlets": [product, residue],
                  "separation": {"initial_method": "Apply feed-component recoveries to D and close W by balance",
                                 "conditions": [quantity("temperature", 300, "K", 7, mode="fixed"),
                                                quantity("pressure", 2, "bar", 8, mode="fixed")],
                                 "targets": [quantity("A cut", 90, "%", 9, kind="recovery", component="A", outlet="D", comparison="ge", acceptance_tolerance=self.tolerance),
                                             quantity("B cut", 10, "%", 10, kind="recovery", component="B", outlet="D", comparison="le", acceptance_tolerance=self.tolerance)]},
                  "first_model": first("SEP", {"A recovery": "separation.targets.0", "B recovery": "separation.targets.1"})}
        self.r["reaction"]["planning_research"], self.s["separation"]["planning_research"] = self.research()
        self.gate = _Gate({}, self.root, {})
        self.gate.modules = {"R1": self.r, "S1": self.s}
        for module in self.gate.modules.values():
            module["thermodynamics"] = {"selection_status": "supported"}

    def put(self, name, content):
        raw = content.encode() if isinstance(content, str) else content
        (self.root / name).write_bytes(raw)
        return {"path": name, "sha256": hashlib.sha256(raw).hexdigest()}

    def research(self):
        rate = {
            "rate_law": "r_A = k*p_A*p_H2",
            "rate_units": "mol/(kg_cat s)",
            "rate_basis": "A consumption per mass of catalyst",
            "parameters": "k = 0.002 mol/(kg_cat s bar^2) at 310 K",
            "catalyst": "Cat-X pellets",
            "validity": "295–325 K and 3–5 bar with inlet H2/A 1.8–2.2",
        }
        phase = {"phases": ["vapor", "liquid"], "phase_data": "A/B relative volatility = 4.0",
                 "operating_range": "295–310 K and 1.8–2.2 bar"}
        passages = [
            "Case A/H2 with gaseous feed. " + ". ".join(rate.values()) + ".",
            "Binary A/B vapor-liquid measurements: " + phase["phase_data"] + " over " + phase["operating_range"] + ".",
        ]
        self.study = self.put("technical-study.txt", "\n".join(passages))

        def evidence(index, locator):
            return {"source_ref": self.study, "locator": f"L{index+1}", "excerpt": passages[index],
                    "citation": "Synthetic measurements for unit test only", "source_locator": locator}

        rr = {"selected_candidate_id": "rx-rate", "selection_criterion": "Reported law covers the same rate basis and nominal window",
              "alternatives_limit": "This synthetic test case fixes Cat-X and measures only this fitted rate mechanism",
              "article_excerpt": ARTICLE.splitlines()[13],
              "response_required": True, "response_basis": "Predict A conversion at the case pressure and varied residence time",
              "target_mappings": [{"spec_id": "reaction.extent.0", "model_use": "verification",
                                   "basis": "Verify 70% per-pass A conversion using A entering R1 as denominator"}],
              "candidates": [{"id": "rx-rate", "method": "pressure-law kinetics", "strategy": "kinetic",
                              "mechanism": "Gas phase hydrogenation of A over Cat-X",
                              "applicability": "Gaseous A/H2 and Cat-X overlap 310 K, 4 bar and H2/A of 2",
                              "assessment": "Use only inside the measured catalyst and process window",
                              "transfer_scope": "same_system",
                              "evidence": [evidence(0, "Eq. 1 and range notes")],
                              "basis": rate, "mapped_inputs": [{"parameter": "RPlug A consumption rate",
                                                                "source_basis": rate["rate_law"],
                                                                "model_use": "Use partial pressures in bar and a catalyst-mass rate basis"}]}]}
        ss = {"selected_candidate_id": "vle", "selection_criterion": "Staged VLE can enrich A while retaining B",
              "alternatives_limit": "The synthetic task restricts testing to an A/B distillation service without added agents",
              "article_excerpt": ARTICLE.splitlines()[14],
              "target_mappings": [{"spec_id": f"separation.targets.{i}", "model_use": "verification", "basis": basis}
                                  for i, basis in enumerate(("Verify A recovery to D on the inlet M basis",
                                                              "Verify B leakage to D on the inlet M basis"))],
              "candidates": [{"id": "vle", "method": "A-enriching rectification", "mechanism": "Staged vapor-liquid equilibrium",
                              "applicability": "A/B vapor-liquid data spans 300 K and 2 bar",
                              "assessment": "Use staged rectification and verify the net D and W recoveries in the later island",
                              "transfer_scope": "same_system",
                              "evidence": [evidence(1, "Table 1 A/B VLE")], "basis": phase,
                              "mapped_inputs": [{"parameter": "A light key / B heavy key ordering", "source_basis": phase["phase_data"],
                                                 "model_use": "Use component ordering and validate a physical column at the frozen cuts"}]}]}
        return rr, ss

    def add_feed(self):
        plan = ARTICLE + "F enters with 10 kg/h at 310 K and 4 bar, with mass fractions A 0.75 and H2 0.25.\n"
        self.article = self.put("plan.md", plan)
        excerpt = plan.splitlines()[-1]
        feed = self.r["inlets"][0]
        feed.update(composition={"A": 0.75, "H2": 0.25}, basis="mass fraction", article_excerpt=excerpt,
                    feed_state={k: {"name": k, "value": value, "unit_or_basis": unit, "basis": "mass feed F",
                                    "source_ref": self.source, "mode": "fixed", "article_excerpt": excerpt}
                                for k, value, unit in [("flow", 10, "kg/h"), ("temperature", 310, "K"), ("pressure", 4, "bar")]})
        return feed


class IntegratedBuildableFixture(BuildableReviewFixture):
    """Complete synthetic article/contract/handoff/three-call dossier for public source entry."""
    def __init__(self, root):
        super().__init__(root)
        plan = BuildableInputs(root)
        self.balance_integrated_plan(plan)
        self.article = plan.article
        self.contract["planning_scope"] = "buildable_flowsheet"
        for record, module in zip(self.modules, (plan.r, plan.s)):
            thermo = {**record["thermodynamics"], **module["thermodynamics"], "components": ["A", "B", "H2"]}
            record.update(module, thermodynamics=thermo, auxiliaries=[])
            record["auxiliary_requirements"] = self.modules[1]["auxiliary_requirements"]
        self.modules[1]["separation"].pop("conditions")
        self.rebuild_source()
        gate = self.contract["source_gate"]
        data = self.read(gate["handoff_input_ref"])
        data["nodes"] = [{"id": x, "kind": "external" if x not in ("R1", "S1") else "process"}
                         for x in ("FEED", "R1", "S1", "PRODUCT", "WASTE")]
        data["streams"] = [{"id": tag, "from": a, "to": b, "state": "documented", "evidence": "synthetic article", "gap": None}
                           for tag, a, b in [("F", "FEED", "R1"), ("M", "R1", "S1"), ("D", "S1", "PRODUCT"), ("W", "S1", "WASTE")]]
        data["control_volumes"][0].update(members=["R1", "S1"], inflows=["F"], outflows=["D", "W"])
        for unit in data["source_review"]["units"]:
            unit["stream_ids"] = ["F"]
        gate.update(self.write_handoff(data), planning_article_ref=self.article)
        gate.update(self.reviews("source", 3, {"design_basis_sha256": gate["design_basis_ref"]["sha256"]}))
        parser = _Gate({}, self.root, {})
        parser.modules = {m["id"]: m for m in self.modules}
        parser.buildable_plan(gate)
        parser.buildable_interfaces(data)
        assert not parser.needs, parser.needs
        self.specs = parser.buildable_review_specs
        self.annotate_source_reviews()

    @staticmethod
    def balance_integrated_plan(plan):
        feed = plan.add_feed()
        state = feed["feed_state"]
        state["flow"].update(value=30, unit_or_basis="mol/s", basis="total molar feed F")
        temperature = state["temperature"]
        pressure = state["pressure"]
        feed_excerpt = (f"F enters with 30 mol/s at {temperature['value']} {temperature['unit_or_basis']} and "
                        f"{pressure['value']} {pressure['unit_or_basis']}, with component rates A 10 and H2 20 mol/s.")
        feed.update(composition={"A": 10, "H2": 20}, basis="mol/s", article_excerpt=feed_excerpt)
        for setting in state.values():
            setting["article_excerpt"] = feed_excerpt
            setting["basis"] = "molar feed F"

        balance = {
            "M": ({"A": 3, "B": 7, "H2": 13}, "M carries A 3, B 7 and H2 13 mol/s from R1 into S1."),
            "D": ({"A": 2.7, "B": 0.7, "H2": 13}, "D carries A 2.7, B 0.7 and H2 13 mol/s to light-ends handling."),
            "W": ({"A": 0.3, "B": 6.3}, "W carries A 0.3 and B 6.3 mol/s to heavy-ends handling."),
        }
        for stream in [*plan.r["outlets"], *plan.s["inlets"], *plan.s["outlets"]]:
            composition, excerpt = balance[stream["stream_id"]]
            stream.update(composition=dict(composition), basis="mol/s", article_excerpt=excerpt)

        split = "S1 sends 100 % of feed H2 to light outlet D, leaving zero H2 in W."
        separation = plan.s["separation"]
        for target in separation["targets"]:
            target["comparison"] = "eq"
        separation["targets"].append({"name": "H2 recovery to D", "value": 100, "unit_or_basis": "%",
                                      "kind": "recovery", "component": "H2", "outlet": "D", "comparison": "eq",
                                      "acceptance_tolerance": plan.tolerance,
                                      "basis": "H2 in M entering S1", "article_excerpt": split, "source_ref": plan.source})
        first = plan.s["first_model"]
        first["required_inputs"].append("H2 recovery")
        first["inputs"].append({"name": "H2 recovery", "spec_id": "separation.targets.2"})
        research = separation["planning_research"]
        research["target_mappings"].append({"spec_id": "separation.targets.2", "model_use": "verification",
                                            "basis": "Verify H2 in the light outlet D on the H2 in M basis"})
        candidate = research["candidates"][0]
        phase_data = "A/B relative volatility = 4.0 with H2 noncondensable at the tested load"
        window = "305–315 K and 3.8–4.2 bar"
        candidate["basis"].update(phase_data=phase_data, operating_range=window)
        candidate["applicability"] = "The A/B/H2 study covers 310 K, 4 bar and the nominal H2 fraction in M."
        candidate["mapped_inputs"][0]["source_basis"] = phase_data
        rate = plan.r["reaction"]["planning_research"]["candidates"][0]["evidence"][0]
        phase = f"A/B with H2 fed at 13/23 mole fraction: {phase_data}, over {window}."
        study = plan.put("integrated-technical-study.txt", rate["excerpt"] + "\n" + phase)
        rate["source_ref"] = study
        candidate["evidence"][0].update(source_ref=study, excerpt=phase)

        excluded_lines = {"S1 temperature is 300 K.", "S1 pressure is 2 bar.", "The flash calculates the split by fugacity equality.",
                          "The outlet pressure follows inlet minus line loss, assessed in bar."}
        article = [line for line in ARTICLE.splitlines() if line not in excluded_lines]
        article.extend([feed_excerpt, *(row[1] for row in balance.values()), split,
                        "The nominal SEP inherits the inlet state, with zero planned pressure drop."])
        plan.article = plan.put("plan.md", "\n".join(article) + "\n")


class BuildablePlanTests(unittest.TestCase, BuildableInputs):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        BuildableInputs.__init__(self, self.tmp.name)

    def run_plan(self):
        self.gate.needs.clear()
        self.gate.buildable_plan({"planning_article_ref": self.article})
        return {r["code"] for r in self.gate.needs}

    def test_valid_initial_conditions_and_independent_component_splits(self):
        self.assertEqual(self.run_plan(), set(), self.gate.needs)
        target = self.gate.buildable_review_specs["R1"]["reaction.extent.0"]
        self.assertEqual((target["value"], target["article_locator"], target["node_id"]), (70, "L5", "R1"))
        self.assertEqual(self.gate.buildable_review_specs["R1"]["reaction.conditions.0.bounds.lower"]["value"], 300)
        self.assertEqual(self.gate.buildable_operating_rules["S1"]["separation.targets.0"]["comparison"], "ge")
        self.assertEqual(self.gate.summary["planning_research"]["unresolved_module_ids"], [])

    def test_missing_conversion_or_percentage_basis(self):
        row = self.r["reaction"]["extent"][0]
        row.pop("value")
        self.assertIn("PLAN_NOMINAL_REQUIRED", self.run_plan())
        row.update(value=70, unit_or_basis="fraction", pass_basis="unknown")
        self.assertTrue({"PLAN_FRACTION_UNIT_OR_RANGE", "PLAN_CONVERSION_BASIS", "PLAN_FIXED_CONVERSION"} <= self.run_plan())
        self.assertTrue(any(issue["scope"].startswith("module.R1") for issue in self.gate.needs))

    def test_source_and_hydrogen_sizing_basis_required(self):
        self.r["reaction"].pop("hydrogen_basis")
        self.r["reaction"]["network"][0].pop("source_ref")
        self.run_plan()
        for scope in ("reaction.hydrogen_basis", "network.0.source_ref"):
            self.assertTrue(any(scope in row["scope"] for row in self.gate.needs), self.gate.needs)

    def test_repeated_or_absent_split_cannot_determine_other_component(self):
        self.s["separation"]["targets"].pop()
        self.assertIn("PLAN_SEPARATION_UNDERSPECIFIED", self.run_plan())
        self.s["separation"]["targets"] *= 2
        self.assertTrue({"PLAN_DUPLICATE_RECOVERY", "PLAN_SEPARATION_UNDERSPECIFIED"} <= self.run_plan())

    def test_purity_rank_resolves_binary_outlets(self):
        first, second = self.s["separation"]["targets"]
        first.update(kind="purity", amount_basis="mole")
        second.update(kind="purity", amount_basis="mole", component="A", outlet="W")
        first["article_excerpt"] = "S1 target in D is 90 mol% A."
        second["article_excerpt"] = "S1 target in W is 10 mol% A."
        self.article = self.put("plan.md", ARTICLE + first["article_excerpt"] + "\n" + second["article_excerpt"])
        self.assertNotIn("PLAN_SEPARATION_UNDERSPECIFIED", self.run_plan())
        self.assertIn("PLAN_NATIVE_SEP_SPLITS", self.run_plan())
        self.s["first_model"]["inputs"] = [
            {"name": name, "value": val, "unit_or_basis": "%", "mode": "derived", "kind": "recovery",
             "component": comp, "outlet": "D", "basis": "derived synthetic component balance",
             "article_excerpt": line, "source_ref": self.source}
            for name, comp, val, line in [("A recovery", "A", 90, ARTICLE.splitlines()[9]),
                                          ("B recovery", "B", 10, ARTICLE.splitlines()[10])]]
        self.assertFalse(self.run_plan(), self.gate.needs)

    def test_aggregate_sep_runs_without_choosing_tower_or_internal_tp(self):
        self.s["separation"].pop("conditions")
        self.assertFalse(self.run_plan(), self.gate.needs)
        self.s["separation"] = {"initial_method": "absorption"}
        self.assertIn("PLAN_SEPARATION_UNDERSPECIFIED", self.run_plan())

    def test_placeholders_still_require_reactor_and_separation_research(self):
        for role, module in [("reaction", self.r), ("separation", self.s)]:
            module[role].pop("planning_research")
        self.assertEqual(self.run_plan(), {"PLAN_REACTION_RESEARCH_REQUIRED", "PLAN_SEPARATION_RESEARCH_REQUIRED"})
        self.assertEqual(self.gate.summary["planning_research"]["unresolved_module_ids"], ["R1", "S1"])

    def test_checked_source_bytes_and_material_passage_are_required(self):
        candidate = self.s["separation"]["planning_research"]["candidates"][0]
        candidate["evidence"][0]["locator"] = "L1"
        self.assertIn("PLAN_RESEARCH_SOURCE_PASSAGE", self.run_plan())
        self.assertEqual(self.gate.summary["planning_research"]["unresolved_module_ids"], ["S1"])
        candidate["evidence"][0]["locator"] = "L2"
        candidate["basis"]["phase_data"] = "Generic reference to VLE methods"
        self.assertIn("PLAN_SEPARATION_RESEARCH_BASIS", self.run_plan())
        (self.root / self.study["path"]).write_text("source replaced", encoding="utf-8")
        self.assertIn("EVIDENCE_UNAVAILABLE", self.run_plan())

    @unittest.skipUnless(find_spec("pypdf") and find_spec("reportlab"), "optional PDF tooling unavailable")
    def test_technical_pdf_honors_physical_page_and_text_line(self):
        from reportlab.pdfgen.canvas import Canvas

        candidate = self.s["separation"]["planning_research"]["candidates"][0]
        citation = candidate["evidence"][0]
        buf = BytesIO()
        pdf = Canvas(buf)
        pdf.drawString(20, 750, "First page covers a different phase system.")
        pdf.showPage()
        pdf.drawString(20, 750, "Measurements for the synthetic case")
        pdf.drawString(20, 730, citation["excerpt"])
        pdf.showPage()
        pdf.save()
        citation.update(source_ref=self.put("vle.pdf", buf.getvalue()), locator="P2:L2", source_locator="p. 2, Table 1")
        self.assertFalse(self.run_plan(), self.gate.needs)
        citation["locator"] = "P1:L2"
        self.assertIn("PLAN_RESEARCH_SOURCE_PASSAGE", self.run_plan())

    def test_direct_pdf_extraction_has_a_bounded_local_reader_fallback(self):
        reader = self.root / ("pdftotext.exe" if os.name == "nt" else "pdftotext")
        reader.touch()
        reader.chmod(0o700)
        source = self.root / "file with spaces.pdf"
        result = subprocess.CompletedProcess([], 0, stdout=b"\nFirst line\r\n\r\nTechnical measurement\n\x0c", stderr=b"")
        with (patch("tools.planning_research._pypdf_text", side_effect=ImportError),
              patch("tools.planning_research.os.get_exec_path", return_value=[str(self.root)]),
              patch("tools.planning_research.subprocess.run", return_value=result) as extraction):
            self.assertEqual(_pdf_text(source, 3), "First line\nTechnical measurement")
        args, options = extraction.call_args
        self.assertEqual(args[0], [str(reader), "-f", "3", "-l", "3", "-layout", "-enc", "UTF-8", str(source), "-"])
        self.assertEqual(options["timeout"], 15)

    def test_eligible_analog_preserves_scoped_later_gap_and_first_model(self):
        research = self.s["separation"]["planning_research"]
        research["candidates"][0]["transfer_scope"] = "analog"
        self.assertIn("PLAN_RESEARCH_PROVISIONAL_SCOPE", self.run_plan())
        research["provisional"] = {"unresolved_inputs": ["A/B measured VLE at the case solvent loading"],
                                   "refine_trigger": "Obtain mixture VLE and compare with the selected property model",
                                   "independent_work": "Retain the sourced nominal component splits for the SEP scaffold"}
        self.assertFalse(self.run_plan(), self.gate.needs)
        summary = self.gate.summary["planning_research"]
        self.assertEqual(summary["provisional_module_ids"], ["S1"])
        self.assertEqual(summary["modules"][1]["independent_work"], research["provisional"]["independent_work"])

    def test_fixed_basis_can_exclude_kinetic_model_using_actual_technical_evidence(self):
        plan = self.r["reaction"]["planning_research"]
        candidate = plan["candidates"][0]
        quote = "Extent fixed at measured nominal conversion for a single run. No residence-time measurements were taken."
        source = self.put("nominal-test.txt", quote)
        evidence = {"source_ref": source, "locator": "L1", "excerpt": quote,
                    "citation": "Synthetic test report", "source_locator": "Single-run protocol"}
        self.article = self.put("plan.md", ARTICLE + "R1 retains a single-condition balance for the fixed test scope.\n")
        plan.update(article_excerpt="R1 retains a single-condition balance for the fixed test scope.",
                    response_required=False, response_basis="Only nominal fixed conversion is within case requirements")
        candidate.update(strategy="balance", method="single-condition balance", evidence=[evidence],
                         basis={"relation": "Extent fixed at measured nominal conversion", "validity": "for a single run",
                                "limit": "Cannot determine conversion change with residence time"},
                         mapped_inputs=[{"parameter": "fixed conversion", "source_basis": "measured nominal conversion",
                                         "model_use": "Use nominal feed basis only"}])
        self.assertIn("PLAN_REACTION_RESEARCH_KINETICS_SCREEN", self.run_plan())
        plan["kinetics_exclusion"] = {"source_finding": "No residence-time measurements were taken.",
                                      "case_limit": "Cannot derive kinetic response from the checked nominal test", "evidence": [evidence]}
        self.assertFalse(self.run_plan(), self.gate.needs)
        plan.update(response_required=True,
                    provisional={"unresolved_inputs": ["Residence-time data"],
                                 "refine_trigger": "Obtain matching catalyst and residence-time measurements",
                                 "independent_work": "Verify material balances at the established nominal point"})
        self.assertEqual(self.run_plan(), {"PLAN_REACTION_RESEARCH_RESPONSE_OPEN"})
        summary = self.gate.summary["planning_research"]
        self.assertEqual(summary["unresolved_module_ids"], ["R1"])
        self.assertTrue(summary["modules"][0]["response_open"])
        self.assertEqual(summary["modules"][0]["independent_work"], plan["provisional"]["independent_work"])

    def test_multiple_conditions_need_verified_paired_numeric_responses(self):
        plan = self.r["reaction"]["planning_research"]
        relation = "Interpolate conversion between tested residence times"
        validity = "A/H2 at 310 K and 4 bar over Cat-X"
        observations = [("5 s residence time", "55 % inlet-based A conversion", 55),
                        ("10 s residence time", "70 % inlet-based A conversion", 70)]
        pairs = [f"{condition}: {result}." for condition, result, _ in observations]
        quote = ". ".join([relation, validity, *pairs])
        ref = self.put("multi-condition-test.txt", quote)
        evidence = {"source_ref": ref, "locator": "L1", "excerpt": quote,
                    "citation": "Test-only time sweep", "source_locator": "Results table"}
        empirical = {"id": "residence-time-fit", "method": "residence-time interpolation", "strategy": "multi_condition",
                     "mechanism": "Scoped empirical response of hydrogenation over the same catalyst",
                     "applicability": "Case matches tested state and varies only residence time between 5 and 10 s",
                     "assessment": "Use for specified response with the same reactor conditions and catalyst",
                     "transfer_scope": "same_system", "evidence": [evidence],
                     "basis": {"relation": relation, "validity": validity, "limit": "No extrapolation beyond tested times or T/P",
                               "measurements": [{"condition": condition, "result": result, "value": value,
                                                 "unit_or_basis": "%", "source_basis": pair}
                                                for (condition, result, value), pair in zip(observations, pairs)]},
                     "mapped_inputs": [{"parameter": "interpolation domain", "source_basis": validity,
                                        "model_use": "Allow interpolation only for this mixture, temperature and pressure"}]}
        plan["candidates"].append(empirical)
        plan.update(selected_candidate_id="residence-time-fit", article_excerpt="R1 retains residence-time interpolation.")
        self.article = self.put("plan.md", ARTICLE + plan["article_excerpt"])
        self.assertFalse(self.run_plan(), self.gate.needs)
        first, second = empirical["basis"]["measurements"]
        second["source_basis"] = first["source_basis"]
        self.assertIn("PLAN_REACTION_RESEARCH_BASIS", self.run_plan())
        second.update(source_basis=pairs[1], value="reported")
        self.assertIn("PLAN_REACTION_RESEARCH_BASIS", self.run_plan())

    def test_research_must_map_each_original_target(self):
        self.s["separation"]["planning_research"]["target_mappings"].pop()
        self.assertIn("PLAN_RESEARCH_TARGET_MAPPING", self.run_plan())
        self.assertTrue(any("separation.targets.1" in issue["detail"] for issue in self.gate.needs))

    def test_external_feeds_are_determined_from_actual_stream_endpoints(self):
        feed = self.add_feed()
        self.assertFalse(self.run_plan(), self.gate.needs)
        data = {"nodes": [{"id": x, "kind": "external"} for x in ("FEED", "PRODUCT", "WASTE")],
                "streams": [{"id": tag, "from": src, "to": dest} for tag, src, dest in
                            [("F", "FEED", "R1"), ("M", "R1", "S1"), ("D", "S1", "PRODUCT"), ("W", "S1", "WASTE")]]}
        self.gate.buildable_interfaces(data)
        self.assertFalse(self.gate.needs, self.gate.needs)
        self.assertIn("inlets.0.feed_state.flow", self.gate.buildable_review_specs["R1"])
        self.assertNotIn("inlets.0.feed_state.flow", self.gate.buildable_review_specs["S1"])
        feed["feed_state"]["flow"]["unit_or_basis"] = "kg/kg"
        feed["feed_state"]["pressure"]["unit_or_basis"] = "K"
        self.gate.buildable_interfaces(data)
        self.assertTrue({"PLAN_FEED_RATE_BASIS", "PLAN_CONDITION_UNIT"} <= {n["code"] for n in self.gate.needs})
        feed["feed_state"].pop("flow")
        self.gate.buildable_interfaces(data)
        self.assertTrue(any("feed_state.flow" in n["scope"] for n in self.gate.needs))
        self.gate.needs.clear()
        data["streams"][2]["id"] = "TYPO"
        self.gate.buildable_interfaces(data)
        self.assertIn("PLAN_INTERFACE_TOPOLOGY", {n["code"] for n in self.gate.needs})

    def test_model_determined_extent_still_has_quantitative_benchmark(self):
        self.r["first_model"]["block_type"] = "REquil"
        self.r["first_model"]["inputs"].pop(0)
        self.r["first_model"]["required_inputs"].pop(0)
        row = self.r["reaction"]["extent"][0]
        row.update(kind="model_determined", governing_model="equilibrium constant at T")
        self.assertFalse(self.run_plan(), self.gate.needs)
        row["value"] = "equilibrium"
        self.assertIn("PLAN_NOMINAL_REQUIRED", self.run_plan())

    def test_only_real_governing_separation_model_may_determine_residual_splits(self):
        self.s["separation"]["targets"].pop()
        self.s["separation"]["planning_research"]["target_mappings"].pop()
        self.s["first_model"]["required_inputs"].pop()
        self.s["first_model"]["inputs"].pop()
        self.s["separation"]["governing_model"] = {"relation": "fugacity equality", "source_refs": [self.source],
                                                   "article_excerpt": ARTICLE.splitlines()[11]}
        self.assertIn("PLAN_SEPARATION_UNDERSPECIFIED", self.run_plan())
        self.s["first_model"] = {"block_type": "Flash2", "source_ref": self.source, "required_inputs": ["T", "P"],
                                 "inputs": [{"name": "T", "spec_id": "separation.conditions.0"}, {"name": "P", "spec_id": "separation.conditions.1"}]}
        self.assertFalse(self.run_plan(), self.gate.needs)

    def test_missing_native_input_and_auxiliary_model_identified(self):
        self.r["first_model"]["inputs"].pop()
        self.r["auxiliaries"] = [{"node_id": "H1", "kind": "heating"}]
        self.assertIn("PLAN_MODEL_INPUT_COVERAGE", self.run_plan())
        self.assertTrue(any("auxiliaries.0.first_model" in row["scope"] for row in self.gate.needs))

    def test_bounds_need_reproducible_nominal_or_sourced_determined_relation(self):
        row = self.r["reaction"]["conditions"][0]
        row["value"] = "300 to 320"
        self.assertIn("PLAN_OPERATING_BOUNDS", self.run_plan())
        row = self.r["reaction"]["conditions"][1]
        row.update(mode="determined", value="inlet minus line loss", depends_on=["F pressure", "line pressure drop"],
                   article_excerpt=ARTICLE.splitlines()[12])
        self.r["reaction"]["conditions"][0]["value"] = 310
        self.assertFalse(self.run_plan(), self.gate.needs)
        row.pop("depends_on")
        self.assertIn("INVALID_SHAPE", self.run_plan())

    def test_complete_inventory_still_needs_nominal_native_inputs(self):
        model = self.r["first_model"]
        model["required_inputs"].append("duration")
        model["inputs"].append({"name": "duration", "mode": "fixed", "value": "2–5", "unit_or_basis": "h",
                                "basis": "synthetic initial operation", "article_excerpt": "Duration is 2–5 h.",
                                "source_ref": self.source})
        self.article = self.put("plan.md", ARTICLE + "Duration is 2–5 h.")
        self.assertIn("PLAN_NOMINAL_REQUIRED", self.run_plan())

    def test_rehashed_substitute_article_or_stale_numbers_fail(self):
        self.article = self.put("plan.md", "# Other case\nR1 exists but its design changed.")
        self.assertIn("PLAN_ARTICLE_EXCERPT", self.run_plan())
        self.article = self.put("plan.md", ARTICLE)
        row = self.r["reaction"]["extent"][0]
        row["value"] = 7
        self.assertIn("PLAN_ARTICLE_VALUE", self.run_plan())
        row.update(value=70, unit_or_basis="fraction")
        self.assertIn("PLAN_ARTICLE_UNIT", self.run_plan())

    def test_json_renamed_as_markdown_is_not_an_article(self):
        self.article = self.put("plan.md", '{"case":"test"}')
        self.assertIn("PLAN_ARTICLE_UNREADABLE", self.run_plan())

    def test_docx_article_paragraphs_have_same_locators(self):
        path = self.root / "plan.docx"
        with ZipFile(path, "w") as doc:
            paragraphs = "".join(f"<w:p><w:r><w:t>{line}</w:t></w:r></w:p>" for line in ARTICLE.splitlines())
            doc.writestr("word/document.xml", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                         + "<w:body>" + paragraphs + "</w:body></w:document>")
        self.article = self.put("plan.docx", path.read_bytes())
        self.assertFalse(self.run_plan(), self.gate.needs)
        self.assertEqual(self.gate.buildable_review_specs["R1"]["reaction.extent.0"]["article_locator"], "L5")

    def test_uncertain_property_prerequisite_localizes_unresolved_module(self):
        self.s["thermodynamics"]["selection_status"] = "outside_range"
        self.assertEqual(self.run_plan(), {"PLAN_PROPERTY_REVIEW_OPEN"})
        self.assertEqual(self.gate.needs[0]["scope"], "module.S1.thermodynamics")

    def test_complete_public_source_stage_and_exact_article_binding(self):
        fixture = IntegratedBuildableFixture(self.root)
        payload = {"stage": "source", "fullflow_contract": fixture.put("contract.json", fixture.contract)}
        result = check_fullflow(payload, self.root)
        self.assertEqual(result["status"], "EVIDENCE_STRUCTURE_CONSISTENT", result["needs"])
        self.assertTrue(result["buildable_plan_required"])
        self.assertFalse(result["engineering_accepted"])
        (self.root / fixture.article["path"]).write_text("Different revision", encoding="utf-8")
        self.assertEqual(check_fullflow(payload, self.root)["status"], "ACTION_REQUIRED")


if __name__ == "__main__":
    unittest.main()
