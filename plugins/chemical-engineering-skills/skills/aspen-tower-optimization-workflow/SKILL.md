---
name: aspen-tower-optimization-workflow
description: Optimize and reconnect a source-frozen Aspen distillation or solvent-recovery island using the required shortcut/rigorous route, live Design Specs, same-product comparisons and hydraulic/equipment checks. Use for tower optimization, DSTWU-to-RadFrac, special columns, recycle quality and pressure/vacuum audit; no universal example values.
---

# Aspen Tower Optimization

## Authority First

Read `references/ERROR_MEMORY.md`, the chemical expert's strict
acceptance/learning policy, and the current project change-offset plus tower
ledger. Upstream `aspen-document-driven-flowsheet` owns route, feed,
products and property/phase model; operations owns mechanical cards and the
single strict Summary/history implementation.

## Choose the route

Ordinary key-based distillation may use DSTWU after source, feed, keys,
recoveries, pressure and targets are frozen. Preserve a user-required
DSTWU→RadFrac sequence; the initialization values come from that task, not
an old taught multiplier.

For azeotropic/extractive, absorber/stripper, VLL/reactive or no-meaningful-key
duties, record why shortcut assumptions do not apply and use the authorized
rigorous route. Do not silently substitute a different required method.

## Do the next stage, then verify

`target/property freeze -> shortcut or justified rigorous initialization ->
converged baseline -> bounded sensitivity -> live SPEC/VARY -> full-flow
reconnect -> hydraulics/equipment/pressure -> strict same-file verification`

Read `references/tower_optimization_workflow.md` when executing the stage,
special-column or hydraulic details. Use an optional user-supplied local textbook graph and the legally installed
current Aspen help for fragile card rules; source bodies are not bundled.

- Define a real target, bounded manipulated input, units and applicability for
  each spec. A fixed offline sweep is not a live Design Spec.
- Every outer optimization point re-solves the authorized inner quality
  controls. Compare energy/cost only for matching capacity, purity and recovery.
- Conflicting specs are diagnosed; no target is silently dropped and no
  precision is relaxed to obtain a strict pass.
- Pressure drops, reflux, stage count, HETP, packing and capacity limits require
  current source/geometry/traffic evidence. There are no global pressure-drop,
  inlet-pressure-fraction or old project purity defaults.
- Parallel towers require attributable capability/whole-system justification
  and actual same-basis reconnect verification. Equal splitting is an
  assumption to verify, not a rule for every multi-train design.
- A converged material tower or HYDRAULIC=NO case is not a software hydraulic
  rating. Keep material, source-static, preliminary, software and vendor/
  mechanical evidence levels separate.
- Use `chemical-tower-design` and the expert's equipment-feedback gate for
  section/load-case envelopes and downstream geometry/cost/report propagation.
  Use the dedicated heat-pump replacement skill for VRC/MVR.

## Return contract

Return current tower ledger, same-run feeds/products, live spec/residuals,
pressure/heat/power, hydraulic/selection state and exact-file evidence.
All strict Summary counts for the supported real schema and actual raw
history must pass; products and full-flow gates remain additional requirements.

A relaxed local result is labeled case-only and excluded with all descendants
from learning/default retrieval. Historical case examples and prior entry archives are not distributed; optional
same-case local evidence never becomes a generic default.

