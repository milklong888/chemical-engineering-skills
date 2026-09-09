# Aspen Flowsheet Knowledge Graph

Use this file as the retrieval-chain index for nontrivial Aspen Plus work. It is
not a graph database or a substitute for reading current source documents.
Current documents, rubrics, taskbooks, and user-named gates always outrank
historical cases and reusable patterns.

Load only the modules that match the active blocker. Never copy a case value,
stream name, project path, kinetic constant, column spec, pressure, or product
rate into a new model unless the current project documents independently
support it and the unit/card ledger verifies it.

## Node Map

| Node | Load When | Primary References | Related Checks |
| --- | --- | --- | --- |
| `document-evidence` | Extracting DOCX/PDF/process documents or deciding whether reactions, kinetics, specs, or constraints exist | `SKILL.md`, `aspen_audit_gates.md` | equations/XML/tables/captions/rendered pages, authority manifest |
| `unit-card-ledger` | Any number moves from document, literature, spreadsheet, script, case, or subagent into Aspen | `SKILL.md`, `aspen_audit_gates.md` | source units, conversion formula, Aspen basis, destination card meaning |
| `literature-parameter-audit` | Kinetic, equilibrium, adsorption, transport, catalyst, or property parameters come from papers, OCR, screenshots, translations, patents, secondary sources, or cited originals | `literature_parameter_extraction_audit.md`, `aspen_audit_gates.md` | source matrix, branch discipline, dimensional conversion, independent calculator/microprobe, release gate |
| `competition-modern-design` | A competition rubric, taskbook, source-file requirement, or scoring deduction controls the work | `competition_modern_design_gates.md`, `aspen_audit_gates.md`, `aspen_builtin_solve_fit_tools.md` | deductions as hard gates, default precision, source files, deferred heat-network scope |
| `engineering-practice-framing` | The design question, capacity, product slate, or economic boundary is unclear | `process_design_practice_patterns.md`, `competition_modern_design_gates.md` | problem definition, limiting estimate, external anchors, option screening |
| `bounded-estimate` | A feed/product/capacity/recovery number looks unreasonable or a sweep lacks a sanity check | `process_design_practice_patterns.md`, `aspen_audit_gates.md` | limiting material balance, conversion/selectivity envelope, purge/recycle loss |
| `experimental-data-audit` | OCR, literature, old tables, kinetic/VLE/LLE data, or example notebooks may be used | `process_design_practice_patterns.md`, `literature_parameter_extraction_audit.md`, `aspen_audit_gates.md` | data quality, units, applicability, visual verification |
| `from-zero-scaffold` | Building from documents or repairing an unreliable draft | `aspen_workflow_playbooks.md` | scaffold labels, recycle seeds, pressure islands, accepted authority |
| `kinetics` | Reactions, reactors, rate laws, catalyst basis, or missing constants drive the task | `literature_parameter_extraction_audit.md`, `aspen_workflow_playbooks.md`, `aspen_failure_patterns.md`, `aspen_builtin_solve_fit_tools.md` | PowerLaw/LHHW cards, real-kinetics gate, property/component identity |
| `reactor-target-planning` | A reaction system is selected, a framework is about to be built, or conversion/product-feed ratio is being tuned | `competition_modern_design_gates.md`, `aspen_builtin_solve_fit_tools.md`, `reactor_separation_solvefit_patterns.md` | pre-framework target ledger, external target windows, limiting balance, conversion/selectivity gates |
| `reactor-optimization` | Product output is low, conversion is weak, or reactor structure/operation must be optimized | `competition_modern_design_gates.md`, `aspen_builtin_solve_fit_tools.md`, `process_design_practice_patterns.md` | scorecard, physical variables, Sensitivity/Design Spec, downstream gates, economic stop |
| `kinetics-unit-audit` | Reactor size, residence time, RPLUG length, or conversion looks surprising | `aspen_failure_patterns.md`, `aspen_audit_gates.md`, `aspen_builtin_solve_fit_tools.md` | exported cards, POWERLAW units, activation-energy basis, micro-probes |
| `solve-fit` | Manual tuning, fitting, or targeting is growing costly | `aspen_builtin_solve_fit_tools.md`, `aspen_convergence_trials.md` | Calculator, Sensitivity, Design Spec, Optimization, Regression/Data-Fit |
| `calculator-trigger` | A live Aspen value must compute another set point, draw, makeup, feed ratio, purge estimate, or recycle-quality indicator | `aspen_builtin_solve_fit_tools.md`, `reactor_separation_solvefit_patterns.md` | import/export variables, execution point, stale/locked variable audit |
| `design-spec-trigger` | A scalar process target must be met by a real degree of freedom | `aspen_builtin_solve_fit_tools.md`, `aspen_audit_gates.md` | target/residual, manipulated variable, bounds, convergence block, same-run evidence |
| `separation-replacement` | Replacing `SEP`/`SEP2` or choosing physical separators, including difficult separations | `aspen_distillation_patterns.md`, `reactor_separation_solvefit_patterns.md`, `aspen_convergence_trials.md`, `aspen_failure_patterns.md` | separation target ledger, option table, phase behavior, intended outlets, Design Spec/Calculator variable, island proof |
| `separation-rigorous-optimization` | A rigorous/equilibrium/rate-based separation parameter must be optimized | `competition_modern_design_gates.md`, `aspen_distillation_patterns.md`, `aspen_builtin_solve_fit_tools.md` | property method, stages/packing, feed stage, side draw, reflux, solvent rate |
| `distillation` | Diagnosing columns, special distillation, extraction, solvent/entrainer loops, or `BATCHSEP` | `aspen_distillation_patterns.md`, `aspen_builtin_solve_fit_tools.md`, relevant `cases/` | feed inventory, product-rate bounds, property method, exported streams |
| `recycle` | Closing raw-material, solvent, product, treatment, or utility loops | `aspen_workflow_playbooks.md`, `aspen_convergence_trials.md`, `aspen_failure_patterns.md` | seed-vs-closed recycle, purge policy, pressure equipment, contaminants |
| `pressure-topology` | Pressure changes, compressors, pumps, valves, or `HEATER PRES=0` appear | `aspen_failure_patterns.md`, `aspen_audit_gates.md` | phase before pressure equipment, avoid hidden pressure rise |
| `thermo-property` | Phase split, VLE/LLE, polar/aqueous species, BIP gaps, or component aliases matter | `aspen_distillation_patterns.md`, `aspen_failure_patterns.md`, `aspen_builtin_solve_fit_tools.md` | property comparison, Data Regression, component identity |
| `convergence` | Runs fail, recycle diverges, columns retain warnings, sweeps stall, or a runnable case still has report errors/warnings | `aspen_convergence_trials.md`, `aspen_zero_warning_repair.md`, `aspen_builtin_solve_fit_tools.md` | topology before numbers, branch preservation, no-run syntax gate, Control Panel/history first, stop blind sweeps |
| `heat-integration-pinch` | Heat-network or pinch work starts, or completion is claimed | `competition_modern_design_gates.md`, `aspen_audit_gates.md` | pinch analysis, composite curves, HEN alternatives; deferred only by explicit scope |
| `equipment-detail-design` | Detailed exchanger/tower design is active or claimed complete | `competition_modern_design_gates.md`, `aspen_audit_gates.md` | hydraulics, flooding, HETP, exchanger area/fouling/dP |
| `layout-3d-design` | 3D layout, drawings, CAD-compatible files, or plant layout deliverables are active | `competition_modern_design_gates.md`, `aspen_delivery_evolution.md`, `aspen_audit_gates.md` | source files, drawing consistency, deferred scope |
| `audit-delivery` | Promoting a final case or writing reports/PDFs | `aspen_audit_gates.md`, `aspen_delivery_evolution.md` | latest exports, PDF text/render, single authority manifest |
| `portable-package` | User asks for reusable package, another-computer run, or production handoff | `aspen_delivery_evolution.md`, `aspen_audit_gates.md` | relative manifest, verifier scripts, portable commands |
| `execution-efficiency` | Tool calls, subagents, sweep families, or repeated trials are expanding | `aspen_workflow_playbooks.md`, `aspen_convergence_trials.md` | execution queue, sidecar evidence contracts, stop condition |
| `self-evolution` | A reusable failure pattern was proven by artifacts | `aspen_delivery_evolution.md` | evidence trail, candidate patch, no project-specific promotion |

