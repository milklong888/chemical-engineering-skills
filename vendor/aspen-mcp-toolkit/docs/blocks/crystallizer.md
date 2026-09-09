# Crystallizer

Crystallization model for producing solid crystals from solution. Supports cooling, evaporative, and reactive crystallization.

## Ports

| Port | Direction | Type |
|------|-----------|------|
| F | IN | Feed |
| P | OUT | Product (crystal slurry) |
| V | OUT | Vapor |

## Input

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\TEMP` | float | Temperature |
| `\Data\Blocks\{name}\Input\PRES` | float | Pressure |
| `\Data\Blocks\{name}\Input\DUTY` | float | Heat duty |
| `\Data\Blocks\{name}\Input\MODE` | string | Operating mode |
| `\Data\Blocks\{name}\Input\SALT` | string | Salt component ID |
| `\Data\Blocks\{name}\Input\SOL_METHOD` | string | Saturation calculation method |
| `\Data\Blocks\{name}\Input\VOL` | float | Crystallizer volume |
| `\Data\Blocks\{name}\Input\PROD_RATE` | float | Product flow rate |
| `\Data\Blocks\{name}\Input\OPT_PSD` | string | PSD calculation option |

## Output

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Output\B_TEMP` | float | Calculated temperature |
| `\Data\Blocks\{name}\Output\B_PRES` | float | Calculated pressure |
| `\Data\Blocks\{name}\Output\QCALC` | float | Calculated heat duty |
| `\Data\Blocks\{name}\Output\QNET` | float | Net duty |
| `\Data\Blocks\{name}\Output\VOLUME` | float | Calculated volume |
| `\Data\Blocks\{name}\Output\RES_TIME` | float | Residence time |
| `\Data\Blocks\{name}\Output\B_MASSFLOW` | float | Crystal product flow rate |
| `\Data\Blocks\{name}\Output\VFLOW` | float | Vapor flow rate |
| `\Data\Blocks\{name}\Output\SLURRY_DEN` | float | Magma density |

## Typical Setup

1. Place: `place_block(session, 'CRY1', 'Crystallizer')`
2. Salt: `set_value(session, aspen_path='\Data\Blocks\CRY1\Input\SALT', value='NACL')`
3. Temperature or duty spec.
