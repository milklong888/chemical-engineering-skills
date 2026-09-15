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

## OC02：精馏动态控制与特殊分离

本批新增 13 个完整知识块，覆盖动态精馏的质量变量、温度代理、压力补偿、库存回路、串级/比值/前馈和稳态到动态的物理闭合，并延伸到萃取、变压、共沸与隔壁塔的可行性判断，以及热集成控制耦合、CO2 吸收—解吸循环负荷补偿、带中间罐的批式精馏和含反应/分离/回收的全流程案例。使用时可按“物系可分离性—流程拓扑—控制结构—流量/组成扰动”的问题顺序定位主题；这些内容提供章级方法与筛选条件，不把案例参数当默认设计值。

可直接查询：

```text
python knowledge/scripts/query_knowledge.py --query "动态精馏 温度代理 压力补偿 串级 扰动验证" --json
python knowledge/scripts/query_knowledge.py --query "中间罐 间歇精馏 库存" --vector --json
```

[OC02 知识块目录](../chemical_principles/knowledge_graph/source_records/OC02/) · [OC02 来源采纳记录](../source_adoptions/OC02.json)

## TH03：热力学性质、能量利用与相平衡

本批新增 25 个完整知识块，覆盖相区与状态方程、多根选择、参考态和残余性质、稳流能量衡算、节流温度效应、多级压缩、熵产与设备效率、动力/制冷循环、有效能，以及混合物的逸度/活度标准态、数据一致性、相平衡与闪蒸、气体溶解、液液/固液平衡和水合物。

按章节筛选并回读有用主题，合并重复解释，跳过无独立用途的公式展开、附录条目和例题数值；不是全文转写。公式或结论保留必要条件，具体物系参数仍需当前来源核验。原始资料不随包，公开来源编号、文件哈希与物理页锚；正文、关联节点和查询索引均随包可用，内容采纳不代表物性模型或工程计算已经验证。

可直接查询：

```text
python knowledge/scripts/query_knowledge.py --query "活度系数 标准态 Henry" --json
python knowledge/scripts/query_knowledge.py --query "节流 压降 温度" --limit 12 --json
python knowledge/scripts/query_knowledge.py --node-id TH03-B4 --full-text --json
```

[TH03 知识块目录](../chemical_principles/knowledge_graph/source_records/TH03/) · [TH03 来源采纳记录](../source_adoptions/TH03.json)
