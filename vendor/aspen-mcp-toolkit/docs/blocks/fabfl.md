# FabFl (Fabric Filter / Baghouse)

Fabric filter (baghouse) for removing particulate matter from gas streams.

## Ports

| Port | Direction | Type |
|------|-----------|------|
| F | IN | Feed (gas + solids) |
| GAS | OUT | Clean gas |
| SOL | OUT | Collected solids |

## Input

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\METHOD` | string | Model |
| `\Data\Blocks\{name}\Input\MODE` | string | Operating mode |
| `\Data\Blocks\{name}\Input\SOLID_SPLIT` | float | Fraction of solids to solid outlet |
| `\Data\Blocks\{name}\Input\SHARPNESS` | float | Separation sharpness |
| `\Data\Blocks\{name}\Input\NCELLS` | int | Number of cells |
| `\Data\Blocks\{name}\Input\NBAGS` | int | Number of bags per cell |
| `\Data\Blocks\{name}\Input\DIAM` | float | Bag diameter |
| `\Data\Blocks\{name}\Input\AVG_PDROP` | float | Average pressure drop |
| `\Data\Blocks\{name}\Input\FILT_TIME` | float | Filtration time |

## Output

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Output\EFF` | float | Overall collection efficiency |
| `\Data\Blocks\{name}\Output\TOT_AREA` | float | Total filter area |
| `\Data\Blocks\{name}\Output\TIME` | float | Filtration time |
| `\Data\Blocks\{name}\Output\VELOCITY` | float | Filtration velocity |
| `\Data\Blocks\{name}\Output\PDROP` | float | Average pressure drop |
| `\Data\Blocks\{name}\Output\THICKNESS` | float | Maximum cake height |
| `\Data\Blocks\{name}\Output\SOLD_RECOV` | float | Fraction of solids collected |
| `\Data\Blocks\{name}\Output\D50` | float | D50 of separation curve |

## Typical Setup

1. Place: `place_block(session, 'BH1', 'FabFl')`
2. Set model and mode.
3. Specify bag geometry and operating conditions.
