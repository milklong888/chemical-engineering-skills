# Aspen Workflow Playbooks

Use this reference when building a document-driven Aspen model from zero,
promoting a scaffold to rigorous islands, coordinating subagents, or deciding
which branch is the current authority.

## Contents

- Default from-zero build paradigm
- Execution-efficiency loop
- Reuse-first dispatch protocol
- Subagent scheduling protocol
- Authority promotion rules

## Default From-Zero Build Paradigm

Use this pattern when the user asks for a complete Aspen process, when only
documents exist, or when the inherited Aspen file is too unstable to repair
directly.

1. Route lock.
   Extract the route, feeds, products, reactions, recycle paths, and separation
   purposes from the current documents. Decide the active completion goal and
   write the initial authority note before creating Aspen inputs.

2. Full-process scaffold.
   Build the whole flowsheet first with yield or stoichiometric checkout
   reactors and shortcut separators. Include mixers, splitters, recycle returns,
   pressure changers, heat exchangers, purge points, product outlets, and
   waste/treatment boundaries. The scaffold finds capacity basis, stream naming,
   recycle topology, pressure islands, and tear-stream estimates. It is not final
   when strict kinetics or non-`SEP` separators are required.

3. Recycle initialization.
   Use the scaffold to generate initial values for recycle streams. Seed each
   recycle with realistic temperature, pressure, phase, total flow, and dominant
   key components. Add small labeled purges when a closed loop has no documented
   purge policy. Remove or relabel seed streams once the real recycle is
   connected.

4. Island extraction.
   Pull each reactor and separation sequence into an island with frozen inlet
   streams from the latest scaffold or full-flow export. Record inlet basis,
   target outlet function, candidate block types, unit/card conversions,
   warnings, exported input, stream CSV, and pass/fail. Islands may use temporary
   shortcuts only to isolate the next physical question.

5. Reactor upgrade.
   Replace one checkout reactor at a time with strict kinetic equipment such as
   `RPLUG` or `RCSTR` plus `POWERLAW`, `LHHW`, or a documented custom-rate
   surrogate. Prove the kinetic card in a micro-segment before reconnecting it.
   Tune operating temperature, pressure, residence time, catalyst amount, reactor
   volume, feed ratios, and recycle composition before changing sourced kinetic
   constants. For numeric conversion, selectivity, heat release, or outlet
   composition targets, run Sensitivity first; use Design Spec or Optimization
   only after the feasible region is known. Fit kinetic constants only through
   Regression/Data-Fit from primary data.
   Promotion checklist: target-window lookup; original full-flow yield and
   material-balance audit; one-reactor kinetic island; kinetic-card unit and
   reaction-set export; Sensitivity bracketing on a physical parameter; bounded
   Design Spec or Optimization only after bracketing; back-substitution into the
   full-flow case; retained solve/fit evidence; downstream product, recycle,
   pressure, terminal, warning, and material-balance gates from the same run.

6. Separation upgrade.
   When a case contains `SEP`/`SEP2`, first translate it into a separation
   target ledger: feed, key species, intended outlet, recovery/purity target,
   recycle or terminal destination, phase/pressure basis, and the live Design
   Spec or Calculator variable that should drive the split. Then implement that
   target with physical non-`SEP` equipment: flash or condenser for defensible
   vapor-liquid cuts, decanter or LLE/extraction for liquid-liquid cuts, RadFrac
   or equivalent columns for volatility cuts, extractive/azeotropic columns for
   difficult aromatics, absorber/stripper or low-temperature methanol wash with
   solvent recycle for gas cleanup, evaporators/vacuum flashes for
   concentration, and adsorption/membranes/PSA only when the source supports
   them. A non-`SEP` block still fails if the intended recovery outlet is zero,
   phase-infeasible, lacks the live target spec, or contaminates the upstream
   recycle.

7. Product finishing.
   For high-purity products, collect compatible product-bearing streams into one
   crude pool, remove noncondensables and gross phase contaminants first, then
   select the finishing method from phase behavior. If ordinary distillation
   gives dry columns, false cryogenic condensers, wrong-outlet products, or
   purity that depends on a bad block, test extractive, azeotropic,
   pressure-swing, LLE/extraction, absorber, evaporator, membrane, or PSA islands.
   Keep raw-material recycle, solvent recycle, product recovery, and waste purge
   as separate gates; do not send a valuable but contaminated product/solvent
   stream upstream merely to make the recycle loop look closed.
   When preliminary waste or purge cleanup creates a feed compatible with an
   existing finishing or regeneration unit, reuse that unit instead of creating
   a separate small tower train. Treat separate trains as diagnostic unless a
   safety, phase, contamination, or source requirement justifies them.

