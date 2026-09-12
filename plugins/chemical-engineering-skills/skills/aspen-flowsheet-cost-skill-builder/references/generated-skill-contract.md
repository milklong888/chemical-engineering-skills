# Generated Skill Contract

## Required tree

```text
<generated-skill>/
  SKILL.md
  agents/openai.yaml
  references/
    mother-template.csv
    equipment-inventory.csv
    equipment-method-assignment.csv
    missing-parameter-register.csv
    source-request-register.csv
    source-search-log.csv
    source-evidence-ledger.csv
    method-library.csv
    netl-equipment-cost-points.csv
    replacement-cost-library.csv
    comparison-service-replacement-library.csv
    comparison-cost-fallback-policy.csv
    comparison-completion-schema.md
    batch-manifest-template.csv
    equipment-input-template.csv
  scripts/
    audit_generated_method.py
    run_recipe_batch.py
    netl_equipment_cost_estimators.py
    aspen_offline_sizing.py
    cost_basis_adjustment.py
    comparison_cost_completion.py
```

## Ready criteria

- source file identity and hashes are current;
- every block has one scope classification;
- every included physical item has a reviewed mapping and known method ID;
- every cost method points to approved source evidence;
- parameter names, sources, units, equations, ranges, and rejection conditions
  are explicit;
- exact source anchors and unit tests pass;
- reactors, logical items, utility OPEX, duplicate package items, installed cost,
  and total capital are separated;
- generated batch outputs preserve candidate, selected, excluded, and unresolved
  strict states;
- no strict selected total is emitted while a physical item is unresolved or
  unreviewed;
- every comparison row has numeric central/low/high values, an IF rule ID,
  source, tier, and structural-zero flag;
- every nonstructural comparison row is positive.

## Batch manifest fields

`case_id`, `template_id`, `chain_id`, `stage`, `bkp_path`,
`expected_bkp_sha256`, `equipment_input_csv`, `base_cost_index`,
`target_cost_index`, `index_name`, `base_period`, `target_period`,
`index_source`, `operating_hours_per_year`, `enabled`, and `note`.

Each equipment input row supplies `equipment_item_id`, `method_id`,
`parameters_json`, `selected_after_review`, `selection_reason`, and `note`.
Optional comparison scaling fields belong inside `parameters_json`:
`comparison_scale_ratio`, `comparison_proxy_name`, `comparison_proxy_value`,
and `comparison_reference_proxy_value`.

## Outputs

Per case:

- `equipment_cost_candidates.csv`;
- `comparison_equipment_cost_inventory.csv`;
- `case_audit.json`;
- optional strict selected total only when all included items pass;
- mandatory comparison central/low/high totals.

Batch:

- `batch_summary.csv`;
- `batch_audit.json`;
- a strict blocked-reason list for every incomplete case;
- comparison completeness and fallback-share fields.

The generator may create an explicit draft with open strict-method gaps. The
default runner continues only when the comparison contract passes and always
produces comparison totals. `--strict-engineering` restores fail-closed behavior
for publication-quality strict totals.

## Entry And Batch Readiness

Use the bundled runner. Every invocation consumes a fresh method-audit result;
audit crashes cannot reuse `method_audit.json` from an earlier successful run.
Current source identity and package-coverage failures block both strict and
comparison calculations. Comparison fallback numbers still require separately
reviewed and hashed original sources registered in the same ledger.

Overall strict readiness is `all(enabled case strict statuses pass)` and requires
at least one enabled case. A successful first or last case cannot clear another
case's unresolved state. Check both mixed-case orderings. A no-data draft emits
only a blocking audit; its empty schemas and disabled example are not cost results.

`equipment_coverage_status` is a shared precondition: both inventory and assignment
IDs must be nonempty, unique and exactly equal as sets. Coverage failure blocks
comparison and strict calculation. `UTILITY_OPEX` pairs only with
`utility_opex_separate`; exclusion scopes pair with `LOGICAL_OR_REACTOR_EXCLUSION`.

Every row in `netl-equipment-cost-points.csv` needs a ledger-bound `source_id`.
The selected equipment/subtype/variant group's sources must be a subset of the
assignment's explicit `source_ids`; multiple qualified sources can be declared.
Candidate output `source_ids` records that actual source group and
`assignment_source_ids` retains the complete original contract. A source mismatch
blocks the batch before either cost layer emits values; it cannot fall through
to a seemingly successful comparison result.
