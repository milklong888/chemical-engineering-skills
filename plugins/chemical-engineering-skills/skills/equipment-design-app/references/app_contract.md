# 设备计算、选型与结果协议

## 权威与包含关系

`本Skill的专业工作流 -> 包内设备规则/数据/计算 -> CLI或MCP -> 同版结果与流程反馈`

本文件中app/、scripts/、knowledge_graph/等路径均相对于本仓库
`backends/equipment/`，安装后位于工作区的
`chemical-engineering-runtime/backends/equipment/`。不需要安装另一个设备产品。
确定性程序执行版本化规则、参数推导和选择，大模型不替代主匹配计算。

## Agent 原生控制

- 主入口：`app/equipment_design_agent.py`。
- 请求/响应：`equipment-design-agent-request-v1` / `equipment-design-agent-response-v1`。
- 支持JSON文件、单请求stdin/stdout和驻留`--session-jsonl`。统一入口为运行根目录的`tools/expert_cli.py`及`tools/expert_mcp.py`。连续设备请求复用一个驻留进程：运行资产验签、设备目录和同一API实例每进程只加载一次；每行有独立响应和退出状态，单行失败不得终止后续设备。
- GUI 只是服务层客户端；Agent 的数据输入输出不得依赖鼠标、坐标、OCR 或窗口可见性。
- 每次响应必须给出请求哈希、操作名、明确状态、引擎版本、结果、工件路径、错误码和进程退出码。
- 本仓库的设备后台在调用前校验自身源与运行资产清单：精确路径集合、大小、SHA-256和标准SQLite完整性/表计数。缺失、篡改或额外必需资产必须失败；不能以旧源码树的非适用标签跳过本包验证。
- Agent/CLI 的 LLM Key 只从固定 `EQUIPMENT_DESIGN_LLM_API_KEY` 读取；远程兼容端点只从固定 `EQUIPMENT_DESIGN_LLM_BASE_URL` 读取。每个启用的调用配置还必须含有用户可编辑、非空并实际传入请求的 `model_id`（受控远程调用从固定 `EQUIPMENT_DESIGN_LLM_MODEL_ID` 读取）；不得以代码中的隐藏默认模型代替配置。请求不能选择其他环境变量或携带远程 `base_url`，Key 不得进入请求/响应工件。
- `render_report` 只接收可重放的 `input.operation + input.payload`，先由当前确定性引擎复算，再由展示层输出 `equipment-design-presentation-v1` 和可选 HTML；裸结果/响应被拒绝，展示层自身不得计算或改状态。
- `customer_export` 使用相同重放契约，输出权威总表、族级数据表和证据索引；缺字段必须显式保留，标准参考路线不得写成已采用标准，候选标记不得写成厂家最终型号。
- `pfd_build` / `aspen.pfd.build` 从只读 `aspen-equipment-export-v1` 文件构建确定性 PFD；`pfd_override` / `aspen.pfd.override` 只接受目录内 selection ID，`AUTO` 清空该模块的类型改写并恢复自动识别。`pfd_recalculate` / `aspen.pfd.recalculate` 至少接收 `bundle_path + block_id`，调用方必须传回上次响应的完整 `parameter_overrides` 状态，本次非空补录放入 `values`；`clear=true` 清空该设备的参数补录。三者不得覆盖 bundle/BKP，也不得把改型或补录当机械设计、厂家证据或型号证据。

### PFD 映射与显示契约

真实和模拟 Aspen worker 都必须生成 `aspen_pfd_mapping.json`，返回文件 SHA、
`mapping_sha256`、节点/边计数与拓扑门。映射首先读取 `HAP_RECORDTYPE` 对应
的 `block_type`；读不到或目录未知时，才按 equipment_map、字段、相态、压力
方向、端口及连接特征生成候选。不能唯一闭合时只保留共同上位族和候选集，
不得生成专用 selection ID。

精确 `FSPLIT`、`MIXER`、`HIERARCHY` 是默认模拟拓扑节点，必须标为
`NOT_APPLICABLE_SIMULATION_LOGIC_NODE`并保留PFD、连接、参数及独立override
数据；不得推断独立物理设备或型号。仅这类精确且未被用户改型的记录可从
设备闭合聚合门排除，其他未匹配模块仍阻断正式流程基础。

参数补录层按 `block_id` 独立保存，留空字段不写入 `values`，继续沿用 Aspen/
已有值。确定性重放只把当前设备标为已重算；关联流股和直接上下游继续标为
`stale`，等各自重放后才恢复。参数字段应携带已有值、空值语义、单位、公式
消费者和证据边界；说明随结构化数据传递，不依赖弹窗。

PFD机器协议保留`compact`、`standard`、`detailed`三级信息密度。
节点包含设备ID、源模块、映射类型和选择状态；边保留流股ID、方向与连接。
完整参数始终在JSON中，不能靠界面读取补齐。修改型式只能使用当前catalog
中的selection ID；旧选择结果失效后，明确标记当前设备及相关流股和上下游
待复算，无关节点保持稳定。override独立存储，不得回写BKP。

