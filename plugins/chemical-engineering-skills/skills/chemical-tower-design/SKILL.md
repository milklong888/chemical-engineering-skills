---
name: chemical-tower-design
description: Evidence-driven workflow for designing, recalculating, auditing, and documenting chemical tray or packed columns. Use for tower process sizing, tray/packing hydraulics, column geometry, internals, mechanical handoff, standards lookup, engineering drawings, dependency propagation, formula-chain cleanup, or independent tower-design review from PDF/DOCX/project data.
---

# Chemical Tower Design

## 工作过程

从已核实的塔进料、产品、温压、级数和回流基准出发，先调用设备程序识别塔型和可计算参数，再查询适用的塔盘、填料与标准方法。随后按各段实际汽液负荷推算直径、有效面积和内部几何，计算压降、漏液、夹带与液泛等边界，形成各负荷工况的性能范围，才继续确定塔高及机械设计交接条件。

操作点、负荷或几何变化时，按[阶段调用规则](../chemical-engineering-expert/references/DESIGN_STAGE_ROUTING.md)刷新相关检查，把新压降与能力限制送回塔优化和全流程复算。图纸、重量、材料与报告都随同一计算账本更新。F1负荷图只在相应任务下读取专用入口；缺少实测、软件或厂家依据的项目，不因曲线画出来了就算正式通过。

Use this skill to produce a traceable tower design whose process basis, hydraulic geometry, mechanical envelope, figures, and report equations remain mutually consistent.

Read [references/ERROR_MEMORY.md](references/ERROR_MEMORY.md) before the ordinary workflow. Read [references/NEW_KNOWLEDGE.md](references/NEW_KNOWLEDGE.md) when recent candidate knowledge may affect the active design.

For acceptance or learning, follow the central chemical-expert
`references/STRICT_ACCEPTANCE_AND_LEARNING.md`: current-stage strict evidence
is default; a user-approved case relaxation does not update shared rules or
enter learning/default retrieval, including through descendants.

## Start with authority and retrieval

1. Open the workspace knowledge-graph link map and `equipment-design-app` before changing a design. Resolve the bundled runtime, equipment graph and standards evidence there; no separate desktop app or repository is required.
2. For Aspen exports, use the bundled equipment derivation route through the unified interface so every process-side parameter keeps its stream/block field, unit conversion, export hash, run-evidence state and equation chain. For canonical parameters use its registered manual matching request. Discover exact fields with `tools/expert_cli.py --describe` and `--schema`; do not guess top-level script paths. Treat deterministic family/formula/standard/model-status output as the primary match, then audit and execute this tower workflow.
3. If several tray/packing/structural branches remain feasible, retain the most general tower family/type and candidate set until their required inputs close one branch; do not select a specialized internal merely by score or convention.
4. Freeze project inputs, approved deviations, software outputs, and unresolved values in a source ledger.
5. Query bundled standards facts through the unified `equipment_standards` search. Use `scripts/query_tower_sources.py` only with its explicitly configured local source profile; do not treat private original pages as bundled.
6. Classify every retrieved source as `direct_reuse`, `method_only`, `software_boundary`, `vendor_boundary`, or `forbidden_transfer` before using it.
7. Never copy example geometry, vendor capacity, stream data, or another equipment tag's values into the active tower.

Read [references/evidence_routing.md](references/evidence_routing.md) whenever authority is incomplete or sources disagree. Read [references/query_contract.md](references/query_contract.md) before running standards queries.

## Execute the design chain

Follow [references/tower_design_workflow.md](references/tower_design_workflow.md) in order. Do not skip directly from Aspen results to mechanical dimensions.

The complete chain applies to a complete tower-design request. A formula lookup,
pressure-drop check or geometry audit executes only its dependent segment and
reports that scope, without manufacturing a full mechanical-design assignment.

At minimum, freeze and propagate:

`feed/product targets -> thermodynamics and operating pressure -> stage/reflux/duty basis -> internal type -> traffic envelope -> diameter -> downcomer/receiving/inactive areas -> active area -> hole or packing geometry -> pressure drop and entrainment/weeping/flooding -> section/load-case performance envelopes and plots -> tray spacing/tower height -> shell/nozzles/supports -> mass/material/cost basis -> drawings/specification/report`

When an upstream value changes, use the dependency ledger in the workflow reference to identify and recalculate every downstream consumer. A drawing is not accepted if it still depicts superseded geometry.

Only for an F1 float-valve load-performance boundary task, read
[references/f1_load_performance_intake.md](references/f1_load_performance_intake.md).
Its deterministic utility checks source-bound supplied curves and connected
operating intervals; it does not supply empirical defaults, load third-party
neural weights, or certify formal F1 sizing. Do not load it for unrelated towers.

## Write calculations as coherent equation chains

Use one target label at the start of a chain:

`target = symbolic formula = substituted calculation = result with unit`

Do not prefix every intermediate number with a new target label. Reuse a previously calculated value by equation or table reference instead of repeating its derivation. Keep units visible at substitution and result boundaries, and state basis changes explicitly.

## Treat figures as engineering evidence

Use dimensioned engineering linework for tray layouts, section views, internals, and nozzle arrangements. Keep data plots unchanged unless the plotted data or method changed. Avoid decorative text boxes, cartoon styling, redundant legends, and unattached dimensions. Every drawing dimension must agree with the latest calculation ledger.

Project-specific construction details are not universal defaults. For example, end flats on a serrated weir or left/right downcomer orientation must come from the active design authority or drawing requirement, not from this skill.

## Completion gates

Do not call the tower complete until all gates pass:

- source ledger and evidence classification are complete;
- formulas, substitutions, units, and conclusions are reproducible;
- active, downcomer, receiving, and inactive areas close geometrically;
- hydraulic checks use the same traffic and geometry basis;
- every section and governing load case has a refreshed load-performance envelope/plot after geometry or traffic changes;
- pressure-drop feedback is reconciled with the process model;
- mechanical dimensions and drawings match the accepted calculation set;
- mass, material, selected size, and any course-design/correlation cost estimate are refreshed or explicitly marked vendor-boundary;
- standards/software/vendor boundaries are explicit;
- retrieval evidence includes source PDF, hash, page, bounding box, and asset path;
- an independent reviewer rechecks the dependency graph and high-risk assumptions.

Record unresolved or low-confidence OCR/table cells as review items; never silently promote them to formal design values.

阶段收尾若发现有证据且值得复用的新方法或原则，将候选交主助手，按
[主动经验提醒](../chemical-engineering-expert/references/EXPERIENCE_INBOX.md#主动提醒使用者)
展示可审阅摘要并推进确认/投稿；拒绝不催促，已有有效授权不重复询问。
