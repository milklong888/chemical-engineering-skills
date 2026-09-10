---
name: aspen-non-reactor-equipment-cost
description: "Generate or reuse Aspen Plus Economic Evaluation Scenario1 packages and extract item-level non-reactor equipment costs from one BKP/APW or a validated batch manifest. Use for ordinary equipment cost, AEPA caseCost generation, EQUIP.ICS parsing, purchased-equipment candidates, equipment coverage, and safe batch scaling."
---

# Aspen Non-Reactor Equipment Cost

## 工作过程

先根据当前模型身份检查是否已有可用的AEPA Scenario1文件，优先直接读取同案设备明细，逐项分清购置费、安装费和项目总投资，并核对真实设备覆盖情况。对塔等被软件拆成多行的设备按所属单元汇总，反应器单独保留为范围外项目，不能把缺失行当作零费用。

本模块优先处理已有文件，但随包封装仍需要用户明确提供兼容的提取和设备锚点脚本；不具备这些依赖时只完成可读证据整理，不声称自动解析成功。生成新的AEPA文件还需要另行授权、商业软件和已验证的自动化环境，历史界面生成路径不是离线必需步骤。最终输出逐项来源、非反应器合计、未覆盖设备和口径差异，交回流程比较。工况或设备数量变化后费用结果失效，应从新版本的设备与经济文件重新计算。

## Scope And Safety

Use this skill for ordinary non-reactor equipment cost only. Do not run
openLCA/LCIA, monetize impacts, edit source BKPs, or change Aspen/AEPA
installation, registry, licenses, certificates, services, DLLs, or files under
Aspen installation directories.

Treat the canonical absolute BKP path as case identity. GUI work must use a
fresh copy under `C:\AspenDeliveryTest` (or another explicit scratch root).
Close or terminate only processes whose command line contains that copied work
directory. Never touch unrelated Aspen sessions.

## One-BKP Entry Point

Use the bundled wrapper with explicitly supplied compatible extraction and
anchor scripts. It first detects an existing usable package, parses it and
writes a summary. The two external scripts below are required, not bundled
aliases. GUI generation is a separately authorized optional route, never a
default stage-check dependency.

```powershell
C:\Python314\python.exe {CHEM_SKILLS}\aspen-non-reactor-equipment-cost\scripts\single_bkp_aepa_non_reactor_cost.py `
  --bkp-path <absolute_bkp> `
  --out-root <case_work_root> `
  --chain-id <chain_id> `
  --stage <stage> `
  --product <product> `
  --route <route> `
  --engine-script <absolute-reviewed-extractor.py> `
  --anchor-script <absolute-reviewed-anchor-reader.py> `
  --compact-paths `
  --precheck-timeout-s 180 `
  --launch-timeout-s 120 `
  --run-timeout-s 300 `
  --save-timeout-s 120 `
  --close-timeout-s 5 `
  --gui-timeout-s 480
