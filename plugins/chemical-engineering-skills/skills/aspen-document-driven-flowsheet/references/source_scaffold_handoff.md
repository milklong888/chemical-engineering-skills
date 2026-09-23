# Source/scaffold boundary and rigorous handoff

Use this record when delivering a document-driven source or scaffold arrangement
of process nodes, streams or simplified placeholders. A team responsibility or
section contract alone uses the two-section Skill's Section Contract template
and applicable stage query; do not invent a topology merely to populate this record.
An individual principle lookup, title/table audit or a stage-routing receipt alone
does not create this deliverable or enlarge the task into a whole flowsheet.
Copy [the blank input](../assets/source_scaffold_handoff.json) into the current
project, or project equivalent fields from its existing authority/topology ledger.
Fill it from the task, current source and actual exports; do not put project data
in the Skill. The blank rows are field shapes to fill/remove, not valid project
entries. Missing evidence stays explicit in the current record.

## Fill the arrangement

- `authority_reference` is nonempty text identifying the current task/source and revision or hash;
  it is a citation to inspect, not a verified identity supplied by this checker.
- `nodes` declares each process node and each external endpoint separately with
  `kind=process|external`. Each control volume lists its process `members`.
  A process node outside one selected volume may be inside a larger one.
- `streams` represents actual material transfer, with a unique stream ID, `from`, `to`, `state` and evidence anchor.
  Use `documented` for a source-stated connection, `proposed` for an explicitly
  permitted arrangement, and `unresolved` with `null` endpoint(s) and a specific
  `gap` when the connection is unknown. A familiar stream name supplies no endpoint.
  Split mixed or aggregated boundary terms into disjoint stream IDs first.
- Trace every declared process node's incoming and outgoing interfaces. A recycle
  return also needs its upstream recovery/source connection; a missing origin or
  destination is a stream with the known node at one end and `null` at the other,
  not a reason to omit the stream. Do not invent a recovery location from a name.
  An unrelated null-to-null stream, a self-loop or a handoff gap does not supply
  a missing node interface. External endpoints need no artificial reverse flow.
  The check applies to the declared graph, independently of the selected local
  control volume; it does not require enlarging that volume.
- If the current source actually defines a phase with no inlet or no outlet
  (for example, a documented inventory withdrawal or filling phase), a process
  node may include optional `no_inflow_reason` or `no_outflow_reason` text. Give
  the actual reason and source/phase anchor. Unknown connectivity, missing data
  or a decision postponed to a later stage must instead use an unresolved stream.
  The checker reports these absence declarations but cannot verify their meaning
  or source: the assistant must check them against the current material. A reason
  contradicting a known or unresolved connection is a structural error.
- For each control volume, declare the intended `inflows` and `outflows` by
  stream ID, the material/time/component basis in `balance_basis`, and the
  relevant `reaction_terms` (or its source-bound absence/unknown status).
  The checker derives crossing directions from membership and flags a mismatch.
  It does not calculate reaction terms, rates, inventory or numerical closure;
  those remain under the expert's [derivation protocol](../../chemical-engineering-expert/references/REASONING_PROTOCOL.md).
- Inventory every currently allowed placeholder in `placeholders`, binding its
  duty to `node_ids`, purpose, valid scope and permission/source reference. Keep
  that reference faithful to the actual source: cite the authorizing statement
  and state any execution restriction separately in direct wording. Check that
  the reference and `required_returns` do not contradict one another; permission
  to arrange or calculate a placeholder does not override an explicit
  software-execution restriction. Each
  needs exactly one `handoffs` row. If there are none, give the actual reason in
  `no_placeholders_reason`; do not omit planned placeholders to shorten the form.

## Material channels

