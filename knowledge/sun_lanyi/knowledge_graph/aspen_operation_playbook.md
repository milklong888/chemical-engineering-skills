# Aspen Plus Codex 操作手册

来源：`Aspen Plus-孙兰义.pdf` 章节提取层，详见 `../chapter_extracts/`。

本文是 Codex 后续在本项目中操作 Aspen Plus 的默认入口。遇到未知情况时，不先凭经验猜卡片，而是先查 `unknowns_router.md` 和 `knowledge_graph_index.md`。
若当前问题类似讲义例题，尤其是复杂精馏、节能塔、塔优化、流程工具、反应器填卡或动态导出，再查 `classic_cases_playbook.md` 获取可迁移模式。

## 1. 默认工作顺序

1. 定义问题家族：组分/物性、物流输入、单元模块、反应器、精馏、收敛、分析工具、动态模拟或结果核查。
2. 打开 `knowledge_graph_index.md`，用触发词查节点。
3. 打开节点指向的章节提取稿。
4. 若涉及复杂精馏、节能塔、塔优化、流程工具或案例迁移，打开 `classic_cases_playbook.md`，只迁移路径、字段意义、判断顺序和检查清单。
5. 若涉及动力学反应器，立即转入 `kinetics_expert_system.md` 和 `kinetics_freeze_template.md`。
6. 若涉及 Aspen 实际填卡，记录：来源页、源单位、Aspen 路径、填入值、导出/截图验证。
7. 若讲义未给字段、单位或参数，标记 `blocked` 或 `provisional`，不要补讲义外参数。

## 2. 章节到任务的路由

| 任务 | 先查文件 | 典型触发词 |
| --- | --- | --- |
| 基本建模流程 | `ch01_process_simulation_basics.md`, `ch02_flowsheet_setup_basics.md` | 新建、模板、Next、Run、流股、流程图 |
| 物性/参数估算/回归 | `ch03_property_methods_and_regression.md` | NRTL、UNIQUAC、Henry、电解质、二元参数、回归 |
| 混合/闪蒸/分离 | `ch04_mixing_flash_sep_modules.md` | Mixer、Flash、Sep、相平衡、组分分割 |
| 压力设备 | `ch05_pressure_modules.md` | Pump、Compressor、Valve、压降、升压 |
| 换热器 | `ch06_heat_exchanger_modules.md`, `ch15_appendices_tools.md` | Heater、HeatX、MHeatX、EDR、换热网络 |
| 塔模块 | `ch07_column_shortcut_and_absorption.md`, `ch10*.md`, `ch12_convergence_strategy.md`, `ch15_appendices_tools.md` | DSTWU、RadFrac、萃取精馏、反应精馏、水力学 |
| 反应器 | `ch08a_nonkinetic_reactors.md`, `ch08b_reactions_kinetics_cards.md`, `ch08f_kinetics_parameter_card_audit.md` | RStoic、RYield、REquil、RGibbs、RCSTR、RPlug、RBatch、动力学 |
| 流程选项/分析 | `ch09_flowsheet_options_analysis.md` | Design Spec、Calculator、Sensitivity、Optimization |
| 收敛排障 | `ch11_process_simulation_workflow.md`, `ch12_convergence_strategy.md` | 循环、断裂物流、Err/Tol、Nesting、Sequence |
| 石油蒸馏 | `ch13_petroleum_distillation.md` | Assay、假组分、PetroFrac、TBP、ASTM |
| 动态模拟 | `ch14_dynamic_simulation.md` | Dynamics、Pressure Driven、控制器、Initialization |
| 附录工具 | `ch15_appendices_tools.md` | Activated Energy Analysis、Column Analysis、CUP-Tower |
| 经典案例模式 | `classic_cases_playbook.md` | 复杂精馏、DWC、热泵、HIDiC、塔优化、流程工具、反应器案例、动态案例 |

## 3. 硬门禁

- 物性方法不确定时，先查第 3 章，不靠单元模块调参掩盖物性错误。
- 动力学参数未冻结时，不得填写正式 `Reactions|...|Input|Kinetic`。
- `PowerLaw` 指数不能从化学计量系数自动推断。
- `LHHW` 的推动力和吸附分母不能压成普通 `PowerLaw`，除非显式标为临时代理并得到用户接受。
- `USER` 动力学没有 Fortran 源码、接口、编译和测试证据时，一律阻断。
- 收敛失败时，先看断裂物流、算法、初值、计算顺序和 Err/Tol 走势，不盲目改设备参数。
- 动态模拟导出前必须通过压力拓扑、阀门、设备尺寸和 Pressure Checker 门禁。

