# 新增知识主题与处理范围

## RE01：反应器与反应过程判断

本批新增 14 个完整知识块：反应器组合与选择性、停留时间分布、催化本征速率与传递限制、催化剂失活、固定床/流化床/气液反应模型，以及热稳定性和热点风险。按章节筛选、回读有用主题，不做全文转写；重复解释、例题数字和无新增用途的展开不单独入库。

内容达到“能无歧义复述其含义和必要条件”即可。资料内容通过不等于工程验证，项目仍需当前数据、物料/能量衡算和适用的安全检查。

可直接查询：

```text
python knowledge/scripts/query_knowledge.py --query "反应器组合 选择性 停留时间分布" --json
python knowledge/scripts/query_knowledge.py --query "固定床 孔内扩散 热稳定性" --vector --json
```

节点位于 [RE01 知识块目录](../chemical_principles/knowledge_graph/source_records/RE01/)，采纳范围见 [RE01 来源记录](../source_adoptions/RE01.json)。原有记录没有被重写或替换。

来源采用编号 `RE01`、原文件 SHA256 和每块 PDF 物理页锚追溯；完整文件身份保留在私有来源台账，原件不随包。这里公开的是新写的通用知识释义，不包含整页文字或例题数据，也不转授源材料权利。
