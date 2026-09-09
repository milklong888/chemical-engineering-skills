# Literature Parameter Extraction And Conversion Audit

Use for source-derived kinetics, equilibrium/adsorption, transport, property,
catalyst and pressure parameters. This original workflow summary includes no
paper/book tables, private cases or proprietary manual text.

## Source and intent first

Separate paper-literal reproduction, cited-original reconstruction, deterministic
conversion, numerical probes and formal Aspen entry. An old runnable case or a
successful diagnostic does not make its constants the current design basis.

Each affected parameter needs:

```text
source document/version/hash and page/table/equation locator
raw observed text/value and confidence
full source equation, term role and algebraic powers
pressure/concentration/activity/catalyst/time/amount/geometry basis
conversion expression and explicit assumptions
Aspen model/equation/card/units/version
independent calculation/probe and exported-card evidence
status, competing branch, affected consumers and next action
```

Defaults and initializers count if the model uses them. A known source form may
remain frozen while its destination card is unresolved.

## Exhaust extraction and derivation before missingness

Search equations, symbols/aliases, captions, footnotes, appendices, supporting
information and cited originals. Compare available independent text extractors;
inspect actual formula/table pages. Page/character counts find dropout, not
semantic correctness. Keep damaged OCR as locator-only.

Preserve raw observations. A unique source-local reconstruction can be recorded
with its constraints and uncertainty, never relabeled literal glyph verification.
If multiple readings remain, block only that claim and identify the minimum gap.
Check network/rate-law completeness, units, temperature function, catalyst basis,
species mapping, operating range and model compatibility. Trends alone can guide
hypotheses but cannot supply missing kinetic constants.

## Convert the full equation, not the table heading

- Derive pressure/concentration powers term by term in numerator, denominator,
  equilibrium and adsorption expressions; no global factor for a whole LHHW table.
- Keep `exp(-B/T)` distinct from `exp(-E/(R*T))`. Only the destination requiring
  the latter justifies `E=B*R`, using consistent gas-constant units.
- Separate catalyst particle/bulk density, voidage, loading, activity, active-site
  or metal basis and tube count.
- Convert time, molar amount, mass, bed/catalyst volume and area explicitly.
- Distinguish component-formation rates from reaction rates through stoichiometry.
- Release heat/mass-transfer or pressure-drop correlations with their equation,
  symbols, properties, geometry, coefficient range and resistance-network basis.

Use `scripts/kinetics_conversion_template.py` when its family applies; it is
arithmetic, not authority. Preserve term-by-term factors and an independent
back-calculation.

## Separate evidence branches

Keep source-literal, cited-original, prior-work candidate, dimensionally derived
candidate, provisional and formal-entry states distinct. Do not average conflicts
or select values because they converge or resemble a familiar model. Industrial
design inputs, literature validation data, finite probes and solver initializers
remain separate; shared use requires explicit source authority.

## Diagnose magnitude and singularities

Use applicable one-point rate/property/transport calculations, denominator checks,
stoichiometric bounds, inlet sensitivities and microsteps. A differential probe
must actually be differential; appreciable conversion is a scale warning.
A singular zero-product inlet is a source/model/initializer question, not
permission to add arbitrary trace species to the design. Extreme rates or
sensitivity reopen the affected unit/basis row; do not fit constants, catalyst
mass, geometry or duty to conceal it.

## Same-case Aspen and release evidence

Maintain:
`source equation/value -> source units -> deterministic conversion -> verified
Aspen card equation/units -> exact input -> same-version exported verification`.

Freeze property/phase and affected feed, catalyst, geometry, transport and
pressure assumptions before non-provisional claims. Authorized diagnostic or
scaffold work may continue within its scope; it is not formal kinetics.
The shared strict policy/operations checker owns delivery; provisional claims,
clean run, products, equipment and final-file acceptance remain distinct.
Case-local relaxation cannot become shared strict success or learning.

## Correct now; evolve only after closure

Correct the current ledger, quarantine affected outputs and replay downstream
consumers. During ongoing work, record the incident only in the project audit.
Explicit user closure of the current task revision is required before shared
evolution. A candidate states trigger, observation, mechanism, action,
verification and applicability; technical claims need appropriate strict
evidence. No transferable increment means no change. Private source pages,
case IDs and parameter tables stay local.

