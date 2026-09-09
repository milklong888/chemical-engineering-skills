# Flowsheet repair — on-demand diagnosis patterns

Current authority: chemical expert STRICT_ACCEPTANCE_AND_LEARNING.md and
operations/aspen_evidence.py. Local removal of one blocker is not whole-flow
acceptance. Every relaxed-origin record is excluded from learning.

## Network Position

This is the secondary main skill for pure flowsheet repair. Use the startup
triad before detailed hunting:

```text
aspen-document-driven-flowsheet
-> aspen-flowsheet-error-repair
-> aspen-plus-operations
```

`aspen-document-driven-flowsheet` owns process authority, change-offset status,
source gates, and final promotion. This skill owns the repair diagnosis loop:
what failed, what evidence controls the next fix, what may be changed, and what
must be quarantined. `aspen-plus-operations` owns mechanical Aspen actions such
as import/export, card edits, run/export, Control Panel capture, and archive QA.

Return every fix attempt to the process authority layer as `accepted`,
`provisional`, or `blocked`.

## Repair Red Lines

- Default precision is untouchable. Do not change default/global convergence
  precision, `CONV-OPTIONS PARAM TOL`, tower `TOL-SPEC`, balance tolerances,
  product-spec tolerances, or source/user-frozen tolerances as a repair.
  Relaxed-precision branches cannot pass strict repair/delivery or learning.
  An explicit user exception is case-only and keeps every failed strict gate.
- Do not loosen product purity, capacity, recovery, conversion, recycle, or
  pressure targets unless the change-offset table authorizes a real process
  deviation first.
- Do not fix a physical tower failure by replacing it with `SEP/SEP2/SEPARATOR`
  unless the source route explicitly authorizes a surrogate.
- Do not change kinetics, property method, pressure topology, recycle topology,
  or separation family before the evidence points there.
- Do not hide pressure changes in `HEATER` blocks.
- Do not rely on final stream numbers alone; Control Panel/history messages
  control the first repair step.

## Repair Loop

1. Authority and backup.
   Read project instructions, current authority files, change-offset table,
   latest status note, latest static/dynamic audits, and freeze ledgers. Identify
   the current accepted case and make or preserve a same-version backup before
   mutation.

2. Separate blocker type.
   Classify the failure before editing:
   resource/lock/COM startup, no-run import/export syntax, Required Input,
   dynamic calculation, bad block, recycle/tear, Design Spec/Calculator,
   property method, pressure topology, product gate, or delivery/package drift.

3. Principle-first feasibility pass.
   Before changing solver settings, reflux ratio, tower temperature, stage
   count, property method, or topology, reconstruct the failed unit's process
   service from the active stream path:

   ```text
   upstream block and phase:
   feed temperature/pressure and vapor fraction:
   noncondensable/inert fraction:
   condensable recovery path:
   product phases and downstream consumers:
   active operating specs and component-basis modifiers:
   ```

   If a RadFrac or other equilibrium unit reports condenser superheat,
   bubble/dew-point conflict, dry stages, or component-balance failure, treat
   that first as a phase-equilibrium/specification feasibility question, not
   as a generic iteration-limit problem. Export or probe stream component
   flows and compare the spec basis with the physical duty of the unit. For an
   inert-gas vent plus partial condenser, distinguish total overhead/feed
   ratio from a component-basis ratio such as `DB:F-PARAMS COMPS=...`; the
   latter may overconstrain the tower by tying a distillate/feed spec only to
   inerts while the real service also needs condensable recovery and reflux.
   Prefer the smallest basis repair that makes chemical sense over broad
   scans of `MAXOL`, damping, T1, reflux, pressure, or three-phase options.

   For a RadFrac tower whose bottoms also pass through an external heater,
   flash, and vapor-return loop, check whether the tower has duplicated
   reboiling service before treating the case as a generic recycle failure.
   An internal thermosyphon/kettle reboiler plus a PFD-visible external
   reboiler loop can overconstrain the bottom section, create utility
   temperature-cross messages, and later expose hydraulic flooding. Repair in
   process order: internal-versus-external reboiler role, external utility heat
   level, vapor-return/liquid-purge split role, then column diameter or
   hydraulic sizing. Do not transfer another case's split fraction, utility, or
   diameter without current exported evidence.

   For APW/PFD-preserving delivery, do not promote a branch solely because an
   exported INP or `Run2` succeeds after blanking RadFrac reboiler fields.
   Aspen GUI can still own a thermosyphon/kettle object and report Required
   Input on the tower. Treat `REBOILER`, `REB_UTIL`, and `TH_VFRAC` as one
   consistency group: preserve the original values unless the replacement
   tower configuration is proven GUI-complete. The delivery gate is a clean
   no-mutation reopen with `NextIncomplete(\Data)=('', 0)`, then run/export
   evidence from that same APW.

