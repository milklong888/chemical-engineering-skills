# Tower optimization — on-demand method and hydraulics

Apply the chemical expert's STRICT_ACCEPTANCE_AND_LEARNING.md. Old project
numbers and default pressure/reflux assumptions have no global authority.
Private case inputs are not distributed. Original calculation functions are
preserved in the explicit-profile scripts described below.

## Network Position

Upstream authority is `aspen-document-driven-flowsheet`: it supplies the source
route, change-offset status, frozen feed, separation target ledger,
property-method row, and promotion gate. This skill owns the tower-island
workflow and returns tower sidecars, exported evidence, and reconnect gates to
the process authority layer. Use `aspen-plus-operations` only for mechanical
Aspen create/set/run/export actions. Use `aspen-pressure-pfd-delivery` when the
tower result needs pressure, vacuum, heat-exchanger, or PFD/package audit.

## First Gate

Before editing Aspen files, read the active project change-offset table and the
latest tower sidecar/stepbook for the same duty. If a user-qualified local textbook graph exists under `{CHEM_WORKSPACE}`, use
its actual unknowns/special-column routing. No source book or private graph is
bundled; examples give methods, not values.

Never use a rejected branch or lecture-case number as a default. Record a new
change-offset row before mutating `.inp` scripts or Aspen cases.

Freeze the tower property method before the shortcut or rigorous tower exists.
Use the real tower service: component family, pressure/temperature window,
expected VLE/LLE/VLL behavior, polarity/non-ideality, solvent/entrainer or
azeotrope needs, binary-parameter support, and transport-property needs for
hydraulics. After the property row is accepted, do not change it to rescue
reflux, stages, hydraulic warnings, or product purity unless the upstream
process authority records a change-offset row and reruns affected tower
evidence.

## Choose The Route

Ordinary distillation may use `DSTWU` only after freezing:

- feed stream/export;
- separation duty and product specs;
- LK/HK and key recoveries;
- pressure path and allowed pressure drop;
- final Design Spec target and Vary bounds.

Special towers skip `DSTWU` and start rigorous:

- azeotropic or extractive distillation;
- absorber, stripper, solvent wash, regeneration;
- VLL/three-phase or reactive distillation;
- any duty without meaningful light/heavy keys.

For special towers, write a `DSTWU-SKIP` reason plus property-method and phase
support before creating `RadFrac`.

For an absorber/regenerator, first label physical stream roles in the island:
untreated feed gas enters the absorber and treated gas leaves it; lean
absorbent enters, rich absorbent leaves for regeneration, and regenerated
lean absorbent returns through the justified cooling/pressure route.
Regenerator overhead CO2/vent, solvent loss, makeup and purge each need a
destination. Do not describe already-treated gas as the absorber feed.
Tower stage count, contact-section count and feed/contact locations are
**outer discrete structural choices**, never a tower-internal continuous
`VARY`. A tower-internal quality target needs an independent, physically
writable continuous input with a justified interval (for example solvent
circulation or a suitable regeneration duty/flow after source and freedom
checks). If the solvent mechanism, target or such an input is unresolved,
leave that tower's formal target locally pending; do not fabricate a stage-
count `VARY` or claim the two-tower recycle is controlled.

For gas-throughput changes, decide who owns absorbent circulation before
building either control object. If the absorber's internal SPEC uses solvent
circulation as its VARY, a Calculator may give a **one-time initialization**
or compute a different input such as independently sourced makeup, but it
must not rewrite circulation on every solve. If a source-required ratio
Calculator must write circulation every iteration, that degree of freedom
is occupied: choose another source-supported continuous VARY for the gas
quality target or leave that target locally pending. Record separate writer,
producer, consumer and coupled-recycle order for absorber and regenerator.
For a source `<`/`≤` gas-quality limit, keep the inequality as the acceptance
or guard; an equality-type internal SPEC requires a justified design setpoint
inside that limit, not a silent replacement by the limit value.

## 建塔入口：从初估到优化的完整顺序

本库的正式塔建模和塔优化**强制使用有效的 Design Spec/Vary**。
这是当前用户指定的工作方法，不是声称孙兰义讲义要求所有塔都如此。
仅画骨架的 SEP、DSTWU 初估、既有固定塔的只读报告/水力审核不冒充正式塔建模，
也不擅改模型来补控制器；一旦要把严格塔作为已建成/已优化结果交回，就须过此门。

