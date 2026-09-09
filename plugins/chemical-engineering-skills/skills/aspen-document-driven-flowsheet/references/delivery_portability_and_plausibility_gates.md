# Aspen Delivery Portability And Physical Plausibility Gates

Use these gates when a case is close to delivery, when users will move files to
another path, or when a converged Aspen run looks physically unrealistic.
Convergence is evidence, not acceptance.

## Path Migration Gate

A deliverable package must survive relocation before it is called runnable.
Test the exact files that will be delivered, not a working directory that still
contains old temporary dependencies.

Minimum test:

```text
source_package_or_case:
migration_test_dir:
copied_files:
hash_or_size_before_after:
opened_file_in_migrated_path:
clean_session_reopen:
required_input_complete:
run_can_start_without_manual_input:
same_version_export_after_migration:
control_panel_or_history:
absolute_path_scan_result:
decision:
```

Procedure:

1. Copy the final package to a new short neutral directory, preferably an ASCII
   path outside the project tree, for example `C:\AspenDeliveryTest\<case_id>`.
2. Open only the migrated copy in a fresh Aspen session.
3. Check Required Input and start a run without manually fixing prompts.
4. Export `.inp`, status, stream, and Control Panel/history evidence from the
   migrated copy.
5. Scan scripts/manifests/text files for absolute paths pointing to the old
   workspace. Scripts must use CLI args, relative paths, or documented
   environment variables.
6. If the migrated copy fails to open, asks for missing input, or cannot start a
   run, mark the package `blocked-portability`.

## BKP Promotion Rule

Treat `.bkp` as a final deliverable only after the accepted run has completed.
Do not save or promote a final `.bkp` from an unrun, half-entered, or
pre-readiness branch.

Required insurance:

- final `.bkp` is saved/exported after the accepted run, not before;
- the saved `.bkp` is reopened in a clean session;
- the reopened `.bkp` passes Required Input and start-run checks;
- the same `.bkp` is copied to the migration-test path and passes the migration
  gate;
- an after-reopen `.inp` export and status/stream/Control Panel evidence are
  delivered beside the `.bkp`.

If any row is missing, call the file `candidate` or `backup`, not
`accepted-runnable`.

## USER Subroutine Package Gate

Run this gate before the delivery file list is finalized. First scan the
accepted after-run `.inp`, `.bkp` evidence, reaction cards, and package scripts
for `REACTIONS ... USER`, `SUBROUTINE=`, inline Fortran, `DLOPT`, or `xdlopt`.
If any hit is present, switch from "single Aspen file" delivery to a USER
runtime package and verify the exact open path the user will use.

Aspen `.bkp` archives do not reliably carry compiled USER routines as a
self-contained runtime. A USER case is deliverable only as a folder or archive,
not as a bare `.bkp`, unless the USER model has been replaced by an exactly
equivalent native Aspen card and revalidated.

Preferred decision order:

1. Try an Aspen-native card only if it exactly preserves the source equation,
   signs, units, denominator/adsorption terms, and exported-card result.
2. If native mapping is not exact, keep USER but ship a no-compiler runtime
   package.
3. If neither path can pass a migrated run, mark the case
   `blocked-portability`.

No-compiler runtime package requirements:

```text
post_run_bkp:
after_run_inp:
compiled_dll_same_aspen_version_and_bitness:
dll_dependency_audit:
dependent_runtime_dlls_or_installer:
dlopt_file:
aspfiles_def_or_launch_wrapper_sets_xdlopt:
source_and_compile_log_as_evidence_not_runtime:
manifest_with_hashes_and_aspen_version:
migrated_test_dir_without_root_obj_or_source:
fresh_session_open_run_export_status:
decision:
```

For Aspen Plus V14 dynamic-link delivery, the root `DLOPT` file should load the
compiled DLL instead of object/source files, for example:

```text
G781U.dll
:usegen
```

