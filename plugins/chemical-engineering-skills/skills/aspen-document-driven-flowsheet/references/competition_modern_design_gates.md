# Competition Modern Design Gates

Use this reference when a chemical-design-competition project, scoring rubric,
modern design method review, reactor optimization, or process-design taskbook is
part of the source basis. Rubric deductions are hard gates unless the user
explicitly defers that design scope.

## Source Map

| Source | Use For | Authority Limits |
| --- | --- | --- |
| `modern-design-rubric` | Simulation, reactor, separation, heat-integration, and equipment-design scoring gates | Converts deductions into review gates. Default simulation precision is `0.0001`; `0.001` is already a deduction. Heat-network items may be deferred only when the active scope excludes heat-network design. |
| `competition-taskbook` | Required deliverables, source-file availability, clean production, green/low-carbon, safety, economics, PFD/PID, material and heat balance | Defines submission expectations. It intentionally leaves raw-material specs, product slate, and plant scale for the team to justify from resource/market planning. |
| `reactor-ga-python-note` | RPLUG variables, Python-Aspen loop, objective functions, multi-objective optimization pattern | Method template only. Example numerical bounds are not authority because the note states some are arbitrary. |
| `process-engineering-practice` | Industrial-design reasoning, limiting-case calculations, economic screening, design-problem framing | Scan/OCR source. Use as engineering heuristics unless exact pages are visually checked; never promote OCR numbers directly. |

Supplemental-folder anchors and clean filename aliases may include:

- `现代设计方法.pdf`
- `化工设计竞赛任务书.pdf`
- `使用遗传算法与python对反应器优化.pdf`
- `化工过程工程工业实践.pdf`

Only the reusable method gates and failure patterns from supplemental files
belong in the skill. Project-specific rates, capacities, reaction targets, and
column specs still require a unit/card ledger before they are written to Aspen.

- `现代设计方法.pdf` p1-p7: Aspen simulation, reactor-rate, reactor-source,
  reactor-optimization, separation-optimization, and heat-network/detail-exchanger
  deduction gates. Treat deduction items as hard review gates for the active
  scope.
- `化工设计竞赛任务书.pdf` p4: submit simulation/optimization source files that
  open and run in the corresponding professional software.
- `使用遗传算法与python对反应器优化.pdf` p1-p16: external Python/GA can vary
  temperature, reactor length, diameter, pressure, and feed flow. The note's
  example numerical bounds are not transferable evidence because the note
  explicitly says some bounds were arbitrary; reuse the method pattern, not its
  numbers.
  Its useful reactor-optimization lesson is the progression from a single
  product-flow objective to a weighted or constrained score that also penalizes
  temperature, pressure, and feed use. For competition flowsheets, extend that
  score with hard constraints for product purity, selectivity, recycle quality,
  purge/vent load, and downstream separator feasibility before using GA results.
- `化工过程工程工业实践.pdf`: if plain text extraction fails, use rendered pages
  and OCR as method context. Promote its themes (problem framing, limiting
  calculations, economic feedback, data-quality review), not unchecked OCR
  numbers.

## Engineering-Practice Nodes

- `problem-definition`: before optimizing, state the real decision question.
  Reject work that answers a different question, such as maximizing one stream
  while ignoring product slate, recycle burden, or downstream separation.
- `bounding-calculation`: before broad Aspen sweeps, do a limiting-case material
  balance, conversion/selectivity estimate, or equipment-capacity estimate to
  narrow the search space.
- `data-quality`: treat old books, OCR tables, and example notebooks as search
  cues. Promote only visually checked, cited data with units.
- `reactor-network-selection`: compare CSTR, CSTR series, recycle reactor, and
  plug-flow/tubular candidates when conversion or selectivity is the blocker.
  Judge by conversion, selectivity, recycle load, heat removal, safety, and cost.
- `pre-framework-reactor-targets`: before building the process framework for a
  selected route, search current documents plus broad external industrial,
  literature, patent, or public-project anchors for approximate conversion and
  selectivity windows for every reactor. Use the windows to size and connect the
  first framework; do not leave each reactor's conversion as an unnamed knob.
- `reactor-column-coupling`: do not optimize a reactor without checking the
  separation train it feeds; reactor outlet composition sets column load, and
  column recycle quality changes reactor economics.
- `economic-sensitivity`: identify variables that materially move economics or
  hard gates. Do not over-tune insensitive parameters just because a solver can.
- `stage-gate-economics`: after each major design stage, ask whether the next
  modeling effort is justified by the expected economic or hard-gate benefit.
  Stop or narrow computation when the design question can be answered by a
  limiting calculation.

