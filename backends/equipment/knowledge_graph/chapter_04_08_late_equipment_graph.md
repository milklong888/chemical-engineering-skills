# Chapter 04-08 Late Equipment Graph

本节点保留原图谱第4—8章设备族的方法、参数来源和证据边界。原项目覆盖结论及 ledger 为可选本地资料，不随包提供。

## 第四章：气液分离器

### 节点

- `chapter_04_separator_design -> maps_to -> family_separator`
- `family_separator -> method -> gravity_separator_sizing`
- `family_separator -> method -> demister_velocity_check`
- `family_separator -> uses_formula -> formula_separator_souders_brown`
- `family_separator -> uses_formula -> formula_nozzle_required_diameter`
- `family_separator -> uses_formula -> formula_nozzle_actual_velocity`
- `family_separator -> uses_formula -> formula_cylinder_thickness`
- `family_separator -> boundary -> vendor_or_standard_for_demister`

### 参数源

| 参数 | 来源优先级 |
| --- | --- |
| 气/液相流量、密度、T/P、相分率 | Aspen或同案流股表 |
| 液滴粒径、允许夹带率 | 人工/规范/厂家 |
| 丝网允许气速系数K | 规范/厂家/文献 |
| 筒体/封头/接管尺寸 | 文档表格+标准/SW6边界 |

## 第五章：压缩机

### 节点

- `chapter_05_compressor_selection -> maps_to -> family_compressor`
- `family_compressor -> uses_formula -> formula_pressure_ratio`
- `family_compressor -> uses_formula -> formula_isentropic_compression_work`
- `family_compressor -> boundary -> vendor_curve_required`

### 参数源

| 参数 | 来源优先级 |
| --- | --- |
| 入口/出口T/P、组成、体积流量 | Aspen/文档流股表 |
| MW、k、Z | Aspen/物性包 |
| 等熵/多变效率 | 厂家/人工默认 |
| 型号、电机功率/轴功率 | 厂家样本/目录表 |

## 第六章：储罐/回流罐/缓冲罐

### 节点

- `chapter_06_storage_reflux_buffer -> maps_to -> family_storage`
- `family_storage -> uses_formula -> formula_inventory_volume`
- `family_storage -> uses_formula -> formula_tower_holdup`
- `family_storage -> uses_formula -> formula_cylinder_thickness`
- `family_storage -> boundary -> tank_code_and_breathing_required`
- `family_storage -> routes_to_standard_nodes -> standards_graph/vessel_standards_nodes.md`

### 参数源

| 参数 | 来源优先级 |
| --- | --- |
| 密度、蒸气压、操作T/P | Aspen |
| 储存天数/停留时间 | 人工/设计任务书 |
| 装填系数、液位 | 规范/人工 |
| 呼吸阀/氮封/防火间距 | 规范/安全设计 |
| 规格、公称容积、设计T/P、材料、标准序号 | 文档表格 |

## 第七章：管道混合器/膜

### 节点

- `chapter_07_pipeline_mixer -> maps_to -> family_static_mixer`
- `chapter_07_membrane -> maps_to -> family_mixer_membrane`
- `family_static_mixer -> uses_formula -> formula_mixer_reynolds`
- `family_static_mixer -> uses_formula -> formula_mixer_pressure_drop`
- `family_mixer_membrane -> uses_formula -> formula_membrane_area_geometry`
- `family_static_mixer -> boundary -> vendor_mixing_performance_required`
- `family_mixer_membrane -> boundary -> membrane_vendor_or_literature_required`

### 参数源

| 参数 | 来源优先级 |
| --- | --- |
| 入口物流流量、密度、黏度 | Aspen |
| 允许压降 | 工艺包/人工 |
| 混合均匀度、单元数、压降曲线 | 厂家 |
| 膜面积、通道数、长度 | 文档几何表 |
| 膜通量、选择性、回收率、寿命 | 厂家/文献 |

## 第八章：泵/透平/倾析器

### 节点

- `chapter_08_pump_selection -> maps_to -> family_pump`
- `family_pump -> uses_formula -> formula_pump_hydraulic_power + formula_pump_shaft_power`
- `family_pump -> uses_formula -> formula_NPSHa`
- `family_pump -> boundary -> pump_vendor_curve_required`

### 参数源

| 参数 | 来源优先级 |
| --- | --- |
| 流量、密度、蒸气压、入口压力 | Aspen |
| 扬程、管损 | 管路计算/报告 |
| 效率、NPSHr、BEP | 厂家曲线 |
| 轴功率/电机功率 | 计算+厂家 |
| 透平效率/功率 | 厂家+Aspen密度 |
| 倾析器分离性能 | 液液相平衡/厂家能力 |

## 可新增/已新增脚本函数

| 公式族ID | 公式 | 适用章节 | 前置证据 |
| --- | --- | --- | --- |
| `formula_separator_souders_brown` | `u_allow=K*sqrt((rho_l-rho_v)/rho_v)` | 第四章 | K、密度、液滴/丝网依据 |
| `formula_nozzle_actual_velocity` | `u=4Q/(pi*d_i^2)` | 第四章 | 相态流量、目标流速标准 |
| `formula_pressure_ratio` | `Pout/Pin` | 第五章 | 同工况入口/出口压力 |
| `formula_inventory_volume` | `V=flow*time/fill_fraction` | 第六章 | 流量/密度、停留时间、装填系数 |
| `formula_membrane_area_geometry` | `A=N*pi*d_i*L` | 第七章 | 通道数、内径、长度、元件数 |
| `formula_pump_hydraulic_power` | `Ph=rho*g*Q*H` | 第八章 | 密度、流量、扬程 |
| `formula_pump_shaft_power` | `Pshaft=rho*g*Q*H/eta` | 第八章 | 密度、流量、扬程、效率 |
| `formula_NPSHa` | `NPSHa=(P_suction-P_vapor)/(rho*g)+z-h_f` | 第八章 | 吸入压力、蒸气压、液位、管损 |
| `formula_isentropic_compression_work` | 等熵/多变压缩功 | 第五章 | MW、k、Z、效率、压比 |
| `formula_mixer_reynolds` | `Re=rho*u*D/mu` | 第七章 | 密度、黏度、管径、流量 |

---
离线迁移说明：本文件保留原图谱的方法与边界正文；同案数值、私有审计及未随包的原件不作公共输入。来源及字段级剔除记录见 `RESTORATION_PROVENANCE.json`。本节点不升级原计算或证据状态。
