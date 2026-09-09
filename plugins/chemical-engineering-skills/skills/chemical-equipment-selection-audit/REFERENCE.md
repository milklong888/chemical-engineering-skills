# Chemical Equipment Selection Audit Reference

## Formula Families

| Family | Formula or method | Typical equipment | Human decision required |
| --- | --- | --- | --- |
| Nozzle required diameter | `d=sqrt(4Q/(pi*u))` | towers, exchangers, reactors, tanks | phase, target velocity, Q units |
| Selected-pipe velocity | `u=4Q/(pi*d_i^2)` | all nozzles | standard pipe, corrosion allowance, wall thickness |
| Design pressure factor | `P_design=f_source(P_op)` | vessels/reactors/exchangers | applicable standard/document rule |
| Design pressure increment | `P_design=Pmax+ΔP_source` | some exchanger/vessel cases | source rule must be cited before formal use |
| Design temperature margin | `T_design-T_max` | vessels/exchangers/reactors | margin range and material limits |
| Tower holdup | `(Q*t)/(piD^2/4)` | towers, reflux drums, buffers | residence time and layout override |
| Tower height sum | `HD+HB+HR+packing+head+skirt` | packed towers | source of each height component |
| Shell thickness | `PDi/(2sigma phi-P)` | cylindrical shells | allowable stress, weld efficiency, SW6 boundary |
| Head thickness | `PDi/(2sigma phi-0.5P)` | ellipsoidal heads | same as shell thickness |
| Stream balance | inlet minus outlets | columns/separators | mass/mole conserved; volume may not be |
| Column Internals table | capacity, packing height, pressure drop ranges | towers | Aspen export remains formal evidence |
| Heat transfer | Nu, U, A, margin | exchangers/fixed-bed reactors | property averaging, area basis, heat-side assumptions |
| Ergun pressure drop | packed-bed dP | fixed beds | particle size, voidage, superficial velocity |
| Arrhenius audit | `ln(k)=ln(A)-E/(RT)` | kinetics arithmetic only | not formal Aspen kinetics without freeze chain |

## Calculation Ledger Schema

Each calculation row should include:

- `module`
- `item`
- `source_location`
- `formula`
- `input_values`
- `value`
- `unit`
- `document_value_raw`
- `tolerance`
- `pass_check`
- `reliability_class`
- `status`
- `note`

Never hide a mismatch by widening tolerance. Add a root-cause audit row or report.

## Evidence Classes

| Class | Meaning | Typical status |
| --- | --- | --- |
| A | Explicit formula reproduced | `reproduced` |
| B | Pre-selection/rounded/software-boundary step reproduced | `reproduced`, `software_dependent`, `informational` |
| C | External software evidence required | listed in boundary report |
| D | Kinetics provisional | `provisional` or `blocked` |
| E | Symbolic/catalog selection | listed in boundary report |

## Standard Source Subtypes

| Subtype | Meaning | Action |
| --- | --- | --- |
| `direct_reuse` | Same standard/version/input/unit can be checked by formula or table | Cite as standard source only after table/page evidence is recorded |
| `method_only` | Standard/manual/textbook supplies workflow or field meanings only | Keep project values from Aspen/document/manual defaults |
| `software_boundary` | Formal value requires EDR, SW6, Column Internals, or equivalent | Do not replace software evidence with handbook arithmetic |
| `vendor_boundary` | Formal value requires manufacturer data or curves | Keep as evidence gap until vendor source is attached |
| `forbidden_transfer` | Example, course-design, graduation-design, or other-equipment value | Never migrate as project default |

## Report Set

A mature work package should contain:

- Module split and task list.
- Calculation ledger / scripted recalc result.
- Section-level precision table.
- Section-level parameter source table.
- Manual/default parameter list.
- Aspen-required parameter list.
- Reliability boundary list.
- Device tag mapping table.
- Mismatch/root-cause audit report.
- Generalization and manual-decision rules.
- Knowledge graph README and router.

## Mismatch Root-Cause Checklist

1. Re-read original source cells.
2. Verify extraction output.
3. Check unit conversions.
4. Recompute with independent small calculations.
5. Cross-check within the same document.
6. Cross-check supplemental documents.
7. Classify cause and keep `review` if evidence is incomplete.

## Same-Case Interface

User project ledgers supply equipment IDs, source values, current standards,
calculation results and any conflicting readings. Local graphs under
`{CHEM_WORKSPACE}` are optional user assets, not distributed examples.

Retain the source-value/unit/conversion/Aspen-card chain and classify unresolved
kinetics, mechanics or vendor values as provisional. No historical tag map,
private temperature correction or case verdict is supplied as a default.

