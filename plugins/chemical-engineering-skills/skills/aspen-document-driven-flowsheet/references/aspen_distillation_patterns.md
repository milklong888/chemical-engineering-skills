# Aspen Distillation Build Patterns

Load this reference when a project needs a fast Aspen Plus separation section or
a rigorous replacement for `SEP`/`SEP2`: conventional `RADFRAC`, liquid-liquid
extraction, pressure-swing, azeotropic, extractive, `BATCHSEP`, heat-pump,
multi-effect, or dividing-wall distillation. Use this as a construction method.
Do not copy case values unless the current documents or property checks
reproduce the same basis.

## Energy-Saving Options Are Optional

Multi-effect, heat-pump/VRC, and dividing-wall/Petlyuk designs are opportunity
patterns. They are useful when the column system has material energy cost or a
low-carbon/utility objective; they are not mandatory upgrades for every
distillation task. Always keep a conventional, converged base column or
surrogate sequence as the comparison case.

Consider an energy-saving option when at least one condition is true:

- Reboiler/condenser duty is a meaningful cost, emissions, or utility bottleneck.
- Several columns perform similar or related separations and their temperature
  levels may be matched.
- A rubric or design objective rewards heat integration, low carbon, or utility
  reduction.
- A ternary split has stable light/middle/heavy products and a conventional
  sequence has already proven the product routing.
- Overhead vapor can plausibly be compressed to a useful reboiler temperature at
  acceptable pressure ratio and compressor work.

Reject or defer the option when any condition is true:

- The base separation is not yet proven, product routing is wrong, or property
  method/BIP evidence is weak.
- Heat-source and heat-sink temperatures cannot meet a positive exchanger
  approach after pressure and relative-volatility effects are included.
- Added pressure equipment, controls, capital, operability, solvent/entrainer
  recycle, or convergence risk is larger than the expected utility saving.
- Column duty is small relative to the process energy balance or the current
  task is only a scaffold/diagnostic model.
- The option would hide unresolved product purity, recycle quality, or pressure
  topology failures.

Minimum screening record:

- Base-column duty, product purity/recovery, and pressure.
- Candidate energy-saving pattern and reason it is plausible.
- Temperature approach or pressure ladder/compressor-ratio estimate.
- Added equipment and controls.
- Net utility/work comparison and whether the option is promoted, deferred, or
  rejected.

## Non-Copy Rule

Old cases provide block vocabulary, convergence order, and useful initial ranges.
They do not provide the new project's property method, pressure, solvent,
entrainer, feed split, reflux, stage count, product rate, or recycle policy.
Before reusing any number, pass it through the normal source-to-Aspen unit/card
ledger and prove it is feasible for the current feed inventory.

## Fast Construction Loop

1. Define the separation question.
   Record feed basis, phase, key light/heavy components, target purity/recovery,
   pressure constraints, heat-sensitive components, allowed solvents/entrainers,
   recycle policy, and product/waste boundaries.
2. Follow the Sun-Lanyi tower promotion chain for any tower duty.
   Select the separation family before modeling. Cut the duty into an isolated
   frozen-feed island. Use `DSTWU` or another shortcut only to obtain initial
   stages, reflux, and feed-stage guesses when the selected method permits it;
   if the duty is absorption/stripping, low-temperature solvent wash,
   azeotropic or extractive distillation, three-phase, reactive, electrolyte,
   petroleum, or otherwise outside shortcut assumptions, start directly from a
   minimal rigorous tower. Store the island under the current project in a
   subfolder named for the equipment or duty. Name the Aspen file
   `<project>-<equipment>`, and keep each optimization step as a separate block
   in that one file: `DSTWU` when applicable, initial rigorous tower,
   feed-stage-adjusted tower, and Design-Spec tower. Do not overwrite a previous
   tower state to make the next one. After the rigorous island passes, reconnect
   it to the full flowsheet and add live Design Specs or equivalent external
   specs for purity and/or key-component recovery with bounded manipulated
   variables.
3. If the split is difficult, search before hard-tuning.
   Check this reference's selection table plus relevant `references/cases/`
   cards for known patterns: LLE, extractive, azeotropic/decanter,
   pressure-swing, heat-pump/VRC, multi-effect, DWC/Petlyuk, `BATCHSEP`,
   hybrid flash-column trains, and product-pooling schemes. Write a short
   option table with the required columns below before committing to one path.