## Mandatory Routing Patterns

- New project from documents: `document-evidence` -> `unit-card-ledger` ->
  `literature-parameter-audit` when literature parameters are involved ->
  `engineering-practice-framing` -> `reactor-target-planning` ->
  external industrial/literature/patent anchors -> `from-zero-scaffold` ->
  `kinetics` and `separation-replacement` -> `recycle` -> `audit-delivery`.
- Competition-scored repair before heat-network stage:
  `competition-modern-design` -> `engineering-practice-framing` ->
  `unit-card-ledger` -> `reactor-target-planning` ->
  `reactor-optimization` and `separation-rigorous-optimization` ->
  `recycle` -> `audit-delivery`. Mark heat-network, equipment-detail, and
  layout gates deferred only if the active scope explicitly excludes them.
- Low product/feed ratio or weak conversion after a framework run:
  `bounded-estimate` -> `reactor-target-planning` ->
  `reactor-optimization` -> `solve-fit` -> per-reactor conversion acceptance ->
  material-balance audit -> `separation-replacement` if losses occur after
  reaction. Do not begin another broad volume/length/product-draw sweep until
  the scorecard names targets, variables, bounds, Aspen tools, downstream gates,
  and economic stop.
- Reactor replacement: `reactor-target-planning` -> yield or stoichiometric
  scaffold -> original full-flow yield audit -> kinetic island replacement ->
  `solve-fit` on a physical reactor parameter -> full-flow back-substitution ->
  retained exported solve/fit evidence -> downstream gate audit. A
  back-substituted point without the retained tool record stays diagnostic.
