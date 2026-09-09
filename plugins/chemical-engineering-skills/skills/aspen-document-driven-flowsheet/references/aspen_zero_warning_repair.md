# Aspen Zero-Warning Repair Protocol

Use this reference when an Aspen Plus case is already runnable or nearly
runnable, but the user asks for zero simulation errors/warnings, or a previous
branch "ran through" while `.his/.sum/.rep` still contain nonterminal errors,
warnings, or final-pass recycle residue.

Do not copy chemistry, stream names, branch numbers, local paths, rates,
targets, property methods, or project-specific edits from historical cases into
a new project. Reuse only the diagnostic shape below.

## Fast Authority Pass

Before mutating the model:

1. Read the active project instructions, change-offset table, current status
   note, latest audit JSON/text, latest `.his/.inp/.bkp`, and any frozen
   kinetics or reactor ledgers.
2. Identify the current accepted surface and the last rejected surfaces.
3. List forbidden edits: kinetics, reaction network, capacity, product targets,
   tower specs, topology, rigorous block types, and property-method routes
   unless the current ledger authorizes changing them.
4. Write or update the change-offset table before any confirmed deviation.

The latest authority files outrank compressed conversation memory, old branch
names, and old "clean-looking" summaries.

## Resource And Wait Gate

Aspen COM/GUI/Engine work is lock-controlled. A lock or hung startup is not a
reason to sit idle.

1. If the workspace global Aspen lock exists, inspect owner, case path, live
   `AspenPlus.exe`/`apmain.exe`, parent Python process, command line, process
   age, CPU, and visible window.
2. If the lock is foreign and live, do static work: parse exported files, update
   ledgers, prepare no-run scripts, and define the next short probe.
3. If the lock is stale or no live Aspen engine exists, record why and continue
   with the next bounded step.
4. If logs stop at `Dispatch`, `DispatchEx`, `EnsureDispatch`,
   `DispatchWithEvents`, event-sink attach, or `InitFromArchive2`, classify the
   issue as COM startup/opening, not model convergence.
5. Put fragile COM startup in a child process controlled by an outer watchdog.
   The watchdog may kill only its own process tree and release only its own
   lock.
6. Use a clean ASCII working directory and explicit Windows environment values
   when non-ASCII paths or Aspen desktop startup exceptions appear.

Waiting tens of minutes is justified only for a final true-run verification
after cheap blockers are gone. It is not justified for lock contention, COM
creation, no-run syntax validation, or discovering a first limiting message.

## Evidence Hierarchy

Use Aspen's own diagnostics in this order:

1. Current Control Panel messages, especially the first fatal or limiting
   message in the current phase.
2. Final `.his` sequence monitor, final convergence loop tables, and final
   Results Summary.
3. Named bad-block status, `BLKSTAT`, `BLKMSG`, and run-status tree.
4. Exported `.inp` cards and convergence tree paths.
5. Stream results and product gates.
6. Raw substring counts only after phase-aware parsing.

Control Panel and `.his` files are chronological. Earlier `NOT CONVERGED`,
bound-hit, or middle-loop iteration messages can be normal history if later
sections show the loop converged and the final summary is clean. Conversely, a
file that opens and produces block results is not accepted if the final summary
still reports errors/warnings or a final loop is not converged.

For delivery packages, use the exact copied APW/BKP as the evidence source, not
only the pre-copy working file. Reopen the delivery file, run it, export the
after-run `.inp/.bkp`, stream and block-status tables, and capture the newly
written `.his`. A package with clean product streams but a dirty Control Panel
history is a failed delivery candidate until the underlying tear estimates,
reactor basis, pressure/NPSH topology, or named warning source is repaired.

## No-Run Syntax Gate

Every branch that changes `.inp` card syntax must pass no-run import/export
before dynamic calculation. This includes:

- RadFrac convergence cards such as `EXTRA-ML`.
- Design Spec/Vary cards or bounds.
- `TEAR`, component group, and convergence option cards.
- Feed composition basis rows.
- Any hand-generated `.inp` created from scripts.

