<!-- generated: aspen_user_guide_v10 -->
# UG10-CH38 - 第38章 使用ASPEN PLUS的ActiveX自动控制服务器

Source extract: `../../chapter_extracts/ch38_activex_automation.md`

PDF pages: 545-571

Operation routes:
- `case-io`: open, create, save, import, export, archive, and automate case files
- `block-stream`: flowsheet drawing, block/stream objects, stream connection, and information transfer
- `equipment-card`: unit-operation model selection and equipment/block input context
- `run-export`: run sequence, control panel, results, reports, plots, and stream summaries

## Use When

Triggers: `ActiveX`, `automation`, `COM`, `自动控制服务器`, `脚本`

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `第38章 使用ASPEN PLUS的ActiveX自动控制服务器`.

## Chapter Topics

- PDF Page 545
- 第38章 使用 ASPEN PLUS的ActiveX自动控
- 制服务器
- 关于自动控制服务器
- 列出对象
- 使用自动控制接口 你能够
- 序或数据库等
- 界面的用户
- 使用自动控制服务器
- 为了使用 ASPEN PLUS 自动控制服务器 你必须
- PDF Page 546
- 该服务器是一个来自过程的服务器 执行程序是 apwn.exe.
- 型库框
- 用户界面的系统目录 选中 happ.tlb 文件.
- 错误处理
- 相应显示一个异常 但大多数并不是严重或致命的错误
- 时遇到严重的错误 通常会建立一个错误处理子程序 以整理应用并完整退出
- 浏览 ASPEN PLUS 对象的属性和方法
- 目前菜单项的分页模块必须是活动的
- 是在 Excel VBA的对象浏览器下
- ASPEN PLUS 列出的对象
- 通过 ASPEN PLUS 列出的对象如下

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `UG10-CH38` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

- previous: `UG10-CH37`
- operation-route: `case-io`
- operation-route: `block-stream`
- operation-route: `equipment-card`
- operation-route: `run-export`
