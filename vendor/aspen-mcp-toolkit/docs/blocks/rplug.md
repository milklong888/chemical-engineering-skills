# RPlug (Plug Flow Reactor)

Tubular plug flow reactor with rigorous kinetics. Requires an external reaction set (POWERLAW or LHHW).

## Ports

| Port | Direction | Type |
|------|-----------|------|
| F | IN | Feed |
| C | IN | Coolant in |
| P | OUT | Product |
| C | OUT | Coolant out |
| HS | OUT | Heat stream out |

## Input

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\TYPE` | string | Reactor type: `ADIABATIC`, `CONSTANT-T`, `T-SPEC`, `COOLANT` |
| `\Data\Blocks\{name}\Input\LENGTH` | float | Reactor length |
| `\Data\Blocks\{name}\Input\DIAM` | float | Reactor diameter |
| `\Data\Blocks\{name}\Input\NTUBE` | int | Number of tubes (default 1) |
| `\Data\Blocks\{name}\Input\PDROP` | float | Pressure drop at reactor inlet |
| `\Data\Blocks\{name}\Input\PHASE` | string | Valid phases: `V` (Vapor-Only), `L` (Liquid-Only), `V-L` (Vapor-Liquid) |
| `\Data\Blocks\{name}\Input\NPHASE` | int | Number of phases (1 or 2) |
| `\Data\Blocks\{name}\Input\RXN_ID` | table | Selected reaction set(s) |

### Catalyst Settings

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\CAT_PRESENT` | string | `YES` or `NO` — enables catalyst |
| `\Data\Blocks\{name}\Input\BED_VOIDAGE` | float | Bed voidage (e.g. 0.9) |
| `\Data\Blocks\{name}\Input\CAT_RHO` | float | Particle density (e.g. 900 kg/cum) |
| `\Data\Blocks\{name}\Input\DIA_PART` | float | Particle diameter (default 0.1 meter) |
| `\Data\Blocks\{name}\Input\SPHERICITY` | float | Shape factor (default 1.0) |
| `\Data\Blocks\{name}\Input\IGN_CAT_VOL` | string | Ignore catalyst volume in rate/residence time: `YES` or `NO` |

> **TYPE is required** — must be set explicitly (e.g. `ADIABATIC`). Without it, the block is incomplete.
> Reactor geometry (LENGTH + DIAM) is required. NTUBE defaults to 1 if not set.
> **CAT_RHO vs RHO_CAT**: `CAT_RHO` is the required particle density field. `RHO_CAT` also exists but does NOT satisfy the input check. Always use `CAT_RHO`.

## Output

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Output\QCALC` | float | Heat duty |
| `\Data\Blocks\{name}\Output\TMIN` | float | Minimum reactor temperature |
| `\Data\Blocks\{name}\Output\TMAX` | float | Maximum reactor temperature |
| `\Data\Blocks\{name}\Output\RES_TIME` | float | Residence time |
| `\Data\Blocks\{name}\Output\COOLANT_TIN` | float | Thermal fluid inlet temperature |
| `\Data\Blocks\{name}\Output\COOLANT_VIN` | float | Thermal fluid inlet vapor fraction |

## Assigning a Reaction Set

RXN_ID starts empty — must `insert_row` first, then set the value:
```
insert_row(session, '\Data\Blocks\R1\Input\RXN_ID')
set_value(session, aspen_path='\Data\Blocks\R1\Input\RXN_ID\#0', value='RXN1')
```

## Typical Setup

1. Place block: `place_block(session, 'R1', 'RPlug')`
2. Set type: `set_value(session, aspen_path='\Data\Blocks\R1\Input\TYPE', value='ADIABATIC')`
3. Set length: `set_value(session, aspen_path='\Data\Blocks\R1\Input\LENGTH', value='12', unit='meter')`
4. Set diameter: `set_value(session, aspen_path='\Data\Blocks\R1\Input\DIAM', value='1', unit='meter')`
5. Set catalyst: `set_value(session, ...\CAT_PRESENT', value='YES')`, then `BED_VOIDAGE`, `CAT_RHO`, `DIA_PART`, `SPHERICITY`
6. Create reaction set: `add_reaction_set(session, 'RXN1', 'POWERLAW')`
7. Add reaction: `add_reaction(session, 'RXN1', 1, reactants={...}, products={...}, phase='V')`
8. Set kinetics: `set_value(session, aspen_path='\Data\Reactions\Reactions\RXN1\Input\PRE_EXP\1', value='51.55')`
9. Assign to block: `insert_row(session, '\Data\Blocks\R1\Input\RXN_ID')` then `set_value(...\RXN_ID\#0', value='RXN1')`

## Gotchas

- **TYPE must be set** — `ADIABATIC`, `CONSTANT-T`, `T-SPEC`, or `COOLANT`. Block is incomplete without it.
- Must specify reactor geometry (length + diameter).
- Requires kinetic reaction set (POWERLAW or LHHW).
- **RXN_ID starts empty** — must `insert_row` before `set_value`. Unlike RCSTR, there is no pre-existing `#0` element.
- **Use `CAT_RHO` for particle density**, not `RHO_CAT`. Both fields exist but only `CAT_RHO` satisfies the input check.
- Has coolant ports for heat exchange — can model co-current or counter-current cooling.