Input translation failures are script/card bugs until proven otherwise. Examples
include a missing newline that merges adjacent `BLOCK` cards, a wrong old-style
keyword, an invalid component-group reference, or a malformed paragraph. Fix the
exported card and rerun no-run before running the engine.

## Structure-Preserving Fast Convergence Operations

Use these operations to converge faster without scrambling the process
structure. They are allowed only when they preserve reaction network, kinetics,
capacity, product targets, tower specs, topology, property-method routes, and
rigorous block types.

### 1. Snapshot And Partition The Run

- Save a new candidate name before each probe. Keep the last accepted `.bkp`,
  exported `.inp`, `.his`, and audit JSON/text.
- Split automation into no-run roundtrip, short diagnostic run, true-run
  verification, after-run export, and backup-reopen check. Do not combine all
  phases into one opaque script.
- Parse the latest `.his` by final phase: input translation, block/local tower
  solve, Design Spec solve, recycle/sequence convergence, final Results
  Summary. Repair the earliest still-active phase only.
- Treat repeated iteration lines as trace evidence, not final status by
  themselves. A `.his` can contain many earlier `VARS NOT CONVERGED` or
  Design Spec bound messages and still be clean if the later sequence monitor,
  run-status tree, key block statuses, and final summary say the run converged.
- Conversely, do not accept a run merely because key blocks have results if the
  final summary still reports a convergence block, severe error, or final
  mass-balance warning.

### 2. Run Short Probes To Discover, Not To Finish

- For first-limiting-message discovery, temporarily cap iteration budgets enough
  to return Control Panel/history evidence quickly. Restore or re-evaluate the
  full-run budget only after local blockers are gone.
- Stop the probe as soon as it names a bad card, tower middle loop, Design Spec
  bound, tear stream, sequence object, or mass-balance location.
- Do not run a long Broyden/Wegstein branch merely to rediscover a message that
  already exists in Control Panel/history.

### 3. Improve Initial Estimates Before Solver Method

- Prefer realistic initial stream estimates over solver-method switching.
  Reuse estimates from a previously converged scaffold, island, or earlier clean
  run when the physical boundary and property method still match.
- Seed tear streams with plausible temperature, pressure, total flow, phase, and
  key-component composition. Avoid blank, pure-component, zero-flow, or stale
  estimates for strict recycle loops.
- When a recycle/tower loop has no explicit tear estimates, Aspen may start
  recycle streams at zero. This can leave `ZERO FEED` messages in blocks that
  later converge normally. Repair by adding realistic initial estimates for the
  actual Aspen tear streams, then rerun and reparse the final `.his`; do not
  waive zero-feed history just because final stream tables look reasonable.
- Close or verify the easiest recycle first: same phase, compatible pressure,
  obvious key component, and small contaminant risk. Bring harder side loops
  back only after the main loop is stable.
- If a recycle accumulates inerts, byproducts, solvent, or trace product, test a
  small documented purge only as a closure assumption. Do not hide missing
  process treatment or product recovery behind an untracked purge.

### 4. Repair Local Tower And Design-Spec Setup First

- When Aspen names a RadFrac middle-loop issue and suggests a local convergence
  card, add that local card only to the named tower and no-run export it before
  dynamic calculation.
- When a RadFrac block eventually converges but the final history still carries
  early nonterminal tower errors, compare the accepted final tray profile with
  the block's initial estimates such as `T-EST`. If the initial profile is far
  from the accepted solution, try a local profile-seeded estimate repair before
  changing algorithms, tower specs, tolerances, or property methods. No-run
  export the revised estimate card first, then reopen/run the generated BKP to
  prove the historical errors do not recur. Do not promote the project-specific
  tray temperatures as defaults for another case.
- For Design Spec bound contact, check whether the manipulated variable path,
  units, lower/upper bounds, current value, residual, and target stream are
  correct. Widen a Vary window only if the existing target is physically
  feasible and the variable is genuinely clipped.
- If the result already meets a minimum purity or recovery but an equality
  Design Spec remains unstable, do not change the product target. Record whether
  the formal spec should remain an Aspen Design Spec or be audited externally as
  a `>=` product gate, then update the project ledger before changing it.
- Clear invalid local cards and dry-stage problems before changing global
  convergence settings. A global method switch over an active local card error
  is a time sink.

