# RGibbs (Gibbs Free Energy Minimization Reactor)

Equilibrium reactor that minimizes Gibbs free energy to determine product composition. No reaction stoichiometry needed.

## Ports

| Port | Direction | Type |
|------|-----------|------|
| F | IN | Feed |
| HS | IN | Heat stream |
| P | OUT | Product |
| HS | OUT | Heat stream out |

## Input

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\TEMP` | float | Specified temperature |
| `\Data\Blocks\{name}\Input\PRES` | float | Specified pressure |
| `\Data\Blocks\{name}\Input\DUTY` | float | Specified heat duty |

## Output

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Output\B_TEMP` | float | Outlet temperature |
| `\Data\Blocks\{name}\Output\B_PRES` | float | Outlet pressure |
| `\Data\Blocks\{name}\Output\QCALC` | float | Calculated heat duty |
| `\Data\Blocks\{name}\Output\QNET` | float | Net heat duty |
| `\Data\Blocks\{name}\Output\B_VFRAC` | float | Vapor fraction |
| `\Data\Blocks\{name}\Output\NPHASE_OUT` | int | Number of fluid phases in product |
| `\Data\Blocks\{name}\Output\CSD-PHASE` | int | Maximum number of pure solids |

## When to Use

- Chemical equilibrium calculations without knowing reactions.
- Combustion, gasification, steam reforming.
- Phase equilibrium with simultaneous chemical equilibrium.

## Typical Setup

1. Place: `place_block(session, 'R1', 'RGibbs')`
2. Temperature: `set_value(session, aspen_path='\Data\Blocks\R1\Input\TEMP', value='1000', unit='C')`
3. Pressure: `set_value(session, aspen_path='\Data\Blocks\R1\Input\PRES', value='1', unit='atm')`

## Gotchas

- Does NOT require reaction definitions — it finds equilibrium automatically.
- May need to restrict products if unrealistic species appear in results.
- Computationally more expensive than RStoic or REquil.