Then `aspfiles.def` or the launcher must point Aspen to that DLOPT file:

```text
DLOPT: G781U.dlo
```

Root runtime folders must not depend on `.obj`, `.for`, `.f`, `.lib`, or local
compiler environment variables. Keep those files in an evidence/source
subfolder if needed. The portability test must copy only the runtime root files
needed on the target computer, open the migrated `.bkp` or `.inp`, run without
manual recompilation, and export an after-run `.inp` plus status evidence.
Also audit the compiled DLL with a dependency tool such as `dumpbin
/dependents`. Include required non-system runtime DLLs beside the USER DLL, or
provide an installer/launcher that puts their folders on `PATH`. For Fortran
USER DLLs this commonly includes Intel runtime DLLs such as
`libifcoremd.dll` and `libmmd.dll`; missing dependencies may surface in Aspen
only as `SUBROUTINE "<name>" IS MISSING`.

For USER cases, do not assume `.inp` import is no-compiler runnable. If the
portable test only proves `.bkp` reopen/run through a compiled DLL, state that
the post-run `.bkp` is the target-computer runtime and the exported `.inp` is
audit evidence. Claim `.inp` portability only after a separate `InitFromFile`
test passes in a directory without root `.obj`/source files.

## Physical Plausibility Gate

An Aspen run that converges but violates the source route or engineering
common sense is `provisional` or `blocked`, not accepted. Build a compact
plausibility ledger before final delivery.

Check at least:

```text
source_capacity_and_product_basis:
feed_to_product_mass_closure:
element_or_key_component_balance:
stoichiometric_limit_check:
conversion_selectivity_yield_window:
raw_material_recovery_and_purge_reason:
recycle_closure_and_makeup_logic:
property_method_applicability:
phase_temperature_pressure_sanity:
heating_cooling_duty_sign_and_scale:
pressure_device_topology:
tower_or_separator_recovery_logic:
kinetics_or_surrogate_reactor_status:
source_named_unit_duty_trace:
terminal_stream_classification:
decision:
```

Rules:

- Product purity/capacity passing alone is not enough.
- For each source-named conversion, absorption, wash, tail-treatment,
  demisting, polishing, or separation duty, prove a non-empty duty trace from
  the accepted after-run streams: key component or pollutant in, intended
  change across the unit, and classified outlet fate. Zero-load "removal" or
  clean block status is not physical treatment evidence.
- A reaction cannot consume more key reactant than feed/recycle supplies or
  exceed source/literature/thermodynamic bounds without an approved offset.
- If an upstream reaction or boundary repair changes which intermediate reaches
  downstream units, repeat the stoichiometric limit and conversion-key audit for
  every affected surrogate reactor or treatment block before promotion.
- Heat duties, pressure changes, phase changes, and tower separations must have
  equipment/topology that explains them.
- Purges, vents, wastewater, residues, and byproducts must be named and
  justified. Valuable feed or solvent disappearing into waste is a blocker
  unless the source route says so.
- SEP scaffold splits may demonstrate a target, but they do not prove a final
  physical separation.
- Kinetics, property methods, and equipment/software values keep their own hard
  evidence boundaries.

## Decision Labels

| Label | Meaning |
| --- | --- |
| `accepted-runnable` | open-run ready, path-migration ready, and physically plausible |
| `open-run-ready-only` | can open/start, but physical plausibility or accepted-run evidence is incomplete |
| `blocked-portability` | original path works, migrated path fails |
| `blocked-physical` | Aspen runs, but violates route/engineering plausibility |
| `candidate-backup` | useful file or `.bkp`, but not saved after accepted run or not migrated/reopened |

## Final Handoff Requirement

For any final Aspen delivery, include:

- original accepted case path;
- post-run `.bkp` path and after-reopen `.inp` path;
- migration-test directory and evidence path;
- physical plausibility ledger path;
- unresolved portability or realism blockers, if any.
