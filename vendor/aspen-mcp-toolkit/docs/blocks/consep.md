# ConSep (Conceptual Separator)

Conceptual distillation column that estimates separation performance using shortcut methods. Calculates column design (stages, reflux, duties) from component recovery or composition specs.

## Ports

| Port | Direction | Type |
|------|-----------|------|
| F | IN | Feed |
| D | OUT | Distillate |
| B | OUT | Bottoms |

## Input

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\SELCOMP1` | string | Key component 1 |
| `\Data\Blocks\{name}\Input\SELCOMP2` | string | Key component 2 |
| `\Data\Blocks\{name}\Input\SELCOMP3` | string | Key component 3 |
| `\Data\Blocks\{name}\Input\IBASIS` | string | Basis for compositions |
| `\Data\Blocks\{name}\Input\DISTRECO1` | float | Distillate recovery of component 1 |
| `\Data\Blocks\{name}\Input\DISTRECO2` | float | Distillate recovery of component 2 |
| `\Data\Blocks\{name}\Input\DISTRECO3` | float | Distillate recovery of component 3 |
| `\Data\Blocks\{name}\Input\MOLE_RR` | float | Specified molar reflux ratio |
| `\Data\Blocks\{name}\Input\MASS_RR` | float | Specified mass reflux ratio |
| `\Data\Blocks\{name}\Input\P_SPEC` | float | Specified pressure |
| `\Data\Blocks\{name}\Input\IPHASE` | string | Valid phases |

## Output

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Output\ACT_STAGES2` | float | Total number of stages |
| `\Data\Blocks\{name}\Output\FEED_LOCATN2` | float | Feed stage location |
| `\Data\Blocks\{name}\Output\RR2` | float | Reflux ratio |
| `\Data\Blocks\{name}\Output\DISTIL_TEMP2` | float | Condenser temperature |
| `\Data\Blocks\{name}\Output\COND_DUTY2` | float | Condenser duty |
| `\Data\Blocks\{name}\Output\BR2` | float | Reboil ratio |
| `\Data\Blocks\{name}\Output\BOTTOM_TEMP2` | float | Reboiler temperature |
| `\Data\Blocks\{name}\Output\REB_DUTY2` | float | Reboiler duty |
| `\Data\Blocks\{name}\Output\F2` | float | Distillate flowrate |
| `\Data\Blocks\{name}\Output\F3` | float | Bottoms flowrate |

## Typical Setup

1. Place: `place_block(session, 'CS1', 'ConSep')`
2. Key components: `set_value(session, aspen_path='\Data\Blocks\CS1\Input\SELCOMP1', value='BENZENE')`
3. Recoveries: `set_value(session, aspen_path='\Data\Blocks\CS1\Input\DISTRECO1', value='0.99')`
4. Pressure: `set_value(session, aspen_path='\Data\Blocks\CS1\Input\P_SPEC', value='1', unit='atm')`

## Gotchas

- Conceptual model — estimates column design, not rigorous simulation.
- Useful for early-stage process synthesis and screening.
