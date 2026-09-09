<!-- generated: aspen_user_guide_v10 -->
# UG10-CH29 - 第29章 分析物性

Source extract: `../../chapter_extracts/ch29_property_analysis.md`

PDF pages: 399-425

Operation routes:
- `component-property`: component IDs, databanks, physical-property methods, property data, and pseudocomponents
- `run-export`: run sequence, control panel, results, reports, plots, and stream summaries

## Use When

Triggers: `property analysis`, `phase envelope`, `binary analysis`, `物性分析`, `相图`

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `第29章 分析物性`.

## Chapter Topics

- PDF Page 399
- 第 29 章 分析物性
- 据这些数值作图 以更好地理解通过物性规定预测的物性
- 通过下列方法可进入 Property Analysis 物性分析
- 文件夹生成 Property Analysis 这种方法最灵活
- 主题包括
- 可以通过下列方法使用 Property Analysis 物性分析
- PDF Page 400
- 列表中规定 Property Analysis
- 用的物性分析
- 一个内置的图形可快速容易地查看常用信息
- 快速 更容易
- 可以在完成物性规定后的任何时候使用交互 Analysis 分析 命令
- 交互 Analysis 分析 命令可产生
- 组分 命令
- 纯组分
- 为缺省 其中包括
- 项 信息
- 窗口中任一 Property Method 性质分析
- 温度  缺省温度范围是 0 到 25 可以通过改变低限和高限温
- 度来输入一个新的温度范围 或者将温度范围改为温度
- 值列表并规定预测温度值

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `UG10-CH29` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

- previous: `UG10-CH28`
- next: `UG10-CH30`
- operation-route: `component-property`
- operation-route: `run-export`
