# Aspen Plus 经典案例 Playbook

来源：`Aspen Plus-孙兰义.pdf` 章节提取层，尤其 `../chapter_extracts/` 中第 3、4、7、8、9、10、11、12、13、14、15 章。

用途：给 Codex 后续操作 Aspen Plus 时使用的“案例模式库”。它不替代 `knowledge_graph_index.md`、`unknowns_router.md`、`kinetics_expert_system.md`，而是在遇到相似任务时提供可迁移的建模套路、卡片路径、排障顺序和误用门禁。

## 0. 使用协议

1. 先按 `unknowns_router.md` 判定未知类型，再决定是否进入本文件。
2. 经典案例只能迁移四类内容：问题模式、Aspen 路径、字段含义、操作顺序。
3. 经典案例数值只属于原例题。不得把例题的流量、温度、压力、板数、回流比、持液量、压缩比、换热量、动力学参数、物性参数、控制器参数写成通用默认值。
4. 当前项目源文件永远高于讲义例题。若项目源文件与例题不同，以项目源文件为准。
5. 物性方法不确定时，先回 `ch03_property_methods_and_regression.md`，不要靠塔参数、回流比或收敛方法掩盖物性错误。
6. 任何涉及正式动力学的案例，必须先进入 `kinetics_expert_system.md` 和 `kinetics_freeze_template.md`，完成 `source equation/value -> source units -> conversion -> Aspen card units -> exact Aspen input -> exported verification`。
7. 若案例卡中提到某个例题数值，只把它当作“原例题事实”或“排障候选”，不能当作当前模型输入。

## 1. 案例选择索引

| 任务情景 | 优先案例卡 | 再查 |
| --- | --- | --- |
| 普通塔从初设到严格塔 | `CASE-COL-01`, `CASE-COL-02` | `ch07_column_shortcut_and_absorption.md`, `ch12_convergence_strategy.md` |
| 产品纯度/回收率/馏程点反求 | `CASE-TOOL-01`, `CASE-COL-02`, `CASE-COL-04` | `ch09_flowsheet_options_analysis.md` |
| 萃取精馏/共沸精馏/变压精馏 | `CASE-C10-ED-01`, `CASE-C10-AZ-01`, `CASE-C10-PSD-01` | `ch10a_extractive_azeotropic_pressure_swing.md` |
| 反应精馏/三相反应精馏 | `CASE-C10-RD-01`, `CASE-C10-3RD-01` | `ch10b_reactive_three_phase_distillation.md`, `kinetics_expert_system.md` |
| 多效/DWC/热泵/HIDiC | `CASE-C10-ME-01`, `CASE-C10-DWC-01`, `CASE-C10-HP-01`, `CASE-C10-HIDIC-01` | `ch10c_energy_saving_distillation_structures.md` |
| 塔板数、进料板、回流比、热负荷优化 | `CASE-ANALYSIS-01`, `CASE-C10-TA-01`, `CASE-C10-NQ-01` | `ch10d_column_analysis_nq_curves.md`, `ch15_appendices_tools.md` |
| 流程工具选型 | `CASE-TOOL-01` 到 `CASE-TOOL-04` | `ch09_flowsheet_options_analysis.md` |
| 全流程不收敛 | `CASE-CONV-01` | `ch11_process_simulation_workflow.md`, `ch12_convergence_strategy.md` |
| 原油/假组分/PetroFrac | `CASE-COL-04` | `ch13_petroleum_distillation.md` |
| 换热网络/节能改造/EDR | `CASE-ANALYSIS-02` | `ch15_appendices_tools.md`, `ch06_heat_exchanger_modules.md` |
| 反应器参数怎么填 | `CASE-RXN-01` 到 `CASE-RXN-05` | `ch08*.md`, `kinetics_expert_system.md` |
| 动态模拟/控制器迁移 | `CASE-DYN-01` 到 `CASE-DYN-04` | `ch14_dynamic_simulation.md` |

## 2. 通用迁移门禁

### 2.1 可以迁移

- Aspen 模块选择逻辑。
- Aspen 路径和页面名称。
- 字段意义与互斥关系。
- 先简单后严格、先无循环后闭合、先基线后优化的建模顺序。
- 结果查看路径和证据要求。
- 收敛排障的诊断顺序。

### 2.2 不可直接迁移

- 例题的组分、流量、温度、压力、热负荷、塔板数、进料板、回流比、压降、持液量、停留时间。
- 例题的物性方法，除非当前体系与例题相平衡特征、组分族和数据来源一致。
- 例题的二元参数、回归参数、Henry 参数、LLE 数据库来源。
- 例题的动力学 `k/E/Exponent/[Ci] basis/Rate basis/LHHW/USER`。
- 例题节能比例、压缩比、电热折算系数、板间换热量、夹点温度。
- 例题控制器死区、扰动幅度、控制器方向、动态导出文件名。

## 3. 基础建模与物性案例

### CASE-BASE-01 | ch02 | 异丙苯基础流程骨架

- 使用场景：新建 Aspen 文件、录入组分、建立简单反应或流程骨架、查看基础结果。
- 来源：`ch02_flowsheet_setup_basics.md`，讲义例题使用苯和丙烯生成异丙苯作为基础流程。
- Aspen 路径或模块/卡片：`Components|Specifications`，`Properties|Methods`，`Streams|FEED|Input|Mixed`，`Results Summary|Streams|Material`。
- 可迁移做法：先定义组分和物性方法，再填进料温度、压力、流量、组成，最后运行并到 Results Summary 查看产品流股。
- 不可迁移内容：例题 `FEED` 的温度、压力、苯/丙烯流量、`PRODUCT` 中异丙苯结果只属于讲义例题。
- 误用警戒：基础流程能跑通不代表反应器、物性或分离已经工程正确；它只适合作为 Aspen 工作流入口。
- 未知路由：`unknowns_router.md` -> `../chapter_extracts/ch02_flowsheet_setup_basics.md`。

### CASE-PROP-01 | ch03 | 乙酸-水物性反例

- 使用场景：精馏/共沸/强非理想体系结果与常识冲突，怀疑物性方法漏掉气相缔合或特殊相平衡。
- 来源：`ch03_property_methods_and_regression.md`，乙酸-水体系。
- Aspen 路径或模块/卡片：`Properties|Methods|Global`，必要时查二元参数、气相缔合模型和 VLE 结果。
- 可迁移做法：若普通 NRTL 等方法预测出与常识冲突的共沸或相图，先复核体系是否需要气相缔合模型，如 NRTL-HOC 这类路线。
- 不可迁移内容：乙酸-水的模型选择不能推广到所有有机酸/水体系；仍需按当前组分、数据和压力范围判定。
- 误用警戒：物性方法选错会改变“是否共沸”“能否分离”的方向性判断，不是小数值误差。
- 未知路由：`unknowns_router.md` -> `../chapter_extracts/ch03_property_methods_and_regression.md`。

