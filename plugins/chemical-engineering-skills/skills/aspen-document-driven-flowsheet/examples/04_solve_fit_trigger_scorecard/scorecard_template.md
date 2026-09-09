# Solve/Fit Trigger Scorecard

Create this scorecard before broad manual sweeps.

## Reactor Replacement

| Field | Entry |
| --- | --- |
| Current source basis | `source_docs/current_document` |
| Key reactant and inlet/outlet streams | `A`, `RIN` -> `ROUT` |
| Target conversion window | `0.80-0.90`, from current document plus external anchor |
| Scaffold evidence | `RYIELD/RSTOIC case`, material balance only |
| Original full-flow yield audit | product/feed, recycle loss, purge loss, separation loss |
| Kinetic island | `RCSTR` or `RPLUG` with exported reaction set |
| Manipulated physical variable | volume, length, residence time, temperature, pressure, feed ratio |
| Aspen tool | Sensitivity bracket, then Design Spec or Optimization |
| Promotion evidence | exported input, block status, stream results, residual/status, warning scan |
| Back-substitution gate | full-flow rerun keeps solve/fit record and downstream gates pass |

## Column Concentration Target

| Field | Entry |
| --- | --- |
| Column and product stream | `C1`, `PROD` |
| Target | mass or mole fraction, recovery, or impurity limit |
| Feed inventory check | key component feed rate and feasible product rate |
| Manipulated variable | reflux ratio, distillate rate, bottoms rate, pressure, solvent rate, side draw |
| Aspen tool | Design Spec after a Sensitivity bracket |
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
