<!-- generated: aspen_user_guide_v10 -->
# UG10-CH08 - 第8章 物性参数和数据

Source extract: `../../chapter_extracts/ch08_property_parameters_data.md`

PDF pages: 103-129

Operation routes:
- `component-property`: component IDs, databanks, physical-property methods, property data, and pseudocomponents
- `optimization-regression`: optimization, model/data fitting, and property-parameter regression

## Use When

Triggers: `binary parameter`, `databank`, `property data`, `parameter`, `二元参数`, `物性参数`

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `第8章 物性参数和数据`.

## Chapter Topics

- PDF Page 103
- 入数据库中查不到的参数和数据
- 标题包括
- 关于参数和数据
- 为了理解这章和以后章节 把术语 参数 和 数据 区别开很重要
- 术语  定义  举例
- 参数 它是在许多物性模型或
- 方程中使用的常数
- ASPEN PLUS用它来预测
- 这些参数可以是标量常数 例如 摩尔重量
- MW 临界温度 TC 或者它们可以是
- 温度相关的性质关联式参数 例如 扩展
- Antoine蒸汽压方程的系数 PLXANT
- 数据 用于估计或回归参数的
- 原始实验性质数据
- 使用蒸汽压相对温度的数据估计或回归扩展
- 的Antoine参数 PLXANT
- 确定模拟要求的物性数据
- 参数 这些计算是
- 型 中的 物性方法表
- PDF Page 104
- 质量和能量平衡模拟要求的参数

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `UG10-CH08` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

- previous: `UG10-CH07`
- next: `UG10-CH09`
- operation-route: `component-property`
- operation-route: `optimization-regression`
