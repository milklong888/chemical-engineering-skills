# Macro Chemical-Process Design Quality

Use this reference when judging, creating, comparing, or repairing a process
route or flowsheet. It defines what “reasonable” and “good” mean at the macro
level. Detailed unit-operation skills remain responsible for equations, cards,
equipment sizing, and implementation.

## 1. Meaning of a good design

A good process design is not merely a converged simulation, a collection of
individually plausible units, or the lowest value of one objective. It must be:

1. **admissible** — consistent with chemistry, conservation, thermodynamics,
   safety, law, and stated project constraints;
2. **complete** — the system boundary, every component fate, utility source,
   recycle, purge, product, emission, wastewater, solid, and residue are
   accounted for;
3. **operable** — it has feasible inventories, measurements, manipulated
   variables, startup, shutdown, turndown, maintenance, and upset responses;
4. **competitive** — it was compared with credible alternatives on a common
   basis and is not obviously dominated in cost, energy, risk, complexity,
   environmental burden, reliability, or flexibility;
5. **defensible** — project facts, derivations, judgments, external knowledge,
   uncertainties, model limits, and verification evidence are distinguishable.

Do not collapse these into one compensating score. A favorable economic score
cannot offset a failed conservation, phase-feasibility, safety, or legal gate.

### Decision states

| State | Meaning |
| --- | --- |
| `inadmissible` | At least one non-compensable hard gate fails. |
| `undemonstrated` | No hard failure is proven, but a critical gate lacks indispensable evidence. |
| `feasible` | All hard gates pass on the declared basis; comparative quality is not yet established. |
| `good` | Feasible, complete, robust enough for the stated stage, and justified against credible alternatives. |
| `preferred` | The selected good design best satisfies the declared priorities or occupies the chosen Pareto trade-off, with the decision rule disclosed. |

“Feasible” is not synonymous with “good”, and “good” is always relative to the
declared objective, boundary, maturity stage, and uncertainty range.

## 2. Macro-to-micro review order

Review in this order, iterating when a later result changes an earlier choice:

1. objective, battery limits, capacity/time basis, products, specifications,
   constraints, and comparison basis;
2. chemistry and route alternatives: stoichiometry, equilibrium, kinetics,
   selectivity, by-products, catalyst/solvent fate, and reaction hazards;
3. input/output structure and the destination of every component;
4. reactor–separation–recycle structure, purge/makeup, and inventory closure;
5. thermodynamic phases and property-method coverage across the full T/P and
   composition envelope;
6. separation sequence and the physical driving force of every separation;
7. energy and pressure architecture, heat recovery, utility levels, and only
   then detailed heat integration or heat pumping;
8. plantwide inventories, production-rate manipulation, product-quality
   control, disturbances, startup/shutdown, and abnormal operation;
9. inherent safety, safeguards, emissions, wastes, materials, reliability,
   maintainability, construction, and logistics;
10. common-basis economics, uncertainty, sensitivity, alternatives, and the
    evidence required for the current design stage.

The hierarchy adds detail without allowing the detail layer to rewrite an
earlier design decision silently.

## 3. Non-compensable hard gates

For every material design review, assign each gate `pass`, `fail`, or
`unknown`, with an `A/R/D/J/X/U/F` basis. A critical `unknown` prevents a final
acceptance claim; it does not prevent unrelated calculations or bounded work.

### G0 — Objective, boundary, and basis

- Feed, products, by-products, wastes, utilities, battery limits, capacity,
  operating time, purity/recovery/yield definitions, and acceptance criteria
  refer to one declared basis.
- The comparison does not mix different production rates, years, currencies,
  utility definitions, product slates, or environmental boundaries.
- Required methods and forbidden substitutions are frozen.

### G1 — Chemistry and route feasibility

- Products and by-products have an atom source; stoichiometric, equilibrium,
  kinetic, catalyst, selectivity, and residence-time limits are respected.
- Feed impurities and side products that poison catalysts, accelerate
  corrosion, foul equipment, deactivate solvents, or compromise product
  quality are traced.
- Heat release/absorption, runaway/decomposition potential, and scale-dependent
  mixing or heat-transfer limits are not hidden by a conversion specification.

### G2 — Thermodynamics and phase behavior

