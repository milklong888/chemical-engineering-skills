# Source/scaffold boundary and rigorous handoff

Use this record when delivering a document-driven source or scaffold arrangement.
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
- `streams` gives a unique stream ID, `from`, `to`, `state` and evidence anchor.
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
  duty to `node_ids`, purpose, valid scope and permission/source reference. Each
  needs exactly one `handoffs` row. If there are none, give the actual reason in
  `no_placeholders_reason`; do not omit planned placeholders to shorten the form.

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
against the actual source. The script cannot detect omitted source duties,
invented citations, wrong physical choices or a contradictory free-text equation.

The existing process-feedback backend owns affected-consumer propagation and
real source/constraint binding. This report includes a `declared_topology`
projection in its existing `nodes` / `[from, to]` format for known endpoints;
it is explicitly partial if any endpoint is unknown. Do not pass a source plan
off as a same-case simulation export or a complete equipment inventory.