### CASE-PROP-02 | ch03 | Data Fit / Regression 物性数据回归

- 使用场景：缺纯组分温度相关参数、二元 VLE/LLE 参数，或数据库参数来源不可靠。
- Aspen 路径或模块/卡片：`Data` 实验数据；`Run Mode=Regression`；`Regression|Setup/Parameters`；结果看 `Results|Parameters/Residual/Sum of Squares/Profiles/Consistency Tests`；参数回写到 `Methods|Parameters`。
- 可迁移步骤：先确定物性方法框架；录入实验数据并定义数据类型，如 `PURE-COMP + TDEW` 或 `MIXTURE + TPXY`；映射待回归参数；运行后检查参数标准差、残差、平方和、作图和一致性检验；必要时用 TDE 数据补充。
- 不可迁移内容：Wilson/NRTL 参数、PLXANT 系数、组分顺序、实验数据点不可复用。
- 误用警戒：回归收敛不等于物性可信；TPXY 组分顺序错会让结果物理意义错；估算值和回归值必须标明来源。
- 未知路由：`../chapter_extracts/ch03_property_methods_and_regression.md`。

### CASE-BASIC-01 | ch04 | Mixer/FSplit/Flash/Decanter/Sep 快速闭合

- 使用场景：流程初期需要先把混合、分流、相分离、抽象分离跑通。
- Aspen 路径或模块/卡片：`Blocks|MIXER|Input|Flash Options`；`Blocks|FSPLIT|Input|Specifications/Key Components`；`Blocks|FLASH2/FLASH3|Input|Specifications`；`Blocks|DECANTER|Input|Specifications/Efficiency`；`Blocks|SEP|Input|Specifications/Feed Flash`。
- 可迁移步骤：先判定任务是混合、分流、复制/缩放、闪蒸、液液分相还是按组分去向分离；Flash2/Flash3 用温度、压力、气相分数、热负荷中允许的两个量闭合；Decanter/Flash3 要明确第二液相判定；Sep 只用于已知组分去向的抽象分离。
- 不可迁移内容：例 4.5 的 `Duty=0` 和压力、例 4.6/4.7 的物性方法、Decanter 分离效率、Sep 组分流量不可复用。
- 误用警戒：FSplit 不是分相器；Flash2/Flash3 不能同时规定气相分数和热负荷；Sep 不是严格分离机理，若用户禁用 `SEP` 或要求物理设备，不可用它偷懒。
- 未知路由：`../chapter_extracts/ch04_mixing_flash_sep_modules.md`。

## 4. 塔设备基础与优化案例

### CASE-COL-01 | ch07 | Shortcut 到 RadFrac 的塔初设迁移

- 使用场景：普通精馏先估理论板数、回流比、进料板，再转严格塔精算。
- Aspen 路径或模块/卡片：Shortcut/DISTL 类简捷塔；`Blocks|RADFRAC|Specifications|Setup|Configuration/Streams/Pressure/Operating specifications`。
- 可迁移步骤：先用简捷塔给板数、回流比、进料位置初值；再建 RadFrac，明确冷凝器、再沸器、级数、压力、进料板和操作规定；产品纯度或回收率不达标时用 `Design Specifications + Vary` 调整。
- 不可迁移内容：例题塔板数、回流比、塔顶/塔底流量、压力、进料位置、物性方法只属于原例题。
- 误用警戒：简捷结果不能作为最终严格设计；RadFrac 的级数通常包含冷凝器和再沸器；不要用调物性方法掩盖产品纯度不达标。
- 未知路由：`../chapter_extracts/ch07_column_shortcut_and_absorption.md` -> `../chapter_extracts/ch12_convergence_strategy.md`。

### CASE-COL-02 | ch07/ch12 | RadFrac 严格塔规格、设计规定与收敛

- 使用场景：精馏、汽提、萃取精馏、共沸精馏、吸收等需要严格相平衡和塔内曲线的分离。
- Aspen 路径或模块/卡片：`Blocks|RADFRAC|Specifications|Setup|Configuration`；`...|Streams`；`...|Pressure`；`...|Design Specifications/Vary`；`Blocks|RADFRAC|Convergence|Convergence`。
- 可迁移步骤：先锁物性方法；再填级数、冷凝器/再沸器、有效相态、收敛方法、压力路径；操作规定优先选择工程上稳定的回流比、产品流量或产品/进料比；纯度/回收率目标用 Design Spec + Vary；不收敛时先看 `Err/Tol`、初值、规格可行性和 RadFrac 预置收敛方法。
- 不可迁移内容：乙苯-苯乙烯等例题的 `Standard` 方法、压力、产品规格、板数、迭代次数不可直接外推。
- 误用警戒：一个 Design Spec 应配可行的输入变量；规格过严时先放宽拿到收敛解再逐步收紧；不要一开始就盲目改容差。
- 未知路由：`../chapter_extracts/ch07_column_shortcut_and_absorption.md` -> `../chapter_extracts/ch12_convergence_strategy.md`。

### CASE-COL-03 | ch07 | Absorption / ABSORBER 与 RadFrac 吸收配置

- 使用场景：气体中稀溶质被液体吸收剂吸收，或需按吸收塔方式设置 RadFrac。
- Aspen 路径或模块/卡片：`Blocks|ABSORBER`；或 `Blocks|RADFRAC|Setup|Configuration/Streams/Pressure`；必要时 `RadFrac|Convergence|Advanced|Absorber=YES`。
- 可迁移步骤：先确认吸收剂、轻气 Henry 组分和物性方法；按塔板数、进料位置、压力、有效相态建吸收塔；不收敛时检查相态、Henry 参数、温度估值、迭代次数和 Absorber 选项。
- 不可迁移内容：水/胺吸收剂流量、塔板数、压力、Henry 参数、迭代次数只属于原例题。
- 误用警戒：复杂反应吸收、多相吸收不得从普通吸收例题外推；Henry 组分和参数缺失时，收敛结果也不可信。
- 未知路由：`../chapter_extracts/ch07_column_shortcut_and_absorption.md` -> `../chapter_extracts/ch03_property_methods_and_regression.md`。

### CASE-COL-04 | ch13 | PetroFrac 原油常压塔/石油蒸馏

