<!-- generated: aspen_user_guide_v10 -->
# Aspen Plus V10 User Guide Operation Router

Use this router from `aspen-plus-operations` when a mechanical operation needs manual-backed workflow context from the Aspen Plus V10 user guide.

## Routing Rule

1. Identify the operation node from `aspen-plus-operations/references/operation_graph.md`.
2. Open the matching V10 chapter node below for workflow/UI/report/help context.
3. For high-risk card fields, still query `aspen-plus-operations/references/manual_knowledge_graph.json`.
4. Record both evidence families in the operation report, for example `UG10-CH17` plus `design_spec.define_vary`.

## Duplicate Boundary

- This graph does not duplicate the V14 help graph. It is chapter-level and source-extract backed.
- The V14 help graph remains the structured card-field authority.
- The Sun Lanyi graph remains the textbook/lecture pattern authority.
- Project source ledgers and change-offset tables outrank all manual-derived patterns for project values.

## Operation Routes

### `block-stream`

flowsheet drawing, block/stream objects, stream connection, and information transfer

| Chapter Node | Chapter | Pages | Use For |
| --- | --- | --- | --- |
| `UG10-CH01` | 第1章 用户界面 | 3-15 | UI, Data Browser, Next, Control Panel, 主窗口 |
| `UG10-CH02` | 第2章 建立模拟模型 | 16-31 | new simulation, template, components, property method, stream input |
| `UG10-CH04` | 第4章 定义流程 | 36-52 | flowsheet, model library, ports, stream connect, 流程 |
| `UG10-CH09` | 第9章 规定物流 | 130-148 | stream, flash specification, composition, 物流, 温度 |
| `UG10-CH10` | 第10章 单元操作模型 | 149-177 | unit operation, block, heater, column, reactor |
| `UG10-CH14` | 第14章 给工艺流程作注解 | 208-217 | annotation, PFD, text, 注解, 标注 |
| `UG10-CH24` | 第24章 在物流或模块间传递信息 | 359-363 | transfer, information, calculator, 传递信息, 模块间信息 |
| `UG10-CH25` | 第25章 平衡模块 | 364-373 | balance, mass balance, energy balance, 平衡模块, 物料平衡 |
| `UG10-CH34` | 第34章 插入 | 501-504 | insert, object, OLE, 插入, 对象 |
| `UG10-CH35` | 第35章 创建物流库 | 505-509 | stream library, 物流库 |
| `UG10-CH38` | 第38章 使用ASPEN PLUS的ActiveX自动控制服务器 | 545-571 | ActiveX, automation, COM, 自动控制服务器, 脚本 |
### `calculator`

flowsheet variables, information transfer, Balance blocks, and Fortran/Calculator logic

| Chapter Node | Chapter | Pages | Use For |
| --- | --- | --- | --- |
| `UG10-CH18` | 第18章 访问流程变量 | 261-283 | flowsheet variable, variable explorer, access variables, 流程变量, 变量访问 |
| `UG10-CH19` | 第19章 FORTRAN块及内嵌FORTRAN | 284-300 | Fortran, inline Fortran, user model, FORTRAN块, 内嵌FORTRAN |
| `UG10-CH24` | 第24章 在物流或模块间传递信息 | 359-363 | transfer, information, calculator, 传递信息, 模块间信息 |
| `UG10-CH25` | 第25章 平衡模块 | 364-373 | balance, mass balance, energy balance, 平衡模块, 物料平衡 |
### `case-io`

open, create, save, import, export, archive, and automate case files

| Chapter Node | Chapter | Pages | Use For |
| --- | --- | --- | --- |
| `UG10-CH01` | 第1章 用户界面 | 3-15 | UI, Data Browser, Next, Control Panel, 主窗口 |
| `UG10-CH02` | 第2章 建立模拟模型 | 16-31 | new simulation, template, components, property method, stream input |
| `UG10-CH05` | 第5章 计算的全局信息 | 53-68 | setup, global, units, diagnostics, report options |
| `UG10-CH15` | 第15章 管理文件 | 218-224 | file, backup, archive, APW, BKP |
| `UG10-CH16` | 第16章 定制ASPEN PLUS环境 | 225-238 | customize, toolbar, preferences, environment, 定制 |
| `UG10-CH35` | 第35章 创建物流库 | 505-509 | stream library, 物流库 |
| `UG10-CH37` | 第37章 和其他Windows程序协同工作 | 524-544 | Windows, Excel, OLE, clipboard, Windows程序 |
| `UG10-CH38` | 第38章 使用ASPEN PLUS的ActiveX自动控制服务器 | 545-571 | ActiveX, automation, COM, 自动控制服务器, 脚本 |
### `component-property`

