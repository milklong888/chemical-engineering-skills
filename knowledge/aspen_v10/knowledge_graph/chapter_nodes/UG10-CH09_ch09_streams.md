<!-- generated: aspen_user_guide_v10 -->
# UG10-CH09 - 第9章 规定物流

Source extract: `../../chapter_extracts/ch09_streams.md`

PDF pages: 130-148

Operation routes:
- `block-stream`: flowsheet drawing, block/stream objects, stream connection, and information transfer
- `component-property`: component IDs, databanks, physical-property methods, property data, and pseudocomponents

## Use When

Triggers: `stream`, `flash specification`, `composition`, `物流`, `温度`, `压力`, `组成`

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `第9章 规定物流`.

## Chapter Topics

- PDF Page 130
- 第 9 章 规定物流
- 模块带到另一个单元模块 物流可以是
- 本章包括以下内容
- 规定物流
- 对于所有的进料物流 必须规定
- 还可以提供撕裂 循环 物流的初始估值
- 输入物流规定
- 要输入一个物流的规定
- 1. 双击流程图中的物流
- 象管理器 窗口中 选择物流并单击 Edit 编辑
- 分率 要了解其有效的选项 请参见第九章 可能的物流热状态规定一节
- 输入物流组成一节 如果物流中包括固体子物流 执行4-6步
- PDF Page 131
- 规定它们的值 要了解更多的信息 请参见第九章 规定粒子尺寸分布一节
- 允许的物流热状态规定
- 该表说明了允许的物流热状态规定
- 相态  游离水  状态规定  物流物性的计算方法
- 气相 不 温度 压力 气相热计算
- 固相 不 温度 压力 固相热计算
- 液相 不 温度 压力 液相热计算
- 液相-游离水相 不 温度 压力 带有游离水的

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `UG10-CH09` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

- previous: `UG10-CH08`
- next: `UG10-CH10`
- operation-route: `block-stream`
- operation-route: `component-property`
