# Special Columns: Direct Rigorous-Tower Start When DSTWU Is Invalid

This project-overlay node explains what to do when a separation is a tower
problem but `DSTWU` cannot produce a meaningful shortcut estimate. It is a
pre-route rule: for the trigger cases below, do not build a sacrificial `DSTWU`
block merely to prove that it fails.

## Trigger

Skip `DSTWU` deliberately when any of the following is true:

- Aspen cannot define meaningful light/heavy keys.
- The separation is absorption, stripping, low-temperature methanol wash, or
  cryogenic solvent absorption.
- The separation is extractive distillation, azeotropic distillation, pressure
  swing distillation, vapor-liquid-liquid, three-phase, or reactive
  distillation.
- The system is electrolyte/sour-water, petroleum, assay, or pseudocomponent
  service.
- Shortcut relative-volatility assumptions conflict with the physical
  separation method.

`DSTWU` is an initializer, not a compulsory score item. A documented bypass is
correct for special systems.

## Pre-Tower Target Freeze Rule

Before any `DSTWU`, `DSTWU-SKIP`, `RIG-INIT`, copied tower, sensitivity, or
Design Spec is created, write a target-freeze note for the tower duty.

This note is a hard stop, not a documentation nicety. `DSTWU` is only a
shortcut initializer after ordinary distillation targets are already known; it
does not discover or justify the separation objective by itself. A shortcut
tower built before LK/HK and key recoveries are frozen is diagnostic only,
regardless of convergence or plausible stage/reflux output.

For ordinary distillation, the freeze note must define:

- frozen feed stream or feed export;
- separation objective and product specifications;
- light key and heavy key, with units and source;
- target recovery/split for the keys;
- pressure path, condenser/reboiler mode, and allowable pressure drop;
- candidate manipulated variables for later Design Spec/Vary;
- pass/fail thresholds for shortcut, rigorous baseline, and final strict tower.

`DSTWU` may be built only after this note exists. A `DSTWU` run without frozen
keys and recovery targets is not a design step; it is diagnostic only.

For ordinary columns, also write a `DSTWU preflight` row before creating the
block. The row must contain feed stream/export, product names, LK, HK, LK
recovery or leakage target, HK recovery or loss target, pressure path,
condenser/reboiler assumption, candidate final Design Spec target, candidate
Vary variable and bounds, and pass/fail thresholds. If any field is not
source-backed or user-approved, stop and mark the tower
`blocked_before_DSTWU`. Do not run a shortcut column to invent these values.

For special towers, the freeze note must instead define the physical separation
target, solvent/entrainer/absorbent role, product purity or recovery targets,
solvent loss or regeneration target, pressure/temperature window, and why
ordinary light/heavy-key shortcut assumptions fail. Skipping `DSTWU` does not
skip target definition.

The final promoted rigorous tower must have a live `Design Spec/Vary` or a
documented equivalent external solve that targets the frozen purity, recovery,
solvent-loss, regeneration, or product-ratio specification. If not, it is not
accepted, even if the tower converges.

For ordinary towers, the final controller should usually target product purity,
key recovery, or product split and vary a bounded input such as reflux ratio,
distillate or bottoms rate, boilup, side draw, or another engineering-justified
degree of freedom. For regeneration or solvent-loop towers, target lean-solvent
quality, solvent loss, rich/lean loading, or the downstream gas/product ratio;
do not hand tune solvent makeup or heat duty when the same target can be closed
with `Design Spec` or a Calculator-linked `Design Spec`.

## Direct-Rigorous Start Rule

When this node is triggered, the first optimization evidence is a written
property-method-first record plus a written `DSTWU-SKIP` record, not a
shortcut-column run. The property record must be completed before any rigorous
tower block is created, because a wrong property method invalidates later
optimization. The records must state:

- component family, pressure/temperature window, expected vapor/liquid/liquid
  phases, polarity and non-ideality, gas-solubility or Henry needs, electrolyte
  or association needs, azeotrope/extractive/solvent behavior, binary-parameter
  or PCES/structure support, selected Aspen method, missing data, and status;
- why light/heavy key shortcut assumptions are invalid or unreliable;
- selected physical separation method;
- frozen feed stream or island-feed export used for the tower island;
- component list, valid phases, pressure path, and property method;
- initial engineering degrees of freedom to test in the rigorous tower.

Only ordinary distillation duties with meaningful keys should contain a
`DSTWU` block. Absorbers, solvent washes, azeotropic/extractive towers,
three-phase towers, regeneration towers for solvent systems, and electrolyte or
pseudocomponent services should start directly from the simplest rigorous
`RadFrac` or another suitable rigorous tower model.

## Required Route

1. Freeze the separation indicators before any tower block exists. For
   ordinary distillation this includes LK/HK and key recoveries before
   `DSTWU`; for special systems it includes the `DSTWU-SKIP` reason and the
   solvent/entrainer/regeneration targets before `RIG-INIT`.
2. Record the physical reason `DSTWU` is invalid in a `DSTWU-SKIP` note when
   the duty is special.
