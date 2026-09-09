# Tower optimization — on-demand method and hydraulics

Apply the chemical expert's STRICT_ACCEPTANCE_AND_LEARNING.md. Old project
numbers and default pressure/reflux assumptions have no global authority.
The private predecessor and historical case scripts are not distributed.

## Network Position

Upstream authority is `aspen-document-driven-flowsheet`: it supplies the source
route, change-offset status, frozen feed, separation target ledger,
property-method row, and promotion gate. This skill owns the tower-island
workflow and returns tower sidecars, exported evidence, and reconnect gates to
the process authority layer. Use `aspen-plus-operations` only for mechanical
Aspen create/set/run/export actions. Use `aspen-pressure-pfd-delivery` when the
tower result needs pressure, vacuum, heat-exchanger, or PFD/package audit.

## First Gate

Before editing Aspen files, read the active project change-offset table and the
latest tower sidecar/stepbook for the same duty. If a user-qualified local textbook graph exists under `{CHEM_WORKSPACE}`, use
its actual unknowns/special-column routing. No source book or private graph is
bundled; examples give methods, not values.

Never use a rejected branch or lecture-case number as a default. Record a new
change-offset row before mutating `.inp` scripts or Aspen cases.

Freeze the tower property method before the shortcut or rigorous tower exists.
Use the real tower service: component family, pressure/temperature window,
expected VLE/LLE/VLL behavior, polarity/non-ideality, solvent/entrainer or
azeotrope needs, binary-parameter support, and transport-property needs for
hydraulics. After the property row is accepted, do not change it to rescue
reflux, stages, hydraulic warnings, or product purity unless the upstream
process authority records a change-offset row and reruns affected tower
evidence.

## Choose The Route

Ordinary distillation may use `DSTWU` only after freezing:

- feed stream/export;
- separation duty and product specs;
- LK/HK and key recoveries;
- pressure path and allowed pressure drop;
- final Design Spec target and Vary bounds.

Special towers skip `DSTWU` and start rigorous:

- azeotropic or extractive distillation;
- absorber, stripper, solvent wash, regeneration;
- VLL/three-phase or reactive distillation;
- any duty without meaningful light/heavy keys.

For special towers, write a `DSTWU-SKIP` reason plus property-method and phase
support before creating `RadFrac`.

## Standard Sequence

Preserve each step as a new block, copied case, or sidecar entry:

```text
TARGET-FREEZE
  -> DSTWU or DSTWU-SKIP + RIG-INIT
  -> RIG-FEED
  -> RIG-SENS or RIG-ANALYSIS
  -> RIG-SPEC
  -> reconnect to full flow
  -> pressure/vacuum/HX audit
  -> dynamic run evidence
```

For ordinary towers, derive the shortcut initial specification and bounds from
current feed, keys, recoveries and source method. Do not assign a taught reflux
multiplier without that task's authority. Negative Aspen shortcut notation is
an input convention, not a negative physical reflux ratio; verify its meaning
against the current help/export. Convert to a converged rigorous baseline,
then add the authorized live specifications.

When the course/user specifies the taught `DUSTWU/DSTWU -> RadFrac` sequence,
do not replace it with a direct RadFrac sweep. Preserve the exact step chain:

```text
DSTWU with the source-authorized reflux or stage specification
  -> read minimum reflux/stages and actual stages
  -> run a stage-number sensitivity around the current shortcut actual-stage region
  -> choose the first plateau/sensitive stage where RR no longer drops much
  -> rerun DSTWU with NSTAGE fixed to that stage to get the exact RR and D/F
  -> build the first RadFrac from the exact DSTWU values
  -> extract RadFrac liquid composition profiles
  -> move the feed stage to the tray/packing theoretical stage whose liquid
     composition is closest to the feed composition
  -> rerun RadFrac and only then tune D:F, RR, and any allowed feed-scale
     design variable against product/recycle/capacity gates
```

When the user, taskbook, or course workflow says a tower target must be met by
`Design Spec`/`设计规定`, do not promote a fixed `D:F`/`B:F`/reflux sweep as the
formal result. Use the sweep only to bracket a feasible window and provide
initial values, then add/export a live tower-internal RadFrac `SPEC/VARY` pair
or a documented Aspen Design Spec that manipulates the tower variable in the
same run. For recycle impurity targets, `D:F` or distillate split is normally
the manipulated variable; `RR` may be held or separately tuned to protect
separation sharpness. Promotion evidence must include the exported `SPEC` and
`VARY` cards, the target stream composition from the same after-run, and a
statement that the manipulated variable is not merely hand-entered from an
offline scan.

