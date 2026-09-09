---
name: aspen-flowsheet-error-repair
description: Diagnose and repair Aspen flow failures using current authority, physical service, Control Panel/history, one evidenced change and same-case replay. Use for bad blocks, recycle/control/scale failures, product misses, I/O or run evidence defects; preserve process and precision contracts and separate local progress from strict delivery.
---

# Aspen Flowsheet Error Repair

## First reads and scope

Read `references/ERROR_MEMORY.md`, the chemical expert's
`STRICT_ACCEPTANCE_AND_LEARNING.md`, and current project change-offset,
status and freeze ledgers. The triad remains:

`aspen-document-driven-flowsheet -> this repair skill -> aspen-plus-operations`

The process layer owns allowed changes. This skill diagnoses; operations
executes and supplies the single strict version-bound evidence gate.

## Repair Loop

1. Preserve the accepted candidate and freeze the current failure/allowed edits.
2. Classify resource/startup, input/card, property/phase, solver/recycle/control,
   process target, equipment capacity or delivery identity before changing anything.
3. Reconstruct the physical service and affected stream path before solver knobs.
   Convergence is not feasibility; heat/pressure paths and component fate matter.
4. Capture the current limiting message, object and same-run evidence. Apply one
   evidenced repair family on a protected candidate; inspect the next run again.
5. Recompute downstream consumers, inner quality controls, balances, utilities
   and equipment when the change affects them.
6. Report whether the original blocker is removed, another blocker was exposed,
   or the same hypothesis failed. That local result does not imply full acceptance.

## At the relevant failure, read the detailed method

- Phase/specification or external-reboiler/APW consistency:
  `references/repair_workflow.md`.
- Recycle inventory, scale/root, Calculator ordering or startup state:
  `references/recycle_scale_control_repair.md`.
- Tower island/spec optimization: `aspen-tower-optimization-workflow`.
- Formal kinetics: current kinetics expert/freeze before touching rates.
- Mechanical I/O, events, lock/timeout, cards or exact-file verification:
  `aspen-plus-operations`; do not write another parser/COM lifecycle.

## Red lines

Preserve current method, property/kinetics, precision and product targets.
No hidden heater pressure rise, external outlet substitution or unapproved
SEP surrogate. Initial estimates/damping/solver method/iteration limits can
be tested after diagnosis, but they do not authorize lowering tolerances.

A user may explicitly authorize a current-case relaxation. Preserve its scope
and failed strict checks; all results/descendants remain case-only and cannot
enter self-evolution, shared success cases, default retrieval or rules.

## Acceptance and return

Keep `local_fix_verified`, `simulation_clean`, product gates and
`strict_delivery_passed` separate. Strict delivery needs complete supported
version/format counts, no actual same-run raw-history problems, valid run/file
identity and the exact final-path no-edit reopen, plus every current project gate.
Required Input, BLKSTAT and product values never override dirty/missing evidence.

Return changed files/cards, original and new diagnostics, source/run hashes,
affected consumers, verified scope and remaining actions. Audit logs may retain
all attempts; they are not automatically learning examples.
