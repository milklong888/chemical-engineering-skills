# Exploration Lessons And Generalization

## What was tried

1. Direct AEPA generation and extraction was explored first because item-level
   `EQUIP` rows are a useful same-case gold check.
2. GUI/COM activation, certificate state, sizing completion, and package creation
   proved too fragile for a thousand-case primary method. System-level repair or
   bypass also creates unacceptable risk for the offline installation.
3. Official Aspen V14 documentation showed the explainable workflow that must be
   preserved: simulation object mapping, one-to-many physical equipment mapping,
   preliminary sizing, then model-based cost evaluation.
4. Aspen's proprietary cost database was therefore replaced, for the public and
   reproducible layer, with extracted authoritative correlations and explicit
   project evidence. DOE/NETL-2002/1169 yielded 664 purchased-cost anchors across
   conventional equipment families.
5. The NETL anchors were converted to raw CSV, exact-anchor tests, bounded 1D and
   2D interpolation, and explicit cost-basis adjustments. Purchased and installed
   costs remained separate.
6. A clean Stage2 MEA-H2 case was mapped to 11 physical AEPA items. The offline
   same-case total was 852,603.71 USD versus 865,200 USD AEPA item cost, with
   -1.456% total error, 1.086% item median absolute error, and 6.248% maximum.
   This validates implementation consistency for one sample, not transferability.
7. Sources were then broadened by project service: NREL gasification/FT/methanol
   studies, NETL scaling and SNG baselines, EPA absorber/control manuals, VTT
   biomass studies, official Aspen mapping/sizing guides, standards, and vendor
   evidence for specialized packages.

## What generalized

The reusable object is not one universal cost equation. It is a controlled
evidence pipeline:

```text
identity -> mapping -> sizing -> base purchased cost -> explicit adjustment
         -> same-case calibration -> blind validation -> batch selection
```

Each layer has its own source and rejection gate. This prevents recurring errors:

- treating an Aspen duty as a cost;
- mapping SEP2 gas-solid service to a vertical gas-liquid vessel;
- costing a RADFRAC block without its physical subitems;
- using a utility price as equipment CAPEX;
- mixing purchased, installed, BEC, TPC, and TASC;
- fitting one AEPA sample and calling it a universal formula;
- filling an unsupported cyclone/package with the nearest generic equipment;
- converting missing evidence to zero.

## Source expansion policy

Use `authoritative-source-catalog.csv` as the discovery index and copy only the
qualified rows into a generated Skill's source-evidence ledger. The catalog is
not automatic approval. Licensed Aspen manuals can support mapping/sizing while
remaining non-redistributable; public NETL/NREL/EPA reports can support numerical
methods when their exact tables/formulas are acquired, hashed, extracted, and
reproduced. Vendor evidence is preferred for specialized packages absent from
public generic curves.

The final method must say what remains unknowable. Proprietary Aspen price models
can be used as validation outputs when legally available, but they are not
invented or reverse-engineered into undocumented equations.
