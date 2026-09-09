<!-- generated: aspen_user_guide_v10 -->
# UG10-CH17 - 第17章 收敛

Source extract: `../../chapter_extracts/ch17_convergence.md`

PDF pages: 239-260

Operation routes:
- `run-export`: run sequence, control panel, results, reports, plots, and stream summaries
- `sensitivity`: variable scans, convergence bracketing, and case studies
- `design-spec`: feedback-control style target/vary operations

## Use When

Triggers: `convergence`, `tear`, `sequence`, `Broyden`, `Wegstein`, `收敛`, `断裂物流`, `迭代`

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `第17章 收敛`.

## Chapter Topics

- PDF Page 239
- 第 17 章 收敛
- 17-1
- 本章包含了下列关于收敛的内容
- 流程再循环和设计规定
- 块计算出来的输出流股被作为下一个模块的进料使用
- 和焓的循环流股 它可以是一个回路中的任意一股流股
- 股或设计规定控制的变量的估测如何在循环过程中更新
- 符 $ 开始 而由用户定义的收敛模块不应以字符 $ 开始
- 还会核查由用户规定的确保所有回路均被撕裂的次序
- 你可以作的收敛规定为
- 要知更详细的情况参见本
- 章的相关部分
- 收敛参数和 /或用于收敛模块的
- Conv Options 收敛选项
- 所需的用于系统生成的收敛模块
- 的一些或全部撕裂流股
- Tear 规定撕裂流股
- 用于一些或全部用户定义的收敛
- 模块的收敛顺序
- Conv Order 规定收敛顺序
- 用于流程的全部或一部分的次序 Sequence 规定计算次序

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `UG10-CH17` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

- previous: `UG10-CH16`
- next: `UG10-CH18`
- operation-route: `run-export`
- operation-route: `sensitivity`
- operation-route: `design-spec`