- 使用场景：原油评价、假组分生成、常压塔、侧线汽提、中段回流、产品馏程约束。
- Aspen 路径或模块/卡片：`Components|Assay/Blend|Assay Data`；`Components|PetroCharacterization|Generation|Cuts`；`Columns|PetroFrac|CDU*`；`Blocks|CRUDE|Setup|Pressure/Strippers/Pumparounds/Design Specifications`。
- 可迁移步骤：先导入或录入蒸馏曲线与重度/API；将 ASTM D86/D1160/D2887 等按规则换算/拟合到 TBP 表征；生成假组分；PetroFrac 中填全塔板、压力、炉出口、进料方式、侧线汽提与中段回流；用 Design Spec 约束产品 D86/TBP 关键点；结果看 TPFQ、Vol.% Curves、5%/95% 点和整条曲线。
- 不可迁移内容：25 块理论板、塔顶产品流量、炉出口温度、压力分布、蒸汽比例、D86 目标温度等都是例题条件。
- 误用警戒：不能把 ASTM D86 直接当 TBP；不能用普通恒摩尔回流精馏假设硬套原油常压塔；只看收敛和流量不能证明馏分合格。
- 未知路由：`../chapter_extracts/ch13_petroleum_distillation.md`。

## 5. 流程工具情景案例

### CASE-TOOL-01 | ch09 | Design Spec 目标反求

- 使用场景：产品纯度、回收率、馏程点、循环杂质或控制目标需要通过调某个输入变量满足。
- Aspen 路径或模块/卡片：`Flowsheeting Options|Design Specs|DS-*|Input|Define/Spec/Vary`；结果看 `DS-*|Results` 和对应收敛模块。
- 可迁移步骤：先定义采集变量；再设 `Target` 与 `Tolerance`；最后选择输入变量作为 `Vary` 并给上下限；上线前用 Sensitivity 验证目标落在可行范围。
- 不可迁移内容：目标纯度、容差、操纵变量上下限、初值不可复用。
- 误用警戒：Design Spec 改的是输入变量，不是直接改结果；多个 Design Spec 会引入强耦合回路；守恒闭合问题优先考虑 Balance。
- 未知路由：`../chapter_extracts/ch09_flowsheet_options_analysis.md` -> `../chapter_extracts/ch12_convergence_strategy.md`。

### CASE-TOOL-02 | ch09/ch10A | Calculator / Balance 用于补料和显式逻辑

- 使用场景：补充溶剂等于各损失流之和、压降/经验式计算、外部 Fortran/Excel 逻辑写回流程。
- Aspen 路径或模块/卡片：`Flowsheeting Options|Calculator|C-*|Input|Define/Calculate/Sequence`；守恒闭合用 `Flowsheeting Options|Balance|B-*`。
- 可迁移步骤：明确输入变量和输出变量；写单位一致的显式公式；设置 Calculator 在被修改模块之前或结果生成之后执行；若只是物料/能量守恒，改用 Balance 减少收敛回路。
- 不可迁移内容：补料流名、损失流名、Fortran 变量名、计算公式数值系数不可复用。
- 误用警戒：Sequence 错会导致本轮计算未生效；所有收敛模块都收敛但总量衡算不闭合时优先查 Calculator；不要用 Calculator 代替本该由 Design Spec 求根的问题。
- 未知路由：`../chapter_extracts/ch09_flowsheet_options_analysis.md` -> `../chapter_extracts/ch12_convergence_strategy.md`。

### CASE-TOOL-03 | ch09/ch10A/ch10C | Sensitivity 变量筛选

- 使用场景：萃取剂量、回流比、进料温度、压缩比、热负荷、产品纯度等 what-if 扫描。
- Aspen 路径或模块/卡片：`Model Analysis Tools|Sensitivity|S-*|Input|Vary/Define/Tabulate/Fortran`；结果看 `Results|Summary` 和曲线。
- 可迁移步骤：先定义要观察的结果变量；再给输入变量范围和步长；必要时用 Fortran 定义组合指标；用曲线判断单调性、峰谷、平坦区和约束边界，再决定 Design Spec 或 Optimization 范围。
- 不可迁移内容：苯酚初值、扫描范围、温度压力点、压缩比范围不可复用。
- 误用警戒：Sensitivity 不会把结果写回基础模型；范围过宽会制造无意义失败点；不能用一次扫描替代最终严格收敛验证。
- 未知路由：`../chapter_extracts/ch09_flowsheet_options_analysis.md`。

### CASE-TOOL-04 | ch09 | Optimization + Constraint 正式优化

- 使用场景：在稳定流程上最小化能耗/蒸汽用量/公用工程，或最大化收益/选择性，并受产品质量、排放或流量约束。
- Aspen 路径或模块/卡片：`Model Analysis Tools|Optimization|O-*|Input|Define/Objective & Constraints/Vary`；`Model Analysis Tools|Constraint(s)|C-*|Input|Define/Spec`。
- 可迁移步骤：先让基础模拟稳定；用 Sensitivity 缩小决策变量范围；定义目标函数采集变量；挂接约束；给决策变量上下限；优化后同时检查 Optimization 与 Constraint 结果。凡是塔、反应器、溶剂循环、压缩网络或换热/节能分支已经稳定，且存在两个及以上可调变量或明确能耗-质量-转化率权衡时，应优先创建并保留 Optimization 对象作为正式优化证据；手动扫描只用于找边界和初值。
- 不可迁移内容：目标函数变量、约束上限、蒸汽流量范围等例题范围不可迁移。
- 误用警戒：Optimization 难执行、难收敛；基础流程不稳时优化只会放大错误；变量范围过宽会显著增加失败概率。若合格分支跳过 Optimization，必须在优化记录中说明原因，如只有一个自由度、目标更适合 Design Spec、Aspen 对该模块不可用、基础模型未稳、或用户明确暂缓。
- 未知路由：`../chapter_extracts/ch09_flowsheet_options_analysis.md` -> `../chapter_extracts/ch12_convergence_strategy.md`。

### CASE-CONV-01 | ch11/ch12 | 通用流程与 RadFrac 收敛策略