4. Choose a thermodynamic basis from behavior, not habit.
   Run or require VLE/LLE sanity checks. Use activity-coefficient methods for
   polar/aqueous/azeotropic/LLE sections, EOS methods for dry gas/hydrocarbon
   pressure sections, and compare methods when product or recycle gates depend
   on the split.
5. Generate the simplest physical island.
   Start with the smallest equipment set that can prove split direction:
   `RADFRAC`, flash/decanter screen, `BATCHSEP`, solvent column, or surrogate
   column pair. Freeze the feed from the latest upstream export.
6. Choose bounded specifications.
   Prefer two independent column specs such as reflux ratio plus distillate rate,
   boilup ratio plus bottoms rate, or Design Spec purity plus bounded reflux.
   Bound flow specs by feed and key-component inventory.
7. Map feasibility before targeting.
   Use Sensitivity over stage count, feed stage, reflux, pressure, product rate,
   solvent/entrainer ratio, compressor pressure ratio, or heat-integrated split.
   Use Design Spec only after the feasible window is visible.
8. Promote only after exported evidence.
   Check block status, stream phase, product purity/recovery, duties, pressure
   devices, and key-component routing from exported input and stream results.
9. Stop repeated same-topology failures.
   After three focused conventional-column failures, and after checking syntax,
   feed inventory, degrees of freedom, fixed draws, Calculator order, property
   warnings, and key-component routing, classify the blocker as setup or
   separation-method/property-chain. Do not continue reflux, stage, or MAXIT
   sweeps until a special-separation option table has been built.

## Option Table Columns

For difficult separations, include these columns before choosing the next island:

- Candidate method and reason it could work.
- Phase-equilibrium evidence, including VLE/LLE/azeotrope or relative-volatility
  basis.
- Property-method and BIP/Data Regression status.
- First island model and frozen-feed basis.
- Manipulated variables and physical bounds.
- Solvent, entrainer, pressure, or recycle-loop implications.
- Expected downstream gates and terminal-boundary effects.
- Rejection, defer, or promotion reason.

## Selection Logic

| Evidence | Candidate | First Island | Critical Proof |
| --- | --- | --- | --- |
| Relative volatility gives clean split | Conventional `RADFRAC` | One column | Key components exit intended ends |
| Azeotrope composition changes with pressure | Pressure-swing | Two columns at candidate pressures | Recycle crosses useful side of azeotrope |
| Solvent forms a second liquid phase | Liquid-liquid extraction | Mixer/extractor + `DECANTER` or extraction column | Extract phase carries target and solvent recycle is cleanable |
| Entrainer creates hetero azeotrope or LLE split | Azeotropic + decanter | Column + `DECANTER` | Entrainer-rich phase separates and recycles |
| Solvent changes relative volatility | Extractive | Solvent-fed column + recovery column | Product purity and solvent recovery both pass |
| Finite charge or time-varying cuts | `BATCHSEP` | Batch column with receivers | Cut sequence and batch mass balance pass |
| High duty and useful temperature lift | Multi-effect | Base column plus pressure ladder | Heat-source column can reboil sink column |
| Overhead vapor can be recompressed | Heat pump/VRC | Base column plus compressor/HEATX | Positive exchanger approach at acceptable PR |
| Ternary middle product and energy saving | DWC/Petlyuk | Two-column surrogate first | Light/middle/heavy split works before merge |

## Conventional RADFRAC

Minimum inputs:

- Feed flow, composition, phase, pressure, temperature, and component IDs.
- Key light/heavy components and product/recovery targets.
- Pressure basis from upstream/downstream equipment, condenser utility, and
  thermal stability.
- Property method with VLE sanity check.

Initial generation:

- If shortcut/DSTWU/Fenske data are available, use them for minimum stages and
  minimum reflux, then start `RADFRAC` above both.
- If no shortcut data exist, start broad: enough stages to show a composition
  gradient, feed stage near the thermal/feed composition transition, total
  condenser unless noncondensables or vapor product require partial condenser,
  and reflux/product-rate Sensitivity ranges wide enough to bracket the target.
