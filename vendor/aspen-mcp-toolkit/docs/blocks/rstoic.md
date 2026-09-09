# RStoic (Stoichiometric Reactor)

Reactor with known stoichiometry and fractional conversion. No kinetics needed — specify reactions and conversions directly via internal tables.

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
| `\Data\Blocks\{name}\Input\VFRAC` | float | Specified vapor fraction (0–1) |
| `\Data\Blocks\{name}\Input\SPEC_OPT` | string | Specification option: `TP` (temp+pres), `TD` (temp+duty), etc. |
| `\Data\Blocks\{name}\Input\CONV\{rxn}` | float | Fractional conversion of key component |
| `\Data\Blocks\{name}\Input\KEY_CID\{rxn}` | string | Key reactant component ID |
| `\Data\Blocks\{name}\Input\KEY_SSID\{rxn}` | string | Substream ID for key reactant (usually `MIXED`) |
| `\Data\Blocks\{name}\Input\COEF\{rxn}\{comp}\{substream}` | float | Reactant stoichiometric coefficient (negative) |
| `\Data\Blocks\{name}\Input\COEF1\{rxn}\{comp}\{substream}` | float | Product stoichiometric coefficient (positive) |
| `\Data\Blocks\{name}\Input\OPT_EXT_CONV\{rxn}` | string | Reaction mode: `CONVERSION` (default) or `EXTENT` |
| `\Data\Blocks\{name}\Input\EXTENT\{rxn}` | float | Molar extent of reaction (kmol/hr). Only used when `OPT_EXT_CONV=EXTENT` |

## Output

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Output\B_TEMP` | float | Outlet temperature |
| `\Data\Blocks\{name}\Output\B_PRES` | float | Outlet pressure |
| `\Data\Blocks\{name}\Output\QCALC` | float | Calculated heat duty |
| `\Data\Blocks\{name}\Output\QNET` | float | Net heat duty |
| `\Data\Blocks\{name}\Output\B_VFRAC` | float | Calculated vapor fraction |
| `\Data\Blocks\{name}\Output\LIQ_RATIO` | float | First liquid / total liquid ratio |

## Stoichiometry Setup

RStoic uses its own internal stoichiometry tables, NOT external reaction sets. The setup requires inserting blank rows first, then setting labels and values.

### Step-by-step for each reaction:

**1. Insert a reaction row into CONV (this creates all related table entries):**
```
insert_row(session, '\Data\Blocks\R1\Input\CONV')
```

**2. Set the reaction number label:**
```
set_label(session, '\Data\Blocks\R1\Input\CONV', index=0, label='1')
```

**3. Set key reactant and substream:**
```
set_value(session, aspen_path='\Data\Blocks\R1\Input\KEY_CID\1', value='ETHANOL')
set_value(session, aspen_path='\Data\Blocks\R1\Input\KEY_SSID\1', value='MIXED')
```

**4. Set fractional conversion:**
```
set_value(session, aspen_path='\Data\Blocks\R1\Input\CONV\1', value='0.9')
```

**5. Set reactant coefficients (COEF) — need to insert rows first:**

For each reactant component, insert into `COEF\{rxn}` (dim=0 for components, dim=1 for substream):
```
# Insert component rows (dim=0) and substream row (dim=1)
insert_row(session, '\Data\Blocks\R1\Input\COEF\1', dimension=0)  # first reactant
insert_row(session, '\Data\Blocks\R1\Input\COEF\1', dimension=1)  # substream dimension

# Set labels
set_label(session, '\Data\Blocks\R1\Input\COEF\1', index=0, label='ETHANOL', dimension=0)
set_label(session, '\Data\Blocks\R1\Input\COEF\1', index=1, label='ACETICAC', dimension=0)
set_label(session, '\Data\Blocks\R1\Input\COEF\1', index=0, label='MIXED', dimension=1)

# Set values (negative for reactants)
set_value(session, aspen_path='\Data\Blocks\R1\Input\COEF\1\ETHANOL\MIXED', value='-1')
set_value(session, aspen_path='\Data\Blocks\R1\Input\COEF\1\ACETICAC\MIXED', value='-1')
```

**6. Set product coefficients (COEF1) — same pattern:**
```
insert_row(session, '\Data\Blocks\R1\Input\COEF1\1', dimension=0)
insert_row(session, '\Data\Blocks\R1\Input\COEF1\1', dimension=1)

set_label(session, '\Data\Blocks\R1\Input\COEF1\1', index=0, label='ETHYLACE', dimension=0)
set_label(session, '\Data\Blocks\R1\Input\COEF1\1', index=1, label='WATER', dimension=0)
set_label(session, '\Data\Blocks\R1\Input\COEF1\1', index=0, label='MIXED', dimension=1)

set_value(session, aspen_path='\Data\Blocks\R1\Input\COEF1\1\ETHYLACE\MIXED', value='1')
set_value(session, aspen_path='\Data\Blocks\R1\Input\COEF1\1\WATER\MIXED', value='1')
```

## Typical Setup

1. Place: `place_block(session, 'R1', 'RStoic')`
2. Temperature: `set_value(session, aspen_path='\Data\Blocks\R1\Input\TEMP', value='80', unit='C')`
3. Pressure: `set_value(session, aspen_path='\Data\Blocks\R1\Input\PRES', value='1', unit='atm')`
4. Set stoichiometry and conversion following the steps above.

## Gotchas

- RStoic does **NOT** use the `add_reaction_set` / `add_reaction` workflow — those are for RCSTR/RPlug.
- Stoichiometry tables (COEF, COEF1) require `insert_row` before values can be set — the nodes don't exist until rows are inserted.
- COEF and COEF1 are 2D tables: dimension 0 = component, dimension 1 = substream.
- After inserting into CONV (dim=0), the first `insert_row` on `COEF\{rxn}` (dim=0) creates one component slot. Additional components appear from the dim=1 insert (substream). Set labels for both dimensions.
- Dimension 1 labels for substream only accept valid substream names (e.g. `MIXED`), not component names.
- When a reaction has more than 2 reactants (or products), `insert_row` on `COEF\{rxn}` (dim=0) only works for the first 2 rows. For additional components, skip `insert_row` and directly use `set_label(index=N, label='COMP_NAME', dimension=0)` to expand the table, then `set_value` as normal. Example for a 3rd reactant:
```
set_label(session, '\Data\Blocks\R1\Input\COEF\1', index=2, label='OXYGEN', dimension=0)
set_value(session, aspen_path='\Data\Blocks\R1\Input\COEF\1\OXYGEN\MIXED', value='-0.5')
```
- **CONVERSION vs EXTENT mode:** By default, reactions use `CONVERSION` (fractional conversion of key component). When the reactor is inside a **recycle loop**, CONVERSION applies to the total feed (fresh + recycle), causing the reaction rate to scale with recycle flow — often consuming more reactant than available. Switch to `EXTENT` mode to fix the molar reaction rate:
  ```
  set_value(session, aspen_path='\Data\Blocks\R1\Input\OPT_EXT_CONV\1', value='EXTENT')
  set_value(session, aspen_path='\Data\Blocks\R1\Input\EXTENT\1', value='145')  # kmol/hr
  ```
  Use EXTENT when: (1) reactor is in a recycle loop, (2) you want a fixed production rate regardless of feed composition, (3) the limiting reagent may change between iterations.
