# 完整建模规划独立审查任务

独立审查本次冻结版本的整篇工艺规划。按下附的冻结输入读取当前正文、设计基准、交接账和规划检查回执。报文中的 `evidence_root` 是绝对路径，按此解析这四份文件及其内部引用的相对路径。读取前核 SHA-256，回填 JSON 证据引用时保留原引用的路径字符串和哈希。自行从正文和引用逆向重建拟建流程，随后用结构化记录对照。逐一覆盖所有模块、连接、外接进料、循环、排放和终端。用当前来源、计算和明确的工程判据评价每处。冻结输入只读。保留你自己的解读，不依赖其他审查员或主代理的结论。

沿四份输入读取其中所引的原始依据。包括 `source_review.documents`、关键输入的来源、规划计算回执，以及每个反应与分离模块 `planning_research` 中所选候选和关系式所引用的论文、技术材料、定位摘录或同案例证。优先核对决定目标、选型或适用范围的原页、表、图与方程。在相应 `observed_result` 或 `issues.finding` 写出实际读到的来源、位置、关键数值或关系、单位与适用范围。文件不可读取、缺原文位置或证据不足时，记录对应引用、已查路径与工程影响。仅有结构化账内誊录时据实说明证据边界。

## 每个模块的审查判据

1. **物理可行性 `physical_feasibility`。** 从工艺目的和物料去向重建连接、进出组成及基准，核对总量、组分与反应源项，复算决定性指标。沿上下游核温度、绝压、相态、热负荷与压力功，检查必要的换热、调压、分相及辅助节点，核实公用工程、温差和供热供冷条件。检验物性方法与实际组分、操作窗口、预期相态、非理想性和参数支持是否相符。查循环来源、回接、开环初值、积累/放空，核实产品和废物流终端及明显操作、安全和环保约束。逐股对照起点、终点与相态，核压力动作里的设备位号和通称（如“油塔”）是否属于该接口。跨设备的压力预算写明路径；气液分口分别取压。标出误引设备的具体流股和原句。
2. **首版精细度 `design_depth`。** 从正文提取每个单元的拟用模型和可复建首轮指定输入，含具体基准/启动值或能唯一计算的关系、单位、基准与有效范围。分清固定输入、可调变量、求解值和验收指标，核自由度及控制配对。逐项从正文提取数值设计目标、单位和分母、比较方向、允许偏差与依据，独立算出可接受边界。绝对偏差与相对于目标的偏差分别核算；硬限保留零越界。目标缺少验收口径、单位或来源，须记录为规划问题并回查。对 SEP 核整段净边界、各组分到所有出口的定量分配、闭合和去向。对固定转化率 RStoic 核反应式、转化率、基准组分与分母、单程/全流程边界、选择性/产率、温压和热模式。证据充分的 SEP/RStoic 可用于首版。
3. **动力学 `reaction_kinetics`，逐反应模块。** 审查已查到的原始研究及所选反应建模方法。对动力学逐条对照反应式、速率方程与参数来源，核数值与单位、速率定义、浓度/分压/活度等基准、相态、催化剂与质量/体积基准，以及温度、压力、组成和适用范围。核单位换算、量纲、模型能否表达及所选严化反应器所需输入，指出外推或不可转换的部分。对平衡、集总、多工况关系或有据衡算等替代，核对物理依据、能回答的设计问题、有效范围和受限结论。首版固定转化率与后续研究依据应各自明确。
4. **分离严化准备 `separation_readiness`，逐分离模块。** 核候选、选型依据和决定。审查可实际实施的分离机理及操作窗口，以相平衡、物性、传递、容量或其他决定性证据核对目标，关注共沸、两相区、选择性、热压条件以及溶剂和再生边界等适用约束。追溯数据、关键组分、目标与必要的后续模型输入或求取关系。检查后续单元组合能解释首版 SEP 对各股的净分配义务及产品纯度、回收率和切点的确切基准，指出任何物理不相容或仍需验证的范围。严化求解及设备细化留给后续阶段。
5. **证据适用性 `evidence_applicability`。** 核到原论文、已有流程模拟、补充材料、项目数据或可复算推导的具体页、式、表、图、字段。比较物料/催化剂、规模、工况、相态和数据定义，说明来源可用于哪些输入、选型、范围或验证。区分项目事实、外部数据、推导、限定使用的类比和无法取得的证据。遇到缺口，优先进行可执行的针对性查证、换词、沿引文找原文、查技术包或核对同类数据与适用性，检查能否用换算、衡算或有据替代解决。按来源、搜索或推导结果指出最小缺项及影响。
6. **切岛与回装基准 `handoff`。** 说明原接口、各股进出基准、需继承的目标及其容差、热压服务、可调范围与适用专业方法。核对后续应从骨架实际运行提取的入口/循环值和严化时应验证并返回的结果，追踪对上下游与循环的影响。区分已冻结的规划依据和后续实跑才能获得的值。

## 返回记录

整份答卷只有一个 `process_chain`。下面展示一个模块在答卷中的位置。提交时按模块重复该对象，补齐身份、摘要、各项实读值和证据。空对象只用于展示层级。

```json
{
  "process_chain": [],
  "module_reviews": [
    {
      "module_id": "<当前模块>",
      "verification_checks": {},
      "planning_assessments": {},
      "quantitative_extractions": [],
      "issues": []
    }
  ]
}
```

每条定量摘录和问题都放进所属 `module_reviews[i]`，主节点和辅助节点按设计基准归属。跨模块问题注明另一端和复审范围。保存整份 JSON 后可用运行库 `tools.fullflow_gate.planning_review_layout(答卷对象)` 自查层级，返回空列表表示格式检查通过，证据和工程判断仍由完整审核检查。

