# 普通精馏塔：原模板脚本与项目适配

本参考只在普通塔的 DSTWU 子模板、进料板/总级数候选和回装任务触发。
塔工艺顺序与验收仍由 [塔完整方法](tower_optimization_workflow.md)决定；
脚本负责可重复的候选生成、受控运行和取证，不能取代相平衡、自由度或
塔内 Design Spec 判断。首次运行前先读当前项目的来源/变更偏移表和本机版本帮助。

## 先确认实际有的资产

| 资产 | 在这条链中的作用 | 不具备的能力 |
| --- | --- | --- |
| `../../aspen-document-driven-flowsheet/scripts/query_script_template_graph.py --path-name tower_island`，或 `workflow_lookup` 的 `action=script` | 只读返回原脚本图谱与模板路径 | 不创建案例、不调用 Aspen |
| `../../aspen-document-driven-flowsheet/scripts/templates/aspen_candidate_matrix_template.py` | `--spec-json` + `--out-dir`；按项目 JSON 的 `cases[].patches` 从指定文本基案生成离散候选及 sidecar，默认 `--mode generate` | 正则替换只检查是否命中，不理解卡片语义；不创建/验证原生塔内 SPEC/VARY；`generate-run` 只运行调用方给出的 shell 命令 |
| `../../aspen-document-driven-flowsheet/scripts/templates/aspen_operation_template.py` | 在既有合法 Aspen runtime/监督器下打开、运行、导出受保护候选 | 没有现成的 NSTAGE、进料级、RR/D:F 或 SPEC/VARY 写卡函数 |
| `../../aspen-document-driven-flowsheet/scripts/extract_distillation_patterns.py` | 从已有 BKP/APWZ 抽取 NSTAGE、FEED-STAGE、RR、D/F 等卡片线索 | 只读摘要，不修改卡片；匹配到字段不证明对象运行、目标收敛或导出完整 |

目前没有经过同案验证的端到端脚本，能直接完成
“DSTWU 子模板→进料板逐点→再调级数→每点原生双 SPEC/VARY→回装”。
不得把上述模板命名、图谱节点或只读 MCP 回执说成这种能力已经存在。

## 脚本怎么接到真实方法

1. **隔离初估。** 从母流程冻结的同版进料复制入口状态和组分/物性/压力依据，
   建独立 DSTWU 子模板，只添加该塔及必需连接。保持母流程原塔和进料不变。
   依据当前来源允许的回流或级数规定运行 DSTWU，记录最小量、选定 N₀、
   进料位置种子、RR/D:F 种子及它们的同案导出。无获准设计规定时
   DSTWU 不能凭空给唯一实际 N₀。
2. **严格塔与内层求解。** 在独立塔岛用同边界建 RadFrac，先固定 N₀，
   按当前产品纯度/回收指标配置两项独立的塔内 SPEC/VARY，
   以 RR、D/F 为候选真实输入。先按操作层/本机版本帮助完成并导出原生
   对象、目标、单位、边界、唯一写入者和残差。候选矩阵不负责创建它们；
   缺少经过版本核实的建卡适配器时，先由操作层合法方法建卡/读回，
   不能退化为外部固定 RR、D/F 逐点试错。
3. **固定 N₀ 找进料级。** 使用候选矩阵的项目 JSON，
   只对受保护塔岛的目标塔块生成合法进料级候选。项目适配器须核
   块 ID、当前版本字段、每项替换的精确出现次数、级号范围及必要连接；
   原模板的“匹配数大于零”不足以证明只改了目标卡。
   每个候选通过原操作路径运行/导出，由原生塔内规格重新求 RR、D/F；
   同案检查两个产品目标、守恒、状态和 Qreb，选该 N₀ 可行范围内的
   低负荷进料位置，保留失败点。
4. **再调整总级数。** 以有据 N 候选生成新的离散外层；
   每个 N 改 NSTAGE 时同时核进料、采出、侧线、中段循环/分相位置的合法映射。
   上一步的进料级 j₀ 或 j₀/N₀ 比例只能当新 N 的初始位置，
   不能原号照搬或假定仍是低负荷点。对每个 N 重新核/寻找进料位置，
   并让两项塔内规格逐点重新求 RR、D/F。
   可用目标版本已核实的 NQ/Column Analysis 加速，或由候选矩阵编排
   离散案例；后一方式不能冒称原生 NQ/Sensitivity。
   比较 Qreb 时同时列塔高/级数、塔水力和设备投资负担；
   没有当前选择准则，不仅凭最大 N 的热耗较低就称“最优级数”。
5. **只回装最终严格塔。** 将选定、同案已验证且保留塔内 SPEC/VARY 的
   RadFrac 放回母流程原进出、回流和热压接口；不回装 DSTWU、
   子模板的临时进料/产品流股或外部固定控制值。
   用母流程真实进料和循环重新解 RR、D/F，刷新产品、Qreb、压力、
   塔水力及下游；精确交付文件另做严格无编辑复开运行。

每个候选记录：母案/子模板 SHA、同版进料边界、物性、N、进料级、
两个 SPEC/VARY 的目标/操纵量/边界/残差、RR、D/F、产品和 Qreb、
原始运行/历史、设备状态、失败原因、回装后身份。文本生成的静态 sidecar
只能作为候选清单，不能作为模拟通过或工程接受。

## MCP 与脚本执行边界

`workflow_lookup` 和 `query_script_template_graph.py` 只发现资产；
`aspen_solve_route` 只分类工具。原生塔卡的写入、运行和导出经
`aspen-plus-operations` 的版本合格 COM/MCP/脚本路径及保护副本执行。
候选矩阵模板的 `generate-run` 接受任意 shell 命令，不能无审核地
作为通用 MCP 执行接口暴露。当前任务若只做文字规划，应给适配方案与
待验证项，不声称已启动 Aspen 或已完成任何一轮候选。
