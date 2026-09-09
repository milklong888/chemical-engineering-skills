# Archive I/O, layout preservation and diagnostic evidence

Read for APW/APWZ preservation, graphical-state loss, archive repair, history
generation or deep Windows output paths. These are file/operation procedures;
they never waive the central exact-file all-zero acceptance gate. Retain source
identity and choose the procedure supported by the installed Aspen version.

## APW supplement and original-layout branch

`../scripts/apw_saveas_reopen_check.py` is the existing COM route for adding APW
supplement files from an accepted `.bkp/.inp/.apw`. It can run before SaveAs,
prevents same-stem `.bkp` overwrite by default, reopens each APW, runs it,
exports after-run `.inp/.bkp`, and writes a JSON evidence summary. It opens
`.bkp/.apw` through archive-first methods and uses an ASCII SaveAs fallback
before copying to the requested output path. Mechanical save/reopen success is
reported separately from strict simulation and project delivery evidence.

Keep the user's original archive as the layout authority. An `.inp`-roundtrip
branch may be used to discover minimal card/node changes, but a layout-preserving
delivery branch reopens the original archive and applies only accepted COM-tree
mutations, leaving unrelated graphical/template state untouched. If direct
`node.Delete()` fails for flowsheeting objects, inspect the documented parent
collection operation, for example `parent.Elements.Remove("<name>")`, and verify
the intended object is absent after reopen. Do not invent input for a stale
object merely to silence its missing-input status. Establish its physical and
saved-layout ownership before removing it or defining an explicit layout-only
repair in the project change table.

Do not promote the first successful session. Reopen the generated BKP/APW with
no model edits, rerun, export evidence, and compare file identities before any
user-facing replacement. No unrelated session may be changed or terminated.

## APWZ package and backup companion

Treat the APWZ as a graphics/package authority, not as simulation text. Inspect
its actual member list first. On an isolated copy, reject absolute/traversal
member paths and extract to a short ASCII work directory. When the inspected
package uses an APW plus `.bkp.backup` companion, place that companion beside the
APW as a same-stem `.bkp` for Aspen to open; this is file packaging, not a license
to edit the binary model body.

Open the APW using the established COM route, apply only approved tree changes,
then SaveAs APW and export a BKP. Repackage the verified APW and the required
same-stem `.bkp.backup` companion using the inspected member convention. Preserve
other required package members. Do not assume all versions use the same layout.
Re-extract the candidate APWZ, reopen without further changes, run, and collect
after-run evidence. A working loose APW is not evidence that the final APWZ is
complete or valid. Back up an existing user-facing file before replacement.

## Input-basis and actual stream-path checks

When resolving stream translation warnings, distinguish total-flow basis from
component-flow basis. If the input exports `MASS-FLOW=<total>` and component
`MOLE-FLOW`, write component molar values on the declared units which close with
total mass and molecular weights; do not substitute component mass values into
molar fields. Source units and same-case component identity remain mandatory.
A zero-feed auxiliary block may be removed or bypassed only after the same-run
path audit proves the branch carries no material and the accepted downstream
connection still runs cleanly.

Audit separation targets along the physical stream path, not just a convenient
final product. Where present, an overhead requirement may need overhead vapor,
condenser outlet, reflux-drum phase and final product/recycle checks. A bottoms
specification feeding another tower requires both the bottoms and the actual
downstream feed. Record stream identity and values so clean solver status cannot
hide a missed source requirement.

## BKP-only graphical cleanup boundary

Only when the user explicitly abandons APW/APWZ/layout preservation may an
accepted after-run INP be imported and exported to a fresh BKP to remove stale
saved UI references. The path can discard graphical state. Check the stale
object in the reopened tree, after-run INP and retained archive, not only the
visible display. A later observation export may reintroduce local UI references;
it must not replace a cleaner accepted file without the same identity checks.
Property warnings are still warnings: no exception is implied by their origin.

## Column Internals object versus rating

Do not scalar-write `CA_*` result nodes before Aspen has an internals tree.
First retrieve the installed-version card rule and verify an input/export that
creates the corresponding `SUBOBJECTS INTERNALS`, `COL-CONFIG`, `INTERNALS` and
packing/rating records. Verify both saved object existence and strict run status.
Creating an object is not a completed hydraulic rating. Turning calculation off
does not discharge a required rating gate; manual or vendor evidence is a
different, explicitly approved evidence route on the same operating point.

## Locks, history generation and short labels

If an already-open visible Aspen window locks an APW, do not force-kill it or
silently leave stale files. Save under a non-colliding stem, document the lock,
and replace the original name only when it can be moved safely. Keep earlier
diagnostic histories out of the final delivery's current-run evidence set;
preserve them in the diagnostic record instead of erasing failure history.

`../scripts/aspen_clean_delivery_audit.py` stages a copy in an isolated ASCII
directory, captures available run events, exports after-run evidence, forces
history generation through the supported save route and applies the common
strict parser. That staged-copy result does not replace the final path reopen.
Use a short ASCII audit label, such as `APW01`, under deep Windows paths.
An overlong temporary history name can fail while import/run/export succeeded;
repeat the same-source audit with a short label, retaining the failed receipt,
and judge only complete current `.his`/Summary evidence.

For Design Spec, step-size, feed-estimate or enum probes, separate no-run card
probes from full run probes, and export the card values that actually reached
Aspen. A probe that removes one warning but increases another warning, error,
bad block or recycle failure remains diagnostic. Product, hydraulic, version and
exact-delivery gates must still all be satisfied.

## Preservation basis

This route retains the general procedures from the original operations entry's
`Reusable Operation Scripts` section. Private case numbers, warning exemptions,
unsourced orphan-input substitution and automatic rating bypass are not current
instructions. The original source identity and section disposition are recorded
in the release asset-preservation ledger; this is a reviewed routing repair,
not learned evidence that any new engineering case has passed.
