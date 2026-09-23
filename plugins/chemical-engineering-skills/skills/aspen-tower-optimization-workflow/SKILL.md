---
name: aspen-tower-optimization-workflow
description: Optimize and reconnect a source-frozen Aspen distillation or solvent-recovery island using the required shortcut/rigorous route, live Design Specs, same-product comparisons and hydraulic/equipment checks. Use for tower optimization, DSTWU-to-RadFrac, special columns, recycle quality and pressure/vacuum audit; no universal example values.
---

# Aspen Tower Optimization

## 工作过程

单模块文字规划也要交接完整：必须实际读取
[单模块方法及交接检查](../aspen-plus-operations/references/unit_modeling_workflow.md)
的适用部分。输出当前目标—具体操纵/写入变量—边界来源—插入阶段—每轮执行先后
及验证对象，不能只说“用设计规定/计算器”。仅禁止启动Aspen时仍执行相关只读查询
和原 solve_route；真实数值与软件结果保持未验证。每座正式塔必须有有效DS配对方案。

正式塔建模/优化强制使用有效 Design Spec/Vary；按
[建塔、设计规定与优化的完整顺序](references/tower_optimization_workflow.md#建塔入口从初估到优化的完整顺序)
执行。规划先列目标—操纵量，合理基础塔与可行区间形成后启用；每个优化点和回装点
重新解目标。缺目标/自由度/边界须明确局部缺口，不用手扫或固定值静默替代。
保留来源不等式含义；Calculator 不得重复占用 Vary。仅初估/只读审查的边界见该方法。

普通精馏的当前主线：复制母流程进料边界建只含必要 DSTWU 模块/连接的子模板；
DSTWU 按有据设计规定给初始理论级数 N₀，并非无条件给唯一最优级数。
严格塔先固定 N₀，以产品纯度/回收的独立目标配置**塔内** SPEC/VARY，
通常由回流比 RR 与采出比 D/F 分别作真实输入型 Vary；先找该 N₀ 下低
再沸负荷的进料板，再调整总级数。每改级数都重核进料位置并重解 RR、
D/F 与产品目标，不能沿用旧点。最终带塔内规格的严格塔才回到母流程原接口。
进入实现时读[原模板脚本与适配边界](references/tower_script_handoff.md)，
先复用现有候选矩阵/操作模板，不把其只读或文本生成能力冒称已完成原生建卡。

交付塔方案时，把每个产品指标逐项列成“来源语义与单位 → 可推导关系 →
有效 SPEC → 独立且可调的 VARY → 当前区间依据/缺口 → 残差和导出待验”。
先用物料衡算求可闭合的产品量/回收率，再单独审查控制自由度；推导出采出量
不自动使两个产品纯度目标冗余。用一项 DS 求解、另一项同轮守恒核验时，
还须把等价推导所需的另一独立操作量合法固定，并说明其唯一写入者；
否则保留两项独立 SPEC/VARY。不得仅写“必要时配 Vary”，也不得把等于目标改成至少目标。
级数/进料板与连续操作量分开安排，不能把级数当连续内层 VARY。

为当前塔岛制定约束求解或操作点比较方案时，先按[阶段调用规则](../chemical-engineering-expert/references/DESIGN_STAGE_ROUTING.md)实际执行 `island` 知识准备，并与本次 `solve_route` 回执一起核对。准备方案也需要完成已有资料支持的查询；缺模型只限制依赖模型的计算，具体缺口写入结果。独立求解路由和读取规则都不能代替岛阶段调用。单纯解释优化原理、不涉及当前塔岛方案的问答不因此扩成工程任务。

执行入口是运行库 `tools/expert_cli.py` 的 `design_stage` 操作，或同一实现的 `design_stage_check`。从工作区链接图取得运行库位置并查看 `--schema design-stage`，把当前任务原文写入 `question`，以 `stage=island` 保存请求；CLI 使用 `--request 请求文件 --output 回执文件`。方案准备可只提交这一最小结构：

```json
{"operation":"design_stage","payload":{"stage":"island","question":"当前任务原文"}}
```

其中 `question` 必须替换为本题实际内容。这个最小请求执行本地知识准备和阶段编排，不会打开或运行 Aspen、EDR、SW6；未提供的模型身份与设备工况保持缺口。取得并读取本次阶段回执后再交回求解方案，不能把“禁止启动商业软件”解释成跳过该只读入口。独立路由回执仍另外核对，不能写成阶段回执。

回执先核 `stage`、`status`、`execution_summary` 和缺口，再读取实际采用的知识命中与适用条件；完整回执保存一次，不反复打印整份大文件。

先固定当前塔的进料、物性、产品纯度、产量和回收要求，判断快捷方法是否适用；适用时在隔离子模板用DSTWU给严谨塔初始化，不适用时说明原因并按获准方法建立基准。基准稳定后，复用同版有效响应区间，未知时先做有边界的敏感性分析；用塔内Design Spec按产品标准联动RR与D/F，在固定初始级数下先比较进料板，再调整级数并重新核对进料板，比较同产品热量和设备负荷。

每个候选都必须在同一产品基准下比较。流量、级数、温压或负荷变化时，按上述阶段调用规则调用知识与设备检查，再交塔设计模块核对水力学；有真实能力限制才评估并联等方案。合格塔岛逐个接回全流程，并用新的入口和循环重新验证，不能把岛内最优点直接当整厂最优。

## Authority First

Read `references/ERROR_MEMORY.md`, the chemical expert's strict
acceptance/learning policy, and the current project change-offset plus tower
ledger. Upstream `aspen-document-driven-flowsheet` owns route, feed,
products and property/phase model; operations owns mechanical cards and the
single strict Summary/history implementation.

## Choose the route

Ordinary key-based distillation may use DSTWU after source, feed, keys,
recoveries, pressure and targets are frozen. Preserve a user-required
DSTWU→RadFrac sequence; the initialization values come from that task, not
an old taught multiplier.

For azeotropic/extractive, absorber/stripper, VLL/reactive or no-meaningful-key
duties, record why shortcut assumptions do not apply and use the authorized
rigorous route. Do not silently substitute a different required method.

## Do the next stage, then verify

调回流、采出、溶剂、压力或热负荷前，按
[内置工具规则](../aspen-document-driven-flowsheet/references/aspen_builtin_solve_fit_tools.md)
完成工具分类和工作过程要求的实际岛阶段检查。找指定指标用 live SPEC/VARY；看未知响应先 Sensitivity，
已有同版有效区间可复用；多个连续变量在产品约束下寻优先评估原生 Optimization。
普通精馏先在DSTWU选定的初始级数下比较进料板，再调整级数；二者均属外层
离散候选，每个候选内重解塔内质量控制，不固定旧RR或D/F。吸收/再生塔同样
不得把级数或进料板当作内层连续Vary。
特殊塔先画明原料气进吸收塔、净化气出塔、贫液进塔、富液去再生、
再生贫液返回的真实物料方向；级数/接触段数/进料位置只作外层结构候选。
塔内 SPEC/VARY 只配来源允许、可连续写入且有界的真实操作量，
没有这样的自由度时保留局部待解，不用级数填空。
若吸收塔内 SPEC 以溶剂循环量为 Vary，本轮 Calculator 不得再写
该循环量；比例公式至多给一次初值，或另算不占用 Vary 的补液等输入。
若来源要求比例公式每轮写循环量，就改找独立 Vary 或标目标待解。
净化上限保留不等式验收，等式型 SPEC 需有据设定点。

交出求解方案时列明外层变量、产品约束，以及每个必要内层目标对应的独立操纵量、
边界和主写入者。只写“逐点重解质量目标”不构成控制配对。未有资料证明另一个
获准自由度时，明确记录内层操纵量尚未确定；保留“至少/不超过”为直接不等式，
不能为配 Design Spec 擅自把它改成等式，也不能让内外两层争用同一变量。

`target/property freeze -> shortcut or justified rigorous initialization ->
converged baseline -> establish/reuse bounded response evidence -> live SPEC/VARY -> full-flow
reconnect -> hydraulics/equipment/pressure -> strict same-file verification`

Reconnect applies when a real parent section/full-flow is in the authorized
task. A standalone tower task returns an accepted-for-scope island and its
boundary contract; it does not fabricate a larger plant.

Read `references/tower_optimization_workflow.md` when executing the stage,
special-column or hydraulic details. Use an optional user-supplied local textbook graph and the legally installed
current Aspen help for fragile card rules; source bodies are not bundled.

- Define a real target, bounded manipulated input, units and applicability for
  each spec. A fixed offline sweep is not a live Design Spec.
- Every outer optimization point re-solves the authorized inner quality
  controls. Compare energy/cost only for matching capacity, purity and recovery.
- Conflicting specs are diagnosed; no target is silently dropped and no
  precision is relaxed to obtain a strict pass.
- Pressure drops, reflux, stage count, HETP, packing and capacity limits require
  current source/geometry/traffic evidence. There are no global pressure-drop,
  inlet-pressure-fraction or old project purity defaults.
- Parallel towers require attributable capability/whole-system justification
  and actual same-basis reconnect verification. Equal splitting is an
  assumption to verify, not a rule for every multi-train design.
- A converged material tower or HYDRAULIC=NO case is not a software hydraulic
  rating. Keep material, source-static, preliminary, software and vendor/
  mechanical evidence levels separate.
- Use `chemical-tower-design` and the expert's equipment-feedback gate for
  section/load-case envelopes and downstream geometry/cost/report propagation.
  Use the dedicated heat-pump replacement skill for VRC/MVR.

## Return contract

Return current tower ledger, same-run feeds/products, live spec/residuals,
pressure/heat/power, hydraulic/selection state and exact-file evidence.
All strict Summary counts for the supported real schema and actual raw
history must pass; products and full-flow gates remain additional requirements.

A relaxed local result is labeled case-only and excluded with all descendants
from learning/default retrieval. Historical case examples and prior entry archives are not distributed; optional
same-case local evidence never becomes a generic default.

阶段收尾若发现有证据且值得复用的新方法或原则，将候选交主助手，按
[主动经验提醒](../chemical-engineering-expert/references/EXPERIENCE_INBOX.md#主动提醒使用者)
展示可审阅摘要并推进确认/投稿；拒绝不催促，已有有效授权不重复询问。
