# Governed Chemical Knowledge and Skill Distillation

This workspace performs **behavioral/knowledge distillation into an Agent
Skill**, not neural-network weight distillation. It converts source-backed
methods, expert checks, tool traces, and verified corrections into compact
instructions, references, deterministic scripts, retrieval metadata, and
evaluations. It cannot inspect or retrain the base model’s hidden weights.

## 1. What may be distilled

Classify the target before intake.

| Target | Treatment |
| --- | --- |
| Physical invariant or deterministic identity | May be promoted after exact definition, basis, and verification |
| General engineering review mechanism | May be independently restated and promoted after cross-source/forward testing |
| Heuristic or correlation | Keep scope, source, units, range, uncertainty, and counterexamples; usually `J` or `X` |
| Standard/manual/software rule | Preserve edition/version, exact anchor, and applicability; never paraphrase away a condition |
| Project value or same-case result | Keep in project authority/result ledgers, not the global expert skill |
| Example value, persona claim, model memory, or unsupported “industry norm” | Quarantine; it may suggest a search term but cannot become fact |
| User behavioral correction | Add atomically to error memory as `verified_by_user` |
| User technical correction | Keep candidate until a source, calculation, same-case test/software result, or supplied authority verifies it |

The useful target is usually “how to decide, detect, verify, and stop”, not the
answer from one case.

## 2. End-to-end pipeline

For canonical task-derived promotion follow `EVOLUTION_LOOP.md`: require
user-requested consolidation and explicit current-revision closure, then choose
prompt_principle or data_pattern. During-task logging and optimization continue.
Authorized temporary submission follows [EXPERIENCE_INBOX.md](EXPERIENCE_INBOX.md)
and does not start canonical learning, default retrieval or Skill reorganization.
Directly requested source ingestion or mechanism maintenance remains its own
authorized task; it cannot be used to disguise premature experience learning.

### Stage 0 — Freeze the intake contract

First apply `STRICT_ACCEPTANCE_AND_LEARNING.md` and run the lineage-aware
eligibility check. Any applied case relaxation anywhere in the ancestry
permanently excludes that artifact family from this pipeline, including
summaries, examples, reflections and negative/error-memory candidates. Keep
only project audit records; renaming or strict rerunning the same inherited
artifact cannot erase its origin. This prohibition is independent of whether
the user accepted that local deliverable.

Record:

- intended capability and trigger;
- source types and allowed licenses;
- project/domain/version scope;
- facts or values forbidden from transfer;
- required deterministic and semantic evaluations;
- human approval and rollback owner.

### Stage 1 — Immutable source layer

For every source retain:

`source_id, title, author/owner, URL/path, version/commit/date, license,
file_hash, page/line/section anchor, parser/OCR status, access date`

Do not replace original text with a summary. OCR, extraction, embeddings, and
LLM notes are derived artifacts and must point back to the immutable source.

### Stage 2 — Atomic claim ledger

Extract one claim per entry:

`claim -> exact source anchor -> evidence class -> units/basis ->
applicability -> exclusions -> conflicts -> derivations -> validation -> status`

Split a paragraph when its clauses have different evidence or scopes. Mark
negation, exceptions, equations, definitions, software versions, and standard
editions explicitly. A bibliography entry alone does not support a claim.

### Stage 3 — Candidate knowledge graph

Represent useful links without turning graph adjacency into truth:

- `supports`, `contradicts`, `defines`, `derives_from`;
- `requires_input`, `valid_for`, `invalid_for`;
- `implements`, `verified_by`, `supersedes`;
- `belongs_to_project`, `belongs_to_equipment`, `belongs_to_version`.

Nodes retain claim/source IDs. Graph expansion is a retrieval aid; every
returned claim still carries its own evidence and scope.

### Stage 4 — Hybrid vector/lexical index

A vector knowledge base is useful for finding semantically related passages,
synonyms, old terminology, and cross-file links. It is not an authority layer.

