# Formula Family Nodes

<a id="formula_nozzle_required_diameter"></a>
<a id="formula_nozzle_actual_velocity"></a>
<a id="formula_design_temperature_margin"></a>
<a id="formula_tower_holdup"></a>
<a id="formula_tower_height_sum"></a>
<a id="formula_cylinder_thickness"></a>
<a id="formula_head_thickness"></a>
<a id="formula_stream_balance"></a>
<a id="formula_column_internals_table"></a>
<a id="formula_LMTD"></a>
<a id="formula_exchanger_area_screening"></a>
<a id="formula_heat_transfer"></a>
<a id="formula_ergun"></a>
<a id="formula_arrhenius_fit"></a>
<a id="formula_separator_souders_brown"></a>
<a id="formula_inventory_volume"></a>
<a id="formula_cylindrical_geometry_volume"></a>
<a id="formula_pump_hydraulic_power"></a>
<a id="formula_pump_shaft_power"></a>
<a id="formula_pressure_head_rise"></a>
<a id="formula_pump_reverse_density"></a>
<a id="formula_NPSHa"></a>
<a id="formula_pressure_ratio"></a>
<a id="formula_isentropic_compression_work"></a>
<a id="formula_mixer_reynolds"></a>
<a id="formula_membrane_area_geometry"></a>
<a id="formula_mixer_pressure_drop"></a>

