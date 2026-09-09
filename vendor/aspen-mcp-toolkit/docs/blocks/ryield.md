# RYield (Yield Reactor)

Reactor where you specify product yields directly. No reaction mechanism or stoichiometry needed.

## Ports

| Port | Direction | Type |
|------|-----------|------|
| F | IN | Feed |
| HS | IN | Heat stream |
| P | OUT | Product |
| HS | OUT | Heat stream out |

## Input

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\TEMP` | float | Specified temperature |
| `\Data\Blocks\{name}\Input\PRES` | float | Specified pressure |
| `\Data\Blocks\{name}\Input\DUTY` | float | Specified heat duty |
| `\Data\Blocks\{name}\Input\VFRAC` | float | Specified vapor fraction (0–1) |
| `\Data\Blocks\{name}\Input\DELT` | float | Specified temperature change |
| `\Data\Blocks\{name}\Input\MOLE_YIELD\{comp}\MIXED` | float | Yield per unit mass of total feed (non-inert components) |

## Output

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Output\B_TEMP` | float | Outlet temperature |
| `\Data\Blocks\{name}\Output\B_PRES` | float | Outlet pressure |
| `\Data\Blocks\{name}\Output\QCALC` | float | Calculated heat duty |
| `\Data\Blocks\{name}\Output\QNET` | float | Net heat duty |
| `\Data\Blocks\{name}\Output\B_VFRAC` | float | Calculated vapor fraction |
| `\Data\Blocks\{name}\Output\B_IDELT` | float | Calculated temperature change |

## When to Use

- Known product distribution from experimental data.
- Complex processes where detailed kinetics/stoichiometry is unknown (e.g. coal gasification, pyrolysis).

## Yield Setup

MOLE_YIELD is a 2D table (component × substream). The node doesn't exist until rows are inserted.

### Step-by-step:

**1. Insert rows to create the component slots:**

Insert one row per component. The first insert creates 1 slot, the second insert expands to all components automatically:
```
insert_row(session, '\Data\Blocks\R1\Input\MOLE_YIELD')  # first component
set_label(session, '\Data\Blocks\R1\Input\MOLE_YIELD', index=0, label='ETHANOL')

insert_row(session, '\Data\Blocks\R1\Input\MOLE_YIELD')  # triggers expansion to all components
set_label(session, '\Data\Blocks\R1\Input\MOLE_YIELD', index=1, label='ACETICAC')
set_label(session, '\Data\Blocks\R1\Input\MOLE_YIELD', index=2, label='ETHYLACE')
set_label(session, '\Data\Blocks\R1\Input\MOLE_YIELD', index=3, label='WATER')
```

> **Note:** After the second `insert_row`, the table expands to all components. Further `insert_row` calls will error — this is expected.

**2. Set yield values using `{comp}\MIXED` path:**
```
set_value(session, aspen_path='\Data\Blocks\R1\Input\MOLE_YIELD\ETHANOL\MIXED', value='0.1')
set_value(session, aspen_path='\Data\Blocks\R1\Input\MOLE_YIELD\ACETICAC\MIXED', value='0.1')
set_value(session, aspen_path='\Data\Blocks\R1\Input\MOLE_YIELD\ETHYLACE\MIXED', value='0.4')
set_value(session, aspen_path='\Data\Blocks\R1\Input\MOLE_YIELD\WATER\MIXED', value='0.4')
```

## Typical Setup

1. Place: `place_block(session, 'R1', 'RYield')`
2. Temperature: `set_value(session, aspen_path='\Data\Blocks\R1\Input\TEMP', value='800', unit='C')`
3. Pressure: `set_value(session, aspen_path='\Data\Blocks\R1\Input\PRES', value='1', unit='atm')`
4. Set yields following the steps above.

## Gotchas

- RYield does **NOT** use reaction sets — yields are specified directly.
- MOLE_YIELD is "yield per unit mass of total feed" — Aspen will normalize if values don't maintain mass balance.
- The `YIELD` node is for a user-supplied Fortran subroutine name, NOT for setting yield values.
- MOLE_YIELD requires `insert_row` before values can be set — the node is None until rows are created.
- After 2 `insert_row` calls, the table auto-expands to all components. Additional inserts will error.
- Use `{comp}\MIXED` path format to set values (e.g. `MOLE_YIELD\ETHANOL\MIXED`).
