# AImodelbuilder Cold-Start Examples

These fixtures are toy training materials for a new Aspen project. They show
how to start from documents, choose the knowledge-graph route, build a
unit/card ledger, define audit checks, and decide when Calculator, Design
Spec, Sensitivity, or special separation logic should be used.

Rules:

- Treat every value, stream name, block ID, and component as synthetic.
- Do not copy example chemistry, product specs, or rates into a real model.
- Use examples for workflow shape, then return to current source documents and
  `skill/references/knowledge_graph.md` for the actual project route.

## Example Map

- `00_init_project_minimal/`: filled manifest/config snippets for a new project.
- `01_document_to_unit_card_ledger/`: source-value to Aspen-card ledger shape.
- `02_knowledge_graph_routing/`: recall cues and route chains for common blockers.
- `03_audit_case_fixture/`: synthetic positive/negative audit inputs.
- `04_solve_fit_trigger_scorecard/`: scorecards for reactor targeting,
  concentration-spec columns, Calculator links, and special separation.
- `05_feed_product_recovery_closure/`: low product/fresh-feed diagnosis that
  checks reactor target windows first, then buckets valuable-material losses
  into recycle, recovery, purge, vent, wastewater, solvent, and failed-separation
  outlets before increasing reactor severity.

## Using the audit fixtures

Inspect the two export sets and their configuration files to understand audit
inputs and deliberately violated conditions. The historical `audit-case`
execution wrapper is not distributed in this release, so these directories are
structural examples, not a runnable end-to-end tutorial or accepted Aspen runs.
For executable evidence-parser regression tests, use the distributed
`aspen-plus-operations/scripts/tests/test_aspen*.py` tests as documented in the
release verification guide. Real projects still require their own run evidence.