### 协议 1.9 的受控 AI 辅助计算与编排链

```text
hybrid_prepare(input.operation + input.payload)
-> 当前引擎复算并冻结 deterministic result + replay contract + KG context
   + candidate/condition registry + calculation recipe catalog + hashes
-> 外部 Agent 严格 JSON：优先选择补算配方，可组织中间操作块
-> hybrid_continue 重放输入、重建 prepared、逐条校验严格 JSON
-> 程序初算锚点 -> AI 操作块 -> 可选程序复算锚点
-> 描述性修改/候选引用仍由 llm_apply 在人工批准后复算
```

`hybrid_prepare`、`hybrid_run`、`llm_review` 禁止调用方提交裸 `deterministic_result/path`。内置 provider 使用 `hybrid_run`，但必须复用同一个 `hybrid_continue` 校验器，并统一返回 `equipment-design-hybrid-result-v2`；模型关闭或失败时确定性结果仍完整保留。prepared/orchestration 必须绑定 `authority_revision`：协议/匹配器版本、核心规则与型号/模板/数据/图谱 SHA、全部协议 Schema SHA，以及打包 manifest SHA 和 bundle revision；任一项变化都使旧 continue/apply 失效。`injection_point` 只允许 `semantic_extraction`、`textual_condition_judgment`、`ambiguity_resolution`、`kg_retrieval_planning`、`audit`；`context_scope` 只允许 `minimum`、`routed`、`full_family`、`full_bundle`。上下文包必须返回 `coverage_status`、已包含/截断资产、字符数和哈希；`PARTIAL` 不得声称完整知识覆盖。

每个嵌套模型判断至少引用一个冻结 `context_id`。文本条件只能引用 condition registry；候选只能引用既有 `candidate_id + designation + selection_feature_vector_sha256 + selection_context_sha256`。模型先选择已登记的简单推导配方，数值由程序计算；仅当全部输入已冻结、目标字段为空且程序校验通过时，`manual_match/auto_match` 才自动补入并返回独立复算结果。配方依赖图穷尽后，模型可对 `missing_input_registry` 中仍缺失的预选字段返回 `model_inference`，但必须逐项提供同工况/工程要求/登记范围/保守初筛依据、非空假设、数值上下界或登记枚举、置信度、敏感性和预选自动带入请求。程序通过宽范围物理门、字段与交叉校核后才 missing-only 带入和重算；该值始终为 `J/provisional`、封顶 `TYPE_SCREENING`，不得覆盖已有值、正式证据或厂家最终型号，脚本冲突时程序值优先。模型也可把 `DEFAULTED_TERMINAL_TYPE_SELECTED` 升级成同设备族登记过且当前条件判断为 supported 的终点型式，但必须回传准确 `terminal_rule_id + condition_id + selection_context_sha256`，由程序重放；自由型式文本、虚构规则、条件不支持、上下文哈希不符或修改已指定/已条件选定型式均逐条拒绝。未知配方、越界估算、缺依据和冲突只降级该条，不得阻断整批。AI 可决定其中间块的标题和顺序，但不得改写程序初算/复算锚点。自由生成 `candidate_model`、覆盖已有数值/单位/压力基准/证据状态/型号状态均禁止。

## 先计算后选型协议

固定顺序：

```text
归一化 -> 设备族 -> 可闭合计算 -> equipment-design-parameter-package-v1
-> constraint_checks -> selection_feature_vector -> 候选匹配 -> 证据升级
```

- 17 族参数布局：`knowledge_graph/equipment_parameter_chain_templates.json`。
- 型号规则：`knowledge_graph/equipment_model_recommendation_rules.json`。
- 每个派生目标量必须同时出现在 `calculations[].target_field`、`derived_parameters` 和参数包对应行。
- 选型只能读取参数包 `selection_context.values`，并记录上下文 SHA-256；不得从原始请求旁路取值。
- 参数不全时保留上位类型、补齐路径和最泛用型号/工程规格候选；`WAITING_CALCULATED_PARAMETERS` 只限制正式升级，不得清空物理设备候选或伪造厂家型号。
- 机器 JSON 保存全精度；参数卡与公式展示使用紧凑工程精度。

## 三种导入方式

1. Aspen `.bkp/.apw/.inp`：可选 COM；独立子进程、外层超时、源文件只读复制、逐模块遍历、全过程留痕。
2. 手动输入：先选模块/设备族，再按JSON字段逐项给值，数量与单位/基准明确对应。
3. LLM 辅助：用户自行提供进程外 API 配置；端点、密钥和 `model_id` 三者缺一时不得发起远程调用，必须显式提供模型ID，不能隐式使用代码默认值。通过协议 1.9 的确定性重放、冻结上下文和严格 JSON，先补齐可由登记配方闭合的数据；仍缺失时，只对登记的预选字段给出带依据、假设、上下界/登记枚举、置信度和敏感性的最后一级工程估算，由程序校核、带入并重算，同时在终表注明。模型还可把无条件默认型式升级为当前上下文明确支持的登记条件型式，再完成语义抽取、文字条件判断、歧义处理、图谱检索规划、输出编排或审核。程序保留初算和复算结果；API 配置不完整时前两种方式完整可用。

