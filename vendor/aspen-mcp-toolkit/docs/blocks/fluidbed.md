# Fluidbed (Fluidized Bed Reactor)

Fluidized bed reactor with detailed hydrodynamic modeling (bubble phase, emulsion phase, freeboard).

## Ports

| Port | Direction | Type |
|------|-----------|------|
| GAS | IN | Fluidizing gas |
| SOL | IN | Solids feed |
| GASOUT | OUT | Gas product |
| SOLOUT | OUT | Solids product |

## Input

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\BED_MASS` | float | Bed mass |
| `\Data\Blocks\{name}\Input\BED_PDROP` | float | Bed pressure drop |
| `\Data\Blocks\{name}\Input\HEIGHT` | float | Vessel height |
| `\Data\Blocks\{name}\Input\DIAM` | float | Vessel diameter |
| `\Data\Blocks\{name}\Input\MF_VOIDAGE` | float | Voidage at minimum fluidization |
| `\Data\Blocks\{name}\Input\GELDART_TYPE` | string | Geldart particle classification |
| `\Data\Blocks\{name}\Input\NCELL_BOTTOM` | int | Number of cells for bottom zone |
| `\Data\Blocks\{name}\Input\NCELL_DILUTE` | int | Number of cells for dilute zone |

## Output

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Output\H_BOTTOMZONE` | float | Height of bottom zone |
| `\Data\Blocks\{name}\Output\H_FREEBOARD` | float | Height of freeboard |
| `\Data\Blocks\{name}\Output\SOL_HOLDUP` | float | Solids holdup |
| `\Data\Blocks\{name}\Output\BED_DPCALC` | float | Fluidized bed pressure drop |
| `\Data\Blocks\{name}\Output\TOT_DPCALC` | float | Overall pressure drop |
| `\Data\Blocks\{name}\Output\QCALC` | float | Heat duty |
| `\Data\Blocks\{name}\Output\VELOCITY` | float | Minimum fluidization velocity |
| `\Data\Blocks\{name}\Output\TEMP` | float | Bed temperature |

## Typical Setup

1. Place: `place_block(session, 'FB1', 'Fluidbed')`
2. Geometry: set HEIGHT and DIAM.
3. Set bed mass or bed pressure drop.
4. Configure particle properties and reactions.
