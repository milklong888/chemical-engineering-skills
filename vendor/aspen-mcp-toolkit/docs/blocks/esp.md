# ESP (Electrostatic Precipitator)

Electrostatic precipitator for removing fine particles from gas streams using electric fields.

## Ports

| Port | Direction | Type |
|------|-----------|------|
| F | IN | Feed (gas + solids) |
| GAS | OUT | Clean gas |
| SOL | OUT | Collected solids |

## Input

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\TYPE` | string | ESP type (plate or tube) |
| `\Data\Blocks\{name}\Input\MODE` | string | Operating mode |
| `\Data\Blocks\{name}\Input\MODEL` | string | Calculation method |
| `\Data\Blocks\{name}\Input\SOLID_SPLIT` | float | Fraction of solids to solid outlet |
| `\Data\Blocks\{name}\Input\SHARPNESS` | float | Separation sharpness |
| `\Data\Blocks\{name}\Input\EFF` | float | Separation efficiency |
| `\Data\Blocks\{name}\Input\HT_PLATE` | float | Plate height |
| `\Data\Blocks\{name}\Input\LEN_PLATE` | float | Plate length |
| `\Data\Blocks\{name}\Input\NPLATE` | int | Number of plates |
| `\Data\Blocks\{name}\Input\VOLT_LOAD` | float | Loading area voltage |
| `\Data\Blocks\{name}\Input\VOLT_PRECIP` | float | Precipitation area voltage |

## Output

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Output\SOLD_RECOV` | float | Fraction of solids collected |
| `\Data\Blocks\{name}\Output\D50` | float | D50 of separation curve |
| `\Data\Blocks\{name}\Output\EFF_OUT` | float | Overall collection efficiency |
| `\Data\Blocks\{name}\Output\VOLTAGE` | float | Calculated corona voltage |
| `\Data\Blocks\{name}\Output\POWER` | float | Power requirement |
| `\Data\Blocks\{name}\Output\AREA_PRECIP` | float | Precipitation area |
| `\Data\Blocks\{name}\Output\PDRP` | float | Calculated pressure drop |

## Typical Setup

1. Place: `place_block(session, 'ESP1', 'ESP')`
2. Type and mode selection.
3. Set geometry or efficiency target.
