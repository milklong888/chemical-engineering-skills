<!-- generated: aspen_user_guide_v10 -->
# UG10-CH34 - 第34章 插入

Source extract: `../../chapter_extracts/ch34_insert.md`

PDF pages: 501-504

Operation routes:
- `block-stream`: flowsheet drawing, block/stream objects, stream connection, and information transfer
- `delivery-qa`: reports, PFD annotations, file packages, plots, external program exchange, and deliverable checks

## Use When

Triggers: `insert`, `object`, `OLE`, `插入`, `对象`

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `第34章 插入`.

## Chapter Topics

- PDF Page 501
- 第 34 章 插入
- 创建你自己的插入
- 本章讨论这些文件的使用 包括
- 创建一个插入
- 你可以使用插入来创建
- 2. 在 File菜单上 单击 Export
- 4. 对于你想包含插入的备用文件 为其输入目录和一个文件名
- 5. 单击 Save
- 你可以将创建的备用文件转入到运行里
- 转入插入
- 在已存在的 ASPEN PLUS 模拟中转入插入
- 3  在 Import 对话框里 找到插入 然后单击 Open
- 把插入已存在的运行中后 你的模拟就包括来自两个文件的输入
- 解决 ID 矛盾
- 两个文件中的所有有匹配 IDs 的对象
- PDF Page 502
- 方法  步骤
- 替代存在对象 1  选择一个或多个对象
- 2  单击 Replace.
- ASPEN PLUS 删除当前运行中的对象并用转入的对象替代
- 合并新对象和存在对

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `UG10-CH34` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

- previous: `UG10-CH33`
- next: `UG10-CH35`
- operation-route: `block-stream`
- operation-route: `delivery-qa`
