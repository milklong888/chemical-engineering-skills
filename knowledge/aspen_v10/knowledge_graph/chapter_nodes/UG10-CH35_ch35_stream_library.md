<!-- generated: aspen_user_guide_v10 -->
# UG10-CH35 - 第35章 创建物流库

Source extract: `../../chapter_extracts/ch35_stream_library.md`

PDF pages: 505-509

Operation routes:
- `case-io`: open, create, save, import, export, archive, and automate case files
- `block-stream`: flowsheet drawing, block/stream objects, stream connection, and information transfer

## Use When

Triggers: `stream library`, `物流库`

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `第35章 创建物流库`.

## Chapter Topics

- PDF Page 505
- 第 35 章 创建物流库
- 第35章   创建物流库
- 你能从物流库中检索关于物流组分和条件的信息 而不用从物流表中输入数据
- 下表显示使用物流库能做到的功能
- 创建一个经常使用的进
- 料物流数据库
- 将经常使用的进料物流组成和状态存储在物流数据库中 从一
- 个模拟的不同模型中检索该信息 而不用重新输入
- 在一个模拟与另一个模
- 拟之间传递物流信息
- 模拟一段流程 把出口物流存储在一个库中 在另一个模拟过
- 程中检索该信息
- 或在模拟一个过程中不同部分的两个组之间共享一个库
- 初始化撕裂流 把一个模拟过程的最终撕裂流的值存储在库中
- 果你不知道选哪一个作为撕裂流 从第一个模拟过程存储所有
- 物流 在新运行时检索所有物流
- 从一个大流程中隔离出
- 一个模块
- 把一个大流程的物流存储在一个库中
- 从已存储的流程中检索分析一个模块 并单独模拟它 也可用
- 更高级诊断或改变条件 对于一个隔离模块可以省去重新输入

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `UG10-CH35` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

- previous: `UG10-CH34`
- next: `UG10-CH36`
- operation-route: `case-io`
- operation-route: `block-stream`
