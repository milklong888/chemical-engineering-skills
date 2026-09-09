# Aspen Source Taskbook And Gate Protocol

Use this protocol before the first Aspen mutation, before replacing a scaffold
with a rigorous island, and before final delivery. It fixes the common failure
where the process runs but the official taskbook, buyer note, or user-added
constraint was only partly read.

## Gate Families

Use three gate families plus one overlay:

1. Aspen inherent gates.
   Required Input, Control Panel/history, block/calculator/spec status, run
   status, clean reopen, and same-version exports. The Control Panel is the
   first authority for failed runs, warnings, bad blocks, and convergence
   repair.
2. Source/taskbook gates.
   Official design book, assignment file, buyer requirement, report text,
   standards excerpt, drawings, and approved change-offset rows. These own
   capacity, purity, recovery, equipment families, pressure/temperature limits,
   recycle/purge requirements, deliverables, and grading gates.
3. Physical common-sense gates.
   Mass and element closure, stoichiometric limits, phase/T/P sanity, pressure
   devices, heat-duty sign and scale, recycle/makeup logic, separation
   feasibility, and terminal-stream classification.
4. User-adjustment overlay.
   Fresh user instructions may tighten a gate or authorize an offset. If they
   conflict with source text, update the project change-offset table before
   changing Aspen or the report. User adjustments do not override Aspen
   Required Input, Control Panel, physics, or default-precision red lines.

## Property-Method Freeze

Choose the property method from the real module service before any scaffold,
reactor, tower, flash, separator, recycle closure, Calculator, Design Spec,
Sensitivity, or Optimization. Record:

```text
module_or_section:
component_family:
temperature_pressure_window:
expected_phases:
polarity_nonideality:
Henry_electrolyte_association_or_acid_gas_need:
azeotrope_LLE_VLL_or_solvent_behavior:
binary_parameter_or_PCES_regression_support:
transport_property_need_for_HX_hydraulics:
selected_method:
status: accepted/provisional/blocked
evidence:
```

After the row is accepted, freeze it. A later property-method change is a major
model mutation: update the change-offset table, explain the physical reason,
rerun affected islands/recycles/towers/hydraulics, and quarantine old results.
Do not change property method just to make convergence, product purity, or
hydraulics look better.

If the property row is `provisional` or `blocked`, the associated module cannot
be promoted as accepted. Equipment tuning cannot hide a property-method gap.

## Source/Taskbook Completeness

Build a source ledger before mutating Aspen. Do not rely on memory or a single
skim of the taskbook.

Pass A: direct extraction.

```text
document_inventory:
source_route_and_block_intent:
feeds_and_capacity_basis:
products_byproducts_waste_and_purity_targets:
reaction_network_and_conversion_or_kinetics_requirements:
separation_targets_and_equipment_family_requirements:
recycle_purge_makeup_and_solvent_logic:
pressure_temperature_utility_and_material_constraints:
tower_hydraulic_or_equipment_design_requirements:
deliverables_and_grading_gates:
user_adjustments_and_approved_offsets:
ambiguous_missing_or_unread_items:
```

Each row needs a source file/page or message, extracted value or requirement,
unit/basis, Aspen destination or report destination, status, and next allowed
action.

For recycle/purge/makeup/solvent rows, require a connectivity disposition:

```text
source intent:
aspen stream(s):
upstream source unit:
downstream return unit or boundary:
splitter_purge_or_pressure_device:
tear_or_convergence_setup:
disposition: closed / open_boundary / blocked
evidence:
```

Do not accept recycle-named boundary streams as closure evidence. Before final
delivery, compare the exported flowsheet connectivity against this disposition
ledger. A full-flow claim fails the source/taskbook gate if the taskbook says a
stream recycles but the Aspen case only sends it to an unconnected boundary,
unless the active change-offset table explicitly approves that boundary.

For difficult recycle rows, use a staged closure discipline. First run the
equivalent open-boundary/open-loop case until the downstream towers or reactors
meet their material gates. Then reconnect the source-required recycle path with
explicit split/purge/tear evidence, seeding tear streams from the accepted
open-loop outputs. If the first closed iterations make downstream blocks fail
before the loop settles, add warm-start estimates for the key intermediate
streams from the accepted open-loop or previous closed solution. The closed
case still needs its own exported connectivity, block-status, Control
Panel/history, and product/recovery evidence; the open-loop pass is only an
initialization gate.

Pass B: reverse checklist search.

- Search the original documents for terms such as product, purity, capacity,
  recovery, conversion, selectivity, pressure, temperature, utility, recycle,
  purge, solvent, inhibitor, tower, column, hydraulic, equipment, standard,
  deliverable, and appendix.
- Search for source-complete topology items that do not always affect product
  purity directly: feed pretreatment, drying, filtration, adsorption, impurity
  removal, reactor outlet cooler/condenser/quench, phase separator, gas
  recovery, vent or purge treatment, hydrogen/fuel/utilities split, inhibitor
  or polymerization prevention, heavy residue, wastewater, solid waste,
  off-spec/light-aromatics waste, named preheater, and required product-tower
  count. Add a ledger row for each required block and terminal stream.
- Compare the hit list against the source ledger.
- Mark any missed or OCR-uncertain item as `provisional` or `blocked`; do not
  silently continue if the item could change the model.
- Recheck user-added requirements and buyer gates against the same ledger.

A final source/taskbook pass must compare the required topology rows to the
same-version exported Aspen connectivity, not only to product stream metrics.
If a candidate hits capacity/purity but lacks source-required auxiliary units,
waste streams, inhibitor feeds, or product-stage count, demote it to a
capacity-closed baseline and continue from a source-complete branch.

For PDF/DOCX sources, render or extract the relevant pages when a table, figure,
formula, or footnote could affect Aspen inputs. Low-confidence OCR or garbled
tables are blockers for the affected row until verified another way.

## Two-Pass Verification

Run two verification passes:

1. Pre-mutation verification.
   Before Aspen edits, verify source/taskbook rows, property-method freeze
   rows, and change-offset rows. Every row is `accepted`, `provisional`, or
   `blocked`.
2. Pre-delivery verification.
   Re-read the source ledger and compare it to the same-version Aspen exports,
   Control Panel/history, status files, stream results, physical-plausibility
   ledger, migrated-path evidence, and user adjustments. Repeat the gate check
   after any late tower, recycle, pressure, property, or report change.

If the two passes disagree, the later edit is not deliverable until the ledger
and Aspen evidence are reconciled.

## Final Gate Statement

Every completed Aspen handoff must include a compact gate statement so the user
can audit the claim quickly:

```text
Property-method freeze:
Aspen inherent gate:
Source/taskbook gate:
Physical common-sense gate:
User-adjustment/offset gate:
Second-pass verification:
Remaining provisional or blocked rows:
```

Use evidence paths, not vague assurance. If a gate is incomplete, say exactly
which row is missing and what the next allowed action is.
