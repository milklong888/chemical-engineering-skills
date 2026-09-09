# Aspen Built-In Solve And Fit Tools

Use this reference when an Aspen task starts to look like manual parameter
hunting. The purpose is to reduce trial count while leaving an exported,
auditable trail. Built-in tools do not fix wrong chemistry, topology, property
method, pressure equipment, or source-unit conversion.

## Tool Selection

- `CALCULATOR`: Use for derived variables, stream-dependent estimates,
  stoichiometric links, reaction-parameter relationships, feed-forward
  calculations, inventory-based product draws, and recycle-quality indicators
  that must update inside Aspen. Audit `DEFINE`, `READ-VARS`, `WRITE-VARS`,
  `EXECUTE BEFORE/AFTER`, and convergence order.
- `SENSITIVITY`: Use before dense sweeps. Map feasibility windows for physical
  variables such as reactor length, reactor volume, residence time, temperature,
  pressure, feed ratio, reflux, stages, side draw, solvent rate, purge, flash
  temperature, or condenser duty. Promote only settings that pass the full
  downstream hard gate, not only the local metric.
- `DESIGN-SPEC`: Use when one scalar target can be met by one meaningful
  manipulated variable, such as product concentration by reflux or draw,
  reactor conversion by length or volume, recycle impurity by purge, or outlet
  temperature by duty. Set physical lower/upper bounds.
- `OPTIMIZATION`: Use after a feasible model exists and the goal is an objective
  with constraints, such as minimum utility at product/recycle specs or maximum
  recovery under purity and pressure limits. Do not use it to fix wrong topology.
- `REGRESSION` / Data-Fit: Use for kinetic or model-parameter fitting from
  primary conversion, selectivity, concentration, time, or reactor-profile data.
  Vary only identifiable parameters and report fitted values, bounds, residuals,
  and validity range.
- Property Data Regression: Use for NRTL/UNIQUAC/EOS/BIP fitting from VLE, LLE,
  pure-property, or mixture-property data. ThermoML/NIST files are regression
  candidates, not Aspen-ready BIP cards until regressed, residual-checked, and
  exported.
- External Python/GA/NSGA-II loop: Use only after the Aspen base case converges,
  variable bounds are sourced, failed runs are captured, and Aspen
  `SENSITIVITY`/`DESIGN-SPEC`/`OPTIMIZATION` cannot cover the search need.
  Treat external optimizers as search aids; they are not promotion evidence
  unless each candidate records inputs, convergence status, warnings/errors,
  objective components, and downstream hard-gate results. Promote an external
  result only after the selected point is rerun inside Aspen, exported, and
  audited against the same gates as a built-in solve/fit result.

## Common Trigger Graph

Use this as a symptom-to-tool map. Aspen's sequential modular tools interact
with convergence order: Design Specs introduce manipulated variables into
convergence, and Calculator blocks import/export flowsheet variables at a
defined execution point. Therefore every trigger below also needs exported-card
and same-run evidence.

| Symptom Or Intent | First Tool To Consider | Manipulated Or Written Variable | Required Audit |
| --- | --- | --- | --- |
| A product draw must track available key-component feed inventory | `CALCULATOR`, then optional `DESIGN-SPEC` | Draw estimate, recovery target, or bounded initial spec | Read feed stream, write draw/target before the column, prove draw is below inventory |
| Tower target is a concentration, mass fraction, mole fraction, or recovery | `SENSITIVITY` then `DESIGN-SPEC` | Reflux, distillate/bottoms/side draw, solvent rate, or feed stage | Feasible bracket, concentration residual, current-feed inventory, clean column status |
| Reactor must hit conversion/selectivity by changing equipment or operation | `SENSITIVITY` then `DESIGN-SPEC` or `OPTIMIZATION` | Length, volume, residence time, temperature, pressure, feed ratio, catalyst amount, CSTR count | Target ledger, physical bounds, kinetic-unit audit, downstream gates |
| Recycle impurity, purge, or solvent return quality controls full-flow closure | `CALCULATOR` for indicators; `DESIGN-SPEC` for scalar target | Purge fraction, recycle split, solvent makeup, regeneration draw | Loop topology, contaminant balance, pressure/phase compatibility, terminal gates |
| Heat duty, outlet temperature, or heat-integration match is the scalar target | `DESIGN-SPEC`; `OPTIMIZATION` for utility objective | Heater/HEATX duty, approach, stream split, compressor ratio | Energy balance, pressure equipment, utility feasibility, downstream product gates |
| Feed ratio, stoichiometric ratio, or makeup rate depends on live stream results | `CALCULATOR` | Feed, makeup, split, or stream-dependent set point | `READ-VARS`/`WRITE-VARS`, execution before consuming block, no circular stale value |
| A user or rubric asks for optimum yield, energy, solvent loss, or economics | `OPTIMIZATION` after feasible model | Real design/operation variables with constraints | Objective components, bounds, active constraints, no broken product/recycle gates |
| Kinetic, property, or BIP parameters must be fitted from data | Regression/Data-Fit or Property Data Regression | Identifiable model parameters | Primary data, units, weights, residuals, exported fitted cards, validity range |
| Manual sweeps are repeating without moving the hard gate | `SENSITIVITY` or blocker reclassification | One or two physical variables only | Stop condition, bad-run matrix, branch status, next missing island or property check |

