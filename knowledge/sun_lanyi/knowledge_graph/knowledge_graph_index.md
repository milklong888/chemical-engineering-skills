# Aspen Plus Knowledge Graph Index

Source: `Aspen Plus-孙兰义.pdf` chapter extracts.

## Lookup Rules

1. Match the unknown situation to trigger words in the node list.
2. Open the source extract file shown in the `Source Extract` column.
3. For kinetics, open `kinetics_expert_system.md` and freeze parameters before Aspen card entry.
4. For every new or rebuilt module, create the property-method row first. This
   is required even when the method seems obvious; use chapter 3 nodes before
   unit operation selection, tower initialization, reactor cards, Design Specs,
   Calculators, Sensitivities, or Optimization.
5. For property-method uncertainty, keep the module `provisional` or `blocked`
   before tuning unit blocks.

## Nodes

| Node ID | Source Extract | Node Draft |
| --- | --- | --- |
| `K01-001` | `ch01_process_simulation_basics.md` | - K01-001 \| 化工过程模拟 \| 概念 \| 模拟、虚拟流程、再现、预测 \| 用计算机和数学模型描述真实工艺过程，核心是用变量和约束代替现场试错 \| P10-P11 |
| `K01-002` | `ch01_process_simulation_basics.md` | - K01-002 \| 适用场景 \| 场景 \| 方案比较、优化、诊断、改造、设计 \| 适用于研发、设计、改造、调优、诊断与经济评估 \| P11-P12 |
| `K01-003` | `ch01_process_simulation_basics.md` | - K01-003 \| 模拟边界 \| 约束 \| 不包含现场全部细节、不能替代实验 \| 模拟是工程推演工具，不是现场装置本体 \| P10-P12 |
| `K01-004` | `ch01_process_simulation_basics.md` | - K01-004 \| 物性数据库 \| 资源 \| 物性、热力学、传递性质、估算 \| 先保证组分与物性可得，物性方法决定结果可信度 \| P11-P12 |
| `K01-005` | `ch01_process_simulation_basics.md` | - K01-005 \| 单元操作模块 \| 资源 \| 塔、泵、换热器、反应器、分离 \| 用模块组合还原工艺流程，是流程计算主体 \| P11-P12 |
| `K01-006` | `ch01_process_simulation_basics.md` | - K01-006 \| 数据输入系统 \| 机制 \| 输入、命令、文件、图形界面 \| 支持图形和文件输入；复杂场景可用文件/命令提高效率 \| P11-P12 |
| `K01-007` | `ch01_process_simulation_basics.md` | - K01-007 \| 数据检查系统 \| 机制 \| 检查、校验、缺项、错误 \| 只检查完整性与合理性；发现问题应返回输入阶段修正 \| P10-P12 |
| `K01-008` | `ch01_process_simulation_basics.md` | - K01-008 \| 调度系统 \| 机制 \| 运行顺序、迭代、回路、收敛 \| 负责模块调用与求解推进；遇到回路需关注迭代策略 \| P11-P12 |
| `K01-009` | `ch01_process_simulation_basics.md` | - K01-009 \| 结果输出系统 \| 机制 \| 报告、导出、作图、查看结果 \| 将输入与计算结果保存成报表，支持后续分析 \| P11-P12 |
| `K01-010` | `ch01_process_simulation_basics.md` | - K01-010 \| 状态符号 \| 诊断标记 \| 未完成、已完成、错误、警告、可选、变更 \| 通过导航面板状态快速定位输入和计算问题 \| P14 |
| `K01-011` | `ch01_process_simulation_basics.md` | - K01-011 \| Next 按钮 \| 操作 \| 下一步、向导 \| 按向导推进输入流程，适合顺序建模 \| P14 |
| `K01-012` | `ch01_process_simulation_basics.md` | - K01-012 \| Run 按钮 \| 操作 \| 开始运行、计算 \| 输入完成后启动计算；运行前先过完整性检查 \| P14 |
| `K01-013` | `ch01_process_simulation_basics.md` | - K01-013 \| Reset 按钮 \| 操作 \| 初始化、重算 \| 放弃上次计算结果并重置初值 \| P14 |
| `K01-014` | `ch01_process_simulation_basics.md` | - K01-014 \| Reconcile Stream \| 操作 \| 流股协调、对齐输入 \| 用于让输入变量与计算结果一致 \| P14 |
| `K01-015` | `ch01_process_simulation_basics.md` | - K01-015 \| Navigation Pane \| 界面 \| 对象树、输入、结果 \| 通过层级树查看流程对象、输入项和结果项 \| P13-P14 |
| `K01-016` | `ch01_process_simulation_basics.md` | - K01-016 \| Control Panel \| 界面 \| 运行监控、控制 \| 用于查看运行过程并进行控制 \| P14 |
| `CH02-001` | `ch02_flowsheet_setup_basics.md` | - CH02-001 \| 新建模拟 \| 操作 \| File/New, Ctrl+N, Blank Simulation \| 新建时先选模板，空白模拟适合从零建模 \| 15-17 |
| `CH02-002` | `ch02_flowsheet_setup_basics.md` | - CH02-002 \| 文件保存策略 \| 规则 \| Save As, bkp, apwz, apw \| 建模前先保存，区分三种文件类型与用途 \| 17 |
| `CH02-003` | `ch02_flowsheet_setup_basics.md` | - CH02-003 \| 组分选择 \| 操作 \| Components, Selection, Find \| 识别不到时用 Find 按分子式/CAS 搜索纯组分库 \| 18-19 |
| `CH02-004` | `ch02_flowsheet_setup_basics.md` | - CH02-004 \| 组分 ID 限制 \| 规则 \| Component ID \| 组分标识最多 8 个字符 \| 19 |
| `CH02-005` | `ch02_flowsheet_setup_basics.md` | - CH02-005 \| 物性方法选择 \| 操作 \| Methods, Global, F4 \| 物性方法决定相平衡和性质计算精度 \| 19-20 |
| `CH02-006` | `ch02_flowsheet_setup_basics.md` | - CH02-006 \| RK-SOAVE \| 方法 \| RK-SOAVE, 烃, 轻气体 \| 适用于非极性或弱极性混合物，高温高压常用 \| 20, 28 |
| `CH02-007` | `ch02_flowsheet_setup_basics.md` | - CH02-007 \| 自动二元参数 \| 规则 \| binary parameters \| 部分模型会自动调用内置二元参数，EOS 需谨慎核对 \| 20, 32-33 |
| `CH02-008` | `ch02_flowsheet_setup_basics.md` | - CH02-008 \| 全局规定 \| 操作 \| Setup, Global, Title \| 在 Global 页面设置标题、单位、运行类型 \| 20 |
| `CH02-009` | `ch02_flowsheet_setup_basics.md` | - CH02-009 \| 模块选项板 \| 界面对象 \| Model Palette, F10, View \| 模块选项板用于放置单元操作图标 \| 21-22 |
| `CH02-010` | `ch02_flowsheet_setup_basics.md` | - CH02-010 \| 物流端口颜色 \| 规则 \| red port, blue port \| 红色是必选物流端口，蓝色是可选端口 \| 22 |
| `CH02-011` | `ch02_flowsheet_setup_basics.md` | - CH02-011 \| 重连物流 \| 操作 \| Reconnect Destination \| 物流连错时可重连到新模块 \| 23 |
| `CH02-012` | `ch02_flowsheet_setup_basics.md` | - CH02-012 \| 对象重命名 \| 操作 \| Rename Stream, Rename Block, Ctrl+M \| 物流和模块可按实际意义重命名 \| 23-24 |
| `CH02-013` | `ch02_flowsheet_setup_basics.md` | - CH02-013 \| 物流输入 \| 操作 \| Streams, Input, Mixed, Total flow, Composition \| 温度/压力/气相分率中通常给两个，再给流量或组成 \| 24-25 |
| `CH02-014` | `ch02_flowsheet_setup_basics.md` | - CH02-014 \| 压力语义 \| 规则 \| Pressure > 0 / <= 0 \| 正值是操作压力，非正值代表压降 \| 25 |
| `CH02-015` | `ch02_flowsheet_setup_basics.md` | - CH02-015 \| 反应器输入 \| 操作 \| Blocks, Setup, Reactions, Edit Stoichiometry \| 先设压力和 Duty，再定义反应式和转化率 \| 26 |
| `CH02-016` | `ch02_flowsheet_setup_basics.md` | - CH02-016 \| Required Input Complete \| 状态 \| Required Input Complete \| 关键输入完成后可运行模拟 \| 26-27 |
| `CH02-017` | `ch02_flowsheet_setup_basics.md` | - CH02-017 \| 运行入口 \| 操作 \| Run, F5, Reset \| 改动后先 Reset 再 Run，减少旧状态干扰 \| 27 |
| `CH02-018` | `ch02_flowsheet_setup_basics.md` | - CH02-018 \| 控制面板 \| 诊断 \| Control Panel, F7 \| 警告和错误集中显示 \| 27-28 |
| `CH02-019` | `ch02_flowsheet_setup_basics.md` | - CH02-019 \| 结果查看 \| 操作 \| Results Summary, Streams, Material, Stream Table \| 查看物流结果并可在流程图上显示表格 \| 28 |
| `CH02-020` | `ch02_flowsheet_setup_basics.md` | - CH02-020 \| 流程显示选项 \| 规则 \| File, Options, Flowsheet, Modify \| 可在显示选项中叠加温度、压力、汽化分率等 \| 28 |
| `CH3-PM-01` | `ch03_property_methods_and_regression.md` | - CH3-PM-01 \| 气相缔合判定 \| 规则节点 \| 羧酸, 气相缔合, 二聚, HOC, NTH \| 含羧酸/HF 等气相缔合体系必须同时判断气相模型, 低压二聚可用 NTH, 中压优先 HOC, HF 路线约束更严 \| PDF页39-42 |
| `CH3-PM-02` | `ch03_property_methods_and_regression.md` | - CH3-PM-02 \| 乙酸-水反例 \| 案例节点 \| 乙酸-水, 共沸, NRTL-HOC \| 不考虑羧酸气相缔合会误判 VLE, 若出现与常识冲突的共沸/相图, 应优先回查气相缔合模型 \| PDF页39-42 |
| `CH3-PM-03` | `ch03_property_methods_and_regression.md` | - CH3-PM-03 \| 石油体系方法分层 \| 规则节点 \| 石油, 天然气, 虚拟组分, BK10, GRAYSON, HYSPR \| 石油/天然气体系按压力和是否含轻气体/氢分层选法, 低压 K 值模型, 高压转石油调整 EOS \| PDF页42-44, 54 |
| `CH3-PM-04` | `ch03_property_methods_and_regression.md` | - CH3-PM-04 \| 高压烃 EOS \| 方法节点 \| PR-BM, RKS-BM, BWRS, 近临界, 超临界 \| 高压烃/轻气体/近临界体系优先 EOS, 若重视液体体积与焓可考虑 BWRS \| PDF页43-44 |
| `CH3-PM-05` | `ch03_property_methods_and_regression.md` | - CH3-PM-05 \| 预测型 EOS \| 方法节点 \| PSRK, PRWS, MHV2, Wong-Sandler, SR-POLAR \| 高压强非理想、极性/非极性共存、高压 LLE、超临界萃取优先预测型 EOS \| PDF页43-44 |
| `CH3-PM-06` | `ch03_property_methods_and_regression.md` | - CH3-PM-06 \| 活度系数法边界 \| 规则节点 \| NRTL, UNIQUAC, Wilson, UNIFAC, 中低压 \| 活度系数法适合中低压强非理想非电解质体系, Wilson 不能处理 LLE, NRTL/UNIQUAC 可处理部分互溶 \| PDF页44-46 |
| `CH3-PM-07` | `ch03_property_methods_and_regression.md` | - CH3-PM-07 \| Henry 组分 \| 规则节点 \| Henry, 轻气体, 超临界溶质, 微溶 \| 轻气体/超临界溶质在液相微溶时必须定义 Henry 组分, 否则溶解度可能严重失真 \| PDF页46-50 |
| `CH3-PM-08` | `ch03_property_methods_and_regression.md` | - CH3-PM-08 \| 电解质方法选择 \| 规则节点 \| ELECNRTL, PITZER, AMINES, APISOUR \| 电解质体系不可沿用普通非电解质模型, 优先识别专用包或 ELECNRTL/PITZER 路线 \| PDF页50-51, 54 |
| `CH3-PM-09` | `ch03_property_methods_and_regression.md` | - CH3-PM-09 \| 参数与数据区分 \| 概念节点 \| 参数, 数据, PLXANT, 二元参数 \| 参数是模型常数, 数据是估算/回归输入; 先明确缺的是参数还是数据 \| PDF页65-66 |
| `CH3-PM-10` | `ch03_property_methods_and_regression.md` | - CH3-PM-10 \| 二元参数来源管理 \| 规则节点 \| Binary Interaction, Databanks, PRKIJ, HOCETA \| 大多数 EOS/活度模型都依赖二元参数; 应核对参数页与数据库来源, 不能默认自动提取即可信 \| PDF页66, 101 |
| `CH3-PM-11` | `ch03_property_methods_and_regression.md` | - CH3-PM-11 \| PCES 纯组分估算 \| 工具节点 \| PCES, TB, MW, 结构 \| 纯组分估算至少依赖 TB/MW/结构, TB 是核心枢纽, 有实验 TB 时应优先输入 \| PDF页87-95 |
| `CH3-PM-12` | `ch03_property_methods_and_regression.md` | - CH3-PM-12 \| TB 估算方法分流 \| 规则节点 \| Joback, Gani, Ogata-Tsuchida, Mani \| 结构已知时优先更准确的 Gani/Ogata-Tsuchida, 有蒸气压数据时 Mani 更强 \| PDF页88-89 |
| `CH3-PM-13` | `ch03_property_methods_and_regression.md` | - CH3-PM-13 \| UNIFAC 与 GAMINF 估算 \| 规则节点 \| UNIFAC, UNIF-DMD, GAMINF, R-PCES \| 缺二元参数时可借无限稀释活度系数估算, 实验 GAMINF 最优, UNIF-DMD 在 UNIFAC 族中精度最高 \| PDF页95-101 |
| `CH3-PM-14` | `ch03_property_methods_and_regression.md` | - CH3-PM-14 \| NRTL alpha 经验值 \| 规则节点 \| cij, alpha, NRTL \| NRTL 的 alpha 默认 0.3 但需按体系调整, 烷烃+非缔合极性液体常用 0.2, 强缔合+非极性可用 0.47 \| PDF页95 |
| `CH3-PM-15` | `ch03_property_methods_and_regression.md` | - CH3-PM-15 \| 数据回归流程 \| 流程节点 \| Regression, TPXY, Residual, Consistency \| 回归后必须看参数、残差、平方和、作图和一致性检验, 不能只看是否收敛 \| PDF页101-112, 117-118 |
| `CH3-PM-16` | `ch03_property_methods_and_regression.md` | - CH3-PM-16 \| TDE 数据引入 \| 工具节点 \| TDE, NIST, 实验数据, 一致性检验 \| TDE 可导入实验数据并做一致性检验, 用于后续回归或参数核验 \| PDF页112-118 |
| `CH3-PM-17` | `ch03_property_methods_and_regression.md` | - CH3-PM-17 \| 参数清理与重置 \| 维护节点 \| Clean Parameters, Purge incomplete \| 在多轮估算/回归后可清理参数污染, 避免旧参数残留影响新判断 \| PDF页113-114 |
| `CH04-001` | `ch04_mixing_flash_sep_modules.md` | - CH04-001 \| Mixer \| 模块 \| 混合、把多股流合成一股 \| `Blocks\|MIXER\|Input\|Flash Options` \| 物流混合要指定出口压力/压降与有效相态；若都不填，出口压力取最低进料压力 \| p. 130 |
| `CH04-002` | `ch04_mixing_flash_sep_modules.md` | - CH04-002 \| Mixer-Pressure \| 规则 \| 出口压力 \| `Blocks\|MIXER\|Input\|Flash Options` \| 指定压降时按最低进料压力推算出口压力；不指定则出口压力取最低进料压力 \| p. 130 |
| `CH04-003` | `ch04_mixing_flash_sep_modules.md` | - CH04-003 \| FSplit \| 模块 \| 分流、分配、出口流量 \| `Blocks\|FSPLIT\|Input\|Specifications` \| 可按 split fraction 或 flow 指定已知出口；只能指定 N-1 股，剩余出口由守恒补齐 \| pp. 133-134 |
| `CH04-004` | `ch04_mixing_flash_sep_modules.md` | - CH04-004 \| FSplit-KeyComp \| 规则 \| 关键组分 \| `Blocks\|FSPLIT\|Input\|Key Components` \| 用组分流量闭合时要在 Key Components 页建立关键组分映射 \| p. 134 |
| `CH04-005` | `ch04_mixing_flash_sep_modules.md` | - CH04-005 \| Mult \| 模块 \| 倍增、缩放 \| `Blocks\|MULT\|Input\|Specifications` \| 物流缩放因子必须为正；能流/功流可正可负；不守恒 \| p. 135 |
| `CH04-006` | `ch04_mixing_flash_sep_modules.md` | - CH04-006 \| Dupl \| 模块 \| 复制、并行处理 \| `Blocks\|DUPL\|Input\|Properties` \| 无需参数，直接复制为多股完全相同的出口流 \| p. 136 |
| `CH04-007` | `ch04_mixing_flash_sep_modules.md` | - CH04-007 \| Flash2 \| 模块 \| 两出口闪蒸 \| `Blocks\|FLASH1/FLASH2\|Input\|Specifications` \| 温度、压力、气相分数、热负荷中选两个；不能同时定气相分数和热负荷 \| p. 138 |
| `CH04-008` | `ch04_mixing_flash_sep_modules.md` | - CH04-008 \| Flash2-Duty \| 规则 \| 热负荷 \| `Blocks\|FLASH2\|Input\|Specifications` \| 若只规定一个参数，模块用入口热流之和作为热负荷规定；否则用入口热流算净热负荷 \| p. 138 |
| `CH04-009` | `ch04_mixing_flash_sep_modules.md` | - CH04-009 \| Flash3 \| 模块 \| 三出口闪蒸 \| `Blocks\|FLASH3\|Input\|Specifications` \| 适合 V-L-L；二液相归属可由关键组分或密度规则判定 \| pp. 140-141 |
| `CH04-010` | `ch04_mixing_flash_sep_modules.md` | - CH04-010 \| Decanter \| 模块 \| 液液分相 \| `Blocks\|DECANTER\|Input\|Specifications` + `...\|Efficiency` \| 可设分离效率；默认 1；第二液相由关键组分或密度规则判定 \| pp. 142-143 |
| `CH04-011` | `ch04_mixing_flash_sep_modules.md` | - CH04-011 \| Sep \| 模块 \| 组分分离 \| `Blocks\|SEP\|Input\|Specifications` \| 按各组分分数或流量分到多股出口；可设进料闪蒸压力和有效相态 \| pp. 143-145 |
| `CH04-012` | `ch04_mixing_flash_sep_modules.md` | - CH04-012 \| Sep-FeedFlash \| 规则 \| 进料闪蒸 \| `Blocks\|SEP\|Input\|Feed Flash` \| `Pressure` 与 `Valid phase` 会影响分离前状态；缺省 `Valid phase=Vapor-Liquid` \| p. 144 |
| `CH04-013` | `ch04_mixing_flash_sep_modules.md` | - CH04-013 \| Sep2 \| 模块 \| 两出口组分分离 \| `Blocks\|SEP2\|Input\|...` \| 与 Sep 类似，但讲义明确提到支持更多输入选项，如纯度 \| p. 145 |
| `CH04-014` | `ch04_mixing_flash_sep_modules.md` | - CH04-014 \| Property-UNIQ \| 依赖 \| 活度系数法 \| `Methods\|Specifications\|Global` \| 液液分相、部分互溶体系、组分分离例题中常用 UNIQUAC \| pp. 140-145 |
| `CH04-015` | `ch04_mixing_flash_sep_modules.md` | - CH04-015 \| Property-SRK \| 依赖 \| 状态方程 \| `Methods\|Specifications\|Global` \| 高压体系例题建议用状态方程法，如 PENG-ROB \| p. 127 |
| `CH04-016` | `ch04_mixing_flash_sep_modules.md` | - CH04-016 \| Result-Streams \| 检查点 \| 结果查看 \| `Results\|Summary\|Streams\|Material` \| 重点核对温度、压力、气相分数、总流量、各组分流量 \| pp. 131-145 |
| `N5-01` | `ch05_pressure_modules.md` | - N5-01 \| 泵选型与升压 \| 决策节点 \| 泵、升压、液体、功率、Discharge pressure \| `Pressure Changers\|Pump\|ICON1` / `Blocks\|PUMP\|Setup\|Specifications` \| 液体升压优先泵；可用出口压力、压升、压比、功率或曲线求解 \| 158-162 |
| `N5-02` | `ch05_pressure_modules.md` | - N5-02 \| 泵效率填卡 \| 参数节点 \| Pump efficiency、Driver efficiency、轴功率 \| `Blocks\|PUMP\|Setup\|Specifications\|Efficiencies` \| 泵效率与驱动机效率分开填；结果要看有效功率、轴功率、电功率 \| 159-162 |
| `N5-03` | `ch05_pressure_modules.md` | - N5-03 \| 泵性能曲线 \| 数据节点 \| 特性曲线、Head vs flow、Vol-Flow \| `Blocks\|PUMP\|Performance Curves\|Curve Setup / Curve Data` \| 曲线格式用 Tabular data；流量变量用 Vol-Flow；按扬程-流量表录入 \| 160-162 |
| `N5-04` | `ch05_pressure_modules.md` | - N5-04 \| 压缩机选型 \| 决策节点 \| 压缩机、气体压缩、Polytropic、Isentropic、ASME \| `Pressure Changers\|Compr\|ICON2` / `Blocks\|COMPR\|Setup\|Specifications` \| 可做单相/两相/三相；ASME 比 GPSA 更严格，且不能用于涡轮机 \| 162-164 |
| `N5-05` | `ch05_pressure_modules.md` | - N5-05 \| 压缩机出口规定 \| 参数节点 \| Discharge pressure、pressure ratio、power \| `Blocks\|COMPR\|Setup\|Specifications\|Outlet specification` \| 压缩机可由出口压力、压升、压比、功率或曲线闭合 \| 162-164 |
| `N5-06` | `ch05_pressure_modules.md` | - N5-06 \| 压缩机效率与功率 \| 参数节点 \| Polytropic efficiency、Isentropic efficiency、Mechanical efficiency、loss power \| `Blocks\|COMPR\|Setup\|Specifications` / `Results\|Summary` \| 结果必须同时核对出口温度、体积流量、指示功率、轴功率、损失功率 \| 163-164 |
| `N5-07` | `ch05_pressure_modules.md` | - N5-07 \| 多级压缩配置 \| 决策节点 \| stages、cooler、final discharge pressure \| `Pressure Changers\|MCompr\|ICON1` / `Blocks\|MCOMPR\|Setup\|Configuration` \| 需要分级压缩和中间冷却时使用；可固定末级出口压力 \| 164-168 |
| `N5-08` | `ch05_pressure_modules.md` | - N5-08 \| 多级压缩冷却器 \| 参数节点 \| Duty、Outlet Temp、Pressure drop \| `Blocks\|MCOMPR\|Setup\|Cooler` \| 中间冷却器可设热负荷或出口温度，并可设压降；用于改善出口温度 \| 165-168 |
| `N5-09` | `ch05_pressure_modules.md` | - N5-09 \| 阀门节流与校核 \| 决策节点 \| Valve、开度、阀型、厂家、系列、尺寸 \| `Pressure Changers\|Valve\|VALVE` / `Blocks\|VALVE\|Input\|Operation / Valve Parameters` \| 阀门按绝热节流处理；校核需给出阀型、厂家、系列、尺寸、开度 \| 169-170 |
| `N5-10` | `ch05_pressure_modules.md` | - N5-10 \| 阀门出口压力计算 \| 参数节点 \| Calculate outlet pressure for specified valve (rating) \| `Blocks\|VALVE\|Input\|Operation` \| 已知阀门规格和开度时，按 rating 求出口压力 \| 169-170 |
| `N5-11` | `ch05_pressure_modules.md` | - N5-11 \| 管道压降计算 \| 决策节点 \| Pipe、Pipeline、Length、Diameter、Elevation、Roughness \| `Pressure Changers\|Pipe / Pipeline` \| 单段用 Pipe，多段异径或不同标高用 Pipeline \| 157, 170 |
| `HX-001` | `ch06_heat_exchanger_modules.md` | - HX-001 \| 换热器模块总览 \| 概念 \| 换热器、Heater、Cooler、HeatX、MHeatX、EDR \| `Exchangers` 模块库 \| 先分单股/两股/多股，再分简捷/详细/严格 \| p179-180 |
| `HX-002` | `ch06_heat_exchanger_modules.md` | - HX-002 \| Heater 单股状态调整 \| 操作规则 \| Heater、Cooler、冷凝器、泡点、露点 \| `Blocks\|...\|Input\|Specifications` \| 可用热负荷、出口温度、气相分数、温度改变等规定 \| p180-182 |
| `HX-003` | `ch06_heat_exchanger_modules.md` | - HX-003 \| Pressure 字段解释 \| 字段规则 \| Pressure、压降、绝压 \| `Blocks\|...\|Input\|Specifications\|Pressure` \| >0 表示出口绝压，≤0 表示相对进口压降 \| p182 |
| `HX-004` | `ch06_heat_exchanger_modules.md` | - HX-004 \| HeatX 简捷法 \| 方法 \| Shortcut、Constant U value \| `Blocks\|HEX\|Setup\|Specifications`、`Setup\|U Methods` \| 适合初算，不要依赖结构参数 \| p189-193 |
| `HX-005` | `ch06_heat_exchanger_modules.md` | - HX-005 \| HeatX 详细法 \| 方法 \| Detailed、Film coefficients、Geometry \| `Blocks\|HEX\|Setup\|...`、`Geometry\|...` \| 需几何与膜系数，不能直接用于设计模式 \| p198-203 |
| `HX-006` | `ch06_heat_exchanger_modules.md` | - HX-006 \| HeatX 严格法 \| 方法 \| Rigorous、EDR、Shell&Tube、AirCooled、Plate \| `Blocks\|HEX\|EDR Options\|Input file` \| 通过 EDR 求严格设计/校核/模拟 \| p189-203 |
| `HX-007` | `ch06_heat_exchanger_modules.md` | - HX-007 \| EDR 设计参数 \| 字段 \| Fouling factor、Maximum delta-P、Layout type、Shell ID \| `Blocks\|HEX\|EDR Browser\|Geometry`、`EDR Options\|Analysis Parameter` \| 严格设计依赖结构与允许压降 \| p196-203 |
| `HX-008` | `ch06_heat_exchanger_modules.md` | - HX-008 \| EDR 结果检查 \| 结果 \| Exchanger Details、Delta P、面积余量 \| `Thermal Results\|Exchanger Details`、`EDR Shell&Tube Results\|Delta P` \| 同时看面积、U、压降和余量 \| p201-203 |
| `HX-009` | `ch06_heat_exchanger_modules.md` | - HX-009 \| MHeatX 多股换热 \| 模块 \| MHeatX、LNG、总能量衡算 \| `Blocks\|CBOX\|Input\|Specifications` \| 不算几何；未规定出口的物流共用出口温度 \| p193-195 |
| `HX-010` | `ch06_heat_exchanger_modules.md` | - HX-010 \| 公用工程 \| 辅助资源 \| Utilities、steam、cooling water \| `Utilities\|...` \| 可用于费用、用量和冷热公用工程匹配 \| p179, p184, p189 |
| `CH07-N01` | `ch07_column_shortcut_and_absorption.md` | - CH07-N01 \| 简捷初设 \| Concept \| 简捷、DISTL、初值、板数、回流比 \| 简捷模块输出理论板数/回流比/进料位置，作为 RadFrac 初值 \| p214-216 |
| `CH07-N02` | `ch07_column_shortcut_and_absorption.md` | - CH07-N02 \| RadFrac 严格塔 \| Module \| RadFrac、严格计算、精馏、吸收、汽提、萃取精馏、共沸精馏 \| Blocks/RadFrac \| 精算主模块，适用多类塔过程 \| p214-215 |
| `CH07-N03` | `ch07_column_shortcut_and_absorption.md` | - CH07-N03 \| 平衡级模式 \| Setting \| Equilibrium、平衡级 \| Blocks/RADFRAC/Specifications/Setup/Configuration/Calculation type \| 每块理论级汽液相假定达到平衡 \| p216 |
| `CH07-N04` | `ch07_column_shortcut_and_absorption.md` | - CH07-N04 \| 级数定义 \| Rule \| Number of stages、理论板数、实际板数 \| Blocks/RADFRAC/Specifications/Setup/Configuration/Number of stages \| 板数包含冷凝器和再沸器；若输入实际板数需效率 \| p216 |
| `CH07-N05` | `ch07_column_shortcut_and_absorption.md` | - CH07-N05 \| 冷凝器类型 \| Setting \| Total、Partial、None \| Blocks/RADFRAC/Specifications/Setup/Configuration/Condenser \| 按塔顶是否只要液相、是否需要部分冷凝选择 \| p216 |
| `CH07-N06` | `ch07_column_shortcut_and_absorption.md` | - CH07-N06 \| 再沸器类型 \| Setting \| Kettle、Thermosiphon、None \| Blocks/RADFRAC/Specifications/Setup/Configuration/Reboiler \| 按塔底物料状态与返塔汽相平衡关系选择 \| p216-217 |
| `CH07-N07` | `ch07_column_shortcut_and_absorption.md` | - CH07-N07 \| 热虹吸再沸器 \| Rule \| Thermosiphon、Specify both flow and outlet condition、vapour fraction 5%~35% \| Blocks/RADFRAC/Specifications/Setup/Reboiler \| 低于5%循环不足，高于35%应转 Kettle \| p217 |
| `CH07-N08` | `ch07_column_shortcut_and_absorption.md` | - CH07-N08 \| 相态设置 \| Rule \| Vapor-Liquid、FreeWater、DirtyWater \| Blocks/RADFRAC/Specifications/Setup/Configuration/Phases \| 仅在有自由水/污水相/三相需要时启用扩展相态 \| p217-218 |
| `CH07-N09` | `ch07_column_shortcut_and_absorption.md` | - CH07-N09 \| 收敛方法 \| Setting \| Standard、Petroleum/Wide-boiling、Strongly non-ideal liquid、Azeotropic、Cryogenic、Custom \| Blocks/RADFRAC/Specifications/Setup/Configuration/Convergence method \| 体系不同，收敛方法不同；乙苯-苯乙烯例用 Standard \| p218 |
| `CH07-N10` | `ch07_column_shortcut_and_absorption.md` | - CH07-N10 \| 操作规定 \| Rule \| Reflux ratio、Distillate rate、Bottoms to feed ratio、Condenser duty \| Blocks/RADFRAC/Specifications/Setup/Operating specifications \| 常优先回流比+塔顶产品/进料比，或塔顶产品流量 \| p218-222 |
| `CH07-N11` | `ch07_column_shortcut_and_absorption.md` | - CH07-N11 \| 进料方式 \| Rule \| Above-Stage、On-Stage、Vapor on stage、Liquid on stage \| Blocks/RADFRAC/Specifications/Setup/Streams \| 单相进料、避免闪蒸或校核效率时可用 on-stage/vapor-liquid on stage \| p218-219 |
| `CH07-N12` | `ch07_column_shortcut_and_absorption.md` | - CH07-N12 \| 压力定义 \| Rule \| Top/Bottom、Pressure profile、Section pressure drop \| Blocks/RADFRAC/Specifications/Setup/Pressure \| 至少给出第一块板压力，必要时补压降 \| p219-220 |
| `CH07-N13` | `ch07_column_shortcut_and_absorption.md` | - CH07-N13 \| 设计规定 \| Rule \| Design Spec、Vary、Mass purity、Distillate to feed ratio \| Blocks/RADFRAC/Design Specifications / Vary \| 一个设计规定配一个调节变量，优先流量类变量 \| p220-223 |
| `CH07-N14` | `ch07_column_shortcut_and_absorption.md` | - CH07-N14 \| 温度/组成曲线 \| Result \| Temperature、Composition、TPFQ、Plot \| Blocks/RADFRAC/Profiles/TPFQ \| 用于判断塔内分布和是否存在异常波动 \| p223-224 |
| `CH07-N15` | `ch07_column_shortcut_and_absorption.md` | - CH07-N15 \| 塔板校核 \| Rating \| Tray Rating、Maximum flooding factor、backup/tray spacing \| Blocks/RADFRAC/Sizing and Rating/Tray Rating \| 液泛因子一般 <0.8，backup/spacing 常看 0.2~0.5 \| p226-227 |
| `CH07-N16` | `ch07_column_shortcut_and_absorption.md` | - CH07-N16 \| 填料设计 \| Rating \| Pack Sizing、Fractional approach to maximum capacity、Pdrop \| Blocks/RADFRAC/Sizing and Rating/Pack Sizing \| 按液泛分率和压降控制设计塔径 \| p228-230 |
| `CH07-N17` | `ch07_column_shortcut_and_absorption.md` | - CH07-N17 \| 吸收塔 \| Module \| ABSORBER、Henry component、Sum-Rate、Absorber option \| Blocks/ABSORBER \| 稀溶液吸收常需 Henry 组分与合适收敛设置 \| p231-233 |
| `CH07-N18` | `ch07_column_shortcut_and_absorption.md` | - CH07-N18 \| Extract \| Module \| Extract、Key Components、LLE、Adiabatic \| Blocks/EXTRACT \| 两液相萃取，关键组分决定相流向与分配 \| p240-243 |
| `CH07-N19` | `ch07_column_shortcut_and_absorption.md` | - CH07-N19 \| 电解质汽提 \| Module \| ELECNRTL、电解质向导、Sour stripper \| Components/Specifications/Selection; Electrolyte Wizard; RadFrac \| 酸性水汽提必须按电解质体系建模 \| p244 |
| `N08A-01` | `ch08a_nonkinetic_reactors.md` | - N08A-01 \| 模块选择总入口 \| 决策节点 \| 触发词：反应器选型、动力学未知、平衡、产率、转化率 \| Aspen路径：`Reactors\|RStoic / RYield / REquil / RGibbs` \| 先判定“计量已知/产率已知/平衡已知/仅组分集合已知” \| 来源页码：PDF p252, p257, p259, p261 |
| `N08A-02` | `ch08a_nonkinetic_reactors.md` | - N08A-02 \| RStoic 计量反应器 \| 功能节点 \| 触发词：转化率、计量式、选择性、反应热 \| Aspen路径：`Blocks\|RSTOIC\|Setup\|Reactions` \| 适合动力学未知但计量已知；可算热负荷与选择性 \| 来源页码：PDF p252-p253 |
| `N08A-03` | `ch08a_nonkinetic_reactors.md` | - N08A-03 \| RStoic 选择性设置 \| 参数节点 \| 触发词：selectivity、并联反应、参考反应组分 \| Aspen路径：`Blocks\|RSTOIC\|Setup\|Selectivity` \| 选择性是“产物组分对参考组分”的约束，不是速率方程 \| 来源页码：PDF p252-p253 |
| `N08A-04` | `ch08a_nonkinetic_reactors.md` | - N08A-04 \| RStoic 反应热 \| 参数节点 \| 触发词：heat of reaction、热负荷、参考基准 \| Aspen路径：`Blocks\|RSTOIC\|Setup\|Heat of Reaction` \| 参考基准默认 25 C、1 atm、气相；热负荷会随定义变化 \| 来源页码：PDF p252-p253 |
| `N08A-05` | `ch08a_nonkinetic_reactors.md` | - N08A-05 \| RYield 产率分布 \| 功能节点 \| 触发词：yield、产品分布、固定产率 \| Aspen路径：`Blocks\|RYIELD\|Setup\|Yield` \| 产率是固定分布，不是动力学；默认 `Component yields` \| 来源页码：PDF p257-p259 |
| `N08A-06` | `ch08a_nonkinetic_reactors.md` | - N08A-06 \| RYield 组件映射 \| 参数节点 \| 触发词：mapping、lump、delump \| Aspen路径：`Blocks\|RYIELD\|Setup\|Comp.Mapping` \| lump/de-lump 体系必须映射清楚，否则产率失真 \| 来源页码：PDF p257-p259 |
| `N08A-07` | `ch08a_nonkinetic_reactors.md` | - N08A-07 \| REquil 平衡反应器 \| 功能节点 \| 触发词：equilibrium、平衡常数、温差、摩尔程度 \| Aspen路径：`Blocks\|REQUIL\|Input\|Specifications`、`Blocks\|REQUIL\|Input\|Reactions` \| 只做单相/两相；可用 extent 或 temperature approach 限制平衡 \| 来源页码：PDF p259-p261 |
| `N08A-08` | `ch08a_nonkinetic_reactors.md` | - N08A-08 \| REquil 固体处理 \| 边界节点 \| 触发词：solid、纯固相、惰性固体 \| Aspen路径：`Blocks\|REQUIL\|Input\|Reactions` \| 每个参与反应的常规固体视为单独纯固相；非反应固体只影响能量平衡 \| 来源页码：PDF p259-p261 |
| `N08A-09` | `ch08a_nonkinetic_reactors.md` | - N08A-09 \| RGibbs 自由能最小化 \| 功能节点 \| 触发词：Gibbs、无需反应式、热力学极限 \| Aspen路径：`Blocks\|RGIBBS\|Setup\|Specifications` \| 不写反应式，按最小 Gibbs 自由能求平衡 \| 来源页码：PDF p261-p263 |
| `N08A-10` | `ch08a_nonkinetic_reactors.md` | - N08A-10 \| RGibbs 产品集与相分配 \| 参数节点 \| 触发词：products、assign streams、相态 \| Aspen路径：`Blocks\|RGIBBS\|Input\|Products`、`Blocks\|RGIBBS\|Input\|Assign Streams` \| 默认把所有组分当产品并自动分配出口相 \| 来源页码：PDF p261-p263 |
| `N08A-11` | `ch08a_nonkinetic_reactors.md` | - N08A-11 \| 结果审查 \| 结果节点 \| 触发词：stream results、summary、heat load \| Aspen路径：`Blocks\|*/Stream Results\|Material`、`Blocks\|*/Results\|Summary` \| 先看物料分布，再看热负荷，最后核对相态与警告 \| 来源页码：PDF p253, p259, p263 |
| `CH08B-RXN-OBJ` | `ch08b_reactions_kinetics_cards.md` | - CH08B-RXN-OBJ \| Reactions 对象 \| Aspen对象 \| Reactions, reaction set, R-1 \| `Reactions \| Reactions` \| 反应对象独立于反应器/塔模块，可被 RadFrac、RBatch、RCSTR、RPlug、Pressure Relief 等引用；创建对象后还要在 block 中选入 reaction set \| PDF p263 / reaction_kinetics-263.png |
| `CH08B-RXN-CREATE` | `ch08b_reactions_kinetics_cards.md` | - CH08B-RXN-CREATE \| 创建反应对象 \| 操作步骤 \| New, Create New ID, Select Type \| `Reactions \| Reactions \| New...` \| 输入反应 ID，选择 POWERLAW/LHHW/USER 等类型，进入 `R-1` 后继续定义反应式 \| PDF p263 / reaction_kinetics-263.png |
| `CH08B-STOICH` | `ch08b_reactions_kinetics_cards.md` | - CH08B-STOICH \| Stoichiometry 页 \| Aspen卡片 \| Stoichiometry, Edit Reaction, Reaction type \| `Reactions \| R-1 \| Input \| Stoichiometry` \| 每条反应必须定义 Reactants、Products、Coefficient；Reaction type 为 Kinetic 或 Equilibrium \| PDF p263-p264 / reaction_kinetics-264.png |
| `CH08B-POWERLAW-EXP` | `ch08b_reactions_kinetics_cards.md` | - CH08B-POWERLAW-EXP \| PowerLaw 指数 \| 字段规则 \| Exponent, POWERLAW \| `Edit Reaction \| Reactants/Products \| Exponent` \| POWERLAW 需输入速率方程中每个组分指数；未输入默认为 0，表示速率与该组分无关 \| PDF p263-p264 / reaction_kinetics-263.png, reaction_kinetics-264.png |
| `CH08B-KINETIC-GEN` | `ch08b_reactions_kinetics_cards.md` | - CH08B-KINETIC-GEN \| Kinetic 通用页 \| Aspen卡片 \| Kinetic, Reacting phase, Rate basis \| `Reactions \| R-1 \| Input \| Kinetic` \| Kinetic 反应必须规定反应相态、速率控制基准、动力学参数和浓度基准 \| PDF p264 / reaction_kinetics-264.png |
| `CH08B-KINETIC-UNITS` | `ch08b_reactions_kinetics_cards.md` | - CH08B-KINETIC-UNITS \| 动力学单位链 \| 硬门禁 \| Units, k, E, To, [Ci] basis \| `Kinetic \| Units / k / n / E / To / [Ci] basis` \| 源方程/源数值 -> 源单位 -> 换算 -> Aspen 卡片单位 -> 精确输入 -> 导出验证；缺一环不得正式填卡 \| PDF p264-p265 / reaction_kinetics-264.png, reaction_kinetics-265.png |
| `CH08B-POWERLAW-K` | `ch08b_reactions_kinetics_cards.md` | - CH08B-POWERLAW-K \| PowerLaw Kinetic factor \| 字段规则 \| k, n, E, To \| `Kinetic \| Power Law kinetic expression` \| Aspen 图示区分指定 To 与不指定 To 的温度函数；k、n、E、To 必须与源式和卡片单位一致 \| PDF p264 / reaction_kinetics-264.png |
| `CH08B-LHHW-MAIN` | `ch08b_reactions_kinetics_cards.md` | - CH08B-LHHW-MAIN \| LHHW 主表达式 \| 模型结构 \| LHHW, kinetic factor, driving force, adsorption \| `Kinetic \| LHHW kinetic expression` \| LHHW 速率为动力学因子乘推动力再除以吸附表达式；讲义注明 LHHW 不适用于反应精馏系统 \| PDF p263-p265 / reaction_kinetics-263.png, reaction_kinetics-265.png |
| `CH08B-LHHW-DF` | `ch08b_reactions_kinetics_cards.md` | - CH08B-LHHW-DF \| LHHW Driving Force \| 子卡片 \| Driving Force, Term 1, Term 2 \| `Kinetic \| Driving Force` \| Term 1 与 Term 2 分别代表正反应和逆反应推动力；常数满足 `ln K = A + B/T + C lnT + D T` \| PDF p264-p265 / reaction_kinetics-264.png, reaction_kinetics-265.png |
| `CH08B-LHHW-ADS` | `ch08b_reactions_kinetics_cards.md` | - CH08B-LHHW-ADS \| LHHW Adsorption \| 子卡片 \| Adsorption, m, A/B/C/D \| `Kinetic \| Adsorption` \| 输入吸附表达式指数 m、组分浓度指数和吸附常数 A/B/C/D；无吸附影响时才可令 m=0 \| PDF p265 / reaction_kinetics-265.png |
| `CH08B-EQ` | `ch08b_reactions_kinetics_cards.md` | - CH08B-EQ \| Equilibrium 页 \| Aspen卡片 \| Equilibrium, Gibbs energies, Built-in Keq expression \| `Reactions \| R-1 \| Input \| Equilibrium` \| 平衡型反应需规定反应相态、平衡温差，并选择 Gibbs energies 或 Built-in Keq expression \| PDF p265 / reaction_kinetics-265.png |
| `CH08B-USER` | `ch08b_reactions_kinetics_cards.md` | - CH08B-USER \| USER 动力学 \| 自定义模型 \| USER, Subroutine, Fortran \| `Create New ID \| USER`; `Subroutine` \| 用用户提供的 Fortran 子程序计算反应速率；必须规定子程序名称和相关参数 \| PDF p263,p265 / reaction_kinetics-263.png, reaction_kinetics-265.png |
| `CH08B-BLOCK-SELECT` | `ch08b_reactions_kinetics_cards.md` | - CH08B-BLOCK-SELECT \| 反应对象挂接到模块 \| 操作门禁 \| Available reaction sets, Selected reaction sets \| `Blocks \| <block> \| Setup \| Reactions` \| reaction set 必须从 Available 选入 Selected，才会被具体反应器或模块使用 \| PDF p272 文本例证，关联第 8.6 节对象边界 |
| `CH08C-RCSTR-001` | `ch08c_rcstr_cards.md` | - CH08C-RCSTR-001 \| RCSTR模块适用边界 \| module \| 全混釜,完全混合,连续搅拌釜 \| Blocks\|RCSTR \| 可模拟1-3相、可处理平衡/动力学/含固体体系，釜内状态等于出口状态 \| p266 |
| `CH08C-RCSTR-002` | `ch08c_rcstr_cards.md` | - CH08C-RCSTR-002 \| RCSTR主规格页 \| page \| Specifications,操作条件,有效相态 \| Blocks\|RCSTR\|Setup\|Specifications \| 必填压力；温度/热负荷二选一；体积/停留时间二选一；必须设Valid phases \| p266-p268 |
| `CH08C-RCSTR-003` | `ch08c_rcstr_cards.md` | - CH08C-RCSTR-003 \| 有效相态字段 \| field \| Valid phases,Liquid-Only,Vapor-Only \| Blocks\|RCSTR\|Setup\|Specifications\|Valid phases \| 决定RCSTR在哪些相中求解，需与真实反应承载相一致 \| p266,p268 |
| `CH08C-RCSTR-004` | `ch08c_rcstr_cards.md` | - CH08C-RCSTR-004 \| 体积输入字段 \| field \| Reactor Volume,体积 \| Blocks\|RCSTR\|Setup\|Specifications\|Reactor Volume \| 已知设备体积时直接填；停留时间由流量和相态反算 \| p266-p268 |
| `CH08C-RCSTR-005` | `ch08c_rcstr_cards.md` | - CH08C-RCSTR-005 \| 停留时间规则 \| rule \| Residence Time,停留时间 \| Blocks\|RCSTR\|Setup\|Specifications \| 总停留时间与分相停留时间按式(8-6)、式(8-7)处理，出口总摩尔流量参与计算 \| p266-p267 |
| `CH08C-RCSTR-006` | `ch08c_rcstr_cards.md` | - CH08C-RCSTR-006 \| 多出口相态分配 \| page \| Streams页面,两股出口,三股出口 \| Blocks\|RCSTR\|Setup\|Streams \| 两出口或三出口时必须逐股指定出口相态；Valid phases不能替代该页 \| p266 |
| `CH08C-RCSTR-007` | `ch08c_rcstr_cards.md` | - CH08C-RCSTR-007 \| 反应对象创建入口 \| page \| Reactions,New,反应集 \| Reactions\|Reactions \| 反应对象独立于RCSTR存在，先创建后挂接 \| p263,p268 |
| `CH08C-RCSTR-008` | `ch08c_rcstr_cards.md` | - CH08C-RCSTR-008 \| 反应计量页 \| page \| Stoichiometry,Reaction type \| Reactions\|R-1\|Input\|Stoichiometry \| 在这里录反应式，并给每条反应指定Equilibrium或其他类型 \| p268 |
| `CH08C-RCSTR-009` | `ch08c_rcstr_cards.md` | - CH08C-RCSTR-009 \| 平衡参数页 \| page \| Equilibrium,Reacting phase,Keq \| Reactions\|R-1\|Input\|Equilibrium \| 平衡反应需填反应相态、平衡温差、Keq方法、Keq基准与参数 \| p265,p268 |
| `CH08C-RCSTR-010` | `ch08c_rcstr_cards.md` | - CH08C-RCSTR-010 \| RCSTR反应挂接页 \| page \| Available reaction sets,Selected reaction sets \| Blocks\|RCSTR\|Setup\|Reactions \| 真正让RCSTR调用反应对象的动作是把反应集移入Selected \| p268 |
| `CH08C-RCSTR-011` | `ch08c_rcstr_cards.md` | - CH08C-RCSTR-011 \| 温度已知流程 \| operation \| 指定温度,热负荷结果 \| Blocks\|RCSTR\|Setup\|Specifications \| 题目给温度时直接填温度，热负荷转到结果页核查 \| p266,p268 |
| `CH08C-RCSTR-012` | `ch08c_rcstr_cards.md` | - CH08C-RCSTR-012 \| 热负荷已知流程 \| operation \| 指定热负荷,求温度 \| Blocks\|RCSTR\|Setup\|Specifications \| 书中明确温度/热负荷二选一，但本段未给热负荷算例，不得臆造附加字段规则 \| p266 |
| `CH08C-RCSTR-013` | `ch08c_rcstr_cards.md` | - CH08C-RCSTR-013 \| 动力学硬门禁 \| gate \| k,E,单位,浓度基准,相态 \| Reactions\|...\|Input\|Kinetic \| 速率式来源、单位换算、Aspen卡值必须闭环；不得把例题参数当通用值 \| p263,p266-p269; ch08b硬门禁 |
| `CH08C-RCSTR-014` | `ch08c_rcstr_cards.md` | - CH08C-RCSTR-014 \| 例8.5流程模板 \| example \| 乙醇,乙酸,酯化,RCSTR \| Streams\|FEED / Blocks\|RCSTR / Reactions\|R-1 \| 可迁移的是操作顺序，不可迁移的是数值本身 \| p267-p269 |
| `CH08D-RPLUG-001` | `ch08d_rplug_cards.md` | - CH08D-RPLUG-001 \| RPlug适用边界 \| rule \| RPlug, 平推流, 动力学已知 \| Blocks\|RPLUG \| 仅在已知动力学、按轴向积分时使用；未知动力学不得硬填 \| PDF p269, p251-p252 |
| `CH08D-RPLUG-002` | `ch08d_rplug_cards.md` | - CH08D-RPLUG-002 \| RPlug反应器类型 \| parameter \| Reactor type, 指定温度, 绝热, 热媒 \| Blocks\|RPLUG\|Setup\|Specifications \| reactor type 由温度/传热边界决定，不由“习惯”决定 \| PDF p269-p271, rplug_powerlaw-271.png |
| `CH08D-RPLUG-003` | `ch08d_rplug_cards.md` | - CH08D-RPLUG-003 \| 指定温度Profile \| parameter \| Temperature profile, Location, Temperature \| Blocks\|RPLUG\|Setup\|Specifications \| 已知轴向温度点时可用 profile；例8.6 点位为 0/0.9/1 \| PDF p270-p271, 图8-45, rplug_powerlaw-271.png |
| `CH08D-RPLUG-004` | `ch08d_rplug_cards.md` | - CH08D-RPLUG-004 \| 几何参数 \| parameter \| Length, Diameter, 多管, 变径 \| Blocks\|RPLUG\|Setup\|Configuration \| 长度、直径必填；多管和变径只在设备信息已知时启用 \| PDF p269-p271, 图8-46, rplug_powerlaw-271.png |
| `CH08D-RPLUG-005` | `ch08d_rplug_cards.md` | - CH08D-RPLUG-005 \| 压降边界 \| parameter \| pressure drop, 压降 \| Blocks\|RPLUG\|相关压降页字段待界面核对 \| 教材明确要求填压降；例8.6 题干给压降=0，但指定页未展开字段路径，不可脑补 \| PDF p269-p270 |
| `CH08D-RPLUG-006` | `ch08d_rplug_cards.md` | - CH08D-RPLUG-006 \| 反应对象先定义后挂接 \| workflow \| Reactions, reaction set, Selected reaction sets \| Reactions\|Reactions; Blocks\|RPLUG\|Setup\|Reactions \| 先在 Reactions 定义对象，再挂到块上 \| PDF p263-p264, p272 |
| `CH08D-RPLUG-007` | `ch08d_rplug_cards.md` | - CH08D-RPLUG-007 \| PowerLaw建模入口 \| workflow \| POWERLAW, Kinetic \| Reactions\|Reactions; Reactions\|R-1\|Input\|Stoichiometry/Kinetic \| PowerLaw 的速率参数不在块卡片中，而在反应对象 Kinetic 页 \| PDF p263-p264, p271 |
| `CH08D-RPLUG-008` | `ch08d_rplug_cards.md` | - CH08D-RPLUG-008 \| 反应1动力学参数 \| parameter \| ENG, Vapor, k, E, Molarity \| Reactions\|R-1\|Input\|Kinetic \| 反应1：Units=ENG，phase=Vapor，k=90.46，E=6860，[Ci]basis=Molarity \| PDF p270-p271, 图8-48, rplug_powerlaw-271.png |
| `CH08D-RPLUG-009` | `ch08d_rplug_cards.md` | - CH08D-RPLUG-009 \| 反应2动力学参数 \| parameter \| 1.5e6, 27200, Molarity \| Reactions\|R-1\|Input\|Kinetic \| 反应2同页切换填写；k=1.5×10^6，E=27200，phase/basis 与题意一致 \| PDF p270-p272 |
| `CH08D-RPLUG-010` | `ch08d_rplug_cards.md` | - CH08D-RPLUG-010 \| PowerLaw指数填写 \| parameter \| Exponent, [Cl2], [C3H6] \| Reactions\|R-1\|Input\|Stoichiometry \| 速率式中出现的反应物指数按式填写；本例 Cl2、C3H6 均为 1 \| PDF p263-p264, p271, 图8-47 |
| `CH08D-RPLUG-011` | `ch08d_rplug_cards.md` | - CH08D-RPLUG-011 \| 组合模型处理非理想流型 \| pattern \| Flash2, Fsplit, Mixer, RCSTR串联 \| Flowsheet-level combination \| 多相、滞留、旁通、返混应通过模块组合处理，而非单 RPlug 硬拟合 \| PDF p272-p273 |
| `CH08E-RBATCH-001` | `ch08e_rbatch_cards.md` | - CH08E-RBATCH-001 \| RBatch适用边界 \| 规则 \| 间歇反应器/半间歇反应器/RBatch适用 \| Blocks > RBATCH \| 仅用于间歇或半间歇操作，且只能处理动力学反应 \| PDF p273, p276; 渲染图 rbatch_powerlaw-276.png |
| `CH08E-RBATCH-002` | `ch08e_rbatch_cards.md` | - CH08E-RBATCH-002 \| 稳态物流连接规则 \| 规则 \| 储罐连接/稳态物流/半间歇连接 \| Flowsheet + Streams > Input > Specifications \| 用储罐概念连接周期操作与稳态物流；区分间歇进料、连续进料、连续出料 \| PDF p273; 渲染图 rbatch_powerlaw-276.png |
| `CH08E-RBATCH-003` | `ch08e_rbatch_cards.md` | - CH08E-RBATCH-003 \| 反应器操作方式 \| 参数卡 \| Constant temperature/恒温操作 \| Blocks > RBATCH > Setup > Specifications > Reactor operating specification \| 操作模式先选，再填对应操作温度 \| PDF p276; 渲染图 rbatch_powerlaw-276.png |
| `CH08E-RBATCH-004` | `ch08e_rbatch_cards.md` | - CH08E-RBATCH-004 \| 反应器压力字段 \| 参数卡 \| Reactor pressure/反应器压力 \| Blocks > RBATCH > Setup > Specifications > Reactor pressure \| 块页压力是反应器操作压力，不能用进料压力替代 \| PDF p276; 渲染图 rbatch_powerlaw-276.png |
| `CH08E-RBATCH-005` | `ch08e_rbatch_cards.md` | - CH08E-RBATCH-005 \| PowerLaw反应集创建 \| 参数卡 \| POWERLAW/Reactions/R-1 \| Reactions > Reactions; Reactions > R-1 > Input > Stoichiometry \| 先建反应集，再逐条定义反应式、计量系数和指数 \| PDF p264, p276; 渲染图 rbatch_powerlaw-276.png |
| `CH08E-RBATCH-006` | `ch08e_rbatch_cards.md` | - CH08E-RBATCH-006 \| PowerLaw指数规则 \| 规则 \| Exponent/动力学指数/一阶 \| Reactions > R-1 > Input > Stoichiometry \| PowerLaw 下各组分指数必须核实；不填默认 0 只代表软件默认，不代表工程可用 \| PDF p264 |
| `CH08E-RBATCH-007` | `ch08e_rbatch_cards.md` | - CH08E-RBATCH-007 \| Kinetic参数页 \| 参数卡 \| Reacting phase/k/E/[Ci] basis/Molarity \| Reactions > R-1 > Input > Kinetic \| 至少确认反应相态、k、E、浓度基准；本例为 Liquid + Molarity \| PDF p277; 渲染图 rbatch_powerlaw-277.png |
| `CH08E-RBATCH-008` | `ch08e_rbatch_cards.md` | - CH08E-RBATCH-008 \| 反应集挂接 \| 操作 \| Selected reaction sets/挂接反应集 \| Blocks > RBATCH > Setup > Reactions \| Reactions 对象建好后必须从 Available 移入 Selected \| PDF p277; 渲染图 rbatch_powerlaw-277.png |
| `CH08E-RBATCH-009` | `ch08e_rbatch_cards.md` | - CH08E-RBATCH-009 \| 停止判据 \| 参数卡 \| Stop Criteria/Time/Stop value \| Blocks > RBATCH > Setup > Stop Criteria \| 可设一个或多个判据，达到任一判据即停止；本例按 Time=1.5 hr 停止 \| PDF p277; 渲染图 rbatch_powerlaw-277.png |
| `CH08E-RBATCH-010` | `ch08e_rbatch_cards.md` | - CH08E-RBATCH-010 \| 操作周期与剖面时间 \| 参数卡 \| Batch feed time/Maximum calculation time/Profile points \| Blocks > RBATCH > Setup > Operation Times \| 区分 Batch feed time、Total cycle time、Down time、Maximum calculation time、时间剖面间隔 \| PDF p278; 渲染图 rbatch_powerlaw-277.png |
| `CH08E-RBATCH-011` | `ch08e_rbatch_cards.md` | - CH08E-RBATCH-011 \| 间歇总量换算 \| 规则 \| 总量/流率/Batch feed time \| Streams > Input > Specifications; Blocks > RBATCH > Setup > Operation Times \| 间歇总量由流股基准流率与 Batch feed time 联合决定 \| PDF p274, p278; 渲染图 rbatch_powerlaw-276.png, rbatch_powerlaw-277.png |
| `CH08E-RBATCH-012` | `ch08e_rbatch_cards.md` | - CH08E-RBATCH-012 \| 动力学未冻结禁止填卡 \| 审核规则 \| 动力学未知/参数未冻结/不能填卡 \| Reactions > R-1 > Input > Stoichiometry/Kinetic \| 未确认模型、指数、k、E、相态、浓度基准前，不得进入 RBatch 正式填卡 \| PDF p273-p278 |
| `CH08F-RXNSET` | `ch08f_kinetics_parameter_card_audit.md` | - CH08F-RXNSET ：Reaction Set 对象 |
| `CH08F-STOICH` | `ch08f_kinetics_parameter_card_audit.md` | - CH08F-STOICH ：Stoichiometry 页 |
| `CH08F-KIN-GEN` | `ch08f_kinetics_parameter_card_audit.md` | - CH08F-KIN-GEN ：Kinetic 通用页 |
| `CH08F-EXP-DEFAULT0` | `ch08f_kinetics_parameter_card_audit.md` | - CH08F-EXP-DEFAULT0 ：Exponent 空白默认 0 |
| `CH08F-ORDER-NE-STOICH` | `ch08f_kinetics_parameter_card_audit.md` | - CH08F-ORDER-NE-STOICH ：反应级数不等于计量系数 |
| `CH08F-RATE-BASIS` | `ch08f_kinetics_parameter_card_audit.md` | - CH08F-RATE-BASIS ：Rate basis |
| `CH08F-CI-BASIS` | `ch08f_kinetics_parameter_card_audit.md` | - CH08F-CI-BASIS ：浓度/分压/摩尔分率基准 |
| `CH08F-ARRH-BTEMP` | `ch08f_kinetics_parameter_card_audit.md` | - CH08F-ARRH-BTEMP ：`exp(-B/T)` 到 `exp(-E/RT)` 转换 |
| `CH08F-POWERLAW` | `ch08f_kinetics_parameter_card_audit.md` | - CH08F-POWERLAW ：PowerLaw 可表达边界 |
| `CH08F-LHHW` | `ch08f_kinetics_parameter_card_audit.md` | - CH08F-LHHW ：LHHW 可表达边界 |
| `CH08F-USER` | `ch08f_kinetics_parameter_card_audit.md` | - CH08F-USER ：USER 子程序边界 |
| `CH08F-RCSTR-LINK` | `ch08f_kinetics_parameter_card_audit.md` | - CH08F-RCSTR-LINK ：RCSTR 联动 |
| `CH08F-RPLUG-LINK` | `ch08f_kinetics_parameter_card_audit.md` | - CH08F-RPLUG-LINK ：RPlug 联动 |
| `CH08F-RBATCH-LINK` | `ch08f_kinetics_parameter_card_audit.md` | - CH08F-RBATCH-LINK ：RBatch 联动 |
| `CH08F-BLOCKERS` | `ch08f_kinetics_parameter_card_audit.md` | - CH08F-BLOCKERS ：阻断条件 |
| `CH09-N01` | `ch09_flowsheet_options_analysis.md` | - CH09-N01 \| 可访问变量单位规则 \| 规则 \| 单位、局部单位、全局单位、SI、Property Sets \| `Information`, `Property Sets`, `Define/Vary` \| 标量变量多按 Information 页单位访问；矢量变量与物性参数常按 SI；Stream-Prop 按 Property Sets；参数变量按所在页用户指定单位 \| PDF p.281 |
| `CH09-N02` | `ch09_flowsheet_options_analysis.md` | - CH09-N02 \| 输入变量/结果变量判别 \| 规则 \| DUTY、QCALC、Calculation、结果变量 \| `Edit Variable Definition` \| 用变量列表工具提示判别；提示以 `Calculation` 开头的是结果变量 \| PDF p.281 |
| `CH09-N03` | `ch09_flowsheet_options_analysis.md` | - CH09-N03 \| Design Spec \| 工具 \| 设计规定、Target、Tolerance、Sampled、Manipulated \| `Flowsheeting Options > Design Specs > DS-*` \| 通过操纵输入变量满足目标；不能直接改流程结果值 \| PDF p.282-284 |
| `CH09-N04` | `ch09_flowsheet_options_analysis.md` | - CH09-N04 \| Design Spec Define \| 页面 \| Define、采集变量、Mole-Frac、Streams \| `... > Input > Define` \| 先定义采集变量；可取流程变量或变量函数中的基础变量 \| PDF p.283-284 |
| `CH09-N05` | `ch09_flowsheet_options_analysis.md` | - CH09-N05 \| Design Spec Spec \| 页面 \| Target、Tolerance、目标、容差 \| `... > Input > Spec` \| 实际判据是 `\|Target - Calculated\| < Tolerance` \| PDF p.283-284 |
| `CH09-N06` | `ch09_flowsheet_options_analysis.md` | - CH09-N06 \| Design Spec Vary \| 页面 \| 操纵变量、上下限、Vary \| `... > Input > Vary` \| 操纵变量必须是输入变量；上下限直接决定可行搜索域 \| PDF p.282-284 |
| `CH09-N07` | `ch09_flowsheet_options_analysis.md` | - CH09-N07 \| Design Spec Convergence \| 风险 \| 收敛模块、回路、初值、排序 \| 收敛模块结果页 \| 每个 Design Spec 默认生成并排序收敛模块；好初值可减少迭代 \| PDF p.282-283 |
| `CH09-N08` | `ch09_flowsheet_options_analysis.md` | - CH09-N08 \| Calculator \| 工具 \| 计算器、Fortran、Excel、外部文件 \| `Flowsheeting Options > Calculator > C-*` \| 用显式逻辑读写流程变量；适合公式型或外部逻辑任务 \| PDF p.285-287 |
| `CH09-N09` | `ch09_flowsheet_options_analysis.md` | - CH09-N09 \| Calculator Define \| 页面 \| 输入变量、输出变量、PD、VF \| `... > Input > Define` \| 必须明确输入/输出角色和单位 \| PDF p.286 |
| `CH09-N10` | `ch09_flowsheet_options_analysis.md` | - CH09-N10 \| Calculator Calculate \| 页面 \| Fortran、表达式、计算公式 \| `... > Input > Calculate` \| 在此输入可执行 Fortran 语句 \| PDF p.287 |
| `CH09-N11` | `ch09_flowsheet_options_analysis.md` | - CH09-N11 \| Calculator Sequence \| 页面 \| 执行顺序、before、after、Sequence \| `... > Input > Sequence` \| 要在被修改模块之前或结果生成之后运行，顺序决定值是否生效 \| PDF p.287 |
| `CH09-N12` | `ch09_flowsheet_options_analysis.md` | - CH09-N12 \| Balance \| 工具 \| 平衡、物料平衡、能量平衡、补充流 \| `Flowsheeting Options > Balance > B-*` \| 守恒闭合问题优先；可替代 Calculator，甚至替代 Design Spec 回路 \| PDF p.291-294 |
| `CH09-N13` | `ch09_flowsheet_options_analysis.md` | - CH09-N13 \| Balance Mass \| 页面 \| Mass balance number、HX \| `... > Setup > Mass Balance` \| 为指定模块建立物料衡算条目 \| PDF p.293 |
| `CH09-N14` | `ch09_flowsheet_options_analysis.md` | - CH09-N14 \| Balance Energy \| 页面 \| Energy balance number \| `... > Setup > Energy Balance` \| 为指定模块建立能量衡算条目 \| PDF p.293 |
| `CH09-N15` | `ch09_flowsheet_options_analysis.md` | - CH09-N15 \| Balance Calculate \| 页面 \| Stream name、Calculated Variables \| `... > Calculate`, `... > Results > Calculated Variables` \| 选定由 Balance 计算的物流，结果在 Calculated Variables 查看 \| PDF p.293-294 |
| `CH09-N16` | `ch09_flowsheet_options_analysis.md` | - CH09-N16 \| Sensitivity \| 工具 \| 灵敏度、what-if、趋势、扫描 \| `Model Analysis Tools > Sensitivity > S-*` \| 不改变基本工况；适合范围扫描、验证设计规定范围、简单优化 \| PDF p.294-299 |
| `CH09-N17` | `ch09_flowsheet_options_analysis.md` | - CH09-N17 \| Sensitivity Vary \| 页面 \| 范围、步长、双变量 \| `... > Input > Vary` \| 操纵变量必须是输入变量；需给范围和步长 \| PDF p.295-299 |
| `CH09-N18` | `ch09_flowsheet_options_analysis.md` | - CH09-N18 \| Sensitivity Define \| 页面 \| 采集变量、PP \| `... > Input > Define` \| 定义要观察的结果变量 \| PDF p.296-299 |
| `CH09-N19` | `ch09_flowsheet_options_analysis.md` | - CH09-N19 \| Sensitivity Fortran \| 页面 \| 选择性、组合指标、Fortran \| `... > Input > Fortran` \| 当考察指标不是现成变量时，在此定义表达式 \| PDF p.299 |
| `CH09-N20` | `ch09_flowsheet_options_analysis.md` | - CH09-N20 \| Sensitivity Tabulate \| 页面 \| Tabulate、列位置 \| `... > Input > Tabulate` \| 定义输出表格中变量/表达式列位置 \| PDF p.296, p.299 |
| `CH09-N21` | `ch09_flowsheet_options_analysis.md` | - CH09-N21 \| Sensitivity Results \| 结果 \| Summary、Curve、绘图 \| `... > Results > Summary` \| 结果可表格查看，也可画曲线判断单调性与最优区 \| PDF p.294, p.296-299 |
| `CH09-N22` | `ch09_flowsheet_options_analysis.md` | - CH09-N22 \| Optimization \| 工具 \| 优化、目标函数、最小化、最大化 \| `Model Analysis Tools > Optimization > O-*` \| 正式最值问题工具；难执行、难收敛 \| PDF p.300-305 |
| `CH09-N23` | `ch09_flowsheet_options_analysis.md` | - CH09-N23 \| Optimization Define \| 页面 \| FLOW1、FLOW2、采集变量 \| `... > Input > Define` \| 先定义目标函数中用到的采集变量 \| PDF p.302 |
| `CH09-N24` | `ch09_flowsheet_options_analysis.md` | - CH09-N24 \| Objective & Constraints \| 页面 \| 目标函数、约束添加 \| `... > Input > Objective & Constraints` \| 填写目标函数并挂接约束条件 \| PDF p.303-304 |
| `CH09-N25` | `ch09_flowsheet_options_analysis.md` | - CH09-N25 \| Optimization Vary \| 页面 \| 决策变量、Variable number、范围 \| `... > Input > Vary` \| 决策变量要给上下界；范围过宽会增大求解难度 \| PDF p.303 |
| `CH09-N26` | `ch09_flowsheet_options_analysis.md` | - CH09-N26 \| Constraint \| 工具 \| 约束、等式、不等式、ppm \| `Model Analysis Tools > Constraint(s) > C-*` \| 约束可为流程变量函数，必须指定容差 \| PDF p.300, p.303-305 |
| `CH09-N27` | `ch09_flowsheet_options_analysis.md` | - CH09-N27 \| Constraint Define \| 页面 \| FCH2CL2、产品质量分数 \| `... > Input > Define` \| 定义约束表达式使用的采集变量 \| PDF p.303-304 |
| `CH09-N28` | `ch09_flowsheet_options_analysis.md` | - CH09-N28 \| Constraint Spec \| 页面 \| Spec、上限、Tolerance \| `... > Input > Spec` \| 约束表达式和容差在此填写 \| PDF p.304 |
| `CH09-N29` | `ch09_flowsheet_options_analysis.md` | - CH09-N29 \| Optimization Strategy \| 策略 \| 先模拟、先灵敏度、候选变量、初值 \| `Optimization/Sensitivity workflow` \| 先跑稳基础模拟，再做 Sensitivity，再做 Optimization \| PDF p.300 |
| `CH09-N30` | `ch09_flowsheet_options_analysis.md` | - CH09-N30 \| Convergence Simplification \| 策略 \| 删除收敛回路、用 Balance 替代 \| `Balance vs Design Spec/Calculator` \| 守恒问题优先改写为 Balance，可减少回路 \| PDF p.291 |
| `CH10A-ED-01` | `ch10a_extractive_azeotropic_pressure_swing.md` | - CH10A-ED-01 \| 萃取精馏适用性 \| 规则 \| 相对挥发度小, 沸点差小, 普通精馏困难 \| 无 \| 难分体系优先考虑 ED \| p318 |
| `CH10A-ED-02` | `ch10a_extractive_azeotropic_pressure_swing.md` | - CH10A-ED-02 \| 萃取剂选择原则 \| 规则 \| 萃取剂, 溶剂选择, 不形成共沸 \| 无 \| 提高相对挥发度, 不共沸, 不反应, 易再生 \| p318 |
| `CH10A-ED-03` | `ch10a_extractive_azeotropic_pressure_swing.md` | - CH10A-ED-03 \| ED物性方法 \| Aspen方法 \| UNIFAC, 物性方法 \| Properties/Methods/Global \| 例10.1采用 UNIFAC \| p318-p319 |
| `CH10A-ED-04` | `ch10a_extractive_azeotropic_pressure_swing.md` | - CH10A-ED-04 \| ED主塔填卡 \| Aspen块 \| EXT-COL, 萃取塔, RadFrac \| Blocks/EXT-COL/Setup \| 先填 Configuration, Streams, Pressure \| p319-p320 |
| `CH10A-ED-05` | `ch10a_extractive_azeotropic_pressure_swing.md` | - CH10A-ED-05 \| ED溶剂灵敏度 \| Aspen分析 \| Sensitivity, 溶剂流量, 热负荷 \| Model Analysis Tools/Sensitivity \| 用溶剂流量作 Vary, 同看 Q 与产品纯度 \| p320-p322 |
| `CH10A-ED-06` | `ch10a_extractive_azeotropic_pressure_swing.md` | - CH10A-ED-06 \| ED再生塔 \| Aspen块 \| REGEN, 再生塔 \| Blocks/REGEN/Setup \| 主塔跑通后再加再生塔 \| p322-p323 |
| `CH10A-ED-07` | `ch10a_extractive_azeotropic_pressure_swing.md` | - CH10A-ED-07 \| ED补充溶剂 \| Aspen块 \| MAKEUP, Calculator \| Flowsheeting Options/Calculator \| 补料量等于各损失流之和 \| p323-p325 |
| `CH10A-AZ-01` | `ch10a_extractive_azeotropic_pressure_swing.md` | - CH10A-AZ-01 \| 共沸精馏适用性 \| 规则 \| 共沸, 相对挥发度接近1 \| 无 \| 普通精馏难分时考虑 AD \| p326-p327 |
| `CH10A-AZ-02` | `ch10a_extractive_azeotropic_pressure_swing.md` | - CH10A-AZ-02 \| 共沸剂选择原则 \| 规则 \| 共沸剂, 低沸共沸物, 易回收 \| 无 \| 优先低沸共沸剂, 用量小, 易回收 \| p327 |
| `CH10A-AZ-03` | `ch10a_extractive_azeotropic_pressure_swing.md` | - CH10A-AZ-03 \| 三元图初值法 \| 方法 \| Residue Curves, ternary maps, 初始用量 \| Home/Residue Curves \| 用连线和精馏边界选共沸剂初值 \| p328-p329 |
| `CH10A-AZ-04` | `ch10a_extractive_azeotropic_pressure_swing.md` | - CH10A-AZ-04 \| AD物性与LLE \| Aspen方法 \| UNIQ-RK, 液液平衡, 二元参数 \| Methods/Parameters/Binary Interaction \| 互不相溶体系需依赖 LLE 数据 \| p327 |
| `CH10A-AZ-05` | `ch10a_extractive_azeotropic_pressure_swing.md` | - CH10A-AZ-05 \| 主塔三相设置 \| Aspen块 \| COL-MAIN, Vapor-Liquid-Liquid, WATER second liquid \| Blocks/COL-MAIN/Specifications/Setup/3-Phase \| 非均相共沸塔按三相塔处理 \| p330-p331 |
| `CH10A-AZ-06` | `ch10a_extractive_azeotropic_pressure_swing.md` | - CH10A-AZ-06 \| 共沸塔稳算包 \| 收敛策略 \| Newton, Dogleg, Generate Estimates \| Blocks/COL-MAIN/Convergence \| 中间解时按 Custom+Newton+Dogleg+估计值 \| p332 |
| `CH10A-AZ-07` | `ch10a_extractive_azeotropic_pressure_swing.md` | - CH10A-AZ-07 \| 共沸塔Design Spec \| Aspen分析 \| Design Spec, ETOH 0.9995 \| Blocks/COL-MAIN/Specifications/Design Specifications \| 产品纯度用 Design Spec 锁定 \| p332-p333 |
| `CH10A-AZ-08` | `ch10a_extractive_azeotropic_pressure_swing.md` | - CH10A-AZ-08 \| 共沸流程撕裂流 \| 收敛策略 \| WEGSTEIN, REC-FEED, SOLVENT \| Convergence/Convergence \| 先假流逐步逼近, 后 Join Streams 建撕裂流 \| p333-p337 |
| `CH10A-AZ-09` | `ch10a_extractive_azeotropic_pressure_swing.md` | - CH10A-AZ-09 \| 共沸剂补料平衡 \| Aspen块 \| S-MAKEUP, Mass Balance \| Flowsheeting Options/Mass Balance \| 用衡算块自动算补料 \| p336-p337 |
| `CH10A-PSD-01` | `ch10a_extractive_azeotropic_pressure_swing.md` | - CH10A-PSD-01 \| 变压精馏判据 \| 规则 \| 压力敏感共沸, 5% \| 无 \| 共沸组成变化 >=5% 或共沸消失可用 PSD \| p338 |
| `CH10A-PSD-02` | `ch10a_extractive_azeotropic_pressure_swing.md` | - CH10A-PSD-02 \| PSD路线选择 \| 规则 \| 加压塔, 减压塔, 常压塔 \| 无 \| 依压力敏感性和能耗选高低压组合 \| p339 |
| `CH10A-PSD-03` | `ch10a_extractive_azeotropic_pressure_swing.md` | - CH10A-PSD-03 \| PSD物性方法 \| Aspen方法 \| NRTL-RK \| Methods/Specifications/Global \| 例10.3采用 NRTL-RK \| p339-p340 |
| `CH10A-PSD-04` | `ch10a_extractive_azeotropic_pressure_swing.md` | - CH10A-PSD-04 \| 压力相图验证 \| 方法 \| T-xy, 101.325kPa, 800kPa \| Properties analysis / phase diagram \| 先验证不同压力下共沸组成变化 \| p340 |
| `CH10A-PSD-05` | `ch10a_extractive_azeotropic_pressure_swing.md` | - CH10A-PSD-05 \| PSD初值衡算 \| 方法 \| B1, B2, RE, FEED2 \| 无 \| 先做全流程与高压塔局部物料衡算求初值 \| p340 |
| `CH10A-PSD-06` | `ch10a_extractive_azeotropic_pressure_swing.md` | - CH10A-PSD-06 \| PSD双塔填卡 \| Aspen块 \| HP, LP, RadFrac \| Blocks/HP; Blocks/LP \| 先建无循环双塔流程并分别填卡 \| p340-p341 |
| `CH10A-PSD-07` | `ch10a_extractive_azeotropic_pressure_swing.md` | - CH10A-PSD-07 \| PSD低压塔收敛 \| 收敛策略 \| 最大迭代次数, LP不收敛 \| Blocks/LP/Convergence/Basic \| 先加迭代次数再跑 \| p341 |
| `CH10A-PSD-08` | `ch10a_extractive_azeotropic_pressure_swing.md` | - CH10A-PSD-08 \| PSD循环闭合 \| 收敛策略 \| Join Streams, RE \| Flowsheet stream join \| 先无循环跑通, 后闭合 RE 循环 \| p342 |
| `CH10B-N01` | `ch10b_reactive_three_phase_distillation.md` | - CH10B-N01 \| REAC-DIST反应对象 \| 反应对象 \| `反应精馏, REAC-DIST` \| `Reactions\|Reactions` \| RD/3RD 塔内反应必须先创建 `REAC-DIST` 反应对象。 \| p343-p344, p353 |
| `CH10B-N02` | `ch10b_reactive_three_phase_distillation.md` | - CH10B-N02 \| 反应式录入页 \| 界面节点 \| `Stoichiometry, 正反应, 逆反应` \| `Reactions\|R-1\|Stoichiometry` \| 正逆反应分开建；反应类型从 `Kinetic/Equilibrium/Conversion` 中选。 \| p343-p345, p353-p354 |
| `CH10B-N03` | `ch10b_reactive_three_phase_distillation.md` | - CH10B-N03 \| 动力学数据页 \| 界面节点 \| `Kinetic, [Ci] basis, 活化能` \| `Reactions\|R-1\|Kinetic` \| 动力学数据必须与题源基准一致；10.4 用 `Mole fraction`，10.5b 用浓度型。 \| p344-p345, p352, p354 |
| `CH10B-N04` | `ch10b_reactive_three_phase_distillation.md` | - CH10B-N04 \| RD反应段 \| 规则节点 \| `反应段, 全塔反应, 再沸器反应` \| `Blocks\|RD\|Reactions\|Specifications` / `Blocks\|3RD\|Specifications\|Reactions\|Specifications` \| 反应可在任一板甚至再沸器发生；反应段必须显式指定。 \| p343, p346, p355 |
| `CH10B-N05` | `ch10b_reactive_three_phase_distillation.md` | - CH10B-N05 \| RD Holdups \| 规则节点 \| `Holdups, 持液量, 持汽量` \| `Blocks\|...\|Reactions\|Holdups` \| `Holdups` 直接关联反应速率；先假设后校核。 \| p343, p346 |
| `CH10B-N06` | `ch10b_reactive_three_phase_distillation.md` | - CH10B-N06 \| RD压力变量 \| 工艺变量 \| `压力, 温度分布` \| `Blocks\|RD\|Setup\|Pressure` \| 压力同时影响反应与分离，是 RD 首要变量。 \| p343, p346 |
| `CH10B-N07` | `ch10b_reactive_three_phase_distillation.md` | - CH10B-N07 \| RD收敛方法 \| 收敛节点 \| `Strongly non-ideal liquid` \| `Blocks\|RD\|Setup\|Configuration` \| 例10.4 的反应精馏配置使用 `Strongly non-ideal liquid`。 \| p345 |
| `CH10B-N08` | `ch10b_reactive_three_phase_distillation.md` | - CH10B-N08 \| 三相精馏塔模型 \| 模型节点 \| `DECANT3, 三相精馏` \| `Columns\|RadFrac\|DECANT3` \| 简单三相精馏例10.5a 使用 `DECANT3`。 \| p351 |
| `CH10B-N09` | `ch10b_reactive_three_phase_distillation.md` | - CH10B-N09 \| 三相反应精馏塔模型 \| 模型节点 \| `DECANT1, 三相反应精馏` \| `Columns\|RadFrac\|DECANT1` \| 三相反应精馏例10.5b 使用 `DECANT1`。 \| p353 |
| `CH10B-N10` | `ch10b_reactive_three_phase_distillation.md` | - CH10B-N10 \| 三相区设置 \| 界面节点 \| `三相区, 3-phase zone` \| `Blocks\|3PHD\|Specifications\|Setup\|Configuration` / `Blocks\|3RD\|Specifications\|Setup\|Configuration` \| 三相塔必须在配置页明确三相区位置。 \| p351, p354-p355 |
| `CH10B-N11` | `ch10b_reactive_three_phase_distillation.md` | - CH10B-N11 \| 塔内Decanter位置 \| 界面节点 \| `Decanters, 第9板, 第11板` \| `Blocks\|...\|Configuration\|Decanters\|Decanters` \| 先创建分相器，再绑定到具体板位。 \| p351, p354 |
| `CH10B-N12` | `ch10b_reactive_three_phase_distillation.md` | - CH10B-N12 \| 第二液相关键组分 \| 规则节点 \| `2nd liquid, H2O, 关键组分` \| `Blocks\|...\|Configuration\|Decanters\|<stage>\|Specifications` \| `2nd liquid` 指含关键组分更多的一相；例中 `H2O` 对应水相。 \| p351, p354 |
| `CH10B-N13` | `ch10b_reactive_three_phase_distillation.md` | - CH10B-N13 \| 液相返塔比例 \| 操作节点 \| `Fraction returned, 有机相返水相` \| `Blocks\|...\|Configuration\|Decanters\|<stage>\|Specifications` \| 例10.5a 为 `1st=1, 2nd=0.05`；例10.5b 为两相均 `0.30`。 \| p351, p354 |
| `CH10B-N14` | `ch10b_reactive_three_phase_distillation.md` | - CH10B-N14 \| 三相LLE数据库门禁 \| 硬门禁 \| `二元交互参数, 液液平衡数据库` \| `Methods\|...\|Binary Interaction` \| 部分互溶/液液分相体系的二元参数必须来自 LLE 数据库。 \| p350 |
| `CH10B-N15` | `ch10b_reactive_three_phase_distillation.md` | - CH10B-N15 \| 用户动力学子程序 \| 子程序节点 \| `Use user kinetic subroutine, ACTKIN` \| `Reactions\|USER\|Kinetic` / `Reactions\|USER\|Subroutine` \| 用户子程序路线下，反应对象仍是 `REAC-DIST`；子程序名和参数单独录入。 \| p348-p349 |
| `CH10B-N16` | `ch10b_reactive_three_phase_distillation.md` | - CH10B-N16 \| ch08b动力学硬门禁 \| 外部约束 \| `基准, 单位, Ea, A, 子程序参数` \| `ch08b` \| 只要涉及动力学值与基准映射，必须先过 `ch08b`，本章不允许经验补值。 \| p343-p345, p352-p354 |
| `node_ch10c_001` | `ch10c_energy_saving_distillation_structures.md` | - node_ch10c_001 \| 多效精馏 \| 结构节点 \| 多效, 双效, 三效, 效数 \| Blocks\|RadFrac; Blocks\|Heater; Blocks\|HeatX \| 先单塔后拆塔；先无热耦合后加热耦合；效数增加需权衡投资与节能 \| p356-357 |
| `node_ch10c_002` | `ch10c_energy_saving_distillation_structures.md` | - node_ch10c_002 \| 多效热耦合顺序 \| 流程节点 \| 热耦合, Heater, HeatX \| Blocks\|...\|Setup\|Configuration; HeatX 替换 \| 先用 Heater/热流稳定双效，再换 HeatX 细化设备参数 \| p357 |
| `node_ch10c_003` | `ch10c_energy_saving_distillation_structures.md` | - node_ch10c_003 \| DWC 适用性 \| 决策节点 \| 隔壁塔, DWC, Petlyuk \| Blocks\|MultiFrac\|PETLYUK 或 RadFrac 连接 \| 中间组分较高、产品纯度高、三产品同塔壳；压力不能随意改 \| p366-367 |
| `node_ch10c_004` | `ch10c_energy_saving_distillation_structures.md` | - node_ch10c_004 \| DWC 内部连接物流 \| 流程节点 \| 内部连接物流, connect stream \| Blocks\|DWC\|Connect Streams \| 四股内部连接物流是 DWC 收敛关键，初值要接近真实回路 \| p368-372 |
| `node_ch10c_005` | `ch10c_energy_saving_distillation_structures.md` | - node_ch10c_005 \| DWC 纯度规定 \| 约束节点 \| 设计规定, 侧线产品, 塔顶产品 \| Blocks\|DWC\|Design Specifications; Vary \| 三个产品纯度分别设设计规定，操纵变量绑塔顶流量/侧线流量/连接蒸汽/回流比 \| p372-374 |
| `node_ch10c_006` | `ch10c_energy_saving_distillation_structures.md` | - node_ch10c_006 \| 热泵精馏 \| 结构节点 \| 热泵, 压缩机, 闪蒸器, 阀门 \| Blocks\|COMPR; ASSI-REB; FLASH; VALVE \| 塔顶蒸汽压缩回塔底；压缩比需灵敏度扫描；电功要折算热负荷 \| p377-386 |
| `node_ch10c_007` | `ch10c_energy_saving_distillation_structures.md` | - node_ch10c_007 \| 热泵回路闭合 \| 收敛节点 \| Reflux, FLA-OUT, VAPOR, SPLI-OUT \| Convergence\|Tear\|Specifications; Convergence\|Options\|Default Methods \| 比较输入/计算值并逐步逼近；Tears 用 Broyden；必要时加辅助冷凝器/再沸器 \| p385-386 |
| `node_ch10c_008` | `ch10c_energy_saving_distillation_structures.md` | - node_ch10c_008 \| HIDiC \| 结构节点 \| 内部热耦合, HIDiC, Internally Heat Integrated Distillation Column \| Blocks\|RECT; STRIP; COMP; VALVE \| 精馏段高压、提馏段低压；板间逐板热耦合；先确认板间温差>5℃再做换热 \| p377-383 |
| `node_ch10c_009` | `ch10c_energy_saving_distillation_structures.md` | - node_ch10c_009 \| HIDiC 板间换热量 \| 参数节点 \| Side Duties, 换热板, 每块板换热量 \| Blocks\|RECT\|Configuration\|Heaters and Coolers\|Side Duties; Blocks\|STRIP\|... \| 总换热量先取较小热负荷，再分配到板上；先小热量起步，后逐步逼近 \| p382-383 |
| `node_ch10c_010` | `ch10c_energy_saving_distillation_structures.md` | - node_ch10c_010 \| 压缩比优化 \| 优化节点 \| 压缩比, 对数平均温差, 能耗 \| Blocks\|COMPR\|Setup\|Specifications; Sensitivity \| 压缩比同时影响温差、换热面积和电耗，必须用灵敏度分析而不是拍值 \| p382-383 |
| `node_ch10c_011` | `ch10c_energy_saving_distillation_structures.md` | - node_ch10c_011 \| 收敛增强 \| 方法节点 \| 估计值, 牛顿, 逐步更改设计规定 \| Convergence; Estimates; Design Specs \| 中间解时先生成估计值，再切 Newton/Broyden，逐步改参数 \| p332, p372-374, p379-380 |
| `node_ch10c_012` | `ch10c_energy_saving_distillation_structures.md` | - node_ch10c_012 \| 能耗比较 \| 评估节点 \| 等量负荷, 电热转换系数 \| Results\|Summary; Streams\|Material \| 压缩机电耗按电热系数折算，再和再沸/冷凝负荷一起比；不能只看单个设备 \| p383, p386 |
| `D-TA-01` | `ch10d_column_analysis_nq_curves.md` | - D-TA-01 \| 热力学分析入口 \| 入口 \| `热力学分析`、`Column Targeting` \| `Blocks\|RADFRAC\|Analysis\|Analysis Options` \| 先做热力学分析，再谈回流比/进料板优化 \| p394 |
| `D-TA-02` | `ch10d_column_analysis_nq_curves.md` | - D-TA-02 \| PNMTC 概念 \| 原理 \| `PNMTC`、`最小热力学条件` \| `Thermal Analysis` \| S-H/T-H 总组合曲线是 PNMTC 近似；看热量分配是否合理 \| p394 |
| `D-TA-03` | `ch10d_column_analysis_nq_curves.md` | - D-TA-03 \| S-H 判读 \| 判读 \| `S-H`、`Stage-Enthalpy` \| `Profiles Thermal Analysis` \| 进料点突变大通常表示进料板不合适 \| p394-400 |
| `D-TA-04` | `ch10d_column_analysis_nq_curves.md` | - D-TA-04 \| T-H 判读 \| 判读 \| `T-H`、`Temperature-Enthalpy` \| `Profiles Thermal Analysis` \| 曲线越对称，热负荷越均衡；可用于改进进料温度/回流比 \| p398-400 |
| `D-TA-05` | `ch10d_column_analysis_nq_curves.md` | - D-TA-05 \| 中间冷凝器/再沸器 \| 优化 \| `中间冷凝器`、`中间再沸器` \| `Thermal Analysis` \| 利用理想与实际曲线间的面积判断可用温区 \| p401 |
| `D-TA-06` | `ch10d_column_analysis_nq_curves.md` | - D-TA-06 \| 有效能损失 \| 辅助判据 \| `Exergy loss`、`有效能` \| `Profiles Thermal Analysis` \| 用于比较方案，不作为唯一目标 \| p401-402 |
| `D-HY-01` | `ch10d_column_analysis_nq_curves.md` | - D-HY-01 \| 水力学分析入口 \| 入口 \| `Hydraulic Analysis`、`水力学` \| `Blocks\|RADFRAC\|Analysis\|Analysis Options` \| 用于判定塔内负荷和泛点风险 \| p394 |
| `D-HY-02` | `ch10d_column_analysis_nq_curves.md` | - D-HY-02 \| 喷射液泛因子 \| 约束 \| `Jet Flooding Limit` \| `Tray Rating\|1\|Setup\|Design/Pdrop` / `Pack Rating\|1\|Setup\|Design/Pdrop` \| 默认值 0.85；决定最大气相流量 \| p394 |
| `D-HY-03` | `ch10d_column_analysis_nq_curves.md` | - D-HY-03 \| 液泛因子 \| 约束 \| `Flooding limit` \| `Tray Rating\|1\|Setup\|Downcomers` \| 默认值 0.5；用于板式塔液相液泛判断 \| p394 |
| `D-HY-04` | `ch10d_column_analysis_nq_curves.md` | - D-HY-04 \| 流量三线图 \| 判读 \| `Actual liquid flow`、`Hydraulic maximum liquid flow`、`Ideal minimum liquid flow` \| `Profiles Hydraulic Analysis` \| 实际流量必须低于最大允许流量 \| p397-401 |
| `D-NQ-01` | `ch10d_column_analysis_nq_curves.md` | - D-NQ-01 \| NQ 曲线入口 \| 入口 \| `NQ Curves` \| `Blocks\|COLUMN\|Analysis\|NQ Curves` \| 用于筛塔板数、进料板、回流比和热负荷 \| p402-405 |
| `D-NQ-02` | `ch10d_column_analysis_nq_curves.md` | - D-NQ-02 \| 目标函数 \| 参数 \| `Qreb-Qcond`、`Qcond`、`Qreb`、`Mole-Rr` 等 \| `NQ Curves\|1\|Setup\|Specifications` \| 先定优化目标，再生成曲线 \| p403-404 |
| `D-NQ-03` | `ch10d_column_analysis_nq_curves.md` | - D-NQ-03 \| 收敛算法 \| 参数 \| `NQ-Fopt-Meth`、`Case study`、`QP search`、`Hybrid` \| `Blocks\|COLUMN\|Convergence\|Convergence\|Advanced` \| 两相塔默认可用 Hybrid；三相塔用 Case study \| p404 |
| `D-NQ-04` | `ch10d_column_analysis_nq_curves.md` | - D-NQ-04 \| 结果收口 \| 判读 \| `目标函数变平`、`21板后不再变化` \| `NQ Curves` \| 边际收益消失时停止盲目加板 \| p404-405 |
| `D-OPT-01` | `ch10d_column_analysis_nq_curves.md`; `project_cases_T03101A_feed_stage_selection.md` | - D-OPT-01 \| 进料位置优化 \| 规则 \| `feed stage`、`进料位置`、`设计规定` \| `DSTWU` 初值 + `RadFrac Design Spec/Vary` + `Sensitivity`；`Thermal Analysis`/`NQ Curves` 作诊断 \| 普通塔先冻结分离目标，用 DSTWU 给初值，在严格塔里保持产品回收率设计规定，扫进料板对回流比和热负荷的影响，按曲线拐点/低边际收益选板；特殊塔仍先走 DSTWU-SKIP \| p396-405 + T03101A DOCX |
| `D-OPT-02` | `ch10d_column_analysis_nq_curves.md` | - D-OPT-02 \| 回流比优化 \| 规则 \| `reflux ratio`、`回流比` \| `Thermal Analysis` + `NQ Curves` \| 降回流比常可降热负荷，但可能要补塔板数 \| p398-399、p402-405 |
| `D-OPT-03` | `ch10d_column_analysis_nq_curves.md` | - D-OPT-03 \| 热负荷优化 \| 规则 \| `Qred-Qcond`、`总热负荷` \| `NQ Curves` \| 以最小总热负荷作为塔板数与进料板筛选准则 \| p403-405 |
| `N11-01` | `ch11_process_simulation_workflow.md` | - N11-01 \| 序贯模块法 \| 原理 \| 序贯模块法、单元模块、输入物流、输出物流 \| Setup/Block 模拟顺序 \| 单元按给定顺序逐一求解，流程含循环时需在循环段迭代至收敛 \| PDF page 406-407 |
| `N11-02` | `ch11_process_simulation_workflow.md` | - N11-02 \| 循环物流迭代 \| 流程机制 \| 循环物流、RECYCLE、迭代、容差 \| Flowsheet循环段 \| 先给循环物流初值，再计算回路，比较计算值与初值直至进入容差 \| PDF page 406-407 |
| `N11-03` | `ch11_process_simulation_workflow.md` | - N11-03 \| 断裂物流 \| 收敛控制 \| tear、RECYCLE、PRODUCT、初值 \| Convergence\|Tear / Nesting Order / Sequence \| 默认初值为 0；不收敛时需改初值、改断裂物流或改求解顺序 \| PDF page 407, 411-412, 419-421 |
| `N11-04` | `ch11_process_simulation_workflow.md` | - N11-04 \| 收敛算法选择 \| 收敛控制 \| Direct、Wegstein、Broyden、Newton \| Convergence\|Options\|Defaults\|Default Methods \| 默认常用 Wegstein；耦合强可考虑 Broyden；Newton 快但计算量大 \| PDF page 407 |
| `N11-05` | `ch11_process_simulation_workflow.md` | - N11-05 \| 最大迭代次数 \| 参数 \| Maximum flowsheet evaluations、30、100 \| Convergence\|Options\|Methods \| 默认值 30；不收敛时可提高上限再判断问题来源 \| PDF page 407, 411-412 |
| `N11-06` | `ch11_process_simulation_workflow.md` | - N11-06 \| 初始化 \| 操作 \| initialize、重新运行、上次结果 \| Simulation 初始化 \| 改条件后必须初始化，否则沿用上次模拟结果 \| PDF page 407, 411-412, 419-421 |
| `N11-07` | `ch11_process_simulation_workflow.md` | - N11-07 \| 简单模块 \| 建模策略 \| Sep、Sep2、Flash、Decanter \| Block 输入 \| 用于先跑通流程、验证物料衡算与结构逻辑 \| PDF page 408-409, 413-416 |
| `N11-08` | `ch11_process_simulation_workflow.md` | - N11-08 \| 严格模块 \| 建模策略 \| Flash2、Decanter、RadFrac \| Block 替换 \| 在简单模型收敛后逐步替换，替换前先用简单模型结果作初值 \| PDF page 413-421 |
| `N11-09` | `ch11_process_simulation_workflow.md` | - N11-09 \| 物性方法 \| 热力学 \| NRTL、UNIQUAC、PENG-ROB \| Methods\|Specifications\|Global \| 物性方法必须与体系相符；强非理想体系优先关注合适模型 \| PDF page 408-409, 439-440 |
| `N11-10` | `ch11_process_simulation_workflow.md` | - N11-10 \| 物料优先 \| 建模顺序 \| heat balance calculations、物料衡算 \| Setup\|Calculation Options\|Calculations \| 初始阶段可先关能量衡算，只做物料衡算降低复杂度 \| PDF page 409 |
| `N11-11` | `ch11_process_simulation_workflow.md` | - N11-11 \| 控制面板诊断 \| 调试 \| control panel、error、warning、$OLVER01 \| Control Panel / Results \| 先看控制面板定位错误类型，再按断裂物流、算法和顺序排查 \| PDF page 410-412, 419-421 |
| `N11-12` | `ch11_process_simulation_workflow.md` | - N11-12 \| 子流程拆分 \| 设计方法 \| 子流程、逐步建模、组合流程 \| Flowsheet分段 \| 复杂流程应先拆成子流程，各段收敛后再组合成全流程 \| PDF page 412-413, 423-430 |
| `N11-13` | `ch11_process_simulation_workflow.md` | - N11-13 \| 严格模块单独运行 \| 调试策略 \| 单独运行、初值 \| 单元级计算 \| 严格模块先独立收敛，再嵌入循环子流程 \| PDF page 412-413 |
| `N11-14` | `ch11_process_simulation_workflow.md` | - N11-14 \| 断裂物流重定向 \| 调试策略 \| 改变断裂物流、重新指定求解顺序 \| Convergence\|Sequence \| 默认断裂物流不合适时，要连同求解顺序一起重设 \| PDF page 411-412, 419-421 |
| `N11-15` | `ch11_process_simulation_workflow.md` | - N11-15 \| 流程分段升级 \| 工程方法 \| 先简单后严格、1~2个替换 \| 整体流程 \| 从简单模型升级到完整流程时逐步收紧规定，避免一次性引入太多不确定性 \| PDF page 412-413 |
| `CH12-N01` | `ch12_convergence_strategy.md` | - CH12-N01 \| 序贯模块法流程收敛 \| 概念 \| 序贯模块法,循环物流,设计规定 \| Convergence\|Options \| 有循环才有流程收敛；每个 tear/设计规定都要对应收敛模块 \| 441-443 |
| `CH12-N02` | `ch12_convergence_strategy.md` | - CH12-N02 \| 断裂物流选择 \| 规则 \| tear stream,断裂物流,循环切断 \| Convergence\|Tear \| 优先选变量少、组成稳定、变化幅度小、能少断就少断 \| 442, 449, 462 |
| `CH12-N03` | `ch12_convergence_strategy.md` | - CH12-N03 \| Tear 容差与痕量组分 \| 参数 \| Tolerance,Trace threshold,Trace option \| Convergence\|Options\|Defaults\|Tear Convergence \| `Err/Tol` 判据以相对误差为核心；痕量组分可跳过或渐进放宽 \| 443-444 |
| `CH12-N04` | `ch12_convergence_strategy.md` | - CH12-N04 \| 组分组降维 \| 规则 \| Component group,Comp-Groups \| Convergence\|Options\|Defaults\|Tear Convergence; Setup\|Comp-Groups \| 零流量/恒定组分建组，配合矩阵法减小矩阵和扰动 \| 443 |
| `CH12-N05` | `ch12_convergence_strategy.md` | - CH12-N05 \| Wegstein 调参 \| 算法规则 \| Wegstein,q,Wait,振荡,收敛慢 \| Convergence\|Options\|Methods \| 慢则 `Lower bound` 更负；振荡则 `Upper bound` 设 0.5 或边界放到 0~1；`q=0` 等效直接迭代 \| 445, 461-465 |
| `CH12-N06` | `ch12_convergence_strategy.md` | - CH12-N06 \| Direct 判别法 \| 算法规则 \| Direct,直接迭代,组分累积 \| Convergence\|Options\|Default Methods \| 慢但稳；用于识别累积和判断是否存在稳态解 \| 445, 462, 464 |
| `CH12-N07` | `ch12_convergence_strategy.md` | - CH12-N07 \| Secant 设计规定收敛 \| 算法规则 \| Secant,Bracket,边界 \| Convergence\|Options\|Methods \| 平缓函数用 `Bracket=Yes`；非单调或撞边界用 `Check bounds` \| 445-446, 462-465 |
| `CH12-N08` | `ch12_convergence_strategy.md` | - CH12-N08 \| Broyden/Newton 强耦合联解 \| 算法规则 \| Broyden,Newton,强耦合,联解 \| Convergence\|Convergence \| 多 tear、多 design spec、内外层强耦合时优先联解 \| 446-447, 461-463 |
| `CH12-N09` | `ch12_convergence_strategy.md` | - CH12-N09 \| 嵌套顺序与局部顺序 \| 顺序规则 \| Nesting Order,Sequence,Design spec nesting \| Convergence\|Nesting Order; Convergence\|Sequence; Convergence\|Options\|Defaults\|Sequencing \| 先默认顺序，后局部修改；外层/内层关系优先在 Nesting Order 处理 \| 448-450, 464-465 |
| `CH12-N10` | `ch12_convergence_strategy.md` | - CH12-N10 \| Convergence 结果诊断 \| 诊断 \| Summary,Tear History,Spec History,Err/Tol \| Convergence\|Convergence\|Results \| 先看最大误差变量，再决定修 tear、spec 还是 Calculator \| 456-459 |
| `CH12-N11` | `ch12_convergence_strategy.md` | - CH12-N11 \| 控制面板诊断级别 \| 诊断 \| Diagnostics,Level 4,Level 5 \| Setup\|Specifications\|Diagnostics; Blocks\|Block Options\|Diagnostics \| Level 4 看摘要，Level 5 看每次未收敛变量；推荐 `Simulation=3, Convergence=5` \| 457-459 |
| `CH12-N12` | `ch12_convergence_strategy.md` | - CH12-N12 \| Calculator 断裂变量排序 \| 规则 \| Tear Calculator export variables,Import,Export \| Convergence\|Options\|Defaults\|Sequencing \| 勾选后排序算法可识别 Calculator 断裂变量；Import/Export 变量必须列全 \| 463 |
| `CH12-N13` | `ch12_convergence_strategy.md` | - CH12-N13 \| 流程收敛共性风险 \| 规则 \| 循环物流数,循环比 \| Convergence\|Tear; Control Panel \| 循环越多、回流比越大越难收敛；回流超过进料 3 倍时非常困难 \| 460 |
| `CH12-N14` | `ch12_convergence_strategy.md` | - CH12-N14 \| RadFrac 预置方法映射 \| 模块方法 \| Standard,Sum-Rates,Nonideal,Azeotropic,Cryogenic,Custom \| Blocks\|RADFRAC\|Specifications\|Setup\|Configuration \| 预置方法本质是“算法+初始化”的组合 \| 468-470 |
| `CH12-N15` | `ch12_convergence_strategy.md` | - CH12-N15 \| RadFrac 内层/外层收敛 \| 模块高级参数 \| Ilmeth,Tolil0,Tolilfac,Tolilmin,Stable-Meth \| Blocks\|RADFRAC\|Convergence\|Convergence\|Advanced \| 外层越接近收敛，内层容差越应收紧；Newton 可用 Dogleg/Line search 稳定 \| 470-471 |
| `CH12-N16` | `ch12_convergence_strategy.md` | - CH12-N16 \| RadFrac 设计规定模式 \| 模块高级参数 \| Dsmeth,Nested,Simult,Weighting Factor,Scale Factor \| Blocks\|RADFRAC\|Convergence\|Convergence\|Advanced; Blocks\|RADFRAC\|Specifications\|Design Specifications\|1\|Options \| `Nested` 允许设计规定数≥操纵变量数；`Simult` 要求两者相等 \| 471-472 |
| `CH12-N17` | `ch12_convergence_strategy.md` | - CH12-N17 \| RadFrac 操作规定可行性 \| 规则 \| D/F,B/F,Jacobian singular,侧线 \| Blocks\|RADFRAC\|Specifications \| 优先比值规格；避免导致雅可比奇异或物料守恒不可能的规定 \| 472-473 |
| `CH12-N18` | `ch12_convergence_strategy.md` | - CH12-N18 \| RadFrac 物性适配 \| 规则 \| HV,CPIG,K值,三相,LLE \| Properties; Blocks\|RADFRAC\|Results \| 物性法错误会表现成干板、外层失败、三相预测错误或异常 K 值 \| 473-474 |
| `CH12-N19` | `ch12_convergence_strategy.md` | - CH12-N19 \| RadFrac 故障排除 \| 排障 \| Damping Level,Fminfac,Error Tolerance,Max iterations \| Blocks\|RADFRAC\|Convergence\|Convergence\|Basic; Blocks\|RADFRAC\|Convergence\|Convergence\|Advanced \| `Err/Tol` 下降就加迭代；发散先估值/简化/换算法；振荡先加阻尼 \| 473-480 |
| `CH12-N20` | `ch12_convergence_strategy.md` | - CH12-N20 \| RadFrac 自定义收敛 \| 模块方法 \| Custom,Algorithm,Initialization \| Blocks\|RADFRAC\|Specifications\|Setup\|Configuration; Blocks\|RADFRAC\|Convergence\|Convergence\|Basic \| 复杂塔常需自定义；默认外层 25 次不够时优先加迭代，不随意放宽容差 \| 477-480 |
| `CH13-N01` | `ch13_petroleum_distillation.md` | - CH13-N01 \| 原油复杂性 \| concept \| 原油、复杂混合物、无法定义确切组分 \| 无 \| 原油模拟必须依赖原油评价数据与虚拟组分，不走常规纯组分建模 \| p. 481, p. 484-487 |
| `CH13-N02` | `ch13_petroleum_distillation.md` | - CH13-N02 \| API 重度 \| property \| API、相对密度、重度 \| 无 \| API 与 d15.6_15.6 关联；API 越低通常越重 \| p. 481-482 |
| `CH13-N03` | `ch13_petroleum_distillation.md` | - CH13-N03 \| K 值 \| property \| Watson K、UOP K、特性因数 \| 无 \| K 用平均沸点与相对密度表征油品性质，K 越大通常越偏轻质/石蜡性 \| p. 482 |
| `CH13-N04` | `ch13_petroleum_distillation.md` | - CH13-N04 \| 蒸馏曲线类型 \| rule \| TBP、D86、D1160、D2887、减压蒸馏 \| Assay/Distillation curve \| Aspen 接受 5 类蒸馏曲线；做油品模拟至少要有蒸馏曲线和重度/API \| p. 484 |
| `CH13-N05` | `ch13_petroleum_distillation.md` | - CH13-N05 \| TBP 参考条件 \| rule \| TBP、14~18 板、5:1、310℃ \| Distillation/TBP \| TBP 是最接近真实沸点的参考，蒸馏釜温度通常不超过 310℃ \| p. 484 |
| `CH13-N06` | `ch13_petroleum_distillation.md` | - CH13-N06 \| 曲线换算 \| transformation \| Edmister、Maxwell、Hadden、Daubert \| Distillation curve conversion \| ASTM/D 线需要先换成 TBP；换算是近似但工业上可接受 \| p. 485 |
| `CH13-N07` | `ch13_petroleum_distillation.md` | - CH13-N07 \| Assay Library \| data-source \| Assay Library、Import Assay Library、原油评价数据库 \| Components\|Assay/Blend\|Assay Data \| 库内原油可直接导入 Aspen；每种原油含蒸馏曲线、重度及性质曲线 \| p. 485 |
| `CH13-N08` | `ch13_petroleum_distillation.md` | - CH13-N08 \| ASPEN 物性法 \| property-method \| API-METH、ASPEN、LK、API-TWU、EXT-TWU \| Property method / petroleum assay properties \| Aspen 的推荐石油馏分物性估算方法是 ASPEN；扩展法用于更高沸点区间 \| p. 485-486 |
| `CH13-N09` | `ch13_petroleum_distillation.md` | - CH13-N09 \| 逐一定义假组分 \| input-rule \| pseudo component、平均正常沸点、密度、分子量 \| Components / Pseudocomponent \| 至少给两个基础物性，第三个可由关联式求出 \| p. 487 |
| `CH13-N10` | `ch13_petroleum_distillation.md` | - CH13-N10 \| 曲线生成假组分 \| input-rule \| Dist Curve、SPGR、API、light ends \| Components\|PetroCharacterization\|Generation\|Cuts \| 至少 4 个蒸馏点 + SPGR/API；可加轻端、重度、MW、硫、辛烷值曲线 \| p. 487-488 |
| `CH13-N11` | `ch13_petroleum_distillation.md` | - CH13-N11 \| 切割点默认集 \| rule \| cut set、28 cuts、8 cuts、4 cuts \| Generation\|Cuts \| Aspen 默认切点按 TBP 范围分段，重端切割更粗 \| p. 488 |
| `CH13-N12` | `ch13_petroleum_distillation.md` | - CH13-N12 \| 轻端处理 \| rule \| light ends、match TBP、specified fraction \| Light Ends handling \| 轻端要独立处理，不要粗暴塞入某个窄馏分 \| p. 488 |
| `CH13-N13` | `ch13_petroleum_distillation.md` | - CH13-N13 \| 常压塔流程 \| equipment \| PetroFrac、CDU、preflash、side stripper、pumparound \| Columns\|PetroFrac\|CDU10F/CDU6F \| 常压塔要配一次汽化、侧线汽提和中段循环；不能用恒摩尔回流简化 \| p. 511-514 |
| `CH13-N14` | `ch13_petroleum_distillation.md` | - CH13-N14 \| 进料与炉 \| equipment-card \| Furnace、Single stage flash、overflash \| Blocks\|CRUDE\|Setup\|Streams/Furnace \| 进料板位、进料方式、加热炉类型、过汽化度和出口压力是关键输入 \| p. 514-515 |
| `CH13-N15` | `ch13_petroleum_distillation.md` | - CH13-N15 \| 压力分布 \| equipment-card \| condenser pressure、top pressure、pressure drop \| Blocks\|CRUDE\|Setup\|Pressure \| 常压塔必须填全塔压力分布，示例为 0.11/0.145/0.028 MPa 这一类结构 \| p. 515 |
| `CH13-N16` | `ch13_petroleum_distillation.md` | - CH13-N16 \| 汽提塔与中段回流 \| equipment-card \| stripper, draw stage, return stage, pumparound \| Blocks\|CRUDE\|Strippers / Pumparounds \| 侧线汽提塔和中段回流是调馏程与取热的关键卡位 \| p. 512-517 |
| `CH13-N17` | `ch13_petroleum_distillation.md` | - CH13-N17 \| 设计规定 \| solve-fit \| Design Specifications、95% temperature、distillate flow \| Blocks\|CRUDE\|Design Specifications \| 用产品流量或塔底汽提负荷去约束产品馏程，不是单看收敛 \| p. 518-520 |
| `CH13-N18` | `ch13_petroleum_distillation.md` | - CH13-N18 \| 结果审查 \| audit \| Profiles TPFQ、Stream Results、Vol.% Curves \| Results / Profiles / Stream Results \| 必须同时核对塔内分布、物流蒸馏曲线和 5%/95% 点 \| p. 509-521 |
| `Chapter14_SimpleDynamicSimulation` | `ch14_dynamic_simulation.md` | - Chapter14_SimpleDynamicSimulation ：范围 PDF p524-p558；包含动态模拟目的、Aspen Plus Dynamics、稳态导入、闪蒸、反应器、精馏塔、隔壁塔。 |
| `DynamicSimulationPurpose` | `ch14_dynamic_simulation.md` | - DynamicSimulationPurpose ：安全操作、减少污染、提升操作性能、改善开停工、维持产品质量、故障模拟、间歇操作优化。 |
| `AspenPlusDynamics` | `ch14_dynamic_simulation.md` | - AspenPlusDynamics ：支持工艺设计与控制方案并行研究；可做压力驱动/流量驱动动态模拟。 |
| `PressureDrivenExportGate` | `ch14_dynamic_simulation.md` | - PressureDrivenExportGate ：依赖泵、压缩机、阀门、设备尺寸、压力检测。 |
| `DynamicModeInput` | `ch14_dynamic_simulation.md` | - DynamicModeInput ：`Dynamics -> Dynamic Mode`；暴露动态数据输入页面。 |
| `PressureChecker` | `ch14_dynamic_simulation.md` | - PressureChecker ：导出前门禁；失败则停止。 |
| `PressureDrivenExport` | `ch14_dynamic_simulation.md` | - PressureDrivenExport ：`Dynamics -> Pressure Driven`；成功生成 `.dynf`。 |
| `ValveSizingGate` | `ch14_dynamic_simulation.md` | - ValveSizingGate ：操纵阀压降不能过小；有效相态应匹配物流。 |
| `HoldupSizingRule` | `ch14_dynamic_simulation.md` | - HoldupSizingRule ：50% 持液、5 min 停留时间、长度/高度为直径两倍。 |
| `RadFracDynamicData` | `ch14_dynamic_simulation.md` | - RadFracDynamicData ：回流罐、塔釜液槽、塔板水力学、溢流堰高度。 |
| `FlashDynamicVesselGate` | `ch14_dynamic_simulation.md` | - FlashDynamicVesselGate ：闪蒸罐从 `Instantaneous` 改为 `Vertical` 并输入尺寸。 |
| `InitializationRun` | `ch14_dynamic_simulation.md` | - InitializationRun ：新 `.dynf` 必须先初始化。 |
| `ControlSignalConnection` | `ch14_dynamic_simulation.md` | - ControlSignalConnection ：ControlSignal 蓝色箭头连接 PV 与 OP。 |
| `PIDIncrController` | `ch14_dynamic_simulation.md` | - PIDIncrController ：常用控制器；需设置 Gain、Integral time、作用方向、范围、初值。 |
| `FlowControllerRule` | `ch14_dynamic_simulation.md` | - FlowControllerRule ：流量控制常用 Gain 0.5、Integral time 0.3 min、反作用；限讲义例题语境。 |
| `PressureControllerRule` | `ch14_dynamic_simulation.md` | - PressureControllerRule ：压力控制器缺省 Gain 20、Integral time 12 min；常见为正作用。 |
| `LevelControllerRule` | `ch14_dynamic_simulation.md` | - LevelControllerRule ：液位常用比例控制，Integral time 9999 min；液位升高时采出阀增大则正作用。 |
| `RatioCascadeRule` | `ch14_dynamic_simulation.md` | - RatioCascadeRule ：比值控制输出接下游控制器远程设定值，下游需 `Cascade`。 |
| `DeadTimeGate` | `ch14_dynamic_simulation.md` | - DeadTimeGate ：先初始化控制器，再插入死区时间；闭环调谐需要死区时间元件。 |
| `ReactorTemperatureByDuty` | `ch14_dynamic_simulation.md` | - ReactorTemperatureByDuty ：`Constant duty`，TC 输出热负荷，响应较快。 |
| `ReactorTemperatureByMediumTemperature` | `ch14_dynamic_simulation.md` | - ReactorTemperatureByMediumTemperature ：`Constant temperature`，TC 输出 `T_med`，反作用。 |
| `ReactorTemperatureByMediumFlow` | `ch14_dynamic_simulation.md` | - ReactorTemperatureByMediumFlow ：`LMTD`，TC 输出 `Fl_med`，正作用，更接近生产但响应较慢。 |
| `DistillationSensitiveTrayCriteria` | `ch14_dynamic_simulation.md` | - DistillationSensitiveTrayCriteria ：斜率、灵敏度、SVD、恒温、最小纯度变化。 |
| `DistillationTemperatureControl` | `ch14_dynamic_simulation.md` | - DistillationTemperatureControl ：第46板温度、再沸器热负荷、1 min 死区、继电反馈调谐。 |
| `DistillationCompositionControl` | `ch14_dynamic_simulation.md` | - DistillationCompositionControl ：塔顶苯乙烯质量纯度、再沸器负荷、3 min 死区、调节慢于温度控制。 |
| `DWCControlStructure` | `ch14_dynamic_simulation.md` | - DWCControlStructure ：预分馏塔/主塔压力液位流量、液相分离比、TC5/TC14/TC20。 |
| `DynamicDisturbanceTest` | `ch14_dynamic_simulation.md` | - DynamicDisturbanceTest ：设置 `Pause At`，引入进料量或组成扰动，观察产品纯度/流量恢复。 |
| `CH15_TOOL_ACTIVATED_ENERGY` | `ch15_appendices_tools.md` | - CH15_TOOL_ACTIVATED_ENERGY \| 工具 \| Activated Energy Analysis \| 用于能量分析、节能潜力、改造方案生成、公用工程/温室气体目标对比 \| 入口：`Home\|Activated Analysis\|Activated Energy Analysis` \| 来源：PDF p560-p563。 |
| `CH15_PRECONV_RUN_REQUIRED` | `ch15_appendices_tools.md` | - CH15_PRECONV_RUN_REQUIRED \| 门禁 \| 运行收敛前不得分析 \| Activated Energy Analysis、Column Analysis 均以 `Run` 后收敛为前提 \| 来源：PDF p560-p565。 |
| `CH15_UTILITY_CREATE_BIND` | `ch15_appendices_tools.md` | - CH15_UTILITY_CREATE_BIND \| 操作 \| 创建并绑定公用工程 \| `Utilities\|New...` 创建 `U-1 Cooling Water`、`U-2 HP Steam`；设备页 `Input\|Utility` 绑定 \| 来源：PDF p560-p561。 |
| `CH15_ENERGY_GENERATE_SCENARIOS` | `ch15_appendices_tools.md` | - CH15_ENERGY_GENERATE_SCENARIOS \| 操作 \| 生成改造方案 \| `Generate` 可生成 `Modify Exchangers`、`Add Exchangers`、`Relocate Exchangers` \| 来源：PDF p562-p563。 |
| `CH15_ENERGY_COMPARE_SCENARIOS` | `ch15_appendices_tools.md` | - CH15_ENERGY_COMPARE_SCENARIOS \| 操作 \| 比较方案 \| `Home\|Compare Scenarios` \| 来源：PDF p564。 |
| `CH15_ENERGY_APPLY_ADD_E100` | `ch15_appendices_tools.md` | - CH15_ENERGY_APPLY_ADD_E100 \| 操作 \| 应用新增换热器方案 \| 查看 `Location of new heat exchanger`，在流程中添加 `HeatX\|GEN-HS` 并设置 `E-100` \| 来源：PDF p564-p565。 |
| `CH15_ENERGY_ANALYZER_DETAILS` | `ch15_appendices_tools.md` | - CH15_ENERGY_ANALYZER_DETAILS \| 结果工具 \| Aspen Energy Analyzer \| `Home\|Details` -> `Yes`；查看组合曲线、Targets、Pinch Temperatures、网格图 \| 来源：PDF p565-p566。 |
| `CH15_EDR_RIGOROUS_EXCHANGER` | `ch15_appendices_tools.md` | - CH15_EDR_RIGOROUS_EXCHANGER \| 工具 \| Activated Exchanger Analysis/EDR \| `Convert` -> `Size Exchanger` -> `Accept Design` -> `Overall Heat Trans. Coeff Method=Simulation` \| 来源：PDF p566-p568。 |
| `CH15_PINCH_STREAM_FILTER` | `ch15_appendices_tools.md` | - CH15_PINCH_STREAM_FILTER \| 结果工具 \| 夹点物流筛选 \| 查看夹点之上、夹点之下、跨越夹点的物流 \| 来源：PDF p568。 |
| `CH15_TOOL_COLUMN_ANALYSIS` | `ch15_appendices_tools.md` | - CH15_TOOL_COLUMN_ANALYSIS \| 工具 \| Column Analysis \| Aspen Plus 9.0 RadFrac 塔水力学分析，用于塔内件设计 \| 来源：PDF p569。 |
| `CH15_COLUMN_FLOW_RATE_PLOT` | `ch15_appendices_tools.md` | - CH15_COLUMN_FLOW_RATE_PLOT \| 图表 \| 气液质量流量分布 \| `Blocks\|RADFRAC\|Results` -> `Column Design\|Plot\|Flow Rate` \| 来源：PDF p569-p570。 |
| `CH15_COLUMN_GENERATE_HYD_DATA` | `ch15_appendices_tools.md` | - CH15_COLUMN_GENERATE_HYD_DATA \| 操作 \| 生成水力学数据 \| `Specification\|Setup\|Configuration` -> `Design and specify column internals` -> `Generate` \| 来源：PDF p570。 |
| `CH15_COLUMN_AUTO_SECTION` | `ch15_appendices_tools.md` | - CH15_COLUMN_AUTO_SECTION \| 操作 \| 按流量分段 \| `Auto Section\|Based on Flows`，示例分为 `CS-1`、`CS-2` \| 来源：PDF p570-p571。 |
| `CH15_COLUMN_DESIGN_PARAMETERS` | `ch15_appendices_tools.md` | - CH15_COLUMN_DESIGN_PARAMETERS \| 参数组 \| 塔板设计参数 \| Jet flood、downcomer backup、entrainment、weir loading、pressure drop、foaming factor 等 \| 来源：PDF p571-p572。 |
| `CH15_COLUMN_HYDRAULIC_PLOTS` | `ch15_appendices_tools.md` | - CH15_COLUMN_HYDRAULIC_PLOTS \| 图表 \| 水力学操作区图 \| 查看操作点是否在适宜操作区，边界包括液泛、夹带、堰负荷、漏液 \| 来源：PDF p570-p574。 |
| `CH15_COLUMN_WARNING_GATE` | `ch15_appendices_tools.md` | - CH15_COLUMN_WARNING_GATE \| 门禁 \| 水力学警告处理 \| 若接近 `maximum 85% jet flood limit`，需调整塔径并复查 \| 来源：PDF p572-p574。 |
| `CH15_COLUMN_PRESSURE_PROFILE` | `ch15_appendices_tools.md` | - CH15_COLUMN_PRESSURE_PROFILE \| 图表 \| 压力分布图 \| `Blocks\|RADFRAC\|Profiles` -> `Plot\|Pressure` \| 来源：PDF p573-p575。 |
| `CH15_COLUMN_PRESSURE_DROP_UPDATE` | `ch15_appendices_tools.md` | - CH15_COLUMN_PRESSURE_DROP_UPDATE \| 操作 \| 压降更新模式 \| `Don't update pressure drop`、`Update pressure drop from top stage`、`Update pressure drop from bottom stage` \| 来源：PDF p573-p575。 |
| `CH15_COLUMN_HYD_RESULTS` | `ch15_appendices_tools.md` | - CH15_COLUMN_HYD_RESULTS \| 结果页 \| 塔内件水力学结果 \| `Column Hydraulic Results`；示例全塔压降 `0.414761 bar`、液泛分率小于 `80%` \| 来源：PDF p575-p576。 |
| `CH15_TOOL_CUP_TOWER` | `ch15_appendices_tools.md` | - CH15_TOOL_CUP_TOWER \| 外部工具 \| CUP-Tower \| 塔内件水力学设计/校核，支持板式塔、填料塔、萃取塔等 \| 来源：PDF p576。 |
| `CH15_CUP_DESIGN_VS_RATING` | `ch15_appendices_tools.md` | - CH15_CUP_DESIGN_VS_RATING \| 门禁 \| 新塔设计/旧塔校核输入不同 \| 校核旧塔需完整塔内件结构参数 \| 来源：PDF p576。 |
| `CH15_CUP_REPORT_EXPORT` | `ch15_appendices_tools.md` | - CH15_CUP_REPORT_EXPORT \| 结果工具 \| Excel/Word 报表 \| CUP-Tower 内置结果输出模板 \| 来源：PDF p577。 |
| `CH15_CUP_LOAD_PERFORMANCE` | `ch15_appendices_tools.md` | - CH15_CUP_LOAD_PERFORMANCE \| 图表 \| 负荷性能图 \| 操作线、上下限、漏液线、夹带线、液泛线；横液相流量，纵气相流量 \| 来源：PDF p577-p578。 |
| `CH15_CUP_ASPEN_IMPORT` | `ch15_appendices_tools.md` | - CH15_CUP_ASPEN_IMPORT \| 操作 \| Aspen 水力学数据导入 CUP-Tower \| 从 `Profiles\|Hydraulics` 复制到 Excel，删两列，另存 `Tray.xls`，选最大气液负荷理论板导入 \| 来源：PDF p578-p579。 |
| `CH15_CUP_METCBAR_GATE` | `ch15_appendices_tools.md` | - CH15_CUP_METCBAR_GATE \| 门禁 \| CUP-Tower 导入单位制 \| 建议 `METCBAR`：`KG/HR`、`M3/HR`、`KG/M3`、`DYNE/CM`、`CP` \| 来源：PDF p578。 |
| `CH15_PROPERTY_ANALYSIS_ABSENT` | `ch15_appendices_tools.md` | - CH15_PROPERTY_ANALYSIS_ABSENT \| 边界节点 \| 本 chunk 未展开物性分析工具 \| 不得补充讲义外物性分析曲线、参数或入口 \| 来源：PDF p559-p581。 |

Total nodes: 390

