<!-- generated: aspen_user_guide_v10 -->
# UG10-CH20 - 第20章 灵敏度分析

Source extract: `../../chapter_extracts/ch20_sensitivity_analysis.md`

PDF pages: 301-308

Operation routes:
- `sensitivity`: variable scans, convergence bracketing, and case studies

## Use When

Triggers: `Sensitivity`, `vary`, `tabulate`, `灵敏度`, `变量扫描`

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `第20章 灵敏度分析`.

## Chapter Topics

- PDF Page 301
- 第 20 章 灵敏度分析
- 关于灵敏度分析
- 计算出的参数
- 立于灵敏度研究而运行
- 度分析模块
- 上输入一个表达式来转换变量 被访问的矢量型变量总是按 SI 单位
- 按下列步骤定义一个灵敏度分析块
- PDF Page 302
- 建立一个灵敏度分析模 块
- Sensitivity 灵敏度分析
- 然后 单击 OK
- 标识被采集流程变量
- 的流程变量
- 在 Define 定义 页面上
- 一个变量并单击 Edit 编辑 按扭
- 2. 在 Variable Name 变量名 字段中 输入变量名
- 击鼠标右键 在弹出菜单上单击 Rename 重命名 变量名必须是
- 3. 在 Category 类别 框中 用选项按扭选择变量类别
- PLUS 还显示为完成变量定义所需的其它字段
- 5. 单击 Close 关闭 返回 Define 定义 页面
- 关于访问变量的更详细信息 参见第十八章

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `UG10-CH20` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

- previous: `UG10-CH19`
- next: `UG10-CH21`
- operation-route: `sensitivity`
