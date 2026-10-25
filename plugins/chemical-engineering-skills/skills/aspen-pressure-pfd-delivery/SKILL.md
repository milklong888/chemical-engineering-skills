---
name: aspen-pressure-pfd-delivery
description: Audit and repair Aspen Plus full-flow pressure topology, PFD-style documentation, and LaTeX/PDF delivery packages for chemical-design projects. Use when the user mentions Aspen pressure equipment, compressors/pumps/valves, natural high-pressure feeds, HEATER PRES=0, PFD/PDF/LaTeX reports, bkp/apwz generation, or final delivery packaging for Aspen flowsheets.
---

# Aspen Pressure PFD Delivery

## 工作过程

先沿当前流程的真实连接逐段核对压力：入口是什么压力，哪些地方需要泵或压缩机升压，哪些单元产生压降，哪里允许节流。用当前几何、物性和适用计算方法建立压降账本，检查热块是否隐藏升压、循环是否有回流压差，以及串联损失和并联共同压差是否处理正确。

审查具体流程的压力路径或压力设备安排时，按[阶段调用规则](../chemical-engineering-expert/references/DESIGN_STAGE_ROUTING.md)选择当前设计事件的阶段，执行检查或引用仍有效的同阶段回执；“不改模型”只限定实施范围。需要修改时，再由操作模块修改受保护模型和重跑。确认后才同步PFD、设备标签和报告，让图中的顺序、压力和回流路径都来自同版导出。最后检查模型验收、图文一致性和渲染页面；仅修改排版时不无故重算全流程。

## Network Position

Use this as a pressure/PFD overlay under `aspen-document-driven-flowsheet` or a
specialist section/tower workflow. Upstream authority supplies the accepted
case, pressure ledger, allowed pressure-drop convention, and claims to verify.
This skill returns pressure topology evidence, PFD/PDF synchronization evidence,
and any blocked pressure assumptions to the process authority layer. Mechanical
case generation, run/export, and package QA still go through
`aspen-plus-operations` when that skill is available.

## Scope

Use this on an existing process flowsheet, section or tower when its pressure topology or PFD/delivery evidence needs work. A component-only template does not by itself trigger a pressure workflow. Use the relevant document skill for PDF layout when needed. This skill covers hidden pressure changes in heaters, stale `.bkp/.apwz` files, forced sequences causing recycle mass imbalance, and PDF/PFD claims drifting from the actual model.

When the current workspace contains
`aspen_sun_lanyi_knowledge/knowledge_graph/README.md`, read it as a local Aspen
knowledge overlay before pressure/PFD edits. Use `unknowns_router.md` for
pressure, dynamic-export, convergence, and unit-block routing, and use
`kinetics_expert_system.md` before changing any kinetic reactor that also has a
pressure, geometry, or delivery impact. If the pressure/PFD issue resembles a
lecture case such as heat pump distillation, HIDiC, dynamic export, or column
pressure analysis, use `classic_cases_playbook.md` only for transferable
patterns, not example values. Ignore this hook outside that workspace.

## Aspen Editing Rules

- Do not hand-edit `.bkp` or `.apwz` internals. Use the existing operations path on a protected candidate. Regenerate from INP only when that route is authorized and preserves the required graphical/layout authority; do not rebuild an accepted intermediate model merely for a pressure check.
- Freeze each fresh/boundary feed pressure from current source evidence; do not assume natural high pressure or a universal low-pressure value.
- Put pressure changes in explicit equipment:
  - Gas to higher pressure: `COMPR`, with the current pressure target and source-backed efficiency/basis.
  - Liquid to higher pressure: `PUMP`, with the current pressure target and source-backed efficiency.
  - Letdown: `VALVE`, e.g. `PARAM P-DROP=<bar>`.
- Make the thermal block's pressure-drop convention explicit and source-backed. Use `PRES=0` only when the current model/version and authorized no-drop convention call for it; do not conceal a pressure rise in a heater.
- Keep every reactor pressure condition explicit and tied to its current source and accepted pressure ledger; no private-case reactor pressure table is supplied.
- If a closed recycle case breaks after adding pressure equipment, suspect forced `SEQUENCE MASTER` before weakening the process model. Prefer `CHECKSEQ=NO` with a convergence method already proven for the case.

## Pressure Audit Checklist

### 仅文字规划时也交出方法和关系

