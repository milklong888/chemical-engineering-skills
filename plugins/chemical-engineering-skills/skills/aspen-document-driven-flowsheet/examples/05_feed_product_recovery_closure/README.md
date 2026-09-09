# Feed/Product Recovery Closure Example

Use this example when a full flowsheet has clean-looking products but a poor
fresh-feed/product ratio. The point is to diagnose where valuable material goes
before changing reactor severity.

## Cold-Start Prompt

```text
Audit this Aspen case for low product/fresh-feed ratio. First verify whether
the key reactor conversions match sourced single-pass target windows. If they
do, bucket valuable material losses into product, recycle, qualified external
recovery, purge, vent, wastewater, heavy residue, solvent/entrainer loss, and
failed-separation outlets before changing reactor parameters. Check Calculator
and Design Spec dependencies, especially equality specs that target a minimum
purity already exceeded by the product or recycle stream.
```

## Expected Agent Moves

1. Build a reactor target ledger and compare exported reactor conversions.
2. Compute fresh feed, product mass, product/fresh ratio, and valuable-material
   terminal losses from stream CSV data.
3. Trace recovery-like terminal streams back through the exported FLOWSHEET.
4. Route contaminated valuable-material recovery to a recovery/refining boundary
   until the receiving recycle quality gate passes.
5. For tower purity gates, check whether a Calculator writes the same variable a
   Design Spec varies.
6. If a minimum-purity stream already exceeds the target but the Design Spec is
   out of bounds, treat that as an over-constrained setup and replace it with an
   explicit external `>=` audit only after same-run downstream gates pass.
7. Check terminal-treatment temperatures and phases before final packaging.

## Do Not Copy

Do not copy stream names, rates, conversions, component choices, column specs,
or reactor dimensions from any old case. This example is only a reasoning
pattern for cold-start diagnosis.
