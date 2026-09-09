<!-- generated: aspen_user_guide_v10 -->
# UG10-CH32 - 第32章 石油分析和虚拟组分

Source extract: `../../chapter_extracts/ch32_petroleum_pseudocomponents.md`

PDF pages: 465-479

Operation routes:
- `component-property`: component IDs, databanks, physical-property methods, property data, and pseudocomponents
- `equipment-card`: unit-operation model selection and equipment/block input context

## Use When

Triggers: `petroleum`, `assay`, `pseudocomponent`, `石油分析`, `虚拟组分`

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `第32章 石油分析和虚拟组分`.

## Chapter Topics

- PDF Page 465
- 第 32 章 石油分析和虚拟组分
- 本章内容包括如何实现下述功能
- 关于 ADA/PCS
- 可以用 ADA/PCS 定义和表征石油混合物
- 你可以输入你所选择的数据 如
- 也可以输入任何数量的石油特性曲线 如
- 可以给出任何数量的化验分析数据 ADA/PCS 会实现下述功能
- 你可以定义自己的虚拟组分并用 ADA/PCS 估计它们的物理物性
- ADA/PCS 的应用
- 你可以在以下两种情况下应用 ADA/PCS
- PDF Page 466
- 它们的特性
- 创建分析
- 你可以用下列列表之一来定义化验样品
- 识 中 输入化验样品的名字
- 文件夹
- 选择相应的 Assay 页输入分析数据
- PDF Page 467
- 个步骤
- 品/调和样品
- 择 Assay

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `UG10-CH32` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

- previous: `UG10-CH31`
- next: `UG10-CH33`
- operation-route: `component-property`
- operation-route: `equipment-card`
