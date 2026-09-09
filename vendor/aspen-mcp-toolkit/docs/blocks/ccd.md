# CCD (Counter-Current Decanter)

Multi-stage counter-current decantation (washing) model. Separates solids from liquids through successive stages of settling and washing.

## Ports

| Port | Direction | Type |
|------|-----------|------|
| F | IN | Feed (slurry) |
| W | IN | Wash water |
| OF | OUT | Overflow (clarified liquid) |
| UF | OUT | Underflow (thickened slurry) |

## Input

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\NSTAGE` | int | Number of stages |
| `\Data\Blocks\{name}\Input\PRES` | float | Operating pressure |
| `\Data\Blocks\{name}\Input\TAMB` | float | Ambient temperature |

## Output

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Output\FEED_FLOW` | float | Top stage feed mass flow |
| `\Data\Blocks\{name}\Output\FEED_LFLOW` | float | Bottom stage feed mass flow |
| `\Data\Blocks\{name}\Output\TOP_LFLOW` | float | Top stage product mass flow |
| `\Data\Blocks\{name}\Output\PROD_LFLOW` | float | Bottom stage product mass flow |
| `\Data\Blocks\{name}\Output\TOP_TEMP` | float | Top stage temperature |
| `\Data\Blocks\{name}\Output\BOTTOM_TEMP` | float | Bottom stage temperature |
| `\Data\Blocks\{name}\Output\DUTY` | float | Total stage duty |

## Typical Setup

1. Place: `place_block(session, 'CCD1', 'CCD')`
2. Stages: `set_value(session, aspen_path='\Data\Blocks\CCD1\Input\NSTAGE', value='5')`
3. Pressure: `set_value(session, aspen_path='\Data\Blocks\CCD1\Input\PRES', value='1', unit='atm')`

## Gotchas

- Used in minerals processing (hydrometallurgy) and chemical engineering for solid-liquid separation.
- Requires proper solids substream configuration.