1. **先定分离任务。** 固定进料、组分/单位、物性与相态依据、产品纯度/回收/
   产量及约束方向、压力路径、允许调节的量。先用总量/组分衡算推导能闭合的
   产品流量、回收率，再列真正不可替代的缺口；推导出的结果还要与独立操作
   规定分开。此时就列出拟用 Design Spec 和候选 Vary，不能等优化完再补对象名称。
2. **在进料副本上初估。** 对普通轻重关键组分塔，复制母流程当前进料边界至
   隔离子模板，仅添加 DSTWU 及必需连接；不能在母流程原塔位直接试改，
   也不把子模板的进料副本作为最终新增物理进料。DSTWU 给最小级数/最小回流，
   并按来源获准的回流或级数设计规定取得初始 N₀；它不无条件给唯一最优级数。
   共沸、萃取、吸收/汽提、反应等特殊塔不套普通快捷假设，记录原因并走获准严格路线。
   简捷结果只供初始化；不迁移旧案回流倍数、板数或压降。
3. **建立基础严格塔。** 在隔离塔岛用同一入口边界建 RadFrac，先固定 N₀；
   配冷凝器/再沸器、有效相态、进料位置/约定、产品出口与操作规定、
   压力剖面；保留有物理意义的初值。进料相关的配料、
   溶剂或库存显式关系在消费者首次计算前接入 Calculator；统计计算放在结果之后。
4. **先验证基础塔。** 看实际流股、组成/温度/气液负荷剖面和守恒，修复物性、
   配置、压力或相态缺陷。基础试算是初始化证据，不是跳过 Design Spec 的最终成果。
5. **建立可求解区间。** 复用同版同边界的有效响应证据；没有时使用有界原生
   Sensitivity 核 RR 与 D/F 等真实连续输入的可行窗口。未知响应才扫描，
   不每次重复全范围。进料组成接近法只给候选，不证明最低热负荷位置。
6. **启用并验证塔内 Design Spec。** 按当前纯度/回收要求选独立目标，
   明确采集量、单位/容差、真实输入型 Vary、初值和上下限。普通两产品塔
   的主方案由塔内 SPEC/VARY 分别求 RR、D/F；原固定操作值只作初值，
   不与正在求解的输入重复锁定。二元衡算导出的 D/F 是初值/结果核对，
   不是在 D/F 作为 Vary 时又固定的卡片。跨塔目标才考虑 flowsheet
   Design Spec，不把它冒充用户要求的塔内控制。核实际残差、状态、产品流量及导出卡。
7. **先进料板、后总级数。** 在固定 N₀ 且两项塔内 SPEC/VARY 生效时，把
   合法进料级逐个作外层离散候选；每点重新求 RR、D/F 和产品目标，只在
   同产品且其他硬门合格的点比较 Qreb，得到该 N₀ 范围内的低负荷进料位置。
   然后再调整总级数 N；每个 N 须重新映射/核进料位置，必要时重新寻找
   该 N 的低负荷进料级，再解两项塔内规格、比较 Qreb 和设备/投资负担。
   不能把原最佳进料级原号照搬、把 N 当连续内层 Vary，或固定旧 RR/D/F。
   N 增加通常有热耗与设备投资权衡；没有同基准成本/限制准则时只报告
   候选关系，不能仅凭最大 N 热负荷较低就称最优级数。保留失败点，选定点重算。
8. **校核当前工况的物理可实现性。** 对同点流股/气液剖面调用设备选型、
   塔水力及压降校核。限制是容量/液泛等真实能力问题才评估并联或其他调整；
   缺目录/缺几何不直接证明需要多塔。改变压降、结构或负荷就回到受影响的步骤。
9. **按原接口回装最终严格塔。** 有母流程时仅把最终带塔内 SPEC/VARY 的
   RadFrac 放回原塔位/进出及回流接口，DSTWU 子模板和进料副本不回装；
   用母流程新的实际进料和循环重新解 RR、D/F 与产品规格，复核受影响的
   压力、换热、产品及设备。独立塔则交付边界账本，不虚构母流程。
