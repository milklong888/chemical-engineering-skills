<!-- generated: aspen_user_guide_v10 -->
# UG10-CH18 - 第18章 访问流程变量

Source extract: `../../chapter_extracts/ch18_access_flowsheet_variables.md`

PDF pages: 261-283

Operation routes:
- `calculator`: flowsheet variables, information transfer, Balance blocks, and Fortran/Calculator logic
- `sensitivity`: variable scans, convergence bracketing, and case studies
- `design-spec`: feedback-control style target/vary operations
- `optimization-regression`: optimization, model/data fitting, and property-parameter regression

## Use When

Triggers: `flowsheet variable`, `variable explorer`, `access variables`, `流程变量`, `变量访问`

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `第18章 访问流程变量`.

## Chapter Topics

- PDF Page 261
- 第 18 章 访问流程变量
- 当使用下列功能时 你得访问或操作流程变量
- 本章描述了
- 访问流程变量
- 和灵敏度模块
- 化改变的变量没有一个相关的名称
- 在一个模拟中有两种变量
- 变量类型   信息
- 用户输入的变量 用户可以直接操作任何用户输入的变量 这些变量可以或者
- 被读或者被写
- 由 ASPEN PLUS
- 计算的变量
- 这些变量不应被重写或者被直接改变 因为这会导致不一致
- 的结果 这些变量仅应该被读
- 访问的流程变量类型部分
- 表底部的提示
- 量是对模块的压力规定 如果输入了压降 那么它的值将是负的
- 被访问的流程变量的类型
- PDF Page 262
- 访问变量(既包括定义的也包括改变的)的单位在一个相同的单位集中
- 你可以访问这些变量类型的流程变量

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `UG10-CH18` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

- previous: `UG10-CH17`
- next: `UG10-CH19`
- operation-route: `calculator`
- operation-route: `sensitivity`
- operation-route: `design-spec`
- operation-route: `optimization-regression`