- Product concentration or purity target in a tower: `distillation` ->
  `separation-rigorous-optimization` -> `solve-fit`. Use feed inventory and
  component concentration/recovery specs, not stale fixed product draws. If
  ordinary distillation cannot meet the target cleanly, route to special
  separation patterns before forcing more reflux.
- Calculator plus Design Spec branch: `solve-fit` -> dependency-chain audit ->
  final residual/status -> downstream gates. Promotion requires Calculator
  read/write variables, execution point, Design Spec target, manipulated
  variable, bounds, independent degree of freedom, exported cards, and latest
  stream/block evidence.
- Live set-point calculation: `calculator-trigger` -> `solve-fit` ->
  dependency-chain audit -> stale/locked variable audit -> downstream gates.
  Trigger examples include feed-inventory product draws, feed-forward ratios,
  solvent makeup, purge estimates, recycle-quality indicators, and live
  concentration or recovery targets.
- Scalar targeting: `design-spec-trigger` -> `solve-fit` -> Sensitivity bracket
  -> bounded Design Spec -> same-run downstream audit. Trigger examples include
  reactor conversion by length/volume/residence time, product concentration by
  reflux/draw/solvent rate, recycle impurity by purge, and outlet temperature or
  heat-duty match by duty.
- Long or surprising reactor dimensions: `literature-parameter-audit` ->
  `kinetics-unit-audit` ->
  `unit-card-ledger` -> `reactor-target-planning` -> `reactor-optimization`.
  Stop length/residence-time tuning until exported Aspen card units and kinetic
  row status are known.
- Special or difficult separation: `thermo-property` -> `distillation` ->
  option table from `aspen_distillation_patterns.md` and relevant cases ->
  `solve-fit` -> island proof -> full-flow integration.
- Recycle closure failure: `recycle` -> `pressure-topology` -> `convergence` ->
  `unit-card-ledger` -> `audit-delivery`.
- External Python/GA reactor search: `reactor-target-planning` -> `solve-fit` ->
  external-loop guardrails in `aspen_builtin_solve_fit_tools.md` ->
  final Aspen rerun -> `audit-delivery`. Use external search only after built-in
  Sensitivity/Design Spec/Optimization limits are clear.
- Final handoff/package: `audit-delivery` -> `portable-package` ->
  `self-evolution`.

## Active Recall Cues

Use these cues before deciding the next Aspen trial. They are meant to make the
skill call the right chain even when the user does not name the tool.