Use process nodes at the level of independently connected material services.
Separate the nonmixing channels of one physical device: a stream passing through
its cold service, then another unit, then its hot service does not return to its
own inlet. Merging those services into one node creates a false material cycle.
Bind both services to the same physical device in the existing node IDs/naming,
method applicability and relevant handoff; do not add unsupported schema keys,
count two devices, or pretend planning IDs are actual Aspen block IDs.
Direct-contact heating/mixing really transfers mass and retains that connection.
Different phases alone do not define nonmixing channels. A contacting, mass-transfer
or reacting unit retains its common material/reaction relation and actual phase
outlets; do not split it into noncommunicating services merely to remove a graph
cycle. A phase-separated display still records the cross-phase transfer/reaction
and downstream separation. Graph reachability alone does not mean every component
follows a recycle: check the actual component split before changing the topology.

Steam, condensate, cooling water, refrigerant, makeup and blowdown remain material
streams even when their purpose is utility supply. Keep actual internal headers
and returns inside their true boundary, not external to evade a cycle check.
Heat duty, shaft work, electricity and control read/write dependencies are not
material streams and cannot supply a missing material inlet or outlet.

Keep nonmaterial relations in the existing service `methods` and its evidence,
or in a genuinely authorized placeholder's `handoffs.inputs/required_returns`:
name the producer, consumer, relation, basis and initialization/closure obligation.
Do not invent a placeholder to store prose. Formal full-flow work also reuses
`planning_checks_ref.heat_strategy/compression_decisions` and the original native
control route. These are source-linked engineering records, not a typed-edge
verification or solved energy balance. `no_recycle_reason` means no material
recycle only; heat/control coupling can still require iterative solution.

The checker cannot infer material identity from names. It treats every submitted
stream as a material edge. The agent must review this classification and the
separate nonmaterial obligations. Later map planning services to actual exported
blocks through existing module `node_ids` and `original_node_ids` records; preserve
the original exports including real heat/work streams and all existing export
coverage gates. The planning graph is not a replacement for a native Aspen graph.

## Deliver the handoff now

For every placeholder row, record the receiving `owner` using the existing
[task registry](../../chemical-engineering-expert/references/ACTIVE_ASSET_REGISTRY.md).
If the physical family is not established, set owner to `null` and give the
specific `selection_condition` and relevant owner candidates in that condition.
This is a current decision boundary, not an instruction to decide everything later.

List each enabling input with either its actual value/reference or the precise
missing evidence. Fill all four `required_returns` for this duty:

| Field | What the receiving owner must return |
|---|---|
| `method_basis` | Applicable physical method, property/reaction basis and source limits |
| `boundary_states` | Same-case inlet/outlet IDs, flow/composition, temperature, pressure and phase needed for reconnection |
| `closure_targets` | This duty's component fate, relevant balance/target checks and impacts on connected consumers |
| `execution_evidence` | Actual performed/not-performed actions, current files/exports/receipts, unresolved gates and what may reconnect |

Use concrete duty-specific obligations in these cells; headings or a generic
“verify later” are not a completed handoff. `execution_status=not_executed`
is appropriate for a source-only plan. If execution is merely reported, use
`reported_unverified` with its reference; this helper does not accept it as proof.

## Check and return

### Source text review

For expert full-flow planning, bind the existing source-ledger pass to this
same record with top-level `source_review`. It is not a second process graph.
`documents` lists the current task/source/approved-offset text files, each with
`id`, `path`, and the exact `sha256`. Use original supplied UTF-8 `.txt`/`.md`,
or text already extracted and checked by the existing document-reading route
with its original page/figure locations retained. If the source is a user
message only, first preserve its unrewritten text and message identity locally.
Do not replace the source with an agent's summary or register reference books
as if they were current-project instructions. Unread/unextracted tables or
figures remain explicit gaps; this inventory cannot prove extraction completeness.

For a new expert plan set `source_review.unit_mode="layout_blocks_v2"`.
This keeps explicit list-item and Markdown-heading starts as separate reading
blocks, while ordinary wrapped lines stay together. It does not split by
chemical meaning or certify that one block contains only one function.
The omitted mode remains `paragraphs_v1` for old ordinary records; strict
source review rejects an old paragraph that aggregates several explicit list
items and asks for a new inventory and dispositions. Never silently rewrite
old unit IDs or reuse their receipts after migration.