Do not use Calculator to hide an impossible separation, and do not use Design
Spec to vary a variable already fixed by another card. When the trigger is only
"make the number look right," first rebuild the source target, feed inventory,
and physical degree of freedom.

## Default Sequence

1. Fix topology, components, property method, pressure equipment, and unit/card
   conversion before using any built-in solver.
   Property method means module-specific, not merely a global Aspen default:
   identify the reactor, gas-cleanup, solvent, hydrocarbon, azeotropic,
   extractive, aqueous, and compression/recycle sections that see different
   component families, phase behavior, pressure/temperature windows, or
   nonideality. For each changed module, run a small property or island probe
   before reconnecting it, then rerun the full case and bind the final evidence
   to that same run family.
2. For reactor retuning or low product/feed ratio, write a scorecard before the
   next run: target conversion/selectivity window, limiting material balance,
   current conversion, variables and bounds, built-in tool route, downstream
   gates, and economic stop.
3. If the scorecard implies unexpected reactor dimensions or space times, insert
   a kinetics-unit audit before stretching length, volume, or residence time.
4. Use `CALCULATOR` only for auditable relationships that must update with the
   run. Keep the calculation small and name every read/write variable.
5. Run coarse `SENSITIVITY` to bracket feasibility and discover broken
   formulations before Design Spec.
6. Use `DESIGN-SPEC` for a bounded scalar target only after feasibility is
   bracketed and the manipulated variable is a real design or operating degree
   of freedom.
7. Use `OPTIMIZATION` only after the model converges near a feasible region.
8. Use `REGRESSION` when the unknown is a model parameter and primary data exist.
9. Use external search only for stable, bounded, multi-variable problems whose
   objective includes product, selectivity, energy, pressure, feed use, and
   downstream separation constraints.
10. Export `*_after_run.inp`, block status, stream results, and any tool result
    tables or residual reports before promotion.
11. For reactor conversion retuning, make solve/fit evidence a promotion gate. A
    single back-substituted point without a retained, completed Sensitivity,
    Design Spec, Optimization, Regression, or equivalent auditable tool record
    remains diagnostic even if conversion and product purity pass.

## Reactor Replacement Chain

Use this chain whenever a yield or stoichiometric reactor is being replaced by a
kinetic reactor, or when reactor conversion is the named blocker:

1. Look up a target conversion/selectivity window from the current documents and
   rough external industrial, literature, patent, or public-project anchors.
2. Build or preserve a yield/stoichiometric scaffold only as a topology and
   material-balance baseline. Label it provisional.
3. Audit the original full-flow case: total feed, reactor inlet/outlet flows,
   per-reactor conversion, selectivity if available, product rates, recovery or
   sale streams, purges, vents, and wastewater.
4. Replace the reactor as an isolated kinetic island first. Verify reaction-set
   binding, phase, sizing basis, temperature/pressure, and exported cards.
5. Use `SENSITIVITY` before `DESIGN-SPEC` to vary a physical parameter such as
   length, volume, residence time, temperature, pressure, feed ratio, or catalyst
   amount. If the source supports CSTR behavior better than plug flow, use CSTR
   volume or a CSTR-series variable and explain the selection basis.