- Estimate distillate or bottoms rate from feed key-component inventory and
  intended recovery. Never specify product flow above available key material.

Degrees of freedom:

- Stage count and feed stage set separation capacity and hydraulics.
- Reflux or boilup controls sharpness and duty.
- Distillate/bottoms/side-draw rate controls material split.
- Pressure controls relative volatility, condenser/reboiler temperature, and
  pressure-equipment needs.

Named light-removal towers:

- A source name such as debenzene, light-ends, or light-aromatics tower names
  the service, not necessarily the only Design Spec component. Choose the live
  spec from the actual contaminants that must leave the downstream recycle or
  product section.
- If side reactions or source impurities create toluene, light aromatics,
  sulfur/chlorine traces, water, or other minor components, audit where they
  exit. A benzene-only overhead spec can satisfy the tower name while trapping
  heavier light aromatics in an EB/product recycle; in that case use the
  limiting impurity or a purge/recycle split that removes the whole light
  contaminant family.
- When a light-removal tower overhead is partly recycled for raw-material
  recovery, include an explicit purge/waste branch for the non-target light
  components and gate both the recycle quality and purge existence from the
  exported stream table.

Aspen usage notes:

- For old-style input keep `MAXOL <= 200` before diagnosing convergence.
- Use `ALGORITHM=NEWTON` or the locally stable nonideal option after property
  behavior is set.
- Avoid over-specifying purity, product rate, and reflux simultaneously.

Hydraulics and internals:

- Treat tray or packing hydraulics as a second design layer after the rigorous
  separation has a plausible material and energy balance. First make the
  `RADFRAC` split physically meaningful; then attach internals/sizing/rating.
- For tray columns, exported input should show a section object such as
  `SUBOBJECTS INTERNALS=CS-1`, static pressure-drop logic such as
  `PARAM2 STATIC-DP=YES`, an `INTERNALS` card with tray type, passes, tray
  spacing, diameter, weir/downcomer/hole/flooding parameters, and the matching
  `TRAY-SIZE` card. For packing, require the analogous packing section and
  packing-size/rating cards.
- If transport-property errors appear during hydraulic calculation, repair
  property support first: PCES/structure data/source-backed pure-component
  parameters for vapor density, liquid density, viscosity, surface tension,
  boiling volume, or other model-requested data. Do not disable internals or
  static pressure drop as the fix.
- Use knowledge-graph routing: `CH07-N15` for tray rating, `CH07-N16` for
  packing sizing, `D-HY-01..04` for Hydraulic Analysis interpretation, and
  `CH15_COLUMN_*` / `CH15_CUP_*` for Column Analysis, pressure-drop update, and
  CUP-Tower export.

Hydraulic audit sequence:

1. Confirm latest `RADFRAC` run is converged and product/recovery targets are
   feasible against current feed inventory.
2. Generate column hydraulics data; a flow-rate profile alone is only inventory
   context, not a rating result.
3. Inspect tray/packing sizing and rating: maximum flooding or approach to
   capacity, downcomer backup or packing pressure drop, entrainment/weeping,
   weir loading, tray spacing, diameter, section pressure drop, and warnings.
4. Inspect Hydraulic Analysis plots: actual liquid/vapor load must stay below
   hydraulic maximum and above relevant minimum/load limits. If the actual load
   crosses a limit, the design is not promotable even if the column converges.
5. If pressure drop is updated from hydraulics, switch to rating mode, choose
   the top-stage or bottom-stage update basis deliberately, rerun, and recheck
   the pressure profile plus material results.
6. Record evidence from exported `.inp`, block status, stream results, and
   RadFrac hydraulic result pages or exported report/screenshots. Name any
   accepted warning and why it is not blocking.

CUP-Tower handoff:

- New tower design needs gas/liquid loads, physical properties, operating
  limits, and control/design parameters.
- Old tower rating additionally needs complete internals geometry; without it,
  the task is blocked or provisional.
- Export Aspen hydraulics data from `Profiles|Hydraulics` to Excel, remove
  columns CUP-Tower cannot import as required by the local knowledge graph,
  keep units consistent, and prefer `METCBAR` style data when applicable.
- Select the theoretical stage with the maximum gas/liquid load for CUP-Tower
  import; do not pick an arbitrary stage.
