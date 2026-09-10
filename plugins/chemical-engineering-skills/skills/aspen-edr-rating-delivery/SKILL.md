---
name: aspen-edr-rating-delivery
description: Build, audit, repair, and deliver Aspen Plus EDR shell-and-tube exchanger ratings with complete HeatX coverage, non-GUI COM/file workflows, true-EDR readback, engineering acceptance gates, and exact BKP/APW zero-warning verification. Use when a user asks to add EDR to every exchanger, check whether EDR was omitted, distinguish HeatX Detailed/Shortcut from real EDR, automate EDR without GUI, bind or repair `.EDR` files, review Rating/Design results, or pass Aspen Required Input and Control Panel delivery gates.
---

# Aspen EDR Rating Delivery

## 工作过程

从当前流程逐台列出需要EDR的双流体换热器，先核对每台的冷热侧、负荷、温压、允许压降和已有文件，再判断它只是流程估算、详细HeatX，还是已经执行了真实EDR。对需要建立或修复的设备，用同一台设备的数据运行EDR，检查面积、流速、压降、振动、物性范围和材料依据，然后通过操作模块绑定到Aspen并复开读取，证明绑定没有丢失。

EDR改变面积、压降或出口状态时，不能只更新换热器表；按[阶段调用规则](../chemical-engineering-expert/references/DESIGN_STAGE_ROUTING.md)回到工艺层复算受影响的循环、产品和公用工程。最后同时交付逐台覆盖记录、EDR依据和精确Aspen文件的验收证据。包内提供方法及接口，不提供商业软件，也不把热工评级当作厂家机械设计批准。

## Role

Operate the EDR-specific layer between process HeatX definition and final Aspen
delivery. Keep three authorities separate:

- process authority: accepted Aspen case, stream conditions, duty/temperature/
  vapor-fraction targets, pressure constraints, and product/recycle gates;
- EDR authority: same-equipment `.EDR`, `TascMsg`, geometry, duty, area, U,
  pressure drop, velocity/RhoV2, vibration, and property-range results;
- delivery authority: exact copied BKP/APW reopened without edits, Required
  Input complete, all-zero Run Status/history, and preserved process targets.

Do not use a clean Aspen run to hide an EDR engineering failure. Do not use a
clean EDR report to bypass the exact Aspen delivery gate.

## Required Routing

Read the active project's change-offset table and same-equipment Aspen/EDR
evidence before any edit. If a user-configured local equipment graph exists
under `{CHEM_WORKSPACE}`, its current registry may route to an EDR overlay.
Private project cases and source textbooks are not bundled; they are optional
local evidence, never default design values.

Use `aspen-plus-operations` for COM/open/set/run/export/save/reopen mechanics
and its strict delivery gate. Use `chemical-equipment-selection-audit` for
materials, standards, SW6/vendor boundaries and report wording.

Read the bundled references:

- [EDR acceptance gates](references/edr_acceptance_gates.md)
- [COM and Aspen card patterns](references/edr_com_card_patterns.md)
- [APWZ compound delivery](references/apwz_compound_delivery.md)

## Operation Contract

Before mutation, record:

```text
Authority Aspen artifact:
Protected working copy:
Eligible HeatX inventory:
Frozen process target for each HeatX:
Allowed EDR/geometry/material changes:
Required engineering gates:
Required Aspen delivery gates:
Stop condition:
```

If the project already has a change-offset table, update it before changing an
accepted EDR mode, file path, geometry, materials, process target, or method.

## Workflow

### 1. Freeze Complete Coverage

Freeze the authorized coverage first: named exchangers for a single-device task,
or every eligible exchanger when full-flow EDR coverage is requested. Export or
inspect the accepted case and inventory every exchanger-like block in that scope.

- Route two-stream `HeatX` blocks to the EDR coverage ledger.
- Keep one-stream `Heater` blocks outside EDR unless the source authorizes a
  second side and the topology change.
- Record tag, block type, hot/cold streams, process target, current method,
  EDR file, evidence, status, and next action.
- Stop scope-completion claims if any eligible HeatX in that authorized scope is absent.

### 2. Classify The Starting State

Use decisive states:

- `shortcut`: process calculation only;
- `detailed_non_edr`: geometry/detail calculation without proven TASC EDR;
- `edr_file_unaccepted`: `.EDR` exists but message/result gates fail;
- `edr_unbound`: accepted `.EDR` not proven in Aspen after reopen;
- `edr_bound_diagnostic`: EDR executes but engineering/process/delivery gates fail;
- `edr_accepted_for_simulation`: EDR and exact Aspen delivery gates pass;
- `vendor_mechanical_open`: thermal rating accepted but SW6/vendor work remains.

Never call `DETAILED`, a path string, `Run2=0`, or clean Control Panel evidence
"EDR complete" without EDR execution and result readback.

### 3. Build Or Repair Same-Equipment EDR

- Use only current-project stream/property/process evidence.
- Use installed Aspen examples to discover local-version enums and file roles.
- Use `BJACWIN.BJACApp` when available for non-GUI EDR open/run/save.
- Parse `.EDR` XML `TascMsg`; do not rely only on COM return values or
  incomplete scalar reads.
