# HeatX — Advanced

See [common-advanced.md](common-advanced.md) for property method override, electrolyte, free-water, EO, utility, and CO2e tracking paths shared by all blocks.

HeatX has separate property method settings for hot and cold sides instead of the standard `OPSETNAME`:

## Block-Specific Advanced Inputs

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\HOPSET` | string | Hot side property method |
| `\Data\Blocks\{name}\Input\HHENRY_COMPS` | string | Hot side Henry's component list ID |
| `\Data\Blocks\{name}\Input\HCHEMISTRY` | string | Hot side electrolyte chemistry ID |
| `\Data\Blocks\{name}\Input\HTRUE_COMPS` | string | Hot side true-species approach |
| `\Data\Blocks\{name}\Input\HFREE_WATER` | string | Hot side free-water phase properties method |
| `\Data\Blocks\{name}\Input\HSOLU_WATER` | string | Hot side water solubility method |
| `\Data\Blocks\{name}\Input\COPSET` | string | Cold side property method |
| `\Data\Blocks\{name}\Input\CHENRY_COMPS` | string | Cold side Henry's component list ID |
| `\Data\Blocks\{name}\Input\CCHEMISTRY` | string | Cold side electrolyte chemistry ID |
| `\Data\Blocks\{name}\Input\CTRUE_COMPS` | string | Cold side true-species approach |
| `\Data\Blocks\{name}\Input\CFREE_WATER` | string | Cold side free-water phase properties method |
| `\Data\Blocks\{name}\Input\CSOLU_WATER` | string | Cold side water solubility method |
| `\Data\Blocks\{name}\Input\HOT_UTIL` | string | Hot utility ID |
| `\Data\Blocks\{name}\Input\COLD_UTIL` | string | Cold utility ID |
| `\Data\Blocks\{name}\Input\FAN_UTIL` | string | Fan electricity utility ID |
| `\Data\Blocks\{name}\Input\HOT_COMPS` | string | Hot side EO model components |
| `\Data\Blocks\{name}\Input\COLD_COMPS` | string | Cold side EO model components |

## Advanced Outputs

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Output\HX_AREAP` | float | Actual exchanger area |
| `\Data\Blocks\{name}\Output\HX_UAVD` | float | Average U (dirty) |
| `\Data\Blocks\{name}\Output\HX_UAVC` | float | Average U (clean) |
| `\Data\Blocks\{name}\Output\HX_XIC` | float | Thermal effectiveness |
| `\Data\Blocks\{name}\Output\HX_NTUC` | float | Number of transfer units |
| `\Data\Blocks\{name}\Output\HX_NSHLS` | float | Number of shells in series |
| `\Data\Blocks\{name}\Output\HX_NSHLP` | float | Number of shells in parallel |
| `\Data\Blocks\{name}\Output\FAN_USAGE` | float | Fan electricity usage |
| `\Data\Blocks\{name}\Output\FAN_UCOST` | float | Fan electricity cost |
| `\Data\Blocks\{name}\Output\UTL_COST` | float | Utility cost |

> Note: HeatX uses `UTL_COST` (not `UTIL_COST`) for the utility cost output path.
