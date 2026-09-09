# 父任务集成说明

## 可直接提升的文件

下列文件可作为“设备设计图谱与脚本”的类型选择子包直接挂载：

- `type_catalog.csv`
- `candidate_capabilities.csv`
- `condition_registry.csv`
- `service_label_derivation.csv`
- `hard_exclusions.csv`
- `compatibility_matrix.csv`
- `selection_rules.csv`
- `tie_default_priority.csv`
- `warning_templates.csv`
- `select_terminal_type.py`
- `input_schema.json`

证据和审计侧同时挂载：`source_records.csv`、`source_relations.csv`、`logical_table_grouping_manifest.csv`、`package_metadata.json`、`hash_manifest.csv`。

## 集成过滤器

1. `type_catalog.csv` 只加载 `terminal_selectable=true` 的行作为最终候选；`facing_component` 行只供术语/图谱关系查询。
2. 标准事实只提升 `source_records.csv` 中 `terminal_class=DIRECT_REUSE_EVIDENCE` 且 `qa_status=PASS_PAGE_VISUAL_REVIEW` 的记录。
3. `annotation_class=ENGINEERING_NORMALIZATION` 或 `DETERMINISTIC_POLICY` 的记录必须保留原标签，不能改写成标准原文或项目默认。
4. 2012年5月勘误页 `E_P531/E_P532` 优先于基准页的旧代码/旧等级；`PMF/PMS/PFT/LMN/NPY` 不得进入当前代码表。
5. LLM 接入只能读取程序结果、原文注释和缺口，补充结构化 `property_evidence` 候选；最终必须回到确定性引擎重算，LLM 不能改写硬排除、候选边界或 `terminal_type`。

## 上游接口要求

上游 Aspen/手动导入只传原始字段：温度及单位、压力及单位、汽/固相分率、组分 ID 与组成、模块 ID/类型、设计额定等级和口径。腐蚀性、毒性、可燃性、清洁度、密封等级、真空、循环和热冲击等不是用户直接标签；须由有来源物性/相容性/项目要求图谱生成 `property_evidence`。每条事实至少有 `fact/value/source_id`，适用温度区间可选。缺失或来源为空时引擎保持 `UNKNOWN` 并报警。

## 输出契约

每次调用必须满足：

- `terminal_count == 1`
- `terminal_type.candidate_id` 非空且属于当前目录的注册候选
- `status` 为 `CONDITION_SELECTED`、`CONDITION_SELECTED_PROVISIONAL` 或 `DEFAULTED_PROVISIONAL`
- 保留 `normalized_service_labels`、`service_fact_evidence`、`hard_excluded_candidates`、`decision_chain`、`minimum_missing_fields`、`warnings` 和 `source_refs`

## 已知阻断/边界

- 本包只闭合类型—适用性—选择关键链，不宣称闭合原包中 560 个待单元格 QA 的尺寸/材料表。
- 材料 p-T 曲线、具体填充材料温限、腐蚀相容性、泄漏等级、防火、卫生和零逸散认证必须接外部有来源图谱或项目/供应商证据。
- 金属环垫选择仍需环号、槽尺寸和硬度匹配；当前仅能唯一推荐椭圆/八角终端类型并报警复核。
- 超出标准表列压力、口径或温度时，引擎为避免中停仍返回注册泛用类型，但标 `PROVISIONAL` 和 `W_SCOPE_MISMATCH`；不得据此宣称标准符合性。
- `audit_page_renders` 仅为本次人工审查证据，不进入运行清单，不得被运行时读取。

## 验收命令

`python validate_package.py --json`

验证器只读、双次重放、禁止 PDF/图片/source-layer 读取，并检查至少 36 个典型/边界/冲突/缺失用例恰好一个终端类型。

