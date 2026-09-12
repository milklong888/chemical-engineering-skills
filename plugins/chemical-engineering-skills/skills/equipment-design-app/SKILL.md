---
name: equipment-design-app
description: Run the bundled headless equipment-design backend for parameter derivation, family and type selection, standards lookup, optional isolated Aspen import, deterministic replay and evidence-bound feedback into process design. Preserve original formula and rule provenance; GUI software is not required.
---

# Equipment Calculation and Selection

## 工作过程

接到同案流程导出或人工参数后，先发现设备族和字段合同，将数值、单位、来源与设备位号对齐，再让本地程序完成所有输入已齐的公式链。程序据此形成参数包、进行适用性检查并给出有条件的设备型式或候选；缺少数据时仍保留已算结果，区分最少补充输入、目录覆盖不足与真实能力限制。

如果任务涉及流程建设或工况变化，就按[阶段调用规则](../chemical-engineering-expert/references/DESIGN_STAGE_ROUTING.md)在相应阶段执行，而不是等用户索要设备表。存在同案约束时，反馈入口把选型问题送回工艺层，列出需要重算的物流、设备和压力热量关系；采用修改后再次读取新版本结果。最终可生成设备表和来源索引，但初筛型式不等于厂家最终型号，程序也不会替代真实Aspen、EDR或机械设计验收。

Use this product's deterministic equipment engine through JSON, CLI or MCP.
The engine, rules, structured database and schemas are included in this
repository. This workflow does not outrank current-project authority or
physical constraints. No other repository or desktop application is required.

## Start

1. Open the workspace `LOCAL_KNOWLEDGE_GRAPH_LINKS.md`.
2. Resolve the backend through that map. In an installed workspace its root is
   `{CHEM_WORKSPACE}/chemical-engineering-runtime/backends/equipment`;
   read its `README.md` and `knowledge_graph/README.md`.
3. Read [references/ERROR_MEMORY.md](references/ERROR_MEMORY.md), then [references/app_contract.md](references/app_contract.md).
4. Read [references/NEW_KNOWLEDGE.md](references/NEW_KNOWLEDGE.md) only when recently ingested application knowledge is relevant.
5. Use `tools/expert_cli.py --describe` under the runtime root, then discover
   the original `catalog` and `schema_get` contracts through its `equipment`
   operation. The bundled `app/equipment_design_agent.py` is the underlying
   engine, not a separately installed application. Keep one JSONL session or
   MCP lifespan for repeated requests. No GUI/EXE is distributed or required.

## Agent-first execution

### Flow-design feedback use

When checking a built process or changed process parameters/modules, use the
chemical expert's `references/PROCESS_EQUIPMENT_FEEDBACK.md`. In this workspace,
the unified entry is `tools/expert_cli.py` under the runtime root. Its
`feedback` operation calculates equipment, binds same-case inputs and constraints,
then builds a process revision plan. Data and algorithms have explicit version
identities; use those identities in the result. Source-maintenance tools are
separate from routine equipment execution.

Return parameter/formula/rule provenance, attributable capacity or physical
diagnostics, catalog/evidence gaps, and adjustment-plan hashes to process design.
Exchanger series-first alternatives, compressor staged-series and parallel-column
alternatives require their own duty/pressure/phase/flow rationale and downstream
replay. A program adjustment is a candidate until the flowsheet is actually
changed and rerun; no-match, a default terminal form, or open vendor evidence
alone must not trigger blind splitting or imply whole-process acceptance.
See `references/process_feedback_bridge.md` for invocation and return paths.

Create an `equipment-design-agent-request-v1` JSON object as the `payload` of
an expert request with `operation: equipment`; invoke `tools/expert_cli.py
--request <path>`. The response retains the original
`equipment-design-agent-response-v1`. `equipment_batch` accepts `requests[]`;
`tools/expert_cli.py --session-jsonl` accepts one complete expert request per line.
Runtime verification, catalog loading and one API instance are reused. Retain
each response's own exit code; a bad request must not erase later valid results.
Close stdin to finish the session. Direct backend commands remain available
for its explicitly scoped software/provider interfaces.

Use `capabilities`, `schema_get`, or `catalog` to discover operations, exact JSON contracts, and per-equipment fields before constructing requests. Use `manual_batch` for multiple manual records. Preserve the returned request hash, exit code, errors, and artifact paths. The unified local gateway exposes 18 registered local operations; `aspen_import`, `hybrid_run` and legacy `llm_review` are separate, explicitly authorized routes, not automatic dependencies. For an authorized direct provider call, read keys only from `EQUIPMENT_DESIGN_LLM_API_KEY` and endpoints only from `EQUIPMENT_DESIGN_LLM_BASE_URL`; never put credentials in JSON. Local prepare/continue/apply need no provider connection.

