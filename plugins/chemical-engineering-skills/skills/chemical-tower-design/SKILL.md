---
name: chemical-tower-design
description: Evidence-driven workflow for designing, recalculating, auditing, and documenting chemical tray or packed columns. Use for tower process sizing, tray/packing hydraulics, column geometry, internals, mechanical handoff, standards lookup, engineering drawings, dependency propagation, formula-chain cleanup, or independent tower-design review from PDF/DOCX/project data.
---

# Chemical Tower Design

Use this skill to produce a traceable tower design whose process basis, hydraulic geometry, mechanical envelope, figures, and report equations remain mutually consistent.

Read [references/ERROR_MEMORY.md](references/ERROR_MEMORY.md) before the ordinary workflow. Read [references/NEW_KNOWLEDGE.md](references/NEW_KNOWLEDGE.md) when recent candidate knowledge may affect the active design.

For acceptance or learning, follow the central chemical-expert
`references/STRICT_ACCEPTANCE_AND_LEARNING.md`: current-stage strict evidence
is default; a user-approved case relaxation does not update shared rules or
enter learning/default retrieval, including through descendants.

## Start with authority and retrieval

1. Open the workspace knowledge-graph link map and the top-level `设备设计图谱与脚本` entry before changing a design. This skill consumes the equipment graph, standards evidence subgraph, and deterministic scripts; it does not contain or supersede them.
2. When tower inputs come from Aspen, first run the top-level deterministic `aspen_equipment_derivation.py` so every process-side parameter keeps its stream/block field, unit conversion, export hash, clean-run gate, and equation chain; then consume its embedded `equipment_design_match.py` result. For already-canonical tower parameters, run `equipment_design_match.py` directly. Treat the deterministic equipment-family, formula-route, standard-route, and model-status output as the primary match; use this skill only to audit and execute the tower workflow.
3. If several tray/packing/structural branches remain feasible, retain the most general tower family/type and candidate set until their required inputs close one branch; do not select a specialized internal merely by score or convention.
4. Freeze project inputs, approved deviations, software outputs, and unresolved values in a source ledger.
5. Query the standards source layer with `scripts/query_tower_sources.py`; do not browse folders manually when the script can retrieve the evidence.
6. Classify every retrieved source as `direct_reuse`, `method_only`, `software_boundary`, `vendor_boundary`, or `forbidden_transfer` before using it.
7. Never copy example geometry, vendor capacity, stream data, or another equipment tag's values into the active tower.

Read [references/evidence_routing.md](references/evidence_routing.md) whenever authority is incomplete or sources disagree. Read [references/query_contract.md](references/query_contract.md) before running standards queries.

## Execute the design chain

Follow [references/tower_design_workflow.md](references/tower_design_workflow.md) in order. Do not skip directly from Aspen results to mechanical dimensions.

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
