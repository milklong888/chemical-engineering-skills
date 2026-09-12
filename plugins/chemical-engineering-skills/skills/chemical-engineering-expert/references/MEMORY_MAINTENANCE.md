# Error and New-Knowledge Maintenance

## Memory layers

Follow `EVOLUTION_LOOP.md` for canonical updates. During active work record
corrections and trials in the project audit and fix their current consequences.
Authorized temporary submissions follow [EXPERIENCE_INBOX.md](EXPERIENCE_INBOX.md)
and remain outside canonical/default retrieval. Formal prompt/rule promotion
requires user-requested consolidation and explicit closure of the current task
revision; new adjustments invalidate that closure. Direct user-requested rule
maintenance is separately authorized implementation, not automatic learning.

Apply `STRICT_ACCEPTANCE_AND_LEARNING.md` before all capture/promotion. A
case-local relaxation and every descendant are audit-only: no global error
entry containing the exception, new-knowledge promotion, success example,
training/distillation, default retrieval or preference-weight increase. Store
the original case exception in its project ledger. Missing lineage is not
proof of eligibility. The general user rule prohibiting such learning may be
recorded here; the relaxed case's technical content may not.

Keep the four active memory layers separate from the temporary submission queue:

1. `ERROR_MEMORY.md`: compact, externally verified procedural corrections.
2. `NEW_KNOWLEDGE.md`: atomic incoming knowledge with provenance and lifecycle.
3. canonical skill/graph files: only promoted, reusable rules.
4. project authority files: current case facts and accepted deviations; never
    replace them with global memory.

The public inbox is a noncanonical review queue governed by its own submission
contract; its presence does not create another rule owner or active graph.

For an authorized candidate review, keep both deliverables from
[the inbox review contract](EXPERIENCE_INBOX.md#本次候选审查的两项交付):
the admission/governance result and the actual technical comparison record.
In the existing project audit, bind the comparison to the candidate content,
current owner/source anchors and versions, overlap/conflict findings,
applicability/counterexample results and specific unresolved facts. Record the
actual read/check evidence; validator pending or a Skill-read event alone cannot
stand in for that comparison. This remains preparatory fact checking even when
complete: it does not create the later, post-confirmation approval event or
upgrade memory status. Restricted lineage keeps these records audit-only.
For requested batch consolidation, EVOLUTION_LOOP.md owns concrete placement,
available counterexample checks and the version/rollback proposal, using this
record rather than deferring the technical comparison again.

Do not use raw conversation summaries, self-confidence, or synthetic examples
as verified long-term memory.

## Capturing a user correction

1. Correct the current answer/model first and state the changed conclusion.
2. Identify one root cause; do not store the entire conversation.
   Until explicit user closure, keep the active incident in the project;
   separately authorized inbox submission is not a shared/default rule update.
   At user-requested consolidation after closure, deduplicate by root cause, scope and
   original correction message ID; replaying the same message adds no count.
3. Search central and route-specific memories for the same invariant.
4. If found, increment `repeat_count`, update `last_seen`, attach new evidence,
   and raise priority when warranted. Do not add a duplicate.
5. If new, add the minimum atomic entry to both the central memory when it is
   cross-domain and the relevant skill/graph memory when it is route-specific.
6. Mark behavioral preference corrections `verified_by_user`. Mark technical
   corrections `candidate` until a governing source, deterministic
   calculation, same-case software result, or user-supplied authority verifies
   the fact.
7. If a newer authority contradicts an entry, mark it `quarantined` or
   `superseded`; never silently delete history.

## Error schema and weighting

Required fields:

`id, scope, trigger, mistaken_behavior, invariant, detector, repair, evidence,
authority, status, priority, severity, repeat_count, last_seen, supersedes`

- `P0`: user-verified cross-domain behavior; safety/physics/authority/delivery
  failure. Repetition may raise review priority only within the proven scope;
  two copies of a narrow preference do not automatically become a global P0.
- `P1`: verified route-specific error with material impact. Read when that
  skill/graph triggers.
- `P2`: verified narrow implementation error. Retrieve by its trigger.
- `pending`: self-detected suspicion or unverified technical correction. It may
  guide a check but cannot override accepted rules.

Repeated reports increase retrieval weight, not truth authority. Technical
truth still follows the evidence hierarchy.

Prompt evolution condenses macro principles and ways of deciding/working, not
verbatim prompts, phrasing preferences or single-case settings. Data-pattern
evolution keeps measurements, uncertainty and applicability in lower references
until a cross-context mechanism warrants promotion. Organization uses one owner
and an explicit no_change/merge/specialize/replace/add/retract decision.

## New-knowledge lifecycle

Use these states:

- `candidate`: provenance known; applicability not fully verified;
- `validated`: source identity, units, scope, and conflicts checked;
- `promoted`: incorporated into a named canonical node/skill rule with a backlink;
- `quarantined`: unsafe, contradictory, wrong-scope, license-limited, or low quality;
- `superseded`: retained for history but replaced by a newer authority.

Legacy events without current strict verification retain their original status
as provenance, but use effective `legacy_unassessed` for shared retrieval and
learning. Do not silently change old evidence or automatically re-promote it.

For every item, record:

`id, scope, claim, source, source_type, source_date_or_version, evidence_class,
units_and_basis, applicability, derived_implications, prohibited_reuse,
validation, status, target_nodes, conflicts, supersedes, added_on`

Store claims atomically. Link to source artifacts rather than pasting long
copyrighted text. Before promotion, check duplicates, versions, project
boundaries, units, software/vendor boundaries, and whether a deterministic
derivation already supplies the same knowledge.

## Structural rules

- Every active skill has `references/ERROR_MEMORY.md` and
  `references/NEW_KNOWLEDGE.md`.
- Every active graph or independently routed overlay has `00_ERROR_MEMORY.md`
  and `NEW_KNOWLEDGE.md` in its root.
- Backups, archives, build products, unrouted scratch/temporary graphs, and
  packaged snapshots do not get independent memories; the asset registry maps
  them to one active canonical authority. A directory whose name still says
  `temporary` may receive project-local memory only when the registry explicitly
  designates it as the current project authority and keeps it out of shared
  cross-project retrieval.
- Add files to the workspace vector index with explicit memory status and
  priority metadata. Candidate knowledge must never outrank accepted rules.
- Validate the registry and companion-file presence after every batch.