3. Freeze the property method, separation method, component list, valid phases,
   pressure path, product targets, recovery targets, solvent/entrainer loss or
   regeneration target, and final Design Spec/Vary candidate before tower
   creation.
4. Create an isolated tower island folder and Aspen file named
   `<project>-<equipment>`.
5. Build a minimal rigorous tower as a new block named `RIG-INIT`.
6. After `RIG-INIT` converges, create new blocks instead of overwriting:
   `RIG-FEED` for feed-stage or solvent-entry adjustment,
   `RIG-SENS` for sensitivity or analysis variants,
   `RIG-ANALYSIS` for Column Analysis/NQ/hydraulic evidence when used,
   and `RIG-SPEC` for Design Spec/Vary.
7. For every generated or copied tower block, update a same-folder Markdown
   sidecar note before moving on. The note must state the tower block ID,
   whether it was a shortcut, initial rigorous, feed/solvent-stage adjustment,
   sensitivity/analysis, or Design-Spec step; how it was generated; what
   variables were optimized; core data such as stages, feed stages, pressure,
   reflux/boilup, solvent or entrainer rate, product purity/recovery, solvent
   loss, duty, and warnings; the pass/fail status; and why the next step was
   created.
   Immediately after writing the sidecar, send the user a short progress note
   with the optimization action, core data, status, and Markdown path.
8. Use Design Spec only as a controller for a target purity, recovery, solvent
   loss, regeneration target, or product ratio. It is not decoration.
9. Promote only the final converged rigorous block back into the full
   flowsheet.

## Full Tower Coverage And Same-System Grouping

Before a full flowsheet is accepted, create a tower coverage ledger from the
latest exported Aspen input. The ledger must list every final tower-like block:
ordinary distillation columns, azeotropic or extractive columns, absorbers,
strippers, low-temperature solvent-wash towers, regeneration towers, solvent or
entrainer recovery towers, polishing columns, and any recovery tower introduced
to replace a forbidden separator.

Every listed tower must be represented in an isolated optimization island. A
tower is accepted only when the evidence shows the applicable route:
`DSTWU` to rigorous tower for ordinary distillation, or `DSTWU-SKIP` to
`RIG-INIT` for special systems, followed by copied-forward optimization blocks
such as `RIG-FEED`, `RIG-SENS` or `RIG-ANALYSIS`, and `RIG-SPEC`.
Each retained block must have a Markdown sidecar entry with the optimization
method and core data; otherwise the block is treated as diagnostic only.

Multiple towers may be optimized together only when they form one physical
separation system. Acceptable grouping reasons include a shared frozen feed
boundary, a common entrainer or solvent loop, a main column plus recovery or
regeneration column that determines the same recycle quality, or coupled product
purity/recovery targets that cannot be judged independently. The island note
must state the grouping reason, the final full-flow tower IDs covered by the
group, the shared Design Specs or manipulated variables, and any tower-specific
targets that still need separate evidence. For grouped towers, the sidecar must
include one subsection per tower step and a short system-level summary.

Do not use "double tower" as a generic exemption. If two towers do not share a
solvent/entrainer/recycle loop, product-quality coupling, or a common degree of
freedom, they require separate islands and separate optimization evidence.

## Direct Rigorous Optimization Template

Use this template when `DSTWU-SKIP` is triggered. The objective is to get the
smallest physically faithful rigorous tower to converge before adding
controllers or optimization.

### `RIG-INIT` Baseline

Create `RIG-INIT` as the first tower block in the island file. Fill only the
minimum rigorous-column information needed for a physical baseline:

- block family: `RadFrac` or another rigorous column model justified by the
  selected separation method;
- calculation type and condenser/reboiler options that match the duty:
  absorber or wash towers usually have no condenser/reboiler, regeneration or
  distillation towers may need them;
- number of stages or packing height from the source, a prior accepted island,
  a bounded engineering estimate, or a sensitivity plan marked provisional;
- feed and solvent/entrainer stages, with gas and liquid entering from
  physically opposite ends when applicable;
- pressure path from the upstream/downstream pressure topology, including
  explicit pressure drop if relevant;
- phase option and convergence preset suitable for the system, such as
  `Azeotropic`, `Strongly non-ideal liquid`, `Cryogenic`, absorber mode, or
  custom convergence only when the property and phase ledger supports it;
- simple operating specifications only. Do not add Design Spec, recycle
  closure, heat integration, hydraulics, or aggressive purity targets yet.

The acceptance gate for `RIG-INIT` is convergence with physically reasonable
temperature, phase, and material-balance results. It is not required to meet the
final purity or recovery target.

### `RIG-FEED` / `RIG-SENS`

After `RIG-INIT` converges, copy it to a new tower block instead of overwriting
it. Use the next blocks to locate a feasible operating window:

- `RIG-FEED`: adjust feed stage, solvent or entrainer stage, side draw stage,
  and feed thermal condition.
- `RIG-SENS`: use Sensitivity or a documented sweep for stages or packing
  height, reflux or boilup, solvent or entrainer flow, regeneration heat duty,
  pressure, and product draw rates.
