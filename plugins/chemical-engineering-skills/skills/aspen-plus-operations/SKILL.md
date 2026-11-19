---
name: aspen-plus-operations
description: Execute Aspen Plus case I/O, component/property and block/stream cards, calculations, run/export and strict evidence checks under a frozen upstream engineering contract. Use for mechanical Aspen implementation, COM operation, card syntax and exact-file QA; do not choose the process route or substitute project values.
---

# Aspen Plus Operations

参数/卡片依据不明或warning无法解释时，先按[来源升级与留账](../chemical-engineering-expert/references/KNOWLEDGE_LOOKUP_ESCALATION.md)查询原生图谱、官方知识库及必要的网络来源，再提出有依据的修改。

## 工作过程

新建完整简化流程的第一次原生求解，从阶段协调器 `tools.design_stage.run_buildable_first_scaffold` 调用本层的既有运行函数。三份独立全链审查使用同一份可建模正文，检查未齐时继续补相应规格或复核。已存在文件的机械复开、故障取证和纯资料咨询沿用各自入口。[首版与切岛规格交接](references/unit_modeling_workflow.md)

单模块文字规划也要交接完整：必须实际读取
[单模块方法及交接检查](references/unit_modeling_workflow.md)
的适用部分。输出当前目标—具体操纵/写入变量—边界来源—插入阶段—每轮执行先后
及验证对象，不能只说“用设计规定/计算器”。仅禁止启动Aspen时仍执行相关只读查询
和原 solve_route；真实数值与软件结果保持未验证。每座正式塔必须有有效DS配对方案。

首次建单元、从骨架严化或审核模块遗漏时，先读
[单模块建模入口与必要条件](references/unit_modeling_workflow.md)，按单元族进入既有 owner。
需要控制/分析时读取其中所链的完整内置工具方法；塔正式建模强制 Design Spec/Vary，
不能只列工具名而不说明插入阶段、每轮执行位置和验证证据。

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

在已有流程中落实 HCH 或配对表时，先从[增量接入工作流](../aspen-document-driven-flowsheet/references/hen_incremental_integration.md)取得服务映射和保留清单，再写卡片或改连接。

文件身份、动态工程依赖、目标版本验证或原生分析交付发生类似问题时，参照[项目方法复盘](../chemical-engineering-expert/references/ASPEN_CASE_REVIEW.md)的相应记录。实际接口与验收依当前使用的软件版本。

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
| Summary/history interpretation | `scripts/aspen_evidence.py` | Actual diagnostics and supported-schema counts when reported |
| No-edit candidate audit | `scripts/aspen_clean_delivery_audit.py` | The emitted evidence gates for the tested candidate/run |
| APW save/reopen | `scripts/apw_saveas_reopen_check.py` | Mechanical save/reopen separately from strict simulation/delivery evidence |
| Card rules and targeted static checks | `references/operation_graph.md` | Routes to existing documented field-specific tools |

Keep old CLI entrypoints usable. Do not create another COM/lock/parser in a
project when these cover the operation. A missing target version, partial
history, uncertain engine state or unsupported format is explicit—not zero.

## 会话清理

启动前登记会话归属。运行结束、项目完成、暂停、取消或异常时，按[自动化收尾](references/operations_workflow.md#aspen-automation-closeout)保存检查点、关闭本轮自有会话、核验残留并记录锁状态。

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
- Never change Aspen default or pre-existing global/local solver tolerances
  (including tear/recycle, `CONV-OPTIONS PARAM TOL`, tower `TOL-SPEC` and
  `FLASH_TOL`) to obtain convergence, in either direction. Preserve the
  baseline value and default/explicit card state; no-edit audit alone does not
  prove earlier candidates kept that precision contract.

## Strict handoff

Apply the expert's [Aspen run evidence standard](../chemical-engineering-expert/references/STRICT_ACCEPTANCE_AND_LEARNING.md#2-aspen运行状态检查). Confirm calculation completion, candidate and run identity, and fully captured, decodable Control Panel messages and raw `.his` from that run. Scan both for actual errors, warnings and contradictions. Check Required Input, block status, recycle, balances, products and equipment where applicable. Compare final tolerance cards against the frozen pre-edit baseline. Missing relevant evidence leaves its gate open.

Use `scripts/aspen_clean_delivery_audit.py --mode run` for the normal default check. Use `--mode strict` when the user asks for proof all 12 native counts are zero or the project contract expressly requires that table. Consult the native Summary to investigate anomalies and retain observed nonzero counts. If a clean run emits no native table, record the counts as unavailable and finish the applicable checks.

After copying to the user-facing path, reopen and run that exact file without
model edits and bind its hashes/evidence. A staged-copy diagnostic cannot
substitute. Target-version, PFD/sidecar/USER-library and product gates remain
separate and must actually be tested for the claimed scope.

For later package revisions, use the expert's
[file-scope branches](../chemical-engineering-expert/references/STRICT_ACCEPTANCE_AND_LEARNING.md#文件范围与证据复用).
Keep the verified scope of unchanged assets and the newly delivered file's
exact-path check separate. Apply the check above to the current final model.

Return operation, simulation, product and delivery states separately, together
with artifact identities, failed/unknown gates and the next scoped action.
A local relaxation is `case_accepted_with_relaxation`, never `strict_passed`.

阶段收尾若发现有证据且值得复用的新方法或原则，将候选交主助手，按
[主动经验提醒](../chemical-engineering-expert/references/EXPERIENCE_INBOX.md#主动提醒使用者)
展示可审阅摘要并推进确认/投稿；拒绝不催促，已有有效授权不重复询问。

<!-- milklong-attribution:start -->
作者：milklong（GitHub：milklong888）。[版权与AI辅助编辑署名规则](ATTRIBUTION.md)。
<!-- milklong-attribution:end -->

需要Dynamics导出数据、PFS布局、边界对比或文件交付辅助时，读取[离线工具合同](references/offline_module_tools.md)，选择相应CLI/MCP；原生会话与验收仍按本专业流程。