Before drawing the summary graph, run the same checker in inventory mode:

```text
<configured Python> -B -X utf8 <this Skill>/scripts/check_flow_handoff.py --input <current source record> --source-inventory --source-root <project evidence root>
```

At this point the input may contain only `source_review.documents`; the other
planning fields can still be under construction. This mode reads only those
explicit files under the declared root, checks their bytes against their hashes,
and returns `inventory` with generated `unit_id`, original paragraph text,
line positions and hashes. It does not read arbitrary citations or fetch sources.
Do not invent inventory IDs or copy a prior revision's inventory.

Work through the returned blocks in source order and complete the functions
inside each block before moving on. A listed function can still contain several
material or nonmaterial relationships; the mode is a reading aid, not semantic
coverage proof. Add each actual material service
and every material branch/return to the original `nodes/streams`, recording nonmaterial
obligations in their existing method/handoff fields, then add exactly one
`source_review.units` disposition for that paragraph:

- `unit_id`: the ID returned by the actual inventory.
- `disposition`: `mapped`, `context`, or `unresolved`.
- `stream_ids`: existing material graph edges supported by this paragraph. For `mapped`,
  a nonempty list; for nonmaterial-context `context`, an empty list. An unresolved
  connection may still name its known provisional edges, without inventing ends.
- `reason`: the actual source interpretation, non-connection purpose or precise
  unresolved question. Pure heat/power/control paragraphs use `context` with the
  actual relation and its existing method/handoff record location, not dismissal
  as irrelevant. Mixed paragraphs map every material branch and also record their
  nonmaterial obligations. A statement that source flow/pressure is missing is not
  a reason to omit an already stated connection.

One paragraph may have several connections: mapping only its main outlet does
not account for a stated return or remaining fraction. Shared physical routes
may be cited by multiple paragraphs. Storage/group headings do not replace
independently described treatment, separation or return functions. At reverse
review, compare the returned source paragraphs against the projected original
stream endpoints; especially recheck `context` rows and paragraphs with several
destinations. Source values/units and their exact stream or equipment identity
also stay in the existing inputs and initialization fields when read.
For a receiving-state qualifier, identify the upstream operation or source-bound
condition that actually establishes it, including any later reaction that
changes that state again. A renamed stream is not a treatment function. Keep
a necessary unresolved function and its material fates without inventing a
specific apparatus; do not add equipment when the source-bound feed already
meets the condition. Check explicit heat/work/control uses individually in the
existing method/handoff locations; a utility-group label is not their mapping.

`source_review_checked` means the supplied files' identity, complete paragraph
disposition set and registered stream references were checked. It does not prove
that the supplied document set is complete, a `context` claim is true, or every
sentence was interpreted correctly. The old `source_inventory_verified`,
authority and engineering flags remain false. Unknown endpoints or genuine
local source ambiguities remain unresolved, not invented to make a green result.

Old ordinary handoffs may omit this field. If supplied, the checker requires
an explicit `source_root` and validates it even without the strict switch;
it never silently uses the current working directory as source authority.

### Full-flow expert text planning, without software execution

When the task stops at expert-layer full-flow text planning, reuse this source
record and add `expert_plan`; do not make a second topology ledger. The record
is ordinary planning evidence, not an Aspen model. The agent creates it from
the current plan even when the user supplied only prose.

Create this project-local file when entering planning, then fill it while reading
and calculating. Do not write a separate final narrative first and attempt to
reconstruct the record afterwards. Use the existing `design_stage` entry with `stage=source` and
`source_work=expert_plan`. Its initial missing-record response means continue
the routed planning work. At closeout supply this file's exact path and SHA-256
as `planning_handoff`; the stage entry actually calls the registered checker
with **`require_source_review=True, source_root=<declared evidence root>`**
(which also enables the four existing planning/reaction checks) and preserves
the result in `expert_planning`. Save the input and complete stage receipt.
See the expert's [stage routing](../../chemical-engineering-expert/references/DESIGN_STAGE_ROUTING.md)
for the current entry. A narrow source lookup retains the old route.

