---
name: chemical-equipment-selection-audit
description: Audit and script chemical equipment design/selection calculations from DOCX/PDF/project reports, building a document-led equipment knowledge graph with formula families, parameter sources, manual decision gates, and evidence boundaries. Use when the user asks to read equipment selection reports, split modules, verify formulas, script calculations, classify Aspen/EDR/SW6/vendor/manual parameters, generalize calculation templates, or turn equipment-selection work into reusable knowledge/skills.
---

# Chemical Equipment Selection Audit

## 工作过程

从当前设备说明书和同案流程导出开始，先确认每台设备的用途、位号、介质和最新数据，再把报告中的公式、输入、单位与结果拆成可复算的账本。通过本产品设备计算入口执行可闭合的推导，查询适用方法和标准事实，随后逐项比较脚本、原文和软件证据；出现差异先查提取、单位、公式适用性和旧模板污染，不靠改容差消除问题。

能够判定的错误直接给出纠正及依据，确需EDR、SW6、塔内件或厂家证据的结论留在相应边界。设计值变化时按[阶段调用规则](../chemical-engineering-expert/references/DESIGN_STAGE_ROUTING.md)交回工艺与设备负责人复核影响，再更新报告、图表和设备清单。最后交付逐项计算及正文级修改情况，不用章节提纲冒充完整报告。

## Product Retrieval And Optional Local Sources

Resolve this product's runtime through `LOCAL_KNOWLEDGE_GRAPH_LINKS.md`.
Use its `tools/expert_cli.py` search/equipment/feedback entry for the bundled
knowledge, equipment rules and structured standards facts. Read
`equipment-design-app` for the actual backend contracts. Private project
overlays and textbook/standard source pages are optional user-supplied sources;
their absence does not mean the bundled calculation backend is absent.

The vector index is retrieval support only. It does not replace source
documents, calculation ledgers, software/vendor evidence or decision gates.

## Quick Start

1. Read the project instructions and source documents first. Current project documents outrank templates and historical examples.
2. When same-case Aspen exports are available, invoke the bundled equipment derivation/matching route through `equipment-design-app`. Preserve raw fields, explicit units, equations, export hash and run evidence. Canonical parameters may enter the registered deterministic matcher directly. Actual live Aspen import is separately authorized and licensed; missing COM does not block manual/exported-parameter calculations. Report genuinely missing source or formal evidence locally without inventing a private catalog.
3. Run a route/component/template-contamination scan before writing equipment roles, media, products, materials, or process names. If current project Aspen/components/reactions do not support a copied chemistry, solvent, product purity, material, or route, quarantine it as wrong even when it appears in an old handoff or generated draft.
4. Build an equipment map: equipment family, tag, source document, role, reusable methods, forbidden value transfers.
5. Build a calculation ledger: formula, inputs, units, source location, script value, document value, tolerance, reliability class, status, note.
6. If design standards, manuals, textbooks, or course-design examples are added, classify them as direct reuse, method only, software boundary, vendor boundary, or forbidden transfer before changing any parameter.
7. Separate what the script can prove from what needs external evidence: Aspen/EDR/SW6/Column Internals/vendor/literature.
8. When values do not match, perform root-cause audit before changing formulas, inputs, or tolerances.
9. For kinetic reactors, stop at the project kinetics gate; do not present k/E/Aspen card values as formal without a freeze chain.
10. Before claiming section-by-section completion, verify target-document page/paragraph coverage and chapter numbering. A chapter skeleton or prompt table is not a正文-level redline; if coverage is missing, label it as prompt-level or boundary-level.

## Core Rule

The deterministic matcher must choose the equipment family, formula route, standard path, and evidence/model status from versioned rules without an LLM or network. The model and human reviewer audit the result; they do not silently replace it. A genuine authority decision may approve a machine-blocked branch only by updating the project ledger/rules with explicit evidence, never by free-text model judgment. Methods may migrate across similar equipment; stream data, geometry, kinetics, software outputs, and vendor values may not migrate automatically.

When several subtypes, formula branches, or vendor/standard candidates remain feasible, retain the most general common family/type and the candidate set. Do not use score, habit, or model preference to select a specialized branch; only a physical or cross-family contradiction should block the parent match.

Aspen-derived parameters are process-basis evidence only when the run-status counts are reproduced from a separately hashed `aspen-run-status-evidence-v1` artifact. They do not set design pressure/temperature, material, corrosion allowance, mechanical thickness, internals, or vendor models. `final_model` additionally requires a gate-to-artifact `equipment-evidence-manifest-v1` plus a separately hashed `equipment-audit-approval-v1`; a manifest's self-declaration alone is not approval.

Generated drafts and previous handoffs are evidence candidates, not authority. Treat them as contaminated until revalidated against current project source documents and the accepted Aspen export. Preserve methods and structure when useful, but do not preserve chemistry, stream IDs, products, purities, materials, or software conclusions unless the current project source ledger independently supports them.

## Workflow

### 1. Evidence Ingest

