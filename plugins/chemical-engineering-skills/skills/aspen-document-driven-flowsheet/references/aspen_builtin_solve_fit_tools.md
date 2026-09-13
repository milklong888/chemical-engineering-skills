# Aspen Built-In Solve And Fit Tools

Use this reference when an Aspen task starts to look like manual parameter
hunting. The purpose is to reduce trial count while leaving an exported,
auditable trail. Built-in tools do not fix wrong chemistry, topology, property
method, pressure equipment, or source-unit conversion.

## 先按问题选工具，再实施卡片

这份文件是工具选择与插入时机的详细规则唯一入口。即使用户没有说工具名称，
只要要调参、找工况、匹配指标、研究响应或让参数随进料改变，就先完成下面的
分类。专业Skill负责理解问题，操作Skill负责查当前版本字段并真正建立、运行、
导出工具；两者不能由一个叫“sensitivity”的外部函数名称代替。

使用运行根的 `tools/expert_cli.py --schema solve-route` 发现输入，调用
`solve_route`，或同一实现的 MCP `aspen_solve_route`。独立查数不需要全流程
阶段检查和设备清单；流程阶段入口会同时给出工具路由。自然语言匹配只是有限
提示，主代理必须根据实际目标确认 intents；没有命中不表示工具不适用。
显式 `intents` 是调用者自己的分类，`finite_hints` 才是程序的词面提示。
只有目标匹配而无优选目标函数时不添加 `optimize`；变量多不改变这个条件。
候选包含 `optimize` 时，须按当前真实目标提供 `objective.definition`（优化什么）
与 `objective.direction`（`minimize` 或 `maximize`）；阶段请求使用
`solve_request.objective`。缺任一项只返回分类待核，不选定 Optimization。
这个声明不替代目标的项目来源、用户范围、量纲、可行性或真实执行证据；不能为
通过路由编造目标。纯读值、匹配目标等任务无需该字段，也不由它自动增加优化意图。
发现自己传错意图时，保留原回执并按已澄清问题重新调用，不能只在答复中否定
旧路由或把自己传入的意图解释为程序误识别。未知/冲突状态与阶段状态分别报告。
`AGENT_CLASSIFICATION_REQUIRED` 时 `routes` 为空，`pending_route_intents` 仅是
待判断候选；它们不能写成已选路线。否定句、背景或引用里的词也可能命中有限
规则。核对原意后，用准确的当前任务描述重述并重调，保留原请求和未决回执；
不能为获得绿灯删去真实目标。仍无法消除的歧义如实列出，不阻断无关检查。
阶段回执的 `solve_route.status=EXECUTED` 只证明调用发生，路由结论应读
`solve_route.result.status`，字段层次见[阶段调用](../../chemical-engineering-expert/references/DESIGN_STAGE_ROUTING.md)。
路由收据证明分类与待办，不证明已经插入或运行 Aspen 工具。返回的
`decision_chain` 给出按当前问题裁剪的下一步与结果反馈触发，实际应用这些
判断由专业agent负责，不是程序已经理解或执行了工程分析。

## 从工程问题触发下一步

调参前先说明：**研究什么、什么保持不变、哪些操作量需要联动、用什么结果
判断优劣**。从当前资料直接确认，只有会改变方案且无法自行判明的歧义才问用户。
“控制变量缺失”先按物理控制关系理解；明确关系后，再检查界面槽位、节点和卡片。

1. **辨明问题。** 读值、一次推导、显式实时关系、未知响应、目标闭合与约束
   优化是不同任务。简单查值不走下面的研究链，不为一次算数建立 Calculator。
2. **定比较基准。** 固定操作设置看响应，可以保留设定、让产品随研究变量变化；
   同产品要求下比能耗/成本，则逐点重解必要的授权内层控制，或证明目标自然满足。
   不能算固定控制响应却宣称同产品最优；也不能把“至少达标”擅自改成精确等式。
3. **先推导再找范围。** 从当前可行基准、守恒或条件明确的代数关系构造初值；
   复用未失效区间，未知响应才做有界稀疏 Sensitivity。初值不得永久锁住真实自由度，
   也不能把旧案数值、跨不同支路/相态的类比当新工况输入。
4. **把目标配到可用操纵量。** 核对研究变量、保持条件、控制目标、内层操纵量，
   审查自由度、耦合与主写入者。显式关系用 Calculator，隐式达标用 Design Spec，
   响应分析用 Sensitivity，可行基准上的约束优选评估 Optimization；可组合，不全开。