If that entry is genuinely unavailable, use the same existing checker directly
with **`--require-source-review --source-root <project evidence root>`**, record the manual
fallback and keep its input/output. This switch implies all four prior strict switches. Do not
skip verification or label a normal knowledge-search receipt as this check.
It requires `stage=source` and unexecuted handoffs, not an Aspen run or the
later independent reviews. This does not waive any formal full-flow contract
gate when modeling begins.

The `expert_plan` object retains its four original fields and adds `reaction_derivations`
for current expert planning. Old ordinary calls may omit it; when supplied it
is checked even without the new flag.

| Field | Content tied to existing nodes/streams |
|---|---|
| `methods` | Groups with `node_ids`, concrete `method`, `phases[]`, `applicability`, `source`, `status=source_fixed\|candidate\|not_applicable`, and `unresolved_inputs[]`. Cover every process node, grouping shared applicability. An identity/logic-only service may use `not_applicable` with `not_applicable_reason`; do not invent a property model for it. |
| `pressure_paths` | Groups with `id`, `node_ids`, `stream_ids`, `state=symbolic\|calculated\|not_applicable`, `method`, `equation_or_reason`, `source`, `inputs[]`, and `refine_trigger`. Cover every process node. Each non-N/A node must be touched by a listed stream; listed streams must touch the group. Branches are allowed. |
| `recycle_plan` | Rows with actual `stream_id/from/to` for chosen material tear edges, `initialization_basis`, positive-integer `closure_order`, `controlled_quantity`, and `purge_or_terminal_basis`. Describe this flow's open-loop seed source and closure sequence, not invented run results. Removing the tears must leave the declared material-channel graph acyclic. Check independent nonmixing channels before inventing a tear. |
| `no_recycle_reason` | Source-bound reason when there is no material recycle; otherwise `null`. This does not assert absence of heat/control coupling. Do not omit a known recycle because no numerical initial state has been run. |

Each non-N/A methods row also carries `named_methods`, a nonempty list of the
current selected candidate(s), not a list of methods to investigate later.
Each declaration has `name`, `name_origin`, `source_ref` and `applies_when`.
Use separate entries for supported condition branches and name the discriminating
condition; parameter gaps remain in the existing `unresolved_inputs`.

- `name_origin=aspen_v14_catalog`: an exact name in
  [the non-exhaustive V14 name reference](../assets/property_method_names_v14.json).
  It only confirms a documented name; it does not select a method or verify
  applicability/parameters. `source_ref` points to the actually inspected method
  definition; `applies_when` ties it to this service and known/conditional facts.
- `name_origin=source_defined`: another version's method, a named physical
  model, or a custom combination outside that list. Also provide
  `definition_ref` locating the actual definition/equations or specified model
  composition. An absent catalog match is not evidence the method is invalid.
  A family label or 'choose later' is not a definition.
- N/A rows use `named_methods=[]` and the original source-bound absence reason.
  Names are nonempty, single-line text of at most 80 characters. The catalog
  route does not carry `definition_ref`; source-defined declarations require it.

Old ordinary handoffs may omit `named_methods`; if present it is checked even
without the new switch. New expert planning uses the switch so every applicable
row has a named candidate. Legitimate unresolved selection is reported as a local
planning gap, not hidden by declaring N/A or inventing a name.
`named_method_declarations_checked` certifies only the supplied declaration
checks (all rows are required only with the switch). Its catalog version/hash
is retained when used. Citations/definitions remain inert and unverified; the
assistant reads the actual sources. Never infer an engineering pass from it.

### Current decisions inside the same plan

Expert text planning also requires the action declarations below; the stage
entry enables them. Old ordinary records remain compatible when the new strict
switch is omitted. Supplied action fields are checked even in the old mode.

