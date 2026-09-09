# Aspen Audit Gates And Commands

Use this reference when promoting a case, reviewing an Aspen draft, checking a
delivery package, or deciding whether the latest model satisfies user-named hard
gates.

Current acceptance and learning are owned by the chemical expert's
`STRICT_ACCEPTANCE_AND_LEARNING.md`. These are stage-specific engineering
checks, not an alternative warning policy or Summary parser. An explicit
case-local exception preserves failed strict gates and remains audit-only;
its results and descendants are excluded from learning and default retrieval.

## Review Gates

- Chemistry gate: every documented reaction is modeled, intentionally excluded
  with a reason, or flagged as missing data.
- Kinetics gate: documented constants/orders/adsorption terms are represented in
  PowerLaw/LHHW first pass or recorded as unresolved implementation details.
- Real-kinetics gate: final kinetic constants and reaction orders are sourced,
  unit-converted, and mapped to Aspen; provisional conversion, yield, or
  space-time assumptions are labeled checkout baselines and do not satisfy this
  gate.
- Literature-branch gate: when kinetic or transport evidence conflicts across a
  current source, OCR text, secondary reproductions, and cited-original
  conventions, the authority note must list each branch and status:
  source-literal reproduction, cited-original conversion, and Aspen-release
  basis. Diagnostic source-literal calculators may run with labels, but Aspen
  block creation, reruns, and delivery claims require the Aspen-release branch
  to be frozen with unit/card and exported-card evidence.
- Reactive-component property gate: formula, hypothetical, or user-databank
  intermediates have enough thermodynamic data for the selected reactor and
  property method before reaction tuning begins.
- Reactor-rigor gate: final reactor block types are enumerated. If full kinetics
  were requested or the document provides enough kinetic data, any remaining
  `RYield`, `RStoic`, `REquil`, or `RGibbs` is a failed gate unless explicitly
  justified.
- Document extraction gate: equations and tables were checked beyond plain text
  before claiming absence.
- Unit/card gate: every copied source value records source units, conversion
  formula, converted Aspen-basis value, destination card, card meaning, and
  exported-input verification.
- Priority gate: the current authority artifact names the user-requested target,
  accepted source basis, accepted scaffold, latest hard blocker, and next module.
- Zero-warning gate: strict is the default. Use the canonical checker on the
  source-verified complete Summary schema and current raw history, preserving
  run/file identity. Any actual warning/error fails strict acceptance; missing
  evidence is not zero. Block-status and named-gate messages are additional
  diagnosis, not replacements. A user-authorized exception is case-local only
  and cannot qualify as strict promotion or learning evidence.
- Scaffold gate: a yield/stoichiometric plus shortcut skeleton is explicitly
  labeled as scaffold, capacity-balanced, pressure-audited, and not final
  kinetics or separator rigor.
- Reactor-target ledger gate: before the first framework is built for a chosen
  reaction system, each reactor has a key reactant, approximate external or
  document-backed conversion target window, selectivity/safety/economic limits,
  provisional block type, manipulated variables, and intended Aspen tool route.
  Framework assumptions that lack this ledger are provisional at best.
- Reactor-conversion acceptance gate: after the framework runs, compute each
  reactor's actual key-reactant conversion and selectivity from exported stream
  results, compare them with the target ledger, and only then interpret product
  rate or feed/product sanity. Low product rate without this per-reactor check is
  an incomplete diagnosis.
- Promotion gate: an island or probe may replace a scaffold block only after
  its frozen strict stage contract passes: local run/export/reopen, complete
  clean-run evidence, meaningful outlet flows, target component in intended
  outlet, unit/card ledger, and full-flow reintegration. Explained failures
  remain diagnosis or explicitly relaxed case-only work, never strict pass.
- Built-in solve/fit gate: Calculator, Design Spec, Sensitivity, Optimization,
  Regression, Data-Fit, `DATA-SET`, or `PROFILE-DATA` use has target,
  variable/parameter list, bounds, data source or target basis,
  convergence/residual status, exported `*_after_run.inp` evidence, and no stale
  manual-sweep override. Reject tool results with missing exported cards,
  unreadable targets or bounds, variables pinned to absurd limits, or downstream
  product/recycle gates broken after the solve.
- Reactor solve/fit promotion gate: when a user or rubric names reactor
  conversion, reactor sizing, reactor optimization, or reactor replacement as an
  active target, require retained Aspen solve/fit evidence in the promoted case.
  Manual or external back-substitution points without a completed exported
  `SENSITIVITY`, `DESIGN-SPEC`, `OPTIMIZATION`, `REGRESSION`, or equivalent
  auditable tool record remain diagnostics even if their stream results satisfy
  conversion and product specifications.
