# L3-05 热量既有数量也有温位：先减负荷、再回收、后升级

- `knowledge_layer`: L3_worldview
- `status`: active_source_backed_and_cross_checked
- `source_scope`: 教材通用知识与化工专家宏观设计规则

## 思想

能量衡算只说明数量闭合，不能说明某一热源能够在所需温度下完成加热。
高温/高品位公用工程不应被当作默认入口。合理顺序是：

1. 减少不必要的加热、蒸发、过度纯化和反复相变；
2. 用温度匹配的过程热直接预热或回收；
3. 调整流程顺序、压力和温位，保存并级联利用可用热；
4. 对合适蒸汽/热源评估多效、闪蒸、蒸汽再压缩或热泵升级；
5. 仅为剩余且确需该温位的热负荷选择最低充分外部公用工程。

压缩提高热源温度/压力的代价是轴功、设备和新的操作约束。回收热与压缩功
必须在同一边界闭合，不能把二者重复计作免费热量。

## 判断清单

- 热源与热汇的全程温度曲线和最小温差是否可行；
- 时间、负荷和相态是否匹配，是否需要储能或中间公用工程；
- 压缩吸入相态、清洁度、压比、效率、排气温度和设备范围是否合理；
- 新增面积、压降、旁路、启动、控制、清洗、失热源和备用热如何处理；
- 外供燃料/蒸汽与电功、资本、维护、碳排和可靠性是否用同一基准比较。

## 下行证据

- `CEPR-UPPER-WANG-HE`, PDF p14：节能、减排与整体过程优化的设计意义。
- `CEPR-UPPER-WANG-HE`, 第 4 章：温差、热阻和换热器约束。
- `CEPR-UPPER-WANG-HE`, PDF p302、p309、p319、p327、p329：
  蒸发衡算、多效潜热利用、二次蒸汽、压缩式热泵与闪蒸路线。
- `CEPR-LOWER-PAN-WU`, PDF p76–78：精馏节能须同时考虑能量品位、
  操作/序列/集成，热泵压缩存在适用条件，中间换热以传质或级数负担为代价。
- `CEPR-LOWER-PAN-WU`, PDF p244–245、p268–269：干燥前减小蒸发负荷，
  回收尾气热量，并区分系统节能与单元设备节能。
- L2 章节节点：`../chapter_nodes/CEPR-CH04-heat-transfer-and-exchangers.md`,
  `../chapter_nodes/CEPR-CH05-evaporation-and-heat-upgrading.md`,
  `../chapter_nodes/CEPR-CH06-distillation.md`,
  `../chapter_nodes/CEPR-CH09-drying.md`。
- 代表性 L0 锚点：
  `../../source_pages/lower/page_0076.txt`、
  `../../source_pages/lower/page_0077.txt`、
  `../../source_pages/lower/page_0078.txt`、
  `../../source_pages/lower/page_0244.txt`、
  `../../source_pages/lower/page_0268.txt`、
  `../../source_pages/lower/page_0269.txt`。
- 宏观实施边界：
  `../../../skill_packages/chemical-engineering-expert/references/MACRO_DESIGN_QUALITY.md`。

教材中的效数、压比、效率、经济指标和例题数据不进入本思想节点；项目采用
必须重建同案例热量、温位、压缩功、控制和经济边界。
