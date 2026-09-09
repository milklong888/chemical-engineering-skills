# Aspen Plus Operation Graph

This graph is for mechanical Aspen actions. It assumes an upstream skill has
already chosen the process target and acceptance gates.

## Node Routing

| Node | Call When | Minimum Evidence |
| --- | --- | --- |
| `case-io` | Need to create, open, import, export, rename, or verify `.inp/.bkp/.apwz` | Source path, generated path, reopen/export proof; query `case_io.import_export` |
| `component-property` | Need component IDs, aliases, property method, phase behavior, BIP/property checks | Component list, property method card, warning/property notes; query `component_property.components_method` |
| `block-stream` | Need to create or reconnect blocks/streams | `FLOWSHEET` lines, stream IDs under Aspen length limits, connection map; query `block_stream.connectivity` |
| `reaction-card` | Need PowerLaw/LHHW/RStoic/RCSTR/RPLUG reaction setup | Reaction set card, stoichiometry, phase, basis, unit ledger; query reaction-family graph nodes such as `reaction.powerlaw.overview`, `reaction.lhhw.*`, or `reaction.rstoic.overview` |
| `equipment-card` | Need heater, pump, compressor, valve, HeatX, flash, split, column, or reactor card values | Block card, physical role, pressure/temperature/phase consistency; for heat-pump/VRC compressor work prove vapor-rich suction, no wet-compression error, downstream pressure propagation, and separated compressor-work/thermal-duty evidence; for HeatX prove Design/Rating/Simulation mode, specified side/variable, pressure drops, feed/outlet roles, and after-run area/duty; for RPlug query `rplug.geometry`, `rplug.temperature`, `rplug.catalyst` as applicable |
| `calculator` | A live stream value must write another set point or feed/makeup/draw | `DEFINE`, read/write variables, execution point, stale-value audit; query `calculator.define_sequence` |
| `sensitivity` | Need to bracket a physical variable before targeting | Varied variable, bounds, sampled results, failed-run handling; query `sensitivity.vary_tabulate` |
| `design-spec` | One scalar target must be met by one physical degree of freedom | Target, manipulated variable, bounds, residual/status, same-run evidence; query `design_spec.define_vary` |
| `optimization-regression` | Need constrained objective optimization or parameter fitting | Objective/parameters, constraints/bounds, residuals, validity range |
| `run-export` | Need Aspen run and authority exports | `Run2` status, block status CSV, stream results CSV, after-run `.inp`; query `run_export.evidence` |
| `delivery-qa` | Need final Aspen package or PDF verification | Exact delivery file reopen/run proof, `.his` Run Status all-zero proof, stream/block product evidence, target-version compatibility evidence when a target version is named, hashes, and file list |

## Manual Graph Queries

Before editing high-risk cards, run:

```text
python scripts/query_manual_knowledge.py <node-or-keywords>
```

The public `references/manual_knowledge_graph.json` is a local-help ingestion
contract with no commercial manual body or historical tested cases. If the
user supplies a qualified local graph, record its queried IDs, version and
source locations. Otherwise search the legally installed Aspen help using
`scripts/search_aspen_help.py`; absent local nodes are not evidence of missing
physics and cannot be replaced by invented card defaults.

The following terms are search hints, not a promise that public graph nodes or
private V10 source chapters are bundled.

| Operation Need | Query |
| --- | --- |
| LHHW reaction card | `lhhw` |
| LHHW Arrhenius and activation energy | `lhhw rate_con` |
| LHHW driving force constants | `lhhw dforce` |
| LHHW adsorption denominator | `lhhw adsorption` |
| Reaction phase, pressure/concentration, and rate basis | `lhhw units` |
| PowerLaw kinetic reaction | `powerlaw kinetics` |
| RStoic conversion/extent reactor | `rstoic` |
| RYield fixed yield reactor | `ryield yield inert normalization atom balance` |
| RPlug catalyst basis for `CAT-WT` rates | `rplug catalyst` |
| RPlug geometry and pressure drop | `rplug geometry` |
| RPlug specified temperature or heat boundary | `rplug temperature` |
| Component list and property method | `component-property` |
| Block/stream connections | `block-stream connectivity` |
| HeatX shortcut design or missing area warning | `heatx shortcut design area specification` |
| Calculator variable sequencing | `calculator sequence` |
| Sensitivity bracketing | `sensitivity vary tabulate` |
| Design Spec target and Vary | `design-spec vary` |
| Aspen import/export packaging | `case-io` |
| Accepted-run evidence | `run-export` |
| Unseeded manual page | `python scripts/search_aspen_help.py <terms>` |

## Standard Operation Sequences

