<!-- generated: aspen_user_guide_v10 -->
# UG10-CH00 - 前言

Source extract: `../../chapter_extracts/ch00_preface.md`

PDF pages: 1-2

Operation routes:
- `manual-source-boundary`: manual scope and source hierarchy for this graph

## Use When

Triggers: `manual scope`, `volume`, `support`, `手册范围`, `技术支持`

Use this chapter node when an Aspen operation needs the user-guide workflow, UI path, object meaning, or diagnostic order covered by `前言`.

## Chapter Topics

- PDF Page 1
- 关于这本手册
- 型提供了入门知识
- 务 主题包括:
- 第二卷介绍了使用ASPEN PLUS附加功能的过程
- 第三卷信息是关于:
- 关于更多的信息
- PLUS的强大功能来完成你需要做的工程工作
- PDF Page 2
- CD光盘上 你也可以订购Aspen Tech印刷的手册
- 技术支持
- Aspen Tech 主页 网址为:
- http://www.aspentech.com/
- http://www.aspentech.com/ts/
- 列出了最常用的热线联系信息 其它信息包括:
- 们下列地域的任何一个热线联系:
- North America & the
- Caribbean
- +1-617/949-1021
- +1-888/996-7001
- (toll free)
- +1-617/949-1724 support@aspentech.

## Operation Skill Handoff

When `aspen-plus-operations` uses this node, record `UG10-CH00` in the operation note beside any card-level manual graph node IDs. Use this V10 chapter node for workflow/path context, and use `references/manual_knowledge_graph.json` in the operation skill for fragile field-level card rules.

## Reuse Boundary

- Allowed transfer: Aspen UI path, workflow sequence, object definitions, diagnostic order, report/result lookup, and checklist prompts.
- Forbidden transfer: project values, kinetic constants, pressure/temperature defaults, tower stages/reflux, stream compositions, equipment geometry, or example-specific settings.
- If this node conflicts with a project change-offset table, source-freeze ledger, or exported Aspen evidence, the project-local authority wins.

## Edges

- next: `UG10-CH01`
- operation-route: `manual-source-boundary`
