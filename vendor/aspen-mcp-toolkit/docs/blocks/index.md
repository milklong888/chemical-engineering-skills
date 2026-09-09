# Aspen Plus Blocks Index

Each block doc contains: ports, input paths, output paths, typical setup steps, and gotchas.
Advanced files cover property overrides, electrolyte/free-water settings, EO mode, utilities, and CO2e tracking.

## Common

- [common-advanced.md](common-advanced.md) — Advanced settings shared by all blocks (property override, electrolyte, free-water, EO, utility, CO2e)

## Reactors

| Block | Basic | Advanced |
|-------|-------|----------|
| RCSTR (Continuous Stirred Tank Reactor) | [rcstr.md](rcstr.md) | [rcstr-advanced.md](rcstr-advanced.md) |
| RStoic (Stoichiometric Reactor) | [rstoic.md](rstoic.md) | [rstoic-advanced.md](rstoic-advanced.md) |
| RPlug (Plug Flow Reactor) | [rplug.md](rplug.md) | [rplug-advanced.md](rplug-advanced.md) |
| RGibbs (Gibbs Free Energy Minimization) | [rgibbs.md](rgibbs.md) | [rgibbs-advanced.md](rgibbs-advanced.md) |
| REquil (Equilibrium Reactor) | [requil.md](requil.md) | [requil-advanced.md](requil-advanced.md) |
| RYield (Yield Reactor) | [ryield.md](ryield.md) | [ryield-advanced.md](ryield-advanced.md) |
| RBatch (Batch Reactor) | [rbatch.md](rbatch.md) | [rbatch-advanced.md](rbatch-advanced.md) |
| Fluidbed (Fluidized Bed Reactor) | [fluidbed.md](fluidbed.md) | [fluidbed-advanced.md](fluidbed-advanced.md) |

## Distillation Columns

| Block | Basic | Advanced |
|-------|-------|----------|
| RadFrac (Rigorous Distillation) | [radfrac.md](radfrac.md) | [radfrac-advanced.md](radfrac-advanced.md) |
| DSTWU (Shortcut Distillation) | [dstwu.md](dstwu.md) | [dstwu-advanced.md](dstwu-advanced.md) |
| Distl (Edmister Shortcut) | [distl.md](distl.md) | [distl-advanced.md](distl-advanced.md) |
| MultiFrac (Multi-Column Distillation) | [multifrac.md](multifrac.md) | [multifrac-advanced.md](multifrac-advanced.md) |
| PetroFrac (Petroleum Fractionation) | [petrofrac.md](petrofrac.md) | [petrofrac-advanced.md](petrofrac-advanced.md) |
| SCFrac (Short-Cut Fractionation) | [scfrac.md](scfrac.md) | [scfrac-advanced.md](scfrac-advanced.md) |
| Extract (Liquid-Liquid Extraction) | [extract.md](extract.md) | [extract-advanced.md](extract-advanced.md) |
| ConSep (Conceptual Separator) | [consep.md](consep.md) | [consep-advanced.md](consep-advanced.md) |

## Flash Separators

| Block | Basic | Advanced |
|-------|-------|----------|
| Flash2 (Two-Phase Flash) | [flash2.md](flash2.md) | [flash2-advanced.md](flash2-advanced.md) |
| Flash3 (Three-Phase Flash) | [flash3.md](flash3.md) | [flash3-advanced.md](flash3-advanced.md) |
| Decanter (Liquid-Liquid Separator) | [decanter.md](decanter.md) | [decanter-advanced.md](decanter-advanced.md) |
| Sep (Component Separator) | [sep.md](sep.md) | [sep-advanced.md](sep-advanced.md) |
| Sep2 (Two-Outlet Component Separator) | [sep2.md](sep2.md) | [sep2-advanced.md](sep2-advanced.md) |

## Heat Exchangers

| Block | Basic | Advanced |
|-------|-------|----------|
| Heater (Heater / Cooler) | [heater.md](heater.md) | [heater-advanced.md](heater-advanced.md) |
| HeatX (Two-Stream Heat Exchanger) | [heatx.md](heatx.md) | [heatx-advanced.md](heatx-advanced.md) |
| MHeatX (Multi-Stream Heat Exchanger) | [mheatx.md](mheatx.md) | [mheatx-advanced.md](mheatx-advanced.md) |
| HXFlux (Heat Exchanger with Flux) | [hxflux.md](hxflux.md) | [hxflux-advanced.md](hxflux-advanced.md) |

