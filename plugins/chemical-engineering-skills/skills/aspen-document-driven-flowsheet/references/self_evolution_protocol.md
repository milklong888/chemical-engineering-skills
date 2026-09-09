# Aspen Self-Evolution Protocol

Use this protocol for project logging and post-user-closure evolution. The goal is to make learning reliable without
slowing the build path or polluting generic skills with project-specific values.

## Timing Rule

During the task, record material decisions/trials once in the project audit;
reuse existing run/status evidence rather than writing duplicate logs.
At each delivery ask whether the task is finished or needs improvements.
Do not begin task-derived self-evolution until the user explicitly closes the
current task revision. Reopening or further tuning invalidates the old closure.
Read the central `EVOLUTION_LOOP.md` for macro prompt principles, data-pattern
testing, Skill placement and no-change outcomes. Mere wording preferences and
single-case numerical settings are not top-level prompt principles.

Project completion is not learning eligibility. Before candidate generation,
read the chemical expert's STRICT_ACCEPTANCE_AND_LEARNING.md and run its
lineage eligibility check. Only complete, independently verified strict evidence
may enter human candidate review. A user-accepted blocker or locally relaxed
deliverable and every descendant are audit-only and never learning samples;
later renaming, summaries or inherited strict reruns do not remove exclusion.

## Mandatory Event Log

For every design-flow step and every correction attempt, record a compact event:

```text
event_type:
phase:
category:
problem_or_goal:
authority_basis:
action_taken:
evidence:
result:
next_allowed_action:
```

Minimum events to log:

- source-route extraction and change-offset decisions;
- property-method decisions;
- reaction target estimates and kinetic freeze checks;
- yield/SEP scaffold construction;
- scaffold closure, raw-material recovery, and product-gate checks;
- every failed Aspen run or Control Panel limiting message;
- every fix attempt and why it was chosen, including the Control Panel/history
  message before the fix and the first message after the fix;
- every reactor island, separation island, tower step, pressure/HX change, and
  recycle closure step;
- every Calculator, Design Spec, Sensitivity, Optimization, or Regression setup;
- every final promotion, quarantine, blocker, or delivery decision.
- every process slice recorded for the material library, including script reuse
  candidates built in the current work.

Use `scripts/log_aspen_experience.py` when possible. If not, write the same
fields into the project status note or learning log manually.

## Deep Success Review

After the user's explicit closure, summarize the final accepted task revision.
Do not perform this review automatically when the assistant hands over a
candidate. The summary must be specific and causal, not generic. A truthfully
captured unrelaxed failure may inform a hypothesis, not a claimed successful
model or validated fix; keep incomplete evidence out of promotion.

Use this structure:

```text
Task completed:
Accepted evidence:
Initial wrong assumption or uncertainty:
First decisive diagnostic evidence:
Root cause mechanism:
Fix that actually worked:
Why earlier attempts were weaker:
Reusable principle:
Boundary where principle does not apply:
Skill/reference target:
Candidate rule or patch:
Evidence files:
```

Reject shallow lessons such as "check carefully", "use Aspen correctly", "read
the report", or "try another parameter". A usable lesson must name the trigger,
the diagnostic evidence, the mechanism, the action, the acceptance evidence, and
the boundary.

## Classification And Placement

Classify every logged lesson. Record all lessons, but promote only reusable,
evidence-backed ones.

