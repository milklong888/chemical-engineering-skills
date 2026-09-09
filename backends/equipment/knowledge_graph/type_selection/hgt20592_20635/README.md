# HG/T 20592~20635 类型适用性与唯一选型包

本包把该标准合订本中的“多类型对象”拆成四类可执行选择：法兰型式、密封面配对、垫片型式和紧固件组件。运行时不读取 PDF、OCR、页面图片，也不调用大语言模型。

## 运行链

1. 输入 Aspen 流股/模块原始字段，或手动模式中的同类原始字段。
2. 程序完成压力和温度单位换算、相态判断。
3. 腐蚀性、毒性、可燃性、氧化性等标签只接受父级 `connection_component_selection.py` 已完成资产哈希、记录哈希、组成/相态/温压/压力基准和作用域绑定的图谱事实；缺证据就保持 `UNKNOWN` 并报警，绝不按组分名称猜测。
4. 候选侧从本 PDF 的类型、范围、结构和限制生成能力标签。
5. 依次执行：硬排除 → 必需兼容 → 适用性评分 → 泛用性优先级 → 候选 ID 字典序，保证恰好一个终端类型。
6. 条件不足时返回最泛用注册默认，同时状态为 `DEFAULTED_PROVISIONAL`，列出最小缺失字段和风险警告。

## 内部入口边界

本目录的 `select_terminal_type.py` 是父级验签包装器的内部机械选择核，不是 Agent 或用户直接提交物性事实的公开入口。其公开 `select`/CLI 路径会拒绝 `property_evidence`，也不接受直接 `phase` 标签；只有父级包装器在哈希锁定图谱行并冻结程序派生相态后调用私有 `_select_verified`。公开 Agent 应调用 `scripts/connection_component_selection.py` 或设备设计 Agent 协议。

## 快速使用（机械字段演示）

输入示例：

```json
{
  "object_family": "gasket_type",
  "system_series": "CLASS",
  "class_rating": 600,
  "dn_mm": 100,
  "temperature_value": 260,
  "temperature_unit": "C",
  "vapor_fraction": 1.0,
  "components": [
    {"component_id": "ASPEN_COMPONENT_ID", "mole_fraction": 1.0}
  ]
}
```

执行：

```powershell
python select_terminal_type.py input.json --pretty
python validate_package.py --json
```

输出中的 `terminal_type` 永远只有一个；`normalized_service_labels`、`decision_chain`、`hard_excluded_candidates`、`minimum_missing_fields` 和 `warnings` 可直接给 GUI、Agent 或报告模板读取。

## 数据文件

- `type_catalog.csv`：所有当前类型和子型；旧代码只保留在原文证据层。
- `candidate_capabilities.csv`：候选能力/限制标签。
- `condition_registry.csv`：原始输入与派生输出字段登记。
- `service_label_derivation.csv`：Aspen/手动原始字段到工况标签的确定性推导。
- `hard_exclusions.csv`：先行硬排除。
- `compatibility_matrix.csv`：密封面、环垫、孔板、夹套等必需兼容。
- `selection_rules.csv`、`tie_default_priority.csv`：适用性和唯一收敛策略。
- `source_records.csv`、`source_relations.csv`：本后台投影只保留页码、bbox、原文本/记录哈希和关系，不包含逐页原文；见 `SOURCE_PROJECTION.json` 的独立身份。
- `logical_table_grouping_manifest.csv`：跨页表闭合证明。
- `warning_templates.csv`：稳定机器码和人话报警。
- `test_cases.json`：典型、边界、冲突、缺失和越界测试。

## 证据分层

- `SOURCE_RAW_TEXT`：原文逐页证据。
- 以上原始来源分类是原包登记的QA，不表示本投影携带原文；本包来源记录为 `SOURCE_LOCATOR_HASH_ONLY_NOT_ORIGINAL_PARAGRAPH`。
- `SOURCE_NORMALIZATION`：只做同义字段和条件结构化。
- `DETERMINISTIC_DERIVATION`：单位、相态或逻辑必然推导。
- `ENGINEERING_NORMALIZATION`：不外推数值的工程标签和排序说明。
- `DETERMINISTIC_POLICY`：条件不足时的唯一收敛策略，不得冒充标准原文默认。

## 边界

本包不宣称替代材料 p-T 曲线、泄漏等级验证、防火/卫生认证、供应商特殊工况确认、环号与槽尺寸核对，也不包含该合订本 560 个待单元格复核表的全量尺寸数字化。超范围仍会给出一个类型用于不中停，但会明确标为暂定，不能据此直接生成标准尺寸或合格声明。
