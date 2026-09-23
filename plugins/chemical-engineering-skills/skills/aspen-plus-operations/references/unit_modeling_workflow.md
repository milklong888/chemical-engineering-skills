# 单模块建模入口与必要条件

用于把已冻结的模块设计交给 Aspen 操作层；不接管工艺路线，不启动无授权的软件。
第一次建某类模块、由骨架替换严格单元、或检查模块遗漏时读本文件，再进入所列原 owner。
这是按现有资产整理的操作提纲，不是新建一套单元计算程序。

## 文字规划也要过的交接检查

只说“交给某 Skill”“使用 Design Spec/Calculator”不构成操作规划。
交回前逐个实际模块对照下文必要条件；只读其入口段落不能代替已触发的方法文件。
当前任务只禁止启动软件时，仍执行已有本地只读查询和 solve_route 分类；
缺MCP不是跳过CLI的理由。资料未齐只限制相应计算，不把所有检查推给后续人员。
本机原路由器位于工作区链接表登记的离线 runtime
`workspace/chemical-engineering-runtime/tools/expert_cli.py`；在仓库工作时位于
`repository/tools/expert_cli.py`。先沿链接表/安装回执定位根，再用
`--schema solve-route` 核签名后提交只读分类；不要只查当前工具列表或
`.codex/skills` 中有无 MCP 名称便判定路由不可用。
Windows 中文路径/编码使首次命令失败时，按
[原生工具方法的相对工作目录后路](../../aspen-document-driven-flowsheet/references/aspen_builtin_solve_fit_tools.md)
核真实文件、改用 `workdir` 与 UTF-8/ASCII 请求重试；只有成功回执才算已调用。
只读任务不得因路径失败重建索引、修改配置或假报工具不存在。

需要目标求解或运行时公式时，必须填写当前任务自己的控制安排表，不交空模板：

| 对象/用途 | 目标或显式公式及单位/基准 | 具体可调/写入变量（唯一主写入者） | 范围/容差/初值的来源或最小缺口 | 建模时何时加入；每轮生产者→本对象→消费者 | 外层变化时重解什么；要核对的卡片/结果 |
| --- | --- | --- | --- | --- | --- |

允许候选变量未验证，但应给当前最合理的具体配对及理由，或指出为何没有可用
自由度；不能只列“回流/采出/溶剂等”让下游猜。每座正式塔都要占行，
包括吸收和再生，不能只在全文别处提一次设计规定。保持不等式的原意。
Calculator 显式关系不写成“Calculator 或 Design Spec 都行”；说出哪股当前
流量先就绪、写哪项输入、哪个设备随后消费，以及是否进入回流迭代。
特别分清两件事：建卡前只需确认变量身份、来源公式/系数与单位，不必等
生产者实际算出 C 等本轮数值；建好后每轮才按“生产者算 C→Calculator
写 M→消费者读 M”执行。系数尚缺时保留未建卡状态，不拿旧 C 代替。
只做一次单位换算则明确不插控制器，不为了填表增加工具。

反应器另逐项勾核反应集实际挂接、出口相态、热压和几何/时间基准；
RBatch 的停止准则、最大计算时间、操作时间表和输出间隔不得相互代替。
已给数据能唯一闭合的产品流量/回收率等，先做衡算或符号推导，
不要把可推导量再列为用户必须补充的输入。
例如二元、仅顶底两产品、无损失时，对同一组分
`D=F(z_F-x_B)/(x_D-x_B)`、`B=F-D`；两项产品组成给齐即可求产品流量
及关键组分回收率。该推导不自动消去一项塔控制规格：若只用一项纯度 DS，
还要合法固定推导出的产品分割量，才能从守恒同轮推出另一项纯度；
否则为两项独立目标安排两组有效自由度。

每个将要使用的资料/脚本先核真实路径或注册ID。记录实际读取的必要条件，
不要把“准备查”写成“已查”。19个正式职责以本文件清单或 workflow=list 为准。
列正式清单时逐项对齐这19个注册ID并复核总数，不从“本机已安装”推断发行身份：
`aspen-project-equipment-cost-batch` 是另一个项目的专用费用Skill，虽可能
出现在本机活动资产登记中，也不属于本包19项，不能补入正式职责表。
原有 `aspen-non-reactor-equipment-cost` 与
`aspen-flowsheet-cost-skill-builder` 仍是正式入口，仅在费用任务触发。
最后将当前文字计划与必要条件逐项对照，
分别列已覆盖项和仍影响实施的缺项，不以模型未运行作为省略规划细节的理由。

## 建模时找谁