| Category | Add Reusable Lesson To | Do Not Add |
| --- | --- | --- |
| `authority-resume` | `SKILL.md` Authority First or `skill_routing_graph.md` gateways | Old conversation facts, stale branch names |
| `source-taskbook-gate` | `source_taskbook_and_gate_protocol.md`, `quick_router.md`, or source-gate script templates | Vague "read more carefully" reminders without a ledger row |
| `flowsheet-architecture` | `SKILL.md` Operational Architecture or `aspen_workflow_playbooks.md` | Project route values |
| `error-repair` | `aspen-flowsheet-error-repair/SKILL.md` or `aspen_zero_warning_repair.md` | Tolerance loosening, vague "try another setting" rules |
| `section-boundary` | `aspen-two-section-flowsheet/SKILL.md` or its case references | Nonmatching case stream IDs |
| `scaffold` | `aspen_workflow_playbooks.md` or `aspen_convergence_trials.md` | Treating SEP as final equipment |
| `kinetics` | `kinetics_expert_system.md`, freeze template, or kinetic conversion script | Guessed `k/E/Exponent` values |
| `property-method` | Aspen graph ch03 route, `source_taskbook_and_gate_protocol.md`, or main property-method gate | Equipment tuning that masks property errors |
| `tower` | `aspen-tower-optimization-workflow` or `aspen_distillation_patterns.md` | One project tower specs as defaults |
| `separator` | `aspen_workflow_playbooks.md`, `aspen_distillation_patterns.md`, or failure patterns | SEP split fractions without source |
| `recycle` | `aspen_convergence_trials.md`, workflow playbook, or audit gates | Solver-only superstition |
| `control-panel` | `aspen_zero_warning_repair.md` or failure patterns | Log substring counts without phase context |
| `calculator-design-spec` | `aspen_builtin_solve_fit_tools.md` or main priority defaults | Hand-swept values as accepted specs |
| `pressure-hx` | `aspen-pressure-pfd-delivery` or standards/pressure ledger guidance | Hidden pressure changes in heaters |
| `equipment-standards` | `chemical-equipment-selection-audit` or standards graph nodes | Transferring other-equipment values |
| `delivery` | `aspen_delivery_evolution.md`, audit gates, or Output Standard | Claims not tied to same-version exports |
| `skill-routing` | `skill_routing_graph.md` | Duplicating full rules in many skills |
| `material-library` | `material_library_protocol.md` or project slice templates | Old project values mixed into new slices |
| `script-reuse` | `script_template_catalog.md`, `material_library_protocol.md`, current project reusable scripts, or candidate skill scripts | Promoting old or unparameterized scripts |
| `delivery-preflight` | `material_library_protocol.md`, `aspen-pressure-pfd-delivery`, or audit gates | Forgetting heating/pressure/pressure-drop checks |
| `open-run-readiness` | `open_run_readiness_protocol.md`, error-repair skill, or delivery gates | Claiming runnable files without clean reopen/Required Input evidence |
| `path-portability` | `delivery_portability_and_plausibility_gates.md`, open-run readiness protocol, or package templates | Claiming portable packages without migrated-path reopen/start-run evidence |
| `physical-plausibility` | `delivery_portability_and_plausibility_gates.md`, main hard gates, or workflow playbooks | Treating convergence as acceptance when balances, stoichiometry, pressure, energy, or separations are unrealistic |

## Promotion Filter

Before proposing a skill edit, answer:

1. Did independently verified strict evidence pass the central lineage gate,
   without any case-local relaxation, unknown ancestor or excluded origin?
2. Is the lesson reusable beyond this project?
3. Can project-specific values, stream names, pressures, conversions, and file
   paths be removed or moved into a case card?
4. Does the lesson belong in the main skill, a specialist skill, a knowledge
   graph node, a reference, a script, or only the project log?
5. Is there already a rule covering it?
6. Can the proposed patch be one concise rule, checklist item, or script
   improvement?

If any answer fails, keep the lesson in logs and do not edit the skill.

Passing this filter authorizes only a reviewable project-local candidate, not
an automatic canonical edit. Keep exact evidence paths/hashes in the machine
ledger; redact only a separate sharing/presentation copy. Never substitute
literal <local-path> placeholders for the only provenance record.

## Required Final Note

At delivery, state the actual result and ask for completion/improvement feedback.
After user-confirmed closure and the resulting review, include only produced,
relevant items from:

- learning log path;
- material-library slice/digest path;
- success-review/evolution record path when created;
- candidate patch path when created;
- reusable scripts newly built in this work and whether they were promoted,
  kept project-local, or rejected;
- useful skill modifications proposed or applied;
- lessons deliberately not promoted and why.
