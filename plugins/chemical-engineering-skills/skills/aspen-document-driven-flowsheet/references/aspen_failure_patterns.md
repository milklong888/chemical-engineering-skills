# Aspen Failure Patterns

Use this reference when auditing, debugging, or repairing an Aspen Plus flowsheet
after the current document route is established. These patterns are reusable
checks, not route or parameter authority.

## Authority And Branching

- Do not let old skills or historical Aspen cases choose the route. Use them for
  syntax and known failure modes only after the current document route is locked.
- Treat segmented cases as disposable scaffolding. Before final delivery, check
  that interfaces are reconciled, duplicate feeds/products are gone, and the
  final model is one connected topology.
- Do not discard a working full-process scaffold while a strict kinetic or
  non-`SEP` island is still failing. Keep the placeholder connected and labeled
  until the replacement proves local and full-flow behavior.
- Do not promote a case because `Run2` returns, block status is mostly clean, or
  backup reopen succeeds. Promotion depends on block messages, stream
  compositions, product/recycle quality, source/card checks, and intended outlet
  routing.
- Verify generated and exported `.inp` text, not just the generator. Search for
  old seed IDs, non-kinetic reactors, ordinary `SEP`, hidden pressure changes,
  and duplicate block IDs in source and `*_after_run.inp`.

## Reactors, Components, And Kinetics

- Search final models for `RYield`, `RStoic`, `REquil`, `RGibbs`, and `RCSTR`
  when documents provide kinetic data. A converged yield or stoichiometric
  baseline is not a kinetic flowsheet.
- For `RYield`, do not paste absolute product kmol/h or kg/h into
  `MOLE-YIELD` or `MASS-YIELD`. Those fields are per unit mass of total feed or
  explicitly non-inert feed. A large `SPECIFIED YIELDS HAVE BEEN NORMALIZED`
  factor plus avoidable element atom-balance warnings is a release blocker:
  classify inert/pass-through diluents, add the `INERTS` list when needed,
  rebuild the yield values on the feed-mass basis, and prove the fix with
  after-run exported cards plus a warning scan.
- If later chapters contain full kinetics, revisit rate-unit conversion before
  blaming convergence or using stoichiometric reactors. For `POWERLAW
  CBASIS=PARTIALPRES`, locally verify Aspen's pressure-unit interpretation, then
  convert time and pressure powers consistently.
- If a kinetic table's units conflict with symbol notes, OCR text, or the cited
  original paper, stop conversion and triangulate the pressure/concentration
  basis from rendered table units, equation dimensionality, and original-source
  conventions. Do not mix values from different bases in one Aspen card.
- If a reprinted current-source kinetic table conflicts with another secondary
  table or a suspected original-source convention, keep branch labels instead
  of declaring one side wrong too early. Separate source-literal reproduction,
  cited-original reconstruction, and Aspen-release readiness; only the last can
  authorize promoted Aspen cards.
- Do not convert a literature dispute into a fitted constant. A table-to-table
  factor difference must be audited through the full rate equation, including
  pressure powers, adsorption terms, equilibrium constants, correction factors,
  catalyst basis, and time units, then tested with a single-point calculator
  before any Aspen reactor work continues.
- Do not treat OCR or copied text as kinetic authority by itself. Re-check each
  pre-exponential, exponent, adsorption term, equilibrium term, correction
  factor, and unit against rendered pages or the cited original. If the source
  table, equation, and symbol note disagree, freeze an adopted basis in a
  ledger before any Aspen card is touched.
- For `exp(-B/T)` literature constants, audit whether Aspen expects the
  temperature parameter `B` or activation energy `E`. Convert with `E = B*R`
  only for cards that use `exp(-E/RT)`, and verify exported unit tags before
  treating the reactor as kinetic evidence.
- In partial-pressure LHHW equations, pressure-unit conversion is term-specific.
  Recalculate the pressure power for the forward driving force, reverse
  equilibrium term, adsorption denominator, and any `p_i/p_j` ratio separately.
  A single blanket conversion factor for the whole table usually means the card
  basis is unproven.
