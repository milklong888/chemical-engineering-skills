# Extract (Liquid-Liquid Extraction)

Rigorous multi-stage liquid-liquid extraction column.

## Ports

| Port | Direction | Type |
|------|-----------|------|
| F | IN | Feed (multiple — light and heavy liquid feeds) |
| L1 | OUT | First liquid (extract) |
| L2 | OUT | Second liquid (raffinate) |

## Input

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\NSTAGE` | int | Number of stages |

## Output

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Output\TOP_TEMP` | float | Top stage temperature |
| `\Data\Blocks\{name}\Output\TOP_L1FLOW` | float | Top stage first liquid flow |
| `\Data\Blocks\{name}\Output\TOP_L2FLOW` | float | Top stage second liquid flow |
| `\Data\Blocks\{name}\Output\BOTTOM_TEMP` | float | Bottom stage temperature |
| `\Data\Blocks\{name}\Output\BOT_L1FLOW` | float | Bottom stage first liquid flow |
| `\Data\Blocks\{name}\Output\BOT_L2FLOW` | float | Bottom stage second liquid flow |

## Typical Setup

1. Place: `place_block(session, 'EXT1', 'Extract')`
2. Stages: `set_value(session, aspen_path='\Data\Blocks\EXT1\Input\NSTAGE', value='10')`
3. Connect solvent and feed streams to appropriate stages.

## Gotchas

- Requires a property method with LLE capability (e.g. NRTL, UNIQUAC).
- Two liquid outlets only — no vapor product.
