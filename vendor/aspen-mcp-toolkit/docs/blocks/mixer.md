# Mixer

Combines multiple inlet streams into a single outlet stream. Performs an adiabatic flash to determine outlet conditions.

## Ports

| Port | Direction | Type |
|------|-----------|------|
| F | IN | Feed (multiple) |
| HS | IN | Heat stream |
| WS | IN | Work stream |
| PS | IN | Pseudo stream |
| P | OUT | Product |
| HS | OUT | Heat stream out |
| WS | OUT | Work stream out |
| PS | OUT | Pseudo stream out |
| WD | OUT | Work duty |

## Input

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\PRES` | float | Outlet pressure (optional — defaults to minimum inlet pressure) |
| `\Data\Blocks\{name}\Input\T_EST` | float | Temperature estimate (helps convergence) |

## Output

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Output\B_TEMP` | float | Outlet temperature |
| `\Data\Blocks\{name}\Output\B_PRES` | float | Calculated outlet pressure |
| `\Data\Blocks\{name}\Output\B_VFRAC` | float | Vapor fraction |
| `\Data\Blocks\{name}\Output\LIQ_RATIO` | float | First liquid / total liquid ratio |

## Typical Setup

1. Place: `place_block(session, 'MIX1', 'Mixer')`
2. Connect inlet streams — no additional configuration needed.
3. Optionally set outlet pressure: `set_value(session, aspen_path='\Data\Blocks\MIX1\Input\PRES', value='2', unit='atm')`

## Gotchas

- If no outlet pressure is specified, the mixer uses the lowest inlet stream pressure.
- Mixer does not require any specs beyond stream connections.
- `connect_stream` with `port_name='P'` will fail due to fuzzy matching ambiguity with `PS(IN)`/`PS(OUT)`. Always use the full port name `P(OUT)` when connecting the outlet stream.