Before invoking Aspen, choose the smallest reliable automation route. If Codex
exposes `mcp__aspenplus__*` tools, read
[aspen_mcp_invocation.md](aspen_mcp_invocation.md) and prefer them for bounded
open/run/get/set and supported simple block/stream actions. Use existing
COM/watchdog/export scripts whenever the operation needs exported authority
files, lock handling, long-run supervision, protected-copy repair, packaging, or
delivery QA.

### Create Or Modify A Case

1. `case-io`: query `case_io.import_export`, copy or import the authority
   `.inp`, and preserve a branch name.
2. `component-property`: query `component_property.components_method` and verify
   required components and property method.
3. `block-stream`: query `block_stream.connectivity`, add or modify flowsheet
   connections, and preserve a connection map.
4. `equipment-card` and `reaction-card`: set block/reaction cards from ledgers.
5. `run-export`: query `run_export.evidence`, run, export after-run input,
   stream results, and block status.
6. Return evidence to the upstream flowsheet skill for gate audit.

### Add A Reactor Or Replace A Reactor

1. Confirm upstream target ledger and source-to-card unit ledger. For kinetics,
   require a per-parameter chain: literature/source value -> source units ->
   conversion formula -> Aspen card value -> exported-card verification. Query
   the reaction-family graph nodes before selecting Aspen card fields.
2. `reaction-card`: create only the frozen source-model mapping supplied by the
   upstream ledger. Do not patch old kinetic constants or simplify a source rate
   law to fit a familiar card. If the requested standard card cannot express a
   reversible driving force, LHHW denominator, total-pressure multiplier,
   explicit temperature power, or deactivation term, stop with a custom/user-
   kinetics blueprint or a blocked-operation report. For LHHW, query
   `reaction.lhhw.overview`, `reaction.lhhw.units`, `reaction.lhhw.rate_con`,
   `reaction.lhhw.dforce`, and `reaction.lhhw.adsorption`.
   For PowerLaw, query `reaction.powerlaw.overview`. For RStoic, query
   `reaction.rstoic.overview` and keep it outside the kinetics gate unless the
   upstream authority explicitly requested a conversion/extent surrogate. If
   an RStoic block exports `SERIES=YES` or the UI "reactions occur in series" /
   "反应连续发生" option is selected, verify the same block has at least two
   numbered `STOIC` reactions; one-reaction RStoic blocks must omit
   `SERIES=YES`.
3. `equipment-card`: set reactor type, phase, dimensions/volume, catalyst basis,
   temperature/pressure, and pressure drop. For RPlug, query
   `rplug.geometry`, `rplug.temperature`, and `rplug.catalyst` when relevant.
4. `sensitivity`: bracket physical variables such as length, volume, residence
   time, temperature, pressure, feed ratio, or catalyst amount.
5. `design-spec` or `optimization-regression` only after a feasible bracket.
6. `run-export`: prove conversion/selectivity and downstream gates in the same
   accepted run. For RStoic cases, run or reproduce the
   `check_rstoic_series.py` scan on the accepted after-run `.inp` and include
   violations, if any, in the gate report.

### Add Calculator And Design Spec

1. `calculator`: query `calculator.define_sequence`, define every read variable
   and write variable, and choose execution point before the consuming block.
2. Audit circular dependencies and stale/locked values.
3. `sensitivity`: query `sensitivity.vary_tabulate` and bracket the manipulated
   variable when possible.
4. `design-spec`: query `design_spec.define_vary`, set target expression,
   manipulated variable, lower/upper bounds, tolerance, and convergence block.
5. If the spec reports bound contact after a reasonable bound expansion, compare
   live stream results with the spec target. When the physical result is feasible
   or already met, inspect the actual Vary data-tree/COM path, units, current
   value, and `BASIS_*` or equivalent input node before changing any target.
6. `run-export`: export cards plus final residual/status and downstream streams.

### HeatX Shortcut With Complete Inputs

When a source requires process heat exchange but does not provide exchanger
geometry, do not leave HeatX as an empty rating/area case. Use a process target
such as outlet temperature, specify hot/cold feeds and outlets, explicit
pressure drops on both sides, and enable T-Q/result export when available. A
complete shortcut-design HeatX is acceptable process-simulation evidence; a
missing-area warning or blank HeatX input is not deliverable.

### Design Spec Coupled To Tears

If Aspen reports `AFLSPC.23` or says a convergence loop was automatically
extended to cover a tear loop, inspect whether a Design Spec varies an upstream
feed across a recycle or heat-integration tear. Before changing physical
targets, test explicit Design Spec nesting:

```text
CONV-OPTIONS
    PARAM TEAR-METHOD=BROYDEN SPEC-LOOP=OUTSIDE CHECKSEQ=NO
    BROYDEN MAXIT=<current-authorized-limit> WAIT=<current-authorized-wait>
```

This is a convergence-layer repair only. Accept it only if the exported input
preserves the card, the exact BKP/APW reopen `.his` has zero warnings/errors,
and all upstream product, pressure, no-SEP, property-method, reactor, and
hydraulic gates still pass.