4. Control Panel repeatedly.
   Capture Control Panel/history before every fix attempt and after the next
   run. Record:

   ```text
   first limiting message before fix:
   affected block/spec/sequence/tear stream:
   fix attempted:
   first limiting message after fix:
   blocker changed/disappeared:
   ```

   If the message changes, follow the new first limiting message. If it repeats,
   narrow the hypothesis instead of broadening edits.

5. Fix the smallest evidenced surface.
   Use one repair family per branch: syntax/card path, missing input, property
   support, tower card, Design Spec/Vary bounds, Calculator dependency, tear
   estimate/location, pressure device, phase/feed conditioning, or product
   inventory/spec formulation. Avoid mixed edits unless an accepted backup exists.

6. Use allowed convergence aids only after diagnosis.
   Allowed aids include initial estimates, tear stream choice, solver method,
   damping/acceleration, iteration limits, diagnostic trace output, Aspen-
   recommended local cards, and physically justified feed conditioning. Do not
   change default/global precision or spec tolerances.

7. Verify same-version evidence.
   Every repair candidate must pass import/export or run/export evidence on the
   same case version: `.inp`, after-run `.inp`, block/status CSV, stream CSV,
   Control Panel/history, and any audit JSON required by the authority gate.

8. Log and return.
   Write a learning log event for every failure and fix attempt. Return changed
   files, cards touched, first message before/after, evidence files, remaining
   blockers, and the next allowed action to `aspen-document-driven-flowsheet`.
   For every completed repair family or accepted repair, also record a process
   slice in the active project's material library. Include the pre/post Control
   Panel messages, affected object, files touched, and any script newly created
   in this work that may be reusable.

## Reusable Pattern: External-Reboiler APW Hard-History Repair

Use this pattern when a RadFrac tower has an internal reboiler configuration
and the PFD also shows a tower-bottom heater/flash/split vapor-return loop, and
the user asks to preserve APW/PFD/modules.

1. Diagnose from service roles before solver knobs:
   tower bottoms heat addition, flash vapor return, liquid product or purge,
   any liquid recycle, utility heat level, and hydraulic sizing.
2. Treat `REBOILER`, `REB_UTIL`, and thermosyphon vapor-fraction fields as a
   GUI consistency group. Preserve them unless the replacement is proven
   Required-Input-complete after a clean APW reopen.
3. Use INP branches only to prove mechanism. Translate accepted changes back to
   an APW through COM, then `SaveAs(.apw)`.
4. If a replay from the original APW runs but reopens with
   `NextIncomplete(\Data)` pointing to the tower, restart from the latest
   Required-Input-complete APW branch and apply only the newly proven minimal
   change.
5. Split fractions are role variables, not reusable values. Keep vapor return
   nonzero when it supplies boilup; reduce it only when the current `.his`
   proves excess return/boilup, temperature cross, or tower hard errors. Do not
   transfer another case's split fraction, utility, or diameter.
6. Gate promotion in layers: Required Input complete, same-run hard-history
   clean and complete all-zero version-bound Summary; any actual warning also
   blocks strict delivery. `PER_ERROR=0`, `BLKSTAT=0`, or a clean result
   tree does not override severe/error messages in the same delivered `.his`.

## Reusable Pattern: RadFrac Decision-Variable Seed Repair

Use this pattern when a RadFrac block is the first hard blocker, the case has
complete Required Input, and the history says `RADFRAC NOT CONVERGED` or
material/energy balance failed without a temperature cross, missing input, or
obvious physical service conflict.

1. Preserve the product specification and its `VARY` bounds first. Do not
   loosen purity, recovery, global tolerances, `TOL-SPEC`, or default balance
   tolerances just to make the tower run.
2. Identify the manipulated decision variable used by the live specification,
   such as `B:F`, `D:F`, `MASS-B`, or reflux ratio. In COM these often appear
   directly under `\Data\Blocks\<tower>\Input\<variable>` with bounds under
   nodes such as `LB` and `UB`.
3. Compare the current seed with physically plausible or already accepted
   same-flowsheet values. A seed at the wrong side of the feasible separation
   window can make RadFrac fail even when the spec, utility, pressure path, and
   stages are otherwise valid.
4. Branch-test only the seed first, keeping the live `SPEC`, `VARY` bounds,
   condenser/reboiler type, utilities, internals, and PFD/module inventory
   unchanged. Treat the changed value as an initial guess, not as a transferred
   design target.
