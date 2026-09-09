# Aspen Skill And Knowledge Routing Graph

Use this file when an Aspen task mixes source-document authority, local
knowledge-graph lookups, process decisions, mechanical Aspen operations,
equipment-design standards, and final delivery claims. The graph keeps every
layer strong and prevents a lower layer from inventing process authority.

## Network Topology

```text
User goal
  -> project instructions / AGENTS.md
  -> latest authority files
     change-offset table, status note, dynamic/static audits, freeze ledgers
  -> local knowledge graphs
     Aspen graph, equipment graph, standards graph
  -> process authority skill
     aspen-document-driven-flowsheet
  -> source/taskbook and property-method gate
     source_taskbook_and_gate_protocol.md
  -> repair authority skill, when the task is pure error repair
     aspen-flowsheet-error-repair
  -> specialist process skills
     section boundary, tower workflow, pressure/PFD, equipment audit
  -> operation skill
     aspen-plus-operations
  -> exported evidence
     .inp/.bkp/.apwz, Control Panel, status CSV, stream CSV, audit JSON
  -> process authority skill
     promotion, quarantine, or blocker
```

Rule: evidence flows back upward before a branch is promoted. A specialist or
operation skill may produce files, but only `aspen-document-driven-flowsheet`
promotes the process claim unless the user explicitly scopes the task to a
specialist-only audit.

## Authority Gateways

Open these gateways before routing to detailed skills:

| Gateway | Open When | First Files | Output |
| --- | --- | --- | --- |
| Project instructions | Every workspace task | `AGENTS.md` or injected project instructions | Active hard gates and local overlays |
| Current authority | Resume, compaction, existing project, repair | change-offset table, current status note, latest dynamic/static audits, kinetics ledgers | Current accepted branch, frozen decisions, blocker |
| Source/taskbook gate | Before Aspen mutation, source uncertainty, user-added offsets, final delivery | `source_taskbook_and_gate_protocol.md`, project source ledger, change-offset table | Direct extraction pass, reverse checklist pass, property-method freeze, user-adjustment overlay |
| Aspen knowledge graph | Aspen card, property, convergence, reactor, tower, recycle, analysis | `aspen_sun_lanyi_knowledge/knowledge_graph/README.md`, then `unknowns_router.md`, `knowledge_graph_index.md`, `aspen_operation_playbook.md` | Chapter nodes, card routes, unknown classification |
| Classic cases | Lecture-like tower, reactor-card, convergence, dynamics, solve/fit pattern | `classic_cases_playbook.md` | Transferable workflow only, never values |
| Kinetics expert | Any formal kinetic reactor or kinetic card | `kinetics_expert_system.md`, `kinetics_freeze_template.md` | Frozen/provisional/blocked source-to-card chain |
| Equipment graph | Equipment sizing/selection report, EDR/SW6/vendor/Column Internals boundary | `设备设计选型工作包/knowledge_graph/README.md`, then its `unknowns_router.md` | Formula family, source classification, equipment ledger |
| Standards graph | Design standards folder is used | `standards_graph/README.md`, then `priority_report_fastmap.md`, `standard_parameter_crosswalk.md` | `direct_reuse`, `method_only`, `software_boundary`, `vendor_boundary`, or `forbidden_transfer` |

If a gateway is unavailable, continue only with a written fallback and mark the
affected row `provisional` or `blocked`.

## Responsibility Layers

| Layer | Skill Or Graph | Owns | Must Not Own |
| --- | --- | --- | --- |
| Project authority | `AGENTS.md`, change-offset table, status/audit ledgers | Latest accepted deviations, frozen decisions, current blocker | New technical values without evidence |
| Aspen graph | Local `aspen_sun_lanyi_knowledge` | Unknown routing, chapter/card lookup, property/reactor/tower/convergence paths | Project values or delivery claims |
| Equipment/standards graphs | Equipment work package graphs | Formula families, parameter-source classification, standards boundaries | Transferring other-equipment values |
| Process authority | `aspen-document-driven-flowsheet` | Source route, hard gates, scaffold/island architecture, unit/card ledgers, final promotion | Raw Aspen mechanics without operation contract |
| Repair authority | `aspen-flowsheet-error-repair` | Flow error/warning diagnosis, Control Panel/history repair loop, default precision lock, repair-family selection | Source-route redesign, Aspen mechanics, final process promotion |
| Section boundary | `aspen-two-section-flowsheet` | Explicit section contracts, cross-section stream validation, section-specific gates | Aspen import/export/run mechanics |
| Tower island workflow | `aspen-tower-optimization-workflow` | Tower target freeze, `DSTWU`/`DSTWU-SKIP`, rigorous tower steps, Design Spec/Vary reconnect | Full-flow authority or non-tower separations |
| Pressure/PFD delivery | `aspen-pressure-pfd-delivery` | Pump/compressor/valve topology, HEATER `PRES=0`, PFD/PDF pressure claims | Reactor/separation target choice |
| Equipment report audit | `chemical-equipment-selection-audit` | Equipment formula ledgers, report calculation scripts, EDR/SW6/vendor/manual boundary | Aspen process route authority |
| Operation layer | `aspen-plus-operations` | Create/set/run/export/reopen/check Aspen actions through MCP, COM, or scripts; Calculator/Design Spec/Sensitivity mechanics | Chemistry choice, target values, acceptance claims |
| Component template | `aspen-plus-template` | Component/template generation through Aspen COM | Process-route repair |

