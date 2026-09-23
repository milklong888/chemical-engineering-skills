# 建模从哪里开始

使用者只需说明要建整条流程、单座塔、反应器、换热系统，还是修复已有模型。
助手先确定主工作流，再按当前阶段读取方法、调用程序；不需要使用者记住19个模块名。

## 从文字到完整流程

先安排功能模块，再决定 Aspen 块。助手从原料和反应网络出发，沿每种组分追踪
它经过哪一步反应、从哪里分出、作为产品还是回收料、惰性或废物流去哪里。
这样排出预处理、反应、分离、回收/再生、产品整理的真实连接；具体先后由
当前反应和分离机理决定，不套一条固定的通用工艺路线。提示词没有说明循环、
吹扫或分离方法时，先给有依据的候选，并把来源事实、计算结果、设计提案和
尚缺条件分开，不把空白直接当成“不需要”。

在这条物料链上逐个检查相邻模块的接口：下游需要什么温度、压力和相态，
上游能否提供；需要时才在正确位置补入冷却分相、换热预热、泵、压缩机、
阀及损失预算。换热器的冷热两侧分别走各自物流，循环和补料必须回到明确的
节点；每个产品、放空、废液与固体残余都要有终点。排完后再查是否出现
无用途的混合后重分离、反复冷热或压缩后节流，以及高品位热源本可由过程余热
预热替代的情形。这一步形成可追溯的模块—物流连接账，不是只画几个大方框。

同一版补全要求交给五份独立流程链审查，逐项比对模块遗漏、连接方向、组分去向、
物性依据和热压配套。差异闭合后才用 SEP、RStoic 等简化单元搭完整骨架；
反应和分离可暂时简化，泵、压缩机及加热/换热等真实热压作用不能省略。
骨架实际运行并从导出取得循环初值，再由三份独立复核按实际块和物流机械复述
流程。之后按原接口切出反应、分离等模块，逐个严化。每个模块完成计算后，先将
该模块的全部物理设备及同版工况送入选型器；它会返回参数计算、型式初筛、
真实能力限制与证据缺口。发现适用的单机限制，就在岛内比较分段、串并联或改型，
实施后重跑该岛和选型；没有未处理的限制，才将该模块换回母流程。换热器单台
负荷或面积确实过大时先评串联分段，小负荷或目录无匹配不因此增加设备；泵和压缩机
依扬程/压比还是流量受限决定串并联，塔依水力容量还是分离分段任务判断。
每次回装都用母流程真实入口重算受影响的循环、产品、热量和压力。完整接回后
还要按整厂最新导出逐台复核全部适用设备，因为岛内工况可能已变化。费用分析是
后续独立分支，不替代上述流程判断。
详细的来源审查、结构交接、导出复核与交付门沿用
[全流程生成方法](../plugins/chemical-engineering-skills/skills/aspen-document-driven-flowsheet/references/fullflow_generation_workflow.md)。

## 塔怎么建、什么时候优化

先定母流程当前进料、物性和产品目标。普通精馏从这股进料复制边界，建立
只加 DSTWU 及必要连接的隔离子模板，按有据的回流或级数规定取得初始板数；
特殊塔若不适用 DSTWU，则记录原因并直接进入获准严格模型。随后在塔岛里
以初始板数建 RadFrac，把两项产品纯度/回收目标分别接入**塔内**
Design Spec/Vary，由它们求回流比和 D/F。先保持初始板数逐个比较进料板，
在同产品条件下找较低再沸负荷的位置；之后调整总板数，每次都重新核进料板、
重解两项规格并比较热负荷与设备负担。不能固定旧回流比继续扫，也不能仅因
最大板数热耗最低便称它为最优。
二元、只有顶底两股产品时，先用总量和组分衡算求能确定的采出量与回收率；
算出采出量不等于已经把它设为塔的操作规定，两个纯度目标的控制自由度仍须核对。

正式塔建模和优化必须保留有效设计规定。没有目标、自由度或可行边界时，说明
缺少什么，不能把手工试出的数值当成已完成设计规定。只读审核和简捷初估本身
不改造为正式塔模型。最终只把带塔内设计规定的严格塔放回母流程原接口，
不把 DSTWU 或临时进料流股接回；用母流程实际进料、循环和压力重新求规格。
水力、压降或设备选型引起工况改变后，也要回塔重新计算。
完整步骤见[塔建模与优化](../plugins/chemical-engineering-skills/skills/aspen-tower-optimization-workflow/references/tower_optimization_workflow.md)，
可复用脚本及其尚缺的自动建卡能力见[塔脚本交接](../plugins/chemical-engineering-skills/skills/aspen-tower-optimization-workflow/references/tower_script_handoff.md)。

## 计算器何时加入

如果已知补料、配比或定尺寸关系应随进料改变，就在依赖设备首次计算前安排
Calculator。创建关系时要有变量身份、系数和单位，不必先运行出当前 C 的数值；
每轮执行时才先取得当前输入，再计算并写入下游设备；涉及回流的关系要放进
对应收敛顺序，不能读取上一次工况。只统计能耗或收率的计算器放在结果产生后。

