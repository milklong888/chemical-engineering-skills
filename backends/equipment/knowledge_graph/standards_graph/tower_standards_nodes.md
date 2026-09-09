# Tower Standards Nodes

## 设备族覆盖

塔设计步骤技能：包内 `chemical-tower-design`；原文查询需用户另行提供本地源层。
结构化事实由后台 Agent `knowledge_search` 的 `design_standards` 包查询；原文/页图是可选用户资料，未随本包提供。节点正文不替代源页。

| 族节点 | 覆盖对象 |
| --- | --- |
| `family_tower` | 精馏塔、填料塔、塔式容器 |
| `family_nozzle_pipe` | 塔接管/标准钢管 |
| `family_packing` | 填料、填料支承、塔内件 |
| `family_tower_strength` | 壳体、封头、裙座、开孔 |

## 来源节点

| 节点ID | 来源 | supplies/method | boundary |
| --- | --- | --- | --- |
| `std_NB_T47041_2014` | NB/T 47041-2014 塔式容器 | 塔体、封头、裙座、开孔、塔式容器设计方法入口 | 壁厚、裙座、开孔等正式结论需完整输入/SW6 |
| `std_SH_T3098_2011` | SH/T 3098-2011 石油化工塔器设计规范 | 塔器设计方法、内件、支承、载荷、液泛/压降方法入口 | 不能替代 Column Internals 或 SW6 |
| `std_GB_T17395_2024` | GB/T 17395-2024 钢管尺寸、外形、重量及允许偏差 | 标准管尺寸、公差、重量入口 | 接管强度和补强仍需校核 |
| `std_GB_T8163_2018` | GB/T 8163-2018 输送流体用无缝钢管 | 无缝钢管规格入口 | 不自动证明材质/强度适用 |
| `std_GB_T12771_2019` | GB/T 12771-2019 流体输送用不锈钢焊接钢管 | 不锈钢焊接钢管规格入口 | 不替代接管补强 |
| `std_GB_T25198_2023` | GB/T 25198-2023 压力容器封头 | 封头型式、几何尺寸、制造要求入口 | 封头厚度/强度需设计条件和 SW6 |
| `std_GB_T18749_2019` | GB/T 18749-2019 耐化学腐蚀陶瓷塔填料技术条件 | 陶瓷填料规格/技术条件入口 | 不证明结构填料 HETP、液泛、压降 |
| `std_HG_T21514_2005` | HG/T 21514-2005 钢制人孔和手孔 | 人孔/手孔型式和尺寸入口 | 补强需 SW6 |
| `std_HGJ_211_85` | HGJ 211-85 化工塔类设备施工及验收规范 | 施工、安装、验收方法 | 不是设计参数源 |
| `std_JB_T4712_2007` | JB/T 4712-2007 鞍座标准 | 卧式容器鞍座入口 | 不是塔裙座主源 |

## 当前报告参数判定

| 参数 | 标准图谱结论 |
| --- | --- |
| 接管 | 标准管规格可接 `GB/T 17395-2024`，但需表页核验 |
| 塔径 | 标准只方法，正式证据仍是 Aspen |
| %Capacity/液泛/压降 | 标准不可替代 Aspen 水力学数据库 |
| 填料 HETP | `GB/T 18749-2019` 只对陶瓷填料适配，不能替代结构填料厂家 |
| 壁厚/裙座/开孔 | 标准提供方法入口，正式仍需 SW6 |
| 施工验收 | `HGJ 211-85` 仅挂施工边界 |

## 图谱边

- `std_NB_T47041_2014 -> method -> tower_shell_head_skirt_opening_design`
- `std_NB_T47041_2014 -> boundary -> tower_strength_requires_design_inputs_and_SW6`
- `std_SH_T3098_2011 -> method -> tower_internal_layout_flooding_pressure_drop`
- `std_SH_T3098_2011 -> boundary -> column_hydraulics_requires_Aspen_Column_Internals_or_vendor`
- `std_GB_T17395_2024 -> supplies -> pipe_dimensions_weights_tolerances`
- `std_GB_T17395_2024 -> refines -> formula_nozzle_actual_velocity`
- `std_GB_T25198_2023 -> supplies -> head_type_geometry`
- `std_GB_T25198_2023 -> boundary -> head_thickness_requires_strength_check`
- `std_HG_T21514_2005 -> supplies -> manhole_handhole_type_size`
- `std_HGJ_211_85 -> boundary -> not_design_parameter_source`
- `family_tower -> workflow -> chemical-tower-design`
- `chemical-tower-design -> queries -> standards_graph.source_layer`
- `tower_geometry_change -> invalidates -> active_area_hydraulics_mechanics_drawings`

---
离线迁移说明：本文件保留原图谱的方法与边界正文；同案数值、私有审计及未随包的原件不作公共输入。来源及字段级剔除记录见 `../RESTORATION_PROVENANCE.json`。本节点不升级原计算或证据状态。