For a machine-readable Aspen flowsheet, call `pfd_build` with a read-only
`aspen-equipment-export-v1` `bundle_path`. Use `pfd_override` with the current
override map, block ID, and a catalog selection ID; use `AUTO` to restore the
automatic route. Use `pfd_recalculate` / `aspen.pfd.recalculate` with at least
`bundle_path + block_id`; carry the complete `parameter_overrides` returned by
the prior call as the current state and put this block's nonblank replacement
row in `values`. Omit blank fields to retain Aspen/existing values; use
`clear=true` to remove this block's parameter layer. Recalculate only the
changed block, then keep incident streams and immediate upstream/downstream
blocks stale until they are replayed separately. Never write the mapping or
parameter layer over the bundle/BKP, and never treat a user type/parameter
override as mechanical-design or model evidence. Keep the compact/standard/detailed
data projections as optional information-density choices. Preserve complete
parameters in JSON and build permitted type overrides from the current catalog.
No left-click, right-click, canvas or other GUI operation is part of this Skill's
execution path. Invalidate stale selection overlays before recalculation. Parameter metadata must explain existing values,
blank behavior, units, dependent formulas and evidence boundaries. These are
machine-readable data requirements, not a requirement to operate a dialog.

Route every new model-assisted call through protocol `1.9` rather than the legacy one-shot review path. Its primary model role is calculation assistance and avoidable-stop reduction; output composition and review are secondary:

1. Call `hybrid_prepare` with `input.operation + input.payload`; it reruns the current deterministic engine and freezes the result, replay contract, allowlisted knowledge context, candidate/condition registries, calculation-recipe catalog, coverage state, and hashes. Never accept a caller-supplied naked deterministic result.
2. For an external Agent, send only that prepared package and validate its strict `equipment-design-llm-step-output-v1` JSON with `hybrid_continue`; this must replay the source input and rebuild the prepared package before accepting the output.
3. For the built-in provider, call `hybrid_run`; it must reuse the same `hybrid_continue` validator and always return `equipment-design-hybrid-result-v2`, preserving the initial deterministic result on disabled, failed, or successful LLM paths. A model may select an allowlisted simple recipe, but the program computes its value. When every recipe input is frozen and the target is missing, `manual_match/auto_match` may inject that verified value and automatically return a separate deterministic recalculation. A model may also upgrade a visibly default-selected terminal equipment form only by returning an exact registered family condition/rule and the frozen selection-context hash; the program must replay the deterministic engine. Free-text types, invented rules, unsupported conditions, and changes to explicit or already condition-selected forms are invalid.
4. Treat unknown recipes, missing recipe inputs, existing-value conflicts, and model-only inferred values as item-local nonblocking outcomes. Exhaust the registered recipe dependency graph first. A remaining allowlisted preliminary field may use `model_inference` only with `uncertain`, a cited same-case/engineering/conservative-screening basis, nonempty assumptions, numeric bounds or a registered enum, confidence, sensitivity, and an explicit preliminary-auto-apply request. The program must validate it, fill only a missing field, replay the deterministic matcher, expose it as `J/provisional`, and cap it at `TYPE_SCREENING`; a deterministic result always supersedes it. A certain program-verified recipe needs no uncertainty warning.
5. Let the model order and title only its own intermediate operation blocks. Preserve the program's initial and recalculated result blocks as immutable authoritative anchors on either side of those AI operations.
6. Apply descriptive changes or candidate references only through `llm_apply` with explicit approval bound to both `context_sha256` and `orchestration_sha256`.

The prepared and orchestration objects must also bind the current `authority_revision`: Agent/matcher versions, hashes of core rules/model rules/parameter templates/pump points/model graph, every protocol Schema hash, and—when packaged—the verified runtime manifest hash and bundle revision. Reject continue/apply when any bound revision differs, even if a caller recomputes outer hashes.

Choose one injection point: `semantic_extraction`, `textual_condition_judgment`, `ambiguity_resolution`, `kg_retrieval_planning`, or `audit`. Choose `minimum`, `routed`, `full_family`, or `full_bundle` context deliberately. Treat `PARTIAL` coverage as incomplete; never describe a full deterministic JSON object as full graph coverage. Model calls may fail without deleting or changing the deterministic result.

For human-readable output, call `render_report` with a replayable `input.operation + input.payload`; the current engine must recalculate before producing `equipment-design-presentation-v1` or self-contained HTML. Reject caller-supplied result/response objects so a forged model state cannot be rendered as deterministic authority. Do not reconstruct parameter tables by scraping GUI text.