| 公式族ID | 公式/方法 | 适用设备 | 脚本能力 | 人工判定 |
| --- | --- | --- | --- | --- |
| formula_nozzle_required_diameter | `d=sqrt(4Q/(pi*u))` | 接管 | 理论管径 | Q单位/相态、目标流速 |
| formula_nozzle_actual_velocity | `u=4Q/(pi*d_i^2)` | 接管 | 选管后流速 | 标准管、腐蚀裕量、壁厚 |
| formula_design_pressure_factor | `P_design=k*P_op,g` | 容器/反应器/换热器 | 仅在 `k` 已由项目权威或用户明确时可复算 | `k` 的来源、适用设备与压力基准；通用节点不提供 `1.1` 默认值 |
| formula_design_temperature_margin | `T_design-T_max` | 容器/换热器/反应器 | 裕量范围校核 | 裕量来源与适用边界 |
| formula_tower_holdup | `(Q*t)/(piD^2/4)` | 塔/罐 | 库存高度初筛 | 内件/人孔/布置是否覆盖 |
| formula_tower_height_sum | `HD+HB+HR+packing+head+skirt` | 塔 | 塔高加和 | 各空间高度来源 |
| formula_cylinder_thickness | `PDi/(2sigma phi-P)` | 筒体 | 基础壁厚 | 材料/焊接系数/SW6边界 |
| formula_head_thickness | `PDi/(2sigma phi-0.5P)` | 封头 | 基础壁厚 | 同上 |
| formula_stream_balance | feed-outlets | 塔/分离器 | 质量/摩尔衡算 | 体积流量非守恒 |
| formula_column_internals_table | %Capacity/height/dP范围 | 塔 | 表读数审计 | 正式证据仍Aspen导出 |
| formula_LMTD | `DeltaT_lm=(DeltaT1-DeltaT2)/ln(DeltaT1/DeltaT2)` | 换热器 | 换热温差初筛 | 相变、多程修正和温度交叉需EDR/人工判定 |
| formula_exchanger_area_screening | `A=Q/(U*F*DeltaT_lm)` | 换热器/换热型反应器 | 面积初筛 | U、F、污垢热阻和相变区间来源 |
| formula_heat_transfer | Nu, U, A, margin | 固定床/换热器 | 可复算示例 | 物性平均、面积基准、热媒侧系数 |
| formula_ergun | Ergun pressure drop | 固定床 | 可复算 | 粒径/空隙率/表观速度来源 |
| formula_arrhenius_fit | `ln(k)=ln(A)-E/(RT)` | 动力学审计 | 表格算术审计 | 不能替代动力学冻结链 |
| formula_separator_souders_brown | `u_allow=K*sqrt((rho_l-rho_v)/rho_v)` | 气液分离器/丝网除沫 | 未来可脚本化 | K值、液滴/丝网依据、Aspen密度 |
| formula_storage_required_volume | `V_required=Q*t/phi_fill`（时间单位须一致） | 储罐/回流罐/缓冲罐 | 已脚本化所需总容积初筛 | `t`、`phi_fill` 和流量基准必须显式；不得与直筒几何容积或已选总容积混用 |
| formula_inventory_volume | `V_required=Q*t/phi_fill` | 储罐/回流罐/缓冲罐 | 旧 ledger 兼容别名，路由到 `formula_storage_required_volume` | 不构成另一套公式或默认停留时间/装填系数 |
| formula_cylindrical_geometry_volume | `Vstraight=pi*Di^2*Lstraight/4` | 储罐/分离器/卧式或立式圆筒 | 仅按明确筒体内径和圆筒直段长度复核直筒段几何容积 | 不得用设备总高或通用/公称直径回退；不含封头容积、液位、装填系数、内件和附件空间 |
| formula_pump_hydraulic_power | `Ph=rho*g*Q*H` | 泵 | 已脚本化 | 密度、流量、扬程、单位；这是传给液体的水力功率，不含效率 |
| formula_pump_shaft_power | `Pshaft=rho*g*Q*H/eta` | 泵 | 已脚本化 | 密度、流量、扬程、效率、单位；这是泵所需轴功率 |
| formula_pressure_head_rise | `H_ΔP=(P_out-P_in)/(rho*g)` | 泵 | 压力头分量初筛 | 不是完整系统总扬程；位差、速度头和管路损失必须另行闭合 |
| formula_pump_reverse_density | `rho=P*eta/(g*Q*H)` | 泵 | 用表中功率反推密度筛错 | 只作物理量级判断，不替代厂家曲线 |
| formula_NPSHa | `(P_suction-P_vapor)/(rho*g)+z-h_f` | 泵 | 未来可脚本化 | 吸入压力、蒸气压、液位、管损 |
| formula_pressure_ratio | 压缩 `PR=Pout_abs/Pin_abs`；膨胀 `ER=Pin_abs/Pout_abs` | 压缩机/真空压缩/膨胀机 | 压比/膨胀比筛错 | 必须确认绝压/表压基准、当地大气压、流向和压力单位 |
| formula_liquid_power_recovery | `H_delta_p=(P_in-P_out)/(rho*g)`；`P_delta_p=(P_in-P_out)*Q`；若显式给出效率，仅写入专用初筛字段 `P_screen,delta_p=eta*P_delta_p` | 液体膨胀机/液力透平 | 压差水头、压力功分量和压力分量轴功率初筛 | B类/`J`/`PROVISIONAL`，最高 `TYPE_SCREENING`；不得写入通用同工况轴功率，不证明总水力功率或实际可回收轴功率 |
| formula_isentropic_compression_work | 压比/等熵或多变压缩功 | 压缩机 | 未来可脚本化 | MW、k、Z、效率、级间条件 |
| formula_mixer_reynolds | `Re=rho*u*D/mu` | 管道混合器 | 未来可脚本化 | 流量、密度、黏度、管径 |
| formula_membrane_area_geometry | `A=N*pi*d_i*L` | 膜组件 | 几何膜面积复核 | 不证明通量、选择性、寿命或回收率 |
| formula_mixer_pressure_drop | 厂家阻力系数或局部阻力法 | 静态混合器 | 压降候选 | 阻力系数、元件数和混合均匀度需厂家/模型 |

兼容说明：旧参数 ledger 中若 `formula_pump_hydraulic_power` 同时写有 `/eta`，该旧链接按 `formula_pump_shaft_power` 解释并标记为历史命名错误，不得据此把轴功率重新称作水力功率。旧 `formula_inventory_volume` 链接仅作为 `formula_storage_required_volume` 的兼容入口，不得引入默认停留时间或装填系数。

## formula_design_pressure_factor

