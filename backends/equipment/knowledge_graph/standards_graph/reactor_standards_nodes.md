# Reactor Standards Nodes

## 设备族覆盖

| 族节点 | 覆盖对象 |
| --- | --- |
| `family_fixed_bed_reactor` | 固定床/换热型反应器 |
| `family_agitated_reactor` | 搅拌釜式反应器/搅拌容器 |
| `family_reactor_opening` | 人孔、手孔、接管开口 |
| `family_kinetics_boundary` | 反应动力学输入边界 |

## 来源节点

| 节点ID | 来源 | supplies/method | boundary |
| --- | --- | --- | --- |
| `std_HG_T20569_2013` | HG/T 20569-2013 机械搅拌设备 | 搅拌器型式、桨/挡板/轴封、搅拌设备布置查表入口 | 不能直接给本项目功率、转速、桨径；需标准表页、介质和厂家/机械校核 |
| `std_HG_T21514_2005` | HG/T 21514-2005 钢制人孔和手孔 | 人孔/手孔类型、压力等级、标准尺寸入口 | 开孔补强、法兰强度、壳体强度需 SW6 |
| `txt_Luyben_reactor_design` | Chemical Reactor Design and Control | 反应器类型选择、停留时间、体积、控温/移热、控制结构方法 | 教材不是规范；示例值禁止迁移 |
| `txt_CN_reactor_selection` | 化学反应过程与设备：反应器选择、设计和操作 | 固定床/釜式/管式选型、停留时间-体积、压降和传热方法 | 不提供正式 Aspen 动力学卡片；数值不可迁移 |

## 参数判定

| 参数 | 标准图谱判定 | 下一证据 |
| --- | --- | --- |
| 催化剂量、管束直径、传热面积 | 教材只作方法源，不构成同案结果 | 若正式设计，补结构/SW6 |
| Ergun 压降 | 反应器教材可支持方法，但粒径/空隙率/物性来自项目 | Aspen 物性和床层输入 |
| 传热系数/面积 | 教材可支持传热方法；热媒侧系数和污垢热阻仍是人工/文献边界 | Aspen/EDR 或专门换热校核 |
| 设计 T/P | 新增目录无直接条文数值 | 项目工艺边界、容器规范、SW6 |
| 动力学 | 禁止从教材迁移 | kinetics freeze chain |
| 搅拌功率/尺寸 | `HG/T 20569-2013` 可作为后续查表入口 | 搅拌功率计算、厂家/标准表、SW6 |
| 反应器人孔/手孔 | `HG/T 21514-2005` 可作为标准型式入口 | 开孔补强/SW6 |

## 图谱边

- `std_HG_T20569_2013 -> supplies -> agitator_type`
- `std_HG_T20569_2013 -> supplies -> impeller_geometry_table_entry`
- `std_HG_T20569_2013 -> supplies -> shaft_seal_baffle_layout`
- `std_HG_T20569_2013 -> boundary -> numeric_power_speed_requires_medium_and_table`
- `std_HG_T21514_2005 -> supplies -> reactor_manhole_handhole_type`
- `std_HG_T21514_2005 -> boundary -> opening_reinforcement_requires_SW6`
- `txt_Luyben_reactor_design -> method -> reactor_type_selection`
- `txt_Luyben_reactor_design -> method -> heat_removal_control_logic`
- `txt_CN_reactor_selection -> method -> fixed_bed_volume_pressure_drop`
- `txt_CN_reactor_selection -> boundary -> example_values_forbidden_transfer`
- `family_fixed_bed_reactor -> requires -> source_aspen_stream`
- `family_fixed_bed_reactor -> requires -> kinetics_freeze_chain_if_kinetic`

---
离线迁移说明：本文件保留原图谱的方法与边界正文；同案数值、私有审计及未随包的原件不作公共输入。来源及字段级剔除记录见 `../RESTORATION_PROVENANCE.json`。本节点不升级原计算或证据状态。
