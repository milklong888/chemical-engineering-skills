# Vector Knowledge Base Design for Chemical Engineering

## Decision

A vector knowledge base is useful here, but only as a candidate-retrieval
layer. It must not choose the engineering method, transfer project values, or
promote evidence. The workspace already has an offline 768-dimensional index,
but it uses signed character/token n-gram hashing rather than a learned semantic
embedding. It is good at exact terminology and aliases; it is weak at semantic
paraphrase and previously allowed project-specific records to compete with
shared knowledge.

For the present corpus (about nine thousand chunks), search speed is not the
limiting problem. The priority order is:

1. hard metadata scope and authority filtering;
2. reliable chunk identity, provenance, supersession, and candidate state;
3. hybrid lexical plus semantic recall;
4. graph/authority reranking;
5. only then approximate-nearest-neighbor optimization.

## Retrieval architecture

```text
task contract and chemical trigger
  -> infer domain + explicit project/course scope
  -> hard metadata filter
  -> sparse/lexical retrieval || dense semantic retrieval
  -> rank fusion
  -> knowledge-graph neighbour expansion
  -> authority/evidence/status + highest-sufficient-layer rerank
  -> source opening and deterministic verification
  -> engineering answer
```

Similarity can nominate a source. It cannot turn `X`, `U`, `F`, a candidate,
an old case, or another equipment tag into current-project `A` or `R` evidence.

## Required metadata per chunk

- stable `asset_id`, `source_group`, `source_path`, `chunk_id`, and source hash;
- `authority_scope`: `shared`, `project_local`, `project_overlay`,
  `course_local`, or `historical_case`;
- `scope_keys`: project ID/root, course identity, equipment tag, case ID;
- `knowledge_role`: router, canonical reference, error memory, new knowledge,
  evolution history, template;
- `knowledge_layer`: L3 worldview/concept, L2 principle/mechanism, L1
  method/derivation, or L0 source detail;
- `knowledge_status`: active, verified, candidate, quarantined, superseded;
- evidence class `A/R/D/J/X/U/F` and factual authority owner;
- standard/software version, file SHA256, page/table/card where applicable;
- units, basis, phase, equipment tag, validity date, and `supersedes` relation;
- exact-file delivery hash for Aspen/EDR/SW6 results.

Fields used to prevent forbidden transfer are filters, not soft score bonuses.

## Current implementation

`scripts/vectorize_workspace_knowledge.py` and
`scripts/query_workspace_vectors.py` now record and enforce
`authority_scope/scope_keys`. Project-only document skills, project cost
batches, course material, project overlays, project-case nodes, selection
history, and evolution records are excluded unless the query or caller
explicitly activates their scope. Negative-scope cases are part of the
retrieval regression set.

The current deterministic hash index remains the release baseline because it
is offline, inspectable, and reproducible. It should be retained as the sparse
side of a future hybrid retriever.

For large scanned textbook/manual corpora, do not flatten every OCR page into
the workspace index. Store full L0 pages/chunks in a source-local FTS/trigram
evidence index with page/hash/quality metadata. Put only source-backed L3/L2/L1
retrieval cards in the global vector index, then descend to L0 after the upper
node selects the mechanism or method. High-level queries should boost L3/L2 and
penalize raw pages; formula/value/page queries should retain the governing
concept and explicitly open the L0 anchor. This is an abstraction hierarchy,
not a factual-authority hierarchy.

## Semantic ambiguity guard

Domain keywords are not sufficient when a term has multiple active meanings.
Route inference may apply explicit compound-phrase suppressors before scoring.
For example, `模型蒸馏`, `知识蒸馏`, and `Skill distillation` suppress the
distillation-column route while retaining the chemical-expert knowledge/Skill
governance guard. Explicit column context such as `精馏塔`, `RadFrac`, reflux,
condenser, or reboiler remains a tower task. A negative-route regression covers
this behavior and implements `CE-ERR-007` without changing factual authority.

## Dense-vector backend assessment

- Qdrant is the best fit if a local vector database is added: its JSON payload
  metadata supports boolean filters, and its query interface supports dense +
  sparse hybrid and multi-stage reranking. Those features match this workspace's
  authority/scope problem.
- FAISS is a strong local similarity-search library, but its native dynamic
  filtering is largely ID/subset oriented. It is suitable as a lightweight
  dense index only if hard metadata filtering is performed before search or
  separate indexes are built per scope.
- A database engine alone does not improve meaning. A Chinese/English
  chemistry-capable embedding model and a measured evaluation set are required.

Official references:

- Qdrant payload/filtering: <https://qdrant.tech/documentation/concepts/payload/>
- Qdrant hybrid/multi-stage queries:
  <https://qdrant.tech/documentation/search/hybrid-queries/>
- FAISS project and filtering limitations:
  <https://github.com/facebookresearch/faiss> and
  <https://github.com/facebookresearch/faiss/wiki/FAQ>

## Migration gate

Do not replace the current index merely because a dense model appears more
advanced. Build a shadow index and compare it on:

- paraphrase recall in Chinese/English chemical terminology;
- exact card/standard/equipment-tag retrieval;
- method-lock and correction-memory retrieval;
- project/course/historical negative-scope leakage;
- candidate/superseded demotion;
- top-k recall, reciprocal rank, false-authority rate, latency, and rebuild
  reproducibility.

Promote a dense or Qdrant backend only if it improves the semantic cases while
passing every authority and negative-scope gate. Keep source text and metadata
outside the embedding so the index can be rebuilt and audited.
