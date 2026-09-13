# 任务入口与活动资产

本页是本发行包 19 个 Skill 的任务导航。安装根为 `{CHEM_SKILLS}`；模块名和入口保持稳定。
先按交付目标选择一条主线，再只加载当前动作需要的专业内容。分组便于查找，不表示先后顺序、
强制组合或新的事实权威；具体要求以各 Skill 和[规则归属表](CANONICAL_RULE_OWNERSHIP.md)为准。

## 怎样读这张图

- **主导**：当前交付目标的专业 owner；化工专家提供判断与证据层，不另造一条软件执行主线。
- **协作**：主线缺少具体能力时再加载，如卡片实现、塔水力学或真实 EDR。已有充分结果可直接复用。
- **检查**：核当前任务要求和专业 owner 的验收证据。导航命中、文件存在和返回状态均不能代替执行。
- **不适用**：按表中边界排除相近但不同的任务。目标或证据未知时，走[决策树](TASK_DECISION_TREES.md)的区分查询。

下表的“接收 → 交回”是信息交接，不要求用户预先备齐所有材料；能从当前来源推导的先推导，
缺口只限制依赖它的结论。一个 Skill 可以独立接单，也可以作为另一主线的协作模块。

## 判断与分工

| 主导入口 | 何时进入 | 接收 → 交回 | 按需协作与边界 |
|---|---|---|---|
| [chemical-engineering-expert](../../chemical-engineering-expert/SKILL.md) | 方案、依据或可行性判断 | 当前问题、资料、允许修改 → 设计合同、来源分级和结论 | 相关专业按需实施；具体卡片与公式仍回各自 owner |
| [subagent-dispatch](../../subagent-dispatch/SKILL.md) | 并行事实任务、依赖交接或重叠编辑协调 | 边界、材料、依赖与写入范围 → 可复核产物及主助手接纳结果 | 主助手负责最终整合；按依赖安排先后，不能多人同时写同一模型；分工规划不强制实际委派 |

## 流程组织

| 主导入口 | 何时进入 | 接收 → 交回 | 按需协作与边界 |
|---|---|---|---|
| [aspen-document-driven-flowsheet](../../aspen-document-driven-flowsheet/SKILL.md) | 从文档建流程、严化与接回 | 当前来源与阶段 → 同版模型、阶段证据和未闭合项 | 需要分段/塔/热泵时转相应模块，操作由 operations 实施 |
| [aspen-two-section-flowsheet](../../aspen-two-section-flowsheet/SKILL.md) | 划分工程段，审查气液交接、溶剂返回与跨段职责 | 当前连接与段职责 → 段合同、跨段物流、未定分支与连接证据 | 只有总流量时不默认分相位置；已处在文档流程内则交回该流程 |

## 软件动作与同案修复

| 主导入口 | 何时进入 | 接收 → 交回 | 按需协作与边界 |
|---|---|---|---|
| [aspen-plus-template](../../aspen-plus-template/SKILL.md) | 仅建立组分模板 | 可追溯组分/CAS清单 → 回读过的组分模板 | 只核组分与文件；出现 Aspen 一词不自动补建生产流程 |
| [aspen-plus-operations](../../aspen-plus-operations/SKILL.md) | 已定合同的软件实现、读值或文件核验 | 获准动作、当前文件/版本 → 节点回读、运行/导出与原始证据 | 工艺 owner 决定路线；只读任务不自动改参数或运行 |
| [aspen-flowsheet-error-repair](../../aspen-flowsheet-error-repair/SKILL.md) | 已有流程的错误与失效诊断 | 当前失败、历史与身份 → 有据修改、同案复跑和剩余缺口 | 按需调用 operations；修复成功与全流程交付分别判断 |

## 塔、改造与适应性研究

| 主导入口 | 何时进入 | 接收 → 交回 | 按需协作与边界 |
|---|---|---|---|
| [aspen-tower-optimization-workflow](../../aspen-tower-optimization-workflow/SKILL.md) | 塔分离方案、严格模型与工况优化 | 来源冻结的分离义务和边界 → 同产品比较、塔岛与接回结果 | 塔径/内件交 chemical-tower-design；热泵替换转专用模块 |
| [aspen-heat-pump-distillation-replacement](../../aspen-heat-pump-distillation-replacement/SKILL.md) | 空塔/VRC/MVR替换，或只审塔改造节能与新增电耗 | 原塔边界或改造表 → 同基准收益、设备状态缺口；获准实施时再交热泵岛与接回证据 | 先识别新增耗电设备；审查分支不要求建模，真实 EDR 调 edr-rating |
| [aspen-adaptive-generalization-loop](../../aspen-adaptive-generalization-loop/SKILL.md) | 跨进料模板适应与规律验证 | 代表工况、同基准控制与范围 → 受检规则和批量证据 | 求解工具先走统一 solve_route；任务内试算不自动晋级共享经验 |
| [chemical-tower-design](../../chemical-tower-design/SKILL.md) | 塔尺寸、内件与水力学设计 | 当前塔负荷、物性和结构依据 → 尺寸/水力学、图纸或机械交接 | 需改分离工况时交回流程/塔优化；SW6仅在明确请求时进入 |

## 设备核查、压力与交付

