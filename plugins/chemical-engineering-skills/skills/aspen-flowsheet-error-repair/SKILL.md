---
name: aspen-flowsheet-error-repair
description: Diagnose and repair Aspen flow failures using current authority, physical service, Control Panel/history, one evidenced change and same-case replay. Use for bad blocks, recycle/control/scale failures, product misses, I/O or run evidence defects; preserve process and precision contracts and separate local progress from strict delivery.
---

# Aspen Flowsheet Error Repair

## 工作过程

收到错误日志或不合理结果后，先保留可回退的候选文件，读取当前项目要求和同次运行的具体报错，再沿物流还原出错单元的真实用途。区分输入、物性、相态、循环与控制、产品目标、设备能力以及文件问题后，只针对有证据的原因作一组受控修改，交操作模块重跑，并观察原问题是否消失或暴露了下一问题。

纯文件或数值诊断不必重新设计全厂；但修复一旦改变负荷、温压、相态或连接，就按[阶段调用规则](../chemical-engineering-expert/references/DESIGN_STAGE_ROUTING.md)重查方法和设备，并让受影响结果重新计算。返回原报错、修改、同案复跑和剩余问题；修好一个块只表示局部修复，不表示全流程已经交付。

## First reads and scope

Read `references/ERROR_MEMORY.md`, the chemical expert's
`STRICT_ACCEPTANCE_AND_LEARNING.md`, and current project change-offset,
status and freeze ledgers. The triad remains:

`aspen-document-driven-flowsheet -> this repair skill -> aspen-plus-operations`

The process layer owns allowed changes. This skill diagnoses; operations
executes and supplies the single strict version-bound evidence gate.

## Repair Loop

1. Preserve the accepted candidate and freeze the current failure/allowed edits.
2. Classify resource/startup, input/card, property/phase, solver/recycle/control,
   process target, equipment capacity or delivery identity before changing anything.
3. Reconstruct the physical service and affected stream path before solver knobs.
   Convergence is not feasibility; heat/pressure paths and component fate matter.
4. Capture the current limiting message, object and same-run evidence. Apply one
   evidenced repair family on a protected candidate; inspect the next run again.
5. Recompute downstream consumers, inner quality controls, balances, utilities
   and equipment when the change affects them.
6. Report whether the original blocker is removed, another blocker was exposed,
   or the same hypothesis failed. That local result does not imply full acceptance.

## At the relevant failure, read the detailed method

出现逐点改参数仍无进展、Vary不动、重复写入或缺少随进料联动时，先按
[内置工具规则](../aspen-document-driven-flowsheet/references/aspen_builtin_solve_fit_tools.md)
分类，并检查实际自由度和依赖顺序；不能把“每轮只改一类故障”的诊断原则误用为
任何优化都要外部逐点试跑。工具结构完整后才继续有界响应分析或目标求解。

- Phase/specification or external-reboiler/APW consistency:
  `references/repair_workflow.md`.
- Recycle inventory, scale/root, Calculator ordering or startup state:
  `references/recycle_scale_control_repair.md`.
- Tower island/spec optimization: `aspen-tower-optimization-workflow`.
- Formal kinetics: current kinetics expert/freeze before touching rates.
- Mechanical I/O, events, lock/timeout, cards or exact-file verification:
  `aspen-plus-operations`; do not write another parser/COM lifecycle.

## Red lines

Preserve current method, property/kinetics, precision and product targets.
No hidden heater pressure rise, external outlet substitution or unapproved
SEP surrogate. Initial estimates/damping/solver method/iteration limits can
be tested after diagnosis, but they do not authorize lowering tolerances.

A user may explicitly authorize a current-case relaxation. Preserve its scope
and failed strict checks; all results/descendants remain case-only and cannot
enter self-evolution, shared success cases, default retrieval or rules.

## Acceptance and return

Keep `local_fix_verified`, `simulation_clean`, product gates and
`strict_delivery_passed` separate. Strict delivery needs complete supported
version/format counts, no actual same-run raw-history problems, valid run/file
identity and the exact final-path no-edit reopen, plus every current project gate.
Required Input, BLKSTAT and product values never override dirty/missing evidence.

Return changed files/cards, original and new diagnostics, source/run hashes,
affected consumers, verified scope and remaining actions. Audit logs may retain
all attempts; they are not automatically learning examples.

阶段收尾若发现有证据且值得复用的新方法或原则，将候选交主助手，按
[主动经验提醒](../chemical-engineering-expert/references/EXPERIENCE_INBOX.md#主动提醒使用者)
展示可审阅摘要并推进确认/投稿；拒绝不催促，已有有效授权不重复询问。
