<!-- generated: aspen_user_guide_v10 -->
# UG10-CH23 - 第23章 模拟模型的数据拟合

Source extract: `../../chapter_extracts/ch23_data_fit.md`

PDF pages: 341-358

Operation routes:
- `optimization-regression`: optimization, model/data fitting, and property-parameter regression
- `component-property`: component IDs, databanks, physical-property methods, property data, and pseudocomponents

## Use When

Triggers: `data fit`, `model fit`, `parameter fit`, `数据拟合`, `模型拟合`

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `第23章 模拟模型的数据拟合`.

## Chapter Topics

- PDF Page 341
- 第 23 章 模拟模型的数据拟合
- 量的测量数据而匹配被拟合的模型 也可同时做这个工作
- 本章介绍
- 并且给出了两个综合示例
- Data-Fit 数据拟合 应用的类型
- Data-Fit 数据拟合 应用分为两大类
- 下列功能
- 定义一个 Data-Fit 数据拟合 问题
- 将一个模拟模型与数据拟合涉及下面三个主要步骤
- 1. 建立基本工况 ASPEN PLUS 模型
- PDF Page 342
- 拟合 问题的初始估值
- 2. 建立一个或多个 Data-Fit 数据拟合 数据集
- 数据集类型  要拟合的数据
- POINT-DATA
- PROFILE-DATA l 一个间歇反应器的时间系列数据
- 定义 Data-Fit 数据拟合 回归工况
- 建立 Point-Data 点数据 数据集
- 向 Data Fit 数据拟合
- 标识流程变量
- 它数据集页面上的流程变量

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `UG10-CH23` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

- previous: `UG10-CH22`
- next: `UG10-CH24`
- operation-route: `optimization-regression`
- operation-route: `component-property`
