---
name: aspen-heat-pump-distillation-replacement
description: Replace an Aspen Plus RadFrac distillation column with an empty-column vapor-recompression heat-pump distillation island and reconnect it into a larger section. Use when the user asks for heat-pump distillation, VRC/MVR distillation, external condenser/reboiler replacement, empty tower conversion, HeatX-assisted distillation retrofit, or boundary-preserving tower-island replacement.
---

# Aspen Heat-Pump Distillation Replacement

## 工作过程

先运行并固定原塔的进料、产品和热量基准，再切出边界明确的塔岛，按本模块的等效替换方法建立外部换热、蒸汽压缩、回流和汽化返回回路。先恢复原塔的分离结果，再调节压缩和换热条件，比较外供热量的减少是否值得新增的电耗、设备和控制要求；不会为了节能数字好看而悄悄降低产品要求。

塔的分离计算交塔优化模块，卡片和运行交操作模块；压缩与换热条件形成后，按[阶段调用规则](../chemical-engineering-expert/references/DESIGN_STAGE_ROUTING.md)实际查适用方法并校核设备。温差、排气状态、压降或能力不满足时先修岛内方案，经过边界核验后再接回全流程复算。结果同时说明等效替换、节能收益、设备证据和整体验收各自达到的程度。

## Trigger Contract

Use this skill for heat-pump distillation replacement, not for generic heat
integration.

When reviewing a retrofit's savings claim without editing a model, retain the
same product/capacity basis and review compressor discharge temperature,
pressure, phase and operability along with heat, power, economics and emissions.
Missing discharge evidence remains a feasibility gap even if the utility
arithmetic can be evaluated.

The accepted pattern is an equivalent tower retrofit:

```text
RadFrac internal condenser/reboiler disabled
-> tower overhead vapor compressed
-> compressed vapor heats tower bottoms in external HeatX
-> hot-side condensate is let down and split by one FSPLIT for reflux/distillate
-> cold-side heated bottoms flash to vapor return and bottoms product
-> tower-equivalence variables recover the original tower products first
-> HeatX/compressor variables polish heat-pump reasonableness second
```

Route mechanical Aspen actions through `aspen-plus-operations`. Use
`aspen-tower-optimization-workflow` for the base tower target ledger and
`aspen-document-driven-flowsheet` for section authority, boundary contracts,
change-offset rows, and final promotion.

## Required Reads

First read `references/ERROR_MEMORY.md` and the chemical expert's
`STRICT_ACCEPTANCE_AND_LEARNING.md`. Strict is the default; a user-authorized
local relaxation and all descendants are audit-only, never self-evolution or
shared/default knowledge. Use the same complete version-bound Summary/history
gate as operations, not a separate warning exception.

Open these files before edits:

- `references/replacement_workflow.md`
- `templates/empty_column_vrc_template.inp`
- `templates/design_spec_patterns.inp`

Historical project cards are not distributed. If comparable local case evidence
is supplied, use it only for transferable workflow and independently verify all
stream values, equipment and operating targets against the current case.
For an already on-spec base tower, equivalent replacement must preserve its
product boundary before considering any additional polishing equipment.

## Quick Workflow

等效替换开始调参及改变压缩压力前，按
[内置工具规则](../aspen-document-driven-flowsheet/references/aspen_builtin_solve_fit_tools.md)
调用 `solve_route`。原产品边界由活跃 Design Specs 闭合，压缩/换热外层
采用原生 Sensitivity 或适用的 Optimization；每个点都重解内层分离规格，
再比较供热、压缩功及设备。只读某股焓或某点温差不因此启动优化。

1. Freeze the original tower/section baseline.
   Run the unmodified tower island and, when full-flow/section integration is
   in scope, its actual larger section island. A standalone tower request does
   not require inventing a parent flowsheet. Export
   after-run INP, stream results, block status, energy summary, and boundary
   stream table.
2. Cut scope conservatively.
   Build a single-tower island first if needed, then the larger section island
   that owns the real reconnect boundary. Do not edit the full flow first.
3. Convert the tower to an empty tower.
   Set `COL-CONFIG CONDENSER=NONE REBOILER=NONE`. Remove internal distillate
   and bottoms duties as active heat sources. Adjust stage count and feed
   stages after removing condenser/reboiler stages.
4. Insert the VRC loop.
   Send tower overhead vapor to compressor, then HeatX hot side. Send tower
   bottoms liquid to HeatX cold side. Flash the heated bottoms to a vapor return
   plus bottoms product. Cool/let down/split condensed overhead into distillate
   and reflux.
   Use one tower-top reflux/product splitter by default. Do not add a flash,
   mixer, or heater chain above the splitter just to patch phase or flow unless
   the current case has a documented physical reason; otherwise that branch is
   diagnostic, not the standard heat-pump replacement.