10. **核验精确候选。** 依据原严格交付规则检查实际对象、执行结果、导出、
    原文件重开及同案产品/设备证据。文字计划不算任何一项软件门已通过。

### Design Spec 强制门如何避免过规定

二元、只有顶底两产品且无损失时，选同一组分作基准：
`D=F(z_F-x_B)/(x_D-x_B)`，`B=F-D`；再由产品组分流量求回收率。
`x_B`须是塔底**同一组分**的摩尔分数，不能直接代入另一组分纯度。
若两个产品组成均已规定且 `x_D≠x_B`，不要索要可由此求出的采出量/回收率。
但两项纯度仍是两项产品要求；计算得到 D 不等于已把 D 设成塔的独立操作输入。
可用两组独立 SPEC/VARY，或合法固定该 D（或 D/F）且用另一连续 Vary
解一项纯度、在同轮衡算核证第二项。后一种等价实现必须写出固定采出量的
卡片/唯一写入者及守恒前提；未固定分割量时仅解一项纯度不能保证另一项。

“强制”不能变成任意找个变量配一个无意义目标。缺少目标、独立可调量、
可行边界或必要物性时，完成能完成的基础建模/推导，列最小缺口，
状态保留在初始化/待解，不把手扫最优、直接固定输入或不等式检查当作
必需 Design Spec 已完成。只有用户明确允许的本案放宽才能豁免，且不得入自进化。

保留来源中的 ≥/≤ 约束。在其内选择设计设定点须给出可行性和设计理由；
若没有适当设定点/获准自由度，先澄清，不静默把“至少”改成精确等式。
原生优化中的其他不等式仍独立保留；优化器 Constraint 也不替代本库要求的
有效塔控制。Calculator 不得每轮覆盖 Vary 正在求的同一个量；只作初值的
赋值必须是一次初始化，不是循环强写。

### 塔优化的两个分支与调用入口

- **普通塔的进料板→级数候选**：先固定 DSTWU 初始 N₀，用塔内 RR/D:F
  设计规定逐进料板比较 Qreb；之后才把 N 作为另一层离散候选，每个 N
  重新核进料位置与塔内规格。需要加速时评估 Column Analysis / NQ；
  NQ 只用于适用的平衡级模型，先核目标函数、级数范围、进料板范围及
  其他进料、侧线、中段循环和分相位置的移动规则；NQ 级数上限不得超过
  其基准塔（讲义 PDF p.402–405）。速率模型不硬套 NQ。脚本调用与
  能力边界见 [tower_script_handoff.md](tower_script_handoff.md)。
- **热耦合/热泵优化**：常规塔达标后才交
  `aspen-heat-pump-distillation-replacement`；改压缩机压力时，塔的内层质量
  控制必须逐点重解。原塔内部负荷与外部换热不能重复计入节能。

进入操作层时先查 `aspen-plus-operations/references/operation_graph.md`
的 `design-spec`、`sensitivity`、`calculator`、`optimization-regression` 节点，
再用其 `scripts/query_manual_knowledge.py` 查询
`design_spec.define_vary`、`sensitivity.vary_tabulate`、
`calculator.define_sequence`。若涉及 NQ、Balance、特殊塔或当前版本字段，
继续查讲义相关节点和合法安装帮助，不能按记忆编数据树路径。
工作流/脚本发现可走 `workflow_lookup` 或 expert CLI 的 `workflow`；
不存在该 MCP 时走本机文件与已有 CLI，不改成外部数值试错。

## Standard Sequence

Preserve each step as a new block, copied case, or sidecar entry:

```text
TARGET-FREEZE
  -> clone current feed boundary + DSTWU side-template (or justified DSTWU-SKIP)
  -> RIG-INIT at source-selected N0
  -> bounded response + live tower-internal SPEC/VARY for RR and D/F
  -> RIG-FEED: vary feed stage at fixed N0, re-solve both specs at every point
  -> RIG-N: vary stage count; remap/recheck feed stage and re-solve both specs
  -> optional continuous optimization only with remaining authorized freedoms
  -> same-point equipment/hydraulics check
  -> reconnect to full flow
  -> pressure/vacuum/HX audit
  -> dynamic run evidence
```

