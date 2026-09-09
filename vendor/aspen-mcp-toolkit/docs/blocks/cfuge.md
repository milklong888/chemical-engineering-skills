# Cfuge (Centrifuge)

Centrifuge model for liquid-solid separation. Supports decanter, disc, and pusher centrifuge types with classification and deliquoring.

## Ports

| Port | Direction | Type |
|------|-----------|------|
| F | IN | Feed (slurry) |
| SOL | OUT | Solids (cake) |
| LIQ | OUT | Liquid (centrate) |

## Input

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\TYPE` | string | Centrifuge model type |
| `\Data\Blocks\{name}\Input\SOLID_SPLIT` | float | Fraction of solids to solid outlet |
| `\Data\Blocks\{name}\Input\FLUID_SPLIT` | float | Fraction of liquid to liquid outlet |
| `\Data\Blocks\{name}\Input\SHARPNESS` | float | Separation sharpness |
| `\Data\Blocks\{name}\Input\CUT_SIZE` | float | Cut size |
| `\Data\Blocks\{name}\Input\DIAM_DRUM` | float | Drum diameter |
| `\Data\Blocks\{name}\Input\LEN_CYL` | float | Cylindrical length |
| `\Data\Blocks\{name}\Input\DEC_SPEED` | float | Drum rotary speed |
| `\Data\Blocks\{name}\Input\WETNESS` | float | Residual moisture |

## Output

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Output\SOLD_RECOV` | float | Fraction of solids to solid outlet |
| `\Data\Blocks\{name}\Output\FLUD_RECOV` | float | Fraction of liquid to liquid outlet |
| `\Data\Blocks\{name}\Output\SEP_D50` | float | D50 of separation curve |
| `\Data\Blocks\{name}\Output\RES_MOISTURE` | float | Residual moisture |
| `\Data\Blocks\{name}\Output\DRY_CONTENT` | float | Dry substance content |
| `\Data\Blocks\{name}\Output\SEP_GRADE` | float | Total separation grade |
| `\Data\Blocks\{name}\Output\RES_TIME` | float | Residence time |

## Typical Setup

1. Place: `place_block(session, 'CTF1', 'Cfuge')`
2. Type: `set_value(session, aspen_path='\Data\Blocks\CTF1\Input\TYPE', value='DECANTER')`
3. Set geometry and operating speed.