5. **到实现层核实。** 读取现有操作节点，核对当前版本的对象与变量；查不到旧导出
   只表示该证据缺失，不证明软件不支持，也不自动授权转成外部逐点求解。
6. **用结果决定下一步。** 控制量看似不变，先核对同轮读写、残差和求解状态；
   局部指标改善却破坏必需产品/设备/物理约束，回查目标和下游而非只扩大边界。
   优选点靠近失败边界时，先区分物理与数值原因，再有目的细化；只声明实际采样范围。
7. **收回选定工况。** 保留分析定义、结果和失败点，恢复选定参数并说明分析启停状态，
   避免交付模型停在最后扫描点。按任务范围复验，不能以分析完成替代工程交付。

进料、物性、相态、连接或控制基准改变时，沿依赖关系重查受影响的区间、控制和
结果；未受影响的有效证据可复用。这个次序服务判断，不是强制逐项重建整厂。

需要记录研究基准时，可在 `solve_route` 的 `study_context` 或阶段请求的
`solve_request.study_context` 提供：`mode`（`fixed_controls`、`same_targets`
或 `unspecified`）、`varied_variables`、`fixed_conditions`、`maintained_targets`、
`inner_controls`。列表填写当前合同中的量与条件，不填旧例子数值；这些只是声明，
不证明单位、独立自由度、控制执行或工程通过。缺项只提示相关研究需要核对；目标
本来即可满足时，允许核实无需额外控制，不为填满列表强造控制器。

## 工具选择表

| 用户实际要做什么（示例，不要求原词） | 首选路径与插入时机 | 不能混淆的边界 |
| --- | --- | --- |
| “读一下这股物流的焓”“某板温度是多少”“查询特殊值” | 先读当前有效结果、块/物流表或已核实的数据树；需要额外物性时查版本支持的 Property Analysis/物性集 | 读取不改模型、不为查数加控制器。结果缺失或已失效才安排授权的计算；未给定组成、温压或相态只影响相应查询。 |
| “把这些量换算一下”“由现有数据算一个比值” | 确定性代数、单位换算或结果表达式；一次性计算可在外部完成 | 一次算数不必插 Calculator。若该比值要在每个扫描点输出，可作为分析工具的表达式/Tabulate；确需中间计算才加只读计算器。 |
| “进料变了，补水/补氢/溶剂也要自动跟着变” | 已知且有据的显式关系用 Calculator；读取上游本轮有效量后、下游消费者之前执行 | 不用冻结的旧结果代替实时读值；夹限后未满足原关系须报告，不能把夹限写成目标达成。 |
| “看看变化规律、可行范围、阈值或峰值”“多变量复杂调参但目标还不清楚” | 基准可运行后，用原生 Sensitivity 做有界、稀疏的响应分析；高维先筛主要变量，避免组合爆炸 | 保留失败点。离散峰值只是采样最优，不是连续或全局最优；先明确要分析响应还是解方程/优化。 |
| “找到刚好达到某纯度的回流比”“匹配特定值”“热负荷相等时是什么工况” | 先定义带单位的目标残差和真实自由度；无有效区间/响应证据时先 Sensitivity，之后原生 Design Spec/Vary | 已有同版、同物性、同边界的有效区间可直接复用；至少/不超过是约束，不自动改成等式。一个变量不能由两个独立目标争用。 |
| “几个参数一起调，满足产品要求时能耗/成本最低” | 可行基准上优先评估原生 Optimization，明确连续设计变量、目标函数和约束；必要内层 Design Specs 随每个外层点重解 | 多变量本身不是外部 Python/GA 的理由。不得把一个参考点的质量控制值固定到所有点；局部收敛不声称全局最优。 |
| “比较几种流程、不同台数、多个相态分支或黑箱目标” | 有来源的离散方案可在外层编排；每个固定方案内部仍按本表选择原生分析/求解 | 不把整数级数、进料板或台数当成未说明的连续变量；外层编排不是原生 Sensitivity。 |
| “由实验数据拟合参数” | 授权且有可辨识原始数据时走 Regression/Data-Fit/物性回归 | 这不是为了收敛去改已冻结动力学或物性。没有数据不能拟合出项目事实。 |
| “一直不收敛”“变量到上限了但值没动” | 先读本轮报错、有效输入、变量映射、单位、自由度和执行顺序；进入修复工作流 | 物性、缺输入、错误节点或不合理拓扑不能靠堆 Calculator、加迭代次数或反复搜索掩盖。 |