- Copy source files into a project work package.
- Extract DOCX/PDF tables and outline evidence.
- If current-project Aspen artifacts are present (`.inp`, `.bkp`, `.apw`,
  `.apwz`, COM/CSV exports, stream tables, block ledgers, or JSON extracts),
  parse the accepted or priority Aspen flow before writing placeholders or
  asking the user for data. Build a flow ledger covering components, reactions,
  block IDs/types, feeds/products, stream IDs, stream T/P/flow/phase values, and
  card parameters. If multiple Aspen files conflict, apply the project's stated
  priority rule first and record the losing file as a conflict branch.
- Assign stable document IDs.
- Keep raw extracted tables available for re-checking.

### 2. Equipment Graph

Create nodes for:

- Equipment families: tower, exchanger, fixed-bed reactor, separator, pump, compressor, storage, membrane, mixer.
- Tags: the exact identifiers from the current equipment ledger.
- Formula families: nozzle velocity, design pressure, wall thickness, tower holdup, stream balance, heat transfer, Ergun, Arrhenius audit.
- Parameter sources: Aspen, document table, literature, standard, software export, vendor, manual default.
- Standard-source subtypes: direct reuse, method only, software boundary, vendor boundary, forbidden transfer.
- Evidence classes: A/B/C/D/E.

### 3. Manual Decision Gates

Before calculating, decide:

- Same equipment or only same family?
- Same current project route/component system, or copied template language?
- Which formula family applies?
- Which parameters are Aspen/literature/standard/manual/software/vendor?
- Does the result prove formal design, or only pre-selection arithmetic?
- Which software or vendor evidence is still required?
- Is a cited standard a verified table value, a method source, a software/vendor boundary, or a forbidden example value?

Before writing or redlining a report, add a discard ledger for old assumptions: wrong route names, unsupported solvents/products, copied product purities, stream IDs used as materials, old Aspen values superseded by the accepted export, and software/vendor pass claims without same-equipment evidence.

Before continuing a partially written equipment report, run an Aspen-flow
availability check. Any process fact that can be extracted from the accepted
Aspen artifact is `AI可自取`, including route/component identity, RadFrac/RPlug/
Heater/Pump/Compressor/Flash/Mixer block membership, stream roles, feed/product
connections, stage/feed-location cards, pressure/temperature cards, and exported
stream values. Do not replace these with generic placeholders, inherited
template language, or a request for the user to supply them. Only external
software/vendor/formal-kinetics evidence remains outside this self-extraction
gate.

Before completing a multi-chapter handoff, verify every chapter/family against the current target document and equipment ledger. Do not inherit another project's chapter numbering; correct mismatched mappings explicitly.

### 4. Scripted Audit

Use deterministic scripts for repeatable arithmetic and table checks. For every row, store source location, formula, inputs, output, document comparator, tolerance, pass/fail, reliability, and a note.

### 5. Mismatch Audit

If a row fails:

1. Re-read original source cells, not just extracted CSV.
2. Check units and dimensions.
3. Recalculate with an independent small case.
4. Cross-check nearby tables and supplemental documents.
5. Check whether the mismatch is actually template contamination or an old generated-handoff assumption.
6. Classify root cause: formula, unit, extraction, source-table label, manual assumption, template contamination, old-handoff contamination, or missing external evidence.
7. If a decisive conflict ruling is possible, write the corrected value and mark the old value wrong. Keep `review` only for evidence-boundary items that cannot enter formal正文 as correct values.

## Redline/Completion Output Gate

When the user asks to correct or complete a report, deliver a concise handoff table before any generated prose is treated as final:

- change summary first;
- data-source reliability table with exact paths;
- discarded-old-assumptions table;
- page/paragraph-level "where wrong, why wrong, how to fix" table;
- text/extraction/calculation/Aspen comparison table;
- expert-system result with only decisive `correct/wrong/boundary` labels;
- minimum generation prompts for each section, including exact values and禁写项.
- a completion-state column for each section: `正文级已修改`, `提示词级补全`, or `边界/待补证`; prompt-level coverage must not masquerade as completed Word redline work.

Correct values may enter正文 only when either two-sided evidence agrees or the conflict has been explicitly decided. Unsupported software/vendor/kinetic claims must be cleared or moved to an input/boundary table.

## Placeholder Completion Rule

When the user allows missing equipment content to be occupied with placeholders, do not leave a blank table, chapter skeleton, or generic "待确认" note. Write readable正文-level placeholder text directly under the relevant subsection and mark it as redline/new content in the target artifact. Each placeholder must state:

- what the section should eventually contain;
- which current values are only `目录级`, `筛错级`, or `边界/待补证`;
- exactly what the user or next AI must provide, such as Aspen stream/property exports, SW6/EDR/Column Internals reports, vendor curves, membrane literature, pump NPSHr, compressor MW/k/Z/efficiency, storage days, or liquid-level assumptions;
- which conclusion is wrong until evidence exists, using decisive labels such as `不能判为通过`, `清空原结论`, or `证据边界`.