| 当前任务 | 主 Skill（相对本目录上两级） | 先查的方法/资产 | 返回给谁 |
| --- | --- | --- | --- |
| 从文字生成完整流程、切出与接回单模块 | aspen-document-driven-flowsheet | references/fullflow_generation_workflow.md；source_scaffold_handoff.md | 上游任务合同/全流程 |
| 物性、组分、块卡、物流、原生工具、运行/导出 | aspen-plus-operations | operation_graph.md；scripts/query_manual_knowledge.py；scripts/aspen_runtime.py | 当前主专业 Skill |
| 只建组分模板 | aspen-plus-template | scripts/create_aspen_template.py（先看参数和源清单） | 后续模型构建 |
| 精馏、吸收、汽提、溶剂回收塔 | aspen-tower-optimization-workflow | references/tower_optimization_workflow.md | 塔岛/母流程 |
| 常规塔改蒸汽再压缩/热泵 | aspen-heat-pump-distillation-replacement | SKILL.md 的空塔—压缩—外部换热工作流 | 塔优化/全流程 |
| 已有模型报错、循环/控制失效 | aspen-flowsheet-error-repair | references/ERROR_MEMORY.md 与主工作流 | 原候选及精确复跑 |
| 压力网络、泵/压缩机/阀、压降与PFD | aspen-pressure-pfd-delivery | SKILL.md 压力预算；expert CLI pressure 方法 | 受影响上下游 |
| 换热器真正 EDR rating | aspen-edr-rating-delivery | SKILL.md 与其 EDR 方法参考 | 同点换热/流程验收 |
| 动力学来源、换算、卡片说明 | aspen-kinetics-documentation | 来源→单位→输入→导出链；动力学图谱 | 反应器建模/文档 |
| 两段/多段边界拆分 | aspen-two-section-flowsheet | 现有边界合同和拆分流程 | docflow；不是“每类反应都另分段” |
| 多进料模板与实时调节 | aspen-adaptive-generalization-loop | Rule Types、Physical-Law-First；query_error_memory.py | 代表工况模板及验证 |
| 塔径/内件/水力设计 | chemical-tower-design | references/evidence_routing.md；query_tower_sources.py | 塔同点设备校核 |
| 设备报告公式/来源审计 | chemical-equipment-selection-audit | 原报告与设备图谱、计算账本 | 报告/工艺修改 |
| 确定性设备计算、筛型及反馈 | equipment-design-app | 现有 expert equipment/feedback；不用 GUI | 全流程设计者 |
| SW6 受控字段传递/回读 | sw6-scripted-equipment-design | 已验证同版本字段映射与软件证据门 | 机械设计审计 |
| 单案非反应器设备费用 | aspen-non-reactor-equipment-cost | 原有经济评价/费用提取脚本 | 同基准经济比较 |
| 新流程需要可复用费用方法 | aspen-flowsheet-cost-skill-builder | 映射/尺寸/价格来源与批量脚本生成流程 | 项目费用 Skill |
| 化工宏观判断、来源/设备反馈/学习治理 | chemical-engineering-expert | HIGHEST_LEVEL_GUARDS；REASONING_PROTOCOL | 各专业 owner |
| 并行事实工作与独立复核 | subagent-dispatch | SKILL.md 范围、模型身份、并发和回收 | 主代理判断，不另做技术标准 |

19 个 Skill 是职责分工，不是 19 种单元。反应器、混合/闪蒸、压力设备和普通
热交换的建模由操作层结合原讲义节点执行；塔、热泵、EDR、修复等有独立专业流程。
不要为了凑数再建重复 Skill。

## 每类模块共同的交接

实施前必须已有：当前来源/允许修改、进出口角色和组分基准、物性及相态依据、
真实温压范围与压降/供热方式、待求量与已规定量、依赖的回流/控制关系、验收项。
读本机图谱 README/unknowns_router，再取对应章节；方法不确定时按专家层优先
查登记的外置专著。教材例题数值不填进项目卡片。

每个必要条件记录四种状态之一：已知并引用、可推导并给式、需试算/待验证、
不可替代输入缺失。提纲完整不等于模型已经运行。

## 单元族必要条件与工具触发

### 1. 混合、分流、闪蒸和简化分离

- Mixer：连接真实入口/出口；明确压力和有效相态，检查混合后闪蒸与焓/组分衡算。
  FSplit 是同组成分流，不能代替气液分相；N 个出口只给 N−1 个独立分配。
- Flash2/Flash3/Decanter：按实际气液/液液情况选模型，给独立闭合的状态规定；
  读物性适用性和版本规定，不把不独立的温度/汽化率/热负荷组合硬凑。分相组成、
  流量与能量均核对。SEP 在骨架中按组分分配；正式分离须转实际机理模块。
- 已知显式补料/分流规律才用 Calculator；仅复制信息考虑 Transfer；
  能由明确边界物料/能量衡算直接闭合先评估 Balance。
  要反求闪蒸操作量命中项目目标时才配 Design Spec，不给简单固定条件多套控制器。