多个目标同时匹配时，先列目标—操纵量对应关系，检查独立自由度、耦合方向、
量纲和可行区间，再按版本支持选择多条 Design Specs/相应联立求解或约束优化。
不能把强耦合问题拆成互相覆盖的外部单变量循环；也不能因为目标数多，就把
尚未定义的目标函数称为“优化”。已知关系能直接消元时先简化问题。

## Calculator 在什么时刻插入

在骨架阶段就能确定的物料比、补料和库存关系，应在依赖它们的单元正式试算前
建立，不等批量失败以后再补。只依赖独立进料的关系可前馈计算；依赖回流闭合
值的关系须进入正确的循环/收敛顺序，每轮使用当前回流基准，不能声称第一次
顺序执行已得到最终闭合值。纯统计指标在其所有生产者计算后执行，通常不写模型。

建卡前列明“读什么、算什么、写哪里、谁先算、谁后用、谁还会写这个变量”。
每个操纵节点只有一个主写入者。Calculator 可以计算 Design Spec 的目标、
初值或边界，但不能在迭代中反复覆盖 Design Spec 正在求解的同一个操纵量。
若初值只应初始化一次，必须明确初始化范围，不能误设为每轮强制写值。
公式循环依赖要先判断是否应改为 Design Spec/收敛循环，不用任意执行顺序隐藏。

几何随流量缩放只适用于授权的设计定尺寸任务；固定设备能力测试保持几何不变。
改了进料、相态、单位基准、控制对象或连接后，重新核对依赖链、边界和写入值，
并用改变前后至少两个有区分度的当前工况检查响应。复用模板的核心自适应关系
必须保存在交付模型中，不能仅存在外部批处理脚本。

## 怎么实施，怎样才算用了原生工具

先确认现有对象/结果是否已经满足目标，避免重复建卡。工具选择完成后，进入
`aspen-plus-operations/references/operation_graph.md` 对应的 calculator、
sensitivity、design-spec 或 optimization-regression 节点，查询本机合法帮助
或已核实图谱。先在受保护候选验证当前版本字段与单位，再通过既有 COM/脚本
路径建卡、运行、导出。不知道路径时先探测；不先写外部数值循环碰碰运气。

程序化配置原生工具、一次启动原生批量分析、收集结果和比较离散方案，都是正常
自动化。所谓“内置优先”不是禁止 Python，而是把适合原生求解的数学任务交给
原生对象执行。随包 MCP 的 `sensitivity` 是外部逐点 SetValue/Run 循环，
`linked_params` 是比例联动，不是内层 Design Spec；必须标为外部扫描。
通用 get/set/RunScript 只是底层通道，不等于已有验证过的原生对象创建接口。

| 工具 | 必须留下的同案证据 |
| --- | --- |
| 读取/一次推导 | 当前结果身份、变量路径/表列、单位和公式；没有执行过的计算不能报新结果 |
| Calculator | 公式、读写变量/单位、执行顺序、实际写入值；交付导出中保留对应对象 |
| Sensitivity | 实际原生对象及 Vary/Tabulate 定义、范围、同次分析结果表与失败点 |
| Design Spec/Vary | 实际对象或塔内 SPEC/VARY 配对、目标/容差、独立操纵量/边界、最终残差与状态 |
| Optimization | 实际原生对象、目标/约束/变量、算法终止状态、最终点和邻域比较范围；内层目标保持同一基准 |
| 回归 | 数据来源、单位/权重、参数边界、残差/验证集与适用范围、导出参数 |

卡片字样、调用返回成功、路由收据和哈希都不单独证明工具执行成功。目标求解
与优化完成后，回到同版产品、物料能量、压力和设备反馈；有工程接受声明时再
执行原有严格软件验收。Sensitivity 的失败样本是诊断证据，不是可交付成功点；
保留分析定义和结果，并说明分析启停状态，不能为了清洁报告删除失败记录。

## Tool Selection (detailed scope)

- `CALCULATOR`: Use for derived variables, stream-dependent estimates,
  stoichiometric links, reaction-parameter relationships, feed-forward
  calculations, inventory-based product draws, and recycle-quality indicators
  that must update inside Aspen. Audit `DEFINE`, `READ-VARS`, `WRITE-VARS`,
  `EXECUTE BEFORE/AFTER`, and convergence order.
