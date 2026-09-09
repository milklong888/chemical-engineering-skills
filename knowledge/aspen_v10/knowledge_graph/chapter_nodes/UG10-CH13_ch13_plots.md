<!-- generated: aspen_user_guide_v10 -->
# UG10-CH13 - 第13章 操作曲线图

Source extract: `../../chapter_extracts/ch13_plots.md`

PDF pages: 195-207

Operation routes:
- `run-export`: run sequence, control panel, results, reports, plots, and stream summaries
- `delivery-qa`: reports, PFD annotations, file packages, plots, external program exchange, and deliverable checks

## Use When

Triggers: `plot`, `curve`, `graph`, `操作曲线`, `绘图`, `曲线图`

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `第13章 操作曲线图`.

## Chapter Topics

- PDF Page 195
- 图的方法 包括
- 关于曲线图
- 列信息
- Pres-Relief 卸压 的结果
- 与生成曲线图有关的步骤有下列三个
- 2. 用下列方法生成曲线图
- 3. 定制曲线图外观
- 第一步 显示数据
- 要显示数据 可按下列步骤进行
- 1. 在 Data 菜单上 单击 Data Browser.
- 2. 在左窗格中 单击含有绘制曲线图所需数据的表
- 3. 在该表上 单击页显示出数据
- 该页即可以是输入页 也可以是结果页 但它更常用于绘制结果曲线
- 4. 要绘制结果曲线 要保证模拟运行有可用的结果
- 结果时的状态消息的详细信息 参见第十二章
- 第二步 生成曲线图
- 你可以用下列方法中的任一个生成曲线图
- PDF Page 196
- 使用 Plot Wizard
- 在你显示出数据之后 进行下列步骤
- 1. 在 Plot 菜单上 单击 Plot Wizard

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `UG10-CH13` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

- previous: `UG10-CH12`
- next: `UG10-CH14`
- operation-route: `run-export`
- operation-route: `delivery-qa`
