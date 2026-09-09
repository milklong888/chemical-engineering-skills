# Aspen operations — on-demand detailed playbook

Current acceptance/learning authority is the chemical expert's
`STRICT_ACCEPTANCE_AND_LEARNING.md`. Historical warning exemptions and case
values from the old entry have been removed from this active playbook; their
unaltered source remains private, not as a distributed default instruction.
Read only the section relevant to the current operation.

## Role

This skill is the Aspen operation layer. It does not decide the chemistry,
process route, target conversion, separation method, or acceptance criteria.
Those come from an upstream skill or the current project documents.

Reuse verified methods first. Before writing a new COM/Python/MCP/script route,
check the operation graph, MCP invocation bridge, reusable operation scripts,
and manual/vector indexes. Use the smallest skill-verified route that satisfies
the operation contract. Explore a new route only when the indexed route is
missing, blocked, unsafe for the current authority files, contradicted by fresh
exports, or explicitly requested by the user; report the bypass reason.

Use this skill after the caller states:

```text
Operation goal:
Authority artifact:
Inputs and source units:
Allowed changes:
Required evidence:
Stop condition:
```

If any item is missing, pause the operation and reconstruct it from the current
task before editing Aspen files.

## Operation Graph

Load [references/operation_graph.md](references/operation_graph.md) for the
specific node:

- `case-io`: create/open/import/export `.inp`, `.bkp`, `.apwz`.
- `component-property`: components, aliases, property method, BIP/property checks.
- `block-stream`: create blocks, streams, connections, and short Aspen IDs.
- `reaction-card`: PowerLaw, LHHW, stoichiometry, phase, basis, units.
- `equipment-card`: heater, pump, compressor, valve, flash, column, split, reactor.
- `calculator`: live read/write variables and execution order.
- `sensitivity`: bracket feasible windows before targeting.
- `design-spec`: scalar target with one real manipulated variable and bounds.
- `optimization-regression`: objective/constraint or parameter fitting.
- `run-export`: run Aspen and export after-run input, stream table, block status.
- `delivery-qa`: package, PDF render/text checks, and final file integrity.

## Aspen Invocation Bridge

MCP is optional, not a hard requirement. When the `aspenplus` MCP server is
visible in Codex, load
[references/aspen_mcp_invocation.md](references/aspen_mcp_invocation.md) before
choosing an automation route. Prefer MCP for bounded standard open/run/get/set
and simple supported block/stream operations. If MCP is unavailable, continue
with the existing COM/script route and ask whether the user wants MCP installed
or enabled for future acceleration. Prefer existing COM scripts for exports,
watchdogs, global locks, hash evidence, GUI-preserving repair, unsupported
cards, packaging, and delivery QA. MCP output is operation evidence, not process
authority; all source ledgers, change-offset gates, V14 manual graph rules,
reopen/export proof, and final promotion rules still apply.

## User-Provided Manual And Graph Data

The public `references/manual_knowledge_graph.json` is an empty local-help
contract, not a commercial manual or historical test-case library. Read
`references/manual_knowledge_graph.md` for availability. Search the user's
legally installed current help through `scripts/search_aspen_help.py`, or
query separately qualified local nodes with `scripts/query_manual_knowledge.py`.
No match means unavailable local data.

An optional graph configured under `{CHEM_WORKSPACE}` may supply textbook,
standards or workflow context. Preserve source version/hash/location and
applicability. No private V10 chapters or vector payloads are bundled.

Keep value authority and card mechanics separate: current source ledgers
supply values; current software help and same-version exports prove entry
meaning. Record node IDs only when those actual qualified nodes exist.
Named IDs below are search hints when no user graph is available, not promises
of included content. Missing local help cannot be filled from historical values.

## Hard Gates