component IDs, databanks, physical-property methods, property data, and pseudocomponents

| Chapter Node | Chapter | Pages | Use For |
| --- | --- | --- | --- |
| `UG10-CH02` | 第2章 建立模拟模型 | 16-31 | new simulation, template, components, property method, stream input |
| `UG10-CH06` | 第6章 规定组分 | 69-86 | component, databank, formula, CAS, 组分 |
| `UG10-CH07` | 第7章 物性方法 | 87-102 | property method, base method, NRTL, SRK, 物性方法 |
| `UG10-CH08` | 第8章 物性参数和数据 | 103-129 | binary parameter, databank, property data, parameter, 二元参数 |
| `UG10-CH09` | 第9章 规定物流 | 130-148 | stream, flash specification, composition, 物流, 温度 |
| `UG10-CH23` | 第23章 模拟模型的数据拟合 | 341-358 | data fit, model fit, parameter fit, 数据拟合, 模型拟合 |
| `UG10-CH27` | 第27章 规定反应和化学 | 377-393 | reaction, chemistry, stoichiometry, kinetics, 反应 |
| `UG10-CH28` | 第28章 物性集 | 394-398 | property set, stream property, 物性集, 结果变量 |
| `UG10-CH29` | 第29章 分析物性 | 399-425 | property analysis, phase envelope, binary analysis, 物性分析, 相图 |
| `UG10-CH30` | 第30章 估计物性参数 | 426-443 | estimate property, PCES, group contribution, 估计物性参数 |
| `UG10-CH31` | 第31章 物性数据回归 | 444-464 | property regression, data regression, 物性数据回归 |
| `UG10-CH32` | 第32章 石油分析和虚拟组分 | 465-479 | petroleum, assay, pseudocomponent, 石油分析, 虚拟组分 |
### `delivery-qa`

reports, PFD annotations, file packages, plots, external program exchange, and deliverable checks

| Chapter Node | Chapter | Pages | Use For |
| --- | --- | --- | --- |
| `UG10-CH12` | 第12章 检查结果和生成报告 | 188-194 | results, report, history, 结果, 报告 |
| `UG10-CH13` | 第13章 操作曲线图 | 195-207 | plot, curve, graph, 操作曲线, 绘图 |
| `UG10-CH14` | 第14章 给工艺流程作注解 | 208-217 | annotation, PFD, text, 注解, 标注 |
| `UG10-CH15` | 第15章 管理文件 | 218-224 | file, backup, archive, APW, BKP |
| `UG10-CH19` | 第19章 FORTRAN块及内嵌FORTRAN | 284-300 | Fortran, inline Fortran, user model, FORTRAN块, 内嵌FORTRAN |
| `UG10-CH33` | 第33章 泄压计算 | 480-500 | relief, safety valve, 泄压, 安全阀 |
| `UG10-CH34` | 第34章 插入 | 501-504 | insert, object, OLE, 插入, 对象 |
| `UG10-CH36` | 第36章 物流汇总格式 | 510-523 | stream summary, format, 物流汇总, 格式 |
| `UG10-CH37` | 第37章 和其他Windows程序协同工作 | 524-544 | Windows, Excel, OLE, clipboard, Windows程序 |
### `design-spec`

feedback-control style target/vary operations

| Chapter Node | Chapter | Pages | Use For |
| --- | --- | --- | --- |
| `UG10-CH17` | 第17章 收敛 | 239-260 | convergence, tear, sequence, Broyden, Wegstein |
| `UG10-CH18` | 第18章 访问流程变量 | 261-283 | flowsheet variable, variable explorer, access variables, 流程变量, 变量访问 |
| `UG10-CH21` | 第21章 设计规定：反馈控制 | 309-321 | Design Spec, feedback control, vary, 设计规定, 反馈控制 |
### `equipment-card`

unit-operation model selection and equipment/block input context

| Chapter Node | Chapter | Pages | Use For |
| --- | --- | --- | --- |
| `UG10-CH02` | 第2章 建立模拟模型 | 16-31 | new simulation, template, components, property method, stream input |
| `UG10-CH10` | 第10章 单元操作模型 | 149-177 | unit operation, block, heater, column, reactor |
| `UG10-CH32` | 第32章 石油分析和虚拟组分 | 465-479 | petroleum, assay, pseudocomponent, 石油分析, 虚拟组分 |
| `UG10-CH33` | 第33章 泄压计算 | 480-500 | relief, safety valve, 泄压, 安全阀 |
| `UG10-CH38` | 第38章 使用ASPEN PLUS的ActiveX自动控制服务器 | 545-571 | ActiveX, automation, COM, 自动控制服务器, 脚本 |
### `manual-lookup`

