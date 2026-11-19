"""Synthetic scaffold evidence. Nothing invokes Aspen or a review provider."""
import tempfile
import unittest

from test_fullflow_gate import FullflowFixture
from test_design_target_tolerance import prepare_scaffold
from tools.fullflow_gate import _Gate


class RecycleScaffoldFixture(FullflowFixture):
    def handoff(self):
        data = self.read(super().handoff()["handoff_input_ref"])
        data["streams"].append({"id": "RETURN", "from": "S1", "to": "R1", "state": "documented",
                                "evidence": "Synthetic return connector", "gap": None})
        return self.write_handoff(data)

    def freeze_interface_names(self, names):
        source = self.contract["source_gate"]
        basis = self.read(source["design_basis_ref"])
        basis["scaffold_interface_names"] = names
        source["design_basis_ref"] = self.put("design-basis.json", basis)
        source.update(self.reviews("source", 3, {"design_basis_sha256": source["design_basis_ref"]["sha256"]}))

    def verifications(self, stage, index, module):
        checks = super().verifications(stage, index, module)
        basis = self.reference("design-basis.json")
        names = self.read(basis).get("scaffold_interface_names")
        if names:
            check = checks["connections_terminals"]
            check["observation"].append({"evidence_ref": basis, "value_path": "scaffold_interface_names", "value": names})
            check["evidence_refs"].append(basis)
        return checks

    def bind_cycle(self, *, stream="RETURN", snapshot_run="scaffold-1", mutate_export=None, mutate_state=None):
        scaffold = self.contract["scaffold_gate"]
        record = self.scaffold_record
        export = self.read(record["export_ref"])
        export["recycle_stream_ids"] = [stream]
        if mutate_export is not None:
            mutate_export(export)
        record["export_ref"] = self.put("scaffold-1-export.json", export)
        prefix = f"\\Data\\Streams\\{stream}\\Output\\"
        fields = [("TEMP_OUT\\MIXED", 30, "C"), ("PRES_OUT\\MIXED", 2.5, "bar"),
                  ("VFRAC_OUT\\MIXED", 0.25, ""), ("MOLEFLMX\\MIXED", 84, "kmol/hr"),
                  ("MOLEFLOW\\MIXED\\A", 63, "kmol/hr"), ("MOLEFLOW\\MIXED\\B", 21, "kmol/hr")]
        probes = [{"path": prefix + field, "Value": value, "UnitString": unit} for field, value, unit in fields]
        native = self.read(record["native_run_ref"])
        native["result_snapshot_ref"] = self.put("scaffold-probes.json", {"run_id": snapshot_run,
            "case_sha256": record["model_ref"]["sha256"], "probes": {prefix: probes}})
        record["native_run_ref"] = self.put("scaffold-1-native.json", native)
        state = {**self.stream(stream), "source_ref": native["result_snapshot_ref"],
                 "flow": {"value": 84, "unit_or_basis": "kmol/h"},
                 "temperature": {"value": 30, "unit_or_basis": "C"},
                 "pressure": {"value": 250, "unit_or_basis": "kPa(a)"},
                 "phase": "two_phase", "composition": {"A": 0.75, "B": 0.25}}
        if mutate_state is not None:
            mutate_state(state)
        cycle = self.read(scaffold["cycle_initials_ref"])
        cycle.update(mode="recycle", basis="Synthetic actual run output", streams=[state],
                     source_refs=[native["result_snapshot_ref"]], export_sha256=record["export_ref"]["sha256"])
        scaffold["run_ref"] = self.put("scaffold-1-record.json", record)
        scaffold["cycle_initials_ref"] = self.put("cycle.json", cycle)
        scaffold.update(self.reviews("scaffold", 3, {"run_id": record["run_id"],
            "export_sha256": record["export_ref"]["sha256"], "cycle_initials_sha256": scaffold["cycle_initials_ref"]["sha256"]}))


class ScaffoldEvidenceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = temporary.name

    def test_native_recycle_state_and_frozen_endpoints_agree(self):
        fixture = RecycleScaffoldFixture(self.root)
        fixture.bind_cycle(mutate_state=lambda state: state.update(temperature={"value": 303.15, "unit_or_basis": "K"}))
        result = fixture.check("scaffold")
        self.assertEqual(result["status"], "EVIDENCE_STRUCTURE_CONSISTENT", result["needs"])
        self.assertFalse(result["engineering_accepted"])

    def test_nonexistent_recycle_and_once_through_edge_cannot_be_tear_streams(self):
        for stream in ("GHOST", "T0"):
            with self.subTest(stream=stream):
                fixture = RecycleScaffoldFixture(self.root)
                fixture.bind_cycle(stream=stream)
                self.assertIn("CYCLE_CONNECTION_NOT_VERIFIED", {row["code"] for row in fixture.check("scaffold")["needs"]})

    def test_repeat_review_does_not_make_old_run_or_wrong_state_correct(self):
        fixture = RecycleScaffoldFixture(self.root)
        fixture.bind_cycle(snapshot_run="old-run")
        self.assertIn("NATIVE_DESIGN_RESULT_IDENTITY", {row["code"] for row in fixture.check("scaffold")["needs"]})

        for field, replacement in (
            ("flow", {"value": 85, "unit_or_basis": "kmol/h"}),
            ("temperature", {"value": 35, "unit_or_basis": "C"}),
            ("pressure", {"value": 251, "unit_or_basis": "kPa(a)"}),
            ("phase", "vapor"), ("composition", {"A": 1.0}),
        ):
            with self.subTest(field=field):
                fixture = RecycleScaffoldFixture(self.root)
                fixture.bind_cycle(mutate_state=lambda state: state.update({field: replacement}))
                expected_field = {"pressure": "pressure (Pa)", "composition": "composition.A"}.get(field, field)
                failures = fixture.check("scaffold")["needs"]
                self.assertTrue(any(row["code"] == "CYCLE_NATIVE_STATE_MISMATCH" and row["detail"]["field"] == expected_field
                                    for row in failures), failures)

    def test_frozen_tear_plan_blocks_a_no_recycle_claim(self):
        fixture = RecycleScaffoldFixture(self.root)
        source_gate = fixture.contract["source_gate"]
        handoff = fixture.read(source_gate["handoff_input_ref"])
        handoff["expert_plan"] = {"recycle_plan": [{"stream_id": "RETURN"}]}
        source_gate["handoff_input_ref"] = fixture.put("handoff-input.json", handoff)
        gate = _Gate({}, self.root, {})
        gate.identity = fixture.identity
        record = fixture.scaffold_record
        export = fixture.read(record["export_ref"])
        cycle = fixture.read(fixture.contract["scaffold_gate"]["cycle_initials_ref"])
        gate.scaffold_cycles(fixture.contract, record, export, {}, cycle, {})
        self.assertIn("CYCLE_FROZEN_PLAN_MISMATCH", {row["code"] for row in gate.needs})

    def test_source_stream_cannot_keep_its_tag_on_the_wrong_port(self):
        fixture = RecycleScaffoldFixture(self.root)

        def change_return(export):
            next(row for row in export["connections"] if row["stream_id"] == "RETURN")["to"] = "H1"

        fixture.bind_cycle(mutate_export=change_return)
        self.assertIn("SCAFFOLD_CONNECTION_MISMATCH", {row["code"] for row in fixture.check("scaffold")["needs"]})

    def test_dropped_product_is_blocked_and_abstracted_internal_edge_is_allowed(self):
        for stream, expected in (("T4", "SCAFFOLD_NET_INTERFACE_MISSING"), ("T1", None)):
            with self.subTest(stream=stream):
                fixture = RecycleScaffoldFixture(self.root)
                fixture.bind_cycle(mutate_export=lambda export: export.update(
                    connections=[row for row in export["connections"] if row["stream_id"] != stream]))
                result = fixture.check("scaffold")
                if expected:
                    self.assertIn(expected, {row["code"] for row in result["needs"]})
                else:
                    self.assertEqual(result["needs"], [])

    def test_readable_native_name_mapping_preserves_frozen_topology(self):
        fixture = RecycleScaffoldFixture(self.root)
        basis = "Same S1 product port; native naming differs"
        fixture.freeze_interface_names({"streams": {"T4": {"actual_id": "PROD-01", "basis": basis}},
                                        "terminals": {"PRODUCT": {"actual_id": "DELIVERY", "basis": basis}}})

        def rename_product(export):
            edge = next(row for row in export["connections"] if row["stream_id"] == "T4")
            edge.update(stream_id="PROD-01", to="DELIVERY")

        fixture.bind_cycle(mutate_export=rename_product)
        self.assertEqual(fixture.check("scaffold")["needs"], [])

    def test_exported_alias_cannot_justify_a_rename_or_swap_product_semantics(self):
        fixture = RecycleScaffoldFixture(self.root)

        def rename_without_frozen_authority(export):
            edge = next(row for row in export["connections"] if row["stream_id"] == "T4")
            edge.update(stream_id="PROD-01", to="DELIVERY")
            basis = {"basis": "Claimed product rename", "evidence_ref": export["raw_export_ref"]}
            export["stream_aliases"] = {"T4": {**basis, "actual_id": "PROD-01"}}
            export["terminal_aliases"] = {"PRODUCT": {**basis, "actual_id": "DELIVERY"}}

        fixture.bind_cycle(mutate_export=rename_without_frozen_authority)
        result = fixture.check("scaffold")
        self.assertIn("SCAFFOLD_NET_INTERFACE_MISSING", {row["code"] for row in result["needs"]})

        source = {"nodes": [{"id": n, "kind": k} for n, k in [("COL", "process"), ("TOP", "external"), ("BOTTOM", "external")]],
                  "streams": [{"id": "D", "from": "COL", "to": "TOP"}, {"id": "B", "from": "COL", "to": "BOTTOM"}]}
        basis = "Frozen reviewed correspondence"
        gate = _Gate({}, self.root, {})
        gate.scaffold_interface_names = {"streams": {"D": {"actual_id": "X1", "basis": basis}, "B": {"actual_id": "X2", "basis": basis}},
                                         "terminals": {"TOP": {"actual_id": "XDS", "basis": basis}, "BOTTOM": {"actual_id": "XBS", "basis": basis}}}
        export = {"connections": [{"stream_id": "X1", "from": "COL", "to": "XBS"}, {"stream_id": "X2", "from": "COL", "to": "XDS"}],
                  "stream_aliases": {"D": {"actual_id": "X2", "basis": "Self-reported override"}, "B": {"actual_id": "X1", "basis": "Self-reported override"}}}
        gate.scaffold_connections(source, export, {})
        self.assertIn("SCAFFOLD_CONNECTION_MISMATCH", {row["code"] for row in gate.needs})

    def test_first_model_choice_comes_from_frozen_buildable_plan(self):
        gate = _Gate({}, self.root, {})
        gate.require_buildable_plan = True
        for role, block in (("reaction", "RPlug"), ("separation", "SEP2")):
            with self.subTest(role=role):
                module = {"role": role, "node_ids": ["M1"], "first_model": {"block_type": block}}
                gate.scaffold_block_types("M1", module, {"block_type": block})
                self.assertEqual(gate.needs, [])
                gate.scaffold_block_types("M1", module, {"block_type": "Flash2"})
                self.assertEqual(gate.needs.pop()["code"], "SCAFFOLD_MODEL_TYPE")

    def test_scaffold_findings_need_an_evidenced_disposition_for_each_issue(self):
        fixture = prepare_scaffold(self.root)
        stage = fixture.contract["scaffold_gate"]
        issue_id = "SCAFFOLD-001"

        def report_finding(answer):
            answer["module_reviews"][0]["issues"].append({
                "id": issue_id, "finding": "The reactor's inlet pressure may disagree with the frozen design."})

        fixture.change_call("scaffold", 0, revise_output=report_finding)
        current_export = fixture.scaffold_record["export_ref"]
        previous_export = fixture.put("prior-export.json", {**fixture.read(current_export), "run_id": "older-scaffold"})
        for disposition, issues, evidence, expected in (
            ("no_difference", [issue_id], [current_export], {"DIFFERENCE_UNRESOLVED"}),
            ("adopt", [issue_id], [current_export], {"SCAFFOLD_REVIEW_RERUN_REQUIRED"}),
            ("reject", [issue_id], [previous_export], {"SCAFFOLD_REVIEW_EXPORT_EVIDENCE_REQUIRED"}),
            ("reject", [issue_id], [fixture.source], {"SCAFFOLD_REVIEW_EXPORT_EVIDENCE_REQUIRED"}),
            ("reject", [], [current_export], {"DIFFERENCE_COVERAGE"}),
            ("reject", [issue_id, issue_id], [current_export], {"DIFFERENCE_COVERAGE"}),
            ("reject", [issue_id], [current_export, fixture.source], set()),
        ):
            with self.subTest(disposition=disposition, issues=issues, evidence=evidence):
                def record_disposition(closure):
                    closure["comparisons"][0].update(
                        disposition=disposition, issue_ids=issues,
                        rationale="Compared the reactor inlet to the exact scaffold export and frozen design.",
                        evidence_refs=evidence)

                stage["difference_closure_ref"] = fixture.rewrite(stage["difference_closure_ref"], record_disposition)
                result = fixture.check("scaffold")
                self.assertEqual({row["code"] for row in result["needs"]}, expected, result["needs"])
                epochs = result["gate_summary"].get("buildable_review_epochs", {})
                self.assertEqual("scaffold_closed_epoch" in epochs, not expected)

    def test_grouped_scaffold_checks_each_native_block_type(self):
        gate = _Gate({}, self.root, {})
        gate.require_buildable_plan = True
        module = {"role": "separation", "node_ids": ["B1", "B2"],
                  "first_model": {"B1": {"block_type": "Flash2"}, "B2": {"block_type": "SEP2"}}}
        exported = {"node_ids": ["FLASH", "CUTS"], "block_types": {"FLASH": "Flash2", "CUTS": "SEP2"}}
        gate.scaffold_block_types("S1", module, exported)
        self.assertFalse(gate.needs)
        exported["block_types"]["CUTS"] = "SEP"
        gate.scaffold_block_types("S1", module, exported)
        self.assertEqual(gate.needs[-1]["code"], "SCAFFOLD_MODEL_TYPE")


if __name__ == "__main__":
    unittest.main()