- `SENSITIVITY`: Use before dense sweeps. Map feasibility windows for physical
  variables such as reactor length, reactor volume, residence time, temperature,
  pressure, feed ratio, reflux, stages, side draw, solvent rate, purge, flash
  temperature, or condenser duty. Promote only settings that pass the full
  downstream hard gate, not only the local metric.
- `DESIGN-SPEC`: Use when one scalar target can be met by one meaningful
  manipulated variable, such as product concentration by reflux or draw,
  reactor conversion by length or volume, recycle impurity by purge, or outlet
  temperature by duty. Set physical lower/upper bounds.
- `OPTIMIZATION`: Use after a feasible model exists and the goal is an objective
  with constraints, such as minimum utility at product/recycle specs or maximum
  recovery under purity and pressure limits. Do not use it to fix wrong topology.
- `REGRESSION` / Data-Fit: Use for kinetic or model-parameter fitting from
  primary conversion, selectivity, concentration, time, or reactor-profile data.
  Vary only identifiable parameters and report fitted values, bounds, residuals,
  and validity range.
- Property Data Regression: Use for NRTL/UNIQUAC/EOS/BIP fitting from VLE, LLE,
  pure-property, or mixture-property data. ThermoML/NIST files are regression
  candidates, not Aspen-ready BIP cards until regressed, residual-checked, and
  exported.
- External Python/GA/NSGA-II loop: Use only after the Aspen base case converges,
  variable bounds are sourced, failed runs are captured, and Aspen
  `SENSITIVITY`/`DESIGN-SPEC`/`OPTIMIZATION` cannot cover the search need.
  Treat external optimizers as search aids; they are not promotion evidence
  unless each candidate records inputs, convergence status, warnings/errors,
  objective components, and downstream hard-gate results. Promote an external
  result only after the selected point is rerun inside Aspen, exported, and
  audited against the same gates as a built-in solve/fit result.

## Common Trigger Graph

Use this as a symptom-to-tool map. Aspen's sequential modular tools interact
with convergence order: Design Specs introduce manipulated variables into
convergence, and Calculator blocks import/export flowsheet variables at a
defined execution point. Therefore every trigger below also needs exported-card
and same-run evidence.

| Symptom Or Intent | First Tool To Consider | Manipulated Or Written Variable | Required Audit |
| --- | --- | --- | --- |
| A product draw must track available key-component feed inventory | `CALCULATOR`, then optional `DESIGN-SPEC` | Draw estimate, recovery target, or bounded initial spec | Read feed stream, write draw/target before the column, prove draw is below inventory |
| Tower target is a concentration, mass fraction, mole fraction, or recovery | Valid current bracket or native `SENSITIVITY`, then `DESIGN-SPEC` | Authorized reflux/draw/solvent rate; discrete feed stages in a separate scenario | Feasible bracket, concentration residual, current-feed inventory, clean column status |
| Reactor must hit conversion/selectivity by changing equipment or operation | Valid current bracket or native `SENSITIVITY`, then `DESIGN-SPEC` or `OPTIMIZATION` | Continuous physical geometry/operation; integer reactor counts as discrete candidates | Target ledger, physical bounds, kinetic-unit audit, downstream gates |
| Recycle impurity, purge, or solvent return quality controls full-flow closure | `CALCULATOR` for indicators; `DESIGN-SPEC` for scalar target | Purge fraction, recycle split, solvent makeup, regeneration draw | Loop topology, contaminant balance, pressure/phase compatibility, terminal gates |
| Heat duty, outlet temperature, or heat-integration match is the scalar target | `DESIGN-SPEC`; `OPTIMIZATION` for utility objective | Heater/HEATX duty, approach, stream split, compressor ratio | Energy balance, pressure equipment, utility feasibility, downstream product gates |
| Feed ratio, stoichiometric ratio, or makeup rate depends on live stream results | `CALCULATOR` | Feed, makeup, split, or stream-dependent set point | `READ-VARS`/`WRITE-VARS`, execution before consuming block, no circular stale value |
| A user or rubric asks for optimum yield, energy, solvent loss, or economics | `OPTIMIZATION` after feasible model | Real design/operation variables with constraints | Objective components, bounds, active constraints, no broken product/recycle gates |
| Kinetic, property, or BIP parameters must be fitted from data | Regression/Data-Fit or Property Data Regression | Identifiable model parameters | Primary data, units, weights, residuals, exported fitted cards, validity range |
| Manual sweeps are repeating without moving the hard gate | Native `SENSITIVITY` or blocker reclassification | Screen the main physical variables first; one or two is a small-probe recommendation, not a software limit | Stop condition, bad-run matrix, branch status, next missing island or property check |

