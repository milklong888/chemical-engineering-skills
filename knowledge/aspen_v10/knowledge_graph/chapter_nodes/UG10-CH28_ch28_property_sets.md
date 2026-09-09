<!-- generated: aspen_user_guide_v10 -->
# UG10-CH28 - 第28章 物性集

Source extract: `../../chapter_extracts/ch28_property_sets.md`

PDF pages: 394-398

Operation routes:
- `component-property`: component IDs, databanks, physical-property methods, property data, and pseudocomponents
- `run-export`: run sequence, control panel, results, reports, plots, and stream summaries

## Use When

Triggers: `property set`, `stream property`, `物性集`, `结果变量`

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `第28章 物性集`.

## Chapter Topics

- PDF Page 394
- 第 28 章 物性集
- 本章包括
- 关于物性集
- 物性集是热力学 传递性质和其它物性的集合 你可以使用它在
- 的内容
- 定义一个物性集
- 定义一个物性集采取如下步骤
- 1. 从 Data 菜单 单击 Properties
- 集 ID 或接受一个缺省的 ID 并且单击 OK
- 中选择名称 并且单击 Edit
- 将出现一个命令符
- 对话框中的关于寻找对话框部分
- 6. 使用 Units 区域来选择一个或多个物性的单位
- PDF Page 395
- 计算物性
- 使用寻找对话框
- 单击 OK 返回到 Prop-Sets 表
- 使用 Search 查找物性的示例
- 规定相态限定
- PDF Page 396
- 宜的其它选项 液相 气相 第一液相 第二液相或固相

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `UG10-CH28` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

- previous: `UG10-CH27`
- next: `UG10-CH29`
- operation-route: `component-property`
- operation-route: `run-export`
