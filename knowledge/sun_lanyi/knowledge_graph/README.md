# Aspen Plus Sun Lanyi Knowledge Graph

Source PDF: `Aspen Plus-孙兰义.pdf`

This directory is the reusable expert-system layer for future Codex Aspen work.
It is built from chapter-level extracts under `../chapter_extracts/`.

## Lookup Protocol

Before any lookup, read `00_ERROR_MEMORY.md`; when ingesting recent external
knowledge, read `NEW_KNOWLEDGE.md` and use only entries whose status and scope
permit the current task.

When operating Aspen Plus and encountering an unknown situation:

1. Identify the unknown family: component/property, flowsheet input, unit block, reactor kinetics, convergence, result interpretation, file handling, or analysis tool.
2. Search `knowledge_graph_index.md` first for trigger words and node IDs.
3. If the problem resembles a lecture case, especially complex distillation, energy-saving distillation, column optimization, flowsheet tools, reactor cards, or dynamic export, open `classic_cases_playbook.md` for the transferable pattern.
4. Open the referenced chapter extract and source pages.
5. Before creating any module, island, or tower block, open the property-method
   route for the module service and record a property-method-first gate:
   component family, temperature/pressure window, expected phases, polarity and
   non-ideality, Henry/electrolyte/association or gas-solubility needs,
   azeotrope/extractive/solvent behavior if present, binary-parameter or
   PCES/structure support, selected Aspen method, missing data, and status
   (`accepted`, `provisional`, or `blocked`). If this gate fails, do not
   optimize equipment to hide the property-method error.
6. For kinetic reactors, stop at the kinetic freeze gate before entering any Aspen card value.
7. Record source page, source units, Aspen destination card, and verification evidence before promoting a model as accepted.

## Outputs

- `knowledge_graph_index.md`: full node index and trigger map.
- `aspen_operation_playbook.md`: default operating workflow for Codex.
- `kinetics_expert_system.md`: strict reactor kinetics gate and card-entry guide.
- `unknowns_router.md`: unknown-situation routing table.
- `classic_cases_playbook.md`: reusable lecture-case pattern library for complex distillation, energy-saving columns, column optimization, flowsheet tools, reactors, dynamics, and tool scenarios.
## Complementary User Guide Graph

For Aspen Plus V10 user-guide workflow, detailed operations, UI path, help,
file management, reports, plots, convergence, analysis tools, and ActiveX
automation, use the project extension graph:

`{CHEM_WORKSPACE}\aspen_user_guide_v10_knowledge\knowledge_graph\README.md`

This graph is complementary. Keep this Sun Lanyi graph as the textbook/case
pattern authority, and keep `aspen-plus-operations` V14
`manual_knowledge_graph.json` as the field-level card-rule authority. Do not
copy chapter/detail nodes between the graphs; record `UG10-CHxx` or
`UG10-CHxx-Dnnn` IDs when the V10 user guide is used.

## Hard Kinetics Rule

For every kinetic reactor, use `kinetics_expert_system.md` before editing Aspen.
Do not enter `k`, `E`, `Exponent`, LHHW constants, adsorption terms, `Rate basis`,
`[Ci] basis`, or USER subroutine fields until `kinetics_freeze_template.md` is
filled and the row is marked `frozen` or explicitly accepted as `provisional`.

## Property-Method-First Rule

Property method selection is the first step of every Aspen module creation.
This includes full-flow scaffolds, isolated tower islands, reaction islands,
absorbers/strippers, low-temperature solvent washes, regeneration towers,
recycle closures, and pressure/heat-exchanger sections. Choose the property
method from the real component system and phase behavior before `DSTWU`,
`RadFrac`, reactor cards, Design Specs, Calculators, Sensitivities, or
Optimization. If the selected method lacks required binary parameters, Henry
support, electrolyte/association treatment, azeotrope/LLE support, or
temperature/pressure validity for the frozen feed, mark the module
`provisional` or `blocked` and resolve the property gap before optimization.

## Classic Case Rule

Use `classic_cases_playbook.md` to transfer routes, Aspen paths, field meanings,
diagnostic order, and audit checklists. Do not transfer example values as
defaults. Current project source documents outrank every lecture example.

## Project Overlay: Special Columns

Some tower systems cannot or should not start from `DSTWU`. For absorption,
stripping, low-temperature methanol wash, cryogenic solvent absorption,
extractive distillation, azeotropic distillation, three-phase/VLL, reactive
distillation, electrolyte/sour-water, petroleum, or pseudocomponent service,
open `special_columns_direct_radfrac.md`.

The required route is: document why `DSTWU` is invalid, create an isolated
tower-island file named `<project>-<equipment>`, start from a minimal rigorous
`RadFrac` or suitable rigorous column block, preserve each optimization step as
a new tower block, then add Design Spec/Vary only after the rigorous baseline
converges. `SEP/SEP2/SEPARATOR` is not an acceptable replacement for a physical
tower when the project requires a real separation unit.
Each generated tower step must have a same-folder Markdown sidecar note that
briefly records the generation/copy source, optimization action, core inputs and
outputs, pass/fail status, and why the next tower step is needed or why the step
is accepted. Without this sidecar, the tower block is diagnostic only.

Before accepting a full flowsheet, build a tower coverage ledger from the latest
exported input. Every tower-like final block, including main columns, polishing
columns, absorbers, strippers, solvent-wash towers, regeneration towers, and
solvent or entrainer recovery towers, must have isolated design or optimization
evidence. Towers may be optimized together only when they are one physical
separation system, such as a main column plus recovery/regeneration tower
sharing the same solvent or entrainer recycle, frozen feed boundary, product
target, or manipulated degree of freedom. The evidence must state the grouping
reason, the final tower IDs covered, and the sidecar Markdown files supporting
each retained tower step.