- Expected vapor, liquid, aqueous, organic, solid, supercritical, electrolyte,
  association, Henry-component, azeotropic, or LLE behavior is represented.
- The property method and parameters cover the actual component set, phase
  topology, composition, temperature, and pressure range.
- A solver phase label is not accepted when it conflicts with physical bounds
  or applicable phase-equilibrium evidence.

### G3 — Conservation and component fate

- Total, component, elemental, and—where relevant—charge balances close on the
  same basis; flows and inventories are non-negative.
- Every feed component reaches a product, recycle, purge, vent, wastewater,
  solid, loss, reaction product, or documented accumulation term.
- Energy and momentum/pressure relations are consistent with the declared
  steady or dynamic boundary.

### G4 — Flowsheet topology and sequence

- Every block has one stated physical purpose and mechanism; every stream has a
  source, destination, state, and reason to exist.
- Unit order protects sensitive downstream operations and avoids needless load,
  dilution, contamination, phase change, and pressure reversal.
- Mixing, splitting, bypassing, recycling, and purging have explicit material,
  energy, control, maintenance, safety, or product reasons.
- No unit is included only because a familiar example used it.

### G5 — Energy, pressure, and utility feasibility

- Heat moves from an available source to a sink through a feasible temperature
  approach; pressure increases require a pump/compressor and pressure losses or
  letdown have a physical path.
- Utility temperature/pressure/quality is no higher than needed after feasible
  process heat recovery and upgrading have been assessed.
- Compression, refrigeration, vacuum, heat pumping, and phase change include
  their work, rejected heat, discharge conditions, equipment limits, and
  off-design behavior. Energy upgrading is never treated as free.

### G6 — Operability and plantwide control

- The design identifies throughput manipulation, material and energy
  inventories, product-quality variables, measurements, manipulated variables,
  constraints, and key disturbances.
- Recycles possess a stable material-balance structure, makeup/purge logic, and
  a bounded startup path; inert, impurity, solvent, and by-product accumulation
  are addressed.
- Startup, shutdown, turndown, grade change, maintenance isolation, loss of
  utilities, and important failure states have physically possible paths.

### G7 — Safety, environment, and legal constraints

- First seek inherent risk reduction by elimination/substitution, inventory
  minimization, moderated conditions, and simplification; then add independent
  prevention and mitigation appropriate to the residual risk.
- Reaction hazards, relief/vent disposition, loss of containment, fire,
  explosion, toxicity, asphyxiation, dust, corrosion, overpressure, vacuum,
  human factors, siting, and emergency response are not deferred beyond the
  point where they can change the concept.
- Air, water, solid, hazardous-waste, and life-cycle boundaries are explicit;
  pollution is not merely moved outside the chosen battery limit.

### G8 — Equipment, materials, construction, and maintenance

- Equipment type matches phase, duty, pressure, temperature, solids, viscosity,
  corrosion/erosion, fouling, cleanability, containment, and scale.
- The design has plausible access, isolation, drainage/venting, inspection,
  replacement, spares/redundancy where justified, and constructable geometry.
- Exotic materials, extreme conditions, very large trains, and novel equipment
  are supported by current evidence rather than optimism.

### G9 — Model and evidence adequacy

- Model fidelity matches the decision: shortcuts may screen; they cannot prove
  a claim that depends on rigorous phase behavior, hydraulics, dynamics,
  mechanical integrity, vendor performance, or safety analysis.
- Units, bases, versions, parameters, assumptions, residuals, convergence,
  validation range, and source provenance are recorded.
- Important conclusions survive bounds, sensitivity, off-design cases, or
  uncertainty analysis appropriate to the design stage.

## 4. Flowsheet-arrangement reasonableness

Use a function-first topology audit before sizing equipment.

### 4.1 Unit-purpose and stream-causality map

For each unit, record:

`purpose -> physical mechanism -> required inlet state -> intended outlet change -> downstream consumer -> upset consequence`

For each stream, record:

`source -> components/phases -> useful role -> destination -> recycle/purge/terminal status`

A missing purpose or consumer is a topology defect, not a drawing defect.

### 4.2 Sequence tests

The following are high-value design hypotheses, not universal laws. Apply them
only when their physical premises hold and compare exceptions explicitly.