Aspen 未运行或 `compstatus` 含 `NOT_RUN/NORESULTS` 时，Output 节点的零值/空单位是占位而不是工程数据，必须略过；连接和模块语义仍可用于 PFD。请求运行时只运行哈希一致的隔离副本，COM 树读取后用隔离 `SaveAs` 捕获 `.his`，并保留 REP/SUM/MSG 诊断。无带哈希原始历史或历史门不全零时，推导最多 provisional。

有限数也不自动等于可用工程数据。流程流量、质量流量、热负荷、功率、面积和几何值必须先过宽松的非设计哨兵量级门；质量流量、体积流量与密度还要做数量级一致性诊断。异常字段进入 `ignored_input_diagnostics`，不得进入有效参数包、公式或 designation；对应设备身份和最泛用候选继续输出。

## 硬门

- `HAP_RECORDTYPE` 是 Aspen 模块/流股语义类型；节点 `Value` 可能只是图标令牌，不能代替类型。
- 压力必须声明绝压或表压；表压需当地大气压。压缩/膨胀方向不可反用。
- Aspen 运行证据、源文件和导出文件必须带实际文件哈希；COM 提取身份或连接冲突进入正式使用阻断项。
- PFD override 必须复核输入 bundle 文件哈希并写入独立 JSON；禁止回写 Aspen 源文件或把 `USER_TYPE_OVERRIDE` 升为 `final_model`。
- 每台物理设备必须唯一落到已指定、条件选定或明确标注默认的终点设备型式；设备族名不是终点型式。可保留候选集供比较，但不得让候选集替代唯一终选。终点型式不等于厂家最终型号，正式厂家/同设备证据门继续独立保留。
- 远程模型配置和状态报告必须包含非敏感的 `provider`、`endpoint_profile` 与实际 `model_id`；测试至少切换两个不同模型 ID，并验证线上的请求载荷确实改变。缺失或空白 `model_id` 是局部配置错误，只禁用 AI 分支，不得影响确定性计算、选型和无 LLM 输出。
- 公式显示采用 `目标量 = 公式 = 代入式 = 答案`，不为每个中间数重复目标量。
- 所有内置公式和保底值必须在机器 JSON、参数卡、公式页和报告中显示结构化告警，说明其不是 Aspen/用户直接值。固定按 `同工况/Aspen/用户值 -> 精确推导 -> 图谱/标准条件推荐 -> 登记内置推荐公式 -> 显式最终保底值` 执行；后三级按 `J/provisional` 处理，逐项记录条件、假设和敏感性，禁止覆盖同工况提供值，最高只到 `TYPE_SCREENING`。登记默认可覆盖预设计所需的密度、效率、流速、停留时间、装填系数、材料路线和 LMTD 修正系数等，但不得生成厂家最终值，也不得污染已批准的同设备证据包。
- 换热负荷 `Q=0` 不得闭合为零面积换热器；面积链保持待核实，最泛用换热器工程规格候选继续输出但不得正式升级。`design_pressure_mpa` 显示中性 `MPa`，直接值必须带 `design_pressure_basis`；绝压用显式或已登记并告警的当地/标准大气压规范化为表压，规范化表压小于或等于零时进入外压设计分支，不执行内压厚度式。
- 已选 `volume_m3` 必须带 `volume_basis`。最低总容积与直筒段几何容积分开；`nominal_total`、`geometric_total` 直接和最低总容积比较，`effective_working` 与 `required_volume_m3 * fill_fraction` 比较。
- 液透平 `ΔP/(ρg)`、`ΔP·Q` 和乘效率结果分别只代表压差水头分量、压差功率分量和轴功初筛，不得写成全机总轴功或最终机组选型。塔 `πDi²/4` 只代表全筒截面积，不代表扣除降液管、受液板和无效区后的有效面积。
- 膜面积内置几何式只适用于 `cylindrical_channels`；其他几何必须提供同工况外部 `membrane_area_m2`。材料默认可见但属于可选偏好，不填时保留泛用候选和证据缺口。

## 本仓库的后台文件

- 总包：`README.md`
- 内部API适配器：`app/equipment_design_app.py`（不是GUI启动器）
- 图谱：`knowledge_graph/README.md`
- Aspen 推导链：`knowledge_graph/aspen_equipment_derivation_chain.md`
- 匹配器：`scripts/equipment_design_match.py`
- Aspen 适配器：`scripts/aspen_equipment_derivation.py`
- Agent CLI：`app/equipment_design_agent.py`
- 参数模板：`knowledge_graph/equipment_parameter_chain_templates.json`
- 展示适配器：`app/result_presentation.py`
- 客户输出剖面：`knowledge_graph/equipment_customer_output_profiles.json`
- 客户交付适配器：`app/customer_delivery.py`
- Agent Schema：`app/schemas/`
- PFD 映射核心：`app/aspen_pfd.py`
- PFD Schema：`app/schemas/equipment_design_pfd_mapping.schema.json`
