"""Synthetic graph/contract tests, not chemistry or Aspen execution evidence."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "check_flow_handoff.py"
spec = importlib.util.spec_from_file_location("flow_handoff", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture():
    return {"schema": module.SCHEMA, "stage": "source",
        "authority_reference": "Synthetic graph fixture revision a; not engineering evidence",
        "nodes": [{"id": x, "kind": "process" if x in ("A", "B") else "external"}
                  for x in ("F", "A", "B", "P")],
        "streams": [{"id": identifier, "from": a, "to": b, "state": "documented",
                     "evidence": "Synthetic graph specification", "gap": None}
                    for identifier, a, b in (("feed", "F", "A"), ("link", "A", "B"),
                                              ("return", "B", "A"), ("product", "B", "P"))],
        "control_volumes": [{"id": "combined", "members": ["A", "B"], "inflows": ["feed"],
            "outflows": ["product"], "balance_basis": "Symbolic fixture, no numeric balance",
            "reaction_terms": "No chemistry asserted by this fixture"}],
        "placeholders": [{"id": "duty-b", "node_ids": ["B"], "purpose": "Synthetic duty",
            "valid_scope": "Structural test only", "permission_reference": "Synthetic test permission"}],
        "no_placeholders_reason": None,
        "handoffs": [{"id": "duty-b", "owner": "Synthetic reviewer (not a real engineering owner)",
            "selection_condition": None,
            "inputs": [{"name": "fixture input", "reference": "Synthetic source value", "gap": None}],
            "required_returns": {"method_basis": "Synthetic method applicability record",
                "boundary_states": "State references for link, return and product",
                "closure_targets": "Current fixture target and boundary checks",
                "execution_evidence": "Performed status and actual output identity, if any"},
            "execution_status": "not_executed", "execution_reference": None}]}


class FlowHandoffTests(unittest.TestCase):
    def test_combined_internal_streams_excluded(self):
        result = module.check(fixture())
        self.assertEqual(result["status"], "STRUCTURE_VALID")
        self.assertEqual(result["volume_terms"][0]["internal"], ["link", "return"])
        self.assertFalse(result["engineering_accepted"])
        self.assertFalse(result["execution_verified"])

    def test_internal_effluent_cannot_be_combined_outflow(self):
        data = fixture(); data["control_volumes"][0]["outflows"].append("link")
        result = module.check(data)
        self.assertEqual(result["status"], "STRUCTURE_INVALID")
        self.assertIn("endpoint-derived ['product']", " ".join(result["errors"]))

    def test_internal_return_cannot_be_combined_inflow(self):
        data = fixture(); data["control_volumes"][0]["inflows"].append("return")
        self.assertEqual(module.check(data)["status"], "STRUCTURE_INVALID")

    def test_legal_smaller_control_volume_counts_actual_crossings(self):
        data = fixture()
        data["control_volumes"].append({"id": "local-a", "members": ["A"],
            "inflows": ["feed", "return"], "outflows": ["link"],
            "balance_basis": "Symbolic local boundary", "reaction_terms": "Not evaluated"})
        result = module.check(data)
        self.assertEqual(result["status"], "STRUCTURE_VALID")
        self.assertEqual(result["volume_terms"][1]["in"], ["feed", "return"])

    def test_unregistered_endpoint_not_default_external(self):
        data = fixture(); data["streams"][0]["from"] = "unregistered"
        self.assertIn("unregistered", " ".join(module.check(data)["errors"]))

    def test_unknown_endpoint_remains_unresolved(self):
        data = fixture()
        data["streams"][0].update({"from": None, "state": "unresolved", "evidence": None,
                                  "gap": "Source does not establish the feed origin"})
        data["control_volumes"][0]["inflows"] = []
        result = module.check(data)
        self.assertEqual(result["status"], "STRUCTURE_VALID_WITH_UNRESOLVED")
        self.assertEqual(result["boundary_rows"][0]["from_kind"], "unknown")
        self.assertEqual(result["declared_topology"]["coverage"], "DECLARED_PARTIAL")
        self.assertEqual(len(result["declared_topology"]["edges"]), 3)

    def test_unknown_endpoint_cannot_enter_balance_as_known(self):
        data = fixture()
        data["streams"][0].update({"from": None, "state": "unresolved", "gap": "Unknown origin"})
        self.assertEqual(module.check(data)["status"], "STRUCTURE_INVALID")

    def test_external_node_cannot_be_a_process_member(self):
        data = fixture(); data["control_volumes"][0]["members"].append("F")
        self.assertEqual(module.check(data)["status"], "STRUCTURE_INVALID")

    def test_missing_handoff_detected_against_placeholder_inventory(self):
        data = fixture(); data["handoffs"] = []
        self.assertIn("missing ['duty-b']", " ".join(module.check(data)["errors"]))

    def test_no_placeholders_requires_current_reason(self):
        data = fixture(); data["handoffs"] = []; data["placeholders"] = []
        self.assertEqual(module.check(data)["status"], "STRUCTURE_INVALID")
        data["no_placeholders_reason"] = "Synthetic request contains only established explicit units"
        self.assertEqual(module.check(data)["status"], "STRUCTURE_VALID")

    def test_unknown_owner_needs_present_selection_condition(self):
        data = fixture(); data["handoffs"][0]["owner"] = None
        self.assertEqual(module.check(data)["status"], "STRUCTURE_INVALID")
        data["handoffs"][0]["selection_condition"] = "Resolve physical mechanism to choose the relevant registered owner"
        self.assertEqual(module.check(data)["status"], "STRUCTURE_VALID_WITH_UNRESOLVED")

    def test_missing_input_keeps_current_handoff(self):
        data = fixture(); data["handoffs"][0]["inputs"][0].update({"reference": None, "gap": "Missing source boundary state"})
        result = module.check(data)
        self.assertEqual(result["status"], "STRUCTURE_VALID_WITH_UNRESOLVED")
        self.assertEqual(len(result["handoff_rows"]), 1)

    def test_missing_return_contract_is_not_plan_completion(self):
        data = fixture(); del data["handoffs"][0]["required_returns"]["boundary_states"]
        self.assertEqual(module.check(data)["status"], "STRUCTURE_INVALID")

    def test_execution_label_cannot_be_upgraded(self):
        data = fixture(); data["handoffs"][0]["execution_status"] = "accepted"
        self.assertEqual(module.check(data)["status"], "STRUCTURE_INVALID")

    def test_contradictory_execution_reference_rejected(self):
        data = fixture(); data["handoffs"][0]["execution_reference"] = "old report"
        self.assertEqual(module.check(data)["status"], "STRUCTURE_INVALID")

    def test_proposal_is_not_observed_connectivity(self):
        data = fixture(); data["streams"][1]["state"] = "proposed"
        self.assertEqual(module.check(data)["status"], "STRUCTURE_VALID_WITH_UNRESOLVED")

    def test_duplicate_stream_and_balance_ids_rejected(self):
        for kind in ("stream", "balance"):
            with self.subTest(kind=kind):
                data = fixture()
                if kind == "stream": data["streams"].append(copy.deepcopy(data["streams"][0]))
                else: data["control_volumes"][0]["inflows"].append("feed")
                self.assertEqual(module.check(data)["status"], "STRUCTURE_INVALID")

    def test_malformed_nested_json_fails_closed(self):
        for value in (None, [], 3, True, {"schema": []}):
            with self.subTest(top=value):
                self.assertEqual(module.check(value)["status"], "STRUCTURE_INVALID")
        for field, value in (("nodes", [False]), ("streams", {}), ("control_volumes", [None]),
                             ("handoffs", [{"id": []}]), ("placeholders", "text")):
            with self.subTest(field=field):
                data = fixture(); data[field] = value
                self.assertEqual(module.check(data)["status"], "STRUCTURE_INVALID")

    def test_cli_writes_input_bound_results_and_never_opens_cited_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / "input.json"; output = root / "review"
            data = fixture(); data["authority_reference"] = "../../nonexistent-source $(not-a-command)"
            source.write_text(json.dumps(data), encoding="utf-8")
            args = [sys.executable, "-B", "-X", "utf8", str(SCRIPT), "--input", str(source), "--output-dir", str(output)]
            run = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            report = json.loads((output / "review.json").read_text(encoding="utf-8"))
            self.assertEqual(report["input_sha256"], module.hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertFalse(report["authority_verified"])
            self.assertIn("duty-b", (output / "handoff.md").read_text(encoding="utf-8"))
            before = (output / "review.json").read_bytes()
            repeated = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(repeated.returncode, 2)
            self.assertEqual(before, (output / "review.json").read_bytes())

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(ValueError):
            json.loads('{"stage":"source","stage":"scaffold"}', object_pairs_hook=module.unique_object)


if __name__ == "__main__":
    unittest.main()
