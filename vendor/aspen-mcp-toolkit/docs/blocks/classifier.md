# Classifier (Particle Classifier)

Particle size classifier for separating solids by size, velocity, or density. Supports gravity, centrifugal, and sifter models.

## Ports

| Port | Direction | Type |
|------|-----------|------|
| F | IN | Feed |
| COARSE | OUT | Coarse solids |
| FINES | OUT | Fine solids / fluid |

## Input

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\METHOD` | string | Classification option |
| `\Data\Blocks\{name}\Input\MODEL` | string | Classification function |
| `\Data\Blocks\{name}\Input\CLASS_CHAR` | string | Classification characteristic (size, velocity, density) |
| `\Data\Blocks\{name}\Input\TYPE` | string | Sifter model type |
| `\Data\Blocks\{name}\Input\CUT_SIZE` | float | Cut size |
| `\Data\Blocks\{name}\Input\CUT_VELOCITY` | float | Cut velocity |
| `\Data\Blocks\{name}\Input\SHARPNESS` | float | Separation sharpness |
| `\Data\Blocks\{name}\Input\FLUID_SPLIT` | float | Fluid split factor |
| `\Data\Blocks\{name}\Input\TEMP` | float | Temperature |
| `\Data\Blocks\{name}\Input\PRES` | float | Pressure |
| `\Data\Blocks\{name}\Input\AREA` | float | Cross-sectional area |

## Output

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Output\AREA_CALC` | float | Calculated cross-sectional area |
| `\Data\Blocks\{name}\Output\EFFICIENCY` | float | Overall separation efficiency |
| `\Data\Blocks\{name}\Output\PDROP` | float | Calculated pressure drop |
| `\Data\Blocks\{name}\Output\VELOCITY2` | float | Calculated cut velocity |
| `\Data\Blocks\{name}\Output\FEED_DIAM` | float | Feed mean diameter |
| `\Data\Blocks\{name}\Output\COARSE_D50` | float | Coarse outlet mean diameter |
| `\Data\Blocks\{name}\Output\FINES_D50` | float | Fines outlet mean diameter |
| `\Data\Blocks\{name}\Output\QCALC` | float | Calculated heat duty |
| `\Data\Blocks\{name}\Output\B_TEMP` | float | Outlet temperature |
| `\Data\Blocks\{name}\Output\B_PRES` | float | Outlet pressure |

## Typical Setup

1. Place: `place_block(session, 'CL1', 'Classifier')`
2. Method and model selection.
3. Set cut size or cut velocity and sharpness.