For every non-N/A pressure group, `interface_actions` contains exactly one row
for each existing `stream_id` in that group's `stream_ids`. A group may still
contain branches: the checker does not assume list order is one linear path.
Each row has:

- `stream_id`: reference to the existing edge; its from/to are projected, not
  copied into a competing topology.
- `receiver_requirement`: this receiving service's pressure/phase requirement,
  using source values or explicit symbols/conditions.
- `budget_relation`: the current endpoint relation, applicable losses/raises
  and input basis. A generic plant-wide slogan is not a completed decision.
- `equipment_action`: existing equipment, justified direct connection, or the
  conditional pumping/compression/letdown action at this interface.
- `condition_or_basis`: why that action applies or the minimum condition that
  decides the branch. Unknown numbers do not erase the interface decision.

N/A pressure groups omit this field or use an empty list with their original
specific N/A reason. N/A cannot mean “operating data not supplied”; that remains
a symbolic service. These declarations are not a new pressure calculator.

Each recycle row also has `startup_plan` with:

- `temporary_boundary`: what temporarily supplies or bounds the receiving
  service, and its source/conditional basis without inventing values.
- `forward_pass`: what is calculated first while the return is open, sufficient
  to reach the chosen seed outlet; a source-bounded simple scaffold is allowed.
- `seed_outlet_stream_id`: registered outlet from the return's source node;
  it may be the torn stream itself. It identifies where a future seed will be
  read, not an existing run result.
- `depends_on_recycles`: existing tear IDs that must close first, or an empty
  list for independent work.
- `closure_reason`: the engineering dependency or reason for independence.

Dependencies must reference other declared tears with earlier `closure_order`.
Independent tears may share an order; integers need not be unique or contiguous.
The existing `initialization_basis` remains the source/seed explanation.
The checker does not prove that the dependency list or forward computation is
physically adequate.

`plan_action_declarations_checked` certifies these fields and registered-edge,
seed-source and declared-dependency consistency only. The agent still checks
whether the proposed actions follow the actual source, operate on the right
phase, use coherent units, and can start the intended calculation. It never
means “planning passed,” “pressure calculated” or “recycle converged.”

Each pressure input has `name`, `unit`, and exactly one of
`value_or_reference` or `gap`. Symbolic plans need an explicit input gap;
calculated declarations have no input gap and need `result_reference`.
That is an inert citation to the actual calculation result, not proof of an
Aspen run; the checker does not open/authenticate it. Other states must not
carry `result_reference`. N/A needs a concrete `equation_or_reason`; its
streams/inputs may be empty. Cite a real method/equation now: “calculate later”
is not an engineering method even if it can satisfy a nonempty-text check.

`expert_plan_checked=true` means structural checks ran, including cycle
coverage only on declared process edges. It does not verify source completeness,
method applicability, chemistry, phases, units/dimensions, equations, results,
citations or execution. The separate source-review result only checks the
explicitly registered text identities, paragraph dispositions and edge references.
Unknown endpoints stay unresolved. Read the output and
manually review the sources and key calculations. Keep all existing false
engineering/execution/authority flags. Parameter gaps can remain in a useful
text plan but must close before the affected engineering claim is accepted.

### Reaction-derived numbers in the same record

When the plan uses explicit reactions to derive quantities, supply
`reaction_derivations={"reactions":[...]}`. Each reaction has `id`, `scope`
(the quantified subset), `basis_ref`, and `species`. Each species has `id`,
`formula`, signed `coefficient` (negative reactant, positive product), integer
`charge`, and `basis_ref`. Exact fraction strings are allowed. Declare the
actual molecular or fixed repeat-unit formula, not a variable polymer label.
Use the full reaction including relevant co-reactants and coproducts; omitting
water or a gas product merely to make a yield calculation shorter is invalid.

