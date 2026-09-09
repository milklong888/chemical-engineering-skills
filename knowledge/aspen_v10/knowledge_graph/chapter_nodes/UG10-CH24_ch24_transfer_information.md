<!-- generated: aspen_user_guide_v10 -->
# UG10-CH24 - 第24章 在物流或模块间传递信息

Source extract: `../../chapter_extracts/ch24_transfer_information.md`

PDF pages: 359-363

Operation routes:
- `calculator`: flowsheet variables, information transfer, Balance blocks, and Fortran/Calculator logic
- `block-stream`: flowsheet drawing, block/stream objects, stream connection, and information transfer

## Use When

Triggers: `transfer`, `information`, `calculator`, `传递信息`, `模块间信息`

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `第24章 在物流或模块间传递信息`.

## Chapter Topics

- PDF Page 359
- 第 24 章 在物流或模块间传递信息
- 下述的目标
- 最常用的是将一个物流拷贝成另一个物流
- 本章包括
- 定义一个传递模块
- 1. 创建传递模块
- 2. 拷贝一个物流 物流流率 一个子物流或一个模块或物流变量
- 3. 可选择地输入目标物流的闪蒸规定
- 艺进料物流表或其它物流的源模块中的闪蒸选项
- 4. 当传递模块运行时可选择地规定
- 缺省情况下 ASPEN PLUS 将自动地将模块排序
- 本章的后续部分将描述这些步骤
- 创建一个传递模块
- 拷贝流程图变量
- PDF Page 360
- 在 Form 页中如果你选择 ASPEN PLUS 拷贝
- Entire stream 完整物流
- Stream flow 只有组分流率和一个物流的全流率
- Substream 全部子物流
- 当比例缩放的变量被拷贝时 同一页中的变
- 量类型不必相同 但每个变量类型必须有相

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `UG10-CH24` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

- previous: `UG10-CH23`
- next: `UG10-CH25`
- operation-route: `calculator`
- operation-route: `block-stream`
