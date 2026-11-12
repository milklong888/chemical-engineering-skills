# Read-only engineering checks JSON API

This API supports arithmetic and evidence-gap diagnostics. Every result retains
`engineering_acceptance: "not_assessed"` and
`native_calculation_acceptance: "not_assessed"`. A diagnostic `pass` applies only
to the supplied checks, metadata and caller authority. It never establishes EDR
execution, native validation, equipment delivery or source authenticity.

The examples below are **synthetic interface examples, not engineering evidence,
catalog entries, recommended limits or project defaults**. Supply actual same-case
values and source revisions in production. No source file or tolerance card is
modified. Unsupported units/bases remain `unverified`; the caller must explicitly
convert and preserve the conversion source before submitting canonical units.

## Entry points

CLI (PowerShell; JSON file read only, result on stdout):

```text
python -B -X utf8 scripts/engineering_checks.py screen_pipe_candidates --input examples/pipe.json
python -B -X utf8 scripts/engineering_checks.py check_exchanger_basis --input examples/exchanger.json
python -B -X utf8 scripts/engineering_checks.py check_packed_beds --input examples/packed.json
python -B -X utf8 scripts/engineering_checks.py audit_edr_geometry --input examples/geometry.json
```

`--input -` accepts UTF-8 JSON stdin. Exit 0 means a JSON diagnostic was produced,
including a `fail`/`unverified` diagnostic; it does not mean engineering acceptance.
Exit 2 means malformed/unsupported request or file I/O. JSON NaN/Infinity is
rejected. Python callers may import the identically named functions and pass a
dictionary. MCP callers use the same tool names and arguments `{"request": {...}}`.
Malformed nested shapes (for example a null/list acceptance profile, non-array
stages or a null catalog row) return `diagnostic_status: "unverified"` with an
`invalid_request` check and reasons. They cannot produce a pass. Invalid top-level
MCP arguments may additionally receive the SDK's normal validation error.

All source objects have this shape (values below are illustrative):

```json
{"id":"SYNTHETIC-NOT-ENGINEERING-EVIDENCE","locator":"toy-table/row-1","revision":"toy-v1","current_revision":"toy-v1","stale":false}
```

`id`, `locator`, `revision` must be nonblank JSON strings. A supplied `stale`
must be a JSON boolean; numeric/string/null substitutes are unverified, and
`stale: true` prevents a pass. A supplied `current_revision` must be a nonblank
string equal to `revision`. No type coercion is performed. This checks
metadata consistency only; it cannot discover a newer source revision or prove
provenance. Every profile is caller authority, not a built-in universal criterion.

## screen_pipe_candidates

Required top-level fields: `volumetric_flow_m3_s`, `flow_unit: "m3/s"`,
`flow_source`, `velocity_bounds_m_s: {min,max,source}`, and `catalog` list.
Each catalog row needs `id`, `od_mm`, `wall_mm`, `dimension_unit: "mm"`, `source`.
IDs must be nonblank strings or integers (including zero), never booleans,
floats, nulls or containers. IDs must be unique across the supplied catalog;
duplicate references fail and neither duplicate enters feasible candidate IDs.
Source locator should identify the actual catalog row and edition. Positive OD
and wall and `OD > 2*wall` are required. Q may be zero if authority permits it.

The calculation is `ID = (OD - 2*wall)/1000`, `v = Q/(pi*ID^2/4)`.
Bounds are inclusive. It returns per-row source, derived ID, velocity and checks;
`feasible_candidate_ids` contains only rows whose complete diagnostic passes.
No catalog is created and no rounding or selection is performed. The overall
diagnostic aggregates all rows: a rejected alternative may make it `fail` while
other alternatives remain feasible in `feasible_candidate_ids`.

Synthetic example (replace every value/source):

```json
{
  "volumetric_flow_m3_s": 0.002,
  "flow_unit": "m3/s",
  "flow_source": {"id":"SYNTHETIC","locator":"toy-flow","revision":"v1"},
  "velocity_bounds_m_s": {"min":0.5,"max":2,"source":{"id":"SYNTHETIC","locator":"toy-limit","revision":"v1"}},
  "catalog":[{"id":"toy-row","od_mm":60,"wall_mm":3,"dimension_unit":"mm","source":{"id":"SYNTHETIC","locator":"toy-catalog/row-1","revision":"v1"}}]
}
```