- CUP-Tower load performance diagrams should be used to show operating line,
  flooding, entrainment, weeping, and lower/upper load boundaries.

Validation:

- Key-component distribution matches intended product ends.
- Purity/recovery is from latest stream results.
- Duty and temperature are physical, not false cryogenic convergence.
- Product-rate specs are feasible against feed inventory.
- Hydraulics claims include latest internals cards, pressure-drop basis,
  flood/capacity margins, pressure profile, and warning disposition.

## Pressure-Swing Distillation

Use only when a property check or source shows the azeotrope or relative
volatility changes enough with pressure to create a recycle path.

Minimum inputs:

- Binary/ternary Pxy/Txy or azeotrope composition at candidate pressures.
- Maximum pressure allowed by equipment, temperature limits, and utilities.
- Which outlet recycles and which outlet leaves as product.

Initial generation:

- Pick a low pressure from condenser/downstream constraints.
- Pick high-pressure candidates by property movement, not by old-case pressure.
- Use pump for liquid pressure rise and compressor for gas pressure rise.
- Start with two independent open-loop columns before closing recycle.

Degrees of freedom:

- Low/high pressure pair.
- Recycle cut rate and composition.
- Each column reflux and product rate.

Validation:

- The high-pressure column actually moves composition in the useful direction.
- Recycle returns to the correct side of the azeotrope with nonzero flow.
- Pressure equipment phase and pressure changes are correct.

## Azeotropic Distillation With Decanter

Use when an entrainer creates a separable overhead phase or carries a difficult
component into a hetero azeotrope that can be split by LLE.

Minimum inputs:

- Entrainer identity, allowed impurity in product, makeup/purge policy, and
  whether it is allowed to enter upstream recycle.
- VLE/LLE evidence for ternary behavior and decanter split.
- Product, entrainer-rich, aqueous/organic waste, and recovery boundaries.

Initial generation:

- Screen entrainer/feed ratio and condenser temperature with a flash/decanter
  island before building the full column.
- Feed entrainer/recycle where it can shape the rectifying section; feed the main
  mixture where its thermal/composition state belongs.
- Add recovery column only after the decanter outlet has meaningful phase split.

Degrees of freedom:

- Entrainer/feed ratio, entrainer feed stage, condenser pressure/temperature,
  reflux, decanter temperature, recovery-column product rate, purge fraction.

Validation:

- `DECANTER` produces meaningful phases with expected dominant components.
- Entrainer recycle is nonzero and final product entrainer loss is acceptable.
- Entrainer loop has makeup/purge/loss accounting.

## Liquid-Liquid Extraction

Use when phase behavior shows a real LLE split or a solvent selectively extracts
one key component without needing vapor-liquid staging. This is separate from
extractive distillation: the first proof is liquid phase split and distribution,
not relative-volatility change.

Minimum inputs:

- Feed composition, phase, temperature, pressure, and expected impurity range.
- Solvent identity, solvent/feed basis, mutual solubility, target distribution
  coefficient or literature LLE evidence, solvent loss limit, and regeneration
  route.
- Product, extract, raffinate, solvent recycle, makeup, purge, and wastewater or
  treatment boundaries.

Initial generation:

- Start with mixer plus `DECANTER` or a simple extraction column island at a
  frozen feed basis. Do not close solvent recycle until the extract/raffinate
  directions are proven.
- Sweep solvent/feed ratio and decanter temperature with `SENSITIVITY`; then use
  `DESIGN-SPEC` only for one bounded scalar target such as raffinate impurity or
  extract recovery.
- Add solvent recovery by flash, `RADFRAC`, stripping, drying, or adsorption
  only after the extraction outlet has meaningful flow and composition.

Degrees of freedom:

- Solvent/feed ratio, extraction temperature, number of stages or contactors,
  phase split temperature, solvent recovery split, purge fraction, and wash rate.

Validation:

- Both liquid phases are nonzero and key components route in the intended
  direction.
- Product purity and solvent loss pass from exported stream results.
- Solvent recycle is clean enough for direct return; otherwise keep it as a
  regeneration boundary.

## Extractive Distillation

Use when a high-boiling solvent changes relative volatility without needing a
heterogeneous overhead split.

Minimum inputs:

