# L3-07 局部强化只有在系统负担下降时才算改进

- `knowledge_layer`: L3_worldview
- `status`: active_source_backed_and_cross_checked
- `source_scope`: 教材通用知识与化工专家宏观设计规则

## 思想

增大传热/传质系数、推动力、流速、压差或外力，可能缩小局部面积/高度，
也可能同时增加泵压缩功、夹带、液泛、磨损、污染、温降/压降、产品损伤、
再生负荷和控制脆弱性。局部指标变好并不等于系统总目标变好。

强化应被写成一条因果链：

`操作变化 -> 机制/控制阻力变化 -> 局部能力 -> 能量/压降/相态/负荷传播
-> 上下游与控制影响 -> 安全环境经济结果`

只有在相同产品、处理量、边界和风险基准上比较，才能判断净改进。

## 设计含义

- 先找控制阻力或真正瓶颈，不平均地“全面加大”；
- 检查强化是否把负担推给换热、压缩、分离剂再生、下游精制或废物处理；
- 对热敏/易损产品，把质量和停留时间纳入目标；
- 比较名义、低负荷、启动、污染/结垢和扰动工况；
- 保留旁路、清洗、维护和失效后的可达安全状态。

## 下行证据

- `CEPR-UPPER-WANG-HE`, PDF p14：单元强化应服务于整体过程优化。
- `CEPR-UPPER-WANG-HE`, PDF p221：传热由流动、物性、几何与边界层共同决定。
- `CEPR-LOWER-PAN-WU`, PDF p151：传质单元高度/系数同时受物系、
  操作和设备结构影响。
- `CEPR-LOWER-PAN-WU`, PDF p244–245：干燥需同时评价产品质量、
  经济性、环境和能量系统集成。
- OCR：`../../source_pages/upper/page_0221.txt`,
  `../../source_pages/lower/page_0151.txt`,
  `../../source_pages/lower/page_0244.txt`。
- 系统级判据：
  `../../../skill_packages/chemical-engineering-expert/references/MACRO_DESIGN_QUALITY.md`。

本节点不定义通用强化倍数、压降、效率或经济权重；这些必须在当前项目边界
内计算或验证。
