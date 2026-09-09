<!-- generated: aspen_user_guide_v10 -->
# UG10-CH07 - 第7章 物性方法

Source extract: `../../chapter_extracts/ch07_property_methods.md`

PDF pages: 87-102

Operation routes:
- `component-property`: component IDs, databanks, physical-property methods, property data, and pseudocomponents

## Use When

Triggers: `property method`, `base method`, `NRTL`, `SRK`, `物性方法`, `热力学模型`

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `第7章 物性方法`.

## Chapter Topics

- PDF Page 87
- 第 7 章 物性方法
- 近的物性方法和模型的指南 包括
- 什么是物性方法
- 热力学物性是
- 迁移性质是
- 新的适合你的模拟需要的物性方法
- 可以采用的物性方法
- 每一个方法都有专门的计算法表示 K 值
- 下表列出了所有的 ASPEN PLUS 中可以采用的物性方法
- PDF Page 88
- 性方法
- 物性方法
- 理想物性方法
- 理想物性方法  K 值方法
- IDEAL 理想气体/Raoult 定律/亨利定律
- SYSOP0 第 8 版本的理想气体/Raoult 定律
- 状态 方程物性方法
- 状态方程物性方法  K 值方法
- BWR-LS BWR Lee-Starling
- LK-PLOCK Lee-Kesler-Plocker
- PENG-ROB Peng-Robinson

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `UG10-CH07` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

- previous: `UG10-CH06`
- next: `UG10-CH08`
- operation-route: `component-property`
