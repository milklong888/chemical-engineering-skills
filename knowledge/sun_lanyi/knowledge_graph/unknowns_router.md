# 未知情况路由表

用途：Codex 在 Aspen Plus 工作中不知道如何选方法、补证据、填卡片或排障时，
先按本表路由，不凭预训练记忆直接猜值或改流程。

## 0. 必读门槛

1. 先读 `00_ERROR_MEMORY.md`，再确认当前项目 authority、变更偏移表、源冻结台账和最新同案例证据。
2. 若用户指定方法、公式、软件路线或禁止替代项，先冻结 required-method lock；实现层不得静默改法。
3. 任何模块创建或重建都先做物性方法门：介质族、温压范围、预期相态、极性/非理想性、Henry/气体溶解、电解质/缔合、共沸/LLE/萃取/溶剂行为、二元参数或 PCES/结构支持、所选方法、缺口和状态。状态不是 `accepted` 时，只允许明确标注的诊断或临时分支。
4. 原文未直接给值时，执行化工专家层的 derivation-before-missing；不得把“没检索到原句”等同于“信息不可得”。

## 1. 快速路由

| 未知情况 | 先打开 | 再打开 | 允许动作 |
| --- | --- | --- | --- |
| 不知道物性方法 | `../chapter_extracts/ch03_property_methods_and_regression.md` | `knowledge_graph_index.md` | 先按真实介质和相行为选方法并核参数覆盖，再建模块 |
| 组分找不到或需要假组分 | `../chapter_extracts/ch02_flowsheet_setup_basics.md` | `../chapter_extracts/ch13_petroleum_distillation.md` | 核对 component ID、assay 与假组分规则；不自造物性 |
| 流股温度、压力、流量或组成不明确 | `../chapter_extracts/ch02_flowsheet_setup_basics.md` | 当前项目源台账与导出 | 先提取、换算、闭合衡算；无法闭合的最小缺口才标 `U` |
| 不知道选哪个单元模块 | `knowledge_graph_index.md` | 对应第 4–8 章节点 | 按物理作用、相态、自由度和证据选择，不按熟悉程度选择 |
| 反应器类型不确定 | `../chapter_extracts/ch08a_nonkinetic_reactors.md` | `kinetics_expert_system.md` | 先判断是否有正式动力学；转化率/收率资料不等于动力学 |
| 动力学参数或 basis 不确定 | `kinetics_expert_system.md` | `kinetics_freeze_template.md` | 冻结来源—单位—换算—卡片—导出链；否则阻断或临时化 |
| PowerLaw 指数不确定 | `../chapter_extracts/ch08b_reactions_kinetics_cards.md` | `../chapter_extracts/ch08f_kinetics_parameter_card_audit.md` | 回到源速率式和 basis，不从案例迁移指数 |
| LHHW 是否可简化 | `kinetics_expert_system.md` | `../chapter_extracts/ch08b_reactions_kinetics_cards.md` | 保留推动力与吸附结构；不能等价表达则 USER 或阻断 |
| RCSTR 卡片不确定 | `../chapter_extracts/ch08c_rcstr_cards.md` | `kinetics_expert_system.md` | 先闭合相态、体积/停留时间、压力和热边界 |
| RPlug 卡片不确定 | `../chapter_extracts/ch08d_rplug_cards.md` | `kinetics_expert_system.md` | 先定 reactor type、几何、压降、温度和传热 |
| RBatch 卡片不确定 | `../chapter_extracts/ch08e_rbatch_cards.md` | `kinetics_expert_system.md` | 先闭合进料总量、时间、操作步骤和停止判据 |
| RadFrac 不收敛 | `../chapter_extracts/ch12_convergence_strategy.md` | `../chapter_extracts/ch11_process_simulation_workflow.md` | 先查物性、规格自由度、Err/Tol、初值和物流相态，再调算法 |
| 普通塔初设或严格塔迁移 | `classic_cases_playbook.md` | `../chapter_extracts/ch07_column_shortcut_and_absorption.md` | Shortcut 只供可适用体系的初值，最终用严格塔和同目标验证 |
| 复杂精馏路线 | `classic_cases_playbook.md` | `../chapter_extracts/ch10a_extractive_azeotropic_pressure_swing.md` | 先判 ED/AD/PSD 等机理，再核物性、相图与溶剂/压力依据 |
| 节能精馏、DWC、热泵或 HIDiC | `classic_cases_playbook.md` | `../chapter_extracts/ch10c_energy_saving_distillation_structures.md` | 先有常规基线，再逐步加入热耦合、压缩与连接并核能量品位 |
| 塔优化、Thermal/Hydraulic/NQ | `classic_cases_playbook.md` | `../chapter_extracts/ch10d_column_analysis_nq_curves.md` | 保持产品规格，按 Thermal→Hydraulic→NQ→严格复核 |
| Design Spec、Calculator、Sensitivity、Optimization | `classic_cases_playbook.md` | `../chapter_extracts/ch09_flowsheet_options_analysis.md` | 先定义未知量、操纵量、约束和自由度，再选工具 |
| 反应精馏或三相塔 | `../chapter_extracts/ch10b_reactive_three_phase_distillation.md` | `kinetics_expert_system.md` | 同时审反应段、holdup、动力学、相平衡与热/压边界 |
| 塔水力学 | `../chapter_extracts/ch15_appendices_tools.md` | `../chapter_extracts/ch10d_column_analysis_nq_curves.md` | 先取得同塔几何与负荷，再审操作区；手册候选不是软件通过 |
| 能量分析或换热网络 | `../chapter_extracts/ch15_appendices_tools.md` | `../chapter_extracts/ch06_heat_exchanger_modules.md` | 先确保物料流程收敛并冻结 utilities、温度区间与夹点约束 |
| 动态模拟导出失败 | `../chapter_extracts/ch14_dynamic_simulation.md` | `../chapter_extracts/ch05_pressure_modules.md` | 先过压力路径、阀门、设备尺寸、控制自由度与稳态一致性 |
| EDR 身份、评级或交付不清 | `project_cases_0710_edr_rating_delivery.md` | `../../设备设计选型工作包/knowledge_graph/project_overlays/aspen_edr_rating_delivery/00-index.md` | 区分 Detailed 与 true EDR，核同设备文件、结果和精确交付证据 |

