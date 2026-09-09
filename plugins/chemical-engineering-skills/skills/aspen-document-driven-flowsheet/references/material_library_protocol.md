# Aspen Material Library And Slice Protocol

Use this protocol to record project work as it happens and to verify delivery
across slices. Mid-task records are not permission to start self-evolution.

## Slice Timing

All slices are project audit records by default, with learning and default
retrieval disabled. Apply the chemical expert's STRICT_ACCEPTANCE_AND_LEARNING
policy before any generalization. A relaxed case or descendant never becomes a
shared slice, success example, reusable default or evolution candidate merely
because the user accepted the local result. Unknown provenance also stays local.

After each completed chunk, island, repair family, or accepted run, create a
process slice. Do not wait until the final answer to reconstruct it from memory.

At delivery, provide the result and ask whether the task is complete and whether
the user has improvement feedback. Delivery itself, an accepted local run,
`created_or_modified_in_current_work=yes`, or an ambiguous “好” does not close
the task. Keep recording within the project until the user explicitly closes
the current task/version. Preserve that user's original `close_task` message,
locator and artifact hash in the central `task_closure` contract, bound to
`task_id` and `task_revision`; use the central verifier, not free-text guessing.

Only after valid user closure may a governed review consider the central two
channels: `prompt_principle` for broad design judgment, macro principles and
ways of working (not a growing list of wording preferences), and `data_pattern`
for evidenced convergence/optimization patterns. Concrete parameters and local
solver experience remain in scoped lower-layer cases/methods. Both use the
same strict lineage and candidate-quality gates; mid-task adaptation remains
project work, not shared/default self-evolution. If no information gap or useful
general principle is demonstrated, choose `no_change`; never force a new rule
from every completed task. The post-closure digest proposes,
but does not authorize, what becomes:

- project-only evidence;
- reusable script from this current work;
- candidate skill/reference update;
- blocked or quarantined lesson.

## Slice Fields

Record each slice with:

```text
slice_id:
phase:
scope:
authority_basis:
input_boundary:
output_boundary:
blocks_or_scripts_touched:
run_status:
control_panel_or_history:
stream/status/audit_evidence:
heating_pressure_pressure_drop_notes:
calculator_design_spec_notes:
what_worked:
what_failed:
reusable_script_candidate:
next_allowed_action:
```

Use `scripts/record_process_slice.py` when possible. Store slices in the active
project folder, normally `aspen_material_library/`, not inside the generic skill.
For project scripts, choose a starting point from
`references/script_template_catalog.md` and copy the template into the project
before adding project-specific adapters.

## Script Reuse Rule

Reusable scripts may be generalized only from scripts newly built or materially
modified in the current work. This avoids mixing old project assumptions into a
new project.

Before saving a script as reusable, write:

```text
script_path:
created_or_modified_in_current_work: yes/no
original_project_values_removed:
inputs_parameterized:
outputs_and_evidence:
tested_on_current_slice:
safe_reuse_scope:
do_not_reuse_for:
target_location:
```

Allowed locations:

- project-local reusable script: `aspen_material_library/reusable_scripts/`;
- candidate skill script: a new project-local candidate directory after strict lineage admission, never the installed skill's own log directory;
- generic skill `scripts/`: only after successful evidence, generalization, and
  review.

Never promote an old script just because it exists. Reuse old scripts only as
execution references through the reuse-first gate, and quarantine their
chemistry, stream names, component IDs, pressures, split values, tolerances, and
file paths.

When a script is a reuse candidate, invoke the installed
`scripts/templates/script_generalization_manifest_template.py` with the original
script/scope parameters and a project-local `--out-dir` or `--project-dir`.
For post-closure candidate review also provide `--lineage-manifest`: the central
verifier must confirm explicit user closure for the exact task/version (with
`task_closure_verified=true`; older results without it fail), the
reachable lineage must hash-bind the exact source script, and the root artifact
must bind submitted safe and forbidden scope text. The template uses the existing
`learning_admission.py`; do not replace its decision with a manually filled
manifest. Manual notes remain audit-only.

Without verified user closure and qualified strict lineage, the command returns `2` and records only
`case_audit_only` with learning/default retrieval/canonical write all false.
After verified user closure, admitted lineage without the central
`--candidate-review` permits a project-local `draft_review_only` and returns `0`
for completed draft creation, not quality readiness. The existing shared
`learning_admission.quality_review` checks that proposal; only a ready review
may mark `candidate_review_only`, still with no canonical write/default
retrieval and no claim that generalization was proven. Inspect
the result's exact source hash, scope, test coverage and generalization risks;
then follow the central candidate-quality and human-promotion contract.
Neither an empty regex finding list nor a reused file name verifies engineering
applicability. Case-local relaxed ancestry never becomes a learning candidate.

Repeated calls for the same closed task/revision, closure hash, channel, root
and target in the same project output reuse the existing hash-verified candidate
through the shared candidate-once helper. Quality updates are separate immutable
review versions; the original manifest retains its initial review state. Read
the returned `quality_review_version` for the new assessment, not a stale initial
status. Missing/changed existing artifacts fail closed. `no_change` records do
not become shared rules, and repetition does not create another candidate.

## Final Digest

For delivery, read the necessary slices/logs and summarize project evidence;
ask for completion confirmation and feedback. Do not automatically launch deep
reflection or learning merely because a file was delivered. After explicit
version-bound user closure, the governed review may additionally summarize:

- accepted slices and evidence;
- rejected or diagnostic slices;
- reusable scripts created in this work;
- candidate skill/reference updates;
- project-specific facts deliberately kept out of generic skills;
- unresolved blockers.

## Delivery Preflight

Before final delivery, run a final cross-slice audit even if the last local fix
looked successful:

- heaters used only for heat must not hide pressure changes;
- source/taskbook gate rows and user-adjustment overlays still match the final
  claimed process and report text;
- property-method freeze rows still match every final module, section, tower,
  reactor, recycle closure, and hydraulic/equipment calculation;
- gas pressure rises have compressors;
- liquid pressure rises have pumps;
- letdown has valves;
- heat-exchanger pressure-drop convention is recorded and matches the active
  pressure ledger;
- liquid/gas pressure-drop ratios, if authorized, are checked against exported
  stream pressures;
- tower pressure paths and pressure drops are present;
- no stream has unexplained phase, temperature, pressure, or composition jump;
- recycle/makeup/Calculator/Design Spec links still point to current streams;
- final claims match same-version exports, Control Panel/history, block/status
  CSV, stream CSV, and audit JSON.
- delivered Aspen archives pass open-run readiness: clean-session reopen,
  Required Input complete, no manual input needed after opening, run can start,
  and same-version export after reopen exists.
- final package passes path-migration readiness: the copied package opens from a
  fresh neutral path, starts Run without manual fixes, exports same-version
  evidence, and has no stale absolute paths to the old workspace.
- final `.bkp` was saved/exported after the accepted run; otherwise it is a
  candidate backup, not an accepted deliverable.
- final run passes the physical plausibility ledger: source capacity,
  stoichiometry, conversion/selectivity, mass/key-component closure,
  recycle/makeup, phase/pressure/temperature, duty signs/scales, and
  separation/recovery logic are credible.
