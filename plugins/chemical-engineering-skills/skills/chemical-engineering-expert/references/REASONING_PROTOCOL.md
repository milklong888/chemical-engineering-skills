# Chemical-Engineering Reasoning Protocol

## 1. Priority and role separation

Apply this protocol whenever chemistry, chemical engineering, process design,
simulation, or chemical equipment is materially involved.

Use the following priority order for decisions:

1. safety, law, and non-negotiable physical invariants;
2. the user's current explicit instruction and required method;
3. the active project's current authority files and accepted change-offsets;
4. same-case verified experimental, software, inspection, or vendor evidence;
5. direct statements from the governing source;
6. deterministic derivations from items 3-5;
7. applicable verified standards and cited external sources;
8. explicit provisional engineering estimates;
9. pretrained memory, which may route searches but is not evidence.

`ERROR_MEMORY.md` has highest *inspection priority*: read it before using a
skill or graph. It does not become higher factual authority than fresh project
evidence. If an error-memory rule conflicts with a newer authority, quarantine
the old rule and record the conflict.

Keep two roles separate:

- **Design layer:** decides system boundary, chemistry, property method,
  topology, balances, specifications, feasibility, and acceptance.
- **Implementation layer:** enters cards, writes scripts, drives software,
  formats documents, and captures results under the frozen design contract.

The implementation layer may report a blocker but may not silently redesign
the process.

## 2. Evidence classes

Tag every consequential fact, number, or decision with one class.

| Tag | Class | Allowed use | Required disclosure |
| --- | --- | --- | --- |
| `A` | Active authority | Formal project basis or accepted offset | Exact file/node/row and version/date |
| `R` | Same-case result | Experiment, Aspen/software export, inspection, calculation script, or vendor result for the same item and basis | Exact artifact, run/candidate, units, and status |
| `D` | Deterministic derivation | Algebra, unit conversion, stoichiometry, balances, ordering, bounds, or direct logical implication from `A/R` | Inputs, equation/rule, units, and check |
| `J` | Engineering judgment | Estimate, correlation choice, simplifying model, analogy, or assumption | Assumptions, applicability range, sensitivity, and `provisional` status |
| `X` | External knowledge | Cited standard, paper, database, handbook, official manual, or current web source not yet adopted into the project | Source, date/version, scope, and whether it is candidate or accepted |
| `U` | Unresolved | Indispensable information remains missing after the derivation ladder | Exact missing variable, blocked equation/decision, and what remains possible |
| `F` | Forbidden transfer | Value or conclusion belongs to another project, example, equipment item, version, or operating basis | Why transfer is invalid and what same-case evidence is required |

Do not relabel `J` or `X` as `A`, and do not treat a vector-search hit as
evidence. A calculation is `D` only when it introduces no unverified empirical
constant or modeling choice; otherwise it is `J`.

## 3. Required-method lock

At task start, record:

- required method and named source;
- purpose of the method;
- immutable steps, formulas, software, and output form;
- allowed numerical or implementation freedom;
- forbidden substitutions;
- evidence needed to claim compliance.

Before deviating, identify the exact blocker and distinguish:

- **implementation variation:** same method and basis, allowed;
- **equivalent transformation:** mathematically demonstrable equivalence,
  record it;
- **method substitution:** different correlation, topology, model, or software
  basis, forbidden without user approval or an explicit authority update.

Never use familiarity, convenience, convergence, or prettier output as a
reason to substitute the method.

## 4. Derivation-before-missing ladder

Do not say “not provided”, “not found”, or “cannot calculate” after one search.
Proceed until the first genuinely inapplicable rung and record the search scope.

1. Search the authority file, tables, captions, appendices, nearby paragraphs,
   alternate spellings, IDs, and units.
2. Inspect structured artifacts: Aspen exports, stream/block tables, ledgers,
   spreadsheets, scripts, JSON/CSV/XML, software reports, and drawings.
3. Normalize units, bases, reference states, dry/wet basis, mass/molar basis,
   actual/standard volume, time basis, and component names.
4. Derive with algebra, ratios, chemical stoichiometry, composition closure,
   reaction extent, recovery/selectivity/yield identities, and time ordering.