- Solvent identity, solvent/feed basis, boiling point/thermal limit, product
  solvent limit, and solvent recovery target.
- VLE or selectivity evidence for solvent effect.
- Boundary for heavy impurities and solvent purge.

Initial generation:

- Build extractive column and solvent recovery column as a local island.
- Put solvent feed above main feed unless source evidence says otherwise.
- Sweep solvent/feed ratio and solvent feed stage before closing recycle.
- If a concentration Design Spec converges only at relaxed targets, tighten from
  the latest clean after-run in small steps. Do not reuse the same lower-purity
  source for every target and call it staged continuation.
- Use heat exchangers/pumps only after solvent loop composition is stable.

Degrees of freedom:

- Solvent/feed ratio, solvent feed stage, main feed stage, reflux, product rate,
  recovery-column pressure and split, solvent purge.

Validation:

- Product purity passes without unacceptable solvent contamination.
- Solvent recovery is high enough for recycle and makeup is explicit.
- Heavy impurity/purge outlet is nonzero when needed.
- Product concentration, block status, solvent recovery, and property/BIP
  support must pass together. If the stream looks pure but the extractive column
  is not converged at the accepted target, move to property/solvent/feed-stage
  repair instead of continuing single-variable reflux sweeps.

## BatchSep Distillation

Use for finite charges, time-varying cuts, total-reflux startup, vacuum batch,
multiple receivers, VLL batch behavior, or batch reactive distillation.

Minimum inputs:

- Charge amount/composition, pot holdup, pressure policy, condenser type, receiver
  policy, cut targets, and operation-step triggers.
- Phase behavior over the batch path, especially VLL/entrainer cases.

Initial generation:

- Start with one `BATCHSEP`, finite stage count, stated pressure, condenser type,
  and simple receiver sequence.
- Use high reflux or total reflux only to establish internal profiles, then add
  finite-reflux product collection steps.
- Add feeds or reactions only after the base batch separation mass balance is
  understood.

Degrees of freedom:

- Reflux profile over time, operation-step trigger, receiver switch criteria,
  pressure profile, condenser temperature, holdup, feed stage for semi-batch or
  reactive additions.

Validation:

- Receiver sequence, cut quality, and cumulative mass balance pass.
- Step triggers fire in the intended order.
- Do not use `BATCHSEP` output as steady-state product capacity proof.

## Multi-Effect Distillation

Use after a base column works and total duty is large enough to justify extra
columns, pressure equipment, and heat exchangers.

Minimum inputs:

- Base column purity/recovery/duty at a valid property method.
- Temperature levels for candidate pressure columns.
- Required exchanger temperature approach, utility limits, and pressure limits.

Initial generation:

- Clone the base separation into pressure levels only after the base column
  passes.
- Choose pressure ladder by temperature approach and relative-volatility penalty.
  The heat-source overhead must be hotter than the heat-sink reboiler by the
  required approach; 10 C is a lower screening value and 20 C is a safer first
  engineering target when no better exchanger data exist.
- Add pumps/compressors explicitly. Heaters used only for thermal trim keep
  `PRES=0`.
- Use Design Spec to match heat duties or product purity by varying physically
  meaningful split fractions, product rates, or reflux.

Degrees of freedom:

- Pressure levels, feed split or sequence, reflux per tower, product rate per
  tower, heat-exchanger pairing, duty balance target.

Validation:

- Heat-source and heat-sink duties match with correct sign and feasible approach.
- Product purity/recovery still passes after heat integration.
- Extra pressure reduces net utility enough to justify added complexity.

## Vapor Recompression Heat Pump

Use when a column overhead vapor can be compressed to a temperature high enough
to reboil the same or another column at acceptable compressor work.

For an actual flowsheet connection, load
`aspen_heat_pump_distillation_integration.md`. This section only selects the
pattern; the integration reference controls the connection levels, compressor
phase gate, utility-credit boundary, and hard-gate rerun.

Minimum inputs:

- Base column overhead flow/phase, reboiler duty, condenser duty, pressure,
  allowable compressor type/efficiency, and minimum exchanger approach.

Initial generation:

- Start from a converged base column.
- Sweep compressor pressure ratio or discharge pressure against exchanger
  approach and compressor work.