- **Protect sensitive steps:** remove or limit catalyst poisons, solids,
  corrosives, water, oxygen, heavy ends, light gases, or fouling precursors
  before a sensitive catalyst, membrane, adsorbent, cryogenic step, high-purity
  step, or vulnerable material when the contaminant matters there.
- **Exploit the natural state:** use an available phase split, pressure, or
  temperature driving force before paying to destroy it and recreate it later.
- **Bulk removal before polishing:** a robust, low-cost operation often removes
  the large load before a selective or expensive finishing step. Reject this
  heuristic when recovery, equilibrium, degradation, contamination, or heat
  integration makes another order superior.
- **Avoid unnecessary mixing or dilution:** do not combine streams that must be
  separated again, or dilute a target before separation, unless reaction,
  safety, heat transfer, control, transport, or equipment constraints justify it.
- **Avoid thermodynamic backtracking:** repeated heat–cool, vaporize–condense,
  compress–throttle, dissolve–dry, or mix–separate cycles require an explicit
  process benefit and common-basis comparison.
- **Keep loads out of expensive steps:** do not send easily removable inert,
  solvent, water, or by-product loads through high-pressure, cryogenic,
  high-vacuum, high-purity, or highly selective equipment without a reason.
- **Place recycle by component role:** recover valuable reactant, catalyst, or
  solvent to a point with compatible state and composition; do not return
  products, poisons, inerts, or irreversible by-products without a controlled
  purge or conversion path.
- **Preserve product and waste separation:** remove a purge before it
  contaminates a useful recycle, and avoid creating a harder mixed waste merely
  to improve one local recovery metric.
- **Integrate without trapping the plant:** heat/mass integration must retain a
  credible startup, shutdown, turndown, bypass, cleaning, isolation, and
  disturbance path.

### 4.3 Recycle and purge questions

1. Which components are consumed on each pass, and which are conserved or
   generated?
2. What prevents each conserved impurity or inert from accumulating?
3. Is the purge location compositionally selective enough to avoid excessive
   valuable-material loss?
4. Are makeup and purge coupled to the correct inventory or composition?
5. Can the system reach the intended steady state from a finite initial charge?
6. Does increasing recovery create an unbounded circulation or a second scale
   root?
7. Are the reactor, separator, and recycle capacities based on circulation load
   rather than only fresh feed?

### 4.4 Pressure-path questions

- Does every pressure rise have a compatible pump, compressor, ejector, or
  hydrostatic source?
- Is gas being sent to a liquid pump or liquid carryover to a gas compressor?
- Is valuable pressure destroyed in a valve and then restored immediately?
- Can pressure be used to drive separation, transfer, expansion work, or heat
  upgrading without compromising safety or control?
- Are suction conditions, cavitation/surge/choke risk, discharge temperature,
  pressure drop, and relief boundaries plausible?

## 5. Reduce high-grade utility: preheat, recover, then upgrade

External high-temperature heat is a scarce, costly, and often carbon-intensive
resource. A good design does not demand zero high-grade utility; it minimizes
and justifies the residual demand using this order.

### 5.1 Utility hierarchy

1. **Avoid the duty:** reconsider reaction/separation conditions, excess
   dilution, avoidable evaporation, over-purification, heat loss, and repeated
   phase or temperature cycling.
2. **Recover directly:** use compatible hot process streams, condensates, or
   other waste heat to preheat feeds or intermediate streams with a valid
   temperature approach and operable exchanger network.
3. **Rearrange the process:** change sequencing, pressure levels, intermediate
   temperatures, or heat-source/sink timing when this reduces total burden
   without violating chemistry, product, safety, or control constraints.
4. **Upgrade suitable heat:** evaluate mechanical vapor recompression,
   closed-cycle heat pumps, steam/thermal recompression, or another justified
   upgrading route when a source and sink are well matched.
5. **Use the lowest adequate external utility level:** reserve higher-grade
   steam, hot oil, fuel, or electricity-driven heating for the residual sink
   that genuinely needs it.

For a steady heat pump or vapor-recompression boundary, the useful hot-side
heat is supplied by recovered source heat plus compressor/input work. Report
both; do not count recovered heat as an independent energy source twice.