## check_exchanger_basis

Required shared fields: `equipment_id`, `basis_id`, `source`,
`acceptance_profile.source`, and `acceptance_profile.basis_id` equal to `basis_id`.
These three identity fields must each be a nonblank string or non-boolean
integer. Nulls, booleans, floats and containers cannot satisfy identity, even
when two malformed containers compare equal. Source metadata fields use the
stricter string-only rule above.
For each side named `hot` and `cold`, supply:

```json
{
  "pin_abs_pa":200000,"pout_abs_pa":190000,"calculated_dp_pa":10000,
  "pressure_unit":"Pa","pressure_basis":"absolute",
  "source":{"id":"SYNTHETIC","locator":"toy-side","revision":"v1"},
  "reynolds_endpoints":{
    "inlet":{"phase":"liquid","value":100,"source":{"id":"SYNTHETIC","locator":"toy-Re-in","revision":"v1"}},
    "outlet":{"phase":"liquid","value":100,"source":{"id":"SYNTHETIC","locator":"toy-Re-out","revision":"v1"}}
  }
}
```

Each corresponding `acceptance_profile.hot`/`.cold` needs
`max_dp_pa`, `dp_closure_tolerance_pa`, and `reynolds_endpoints` with inlet/outlet
objects `{phase,min?,max?}`. At least one Re bound must be present; phase must
match each actual endpoint. `min` and `max` are inclusive for compatibility.
Use numeric `min_exclusive` and/or `max_exclusive` for strict inequalities, for
example `{ "phase":"liquid", "min_exclusive":6000 }` means `Re > 6000` and
rejects exactly 6000. Do not supply both `min` and `min_exclusive` or both `max`
and `max_exclusive`; conflicting, null or empty-range bounds remain unverified.
No generic turbulent-flow threshold is imposed.
Pressure is positive absolute; `Pin-Pout >= 0`. Calculated DP must be independently
supplied; it is never filled from Pin-Pout. Check closure
`abs(calculated_dp - (Pin-Pout)) <= supplied_tolerance` and allowance separately.
The closure tolerance is a diagnostic acceptance input, never a solver edit.

Area needs `actual`, `required` (positive), `unit: "m2"`, `actual_basis`,
`required_basis` (`gross` or `effective`), `actual_condition`, `required_condition`
(`clean` or `fouled`), and `source`. `acceptance_profile.area` needs `basis`,
`condition`, `min_margin_fraction`, and optional `max_margin_fraction`. All
bases/conditions must match. The margin is `actual/required - 1` and is compared
with the supplied inclusive minimum and, when supplied, inclusive maximum.
For example, caller authority requiring 30–50% uses `min_margin_fraction:0.3`
and `max_margin_fraction:0.5`; `actual/required = 1.6` fails that interval.
An explicitly null/nonfinite maximum or a maximum below the minimum is
unverified; omitting the maximum preserves a minimum-only criterion. Missing,
mixed clean/fouled, mixed gross/effective or unknown units remain `unverified`.

## check_packed_beds

Required fields:

- `expected_stage_ids`: explicit nonempty unique list of nonblank string/integer IDs;
  `stage_source`: authority for the complete expected stage inventory.
- `stages`: list `{stage_id,fc,fc_unit:"dimensionless",source}`. Exact coverage,
  duplicates, missing IDs and extra IDs are checked. Every stage FC is compared
  individually; an average cannot hide an out-of-range stage.
- `diameter_m`, `diameter_unit:"m"`, `diameter_source`.
- `beds`: list `{id,stage_ids,height_m,height_unit:"m",source,hetp_m,
  hetp_unit:"m/stage",hetp_source}`. Exact unique stage coverage across beds is
  required. HETP is supplied per bed from its own source, never filled globally.
- `total_packed_height_m`, `total_height_unit:"m"`, `total_height_source`.
- `acceptance_profile`: `{source,fc_min,fc_max,fc_unit:"dimensionless",
  height_closure_tolerance_m,height_rules,grading_rule?}`.

Expected stage IDs, actual stage IDs, every bed's stage IDs and bed IDs use the
same nonblank-string/non-boolean-integer identity rule. No coercion is performed:
`true` cannot match stage integer `1`, floats cannot match integer IDs, and
blank IDs cannot pass. Invalid identity values remain unverified; observed
valid-ID duplicates or missing/extra coverage fail their respective checks.