8. Solvent and entrainer closure.
   For extractive, azeotropic, or extraction sections, close the solvent loop
   inside the island before final promotion: product column -> solvent-rich
   outlet -> regeneration/recovery equipment -> purge/makeup -> cooler/heater or
   pressure equipment -> return to the solvent-using unit. Do not count a
   solvent-rich terminal stream as closure. Audit terminal outputs from the
   exported `FLOWSHEET` and allow only named product, recovery/treatment, purge,
   vent, or wastewater boundaries.

9. Reconnect and ramp.
   Reconnect upgraded islands back into the full flowsheet one at a time. Start
   with scaffold-derived tear estimates, run import/export/run/after-run and
   backup-reopen checks, then ramp recycle closure, reactor severity, separator
   recovery, and product specs gradually. Do not integrate several new kinetic
   and separation changes in the same run unless a clean intermediate backup
   exists.
   Before tightening a column spec, calculate feed key-component inventory and
   cap fixed draws or recoveries by what actually enters the island.

10. Final audit.
   Promote the newest case only after exported block and stream results prove
   the named primary goals, solvent/entrainer loops, and terminal boundaries.
   Historical branches, failed islands, and diagnostic sweeps remain evidence
   but must not become the accepted scaffold.

11. Authority promotion.
    Update exactly one authority manifest or status note with the accepted case,
    user-named gates, current hard blocker, promoted islands, rejected diagnostic
    branches, and the next module to attack. Never let an older, cleaner-looking
    diagnostic branch override the current accepted scaffold.

## Execution-Efficiency Loop

Use this loop before a long trial family, after three similar failures, or when
the user asks for faster construction.

1. Queue the next work.
   Write five fields: active hard gate, local critical-path action, parallel
   sidecar calls, expected evidence from each call, and stop condition.

2. Keep the main path local.
   The main agent owns topology edits, authority promotion, and full-flow
   reconnects. Do not block on a sidecar unless its result is needed for the next
   local command.

3. Parallelize independent evidence.
   Split source extraction, unit ledgers, property checks, separation-option
   screening, recycle tracing, and PDF/text audits into sidecars when allowed.
   Give each sidecar one inlet basis, one artifact target, and one output table.

4. Prefer probes over full rebuilds.
   Before editing the full case, run the smallest probe that can falsify a path:
   component identity, property method, feed inventory, phase split, product
   draw feasibility, recycle quality, or one-block island.

5. Stop repeated families early.
   If three trials fail for the same structural reason, stop the family and
   switch nodes: property data, candidate separation type, topology, source
   evidence, or built-in solve/fit setup.

6. Record the reusable lesson.
   At phase end, note the call pattern that saved time, the call pattern that
   wasted time, and the next default ordering. Promote only general patterns to
   the skill; keep chemistry and stream values in the case card.

## Reuse-First Dispatch Protocol

Use this protocol before creating any subflowsheet, island, recycle closure,
kinetic microcase, tower optimization, or low-level Aspen operation from zero.
It saves tokens and reduces contamination by separating reusable execution
experience from current-project process authority.
If the reuse-first dispatch record is missing, stop before spawning a fresh
subagent or creating a new island; do not proceed on an implicit cold start.

Default dispatch order:

1. Current/live subagent that already worked on the same family.
2. Recent Codex thread with the same project, unit family, hard gate, or artifact
   stem.
3. Handoff/authority/audit note in the project folder.
4. Exported Aspen branch, run script, sweep CSV, or probe directory.
5. Fresh subagent or cold-start island, only with a recorded reason.

Use this compact delta contract when resuming a prior dialogue or artifact:

```text
Reuse artifact:
What changed:
Current hard gates:
Values/specs quarantined:
Expected evidence:
Stop condition:
```

1. Search live conversation memory first.
   Use available thread/subagent tools before spawning new work. Query recent
   threads for the project name, route name, unit family, hard gate, and likely
   artifact stem. Read the best hit enough to learn its accepted basis, changed
   files, blocker, and reusable artifact. If a live or resumable thread already
   executed a similar task, continue that thread with only the delta: changed
   feed, changed target, new forbidden unit, new source evidence, or narrower
   audit. Do not ask it to re-extract the whole project.
   If an existing subagent is listed in the environment and its prior role
   matches the needed family, send it the delta contract before spawning a fresh
   agent. If a prior background thread is the best match, send a follow-up
   prompt to that thread and keep the main path working locally while it runs.

