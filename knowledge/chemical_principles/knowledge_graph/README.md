# 化工原理知识图谱

本图谱是两本用户提供《化工原理》教材的分层检索入口。它补充化工专家
的通用物理常识，不替代项目权威、现行标准、同案例软件/实验结果或厂家
证据。

## 强制读取顺序

1. `00_ERROR_MEMORY.md`
2. `00_HIERARCHY.md`
3. `unknowns_router.md`
4. `knowledge_graph_index.md`
5. 相应 L3/L2/L1 节点
6. 仅在需要证明、公式或数字时下钻到 L0 本地证据索引和页文本

## 四层结构

| 层 | 作用 | 典型内容 | 检索优先级 |
| --- | --- | --- | --- |
| L3 | 思想与系统观 | 守恒、边界、平衡与速率、推动力与阻力、尺度、耦合、能量品位、可操作性 | 宏观/判断问题首先读取 |
| L2 | 原理与机制 | 流动、传热、传质、相平衡、颗粒与分离机制 | 解释“为什么” |
| L1 | 方法与模型 | 衡算、关联式、图解/逐级/传质单元方法、设计与校核路线 | 解释“怎样算” |
| L0 | 细节与来源 | 公式、符号、数字、例题、图表、PDF 页 OCR | 追溯/定量时读取 |

L3/L2/L1 图谱卡进入工作区全局向量索引；687 页 OCR 全文不进入全局
向量库，而保存在 `..\indexes\chemical_principles_evidence.sqlite`。这一
分离防止 L0 数量优势覆盖思想层。

当前上层节点为 8 个 L3、10 个 L2 和 5 个 L1（2026-09-09 增补工艺—设备反馈）。检索不是固定只读 L3：
宏观判断从 L3 开始，机制问题从 L2 开始，计算/筛选从 L1 开始，并保留
必要的上层约束和 L0 追溯链。

跨电脑接入见 `RAG_INTAKE_CROSSWALK.md`。常识查询可调用工作区
`integrations/github_20260909/rag_bridge.py`：复用当前卡与687页本地证据，
不把 GitHub 中另一电脑的聚合页数当成已下载内容。2026-07-24的构建/验证报告
保留为历史快照；本次接入验证位于 `integrations/github_20260909/validation/`。

## 证据状态

- L3/L2/L1 的综合节点必须链接到下层教材页或其他已验证来源。
- 页 OCR 是 `ocr_candidate`；普通正文可辅助检索，数字、公式、上下标、
  图表和适用范围必须回看原 PDF。
- 教材例题和设备参数只属于教学案例，禁止成为项目默认值。

## 源文件

源身份、SHA256、页数和使用边界见：

`..\source_registry.json`

章节与 PDF 页范围见：

`..\chapter_map.json`

L0 查询：

```text
python chemical_principles_knowledge\scripts\query_textbook_evidence.py <terms>
```

完整构建与视觉 QA 状态见：

- `..\extraction\build_report.json`
- `..\indexes\search_index_summary.json`
- `..\extraction\visual_qa_report.md`
- `..\extraction\source_audit_upper.md`
- `..\extraction\source_audit_lower.md`
- `..\extraction\validation_report.json`
- `..\extraction\ingestion_summary.md`
