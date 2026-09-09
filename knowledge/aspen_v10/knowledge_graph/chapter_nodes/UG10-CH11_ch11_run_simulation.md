<!-- generated: aspen_user_guide_v10 -->
# UG10-CH11 - 第11章 运行模拟程序

Source extract: `../../chapter_extracts/ch11_run_simulation.md`

PDF pages: 178-187

Operation routes:
- `run-export`: run sequence, control panel, results, reports, plots, and stream summaries

## Use When

Triggers: `run`, `sequence`, `control panel`, `运行`, `计算顺序`, `控制面板`

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `第11章 运行模拟程序`.

## Chapter Topics

- PDF Page 178
- 本章介绍如何运行模拟程序 主要介绍下列内容
- 可以按下列方式运行模拟程序
- 运行方式  信息
- 模拟计算的运行 你可以一步一步地执行模
- 拟运算 可以在任意点停止运算 可以查看
- 任意中间结果 并且可以进行修改
- 不能控制模拟计算的运行 对于较长的模拟
- 计算 或者想同时运行几个模拟程序 工况
- 研究 时 采用批处理 Batch 方式运行模
- 拟程序非常有效
- Standalone ASPEN PLUS 只有文本
- 独立 方式
- 独立运行方式与批处理运行方式类似 只是
- 它在用户界面的外面独立运行
- 交互式运行模拟程序
- 你可以用下列方法交互式控制模拟程序的执行
- 修改输入规定
- PDF Page 179
- 控制面板 Control Panel 中包括下列内容
- 控制模拟计算的命令
- 面板 来控制模拟计算

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `UG10-CH11` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

- previous: `UG10-CH10`
- next: `UG10-CH12`
- operation-route: `run-export`