- Resolve input errors, operation failures, property-curve range, nonphysical
  outlet states, pressure consistency, geometry, and vibration before binding.
- Keep materials same-equipment and temperature/corrosion-specific. Alloy
  changes do not extend Aspen property curves.

### 4. Bind With The Correct File Role

For a shell-and-tube rating/checking file, the accepted exported pattern should
show the local equivalent of:

```text
CALC-TYPE=RATING
CALC-METHOD=TASCPLUS-RIG
HETRAN-PARAM INPUT-FILE=<same-equipment .EDR>
BJAC-INPUTS METHOD=<EDR-DEFAULT or justified method>
```

Use a Rating file as `RATING`. Do not force it into `DESIGN` merely because the
task asks for design work. Regenerate a true design template when Design is
actually required.

### 5. Prove True EDR After Reopen

Reopen the protected candidate without edits and require:

- rigorous EDR mode and program mode survive;
- input path points to the same-equipment `.EDR`;
- EDR execution/result state such as `EDRBLK=1` and `EDR_PGM=TASCPLUS`;
- report text equivalent to `THIS BLOCK RUNS WITH ASPEN EDR`;
- report program mode `RATING` or the authorized alternative;
- populated EDR duty, area, U, pressure-drop, velocity/RhoV2, and vibration
  results.

Quarantine a branch if reopen returns `SHORTCUT`, `EDRBLK=0`, missing EDR
results, or incomplete Required Input.

### 6. Apply Engineering Gates

For every covered tag, record and judge:

- duty and process-target consistency;
- required area, actual area, and percent over/under design;
- shell/tube pressure drops and allowed limits;
- velocity and high-RhoV2 state;
- vibration state;
- temperature/pressure property-curve coverage;
- material temperature/corrosion/fabrication basis;
- parallel/series arrangement and process integration.

A negative area margin is an open design action even when Aspen is warning-free.
Label the exchanger EDR-rated but not ready for vendor issue until the margin is
closed or explicitly accepted by project authority.

### 7. Apply Aspen Delivery Gates

On the exact candidate, then on the exact copied user-facing file:

1. Reopen without edits.
2. Check `Data.NextIncomplete()==('', 0)` after open, ProcessInput, and run.
3. Run and capture the real `.his`, `.sum`, and `.rep` evidence.
4. Apply the chemical expert's `STRICT_ACCEPTANCE_AND_LEARNING.md` and the
   canonical operations evidence checker: require every named row and column
   in the source-verified version/format schema to be present and all-zero.
   Unknown/incomplete schemas fail; never split a wrapped header or pad zeros.
5. Scan raw history for actual warning/error/severe lines.
6. Confirm every eligible HeatX still reports EDR.
7. Verify process duty, phases, recycle convergence, capacity, and product gates.
8. Hash the exact delivered file and preserve superseded branches as quarantined.

### 8. Package External EDR Files Portably

When rigorous HeatX blocks depend on relative `.EDR` files, prefer an Aspen
compound `.apwz` for a single-file transfer or a fully extracted folder/flat
ZIP for an explicit no-GUI runner.

- Build APWZ through Aspen COM `SaveAs(...apwz, True)` with the accepted model
  and same-equipment EDR files staged together under relative names.
- Never hand-edit APWZ internals. Read-only member enumeration and hashing are
  allowed as packaging evidence.
- Prove every expected EDR member is embedded and byte-identical to the
  accepted sidecar before running the package.
- Aspen Plus V14 standard automation initialization may not open the APWZ
  wrapper directly. For no-GUI QA, hash the exact APWZ, safely extract it into
  a fresh isolated directory while preserving paths, and open the embedded
  BKP/APW without edits. Capture the full Control Panel event stream and same-
  run history from that extracted model.
- Run the APWZ audit without external same-name EDR files beside the package;
  otherwise a missing embedded member can be masked by the filesystem.
- Do not treat Windows ZIP preview as full extraction. Clicking a BKP member
  can omit its EDR siblings even when the archive itself is flat.

## Stop Rules

Stop and quarantine rather than improvise when:

- no same-equipment property/heat-curve basis exists;
- `TascMsg` contains unresolved input error or operation failure;
- property curves do not span the operating envelope;
- outlet temperature, phase, duty, or pressure is nonphysical;
- EDR binding changes a protected process target without authority;
- Aspen resets the EDR mode/file role after reopen;
- Required Input or any final Run Status warning/error is nonzero;
- an eligible HeatX remains uncovered.

## Transfer Rule

Transfer workflows, field meanings, failure signatures, evidence order, and
promotion gates. Never transfer another exchanger's streams, duty, area,
geometry, materials, fouling, pressure drops, method choice, or parallel/series
arrangement without same-equipment evidence.

## Return Contract

```text
Coverage: <covered eligible HeatX>/<total eligible HeatX>
True EDR identity: <per-tag mode/file/readback>
Engineering gates: <area/DP/RhoV2/vibration/property/material status>
Aspen delivery gate: <Required Input and Run Status/history>
Exact delivery file and SHA256:
Quarantined branches:
Open SW6/vendor actions:
```