5. Close material and component balances; then energy and pressure relations
   when the needed thermodynamic data or justified bounds exist.
   Define the control volume first. For a reacting species, accumulation equals
   inflow minus outflow plus net reaction generation; at steady state include
   the stoichiometric source term, or use conserved elements instead. Internal
   recycles cancel at the whole-system boundary and are counted only when they
   cross the chosen control volume. Do not apply inert-species closure to all
   reactants and products.
6. Use physical bounds, monotonicity, interpolation, bracketing, scaling, and
   limiting cases to obtain a range or consistency test.
7. Use an explicit engineering estimate only when its source/correlation,
   applicability, assumptions, and sensitivity are recorded as `J`.
8. Declare `U` only when a variable is indispensable and neither derivable nor
   safely estimable. Name the smallest missing set and the exact next evidence
   that would unblock it.

Distinguish these outcomes:

- `not_yet_found`: retrieval is incomplete;
- `not_explicit_but_derived`: report the `D` result;
- `bounded`: report the defensible interval;
- `provisional_estimate`: report the `J` result and sensitivity;
- `requires_external_evidence`: state the source/software/vendor needed;
- `blocked`: only the affected claim is blocked, not unrelated work.

## 5. Macro design contract

Before detailed implementation, freeze the smallest useful contract.

1. **Objective and boundary:** feed, products, by-products, wastes, utilities,
   battery limits, capacity, time basis, and acceptance metrics.
2. **Chemistry:** reactions, stoichiometry, conversion/selectivity/yield basis,
   catalyst or equilibrium limits, side reactions, and component fate.
3. **Thermodynamics and phases:** expected phases, property method, parameter
   coverage, association/electrolyte/Henry/LLE/azeotrope needs, and T/P range.
4. **Material closure:** total, component, and elemental balance; recovery and
   purge losses; recycle accumulation; scale consistency.
5. **Energy and pressure:** heat sources/sinks, utility levels, temperature
   approaches, phase-change feasibility, compression/pumping/letdown duties,
   and pressure direction.
6. **Topology and roles:** every block has one physical purpose; every stream
   has an origin and destination; separation and recycle logic are explicit.
7. **Products and terminals:** purity/capacity/recovery basis plus disposition
   of every terminal gas, liquid, solid, purge, vent, wastewater, and residue.
8. **Operability and control:** degrees of freedom, manipulated variables,
   inventory, startup/shutdown, recycle root stability, and failure response.
9. **Safety, environment, and materials:** credible hazards, relief/venting,
   temperature/pressure/material compatibility, emissions, and waste handling.
10. **Economics and constructability:** dominant equipment/utility burden,
    unrealistic complexity, unavailable heat levels, and evidence boundaries.

For a narrow task, do not create a long report; perform a quick impact scan
against these ten items and surface only material conflicts.

For route, flowsheet, optimization, or design-quality decisions, use
`MACRO_DESIGN_QUALITY.md`. Hard-gate feasibility is non-compensable. Only after
all material hard gates pass may alternatives be compared for “good” or
“preferred” status. A converged or locally optimized design is not thereby
feasible, complete, operable, safe, or preferred.

## 6. Whole-system sanity gates

Before acceptance, check at least:

- units and bases are consistent;
- compositions close and flows are non-negative;
- stoichiometric and elemental limits are respected;
- phase labels agree with T/P and the chosen thermodynamics;
- heat flows from an available level to a feasible sink with a valid approach;
- pressure changes match pumps, compressors, valves, and equipment limits;
- recycle has purge/makeup/inventory control and does not create scale drift;
- separation claims match volatility, phase split, solvent, reaction, or
  membrane mechanism;
- equipment type matches physical service and no duty is silently duplicated;
- every feed/component has a plausible fate and every terminal is classified;
- product purity, capacity, recovery, and time basis refer to the same case;
- safety, environmental, economic, and operability consequences were not
  hidden by local convergence or formatting success.

## 7. Completion states

Use explicit states instead of a binary answer:

- `accepted`: authority, derivation, implementation, and verification align;
- `provisional`: useful result with explicit assumptions/sensitivity;
- `bounded`: only a range is defensible;
- `diagnostic_only`: useful for fault isolation, not delivery;
- `quarantined`: contradicted, wrong-scope, stale, or unsafe;
- `blocked`: an indispensable missing item prevents only the named claim.

Lead with the conclusion, then show evidence tags, decisive calculations,
assumptions, status, and the macro checks that could overturn it.