## 2. 原文未直给时的推导路由

依次检查：同一权威文件的表格/图注/附录和邻近段落 → Aspen/CSV/JSON/脚本等
结构化证据 → 单位与 basis 统一 → 化学计量与代数 → 总量/组分/元素衡算 →
能量与压力关系 → 物理界限、插值和尺度推算 → 有来源且有适用域的临时工程估计。

最终必须区分：`not_yet_found`、`derived`、`bounded`、`provisional_estimate`、
`requires_external_evidence` 和 `blocked`。只阻断受影响的结论，并写明最小缺失变量。

## 3. 动力学强制分支

请求中包含以下任一类内容，直接进入 `kinetics_expert_system.md`：

- `k`、`E`、`A`、`B/T`、Arrhenius、活化能、速率常数；
- `POWERLAW`、`LHHW`、`USER`、Exponent、反应级数；
- 分压、摩尔分率、活度、逸度、Molarity、吸附项；
- 催化剂质量、床层体积、rate basis、浓度 basis；
- RCSTR、RPlug、RBatch 的动力学反应。

若资料只给转化率、收率或产物分布，不进入正式动力学填卡。先查
`ch08a_nonkinetic_reactors.md`，判断 RStoic、RYield、REquil 或 RGibbs 等
非动力学表达是否与任务证据和目的相符。

## 4. 经典案例分支

以下触发可打开 `classic_cases_playbook.md`：复杂/节能/反应精馏，塔分析与优化，
Design Spec/Calculator/Sensitivity/Optimization，流程分析工具或讲义相似案例。