If the final model needs parallel towers for attributable equipment limits,
derive the feed/reflux distribution from the current duties and design basis.
An equal split with identical cards is only a candidate for demonstrably
symmetric trains. Separately justify shared or independent condenser/drum,
reflux and bottoms systems; their arrangement is not a universal case default.
Check the parallel topology explicitly; a passing material balance from a
single tower is not evidence for the parallel equipment design.

For special towers, first find a favorable rigorous window by stages, feed
stage, draw rate, reflux/boilup, solvent or entrainer rate, recycle split, and
pressure. Add Design Specs after the response is feasible and bounded.

## Design Spec Discipline

Design Specs must control a real target: purity, recovery, solvent/entrainer
loss, recycle quality, product ratio, or product split. Each spec needs one
bounded manipulated input with an engineering reason.

Use tower-internal RadFrac `SPEC/VARY` when the target and manipulated variable
both belong to one tower. Pair `SPEC n` and `VARY n` by the same index, bracket
the feasible range first, then promote the live spec only after the same run
exports the cards and the downstream product/recycle gates pass.

Prefer `MOLE-RECOV` or `MASS-RECOV` when the target must scale with feed
perturbations, such as final recovery from a changing recycle/feed mix. Prefer
`MASS-FRAC` or `MOLE-FRAC` for product purity or impurity leakage when the
target stream has meaningful flow. Use absolute `MOLE-FLOW` or `MASS-FLOW` only
for a source-given draw, a wetness/minimum-flow guard, or a diagnostic fixed-draw
candidate; do not promote it as a feed-scale-independent final recovery control.

Keep external flowsheet Design Specs for cross-tower, cross-stream, merged
stream, or overall-loop targets. Do not force those targets into a RadFrac
internal spec. Respect the requested precision exactly: a "three nines" purity
target means `0.999`, not an unrecorded six-nines tightening.

If equality specs conflict, inspect degrees of freedom, physical feasibility
and the current authority. Do not silently drop one required equality or relax
precision. Keep an infeasible point diagnostic; a change needs explicit current
project authority and any relaxation is case-only/no-learning.

## Pressure And Equipment Audit

Before promotion:

- every retained RadFrac has a pressure path and tower pressure drop;
- tower and exchanger pressure drops come from the current source/method and
  same-duty hydraulic evidence, with units and basis; no project ratio is a
  universal default;
- liquid pressure rise uses pumps, gas pressure rise uses compressors, letdown
  uses valves;
- vacuum service has explicit pressure devices or a documented boundary;
- distinguish actual liquid/gas service and phase changes; no shared liquid-HX
  pressure fraction is imposed on unrelated gas/reaction service;
- no orphan vacuum streams or stale pressure placeholders remain.

## Energy-Saving Tower Supplements

After the rigorous base tower passes product/recycle gates, optional energy
optimization may branch into low-reflux operation, pressure changes,
multi-effect coupling, or heat-pump/VRC integration. Keep these as tower
supplements until they pass the upstream full-flow gates.

For heat-pump/VRC replacement work, route through
`aspen-heat-pump-distillation-replacement` before asking the operation layer to
add compressors or external HeatX blocks. Use the older document-driven
heat-pump integration reference only for background energy-integration
classification when the task is not an empty-column replacement.
Classify the result as:

- runnable VRC supplement;
- partial heat integration;
- final countable heat-pump design.

Do not count heat-pump utility savings from a branch where the RadFrac internal
condenser/reboiler duties remain active and unlinked. Preserve the base tower
and compare duties only from same-run exported evidence.

## Packed-Tower Hydraulic Predesign Gate

When a taskbook, buyer, report, or final claim asks for tower hydraulic or
equipment design, do not invent a tower standard and do not claim hydraulics
from a material-balance-only RadFrac. Freeze the current source text first:

- tower type, top/bottom pressure or pressure path, condenser/drum behavior;
- required product/recycle specifications;
- any grading gates for HETP, bed height, redistributors, flooding/capacity
  factor, tray liquid level, or pressure drop;
- whether the task needs preliminary course design or a vendor-grade internals
  result.

Use the local knowledge graph operation path before web tutorials when present:
RadFrac strict tower -> Sizing and Rating/Pack Sizing or Column Analysis ->
hydraulic result pages. Lecture cases provide paths and diagnostics only; they
do not provide reusable HETP, flooding factors, diameters, pressure drops, or
packing types.

Generic hydraulic acceptance ladder:

```text
accepted same-version RadFrac operating point
  -> verify property-method/transport-property row
  -> generate column hydraulic data or export RadFrac hydraulic profiles
  -> define tray or packing section geometry/internals
  -> inspect Hydraulic Plots, warning status, pressure profile, and Column
     Hydraulic Results or project-local packed/tray ledger
  -> record diameter, section range, pressure drop, flooding or capacity
     approach, weeping/entrainment/downcomer/packing warnings, and source gates
  -> rerun/reopen/export if hydraulics or internals cards are kept in Aspen
  -> reconnect only after product, pressure, recycle, and delivery gates still
     pass
```

