---
name: aspen-double-effect-distillation
description: Plan or audit Aspen double-effect distillation connections, including cross-column condenser–reboiler coupling, liquid reflux, boilup, HeatX sides and net boundaries. Use for 双效精馏、双效塔岛连接; VRC/MVR compression and tower optimization retain their specialist workflows.
license: CC-BY-4.0
---

# 双效精馏连接与交接

## 工作过程

本Skill负责跨塔热集成的结构与边界。先确定本题是局部连接审查、完整双效岛规划，还是已授权模型改造；只读题不启动Aspen，不扩成优化或整厂。安装此方法不代表任何工况或跨版本卡片已经验证。

按活动登记定位本入口；向量索引未命中不代表该方法不存在，旧VRC检索材料也不能替换当前已选的双效构型。新增入口的文件可用性与索引是否已收录分别核实。

先按[化工专家](../chemical-engineering-expert/SKILL.md)核当前项目授权、中央及本专业[错误记忆](references/ERROR_MEMORY.md)，不把当前任务扩为无关阶段。
再读[边界与逐口检查](references/boundaries.md)，选择三项：进料/跨塔物料安排、LP再沸型式、热服务表示。HP/LP表示相对压力，不表示进料先后，也不能单凭其名称确认传热温位。

## 按选择读取

同时命中多行时合并必读范围：显式过程侧变体先读基本接口；补冷/补热加读热服务，分相/分级冷凝加读相态章节。纯内置端器热负荷抽象不强制套显式四口骨架。

| 当前结构 | 需读方法 |
|---|---|
| 显式过程HeatX；并联或底物流串联 | [基本物料连接](references/material_connections.md)：基本骨架、HP→LP和LP→HP底物流变体 |
| 自然循环、强制循环、HP部分冷凝/不凝气、分级冷凝 | 在基本接口上读[相态与循环变体](references/phase_and_circulation.md)的相关完整节 |
| 内置端器热流耦合、部分回收、补冷/补热或内外混合 | [热服务变体](references/heat_services.md)；采用显式物料侧时同时读取其基本接口 |
| 需要看图或解释接口 | [图件索引](references/FIGURES.md)，按构型查看；图不替代正文 |
| 核文献支持、适用域或软件证据级别 | [来源与知识边界](references/public_sources.md) |

所选必读范围若被工具截断，应补读缺段；按需读取不等于只看标题。不同构型可以组合，不能把全外置釜式骨架强加给合法内置端器、热虹吸或混合配置。多效扩展逐对核相邻热服务及全局净边界，不把两效图直接当完整多效设计。

## 输出与下一步

连接审查给出：采用构型/必要假设 → 真实物料箭头和独立热联系 → HP及LP液体回流、LP返汽/两相返回 → 本次控制体的净进出 → 已核/未知及其影响。局部输出明确写“本局部”，完整岛才列完整岛清单；不将未知流改名产品过审。

实际规划/改造另冻结当前进料、物性和相态、产品义务、允许改动及原接口；用同案数据核全段温焓、压降/压头、热量、组分和控制自由度。缺数据只限制相应结论，不用通用示意填项目数值。换热器两侧、回流和返汽服务不得靠图面位置或设备名字推断。

后续按任务交回已有owner：

- [塔优化](../aspen-tower-optimization-workflow/SKILL.md)：塔分离、有效Design Spec/Vary、初始化和同产品比较；不在此复制塔优化程序。
- [热泵替换](../aspen-heat-pump-distillation-replacement/SKILL.md)：VRC/MVR或压缩循环。普通双效不因外置HX就套用压缩机模板。
- [Aspen操作](../aspen-plus-operations/SKILL.md)：真实版本端口/级数/卡片、运行导出及唯一严格验收；[文档流程](../aspen-document-driven-flowsheet/SKILL.md)：有母流程时的授权变更与原接口回装。
- [设备反馈](../chemical-engineering-expert/references/PROCESS_EQUIPMENT_FEEDBACK.md)：实质工况/负荷变化后的同案能力与设备校核；真实EDR按当前任务需要进入原专用Skill。

结构可解释、热力学可行、设备可实现和精确文件通过是不同结论。只交出本次实际证据支持的层级。
