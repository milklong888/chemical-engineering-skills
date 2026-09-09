# FSplit (Stream Splitter)

Splits one inlet stream into multiple outlet streams by fraction. All outlets have the same composition and conditions as the inlet.

## Ports

| Port | Direction | Type |
|------|-----------|------|
| F | IN | Feed |
| HS | IN | Heat stream |
| WS | IN | Work stream |
| PS | IN | Pseudo stream |
| P | OUT | Product (multiple) |
| HS | OUT | Heat stream out |
| WS | OUT | Work stream out |
| PS | OUT | Pseudo stream out |

## Input

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\FRAC\{stream}` | float | Split fraction for an outlet stream (0–1) |
| `\Data\Blocks\{name}\Input\VOL_FLOW\{stream}` | float | Actual volume flow for an outlet stream |
| `\Data\Blocks\{name}\Input\BASIS_LIMIT\{stream}` | float | Limit flow for an outlet stream |

> Leave one outlet stream without a specified fraction — it becomes the balance stream and receives the remainder.

## Output

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Output\STREAMFRAC\{stream}` | float | Calculated split fraction for each outlet |

## Typical Setup

1. Place: `place_block(session, 'SP1', 'FSplit')`
2. Connect multiple outlet streams.
3. Set fractions: `set_value(session, aspen_path='\Data\Blocks\SP1\Input\FRAC\S2', value='0.3')`
4. Leave one stream unspecified (it gets the balance).

## Gotchas

- Fractions must sum to 1.0. Leave one outlet without a fraction — it becomes the balance stream.
- Alternatively, you can specify outlet flow rates instead of fractions.
- `connect_stream` with `port_name='P'` will fail due to fuzzy matching ambiguity with `PS(IN)`/`PS(OUT)`. Always use the full port name `P(OUT)` when connecting outlet streams.
