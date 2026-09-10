---
name: aspen-adaptive-generalization-loop
description: Build self-evolving Aspen Plus templates by tuning representative seed cases, converting manual knobs into Calculator, Design Spec, guard, inventory, root-selection, and classifier rules, batch-testing broad feed sets, and freezing evidence-backed generalized flowsheets. Use for Aspen biomass/syngas superstructures, recycle scale drift, ratio control, startup transients, multiple recycle roots, gasification, MEA, WGS, RWGS, hydrogen makeup, and multi-feed batch runs.
---

# Aspen Adaptive Generalization Loop

## 工作过程

当一个流程需要处理多种进料或负荷时，先固定物理边界、允许调节的变量和有代表性的测试范围，再用少量代表工况查清哪些量应随入口改变。优先从衡算、空速、回收和压力关系推导控制规律，分别落实为Calculator、Design Spec或有依据的分类规则，避免为每个原料名称另写一套流程。

操作模块执行受保护副本的试算，修复模块处理具体异常；结构或工况变更按[阶段调用规则](../chemical-engineering-expert/references/DESIGN_STAGE_ROUTING.md)重新检索和校核设备。规律要经过相反工况、边界工况及完整约定样本复跑，才能用于当前任务的模板交付。当前任务调参不等于共享自进化；只有用户确认结束后，才把符合严格来源条件的宏观原则和数据规律送入中央审查。

## Purpose

Use this skill when an Aspen island must accept many feedstocks or route cases without case-by-case hand repair. The target is a reusable template whose calculators, design specs, and classifiers adapt operating variables while preserving feed composition and process physics.

## Operating Contract

- In-task tuning and data capture support the current engineering objective;
  they are not authorization for cross-task self-evolution. At each delivery
  ask whether the task is finished or needs improvements. Only the user's
  explicit closure of the current task revision starts the central
  `EVOLUTION_LOOP.md`: macro `prompt_principle` or tested `data_pattern`.
  If the user reopens/adjusts the task, invalidate the old closure.

- Before any planning, edit, or Aspen run, read the compact
  `references/ERROR_MEMORY.md`. The default `scripts/query_error_memory.py`
  reads its compact guards without a historical database. Historical audit
  additionally requires a user-supplied, verified compatible
  `references/error_memory/index.json` and event files, not included here.
  Retrieve only the relevant incidents by project/theme in explicit audit mode,
  or by exact legacy ID/UID; do not load the whole legacy archive by default.
  Original incident labels remain preserved, while `legacy_unassessed` events
  are audit-only and cannot authorize current engineering or learning.
  When the user states or corrects a project engineering rule, persist it to
  the project authority first and treat it as authoritative for dependent
  work. If observed Aspen evidence, conservation, safety, or an immutable
  constraint conflicts with it, stop and report the exact conflict instead of
  silently substituting an agent-preferred rule.
- Close every newly discovered mistake as a project incident before affected
  work continues: record or version that incident, preserving prior
  evidence and duplicate-ID aliases, with trigger, mistaken
  behavior, invariant, executable detector, repair, regression test,
  authority, severity, and last-seen date. Also map the rule into the project
  authority or machine-readable gate. A verbal apology or chat-only reminder
  is not incident resolution. Shared memory/rule updates wait for user task
  closure; unrelated valid work need not stop for an unpromoted lesson.
- Read project authority files, current INP/BKP exports, reports, and run evidence before changing rules.
- Treat BKP as the promoted Aspen run basis. INP may support readable card audit and diffs, but it must not replace direct BKP open/run/reopen evidence.
- Treat manual tuning as candidate evidence only after current strict learning
  eligibility is established. A case-local relaxation and every dependent
  result or summary are audit-only and never training data, success cases,
  common parameters, default acceptance or promoted rules.
- Freeze scale as a vector of all independent fresh boundaries and component
  bases. Do not infer capacity from one headline feed or force the internal
  recycle inlet to equal fresh feed.
