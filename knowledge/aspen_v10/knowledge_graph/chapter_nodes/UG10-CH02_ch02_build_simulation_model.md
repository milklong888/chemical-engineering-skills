<!-- generated: aspen_user_guide_v10 -->
# UG10-CH02 - 第2章 建立模拟模型

Source extract: `../../chapter_extracts/ch02_build_simulation_model.md`

PDF pages: 16-31

Operation routes:
- `case-io`: open, create, save, import, export, archive, and automate case files
- `component-property`: component IDs, databanks, physical-property methods, property data, and pseudocomponents
- `block-stream`: flowsheet drawing, block/stream objects, stream connection, and information transfer
- `equipment-card`: unit-operation model selection and equipment/block input context
- `run-export`: run sequence, control panel, results, reports, plots, and stream summaries

## Use When

Triggers: `new simulation`, `template`, `components`, `property method`, `stream input`, `run`, `新建模拟`, `模板`, `物流输入`

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `第2章 建立模拟模型`.

## Chapter Topics

- PDF Page 16
- 第2章   建立模拟模型
- 本章描述了如何使用ASPEN PLUS建立模拟模型 包括下列内容
- 使用 ASPEN PLUS进行工艺过程模拟
- PLUS能够帮助你设计更好的装置并增加现有装置的利润
- 分析你的结果
- ASPEN PLUS允许你做广泛的其它应用 你能够
- 建立新运行
- 下面介绍两种情况
- 启动 ASPEN PLUS并建立新的运行
- 启动ASPEN PLUS并建立一个新的运行
- 在相应的按钮上单击, 然后单击OK
- 模拟模板的更多信息见选择模板
- 5. 单击 OK
- PDF Page 17
- 息见第一章
- 在ASPEN PLUS中建立一个新的运行
- 1. 如果你想以后打开当前运行 则保存当前运行
- 2. 从File菜单中 单击New
- Cancel:
- 在新的运行开发之前 将给你一个保存当前运行的选项
- No 当前运行将在现有的窗口中保持激活 而一个新的运行将在第二个

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `UG10-CH02` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

- previous: `UG10-CH01`
- next: `UG10-CH03`
- operation-route: `case-io`
- operation-route: `component-property`
- operation-route: `block-stream`
- operation-route: `equipment-card`
- operation-route: `run-export`
