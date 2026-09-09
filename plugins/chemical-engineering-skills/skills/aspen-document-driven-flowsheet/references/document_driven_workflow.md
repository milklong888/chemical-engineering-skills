# Document-driven flowsheets — on-demand engineering workflow

The current chemical expert's strict acceptance/learning policy overrides
historical numerical shortcuts. Read relevant sections only; shared operation
mechanics and Summary/history parsing belong to aspen-plus-operations.

## Priority Operating Defaults

- After building a flowsheet or materially changing process parameters/modules,
  apply `chemical-engineering-expert/references/PROCESS_EQUIPMENT_FEEDBACK.md`
  through `equipment-design-app`. Test same-candidate duties against equipment
  capability before claiming process reasonableness. Classify true physical or
  capacity conflicts separately from input/catalog/vendor-evidence gaps; use
  source-backed common-sense RAG for the mechanism and alternative. Where
  justified, compare exchanger parallel trains/sections, compression stages or
  other registered equipment/process changes, record the change-offset, then
  rerun affected streams, recycles, pressure/heat networks, controls, products
  and utilities. Every physical device needs input/formula/rule/adjustment/rerun
  traceability; a screening candidate alone is not a passed process gate.
- Property method comes first and then freezes. For every module, section,
  island, tower, reactor, recycle closure, Calculator, Design Spec,
  Sensitivity, or Optimization, select the method from the real component
  family, T/P window, expected phases, non-ideality, Henry/electrolyte/
  association/LLE/VLL needs, binary-parameter support, and transport-property
  needs. Once accepted, do not change it to fix convergence, product purity, or
  hydraulics. A property-method change is a major model mutation requiring a
  change-offset row, physical reason, rerun of affected evidence, and
  quarantine of old results.
- Use Aspen `Calculator`, `Design Spec`, `Sensitivity`, `Optimization`, and
  Regression/Data-Fit deliberately. Do not manually freeze a derived flow,
  split, recycle ratio, product draw, reactor severity, or makeup amount when a
  live Calculator/Design Spec can express the documented dependency and produce
  exported evidence. Bracket the feasible window with Sensitivity before strict
  Design Specs or Optimization.
- Default precision is a repair red line. Do not change default/global
  convergence precision, source/user-frozen tolerances, `CONV-OPTIONS PARAM
  TOL`, tower `TOL-SPEC`, balance tolerances, or product-spec tolerances to fix
  a case or make it look passed. Convergence aids may change initial estimates,
  tear location, solver method, damping, iteration limits, trace output, or
  Aspen-recommended local cards after Control Panel/history diagnosis. Any
  relaxed-precision experiment is diagnostic/quarantined and cannot be promoted
  as the accepted repair.
- Treat product purity, capacity, recycle closure, raw-material recovery,
  kinetics, property-method validity, pressure topology, and delivery evidence
  as physical gates, not numerical residuals to hide.
- Source-named duties must be non-empty. For every reactor, converter,
  absorber, washer, tail-treatment unit, separator, or polishing block that the
  source/taskbook names as doing work, prove from the same after-run export that
  the documented key component or pollutant enters the unit, the intended
  reaction/separation/treatment changes it, and the outlet fate is classified.
  A block that exists, converges, or has `BLKSTAT=0` is not accepted if its
  inlet duty is zero or was bypassed by an upstream boundary.
- A stream name such as `REC`, `RECYCLE`, `GASREC`, or `SOLVREC` is not
  recycle-closure evidence by itself. For any source/taskbook full-flow claim,
  inventory every recycle, purge, makeup, solvent, vent, and waste intent and
  compare it to exported block connectivity. A recycle row is closed only when
  the stream returns to the documented upstream mixer/unit through any required
  splitter, purge, pressure device, or tear/convergence setup, or when the
  change-offset table explicitly marks it as an open boundary/blocker.
- For a difficult closed recycle, tune the equivalent open-boundary/open-loop
  case first and record the accepted recycle outputs. When reconnecting the
  loop, seed tear streams and, if early downstream blocks fail before the loop
  settles, also seed key intermediate streams from the accepted open-loop or
  previous closed solution. Do not promote the closed case only because the
  open-loop case passed; rerun the exported closed connectivity and gates.
