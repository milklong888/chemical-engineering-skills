# Flash2 (Two-Phase Flash)

Two-outlet flash separator that splits a feed into vapor and liquid phases at equilibrium.

## Ports

| Port | Direction | Type |
|------|-----------|------|
| F | IN | Feed |
| HS | IN | Heat stream |
| V | OUT | Vapor |
| L | OUT | Liquid |
| WD | OUT | Work duty |
| HS | OUT | Heat stream out |

## Input

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\TEMP` | float | Flash temperature |
| `\Data\Blocks\{name}\Input\PRES` | float | Flash pressure |
| `\Data\Blocks\{name}\Input\DUTY` | float | Specified heat duty |
| `\Data\Blocks\{name}\Input\VFRAC` | float | Specified vapor fraction (0–1) |

> Specify exactly 2 of: temperature, pressure, duty, vapor fraction. Most common: temperature + pressure.

## Output

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Output\B_TEMP` | float | Outlet temperature |
| `\Data\Blocks\{name}\Output\B_PRES` | float | Outlet pressure |
| `\Data\Blocks\{name}\Output\B_VFRAC` | float | Vapor fraction |
| `\Data\Blocks\{name}\Output\QCALC` | float | Calculated heat duty |
| `\Data\Blocks\{name}\Output\QNET` | float | Net duty |
| `\Data\Blocks\{name}\Output\LIQ_RATIO` | float | First liquid / total liquid ratio |

## Typical Setup

1. Place: `place_block(session, 'F1', 'Flash2')`
2. Temperature: `set_value(session, aspen_path='\Data\Blocks\F1\Input\TEMP', value='25', unit='C')`
3. Pressure: `set_value(session, aspen_path='\Data\Blocks\F1\Input\PRES', value='1', unit='atm')`
