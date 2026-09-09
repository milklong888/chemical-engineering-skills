# Reactor Separation Solve/Fit Patterns

Use this anonymized pattern card when a flowsheet has acceptable-looking product
purity but reactor conversion, tower concentration, product/feed yield, or
separation topology is still suspect. The card contains reusable workflow
lessons only. It intentionally excludes source-project files, stream names,
local paths, version branches, product rates, and chemistry-specific values.

## Do Not Use As Authority

- Do not copy reactor types, conversions, dimensions, column specs, split
  fractions, solvent choices, property methods, product specs, or rates.
- Do not treat a historical branch label as a gate. Gates come from the current
  documents, rubric, user request, and latest exported Aspen evidence.
- Do not promote a back-substituted parameter value unless the solve/fit tool or
  equivalent audited bracketing evidence is retained with the promoted case.

## Reactor Replacement Pattern

1. Define the reactor target ledger before framework construction.
   For each reactor, list key reactant, target conversion window, selectivity or
   safety constraints, provisional reactor type, phase, and source basis.
2. Build a yield or stoichiometric scaffold only to prove topology, feed basis,
   pressure islands, and rough material balance. Label it provisional.
3. Audit the original full-flow scaffold before replacing reactors:
   total feed, reactor inlet/outlet component flows, per-reactor conversion,
   selectivity if available, product flows, recycle returns, sale/reuse streams,
   purges, vents, wastewater, warnings, and failed blocks.
4. Replace one reactor at a time in an island. Verify component mapping,
   reaction-set binding, kinetic-card units, phase, temperature/pressure,
   sizing basis, and exported cards.
5. Choose the reactor form from evidence. A CSTR, CSTR series, recycle reactor,
   or RPLUG/PFR can all be defensible, but the choice must be tied to current
   kinetics, mixing, heat-removal, catalyst, pressure-drop, or document evidence.
6. Use `SENSITIVITY` before `DESIGN-SPEC` to bracket a physical parameter:
   length, volume, residence time, temperature, pressure, feed ratio, catalyst
   amount, or stage/reactor count.
7. If `DESIGN-SPEC` is used, vary the actual design or operating degree of
   freedom and set physical bounds. Conversion alone is not enough; selectivity,
   product purity, recycle quality, pressure, temperature, terminal boundaries,
   and warnings must still pass.
8. Back-substitute the kinetic island into the full-flow case and keep the
   solve/fit evidence. Recompute all downstream gates from that same run family.

## Calculator And Design Spec Dependency Pattern

Before promotion, write and verify this chain:

- Calculator read variables, write variables, formula meaning, execution point,
  and convergence order.
- Design Spec target, residual basis, manipulated variable, bounds, and
  independent degree of freedom.
- Proof the manipulated variable is not also fixed by a stale product draw,
  Calculator write, template constant, or external script.
- When a Calculator writes the live inventory draw needed for a separator, do
  not remove it merely because a Design Spec fails. Test whether the failure is
  duplicate control, equality forcing of a minimum target, or wrong separation
  family.
- Exported `CALCULATOR`, `READ-VARS`, `WRITE-VARS`, `EXECUTE`,
  `DESIGN-SPEC`, and `VARY` cards.
- Final residual/status, warning/error count, block status, and stream results.
- Downstream product, recycle, terminal-boundary, pressure, and material-balance
  gates after the Design Spec run.

A product stream that is pure only because a Calculator did not update, a block
failed, or a fixed draw starved the tower is failed evidence.

### Stale Or Locked Manipulated Variable Audit

- Compare the manipulated variable and every Calculator write target before the
  run, after the run, and in exported stream/block tables. A value that stays at
  an old constant while the feed changes is stale until proven otherwise.
- Search the latest exported input and scripts for duplicate control of the
  same variable: `VARY`, fixed product draw, fixed split, `WRITE-VARS`, template
  constants, external loop assignments, and restart initial values.
- Verify `EXECUTE BEFORE/AFTER` order against the block that consumes the value.
  A Calculator that writes after the consuming block, or writes before its read
  variables exist, is a setup blocker.
- Bind product purity, block status, residual, material balance, and downstream
  gates to the same run family as the Calculator and Design Spec evidence. Do
  not combine a clean product stream from one branch with a solve/fit card from
  another.
- If a minimum target is already exceeded and an equality Design Spec goes
  out-of-bounds, prefer an audited external `>=` gate over forcing an artificial
  exact equality. This is acceptable only when block status, terminal boundaries,
  recycle quality, and temperature/phase sanity all pass in the same run.

## Tower Concentration And Special-Separation Pattern

- Treat property-method selection as part of the separation design, not as a
  background setting. Before a tower, absorber, low-temperature solvent wash,
  azeotropic/extractive section, or recovery island is optimized, list the local
  feed components, expected phases, pressure/temperature range, nonideality
  drivers, selected property method, and BIP/data status. Verify the local
  method with a property probe or island run before trusting reflux, stage,
  solvent, regeneration, or draw optimization.
