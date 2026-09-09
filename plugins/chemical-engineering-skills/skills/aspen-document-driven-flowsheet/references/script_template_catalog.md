# Aspen Script Template Catalog

Use this catalog when a project needs a new script that future agents can adapt
quickly. Prefer scripts newly built or materially modified in the current work.
Old scripts may be consulted as examples, but their chemistry, stream IDs,
component IDs, pressures, split values, tolerances, and local paths stay
quarantined until re-derived.

For broad selection, open `script_template_knowledge_graph.md` first. It
contains dozens of connected template nodes and points each node back to one of
the executable anchor templates below.

## Template Index

| Scenario | Template | Function | Edit These First |
| --- | --- | --- | --- |
| Crawl project folders for reusable script families | `scripts/templates/project_script_inventory_template.py` | Count script prefixes, repeated basenames, and content keyword families | root path, suffixes, exclude folders |
| Source/taskbook gate audit | `scripts/templates/source_taskbook_gate_audit_template.py` | Check source-ledger completeness, property-method freeze rows, user adjustments, and unread/blocked taskbook items | required categories, project source ledger schema, evidence paths |
| Aspen COM run/export or no-run probe | `scripts/templates/aspen_operation_template.py` | Open case, optionally run, export evidence, write summary | `connect_aspen`, `open_case`, `export_case`, stream/status adapters |
| Layout-preserving original-archive repair | `scripts/templates/aspen_operation_template.py` plus project-local no-mutation reopen mode | Use `.inp` only for diagnosis, apply accepted COM-tree edits to the original `.bkp/.apw`, rerun, reopen without edits, export, and hash-copy | original archive path, accepted mutation list, no-mutation flag, Control Panel scan, hash manifest |
| Aspen COM lock/watchdog helper | `scripts/templates/aspen_com_lock_watchdog_template.py` | Prevent parallel Aspen sessions, record lock owner, provide idle wait helper | lock path, owner, project wait/export adapters |
| Candidate matrix or INP variant sweep | `scripts/templates/aspen_candidate_matrix_template.py` | Patch text candidates from a JSON spec, write sidecars, optionally run queue | candidate JSON spec, regex patches, runner command |
| Heat-pump/VRC connection sweep | `scripts/templates/aspen_candidate_matrix_template.py` plus `aspen_operation_template.py` | Generate compressor-pressure/suction-superheat candidates and run/export phase, duty, and product-gate evidence | tower tag, overhead stream, reflux-drum route, discharge-pressure list, superheat basis, no project values |
| Open-run delivery QA | `scripts/templates/open_run_readiness_template.py` | Clean reopen, Required Input/start-run placeholders, call readiness recorder | Required Input adapter, start-run adapter, evidence paths |
| Migrated-path portability QA | `scripts/templates/path_migration_readiness_template.py` | Copy package to neutral path, inventory/hash, scan stale absolute paths, leave Aspen migrated-run adapter | migration path, old root, Aspen reopen/start-run adapter |
| Physical plausibility gate | `scripts/templates/physical_plausibility_gate_template.py` | Refuse accepted delivery when a converged run violates source/engineering checks | project ledger JSON with check statuses and evidence |
| Repeated error repair loop | `scripts/templates/control_panel_repair_loop_template.py` | Capture before/after messages and log each fix attempt | `capture_control_panel`, `apply_fix`, stop condition |
| Static exported-INP support audit | `scripts/templates/static_inp_audit_template.py` | Check expected blocks/streams/cards and forbidden text before delivery review | expected IDs/patterns; do not treat as runnable proof |
| Delivery hard-gate audit | `scripts/templates/delivery_gate_audit_template.py` | Check required files, forbidden text, and JSON pass/fail gates | project-local manifest, required files, text/json rules |
| Current-work script generalization | `scripts/templates/script_generalization_manifest_template.py` | Scan/review a project script and write a reuse manifest | safe scope, forbidden scope, parameter map |

## Standard Script Structure

Every reusable Aspen script should follow this shape:

```text
1. argparse inputs
2. explicit config/dataclass
3. authority/evidence paths
4. adapter functions for Aspen-specific calls
5. main action with small stop condition
6. JSON + Markdown summary output
7. nonzero exit on failed hard gate
```

## Scenario Notes

`aspen_operation_template.py` is the base shape for mechanical Aspen probes.
Copy it into the active project and fill only the adapter functions. Keep
project values in CLI arguments or a local config file, not in the generic
template.

`project_script_inventory_template.py` is the crawler to run before script
promotion. It says which folders and function families are common; it does not
make any script reusable by itself.

`source_taskbook_gate_audit_template.py` is the pre-mutation source gate. It
does not read source files by itself; copy it into the project and feed it a
project-local JSON ledger created from the taskbook/design report. It blocks
model mutation or final delivery when official requirements, property-method
freeze rows, user adjustments, or unread/ambiguous items are missing.

`aspen_com_lock_watchdog_template.py` supplies the common lock/timeout helper
seen across many Aspen projects. Use it to avoid concurrent COM sessions and to
record ownership; do not put card edits inside the helper.

