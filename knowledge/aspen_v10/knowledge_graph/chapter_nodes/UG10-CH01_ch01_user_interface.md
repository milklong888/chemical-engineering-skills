<!-- generated: aspen_user_guide_v10 -->
# UG10-CH01 - 第1章 用户界面

Source extract: `../../chapter_extracts/ch01_user_interface.md`

PDF pages: 3-15

Operation routes:
- `case-io`: open, create, save, import, export, archive, and automate case files
- `block-stream`: flowsheet drawing, block/stream objects, stream connection, and information transfer
- `run-export`: run sequence, control panel, results, reports, plots, and stream summaries

## Use When

Triggers: `UI`, `Data Browser`, `Next`, `Control Panel`, `主窗口`, `数据浏览器`, `快捷键`

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `第1章 用户界面`.

## Chapter Topics

- PDF Page 3
- 第1章  用户界面
- ASPENPLUS建立和运行工艺模型入门中的练习题
- 本章解释了下列内容:
- 有关按钮 菜单和其它屏幕选项获得帮助的更多信息见第三章
- 启动 ASPEN PLUS
- 1. 点击Start 然后指向Programs
- 拟 或者打开一个已经存在的模拟
- 有关建立一个新运行的更多信息见第二章
- 择More File的文件 然后点击OK
- 果你选择More File Open对话框出现
- 息见十六章
- Open
- 连接到 ASPEN PLUS主机上
- 信息询问你的ASPEN PLUS系统管理员
- 引擎)对话框出现
- 2. 指定ASPEN PLUS 模拟引擎将运行的位置
- PDF Page 4
- 服务器类型  ASPEN PLUS引擎运行位置
- 本地 PC  你的PC 使用网络管理器
- Unix 主机 一个Unix服务器
- OpenVMS主机 一个 OpenVMS 服务器

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `UG10-CH01` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

- previous: `UG10-CH00`
- next: `UG10-CH02`
- operation-route: `case-io`
- operation-route: `block-stream`
- operation-route: `run-export`