Do not use Calculator to hide an impossible separation, and do not use Design
Spec to vary a variable already fixed by another card. When the trigger is only
"make the number look right," first rebuild the source target, feed inventory,
and physical degree of freedom.

## Default Sequence

1. Fix topology, components, property method, pressure equipment, and unit/card
   conversion before using any built-in solver.
   Property method means module-specific, not merely a global Aspen default:
   identify the reactor, gas-cleanup, solvent, hydrocarbon, azeotropic,
   extractive, aqueous, and compression/recycle sections that see different
   component families, phase behavior, pressure/temperature windows, or
   nonideality. For each changed module, run a small property or island probe
   before reconnecting it, then rerun the full case and bind the final evidence
   to that same run family.
2. For reactor retuning or low product/feed ratio, write a scorecard before the
   next run: target conversion/selectivity window, limiting material balance,
   current conversion, variables and bounds, built-in tool route, downstream
   gates, and economic stop.
3. If the scorecard implies unexpected reactor dimensions or space times, insert
   a kinetics-unit audit before stretching length, volume, or residence time.
4. Use `CALCULATOR` only for auditable relationships that must update with the
   run. Keep the calculation small and name every read/write variable.
5. Run coarse native `SENSITIVITY` when the response or feasible bracket is
   unknown. Reuse a still-valid same-case bracket instead of repeating a sweep.
6. Use `DESIGN-SPEC` for a bounded scalar target only after feasibility is
   bracketed and the manipulated variable is a real design or operating degree
   of freedom.
7. Use `OPTIMIZATION` only after the model converges near a feasible region.
8. Use `REGRESSION` when the unknown is a model parameter and primary data exist.
9. Use external search only with a recorded, specific native-tool applicability
   or capability gap (or an explicit user-required method), not merely because
   several variables exist. Preserve the native-solver assessment and the
   product, energy, pressure, feed, and downstream constraints.
10. Export `*_after_run.inp`, block status, stream results, and any tool result
    tables or residual reports before promotion.
11. For reactor conversion retuning, make solve/fit evidence a promotion gate. A
    single back-substituted point without a retained, completed Sensitivity,
    Design Spec, Optimization, Regression, or equivalent auditable tool record
    remains diagnostic even if conversion and product purity pass.

## Reactor Replacement Chain

Use this chain whenever a yield or stoichiometric reactor is being replaced by a
kinetic reactor, or when reactor conversion is the named blocker:

1. Look up a target conversion/selectivity window from the current documents and
   rough external industrial, literature, patent, or public-project anchors.
2. Build or preserve a yield/stoichiometric scaffold only as a topology and
   material-balance baseline. Label it provisional.
3. Audit the original full-flow case: total feed, reactor inlet/outlet flows,
   per-reactor conversion, selectivity if available, product rates, recovery or
   sale streams, purges, vents, and wastewater.
4. Replace the reactor as an isolated kinetic island first. Verify reaction-set
   binding, phase, sizing basis, temperature/pressure, and exported cards.
5. Reuse a still-valid current response bracket or use native `SENSITIVITY`
   before `DESIGN-SPEC` to vary a physical parameter such as
   length, volume, residence time, temperature, pressure, feed ratio, or catalyst
   amount. If the source supports CSTR behavior better than plug flow, use CSTR
   volume or a CSTR-series variable and explain the selection basis.
6. Back-substitute the kinetic island into the full flow without deleting the
   solve/fit cards or result evidence.
7. Recompute downstream gates from the same run family: product purity and rate,
   recycle quality, pressure, temperature, terminal boundaries, warnings,
   block status, and material balance.
8. Keep the solve/fit tool in the promoted full-flow case. If Aspen cannot retain
   the intended Design Spec syntax, retain the completed Sensitivity or
   equivalent audited external bracketing evidence and state the limitation.

## Calculator Plus Design Spec Gate

