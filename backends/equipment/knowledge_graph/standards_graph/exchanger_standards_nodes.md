# Exchanger Standards Nodes

## 设备族覆盖

| 族节点 | 覆盖对象 |
| --- | --- |
| `family_exchanger` | 壳管式换热器 |
| `family_fixed_tubesheet_exchanger` | 固定管板换热器 |
| `family_floating_head_exchanger` | 浮头换热器 |
| `family_heat_exchanger_network` | 换热网络/系统优化 |

## 来源节点

| 节点ID | 来源 | method/supplies | boundary |
| --- | --- | --- | --- |
| `handbook_exchanger_mech_A/B` | 化工机械手册 换热器 | 结构型式、部件认知、经验范围入口 | 手册经验值不可迁移；不替代 EDR/SW6/厂家 |
| `book_exchanger_design_A/B/C` | 化工设备设计全书 换热器设计 | 热负荷、LMTD、U、面积、污垢、流速、压降方法 | 教材示例值不可迁移 |
| `case_exchanger_course` | 化工原理课程设计-换热器设计 | 课程设计流程样例 | 案例工况/物性/尺寸/压降禁止迁移 |
| `case_exchanger_course_full` | 化工原理课程设计全册 | 模板和流程样例 | 例题数值禁止迁移 |
| `handbook_fixed_tubesheet` | 钢制列管式固定管板换热器结构设计手册 | 管束、管板、折流板、壳体、管箱、法兰、支承结构入口 | 结构尺寸/校核需同工况、EDR/SW6/厂家 |
| `case_floating_head_exchanger` | 浮头换热器毕业设计 | 浮头结构流程样例 | 毕业设计数值禁止迁移 |
| `book_heat_exchanger_network` | 换热器系统的模拟、优化与综合 | 夹点/网络/系统优化方法 | 不给单台换热器机械参数 |

## 参数判定

| 参数 | 标准图谱判定 |
| --- | --- |
| 热负荷 Q | 教材可作能量衡算方法；数值来自 Aspen |
| LMTD | 数学公式可用，复杂多程/相变正式值用 EDR |
| 总传热系数 U | 手册经验 U 不能替代 EDR |
| 污垢热阻 | 新增手册仅查取方法，不能自动改默认值 |
| 换热面积 A | 手算面积只作初筛；最终面积需 EDR |
| 管/壳程流速 | 手册经验范围只能作 sanity check |
| 允许压降 | 手册不替代项目压降分配；需 EDR/工艺包 |
| 管束/管板/折流板 | 固定管板手册可作结构入口，正式仍需 EDR/SW6 |

## 图谱边

- `book_exchanger_design_C -> method -> heat_duty_LMTD_U_area_pressure_drop`
- `handbook_exchanger_mech_A -> method -> exchanger_structure_type_and_parts`
- `handbook_fixed_tubesheet -> supplies -> fixed_tubesheet_structure_boundary`
- `handbook_fixed_tubesheet -> boundary -> tubesheet_baffle_nozzle_flange_requires_EDR_SW6_vendor`
- `case_exchanger_course -> boundary -> case_values_forbidden_transfer`
- `case_floating_head_exchanger -> method -> floating_head_structure_case_flow`
- `book_heat_exchanger_network -> method -> heat_integration_optimization`
- `family_exchanger -> requires -> Aspen_EDR_for_area_U_Re_pressure_drop_velocity`
- `family_exchanger -> requires -> SW6_for_tubesheet_flange_opening_strength`

---
离线迁移说明：本文件保留原图谱的方法与边界正文；同案数值、私有审计及未随包的原件不作公共输入。来源及字段级剔除记录见 `../RESTORATION_PROVENANCE.json`。本节点不升级原计算或证据状态。