For ordinary towers, derive the shortcut initial specification and bounds from
current feed, keys, recoveries and source method. Do not assign a taught reflux
multiplier without that task's authority. Negative Aspen shortcut notation is
an input convention, not a negative physical reflux ratio; verify its meaning
against the current help/export. Convert to a converged rigorous baseline,
then add the authorized live specifications.

Only when the task explicitly requests the lecture's additional minimum
reflux/minimum-stage or stage-plateau study, retain this historical extension.
It is not triggered merely by requesting DSTWU→RadFrac; the current main route
is the feed-stage-then-stage-candidate sequence above:

```text
DSTWU with the source-authorized reflux or stage specification
  -> read minimum reflux/stages and actual stages
  -> run a stage-number sensitivity around the current shortcut actual-stage region
  -> choose the first plateau/sensitive stage where RR no longer drops much
  -> rerun DSTWU with NSTAGE fixed to that stage to get the exact RR and D/F
  -> build the first RadFrac from the exact DSTWU values
  -> extract RadFrac liquid composition profiles
  -> move the feed stage to the tray/packing theoretical stage whose liquid
     composition is closest to the feed composition
  -> rerun RadFrac and only then tune D:F, RR, and any allowed feed-scale
     design variable against product/recycle/capacity gates
```

For every formal tower-modeling or tower-optimization result in this workflow,
`Design Spec`/`设计规定` is required. Do not promote a fixed `D:F`/`B:F`/reflux sweep as the
formal result. Use the sweep only to bracket a feasible window and provide
initial values. For a single-tower product target, add/export live
**tower-internal RadFrac `SPEC/VARY`** pairs; a flowsheet-level Design Spec
is not a substitute. Cross-tower or overall-loop targets may additionally use
an external flowsheet Design Spec without displacing the tower-internal pairs.
Promotion evidence must include exported tower `SPEC` and `VARY` cards,
their same-run residuals and product compositions, and proof that RR/D:F were
solved rather than hand-entered from an offline scan.

If the final model needs parallel towers for attributable equipment limits,
derive the feed/reflux distribution from the current duties and design basis.
An equal split with identical cards is only a candidate for demonstrably
symmetric trains. Separately justify shared or independent condenser/drum,
reflux and bottoms systems; their arrangement is not a universal case default.
Check the parallel topology explicitly; a passing material balance from a
single tower is not evidence for the parallel equipment design.

For special towers, first find a favorable rigorous window by stages,
feed/contact positions, draw rate, reflux/boilup, solvent or entrainer rate,
recycle split, and pressure. Keep stage/position alternatives in the discrete
outer layer; use only verified continuous, writable inputs for inner
SPEC/VARY. Add Design Specs after the response is feasible and bounded.

## Design Spec Discipline

Design Specs must control a real target: purity, recovery, solvent/entrainer
loss, recycle quality, product ratio, or product split. Each spec needs one
bounded manipulated input with an engineering reason.

Use tower-internal RadFrac `SPEC/VARY` when the target and manipulated variable
both belong to one tower. Pair `SPEC n` and `VARY n` by the same index, bracket
the feasible range first, then promote the live spec only after the same run
exports the cards and the downstream product/recycle gates pass.

Prefer `MOLE-RECOV` or `MASS-RECOV` when the target must scale with feed
perturbations, such as final recovery from a changing recycle/feed mix. Prefer
`MASS-FRAC` or `MOLE-FRAC` for product purity or impurity leakage when the
target stream has meaningful flow. Use absolute `MOLE-FLOW` or `MASS-FLOW` only
for a source-given draw, a wetness/minimum-flow guard, or a diagnostic fixed-draw
candidate; do not promote it as a feed-scale-independent final recovery control.

Keep external flowsheet Design Specs for cross-tower, cross-stream, merged
stream, or overall-loop targets. Do not force those targets into a RadFrac
internal spec. Respect the requested precision exactly: a "three nines" purity
target means `0.999`, not an unrecorded six-nines tightening.

If equality specs conflict, inspect degrees of freedom, physical feasibility
and the current authority. Do not silently drop one required equality or relax
precision. Keep an infeasible point diagnostic; a change needs explicit current
project authority and any relaxation is case-only/no-learning.

## Pressure And Equipment Audit

Before promotion:

- every retained RadFrac has a pressure path and tower pressure drop;
- tower and exchanger pressure drops come from the current source/method and
  same-duty hydraulic evidence, with units and basis; no project ratio is a
  universal default;
