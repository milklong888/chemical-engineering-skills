# RCSTR (Continuous Stirred Tank Reactor)

Kinetic reactor with perfect mixing. Requires an external reaction set with kinetic parameters.

## Ports

| Port | Direction | Type |
|------|-----------|------|
| F | IN | Feed |
| HS | IN | Heat stream |
| VI | IN | Vapor inlet |
| P | OUT | Product |
| HS | OUT | Heat stream out |

## Input

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\TEMP` | float | Specified temperature |
| `\Data\Blocks\{name}\Input\PRES` | float | Specified pressure |
| `\Data\Blocks\{name}\Input\DUTY` | float | Specified heat duty |
| `\Data\Blocks\{name}\Input\VOL` | float | Reactor volume (when SPEC_TYPE=TOT-VOL) |
| `\Data\Blocks\{name}\Input\RES_TIME` | float | Residence time (when SPEC_TYPE=RES-TIME) |
| `\Data\Blocks\{name}\Input\SPEC_OPT` | string | Thermal spec: `TEMP`, `DUTY`, `VFRAC` |
| `\Data\Blocks\{name}\Input\SPEC_TYPE` | string | Size spec: `TOT-VOL`, `RES-TIME` |
| `\Data\Blocks\{name}\Input\PHASE` | string | Valid phases: `V`, `L`, `V-L` |
| `\Data\Blocks\{name}\Input\NPHASE` | int | Number of phases (1 or 2) |
| `\Data\Blocks\{name}\Input\RXN_ID` | table | Selected reaction set(s) |

## Output

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Output\B_TEMP` | float | Outlet temperature |
| `\Data\Blocks\{name}\Output\QCALC` | float | Calculated heat duty |
| `\Data\Blocks\{name}\Output\QNET` | float | Net heat duty |
| `\Data\Blocks\{name}\Output\TOT_VOL` | float | Total reactor volume |
| `\Data\Blocks\{name}\Output\VAP_VOL` | float | Vapor phase volume |
| `\Data\Blocks\{name}\Output\LIQ_VOL` | float | Liquid phase volume |
| `\Data\Blocks\{name}\Output\TOT_RES_TIME` | float | Total residence time |
| `\Data\Blocks\{name}\Output\VAP_RES_TIME` | float | Vapor phase residence time |
| `\Data\Blocks\{name}\Output\COND_RES_TIM` | float | Condensed phase residence time |

## Assigning a Reaction Set

The RXN_ID node has a pre-existing empty element. Use `list_elements` to see it, then `set_value` to assign:

```
list_elements(session, '\Data\Blocks\R1\Input\RXN_ID')
→ [0] #0 = None

set_value(session, aspen_path='\Data\Blocks\R1\Input\RXN_ID\#0', value='CRACKING')
```

## Typical Setup

1. Place block: `place_block(session, 'R1', 'RCSTR')`
2. Set temperature: `set_value(session, aspen_path='\Data\Blocks\R1\Input\TEMP', value='850', unit='C')`
3. Set pressure: `set_value(session, aspen_path='\Data\Blocks\R1\Input\PRES', value='1.7', unit='atm')`
4. Set volume: `set_value(session, aspen_path='\Data\Blocks\R1\Input\VOL', value='10')`
5. Create reaction set: `add_reaction_set(session, 'RXN1', 'POWERLAW')`
6. Add reaction: `add_reaction(session, 'RXN1', 1, reactants={...}, products={...}, phase='V')`
7. Set kinetics: `set_value(session, aspen_path='\Data\Reactions\Reactions\RXN1\Input\PRE_EXP\1', value='3.6e15')`
8. Assign to block: `set_value(session, aspen_path='\Data\Blocks\R1\Input\RXN_ID\#0', value='RXN1')`

## Gotchas

- Must set VOL or RES_TIME for reactor sizing.
- PHASE defaults to `V` (vapor only). Set to `V-L` for two-phase reactions.
- NPHASE must match PHASE setting (1 for V or L, 2 for V-L).