- 返回完整审查记录，设 `schema=fullflow-independent-review-v1`，保留 `case_id`、`task_revision`、`design_basis_sha256` 和 `planning_article_sha256`。记录由主代理绑定实际调用身份 `call_id`。在 `process_chain` 中依交接账中流股顺序逐条声明 `stream_id`、`from`、`to`。在 `module_reviews` 中每模块给出 `module_id`、`role_summary`、`boundary_summary`、`thermodynamics_summary`、`reaction_or_separation_summary` 和下列证据与问题。
- 每个模块填写 `verification_checks` 的 `module_purpose`、`inlet_outlet_composition`、`reaction_or_separation_basis`、`thermodynamic_basis`、`heat_pressure_auxiliaries`、`connections_terminals`。每项包含 `observation` 数组（元素为 `{evidence_ref,value_path,value}`）和 `evidence_refs` 数组（元素为原始 `{path,sha256}`）。依上述顺序，精确读回设计基准当前模块的 `role` 和 `purpose`、`inlets` 和 `outlets`、`reaction` 或 `separation`（其他模块用 `targets`）、`thermodynamics`、`auxiliary_requirements` 和 `auxiliaries`，以及交接账的相邻节点、物流单行记录。对最后一项，先取本模块的 `node_ids` 与各 `auxiliaries[].node_id`，再取交接账中任一端接此前述节点的每个 `streams.<i>`，以及上述所有节点和各所取物流另一端的 `nodes.<i>`。每条只读回一次，完整拓扑已在整份答卷的 `process_chain` 中给出。用零起始的点路径，如 `modules.0.inlets`，并保留原字段类型。
- 按 `review_specifications` 列出的节点与规格标识，从冻结正文为每项填一条 `quantitative_extractions`。保留 `node_id`、`spec_id`、`value`、`unit_or_basis`、`basis`、适用的 `design_context`、`article_locator`（如 `L31`）、对应的连续原文 `article_excerpt` 和 `comparison`（`match`、`difference` 或 `ambiguous`）。若列有 `acceptance_field`，自行从当版正文和依据读出该项。不向审核人提供标准数值。按指定字段名回填 `acceptance_tolerance` 的 `kind`、`value`、`unit` 和相对量的 `reference`，或原定的 `acceptance_decimals`。在 `design_depth` 说明取值依据及可接受边界；查不到时用 `ambiguous` 并给出问题编号。按相应 `design_context_keys` 填实际判出的上下文字段，空列表可省略 `design_context`。定位使用正文文本行，从 1 开始。对 DOCX 按 `word/document.xml` 顺序取每个 `w:p` 内的 `w:t` 文本并连成一行，保留空段和表格单元格内的段落。只在确有歧义时用空值并解释。差异、歧义均绑定 `issue_id`。
- 在 `planning_assessments` 内为本模块填写适用的上述判据。每项给出 `node_ids`、`evidence`、`observed_result`、`action` 和 `status`（`adequate`、`provisional` 或 `issue`）。`node_ids` 覆盖该模块主节点及相关辅助节点。证据用 `{evidence_ref,value_path,value}` 精确定位现有 JSON，或用 `{evidence_ref,article_locator,article_excerpt}` 定位冻结正文。观察和动作说明具体结论与复算、补证或修改对象。仅有受限而已查证的依据时说清有效范围、待判定的最小变量和细化触发条件。状态为 `issue` 时绑定 `issue_id`。使用以下证据锚点，按记录中该模块和所选候选的实际索引填写路径。

  | 判据 | 当前记录中的证据 |
  | --- | --- |
  | `physical_feasibility` | 设计基准的模块 `inlets`、`outlets`，以及规划检查中的相关 `pressure_budget`、`heat_strategy`、`compression_decisions` 行。 |
  | `design_depth` | 模块的 `physical_service`、`first_model`，适用时包括 `planning_research.selected_candidate_id`，并引用冻结正文中包含设计基准 `article_excerpt` 的本模块原文。 |
  | `reaction_kinetics` / `separation_readiness` | 对应角色下 `planning_research.selected_candidate_id`、所选 `candidates.<i>` 的 `basis` 和 `evidence`（或所选候选完整行），以及 `planning_research.target_mappings`。适用时补核 `kinetics_exclusion` 和 `provisional`。 |
  | `evidence_applicability` | 模块 `thermodynamics`，适用时包括所选候选的 `evidence`。 |
  | `handoff` | 交接账中该模块涉及的各个 `streams.<i>`，以及匹配模块或主、辅节点 ID 的 `handoffs.<i>` 专业交接行（若有）。 |
- `issues` 逐项写 `id`、`node_id`、`finding`、`recommended_change` 和 `rereview_scope`，给出对应原文定位、计算或物理理由。指出受影响的正文、交接、单位、规格、连接、上下游、循环与验收结论。说明如何重新取证与检查。同一模块的每个独立发现使用不同 `id`，便于主审逐条处置。无发现时返回 `issues: []`，没有所列规格时返回 `quantitative_extractions: []`。输出实际读回的数值、关系、差异与依据，避免通用的通过标签。规划审查结论限定于本冻结版本及已有证据。

可直接返回完整 JSON。答卷较大且宿主允许写临时文件时，在审查者自行新建的唯一目录中分别保留带 `process_chain` 的答卷头和每个模块独立的 UTF-8 JSON，在最终返回中列出全部绝对路径。主代理按上述格式将这些原始模块对象装入 `module_reviews`，保留独立答卷头和模块原文件。每位审查者仍独立完成全流程。
