# Solve/Fit Trigger Scorecard

Complete this record before proposing repeated trials. Read
[the shared tool rule](../../references/aspen_builtin_solve_fit_tools.md) first.

## Intent And Execution Contract

| Field | Current-case entry |
| --- | --- |
| User objective and method | Exact current requirement; equality, inequality, response analysis or objective |
| Intent classification | read_value / derive_once / live_relation / scan_range / match_target / optimize / fit_data / discrete_scenarios / diagnose |
| Route receipt | New solve_route receipt path; classification is not Aspen execution |
| Continuous/discrete variables | Names, units, authorized bounds, physical degrees of freedom and current writers |
| Existing response evidence | Same-case valid interval or reason a new native Sensitivity is needed |
| Calculator timing | Producer, current-run read basis, formula, target input, consumer, convergence order |
| Native implementation | Current-version help/node evidence, actual objects and protected candidate |
| External substitution if needed | Specific native gap and supporting evidence; missing MCP wrapper alone is insufficient |
| Execution evidence | Exported objects, table/residual/status and same-run downstream gates |
| Final scope | Analysis executed / target met / sampled or local optimum / engineering acceptance separately |

## Reactor Replacement

| Field | Entry |
| --- | --- |
| Current source basis | `source_docs/current_document` |
| Key reactant and inlet/outlet streams | `A`, `RIN` -> `ROUT` |
| Target conversion window | Current authorized source value, units/basis and source location; no example default |
| Scaffold evidence | `RYIELD/RSTOIC case`, material balance only |
| Original full-flow yield audit | product/feed, recycle loss, purge loss, separation loss |
| Kinetic island | `RCSTR` or `RPLUG` with exported reaction set |
| Manipulated physical variable | volume, length, residence time, temperature, pressure, feed ratio |
| Aspen tool | Reuse a valid response bracket or native Sensitivity, then Design Spec or Optimization as appropriate |
| Promotion evidence | exported input, block status, stream results, residual/status, warning scan |
| Back-substitution gate | full-flow rerun keeps solve/fit record and downstream gates pass |

## Column Concentration Target

| Field | Entry |
| --- | --- |
| Column and product stream | `C1`, `PROD` |
| Target | mass or mole fraction, recovery, or impurity limit |
| Feed inventory check | key component feed rate and feasible product rate |
| Manipulated variable | reflux ratio, distillate rate, bottoms rate, pressure, solvent rate, side draw |
| Aspen tool | Design Spec with a valid response bracket; reuse current evidence instead of rescanning |
| Failure stop | after three focused same-topology failures, build special-separation option table |
| Promotion evidence | concentration spec residual, block status, stream composition, warning scan |

## Calculator Dependency Chain

| Field | Entry |
| --- | --- |
| Read variables | stream/component/flow values read by Calculator |
| Write variables | block specs or stream values written by Calculator |
| Execution point | before/after named block or convergence step |
| Downstream Design Spec | target and manipulated variable using Calculator output |
| Stale-value audit | same-run export proves value changed with live inventory |
| Promotion evidence | Calculator card, Design Spec card, residual/status, downstream stream results |

## Special-Separation Option Table

| Option | Trigger | First proof |
| --- | --- | --- |
| Conventional RadFrac | relative volatility adequate and no azeotrope warning | feed inventory plus concentration Design Spec |
| Pressure-swing distillation | pressure-sensitive azeotrope or close-boiling system | two-pressure VLE and recovery check |
| Extractive distillation | solvent changes relative volatility and can be regenerated | solvent loop, purge, makeup, return composition |
| Azeotropic distillation | entrainer creates removable phase or azeotrope shift | entrainer recovery and recycle closure |
| LLE extraction/decanter | phase split supports target component transfer | ternary/LLE check and solvent regeneration |
| Absorption/stripping | gas-liquid transfer controls recovery | solvent rate or stripping duty sensitivity |
| Membrane/PSA shortcut | rigorous model unavailable but unit is named and justified | whitelist, recovery basis, terminal boundary audit |
