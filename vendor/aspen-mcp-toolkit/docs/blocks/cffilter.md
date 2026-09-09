# CfFilter (Crossflow Filter)

Crossflow (tangential flow) membrane filtration model for liquid-solid separation.

## Ports

| Port | Direction | Type |
|------|-----------|------|
| F | IN | Feed (slurry) |
| FILT | OUT | Filtrate (liquid) |
| CONC | OUT | Concentrate (solids-rich) |

## Input

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\TYPE` | string | Model type |
| `\Data\Blocks\{name}\Input\MODE` | string | Operating mode |
| `\Data\Blocks\{name}\Input\MODEL` | string | Calculation method |
| `\Data\Blocks\{name}\Input\SOLID_SPLIT` | float | Fraction of solids to solid outlet |
| `\Data\Blocks\{name}\Input\FLUID_SPLIT` | float | Fraction of liquid to liquid outlet |
| `\Data\Blocks\{name}\Input\SHARPNESS` | float | Separation sharpness |
| `\Data\Blocks\{name}\Input\WIDTH` | float | Channel width |
| `\Data\Blocks\{name}\Input\HEIGHT` | float | Channel height |
| `\Data\Blocks\{name}\Input\LENGTH` | float | Channel length |
| `\Data\Blocks\{name}\Input\NUM_CHANNEL` | int | Number of channels |
| `\Data\Blocks\{name}\Input\MODULE_NUM` | int | Number of modules |
| `\Data\Blocks\{name}\Input\AVG_VELOCITY` | float | Average fluid velocity |
| `\Data\Blocks\{name}\Input\PDROP` | float | Pressure drop |
| `\Data\Blocks\{name}\Input\FILTR_RATE` | float | Specific filtration rate |
| `\Data\Blocks\{name}\Input\POROSITY` | float | Porosity |
| `\Data\Blocks\{name}\Input\FILTER_RES` | float | Resistance of filter medium |

## Output

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Output\CALC_NMOD` | int | Calculated number of modules |
| `\Data\Blocks\{name}\Output\CALC_FRATE` | float | Calculated filtration rate |
| `\Data\Blocks\{name}\Output\CALC_CFAC` | float | Calculated concentration factor |
| `\Data\Blocks\{name}\Output\TOT_AREA` | float | Total membrane area |
| `\Data\Blocks\{name}\Output\MOD_PDROP` | float | Pressure drop per module |
| `\Data\Blocks\{name}\Output\REYNOLDS` | float | Reynolds number |
| `\Data\Blocks\{name}\Output\SFRAC` | float | Calculated fraction of solids to solid outlet |
| `\Data\Blocks\{name}\Output\LFRAC` | float | Calculated fraction of liquid to liquid outlet |
| `\Data\Blocks\{name}\Output\D50` | float | D50 of separation curve |
| `\Data\Blocks\{name}\Output\QCALC` | float | Duty |

## Typical Setup

1. Place: `place_block(session, 'CF1', 'CfFilter')`
2. Set model type and mode.
3. Specify membrane geometry or separation splits.
