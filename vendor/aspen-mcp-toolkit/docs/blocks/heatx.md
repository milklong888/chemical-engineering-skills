# HeatX (Two-Stream Heat Exchanger)

Rigorous two-stream heat exchanger with separate hot and cold sides. Supports design, rating, and simulation modes.

## Ports

| Port | Direction | Type |
|------|-----------|------|
| H | IN | Hot stream in |
| C | IN | Cold stream in |
| H | OUT | Hot stream out |
| C | OUT | Cold stream out |

## Input

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\CALC_MODE` | string | Calculation mode: `DESIGN`, `RATING`, `SIMULATION` |
| `\Data\Blocks\{name}\Input\VALUE` | float | Exchanger specification value |
| `\Data\Blocks\{name}\Input\SPECUN` | string | Units for exchanger specification |
| `\Data\Blocks\{name}\Input\AREA` | float | Exchanger area |
| `\Data\Blocks\{name}\Input\UA` | float | Constant UA value |
| `\Data\Blocks\{name}\Input\MIN_TAPP` | float | Minimum temperature approach |
| `\Data\Blocks\{name}\Input\PRES_HOT` | float | Hot side outlet pressure |
| `\Data\Blocks\{name}\Input\PRES_COLD` | float | Cold side outlet pressure |

> Choose calculation mode first, then set the appropriate spec. In shortcut/design mode, specify duty or outlet temperature. In simulation mode, specify UA or area.

## Output

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Output\HOTINT` | float | Inlet hot stream temperature |
| `\Data\Blocks\{name}\Output\HOTINP` | float | Inlet hot stream pressure |
| `\Data\Blocks\{name}\Output\HOTINVF` | float | Inlet hot stream vapor fraction |
| `\Data\Blocks\{name}\Output\HOT_TEMP` | float | Outlet hot stream temperature |
| `\Data\Blocks\{name}\Output\HOT_PRES` | float | Outlet hot stream pressure |
| `\Data\Blocks\{name}\Output\HOT_VFRAC` | float | Outlet hot stream vapor fraction |
| `\Data\Blocks\{name}\Output\COLDINT` | float | Inlet cold stream temperature |
| `\Data\Blocks\{name}\Output\COLDINP` | float | Inlet cold stream pressure |
| `\Data\Blocks\{name}\Output\COLDINVF` | float | Inlet cold stream vapor fraction |
| `\Data\Blocks\{name}\Output\COLD_TEMP` | float | Outlet cold stream temperature |
| `\Data\Blocks\{name}\Output\COLD_PRES` | float | Outlet cold stream pressure |
| `\Data\Blocks\{name}\Output\COLD_FRAC` | float | Outlet cold stream vapor fraction |
| `\Data\Blocks\{name}\Output\HX_DUTY` | float | Calculated heat duty |
| `\Data\Blocks\{name}\Output\HX_AREAC2` | float | Required exchanger area |
| `\Data\Blocks\{name}\Output\HX_UA` | float | UA value |
| `\Data\Blocks\{name}\Output\HX_DTLM` | float | LMTD (corrected) |
| `\Data\Blocks\{name}\Output\HX_FMTD` | float | LMTD correction factor |

## Typical Setup

1. Place: `place_block(session, 'HX1', 'HeatX')`
2. Mode: `set_value(session, aspen_path='\Data\Blocks\HX1\Input\CALC_MODE', value='DESIGN')`
3. Connect hot and cold side streams.
4. Set spec as needed (e.g. duty, outlet temp, or area depending on mode).

## Gotchas

- Requires both hot and cold side connections.
- Choose calculation mode before setting other parameters.
- MHeatX (multi-stream heat exchanger) cannot be placed via COM.