- 使用场景：循环物流、Design Spec、Calculator、Optimization、复杂塔或全流程不收敛。
- Aspen 路径或模块/卡片：`Convergence|Tear`；`Convergence|Convergence`；`Convergence|Nesting Order`；`Convergence|Sequence`；`Convergence|Options`；`Convergence|Convergence|<CV>|Results|Tear History/Spec History`；RadFrac 用 `Blocks|RADFRAC|Convergence|Convergence|Basic/Advanced`。
- 可迁移步骤：先判断单元模块错误还是流程收敛错误；打开诊断，推荐 `Simulation=3`、`Convergence=5`；看 `Max Err/Tol` 走势；tear 优先选变量少、组成稳定、变化幅度小的物流；慢收敛先改善初值和增加迭代，Wegstein 慢可调 Lower bound，振荡可调 Upper bound 或换 Broyden/Direct；平台期检查内外层容差；强耦合用 Broyden/Newton 联解。
- 不可迁移内容：迭代次数、Wegstein Lower bound、Upper bound、Wait 等只可作为排障候选，不是默认卡值。
- 误用警戒：所有收敛模块显示收敛但总量不闭合时查 Calculator；改条件后要初始化；复杂流程先简单模块、先物料衡算、先子流程，再逐步替换严格模块。
- 未知路由：`../chapter_extracts/ch11_process_simulation_workflow.md` -> `../chapter_extracts/ch12_convergence_strategy.md`。

## 6. 复杂精馏案例

### CASE-C10-ED-01 | ch10A | 萃取精馏

- 问题模式：相对挥发度小、沸点差小、普通精馏塔板数过多。
- Aspen 路径或模块/卡片：`RadFrac` 主塔 `EXT-COL`；`Blocks|EXT-COL|Setup|Configuration/Streams/Pressure`；`Model Analysis Tools|Sensitivity`；再生塔 `REGEN`；`Flowsheeting Options|Calculator` 或 `Balance` 做补料。
- 可迁移做法：先选萃取剂，再建“萃取塔 + 再生塔 + 溶剂循环 + MAKEUP”；先跑主塔，再加再生塔和循环；用 Sensitivity 同时看产品纯度和再沸器热负荷；补充溶剂按损失量闭合。
- 不可迁移内容：例 10.1 的 UNIFAC、苯酚、溶剂流量、压力、板压降、进料板位等只属例题。
- 误用警戒：不得把例题溶剂比当通用经验；萃取剂必须满足不共沸、不反应、易再生、热稳定等条件。
- 未知路由：`../chapter_extracts/ch10a_extractive_azeotropic_pressure_swing.md`；物性不确定转 `../chapter_extracts/ch03_property_methods_and_regression.md`。

### CASE-C10-AZ-01 | ch10A | 非均相共沸精馏

- 问题模式：形成共沸，且塔顶冷凝后存在液液分层，或需共沸剂改变精馏边界。
- Aspen 路径或模块/卡片：`Home|Residue Curves / Distillation Synthesis ternary maps`；`RadFrac` 主塔 `COL-MAIN` 与回收塔 `COL-REC`；`Vapor-Liquid-Liquid`；`Blocks|...|Setup|3-Phase`；`DECANTER`；`Design Specifications`；流程 `Convergence`。
- 可迁移做法：先画三元残余曲线/精馏区域，再用原料点和共沸剂点连线选初值；先建无循环流程，再逐步闭合回收与共沸剂循环；三相塔用 Decanter 和 3-Phase 设置；中间解时先 Generate Estimates，再改 Newton/Dogleg。
- 不可迁移内容：例 10.2 的 UNIQ-RK、共沸剂初值、进料板位、设计纯度、递增序列不可迁移。
- 误用警戒：不得只按 VLE 处理部分互溶体系；二元参数需支持 LLE；共沸剂初值不能只追求最小用量而贴近精馏边界。
- 未知路由：`../chapter_extracts/ch10a_extractive_azeotropic_pressure_swing.md`；LLE/二元参数转 `../chapter_extracts/ch03_property_methods_and_regression.md`；RadFrac 不收敛转 `../chapter_extracts/ch12_convergence_strategy.md`。

### CASE-C10-PSD-01 | ch10A | 变压精馏

- 问题模式：共沸组成随压力显著变化，或某压力下共沸消失。
- Aspen 路径或模块/卡片：不同压力下相图/T-xy 分析；两个 `RadFrac` 塔 `HP` 与 `LP`；`Setup|Pressure`；`Join Streams` 闭合循环。
- 可迁移做法：先比较不同压力下 T-xy/相图，确认共沸组成变化足够大或共沸消失；先做全流程与局部物料衡算估循环初值；先无循环双塔跑通，再闭合循环。
- 不可迁移内容：例 10.3 的 THF/H2O、NRTL-RK、低压/高压数值、循环流初值等只属例题。
- 误用警戒：未验证压力敏感性就套用变压精馏是错误路线；高低压选择需兼顾能耗、设备投资和热集成温差。
- 未知路由：`../chapter_extracts/ch10a_extractive_azeotropic_pressure_swing.md`；压力设备转 `../chapter_extracts/ch05_pressure_modules.md`；收敛转 `../chapter_extracts/ch12_convergence_strategy.md`。

### CASE-C10-RD-01 | ch10B | 反应精馏

- 问题模式：可逆反应与分离耦合，通过连续移出产物/反应物提高转化率或选择性。
- Aspen 路径或模块/卡片：`Columns|RadFrac|FRACT1`；`Reactions|Reactions` 新建 `REAC-DIST`；`Stoichiometry`；`Kinetic`；`Blocks|RD|Reactions|Specifications`；`Holdups`。
- 可迁移做法：反应对象、反应段、Holdups 三者必须同时闭合；压力是首要工艺变量；反应段必须显式指定；Holdups 是速率相关量，后续需用塔径校核。
- 不可迁移内容：例 10.4 的物性方法、板数、压力、进料板、回流比、采出量、持液量、动力学参数只属例题。
- 误用警戒：严禁复制例题动力学、`k/E/Exponent/[Ci] basis`；不得默认全塔反应；不得把 Holdups 当普通收敛调节量。
- 未知路由：任何动力学字段先 `kinetics_expert_system.md` + `kinetics_freeze_template.md`；再查 `../chapter_extracts/ch10b_reactive_three_phase_distillation.md`。

### CASE-C10-3P-01 | ch10B | 三相精馏

- 问题模式：汽-液-液三相平衡，塔内或冷凝器中出现分相。
- Aspen 路径或模块/卡片：`Columns|RadFrac|DECANT3`；`Blocks|3PHD|Setup|Configuration` 三相区；`Configuration|Decanters`；`2nd liquid`；液相返塔比例。
- 可迁移做法：明确三相区、Decanter 所在板、第二液相关键组分、两液相返塔比例、抽出位置；LLE 参数来源需核查。
- 不可迁移内容：例 10.5a 的物性方法、塔板数、回流比、塔顶流量、有机相/水相返塔比例等不可迁移。
- 误用警戒：不得把三相塔简化成普通 VLE RadFrac；第二液相不能凭名称猜，需按关键组分或数据定义。
- 未知路由：`../chapter_extracts/ch10b_reactive_three_phase_distillation.md`；LLE 参数转 `../chapter_extracts/ch03_property_methods_and_regression.md`。