- Aspen delivery first criterion: after reopening the exact delivery
  `.bkp/.apw/.apwz` candidate and running it without further edits, the Aspen
  Run Status Results table `Summary of Simulation Errors` must be all zeros
  across every named column of the independently verified version/format
  schema. Physical Property is one wrapped column in the observed three-column
  format, alongside System and Simulation. The checked rows are Terminal
  Errors, Severe Errors, Errors, and Warnings; no missing cell may be padded. A nonzero Simulation severe/error/warning count fails delivery even
  when Terminal Errors is zero. Product flow, purity, `BLKSTAT=0`, exported
  streams, or a clean Required Input check cannot override this first
  criterion. Also scan the exact run's raw `.his` for actual problem lines such
  as `* WARNING`, `WARNING IN THE`, `SEVERE ERROR`, `ERROR IN THE`, terminal
  errors, or `CHECK THE RUN STATUS`; the final phrase `NO ERRORS OR WARNINGS
  GENERATED` is success evidence, but it does not excuse earlier actual warning
  or error lines in the same history file.
- For direct Control Panel evidence, attach an `OnControlPanelMessage` COM event
  sink and run asynchronously with `Engine.Run2(False)` while pumping COM
  messages until `Engine.IsRunning` is false. A synchronous `Run2(True)` can
  return a valid run yet deliver only a partial event stream, so it cannot prove
  the final summary by itself. Keep the event handler alive, pump briefly after
  completion, persist the full message text, and cross-check the same run's
  `.his/.sum`. Use `scripts/aspen_clean_delivery_audit.py` for BKP/INP delivery
  checks when applicable.
- Target-version compatibility gate: when the user or customer names an older
  Aspen target version, do not hand off only a latest-version `.bkp/.apw`.
  Produce or request an importable package for that target version and scan the
  text/exported evidence for newer-version-only records. For a V12 target from
  a V14 workstation, avoid V14-bound databank symbols such as `APV140`,
  `APESV140`, and `NISTV140`, avoid RadFrac `PARAM2` cards and optional V14
  column-internals export cards unless the target version is proven to accept
  them, and prefer an ASCII/no-BOM `.inp` compatibility file with old-style
  databank names when a true V12 save is unavailable. Validate in the newest
  available Aspen as a regression only; if local V12 is unavailable, label the
  V12 package as target-version compatibility candidate until it is opened in
  V12.
- Never edit `.bkp` or `.apwz` internals. Modify `.inp` or use Aspen COM, then
  regenerate Aspen binary/project files.
- When a deliverable must preserve PFD graphics, layer membership, block/stream
  sizes, or an APW/BKP template, do not promote a final file generated by
  importing an exported `.inp`; text import can drop or normalize graphical
  layout metadata. Use `.inp` exports as diagnostic/static support only, such
  as card diffs, field-name discovery, and before/after evidence. Translate the
  accepted edits back onto a copy of the original `.bkp/.apw` through Aspen COM
  tree or GUI-preserving Aspen operations. After candidate verification, copy to
  the delivery location and verify that exact copied file without model edits;
  the pre-copy working candidate does not substitute for delivery-path proof.
- APW supplement delivery must be produced through Aspen COM `SaveAs(...)` and
  then verified by reopening the `.apw`, running `Run2`, exporting after-run
  `.inp/.bkp`, and applying the project hard gates to the reopened result.
  Aspen `SaveAs(.apw)` can create or rewrite same-stem sibling files such as
  `.bkp`, `.his`, `.def`, `.appdf`, and `.ads`; therefore prefer a non-colliding
  APW stem such as `*_APW` when an accepted `.bkp` with the same stem already
  exists. If same-stem SaveAs is unavoidable, hash the protected `.bkp` before
  saving and restore/re-hash it after APW generation before final delivery.
  When a watchdog/control-panel script saves an APW in a temporary Aspen COM
  directory, copy that exact APW into the project delivery/authority folder,
  hash it, and reopen that copied APW as the source for the final audit. A BKP
  clean run plus a temp APW path is not a complete APW deliverable; the copied
  delivery APW itself must produce clean Control Panel history and project
  hard-gate evidence.
