# Aspen Convergence And Trial Patterns

Use this reference when an Aspen model fails to run, a recycle will not close, a
separator or column is unstable, or local sweeps are not moving the named hard
gate.

## Contents

- Convergence adjustment playbook
- Branch control
- Cheap probes before expensive runs
- Sweep design
- Recycle startup
- Separator replacement
- Kinetic upgrade
- Product and intermediate gates

## Convergence Adjustment Playbook

When convergence is difficult, adjust in this order:

1. Preserve evidence first.
   Copy or archive the last useful `.bkp`, `.apwz`, exported `.inp`, block CSV,
   stream CSV, and run summary before changing a fragile case. Split automation
   into import, roundtrip export, run, after-run export, and backup-reopen checks.

2. Fix topology before numbers.
   Check that streams are connected to the right block, recycle outlets return
   to the intended upstream mixer, pressure rises have pumps or compressors, and
   no product or waste outlet is unintentionally routed into raw-material feed.

3. Stabilize the skeleton.
   If the rigorous model will not start, fall back to the yield-reactor plus
   shortcut-separator scaffold, close recycle there, and export tear estimates.
   Use those estimates to cold-start the strict model.

4. Ramp recycle closure.
   Close one recycle at a time. Start with realistic tear estimates, modest purge
   fractions, conservative separator recoveries, and nonzero key-component
   recycle flow. After the loop runs, reduce artificial purges or seeds only if
   key-component return remains physically meaningful.

5. Ramp kinetic severity.
   Prove each kinetic reactor independently, then reconnect it at mild severity.
   Increase reactor volume, residence time, temperature, catalyst loading,
   feed ratio, or pressure gradually. Do not tune `PRE-EXP`, `ACT-ENERGY`,
   reaction orders, or denominator terms to force convergence unless values are
   fitted from documented primary data and labeled.

6. Use built-in solvers before dense hand sweeps.
   Run a small Sensitivity map first. Use Design Spec for scalar targets with
   meaningful manipulated variables and bounds. Use Optimization only after the
   case runs near the feasible region. Use Regression/Data-Fit for unknown model
   parameters from data. Promote only after exported input, block status, stream
   CSV, and residual/status reports support the result.

7. Replace separators by physical target.
   Treat `SEP`/`SEP2` as a placeholder for a separation target, not a unit
   choice. Write the target first: key split, outlet destination,
   recovery/purity, phase basis, pressure level, recycle boundary, and the
   manipulated variable that a Design Spec or Calculator should adjust. A
   RadFrac is not automatically better than a flash, condenser, decanter,
   absorber, evaporator, low-temperature methanol wash, adsorption bed, or
   membrane. Start with the simplest physical equipment that expresses the
   target, then add product purity specs only after the target component leaves
   by the intended outlet.

8. Diagnose separator failure from streams.
   For dry columns, zero-feed, no-phase-splitting, impossible product-rate,
   wrong-outlet, or binary-parameter warnings, inspect feed phase/composition,
   property method, pressure, and product spec feasibility before sweeping
   stages, reflux, or recovery.

9. Protect upstream reaction feed quality.
   Check contaminants that poison or contradict the upstream reaction section,
   especially product, water, heavy byproducts, oxidants, or phase-incompatible
   components. If a recycle contaminates the upstream reactor, keep it as a
   diagnostic side loop or add cleanup before promotion.

10. Stop blind sweeps.
    If repeated local changes do not move the named hard gate, stop sweeping.
    Update the authority note, write the current blocker matrix, and switch to
    the missing island, property-method check, source-data search, or topology
    correction that can actually change the gate.

11. Review call efficiency.
    After a difficult block is solved or abandoned, summarize which tool calls,
    probes, sidecars, or built-in Aspen tools moved the gate fastest. Convert the
    next similar task into a narrower queue: one cheap falsification probe, one
    candidate-option screen, one bounded solver setup, then promotion audit.

## Branch Control

- Keep a runnable baseline untouched. New trials write to
  `vNN_<purpose>_<key-settings>` directories or equivalent names.
- Keep one authority file that says `accepted`, `candidate`, `diagnostic`, or
  `rejected` for each branch.
- Promote the branch that satisfies the named hard gates, not the branch with
  the prettiest local metric.
- If a later trial breaks a named gate, keep it as negative evidence and return
  to the accepted baseline.
- Do not compare cases from different feed bases without recording the inlet
  basis difference.
- Preserve segmented models when they express the real process boundary better
  than a forced full loop. A connected full flowsheet is final only after
  boundary streams and side-line returns are meaningful.
- Do not overwrite a converged baseline with property-method, kinetic, or
  column-spec experiments.

## Cheap Probes Before Expensive Runs

- Before product polishing, collect compatible product-bearing streams into a
  common crude pool and calculate key-component inventory.
- Before building a full column, run a flash or binary/property probe to learn
  phase split, relative volatility, azeotrope risk, and outlet direction.
- Before reconnecting a recycle, test pressure, phase, target component fraction,
  product carryover, water, oxidant/reductant, heavy components, and total flow
  significance against the receiving feed.
- Before changing kinetic constants, run a micro-reactor probe with fixed feed to
  verify rate-card units, activation-energy basis, reaction order signs, and
  material change.
- Before sweeping product specs, compute available key-component inventory from
  the current feed stream. Reject distillate, bottoms, side-draw, or recovery
  specs that ask for more material than the feed contains.
- Before adding a pressure device, check stream phase.
- Before copying a kinetic reactor from another Aspen file, export the source
  input and verify component mapping, reaction-set binding, basis, catalyst
  quantity, reactor dimensions, and property method in a standalone probe.
