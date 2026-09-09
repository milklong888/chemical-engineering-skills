# Electrolyzer

Electrolyzer model for water electrolysis (hydrogen production). Supports PEM, alkaline, and SOEC cell types.

## Ports

| Port | Direction | Type |
|------|-----------|------|
| F | IN | Feed (water/electrolyte) |
| ANODE | OUT | Anode product (oxygen-rich) |
| CATHODE | OUT | Cathode product (hydrogen-rich) |

## Input

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\MODEL_TYPE` | string | Calculation method |
| `\Data\Blocks\{name}\Input\MODEL_SCOPE` | string | Model scope |
| `\Data\Blocks\{name}\Input\CELL_TYPE` | string | Electrolyzer type (PEM, Alkaline, SOEC) |
| `\Data\Blocks\{name}\Input\NSTACKS` | int | Number of electrolyzer stacks |
| `\Data\Blocks\{name}\Input\NCELLS` | int | Number of cells per stack |
| `\Data\Blocks\{name}\Input\CURRENT` | float | Specified current |
| `\Data\Blocks\{name}\Input\POWER` | float | Specified power |
| `\Data\Blocks\{name}\Input\TEMPERATURE` | float | Operating temperature |
| `\Data\Blocks\{name}\Input\HEAT_DUTY` | float | Heat duty consumed |
| `\Data\Blocks\{name}\Input\AN_FD_RATIO` | float | Feed split ratio to anode |
| `\Data\Blocks\{name}\Input\PRES_ANODE` | float | Anode pressure / pressure drop |
| `\Data\Blocks\{name}\Input\PRES_CATH` | float | Cathode pressure / pressure drop |

## Output

Output paths use the `SharedData` node instead of `Output`:

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\SharedData\FaradayEfficiency` | float | Faraday efficiency |
| `\Data\Blocks\{name}\SharedData\HHVEfficiency` | float | HHV efficiency |
| `\Data\Blocks\{name}\SharedData\LHVEfficiency` | float | LHV efficiency |
| `\Data\Blocks\{name}\SharedData\VoltageEfficiency` | float | Voltage efficiency |
| `\Data\Blocks\{name}\SharedData\SpecificMassEnergyConsumption` | float | Specific energy per unit mass H2 |
| `\Data\Blocks\{name}\SharedData\SpecificMassWaterConsumption` | float | Specific water per unit mass H2 |
| `\Data\Blocks\{name}\SharedData\MassH2GenerationRateAssembly` | float | H2 production rate (mass) |
| `\Data\Blocks\{name}\SharedData\MoleH2GenerationRateAssembly` | float | H2 production rate (mole) |
| `\Data\Blocks\{name}\SharedData\PowerAssembly` | float | Assembly power |
| `\Data\Blocks\{name}\SharedData\VoltageAssembly` | float | Assembly voltage |
| `\Data\Blocks\{name}\SharedData\CurrentAssembly` | float | Assembly current |
| `\Data\Blocks\{name}\SharedData\ElectrolyzerTemperature` | float | Electrolyzer temperature |
| `\Data\Blocks\{name}\SharedData\HydrogenPurity` | float | H2 purity (mole fraction) |
| `\Data\Blocks\{name}\SharedData\OxygenPurity` | float | O2 purity (mole fraction) |

## Typical Setup

1. Place: `place_block(session, 'EL1', 'Electrolyzer')`
2. Cell type: `set_value(session, aspen_path='\Data\Blocks\EL1\Input\CELL_TYPE', value='PEM')`
3. Stacks: `set_value(session, aspen_path='\Data\Blocks\EL1\Input\NSTACKS', value='1')`
4. Cells: `set_value(session, aspen_path='\Data\Blocks\EL1\Input\NCELLS', value='100')`
5. Current or power spec.

## Gotchas

- Output paths use `SharedData` instead of the standard `Output` node.
- Available in Aspen Plus V15.0+ (newer block type).
- Requires proper electrolyte property method for alkaline type.
