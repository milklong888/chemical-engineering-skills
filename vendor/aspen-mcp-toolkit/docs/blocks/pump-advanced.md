# Pump — Advanced

See [common-advanced.md](common-advanced.md) for property method override, electrolyte, free-water, EO, utility, and CO2e tracking paths shared by all blocks.

## Block-Specific Advanced Inputs

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\SUCT_AREA` | float | Suction area |
| `\Data\Blocks\{name}\Input\HEAD_STATIC` | float | Hydraulic static head |
| `\Data\Blocks\{name}\Input\NCURVES` | int | Number of performance curves |
| `\Data\Blocks\{name}\Input\ACT_SH_SPEED` | float | Operating shaft speed |
| `\Data\Blocks\{name}\Input\IMPELLER_DIA` | float | Impeller diameter |

## Advanced Outputs

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Output\NPSH-AVAIL` | float | NPSH available |
| `\Data\Blocks\{name}\Output\NPSH_REQ` | float | NPSH required |
| `\Data\Blocks\{name}\Output\SP-SPEED` | float | Specific speed (operating) |
| `\Data\Blocks\{name}\Output\SUCT_SPEED` | float | Suction specific speed (operating) |
| `\Data\Blocks\{name}\Output\HEAD-COF` | float | Head coefficient |
| `\Data\Blocks\{name}\Output\FLOW-COF` | float | Flow coefficient |