For customer-facing equipment schedules, call `customer_export` with the same replayable input contract. It must return the overview table, family datasheet, and evidence index from the frozen 19-profile authority file. Keep every required field even when missing; show customer-table gaps separately from algorithm/evidence-gate gaps; keep standard reference routes separate from formally adopted standards; and never promote a standard marking or engineering designation into a vendor-final model.

## Calculate before selecting

Enforce this order for every family:

`raw/Aspen values -> normalization -> family -> all closable calculations -> equipment-design-parameter-package-v1 -> checks -> selection_feature_vector -> candidate matching -> evidence promotion`.

Read `knowledge_graph/equipment_parameter_chain_templates.json` under the resolved backend root for the 17 family layouts and `equipment_model_recommendation_rules.json` for candidate classes and gates. Require every derived target to appear in `derived_parameters` and the parameter package before selection. Verify that `model_recommendation.selection_execution.context_sha256` equals the package selection-context hash.

Partial input must return the known parameter rows, candidate family, minimum missing sets, next fields, and a deterministic most-general model/engineering-specification candidate for every physical equipment record. It may not promote that screening candidate to a catalog/vendor final choice until the candidate feature vector and same-equipment evidence gates are ready. Never map a screening result to a final result: calculated pipe diameter is not selected DN; a GB/T pump marking is not a vendor model; a custom tower or vessel uses an engineering designation rather than an invented commercial model.

## Route the input

- Aspen file: copy the source, hash it, open the staged copy in an isolated worker, traverse every block/stream, preserve raw paths/units/status/connectivity, generate the deterministic `aspen_pfd_mapping.json`, and pass the export to `aspen_equipment_derivation.py`. Treat `NOT_RUN/NORESULTS` Output zero/blank-unit nodes as unavailable placeholders, not process zeros. Apply deliberately broad non-design hard-sanity ranges to finite Aspen flow, mass-flow, heat-duty, power, area and geometry values; isolate sentinel-scale values and mass/volume/density conflicts as field-local diagnostics before the parameter package, formulas and designation are built. Preserve the physical equipment identity and most-general candidate. Classify exact `FSPLIT`/`MIXER`/`HIERARCHY` blocks as non-equipment simulation logic nodes by default: retain their PFD/connectivity/override surface, but never invent an independent physical device or model, and exclude only those exact records from the equipment-closure aggregate. When run is requested, use only the staged copy, capture and hash the finalized raw `.his` through an isolated SaveAs, and retain REP/SUM/MSG as diagnostics; without clean raw-history evidence the process basis remains provisional. COM is optional; its absence must never block the other routes.
- Manual input: select the Aspen module or equipment family and provide one explicit physical quantity per JSON field. Run the deterministic matcher without a remote model or network.
- LLM-assisted calculation/review: require a human-configured endpoint profile/model/key for remote calls. Keep the key outside request artifacts. Use protocol 1.9 first to close simple missing inputs through allowlisted recipes and program recalculation, then to upgrade a visible terminal default through a registered condition/rule and deterministic replay, and finally for semantic extraction, textual conditions, ambiguity handling, graph-retrieval planning, output organization, or audit. Descriptive changes and candidate references remain approval-bound.
- Knowledge lookup: query the workspace vector index when present; otherwise use the bundled deterministic graph search. Do not invent an unindexed route.

## Preserve authority

