# Filter (Rotary/Belt/Disc Filter)

Vacuum or pressure filter model. Supports drum, belt, and disc filter types with filtration, washing, and deliquoring stages.

## Ports

| Port | Direction | Type |
|------|-----------|------|
| F | IN | Feed (slurry) |
| SOL | OUT | Solids (filter cake) |
| FILT | OUT | Filtrate |

## Input

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\TYPE` | string | Filter type |
| `\Data\Blocks\{name}\Input\MODE` | string | Operating mode |
| `\Data\Blocks\{name}\Input\MODEL` | string | Filtration model |
| `\Data\Blocks\{name}\Input\SOLID_SPLIT` | float | Fraction of solids to solid outlet |
| `\Data\Blocks\{name}\Input\FLUID_SPLIT` | float | Fraction of liquid to liquid outlet |
| `\Data\Blocks\{name}\Input\DIAM` | float | Drum/disc diameter |
| `\Data\Blocks\{name}\Input\WIDTH` | float | Drum width |
| `\Data\Blocks\{name}\Input\REVS` | float | Drum speed |
| `\Data\Blocks\{name}\Input\PDROP` | float | Filtration pressure drop |
| `\Data\Blocks\{name}\Input\CAKE_THICK` | float | Cake thickness |
| `\Data\Blocks\{name}\Input\POROSITY` | float | Cake porosity |

## Output

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Output\TOT_AREA` | float | Total filter area |
| `\Data\Blocks\{name}\Output\PDROP_CALC` | float | Calculated pressure drop |
| `\Data\Blocks\{name}\Output\CAKE_THICK_C` | float | Maximum cake thickness |
| `\Data\Blocks\{name}\Output\POROSITY_C` | float | Cake porosity |
| `\Data\Blocks\{name}\Output\CAKE_SFRAC` | float | Mass fraction of solids in cake |
| `\Data\Blocks\{name}\Output\DIAM_CALC` | float | Calculated drum diameter |
| `\Data\Blocks\{name}\Output\SRECOVERY` | float | Fraction of solids to solid outlet |
| `\Data\Blocks\{name}\Output\LRECOVERY` | float | Fraction of liquid to liquid outlet |
| `\Data\Blocks\{name}\Output\QCALC` | float | Heat duty |

## Typical Setup

1. Place: `place_block(session, 'FLT1', 'Filter')`
2. Type and mode selection.
3. Set geometry and operating conditions.