```

The normal entry above does not launch GUI. Only with explicit generation
authorization and the required licensed environment, add `--force-gui` and
`--gui-engine-script <absolute-reviewed-generation-engine.py>` when a package
must be regenerated. Missing, stale or wrong-identity input otherwise remains
an explicit dependency; it does not authorize desktop operation.

## Deterministic GUI State Machine

This retained procedure is only for the separately authorized software-generation
route above. It is not the standalone product's ordinary equipment calculation
path and must not be activated by `design_stage`.

Run these states in order. Do not skip forward based on an estimate or on the
mere existence of `.szp/.izp` files.

1. **Copy and precheck**
   - Copy the BKP into one new case work directory.
   - Run the COM precheck on `_precheck\case.bkp`.
   - Stop immediately on precheck error/warning failure; do not open GUI.

2. **Run Aspen before economic activation**
   - Open the copied BKP in Aspen Plus GUI.
   - Invoke Aspen Run once while the economic layer is still inactive.
   - Wait for `结果可供查询` / results available and an idle Run state.
   - A Run timeout is terminal for that attempt. Do not click any economics
     control, dashboard switch, Map, or Save after a Run timeout.

3. **Activate the economic layer after the run**
   - Select the `Economics` ribbon tab.
   - Verify `igRibbon_CheckBoxTool_1` is `激活经济估算` / `Activate`.
   - Enable it through UIA. For the Infragistics checkbox, the validated
     fallback is UIA focus plus a Space window message; verify toggle `0 -> 1`.
   - Require `Map` (`igRibbon_ButtonTool_93`) to become enabled. A checked box
     with disabled Map controls is not successful activation.
   - Require Auto Evaluate (`igRibbon_CheckBoxTool_2`) to be OFF. If it is ON,
     turn it OFF and verify the resulting toggle state. Do not run Aspen with
     Auto Evaluate enabled.

4. **Click the exact dashboard switch once**
   - Enumerate `PART_HorizontalTeaser` controls after the run is idle and the
     economic layer is active.
   - Match Legacy Help `这将显示工艺过程的公用工程成本。` / `utility cost`.
   - Invoke that exact control once with UIA Invoke/Legacy default action.
   - Stable fallback: second teaser from the left.
   - Never click the first/capital-cost teaser in this workflow.
   - Never infer its state from `发送到APEA` or status-bar text.

5. **Evaluate cost**
   - Invoke `Map` (`igRibbon_ButtonTool_93`).
   - In Map Options, require `Evaluate Cost` to be OFF, verify its before/after
     state, then confirm the dialog.
   - Confirm the mapping page with exact `btnOk: OK`. Wait for that page to
     settle before continuing; omitting this confirmation leaves `Size` locked.
   - Require and invoke `Size` (`igRibbon_ButtonTool_94`), then require and
     invoke `Estimate` (`igRibbon_ButtonTool_95`) in that order.
   - Do not wait for a standard package before Save; the validated package is
     created by saving after the explicit Map/confirm/Size/Estimate chain.

6. **Save once after cost evaluation**
   - Use economic-page `btnSave` when enabled.
   - Otherwise use Aspen global Save (`igRibbon_ButtonTool_3`) after Map Options
     cost evaluation is confirmed.
   - Do not try an early Save before Map/confirm/Size/Estimate completes.

7. **Verify the completion gate**
   - Wait for the standard `caseCost\Scenario1` package, not only
     `$CASE$backupCost\Scenario1`.
   - Inspect the package for `EQUIP.ICS`/`EQUIP.TXT` and equipment rows.
   - If the first standard package is stable but lacks the equipment anchor,
     keep the same Aspen session open and perform exactly one bounded
     `Map/confirm/Size/Estimate -> Save -> anchor check` repair attempt.
   - If the second saved package still lacks the anchor, stop the case as
     `equipment_sizing_missing`; never loop indefinitely.
   - Parse item-level values before declaring success.

8. **Close and clean up**
   - Once the package and parse gates pass, stop clicking and do not rerun.
   - Close the launched Aspen window; after the bounded close wait, terminate
     only the copied-work-directory process tree if necessary.
   - Verify zero lingering Aspen/AEPA processes for that work marker.

## Exact Completion Timing

Declare one case complete only when all four gates are true:

```text
casecost_pair_ok = true
equipment_anchor_ok = true
parse_status = parsed
process_exit_verified = true AND lingering_aspen_pid_count = 0
```

Stop immediately once all four are true. Do not click Save again, rerun Aspen,
or reopen AEPA.

These are intermediate evidence, not completion:

- `precheck_ok=True`;
- Aspen status says results are available;
- `$CASE$backupCost` contains `.szp/.izp`;
- standard `.szp/.izp` exists but lacks `EQUIP.ICS`;
- Map/Size/Estimate reports that an action was invoked;
- a GUI method returns without raising an exception.

An empty backup package must never short-circuit the explicit evaluation chain.
A standard package without an equipment anchor triggers the one in-session repair above;
after that bounded attempt, return `equipment_sizing_missing` rather than
inventing zero.

## Bounded Waiting And Failure Stops

- Required control missing or wrong Help/name: stop that case and report the
  control inventory; do not guess coordinates beyond the documented fallback.
- Mapping `btnOk`, `Size`, or `Estimate` unavailable after its bounded wait:
  stop the case at that exact step and preserve the control inventory.
- Save timeout without standard package: `casecost_timeout`.
- Standard package without equipment rows: `equipment_sizing_missing`.
- Parser failure: `parse_failed`.
- Any exception: preserve logs, close only the marked process, and stop. Let the
  main agent diagnose before a retry.

Do not use Computer Use or external `发送到APEA` project creation for routine
generation. Prefer UIA Selection/Toggle/Invoke and UIA-focus/window-message
patterns, which do not require an active desktop. Use bounded `click_input()`
only when the target exposes none of those patterns and an interactive desktop
is available.

## Cost Basis

Preferred item-level sources, in order:

1. `caseCost\Scenario1\Scenario1.szp`
2. `caseCost\Scenario1\Scenario1.izp`
3. unpacked `EQUIP.ICS` / `EQUIP.TXT`

Use `EQUIP` column `Equipment Cost` as the purchased/bare equipment candidate.
Use `PROJSUM` `Purchased Equipment` only as a project-level cross-check. Do not
substitute Installed Cost, Total Direct Cost, Total Project Capital Cost, Total
Project Cost, or installed weight.

Exclude rows whose `component_type` contains `REACTOR`, but retain them in the
audit table with `status=reactor_excluded`. Sum AEPA split tower items by Aspen
block prefix. Explicit AEPA zero-cost connector rows remain zero, not missing.

When item-level and project-level purchased-equipment totals disagree, keep both
and mark `report_tables_disagree_requires_review`.

## Batch Scaling

The validated source manifest is authoritative. Never discover a batch by
recursively grabbing every BKP under a large tree.

```text
<batch_root>\
  source_manifest.csv
  batch_ledger.csv
  cases\
    <sequence>__<stage>__<product>__<route>__<path_sha10>\
      case_manifest.json
      source_bkp_pointer.txt
      single_bkp_runs\
        r<timestamp>\
          gui\
          extract\
          logs\
          single_bkp_non_reactor_cost_summary.json
```

Before submission, require `batch_audit.json status=pass`, unique canonical BKP
paths, unique case IDs/work directories, and count reconciliation. Retain ignored
superstructure rows in the manifest with `skip_economic=True`; do not submit
them to Aspen.

Submit cases sequentially at first. After a clean streak with all four completion
gates and zero lingering processes, enlarge the sequential chunk size. A worker
may only execute/read/query; it must stop on the first failed case and return the
evidence to the main agent for diagnosis.

## Required Outputs

Keep these artifacts per BKP identity:

- `single_bkp_non_reactor_cost_summary.json`;
- `summary.csv/json` and GUI JSONL log;
- `caseCost\Scenario1\Scenario1.szp/.izp`;
- `non_reactor_source_inventory.csv`;
- `non_reactor_raw_value_inventory.csv`;
- `non_reactor_selected_basis_candidates.csv`;
- full `aepa_report_*` audit tables.

Report the scenario path, `EQUIP` presence/size, non-reactor item sum, item count,
reactor-excluded count, unresolved count, report-consistency status, block
coverage, elapsed time, and process-cleanup result.