### CASE-C10-3RD-01 | ch10B | 三相反应精馏

- 问题模式：同一塔内既有反应，又有汽-液-液分相。
- Aspen 路径或模块/卡片：`Columns|RadFrac|DECANT1`；`REAC-DIST`；`Stoichiometry/Kinetic`；`Setup|Configuration` 三相区；`Decanters`；`Reactions|Specifications/Holdups`。
- 可迁移做法：分别定义反应对象、反应段、Holdups、三相区、Decanter 和两液相返塔比例；反应位置和分相位置不能互相替代。
- 不可迁移内容：例 10.5b 的物性方法、Decanter 板位、返塔比例、再沸器反应、持液量等只属例题。
- 误用警戒：动力学和三相设置都不可省；若题源只说“会反应”，不能自动填 Kinetic 参数或铺满全塔反应段。
- 未知路由：动力学先 `kinetics_expert_system.md`；三相/Decanter 查 `../chapter_extracts/ch10b_reactive_three_phase_distillation.md`。

## 7. 复杂精馏节能技术案例

### CASE-C10-ME-01 | ch10C | 双效/多效精馏

- 问题模式：利用相邻塔压力层级，使一塔冷凝热供另一塔再沸。
- Aspen 路径或模块/卡片：多个 `RadFrac`；`Heater`/热流概念验证；必要时 `HeatX`；全局 Design Spec 匹配热负荷。
- 可迁移做法：建模顺序为基线单塔 -> 无热耦合双塔 -> 加热耦合 -> 调压力层级 -> 能耗比较；先用 Heater 稳定，再用 HeatX 细化；压力层级由可用温差倒推。
- 不可迁移内容：例题塔压、热负荷相等目标、具体塔数与压力均不可迁移。
- 误用警戒：多效不是效数越多越好；没有足够温差或经济性不成立时不应强行多效。
- 未知路由：`../chapter_extracts/ch10c_energy_saving_distillation_structures.md`；换热器转 `../chapter_extracts/ch06_heat_exchanger_modules.md`；能量分析转 `../chapter_extracts/ch15_appendices_tools.md`。

### CASE-C10-DWC-01 | ch10C | 隔壁塔 / DWC

- 问题模式：三组分以上切成三个高纯产品，需提高中间组分纯度并减少返混。
- Aspen 路径或模块/卡片：`MultiFrac|PETLYUK` 或多个 `RadFrac` 连接；`Connect Streams`；`Design Specifications`；`Vary`。
- 可迁移做法：先判断中间组分占比、三产品纯度、相对挥发度和压力约束；DWC 可用 MultiFrac 直接法或 RadFrac 近似连接法；设计规定围绕三个产品纯度建立，操纵变量通常围绕塔顶/侧线/内部连接/回流相关量。
- 不可迁移内容：中间组分比例提示、内部连接流初值、产品纯度目标都不可照搬。
- 误用警戒：中间产品纯度要求不高时不要强上 DWC；内部连接物流需逐步逼近，不能猛改；压力不能随意改。
- 未知路由：`../chapter_extracts/ch10c_energy_saving_distillation_structures.md`；收敛转 `../chapter_extracts/ch12_convergence_strategy.md`。

### CASE-C10-HP-01 | ch10C | 热泵精馏

- 问题模式：塔顶冷凝温度与塔底再沸温度差不大，可用压缩提升热品位。
- Aspen 路径或模块/卡片：`COMPR`；辅助 `Heater/Reboiler`；`FLASH`；`VALVE`；分流器；Tear streams；Sensitivity 扫压缩比。
- 可迁移做法：先建常规塔基线；再加压缩机并扫压缩比；再用辅助再沸器、闪蒸器、阀门和分流器闭合；电功按项目约定折算成等量热负荷后再比较能耗。
- 不可迁移内容：例题压缩比、目标温差、节能比例、电热系数等不可通用外推。
- 误用警戒：不得只看压缩机功率；温差过大时压缩比和电耗会恶化；返塔相态不满足时需辅助设备。
- 未知路由：压缩机/阀门转 `../chapter_extracts/ch05_pressure_modules.md`；换热转 `../chapter_extracts/ch06_heat_exchanger_modules.md`；流程收敛转 `../chapter_extracts/ch12_convergence_strategy.md`。

### CASE-C10-HIDIC-01 | ch10C | HIDiC 内部热耦合精馏

- 问题模式：精馏段高压、提馏段低压，塔内逐板热集成。
- Aspen 路径或模块/卡片：分段 `RadFrac`，如 RECT/STRIP；`COMPR`；`VALVE`；`Side Duties`；Tear streams；Design Spec。
- 可迁移做法：先确认板间温差足够；先小热量启动，再逐步放大；保留辅助冷凝器/再沸器帮助收敛，跑通后再削减；压缩比、板间换热量和产品纯度目标需要逐步优化。
- 不可迁移内容：例题总换热量、每板换热量、板间温差阈值、产品纯度和节能比例都不可直接迁移。
- 误用警戒：没有板间温差时不能硬塞换热量；压缩比会同时影响电耗、温差和换热面积，必须优化。
- 未知路由：`../chapter_extracts/ch10c_energy_saving_distillation_structures.md`；压力设备转 `../chapter_extracts/ch05_pressure_modules.md`；换热转 `../chapter_extracts/ch06_heat_exchanger_modules.md`；收敛转 `../chapter_extracts/ch12_convergence_strategy.md`。

## 8. 塔分析、节能分析与外部工具案例

### CASE-C10-TA-01 | ch10D | 塔热分析 Thermal Analysis

- 使用场景：判断热负荷分配、进料点、进料热状态、中间冷凝器/再沸器潜力。
- Aspen 路径或模块/卡片：`Blocks|RADFRAC|Analysis|Analysis Options` 选择 `Thermal Analysis`；看 `S-H`、`T-H`、`Exergy loss`。
- 可迁移步骤：用 S-H/T-H 曲线判断进料板是否过上/过下；曲线越对称，热负荷分配通常越合理；曲线面积可提示中间换热设备潜力。
- 不可迁移内容：例题进料板调整、热负荷减少量、进料温度变化不可迁移。
- 误用警戒：Thermal Analysis 是设计诊断工具，不是最终合格证明；`Exergy loss` 只能作辅助判据。
- 未知路由：`../chapter_extracts/ch10d_column_analysis_nq_curves.md`。

