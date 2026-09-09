# Granulator

Fluidized bed granulation model for particle growth through layering or agglomeration.

## Ports

| Port | Direction | Type |
|------|-----------|------|
| F | IN | Feed (spray liquid + seed particles + gas) |
| P | OUT | Product (granules) |
| GAS | OUT | Exhaust gas |

## Input

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\METHOD` | string | Modeling method |
| `\Data\Blocks\{name}\Input\BED_MASS` | float | Cumulative bed mass |
| `\Data\Blocks\{name}\Input\MOISTURE` | float | Outlet solids moisture content |
| `\Data\Blocks\{name}\Input\MODEL` | string | Granulation model |
| `\Data\Blocks\{name}\Input\GROWTH_MODEL` | string | Growth model |
| `\Data\Blocks\{name}\Input\AREA` | float | Cross-sectional area |
| `\Data\Blocks\{name}\Input\TEMP` | float | Temperature |
| `\Data\Blocks\{name}\Input\PRES` | float | Pressure |

## Output

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Output\RES_TIME` | float | Average particle residence time |
| `\Data\Blocks\{name}\Output\RATE` | float | Average growth rate |
| `\Data\Blocks\{name}\Output\AVERAGE` | float | Product mean diameter |
| `\Data\Blocks\{name}\Output\QCALC` | float | Heat duty |
| `\Data\Blocks\{name}\Output\B_TEMP` | float | Outlet temperature |
| `\Data\Blocks\{name}\Output\BED_MASS` | float | Calculated bed mass |

## Typical Setup

1. Place: `place_block(session, 'GR1', 'Granulator')`
2. Model and growth model selection.
3. Set bed mass and operating conditions.
