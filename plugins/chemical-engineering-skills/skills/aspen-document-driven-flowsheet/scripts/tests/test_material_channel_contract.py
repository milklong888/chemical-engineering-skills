"""Synthetic material-channel contracts against the unchanged installed checker.

No campaign inputs, answers, source reviews, Aspen calls, or file writes are used.
The installed blank handoff asset supplies the existing record shape. This is
an in-memory structural regression, not source truth, numerical mass/energy
closure, method applicability, or engineering acceptance. Run with Python -B.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest


sys.dont_write_bytecode = True
LOCAL_SKILL_ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = (
    LOCAL_SKILL_ROOT
    if (LOCAL_SKILL_ROOT / "scripts" / "check_flow_handoff.py").is_file()
    else Path.home() / ".codex" / "skills" / "aspen-document-driven-flowsheet"
)
CHECKER_PATH = SKILL_ROOT / "scripts" / "check_flow_handoff.py"
TEMPLATE_PATH = SKILL_ROOT / "assets" / "source_scaffold_handoff.json"
CHECKER_SHA256 = hashlib.sha256(CHECKER_PATH.read_bytes()).hexdigest()
SPEC = importlib.util.spec_from_file_location("synthetic_original_handoff", CHECKER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Cannot load the installed handoff checker")
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)
BLANK = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8-sig"))

ENERGY_NOTE = (
    "SYN_Q couples the two independent material services without mixing. "
    "SYN_W is a pure shaft/electrical work dependency, not a material edge. "
    "No duty, work, or energy balance has been calculated or verified."
)


def stream(identifier: str, origin: str, destination: str) -> dict:
    return {
        "id": identifier,
        "from": origin,
        "to": destination,
        "state": "documented",
        "evidence": "Synthetic graph definition only; no project source claim.",
        "gap": None,
    }


def plan(process_ids: list[str], edges: list[dict], energy_note: str = "") -> dict:
    """Fill the original schema without extending or replacing the checker."""
    record = copy.deepcopy(BLANK)
    external_ids = sorted(
        {row[side] for row in edges for side in ("from", "to")} - set(process_ids)
    )
    record.update(
        authority_reference="SYN_CONTRACT: abstract in-memory software fixture only",
        nodes=[{"id": identifier, "kind": "process"} for identifier in process_ids]
        + [{"id": identifier, "kind": "external"} for identifier in external_ids],
        streams=copy.deepcopy(edges),
        control_volumes=[
            {
                "id": "SYN_CV",
                "members": list(process_ids),
                "inflows": [row["id"] for row in edges if row["from"] in external_ids],
                "outflows": [row["id"] for row in edges if row["to"] in external_ids],
                "balance_basis": (
                    "Synthetic steady material channels; utility steam and condensate "
                    "are material streams. No quantitative balance is supplied."
                ),
                "reaction_terms": "No reactions in this abstract connectivity fixture.",
            }
        ],
        placeholders=[
            {
                "id": "SYN_PH",
                "node_ids": list(process_ids),
                "purpose": "Represent declared material interfaces without a physical calculation.",
                "valid_scope": "Source-stage synthetic structure only; no engineering pass.",
                "permission_reference": "SYN_CONTRACT permits only in-memory checker regression.",
            }
        ],
        no_placeholders_reason=None,
        handoffs=[
            {
                "id": "SYN_PH",
                "owner": "aspen-document-driven-flowsheet",
                "selection_condition": None,
                "inputs": [
                    {"name": "synthetic channel graph", "reference": "SYN_CONTRACT", "gap": None}
                ],
                "required_returns": {
                    "method_basis": "Preserve each declared material channel separately. " + energy_note,
                    "boundary_states": "Return each declared material stream without merging services.",
                    "closure_targets": (
                        "Check source semantics and numerical material/energy closure separately; "
                        "neither is established by this fixture. " + energy_note
                    ),
                    "execution_evidence": "Not executed; only the structural checker is exercised.",
                },
                "execution_status": "not_executed",
                "execution_reference": None,
            }
        ],
    )
    record["expert_plan"] = {
        "methods": [
            {
                "node_ids": list(process_ids),
                "method": "Synthetic channel-preserving identity relation. " + energy_note,
                "phases": ["synthetic material state; no phase calculation"],
                "applicability": "Abstract graph regression only, not a property-method recommendation.",
                "source": "SYN_CONTRACT",
                "status": "candidate",
                "unresolved_inputs": ["Physical state and numerical balances are intentionally unspecified."],
            }
        ],
        "pressure_paths": [
            {
                "id": "SYN_PRESSURE",
                "node_ids": list(process_ids),
                "stream_ids": [row["id"] for row in edges],
                "state": "symbolic",
                "method": "Keep pressure interfaces per declared material channel.",
                "equation_or_reason": "Each channel requires its own inlet and outlet state; no value is assigned.",
                "source": "SYN_CONTRACT",
                "inputs": [{"name": "interface states", "unit": "Pa", "gap": "No physical states are supplied."}],
                "refine_trigger": "Obtain source-backed physical states before a numerical claim.",
            }
        ],
        "recycle_plan": [],
        "no_recycle_reason": "SYN_CONTRACT declares only once-through material channels.",
    }
    return record


def multipass_record(collapsed: bool = False) -> dict:
    # One physical non-mixing device is encountered through two distinct
    # services. The material path is E0 -> service 0 -> N1 -> service 1 -> E1.
    first, second = ("SYN_N0", "SYN_N0") if collapsed else ("SYN_N0_SIDE0", "SYN_N0_SIDE1")
    nodes = list(dict.fromkeys([first, "SYN_N1", second]))
    return plan(
        nodes,
        [
            stream("SYN_S0", "SYN_E0", first),
            stream("SYN_S1", first, "SYN_N1"),
            stream("SYN_S2", "SYN_N1", second),
            stream("SYN_S3", second, "SYN_E1"),
        ],
        ENERGY_NOTE,
    )


def recycle_record() -> dict:
    return plan(
        ["SYN_N0", "SYN_N1"],
        [
            stream("SYN_S0", "SYN_E0", "SYN_N0"),
            stream("SYN_S1", "SYN_N0", "SYN_N1"),
            stream("SYN_S2", "SYN_N1", "SYN_E1"),
            stream("SYN_RETURN", "SYN_N1", "SYN_N0"),
        ],
    )


def utility_record() -> dict:
    # SYN_S2 is incoming steam and SYN_S3 is outgoing condensate.
    # Both carry material, unlike the separate SYN_Q/SYN_W dependency text.
    return plan(
        ["SYN_N0_SIDE0", "SYN_N0_SIDE1"],
        [
            stream("SYN_S0", "SYN_E0", "SYN_N0_SIDE0"),
            stream("SYN_S1", "SYN_N0_SIDE0", "SYN_E1"),
            stream("SYN_S2", "SYN_E2", "SYN_N0_SIDE1"),
            stream("SYN_S3", "SYN_N0_SIDE1", "SYN_E3"),
        ],
        ENERGY_NOTE,
    )


class MaterialChannelContractTests(unittest.TestCase):
    def check(self, record: dict) -> dict:
        return CHECKER.check(record, require_expert_plan=True)

    def assert_valid_unverified(self, result: dict) -> None:
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["status"], "STRUCTURE_VALID_WITH_UNRESOLVED")
        self.assertTrue(result["expert_plan_checked"])
        for flag in (
            "engineering_accepted", "execution_verified", "authority_verified",
            "source_inventory_verified", "source_review_checked", "reaction_derivations_checked",
        ):
            self.assertFalse(result[flag], flag)
        self.assertFalse(result["declared_topology"]["source_verified"])

    def test_separate_nonmixing_services_have_no_false_material_cycle(self):
        result = self.check(multipass_record())
        self.assert_valid_unverified(result)
        coverage = result["expert_plan_rows"]["cycle_coverage"]
        self.assertEqual(coverage["tear_stream_ids"], [])
        self.assertEqual(
            coverage["topological_order_after_tears"],
            ["SYN_N0_SIDE0", "SYN_N1", "SYN_N0_SIDE1"],
        )
        self.assertEqual(result["volume_terms"][0]["internal"], ["SYN_S1", "SYN_S2"])

    def test_collapsing_independent_services_creates_rejected_false_cycle(self):
        result = self.check(multipass_record(collapsed=True))
        self.assertEqual(result["status"], "STRUCTURE_INVALID")
        self.assertEqual(len(result["errors"]), 1, result["errors"])
        self.assertIn("still contains a cycle", result["errors"][0])
        self.assertFalse(result["expert_plan_checked"])

    def test_real_material_recycle_without_tear_is_rejected(self):
        result = self.check(recycle_record())
        self.assertEqual(result["status"], "STRUCTURE_INVALID")
        self.assertEqual(len(result["errors"]), 1, result["errors"])
        self.assertIn("still contains a cycle", result["errors"][0])

    def test_real_material_recycle_tear_is_plan_only_and_preserves_stream(self):
        record = recycle_record()
        record["expert_plan"]["no_recycle_reason"] = None
        record["expert_plan"]["recycle_plan"] = [
            {
                "stream_id": "SYN_RETURN", "from": "SYN_N1", "to": "SYN_N0",
                "initialization_basis": "Future forward-pass outlet only; no computed seed exists.",
                "closure_order": 1,
                "controlled_quantity": "Material inventory remains to be established.",
                "purge_or_terminal_basis": "SYN_S2 is the declared terminal; no extra purge is invented.",
            }
        ]
        result = self.check(record)
        self.assert_valid_unverified(result)
        coverage = result["expert_plan_rows"]["cycle_coverage"]
        self.assertEqual(coverage["tear_stream_ids"], ["SYN_RETURN"])
        self.assertEqual(coverage["topological_order_after_tears"], ["SYN_N0", "SYN_N1"])
        self.assertFalse(coverage["source_cycles_verified"])
        self.assertIn("SYN_RETURN", result["volume_terms"][0]["internal"])
        self.assertIn(["SYN_N1", "SYN_N0"], result["declared_topology"]["edges"])

    def test_steam_and_condensate_remain_material_boundary_terms(self):
        result = self.check(utility_record())
        self.assert_valid_unverified(result)
        terms = result["volume_terms"][0]
        self.assertEqual(set(terms["in"]), {"SYN_S0", "SYN_S2"})
        self.assertEqual(set(terms["out"]), {"SYN_S1", "SYN_S3"})
        self.assertEqual(terms["internal"], [])

    def test_omitting_declared_steam_from_volume_is_rejected(self):
        record = utility_record()
        record["control_volumes"][0]["inflows"].remove("SYN_S2")
        result = self.check(record)
        self.assertEqual(result["status"], "STRUCTURE_INVALID")
        self.assertEqual(len(result["errors"]), 1, result["errors"])
        self.assertIn("volume SYN_CV in:", result["errors"][0])
        self.assertIn("SYN_S2", result["volume_terms"][0]["in"])

    def test_omitting_declared_condensate_from_volume_is_rejected(self):
        record = utility_record()
        record["control_volumes"][0]["outflows"].remove("SYN_S3")
        result = self.check(record)
        self.assertEqual(result["status"], "STRUCTURE_INVALID")
        self.assertEqual(len(result["errors"]), 1, result["errors"])
        self.assertIn("volume SYN_CV out:", result["errors"][0])
        self.assertIn("SYN_S3", result["volume_terms"][0]["out"])

    def test_pure_heat_work_text_is_retained_without_material_edges_or_acceptance(self):
        record = utility_record()
        result = self.check(record)
        self.assert_valid_unverified(result)
        self.assertEqual({row["id"] for row in record["streams"]}, {"SYN_S0", "SYN_S1", "SYN_S2", "SYN_S3"})
        self.assertEqual(len(result["declared_topology"]["edges"]), 4)
        self.assertIn(ENERGY_NOTE, result["expert_plan_rows"]["methods"][0]["method"])
        self.assertIn(ENERGY_NOTE, result["handoff_rows"][0]["required_returns"]["closure_targets"])
        self.assertEqual(result["handoff_rows"][0]["execution_status"], "not_executed")
        self.assertTrue(all(not row["calculation_verified"] for row in result["expert_plan_rows"]["pressure_paths"]))
        self.assertNotIn("energy_balance_verified", result)

    def test_installed_checker_bytes_are_unchanged(self):
        self.assertEqual(hashlib.sha256(CHECKER_PATH.read_bytes()).hexdigest(), CHECKER_SHA256)


if __name__ == "__main__":
    print(f"Installed checker: {CHECKER_PATH}")
    print(f"Checker SHA-256: {CHECKER_SHA256}")
    print("Scope: synthetic declared material topology only; energy/source/engineering unverified.")
    unittest.main(verbosity=2)