5. Keep optional trim equipment small and documented.
   Phase conditioning requires the current phase/model and equipment basis;
   do not automatically add a guard heater or override an explicitly authorized
   vapor-liquid process model. Its duty is not the main heat source. A trim cooler/heater may polish flash
   temperature, but the HeatX/compressor loop must carry the heat-pump duty.
6. Tune for equivalence, not instant optimum.
   First prove the exported topology is complete: empty tower, COMPR, HEATX,
   FLASH2, FSPLIT, VALVE, reflux, and vapor return. Then freeze the tower feed
   boundary and recover the original tower products before optimizing heat
   recovery. Use stage/tray count or feed/return stage, the single
   reflux/product splitter fraction, and the liquid-side flash temperature or
   pressure as the default separation knobs. These should usually be enough to
   return the tower to its standard result. Only after that, polish compressor
   pressure, HeatX cold outlet/approach, and small trim temperatures.
   Use only the current user's explicitly authorized local bracketing tolerance;
   it is case-local, not a shared numerical default. The connected tower system must still
   return to default/design-rule precision before delivery.
   If downstream tower-system history remains dirty after local equivalence,
   repair the convergence boundary first: tear a stable downstream section feed
   or mixer outlet plus the local heat-pump recycles before touching final
   product streams, downstream tower specs, product standards, or tolerances.
   Good first guesses: keep the original tower stage count adjusted only for
   removed condenser/reboiler stages; keep the feed stage near the original
   relative position; set the reflux split from the original reflux/(reflux +
   distillate) scale, not an arbitrary product fraction; set the bottom flash
   near the original bottom/reboiler-side temperature and pressure; set HeatX
   cold outlet near but slightly below the desired flash temperature; set
   compressor pressure only high enough to give a positive HeatX approach; set
   trim cooler near the original condenser/drum temperature.
   If the original single RadFrac already met a strict product purity, the
   first target is equivalent replacement: reproduce the original reflux scale,
   boilup/vapor-return scale, tower temperature logic, and product impurity
   leakage before changing downstream equipment. Do not add a second polishing
   tower, a bottoms-liquid bypass splitter, or any splitter other than the
   overhead reflux/product splitter as a promoted fix.
7. Promote only after gates pass.
   Required gates: baseline and candidate run, heat-pump blocks present,
   empty-tower cards exported, required block statuses acceptable, compression
   compatible with the frozen phase/model and equipment evidence (no unresolved
   actual wet-compression error), boundary streams within tolerance, reconnect seed streams
   exported, and same-version BKP saved after the accepted run.
   Separate a topology/equivalence acceptance from a zero-warning delivery
   acceptance. A candidate may be useful for design once final blocks and
   boundary streams pass, but it is not a delivery candidate while copied
   history still contains startup/recycle warnings or errors.
   Property-parameter warnings are a separate property/databank repair gate;
   do not clear them by retuning accepted separation targets or product specs.
   If Aspen COM cannot persist added local recycle streams on the exported
   `TEAR` card, do not rebuild the tower solely for that text-card gap when the
   streams are real, connected, nonzero, and a no-mutation BKP reopen/run
   returns the same solution. Classify it as convergence/delivery cleanup and
   keep strict zero-warning delivery blocked until the required evidence is
   resolved. Documentation alone does not waive a failed strict gate.

## Delegation Pattern

For nontrivial replacements, delegate bounded factual work when multi-agent
tools are available:

- one agent reads baseline/tower cards and reports exact streams/cards;
- one agent scans final INP/history/CSV gates;
- one agent verifies package files, hashes, and boundary rows.

Subagents must be fact-only. The main agent keeps topology choices, Design Spec
selection, acceptance, and final user-facing claims.

Follow the current task's authorized subagent cap. Reuse an
existing factual subagent when possible. Do not let a subagent decide that a
candidate is accepted; it may only report exact paths, rows, block statuses,
card snippets, and command status.

## Stop Conditions

Stop and report a blocker instead of promoting when any of these remain:

- compression conflicts with the frozen phase/model/equipment contract or
  history reports an unresolved actual wet-compression error; a user-authorized
  vapor-liquid calculation still needs same-case physics and equipment evidence;
- internal condenser/reboiler still carry unlinked main duty;
- exported topology lacks HeatX, flash, valve, splitter, reflux, or vapor return;
- boundary streams fail against the accepted baseline;
- Design Specs hit bounds or fight each other without a project decision;
- the large section cannot rerun after the single-tower island passes;
- the delivered BKP was not saved after the accepted run.

阶段收尾若发现有证据且值得复用的新方法或原则，将候选交主助手，按
[主动经验提醒](../chemical-engineering-expert/references/EXPERIENCE_INBOX.md#主动提醒使用者)
展示可审阅摘要并推进确认/投稿；拒绝不催促，已有有效授权不重复询问。