5. Promote only after the delivered APW is edited through COM, `SaveAs(.apw)`,
   reopened with no mutation, run/exported, and its same-version history has no
   actual warning/error diagnostics and passes the complete strict Summary gate.

Do not transfer another case's numeric seed. Transfer the diagnosis order:
hard blocker -> confirm no missing input/temperature cross -> inspect live
Design Spec/Vary -> adjust only the decision-variable seed inside the current
case's feasible range -> reopen/run the final APW.

## Reusable Pattern: Tear/Design-Spec Warning Hygiene

Use this pattern after the hard gate already passes and the user asks to reduce
or clear warnings while preserving APW/PFD/modules/heat network.

1. Classify warnings by current evidence, not by raw word search. Parse the
   final `.his` summary table for terminal errors, severe errors, errors, and
   warnings, then inspect the message context that contributes to the final
   count. Do not let transient `NOT CONVERGED` iteration text override a clean
   final hard gate unless it ends as a counted severe/error/warning or names a
   bad block.
2. For zero-feed warnings in a recycle island, prefer a tear-stream initial
   estimate from the same case's accepted converged stream result. Preserve
   stream identity, component basis, temperature, pressure, and phase/basis
   consistency. Do not delete bypassed blocks or borrow another project's tear
   composition.
3. For a Design Spec whose varied feed can start at exactly zero but the
   physical target requires a nonzero feed, a tiny positive lower bound can be
   a legitimate numerical hygiene edit. Keep the target, tolerance, upper
   bound, and manipulated variable unchanged, and verify that the final solution
   is away from the new lower bound.
4. Escalate cautiously. Local initial estimates and physically justified
   bounds come before global solver-method, nesting, or sequencing changes. If
   a global method change removes a warning but introduces final errors or a
   slower/brittle run, discard that branch.
5. Stop when the next warning would require changing Design Spec formulation,
   nesting order, property method, heat network, product target, or topology
   without a fresh authority ledger. Record the residual warning and the failed
   probes instead of hiding it by deleting modules or relaxing specs.

Transfer the workflow, not the numbers. Tear estimates, water-flow bounds,
and solver choices are case evidence, not reusable defaults.

Extra caution for last-warning cleanup: Aspen Help may recommend a GUI option
such as Secant `Bracket = Check Bounds`, but the COM/tree value can still be
unwritable or use an undisclosed enum. Probe enum values in a no-run branch
before relying on that route. Also, do not assume a same-case final manipulated
value is a safe new initial value or lower bound: in coupled recycle/design-spec
loops it can shrink the convergence basin, revive zero-flow bypass warnings, or
turn a cosmetic warning into final errors. Compare branches only after the full physical, source, product and strict
history gates pass. Fewer warnings cannot compensate for a physical failure;
a plausible local edit cannot compensate for a dirty final run.

## Reusable Pattern: Recycle Scale, Root, And Live-Control Repair

Use this pattern when a connected recycle runs but scale drifts, makeup or air
grows without bound, conversion is misreported, a Calculator works only after
the recycle closes, or early iterations produce warnings that disappear at the
final physical point. Read
`references/recycle_scale_control_repair.md` for the complete workflow.

1. Freeze scale as a boundary vector, not one feed number. Include every
   independent fresh feed, component-flow basis, composition, temperature,
   pressure, product boundary, recycle return, purge, and recovery pool.
2. Separate physical topology from numerical topology. Removing a stream from
   the explicit tear table does not disconnect it; cutting a physical recycle
   to make Aspen run is a process change and needs authority.
3. Close conversion across every physical outlet phase. Gas-stripped reactant
   is unreacted material, not chemical conversion. For seeded products, use net
   product formation when calculating selectivity.
4. Fingerprint each recycle root with fresh-boundary flows, loop inventory,
   limiting-reactant/intermediate flows, recovery split, purge, and final guard
   actuation. A clean run on the wrong root is still rejected.
5. Validate Calculator dependency and input basis from the exported computation
   order. A loop-basis ratio controller must read the recycle-closed inlet and
   execute before the block that consumes its written variable.
6. A startup guard may use `max(source_floor, margin*live_demand)` to keep
   intermediate iterations feasible, but it must return to the source floor at
   the accepted steady state. If it remains active, repair inventory/root
   selection instead of accepting the larger plant scale.
7. Use same-case converged results only as initialization. Start with the local
   failed path; broaden the warm start only after a process variable or bound
   makes the desired root unique. Broad seeding can select a different stable
   root.
8. Promote only after candidate no-edit reopen, copied-delivery no-edit reopen,
   direct Control Panel summary capture, raw-history scan, and same-run process
   gates all agree.

