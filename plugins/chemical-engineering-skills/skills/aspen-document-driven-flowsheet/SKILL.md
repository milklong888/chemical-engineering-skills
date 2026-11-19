---
name: aspen-document-driven-flowsheet
description: Coordinate document-driven process planning and Aspen construction, including process articles ready for first-model construction, staged rigorous replacement, repair routing and full-flow evidence under current source and change-offset authority. Use for process-route/scaffold/island/recycle integration; delegate Aspen mechanics and specialized tower/equipment work to existing skills.
---

# Aspen Document Driven Flowsheet

参数/卡片依据不明或warning无法解释时，先按[来源升级与留账](../chemical-engineering-expert/references/KNOWLEDGE_LOOKUP_ESCALATION.md)查询原生图谱、官方知识库及必要的网络来源，再提出有依据的修改。

## 工作过程

完整流程或节点—物流的来源/骨架安排，先冻结**模块排布**，再进入单元卡片：
逐来源块把预处理、反应、分离、回收/再生及产品/排放落到同一份
`nodes/streams`账，追清各组分的分支、回流和终端；沿真实接口核接收端相态、
温压与热量，必要时才放入换热、冷凝分相、泵或压缩等功能。
文字规划也要填[原边界与严化交接记录](references/source_scaffold_handoff.md)，
经[第1节的对应 source 检查](references/fullflow_generation_workflow.md#1-补全自然语言先闭合条件再建模)后回源逐句核语义。
单模块、纯职责分工或工段合同不因此被扩大为整厂拓扑任务。

单模块文字规划也要交接完整：必须实际读取
[单模块方法及交接检查](../aspen-plus-operations/references/unit_modeling_workflow.md)
的适用部分。输出当前目标—具体操纵/写入变量—边界来源—插入阶段—每轮执行先后
及验证对象，不能只说“用设计规定/计算器”。仅禁止启动Aspen时仍执行相关只读查询
和原 solve_route；真实数值与软件结果保持未验证。每座正式塔必须有有效DS配对方案。

逐模块严化前用
[单模块入口与必要条件](../aspen-plus-operations/references/unit_modeling_workflow.md)
确定主专业 owner、来源节点和现有脚本。塔按其完整流程强制 Design Spec/Vary；
Calculator/目标求解的插入时机、每轮顺序及主写入者依原内置工具规则记录，
不得以“调用相关模块”代替具体交接。

文字规划执行[第1节规划工作过程](references/fullflow_generation_workflow.md)，在项目内建立同一份交接记录。沿来源逐段填连接，就地补方法、热压接口、回流启动与计算依据，回原文反查后据此整理正文和图。通过原 `design_stage` 的 `source` 阶段保留最终 `planning_handoff` 路径、哈希和实际检查回执。只讨论方案、草稿或明确只要路线时用 `source_work=expert_plan`，依约定范围交付。

新建完整流程项目或用户索取可直接据以搭首版模型的完整规划时，`source_work=buildable_plan` 在交稿前触发三位采用同一模型和同一推理档的子代理，分别独立审核同版完整流程，即使只交工艺文章或明确不启动 Aspen。正文及所引依据应能让建模者独立重建首版的连接、输入、条件和判据。所有单元的首版必填输入逐项给出基准或启动值、单位、依据和适用范围。首版可用 SEP 表示分离工段的净分配，用 RStoic 表示有据的固定转化率。规划时同时查清严化分离方案及反应动力学资料，选定适用方法和可采用的资料，落实参数基准、适用限度和检查指标。详细严化求解在对应建模阶段进行。主代理给每位审查者派发同一份[完整任务说明](references/planning_review_brief.md)及冻结资料，逐项查缺、补证、改稿及重审受影响的链。常规缺项在本轮自行查证，真正无法取得的资料按[规划工作流](references/fullflow_generation_workflow.md#规划阶段先查明严化依据)核实可用替代并界定影响。重大歧义仍影响首版时，暂缓受影响部分的试跑和可开工结论。只交文稿时在源审闭合后结束；三份实际导出复核留到骨架真实运行后的阶段。

完整流程生成先读[全流程生成工作流](references/fullflow_generation_workflow.md)：补全自然语言要求及每模块物性依据，完成三份同模型、同推理档的独立流程链审查后，用SEP/RStoic建立包含必要加热、换热、压缩、泵及压力路径的完整骨架；真实运行，有循环时取得循环初值，无循环时记录依据，再完成三份针对同次运行导出的独立逐模块复核。逐模块细化沿用首版的入口基准、工艺目标、参数及允许调整范围，按专业方法实现设计规定、求解和验收。每岛以同版全设备选型反馈为回装前收尾门；合格模块逐个替换回原位置，完整接回后再检查所有适用物理设备并复算。这里的“切岛”不表示重新划分整厂路线。已有模型从实际阶段补齐证据和修复，不无理由从零重建。

图谱在选择方法和处理未知问题时介入，设备程序在骨架有负荷、每岛严化末尾及接回后分别复核，执行[阶段调用规则](../chemical-engineering-expert/references/DESIGN_STAGE_ROUTING.md)。若设备限制要求改工况或结构，先更新项目决定，再交操作模块修改和重算；目录无型号或偏小不自动拆设备。最终交付的是同一版本的模型、来源和修改记录、全流程结果及真实验收证据；简化骨架和单岛收敛不冒充最终全流程。

交付含节点、物流或简化占位的 `source` / `scaffold` 流程安排时，现在就完成[边界与严化交接记录](references/source_scaffold_handoff.md)及其结构检查。每个简化占位要有接手专业（未定时写选择条件）、必要输入和必须返回的结果；循环既列返回端，也列来源端，未知端点明确保留。只做这类流程安排、尚不能运行模型时仍交这些内容，不能以“以后严化”或“另行立项”代替当前交接。阶段查询回执不代替这份安排记录。仅交团队职责和工段合同而未交付节点—物流拓扑时，使用[工段合同模板](../aspen-two-section-flowsheet/SKILL.md#section-contract)和适用的阶段查询，不为满足拓扑检查器另造一张流程图。

## 既有流程接入换热网络

HCH 或换热配对表接入已有流程时，按[增量接入规则](references/hen_incremental_integration.md)明确换热服务、拟用模型和原节能回路的保留范围，再分步实施。

## Authority First

弱提示词同样先进入上述工作流第1节：复用原有循环、分离和排放/吹扫经验，主动补出有据的流程方案；区分原文要求、推导、工程提案和待定，不让用户逐项点名，也不把旧案例数值当默认。完整建模规划的补项随同版正文进入三份独立全链源审；实际运行后按原规则完成三份导出复核。

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

`prompt completion and three independent whole-plan source reviews -> SEP/RStoic full-flow
scaffold with energy/pressure equipment -> native run, recycle initials and three
independent checks -> individual module refinement -> replace at original interfaces
-> whole-flow equipment coverage and feedback -> rerun and exact-file verification`

For full-flow generation, carry the hash-bound `fullflow_contract` through the
existing design-stage entry. Missing prior-stage evidence is ACTION_REQUIRED,
not an optional reading suggestion; the detailed owner above defines the two
review gates. Narrow tasks retain their existing scope.

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
  a clean status. Default and pre-existing solver tolerances are frozen in
  both directions; compare value and default/explicit card state to the
  pre-edit baseline. Physical purpose, mass/component fate, pressure/energy paths,
  control/recycle and product targets require same-candidate evidence.
- Delivery requires a no-edit rerun of the exact final file, confirmed run
  completion and identity, complete clean Control Panel messages and raw
  history, and every applicable project gate. Use the operations checker and
  consult the native Summary for anomalies or expressly requested count proof.
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

At a real handoff, check the actual files and open findings under [final delivery review](../chemical-engineering-expert/references/DELIVERY_FINDINGS.md). Ask once in the user-visible reply whether this revision is finished or needs a change. On explicit closure prepare the local retrospective and proposed submission table in that turn. Follow the expert's `EVOLUTION_LOOP.md` to condense macro prompt
principles and test data-pattern hypotheses separately; keep specific values
and operations below the prompt layer. No reusable increment means no change.

ACM自定义气体膜、材料参数与流程条件混用或原生灵敏度交接时，读取[膜分离案例](references/cases/acm_membrane_modeling.md)。图形摘要、PFD布局或交付包更新按专家层[图文与文件交付](../chemical-engineering-expert/references/ENGINEERING_PRESENTATION.md)路由；只核当前任务范围，不自动启动模型或图纸生成。

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

<!-- milklong-attribution:start -->
作者：milklong（GitHub：milklong888）。[版权与AI辅助编辑署名规则](ATTRIBUTION.md)。
<!-- milklong-attribution:end -->