6. Back-substitute the kinetic island into the full flow without deleting the
   solve/fit cards or result evidence.
7. Recompute downstream gates from the same run family: product purity and rate,
   recycle quality, pressure, temperature, terminal boundaries, warnings,
   block status, and material balance.
8. Keep the solve/fit tool in the promoted full-flow case. If Aspen cannot retain
   the intended Design Spec syntax, retain the completed Sensitivity or
   equivalent audited external bracketing evidence and state the limitation.

## Calculator Plus Design Spec Gate

Promotion requires a dependency chain, not just a clean-looking product stream:

- Calculator purpose and formulas.
- Calculator read variables, write variables, execution point, and convergence
  order.
- Design Spec target, target units, manipulated variable, bounds, and independent
  degree of freedom.
- Proof the manipulated variable is not also frozen by a Calculator, fixed draw,
  or stale template value.
- Exported `CALCULATOR`, `DESIGN-SPEC`, `VARY`, `READ-VARS`, `WRITE-VARS`, and
  `EXECUTE` cards.
- Final residual/status plus latest stream and block evidence.
- Downstream gates after the Design Spec run, not from an older branch.

A pure-looking product from a nonconverged block or stale Calculator value fails
the solve/fit gate.

If the target is a minimum such as "at least this purity" and the stream already
exceeds it, an equality Design Spec can create a false failure by pushing the
manipulated variable outside physical bounds. Do not delete a live Calculator
that computes a real feed-inventory draw or makeup just to make the Design Spec
disappear. Instead, prove whether the Calculator is needed, remove duplicate
control of the same variable, and promote only with an explicit external
minimum-purity audit plus clean block, stream, terminal, and temperature gates.

## Distillation And Concentration Targets

- For high-purity or concentration targets, use true staged continuation:
  promote each tighter target only from the latest clean after-run.
- Before optimizing a tower or special separation, freeze its local property
  method and property-data status for the actual feed family. Check VLE/LLE,
  azeotrope or entrainer behavior, relative volatility, solubility, and binary
  parameter warnings in an isolated column or property probe. If the local
  method changes, all old reflux, duty, draw, feed-stage, solvent-rate, and
  Design Spec evidence is diagnostic until the changed island and the final full
  flow are rerun.
- Formulate tower specs around component concentration, recovery, reflux, boilup,
  product draw, bottoms draw, side draw, solvent rate, or feed stage as the
  physical separation requires.
- Bound product draws by latest feed inventory. Fixed product-rate values from
  older islands are not reusable after reactor, recycle, or solvent-loop changes.
- If a lower target converges but the accepted target fails after true staging,
  stop blind reflux/iteration sweeps and repair property method, BIP data,
  solvent/entrainer mapping, feed-stage placement, or manipulated-variable
  formulation.
- A tower that meets a concentration number while drying up the feed, starving a
  downstream column, or carrying block warnings is diagnostic only.

## Guardrails

- A built-in tool result is not evidence unless the exported input preserves the
  intended cards.
- Do not fit more free parameters than the data can identify.
- Do not manipulate kinetic constants, split fractions, or product rates that
  should be fixed by equipment design unless that is the actual design variable.
- Reject a Design Spec or Optimization solution that sits on an absurd bound or
  breaks recycle/product hard gates.
- Treat Calculator dependencies as part of convergence topology; a wrong
  execution point can create stale or circular values.
- Keep source-unit and Aspen-card ledgers for all fitted or calculated values.
- For `RPLUG` or tube-reactor optimization, do not vary length, diameter, tube
  count, `L/D`, volume, or residence time as anonymous knobs. Record physical
  meaning, equipment bounds, source basis, and exported input card.
- Before promoting a long `RPLUG` or reactor Design Spec, verify exported
  kinetic-card units and defaults. Ledger units and Aspen card units may use
  different bases.
- If a source does not authorize the chosen reactor type, label the change as a
  reactor-network candidate or engineering branch. Compare plausible alternatives
  such as CSTR, CSTR series, recycle reactor, or plug-flow before claiming final
  structure.
