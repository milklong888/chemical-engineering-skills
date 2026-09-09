# RadFrac — Advanced

See [common-advanced.md](common-advanced.md) for property method override, electrolyte, free-water, EO, utility, and CO2e tracking paths shared by all blocks.

## 3-Phase Setup

When the system contains immiscible liquids (e.g., water + organic), enable 3-phase mode:

1. Set number of phases: `set_value(session, aspen_path='\Data\Blocks\COL1\Input\NO_PHASE', value='3')`
2. Set stage range to test for two liquid phases (table node):
   ```
   insert_row(session, '\Data\Blocks\COL1\Input\TRAY2')
   set_label(session, '\Data\Blocks\COL1\Input\TRAY2', index=0, label='{starting_stage}')
   set_value(session, aspen_path='\Data\Blocks\COL1\Input\TRAY2\{starting_stage}', value='{ending_stage}')
   ```
3. Set key component to identify 2nd liquid phase (list node):
   ```
   insert_row(session, '\Data\Blocks\COL1\Input\COMP_LIST')
   set_value(session, aspen_path='\Data\Blocks\COL1\Input\COMP_LIST\#0', value='WATER')
   ```

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\NO_PHASE` | int | Number of phases (2 or 3) |
| `\Data\Blocks\{name}\Input\TRAY2\{starting_stage}` | int | Ending stage for LL test range (table node, key = starting stage) |
| `\Data\Blocks\{name}\Input\COMP_LIST\#0` | string | Key component for 2nd liquid phase (list node, use `insert_row` first) |

> **Note:** `TRAY2` is a table node. To create a row: `insert_row` → `set_label` (starting stage) → `set_value` (ending stage). Reading back: `get_value` on `\...\TRAY2\{starting_stage}` returns the ending stage.

> **Note:** `COMP_LIST` is a list node. Use `insert_row` to create a slot, then `set_value` on `#0` to assign the component. To read back: `list_elements` on `COMP_LIST`. Multiple key components can be added with additional `insert_row` calls.

> **Important:** 3-phase mode (`NO_PHASE=3`) requires `ALGORITHM=STANDARD`. The default `SUM-RATES` (Petroleum/Wide-boiling) is **not compatible** with VLL phases and will produce the error: *"Convergence = Petroleum/Wide-boiling is not allowed when Valid Phases = Vapor-Liquid-Liquid"*. Change algorithm before running:
> ```
> set_value(session, aspen_path='\Data\Blocks\COL1\Input\ALGORITHM', value='STANDARD')
> ```
> Valid ALGORITHM values: `STANDARD`, `SUM-RATES`, `NEWTON`

> **Warning:** `reinit_simulation` clears TRAY2 and COMP_LIST table data. After reinit, you must re-insert rows and re-set values for 3-phase configuration.