- Preserve material composition unless the process unit itself changes it by reaction or separation.
- Control only defensible variables: feed amounts, makeup utilities, reactor temperature, pressure within engineering bounds, duties, reflux, solvent rate, recovery targets, and initial guesses.
- Keep steam, water, solvent, MEA, oxygen, and hydrogen as explicit boundary or utility streams; never let them appear without a block, heater, pump, compressor, or makeup rule.
- Check Aspen status, bad blocks, design-spec convergence, product gates, boundary streams, utilities, exported evidence, and COM locks before accepting a template.
- For strict promotion and the default delivery contract, reject every candidate
  that has any control-panel or fresh-history
  warning/error. Require first run, unmodified BKP reopen/rerun, and direct run
  from the promoted delivery path to each report zero terminal errors, severe
  errors, errors, and warnings. Do not allowlist expected Calculator, Design
  Spec, inactive-branch, or zero-flow warnings; `INFORMATION` records remain
  evidence but are not warnings.
- Keep an immutable `strict_baseline` before tuning. Record explicit case-local
  relaxation separately under `relaxation`, and propagate that exclusion through
  the complete `lineage` of results, summaries and proposed rules. Such a case
  may continue within its current authorization, but may never be relabeled as
  a strict pass or fed into self-evolution. Current source/schema corrections
  are evidence corrections, not automatically relaxations. Before any reusable
  promotion, use the central `evaluate_learning_eligibility.py` contract and
  current complete strict source/engineering validation; an old `verified`
  incident label or later rewritten summary cannot satisfy or bypass this gate.
- Close conversion/selectivity across every physical outlet phase, and require
  transient guards to return to their source floors at accepted steady states.

## Generalization Workflow

This workflow can tune and verify templates inside the user's current project.
Project-local iteration and delivery are not cross-task publication. References
below to shared laws, learning evidence or reusable promotion require explicit
current-revision closure and the central eligibility gate before any shared
candidate generation; strict local runs alone do not open that gate.

1. Freeze the island boundary, allowed manipulations, current strict baseline,
   acceptance gates, and evidence files. Separate any authorized case-local
   relaxation and all of its descendants from this generalization population.
2. Freeze a representative seed panel from the project's feature coverage and
   acceptance contract, covering applicable route, product target, composition,
   contaminants, pressure, and wet/dry extremes. Historical 20-case panels are
   examples, not a universal count or permission to omit required coverage.
3. Tune seed cases through the shared native-tool route and log every setting
   and failed attempt; manual intervention is for diagnosed setup/repair, not
   the default point-by-point numerical search. Only cases
   eligible under the unchanged current strict baseline may support learning;
   relaxed case-local work remains in a separate audit ledger.
4. Convert each seed into scalar features such as H2/CO, H2O/CO2, H2S/CO2, CO2 load, water load, pressure gap, route, product target, and gasifier branch.
5. Classify failures before patching: missing rule, wrong class threshold, physical infeasibility, template/card bug, numeric initial guess, or COM/file issue.
   For recycle cases, also classify wrong-root selection, boundary-scale drift,
   feedback runaway, and startup-only transient failure.
6. From eligible strict evidence, draft the smallest generalized rule that
   explains a failure class by features, not feedstock names. Do not derive
   reusable lessons from any relaxed case-local ancestor.
7. Implement the rule as a Calculator, Design Spec, sensitivity bracket, or external pre-run classifier.
8. Build an initial unified template and batch-test the remaining cases.
9. Rerun failed and affected classes after each patch; full reruns are for release candidates.
   Record a root fingerprint for every accepted and rejected recycle run.
10. After broad coverage is achieved, simplify overlapping logic and freeze grouped templates plus evidence.

## Incident Reflection Gate

1. Stop dependent edits, delegation, promotion, and completion reporting when a
   new mistake or user correction is identified. Unrelated accepted work may
   continue only when it cannot consume the disputed artifact or claim.
