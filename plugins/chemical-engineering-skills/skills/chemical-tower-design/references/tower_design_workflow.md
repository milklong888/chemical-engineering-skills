# Tower design workflow

## 1. Freeze the task

Create a tower identity card: tag, service, feed/product targets, phase behavior, capacity basis, turndown/overload cases, operating and design pressure/temperature, materials/corrosion basis, and user-approved deviations. Separate confirmed, calculated, selected, provisional, vendor, and unresolved values.

## 2. Process design basis

Confirm property method and vapor-liquid equilibrium suitability. Freeze stage count, feed stage, reflux/solvent ratio, condenser/reboiler duties, pressure profile, compositions, mass and molar flows, and controlling load cases. Preserve the difference between theoretical stages and real trays or packing height.

## 3. Select internal family

Choose tray or packing family from fouling, foaming, corrosiveness, pressure drop, capacity, turndown, maintenance, and separation efficiency. Mark proprietary capacity factors, pressure-drop correlations, and construction details as vendor boundaries.

## 4. Diameter and usable area

Calculate the governing vapor/liquid traffic and preliminary diameter. Close the plan area explicitly:

`total cross-section = active bubbling/packing area + downcomer area + receiving area + inactive/edge areas + other occupied areas`

Do not label total clear circle area as active area. For a single-pass tray, identify inlet/receiving and outlet/downcomer sides consistently in calculations and drawings. Recalculate active area when chord widths, apron/receiving geometry, edge strips, support rings, calming zones, or inactive areas change.

## 5. Tray or packing hydraulics

For trays, reconcile hole/valve area, open-area ratio, weir geometry, liquid height, residence time, downcomer backup, pressure drop, entrainment, weeping/dumping, and flooding margin on the same geometry and load case. For packing, reconcile capacity, liquid distribution, pressure drop, HETP/HTU-NTU, distributor limits, and bed segmentation.

Use a case matrix for normal, minimum, maximum, startup-relevant, and upset/design cases. Do not mix mass and molar traffic or actual and standard volume.

Generate or refresh a load-performance envelope for every hydraulic section and governing case. Its operating point and boundary curves are downstream calculation products, not decorative figures; geometry, traffic, pressure, area, weir/hole/packing, or tray-spacing changes make the corresponding plot stale.

## 6. Height and mechanical envelope

Convert separation requirements to real tray count or packed height, then add disengagement, feed, draw, manway, support, distributor/redistributor, sump, and head allowances. Reconcile shell diameter, tangent-to-tangent height, heads, skirts/lugs, platforms, nozzles, manways, supports, and internals installation/removal clearances.

## 7. Pressure feedback

Sum internal, distributor, demister, nozzle, and static-head pressure drops. Feed the accepted pressure profile back to the process model when material balance, equilibrium, duty, or product targets are pressure-sensitive. Iterate until process and equipment bases agree.

## 8. Calculations and equation chains

Write each derivation as:

`target = symbolic formula = substituted expression = numeric result unit`

Define symbols once near first use. A calculation sequence should read as a causal chain, not a list of isolated numbers. If an input comes from a prior result, cite that result. If a selected standard size replaces a calculated minimum, show both and propagate the selected value.

## 9. Engineering figures

Prepare restrained, dimensioned line drawings: plan layout, section/elevation, tray/packing detail, nozzle orientation, and support/interface detail as needed. Use standard line weights, hatching, centerlines, leaders, and dimension placement. Avoid decorative frames and duplicate narrative. Data charts may remain unchanged if their data and method are unchanged.

## 10. Dependency ledger

For every changed input, list downstream consumers and mark them stale until recalculated. Typical dependency groups:

| Upstream change | Required downstream review |
|---|---|
| pressure/profile | equilibrium, traffic, density, duty, diameter, pressure drop |
| stage/reflux/feed location | duties, traffic envelope, section load-performance plots, tray count/height, nozzles |
| diameter | total area, chord areas, active area, hole count, flooding/weeping, section load-performance plots, shell/mechanics, mass/cost basis, drawings |
| downcomer or receiving geometry | active area, residence, backup, weir loading, hole layout, section load-performance plots, drawings |
| tray spacing | entrainment/flooding basis, section load-performance plots, tower height, manways/supports, mass/cost basis, drawings |
| selected standard size/material | thickness/mass, flanges/nozzles/supports, fabrication or correlation cost basis, specification sheets |
| shell height, tray count, internals or support change | material takeoff, mass, course-design/correlation cost, lifting/support interfaces, drawings and specification |

## 11. Independent review

An independent chemical-equipment reviewer should query the same knowledge graph and challenge: source applicability, area closure, controlling load case, unit/basis conversions, selected-versus-calculated propagation, pressure feedback, vendor/software boundaries, and drawing/calculation consistency. Resolve every high-risk finding before delivery; retain lower-risk OCR uncertainties in a review ledger.
