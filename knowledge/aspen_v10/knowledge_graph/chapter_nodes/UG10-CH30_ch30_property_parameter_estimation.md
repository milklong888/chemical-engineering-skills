<!-- generated: aspen_user_guide_v10 -->
# UG10-CH30 - 第30章 估计物性参数

Source extract: `../../chapter_extracts/ch30_property_parameter_estimation.md`

PDF pages: 426-443

Operation routes:
- `component-property`: component IDs, databanks, physical-property methods, property data, and pseudocomponents
- `optimization-regression`: optimization, model/data fitting, and property-parameter regression

## Use When

Triggers: `estimate property`, `PCES`, `group contribution`, `估计物性参数`

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `第30章 估计物性参数`.

## Chapter Topics

- PDF Page 426
- 第 30 章 估计物性参数
- PLUS 数据库中 则可以
- Regression(数据回归)中运行
- 计方式 则采用下列的一种方法
- 类型)
- 质估计)
- 行物性估计
- PDF Page 427
- 是要知道哪个参数是可用的
- 用运行
- 数 包括
- 下表列出了 ASPEN PLUS 可以估计的物性参数
- 纯组分常数 的物性名称及估计方法
- 说明  参数  方法  所需信息 *
- 分子量 MW FORMULA 结构
- 标准沸点
- TB JOBACK
- OGATA-TSUCHIDA
- GANI
- MANI
- TC PC 气相压力

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `UG10-CH30` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

- previous: `UG10-CH29`
- next: `UG10-CH31`
- operation-route: `component-property`
- operation-route: `optimization-regression`
