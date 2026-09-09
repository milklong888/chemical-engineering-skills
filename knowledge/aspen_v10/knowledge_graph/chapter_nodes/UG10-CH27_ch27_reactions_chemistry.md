<!-- generated: aspen_user_guide_v10 -->
# UG10-CH27 - 第27章 规定反应和化学

Source extract: `../../chapter_extracts/ch27_reactions_chemistry.md`

PDF pages: 377-393

Operation routes:
- `reaction-card`: reaction sets, stoichiometry, chemistry, kinetic/card boundaries, and user models
- `component-property`: component IDs, databanks, physical-property methods, property data, and pseudocomponents

## Use When

Triggers: `reaction`, `chemistry`, `stoichiometry`, `kinetics`, `反应`, `化学`, `动力学`

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `第27章 规定反应和化学`.

## Chapter Topics

- PDF Page 377
- 第 27 章 规定反应和化学
- 本章描述了如何使用 ASPEN PLUS 定义反应系统 包括
- 关于反应和化学
- 反应系统  说明  使用 Data Brower 表
- 电解质溶液化学 包含离子类型的反应 Chemistry
- 非电解质反应 流率控制或平衡限制
- 用于反应器和反应蒸馏模
- Reactions
- 压计算 这些反应用于
- 使用下述表达式之一描述以流率为基础的反应的反应动力学
- 们用于使用那个物性规定的所有计算
- PDF Page 378
- 关于电解质化学
- 系统中
- 电解质系统使用它们的基础分子组成 表观的组成 来描述 并且通过
- 有三种类型的电解质
- 类  型 例   子
- 部分电离平衡* HCl + H2O H3O+ + Cl
- 盐沉降平衡* NaCl(盐) Na+ + Cl
- 完全电离 NaCl(液相) Na+ + Cl
- 的内容

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `UG10-CH27` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

- previous: `UG10-CH26`
- next: `UG10-CH28`
- operation-route: `reaction-card`
- operation-route: `component-property`
