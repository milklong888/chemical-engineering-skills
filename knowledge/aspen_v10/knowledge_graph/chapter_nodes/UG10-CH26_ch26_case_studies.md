<!-- generated: aspen_user_guide_v10 -->
# UG10-CH26 - 第26章 工况研究

Source extract: `../../chapter_extracts/ch26_case_studies.md`

PDF pages: 374-376

Operation routes:
- `sensitivity`: variable scans, convergence bracketing, and case studies
- `run-export`: run sequence, control panel, results, reports, plots, and stream summaries

## Use When

Triggers: `case study`, `scenario`, `工况研究`, `多工况`

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `第26章 工况研究`.

## Chapter Topics

- PDF Page 374
- 第 26 章 工况研究
- 本章包括
- 使用工况研究
- 同一流程的模拟 工况研究模块不影响基础工况的模拟或基础工况报告
- 章 关于批处理运行你的模拟
- 创建一个工况研究
- 本章关于表示工况研究变量的部分
- 章关于规定工况研究变量值的部分
- 项的部分
- 标识工况研究变量
- 改变模块输入 工艺进料物流和其它输入变量 结果变量不能被直接改变
- 标识你想要从一个工况到另一个工况改变的变量按以下步骤
- 量 见第十八章关于访问流程变量的内容
- 些变量
- 6. 重复步骤 2-5 直到你标识了所有的工况研究变量
- PDF Page 375
- 规定工况研究的变量值
- 规定工况研究变量的值采取以下步骤
- 页中标识的顺序输入多个变量值
- 5. 输入另一个工况 重复步骤 2-3 直到你定义了想运行的所有工况
- 重置初始值

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `UG10-CH26` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

- previous: `UG10-CH25`
- next: `UG10-CH27`
- operation-route: `sensitivity`
- operation-route: `run-export`