| If You See | Recall | First Action |
| --- | --- | --- |
| Low product/feed ratio, weak conversion, large reactor size, or reactor replacement | `bounded-estimate` -> `reactor-target-planning` -> `reactor-optimization` -> `solve-fit` | Build target ledger, audit original full-flow yield, bracket physical reactor variables, then bucket losses before increasing severity |
| Single-pass conversion is plausible but fresh-feed utilization or total conversion is low | `bounded-estimate` -> `separation-replacement` -> `recycle` -> `audit-delivery` | Build a reaction-separation-recycle option table: recover unreacted reactants by flash/condensation, stripping/absorption, membrane/adsorption, purge inerts, and return pressure-compatible recycle before hardening the reactor |
| Freshly converted kinetic, adsorption, equilibrium, catalyst, property, or transport values are about to enter Aspen | `document-evidence` -> `literature-parameter-audit` -> `unit-card-ledger` -> `kinetics-unit-audit` -> `kinetics` | Stop construction until the source matrix, branch status, ledger, calculator output, rendered source evidence, Aspen unit/card basis, and independent review reproduce the same values; correctness outranks token or time cost |
| Yield/RStoic scaffold being promoted to final work | `reactor-target-planning` -> `kinetics` -> `solve-fit` | Replace one reactor in an island, then back-substitute with retained solve/fit evidence |
| Tower purity or concentration target, especially 0.995+ | `distillation` -> `separation-rigorous-optimization` -> `design-spec-trigger` | Use concentration/recovery Design Spec tied to current feed inventory |
| Product draw or split should depend on live feed composition | `calculator-trigger` -> `solve-fit` | Use Calculator read/write variables and audit execution order before promotion |
| Pure-looking product but bad block status, stale values, or impossible draw | `calculator-trigger` plus `convergence` | Run stale/locked manipulated-variable audit and same-run evidence check |
| Minimum purity already exceeded but Design Spec reports out-of-bounds manipulated variable | `calculator-trigger` -> `design-spec-trigger` -> `convergence` | Check Calculator/Design Spec conflict, keep live inventory links, replace equality forcing with external `>=` audit only if downstream gates pass |
| Three focused conventional-column failures with the same topology | `thermo-property` -> `distillation` -> `separation-replacement` | Stop reflux/stage/MAXIT sweeps and build the special-separation option table |
| Dry column, wrong outlet, zero recovery, azeotrope, LLE/VLE warning, BIP gap, or nonphysical water/organic outlet temperature | `thermo-property` -> `separation-replacement` | Screen flash/decanter, LLE, extractive, azeotropic, pressure-swing, absorber, evaporator, membrane, or PSA; condition terminal treatment streams |
| Solvent or entrainer leaves as a terminal stream | `recycle` -> `distillation` -> `audit-delivery` | Build regeneration, purge/makeup, conditioning, and return topology before promotion |
| User asks for no warnings, no errors, or 0-warning run | `convergence` -> `audit-delivery` -> `aspen_zero_warning_repair.md` | Read authority files, inspect lock/process state, run no-run syntax gate, parse Control Panel/history by final phase, then accept only from true-wait dynamic evidence |

## Optional Case Cards

Load a case card only when its workflow pattern matches the current blocker:

- `reactor_separation_solvefit_patterns.md`: anonymized patterns for
  reactor-target planning, reactor replacement, Calculator/Design Spec
  dependency chains, product concentration towers, separation-retargeting, and
  capacity sanity. This replaces project-specific case cards and contains no
  source-project artifacts.
- `case_kinetic_closed_recycle.md`: document kinetics, seed cleanup,
  internal recycle closure, and pressure topology.
- `case_scaffold_to_radfrac.md`: material-balance scaffold upgraded to
  kinetic reactors and `RADFRAC` separation.
- `case_segmented_recycle_boundary.md`: segmented model boundaries and selective
  internal recycle promotion.
- `references/cases/`: compact historical workflow cases. Use them only for
  audit shape and failure recognition, never as process authority.

## Promotion Rule

Promote a model or reference pattern only when the latest exported Aspen input,
block status, stream results, authority manifest, and delivery text support the
active hard gates. Historical cases, segmented runs, and old branches are
evidence, not authority.
