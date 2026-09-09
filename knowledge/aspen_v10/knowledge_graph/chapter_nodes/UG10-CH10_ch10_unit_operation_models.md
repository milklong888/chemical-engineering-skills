<!-- generated: aspen_user_guide_v10 -->
# UG10-CH10 - 第10章 单元操作模型

Source extract: `../../chapter_extracts/ch10_unit_operation_models.md`

PDF pages: 149-177

Operation routes:
- `equipment-card`: unit-operation model selection and equipment/block input context
- `reaction-card`: reaction sets, stoichiometry, chemistry, kinetic/card boundaries, and user models
- `block-stream`: flowsheet drawing, block/stream objects, stream connection, and information transfer

## Use When

Triggers: `unit operation`, `block`, `heater`, `column`, `reactor`, `单元操作`, `模块`, `反应器`, `塔`

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `第10章 单元操作模型`.

## Chapter Topics

- PDF Page 149
- 第 10 章 单元操作模型
- 见到 要运行一个流程模拟 必须至少规定一个单元操作模块
- 当定义你的模拟流程时 要选择流程模块的单元操作模型 参见第四章
- 选择正确的单元操作模型
- 单元操作模型
- 从下表中选择合适的单元操作模型
- 类型  模型  说明
- 混合器/分流器 Mixer
- Fsplit
- Ssplit
- 物流混合
- 物流分流
- 子物流分流
- 分离器 Flash2
- Flash3
- Decanter
- Sep
- Sep2
- 双出口闪蒸
- 三出口闪蒸
- 液-液倾析器

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `UG10-CH10` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

- previous: `UG10-CH09`
- next: `UG10-CH11`
- operation-route: `equipment-card`
- operation-route: `reaction-card`
- operation-route: `block-stream`