## Score-Driven Hard Gates Before Heat Network

- Consistency gate: major raw-material specs, product specs, main unit
  equipment, recycle streams, and utility specs must match the design report and
  latest Aspen exports. Each mismatch is a scoring deduction and a failed
  delivery gate.
- Simulation gate: full-flow or section models must run at the Aspen default
  convergence precision `0.0001` whenever possible. In the cited rubric,
  setting precision to `0.001` is already a deduction, and setting it above
  `0.001` is a larger deduction. Record run status, control-panel
  errors/warnings, block CSV, stream CSV, and exported after-run input. Do not
  promote a strict case with any actual simulation error or warning; explaining
  the cause is not an exemption. Use the central complete source-bound Summary
  and raw-history gate. Any explicitly relaxed case and its descendants remain
  audit-only and learning-ineligible.
- Taskbook basis gate: because the taskbook leaves raw materials, product
  structure/specs, and production scale open, do not treat the taskbook as a
  process recipe. Require market/resource/economic justification plus a
  unit/card ledger before capacity, product specs, or feed composition enter
  Aspen.
- Source-file delivery gate: any simulation, optimization, equipment-design,
  HAZOP, energy-integration, 3D-layout, economic-analysis, PFD/PID, or drawing
  work done in professional software needs the corresponding source files in
  the package, and those files must open/run in the software used. PDF/PNG
  exports are evidence views, not source-file substitutes.
- Recycle gate: recycle streams must be real topology, not seed-only or
  terminal recovery names. Partial recycle disconnection is a hard issue even if
  the model converges.
- Reactor-rate gate: at least one reactor operation must use a rate, equilibrium,
  or rapid-rate model with sourced parameters and correct units; when more
  kinetic evidence exists, non-rate checkout reactors are not final.
- Reactor-source gate: kinetic parameters may come from published data or
  justified chemical-reaction-engineering estimates. Every parameter needs source
  units, conversion, Aspen card, and exported-card evidence.
- Reactor-optimization gate: at least one reactor needs documented structure and
  operation optimization. For `RPLUG`, include length, diameter, tube count or
  equivalent geometry, `L/D`, residence time or space velocity, temperature,
  pressure, feed ratio/concentration, and bounds.
- Reactor optimization evidence must be generated as a construction gate. A
  final-looking case that merely reports a manually selected reactor parameter
  after the fact does not satisfy the optimization gate; retain the Sensitivity,
  Design Spec, Optimization, Regression, or auditable external-loop record that
  produced or bracketed the chosen parameter.
- Reactor-conversion acceptance gate: after the framework runs, each reactor's
  key-reactant conversion must be calculated from latest stream results and
  compared with the pre-framework target ledger. This is the primary check
  before capacity or feed/product yield is interpreted.
- Separation-rigor gate: separation columns should use rigorous/equilibrium-stage
  or rate-based models with a justified property method. Shortcut towers fail
  unless explicitly kept as provisional.
- Separation-optimization gate: at least one column or equivalent separator needs
  parameter optimization evidence: stages or packing height, feed stage,
  side-draw stage and rate when present, reflux ratio, gas/liquid ratio,
  extraction-solvent rate, or adsorption/desorption operating conditions.
- Material-balance gate: product rate, purity, recovery, purge, vent, wastewater,
  and valuable recovery boundaries must reconcile with total feed and reaction
  stoichiometry. A low product/feed ratio must be explained by conversion,
  selectivity, recycle inventory, sale/reuse boundaries, or purge losses.

## Deferred Heat-Network Gates

When the user says heat-network design has not started, do not block the current
reactor/separation flow repair on these items. Keep them as deferred gates and do
not claim they are complete:

- process heat-integration and pinch analysis;
- process-to-process heat exchanger network application;
- heat-network alternatives, composite curves, pinch temperature/economic trade;
- detailed design of at least two heat exchangers;
- exchanger turbulence, fouling resistance, area, pressure drop, and load
  performance checks.
- detailed tower/exchanger mechanical-process checks that belong to the later
  equipment-design package;
- 3D layout, plan/elevation drawings, and AutoCAD-compatible drawing exports
  when layout work has not started.

Current-stage flowsheets may still use heaters/coolers for temperature control
and utility duties, but report them as pre-heat-network placeholders unless
process-to-process exchanger design has been performed.

If the user only defers heat-network optimization, keep the boundary narrow:
defer pinch/composite-curve/network-optimization claims, but do not silently
defer reactor kinetics, separator rigor, default-precision clean-run evidence,
utility setup, process-stream HEATX evidence when claimed, segmented source
models, reactor/separator optimization, or the separate requirement for detailed
design of at least two heat exchangers.

