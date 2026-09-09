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