## Routing From Failure Type

| Failure Type | First Drilldown |
| --- | --- |
| Aspen lock, COM startup, no output files | main resource gate, then operation-layer case I/O |
| No-run import/export syntax | `aspen-plus-operations` case I/O and exported `.inp` diff |
| Required Input or bad card | Aspen graph `unknowns_router.md`, chapter node, operation card edit |
| Opens with missing Required Input | `open_run_readiness_protocol.md` -> Required Input tree/`NextIncomplete(\Data)` -> smallest missing-card fix; for RadFrac external-reboiler loops, first check the reboiler consistency group before changing topology |
| Kinetic reactor failure | `kinetics_expert_system.md` and freeze ledger before any card edit |
| Tower nonconvergence or tower bad block | `aspen-tower-optimization-workflow` and Control Panel message; when Required Input is complete and no temperature cross/service conflict appears, inspect the live Design Spec/Vary seed before changing specs or topology |
| Recycle nonconvergence | Aspen convergence graph, tear estimate/location, short probes; for external reboiler loops, first audit duplicated reboiling and vapor-return/liquid-purge roles, then prove the APW Required Input gate before promotion |
| Scale/feed drift after recycle closes | `references/recycle_scale_control_repair.md`; freeze all fresh boundaries, fingerprint the root, inspect live Calculator basis/order, and require final guards to return to their source floors |
| Startup-only reactant/flash warnings | Same-case local stream estimates first; broaden warm start only after desired-root inventory control is proven; do not accept a clean final `BLKSTAT` over dirty same-run history |
| Conversion inconsistent with material balance | Recalculate across all outlet phases and use net seeded-product formation; do not count vapor stripping as reaction |
| Calculator/Design Spec failure | `aspen_builtin_solve_fit_tools.md`, dependency chain, bounds evidence |
| Product purity/capacity miss | feed inventory, recovery path, target ledger, tower/product gate |
| Pressure/HX/PFD inconsistency | `aspen-pressure-pfd-delivery` |
| Warnings/errors in runnable case | `aspen_zero_warning_repair.md` |
| Final package claim drift | delivery/audit gates and package QA |

## Operation Contract

Pass this to `aspen-plus-operations`:

```text
Operation goal:
Authority artifact:
Current case/version:
First limiting Control Panel/history message:
Allowed repair family:
Forbidden changes:
Default precision lock:
Required evidence:
Stop condition:
```

`Default precision lock` should normally say:

```text
Do not change CONV-OPTIONS PARAM TOL, TOL-SPEC, balance tolerances,
product-spec tolerances, or source/user-frozen precision.
```

## Acceptance

A local repair is verified only for its explicitly claimed scope when:

- same-version case opens/imports/exports cleanly;
- Required Input is complete after clean-session reopen;
- run can start without manual input after opening;
- the pre-fix limiting Control Panel/history message is gone or replaced by a
  documented next blocker;
- no default/global precision or spec tolerance was changed;
- hard gates from the process authority layer still pass;
- block/calculator/spec statuses and stream results support the claimed fix;
- learning log records the failure, fix, evidence, result, and next action.
- process slice records the accepted repair and any current-work reusable script
  candidate.
- scale restoration proves every frozen fresh boundary and component basis, not
  only the headline feed; any temporary guard is inactive at the accepted point.
- conversion/selectivity claims close across all physical outlet phases on the
  same run used for Control Panel acceptance.
- same-run Control Panel/history hard-error scans agree with the claim. Result
  tree values such as `PER_ERROR=0` and repaired-block `BLKSTAT=0` are not
  sufficient when the same delivered run's `.his` still contains terminal
  severe/error messages, `ERROR WHILE EXECUTING`, `RADFRAC NOT CONVERGED`,
  `FAILED TO CONVERGE`, material/energy-balance failure, or utility
  temperature-cross errors. Such a branch is open-run evidence at most until a
  no-mutation reopen/run/export from the exact delivered file has a clean hard
  history and the complete source-verified Summary schema with all counts zero.

## Repair Learning: APW State Branching

For APW/PFD-preserving repairs, if replaying edits from the original archive
produces a clean run but the saved APW reopens with `NextIncomplete(\Data)`
pointing to a tower, retry from the latest Required-Input-complete APW branch
and apply only the newly proven minimal card change. Aspen GUI tower state can
survive in one branch but lose its input-complete bit when a larger edit set is
replayed from an older archive. Promote the branch that passes both gates:
`NextIncomplete(\Data)=('', 0)` after clean reopen, and clean hard-history
scan after no-mutation reopen/run.
