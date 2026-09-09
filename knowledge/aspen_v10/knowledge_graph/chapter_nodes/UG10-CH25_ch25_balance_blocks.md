<!-- generated: aspen_user_guide_v10 -->
# UG10-CH25 - 第25章 平衡模块

Source extract: `../../chapter_extracts/ch25_balance_blocks.md`

PDF pages: 364-373

Operation routes:
- `calculator`: flowsheet variables, information transfer, Balance blocks, and Fortran/Calculator logic
- `block-stream`: flowsheet drawing, block/stream objects, stream connection, and information transfer

## Use When

Triggers: `balance`, `mass balance`, `energy balance`, `平衡模块`, `物料平衡`, `能量平衡`

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `第25章 平衡模块`.

## Chapter Topics

- PDF Page 364
- 第 25 章 平衡模块
- 用计算的结果更新进入或离开封闭区的物流变量 比如 平衡模块可以计算
- 本章包括下述题目
- 定义一个平衡模块
- 定义一个平衡模块按下述步骤
- 1. 创建一个平衡模块
- 2. 规定平衡计算的模块和物流
- 3. 规定和更新物流变量
- 4. 平衡模块排序
- 5. 可选择地规定闪蒸条件
- 创建一个平衡模块
- 表 页 规定的是什么
- Energy Balance 包括在每个能量平衡封闭区内的模块或物
- 和 Energy Balance 页上所做的规定
- Calculate 在物料和能量平衡计算后物流变量要计算
- 且更新
- Scale 物流比例缩放因子
- PDF Page 365
- Sequence 平衡模块可选择的运行顺序
- Stream Flash 规定物流的可选的闪蒸规定
- 本页也用于不对由 Balance 模块更新的物流

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `UG10-CH25` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

- previous: `UG10-CH24`
- next: `UG10-CH26`
- operation-route: `calculator`
- operation-route: `block-stream`
