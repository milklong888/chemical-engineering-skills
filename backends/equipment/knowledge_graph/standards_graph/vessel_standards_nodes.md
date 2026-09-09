# Vessel Standards Nodes

## 设备族覆盖

| 族节点 | 覆盖对象 |
| --- | --- |
| `family_pressure_vessel` | 一般立式/卧式钢制压力容器 |
| `family_high_pressure_vessel` | 高压容器 |
| `family_spherical_vessel` | 球形容器/球罐 |
| `family_vessel_support_opening` | 支座、开孔、补强 |

## 来源节点

| 节点ID | 来源 | method | boundary |
| --- | --- | --- | --- |
| `handbook_pressure_vessel_steel` | 化工机械手册——钢制压力容器设计 | 壳体、封头、开孔、支座的一般设计方法 | 手册示例值不可迁移；正式需标准条文/SW6 |
| `book_high_pressure_vessel_2003` | 化工设备设计全书 高压容器 2003 | 高压厚壁、加强、法兰/封头方法 | 高压设计必须完整规范链和 SW6/厂家校核 |
| `book_chemical_vessel` | 化工设备设计全书.化工容器 | 一般化工容器设计流程和术语 | 示例工况/厚度/补强/支座尺寸不可迁移 |
| `book_spherical_vessel` | 化工设备设计全书.球形容器设计 | 球壳、球罐支承、开孔方法 | 只适用于球形容器，不能外推到圆筒塔器 |
| `book_pressure_vessel_heat_transfer` | 压力容器与传热设备 | 承压设备和传热设备承压件基础方法 | 不给单台换热器正式结构参数 |

## 参数判定

| 参数 | 标准图谱判定 |
| --- | --- |
| 设计压力/温度 | 容器手册不能提供项目默认值；需项目边界 |
| 腐蚀裕量 | 只能保留人工默认/规范边界；不能从手册示例迁移 |
| 焊接接头系数 | 需 NDT 条件和规范条文；手册示例不可迁移 |
| 壳体/封头壁厚 | 手册可解释方法，正式需 SW6 |
| 开孔补强 | 必须 SW6 或完整规范计算 |
| 支座/裙座/鞍座 | 不同设备族不得互相迁移；卧式鞍座不等于塔裙座 |
| 球罐/高压容器 | 仅建未来路由，不能套一般容器默认值 |

## 图谱边

- `handbook_pressure_vessel_steel -> method -> shell_head_opening_support_design`
- `handbook_pressure_vessel_steel -> boundary -> handbook_example_values_forbidden_transfer`
- `book_high_pressure_vessel_2003 -> method -> high_pressure_thick_wall_design`
- `book_high_pressure_vessel_2003 -> boundary -> high_pressure_requires_full_code_SW6_vendor`
- `book_chemical_vessel -> method -> general_vessel_design_framework`
- `book_spherical_vessel -> method -> spherical_shell_support_opening`
- `book_spherical_vessel -> boundary -> not_for_cylindrical_tower_or_exchanger_shell`
- `book_pressure_vessel_heat_transfer -> method -> pressure_parts_for_heat_transfer_equipment`
- `family_pressure_vessel -> requires -> material_allowable_stress_weld_eff_corrosion_allowance`
- `family_vessel_support_opening -> requires -> SW6_or_full_code_check`

---
离线迁移说明：本文件保留原图谱的方法与边界正文；同案数值、私有审计及未随包的原件不作公共输入。来源及字段级剔除记录见 `../RESTORATION_PROVENANCE.json`。本节点不升级原计算或证据状态。