从接收端所需压力沿实际连接倒查，把可用压差、设备/管路损失、增压和有用途的
降压分别写清。缺尺寸/流量时先交符号关系与每个变量的单位、已知来源或最小缺口，
不是只列“以后算压降”，也不填无据范围。液体关系须区分静压、高差、速度变化和
不可逆损失；热设备两侧各算各的流动损失。气体、两相和浆料不能强套清水式。

从工作区链接表定位已安装runtime，运行
`tools/expert_cli.py --schema pressure-methods`读当前签名和适用域，再通过原
`operation=pressure`或阶段`pressure_checks`计算。当前原实现
`backends/process/pressure.py`可复用：

| 情形 | 原方法与边界 |
|---|---|
| 等径、恒密度牛顿液体管路 | `liquid_pipe_loss`：Darcy–Weisbach摩擦/局部损失与静压高差分开；需要ρ、μ、流量、D、L、局部K和高差，湍流还需有据Darcy摩阻因子。不混用Fanning因子，不自动扩展到浆料/两相/气体。 |
| 已知各损失的串联路径 | `series_pressure`沿真实顺序累计；各损失先由自己的适用方法得到，它不计算换热器或塔压降。 |
| 已声明理想气体/定比热近似的分级初筛 | `compressor_train`需逐级吸气温度、效率、压比、后续损失及气相条件；`equal_ratio_initializer`只给含已定损失的等压比初值，不是最优或厂家额定。真实气体/湿压缩走同物系焓与设备方法。 |
| 有来源的并联支路Q–ΔP关系 | `parallel_distribution`在共同边界压差下分流，只在源曲线内插值、不假定均分、不相加支路压降。 |

数据不足时读原实现/专业图谱写本案符号式，保留未解变量；足够时实际运行并保留
结果。换热器分侧额定、塔水力学、气/两相阻力仍转原EDR、塔和设备专业owner，
不为填表强造计算器。文字规划将这些关系接入docflow的`expert_plan`交接检查；
字段检查不替代正式压降计算、同案物性或设备验收。

### 将方法写成当前流程的压力预算

先选一条实际的供给端→接收端路径，再按相态/功能分段。每段写明确的起止节点、
已知压力锚点、增压/降压节点、损失项与当前关系；不能把整片区域中的若干不相连
支路当作一条预算。方法可以复用，预算端点不能省略。

先给每个压力变量标明实际位置：接收设备的工艺/相平衡要求、供给压力和泵/
压缩机出口不是一个量。先确定接收端所需状态，再把沿途损失加到供给端预算；
不能无解释把上游管损叠进反应器局部相态下限。混合物的相态约束应来自其T、
组成与适用物性；以纯组分饱和压作初筛时，另明示近似、保守方向和适用条件，
不能把这种估算写成混合物必满足的确定等式。

复用上述原实现时，先统一返回量的含义。对其适用的等径、恒密度液体段：
`P_out = P_in + DeltaP_raise - DeltaP_irreversible - rho*g*(z_out-z_in)`。
这里DeltaP_irreversible是该路径总不可逆损失，不含高差。原液管函数的
irreversible_loss_pa只含沿程和minor_k对应局部损失；另台设备损失须由其专业
方法计算后另计，已经放进minor_k的不得重复加入。若已经使用原函数的
`inlet_minus_outlet_pressure_pa`（含高差），不得再加一次静压项。端点速度不等、
变密度或其他相态须换成相应能量/可压缩流方法，不把此式扩展为通用气液管路式。
压缩级与级间设备按原实现写 `P_next = P_suction*r - DeltaP_after`，压比用绝压；
相态/效率/焓与损失的验证仍是独立输入，式子本身不证明级数或设备合格。

把本案实际节点代入关系中的位置，不要求代入不存在的数值。所选方法的每个
输入都要在当前账本中有单位和“已有来源/可推导/缺失”状态；不得用一个“几何
物性均缺”概括整组变量。每项损失只出现一次，静压、不可逆损失、设备升压与
允许的减压功能分别计入。用接收端要求检查直连是否成立；尚不能判定时保留
明确的条件分支和对应泵/压缩/调压位置，而不是丢掉这条功能连接。

换热器分侧、塔内部、膜、气体/两相/浆料等没有适用输入时，先读原专业方法，
把其决定压力所需的关系及最小变量接入该路径；不能用液管公式替它们计算，
也不能只写设备名称或“以后定压差”。当前能计算的部分照常计算；未闭合部分
保持符号状态并写明哪项新数据触发重算。流程符号预算不等于数值水力学校核。


