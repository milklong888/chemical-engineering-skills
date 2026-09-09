# Kinetics Freeze Template

Use this before entering any kinetic reactor card value in Aspen Plus.

## Status

- Reactor/block:
- Reaction set:
- Status: `blocked | provisional | frozen`
- Source document/page:
- Aspen destination: `Reactions|<ID>|Input|Stoichiometry`, `Reactions|<ID>|Input|Kinetic`, block reaction assignment page, exported input card

## Source Evidence

| Row | Item | Source equation/value | Source units | Source page/render | Adopted basis | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Rate law form |  |  |  |  |  |
| 2 | Stoichiometry |  |  |  |  |  |
| 3 | Phase |  |  |  |  |  |
| 4 | Concentration/pressure basis |  |  |  |  |  |
| 5 | Pre-exponential factor |  |  |  |  |  |
| 6 | Activation energy or B/T term |  |  |  |  |  |
| 7 | Reaction orders/exponents |  |  |  |  |  |
| 8 | Adsorption/equilibrium terms |  |  |  |  |  |
| 9 | Catalyst or volume basis |  |  |  |  |  |

## Conversion Ledger

| Row | Source item | Conversion formula | Aspen card units | Aspen card value | Independent check |
| --- | --- | --- | --- | --- | --- |
| 1 |  |  |  |  |  |

## Aspen Card Mapping

| Aspen path/field | Meaning | Value to enter | Evidence row | Exported verification |
| --- | --- | --- | --- | --- |
| `Reactions|...|Input|Stoichiometry` | Reactants/products coefficients |  |  |  |
| `Reactions|...|Input|Kinetic|Units` | Kinetic unit system |  |  |  |
| `Reactions|...|Input|Kinetic|Reacting phase` | Phase where rate applies |  |  |  |
| `Reactions|...|Input|Kinetic|[Ci] basis` | Concentration basis |  |  |  |
| `Reactions|...|Input|Kinetic|k` | Pre-exponential/rate constant field |  |  |  |
| `Reactions|...|Input|Kinetic|E` | Activation energy field |  |  |  |

## Release Gate

- [ ] Rendered source equation/table inspected.
- [ ] Text extraction checked against rendered source.
- [ ] Full rate law classified before conversion.
- [ ] Units close dimensionally, including pressure/concentration powers.
- [ ] `exp(-B/T)` and `exp(-E/RT)` conventions separated.
- [ ] One-point manual or script rate check reproduced.
- [ ] Aspen destination card meaning verified.
- [ ] Exported Aspen input confirms exact entered values.
- [ ] Any surrogate or fitted value is labeled provisional.