2. Read the short memory router, then use `scripts/query_error_memory.py --audit`
   with the current project and trigger. Preserve exact original incident bytes;
   record the current recurrence in the project audit. Update shared atomic
   memory/index only in post-closure evolution, using source-message identity
   so replaying a correction cannot increase its weight twice.
   Repeated reports change retrieval priority, not technical truth or learning
   eligibility. Resolve ambiguous legacy IDs by title/locator/UID.
3. Persist the project-specific consequence in the project authority and name
   the affected mother templates, pointers, runners, variables, evidence, and
   acceptance gates.
4. Implement an executable preflight or post-run detector wherever the mistake
   can be recognized mechanically. Human memory is not an acceptance gate.
5. Prove the repaired detector on the failing example and one contrasting
   control before resuming the dependent workflow.

For mother-template replacement, the detector must resolve the same authority
pointer and package-relative files as the production entry point and compare
their hashes with the launch manifest. A sidecar adapter or isolated smoke is
diagnostic evidence, not a completed replacement.

For full-chain reporting, count only terminal evidence records. Keep planned
leaves, Stage-2 terminal classifications, Stage-3 attempts, strict Stage-3
passes, and final Q1-Q4/economic aggregates as separate counters.

## Two-Phase Agent Work Pattern

### Phase 1: Prebuild And Generalize

Goal: build one reasonable, generalized, industrially defensible Aspen template
that passes the complete representative panel frozen by the current project.

1. Select qualifying but deliberately non-identical training streams sufficient
   for the frozen coverage contract. Record applicable feature columns before
   running, such as scale, H2/CO, CO2, H2S, H2O, inert load, pressure, phase
   state, product target, and route; do not inherit a historical panel count.
2. Pick one seed case and manually or randomly tune it only to discover likely control locations. Treat this as exploration, not a template.
3. Convert discovered knobs into Calculator, Design Spec, Sensitivity bracket, classifier, or bounded initial-value rules.
4. Build the first template from those rules and run the remaining training cases.
5. For every bad or unreasonable result, classify the cause before editing: bad control scheme, missing control, wrong class boundary, physical infeasibility, missing separation/equipment, numeric setup, or file/COM issue.
6. If a missing unit operation or structural patch is proposed, prove that it is industrially reasonable and that simpler control of existing equipment cannot meet the duty within bounds.
7. If the response has no obvious rule, add cases to expose the pattern. If an obvious feature relationship exists, such as flow scale versus reactor space time, force a control-law search before adding equipment.
8. When a failure class meets the project's frozen recurrence/coverage trigger,
   investigate its feature pattern and propose a generalized rule or show why
   the feature is irrelevant. Historical occurrence counts are not thresholds.
9. After any structure or algorithm correction, rerun affected cases and then
   the full frozen representative panel before promoting the template.
10. Freeze the template only with BKP evidence, after-run INP, stream/block tables, batch results, rejected-candidate notes, and a concise algorithm report.

### Phase 2: Process And Evolve

Goal: run all production cases in order, using low-judgment workers for execution and escalating only anomalies.

1. The main agent defines the active template version, case queue, output table schema, acceptance gates, anomaly thresholds, and stop conditions.
2. Low-intelligence workers run cases sequentially or in safe parallel only through approved scripts. They extract results to tables and do not invent process fixes.
3. Each worker returns case id, template version, input features, run status, bad blocks, warning/error counts, product gates, utility metrics, boundary streams, and raw evidence paths.
4. If a result fails gates or looks unreasonable, pause the processing queue and escalate with a compact anomaly packet.
5. The main agent classifies whether the anomaly supports a strict generalized
   repair or an authorized case-local action. Only eligible strict evidence may
   re-enter Phase 1; relaxed case-local outcomes and all derived summaries remain
   excluded from shared template/rule changes and success-case collections.
6. In processing mode, accepted previous results remain pinned to their template version. Do not silently rewrite earlier results unless the new rule exposes a global invalidation that the user accepts.
7. Continue the queue from the upgraded template version after the anomaly clears.
8. Accumulate anomaly audit evidence separately from eligible strict success
   cases. Case-local relaxed lineage never enters algorithm learning. At the
   project-configured review cadence, look for drift, repeated near-failures,
   weak bounds, irrelevant variables, or emerging case classes.
