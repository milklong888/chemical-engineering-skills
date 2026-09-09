# Dryer

Drying model for removing moisture from solids. Supports convective dryers and spray dryers.

## Ports

| Port | Direction | Type |
|------|-----------|------|
| WET | IN | Wet solids feed |
| GAS | IN | Drying gas (hot air) |
| DRY | OUT | Dried solids |
| EXGAS | OUT | Exhaust gas |

## Input

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\DRYER_TYPE` | string | Dryer type |
| `\Data\Blocks\{name}\Input\PRES` | float | Pressure |
| `\Data\Blocks\{name}\Input\TEMP` | float | Temperature |
| `\Data\Blocks\{name}\Input\DELT` | float | Temperature change |
| `\Data\Blocks\{name}\Input\HEATIN` | float | Heat duty |
| `\Data\Blocks\{name}\Input\VOLUME` | float | Dryer volume |
| `\Data\Blocks\{name}\Input\LENGTH` | float | Dryer length |
| `\Data\Blocks\{name}\Input\AREA` | float | Cross-sectional area |
| `\Data\Blocks\{name}\Input\SOL_RES_TIME` | float | Solids residence time |
| `\Data\Blocks\{name}\Input\FLOW_DIR` | string | Gas flow direction |
| `\Data\Blocks\{name}\Input\MOIST_BASIS` | string | Moisture specification basis |

## Output

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Output\EXGT` | float | Exhaust gas temperature |
| `\Data\Blocks\{name}\Output\EXDEW` | float | Exhaust gas dew point |
| `\Data\Blocks\{name}\Output\ADQ` | float | Calculated duty |
| `\Data\Blocks\{name}\Output\XC_AREA` | float | Calculated cross-sectional area |
| `\Data\Blocks\{name}\Output\SOL_RES_TIME` | float | Calculated solids residence time |
| `\Data\Blocks\{name}\Output\EVAP_RATE2` | float | Overall evaporation rate |
| `\Data\Blocks\{name}\Output\INSOL_MO_CON` | float | Inlet solids moisture content |
| `\Data\Blocks\{name}\Output\OUSOL_MO_CON` | float | Outlet solids moisture content |

## Typical Setup

1. Place: `place_block(session, 'DR1', 'Dryer')`
2. Dryer type and flow direction.
3. Set geometry and operating conditions.