- Do not borrow validation-case catalyst density, catalyst loading, feed,
  pressure, geometry, outlet temperature, or conversion into the base reactor.
  Treat validation tables as separate cases unless the document explicitly
  defines a shared parameter.
- If reactor sizing, residence time, or space time values produce low conversion,
  verify the Aspen reactor volume/card basis before blaming kinetics.
- If a reactor length or residence time grows into an unexpectedly large
  `RPLUG` result, audit kinetic-card units before accepting the size. In
  old-style `POWERLAW`, exported `.bkp` unit tags can show a card energy basis
  such as `cal/mol` even when the project ledger stores activation energy in
  `J/kmol`; those are not interchangeable Aspen inputs.
- If a product/feed ratio looks too low, separate reactor conversion,
  selectivity, fixed product-draw caps, sale/reuse boundaries, purge/recovery
  streams, and vent losses before changing reactor severity. Low main products
  can be caused by missed reactor targets, stale product-column draws, and large
  terminal boundaries at the same time; do not blame conversion alone until each
  bucket is quantified.
- Do not tune `PRE-EXP`, `ACT-ENERGY`, reaction orders, or LHHW denominator terms
  to force conversion unless values are sourced and unit-converted.
- If an independent kinetic calculator returns rates large enough that a
  microscopic reactor slice gives finite conversion, classify the result as a
  unit/basis blocker. Audit catalyst mass basis, bed density, time units,
  pressure units, kmol-vs-mol scaling, and missing inlet trace species before
  attempting Aspen convergence fixes or parameter fitting.
- If a formula component fails only when participating in reactions, check
  formation enthalpy/free energy and EOS/vapor-pressure properties in a user
  databank before replacing chemistry with a surrogate.
- If a component lookup imports only as formula-like/name-only, lacks exported
  CAS/MW identity, or succeeds only in nonreactive blocks, treat it as an
  identity/property probe, not a reactor-ready component.
- If a kinetic card exports correctly but produces no material change, run a
  micro-probe varying only the suspect card basis before changing chemistry,
  reactor size, or convergence settings.
- For LHHW cards with adsorption denominators and equilibrium driving forces,
  compare at least one independent single-point rate calculation with an Aspen
  micro-reactor/card probe before reconnecting the full reactor.
- A source-literal diagnostic ODE is not an Aspen-ready reactor. Keep it labeled
  provisional if catalyst loading or bed density, heat-transfer correlations,
  inlet trace-product policy, pressure basis, or Aspen LHHW/User Kinetics card
  equivalence is missing.
- If a source reactor model solves heat transfer through `K`, `U`, `UA`, wall,
  fouling, bed-transfer, or `Kbf` correlations, a fixed outlet temperature,
  fitted heat duty, or `T-SPEC` profile is only a diagnostic shortcut until the
  Aspen heat-transfer card has been matched to the source model.
- RPLUG cards can be syntactically accepted while semantically wrong. Check that
  length, diameter, tube count/equivalent volume, phase, pressure, temperature
  profile, and reaction-set basis survive export and produce the expected local
  conversion before reconnecting downstream columns.
- A reactor can hit the literature conversion window and still be a failed
  process case. If fixed downstream draws, light-end handling, or recycle quality
  no longer match the new inventory, the full-flow case still fails. Treat
  conversion as one constraint, not the objective.

## Separators And Distillation

- Search final models for ordinary `SEP`. When the user forbids `SEP`, both
  `SEP` and `SEP2` are release blockers with no placeholder exception. Treat
  each old shortcut as evidence that a separation target is missing: record the
  key split, target outlet, recovery/purity, recycle or terminal boundary, and
  physical unit chosen to implement it.
- Do not bury reactor/separator shortcut checks in generic run-status validation.
  The report must say whether reactor-rigor and separator-rigor gates passed,
  failed, or passed only as documented placeholders.
