---
name: aspen-plus-operations
description: Execute Aspen Plus case I/O, component/property and block/stream cards, calculations, run/export and strict evidence checks under a frozen upstream engineering contract. Use for mechanical Aspen implementation, COM operation, card syntax and exact-file QA; do not choose the process route or substitute project values.
---

# Aspen Plus Operations

## 工作过程

接收上层已经确定的模型、单位、允许修改范围和取证要求后，先查操作图谱或当前版本帮助，选择已有脚本处理卡片、文件读写、运行及导出。操作始终在受控文件和自有会话内进行，完成后读取实际输入与结果，确认修改被软件接受，而不是只根据调用返回值判断成功。

它不替上层挑工艺路线。发现要求涉及未冻结的反应、分离或工况变更时先交回专业模块，按[阶段调用规则](../chemical-engineering-expert/references/DESIGN_STAGE_ROUTING.md)补齐需要的检索与设备检查。正式交付时复用唯一错误汇总与原始历史检查器，并对最终路径文件无编辑复开运行；返回操作、运行、产品及交付的不同状态和对应证据。

## Start here

1. Read `references/ERROR_MEMORY.md` and the chemical expert's current
   `STRICT_ACCEPTANCE_AND_LEARNING.md`. Strict is default; any explicit
   case-local relaxation and its descendants remain audit-only, never learning.
2. Freeze the operation goal, source identity, input units, allowed edits,
   required evidence and stop condition from the current task. Missing text
   does not mean missing data: first retrieve or derive what is recoverable.
3. Use `references/operation_graph.md` to select a proven path. For fragile
   fields, query `scripts/query_manual_knowledge.py` or
   `scripts/search_aspen_help.py`; record the node/source IDs.
4. Read only the relevant section of
   `references/operations_workflow.md` before executing detailed cards,
   graphical-file preservation, reaction, solve/control or delivery work.
   For archive/layout preservation, APWZ backup companions, stale saved objects,
   history generation or long Windows paths, also read
   `references/archive_io_workflow.md`.

## Existing execution paths

查当前值先复用同案导出或 `aspen_runtime.py` 的只读节点接口；不要改 Output
或为一次换算添加 Calculator。涉及运行关系、匹配目标或调参时，先读取
[统一内置工具规则](../aspen-document-driven-flowsheet/references/aspen_builtin_solve_fit_tools.md)
并接收其工具方案，再查版本帮助实施原生卡片。外部脚本建卡是自动化，外部逐点
SetValue/Run 不是原生 Sensitivity；卡片、结果表、残差和依赖顺序要同案核对。

| Task | Entry | What it proves |
| --- | --- | --- |
| Common session, units, version and resources | `scripts/aspen_runtime.py` | Structured operation/lifecycle evidence, not process feasibility |
| Bounded external worker | `scripts/aspen_run_supervisor.py` | Stage timeout/owned-worker supervision, not permission to kill other sessions |
| Summary/history interpretation | `scripts/aspen_evidence.py` | Complete supported-schema counts and actual diagnostics |
| No-edit candidate audit | `scripts/aspen_clean_delivery_audit.py` | The emitted evidence gates for the tested candidate/run |
| APW save/reopen | `scripts/apw_saveas_reopen_check.py` | Mechanical save/reopen separately from strict simulation/delivery evidence |
| Card rules and targeted static checks | `references/operation_graph.md` | Routes to existing documented field-specific tools |

Keep old CLI entrypoints usable. Do not create another COM/lock/parser in a
project when these cover the operation. A missing target version, partial
history, uncertain engine state or unsupported format is explicit—not zero.

## Non-skippable boundaries

- Never edit Aspen binary/archive internals as simulation inputs. Preserve the
  original graphical/layout authority when required; an INP reconstruction
  does not automatically preserve it.
- Only an independently created/owned session may be changed or closed. Aspen
  live imports are serial; release only the current owner lock. Do not attach
  to or terminate a user's unrelated session.
- Values/units come from the current project; card mechanics from current help
  and exported verification. Kinetics require their source-to-card freeze.
  Pretrained/example numbers are never defaults.
- Keep the V14 manual graph read-only to V10/vector/project imports. A new
  field-level rule needs deliberate current-help/exported-card verification.
- MCP is optional. Read `references/aspen_mcp_invocation.md` when actually
  using it; missing MCP does not block the available COM/script route.
- A run return, save, readable stream, `BLKSTAT=0`, product result or clean
  success phrase cannot substitute for strict acceptance.

## Strict handoff

Verify the same candidate's complete source-verified version/format Summary
(Terminal Errors, Severe Errors, Errors, Warnings: all named counts zero),
current raw history, run identity, and no contradictions. Physical Property is
one wrapped column in the observed local format; never fabricate columns or
missing zeros. Then check current project targets, balances and equipment.

After copying to the user-facing path, reopen and run that exact file without
model edits and bind its hashes/evidence. A staged-copy diagnostic cannot
substitute. Target-version, PFD/sidecar/USER-library and product gates remain
separate and must actually be tested for the claimed scope.

For later package revisions, compare the model and every runtime dependency
separately from cover notes or other packaging text. Proven unchanged runtime
assets retain their earlier evidence within its original scope; changed notes
need their own consistency review. A changed package hash alone neither proves
the model changed nor transfers a whole-package pass. Missing asset identities
remain unresolved. A newly copied final model still needs the exact-path
delivery check above.

Return operation, simulation, product and delivery states separately, together
with artifact identities, failed/unknown gates and the next scoped action.
A local relaxation is `case_accepted_with_relaxation`, never `strict_passed`.

阶段收尾若发现有证据且值得复用的新方法或原则，将候选交主助手，按
[主动经验提醒](../chemical-engineering-expert/references/EXPERIENCE_INBOX.md#主动提醒使用者)
展示可审阅摘要并推进确认/投稿；拒绝不催促，已有有效授权不重复询问。