- If the requirement is concentration, write the tower spec as concentration,
  mass fraction, mole fraction, or recovery of the key component as specified by
  the current source. Do not substitute a product-flow target unless the source
  actually defines product flow as the spec.
- Bound distillate, bottoms, side draw, reflux, solvent rate, and feed stage by
  the latest feed inventory and component distribution. Reactor or recycle
  changes invalidate old fixed draws.
- Use true staged continuation for tight targets: promote each tighter target
  only from the latest clean after-run.
- If clean staged targets stall, diagnose whether the blocker is property
  method, BIP/LLE/VLE data, solvent or entrainer selection, feed-stage mapping,
  degree-of-freedom formulation, phase behavior, or wrong separation family.
- If the property method or binary-data branch changes after an optimization
  run, discard the old tower/recycle numbers as promotion evidence. Rebuild the
  island evidence under the new method, then reconnect and rerun the full
  flowsheet before claiming product purity, recovery, recycle quality, or zero
  warnings.
- If ordinary distillation cannot physically support the split, load
  `aspen_distillation_patterns.md` and screen pressure-swing, azeotropic,
  extractive, extraction/decanting, absorption, evaporation/vacuum, or other
  documented special-separation routes before forcing more reflux.
- For water/organic dewatering or other likely hetero splits, treat a converged
  ordinary column with nonphysical outlet temperature or phase behavior as
  diagnostic. Screen flash/decanter/LLE islands and explicitly condition
  treatment-boundary outlets before final promotion.
- After three focused same-topology conventional-column failures, and after
  checking syntax, feed inventory, degrees of freedom, fixed draws, Calculator
  order, property warnings, and key-component routing, mark the blocker as
  `separation-method/property-chain` instead of continuing blind reflux or
  stage sweeps.

## Separation-Retarget Pattern After Reactor Changes

- Reactor severity changes column feed inventory. Before retuning columns,
  compute key-component flow entering each column and compare it to every fixed
  product or recovery target.
- Retarget separation with a small option table:
  current feed inventory, feasible product draw range, property-method risk,
  likely special-separation need, manipulated variables, and downstream gates.
- Score candidates by component mass and purity, not total stream mass.
- If a light-end or flash adjustment recovers one component but destroys another
  product or solvent loop, classify it as diagnostic and rebuild the separation
  island.
- Do not use direct recycle or sale/reuse splits to mask failed light-end,
  solvent, product-polishing, or treatment separations.

## Product/Feed And Capacity Sanity Pattern

- Compute product/feed yield from limiting raw-material conversion, selectivity,
  main-product component mass, recycle quality, purge/vent loss, sale/reuse
  boundaries, and wastewater/treatment streams.
- If the user explicitly relaxes capacity or allows feed-rate adjustment after
  a purity target is reached, demote capacity to a scale/reference gate only
  after updating the audit schema. Do not use that relaxation to skip
  separation duties: every physical separator still needs a per-unit target
  check, and every valuable raw-material recycle loop needs an exported path
  check in the same accepted run.
- Keep source values distinct from audit thresholds. When a source names only
  component destinations but not internal recovery percentages, any temporary
  per-separator recovery threshold is an audit acceptance rule, not a sourced
  Aspen card value or literature/design datum.
- Do not infer total process yield from a co-product ratio.
- If product/feed yield is low, identify which bucket owns the loss:
  reactor conversion, selectivity, fixed downstream draws, failed separation,
  recycle impurity, purge/vent/sale boundaries, or product routed to treatment.
- If key-reactant single-pass conversion matches the sourced industrial window,
  do not call it the root cause of a poor fresh-feed/product ratio until recycle
  quality and all terminal valuable-material buckets have been quantified.
- When single-pass conversion is acceptable but overall fresh-feed utilization is
  low, look for recoverable unreacted reactants before enlarging or overdriving
  the reactor. Build a small reaction-separation-recycle option table covering
  flash/condensation, stripping or absorption of dissolved reactants, membrane
  or adsorption recovery, inert purge, pressure/phase compatibility, recycle
  compressor or pump duty, and total conversion from fresh feed.
- For gas-liquid post-reactor systems, check whether valuable gases remain
  dissolved in the product condensate. If they do, a stripper or absorber can be
  the utilization-improving unit that raises overall conversion while leaving
  the literature single-pass conversion nearly unchanged.
- Search broad industrial/literature/patent/public-project anchors before
  deciding that a low capacity is acceptable or that a reactor must be larger.

## Diagnostic Wording

When reporting a blocker, be sharp:

- "Setup problem": wrong card syntax, stale Calculator, missing exported tool
  evidence, frozen product draw, wrong units, or hidden pressure change.
- "Separation method problem": ordinary column or flash cannot perform the
  required split; route to special separation and property-data checks.
- "Reaction problem": key-reactant conversion or selectivity misses the target
  ledger even before downstream separations.
- "Integration problem": reactor island passes but full-flow product, recycle,
  terminal, pressure, or material-balance gates fail after reconnection.

Only one of these may be the primary blocker in the authority note; list
secondary issues separately.
