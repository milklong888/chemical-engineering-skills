# Chemical engineering workspace

Use the installed `chemical-engineering-expert` skill before chemical-process,
Aspen, equipment or engineering-report work:

`{CHEM_SKILLS}/chemical-engineering-expert/SKILL.md`

本工作区的交付还包括配套脚本、文件处理和工具维护。收尾出现新的可复用成果，
或用户让你整理/确认经验时，先读
`{CHEM_SKILLS}/chemical-engineering-expert/references/EXPERIENCE_INBOX.md`，
再按该规则交付；这条入口不依赖是否正在运行工程模型。简短回复仍须保留当前
合格候选的具体摘要、已验证范围和投稿入口。没有发布授权时只停止发布，仍完成
本地提醒并就展示的摘要询问一次；已拒绝、已询问待答或已有有效授权时按对应分支处理。

1. Establish the current objective, system boundary, design basis, required
   method, allowed changes and acceptance criteria.
2. Read the current project authority and change record, then the expert's
   compact guards and the selected professional workflow. Use one main workflow
   and load detailed references when their operation is needed.
3. Distinguish source facts, same-case results, deterministic derivations,
   engineering estimates and unresolved inputs. Retrieval rank is not evidence.
4. Check derivable inputs before declaring them missing. Keep estimates and
   assumptions visible, and limit missing evidence to the affected conclusion.
5. Review chemistry, properties/phases, balances, process order, component fate,
   heat/pressure paths, recycle/purge, equipment, operability and safety before
   detailed implementation and common-basis optimization.
6. Keep engineering decisions separate from card-writing and software mechanics.
   Record material changes before applying them, then recalculate affected units.
7. Use same-candidate exports for equipment checks. Distinguish physical limits
   from incomplete data or catalog coverage; justify extra stages or parallel
   equipment by applicable constraints or whole-system benefits.
   At source/scaffold/island/reconnect/change/delivery events, follow the expert's
   `references/DESIGN_STAGE_ROUTING.md` and actually execute `design_stage`
   through the bundled CLI or MCP. Preserve its real query/calculation receipt.
   It is not an engineering pass. Narrow lookup, template and formatting tasks
   use only their relevant workflow; do not manufacture a full-flow scope.
8. Keep readout, preliminary calculation, software execution, clean convergence,
   product compliance and formal delivery as separate states. Apply the version-
   bound evidence checks in the expert and operation skills.
9. Keep project inputs and results outside the skill directory. Use controlled
   working copies, record file identities and preserve original sources.
10. 收尾按上面的经验入口读取对应分支，由主助手展示当前候选和
    [投稿入口](https://github.com/milklong888/chemical-engineering-experience-inbox)。
    已授权准备就交实际摘要/草稿；思想先确认同一原文，再审核；不得用“待确认”
    代替需要的当次请求，已有有效授权不重复索取，拒绝后不催促。没有新可复用
    增量则不凑经验。临时收件不进入正式 Skill/默认检索；正式晋升仍需用户发起
    整理并明确关闭相关版本，放宽标准的案例及派生内容仅留项目审计。

Before lookup, live relations, target matching, response studies or multi-variable
tuning, read the document-driven workflow's
`references/aspen_builtin_solve_fit_tools.md` and call `solve_route`.
Classify intent even without tool names. Native analysis is preferred when
applicable; scripts may configure it, but an external point sweep is not a native
Sensitivity object. The routing receipt is not execution or acceptance evidence.

Read `LOCAL_KNOWLEDGE_GRAPH_LINKS.md` before resolving knowledge/software paths.
The installed `chemical-engineering-runtime/` provides bundled headless knowledge,
equipment, pressure and process-feedback interfaces. Resolve legacy graph names
through that map; a missing desktop GUI is not a missing calculation backend.
Use source-bound constraints before exchanger-series, compressor-stage or
parallel-column proposals, then update the real model and recalculate affected
consumers. Never count a proposed topology as an implemented flowsheet.

Missing source material or licensed software is a declared dependency, not
permission to fabricate results. This workspace template contains no project data.
