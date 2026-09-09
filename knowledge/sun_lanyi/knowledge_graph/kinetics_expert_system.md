# 反应动力学专家系统

来源主文件：

- `../chapter_extracts/ch08b_reactions_kinetics_cards.md`
- `../chapter_extracts/ch08c_rcstr_cards.md`
- `../chapter_extracts/ch08d_rplug_cards.md`
- `../chapter_extracts/ch08e_rbatch_cards.md`
- `../chapter_extracts/ch08f_kinetics_parameter_card_audit.md`
- `kinetics_freeze_template.md`

本文件是 Codex 填 Aspen Plus 动力学反应卡片前的强制入口。

## 1. 最高规则

动力学必须先冻结，后填卡。

完整链条为：

`source equation/value -> source units -> conversion -> Aspen card units -> exact Aspen input -> exported verification`

缺任一环，状态只能是 `blocked` 或 `provisional`，不能交付为正式动力学。

## 2. 对象层级

| 层级 | Aspen 路径 | 作用 |
| --- | --- | --- |
| 反应集 | `Reactions|Reactions` | 创建 `POWERLAW`、`LHHW` 或 `USER` 反应对象 |
| 化学计量 | `Reactions|<ID>|Input|Stoichiometry` | 逐条反应定义组分、计量系数、反应类型、PowerLaw 指数 |
| 动力学参数 | `Reactions|<ID>|Input|Kinetic` | 填相态、速率基准、单位、浓度基准、`k/n/E/To` 或 LHHW 子项 |
| 反应器挂接 | `Blocks|<RCSTR/RPLUG/RBATCH>|Setup|Reactions` | 把 reaction set 从 `Available` 移入 `Selected` |

反应集创建成功不等于反应器已调用；反应器挂接成功也不等于参数正确。

## 3. 先判断模型族

| 源速率式 | Aspen 方向 | 门禁 |
| --- | --- | --- |
| 幂律浓度项，无遮挡分母、无正逆推动力差 | `POWERLAW` | 级数、相态、基准、`k/E` 单位闭合 |
| 动力学因子 × 推动力 / 吸附表达式 | `LHHW` | 驱动力、吸附常数、指数、温度函数全部可映射 |
| 分段函数、复杂活度/逸度、失活、扩散修正、非标准结构 | `USER` | Fortran 源码、接口、编译、测试点齐全 |
| 只有转化率/收率/出口组成 | 非动力学反应器或阻断 | 不得伪装成动力学 |

## 4. Stoichiometry 审计

- `Reaction type` 必须逐条设为 `Kinetic` 或 `Equilibrium`。
- `Reactants/Products | Coefficient` 只表示化学计量。
- `Exponent` 只在 `POWERLAW` 中直接表示速率级数。
- `Exponent` 空白默认 `0`，不是默认一级。
- 反应级数不等于计量系数，例如 `2A + B -> P` 可对应 `r = k C_A^1 C_B^0.5`。

阻断条件：

- 反应式未配平或组分 ID 不能映射 Aspen component。
- 用计量系数直接填指数，且没有源速率式支持。
- 多反应集未逐条切换 `Reaction No.` 核对。

## 5. Kinetic 通用字段

| 字段 | 含义 | 填写规则 |
| --- | --- | --- |
| `Units` | 动力学参数单位制 | 与换算后的 `k/E` 一致；例题 `ENG` 不是通用默认 |
| `Reacting phase` | 反应发生相态 | 来自源方程、实验说明或反应器假设 |
| `Rate basis` | 速率控制基准 | 决定 `k` 量纲；反应体积、相体积、催化剂质量、床层体积不可混用 |
| `[Ci] basis` | 浓度基准 | `Molarity`、分压、摩尔分率等必须与源式换算闭合 |
| `k` | 指前因子/速率常数 | 按当前单位、级数、相态、基准换算后填 |
| `n` | 温度幂指数 | 源式没有 `T^n` 或 `(T/To)^n` 时不得随意填 |
| `E` | 活化能 | 确认 Aspen 公式为 `exp(-E/RT)` 后再换算 |
| `To` | 参考温度 | 只有源式采用参考温度形式时才填 |

`exp(-B/T)` 特别规则：`B` 是温度参数，不是能量。只有目标卡片确认为 `exp(-E/RT)` 时，才按 `E = B * R` 转换，并记录 `R` 单位。

## 6. PowerLaw

允许使用的条件：

