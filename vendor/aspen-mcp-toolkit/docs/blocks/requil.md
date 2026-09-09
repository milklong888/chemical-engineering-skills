# REquil (Equilibrium Reactor)

Chemical and phase equilibrium reactor with specified equilibrium reactions. Faster than RGibbs when you know which reactions occur.

## Ports

| Port | Direction | Type |
|------|-----------|------|
| F | IN | Feed |
| HS | IN | Heat stream |
| V | OUT | Vapor product |
| L | OUT | Liquid product |
| HS | OUT | Heat stream out |

## Input

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\TEMP` | float | Specified temperature |
| `\Data\Blocks\{name}\Input\PRES` | float | Specified pressure |
| `\Data\Blocks\{name}\Input\DUTY` | float | Specified heat duty |
| `\Data\Blocks\{name}\Input\VFRAC` | float | Specified vapor fraction (0–1) |
| `\Data\Blocks\{name}\Input\COEF\{rxn}\{comp}` | float | Reactant stoichiometric coefficient (negative) |
| `\Data\Blocks\{name}\Input\COEF1\{rxn}\{comp}` | float | Product stoichiometric coefficient (positive) |
| `\Data\Blocks\{name}\Input\DELT\{rxn}` | float | Temperature approach for equilibrium |

## Output

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Output\B_TEMP` | float | Outlet temperature |
| `\Data\Blocks\{name}\Output\B_PRES` | float | Outlet pressure |
| `\Data\Blocks\{name}\Output\QCALC` | float | Calculated heat duty |
| `\Data\Blocks\{name}\Output\QNET` | float | Net heat duty |
| `\Data\Blocks\{name}\Output\B_VFRAC` | float | Calculated vapor fraction |

## When to Use

- Known reactions that reach equilibrium.
- Faster than RGibbs when you know which reactions occur.
- Two product streams (vapor + liquid).

## Stoichiometry Setup

REquil uses internal COEF/COEF1 tables similar to RStoic, but **without the MIXED substream dimension**. The path is `COEF\{rxn}\{comp}` (not `COEF\{rxn}\{comp}\MIXED`).

### Step-by-step:

**1. Insert a reaction row into COEF:**
```
insert_row(session, '\Data\Blocks\R3\Input\COEF')
set_label(session, '\Data\Blocks\R3\Input\COEF', index=0, label='1')
```

**2. Insert component rows and set reactant coefficients:**
```
# First reactant
insert_row(session, '\Data\Blocks\R3\Input\COEF\1', dimension=0)
set_label(session, '\Data\Blocks\R3\Input\COEF\1', index=0, label='ETHANOL', dimension=0)
set_value(session, aspen_path='\Data\Blocks\R3\Input\COEF\1\ETHANOL', value='-1')

# Second reactant
insert_row(session, '\Data\Blocks\R3\Input\COEF\1', dimension=0)
set_label(session, '\Data\Blocks\R3\Input\COEF\1', index=1, label='ACETICAC', dimension=0)
set_value(session, aspen_path='\Data\Blocks\R3\Input\COEF\1\ACETICAC', value='-1')
```

**3. Set product coefficients (COEF1 auto-created after COEF insert):**
```
insert_row(session, '\Data\Blocks\R3\Input\COEF1\1', dimension=0)
set_label(session, '\Data\Blocks\R3\Input\COEF1\1', index=0, label='ETHYLACE', dimension=0)
set_value(session, aspen_path='\Data\Blocks\R3\Input\COEF1\1\ETHYLACE', value='1')

insert_row(session, '\Data\Blocks\R3\Input\COEF1\1', dimension=0)
set_label(session, '\Data\Blocks\R3\Input\COEF1\1', index=1, label='WATER', dimension=0)
set_value(session, aspen_path='\Data\Blocks\R3\Input\COEF1\1\WATER', value='1')
```

## Typical Setup

1. Place: `place_block(session, 'R3', 'REquil')`
2. Temperature: `set_value(session, aspen_path='\Data\Blocks\R3\Input\TEMP', value='80', unit='C')`
3. Pressure: `set_value(session, aspen_path='\Data\Blocks\R3\Input\PRES', value='1', unit='atm')`
4. Set stoichiometry following the steps above.

## Gotchas

- REquil does **NOT** use external reaction sets — stoichiometry is set via internal COEF/COEF1 tables.
- Unlike RStoic, REquil's COEF path is `COEF\{rxn}\{comp}` (1D per reaction) — no MIXED substream dimension.
- COEF1 is auto-created when COEF reaction row is inserted.
- No CONV (conversion) needed — REquil calculates equilibrium composition automatically.
- Has two output ports: V (vapor) and L (liquid), unlike RStoic which has a single P (product).
- Temperature approach (DELT) allows you to offset from true equilibrium.