Index chunks with metadata at least for:

`source_id, path, heading, claim_ids, source_type, source_group, project_scope,
equipment_scope, software_version, knowledge_role, status, priority,
date/version, license, units/basis, hash`

Retrieve in this order:

1. normalize terminology, units, equipment tags, and user intent;
2. apply hard project/equipment/version/license/status filters;
3. combine lexical/BM25-style and vector similarity candidates;
4. add explicitly connected graph nodes;
5. rerank for active authority, verified memory, domain route, source quality,
   and exact-term matches;
6. return the original anchor and metadata, not a free-floating summary;
7. separate `A/R/D/J/X/U/F` before using the hit.

Similarity and graph proximity may never bypass a hard scope filter. Candidate
or historical material must not outrank current authority merely because its
wording resembles the query.

### Stage 5 — Generate a bounded candidate patch

Write only to `NEW_KNOWLEDGE.md`, an isolated candidate branch/directory, or a
reviewable patch. Keep:

- `SKILL.md` concise and procedural;
- detailed sources and domain reasoning in `references/`;
- repeatable deterministic checks in `scripts/`;
- output templates/assets only when they reduce repeated work.

Do not let a summarizer, memory daemon, or reflection agent write directly to
the canonical skill or error memory.

### Stage 6 — Chemical-engineering verification

Verification must match the claim class. Depending on scope, check:

- dimensions, units, reference state, time and mass/molar bases;
- algebra, stoichiometry, component/element/energy closure, physical bounds;
- phase behavior and property-method applicability;
- correlation range and required empirical parameters;
- reactor, separation, heat-transfer, fluid, equipment, material, control,
  safety, environmental, and legal boundaries;
- current standard/manual/software version;
- same-case simulator/export, experiment, inspection, vendor result, or
  independently reproduced calculation.

An LLM score, self-consistency, schema validation, or successful tool call is
not a chemical truth oracle.

### Stage 7 — Fresh-context evaluation

Freeze hidden cases before candidate generation. Compare at least:

- no skill/baseline;
- current canonical skill;
- candidate skill.

Use fresh agents that do not see the expected answer or generation history.
Test:

- known-answer calculations and unit/basis traps;
- missing-but-derivable information;
- insufficient empirical data and correct minimum-gap diagnosis;
- wrong-scope similar cases and outdated versions;
- converged-but-physically-wrong simulations;
- irrational flowsheet ordering, recycles without purge, missing terminal
  streams, impossible heat/pressure paths, and high-grade utility misuse;
- reasonable alternative designs where one rigid sequence must not be forced;
- trigger and negative-trigger behavior.

Score hard violations separately from style. Repeat stochastic cases and
record variance. The candidate must improve held-out performance without a
critical regression.

### Stage 8 — Promotion ratchet

Promote only when:

1. provenance, license, scope, units, conflicts, and status are complete;
2. technical claims have an appropriate non-LLM oracle;
3. held-out evaluation strictly improves or fills a demonstrated gap;
4. no critical physics, authority, safety, or scope-isolation regression occurs;
5. the change is minimal and has a named canonical owner;
6. a human approves material technical rules.

All six conditions are necessary, not overrides of relaxation exclusion.
Unknown or incomplete provenance fails eligibility before candidate generation;
old `accepted/verified` labels do not substitute for current strict evidence.

Record file hashes, evaluation results, change notes, and a recoverable prior
snapshot. Reject or revert a candidate that does not improve the gate.

### Stage 9 — Runtime learning

- User corrections update the live task and project incident first; canonical
  atomic memory updates wait for user-requested consolidation and task closure.
- Report delivery scope and remaining work. Follow EVOLUTION_LOOP.md for an
  unresolved closure needed by user-requested formal promotion; do not repeat
  confirmed or pending requests or infer closure from assistant completion.
- Repeated root causes raise retrieval priority, not factual authority.
- New external material remains candidate until the full gate passes.
- Superseded entries remain traceable; do not silently erase history.

