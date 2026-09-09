<!-- generated: aspen_user_guide_v10 -->
# UG10-CH14 - 第14章 给工艺流程作注解

Source extract: `../../chapter_extracts/ch14_flowsheet_annotations.md`

PDF pages: 208-217

Operation routes:
- `delivery-qa`: reports, PFD annotations, file packages, plots, external program exchange, and deliverable checks
- `block-stream`: flowsheet drawing, block/stream objects, stream connection, and information transfer

## Use When

Triggers: `annotation`, `PFD`, `text`, `注解`, `标注`, `流程图`

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `第14章 给工艺流程作注解`.

## Chapter Topics

- PDF Page 208
- 本章介绍了给工艺流程作注解的方法 其中包括
- 添加注解
- 可以把附加的文本 图形和表加到流程上
- 例如 下图所示即是带有注解的流程 它列出了标题和流股结果表
- 添加流股表
- 你可以向流程中添加流股表 以表格形式显示出流股的性质
- 要在你的流程中生成一个流股表 可按下列步骤进行
- 1. 保证该流程有可用的结果 如果没有可用的结果 则运行模拟
- 2. 在 View菜单上 保证选定了 Annotation
- Streams
- 所有流股的结果都可显示出来 详细信息参见第十二章
- PDF Page 209
- 其选项有 顺序 标签 单位和精度 参见第十二章和第三十六章
- 5.  单击 Stream Table 按钮
- ASPEN PLUS 即把流股表添加到你的图中
- 缩小 或者改变它的尺寸
- 6.  用键盘或者鼠标把该表格移到你希望的位置
- 调整流股表的大小
- 可以通过改变字体大小调整流股表的大小 方法如下
- 1. 单击流股表选定它
- 2. 在 Draw 工具栏上 改变字体大小

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `UG10-CH14` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

- previous: `UG10-CH13`
- next: `UG10-CH15`
- operation-route: `delivery-qa`
- operation-route: `block-stream`