- USER subroutine delivery preflight: before handing off any Aspen package,
  scan the accepted after-run `.inp`, `.bkp` evidence, and reaction cards for
  `REACTIONS ... USER`, `SUBROUTINE=`, inline Fortran, `DLOPT`, or `xdlopt`.
  If any USER routine is involved, a bare `.bkp` is not a complete delivery.
  Package the compiled same-version DLL, DLO/linker file, `aspfiles.def` or a
  launcher that sets `xdlopt`, required runtime DLLs, source/audit evidence,
  and an open-run verification from the exact delivered folder. If the user
  wants "open Aspen and run", also prove the GUI-open path they will use, not
  only a Python/COM run with temporary environment variables.
- Absolute reaction-card gate: do not create, edit, run, or promote any kinetic
  reactor card unless every kinetic value has a frozen source-to-card ledger:
  source equation/value, source units, dimensional conversion, Aspen card units,
  exact Aspen input value, and exported-card verification. If the literature
  formula cannot be represented by the selected Aspen reaction model, stop and
  report the mismatch instead of inventing a surrogate. Fitted or apparent
  values may be used only when explicitly labeled provisional and accepted by
  the upstream authority.
- Reaction-card preflight: before touching a kinetic reaction card, verify that
  the caller supplied or referenced a kinetics-freeze ledger plus calculator
  output when unit arithmetic is nontrivial. The ledger must classify the target
  reactor as frozen/provisional/blocked and name the exact Aspen card unit
  basis to use. If the card unit basis is not confirmed, export or inspect the
  unit basis first; do not infer it from a previous runnable case. Also query
  the manual knowledge graph for the reaction family and record the node IDs
  used, such as `reaction.lhhw.overview`, `reaction.lhhw.units`,
  `reaction.lhhw.rate_con`, `reaction.lhhw.dforce`, and
  `reaction.lhhw.adsorption`. For PowerLaw, query
  `reaction.powerlaw.overview`. For RStoic, query
  `reaction.rstoic.overview` and do not present it as a kinetic reaction zone.
- RStoic series gate: if the Aspen UI option "reactions occur in series" /
  "反应连续发生" is selected, or the exported card contains `SERIES=YES`, the
  same RStoic block must contain at least two numbered `STOIC` reactions with
  matching conversion/extent entries. A one-reaction RStoic block must omit
  `SERIES=YES`; do not add a dummy reaction merely to satisfy this UI rule.
  Before promoting any RStoic case, scan the accepted after-run `.inp` for
  `RSTOIC` blocks where `SERIES=YES` and `STOIC` count is less than two. Use
  `scripts/check_rstoic_series.py` when available, and record the result in the
  run/export or final-gate evidence.
- RYield preflight: query `reaction.ryield.overview` before creating or
  repairing a yield reactor. `MOLE-YIELD` and `MASS-YIELD` are per unit mass of
  total feed or non-inert feed, not absolute kmol/h or kg/h product flows. If
  steam, water, nitrogen, solvent, or another diluent should not define the
  yield basis, classify it explicitly and use `INERTS` so Aspen bases yields on
  non-inert feed. Do not promote a conventional-component RYield case with a
  huge `SPECIFIED YIELDS HAVE BEEN NORMALIZED BY A FACTOR ...` warning or an
  avoidable H/O/C atom-balance warning; repair the basis, inert list, or yield
  ledger and prove the exported after-run RYield card plus block status.
- RPlug catalyst preflight: when a reaction uses `RBASIS=CAT-WT`, query
  `rplug.catalyst` and prove the catalyst mass basis. Distinguish catalyst
  particle density from bed bulk catalyst density; if the source gives
  kg-catalyst per bed volume, convert through bed voidage before filling
  `CAT-RHO`.
