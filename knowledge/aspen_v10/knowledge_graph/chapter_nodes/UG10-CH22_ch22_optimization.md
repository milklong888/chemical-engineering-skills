<!-- generated: aspen_user_guide_v10 -->
# UG10-CH22 - 第22章 优化

Source extract: `../../chapter_extracts/ch22_optimization.md`

PDF pages: 322-340

Operation routes:
- `optimization-regression`: optimization, model/data fitting, and property-parameter regression

## Use When

Triggers: `Optimization`, `objective`, `constraint`, `优化`, `目标函数`, `约束`

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `第22章 优化`.

## Chapter Topics

- PDF Page 322
- 第 22 章 优化
- 本章介绍下列内容
- 关于优化
- 户指定的目标函数最大化或最小化
- 函数 你必须指定约束的误差 撕裂流和优化问题可以同时收敛或单独收敛
- 优化问题的收敛
- 束的优化问题尤为重要
- 推荐的做优化过程
- 要 我们推荐的建立一个优化问题的过程是
- 1. 从一个模拟开始 而不是从一个优化开始 使用该方法有下列原因
- PDF Page 323
- 2. 在优化之前做灵敏度分析 以便找出合适的决策变量和它们的范围
- 3. 用灵敏度分析来估算问题的解以便确定最优值是宽还是窄
- 定义一个优化问题
- 按下列步骤定义优化问题
- 1. 创建一个优化问题
- 2. 标识目标函数中所用的被采集变量
- 上下限
- 5. 输入可选的 Fortran 语句
- 6. 定义优化问题的约束条件
- 建立一个优化问题

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `UG10-CH22` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

- previous: `UG10-CH21`
- next: `UG10-CH23`
- operation-route: `optimization-regression`
