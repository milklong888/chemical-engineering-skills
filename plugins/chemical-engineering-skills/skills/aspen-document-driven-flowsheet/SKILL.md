---
name: aspen-document-driven-flowsheet
description: Coordinate document-driven Aspen process construction, staged rigorous replacement, repair routing and full-flow evidence under current source and change-offset authority. Use for process-route/scaffold/island/recycle integration; delegate Aspen mechanics and specialized tower/equipment work to existing skills.
---

# Aspen Document Driven Flowsheet

## 工作过程

拿到任务书、论文或现有模型后，先把路线、产品、物性、反应依据和修改权限整理成当前项目合同。需要从零建模且允许简化时，先用最简单但连接完整的模块建立全流程骨架，检查规模、组分去向、压力和循环；随后用最新导出的入口条件切出反应或分离岛，交给动力学、塔优化或热泵模块逐一严化，再一次接回一个已核验的岛。已有模型从它实际所在阶段继续，不重复从零开始。

图谱在选择方法和处理未知问题时介入，设备程序在骨架有负荷、岛内工况确定及接回后分别复核，执行[阶段调用规则](../chemical-engineering-expert/references/DESIGN_STAGE_ROUTING.md)。若设备限制要求改工况或结构，先更新项目决定，再交操作模块修改和重算。最终交付的是同一版本的模型、来源和修改记录、全流程结果及真实验收证据；简化骨架和单岛收敛不冒充最终全流程。

## Authority First

Read `references/ERROR_MEMORY.md`, the chemical expert, and its
`STRICT_ACCEPTANCE_AND_LEARNING.md`. Then read the current project's
change-offset/status/freeze ledgers before using old reports or candidates.
Do not import another project's accepted reactor, pressure ratio or product target.

Freeze route, method, basis, property/phase model, component fate, targets,
allowed edits and acceptance gates. A missing-but-derivable value is calculated;
an indispensable unsupported value blocks only its dependent claim.

## Fast Entry

Use `references/quick_router.md`. When a source/build/reconnect question needs
detail, read the relevant section of `references/document_driven_workflow.md`.

| Current task | Next existing entry |
| --- | --- |
| Source/required-method extraction | `references/source_taskbook_and_gate_protocol.md` |
| New scaffold or rigorous island replacement | `references/aspen_workflow_playbooks.md` |
| Existing run errors/warnings | `aspen-flowsheet-error-repair` then `aspen-plus-operations` |
| Tower/solvent/entrainer island | `aspen-tower-optimization-workflow` |
| Heat-pump replacement | `aspen-heat-pump-distillation-replacement` |
| Kinetic reactor | Sun Lanyi kinetics expert system + current freeze ledger |
| Calculator/DS/Sensitivity | `references/aspen_builtin_solve_fit_tools.md` |
| Section boundary | `aspen-two-section-flowsheet` |
| Shared operation template | `references/script_template_catalog.md` |
| Strict final file | `aspen-plus-operations` complete schema/history and exact-path gate |

## Operational Architecture

Start at the current project's actual stage, not automatically from zero:

`source and macro contract -> faithful scaffold when authorized -> rigorous
islands -> one-by-one reconnect -> pressure/heat/state audit -> equipment
feedback -> whole-flow and exact-file verification`

Use a new protected candidate for material edits. Before an accepted deviation,
update the project authority; after a change, recompute downstream streams,
recycles, control targets, heat/power utilities, equipment and claims.

Building/changing flow duties requires the expert's
`PROCESS_EQUIPMENT_FEEDBACK.md` and current `equipment-design-app`.
Use common-sense RAG for mechanism/alternatives, not project defaults. Preserve
a simple feasible baseline; catalog proximity does not justify extra equipment.

## Hard Gates

- Preserve the required method; a surrogate or SEP scaffold is not a silent
  replacement for requested kinetics or physical separation.
- Property method, chemistry and precision cannot be retuned merely to obtain
  a clean status. Physical purpose, mass/component fate, pressure/energy paths,
  control/recycle and product targets require same-candidate evidence.
- Strict delivery uses all-zero complete version-bound Summary plus raw current
  history, actual run identity and the exact final-file reopen, then all required
  project gates. Do not maintain another parser or warning policy here.
- A local user relaxation is explicitly case-only, reported with failed strict
  gates, and permanently barred from learning and shared/default retrieval.
- Preserve required PFD/layout, USER dependencies, target version and sidecars;
  use existing portability/readiness references when the delivery needs them.

## Learning Log And Self-Evolution

Read `references/self_evolution_protocol.md` only for logging or promotion.
Audit logs are project-local, not training examples. Candidate generation requires
explicit user closure of the current task revision plus the central strict
lineage eligibility check; accepted blockers or relaxed
deliverables never qualify. Detailed events remain traceable without loading
the entire history into every task.

At each delivery ask whether the task is finished or needs improvement. After
explicit closure follow the expert's `EVOLUTION_LOOP.md`: condense macro prompt
principles and test data-pattern hypotheses separately; keep specific values
and operations below the prompt layer. No reusable increment means no change.

## Output Standard

Return the engineering conclusion, current source/change-offset identity, key
verified results, unresolved/relaxed gates and the next scoped action. Keep
operation completion, local repair, simulation cleanliness, products and final
delivery separate. Report only relevant artifacts actually produced.
