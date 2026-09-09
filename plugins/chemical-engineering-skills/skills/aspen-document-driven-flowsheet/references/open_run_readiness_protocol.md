# Aspen Open-Run Readiness Protocol

Use this protocol before any Aspen file is called a deliverable. A file that
opens with missing Required Input, missing cards, disconnected streams, or a run
button that cannot start is not deliverable even if an older branch once ran.

## Two Gates

`Open-Run Readiness` is the minimum gate:

- The delivered `.bkp`/`.apwz`/`.inp` opens in a clean Aspen session.
- Required Input is complete for the delivered version.
- The model can start a run without manual entry after opening.
- A same-version export after reopening exists.

`Accepted Run` is the promotion gate:

- The same reopened version runs or reaches the user-accepted blocker.
- Block/calculator/spec statuses, stream results, Control Panel/history, and
  audit files support the process claim.
- Product, recycle, pressure, kinetics, property, and delivery gates pass or are
  explicitly quarantined.
- The final package also passes migrated-path readiness and physical
  plausibility gates from `delivery_portability_and_plausibility_gates.md`.

Do not merge these gates. A file may be open-run-ready but not accepted; a file
that is not open-run-ready cannot be delivered as runnable.

## Required Checks

For the delivered version, verify and record:

```text
case_file:
case_version:
clean_session_reopen:
required_input_complete:
manual_inputs_needed_after_open:
run_can_start_without_manual_input:
run_result_or_user_accepted_blocker:
same_version_export_after_reopen:
control_panel_or_history:
block_status_file:
stream_status_file:
audit_json:
remaining_required_input_items:
post_run_bkp_saved:
migrated_path_readiness_record:
physical_plausibility_record:
decision:
```

`manual_inputs_needed_after_open` must normally be `none`. If any manual input is
needed, the case is not a runnable deliverable.

## Detection Ladder

Use Aspen's own state as the primary evidence. Static file parsing is only a
supporting check.

1. Clean-session reopen.
   Start a fresh Aspen session, not a previously solved GUI state. Open the
   delivered `.bkp`/`.apwz` or import the delivered `.inp`. Record whether the
   file opens without repair prompts, missing component/property prompts, or
   broken references.

2. Required Input tree check.
   Inspect the Aspen Required Input/Data Browser/Navigation status through COM
   if available, or through captured GUI/Control Panel evidence if COM cannot
   expose the tree. List every incomplete node by path or block/card name. If
   any Required Input item remains, the case is `blocked`, not runnable.

3. No-manual-input start-run check.
   Without typing or clicking any missing-data fixes, start `Run`/`Run2`. This
   is a smoke test that proves Aspen can begin calculation from the delivered
   file. If Aspen stops later for convergence or product-gate reasons, the file
   may still be open-run-ready but not accepted. If Aspen refuses to start
   because input is incomplete, the file fails readiness.

4. Same-version export after reopen.
   Export the reopened case immediately after the readiness probe. The export
   proves the delivered file, not an older solved branch, is the evidence
   surface. Keep the exported `.inp`, Control Panel/history, and any status CSVs
   beside the readiness record.

5. Static completeness audit.
   Parse exported `.inp` and status files for expected components, property
   method, feed streams, block paragraphs, reaction bindings, Calculator/Design
   Spec paths, pressure devices, and product/recycle outlets. This can find
   omissions, but it cannot overrule Aspen's Required Input tree. A static pass
   without a clean-session reopen/start-run check is only `provisional`.

6. Migrated-path readiness.
   Copy the exact final package or final case file to a fresh neutral path and
   repeat clean-session reopen, Required Input, start-run, and same-version
   export on the migrated copy. Scan text/scripts/manifests for stale absolute
   paths pointing to the old workspace. If migration fails, the package is
   `blocked-portability`.

7. Post-run `.bkp` confirmation.
   If a `.bkp` is claimed as final, it must be saved/exported after the accepted
   run, then reopened and migration-tested. A `.bkp` from an unrun or
   half-entered branch is only a `candidate-backup`.

Truth table:

| Evidence | Decision |
| --- | --- |
| Clean reopen + Required Input complete + Run starts without manual input + same-version export | `open-run-ready` |
| Open-run-ready + same-version run/audit gates pass + migrated-path gate + physical plausibility gate | `accepted-runnable` |
| Static audit passes, but no Aspen clean reopen/start-run evidence | `blocked` or `provisional`, not deliverable |
| Aspen opens with missing Required Input or asks for manual card values | `blocked` |
| Run starts but later fails convergence/product gate | open-run-ready may pass; accepted run fails until repaired or accepted as blocker |
| Original path opens but migrated path fails | `blocked-portability` |
| Run converges but physical plausibility fails | `blocked-physical` |
| `.bkp` was not saved/exported after accepted run | `candidate-backup`, not accepted-runnable |

## Required Input Surfaces

Check at least:

- component list and component data;
- property method and binary/parameter support needed by the active route;
- all feed streams: flow, composition, temperature, pressure, and valid phase;
- all block required cards: reactors, flashes, towers, separators, pressure
  devices, heaters/exchangers, splitters, mixers, pumps/compressors/valves;
- reaction sets and reactor bindings;
- Calculator read/write paths and execution order;
- Design Spec/Vary targets, variables, bounds, and tolerance lock;
- convergence objects, tear streams, and initialization values;
- product, purge, vent, wastewater, treatment, and recycle outlet streams;
- pressure path and heat-exchanger pressure-drop convention;
- report/package claims tied to the same version.

## Operation Contract

Ask `aspen-plus-operations` for a delivery/readiness QA operation:

```text
Operation goal: clean-session reopen, Required Input check, start-run check, same-version export
Authority artifact:
Current case/version:
Forbidden changes: no process/card edits except explicitly authorized readiness fixes
Default precision lock:
Required evidence: reopen evidence, Required Input status, Control Panel/history, after-reopen export, block/status and stream/status files
Stop condition: ready, blocked by named Required Input item, or blocked by Aspen resource/COM failure
```

For final packages, add:

```text
Migration test dir:
Post-run BKP requirement:
Physical plausibility ledger:
Required evidence: migrated reopen/start-run/export, path scan, physical plausibility decision
Stop condition: accepted-runnable, open-run-ready-only, blocked-portability, blocked-physical, or candidate-backup
```

## Failure Handling

If the readiness check fails:

1. Do not deliver the file as runnable.
2. Route through `aspen-flowsheet-error-repair`.
3. Read the Required Input tree and Control Panel/history before editing.
4. Fix the smallest missing input or broken reference.
5. Re-run clean-session reopen and start-run checks.
6. Record the result in the learning log and material-library slice.
7. If the original path works but the migrated path fails, repair packaging and
   path assumptions before touching process chemistry.
8. If the run converges but plausibility fails, route back to process authority:
   source route, stoichiometry, conversion/selectivity, property method,
   pressure/HX topology, recycle closure, or separation target may be wrong.

## Final Claim Text

The final handoff must say one of:

- `Open-run ready`: clean reopen, Required Input complete, and run starts
  without manual input.
- `Accepted runnable`: open-run ready plus same-version accepted run evidence.
- `Accepted runnable and portable`: accepted runnable plus migrated-path
  readiness and physical plausibility evidence.
- `Blocked`: names the exact Required Input item, COM/resource blocker, or
  user-accepted limitation.