`aspen_candidate_matrix_template.py` covers repeated candidate generation and
queue execution. Put all tower/feed/spec values in a project JSON spec, keep the
generic template value-free, and promote only from Aspen run/export evidence.
For heat-pump/VRC sweeps, generate topology variants from an already accepted
base tower, then run the compressor phase gate and project hard-gate audit
before claiming even a supplement. Pressure ratios, efficiencies, superheat
temperatures, and savings from old projects are not reusable values.

`open_run_readiness_template.py` is for final deliverables. It must prove clean
reopen, Required Input completeness, start-run readiness, and same-version
export after reopen before a file is called runnable.

`path_migration_readiness_template.py` is for package portability. It copies the
final files to a neutral path, inventories hashes/sizes, scans stale absolute
paths, and provides an adapter slot for migrated Aspen reopen/start-run.

`physical_plausibility_gate_template.py` is for "runs but unrealistic" cases.
It evaluates a project-local plausibility ledger and blocks delivery unless the
source/stoichiometry/mass/recycle/pressure/energy/separation checks pass.

`control_panel_repair_loop_template.py` is for repair-only work. It records the
first limiting Control Panel/history message before and after a single repair
family. It must not edit default/global precision.

`static_inp_audit_template.py` is a cheap support check for exported `.inp`
files. It can catch missing expected block/stream names or forbidden edits, but
it never replaces Aspen Required Input or clean-session start-run evidence.

`delivery_gate_audit_template.py` is for final package checks: required files,
forbidden text, and JSON booleans. It must be paired with open-run readiness for
any runnable-case claim.

`script_generalization_manifest_template.py` writes a project-local reuse audit,
not a promotion decision. Invoke the installed template so it can reuse
`scripts/learning_admission.py`; do not copy a standalone validator into a project.
It retains the original CLI parameters and adds `--project-dir`,
`--lineage-manifest`, `--task-closure`, `--candidate-review`, and the reviewed test-only
`--eligibility-module` / `--quality-assessor` overrides. Overrides accept only
the existing installed/source canonical modules, never a project-supplied gate.
The central lineage verifier must first confirm the user's explicit closure of
the exact task/version through `task_closure`; a delivered result or “好” is not
closure. Mid-task work only records project audits. Missing closure/ineligible
lineage, unbound source/scope or unresolved lexical findings return `2` with
audit-only output. After verified user closure, strict lineage without a
complete quality review permits `draft_review_only` and returns `0` for draft
creation, not quality readiness. A ready central quality review may mark
`candidate_review_only`; no path writes a skill or enables default RAG.
The quality call is the existing shared
`learning_admission.quality_review`, not another template-owned evaluator.
`--task-closure` supplies the user's close event through the shared adapter;
omit it only when that hash-bound event is already in the manifest. The central
result must explicitly include `task_closure_verified=true`; an older evaluator
without this field cannot admit a draft.
The existing `begin_candidate_once` / `finish_candidate_once` helper keys one
candidate by closed task/revision, closure hash, channel, admitted root and target
within the project output directory. Repeated calls reuse hash-verified artifacts;
`add_quality_review_version` appends a changed review without another candidate.
An incomplete or drifted prior candidate is reported, never overwritten.
No lexical findings do not prove that project values have been generalized.
Use the central candidate-quality/promotion contract before any shared release.

## Observed Reusable Families

Workspace crawl showed these recurring script families across project folders:

- `build/run/probe/audit/write`: dominant naming families; use them as scenario
  labels, not as proof of reuse.
- Aspen COM open/run/export with global lock, timeout, Control Panel capture,
  and before/after export: use the operation and lock/watchdog templates.
- Candidate matrices and sweep queues: use the candidate-matrix template plus a
  project-local JSON spec.
- Delivery/package gates: use delivery-gate audit, static INP audit, and
  open-run readiness together.
- Kinetics/unit ledgers: keep in the kinetics freeze route; do not generalize
  constants or reaction values from old projects.

## Knowledge Graph Link

Use `script_template_knowledge_graph.md` when:

- a task says "prepare many templates" or "knowledge graph";
- no single row in this catalog is specific enough;
- an old project script seems reusable but its family has not been classified;
- the agent needs a canonical chain such as new build, repair, tower island,
  delivery, or script reuse.

The matching machine-readable graph is `script_template_knowledge_graph.json`.
Use `scripts/query_script_template_graph.py` when a task needs quick lookup by
cluster, node ID, keyword, or canonical path without loading the whole graph.

## Evidence Contract

Each script should write:

```text
changed_or_checked_files:
case_version:
control_panel_or_history:
required_input_status:
block_status_file:
stream_status_file:
summary_json:
decision:
next_allowed_action:
```

## Promotion Rule

This local checklist is necessary context, not a release gate. The central
candidate-quality and human-promotion contract additionally owns demonstrated
information gain, claim-appropriate verification/contrasting scope, approval,
and exact source/target version binding; a single successful slice cannot
establish cross-project generality.

Before moving a script from project-local material library into a generic skill:

- it was newly built or materially modified in the current work;
- project values were removed or parameterized;
- inputs and outputs are documented;
- it was tested on at least one current slice;
- failure exits are meaningful;
- safe reuse scope and forbidden reuse scope are written.