- Separate gates into Aspen inherent gates, source/taskbook gates, and physical
  common-sense gates, with fresh user adjustments recorded as an overlay in the
  change-offset table. The weak point is usually incomplete source/taskbook
  reading, so run the two-pass source gate before model mutation and again
  before final delivery.
- A capacity/purity-passing process branch is not source-complete by itself.
  Before calling a document-driven flowsheet accepted, run a source-complete
  topology audit against the source/taskbook: feed pretreatment and impurity
  waste, reactor outlet cool/flash/quench duties, recycle/vent/purge branches,
  required product-stage count, inhibitor/additive feeds, byproduct/heavy/
  wastewater/fuel/utilities boundaries, and named preheaters or auxiliaries.
  Missing official units or terminal streams fail the source/taskbook gate even
  when product metrics and block statuses pass.
- When a repair changes upstream stoichiometry, reaction topology, or a source
  boundary stream, revalidate all downstream surrogate reactor and treatment
  keys. For `RStoic`, `RYield`, `REquil`, `RGibbs`, or simplified treatment
  blocks, compare key-reactant availability, stoichiometric limits,
  conversion/extent basis, before/after load, and exported card text after the
  upstream change. Do not reuse an old conversion key merely because the
  downstream block still runs cleanly.
- A converged run is not accepted until it is physically plausible and portable.
  Final Aspen files must pass migrated-path reopen/start-run evidence, and
  final `.bkp` files may be promoted only after the accepted run has completed.
- If the user cares about original PFD graphics, layers, a starter template, or
  block/stream size and arrangement, treat layout preservation as a delivery
  authority. `.inp` branches may support diagnosis, card comparison, and field
  discovery, but final promotion must be a COM/GUI-preserving repair applied to
  the original `.bkp/.apw`, followed by a no-mutation reopen/run/export proof.
  Record this in the project change-offset table before replacing the
  user-facing case.
- Aspen cases with USER subroutines are not portable as `.bkp` alone. If a
  native Aspen reaction card cannot exactly replace the USER model, deliver a
  package with the post-run `.bkp`, exported `.inp`, compiled same-version
  DLL, `DLOPT`/`aspfiles.def` loader files, source/audit evidence, and a
  clean migrated-path reopen/run/export test. A root `DLOPT` that points to
  `.obj`/source files is a compiler-dependent candidate, not a no-compiler
  delivery.

## Authority First

Before model mutation, script mutation, route reversal, or delivery claim:

1. Read project instructions (`AGENTS.md` or injected workspace rules).
2. Read the active change-offset table, current status note, latest static and
   dynamic audits, and kinetics/freeze ledgers.
3. Read or create the source/taskbook gate ledger from
   `references/source_taskbook_and_gate_protocol.md`; include user adjustments
   and unresolved source gaps before Aspen edits.
4. Treat latest local authority files as stronger than old conversation memory,
   old branches, or the original report text for approved deviations.
5. Reopen the original design book/report only for the specific source check
   needed by the next edit.
6. Update the change-offset table before confirmed deviations in reaction
   network, reactor type/card basis, separation block type, recycle topology,
   capacity scale, product target, tower specs, or pressure conventions.

Project recovery is always resolved from that project's current change-offset,
kinetics freeze and status. No named project or reactor's accepted state is a
global default; do not reopen an accepted decision without fresh authority.

## Optional Local Knowledge Gateways

Use the configured `{CHEM_WORKSPACE}` asset registry when the correct local
graph, standards method or equipment bridge is not obvious. Graph bodies,
commercial standards, private overlays and vector payloads are not included in
this public skill. Missing local data is unavailable, not a license to invent
a replacement index or project parameter.

Use the actual local unknowns router and method/evidence nodes. Record the
source version/hash/location and current applicability. Retrieval cannot
override the current change-offset table, source-freeze ledger or same-case
exports. Kinetics retains the source-equation/unit/conversion/card/export gate
whether or not a graph exists. Classify standards as direct reuse, method only,
software/vendor boundary or forbidden transfer before changing values.

## Operation Boundary

This skill does not perform low-level Aspen mechanics when an operation contract
can be formed. Call `aspen-plus-operations` for case I/O, component/property
setup, block/stream edits, reaction cards, equipment cards, Calculator,
Sensitivity, Design Spec, Optimization/Regression, run/export, and delivery QA.