Promotion requires a dependency chain, not just a clean-looking product stream:

- Calculator purpose and formulas.
- Calculator read variables, write variables, execution point, and convergence
  order.
- Design Spec target, target units, manipulated variable, bounds, and independent
  degree of freedom.
- Proof the manipulated variable is not also frozen by a Calculator, fixed draw,
  or stale template value.
- Exported `CALCULATOR`, `DESIGN-SPEC`, `VARY`, `READ-VARS`, `WRITE-VARS`, and
  `EXECUTE` cards.
- Final residual/status plus latest stream and block evidence.
- Downstream gates after the Design Spec run, not from an older branch.

A pure-looking product from a nonconverged block or stale Calculator value fails
the solve/fit gate.

If the target is a minimum such as "at least this purity" and the stream already
exceeds it, an equality Design Spec can create a false failure by pushing the
manipulated variable outside physical bounds. Do not delete a live Calculator
that computes a real feed-inventory draw or makeup just to make the Design Spec
disappear. Instead, prove whether the Calculator is needed, remove duplicate
control of the same variable, and promote only with an explicit external
minimum-purity audit plus clean block, stream, terminal, and temperature gates.

## Distillation And Concentration Targets

- For high-purity or concentration targets, use true staged continuation:
  promote each tighter target only from the latest clean after-run.
- Before optimizing a tower or special separation, freeze its local property
  method and property-data status for the actual feed family. Check VLE/LLE,
  azeotrope or entrainer behavior, relative volatility, solubility, and binary
  parameter warnings in an isolated column or property probe. If the local
  method changes, all old reflux, duty, draw, feed-stage, solvent-rate, and
  Design Spec evidence is diagnostic until the changed island and the final full
  flow are rerun.
- Formulate tower specs around component concentration, recovery, reflux, boilup,
  product draw, bottoms draw, side draw, solvent rate, or feed stage as the
  physical separation requires.
- Bound product draws by latest feed inventory. Fixed product-rate values from
  older islands are not reusable after reactor, recycle, or solvent-loop changes.
- If a lower target converges but the accepted target fails after true staging,
  stop blind reflux/iteration sweeps and repair property method, BIP data,
  solvent/entrainer mapping, feed-stage placement, or manipulated-variable
  formulation.
- A tower that meets a concentration number while drying up the feed, starving a
  downstream column, or carrying block warnings is diagnostic only.

## Guardrails

- A built-in tool result is not evidence unless the exported input preserves the
  intended cards.
- Do not fit more free parameters than the data can identify.
- Do not manipulate kinetic constants, split fractions, or product rates that
  should be fixed by equipment design unless that is the actual design variable.
- Reject a Design Spec or Optimization solution that sits on an absurd bound or
  breaks recycle/product hard gates.
- Treat Calculator dependencies as part of convergence topology; a wrong
  execution point can create stale or circular values.
- Keep source-unit and Aspen-card ledgers for all fitted or calculated values.
- For `RPLUG` or tube-reactor optimization, do not vary length, diameter, tube
  count, `L/D`, volume, or residence time as anonymous knobs. Record physical
  meaning, equipment bounds, source basis, and exported input card.
- Before promoting a long `RPLUG` or reactor Design Spec, verify exported
  kinetic-card units and defaults. Ledger units and Aspen card units may use
  different bases.
- If a source does not authorize the chosen reactor type, label the change as a
  reactor-network candidate or engineering branch. Compare plausible alternatives
  such as CSTR, CSTR series, recycle reactor, or plug-flow before claiming final
  structure.
- Keep side-reaction and selectivity metrics visible, but do not invent hard
  selectivity thresholds. Promote thresholds only when documents, cited data,
  safety constraints, or economic limits define them.
- If meeting conversion alone destroys selectivity, product purity, recycle
  quality, terminal handling, or block status, promote the failure as evidence
  and change the target formulation rather than increasing bounds.

## Local Syntax Templates

Use these as audit templates, not copy-paste Aspen input. Aspen card syntax
varies by version and export style; build the tool in Aspen or through COM,
export the case, then verify the exported cards.

Calculator:

- Useful cards: `CALCULATOR <id>`, `DEFINE`, `READ-VARS`, `WRITE-VARS`,
  `EXECUTE BEFORE BLOCK <id>`, `EXECUTE AFTER BLOCK <id>`, explicit
  convergence order.
