# APWZ Compound Delivery

Use this reference when an Aspen Plus case has rigorous HeatX blocks that rely
on external `.EDR` files and the user wants one transferable file or a reliable
extract-and-run package.

## Current-Version Authority

Aspen Plus V14 local help defines `.apwz` as a compound file containing the
simulation and normally external dependencies, explicitly including EDR input
files for rigorous HeatX. Files referenced by relative paths in the simulation
folder or its subfolders are embedded. When Aspen opens the compound file, it
expands the members into a temporary working folder.

Relevant installed help topics:

```text
Subsystems/userguide1/Content/html/compound_document_files_apwz_.htm
Subsystems/gettingstarted/Content/html/Running the Excel Model.htm
Subsystems/heatx/Content/html/heatxhetranoptionshetranfilesheet.htm
Subsystems/userguide3/Content/html/basicfileoperations.htm
```

## Build Pattern

1. Freeze the accepted BKP/APW hash and every accepted same-equipment EDR hash.
2. Stage the model and EDR files together in a short ASCII working directory.
3. Confirm the HeatX cards use relative EDR file names.
4. Open the protected staged model through Aspen COM.
5. Call `SaveAs(<output>.apwz, True)`.
6. Close the COM instance without changing the protected authority source.
7. Enumerate the APWZ members read-only and require one Aspen model member plus
   every expected EDR member.
8. Hash each embedded EDR payload and compare it with the accepted sidecar.

Do not construct or repair APWZ by editing ZIP members. Member inspection is
verification only; Aspen COM remains the writer.

## No-GUI Reopen Pattern

On Aspen Plus V14, the usual automation initializers such as
`InitFromArchive2` and `InitFromFile2` may reject the APWZ wrapper even though
Aspen's desktop file association supports compound files. Do not report this
wrapper-open failure as a simulation error.

For a non-GUI delivery audit:

1. Hash the exact user-facing APWZ.
2. Ensure no external same-name EDR files are available beside it.
3. Safely extract the exact APWZ to a fresh isolated directory; reject absolute
   paths and `..` traversal and preserve embedded relative paths.
4. Record every extracted member hash and select the unambiguous embedded BKP
   or APW.
5. Open that embedded model without edits through Aspen COM.
6. Attach `OnControlPanelMessage` before asynchronous `Engine.Run2(False)`.
7. Require the complete all-zero Control Panel summary, zero hard-pattern
   counts, zero bad blocks, and a clean same-run history.
8. Export after-run input and confirm every eligible HeatX still uses rigorous
   EDR Rating/Design as authorized and references its embedded same-equipment
   EDR file.

This audit starts from the exact compound package and reproduces Aspen's
documented expansion behavior explicitly. Record the strategy as
`safe_extract_exact_package_then_open_embedded_model`; do not call it a native
COM direct-open of the APWZ wrapper.

## Ordinary ZIP Fallback

If a normal ZIP is required, place the BKP, all EDR files, manifest, and runner
at the archive root. After a fresh full extraction, verify all hashes and run
the exact extracted BKP with all sidecars. A flat archive improves ergonomics
but does not make Windows ZIP preview safe: a preview launch can still extract
only the clicked BKP.

## Acceptance Record

Record:

```text
Source model hash before/after APWZ SaveAs:
APWZ hash:
Embedded model member and hash:
Expected EDR members and hashes:
No-external-sidecar proof:
No-GUI extraction/open strategy:
Control Panel message count and all-zero summary:
Same-run history scan:
After-run true-EDR readback:
Target Aspen/EDR version and license requirement:
Quarantined wrapper-open or ZIP-preview attempts:
```