Use this contract:

```text
Operation goal:
Authority artifact:
Inputs and source units:
Property-method gate:
Source/taskbook gate:
Allowed changes:
Required evidence:
Stop condition:
```

Return from the operation layer only after it reports changed/generated files,
cards touched, run/reopen/export status, evidence files, and failed/deferred
operations.

## Operational Architecture

Default construction route:

```text
source route and change-offset table
-> source/taskbook gate and property-method freeze
-> reaction target ledger and kinetics freeze
-> process skeleton
-> yield/SEP scaffold
-> scaffold closure gate
-> reactor and separation islands
-> one-by-one full-flow replacement
-> pressure/HX network and stream-state audit
-> equipment realizability feedback and affected-process replay
-> full-flow run and final gate
```

1. Source-route, taskbook gate, and property-method pass.
   Extract feeds, products, reactions, recycle intent, capacity/purity targets,
   pressure levels, utilities, and separation duties. For each reaction, record
   stoichiometry, key reactant, provisional conversion/selectivity/yield window,
   basis, and evidence status. If no conversion is given, use literature values
   only as provisional bounded estimates, or use simple Aspen thermodynamic
   probes (`REquil`, `RGibbs`, flash) to bracket feasibility. Build the
   source/taskbook gate ledger with a direct extraction pass and a reverse
   checklist/search pass. Freeze property-method rows for every active module
   family before building or optimizing that module.

2. Kinetics freeze, three independent checks.
   Formal kinetics must close:
   `source equation/value -> source units -> conversion -> Aspen card units ->
   exact Aspen input -> exported verification`. Check with the freeze ledger, an
   independent conversion calculation/script, and an Aspen microcase/exported
   card. If any disagree, keep the reactor `blocked` or `provisional`. If no
   defensible kinetics exists, keep the formal kinetic claim blocked. A separate
   stoichiometric/yield/equilibrium scaffold may be built only when the current
   upstream method authorizes it, with its limitation explicit; never silently
   substitute it for a required kinetic model.

3. Process skeleton.
   Draw full topology before detailed equipment: sections, stream IDs, fresh
   feeds, products, waste/treatment, recycles, purges, pressure islands,
   heating/cooling duties, and interface streams. Mark each recycle/purge row
   as `closed`, `open_boundary`, or `blocked` before calling the skeleton a
   full-flow model.

4. Yield/SEP scaffold.
   Build a runnable full-process scaffold using non-kinetic reactors and
   `SEP/SEP2` placeholders. Each SEP represents a separation duty or train, not
   one field device. Use it to determine provisional conversions, split targets,
   recycle destinations, makeup flows, purge needs, pressure estimates, and
   product-capacity sensitivity.

5. Scaffold closure gate.
   Trace every valuable raw material, intermediate, solvent, entrainer, and
   useful gas into internal recycle, qualified product, justified purge/vent,
   treatment, wastewater, heavy residue, or blocked unknown. Add Calculator or
   Design Spec links only for documented scalar relations such as makeup flow,
   recycle ratio, product draw, recovery target, or purge ratio.

6. Reactor and separation islands.
   Replace scaffold duties by isolated islands with frozen inlet streams.
   Reactor islands keep the same duty and use formal kinetics only after the
   three-check freeze. Separation islands start from a target ledger, then choose
   the physical family from feed phase behavior and duty. For towers, call
   `aspen-tower-optimization-workflow`.

7. Replace islands into full flow.
   Reconnect one accepted island at a time, keeping same-version backups. If the
   run fails, read Control Panel/history before every fix attempt and again
   after the next run. Capture the first limiting message, affected block/spec/
   sequence/tear stream, and the later message after the fix. Classify syntax,
   property, feed inventory, convergence, pressure topology, recycle
   initialization, or over-tight target from those messages instead of guessing
   from final stream numbers alone.

8. Pressure, heating, and stream-state audit.
   Add pressure and heat network deliberately: gas pressure rise uses
   compressors, liquid pressure rise uses pumps, letdown uses valves, and
   thermal-only heaters must not hide pressure changes. Call
   `aspen-pressure-pfd-delivery` for pressure/PFD/package issues. If the active
   project authorizes a pressure convention, record the source, units and
   physical basis. Distinguish outlet-pressure ratio from pressure-drop fraction;
   derive current losses from the authorized method and same-duty evidence.
   There is no universal liquid/gas exchanger pressure ratio.

