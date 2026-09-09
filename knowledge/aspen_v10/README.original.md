<!-- generated: aspen_user_guide_v10 -->
# Aspen Plus V10 User Guide Knowledge Graph

This graph is built from the local PDF source:

`source/source_user_manual.pdf`

Source SHA256: `90ABE362DCAA88DF776A9BD9204A40FC101AE47DB506438C4BD648A50FF37A27`

PDF pages: 571

## Purpose

The graph splits the Aspen Plus 10 user guide by PDF outline chapter and connects each chapter to the `aspen-plus-operations` operation graph.

It is a chapter-level operation/navigation graph. It does not replace:

- the project source/change-offset ledgers that decide project values;
- the operation skill's V14 help-backed `manual_knowledge_graph.json` for fragile card field rules;
- the Sun Lanyi textbook graph for lecture/case patterns.

## V14 Operation Preservation Guard

Do not overwrite, regenerate, or merge into the Aspen Plus V14 operation manual
graph:

`{CHEM_SKILLS}/aspen-plus-operations/references/manual_knowledge_graph.json`

This V10 graph may only be used as workflow/UI/detail-operation retrieval
support. V14 card-field rules remain authoritative for low-level Aspen card
mechanics.

## Entry Order

1. `knowledge_graph/00_ERROR_MEMORY.md`
2. `knowledge_graph/unknowns_router.md`
3. `knowledge_graph/user_guide_operation_router.md`
4. `knowledge_graph/user_guide_index.md`
5. `knowledge_graph/operation_detail_index.md`
6. `knowledge_graph/chapter_detail_indexes/UG10-CHxx_details.md`
7. `knowledge_graph/chapter_nodes/UG10-CHxx_*.md`
8. `chapter_extracts/chxx_*.md` only when source text is needed

Read `knowledge_graph/NEW_KNOWLEDGE.md` only for recent candidate or validated
items that have not yet been promoted by this builder.

## Query

```text
python aspen_user_guide_v10_knowledge/scripts/query_user_guide_knowledge.py <terms>
python aspen_user_guide_v10_knowledge/scripts/query_user_guide_knowledge.py <terms> --ids
python aspen_user_guide_v10_knowledge/scripts/query_user_guide_knowledge.py <terms> --json
python aspen_user_guide_v10_knowledge/scripts/query_user_guide_knowledge.py <terms> --scope details
```

## Vector Search

Local graph-only vector index:

```text
python aspen_user_guide_v10_knowledge/scripts/vectorize_user_guide_graph.py
python aspen_user_guide_v10_knowledge/scripts/query_user_guide_vectors.py <terms>
```

Workspace-wide graph and skill-chain vector index:

```text
python scripts/vectorize_workspace_knowledge.py
python scripts/query_workspace_vectors.py <terms>
```

## Non-Duplication Choices

- No page-level text extracts are generated.
- Each PDF outline entry becomes exactly one source extract and one graph node.
- Detail operation indexes are generated as searchable pointers and short operation records.
- Existing operation-skill manual graph files are linked, not copied.
- Rebuilds overwrite only files marked with the generated marker.

## Coverage

Generated chapter nodes: 39

Searchable detail records: 6986