| 主导入口 | 何时进入 | 接收 → 交回 | 按需协作与边界 |
|---|---|---|---|
| [chemical-equipment-selection-audit](../../chemical-equipment-selection-audit/SKILL.md) | 审查设备报告、公式链和参数来源 | 报告/参数与标准证据 → 设备账本、公式审计和缺口 | 需要确定性计算时调用 equipment-design-app；不把审核等同于运行软件 |
| [equipment-design-app](../../equipment-design-app/SKILL.md) | 调用随包设备计算和选型后台 | 同候选工况、来源/范围 → 计算轨迹、能力约束或数据缺口 | 真实能力限制交回工艺 owner；目录无覆盖不直接推出并联/分级 |
| [aspen-edr-rating-delivery](../../aspen-edr-rating-delivery/SKILL.md) | 真实 EDR 换热器校核与交付 | 换热服务、同版模型与 EDR 依赖 → EDR身份、结果及工程门证据 | HeatX Detailed/Shortcut 不等于 EDR；文件操作由 operations 支持 |
| [aspen-pressure-pfd-delivery](../../aspen-pressure-pfd-delivery/SKILL.md) | 全流程压力路径、PFD和交付包 | 压力拓扑或已核实结果 → 压力审计、图纸与交付文件 | EDR转专用模块；只排版则只处理已有证据和版式 |
| [sw6-scripted-equipment-design](../../sw6-scripted-equipment-design/SKILL.md) | SW6 文件传参/读回，或容器文件的字段偏移与序列化风险审查 | 文件/软件身份、版本及已有映射 → 风险分级、传参回读与报告证据状态 | 软件未明先审风险，不推定 SW6；一般选型走 audit/app；字节写入不代表计算通过 |

## 费用与来源说明

| 主导入口 | 何时进入 | 接收 → 交回 | 按需协作与边界 |
|---|---|---|---|
| [aspen-flowsheet-cost-skill-builder](../../aspen-flowsheet-cost-skill-builder/SKILL.md) | 块到实物/采购项映射、重复计费审查，或新流程建立费用方法 | 文字清单或模板、设备族与已有经济基准 → 物理候选与待核采购范围；需要计算时再交来源、尺寸/购置费配方和批量方法 | 映射审查不要求先建模型或生成 Skill；费用数字仍须来源与审查 |
| [aspen-non-reactor-equipment-cost](../../aspen-non-reactor-equipment-cost/SKILL.md) | 已有费用流程的非反应器费用提取 | 同案BKP/APW或验证清单、经济基准 → 逐设备费用与覆盖缺口 | 需生成 Scenario1 时按本模块；新费用方法回 cost-skill-builder |
| [aspen-kinetics-documentation](../../aspen-kinetics-documentation/SKILL.md) | 写清动力学来源及 Aspen 换算输入 | 文献、冻结台账、卡片/USER来源 → 可追溯动力学说明 | 反应参数权威仍是当前冻结链；只写说明不擅自改模型 |

## 交接后怎样继续

交接只补主线当前缺少的信息：任务/当前版本、允许修改、输入及单位来源、实际产物及证据、
未闭合项和受影响消费者。已有合同用路径和版本引用，不全文抄写。未执行与执行失败分别记录。
文档全流程内的岛交回文档流程；独立塔、模板、设备或说明任务交回原主任务，不自动扩大成全流程。
修改实质工况后，按原[设备反馈](PROCESS_EQUIPMENT_FEEDBACK.md)和[阶段规则](DESIGN_STAGE_ROUTING.md)复算并回接。

各模块的 `references/ERROR_MEMORY.md` 保存适用检查，`NEW_KNOWLEDGE.md` 保存新增方法状态；
只读被选模块的相关项。备份、发行镜像与历史项目不成为第二套活动权威。

## 随包图谱及其治理入口

后台根目录为`{CHEM_WORKSPACE}/chemical-engineering-runtime`，以下位置相对此根。
先读各图谱的错误记忆，再按最高充分层检索；新知识先登记候选与来源，不能直接
追加到已签名的运行数据库或向量矩阵。

| 图谱 | 原节点与查询资料 | 错误/新知识入口 |
| --- | --- | --- |
| 化工原理 | `knowledge/chemical_principles/knowledge_graph/` | 同目录`00_ERROR_MEMORY.md`、`NEW_KNOWLEDGE.md` |
| 孙兰义方法图谱 | `knowledge/sun_lanyi/knowledge_graph/` | 同目录`00_ERROR_MEMORY.md`、`NEW_KNOWLEDGE.md` |
| Aspen V10操作细节 | `knowledge/aspen_v10/knowledge_graph/` | 同目录`00_ERROR_MEMORY.md`、`NEW_KNOWLEDGE.md` |
| 设备规则及标准事实 | `backends/equipment/knowledge_graph/`、`backends/equipment/data/` | `knowledge/equipment/00_ERROR_MEMORY.md`路由到已有专业owner，`knowledge/equipment/NEW_KNOWLEDGE.md`记录待审入口 |

统一查询为`tools/expert_cli.py`。原始教材/商业帮助整页、私人项目图谱与真实
工程结果仍是可选本地资产；位置、来源、版本和项目范围按工作区
LOCAL_KNOWLEDGE_GRAPH_LINKS.md登记。缺少的是具体原件或证据时，不能把包内
已经提供的结构化知识和算法也说成未安装，更不能以其他项目数值补齐。