- liquid pressure rise uses pumps, gas pressure rise uses compressors, letdown
  uses valves;
- vacuum service has explicit pressure devices or a documented boundary;
- distinguish actual liquid/gas service and phase changes; no shared liquid-HX
  pressure fraction is imposed on unrelated gas/reaction service;
- no orphan vacuum streams or stale pressure placeholders remain.

## Energy-Saving Tower Supplements

After the rigorous base tower passes product/recycle gates, optional energy
optimization may branch into low-reflux operation, pressure changes,
multi-effect coupling, or heat-pump/VRC integration. Keep these as tower
supplements until they pass the upstream full-flow gates.

For heat-pump/VRC replacement work, route through
`aspen-heat-pump-distillation-replacement` before asking the operation layer to
add compressors or external HeatX blocks. Use the older document-driven
heat-pump integration reference only for background energy-integration
classification when the task is not an empty-column replacement.
Classify the result as:

- runnable VRC supplement;
- partial heat integration;
- final countable heat-pump design.

Do not count heat-pump utility savings from a branch where the RadFrac internal
condenser/reboiler duties remain active and unlinked. Preserve the base tower
and compare duties only from same-run exported evidence.

## Packed-Tower Hydraulic Predesign Gate

When a taskbook, buyer, report, or final claim asks for tower hydraulic or
equipment design, do not invent a tower standard and do not claim hydraulics
from a material-balance-only RadFrac. Freeze the current source text first:

- tower type, top/bottom pressure or pressure path, condenser/drum behavior;
- required product/recycle specifications;
- any grading gates for HETP, bed height, redistributors, flooding/capacity
  factor, tray liquid level, or pressure drop;
- whether the task needs preliminary course design or a vendor-grade internals
  result.

Use the local knowledge graph operation path before web tutorials when present:
RadFrac strict tower -> Sizing and Rating/Pack Sizing or Column Analysis ->
hydraulic result pages. Lecture cases provide paths and diagnostics only; they
do not provide reusable HETP, flooding factors, diameters, pressure drops, or
packing types.

Generic hydraulic acceptance ladder:

```text
accepted same-version RadFrac operating point
  -> verify property-method/transport-property row
  -> generate column hydraulic data or export RadFrac hydraulic profiles
  -> define tray or packing section geometry/internals
  -> inspect Hydraulic Plots, warning status, pressure profile, and Column
     Hydraulic Results or project-local packed/tray ledger
  -> record diameter, section range, pressure drop, flooding or capacity
     approach, weeping/entrainment/downcomer/packing warnings, and source gates
  -> rerun/reopen/export if hydraulics or internals cards are kept in Aspen
  -> reconnect only after product, pressure, recycle, and delivery gates still
     pass
```

Do not treat a `Flow Rate` plot, vapor/liquid load table, or old tower profile
as final hydraulic evidence. A hydraulic claim needs generated hydraulic data
and an explicit result page/ledger from the same final operating point.

Separate hydraulic evidence levels before making a delivery claim:

- `L0 material`: RadFrac/DSTWU converges and products pass; no hydraulic claim.
- `L1 source-static`: taskbook tower type, diameter, bed height,
  redistributor, tray liquid-level or packing capacity/flood gates pass.
- `L2 course-predesign`: same-run RadFrac profiles plus transparent HETP,
  packing, pressure-drop and capacity assumptions in a manual/script ledger.
- `L3 software-rating`: Aspen Column Analysis/Column Internals or equivalent
  tray/packing rating from the same final operating point, with pressure drop,
  capacity/flooding and warnings checked.
- `L4 vendor/mechanical`: vendor internals package plus mechanical/nozzle/shell
  checks. Do not promote L2 as L3 or L3 as L4.

For a physically credible packed-column predesign, also check practical
operability beyond the pass/fail number: property and transport-property basis,
section and total pressure drop, distributor and redistributor locations,
liquid turndown/loading, fouling or contaminated-liquid service, HETP source,
support grids, collectors, hold-downs, feed devices, nozzles, and the expected
high/low-load envelope. A warning-free material simulation is only the minimum
screen; it is not proof that the packed tower is an engineering-grade design.
Local standards can supply method routes, but formal diameter, percent
capacity, flooding, pressure drop, HETP and internals claims require Aspen
Column Internals/Column Analysis, vendor data, or an explicitly labelled
course-design assumption.

