<!-- generated: aspen_user_guide_v10 -->
# UG10-CH04 - 第4章 定义流程

Source extract: `../../chapter_extracts/ch04_define_flowsheet.md`

PDF pages: 36-52

Operation routes:
- `block-stream`: flowsheet drawing, block/stream objects, stream connection, and information transfer

## Use When

Triggers: `flowsheet`, `model library`, `ports`, `stream connect`, `流程`, `模型库`, `物流连接`

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `第4章 定义流程`.

## Chapter Topics

- PDF Page 36
- 第 4章 定义流程
- 本章说明了如何在 ASPEN PLUS 中定义一个过程流程图 包括
- 关于用户界面的说明和信息 请参见第一章
- 创建一个流程
- 定义一个流程用如下步骤
- 成你模拟模型的一部分 想了解更多的信息 请参见第十四章
- 2. 选择单元操作模块并将它们放置到流程窗口
- 3. 用物流连接模块
- 在放置模块和物流后 你可以
- 式的含义
- 指针形状  功能  使用
- 选择模式 单击一个对象去选择它 单击并拖动一个对象进入移动
- 模式 单击并拖动所选择的区域或移动或改变所选区域
- 的尺寸 指针改变用以改变尺寸的形状
- 插入模式 单击并放置一个从模型库中选择的模型类型 注 放置
- 每个模块后 你将一直保持插入模式 直到你在模型库
- 的左上角单击选择模式键
- 连接模式 单击一个端口将其与物流连接 单击流程的空白区域放
- 置进料或产品
- 移动模式 单击并按住鼠标将对象移动到想要的位置
- 端口移动模式 单击并按住鼠标键移动端口到想要的位置 拖动此端口

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `UG10-CH04` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

- previous: `UG10-CH03`
- next: `UG10-CH05`
- operation-route: `block-stream`