完整流程规划时就调用本压力工作流建立路径预算，并按现有信息执行适用压降计算。
换热器两侧、塔、管线、阀及循环回路分别用相应方法；几何未定可保留有来源的
初筛范围、关键缺口和细化触发，不以全零压降代替计算。新增换热/分段后同时更新
动力设备压力需求与耗功。宏观经验归 docflow 的
[规划经验段](../aspen-document-driven-flowsheet/references/fullflow_generation_workflow.md#规划阶段的经验补齐先把热量和压力安排对)，
这里继续负责压力计算与同案复算，不另建一套算法。

压力基准转换采用 `P_abs = P_gauge + P_atm`，其中现场 `P_atm` 未知时保留符号式。
[标准大气压](https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors)
的 0.101325 MPa 只用于明确标注该假设的示例，不自动成为项目现场值。
每个具体换算结果须带其基准和该假设；设计压力与操作压力分栏核对。

After regeneration, verify these from the exported `*_after_run.inp`, block CSV, and stream CSV:

- All thermal-block pressure specifications match the accepted pressure-drop convention; no hidden pressure-raising service is assigned to a heater.
- Fresh/boundary feeds match current source pressure before each explicit pressure-changing device.
- Each pressure jump has a named pump/compressor/valve and status `0`.
- Stream pressures show the intended breakpoints before and after equipment.
- Reactor blocks still run at intended pressure and are not relying on upstream heater pressure.
- Calculators writing feed streams do not write over the outlet of an already-calculated block.

Useful PowerShell patterns:

```powershell
Import-Csv '.\*_blocks.csv' |
  Where-Object { $_.blkstat -notin @('', '0') -or $_.blkmsg }

Import-Csv '.\*_streams.csv' |
  Where-Object { $_.stream -in $currentPressureAuditStreams } |
  Select stream,temp_C,pressure_bar,mole_flow_kmol_h,mass_flow_kg_h

Select-String -LiteralPath '.\*_after_run.inp' `
  -Pattern 'BLOCK E\d+ HEATER|PARAM .*PRES=0|BLOCK K\d+ COMPR|BLOCK P\d+ PUMP|BLOCK V\d+ VALVE'
```

## PFD And Documentation Rules

- PFD pages must reflect the current Aspen topology. Trace each fresh feed, conditioning unit, pressure device, mixer and recycle in actual order; do not reproduce a private-case block sequence.
- Show every current pressure-changing device and its current tag on the PFD when it matters to the pressure audit.
- State the accepted thermal-block pressure-drop convention and expose pressure errors in the actual pumps, compressors, valves, flashes and reactors.
- If a calculator leaves a near-zero positive feed, document the numerical bound separately from physical feed-system requirements; the bound must come from the current project, not a historical example.
- When replacing a boundary or seed recycle with an internal recycle, update the PFD/report to show the real return path and pressure equipment. Then search the generated PDF text, Markdown, LaTeX, and `*_after_run.inp` for stale seed-stream names or obsolete recycle claims.
- When updating Markdown, LaTeX, and generated PDF, keep claims synchronized with file timestamps, page count, and rendered pages.

## PDF/LaTeX Delivery Workflow

1. Regenerate `.tex` from the current Markdown/source script.
2. Compile with XeLaTeX twice.
3. If the target PDF is open and locked, do not fight the viewer; compile with a new job name such as `_fixed`.
4. Verify page count with `pypdf`.
5. Render key PFD pages using `pdftoppm` and inspect PNGs visually.
6. Extract text from PFD pages with `pdftotext` to confirm critical equipment labels are present.
7. In the final response, mention the locked old PDF if the correct version has a new filename.

## Delivery Package

For a requested combined model/PFD/report handoff, package the following
applicable artifacts. A pressure-only or formatting-only task returns its scoped
evidence without inventing additional model or document deliverables:

- Correct PDF, `.tex`, Markdown source, and report generation script.
- Root `.bkp/.apwz` files for the deliverable Aspen case and any standalone reactor case.
- The Aspen generation script and exported `.inp`, `*_after_run.inp`, stream CSV, block CSV, and run summary CSV.
- A short note in the final answer with validation status, page count, and any file that could not be overwritten because it was open.

阶段收尾若发现有证据且值得复用的新方法或原则，将候选交主助手，按
[主动经验提醒](../chemical-engineering-expert/references/EXPERIENCE_INBOX.md#主动提醒使用者)
展示可审阅摘要并推进确认/投稿；拒绝不催促，已有有效授权不重复询问。

<!-- milklong-attribution:start -->
作者：milklong（GitHub：milklong888）。[版权与AI辅助编辑署名规则](ATTRIBUTION.md)。
<!-- milklong-attribution:end -->
