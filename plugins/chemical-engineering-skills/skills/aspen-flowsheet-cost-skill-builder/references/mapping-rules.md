# Mapping Rules

## Rule order

1. Establish the physical process boundary.
2. Read block card, connections, utility mounts, and service context.
3. Propose a physical equipment family from block type.
4. Override the proposal using actual service and package evidence.
5. Enumerate physical auxiliaries and duplicate representations.
6. Assign one versioned method and its source IDs, or leave unresolved.

## Starting candidates

| Aspen block | Candidate physical equipment | Mandatory review |
|---|---|---|
| `HEATER`, `COOLER`, `HEATX` | shell-and-tube, air cooler, furnace, evaporator, or process-process exchanger | service, both temperature sides, U, area, pressure, material; HEATER is not automatically a purchased exchanger |
| `PUMP` | centrifugal, inline, rotary, reciprocating, or vacuum pump | liquid phase, positive head, flow, type, efficiency, train/standby count |
| `COMPR`, `MCOMPR` | centrifugal/reciprocating compressor, fan, or blower | actual inlet volume, power, stages, pressure ratio, train boundary |
| `FLASH`, `FLASH2`, `SEP` | horizontal/vertical vessel or specialized separator | phase flows/densities, residence time, orientation, pressure; SEP may be cyclone/filter/membrane instead |
| `RADFRAC`, `ABSBR` | tray/packed tower plus physical auxiliaries | hydraulics, diameter, height, internals, condenser/reboiler/drum/pump scope |
| `MIXER`, `FSPLIT`, `SPLIT`, `VALVE` | logical routing/bulk item by default | include only with evidence of a physical vessel, agitator, packaged valve station, or pressure-recovery device |
| reactor models | reactor/internal chemistry | exclude from ordinary equipment; route to a separate reactor method |

## Service overrides

- CFB/DFB gas-solid separators map to cyclone/hopper packages, not generic
  vertical vessels.
- A process-process exchanger represented by two duty blocks is one physical
  item unless the PFD proves two shells.
- A distillation/stripper block may expand into shell, internals, condenser,
  reboiler, reflux drum, reflux pump, and bottoms pump. Cost only present items.
- Purchased steam means OPEX and no onsite boiler CAPEX. Onsite generation may
  add a boiler package only when inside the declared boundary.
- Utility film coefficient is not the overall exchanger U.
- Aspen duty/work/flow is a sizing anchor, not a cost.

## Method readiness

Set `mapping_status=reviewed` only when physical family, service, scope,
subtype, and duplicate handling are explicit. Set `source_ids` only to evidence
that supports the exact cost method. Keep unsupported methods as
`method_gap_open`; do not select the closest available curve.

## Procurement Coverage For Towers And Packages

The physical inventory and the chargeable quote lines are different ledgers.
For a tower represented by a tower body, external reboiler, condenser, splitter
and mixer, first issue this **pending mapping**, not an unconditional count of
three separately purchased items:

| Representation | Physical inventory | Separate charge | Evidence still needed |
| --- | --- | --- | --- |
| Tower body | One candidate tower body/internals | Pending | Tower/package inclusion schedule |
| External reboiler | One physical exchanger candidate | Pending; only if not paid through a package | Package exclusions and separate quote scope |
| Condenser | One physical exchanger candidate | Pending; only if not paid through a package | Package exclusions and separate quote scope |
| Splitter/mixer | Logical connection by default | None by default | Actual valve/manifold/equipment evidence if claimed |

Three physical candidates do not establish three independent charge lines.
Do not begin with an unconditional sum of tower + reboiler + condenser and add a
qualification only afterward. A purchased total is defined only after boundary
review: sum each confirmed package once, then add only separately procured items
confirmed absent from every counted package. Formally, `C = sum(C_package_q) +
sum(delta_i * C_separate_i)`, where each `delta_i` is established by that review.
Unknown inclusion means `delta_i` and the total remain unresolved, never an assumed
1 or a fabricated zero. Retain included auxiliaries in the physical inventory.

Before summing a tower/package quote, inspect its inclusion/exclusion schedule:
column shell and internals, condenser, reboiler, reflux drum, pumps/drivers,
controls, spares, installation and delivery basis. A separately drawn auxiliary
may already be paid for in the package. An unknown inclusion is a gap, not proof
that the auxiliary should be added. A shell-only quote requires explicit evidence
before auxiliary prices are added separately.

Add these assignment fields when a row concerns a tower/package or a quote:

- `procurement_role`: `standalone`, `package`, or `included_in_package`.
- `package_scope_status`: `reviewed` only after inspecting the actual schedule.
- `package_scope_source_ids` and `package_scope_locator`: original ledger IDs
  and exact inclusion/exclusion page/table, including evidence of separate scope.
- `covered_equipment_ids`: semicolon-separated inventory IDs for a package,
  including its own ID. Every covered auxiliary stays in the physical inventory.
- `parent_package_id`: populated on every covered auxiliary; its role is
  `included_in_package` and its `scope_class` is `included_in_package_excluded`.

A covered auxiliary cannot also be a separately chargeable candidate. Two package
rows cannot cover the same item. The shared source and procurement audit checks
these relations before either cost layer runs. It checks recorded evidence
identity and ledger consistency; review of the actual quote boundary is still
required and cannot be inferred from a field label.