- Deterministic matching, units, pressure basis, physical direction, source hashes, run status, evidence gates, and model status are authoritative.
- Aspen supplies process-side conditions and properties, not automatic mechanical design, materials, internals, vendor curves, or final model evidence.
- When several valid branches remain, retain their common most-general family/type and candidate set. Do not silently choose a specialized subtype.
- Keep equations as a coherent chain: `target = formula = substituted calculation = answer`. Omit needless repetition; every displayed number must serve the substitution or result.
- Every value generated by a built-in formula or fallback must carry a structured, visible notice in JSON and presentation stating that it is not an Aspen/user-direct value. Apply the registered hierarchy `same-case/Aspen/user value -> exact deterministic derivation -> graph/standard conditional recommendation -> built-in recommended formula -> explicit final fallback`. Class-A identities remain `D`; every recommendation/formula/default branch is `J/provisional`, assumption- and sensitivity-tagged, may not overwrite a supplied same-case result, and is capped at type screening. Registered defaults may cover density, efficiency, velocity, retention time, fill fraction, material route, LMTD correction factor and similar preliminary inputs, but never a vendor-final value or an approved same-equipment evidence package. Every physical device must also expose exactly one terminal equipment form with `EXPLICIT_TERMINAL_TYPE_SELECTED`, `CONDITIONED_TERMINAL_TYPE_SELECTED`, or `DEFAULTED_TERMINAL_TYPE_SELECTED`; broad family labels are identity inputs, not explicit forms. Terminal form remains separate from vendor-final model evidence.
- Do not close a heat-exchanger area chain or promote a candidate on `Q=0`; zero duty does not prove that a zero-area exchanger has been designed. Retain the most-general preliminary exchanger specification with the duty gap visible. Show `design_pressure_mpa` with neutral `MPa`, require or visibly recommend `design_pressure_basis` for a direct value, normalize absolute pressure to gauge with explicit or registered-and-warned atmospheric pressure, and route nonpositive normalized gauge pressure to the external-pressure branch instead of an internal-pressure thickness equation.
- Require `volume_basis` with selected `volume_m3`. Keep minimum total required volume separate from straight-shell geometric volume: compare `nominal_total` and `geometric_total` directly with the required total, and compare `effective_working` with `required_total * fill_fraction`.
- Treat `ΔP/(ρg)`, `ΔP·Q`, and efficiency-adjusted liquid-turbine results only as pressure-head component, pressure-power component, and shaft-power screening. They are not total machine duty or a final unit selection. Treat tower `πDi²/4` as total shell cross-section, not active area after downcomer, receiving-pan, or inactive-zone deductions.
- Use the built-in membrane-area geometry only for `cylindrical_channels`; every other geometry needs a same-duty external `membrane_area_m2`. Keep material visible as an optional preference, never as an implicit required field or silently selected formal material.
- Preserve full numeric values in JSON and use compact engineering precision only in presentation fields.
- Never let an LLM overwrite existing design numbers, units, pressure basis, evidence state, hard blockers, or final equipment model. It may select an allowlisted recipe for a missing input, or an exact registered terminal condition/rule for a currently default-selected form; the program must compute, replay, and verify the resulting value or form. After recipes are exhausted, a structured estimate may be auto-applied only to an allowlisted still-missing preliminary field after bounds, enum, physical and cross-field validation; it remains visible `J/provisional`, carries assumptions/confidence/sensitivity, and cannot promote beyond `TYPE_SCREENING`. An unregistered or unbounded free inference is rejected, and a free equipment type is always rejected.
- Do not accept free-text `candidate_model`. A model may reference only an existing deterministic candidate with exact `candidate_id`, `designation`, `selection_feature_vector_sha256`, and `selection_context_sha256`; revalidate all four after deterministic recalculation.
- Require every nested LLM claim to cite a `context_id` from the immutable prepared package. Condition judgments may use only registered deterministic condition IDs.
- `final_model` requires the package’s evidence manifest and independent audit approval. Otherwise stop at the highest supported provisional state.

## Verify delivery

Verify the delivered headless surface: protocol schemas, JSON file/stdin/stdout
and resident `--session-jsonl` round trips, deterministic replay and tamper
rejection, and exact runtime source/data/schema manifests. Require independent
responses from one resident process and one frozen authority instance.

For supported calculation operations, test missing-only recipe closure,
order-independent multistep derivation, provisional bounded estimates,
registered terminal-condition upgrades and local rejection of invented rules,
out-of-range values or overwrites. Preserve the initial and recalculated program
anchors, units, formula chains, source traces and evidence states. PFD data
operations retain node/edge identity, current-block recalculation and adjacent
stale propagation; no desktop canvas or coordinate control is required.

The published regression suite is `tests/test_equipment_backend.py` under the
runtime source repository. It checks all 17 family contracts, source/data
identities, guarded execution and actual database consumers. Private ten-case
BKP replay is an additional user-supplied evidence profile, not an included
fixture or a reason to claim real Aspen testing. Source-maintenance scripts
need their explicitly declared original inputs.

Test from a different working directory without the old workspace. Database
queries must return source identity, units, applicability and reuse status.
A missing, changed or extra required runtime asset fails verification. GUI/EXE
self-tests are outside this Skill's distribution and acceptance scope. For a
real Aspen candidate, independently apply the all-zero version-bound Summary
and raw-history gate to the exact reopened delivery file.

Do not declare the app or a design result ready until an independent chemical-equipment/knowledge-graph reviewer has checked the deterministic boundary, formula chains, evidence propagation, and packaging result.

阶段收尾若发现有证据且值得复用的新方法或原则，将候选交主助手，按
[主动经验提醒](../chemical-engineering-expert/references/EXPERIENCE_INBOX.md#主动提醒使用者)
展示可审阅摘要并推进确认/投稿；拒绝不催促，已有有效授权不重复询问。