9. Report trend summaries: repeated bad blocks, common bound contacts, product-spec margins, utility outliers, route classes, and proposed next optimization.
10. Only final release candidates need broad reprocessing; routine processing upgrades should be versioned and forward-applied unless a hard-gate defect invalidates earlier evidence.

### Three-Role Generalization Contract

1. The main agent owns method and acceptance: freeze the immutable source
   version, physical boundary, representative panel, allowed manipulated
   variables, staged representative-panel criteria, stop conditions, and evidence schema before
   any tuning starts.
2. When a high-reasoning tuning agent is assigned, give it an immutable source
   and a candidate-only write area. It performs the concrete Aspen diagnosis and
   tuning, stops at the first unexplained hard failure, and returns the BKP
   first-run/reopen evidence plus the proposed shared control law. It must not
   publish, activate pointers, edit locked roots, or weaken the frozen gates.
3. Low-reasoning workers are execution adapters only: run approved scripts in
   the canonical order, read/export records, and stop on an anomaly. They do not
   choose controls or invent repairs.
4. The main agent independently verifies candidate hashes, real BKP first-run
   and reopened-run results, controlled-variable readbacks, boundary streams,
   terminal warning/error counts, and contrasting-case evidence. Only the main
   agent may publish an immutable successor and advance the gate, only after
   the central current strict learning-eligibility and lineage checks pass.
5. Passing one tuned case is diagnostic evidence, not generalization. Promotion
   requires the complete frozen project panel. Historical `Gate 1/5/20`
   labels apply only where that exact project contract requires them. A newly
   diagnosed hard defect invalidates and restarts the version; it does not
   waive remaining release evidence.
6. Once a mother has passed its representative panel and entered production,
   sparse residual failures do not automatically reopen generalization. Keep the
   mother frozen, repair copied cases within the protected-control contract, and
   record the cause and exact case identity. Reopen mother work only when a
   shared intrinsic defect is demonstrated across a material portion of ordinary
   cases, or when the user explicitly requests another generalization cycle.

## Rule Types

工具触发与插入时机统一见
[内置工具规则](../aspen-document-driven-flowsheet/references/aspen_builtin_solve_fit_tools.md)；
开始代表工况调参时先调用 `solve_route`。这里保留模板泛化的专业要求：
已知运行关系先实现为实时规则，未知响应才试算；多变量不自动转外部搜索。
一次性换算不加 Calculator，固定设备容量评估不让尺寸随流量偷偷变化。

- Calculator: forward translator from measured feed/process features to Aspen inputs, makeup flows, initial guesses, utility loads, or design-spec starting values.
- Design Spec: feedback goal for one scalar target with one manipulated variable and engineering bounds, such as syngas ratio, CO2 removal, solvent recovery, or makeup closure.
- Classifier: deterministic if/else or case logic that chooses calculator constants, active design specs, initial guesses, or grouped templates before the run.
- Sensitivity: short bracketing sweep used to discover feasible ranges before locking a stricter design spec.
- Guard: a bounded transient feasibility rule such as
  `max(source_floor, margin*live_demand)`. It is accepted only when the final
  value returns to the intended steady-state floor or authority target.
- Inventory/root rule: a bounded recovery, purge, or inventory target that
  makes the intended recycle root stable without cutting the physical recycle
  or changing an independent feed scale.

## Physical-Law-First Control Search

Before adding a classifier, alternative unit, or case-specific branch, derive the
smallest physical relation between the measured inlet state, the controlled
quantity, and the available manipulated variable.

1. Write the component balance, reaction extent, phase split, or recovery
   equation on the actual Aspen stream basis.
2. Count degrees of freedom and list every runtime writer. Require one primary
   writer per manipulated node.
