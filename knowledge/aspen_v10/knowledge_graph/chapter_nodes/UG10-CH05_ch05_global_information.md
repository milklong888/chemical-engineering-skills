<!-- generated: aspen_user_guide_v10 -->
# UG10-CH05 - 第5章 计算的全局信息

Source extract: `../../chapter_extracts/ch05_global_information.md`

PDF pages: 53-68

Operation routes:
- `case-io`: open, create, save, import, export, archive, and automate case files
- `run-export`: run sequence, control panel, results, reports, plots, and stream summaries

## Use When

Triggers: `setup`, `global`, `units`, `diagnostics`, `report options`, `全局信息`, `单位集`, `诊断`

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `第5章 计算的全局信息`.

## Chapter Topics

- PDF Page 53
- 第 5章 计算的全局信息
- 本章解释了如何规定和改变所有类型的全局信息 包括
- 关于全局信息
- 要规定全局信息
- 变输入 但建议你在开始一个新的运行之前使用它
- 在 Setup 窗体中输入全局规定 为了访问 Setup 窗体
- 1. 在 Data 菜单中单击 Setup
- 2. 下表显示了输入信息要用哪种表格
- 使用这种表格  来
- 规定 输入全局信息
- 模拟选项 规定计算 闪蒸收敛 系统选项 时间和误差限制
- 物流类 定义物流类和物流性质
- 子物流 定义子物流和属性
- 单位集 定义度量单位集
- 报告选项 规定报告选项
- 说 不必要在其它 Setup 页上改变缺省值
- 输入全局规定
- 行说明 下面的表格显示了你可以在每页中输入的信息
- 在规定表格的下述页上  输入这些信息
- 全局 运行类型 运行标题 运行说明 全局缺省值 单位 流率
- 基准 相平衡 计算选项 物流类

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `UG10-CH05` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

- previous: `UG10-CH04`
- next: `UG10-CH06`
- operation-route: `case-io`
- operation-route: `run-export`
