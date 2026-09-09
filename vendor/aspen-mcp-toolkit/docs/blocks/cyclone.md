# Cyclone (Gas-Solid Cyclone)

Cyclone separator for removing solid particles from a gas stream using centrifugal force.

## Ports

| Port | Direction | Type |
|------|-----------|------|
| F | IN | Feed (gas + solids) |
| GAS | OUT | Clean gas |
| SOL | OUT | Collected solids |

## Input

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\MODEL` | string | Cyclone model |
| `\Data\Blocks\{name}\Input\MODE` | string | Operating mode (design/rating) |
| `\Data\Blocks\{name}\Input\METHOD` | string | Calculation method |
| `\Data\Blocks\{name}\Input\TYPE` | string | Cyclone type |
| `\Data\Blocks\{name}\Input\SOLID_SPLIT` | float | Fraction of solids to solid outlet |
| `\Data\Blocks\{name}\Input\SHARPNESS` | float | Separation sharpness |
| `\Data\Blocks\{name}\Input\EFF` | float | Separation efficiency |
| `\Data\Blocks\{name}\Input\DES_PDROP` | float | Design pressure drop |
| `\Data\Blocks\{name}\Input\LEN_CYLINDER` | float | Cylinder length |
| `\Data\Blocks\{name}\Input\LEN_CONE` | float | Cone length |
| `\Data\Blocks\{name}\Input\DIAM_OVER` | float | Overflow (vortex finder) diameter |
| `\Data\Blocks\{name}\Input\DIAM_UNDER` | float | Underflow diameter |

## Output

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Output\SOLD_RECOV` | float | Fraction of solids collected |
| `\Data\Blocks\{name}\Output\D50` | float | D50 of separation curve |
| `\Data\Blocks\{name}\Output\PDROP` | float | Calculated pressure drop |
| `\Data\Blocks\{name}\Output\DIAM_CYL` | float | Calculated cylinder diameter |
| `\Data\Blocks\{name}\Output\EFF_OUT` | float | Calculated efficiency |
| `\Data\Blocks\{name}\Output\NUMBER` | float | Calculated number of cyclones |

## Typical Setup

1. Place: `place_block(session, 'CYC1', 'Cyclone')`
2. Mode and method selection.
3. Set geometry or desired efficiency/pressure drop.