## RPLUG And Design-Spec Route

Use this route when product output is too low, conversion looks weak, or the user
asks for plug-flow reactor sizing:

Before any new framework or sweep, write a reactor target or optimization
scorecard. It must name the source target window, current or assumed
conversion/selectivity, limiting material balance, manipulated variables,
physical bounds, Aspen built-in tool sequence, downstream hard gates, and
economic stop condition. If this scorecard is absent, pause the framework/sweep
and build it first.

1. Audit the current case before changing it: total fresh feed, recycle feed,
   reactor inlet/outlet component flows, product outputs, recovery/sale streams,
   purges, vents, and wastewater.
2. Compute conversion and selectivity around each reactor from stream CSV after
   the framework run. Identify whether low product comes from a missed reactor
   target, wrong selectivity, separation loss, or product routed to
   recovery/sale boundaries.
3. If a rate reactor has only `RCSTR` sizing and the chemistry supports flow
   reaction, build an `RPLUG` probe or branch. Keep reaction set and units
   unchanged until the unit/card ledger is verified.
4. Add `CALCULATOR` only for auditable derived values that should update inside
   Aspen, such as product draw from feed inventory, split fractions from recovery
   targets, or residence-time indicators. Export and audit the cards before
   treating the result as tool evidence.
5. Run `SENSITIVITY` on physically meaningful variables first: length, diameter,
   tube count/equivalent area, residence time, temperature, pressure, and feed
   ratio. Promote only windows that keep downstream product, recycle, pressure,
   phase, and terminal gates valid.
6. Use `DESIGN-SPEC` for scalar targets such as conversion, product mass flow,
   reactor outlet temperature, or key impurity, with length or residence time as
   the manipulated variable when that is the actual design variable. Do not claim
   a reactor Design Spec unless the exported Aspen input preserves the cards.
   If the syntax is not proven, use Sensitivity or an external bisection as an
   equivalent targeting method and record that limitation.
7. Use `OPTIMIZATION` or an external Python/GA loop only after the model is
   stable, variable bounds are sourced, failed runs are trapped, and the
   objective includes product, selectivity, utility/equipment cost, safety, and
   downstream separation constraints.

## Python Or External GA Guardrails

- External GA is a search wrapper, not design evidence by itself.
- Capture Aspen convergence status, errors, warnings, changed inputs, output
  metrics, and failed-run handling for every evaluated point.
- Record objective-function units and weighting or use a Pareto/constraint
  formulation. Do not use arbitrary weights as evidence.
- Do not optimize only target product flow. Penalize or constrain temperature,
  pressure, feed consumption, selectivity loss, purge loss, utility load,
  pressure equipment, and downstream separator feasibility.
- Numerical ranges copied from examples are not valid bounds unless the current
  source documents or equipment design justify them.
- When an example optimization maximizes only one product stream, add hard
  constraints or penalties for product purity, selectivity, recycle quality,
  purge/vent/recovery loads, pressure and temperature limits, and downstream
  separator feasibility before treating the result as design evidence.
- Learn from the reactor-GA note's two-stage objective pattern: first prove the
  Aspen-Python loop with a simple product-flow objective; then replace it with a
  process score such as product component mass minus penalties for reactor
  severity, pressure, fresh-feed use, selectivity loss, recycle impurity,
  purge/vent/recovery load, and failed downstream blocks. A single product-flow
  maximum is a debugging target, not a design target.
- For coupled reaction-separation networks, never let a GA individual win only
  by raising reactor severity. Penalize safety/selectivity risk, byproduct
  formation, product impurity, fixed-draw infeasibility, recycle impurity,
  organic purge, vent gas, and any failed hard gate.

## Retrieval Chain Hooks

These are routing hooks for `knowledge_graph.md`, not a real graph database:

- `competition-modern-design`: load this file for simulation, kinetics,
  reactor optimization, separation optimization, material balance, and deferred
  heat-network scoring gates.
- `competition-taskbook`: load this file before accepting capacity, product
  specs, source-file delivery, safety, green/low-carbon, economics, and
  professional-software package claims.
- `engineering-practice-framing`: start with problem definition, limiting
  calculation, data-quality review, and economic sensitivity before broad
  Aspen sweeps.
- `reactor-optimization`: route through `SENSITIVITY` -> `DESIGN-SPEC` ->
  `OPTIMIZATION` -> external GA only after topology, units, and feasible
  windows are proven.