- Do not bury product quality checks in generic run-status validation. A normal
  block table does not prove column specs are feasible or product streams meet
  capacity and purity after topology changes.
- Do not treat a downstream polishing-column failure as recycle-closure failure
  unless the changed outlet feeds a recycle path or changes a pre-recycle cut.
- Do not use a two-outlet shortcut separator block as a multi-outlet splitter in
  old-style Aspen input. Split gas/light removal, component recovery, and product
  cuts into serial separators or use suitable rigorous/multi-outlet blocks.
- Check every outlet from each flash/split/separator. If one phase is recycled
  but another phase from the same recovered material is unintended product, it is
  a topology leak.
- When replacing a shortcut separator with rigorous equipment, verify that the
  physical split still matches the process intent and is driven by a real target
  variable when adjustment is required. Removing `SEP2` is not enough if the
  replacement sends target product to wastewater, purge, recycle, or heavy
  residue because of infeasible specs.
- If a replacement imports, runs, and backup-reopens but the intended
  reject/recovery outlet has zero flow, blank output, or no-phase-splitting
  messages, treat it as failed separation evidence.
- For concentration, evaporation, or vacuum steps with mass-fraction targets,
  verify product stream mass fractions after unit conversion. A column with
  dry-column/flow-limit messages or vapor sent into a liquid pump still fails.
- Do not keep increasing reflux or stages when binary probes show wrong
  volatility or unsuitable property method. Fix component identity and
  thermodynamics first.
- Do not accept a high-purity product stream from a nonconverged column. If a
  concentration `SPEC/VARY` passes at relaxed targets but fails after true
  staged continuation and micro-staging, classify the remaining blocker as
  special-separation/property-chain or degree-of-freedom formulation until
  property/BIP evidence, solvent/feed mapping, and clean block status are proven.
- For RadFrac starts, bound distillate, bottoms, side-draw, and reflux specs by
  latest feed and key-component inventory. Fixed product-rate values from older
  islands are not reusable after recycle closure.
- Reactor severity changes invalidate old fixed product draws. Recompute
  key-component inventory in the column feed before reusing a `MOLE-D`, side
  draw, or recovery target; otherwise product streams can remain at the old mass
  rate while carrying the wrong component.
- Try simpler physical bridges before complex columns when proving boundary
  feasibility or recycle cleanup: flash, condenser, decanter/LLE screen, absorber,
  evaporator/vacuum flash, or labeled flow split.
- Do not assume ordinary distillation is adequate for high-purity polar or
  aqueous products. If probes or literature indicate azeotropic, extractive, or
  entrainer-assisted purification, model that finishing island separately.
- Keep solvent loops inside product-finishing or cleanup islands until pressure,
  purge, loss, and product gates pass. Do not connect solvent recycle to
  raw-material recycle by default.
- Do not count an extractive-distillation solvent-rich outlet as recovered until
  it returns to the extractive column through regeneration, purge/makeup, and
  pressure or temperature conditioning. A terminal `SOLV`/`NOCT`/`REC` stream is
  a failed solvent-loop gate unless explicitly accepted as a regeneration
  boundary.
- When replacing product-polishing shortcuts with extractive or azeotropic
  islands, run the island independently with source-derived starts, pressure
  letdown, and local spec sweeps before integrating full recycle.

## Recycle And Pressure

- Prove each documented recycle with topology and numbers: separator outlet ->
  purge/split if needed -> pressure equipment if needed -> upstream mixer/reactor,
  plus nonzero key-component return flow.
- If a document says material is "sent back", model it as real recycle unless
  disposal, sale, purge, or fuel use is explicitly described. Add purge only as a
  labeled closure assumption when no purge policy is supplied.
- When replacing a seed or boundary recycle with a real internal recycle, remove
  obsolete seed-stream claims and recalculate fresh-feed/product basis.
- If low-pressure liquid recycle returns to a high-pressure feed section, insert
  a pump. If gas recycle returns to a higher-pressure section, insert a
  compressor. Do not let exchanger or reactor pressure specs hide pressure rise.