若未知操作量需要反求才能达到目标，才进入 Design Spec/Vary。
Calculator 和 Design Spec 不能同时写同一操纵量。
只是读一个焓值或做一次单位换算，不需要新增控制器。
详见[原生工具的选择和双重时机](../plugins/chemical-engineering-skills/skills/aspen-document-driven-flowsheet/references/aspen_builtin_solve_fit_tools.md)。

## 其他模块去哪里找

[单模块建模入口](../plugins/chemical-engineering-skills/skills/aspen-plus-operations/references/unit_modeling_workflow.md)
列出了19个职责入口，以及混合/分相、各种反应器、换热、压力设备、塔和循环的
必要输入、资料节点与工具触发条件。表内给出的是原有 owner，不另造第二套求解器。

- 普通建卡、读取、运行与导出：aspen-plus-operations。
- 原模型报错：aspen-flowsheet-error-repair，先找本次运行的首个有效原因。
- 塔的水力与内件：chemical-tower-design；真正 EDR 校核：aspen-edr-rating-delivery。
- 设备参数计算与选型：equipment-design-app；报告公式审计：chemical-equipment-selection-audit。
- 压力设备与压降：aspen-pressure-pfd-delivery 从接收端回推压力预算；液管、串联、
  并联与压缩初筛走现有 pressure 方法，换热器两侧和塔内压降各回本专业方法，
  不用一个管路公式包办。
- 动力学来源说明、费用、SW6字段回读和多进料模板，分别进入表中专用模块。

## 现有脚本和经验怎样复用

脚本先按任务查
[原脚本目录](../plugins/chemical-engineering-skills/skills/aspen-document-driven-flowsheet/references/script_template_catalog.md)
和同目录 script_template_knowledge_graph.json。
查询会返回原模板、后续节点和实际文件是否存在。模板中的项目适配器、旧案数值
和外部扫描不是已经验证的原生建卡接口；使用前按当前来源配置。

| 做到这里 | 优先复用 | 输入与返回 |
| --- | --- | --- |
| 寻找既有脚本/依赖 | tools/skill_organization.py；query_script_template_graph.py | 当前库/任务词 → 文件、引用或原模板节点；不证明执行 |
| 来源与接口交接 | docflow/scripts/check_flow_handoff.py | 当前账本/合同 → 声明缺项；不证明软件运行 |
| 打开、受控修改、运行、导出 | operations/scripts/aspen_runtime.py、aspen_run_supervisor.py | 受保护同案文件与获准动作 → 同案结果/日志；按原锁与超时规则 |
| 读原生工具字段 | operations/scripts/query_manual_knowledge.py | 实际节点/关键词 → 已登记操作说明；未知项继续查合法帮助 |
| 建普通精馏塔岛 | tower_script_handoff.md；candidate_matrix_template.py；operation_template.py；extract_distillation_patterns.py | 复制进料建 DSTWU 子模板 → 文本外层候选与现有卡片线索；塔内 SPEC/VARY 的真实建卡、运行、残差和回装另需版本核实，不能由这些模板自动证明 |
| 找设备/压力问题 | expert_cli 的 equipment、pressure、feedback | 同案参数/单位/来源 → 已注册计算、局部缺口与需复算的消费者 |
| 收敛/产品正常后交付 | operations/scripts/aspen_clean_delivery_audit.py、aspen_evidence.py | 精确候选的原始证据 → 严格验收；静态文本通过不代替重开运行 |
| 检索旧经验 | 各owner ERROR_MEMORY；adaptive/query_error_memory.py | 触发/项目范围 → 有作用域的经验；旧案数值不可直接迁移 |
| 保存当前新经验 | 原process-slice、learning-admission/evolution入口 | 当前项目审计先保存；用户确认结束后才走共享晋升门 |

这些资产没有因入口整理而删除。完整存量与三处镜像的身份应以本轮审计清单为准，
私有补充与发行副本有差异不意味着应相互覆盖。

## MCP与本地程序的边界

新增 workflow_lookup 让助手按注册ID读取19个Skill和完整方法，或查询原脚本图谱；
它只提供指引与定位。实际设备/压力计算仍由原来的已注册工具执行；
Aspen模型操作仍需合法软件与原COM/脚本路径。
当前会话未列出某MCP工具时，使用同一实现的CLI，不谎称工具已连接。

用现有安装路径发现运行根，运行 tools/expert_cli.py --schema workflow-catalog。
以下是请求内容；通过 --request 请求文件 --output 新回执文件 调用：

```json
{"operation":"workflow","payload":{"action":"list"}}
```

```json
{"operation":"workflow","payload":{"action":"read","mode":"resource","resource":"unit-build"}}
```

```json
{"operation":"workflow","payload":{"action":"script","path_name":"tower_island"}}
```

方法资源还包括 native-tools、tower-method、script-catalog。
读完整Skill用 action=read、mode=skill、skill_id=表中真实名称。
返回路径、原文和哈希仅证明读到了哪个版本；不是完成建模或工程验收的证明。
