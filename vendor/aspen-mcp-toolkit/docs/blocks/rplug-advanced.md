# RPlug — Advanced

See [common-advanced.md](common-advanced.md) for property method override, electrolyte, free-water, EO, utility, and CO2e tracking paths shared by all blocks.

## Block-Specific Advanced Inputs

RPlug has separate property method settings for the process stream and the thermal (coolant) fluid:

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\COPSETNAME` | string | Thermal fluid property method |
| `\Data\Blocks\{name}\Input\CHENRY_COMPS` | string | Thermal fluid Henry's component list ID |
| `\Data\Blocks\{name}\Input\CCHEMISTRY` | string | Thermal fluid electrolyte chemistry ID |
| `\Data\Blocks\{name}\Input\CTRUE_COMPS` | string | Thermal fluid true-species approach |
| `\Data\Blocks\{name}\Input\CFRWATEROPSE` | string | Thermal fluid free-water phase properties method |
| `\Data\Blocks\{name}\Input\CSOLU_WATER` | string | Thermal fluid water solubility method |

> Note: RPlug does not have utility cost outputs in the sgxml summary. Use the common CO2e tracking outputs.
