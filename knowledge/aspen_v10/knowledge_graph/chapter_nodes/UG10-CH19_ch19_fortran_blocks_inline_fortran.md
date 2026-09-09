<!-- generated: aspen_user_guide_v10 -->
# UG10-CH19 - 第19章 FORTRAN块及内嵌FORTRAN

Source extract: `../../chapter_extracts/ch19_fortran_blocks_inline_fortran.md`

PDF pages: 284-300

Operation routes:
- `calculator`: flowsheet variables, information transfer, Balance blocks, and Fortran/Calculator logic
- `reaction-card`: reaction sets, stoichiometry, chemistry, kinetic/card boundaries, and user models
- `delivery-qa`: reports, PFD annotations, file packages, plots, external program exchange, and deliverable checks

## Use When

Triggers: `Fortran`, `inline Fortran`, `user model`, `FORTRAN块`, `内嵌FORTRAN`

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `第19章 FORTRAN块及内嵌FORTRAN`.

## Chapter Topics

- PDF Page 284
- 第 19 章 FO RTRAN 块及内嵌 FORTRAN
- 第19章 FORTRAN 块及内嵌 FORTRAN
- 在 ASPEN PLUS中使用 Fortran
- Fortran 块
- 多数错误 如果在某个 Fortran 页上的状态指示器是
- 请使用 Next(下一步)找出未完成的
- 请参见 ASPEN PLUS 用户模型
- 推荐的编译器 请参见 ASPEN PLUS 安装指南
- 关于 FORTRAN 模块
- 务 例如
- PDF Page 285
- 第 19 章 FORTRAN 块及内嵌 FORTRAN
- 确定某个 Fortran 模块的执行顺序
- 通过下列步骤来定义一个 Fortran 模块
- 1. 建立一个 Fortran 模块
- 2. 标识模块被采集的或被操纵的流程变量
- 3. 输入 Fortran 语句
- 4. 指定何时执行 Fortran 模块
- 建立一个 Fortran 模块
- Fortran
- 下列章节介绍如何填写必需的页面

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `UG10-CH19` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

- previous: `UG10-CH18`
- next: `UG10-CH20`
- operation-route: `calculator`
- operation-route: `reaction-card`
- operation-route: `delivery-qa`