## Pressure Changers

| Block | Basic | Advanced |
|-------|-------|----------|
| Compr (Compressor / Turbine) | [compr.md](compr.md) | [compr-advanced.md](compr-advanced.md) |
| MCompr (Multi-Stage Compressor) | [mcompr.md](mcompr.md) | [mcompr-advanced.md](mcompr-advanced.md) |
| Pump | [pump.md](pump.md) | [pump-advanced.md](pump-advanced.md) |
| Valve | [valve.md](valve.md) | [valve-advanced.md](valve-advanced.md) |
| Pipe (Single-Segment Pipe) | [pipe.md](pipe.md) | [pipe-advanced.md](pipe-advanced.md) |
| Pipeline (Multi-Segment Pipeline) | [pipeline.md](pipeline.md) | [pipeline-advanced.md](pipeline-advanced.md) |

## Mixers / Splitters

| Block | Basic | Advanced |
|-------|-------|----------|
| Mixer | [mixer.md](mixer.md) | [mixer-advanced.md](mixer-advanced.md) |
| FSplit (Stream Splitter) | [fsplit.md](fsplit.md) | [fsplit-advanced.md](fsplit-advanced.md) |
| SSplit (Substream Splitter) | [ssplit.md](ssplit.md) | [ssplit-advanced.md](ssplit-advanced.md) |
| Makeup (Stream Makeup) | [makeup.md](makeup.md) | [makeup-advanced.md](makeup-advanced.md) |

## Solids Handling

| Block | Basic | Advanced |
|-------|-------|----------|
| Crusher (Size Reduction) | [crusher.md](crusher.md) | [crusher-advanced.md](crusher-advanced.md) |
| Screen (Vibrating Screen) | [screen.md](screen.md) | [screen-advanced.md](screen-advanced.md) |
| Classifier (Particle Classifier) | [classifier.md](classifier.md) | [classifier-advanced.md](classifier-advanced.md) |
| Crystallizer | [crystallizer.md](crystallizer.md) | [crystallizer-advanced.md](crystallizer-advanced.md) |
| Granulator | [granulator.md](granulator.md) | [granulator-advanced.md](granulator-advanced.md) |
| Dryer | [dryer.md](dryer.md) | [dryer-advanced.md](dryer-advanced.md) |
| Swash (Solid Washer) | [swash.md](swash.md) | [swash-advanced.md](swash-advanced.md) |
| CCD (Counter-Current Decanter) | [ccd.md](ccd.md) | [ccd-advanced.md](ccd-advanced.md) |

## Solid-Fluid Separators

| Block | Basic | Advanced |
|-------|-------|----------|
| Cyclone (Gas-Solid Cyclone) | [cyclone.md](cyclone.md) | [cyclone-advanced.md](cyclone-advanced.md) |
| ESP (Electrostatic Precipitator) | [esp.md](esp.md) | [esp-advanced.md](esp-advanced.md) |
| FabFl (Fabric Filter / Baghouse) | [fabfl.md](fabfl.md) | [fabfl-advanced.md](fabfl-advanced.md) |
| Vscrub (Venturi Scrubber) | [vscrub.md](vscrub.md) | [vscrub-advanced.md](vscrub-advanced.md) |
| HyCyc (Hydrocyclone) | [hycyc.md](hycyc.md) | [hycyc-advanced.md](hycyc-advanced.md) |
| CfFilter (Crossflow Filter) | [cffilter.md](cffilter.md) | [cffilter-advanced.md](cffilter-advanced.md) |
| Cfuge (Centrifuge) | [cfuge.md](cfuge.md) | [cfuge-advanced.md](cfuge-advanced.md) |
| Filter (Rotary/Belt/Disc Filter) | [filter.md](filter.md) | [filter-advanced.md](filter-advanced.md) |

## Electrochemical

| Block | Basic | Advanced |
|-------|-------|----------|
| Electrolyzer | [electrolyzer.md](electrolyzer.md) | [electrolyzer-advanced.md](electrolyzer-advanced.md) |

## How to Place a Block

```
place_block(session, block_name='B1', block_type='RadFrac')
```
Or with generic tool:
```
add_element(session, '\Data\Blocks', 'B1!RadFrac')
```