If an external AI will continue the work, add a minimum generation prompt for every incomplete subsection. The prompt must include the allowed facts, forbidden template language, required input fields, and the proof boundary. Missing evidence should be written as a concrete supply request, not as a vague request for the reader to check.
Before asking the user for data, split responsibility into `AI可自取`, `需外部软件/厂家证据`, and `需用户决策`. Any value available from the current project folder, accepted Aspen exports, APW files, extracted tables, ledgers, or deterministic scripts must be assigned to `AI可自取`, not pushed back to the user.
If the user points out that an Aspen process flow already exists, immediately
stop placeholder drafting, extract or reuse the project-local Aspen flow ledger,
and revise the正文 with exact Aspen-backed flow/block/stream facts. Keep
unsupported EDR/SW6/Column Internals/vendor/formal-kinetics conclusions as
`边界` or `禁写`; do not let those boundaries erase Aspen facts that were
locally extractable.

## Experience Selection Supplement Rule

When the user asks to “按经验把选型做了”, “能算的尽量算”, or “按照脚本”, do not answer with generic selection advice. Build a deterministic enhancement ledger first, then write it into the target artifact if requested.

Required behavior:

- Treat current-project Aspen/document/script artifacts as the only project-fact source. Reference reports from another chemistry may supply only chapter shape or method vocabulary; their route, media, product names, materials, equipment values, and software conclusions are `forbidden_transfer`.
- Separate Aspen block IDs from document catalog equipment tags. Resolve identity from current evidence and actual Aspen block type, not letter prefixes or similar names; a compressor may have a pump-like label.
- Compute every closed screening item available from scripts or accepted Aspen data before writing正文:
  - separator mass balance, design-pressure factor, Souders-Brown required `K`, superficial/nozzle velocities;
  - compressor pressure ratios and high-ratio flags;
  - storage/vessel geometric volume ratio and impossible `V_nominal > V_geo` cases;
  - membrane geometric area;
  - pump reverse-density screening and Aspen pump hydraulic-power screening when stream volume flow and pressure rise are available.
- Label each result decisively as `对`, `错`, or `边界`. Use `对（筛查）` or `对（预选）` only when the arithmetic or Aspen fact is closed but formal vendor/software evidence is still missing. Use `错` for physically impossible or clearly conflicting combinations. Use `边界` for missing EDR/SW6/Column Internals/vendor/NPSH/formal-kinetics proof.
- Write wrong values as redline corrections or clear them from formal正文. Do not leave the reader to decide which value is right when a script/Aspen conflict ruling is possible.
- Produce a machine-readable JSON/CSV or Markdown enhancement table with parameter, formula, inputs or source, calculated value, text value when available, judgement, and正文 action. If a Word/PDF deliverable is produced, render it and visually inspect the pages containing the dense tables.

## Reliability Classes

- A: formula reproduced from explicit inputs and document value.
- B: reproduced to pre-selection or rounded/software boundary step.
- C: requires EDR/SW6/Column Internals or equivalent software evidence.
- D: kinetics provisional; needs source equation to Aspen exported-card freeze chain.
- E: symbolic/catalog selection; needs vendor/standard/Aspen support.

## Optional Project Knowledge Graph

Use this product's link map to locate its bundled equipment graph and query
interface. Route through family, parameter-source, evidence-boundary and
mismatch-audit nodes. A user's private overlay can add current-project evidence,
but is not a prerequisite for the bundled methods and structured standards facts.

Read a source-backed standards crosswalk before reclassifying parameters from
manuals, textbooks or course examples; unavailable source data stays an
explicit dependency, not a fabricated packaged capability.

## References

See `REFERENCE.md` for formula families, ledger schema, and report outputs.

## Final Artifact Hygiene Gate

When the task ends in a user-facing Word or Markdown deliverable, treat the
artifact itself as another audit target.

- After any edit to the final deliverable, rerender the current artifact and
  inspect the pages affected by the edit plus at least one page before and
  after. Do not rely on stale PNG/PDF renders as proof for a newly edited
  document.
- Scan final prose for internal workflow labels such as `family_*`,
  `AI可自取`, `forbidden_transfer`, `prompt-level`, placeholder labels, or
  similar routing terms. Replace them with reader-facing language or remove
  them before delivery.
- Scan for encoding corruption, mojibake, replacement characters, half-broken
  HTML/Markdown tags, or terminal-copy artifacts. A numerically correct
  document with visibly corrupted text is not complete.
- If the render toolchain fails because LibreOffice/`soffice` is unavailable,
  use the project-local fallback renderer, record that fallback explicitly, and
  keep the new render output tied to the current deliverable version.

## Script Double-Check Rule

If a value is calculable by script, it must not enter formal prose from a
single computation alone.

- Close the value with two-sided evidence: script plus an independent formula,
  unit-conversion replay, second script path, or raw-source recomputation.
- If the two sides disagree and no decisive conflict ruling is possible, keep
  the value out of formal正文 and downgrade it to `boundary`, `input only`, or
  `needs evidence`.
- When a conflict ruling is possible, write the corrected value, mark the old
  value wrong, and record the root cause in the ledger or handoff artifact.