The fixed sibling chemical-expert helper checks each elemental and charge
residual; it does not auto-balance, invent a reaction, read citations, or prove
physical feasibility. Unsupported formula syntax fails explicitly. Empirical
COD or lumped-component mappings are not molecular stoichiometry: identify
those separately and verify their actual source ratio/calculation. If no
explicit reaction is used quantitatively, give
`{"reactions":[],"none_reason":"the actual task-bound reason"}`. Omit
`none_reason` for nonempty reactions; an explicit N/A is not a mathematical pass.
A cited independent check is needed for a used relation the helper cannot handle;
do not hide a used molecular derivation behind an empty list.

Optional per-reaction `mass_projection` contains `reactant_id`, `product_id`,
`feed_mass={value,unit,basis_ref}`, and exactly two `molar_masses` records
`{species_id,value,unit,basis_ref}` for those species. Supported molar-mass units
are `g/mol` or `kg/kmol`; the mass/feed unit is retained (`mg`, `g`, `kg`, `t`,
optionally `/s`, `/min`, `/h`, `/d`, `/day`). This computes only a hypothetical
complete-consumption contribution using supplied coefficients and molar masses.
The caller must still verify feed identity, co-reactant availability, molecular
weights, conversion/recovery assumptions, and the stated subset. Read the result
and use that same value/basis in the prose; no separate handwritten yield table.
When using a supported reaction-derived mass claim, include its actual projection
before quoting the result. Cover every claimed feed contribution: either separate
rows with unique IDs, or a clearly sourced aggregate sharing the same chemical
entity and molecular/repeat-unit basis. A checked equation or one feed's projection cannot certify other omitted
numeric rows. If the helper cannot express the calculation, retain its actual
independent verification and explain that limit instead of reporting helper coverage.

The original checker loads only the fixed registered sibling helper and records
its hash and original result. No caller-provided code path is accepted. Missing
helper, invalid payload, nonzero residual or invalid projection prevents this
check from passing. An empty justified declaration remains explicitly N/A.
This addition verifies only submitted reaction arithmetic, not omitted prose,
source truth, all equations, complete balances or engineering acceptance.
The existing declaration flags retain their original limited meanings.

### Direct checker: ordinary handoffs or declared fallback


Run the installed script with the project's filled input and a new output directory:

```text
<configured Python> -B -X utf8 <this Skill>/scripts/check_flow_handoff.py --input <project>/source_scaffold_handoff.json --output-dir <project>/handoff_check
```

It writes `review.json` and `handoff.md`, bound to the exact input SHA-256.
Use the generated process-interface table, edge table and per-volume crossing lists in the delivered
arrangement. Unknown endpoints are listed outside the balance terms; do not
turn them into an assumed external stream. A stream with both endpoints inside
a combined volume cannot appear on either single side of that volume's balance.
In a smaller volume, only actual crossings belong in its inflow/outflow lists.

`STRUCTURE_INVALID` means correct the stated mismatch or undeclared process interface, or report that arrangement
as incomplete; `STRUCTURE_VALID_WITH_UNRESOLVED` preserves proposed connections,
unknown endpoints or missing handoff evidence. `STRUCTURE_VALID` means only
that the submitted fields and declared edge memberships are consistent.
All outcomes retain `engineering_accepted=false` and `execution_verified=false`.
An unexecuted or `reported_unverified` handoff may still have valid structure;
`STRUCTURE_VALID` does not upgrade either execution state.
The assistant still compares every diagram/equation, absence declaration and placeholder inventory
against the actual source. The source-review option binds its explicit files and
paragraph dispositions, but cannot detect omitted source meaning, an omitted
original document/figure, false interpretation, wrong physical choices or a
contradictory free-text equation.
The added reaction check covers only its explicit structured declarations; a
passing result cannot certify a different formula or number in the prose.

The existing process-feedback backend owns affected-consumer propagation and
real source/constraint binding. This report includes a `declared_topology`
projection in its existing `nodes` / `[from, to]` format for known endpoints;
it is explicitly partial if any endpoint is unknown. Do not pass a source plan
off as a same-case simulation export or a complete equipment inventory.
