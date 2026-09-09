# 19 一览表精度厂家资料层

本节点把资料深度固定在“可填写设备一览表”层，不延伸到厂家曲线、询价数据表或制造图。

资料包：`../../设备一览表_型号级资料包_20260713`。

## 来源层

| 来源 | 设备族 | 可复用到一览表 | 不能越界 |
| --- | --- | --- | --- |
| Sulzer Structured Packings官方目录 | 塔填料 | 商品系列名、结构系列、公开概述参数 | 不证明本项目水力学通过 |
| 上海泽尔SV官方页 | 静态混合器 | 完整标记段语法和SV系列 | 不证明现有缺段字符串已定型 |
| Atlas Copco压缩机/膨胀机官方目录 | 压缩机、气体膨胀机 | 平台/系列、能力范围和一览表字段 | 不拼造完整订货型号 |
| Sulzer HST官方目录 | 鼓风机 | 公开型号系列和额定范围 | 不把最大范围当设计点 |
| Emerson Fisher产品指南 | 阀门 | 阀型、DN/Class、Cv、材料和系列入口 | 无Line List时不生成逐阀型号 |
| UBE/Evonik官方膜资料 | 膜组件 | 膜型、材料、模块尺寸/应用范围 | 不跨气体体系迁移型号或性能 |
| Siemens汽轮机目录 | 工业汽轮机 | 系列、功率/温压/转速范围 | 不用于CO2工艺气膨胀机 |

## 状态规则

- 公开厂家系列且字段匹配：`manufacturer_series_candidate`。
- 官方公开完整型号和逐型号参数：`manufacturer_exact_model_public`。
- 厂家平台/工程定制：`engineered_to_order_platform`。
- 同位号工况、材料或适用介质不闭合：仍为 `vendor_candidate`，型号栏允许留空。

## 当前项目直接纠错

- `MellapakPlus752Y` → `MellapakPlus 752.Y`。
- `MellapakPlus452Y` → `MellapakPlus 452.Y`。
- `MELLAPAK250Y` → `Mellapak 250.Y`。
- `MELLAPAK2X` → `Mellapak 2X`。
- `Mellapak125X` → `Mellapak 125.X`。
- `SV-*`字符串缺少官网完整标记段，不升级为正式型号。
- `PI-HF-CO2-2000×10`未找到厂家原型，只保留为历史候选。