3. If the relation has a closed-form bounded solution, implement a Calculator.
   Record raw value, clamped value, active bound, units, and feasibility class.
4. If the relation is nonlinear but continuous and locally monotonic, use one
   Design Spec with one manipulated variable and evidence-backed bounds.
5. If monotonicity or root uniqueness is unknown, run a short sensitivity
   bracket to discover the response. Do not promote the sensitivity block as
   the production controller.
6. Use a deterministic classifier or grouped template only when the response
   has proven discontinuities, multiple roots, distinct phase regimes, or
   genuinely different route physics.
7. Add equipment only when the existing topology lacks a physical degree of
   freedom or violates pressure, temperature, phase, or material continuity.
   A missing compressor or condensate outlet is a topology defect; a missing
   flow formula is not.
8. Treat bound saturation as evidence: distinguish target met, high-side no-add
   ignore, low-side reaction-capacity insufficient, and numerical failure.
   Never call a mathematically saturated controller a converged target.
9. Keep temperature as a bounded secondary control after mass and reaction
   relationships close. Use it only with a defensible response relation or
   local bracket; do not use temperature tuning to hide a missing mass control.

For a scale-only panel, first test whether a dimensionless split, conversion,
recovery, solvent-to-load ratio, residence time, or space velocity should remain
constant. Prefer these invariants over feedstock-name rules or saved case values.

## Recycle Scale And Root Pattern

1. Store the boundary-scale vector: every fresh total/component flow, basis,
   temperature, pressure, and phase.
2. Store physical recycle connectivity separately from explicit tear streams.
3. Define the root fingerprint as fresh boundaries, loop inventory, key
   intermediate, limiting reactant, recovery/purge, guard output, and product.
4. Make loop-basis Calculators read the recycle-closed inlet and execute before
   dependent blocks. Preserve component-flow versus total-flow input basis.
5. Use local same-case seeds first. Broaden warm starts only after an inventory
   or bound rule makes the intended root unique; seeding is not a process rule.
6. Reject any clean run whose final guard remains above the frozen source floor,
   whose root fingerprint belongs to a rejected high/low root, or whose apparent
   conversion comes from phase transfer.
7. Validate the candidate and copied delivery through asynchronous Control
   Panel capture plus raw-history and same-run process gates.

## Aspen Implementation Pattern

- Use calculators for mass-basis normalization, oxygen/steam/H2 makeup, MEA or water loss replacement, utility accounting, reactor space-time or space-velocity scaling, and route-specific initial values.
- Use design specs for live targets: CO2 removal, target H2/CO ratio, stripper recovery, reactor conversion proxy, or boundary product constraints.
- For reactor islands, treat residence time, GHSV/WHSV, catalyst inventory, reactor volume, tube count, bed length/diameter, and parallel reactor count as first-class adaptive variables. The standard is not "bigger feed gets a bigger number"; the standard is that reactor residence time or space velocity must remain consistent with the source/literature design window and must stay physically reasonable. If feed throughput, volumetric flow, composition, temperature, pressure, or conversion/severity target changes, first decide whether the case is a design-sizing case or a fixed-equipment capacity case. In design-sizing mode, prefer a Calculator that reads the reactor inlet flow and writes reactor geometry or catalyst inventory before the reactor, preserving the target residence time/GHSV/WHSV. Use a Design Spec for reactor sizing only after a sensitivity bracket proves a continuous physical manipulated variable is appropriate. In fixed-equipment mode, keep geometry fixed and report conversion/selectivity drift as capacity evidence instead of hiding it with downstream separation tuning.
- Keep one target per primary manipulated variable when possible. If two targets fight for one variable, split the route or add a physically meaningful second manipulated variable.
- Put broad case logic in a classifier when Aspen lacks convenient loops. If embedded Fortran is used, prefer explicit feature thresholds and compact branch tables.
- Set lower and upper bounds from literature ranges, seed runs, or equipment logic. Do not use tolerance relaxation as a control strategy.
- Prefer grouped templates when route physics differ: for example product-ratio groups or WGS/MEA, MEA/H2, and RWGS/MEA branches.
- Map the property and component basis across every process boundary. In an
  electrolyte flowsheet, do not let true-species aqueous chemistry silently
  propagate through a high-temperature dry-gas equilibrium island. Use a
  compatible apparent/non-electrolyte basis for the gas island and explicit
  true-component overrides for the aqueous electrolyte blocks, then verify the
  crossing on at least two compositionally different real feeds.