- 来源节点：孙兰义 ch04（PDF p.130–145），ch09（p.282–300）。
  操作入口：operation_graph 的 component-property、block-stream；
  查本机帮助后记录实际对象/单位，不编字段。

### 2. RStoic / RYield / REquil / RGibbs

- RStoic：配平反应式、基准组分、转化率/反应程度定义和限量关系，温度或热负荷、
  压力与有效相态。不能只写“选化学计量反应器”而漏反应集/反应程度。
- RYield：当前来源的质量/摩尔产率基准与分布闭合；有 lump/de-lump 才作组分映射，
  非常规固体属性/粒径按任务补齐；产率不是动力学常数。
- REquil：反应平衡式、允许相态、温压、必要的平衡接近规定；RGibbs：
  合法产品组分集合、相态/出口分配、温压与允许约束。热力学极限不冒充实际产率。
- 显式进料比例在入口就绪后、反应器之前计算；固定给定转化不另“拟合”动力学。
  要反求真实操作量达到目标则进入内置求解方法，先判断自由度与可实现性。
- 来源：ch08a（p.252–263）；操作节点 reaction.rstoic.overview；
  其他未注册细卡用原帮助查询，不假装节点都存在。

### 3. 动力学 RCSTR / RPlug

- 先过反应来源冻结：原方程与数值、原单位、换算、Aspen 卡片单位、相态/浓度/
  催化剂基准、精确输入和导出复核。动力学不足只限制严格动力学结果，可保留有标注骨架。
- RCSTR：压力、温度或热负荷、有效相态、体积或停留时间；建立全局 reaction set
  后在块中选中，逐个出口设置相态，不能用 valid phases 代替出口规定。
- RPlug：选择符合来源的热边界（指定温度/绝热/热流体等），长度、直径/管数、
  压降及相应传热参数；动力学写在 Reactions 并真正挂接。不能把管数当无解释连续量。
- 定尺寸且有明确关系：入口就绪 → Calculator 求体积/催化剂量 → 反应器；
  固定设备能力分析不得改几何。要按转化/选择性反求尺寸或操作量，核实
  动力学/热边界后用有界 Sensitivity（或有效区间）→ Design Spec/约束优化。
- 来源：ch08c（p.266–269）、ch08d（p.269–273）、动力学图谱。
  操作节点 reaction.powerlaw.overview、reaction.lhhw.*、
  rplug.geometry/temperature/catalyst；先查询实际节点支持，不直接写未知节点。

### 4. RBatch / 半间歇

先冻结单批投料与基准流率/进料时间的换算、温压/热边界、操作时间表、
连续进出料及相态、reaction set 绑定、至少一个有效停止准则。
停止准则、最大计算时间和结果输出间隔分别定义。
只需按指定停止准则运行不另套设计规定；逆求批次时间/其他操作量达到目标时
才评估真实可调输入及其界限。输出检查总投料、最终时刻、转化/热量和时间剖面。
来源：ch08e（p.273–278）；精确卡片转操作层现版本帮助。

### 5. Heater / HeatX / EDR

- 单股调温用 Heater/Cooler；两股换热要交代冷热侧进出口、相变、流向、温差
  与能量关系、两侧压降。骨架亦不得以改流股温压替代真实加热/升压设备。
- HeatX 的 Shortcut、Detailed 和真正 EDR 是不同证据层级；
  U/几何/污垢/允许压降等按选定模式提供来源。不能把 Detailed 名称当 EDR 通过。
- 已知流量—压降/补料关系：生产者 → Calculator → 换热器；仅有目标出口温度
  且块本身支持直接规定时先用块规定，不重复套 DS。跨设备热负荷匹配/
  热泵匹配才按真实自由度考虑 DS；每轮源热量更新后再求匹配。
- 核验两侧能量、最小温差/温度交叉、相态、压降、面积与负荷；设备校核
  返回几何或压降改变后复算原流程，不只更新设备表。
- 来源 ch06（p.180–203）；EDR 交给专用 Skill。

### 6. Pump / Compr / MCompr / Valve / Pipe

- 先有各接口绝压及压降预算、相态/流量/物性和压力变化目的，再选设备。
  泵与压缩机分清相态；常规气体压缩的液滴风险与获准两相模型分别核证。
- Pump：压力/压升/压比/功率或适用曲线规定，区分泵效率与驱动效率。
  Compr：模型、类型、出口规定、效率与出口温度/功率边界。
  MCompr：级数、压力分配、级间冷却/压降及凝液处理。
- Valve：节流目的、出口压力或适用设计/rating 参数；Pipe/Pipeline：
  长径、标高、粗糙度、管件和热边界。无来源不得给全厂统一压降百分比。
- 直接出口压力规定不需要额外 DS；跨单元达到某目标、或同产品下寻最低能耗，
  才进入 DS/Optimization。总压比均分只是初始化，不忽略各级冷却器压降。
