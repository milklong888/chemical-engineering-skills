# Aspen Heat-Pump Distillation Integration

Use this reference when a project asks to add, evaluate, audit, or package heat
pump distillation, mechanical vapor recompression, VRC/MVR, heat-integrated
column overhead compression, or a compressor on a tower overhead stream.

This is an integration workflow, not a value source. Do not copy pressures,
efficiencies, duties, savings, stream IDs, or temperature approaches from old
cases. Derive every value from the current column, source ledger, and exported
Aspen evidence.

## Position In The Workflow

Heat-pump distillation is a second-layer energy option. It starts only after a
conventional or otherwise rigorous base tower has passed material gates.

```text
accepted base RadFrac
  -> base duty and temperature evidence
  -> pressure-ratio / temperature-lift screen
  -> VRC topology candidate
  -> compressor phase gate
  -> product/recycle hard-gate rerun
  -> energy-accounting classification
  -> supplement, rejected option, or final linked heat-pump design
```

Do not use a heat-pump branch to hide a bad base tower, failed product purity,
wrong recycle route, missing pressure equipment, missing inhibitor/additive, or
unresolved property-method support.

## Three Integration Levels

Classify the branch before making claims.

### Level 1: Runnable VRC Supplement

Use this when the goal is to show a heat-pump/VRC branch in Aspen and prove the
phase/topology can run.

Typical topology:

```text
tower overhead vapor
  -> optional suction superheater
  -> compressor
  -> cooler or condenser / exchanger
  -> flash or reflux drum
  -> pump/valve as needed
  -> reflux and distillate/recycle split
```

Evidence:

- compressor block status is clean;
- no wet-compression or liquid-phase compressor error remains;
- visible overhead cooler/drum/reflux path is retained;
- product purity, capacity, recycle quality, no-SEP, additives, and pressure
  gates still pass.

Claim boundary:

- call it a runnable supplement or exploration;
- do not claim main-column utility savings if the original RadFrac still keeps
  its internal condenser/reboiler duties.

### Level 2: Partial Heat-Integration Branch

Use this when compressed overhead is connected to a real external HeatX or
thermal target but does not fully replace the column internal duty.

Evidence:

- heat-source and heat-sink streams have a positive approach;
- HeatX mode/specification is complete;
- auxiliary heater/cooler duties are reported;
- product gates still pass.

Claim boundary:

- credit only the external heat actually transferred and audited;
- do not subtract unreplaced RadFrac internal duties.

### Level 3: Final Countable Heat-Pump Design

Use this only when the heat-pump loop actually replaces, links, or balances the
column condenser/reboiler duty in the same accepted run.

Minimum evidence:

- internal condenser/reboiler duty is removed, externally linked, or explicitly
  balanced by equivalent energy streams and auxiliary trim blocks;
- compressed vapor supplies the intended reboiler or another column's duty;
- auxiliary reboiler, auxiliary condenser, compressor work, pumps, and letdown
  devices are all in the energy audit;
- final hard gates and open-run delivery gates pass.

Only this level can support a final heat-pump utility-saving claim.

## Screening

Screen before running a long full-flow candidate.

Record:

- base overhead stream temperature, pressure, phase, molar/mass flow, and
  composition;
- base top and bottom temperatures;
- base condenser and reboiler duties;
- candidate compressor discharge pressures or pressure ratios;
- estimated discharge temperatures;
- approach to the target reboiler/heat sink;
- estimated compressor work and electric-to-heat accounting basis.

Reject or defer candidates when:

- discharge temperature does not clear the heat sink by a positive engineering
  approach;
- pressure ratio is excessive for the expected savings;
- relative volatility/product purity is likely damaged by the pressure shift;
- compressor feed is not vapor-rich;
- the required heat integration would break a source-required reflux/drum path.

## Aspen Topology Rules

Keep pressure changes in pressure equipment:

- gas pressure rise: `COMPR`;
- liquid pressure rise: `PUMP`;
- letdown: `VALVE` or a documented pressure boundary;
- thermal-only conditioning: `HEATER` or `HEATX`, with pressure changes
  explicitly justified and not hidden.

For a Level 1 supplement, a stable first topology is:

```text
OVHD -> SHP? -> KHP -> EHP -> VHP -> PHP? -> split/reflux/product
```

Use short Aspen IDs. Keep the original source-required cooler/drum/reflux route
visible unless the project authority approves replacing it with an equivalent
external heat-pump loop.

When compressor discharge pressure changes, propagate compatible pressures to
the downstream cooler/condenser and flash/reflux drum, then add a pump/valve to
return to the downstream pressure boundary.

## Compressor Phase Gate

Direct saturated overhead compression often fails because the compression path
crosses into a two-phase region.

Do this first:

```text
check overhead vapor fraction / dew margin
screen discharge pressure
if near-saturated, add a small justified suction superheater
run and inspect compressor block status and error text
```

Do not use `VALID PHASES` or two/three-phase compressor settings merely to make
a wet-compression warning disappear. Treat liquid-phase-at-outlet/intermediate
messages as topology failures unless the upstream source explicitly accepts a
two-phase compression model.

## Energy Accounting

Keep these buckets separate:

```text
base case:
  condenser duty
  reboiler duty
  product/recycle gates

heat-pump case:
  unreplaced internal condenser/reboiler duties
  external HeatX/cooler/heater duties
  compressor brake power / WNET
  pump power
  auxiliary reboiler/condenser trim
  electric-to-heat conversion factor, if used
```

If internal RadFrac duties remain, write:

```text
accepted as runnable heat-pump/VRC supplement;
not accepted as final heat-duty credit
```

If a final countable branch is achieved, compare:

```text
base external utilities
vs
heat-pump auxiliary heat + auxiliary cooling + compressor electric work
```

State whether electric work is reported directly or converted to heat-equivalent
with a project-approved factor.

## Hard-Gate Rerun

After adding VRC/heat-pump equipment, rerun the project hard gates. At minimum,
check:

- no forbidden `SEP/SEP2/SEPARATOR` final blocks;
- tower overhead phase and visible cooler/drum/reflux route;
- compressor, superheater, condenser/HeatX, flash/drum, pump/valve statuses;
- product purity and capacity;
- recycle impurity/loss;
- additive/inhibitor/solvent route preservation;
- RYield/kinetics warnings not reintroduced;
- pressure devices and HeatX inputs complete;
- APW/BKP reopen evidence if delivered as a supplement.

## Operation Contract

Send this contract to `aspen-plus-operations`:

```text
Operation goal: add or audit heat-pump/VRC branch for <tower>
Authority artifact: base tower branch and change-offset table
Inputs and source units: base top/bottom temperatures, duties, overhead phase/flow
Property-method gate: accepted for base tower and compression/condensation range
Allowed changes: add compressor, optional suction superheater, cooler/HeatX,
flash/drum, pump/valve, auxiliary trim; preserve source route hard gates
Required evidence: after-run INP/BKP, stream CSV, block CSV, compressor phase,
energy table, hard-gate audit, delivery reopen audit if packaged
Stop condition: promoted supplement/final branch, rejected candidate, or named
blocking phase/property/convergence issue
```

## Reporting Language

Use precise language:

- "VRC supplement" when the branch runs but does not replace internal duty.
- "partial heat integration" when an external heat exchange is proven but the
  internal duty remains partly active.
- "heat-pump utility saving" only for a same-run linked/balanced branch whose
  internal duty replacement and auxiliary duties are audited.