### CASE-C10-NQ-01 | ch10D | NQ 曲线

- 使用场景：筛选塔板数 N、进料板、回流比与总热负荷 Q 的组合。
- Aspen 路径或模块/卡片：`Blocks|COLUMN|Analysis|NQ Curves`；`NQ Curves|Setup|Specifications`；`Convergence|Advanced|NQ-Fopt-Meth`。
- 可迁移步骤：设目标函数、塔板数上下限和进料板范围；用 NQ 曲线快速筛掉边际收益低的塔板数区间；两相塔可用 Hybrid，三相塔用 Case study 更稳。
- 不可迁移内容：例题最优板数、进料板和边际收益平坦位置只属例题。
- 误用警戒：NQ 基于平衡级模型，不适用于速率模型；塔板数上限不能超过基本工况塔板数；警告不等于失败，要看是否进入稳定区。
- 未知路由：`../chapter_extracts/ch10d_column_analysis_nq_curves.md`；速率模型/动力学转 `kinetics_expert_system.md`。

### CASE-ANALYSIS-01 | ch10D/ch15 | Column Analysis / Thermal / Hydraulic / NQ 联用

- 使用场景：塔板数、进料板、回流比、热负荷、水力学负荷和中间冷凝/再沸潜力诊断。
- Aspen 路径或模块/卡片：`Blocks|RADFRAC|Analysis|Analysis Options`；`Blocks|COLUMN|Analysis|NQ Curves`；`Tray Rating|1|Setup|Design/Pdrop/Downcomers`；`Pack Rating|1|Setup|Design/Pdrop`。
- 可迁移步骤：先做 Thermal Analysis 看 S-H/T-H 对称性和进料板突变；再做 Hydraulic Analysis，确认 Actual flow 低于 Hydraulic maximum；用 NQ Curves 筛塔板数、进料板和热负荷平坦区；最后回到严格塔验证产品指标。
- 不可迁移内容：例题板数、进料板、热负荷降幅、液泛设置只能作为例题证据或候选，不可无审查照搬。
- 误用警戒：热力学上省热但水力学超限仍不可行；Column Analysis 不是最终证明。
- 未知路由：`../chapter_extracts/ch10d_column_analysis_nq_curves.md` -> `../chapter_extracts/ch15_appendices_tools.md`。

### CASE-ANALYSIS-02 | ch15 | Activated Energy Analysis / Exchanger Analysis

- 使用场景：已收敛流程的公用工程目标、温室气体目标、夹点、换热网络改造和 EDR 严格换热器设计。
- Aspen 路径或模块/卡片：`Utilities`；`Blocks|HEATER|Input|Utility`；`Home|Activated Analysis|Activated Energy Analysis`；`Energy Analysis|Home|Details`；`Home|Activated Analysis|Activated Exchanger Analysis`。
- 可迁移步骤：先确认流程已 Run 并收敛；绑定公用工程；生成 Energy Analysis 方案；比较基础/改造/目标方案；应用方案后补建 Aspen 模块并重新运行；需要严设时 Convert/Size/Accept EDR 设计，并将传热系数方法设为 Simulation。
- 不可迁移内容：公用工程 ID、换热器编号、费用、节能比例、夹点温度、传热系数不可迁移。
- 误用警戒：Generate 只是候选方案，不等于流程已改造；未绑定 Utilities 不应解释公用工程目标；不要补讲义外面积、材质、压降或经济假设。
- 未知路由：`../chapter_extracts/ch15_appendices_tools.md` -> `../chapter_extracts/ch06_heat_exchanger_modules.md`。

### CASE-ANALYSIS-03 | ch15 | CUP-Tower 外部塔内件校核

- 使用场景：板式塔、规整填料塔、散装填料塔、萃取塔的水力学设计/校核。
- Aspen 路径或模块/卡片：Aspen 侧 `Blocks|RADFRAC|Profiles|Hydraulics`；CUP-Tower 侧 `Aspen Plus` 数据导入。
- 可迁移步骤：从 Aspen 导出 Hydraulics 数据到 Excel；删除 `Molecular wt liquid from` 和 `Molecular wt vapor to` 两列；另存低版本 `.xls`；建议使用 `METCBAR` 单位；选择气液负荷最大的理论板导入 CUP-Tower；查看负荷性能图和报表。
- 不可迁移内容：文件名、示例塔结构参数、具体塔板编号不可迁移。
- 误用警戒：新塔设计与旧塔校核输入不同，旧塔校核必须有完整塔内件结构；单位制或列清洗错误会导致导入结果不可信。
- 未知路由：`../chapter_extracts/ch15_appendices_tools.md`。

## 9. 反应器经典案例

### CASE-RXN-01 | ch08A | 非动力学反应器选型

- 使用场景：只知道转化率、收率、产率分布、平衡限制或吉布斯最小化，不掌握可冻结的速率方程。
- Aspen 路径或模块/卡片：`RStoic`、`RYield`、`REquil`、`RGibbs`；对应章节 `ch08a_nonkinetic_reactors.md`。
- 可迁移做法：已知指定转化率用 RStoic；已知产率分布但化学计量不全用 RYield；已知平衡约束用 REquil；只想按吉布斯自由能最小化判断平衡组成用 RGibbs。
- 不可迁移内容：例题转化率、产率、平衡温差、组分列表和热边界不可复用。
- 误用警戒：只有转化率或收率时，不进入正式动力学填卡；不要为了用 RCSTR/RPlug 而发明 `k/E`。
- 未知路由：`../chapter_extracts/ch08a_nonkinetic_reactors.md`；若出现速率式再转 `kinetics_expert_system.md`。

### CASE-RXN-02 | ch08C | RCSTR 动力学反应器

- 使用场景：连续搅拌釜，已冻结动力学，需用体积或停留时间、压力和热边界计算。
- Aspen 路径或模块/卡片：`Blocks|RCSTR|Setup|Specifications`；`Blocks|RCSTR|Setup|Reactions`；全局 `Reactions|...|Stoichiometry/Kinetic`。
- 可迁移做法：先冻结 reaction set；再填压力、热边界、有效相态、反应器体积或停留时间；最后把 reaction set 从 Available 选入 Selected。
- 不可迁移内容：例题体积、停留时间、温度、压力、热负荷、相态和动力学不可迁移。
- 误用警戒：RCSTR 的体积/停留时间影响速率解释，不是任意调参；反应集创建不等于已挂到反应器。
- 未知路由：`../chapter_extracts/ch08c_rcstr_cards.md` -> `kinetics_expert_system.md`。