Useful fast-convergence sequence:

1. Clear invalid local tower cards first, especially options Aspen names as
   physically impossible or inconsistent with dry-stage behavior.
2. For Design Spec bound messages, widen only the manipulated-variable search
   window after checking path, units, target, current value, and both bounds.
   Do not change the product spec itself.
3. Add local advanced convergence such as `EXTRA-ML=1` only to the tower named
   by Aspen and only after a no-run export proves the card syntax.
4. If the remaining warning says mass imbalance is due to loose tear tolerance,
   inspect the final sequence monitor before tightening global tolerance.
   Moving an ill-placed tear boundary plus a realistic initial estimate can
   clear the warning faster than tolerance bracketing.
5. Clean harmless input-basis warnings last, and only when component entries
   already have a valid fraction basis with a separate total-flow specification.

### 4a. Diagnose "Failed After Utilities Were Added"

When the user says a case ran before utilities/heat integration but fails or
shows a large product drop after utilities were added, treat it as a regression
diagnosis before editing the model.

- First search for the true pre-utility archive. If it is missing, say so and
  compare only the earliest available post-utility archive, the user's resaved
  bad-state file, and the repaired/accepted file.
- Use an export-only, no-run roundtrip for each archive so all cases are in the
  same `.inp` format. Do not infer topology from ad hoc `.bkp` regex when Aspen
  can export the input.
- Diff physical flowsheet connections, block inventories, utility definitions,
  heat-exchanger material connections, product stream destinations, `FSPLIT`
  fractions, Design Spec/Vary cards, convergence objects, and tear streams.
- If a resaved `.apw/.bkp` has the same exported cards as the earlier archive,
  do not blame the resave or file version. The bad state was already present in
  the earlier archive.
- Separate two causes that look similar to users: a material stream actually
  misrouted into a utility or waste path versus a local tower/Design Spec/recycle
  loop failure triggered by the larger integrated flowsheet. Control Panel and
  final `.his` messages decide which one is active.
- Do not use nonconverged stream tables as production-rate proof. If the run has
  severe errors, RadFrac failures, Design Spec bound hits, or nonconverged final
  recycle loops, product flow can be stale or iteration-dependent. State that
  the "product drop" is a symptom until a clean material balance verifies it.
- If utilities are present only as utility definitions and product streams still
  terminate or route to product equipment, do not remove utilities as a repair.
  Fix the named local card, tower Vary window, middle-loop convergence, explicit
  tear boundary, or initial estimate while preserving the utility layer.

### 5. Move Or Narrow Tears Only From Final Evidence

- Use the final sequence monitor and final residual table to identify the
  active tear boundary. If a downstream block writes a stream that is later
  overwritten by final-pass tear updates, test moving the tear boundary to the
  upstream or downstream side supported by block mass-balance evidence.
- Component-group narrowing is diagnostic unless it improves the final loop,
  report counts, and key block mass balance together. If narrowing hides trace
  residuals but shifts imbalance to another block, quarantine the branch.
- Keep tear boundary edits separate from tolerance edits. Do not change
  boundary, component group, method, and tolerance in one candidate unless the
  previous no-run/dynamic evidence has already isolated all but one effect.

### 6. Use Solver Options As Bounded Last-Mile Tools

- Try global solver-method or tolerance changes only after topology, pressure,
  local tower cards, Design Spec paths, and initial estimates are reasonable.
- Change one convergence lever per candidate: method, maximum iterations,
  damping/acceleration bounds, final-pass option, state basis, or tolerance.
- If the user freezes tolerance, do not loosen it. Keep the exact exported
  `CONV-OPTIONS PARAM TOL` value in every candidate and final file. Other
  convergence-layer controls may be set directly to high or maximum practical
  values when the final Control Panel/history evidence names a convergence
  object: maximum iterations, Wegstein/Broyden/Newton wait counts,
  acceleration/damping bounds, final update behavior, trace/minor-component
  handling, and diagnostic print levels. These are still solver controls, not
  permission to change towers, utilities, reactions, product targets, property
  methods, topology, stream routing, or layout.
