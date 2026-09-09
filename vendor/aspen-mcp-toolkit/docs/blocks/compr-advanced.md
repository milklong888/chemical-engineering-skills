# Compr — Advanced

See [common-advanced.md](common-advanced.md) for property method override, electrolyte, free-water, EO, utility, and CO2e tracking paths shared by all blocks.

## Advanced Outputs

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Output\POWER_ISEN` | float | Isentropic power requirement |
| `\Data\Blocks\{name}\Output\IN_CPR` | float | Inlet heat capacity ratio |
| `\Data\Blocks\{name}\Output\DIS` | float | Displacement (positive-displacement only) |
| `\Data\Blocks\{name}\Output\EV` | float | Volumetric efficiency (positive-displacement only) |
| `\Data\Blocks\{name}\Output\Z_IN` | float | Inlet compressibility factor |
| `\Data\Blocks\{name}\Output\Z_OUT` | float | Outlet compressibility factor |
| `\Data\Blocks\{name}\Output\ABVSRG` | float | Compressor percent above surge |
| `\Data\Blocks\{name}\Output\BELSWL` | float | Percent below stonewall |
| `\Data\Blocks\{name}\Output\SURGE_FLOW` | float | Surge volume flow rate |
| `\Data\Blocks\{name}\Output\SWALL_FLOW` | float | Stonewall volume flow rate |
| `\Data\Blocks\{name}\Output\SH_SPEED` | float | Shaft speed |
| `\Data\Blocks\{name}\Output\SP_SPEED` | float | Specific speed |
| `\Data\Blocks\{name}\Output\IN_MACH` | float | Inlet Mach number |
