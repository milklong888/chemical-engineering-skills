# External Cost Data Contract

This package distributes methods and code, not NETL table extracts, project
recipes, private comparison medians or commercial cost libraries. The user
must lawfully supply and review a project-local data directory. Do not put
private source data into the public repository or silently populate missing
rows with default prices.

`inventory_flowsheet.py --data-dir <absolute_data_dir>` needs:

- `method-library.csv`
- `project-equipment-method-matrix.csv`

Supply this option alongside the template, project, INP and output arguments.
The inventory reader does not search the installed Skill for private data.

`scaffold_cost_skill.py --data-dir <absolute_data_dir>` needs:

- `method-library.csv`
- `netl-equipment-cost-points.csv`
- `replacement-cost-library.csv`
- `comparison-service-replacement-library.csv`
- `comparison-cost-fallback-policy.csv`
- `source-catalog.csv` only when the inventory does not already have a
  `source_evidence_ledger.csv`

`self_test.py --data-dir <absolute_data_dir>` additionally checks the original
reference profile's `authoritative-source-catalog.csv` and
`project-equipment-method-matrix.csv`. Its exact counts/anchors belong to that
method profile, not an acceptance standard for unrelated cost databases.

Missing, empty or unprovided required files return `dependency_unavailable`
with exit 2 before the inventory or scaffold creates any target directory.
The inventory also rejects unreadable CSVs or tables without data rows before
creating outputs. The source
review, mapping readiness, exact-anchor/range tests and strict engineering
selection gates still apply after files are supplied. File presence alone is
not source approval or a valid cost result.

Scaffolding a new Skill requires
the local Codex Skill initializer; if unavailable, the command reports that
dependency before starting creation. The public comparison schema document
and generic program templates remain bundled.
