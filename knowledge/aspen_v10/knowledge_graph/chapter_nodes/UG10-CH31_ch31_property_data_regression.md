<!-- generated: aspen_user_guide_v10 -->
# UG10-CH31 - 第31章 物性数据回归

Source extract: `../../chapter_extracts/ch31_property_data_regression.md`

PDF pages: 444-464

Operation routes:
- `optimization-regression`: optimization, model/data fitting, and property-parameter regression
- `component-property`: component IDs, databanks, physical-property methods, property data, and pseudocomponents

## Use When

Triggers: `property regression`, `data regression`, `物性数据回归`

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `第31章 物性数据回归`.

## Chapter Topics

- PDF Page 444
- 第 31 章 物性数据回归
- 你可以输入任何实验物性数据 如
- 本章含有关于物性回归系统的如下信息
- 数据回归系统的设定
- 设定一数据回归系统有以下几个步骤
- 输入或估计任何附加的物性参数 参见第九章和第三十章
- 回归工况
- 下面的应用将由这些步骤来指导
- PDF Page 445
- 物性方法的选择
- 你必须选择使用某物性模型的物性方法 用它来确定你想要的参数
- 例如 为拟合 UNIQUAC二元参数 可选择下列物性方法之一
- 可用的
- 输入附加参数
- 数据回归 将用这些值作为初值
- 拟合纯组分数据
- 为拟合纯组分的与温度有关的物性数据 如蒸汽压 要进行如下操作
- 回归的参数
- 输入纯组分数据
- 作为温度的函数 例如 可以输入蒸汽压作为温度的函数
- 输入纯组分数据有以下几个步骤

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `UG10-CH31` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

- previous: `UG10-CH30`
- next: `UG10-CH32`
- operation-route: `optimization-regression`
- operation-route: `component-property`