- Use as a small no-op probe if syntax is uncertain before applying the
  Calculator to the authority case.

Sensitivity:

- Target: map a feasible window, not force a final answer.
- Manipulated variables: start with the main one or two physical variables for
  an interpretable probe; this is not a native software capability limit.
  Treat discrete counts/stages separately from continuous target variables.
- Bounds: broad enough to bracket the target but capped by feed inventory,
  pressure limits, thermal stability, utility feasibility, and equipment reality.
- Evidence: exported `SENSITIVITY` cards, result table, block status, stream
  results, and downstream hard-gate audit.

Design Spec:

- Target: one scalar residual such as product mass fraction, recovery, recycle
  impurity, reactor conversion, outlet concentration, outlet temperature, or duty
  match.
- Vary: one meaningful variable such as reflux, distillate rate, bottoms rate,
  side draw, solvent rate, heat duty, purge, split fraction, reactor length,
  reactor volume, residence time, or feed ratio.
- Evidence: exported `DESIGN-SPEC`/`VARY` cards, final residual, block status,
  and unchanged downstream hard gates.

RPLUG or reactor probe:

- Target: prove geometry and reaction semantics before full-flow promotion.
- Variables: length, diameter, tube count/equivalent area, residence time,
  temperature profile, pressure, phase, and reaction set.
- Evidence: exported block cards, geometry cards, active reaction set, block
  status, conversion/selectivity calculation, and downstream gates.

Optimization:

- Objective: utility, solvent loss, compressor work, product recovery, or an
  economic proxy.
- Constraints: product purity, conversion, selectivity, recycle quality,
  pressure, temperature, material balance, terminal handling, and equipment
  limits.
- Evidence: exported `OPTIMIZATION` cards, objective value, active constraints,
  variable bounds, and proof that the optimum did not break base hard gates.

Regression/Data-Fit:

- Data: source, units, temperature, pressure, composition basis, and uncertainty
  where available.
- Fit: varied parameters, bounds, weighting, objective residual, and validity
  range.
- Promotion: export fitted cards, rerun the relevant island, and compare product
  and recycle gates before accepting parameters.

## External Targeting Acceptance

External search, Python automation, genetic algorithms, or spreadsheet
optimizers may substitute for a built-in solve/fit trail only when the record
contains:

- Which native tool was assessed, the current version/provider, what specific
  capability or applicability failed, and the supporting help/export/probe
  evidence. A vague reason, an absent MCP wrapper, or a caller's approved=true
  does not establish this. Check the existing COM/script route first.
- Sourced lower/upper bounds and physical meaning for each candidate input.
- Candidate inputs, convergence status, warnings/errors, failed-run handling,
  and objective components for the accepted point and rejected neighbors.
- Product, conversion, selectivity, pressure, recycle, terminal-boundary, and
  material-balance gates evaluated on the same candidate.
- Final Aspen rerun, exported input, block status, stream results, and gate
  audit after applying the selected point.

Without the final Aspen rerun/export/audit, the external result is only a
screening hint.

## 来源与适用范围

上述工具职责与 AspenTech 的 [Process Modeling 课程](https://esupport.aspentech.com/T_course?id=a3p0B000000hWIJQA2)
和 [Flowsheet Convergence 课程](https://esupport.aspentech.com/UniversityCourse?Id=a3p0B0000004YnRQAU)
列出的变量访问、灵敏度分析、设计规定、计算器信息流/执行顺序和 SM Optimization
范围一致。这里的触发顺序是本工作库的工程组织规则，不是厂商保证任意模型收敛。
具体字段、版本支持、算法和可用变量仍以目标机器帮助及同案导出核实；公开课程
不提供项目数值，也不替代软件动态验证。

## Audit Snippets

```powershell
rg -n "^\s*(CALCULATOR|DESIGN-SPEC|SENSITIVITY|OPTIMIZATION|REGRESSION|DATA-SET|PROFILE-DATA)\b|READ-VARS|WRITE-VARS|EXECUTE BEFORE|EXECUTE AFTER|VARY " .\*_after_run.inp

rg -n "REGRESSION|PROFILE-DATA|DATA-SET|LIMITS|RESID|VARY " .\*.inp .\*.out .\*.sum .\*.md .\*.json
```

When reporting a built-in solve/fit result, include target, manipulated
variables or varied parameters, bounds, source data, result status, residuals
when applicable, exported-card evidence, and downstream gate status.