- Treat solver controls as diagnosed numerical controls, not blanket tuning.
  Increase an inner-iteration limit only when the inner error is demonstrably
  decreasing at the old limit; add damping or a minimum bounded step only when
  the outer history demonstrates oscillation. Freeze the exact control
  readbacks and rerun contrasting feeds after either change.
- Do not accept an outer-loop convergence flag by itself. If a nested unit hits
  its inner-iteration cap and the outer residual later appears converged, audit
  unit and flowsheet mass balance, iteration history, and first-run/reopen
  agreement. A false outer fixed point with bad mass closure is a failed run;
  raise the specific inner limit only when its residual was still decreasing,
  then prove the same setting on contrasting feeds.
- Freeze the controlled process boundary before testing a ratio law. When a
  downstream absorber or separator has acknowledged component losses, accept
  the controller at its upstream boundary and record downstream drift only as a
  separate loss metric. Do not retune the upstream ratio controller to cancel a
  loss that lies outside its declared physical scope.

## Failure Taxonomy

- Missing algorithm: a variable that should adapt is fixed.
- Boundary-scale drift: only one fresh feed is restored or a guard silently
  changes final plant capacity.
- Feedback runaway: recovery or loop inventory raises a live makeup/controller
  output, which further raises recovery and stabilizes an unintended root.
- Wrong recycle root: the run is numerically clean but its inventory,
  intermediate, limiting-reactant, guard, or product fingerprint is wrong.
- Startup-path failure: the final point is feasible but early iterations cross
  zero reactant, invalid flash, or bad basis states; repair initialization and
  dependency order without changing the accepted physical point.
- Space-time mismatch: reactor inventory or geometry is fixed while feed throughput or gas volumetric flow changes, or is scaled by the wrong feature such as one reactant flow while total reactor inlet gas flow changes. Apparent downstream separation or recycle failures may actually be reactor severity failures.
- Misclassification: the case belongs to a different operating bucket or threshold edge.
- Infeasible physics: target cannot be achieved within allowed temperature, pressure, feed, or separation bounds.
- Unit/template bug: wrong card, disconnected utility, hidden pressure drop, fake separator, or bad stream mapping.
- Property-basis boundary defect: electrolyte true/apparent species or property
  methods cross into an incompatible reactor, heater, flash, or compressor
  region and create false duties, mass imbalance, or property failures.
- Numeric issue: poor initial guess, too narrow bound, or overly stiff design-spec path.
- External issue: Aspen COM lock, file path conflict, stale export, or failed batch runner.

## Release Evidence

- Save the parent Aspen flowsheet as `.bkp`; prove it by direct BKP open/run/export and reopened after-run BKP rerun. Keep `.inp` only as readable card/diff evidence.
- Save grouped fixed templates with manifest files and hashes.
- Save batch CSV/JSON summaries with case id, branch, target, features, manipulated values, status, bad blocks, and gate metrics.
- Save a repair log explaining each failed class, rule patch, and rerun result.
- Save accepted/rejected root fingerprints, final guard actuation, the complete
  boundary-scale vector, physical recycle map, tear map, and multiphase metric
  formulas/results.
- Save a final algorithm report that states allowed manipulations, rule equations, thresholds, literature or engineering support, and residual limits.
- Save the block-level property/component-basis map and every nondefault solver
  control with the iteration evidence that justified it.

## Low-Capability Execution Capsule

- Package routine trials as a fixed-config, one-command capsule. The worker may
  run preflight, execute the approved command, read the result, and stop. It
  must not tune, repair, select a different mother, retry, or edit any input.