9. Full-flow run and final gate.
   Close recycles one at a time using scaffold-derived tear estimates. Run short
   Control Panel probes before broad solver waits. Final acceptance requires
   same-version evidence for input completeness, block/calculator/spec status,
   material balance, kinetics or conversion/selectivity, physical separation
   replacement, recycle closure, raw-material recovery, product capacity/purity,
   pressure topology, terminal-stream classification, and delivery integrity.
   Before final handoff, run the material-library final digest and delivery
   preflight: re-check heating, pressurization, pressure-drop conventions,
   pressure devices, tower pressure paths, stream-state jumps, recycle/makeup
   links, and same-version claims.
   Also run `references/open_run_readiness_protocol.md` and
   `references/delivery_portability_and_plausibility_gates.md`: the delivered
   case must reopen in a clean Aspen session, show Required Input complete,
   start a run without manual input, export same-version evidence after reopen,
   pass a migrated-path reopen/start-run check, and pass a physical
   plausibility ledger. Repeat the source/taskbook and property-method gate
   check against same-version exports after any late edit. A `.bkp` is final
   only if saved/exported after the accepted run and then reopened from the
   migrated path.

## Cross-Skill Routing

Open `references/skill_routing_graph.md` when more than one graph, skill, or
operation layer is involved. Short routing:

- `aspen-two-section-flowsheet`: explicit two-section or sectioned boundary
  contracts, cross-section stream validation, section-specific gates.
- `aspen-flowsheet-error-repair`: pure Aspen flowsheet error/warning repair,
  bad-block diagnosis, recycle nonconvergence, product-gate misses, and
  Control Panel-driven fix loops. Use it beside this process-authority skill and
  `aspen-plus-operations` before drilling into detailed references.
- `aspen-tower-optimization-workflow`: tower target freeze, `DSTWU` or
  `DSTWU-SKIP`, rigorous tower island steps, Design Spec/Vary reconnect, tower
  pressure evidence.
- `aspen-heat-pump-distillation-replacement`: boundary-preserving replacement
  of a RadFrac tower with empty-column heat-pump/VRC/MVR distillation using an
  external compressor, HeatX, flash, reflux split, Design Specs, and large
  section reconnect gates. Use this before mechanical Aspen edits whenever the
  user asks to convert, retrofit, or replace a tower by heat-pump distillation.
- `aspen-pressure-pfd-delivery`: pressure topology, compressors/pumps/valves,
  HEATER `PRES=0`, pressure/HX/PFD/PDF delivery.
- `chemical-equipment-selection-audit`: equipment sizing/selection reports,
  formula-family choice, EDR/SW6/Column Internals/vendor evidence, standards
  boundaries, reusable calculation scripts.
- `aspen-plus-template`: component/template generation through Aspen COM, not
  process-route repair.

## Hard Gates

- Property method first for every module, island, section, tower, reactor,
  pressure section, recycle closure, Calculator, Design Spec, Sensitivity, or
  Optimization. If the property row is not accepted, the module is
  `provisional` or `blocked`. After acceptance, the property method is frozen;
  changing it requires change-offset authorization and rerunning affected
  evidence.
- Gate taxonomy is mandatory. Track Aspen inherent gates, source/taskbook
  gates, and physical common-sense gates separately, with user adjustments as
  logged overlays. Control Panel/history is the first Aspen-inherent evidence
  for failures; source/taskbook ledger rows are the first evidence for official
  targets and restrictions; physical plausibility is the first evidence for
  converged-but-unrealistic models.
- Source/taskbook gates require two passes: direct extraction before model
  mutation and a reverse checklist/search verification before final delivery.
  If a taskbook row is unread, garbled, ambiguous, or missing, the affected
  Aspen claim is `provisional` or `blocked`.
- No invented kinetics. Never invent or copy `k`, `E`, `Exponent`, LHHW terms,
  adsorption constants, rate basis, concentration basis, catalyst basis, or USER
  settings without the freeze chain.
- No unapproved final `SEP/SEP2/SEPARATOR` for physical separation duties.
  Scaffolds may use SEP only as a labeled temporary separation duty.