### CASE-RXN-03 | ch08D | RPlug PowerLaw 例 8.6 参数填卡

- 使用场景：已知气相幂律速率式、轴向温度 profile、反应器长度/直径/压降，适合平推流积分。
- Aspen 路径或模块/卡片：`Reactions|Reactions` 新建 `R-1`，选 `POWERLAW`；`Reactions|R-1|Input|Stoichiometry/Kinetic`；`Blocks|RPLUG|Setup|Specifications/Configuration/Reactions`。
- 可迁移做法：先在 Reactions 对象中建立反应集，填计量系数和每个速率式指数；Kinetic 页冻结 `Units`、`Reacting phase`、`k`、`E`、`[Ci] basis`；RPlug 块中选择 reactor type、温度 profile、长度、直径、压降，再挂接 reaction set。
- 不可迁移内容：例 8.6 的 `Units=ENG`、`Reacting phase=Vapor`、`k`、`E`、温度 profile、长度、直径、压降值都只属于该题。
- 误用警戒：幂律指数不等于计量系数；`Exponent` 空白默认 0；动力学参数不在 RPlug 块里，而在 `Reactions` 对象里；源式若是 LHHW/可逆驱动力/分压基准，不能强行塞 PowerLaw。
- 未知路由：`../chapter_extracts/ch08d_rplug_cards.md` -> `../chapter_extracts/ch08f_kinetics_parameter_card_audit.md` -> `kinetics_expert_system.md`。

### CASE-RXN-04 | ch08E | RBatch 动力学与停止判据

- 使用场景：间歇反应器，已冻结液相或指定相态动力学，需按操作时间和停止条件模拟。
- Aspen 路径或模块/卡片：`Reactions|...|Stoichiometry/Kinetic`；`Blocks|RBATCH|Setup|Specifications/Reactions/Stop Criteria/Operation Times`。
- 可迁移做法：先冻结 reaction set，再填进料总量、相态、温度/热边界、操作时间和停止判据；运行后检查随时间的组成或转化趋势。
- 不可迁移内容：例题 `k/E`、液相基准、操作时间、停止标准、初始装料不可复用。
- 误用警戒：没有停止判据或操作时间时，RBatch 结果缺少工艺意义；不要用间歇例题常数填连续反应器。
- 未知路由：`../chapter_extracts/ch08e_rbatch_cards.md` -> `kinetics_expert_system.md`。

### CASE-RXN-05 | ch08B/ch08F | LHHW / USER 反应卡片

- 使用场景：源速率式含动力学因子、推动力、吸附分母，或内置 PowerLaw/LHHW 不能表达，需要用户子程序。
- Aspen 路径或模块/卡片：`Reactions|R-1|Input|Kinetic` 的 LHHW kinetic expression；`Subroutine` 页；Fortran USER 子程序相关字段。
- 可迁移做法：LHHW 必须保留 kinetic factor、driving force、adsorption expression；无吸附影响才可令吸附指数或相关项为无影响；USER 必须有 Fortran 源码、接口、编译和测试证据。
- 不可迁移内容：任何 LHHW 常数、吸附参数、驱动力指数、USER 子程序名和参数不可从例题或旧模型复制。
- 误用警戒：讲义注明 LHHW 不适用于反应精馏系统；无法表达时应 USER/阻断，不能压成方便的 PowerLaw 代理并声称正式正确。
- 未知路由：`kinetics_expert_system.md` -> `../chapter_extracts/ch08b_reactions_kinetics_cards.md` -> `../chapter_extracts/ch08f_kinetics_parameter_card_audit.md`。

## 10. 动态模拟案例

### CASE-DYN-01 | ch14 | RadFrac 压力驱动动态导出

- 使用场景：稳态精馏塔要导出 Dynamics，或动态导出因压力拓扑、阀门、设备尺寸失败。
- Aspen 路径或模块/卡片：`Dynamics` export；Pressure Driven 模式；压力检查、阀门、设备尺寸和控制对象。
- 可迁移做法：导出前先检查压力拓扑和设备尺寸；压力驱动动态不是稳态直接另存，必须有压差、阀门和可积累设备。
- 不可迁移内容：例 14.1 的乙苯-苯乙烯塔文件名、控制参数和稳态规格不可迁移。
- 误用警戒：稳态收敛不等于动态可导出；HEATER `PRES=0`、无压差或无阀门常导致动态失败。
- 未知路由：`../chapter_extracts/ch14_dynamic_simulation.md` -> `../chapter_extracts/ch05_pressure_modules.md`。

### CASE-DYN-02 | ch14 | Flash 动态与液位/压力边界

- 使用场景：两相闪蒸器从稳态转动态，需要压力、体积、阀门和液位控制。
- Aspen 路径或模块/卡片：`Flash2` 稳态块；Dynamics export；动态控制器/阀门设置。
- 可迁移做法：先确认闪蒸稳态结果合理，再补动态必须的设备尺寸、压力边界和控制变量。
- 不可迁移内容：例 14.2 的扰动、尺寸、控制器参数和文件名不可迁移。
- 误用警戒：Flash2 可稳态闪蒸，不代表动态体积和液位已定义。
- 未知路由：`../chapter_extracts/ch14_dynamic_simulation.md`。

### CASE-DYN-03 | ch14 | RCSTR 温度控制

- 使用场景：放热 CSTR 需要温度控制策略或比较不同控制结构。
- Aspen 路径或模块/卡片：稳态 `RCSTR`；动态导出；温度控制器、冷却/加热操纵变量。
- 可迁移做法：先冻结动力学和热边界，再决定 PV/OP/作用方向；扰动测试只用于检验控制结构，不用于回填动力学。
- 不可迁移内容：例 14.3-14.5 的苯胺加氢体系、控制器参数、扰动幅度不可迁移。
- 误用警戒：控制器调好不能证明动力学正确；动力学仍需 freeze gate。
- 未知路由：`../chapter_extracts/ch14_dynamic_simulation.md` -> `kinetics_expert_system.md`。

### CASE-DYN-04 | ch14 | DWC 动态控制结构

