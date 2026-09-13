---
name: aspen-tower-optimization-workflow
description: Optimize and reconnect a source-frozen Aspen distillation or solvent-recovery island using the required shortcut/rigorous route, live Design Specs, same-product comparisons and hydraulic/equipment checks. Use for tower optimization, DSTWU-to-RadFrac, special columns, recycle quality and pressure/vacuum audit; no universal example values.
---

# Aspen Tower Optimization

## 工作过程

先固定当前塔的进料、物性、产品纯度、产量和回收要求，判断指定的快捷方法是否适用；适用时用DSTWU给严谨塔初始化，不适用时说明原因并按获准方法建立基准。基准稳定后，复用同版有效响应区间，未知时先做有边界的敏感性分析。按实际目标确定直接约束或有独立操纵量的在线Design Spec，再比较不同操作点的热量、回流和设备负荷。

每个候选都必须在同一产品基准下比较。流量、级数、温压或负荷变化时，按[阶段调用规则](../chemical-engineering-expert/references/DESIGN_STAGE_ROUTING.md)调用知识与设备检查，再交塔设计模块核对水力学；有真实能力限制才评估并联等方案。合格塔岛逐个接回全流程，并用新的入口和循环重新验证，不能把岛内最优点直接当整厂最优。

## Authority First

Read `references/ERROR_MEMORY.md`, the chemical expert's strict
acceptance/learning policy, and the current project change-offset plus tower
ledger. Upstream `aspen-document-driven-flowsheet` owns route, feed,
products and property/phase model; operations owns mechanical cards and the
single strict Summary/history implementation.

## Choose the route

Ordinary key-based distillation may use DSTWU after source, feed, keys,
recoveries, pressure and targets are frozen. Preserve a user-required
DSTWU→RadFrac sequence; the initialization values come from that task, not
an old taught multiplier.

For azeotropic/extractive, absorber/stripper, VLL/reactive or no-meaningful-key
duties, record why shortcut assumptions do not apply and use the authorized
rigorous route. Do not silently substitute a different required method.

## Do the next stage, then verify

调回流、采出、溶剂、压力或热负荷前，按
[内置工具规则](../aspen-document-driven-flowsheet/references/aspen_builtin_solve_fit_tools.md)
完成工具分类，并按[阶段规则](../chemical-engineering-expert/references/DESIGN_STAGE_ROUTING.md)
实际执行 `island` 检查；准备求解与比较基准时也要完成现有资料支持的查询，
不以独立 `solve_route` 回执替代岛阶段。找指定指标用 live SPEC/VARY；看未知响应先 Sensitivity，
已有同版有效区间可复用；多个连续变量在产品约束下寻优先评估原生 Optimization。
板数、进料板等离散变量分开编排，每个候选内重解质量控制，不固定旧内层操纵值。

交出求解方案时列明外层变量、产品约束，以及每个必要内层目标对应的独立操纵量、
边界和主写入者。只写“逐点重解质量目标”不构成控制配对。未有资料证明另一个
获准自由度时，明确记录内层操纵量尚未确定；保留“至少/不超过”为直接不等式，
不能为配 Design Spec 擅自把它改成等式，也不能让内外两层争用同一变量。

`target/property freeze -> shortcut or justified rigorous initialization ->
converged baseline -> establish/reuse bounded response evidence -> live SPEC/VARY -> full-flow
reconnect -> hydraulics/equipment/pressure -> strict same-file verification`

Reconnect applies when a real parent section/full-flow is in the authorized
task. A standalone tower task returns an accepted-for-scope island and its
boundary contract; it does not fabricate a larger plant.

Read `references/tower_optimization_workflow.md` when executing the stage,
special-column or hydraulic details. Use an optional user-supplied local textbook graph and the legally installed
current Aspen help for fragile card rules; source bodies are not bundled.

- Define a real target, bounded manipulated input, units and applicability for
  each spec. A fixed offline sweep is not a live Design Spec.
- Every outer optimization point re-solves the authorized inner quality
  controls. Compare energy/cost only for matching capacity, purity and recovery.
- Conflicting specs are diagnosed; no target is silently dropped and no
  precision is relaxed to obtain a strict pass.
- Pressure drops, reflux, stage count, HETP, packing and capacity limits require
  current source/geometry/traffic evidence. There are no global pressure-drop,
  inlet-pressure-fraction or old project purity defaults.
- Parallel towers require attributable capability/whole-system justification
  and actual same-basis reconnect verification. Equal splitting is an
  assumption to verify, not a rule for every multi-train design.
- A converged material tower or HYDRAULIC=NO case is not a software hydraulic
  rating. Keep material, source-static, preliminary, software and vendor/
  mechanical evidence levels separate.
- Use `chemical-tower-design` and the expert's equipment-feedback gate for
  section/load-case envelopes and downstream geometry/cost/report propagation.
  Use the dedicated heat-pump replacement skill for VRC/MVR.

## Return contract

Return current tower ledger, same-run feeds/products, live spec/residuals,
pressure/heat/power, hydraulic/selection state and exact-file evidence.
All strict Summary counts for the supported real schema and actual raw
history must pass; products and full-flow gates remain additional requirements.

A relaxed local result is labeled case-only and excluded with all descendants
from learning/default retrieval. Historical case examples and prior entry archives are not distributed; optional
same-case local evidence never becomes a generic default.

阶段收尾若发现有证据且值得复用的新方法或原则，将候选交主助手，按
[主动经验提醒](../chemical-engineering-expert/references/EXPERIENCE_INBOX.md#主动提醒使用者)
展示可审阅摘要并推进确认/投稿；拒绝不催促，已有有效授权不重复询问。
