# Aspen Quick Router

Use this first when token budget matters. Open the detailed routing graph only
when the task crosses several skills or the route is unclear.

## Route By Task

| Task | Open Next | Then |
| --- | --- | --- |
| Build a new document-driven flowsheet | `SKILL.md` Operational Architecture | `aspen_workflow_playbooks.md` only if needed |
| Source/taskbook requirements may be incomplete | `source_taskbook_and_gate_protocol.md` | run two-pass source ledger before Aspen mutation |
| Property method must be chosen or changed | `source_taskbook_and_gate_protocol.md` property-method freeze | local Aspen graph ch03 route, then operation contract |
| Pure error/warning/bad block/recycle repair | `aspen-flowsheet-error-repair` | `aspen_zero_warning_repair.md` only for stubborn runnable cases |
| Deliver a runnable Aspen case | `open_run_readiness_protocol.md` | `material_library_protocol.md` preflight, then operations QA |
| Migrated path cannot open or package is not portable | `delivery_portability_and_plausibility_gates.md` | path-migration gate, then open-run readiness |
| Run converges but process is unrealistic | `delivery_portability_and_plausibility_gates.md` | physical plausibility gate, then process authority repair |
| Tower design or tower replacement | `aspen-tower-optimization-workflow` | `aspen_distillation_patterns.md` only for special/complex towers |
| Pressure/HX/PFD issue | `aspen-pressure-pfd-delivery` | standards/equipment graph only if report parameters are changed |
| Explicit section split | `aspen-two-section-flowsheet` | case reference only if historical family matches |
| Formal kinetics | local Aspen graph `kinetics_expert_system.md` | `kinetics_freeze_template.md`, then operation contract |
| Calculator/Design Spec/Sensitivity | `aspen_builtin_solve_fit_tools.md` | operation contract |
| Equipment report or standards | equipment graph README | standards graph only if standards folder is active |
| Need script reuse/template | `script_template_catalog.md` | `script_template_knowledge_graph.md` for broad node selection |
| More than one route applies | `skill_routing_graph.md` | choose one primary route and one evidence return path |

## Token Rules

- Read only one next file at a time.
- Search large references with `Select-String`/`rg` before opening sections.
- Prefer project authority files over old conversation memory.
- Use scripts to write logs/slices/readiness records instead of loading their
  protocols during routine work.
- Historical policy archives are not distributed. If a user supplies one for
  explicit audit, keep it outside default loading and check current authority
  before reusing any scoped statement.

## Return Rule

Every route returns to `aspen-document-driven-flowsheet` with:

```text
accepted/provisional/blocked:
evidence files:
current blocker:
next allowed action:
```
