<!-- generated: aspen_user_guide_v10 -->
# UG10-CH21 - 第21章 设计规定：反馈控制

Source extract: `../../chapter_extracts/ch21_design_specs_feedback_control.md`

PDF pages: 309-321

Operation routes:
- `design-spec`: feedback-control style target/vary operations

## Use When

Triggers: `Design Spec`, `feedback control`, `vary`, `设计规定`, `反馈控制`

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `第21章 设计规定：反馈控制`.

## Chapter Topics

- PDF Page 309
- 第 21 章 设计规定 反馈控制
- 第21章 设计规定 反馈控制
- 在你的模拟中 可使用设计规定作为反馈控制器 本章介绍
- 关于设计规定
- 稳态影响
- 一个模块输入变量或过程进料变量以便满足设计规定 该变量称为被操纵变量
- 率 而该循环物流是其一个出口物流 设计规定只能调整一个输入变量的值
- 完整描述 参见第十七章
- 定的大流程特别重要
- 足目标函数关系 因此 实际上必须满足的方程是
- |规定值-计算值|<允差
- 块的 Results 结果 页面 可以查看收敛模块的摘要和收敛历史
- 定义一个设计规定
- 定义一个设计规定有下列五个步骤
- PDF Page 310
- 本章后面几节介绍上述各步骤
- 建立一个设计规定
- 管理器 中 单击 N ew 新建
- 然后单击 OK
- 下面几节如何完成所需的页面
- 标识被采集流程变量

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `UG10-CH21` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

- previous: `UG10-CH20`
- next: `UG10-CH22`
- operation-route: `design-spec`
