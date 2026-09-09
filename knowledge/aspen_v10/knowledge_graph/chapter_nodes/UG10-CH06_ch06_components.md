<!-- generated: aspen_user_guide_v10 -->
# UG10-CH06 - 第6章 规定组分

Source extract: `../../chapter_extracts/ch06_components.md`

PDF pages: 69-86

Operation routes:
- `component-property`: component IDs, databanks, physical-property methods, property data, and pseudocomponents

## Use When

Triggers: `component`, `databank`, `formula`, `CAS`, `组分`, `数据库`, `别名`

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `第6章 规定组分`.

## Chapter Topics

- PDF Page 69
- 第 6 章 规定组分
- 本章说明在模拟中怎样去定义组分 包括的信息为
- 使用这些窗口规定组分信息:
- 窗口  页 规定的是什么
- Specifications
- Selection
- Petroleum
- Nonconventional
- Databanks
- 在模拟中使用的所有组分
- 混合和虚拟组分
- 非常规组分
- 查找物性参数的纯组分库
- Assay/Blend
- Petro
- Characterization
- 分析和混合 更详细的内容 参见第
- 三十二章
- 虚拟组分特性 更详细的内容 参见
- 第三十二章
- Attr-Comps Selection 给出常规组分的组分属性

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `UG10-CH06` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

- previous: `UG10-CH05`
- next: `UG10-CH07`
- operation-route: `component-property`