### Replace SEP-Like Boundary With Physical Separation

1. Upstream skill chooses the physical separation method and target components.
2. `equipment-card`: create flash/decanter/absorber/column/extractor/membrane
   surrogate or rigorous block as appropriate.
3. `component-property`: verify phase/property support.
4. `sensitivity`/`design-spec`: target recovery, purity, solvent rate, reflux,
   stage, pressure, or purge using live feed inventory.
5. `run-export`: prove source block status, product/recovery streams, and
   terminal-boundary classification.

### Final Package And PDF

1. For Aspen `.bkp/.apw/.apwz`, run `delivery-qa` before reporting a final
   candidate: reopen the exact candidate without model edits, run it, force
   `.his` generation, parse Run Status Results -> Summary of Simulation Errors,
   and scan the same raw `.his` for actual problem lines such as `* WARNING`,
   `WARNING IN THE`, `SEVERE ERROR`, `ERROR IN THE`, terminal errors, or
   `CHECK THE RUN STATUS`.
2. Use the canonical evidence checker and the chemical expert's
   `STRICT_ACCEPTANCE_AND_LEARNING.md`: every named row and column of the
   source-verified version/format schema must be present and all-zero.
   Unknown/incomplete schema, any nonzero count, or any actual problem line in
   the current raw `.his` quarantines the candidate. Product flow, purity,
   `BLKSTAT=0`, and Required Input completeness cannot override this criterion.
3. After the Run Status first criterion is all-zero, verify product, impurity,
   recycle, stream, and block gates on the same accepted candidate.
4. Copy the accepted Aspen file to the user-facing delivery path, hash it,
   reopen that copied file with no edits, rerun the Run Status first criterion,
   and record the final `.his` plus after-run `.inp/.bkp` evidence.
5. If the customer target Aspen version is older than the local working version,
   add a target-version compatibility package. For V12 targets from V14, scan
   the exact `.inp` for V14-bound databanks, RadFrac `PARAM2`, optional V14
   column-internals export cards, UTF-8 BOM, and non-ASCII path/comment hazards.
   Treat local newer-version import/run as regression evidence only; actual V12
   open/run remains the target-version authority.
6. Compile report from synchronized source text.
7. Confirm the PDF/report contains stepwise kinetics ledgers and honest
   surrogate/intrinsic-kinetics labels before calling the kinetics section done.
8. Render PDF pages to PNG and visually inspect wide tables, glyphs, headers,
   page numbers, equations, and file lists.
9. Extract UTF-8 text and grep for core terms, numbers, and "not completed"
   limitations.
10. Zip the package and verify the zip contains PDF, Aspen files, status files,
   stream/block CSVs, and metrics.

## Operation Guardrails

- Treat `.inp` cards, stream CSVs, block CSVs, and after-run exports as evidence;
  old screenshots or chat summaries are not authority.
- If a card syntax fix makes the case importable but the block fails, report it
  as diagnostic, not promoted.
- If a binary Aspen file cannot be reopened, keep the `.inp` and failure log as
  evidence and do not call the package complete.
- If a solver reaches the target by violating a downstream gate, reject the
  operation and return the conflicting gate to the upstream skill.
- For failed or uncertain runs, capture Control Panel/history first and use a
  short watchdog probe. Do not spend a long convergence wait rediscovering a
  named bad card, dry stage, bound Vary variable, missing input, bad block,
  tear, sequence, or license/startup problem.
  A probe has done its job once the current limiting object is named. Before
  running broad Broyden/Wegstein or increasing MAXIT, verify from the latest
  Control Panel/history section, final sequence monitor, convergence tree, or
  exported input that no smaller card/path/spec repair remains.
- For reused after-run cases, prefer the last sequence monitor, last convergence
  block table, and Results Summary convergence tree over a naive first-error
  grep. Earlier Control Panel/history messages may describe already-cleared
  bounds or card errors; record them as history, not as the current repair
  target, when late convergence evidence points elsewhere.
- Classify Aspen automation state before waiting: COM/license/case-open startup,
  model input processing, or actual flowsheet convergence. A startup hang is a
  resource/automation blocker, not evidence that the model needs more MAXIT.
- Guard COM creation with an outer process watchdog for fragile runs. A timeout
  inside the same Python process may never execute if `Dispatch`, `DispatchEx`,
  `EnsureDispatch`, or event binding blocks. The watchdog must kill only its own
  child process tree and release only its own lock.
- If another run holds the global Aspen lock, continue static evidence work and
  script preparation, then poll briefly. Long passive waiting is not an
  operation. After one or two short polls, leave a queued-run note with the
  exact next command and stop condition instead of blocking the conversation.
- When COM is unstable, stop broad retries and preserve the last successful
  exported run as authority only if it already satisfies the upstream gates.