## 3. Public projects and the part worth borrowing

No reviewed project supplies the complete chemical-engineering pipeline.

| Project | Useful mechanism | Boundary |
| --- | --- | --- |
| [Agent Skills specification](https://agentskills.io/specification) and [evaluation guide](https://agentskills.io/skill-creation/evaluating-skills) | Portable `SKILL.md` structure, progressive disclosure, fresh-context and baseline evaluation | Format/behavior evaluation does not verify chemical facts |
| [OpenAI Codex skills/plugins](https://developers.openai.com/codex/codex-manual.md) | Concise trigger metadata, on-demand references/scripts, installable plugin boundary | Packaging is not domain validation |
| [Paper-Distiller](https://github.com/YihanJIANG-lab/Paper-Distiller) | Paper/PDF ingestion and structured research notes | Intake front end; summaries need source anchors and independent validation |
| [Corpus2Skill](https://github.com/dukesun99/Corpus2Skill) | Hierarchical navigation while retaining original corpus retrieval | Work in progress and no verified license found during review; do not copy code/text |
| [MemSearch](https://github.com/zilliztech/memsearch) | Experience-to-skill candidates, Git history, explicit human installation | Transcript-derived candidates are not facts |
| [Acontext](https://github.com/memodb-io/Acontext) | Route remembered experience into skills | Automatic write-back is unsafe for canonical engineering rules |
| [Armory](https://github.com/Mathews-Tom/armory) / [CoEvoSkills](https://github.com/Zhang-Henry/CoEvoSkills) | Separate generator history from a surrogate verifier | Skill-derived assertions and LLM judges are not independent chemical truth |
| [Microsoft SkillOpt](https://github.com/microsoft/SkillOpt) | Bounded edits, rejected-edit memory, held-out strict-improvement acceptance | Depends on a trustworthy evaluation oracle |
| [colleague-skill](https://github.com/titanwings/colleague-skill/tree/dot-skill) / [Nuwa](https://github.com/alchaincyf/nuwa-skill) | Conflicts/gaps, known-answer and boundary/voice tests | Suited to behavior/style fidelity, not engineering fact verification |
| [Memento-Skills](https://github.com/Memento-Teams/Memento-Skills) / [Hermes Agent](https://github.com/NousResearch/hermes-agent) | Execution-reflection candidates and restoration concepts | Self-modification can pollute a skill; canonical writes must be gated |

The resulting local composition is:

`source-preserving intake -> atomic claim ledger -> hard-scoped hybrid retrieval
-> candidate patch -> chemical hard checks -> blind held-out comparison ->
human promotion -> hash/rollback`

## 4. OpenAI/GitHub packaging boundary

Follow progressive disclosure:

- `AGENTS.md`: short, always-on repository invariants and routing;
- `SKILL.md`: reusable chemical-expert workflow and when to load references;
- `references/`: macro quality, sources, memories, domain details, and audits;
- `scripts/`: deterministic validators, retrieval, and repeatable calculations;
- plugin: distribution wrapper with `.codex-plugin/plugin.json` and `skills/`;
- Git/history or lock manifest: review, hashes, provenance, and rollback;
- MCP/connectors: live external tools/data only when needed, never a substitute
  for authority or same-case verification.

The canonical workspace skill is edited first. Installed and plugin mirrors are
generated from it and must match by relative-path SHA256 manifests.

## 5. Failure conditions

Quarantine the candidate when any of these occurs:

- missing source, license, version, exact anchor, units, basis, or scope;
- a summary is treated as the original source;
- a vector hit or model agreement is treated as evidence;
- one case’s values become a global default;
- technical truth is judged only by the model that generated it;
- the same examples are used both to generate and to “blindly” validate;
- a new rule increases false triggering or project-scope leakage;
- a behavioral improvement hides a physics, safety, or authority regression;
- canonical files are changed without a candidate record, evaluation, and
  rollback path.
