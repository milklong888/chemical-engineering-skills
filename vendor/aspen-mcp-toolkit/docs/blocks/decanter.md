# Decanter (Liquid-Liquid Separator)

Liquid-liquid phase separator. Splits a feed into two immiscible liquid phases (no vapor product).

## Ports

| Port | Direction | Type |
|------|-----------|------|
| F | IN | Feed |
| HS | IN | Heat stream |
| L1 | OUT | First liquid |
| L2 | OUT | Second liquid |
| HS | OUT | Heat stream out |

## Input

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\TEMP` | float | Temperature |
| `\Data\Blocks\{name}\Input\PRES` | float | Pressure |
| `\Data\Blocks\{name}\Input\DUTY` | float | Specified heat duty |

## Output

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Output\B_TEMP` | float | Outlet temperature |
| `\Data\Blocks\{name}\Output\B_PRES` | float | Outlet pressure |
| `\Data\Blocks\{name}\Output\QCALC` | float | Calculated heat duty |
| `\Data\Blocks\{name}\Output\QNET2` | float | Net duty |
| `\Data\Blocks\{name}\Output\LIQ_RATIO` | float | First liquid / total liquid ratio |

## When to Use

- Liquid-liquid extraction systems.
- Any two-phase liquid separation (e.g. water + organic solvent).

## Typical Setup

1. Place: `place_block(session, 'DEC1', 'Decanter')`
2. Temperature: `set_value(session, aspen_path='\Data\Blocks\DEC1\Input\TEMP', value='25', unit='C')`
3. Pressure: `set_value(session, aspen_path='\Data\Blocks\DEC1\Input\PRES', value='1', unit='atm')`

## Gotchas

- Requires a property method with LLE (liquid-liquid equilibrium) capability (e.g. NRTL, UNIQUAC).
- No vapor product — if you need V-L-L separation, use Flash3 instead.
