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

## EN04：换热网络与蒸汽动力系统

本批新增 17 个完整知识块：11 个夹点、换热网络及总厂集成主题，5 个能量分析工具与蒸汽系统建模主题，以及 1 个按温差要求分配自热回收蒸汽的案例机制。内容覆盖复合曲线和热级联、数据提取与安全侧、经济及公用工程目标、热机/热泵位置、塔器集成、网络设计/调优/改造、总厂源汇与蒸汽等级，以及模型接口、负荷曲线和多周期约束。

按目录和真实章节边界筛选，定向回读有用主题；不是全书逐页转写。八个案例分别检查新增机制，已覆盖的常规流程、重复经济判断、旧界面操作、例题数字和无独立用途的推导跳过。线上附录不在所供资料内，未访问、不算已处理。工具相关说明保留 V9 来源边界，不视为当前软件能力验证。

可直接查询：

```text
python knowledge/scripts/query_knowledge.py --query "热泵 夹点 热公用工程" --json
python knowledge/scripts/query_knowledge.py --query "蒸汽 多周期 可用性 约束" --vector --json
python knowledge/scripts/query_knowledge.py --node-id EN04-C1 --full-text --json
```

[EN04 知识块目录](../chemical_principles/knowledge_graph/source_records/EN04/) · [EN04 来源采纳记录](../source_adoptions/EN04.json)

本轮四批合计新增 69 块（14 + 13 + 25 + 17）。完整释义、关系与查询索引随包公开；原始 PDF、整页转写、私人路径与未审稿不公开。入库标准与贡献步骤见[知识贡献与读取准则](../CONTRIBUTING.md)。
