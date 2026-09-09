<!-- generated: aspen_user_guide_v10 -->
# UG10-CH12 - 第12章 检查结果和生成报告

Source extract: `../../chapter_extracts/ch12_results_reports.md`

PDF pages: 188-194

Operation routes:
- `run-export`: run sequence, control panel, results, reports, plots, and stream summaries
- `delivery-qa`: reports, PFD annotations, file packages, plots, external program exchange, and deliverable checks

## Use When

Triggers: `results`, `report`, `history`, `结果`, `报告`, `流股表`

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `第12章 检查结果和生成报告`.

## Chapter Topics

- PDF Page 188
- 本章叙述进行下列工作的方法
- 交互式查看模拟结果
- 只要窗口底部状态栏中状态消息为下表中的内容 你即可查看模拟结果
- 消息   意义
- 控制面板 Control Panel 或历史 History 中可
- 查看消息
- 了输入 因此该结果可能与当前的输入不匹配
- 对象 状态指示器的完整列表 参见第一章
- 查看当前的模拟结果
- 1. 在 Run 菜单上 单击 Settings 命令
- 3. 在 Run 菜单上 单击 Check Results 命令
- 表和对象
- PDF Page 189
- 检查运行的完成状态
- 明了计算是否为正常完成
- 要显示 Results Summary 页面 可用下列某一方法
- 从 选择
- Run 菜单  Check Results 命令
- 息 诊断消息 警告消息和错误消息
- 在控制面板中检查完成状态
- Simulation Run工具栏或者

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `UG10-CH12` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

- previous: `UG10-CH11`
- next: `UG10-CH13`
- operation-route: `run-export`
- operation-route: `delivery-qa`
