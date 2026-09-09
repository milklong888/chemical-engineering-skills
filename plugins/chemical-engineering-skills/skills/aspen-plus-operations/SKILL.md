---
name: aspen-plus-operations
description: Execute Aspen Plus case I/O, component/property and block/stream cards, calculations, run/export and strict evidence checks under a frozen upstream engineering contract. Use for mechanical Aspen implementation, COM operation, card syntax and exact-file QA; do not choose the process route or substitute project values.
---

# Aspen Plus Operations

## Start here

1. Read `references/ERROR_MEMORY.md` and the chemical expert's current
   `STRICT_ACCEPTANCE_AND_LEARNING.md`. Strict is default; any explicit
   case-local relaxation and its descendants remain audit-only, never learning.
2. Freeze the operation goal, source identity, input units, allowed edits,
   required evidence and stop condition from the current task. Missing text
   does not mean missing data: first retrieve or derive what is recoverable.
3. Use `references/operation_graph.md` to select a proven path. For fragile
   fields, query `scripts/query_manual_knowledge.py` or
   `scripts/search_aspen_help.py`; record the node/source IDs.
4. Read only the relevant section of
   `references/operations_workflow.md` before executing detailed cards,
   graphical-file preservation, reaction, solve/control or delivery work.

## Existing execution paths

| Task | Entry | What it proves |
| --- | --- | --- |
| Common session, units, version and resources | `scripts/aspen_runtime.py` | Structured operation/lifecycle evidence, not process feasibility |
| Bounded external worker | `scripts/aspen_run_supervisor.py` | Stage timeout/owned-worker supervision, not permission to kill other sessions |
| Summary/history interpretation | `scripts/aspen_evidence.py` | Complete supported-schema counts and actual diagnostics |
| No-edit candidate audit | `scripts/aspen_clean_delivery_audit.py` | The emitted evidence gates for the tested candidate/run |
| APW save/reopen | `scripts/apw_saveas_reopen_check.py` | Mechanical save/reopen separately from strict simulation/delivery evidence |
| Card rules and targeted static checks | `references/operation_graph.md` | Routes to existing documented field-specific tools |

Keep old CLI entrypoints usable. Do not create another COM/lock/parser in a
project when these cover the operation. A missing target version, partial
history, uncertain engine state or unsupported format is explicit—not zero.

## Non-skippable boundaries

- Never edit Aspen binary/archive internals as simulation inputs. Preserve the
  original graphical/layout authority when required; an INP reconstruction
  does not automatically preserve it.
- Only an independently created/owned session may be changed or closed. Aspen
  live imports are serial; release only the current owner lock. Do not attach
  to or terminate a user's unrelated session.
- Values/units come from the current project; card mechanics from current help
  and exported verification. Kinetics require their source-to-card freeze.
  Pretrained/example numbers are never defaults.
- Keep the V14 manual graph read-only to V10/vector/project imports. A new
  field-level rule needs deliberate current-help/exported-card verification.
- MCP is optional. Read `references/aspen_mcp_invocation.md` when actually
  using it; missing MCP does not block the available COM/script route.
- A run return, save, readable stream, `BLKSTAT=0`, product result or clean
  success phrase cannot substitute for strict acceptance.

## Strict handoff

Verify the same candidate's complete source-verified version/format Summary
(Terminal Errors, Severe Errors, Errors, Warnings: all named counts zero),
current raw history, run identity, and no contradictions. Physical Property is
one wrapped column in the observed local format; never fabricate columns or
missing zeros. Then check current project targets, balances and equipment.

After copying to the user-facing path, reopen and run that exact file without
model edits and bind its hashes/evidence. A staged-copy diagnostic cannot
substitute. Target-version, PFD/sidecar/USER-library and product gates remain
separate and must actually be tested for the claimed scope.

Return operation, simulation, product and delivery states separately, together
with artifact identities, failed/unknown gates and the next scoped action.
A local relaxation is `case_accepted_with_relaxation`, never `strict_passed`.
