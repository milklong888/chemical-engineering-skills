# Examples

## Example 1: Read an equipment selection report

User asks: `阅读这个设备选型说明书，拆模块，告诉我每块做什么，哪些能脚本化。`

Workflow:

1. Extract tables and outline evidence.
2. Build equipment family/tag map.
3. Classify modules into calculation, software evidence, vendor/catalog, and manual defaults.
4. Script only explicit formulas or table conditions.
5. Report Aspen/EDR/SW6/vendor parameters still required.

## Example 2: Formula mismatch

User asks: `对不上就要好好审查，是公式问题还是什么。`

Workflow:

1. Locate failed calculation ledger rows.
2. Re-read source DOCX/PDF cells.
3. Recompute formula independently.
4. Check units and nearby tables.
5. Cross-check supplementary documents.
6. Produce root-cause report.

## Example 3: Generalize to new equipment

User asks: `稍微有的泛化能力也是要的，最终还是要人工决定怎么计算。`

Workflow:

1. Identify equipment family and tag.
2. Choose formula family manually.
3. Declare parameter source and default values.
4. Run script audit.
5. Keep external evidence boundaries explicit.

## Example 4: Build a reusable skill/graph

User asks: `搞成知识图谱再整理成设备skill。`

Workflow:

1. Create project `knowledge_graph/` with README, router, equipment nodes, formula nodes, source nodes, evidence boundaries, manual gates, mismatch playbook.
2. Create user skill with `SKILL.md`, `REFERENCE.md`, and examples.
3. Link the project knowledge graph as a project-specific instance.
4. Verify the skill description contains trigger phrases.

## Example 5: Integrate design standards

User asks: `设计标准里新增了反应器、塔、换热器、容器标准，看看关键参数能不能复用。`

Workflow:

1. Split standards by equipment family and create source nodes.
2. Classify each source as direct reuse, method only, software boundary, vendor boundary, or forbidden transfer.
3. Compare only current-report key parameters with standards objectively.
4. Keep matching report values unchanged; if evidence is incomplete, mark method/boundary/review instead of changing values.
5. Connect the standards graph to parameter-source nodes, manual gates, evidence boundaries, and mismatch audit.