2. Search local execution artifacts second.
   If no compatible live thread exists, scan the current project folder for
   authority manifests, handoff notes, audit JSON, branch matrices, run notes,
   exported `.inp/.bkp/.apwz`, stream CSVs, sweep tables, scripts, and branch
   directories. Prefer the nearest artifact that already passed the relevant
   mechanical gate, even if its process assumptions are now rejected; mutate the
   artifact only after recording why the old assumptions cannot be reused.

3. Apply the contamination filter.
   Reuse only execution patterns: Aspen COM calls, card paths, convergence
   order, audit scripts, special-separation topology templates, recycle startup
   strategy, report structure, and known failure signatures. Do not reuse
   components, reaction routes, CO2 cleanup sections, solvent choices, split
   targets, kinetic constants, property methods, stream names, pressure levels,
   or product specs unless the current project document independently supports
   them. Any imported value starts as `candidate` evidence and must pass the
   source -> unit -> Aspen-card -> export ledger before promotion.

4. Decide whether to resume, mutate, or cold-start.
   Resume a live conversation when it has the needed local context and can work
   on a delta. Mutate a local artifact when the mechanical structure is useful
   but the old process basis is quarantined. Cold-start only when there is no
   compatible artifact, the artifact fails a hard gate that invalidates its
   mechanics, or the current document contradicts the artifact's core route.

5. Record the dispatch decision.
   In the authority manifest, run note, or branch audit, write: search terms or
   artifact paths checked, selected conversation/artifact, reusable part,
   quarantined part, delta sent or mutation planned, model/subagent size choice
   if any, and the exact stop condition. This record is mandatory evidence for
   later delivery claims.
   Use this stamp when no local project template exists:

   ```text
   Reuse-first dispatch record:
   Searched threads/subagents/artifacts:
   Selected reuse source:
   Reusable mechanics:
   Quarantined chemistry/specs/values:
   Delta contract:
   Cold-start reason, if any:
   ```

## Subagent Scheduling Protocol

Use subagents only when the user explicitly asks for subagents, delegation, or
parallel agent work. The main agent owns the active goal, the authority manifest,
and the final Aspen promotion decision.
This restriction governs spawning fresh subagents. Reusing or messaging an
already-listed subagent or background thread is part of the reuse-first gate,
provided old chemistry, values, components, and separation targets remain
quarantined until current-source ledgers re-authorize them.

Good subagent tasks are bounded sidecars:

- Source agent: extract route, reactions, kinetics, product specs, recycle
  statements, and missing data from DOCX/PDF/source files.
- Unit-card agent: build a source-value -> Aspen-card conversion ledger for
  feeds, kinetics, reactor sizing, separator specs, pressure, temperature,
  purity, and recycle rates.
- Island agent: build or audit one reactor or separation island and return
  exported input, block status, stream results, warnings, and pass/fail.
- Recycle agent: trace one recycle path from recovery outlet to upstream mixer,
  including phase, pressure equipment, purge policy, and key-component return.
- Solve-fit agent: propose Calculator, Design Spec, Sensitivity, Optimization,
  or Regression setup for a bounded target, including targets, variables,
  bounds, source data, and expected exported cards.
- Thermo/special-separation agent: compare property-method islands and propose
  extraction, extractive distillation, azeotropic distillation, pressure-swing,
  heat-pump distillation, absorber/stripper, evaporator/vacuum flash, membrane,
  or PSA routes with component identity, phase evidence, and BIP/regression
  status.
- Delivery agent: check Markdown/LaTeX/PDF text for stale claims, wrong authority
  branch, missing gate results, and outdated stream numbers.

Every subagent result is raw evidence until checked by the main agent. Before
using it in Aspen, require source path, source units, converted Aspen units,
destination card, card meaning, export evidence, and current-flow compatibility.
For island work, require the subagent to state whether its inlet basis comes from
the accepted full scaffold or from an older diagnostic branch.

Standard sidecar return format:

- `basis`: source file or exported case, inlet stream, date/version.
- `decision`: pass/fail/unknown and the recommended next action.
- `evidence`: exact file paths, stream/block names, converted units, and warnings.
- `limits`: assumptions, missing data, and when this result must not be reused.

Do not assign the immediate blocking task to a subagent if the main agent cannot
make progress without it. Keep tightly coupled Aspen edits local; delegate
document extraction, ledger construction, isolated island experiments, and
independent audits. When multiple subagents work in parallel, give them disjoint
write scopes or make them read-only.

