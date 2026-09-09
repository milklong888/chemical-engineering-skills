# 设备选型一览表权威知识图谱 v3

本图谱把当前项目工况、现行标准、软件计算和厂家性能证据分层，用于生成真实、可追溯的设备选型一览表。它不允许把参考项目介质、尺寸、材料、型号或管号迁移到本项目。

## 必读顺序

1. `00_ERROR_MEMORY.md`：先执行已核验纠错；只在需要近期候选知识时读取 `NEW_KNOWLEDGE.md`。
2. `00-authority-registry.md`：标准身份、版本、原文和状态。
3. `05-evidence-reuse-boundaries.md`：`direct_reuse` / `method_only` / `software_boundary` / `vendor_boundary` / `forbidden_transfer`。
4. `10-equipment-family-router.md`：设备族路由。
5. `12-template-coverage-router.md`：Excel 8 个工作表、Word 14 张表和 5 类管道扩展的对应。
6. `13-overview-table-field-schema.md`：每张表的必填参数和证据列。
7. `15-standard-designation-rules.md`：标准标记和查表边界。
8. `16-dynamic-vendor-rules.md`：泵、压缩机、透平、膜、混合器的厂家证据门。
9. `17-piping-selection-router.md`：管道、管件、法兰、垫片和阀门。
10. `18-model-size-standard-router.md`：哪些标准真的给型号/尺寸，哪些只给设计边界或缺正文。
11. `19-overview-table-source-precision.md`：一览表精度的厂家资料层及当前型号纠错。
12. `20-model-determination-card.md`：逐位号型号确定卡。
13. `21-line-determination-card.md`：逐管线确定卡。
14. `30-overview-table-interface.md`和 `31-piping-overview-interface.md`：输出字段。
15. `40-legacy-model-quarantine.md`和 `90-unknowns-router.md`：旧型号隔离与证据不足停机。

## 核心裁决

- “有国标”不等于“国标直接给出可采购商品型号”。
- 塔、反应器、分离器、储罐和多数换热器是工程定制设备，以型式、结构、尺寸和计算状态为主，不强造商品型号。
- 泵、压缩机、透平、膜组件、静态混合器和阀门的最终型号通常依赖同工况厂家曲线/数据表。
- 管材产品标准不能单独证明 DN、壁厚、管道等级、应力或阀门选型已通过。
- 泵保持 2026-07-12 项目冻结：GB/T 5662-2013 正文已入包，GB/T 3215-2025 因采标版权无官方全文；两者都不自动替换现有泵型号。

## 数据产品

- 机器图：`equipment_selection_graph_v2.json`（内部版本已升级为 v3，文件名保留以兼容已有索引）。
- 官方标准包：`../../设备选型全类别标准包_20260712`。
- 结构校验：`../validation/graph_validation_report.md`。
- 完整性校验：`../validation/complete_coverage_validation_report.md`。
