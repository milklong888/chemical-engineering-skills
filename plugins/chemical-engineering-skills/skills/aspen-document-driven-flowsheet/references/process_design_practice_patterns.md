# Process Design Practice Patterns

Use this reference before detailed Aspen tuning when the active question is
still a design decision: what problem is being answered, whether a capacity or
product rate is reasonable, which variables deserve rigorous simulation, or
whether another optimization run is worth its cost.

When using scan-like engineering-practice sources, render pages and use OCR only
as a search aid. Treat them as engineering practice guides. Do not promote OCR
tables, old prices, kinetic constants, equipment correlations, FORTRAN outputs,
or English-unit examples without visual verification, modern source checking,
and a unit/card ledger.

## Front-End Chain

1. Define the real question.
   State design requirements, product slate, production scale, purity,
   boundaries, and what would count as a useful answer. Reject work that answers
   an unasked question.
2. Check market and capacity assumptions.
   Tie feed rate, product rate, sales volume, price, build schedule, and policy
   constraints to the economic basis before treating capacity as fixed.
   If the expected industrial scale, feed/product ratio, conversion, or product
   slate is uncertain, search external industrial/literature/patent/project
   sources before accepting an Aspen result.
3. Audit experimental and literature data.
   Record data source, method quality, theory/measurement limits, units,
   uncertainty, and applicability range before using the data in Aspen.
4. Do bounded estimates.
   Use limiting material balances, conversion/selectivity envelopes, heat-duty
   estimates, residence-time bounds, or rough equipment-capacity checks to
   eliminate impossible options before rigorous models.
5. Screen options economically.
   Compare rough investment, utility, raw-material loss, recovery, purge,
   solvent makeup, and operating cost proxies before deep simulation.
6. Build the detailed model only after the decision frame is clear.
   Use Aspen Sensitivity, Design Spec, Optimization, Calculator, or Regression
   to refine the surviving options, not to compensate for an undefined problem.
7. Explain assumptions and next evidence.
   Delivery notes should say which costs, data gaps, safety limits, or detailed
   equipment checks are unresolved.

## Aspen Usage Patterns

- Reaction-system framework setup:
  `problem-definition` -> rough external industrial/literature/patent anchors
  -> per-reactor target conversion/selectivity ledger -> framework scaffold.
  Do this before Aspen framework design so reactor conversions are bounded
  assumptions rather than unnamed tuning knobs.
- Low product/feed sanity check:
  framework run -> per-reactor conversion/selectivity acceptance ->
  material-balance audit -> separation/recovery loss audit ->
  economic/capacity interpretation. Compute this from limiting raw-material
  conversion, selectivity, recycle quality, purge/vent loss, and component
  main-product yield. Do not confuse a co-product ratio, such as PO:SM, with the
  feed/product yield.
- Reactor network choice:
  compare CSTR, CSTR series, recycle reactor, and PFR/RPLUG by conversion,
  selectivity, heat removal, residence time, recycle load, safety, and cost.
- Strongly exothermic reactor:
  check heat-removal capacity, coolant temperature, thermal stability, runaway
  risk, and disturbance response before relying on a controller to save an
  unstable design.
- LLE/extraction design:
  audit distribution coefficients and solvent loss, then compare mixer-settler
  stages, extraction columns, regeneration, purge, and makeup.
- Vacuum or heat-sensitive distillation:
  check tower pressure drop, bottom temperature, residence time, reflux ratio,
  tray/packing efficiency, polymerization/heavy-formation risk, and inhibitor
  assumptions.
- Reactor-separation integrated optimization:
  do not promote a locally optimal reactor or tower if it raises recycle load,
  solvent loss, purge burden, product impurities, or downstream utility cost.
- Utility or infrastructure screening:
  for pipeline, pumping, heating, storage, rail/truck, or other boundary
  choices, use simple cost and operability estimates before building detailed
  Aspen machinery around a boundary assumption.

## Do Not Promote Without Rechecking

- Historical prices, equipment-cost correlations, depreciation, labor, utility
  costs, ENR-index adjustments, or 1960s dollar bases.
- Kinetic constants, activation energies, reaction orders, transfer
  coefficients, Thiele moduli, effectiveness factors, VLE/LLE tables,
  distribution coefficients, tray efficiencies, pressure drops, pipe diameters,
  pump-station counts, or temperature/pressure limits from OCR.
- OCR tables and appendix program outputs. Reopen rendered pages or primary
  sources, verify units, and create a unit/card ledger before Aspen use.
