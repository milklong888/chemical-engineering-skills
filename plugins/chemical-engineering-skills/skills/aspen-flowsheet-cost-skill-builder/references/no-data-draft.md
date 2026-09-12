# Framework When Cost Data Are Missing

Missing source data authorizes inventory and schemas, never prices. Reuse the
scaffolder with `--draft-only`; do not recreate its runner. Keep all uncertainty
in the input ledgers. A disabled example is not a successful cost run.

For a text-only equipment list, write the following minimal inventory files to
the project work directory. Empty CSVs have headers only, with no placeholder
prices or fabricated evidence. Populate known values and leave unknowns empty.

| File | Minimum columns or keys |
| --- | --- |
| `skill_spec.json` | `project_name`, `template_id` |
| `mother_template_inventory.csv` | `template_id,bkp_path,bkp_sha256` (one row, blank path/hash if unavailable) |
| `equipment_inventory.csv` | `equipment_item_id,block_id,aspen_block_type,physical_equipment` |
| `equipment_method_assignment.csv` | `equipment_item_id,block_id,aspen_block_type,physical_equipment,scope_class,method_id,source_ids,mapping_status` |
| `missing_parameter_register.csv` | `equipment_item_id,parameter,unit,source,status` |
| `source_request_register.csv` | `gap_id,block_id,status,request` |
| `source_search_log.csv` | `query,source_id,result` |

Use these literal values; `scope_class` and `method_id` are different columns.
Do not invent synonyms such as `INCLUDED_ORDINARY_EQUIPMENT` or `EXCLUDED_REACTOR`.

```csv
equipment_item_id,block_id,aspen_block_type,physical_equipment,scope_class,method_id,source_ids,mapping_status
HX-001,,,heat_exchanger,purchased_equipment_candidate,METHOD_GAP,,unreviewed
R-001,,,reactor,reactor_excluded,LOGICAL_OR_REACTOR_EXCLUSION,,rule_fixed
S-001,,,logical_splitter,excluded_logical_or_bulk,LOGICAL_OR_REACTOR_EXCLUSION,,candidate_requires_physical_scope_review
U-001,,,utility,utility_opex_separate,UTILITY_OPEX,,unreviewed
X-001,,,unknown,physical_scope_unresolved,METHOD_GAP,,method_gap_open
```

The last row is a legal unresolved draft state, not permission to calculate.
All inventory IDs must have exactly one assignment and vice versa. If inventory
also includes `scope_class` or `method_id`, they must agree with the assignment.
Source gaps, `METHOD_GAP`, unreviewed mappings and unknown package inclusions may
remain pending; missing columns, unknown enums, duplicates and scope/method
reversal are invalid input even in `--draft-only`. The scaffolder rejects such
input before creating/updating a target. Correct it and rerun the official tool.

When no reviewed recipe exists, use `METHOD_GAP`, empty `source_ids`, and unreviewed
mapping. Logical blocks/reactors remain documented exclusions. One HeatX
with hot and cold sides remains one exchanger, with subtype unknown until
equipment evidence exists. Record explicit open requests rather than guessed
universal sizing rules. Package boundaries use the fields in `mapping-rules.md`.

```powershell
python <builder>/scripts/scaffold_cost_skill.py --inventory-dir <inventory> --draft-only --skill-name <name> --skills-root <project-local-drafts>
python <generated>/scripts/run_recipe_batch.py --manifest <generated>/references/batch-manifest-template.csv --out-dir <project-output>
```

The second command revalidates the copied input contract. A valid draft returns
nonzero with `input_contract_status=pass` and `draft_only:no_cost_calculation`;
an invalid/mutated one returns `invalid_input_contract` with specific issues.
`validate_generated_skill.py --allow-draft` also requires that contract to pass.
The no-price result proves the draft's blocking path,
not a priced batch. The generated example remains disabled. Later supply reviewed
data and use `--update` without `--draft-only`; all current evidence gates apply.