- Competition-rubric gate: when a modern-design-method rubric applies, every
  active deduction is a hard gate. Before heat-network design, enforce
  report/model consistency, frozen simulation precision, strict clean run
  status (explained failures remain diagnostic/case-relaxed, not strict pass), connected recycle topology, rate-model reactor evidence, sourced
  kinetic units, at least one reactor structure/operation optimization, rigorous
  separation models, at least one separation-parameter optimization, material
  balance, and source-file delivery. Mark heat-integration and detailed
  exchanger checks as deferred only when the user explicitly excludes that stage.
- Hard-gate-first scoring gate: accepted-case selection is a two-stage process,
  not a weighted score. First evaluate all active hard gates from the user,
  rubric, document, and authority manifest; only branches with every hard gate
  passing may enter numerical ranking. A branch with run success, zero bad
  blocks, high purity, or higher utilization is still rejected if any hard gate
  fails. Promotion scripts must make this visible by writing `accepted_*` files
  only for passing branches; failed branches should be written as `case_*`,
  `diagnostic_*`, or `rejected_*` evidence.
- Reactor-optimization gate: for RPLUG or tube-reactor promotion, verify
  structural variables (`LENGTH`, `DIAM`, tube count or equivalent flow area,
  `L/D`, volume/residence time) and operating variables (temperature, pressure,
  feed ratio/concentration, space velocity) have bounds, source basis,
  Sensitivity or Design Spec evidence, and exported cards. Low product/feed ratio
  claims must first pass through per-reactor conversion acceptance, then be
  traced to conversion, selectivity, separation loss, recovery sale/reuse,
  purge, or wastewater.
- Reactor-type authority gate: if the promoted branch changes reactor type,
  state whether the current documents authorize the type or whether the branch is
  an engineering candidate. Do not present a CSTR, CSTR-series, recycle-reactor,
  fixed-bed, or plug-flow substitute as final merely because it is numerically
  stable; compare conversion, selectivity, heat removal, pressure, recycle load,
  and downstream separation gates before promotion.
- Recycle gate: all real recycle loops are closed or explicitly open; seed
  streams are labeled as seeds.
- Solvent-loop gate: extraction, extractive-distillation, azeotropic, and
  entrainer loops show real topology from separator outlet through regeneration,
  purge/makeup, pressure or thermal conditioning, and return to the consuming
  unit. Solvent-rich `REC` terminal streams fail unless the user explicitly
  accepts a regeneration boundary.
- Terminal-boundary gate: parse the latest exported `FLOWSHEET`, enumerate every
  produced stream with no consumer, and compare it with the allowed product,
  recovery, purge, vent, and wastewater list. Fail unapproved terminal names that
  look like recovery, solvent, return, heavy, product, purge, vent, or waste
  streams. A flow is not "handled" merely because it has a stream name.
- Terminal-tail-operation gate: after the terminal-boundary gate, trace each
  terminal path upstream from meaningful source blocks (`RADFRAC`, `BATCHSEP`,
  `MULTIFRAC`, `FLASH2/3`, `DECANTER`, `EXTRACT`, `ABSBR`, `RCSTR`, `RPLUG`,
  kinetic reactors, or a project-configured recovery source). If the only
  intervening blocks are tail operations (`PUMP`, `COMPR`, `HEATER`, `HEATX`,
  `VALVE`, or simple `FSPLIT`), fail the case unless the exact path is configured
  as a sale product, treatment boundary, fuel/utility export, purge/waste
  boundary, external regeneration boundary, or controlled-reuse interface with a
  reason and quality evidence. Do not use `MIXER` as a default source block;
  enable it only when project evidence makes a mixer the material boundary.
  Pressure or thermal conditioning alone is not recovery, recycle, purification,
  or disposal. The older `post_pressure_terminal_check` is a compatibility alias
  for the one-hop `RADFRAC -> PUMP/COMPR -> terminal` subset.
- Pressure gate: every pressure rise is assigned to compressor or pump equipment;
  heaters with `PRES=0` are only heat exchangers with no pressure change. Also
  check avoidable compression/letdown/recompression cycles when credible
  operating-condition ranges exist.
- Interface gate: cross-section streams, duplicated blocks, and repeated
  accounting boundaries are reconciled.
- Balance gate: component, mass, and key element balances are checked across the
  full flowsheet and major sections.
- Capacity gate: final product rate and purity are checked from the latest
  exported stream results after recycle closure and treatment boundaries.
- Column-spec gate: for each rigorous column, product rate is feasible against
  latest feed, intended key component leaves by intended outlet, and no product
  claim depends on abnormal or stale column results.
- Product-spec gate: product purity and capacity are checked against documented
  specifications from latest stream CSV; nonzero product flow or clean block
  status is insufficient.
