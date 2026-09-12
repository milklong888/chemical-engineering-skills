# Aspen Quick Router

Use this first when token budget matters. Open the detailed routing graph only
when the task crosses several skills or the route is unclear.

## 当前阶段 → 下一份资料

本页服务于已进入的文档流程。选择哪个专业 Skill、如何区分塔/热泵/EDR/设备/费用任务，
统一查[任务登记](../../chemical-engineering-expert/references/ACTIVE_ASSET_REGISTRY.md)，不在这里维护第二张专业表。

| 当前需要 | 读取入口 | 返回的依据 |
|---|---|---|
| 提取任务书或冻结/改变物性方法 | [来源协议](source_taskbook_and_gate_protocol.md) | 两遍来源核查、物性冻结及允许修改 |
| 新建骨架、严化岛或逐段接回 | [流程方法](aspen_workflow_playbooks.md) | 当前阶段和同版边界 |
| 实施正式动力学反应器 | 工作区登记的孙兰义图谱 `kinetics_expert_system.md`、`kinetics_freeze_template.md`，再交操作层 | 冻结的来源→换算→卡片链；仅写动力学说明才走文档 Skill |
| 打开运行与交付就绪 | [打开运行协议](open_run_readiness_protocol.md) | 当前文件可打开、Required Input 与运行证据 |
| 路径迁移、便携性或物理合理性异常 | [便携与合理性检查](delivery_portability_and_plausibility_gates.md) | 区分路径问题和工艺问题 |
| 查值、联动、目标、响应或优化 | [原生工具规则](aspen_builtin_solve_fit_tools.md) | 固定量/联动量与实际 solve_route 回执 |
| 修复主线已定位的顽固可运行问题 | [零警告修复](aspen_zero_warning_repair.md) | 有据假设、同案复跑与原始结果 |
| 需要复用脚本或材料切片 | [脚本目录](script_template_catalog.md)、[材料库](material_library_protocol.md) | 项目副本与来源记录 |
| 多层交接不清楚 | [协作图](skill_routing_graph.md) | 明确主线、输入、产物和交回对象 |

## Token Rules

- Load the references needed for the current decision; already-current reads can be reused.
- Search large references with `Select-String`/`rg` before opening sections.
- Prefer project authority files over old conversation memory.
- Use scripts to write logs/slices/readiness records instead of loading their
  protocols during routine work.
- Historical policy archives are not distributed. If a user supplies one for
  explicit audit, keep it outside default loading and check current authority
  before reusing any scoped statement.

## Return Rule

For source/scaffold/island/reconnect/change/delivery events, use the expert's
`DESIGN_STAGE_ROUTING.md` actual call contract. A returned node path is
navigation, not proof that knowledge or equipment checks executed.

Within an active document-driven flowsheet, delegated work returns to that
workflow. Independently scoped specialist tasks return to their own main task.
Use the relevant fields without repeating an existing contract:

```text
accepted/provisional/blocked:
evidence files:
current blocker:
next allowed action:
```