- Components/property preflight: before creating reaction or separation blocks,
  query `component_property.components_method`, freeze component IDs and the
  property method from source authority, and scan exported evidence for missing
  or estimated parameters that affect hard gates.
- Missing-property repair order: when a required component or active property
  has missing/estimated-property warnings or run failures, first try documented
  Aspen component lookup, databanks, property-source options, and source-backed
  component definitions while preserving the approved property method unless a
  change-offset authorizes otherwise. Promote only after the same run's `.his`
  and targeted scans are clean for the missing property family; do not mask a
  property gap by retuning reactions, separations, feeds, or product targets.
- Inhibitor/additive component gate: if the source names a specific inhibitor,
  entrainer, solvent, catalyst additive, or trace chemical but omits its dosage,
  do not use a major process component as a hidden placeholder. First probe
  Aspen component lookup names, CAS/formula, or an allowed pseudo-component
  route. If a trace design-basis feed is used only for flowsheet visibility,
  label it as source-limited and verify the exported `COMPONENTS` table plus
  stream composition. A final audit must not pass merely because a stream is
  named `INHIB`, `SOLV`, or similar.
- Flowsheet connectivity preflight: before creating or reconnecting blocks,
  query `block_stream.connectivity` and keep a block/stream/port map. Do not
  rely on graphical screenshots as connectivity authority.
- Calculator/Design Spec/Sensitivity preflight: query
  `calculator.define_sequence`, `design_spec.define_vary`, or
  `sensitivity.vary_tabulate` before creating live variable operations. Record
  variable units, bounds, stale-value/reinitialization risk, and same-run
  residual/results evidence.
- Calculator input-basis and sequence gate: preserve the target stream's native
  input basis. If it is defined by component mole flows, write the intended
  component flow rather than mixing a new total flow with stale component rows.
  For a recycle-loop ratio or transient guard, export the computation order and
  prove the Calculator reads the recycle-closed basis stream and executes before
  the first block that consumes the written variable. Record the final written
  value; a protective source-floor guard must be back at that floor in the
  accepted steady state unless the authority explicitly permits a scale change.
- Reaction-result audit gate: calculate reactant conversion across every
  physical outlet phase from the reactor island. When product is present in an
  inlet seed or recycle, calculate selectivity from net product formation. Do
  not use liquid-only disappearance when gas outlets contain reactant.
- Do not create a Design Spec claim from an offline sweep. For a RadFrac tower
  purity/recycle target, a fixed `D:F`, `B:F`, or reflux-ratio scan is only
  bracketing evidence unless the promoted file exports a live tower-internal
  `SPEC/VARY` pair or Aspen Design Spec that manipulates the tower variable in
  the same run. Promotion requires exported target, manipulated variable,
  bounds, residual/status where available, and same-run downstream evidence.
- RadFrac tower-internal `SPEC/VARY` card gate: export native tower specs inside
  the RadFrac block as `SPEC n ...` and `VARY n ...`, with the same index for
  each target/variable pair. The target must use a supported basis such as
  `MASS-FRAC`, `MOLE-FRAC`, `MOLE-RECOV`, `MASS-RECOV`, `MOLE-FLOW`, or
  `MASS-FLOW`; `STREAMS=` must name a real product stream of that tower; and
  `COMPS=` must name real case components. The `VARY` item must be a bounded
  RadFrac input such as `MOLE-D`, `D:F`, `B:F`, or `MOLE-RR`. For feed
  perturbation resistance, prefer recovery specs to absolute flow specs. If the
  target references streams outside the tower, use a flowsheet Design Spec
  instead of an internal RadFrac spec.