- Product/recovery pooling gate: compatible product-bearing, solvent-bearing, or
  waste-recovery streams are pooled before polishing or treatment unless a
  source or safety/equipment reason justifies separate handling. Preliminary
  cleanup should reuse existing finishing or regeneration units when feasible.
- Product property-method gate: component IDs, binary relative volatility, and
  property-method choices are verified before product-purity claims. Polar or
  aqueous finishing sections need activity-coefficient comparison and
  binary-parameter audit unless the document justifies another method.
- Separator-rigor gate: final separator block types are enumerated and compared
  with a whitelist from the document and user request. Any `SEP`, `SEP2`, or
  shortcut flash outside the whitelist fails; if the active user request forbids
  `SEP`, no whitelist or placeholder exception may keep it. For every removed
  `SEP`/`SEP2`, the audit must show the target ledger and the physical unit that
  realizes it, including key-component outlet, recovery/purity target, live
  Design Spec/Calculator variable when needed, and same-run stream evidence.
- User-forbidden separator gate: when the user says `SEP`/`SEP2` is not allowed,
  no forbidden `SEP`, `SEP2`, or `SEPARATOR` block may appear in the promoted
  exported input. If the user states the full flowsheet may not contain `SEP`,
  there is no membrane/proxy exception; the text audit must require zero
  `BLOCK ... SEP`, `SEP2`, and `SEPARATOR` entries. The audit command must exit
  nonzero when forbidden blocks remain, and no product, conversion, or recycle
  metric may override this failure.
- Delivery gate: delivery text matches the requested artifact policy. If source
  text is requested, Markdown/LaTeX sources plus rendered PDF exist and are
  synchronized. If PDF-only text is requested, human-readable Markdown, TXT,
  DOCX, and TEX are absent from the shipped package. In all cases, the PDF was
  compiled from current claims, page-rendered, and checked for missing text,
  table overflow, stale recycle values, stale pressure-equipment claims,
  mojibake, and question-mark replacement.
- Professional-source-file gate: competition or production packages must include
  the source files for every professional-software result they claim. Aspen
  simulations/optimizations need openable Aspen source files and exported inputs;
  drawings need editable drawing sources plus required PDF views; HAZOP, energy
  integration, economics, equipment design, and 3D layout need the native files
  from the software used or an explicit deferred/not-started label. A rendered
  PDF, screenshot, CSV, or JSON summary is not a substitute for the native source
  when the rubric asks for source files.
- Audit-command gate: the command used for promotion must fail when hard gates
  fail. Do not accept a wrapper that merely writes `passed=false` JSON and exits
  successfully. Named regression fixtures are the exception: they must return
  successfully only when the expected failure gates are present, and fail if the
  regression unexpectedly passes or fails for unrelated gates.
- Authority-manifest gate: multi-branch deliveries identify one current hard gate
  and accepted scaffold, mark older branch audits historical or diagnostic, and
  search generated reports/PDF text for stale branch labels before handoff.
- Portable-production gate: if another-computer use is requested, the package
  contains generic tools, templates, case evidence, project-specific scripts,
  install/verify commands, a relative manifest, and README statements about what
  is generic or case-specific and where failed runs write logs. Keep the
  PDF-only process delivery package separate from the broader skill/production
  package: process delivery may contain Aspen/CSV/JSON evidence plus PDFs, while
  skill/tool packages may contain Markdown instructions because the skill itself
  is Markdown.
- Evolution gate: candidate generation additionally requires the central
  strict lineage eligibility receipt. Relaxed or unassessed history stays
  audit-only; project-specific facts stay in the project package.

## Final Audit Commands

Use project-specific filenames, but keep this shape:

