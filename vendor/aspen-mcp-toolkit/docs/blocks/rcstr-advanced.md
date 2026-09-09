# RCSTR — Advanced

See [common-advanced.md](common-advanced.md) for property method override, electrolyte, free-water, EO, utility, and CO2e tracking paths shared by all blocks.

## Block-Specific Advanced Inputs

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\REACT_VOL` | float | Phase volume (specify volume of a specific phase) |
| `\Data\Blocks\{name}\Input\REACT_VOL_FR` | float | Phase volume fraction |
| `\Data\Blocks\{name}\Input\PH_RES_TIME` | float | Phase residence time |

## Advanced Outputs

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Output\LIQ1_VOL` | float | Liquid 1 phase volume |
| `\Data\Blocks\{name}\Output\SALT_VOL` | float | Salt phase volume |
| `\Data\Blocks\{name}\Output\COND_VOL` | float | Condensed phase volume |