- RadFrac component-basis operating-spec audit: before retuning a partial
  condenser, vapor-vent tower, absorber/stripper-like RadFrac, or other tower
  whose feed contains large noncondensables, export the tower card and inspect
  both `COL-SPECS` and companion basis cards such as `DB:F-PARAMS`. Then read
  feed and product component flows from the COM tree, not only total stream
  flags, to decide whether a spec is total-stream basis or component basis.
  A branch where `MASS-D:F` or `D:F` is paired with `DB:F-PARAMS COMPS=...`
  can be physically different from the same ratio on total distillate/feed.
  If the accepted repair is to remove an erroneous component list while
  preserving the original BKP layout, operate on the list node itself, for
  example `\Data\Blocks\<tower>\Input\DB_COMPS`, and call `RemoveAll()`; do
  not clear `#0` one child at a time because Aspen may shift the remaining
  list entries, and `Delete()` on child nodes can fail while the child remains
  attached. Verify the after-run `.inp` no longer exports the companion basis
  card, then reopen the exact saved BKP without further edits, rerun, export,
  and compare protected inventories or heat-network inputs required by the
  project.
- For any run/export repair, use a short Control Panel/history probe before a
  long recycle/convergence wait. The probe must capture the first limiting
  Control Panel or history message, run summary, bad block/spec/sequence name,
  and any `.his/.sum/.rep` text that Aspen actually generated. If the first
  message already names a bound contact, invalid card, dry stage, missing input,
  bad block, Design Spec, Vary variable, tear, or sequence, stop the probe and
  repair that object before launching another full-iteration run.
  A diagnostic probe is successful once it names the next limiting object; do
  not convert that probe into a 30-minute wait. Long convergence runs require a
  written reason that cheaper card/path/spec repairs have already been ruled
  out by late Control Panel/history, final sequence, convergence-tree, or
  exported-input evidence.
- For layout-preserving recycle repairs, do not wholesale rewrite internal tear
  stream compositions or bases just because a clean `.inp` branch contains
  later tear estimates. First try the smallest accepted model edit on the
  original archive, preserve existing initialization, and use convergence aids
  that do not relax precision, such as solver method, damping, trace, or
  iteration limits. Verify Aspen tree names directly; for example exported
  `CONV-OPTIONS WEGSTEIN MAXIT=...` maps to the COM node
  `\Data\Convergence\Conv-Options\Input\WEG_MAXIT` in Aspen Plus V14.
  Promote only if the reopened original-archive candidate has the complete strict version-bound summary and actual raw-history gate;
  a local warning exemption is diagnostic/relaxed-case evidence only.
- Treat physical connectivity and convergence tears as separate evidence. A
  stream removed from the explicit tear list can remain physically connected;
  verify both the FLOWSHEET block/stream map and the exported TEAR card before
  claiming that recycle was preserved. Same-case stream results used as initial
  estimates must be logged separately from physical cards because broad seeding
  can select a different stable recycle root.
- When reusing a case that already contains earlier failed iterations, do not
  diagnose by the first historical match alone. If the final sequence monitor,
  last convergence block table, or Results Summary convergence tree names a
  later blocker, that late evidence controls the next operation. Record both the
  old message and the current final blocker so stale `.his` text does not send
  another agent back to an already-cleared bound or card issue.
- Distinguish COM startup hangs from Aspen model-run hangs. While automation is
  still creating COM, attaching events, opening/importing a case, or waiting for
  license/UI startup, do not treat elapsed time as flowsheet convergence. Check
  the shared Aspen lock, Aspen/Python parentage, process age, CPU, window title,
  and command line/case path. Clean up only documented orphan processes from the
  current operation; never kill another project's active Aspen process.
  Do not rely on an in-function timeout around `Dispatch`, `DispatchEx`,
  `EnsureDispatch`, or event attachment. These calls can block the Python thread
  before timeout checks run. Wrap Aspen startup in an outer watchdog process
  whenever repeatable evidence matters; the watchdog may kill only its own child
  tree, release only its own lock, and must record the last startup stage.