## 4. 可迁移与不可迁移

讲义例题的可迁移部分是路径、字段意义、判断顺序和检查清单。

讲义例题的数值只属于对应例题。除非当前项目源文件给出同一来源、同一单位、同一基准，不得迁移 `k`、`E`、塔板数、压力、温度、体积、停留时间、公用工程或控制器参数。

## 5. 交付证据格式

每次 Aspen 操作完成后，至少留下：

- 使用的知识节点或章节文件。
- Aspen 路径和卡片字段。
- 输入值与单位。
- 运行状态、警告/错误状态。
- 对应结果页、导出文件、截图或 `.inp/.bkp/.apwz` 证据。

## 6. Project Overlay: DSTWU Applicability Gate

## 5a. Project Overlay: Property-Method-First Gate

Before creating any Aspen module, island, tower, reactor, pressure section,
recycle closure, Calculator, Design Spec, Sensitivity, or Optimization, record
the property method selected for that module. The row must include the service,
component family, pressure and temperature window, expected phases, nonideality
and polarity, Henry/gas-solubility or electrolyte/association needs,
azeotrope/extractive/solvent behavior when relevant, available binary
parameters or PCES/structure support, selected Aspen method, missing data, and
status (`accepted`, `provisional`, or `blocked`).

If the property method or required parameter support is wrong or incomplete,
stop the module at `provisional` or `blocked`. Do not proceed by tuning stages,
reflux, solvent rate, reaction conversion, Design Specs, or recycle variables
to compensate for a property-method error.

## 6. Project Overlay: DSTWU Applicability Gate

Before creating a shortcut tower, decide whether `DSTWU` is physically valid.
`DSTWU` is only an initializer for ordinary distillation. It is not a required
first step for absorption, stripping, low-temperature methanol wash, cryogenic
solvent absorption, extractive distillation, azeotropic distillation,
three-phase/VLL, reactive distillation, electrolyte/sour-water service,
petroleum/pseudocomponent service, or any system where meaningful light/heavy
keys cannot be defined.

This is a pre-route gate, not a trial-and-error step. For those special
systems, write a `DSTWU-SKIP` evidence note and go directly to a rigorous
tower island; do not create a throwaway shortcut tower just to fail.

If `DSTWU` is invalid, open `special_columns_direct_radfrac.md` and start from a
minimal rigorous tower in an isolated tower island file named
`<project>-<equipment>`. Preserve optimization evidence by creating new blocks:
`RIG-INIT`, then `RIG-FEED`, optional `RIG-SENS` or `RIG-ANALYSIS`, and finally
`RIG-SPEC` with Design Spec/Vary. The first block in the island is therefore
the rigorous baseline, not `DSTWU`. Promote only the final converged rigorous
block back to the full flowsheet.

Never use `SEP/SEP2/SEPARATOR` as a shortcut replacement for a required physical
tower.

## 7. Project Overlay: Full Tower Coverage Gate

Before promoting any full flowsheet, export the latest input and inventory every
tower-like final block. The inventory must include ordinary distillation,
azeotropic or extractive distillation, absorbers, strippers, low-temperature
solvent wash, regeneration, solvent or entrainer recovery, and polishing or
recovery towers.

For every listed tower, point to an isolated tower-island folder and Aspen file
that preserves the design path. Ordinary distillation may start from `DSTWU`
when meaningful keys exist; special systems must use a `DSTWU-SKIP` note and
start from `RIG-INIT`. Later optimization steps must be retained as new blocks
or cases, and the final block must have a live Design Spec/Vary or documented
equivalent specification for purity, recovery, solvent loss, regeneration
quality, or product ratio.

Two or more towers may be optimized together only when they are one physical
separation system. Record the shared frozen feed boundary, solvent or entrainer
loop, recycle quality, common product target, or manipulated variable that makes
the grouping valid. If that reason is absent, optimize the towers separately.

## 8. Project Overlay: HeatX Shortcut Design Fill Gate

When a project source requires process heat exchange but does not give exchanger
area, tube/shell geometry, or EDR/vendor data, do not ship an empty HeatX card
or a rating case that asks Aspen to calculate missing area. Use a process target
that is justified by the flowsheet, then mark detailed exchanger design as a
later equipment-design boundary.