- Keep side-reaction and selectivity metrics visible, but do not invent hard
  selectivity thresholds. Promote thresholds only when documents, cited data,
  safety constraints, or economic limits define them.
- If meeting conversion alone destroys selectivity, product purity, recycle
  quality, terminal handling, or block status, promote the failure as evidence
  and change the target formulation rather than increasing bounds.

## Local Syntax Templates

Use these as audit templates, not copy-paste Aspen input. Aspen card syntax
varies by version and export style; build the tool in Aspen or through COM,
export the case, then verify the exported cards.

Calculator:

- Useful cards: `CALCULATOR <id>`, `DEFINE`, `READ-VARS`, `WRITE-VARS`,
  `EXECUTE BEFORE BLOCK <id>`, `EXECUTE AFTER BLOCK <id>`, explicit
  convergence order.
- Use as a small no-op probe if syntax is uncertain before applying the
  Calculator to the authority case.

Sensitivity:

- Target: map a feasible window, not force a final answer.
- Manipulated variables: one or two physical variables.
- Bounds: broad enough to bracket the target but capped by feed inventory,
  pressure limits, thermal stability, utility feasibility, and equipment reality.
- Evidence: exported `SENSITIVITY` cards, result table, block status, stream
  results, and downstream hard-gate audit.

Design Spec:

- Target: one scalar residual such as product mass fraction, recovery, recycle
  impurity, reactor conversion, outlet concentration, outlet temperature, or duty
  match.
- Vary: one meaningful variable such as reflux, distillate rate, bottoms rate,
  side draw, solvent rate, heat duty, purge, split fraction, reactor length,
  reactor volume, residence time, or feed ratio.
- Evidence: exported `DESIGN-SPEC`/`VARY` cards, final residual, block status,
  and unchanged downstream hard gates.

RPLUG or reactor probe:

- Target: prove geometry and reaction semantics before full-flow promotion.
- Variables: length, diameter, tube count/equivalent area, residence time,
  temperature profile, pressure, phase, and reaction set.
- Evidence: exported block cards, geometry cards, active reaction set, block
  status, conversion/selectivity calculation, and downstream gates.

Optimization:

- Objective: utility, solvent loss, compressor work, product recovery, or an
  economic proxy.
- Constraints: product purity, conversion, selectivity, recycle quality,
  pressure, temperature, material balance, terminal handling, and equipment
  limits.
- Evidence: exported `OPTIMIZATION` cards, objective value, active constraints,
  variable bounds, and proof that the optimum did not break base hard gates.

Regression/Data-Fit:

- Data: source, units, temperature, pressure, composition basis, and uncertainty
  where available.
- Fit: varied parameters, bounds, weighting, objective residual, and validity
  range.
- Promotion: export fitted cards, rerun the relevant island, and compare product
  and recycle gates before accepting parameters.

## External Targeting Acceptance

External search, Python automation, genetic algorithms, or spreadsheet
optimizers may substitute for a built-in solve/fit trail only when the record
contains:

- Why Aspen built-ins were insufficient or impractical for the selected search.
- Sourced lower/upper bounds and physical meaning for each candidate input.
- Candidate inputs, convergence status, warnings/errors, failed-run handling,
  and objective components for the accepted point and rejected neighbors.
- Product, conversion, selectivity, pressure, recycle, terminal-boundary, and
  material-balance gates evaluated on the same candidate.
- Final Aspen rerun, exported input, block status, stream results, and gate
  audit after applying the selected point.

Without the final Aspen rerun/export/audit, the external result is only a
screening hint.

## Audit Snippets

```powershell
rg -n "^\s*(CALCULATOR|DESIGN-SPEC|SENSITIVITY|OPTIMIZATION|REGRESSION|DATA-SET|PROFILE-DATA)\b|READ-VARS|WRITE-VARS|EXECUTE BEFORE|EXECUTE AFTER|VARY " .\*_after_run.inp

rg -n "REGRESSION|PROFILE-DATA|DATA-SET|LIMITS|RESID|VARY " .\*.inp .\*.out .\*.sum .\*.md .\*.json
```

When reporting a built-in solve/fit result, include target, manipulated
variables or varied parameters, bounds, source data, result status, residuals
when applicable, exported-card evidence, and downstream gate status.
