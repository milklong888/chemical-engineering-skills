<!-- generated: aspen_user_guide_v10 -->
# UG10-CH15 - 第15章 管理文件

Source extract: `../../chapter_extracts/ch15_file_management.md`

PDF pages: 218-224

Operation routes:
- `case-io`: open, create, save, import, export, archive, and automate case files
- `delivery-qa`: reports, PFD annotations, file packages, plots, external program exchange, and deliverable checks

## Use When

Triggers: `file`, `backup`, `archive`, `APW`, `BKP`, `文件`, `备份`, `归档`

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `第15章 管理文件`.

## Chapter Topics

- PDF Page 218
- 第 15 章 管理文件
- ASPEN PLUS 的文件格式
- ASPEN PLUS中使用如下几种主要的文件类型
- 文件类型  扩展名  格式 * 描述
- 文档 *.apw 二进制 快速重启动包含模拟输入
- 结果和中间收敛信息的文
- 备份 *.bkp ASCII 存档包含模拟输入和结果
- 的文件
- 模板 *.apt ASCII 包含缺省输入的模板
- 输入 *.inp 文本 模拟程序输入
- 运行信息 *.cpn 文本 控制面板中显示的计算历
- 史信息
- 历史信息 *.his 文本 详细的计算历史和诊断信
- 汇总 *.sum ASCII 模拟结果
- 问题定义 *.appdf 二进制 二进制文件 包含模拟计算
- 中的数组和中间的收敛信
- 报告 *.rep 文本 模拟报告
- 上使用
- 文档文件  (*.apw)
- ASPEN PLUS使用先前的结果重新启动计算
- 文档文件可在ASPEN PLUS 用户界面中打开和保存

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `UG10-CH15` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

- previous: `UG10-CH14`
- next: `UG10-CH16`
- operation-route: `case-io`
- operation-route: `delivery-qa`