- 使用场景：隔壁塔稳态模型导出动态并建立压力、液位、流量、组成/温度控制。
- Aspen 路径或模块/卡片：DWC 稳态模型；Dynamics export；预分馏塔/主塔控制结构；液相分离比、温度或浓度控制器。
- 可迁移做法：先按 DWC 稳态案例确认内部连接和产品纯度，再建立动态压力液位流量基础控制，最后加温度/浓度控制。
- 不可迁移内容：例 14.8 的物性方法、组分、控制器位置、TC/CC 参数不可迁移。
- 误用警戒：DWC 动态比普通塔更敏感，不能把普通二产品塔控制结构直接套用。
- 未知路由：`../chapter_extracts/ch14_dynamic_simulation.md` -> `../chapter_extracts/ch10c_energy_saving_distillation_structures.md`。

## 11. 操作流程模板

### 11.1 复杂精馏建模模板

1. 判断分离困难来源：低相对挥发度、共沸、压力敏感共沸、液液分相、塔内反应、三产品高纯。
2. 回 `ch03` 确认物性方法、VLE/LLE/气相缔合/二元参数。
3. 建普通或简化基线塔，先收敛，不加复杂循环。
4. 按案例选择结构：ED、AD、PSD、RD、3P、3RD、DWC、多效、热泵、HIDiC。
5. 先无循环或弱耦合运行，再逐步闭合循环、热耦合、Design Spec。
6. 用 Sensitivity 缩变量范围，再用 Design Spec 或 Optimization 反求目标。
7. 用 Thermal/Hydraulic/NQ/Column Analysis 校核塔板数、进料板、回流比、热负荷和水力学。
8. 最终证据必须包括：产品指标、塔内曲线、能耗、收敛状态、硬门禁。

### 11.2 塔优化模板

1. 已收敛严格塔作为基线。
2. Thermal Analysis 看 S-H/T-H，先修进料板和进料热状态。
3. Hydraulic Analysis 或 Column Analysis 看 Actual flow 与 Hydraulic maximum。
4. NQ Curves 筛塔板数、进料板和热负荷平台。
5. Sensitivity 扫回流比、进料板、溶剂量、压缩比或热耦合量。
6. Design Spec 锁纯度/回收率/馏程点，Vary 选择输入变量。
7. Optimization 只在基础流程稳定、变量范围已缩小、约束已明确时启用；一旦满足这些条件，应优先把 Optimization 作为正式优化证据保留，而不是只停留在人工 sweep。
   若基础塔/反应器已有积分失败、物性方法缺口、Calculator/Design Spec
   旧值、或物理结果明显不合理，先诊断模型，不得用 Optimization 掩盖。
8. Optimization 必须保留 Aspen 对象和导出证据：目标函数、决策变量终值、
   上下限、活跃约束、残差/容差、失败点和同一 after-run 的下游指标。
9. 结果用经济性、能耗、可操作性和收敛风险一起判定，不只看单一纯度或热负荷。

### 11.3 节能技术模板

1. 先建常规塔基线并记录再沸器/冷凝器负荷。
2. 检查是否有可用温差、压力重构空间、三产品需求或塔顶热回收价值。
3. 选择结构：多效、DWC、热泵、HIDiC、换热网络改造。
4. 先弱耦合、无循环或辅助设备版本收敛。
5. 逐步提高热耦合强度、压缩比或内部连接精度。
6. 用 Sensitivity 评估能耗、温差、换热面积和收敛稳定性。
7. 电耗按项目采用的折算准则转成等量热负荷后再比较。
8. 使用 Activated Energy Analysis 时，必须先绑定 Utilities 并重新 Run。

### 11.4 反应器填卡模板

1. 先判定是否真的有动力学。只有转化率/收率时用非动力学反应器，不进 RCSTR/RPlug/RBatch 正式动力学。
2. 有速率式时，先冻结 reaction set：计量、模型家族、相态、基准、单位、参数。
3. PowerLaw 只能表达单一幂律；LHHW 保留推动力和吸附分母；无法表达则 USER 或阻断。
4. 再冻结反应器块：体积/停留时间/几何/压降/温度或传热/操作时间。
5. 把 reaction set 挂到块上，并导出/截图验证卡片。
6. 任何一步缺源值、缺单位、缺换算、缺字段解释时，标 `blocked` 或 `provisional`。

## 12. 最终交付证据清单

- 使用的案例卡 ID。
- 当前项目源文件依据。
- 物性方法与参数来源。
- Aspen 路径和字段。
- 哪些内容来自案例模式，哪些内容来自当前项目。
- 不可迁移例题参数是否已隔离。
- 运行状态、警告/错误、收敛历史或结果页证据。
- 对反应器：动力学 freeze ledger 状态。
- 对塔优化：产品指标、热负荷、水力学、NQ/Analysis 或经济性证据。
- 对节能：基线能耗、改造后能耗、电耗折算、Utilities/夹点/换热网络证据。

## 13. Project Overlay Case: CASE-COL-05

### CASE-COL-05 | special | 特殊体系跳过 DSTWU，直接从严格塔开始

- 使用场景：`DSTWU` 不能给出可靠快捷初值，或体系属于吸收/汽提、低温甲醇洗、低温溶剂吸收、萃取精馏、共沸精馏、VLL/三相、反应精馏、电解质/酸水汽提、石油假组分等。
- Aspen 路径或模块/卡片：`Blocks|RADFRAC|Specifications|Setup/Configuration`；`Streams`；`Pressure`；`Convergence`；`Design Specifications/Vary`；必要时 `Sensitivity`、`Column Analysis`、`NQ Curves`。
- 可迁移步骤：先记录 `DSTWU` 跳过原因；锁定物性方法、有效相态、塔压路径和分离目标；在独立塔岛文件 `<project>-<equipment>` 中直接建最小严格塔 `RIG-INIT`；收敛后新建 `RIG-FEED` 调整进料板或吸收剂入口；再新建 `RIG-SPEC` 加 Design Spec/Vary 锁定纯度、回收率、溶剂损失或再生指标；必要时用 Sensitivity/Column Analysis/NQ 缩小板数、回流比、溶剂量、再沸热负荷或压力范围；最终只把收敛且有证据的严格塔块回接全流程。
- 不可迁移内容：不能迁移例题或旧流程的板数、进料板、压力、溶剂比、回流比、再沸热负荷、Henry 参数、二元参数、Design Spec 目标值。
- 误用警戒：`DSTWU` 不适用不是允许使用 `SEP/SEP2/SEPARATOR` 的理由；特殊体系必须说明为什么快捷塔模型无效，并用严格塔相平衡、收敛和指标证据证明分离可行。每次优化必须新建塔块保留轨迹，不得覆盖旧塔。
- 详细节点：`special_columns_direct_radfrac.md`。