- If the shared Aspen lock is held by another case, do not spin in a long wait.
  Use the interval for static operations: parse exported cards/history, build
  the next COM script, update status/ledger files, and poll the lock only with
  short bounded checks.
  After one or two brief polls, leave a queued-run status with the exact command
  and stop condition, then continue non-COM work. Passive waiting is not a
  valid operation artifact.
- Batch or command-line runs are valid evidence only when Aspen outputs are
  present and clean. A zero return code with license text, no `.his/.sum/.rep`,
  or no Control Panel/history equivalent is a failed evidence path, not a
  successful run and not a reason to wait longer.
- Final delivery zero-warning gate: before promoting an APW/BKP package, reopen
  the exact delivery file, run it, export after-run `.inp/.bkp`, stream and
  block-status tables, and capture the real Aspen `.his` Control Panel history.
  The final Run Status summary must be complete for its source-verified
  version/format and all counts must be zero; the separate current raw `.his`
  must contain no actual problem lines. Targeted scans must also be clean for zero-feed
  startup, RYield normalization, atom-balance, reactor mass-balance,
  negative-NPSH, and warning/error/severe blocks. If products pass but `.his` or
  the Run Status Results table is dirty, the case is not a delivery candidate.
- Zero-warning scanners must parse terminal summary counts and message context,
  not raw warning-word frequency. Phrases that state the final run generated no
  errors or warnings are success evidence only when the same `.his` has no
  earlier actual problem lines such as `* WARNING`, `WARNING IN THE`, `SEVERE
  ERROR`, `ERROR IN THE`, terminal errors, or `CHECK THE RUN STATUS`; targeted
  hard-fail phrases, nonzero terminal counts, bad block messages, and
  current-phase warnings still fail the gate. Persist the parsed counts and raw
  problem-line scan beside the raw `.his` path.
- When a final `.his` has zero terminal/severe/error counts but nonzero
  warnings, split the operation into hard-gate repair and warning hygiene.
  Promote only no-mutation reopen evidence from the exact delivery APW/BKP.
  For warning cleanup, same-case converged tear-stream estimates and tiny
  physically justified positive Design Spec lower bounds are safer first-line
  operations than global solver or sequencing changes. If a probe clears a
  warning by introducing final errors, or raises warnings elsewhere, discard it
  and record the failed branch.
- When a Design Spec reports the manipulated variable at a bound after a
  reasonable bound expansion, and live stream results indicate the physical
  target is feasible or already met, stop widening bounds. Verify the exported
  Vary card and the actual COM/data-tree node being manipulated, including
  units, `BASIS_*` or equivalent block input nodes, lower/upper bounds, current
  value, residual/status, and stale-result risk. Repair the Vary path/setup or
  target expression before changing process targets.
- Do not enter source values directly into cards. Use a source-to-card ledger:
  source value, source units, conversion, Aspen basis value, destination card,
  card meaning, exported verification.
- HeatX shortcut design gate: when a two-stream HeatX has no project geometry
  or EDR file, do not leave it as a rating/simulation area case with missing
  area. Fill a complete process specification instead: `PROGRAM_MODE=DESIGN`,
  a real exchanger `SPEC` such as `T-COLD`, `T-HOT`, duty, or vapor fraction,
  matching `SIDE_VAR` (`COLD` for `T-COLD`, `HOT` for `T-HOT`), `VALUE` and
  units, hot/cold feed streams, hot/cold outlet streams, `MODE=SHORTCUT`,
  pressure drops or outlet pressures for both sides, and U/film options
  consistent with the upstream source/lecture basis. For HeatX text imports,
  verify with the COM tree because exported `.inp` may show `T-COLD` while the
  internal block is still `PROGRAM_MODE=SIMULATION` or `SIDE_VAR=HOT`.
  A final deliverable must include after-run evidence that `HX_AREAP`,
  `HX_DUTY`, hot/cold outlet temperatures, and `BLKSTAT` are populated.