For a packed-column course-design precheck, it is acceptable to combine
exported RadFrac profiles with explicit assumptions, but label the evidence
class correctly:

- `source_direct`: taskbook gates such as max bed height and allowed capacity
  factor range;
- `aspen_export`: same-version RadFrac temperatures, pressures, and internal
  vapor/liquid profiles;
- `manual_assumption`: HETP, packing family, flooding F-factor, nozzle
  velocities, and liquid density when not exported;
- `software_boundary`: Aspen Column Internals/vendor packing data, guaranteed
  flooding, pressure drop, HETP, and final internals dimensions.

For source-authorized packed-tower preliminary design, the method sequence is:

```text
accepted full-flow RadFrac BKP
  -> reopen the exact delivery APW/BKP and rerun cleanly
  -> extract stage T/P and vapor/liquid molar + mass profiles
  -> verify named stage-profile fields, units and identity; do not infer private binary labels from a plausible curve
  -> exclude condenser/reboiler from packed stages
  -> split beds by source max bed height
  -> size diameter at selected capacity fraction
  -> verify actual capacity factor range and bed-height gate
  -> write hydraulic JSON/CSV/MD ledger
  -> keep Column Internals/vendor guarantee as boundary
```

Hydraulic evidence must use the same operating point as the final promoted
case. If reflux ratio, distillate/feed ratio, feed scale, pressure network,
Column Internals cards, or recycle quality changes after a hydraulic ledger was
made, rerun the hydraulic extraction from the final APW/BKP after-run export.
Do not reuse a previous candidate's diameter/capacity factor as final tower
equipment evidence.

For an Aspen built-in Column Internals supplement, create the internals object
from exported/importable RadFrac cards rather than by writing result nodes:

```text
RadFrac block
  -> SUBOBJECTS INTERNALS = CS-...
  -> COL-CONFIG ... CA-CONFIG=INT-1
  -> INTERNALS CS-* STAGE1/STAGE2 INTERNAL=PACKING SIZING=RATING DIAM=...
  -> PACK-RATE rows
  -> reopen/run/export and project hard-gate audit
```

If a vendor/packing text string fails import or `HYDRAULIC=YES` gives a
nonzero tower block status, keep that branch as diagnostic. Promote only the
branch whose exported cards preserve the internals object and whose full-flow
product, pressure, recycle, inhibitor/additive, and run-integrity gates pass.
If `HYDRAULIC=YES` leaves a real warning, that candidate is diagnostic.
Do not disable required hydraulic calculations to manufacture clean acceptance.
A `HYDRAULIC=NO` material-simulation branch is admissible only when the current
stage contract independently permits manual preliminary hydraulics; retain its
same-operating-point calculation ledger and explicit software boundary. It
cannot satisfy a required Column Internals/rating/vendor gate. A user-approved
stage relaxation is case-only and excluded from learning with all descendants.

## Public Hydraulic Interface Boundary

Use `../scripts/radfrac_packed_hydraulic_from_bkp.py` for one column and
`../scripts/parallel_radfrac_packed_hydraulic_from_bkp.py` for parallel columns.
The original parsing and calculation functions are retained; case identities,
stream maps, geometry, physical-property inputs and acceptance limits are
provided through `--config`, not inherited from a previous project.

Read `../scripts/packed_hydraulic_config.schema.json` and the shared
`../scripts/packed_hydraulic_contract.py`. Bind the source file and configuration
hash, named DSET fields, explicit units, applicable packing limits and geometry.
Run with `--config <case.json> --out-prefix <new-output-prefix>`; existing output
is not overwritten. Missing inputs limit only the quantities that depend on
them. Field-label inference is diagnostic only. Ideal-gas density and manual
capacity/HETP estimates remain preliminary, never Column Internals/vendor proof.

Use current same-case named stage profiles with explicit units, geometry and
source-backed packing/tray limits. Column Internals/Column Analysis, vendor
data or an independently verified local calculation may close the applicable
evidence stage. Preserve source hashes, profile identity, equations, assumptions,
gate limits and result scope. This workflow does not claim numerical hydraulic
analysis has been performed.