how to use Aspen help as a source before guessing paths or fields

| Chapter Node | Chapter | Pages | Use For |
| --- | --- | --- | --- |
| `UG10-CH03` | 第3章 使用ASPEN PLUS 帮助 | 32-35 | help, context help, search, 帮助, 上下文帮助 |
### `manual-source-boundary`

manual scope and source hierarchy for this graph

| Chapter Node | Chapter | Pages | Use For |
| --- | --- | --- | --- |
| `UG10-CH00` | 前言 | 1-2 | manual scope, volume, support, 手册范围, 技术支持 |
### `optimization-regression`

optimization, model/data fitting, and property-parameter regression

| Chapter Node | Chapter | Pages | Use For |
| --- | --- | --- | --- |
| `UG10-CH08` | 第8章 物性参数和数据 | 103-129 | binary parameter, databank, property data, parameter, 二元参数 |
| `UG10-CH18` | 第18章 访问流程变量 | 261-283 | flowsheet variable, variable explorer, access variables, 流程变量, 变量访问 |
| `UG10-CH22` | 第22章 优化 | 322-340 | Optimization, objective, constraint, 优化, 目标函数 |
| `UG10-CH23` | 第23章 模拟模型的数据拟合 | 341-358 | data fit, model fit, parameter fit, 数据拟合, 模型拟合 |
| `UG10-CH30` | 第30章 估计物性参数 | 426-443 | estimate property, PCES, group contribution, 估计物性参数 |
| `UG10-CH31` | 第31章 物性数据回归 | 444-464 | property regression, data regression, 物性数据回归 |
### `reaction-card`

reaction sets, stoichiometry, chemistry, kinetic/card boundaries, and user models

| Chapter Node | Chapter | Pages | Use For |
| --- | --- | --- | --- |
| `UG10-CH10` | 第10章 单元操作模型 | 149-177 | unit operation, block, heater, column, reactor |
| `UG10-CH19` | 第19章 FORTRAN块及内嵌FORTRAN | 284-300 | Fortran, inline Fortran, user model, FORTRAN块, 内嵌FORTRAN |
| `UG10-CH27` | 第27章 规定反应和化学 | 377-393 | reaction, chemistry, stoichiometry, kinetics, 反应 |
### `run-export`

run sequence, control panel, results, reports, plots, and stream summaries

| Chapter Node | Chapter | Pages | Use For |
| --- | --- | --- | --- |
| `UG10-CH01` | 第1章 用户界面 | 3-15 | UI, Data Browser, Next, Control Panel, 主窗口 |
| `UG10-CH02` | 第2章 建立模拟模型 | 16-31 | new simulation, template, components, property method, stream input |
| `UG10-CH05` | 第5章 计算的全局信息 | 53-68 | setup, global, units, diagnostics, report options |
| `UG10-CH11` | 第11章 运行模拟程序 | 178-187 | run, sequence, control panel, 运行, 计算顺序 |
| `UG10-CH12` | 第12章 检查结果和生成报告 | 188-194 | results, report, history, 结果, 报告 |
| `UG10-CH13` | 第13章 操作曲线图 | 195-207 | plot, curve, graph, 操作曲线, 绘图 |
| `UG10-CH17` | 第17章 收敛 | 239-260 | convergence, tear, sequence, Broyden, Wegstein |
| `UG10-CH26` | 第26章 工况研究 | 374-376 | case study, scenario, 工况研究, 多工况 |
| `UG10-CH28` | 第28章 物性集 | 394-398 | property set, stream property, 物性集, 结果变量 |
| `UG10-CH29` | 第29章 分析物性 | 399-425 | property analysis, phase envelope, binary analysis, 物性分析, 相图 |
| `UG10-CH36` | 第36章 物流汇总格式 | 510-523 | stream summary, format, 物流汇总, 格式 |
| `UG10-CH38` | 第38章 使用ASPEN PLUS的ActiveX自动控制服务器 | 545-571 | ActiveX, automation, COM, 自动控制服务器, 脚本 |
### `sensitivity`

variable scans, convergence bracketing, and case studies

| Chapter Node | Chapter | Pages | Use For |
| --- | --- | --- | --- |
| `UG10-CH17` | 第17章 收敛 | 239-260 | convergence, tear, sequence, Broyden, Wegstein |
| `UG10-CH18` | 第18章 访问流程变量 | 261-283 | flowsheet variable, variable explorer, access variables, 流程变量, 变量访问 |
| `UG10-CH20` | 第20章 灵敏度分析 | 301-308 | Sensitivity, vary, tabulate, 灵敏度, 变量扫描 |
| `UG10-CH26` | 第26章 工况研究 | 374-376 | case study, scenario, 工况研究, 多工况 |