```powershell
Import-Csv .\Full_*_block_status.csv |
  Where-Object { $_.blkstat -notin @('', '0') -or $_.blkmsg }

Import-Csv .\Full_*_stream_results.csv |
  Where-Object stream -in @('<column-feed>','<target-product>','<recycle>','<heavy-or-waste>') |
  Select stream,temp_C,pressure_bar,mole_flow_kmol_h,mass_flow_kg_h,mol_<key-component>

rg -n "BZCIRC|EBCIRC|RYIELD|RSTOIC|REQUIL|RGIBBS|RCSTR|BLOCK .* SEP\b" .\Full_*_after_run.inp
rg -n "^BLOCK\s+\S+\s+(RYIELD|RSTOIC|RPLUG|RCSTR|REQUIL|RGIBBS|SEP\b|SEP2|FLASH2|FLASH3|DECANTER|RADFRAC|DSTWU|ABSBR)" .\Full_*_after_run.inp
rg -n "^\s*REACTIONS\s+\S+\s+(POWERLAW|LHHW)\b" .\Full_*_after_run.inp
rg -n "^\s*(CALCULATOR|DESIGN-SPEC|SENSITIVITY|OPTIMIZATION|REGRESSION|DATA-SET|PROFILE-DATA)\b|READ-VARS|WRITE-VARS|EXECUTE BEFORE|EXECUTE AFTER|VARY " .\Full_*_after_run.inp
rg -n "^\s*BLOCK\s+\S+\s+IN=.*OUT=" .\Full_*_after_run.inp
rg -n "\b(REC|SOLV|RETURN|NOCT|HEAVY|PURGE|VENT|WASTE)\b" .\Full_*_after_run.inp .\*_audit.json
rg -n "BLOCK .* HEATER|PRES=0|BLOCK .* COMPR|BLOCK .* PUMP|BLOCK .* VALVE" .\Full_*_after_run.inp
rg -n "terminal_tail_operation_check|terminal_tail_operation_results|post_pressure_terminal_check" .\*_audit.json .\*_audit.md
rg -n "external recycle estimate|boundary recycle|seed stream|stale main model|documented engineering placeholders|RStoic" .\*.md .\*.tex .\*.json .\*_pdf_text.txt
rg -n "authority manifest|current hard gate|historical.*audit|accepted scaffold|stale branch|diagnostic only" .\*.md .\*.tex .\*.json .\*_pdf_text.txt
rg -n "RPLUG|POWERLAW|LHHW|RADFRAC|SEP2|<target-product>|<tail-gas>|<recycle>|<treatment-block>" .\*_pdf_text.txt

Get-ChildItem .\full_delivery\failed_run_artifacts -ErrorAction SilentlyContinue

pdfinfo .\*delivery*.pdf
pdftotext -enc UTF-8 .\*delivery*.pdf .\pdf_check.txt
pdftoppm -png -r 150 .\*delivery*.pdf .\render\page
rg -n "\?\?\?\?|\x{FFFD}|stale branch|old authority|seed stream|HEATER PRES=[^0]|SEP2" .\pdf_check.txt
Get-ChildItem -Recurse -File |
  Where-Object { $_.Extension.ToLowerInvariant() -in @('.md','.txt','.docx','.tex') -or $_.Name -like '_qa_*' -or $_.Name -like '_render_*' }
```

For scriptable audit wrappers, add a second-level status check after JSON
creation:

```powershell
$audit = Get-Content .\results\current_audit.json -Raw | ConvertFrom-Json
if (-not [bool]$audit.passed) {
  $gates = @($audit.failures | ForEach-Object { $_.gate }) -join ", "
  throw "Audit hard gates failed: $gates"
}

$regression = Get-Content .\results\regression_audit.json -Raw | ConvertFrom-Json
$actual = @($regression.failures | ForEach-Object { $_.gate })
if ([bool]$regression.passed -or
    $actual -notcontains "terminal_boundaries" -or
    ($actual -notcontains "post_pressure_terminal_check" -and
     $actual -notcontains "terminal_tail_operation_check")) {
  throw "Regression fixture did not prove the expected topology leak."
}
```

## Terminal Tail Operation Configuration

Prefer the general gate for new projects and keep the old post-pressure gate for
regression compatibility:

```json
"terminal_tail_operation_check": {
  "enabled": true,
  "source_block_types": [
    "RADFRAC", "BATCHSEP", "MULTIFRAC", "FLASH2", "FLASH3", "DECANTER",
    "EXTRACT", "ABSBR", "RCSTR", "RPLUG", "RYIELD", "RSTOIC", "REQUIL",
    "RGIBBS"
  ],
  "tail_operation_block_types": ["PUMP", "COMPR", "HEATER", "HEATX", "VALVE", "FSPLIT"],
  "max_tail_hops": 3,
  "allowed_terminal_outputs": [],
  "allowed_paths": [
    {
      "source_block": "CLIGHT",
      "tail_blocks": ["K202", "EPRP", "FPRP"],
      "terminal_outputs": ["PRPSALE", "PRP2REC"],
      "boundary_type": "sale_and_controlled_reuse",
      "reason": "Cooled and split propylene recovery with sale and controlled reuse boundaries."
    }
  ]
}
```

Minimum regression set:

- Fail `RADFRAC -> COMPR -> terminal`.
- Fail `FLASH2 -> PUMP -> terminal`.
- Fail `RPLUG -> HEATER/PUMP -> terminal`.
- Pass source -> tail operation -> nonterminal recycle/treatment consumer.
- Pass source -> tail operations -> exact configured sale, treatment, fuel,
  purge/waste, external regeneration, or controlled-reuse path.
