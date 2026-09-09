# Distl (Edmister Shortcut Distillation)

Edmister shortcut distillation model. Simpler than DSTWU — requires number of stages, feed stage, reflux ratio, and D/F ratio.

## Ports

| Port | Direction | Type |
|------|-----------|------|
| F | IN | Feed |
| D | OUT | Distillate |
| B | OUT | Bottoms |

## Input

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\NSTAGE` | int | Number of stages |
| `\Data\Blocks\{name}\Input\FEED_LOC` | int | Feed stage location |
| `\Data\Blocks\{name}\Input\RR` | float | Reflux ratio |
| `\Data\Blocks\{name}\Input\D_F` | float | Distillate-to-feed mole ratio |
| `\Data\Blocks\{name}\Input\PTOP` | float | Condenser pressure |
| `\Data\Blocks\{name}\Input\PBOT` | float | Reboiler pressure |

## Output

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Output\COND_DUTY` | float | Condenser duty |
| `\Data\Blocks\{name}\Output\REB_DUTY` | float | Reboiler duty |
| `\Data\Blocks\{name}\Output\FEED_TRAY_T` | float | Feed stage temperature |
| `\Data\Blocks\{name}\Output\TOP_TEMP` | float | Top stage temperature |
| `\Data\Blocks\{name}\Output\BOTTOM_TEMP` | float | Bottom stage temperature |
| `\Data\Blocks\{name}\Output\FEED_QUALITY` | float | Feed quality |

## Typical Setup

1. Place: `place_block(session, 'D1', 'Distl')`
2. Stages: `set_value(session, aspen_path='\Data\Blocks\D1\Input\NSTAGE', value='20')`
3. Feed stage: `set_value(session, aspen_path='\Data\Blocks\D1\Input\FEED_LOC', value='10')`
4. Reflux ratio: `set_value(session, aspen_path='\Data\Blocks\D1\Input\RR', value='2')`
5. D/F ratio: `set_value(session, aspen_path='\Data\Blocks\D1\Input\D_F', value='0.5')`
6. Pressure: `set_value(session, aspen_path='\Data\Blocks\D1\Input\PTOP', value='1', unit='atm')`

## Gotchas

- Simpler than DSTWU — no key component recoveries, uses constant relative volatility.
- Good for quick screening; use RadFrac for rigorous results.
