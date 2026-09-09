# Evidence routing

## Precedence

Use the narrowest source that directly governs the active equipment and parameter:

1. User-approved project authority and current change ledger.
2. Same-equipment measured data, simulation export, vendor output, or issued drawing.
3. Applicable standard clause/table with confirmed edition, scope, material, pressure, temperature, and geometry basis.
4. Authoritative manual or textbook method.
5. Course or example material for method orientation only.

When sources conflict, stop automatic propagation and record the conflict, affected quantities, and next allowed action.

## Classification

- `direct_reuse`: the clause/value directly applies after scope and unit checks.
- `method_only`: use the equation or workflow, but supply fresh project inputs.
- `software_boundary`: requires same-case software calculation or export.
- `vendor_boundary`: requires supplier curves, internals rating, or certified data.
- `forbidden_transfer`: another equipment, example, obsolete scope, or unverifiable value.

## Source ledger fields

Record `parameter_id`, `symbol`, `meaning`, `value`, `unit`, `basis`, `equipment_tag`, `source_id`, `PDF hash`, `page`, `bbox`, `table/figure asset`, `evidence_class`, `confidence`, `status`, and `downstream_consumers`.

OCR is a retrieval aid. Formula constants, limits, dimensions, and tabulated values from OCR remain provisional until checked against the rendered page or a reliable native/table extraction.

## Boundary examples

- Aspen/RadFrac may establish flows, stage count, duties, pressure profile, and composition basis; it does not certify real tray capacity or mechanical construction.
- Manual hydraulics may establish preliminary diameter and tray checks; it does not replace vendor rating, Column Internals, or an issued drawing.
- A standard may govern allowable geometry/material/detail within scope; it does not supply the project flow rate or choose a proprietary internal.
- Vendor software/output may support capacity and construction for the quoted internal; it cannot be transferred to a different tower or operating case.