Do not treat a `Flow Rate` plot, vapor/liquid load table, or old tower profile
as final hydraulic evidence. A hydraulic claim needs generated hydraulic data
and an explicit result page/ledger from the same final operating point.

Separate hydraulic evidence levels before making a delivery claim:

- `L0 material`: RadFrac/DSTWU converges and products pass; no hydraulic claim.
- `L1 source-static`: taskbook tower type, diameter, bed height,
  redistributor, tray liquid-level or packing capacity/flood gates pass.
- `L2 course-predesign`: same-run RadFrac profiles plus transparent HETP,
  packing, pressure-drop and capacity assumptions in a manual/script ledger.
- `L3 software-rating`: Aspen Column Analysis/Column Internals or equivalent
  tray/packing rating from the same final operating point, with pressure drop,
  capacity/flooding and warnings checked.
- `L4 vendor/mechanical`: vendor internals package plus mechanical/nozzle/shell
  checks. Do not promote L2 as L3 or L3 as L4.

For a physically credible packed-column predesign, also check practical
operability beyond the pass/fail number: property and transport-property basis,
section and total pressure drop, distributor and redistributor locations,
liquid turndown/loading, fouling or contaminated-liquid service, HETP source,
support grids, collectors, hold-downs, feed devices, nozzles, and the expected
high/low-load envelope. A warning-free material simulation is only the minimum
screen; it is not proof that the packed tower is an engineering-grade design.
Local standards can supply method routes, but formal diameter, percent
capacity, flooding, pressure drop, HETP and internals claims require Aspen
Column Internals/Column Analysis, vendor data, or an explicitly labelled
course-design assumption.

For a packed-column course-design precheck, it is acceptable to combine
exported RadFrac profiles with explicit assumptions, but label the evidence
class correctly:

- `source_direct`: taskbook gates such as max bed height and allowed capacity
  factor range;
- `aspen_export`: same-version RadFrac temperatures, pressures, and internal
  vapor/liquid profiles;
- `manual_assumption`: HETP, packing family, flooding F-factor, nozzle
  velocities, and liquid density when not exported;
- `software_boundary`: Aspen Column Internals/vendor packing data, guaranteed
  flooding, pressure drop, HETP, and final internals dimensions.

For source-authorized packed-tower preliminary design, the method sequence is:

```text
accepted full-flow RadFrac BKP
  -> reopen the exact delivery APW/BKP and rerun cleanly
  -> extract stage T/P and vapor/liquid molar + mass profiles
  -> verify named stage-profile fields, units and identity; do not infer private binary labels from a plausible curve
  -> exclude condenser/reboiler from packed stages
  -> split beds by source max bed height
  -> size diameter at selected capacity fraction
  -> verify actual capacity factor range and bed-height gate
  -> write hydraulic JSON/CSV/MD ledger
  -> keep Column Internals/vendor guarantee as boundary
```

Hydraulic evidence must use the same operating point as the final promoted
case. If reflux ratio, distillate/feed ratio, feed scale, pressure network,
Column Internals cards, or recycle quality changes after a hydraulic ledger was
made, rerun the hydraulic extraction from the final APW/BKP after-run export.
Do not reuse a previous candidate's diameter/capacity factor as final tower
equipment evidence.

For an Aspen built-in Column Internals supplement, create the internals object
from exported/importable RadFrac cards rather than by writing result nodes:

```text
RadFrac block
  -> SUBOBJECTS INTERNALS = CS-...
  -> COL-CONFIG ... CA-CONFIG=INT-1
  -> INTERNALS CS-* STAGE1/STAGE2 INTERNAL=PACKING SIZING=RATING DIAM=...
  -> PACK-RATE rows
  -> reopen/run/export and project hard-gate audit
```

If a vendor/packing text string fails import or `HYDRAULIC=YES` gives a
nonzero tower block status, keep that branch as diagnostic. Promote only the
branch whose exported cards preserve the internals object and whose full-flow
product, pressure, recycle, inhibitor/additive, and run-integrity gates pass.
If `HYDRAULIC=YES` leaves a real warning, that candidate is diagnostic.
Do not disable required hydraulic calculations to manufacture clean acceptance.
A `HYDRAULIC=NO` material-simulation branch is admissible only when the current
stage contract independently permits manual preliminary hydraulics; retain its
same-operating-point calculation ledger and explicit software boundary. It
cannot satisfy a required Column Internals/rating/vendor gate. A user-approved
stage relaxation is case-only and excluded from learning with all descendants.

## Public Hydraulic Interface Boundary

