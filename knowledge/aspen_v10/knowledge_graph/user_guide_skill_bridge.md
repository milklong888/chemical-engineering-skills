<!-- generated: aspen_user_guide_v10 -->
# Aspen Plus V10 User Guide Skill Bridge

This file connects the project-local Aspen Plus V10 user-guide graph to the `aspen-plus-operations` skill.

## Entry Points

- Index: `user_guide_index.md`
- Operation router: `user_guide_operation_router.md`
- Detail operation index: `operation_detail_index.md`
- Unknown router: `unknowns_router.md`
- Query script: `../scripts/query_user_guide_knowledge.py`
- Structured manifest: `../manifest.json`
- Search records: `operation_detail_records.json`

## Operation-Skill Use

Before a mechanical Aspen operation, keep value authority and card-mechanics authority separate:

- Project report, taskbook, change-offset table, and source-freeze ledgers decide project values.
- `aspen-plus-operations/references/manual_knowledge_graph.json` decides fragile card-field meanings where seeded.
- This V10 user-guide graph supplies chapter-level workflow, UI path, file/report/help/convergence/analysis/automation context.

Recommended note format:

```text
User-guide node(s): UG10-CHxx and/or UG10-CHxx-Dnnn
Operation graph node(s): case-io / block-stream / ...
Card manual node(s): reaction.powerlaw.overview / ...
Source value authority: <project ledger or blocked>
```

## Query Examples

```text
python aspen_user_guide_v10_knowledge/scripts/query_user_guide_knowledge.py convergence tear
python aspen_user_guide_v10_knowledge/scripts/query_user_guide_knowledge.py ActiveX COM --ids
python aspen_user_guide_v10_knowledge/scripts/query_user_guide_knowledge.py 物性 方法
```

## Non-Duplication Rule

Do not copy nodes from this graph into the operation skill's `manual_knowledge_graph.json` unless a recurring field-level card rule has been independently verified against current Aspen help/exported cards. For ordinary chapter and detailed-operation routing, link to `UG10-CHxx` or `UG10-CHxx-Dnnn` instead.

## Current Coverage

Chapter nodes generated: 39
