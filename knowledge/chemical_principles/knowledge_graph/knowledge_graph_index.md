# 化工原理分层知识索引

本索引按“思想统领细节”组织。宏观判断先进入 L3，机制问题进入 L2，
计算和筛选进入 L1；只有需要追溯、公式或数字时才进入 L0。

## L3 思想与系统观

| 节点 | 核心问题 |
| --- | --- |
| `concept_nodes/L3-01-conservation-equilibrium-rate.md` | 守恒、平衡边界与有限速率怎样共同约束设计 |
| `concept_nodes/L3-02-common-laws-and-case-specificity.md` | 哪些是通用规律，哪些必须由当前物系/设备/项目给出 |
| `concept_nodes/L3-03-unit-operations-as-a-coupled-system.md` | 为什么单元正确不等于流程合理 |
| `concept_nodes/L3-04-model-experiment-and-scale.md` | 模型、实验、相似与放大怎样分工 |
| `concept_nodes/L3-05-heat-cascade-recovery-and-upgrading.md` | 怎样按减量、回收、温位匹配、升温再利用处理高品位热公用工程 |
| `concept_nodes/L3-06-separation-mechanism-and-complete-route.md` | 怎样从可利用差异而非熟悉设备出发构造完整分离路线 |
| `concept_nodes/L3-07-local-intensification-and-system-burden.md` | 为什么局部强化必须检查全系统代价 |
| `concept_nodes/L3-08-equipment-realizability-feedback.md` | 为什么工艺与设备必须双向校核，调整后怎样证明流程仍合理 |

## L2 章节原理与机制

| 章节节点 | 主题 | 教材 PDF 页 |
| --- | --- | --- |
| `chapter_nodes/CEPR-CH01-introduction.md` | 绪论：单元操作共性与基本框架 | 上册 12–17 |
| `chapter_nodes/CEPR-CH02-fluid-flow-and-transport.md` | 流体流动与输送设备 | 上册 18–120 |
| `chapter_nodes/CEPR-CH03-mechanical-separation-and-fluidization.md` | 机械分离及流态化 | 上册 121–176 |
| `chapter_nodes/CEPR-CH04-heat-transfer-and-exchangers.md` | 传热过程与换热器 | 上册 177–300 |
| `chapter_nodes/CEPR-CH05-evaporation-and-heat-upgrading.md` | 蒸发及热量回收/升级 | 上册 301–331 |
| `chapter_nodes/CEPR-CH06-distillation.md` | 蒸馏 | 下册 14–113 |
| `chapter_nodes/CEPR-CH07-gas-absorption.md` | 气体吸收与解吸 | 下册 114–200 |
| `chapter_nodes/CEPR-CH08-liquid-liquid-extraction.md` | 液-液萃取与溶剂循环 | 下册 201–241 |
| `chapter_nodes/CEPR-CH09-drying.md` | 干燥：热质同时传递 | 下册 242–271 |
| `chapter_nodes/CEPR-CH10-other-separations.md` | 膜、吸附、离子交换与结晶等 | 下册 272–310 |

## L1 方法、模型与推导路线

| 方法节点 | 用途 |
| --- | --- |
| `method_nodes/L1-01-control-volume-balance-and-basis.md` | 冻结控制体、基准、物料/能量衡算和组分去向 |
| `method_nodes/L1-02-dimensionless-correlation-applicability.md` | 使用量纲分析和经验关联式时检查定义、适用域与尺度 |
| `method_nodes/L1-03-design-rating-and-whole-system-check.md` | 区分设计、校核与流程级复核 |
| `method_nodes/L1-04-separation-method-screening.md` | 从物性差异、推动力和完整回收/终端路线筛选分离方法 |
| `method_nodes/L1-05-process-equipment-iteration.md` | 设备能力诊断、分段/并联/分级候选、实际流程重算与逐台追溯 |

## L0 页证据

- 上册页文本：`../source_pages/upper/page_0001.txt` 至 `page_0371.txt`
- 下册页文本：`../source_pages/lower/page_0001.txt` 至 `page_0316.txt`
- 页面状态：`../extraction/page_manifest.jsonl`
- 本地证据库：`../indexes/chemical_principles_evidence.sqlite`
- 查询：`python chemical_principles_knowledge\scripts\query_textbook_evidence.py <terms>`

页 OCR 用于定位。数字、公式、上下标、图、表和曲线在视觉核对前均为
`ocr_candidate`，不得直接作为正式项目输入。

## 跨层与质量入口

- 层级及检索合同：`00_HIERARCHY.md`
- 未知问题路由：`unknowns_router.md`
- 近期本地工作映射（排除 openLCA）：`RECENT_WORK_CROSSWALK.md`
- 来源注册与章节页界：`../source_registry.json`、`../chapter_map.json`
- 上/下册来源审计：`../extraction/source_audit_upper.md`、
  `../extraction/source_audit_lower.md`
- OCR 构建与视觉抽查：`../extraction/build_report.json`、
  `../extraction/visual_qa_report.md`
- 索引摘要与整体验证：`../indexes/search_index_summary.json`、
  `../extraction/validation_report.json`