Minimum HeatX process-fill evidence:

- `CALC-TYPE=DESIGN`.
- `CALC-METHOD=SHORTCUT`.
- A cold-side or hot-side outlet target such as `T-COLD` or equivalent process
  temperature target.
- Hot and cold feeds/outlets explicitly connected.
- Hot and cold pressure drops or outlet pressures specified.
- T-Q curve enabled when heat-integration evidence is needed.
- After-run `BLKSTAT=0` and exported `.inp/.bkp` proof.

## 9. Project Overlay: BKP Run-Status Clean Gate

For final delivery, block `BLKSTAT=0` is necessary but not sufficient. Open or
scan the delivered `.bkp` and confirm the global run status is clean.

Hard checks:

- `RUN-STATUS TOTSTAT` must be `0`.
- No `completed with warnings`.
- No `* WARNING` associated with convergence, Design Spec, RYield
  normalization, or atom balance.
- No `SPECIFIED YIELDS HAVE BEEN NORMALIZED`.
- No `ELEMENTS ARE NOT IN ATOM BALANCE`.
- No `MANIPULATED PARAMETER NOT CHANGING` in a promoted delivery file.

If a strict Design Spec branch reaches the required material result but leaves a
Secant/Design Spec warning, do not ship it by simply relaxing `TOL-SPEC`. Either
repair the solve structure to get a clean BKP, or promote a documented fixed
input branch derived from the strict pre-solve evidence and rerun all product,
ratio, topology, and BKP-status gates.

## 10. Project Overlay: Principle-First Tower Spec-Basis Repair Gate

When a tower failure looks like a RadFrac convergence problem, first decide
whether the operating specifications are physically compatible with the unit
service. This gate applies especially to partial condensers, vapor vents,
absorber/stripper-like towers, and feeds with large noncondensables.

Before broad tuning:

- trace the active upstream and downstream process path;
- read feed/product phase and component inventories from exported evidence or
  the Aspen COM tree;
- identify whether the tower is doing inert purge, condensable recovery,
  ordinary distillation, absorption, stripping, or a mixed service;
- inspect companion basis cards such as `DB:F-PARAMS` alongside `COL-SPECS`;
- compare the active condenser temperature/specification with dew/bubble or
  superheated-region messages in Control Panel/history.

If the exported card shows a component-basis modifier such as
`DB:F-PARAMS COMPS=...`, do not assume `D:F` is a total-stream basis. If the
component list contradicts the physical service, record the evidence in the
change-offset table and test removing only that basis modifier before changing
T1, reflux ratio, pressure, stage count, property method, or topology. Use
`project_cases_0704_radfrac_inert_vent_repair.md` for the reusable diagnostic
pattern and COM delivery details.

## 11. Project Overlay: Non-GUI Aspen EDR Rating Delivery

When a project requires EDR for all exchangers, open
`project_cases_0710_edr_rating_delivery.md` and the equipment overlay before
mutating HeatX cards.

Required order:

1. Freeze the accepted case, process targets, allowed changes, and a complete
   HeatX/Heater coverage ledger.
2. Route only eligible two-stream HeatX blocks to EDR unless a source-backed
   topology change creates a second side for a Heater.
3. Generate or repair a same-equipment `.EDR` file and audit XML `TascMsg`,
   result completeness, outlet states, duty, area, pressure drop, RhoV2, and
   vibration. COM return values are not sufficient.
4. Bind using the local-version official `TASCPLUS-RIG` pattern and a program
   mode consistent with the EDR file role. Do not force a rating file into
   Design merely because Design sounds more complete.
5. Reopen with no edits and prove EDR execution through readback/report/output
   fields. `DETAILED`, `Run2=0`, or a clean Control Panel alone is not EDR.
6. Apply engineering gates: positive or explicitly accepted area margin,
   pressure and velocity limits, vibration, property-curve coverage, and
   materials basis.
7. Apply Aspen delivery gates separately: Required Input complete, all-zero Run
   Status/history, and unchanged authorized process/product/recycle targets.
8. Copy, hash, reopen, rerun, and re-audit the exact user-facing BKP/APW.

Never transfer project exchanger values, geometry, materials, method choice,
or parallel/series arrangement. Detailed project evidence belongs in the
equipment overlay, not in reusable defaults.