- 公式链：`P_design = k*P_op,g`。`P_op,g` 与 `P_design` 必须采用同一表压单位和同一工况边界。
- 必填输入：操作表压 `P_op,g`、项目设计压力系数 `k`，以及 `k` 的项目权威、适用规范条款或用户明确指定记录。
- 证据边界：乘法复算可作为 `D`，但 `k` 本身不是通用常数。缺少明确来源时仅返回缺项，不得静默采用 `1.1`，也不得用本项目历史样例反向定义其他设备的设计压力。
- 样例兼容：旧审计脚本中的 `1.1` 只在相应项目行显式传入，用于复现原审计数值；它不是本节点的默认值。

## formula_storage_required_volume

- 公式链：`V_required = Q*t/phi_fill`；例如 `Q` 用 `m3/h`、`t` 用 `min` 时，先显式换算为 `V_required = Q*t/(60*phi_fill)`。
- 必填输入：同一物料与工况基准的体积流量 `Q`、项目明确的停留/储存时间 `t`、项目明确的允许装填分数 `0<phi_fill<=1`。
- 输出含义：`V_required` 是在上述库存和装填假设下得到的**所需总容积初筛值**。代数计算可作为 `D`，但 `t` 与 `phi_fill` 保留各自的项目权威或 `J` 来源和适用性。
- 禁止混用：`V_required` 不等于直筒段几何容积 `V_cyl=pi*D^2*L/4`，也不等于目录、图纸或机械设计给出的选定/公称总容积 `V_selected`。直筒式不含封头容积；选定总容积还受封头、液位区、气相空间、操作余量、内件和附件等约束。
- 状态边界：该节点不能自行选定直径、长度、封头或标准规格，也不能证明呼吸、氮封、消防、结构或机械强度满足要求。

## formula_liquid_power_recovery

- 公式链：`P_delta_p = (P_in-P_out)*Q`，其中压力用 `Pa`、体积流量用 `m3/s`，结果为 `W`；仅当 `P_in>P_out` 且流体/流量基准明确时执行。
- 物理含义：`P_delta_p` 只是压差对应的功率分量。若显式给出适用于同工况的效率 `eta`，`eta*P_delta_p` 仍只记为压差分量上的筛选值 `P_screen`。
- 证据与状态：本节点整体为 B 类、`J`、`PROVISIONAL`，最高只能进入 `TYPE_SCREENING`。数值乘法可复算，不改变其设备解释的初筛上限。
- 禁止宣称：本节点不包含位能、动能、管路/阀门损失、机械损失、发电机及辅机效率、液体可压缩性、空化、两相/闪蒸、转速和性能曲线，因此既不证明总水力功率，也不证明实际可回收轴功率或发电功率。正式功率与型号必须由同工况完整能量衡算及厂家/软件性能证据闭合。

## 内置公式发布与告警规则

- 所有由应用内置公式生成的值都必须带结构化 `calculation_notice`，并在参数卡、公式页、HTML 和机器 JSON 中标明“非 Aspen / 用户直接输出”。
- A 类仅包含定义、几何或守恒恒等式；仍须满足显式输入、单位、相态、压力基准和物理方向门。应用不内置默认密度、效率、流速、停留时间、装填系数、材料或厂家参数。
- B 类包含公式分支、设计判断或初筛假设，证据类别为 `J`，状态固定为 `PROVISIONAL`，最高只能进入 `TYPE_SCREENING`。B 类公式不得覆盖用户、Aspen、EDR、SW6 或厂家提供的同工况值；只作带告警交叉核对。
- C 类为 EDR、SW6、Column Internals、厂家曲线、材料/许用应力、标准 DN 圆整和未冻结经验关联式。应用不得执行或猜值，只返回 `EXTERNAL_REQUIRED` 与最小补充字段。
- 首版经验默认注册表为空：`embedded_empirical_defaults_enabled=false`。以后新增任何经验范围，必须同时冻结来源版本、页/表/单元格、单位、介质/相态、温压适用范围、复用边界和回归测试。

---
离线迁移说明：本文件保留原图谱的方法与边界正文；同案数值、私有审计及未随包的原件不作公共输入。来源及字段级剔除记录见 `RESTORATION_PROVENANCE.json`。本节点不升级原计算或证据状态。