- Do not add a pump or compressor merely to show recycle equipment when the
  recycle stream is already at receiving pressure.
- Do not stop the pressure audit at equipment presence. Group compatible sections
  into pressure islands when documents or literature support it.
- After changing reactor severity, rerun recycle-quality gates. Better local
  conversion can still break raw-material recycle by changing phase, impurity, or
  separator load.
- If closed-recycle cold start leaves retained or regenerated column
  nonconvergence errors, try Aspen-valid tear-stream estimates before weakening
  the process model.

## Input, Automation, And Delivery Failure Surfaces

- When removing a seed stream from old-style `.inp`, delete the whole stream
  definition, not only the `STREAM <id>` line. Orphan `MOLE-FRAC` lines can attach
  to adjacent streams.
- When generating old-style Aspen stream and block cards, preserve statement
  boundaries, newline termination, and full stream/block definitions.
- Split Aspen automation into import, roundtrip export, run, after-run export,
  and backup-reopen checks. A COM `InitFromFile` `NullReferenceException` is an
  input/import/property blocker until proven otherwise.
- Preserve prior `.bkp`, `.apwz`, exported `.inp`, block CSV, stream CSV, and
  run-summary artifacts before rerunning fragile cases.
- Old-style Aspen stream and block IDs can be truncated in exported files. Keep
  identifiers at eight characters when possible, and compare generated input,
  after-run input, and stream CSV before writing hard-gate names.
- If a run passes but many product, recovery, purge, or vent outlets remain as
  terminal streams, the process is still open. Add a terminal-output audit based
  on `FLOWSHEET` topology before writing the delivery text.
- Do not trust an allowed terminal list without checking the operation chain just
  upstream. An outlet from a column, flash, decanter, absorber, extractor, or
  reactor that is only pumped, compressed, heated/cooled, valved, or simply
  split before becoming terminal is usually only tail conditioning, not completed
  recovery, recycle, sale, or treatment. Add a terminal-tail-operation audit:
  meaningful source -> conditioning tail blocks -> terminal. Allow exceptions
  only as exact configured paths with sale, treatment, fuel/utility, purge/waste,
  external regeneration, or controlled-reuse justification.
- Do not let audit wrappers create false green lights. If the JSON audit says
  `passed=false` but the shell command exits successfully, CI, smoke tests, and
  future agents will promote a failed case. Make promotion audits throw on
  failed hard gates, and make regression audits succeed only when the expected
  failure gates are present.
- Aspen old-style input parsers must preserve continuation lines and tokenized
  stream/block IDs. A runner that ignores `&` continuation syntax or deletes old
  outputs before proving a new case opened can create false green or false stale
  evidence. Verify import, run, after-run export, and reopen before replacing
  artifacts.
- For portable script packages, centralize path assumptions in a package-root
  runner or config file. Expose generic commands for environment check, case
  audit, project initialization, and Aspen input execution without editing
  Python constants.
- On Windows PowerShell literature-fetch scripts, use
  `Invoke-WebRequest -UseBasicParsing` when legacy browser parsing or security
  prompts interfere with scripted downloads.
- When writing a delivery PDF, treat text generation as another model surface,
  not as clerical output. Build from current exported/audit artifacts, render
  pages to PNG, extract UTF-8 text, and search for critical block names, recycle
  paths, pressure devices, `HEATER PRES=0`, reactor types, final numbers, stale
  branch labels, `????`, and replacement characters.
- If Chinese or other non-ASCII text appears as question marks in a PDF, suspect
  the text source path first: Windows shell here-strings and inline scripts can
  replace characters before the PDF library sees them. Regenerate from a
  UTF-8 file, XeLaTeX/ctex source, or escaped Unicode content, then repeat visual
  and extracted-text checks.
- Do not ship temporary PDF QA artifacts. Rendered PNGs, font probes, extracted
  text checks, and smoke-test directories belong outside the final package or
  must be deleted before compression.
