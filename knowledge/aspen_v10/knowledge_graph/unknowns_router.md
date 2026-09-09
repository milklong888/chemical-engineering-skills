<!-- generated: aspen_user_guide_v10 -->
# Aspen Plus V10 User Guide Unknowns Router

Use this when the operation family is unclear.

| Unknown Family | First Nodes | Next Action |
| --- | --- | --- |
| Cannot find a menu/path/help topic | `UG10-CH03`, `UG10-CH01`, `UG10-CH02`, `UG10-CH05`, `UG10-CH15`, `UG10-CH16`, `UG10-CH35`, `UG10-CH37` | Open `UG10-CH03`, then query by UI term. |
| Creating or opening a model | `UG10-CH01`, `UG10-CH02`, `UG10-CH05`, `UG10-CH15`, `UG10-CH16`, `UG10-CH35`, `UG10-CH37`, `UG10-CH38` | Start with `UG10-CH02`, `UG10-CH15`, and operation graph `case-io`. |
| Component/property setup | `UG10-CH02`, `UG10-CH06`, `UG10-CH07`, `UG10-CH08`, `UG10-CH09`, `UG10-CH23`, `UG10-CH27`, `UG10-CH28` | Start with `UG10-CH06`-`UG10-CH08`; then use card graph for field rules. |
| Flowsheet drawing or connection | `UG10-CH01`, `UG10-CH02`, `UG10-CH04`, `UG10-CH09`, `UG10-CH10`, `UG10-CH14`, `UG10-CH24`, `UG10-CH25` | Start with `UG10-CH04` and `UG10-CH09`. |
| Unit-operation model choice | `UG10-CH02`, `UG10-CH10`, `UG10-CH32`, `UG10-CH33`, `UG10-CH38` | Start with `UG10-CH10`; for reactors also open `UG10-CH27`. |
| Run failed or results look stale | `UG10-CH01`, `UG10-CH02`, `UG10-CH05`, `UG10-CH11`, `UG10-CH12`, `UG10-CH13`, `UG10-CH17`, `UG10-CH26` | Start with `UG10-CH11`, `UG10-CH12`, and `UG10-CH17`. |
| Need variable automation | `UG10-CH18`, `UG10-CH19`, `UG10-CH24`, `UG10-CH25`, `UG10-CH17`, `UG10-CH21`, `UG10-CH20`, `UG10-CH26` | Open `UG10-CH18`-`UG10-CH22`. |
| Need Fortran or automation | `UG10-CH18`, `UG10-CH19`, `UG10-CH24`, `UG10-CH25`, `UG10-CH01`, `UG10-CH02`, `UG10-CH05`, `UG10-CH15` | Open `UG10-CH19` and `UG10-CH38`; keep USER delivery gates active. |
| Report/plot/PFD/delivery output | `UG10-CH12`, `UG10-CH13`, `UG10-CH14`, `UG10-CH15`, `UG10-CH19`, `UG10-CH33`, `UG10-CH34`, `UG10-CH36` | Open `UG10-CH12`-`UG10-CH15`, `UG10-CH36`, and `UG10-CH37`. |

If no row matches, run:

```text
python aspen_user_guide_v10_knowledge/scripts/query_user_guide_knowledge.py <terms>
python aspen_user_guide_v10_knowledge/scripts/query_user_guide_knowledge.py <terms> --scope details
```