- Resolve the current mother group through the project pointer and verify its
  pointer, manifest, runner, template, handoff, and configuration hashes before
  Aspen starts. Never copy control equations into a parallel trial
  implementation when the locked runner already owns them; call the locked
  runner's public node function after its original authority gate passes.
- Before invoking a locked node function directly, reproduce the runner's own
  worker-session setup order: clear only the batch-local stale lock allowed by
  that runner, call its `configure_worker_com_contract(lock_file, feed_root)`,
  and then dispatch the node. A wrapper that omits this contract is invalid even
  when every mother and handoff hash is correct. On completion, require zero
  active documents, equal successful open/close counts, no reconnect, and no
  force-termination flag.
- Run only on a writable case copy outside the immutable mother root. Record the
  source hash before and after the trial and reject any mother mutation.
- A single RWGS acceptance capsule includes the independent zero-H2 probe, the
  formal first run, and the untouched after-run BKP reopen. Each real
  `Engine.Run` has its own 60-second ceiling; startup, export, close, and offline
  extraction are timed separately. No hidden retries or reconnects are allowed.
- Preflight must fail closed when another production Aspen batch owns the
  execution window, the handoff is stale or incompatible, the route row is not
  unique, the output identity already conflicts, or any required evidence is
  missing. A policy skip remains a recorded physical classification and never
  becomes a fabricated Aspen pass.
- Put every special value in a machine-readable configuration and repeat its
  meaning in the package introduction. The prose is explanatory; the
  configuration and locked mother are executable authority.

## Superstructure Generalization Guidance

- When many seed cases fail, first suspect a missing control law rather than a need for many case-specific branches.
- Do not infer a mother defect from one or a few difficult cases after a broad
  representative panel has passed. Compare the failure rate, feed diversity,
  normalized root signature, and previously accepted controls first. Sparse,
  non-systematic numerical failures are case-repair evidence, not an automatic
  mandate to replace a generalized calculator or Design Spec.
- Record every manual correction for audit. Only eligible current strict
  evidence may support a scalar feature or reusable Calculator, Design Spec,
  bounded sensitivity bracket, or classifier. A case-local relaxation, its
  results and every dependent lesson are permanently excluded from this path.
- If a structure or algorithm changes during seed tuning, rerun the affected
  class and then the complete frozen project panel before promoting compatibility.
- Do not add a separator, flash, tower, compressor, or heater merely because it fixes one difficult case; prove the original equipment cannot meet the physical duty within reasonable operating bounds.
- Keep route roles explicit. Upstream guard units may control feed quality to a final unit, while the final unit keeps the product purity/recovery design specs.
- For scale-only panels, check whether reactor volume, catalyst inventory, tube count, bed dimensions, solvent circulation, recycle purge, or tower draw rates should scale with feed before modifying composition or adding units. Reactor space time is not optional for design-sizing templates; keep the same target residence time/GHSV/WHSV within a reasonable design window. Only keep it fixed when the task is explicitly a capacity or debottlenecking evaluation.
- Prefer one reusable template with embedded or pre-run classifier logic. Split templates only when route physics differ, not when a single missing rule can explain the failures.
- Record rejected candidates as evidence, especially when they show a manipulated variable has a flat response or a proposed structure is not necessary.

## Prohibited Shortcuts

- Do not change feed composition to force convergence.
- Do not replace physical units with SEP blocks unless the task explicitly asks for a scaffold model.
- Do not create steam, water, solvent, MEA, oxygen, hydrogen, heat, or pressure changes without explicit streams and utilities.
- Do not lower pressure or reset temperature only because a case is hard; justify it by route physics and bounds.
- Do not accept a single lucky run as generalized behavior.
- Do not leave manual changes unlogged or outside the template.
- Do not leave the main adaptive law only in an external batch script when the delivered Aspen template is supposed to be reused directly; core calculators, design specs, and bounds must be present in the promoted BKP/INP evidence.