Each `height_rules` entry has optional `diameter_min_exclusive_m`, optional
`diameter_max_inclusive_m`, and required `max_height_m`. Exactly one rule must
match the diameter. A caller choosing an explicit split at 1 m would specify
one rule with `diameter_max_inclusive_m:1` and a second with
`diameter_min_exclusive_m:1`: exactly 1 m belongs to the first (`D <= 1`).
The tool supplies neither that boundary nor either height limit.

Per bed compare `height <= selected_max`, and
`abs(height - HETP*len(stage_ids)) <= height_closure_tolerance_m`; compare the
sum of all bed heights with the reported total on the same supplied tolerance.
Optional `grading_rule` is `{criterion,source}` with criterion
`nondecreasing_stage_counts` or `nonincreasing_stage_counts`. Bed list order is
the physical ordering specified by the caller. Unknown grading rules remain
unverified. Omitted optional grading does not imply a required grading policy.

## audit_edr_geometry

Provide exactly one of `xml_path` (read bytes only) or `xml_text`. Result contains
the input XML SHA256. DTD/entity declarations are refused. No XML is rewritten.
Required `mapping` fields: `source` (version/schema verification authority),
`coordinate_unit:"m"`, `bundle_path` (ElementTree path from XML root, matching
exactly one TubeBundle), and `endpoint_path` (relative to each TubeLine).

Generic native-shaped mapping example, synthetic and not a native execution:

```json
{
  "xml_path":"exchanger.EDR",
  "mapping":{
    "source":{"id":"YOUR-VERSION-MAPPING","locator":"your-schema-verification","revision":"your-version"},
    "coordinate_unit":"m",
    "bundle_path":"./objects/object[@name='TubeLayout']/Exchanger/TubeBundle",
    "endpoint_path":"CentrePosition"
  },
  "target_tube_count":3,"effective_tube_count":3,
  "count_source":{"id":"YOUR-COUNTS","locator":"same-equipment-count-fields","revision":"your-version"},
  "coordinate_tolerance_m":0.000000000001,
  "coordinate_tolerance_source":{"id":"YOUR-ACCEPTANCE","locator":"coordinate-readback-resolution","revision":"your-version"}
}
```

The native-shaped example expects `tubePitchInLine` value attribute (m),
`tubeLineOrient` (`Horizontal` or `Vertical`), `tubeOD` (m), and each PassRegion's
TubeLine containing **two direct CentrePosition children** (each x/y `value`
attributes, m) plus `tubeType`. The centers are the first and last tube,
inclusive; a singleton repeats the same coordinate twice. The active axis span
must be nonnegative and an integer number of pitches within the explicit
coordinate tolerance; the other axis must stay constant. Unknown geometry,
missing type/position/pitch/tolerance and nonintegral spans remain unverified.
Each line is limited to 100001 decoded centers as a technical resource bound.

`tlNormal` is counted as heating tubes. `tlTieRod`/`tlSpacer` are separately
decoded; other types remain unverified. The tool checks exact duplicate tube
and rod coordinates and compares target/effective/actual **unique normal tube**
counts. Counts may instead be extracted through explicit mapping keys
`target_count_path` and `effective_count_path` (root-relative scalar paths;
dimensionless values). Source metadata is still required. No absent count is
replaced with zero.

For each PassRegion, `xMin,xMax,yMin,yMax` are compared to decoded normal tube
center extrema, using the supplied coordinate tolerance. `TieRod` children of
TubeBundle use `CentrePosition` and `diameter` in m. For line-decoded rods and
spacers, optional root-relative mapping fields `rod_diameter_path` and
`spacer_diameter_path` identify diameters; their XML `uom` or explicit
`rod_diameter_unit`/`spacer_diameter_unit` must be `m` or `mm`. Missing diameter
does not become zero. Circle overlap uses `distance < (tubeOD+rodOD)/2`;
tangency does not count as overlap. This is only a cross-section circle check,
not support, clearance, vibration, heat-transfer or pressure calculation.


Adapted interface documentation; source owner and original document digest are recorded in SOURCE_METADATA.json. Synthetic examples are not recommended limits.
