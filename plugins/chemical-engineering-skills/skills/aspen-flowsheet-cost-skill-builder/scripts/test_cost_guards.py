"""Run synthetic software regressions; fixture prices are not engineering data."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BUILDER = Path(__file__).resolve().parents[1]
ASSETS = BUILDER / "assets" / "project-skill-template"
sys.path.insert(0, str(ASSETS))
from cost_evidence_guard import REQUIRED_FIELDS, audit_procurement


def write_csv(path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def run(script, args, receipt):
    result = subprocess.run([sys.executable, "-B", "-X", "utf8", str(script), *map(str, args)],
                            capture_output=True, text=True, encoding="utf-8", check=False)
    receipt.write_text(json.dumps({"synthetic": True, "command": [str(script), *map(str, args)],
                                  "returncode": result.returncode, "stdout": result.stdout,
                                  "stderr": result.stderr}, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


class CostGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = WORK / "inventory"
        cls.data = WORK / "data"
        cls.inventory.mkdir()
        cls.data.mkdir()
        (WORK / "SYNTHETIC.txt").write_text("Synthetic software fixtures only. No Aspen execution, actual quote, or engineering acceptance.\n", encoding="utf-8")
        original = cls.inventory / "synthetic-original.txt"
        original.write_text("SYNTHETIC anchor table: capacity 100 => 100 tokens; 200 => 200 tokens. Not a real cost source.\n", encoding="utf-8")
        source = {field: "synthetic" for field in REQUIRED_FIELDS}
        source.update(source_id="SYNTHETIC_SOURCE", review_status="approved", local_path=original.name,
                      sha256=hashlib.sha256(original.read_bytes()).hexdigest(), independent_reproduction_status="passed")
        write_csv(cls.inventory / "source_evidence_ledger.csv", [source])
        (cls.inventory / "skill_spec.json").write_text(json.dumps({"project_name": "Synthetic fixture", "template_id": "SYNTHETIC"}), encoding="utf-8")
        write_csv(cls.inventory / "mother_template_inventory.csv", [{"template_id": "SYNTHETIC", "bkp_path": "", "bkp_sha256": ""}])
        item = {"equipment_item_id": "HX001", "block_id": "HX", "aspen_block_type": "HEATX", "physical_equipment": "heat_exchanger"}
        write_csv(cls.inventory / "equipment_inventory.csv", [item])
        cls.assignment = dict(item, scope_class="purchased_equipment_candidate", method_id="HX_Q_U_LMTD_NETL", source_ids="SYNTHETIC_SOURCE", mapping_status="reviewed")
        write_csv(cls.inventory / "equipment_method_assignment.csv", [cls.assignment])
        write_csv(cls.inventory / "missing_parameter_register.csv", [], ["equipment_item_id", "parameter", "status"])
        write_csv(cls.inventory / "source_request_register.csv", [], ["gap_id", "status"])
        write_csv(cls.inventory / "source_search_log.csv", [], ["query", "source_id", "result"])
        write_csv(cls.data / "method-library.csv", [{"method_id": "HX_Q_U_LMTD_NETL"}])
        points = [{"equipment_type": "Shell and Tube Heat Exchanger", "subtype": "", "variant": "",
                   "capacity_value": str(value), "purchased_equipment_cost_1998_usd": str(value),
                   "installed_cost_1998_usd": "", "independent_values_json": json.dumps({"area": value}),
                   "source_id": "SYNTHETIC_SOURCE", "row_index": str(index)} for index, value in enumerate((100, 200))]
        write_csv(cls.data / "netl-equipment-cost-points.csv", points)
        reference = {"reference_cost_usd_at_index": "100", "reference_cost_index": "100", "scaling_exponent": "1",
                     "source_id": "SYNTHETIC_SOURCE", "source_locator": "synthetic-original.txt"}
        write_csv(cls.data / "replacement-cost-library.csv", [dict(method_id=method, **reference) for method in ("HX_Q_U_LMTD_NETL", "*")])
        write_csv(cls.data / "comparison-service-replacement-library.csv", [], ["service", "method_id", *reference])
        rules = ["IF_STRUCTURAL_ZERO", "IF_PUMP_IS_LETDOWN", "IF_REVIEWED_NUMERIC", "IF_NUMERIC_CANDIDATE", "IF_METHOD_PROXY_AVAILABLE", "IF_CYCLONE_PROXY_AVAILABLE", "IF_CYCLONE_NO_PROXY", "IF_METHOD_NO_PROXY", "IF_UNKNOWN_PHYSICAL"]
        write_csv(cls.data / "comparison-cost-fallback-policy.csv", [{"rule_id": rule, "priority": str(i),
                   "low_factor": "0" if i < 2 else "0.5", "high_factor": "0" if i < 2 else "2"} for i, rule in enumerate(rules)])
        generated = WORK / "generated"
        result = run(BUILDER / "scripts" / "scaffold_cost_skill.py",
                     ["--inventory-dir", cls.inventory, "--data-dir", cls.data, "--skills-root", generated,
                      "--skill-name", "synthetic-cost-fixture", "--require-ready"], WORK / "scaffold-receipt.json")
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        cls.template = generated / "synthetic-cost-fixture"
        generation = read_json(cls.template / "generation_audit.json")
        if generation["status"] != "generated_ready":
            raise AssertionError("synthetic complete fixture must qualify structurally")
        if (generation["external_data_dir"] != str(cls.data.resolve())
                or generation["external_data_is_project_supplied"] is not True):
            raise AssertionError("explicit project data directory identity must be retained")

    def setUp(self):
        self.case = WORK / self._testMethodName
        self.case.mkdir()
        self.skill = self.case / "skill"
        shutil.copytree(self.template, self.skill)
        self.refs = self.skill / "references"
        self.good = self.case / "good.csv"
        self.bad = self.case / "bad.csv"
        write_csv(self.good, [{"equipment_item_id": "HX001", "method_id": "HX_Q_U_LMTD_NETL", "parameters_json": '{"capacity_value":100}', "selected_after_review": "yes"}])
        write_csv(self.bad, [{"equipment_item_id": "HX001", "method_id": "HX_Q_U_LMTD_NETL", "parameters_json": "{}", "selected_after_review": "yes"}])

    def batch(self, order=("good",), strict=True):
        rows = [{"case_id": name, "equipment_input_csv": str(getattr(self, name)), "enabled": "yes",
                 "base_cost_index": "100", "target_cost_index": "100", "index_name": "SYNTHETIC",
                 "base_period": "synthetic", "target_period": "synthetic", "index_source": "synthetic-original.txt"} for name in order]
        manifest = self.case / "manifest.csv"
        write_csv(manifest, rows)
        out = self.case / "output"
        result = run(self.skill / "scripts" / "run_recipe_batch.py",
                     ["--manifest", manifest, "--out-dir", out, *(["--strict-engineering"] if strict else [])], self.case / "run-receipt.json")
        return result, read_json(out / "batch_audit.json")

    def assert_blocked_before_cost(self, strict=True):
        result, audit = self.batch(strict=strict)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(audit["status"], "blocked")
        self.assertIs(audit["costs_calculated"], False)
        self.assertFalse((self.case / "output" / "good" / "case_audit.json").exists())
        return audit

    def assert_coverage_blocks_comparison(self, issue_type):
        audit = self.assert_blocked_before_cost(strict=False)
        self.assertEqual(audit["audit"]["equipment_coverage_status"], "fail")
        self.assertIn(issue_type, {issue["type"] for issue in audit["audit"]["equipment_coverage_issues"]})

    def edit_source(self, **fields):
        path = self.refs / "source-evidence-ledger.csv"
        rows = read_csv(path)
        rows[0].update(fields)
        write_csv(path, rows)

    def test_complete_case_calculates(self):
        result, audit = self.batch()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(audit["strict_status"], "pass")
        self.assertEqual(read_json(self.case / "output" / "good" / "case_audit.json")["selected_purchased_equipment_total_usd"], 100)

    def check_mixed(self, order):
        result, audit = self.batch(order)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(audit["strict_status"], "blocked")
        self.assertEqual(audit["selected_case_count"], 1)
        self.assertEqual(audit["case_count"], 2)
        self.assertEqual(read_json(self.case / "output" / "good" / "case_audit.json")["strict_status"], "selected_total_available")
        bad = read_json(self.case / "output" / "bad" / "case_audit.json")
        self.assertEqual(bad["strict_status"], "blocked")
        self.assertEqual(bad["selected_purchased_equipment_total_usd"], "")

    def test_success_then_unresolved(self):
        self.check_mixed(("good", "bad"))

    def test_unresolved_then_success(self):
        self.check_mixed(("bad", "good"))

    def test_approved_without_original(self):
        self.edit_source(local_path="")
        self.assert_blocked_before_cost()

    def test_wrong_source_hash(self):
        self.edit_source(sha256="0" * 64)
        self.assert_blocked_before_cost()

    def test_approved_with_pending_reproduction(self):
        self.edit_source(independent_reproduction_status="pending")
        self.assert_blocked_before_cost()

    def test_unknown_or_substring_exclusion_does_not_bypass(self):
        for scope in ("accidentally_excluded", "", "physical_scope_unresolved"):
            with self.subTest(scope=scope):
                write_csv(self.refs / "equipment-method-assignment.csv", [dict(self.assignment, scope_class=scope)])
                self.assert_blocked_before_cost()

    def test_legacy_nonphysical_exclusion_and_report_fields(self):
        assignments = self.case / "nonphysical.csv"
        write_csv(assignments, [dict(self.assignment, scope_class="not_physical_equipment", source_ids="", method_id="LOGICAL_OR_REACTOR_EXCLUSION")])
        out = self.case / "source-audit.json"
        result = run(BUILDER / "scripts" / "audit_source_evidence.py",
                     ["--assignments", assignments, "--ledger", self.refs / "source-evidence-ledger.csv", "--out", out], self.case / "source-receipt.json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(read_json(out)["source_count"], 1)
        self.assertEqual(read_json(out)["assignment_count"], 1)

    def test_require_ready_reads_original_ledger(self):
        inventory = self.case / "inventory"
        shutil.copytree(self.inventory, inventory)
        path = inventory / "source_evidence_ledger.csv"
        rows = read_csv(path)
        rows[0]["local_path"] = ""
        write_csv(path, rows)
        target = self.case / "must-not-be-ready"
        result = run(BUILDER / "scripts" / "scaffold_cost_skill.py",
                     ["--inventory-dir", inventory, "--data-dir", self.data, "--skill-name", "synthetic-invalid", "--skills-root", target, "--require-ready"], self.case / "invalid-scaffold-receipt.json")
        self.assertEqual(result.returncode, 1)
        self.assertFalse(target.exists())

    def test_changed_original_despite_approved(self):
        changed = self.case / "changed-original.txt"
        changed.write_text("Changed SYNTHETIC source bytes", encoding="utf-8")
        self.edit_source(local_path=str(changed))
        self.assert_blocked_before_cost()

    def test_duplicate_source_identity(self):
        path = self.refs / "source-evidence-ledger.csv"
        rows = read_csv(path)
        write_csv(path, rows + rows)
        self.assert_blocked_before_cost()

    def test_unregistered_comparison_source(self):
        path = self.refs / "replacement-cost-library.csv"
        rows = read_csv(path)
        rows[0]["source_id"] = "SYNTHETIC_UNREGISTERED"
        write_csv(path, rows)
        self.assert_blocked_before_cost()

    def test_stale_green_after_audit_crash(self):
        # The copied fixture already has an earlier successful method_audit.json.
        self.assertEqual(read_json(self.skill / "method_audit.json")["status"], "pass")
        (self.skill / "scripts" / "audit_generated_method.py").write_text('raise RuntimeError("synthetic audit crash")\n', encoding="utf-8")
        self.assert_blocked_before_cost()
        result = run(BUILDER / "scripts" / "validate_generated_skill.py",
                     ["--skill-dir", self.skill, "--allow-draft"], self.case / "validate-receipt.json")
        self.assertEqual(result.returncode, 1)

    def test_draft_without_prices(self):
        root = self.case / "drafts"
        result = run(BUILDER / "scripts" / "scaffold_cost_skill.py",
                     ["--inventory-dir", self.inventory, "--draft-only", "--skill-name", "synthetic-draft", "--skills-root", root], self.case / "draft-receipt.json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.skill = root / "synthetic-draft"
        generation = read_json(self.skill / "generation_audit.json")
        self.assertEqual(generation["status"], "generated_draft")
        self.assertIsNone(generation["external_data_dir"])
        self.assertIs(generation["external_data_is_project_supplied"], False)
        self.assertEqual(read_csv(self.skill / "references" / "netl-equipment-cost-points.csv"), [])
        self.assertEqual(read_csv(self.skill / "references" / "batch-manifest-template.csv")[0]["enabled"], "no")
        self.assert_blocked_before_cost()

    def test_missing_data_without_draft_creates_nothing(self):
        root = self.case / "not-created"
        result = run(BUILDER / "scripts" / "scaffold_cost_skill.py",
                     ["--inventory-dir", self.inventory, "--skill-name", "synthetic-missing", "--skills-root", root], self.case / "missing-data-receipt.json")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(root.exists())

    def package_rows(self):
        evidence = {"package_scope_status": "reviewed", "package_scope_source_ids": "SYNTHETIC_SOURCE", "package_scope_locator": "synthetic inclusion schedule"}
        package = dict(self.assignment, procurement_role="package", covered_equipment_ids="HX001;AUX001", parent_package_id="", **evidence)
        auxiliary = dict(self.assignment, equipment_item_id="AUX001", method_id="LOGICAL_OR_REACTOR_EXCLUSION",
                         scope_class="included_in_package_excluded", procurement_role="included_in_package",
                         covered_equipment_ids="", parent_package_id="HX001", **evidence)
        return [package, auxiliary]

    def test_package_auxiliary_duplicate_charge_rejected(self):
        rows = self.package_rows()
        rows[1].update(procurement_role="standalone", scope_class="purchased_equipment_candidate", parent_package_id="")
        types = {issue["type"] for issue in audit_procurement(rows)}
        self.assertIn("package_item_separately_chargeable", types)
        write_csv(self.refs / "equipment-method-assignment.csv", rows)
        self.assert_blocked_before_cost()

    def test_unknown_tower_quote_boundary_rejected(self):
        row = dict(self.assignment, physical_equipment="tower_package", quote_id="SYNTHETIC_QUOTE")
        write_csv(self.refs / "equipment-method-assignment.csv", [row])
        self.assert_blocked_before_cost()

    def test_package_exclusion_requires_parent_record(self):
        row = dict(self.assignment, scope_class="included_in_package_excluded")
        write_csv(self.refs / "equipment-method-assignment.csv", [row])
        self.assert_blocked_before_cost()

    def test_overlapping_package_coverage_rejected(self):
        rows = self.package_rows()
        rows.append(dict(rows[0], equipment_item_id="PKG002", covered_equipment_ids="PKG002;AUX001"))
        self.assertIn("overlapping_package_coverage", {issue["type"] for issue in audit_procurement(rows)})

    def test_package_keeps_auxiliary_without_double_charge(self):
        rows = self.package_rows()
        self.assertEqual(audit_procurement(rows), [])
        write_csv(self.refs / "equipment-method-assignment.csv", rows)
        write_csv(self.refs / "equipment-inventory.csv", rows)
        write_csv(self.refs / "method-library.csv", [{"method_id": "HX_Q_U_LMTD_NETL"}, {"method_id": "LOGICAL_OR_REACTOR_EXCLUSION"}])
        result, audit = self.batch()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        case = read_json(self.case / "output" / "good" / "case_audit.json")
        self.assertEqual(case["comparison_item_count"], 2)
        self.assertEqual(case["selected_purchased_equipment_total_usd"], 100)
        self.assertEqual(case["comparison_purchased_equipment_total_usd"], 100)

    def test_duplicate_plain_assignment_blocks_comparison(self):
        write_csv(self.refs / "equipment-method-assignment.csv", [self.assignment, self.assignment])
        self.assert_coverage_blocks_comparison("duplicate_equipment_assignment")

    def test_duplicate_package_assignment_blocks_comparison(self):
        package = dict(self.package_rows()[0], covered_equipment_ids="HX001")
        write_csv(self.refs / "equipment-method-assignment.csv", [package, package])
        self.assert_coverage_blocks_comparison("duplicate_equipment_assignment")

    def test_duplicate_inventory_blocks_comparison(self):
        rows = read_csv(self.refs / "equipment-inventory.csv")
        write_csv(self.refs / "equipment-inventory.csv", rows + rows)
        self.assert_coverage_blocks_comparison("duplicate_equipment_inventory")

    def test_inventory_item_without_assignment_blocks_comparison(self):
        rows = read_csv(self.refs / "equipment-inventory.csv")
        write_csv(self.refs / "equipment-inventory.csv", rows + [dict(rows[0], equipment_item_id="HX002")])
        self.assert_coverage_blocks_comparison("equipment_without_assignment")

    def test_assignment_without_inventory_item_blocks_comparison(self):
        write_csv(self.refs / "equipment-method-assignment.csv", [self.assignment, dict(self.assignment, equipment_item_id="HX002")])
        self.assert_coverage_blocks_comparison("assignment_without_equipment")

    def test_missing_inventory_file_blocks_comparison(self):
        (self.refs / "equipment-inventory.csv").unlink()
        self.assert_blocked_before_cost(strict=False)

    def test_empty_inventory_blocks_comparison(self):
        write_csv(self.refs / "equipment-inventory.csv", [], ["equipment_item_id"])
        self.assert_coverage_blocks_comparison("empty_equipment_inventory")

    def test_empty_assignment_blocks_comparison(self):
        write_csv(self.refs / "equipment-method-assignment.csv", [], list(self.assignment))
        self.assert_coverage_blocks_comparison("empty_equipment_assignment")

    def test_blank_equipment_id_blocks_comparison(self):
        write_csv(self.refs / "equipment-inventory.csv", [{"equipment_item_id": ""}])
        self.assert_coverage_blocks_comparison("invalid_equipment_inventory_id")

    def test_two_distinct_equipment_items_both_count(self):
        rows = [self.assignment, dict(self.assignment, equipment_item_id="HX002", block_id="HX2")]
        write_csv(self.refs / "equipment-method-assignment.csv", rows)
        write_csv(self.refs / "equipment-inventory.csv", rows)
        inputs = read_csv(self.good)
        write_csv(self.good, inputs + [dict(inputs[0], equipment_item_id="HX002")])
        result, audit = self.batch(strict=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        case = read_json(self.case / "output" / "good" / "case_audit.json")
        self.assertEqual(case["selected_purchased_equipment_total_usd"], 200)
        self.assertEqual(case["comparison_purchased_equipment_total_usd"], 200)

    def add_source_b(self, with_original=True):
        path = self.refs / "source-evidence-ledger.csv"
        rows = read_csv(path)
        original = self.case / "synthetic-original-b.txt"
        original.write_text("SYNTHETIC independent source B: capacity 200 => 200 tokens. Not engineering evidence.\n", encoding="utf-8")
        rows.append(dict(rows[0], source_id="SYNTHETIC_SOURCE_B", local_path=str(original) if with_original else "",
                         sha256=hashlib.sha256(original.read_bytes()).hexdigest()))
        write_csv(path, rows)

    def set_point_source_b(self):
        path = self.refs / "netl-equipment-cost-points.csv"
        rows = read_csv(path)
        rows[1]["source_id"] = "SYNTHETIC_SOURCE_B"
        write_csv(path, rows)

    def test_unregistered_actual_point_source_blocks_comparison(self):
        self.set_point_source_b()
        audit = self.assert_blocked_before_cost(strict=False)
        self.assertIn("source_not_registered", {issue["type"] for issue in audit["audit"]["issues"]})

    def test_point_source_without_original_blocks_comparison(self):
        self.add_source_b(with_original=False)
        self.set_point_source_b()
        self.assert_blocked_before_cost(strict=False)

    def test_point_source_missing_id_blocks_comparison(self):
        path = self.refs / "netl-equipment-cost-points.csv"
        rows = read_csv(path)
        rows[0]["source_id"] = ""
        write_csv(path, rows)
        audit = self.assert_blocked_before_cost(strict=False)
        self.assertIn("cost_point_source_missing", {issue["type"] for issue in audit["audit"]["issues"]})

    def test_registered_point_source_outside_assignment_blocks_comparison(self):
        self.add_source_b()
        self.set_point_source_b()
        audit = self.assert_blocked_before_cost(strict=False)
        self.assertEqual(audit["reason"], "cost_source_assignment_mismatch")

    def test_explicit_multi_source_group_remains_valid(self):
        self.add_source_b()
        self.set_point_source_b()
        write_csv(self.refs / "equipment-method-assignment.csv", [dict(self.assignment, source_ids="SYNTHETIC_SOURCE;SYNTHETIC_SOURCE_B")])
        inputs = read_csv(self.good)
        inputs[0]["parameters_json"] = '{"capacity_value":150}'
        write_csv(self.good, inputs)
        result, audit = self.batch(strict=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        rows = read_csv(self.case / "output" / "good" / "equipment_cost_candidates.csv")
        self.assertEqual(rows[0]["source_ids"], "SYNTHETIC_SOURCE;SYNTHETIC_SOURCE_B")
        self.assertEqual(rows[0]["assignment_source_ids"], "SYNTHETIC_SOURCE;SYNTHETIC_SOURCE_B")
        self.assertAlmostEqual(float(rows[0]["candidate_purchased_cost_target_usd"]), 150)

    def test_capex_method_cannot_hide_in_utility_scope(self):
        write_csv(self.refs / "equipment-method-assignment.csv", [dict(self.assignment, scope_class="utility_opex_separate")])
        inputs = read_csv(self.good)
        inputs[0]["selected_after_review"] = "no"
        write_csv(self.good, inputs)
        self.assert_blocked_before_cost(strict=False)

    def test_utility_method_cannot_hide_in_purchase_scope(self):
        write_csv(self.refs / "equipment-method-assignment.csv", [dict(self.assignment, method_id="UTILITY_OPEX")])
        write_csv(self.refs / "method-library.csv", [{"method_id": "HX_Q_U_LMTD_NETL"}, {"method_id": "UTILITY_OPEX"}])
        self.assert_blocked_before_cost(strict=False)

    def test_capex_method_cannot_hide_in_excluded_scope(self):
        write_csv(self.refs / "equipment-method-assignment.csv", [dict(self.assignment, scope_class="not_physical_equipment")])
        self.assert_blocked_before_cost(strict=False)

    def test_valid_utility_and_capex_remain_separate(self):
        utility = dict(self.assignment, equipment_item_id="U001", method_id="UTILITY_OPEX", scope_class="utility_opex_separate")
        rows = [self.assignment, utility]
        write_csv(self.refs / "equipment-method-assignment.csv", rows)
        write_csv(self.refs / "equipment-inventory.csv", rows)
        write_csv(self.refs / "method-library.csv", [{"method_id": "HX_Q_U_LMTD_NETL"}, {"method_id": "UTILITY_OPEX"}])
        inputs = read_csv(self.good)
        inputs.append(dict(inputs[0], equipment_item_id="U001", method_id="UTILITY_OPEX", selected_after_review="no",
                           parameters_json='{"utility_quantity":2,"configured_price":3,"operating_hours_per_year":4}'))
        write_csv(self.good, inputs)
        result, audit = self.batch(strict=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        case = read_json(self.case / "output" / "good" / "case_audit.json")
        self.assertEqual(case["selected_purchased_equipment_total_usd"], 100)
        self.assertEqual(case["comparison_purchased_equipment_total_usd"], 100)
        rows = read_csv(self.case / "output" / "good" / "equipment_cost_candidates.csv")
        self.assertEqual(float(rows[1]["utility_cost_usd_h"]), 6)
        self.assertEqual(float(rows[1]["utility_cost_usd_y"]), 24)

    def test_unselected_real_capex_never_enters_strict_total(self):
        inputs = read_csv(self.good)
        inputs[0]["selected_after_review"] = "no"
        write_csv(self.good, inputs)
        result, audit = self.batch(strict=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(audit["strict_status"], "blocked")
        case = read_json(self.case / "output" / "good" / "case_audit.json")
        self.assertEqual(case["selected_purchased_equipment_total_usd"], "")
        self.assertEqual(case["comparison_purchased_equipment_total_usd"], 100)

    def draft_rows(self):
        ordinary = dict(self.assignment, method_id="METHOD_GAP", source_ids="", mapping_status="unreviewed")
        reactor = dict(ordinary, equipment_item_id="R001", physical_equipment="reactor", aspen_block_type="REACTOR",
                       scope_class="reactor_excluded", method_id="LOGICAL_OR_REACTOR_EXCLUSION", mapping_status="rule_fixed")
        return [ordinary, reactor]

    def scaffold_draft(self, rows):
        inventory = self.case / "draft_inventory"
        shutil.copytree(self.inventory, inventory)
        write_csv(inventory / "equipment_method_assignment.csv", rows)
        write_csv(inventory / "equipment_inventory.csv", rows)
        write_csv(inventory / "source_evidence_ledger.csv", [], ["source_id", "review_status", "local_path", "sha256"])
        target = self.case / "draft_target"
        result = run(BUILDER / "scripts" / "scaffold_cost_skill.py",
                     ["--inventory-dir", inventory, "--draft-only", "--skill-name", "synthetic-draft-contract", "--skills-root", target],
                     self.case / "draft-contract-receipt.json")
        return result, target / "synthetic-draft-contract"

    def test_no_source_legal_gap_and_reactor_draft(self):
        result, generated = self.scaffold_draft(self.draft_rows())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.skill = generated
        self.assertEqual(read_json(generated / "generation_audit.json")["input_contract_status"], "pass")
        audit = self.assert_blocked_before_cost(strict=False)
        self.assertEqual(audit["input_contract_status"], "pass")
        self.assertEqual(audit["reason"], "draft_only:no_cost_calculation")
        result = run(BUILDER / "scripts" / "validate_generated_skill.py", ["--skill-dir", generated, "--allow-draft"], self.case / "validate-draft-receipt.json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_invented_ordinary_scope_draft_rejected(self):
        rows = self.draft_rows()
        rows[0]["scope_class"] = "INCLUDED_ORDINARY_EQUIPMENT"
        result, generated = self.scaffold_draft(rows)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["status"], "invalid_input_contract")
        self.assertFalse(generated.exists())

    def test_reversed_reactor_scope_method_draft_rejected(self):
        rows = self.draft_rows()
        rows[1].update(scope_class="LOGICAL_OR_REACTOR_EXCLUSION", method_id="EXCLUDED_REACTOR")
        result, generated = self.scaffold_draft(rows)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(generated.exists())

    def test_legal_reactor_scope_wrong_method_draft_rejected(self):
        rows = self.draft_rows()
        rows[1]["method_id"] = "EXCLUDED_REACTOR"
        result, generated = self.scaffold_draft(rows)
        self.assertEqual(result.returncode, 1)
        self.assertIn("excluded_scope_method_conflict", {i["type"] for i in json.loads(result.stdout)["issues"]})

    def test_pending_inventory_producer_state_allowed_only_in_draft(self):
        rows = self.draft_rows()
        rows[0].update(scope_class="physical_scope_unresolved", method_id="METHOD_GAP", mapping_status="method_gap_open")
        result, generated = self.scaffold_draft(rows)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.skill = generated
        self.assertEqual(self.assert_blocked_before_cost(strict=False)["input_contract_status"], "pass")

    def test_duplicate_draft_rows_rejected(self):
        rows = self.draft_rows()
        result, generated = self.scaffold_draft(rows + [rows[0]])
        self.assertEqual(result.returncode, 1)
        self.assertFalse(generated.exists())

    def test_missing_draft_columns_rejected(self):
        rows = self.draft_rows()
        for row in rows:
            del row["mapping_status"]
        result, generated = self.scaffold_draft(rows)
        self.assertEqual(result.returncode, 1)
        self.assertIn("input_columns_missing", {i["type"] for i in json.loads(result.stdout)["issues"]})

    def test_mutated_generated_draft_fails_runner_and_validator(self):
        result, generated = self.scaffold_draft(self.draft_rows())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        path = generated / "references" / "equipment-method-assignment.csv"
        rows = read_csv(path)
        rows[0]["scope_class"] = "INCLUDED_ORDINARY_EQUIPMENT"
        write_csv(path, rows)
        self.skill = generated
        audit = self.assert_blocked_before_cost(strict=False)
        self.assertEqual(audit["reason"], "invalid_input_contract")
        self.assertEqual(audit["input_contract_status"], "fail")
        result = run(BUILDER / "scripts" / "validate_generated_skill.py", ["--skill-dir", generated, "--allow-draft"], self.case / "invalid-draft-validation.json")
        self.assertEqual(result.returncode, 1)

    def test_unreviewed_package_boundary_remains_legal_draft_gap(self):
        rows = self.draft_rows()
        for row in rows:
            row.update(procurement_role="", package_scope_status="unreviewed")
        rows[0]["physical_equipment"] = "tower_and_physical_auxiliaries"
        result, generated = self.scaffold_draft(rows)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.skill = generated
        self.assertEqual(self.assert_blocked_before_cost(strict=False)["input_contract_status"], "pass")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True)
    args = parser.parse_args()
    args.work_dir.mkdir(parents=True, exist_ok=True)
    WORK = Path(tempfile.mkdtemp(prefix="cost-guards-", dir=args.work_dir.resolve()))
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CostGuards)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {"synthetic": True, "engineering_acceptance": False, "work_dir": str(WORK),
              "tests_run": result.testsRun, "failures": [(str(test), detail) for test, detail in result.failures],
              "errors": [(str(test), detail) for test, detail in result.errors], "passed": result.wasSuccessful()}
    (WORK / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)
