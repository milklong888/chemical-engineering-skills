# Crusher (Size Reduction)

Crushes or grinds solid particles to reduce particle size. Supports jaw, gyratory, cone, roll, hammer, and impact crusher models.

## Ports

| Port | Direction | Type |
|------|-----------|------|
| F | IN | Feed |
| P | OUT | Product (crushed) |

## Input

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\PSD_CALC_MET` | string | Outlet PSD calculation method |
| `\Data\Blocks\{name}\Input\TYPE` | string | Crusher type |
| `\Data\Blocks\{name}\Input\SEL_FUN` | string | Selection function model |
| `\Data\Blocks\{name}\Input\BREAK_FUN` | string | Breakage function model |
| `\Data\Blocks\{name}\Input\DISTR_FUN` | string | Distribution function |
| `\Data\Blocks\{name}\Input\MODE` | string | Operating mode |
| `\Data\Blocks\{name}\Input\DIAM` | float | Maximum particle diameter |
| `\Data\Blocks\{name}\Input\POWER_SPEC` | float | Power specification |
| `\Data\Blocks\{name}\Input\MASS_POWER` | float | Specific power |

## Output

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Output\POWER` | float | Calculated power |
| `\Data\Blocks\{name}\Output\INLET_D80` | float | Inlet D80 particle diameter |
| `\Data\Blocks\{name}\Output\OUTLET_D80` | float | Outlet D80 particle diameter |
| `\Data\Blocks\{name}\Output\INLET_D50` | float | Inlet D50 particle diameter |
| `\Data\Blocks\{name}\Output\OUTLET_D50` | float | Outlet D50 particle diameter |
| `\Data\Blocks\{name}\Output\FP_D80` | float | Size reduction ratio (D80) |
| `\Data\Blocks\{name}\Output\FP_D50` | float | Size reduction ratio (D50) |
| `\Data\Blocks\{name}\Output\SAUTER_IN` | float | Sauter mean diameter (inlet) |
| `\Data\Blocks\{name}\Output\SAUTER_OUT` | float | Sauter mean diameter (outlet) |

## Typical Setup

1. Place: `place_block(session, 'CR1', 'Crusher')`
2. Type: `set_value(session, aspen_path='\Data\Blocks\CR1\Input\TYPE', value='JAW')`
3. Set maximum particle diameter or power spec.