- Treat `MAXIT` increases as verification support, not diagnosis. If the same
  residual persists at a higher iteration limit, stop increasing the limit.
- For an oscillating Wegstein tear loop, prefer damping the acceleration window
  before adding more runtime: keep the high iteration budget, lower/limit
  `QMAX` around the documented damping region such as `0.5`, and only then
  compare Broyden/Direct if the final residual still cannot cross `Err/Tol < 1`.
- Quarantine any solver branch that introduces severe errors, worsens key block
  status, or trades final mass balance for loop nonconvergence.

### 7. Preserve Structure Explicitly

Forbidden as "fast convergence" shortcuts unless a fresh project ledger
authorizes them:

- Changing kinetic constants, rate basis, reaction orders, conversion values, or
  reaction stoichiometry.
- Lowering product purity/capacity targets or tower operating specifications.
- Replacing rigorous towers/reactors with `SEP`, shortcut, or black-box blocks.
- Changing property methods or property-system routing to silence warnings.
- Rerouting physical recycles, vents, purges, product recovery, or waste
  treatment without process evidence.

Fast convergence is a card, estimate, sequence, or solver repair. It is not a
license to change the process.

## Control Panel Repair Patterns

Apply the smallest edit named by Aspen.

- If a tower message says the outside loop tolerance was satisfied but Design
  Spec middle-loop did not converge and explicitly recommends `EXTRA-ML=1`,
  add `CONVERGENCE EXTRA-ML=1` only to the named tower. Do not change the spec
  target, Vary variable, topology, or property method as part of that edit.
- If a Design Spec Vary variable hits a bound, inspect the Vary variable path,
  units, current value, lower/upper nodes, residual, and whether the target
  stream result is stale. Widen only the search window when evidence shows the
  target is physically feasible and the manipulated variable is clipped.
- If a bound has already been reasonably widened and the target stream is at or
  near the requested specification, stop widening. Treat the blocker as Vary
  formulation, tree-path, unit, or stale-result diagnosis.
- If a message names an invalid card, dry stages, missing input, or a named bad
  block, repair that local card/block first. Do not start a global solver sweep
  while the local card failure remains active.
- If Aspen says a mass imbalance may be caused by a tear stream or a stream
  changed after block execution, inspect the final sequence/convergence table
  for the exact tear boundary. A tear-boundary move is allowed only when the
  final residual table and block mass-balance location support it.

### RPlug Divide-By-Zero With Converged Loops

When a runnable case eventually converges but Control Panel/history repeatedly
prints `FORTRAN DIVIDE BY ZERO` or `FPEPRT.1` for named `RPLUG` blocks during
recycle or sequence iterations, keep the repair local and structure-preserving.

Use this route:

1. Prove the first active dirty message names one or more `RPLUG` blocks, not a
   tower spec, Design Spec bound, missing Required Input item, or property-method
   failure.
2. Freeze forbidden surfaces before editing: reaction network, kinetic
   constants, rate basis, reaction orders, reactor geometry, property method,
   tower specs, product targets, physical connectivity, and global
   `CONV-OPTIONS PARAM TOL`.
3. Query or inspect the RPlug/reaction basis as needed, especially PowerLaw,
   LHHW, partial-pressure basis, and catalyst basis. This is diagnostic
   authority only; it is not permission to invent kinetics.
4. Try convergence aids such as tear estimates or solver method only to
   stabilize the loop. If the same RPlug divide-by-zero remains, stop repeating
   broad solver sweeps and inspect the named RPlug input tree.
5. If the named RPlug blocks expose `NONNEG=NO`, test a copied branch that sets
   only those blocks to `INTEG-PARAMS NONNEG=YES` / COM
   `\Data\Blocks\<block>\Input\NONNEG = YES`. This is a local numerical
   stabilization branch, not a kinetic-model change.
6. No-run export the edited candidate and verify the exported card before
   dynamic calculation.
7. Promote only if the exact reopened delivered file passes Required Input,
   starts `Run2` without manual input, exports same-version evidence, has clean
   named block statuses, and the new Control Panel/history scan is clean for
   `SEVERE`, `ERROR`, `WARNING`, `DIVIDE BY ZERO`, and recycle mass-balance
   warnings.