## Trigger Routing

| Task Trigger | Route |
| --- | --- |
| New document-driven flowsheet | Project authority -> Aspen graph -> `aspen-document-driven-flowsheet` -> operations |
| Existing case after compaction/resume | Project authority files first -> `aspen-document-driven-flowsheet` |
| Taskbook/source requirements may be incomplete | `source_taskbook_and_gate_protocol.md` -> two-pass source ledger -> process skill |
| Property method choice or proposed method change | Aspen graph ch03 route -> `source_taskbook_and_gate_protocol.md` property-method freeze -> process skill |
| User adds or tightens a process requirement | change-offset table -> source/taskbook gate overlay -> affected specialist/operation route |
| Pure flowsheet error/warning repair | startup triad: `aspen-document-driven-flowsheet` -> `aspen-flowsheet-error-repair` -> `aspen-plus-operations` |
| Every design step or repair attempt | `aspen-document-driven-flowsheet` learning log -> continue work |
| Completed chunk/island/repair family | `material_library_protocol.md` -> process slice -> continue work |
| Successful completed task | learning log -> `references/self_evolution_protocol.md` -> `scripts/self_evolve_skill.py` candidate record |
| Unknown Aspen card/choice | Aspen graph `unknowns_router.md` -> chapter node -> process skill |
| Property method choice | Aspen graph ch03 route -> process skill property-method gate -> operations |
| Formal kinetics | Aspen graph kinetics expert -> freeze ledger -> process skill -> operations `reaction-card` |
| Yield/SEP scaffold | Process skill `Operational Architecture` -> operations `block-stream`/`equipment-card` |
| Explicit section split | `aspen-two-section-flowsheet` -> process skill promotion audit |
| SEP replacement | Process skill separation target ledger -> tower skill if tower-like -> operations |
| Tower design/optimization | Aspen graph special-column route if needed -> `aspen-tower-optimization-workflow` -> operations |
| Calculator/Design Spec/Sensitivity | Process skill target/bounds -> `aspen-plus-operations` solve/fit nodes -> process audit |
| Recycle convergence | Process skill scaffold/recycle ledger -> Aspen graph convergence nodes -> operations short probes |
| Bad block or failed run | `aspen-flowsheet-error-repair` -> repeated Control Panel/history -> operations |
| Pressure/HX/PFD | `aspen-pressure-pfd-delivery` + pressure graph/standards as needed -> operations |
| Equipment sizing report | Equipment graph -> `chemical-equipment-selection-audit` -> standards graph if used |
| Component/template generation | `aspen-plus-template` -> operations case evidence if process model needs it |
| Zero-warning polish | Process skill zero-warning gate -> `references/aspen_zero_warning_repair.md` -> operations |
| Open-run readiness | `open_run_readiness_protocol.md` -> operations clean-session reopen/Required Input/start-run QA |
| Migrated path opens fail or stale absolute paths | `delivery_portability_and_plausibility_gates.md` -> migrated-path QA -> packaging/path repair before process edits |
| Converged run looks physically unrealistic | `delivery_portability_and_plausibility_gates.md` -> physical plausibility ledger -> process authority repair |
| Need script template or reusable script promotion | `script_template_catalog.md` -> `script_template_knowledge_graph.md` if broad selection is needed -> project-local template copy -> material-library slice/reuse manifest |
| Final package | Process skill accepted authority -> operations `run-export`/`delivery-qa` -> final audit |
| Final preflight | material-library digest -> heating/pressurization/pressure-drop audit -> final response |

