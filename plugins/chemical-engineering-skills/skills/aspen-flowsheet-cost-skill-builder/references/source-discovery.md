# Source Discovery And Qualification

## Contents

1. Evidence layers
2. Define the evidence question
3. Search order
4. Query patterns
5. Source qualification
6. Data extraction and reproduction
7. Validation and source upgrading
8. Rejection rules

## 1. Evidence layers

Keep evidence in six ledgers so one source cannot silently claim authority it
does not have:

```text
L0 case identity and process boundary
L1 Aspen block to physical-equipment mapping
L2 preliminary sizing inputs, equations, assumptions, and valid range
L3 base purchased-equipment source anchors
L4 explicit index/currency/location/material/pressure/count adjustments
L5 same-case and blind-case validation
```

Official Aspen documentation belongs mainly to L1/L2. NETL Appendix B belongs
to L3. Cost-index and material-factor sources belong to L4. AEPA item rows and
vendor comparisons belong to L5. Evidence may support several layers only when
each role is separately documented.

## 2. Define the evidence question

Do not search for a vague phrase such as "Aspen equipment cost". First write a
source request with:

- physical equipment and subtype;
- process service and phase;
- capacity variable needed by the sizing model;
- purchased equipment versus installed/package/plant scope;
- material and pressure class;
- desired base period, currency, and location;
- required range and expected train count;
- whether the gap is mapping, sizing, cost anchor, index, or validation.

Example:

```text
Need: refractory-lined high-temperature biomass CFB primary cyclone + hopper
Basis: inlet actual gas flow, solids loading, cut size, temperature, pressure
Cost scope: purchased package only, excluding reactor and installation bulks
Evidence gap: public capacity-cost anchors and package boundary
```

## 3. Search order

### Tier A: project and software primary evidence

1. Current project's mother INP/BKP identity, run reports, blocks/streams CSV,
   utility cards, equipment datasheets, vendor quotations, and item-level AEPA
   output from the same case.
2. Installed Aspen Help/eSupport documents and official AspenTech product guides
   for mapping and sizing semantics. These establish what Aspen maps and sizes;
   public product pages do not reveal proprietary cost equations.

### Tier B: government reports, standards, and official manuals

Prefer sources with tables, formulas, capacity ranges, and cost scope:

- DOE/NETL and OSTI for conventional process equipment and energy systems;
- US EPA Air Pollution Control Cost Manual for control-specific equipment;
- NREL/DOE technical reports for renewable-fuel process packages;
- recognized standards and handbooks for physical sizing, such as TEMA/HEI/API,
  when the project has lawful access;
- official cost indexes for escalation.

### Tier C: primary peer-reviewed process studies

Use the original paper and supplementary material. Require its equipment list,
capacity basis, equation, exponent or raw anchors, base year, currency, and
boundary. A paper that cites another cost equation is a locator; follow the
citation to the original source.

### Tier D: vendor budget evidence

For specialized cyclones, hot gas filters, gasifiers, proprietary absorbers, or
packages absent from generic tables, obtain a traceable budget quote or public
vendor sizing/cost sheet. Record inclusions, exclusions, date, delivery basis,
material, pressure, temperature, quantity, and validity period.

### Discovery-only sources

Community posts, slide decks, aggregators, online calculators, and AI summaries
may supply search terms but cannot approve a production formula. Trace every
claim back to the original report, standard, official manual, quote, or paper.

## 4. Query patterns

Search local evidence first:

```powershell
rg -n -i "<equipment>|<service>|purchased equipment|cost correlation|capacity" <project_root>
rg --files <project_root> | rg -i "cost|economic|equipment|datasheet|quote|NETL|EPA|NREL"
```

Before web search, query `authoritative-source-catalog.csv` and
`project-equipment-method-matrix.csv` by stage, Aspen block type, physical
equipment, and service. Record every query and accepted/rejected hit in
`source_search_log.csv`; absence of a match is useful evidence for the next tier.

Use targeted web queries, then open the original result:

```text
site:osti.gov "<equipment>" "purchased equipment cost"
site:netl.doe.gov filetype:pdf "<equipment>" cost capacity
site:epa.gov "<equipment or control device>" "Cost Manual"
site:nrel.gov filetype:pdf "<process>" "techno-economic analysis"
site:aspentech.com "<Aspen block or equipment>" sizing mapping
"<exact paper title>" DOI supplementary material
"<specialized package>" budgetary quote capacity material pressure
```

For a cited equation, search the exact report number, author/title, table name,
or a distinctive 6-10 word phrase. Do not use a search-result snippet as data.

## 5. Source qualification

Add one row to `source_evidence_ledger.csv`. A source cannot be `approved` until
these fields are complete:

- source identity: title, author/organization, year, URL/DOI, local path, hash;
- authority tier and source type;
- exact page, table, figure, equation, or spreadsheet cell;
- equipment, subtype, service, material, pressure, and package boundary;
- purchased/installed/total-capital scope;
- capacity variable, units, basis, and published valid range;
- base period, currency, location, and index basis;
- raw extraction method and review status;
- independent reproduction and calibration status.

Use versioned method IDs when assumptions or sources change. Never overwrite a
previous method silently.

## 6. Data extraction and reproduction

1. Store the original PDF/spreadsheet without editing it and compute SHA256.
2. Extract raw cells into CSV with source page/table/row columns.
3. Visually compare every extracted table against the rendered source pages.
4. Keep purchased and installed fields separate.
5. Write deterministic unit conversions and exact-anchor tests.
6. Reproduce every tabulated anchor exactly before interpolation.
7. Interpolate only within a homogeneous subtype/material/pressure group.
8. Prefer piecewise log-log interpolation for positive capacity-cost tables
   unless the source gives a different equation.
9. Reject extrapolation by default. A reviewed extrapolation is a new method
   version with its own evidence and sensitivity test.
10. Apply cost-index, material, pressure, design, count, currency, and location
    adjustments as visible factors.

## 7. Validation and source upgrading

Use these states:

```text
discovered -> acquired -> extracted -> reproduced -> calibrated -> approved
                                             \-> rejected
```

- `discovered`: bibliographic lead only.
- `acquired`: original source stored and hashed.
- `extracted`: raw data/formula plus locator recorded.
- `reproduced`: exact anchors and units pass automated tests.
- `calibrated`: same-case AEPA, vendor, or independent process benchmark checked.
- `approved`: domain, range, and uncertainty reviewed for the target template.

Same-case calibration tests implementation consistency. Blind cases test
transferability. One fitted case cannot establish a universal multiplier.

## 8. Rejection rules

Reject or leave unresolved when:

- only installed or total project cost is available for a purchased-cost task;
- equipment service, package boundary, capacity basis, or year is ambiguous;
- source is a secondary citation and the original cannot be inspected;
- target size is outside the source range;
- a reactor, logical mixer/splitter, or duplicate hot/cold representation would
  be included as ordinary equipment;
- the method relies on hidden Aspen/AEPA proprietary equations that cannot be
  documented or independently checked;
- a specialized cyclone/filter/package is replaced with a generic vessel;
- missing or parser failure would be converted to zero;
- a correction fitted to one route would be borrowed across routes without an
  explicit compatibility study.

The correct output in each case is an open source/method/validation gap and a
specific next-source request.
