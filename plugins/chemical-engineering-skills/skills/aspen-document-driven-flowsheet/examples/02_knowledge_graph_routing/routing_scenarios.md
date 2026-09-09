# Knowledge Graph Routing Scenarios

Use `skill/references/knowledge_graph.md` as the routing index. These examples
show which node chain to recall before another manual Aspen trial.

## Weak Reactor Conversion

Symptom: product/feed ratio is low, or a kinetic reactor misses conversion.

Route:

`bounded-estimate` -> `reactor-target-planning` -> `reactor-optimization` -> `solve-fit`

First actions:

- Build the reactor target ledger from current documents and external anchors.
- Audit original full-flow yield before changing reactor cards.
- Use Sensitivity or Design Spec on a real physical parameter such as length,
  volume, residence time, temperature, or feed ratio.
- Back-substitute the targeted island into the full flow only with retained
  solve/fit evidence.

## Product Concentration Tower

Symptom: a column must reach 0.995+ mass or mole fraction, or a purity target
is named by the user/source.

Route:

`distillation` -> `separation-rigorous-optimization` -> `design-spec-trigger` -> `solve-fit`

First actions:

- Check feed inventory and feasible product rate.
- Write the target as a concentration, recovery, or impurity Design Spec.
- Manipulate a real degree of freedom such as reflux ratio, distillate rate,
  bottoms rate, side draw, solvent rate, or pressure.
- If the same column topology fails three focused times after setup checks,
  build a special-separation option table.

## Live Feed-Dependent Set Point

Symptom: product draw, solvent makeup, purge, or feed ratio should track recycle
closure or live composition.

Route:

`calculator-trigger` -> `solve-fit` -> dependency-chain audit

First actions:

- List Calculator read variables, write variables, and execution point.
- Confirm the manipulated variable is not locked or stale.
- Re-run downstream gates in the same run before promotion.

## Difficult Separation Or Wrong Outlet

Symptom: dry column, zero recovery, azeotrope, LLE/VLE warning, or property BIP
gap.

Route:

`thermo-property` -> `distillation` -> `separation-replacement` -> `solve-fit`

First actions:

- Check property method and phase behavior before more reflux/stage sweeps.
- Compare flash/decanter, extraction, extractive distillation, azeotropic
  distillation, pressure-swing, absorber/stripper, evaporator, membrane, or PSA.
- Prove the chosen island with exported streams before reconnecting recycle.
