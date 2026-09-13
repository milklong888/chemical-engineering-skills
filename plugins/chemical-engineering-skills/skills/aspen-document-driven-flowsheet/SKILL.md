---
name: aspen-document-driven-flowsheet
description: Coordinate document-driven Aspen process construction, staged rigorous replacement, repair routing and full-flow evidence under current source and change-offset authority. Use for process-route/scaffold/island/recycle integration; delegate Aspen mechanics and specialized tower/equipment work to existing skills.
---

# Aspen Document Driven Flowsheet

## 工作过程

拿到任务书、论文或现有模型后，先把路线、产品、物性、反应依据和修改权限整理成当前项目合同。需要从零建模且允许简化时，先用最简单但连接完整的模块建立全流程骨架，检查规模、组分去向、压力和循环；随后用最新导出的入口条件切出反应或分离岛，交给动力学、塔优化或热泵模块逐一严化，再一次接回一个已核验的岛。已有模型从它实际所在阶段继续，不重复从零开始。

图谱在选择方法和处理未知问题时介入，设备程序在骨架有负荷、岛内工况确定及接回后分别复核，执行[阶段调用规则](../chemical-engineering-expert/references/DESIGN_STAGE_ROUTING.md)。若设备限制要求改工况或结构，先更新项目决定，再交操作模块修改和重算。最终交付的是同一版本的模型、来源和修改记录、全流程结果及真实验收证据；简化骨架和单岛收敛不冒充最终全流程。

交付含节点、物流或简化占位的 `source` / `scaffold` 流程安排时，现在就完成[边界与严化交接记录](references/source_scaffold_handoff.md)及其结构检查。每个简化占位要有接手专业（未定时写选择条件）、必要输入和必须返回的结果；循环既列返回端，也列来源端，未知端点明确保留。只做这类流程安排、尚不能运行模型时仍交这些内容，不能以“以后严化”或“另行立项”代替当前交接。阶段查询回执不代替这份安排记录。仅交团队职责和工段合同而未交付节点—物流拓扑时，使用[工段合同模板](../aspen-two-section-flowsheet/SKILL.md#section-contract)和适用的阶段查询，不为满足拓扑检查器另造一张流程图。

## Authority First

Read `references/ERROR_MEMORY.md`, the chemical expert, and its
`STRICT_ACCEPTANCE_AND_LEARNING.md`. Then read the current project's
change-offset/status/freeze ledgers before using old reports or candidates.
Do not import another project's accepted reactor, pressure ratio or product target.

Freeze route, method, basis, property/phase model, component fate, targets,
allowed edits and acceptance gates. A missing-but-derivable value is calculated;
an indispensable unsupported value blocks only its dependent claim.
Even a scaffold balance must define its boundary and retain reaction source
terms for reacting species; use the expert's derivation protocol rather than
equating each species' inlet and outlet across a reacting system.

## Fast Entry

当前文档流程的阶段入口见[快速路由](references/quick_router.md)；
跨专业模块的主导、协作与交接见[任务登记](../chemical-engineering-expert/references/ACTIVE_ASSET_REGISTRY.md)。
来源、建模或接回需要细节时，只读 `references/document_driven_workflow.md` 的相关段。
查值、随进料联动、目标匹配、范围分析和多变量调参不限工具关键词：先读
[原生工具规则](references/aspen_builtin_solve_fit_tools.md)，明确固定量与联动量，再实际调用 `solve_route`。

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
Audit logs are project-local, not training examples. Canonical candidate generation requires
explicit user closure of the current task revision plus the central strict
lineage eligibility check; accepted blockers or relaxed
deliverables never qualify. Detailed events remain traceable without loading
the entire history into every task.

Authorized temporary submissions follow the expert's
[inbox route](../chemical-engineering-expert/references/EXPERIENCE_INBOX.md);
they may precede closure and never authorize default retrieval or canonical writes.

At delivery report the completed scope and remaining work. Request current-revision
closure only when needed for user-requested formal promotion and not already confirmed
or awaiting an answer. After explicit closure follow the expert's `EVOLUTION_LOOP.md`: condense macro prompt
principles and test data-pattern hypotheses separately; keep specific values
and operations below the prompt layer. No reusable increment means no change.

## Output Standard

Return the engineering conclusion, current source/change-offset identity, key
verified results, unresolved/relaxed gates and the next scoped action. Keep
operation completion, local repair, simulation cleanliness, products and final
delivery separate. Report only relevant artifacts actually produced.

For source/scaffold topology arrangements, deliver the current handoff defined in
工作过程 and its linked record. Use its checked control-volume rows for the
displayed balances and sketches, retaining reaction terms. The check verifies
declared structure, not source truth, numerical closure or Aspen execution.
Reuse an equivalent current project ledger through the same check rather than
maintaining a second engineering contract.

阶段收尾若发现有证据且值得复用的新方法或原则，将候选交主助手，按
[主动经验提醒](../chemical-engineering-expert/references/EXPERIENCE_INBOX.md#主动提醒使用者)
展示可审阅摘要并推进确认/投稿；拒绝不催促，已有有效授权不重复询问。
