# 设备设计图谱与脚本 — 离线知识图谱入口

本目录保留原图谱的公式族、参数来源、证据边界与设备方法路由，配合原确定性后台脚本；不包含原项目报告/私有 ledger。

## 包内使用顺序

1. `../README.md` 给出真实可运行接口与数据边界；包内 `equipment-design-app` 技能负责调用。
2. `aspen_equipment_derivation_chain.md`：原始字段、单位换算、参数包和匹配链。
3. `formula_family_nodes.md`、`parameter_source_nodes.md`：公式适用性和来源类型。
4. `evidence_boundary_nodes.md`、`software_boundary_graph.md`、`manual_decision_gates.md`：软件、厂家和人工确认门。
5. `standards_graph/README.md` 与设备族节点：方法和原标准事实身份。
6. `../equipment_selection_graph/README.md`：型号状态机和标准系列。
7. `mismatch_audit_playbook.md`：有冲突时按原顺序复核。

原 project_overlays、项目统计/outputs、项目专用索引和审核历史均为可选本地资料，未随本发行提供；不伪造其验收结果。

## 核心原则

- “设备设计图谱与脚本”是总包；标准证据、项目叠加图谱和设备族 skill 均按子层/调用关系接入。
- 确定性脚本是设备匹配主决策器；协议 1.9 下大模型先选择登记的简单推导配方，也可把无条件默认型式升级为冻结上下文明确支持的登记条件型式，数值与型式均由程序复算。登记配方仍不能闭合时，模型可为 `missing_input_registry` 中的预选缺项给出结构化工程估算；只有具备同工况/工程依据、假设、数值边界或登记枚举、置信度和敏感性且通过程序校核的估算，才可 missing-only 自动带入。该值必须显式为 `J/provisional` 且封顶 `TYPE_SCREENING`；自由设备型式、虚构规则、越权消歧、厂家型号选择或覆盖物理/证据硬门均禁止。
- 所有可闭合计算必须将目标量写回 `derived_parameters`，再构造带哈希的选型特征向量。界面显示公式但下游取不到结果，属于链条失败。
- Aspen 导出是流程侧推导起点，不是机械/厂家终证；运行状态证据未哈希复核时只能 provisional。
- `final_model` 需要 `equipment-evidence-manifest-v1` 的逐门工件映射和 `equipment-audit-approval-v1` 独立审核记录；清单自报或重复文件不能闭门。
- 方法可以迁移，数值不自动迁移。
- 脚本按版本化规则选择公式族和参数来源类别；正式工程批准仍须满足项目权威、软件/厂家和人工签认门，但不得改由大模型自由判断。
- EDR、SW6、Column Internals、厂家曲线、正式动力学卡片不得由简化脚本替代。
- 标准、手册、教材、课程设计资料必须分清：标准查表入口、方法参考、软件边界、禁止迁移值；不得把手册示例值或教材案例值当成本项目默认值。
- 对不上时不强行通过，保留 `review` 并写明根因。

---
离线迁移说明：本文件保留原图谱的方法与边界正文；同案数值、私有审计及未随包的原件不作公共输入。来源及字段级剔除记录见 `RESTORATION_PROVENANCE.json`。本节点不升级原计算或证据状态。