只迁移路线、字段意义、诊断顺序和检查清单。案例数值、物性方法、塔参数、
动力学、流股和设备规格不得自动迁移；涉及动力学仍优先走动力学强制分支。

## 5. 必须回源 PDF 或渲染图的情况

- OCR/抽取使字段名、上下标、希腊字母、分子分母或正负号不清；
- 表格列对齐、单位、指数或卡片选项可能改变结论；
- 下拉选项、USER 字段、Solids、Rate basis、RPlug 压降细节未完整抽取；
- 同一数值在不同页/版本冲突，或图片是唯一权威载体。

视觉复核只恢复源内容，不得借机补入模型记忆中的“常用值”。

## 6. 状态标签

- `accepted`：当前任务所需的来源、推导/假设、实现和验证已闭合。
- `frozen`：必须保持的来源—单位—换算—输入—导出链已锁定。
- `provisional`：可用于临时模型或筛选，但含明确假设或待核证据。
- `bounded`：只有区间或上下限可辩护。
- `diagnostic_only`：只用于排障，不可交付。
- `quarantined`：错误范围、冲突、过期、禁迁移或不安全。
- `blocked`：最小不可替代缺口阻断了命名结论。

最终交付不得把 `provisional`、`diagnostic_only`、`quarantined` 或 `blocked`
写成正式接受结果。

## 7. 特殊塔：跳过 DSTWU 的严格塔直启

用于吸收、汽提、低温甲醇洗/溶剂吸收、萃取精馏、共沸精馏、VLL/三相、
反应精馏、电解质/酸水汽提、石油假组分，或无法定义有意义轻重关键组分的体系。

1. 打开 `special_columns_direct_radfrac.md`。
2. 写 `DSTWU-SKIP` 记录，说明物理原因和所选分离机理。
3. 建立 `<project>-<equipment>` 隔离塔岛。
4. 先建最小严格塔 `RIG-INIT`：物性、有效相、冷凝器/再沸器、级数或填料高、进料/溶剂位置、压力路径和简单操作规格。
5. `RIG-INIT` 未获得合理温度、相态和物料衡算前，不加 Design Spec、循环闭合、热集成、水力学或苛刻纯度目标。
6. 逐步复制为 `RIG-FEED`、`RIG-SENS`/`RIG-ANALYSIS`、`RIG-SPEC`；仅在严格基线收敛后加有界 Design Spec/Vary。
7. `RIG-SPEC` 失败表示规格/窗口失败，不授权改用 SEP/SEP2/SEPARATOR 冒充物理塔。

## 9. Ordinary Tower Feed-Stage Selection

普通精馏且当前项目有明确轻/重关键组分回收或产品纯度目标时，先冻结进料、
LK/HK、产品目标、压力路径和可操纵变量。适用时用 DSTWU 只给初值；不适用则
转 `special_columns_direct_radfrac.md`。保持 Design Spec/Vary 有效地扫描进料级，
从同一规格下的回流与塔负荷趋势选拐点/边际改善低区，再严格复跑产品、回收、
回流、负荷、压力和分流证据。

T03101A 案例的级数、进料级、回流比、D/F、压力、流量、组成或物性方法不得
作为默认值迁移。

## 10. Non-GUI Aspen EDR Rating and Delivery

当请求要求所有合格 HeatX 有 EDR、核 true EDR、禁 GUI 自动化或交付 EDR 加
零告警 Aspen 文件时，打开 `project_cases_0710_edr_rating_delivery.md`。

先盘点 HeatX/Heater；两股 HeatX 才进入覆盖候选。解析同设备 `.EDR` 的 TascMsg
与物理结果，不信任单一 COM 返回码。读回 TASCPLUS-RIG、program mode、文件、
执行字段和报告；拒绝 Detailed-only、clean-history-only 和 path-string-only 分支。
EDR 工程门与 Aspen 交付门分开，最终在精确复制的交付文件上无修改重开、运行、
导出并验证 Required Input、Run Status/history、产品、循环和能力指标。