- 源方程可写成 `rate = k * product(C_i^a_i)` 与 Aspen 温度项组合。
- 没有吸附分母、产物抑制、正逆推动力差、覆盖度联立或非标准活度项。
- 速率基准和浓度基准能换算到 Aspen 卡片。

必须逐项冻结：

- 每个组分的 `Exponent`。
- `k` 的量纲：`rate units = k units * product([Ci] units ^ exponent_i)`。
- `E/n/To` 与 Aspen 温度函数。
- 源式如果基于分压，不得直接把分压常数填入 `Molarity` 基准。

## 7. LHHW

讲义结构：

`r = [Kinetic factor][Driving force expression] / [Adsorption expression]`

关键子项：

- `Kinetic factor`：`k/n/E/To`。
- `Driving Force`：正反应 `Term 1` 与逆反应 `Term 2`。
- 推动力常数：`ln K_l = A_l + B_l/T + C_l ln T + D_l T`。
- `Adsorption`：吸附表达式指数 `m`、浓度指数、吸附常数。
- 吸附常数：`ln K_i = A_i + B_i/T + C_i ln T + D_i T`。

硬规则：

- 只有源方程确实无吸附影响时，才可令 `m = 0`。
- 缺失推动力或吸附参数时阻断，不用 PowerLaw 代替。
- 讲义注明 LHHW 不适用于反应精馏系统；遇到反应精馏要回 `ch10b` 与 `ch08b` 交叉判定。

## 8. USER

使用条件：

- `POWERLAW` 和 `LHHW` 不能表达源模型。
- 源模型要求保留复杂函数、活度/逸度、失活、扩散修正或特殊速率基准。

可用门禁：

- 有 Fortran 子程序源码。
- 有子程序名称、接口变量、参数定义。
- 有单位、相态、基准说明。
- 有编译证据和至少一个速率测试点。
- 有 Aspen 导出验证。

缺任何一项，一律 `blocked`。

## 9. 反应器联动

### RCSTR

- 本体路径：`Blocks|RCSTR|Setup|Specifications`。
- 压力必定；温度/热负荷二选一；体积/停留时间二选一。
- `Valid phases` 必须与反应相一致。
- 多出口时检查 `Streams` 页逐股出口相态。
- 完全混合假设下，出口状态代表釜内状态；动力学相态和速率基准受此影响。

### RPlug

- 本体路径：`Blocks|RPLUG|Setup|Specifications` 与 `Configuration`。
- 需规定管长、管径、管数或压降，以及与 reactor type 对应的温度/传热参数。
- `Reactor type` 由温度/传热边界决定：指定温度、绝热、恒定热媒温度、并流热媒、逆流热媒。
- 例 8.6 的 `Units=ENG`、`Vapor`、`Molarity` 和 `k/E` 只属于该例题。

### RBatch

- 只用于间歇或半间歇动力学反应。
- 间歇总量、流股基准流率、`Batch feed time` 必须闭合：`总量 = 基准流率 × Batch feed time`。
- `Stop Criteria` 决定周期结束；多个判据任一满足即停止。
- `Operation Times` 中的 `Maximum calculation time` 与输出 profile 间隔不是停止条件。

## 10. 阻断清单

- 没有源速率方程。
- 有 `k` 但没有单位。
- 不知道 `Rate basis` 或 `[Ci] basis`。
- 不知道反应相态。
- `exp(-B/T)` 未转换就填入 `E`。
- 分压、活度、逸度、摩尔分率未换算就填 `Molarity`。
- 催化剂质量或床层体积基准没有装填量/密度/体积换算。
- LHHW 被压成 PowerLaw。
- USER 没有源码/接口/测试。
- 只从旧 Aspen、旧对话、模板或能跑案例复制数值。
- Aspen 输入后没有导出卡片或截图验证。

## 11. 一页冻结口令

开始填任何动力学卡前，先建立 `kinetics_freeze_template.md` 副本，并回答：

1. 速率式原文是什么？
2. 源单位是什么？
3. 这是 `POWERLAW`、`LHHW` 还是 `USER`？
4. 反应级数是否逐组分有来源？
5. `k` 的量纲是否随级数和基准重算？
6. `E` 或 `B/T` 是否按 Aspen 目标公式转换？
7. 反应器的相态、体积、停留时间、压降、温度或操作周期是否会改变速率解释？
8. 是否有 Aspen 导出验证？

回答不清就不填正式参数。