- Default precision is untouchable during repair. Do not modify default/global
  tolerances or product/spec tolerances as a fix; diagnostic relaxed-precision
  branches stay quarantined and cannot be delivery evidence.
- Control Panel repeatedly on failed runs, recycle failures, bad blocks, and
  product gate misses. Before changing cards/specs/topology, read the first
  limiting Control Panel/history message; after the fix, read it again to prove
  the blocker changed or disappeared. Log the exact message and affected object.
- Historical cases and lecture examples transfer routes, field meanings,
  diagnostic order, and checklists only; values remain quarantined.
- Final delivery must be same-version: accepted case, static audit, dynamic
  audit, Required Input/Control Panel evidence, retained Aspen exports, and
  synchronized report/PDF/package claims.
- Final replacement must be complete. When a later branch supersedes a previous
  "current final" branch, update the project change-offset row, current status
  note, delivery manifest/file list, hard-gate default inputs, new-skill audit
  script/config, hydraulic/equipment evidence pointer, and final response
  together. Then run a stale-current scan for old branch labels near words such
  as `current`, `final`, `delivery`, `accepted`, and `submit`. Old branches may
  remain as history, but they must be explicitly demoted as historical evidence
  and cannot be the default target for gate scripts.
- Source-complete branches also require gate-script updates. If the repair adds
  a new mixer, splitter, tower, pretreatment block, inhibitor feed, or alternate
  recycle path, update the final-gate script/config to recognize the exported
  new connectivity before claiming pass; otherwise the old script may either
  miss required source units or falsely fail a valid repaired topology.
- Open-run readiness is the minimum delivery gate. A `.bkp`, `.apwz`, or `.inp`
  that opens with missing Required Input or needs manual entry before Run is not
  a runnable deliverable, even if an older branch once ran.
- Path portability is a delivery hard gate. Copy the exact final package to a
  fresh neutral path, reopen the migrated copy, check Required Input, start Run,
  export same-version evidence, and scan for stale absolute paths. If the
  migrated copy fails, the package is `blocked-portability`.
- Physical plausibility is a delivery hard gate. A converged case that violates
  source capacity, stoichiometric limits, conversion/selectivity windows,
  mass/key-component closure, recycle/makeup logic, phase/pressure/temperature
  sanity, duty signs/scales, or separation/recovery logic is
  `blocked-physical` or `provisional`, not accepted.
- `.bkp` promotion is post-run only. Do not call a `.bkp` accepted-runnable
  unless it was saved/exported after the accepted run, reopened cleanly, checked
  for Required Input/start-run, and verified again after path migration.
- Layout/template preservation is a delivery hard gate when requested. A clean
  `.inp`-roundtrip case is only diagnostic if it drops PFD layers, stream/module
  sizing, labels, or APW sidecar state. Promote the original-archive COM repair
  branch, not the text-import branch.

## Learning Log And Self-Evolution

Project audit events may record successes, failures, decisions and local
exceptions. They are not learning samples. Read `self_evolution_protocol.md`
and the expert's `STRICT_ACCEPTANCE_AND_LEARNING.md` before any candidate
review. A case-local relaxation, unknown lineage or descendant is excluded;
user-accepted completion does not clear this gate.

`scripts/self_evolve_skill.py` requires explicit user closure of the current
task revision and a complete eligible lineage before producing a candidate.
User macro principles use the governed user-instruction branch; technical/data
claims require appropriate strict result evidence. It never
writes a canonical rule. `log_aspen_experience.py` and
`record_process_slice.py` record audit-only local artifacts, with no-learning
and no-default-retrieval labels. Only independently strict, source-backed
mechanisms may enter a later human-reviewed promotion step.

## Output Standard

Lead with current engineering status and the decisive gate. Distinguish strict
pass, case-accepted-with-relaxation, provisional, diagnostic and blocked claims.
Link only the source/operation/run/product/flow-equipment evidence actually
needed for the requested stage. Preserve failures and unresolved source inputs;
never substitute output polish or a long list of generated files for acceptance.
Record current authority, affected consumers and the next scoped action.

Private prior entries and task baselines are not distributed; their historical
case numbers and success-only learning shortcuts are not public defaults.