- `RIG-ANALYSIS`: run Thermal Analysis, Hydraulic Analysis, NQ curves, or
  column sizing only after a rigorous block is already converged.

Each block must keep its own evidence: card export, run status, target
variables, and why the next block was created.

### `RIG-SPEC`

Only after a feasible rigorous window exists, copy the best block to
`RIG-SPEC` and add Design Spec/Vary. Each Design Spec must have:

- a real process target, such as product purity, key-component recovery,
  solvent loss, lean-solvent loading, regeneration target, or a gas-ratio
  target;
- one bounded manipulated variable with an engineering reason;
- a sensitivity or monotonicity check when the relationship is not obvious;
- exported residual and Vary evidence from the accepted run.

If the Design Spec drives the manipulated variable to a bound or makes the
tower fail, keep the converged previous block and classify the spec as a
formulation or feasibility issue. Do not hide the failure by replacing the tower
with `SEP`.

### Duty-Specific Starting Patterns

- Low-temperature methanol wash or solvent absorption: start from a rigorous
  absorber/wash tower with cold lean solvent at the top and gas at the bottom;
  first vary solvent rate, solvent temperature, stages, and pressure. Add
  regeneration as a separate rigorous tower island after the absorber baseline
  is stable.
- Azeotropic or extractive distillation: first justify entrainer or solvent,
  property method, and VLE/LLE support; start directly from a rigorous main
  tower with solvent/entrainer feed, then add recovery/regeneration and recycle.
- Solvent regeneration or stripping: start from the rich-solvent feed and a
  rigorous stripper/regeneration tower; first vary heat duty or boilup,
  pressure, and product draw, then add a Design Spec for lean-solvent quality
  or solvent loss.
- Three-phase or VLL towers: start with the rigorous three-phase/decanter
  configuration and LLE-supported property method; define the second liquid
  phase by source-backed key-component behavior, not by stream name.

## Evidence To Keep

- `DSTWU` skip reason and selected separation method.
- The island feed export and the full-flow stream it came from.
- Property-method decision and missing-parameter audit.
- Cards for every retained tower block.
- Markdown sidecar notes for every generated tower step, including optimization
  method and core data.
- Convergence status and control-panel warnings/errors.
- Product purity, recovery, solvent loss, and energy duty where relevant.
- Sensitivity/Column Analysis/NQ evidence when applicable.
- Final block name and exact reason it was selected for full-flow connection.

## Hard Warnings

- Do not replace a special separation with `SEP`, `SEP2`, or `SEPARATOR` when
  the project requires a physical separation unit.
- Do not tune property methods or tower specs to hide a property-data gap.
- Do not overwrite prior optimization blocks; retained steps are part of the
  audit evidence.
- Do not automatically "fix" an absorber or stripper vapor feed written at
  `NSTAGE + 1`. In old-style RadFrac decks this may be the bottom vapor
  feed/port required when there is no reboiler or bottom heat input. Check the
  source/reference deck and RadFrac error text first, then record the decision
  in the tower sidecar.
- Do not import example values from Sun Lanyi cases or older Aspen files unless
  the current project source independently provides the same value, unit, and
  basis.

## Tower Sidecar Markdown Template

Create or update this Markdown note immediately after each tower block is
created, copied, run, or rejected. Use one file per tower step or one grouped
system file with one subsection per retained block. Missing values must be
written as `not yet exported` or `not applicable`; do not leave silent blanks.

```markdown
# <project>-<equipment> / <tower-block-id>

## Generation Source
- Aspen island file:
- Full-flow source feed / frozen feed export:
- Copied from block:
- Separation method:
- Property-method gate:
- DSTWU route: `DSTWU` / `DSTWU-SKIP`, with reason:

## Optimization Action
- Step type: `DSTWU`, `RIG-INIT`, `RIG-FEED`, `RIG-SENS`, `RIG-ANALYSIS`, or `RIG-SPEC`
- Variables changed:
- Variables deliberately fixed:
- Tool used: manual card edit / Column Analysis / Sensitivity / Design Spec / Calculator / Optimization
- Why this step was needed:

## Core Inputs
- Stages or packing height:
- Feed stage(s):
- Solvent or entrainer stage(s):
- Pressure path and pressure drop:
- Reflux / boilup / heat duty / condenser-reboiler mode:
- Solvent or entrainer flow and temperature:
- Product draw locations and rates:
- Design Spec target and Vary variable with bounds:

## Core Outputs
- Run status and control-panel status:
- Product purity:
- Key-component recovery or split:
- Solvent or entrainer loss:
- Top/bottom/side stream rates:
- Condenser/reboiler duty:
- Temperature profile sanity:
- Pressure-drop sanity:
- Warnings or errors:

## Decision
- Status: `accepted`, `diagnostic`, `rejected`, `blocked`, or `provisional`
- Reason:
- Final full-flow tower IDs covered:
- Grouping reason, if grouped with other towers:

## Next Step
- Next block to create:
- Specific target for the next step:
- Stop condition:
```