Do not promote alternatives that merely move the dirty message to another block,
hide it with a different tear boundary, add arbitrary trace components, loosen
global precision, or alter reaction cards. Intermediate `NOT CONVERGED` loop
lines are acceptable only when later lines show final convergence and the
Control Panel has no active warning/error/severe messages.

## Tear And Recycle Polishing

Keep three levers separate:

- Explicit tear boundary: which stream is torn.
- Initial estimate or state basis: how the torn stream is initialized.
- Tolerance/solver settings: how Aspen judges convergence.

Do not promote a candidate merely because one displayed Err/Tol value improved.
Acceptance requires report counts, final loop convergence, and key block
mass-balance/status to improve together. Removing trace components from a tear
component group can hide a residual while shifting mass imbalance into an
upstream or downstream block; that is diagnostic, not final.

Stop broad global solver sweeps when they trade one failure mode for another:

- If tighter global tolerance removes a loose-tolerance mass-balance warning
  only by reintroducing final-pass nonconvergence, stop bracketing tolerance.
- If raising global `MAXIT` just lengthens the same final-pass residual, stop
  increasing wait time and inspect the tear boundary or local tower cards.
- If Direct/Broyden/Wegstein method probes worsen active block status, report
  totals, or severe errors, quarantine those branches. Do not keep continuing a
  saved Broyden branch if the next run exactly reproduces the same residue.
- If a local `TEAR` numeric/tolerance spelling is preserved in export but the
  final warning still reports the global `PARAM TOL`, stop repeating that local
  spelling probe after one no-run plus one dynamic test.

## Feed-Basis Warning Cleanup

Treat harmless input-basis cleanup separately from process repair.

If a feed already has a total flow and component entries sum to one, and Aspen
warns that component mole flows are being normalized, changing only the
component row basis from flow to fraction may be a valid warning cleanup. Verify
with no-run export and dynamic run. Do not generalize this to arbitrary stream
data that do not sum to one or lack a total-flow basis.

## Property-Method Warnings

Do not erase cross-property-system warnings casually. An input-stage warning
about inconsistent properties across connected streams may reflect original
property routing. If the final dynamic history is clean, classify that as a
separate property-method audit topic. Changing property methods or property
routes requires a fresh property-method ledger and separate acceptance gate.

## Binary-Parameter Warning Repair

When a warning is resolved by Aspen databank retrieval or built-in parameter
estimation, treat the repaired property branch as a new separation model. Do
not assume the previous tower material gates still hold.

Fast route:

1. Preserve the source-approved property method unless the change-offset table
   explicitly authorizes a method change.
2. Use a no-run import/export to prove the estimation/databank cards are
   syntactically accepted.
3. Run the repaired property branch and compare product purity, recovery,
   recycle composition, and key tower impurities against the prior accepted
   material candidate.
4. If broad estimation removes the warning but creates a new split or azeotrope
   limit, bracket the real tower degrees of freedom before declaring the route
   blocked.
5. If a narrower, source-justified estimation set is used, keep it quarantined
   until product/capacity gates pass and the current authority ledger records
   why the selected pairs are sufficient for this project.
6. Any capacity scaling after a lower-product-cut purity bracket must be
   bounded, tied to a provisional feed scaffold rather than source-frozen feed
   data, and verified by reopened-BKP repeat evidence.

Do not add tiny or irrelevant binary parameters merely to silence an "all
pairs zero" warning. The repair must be connected to the documented component
system and then pass the same product and recycle gates as a fresh model.

## Version Suspicion

Aspen release/version suspicion is secondary. If the current Aspen release can
open or resave the file, produce Control Panel/history output, export inputs,
and run candidates, do not keep blaming the original file version unless Aspen
explicitly reports a version translation/import failure.

## True-Run Acceptance

Promote a repaired candidate only when evidence is bound and current:

1. No-run import/export passed for edited card syntax.
2. Dynamic run waited until `Engine.IsRunning=False`, not just a fixed short
   sleep.
3. `.his`, `.inp`, `.bkp` and, when relevant, `.apw` were saved with the same
   candidate stem.
