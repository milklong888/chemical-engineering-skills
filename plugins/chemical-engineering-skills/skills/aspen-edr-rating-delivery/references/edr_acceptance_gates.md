# EDR Acceptance Gates

## Coverage Ledger

Use one row per exchanger:

| Field | Meaning |
| --- | --- |
| Tag | Exact Aspen equipment ID |
| Block type | HeatX, Heater, MHeatX, or other |
| Hot/cold streams | Current accepted Aspen stream IDs |
| Process target | Duty, outlet temperature, vapor fraction, or other authority |
| Starting method | Shortcut, Detailed, EDR Design, EDR Rating |
| Same-equipment EDR file | Exact path and hash when formal evidence matters |
| EDR completeness | `TascMsg`, complete state, physical results |
| Aspen binding | Mode/file/result readback after reopen |
| Engineering status | Area, DP, RhoV2, vibration, property range, materials |
| Delivery status | Required Input, all-zero history, process/product gates |
| Next action | Smallest allowed repair |

## Promotion Ladder

1. File present: filename only; no run claim.
2. EDR calculation accepted: same-equipment file, messages and results valid.
3. Aspen binding accepted: EDR survives reopen and outputs are populated.
4. Aspen delivery accepted: exact copied file passes Required Input, zero
   warnings/errors, and process gates.
5. Engineering design accepted: area, pressure drop, vibration, property range,
   and materials are closed.
6. Mechanical/vendor accepted: SW6, drawings, manufacturing, and performance
   guarantee are closed.

Do not collapse these levels. A model can pass level 4 while area margin or
materials remain open at level 5.

## Engineering Checks

| Check | Pass evidence | Common failure |
| --- | --- | --- |
| Duty | EDR duty matches frozen process target/tolerance | EDR silently changes process duty |
| Area | Required and actual area reported; margin acceptable | Negative `% over/under design` |
| U and thermal resistance | Values populated and physically plausible | Shortcut/default U masquerades as EDR |
| Pressure drop | Shell/tube drops within process allowance | Vacuum-side or recycle disturbance |
| Velocity/RhoV2 | No unacceptable high-RhoV2 indication | Excessive entrance/crossflow load |
| Vibration | No unresolved vibration warning | Unsupported tubes or bad shell arrangement |
| Property range | Curves cover full T/P envelope | APPDF temperature/pressure limit |
| Materials | Temperature/corrosion/fabrication basis documented | Alloy copied from another exchanger |
| Process integration | Phases, recycle, product, and capacity preserved | Clean EDR destabilizes downstream Aspen |

## Failure Signatures

| Signature | Decision |
| --- | --- |
| `DETAILED`, no EDR outputs | Non-EDR |
| `Run2=0`, `IsComplete=false` | Failed/incomplete EDR |
| `Operation Failure` in `TascMsg` | Quarantine |
| Property curve below service temperature | Regenerate/extend properties |
| EDR path lost or mode resets after reopen | Binding failed |
| `EDRBLK=0` | EDR did not execute |
| Clean Control Panel with missing EDR results | Aspen clean, EDR absent |
| Negative area margin | EDR present, engineering action open |
| Vibration fixed by parallelization | Rerate and rerun full Aspen gates |
| EDR changes protected duty/recycle/product | Reject or obtain authority |

## Same-Case Authority

Read the current project's EDR coverage ledger, change-offset table and exact
Aspen/EDR audit artifacts. A user-supplied local overlay under `{CHEM_WORKSPACE}`
may help route these files; private case workspaces are not distributed. Keep
all quantities bound to the same equipment and current source version.