- Add `HEATX` for main heat transfer, flash/drum for condensed overhead, valve
  for pressure letdown, and auxiliary heater/cooler only for residual duty.
- If the overhead is saturated or near its dew point, add an explicit suction
  superheater or otherwise prove a vapor-only compressor feed. Direct saturated
  overhead compression that triggers liquid-phase or two-phase compressor
  warnings is a failed topology, not a tuning problem.

Degrees of freedom:

- Compressor pressure ratio, heat-exchanger specification, reflux/product split,
  auxiliary reboiler/condenser duty, letdown pressure.

Validation:

- Compressor feed is vapor-rich; liquid compression warnings fail the topology.
- Exchanger approach is positive and stable.
- Reflux/product streams have expected phase after condensation/flash.
- Thermal trim blocks do not hide pressure changes.
- If the original `RADFRAC` still has an internal condenser and reboiler, an
  external VRC branch on the overhead stream is only a runnable supplement. Do
  not claim main-column utility savings until the internal condenser/reboiler
  duty is replaced, linked, or balanced by a live external heat-pump exchanger
  with auxiliary trim duties and a same-run energy audit.
- Minimum accepted supplement evidence: compressor block status 0, no wet-
  compression error text, hot-side temperature approach, visible cooler/drum or
  flash route, product/recycle hard-gate PASS, and an energy report separating
  compressor work from unreplaced internal column duties.

## Dividing-Wall Or Petlyuk-Style Columns

Use only after a conventional surrogate proves a ternary light/middle/heavy split.
Do not start from `MULTIFRAC` when product split, side-draw, or stage allocation
is unknown.

Minimum inputs:

- Light, middle, and heavy key components; product purity/recovery for all three;
  surrogate column results; expected side-draw location and rate.

Initial generation:

- Build prefractionator/main-column or two-column `RADFRAC` surrogate first.
- Use surrogate profiles to initialize `MULTIFRAC`/Petlyuk sections, side draw,
  vapor/liquid split, reflux, and boilup.
- Keep middle-product draw bounded by middle-component inventory.

Degrees of freedom:

- Prefractionator split, side-draw rate/location, section stage allocation,
  vapor/liquid split, reflux, boilup.

Validation:

- Light, middle, and heavy products leave by intended outlets.
- Merged model improves duty or equipment count enough to justify complexity.
- Side-draw is nonzero and compositionally meaningful.

## Local Case Lessons To Reuse Carefully

The local `aspen` case library was reverse-tested to make sure the categories
above map to real Aspen block patterns:

- Conventional/multi-effect methanol-water cases show the value of optimizing a
  base column first, then using pressure levels and duty-balancing Design Specs.
- Pressure-swing cases show the two-column plus pressure-equipment topology, but
  their pressures are system-specific.
- Azeotropic/extractive cases show `RADFRAC` plus `DECANTER` or solvent-recovery
  loops, but entrainer/solvent identity must come from the current system.
- Heat-pump cases show the need for compressor-ratio sensitivity, `HEATX`, flash,
  valve, and auxiliary thermal trim.
- Batch cases show `BATCHSEP` operation-step and receiver logic, not steady-state
  production proof.
- Dividing-wall cases show the safer path: surrogate columns first, `MULTIFRAC`
  after the split is already understood.

## Minimum Audit Commands

Use project-specific file names:

```powershell
rg -n "BLOCK\s+\S+\s+(RADFRAC|BATCHSEP|MULTIFRAC|DECANTER|EXTRACT|FLASH2|COMPR|PUMP|HEATER|HEATX|FSPLIT)" .\*_after_run.inp
rg -n "COL-SPECS|P-SPEC|FEEDS|PRODUCTS|REFLUX|MOLE-D|MASS-D|MOLE-RR|MASS-RR|CONDENSER|VALIDPHASES" .\*_after_run.inp
Import-Csv .\*_stream_results.csv |
  Where-Object stream -in @('<feed>','<distillate>','<bottoms>','<recycle>','<solvent>','<entrainer>') |
  Select stream,temp_C,pressure_bar,mole_flow_kmol_h,mass_flow_kg_h,mol_<key>
Import-Csv .\*_block_status.csv |
  Where-Object { $_.blkstat -notin @('', '0') -or $_.blkmsg }
```