- 建模规划时就沿供给端→接收端列压力预算，读取
  `aspen-pressure-pfd-delivery/SKILL.md` 的 Pressure Audit Checklist。
  已有液体管路几何/物性时，经原 pressure CLI 的 `liquid_pipe_loss` 按
  `ΔP=(f_D L/D+ΣK)ρu²/2+ρgΔz` 算同径恒密度牛顿液体段；
  串联已知损失用 `series_pressure`，并联按同边界 Q–ΔP 曲线用
  `parallel_distribution`，压缩分级用 `compressor_train` 初筛。
  各法均须核输入、单位、适用域；换热器两侧和塔内压降分别交 EDR/塔 owner，
  不能把液管公式冒充气/两相或设备额定，也不能无据设零压降。
- 来源 ch05（p.157–170）；压力审计 Skill 与 CLI pressure 方法配合。
  pressure 是声明基准的计算，不是厂商压缩机选型/软件 rating。

### 7. 塔与热泵塔

必须进入
[原塔完整方法](../../aspen-tower-optimization-workflow/references/tower_optimization_workflow.md)。
正式塔强制 Design Spec/Vary；必须体现初估、严格塔配置、可行区间、
产品目标求解、同产品条件的优化（任务需要时）、同点设备/水力学、
原接口回装与精确候选验收。不用这里几句话代替整份方法。
普通精馏按塔 owner 的完整顺序：复制母流程的当前进料边界建立隔离
DSTWU 子模板，只增加简捷塔和必要连接；据当前设计依据取得初始级数，
再用严格塔的塔内 SPEC/VARY 联动 RR、D/F。先在该级数下逐点比较进料板，
随后调整总级数，并在每个新级数重新核进料板、重解产品规格。最终只把
带塔内设计规定的严格塔放回母流程原接口，按真实进料/循环复算。
现有脚本的调用与尚缺原生建卡适配边界见塔 owner 的
`references/tower_script_handoff.md`，不得把文本候选生成等同于已建塔。
吸收/汽提/萃取/共沸塔先核模型适用性，不能都走普通 DSTWU。
吸收/再生的最低拓扑检查是原料气进吸收塔、净化气出塔，
贫吸收剂进塔、富吸收剂去再生、贫液按热压边界返回；
塔级数、接触段数和进料位置为外层离散结构候选，
不能写进塔内 SPEC/VARY 的连续操纵量栏。缺合法连续自由度时，
只阻断对应目标求解，不以结构量假扮控制。
若吸收塔规格用溶剂循环量作 Vary，Calculator 只能一次给初值或写
另一独立输入，不能每轮重写同一循环量；若来源强制每轮比例控制
循环量，则该自由度已占用，须另找合法 Vary 或把净化目标标待解。
来源净化上限仍作不等式验收；等式型塔内 SPEC 需另有据设定点。
热泵由专用 owner 处理空塔、压缩、外部换热和负荷去重。
来源 ch07（p.214–239）、ch10d（p.402–405）。

### 8. 循环、原生工具与结果交接

循环先定义物理回流和 purge/makeup，再定义数值 tear；二者不能互相替代。
最小循环取得可追溯初值，逐段严化，不凭切断回流宣称闭合。
控制对象的“建模时加入/每轮执行/唯一主写入者/返回与验证”
按 [内置工具详细规则](../../aspen-document-driven-flowsheet/references/aspen_builtin_solve_fit_tools.md)
逐条落实。默认收敛顺序失败后才凭证据调整，不把旧案 MAXIT/CHECKSEQ/Broyden
组合当通用模板。来源 ch09、ch11、ch12（顺序方法以原页和现版本支持为准）。

## 现有脚本如何找、怎样算真的调用

1. 在未知实现前查 docflow 的 script_template_catalog 与
   scripts/query_script_template_graph.py；查现有脚本 inventory/OWNER_ROUTES。
2. 查询返回的 base/next 是原模板与依赖，不代表免配置可执行。
   按其参数声明填当前输入/适配器，禁止复制旧案标签、组成、数值或误运行历史构建脚本。
3. 操作层 aspen_runtime 负责受控的打开/写入/运行/导出；模板中的外部逐点扫描不冒充
   Aspen 原生 Sensitivity。没有专用建卡包装时继续查通用 COM/脚本路线，不重写求解器。
4. MCP workflow_lookup 负责发现和读取；aspen_solve_route 分类；
   design_stage_check 作阶段检索/设备编排；equipment_calculate/pressure_calculate
   执行各自已注册计算。它们均不证明原生 Calculator/Design Spec 已运行。
5. 原生工具须留下实际对象/卡片、同次执行结果和残差。没有软件执行时标
   “文字操作计划/待验证”；不能用函数返回成功、hash或PASS字段替代。
