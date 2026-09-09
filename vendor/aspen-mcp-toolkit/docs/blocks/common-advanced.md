# Common Advanced Block Settings

These paths appear on virtually every Aspen Plus block. They are omitted from individual block advanced files to avoid repetition.

All paths below are relative to `\Data\Blocks\{name}\`.

## Property Method Override

| Path | Type | Description |
|------|------|-------------|
| `Input\OPSETNAME` | string | Override the global property method for this block only |

> Use this when a single block needs a different thermodynamic model (e.g. an amine absorber using ELECNRTL while the rest of the flowsheet uses PENG-ROB).

## Electrolyte Settings

| Path | Type | Description |
|------|------|-------------|
| `Input\HENRY_COMPS` | string | Henry's law component list ID |
| `Input\CHEMISTRY` | string | Electrolyte chemistry ID |
| `Input\TRUE_COMPS` | string | Use true-species approach for electrolytes (`YES` / `NO`) |

## Free-Water Settings

| Path | Type | Description |
|------|------|-------------|
| `Input\FRWATEROPSET` | string | Property method for the free-water phase |
| `Input\SOLU_WATER` | string | Water solubility method |

## EO (Equation-Oriented) Mode

| Path | Type | Description |
|------|------|-------------|
| `Input\EO_COMPS` | string | Component list for equation-oriented mode |

## Utility Assignment

| Path | Type | Description |
|------|------|-------------|
| `Input\UTILITY_ID` | string | Utility ID for cost and CO2e tracking |

> Not all blocks expose `UTILITY_ID` in the same way. Some blocks (HeatX, RadFrac) have side-specific utility inputs — see their individual advanced files.

## CO2e Tracking Outputs

These outputs are available on most blocks after simulation completes.

| Path | Type | Description |
|------|------|-------------|
| `Output\BAL_FEEDCO2E` | float | Total feed stream CO2e flow |
| `Output\BAL_PRODCO2E` | float | Total product stream CO2e flow |
| `Output\BAL_NETSTRCO2E` | float | Net stream CO2e production |
| `Output\BAL_UTILCO2E` | float | Utility CO2e production |
| `Output\BAL_TOTCO2E` | float | Total CO2e production |

> `BAL_UTILCO2E` and `BAL_TOTCO2E` are only available on blocks with a utility assignment.

## Utility Cost Output

| Path | Type | Description |
|------|------|-------------|
| `Output\UTL_USAGE` | float | Utility usage |
| `Output\UTIL_COST` | float | Utility cost |