- Before changing global property method, run a copy of the accepted case and
  compare import, block status, key separations, phase splits, and
  binary-parameter warnings.
- Before accepting a high-purity product, check every upstream separator in the
  product path for dry-column, flow-limit, impossible draw, or nonphysical
  condenser warnings.

## Sweep Design

- Decide whether Sensitivity, Design Spec, Optimization, Calculator, or
  Regression can express the same question before writing a custom sweep.
- Sweep coarse first, then refine: use three to five spaced values before dense
  grids.
- Sweep one variable class at a time: reactor severity, separator pressure,
  condenser temperature, reflux/stages, purge fraction, or recycle split.
- Include a rollback point in every sweep set.
- Record bad blocks, block messages, key outlet flow, target purity, recycle
  quality, and product capacity in every row.
- Stop a sweep early when all cases fail for the same structural reason.
- After three structurally identical failures, stop the sweep family and switch
  to property data, alternative separation type, topology, or source evidence.
- Add a negative-control case when possible.
- Treat mostly clean block status as suspect when the one bad block sits on the
  named hard-gate path.
- For Design Specs and Optimizations, start from a converged case and use bounds
  that reflect equipment or chemistry reality.
- For Regression/Data-Fit, include enough primary data to identify varied
  parameters. Report residuals and fitted parameter bounds.

## Recycle Startup

- Close the easiest recycle first: same phase, same or lower pressure, obvious
  key component, and small contaminant risk.
- Use scaffold-derived tear estimates for temperature, pressure, flow, and
  composition; do not cold-start a strict recycle with blank or pure-component
  guesses.
- Add a small purge when a loop accumulates inert, byproduct, solvent, or trace
  product and the document is silent. Label it as a closure assumption.
- After every reactor or separator change upstream of a recycle, rerun recycle
  quality before product polishing.
- A recycle with high target-component fraction can still fail if absolute
  return flow is trivial or contaminant flow changes the receiving reactor.
- Keep side-line resource loops outside the main raw-material recycle until they
  are proven safe and useful.
- Try Broyden-style tear methods and explicit iteration limits only after
  topology, pressure equipment, and initial estimates are reasonable.

## Separator Replacement

- Replace one shortcut separator boundary at a time and preserve the shortcut
  branch until the physical replacement passes.
- Match the first replacement to the actual physical split: flash for
  vapor-liquid, decanter/LLE for liquid-liquid, absorber for gas cleanup,
  evaporator/vacuum flash for concentration, RadFrac for volatility, membrane or
  PSA only when the source supports it.
- Do not use RadFrac as the default answer to every separator. If a flash or
  condenser proves split direction and gives a clean recycle seed, use it as the
  bridge or column initializer.
- If ordinary RadFrac behaves badly for high-purity product, deliberately test
  extraction/LLE, extractive distillation, azeotropic or entrainer-assisted
  distillation, pressure-swing, heat-pump distillation, absorber/stripper,
  evaporator/vacuum flash, membrane, or PSA.
- Keep entrainer and solvent loops inside the product-finishing island with their
  own purge and recovery checks. Raw-material recycle is a separate decision.
- For extractive distillation, the solvent-rich outlet must not stop at
  `REC`. Add a regeneration block, purge/makeup if needed, conditioning
  equipment, and a return stream to the extractive column before promotion.
- Pool compatible product-bearing or waste-recovery streams first, then polish
  the pooled material. Separate towers for every small dirty outlet are usually
  diagnostic only unless a safety, phase, or source constraint requires them.
- Treat no phase splitting, dry-column warnings, zero-flow outlets, or blank
  stream results as failed evidence even when the run returns.
- If a product or recycle outlet is zero, inspect upstream feed availability and
  product-rate specs before increasing stages or reflux.
- A retained shortcut is sometimes better than a fake rigorous block. Keep it
  only as a named placeholder with missing specs; do not mark separator-rigor
  passed.

## Kinetic Upgrade

- Convert yield/stoichiometric reactors to strict kinetics one reactor at a
  time.
- Keep checkout/apparent kinetics explicitly labeled until sourced constants,
  units, reaction orders, catalyst basis, and Aspen card meaning are verified.
- If conversion is too low, first check reactor volume/space-time units, feed
  concentration basis, temperature, pressure, catalyst amount, and phase behavior.
- If conversion is too high or destabilizes recycle, ramp severity down and
  inspect downstream separator loads before changing kinetic constants.
- After any kinetic change, compare fresh-feed draw, recycle flow, product flow,
  and major byproduct flow against the previous accepted case.
- Do not shrink or inflate kinetic constants only to make Aspen converge.
- When a source law is fluidized-bed, membrane, adsorption, or user-kinetics
  shaped, a simple `POWERLAW` may be only a checkout surrogate. Label it and keep
  the real implementation gate open.

## Product And Intermediate Gates

- Product-grade specs are final gates; intermediate cleanup specs are tied to
  downstream tolerance and recycle usefulness.
- Do not over-optimize intermediate purity if the receiving block can tolerate
  impurity and product/economic gates are unaffected.
- Do not under-check recycle contaminants that poison a reactor, create a wrong
  phase, or return product into raw-material feed.
- Separate `process gate passed` from `product finishing open` when the user
  named a narrower goal.
- Split boundary gates by function: product quality, raw-material recycle,
  VOC/tail-gas treatment, wastewater, heavy residue, solvent loop, and purge
  accumulation each need stream evidence.
- For every terminal output, decide one of: sale/product, raw-material recycle,
  solvent/entrainer return, reusable recovery feed, treatment/purge, vent, or
  wastewater. Unclassified terminal streams are failed topology, not open text.
- When source documents conflict on route or feed basis, lock the route boundary
  explicitly and keep alternate readings as open assumptions.
