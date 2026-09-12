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

Use `METHOD_GAP`, empty `source_ids`, and unreviewed mapping when no reviewed
recipe exists. Logical blocks/reactors remain documented exclusions. One HeatX
with hot and cold sides remains one exchanger, with subtype unknown until
equipment evidence exists. Record explicit open requests rather than guessed
universal sizing rules. Package boundaries use the fields in `mapping-rules.md`.

```powershell
python <builder>/scripts/scaffold_cost_skill.py --inventory-dir <inventory> --draft-only --skill-name <name> --skills-root <project-local-drafts>
python <generated>/scripts/run_recipe_batch.py --manifest <generated>/references/batch-manifest-template.csv --out-dir <project-output>
```

The second command deliberately returns nonzero with a current `batch_audit.json`
stating `draft_only:no_cost_calculation`. This proves the draft's blocking path,
not a priced batch. The generated example remains disabled. Later supply reviewed
data and use `--update` without `--draft-only`; all current evidence gates apply.
