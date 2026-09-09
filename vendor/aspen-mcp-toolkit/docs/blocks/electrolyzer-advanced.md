# Electrolyzer — Advanced

See [common-advanced.md](common-advanced.md) for property method override, electrolyte, free-water, EO, utility, and CO2e tracking paths shared by all blocks.

## Advanced Outputs (SharedData)

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\SharedData\MassO2GenerationRateAssembly` | float | O2 production rate (mass) |
| `\Data\Blocks\{name}\SharedData\MassH2OConsumptionRateAssembly` | float | Water consumption rate (mass) |
| `\Data\Blocks\{name}\SharedData\MoleO2GenerationRateAssembly` | float | O2 production rate (mole) |
| `\Data\Blocks\{name}\SharedData\MoleH2OConsumptionRateAssembly` | float | Water consumption rate (mole) |
| `\Data\Blocks\{name}\SharedData\CurrentCell` | float | Cell current |
| `\Data\Blocks\{name}\SharedData\VoltageCell` | float | Cell voltage |
| `\Data\Blocks\{name}\SharedData\PowerCell` | float | Cell power |
| `\Data\Blocks\{name}\SharedData\CurrentStack` | float | Stack current |
| `\Data\Blocks\{name}\SharedData\VoltageStack` | float | Stack voltage |
| `\Data\Blocks\{name}\SharedData\PowerStack` | float | Stack power |
| `\Data\Blocks\{name}\SharedData\AnodeVaporFraction` | float | Anode vapor fraction |
| `\Data\Blocks\{name}\SharedData\CathodeVaporFraction` | float | Cathode vapor fraction |
| `\Data\Blocks\{name}\SharedData\ElectrolyzerDutyAssembly` | float | Electrolyzer duty |
| `\Data\Blocks\{name}\SharedData\AnodePressure` | float | Anode pressure |
| `\Data\Blocks\{name}\SharedData\CathodePressure` | float | Cathode pressure |

> Note: Electrolyzer does not have utility assignment or CO2e tracking outputs.
