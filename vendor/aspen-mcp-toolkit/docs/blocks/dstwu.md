# DSTWU (Shortcut Distillation)

Winn-Underwood-Gilliland shortcut distillation method. Good for quick estimates of column design before using RadFrac.

## Ports

| Port | Direction | Type |
|------|-----------|------|
| F | IN | Feed |
| CHS | IN | Condenser heat stream |
| RHS | IN | Reboiler heat stream |
| D | OUT | Distillate |
| B | OUT | Bottoms |
| CWD | OUT | Condenser work duty |
| CHS | OUT | Condenser heat stream out |
| RHS | OUT | Reboiler heat stream out |

## Input

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\LIGHTKEY` | string | Light key component |
| `\Data\Blocks\{name}\Input\HEAVYKEY` | string | Heavy key component |
| `\Data\Blocks\{name}\Input\RECOVL` | float | Light key recovery in distillate (0–1) |
| `\Data\Blocks\{name}\Input\RECOVH` | float | Heavy key recovery in bottoms (0–1) |
| `\Data\Blocks\{name}\Input\PTOP` | float | Condenser pressure |
| `\Data\Blocks\{name}\Input\PBOT` | float | Reboiler pressure |
| `\Data\Blocks\{name}\Input\CONDENSER` | string | `TOTAL` or `PARTIAL-V` |
| `\Data\Blocks\{name}\Input\NSTAGE` | int | Number of stages (optional — calculated if not given) |
| `\Data\Blocks\{name}\Input\RR` | float | Reflux ratio (optional — calculated if not given) |
| `\Data\Blocks\{name}\Input\RDV` | float | Distillate vapor fraction |

> Specify light/heavy key components and their recoveries. Either reflux ratio or number of stages can be given; the other is calculated.

## Output

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Output\MIN_REFLUX` | float | Minimum reflux ratio |
| `\Data\Blocks\{name}\Output\ACT_REFLUX` | float | Actual reflux ratio |
| `\Data\Blocks\{name}\Output\MIN_STAGES` | float | Minimum number of stages |
| `\Data\Blocks\{name}\Output\ACT_STAGES` | float | Actual number of stages |
| `\Data\Blocks\{name}\Output\FEED_LOCATN` | float | Optimal feed stage |
| `\Data\Blocks\{name}\Output\RECT_STAGES` | float | Number of stages above feed |
| `\Data\Blocks\{name}\Output\DISTIL_TEMP` | float | Distillate temperature |
| `\Data\Blocks\{name}\Output\BOTTOM_TEMP` | float | Bottoms temperature |
| `\Data\Blocks\{name}\Output\DIST_VS_FEED` | float | Distillate-to-feed fraction |

## Typical Setup

1. Place: `place_block(session, 'D1', 'DSTWU')`
2. Light key: `set_value(session, aspen_path='\Data\Blocks\D1\Input\LIGHTKEY', value='BENZENE')`
3. Heavy key: `set_value(session, aspen_path='\Data\Blocks\D1\Input\HEAVYKEY', value='TOLUENE')`
4. Light key recovery: `set_value(session, aspen_path='\Data\Blocks\D1\Input\RECOVL', value='0.99')`
5. Heavy key recovery: `set_value(session, aspen_path='\Data\Blocks\D1\Input\RECOVH', value='0.99')`
6. Condenser pressure: `set_value(session, aspen_path='\Data\Blocks\D1\Input\PTOP', value='1', unit='atm')`
7. Reboiler pressure: `set_value(session, aspen_path='\Data\Blocks\D1\Input\PBOT', value='1.2', unit='atm')`
8. Reflux ratio: `set_value(session, aspen_path='\Data\Blocks\D1\Input\RR', value='1.5')`

## Gotchas

- Shortcut method — results are estimates. Use RadFrac for rigorous simulation.
- Requires exactly one light key and one heavy key component.