## 3-Phase Convergence Tips

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\MAXOL` | int | Max outer loop iterations (default 25, increase to 100+ for 3-phase) |
| `\Data\Blocks\{name}\Input\DAMPING` | string | Damping: `NONE`, `MILD`, `MEDIUM`, `SEVERE` |
| `\Data\Blocks\{name}\Input\LL_METH` | string | Liquid-liquid split method: `GIBBS` (default) |
| `\Data\Blocks\{name}\Input\L2_GAMMA` | string | Activity coefficient model for 2nd liquid phase: `MARGULES` (only valid value) |
| `\Data\Blocks\{name}\Input\L2_CUTOFF` | float | Cutoff for 2nd liquid phase detection (default 0.5) |

- 3-phase columns are harder to converge than 2-phase. If "COLUMN NOT CONVERGED", try increasing `MAXOL` and setting `DAMPING=SEVERE`.
- "LIQUID-LIQUID PHASE SPLIT CALC. FAILED TO CONVERGE" often means the stage range (`TRAY2`) is too narrow — expand to cover the full column (1 to NSTAGE).
- Unreasonable distillate/bottoms rates can prevent convergence. Adjust operating specs to physically realistic values.

## Column Internals (Tray/Packing Sizing)

Column Internals allow hydraulic sizing and rating of trays or packings. They require the simulation to be **run first** before adding internals.

### Setup Steps

1. Run simulation first (equilibrium): `run_simulation(session)`
2. Add Column Internal: `add_element(session, '\Data\Blocks\{name}\Subobjects\Column Internals', 'INT-1')`
3. Add Sections: `add_element(session, '\Data\Blocks\{name}\Subobjects\Column Internals\INT-1\Subobjects\Sections', 'CS-1')`
4. Set section stage range and properties (see paths below)

### Rate-Based Setup

Rating mode requires a diameter value. To get it automatically, first run with Interactive Sizing, then switch to Rating:

1. Run simulation (equilibrium) with `INTER-SIZING` to calculate diameters
2. Switch to rating + rate-based:
   - `set_value(session, aspen_path='\Data\Blocks\{name}\Input\CALC_MODE', value='RIG-RATE')`
   - `set_value(session, aspen_path='...\CA_SIZING\{int}\{sec}', value='RATING')` for each section
   - `set_value(session, aspen_path='...\CA_RATE_BASE\{int}\{sec}', value='YES')` for each section
3. Run simulation: `run_simulation(session)`

> **Important:** `RATING` mode requires `CA_DIAM` to have a value. If you add internals directly as `RATING` without running `INTER-SIZING` first, the diameter will be empty and the simulation will fail. Either run sizing first or set `CA_DIAM` manually.

### Path Pattern

Column Internal properties use a **nested table path**:
```
\Data\Blocks\{name}\Subobjects\Column Internals\{int_name}\Input\{property}\{int_name}\{section_name}
```
Example: `\Data\Blocks\COL1\Subobjects\Column Internals\INT-1\Input\CA_STAGE1\INT-1\CS-1`

### Section Properties

| Property | Type | Description |
|----------|------|-------------|
| `CA_SIZING\{int}\{sec}` | string | Mode: `INTER-SIZING` (Interactive sizing), `RATING` |
| `CA_STAGE1\{int}\{sec}` | int | Start stage |
| `CA_STAGE2\{int}\{sec}` | int | End stage (cannot = NSTAGE if reboiler exists) |
| `CA_INTERNAL\{int}\{sec}` | string | Internal type: `TRAY`, `PACKED` |
| `CA_TRAYTYPE\{int}\{sec}` | string | Tray type: `SIEVE`, `VALVE`, `BUBBLE-CAP` |
| `CA_TRAY_SPC\{int}\{sec}` | float | Tray spacing |
| `CA_DIAM\{int}\{sec}` | float | Column diameter |
| `CA_NPASS\{int}\{sec}` | int | Number of passes |
| `CA_RATE_BASE\{int}\{sec}` | string | Rate-based for this section: `YES`, `NO` |
| `CA_PACKTYPE\{int}\{sec}` | string | Packing type (when PACKED) |
| `CA_PACK_MAT\{int}\{sec}` | string | Packing material |
| `CA_PACK_SIZE\{int}\{sec}` | string | Packing size |
| `CA_PACK_HT\{int}\{sec}` | float | Packing height |

> **End stage constraint:** If the column has a reboiler, the last section's end stage must be ≤ NSTAGE - 1 (e.g., 29 for a 30-stage column). Setting it to NSTAGE gives error: "End Stage=Number of Stages is not allowed unless Reboiler=None or Reboiler Duty=0".

### Listing & Removing

- List internals: `list_elements(session, '\Data\Blocks\{name}\Subobjects\Column Internals')`
- List sections: `list_elements(session, '\Data\Blocks\{name}\Subobjects\Column Internals\{int}\Subobjects\Sections')`
- Remove section: `remove_element(session, '...\Sections', 'CS-1')`
- Remove internal: `remove_element(session, '...\Column Internals', 'INT-1')`

## Side Draws (Side Product)

RadFrac supports liquid or vapor side draws from intermediate stages via the SP(OUT) port.

### Setup Steps

1. Place a new stream: `place_stream(session, 'SIDEDRAW', 'MATERIAL')`
2. Connect to SP(OUT): `connect_stream(session, stream_name='SIDEDRAW', block_name='COL1', port_name='SP(OUT)', block_type='RadFrac')`
3. Set the draw stage, flow rate, and phase:

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\PROD_STAGE\{stream}` | int | Stage number for the side draw |
| `\Data\Blocks\{name}\Input\PROD_FLOW\{stream}` | float | Side draw flow rate (kmol/hr by default) |
| `\Data\Blocks\{name}\Input\PROD_PHASE\{stream}` | string | Phase: `L` (liquid) or `V` (vapor) |

Example:
```
set_value(session, aspen_path='\Data\Blocks\COL1\Input\PROD_STAGE\SIDEDRAW', value='25')
set_value(session, aspen_path='\Data\Blocks\COL1\Input\PROD_FLOW\SIDEDRAW', value='50', unit='kmol/hr')
set_value(session, aspen_path='\Data\Blocks\COL1\Input\PROD_PHASE\SIDEDRAW', value='L')
```

### Gotchas

- Mass balance constraint: Distillate + Side draw + Bottoms = Feed. If D + SD > Feed, you get `***SEVERE ERROR: COLUMN NOT IN MASS BALANCE`.
- To move an existing bottoms/distillate stream to a side draw: `remove_stream` → `place_stream` → `connect_stream` to SP(OUT). See [streams.md](../streams.md#reconnecting-streams) for the reconnection workflow.
- Each SP(OUT) connection adds one side draw. Multiple side draws are supported.

## Block-Specific Advanced Inputs

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Input\BLKOPFREWAT` | string | Free-water option for the column |
| `\Data\Blocks\{name}\Input\COND_UTIL` | string | Condenser utility ID |
| `\Data\Blocks\{name}\Input\REB_UTIL` | string | Reboiler utility ID |

> RadFrac has separate utility assignments for condenser and reboiler, instead of a single `UTILITY_ID`.

## Advanced Outputs

| Path | Type | Description |
|------|------|-------------|
| `\Data\Blocks\{name}\Output\COND_USAGE` | float | Condenser utility usage |
| `\Data\Blocks\{name}\Output\COND_COST` | float | Condenser utility cost |
| `\Data\Blocks\{name}\Output\REB_USAGE` | float | Reboiler utility usage |
| `\Data\Blocks\{name}\Output\REB_COST` | float | Reboiler utility cost |