The original single/parallel case scripts are not distributed. Their private
stream maps, operating values, taskbook gates and label-inference assumptions
cannot be made generic by renaming; no same-name placeholder is supplied.

Use current same-case named stage profiles with explicit units, geometry and
source-backed packing/tray limits. Column Internals/Column Analysis, vendor
data or an independently verified local calculation may close the applicable
evidence stage. Preserve source hashes, profile identity, equations, assumptions,
gate limits and result scope. This workflow does not claim numerical hydraulic
analysis has been performed.

Do not infer a result field from a temperature-looking curve or reuse another
case's binary label offsets. A wrong-profile calculation is invalid even if
the resulting geometry looks plausible.

For a clean material simulation with `HYDRAULIC=NO`, an oversized internals
diameter can make the packed-bed capacity factor fail low even though all
product gates pass. Size or revise `INTERNALS ... DIAM` from the exported vapor
profile so the whole packed bed capacity factor lies in the source/task range,
then rerun the Aspen case, hard gates, Control Panel/APW reopen checks, and
hydraulic extraction from that revised final operating point. Do not claim the
old oversized diameter merely because the Aspen block status is zero.

The inverse is also a failure: an undersized internals diameter can leave block
status zero while the packed-bed capacity factor or flood information is above
the source/task range. In that case, increase or split the tower diameter/duty,
rerun the full Aspen case, and regenerate the same-operating-point hydraulic
ledger. A material-simulation pass is not enough for tower equipment delivery.

Where a tower has a source-given diameter, flooding or packing constraint,
verify the exact final same-duty internals/hydraulic evidence. Packing names
and a material-balance pass do not prove capacity. Record all governing stages,
bed heights, redistributors and current high/low-load limits. Historical example geometry, packing and flooding values are neither included
nor available as default selectors.

For energy optimization, keep the product/recycle hard gates above the duty
objective. A low-reflux or pressure-change candidate is promotable only after
the same-version full-flow audit still passes capacity, purity, visible drum
topology, inhibitor/additive, no-SEP, and run-warning gates. Record the rejected
cases and the accepted operating point; do not let a hydraulic or duty
improvement overwrite a failed product spec.

For document-derived impurity targets, translate wording into the current actual
stream path. Check relevant overhead/condenser/drum/product or bottoms/downstream
feed locations, not a convenient empty or post-processed stream. Require
meaningful product flow/composition and the source target; no private chemical
stream map is supplied.

For tight recycle impurities, use a bounded three-variable polish only after
the full-flow seed is pressure/topology clean:

```text
accepted pressure-clean full flow
  -> vary tower D:F / distillate split for recycle impurity
  -> vary reflux ratio for product/recycle tradeoff
  -> apply small equal-ratio fresh-feed scale only to restore capacity
  -> rerun full-flow hard gates and APW reopen gates
```

Do not promote the lowest-utility point if it fails any document or buyer
purity/recycle specification. A newer buyer specification must be recorded with source, units and basis in
the project change-offset table before mutation; do not transfer old recycle
impurity numbers.

For reduced-stage redesign after a conservative RadFrac has already passed,
rerun the shortcut-to-rigorous chain under the current property method and
current impurity redline. Do not assume the old final stage count or old Rmin
still controls after property, recycle, or product-spec changes. A useful
pattern is:

```text
current accepted full-flow feed boundary
  -> DSTWU with current-source initialization and evidence-derived feasible bounds
  -> fixed-stage DSTWU around the plateau/sensitive stage
  -> low-stage RadFrac with tower-internal SPEC/VARY still active
  -> reject low-RR RadFrac cases that pass recycle impurity but fail final
     product purity
  -> restore product purity by a bounded RR or D:F polish, not by changing the
     property method
  -> apply only a small equal-ratio feed/steam scale if capacity drifts
  -> rerun full-flow hard gates, delivery APW reopen, and hydraulics from that
     final operating point
```

Near a capacity limit, compare same-operating-basis accepted/rejected points
using source-backed hydraulics. Any calibration from a reported flooding ratio
is case-specific and must state its assumptions; it is not a universal capacity
correlation or vendor guarantee. Record the controlling stage and uncertainty.

## Reconnect Gate

A tower island is not promoted until the same-version full-flow candidate has:

- reopened/runnable `.bkp` or generated Aspen archive;
- exported `after_run.inp`, stream CSV, block/status CSV, and summary JSON;
- strict clean block/spec/calculator/run evidence; a quarantined status cannot
  pass the reconnect acceptance gate;
- product purity/capacity and recycle metrics;
- pressure, vacuum, and heat-exchanger pressure-drop evidence.

Current project-specific production, purity, residual SEP, heat-reporting and
recycle requirements are read from that project's latest authority, never from
a named historical case in the global skill.

