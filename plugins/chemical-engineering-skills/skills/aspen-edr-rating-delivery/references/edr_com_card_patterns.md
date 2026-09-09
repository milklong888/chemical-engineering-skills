# EDR COM And Aspen Card Patterns

## Non-GUI EDR Evidence

The local Aspen EDR automation server may expose operations such as:

```text
BJACWIN.BJACApp
FileOpen
FileSaveAs
Run / Run2
CheckData
RefreshData
ImportPSF
TransferData
TransferResults
Scalars / Arrays
ResultScalars / ResultArrays
```

Method availability is not acceptance evidence. Capture:

- COM startup/server identity;
- input and output file paths;
- run return;
- completeness state;
- XML `TascMsg` categories and text;
- physical result fields;
- output file hash.

Prefer XML `TascMsg` parsing when COM item access is incomplete. Fail on
unresolved input errors, operation failures, and property/process warnings that
invalidate the result.

## Aspen Shell-And-Tube Rating Pattern

Use exported-card and installed-example evidence for the exact Aspen version.
A verified project rating pattern is structurally equivalent to:

```text
BLOCK EXAMPLE HEATX
    PARAM T-COLD=<target> CALC-TYPE=RATING  &
        CALC-METHOD=TASCPLUS-RIG
    HETRAN-PARAM INPUT-FILE='<same-equipment>.EDR'
    BJAC-INPUTS FOUL-OPTION=PROGRAM METHOD=EDR-DEFAULT
    FEEDS HOT=<hot-in> COLD=<cold-in>
    OUTLETS-HOT <hot-out>
    OUTLETS-COLD <cold-out>
```

The process target may instead be duty, hot-side temperature, or vapor
fraction when the accepted flowsheet requires it. Preserve the source target;
do not pick one from the example.

## Readback Proof

After SaveAs/reopen/run/export, require all applicable evidence:

```text
CALC-METHOD=TASCPLUS-RIG
CALC-TYPE or PROGRAM_MODE matches the file role
INPUT_FILE points to the intended same-equipment .EDR
EDRBLK=1
EDR_PGM=TASCPLUS
report: THIS BLOCK RUNS WITH ASPEN EDR
report: SHELL&TUBE PROGRAM MODE RATING/DESIGN as authorized
report: duty, required area, actual area, margin, U, pressure drops, vibration
```

## False Positives

- `CALC-METHOD=DETAILED` is not EDR.
- `MODE=RIGOROUS` written before export is not proof if reopen resets it.
- `NextIncomplete=('', 0)` is not EDR identity evidence.
- A clean `.his` is not EDR identity evidence.
- A saved `.EDR` with no valid results is not EDR acceptance.
- A rating file placed in a template/design field is not a valid Design case.

## Exact-File Delivery

Use `aspen-plus-operations` for the final sequence:

```text
protected candidate
-> no-mutation reopen/run/export
-> EDR readback and report audit
-> Required Input and all-zero history
-> process/product/recycle gates
-> copy to delivery path and hash
-> no-mutation reopen/run/export of copied file
-> repeat every gate
```

