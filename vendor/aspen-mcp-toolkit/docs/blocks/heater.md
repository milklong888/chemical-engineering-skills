# Heater (Heater / Cooler)

Simple heater or cooler. Specify outlet conditions or heat duty to determine the exit stream state.

## Ports

| Port | Direction | Type |
|------|-----------|------|
| F | IN | Feed |
| HS | IN | Heat stream |
| P | OUT | Product |
| WD | OUT | Work duty |
| HS | OUT | Heat stream out |

## Input

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\TEMP` | float | Specified temperature |
| `\Data\Blocks\{name}\Input\PRES` | float | Specified pressure |
| `\Data\Blocks\{name}\Input\DUTY` | float | Specified heat duty |
| `\Data\Blocks\{name}\Input\VFRAC` | float | Specified vapor fraction (0–1) |
| `\Data\Blocks\{name}\Input\DELT` | float | Temperature change |
| `\Data\Blocks\{name}\Input\DEGSUP` | float | Degrees of superheating |
| `\Data\Blocks\{name}\Input\DEGSUB` | float | Degrees of subcooling |
| `\Data\Blocks\{name}\Input\DPPARM` | float | Pressure-drop correlation parameter |

> Specify exactly 2 of: temperature, pressure, duty, vapor fraction. Most common combination: temperature + pressure.

> Alternative specs — DELT (temperature change), DEGSUP (superheating), or DEGSUB (subcooling) — can replace TEMP when you want to specify relative to the inlet condition.

## Output

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Output\B_TEMP` | float | Calculated temperature |
| `\Data\Blocks\{name}\Output\B_PRES` | float | Calculated pressure |
| `\Data\Blocks\{name}\Output\B_VFRAC` | float | Calculated vapor fraction |
| `\Data\Blocks\{name}\Output\QCALC` | float | Calculated heat duty |
| `\Data\Blocks\{name}\Output\QNET` | float | Net duty (includes heat stream contributions) |
| `\Data\Blocks\{name}\Output\LIQ_RATIO` | float | First liquid / total liquid ratio |

## Typical Setup

1. Place: `place_block(session, 'H1', 'Heater')`
2. Temperature: `set_value(session, aspen_path='\Data\Blocks\H1\Input\TEMP', value='40', unit='C')`
3. Pressure: `set_value(session, aspen_path='\Data\Blocks\H1\Input\PRES', value='1.5', unit='atm')`

## Gotchas

- Specifying more than 2 conditions will over-specify the block and cause errors.
- If a heat stream is connected, its duty counts toward the energy balance — set DUTY=0 if you want the heat stream to be the only heat source.
