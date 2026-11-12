# Method boundaries and evidence checklist

This is a sanitized method summary from the professional owner references in
SOURCE_METADATA.json, not a replacement canonical owner or licensed source.
Apply current project authority, current software version and physical laws.
It supplies no project values and verifies no standard clause or native case.

## Requirement classes

| Tag | Meaning and required evidence |
| --- | --- |
| N | Standard clause: identifier, edition/status, scope, page/table and conditions |
| C | Explicit current user/scoring condition: source, units and inequality boundaries |
| S | Software definition: verified version, field/schema and meaning |
| J | Engineering judgment: source, applicability, uncertainty and provisional status |
| U | Unverified: exact missing input/evidence and next check |

C or J does not become a universal N. Standard editions and legal applicability
must be checked from the actual authorized current source; this package includes
no standard PDF and makes no current-edition compliance claim. Unknown warnings
or parameters first route to the native graph, then official software knowledge,
then primary web sources where needed; retain query gaps and version identity.

## Size selection and rounding feedback

Freeze service, both fluid/phase/property bases, flow/temperature/absolute
pressure, duty/temperature targets, operating envelope and allowed DP. Separate
operating/design/test pressure and flange rating. Select sourced candidates for
shell size/thickness, tube OD/wall/length/pitch/passes, baffles and all four
nozzles using the applicable material/size combination. Never splice table rows.
DN, OD and actual flow ID differ; OD minus twice nominal wall is arithmetic,
not a guaranteed minimum measured ID. Screening needs the caller's catalog and
velocity limits and does not choose a minimum or round up automatically.

After selection/rounding, recalculate actual ID, count/layout/effective area,
velocity/rho-v-squared, DP, heat transfer, vibration/span, stress/material and
nozzle/condensate/vent arrangements as applicable. A larger nozzle or thicker
shell is not automatically better. Re, U, FC and calculated DP are outputs;
do not round them manually into acceptance or change existing solver tolerances.

## Warning and phase diagnosis (including message 1061)

Obtain the exact warning text and matching software-version meaning before
attributing a cause. Retain side identity, inlet/outlet T/P/h/phase fraction,
full two-phase property basis/range, geometry, actual/allowed DP, allowed changes
and downstream consequences. Compare same-case actual final states and both
energy sides; use native flash/segment calculations when required. Do not disable
real subcooled boiling, delete complete two-phase properties, rewrite messages
or create trace vapor as a generic warning-removal recipe. A justified physical
change requires affected product/recycle/hydraulic reruns. Closing one warning
is not equipment acceptance; preserve default/existing solver tolerance state.
No automatic warning diagnosis tool is implemented in this package.

## Real geometry and area basis

Require actual tube/rod/plate/strip arrangement and native output consistency.
Supported row endpoints include both end tubes; a singleton repeats its center.
Noncontiguous tubes must not be encoded as a continuous row across empty slots.
Input target, effective count and unique normal heating-tube count must agree;
blocked/dummy tubes cannot create heat-transfer area. Version/unit/schema mapping
and derived cache meaning need independent evidence. Update only justified input
and deterministic derived fields; regenerate output through native software.

`audit_edr_geometry` checks the documented subset only. It does not check all
plates, strips, shells, axial structures, clearances, support or vibration.
A cross-section diagnostic pass cannot become whole-equipment geometry approval.
Match gross/effective/finned and dirty/clean area bases before comparing actual
and required area. Independently checking U requires common-area conversion of
film, cylindrical-wall and both fouling resistances without double counting.
Do not change fouling/HTC to hide an unsuitable size. The implemented area check
supports documented gross/effective and clean/fouled matching only; finned or
other unsupported bases remain unverified. The tool does not calculate U.

## Packed stages, operating envelope and plot position

Freeze software stage -> actual packing stage -> continuous bed mapping, with
condenser/reboiler/dummy stages explicitly excluded. Stage coverage does not
prove bed physical continuity, feed location or redistributor/support capability.
Use sourced per-bed HETP, not a global guessed value. Total column height also
includes distributors, supports, nozzles, disengagement/storage and heads.

Check every required stage/section/operating point, not average FC alone.
Verify fractional/percent units and whether the capacity denominator is maximum
efficient capacity, maximum capacity, loading or flood. A caller capacity override
may bypass the native correlation: disclose it and verify units/source/envelope;
its presence alone neither validates nor permanently invalidates the input.
After diameter/packing/height/load change, rate every stage at the actual rounded
ID, refresh product/hydraulic results, propagate native pressure drops into the
column profile and rerun under original design specifications and precision.
Count packing/distributors/support/demister/nozzle/static DP without omission or
double counting. A pressure-update flag is not observed feedback execution.

FC within caller bounds does not locate an operating point within a hydraulic
plot. Fixed-liquid-flow cross-section, constant L/V ray and two-dimensional region
position are distinct definitions. Native boundary coordinates, units, candidate,
version and refreshed operating point identity are required; missing, stale,
inverted or equal bounds cannot establish position. Neighboring DP-slope estimates
do not equal native curves. Plot-position diagnostics remain **not implemented**;
`check_packed_beds` must not be described as computing plot position or centering.
Single-point results do not prove minimum/normal/maximum envelope coverage, and
tray downcomer/flooding criteria must not be silently applied to packed beds.

## Separate acceptance layers

Source/standard applicability, same-case engineering checks, native EDR/Column
Internals/SW6 or vendor evidence, and exact-file simulation/delivery are separate.
Thermal/hydraulic rating is not manufacturing approval. Missing materials,
allowable stress/expansion, tubesheet/flange/reinforcement, drainage/vent/control
or operating-envelope evidence remains U. Exact native file reopen/run, complete
verified error matrix, same-run Control Panel/history, precision lock, bindings
and different-directory dependency checks belong to the existing operations/EDR
owners, not these offline checks. This package launches no native software.
