---
name: aspen-pressure-pfd-delivery
description: Audit and repair Aspen Plus full-flow pressure topology, PFD-style documentation, and LaTeX/PDF delivery packages for chemical-design projects. Use when the user mentions Aspen pressure equipment, compressors/pumps/valves, natural high-pressure feeds, HEATER PRES=0, PFD/PDF/LaTeX reports, bkp/apwz generation, or final delivery packaging for Aspen flowsheets.
---

# Aspen Pressure PFD Delivery

## Network Position

Use this as a pressure/PFD overlay under `aspen-document-driven-flowsheet` or a
specialist section/tower workflow. Upstream authority supplies the accepted
case, pressure ledger, allowed pressure-drop convention, and claims to verify.
This skill returns pressure topology evidence, PFD/PDF synchronization evidence,
and any blocked pressure assumptions to the process authority layer. Mechanical
case generation, run/export, and package QA still go through
`aspen-plus-operations` when that skill is available.

## Scope

Use this as an overlay on top of `aspen-plus-template`, `aspen-two-section-flowsheet`, and `pdf`. It captures the failure modes from full-flow Aspen work: hidden pressure changes in heaters, stale `.bkp/.apwz` files, forced sequence causing recycle mass imbalance, and PDF/PFD statements drifting away from the actual model.

When the current workspace contains
`aspen_sun_lanyi_knowledge/knowledge_graph/README.md`, read it as a local Aspen
knowledge overlay before pressure/PFD edits. Use `unknowns_router.md` for
pressure, dynamic-export, convergence, and unit-block routing, and use
`kinetics_expert_system.md` before changing any kinetic reactor that also has a
pressure, geometry, or delivery impact. If the pressure/PFD issue resembles a
lecture case such as heat pump distillation, HIDiC, dynamic export, or column
pressure analysis, use `classic_cases_playbook.md` only for transferable
patterns, not example values. Ignore this hook outside that workspace.

## Aspen Editing Rules

- Do not hand-edit `.bkp` or `.apwz` internals. Edit the `.inp` source/generation script, then regenerate through Aspen COM.
- Freeze each fresh/boundary feed pressure from current source evidence; do not assume natural high pressure or a universal low-pressure value.
- Put pressure changes in explicit equipment:
  - Gas to higher pressure: `COMPR`, with the current pressure target and source-backed efficiency/basis.
  - Liquid to higher pressure: `PUMP`, with the current pressure target and source-backed efficiency.
  - Letdown: `VALVE`, e.g. `PARAM P-DROP=<bar>`.
- Make the thermal block's pressure-drop convention explicit and source-backed. Use `PRES=0` only when the current model/version and authorized no-drop convention call for it; do not conceal a pressure rise in a heater.
- Keep every reactor pressure condition explicit and tied to its current source and accepted pressure ledger; no private-case reactor pressure table is supplied.
- If a closed recycle case breaks after adding pressure equipment, suspect forced `SEQUENCE MASTER` before weakening the process model. Prefer `CHECKSEQ=NO` with a convergence method already proven for the case.

## Pressure Audit Checklist

After regeneration, verify these from the exported `*_after_run.inp`, block CSV, and stream CSV:

- All thermal-block pressure specifications match the accepted pressure-drop convention; no hidden pressure-raising service is assigned to a heater.
- Fresh/boundary feeds match current source pressure before each explicit pressure-changing device.
- Each pressure jump has a named pump/compressor/valve and status `0`.
- Stream pressures show the intended breakpoints before and after equipment.
- Reactor blocks still run at intended pressure and are not relying on upstream heater pressure.
- Calculators writing feed streams do not write over the outlet of an already-calculated block.

Useful PowerShell patterns:

```powershell
Import-Csv '.\*_blocks.csv' |
  Where-Object { $_.blkstat -notin @('', '0') -or $_.blkmsg }

Import-Csv '.\*_streams.csv' |
  Where-Object { $_.stream -in $currentPressureAuditStreams } |
  Select stream,temp_C,pressure_bar,mole_flow_kmol_h,mass_flow_kg_h

Select-String -LiteralPath '.\*_after_run.inp' `
  -Pattern 'BLOCK E\d+ HEATER|PARAM .*PRES=0|BLOCK K\d+ COMPR|BLOCK P\d+ PUMP|BLOCK V\d+ VALVE'
```

## PFD And Documentation Rules

- PFD pages must reflect the current Aspen topology. Trace each fresh feed, conditioning unit, pressure device, mixer and recycle in actual order; do not reproduce a private-case block sequence.
- Show every current pressure-changing device and its current tag on the PFD when it matters to the pressure audit.
- State the accepted thermal-block pressure-drop convention and expose pressure errors in the actual pumps, compressors, valves, flashes and reactors.
- If a calculator leaves a near-zero positive feed, document the numerical bound separately from physical feed-system requirements; the bound must come from the current project, not a historical example.
- When replacing a boundary or seed recycle with an internal recycle, update the PFD/report to show the real return path and pressure equipment. Then search the generated PDF text, Markdown, LaTeX, and `*_after_run.inp` for stale seed-stream names or obsolete recycle claims.
- When updating Markdown, LaTeX, and generated PDF, keep claims synchronized with file timestamps, page count, and rendered pages.

## PDF/LaTeX Delivery Workflow

1. Regenerate `.tex` from the current Markdown/source script.
2. Compile with XeLaTeX twice.
3. If the target PDF is open and locked, do not fight the viewer; compile with a new job name such as `_fixed`.
4. Verify page count with `pypdf`.
5. Render key PFD pages using `pdftoppm` and inspect PNGs visually.
6. Extract text from PFD pages with `pdftotext` to confirm critical equipment labels are present.
7. In the final response, mention the locked old PDF if the correct version has a new filename.

## Delivery Package

For final handoff, package at least:

- Correct PDF, `.tex`, Markdown source, and report generation script.
- Root `.bkp/.apwz` files for the deliverable Aspen case and any standalone reactor case.
- The Aspen generation script and exported `.inp`, `*_after_run.inp`, stream CSV, block CSV, and run summary CSV.
- A short note in the final answer with validation status, page count, and any file that could not be overwritten because it was open.