## Standard Handoff Contracts

### Process To Operation

The operation layer chooses MCP, COM, or script execution. The process layer
supplies authority, allowed changes, evidence needs, and stop condition only.

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

### Repair To Operation

```text
Operation goal:
Authority artifact:
Current case/version:
First limiting Control Panel/history message:
Allowed repair family:
Forbidden changes:
Default precision lock:
Required evidence:
Stop condition:
```

### Process To Section Boundary

```text
Boundary goal:
Source basis:
Candidate sections:
Cross-section streams:
Allowed placeholders:
Forbidden assumptions:
Required section gates:
Return evidence:
```

### Process To Tower Workflow

```text
Tower goal:
Frozen feed/export:
Separation target:
Property-method row:
DSTWU allowed or DSTWU-SKIP reason:
Allowed manipulated variables:
Required sidecar evidence:
Reconnect gate:
```

### Process To Pressure/PFD

```text
Pressure goal:
Current case/export:
Pressure authority ledger:
Allowed pressure devices:
Forbidden hidden pressure changes:
HX pressure-drop convention, if authorized:
PFD/report claims to verify:
Return evidence:
```

### Process To Equipment/Standards Audit

```text
Equipment goal:
Equipment tag and source basis:
Formula family candidates:
Parameter-source classification needed:
Software/vendor/manual boundary:
Standards files to check:
Reusable report/calculation artifact:
Return evidence:
```

## Return Evidence

Every specialist or operation call must return enough evidence for the process
authority layer to decide one of three states:

- `accepted`: source/ledger basis, exported Aspen evidence, and hard gates pass.
- `provisional`: runnable or useful, but missing source, property, kinetics,
  equipment, or delivery evidence.
- `blocked`: cannot proceed without new source, corrected card syntax, missing
  property support, unresolved Aspen resource failure, or user decision.

Minimum return fields:

```text
Changed/generated files:
Authority row updated:
Source/taskbook gate record:
Property-method freeze row:
Cards/blocks/specs touched:
Run/reopen/export status:
Control Panel or history evidence:
First limiting message before fix:
First limiting message after fix:
Affected block/spec/sequence/tear stream:
Stream/status/audit files:
Learning log entry:
Material-library slice:
Open-run readiness record:
Self-evolution record or candidate patch:
Remaining blockers:
Next allowed action:
```

## Anti-Patterns

- Skipping project authority files and reopening the original report as if no
  accepted offsets exist.
- Skipping the source/taskbook gate when official requirements, buyer gates, or
  user adjustments may change capacity, purity, pressure, recycle, equipment,
  hydraulic, or deliverable claims.
- Changing property method after a module is accepted without a change-offset
  row, physical reason, and rerun of downstream evidence.
- Letting `aspen-plus-operations` choose chemistry, conversion, separation type,
  product target, or acceptance status.
- Skipping `aspen-flowsheet-error-repair` when the task is a pure error,
  warning, bad-block, recycle, or product-gate repair.
- Calling a specialist skill and then promoting its output without returning to
  `aspen-document-driven-flowsheet` for same-version hard-gate audit.
- Reusing historical case values, stream IDs, tower specs, kinetic constants, or
  pressure levels without a fresh source ledger.
- Treating a lecture case or skill example as a value source instead of a route,
  field-meaning, diagnostic-order, or checklist source.
- Relaxing convergence precision to pass a case rather than diagnosing Control
  Panel/history, feed inventory, Design Spec bounds, property method, or recycle
  setup.
- Changing default/global precision, `CONV-OPTIONS PARAM TOL`, tower `TOL-SPEC`,
  balance tolerance, or product-spec tolerance as a repair.
- Treating `SEP/SEP2` as a field device rather than a scaffold separation duty.
- Hiding pressure changes in `HEATER` blocks or PFD text.
- Finishing a successful design/repair without a learning log and a useful
  self-evolution review, or promoting a vague lesson that lacks decisive
  evidence, root cause, fix, boundary, and target skill/reference.
- Delivering after a local fix without digesting process slices and rechecking
  heating, pressurization, pressure-drop convention, pressure devices, tower
  pressure paths, and unexplained stream-state changes.
- Delivering a `.bkp`, `.apwz`, or `.inp` that opens with missing Required
  Input, needs manual input before Run, or lacks same-version reopen/export
  evidence.
- Promoting reusable scripts that were not newly built or materially modified in
  the current work, not parameterized, or still contain project-specific values.