### 5.2 Preheat and direct heat-recovery checks

- Source and sink duties are simultaneous, or storage/intermediate utility is
  explicitly provided.
- Supply/target temperatures and the entire temperature profile maintain a
  feasible minimum approach; endpoint temperatures alone are insufficient.
- Phase change, variable heat capacity, reactions, freezing, thermal
  degradation, corrosion, fouling, and cleanability are considered.
- Added exchanger area, pressure drop, stream splitting, bypasses, control
  interaction, startup heating, and loss-of-source fallback are included.
- Heat recovery is compared on net utility, capital, reliability, and
  operability—not only maximum theoretical recovery.

### 5.3 Compression and heat-upgrading checks

Use compression when it creates a useful temperature/pressure lift on a
suitable vapor or refrigerant and the whole-system benefit survives these
checks:

- source and sink heat duties, temperatures, and availability match;
- required temperature lift and exchanger approach are feasible;
- suction phase, cleanliness, molecular weight, condensables, entrainment,
  corrosivity, and materials are compatible with the machine;
- pressure ratio, stages/intercooling, efficiency, shaft power, discharge
  temperature, operating envelope, and equipment size are credible;
- compression does not cause decomposition, unwanted reaction, product
  contamination, phase instability, or an invalid property-model region;
- coefficient of performance, electricity/fuel prices, carbon factors,
  capital, maintenance, turndown, startup, control, and backup heat are compared
  on the same basis;
- benefits are not claimed by omitting the compressor work, cooling load, heat
  exchanger, pressure loss, or residual utility.

A large temperature lift, poor compressor efficiency, dirty/unstable vapor,
weak source–sink coincidence, or fragile control may make direct utility or a
different process arrangement preferable.

## 6. Comparative quality after hard gates pass

For newly built or materially changed flowsheets, the equipment feasibility
loop in `PROCESS_EQUIPMENT_FEEDBACK.md` is part of the evidence for these gates.
Map simulated duties to actual equipment, test the current operating envelope,
and return attributable capacity/physical failures to process design. Re-run
affected consumers after an accepted split, stage, or operating change; retain
the same-candidate per-device trace. Catalog gaps and provisional model status
alone neither prove nor disprove physical feasibility.

Compare credible alternatives on the same boundary. Keep the axes visible;
weights reflect the declared project objective and must not be invented.

| Axis | Questions |
| --- | --- |
| Product and feed efficiency | Are capacity, purity, recovery, yield, selectivity, and feed loss jointly acceptable? |
| Energy and pressure quality | Are total duties, temperature levels, work, refrigeration, vacuum, pressure losses, and recoverable heat reasonable? |
| Economics | Are capital, raw materials, utilities, waste, labor/maintenance, replacement, downtime, and uncertainty included on one date/location basis? |
| Simplicity and reliability | Can units, recycles, controls, and heat matches be removed or simplified without losing required function? What are the single-point failures? |
| Operability and flexibility | Does the plant tolerate feed, ambient, catalyst, demand, and utility variation and retain turndown/startup/shutdown paths? |
| Safety and environment | Is hazardous inventory and severity reduced? Are emissions, effluent, waste, water, and life-cycle burdens genuinely lower? |
| Constructability and maintainability | Can it be built, isolated, cleaned, inspected, repaired, and supplied with available materials/equipment? |
| Evidence maturity | Are the decisive claims supported by data, applicable models, same-case results, sensitivity, and reproducible artifacts? |

Use Pareto reasoning before weighted ranking. If option A is no worse on all
material axes and better on at least one, option B is dominated unless an
omitted constraint or uncertainty reverses the conclusion.

## 7. Macro red flags

Any of these triggers an explicit investigation before detailed optimization:

- a product, atom, energy source, pressure source, or disposal route appears
  without a physical origin;
- recovery, conversion, selectivity, or yield uses inconsistent denominators,
  exceeds physical limits, or comes from a different run than capacity/purity;
- a converged simulation has negative flows, implausible phases, unclosed
  balances, severe residuals, or an invalid property method;
- a recycle carries a conserved impurity/inert with no purge, or circulation
  grows while fresh-feed/product scale is supposed to remain fixed;
- units are individually valid but arranged as unnecessary mix–separate,
  heat–cool, vaporize–condense, or compress–throttle loops;