4. Final `.his` summary reports no simulation errors/warnings, or the residual
   is explicitly accepted in the current ledger.
5. Named recycle/convergence loops end with final convergence, not only early
   iteration progress.
6. Key blocks have clean status and no active mass-balance/design-spec messages.
7. Product, capacity, tower-spec, and frozen-kinetics gates still pass.
8. Rejected branches are not included in final delivery except as diagnostics.
9. The project current-status note and change-offset table are updated before
   final response or handoff.

Never overwrite the user's original Aspen file unless explicitly instructed.
Save repaired candidates with new names and provide the accepted candidate path.

## Design Spec Auto-Extension Warnings

When a model meets material gates but the Control Panel reports that a Design
Spec convergence loop was extended to cover a tear loop, do not immediately
retune tower specs, feed rates, or property methods. First read the computation
order and identify the manipulated variable, spec, and tear stream. If the
warning is caused by an upstream feed Design Spec crossing a recycle or HeatX
tear, an accepted Aspen-card repair is:

```text
CONV-OPTIONS
    PARAM TEAR-METHOD=BROYDEN SPEC-LOOP=OUTSIDE CHECKSEQ=NO
    BROYDEN MAXIT=500 WAIT=4
```

Only promote this branch after:

- the roundtrip export preserves `SPEC-LOOP=OUTSIDE`;
- the exact BKP/APW reopen history has zero terminal/severe/error/warning
  counts;
- product, capacity, source numeric, heat/pressure, property-method, no-SEP,
  inhibitor/additive, reactor, and hydraulic gates still pass;
- the change-offset table records that the physical model was not retuned.

## APW Layout Preservation

When the deliverable is an Aspen `.apw` and the buyer cares about stream
positions, block placement, PFD annotations, text boxes, or drawing
presentation, treat APW layout as a separate acceptance gate from model
convergence.

- Do not assume a clean `.bkp` or `.inp` import/save preserves the original PFD
  drawing. Aspen may rewrite APW internal drawing/workspace streams and move
  stream labels or annotation boxes even when the model topology is unchanged.
- If the user reports large visual changes, first compare exported `.inp`
  flowsheet connections and block/utility inventories to separate physical
  topology changes from APW drawing-layer changes.
- For APW drawing complaints, inspect the APW compound-document streams when
  possible. Large changes in streams such as `IWD`, `IWB`,
  `PFSVData/#1/PFSVData`, `ApwnShellSettings`, `ADS`, or `ControlPanel` are
  drawing/session-layer evidence, not necessarily model-topology evidence.
- The preferred repair is layout-preserving mutation: open the user's original
  `.apw` directly, apply only the accepted tree/card edits through Aspen COM,
  then save as a new `.apw`. Avoid rebuilding from `.inp` unless the user
  accepts a redrawn PFD.
- If direct APW tree mutation cannot create the required accepted model cards
  without a redraw, a stricter fallback is an APW compound-document payload
  merge: copy the original `.apw`, replace only the embedded model archive
  stream such as `Archive.ZStg` with the already validated repaired APW/BKP
  payload, and keep drawing/session streams such as `IWD`, `IWB`,
  `PFSVData/#1/PFSVData`, `ApwnShellSettings`, and `ADS` byte-identical to the
  original. Validate this on a staging copy by opening in Aspen, exporting
  `.inp`, true-running to `Engine.IsRunning=False`, and checking final `.his`
  plus key model tokens. Do not run/save the deliverable APW itself before the
  layout hash audit, because Aspen `SaveAs` may rewrite the drawing streams.
- Keep two gates in the final audit: model gate (`.his` clean, key blocks
  clean, topology/specs preserved) and layout gate (new APW stays close to the
  original APW drawing streams or passes visual inspection).

## Skill Evolution Rule

After a successful repair, update the shared skill only with generalized,
anonymized patterns:

- Good additions: diagnostic order, stop rules, evidence gates, parser mistakes,
  no-run requirements, lock/process triage, and accepted classes of local Aspen
  cards.
- Forbidden additions: project paths, branch numbers, stream IDs, chemistry,
  rates, property choices, target values, or any source-specific model decision
  unless explicitly framed as a non-transferable historical example.
