---
name: aspen-pressure-pfd-delivery
description: Audit and repair Aspen Plus full-flow pressure topology, PFD-style documentation, and LaTeX/PDF delivery packages for chemical-design projects. Use when the user mentions Aspen pressure equipment, compressors/pumps/valves, natural high-pressure feeds, HEATER PRES=0, PFD/PDF/LaTeX reports, bkp/apwz generation, or final delivery packaging for Aspen flowsheets.
---

# Aspen Pressure PFD Delivery

## 工作过程

先沿当前流程的真实连接逐段核对压力：入口是什么压力，哪些地方需要泵或压缩机升压，哪些单元产生压降，哪里允许节流。用当前几何、物性和适用计算方法建立压降账本，检查热块是否隐藏升压、循环是否有回流压差，以及串联损失和并联共同压差是否处理正确。

需要改变压力设备或工况时，按[阶段调用规则](../chemical-engineering-expert/references/DESIGN_STAGE_ROUTING.md)调用设备检查，再由操作模块修改受保护模型和重跑。确认后才同步PFD、设备标签和报告，让图中的顺序、压力和回流路径都来自同版导出。最后检查模型验收、图文一致性和渲染页面；仅修改排版时不无故重算全流程。

## Network Position

Use this as a pressure/PFD overlay under `aspen-document-driven-flowsheet` or a
specialist section/tower workflow. Upstream authority supplies the accepted
case, pressure ledger, allowed pressure-drop convention, and claims to verify.
This skill returns pressure topology evidence, PFD/PDF synchronization evidence,
and any blocked pressure assumptions to the process authority layer. Mechanical
case generation, run/export, and package QA still go through
`aspen-plus-operations` when that skill is available.

## Scope

Use this on an existing process flowsheet, section or tower when its pressure topology or PFD/delivery evidence needs work. A component-only template does not by itself trigger a pressure workflow. Use the relevant document skill for PDF layout when needed. This skill covers hidden pressure changes in heaters, stale `.bkp/.apwz` files, forced sequences causing recycle mass imbalance, and PDF/PFD claims drifting from the actual model.

When the current workspace contains
`aspen_sun_lanyi_knowledge/knowledge_graph/README.md`, read it as a local Aspen
knowledge overlay before pressure/PFD edits. Use `unknowns_router.md` for
pressure, dynamic-export, convergence, and unit-block routing, and use
`kinetics_expert_system.md` before changing any kinetic reactor that also has a
pressure, geometry, or delivery impact. If the pressure/PFD issue resembles a
lecture case such as heat pump distillation, HIDiC, dynamic export, or column
pressure analysis, use `classic_cases_playbook.md` only for transferable
patterns, not example values. Ignore this hook outside that workspace.

## Aspen Editing Rules

- Do not hand-edit `.bkp` or `.apwz` internals. Use the existing operations path on a protected candidate. Regenerate from INP only when that route is authorized and preserves the required graphical/layout authority; do not rebuild an accepted intermediate model merely for a pressure check.
- Freeze each fresh/boundary feed pressure from current source evidence; do not assume natural high pressure or a universal low-pressure value.
- Put pressure changes in explicit equipment:
  - Gas to higher pressure: `COMPR`, with the current pressure target and source-backed efficiency/basis.
  - Liquid to higher pressure: `PUMP`, with the current pressure target and source-backed efficiency.
  - Letdown: `VALVE`, e.g. `PARAM P-DROP=<bar>`.
- Make the thermal block's pressure-drop convention explicit and source-backed. Use `PRES=0` only when the current model/version and authorized no-drop convention call for it; do not conceal a pressure rise in a heater.
- Keep every reactor pressure condition explicit and tied to its current source and accepted pressure ledger; no private-case reactor pressure table is supplied.
- If a closed recycle case breaks after adding pressure equipment, suspect forced `SEQUENCE MASTER` before weakening the process model. Prefer `CHECKSEQ=NO` with a convergence method already proven for the case.

## Pressure Audit Checklist

After regeneration, verify these from the exported `*_after_run.inp`, block CSV, and stream CSV:

- All thermal-block pressure specifications match the accepted pressure-drop convention; no hidden pressure-raising service is assigned to a heater.
- Fresh/boundary feeds match current source pressure before each explicit pressure-changing device.
- Each pressure jump has a named pump/compressor/valve and status `0`.
- Stream pressures show the intended breakpoints before and after equipment.
- Reactor blocks still run at intended pressure and are not relying on upstream heater pressure.
- Calculators writing feed streams do not write over the outlet of an already-calculated block.

Useful PowerShell patterns:

```powershell
Import-Csv '.\*_blocks.csv' |
  Where-Object { $_.blkstat -notin @('', '0') -or $_.blkmsg }

Import-Csv '.\*_streams.csv' |
  Where-Object { $_.stream -in $currentPressureAuditStreams } |
  Select stream,temp_C,pressure_bar,mole_flow_kmol_h,mass_flow_kg_h

Select-String -LiteralPath '.\*_after_run.inp' `
  -Pattern 'BLOCK E\d+ HEATER|PARAM .*PRES=0|BLOCK K\d+ COMPR|BLOCK P\d+ PUMP|BLOCK V\d+ VALVE'
```

## PFD And Documentation Rules

- PFD pages must reflect the current Aspen topology. Trace each fresh feed, conditioning unit, pressure device, mixer and recycle in actual order; do not reproduce a private-case block sequence.
- Show every current pressure-changing device and its current tag on the PFD when it matters to the pressure audit.
- State the accepted thermal-block pressure-drop convention and expose pressure errors in the actual pumps, compressors, valves, flashes and reactors.
- If a calculator leaves a near-zero positive feed, document the numerical bound separately from physical feed-system requirements; the bound must come from the current project, not a historical example.
- When replacing a boundary or seed recycle with an internal recycle, update the PFD/report to show the real return path and pressure equipment. Then search the generated PDF text, Markdown, LaTeX, and `*_after_run.inp` for stale seed-stream names or obsolete recycle claims.
- When updating Markdown, LaTeX, and generated PDF, keep claims synchronized with file timestamps, page count, and rendered pages.

## PDF/LaTeX Delivery Workflow

1. Regenerate `.tex` from the current Markdown/source script.
2. Compile with XeLaTeX twice.
3. If the target PDF is open and locked, do not fight the viewer; compile with a new job name such as `_fixed`.
4. Verify page count with `pypdf`.
5. Render key PFD pages using `pdftoppm` and inspect PNGs visually.
6. Extract text from PFD pages with `pdftotext` to confirm critical equipment labels are present.
7. In the final response, mention the locked old PDF if the correct version has a new filename.

## Delivery Package

For a requested combined model/PFD/report handoff, package the following
applicable artifacts. A pressure-only or formatting-only task returns its scoped
evidence without inventing additional model or document deliverables:

- Correct PDF, `.tex`, Markdown source, and report generation script.
- Root `.bkp/.apwz` files for the deliverable Aspen case and any standalone reactor case.
- The Aspen generation script and exported `.inp`, `*_after_run.inp`, stream CSV, block CSV, and run summary CSV.
- A short note in the final answer with validation status, page count, and any file that could not be overwritten because it was open.

阶段收尾若发现有证据且值得复用的新方法或原则，将候选交主助手，按
[主动经验提醒](../chemical-engineering-expert/references/EXPERIENCE_INBOX.md#主动提醒使用者)
展示可审阅摘要并推进确认/投稿；拒绝不催促，已有有效授权不重复询问。