- HeatX failure signature: `CANNOT CALCULATE AREA FOR AREA SPECIFICATION`
  usually means the block is in rating/simulation mode without enough area/
  geometry input, or the specified variable is on the wrong side. Repair by
  switching to a proper design specification or by supplying a complete rating
  area/geometry package if rating is truly intended. Do not ship the case with
  this warning as "complete input".
- For reaction cards, the ledger must be stepwise enough to audit by hand:
  literature/source value, source units, dimensional conversion, Aspen card
  value, card name/meaning, and exported-card check for each rate constant,
  activation energy, equilibrium/adsorption term, and reaction order. Surrogate
  or fitted values must be labeled as such instead of presented as
  literature-converted kinetics.
- Do not hide pressure rise in heaters. Use compressors for gas pressure rise,
  pumps for liquid pressure rise, and valves/pressure specs for drops.
- Compressor phase gate: a `COMPR` block that reports liquid phase at the outlet
  or at an intermediate condition is not a clean gas-compression result. Repair
  the upstream phase/topology, add justified suction superheat, or explicitly
  classify a two/three-phase calculation as provisional with source authority.
  A heat-pump or VRC branch cannot be promoted while the compressor has a wet-
  compression error. A syntax skeleton, not a runnable numerical default, is
  `PARAM TYPE=ISENTROPIC PRES=<source_pressure> SEFF=<source_efficiency>`; add mechanical efficiency only
  when the project/source basis requires it.
- Every operation must leave evidence: changed input card, after-run export,
  block status, stream results, and any solver/residual tables needed by the
  caller's hard gates.

## Delivery Workflow Order

For any Aspen `.bkp`, `.apw`, or `.apwz` handoff, use this order. Do not report
the case as "passed", "final", or "deliverable" before step 5 succeeds.

1. Freeze the source route, change-offset table, allowed edits, and product
   targets before mutating Aspen files.
2. Build or repair only a protected working candidate, then run/export enough
   evidence to diagnose required-input, block-status, and product gaps.
3. When a candidate appears solved, run the clean-delivery audit first: reopen
   that exact candidate with no model edits, run it, force `.his` generation,
   and parse `Summary of Simulation Errors`.
4. If any Terminal Errors, Severe Errors, Errors, or Warnings count is nonzero
   in any named column of the complete verified version/format schema,
   quarantine the candidate even if product flow, purity, `BLKSTAT=0`, and
   `NextIncomplete=('', 0)` pass. Repair the Run Status cause before continuing.
5. Only after step 4 is all-zero, run the product/capacity/impurity/recycle
   gates on the same accepted candidate and record stream/block evidence.
6. Copy the accepted file to the user-facing delivery path, hash it, reopen
   that exact copied delivery file without edits, rerun the clean-delivery audit,
   and rerun or attach the product evidence from the exact delivery file.
7. If a target Aspen version is older than the working version, create a
   target-version compatibility package before final handoff. For V12 targets,
   scan the exact `.inp` for V14-bound databanks, RadFrac `PARAM2`, optional
   column-internals export cards, UTF-8 BOM, and non-ASCII path/comment
   hazards; record what was removed or downgraded.
8. Update the project status note and change-offset table. Name any superseded
   or dirty candidate as quarantined so it is not accidentally handed over.


## Shared executable entrypoints

Use `../scripts/aspen_evidence.py` for version-bound summary and raw-history
classification; `aspen_runtime.py` for shared operation/resource primitives;
`aspen_run_supervisor.py` for an external worker deadline; and the existing
`aspen_clean_delivery_audit.py` / `apw_saveas_reopen_check.py` CLI wrappers.
Pure/mock verification does not prove the installed Aspen version or all file
formats. Inspect the emitted capability/verification state for the actual run.

Private pre-refactor entries and local validation artifacts are not distributed.
Only current same-package implementations and actual run receipts establish
operation/acceptance state.