Do not infer a result field from a temperature-looking curve or reuse another
case's binary label offsets. A wrong-profile calculation is invalid even if
the resulting geometry looks plausible.

For a clean material simulation with `HYDRAULIC=NO`, an oversized internals
diameter can make the packed-bed capacity factor fail low even though all
product gates pass. Size or revise `INTERNALS ... DIAM` from the exported vapor
profile so the whole packed bed capacity factor lies in the source/task range,
then rerun the Aspen case, hard gates, Control Panel/APW reopen checks, and
hydraulic extraction from that revised final operating point. Do not claim the
old oversized diameter merely because the Aspen block status is zero.

The inverse is also a failure: an undersized internals diameter can leave block
status zero while the packed-bed capacity factor or flood information is above
the source/task range. In that case, increase or split the tower diameter/duty,
rerun the full Aspen case, and regenerate the same-operating-point hydraulic
ledger. A material-simulation pass is not enough for tower equipment delivery.

Where a tower has a source-given diameter, flooding or packing constraint,
verify the exact final same-duty internals/hydraulic evidence. Packing names
and a material-balance pass do not prove capacity. Record all governing stages,
bed heights, redistributors and current high/low-load limits. Historical example geometry, packing and flooding values are neither included
nor available as default selectors.

For energy optimization, keep the product/recycle hard gates above the duty
objective. A low-reflux or pressure-change candidate is promotable only after
the same-version full-flow audit still passes capacity, purity, visible drum
topology, inhibitor/additive, no-SEP, and run-warning gates. Record the rejected
cases and the accepted operating point; do not let a hydraulic or duty
improvement overwrite a failed product spec.

For document-derived impurity targets, translate wording into the current actual
stream path. Check relevant overhead/condenser/drum/product or bottoms/downstream
feed locations, not a convenient empty or post-processed stream. Require
meaningful product flow/composition and the source target; no private chemical
stream map is supplied.

For tight recycle impurities, use a bounded three-variable polish only after
the full-flow seed is pressure/topology clean:

```text
accepted pressure-clean full flow
  -> vary tower D:F / distillate split for recycle impurity
  -> vary reflux ratio for product/recycle tradeoff
  -> apply small equal-ratio fresh-feed scale only to restore capacity
  -> rerun full-flow hard gates and APW reopen gates
```

Do not promote the lowest-utility point if it fails any document or buyer
purity/recycle specification. A newer buyer specification must be recorded with source, units and basis in
the project change-offset table before mutation; do not transfer old recycle
impurity numbers.

For reduced-stage redesign after a conservative RadFrac has already passed,
rerun the shortcut-to-rigorous chain under the current property method and
current impurity redline. Do not assume the old final stage count or old Rmin
still controls after property, recycle, or product-spec changes. A useful
pattern is:

```text
current accepted full-flow feed boundary
  -> DSTWU with current-source initialization and evidence-derived feasible bounds
  -> fixed-stage DSTWU around the plateau/sensitive stage
  -> low-stage RadFrac with tower-internal SPEC/VARY still active
  -> reject low-RR RadFrac cases that pass recycle impurity but fail final
     product purity
  -> restore product purity by a bounded RR or D:F polish, not by changing the
     property method
  -> apply only a small equal-ratio feed/steam scale if capacity drifts
  -> rerun full-flow hard gates, delivery APW reopen, and hydraulics from that
     final operating point
```

Near a capacity limit, compare same-operating-basis accepted/rejected points
using source-backed hydraulics. Any calibration from a reported flooding ratio
is case-specific and must state its assumptions; it is not a universal capacity
correlation or vendor guarantee. Record the controlling stage and uncertainty.

## Reconnect Gate

A tower island is not promoted until the same-version full-flow candidate has:

- reopened/runnable `.bkp` or generated Aspen archive;
- exported `after_run.inp`, stream CSV, block/status CSV, and summary JSON;
- strict clean block/spec/calculator/run evidence; a quarantined status cannot
  pass the reconnect acceptance gate;
- product purity/capacity and recycle metrics;
- pressure, vacuum, and heat-exchanger pressure-drop evidence.

Current project-specific production, purity, residual SEP, heat-reporting and
recycle requirements are read from that project's latest authority, never from
a named historical case in the global skill.