- high-grade steam/hot oil/fuel is used for preheat while a compatible hot
  process stream is cooled, without an integration or operability explanation;
- vapor recompression or a heat pump is claimed to save heat without compressor
  work, temperature lift, COP, discharge conditions, exchanger approach, or
  backup being modeled;
- a valve raises pressure, a pump handles bulk gas, a compressor ingests bulk
  liquid, or a heat exchanger requires a temperature cross without a mechanism;
- the separation has no credible volatility, solubility, phase split, affinity,
  size, charge, reaction, or transport driving force;
- a product specification is met only by an unreported loss, purge, dilution,
  external feed, or waste transfer;
- the nominal steady state has no finite startup inventory/path, no turndown,
  no maintenance isolation, or no safe state after loss of a key utility;
- optimization silently changes the product basis, design capacity, safety
  constraint, equipment count, operating hours, or environmental boundary;
- a polished report or detailed equipment calculation precedes proof that the
  route, topology, and whole-plant balances are reasonable.

## 8. Minimum expert output for a process-design review

Keep the response proportional to the task, but make these items recoverable:

1. conclusion and state: `inadmissible`, `undemonstrated`, `feasible`, `good`,
   or `preferred`;
2. design basis and required-method lock;
3. one-sentence process logic and topology rationale;
4. failed/unknown hard gates and decisive whole-system checks;
5. key material, energy, pressure, recycle, and terminal-stream calculations;
6. credible alternatives and material trade-offs;
7. evidence tags, assumptions, uncertainty, and next verification action.

For a narrow lookup, perform the gates mentally and expose only material
conflicts. For a formal route/flowsheet decision, use the complete ledger and
optionally validate its status logic with `scripts/macro_design_gate.py`.

## 9. Provenance and limits

The framework independently combines mechanisms from these primary or official
sources; it does not copy their examples or case values:

- [Douglas, hierarchical process synthesis (1985)](https://doi.org/10.1002/aic.690310302): add flowsheet detail through decision levels and compare alternatives/economic trade-offs.
- [Luyben, Tyreus, and Luyben, plantwide control (1997)](https://doi.org/10.1002/aic.690431205): plantwide energy, production, quality, constraint, inventory, makeup, component-balance, and optimization concerns.
- [Linnhoff and Hindmarsh, pinch design method (1983)](https://doi.org/10.1016/0009-2509(83)80185-7): temperature-level targeting and heat-exchanger-network synthesis.
- [IDAES model-diagnostics workflow](https://idaes-pse.readthedocs.io/en/latest/explanations/model_diagnostics/index.html): start simple; check degrees of freedom, structure/units, numerical behavior, multiple states, and maintain a model log.
- [U.S. EPA green engineering principles](https://www.epa.gov/green-engineering/about-green-engineering): systems and life-cycle thinking, safer inputs/outputs, resource conservation, and waste prevention without abandoning viability.
- [U.S. CSB inherent-safety summary](https://www.csb.gov/csb-releases-new-safety-video-on-inherently-safer-design-and-technology-inherently-safer-the-future-of-risk-reduction-examines-how-industry-can-eliminate-or-reduce-hazards/): substitute, minimize, moderate, and simplify.
- [UK HSE reaction-process guidance](https://www.hse.gov.uk/pubns/books/hsg143.htm): establish the reaction-hazard basis of safety for batch and semi-batch processes.
- [U.S. DOE Better Plants process-heating guidance](https://betterbuildingssolutioncenter.energy.gov/better-plants/process-heating): use a systems view, map material/energy movement, recover waste heat, and preheat where justified.
- [U.S. DOE waste-heat recovery report](https://www1.eere.energy.gov/manufacturing/intensiveprocesses/pdfs/waste_heat_recovery.pdf): closed compression cycles and open mechanical/thermal vapor recompression as heat-upgrading routes.
- [Grossmann and Floudas, flexibility analysis (1987)](https://doi.org/10.1016/0098-1354(87)87011-4): test feasibility under uncertain conditions rather than only at the nominal point.

These sources establish methods and review dimensions, not universal equipment
values, property methods, margins, temperature approaches, compressor limits,
costs, or project priorities. Those remain source- and case-specific.
