# Parameter Source Nodes

## 来源类型优先级

1. 当前项目源文档明确数值和单位。
2. 同一设备同一版本 Aspen/EDR/SW6/Column Internals导出。
3. 当前项目引用的文献/厂家/规范，且单位基准完整。
4. 文档人工默认值或工程经验值，必须保留来源说明。
5. 历史案例或讲义只能迁移路径和字段含义，不迁移数值。

## 来源节点

| 来源节点 | 示例 | 用途 | 风险 |
| --- | --- | --- | --- |
| source_aspen_stream | 体积流量、质量流量、T/P、物性 | 接管、衡算、传热、压降 | 必须同设备同工况 |
| source_doc_table | DOCX表格值 | 复算对照 | 可能有标签矛盾，需同案互证 |
| source_literature | HETP、动力学、污垢热阻 | 方法/参数 | 需单位、基准、页码 |
| source_standard | GB/NB/设计规范 | 壁厚、标准管、设计边界 | 需确认版本和适用范围 |
| source_manual_default | 目标流速、停留时间、空间高度 | 初步设计 | 必须人工确认 |
| source_software_export | EDR/SW6/Column Internals | 正式工程证据 | 截图/导出要同模型同版本 |
| source_vendor | 泵/压缩机/膜/填料曲线 | 目录设备升级 | 需曲线点和型号对应 |

## 标准来源细分

新增标准目录已整理到 `standards_graph/`。使用 `source_standard` 时必须再细分：

| 细分标签 | 含义 | 例子 |
| --- | --- | --- |
| direct_reuse | 同版本、同输入、同单位，可查表或公式直接对照 | 标准管 OD/s 表页、封头型式尺寸 |
| method_only | 只迁移方法、流程、字段含义 | 容器手册、换热器教材、反应器教材 |
| software_boundary | 标准只给方法，正式值需软件导出 | 塔径/液泛/压降、EDR 面积/U/Re、SW6 强度 |
| vendor_boundary | 型号或性能需厂家样本 | 结构填料、泵、压缩机、膜 |
| forbidden_transfer | 禁止迁移的数值 | 教材示例、毕业设计案例、他设备参数 |

先读 `standards_graph/standard_parameter_crosswalk.md`，再决定是否能把标准源升为项目参数来源。项目专用 fastmap 为可选本地资料，未随包提供。

## EDR 来源细分

| 来源 | 可支持内容 | 不能单独支持 |
| --- | --- | --- |
| Aspen 同工况流股/热曲线 | 热负荷、进出口 T/P/相态、组成和物性输入 | EDR 已执行或结构已通过 |
| 同设备 `.EDR` + `TascMsg` | EDR 输入完整性、运行消息、结构和结果状态 | 最终 BKP 已绑定并交付 |
| Aspen EDR 在线报告 | Duty、required/actual area、margin、U、压降、速度/RhoV2、振动和运行模式 | SW6 强度、厂家制造保证 |
| 最终 BKP 重开/运行审计 | EDR 绑定存活、Required Input、Run Status、流程/产品一致性 | 负面积裕量或物性范围问题已自动消失 |
| 材料/厂家/标准证据 | 材料适用性、腐蚀和制造边界 | 扩展 Aspen/EDR 物性曲线温度范围 |

---
离线迁移说明：本文件保留原图谱的方法与边界正文；同案数值、私有审计及未随包的原件不作公共输入。来源及字段级剔除记录见 `RESTORATION_PROVENANCE.json`。本节点不升级原计算或证据状态。
